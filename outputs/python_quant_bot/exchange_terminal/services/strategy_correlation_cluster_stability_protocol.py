"""Protocol-v9 preregistration for the report20 cluster-stability consumer."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    GATE_SCHEMA_VERSION as COMPLETE_LINK_GATE_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    AUDIT_SCHEMA_VERSION as STABILITY_AUDIT_SCHEMA_VERSION,
    CORRECTION_METHOD,
    FAMILY_SCOPE,
    FAMILYWISE_CONFIDENCE_LEVEL,
    GATE_SCHEMA_VERSION as STABILITY_GATE_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION as STABILITY_GATE_POLICY_SCHEMA_VERSION,
    STABILITY_RULE,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
    EXTENSION_SCHEMA_VERSION as TARGET_EXTENSION_SCHEMA_VERSION,
    GLOBAL_INDEPENDENCE_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_global_independence_protocol import (
    POLICY_SCHEMA_VERSION as SOURCE_POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as BASE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as BASE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
)


POLICY_SCHEMA_VERSION = "strategy-correlation-cluster-stability-report-policy-v1"
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v7"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v7-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_EXTERNAL_STABILITY_BINDING_FIELDS = [
    "strategy_id",
    "variant_id",
    "lane",
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "expected_stability_gate_hash",
]
_REPORT20_EXCLUDED_FIELDS = [
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "return_series",
]
_WRITER_ACTIVATION_PREREQUISITES = [
    "SOURCE_REGISTRATION_V6_VERIFIED",
    "CLUSTER_STABILITY_REPORT_POLICY_HASH_MATCHES",
    "REPORT19_EXTENSION_EXTERNALLY_VERIFIED",
    "REPORT19_EXTENSION_HASH_EXTERNALLY_BOUND",
    "REGISTRY_BINDINGS_EXTERNALLY_VERIFIED",
    "REPORT20_CONSUMER_VERIFIED",
    "ONE_STABILITY_GATE_PER_REPORT_IDENTITY",
    "STABILITY_EXTERNAL_BINDINGS_EXACTLY_MATCH",
    "STABILITY_GATES_EXACTLY_REBUILT",
    "REPORT20_SOLE_WRITER_IMPLEMENTED",
    "FORMAL_REGISTRY_ACTIVATED",
    "REPORT20_MIGRATION_AUDIT_PASS",
]


def _build_policy() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "source_policy_schema_version": SOURCE_POLICY_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "source_extension_schema_version": GLOBAL_INDEPENDENCE_EXTENSION_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "stability_gate_policy_schema_version": STABILITY_GATE_POLICY_SCHEMA_VERSION,
        "stability_audit_schema_version": STABILITY_AUDIT_SCHEMA_VERSION,
        "stability_gate_schema_version": STABILITY_GATE_SCHEMA_VERSION,
        "source_uncertainty_audit_schema_version": (
            STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION
        ),
        "complete_link_gate_schema_version": COMPLETE_LINK_GATE_SCHEMA_VERSION,
        "family_scope": FAMILY_SCOPE,
        "correction_method": CORRECTION_METHOD,
        "familywise_confidence_level": FAMILYWISE_CONFIDENCE_LEVEL,
        "stability_rule": STABILITY_RULE,
        "source_block_action": "PRESERVE_BLOCK",
        "report19_extension_verification_required": True,
        "external_base_report_hash_required": True,
        "external_report19_extension_hash_required": True,
        "external_registry_bindings_required": True,
        "external_stability_bindings_required": True,
        "external_stability_binding_fields": list(
            _EXTERNAL_STABILITY_BINDING_FIELDS
        ),
        "one_stability_gate_per_report_identity_required": True,
        "expected_stability_gate_hash_required": True,
        "stability_gate_exact_rebuild_required": True,
        "preregistration_matrix_selection_exact_binding_required": True,
        "contract_status_decision_separation_required": True,
        "native_json_type_exactness_required": True,
        "report20_payload_excluded_fields": list(_REPORT20_EXCLUDED_FIELDS),
        "report20_verifier_only": True,
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


def build_strategy_correlation_cluster_stability_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    source = source_registration if type(source_registration) is dict else {}
    policy = _build_policy()
    registration = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "source_registration": source,
        "source_registration_hash": source.get("registration_hash"),
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "cluster_preregistration_hash": source.get("cluster_preregistration_hash"),
        "uncertainty_policy_hash": source.get("uncertainty_policy_hash"),
        "multiplicity_policy_hash": source.get("multiplicity_policy_hash"),
        "family_registration_hash": source.get("family_registration_hash"),
        "complete_link_policy_hash": source.get("complete_link_policy_hash"),
        "strata_policy_hash": source.get("strata_policy_hash"),
        "global_independence_policy_hash": source.get(
            "global_independence_policy_hash"
        ),
        "cluster_stability_policy": policy,
        "cluster_stability_policy_hash": policy["policy_hash"],
        "stability_gate_policy_schema_version": STABILITY_GATE_POLICY_SCHEMA_VERSION,
        "stability_audit_schema_version": STABILITY_AUDIT_SCHEMA_VERSION,
        "stability_gate_schema_version": STABILITY_GATE_SCHEMA_VERSION,
        "schema20_consumer_available": True,
        "report20_verifier_only": True,
        "stability_gate_required": True,
        "external_stability_bindings_required": True,
        "registry_asset_schema_version": source.get("registry_asset_schema_version"),
        "registry_binding_schema_version": source.get(
            "registry_binding_schema_version"
        ),
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "status": "PREREGISTERED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(registration, "registration_hash")


def verify_strategy_correlation_cluster_stability_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("cluster_stability_protocol_registration_invalid")
        source_registration = {}
    else:
        source_registration = document.get("source_registration")
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
    try:
        source_verification = (
            verify_strategy_correlation_global_independence_protocol_registration(
                source_registration
            )
            if type(source_registration) is dict
            else {"status": "BLOCK"}
        )
    except (TypeError, ValueError):
        source_verification = {"status": "BLOCK"}
    if source_verification.get("status") != "PASS":
        blockers.append("source_registration_v6_invalid")

    expected = build_strategy_correlation_cluster_stability_protocol_registration(
        source_registration
    )
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("cluster_stability_protocol_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "cluster_stability_policy_schema_version": POLICY_SCHEMA_VERSION,
        "stability_gate_schema_version": STABILITY_GATE_SCHEMA_VERSION,
        "schema20_consumer_available": True,
        "report20_verifier_only": True,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "BASE_PROTOCOL_SCHEMA_VERSION",
    "BASE_REPORT_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "SOURCE_POLICY_SCHEMA_VERSION",
    "SOURCE_REGISTRATION_SCHEMA_VERSION",
    "TARGET_EXTENSION_SCHEMA_VERSION",
    "TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_stability_protocol_registration",
    "verify_strategy_correlation_cluster_stability_protocol_registration",
]
