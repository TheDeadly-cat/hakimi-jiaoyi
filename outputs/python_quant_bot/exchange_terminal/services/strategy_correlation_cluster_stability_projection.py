"""Redacted public projection for the within-cluster stability consumer gate."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    verify_strategy_correlation_cluster_stability_gate,
)


PUBLIC_SUMMARY_SCHEMA = "strategy-correlation-cluster-stability-public-summary-v1"
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-cluster-stability-public-summary-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260821-within-cluster-stability-calibration-rail-1"

_PERMISSION = {
    "status": "RESEARCH_ONLY",
    "descriptive_only": True,
    "profitability_claim_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
}
_REDACTION = {
    "artifact_hashes_exposed": False,
    "strategy_identity_exposed": False,
    "variant_identity_exposed": False,
    "lane_identity_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
    "correlation_values_exposed": False,
    "interval_values_exposed": False,
    "return_values_exposed": False,
    "rankings_exposed": False,
    "profitability_metrics_exposed": False,
}


def _summary(state: str) -> dict[str, Any]:
    if state == "UNKNOWN":
        source = {
            "status": "UNKNOWN",
            "uncertainty_evidence_status": "UNKNOWN",
            "complete_link_gate_status": "UNKNOWN",
            "stability_policy_status": "UNKNOWN",
            "stability_gate_contract_status": "UNKNOWN",
        }
        gap = {
            "status": "UNKNOWN",
            "stability_decision": "UNKNOWN",
            "report_integration_status": "UNKNOWN",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": "UNKNOWN",
            "family_scope": "UNKNOWN",
            "correction_method": "UNKNOWN",
            "interval_rule": "UNKNOWN",
            "report_integration": "NOT_IMPLEMENTED",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        }
    else:
        source = {
            "status": "OBSERVED",
            "uncertainty_evidence_status": "VERIFIED",
            "complete_link_gate_status": "VERIFIED",
            "stability_policy_status": "SEALED",
            "stability_gate_contract_status": "VERIFIED",
        }
        gap = {
            "status": (
                "REPORT_INTEGRATION_NOT_IMPLEMENTED"
                if state == "PASS"
                else "STABILITY_EVIDENCE_BLOCKED"
            ),
            "stability_decision": state,
            "report_integration_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": "CONSUMER_GATE_PASS" if state == "PASS" else "CONSUMER_GATE_BLOCK",
            "family_scope": "WITHIN_CLUSTER_PAIRS_ONLY",
            "correction_method": "BONFERRONI_TWO_SIDED_FWER_V1",
            "interval_rule": "SEALED",
            "report_integration": "NOT_IMPLEMENTED",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        }
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": source,
        "gap": gap,
        "maturity": maturity,
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_cluster_stability_public_summary(
    stability_gate: Any,
    *,
    source_uncertainty_audit: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    try:
        verification = verify_strategy_correlation_cluster_stability_gate(
            stability_gate,
            source_uncertainty_audit=source_uncertainty_audit,
            complete_link_gate=complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (TypeError, ValueError):
        return _summary("UNKNOWN")
    if (
        type(stability_gate) is not dict
        or strict_research_authority_violations(stability_gate)
        or verification.get("status") != "PASS"
        or verification.get("decision") not in {"PASS", "BLOCK"}
        or stability_gate.get("status") != verification.get("decision")
    ):
        return _summary("UNKNOWN")
    return _summary(verification["decision"])


def verify_strategy_correlation_cluster_stability_public_summary(
    document: Any,
    *,
    stability_gate: Any,
    source_uncertainty_audit: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_stability_public_summary(
        stability_gate,
        source_uncertainty_audit=source_uncertainty_audit,
        complete_link_gate=complete_link_gate,
        preregistration=preregistration,
        correlation_matrix=correlation_matrix,
        selection_cells=selection_cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("public_summary_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        if not strict_json_contract_equal(document, expected):
            blockers.append("public_summary_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "projection_status": (
            expected["maturity"]["status"] if status == "PASS" else "UNKNOWN"
        ),
        "stability_decision": (
            expected["gap"]["stability_decision"] if status == "PASS" else "UNKNOWN"
        ),
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_stability_public_summary",
    "verify_strategy_correlation_cluster_stability_public_summary",
]
