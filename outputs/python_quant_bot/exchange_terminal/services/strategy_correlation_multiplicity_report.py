from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_json_hash import canonical_hash
from .execution_authority import authority_violations
from .strategy_correlation_multiplicity_audit import (
    verify_strategy_correlation_multiplicity_audit,
)
from .strategy_correlation_multiplicity_protocol import (
    TARGET_MATRIX_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_multiplicity_protocol_registration,
)
from .strategy_correlation_multiplicity_registration import (
    verify_strategy_correlation_multiplicity_binding_assessment,
)
from .strategy_correlation_return_replay import (
    verify_replayed_correlation_cluster_gate,
)
from .strategy_correlation_uncertainty_audit import (
    verify_strategy_correlation_uncertainty_audit,
)
from .strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
    verify_strategy_matrix_protocol,
)


STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-report-evidence-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-report-evidence-verification-v1"
)

_EVIDENCE_FIELDS = frozenset({
    "schema_version",
    "status",
    "decision_status",
    "protocol_hash",
    "protocol_registration_hash",
    "source_registration_hash",
    "family_registration_hash",
    "cluster_preregistration_hash",
    "gate_evaluation_hash",
    "gate_hash",
    "matrix_replay_hash",
    "uncertainty_audit_hash",
    "multiplicity_audit_hash",
    "family_binding_assessment_hash",
    "expected_family_size",
    "observed_family_size",
    "gate_status",
    "uncertainty_status",
    "multiplicity_status",
    "family_binding_local_chain_status",
    "family_binding_local_decision_status",
    "replayed_gate",
    "uncertainty_audit",
    "multiplicity_audit",
    "family_binding_assessment",
    "required_matrix_report_schema_version",
    "next_evidence_required",
    "interpretation",
    "formal_registry_bound",
    "current_report_schema_bound",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "permissions",
    "blockers",
    "evidence_hash",
})


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    document = dict(payload)
    document["evidence_hash"] = canonical_hash(document)
    return document


def _invalid_evidence() -> dict[str, Any]:
    return _sealed({
        "schema_version": STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION,
        "status": "BLOCK",
        "decision_status": "BLOCK",
        "protocol_hash": None,
        "protocol_registration_hash": None,
        "source_registration_hash": None,
        "family_registration_hash": None,
        "cluster_preregistration_hash": None,
        "gate_evaluation_hash": None,
        "gate_hash": None,
        "matrix_replay_hash": None,
        "uncertainty_audit_hash": None,
        "multiplicity_audit_hash": None,
        "family_binding_assessment_hash": None,
        "expected_family_size": None,
        "observed_family_size": None,
        "gate_status": "UNKNOWN",
        "uncertainty_status": "UNKNOWN",
        "multiplicity_status": "UNKNOWN",
        "family_binding_local_chain_status": "UNKNOWN",
        "family_binding_local_decision_status": "UNKNOWN",
        "replayed_gate": None,
        "uncertainty_audit": None,
        "multiplicity_audit": None,
        "family_binding_assessment": None,
        "required_matrix_report_schema_version": TARGET_MATRIX_REPORT_SCHEMA_VERSION,
        "next_evidence_required": "VALID_MULTIPLICITY_REPORT_EVIDENCE_INPUTS",
        "interpretation": "DESCRIPTIVE_RESEARCH_ONLY_NOT_PROFITABILITY_OR_TRADING_AUTHORITY",
        "formal_registry_bound": False,
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "parameter_selection_allowed": False,
        "performance_claim_allowed": False,
        "profitability_proven": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "blockers": ["multiplicity_report_evidence_chain_invalid"],
    })


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def build_strategy_correlation_multiplicity_report_evidence(
    protocol: Any,
    replayed_gate: Any,
    uncertainty_audit: Any,
    multiplicity_audit: Any,
    family_binding_assessment: Any,
) -> dict[str, Any]:
    protocol_map = _mapping(protocol)
    gate_map = _mapping(replayed_gate)
    uncertainty_map = _mapping(uncertainty_audit)
    multiplicity_map = _mapping(multiplicity_audit)
    assessment_map = _mapping(family_binding_assessment)
    registration = _mapping(
        protocol_map.get("correlation_multiplicity_protocol_registration")
    )
    source_registration = _mapping(registration.get("source_protocol_registration"))
    family_registration = _mapping(registration.get("family_registration"))
    matrix_replay = _mapping(gate_map.get("matrix_replay"))
    completed_input = _mapping(matrix_replay.get("completed_price_input"))

    protocol_verification = verify_strategy_matrix_protocol(
        protocol,
        verify_current_implementation=False,
    )
    registration_verification = (
        verify_strategy_correlation_multiplicity_protocol_registration(
            registration
        )
    )
    gate_verification = verify_replayed_correlation_cluster_gate(replayed_gate)
    uncertainty_verification = verify_strategy_correlation_uncertainty_audit(
        uncertainty_audit
    )
    multiplicity_verification = verify_strategy_correlation_multiplicity_audit(
        multiplicity_audit
    )
    family_assessment_verification = (
        verify_strategy_correlation_multiplicity_binding_assessment(
            family_binding_assessment,
            family_registration=family_registration,
            multiplicity_audit=multiplicity_audit,
        )
    )

    evaluation = {
        "strategy_id": str(gate_map.get("strategy_id") or ""),
        "variant_id": str(gate_map.get("variant_id") or ""),
        "lane": str(gate_map.get("lane") or ""),
    }
    expected_family_size = _mapping(family_registration.get("family_definition")).get(
        "expected_cross_cluster_family_size"
    )
    observed_family_size = multiplicity_map.get("family_size")
    chain_valid = all(
        verification.get("status") == "PASS"
        for verification in (
            protocol_verification,
            registration_verification,
            gate_verification,
            uncertainty_verification,
            multiplicity_verification,
            family_assessment_verification,
        )
    ) and all((
        protocol_map.get("schema_version")
        == STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
        registration_verification.get("registration_status") == "PREREGISTERED",
        protocol_map.get("correlation_multiplicity_protocol_registration_hash")
        == registration.get("registration_hash"),
        matrix_replay.get("preregistration")
        == source_registration.get("preregistration"),
        completed_input.get("cutoff_date") == source_registration.get("cutoff_date"),
        completed_input.get("selection_alignment_input_hash")
        == source_registration.get("selection_alignment_input_hash"),
        evaluation in list(source_registration.get("evaluations") or []),
        uncertainty_map.get("matrix_replay") == matrix_replay,
        uncertainty_map.get("policy_hash")
        == source_registration.get("uncertainty_policy_hash"),
        multiplicity_map.get("source_uncertainty_audit") == uncertainty_map,
        multiplicity_map.get("source_audit_hash") == uncertainty_map.get("audit_hash"),
        multiplicity_map.get("policy_hash")
        == family_registration.get("multiplicity_policy_hash"),
        assessment_map.get("local_chain_status") == "PASS",
        assessment_map.get("local_decision_status")
        == multiplicity_map.get("status"),
        assessment_map.get("expected_family_size") == expected_family_size,
        assessment_map.get("observed_family_size") == observed_family_size,
        expected_family_size == observed_family_size,
    ))
    if not chain_valid:
        return _invalid_evidence()

    gate_status = str(gate_map.get("status") or "BLOCK")
    uncertainty_status = str(uncertainty_map.get("status") or "BLOCK")
    multiplicity_status = str(multiplicity_map.get("status") or "BLOCK")
    decision_blockers: list[str] = []
    if gate_status != "PASS":
        decision_blockers.append("correlation_gate_decision_block")
        next_evidence = "CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER"
    elif uncertainty_status != "PASS":
        decision_blockers.append("correlation_uncertainty_decision_block")
        next_evidence = "RESOLVE_UNCERTAINTY_BLOCK_OR_REREGISTER"
    elif multiplicity_status != "PASS":
        decision_blockers.append("correlation_multiplicity_decision_block")
        next_evidence = "RESOLVE_MULTIPLICITY_BLOCK_OR_REREGISTER"
    else:
        next_evidence = "MATRIX_REPORT_SCHEMA_8_ENVELOPE"

    return _sealed({
        "schema_version": STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION,
        "status": "PASS",
        "decision_status": "BLOCK" if decision_blockers else "PASS",
        "protocol_hash": str(protocol_map.get("protocol_hash") or ""),
        "protocol_registration_hash": str(registration.get("registration_hash") or ""),
        "source_registration_hash": str(registration.get("source_registration_hash") or ""),
        "family_registration_hash": str(registration.get("family_registration_hash") or ""),
        "cluster_preregistration_hash": str(registration.get("cluster_preregistration_hash") or ""),
        "gate_evaluation_hash": str(gate_map.get("evaluation_hash") or ""),
        "gate_hash": str(_mapping(gate_map.get("gate")).get("gate_hash") or ""),
        "matrix_replay_hash": str(matrix_replay.get("replay_hash") or ""),
        "uncertainty_audit_hash": str(uncertainty_map.get("audit_hash") or ""),
        "multiplicity_audit_hash": str(multiplicity_map.get("audit_hash") or ""),
        "family_binding_assessment_hash": str(assessment_map.get("assessment_hash") or ""),
        "expected_family_size": expected_family_size,
        "observed_family_size": observed_family_size,
        "gate_status": gate_status,
        "uncertainty_status": uncertainty_status,
        "multiplicity_status": multiplicity_status,
        "family_binding_local_chain_status": str(
            assessment_map.get("local_chain_status") or "BLOCK"
        ),
        "family_binding_local_decision_status": str(
            assessment_map.get("local_decision_status") or "BLOCK"
        ),
        "replayed_gate": deepcopy(gate_map),
        "uncertainty_audit": deepcopy(uncertainty_map),
        "multiplicity_audit": deepcopy(multiplicity_map),
        "family_binding_assessment": deepcopy(assessment_map),
        "required_matrix_report_schema_version": TARGET_MATRIX_REPORT_SCHEMA_VERSION,
        "next_evidence_required": next_evidence,
        "interpretation": "DESCRIPTIVE_RESEARCH_ONLY_NOT_PROFITABILITY_OR_TRADING_AUTHORITY",
        "formal_registry_bound": False,
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "parameter_selection_allowed": False,
        "performance_claim_allowed": False,
        "profitability_proven": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "blockers": decision_blockers,
    })


def verify_strategy_correlation_multiplicity_report_evidence(
    document: Any,
    *,
    protocol: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(document)
    if set(payload) != _EVIDENCE_FIELDS:
        blockers.append("multiplicity_report_evidence_fields_invalid")
    if payload.get("schema_version") != (
        STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION
    ):
        blockers.append("multiplicity_report_evidence_schema_invalid")
    clean = dict(payload)
    observed_hash = str(clean.pop("evidence_hash", "") or "")
    if not observed_hash or canonical_hash(clean) != observed_hash:
        blockers.append("multiplicity_report_evidence_hash_invalid")

    expected = build_strategy_correlation_multiplicity_report_evidence(
        protocol,
        payload.get("replayed_gate"),
        payload.get("uncertainty_audit"),
        payload.get("multiplicity_audit"),
        payload.get("family_binding_assessment"),
    )
    if payload != expected:
        blockers.append("multiplicity_report_evidence_replay_mismatch")
    blockers.extend(
        f"multiplicity_report_evidence_authority:{item}"
        for item in authority_violations(payload)
    )
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "evidence_status": str(payload.get("status") or "BLOCK"),
        "decision_status": str(payload.get("decision_status") or "BLOCK"),
        "evidence_hash": observed_hash or None,
        "blockers": sorted(set(blockers)),
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
