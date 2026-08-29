"""Redacted public projection for the temporal report21 candidate binding."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_binding import (
    verify_strategy_correlation_cluster_temporal_stability_report_binding,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-cluster-temporal-stability-candidate-binding-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-cluster-temporal-stability-candidate-binding-public-summary-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260821-temporal-report21-candidate-binding-lock-1"

_NOT_SUPPLIED = object()
_PERMISSION = {
    "status": "RESEARCH_ONLY",
    "descriptive_only": True,
    "profitability_claim_allowed": False,
    "candidate_binding_activation_allowed": False,
    "formal_registration_report_binding_allowed": False,
    "formal_registry_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
}
_REDACTION = {
    "assessment_hash_exposed": False,
    "protocol_registration_hash_exposed": False,
    "report21_extension_hash_exposed": False,
    "report_identity_set_hash_exposed": False,
    "binding_id_exposed": False,
    "facts_exposed": False,
    "blockers_exposed": False,
    "external_assets_exposed": False,
    "external_bindings_exposed": False,
    "strategy_identities_exposed": False,
    "correlation_values_exposed": False,
    "interval_values_exposed": False,
    "return_values_exposed": False,
    "profitability_metrics_exposed": False,
}


def _summary(state: str, report21_decision: str) -> dict[str, Any]:
    if state == "NOT_SUPPLIED":
        source_status = "NOT_SUPPLIED"
        assessment_status = "NOT_SUPPLIED"
        binding_status = "NOT_SUPPLIED"
        gap_status = "CANDIDATE_BINDING_NOT_SUPPLIED"
        maturity_status = "NOT_SUPPLIED"
    elif state == "UNKNOWN":
        source_status = "UNKNOWN"
        assessment_status = "UNKNOWN"
        binding_status = "UNKNOWN"
        gap_status = "CANDIDATE_BINDING_UNKNOWN"
        maturity_status = "UNKNOWN"
    elif state == "CANDIDATE_BOUND":
        source_status = "OBSERVED"
        assessment_status = "VERIFIED"
        binding_status = "CANDIDATE_BOUND"
        gap_status = "FORMAL_BINDING_NOT_ESTABLISHED"
        maturity_status = "CANDIDATE_BOUND_NOT_FORMAL"
    else:
        source_status = "OBSERVED"
        assessment_status = "VERIFIED"
        binding_status = "BLOCK"
        gap_status = "CANDIDATE_BINDING_BLOCKED"
        maturity_status = "CANDIDATE_BLOCKED"
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": source_status,
            "binding_assessment_status": assessment_status,
            "candidate_binding_status": binding_status,
            "report21_decision": report21_decision,
        },
        "gap": {
            "status": gap_status,
            "formal_registration_report_binding": "NOT_ESTABLISHED",
            "formal_registry_status": "NOT_SUPPLIED",
            "writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        },
        "maturity": {
            "status": maturity_status,
            "candidate_binding": binding_status,
            "report21_decision": report21_decision,
            "formal_binding": "NOT_ESTABLISHED",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
    binding_assessment: Any = _NOT_SUPPLIED,
    *,
    protocol_registration: Any = None,
    report21_extension: Any = None,
    binding_id: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_report21_extension_hash: Any = None,
    expected_report_identity_set_hash: Any = None,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
) -> dict[str, Any]:
    if binding_assessment is _NOT_SUPPLIED:
        return _summary("NOT_SUPPLIED", "NOT_SUPPLIED")
    try:
        verification = (
            verify_strategy_correlation_cluster_temporal_stability_report_binding(
                binding_assessment,
                protocol_registration=protocol_registration,
                report21_extension=report21_extension,
                binding_id=binding_id,
                expected_protocol_registration_hash=(
                    expected_protocol_registration_hash
                ),
                expected_report21_extension_hash=expected_report21_extension_hash,
                expected_report_identity_set_hash=expected_report_identity_set_hash,
                expected_base_report_hash=expected_base_report_hash,
                expected_global_independence_extension_hash=(
                    expected_global_independence_extension_hash
                ),
                expected_cluster_stability_extension_hash=(
                    expected_cluster_stability_extension_hash
                ),
                expected_registry_bindings=expected_registry_bindings,
                expected_stability_bindings=expected_stability_bindings,
                expected_temporal_stability_bindings=(
                    expected_temporal_stability_bindings
                ),
            )
            if type(binding_assessment) is dict
            else {"status": "BLOCK", "candidate_bound": False}
        )
    except (KeyError, TypeError, ValueError):
        verification = {"status": "BLOCK", "candidate_bound": False}
    if verification.get("status") != "PASS":
        return _summary("UNKNOWN", "UNKNOWN")
    decision = binding_assessment.get("report21_decision")
    if decision not in {"PASS", "BLOCK", "UNKNOWN"}:
        return _summary("UNKNOWN", "UNKNOWN")
    state = (
        "CANDIDATE_BOUND"
        if verification.get("candidate_bound") is True
        else "CANDIDATE_BLOCKED"
    )
    return _summary(state, decision)


def verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
    document: Any,
    *,
    binding_assessment: Any = _NOT_SUPPLIED,
    protocol_registration: Any = None,
    report21_extension: Any = None,
    binding_id: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_report21_extension_hash: Any = None,
    expected_report_identity_set_hash: Any = None,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
        binding_assessment,
        protocol_registration=protocol_registration,
        report21_extension=report21_extension,
        binding_id=binding_id,
        expected_protocol_registration_hash=expected_protocol_registration_hash,
        expected_report21_extension_hash=expected_report21_extension_hash,
        expected_report_identity_set_hash=expected_report_identity_set_hash,
        expected_base_report_hash=expected_base_report_hash,
        expected_global_independence_extension_hash=(
            expected_global_independence_extension_hash
        ),
        expected_cluster_stability_extension_hash=(
            expected_cluster_stability_extension_hash
        ),
        expected_registry_bindings=expected_registry_bindings,
        expected_stability_bindings=expected_stability_bindings,
        expected_temporal_stability_bindings=expected_temporal_stability_bindings,
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
        "candidate_binding_status": (
            expected["source"]["candidate_binding_status"]
            if status == "PASS"
            else "UNKNOWN"
        ),
        "candidate_bound": (
            expected["source"]["candidate_binding_status"] == "CANDIDATE_BOUND"
            if status == "PASS"
            else False
        ),
        "formal_registration_report_binding": False,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSION),
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary",
    "verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary",
]
