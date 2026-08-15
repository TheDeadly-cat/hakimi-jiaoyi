from __future__ import annotations

from copy import deepcopy
from typing import Any


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
    "mission_authorized",
    "order_allowed",
    "paper_activation_allowed",
    "paper_authorized",
    "paper_armed",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "runtime_mutations_allowed",
    "selection_allowed",
    "trade_allowed",
}

_STATUS_FIELDS = {"status", "level", "mission_status", "risk_status"}
_PRICE_FIELDS = {
    "take_profit",
    "stop_loss",
    "suggested_take_profit",
    "suggested_stop_loss",
}
_VERIFIED_STATUSES = {
    "PASS",
    "READY",
    "DONE",
    "ONLINE",
    "RUNNING",
    "SUCCESS",
    "SUCCEEDED",
}
_BLOCKED_STATUSES = {
    "BLOCK",
    "BLOCKED",
    "ERROR",
    "FAILED",
    "PROTECTED",
    "REJECTED",
    "UNSAFE",
}
_ACTIVE_STATUSES = {"ACTIVE", "IN_PROGRESS", "PARTIAL"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text or fallback


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in _BLOCKED_STATUSES:
        return "RESEARCH_BLOCKED"
    if raw in _ACTIVE_STATUSES:
        return "RESEARCH_REVIEW"
    if raw in _VERIFIED_STATUSES:
        return "RESEARCH_VERIFIED"
    return "RESEARCH_OBSERVE"


def _research_direction(value: Any) -> str:
    raw = _normalise(value, "UNKNOWN")
    if raw == "LONG":
        return "RESEARCH_LONG"
    if raw == "SHORT":
        return "RESEARCH_SHORT"
    return "RESEARCH_NEUTRAL"


def _research_direction_label(value: Any) -> str:
    raw = _normalise(value, "UNKNOWN")
    if raw == "LONG":
        return "研究偏多 · 非订单"
    if raw == "SHORT":
        return "研究偏空 · 非订单"
    return "方向未形成 · 非订单"


def _research_action(value: Any) -> str:
    raw = _normalise(value, "HOLD")
    if raw in {"BUY", "ADD", "LONG", "OPEN", "OPEN_SMALL"}:
        return "研究假设：偏多 · 非订单"
    if raw in {"SELL", "SHORT", "EXIT", "COVER"}:
        return "研究假设：偏空 · 非订单"
    if raw in {"HALT", "BLOCK"}:
        return "研究结论：阻断"
    if raw in {"WAIT", "WATCH", "HOLD"}:
        return "研究结论：继续观察"
    return "研究结论：待核验"


def _sanitize(value: Any, *, path: str = "strategy_analysis") -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        clean: dict[Any, Any] = {}
        paths: list[str] = []
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS:
                clean[key] = False
                if nested is not False:
                    clean[f"raw_{key}"] = deepcopy(nested)
                    paths.append(nested_path)
                continue
            if key in _PRICE_FIELDS:
                clean[key] = None
                if nested is not None:
                    clean[f"raw_{key}"] = deepcopy(nested)
                    paths.append(nested_path)
                continue
            if key in _STATUS_FIELDS:
                raw_status = _normalise(nested)
                clean[f"raw_{key}"] = raw_status
                clean[key] = _research_status(raw_status)
                continue
            if key == "direction":
                raw_direction = _normalise(nested)
                clean["raw_direction"] = raw_direction
                clean["direction"] = _research_direction(raw_direction)
                paths.append(nested_path)
                continue
            if key == "direction_label":
                raw_label = str(nested or "").strip()
                clean["raw_direction_label"] = raw_label
                clean["direction_label"] = _research_direction_label(
                    value.get("direction") if isinstance(value, dict) else "UNKNOWN"
                )
                paths.append(nested_path)
                continue
            if key == "action":
                raw_action = _normalise(nested, "HOLD")
                clean["raw_action"] = raw_action
                clean["action"] = _research_action(raw_action)
                paths.append(nested_path)
                continue
            if key == "reason":
                raw_reason = str(nested or "").strip()
                clean["raw_reason"] = raw_reason
                clean["reason"] = (
                    f"研究说明：{raw_reason} · 非订单"
                    if raw_reason
                    else "研究说明待核验 · 非订单"
                )
                continue
            projected, projected_paths = _sanitize(nested, path=nested_path)
            clean[key] = projected
            paths.extend(projected_paths)
        return clean, paths
    if isinstance(value, list):
        clean_items: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, projected_paths = _sanitize(nested, path=f"{path}[{index}]")
            clean_items.append(projected)
            paths.extend(projected_paths)
        return clean_items, paths
    if isinstance(value, tuple):
        projected, paths = _sanitize(list(value), path=path)
        return tuple(projected), paths
    return deepcopy(value), []


def _flags(payload: dict[str, Any], *, sanitized_paths: list[str]) -> dict[str, Any]:
    payload["analysis_schema"] = "strategy-analysis-research-projection-v1"
    payload["analysis_only"] = True
    payload["planning_only"] = True
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["development_heuristic_only"] = True
    payload["uncalibrated_probability"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["selection_allowed"] = False
    payload["order_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["paper_ready"] = False
    payload["live_order_allowed"] = False
    payload["live_ready"] = False
    payload["live_trading_hard_block"] = True
    payload["interpretation"] = (
        "DESCRIPTIVE_STRATEGY_ANALYSIS_ONLY; price plans and probabilities are "
        "uncalibrated development evidence, not orders, selection, profitability proof, or authorization"
    )
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    return payload


def _project_plan(source: Any, projected: Any = None) -> dict[str, Any]:
    raw = source if isinstance(source, dict) else {}
    result = deepcopy(projected if isinstance(projected, dict) else raw)
    raw_direction = _normalise(raw.get("direction"), "UNKNOWN")
    result["raw_direction"] = raw_direction
    result["direction"] = _research_direction(raw_direction)
    result["raw_direction_label"] = str(raw.get("direction_label") or "")
    result["direction_label"] = _research_direction_label(raw_direction)
    for key in _PRICE_FIELDS:
        raw_value = raw.get(key)
        result[f"planning_{key}"] = deepcopy(raw_value)
        result[key] = None
    result["planning_only"] = True
    result["value_semantics"] = "DEVELOPMENT_PRICE_PLAN_NOT_ORDER"
    result["probability_semantics"] = "UNCALIBRATED_MODEL_ESTIMATE"
    result["selection_allowed"] = False
    result["order_allowed"] = False
    return result


def build_strategy_analysis_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source)
    payload = dict(projected) if isinstance(projected, dict) else {}
    source_analysis = source.get("analysis") if isinstance(source.get("analysis"), dict) else {}
    projected_analysis = projected.get("analysis") if isinstance(projected.get("analysis"), dict) else {}
    analysis = dict(projected_analysis)
    raw_direction = _normalise(source_analysis.get("direction"), "UNKNOWN")
    analysis["raw_direction"] = raw_direction
    analysis["direction"] = _research_direction(raw_direction)
    analysis["raw_direction_label"] = str(source_analysis.get("direction_label") or "")
    analysis["direction_label"] = _research_direction_label(raw_direction)
    for key in _PRICE_FIELDS:
        raw_value = source_analysis.get(key)
        analysis[f"planning_{key}"] = deepcopy(raw_value)
        analysis[key] = None
    source_plans = {
        "long_plan": source_analysis.get("long_plan"),
        "short_plan": source_analysis.get("short_plan"),
    }
    projected_plans = projected_analysis.get("long_plan"), projected_analysis.get("short_plan")
    for (key, raw_plan), projected_plan in zip(source_plans.items(), projected_plans):
        analysis[key] = _project_plan(raw_plan, projected_plan)
    if isinstance(analysis.get("risk_config"), dict):
        analysis["risk_config"]["planning_only"] = True
        analysis["risk_config"]["execution_allowed"] = False
        analysis["risk_config"]["paper_authorized"] = False
        analysis["risk_config"]["live_order_allowed"] = False
        analysis["risk_config"]["config_semantics"] = "RESEARCH_PLANNING_INPUT_ONLY"
    analysis["planning_only"] = True
    analysis["analysis_only"] = True
    analysis["probability_semantics"] = "UNCALIBRATED_MODEL_ESTIMATE"
    analysis["value_semantics"] = "DEVELOPMENT_PRICE_PLAN_NOT_ORDER"
    analysis["selection_allowed"] = False
    analysis["order_allowed"] = False
    payload["analysis"] = analysis
    _flags(payload, sanitized_paths=paths)
    return payload


__all__ = ["build_strategy_analysis_projection"]
