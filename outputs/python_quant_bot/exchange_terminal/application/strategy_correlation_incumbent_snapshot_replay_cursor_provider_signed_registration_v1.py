"""Synthetic signed-registration candidate for an ADR0385 provider profile."""

from __future__ import annotations

import base64
from hashlib import sha256
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1
    as preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REGISTRATION_CLAIM_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-registration-claim-v1"
)
SIGNED_REGISTRATION_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-signed-registration-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "incumbent-snapshot-replay-cursor-provider-signed-registration-"
    "verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-replay-cursor-provider-signed-registration-v1-synthetic-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.replay-cursor.provider-registration.v1"
)
PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "42e1e2a88839b616ac2ebc9f7851ae8266172ade6b1a5a26320635ec90111212"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_KEYS = (
    "current_activation_allowed",
    "live_order_allowed",
    "paper_authorized",
    "provider_registration_allowed",
    "runtime_gate_activation_allowed",
    "signed_provider_receipt_issuance_allowed",
    "writer_allowed",
)
_OPERATIONAL_BLOCKERS = (
    "REGISTRATION_CHALLENGE_SOURCE_AUTHORITY_UNVERIFIED",
    "REGISTRATION_CHALLENGE_FRESHNESS_UNVERIFIED",
    "REGISTRATION_REPLAY_CONSUMPTION_MISSING",
    "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
    "PROVIDER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "DURABLE_ATOMIC_COMPARE_AND_ADVANCE_UNVERIFIED",
    "EXTERNAL_LINEARIZABILITY_UNVERIFIED",
    "SIGNED_PROVIDER_OPERATION_RECEIPT_V1_MISSING",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _validate_hash(name: str, value: Any) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256 hex digest")
    return value


def _canonical_base64(name: str, value: Any) -> tuple[str, bytes]:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be non-empty canonical base64")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be canonical base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{name} must be canonical base64")
    return value, decoded


def _load_ed25519_spki(value: Any) -> tuple[str, bytes, Ed25519PublicKey]:
    encoded, der = _canonical_base64("public_key_spki_base64", value)
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError) as exc:
        raise ValueError("public key SPKI is invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("public key SPKI must contain an Ed25519 key")
    roundtrip = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if roundtrip != der:
        raise ValueError("public key SPKI encoding is not canonical")
    return encoded, der, key


def _claim_body(
    preregistration_document: Mapping[str, Any],
    *,
    challenge_hash: str,
    registration_nonce_hash: str,
) -> dict[str, Any]:
    identity = preregistration_document["identity"]
    return {
        "authority": _locked_authority(),
        "blockers": list(_OPERATIONAL_BLOCKERS),
        "decision": (
            "PROVIDER_REGISTRATION_CLAIM_PREREGISTERED_SIGNATURE_AND_"
            "EXTERNAL_AUTHORITY_UNVERIFIED"
        ),
        "facts": {
            "challenge_freshness_verified": False,
            "challenge_source_authority_verified": False,
            "external_provider_conformance_verified": False,
            "local_claim_complete": True,
            "network_accessed": False,
            "provider_identity_verified": False,
            "provider_implementation_verified": False,
            "provider_key_control_continuity_verified": False,
            "provider_registered": False,
            "registration_replay_consumed": False,
            "runtime_assets_accessed": False,
            "signature_verified": False,
        },
        "identity": {
            "operator_identity_claim": identity["operator_identity_claim"],
            "provider_implementation_claim_sha256": identity[
                "provider_implementation_claim_sha256"
            ],
            "public_key_spki_sha256": identity["public_key_spki_sha256"],
            "registry_id": identity["registry_id"],
            "trust_domain": identity["trust_domain"],
        },
        "schema_version": REGISTRATION_CLAIM_SCHEMA_VERSION,
        "source": {
            "challenge_hash": challenge_hash,
            "preregistration_hash": preregistration_document[
                "preregistration_hash"
            ],
            "preregistration_implementation_sha256": (
                PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "provider_protocol_version": (
                preregistration.PROVIDER_PROTOCOL_VERSION
            ),
            "registration_nonce_hash": registration_nonce_hash,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
    }


def build_replay_cursor_provider_registration_claim_v1(
    preregistration_document: Any,
    *,
    challenge_hash: Any,
    registration_nonce_hash: Any,
    **preregistration_kwargs: Any,
) -> dict[str, Any]:
    challenge_hash = _validate_hash("challenge_hash", challenge_hash)
    registration_nonce_hash = _validate_hash(
        "registration_nonce_hash", registration_nonce_hash
    )
    verification = preregistration.verify_replay_cursor_provider_preregistration_v1(
        preregistration_document,
        **preregistration_kwargs,
    )
    if verification["status"] != "PASS":
        raise ValueError("provider preregistration is not exact")
    if not isinstance(preregistration_document, Mapping):
        raise ValueError("provider preregistration must be a mapping")
    return seal_strict_canonical_document(
        _claim_body(
            preregistration_document,
            challenge_hash=challenge_hash,
            registration_nonce_hash=registration_nonce_hash,
        ),
        "claim_hash",
    )


def verify_replay_cursor_provider_registration_claim_v1(
    document: Any,
    preregistration_document: Any,
    *,
    expected_claim_hash: Any,
    challenge_hash: Any,
    registration_nonce_hash: Any,
    **preregistration_kwargs: Any,
) -> bool:
    try:
        expected_claim_hash = _validate_hash(
            "expected_claim_hash", expected_claim_hash
        )
        expected = build_replay_cursor_provider_registration_claim_v1(
            preregistration_document,
            challenge_hash=challenge_hash,
            registration_nonce_hash=registration_nonce_hash,
            **preregistration_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        expected["claim_hash"] == expected_claim_hash
        and strict_json_contract_equal(document, expected)
    )


def build_signed_replay_cursor_provider_registration_v1(
    claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_claim_hash: Any,
    challenge_hash: Any,
    registration_nonce_hash: Any,
    **preregistration_kwargs: Any,
) -> dict[str, Any]:
    if not verify_replay_cursor_provider_registration_claim_v1(
        claim_document,
        preregistration_document,
        expected_claim_hash=expected_claim_hash,
        challenge_hash=challenge_hash,
        registration_nonce_hash=registration_nonce_hash,
        **preregistration_kwargs,
    ):
        raise ValueError("provider registration claim is not exact")
    public_key_spki_base64, public_key_der, _ = _load_ed25519_spki(
        public_key_spki_base64
    )
    signature_base64, signature = _canonical_base64(
        "signature_base64", signature_base64
    )
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must be 64 bytes")
    return seal_strict_canonical_document(
        {
            "authority": _locked_authority(),
            "claim_hash": expected_claim_hash,
            "preregistration_hash": preregistration_document[
                "preregistration_hash"
            ],
            "public_key_spki_base64": public_key_spki_base64,
            "public_key_spki_sha256": sha256(public_key_der).hexdigest(),
            "schema_version": SIGNED_REGISTRATION_SCHEMA_VERSION,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_base64": signature_base64,
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "SIGNED_CANDIDATE",
        },
        "signed_registration_hash",
    )


def _verify_signature(
    public_key: Ed25519PublicKey,
    signature: bytes,
    claim_hash: str,
) -> bool:
    try:
        public_key.verify(signature, bytes.fromhex(claim_hash))
    except (InvalidSignature, ValueError):
        return False
    return True


def evaluate_signed_replay_cursor_provider_registration_v1(
    signed_registration_document: Any,
    claim_document: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_claim_hash: Any,
    expected_signed_registration_hash: Any,
    challenge_hash: Any,
    registration_nonce_hash: Any,
    **preregistration_kwargs: Any,
) -> dict[str, Any]:
    claim_exact = verify_replay_cursor_provider_registration_claim_v1(
        claim_document,
        preregistration_document,
        expected_claim_hash=expected_claim_hash,
        challenge_hash=challenge_hash,
        registration_nonce_hash=registration_nonce_hash,
        **preregistration_kwargs,
    )
    signed_exact = False
    key_hash_matches = False
    cryptographic_signature_verified = False
    public_key_hash: str | None = None
    signed_registration_hash: str | None = None
    try:
        expected_signed_registration_hash = _validate_hash(
            "expected_signed_registration_hash",
            expected_signed_registration_hash,
        )
        expected_signed = build_signed_replay_cursor_provider_registration_v1(
            claim_document,
            preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_claim_hash=expected_claim_hash,
            challenge_hash=challenge_hash,
            registration_nonce_hash=registration_nonce_hash,
            **preregistration_kwargs,
        )
        signed_exact = (
            expected_signed["signed_registration_hash"]
            == expected_signed_registration_hash
            and strict_json_contract_equal(
                signed_registration_document,
                expected_signed,
            )
        )
        _, public_key_der, public_key = _load_ed25519_spki(
            public_key_spki_base64
        )
        _, signature = _canonical_base64("signature_base64", signature_base64)
        public_key_hash = sha256(public_key_der).hexdigest()
        key_hash_matches = (
            isinstance(preregistration_document, Mapping)
            and public_key_hash
            == preregistration_document["identity"]["public_key_spki_sha256"]
        )
        cryptographic_signature_verified = _verify_signature(
            public_key,
            signature,
            expected_claim_hash,
        )
        signed_registration_hash = expected_signed["signed_registration_hash"]
    except (KeyError, TypeError, ValueError):
        pass

    preregistered_key_signature_verified = (
        claim_exact
        and signed_exact
        and key_hash_matches
        and cryptographic_signature_verified
    )
    dynamic_blockers: list[str] = []
    if not claim_exact:
        dynamic_blockers.append("REGISTRATION_CLAIM_NOT_EXACT")
    if not signed_exact:
        dynamic_blockers.append("SIGNED_REGISTRATION_DOCUMENT_NOT_EXACT")
    if not key_hash_matches:
        dynamic_blockers.append("PREREGISTERED_PUBLIC_KEY_HASH_MISMATCH")
    if not cryptographic_signature_verified:
        dynamic_blockers.append("ED25519_SIGNATURE_INVALID")

    evidence = {
        "authority": _locked_authority(),
        "blockers": dynamic_blockers + list(_OPERATIONAL_BLOCKERS),
        "decision": (
            "PREREGISTERED_KEY_SIGNATURE_OBSERVED_PROVIDER_REGISTRATION_"
            "AND_EXTERNAL_AUTHORITY_STILL_BLOCKED"
            if preregistered_key_signature_verified
            else "SIGNED_PROVIDER_REGISTRATION_UNKNOWN_OR_INVALID"
        ),
        "facts": {
            "challenge_freshness_verified": False,
            "challenge_source_authority_verified": False,
            "claim_document_exact": claim_exact,
            "cryptographic_signature_verified": (
                cryptographic_signature_verified
            ),
            "external_provider_conformance_verified": False,
            "key_hash_matches_preregistration": key_hash_matches,
            "network_accessed": False,
            "preregistered_key_signature_verified": (
                preregistered_key_signature_verified
            ),
            "provider_identity_verified": False,
            "provider_implementation_verified": False,
            "provider_key_control_continuity_verified": False,
            "provider_key_possession_observed": (
                preregistered_key_signature_verified
            ),
            "provider_registered": False,
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "registration_replay_consumed": False,
            "runtime_assets_accessed": False,
            "signed_registration_document_exact": signed_exact,
        },
        "registration_status": (
            "SIGNED_REGISTRATION_CANDIDATE_BLOCKED"
            if preregistered_key_signature_verified
            else "UNKNOWN"
        ),
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "source": {
            "claim_hash": expected_claim_hash if _HASH_PATTERN.fullmatch(str(expected_claim_hash)) else None,
            "preregistration_hash": (
                preregistration_document.get("preregistration_hash")
                if isinstance(preregistration_document, Mapping)
                else None
            ),
            "public_key_spki_sha256": public_key_hash,
            "signed_registration_hash": signed_registration_hash,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if preregistered_key_signature_verified else "BLOCK",
    }
    return seal_strict_canonical_document(
        evidence,
        "verification_evidence_hash",
    )


def verify_signed_replay_cursor_provider_registration_evidence_v1(
    evidence_document: Any,
    signed_registration_document: Any,
    claim_document: Any,
    preregistration_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    try:
        expected_verification_evidence_hash = _validate_hash(
            "expected_verification_evidence_hash",
            expected_verification_evidence_hash,
        )
        expected = evaluate_signed_replay_cursor_provider_registration_v1(
            signed_registration_document,
            claim_document,
            preregistration_document,
            **evaluation_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        expected["verification_evidence_hash"]
        == expected_verification_evidence_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "PREREGISTRATION_IMPLEMENTATION_SHA256",
    "REGISTRATION_CLAIM_SCHEMA_VERSION",
    "SIGNED_REGISTRATION_SCHEMA_VERSION",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "build_replay_cursor_provider_registration_claim_v1",
    "build_signed_replay_cursor_provider_registration_v1",
    "evaluate_signed_replay_cursor_provider_registration_v1",
    "verify_replay_cursor_provider_registration_claim_v1",
    "verify_signed_replay_cursor_provider_registration_evidence_v1",
]
