from __future__ import annotations

from copy import deepcopy
from typing import Any

from .execution_authority import authority_violations, sanitize_authority_claims


MARKET_SCANNER_RESEARCH_PROJECTION_SCHEMA = "market-scanner-research-projection-v1"
_RESEARCH_OBSERVATION = "\u7814\u7a76\u89c2\u5bdf"
_STRATEGY_OBSERVATION = "RESEARCH_OBSERVE"
_STRATEGY_LABEL = "\u7814\u7a76\u89c2\u5bdf \u00b7 \u672a\u9009\u53c2"
_RISK_LABEL = "\u98ce\u9669\u89c2\u5bdf"
_SAFE_ACTION = "\u89c2\u5bdf / \u4ec5\u7814\u7a76 / \u975e\u8ba2\u5355"
_SUMMARY = "\u626b\u63cf\u5feb\u7167\u5df2\u6574\u7406 \u00b7 \u7814\u7a76\u89c2\u5bdf \u00b7 \u4e0d\u9009\u53c2\u3001\u4e0d\u4e0b\u5355"
_VISIBLE_READY_STATUSES = {
    "ACTIVE",
    "AUTO",
    "COMPLETE",
    "COMPLETED",
    "CONNECTED",
    "DONE",
    "ENABLED",
    "HEALTHY",
    "ONLINE",
    "PASS",
    "READY",
    "RUNNING",
    "SUCCESS",
    "SUCCEEDED",
}

def _neutralize_common(value: Any) -> None:
    if isinstance(value, dict):
        for key in ("direction", "preferred", "stance"):
            if key in value:
                raw_key = f"raw_{key}"
                value.setdefault(raw_key, deepcopy(value[key]))
                value[key] = _RESEARCH_OBSERVATION
        if "tone" in value:
            value.setdefault("raw_tone", deepcopy(value["tone"]))
            value["tone"] = "flat"
        if "safe_action" in value:
            value["safe_action"] = _SAFE_ACTION
        if "action" in value:
            value.setdefault("raw_action", deepcopy(value["action"]))
            value["action"] = _SAFE_ACTION
        status = str(value.get("status") or "").upper()
        if status in _VISIBLE_READY_STATUSES:
            value.setdefault("raw_status", deepcopy(value["status"]))
            value["status"] = _RESEARCH_OBSERVATION
        for key, nested in value.items():
            if str(key).startswith("raw_"):
                continue
            _neutralize_common(nested)
    elif isinstance(value, list):
        for nested in value:
            _neutralize_common(nested)
    elif isinstance(value, tuple):
        for nested in value:
            _neutralize_common(nested)


def _project_rows(rows: Any) -> tuple[list[Any], bool]:
    if rows is None:
        return [], False
    if not isinstance(rows, list):
        return [], True
    projected_rows: list[Any] = []
    malformed = False
    for row in rows:
        if not isinstance(row, dict):
            malformed = True
            continue
        item = deepcopy(row)
        if "strategy_id" in item:
            item["raw_strategy_id"] = deepcopy(item["strategy_id"])
        if "strategy_name" in item:
            item["raw_strategy_name"] = deepcopy(item["strategy_name"])
        if "risk" in item:
            item["raw_risk"] = deepcopy(item["risk"])
        item["strategy_id"] = _STRATEGY_OBSERVATION
        item["strategy_name"] = _STRATEGY_LABEL
        item["risk"] = _RISK_LABEL
        item["action"] = _SAFE_ACTION
        item["scan_basis"] = "\u5f00\u53d1\u671f\u89c4\u5219\u626b\u63cf \u00b7 \u975e\u4ea4\u6613\u4fe1\u53f7"
        projected_rows.append(item)
    return projected_rows, malformed


def _invalid_projection(error: str = "invalid_research_payload") -> dict[str, Any]:
    return {
        "ok": False,
        "projection_schema_version": MARKET_SCANNER_RESEARCH_PROJECTION_SCHEMA,
        "status": "UNKNOWN",
        "research_only": True,
        "descriptive_only": True,
        "planning_only": True,
        "direction_signal_allowed": False,
        "parameter_selection_allowed": False,
        "performance_claim_allowed": False,
        "profitability_proven": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "safe_action": _SAFE_ACTION,
        "summary": "\u626b\u63cf\u8bc1\u636e\u672a\u6838\u9a8c",
        "error": error,
    }


def build_market_scanner_projection(payload: Any) -> dict[str, Any]:
    """Project the direct scanner response as descriptive research evidence."""

    if not isinstance(payload, dict):
        return _invalid_projection()

    projected, paths = sanitize_authority_claims(payload, path="payload")
    _neutralize_common(projected)
    rows, malformed_rows = _project_rows(projected.get("rows"))
    if malformed_rows:
        return _invalid_projection("invalid_scanner_rows")

    result = dict(projected)
    if "summary" in result:
        result["raw_summary"] = deepcopy(result["summary"])
    result.update(
        {
            "projection_schema_version": MARKET_SCANNER_RESEARCH_PROJECTION_SCHEMA,
            "research_only": True,
            "descriptive_only": True,
            "planning_only": True,
            "direction_signal_allowed": False,
            "parameter_selection_allowed": False,
            "performance_claim_allowed": False,
            "profitability_proven": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "live_trading_allowed": False,
            "summary": _SUMMARY,
            "summary_basis": "\u5f00\u53d1\u671f\u626b\u63cf\u7ed3\u679c\uff1b\u53ea\u4f5c\u89c2\u5bdf\uff0c\u4e0d\u9009\u53c2\u3001\u4e0d\u4e0b\u5355",
            "safe_action": _SAFE_ACTION,
            "rows": rows,
        }
    )
    if paths:
        result["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    else:
        result.pop("authority_sanitized_paths", None)
    if authority_violations(result):
        return _invalid_projection("authority_projection_postcondition_failed")
    return result
