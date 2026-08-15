from __future__ import annotations

from copy import deepcopy
from typing import Any

from .execution_authority import authority_violations, sanitize_authority_claims


MARKET_ANOMALY_RESEARCH_PROJECTION_SCHEMA = "market-anomaly-research-projection-v1"
_RESEARCH_OBSERVATION = "研究观察"
_SAFE_ACTION = "观察 / 仅研究 / 非订单"
_VISIBLE_READY_STATUSES = {
    "ACTIVE",
    "AUTO",
    "CONNECTED",
    "ENABLED",
    "HEALTHY",
    "ONLINE",
    "PASS",
    "READY",
}

def _neutralize_research_fields(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("direction", "preferred"):
            if key in value:
                raw_key = f"raw_{key}"
                value.setdefault(raw_key, deepcopy(value[key]))
                value[key] = _RESEARCH_OBSERVATION
        if "tone" in value:
            value.setdefault("raw_tone", deepcopy(value["tone"]))
            value["tone"] = "flat"
        if str(value.get("status") or "").upper() in _VISIBLE_READY_STATUSES:
            value.setdefault("raw_status", deepcopy(value["status"]))
            value["status"] = _RESEARCH_OBSERVATION
        if "safe_action" in value:
            value["safe_action"] = _SAFE_ACTION
        for key, nested in value.items():
            if str(key).startswith("raw_"):
                continue
            _neutralize_research_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _neutralize_research_fields(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _neutralize_research_fields(nested)
    return value


def _invalid_projection(error: str = "invalid_research_payload") -> dict[str, Any]:
    return {
        "ok": False,
        "projection_schema_version": MARKET_ANOMALY_RESEARCH_PROJECTION_SCHEMA,
        "status": "UNKNOWN",
        "research_only": True,
        "descriptive_only": True,
        "direction_signal_allowed": False,
        "performance_claim_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "safe_action": _SAFE_ACTION,
        "error": error,
    }


def _base_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _invalid_projection()
    projected, paths = sanitize_authority_claims(payload, path="payload")
    projected = _neutralize_research_fields(projected)
    result = dict(projected)
    result.update(
        {
            "projection_schema_version": MARKET_ANOMALY_RESEARCH_PROJECTION_SCHEMA,
            "research_only": True,
            "descriptive_only": True,
            "direction_signal_allowed": False,
            "performance_claim_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "live_trading_allowed": False,
            "safe_action": _SAFE_ACTION,
        }
    )
    if paths:
        result["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    else:
        result.pop("authority_sanitized_paths", None)
    if authority_violations(result):
        return _invalid_projection("authority_projection_postcondition_failed")
    return result


def build_market_anomaly_radar_projection(payload: Any) -> dict[str, Any]:
    """Project the radar response for descriptive research-only presentation."""

    return _base_projection(payload)


def build_market_anomaly_detail_projection(payload: Any) -> dict[str, Any]:
    """Project the detail response without allowing nested trend/order semantics."""

    return _base_projection(payload)


def build_market_trend_cockpit_projection(payload: Any) -> dict[str, Any]:
    """Project the trend cockpit while retaining raw direction as audit metadata."""

    return _base_projection(payload)
