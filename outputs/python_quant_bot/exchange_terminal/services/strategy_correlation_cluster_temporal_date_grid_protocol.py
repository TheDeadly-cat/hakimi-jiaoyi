"""Protocol-v11 preregistration for a future report22 date-grid extension."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    AUDIT_SCHEMA_VERSION as DATE_GRID_AUDIT_SCHEMA_VERSION,
    DATE_GRID_RULE,
    GATE_SCHEMA_VERSION as DATE_GRID_GATE_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION as DATE_GRID_GATE_POLICY_SCHEMA_VERSION,
    REQUIRED_PRICE_ROWS,
    build_strategy_correlation_cluster_temporal_date_grid_policy,
    verify_strategy_correlation_cluster_temporal_date_grid_policy,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_binding import (
    ASSESSMENT_SCHEMA_VERSION as CANDIDATE_BINDING_ASSESSMENT_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_protocol import (
    POLICY_SCHEMA_VERSION as SOURCE_POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION as SOURCE_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as SOURCE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as SOURCE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_protocol_registration,
)


POLICY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-report-policy-v1"
)
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v9"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v9-verification-v1"
)
TARGET_REPORT_SCHEMA_VERSION = 22
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v11"
TARGET_EXTENSION_SCHEMA_VERSION = (
    "strategy-research-cluster-temporal-date-grid-extension-v1"
)
TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-cluster-temporal-date-grid-extension-v1-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_EXTERNAL_DATE_GRID_BINDING_FIELDS = [
    "strategy_id",
    "variant_id",
    "lane",
    "expected_temporal_date_grid_gate_hash",
]
_REPORT22_EXCLUDED_FIELDS = [
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "return_series",
    "completed_price_datasets",
    "price_rows",
    "price_dates",
]
_WRITER_ACTIVATION_PREREQUISITES = [
    "SOURCE_REGISTRATION_V8_VERIFIED",
    "DATE_GRID_GATE_POLICY_HASH_MATCHES",
    "REPORT21_EXTENSION_EXTERNALLY_VERIFIED",
    "REPORT21_EXTENSION_HASH_EXTERNALLY_BOUND",
    "DATE_GRID_BINDINGS_EXTERNALLY_VERIFIED",
    "DATE_GRID_GATES_EXACTLY_REBUILT",
    "REPORT21_PASS_IMPLIES_ALL_DATE_GRID_GATES_PASS",
    "REPORT22_CONSUMER_VERIFIED",
    "ONE_DATE_GRID_GATE_PER_REPORT_IDENTITY",
    "REPORT22_SOLE_WRITER_IMPLEMENTED",
    "FORMAL_REGISTRY_ACTIVATED",
    "REPORT22_MIGRATION_AUDIT_PASS",
]


def _build_report_policy() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "source_policy_schema_version": SOURCE_POLICY_SCHEMA_VERSION,
        "source_report_schema_version": SOURCE_REPORT_SCHEMA_VERSION,
        "source_protocol_schema_version": SOURCE_PROTOCOL_SCHEMA_VERSION,
        "source_extension_schema_version": SOURCE_EXTENSION_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "date_grid_gate_policy_schema_version": (
            DATE_GRID_GATE_POLICY_SCHEMA_VERSION
        ),
        "date_grid_audit_schema_version": DATE_GRID_AUDIT_SCHEMA_VERSION,
        "date_grid_gate_schema_version": DATE_GRID_GATE_SCHEMA_VERSION,
        "date_grid_rule": DATE_GRID_RULE,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "required_return_observations": REQUIRED_PRICE_ROWS - 1,
        "source_report21_verification_required": True,
        "external_report21_extension_hash_required": True,
        "external_date_grid_bindings_required": True,
        "external_date_grid_binding_fields": list(
            _EXTERNAL_DATE_GRID_BINDING_FIELDS
        ),
        "one_date_grid_gate_per_report_identity_required": True,
        "expected_date_grid_gate_hash_required": True,
        "date_grid_gate_exact_rebuild_required": True,
        "report21_pass_implies_all_date_grid_gates_pass": True,
        "contract_status_decision_separation_required": True,
        "native_json_type_exactness_required": True,
        "report22_payload_excluded_fields": list(_REPORT22_EXCLUDED_FIELDS),
        "report22_consumer_available": False,
        "report22_writer_available": False,
        "writer_activation_prerequisites": list(
            _WRITER_ACTIVATION_PREREQUISITES
        ),
        "formal_registry_activation_allowed": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(policy, "policy_hash")


def build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    source = deepcopy(source_registration) if type(source_registration) is dict else {}
    report_policy = _build_report_policy()
    gate_policy = build_strategy_correlation_cluster_temporal_date_grid_policy()
    registration = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "source_registration": source,
        "source_registration_hash": source.get("registration_hash", ""),
        "source_report_schema_version": SOURCE_REPORT_SCHEMA_VERSION,
        "source_protocol_schema_version": SOURCE_PROTOCOL_SCHEMA_VERSION,
        "source_extension_schema_version": SOURCE_EXTENSION_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "cluster_temporal_date_grid_report_policy": report_policy,
        "cluster_temporal_date_grid_report_policy_hash": report_policy[
            "policy_hash"
        ],
        "temporal_date_grid_gate_policy": gate_policy,
        "temporal_date_grid_gate_policy_hash": gate_policy["policy_hash"],
        "temporal_date_grid_gate_policy_schema_version": (
            DATE_GRID_GATE_POLICY_SCHEMA_VERSION
        ),
        "temporal_date_grid_audit_schema_version": DATE_GRID_AUDIT_SCHEMA_VERSION,
        "temporal_date_grid_gate_schema_version": DATE_GRID_GATE_SCHEMA_VERSION,
        "candidate_binding_assessment_schema_version": (
            CANDIDATE_BINDING_ASSESSMENT_SCHEMA_VERSION
        ),
        "date_grid_candidate_binding_available": True,
        "date_grid_policy_preregistered": True,
        "report22_consumer_available": False,
        "report22_writer_available": False,
        "requires_new_report_schema": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "status": "PREREGISTERED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(registration, "registration_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("temporal_date_grid_protocol_registration_invalid")
        source_registration = {}
        gate_policy = {}
    else:
        source_registration = document.get("source_registration")
        gate_policy = document.get("temporal_date_grid_gate_policy")
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
    try:
        source_verification = (
            verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
                source_registration
            )
            if type(source_registration) is dict
            else {"status": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        source_verification = {"status": "BLOCK"}
    if source_verification.get("status") != "PASS":
        blockers.append("source_registration_v8_invalid")

    gate_policy_verification = (
        verify_strategy_correlation_cluster_temporal_date_grid_policy(
            gate_policy
        )
    )
    if gate_policy_verification.get("status") != "PASS":
        blockers.append("temporal_date_grid_gate_policy_invalid")

    expected = (
        build_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
            source_registration
        )
    )
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("temporal_date_grid_protocol_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "date_grid_policy_preregistered": status == "PASS",
        "date_grid_candidate_binding_available": True,
        "report22_consumer_available": False,
        "report22_writer_available": False,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "CANDIDATE_BINDING_ASSESSMENT_SCHEMA_VERSION",
    "DATE_GRID_AUDIT_SCHEMA_VERSION",
    "DATE_GRID_GATE_POLICY_SCHEMA_VERSION",
    "DATE_GRID_GATE_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "SOURCE_EXTENSION_SCHEMA_VERSION",
    "SOURCE_POLICY_SCHEMA_VERSION",
    "SOURCE_PROTOCOL_SCHEMA_VERSION",
    "SOURCE_REGISTRATION_SCHEMA_VERSION",
    "SOURCE_REPORT_SCHEMA_VERSION",
    "TARGET_EXTENSION_SCHEMA_VERSION",
    "TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_temporal_date_grid_protocol_registration",
    "verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration",
]
