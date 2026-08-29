from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_registration_v1 import (
    PINNED_ASSET_SCHEMA,
    REOPEN_RECEIPT_SCHEMA,
    WRITE_RECEIPT_SCHEMA,
    verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


VERIFIER_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-receipt-verifier-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260929-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-receipt-verifier-1"
)
VERIFIED_STATUS = (
    "WRITE_REOPEN_SIGNATURES_SESSION_SEPARATION_AND_RECORD_REPLAY_VERIFIED_"
    "EXTERNAL_DURABILITY_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
MAX_NATIVE_VALUE = (1 << 63) - 1

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._:/-]{2,127}\Z")
_B64URL = re.compile(r"[A-Za-z0-9_-]+\Z")
_ASSET_FIELDS = frozenset(
    {
        "schema",
        "replay_registry_id",
        "replay_registry_namespace",
        "tree_size",
        "root_hash",
        "checkpoint_hash",
        "source_replay_verifier_receipt_hash",
        "previous_pinned_asset_hash",
        "asset_created_at_ms",
        "asset_hash",
    }
)
_WRITE_FIELDS = frozenset(
    {
        "schema",
        "operation",
        "persistence_provider_id",
        "persistence_namespace",
        "adapter_id",
        "asset_hash",
        "record_hash",
        "record_count",
        "session_id",
        "written_at_ms",
        "key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)
_REOPEN_FIELDS = frozenset(
    {
        "schema",
        "operation",
        "persistence_provider_id",
        "persistence_namespace",
        "adapter_id",
        "asset_hash",
        "record_hash",
        "record_count",
        "session_id",
        "reopened_at_ms",
        "source_write_receipt_hash",
        "key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _strict_identifier(value: Any) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _decode_b64url(value: Any) -> bytes | None:
    if (
        not isinstance(value, str)
        or len(value) > 128
        or _B64URL.fullmatch(value) is None
        or len(value) % 4 == 1
    ):
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, binascii.Error):
        return None
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    return decoded if canonical == value else None


def _authority() -> dict[str, bool]:
    return {
        "persistence_provider_checked": False,
        "durable_write_verified": False,
        "durable_reopen_verified": False,
        "pinned_checkpoint_authoritative": False,
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
        "persistence_registration_verified": verified,
        "persistence_provider_public_key_hash_bound": verified,
        "checkpoint_asset_seal_verified": verified,
        "write_receipt_observed": verified,
        "reopen_receipt_observed": verified,
        "write_receipt_signature_verified": verified,
        "reopen_receipt_signature_verified": verified,
        "write_reopen_session_separation_verified": verified,
        "reopen_cardinality_one_verified": verified,
        "exact_record_replay_verified": verified,
        "source_write_receipt_bound": verified,
        "timestamp_order_verified": verified,
        "source_replay_evaluation_verified": False,
        "external_persistence_provider_trust_attested": False,
        "external_durability_attested": False,
        "external_persistence_time_attested": False,
    }


def _empty_evidence() -> dict[str, Any]:
    return {
        "persistence_registration_receipt_hash": None,
        "persistence_provider_id": None,
        "persistence_namespace": None,
        "persistence_adapter_id": None,
        "persistence_provider_public_key_hash": None,
        "asset_hash": None,
        "previous_pinned_asset_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "tree_size": None,
        "root_hash": None,
        "checkpoint_hash": None,
        "source_replay_verifier_receipt_hash": None,
        "write_receipt_hash": None,
        "reopen_receipt_hash": None,
        "write_session_hash": None,
        "reopen_session_hash": None,
        "asset_created_at_ms": None,
        "written_at_ms": None,
        "reopened_at_ms": None,
        "record_count": None,
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


def _validated_asset(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _ASSET_FIELDS:
        return None, "checkpoint_asset_shape_invalid"
    if value.get("schema") != PINNED_ASSET_SCHEMA:
        return None, "checkpoint_asset_schema_invalid"
    for field in ("replay_registry_id", "replay_registry_namespace"):
        if not _strict_identifier(value.get(field)):
            return None, f"checkpoint_asset_{field}_invalid"
    tree_size = value.get("tree_size")
    if type(tree_size) is not int or not 1 <= tree_size <= MAX_NATIVE_VALUE:
        return None, "checkpoint_asset_tree_size_invalid"
    created_at_ms = value.get("asset_created_at_ms")
    if type(created_at_ms) is not int or not 1 <= created_at_ms <= MAX_NATIVE_VALUE:
        return None, "checkpoint_asset_created_at_invalid"
    for field in (
        "root_hash",
        "checkpoint_hash",
        "source_replay_verifier_receipt_hash",
        "asset_hash",
    ):
        if not _strict_sha256(value.get(field)):
            return None, f"checkpoint_asset_{field}_invalid"
    previous_hash = value.get("previous_pinned_asset_hash")
    if previous_hash is not None and not _strict_sha256(previous_hash):
        return None, "checkpoint_asset_previous_hash_invalid"
    unsigned = dict(value)
    unsigned.pop("asset_hash")
    expected = seal_strict_canonical_document(unsigned, "asset_hash")
    if not strict_json_contract_equal(value, expected):
        return None, "checkpoint_asset_seal_invalid"
    return dict(value), None


def _validated_write_receipt(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _WRITE_FIELDS:
        return None, "write_receipt_shape_invalid"
    if value.get("schema") != WRITE_RECEIPT_SCHEMA or value.get("operation") != "WRITE":
        return None, "write_receipt_contract_invalid"
    for field in (
        "persistence_provider_id",
        "persistence_namespace",
        "adapter_id",
        "session_id",
        "key_id",
    ):
        if not _strict_identifier(value.get(field)):
            return None, f"write_receipt_{field}_invalid"
    for field in ("asset_hash", "record_hash"):
        if not _strict_sha256(value.get(field)):
            return None, f"write_receipt_{field}_invalid"
    if type(value.get("record_count")) is not int:
        return None, "write_receipt_record_count_invalid"
    if type(value.get("written_at_ms")) is not int or not 1 <= value["written_at_ms"] <= MAX_NATIVE_VALUE:
        return None, "write_receipt_timestamp_invalid"
    if not isinstance(value.get("signature_algorithm"), str) or not isinstance(value.get("signature_encoding"), str):
        return None, "write_receipt_signature_contract_invalid"
    if _decode_b64url(value.get("signature")) is None:
        return None, "write_receipt_signature_encoding_invalid"
    return dict(value), None


def _validated_reopen_receipt(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _REOPEN_FIELDS:
        return None, "reopen_receipt_shape_invalid"
    if value.get("schema") != REOPEN_RECEIPT_SCHEMA or value.get("operation") != "REOPEN":
        return None, "reopen_receipt_contract_invalid"
    for field in (
        "persistence_provider_id",
        "persistence_namespace",
        "adapter_id",
        "session_id",
        "key_id",
    ):
        if not _strict_identifier(value.get(field)):
            return None, f"reopen_receipt_{field}_invalid"
    for field in ("asset_hash", "record_hash", "source_write_receipt_hash"):
        if not _strict_sha256(value.get(field)):
            return None, f"reopen_receipt_{field}_invalid"
    if type(value.get("record_count")) is not int:
        return None, "reopen_receipt_record_count_invalid"
    if type(value.get("reopened_at_ms")) is not int or not 1 <= value["reopened_at_ms"] <= MAX_NATIVE_VALUE:
        return None, "reopen_receipt_timestamp_invalid"
    if not isinstance(value.get("signature_algorithm"), str) or not isinstance(value.get("signature_encoding"), str):
        return None, "reopen_receipt_signature_contract_invalid"
    if _decode_b64url(value.get("signature")) is None:
        return None, "reopen_receipt_signature_encoding_invalid"
    return dict(value), None


def _signature_message(receipt: dict[str, Any]) -> bytes:
    unsigned = dict(receipt)
    unsigned.pop("signature")
    canonical = json.dumps(
        unsigned,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return receipt["schema"].encode("ascii") + b"\x00" + canonical


def _verify_signature(public_key: bytes, receipt: dict[str, Any]) -> bool:
    signature = _decode_b64url(receipt.get("signature"))
    if signature is None or len(signature) != 64:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            _signature_message(receipt),
        )
    except (InvalidSignature, ValueError):
        return False
    return True


def evaluate_provider_identity_assertion_replay_checkpoint_persistence_receipts_v1(
    *,
    replay_registration: Any,
    replay_registration_receipt: Any,
    persistence_configuration: Any,
    persistence_registration_receipt: Any,
    persistence_provider_public_key: Any,
    checkpoint_asset: Any,
    write_receipt: Any,
    reopen_receipt: Any,
) -> dict[str, Any]:
    if not verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
        persistence_registration_receipt,
        replay_registration=replay_registration,
        replay_registration_receipt=replay_registration_receipt,
        persistence_configuration=persistence_configuration,
    ):
        return _unknown("persistence_registration_receipt_invalid")
    configuration = persistence_registration_receipt["configuration"]

    public_key = _decode_b64url(persistence_provider_public_key)
    if public_key is None or len(public_key) != 32:
        return _unknown("persistence_provider_public_key_invalid")
    public_key_hash = hashlib.sha256(public_key).hexdigest()
    if public_key_hash != configuration["persistence_provider_public_key_hash"]:
        return _unknown("persistence_provider_public_key_hash_mismatch")

    asset, reason = _validated_asset(checkpoint_asset)
    if asset is None:
        return _unknown(reason or "checkpoint_asset_invalid")
    write, reason = _validated_write_receipt(write_receipt)
    if write is None:
        return _unknown(reason or "write_receipt_invalid")
    reopen, reason = _validated_reopen_receipt(reopen_receipt)
    if reopen is None:
        return _unknown(reason or "reopen_receipt_invalid")

    expected_bindings = {
        "persistence_provider_id": configuration["persistence_provider_id"],
        "persistence_namespace": configuration["persistence_namespace"],
        "adapter_id": configuration["adapter_id"],
        "key_id": configuration["persistence_provider_key_id"],
        "signature_algorithm": configuration["signature_algorithm"],
        "signature_encoding": configuration["signature_encoding"],
    }
    for role, receipt in (("write", write), ("reopen", reopen)):
        for field, expected in expected_bindings.items():
            if receipt.get(field) != expected:
                return _unknown(f"{role}_receipt_{field}_mismatch")
    source = persistence_registration_receipt["source_replay_registration"]
    for field in ("replay_registry_id", "replay_registry_namespace"):
        if asset.get(field) != source[field]:
            return _unknown(f"checkpoint_asset_{field}_mismatch")

    asset_hash = asset["asset_hash"]
    if write["asset_hash"] != asset_hash or reopen["asset_hash"] != asset_hash:
        return _unknown("checkpoint_asset_hash_binding_mismatch")
    if write["record_hash"] != asset_hash or reopen["record_hash"] != asset_hash:
        return _unknown("checkpoint_record_hash_replay_mismatch")
    if type(write["record_count"]) is not int or write["record_count"] != 1:
        return _unknown("write_record_cardinality_invalid")
    if type(reopen["record_count"]) is not int or reopen["record_count"] != 1:
        return _unknown("reopen_record_cardinality_invalid")
    if write["session_id"] == reopen["session_id"]:
        return _unknown("write_reopen_session_not_separated")
    if not asset["asset_created_at_ms"] <= write["written_at_ms"] < reopen["reopened_at_ms"]:
        return _unknown("write_reopen_timestamp_order_invalid")

    write_receipt_hash = strict_canonical_hash(write)
    if reopen["source_write_receipt_hash"] != write_receipt_hash:
        return _unknown("source_write_receipt_hash_mismatch")
    if not _verify_signature(public_key, write):
        return _unknown("write_receipt_signature_unverified")
    if not _verify_signature(public_key, reopen):
        return _unknown("reopen_receipt_signature_unverified")

    evidence = {
        "persistence_registration_receipt_hash": persistence_registration_receipt["receipt_hash"],
        "persistence_provider_id": configuration["persistence_provider_id"],
        "persistence_namespace": configuration["persistence_namespace"],
        "persistence_adapter_id": configuration["adapter_id"],
        "persistence_provider_public_key_hash": public_key_hash,
        "asset_hash": asset_hash,
        "previous_pinned_asset_hash": asset["previous_pinned_asset_hash"],
        "replay_registry_id": asset["replay_registry_id"],
        "replay_registry_namespace": asset["replay_registry_namespace"],
        "tree_size": asset["tree_size"],
        "root_hash": asset["root_hash"],
        "checkpoint_hash": asset["checkpoint_hash"],
        "source_replay_verifier_receipt_hash": asset["source_replay_verifier_receipt_hash"],
        "write_receipt_hash": write_receipt_hash,
        "reopen_receipt_hash": strict_canonical_hash(reopen),
        "write_session_hash": hashlib.sha256(write["session_id"].encode("utf-8")).hexdigest(),
        "reopen_session_hash": hashlib.sha256(reopen["session_id"].encode("utf-8")).hexdigest(),
        "asset_created_at_ms": asset["asset_created_at_ms"],
        "written_at_ms": write["written_at_ms"],
        "reopened_at_ms": reopen["reopened_at_ms"],
        "record_count": 1,
    }
    document = {
        "schema": VERIFIER_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": VERIFIED_STATUS,
        "reason": "signed_write_reopen_record_replay_verified_external_durability_unproven",
        "evidence": evidence,
        "facts": _facts(verified=True),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1(
    evaluation: Any,
    *,
    replay_registration: Any,
    replay_registration_receipt: Any,
    persistence_configuration: Any,
    persistence_registration_receipt: Any,
    persistence_provider_public_key: Any,
    checkpoint_asset: Any,
    write_receipt: Any,
    reopen_receipt: Any,
) -> bool:
    if type(evaluation) is not dict or not _strict_sha256(evaluation.get("receipt_hash")):
        return False
    expected = evaluate_provider_identity_assertion_replay_checkpoint_persistence_receipts_v1(
        replay_registration=replay_registration,
        replay_registration_receipt=replay_registration_receipt,
        persistence_configuration=persistence_configuration,
        persistence_registration_receipt=persistence_registration_receipt,
        persistence_provider_public_key=persistence_provider_public_key,
        checkpoint_asset=checkpoint_asset,
        write_receipt=write_receipt,
        reopen_receipt=reopen_receipt,
    )
    if expected.get("status") != VERIFIED_STATUS:
        return False
    return strict_json_contract_equal(evaluation, expected)


__all__ = [
    "MAX_NATIVE_VALUE",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "VERIFIER_SCHEMA",
    "evaluate_provider_identity_assertion_replay_checkpoint_persistence_receipts_v1",
    "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1",
]
