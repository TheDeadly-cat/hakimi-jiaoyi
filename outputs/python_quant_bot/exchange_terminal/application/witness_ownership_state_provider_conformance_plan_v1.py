"""Unmounted independent-observer conformance plan for ADR0414."""

from __future__ import annotations

import re
from typing import Any, Mapping

from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as provider_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


CONFORMANCE_PLAN_SCHEMA_VERSION = (
    "witness-ownership-state-provider-conformance-plan-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-conformance-plan-v1-lock-1"
)
TARGET_OBSERVER_REPORT_SCHEMA_VERSION = (
    "witness-ownership-provider-conformance-observer-report-v1"
)
TARGET_SIGNED_OBSERVER_REPORT_SCHEMA_VERSION = (
    "witness-ownership-provider-conformance-signed-observer-report-v1"
)
SIGNED_RECEIPT_IMPLEMENTATION_SHA256 = (
    "d0236dafac1f5c81170e97b1e58b4459c0b673814205242deb9adeada12d072d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
STRICT_ED25519_PUBLIC_IMPLEMENTATION_SHA256 = (
    "cfba98df59681ff8318d8a5f70aa37cb9f277f3db12d2f4e33dc427c6fb882d9"
)

EXPECTED_CASE_IDS = (
    "EXACT_ADVANCE_ACCEPTANCE",
    "CLAIM_CONSUMPTION_SINGLE_USE",
    "DUPLICATE_BEFORE_CONFLICT",
    "EXPECTED_STATE_CAS_CONFLICT",
    "EXPECTED_REVISION_CAS_CONFLICT",
    "COMMAND_HASH_REBINDING_REJECTION",
    "NAMESPACE_REBINDING_REJECTION",
    "OWNERSHIP_EVIDENCE_REBINDING_REJECTION",
    "RECEIPT_SCHEMA_EXACTNESS",
    "SIGNED_RECEIPT_BINDING",
    "TIMEOUT_AFTER_COMMIT_IDEMPOTENCY",
    "CONCURRENT_SAME_CLAIM_SINGLE_ADVANCE",
    "LINEARIZABLE_READ_AFTER_WRITE",
    "RESTART_STATE_RECOVERY",
    "ROLLBACK_REFUSAL",
    "DURABLE_COMMIT_ACKNOWLEDGEMENT",
    "REGISTRY_REVISION_MONOTONICITY",
    "PROVIDER_KEY_ROTATION_AND_REVOCATION",
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_OBSERVER_KEYS = frozenset(
    {
        "observer_id",
        "public_key_spki_sha256",
        "organization_claim_hash",
        "trust_domain",
    }
)


def _require_hash(name: str, value: Any) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_identifier(name: str, value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _normalize_observers(
    observer_registrations: Any,
    *,
    provider_public_key_spki_sha256: str,
) -> list[dict[str, str]]:
    if type(observer_registrations) is not list or len(observer_registrations) != 3:
        raise ValueError("exactly three observer registrations are required")
    normalized: list[dict[str, str]] = []
    for row in observer_registrations:
        if type(row) is not dict or frozenset(row) != _OBSERVER_KEYS:
            raise ValueError("observer registration shape is not exact")
        normalized.append(
            {
                "observer_id": _require_identifier(
                    "observer_id", row["observer_id"]
                ),
                "public_key_spki_sha256": _require_hash(
                    "public_key_spki_sha256",
                    row["public_key_spki_sha256"],
                ),
                "organization_claim_hash": _require_hash(
                    "organization_claim_hash",
                    row["organization_claim_hash"],
                ),
                "trust_domain": _require_identifier(
                    "trust_domain", row["trust_domain"]
                ),
            }
        )
    observer_ids = [row["observer_id"] for row in normalized]
    key_hashes = [row["public_key_spki_sha256"] for row in normalized]
    organization_hashes = [row["organization_claim_hash"] for row in normalized]
    if (
        len(set(observer_ids)) != 3
        or len(set(key_hashes)) != 3
        or len(set(organization_hashes)) != 3
        or provider_public_key_spki_sha256 in key_hashes
    ):
        raise ValueError("observer structural separation requirements failed")
    return sorted(normalized, key=lambda row: row["observer_id"])


def expected_witness_ownership_provider_conformance_cases_v1() -> list[dict[str, Any]]:
    return [
        {
            "case_id": case_id,
            "required": True,
            "execution_status": "NOT_RUN",
            "evidence_hash": None,
        }
        for case_id in EXPECTED_CASE_IDS
    ]


def build_witness_ownership_state_provider_conformance_plan_v1(
    provider_preregistration_document: Any,
    *,
    observer_registrations: Any,
    **provider_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if not provider_preregistration.verify_witness_ownership_state_provider_preregistration_v1(
        provider_preregistration_document,
        **provider_preregistration_kwargs,
    ):
        raise ValueError("provider preregistration is not exact")
    if not isinstance(provider_preregistration_document, Mapping):
        raise ValueError("provider preregistration must be a mapping")
    provider_key_hash = provider_preregistration_document["identity"][
        "public_key_spki_sha256"
    ]
    observers = _normalize_observers(
        observer_registrations,
        provider_public_key_spki_sha256=provider_key_hash,
    )
    body = {
        "schema_version": CONFORMANCE_PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "plan_status": "PREREGISTERED_NOT_RUN",
        "decision": (
            "CONFORMANCE_MATRIX_AND_OBSERVER_QUORUM_PREREGISTERED_"
            "EXTERNAL_EXECUTION_AND_SOURCE_TRUST_UNVERIFIED"
        ),
        "provider": {
            "preregistration_hash": provider_preregistration_document[
                "preregistration_hash"
            ],
            "registry_id": provider_preregistration_document["identity"][
                "registry_id"
            ],
            "public_key_spki_sha256": provider_key_hash,
            "provider_implementation_claim_sha256": (
                provider_preregistration_document["identity"][
                    "provider_implementation_claim_sha256"
                ]
            ),
        },
        "observer_policy": {
            "registered_observer_count": 3,
            "required_signature_quorum": 2,
            "observer_role": "INDEPENDENT_PROVIDER_CONFORMANCE_OBSERVER",
            "observer_ids_must_be_unique": True,
            "observer_keys_must_be_unique": True,
            "observer_organization_claims_must_be_unique": True,
            "observer_keys_must_differ_from_provider_key": True,
            "structural_difference_is_not_identity_or_independence_proof": True,
            "caller_supplied_independence_boolean_forbidden": True,
        },
        "observers": observers,
        "cases": expected_witness_ownership_provider_conformance_cases_v1(),
        "target": {
            "observer_report_schema_version": (
                TARGET_OBSERVER_REPORT_SCHEMA_VERSION
            ),
            "signed_observer_report_schema_version": (
                TARGET_SIGNED_OBSERVER_REPORT_SCHEMA_VERSION
            ),
            "signature_algorithm": "ED25519",
            "required_case_count": len(EXPECTED_CASE_IDS),
        },
        "source": {
            "signed_receipt_implementation_sha256": (
                SIGNED_RECEIPT_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "strict_ed25519_public_implementation_sha256": (
                STRICT_ED25519_PUBLIC_IMPLEMENTATION_SHA256
            ),
        },
        "facts": {
            "conformance_cases_preregistered": True,
            "executed_case_count": 0,
            "passed_case_count": 0,
            "observer_profiles_preregistered": True,
            "observer_identities_verified": False,
            "observer_independence_verified": False,
            "observer_source_trust_verified": False,
            "provider_called": False,
            "provider_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "provider_call_allowed": False,
            "observer_report_trust_allowed": False,
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(body, "conformance_plan_hash")


def verify_witness_ownership_state_provider_conformance_plan_v1(
    document: Any,
    provider_preregistration_document: Any,
    *,
    observer_registrations: Any,
    **provider_preregistration_kwargs: Any,
) -> bool:
    try:
        expected = build_witness_ownership_state_provider_conformance_plan_v1(
            provider_preregistration_document,
            observer_registrations=observer_registrations,
            **provider_preregistration_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "CONFORMANCE_PLAN_SCHEMA_VERSION",
    "EXPECTED_CASE_IDS",
    "STATIC_FINGERPRINT",
    "build_witness_ownership_state_provider_conformance_plan_v1",
    "expected_witness_ownership_provider_conformance_cases_v1",
    "verify_witness_ownership_state_provider_conformance_plan_v1",
]
