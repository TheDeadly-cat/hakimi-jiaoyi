from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from hakimi_research.candle_contract import explicit_boolean
from hakimi_research.market_calendar import (
    MARKET_SCHEDULE_ATTESTATION_VERSION,
    infer_market_calendar,
    verify_market_schedule_attestation,
)
from hakimi_research.stock_data_quality import (
    AUTHORITY_LOCK,
    SAFE_ACTION,
    STOCK_DATA_QUALITY_BOUNDARY_VERSION,
    STOCK_MARKET_DATA_GOVERNANCE_VERSION,
    native_epoch_ms,
    observation_time_quality,
)
from hakimi_research.stock_metadata import stock_meta, stock_timezone


STOCK_SESSION_CONTRACT_VERSION = "stock-session-v3"

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
    native_quote = quote if type(quote) is dict else {}
    supplied_value = native_quote.get("session_prices")
    supplied = supplied_value if type(supplied_value) is dict else {}

    def supplied_row(key: str) -> dict[str, Any]:
        row = supplied.get(key)
        if type(row) is dict:
            return _session_row(row.get("price"), row.get("change_pct"), row.get("volume"), row.get("turnover"))
        return {}

    regular = supplied_row("regular") or _session_row(
        native_quote.get("last"), native_quote.get("change24h_pct"), native_quote.get("vol24h"), native_quote.get("volCcy24h")
    )
    pre = supplied_row("pre") or _session_row(
        native_quote.get("pre_price"), native_quote.get("pre_change_rate"), native_quote.get("pre_volume"), native_quote.get("pre_turnover")
    )
    post = supplied_row("post") or _session_row(
        native_quote.get("after_price"), native_quote.get("after_change_rate"), native_quote.get("after_volume"), native_quote.get("after_turnover")
    )
    overnight = supplied_row("overnight") or _session_row(
        native_quote.get("overnight_price"), native_quote.get("overnight_change_rate"), native_quote.get("overnight_volume"), native_quote.get("overnight_turnover")
    )
    return {"pre": pre, "regular": regular, "post": post, "overnight": overnight}


def _calendar_quality(
    symbol: str,
    timestamp_ms: int | None,
    schedule_attestation: Any,
) -> dict[str, Any]:
    expected_calendar = infer_market_calendar(symbol, source="stock")
    timezone_value = stock_timezone(symbol)
    timezone_name = getattr(timezone_value, "key", "")
    local_date = ""
    if timestamp_ms is not None:
        try:
            local_date = datetime.fromtimestamp(
                timestamp_ms / 1000,
                timezone_value,
            ).date().isoformat()
        except (OverflowError, OSError, ValueError):
            local_date = ""
    result = {
        "contract_version": MARKET_SCHEDULE_ATTESTATION_VERSION,
        "calendar_name": expected_calendar,
        "timezone": timezone_name,
        "local_date": local_date,
        "status": "ATTESTATION_MISSING",
        "schedule_verified": False,
        "trading_day": None,
        "session": {},
        "source_class": "",
        "attestation_hash": "",
        "official_source_verified": False,
        "external_truth_verified": False,
    }
    if not local_date:
        result["status"] = "REFERENCE_TIME_INVALID"
        return result
    if type(schedule_attestation) is not dict:
        return result
    try:
        verified = verify_market_schedule_attestation(schedule_attestation)
    except (TypeError, ValueError):
        result["status"] = "ATTESTATION_INVALID"
        return result
    if verified is not True:
        result["status"] = "ATTESTATION_INVALID"
        return result
    result["source_class"] = schedule_attestation["source_class"]
    result["attestation_hash"] = schedule_attestation["attestation_hash"]
    result["official_source_verified"] = (
        schedule_attestation["official_source_verified"] is True
    )
    result["external_truth_verified"] = (
        schedule_attestation["external_truth_verified"] is True
    )
    if schedule_attestation["calendar_name"] != expected_calendar:
        result["status"] = "ATTESTATION_CALENDAR_MISMATCH"
        return result
    if schedule_attestation["timezone"] != timezone_name:
        result["status"] = "ATTESTATION_TIMEZONE_MISMATCH"
        return result
    if not (
        schedule_attestation["coverage_start"]
        <= local_date
        <= schedule_attestation["coverage_end"]
    ):
        result["status"] = "ATTESTATION_OUT_OF_COVERAGE"
        return result
    session = next(
        (
            item
            for item in schedule_attestation["sessions"]
            if item["date"] == local_date
        ),
        None,
    )
    result.update({
        "status": "TRADING_DAY" if session is not None else "NON_TRADING_DATE",
        "schedule_verified": True,
        "trading_day": session is not None,
        "session": dict(session) if session is not None else {},
    })
    return result


def infer_stock_market_phase(symbol: str, at_ms: int) -> str:
    timestamp_ms = native_epoch_ms(at_ms)
    if timestamp_ms is None:
        return "unknown"
    try:
        local = datetime.fromtimestamp(timestamp_ms / 1000, stock_timezone(symbol))
    except (OverflowError, OSError, ValueError):
        return "unknown"
    if local.weekday() >= 5:
        return "closed"
    minute = local.hour * 60 + local.minute
    market = _text(stock_meta(symbol).get("market"), "US").upper()
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
    schedule_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    native_quote = quote if type(quote) is dict else {}
    clean_symbol = _text(stock_meta(symbol).get("symbol"), "AAPL")
    source = _text(native_quote.get("source"), "stock").lower()
    state_value = market_state if type(market_state) is str else native_quote.get("market_state")
    raw_state = _text(state_value).strip().upper().split(".")[-1]
    provider_phase = FUTU_MARKET_PHASES.get(raw_state)
    provider_confirmed = (
        source == "futu"
        and provider_phase is not None
        and provider_phase != "unknown"
    )
    now_value = native_epoch_ms(now_ms_value)
    inferred_phase = infer_stock_market_phase(clean_symbol, now_value or 0)
    phase = provider_phase if provider_confirmed else inferred_phase
    if phase not in SESSION_LABELS:
        phase = "unknown"
    sessions = normalize_stock_session_prices(native_quote)
    active_session = phase if phase in OPEN_PHASES else "regular"
    active_row = sessions.get(active_session) or {}
    if active_row.get("available") is not True:
        active_session = "regular"
        active_row = sessions.get("regular") or {}

    is_open = phase in OPEN_PHASES
    regular_open = phase == "regular"
    extended_open = phase in {"pre", "post", "overnight"}
    calendar_quality = _calendar_quality(
        clean_symbol,
        now_value,
        schedule_attestation,
    )
    calendar_open_conflict = (
        is_open
        and calendar_quality["schedule_verified"] is True
        and calendar_quality["trading_day"] is not True
    )
    calendar_unverified_open = (
        is_open and calendar_quality["schedule_verified"] is not True
    )
    age_limit_ms = 120_000 if is_open else 72 * 60 * 60 * 1000
    time_quality = observation_time_quality(
        native_quote.get("ts"),
        now_ms=now_ms_value,
        max_age_ms=age_limit_ms,
    )
    quote_ts = time_quality["observed_at_ms"] or 0
    quote_age_ms = time_quality["age_ms"]
    provider_open_conflict = (
        provider_confirmed
        and provider_phase in OPEN_PHASES
        and inferred_phase not in OPEN_PHASES
    )
    session_consistent = not provider_open_conflict and not calendar_open_conflict
    sec_status = _text(native_quote.get("sec_status"), "NORMAL").upper()
    suspended = (
        explicit_boolean(native_quote.get("suspension")) is True
        or sec_status not in {"", "NORMAL"}
    )
    active_price = _number(active_row.get("price"))
    active_price_is_fallback = active_session != phase

    if suspended:
        status = "HALTED"
    elif active_price <= 0:
        status = "UNAVAILABLE"
    elif time_quality["status"] in {
        "MISSING_TIMESTAMP",
        "INVALID_TIMESTAMP",
        "INVALID_NOW",
        "FUTURE_TIMESTAMP",
    }:
        status = "TIME_INVALID"
    elif time_quality["stale"]:
        status = "STALE"
    elif provider_open_conflict:
        status = "SESSION_MISMATCH"
    elif calendar_open_conflict:
        status = "SESSION_MISMATCH"
    elif calendar_unverified_open:
        status = "CALENDAR_UNVERIFIED"
    elif source != "futu" or not provider_confirmed:
        status = "DELAYED_SOURCE"
    elif active_price_is_fallback and phase in OPEN_PHASES:
        status = "SESSION_PRICE_FALLBACK"
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
        "SESSION_PRICE_FALLBACK": "当前时段价格缺失",
        "SESSION_MISMATCH": "来源时段与本地时钟冲突",
        "CALENDAR_UNVERIFIED": "交易日历证明缺失或未覆盖当前日期",
        "TIME_INVALID": "报价时间无效",
        "STALE": "行情过期",
        "HALTED": "证券停牌/异常",
        "UNAVAILABLE": "时段价格不可用",
    }
    analysis_ready = status in {
        "LIVE_SESSION",
        "LAST_SESSION",
        "SESSION_BREAK",
        "DELAYED_SOURCE",
    }
    return {
        "contract_version": STOCK_SESSION_CONTRACT_VERSION,
        "quality_boundary_version": STOCK_DATA_QUALITY_BOUNDARY_VERSION,
        "governance_version": STOCK_MARKET_DATA_GOVERNANCE_VERSION,
        "symbol": clean_symbol,
        "market_state": raw_state or "INFERRED",
        "provider_state_known": provider_phase is not None,
        "provider_confirmed": provider_confirmed,
        "provider_phase": provider_phase or "unknown",
        "inferred_phase": inferred_phase,
        "session_consistent": session_consistent,
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
        "active_price_is_fallback": active_price_is_fallback,
        "sessions": sessions,
        "quote_ts": quote_ts,
        "quote_age_ms": quote_age_ms,
        "max_quote_age_ms": age_limit_ms,
        "time_quality": time_quality,
        "timezone": getattr(stock_timezone(clean_symbol), "key", ""),
        "calendar_scope": (
            "ATTESTED_SCHEDULE_COVERAGE"
            if calendar_quality["schedule_verified"] is True
            else "WEEKDAY_AND_FIXED_SESSION_WINDOWS_ONLY"
        ),
        "calendar_quality": calendar_quality,
        "calendar_schedule_verified": calendar_quality["schedule_verified"],
        "calendar_trading_day": calendar_quality["trading_day"],
        "calendar_attestation_hash": calendar_quality["attestation_hash"],
        "exchange_holiday_calendar_attested": calendar_quality["schedule_verified"],
        "official_exchange_calendar_verified": calendar_quality[
            "official_source_verified"
        ],
        "session_schedule_bound": (
            calendar_quality["schedule_verified"] is True
            and (not is_open or calendar_quality["trading_day"] is True)
        ),
        "session_truth_verified": (
            calendar_quality["external_truth_verified"] is True
            and (not is_open or calendar_quality["trading_day"] is True)
        ),
        "source": source,
        "sec_status": sec_status,
        "analysis_ready": analysis_ready,
        "execution_eligible": False,
        "execution_authority": False,
        "authority": dict(AUTHORITY_LOCK),
        "safe_action": SAFE_ACTION,
    }


def with_stock_session_contract(
    quote: dict[str, Any],
    symbol: str,
    *,
    market_state: str = "",
    now_ms_value: int,
    schedule_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = dict(quote) if type(quote) is dict else {}
    contract = build_stock_session_contract(
        symbol,
        normalized,
        market_state=market_state,
        now_ms_value=now_ms_value,
        schedule_attestation=schedule_attestation,
    )
    normalized["market_state"] = contract["market_state"]
    normalized["market_session"] = contract
    normalized["session_prices"] = contract["sessions"]
    normalized["active_session"] = contract["active_session"]
    normalized["active_session_price"] = contract["active_price"]
    normalized["active_session_change_pct"] = contract["active_change_pct"]
    return normalized


__all__ = [
    "FUTU_MARKET_PHASES",
    "OPEN_PHASES",
    "SESSION_LABELS",
    "STOCK_SESSION_CONTRACT_VERSION",
    "build_stock_session_contract",
    "infer_stock_market_phase",
    "normalize_stock_session_prices",
    "with_stock_session_contract",
]
