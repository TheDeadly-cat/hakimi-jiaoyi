"""Candidate capability registration for report22 verifier and builder."""

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
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_protocol import (
    REGISTRATION_SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    VERIFICATION_SCHEMA_VERSION as REPORT22_CONSUMER_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_extension_builder import (
    INPUT_SCHEMA_VERSION as REPORT22_BUILDER_INPUT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_date_grid_report_extension,
)


POLICY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-candidate-capability-policy-v1"
)
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v10"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v10-verification-v1"
)
AVAILABILITY_SCOPE = "IN_MEMORY_VERIFIER_AND_BUILDER_ONLY"

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _build_capability_policy() -> dict[str, Any]:
    consumer_callable = callable(
        verify_strategy_correlation_cluster_temporal_date_grid_report_extension
    )
    builder_callable = callable(
        build_strategy_correlation_cluster_temporal_date_grid_report_extension
    )
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "report22_consumer_verification_schema_version": (
            REPORT22_CONSUMER_VERIFICATION_SCHEMA_VERSION
        ),
        "report22_builder_input_schema_version": (
            REPORT22_BUILDER_INPUT_SCHEMA_VERSION
        ),
        "report22_consumer_callable_name": (
            "verify_strategy_correlation_cluster_temporal_date_grid_report_extension"
        ),
        "report22_builder_callable_name": (
            "build_strategy_correlation_cluster_temporal_date_grid_report_extension"
        ),
        "report22_consumer_callable_bound": consumer_callable,
        "report22_builder_callable_bound": builder_callable,
        "availability_scope": AVAILABILITY_SCOPE,
        "deterministic_in_memory_builder_required": True,
        "self_verification_required": True,
        "exact_identity_set_required": True,
        "independent_expected_gate_hashes_required": True,
        "targeted_contract_validation_embedded": False,
        "candidate_validation_authority": False,
        "migration_assessment_available": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "writer_available": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(policy, "policy_hash")


def build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
    source_registration: Any,
) -> dict[str, Any]:
    source = deepcopy(source_registration) if type(source_registration) is dict else {}
    policy = _build_capability_policy()
    candidate_available = (
        policy["report22_consumer_callable_bound"] is True
        and policy["report22_builder_callable_bound"] is True
    )
    registration = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "source_registration": source,
        "source_registration_hash": source.get("registration_hash", ""),
        "candidate_capability_policy": policy,
        "candidate_capability_policy_hash": policy["policy_hash"],
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "report22_consumer_verification_schema_version": (
            REPORT22_CONSUMER_VERIFICATION_SCHEMA_VERSION
        ),
        "report22_builder_input_schema_version": (
            REPORT22_BUILDER_INPUT_SCHEMA_VERSION
        ),
        "availability_scope": AVAILABILITY_SCOPE,
        "report22_consumer_candidate_available": candidate_available,
        "report22_builder_candidate_available": candidate_available,
        "report22_candidate_activation_allowed": False,
        "targeted_contract_validation_embedded": False,
        "candidate_validation_authority": False,
        "migration_assessment_available": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "status": "CANDIDATE_IMPLEMENTED" if candidate_available else "BLOCK",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(registration, "registration_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("date_grid_candidate_registration_invalid")
        source_registration = {}
    else:
        source_registration = document.get("source_registration")
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
    try:
        source_verification = (
            verify_strategy_correlation_cluster_temporal_date_grid_protocol_registration(
                source_registration
            )
            if type(source_registration) is dict
            else {"status": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        source_verification = {"status": "BLOCK"}
    if source_verification.get("status") != "PASS":
        blockers.append("source_registration_v9_invalid")

    expected = (
        build_strategy_correlation_cluster_temporal_date_grid_candidate_registration(
            source_registration
        )
    )
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("date_grid_candidate_registration_contract_invalid")
    if expected.get("status") != "CANDIDATE_IMPLEMENTED":
        blockers.append("report22_candidate_capabilities_unavailable")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "availability_scope": AVAILABILITY_SCOPE,
        "report22_consumer_candidate_available": (
            status == "PASS"
            and expected["report22_consumer_candidate_available"] is True
        ),
        "report22_builder_candidate_available": (
            status == "PASS"
            and expected["report22_builder_candidate_available"] is True
        ),
        "report22_candidate_activation_allowed": False,
        "targeted_contract_validation_embedded": False,
        "candidate_validation_authority": False,
        "migration_assessment_available": False,
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "AVAILABILITY_SCOPE",
    "POLICY_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "REPORT22_BUILDER_INPUT_SCHEMA_VERSION",
    "REPORT22_CONSUMER_VERIFICATION_SCHEMA_VERSION",
    "SOURCE_REGISTRATION_SCHEMA_VERSION",
    "TARGET_EXTENSION_SCHEMA_VERSION",
    "TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_temporal_date_grid_candidate_registration",
    "verify_strategy_correlation_cluster_temporal_date_grid_candidate_registration",
]
