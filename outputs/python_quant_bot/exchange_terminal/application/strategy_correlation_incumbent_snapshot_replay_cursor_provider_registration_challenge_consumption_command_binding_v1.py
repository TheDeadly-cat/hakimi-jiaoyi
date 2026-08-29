"""Bind exact ADR0388 evidence to an ADR0389 consume-once command.

This application contract constructs immutable messages only. It never invokes
a consumption provider and grants no registration, runtime, or trading authority.
"""

from __future__ import annotations

import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_clock_attestation_binding_v1 as clock_binding,
)
from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1 as consumption_port,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


COMMAND_BINDING_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-registration-challenge-consumption-command-binding-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-replay-cursor-provider-registration-challenge-consumption-command-binding-v1-lock-1"
)
CLOCK_BINDING_IMPLEMENTATION_SHA256 = (
    "620ed3ec9805cf3c73f87bbc9da5b672cb4ceff65e7e9b0ed8ae7f43be7e0f05"
)
CONSUMPTION_PORT_IMPLEMENTATION_SHA256 = (
    "01c3e4aa2684352764bfbd30cf9ab9c377d300fd652a5f96928eecaaa608fa48"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")


class ChallengeConsumptionCommandBindingError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ChallengeConsumptionCommandBindingError(
            f"{label} must be lowercase sha256"
        )
    return value


def _authority() -> dict[str, bool]:
    return {
        "consume_once_allowed": False,
        "challenge_consumption_verified": False,
        "provider_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _require_exact_clock_binding(
    clock_binding_evidence: Any,
    clock_attestation: Any,
    clock_registration: Any,
    clock_receipts: Any,
    clock_public_keys_by_id: Any,
    challenge_evidence: Any,
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    expected_clock_binding_evidence_hash: Any,
    expected_clock_attestation_hash: Any,
    expected_clock_registration_hash: Any,
    expected_clock_receipt_hashes: Any,
    clock_verification_time_ms: Any,
    expected_challenge_evidence_hash: Any,
    challenge_evaluation_kwargs: Any,
) -> tuple[str, str, str]:
    expected_binding_hash = _require_hash(
        expected_clock_binding_evidence_hash,
        "expected_clock_binding_evidence_hash",
    )
    if (
        type(clock_binding_evidence) is not dict
        or clock_binding_evidence.get("clock_binding_evidence_hash")
        != expected_binding_hash
        or not clock_binding.verify_replay_cursor_provider_registration_challenge_clock_binding_evidence_v1(
            clock_binding_evidence,
            clock_attestation,
            clock_registration,
            clock_receipts,
            clock_public_keys_by_id,
            challenge_evidence,
            signed_challenge_document,
            challenge_document,
            provider_preregistration_document,
            challenge_authority_preregistration_document,
            expected_clock_binding_evidence_hash=expected_binding_hash,
            expected_clock_attestation_hash=expected_clock_attestation_hash,
            expected_clock_registration_hash=expected_clock_registration_hash,
            expected_clock_receipt_hashes=expected_clock_receipt_hashes,
            clock_verification_time_ms=clock_verification_time_ms,
            expected_challenge_evidence_hash=expected_challenge_evidence_hash,
            challenge_evaluation_kwargs=challenge_evaluation_kwargs,
        )
    ):
        raise ChallengeConsumptionCommandBindingError(
            "ADR0388 clock-binding evidence is not exact"
        )
    facts = clock_binding_evidence.get("facts")
    required_true = (
        "challenge_evidence_exact",
        "signed_challenge_source_verified",
        "clock_attestation_exact",
        "clock_context_bound_to_signed_challenge",
        "clock_nonce_bound_to_registration_nonce",
        "reference_time_inside_declared_challenge_window",
    )
    if (
        clock_binding_evidence.get("status") != "PASS"
        or type(facts) is not dict
        or any(facts.get(name) is not True for name in required_true)
        or type(clock_binding_evidence.get("authority")) is not dict
        or any(value is not False for value in clock_binding_evidence["authority"].values())
    ):
        raise ChallengeConsumptionCommandBindingError(
            "ADR0388 local binding facts are not exact and fail-closed"
        )
    source = clock_binding_evidence.get("source")
    if type(source) is not dict:
        raise ChallengeConsumptionCommandBindingError("ADR0388 source is invalid")
    signed_hash = _require_hash(
        source.get("signed_challenge_hash"), "signed_challenge_hash"
    )
    if (
        type(signed_challenge_document) is not dict
        or signed_challenge_document.get("signed_challenge_hash") != signed_hash
    ):
        raise ChallengeConsumptionCommandBindingError(
            "signed challenge does not match ADR0388 source"
        )
    if (
        type(challenge_document) is not dict
        or type(challenge_document.get("binding")) is not dict
    ):
        raise ChallengeConsumptionCommandBindingError("challenge binding is invalid")
    nonce_hash = _require_hash(
        challenge_document["binding"].get("registration_nonce_hash"),
        "registration_nonce_hash",
    )
    return signed_hash, nonce_hash, expected_binding_hash


def build_replay_cursor_provider_registration_challenge_consumption_command_binding_v1(
    clock_binding_evidence: Any,
    clock_attestation: Any,
    clock_registration: Any,
    clock_receipts: Any,
    clock_public_keys_by_id: Any,
    challenge_evidence: Any,
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    expected_clock_binding_evidence_hash: Any,
    expected_clock_attestation_hash: Any,
    expected_clock_registration_hash: Any,
    expected_clock_receipt_hashes: Any,
    clock_verification_time_ms: Any,
    expected_challenge_evidence_hash: Any,
    challenge_evaluation_kwargs: Any,
    expected_registry_head_hash: Any,
    expected_provider_revision: Any,
    request_id_hash: Any,
) -> consumption_port.ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1:
    signed_hash, nonce_hash, binding_hash = _require_exact_clock_binding(
        clock_binding_evidence,
        clock_attestation,
        clock_registration,
        clock_receipts,
        clock_public_keys_by_id,
        challenge_evidence,
        signed_challenge_document,
        challenge_document,
        provider_preregistration_document,
        challenge_authority_preregistration_document,
        expected_clock_binding_evidence_hash=expected_clock_binding_evidence_hash,
        expected_clock_attestation_hash=expected_clock_attestation_hash,
        expected_clock_registration_hash=expected_clock_registration_hash,
        expected_clock_receipt_hashes=expected_clock_receipt_hashes,
        clock_verification_time_ms=clock_verification_time_ms,
        expected_challenge_evidence_hash=expected_challenge_evidence_hash,
        challenge_evaluation_kwargs=challenge_evaluation_kwargs,
    )
    try:
        return consumption_port.build_replay_cursor_provider_registration_challenge_consume_once_command_v1(
            signed_challenge_hash=signed_hash,
            challenge_clock_binding_evidence_hash=binding_hash,
            registration_nonce_hash=nonce_hash,
            expected_registry_head_hash=expected_registry_head_hash,
            expected_provider_revision=expected_provider_revision,
            request_id_hash=request_id_hash,
        )
    except (TypeError, ValueError) as exc:
        raise ChallengeConsumptionCommandBindingError(
            "ADR0389 command inputs are invalid"
        ) from exc


def build_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
    clock_binding_evidence: Any,
    *args: Any,
    expected_command_hash: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    command = build_replay_cursor_provider_registration_challenge_consumption_command_binding_v1(
        clock_binding_evidence, *args, **kwargs
    )
    command_hash = _require_hash(expected_command_hash, "expected_command_hash")
    if command.command_hash != command_hash:
        raise ChallengeConsumptionCommandBindingError("expected command hash mismatch")
    document = {
        "schema_version": COMMAND_BINDING_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "CONSUMPTION_COMMAND_EXACTLY_BOUND_PROVIDER_RESULT_DURABILITY_"
            "LINEARIZABILITY_AND_AUTHORITY_UNVERIFIED"
        ),
        "source": {
            "clock_binding_implementation_sha256": (
                CLOCK_BINDING_IMPLEMENTATION_SHA256
            ),
            "consumption_port_implementation_sha256": (
                CONSUMPTION_PORT_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "clock_binding_evidence_hash": (
                command.challenge_clock_binding_evidence_hash
            ),
            "signed_challenge_hash": command.signed_challenge_hash,
            "registration_nonce_hash": command.registration_nonce_hash,
            "command_hash": command.command_hash,
            "expected_registry_head_hash": command.expected_registry_head_hash,
            "expected_provider_revision": command.expected_provider_revision,
            "request_id_hash": command.request_id_hash,
        },
        "facts": {
            "clock_binding_evidence_exact": True,
            "signed_challenge_hash_bound": True,
            "registration_nonce_hash_bound": True,
            "clock_binding_evidence_hash_bound": True,
            "consume_once_command_exact": True,
            "consume_once_called": False,
            "provider_result_observed": False,
            "provider_registered": False,
            "external_atomicity_verified": False,
            "durability_verified": False,
            "linearizability_verified": False,
            "challenge_consumption_verified": False,
            "raw_clock_receipts_redacted": True,
            "raw_public_keys_redacted": True,
            "raw_signatures_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "CONSUMPTION_PROVIDER_UNREGISTERED",
            "CONSUME_ONCE_NOT_CALLED",
            "CONSUMPTION_RESULT_UNOBSERVED",
            "EXTERNAL_ATOMICITY_UNVERIFIED",
            "DURABILITY_UNVERIFIED",
            "LINEARIZABILITY_UNVERIFIED",
            "CHALLENGE_CONSUMPTION_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "command_binding_evidence_hash")


def verify_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
    evidence_document: Any,
    clock_binding_evidence: Any,
    *args: Any,
    expected_command_binding_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = build_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1(
            clock_binding_evidence, *args, **kwargs
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_command_binding_evidence_hash,
                "expected_command_binding_evidence_hash",
            )
            == expected["command_binding_evidence_hash"]
        )
    except (TypeError, ChallengeConsumptionCommandBindingError):
        return False


__all__ = [
    "COMMAND_BINDING_EVIDENCE_SCHEMA_VERSION",
    "ChallengeConsumptionCommandBindingError",
    "build_replay_cursor_provider_registration_challenge_consumption_command_binding_v1",
    "build_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1",
    "verify_replay_cursor_provider_registration_challenge_consumption_command_binding_evidence_v1",
]
