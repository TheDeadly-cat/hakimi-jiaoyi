from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from .strategy_correlation_cluster_projection import build_correlation_cluster_public_summary


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


def _finite_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return value


def _sanitize(value: Any, *, path: str = "strategy_lab") -> tuple[Any, list[str]]:
    """Deep-copy a lab report and fail closed on any known authority field."""

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


def _project_planning_row(row: Any) -> Any:
    if not isinstance(row, dict):
        return deepcopy(row)
    result = deepcopy(row)
    planning = {
        "position_pct": _finite_number(row.get("position_pct")),
        "take_profit": _finite_number(row.get("take_profit")),
        "stop_loss": _finite_number(row.get("stop_loss")),
        "score": _finite_number(row.get("score")),
    }
    result["raw_position_pct"] = planning["position_pct"]
    result["raw_take_profit"] = planning["take_profit"]
    result["raw_stop_loss"] = planning["stop_loss"]
    result["raw_score"] = planning["score"]
    result["planning_candidate"] = planning
    result["planning_only"] = True
    result["parameter_selection_allowed"] = False
    result["apply_to_risk_form_allowed"] = False
    # Keep the legacy keys present for consumers, but make operational reads fail
    # closed. The descriptive values live under planning_candidate instead.
    result["position_pct"] = None
    result["take_profit"] = None
    result["stop_loss"] = None
    result["score"] = None
    result["score_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_RANKING"
    result["evidence_status"] = "RESEARCH_OBSERVE"
    return result


def build_strategy_lab_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Expose strategy-lab output as a descriptive planning artifact only."""

    source = report if isinstance(report, dict) else {}
    correlation_cluster_summary = build_correlation_cluster_public_summary(
        source.get("correlation_cluster_replayed_gate")
    )
    projected, sanitized_paths = _sanitize(source)
    payload = dict(projected)
    payload.pop("correlation_cluster_replayed_gate", None)
    payload["correlation_cluster_summary"] = correlation_cluster_summary
    payload["rows"] = [
        _project_planning_row(row)
        for row in (projected.get("rows") if isinstance(projected.get("rows"), list) else [])
    ]
    payload["lab_schema"] = "strategy-lab-research-projection-v1"
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["planning_only"] = True
    payload["development_heuristic_only"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["apply_to_risk_form_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["paper_ready"] = False
    payload["live_order_allowed"] = False
    payload["live_ready"] = False
    payload["live_trading_hard_block"] = True
    # The interactive lab is intentionally not a substitute for the frozen
    # research runner.  Keep this boundary explicit in the response so a
    # consumer cannot mistake a development heuristic score for plateau,
    # cost-stress, or chronological-slice evidence.
    payload["evidence_contract"] = {
        "schema_version": "strategy-lab-evidence-boundary-v1",
        "mode": "DEVELOPMENT_HEURISTIC_PLANNING_ONLY",
        "parameter_stability_status": "NOT_CONNECTED",
        "cost_sensitivity_status": "NOT_CONNECTED",
        "chronological_slice_status": "NOT_CONNECTED",
        "research_report_source": "FROZEN_RESEARCH_REPORT_NOT_CONNECTED",
        "interpretation": "DESCRIPTIVE_PLANNING_ONLY",
        "research_only": True,
        "descriptive_only": True,
        "development_heuristic_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["interpretation"] = (
        "DEVELOPMENT_HEURISTIC_PLANNING_ONLY; not parameter selection, "
        "profitability proof, paper authorization, or live authorization"
    )
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    return payload


__all__ = ["build_strategy_lab_projection"]


# Consumer-first uncertainty projection. The existing projection remains the source
# for every legacy field; this wrapper only adds a redacted summary and removes
# raw uncertainty sidecars before a public payload can leave the service layer.
from exchange_terminal.services.strategy_correlation_uncertainty_projection import (
    build_strategy_correlation_uncertainty_public_summary,
)

_build_strategy_lab_projection_without_uncertainty = build_strategy_lab_projection


def _drop_raw_correlation_uncertainty(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_raw_correlation_uncertainty(item)
            for key, item in value.items()
            if key != "correlation_uncertainty_audit"
        }
    if isinstance(value, list):
        return [_drop_raw_correlation_uncertainty(item) for item in value]
    return value


def build_strategy_lab_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    source_audit = (
        report.get("correlation_uncertainty_audit")
        if isinstance(report, dict)
        else None
    )
    legacy_projection = _build_strategy_lab_projection_without_uncertainty(report)
    public_projection = _drop_raw_correlation_uncertainty(legacy_projection)
    public_projection["correlation_uncertainty_summary"] = (
        build_strategy_correlation_uncertainty_public_summary(source_audit)
    )
    return public_projection


# Consumer-first multiplicity projection. Protocol-v5 remains owned by the
# nested research runner; this wrapper only emits a redacted aggregate and
# recursively removes raw family evidence from the public strategy-lab payload.
from exchange_terminal.services.strategy_correlation_multiplicity_projection import (
    build_strategy_correlation_multiplicity_public_summary,
)

_build_strategy_lab_projection_without_multiplicity = build_strategy_lab_projection
_RAW_MULTIPLICITY_FIELDS = {
    "correlation_multiplicity_evidence",
    "multiplicity_evidence",
    "multiplicity_audit",
    "family_binding_assessment",
}


def _drop_raw_correlation_multiplicity(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_raw_correlation_multiplicity(item)
            for key, item in value.items()
            if key not in _RAW_MULTIPLICITY_FIELDS
        }
    if isinstance(value, list):
        return [_drop_raw_correlation_multiplicity(item) for item in value]
    return value


def build_strategy_lab_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    governance = (
        source.get("research_governance")
        if isinstance(source.get("research_governance"), dict)
        else {}
    )
    protocol = (
        governance.get("protocol")
        if isinstance(governance.get("protocol"), dict)
        else {}
    )
    legacy_source = (
        None
        if source.get("schema_version") == 16
        else report
    )
    legacy_projection = _build_strategy_lab_projection_without_multiplicity(
        legacy_source
    )
    public_projection = _drop_raw_correlation_multiplicity(legacy_projection)
    public_projection["correlation_multiplicity_summary"] = (
        build_strategy_correlation_multiplicity_public_summary(
            source.get("correlation_multiplicity_evidence"),
            protocol=protocol,
            report_schema_version=source.get("schema_version"),
        )
    )
    return public_projection
