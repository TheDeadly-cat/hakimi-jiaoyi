"""Local dual-signature provider key-continuity candidate for ADR0416."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as provider_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


KEY_STATE_SCHEMA_VERSION = (
    "witness-ownership-provider-key-continuity-state-v1"
)
ROTATION_CLAIM_SCHEMA_VERSION = (
    "witness-ownership-provider-key-rotation-claim-v1"
)
SIGNED_ROTATION_SCHEMA_VERSION = (
    "witness-ownership-provider-dual-signed-key-rotation-v1"
)
ROTATION_EVIDENCE_SCHEMA_VERSION = (
    "witness-ownership-provider-key-rotation-verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-key-continuity-v1-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = (
    "STRICT_CANONICAL_DOMAIN_SEPARATED_SHA256_DIGEST_BYTES_V1"
)
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.provider-key-rotation.v1"
)
ZERO_HASH = "0" * 64
ROTATION_REASON_CODES = frozenset(
    {"SCHEDULED_ROTATION", "POLICY_ROTATION", "COMPROMISE_CONTAINMENT"}
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PERMANENT_BLOCKERS = (
    "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
    "PROVIDER_KEY_CONTROL_CONTINUITY_SOURCE_TRUTH_UNVERIFIED",
    "REVOCATION_SNAPSHOT_SOURCE_UNVERIFIED",
    "TRUSTED_ROTATION_CLOCK_UNVERIFIED",
    "KEY_STATE_PERSISTENCE_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UPDATE_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _require_epoch(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _decode_public_key(value: Any, field: str):
    if type(value) is not str or not value:
        raise ValueError(f"{field} must be non-empty canonical base64")
    spki_bytes = decode_canonical_base64_v1(value, field)
    return spki_bytes, load_canonical_ed25519_public_key_v1(spki_bytes)


def _decode_signature(value: Any, field: str) -> bytes:
    if type(value) is not str or not value:
        raise ValueError(f"{field} must be non-empty canonical base64")
    signature = decode_canonical_base64_v1(value, field)
    if len(signature) != 64:
        raise ValueError(f"{field} must contain exactly 64 bytes")
    return signature


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "provider_key_rotation_allowed": False,
        "provider_activation_allowed": False,
        "current_admission_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_witness_ownership_provider_key_continuity_state_v1(
    provider_preregistration_document: Any,
    *,
    key_epoch: Any,
    active_public_key_spki_sha256: Any,
    predecessor_key_state_hash: Any,
    last_rotation_event_hash: Any,
    provider_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(provider_preregistration_kwargs) is not dict:
        raise ValueError("provider_preregistration_kwargs must be an exact dict")
    if not provider_preregistration.verify_witness_ownership_state_provider_preregistration_v1(
        provider_preregistration_document,
        **dict(provider_preregistration_kwargs),
    ):
        raise ValueError("provider preregistration is not exact")
    if not isinstance(provider_preregistration_document, Mapping):
        raise ValueError("provider preregistration must be a mapping")
    epoch = _require_epoch("key_epoch", key_epoch)
    active_key_hash = _require_hash(
        "active_public_key_spki_sha256", active_public_key_spki_sha256
    )
    predecessor_hash = _require_hash(
        "predecessor_key_state_hash", predecessor_key_state_hash
    )
    rotation_event_hash = _require_hash(
        "last_rotation_event_hash", last_rotation_event_hash
    )
    preregistered_key_hash = provider_preregistration_document["identity"][
        "public_key_spki_sha256"
    ]
    if epoch == 0:
        if (
            active_key_hash != preregistered_key_hash
            or predecessor_hash != ZERO_HASH
            or rotation_event_hash != ZERO_HASH
        ):
            raise ValueError("genesis key state must match preregistration")
    elif predecessor_hash == ZERO_HASH or rotation_event_hash == ZERO_HASH:
        raise ValueError("non-genesis key state requires predecessor and event")
    body = {
        "schema_version": KEY_STATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "provider": {
            "registry_id": provider_preregistration_document["identity"][
                "registry_id"
            ],
            "provider_preregistration_hash": (
                provider_preregistration_document["preregistration_hash"]
            ),
        },
        "state": {
            "key_epoch": epoch,
            "active_public_key_spki_sha256": active_key_hash,
            "predecessor_key_state_hash": predecessor_hash,
            "last_rotation_event_hash": rotation_event_hash,
        },
        "facts": {
            "state_structure_complete": True,
            "key_state_persistence_verified": False,
            "provider_key_control_continuity_verified": False,
            "revocation_source_verified": False,
            "trusted_rotation_clock_verified": False,
            "runtime_assets_accessed": False,
            "network_accessed": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "key_state_hash")


def verify_witness_ownership_provider_key_continuity_state_v1(
    document: Any,
    provider_preregistration_document: Any,
    **build_kwargs: Any,
) -> bool:
    try:
        expected = build_witness_ownership_provider_key_continuity_state_v1(
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _rotation_event_hash(
    *,
    provider_preregistration_hash: str,
    previous_key_state_hash: str,
    previous_key_epoch: int,
    previous_public_key_spki_sha256: str,
    next_key_epoch: int,
    next_public_key_spki_sha256: str,
    rotation_nonce_hash: str,
    revocation_snapshot_hash: str,
    rotation_reason_code: str,
) -> str:
    return strict_canonical_hash(
        {
            "provider_preregistration_hash": provider_preregistration_hash,
            "previous_key_state_hash": previous_key_state_hash,
            "previous_key_epoch": previous_key_epoch,
            "previous_public_key_spki_sha256": (
                previous_public_key_spki_sha256
            ),
            "next_key_epoch": next_key_epoch,
            "next_public_key_spki_sha256": next_public_key_spki_sha256,
            "rotation_nonce_hash": rotation_nonce_hash,
            "revocation_snapshot_hash": revocation_snapshot_hash,
            "rotation_reason_code": rotation_reason_code,
        }
    )


def build_witness_ownership_provider_key_rotation_claim_v1(
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_previous_key_state_hash: Any,
    previous_key_state_build_kwargs: Any,
    next_public_key_spki_sha256: Any,
    rotation_nonce_hash: Any,
    revocation_snapshot_hash: Any,
    rotation_reason_code: Any,
    provider_preregistration_kwargs: Any,
) -> dict[str, Any]:
    previous_hash = _require_hash(
        "expected_previous_key_state_hash", expected_previous_key_state_hash
    )
    if (
        type(previous_key_state_build_kwargs) is not dict
        or type(provider_preregistration_kwargs) is not dict
        or not verify_witness_ownership_provider_key_continuity_state_v1(
            previous_key_state_document,
            provider_preregistration_document,
            **dict(previous_key_state_build_kwargs),
        )
        or previous_key_state_document.get("key_state_hash") != previous_hash
    ):
        raise ValueError("previous key state is not exact")
    if type(rotation_reason_code) is not str or rotation_reason_code not in ROTATION_REASON_CODES:
        raise ValueError("rotation reason code is not preregistered")
    next_key_hash = _require_hash(
        "next_public_key_spki_sha256", next_public_key_spki_sha256
    )
    nonce_hash = _require_hash("rotation_nonce_hash", rotation_nonce_hash)
    revocation_hash = _require_hash(
        "revocation_snapshot_hash", revocation_snapshot_hash
    )
    previous_state = previous_key_state_document["state"]
    previous_key_hash = previous_state["active_public_key_spki_sha256"]
    previous_epoch = previous_state["key_epoch"]
    if next_key_hash == previous_key_hash:
        raise ValueError("rotation must change the active public key")
    next_epoch = previous_epoch + 1
    event_hash = _rotation_event_hash(
        provider_preregistration_hash=provider_preregistration_document[
            "preregistration_hash"
        ],
        previous_key_state_hash=previous_hash,
        previous_key_epoch=previous_epoch,
        previous_public_key_spki_sha256=previous_key_hash,
        next_key_epoch=next_epoch,
        next_public_key_spki_sha256=next_key_hash,
        rotation_nonce_hash=nonce_hash,
        revocation_snapshot_hash=revocation_hash,
        rotation_reason_code=rotation_reason_code,
    )
    next_state = build_witness_ownership_provider_key_continuity_state_v1(
        provider_preregistration_document,
        key_epoch=next_epoch,
        active_public_key_spki_sha256=next_key_hash,
        predecessor_key_state_hash=previous_hash,
        last_rotation_event_hash=event_hash,
        provider_preregistration_kwargs=provider_preregistration_kwargs,
    )
    body = {
        "schema_version": ROTATION_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "KEY_ROTATION_TRANSITION_CANDIDATE_DUAL_SIGNATURE_AND_EXTERNAL_"
            "REVOCATION_SOURCE_TRUTH_UNVERIFIED"
        ),
        "provider": {
            "registry_id": provider_preregistration_document["identity"][
                "registry_id"
            ],
            "provider_preregistration_hash": (
                provider_preregistration_document["preregistration_hash"]
            ),
        },
        "transition": {
            "previous_key_state_hash": previous_hash,
            "previous_key_epoch": previous_epoch,
            "previous_public_key_spki_sha256": previous_key_hash,
            "next_key_epoch": next_epoch,
            "next_public_key_spki_sha256": next_key_hash,
            "rotation_nonce_hash": nonce_hash,
            "revocation_snapshot_hash": revocation_hash,
            "rotation_reason_code": rotation_reason_code,
            "rotation_event_hash": event_hash,
            "next_key_state_hash": next_state["key_state_hash"],
        },
        "next_key_state_candidate": next_state,
        "signature_contract": {
            "algorithm": SIGNATURE_ALGORITHM,
            "domain": SIGNATURE_DOMAIN,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
            "old_key_signature_required": True,
            "new_key_signature_required": True,
        },
        "facts": {
            "key_epoch_increment_arithmetic_verified": True,
            "new_key_differs_from_previous_key": True,
            "dual_signature_verified": False,
            "revocation_source_verified": False,
            "trusted_rotation_clock_verified": False,
            "key_state_persistence_verified": False,
            "provider_key_control_continuity_verified": False,
            "runtime_assets_accessed": False,
            "network_accessed": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "rotation_claim_hash")


def verify_witness_ownership_provider_key_rotation_claim_v1(
    document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_rotation_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not _is_hash(expected_rotation_claim_hash):
        return False
    try:
        expected = build_witness_ownership_provider_key_rotation_claim_v1(
            previous_key_state_document,
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        expected["rotation_claim_hash"] == expected_rotation_claim_hash
        and strict_json_contract_equal(document, expected)
    )


def build_witness_ownership_provider_key_rotation_signature_message_hash_v1(
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
) -> str:
    if (
        type(rotation_claim_document) is not dict
        or type(previous_key_state_document) is not dict
        or type(provider_preregistration_document) is not dict
        or not _is_hash(rotation_claim_document.get("rotation_claim_hash"))
    ):
        raise ValueError("rotation signature message inputs are invalid")
    transition = rotation_claim_document["transition"]
    return strict_canonical_hash(
        {
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "provider_preregistration_hash": provider_preregistration_document[
                "preregistration_hash"
            ],
            "rotation_claim_hash": rotation_claim_document[
                "rotation_claim_hash"
            ],
            "rotation_event_hash": transition["rotation_event_hash"],
            "previous_key_state_hash": previous_key_state_document[
                "key_state_hash"
            ],
            "previous_key_epoch": transition["previous_key_epoch"],
            "previous_public_key_spki_sha256": transition[
                "previous_public_key_spki_sha256"
            ],
            "next_key_epoch": transition["next_key_epoch"],
            "next_public_key_spki_sha256": transition[
                "next_public_key_spki_sha256"
            ],
            "revocation_snapshot_hash": transition[
                "revocation_snapshot_hash"
            ],
        }
    )


def build_dual_signed_witness_ownership_provider_key_rotation_v1(
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    old_public_key_spki_base64: Any,
    new_public_key_spki_base64: Any,
    old_signature_base64: Any,
    new_signature_base64: Any,
    expected_rotation_claim_hash: Any,
    rotation_claim_build_kwargs: Any,
) -> dict[str, Any]:
    if type(rotation_claim_build_kwargs) is not dict or not verify_witness_ownership_provider_key_rotation_claim_v1(
        rotation_claim_document,
        previous_key_state_document,
        provider_preregistration_document,
        expected_rotation_claim_hash=expected_rotation_claim_hash,
        **dict(rotation_claim_build_kwargs),
    ):
        raise ValueError("rotation claim is not exact")
    old_spki, _ = _decode_public_key(
        old_public_key_spki_base64, "old_public_key_spki_base64"
    )
    new_spki, _ = _decode_public_key(
        new_public_key_spki_base64, "new_public_key_spki_base64"
    )
    _decode_signature(old_signature_base64, "old_signature_base64")
    _decode_signature(new_signature_base64, "new_signature_base64")
    old_key_hash = sha256(old_spki).hexdigest()
    new_key_hash = sha256(new_spki).hexdigest()
    transition = rotation_claim_document["transition"]
    if (
        old_key_hash != transition["previous_public_key_spki_sha256"]
        or new_key_hash != transition["next_public_key_spki_sha256"]
        or old_key_hash == new_key_hash
    ):
        raise ValueError("dual signature keys do not bind the rotation claim")
    message_hash = build_witness_ownership_provider_key_rotation_signature_message_hash_v1(
        rotation_claim_document,
        previous_key_state_document,
        provider_preregistration_document,
    )
    body = {
        "schema_version": SIGNED_ROTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "DUAL_SIGNED_CANDIDATE",
        "provider_preregistration_hash": provider_preregistration_document[
            "preregistration_hash"
        ],
        "rotation_claim_hash": expected_rotation_claim_hash,
        "rotation_event_hash": transition["rotation_event_hash"],
        "previous_key_state_hash": previous_key_state_document[
            "key_state_hash"
        ],
        "next_key_state_hash": transition["next_key_state_hash"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_message_hash": message_hash,
        "old_public_key_spki_base64": old_public_key_spki_base64,
        "old_public_key_spki_sha256": old_key_hash,
        "old_signature_base64": old_signature_base64,
        "new_public_key_spki_base64": new_public_key_spki_base64,
        "new_public_key_spki_sha256": new_key_hash,
        "new_signature_base64": new_signature_base64,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "dual_signed_rotation_hash")


def evaluate_dual_signed_witness_ownership_provider_key_rotation_v1(
    signed_rotation_document: Any,
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    old_public_key_spki_base64: Any,
    new_public_key_spki_base64: Any,
    old_signature_base64: Any,
    new_signature_base64: Any,
    expected_rotation_claim_hash: Any,
    expected_dual_signed_rotation_hash: Any,
    rotation_claim_build_kwargs: Any,
) -> dict[str, Any]:
    signed_document_exact = False
    old_signature_verified = False
    new_signature_verified = False
    message_hash = None
    dual_signed_hash = None
    try:
        expected_dual_signed_rotation_hash = _require_hash(
            "expected_dual_signed_rotation_hash",
            expected_dual_signed_rotation_hash,
        )
        expected = build_dual_signed_witness_ownership_provider_key_rotation_v1(
            rotation_claim_document,
            previous_key_state_document,
            provider_preregistration_document,
            old_public_key_spki_base64=old_public_key_spki_base64,
            new_public_key_spki_base64=new_public_key_spki_base64,
            old_signature_base64=old_signature_base64,
            new_signature_base64=new_signature_base64,
            expected_rotation_claim_hash=expected_rotation_claim_hash,
            rotation_claim_build_kwargs=rotation_claim_build_kwargs,
        )
        dual_signed_hash = expected["dual_signed_rotation_hash"]
        signed_document_exact = (
            dual_signed_hash == expected_dual_signed_rotation_hash
            and strict_json_contract_equal(signed_rotation_document, expected)
        )
        _, old_key = _decode_public_key(
            old_public_key_spki_base64, "old_public_key_spki_base64"
        )
        _, new_key = _decode_public_key(
            new_public_key_spki_base64, "new_public_key_spki_base64"
        )
        old_signature = _decode_signature(
            old_signature_base64, "old_signature_base64"
        )
        new_signature = _decode_signature(
            new_signature_base64, "new_signature_base64"
        )
        message_hash = expected["signature_message_hash"]
        try:
            old_key.verify(old_signature, bytes.fromhex(message_hash))
            old_signature_verified = True
        except (InvalidSignature, ValueError):
            old_signature_verified = False
        try:
            new_key.verify(new_signature, bytes.fromhex(message_hash))
            new_signature_verified = True
        except (InvalidSignature, ValueError):
            new_signature_verified = False
    except (KeyError, TypeError, ValueError):
        pass
    dual_signature_verified = (
        signed_document_exact
        and old_signature_verified
        and new_signature_verified
    )
    dynamic_blockers: list[str] = []
    if not signed_document_exact:
        dynamic_blockers.append("DUAL_SIGNED_ROTATION_DOCUMENT_NOT_EXACT")
    if not old_signature_verified:
        dynamic_blockers.append("OLD_KEY_SIGNATURE_INVALID")
    if not new_signature_verified:
        dynamic_blockers.append("NEW_KEY_SIGNATURE_INVALID")
    transition = (
        rotation_claim_document.get("transition", {})
        if isinstance(rotation_claim_document, Mapping)
        else {}
    )
    body = {
        "schema_version": ROTATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if dual_signature_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "continuity_status": (
            "LOCAL_DUAL_KEY_ROTATION_CANDIDATE_BLOCKED"
            if dual_signature_verified
            else "UNKNOWN"
        ),
        "decision": (
            "OLD_AND_NEW_KEY_SIGNATURES_VERIFIED_EXTERNAL_KEY_LIFECYCLE_"
            "SOURCE_TRUTH_STILL_BLOCKED"
            if dual_signature_verified
            else "PROVIDER_KEY_ROTATION_INVALID_OR_INCOMPLETE"
        ),
        "blockers": dynamic_blockers + list(_PERMANENT_BLOCKERS),
        "checks": [
            {
                "name": "dual_signed_rotation_document_exact",
                "ok": signed_document_exact,
            },
            {"name": "old_key_signature_verified", "ok": old_signature_verified},
            {"name": "new_key_signature_verified", "ok": new_signature_verified},
        ],
        "source": {
            "provider_preregistration_hash": (
                provider_preregistration_document.get("preregistration_hash")
                if isinstance(provider_preregistration_document, Mapping)
                else None
            ),
            "rotation_claim_hash": (
                expected_rotation_claim_hash
                if _is_hash(expected_rotation_claim_hash)
                else None
            ),
            "dual_signed_rotation_hash": dual_signed_hash,
            "signature_message_hash": message_hash,
            "previous_key_state_hash": transition.get(
                "previous_key_state_hash"
            ),
            "next_key_state_hash": transition.get("next_key_state_hash"),
            "rotation_event_hash": transition.get("rotation_event_hash"),
            "revocation_snapshot_hash": transition.get(
                "revocation_snapshot_hash"
            ),
        },
        "transition_summary": {
            "previous_key_epoch": transition.get("previous_key_epoch"),
            "next_key_epoch": transition.get("next_key_epoch"),
            "rotation_reason_code": transition.get("rotation_reason_code"),
        },
        "facts": {
            "rotation_claim_exact": signed_document_exact,
            "old_key_possession_observed": dual_signature_verified,
            "new_key_possession_observed": dual_signature_verified,
            "local_dual_key_rotation_signature_verified": (
                dual_signature_verified
            ),
            "key_epoch_increment_arithmetic_verified": (
                dual_signature_verified
            ),
            "provider_key_control_continuity_verified": False,
            "provider_organization_identity_verified": False,
            "revocation_snapshot_source_verified": False,
            "trusted_rotation_clock_verified": False,
            "key_state_persistence_verified": False,
            "provider_implementation_update_verified": False,
            "external_provider_conformance_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "network_accessed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "redaction": {
            "raw_public_keys_redacted": True,
            "raw_signatures_redacted": True,
            "raw_provider_credentials_embedded": False,
            "raw_revocation_snapshot_embedded": False,
        },
        "limitations": [
            "Dual signatures prove only local possession of the old and proposed new private keys for this rotation message.",
            "They do not prove organization continuity, revocation authority, trusted time, key-state persistence, provider implementation update, or external conformance.",
            "The candidate does not rewrite provider preregistration, conformance plans, current, pointer, runtime, paper, live, writer, or trading authority.",
        ],
    }
    return seal_strict_canonical_document(body, "rotation_evidence_hash")


def verify_dual_signed_witness_ownership_provider_key_rotation_evidence_v1(
    evidence_document: Any,
    signed_rotation_document: Any,
    rotation_claim_document: Any,
    previous_key_state_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_rotation_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_rotation_evidence_hash):
        return False
    expected = evaluate_dual_signed_witness_ownership_provider_key_rotation_v1(
        signed_rotation_document,
        rotation_claim_document,
        previous_key_state_document,
        provider_preregistration_document,
        **evaluation_kwargs,
    )
    return (
        expected["rotation_evidence_hash"] == expected_rotation_evidence_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "KEY_STATE_SCHEMA_VERSION",
    "ROTATION_CLAIM_SCHEMA_VERSION",
    "ROTATION_EVIDENCE_SCHEMA_VERSION",
    "SIGNATURE_DOMAIN",
    "SIGNED_ROTATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "ZERO_HASH",
    "build_dual_signed_witness_ownership_provider_key_rotation_v1",
    "build_witness_ownership_provider_key_continuity_state_v1",
    "build_witness_ownership_provider_key_rotation_claim_v1",
    "build_witness_ownership_provider_key_rotation_signature_message_hash_v1",
    "evaluate_dual_signed_witness_ownership_provider_key_rotation_v1",
    "verify_dual_signed_witness_ownership_provider_key_rotation_evidence_v1",
    "verify_witness_ownership_provider_key_continuity_state_v1",
    "verify_witness_ownership_provider_key_rotation_claim_v1",
]
