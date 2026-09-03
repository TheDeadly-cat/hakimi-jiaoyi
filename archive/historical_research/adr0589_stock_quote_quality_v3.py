from __future__ import annotations

import math
from typing import Any

from hakimi_research.stock_data_quality import (
    AUTHORITY_LOCK,
    SAFE_ACTION,
    STOCK_DATA_QUALITY_BOUNDARY_VERSION,
    STOCK_MARKET_DATA_GOVERNANCE_VERSION,
    observation_time_quality,
)


STOCK_QUOTE_QUALITY_CONTRACT_VERSION = "stock-quote-quality-v3"
FALLBACK_SOURCES = {"offline-seed", "stock_sqlite_cache", "quote_preview_seed"}
QUOTE_MAX_AGE_MS = 12 * 60 * 60 * 1000


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


def _text(value: Any, default: str = "") -> str:
    return value if type(value) is str else default


def _unique(values: list[str]) -> list[str]:
    if type(values) is not list:
        return []
    return list(dict.fromkeys(value for value in values if type(value) is str and value))


def normalize_stock_quote_quality(
    quote: dict[str, Any],
    *,
    previous_close: Any = None,
    change_basis: str = "",
    provider_change: Any = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    normalized = dict(quote) if type(quote) is dict else {}
    source = _text(normalized.get("source"), "stock").lower()
    last = _number(normalized.get("last"))
    open_price = _number(normalized.get("open24h"))
    high = _number(normalized.get("high24h"))
    low = _number(normalized.get("low24h"))
    bid = _number(normalized.get("bidPx"))
    ask = _number(normalized.get("askPx"))
    previous_value = (
        previous_close
        if previous_close is not None
        else normalized.get(
            "prevClose",
            normalized.get("previousClose", normalized.get("prev_close", 0)),
        )
    )
    prev_close = _number(previous_value)
    supplied_change = _number(
        provider_change
        if provider_change is not None
        else normalized.get("change24h_pct"),
        float("nan"),
    )
    warnings: list[str] = []
    quarantine_reasons: list[str] = []
    basis_value = (
        change_basis
        if type(change_basis) is str and change_basis
        else normalized.get("change_basis")
    )
    basis = _text(basis_value).strip().lower()

    if last <= 0:
        change = 0.0
        basis = basis or "unavailable"
        quarantine_reasons.append("最新价无效")
    elif prev_close > 0:
        change = (last / prev_close - 1) * 100
        basis = basis or "previous_close"
        if math.isfinite(supplied_change) and abs(change - supplied_change) > 0.35:
            warnings.append("数据源涨跌幅与昨收重算结果不一致，已按昨收修正")
    elif math.isfinite(supplied_change) and basis == "provider":
        change = supplied_change
        warnings.append("数据源未提供昨收，涨跌幅沿用数据源结果")
    elif open_price > 0:
        change = (last / open_price - 1) * 100
        basis = "open"
        warnings.append("缺少昨收，涨跌幅暂按今开计算")
    else:
        change = supplied_change if math.isfinite(supplied_change) else 0.0
        basis = basis or "unavailable"
        warnings.append("缺少昨收和今开，涨跌幅基准不可验证")

    scope_value = _text(normalized.get("last_price_scope")).strip().upper()
    active_session = _text(normalized.get("active_session")).strip().lower()
    if scope_value not in {"REGULAR", "EXTENDED", "UNKNOWN"}:
        scope_value = (
            "REGULAR"
            if active_session == "regular"
            else "EXTENDED"
            if active_session in {"pre", "post", "overnight"}
            else "UNKNOWN"
        )
    price_envelope_status = "VALID"
    if high <= 0 or low <= 0:
        warnings.append("日内最高价或最低价缺失，报价区间不完整")
        price_envelope_status = "INCOMPLETE"
    elif high < low:
        quarantine_reasons.append("最高价低于最低价")
        price_envelope_status = "INVALID"
    else:
        if open_price > high or open_price < low:
            quarantine_reasons.append("今开不在日内最高价与最低价包络内")
            price_envelope_status = "INVALID"
        if last > high or last < low:
            if scope_value == "REGULAR":
                quarantine_reasons.append("常规时段最新价不在日内价格包络内")
                price_envelope_status = "INVALID"
            else:
                warnings.append("最新价超出日内价格包络且时段口径未证明一致")
                if price_envelope_status == "VALID":
                    price_envelope_status = "LAST_SCOPE_UNVERIFIED"

    if bid > 0 and ask > 0:
        if bid > ask:
            book_status = "CROSSED"
            quarantine_reasons.append("买一价高于卖一价，盘口交叉")
        else:
            book_status = "VALID"
    elif bid > 0 or ask > 0:
        book_status = "ONE_SIDED"
        warnings.append("买卖盘仅提供单边报价，盘口完整性降级")
    else:
        book_status = "NOT_SUPPLIED"
        warnings.append("买卖盘未同时提供，盘口完整性未验证")

    fallback = source in FALLBACK_SOURCES or "seed" in source or "offline" in source
    if abs(change) >= 45:
        quarantine_reasons.append("涨跌幅超过45%，需核对复权、拆股和昨收基准")
    elif abs(change) >= 25 and (fallback or basis != "previous_close"):
        quarantine_reasons.append("非实时或非昨收基准出现超过25%的涨跌，需人工复核")
    if high > 0 and low > 0 and (high / max(low, 1e-9) - 1) * 100 >= 40:
        quarantine_reasons.append("日内振幅超过40%，需核对复权或字段错配")

    existing_warning = _text(normalized.get("warning")).strip()
    if existing_warning:
        warnings.insert(0, existing_warning)
    time_quality = observation_time_quality(
        normalized.get("ts"),
        now_ms=now_ms,
        max_age_ms=QUOTE_MAX_AGE_MS,
    )
    if time_quality["status"] == "MISSING_TIMESTAMP":
        warnings.append("报价时间戳缺失，时效无法复算")
    elif time_quality["status"] == "INVALID_TIMESTAMP":
        quarantine_reasons.append("报价时间戳类型或范围无效")
    elif time_quality["status"] == "INVALID_NOW":
        warnings.append("观察时间缺失或无效，报价时效未独立复算")
    elif time_quality["status"] == "FUTURE_TIMESTAMP":
        quarantine_reasons.append("报价时间戳晚于观察时间，疑似时钟或时区错误")
    elif time_quality["status"] == "STALE":
        warnings.append("报价时间超过12小时，按延迟研究数据处理")

    warnings = _unique(warnings)
    quarantine_reasons = _unique(quarantine_reasons)
    price_fields_complete = all(
        value > 0 for value in (last, open_price, high, low, prev_close)
    )
    quote_complete = (
        price_fields_complete
        and book_status == "VALID"
        and time_quality["current"] is True
        and not fallback
        and price_envelope_status == "VALID"
        and not quarantine_reasons
    )
    status = (
        "REVIEW"
        if quarantine_reasons
        else "DEGRADED"
        if warnings or fallback or not quote_complete
        else "PASS"
    )
    basis_labels = {
        "previous_close": "昨收",
        "local_previous_close": "本地K线昨收",
        "provider": "数据源",
        "open": "今开",
        "synthetic": "模拟基准",
        "unavailable": "不可验证",
    }
    quality = {
        "contract_version": STOCK_QUOTE_QUALITY_CONTRACT_VERSION,
        "quality_boundary_version": STOCK_DATA_QUALITY_BOUNDARY_VERSION,
        "governance_version": STOCK_MARKET_DATA_GOVERNANCE_VERSION,
        "status": status,
        "source": source,
        "change_basis": basis,
        "change_basis_label": basis_labels.get(basis, basis or "不可验证"),
        "previous_close": round(prev_close, 6) if prev_close > 0 else 0.0,
        "fallback": fallback,
        "warnings": warnings,
        "quarantined": bool(quarantine_reasons),
        "quarantine_reasons": quarantine_reasons,
        "age_ms": time_quality["age_ms"],
        "time_quality": time_quality,
        "book_status": book_status,
        "book_complete": book_status == "VALID",
        "last_price_scope": scope_value,
        "price_envelope_status": price_envelope_status,
        "price_fields_complete": price_fields_complete,
        "quote_complete": quote_complete,
        "authority": dict(AUTHORITY_LOCK),
        "safe_action": SAFE_ACTION,
    }
    normalized.update({
        "prevClose": quality["previous_close"],
        "change24h_pct": round(change, 2),
        "change_basis": basis,
        "quote_quality": quality,
    })
    if warnings:
        normalized["warning"] = " / ".join(warnings)
    return normalized


def stock_quote_quarantine_reasons(quote: dict[str, Any]) -> list[str]:
    if type(quote) is not dict:
        return ["invalid quote container"]
    quality_value = quote.get("quote_quality")
    quality = quality_value if type(quality_value) is dict else {}
    reason_values = quality.get("quarantine_reasons")
    reasons = (
        [item for item in reason_values if type(item) is str and item]
        if type(reason_values) is list
        else []
    )
    source = _text(quote.get("source")).lower()
    fallback = quality.get("fallback") is True or source in FALLBACK_SOURCES
    change = abs(_number(quote.get("change24h_pct")))
    high = _number(quote.get("high24h"))
    low = _number(quote.get("low24h"))
    bid = _number(quote.get("bidPx"))
    ask = _number(quote.get("askPx"))
    range_pct = (
        (high / max(low, 1e-9) - 1) * 100
        if high > 0 and low > 0
        else 0.0
    )
    if bid > 0 and ask > 0 and bid > ask:
        reasons.append("买一价高于卖一价，盘口交叉")
    if fallback and change >= 25:
        reasons.append("缓存涨跌幅异常，疑似复权、拆股或基准价错配")
    if fallback and range_pct >= 40:
        reasons.append("缓存振幅异常，需重新获取日线与昨收")
    return _unique(reasons)


__all__ = [
    "FALLBACK_SOURCES",
    "QUOTE_MAX_AGE_MS",
    "STOCK_QUOTE_QUALITY_CONTRACT_VERSION",
    "normalize_stock_quote_quality",
    "stock_quote_quarantine_reasons",
]
