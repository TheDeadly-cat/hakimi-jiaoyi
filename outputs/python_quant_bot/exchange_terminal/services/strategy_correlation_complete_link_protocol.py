from __future__ import annotations

from typing import Any

try:
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    AUDIT_SCHEMA_VERSION,
    GATE_SCHEMA_VERSION,
    TOPOLOGY_RULE,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    ABSOLUTE_PEARSON_THRESHOLD,
    MINIMUM_PAIR_OVERLAP,
)
from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as EXTENSION_VERIFICATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_multiplicity_protocol import (
    STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_multiplicity_protocol_registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


POLICY_SCHEMA_VERSION = "strategy-correlation-complete-link-policy-v1"
REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v4"
REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v4-verification-v1"
)
BASE_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v5"
BASE_MATRIX_REPORT_SCHEMA_VERSION = 8

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_WRITER_ACTIVATION_PREREQUISITES = [
    "INDEPENDENT_SCHEMA16_VERIFICATION",
    "BASE_REPORT_HASH_BINDING",
    "COMPLETE_LINK_GATE_V2_REBUILD",
    "PROTOCOL_V6_FORMAL_REGISTRY",
    "SCHEMA17_SOLE_WRITER_MIGRATION_TESTS",
]


def _sha256(value: Any) -> str:
    return strict_canonical_hash(value)


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: _sha256(payload)}


def _verification(blockers: list[str]) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not unique else "BLOCK",
        "blockers": unique,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def build_strategy_correlation_complete_link_protocol_registration(
    source_registration: Any,
) -> dict[str, Any]:
    source_verification = (
        verify_strategy_correlation_multiplicity_protocol_registration(
            source_registration
        )
    )
    if source_verification.get("status") != "PASS":
        raise ValueError("complete_link_source_protocol_registration_invalid")
    if (
        source_registration.get("schema_version")
        != STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION
        or source_registration.get("target_protocol_schema_version")
        != BASE_PROTOCOL_SCHEMA_VERSION
        or source_registration.get("target_report_schema_version")
        != BASE_REPORT_SCHEMA_VERSION
        or source_registration.get("target_matrix_report_schema_version")
        != BASE_MATRIX_REPORT_SCHEMA_VERSION
    ):
        raise ValueError("complete_link_source_protocol_target_invalid")

    policy = _seal(
        {
            "schema_version": POLICY_SCHEMA_VERSION,
            "topology_rule": TOPOLOGY_RULE,
            "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
            "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
            "source_gate_schema_version": GATE_SCHEMA_VERSION,
            "source_audit_schema_version": AUDIT_SCHEMA_VERSION,
            "source_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "source_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_extension_schema_version": EXTENSION_SCHEMA_VERSION,
            "target_extension_verification_schema_version": (
                EXTENSION_VERIFICATION_SCHEMA_VERSION
            ),
            "base_report_hash_binding_required": True,
            "complete_link_gate_rebuild_required": True,
            "writer_activation_prerequisites": list(
                _WRITER_ACTIVATION_PREREQUISITES
            ),
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        },
        "policy_hash",
    )
    payload = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "status": "PREREGISTERED",
        "source_registration": source_registration,
        "source_registration_hash": source_registration["registration_hash"],
        "cluster_preregistration_hash": source_registration[
            "cluster_preregistration_hash"
        ],
        "family_registration_hash": source_registration[
            "family_registration_hash"
        ],
        "multiplicity_policy_hash": source_registration[
            "multiplicity_policy_hash"
        ],
        "uncertainty_policy_hash": source_registration[
            "uncertainty_policy_hash"
        ],
        "complete_link_policy": policy,
        "complete_link_policy_hash": policy["policy_hash"],
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "base_matrix_report_schema_version": BASE_MATRIX_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_extension_schema_version": EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "schema17_consumer_available": True,
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload, "registration_hash")


def verify_strategy_correlation_complete_link_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    if type(document) is not dict or type(document.get("source_registration")) is not dict:
        return _verification(["complete_link_protocol_registration_contract_invalid"])
    try:
        expected = build_strategy_correlation_complete_link_protocol_registration(
            document["source_registration"]
        )
    except (KeyError, TypeError, ValueError):
        return _verification(["complete_link_source_protocol_registration_invalid"])
    blockers = (
        []
        if type(document) is dict
        and strict_json_contract_equal(document, expected)
        else [
        "complete_link_protocol_registration_contract_invalid"
        ]
    )
    return _verification(blockers)
