from __future__ import annotations

import re
from typing import Any

from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 import (
    verify_provider_identity_assertion_replay_adapter_registration_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-registration-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260928-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-registration-1"
)
REGISTERED_STATUS = "PERSISTENCE_ADAPTER_REGISTERED_RECEIPTS_UNOBSERVED"
UNKNOWN_STATUS = "UNKNOWN"
CANONICAL_HASH_ALGORITHM = "sha256"
CANONICAL_HASH_ENCODING = "lowercase-hex"
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_ENCODING = "base64url-no-padding"
PINNED_ASSET_SCHEMA = "provider-identity-assertion-replay-pinned-checkpoint-asset-v1"
WRITE_RECEIPT_SCHEMA = "provider-identity-assertion-replay-checkpoint-write-receipt-v1"
REOPEN_RECEIPT_SCHEMA = "provider-identity-assertion-replay-checkpoint-reopen-receipt-v1"
SESSION_POLICY = "write-and-reopen-distinct-v1"
CARDINALITY_POLICY = "exactly-one-after-reopen-v1"
RECORD_REPLAY_POLICY = "exact-canonical-hash-v1"
TIMESTAMP_ORDER_POLICY = "write-before-reopen-v1"
PROVIDER_MODE = "external-receipt-only-no-local-io-v1"

_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._:/-]{2,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER_FIELDS = (
    "persistence_provider_id",
    "persistence_namespace",
    "adapter_id",
    "persistence_provider_key_id",
)
_HASH_FIELDS = (
    "adapter_implementation_hash",
    "persistence_provider_public_key_hash",
    "source_replay_registration_receipt_hash",
)
_EXACT_FIELDS = {
    "canonical_hash_algorithm": CANONICAL_HASH_ALGORITHM,
    "canonical_hash_encoding": CANONICAL_HASH_ENCODING,
    "signature_algorithm": SIGNATURE_ALGORITHM,
    "signature_encoding": SIGNATURE_ENCODING,
    "pinned_asset_schema": PINNED_ASSET_SCHEMA,
    "write_receipt_schema": WRITE_RECEIPT_SCHEMA,
    "reopen_receipt_schema": REOPEN_RECEIPT_SCHEMA,
    "session_policy": SESSION_POLICY,
    "cardinality_policy": CARDINALITY_POLICY,
    "record_replay_policy": RECORD_REPLAY_POLICY,
    "timestamp_order_policy": TIMESTAMP_ORDER_POLICY,
    "provider_mode": PROVIDER_MODE,
}
_CONFIGURATION_FIELDS = frozenset(
    _IDENTIFIER_FIELDS + _HASH_FIELDS + tuple(_EXACT_FIELDS)
)
_SOURCE_KEY_ID_FIELDS = (
    "provider_receipt_signing_key_id",
    "identity_registry_trust_root_key_id",
    "replay_registry_trust_root_key_id",
)
_SOURCE_KEY_HASH_FIELDS = (
    "provider_receipt_signing_public_key_hash",
    "identity_registry_trust_root_public_key_hash",
    "replay_registry_trust_root_public_key_hash",
)


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _authority() -> dict[str, bool]:
    return {
        "persistence_provider_checked": False,
        "durable_write_verified": False,
        "durable_reopen_verified": False,
        "write_reopen_session_separation_verified": False,
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


def _facts(*, registered: bool) -> dict[str, bool]:
    return {
        "persistence_registration_sealed": registered,
        "source_replay_registration_bound": registered,
        "persistence_key_role_separated": registered,
        "write_reopen_contract_pinned": registered,
        "write_receipt_observed": False,
        "reopen_receipt_observed": False,
        "durable_write_verified": False,
        "durable_reopen_verified": False,
        "write_reopen_session_separation_verified": False,
        "external_persistence_provider_trust_attested": False,
        "external_persistence_time_attested": False,
    }


def _empty_source() -> dict[str, Any]:
    return {
        "replay_registration_receipt_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "replay_adapter_id": None,
        "replay_adapter_implementation_hash": None,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema": REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason": reason,
        "source_replay_registration": _empty_source(),
        "configuration": None,
        "facts": _facts(registered=False),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _validated_configuration(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _CONFIGURATION_FIELDS:
        return None, "persistence_configuration_shape_invalid"
    for field in _IDENTIFIER_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or _IDENTIFIER.fullmatch(item) is None:
            return None, f"{field}_invalid"
    for field in _HASH_FIELDS:
        if not _strict_sha256(value.get(field)):
            return None, f"{field}_invalid"
    for field, expected in _EXACT_FIELDS.items():
        if value.get(field) != expected:
            return None, f"{field}_unsupported"
    return {field: value[field] for field in sorted(_CONFIGURATION_FIELDS)}, None


def build_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
    *,
    replay_registration: Any,
    replay_registration_receipt: Any,
    persistence_configuration: Any,
) -> dict[str, Any]:
    if not verify_provider_identity_assertion_replay_adapter_registration_v1(
        replay_registration_receipt,
        registration=replay_registration,
    ):
        return _unknown("source_replay_registration_receipt_invalid")
    source = replay_registration_receipt["registration"]
    configuration, reason = _validated_configuration(persistence_configuration)
    if configuration is None:
        return _unknown(reason or "persistence_configuration_invalid")
    if (
        configuration["source_replay_registration_receipt_hash"]
        != replay_registration_receipt["receipt_hash"]
    ):
        return _unknown("source_replay_registration_receipt_hash_mismatch")

    source_key_ids = {source[field] for field in _SOURCE_KEY_ID_FIELDS}
    source_key_hashes = {source[field] for field in _SOURCE_KEY_HASH_FIELDS}
    if configuration["persistence_provider_key_id"] in source_key_ids:
        return _unknown("persistence_provider_key_role_not_separated")
    if configuration["persistence_provider_public_key_hash"] in source_key_hashes:
        return _unknown("persistence_provider_public_key_role_not_separated")
    if configuration["adapter_id"] == source["adapter_id"]:
        return _unknown("persistence_adapter_role_not_separated")
    if configuration["persistence_provider_id"] == source["replay_registry_id"]:
        return _unknown("persistence_provider_role_not_separated")

    document = {
        "schema": REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": REGISTERED_STATUS,
        "reason": "persistence_contract_registered_receipts_unobserved",
        "source_replay_registration": {
            "replay_registration_receipt_hash": replay_registration_receipt["receipt_hash"],
            "replay_registry_id": source["replay_registry_id"],
            "replay_registry_namespace": source["replay_registry_namespace"],
            "replay_adapter_id": source["adapter_id"],
            "replay_adapter_implementation_hash": source["adapter_implementation_hash"],
        },
        "configuration": configuration,
        "facts": _facts(registered=True),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
    receipt: Any,
    *,
    replay_registration: Any,
    replay_registration_receipt: Any,
    persistence_configuration: Any,
) -> bool:
    if type(receipt) is not dict or not _strict_sha256(receipt.get("receipt_hash")):
        return False
    expected = build_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
        replay_registration=replay_registration,
        replay_registration_receipt=replay_registration_receipt,
        persistence_configuration=persistence_configuration,
    )
    if expected.get("status") != REGISTERED_STATUS:
        return False
    return strict_json_contract_equal(receipt, expected)


__all__ = [
    "CANONICAL_HASH_ALGORITHM",
    "CANONICAL_HASH_ENCODING",
    "CARDINALITY_POLICY",
    "PINNED_ASSET_SCHEMA",
    "PROVIDER_MODE",
    "RECORD_REPLAY_POLICY",
    "REGISTERED_STATUS",
    "REGISTRATION_SCHEMA",
    "REOPEN_RECEIPT_SCHEMA",
    "SESSION_POLICY",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_ENCODING",
    "STATIC_FINGERPRINT",
    "TIMESTAMP_ORDER_POLICY",
    "UNKNOWN_STATUS",
    "WRITE_RECEIPT_SCHEMA",
    "build_provider_identity_assertion_replay_checkpoint_persistence_registration_v1",
    "verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1",
]
