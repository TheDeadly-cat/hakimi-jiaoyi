"""Bind ADR0399 dual-signature evidence to signed clock observations."""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.application import (
    genesis_replay_reservation_provider_registration_handoff_v1 as handoff_contract,
)
from exchange_terminal.services import trusted_clock_authority_v3 as clock_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


CLOCK_BINDING_EVIDENCE_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-registration-clock-binding-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-provider-registration-clock-binding-"
    "v1-synthetic-lock-1"
)
CHALLENGE_SOURCE_IMPLEMENTATION_SHA256 = (
    "d01e45afd996d4c32e0f4267d649378dfba310902c39f5f0bf67092ee773b8b4"
)
HANDOFF_IMPLEMENTATION_SHA256 = (
    "e64301444c6e6dede1d6948a5aeaac1326a5c97749d6f8ebe744e4c7f8a3a1c6"
)
TRUSTED_CLOCK_IMPLEMENTATION_SHA256 = (
    "9a12682fb00dee3d6851ac62d4a37de0c66992e3f57d8e9715e23712d25a8c62"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_HASH = re.compile(r"^[0-9a-f]{64}$")


class GenesisReplayReservationProviderRegistrationClockBindingError(ValueError):
    pass


def _strict_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def _strict_int(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _copy_kwargs(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise GenesisReplayReservationProviderRegistrationClockBindingError(
            f"{label} must be a dict"
        )
    return copy.deepcopy(value)


def _authority() -> dict[str, bool]:
    return {
        "trusted_current_time_established": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "provider_registration_allowed": False,
        "external_conformance_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _empty_facts() -> dict[str, bool]:
    return {
        "handoff_evidence_exact": False,
        "dual_signature_handoff_verified": False,
        "challenge_source_key_signature_verified": False,
        "provider_key_signature_verified": False,
        "clock_attestation_exact": False,
        "clock_registration_integrity_verified": False,
        "clock_registered_public_key_hashes_verified": False,
        "clock_detached_signatures_verified": False,
        "clock_multi_authority_quorum_verified": False,
        "clock_context_bound_to_signed_challenge": False,
        "clock_nonce_bound_to_registration_nonce": False,
        "reference_time_inside_declared_challenge_window": False,
        "external_time_authority_trust_verified": False,
        "clock_registration_governance_verified": False,
        "verification_time_source_trusted": False,
        "request_nonce_uniqueness_verified": False,
        "clock_replay_registry_verified": False,
        "current_time_established": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "provider_registered": False,
        "external_provider_conformance_verified": False,
        "raw_clock_receipts_redacted": True,
        "raw_public_keys_redacted": True,
        "raw_signatures_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }


def evaluate_genesis_replay_reservation_provider_registration_clock_binding_v1(
    clock_attestation: Any,
    clock_registration: Any,
    clock_receipts: Any,
    clock_public_keys_by_id: Any,
    handoff_evidence: Any,
    challenge_evidence: Any,
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    provider_registration_evidence_document: Any,
    signed_provider_registration_document: Any,
    provider_registration_claim_document: Any,
    *,
    expected_clock_attestation_hash: Any,
    expected_clock_registration_hash: Any,
    expected_clock_receipt_hashes: Any,
    clock_verification_time_ms: Any,
    expected_handoff_evidence_hash: Any,
    expected_challenge_evidence_hash: Any,
    expected_provider_registration_evidence_hash: Any,
    challenge_evaluation_kwargs: Any,
    provider_registration_evaluation_kwargs: Any,
) -> dict[str, Any]:
    facts = _empty_facts()
    signed_challenge_hash = None
    registration_nonce_hash = None
    declared_issued_at_ms = None
    declared_expires_at_ms = None
    reference_time_ms = None
    source_count = None
    provider_spread_ms = None
    local_skew_ms = None

    if type(signed_challenge_document) is dict:
        signed_challenge_hash = _strict_hash(
            signed_challenge_document.get("signed_challenge_hash")
        )
    if (
        type(challenge_document) is dict
        and type(challenge_document.get("binding")) is dict
    ):
        challenge_binding = challenge_document["binding"]
        registration_nonce_hash = _strict_hash(
            challenge_binding.get("registration_nonce_hash")
        )
        declared_issued_at_ms = _strict_int(
            challenge_binding.get("issued_at_unix_ms")
        )
        declared_expires_at_ms = _strict_int(
            challenge_binding.get("expires_at_unix_ms")
        )

    try:
        challenge_kwargs = _copy_kwargs(
            challenge_evaluation_kwargs, "challenge_evaluation_kwargs"
        )
        provider_kwargs = _copy_kwargs(
            provider_registration_evaluation_kwargs,
            "provider_registration_evaluation_kwargs",
        )
        facts["handoff_evidence_exact"] = (
            handoff_contract.verify_genesis_replay_reservation_provider_registration_handoff_v1(
                handoff_evidence,
                challenge_evidence,
                signed_challenge_document,
                challenge_document,
                provider_preregistration_document,
                challenge_authority_preregistration_document,
                provider_registration_evidence_document,
                signed_provider_registration_document,
                provider_registration_claim_document,
                expected_handoff_evidence_hash=expected_handoff_evidence_hash,
                expected_challenge_evidence_hash=expected_challenge_evidence_hash,
                expected_provider_registration_evidence_hash=(
                    expected_provider_registration_evidence_hash
                ),
                challenge_evaluation_kwargs=challenge_kwargs,
                provider_registration_evaluation_kwargs=provider_kwargs,
            )
        )
    except (TypeError, ValueError):
        facts["handoff_evidence_exact"] = False

    if type(handoff_evidence) is dict and type(
        handoff_evidence.get("facts")
    ) is dict:
        handoff_facts = handoff_evidence["facts"]
        facts["dual_signature_handoff_verified"] = (
            facts["handoff_evidence_exact"]
            and handoff_evidence.get("status") == "PASS"
            and handoff_facts.get("dual_signature_handoff_exact") is True
        )
        facts["challenge_source_key_signature_verified"] = (
            facts["dual_signature_handoff_verified"]
            and handoff_facts.get("challenge_source_key_signature_verified")
            is True
        )
        facts["provider_key_signature_verified"] = (
            facts["dual_signature_handoff_verified"]
            and handoff_facts.get("provider_key_signature_verified") is True
        )

    clock_hash = _strict_hash(expected_clock_attestation_hash)
    registration_hash = _strict_hash(expected_clock_registration_hash)
    verification_time = _strict_int(clock_verification_time_ms)
    if (
        signed_challenge_hash is not None
        and registration_nonce_hash is not None
        and clock_hash is not None
        and registration_hash is not None
        and verification_time is not None
    ):
        try:
            facts["clock_attestation_exact"] = (
                type(clock_attestation) is dict
                and clock_attestation.get("attestation_hash") == clock_hash
                and clock_contract.verify_trusted_clock_authority_attestation_v3(
                    clock_attestation,
                    clock_registration,
                    clock_receipts,
                    clock_public_keys_by_id,
                    expected_registration_hash=registration_hash,
                    expected_receipt_hashes=expected_clock_receipt_hashes,
                    request_nonce_hash=registration_nonce_hash,
                    request_context_hash=signed_challenge_hash,
                    verification_time_ms=verification_time,
                )
            )
        except (
            TypeError,
            ValueError,
            clock_contract.TrustedClockAuthorityContractError,
        ):
            facts["clock_attestation_exact"] = False

    if facts["clock_attestation_exact"]:
        clock_facts = clock_attestation.get("facts", {})
        lineage = clock_attestation.get("source_lineage", {})
        verification = clock_attestation.get("verification", {})
        facts["clock_registration_integrity_verified"] = (
            clock_facts.get("registration_integrity_verified") is True
        )
        facts["clock_registered_public_key_hashes_verified"] = (
            clock_facts.get("registered_public_key_hashes_verified") is True
        )
        facts["clock_detached_signatures_verified"] = (
            clock_facts.get("detached_signatures_verified") is True
        )
        facts["clock_multi_authority_quorum_verified"] = (
            clock_facts.get("multi_authority_quorum_verified") is True
        )
        facts["clock_context_bound_to_signed_challenge"] = (
            lineage.get("request_context_hash") == signed_challenge_hash
        )
        facts["clock_nonce_bound_to_registration_nonce"] = (
            lineage.get("request_nonce_hash") == registration_nonce_hash
        )
        reference_time_ms = _strict_int(verification.get("reference_time_ms"))
        source_count = _strict_int(verification.get("source_count"))
        provider_spread_ms = _strict_int(verification.get("provider_spread_ms"))
        local_skew_ms = _strict_int(verification.get("local_skew_ms"))
        facts["reference_time_inside_declared_challenge_window"] = (
            facts["handoff_evidence_exact"]
            and reference_time_ms is not None
            and declared_issued_at_ms is not None
            and declared_expires_at_ms is not None
            and declared_issued_at_ms
            <= reference_time_ms
            <= declared_expires_at_ms
        )

    local_binding_verified = all(
        facts[name]
        for name in (
            "handoff_evidence_exact",
            "dual_signature_handoff_verified",
            "challenge_source_key_signature_verified",
            "provider_key_signature_verified",
            "clock_attestation_exact",
            "clock_registration_integrity_verified",
            "clock_registered_public_key_hashes_verified",
            "clock_detached_signatures_verified",
            "clock_multi_authority_quorum_verified",
            "clock_context_bound_to_signed_challenge",
            "clock_nonce_bound_to_registration_nonce",
            "reference_time_inside_declared_challenge_window",
        )
    )
    blockers = [
        "EXTERNAL_TIME_AUTHORITY_TRUST_UNPROVEN",
        "CLOCK_REGISTRATION_GOVERNANCE_UNPROVEN",
        "VERIFICATION_TIME_SOURCE_UNTRUSTED",
        "REQUEST_NONCE_UNIQUENESS_UNPROVEN",
        "CLOCK_REPLAY_REGISTRY_UNPROVEN",
        "CURRENT_TIME_NOT_ESTABLISHED",
        "CHALLENGE_FRESHNESS_UNVERIFIED",
        "REGISTRATION_REPLAY_UNCONSUMED",
        "PROVIDER_REGISTRATION_UNVERIFIED",
        "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not local_binding_verified:
        blockers.insert(0, "REGISTRATION_CHALLENGE_CLOCK_BINDING_UNKNOWN_OR_INVALID")
    evidence = {
        "schema_version": CLOCK_BINDING_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_binding_verified else "BLOCK",
        "decision": (
            "SIGNED_CLOCK_OBSERVATIONS_BOUND_TO_EXACT_DUAL_SIGNATURE_HANDOFF_"
            "CURRENT_TIME_FRESHNESS_AND_CONSUMPTION_UNPROVEN"
            if local_binding_verified
            else "REGISTRATION_CHALLENGE_CLOCK_BINDING_UNKNOWN_OR_INVALID"
        ),
        "registration_status": "BLOCKED",
        "source": {
            "challenge_source_implementation_sha256": (
                CHALLENGE_SOURCE_IMPLEMENTATION_SHA256
            ),
            "handoff_implementation_sha256": HANDOFF_IMPLEMENTATION_SHA256,
            "trusted_clock_implementation_sha256": (
                TRUSTED_CLOCK_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "signed_challenge_hash": signed_challenge_hash,
            "handoff_evidence_hash": _strict_hash(
                expected_handoff_evidence_hash
            ),
            "clock_registration_hash": registration_hash,
            "clock_attestation_hash": clock_hash,
        },
        "observation": {
            "declared_issued_at_ms": declared_issued_at_ms,
            "declared_expires_at_ms": declared_expires_at_ms,
            "clock_reference_time_ms": reference_time_ms,
            "clock_source_count": source_count,
            "clock_provider_spread_ms": provider_spread_ms,
            "clock_local_skew_ms": local_skew_ms,
        },
        "facts": facts,
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(evidence, "clock_binding_evidence_hash")


def verify_genesis_replay_reservation_provider_registration_clock_binding_v1(
    evidence_document: Any,
    *args: Any,
    expected_clock_binding_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    try:
        expected = (
            evaluate_genesis_replay_reservation_provider_registration_clock_binding_v1(
                *args, **kwargs
            )
        )
        return (
            evidence_document == expected
            and _strict_hash(expected_clock_binding_evidence_hash)
            == expected["clock_binding_evidence_hash"]
        )
    except (TypeError, ValueError):
        return False


__all__ = [
    "CLOCK_BINDING_EVIDENCE_SCHEMA_VERSION",
    "GenesisReplayReservationProviderRegistrationClockBindingError",
    "evaluate_genesis_replay_reservation_provider_registration_clock_binding_v1",
    "verify_genesis_replay_reservation_provider_registration_clock_binding_v1",
]
