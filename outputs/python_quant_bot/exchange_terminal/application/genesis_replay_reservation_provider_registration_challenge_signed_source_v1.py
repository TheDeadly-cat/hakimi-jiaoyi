from __future__ import annotations

import base64
import binascii
import copy
import re
from hashlib import sha256
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.application.challenge_consumption_provider_genesis_replay_reservation_preregistration_v1 import (
    PREREGISTRATION_SCHEMA_VERSION,
    build_genesis_replay_reservation_provider_preregistration_v1,
)
from exchange_terminal.application.challenge_consumption_provider_genesis_replay_reservation_signed_registration_v1 import (
    REGISTRATION_CLAIM_SCHEMA_VERSION,
    SIGNED_REGISTRATION_SCHEMA_VERSION,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


CHALLENGE_AUTHORITY_PREREGISTRATION_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-registration-challenge-authority-preregistration-v1"
)
REGISTRATION_CHALLENGE_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-registration-challenge-v1"
)
SIGNED_REGISTRATION_CHALLENGE_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-signed-registration-challenge-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "genesis-replay-reservation-provider-registration-challenge-signed-source-verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-genesis-replay-reservation-provider-registration-challenge-signed-source-v1-synthetic-lock-1"
)
PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "dfdedb55e1e0d89e25436d64a9597fbf09c359db63101efe457425698075d15e"
)
PROVIDER_SIGNED_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "d60e69e27cd0c746f82e368420c617e2683cb31fd4a36a701ef366705563471c"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.genesis-replay-reservation-provider.registration-challenge-source.v1"
)
SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
CHALLENGE_PURPOSE = "GENESIS_REPLAY_RESERVATION_PROVIDER_REGISTRATION_KEY_POSSESSION_V1"
MAX_CLAIMED_LIFETIME_MS = 300_000

_HASH = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")
_MAX_UNIX_MS = 253_402_300_799_999


class GenesisReplayReservationProviderRegistrationChallengeSourceError(ValueError):
    pass


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be lowercase sha256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be a strict identifier"
        )
    return value


def _require_time(value: Any, label: str) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_UNIX_MS:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be a bounded integer unix millisecond claim"
        )
    return value


def _decode_base64(value: Any, label: str, *, expected_length: int | None = None) -> bytes:
    if type(value) is not str or not value:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be canonical base64"
        )
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be canonical base64"
        ) from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} must be canonical base64"
        )
    if expected_length is not None and len(decoded) != expected_length:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            f"{label} length mismatch"
        )
    return decoded


def _load_ed25519_spki(value: Any) -> tuple[Ed25519PublicKey, bytes]:
    der = _decode_base64(value, "public_key_spki_base64")
    try:
        key = serialization.load_der_public_key(der)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "public key must be canonical Ed25519 DER-SPKI"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "public key must be Ed25519"
        )
    canonical = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if canonical != der:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "public key DER-SPKI is not canonical"
        )
    return key, der


def _authority() -> dict[str, bool]:
    return {
        "challenge_authority_identity_verified": False,
        "challenge_freshness_verified": False,
        "challenge_consumption_verified": False,
        "provider_registration_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _authority_preregistration_kwargs(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "authority_preregistration_kwargs must be a dict"
        )
    expected = {
        "challenge_authority_id",
        "challenge_authority_key_id",
        "challenge_authority_public_key_spki_sha256",
        "challenge_authority_trust_domain",
        "challenge_authority_implementation_claim_sha256",
    }
    if set(value) != expected:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "authority preregistration kwargs are not exact"
        )
    return copy.deepcopy(value)


def _provider_preregistration_exact(
    document: Any,
    kwargs: Any,
) -> dict[str, Any]:
    if type(kwargs) is not dict:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "provider_preregistration_kwargs must be a dict"
        )
    try:
        expected = build_genesis_replay_reservation_provider_preregistration_v1(
            **copy.deepcopy(kwargs)
        )
    except (TypeError, ValueError) as exc:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "provider preregistration kwargs are invalid"
        ) from exc
    if document != expected:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "provider preregistration is not exact"
        )
    return expected


def build_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1(
    *,
    challenge_authority_id: Any,
    challenge_authority_key_id: Any,
    challenge_authority_public_key_spki_sha256: Any,
    challenge_authority_trust_domain: Any,
    challenge_authority_implementation_claim_sha256: Any,
) -> dict[str, Any]:
    identity = {
        "challenge_authority_id": _require_identifier(
            challenge_authority_id, "challenge_authority_id"
        ),
        "challenge_authority_key_id": _require_identifier(
            challenge_authority_key_id, "challenge_authority_key_id"
        ),
        "challenge_authority_public_key_spki_sha256": _require_hash(
            challenge_authority_public_key_spki_sha256,
            "challenge_authority_public_key_spki_sha256",
        ),
        "challenge_authority_trust_domain": _require_identifier(
            challenge_authority_trust_domain, "challenge_authority_trust_domain"
        ),
        "challenge_authority_implementation_claim_sha256": _require_hash(
            challenge_authority_implementation_claim_sha256,
            "challenge_authority_implementation_claim_sha256",
        ),
    }
    document = {
        "schema_version": CHALLENGE_AUTHORITY_PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "CHALLENGE_AUTHORITY_KEY_PREREGISTERED_IDENTITY_KEY_CONTROL_"
            "CONFORMANCE_AND_OPERATION_UNVERIFIED"
        ),
        "identity": identity,
        "source": {
            "provider_preregistration_schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "provider_preregistration_implementation_sha256": (
                PROVIDER_PREREGISTRATION_IMPLEMENTATION_SHA256
            ),
            "provider_registration_claim_schema_version": REGISTRATION_CLAIM_SCHEMA_VERSION,
            "provider_signed_registration_schema_version": SIGNED_REGISTRATION_SCHEMA_VERSION,
            "provider_signed_registration_implementation_sha256": (
                PROVIDER_SIGNED_REGISTRATION_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "facts": {
            "authority_identity_fields_preregistered": True,
            "authority_public_key_hash_preregistered": True,
            "authority_implementation_claim_preregistered": True,
            "authority_identity_verified": False,
            "authority_key_possession_verified": False,
            "authority_implementation_verified": False,
            "external_conformance_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "CHALLENGE_AUTHORITY_IDENTITY_UNVERIFIED",
            "CHALLENGE_AUTHORITY_KEY_POSSESSION_UNVERIFIED",
            "CHALLENGE_AUTHORITY_IMPLEMENTATION_UNVERIFIED",
            "EXTERNAL_CHALLENGE_AUTHORITY_CONFORMANCE_UNVERIFIED",
            "CHALLENGE_FRESHNESS_UNVERIFIED",
            "CHALLENGE_CONSUMPTION_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "authority_preregistration_hash")


def verify_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1(
    document: Any,
    **kwargs: Any,
) -> bool:
    try:
        return document == build_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1(
            **kwargs
        )
    except (TypeError, GenesisReplayReservationProviderRegistrationChallengeSourceError):
        return False


def _authority_preregistration_exact(
    document: Any,
    kwargs: Any,
) -> dict[str, Any]:
    clean = _authority_preregistration_kwargs(kwargs)
    expected = build_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1(
        **clean
    )
    if document != expected:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "challenge authority preregistration is not exact"
        )
    return expected


def build_genesis_replay_reservation_provider_registration_challenge_v1(
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    provider_preregistration_kwargs: Any,
    authority_preregistration_kwargs: Any,
    challenge_id_hash: Any,
    registration_nonce_hash: Any,
    issued_at_unix_ms: Any,
    expires_at_unix_ms: Any,
) -> dict[str, Any]:
    provider = _provider_preregistration_exact(
        provider_preregistration_document, provider_preregistration_kwargs
    )
    authority_preregistration = _authority_preregistration_exact(
        challenge_authority_preregistration_document,
        authority_preregistration_kwargs,
    )
    challenge_id = _require_hash(challenge_id_hash, "challenge_id_hash")
    nonce_hash = _require_hash(registration_nonce_hash, "registration_nonce_hash")
    if challenge_id == nonce_hash:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "challenge id and registration nonce hashes must be distinct"
        )
    issued = _require_time(issued_at_unix_ms, "issued_at_unix_ms")
    expires = _require_time(expires_at_unix_ms, "expires_at_unix_ms")
    if not issued < expires or expires - issued > MAX_CLAIMED_LIFETIME_MS:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "claimed challenge lifetime is invalid"
        )
    document = {
        "schema_version": REGISTRATION_CHALLENGE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "REGISTRATION_CHALLENGE_DECLARED_SOURCE_SIGNATURE_FRESHNESS_"
            "AND_CONSUMPTION_UNVERIFIED"
        ),
        "source": {
            "provider_preregistration_hash": provider["preregistration_hash"],
            "challenge_authority_preregistration_hash": authority_preregistration[
                "authority_preregistration_hash"
            ],
            "provider_registration_claim_schema_version": REGISTRATION_CLAIM_SCHEMA_VERSION,
            "provider_signed_registration_schema_version": SIGNED_REGISTRATION_SCHEMA_VERSION,
        },
        "binding": {
            "challenge_id_hash": challenge_id,
            "registration_nonce_hash": nonce_hash,
            "issued_at_unix_ms": issued,
            "expires_at_unix_ms": expires,
            "max_claimed_lifetime_ms": MAX_CLAIMED_LIFETIME_MS,
            "challenge_purpose": CHALLENGE_PURPOSE,
        },
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "provider_preregistration_exact": True,
            "challenge_authority_preregistration_exact": True,
            "claimed_time_window_well_formed": True,
            "challenge_authority_signature_verified": False,
            "challenge_time_source_authoritative": False,
            "challenge_freshness_verified": False,
            "challenge_consumption_verified": False,
            "provider_registered": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "authority": _authority(),
        "blockers": [
            "CHALLENGE_AUTHORITY_SIGNATURE_UNVERIFIED",
            "CHALLENGE_AUTHORITY_IDENTITY_UNVERIFIED",
            "CLAIMED_TIME_SOURCE_UNVERIFIED",
            "CHALLENGE_FRESHNESS_UNVERIFIED",
            "CHALLENGE_CONSUMPTION_UNVERIFIED",
            "PROVIDER_REGISTRATION_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "challenge_hash")


def verify_genesis_replay_reservation_provider_registration_challenge_v1(
    document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    expected_challenge_hash: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_genesis_replay_reservation_provider_registration_challenge_v1(
            provider_preregistration_document,
            challenge_authority_preregistration_document,
            **build_kwargs,
        )
        return (
            _require_hash(expected_challenge_hash, "expected_challenge_hash")
            == expected["challenge_hash"]
            and document == expected
        )
    except (TypeError, GenesisReplayReservationProviderRegistrationChallengeSourceError):
        return False


def build_signed_genesis_replay_reservation_provider_registration_challenge_v1(
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_challenge_hash: Any,
    **challenge_build_kwargs: Any,
) -> dict[str, Any]:
    expected = build_genesis_replay_reservation_provider_registration_challenge_v1(
        provider_preregistration_document,
        challenge_authority_preregistration_document,
        **challenge_build_kwargs,
    )
    expected_hash = _require_hash(expected_challenge_hash, "expected_challenge_hash")
    if challenge_document != expected or expected_hash != expected["challenge_hash"]:
        raise GenesisReplayReservationProviderRegistrationChallengeSourceError(
            "challenge document is not the exact expected challenge"
        )
    _, der = _load_ed25519_spki(public_key_spki_base64)
    signature = _decode_base64(
        signature_base64, "signature_base64", expected_length=64
    )
    document = {
        "schema_version": SIGNED_REGISTRATION_CHALLENGE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "challenge_hash": expected_hash,
        "challenge_authority_preregistration_hash": (
            challenge_authority_preregistration_document[
                "authority_preregistration_hash"
            ]
        ),
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(der).hexdigest(),
        "signature_base64": signature_base64,
        "signature_sha256": sha256(signature).hexdigest(),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "signed_challenge_hash")


def _safe_hash(value: Any) -> str | None:
    return value if type(value) is str and _HASH.fullmatch(value) else None


def evaluate_signed_genesis_replay_reservation_provider_registration_challenge_v1(
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_challenge_hash: Any,
    expected_signed_challenge_hash: Any,
    **challenge_build_kwargs: Any,
) -> dict[str, Any]:
    challenge_exact = False
    signed_exact = False
    key_hash_matches = False
    cryptographic_signature_verified = False
    key_hash: str | None = None
    expected_authority_hash: str | None = None
    expected_provider_hash: str | None = None

    try:
        expected_challenge = build_genesis_replay_reservation_provider_registration_challenge_v1(
            provider_preregistration_document,
            challenge_authority_preregistration_document,
            **challenge_build_kwargs,
        )
        expected_hash = _require_hash(
            expected_challenge_hash, "expected_challenge_hash"
        )
        challenge_exact = (
            challenge_document == expected_challenge
            and expected_hash == expected_challenge["challenge_hash"]
        )
        expected_authority_hash = challenge_authority_preregistration_document.get(
            "authority_preregistration_hash"
        )
        expected_provider_hash = provider_preregistration_document.get(
            "preregistration_hash"
        )
        key, der = _load_ed25519_spki(public_key_spki_base64)
        signature = _decode_base64(
            signature_base64, "signature_base64", expected_length=64
        )
        key_hash = sha256(der).hexdigest()
        authority_kwargs = _authority_preregistration_kwargs(
            challenge_build_kwargs.get("authority_preregistration_kwargs")
        )
        key_hash_matches = (
            key_hash
            == authority_kwargs["challenge_authority_public_key_spki_sha256"]
        )
        try:
            key.verify(signature, bytes.fromhex(expected_hash))
            cryptographic_signature_verified = True
        except InvalidSignature:
            cryptographic_signature_verified = False
        expected_signed = build_signed_genesis_replay_reservation_provider_registration_challenge_v1(
            challenge_document,
            provider_preregistration_document,
            challenge_authority_preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_challenge_hash=expected_hash,
            **challenge_build_kwargs,
        )
        signed_exact = (
            signed_challenge_document == expected_signed
            and _require_hash(
                expected_signed_challenge_hash,
                "expected_signed_challenge_hash",
            )
            == expected_signed["signed_challenge_hash"]
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        GenesisReplayReservationProviderRegistrationChallengeSourceError,
    ):
        pass

    trusted_signature = (
        challenge_exact
        and signed_exact
        and key_hash_matches
        and cryptographic_signature_verified
    )
    facts = {
        "challenge_document_exact": challenge_exact,
        "signed_challenge_document_exact": signed_exact,
        "authority_key_hash_matches_preregistration": key_hash_matches,
        "cryptographic_signature_verified": cryptographic_signature_verified,
        "preregistered_challenge_key_signature_verified": trusted_signature,
        "challenge_source_key_possession_observed": trusted_signature,
        "claimed_time_window_bound": challenge_exact,
        "challenge_authority_identity_verified": False,
        "challenge_authority_implementation_verified": False,
        "challenge_time_source_authoritative": False,
        "challenge_freshness_verified": False,
        "challenge_consumption_verified": False,
        "provider_registered": False,
        "external_conformance_verified": False,
        "raw_public_key_redacted": True,
        "raw_signature_redacted": True,
        "network_accessed": False,
        "runtime_assets_accessed": False,
    }
    blockers = [
        "CHALLENGE_AUTHORITY_IDENTITY_UNVERIFIED",
        "CHALLENGE_AUTHORITY_IMPLEMENTATION_UNVERIFIED",
        "CLAIMED_TIME_SOURCE_UNVERIFIED",
        "CHALLENGE_FRESHNESS_UNVERIFIED",
        "CHALLENGE_CONSUMPTION_UNVERIFIED",
        "PROVIDER_REGISTRATION_UNVERIFIED",
        "EXTERNAL_CONFORMANCE_UNVERIFIED",
        "CURRENT_ACTIVATION_UNAUTHORIZED",
    ]
    if not trusted_signature:
        blockers.insert(0, "SIGNED_CHALLENGE_SOURCE_UNKNOWN_OR_INVALID")
    evidence = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if trusted_signature else "BLOCK",
        "decision": (
            "CHALLENGE_SOURCE_SIGNATURE_OBSERVED_FRESHNESS_AND_CONSUMPTION_UNVERIFIED"
            if trusted_signature
            else "SIGNED_CHALLENGE_SOURCE_UNKNOWN_OR_INVALID"
        ),
        "source": {
            "provider_preregistration_hash": _safe_hash(expected_provider_hash),
            "challenge_authority_preregistration_hash": _safe_hash(
                expected_authority_hash
            ),
            "challenge_hash": _safe_hash(expected_challenge_hash),
            "signed_challenge_hash": _safe_hash(expected_signed_challenge_hash),
            "authority_public_key_spki_sha256": _safe_hash(key_hash),
        },
        "facts": facts,
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(evidence, "verification_evidence_hash")


def verify_signed_genesis_replay_reservation_provider_registration_challenge_evidence_v1(
    evidence_document: Any,
    signed_challenge_document: Any,
    challenge_document: Any,
    provider_preregistration_document: Any,
    challenge_authority_preregistration_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    try:
        expected = evaluate_signed_genesis_replay_reservation_provider_registration_challenge_v1(
            signed_challenge_document,
            challenge_document,
            provider_preregistration_document,
            challenge_authority_preregistration_document,
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
    except (TypeError, GenesisReplayReservationProviderRegistrationChallengeSourceError):
        return False


__all__ = [
    "CHALLENGE_AUTHORITY_PREREGISTRATION_SCHEMA_VERSION",
    "REGISTRATION_CHALLENGE_SCHEMA_VERSION",
    "SIGNED_REGISTRATION_CHALLENGE_SCHEMA_VERSION",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "GenesisReplayReservationProviderRegistrationChallengeSourceError",
    "build_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1",
    "verify_genesis_replay_reservation_provider_registration_challenge_authority_preregistration_v1",
    "build_genesis_replay_reservation_provider_registration_challenge_v1",
    "verify_genesis_replay_reservation_provider_registration_challenge_v1",
    "build_signed_genesis_replay_reservation_provider_registration_challenge_v1",
    "evaluate_signed_genesis_replay_reservation_provider_registration_challenge_v1",
    "verify_signed_genesis_replay_reservation_provider_registration_challenge_evidence_v1",
]
