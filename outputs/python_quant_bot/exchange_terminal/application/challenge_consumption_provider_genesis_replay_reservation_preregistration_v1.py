"""Preregister an external genesis replay-reservation provider."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.application.ports.challenge_consumption_provider_genesis_replay_reservation_provider_v1 import (
    RESERVATION_NAMESPACE,
    RESERVE_ONCE_COMMAND_SCHEMA_VERSION,
    RESERVE_ONCE_RESULT_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-"
    "provider-preregistration-v1"
)
CONFORMANCE_PLAN_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-"
    "provider-conformance-plan-v1"
)
STATIC_FINGERPRINT = (
    "20260824-challenge-consumption-provider-genesis-replay-"
    "reservation-provider-preregistration-v1-lock-1"
)
PROVIDER_PROTOCOL_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-port-v1"
)
TARGET_SIGNED_RECEIPT_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-"
    "signed-receipt-v1"
)
RESERVATION_PORT_IMPLEMENTATION_SHA256 = (
    "1d8ddf5cbe28481e9b5f911cdd776891d1692c6a2e8183f9bf17e01473924512"
)
GENESIS_ADMISSION_IMPLEMENTATION_SHA256 = (
    "9dba83afda64034335a37e704d000fb1d083c6f617f6bea4211222e45afc553d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_CASES = (
    ("matching_state_reserves_once", "RESERVED"),
    ("sequential_duplicate_precedes_conflict", "ALREADY_RESERVED"),
    ("changed_request_same_key_is_duplicate", "ALREADY_RESERVED"),
    ("same_key_concurrency_has_one_winner", "ONE_RESERVED_ONE_DUPLICATE"),
    ("distinct_keys_same_base_cas_contend", "ONE_RESERVED_ONE_CONFLICT"),
    ("stale_state_fresh_key_conflicts", "COMPARE_AND_SWAP_CONFLICT"),
    ("result_binds_exact_command_hash", "EXACT_RESULT"),
    ("returned_head_derivation_is_exact", "EXACT_HEAD"),
    ("timeout_after_commit_retry_is_duplicate", "ALREADY_RESERVED"),
    ("restart_preserves_reserved_membership", "DURABLE_RECOVERY"),
    ("rollback_attempt_is_detected", "ROLLBACK_REJECTED"),
    ("reserved_result_has_signed_receipt", "SIGNED_RECEIPT_VERIFIED"),
    ("read_after_write_is_linearizable", "LINEARIZABLE_READ"),
)


class GenesisReplayReservationProviderPreregistrationError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise GenesisReplayReservationProviderPreregistrationError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise GenesisReplayReservationProviderPreregistrationError(
            f"{label} must be a strict identifier"
        )
    return value


def _authority() -> dict[str, bool]:
    return {
        "reserve_once_allowed": False,
        "signed_receipt_issuance_allowed": False,
        "provider_registration_allowed": False,
        "external_conformance_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def build_genesis_replay_reservation_provider_preregistration_v1(
    *,
    registry_id: Any,
    operator_identity_claim: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    provider_implementation_claim_sha256: Any,
    provider_protocol_version: Any = PROVIDER_PROTOCOL_VERSION,
) -> dict[str, Any]:
    protocol = _require_identifier(
        provider_protocol_version, "provider_protocol_version"
    )
    if protocol != PROVIDER_PROTOCOL_VERSION:
        raise GenesisReplayReservationProviderPreregistrationError(
            "provider protocol alias is forbidden"
        )
    identity = {
        "registry_id": _require_identifier(registry_id, "registry_id"),
        "operator_identity_claim": _require_identifier(
            operator_identity_claim, "operator_identity_claim"
        ),
        "public_key_spki_sha256": _require_hash(
            public_key_spki_sha256, "public_key_spki_sha256"
        ),
        "trust_domain": _require_identifier(trust_domain, "trust_domain"),
        "provider_implementation_claim_sha256": _require_hash(
            provider_implementation_claim_sha256,
            "provider_implementation_claim_sha256",
        ),
    }
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "GENESIS_REPLAY_RESERVATION_PROVIDER_PREREGISTERED_EXTERNAL_"
            "IDENTITY_KEY_CONTROL_IMPLEMENTATION_AND_CONFORMANCE_UNVERIFIED"
        ),
        "identity": identity,
        "source": {
            "registry_namespace": RESERVATION_NAMESPACE,
            "provider_protocol_version": protocol,
            "reserve_once_command_schema_version": (
                RESERVE_ONCE_COMMAND_SCHEMA_VERSION
            ),
            "reserve_once_result_schema_version": (
                RESERVE_ONCE_RESULT_SCHEMA_VERSION
            ),
            "target_signed_receipt_schema_version": (
                TARGET_SIGNED_RECEIPT_SCHEMA_VERSION
            ),
            "reservation_port_implementation_sha256": (
                RESERVATION_PORT_IMPLEMENTATION_SHA256
            ),
            "genesis_admission_implementation_sha256": (
                GENESIS_ADMISSION_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "requirements": [
            "ATOMIC_RESERVE_ONCE",
            "EXACT_GENESIS_ADMISSION_REPLAY_KEY",
            "EXACT_THRESHOLD_ADMISSION_EVIDENCE",
            "DUPLICATE_BEFORE_CONFLICT",
            "CHANGED_REQUEST_SAME_KEY_DUPLICATE",
            "DISTINCT_KEY_CAS_CONFLICT",
            "LINEARIZABLE_READ_AFTER_WRITE",
            "DURABLE_RESTART_RECOVERY",
            "ROLLBACK_RESISTANCE",
            "TIMEOUT_AFTER_COMMIT_IDEMPOTENCY",
            "SIGNED_RESERVATION_RECEIPT_V1",
            "PREREGISTERED_ED25519_PROVIDER_KEY",
            "INDEPENDENT_CONFORMANCE_OBSERVER",
        ],
        "facts": {
            "local_preregistration_complete": True,
            "provider_identity_fields_preregistered": True,
            "provider_public_key_hash_preregistered": True,
            "provider_implementation_claim_preregistered": True,
            "provider_schema_capabilities_preregistered": True,
            "provider_registered": False,
            "provider_identity_verified": False,
            "provider_key_possession_verified": False,
            "provider_implementation_verified": False,
            "external_provider_conformance_verified": False,
            "external_atomicity_verified": False,
            "durability_verified": False,
            "linearizability_verified": False,
            "signed_reservation_receipt_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "PROVIDER_KEY_POSSESSION_UNVERIFIED",
            "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
            "PROVIDER_IMPLEMENTATION_UNVERIFIED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "EXTERNAL_ATOMICITY_UNVERIFIED",
            "DURABILITY_UNVERIFIED",
            "LINEARIZABILITY_UNVERIFIED",
            "SIGNED_RESERVATION_RECEIPT_MISSING",
            "INDEPENDENT_CONFORMANCE_OBSERVER_UNBOUND",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_genesis_replay_reservation_provider_preregistration_v1(
    document: Any, **kwargs: Any
) -> bool:
    try:
        return document == build_genesis_replay_reservation_provider_preregistration_v1(
            **kwargs
        )
    except (TypeError, GenesisReplayReservationProviderPreregistrationError):
        return False


def build_genesis_replay_reservation_provider_conformance_plan_v1(
    preregistration_document: Any,
    **preregistration_kwargs: Any,
) -> dict[str, Any]:
    expected = build_genesis_replay_reservation_provider_preregistration_v1(
        **copy.deepcopy(preregistration_kwargs)
    )
    if preregistration_document != expected:
        raise GenesisReplayReservationProviderPreregistrationError(
            "provider preregistration is not exact"
        )
    cases = [
        {
            "case_id": f"R{index:02d}",
            "name": name,
            "expected": outcome,
            "executed": False,
            "observed": None,
        }
        for index, (name, outcome) in enumerate(_CASES, start=1)
    ]
    document = {
        "schema_version": CONFORMANCE_PLAN_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "GENESIS_REPLAY_RESERVATION_CONFORMANCE_PLAN_FROZEN_"
            "UNEXECUTED_EXTERNAL_PROVIDER_UNBOUND"
        ),
        "source": {
            "preregistration_hash": expected["preregistration_hash"],
            "registry_namespace": RESERVATION_NAMESPACE,
            "provider_protocol_version": PROVIDER_PROTOCOL_VERSION,
            "reserve_once_command_schema_version": (
                RESERVE_ONCE_COMMAND_SCHEMA_VERSION
            ),
            "reserve_once_result_schema_version": (
                RESERVE_ONCE_RESULT_SCHEMA_VERSION
            ),
        },
        "summary": {
            "planned_case_count": len(cases),
            "executed_case_count": 0,
            "passed_case_count": 0,
            "failed_case_count": 0,
            "runtime_mutations": False,
        },
        "cases": cases,
        "facts": {
            "plan_shape_frozen": True,
            "all_cases_unexecuted": True,
            "external_provider_bound": False,
            "external_provider_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "EXTERNAL_PROVIDER_UNBOUND",
            "CONFORMANCE_CASES_UNEXECUTED",
            "SIGNED_RESERVATION_RECEIPT_MISSING",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "conformance_plan_hash")


def verify_genesis_replay_reservation_provider_conformance_plan_v1(
    document: Any,
    preregistration_document: Any,
    *,
    expected_conformance_plan_hash: Any,
    **preregistration_kwargs: Any,
) -> bool:
    try:
        expected = build_genesis_replay_reservation_provider_conformance_plan_v1(
            preregistration_document, **preregistration_kwargs
        )
        return (
            document == expected
            and _require_hash(
                expected_conformance_plan_hash,
                "expected_conformance_plan_hash",
            )
            == expected["conformance_plan_hash"]
        )
    except (TypeError, GenesisReplayReservationProviderPreregistrationError):
        return False


__all__ = [
    "CONFORMANCE_PLAN_SCHEMA_VERSION",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_PROTOCOL_VERSION",
    "GenesisReplayReservationProviderPreregistrationError",
    "build_genesis_replay_reservation_provider_conformance_plan_v1",
    "build_genesis_replay_reservation_provider_preregistration_v1",
    "verify_genesis_replay_reservation_provider_conformance_plan_v1",
    "verify_genesis_replay_reservation_provider_preregistration_v1",
]
