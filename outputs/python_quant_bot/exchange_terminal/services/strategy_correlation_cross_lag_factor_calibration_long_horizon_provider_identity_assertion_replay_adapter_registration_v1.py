from __future__ import annotations

import hashlib
import re
from typing import Any

from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-adapter-registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260926-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-adapter-registration-1"
)
REGISTERED_STATUS = "REPLAY_ADAPTER_REGISTERED_RECEIPT_UNOBSERVED"
UNKNOWN_STATUS = "UNKNOWN"
LOG_PROTOCOL = "provider-identity-assertion-append-only-log-v1"
INCLUSION_PROOF_PROTOCOL = "domain-separated-binary-merkle-inclusion-v1"
CONSISTENCY_PROOF_PROTOCOL = "domain-separated-binary-merkle-consistency-v1"
ASSERTION_DIGEST_ALGORITHM = "sha256"
ASSERTION_DIGEST_ENCODING = "lowercase-hex"
CHECKPOINT_SIGNATURE_ALGORITHM = "ed25519"
CHECKPOINT_SIGNATURE_ENCODING = "base64url-no-padding"
EMPTY_DOMAIN = "hakimi.provider-identity-assertion-replay.empty.v1"
LEAF_DOMAIN = "hakimi.provider-identity-assertion-replay.leaf.v1"
NODE_DOMAIN = "hakimi.provider-identity-assertion-replay.node.v1"
CHECKPOINT_DOMAIN = "hakimi.provider-identity-assertion-replay.checkpoint.v1"
GENESIS_ROOT_HASH = hashlib.sha256((EMPTY_DOMAIN + "\x00").encode("ascii")).hexdigest()

_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._:/-]{2,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER_FIELDS = (
    "replay_registry_id",
    "replay_registry_namespace",
    "adapter_id",
    "provider_receipt_signing_key_id",
    "identity_registry_trust_root_key_id",
    "replay_registry_trust_root_key_id",
)
_HASH_FIELDS = (
    "adapter_implementation_hash",
    "provider_receipt_signing_public_key_hash",
    "identity_registry_trust_root_public_key_hash",
    "replay_registry_trust_root_public_key_hash",
    "genesis_root_hash",
)
_ROLE_ID_FIELDS = (
    "provider_receipt_signing_key_id",
    "identity_registry_trust_root_key_id",
    "replay_registry_trust_root_key_id",
)
_ROLE_HASH_FIELDS = (
    "provider_receipt_signing_public_key_hash",
    "identity_registry_trust_root_public_key_hash",
    "replay_registry_trust_root_public_key_hash",
)
_EXACT_PROTOCOL_FIELDS = {
    "assertion_digest_algorithm": ASSERTION_DIGEST_ALGORITHM,
    "assertion_digest_encoding": ASSERTION_DIGEST_ENCODING,
    "log_protocol": LOG_PROTOCOL,
    "inclusion_proof_protocol": INCLUSION_PROOF_PROTOCOL,
    "consistency_proof_protocol": CONSISTENCY_PROOF_PROTOCOL,
    "checkpoint_signature_algorithm": CHECKPOINT_SIGNATURE_ALGORITHM,
    "checkpoint_signature_encoding": CHECKPOINT_SIGNATURE_ENCODING,
    "empty_domain": EMPTY_DOMAIN,
    "leaf_domain": LEAF_DOMAIN,
    "node_domain": NODE_DOMAIN,
    "checkpoint_domain": CHECKPOINT_DOMAIN,
}
_REGISTRATION_FIELDS = frozenset(
    _IDENTIFIER_FIELDS
    + _HASH_FIELDS
    + tuple(_EXACT_PROTOCOL_FIELDS)
    + ("genesis_tree_size",)
)


def _authority() -> dict[str, bool]:
    return {
        "replay_registry_checked": False,
        "replay_checkpoint_signature_verified": False,
        "append_only_inclusion_verified": False,
        "append_only_consistency_verified": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _facts(*, registered: bool) -> dict[str, bool]:
    return {
        "adapter_registration_sealed": registered,
        "key_roles_separated": registered,
        "empty_genesis_root_pinned": registered,
        "replay_receipt_observed": False,
        "replay_checkpoint_signature_verified": False,
        "append_only_inclusion_verified": False,
        "append_only_consistency_verified": False,
        "external_registry_trust_attested": False,
        "external_checkpoint_time_attested": False,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema": REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason": reason,
        "registration": None,
        "facts": _facts(registered=False),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _validated_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict) or set(value) != _REGISTRATION_FIELDS:
        return None, "registration_shape_invalid"

    for field in _IDENTIFIER_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or _IDENTIFIER.fullmatch(item) is None:
            return None, f"{field}_invalid"

    for field in _HASH_FIELDS:
        if not _strict_sha256(value.get(field)):
            return None, f"{field}_invalid"

    for field, expected in _EXACT_PROTOCOL_FIELDS.items():
        if value.get(field) != expected:
            return None, f"{field}_unsupported"

    tree_size = value.get("genesis_tree_size")
    if type(tree_size) is not int or tree_size != 0:
        return None, "genesis_tree_size_invalid"
    if value.get("genesis_root_hash") != GENESIS_ROOT_HASH:
        return None, "genesis_root_hash_mismatch"

    role_ids = [value[field] for field in _ROLE_ID_FIELDS]
    if len(set(role_ids)) != len(role_ids):
        return None, "trust_root_key_roles_not_separated"
    role_hashes = [value[field] for field in _ROLE_HASH_FIELDS]
    if len(set(role_hashes)) != len(role_hashes):
        return None, "trust_root_public_key_roles_not_separated"

    return {field: value[field] for field in sorted(_REGISTRATION_FIELDS)}, None


def build_provider_identity_assertion_replay_adapter_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    normalized, reason = _validated_registration(registration)
    if normalized is None:
        return _unknown(reason or "registration_invalid")

    document = {
        "schema": REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": REGISTERED_STATUS,
        "reason": "registration_sealed_no_replay_receipt_observed",
        "registration": normalized,
        "facts": _facts(registered=True),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_adapter_registration_v1(
    receipt: Any,
    *,
    registration: Any,
) -> bool:
    if not isinstance(receipt, dict) or not _strict_sha256(receipt.get("receipt_hash")):
        return False
    expected = build_provider_identity_assertion_replay_adapter_registration_v1(registration)
    if expected.get("status") != REGISTERED_STATUS:
        return False
    return strict_json_contract_equal(receipt, expected)


__all__ = [
    "ASSERTION_DIGEST_ALGORITHM",
    "ASSERTION_DIGEST_ENCODING",
    "CHECKPOINT_DOMAIN",
    "CHECKPOINT_SIGNATURE_ALGORITHM",
    "CHECKPOINT_SIGNATURE_ENCODING",
    "CONSISTENCY_PROOF_PROTOCOL",
    "EMPTY_DOMAIN",
    "GENESIS_ROOT_HASH",
    "INCLUSION_PROOF_PROTOCOL",
    "LEAF_DOMAIN",
    "LOG_PROTOCOL",
    "NODE_DOMAIN",
    "REGISTERED_STATUS",
    "REGISTRATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "build_provider_identity_assertion_replay_adapter_registration_v1",
    "verify_provider_identity_assertion_replay_adapter_registration_v1",
]
