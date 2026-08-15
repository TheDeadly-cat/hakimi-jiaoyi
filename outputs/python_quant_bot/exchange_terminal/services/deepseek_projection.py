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
_DIRECTION_FIELDS = {
    "action",
    "decision",
    "direction",
    "final_decision",
    "preferred",
    "preferred_direction",
    "signal",
}
_PRICE_FIELDS = {
    "take_profit",
    "stop_loss",
    "long_take_profit",
    "long_stop_loss",
    "short_take_profit",
    "short_stop_loss",
    "deepseek_take_profit",
    "deepseek_stop_loss",
    "suggested_take_profit",
    "suggested_stop_loss",
    "entry_price",
    "target_price",
    "invalidation_price",
    "entry_hint",
    "take_profit_hint",
    "stop_loss_hint",
}
_UNCALIBRATED_FIELDS = {
    "confidence",
    "confidence_pct",
    "position_hint_pct",
}
_STATUS_FIELDS = {"status", "severity", "analysis_status", "level"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return text or fallback


def _research_direction(value: Any) -> str:
    raw = _normalise(value, "NEUTRAL")
    if raw in {"LONG", "BUY", "ADD", "OPEN", "OPEN_SMALL"}:
        return "RESEARCH_LONG"
    if raw in {"SHORT", "SELL", "EXIT", "COVER"}:
        return "RESEARCH_SHORT"
    if raw in {"WAIT", "WATCH", "HOLD", "NEUTRAL", "PAPER_ONLY"}:
        return "RESEARCH_NEUTRAL"
    return "RESEARCH_UNCERTAIN"


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in {"ERROR", "FAILED", "BLOCKED", "CRITICAL"}:
        return "RESEARCH_BLOCKED"
    if raw in {"WAIT", "PENDING", "RUNNING"}:
        return "RESEARCH_REVIEW"
    return "RESEARCH_OBSERVE"


def _research_action(value: Any) -> str:
    raw = _normalise(value)
    if raw in {"ALLOW_LIVE", "LIVE", "EXECUTE", "ORDER", "ALLOW_STRATEGY_EVALUATION"}:
        return "RESEARCH_REVIEW_REQUIRED"
    if raw in {"PAPER_ONLY", "WATCH", "WAIT", "OBSERVE"}:
        return "RESEARCH_OBSERVE"
    return "RESEARCH_REVIEW_REQUIRED" if raw != "UNKNOWN" else "RESEARCH_UNCERTAIN"


def _sanitize(value: Any, *, path: str = "deepseek") -> tuple[Any, list[str]]:
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
            if key in _UNCALIBRATED_FIELDS:
                clean[f"raw_{key}"] = deepcopy(nested)
                clean[key] = None
                if nested is not None:
                    paths.append(nested_path)
                continue
            if key == "actionability":
                clean["raw_actionability"] = deepcopy(nested)
                clean[key] = _research_action(nested)
                paths.append(nested_path)
                continue
            if key in _STATUS_FIELDS:
                clean[f"raw_{key}"] = deepcopy(nested)
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


def build_deepseek_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source)
    payload = dict(projected) if isinstance(projected, dict) else {}
    payload["research_projection_schema"] = "deepseek-research-projection-v1"
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["planning_only"] = True
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
    if "safe_action" in source:
        payload["raw_safe_action"] = deepcopy(source.get("safe_action"))
    payload["safe_action"] = "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK"
    payload["interpretation"] = (
        "DESCRIPTIVE_DEEPSEEK_ONLY; direction, confidence and opportunity levels are uncalibrated research evidence, "
        "not orders, permissions or profitability proof"
    )
    if paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    return payload


__all__ = ["build_deepseek_projection"]
