from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 import (
    CHECKPOINT_DOMAIN,
    GENESIS_ROOT_HASH,
    LEAF_DOMAIN,
    NODE_DOMAIN,
    verify_provider_identity_assertion_replay_adapter_registration_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


VERIFIER_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-receipt-verifier-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260927-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-receipt-verifier-1"
)
REPLAY_RECEIPT_SCHEMA = "provider-identity-assertion-replay-receipt-v1"
CHECKPOINT_SCHEMA = "provider-identity-assertion-replay-checkpoint-v1"
PINNED_CHECKPOINT_SCHEMA = "provider-identity-assertion-replay-pinned-checkpoint-v1"
VERIFIED_STATUS = (
    "REPLAY_CHECKPOINT_SIGNATURE_INCLUSION_AND_CONSISTENCY_VERIFIED_"
    "EXTERNAL_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
MAX_TREE_SIZE = (1 << 63) - 1
MAX_PROOF_LENGTH = 128

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_B64URL = re.compile(r"[A-Za-z0-9_-]+\Z")
_CHECKPOINT_FIELDS = frozenset(
    {
        "schema",
        "replay_registry_id",
        "replay_registry_namespace",
        "tree_size",
        "root_hash",
        "issued_at_ms",
        "key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)
_PINNED_CHECKPOINT_FIELDS = frozenset(
    {
        "schema",
        "replay_registry_id",
        "replay_registry_namespace",
        "tree_size",
        "root_hash",
    }
)
_REPLAY_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "replay_registry_id",
        "replay_registry_namespace",
        "adapter_id",
        "adapter_implementation_hash",
        "assertion_receipt_hash",
        "leaf_index",
        "checkpoint",
        "inclusion_proof",
        "consistency_proof",
    }
)


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _decode_b64url(value: Any) -> bytes | None:
    if not isinstance(value, str) or _B64URL.fullmatch(value) is None:
        return None
    if len(value) % 4 == 1:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error):
        return None
    encoded = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    return decoded if encoded == value else None


def _proof(value: Any) -> list[str] | None:
    if type(value) is not list or len(value) > MAX_PROOF_LENGTH:
        return None
    if not all(_strict_sha256(item) for item in value):
        return None
    return list(value)


def _authority() -> dict[str, bool]:
    return {
        "replay_registry_checked": False,
        "replay_absence_verified": False,
        "assertion_uniqueness_verified": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _facts(*, verified: bool) -> dict[str, bool]:
    return {
        "registration_contract_verified": verified,
        "replay_registry_public_key_hash_bound": verified,
        "replay_receipt_observed": verified,
        "checkpoint_signature_verified": verified,
        "assertion_inclusion_verified": verified,
        "append_only_consistency_verified": verified,
        "external_registry_trust_attested": False,
        "external_checkpoint_time_attested": False,
        "assertion_uniqueness_verified": False,
        "replay_absence_verified": False,
    }


def _empty_evidence() -> dict[str, Any]:
    return {
        "registration_receipt_hash": None,
        "replay_receipt_hash": None,
        "assertion_receipt_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "adapter_id": None,
        "adapter_implementation_hash": None,
        "replay_registry_public_key_hash": None,
        "pinned_tree_size": None,
        "pinned_root_hash": None,
        "checkpoint_tree_size": None,
        "checkpoint_root_hash": None,
        "checkpoint_hash": None,
        "checkpoint_issued_at_ms": None,
        "leaf_index": None,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema": VERIFIER_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason": reason,
        "evidence": _empty_evidence(),
        "facts": _facts(verified=False),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _validated_checkpoint(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _CHECKPOINT_FIELDS:
        return None, "checkpoint_shape_invalid"
    if value.get("schema") != CHECKPOINT_SCHEMA:
        return None, "checkpoint_schema_invalid"
    if not all(
        isinstance(value.get(field), str) and bool(value.get(field))
        for field in (
            "replay_registry_id",
            "replay_registry_namespace",
            "key_id",
            "signature_algorithm",
            "signature_encoding",
        )
    ):
        return None, "checkpoint_identity_invalid"
    tree_size = value.get("tree_size")
    if type(tree_size) is not int or not 1 <= tree_size <= MAX_TREE_SIZE:
        return None, "checkpoint_tree_size_invalid"
    issued_at_ms = value.get("issued_at_ms")
    if type(issued_at_ms) is not int or not 1 <= issued_at_ms <= MAX_TREE_SIZE:
        return None, "checkpoint_issued_at_ms_invalid"
    if not _strict_sha256(value.get("root_hash")):
        return None, "checkpoint_root_hash_invalid"
    if _decode_b64url(value.get("signature")) is None:
        return None, "checkpoint_signature_encoding_invalid"
    return dict(value), None


def _validated_pinned_checkpoint(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _PINNED_CHECKPOINT_FIELDS:
        return None, "pinned_checkpoint_shape_invalid"
    if value.get("schema") != PINNED_CHECKPOINT_SCHEMA:
        return None, "pinned_checkpoint_schema_invalid"
    if not all(
        isinstance(value.get(field), str) and bool(value.get(field))
        for field in ("replay_registry_id", "replay_registry_namespace")
    ):
        return None, "pinned_checkpoint_identity_invalid"
    tree_size = value.get("tree_size")
    if type(tree_size) is not int or not 0 <= tree_size <= MAX_TREE_SIZE:
        return None, "pinned_checkpoint_tree_size_invalid"
    if not _strict_sha256(value.get("root_hash")):
        return None, "pinned_checkpoint_root_hash_invalid"
    if tree_size == 0 and value.get("root_hash") != GENESIS_ROOT_HASH:
        return None, "pinned_genesis_root_mismatch"
    return dict(value), None


def _validated_replay_receipt(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _REPLAY_RECEIPT_FIELDS:
        return None, "replay_receipt_shape_invalid"
    if value.get("schema") != REPLAY_RECEIPT_SCHEMA:
        return None, "replay_receipt_schema_invalid"
    if not all(
        isinstance(value.get(field), str) and bool(value.get(field))
        for field in (
            "replay_registry_id",
            "replay_registry_namespace",
            "adapter_id",
        )
    ):
        return None, "replay_receipt_identity_invalid"
    for field in ("adapter_implementation_hash", "assertion_receipt_hash"):
        if not _strict_sha256(value.get(field)):
            return None, f"{field}_invalid"
    leaf_index = value.get("leaf_index")
    if type(leaf_index) is not int or not 0 <= leaf_index < MAX_TREE_SIZE:
        return None, "leaf_index_invalid"
    checkpoint, reason = _validated_checkpoint(value.get("checkpoint"))
    if checkpoint is None:
        return None, reason
    inclusion_proof = _proof(value.get("inclusion_proof"))
    if inclusion_proof is None:
        return None, "inclusion_proof_invalid"
    consistency_proof = _proof(value.get("consistency_proof"))
    if consistency_proof is None:
        return None, "consistency_proof_invalid"
    normalized = dict(value)
    normalized["checkpoint"] = checkpoint
    normalized["inclusion_proof"] = inclusion_proof
    normalized["consistency_proof"] = consistency_proof
    return normalized, None


def _leaf_hash(assertion_receipt_hash: str) -> str:
    payload = LEAF_DOMAIN.encode("ascii") + b"\x00" + bytes.fromhex(assertion_receipt_hash)
    return hashlib.sha256(payload).hexdigest()


def _node_hash(left: str, right: str) -> str:
    payload = (
        NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left)
        + bytes.fromhex(right)
    )
    return hashlib.sha256(payload).hexdigest()


def _verify_inclusion(
    *,
    assertion_receipt_hash: str,
    leaf_index: int,
    tree_size: int,
    root_hash: str,
    proof: list[str],
) -> bool:
    if not 0 <= leaf_index < tree_size:
        return False
    fn = leaf_index
    sn = tree_size - 1
    running = _leaf_hash(assertion_receipt_hash)
    for sibling in proof:
        if sn == 0:
            return False
        if fn == sn or (fn & 1) == 1:
            running = _node_hash(sibling, running)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            running = _node_hash(running, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and running == root_hash


def _verify_consistency(
    *,
    old_size: int,
    new_size: int,
    old_root: str,
    new_root: str,
    proof: list[str],
) -> bool:
    if old_size == 0:
        return old_root == GENESIS_ROOT_HASH and not proof and new_size >= 1
    if old_size > new_size:
        return False
    if old_size == new_size:
        return old_root == new_root and not proof

    fn = old_size - 1
    sn = new_size - 1
    while (fn & 1) == 1:
        fn >>= 1
        sn >>= 1

    proof_index = 0
    if fn == 0:
        first_root = old_root
        second_root = old_root
    else:
        if not proof:
            return False
        first_root = proof[0]
        second_root = proof[0]
        proof_index = 1

    for sibling in proof[proof_index:]:
        if sn == 0:
            return False
        if (fn & 1) == 1 or fn == sn:
            first_root = _node_hash(sibling, first_root)
            second_root = _node_hash(sibling, second_root)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            second_root = _node_hash(second_root, sibling)
        fn >>= 1
        sn >>= 1

    return (
        fn == 0
        and sn == 0
        and first_root == old_root
        and second_root == new_root
    )


def _checkpoint_message(checkpoint: dict[str, Any]) -> bytes:
    unsigned = dict(checkpoint)
    unsigned.pop("signature")
    canonical = json.dumps(
        unsigned,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CHECKPOINT_DOMAIN.encode("ascii") + b"\x00" + canonical


def evaluate_provider_identity_assertion_replay_receipt_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    replay_receipt: Any,
    replay_registry_public_key: Any,
    pinned_checkpoint: Any,
) -> dict[str, Any]:
    if not verify_provider_identity_assertion_replay_adapter_registration_v1(
        registration_receipt,
        registration=registration,
    ):
        return _unknown("registration_receipt_invalid")
    registered = registration_receipt["registration"]

    public_key = _decode_b64url(replay_registry_public_key)
    if public_key is None or len(public_key) != 32:
        return _unknown("replay_registry_public_key_invalid")
    public_key_hash = hashlib.sha256(public_key).hexdigest()
    if public_key_hash != registered["replay_registry_trust_root_public_key_hash"]:
        return _unknown("replay_registry_public_key_hash_mismatch")

    pinned, reason = _validated_pinned_checkpoint(pinned_checkpoint)
    if pinned is None:
        return _unknown(reason or "pinned_checkpoint_invalid")
    receipt, reason = _validated_replay_receipt(replay_receipt)
    if receipt is None:
        return _unknown(reason or "replay_receipt_invalid")
    checkpoint = receipt["checkpoint"]

    expected_bindings = {
        "replay_registry_id": registered["replay_registry_id"],
        "replay_registry_namespace": registered["replay_registry_namespace"],
        "adapter_id": registered["adapter_id"],
        "adapter_implementation_hash": registered["adapter_implementation_hash"],
    }
    for field, expected in expected_bindings.items():
        if receipt.get(field) != expected:
            return _unknown(f"replay_receipt_{field}_mismatch")
    for field in ("replay_registry_id", "replay_registry_namespace"):
        if checkpoint.get(field) != expected_bindings[field]:
            return _unknown(f"checkpoint_{field}_mismatch")
        if pinned.get(field) != expected_bindings[field]:
            return _unknown(f"pinned_checkpoint_{field}_mismatch")
    if checkpoint.get("key_id") != registered["replay_registry_trust_root_key_id"]:
        return _unknown("checkpoint_key_id_mismatch")
    if checkpoint.get("signature_algorithm") != registered["checkpoint_signature_algorithm"]:
        return _unknown("checkpoint_signature_algorithm_mismatch")
    if checkpoint.get("signature_encoding") != registered["checkpoint_signature_encoding"]:
        return _unknown("checkpoint_signature_encoding_mismatch")
    if receipt["leaf_index"] >= checkpoint["tree_size"]:
        return _unknown("leaf_index_out_of_range")
    if pinned["tree_size"] > checkpoint["tree_size"]:
        return _unknown("checkpoint_rollback_detected")

    signature = _decode_b64url(checkpoint["signature"])
    if signature is None or len(signature) != 64:
        return _unknown("checkpoint_signature_invalid")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            _checkpoint_message(checkpoint),
        )
    except (InvalidSignature, ValueError):
        return _unknown("checkpoint_signature_unverified")

    if not _verify_inclusion(
        assertion_receipt_hash=receipt["assertion_receipt_hash"],
        leaf_index=receipt["leaf_index"],
        tree_size=checkpoint["tree_size"],
        root_hash=checkpoint["root_hash"],
        proof=receipt["inclusion_proof"],
    ):
        return _unknown("assertion_inclusion_unverified")
    if not _verify_consistency(
        old_size=pinned["tree_size"],
        new_size=checkpoint["tree_size"],
        old_root=pinned["root_hash"],
        new_root=checkpoint["root_hash"],
        proof=receipt["consistency_proof"],
    ):
        return _unknown("checkpoint_consistency_unverified")

    document = {
        "schema": VERIFIER_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": VERIFIED_STATUS,
        "reason": "cryptographic_replay_proof_verified_external_trust_unproven",
        "evidence": {
            "registration_receipt_hash": registration_receipt["receipt_hash"],
            "replay_receipt_hash": strict_canonical_hash(receipt),
            "assertion_receipt_hash": receipt["assertion_receipt_hash"],
            "replay_registry_id": registered["replay_registry_id"],
            "replay_registry_namespace": registered["replay_registry_namespace"],
            "adapter_id": registered["adapter_id"],
            "adapter_implementation_hash": registered["adapter_implementation_hash"],
            "replay_registry_public_key_hash": public_key_hash,
            "pinned_tree_size": pinned["tree_size"],
            "pinned_root_hash": pinned["root_hash"],
            "checkpoint_tree_size": checkpoint["tree_size"],
            "checkpoint_root_hash": checkpoint["root_hash"],
            "checkpoint_hash": strict_canonical_hash(checkpoint),
            "checkpoint_issued_at_ms": checkpoint["issued_at_ms"],
            "leaf_index": receipt["leaf_index"],
        },
        "facts": _facts(verified=True),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_receipt_evaluation_v1(
    evaluation: Any,
    *,
    registration: Any,
    registration_receipt: Any,
    replay_receipt: Any,
    replay_registry_public_key: Any,
    pinned_checkpoint: Any,
) -> bool:
    if type(evaluation) is not dict or not _strict_sha256(evaluation.get("receipt_hash")):
        return False
    expected = evaluate_provider_identity_assertion_replay_receipt_v1(
        registration=registration,
        registration_receipt=registration_receipt,
        replay_receipt=replay_receipt,
        replay_registry_public_key=replay_registry_public_key,
        pinned_checkpoint=pinned_checkpoint,
    )
    if expected.get("status") != VERIFIED_STATUS:
        return False
    return strict_json_contract_equal(evaluation, expected)


__all__ = [
    "CHECKPOINT_SCHEMA",
    "MAX_PROOF_LENGTH",
    "MAX_TREE_SIZE",
    "PINNED_CHECKPOINT_SCHEMA",
    "REPLAY_RECEIPT_SCHEMA",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "VERIFIER_SCHEMA",
    "evaluate_provider_identity_assertion_replay_receipt_v1",
    "verify_provider_identity_assertion_replay_receipt_evaluation_v1",
]
