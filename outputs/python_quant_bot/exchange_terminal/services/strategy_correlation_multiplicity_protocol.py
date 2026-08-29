from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_json_hash import canonical_hash
from .execution_authority import authority_violations
from .strategy_correlation_multiplicity_registration import (
    STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_multiplicity_family_registration,
)
from .strategy_correlation_protocol_binding import (
    STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2,
    verify_strategy_correlation_protocol_registration,
)


STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v3"
)
STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v3-verification-v1"
)
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v5"
TARGET_REPORT_SCHEMA_VERSION = 16
TARGET_MATRIX_REPORT_SCHEMA_VERSION = 8

_REGISTRATION_FIELDS = frozenset({
    "schema_version",
    "status",
    "target_protocol_schema_version",
    "target_report_schema_version",
    "target_matrix_report_schema_version",
    "source_protocol_registration",
    "source_registration_hash",
    "family_registration",
    "family_registration_hash",
    "cluster_preregistration_hash",
    "uncertainty_policy_hash",
    "multiplicity_policy_hash",
    "family_definition",
    "input_scope",
    "source_before_returns_asserted",
    "requires_replayed_gate",
    "requires_uncertainty_audit",
    "requires_multiplicity_audit",
    "requires_matrix_report_consumer",
    "formal_registry_bound",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "permissions",
    "blockers",
    "registration_hash",
})


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    document = dict(payload)
    document["registration_hash"] = canonical_hash(document)
    return document


def _invalid_registration(blocker: str) -> dict[str, Any]:
    return _sealed({
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION
        ),
        "status": "BLOCK",
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_matrix_report_schema_version": TARGET_MATRIX_REPORT_SCHEMA_VERSION,
        "source_protocol_registration": None,
        "source_registration_hash": None,
        "family_registration": None,
        "family_registration_hash": None,
        "cluster_preregistration_hash": None,
        "uncertainty_policy_hash": None,
        "multiplicity_policy_hash": None,
        "family_definition": None,
        "input_scope": "PREREGISTRATION_ONLY",
        "source_before_returns_asserted": False,
        "requires_replayed_gate": True,
        "requires_uncertainty_audit": True,
        "requires_multiplicity_audit": True,
        "requires_matrix_report_consumer": True,
        "formal_registry_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "blockers": [str(blocker or "family_registration_invalid")],
    })


def build_strategy_correlation_multiplicity_protocol_registration(
    family_registration: Any,
) -> dict[str, Any]:
    family_verification = (
        verify_strategy_correlation_multiplicity_family_registration(
            family_registration
        )
    )
    if (
        family_verification.get("status") != "PASS"
        or not isinstance(family_registration, dict)
        or family_registration.get("status") != "PREREGISTERED"
        or family_registration.get("schema_version")
        != STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_REGISTRATION_SCHEMA_VERSION
    ):
        return _invalid_registration("family_registration_invalid")

    source_registration = family_registration.get("source_protocol_registration")
    source_verification = verify_strategy_correlation_protocol_registration(
        source_registration
    )
    if (
        source_verification.get("status") != "PASS"
        or not isinstance(source_registration, dict)
        or source_registration.get("schema_version")
        != STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2
    ):
        return _invalid_registration("source_protocol_registration_invalid")

    source_hash = str(source_registration.get("registration_hash") or "")
    family_hash = str(family_registration.get("family_registration_hash") or "")
    if (
        not source_hash
        or source_hash != str(family_registration.get("source_registration_hash") or "")
        or not family_hash
    ):
        return _invalid_registration("registration_hash_binding_invalid")

    return _sealed({
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION
        ),
        "status": "PREREGISTERED",
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_matrix_report_schema_version": TARGET_MATRIX_REPORT_SCHEMA_VERSION,
        "source_protocol_registration": deepcopy(source_registration),
        "source_registration_hash": source_hash,
        "family_registration": deepcopy(family_registration),
        "family_registration_hash": family_hash,
        "cluster_preregistration_hash": str(
            family_registration.get("cluster_preregistration_hash") or ""
        ),
        "uncertainty_policy_hash": str(
            source_registration.get("uncertainty_policy_hash") or ""
        ),
        "multiplicity_policy_hash": str(
            family_registration.get("multiplicity_policy_hash") or ""
        ),
        "family_definition": deepcopy(family_registration.get("family_definition")),
        "input_scope": "PREREGISTRATION_ONLY",
        "source_before_returns_asserted": True,
        "requires_replayed_gate": True,
        "requires_uncertainty_audit": True,
        "requires_multiplicity_audit": True,
        "requires_matrix_report_consumer": True,
        "formal_registry_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "blockers": [],
    })


def verify_strategy_correlation_multiplicity_protocol_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = dict(document) if isinstance(document, dict) else {}
    if set(payload) != _REGISTRATION_FIELDS:
        blockers.append("multiplicity_protocol_registration_fields_invalid")
    if payload.get("schema_version") != (
        STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_SCHEMA_VERSION
    ):
        blockers.append("multiplicity_protocol_registration_schema_invalid")

    clean = dict(payload)
    observed_hash = str(clean.pop("registration_hash", "") or "")
    if not observed_hash or canonical_hash(clean) != observed_hash:
        blockers.append("multiplicity_protocol_registration_hash_invalid")

    expected = build_strategy_correlation_multiplicity_protocol_registration(
        payload.get("family_registration")
    )
    if payload != expected:
        blockers.append("multiplicity_protocol_registration_replay_mismatch")

    blockers.extend(
        f"multiplicity_protocol_registration_authority:{item}"
        for item in authority_violations(payload)
    )
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_PROTOCOL_REGISTRATION_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "registration_status": str(payload.get("status") or "BLOCK"),
        "registration_hash": observed_hash or None,
        "blockers": sorted(set(blockers)),
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
