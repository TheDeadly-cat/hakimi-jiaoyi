from __future__ import annotations

from copy import deepcopy
from typing import Any


_AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
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
    "trade_allowed",
}

_VERIFIED_STATUSES = {
    "PASS",
    "READY",
    "DONE",
    "COMPLETE",
    "COMPLETED",
    "SUCCESS",
    "SUCCEEDED",
}
_ACTIVE_STATUSES = {"RUNNING", "ACTIVE", "IN_PROGRESS"}
_BLOCKED_STATUSES = {
    "BLOCK",
    "BLOCKED",
    "ERROR",
    "FAILED",
    "REJECTED",
    "UNSAFE",
}


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


def _research_action(value: Any) -> str:
    raw = _normalise(value, "WAIT")
    if raw in {"BUY", "ADD", "LONG", "OPEN", "OPEN_SMALL"}:
        return "研究假设：偏多 · 非订单"
    if raw in {"SELL", "SHORT", "EXIT", "COVER"}:
        return "研究假设：偏空 · 非订单"
    if raw in {"HALT", "BLOCK"}:
        return "研究结论：阻断"
    if raw in {"WAIT", "WATCH", "HOLD"}:
        return "研究结论：继续观察"
    return "研究结论：待核验"


def _sanitize(value: Any, *, path: str = "strategy_compare") -> tuple[Any, list[str]]:
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
            if key in {"status", "level", "mission_status"}:
                raw_status = _normalise(nested)
                clean[f"raw_{key}"] = raw_status
                clean[key] = _research_status(raw_status)
                continue
            projected, projected_paths = _sanitize(nested, path=nested_path)
            clean[key] = projected
            paths.extend(projected_paths)
        return clean, paths
    if isinstance(value, list):
        clean_items: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, projected_paths = _sanitize(
                nested,
                path=f"{path}[{index}]",
            )
            clean_items.append(projected)
            paths.extend(projected_paths)
        return clean_items, paths
    if isinstance(value, tuple):
        projected, paths = _sanitize(list(value), path=path)
        return tuple(projected), paths
    return deepcopy(value), []


def _project_row(row: Any) -> Any:
    if not isinstance(row, dict):
        return deepcopy(row)
    result = deepcopy(row)
    raw_action = _normalise(row.get("action"), "HOLD")
    raw_reason = str(row.get("reason") or "").strip()
    raw_enabled = str(row.get("enabled_condition") or "").strip()
    raw_stop = str(row.get("stop_condition") or "").strip()
    result["raw_action"] = raw_action
    result["action"] = _research_action(raw_action)
    result["raw_reason"] = raw_reason
    result["reason"] = (
        f"研究说明：{raw_reason} · 非订单"
        if raw_reason
        else "研究说明待核验 · 非订单"
    )
    result["raw_enabled_condition"] = raw_enabled
    result["enabled_condition"] = "仅作开发期观察；需冻结证据、成本与自然前向复核"
    result["raw_stop_condition"] = raw_stop
    result["stop_condition"] = "研究失效条件待核验；不构成交易规则"
    result["evidence_status"] = "RESEARCH_OBSERVE"
    result["score_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_SELECTION"
    result["probability_semantics"] = "UNCALIBRATED_MODEL_ESTIMATE"
    result["selection_allowed"] = False
    result["order_allowed"] = False
    return result


def build_strategy_compare_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Keep strategy comparison descriptive and fail closed for API consumers."""

    source = report if isinstance(report, dict) else {}
    projected, sanitized_paths = _sanitize(source)
    payload = dict(projected)
    payload["rows"] = [
        _project_row(row)
        for row in (projected.get("rows") if isinstance(projected.get("rows"), list) else [])
    ]
    payload["comparison_schema"] = "strategy-compare-research-projection-v1"
    payload["comparison_only"] = True
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["development_heuristic_only"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["selection_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["paper_ready"] = False
    payload["live_order_allowed"] = False
    payload["live_ready"] = False
    payload["live_trading_hard_block"] = True
    payload["ranking_semantics"] = "DEVELOPMENT_HEURISTIC_ORDER_NOT_SELECTION"
    payload["interpretation"] = (
        "DESCRIPTIVE_STRATEGY_COMPARISON_ONLY; scores and probabilities are "
        "uncalibrated research evidence, not parameter selection or order intent"
    )
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    return payload


__all__ = ["build_strategy_compare_projection"]
