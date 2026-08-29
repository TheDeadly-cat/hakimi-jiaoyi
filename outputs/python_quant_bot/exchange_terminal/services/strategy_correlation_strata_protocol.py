"""Protocol-v7 registration for preregistered strata report18 evidence."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_complete_link_protocol import (
    REGISTRATION_SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as BASE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as BASE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_complete_link_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    GATE_SCHEMA as STRATA_GATE_SCHEMA_VERSION,
    REGISTRATION_SCHEMA as STRATA_REGISTRATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    BINDING_ASSESSMENT_SCHEMA as REGISTRY_BINDING_SCHEMA_VERSION,
    REGISTRY_ASSET_SCHEMA as REGISTRY_ASSET_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as EXTENSION_VERIFICATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


POLICY_SCHEMA_VERSION = "strategy-correlation-strata-policy-v1"
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v5"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v5-verification-v1"
)
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_WRITER_ACTIVATION_PREREQUISITES = [
    "INDEPENDENT_REPORT17_EXTENSION_VERIFICATION",
    "SOURCE_PREREGISTRATION_EXACT_REBUILD",
    "STRATA_REGISTRATION_EXACT_REBUILD",
    "STRATA_GATE_V1_REBUILD",
    "REGISTRY_ASSET_V1_VERIFICATION",
    "REGISTRY_BINDING_BOUND_WITH_EXTERNAL_HASHES",
    "SELECTION_CUTOFF_BINDING",
    "PROTOCOL_V7_FORMAL_REGISTRY",
    "SCHEMA18_SOLE_WRITER_MIGRATION_TESTS",
]


def _hash_without(document: dict[str, Any], hash_field: str) -> str:
    return strict_canonical_hash(
        {key: value for key, value in document.items() if key != hash_field}
    )


def _strata_policy() -> dict[str, Any]:
    policy: dict[str, Any] = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_registration_schema_version": (
            SOURCE_REGISTRATION_SCHEMA_VERSION
        ),
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_extension_schema_version": EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "strata_registration_schema_version": (
            STRATA_REGISTRATION_SCHEMA_VERSION
        ),
        "strata_gate_schema_version": STRATA_GATE_SCHEMA_VERSION,
        "registry_asset_schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_binding_schema_version": REGISTRY_BINDING_SCHEMA_VERSION,
        "report17_extension_verification_required": True,
        "source_preregistration_exact_rebuild_required": True,
        "strata_registration_exact_rebuild_required": True,
        "strata_gate_rebuild_required": True,
        "registry_asset_verification_required": True,
        "registry_binding_bound_required": True,
        "external_registry_asset_hash_required": True,
        "external_classification_source_hash_required": True,
        "selection_cutoff_binding_required": True,
        "real_registry_asset_required": True,
        "writer_activation_prerequisites": list(
            _WRITER_ACTIVATION_PREREQUISITES
        ),
        "writer_available": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    policy["policy_hash"] = _hash_without(policy, "policy_hash")
    return policy


def build_strategy_correlation_strata_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    source_verification = (
        verify_strategy_correlation_complete_link_protocol_registration(
            source_registration
        )
    )
    if source_verification.get("status") != "PASS":
        raise ValueError("source_protocol_v6_registration_invalid")
    if type(source_registration) is not dict:
        raise ValueError("source_protocol_v6_registration_invalid")
    if strict_research_authority_invalid(source_registration):
        raise ValueError("source_protocol_v6_authority_invalid")
    policy = _strata_policy()
    document: dict[str, Any] = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "status": "PREREGISTERED",
        "source_registration": source_registration,
        "source_registration_hash": source_registration["registration_hash"],
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_extension_schema_version": EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "cluster_preregistration_hash": source_registration[
            "cluster_preregistration_hash"
        ],
        "family_registration_hash": source_registration[
            "family_registration_hash"
        ],
        "uncertainty_policy_hash": source_registration[
            "uncertainty_policy_hash"
        ],
        "multiplicity_policy_hash": source_registration[
            "multiplicity_policy_hash"
        ],
        "complete_link_policy_hash": source_registration[
            "complete_link_policy_hash"
        ],
        "strata_policy": policy,
        "strata_policy_hash": policy["policy_hash"],
        "registry_asset_schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_binding_schema_version": REGISTRY_BINDING_SCHEMA_VERSION,
        "schema18_consumer_available": True,
        "registry_candidate_contract_available": True,
        "formal_registry_bound": False,
        "writer_available": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    document["registration_hash"] = _hash_without(
        document,
        "registration_hash",
    )
    return document


def verify_strategy_correlation_strata_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("strata_protocol_registration_contract_invalid")
    else:
        if strict_research_authority_invalid(document):
            blockers.append("strata_protocol_registration_authority_invalid")
        try:
            if document.get("registration_hash") != _hash_without(
                document,
                "registration_hash",
            ):
                blockers.append("strata_protocol_registration_hash_invalid")
        except (TypeError, ValueError):
            blockers.append("strata_protocol_registration_hash_invalid")
        try:
            expected = build_strategy_correlation_strata_protocol_registration(
                document.get("source_registration")
            )
        except (MemoryError, RecursionError):
            raise
        except (KeyError, TypeError, ValueError):
            blockers.append("strata_protocol_registration_rebuild_invalid")
        else:
            if document != expected:
                blockers.append(
                    "strata_protocol_registration_exact_rebuild_mismatch"
                )
    blockers = sorted(set(blockers))
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_extension_schema_version": EXTENSION_SCHEMA_VERSION,
        "schema18_consumer_available": True,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
