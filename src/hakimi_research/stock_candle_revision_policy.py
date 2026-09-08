from __future__ import annotations

import math
from statistics import median
from typing import Any

from hakimi_research.candle_contract import candle_is_complete


STOCK_CANDLE_REVISION_POLICY_VERSION = "stock-candle-revision-policy-v1"

COMPATIBLE_FORWARD_ADJUSTED_BASES = {
    "FORWARD_ADJUSTED_QFQ",
    "FORWARD_ADJUSTED_TOTAL_RETURN",
}


def _text(value: Any, default: str = "") -> str:
    return value if type(value) is str else default


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


def _native_rows(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        return []
    return [dict(row) for row in value if type(row) is dict]


def stock_candle_source_priority(source: str) -> int:
    text = _text(source).strip().lower()
    if "futu" in text:
        return 40
    if "yahoo_adjusted" in text:
        return 30
    if "yahoo" in text:
        return 20
    if "stooq" in text:
        return 10
    return 0


def infer_adjustment_basis(source: str, explicit: str = "") -> str:
    supplied = _text(explicit).strip().upper()
    if supplied:
        return supplied
    clean_source = _text(source).strip().lower()
    if "futu" in clean_source:
        return "FORWARD_ADJUSTED_QFQ"
    if clean_source in {"test", "fixture", "unit_test"} or "test_fixture" in clean_source:
        return "TEST_FIXTURE_CONTRACT"
    if "yahoo_adjusted" in clean_source:
        return "FORWARD_ADJUSTED_TOTAL_RETURN"
    if "yahoo" in clean_source:
        return "YAHOO_CHART_CLOSE_UNVERIFIED"
    if "stooq" in clean_source:
        return "STOOQ_CLOSE_UNVERIFIED"
    return "UNKNOWN"


def series_adjustment_contract(sources: list[str]) -> tuple[str, str]:
    native_sources = sources if type(sources) is list else []
    bases = {
        infer_adjustment_basis(source)
        for source in native_sources
        if type(source) is str and source
    }
    if bases and bases <= COMPATIBLE_FORWARD_ADJUSTED_BASES:
        basis = (
            "FORWARD_ADJUSTED_TOTAL_RETURN"
            if "FORWARD_ADJUSTED_TOTAL_RETURN" in bases
            else "FORWARD_ADJUSTED_QFQ"
        )
        return basis, "EMBEDDED_PROVIDER_CONTRACT"
    if len(bases) == 1:
        return next(iter(bases)), "UNKNOWN"
    return "MIXED_UNVERIFIED", "UNKNOWN"


def canonical_adjusted_price(value: Any) -> float:
    parsed = _number(value, float("nan"))
    if not math.isfinite(parsed):
        raise ValueError("adjusted_price_not_exact_native_finite")
    return round(parsed, 4)


def prepare_stock_candle_revision_policy(
    incoming_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    source: str,
    interval: str,
) -> dict[str, Any]:
    incoming = [
        row
        for row in _native_rows(incoming_rows)
        if _integer(row.get("ts")) > 0 and _text(row.get("date"))
    ]
    existing_native = [
        row
        for row in _native_rows(existing_rows)
        if _text(row.get("date"))
    ]
    clean_source = _text(source)
    clean_interval = _text(interval).lower()
    result: dict[str, Any] = {
        "policy_version": STOCK_CANDLE_REVISION_POLICY_VERSION,
        "rows": incoming,
        "chain_linked": False,
        "price_scale": 1.0,
        "anchor_date": "",
        "source": clean_source,
    }
    if clean_interval not in {"1d", "1dutc"} or not incoming or not existing_native:
        return result

    incoming_priority = stock_candle_source_priority(clean_source)
    maximum_existing_priority = max(
        stock_candle_source_priority(_text(row.get("source")))
        for row in existing_native
    )
    incoming_basis = infer_adjustment_basis(clean_source)
    existing_bases = {
        infer_adjustment_basis(_text(row.get("source")))
        for row in existing_native
    }
    if (
        incoming_priority > maximum_existing_priority
        and incoming_basis in COMPATIBLE_FORWARD_ADJUSTED_BASES
        and not (existing_bases & COMPATIBLE_FORWARD_ADJUSTED_BASES)
    ):
        result["verified_provider_upgrade"] = True
        return result

    existing_by_date = {
        _text(row.get("date")): row
        for row in existing_native
    }
    new_dates = [
        _text(row.get("date"))
        for row in incoming
        if _text(row.get("date")) not in existing_by_date
    ]
    compatible_existing = [
        row
        for row in existing_native
        if infer_adjustment_basis(_text(row.get("source"))) in COMPATIBLE_FORWARD_ADJUSTED_BASES
    ]
    if incoming_basis not in COMPATIBLE_FORWARD_ADJUSTED_BASES or len(compatible_existing) != len(existing_native):
        if new_dates:
            raise ValueError("daily_adjustment_basis_incompatible_with_cached_vintage")
        return result

    ratios: list[tuple[str, float]] = []
    for row in incoming:
        trading_date = _text(row.get("date"))
        existing = existing_by_date.get(trading_date)
        incoming_close = _number(row.get("close"))
        existing_close = _number(existing.get("close")) if type(existing) is dict else 0.0
        if (
            type(existing) is dict
            and candle_is_complete(existing, default_if_missing=False)
            and incoming_close > 0
            and existing_close > 0
        ):
            ratios.append((trading_date, existing_close / incoming_close))
    if new_dates and not ratios:
        raise ValueError("daily_adjustment_vintage_has_no_overlap_anchor")

    scale = median([item[1] for item in ratios]) if ratios else 1.0
    if not 0.02 <= scale <= 50.0:
        raise ValueError("daily_adjustment_vintage_scale_out_of_range")
    if ratios:
        dispersion = max(abs(value / max(scale, 1e-12) - 1.0) for _date, value in ratios)
        if dispersion > 0.0025:
            raise ValueError("daily_adjustment_vintage_overlap_is_not_uniform")

    prepared: list[dict[str, Any]] = []
    for row in incoming:
        trading_date = _text(row.get("date"))
        existing = existing_by_date.get(trading_date)
        if type(existing) is dict and candle_is_complete(existing, default_if_missing=False):
            prepared.append({**row, **existing})
            continue
        adjusted = dict(row)
        for field in ("open", "high", "low", "close"):
            value = _number(adjusted.get(field), float("nan"))
            if not math.isfinite(value) or value <= 0:
                raise ValueError("daily_adjustment_vintage_row_invalid")
            adjusted[field] = canonical_adjusted_price(value * scale)
        volume = _number(adjusted.get("volume"), float("nan"))
        if not math.isfinite(volume) or volume < 0:
            raise ValueError("daily_adjustment_vintage_row_invalid")
        adjusted["volume"] = volume / scale
        prepared.append(adjusted)
    result.update({
        "rows": prepared,
        "chain_linked": bool(new_dates) and abs(scale - 1.0) > 1e-8,
        "price_scale": scale,
        "anchor_date": max((item[0] for item in ratios), default=""),
        "overlap_count": len(ratios),
        "new_date_count": len(new_dates),
    })
    return result


__all__ = [
    "COMPATIBLE_FORWARD_ADJUSTED_BASES",
    "STOCK_CANDLE_REVISION_POLICY_VERSION",
    "canonical_adjusted_price",
    "infer_adjustment_basis",
    "prepare_stock_candle_revision_policy",
    "series_adjustment_contract",
    "stock_candle_source_priority",
]
