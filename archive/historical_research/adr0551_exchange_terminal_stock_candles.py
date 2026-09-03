from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from hakimi_research.candle_contract import candle_is_complete

try:
    from hakimi_research.stock_metadata import normalize_stock_interval, stock_meta, stock_timezone
    from utils import now_ms
except ModuleNotFoundError:
    from hakimi_research.stock_metadata import normalize_stock_interval, stock_meta, stock_timezone
    from hakimi_research.terminal_utils import now_ms


STOCK_SESSIONS = {"all", "pre", "regular", "post", "overnight"}


def clean_stock_session(session: str) -> str:
    return session if session in STOCK_SESSIONS else "all"


def filter_stock_rows_by_session(rows: list[dict[str, Any]], session: str) -> list[dict[str, Any]]:
    if session not in {"pre", "regular", "post", "overnight"}:
        return rows
    return [row for row in rows if row.get("session") == session]


def aggregate_stock_rows(rows: list[dict[str, Any]], bucket_ms: int) -> list[dict[str, Any]]:
    if not rows or bucket_ms <= 0:
        return rows
    buckets: dict[int, dict[str, Any]] = {}
    for row in rows:
        ts = int(row.get("ts") or 0)
        key = ts // bucket_ms * bucket_ms
        existing = buckets.get(key)
        if not existing:
            complete = candle_is_complete(row, default_if_missing=False)
            buckets[key] = {
                **row,
                "ts": key,
                "open": float(row.get("open") or 0),
                "high": float(row.get("high") or 0),
                "low": float(row.get("low") or 0),
                "close": float(row.get("close") or 0),
                "volume": float(row.get("volume") or 0),
                "complete": complete,
                "provisional": not complete,
            }
            continue
        existing["high"] = max(float(existing.get("high") or 0), float(row.get("high") or 0))
        low = float(row.get("low") or 0)
        existing["low"] = min(float(existing.get("low") or low), low) if low > 0 else existing["low"]
        existing["close"] = float(row.get("close") or existing.get("close") or 0)
        existing["volume"] = float(existing.get("volume") or 0) + float(row.get("volume") or 0)
        existing["complete"] = (
            candle_is_complete(existing, default_if_missing=False)
            and candle_is_complete(row, default_if_missing=False)
        )
        existing["provisional"] = not existing["complete"]
    return [buckets[key] for key in sorted(buckets)]


def stock_cache_interval(interval: str) -> str:
    if (interval or "").lower() == "4h":
        return "4h"
    normalized_interval, _ = normalize_stock_interval(interval)
    return normalized_interval


def stock_candle_complete_at(
    symbol: str,
    interval: str,
    ts_ms: int,
    trading_date: str = "",
    *,
    at_ms: int | None = None,
) -> bool:
    reference_ms = int(at_ms if at_ms is not None else now_ms())
    if reference_ms <= 0:
        return False
    normalized_interval = stock_cache_interval(interval)
    timezone = stock_timezone(symbol or "AAPL")
    local_now = datetime.fromtimestamp(reference_ms / 1000, timezone)
    if normalized_interval in {"1d", "1dutc"}:
        date_text = str(trading_date or "")[:10]
        if not date_text and int(ts_ms or 0) > 0:
            date_text = datetime.fromtimestamp(int(ts_ms) / 1000, timezone).date().isoformat()
        try:
            row_date = datetime.fromisoformat(date_text).date()
        except (TypeError, ValueError):
            return False
        if row_date < local_now.date():
            return True
        if row_date > local_now.date() or local_now.weekday() >= 5:
            return False
        return local_now.hour * 60 + local_now.minute >= 16 * 60 + 20

    bucket_ms = {
        "1m": 60_000,
        "5m": 5 * 60_000,
        "15m": 15 * 60_000,
        "30m": 30 * 60_000,
        "60m": 60 * 60_000,
        "4h": 4 * 60 * 60_000,
    }.get(normalized_interval, 0)
    start_ms = int(ts_ms or 0)
    return bucket_ms > 0 and start_ms > 0 and start_ms + bucket_ms <= reference_ms


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
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    return f"{meta['symbol']}|{normalized_interval}|{clean_stock_session(session)}"


def stock_candle_stale_warning(rows: list[dict[str, Any]], interval: str, symbol: str = "") -> str:
    if not rows:
        return ""
    latest_ts = max(int(row.get("ts") or row.get("ts_ms") or 0) for row in rows)
    if latest_ts <= 0:
        return ""
    normalized_interval = stock_cache_interval(interval)
    max_age_ms = 14 * 24 * 60 * 60 * 1000 if normalized_interval in {"1d", "1dutc"} else 5 * 24 * 60 * 60 * 1000
    age_ms = now_ms() - latest_ts
    if age_ms <= max_age_ms:
        return ""
    latest = datetime.fromtimestamp(latest_ts / 1000, stock_timezone(symbol or "AAPL")).strftime("%Y-%m-%d %H:%M")
    return f"stale stock candles latest {latest}"


def latest_stock_candle_ts(rows: list[dict[str, Any]]) -> int:
    values = [int(row.get("ts") or row.get("ts_ms") or 0) for row in rows or []]
    return max(values) if values else 0


def stock_current_session_date(symbol: str) -> str:
    now_local = datetime.now(stock_timezone(symbol or "AAPL"))
    return now_local.strftime("%Y-%m-%d") if now_local.weekday() < 5 else ""


def stock_minutes_now(symbol: str) -> int:
    now_local = datetime.now(stock_timezone(symbol or "AAPL"))
    return now_local.hour * 60 + now_local.minute


def stock_daily_should_have_intraday(symbol: str) -> bool:
    if not stock_current_session_date(symbol):
        return False
    market = str(stock_meta(symbol).get("market") or "US").upper()
    minute = stock_minutes_now(symbol)
    if market in {"HK", "CN", "SH", "SZ"}:
        return minute >= 9 * 60 + 35
    return minute >= 9 * 60 + 35


def stock_payload_latest_date(payload: dict[str, Any] | None, symbol: str) -> str:
    rows = list((payload or {}).get("rows") or [])
    latest_ts = latest_stock_candle_ts(rows)
    if latest_ts <= 0:
        return ""
    return datetime.fromtimestamp(latest_ts / 1000, stock_timezone(symbol or "AAPL")).strftime("%Y-%m-%d")


def stock_payload_needs_session_refresh(payload: dict[str, Any] | None, interval: str, symbol: str) -> bool:
    if not payload:
        return False
    normalized_interval = stock_cache_interval(interval)
    if normalized_interval not in {"1d", "1dutc"}:
        return False
    expected = stock_current_session_date(symbol)
    latest = stock_payload_latest_date(payload, symbol)
    return bool(expected and latest and latest < expected and stock_daily_should_have_intraday(symbol))


def stock_payload_has_due_incomplete_daily(
    payload: dict[str, Any] | None,
    interval: str,
    symbol: str,
    *,
    at_ms: int | None = None,
) -> bool:
    if stock_cache_interval(interval) not in {"1d", "1dutc"}:
        return False
    incomplete = [
        row for row in list((payload or {}).get("rows") or [])
        if not candle_is_complete(row, default_if_missing=False)
    ]
    if not incomplete:
        return False
    reference_ms = int(at_ms if at_ms is not None else now_ms())
    local_now = datetime.fromtimestamp(reference_ms / 1000, stock_timezone(symbol or "AAPL"))
    market = str(stock_meta(symbol or "AAPL").get("market") or "US").upper()
    close_buffer_minute = 16 * 60 + 20 if market in {"US", "HK", "CN", "SH", "SZ"} else 16 * 60 + 20
    current_date = local_now.date().isoformat()
    current_minute = local_now.hour * 60 + local_now.minute
    for row in incomplete:
        row_date = str(row.get("date") or "")[:10]
        if not row_date:
            ts_ms = int(row.get("ts") or row.get("ts_ms") or 0)
            if ts_ms > 0:
                row_date = datetime.fromtimestamp(ts_ms / 1000, stock_timezone(symbol or "AAPL")).date().isoformat()
        if row_date and row_date < current_date:
            return True
        if row_date == current_date and current_minute >= close_buffer_minute:
            return True
    return False


def candle_date_from_ts(ts_ms: int) -> str:
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=ZoneInfo("UTC")).strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalize_stock_cache_candle(row: Any, symbol: str) -> dict[str, Any] | None:
    try:
        close = float(row.get("close") or 0)
        if close <= 0:
            return None
        ts_ms = int(float(row.get("ts") or row.get("ts_ms") or row.get("time") or 0))
        date = str(row.get("date") or row.get("trading_date") or "")
        if not date and ts_ms:
            date = datetime.fromtimestamp(ts_ms / 1000, stock_timezone(symbol)).strftime("%Y-%m-%d")
        return {
            "ts": ts_ms,
            "date": date or candle_date_from_ts(ts_ms),
            "open": float(row.get("open") or close),
            "high": float(row.get("high") or close),
            "low": float(row.get("low") or close),
            "close": close,
            "volume": float(row.get("volume") or row.get("vol") or 0),
            "session": str(row.get("session") or ""),
            "complete": candle_is_complete(row, default_if_missing=False),
        }
    except Exception:
        return None


def with_stock_freshness(payload: dict[str, Any], interval: str, symbol: str) -> dict[str, Any]:
    rows = list(payload.get("rows") or [])
    latest_ts = latest_stock_candle_ts(rows)
    if not latest_ts:
        return payload
    warning = str(payload.get("warning") or "")
    source = str(payload.get("source") or "")
    age_ms = max(0, now_ms() - latest_ts)
    normalized_interval = stock_cache_interval(interval)
    live_age_limit_ms = 3 * 24 * 60 * 60 * 1000 if normalized_interval in {"1d", "1dutc"} else 30 * 60 * 1000
    latest_row = max(rows, key=lambda row: int(row.get("ts") or row.get("ts_ms") or 0))
    daily_in_progress = not candle_is_complete(latest_row, default_if_missing=False)
    realtime = bool(
        source == "futu"
        and not warning
        and age_ms <= live_age_limit_ms
        and (normalized_interval not in {"1d", "1dutc"} or daily_in_progress)
    )
    return {
        **payload,
        "latest_ts": latest_ts,
        "latest_at": datetime.fromtimestamp(latest_ts / 1000, stock_timezone(symbol or "AAPL")).strftime("%Y-%m-%d %H:%M"),
        "data_age_ms": age_ms,
        "realtime": realtime,
        "in_progress": daily_in_progress if normalized_interval in {"1d", "1dutc"} else realtime,
    }


def stock_payload_source(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("origin_source") or payload.get("source") or "").lower()


def stock_payload_is_futu(payload: dict[str, Any] | None) -> bool:
    return stock_payload_source(payload) == "futu"
