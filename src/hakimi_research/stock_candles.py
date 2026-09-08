from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from hakimi_research.candle_contract import candle_is_complete
from hakimi_research.stock_metadata import normalize_stock_interval, stock_meta, stock_timezone
from hakimi_research.terminal_utils import now_ms


STOCK_CANDLE_STRUCTURE_CONTRACT_VERSION = "stock-candle-structure-v1"
STOCK_SESSIONS = {"all", "pre", "regular", "post", "overnight"}


def _number(value: Any, default: float = 0.0) -> float:
    if type(value) in {int, float}:
        parsed = float(value)
    elif type(value) is str:
        try:
            parsed = float(value)
        except ValueError:
            return default
    else:
        return default
    return parsed if math.isfinite(parsed) else default


def _integer(value: Any, default: int = 0) -> int:
    parsed = _number(value, float("nan"))
    return int(parsed) if math.isfinite(parsed) else default


def _text(value: Any, default: str = "") -> str:
    return value if type(value) is str else default


def _native_rows(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        return []
    return [dict(row) for row in value if type(row) is dict]


def _reference_ms(at_ms: Any = None) -> int:
    return _integer(now_ms() if at_ms is None else at_ms)


def _local_now(symbol: str, at_ms: Any = None) -> datetime:
    reference_ms = max(_reference_ms(at_ms), 0)
    return datetime.fromtimestamp(reference_ms / 1000, stock_timezone(symbol))


def clean_stock_session(session: str) -> str:
    return session if type(session) is str and session in STOCK_SESSIONS else "all"


def filter_stock_rows_by_session(rows: list[dict[str, Any]], session: str) -> list[dict[str, Any]]:
    native_rows = _native_rows(rows)
    if type(session) is not str or session not in {"pre", "regular", "post", "overnight"}:
        return native_rows
    return [row for row in native_rows if _text(row.get("session")) == session]


def aggregate_stock_rows(rows: list[dict[str, Any]], bucket_ms: int) -> list[dict[str, Any]]:
    native_rows = _native_rows(rows)
    bucket_size = _integer(bucket_ms)
    if not native_rows or bucket_size <= 0:
        return native_rows
    buckets: dict[int, dict[str, Any]] = {}
    for row in native_rows:
        ts = _integer(row.get("ts"))
        close = _number(row.get("close"))
        if ts <= 0 or close <= 0:
            continue
        open_price = _number(row.get("open"), close)
        high = _number(row.get("high"), close)
        low = _number(row.get("low"), close)
        volume = _number(row.get("volume"))
        if open_price <= 0:
            open_price = close
        if high <= 0:
            high = close
        if low <= 0:
            low = close
        if high < max(open_price, close, low) or low > min(open_price, close, high) or volume < 0:
            continue
        key = ts // bucket_size * bucket_size
        existing = buckets.get(key)
        if not existing:
            complete = candle_is_complete(row, default_if_missing=False)
            buckets[key] = {
                **row,
                "ts": key,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "complete": complete,
                "provisional": not complete,
            }
            continue
        existing["high"] = max(_number(existing.get("high")), high)
        existing_low = _number(existing.get("low"), low)
        existing["low"] = min(existing_low, low)
        existing["close"] = close
        existing["volume"] = _number(existing.get("volume")) + volume
        existing["complete"] = (
            candle_is_complete(existing, default_if_missing=False)
            and candle_is_complete(row, default_if_missing=False)
        )
        existing["provisional"] = not existing["complete"]
    return [buckets[key] for key in sorted(buckets)]


def stock_cache_interval(interval: str) -> str:
    text = _text(interval).lower()
    if text == "4h":
        return "4h"
    normalized_interval, _ = normalize_stock_interval(text)
    return normalized_interval


def stock_candle_complete_at(
    symbol: str,
    interval: str,
    ts_ms: int,
    trading_date: str = "",
    *,
    at_ms: int | None = None,
) -> bool:
    reference_ms = _reference_ms(at_ms)
    if reference_ms <= 0:
        return False
    normalized_interval = stock_cache_interval(interval)
    timezone = stock_timezone(_text(symbol, "AAPL") or "AAPL")
    local_now = datetime.fromtimestamp(reference_ms / 1000, timezone)
    if normalized_interval in {"1d", "1dutc"}:
        date_text = _text(trading_date)[:10]
        timestamp_ms = _integer(ts_ms)
        if not date_text and timestamp_ms > 0:
            date_text = datetime.fromtimestamp(timestamp_ms / 1000, timezone).date().isoformat()
        try:
            row_date = datetime.fromisoformat(date_text).date()
        except (TypeError, ValueError):
            return False
        if row_date < local_now.date():
            return True
        if row_date > local_now.date() or local_now.weekday() >= 5:
            return False
        return local_now.hour * 60 + local_now.minute >= 16 * 60 + 20

    bucket_size = {
        "1m": 60_000,
        "5m": 5 * 60_000,
        "15m": 15 * 60_000,
        "30m": 30 * 60_000,
        "60m": 60 * 60_000,
        "4h": 4 * 60 * 60_000,
    }.get(normalized_interval, 0)
    start_ms = _integer(ts_ms)
    return bucket_size > 0 and start_ms > 0 and start_ms + bucket_size <= reference_ms


def stock_cache_fresh_ms(interval: str) -> int:
    normalized_interval = stock_cache_interval(interval)
    if normalized_interval in {"1d", "1dutc"}:
        return 12 * 60 * 60 * 1000
    if normalized_interval == "1m":
        return 45 * 1000
    if normalized_interval in {"5m", "15m", "30m"}:
        return 2 * 60 * 1000
    return 5 * 60 * 1000


def stock_candle_cache_key(symbol: str, interval: str, session: str) -> str:
    meta = stock_meta(_text(symbol, "AAPL"))
    normalized_interval = stock_cache_interval(interval)
    return f"{_text(meta.get('symbol'), 'AAPL')}|{normalized_interval}|{clean_stock_session(session)}"


def latest_stock_candle_ts(rows: list[dict[str, Any]]) -> int:
    values = [
        _integer(row.get("ts", row.get("ts_ms")))
        for row in _native_rows(rows)
    ]
    return max(values) if values else 0


def stock_candle_stale_warning(
    rows: list[dict[str, Any]],
    interval: str,
    symbol: str = "",
    *,
    at_ms: int | None = None,
) -> str:
    latest_ts = latest_stock_candle_ts(rows)
    if latest_ts <= 0:
        return ""
    normalized_interval = stock_cache_interval(interval)
    max_age_ms = 14 * 24 * 60 * 60 * 1000 if normalized_interval in {"1d", "1dutc"} else 5 * 24 * 60 * 60 * 1000
    age_ms = _reference_ms(at_ms) - latest_ts
    if age_ms <= max_age_ms:
        return ""
    latest = datetime.fromtimestamp(
        latest_ts / 1000,
        stock_timezone(_text(symbol, "AAPL") or "AAPL"),
    ).strftime("%Y-%m-%d %H:%M")
    return f"stale stock candles latest {latest}"


def stock_current_session_date(symbol: str, *, at_ms: int | None = None) -> str:
    now_local = _local_now(_text(symbol, "AAPL") or "AAPL", at_ms)
    return now_local.strftime("%Y-%m-%d") if now_local.weekday() < 5 else ""


def stock_minutes_now(symbol: str, *, at_ms: int | None = None) -> int:
    now_local = _local_now(_text(symbol, "AAPL") or "AAPL", at_ms)
    return now_local.hour * 60 + now_local.minute


def stock_daily_should_have_intraday(symbol: str, *, at_ms: int | None = None) -> bool:
    if not stock_current_session_date(symbol, at_ms=at_ms):
        return False
    minute = stock_minutes_now(symbol, at_ms=at_ms)
    return minute >= 9 * 60 + 35


def stock_payload_latest_date(payload: dict[str, Any] | None, symbol: str) -> str:
    if type(payload) is not dict:
        return ""
    latest_ts = latest_stock_candle_ts(payload.get("rows"))
    if latest_ts <= 0:
        return ""
    return datetime.fromtimestamp(
        latest_ts / 1000,
        stock_timezone(_text(symbol, "AAPL") or "AAPL"),
    ).strftime("%Y-%m-%d")


def stock_payload_needs_session_refresh(
    payload: dict[str, Any] | None,
    interval: str,
    symbol: str,
    *,
    at_ms: int | None = None,
) -> bool:
    if type(payload) is not dict:
        return False
    normalized_interval = stock_cache_interval(interval)
    if normalized_interval not in {"1d", "1dutc"}:
        return False
    expected = stock_current_session_date(symbol, at_ms=at_ms)
    latest = stock_payload_latest_date(payload, symbol)
    return bool(expected and latest and latest < expected and stock_daily_should_have_intraday(symbol, at_ms=at_ms))


def stock_payload_has_due_incomplete_daily(
    payload: dict[str, Any] | None,
    interval: str,
    symbol: str,
    *,
    at_ms: int | None = None,
) -> bool:
    if type(payload) is not dict or stock_cache_interval(interval) not in {"1d", "1dutc"}:
        return False
    incomplete = [
        row
        for row in _native_rows(payload.get("rows"))
        if not candle_is_complete(row, default_if_missing=False)
    ]
    if not incomplete:
        return False
    reference_ms = _reference_ms(at_ms)
    if reference_ms <= 0:
        return False
    clean_symbol = _text(symbol, "AAPL") or "AAPL"
    timezone = stock_timezone(clean_symbol)
    local_now = datetime.fromtimestamp(reference_ms / 1000, timezone)
    current_date = local_now.date().isoformat()
    current_minute = local_now.hour * 60 + local_now.minute
    for row in incomplete:
        row_date = _text(row.get("date"))[:10]
        if not row_date:
            timestamp_ms = _integer(row.get("ts", row.get("ts_ms")))
            if timestamp_ms > 0:
                row_date = datetime.fromtimestamp(timestamp_ms / 1000, timezone).date().isoformat()
        if row_date and row_date < current_date:
            return True
        if row_date == current_date and current_minute >= 16 * 60 + 20:
            return True
    return False


def candle_date_from_ts(ts_ms: int) -> str:
    timestamp_ms = _integer(ts_ms)
    if timestamp_ms <= 0:
        return ""
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=ZoneInfo("UTC")).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return ""


def normalize_stock_cache_candle(row: Any, symbol: str) -> dict[str, Any] | None:
    if type(row) is not dict:
        return None
    close = _number(row.get("close"))
    timestamp_ms = _integer(row.get("ts", row.get("ts_ms", row.get("time"))))
    if close <= 0 or timestamp_ms <= 0:
        return None
    open_price = _number(row.get("open"), close)
    high = _number(row.get("high"), close)
    low = _number(row.get("low"), close)
    volume = _number(row.get("volume", row.get("vol")))
    if open_price <= 0:
        open_price = close
    if high <= 0:
        high = close
    if low <= 0:
        low = close
    if high < max(open_price, close, low) or low > min(open_price, close, high) or volume < 0:
        return None
    date_text = _text(row.get("date", row.get("trading_date")))[:10]
    if date_text:
        try:
            datetime.fromisoformat(date_text)
        except ValueError:
            return None
    if not date_text:
        date_text = datetime.fromtimestamp(
            timestamp_ms / 1000,
            stock_timezone(_text(symbol, "AAPL") or "AAPL"),
        ).strftime("%Y-%m-%d")
    return {
        "ts": timestamp_ms,
        "date": date_text or candle_date_from_ts(timestamp_ms),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "session": _text(row.get("session")),
        "complete": candle_is_complete(row, default_if_missing=False),
    }


def with_stock_freshness(
    payload: dict[str, Any],
    interval: str,
    symbol: str,
    *,
    at_ms: int | None = None,
) -> dict[str, Any]:
    normalized = dict(payload) if type(payload) is dict else {}
    rows = _native_rows(normalized.get("rows"))
    normalized["rows"] = rows
    latest_ts = latest_stock_candle_ts(rows)
    if latest_ts <= 0:
        normalized.update({
            "latest_ts": 0,
            "latest_at": "",
            "data_age_ms": None,
            "realtime": False,
            "in_progress": False,
        })
        return normalized
    warning = _text(normalized.get("warning"))
    source = _text(normalized.get("source"))
    age_ms = max(0, _reference_ms(at_ms) - latest_ts)
    normalized_interval = stock_cache_interval(interval)
    live_age_limit_ms = 3 * 24 * 60 * 60 * 1000 if normalized_interval in {"1d", "1dutc"} else 30 * 60 * 1000
    latest_row = max(rows, key=lambda row: _integer(row.get("ts", row.get("ts_ms"))))
    daily_in_progress = not candle_is_complete(latest_row, default_if_missing=False)
    realtime = bool(
        source == "futu"
        and not warning
        and age_ms <= live_age_limit_ms
        and (normalized_interval not in {"1d", "1dutc"} or daily_in_progress)
    )
    normalized.update({
        "latest_ts": latest_ts,
        "latest_at": datetime.fromtimestamp(
            latest_ts / 1000,
            stock_timezone(_text(symbol, "AAPL") or "AAPL"),
        ).strftime("%Y-%m-%d %H:%M"),
        "data_age_ms": age_ms,
        "realtime": realtime,
        "in_progress": daily_in_progress if normalized_interval in {"1d", "1dutc"} else realtime,
    })
    return normalized


def stock_payload_source(payload: dict[str, Any] | None) -> str:
    if type(payload) is not dict:
        return ""
    origin = payload.get("origin_source")
    source = origin if type(origin) is str and origin else payload.get("source")
    return _text(source).lower()


def stock_payload_is_futu(payload: dict[str, Any] | None) -> bool:
    return stock_payload_source(payload) == "futu"


__all__ = [
    "STOCK_CANDLE_STRUCTURE_CONTRACT_VERSION",
    "STOCK_SESSIONS",
    "aggregate_stock_rows",
    "candle_is_complete",
    "candle_date_from_ts",
    "clean_stock_session",
    "filter_stock_rows_by_session",
    "latest_stock_candle_ts",
    "normalize_stock_cache_candle",
    "normalize_stock_interval",
    "now_ms",
    "stock_cache_fresh_ms",
    "stock_cache_interval",
    "stock_candle_cache_key",
    "stock_candle_complete_at",
    "stock_candle_stale_warning",
    "stock_current_session_date",
    "stock_daily_should_have_intraday",
    "stock_meta",
    "stock_minutes_now",
    "stock_payload_has_due_incomplete_daily",
    "stock_payload_is_futu",
    "stock_payload_latest_date",
    "stock_payload_needs_session_refresh",
    "stock_payload_source",
    "stock_timezone",
    "with_stock_freshness",
]
