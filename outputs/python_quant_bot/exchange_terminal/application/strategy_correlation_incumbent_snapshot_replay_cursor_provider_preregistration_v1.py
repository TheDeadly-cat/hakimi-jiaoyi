"""Fail-closed identity and capability preregistration for ADR0384."""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1 import (
    COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION,
    COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-preregistration-v1"
)
PREREGISTRATION_STATIC_FINGERPRINT = (
    "20260824-replay-cursor-provider-preregistration-v1-lock-1"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-preregistration-exact-rebuild-v1"
)
CONFORMANCE_PLAN_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-plan-v1"
)
CONFORMANCE_PLAN_STATIC_FINGERPRINT = (
    "20260824-replay-cursor-provider-conformance-plan-v1-lock-1"
)
CONFORMANCE_PLAN_VERIFICATION_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-conformance-plan-exact-rebuild-v1"
)

PROVIDER_PROTOCOL_VERSION = (
    "incumbent-snapshot-replay-cursor-compare-and-advance-port-v1"
)
PROVIDER_NAMESPACE = "strategy-correlation-incumbent-snapshot-replay-cursor-v1"
TARGET_SIGNED_RECEIPT_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-signed-receipt-v1"
)
PROVIDER_INTERFACE_IMPLEMENTATION_SHA256 = (
    "210f897078503e2a0e7a95d1f3c3a531d8331fe59b82684fb6f2fc14f01c09c5"
)
CAS_IMPLEMENTATION_SHA256 = (
    "4169466135a69ba25fc78621456c8a1f3f555c8cf3ca4d6080d1309c2eb14811"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_AUTHORITY_KEYS = (
    "current_activation_allowed",
    "live_order_allowed",
    "paper_authorized",
    "provider_registration_allowed",
    "runtime_gate_activation_allowed",
    "signed_receipt_issuance_allowed",
    "writer_allowed",
)
_BLOCKERS = (
    "PROVIDER_KEY_POSSESSION_UNVERIFIED",
    "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
    "DURABLE_ATOMIC_COMPARE_AND_ADVANCE_UNVERIFIED",
    "ROLLBACK_RESISTANCE_UNVERIFIED",
    "SIGNED_PROVIDER_RECEIPT_V1_MISSING",
    "INDEPENDENT_CONFORMANCE_OBSERVER_UNBOUND",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)
_REQUIRED_CAPABILITIES = (
    "ATOMIC_COMPARE_AND_ADVANCE",
    "EXACT_BASE_CURSOR_CAS",
    "DUPLICATE_BEFORE_CONFLICT",
    "NONMONOTONIC_SEQUENCE_REJECTION",
    "LINEARIZABLE_READ_AFTER_WRITE",
    "DURABLE_RESTART_RECOVERY",
    "ROLLBACK_RESISTANCE",
    "TIMEOUT_AFTER_COMMIT_IDEMPOTENCY",
    "SIGNED_RECEIPT_V1",
    "PREREGISTERED_ED25519_PROVIDER_KEY",
    "INDEPENDENT_CONFORMANCE_OBSERVER",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_hash(name: str, value: Any) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _validate_identifier(name: str, value: Any) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a bounded lowercase identifier")
    return value


def _validate_claim(name: str, value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty normalized claim")
    if len(value) > 256:
        raise ValueError(f"{name} exceeds its length bound")
    return value


def _preregistration_body(
    *,
    registry_id: str,
    operator_identity_claim: str,
    public_key_spki_sha256: str,
    trust_domain: str,
    provider_implementation_claim_sha256: str,
) -> dict[str, Any]:
    return {
        "authority": _locked_authority(),
        "blockers": list(_BLOCKERS),
        "checks": [
            {
                "blocking": True,
                "name": "provider_identity_fields_preregistered",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "provider_ed25519_public_key_hash_preregistered",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "provider_implementation_claim_preregistered",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "port_command_result_and_receipt_schemas_exact",
                "ok": True,
            },
            {
                "blocking": True,
                "name": "external_identity_and_capabilities_not_self_verified",
                "ok": True,
            },
        ],
        "decision": (
            "PROVIDER_IDENTITY_AND_CAPABILITY_PREREGISTERED_EXTERNAL_"
            "IDENTITY_KEY_CONTROL_AND_CONFORMANCE_UNVERIFIED"
        ),
        "facts": {
            "durable_atomic_compare_and_advance_verified": False,
            "external_endpoint_verified": False,
            "external_linearizability_verified": False,
            "external_provider_conformance_verified": False,
            "local_preregistration_complete": True,
            "network_accessed": False,
            "provider_identity_verified": False,
            "provider_implementation_claim_preregistered": True,
            "provider_implementation_verified": False,
            "provider_key_possession_verified": False,
            "provider_public_key_hash_preregistered": True,
            "provider_registered": False,
            "provider_schema_capabilities_preregistered": True,
            "runtime_assets_accessed": False,
            "signed_provider_receipt_issued": False,
            "signed_provider_receipt_verified": False,
        },
        "identity": {
            "key_algorithm": "Ed25519",
            "operator_identity_claim": operator_identity_claim,
            "provider_implementation_claim_sha256": (
                provider_implementation_claim_sha256
            ),
            "public_key_spki_sha256": public_key_spki_sha256,
            "registry_id": registry_id,
            "trust_domain": trust_domain,
        },
        "requirements": list(_REQUIRED_CAPABILITIES),
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "source": {
            "cas_implementation_sha256": CAS_IMPLEMENTATION_SHA256,
            "command_schema_version": (
                COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION
            ),
            "provider_interface_implementation_sha256": (
                PROVIDER_INTERFACE_IMPLEMENTATION_SHA256
            ),
            "provider_namespace": PROVIDER_NAMESPACE,
            "provider_protocol_version": PROVIDER_PROTOCOL_VERSION,
            "result_schema_version": COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "target_signed_receipt_schema_version": (
                TARGET_SIGNED_RECEIPT_SCHEMA_VERSION
            ),
        },
        "static_fingerprint": PREREGISTRATION_STATIC_FINGERPRINT,
        "status": "BLOCKED",
    }


def build_replay_cursor_provider_preregistration_v1(
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    provider_implementation_claim_sha256: Any,
    provider_protocol_version: Any = PROVIDER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    registry_id = _validate_identifier("registry_id", registry_id)
    operator_identity_claim = _validate_claim(
        "operator_identity_claim", operator_identity_claim
    )
    public_key_spki_sha256 = _validate_hash(
        "public_key_spki_sha256", public_key_spki_sha256
    )
    trust_domain = _validate_identifier("trust_domain", trust_domain)
    provider_implementation_claim_sha256 = _validate_hash(
        "provider_implementation_claim_sha256",
        provider_implementation_claim_sha256,
    )
    if provider_protocol_version != PROVIDER_PROTOCOL_VERSION:
        raise ValueError("provider protocol aliases are forbidden")
    return seal_strict_canonical_document(
        _preregistration_body(
            registry_id=registry_id,
            operator_identity_claim=operator_identity_claim,
            public_key_spki_sha256=public_key_spki_sha256,
            trust_domain=trust_domain,
            provider_implementation_claim_sha256=(
                provider_implementation_claim_sha256
            ),
        ),
        "preregistration_hash",
    )


def verify_replay_cursor_provider_preregistration_v1(
    document: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        expected = build_replay_cursor_provider_preregistration_v1(**kwargs)
        exact = strict_json_contract_equal(document, expected)
    except (TypeError, ValueError):
        exact = False
        expected = None
    return {
        "blockers": [] if exact else ["PROVIDER_PREREGISTRATION_EXACT_REBUILD"],
        "current_activation_allowed": False,
        "durable_atomic_compare_and_advance_verified": False,
        "external_linearizability_verified": False,
        "external_provider_conformance_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "preregistration_document_exactly_rebuilt": exact,
        "preregistration_hash": (
            expected["preregistration_hash"] if exact and expected else None
        ),
        "preregistration_status": "BLOCKED" if exact else "UNKNOWN",
        "provider_identity_verified": False,
        "provider_key_possession_verified": False,
        "provider_registered": False,
        "schema_version": PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "signed_provider_receipt_verified": False,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


def _conformance_cases() -> list[dict[str, Any]]:
    cases = (
        ("FIRST_ADVANCE", "NONE", "ONE_SIGNED_ADVANCED_RECEIPT"),
        ("EXACT_DUPLICATE", "EXACT_RETRY", "DUPLICATE_REJECTED_WITH_ORIGINAL_BINDING"),
        ("STALE_BASE_CONFLICT", "CHANGED_BASE_CURSOR", "CONFLICT_REJECTED_WITHOUT_STATE_CHANGE"),
        ("PARALLEL_SAME_INTENT", "PARALLEL_COLLISION", "EXACTLY_ONE_ADVANCED_ALL_OTHERS_REJECTED"),
        ("PARALLEL_DIFFERENT_INTENTS", "SAME_BASE_DIFFERENT_CANDIDATES", "AT_MOST_ONE_ADVANCED_FROM_BASE"),
        ("TIMEOUT_RETRY_IDEMPOTENCY", "TIMEOUT_AFTER_COMMIT", "RETRY_CANNOT_CREATE_SECOND_ADVANCE"),
        ("DURABLE_RESTART_RECOVERY", "PROCESS_RESTART", "HIGH_WATER_AND_CONSUMED_SET_SURVIVE_RESTART"),
        ("ROLLBACK_RESISTANCE", "STATE_ROLLBACK", "ROLLBACK_CANNOT_REOPEN_CONSUMED_ATTESTATION"),
        ("SIGNED_RECEIPT_BINDING", "RECEIPT_SUBSTITUTION", "HASH_OR_SIGNATURE_MISMATCH_REJECTED"),
        ("PROVIDER_KEY_BINDING", "UNPREREGISTERED_KEY_OR_ROTATION", "UNPREREGISTERED_SIGNING_KEY_REJECTED"),
        ("LINEARIZABLE_READ_AFTER_WRITE", "STALE_READ_AFTER_ADVANCE", "READ_OBSERVES_COMMITTED_HIGH_WATER"),
    )
    return [
        {
            "attack": attack,
            "case_id": case_id,
            "expected": expected,
            "requires_external_provider": True,
            "requires_independent_observer": True,
        }
        for case_id, attack, expected in cases
    ]


def build_replay_cursor_provider_conformance_plan_v1(
    preregistration_document: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    verification = verify_replay_cursor_provider_preregistration_v1(
        preregistration_document,
        **kwargs,
    )
    if verification["status"] != "PASS":
        raise ValueError("provider preregistration is not exact")
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "blockers": [
                "CONFORMANCE_CASES_NOT_EXECUTED",
                "EXTERNAL_PROVIDER_NOT_INVOKED",
                "INDEPENDENT_OBSERVER_NOT_BOUND",
                "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
                "DURABLE_ATOMIC_COMPARE_AND_ADVANCE_UNVERIFIED",
                "SIGNED_PROVIDER_RECEIPT_V1_MISSING",
                "CURRENT_ACTIVATION_UNAUTHORIZED",
            ],
            "cases": _conformance_cases(),
            "decision": (
                "CONFORMANCE_PLAN_PREREGISTERED_EXTERNAL_PROVIDER_AND_"
                "INDEPENDENT_OBSERVATION_REQUIRED"
            ),
            "facts": {
                "conformance_cases_executed": False,
                "conformance_cases_preregistered": True,
                "durable_atomic_compare_and_advance_verified": False,
                "external_linearizability_verified": False,
                "external_provider_conformance_verified": False,
                "external_provider_invoked": False,
                "external_runtime_accessed": False,
                "independent_observer_bound": False,
                "network_accessed": False,
                "provider_identity_verified": False,
                "signed_provider_receipt_verified": False,
            },
            "schema_version": CONFORMANCE_PLAN_SCHEMA_VERSION,
            "source": {
                "preregistration_hash": preregistration_document[
                    "preregistration_hash"
                ],
                "provider_implementation_claim_sha256": kwargs[
                    "provider_implementation_claim_sha256"
                ],
                "provider_protocol_version": PROVIDER_PROTOCOL_VERSION,
                "public_key_spki_sha256": kwargs["public_key_spki_sha256"],
                "registry_id": kwargs["registry_id"],
                "target_signed_receipt_schema_version": (
                    TARGET_SIGNED_RECEIPT_SCHEMA_VERSION
                ),
            },
            "static_fingerprint": CONFORMANCE_PLAN_STATIC_FINGERPRINT,
            "status": "BLOCKED",
        },
        "plan_hash",
    )


def verify_replay_cursor_provider_conformance_plan_v1(
    document: Any,
    preregistration_document: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        expected = build_replay_cursor_provider_conformance_plan_v1(
            preregistration_document,
            **kwargs,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "blockers": [] if exact else ["PROVIDER_CONFORMANCE_PLAN_EXACT_REBUILD"],
        "conformance_cases_executed": False,
        "current_activation_allowed": False,
        "durable_atomic_compare_and_advance_verified": False,
        "external_linearizability_verified": False,
        "external_provider_conformance_verified": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "plan_document_exactly_rebuilt": exact,
        "plan_hash": expected["plan_hash"] if exact and expected else None,
        "plan_status": "BLOCKED" if exact else "UNKNOWN",
        "provider_identity_verified": False,
        "provider_key_possession_verified": False,
        "schema_version": CONFORMANCE_PLAN_VERIFICATION_SCHEMA_VERSION,
        "signed_provider_receipt_verified": False,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "CAS_IMPLEMENTATION_SHA256",
    "CONFORMANCE_PLAN_SCHEMA_VERSION",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_INTERFACE_IMPLEMENTATION_SHA256",
    "PROVIDER_PROTOCOL_VERSION",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "build_replay_cursor_provider_conformance_plan_v1",
    "build_replay_cursor_provider_preregistration_v1",
    "verify_replay_cursor_provider_conformance_plan_v1",
    "verify_replay_cursor_provider_preregistration_v1",
]
