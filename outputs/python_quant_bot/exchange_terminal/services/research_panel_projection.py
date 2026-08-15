from __future__ import annotations

from copy import deepcopy
from typing import Any


RESEARCH_PANEL_PROJECTION_SCHEMA = "research-panel-research-projection-v1"
_SAFE_ACTION = "观察 / 仅研究 / 非订单"
_RESEARCH_OBSERVATION = "研究观察"
_RESEARCH_VERIFIED = "研究证据已核对"

_AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "live_trading_allowed",
    "live_trading_enabled",
    "order_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_authorized",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
}

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


def _normalise_status(value: Any) -> str:
    return str(value or "").strip().upper()


def _sanitize(value: Any, *, path: str) -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        clean: dict[Any, Any] = {}
        paths: list[str] = []
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS:
                clean[key] = False
                if nested is not False:
                    paths.append(nested_path)
                continue
            if key == "tone":
                clean["raw_tone"] = deepcopy(nested)
                clean[key] = "flat"
                if nested != "flat":
                    paths.append(nested_path)
                continue
            if key in {"direction", "preferred", "stance"}:
                clean[f"raw_{key}"] = deepcopy(nested)
                clean[key] = _RESEARCH_OBSERVATION
                if nested not in (None, "", _RESEARCH_OBSERVATION):
                    paths.append(nested_path)
                continue
            if key == "action":
                raw_action = str(nested or "").strip().upper()
                if raw_action in {"BUY", "SELL", "LONG", "SHORT", "OPEN", "CLOSE", "ADD", "EXIT"}:
                    clean["raw_action"] = raw_action
                    clean[key] = _SAFE_ACTION
                    paths.append(nested_path)
                    continue
            if key == "status" and _normalise_status(nested) in _VISIBLE_READY_STATUSES:
                clean["raw_status"] = deepcopy(nested)
                clean[key] = _RESEARCH_VERIFIED
                paths.append(nested_path)
                continue
            projected, nested_paths = _sanitize(nested, path=nested_path)
            clean[key] = projected
            paths.extend(nested_paths)
        return clean, paths
    if isinstance(value, list):
        clean_items: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, nested_paths = _sanitize(nested, path=f"{path}[{index}]")
            clean_items.append(projected)
            paths.extend(nested_paths)
        return clean_items, paths
    if isinstance(value, tuple):
        projected, paths = _sanitize(list(value), path=path)
        return tuple(projected), paths
    return deepcopy(value), []


def _invalid_projection() -> dict[str, Any]:
    return {
        "ok": False,
        "status": "UNKNOWN",
        "projection_schema_version": RESEARCH_PANEL_PROJECTION_SCHEMA,
        "research_only": True,
        "descriptive_only": True,
        "planning_only": True,
        "read_only": True,
        "direction_signal_allowed": False,
        "parameter_selection_allowed": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "safe_action": _SAFE_ACTION,
    }


def build_research_panel_projection(payload: Any) -> dict[str, Any]:
    """Project the research panel without direction or authority promotion."""

    if not isinstance(payload, dict):
        return _invalid_projection()
    projected, paths = _sanitize(payload, path="research_panel")
    result = dict(projected)
    result.update(
        {
            "projection_schema_version": RESEARCH_PANEL_PROJECTION_SCHEMA,
            "research_only": True,
            "descriptive_only": True,
            "planning_only": True,
            "read_only": True,
            "direction_signal_allowed": False,
            "parameter_selection_allowed": False,
            "profitability_proven": False,
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
    return result
