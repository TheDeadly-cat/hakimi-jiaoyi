from __future__ import annotations

from typing import Any

from .execution_authority import canonical_authority_key, sanitize_authority_claims


_LATEST_ORDER_FIELDS = (
    "order_id",
    "signal_id",
    "risk_request_id",
    "market_snapshot_id",
    "symbol",
    "side",
    "state",
    "updated_at",
)


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
_AUTHORITY_FIELD_KEYS = frozenset(
    canonical_authority_key(field) for field in _AUTHORITY_FIELDS
)


def _sanitize_authority(value: Any, *, path: str) -> tuple[Any, list[str]]:
    """Copy a component while preventing nested authority promotion."""

    return sanitize_authority_claims(
        value,
        path=path,
        authority_field_keys=_AUTHORITY_FIELD_KEYS,
    )


def _component_projection(
    value: Any,
    *,
    name: str,
) -> tuple[dict[str, Any], list[str]]:
    projected, paths = _sanitize_authority(value, path=name)
    if not isinstance(projected, dict):
        return {}, paths
    return projected, paths


def build_market_data_health_projection(
    health: dict[str, Any],
    *,
    runtime_read_only: bool,
    live_trading_hard_block: bool,
) -> dict[str, Any]:
    """Add the fixed authority envelope to an already-built health snapshot."""

    projected, paths = _component_projection(health, name="health")
    result = {
        **projected,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "read_only": runtime_read_only,
        "paper_authorized": False,
        "live_trading_hard_block": live_trading_hard_block is True,
        "live_order_allowed": False,
        "live_trading_allowed": False,
    }
    if paths:
        result["authority_sanitized_paths"] = list(dict.fromkeys(paths))
    else:
        result.pop("authority_sanitized_paths", None)
    return result


def _latest_order_projection(latest_order: dict[str, Any]) -> dict[str, Any]:
    if not latest_order:
        return {}
    return {field: latest_order.get(field) for field in _LATEST_ORDER_FIELDS}


def build_platform_control_center_projection(
    *,
    runtime_read_only: bool,
    live_trading_hard_block: bool,
    effective_paper_authorized: bool,
    default_strategy_id: str,
    paper: dict[str, Any],
    risk: dict[str, Any],
    pipeline: dict[str, Any],
    executor: dict[str, Any],
    paper_ledger: dict[str, Any],
    mutation_journal: dict[str, Any],
    latest_order: dict[str, Any],
    data_health: dict[str, Any],
    market_truth: dict[str, Any],
    data_revision: dict[str, Any],
    forward_validation: dict[str, Any],
    small_capital_plan: dict[str, Any],
    audit: dict[str, Any],
    recent_audit: list[dict[str, Any]],
    updated_at: int,
) -> dict[str, Any]:
    """Build the public control-center response from precomputed components.

    This projection performs no I/O. Authority comes only from explicit runtime
    arguments; authority-like fields embedded in component payloads cannot
    promote the response.
    """

    component_inputs = {
        "paper": paper,
        "risk": risk,
        "pipeline": pipeline,
        "executor": executor,
        "paper_ledger": paper_ledger,
        "mutation_journal": mutation_journal,
        "data_health": data_health,
        "market_truth": market_truth,
        "data_revision": data_revision,
        "forward_validation": forward_validation,
        "small_capital_plan": small_capital_plan,
        "audit": audit,
    }
    projected_components: dict[str, dict[str, Any]] = {}
    sanitized_paths: list[str] = []
    for name, value in component_inputs.items():
        projected, paths = _component_projection(value, name=name)
        projected_components[name] = projected
        sanitized_paths.extend(paths)
    projected_recent_audit, recent_audit_paths = _sanitize_authority(
        recent_audit,
        path="recent_audit",
    )
    if not isinstance(projected_recent_audit, list):
        projected_recent_audit = []
    sanitized_paths.extend(recent_audit_paths)
    paper = projected_components["paper"]
    risk = projected_components["risk"]
    pipeline = projected_components["pipeline"]
    executor = projected_components["executor"]
    paper_ledger = projected_components["paper_ledger"]
    mutation_journal = projected_components["mutation_journal"]
    data_health = projected_components["data_health"]
    market_truth = projected_components["market_truth"]
    data_revision = projected_components["data_revision"]
    forward_validation = projected_components["forward_validation"]
    small_capital_plan = projected_components["small_capital_plan"]
    audit = projected_components["audit"]
    latest_run = pipeline.get("latest") or {}
    paper_authorized = effective_paper_authorized is True
    result = {
        "ok": True,
        "product_mode": "strategy_validation_and_paper_trading",
        "read_only": runtime_read_only,
        "live_trading_hard_block": live_trading_hard_block is True,
        "live_order_allowed": False,
        "paper_authorized": paper_authorized,
        "paper_armed": paper.get("armed") is True,
        "paper": paper,
        "risk": risk,
        "pipeline": pipeline,
        "executor": executor,
        "paper_ledger": paper_ledger,
        "mutation_journal": mutation_journal,
        "latest_order": _latest_order_projection(latest_order),
        "data_health": data_health,
        "market_truth": market_truth,
        "data_revision": data_revision,
        "forward_validation": forward_validation,
        "small_capital_plan": small_capital_plan,
        "audit": audit,
        "summary": {
            "symbol": paper.get("symbol"),
            "strategy_id": paper.get("strategy", {}).get("id") or default_strategy_id,
            "paper_armed": bool(paper.get("armed")),
            "paper_authorized": paper_authorized,
            "paper_equity": paper.get("equity"),
            "risk_status": risk.get("pretrade", {}).get("status"),
            "pipeline_status": latest_run.get("status", "NOT_STARTED"),
            "pipeline_run_id": latest_run.get("run_id", ""),
            "data_status": market_truth.get("status") or "UNKNOWN",
            "data_revision_status": data_revision.get("status", "UNKNOWN"),
            "revision_review_count": data_revision.get("latest_revision_review_count", 0),
            "cross_source_review_count": sum(
                1 for item in data_revision.get("latest_cross_source") or [] if item.get("status") == "REVIEW"
            ),
            "audit_events": audit.get("event_count", 0),
            "paper_ledger_backend": paper_ledger.get("backend"),
            "paper_ledger_version": paper_ledger.get("account_version", 0),
            "paper_ledger_restart_ready": paper_ledger.get("restart_ready") is True,
            "mutation_journal_status": "READY" if mutation_journal.get("ok") else "BLOCK",
            "small_capital_plan_status": small_capital_plan.get("status", "BLOCK"),
        },
        "recent_audit": projected_recent_audit,
        "updated_at": updated_at,
    }
    if sanitized_paths:
        result["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    return result
