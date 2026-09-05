from __future__ import annotations

import math
import threading
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Any, Callable

from hakimi_research.market_data_research_projection import (
    build_market_data_research_projection,
)


def _with_market_data_research_projection(
    method: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    @wraps(method)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        payload = method(*args, **kwargs)
        if type(payload) is not dict:
            raise TypeError("market data truth producer must return a native dict")
        payload["research_projection"] = build_market_data_research_projection(payload)
        return payload

    return wrapped


def _finite_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _positive_decimal_text(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return ""
    if not parsed.is_finite() or parsed <= 0:
        return ""
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _timestamp_ms(value: Any) -> int:
    parsed = _finite_number(value)
    if parsed <= 0:
        return 0
    if 1_000_000_000 <= parsed < 10_000_000_000:
        parsed *= 1000
    return int(parsed)


def _unique_text(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value or "").strip()))


def _permission_enabled(value: Any) -> bool:
    return value is True


def _hazard_enabled(value: Any) -> bool:
    if value is None or value is False:
        return False
    return value is True or type(value) is not bool


def _canonical_snapshot_bar(value: Any) -> str:
    text = str(value or "1m").strip() or "1m"
    if text in {"1m", "1M"}:
        return text
    aliases = {
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "2h": "2H",
        "4h": "4H",
        "6h": "6H",
        "12h": "12H",
        "1d": "1D",
        "1dutc": "1Dutc",
        "1w": "1W",
    }
    return aliases.get(text.lower(), text)


def _canonical_snapshot_session(value: Any) -> str:
    text = str(value or "all").strip().lower()
    return text if text in {"all", "pre", "regular", "post", "overnight"} else "all"


def _usable_quote(quote: dict[str, Any] | None) -> bool:
    row = quote if isinstance(quote, dict) else {}
    source = str(row.get("source") or row.get("origin_source") or "").strip().lower()
    status = str(row.get("status") or "").strip().upper()
    return bool(
        _finite_number(row.get("last")) > 0
        and status not in {"OFFLINE", "ERROR", "UNAVAILABLE"}
        and source not in {"offline", "offline-seed"}
    )


def _quote_refresh_failed(quote: dict[str, Any] | None) -> bool:
    row = quote if isinstance(quote, dict) else {}
    source = str(row.get("source") or row.get("origin_source") or "").strip().lower()
    status = str(row.get("status") or "").strip().upper()
    return bool(
        _hazard_enabled(row.get("refresh_failed"))
        or _finite_number(row.get("last")) <= 0
        or status in {"OFFLINE", "ERROR", "UNAVAILABLE"}
        or source in {"offline", "offline-seed"}
    )


def _last_good_after_refresh_failure(
    previous: dict[str, Any],
    failed: dict[str, Any] | None = None,
    *,
    error: str = "",
) -> dict[str, Any]:
    failed_row = failed if isinstance(failed, dict) else {}
    reason = str(
        error
        or failed_row.get("warning")
        or failed_row.get("error")
        or "forced quote refresh failed; using last known good"
    ).strip()
    quality = dict(previous.get("quote_quality") or {})
    quality_warnings = _unique_text([
        *list(quality.get("warnings") or []),
        reason,
    ])
    quality.update({
        "status": "DEGRADED",
        "fallback": True,
        "warnings": quality_warnings,
    })
    return {
        **dict(previous),
        "status": "STALE",
        "fallback": True,
        "forced": True,
        "refresh_failed": True,
        "warning": reason,
        "quote_quality": quality,
    }


def normalize_quote_data_quality(
    quote: dict[str, Any],
    *,
    asset_type: str,
    observed_at_ms: int,
) -> dict[str, Any]:
    """Build one conservative freshness contract for every batch consumer."""
    clean_asset = "stock" if str(asset_type).lower() == "stock" else "crypto"
    source = str(quote.get("source") or quote.get("origin_source") or clean_asset).strip().lower()
    source_status = str(quote.get("status") or "UNKNOWN").upper()
    quote_quality = quote.get("quote_quality") if isinstance(quote.get("quote_quality"), dict) else {}
    market_session = quote.get("market_session") if isinstance(quote.get("market_session"), dict) else {}
    quote_ts = _timestamp_ms(quote.get("ts"))
    max_future_skew_ms = 5_000
    timestamp_future = bool(quote_ts and quote_ts > int(observed_at_ms) + max_future_skew_ms)
    quote_age_ms: int | None = max(int(observed_at_ms) - quote_ts, 0) if quote_ts else None
    if quote_age_ms is None:
        supplied_age = _finite_number(quote_quality.get("age_ms", quote.get("data_age_ms")), -1)
        quote_age_ms = max(int(supplied_age), 0) if supplied_age >= 0 else None

    quality_status = str(quote_quality.get("status") or "").upper()
    fallback = (
        _hazard_enabled(quote_quality.get("fallback"))
        or _hazard_enabled(quote.get("fallback"))
        or any(token in source for token in ("cache", "seed", "offline", "local"))
    )
    quarantined = _hazard_enabled(quote_quality.get("quarantined")) or _hazard_enabled(quote.get("data_quarantined"))
    quality_warnings = [
        *list(quote_quality.get("warnings") or []),
        *list(quote_quality.get("quarantine_reasons") or []),
    ]
    warnings = _unique_text(quality_warnings or [quote.get("warning")])
    last = _finite_number(quote.get("last"))
    max_quote_age_ms = 120_000 if clean_asset == "stock" else 15_000
    timestamp_fresh = bool(
        quote_age_ms is not None
        and quote_age_ms <= max_quote_age_ms
        and not timestamp_future
    )
    source_online = source_status not in {"OFFLINE", "ERROR", "UNAVAILABLE"} and last > 0

    session_status = str(market_session.get("status") or "").upper()
    session_phase = str(market_session.get("phase") or "").lower()
    provider_confirmed = _permission_enabled(market_session.get("provider_confirmed"))
    if clean_asset == "stock":
        realtime = bool(
            source == "futu"
            and source_online
            and timestamp_fresh
            and provider_confirmed
            and session_status == "LIVE_SESSION"
            and _permission_enabled(market_session.get("is_open"))
            and quality_status not in {"DEGRADED", "REVIEW"}
            and not fallback
            and not quarantined
        )
    else:
        realtime = bool(
            source in {"okx", "okx_realtime", "rest"}
            and source_online
            and timestamp_fresh
            and not fallback
            and not quarantined
        )

    if not source_online:
        status = "OFFLINE"
    elif quarantined:
        status = "REVIEW"
    elif timestamp_future:
        status = "REVIEW"
    elif fallback or quality_status == "DEGRADED":
        status = "DEGRADED"
    elif quote_age_ms is None:
        status = "UNKNOWN"
    elif not timestamp_fresh:
        status = "STALE"
    elif clean_asset == "stock" and session_status in {"LAST_SESSION", "SESSION_BREAK"}:
        status = session_status
    elif clean_asset == "stock" and session_status != "LIVE_SESSION":
        status = "DELAYED"
    elif realtime:
        status = "READY"
    else:
        status = "DELAYED"

    if quote_age_ms is None:
        warnings.append("报价时间不可验证")
    elif timestamp_future:
        warnings.append("报价时间晚于本机时钟，需核验时钟或来源")
    elif status == "STALE":
        warnings.append(f"报价已过期 {quote_age_ms}ms")
    warnings = _unique_text(warnings)

    if fallback:
        label = "本地兜底"
    elif clean_asset == "stock" and source == "futu":
        if realtime:
            label = "Futu实时"
        elif session_status == "LAST_SESSION":
            label = "Futu最近时段"
        elif session_status == "SESSION_BREAK":
            label = "Futu盘中休市"
        elif status == "STALE":
            label = "Futu过期"
        else:
            label = "Futu待确认"
    elif clean_asset == "stock" and source in {"yahoo", "stooq", "external"}:
        label = f"{source or '外部源'}延迟"
    elif clean_asset == "crypto" and source in {"okx", "okx_realtime", "rest"}:
        label = "OKX实时" if realtime else "OKX延迟"
    else:
        label = "来源待确认"

    priority_eligible = bool(status == "READY" and realtime and not warnings)
    tone = "up" if priority_eligible else "down" if fallback or quarantined or status in {"OFFLINE", "STALE"} else "flat"
    return {
        "status": status,
        "source": source,
        "source_status": source_status,
        "label": label,
        "tone": tone,
        "realtime": realtime,
        "fallback": fallback,
        "quarantined": quarantined,
        "quarantine_reasons": _unique_text(list(quote_quality.get("quarantine_reasons") or [])),
        "warnings": warnings,
        "quote_ts": quote_ts,
        "quote_age_ms": quote_age_ms,
        "max_quote_age_ms": max_quote_age_ms,
        "max_future_skew_ms": max_future_skew_ms,
        "timestamp_valid": bool(quote_ts and not timestamp_future),
        "timestamp_fresh": timestamp_fresh,
        "session_status": session_status,
        "session_phase": session_phase,
        "provider_confirmed_session": provider_confirmed,
        "priority_eligible": priority_eligible,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


class MarketDataService:
    def __init__(
        self,
        *,
        now_ms: Callable[[], int],
        pct: Callable[..., float],
        is_stock_symbol: Callable[[str], bool],
        read_stock_quote: Callable[..., dict[str, Any]],
        stock_data_sources_snapshot: Callable[..., dict[str, Any]],
        market_chart_candles: Callable[..., dict[str, Any]],
        okx_first: Callable[[str, dict[str, str]], dict[str, Any]],
        read_crypto_quotes: Callable[[], list[dict[str, Any]]] | None = None,
        read_stock_quotes: Callable[[bool], list[dict[str, Any]]] | None = None,
        read_fast_stock_quote: Callable[[str], dict[str, Any]] | None = None,
        publish_event: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.now_ms = now_ms
        self.pct = pct
        self.is_stock_symbol = is_stock_symbol
        self.read_stock_quote = read_stock_quote
        self.stock_data_sources_snapshot = stock_data_sources_snapshot
        self.market_chart_candles = market_chart_candles
        self.okx_first = okx_first
        self.read_crypto_quotes = read_crypto_quotes
        self.read_stock_quotes = read_stock_quotes
        self.read_fast_stock_quote = read_fast_stock_quote
        self.publish_event = publish_event
        self.cache: dict[str, dict[str, Any]] = {}
        self.quote_cache: dict[str, dict[str, Any]] = {}
        self.batch_cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._snapshot_locks: dict[str, threading.Lock] = {}
        self._quote_locks: dict[str, threading.Lock] = {}
        self._batch_locks: dict[str, threading.Lock] = {}
        self._snapshot_force_generations: dict[str, int] = {}
        self._quote_force_generations: dict[str, int] = {}
        self._batch_force_generations: dict[str, int] = {}
        self._snapshot_force_results: dict[str, dict[str, Any]] = {}
        self._quote_force_results: dict[str, dict[str, Any]] = {}
        self._batch_force_results: dict[str, dict[str, Any]] = {}
        self._consumer_usage: dict[str, dict[str, Any]] = {}
        self._snapshot_seq = 0
        self._batch_seq = 0
        self._stats = {
            "snapshot_requests": 0,
            "snapshot_cache_hits": 0,
            "quote_requests": 0,
            "quote_cache_hits": 0,
            "upstream_quote_calls": 0,
            "local_quote_reads": 0,
            "batch_requests": 0,
            "batch_cache_hits": 0,
            "batch_source_calls": 0,
            "batch_quote_reuses": 0,
        }

    def snapshot(
        self,
        symbol: str,
        *,
        bar: str = "1m",
        limit: int = 300,
        session: str = "all",
        fast: bool = False,
        force: bool = False,
        emit_event: bool = False,
        consumer: str = "unspecified",
    ) -> dict[str, Any]:
        clean_symbol = str(symbol or "BTC-USDT").strip().upper() or "BTC-USDT"
        clean_bar = _canonical_snapshot_bar(bar)
        clean_session = _canonical_snapshot_session(session)
        clean_limit = max(30, min(int(limit or 300), 1000))
        asset_type = "stock" if self.is_stock_symbol(clean_symbol) else "crypto"
        if asset_type != "stock":
            clean_session = "all"
        clean_fast = bool(fast and not force and asset_type == "stock")
        cache_key = f"{asset_type}:{clean_symbol}:{clean_bar}:{clean_session}:{clean_limit}:{int(clean_fast)}"
        cache_ttl_ms = 2500 if clean_fast else 4500
        with self._cache_lock:
            cached = self._cached_snapshot(cache_key, cache_ttl_ms, force)
            snapshot_lock = self._snapshot_locks.setdefault(cache_key, threading.Lock())
            force_generation = int(self._snapshot_force_generations.get(cache_key) or 0)
        if cached:
            return self._finalize_snapshot(cached, clean_symbol, consumer, True, None, emit_event)

        with snapshot_lock:
            with self._cache_lock:
                forced_result = self._snapshot_force_results.get(cache_key) if force else None
                if (
                    forced_result
                    and int(forced_result.get("generation") or 0) > force_generation
                    and isinstance(forced_result.get("payload"), dict)
                ):
                    shared_payload = dict(forced_result["payload"])
                    shared_payload["context"] = {
                        **dict(shared_payload.get("context") or {}),
                        "force_coalesced": True,
                    }
                else:
                    shared_payload = None
                cached = None if force else self._cached_snapshot(cache_key, cache_ttl_ms, False)
            if shared_payload:
                return self._finalize_snapshot(shared_payload, clean_symbol, consumer, False, None, emit_event)
            if cached:
                return self._finalize_snapshot(cached, clean_symbol, consumer, True, None, emit_event)

            quote, quote_cache_hit, quote_cache_age_ms = self._shared_quote(
                clean_symbol,
                asset_type,
                force=force,
                fast=clean_fast,
            )
            candles = self.market_chart_candles(clean_symbol, clean_bar, clean_limit, clean_fast, clean_session, force)
            data_sources = self._data_sources(clean_symbol, clean_bar, clean_session, asset_type)
            payload = self._build_snapshot(clean_symbol, asset_type, clean_bar, clean_session, quote, candles, data_sources)
            with self._cache_lock:
                self._snapshot_seq += 1
                refresh_generation = int(self._snapshot_force_generations.get(cache_key) or 0)
                if force:
                    refresh_generation += 1
                    self._snapshot_force_generations[cache_key] = refresh_generation
                payload["context"] = {
                    "snapshot_id": f"{clean_symbol}:{self.now_ms()}:{self._snapshot_seq}",
                    "symbol": clean_symbol,
                    "bar": clean_bar,
                    "session": clean_session,
                    "limit": clean_limit,
                    "fast": clean_fast,
                    "refresh_generation": refresh_generation,
                    "force_coalesced": False,
                    "quote_cache_hit": quote_cache_hit,
                    "quote_cache_age_ms": quote_cache_age_ms,
                }
                self.cache[cache_key] = {"time": self.now_ms(), "payload": payload}
                if force:
                    self._snapshot_force_results[cache_key] = {
                        "generation": refresh_generation,
                        "payload": dict(payload),
                    }
            return self._finalize_snapshot(payload, clean_symbol, consumer, False, quote_cache_hit, emit_event)

    def quote_batch(
        self,
        symbols: list[str],
        *,
        force: bool = False,
        consumer: str = "market_radar",
    ) -> dict[str, Any]:
        clean_symbols = list(dict.fromkeys(
            str(symbol or "").strip().upper()
            for symbol in symbols[:120]
            if str(symbol or "").strip()
        ))
        clean_consumer = str(consumer or "market_radar").strip().lower()[:40] or "market_radar"
        cache_key = "|".join(clean_symbols) or "EMPTY"
        cache_ttl_ms = 4500
        with self._cache_lock:
            self._stats["batch_requests"] += 1
            cached = self._cached_batch(cache_key, cache_ttl_ms, force)
            batch_lock = self._batch_locks.setdefault(cache_key, threading.Lock())
            force_generation = int(self._batch_force_generations.get(cache_key) or 0)
        if cached:
            return self._finalize_batch(cached, clean_consumer, True)

        with batch_lock:
            with self._cache_lock:
                forced_result = self._batch_force_results.get(cache_key) if force else None
                if (
                    forced_result
                    and int(forced_result.get("generation") or 0) > force_generation
                    and isinstance(forced_result.get("payload"), dict)
                ):
                    shared_payload = dict(forced_result["payload"])
                    shared_payload["context"] = {
                        **dict(shared_payload.get("context") or {}),
                        "force_coalesced": True,
                    }
                else:
                    shared_payload = None
                cached = None if force else self._cached_batch(cache_key, cache_ttl_ms, False)
            if shared_payload:
                return self._finalize_batch(shared_payload, clean_consumer, False)
            if cached:
                return self._finalize_batch(cached, clean_consumer, True)

            quote_rows: dict[str, dict[str, Any]] = {}
            previous_quotes: dict[str, dict[str, Any]] = {}
            missing_crypto: list[str] = []
            missing_stocks: list[str] = []
            reused_quotes = 0
            for symbol in clean_symbols:
                asset_type = "stock" if self.is_stock_symbol(symbol) else "crypto"
                quote_key = f"{asset_type}:{symbol}"
                with self._cache_lock:
                    cached_quote = self.quote_cache.get(quote_key)
                    age_ms = self.now_ms() - int(cached_quote.get("time") or 0) if cached_quote else 0
                if cached_quote and _usable_quote(cached_quote.get("payload")):
                    previous_quotes[symbol] = dict(cached_quote["payload"])
                if cached_quote and not force and age_ms <= 3500:
                    quote_rows[symbol] = dict(cached_quote["payload"])
                    reused_quotes += 1
                elif asset_type == "stock":
                    missing_stocks.append(symbol)
                else:
                    missing_crypto.append(symbol)

            source_calls: list[str] = []
            source_errors: list[str] = []
            if missing_crypto and self.read_crypto_quotes:
                source_calls.append("okx_bulk")
                try:
                    raw_crypto = self.read_crypto_quotes() or []
                except Exception as exc:
                    raw_crypto = []
                    source_errors.append(f"okx_bulk: {exc}")
                crypto_map = {
                    str(row.get("symbol") or row.get("instId") or "").upper(): row
                    for row in raw_crypto
                    if isinstance(row, dict)
                }
                for symbol in missing_crypto:
                    raw = crypto_map.get(symbol)
                    if raw:
                        quote_rows[symbol] = self._normalize_crypto_quote(symbol, raw)

            if missing_stocks and self.read_stock_quotes:
                source_calls.append("stock_bulk")
                try:
                    raw_stocks = self.read_stock_quotes(force) or []
                except Exception as exc:
                    raw_stocks = []
                    source_errors.append(f"stock_bulk: {exc}")
                stock_map = {
                    str(row.get("symbol") or row.get("instId") or "").upper(): row
                    for row in raw_stocks
                    if isinstance(row, dict)
                }
                for symbol in missing_stocks:
                    raw = stock_map.get(symbol)
                    if raw:
                        quote_rows[symbol] = {**raw, "symbol": symbol, "instId": raw.get("instId") or symbol}

            if force:
                refresh_error = "; ".join(source_errors) or "forced quote refresh returned no usable row"
                for symbol, previous_quote in previous_quotes.items():
                    refreshed_quote = quote_rows.get(symbol)
                    if refreshed_quote is None or _quote_refresh_failed(refreshed_quote):
                        quote_rows[symbol] = _last_good_after_refresh_failure(
                            previous_quote,
                            refreshed_quote,
                            error=refresh_error,
                        )

            for symbol, previous_quote in previous_quotes.items():
                refreshed_quote = quote_rows.get(symbol)
                previous_timestamp = _timestamp_ms(previous_quote.get("ts"))
                refreshed_timestamp = _timestamp_ms((refreshed_quote or {}).get("ts"))
                if (
                    refreshed_quote is not None
                    and previous_timestamp
                    and refreshed_timestamp
                    and refreshed_timestamp < previous_timestamp
                ):
                    quote_rows[symbol] = {
                        **_last_good_after_refresh_failure(
                            previous_quote,
                            error="quote_timestamp_regression",
                        ),
                        "cache_regression": True,
                    }

            ordered_rows: list[dict[str, Any]] = []
            for symbol in clean_symbols:
                quote = quote_rows.get(symbol)
                if not quote:
                    continue
                asset_type = "stock" if self.is_stock_symbol(symbol) else "crypto"
                quality = normalize_quote_data_quality(
                    quote,
                    asset_type=asset_type,
                    observed_at_ms=self.now_ms(),
                )
                normalized_quote = {
                    **dict(quote),
                    "data_quality": quality,
                    "quote_age_ms": quality.get("quote_age_ms"),
                }
                ordered_rows.append(normalized_quote)
                with self._cache_lock:
                    self.quote_cache[f"{asset_type}:{symbol}"] = {
                        "time": self.now_ms(),
                        "payload": dict(normalized_quote),
                    }

            with self._cache_lock:
                self._batch_seq += 1
                self._stats["batch_source_calls"] += len(source_calls)
                self._stats["batch_quote_reuses"] += reused_quotes
                refresh_generation = int(self._batch_force_generations.get(cache_key) or 0)
                if force:
                    refresh_generation += 1
                    self._batch_force_generations[cache_key] = refresh_generation
                payload = {
                    "ok": bool(ordered_rows) or not clean_symbols,
                    "rows": ordered_rows,
                    "missing_symbols": [symbol for symbol in clean_symbols if symbol not in quote_rows],
                    "source_errors": source_errors,
                    "context": {
                        "batch_id": f"batch:{self.now_ms()}:{self._batch_seq}",
                        "symbol_count": len(ordered_rows),
                        "requested_count": len(clean_symbols),
                        "crypto_count": len([row for row in ordered_rows if not self.is_stock_symbol(str(row.get("symbol") or row.get("instId") or ""))]),
                        "stock_count": len([row for row in ordered_rows if self.is_stock_symbol(str(row.get("symbol") or row.get("instId") or ""))]),
                        "source_calls": source_calls,
                        "source_errors": source_errors,
                        "reused_quotes": reused_quotes,
                        "refresh_generation": refresh_generation,
                        "force_coalesced": False,
                        "updated_at": self.now_ms(),
                    },
                    "live_trading_allowed": False,
                    "updated_at": self.now_ms(),
                }
                self.batch_cache[cache_key] = {"time": self.now_ms(), "payload": payload}
                if force:
                    self._batch_force_results[cache_key] = {
                        "generation": refresh_generation,
                        "payload": dict(payload),
                    }
            return self._finalize_batch(payload, clean_consumer, False)

    @_with_market_data_research_projection
    def data_truth(
        self,
        symbol: str,
        *,
        bar: str = "",
        session: str = "",
    ) -> dict[str, Any]:
        """Describe the latest in-memory market snapshot without starting network work."""
        clean_symbol = str(symbol or "").strip().upper()
        requested_bar = str(bar or "").strip()
        requested_session = str(session or "").strip().lower()
        asset_type = "stock" if self.is_stock_symbol(clean_symbol) else "crypto"
        max_observation_age_ms = 120_000 if asset_type == "stock" else 15_000

        def bar_identity(value: Any) -> str:
            text = str(value or "").strip().lower()
            return "1d" if text in {"1d", "1dutc"} else text

        requested_bar_id = bar_identity(requested_bar)
        with self._cache_lock:
            candidates: list[tuple[int, int, dict[str, Any]]] = []
            for entry in self.cache.values():
                payload = dict(entry.get("payload") or {})
                if str(payload.get("symbol") or "").upper() != clean_symbol:
                    continue
                payload_bar = bar_identity(payload.get("bar"))
                payload_session = str(payload.get("session") or "").lower()
                score = 0
                if requested_bar_id and payload_bar == requested_bar_id:
                    score += 2
                if requested_session and payload_session == requested_session:
                    score += 1
                candidates.append((score, int(entry.get("time") or 0), payload))
            selected = max(candidates, key=lambda item: (item[0], item[1])) if candidates else None
            cached_quote_entry = dict(self.quote_cache.get(f"{asset_type}:{clean_symbol}") or {})
            cached_quote = dict(cached_quote_entry.get("payload") or {})
            quote_cache_time = int(cached_quote_entry.get("time") or 0)
            snapshot_time = int(selected[1]) if selected else 0
            snapshot = dict(selected[2]) if selected else {}
            if snapshot and requested_bar_id and bar_identity(snapshot.get("bar")) != requested_bar_id:
                snapshot = {}
                snapshot_time = 0
            if (
                snapshot
                and asset_type == "stock"
                and requested_session
                and str(snapshot.get("session") or "").lower() != requested_session
            ):
                snapshot = {}
                snapshot_time = 0

        observed_at = self.now_ms()
        if not snapshot:
            quote_quality = normalize_quote_data_quality(
                cached_quote,
                asset_type=asset_type,
                observed_at_ms=observed_at,
            ) if cached_quote else {}
            quote_source = str(cached_quote.get("source") or cached_quote.get("origin_source") or "")
            quote_only_fallback = bool(
                _hazard_enabled(quote_quality.get("fallback"))
                or _hazard_enabled(cached_quote.get("fallback"))
            )
            quote_only_regression = _hazard_enabled(cached_quote.get("cache_regression"))
            quote_only_sizing_blocked = bool(
                asset_type == "crypto" and (quote_only_fallback or quote_only_regression)
            )
            observation_age_ms = max(observed_at - quote_cache_time, 0) if quote_cache_time else None
            return {
                "schema_version": "market-data-truth-v1",
                "status": "UNKNOWN",
                "mode": "QUOTE_ONLY" if cached_quote else "UNOBSERVED",
                "symbol": clean_symbol,
                "asset_type": asset_type,
                "requested_bar": requested_bar,
                "requested_session": requested_session,
                "snapshot_available": False,
                "evidence_scope": "QUOTE_ONLY" if cached_quote else "UNOBSERVED",
                "snapshot_age_ms": observation_age_ms,
                "max_observation_age_ms": max_observation_age_ms,
                "observation_current": bool(
                    observation_age_ms is not None and observation_age_ms <= max_observation_age_ms
                ),
                "quote": {
                    "status": str(quote_quality.get("status") or "UNKNOWN"),
                    "source": quote_source,
                    "label": str(quote_quality.get("label") or quote_source or "等待报价"),
                    "age_ms": quote_quality.get("quote_age_ms"),
                    "timestamp": int(quote_quality.get("quote_ts") or 0),
                    "reference_price": {
                        "status": "NOT_CHECKED",
                        "value": "",
                        "kind": "LAST_TRADE_REFERENCE",
                        "source": quote_source,
                        "timestamp_ms": int(quote_quality.get("quote_ts") or 0),
                        "snapshot_id": "",
                        "in_memory_only": True,
                        "client_price_used": False,
                    },
                    "sizing_reference": {
                        "status": "BLOCK" if quote_only_sizing_blocked else "NOT_CHECKED",
                        "value": "",
                        "kind": "PUBLIC_BEST_ASK_REFERENCE",
                        "available_size": "",
                        "size_basis": "BASE_CURRENCY",
                        "source": quote_source,
                        "timestamp_ms": int(quote_quality.get("quote_ts") or 0),
                        "snapshot_id": "",
                        "depth_levels": 1,
                        "is_executable_quote": False,
                        "in_memory_only": True,
                        "client_price_used": False,
                        "fallback_used": quote_only_fallback,
                        "cache_regression": quote_only_regression,
                    },
                },
                "candles": {
                    "status": "UNKNOWN",
                    "source": "",
                    "bar": requested_bar,
                    "count": 0,
                    "last_completed_ts": 0,
                    "last_completed_at": "",
                    "age_ms": None,
                },
                "revision_status": "UNKNOWN",
                "analysis_ready": False,
                "realtime_ready": False,
                "research_usable": False,
                "execution_usable": False,
                "warnings": ["尚无该标的行情快照"],
                "next_action": "先在行情台加载该标的，再返回总控查看来源与新鲜度",
                "summary": f"{clean_symbol or '--'} · 尚无行情快照",
                "observed_at": observed_at,
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }

        quote = dict(snapshot.get("quote") or {})
        candles = dict(snapshot.get("candles") or {})
        quality = dict(snapshot.get("data_quality") or {})
        market_session = dict(snapshot.get("market_session") or {})
        quote_quality = normalize_quote_data_quality(
            {
                **quote,
                "quote_quality": dict(quality.get("quote") or quote.get("quote_quality") or {}),
                "market_session": market_session,
            },
            asset_type=asset_type,
            observed_at_ms=observed_at,
        )
        def row_timestamp(row: dict[str, Any]) -> int:
            return _timestamp_ms(row.get("ts", row.get("ts_ms")))

        rows = [dict(row) for row in candles.get("rows") or [] if isinstance(row, dict)]
        max_future_skew_ms = 5_000
        completed_rows = [
            row for row in rows
            if row.get("complete") is True
            and 0 < row_timestamp(row) <= observed_at + max_future_skew_ms
        ]
        latest_completed = max(completed_rows, key=row_timestamp) if completed_rows else {}
        last_completed_ts = row_timestamp(latest_completed) if latest_completed else 0
        latest_snapshot_ts = _timestamp_ms(candles.get("latest_ts"))
        last_completed_at = str(latest_completed.get("date") or "")
        if not last_completed_at and last_completed_ts and last_completed_ts == latest_snapshot_ts:
            last_completed_at = str(candles.get("latest_at") or "")

        candle_quality = dict(candles.get("candle_quality") or {})
        revision = dict(candles.get("data_revision_evidence") or {})
        revision_status = str(revision.get("status") or "UNKNOWN").upper()
        quote_status = str(quote_quality.get("status") or "UNKNOWN").upper()
        quote_source = str(quote.get("source") or quote.get("origin_source") or "")
        candle_source = str(candles.get("source") or "")
        snapshot_id = str(dict(snapshot.get("context") or {}).get("snapshot_id") or "")
        snapshot_age_ms = max(observed_at - snapshot_time, 0) if snapshot_time else None
        observation_current = bool(
            snapshot_age_ms is not None and snapshot_age_ms <= max_observation_age_ms
        )
        candle_bar = str(candles.get("bar") or snapshot.get("bar") or requested_bar).lower()
        candle_bar_ms = {
            "1m": 60_000,
            "3m": 180_000,
            "5m": 300_000,
            "15m": 900_000,
            "30m": 1_800_000,
            "1h": 3_600_000,
            "2h": 7_200_000,
            "4h": 14_400_000,
            "6h": 21_600_000,
            "12h": 43_200_000,
            "1d": 86_400_000,
            "1dutc": 86_400_000,
        }.get(candle_bar, 300_000)
        max_candle_age_ms = candle_bar_ms * (4 if asset_type == "stock" and candle_bar_ms >= 86_400_000 else 3)
        completed_candle_age_ms = max(observed_at - last_completed_ts, 0) if last_completed_ts else None
        supplied_candle_age = _finite_number(candles.get("data_age_ms"), -1)
        candle_age_candidates = [
            age for age in (
                completed_candle_age_ms,
                max(int(supplied_candle_age), 0) if supplied_candle_age >= 0 else None,
            )
            if age is not None
        ]
        effective_candle_age_ms = max(candle_age_candidates) if candle_age_candidates else None
        candle_current = bool(
            effective_candle_age_ms is not None
            and effective_candle_age_ms <= max_candle_age_ms
        )
        warnings = _unique_text([
            *list(quality.get("warnings") or []),
            *list(quote_quality.get("warnings") or []),
            candles.get("warning"),
            candle_quality.get("warning"),
        ])
        snapshot_status = str(quality.get("status") or "UNKNOWN").upper()
        quarantined = _hazard_enabled(quality.get("quarantined"))
        candle_contract_status = str(candle_quality.get("status") or "").upper()
        candle_blocked = bool(
            snapshot.get("ok") is not True
            or candles.get("ok") is not True
            or not rows
            or quarantined
            or quote_status == "REVIEW"
            or candle_contract_status in {"BLOCK", "REVIEW"}
            or revision_status == "BLOCK"
        )
        analysis_ready = bool(
            not candle_blocked
            and completed_rows
            and candle_source
            and revision_status != "BLOCK"
        )
        realtime_ready = bool(
            analysis_ready
            and observation_current
            and candle_current
            and snapshot_status == "READY"
            and quote_status == "READY"
            and _permission_enabled(quote_quality.get("realtime"))
            and _permission_enabled(candles.get("realtime"))
            and quote_source
            and not _hazard_enabled(quality.get("fallback"))
            and not _hazard_enabled(candles.get("fallback"))
            and not warnings
        )
        session_relation = str(
            market_session.get("session_relation") or market_session.get("status") or ""
        ).upper()
        historical_ready = bool(
            analysis_ready
            and observation_current
            and asset_type == "stock"
            and session_relation in {"LAST_SESSION", "SESSION_BREAK", "HISTORICAL_SESSION"}
        )

        if candle_blocked or snapshot_status == "OFFLINE":
            status = "BLOCK"
            mode = "REVIEW" if quarantined or candle_contract_status == "REVIEW" else "BLOCK"
        elif not observation_current or not candle_current:
            status = "STALE"
            mode = "STALE"
        elif realtime_ready:
            status = "READY"
            mode = "REALTIME_READY"
        elif historical_ready:
            status = "STALE"
            mode = "HISTORICAL_READY"
        elif not analysis_ready or not quote_source:
            status = "STALE"
            mode = "PARTIAL"
        else:
            status = "STALE"
            mode = "DEGRADED"

        research_usable = bool(
            analysis_ready
            and observation_current
            and candle_current
            and not quarantined
            and revision_status != "BLOCK"
        )
        reference_price_value = _positive_decimal_text(
            quote.get("last_decimal") or quote.get("last")
        )
        reference_price_ready = bool(
            realtime_ready
            and quote_quality.get("priority_eligible") is True
            and reference_price_value
            and quote_source
            and quote_quality.get("timestamp_valid") is True
            and snapshot_id
        )
        reference_price = {
            "status": "PASS" if reference_price_ready else "NOT_CHECKED",
            "value": reference_price_value if reference_price_ready else "",
            "kind": "LAST_TRADE_REFERENCE",
            "source": quote_source,
            "timestamp_ms": int(quote_quality.get("quote_ts") or 0),
            "snapshot_id": snapshot_id,
            "in_memory_only": True,
            "client_price_used": False,
        }
        best_bid_value = _positive_decimal_text(quote.get("bid_decimal"))
        best_ask_value = _positive_decimal_text(quote.get("ask_decimal"))
        best_ask_size = _positive_decimal_text(quote.get("ask_size_decimal"))
        crossed_best_bid_ask = bool(
            best_bid_value
            and best_ask_value
            and Decimal(best_ask_value) < Decimal(best_bid_value)
        )
        sizing_fallback_used = bool(
            _hazard_enabled(quality.get("fallback"))
            or _hazard_enabled(quote.get("fallback"))
        )
        sizing_cache_regression = _hazard_enabled(quote.get("cache_regression"))
        sizing_reference_blocked = bool(
            asset_type == "crypto"
            and (crossed_best_bid_ask or sizing_fallback_used or sizing_cache_regression)
        )
        order_book_identity_valid = bool(
            best_bid_value
            and best_ask_value
            and best_ask_size
            and Decimal(best_ask_value) >= Decimal(best_bid_value)
        )
        sizing_reference_ready = bool(
            reference_price_ready
            and asset_type == "crypto"
            and order_book_identity_valid
            and not sizing_reference_blocked
        )
        sizing_reference = {
            "status": "BLOCK" if sizing_reference_blocked else "PASS" if sizing_reference_ready else "NOT_CHECKED",
            "value": best_ask_value if sizing_reference_ready else "",
            "kind": "PUBLIC_BEST_ASK_REFERENCE",
            "available_size": best_ask_size if sizing_reference_ready else "",
            "size_basis": "BASE_CURRENCY",
            "source": quote_source,
            "timestamp_ms": int(quote_quality.get("quote_ts") or 0),
            "snapshot_id": snapshot_id,
            "depth_levels": 1,
            "is_executable_quote": False,
            "in_memory_only": True,
            "client_price_used": False,
            "fallback_used": sizing_fallback_used,
            "cache_regression": sizing_cache_regression,
        }
        next_action = {
            "REALTIME_READY": "数据可用于观察与研究；模拟和实盘权限仍关闭",
            "HISTORICAL_READY": "最近完成时段可用于研究；等待下一根完成K线",
            "STALE": "刷新该标的快照后再形成新结论",
            "PARTIAL": "等待报价与K线来源同时确认",
            "DEGRADED": "可查看但暂停形成新结论，先复核来源与警告",
            "REVIEW": "停止使用该快照，并先人工核验隔离或尺度异常",
            "BLOCK": "停止使用该快照，并先人工核验数据异常",
        }[mode]
        return {
            "schema_version": "market-data-truth-v1",
            "status": status,
            "mode": mode,
            "symbol": clean_symbol,
            "asset_type": asset_type,
            "requested_bar": requested_bar,
            "requested_session": requested_session,
            "snapshot_available": True,
            "evidence_scope": "FULL_SNAPSHOT",
            "snapshot_id": snapshot_id,
            "snapshot_age_ms": snapshot_age_ms,
            "max_observation_age_ms": max_observation_age_ms,
            "observation_current": observation_current,
            "quote": {
                "status": quote_status,
                "source": quote_source,
                "label": str(quote_quality.get("label") or quote_source or "来源待确认"),
                "age_ms": quote_quality.get("quote_age_ms"),
                "timestamp": int(quote_quality.get("quote_ts") or 0),
                "timestamp_valid": quote_quality.get("timestamp_valid") is True,
                "realtime": _permission_enabled(quote_quality.get("realtime")),
                "fallback": _hazard_enabled(quote_quality.get("fallback")),
                "quarantined": _hazard_enabled(quote_quality.get("quarantined")),
                "reference_price": reference_price,
                "sizing_reference": sizing_reference,
            },
            "candles": {
                "status": "BLOCK" if candle_blocked else "STALE" if status == "STALE" else "READY",
                "source": candle_source,
                "bar": str(candles.get("bar") or snapshot.get("bar") or requested_bar),
                "count": len(rows),
                "completed_count": len(completed_rows),
                "last_completed_ts": last_completed_ts,
                "last_completed_at": last_completed_at,
                "age_ms": effective_candle_age_ms,
                "max_age_ms": max_candle_age_ms,
                "timestamp_valid": last_completed_ts > 0,
                "current": candle_current,
                "fallback": _hazard_enabled(candles.get("fallback")),
                "in_progress": _permission_enabled(candles.get("in_progress")),
            },
            "revision_status": revision_status,
            "analysis_ready": analysis_ready,
            "realtime_ready": realtime_ready,
            "research_usable": research_usable,
            "execution_usable": False,
            "warnings": warnings,
            "next_action": next_action,
            "summary": f"{clean_symbol} · 报价 {quote_source or '待确认'} · K线 {candle_source or '待确认'} · {status}",
            "updated_at": int(snapshot.get("updated_at") or 0),
            "observed_at": observed_at,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def health(
        self,
        symbol: str = "",
        *,
        bar: str = "",
        session: str = "",
    ) -> dict[str, Any]:
        truth = self.data_truth(symbol, bar=bar, session=session) if str(symbol or "").strip() else None
        with self._cache_lock:
            stats = dict(self._stats)
            rows = []
            for symbol, usage in sorted(self._consumer_usage.items()):
                rows.append({
                    "symbol": symbol,
                    "consumers": sorted(usage.get("consumers") or []),
                    "requests": int(usage.get("requests") or 0),
                    "batch_requests": int(usage.get("batch_requests") or 0),
                    "snapshot_cache_hits": int(usage.get("snapshot_cache_hits") or 0),
                    "quote_cache_hits": int(usage.get("quote_cache_hits") or 0),
                    "last_consumer": usage.get("last_consumer", ""),
                    "updated_at": int(usage.get("updated_at") or 0),
                })
            snapshot_requests = int(stats.get("snapshot_requests") or 0)
            snapshot_hits = int(stats.get("snapshot_cache_hits") or 0)
            quote_requests = int(stats.get("quote_requests") or 0)
            quote_hits = int(stats.get("quote_cache_hits") or 0)
            return {
                "ok": True,
                "service_ok": True,
                "service_status": "ONLINE",
                "ok_scope": "SERVICE_OPERATIONAL_ONLY",
                "status": str((truth or {}).get("status") or "UNKNOWN"),
                "quality_status": str((truth or {}).get("status") or "UNKNOWN"),
                "active_symbol": str((truth or {}).get("symbol") or ""),
                "data_truth": truth,
                "summary": f"共享快照 {snapshot_requests} 次请求 / 快照复用 {snapshot_hits} / 报价复用 {quote_hits}",
                "stats": {
                    **stats,
                    "snapshot_hit_rate_pct": round(snapshot_hits / snapshot_requests * 100, 1) if snapshot_requests else 0.0,
                    "quote_hit_rate_pct": round(quote_hits / quote_requests * 100, 1) if quote_requests else 0.0,
                    "snapshot_cache_entries": len(self.cache),
                    "quote_cache_entries": len(self.quote_cache),
                    "batch_cache_entries": len(self.batch_cache),
                },
                "rows": rows,
                "updated_at": self.now_ms(),
            }

    def execution_context(
        self,
        symbol: str,
        requested_price: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_context = dict(context or {})
        clean_symbol = str(symbol or "").strip().upper()
        asset_type = "stock" if self.is_stock_symbol(clean_symbol) else "crypto"
        execution_bar = str(request_context.get("execution_bar") or "1m").lower()
        if execution_bar not in {"1m", "3m", "5m", "15m"}:
            execution_bar = "1m"
        session = str(request_context.get("session") or "all")
        snapshot = self.snapshot(
            clean_symbol,
            bar=execution_bar,
            limit=80,
            session=session,
            fast=True,
            force=False,
            emit_event=request_context.get("audit_event", True) is not False,
            consumer="risk_engine",
        )
        quality = dict(snapshot.get("data_quality") or {})
        quote = dict(snapshot.get("quote") or {})
        source = dict(snapshot.get("source") or {})
        market_session = dict(snapshot.get("market_session") or {})
        snapshot_context = dict(snapshot.get("context") or {})
        authoritative_price = self.pct(quote.get("last", 0))
        quote_age_ms = source.get("quote_age_ms")
        if quote_age_ms is None:
            quote_age_ms = quote.get("data_age_ms")
        try:
            quote_age_ms = max(int(quote_age_ms), 0) if quote_age_ms is not None else None
        except (TypeError, ValueError):
            quote_age_ms = None

        max_quote_age_ms = 120_000 if asset_type == "stock" else 15_000
        price_tolerance_pct = 1.5 if asset_type == "stock" else 0.75
        price_deviation_pct = 0.0
        if requested_price > 0 and authoritative_price > 0:
            price_deviation_pct = abs(float(requested_price) / authoritative_price - 1) * 100

        reasons: list[str] = []
        snapshot_ready = snapshot.get("ok") is True
        quality_quarantined = _hazard_enabled(quality.get("quarantined"))
        quality_fallback = _hazard_enabled(quality.get("fallback"))
        quality_realtime = _permission_enabled(quality.get("realtime"))
        execution_eligible = _permission_enabled(market_session.get("execution_eligible"))
        if not snapshot_ready or authoritative_price <= 0:
            reasons.append("没有可验证的最新报价")
        if quality_quarantined:
            reasons.append("报价或 K 线已进入数据隔离")
        if quality_fallback:
            reasons.append("当前使用缓存或降级行情")
        if not quality_realtime:
            reasons.append("当前行情不是实时源")
        if asset_type == "stock" and not execution_eligible:
            reasons.append("股票新增模拟风险仅允许提供方确认的正常盘实时行情")
        if quote_age_ms is None:
            reasons.append("报价时间不可验证")
        elif quote_age_ms > max_quote_age_ms:
            reasons.append(f"报价已过期 {quote_age_ms}ms，阈值 {max_quote_age_ms}ms")
        if price_deviation_pct > price_tolerance_pct:
            reasons.append(f"请求价格偏离权威报价 {price_deviation_pct:.2f}%")

        status = str(quality.get("status") or "UNKNOWN").upper()
        if not snapshot_ready or authoritative_price <= 0:
            status = "OFFLINE"
        elif quality_quarantined:
            status = "QUARANTINED"
        elif quality_fallback:
            status = "DEGRADED"
        elif not quality_realtime or quote_age_ms is None or quote_age_ms > max_quote_age_ms:
            status = "STALE"
        elif price_deviation_pct > price_tolerance_pct:
            status = "PRICE_MISMATCH"
        elif not reasons:
            status = "READY"

        normalized_quality = {
            **quality,
            "status": status,
            "asset_type": asset_type,
            "realtime": quality_realtime,
            "fallback": quality_fallback,
            "quarantined": quality_quarantined,
            "quote_age_ms": quote_age_ms,
            "max_quote_age_ms": max_quote_age_ms,
            "price_tolerance_pct": price_tolerance_pct,
            "price_deviation_pct": round(price_deviation_pct, 4),
            "can_increase_risk": not reasons,
            "blocking_reasons": list(dict.fromkeys(reasons)),
            "source": source,
            "market_session": market_session,
        }
        return {
            "data_status": status,
            "data_quarantined": normalized_quality["quarantined"] is True,
            "data_realtime": normalized_quality["realtime"] is True,
            "data_fallback": normalized_quality["fallback"] is True,
            "data_quality": normalized_quality,
            "market_snapshot_id": str(snapshot_context.get("snapshot_id") or ""),
            "authoritative_price": authoritative_price,
            "price_deviation_pct": round(price_deviation_pct, 4),
        }

    def _cached_batch(self, cache_key: str, cache_ttl_ms: int, force: bool) -> dict[str, Any] | None:
        cached = self.batch_cache.get(cache_key)
        age_ms = self.now_ms() - int(cached.get("time") or 0) if cached else 0
        if not cached or force or age_ms > cache_ttl_ms:
            return None
        payload = dict(cached["payload"])
        payload["cached"] = True
        payload["cache_age_ms"] = max(age_ms, 0)
        return payload

    def _cached_snapshot(self, cache_key: str, cache_ttl_ms: int, force: bool) -> dict[str, Any] | None:
        cached = self.cache.get(cache_key)
        age_ms = self.now_ms() - int(cached.get("time") or 0) if cached else 0
        if not cached or force or age_ms > cache_ttl_ms:
            return None
        payload = dict(cached["payload"])
        payload["cached"] = True
        payload["snapshot_cache_age_ms"] = max(age_ms, 0)
        return payload

    def _with_snapshot_event(self, payload: dict[str, Any], emit_event: bool) -> dict[str, Any]:
        result = dict(payload)
        if emit_event:
            event = self._publish_snapshot_event(result)
            if event:
                result["event_seq"] = event.get("seq") or event.get("event_seq")
        return result

    def _finalize_batch(self, payload: dict[str, Any], consumer: str, cache_hit: bool) -> dict[str, Any]:
        rows = list(payload.get("rows") or [])
        with self._cache_lock:
            if cache_hit:
                self._stats["batch_cache_hits"] += 1
            for row in rows:
                symbol = str(row.get("symbol") or row.get("instId") or "").upper()
                if not symbol:
                    continue
                usage = self._consumer_usage.setdefault(symbol, {
                    "consumers": set(),
                    "requests": 0,
                    "batch_requests": 0,
                    "snapshot_cache_hits": 0,
                    "quote_cache_hits": 0,
                })
                usage["consumers"].add(consumer)
                usage["batch_requests"] = int(usage.get("batch_requests") or 0) + 1
                usage["last_consumer"] = consumer
                usage["updated_at"] = self.now_ms()
            context = {
                **dict(payload.get("context") or {}),
                "consumer": consumer,
                "cache_hit": cache_hit,
                "shared": cache_hit or bool((payload.get("context") or {}).get("reused_quotes")),
            }
        return {**payload, "context": context}

    def _finalize_snapshot(
        self,
        payload: dict[str, Any],
        symbol: str,
        consumer: str,
        snapshot_cache_hit: bool,
        quote_cache_hit: bool | None,
        emit_event: bool,
    ) -> dict[str, Any]:
        clean_consumer = str(consumer or "unspecified").strip().lower()[:40] or "unspecified"
        with self._cache_lock:
            self._stats["snapshot_requests"] += 1
            if snapshot_cache_hit:
                self._stats["snapshot_cache_hits"] += 1
            usage = self._consumer_usage.setdefault(symbol, {
                "consumers": set(),
                "requests": 0,
                "batch_requests": 0,
                "snapshot_cache_hits": 0,
                "quote_cache_hits": 0,
            })
            usage["consumers"].add(clean_consumer)
            usage["requests"] += 1
            usage["snapshot_cache_hits"] += int(snapshot_cache_hit)
            usage["quote_cache_hits"] += int(bool(quote_cache_hit))
            usage["last_consumer"] = clean_consumer
            usage["updated_at"] = self.now_ms()
            context = {
                **dict(payload.get("context") or {}),
                "consumer": clean_consumer,
                "consumers": sorted(usage["consumers"]),
                "request_count": usage["requests"],
                "reuse_count": usage["snapshot_cache_hits"],
                "snapshot_cache_hit": snapshot_cache_hit,
                "quote_cache_hit": bool(quote_cache_hit) if quote_cache_hit is not None else None,
                "shared": len(usage["consumers"]) > 1 or usage["snapshot_cache_hits"] > 0,
            }
        result = {**payload, "context": context}
        return self._with_snapshot_event(result, emit_event)

    def _shared_quote(
        self,
        symbol: str,
        asset_type: str,
        force: bool = False,
        fast: bool = False,
    ) -> tuple[dict[str, Any], bool, int]:
        cache_key = f"{asset_type}:{symbol}"
        ttl_ms = 3500
        with self._cache_lock:
            self._stats["quote_requests"] += 1
            cached = self.quote_cache.get(cache_key)
            age_ms = self.now_ms() - int(cached.get("time") or 0) if cached else 0
            quote_lock = self._quote_locks.setdefault(cache_key, threading.Lock())
            force_generation = int(self._quote_force_generations.get(cache_key) or 0)
            if cached and not force and age_ms <= ttl_ms:
                self._stats["quote_cache_hits"] += 1
                return dict(cached["payload"]), True, max(age_ms, 0)
        with quote_lock:
            with self._cache_lock:
                forced_result = self._quote_force_results.get(cache_key) if force else None
                if (
                    forced_result
                    and int(forced_result.get("generation") or 0) > force_generation
                    and isinstance(forced_result.get("payload"), dict)
                ):
                    return dict(forced_result["payload"]), False, 0
                cached = self.quote_cache.get(cache_key)
                age_ms = self.now_ms() - int(cached.get("time") or 0) if cached else 0
                if cached and not force and age_ms <= ttl_ms:
                    self._stats["quote_cache_hits"] += 1
                    return dict(cached["payload"]), True, max(age_ms, 0)
                previous_quote = dict(cached["payload"]) if cached and _usable_quote(cached.get("payload")) else None
                local_fast_read = bool(asset_type == "stock" and fast and self.read_fast_stock_quote)
                if local_fast_read:
                    self._stats["local_quote_reads"] += 1
                else:
                    self._stats["upstream_quote_calls"] += 1
            try:
                quote = self._quote(symbol, asset_type, force=force, fast=fast)
            except Exception as exc:
                if not (force and previous_quote):
                    raise
                quote = _last_good_after_refresh_failure(previous_quote, error=str(exc))
            if force and previous_quote and _quote_refresh_failed(quote):
                quote = _last_good_after_refresh_failure(previous_quote, quote)
            previous_timestamp = _timestamp_ms((previous_quote or {}).get("ts"))
            refreshed_timestamp = _timestamp_ms((quote or {}).get("ts"))
            if previous_quote and previous_timestamp and refreshed_timestamp and refreshed_timestamp < previous_timestamp:
                quote = {
                    **_last_good_after_refresh_failure(previous_quote, error="quote_timestamp_regression"),
                    "cache_regression": True,
                }
            with self._cache_lock:
                self.quote_cache[cache_key] = {"time": self.now_ms(), "payload": dict(quote)}
                if force:
                    refresh_generation = int(self._quote_force_generations.get(cache_key) or 0) + 1
                    self._quote_force_generations[cache_key] = refresh_generation
                    self._quote_force_results[cache_key] = {
                        "generation": refresh_generation,
                        "payload": dict(quote),
                    }
            return quote, False, 0

    def _publish_snapshot_event(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.publish_event:
            return None
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
        candles = payload.get("candles") if isinstance(payload.get("candles"), dict) else {}
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        return self.publish_event("market_snapshot", {
            "snapshot_id": context.get("snapshot_id"),
            "symbol": payload["symbol"],
            "asset_type": payload["asset_type"],
            "bar": payload.get("bar"),
            "session": payload.get("session"),
            "last": payload["quote"].get("last"),
            "source": source.get("primary") or source.get("adapter") or "market_data_service",
            "source_detail": source,
            "quality": payload["data_quality"],
            "cached": payload.get("cached", False),
            "candle_count": candles.get("count"),
            "candle_latest_ts": candles.get("latest_ts"),
            "updated_at": payload.get("updated_at"),
        })

    def _quote(
        self,
        symbol: str,
        asset_type: str,
        force: bool = False,
        fast: bool = False,
    ) -> dict[str, Any]:
        if asset_type == "stock":
            if fast and not force and self.read_fast_stock_quote:
                return self.read_fast_stock_quote(symbol)
            return self.read_stock_quote(symbol, max_age_ms=0 if force else 4500, use_futu=True)
        row = self.okx_first("/api/v5/market/ticker", {"instId": symbol})
        return self._normalize_crypto_quote(symbol, row)

    def _normalize_crypto_quote(self, symbol: str, row: dict[str, Any]) -> dict[str, Any]:
        last = self.pct(row.get("last", "0"))
        last_decimal = _positive_decimal_text(row.get("last"))
        bid_decimal = _positive_decimal_text(row.get("bidPx"))
        ask_decimal = _positive_decimal_text(row.get("askPx"))
        ask_size_decimal = _positive_decimal_text(row.get("askSz"))
        open24h = self.pct(row.get("open24h", "0"))
        change = (last / open24h - 1) * 100 if last > 0 and open24h > 0 else 0.0
        return {
            "symbol": symbol,
            "instId": symbol,
            "type": "crypto",
            "category": "swap" if symbol.endswith("-SWAP") else "spot",
            "source": "okx",
            "origin_source": "okx",
            "exchange": "OKX",
            "status": "ONLINE" if last > 0 else "OFFLINE",
            "last": last,
            "last_decimal": last_decimal,
            "bid_decimal": bid_decimal,
            "ask_decimal": ask_decimal,
            "ask_size_decimal": ask_size_decimal,
            "open24h": open24h,
            "high24h": self.pct(row.get("high24h", "0")),
            "low24h": self.pct(row.get("low24h", "0")),
            "vol24h": self.pct(row.get("vol24h", "0")),
            "volCcy24h": self.pct(row.get("volCcy24h", "0")),
            "bidPx": self.pct(row.get("bidPx", "0")),
            "askPx": self.pct(row.get("askPx", "0")),
            "change24h_pct": round(change, 2),
            "ts": int(self.pct(row.get("ts", self.now_ms()), self.now_ms())),
        }

    def _data_sources(self, symbol: str, bar: str, session: str, asset_type: str) -> dict[str, Any]:
        if asset_type != "stock":
            return {
                "ok": True,
                "symbol": symbol,
                "order": ["okx_realtime", "local_market_cache", "fallback_history"],
                "summary": "OKX公共行情 / 本地历史缓存 / 离线回退",
            }
        try:
            return self.stock_data_sources_snapshot(symbol, bar, session)
        except Exception as exc:
            return {"ok": False, "symbol": symbol, "summary": f"股票数据源状态读取失败：{exc}"}

    def _adapter_id(self, asset_type: str, quote_source: str, candle_source: str) -> str:
        source_text = f"{quote_source} {candle_source}".lower()
        if asset_type == "crypto":
            if "okx" in source_text:
                return "okx_adapter"
            return "csv_adapter"
        if "futu" in source_text:
            return "futu_adapter"
        return "stock_cache_adapter"

    def _build_snapshot(
        self,
        symbol: str,
        asset_type: str,
        bar: str,
        session: str,
        quote: dict[str, Any],
        candles: dict[str, Any],
        data_sources: dict[str, Any],
    ) -> dict[str, Any]:
        candle_rows = candles.get("rows") or []
        quote_source = str(quote.get("source") or quote.get("origin_source") or ("okx" if asset_type == "crypto" else "stock"))
        candle_source = str(candles.get("source") or "")
        quote_age_ms = self.now_ms() - int(quote.get("ts") or self.now_ms()) if quote.get("ts") else None
        candle_age_ms = candles.get("data_age_ms")
        quote_quality = quote.get("quote_quality") if isinstance(quote.get("quote_quality"), dict) else {}
        candle_quality = candles.get("candle_quality") if isinstance(candles.get("candle_quality"), dict) else {}
        market_session = quote.get("market_session") if isinstance(quote.get("market_session"), dict) else {}
        raw_warnings = [
            text for text in [
                quote.get("warning"),
                *list(quote_quality.get("warnings") or []),
                *list(quote_quality.get("quarantine_reasons") or []),
                candles.get("warning"),
                candle_quality.get("warning"),
                (data_sources.get("cache") or {}).get("persistent_warning") if isinstance(data_sources.get("cache"), dict) else "",
                data_sources.get("summary") if not data_sources.get("ok", True) else "",
            ]
            if text
        ]
        warnings = list(dict.fromkeys(str(item) for item in raw_warnings if item))
        fallback = (
            _hazard_enabled(candles.get("fallback"))
            or _hazard_enabled(quote_quality.get("fallback"))
            or quote_source in {"offline-seed", "stock_sqlite_cache"}
        )
        requested_session = session if asset_type == "stock" else "all"
        active_phase = str(market_session.get("phase") or "unknown")
        session_status = str(market_session.get("status") or "UNKNOWN")
        if asset_type != "stock":
            session_relation = "LIVE_SESSION"
        elif session_status in {"STALE", "UNAVAILABLE", "HALTED"}:
            session_relation = session_status
        elif session_status == "DELAYED_SOURCE":
            session_relation = "DELAYED_SOURCE"
        elif requested_session in {"all", active_phase}:
            session_relation = session_status
        elif requested_session == "regular" and active_phase in {"pre", "post", "overnight", "break", "closed"}:
            session_relation = "LAST_SESSION"
        else:
            session_relation = "HISTORICAL_SESSION"
        realtime = _permission_enabled(candles.get("realtime")) and not fallback and str(quote.get("status", "")).upper() != "OFFLINE"
        if asset_type == "stock":
            realtime = bool(realtime and quote_source.lower() == "futu" and session_relation == "LIVE_SESSION")
        session_ready = asset_type == "stock" and _permission_enabled(market_session.get("analysis_ready")) and session_relation in {
            "LIVE_SESSION", "LAST_SESSION", "SESSION_BREAK", "HISTORICAL_SESSION"
        }
        last = self.pct(quote.get("last", 0))
        status = "READY"
        if last <= 0 and not candle_rows:
            status = "OFFLINE"
        elif fallback or warnings or (not realtime and not session_ready):
            status = "STALE" if last > 0 or candle_rows else "OFFLINE"
        degradation = " / ".join(str(item) for item in warnings if item) or ("实时数据可用" if realtime else "非实时或缓存数据")
        return {
            "ok": status != "OFFLINE",
            "symbol": symbol,
            "asset_type": asset_type,
            "bar": candles.get("bar", bar),
            "session": session if asset_type == "stock" else "all",
            "session_label": data_sources.get("session_label", "") if asset_type == "stock" else "",
            "quote": {
                "source": quote_source,
                "origin_source": quote.get("origin_source", ""),
                "name": quote.get("name", ""),
                "exchange": quote.get("exchange", ""),
                "market": quote.get("market", ""),
                "sector": quote.get("sector", ""),
                "last": last,
                "last_decimal": quote.get("last_decimal") or _positive_decimal_text(quote.get("last")),
                "open24h": self.pct(quote.get("open24h", 0)),
                "high24h": self.pct(quote.get("high24h", 0)),
                "low24h": self.pct(quote.get("low24h", 0)),
                "vol24h": self.pct(quote.get("vol24h", 0)),
                "volCcy24h": self.pct(quote.get("volCcy24h", 0)),
                "bidPx": self.pct(quote.get("bidPx", 0)),
                "askPx": self.pct(quote.get("askPx", 0)),
                "bid_decimal": quote.get("bid_decimal", ""),
                "ask_decimal": quote.get("ask_decimal", ""),
                "ask_size_decimal": quote.get("ask_size_decimal", ""),
                "change24h_pct": round(float(quote.get("change24h_pct") or 0), 2),
                "prevClose": self.pct(quote.get("prevClose", 0)),
                "change_basis": quote.get("change_basis", ""),
                "quote_quality": quote_quality,
                "session_prices": quote.get("session_prices") if isinstance(quote.get("session_prices"), dict) else {},
                "active_session": quote.get("active_session", ""),
                "active_session_price": self.pct(quote.get("active_session_price", 0)),
                "active_session_change_pct": quote.get("active_session_change_pct"),
                "ts": quote.get("ts"),
                "date": quote.get("date", ""),
                "time": quote.get("time", ""),
                "data_age_ms": quote.get("data_age_ms"),
                "status": quote.get("status", "ONLINE" if last > 0 else "OFFLINE"),
                "refresh_failed": _hazard_enabled(quote.get("refresh_failed")),
                "cache_regression": _hazard_enabled(quote.get("cache_regression")),
                "warning": quote.get("warning", ""),
            },
            "market_session": {
                **market_session,
                "requested_session": requested_session,
                "session_relation": session_relation,
            } if asset_type == "stock" else {},
            "candles": {
                "ok": _permission_enabled(candles.get("ok")),
                "bar": candles.get("bar", bar),
                "count": len(candle_rows),
                "rows": candle_rows,
                "source": candle_source,
                "latest_ts": candles.get("latest_ts", 0),
                "latest_at": candles.get("latest_at", ""),
                "data_age_ms": candle_age_ms,
                "cache_age_ms": candles.get("cache_age_ms"),
                "realtime": _permission_enabled(candles.get("realtime")),
                "in_progress": _permission_enabled(candles.get("in_progress")),
                "fallback": _hazard_enabled(candles.get("fallback")),
                "warning": candles.get("warning", ""),
                "candle_quality": candle_quality,
                "data_revision_evidence": dict(candles.get("data_revision_evidence") or {}),
            },
            "source": {
                "primary": candle_source or quote_source,
                "quote": quote_source,
                "candles": candle_source,
                "origin": quote.get("origin_source", ""),
                "adapter": self._adapter_id(asset_type, quote_source, candle_source),
                "realtime": realtime,
                "cached": _hazard_enabled(candles.get("cached")) or fallback,
                "quote_age_ms": quote_age_ms,
                "data_age_ms": candle_age_ms,
                "degradation_reason": degradation,
                "session_status": session_status if asset_type == "stock" else "",
                "session_relation": session_relation if asset_type == "stock" else "",
            },
            "data_quality": {
                "status": status,
                "realtime": realtime,
                "fallback": fallback,
                "warnings": warnings,
                "quote": quote_quality,
                "candle": candle_quality,
                "quarantined": _hazard_enabled(quote_quality.get("quarantined")) or candle_quality.get("status") == "REVIEW",
                "session_status": session_status if asset_type == "stock" else "",
                "session_relation": session_relation if asset_type == "stock" else "",
                "market_open": _permission_enabled(market_session.get("is_open")) if asset_type == "stock" else True,
                "active_session": market_session.get("active_session", "") if asset_type == "stock" else "",
                "active_price": self.pct(market_session.get("active_price", 0)) if asset_type == "stock" else last,
                "provider_confirmed_session": _permission_enabled(market_session.get("provider_confirmed")) if asset_type == "stock" else True,
            },
            "data_sources": data_sources,
            "cached": False,
            "snapshot_cache_age_ms": 0,
            "updated_at": self.now_ms(),
        }
