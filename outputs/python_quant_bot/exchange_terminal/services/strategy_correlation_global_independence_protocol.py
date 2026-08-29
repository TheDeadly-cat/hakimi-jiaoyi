"""Protocol-v8 preregistration for report-19 global-independence evidence.

The registration freezes the consumer contract and exact graph policy only. It
does not provide a formal registry, report writer, current-pointer mutation, or
paper/live authority.
"""

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
from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    EXTENSION_SCHEMA_VERSION as TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_strata_global_independence import (
    AUDIT_SCHEMA_VERSION as GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION,
    GATE_SCHEMA_VERSION as GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION,
    MAX_EXACT_CLUSTER_COUNT,
    MAX_SEARCH_NODES,
    MINIMUM_GLOBAL_INDEPENDENT_VOTES,
    REQUIRED_GLOBAL_INDEPENDENT_FRACTION,
)
from exchange_terminal.services.strategy_correlation_strata_protocol import (
    EXTENSION_SCHEMA_VERSION as SOURCE_EXTENSION_SCHEMA_VERSION,
    EXTENSION_VERIFICATION_SCHEMA_VERSION as SOURCE_EXTENSION_VERIFICATION_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION as SOURCE_POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    REGISTRY_ASSET_SCHEMA_VERSION,
    REGISTRY_BINDING_SCHEMA_VERSION,
    STRATA_GATE_SCHEMA_VERSION as SOURCE_STRATA_GATE_SCHEMA_VERSION,
    STRATA_REGISTRATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as BASE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as BASE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_strata_protocol_registration,
)


POLICY_SCHEMA_VERSION = "strategy-correlation-global-independence-policy-v1"
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v6"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v6-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_INHERITED_HASH_FIELDS = (
    "cluster_preregistration_hash",
    "uncertainty_policy_hash",
    "multiplicity_policy_hash",
    "family_registration_hash",
    "complete_link_policy_hash",
    "strata_policy_hash",
)


def _build_global_independence_policy() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_registration_schema_version": SOURCE_REGISTRATION_SCHEMA_VERSION,
        "source_policy_schema_version": SOURCE_POLICY_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "source_extension_schema_version": SOURCE_EXTENSION_SCHEMA_VERSION,
        "source_extension_verification_schema_version": (
            SOURCE_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "source_strata_registration_schema_version": (
            STRATA_REGISTRATION_SCHEMA_VERSION
        ),
        "source_strata_gate_schema_version": SOURCE_STRATA_GATE_SCHEMA_VERSION,
        "registry_asset_schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_binding_schema_version": REGISTRY_BINDING_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "global_independence_audit_schema_version": (
            GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION
        ),
        "global_independence_gate_schema_version": (
            GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION
        ),
        "conflict_rule": "ANY_SHARED_PARENT_STRATUM_ACROSS_REGISTERED_DIMENSIONS",
        "independence_algorithm": "EXACT_MAXIMUM_INDEPENDENT_SET",
        "all_registered_dimensions_required": True,
        "registered_and_passing_capacity_required": True,
        "approximation_allowed": False,
        "exact_search_cluster_limit": MAX_EXACT_CLUSTER_COUNT,
        "exact_search_node_limit": MAX_SEARCH_NODES,
        "minimum_global_independent_votes": MINIMUM_GLOBAL_INDEPENDENT_VOTES,
        "required_global_independent_fraction": (
            REQUIRED_GLOBAL_INDEPENDENT_FRACTION
        ),
        "report18_extension_verification_required": True,
        "external_base_report_hash_required": True,
        "external_registry_bindings_required": True,
        "global_independence_gate_exact_rebuild_required": True,
        "contract_status_decision_separation_required": True,
        "native_json_type_exactness_required": True,
        "source_block_action": "PRESERVE_BLOCK",
        "writer_activation_prerequisites": [
            "INDEPENDENT_REPORT18_EXTENSION_VERIFICATION",
            "EXTERNAL_BASE_REPORT_HASH_BINDING",
            "EXTERNAL_REGISTRY_BINDINGS",
            "GLOBAL_INDEPENDENCE_GATE_V2_EXACT_REBUILD",
            "EXACT_MAXIMUM_INDEPENDENT_SET_WITHIN_REGISTERED_LIMITS",
            "PROTOCOL_V8_FORMAL_REGISTRY",
            "SCHEMA19_SOLE_WRITER_MIGRATION_TESTS",
        ],
        "formal_registry_activation_allowed": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(policy, "policy_hash")


def build_strategy_correlation_global_independence_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    """Build a research-only protocol-v8 preregistration from verified v5."""

    if type(source_registration) is not dict:
        raise ValueError("source_protocol_v7_registration_invalid")
    source_verification = verify_strategy_correlation_strata_protocol_registration(
        source_registration
    )
    if source_verification.get("status") != "PASS":
        raise ValueError("source_protocol_v7_registration_invalid")
    if strict_research_authority_violations(source_registration):
        raise ValueError("source_protocol_v7_authority_invalid")
    if source_registration.get("schema_version") != SOURCE_REGISTRATION_SCHEMA_VERSION:
        raise ValueError("source_protocol_v7_schema_invalid")
    if source_registration.get("target_protocol_schema_version") != (
        BASE_PROTOCOL_SCHEMA_VERSION
    ):
        raise ValueError("source_protocol_v7_target_invalid")
    if source_registration.get("target_report_schema_version") != (
        BASE_REPORT_SCHEMA_VERSION
    ):
        raise ValueError("source_protocol_v7_report_invalid")

    policy = _build_global_independence_policy()
    source_copy = deepcopy(source_registration)
    registration = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "source_registration": source_copy,
        "source_registration_hash": source_copy["registration_hash"],
        **{
            field: source_copy[field]
            for field in _INHERITED_HASH_FIELDS
        },
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "registry_asset_schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_binding_schema_version": REGISTRY_BINDING_SCHEMA_VERSION,
        "global_independence_policy": policy,
        "global_independence_policy_hash": policy["policy_hash"],
        "global_independence_audit_schema_version": (
            GLOBAL_INDEPENDENCE_AUDIT_SCHEMA_VERSION
        ),
        "global_independence_gate_schema_version": (
            GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION
        ),
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "global_independence_gate_v2_required": True,
        "schema19_consumer_available": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "status": "PREREGISTERED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(registration, "registration_hash")


def _verification(status: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "global_independence_gate_schema_version": (
            GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION
        ),
        "schema19_consumer_available": status == "PASS",
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_global_independence_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    """Verify registration-v6 by exact reconstruction from embedded v5."""

    if type(document) is not dict:
        return _verification(
            "BLOCK", ["global_independence_protocol_registration_invalid"]
        )
    blockers: list[str] = []
    if strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    source_registration = document.get("source_registration")
    if type(source_registration) is not dict:
        blockers.append("source_protocol_v7_registration_invalid")
        expected = None
    else:
        try:
            expected = (
                build_strategy_correlation_global_independence_protocol_registration(
                    source_registration
                )
            )
        except (KeyError, TypeError, ValueError):
            blockers.append("source_protocol_v7_registration_invalid")
            expected = None
    if expected is not None and not strict_json_contract_equal(document, expected):
        blockers.append("global_independence_protocol_registration_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return _verification(status, blockers)


__all__ = [
    "BASE_PROTOCOL_SCHEMA_VERSION",
    "BASE_REPORT_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "build_strategy_correlation_global_independence_protocol_registration",
    "verify_strategy_correlation_global_independence_protocol_registration",
]
