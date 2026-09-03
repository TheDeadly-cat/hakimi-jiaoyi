from __future__ import annotations

import math
from typing import Any


STOCK_QUOTE_QUALITY_CONTRACT_VERSION = "stock-quote-quality-v1"
FALLBACK_SOURCES = {"offline-seed", "stock_sqlite_cache", "quote_preview_seed"}


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
    previous_value = (
        previous_close
        if previous_close is not None
        else normalized.get("prevClose", normalized.get("previousClose", normalized.get("prev_close", 0)))
    )
    prev_close = _number(previous_value)
    supplied_change = _number(
        provider_change if provider_change is not None else normalized.get("change24h_pct"),
        float("nan"),
    )
    warnings: list[str] = []
    quarantine_reasons: list[str] = []
    basis_value = change_basis if type(change_basis) is str and change_basis else normalized.get("change_basis")
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

    if high > 0 and low > 0 and high < low:
        quarantine_reasons.append("最高价低于最低价")
    if last > 0 and high > 0 and last > high * 1.005:
        warnings.append("最新价高于行情源日内最高价，可能包含盘前盘后或字段不同步")
    if last > 0 and low > 0 and last < low * 0.995:
        warnings.append("最新价低于行情源日内最低价，可能包含盘前盘后或字段不同步")
    if open_price > 0 and high > 0 and open_price > high * 1.005:
        warnings.append("今开高于行情源日内最高价")
    if open_price > 0 and low > 0 and open_price < low * 0.995:
        warnings.append("今开低于行情源日内最低价")

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
    quote_ts = int(_number(normalized.get("ts"), 0))
    now_value = _number(now_ms, float("nan"))
    if math.isfinite(now_value) and quote_ts > 0:
        age_ms: int | float | None = max(0, int(now_value) - quote_ts)
    else:
        supplied_age = _number(normalized.get("data_age_ms"), float("nan"))
        age_ms = supplied_age if math.isfinite(supplied_age) and supplied_age >= 0 else None
    if age_ms is not None and age_ms > 12 * 60 * 60 * 1000:
        warnings.append("报价时间超过12小时，按延迟研究数据处理")
    warnings = _unique(warnings)
    quarantine_reasons = _unique(quarantine_reasons)
    status = "REVIEW" if quarantine_reasons else "DEGRADED" if warnings or fallback else "PASS"
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
        "status": status,
        "source": source,
        "change_basis": basis,
        "change_basis_label": basis_labels.get(basis, basis or "不可验证"),
        "previous_close": round(prev_close, 6) if prev_close > 0 else 0.0,
        "fallback": fallback,
        "warnings": warnings,
        "quarantined": bool(quarantine_reasons),
        "quarantine_reasons": quarantine_reasons,
        "age_ms": age_ms,
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
    reasons = [item for item in reason_values if type(item) is str and item] if type(reason_values) is list else []
    source = _text(quote.get("source")).lower()
    fallback = quality.get("fallback") is True or source in FALLBACK_SOURCES
    change = abs(_number(quote.get("change24h_pct")))
    high = _number(quote.get("high24h"))
    low = _number(quote.get("low24h"))
    range_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else 0.0
    if fallback and change >= 25:
        reasons.append("缓存涨跌幅异常，疑似复权、拆股或基准价错配")
    if fallback and range_pct >= 40:
        reasons.append("缓存振幅异常，需重新获取日线与昨收")
    return _unique(reasons)


__all__ = [
    "FALLBACK_SOURCES",
    "STOCK_QUOTE_QUALITY_CONTRACT_VERSION",
    "normalize_stock_quote_quality",
    "stock_quote_quarantine_reasons",
]
