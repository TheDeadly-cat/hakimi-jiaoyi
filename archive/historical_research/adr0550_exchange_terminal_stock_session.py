from __future__ import annotations

import math
from datetime import datetime
from typing import Any

try:
    from market_data.stocks import stock_meta, stock_timezone
except ModuleNotFoundError:
    from exchange_terminal.market_data.stocks import stock_meta, stock_timezone


SESSION_LABELS = {
    "pre": "盘前",
    "regular": "盘中",
    "post": "盘后",
    "overnight": "夜盘",
    "break": "休市间歇",
    "closed": "休市",
    "unknown": "状态待确认",
}

FUTU_MARKET_PHASES = {
    "AUCTION": "pre",
    "WAITING_OPEN": "pre",
    "PRE_MARKET_BEGIN": "pre",
    "PRE_MARKET_END": "pre",
    "MORNING": "regular",
    "AFTERNOON": "regular",
    "REST": "break",
    "AFTER_HOURS_BEGIN": "post",
    "AFTER_HOURS_END": "closed",
    "NIGHT_OPEN": "overnight",
    "NIGHT_END": "closed",
    "CLOSED": "closed",
    "NONE": "unknown",
}

OPEN_PHASES = {"pre", "regular", "post", "overnight"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _session_row(price: Any, change_pct: Any = None, volume: Any = None, turnover: Any = None) -> dict[str, Any]:
    clean_price = _number(price)
    clean_change = _number(change_pct, float("nan"))
    return {
        "price": clean_price,
        "change_pct": round(clean_change, 3) if math.isfinite(clean_change) else None,
        "volume": _number(volume),
        "turnover": _number(turnover),
        "available": clean_price > 0,
    }


def normalize_stock_session_prices(quote: dict[str, Any]) -> dict[str, dict[str, Any]]:
    supplied = quote.get("session_prices") if isinstance(quote.get("session_prices"), dict) else {}

    def supplied_row(key: str) -> dict[str, Any]:
        row = supplied.get(key)
        if isinstance(row, dict):
            return _session_row(row.get("price"), row.get("change_pct"), row.get("volume"), row.get("turnover"))
        return {}

    regular = supplied_row("regular") or _session_row(
        quote.get("last"), quote.get("change24h_pct"), quote.get("vol24h"), quote.get("volCcy24h")
    )
    pre = supplied_row("pre") or _session_row(
        quote.get("pre_price"), quote.get("pre_change_rate"), quote.get("pre_volume"), quote.get("pre_turnover")
    )
    post = supplied_row("post") or _session_row(
        quote.get("after_price"), quote.get("after_change_rate"), quote.get("after_volume"), quote.get("after_turnover")
    )
    overnight = supplied_row("overnight") or _session_row(
        quote.get("overnight_price"), quote.get("overnight_change_rate"), quote.get("overnight_volume"), quote.get("overnight_turnover")
    )
    return {
        "pre": pre,
        "regular": regular,
        "post": post,
        "overnight": overnight,
    }


def infer_stock_market_phase(symbol: str, at_ms: int) -> str:
    local = datetime.fromtimestamp(max(int(at_ms), 0) / 1000, stock_timezone(symbol))
    if local.weekday() >= 5:
        return "closed"
    minute = local.hour * 60 + local.minute
    market = str(stock_meta(symbol).get("market") or "US").upper()
    if market in {"HK", "CN", "SH", "SZ"}:
        if 9 * 60 <= minute < 9 * 60 + 30:
            return "pre"
        if 9 * 60 + 30 <= minute < 12 * 60 or 13 * 60 <= minute < 16 * 60:
            return "regular"
        if 12 * 60 <= minute < 13 * 60:
            return "break"
        if 16 * 60 <= minute < 18 * 60:
            return "post"
        return "closed"
    if 4 * 60 <= minute < 9 * 60 + 30:
        return "pre"
    if 9 * 60 + 30 <= minute < 16 * 60:
        return "regular"
    if 16 * 60 <= minute < 20 * 60:
        return "post"
    if minute >= 20 * 60 or minute < 4 * 60:
        return "overnight"
    return "closed"


def build_stock_session_contract(
    symbol: str,
    quote: dict[str, Any],
    *,
    market_state: str = "",
    now_ms_value: int,
) -> dict[str, Any]:
    clean_symbol = stock_meta(symbol).get("symbol") or str(symbol or "").upper()
    raw_state = str(market_state or quote.get("market_state") or "").strip().upper().split(".")[-1]
    provider_confirmed = bool(raw_state and raw_state not in {"NONE", "UNKNOWN"})
    phase = FUTU_MARKET_PHASES.get(raw_state) if provider_confirmed else None
    if not phase:
        phase = infer_stock_market_phase(clean_symbol, now_ms_value)
    sessions = normalize_stock_session_prices(quote)
    active_session = phase if phase in OPEN_PHASES else "regular"
    active_row = sessions.get(active_session) or {}
    if not active_row.get("available"):
        active_session = "regular"
        active_row = sessions.get("regular") or {}

    quote_ts = int(_number(quote.get("ts"), 0))
    quote_age_ms = max(0, int(now_ms_value) - quote_ts) if quote_ts > 0 else None
    source = str(quote.get("source") or "stock").lower()
    sec_status = str(quote.get("sec_status") or "NORMAL").upper()
    suspended = bool(quote.get("suspension")) or sec_status not in {"", "NORMAL"}
    is_open = phase in OPEN_PHASES
    regular_open = phase == "regular"
    extended_open = phase in {"pre", "post", "overnight"}
    age_limit_ms = 120_000 if is_open else 72 * 60 * 60 * 1000
    active_price = _number(active_row.get("price"))

    if suspended:
        status = "HALTED"
    elif active_price <= 0:
        status = "UNAVAILABLE"
    elif quote_age_ms is None or quote_age_ms > age_limit_ms:
        status = "STALE"
    elif source != "futu" or not provider_confirmed:
        status = "DELAYED_SOURCE"
    elif phase == "break":
        status = "SESSION_BREAK"
    elif is_open:
        status = "LIVE_SESSION"
    else:
        status = "LAST_SESSION"

    status_labels = {
        "LIVE_SESSION": f"{SESSION_LABELS.get(phase, phase)}进行中",
        "LAST_SESSION": "最近交易时段",
        "SESSION_BREAK": "盘中休市",
        "DELAYED_SOURCE": f"{SESSION_LABELS.get(phase, phase)}推断",
        "STALE": "行情过期",
        "HALTED": "证券停牌/异常",
        "UNAVAILABLE": "时段价格不可用",
    }
    analysis_ready = status in {"LIVE_SESSION", "LAST_SESSION", "SESSION_BREAK", "DELAYED_SOURCE"}
    return {
        "symbol": clean_symbol,
        "market_state": raw_state or "INFERRED",
        "provider_confirmed": provider_confirmed,
        "phase": phase,
        "phase_label": SESSION_LABELS.get(phase, phase),
        "status": status,
        "status_label": status_labels.get(status, status),
        "is_open": is_open,
        "regular_open": regular_open,
        "extended_open": extended_open,
        "active_session": active_session,
        "active_session_label": SESSION_LABELS.get(active_session, active_session),
        "active_price": active_price,
        "active_change_pct": active_row.get("change_pct"),
        "active_price_is_fallback": active_session != phase,
        "sessions": sessions,
        "quote_ts": quote_ts,
        "quote_age_ms": quote_age_ms,
        "max_quote_age_ms": age_limit_ms,
        "source": source,
        "sec_status": sec_status,
        "analysis_ready": analysis_ready,
        "execution_eligible": bool(status == "LIVE_SESSION" and regular_open and not suspended),
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


def with_stock_session_contract(
    quote: dict[str, Any],
    symbol: str,
    *,
    market_state: str = "",
    now_ms_value: int,
) -> dict[str, Any]:
    normalized = dict(quote)
    contract = build_stock_session_contract(
        symbol,
        normalized,
        market_state=market_state,
        now_ms_value=now_ms_value,
    )
    normalized["market_state"] = contract["market_state"]
    normalized["market_session"] = contract
    normalized["session_prices"] = contract["sessions"]
    normalized["active_session"] = contract["active_session"]
    normalized["active_session_price"] = contract["active_price"]
    normalized["active_session_change_pct"] = contract["active_change_pct"]
    return normalized
