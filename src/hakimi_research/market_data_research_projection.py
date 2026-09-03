from __future__ import annotations

import math
from typing import Any, Final


SCHEMA_VERSION: Final = "market-data-research-projection-v1"
SEQUENCE: Final = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
_RAW_SCHEMA: Final = "market-data-truth-v1"
_RAW_STATUSES: Final = frozenset({"READY", "STALE", "UNKNOWN", "BLOCK"})


def _native_record(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        return {}
    if any(type(key) is not str for key in value):
        return {}
    return value


def _native_text(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    return value if type(value) is str else ""


def _native_bool(record: dict[str, Any], key: str) -> bool | None:
    value = record.get(key)
    return value if type(value) is bool else None


def _append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _authority_contradiction(truth: dict[str, Any]) -> bool:
    for key in ("execution_usable", "paper_authorized", "live_order_allowed"):
        value = truth.get(key, False)
        if type(value) is not bool or value:
            return True
    return False


def _positive_timestamp(value: Any) -> bool:
    if type(value) is int:
        return value > 0
    if type(value) is float:
        return math.isfinite(value) and value > 0
    return False


def _source_evidence(truth: dict[str, Any]) -> tuple[bool, bool]:
    quote = _native_record(truth.get("quote"))
    candles = _native_record(truth.get("candles"))
    quote_bound = bool(_native_text(quote, "source").strip())
    candles_bound = bool(_native_text(candles, "source").strip())
    return quote_bound, candles_bound


def _source_projection(truth: dict[str, Any], raw_status: str) -> dict[str, Any]:
    quote_bound, candles_bound = _source_evidence(truth)
    if quote_bound and candles_bound:
        return {
            "status": "BOUND",
            "label": "来源已绑定",
            "quote_observed": quote_bound,
            "candles_observed": candles_bound,
        }
    if quote_bound or candles_bound or raw_status in {"READY", "STALE", "BLOCK"}:
        return {
            "status": "PARTIAL",
            "label": "来源不完整",
            "quote_observed": quote_bound,
            "candles_observed": candles_bound,
        }
    return {
        "status": "UNOBSERVED",
        "label": "尚未观察",
        "quote_observed": False,
        "candles_observed": False,
    }


def _gap_codes(truth: dict[str, Any], raw_status: str, mode: str) -> list[str]:
    codes: list[str] = []
    if (
        _native_text(truth, "schema_version") != _RAW_SCHEMA
        or raw_status not in _RAW_STATUSES
        or type(truth.get("mode")) is not str
    ):
        _append_once(codes, "CONTRACT_MISMATCH")
    if _native_bool(truth, "snapshot_available") is not True:
        _append_once(codes, "SNAPSHOT_UNOBSERVED")
    quote_bound, candles_bound = _source_evidence(truth)
    if not quote_bound:
        _append_once(codes, "QUOTE_SOURCE_MISSING")
    if not candles_bound:
        _append_once(codes, "CANDLE_SOURCE_MISSING")
    if raw_status == "STALE" or (
        raw_status != "UNKNOWN" and _native_bool(truth, "observation_current") is not True
    ):
        _append_once(codes, "OBSERVATION_STALE")
    if raw_status == "BLOCK":
        _append_once(codes, "DATA_BLOCKED")
    if raw_status == "READY" and _native_bool(truth, "realtime_ready") is not True:
        _append_once(codes, "DATA_CONTRACT_INCOMPLETE")

    mode_upper = mode.upper() if mode else ""
    if "FALLBACK" in mode_upper or "SYNTHETIC" in mode_upper:
        _append_once(codes, "FALLBACK_SOURCE")

    quote = _native_record(truth.get("quote"))
    candles = _native_record(truth.get("candles"))
    quote_status = _native_text(quote, "status")
    quote_source = (
        _native_text(quote, "source_kind")
        or _native_text(quote, "source_type")
        or _native_text(quote, "source")
    )
    if quote_status == "QUARANTINED":
        _append_once(codes, "QUOTE_QUARANTINED")
    if quote_source and (
        "FALLBACK" in quote_source.upper() or "SYNTHETIC" in quote_source.upper()
    ):
        _append_once(codes, "FALLBACK_SOURCE")

    revision_status = _native_text(candles, "revision_status")
    if revision_status in {"BLOCK", "BLOCKED"}:
        _append_once(codes, "REVISION_BLOCKED")
    if not _positive_timestamp(candles.get("last_completed_ts")) or (
        "freshness_confirmed" in candles
        and _native_bool(candles, "freshness_confirmed") is not True
    ):
        _append_once(codes, "CANDLE_FRESHNESS_UNCONFIRMED")

    warnings = truth.get("warnings")
    if warnings is not None:
        if type(warnings) is not list or any(type(item) is not str for item in warnings):
            _append_once(codes, "MALFORMED_WARNINGS")
        elif warnings:
            _append_once(codes, "WARNINGS_PRESENT")

    if _authority_contradiction(truth):
        _append_once(codes, "AUTHORITY_CONTRADICTION")
    return codes


def _maturity_projection(
    truth: dict[str, Any],
    raw_status: str,
    mode: str,
    gaps: list[str],
) -> dict[str, Any]:
    if (
        _native_text(truth, "schema_version") != _RAW_SCHEMA
        or raw_status not in _RAW_STATUSES
        or "CONTRACT_MISMATCH" in gaps
        or "MALFORMED_WARNINGS" in gaps
        or raw_status == "BLOCK"
        or _authority_contradiction(truth)
    ):
        status = "BLOCKED"
        label = "已阻断"
    elif raw_status == "UNKNOWN":
        status = "UNOBSERVED"
        label = "尚未观察"
    elif raw_status == "STALE" or gaps:
        status = "DEGRADED_OBSERVATION"
        label = "降级观察"
    elif raw_status == "READY":
        realtime_usable = _native_bool(truth, "realtime_usable") is True
        analysis_usable = _native_bool(truth, "analysis_usable") is True
        research_usable = _native_bool(truth, "research_usable") is True
        mode_upper = mode.upper() if mode else ""
        if realtime_usable or mode == "REALTIME_READY":
            status = "CURRENT_OBSERVATION"
            label = "当前观察"
        elif analysis_usable or research_usable or "HISTORICAL" in mode_upper:
            status = "HISTORICAL_OBSERVATION"
            label = "历史观察"
        else:
            status = "DEGRADED_OBSERVATION"
            label = "降级观察"
    else:
        status = "BLOCKED"
        label = "已阻断"
    return {
        "status": status,
        "label": label,
        "current_observation": status == "CURRENT_OBSERVATION",
        "historical_observation": status == "HISTORICAL_OBSERVATION",
    }


def build_market_data_research_projection(value: Any) -> dict[str, Any]:
    """Project raw market-data truth into neutral research presentation semantics."""

    truth = _native_record(value)
    raw_status = _native_text(truth, "status")
    mode = _native_text(truth, "mode")
    gaps = _gap_codes(truth, raw_status, mode)
    return {
        "schema_version": SCHEMA_VERSION,
        "sequence": list(SEQUENCE),
        "source": _source_projection(truth, raw_status),
        "gap": {
            "status": "OPEN" if gaps else "NONE",
            "label": f"证据缺口 {len(gaps)}" if gaps else "未发现结构缺口",
            "codes": gaps,
        },
        "maturity": _maturity_projection(truth, raw_status, mode, gaps),
        "permission": {
            "status": "RESEARCH_ONLY",
            "label": "仅研究 · 不授予模拟、实盘或订单权限",
            "paper_authorized": False,
            "live_order_allowed": False,
            "order_allowed": False,
            "ranking_allowed": False,
            "parameter_selection_allowed": False,
            "profitability_proven": False,
        },
    }
