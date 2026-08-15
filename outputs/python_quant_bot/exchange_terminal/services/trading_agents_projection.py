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
    "direction",
    "preferred",
    "preferred_direction",
    "final_decision",
    "decision",
    "signal",
    "stance",
}
_PRICE_FIELDS = {
    "entry_price",
    "entry_hint",
    "take_profit",
    "stop_loss",
    "long_take_profit",
    "long_stop_loss",
    "short_take_profit",
    "short_stop_loss",
    "target_price",
    "invalidation_price",
}
_UNCALIBRATED_FIELDS = {
    "confidence",
    "confidence_pct",
    "long_win_rate_pct",
    "short_win_rate_pct",
    "win_rate_pct",
    "position_hint_pct",
    "position_size",
    "allocation_pct",
}
_STATUS_FIELDS = {"status", "severity", "analysis_status", "level"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return text or fallback


def _research_direction(value: Any) -> str:
    raw = _normalise(value, "WAIT")
    if raw in {"LONG", "BUY", "ADD", "OPEN", "OPEN_SMALL", "LONG_OBSERVE"}:
        return "RESEARCH_LONG"
    if raw in {"SHORT", "SELL", "EXIT", "COVER", "SHORT_OBSERVE"}:
        return "RESEARCH_SHORT"
    if raw in {"WAIT", "WATCH", "HOLD", "NEUTRAL", "PAPER_ONLY", "FLAT"}:
        return "RESEARCH_NEUTRAL"
    return "RESEARCH_UNCERTAIN"


def _direction_label(value: Any) -> str:
    projected = _research_direction(value)
    return {
        "RESEARCH_LONG": "RESEARCH_LONG · DESCRIPTIVE_ONLY",
        "RESEARCH_SHORT": "RESEARCH_SHORT · DESCRIPTIVE_ONLY",
        "RESEARCH_NEUTRAL": "RESEARCH_NEUTRAL · DESCRIPTIVE_ONLY",
    }.get(projected, "RESEARCH_UNCERTAIN · DESCRIPTIVE_ONLY")


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in {"ERROR", "FAILED", "BLOCKED", "CRITICAL"}:
        return "RESEARCH_BLOCKED"
    if raw in {"WAIT", "PENDING", "RUNNING", "THINK", "QUEUED"}:
        return "RESEARCH_REVIEW"
    return "RESEARCH_OBSERVE"


def _sanitize(value: Any, *, path: str = "trading_agents") -> tuple[Any, list[str]]:
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
                clean.setdefault("direction_label", _direction_label(nested))
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


def _apply_root_contract(payload: dict[str, Any], source: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    payload["research_projection_schema"] = "trading-agents-research-projection-v1"
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
    payload["probability_semantics"] = "UNCALIBRATED_RESEARCH_WEIGHT_ONLY"
    payload["price_semantics"] = "PLANNING_LEVELS_NOT_ORDERS"
    if "safe_action" in source:
        payload["raw_safe_action"] = deepcopy(source.get("safe_action"))
    payload["safe_action"] = "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK"
    payload["interpretation"] = (
        "DESCRIPTIVE_TRADING_AGENTS_ONLY; stances, confidence and price levels are uncalibrated research evidence, "
        "not orders, permissions or profitability proof"
    )
    if paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    return payload


def build_trading_agents_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source)
    payload = dict(projected) if isinstance(projected, dict) else {}
    final = payload.get("final") if isinstance(payload.get("final"), dict) else None
    raw_final = source.get("final") if isinstance(source.get("final"), dict) else None
    if final is not None and raw_final is not None:
        final["decision_label"] = _direction_label(raw_final.get("decision"))
        if "safe_action" in raw_final:
            final["raw_safe_action"] = deepcopy(raw_final.get("safe_action"))
        final["safe_action"] = "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK"
        final["probability_semantics"] = "UNCALIBRATED_RESEARCH_WEIGHT_ONLY"
        final["price_semantics"] = "PLANNING_LEVELS_NOT_ORDERS"
    for collection_key in ("agents", "debate", "meeting_transcript", "role_assignments"):
        rows = payload.get(collection_key)
        if not isinstance(rows, list):
            continue
        raw_rows = source.get(collection_key) if isinstance(source.get(collection_key), list) else []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            raw_row = raw_rows[index] if index < len(raw_rows) and isinstance(raw_rows[index], dict) else row
            if any(key in raw_row for key in _DIRECTION_FIELDS):
                raw_direction = next((raw_row[key] for key in _DIRECTION_FIELDS if key in raw_row), None)
                row["direction_label"] = _direction_label(raw_direction)
            if "confidence_pct" in raw_row or "win_rate_pct" in raw_row:
                row["probability_semantics"] = "UNCALIBRATED_RESEARCH_WEIGHT_ONLY"
    return _apply_root_contract(payload, source, paths)


def project_trading_agents_event(event: dict[str, Any] | None) -> dict[str, Any]:
    source = event if isinstance(event, dict) else {}
    projected, paths = _sanitize(source, path="trading_agents_event")
    payload = dict(projected) if isinstance(projected, dict) else {}
    if source.get("type") == "complete" and isinstance(source.get("data"), dict):
        projected_data = build_trading_agents_projection(source["data"])
        payload["data"] = projected_data
        paths.extend(
            str(item)
            for item in projected_data.get("authority_sanitized_paths", [])
            if str(item)
        )
        if "safe_action" in source:
            payload["raw_safe_action"] = deepcopy(source.get("safe_action"))
        payload["safe_action"] = "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK"
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["paper_authorized"] = False
    payload["live_order_allowed"] = False
    payload["live_trading_hard_block"] = True
    if paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    return payload


__all__ = ["build_trading_agents_projection", "project_trading_agents_event"]
