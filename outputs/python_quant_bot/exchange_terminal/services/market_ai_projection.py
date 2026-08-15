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

_DIRECTION_FIELDS = {"direction", "preferred_direction", "final_decision"}
_PRICE_FIELDS = {
    "take_profit",
    "stop_loss",
    "long_take_profit",
    "long_stop_loss",
    "short_take_profit",
    "short_stop_loss",
}
_STATUS_FIELDS = {"status", "severity", "analysis_status", "level"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text or fallback


def _research_direction(value: Any) -> str:
    raw = _normalise(value, "WAIT")
    if raw in {"LONG", "BUY", "ADD", "OPEN", "OPEN_SMALL"}:
        return "RESEARCH_LONG"
    if raw in {"SHORT", "SELL", "EXIT", "COVER"}:
        return "RESEARCH_SHORT"
    if raw in {"WAIT", "WATCH", "HOLD", "NEUTRAL"}:
        return "RESEARCH_NEUTRAL"
    return "RESEARCH_UNCERTAIN"


def _research_direction_label(value: Any) -> str:
    projected = _research_direction(value)
    return {
        "RESEARCH_LONG": "研究偏多 · 非订单",
        "RESEARCH_SHORT": "研究偏空 · 非订单",
        "RESEARCH_NEUTRAL": "研究等待 · 非订单",
    }.get(projected, "研究方向待核验 · 非订单")


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in {"HIGH", "CRITICAL", "ERROR", "FAILED", "BLOCKED"}:
        return "RESEARCH_BLOCKED"
    if raw in {"MEDIUM", "PARTIAL", "PENDING", "RUNNING"}:
        return "RESEARCH_REVIEW"
    if raw in {"LOW", "OK", "PASS", "READY", "COMPLETE", "DONE"}:
        return "RESEARCH_OBSERVE"
    return "RESEARCH_OBSERVE"


def _sanitize(value: Any, *, path: str = "market_ai") -> tuple[Any, list[str]]:
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
            if key in _DIRECTION_FIELDS:
                clean[f"raw_{key}"] = deepcopy(nested)
                clean[key] = _research_direction(nested)
                paths.append(nested_path)
                continue
            if key in _PRICE_FIELDS:
                clean[f"planning_{key}"] = deepcopy(nested)
                clean[key] = None
                if nested is not None:
                    paths.append(nested_path)
                continue
            if key in _STATUS_FIELDS:
                clean[f"raw_{key}"] = _normalise(nested)
                clean[key] = _research_status(nested)
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


def _project_report(report: Any, projected: Any = None) -> dict[str, Any]:
    raw = report if isinstance(report, dict) else {}
    result = dict(projected) if isinstance(projected, dict) else deepcopy(raw)
    for key in _DIRECTION_FIELDS:
        if key in raw:
            result[f"raw_{key}"] = deepcopy(raw[key])
            result[key] = _research_direction(raw[key])
    if "preferred_direction" in raw:
        result["direction_label"] = _research_direction_label(raw["preferred_direction"])
    for key in _PRICE_FIELDS:
        if key in raw:
            result[f"planning_{key}"] = deepcopy(raw[key])
            result[key] = None
    result["probability_semantics"] = "UNCALIBRATED_MODEL_ESTIMATE"
    result["price_semantics"] = "DEVELOPMENT_PLAN_NOT_ORDER"
    result["safe_action"] = "观察 / 仅研究 · 模拟未授权 · 实盘永久硬锁"
    result["raw_safe_action"] = deepcopy(raw.get("safe_action"))
    result["analysis_only"] = True
    result["planning_only"] = True
    result["selection_allowed"] = False
    result["order_allowed"] = False
    return result


def build_market_ai_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source)
    payload = dict(projected) if isinstance(projected, dict) else {}
    source_analysis = source.get("analysis") if isinstance(source.get("analysis"), dict) else {}
    projected_analysis = projected.get("analysis") if isinstance(projected.get("analysis"), dict) else {}
    analysis: dict[str, Any] = {}
    for key, raw_report in source_analysis.items():
        projected_report = projected_analysis.get(key) if isinstance(projected_analysis, dict) else None
        analysis[key] = _project_report(raw_report, projected_report)
    payload["analysis"] = analysis
    if isinstance(source.get("local"), dict):
        local_raw = source["local"]
        local_projected = payload.get("local") if isinstance(payload.get("local"), dict) else {}
        local = dict(local_projected)
        for key in ("long_plan", "short_plan"):
            local[key] = _project_report(local_raw.get(key), local_projected.get(key))
        local["preferred"] = _research_direction(local_raw.get("preferred"))
        local["direction_label"] = _research_direction_label(local_raw.get("preferred"))
        local["safe_action"] = "观察 / 仅研究 · 模拟未授权 · 实盘永久硬锁"
        local["analysis_only"] = True
        local["planning_only"] = True
        payload["local"] = local
    payload["analysis_schema"] = "market-ai-research-projection-v1"
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
        "DESCRIPTIVE_MARKET_AI_ONLY; directional estimates, win rates and price plans "
        "are uncalibrated research evidence, not orders or profitability proof"
    )
    if paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    return payload


__all__ = ["build_market_ai_projection"]
