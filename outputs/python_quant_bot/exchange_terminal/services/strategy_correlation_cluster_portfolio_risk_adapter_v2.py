"""Temporal-stability-aware portfolio-risk adapter v2.

The adapter joins the existing dual portfolio-risk gate with the existing
temporal cluster-stability gate.  It is synthetic/research-only and is not wired
to runtime, risk-service, paper, live, or current admission paths.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v1 as adapter_v1_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_stability as temporal_contract,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v2"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-adapter-v2-verification-v1"
)
STATIC_FINGERPRINT = "20260822-portfolio-risk-temporal-stability-adapter-lock-1"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ADAPTER_CONTEXT_KEYS = {
    "preregistration",
    "cluster_correlation_matrix",
    "complete_link_audit",
    "equity",
    "positions",
    "proposed_symbol",
    "proposed_notional",
    "proposed_direction",
    "proposed_cluster",
    "risk_increasing",
    "legacy_correlations",
    "regime",
    "legacy_limits",
    "max_cluster_gross_pct",
}
_TEMPORAL_CONTEXT_KEYS = {
    "source_uncertainty_audit",
    "full_window_stability_gate",
    "complete_link_gate",
    "preregistration",
    "correlation_matrix",
    "selection_cells",
    "strategy_id",
    "variant_id",
    "lane",
}


class PortfolioRiskAdapterV2ContractError(ValueError):
    """Raised when a component or shared lineage cannot be exactly verified."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise PortfolioRiskAdapterV2ContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != expected:
        raise PortfolioRiskAdapterV2ContractError(f"{label} keys do not match schema")
    return result


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise PortfolioRiskAdapterV2ContractError(f"{label} must be lowercase sha256")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result["adapter_hash"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return result


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _has_locked_authority(document: dict[str, Any]) -> bool:
    authority = document.get("authority")
    return (
        type(authority) is dict
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _verify_adapter_v1(
    adapter_v1_document: Any, adapter_v1_verification_context: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _require_exact_keys(
        adapter_v1_verification_context,
        _ADAPTER_CONTEXT_KEYS,
        "adapter_v1_verification_context",
    )
    verification = adapter_v1_contract.verify_strategy_correlation_cluster_portfolio_risk_adapter_v1(
        adapter_v1_document,
        context["preregistration"],
        context["cluster_correlation_matrix"],
        context["complete_link_audit"],
        equity=context["equity"],
        positions=context["positions"],
        proposed_symbol=context["proposed_symbol"],
        proposed_notional=context["proposed_notional"],
        proposed_direction=context["proposed_direction"],
        proposed_cluster=context["proposed_cluster"],
        risk_increasing=context["risk_increasing"],
        legacy_correlations=context["legacy_correlations"],
        regime=context["regime"],
        legacy_limits=context["legacy_limits"],
        max_cluster_gross_pct=context["max_cluster_gross_pct"],
    )
    if (
        type(verification) is not dict
        or verification.get("status") != "PASS"
        or verification.get("adapter_exactly_verified") is not True
    ):
        raise PortfolioRiskAdapterV2ContractError("adapter v1 exact verification failed")
    document = _require_dict(adapter_v1_document, "adapter_v1_document")
    if (
        document.get("schema_version")
        != "strategy-correlation-cluster-portfolio-risk-adapter-v1"
        or document.get("static_fingerprint")
        != adapter_v1_contract.STATIC_FINGERPRINT
        or document.get("status") not in ("PASS", "BLOCK")
        or not _has_locked_authority(document)
    ):
        raise PortfolioRiskAdapterV2ContractError("adapter v1 bounded state mismatch")
    _require_hash(document.get("adapter_hash"), "adapter v1 hash")
    facts = _require_dict(document.get("facts"), "adapter v1 facts")
    if type(facts.get("risk_increasing")) is not bool:
        raise PortfolioRiskAdapterV2ContractError("adapter v1 risk direction is not strict")
    return document, context


def _verify_temporal_gate(
    temporal_stability_gate: Any, temporal_stability_verification_context: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _require_exact_keys(
        temporal_stability_verification_context,
        _TEMPORAL_CONTEXT_KEYS,
        "temporal_stability_verification_context",
    )
    verification = temporal_contract.verify_strategy_correlation_cluster_temporal_stability_gate(
        temporal_stability_gate,
        source_uncertainty_audit=context["source_uncertainty_audit"],
        full_window_stability_gate=context["full_window_stability_gate"],
        complete_link_gate=context["complete_link_gate"],
        preregistration=context["preregistration"],
        correlation_matrix=context["correlation_matrix"],
        selection_cells=context["selection_cells"],
        strategy_id=context["strategy_id"],
        variant_id=context["variant_id"],
        lane=context["lane"],
    )
    if (
        type(verification) is not dict
        or verification.get("status") != "PASS"
        or verification.get("gate_verified") is not True
    ):
        raise PortfolioRiskAdapterV2ContractError(
            "temporal stability exact verification failed"
        )
    document = _require_dict(temporal_stability_gate, "temporal_stability_gate")
    if (
        document.get("schema_version")
        != "strategy-correlation-cluster-temporal-stability-gate-v1"
        or document.get("status") not in ("PASS", "BLOCK")
        or verification.get("decision_status") != document["status"]
        or document.get("consumer_only") is not True
        or document.get("writer_available") is not False
        or document.get("current_admission_allowed") is not False
        or document.get("current_writer_activation_allowed") is not False
        or document.get("permissions")
        != {"paper_authorized": False, "live_order_allowed": False}
    ):
        raise PortfolioRiskAdapterV2ContractError(
            "temporal stability bounded state mismatch"
        )
    _require_hash(document.get("gate_hash"), "temporal stability gate hash")
    _require_hash(document.get("policy_hash"), "temporal stability policy hash")
    return document, context


def _validate_shared_lineage(
    adapter_context: dict[str, Any], temporal_context: dict[str, Any]
) -> dict[str, Any]:
    if adapter_context["preregistration"] != temporal_context["preregistration"]:
        raise PortfolioRiskAdapterV2ContractError("preregistration lineage mismatch")
    if (
        adapter_context["cluster_correlation_matrix"]
        != temporal_context["correlation_matrix"]
    ):
        raise PortfolioRiskAdapterV2ContractError("correlation matrix lineage mismatch")
    proposed_symbol = adapter_context["proposed_symbol"]
    if type(proposed_symbol) is not str or not proposed_symbol:
        raise PortfolioRiskAdapterV2ContractError("proposed symbol is invalid")
    selection_cells = temporal_context["selection_cells"]
    if type(selection_cells) is not list:
        raise PortfolioRiskAdapterV2ContractError("selection cells must be a list")
    matching = [
        cell
        for cell in selection_cells
        if type(cell) is dict
        and cell.get("strategy_id") == temporal_context["strategy_id"]
        and cell.get("variant_id") == temporal_context["variant_id"]
        and cell.get("lane") == temporal_context["lane"]
        and cell.get("symbol") == proposed_symbol
    ]
    if len(matching) != 1 or matching[0].get("gate_status") != "PASS":
        raise PortfolioRiskAdapterV2ContractError(
            "proposed symbol is not uniquely bound to a passing selection cell"
        )
    return matching[0]


def _stability_summary(temporal_gate: dict[str, Any]) -> dict[str, Any]:
    audit = _require_dict(
        temporal_gate.get("temporal_stability_audit"), "temporal stability audit"
    )
    pair_results = audit.get("pair_results")
    if type(pair_results) is not list:
        raise PortfolioRiskAdapterV2ContractError("temporal pair results are invalid")
    window_count = 0
    blocked_window_count = 0
    unstable_window_count = 0
    insufficient_sample_window_count = 0
    for pair in pair_results:
        if type(pair) is not dict or type(pair.get("window_results")) is not list:
            raise PortfolioRiskAdapterV2ContractError("temporal window results are invalid")
        for window in pair["window_results"]:
            if type(window) is not dict:
                raise PortfolioRiskAdapterV2ContractError("temporal window result is invalid")
            window_count += 1
            if window.get("status") == "BLOCK":
                blocked_window_count += 1
            if window.get("classification") == "UNSTABLE_ABSOLUTE_DEPENDENCE":
                unstable_window_count += 1
            if window.get("classification") == "INSUFFICIENT_EFFECTIVE_SAMPLE":
                insufficient_sample_window_count += 1
    return {
        "status": temporal_gate["status"],
        "first_blocking_tier": temporal_gate.get("first_blocking_tier"),
        "within_cluster_pair_count": audit.get("within_cluster_pair_count"),
        "pair_window_hypothesis_count": audit.get("pair_window_hypothesis_count"),
        "window_result_count": window_count,
        "blocked_window_count": blocked_window_count,
        "unstable_window_count": unstable_window_count,
        "insufficient_sample_window_count": insufficient_sample_window_count,
        "blocker_count": len(temporal_gate.get("blockers", [])),
    }


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
    adapter_v1_document: Any,
    temporal_stability_gate: Any,
    *,
    adapter_v1_verification_context: Any,
    temporal_stability_verification_context: Any,
) -> dict[str, Any]:
    """Evaluate the strict union of portfolio and temporal stability gates."""

    adapter_v1, adapter_context = _verify_adapter_v1(
        adapter_v1_document, adapter_v1_verification_context
    )
    temporal_gate, temporal_context = _verify_temporal_gate(
        temporal_stability_gate, temporal_stability_verification_context
    )
    selection_cell = _validate_shared_lineage(adapter_context, temporal_context)
    stability = _stability_summary(temporal_gate)

    base_pass = adapter_v1["status"] == "PASS"
    risk_increasing = adapter_v1["facts"]["risk_increasing"]
    temporal_pass = temporal_gate["status"] == "PASS"
    warnings: list[str] = []
    if not base_pass:
        status = "BLOCK"
        decision = "BLOCKED_BASE_PORTFOLIO_RISK_BUDGET"
        blockers = ["BASE_ADAPTER_V1_BLOCKED"] + list(adapter_v1.get("blockers", []))
    elif not risk_increasing:
        status = "PASS"
        decision = "RISK_REDUCTION_PATH_TEMPORAL_STABILITY_NOT_REQUIRED"
        blockers = []
        if not temporal_pass:
            warnings.append("TEMPORAL_STABILITY_BLOCK_OBSERVED_ON_RISK_REDUCTION_PATH")
    elif not temporal_pass:
        status = "BLOCK"
        decision = "BLOCKED_TEMPORAL_CORRELATION_INSTABILITY"
        blockers = ["TEMPORAL_STABILITY_GATE_BLOCKED"] + list(
            temporal_gate.get("blockers", [])
        )
    else:
        status = "PASS"
        decision = "WITHIN_RESEARCH_RISK_BUDGET_AND_TEMPORAL_STABILITY"
        blockers = []

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "checks": [
            {
                "name": "adapter_v1_exact_verification",
                "ok": True,
                "blocking": True,
            },
            {
                "name": "temporal_stability_exact_verification",
                "ok": True,
                "blocking": True,
            },
            {
                "name": "shared_preregistration_and_matrix_lineage",
                "ok": True,
                "blocking": True,
            },
            {
                "name": "proposed_symbol_selection_cell_binding",
                "ok": True,
                "blocking": True,
            },
            {
                "name": "base_portfolio_risk_budget",
                "ok": base_pass,
                "blocking": True,
            },
            {
                "name": "temporal_stability_for_risk_increase",
                "ok": temporal_pass or not risk_increasing,
                "blocking": risk_increasing,
            },
        ],
        "portfolio": copy.deepcopy(adapter_v1["portfolio"]),
        "stability": stability,
        "source": {
            "adapter_v1_schema_version": adapter_v1["schema_version"],
            "adapter_v1_hash": adapter_v1["adapter_hash"],
            "temporal_stability_schema_version": temporal_gate["schema_version"],
            "temporal_stability_gate_hash": temporal_gate["gate_hash"],
            "temporal_stability_policy_hash": temporal_gate["policy_hash"],
            "preregistration_hash": adapter_context["preregistration"][
                "preregistration_hash"
            ],
            "correlation_matrix_hash": adapter_context["cluster_correlation_matrix"][
                "matrix_hash"
            ],
            "strategy_id": temporal_context["strategy_id"],
            "variant_id": temporal_context["variant_id"],
            "lane": temporal_context["lane"],
            "proposed_symbol": selection_cell["symbol"],
        },
        "facts": {
            "risk_increasing": risk_increasing,
            "base_adapter_passed": base_pass,
            "temporal_stability_passed": temporal_pass,
            "temporal_stability_required": risk_increasing,
            "component_results_jointly_required_for_risk_increase": True,
            "component_results_embedded": False,
            "source_documents_embedded": False,
            "return_series_embedded": False,
            "raw_correlations_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "risk_service_invoked": False,
            "profitability_proven": False,
        },
        "warnings": warnings,
        "blockers": blockers,
        "authority": _authority(),
    }
    return _seal(payload)


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v2(
    document: Any,
    adapter_v1_document: Any,
    temporal_stability_gate: Any,
    *,
    adapter_v1_verification_context: Any,
    temporal_stability_verification_context: Any,
) -> dict[str, Any]:
    """Rebuild the v2 decision from all component evidence and compare exactly."""

    try:
        rebuilt = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            adapter_v1_document,
            temporal_stability_gate,
            adapter_v1_verification_context=adapter_v1_verification_context,
            temporal_stability_verification_context=(
                temporal_stability_verification_context
            ),
        )
        exact = type(document) is dict and document == rebuilt
    except (PortfolioRiskAdapterV2ContractError, ValueError, TypeError, KeyError):
        exact = False
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "FAIL",
        "adapter_exactly_verified": exact,
        "adapter_decision": document.get("decision") if type(document) is dict else None,
        "blockers": [] if exact else ["ADAPTER_V2_EXACT_REBUILD_MISMATCH"],
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "PortfolioRiskAdapterV2ContractError",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2",
]
