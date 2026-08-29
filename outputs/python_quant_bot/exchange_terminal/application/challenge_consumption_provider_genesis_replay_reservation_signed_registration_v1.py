"""Synthetic Ed25519 key-control proof for the ADR0397 provider key."""

from __future__ import annotations

import base64
import binascii
import re
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.application import (
    challenge_consumption_provider_genesis_replay_reservation_preregistration_v1 as preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


REGISTRATION_CLAIM_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-provider-registration-claim-v1"
)
SIGNED_REGISTRATION_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-provider-signed-registration-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "challenge-consumption-provider-genesis-replay-reservation-provider-signed-registration-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-provider-signed-registration-v1-synthetic-lock-1"
)
PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "dfdedb55e1e0d89e25436d64a9597fbf09c359db63101efe457425698075d15e"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.genesis-replay-reservation-provider-registration.v1"
)
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"

_HASH = re.compile(r"^[0-9a-f]{64}$")


class GenesisReplayReservationProviderSignedRegistrationError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            f"{label} must be lowercase sha256"
        )
    return value


def _decode_base64(value: Any, label: str, *, expected_length: int | None = None) -> bytes:
    if type(value) is not str or not value:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            f"{label} must be canonical base64"
        )
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            f"{label} must be canonical base64"
        ) from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            f"{label} must be canonical base64"
        )
    if expected_length is not None and len(decoded) != expected_length:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            f"{label} length mismatch"
        )
    return decoded


def _load_ed25519_spki(value: Any) -> tuple[Ed25519PublicKey, bytes]:
    der = _decode_base64(value, "public_key_spki_base64")
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "public key must be canonical Ed25519 DER-SPKI"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "public key must be Ed25519"
        )
    canonical = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical != der:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "public key DER-SPKI is not canonical"
        )
    return key, der


def _authority() -> dict[str, bool]:
    return {
        "reserve_once_allowed": False,
        "signed_receipt_issuance_allowed": False,
        "provider_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _exact_preregistration(document: Any, kwargs: Any) -> dict[str, Any]:
    if type(kwargs) is not dict:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "preregistration_kwargs must be a dict"
        )
    try:
        expected = preregistration.build_genesis_replay_reservation_provider_preregistration_v1(
            **dict(kwargs)
        )
    except (TypeError, ValueError) as exc:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "preregistration kwargs are invalid"
        ) from exc
    if document != expected:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "provider preregistration is not exact"
        )
    return expected


def build_genesis_replay_reservation_provider_registration_claim_v1(
    preregistration_document: Any,
    *,
    challenge_hash: Any,
    registration_nonce_hash: Any,
    preregistration_kwargs: Any,
) -> dict[str, Any]:
    prereg = _exact_preregistration(
        preregistration_document, preregistration_kwargs
    )
    challenge = _require_hash(challenge_hash, "challenge_hash")
    nonce = _require_hash(registration_nonce_hash, "registration_nonce_hash")
    if challenge == nonce:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "challenge and registration nonce hashes must be distinct"
        )
    document = {
        "schema_version": REGISTRATION_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "GENESIS_REPLAY_RESERVATION_PROVIDER_REGISTRATION_CLAIM_UNSIGNED_CHALLENGE_"
            "SOURCE_FRESHNESS_AND_CONSUMPTION_UNVERIFIED"
        ),
        "source": {
            "preregistration_hash": prereg["preregistration_hash"],
            "preregistration_schema_version": (
                preregistration.PREREGISTRATION_SCHEMA_VERSION
            ),
            "preregistration_implementation_sha256": (
                PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "provider_protocol_version": preregistration.PROVIDER_PROTOCOL_VERSION,
        },
        "binding": {
            "challenge_hash": challenge,
            "registration_nonce_hash": nonce,
            "public_key_spki_sha256": prereg["identity"][
                "public_key_spki_sha256"
            ],
            "provider_implementation_claim_sha256": prereg["identity"][
                "provider_implementation_claim_sha256"
            ],
        },
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "preregistration_exact": True,
            "claim_bindings_exact": True,
            "provider_key_signature_verified": False,
            "provider_key_possession_observed": False,
            "provider_registered": False,
            "challenge_source_authority_verified": False,
            "challenge_freshness_verified": False,
            "registration_replay_consumed": False,
            "external_provider_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "PROVIDER_KEY_SIGNATURE_UNVERIFIED",
            "PROVIDER_IDENTITY_UNVERIFIED",
            "CHALLENGE_SOURCE_AUTHORITY_UNVERIFIED",
            "CHALLENGE_FRESHNESS_UNVERIFIED",
            "REGISTRATION_REPLAY_UNCONSUMED",
            "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "claim_hash")


def verify_genesis_replay_reservation_provider_registration_claim_v1(
    document: Any,
    preregistration_document: Any,
    *,
    expected_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_genesis_replay_reservation_provider_registration_claim_v1(
            preregistration_document, **build_kwargs
        )
        return (
            document == expected
            and _require_hash(expected_claim_hash, "expected_claim_hash")
            == expected["claim_hash"]
        )
    except (TypeError, GenesisReplayReservationProviderSignedRegistrationError):
        return False


def build_signed_genesis_replay_reservation_provider_registration_v1(
    claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_claim_hash: Any,
    **claim_build_kwargs: Any,
) -> dict[str, Any]:
    expected = build_genesis_replay_reservation_provider_registration_claim_v1(
        preregistration_document, **claim_build_kwargs
    )
    claim_hash = _require_hash(expected_claim_hash, "expected_claim_hash")
    if claim_document != expected or claim_hash != expected["claim_hash"]:
        raise GenesisReplayReservationProviderSignedRegistrationError(
            "claim document is not exact"
        )
    _, der = _load_ed25519_spki(public_key_spki_base64)
    signature = _decode_base64(
        signature_base64, "signature_base64", expected_length=64
    )
    document = {
        "schema_version": SIGNED_REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "claim_hash": claim_hash,
        "preregistration_hash": preregistration_document["preregistration_hash"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(der).hexdigest(),
        "signature_base64": signature_base64,
        "signature_sha256": sha256(signature).hexdigest(),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "signed_registration_hash")


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def evaluate_signed_genesis_replay_reservation_provider_registration_v1(
    signed_registration_document: Any,
    claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_claim_hash: Any,
    expected_signed_registration_hash: Any,
    **claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_exact = False
    signed_exact = False
    key_hash_matches = False
    cryptographic_signature_verified = False
    key_hash = None
    preregistration_hash = None
    try:
        expected_claim = build_genesis_replay_reservation_provider_registration_claim_v1(
            preregistration_document, **claim_build_kwargs
        )
        claim_hash = _require_hash(expected_claim_hash, "expected_claim_hash")
        claim_exact = claim_document == expected_claim and claim_hash == expected_claim[
            "claim_hash"
        ]
        key, der = _load_ed25519_spki(public_key_spki_base64)
        signature = _decode_base64(
            signature_base64, "signature_base64", expected_length=64
        )
        key_hash = sha256(der).hexdigest()
        expected_prereg = _exact_preregistration(
            preregistration_document,
            claim_build_kwargs.get("preregistration_kwargs"),
        )
        preregistration_hash = expected_prereg["preregistration_hash"]
        key_hash_matches = (
            key_hash == expected_prereg["identity"]["public_key_spki_sha256"]
        )
        try:
            key.verify(signature, bytes.fromhex(claim_hash))
            cryptographic_signature_verified = True
        except InvalidSignature:
            cryptographic_signature_verified = False
        expected_signed = build_signed_genesis_replay_reservation_provider_registration_v1(
            claim_document,
            preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_claim_hash=claim_hash,
            **claim_build_kwargs,
        )
        signed_exact = (
            signed_registration_document == expected_signed
            and _require_hash(
                expected_signed_registration_hash,
                "expected_signed_registration_hash",
            )
            == expected_signed["signed_registration_hash"]
        )
    except (KeyError, TypeError, ValueError, GenesisReplayReservationProviderSignedRegistrationError):
        pass

    trusted_signature = (
        claim_exact
        and signed_exact
        and key_hash_matches
        and cryptographic_signature_verified
    )
    facts = {
        "claim_document_exact": claim_exact,
        "signed_registration_document_exact": signed_exact,
        "key_hash_matches_preregistration": key_hash_matches,
        "cryptographic_signature_verified": cryptographic_signature_verified,
        "preregistered_key_signature_verified": trusted_signature,
        "provider_key_possession_observed": trusted_signature,
        "provider_registered": False,
        "provider_identity_verified": False,
        "provider_implementation_verified": False,
        "provider_key_control_continuity_verified": False,
        "challenge_source_authority_verified": False,
        "challenge_freshness_verified": False,
        "registration_replay_consumed": False,
        "external_provider_conformance_verified": False,
        "external_atomicity_verified": False,
        "durability_verified": False,
        "linearizability_verified": False,
        "raw_public_key_redacted": True,
        "raw_signature_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }
    blockers = [
        "PROVIDER_IDENTITY_UNVERIFIED",
        "PROVIDER_IMPLEMENTATION_UNVERIFIED",
        "PROVIDER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
        "CHALLENGE_SOURCE_AUTHORITY_UNVERIFIED",
        "CHALLENGE_FRESHNESS_UNVERIFIED",
        "REGISTRATION_REPLAY_UNCONSUMED",
        "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
        "EXTERNAL_ATOMICITY_DURABILITY_LINEARIZABILITY_UNVERIFIED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not trusted_signature:
        blockers.insert(0, "SIGNED_PROVIDER_REGISTRATION_UNKNOWN_OR_INVALID")
    evidence = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if trusted_signature else "BLOCK",
        "decision": (
            "PREREGISTERED_PROVIDER_KEY_SIGNATURE_OBSERVED_REGISTRATION_AND_"
            "EXTERNAL_CAPABILITIES_UNVERIFIED"
            if trusted_signature
            else "SIGNED_PROVIDER_REGISTRATION_UNKNOWN_OR_INVALID"
        ),
        "registration_status": "BLOCKED",
        "source": {
            "preregistration_hash": _safe_hash(preregistration_hash),
            "claim_hash": _safe_hash(expected_claim_hash),
            "signed_registration_hash": _safe_hash(
                expected_signed_registration_hash
            ),
            "provider_public_key_spki_sha256": _safe_hash(key_hash),
        },
        "facts": facts,
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(evidence, "verification_evidence_hash")


def verify_signed_genesis_replay_reservation_provider_registration_evidence_v1(
    evidence_document: Any,
    signed_registration_document: Any,
    claim_document: Any,
    preregistration_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    try:
        expected = evaluate_signed_genesis_replay_reservation_provider_registration_v1(
            signed_registration_document,
            claim_document,
            preregistration_document,
            **evaluation_kwargs,
        )
        return (
            evidence_document == expected
            and _require_hash(
                expected_verification_evidence_hash,
                "expected_verification_evidence_hash",
            )
            == expected["verification_evidence_hash"]
        )
    except (TypeError, GenesisReplayReservationProviderSignedRegistrationError):
        return False


__all__ = [
    "PREREGISTRATION_IMPLEMENTATION_SHA256",
    "REGISTRATION_CLAIM_SCHEMA_VERSION",
    "SIGNED_REGISTRATION_SCHEMA_VERSION",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "GenesisReplayReservationProviderSignedRegistrationError",
    "build_genesis_replay_reservation_provider_registration_claim_v1",
    "build_signed_genesis_replay_reservation_provider_registration_v1",
    "evaluate_signed_genesis_replay_reservation_provider_registration_v1",
    "verify_genesis_replay_reservation_provider_registration_claim_v1",
    "verify_signed_genesis_replay_reservation_provider_registration_evidence_v1",
]
