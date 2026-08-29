"""Verify supplied write/reopen receipts for an ADR0353 checkpoint asset.

The verifier is pure and performs no I/O. It checks one sealed common-view
asset, two domain-separated Ed25519 receipts, exact single-record replay,
session separation, and preregistered timing bounds. Signed claims do not prove
external provider trust, real durability, an authoritative pin, or ADR0352
evaluation source binding.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from hmac import compare_digest
import re
from typing import Any, Callable

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1
    as persistence_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover
    InvalidSignature = Exception  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]


EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-receipt-"
    "verification-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-multi-window-lifecycle-replay-checkpoint-"
    "persistence-receipt-verifier-v1-synthetic-no-io-lock-1"
)
PERSISTENCE_REGISTRATION_V1_IMPLEMENTATION_SHA256 = (
    "7fe3b481fd6344d571cbea0066544bb61467525ac5140e1db427d00cc6ade055"
)
VERIFICATION_STATE = (
    "WRITE_REOPEN_SIGNATURES_SESSION_SEPARATION_AND_RECORD_REPLAY_VERIFIED_"
    "EXTERNAL_DURABILITY_UNPROVEN"
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_AUTHORITY = {
    "authoritative_future_pin_allowed": False,
    "candidate_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "durable_checkpoint_claim_allowed": False,
    "live_order_allowed": False,
    "paper_authorized": False,
    "persistence_provider_use_allowed": False,
    "profitability_claim_allowed": False,
    "writer_allowed": False,
}
_ASSET_FIELDS = frozenset(
    {
        "asset_created_at_utc",
        "asset_hash",
        "asset_hash_domain",
        "persistence_registration_hash",
        "previous_persisted_asset_hash",
        "schema_version",
        "source_checkpoint_issued_at_utc",
        "source_checkpoint_root_hash",
        "source_checkpoint_tree_size",
        "source_common_registry_view_hash",
        "source_preregistration_hash",
        "source_reference_time_utc",
        "source_replay_registry_id",
        "source_replay_registry_namespace",
        "static_fingerprint",
    }
)
_UNSIGNED_WRITE_FIELDS = frozenset(
    {
        "asset_hash",
        "operation",
        "persistence_adapter_id",
        "persistence_namespace",
        "persistence_provider_id",
        "persistence_provider_key_id",
        "persistence_registration_hash",
        "receipt_content_sha256",
        "receipt_encoding",
        "record_count",
        "record_hash",
        "schema_version",
        "session_id",
        "signature_algorithm",
        "signature_domain",
        "signature_message_format",
        "static_fingerprint",
        "written_at_utc",
    }
)
_WRITE_FIELDS = _UNSIGNED_WRITE_FIELDS | {
    "signature_base64",
    "signature_sha256",
    "write_receipt_hash",
}
_UNSIGNED_REOPEN_FIELDS = frozenset(
    {
        "asset_hash",
        "operation",
        "persistence_adapter_id",
        "persistence_namespace",
        "persistence_provider_id",
        "persistence_provider_key_id",
        "persistence_registration_hash",
        "receipt_content_sha256",
        "receipt_encoding",
        "record_count",
        "record_hash",
        "reopened_at_utc",
        "schema_version",
        "session_id",
        "signature_algorithm",
        "signature_domain",
        "signature_message_format",
        "source_write_receipt_hash",
        "static_fingerprint",
    }
)
_REOPEN_FIELDS = _UNSIGNED_REOPEN_FIELDS | {
    "reopen_receipt_hash",
    "signature_base64",
    "signature_sha256",
}
_BLOCKERS = (
    "EXTERNAL_PERSISTENCE_PROVIDER_AUTHORITY_UNPROVEN",
    "REAL_STORAGE_DURABILITY_UNPROVEN",
    "EXTERNAL_PERSISTENCE_TIME_UNPROVEN",
    "AUTHORITATIVE_FUTURE_PIN_UNPROVEN",
    "ADR0352_EVALUATION_SOURCE_BINDING_UNPROVEN",
    "PAPER_LIVE_UNAUTHORIZED",
)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_id(value: Any) -> bool:
    return type(value) is str and bool(_ID_RE.fullmatch(value))


def _utc(value: Any) -> datetime | None:
    if type(value) is not str or value != value.strip():
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        return None
    return parsed


def _decode_base64(value: Any, expected_length: int) -> bytes | None:
    if type(value) is not str or not value or value != value.strip():
        return None
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None
    if (
        len(decoded) != expected_length
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        return None
    return decoded


def _registration_shape_valid(registration: Any) -> bool:
    return bool(
        type(registration) is dict
        and registration.get("schema_version")
        == persistence_registration_v1.REGISTRATION_SCHEMA_VERSION
        and registration.get("static_fingerprint")
        == persistence_registration_v1.STATIC_FINGERPRINT
        and registration.get("status") == "PREREGISTERED_UNMOUNTED"
        and _exact_hash(registration.get("registration_hash"))
        and registration.get("asset_schema_version")
        == persistence_registration_v1.CHECKPOINT_ASSET_SCHEMA_VERSION
        and registration.get("write_receipt_schema_version")
        == persistence_registration_v1.WRITE_RECEIPT_SCHEMA_VERSION
        and registration.get("reopen_receipt_schema_version")
        == persistence_registration_v1.REOPEN_RECEIPT_SCHEMA_VERSION
        and registration.get("permissions") == _PERMISSIONS
        and registration.get("authority") == _AUTHORITY
    )


def build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
    registration: Any,
    *,
    asset_created_at_utc: Any,
    previous_persisted_asset_hash: Any = None,
) -> dict[str, Any] | None:
    if (
        not _registration_shape_valid(registration)
        or (
            previous_persisted_asset_hash is not None
            and not _exact_hash(previous_persisted_asset_hash)
        )
    ):
        return None
    created = _utc(asset_created_at_utc)
    checkpoint_issued = _utc(registration.get("source_checkpoint_issued_at_utc"))
    reference = _utc(registration.get("source_reference_time_utc"))
    if (
        created is None
        or checkpoint_issued is None
        or reference is None
        or not checkpoint_issued <= created <= reference
    ):
        return None
    body = {
        "asset_created_at_utc": asset_created_at_utc,
        "asset_hash_domain": persistence_registration_v1.CHECKPOINT_ASSET_HASH_DOMAIN,
        "persistence_registration_hash": registration["registration_hash"],
        "previous_persisted_asset_hash": previous_persisted_asset_hash,
        "schema_version": persistence_registration_v1.CHECKPOINT_ASSET_SCHEMA_VERSION,
        "source_checkpoint_issued_at_utc": registration[
            "source_checkpoint_issued_at_utc"
        ],
        "source_checkpoint_root_hash": registration[
            "source_checkpoint_root_hash"
        ],
        "source_checkpoint_tree_size": registration[
            "source_checkpoint_tree_size"
        ],
        "source_common_registry_view_hash": registration[
            "source_common_registry_view_hash"
        ],
        "source_preregistration_hash": registration[
            "source_preregistration_hash"
        ],
        "source_reference_time_utc": registration["source_reference_time_utc"],
        "source_replay_registry_id": registration["source_replay_registry_id"],
        "source_replay_registry_namespace": registration[
            "source_replay_registry_namespace"
        ],
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return seal_strict_canonical_document(body, "asset_hash")


def _asset_exact(asset: Any, registration: dict[str, Any]) -> bool:
    if type(asset) is not dict or frozenset(asset) != _ASSET_FIELDS:
        return False
    expected = build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
        registration,
        asset_created_at_utc=asset.get("asset_created_at_utc"),
        previous_persisted_asset_hash=asset.get("previous_persisted_asset_hash"),
    )
    return bool(
        type(expected) is dict
        and strict_json_contract_equal(asset, expected)
    )


def _unsigned_receipt(
    body: dict[str, Any],
) -> dict[str, Any]:
    return {**body, "receipt_content_sha256": strict_canonical_hash(body)}


def build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
    registration: Any,
    asset: Any,
    *,
    session_id: Any,
    written_at_utc: Any,
) -> dict[str, Any] | None:
    if (
        not _registration_shape_valid(registration)
        or not _asset_exact(asset, registration)
        or not _strict_id(session_id)
    ):
        return None
    created = _utc(asset.get("asset_created_at_utc"))
    written = _utc(written_at_utc)
    reference = _utc(registration.get("source_reference_time_utc"))
    if (
        created is None
        or written is None
        or reference is None
        or not created <= written <= reference
        or (written - created).total_seconds()
        > registration["max_write_receipt_delay_seconds"]
    ):
        return None
    body = {
        "asset_hash": asset["asset_hash"],
        "operation": "WRITE",
        "persistence_adapter_id": registration["persistence_adapter_id"],
        "persistence_namespace": registration["persistence_namespace"],
        "persistence_provider_id": registration["persistence_provider_id"],
        "persistence_provider_key_id": registration[
            "persistence_provider_key_id"
        ],
        "persistence_registration_hash": registration["registration_hash"],
        "receipt_encoding": persistence_registration_v1.RECEIPT_ENCODING,
        "record_count": 1,
        "record_hash": strict_canonical_hash(asset),
        "schema_version": persistence_registration_v1.WRITE_RECEIPT_SCHEMA_VERSION,
        "session_id": session_id,
        "signature_algorithm": persistence_registration_v1.SIGNATURE_ALGORITHM,
        "signature_domain": persistence_registration_v1.WRITE_SIGNATURE_DOMAIN,
        "signature_message_format": (
            persistence_registration_v1.SIGNATURE_MESSAGE_FORMAT
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "written_at_utc": written_at_utc,
    }
    return _unsigned_receipt(body)


def build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
    registration: Any,
    asset: Any,
    write_receipt: Any,
    *,
    session_id: Any,
    reopened_at_utc: Any,
) -> dict[str, Any] | None:
    if (
        not _registration_shape_valid(registration)
        or not _asset_exact(asset, registration)
        or type(write_receipt) is not dict
        or frozenset(write_receipt) != _WRITE_FIELDS
        or not _strict_id(session_id)
        or session_id == write_receipt.get("session_id")
        or write_receipt.get("asset_hash") != asset.get("asset_hash")
        or write_receipt.get("persistence_registration_hash")
        != registration.get("registration_hash")
        or not _exact_hash(write_receipt.get("write_receipt_hash"))
    ):
        return None
    written = _utc(write_receipt.get("written_at_utc"))
    reopened = _utc(reopened_at_utc)
    reference = _utc(registration.get("source_reference_time_utc"))
    if written is None or reopened is None or reference is None:
        return None
    separation = (reopened - written).total_seconds()
    if (
        not written < reopened <= reference
        or separation < registration["min_reopen_separation_seconds"]
        or separation > registration["max_reopen_receipt_delay_seconds"]
    ):
        return None
    body = {
        "asset_hash": asset["asset_hash"],
        "operation": "REOPEN",
        "persistence_adapter_id": registration["persistence_adapter_id"],
        "persistence_namespace": registration["persistence_namespace"],
        "persistence_provider_id": registration["persistence_provider_id"],
        "persistence_provider_key_id": registration[
            "persistence_provider_key_id"
        ],
        "persistence_registration_hash": registration["registration_hash"],
        "receipt_encoding": persistence_registration_v1.RECEIPT_ENCODING,
        "record_count": 1,
        "record_hash": strict_canonical_hash(asset),
        "reopened_at_utc": reopened_at_utc,
        "schema_version": persistence_registration_v1.REOPEN_RECEIPT_SCHEMA_VERSION,
        "session_id": session_id,
        "signature_algorithm": persistence_registration_v1.SIGNATURE_ALGORITHM,
        "signature_domain": persistence_registration_v1.REOPEN_SIGNATURE_DOMAIN,
        "signature_message_format": (
            persistence_registration_v1.SIGNATURE_MESSAGE_FORMAT
        ),
        "source_write_receipt_hash": write_receipt["write_receipt_hash"],
        "static_fingerprint": STATIC_FINGERPRINT,
    }
    return _unsigned_receipt(body)


def _assemble_receipt(
    unsigned_receipt: Any,
    unsigned_fields: frozenset[str],
    signature_base64: Any,
    hash_field: str,
) -> dict[str, Any] | None:
    if (
        type(unsigned_receipt) is not dict
        or frozenset(unsigned_receipt) != unsigned_fields
        or not _exact_hash(unsigned_receipt.get("receipt_content_sha256"))
    ):
        return None
    body = deepcopy(unsigned_receipt)
    content_hash = body.pop("receipt_content_sha256")
    if strict_canonical_hash(body) != content_hash:
        return None
    signature = _decode_base64(signature_base64, 64)
    if signature is None:
        return None
    sealed = {
        **unsigned_receipt,
        "signature_sha256": hashlib.sha256(signature).hexdigest(),
    }
    return {
        **sealed,
        "signature_base64": signature_base64,
        hash_field: strict_canonical_hash(sealed),
    }


def assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
    unsigned_receipt: Any,
    signature_base64: Any,
) -> dict[str, Any] | None:
    return _assemble_receipt(
        unsigned_receipt,
        _UNSIGNED_WRITE_FIELDS,
        signature_base64,
        "write_receipt_hash",
    )


def assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
    unsigned_receipt: Any,
    signature_base64: Any,
) -> dict[str, Any] | None:
    return _assemble_receipt(
        unsigned_receipt,
        _UNSIGNED_REOPEN_FIELDS,
        signature_base64,
        "reopen_receipt_hash",
    )


def _signature_valid(
    receipt: dict[str, Any],
    public_key_base64: Any,
    expected_public_key_hash: str,
) -> bool:
    public_key = _decode_base64(public_key_base64, 32)
    signature = _decode_base64(receipt.get("signature_base64"), 64)
    if (
        public_key is None
        or signature is None
        or hashlib.sha256(public_key).hexdigest() != expected_public_key_hash
        or Ed25519PublicKey is None
    ):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            bytes.fromhex(receipt["receipt_content_sha256"]),
        )
    except (InvalidSignature, KeyError, ValueError):
        return False
    return True


def _facts(*, verified: bool) -> dict[str, Any]:
    return {
        "authoritative_future_pin_verified": False,
        "checkpoint_asset_seal_verified": verified,
        "durable_checkpoint_publication_verified": False,
        "exact_record_replay_verified": verified,
        "external_persistence_provider_authority_verified": False,
        "external_persistence_time_verified": False,
        "local_io_performed": False,
        "persistence_provider_public_key_hash_bound": verified,
        "persistence_registration_exactly_verified": verified,
        "reopen_cardinality_one_verified": verified,
        "reopen_receipt_observed": verified,
        "reopen_receipt_signature_verified": verified,
        "source_common_registry_view_bound": verified,
        "source_replay_binding_gate_verified": False,
        "source_write_receipt_bound": verified,
        "timestamp_and_delay_policy_verified": verified,
        "write_cardinality_one_verified": verified,
        "write_receipt_observed": verified,
        "write_receipt_signature_verified": verified,
        "write_reopen_session_separation_verified": verified,
    }


def _result(
    *,
    status: str,
    reason: str,
    facts: dict[str, Any],
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": deepcopy(_AUTHORITY),
            "blockers": list(_BLOCKERS),
            "evidence": evidence,
            "facts": facts,
            "permissions": dict(_PERMISSIONS),
            "reason": reason,
            "schema_version": EVALUATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "verification_state": (
                VERIFICATION_STATE if status == "PASS" else None
            ),
        },
        "verification_hash",
    )


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
    persistence_registration: Any,
    source_preregistration: Any,
    lifecycle_binding_preregistration: Any,
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    persistence_configuration: Any,
    persistence_provider_public_key_base64: Any,
    checkpoint_asset: Any,
    write_receipt: Any,
    reopen_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_asset_hash: Any,
    expected_write_receipt_hash: Any,
    expected_reopen_receipt_hash: Any,
) -> dict[str, Any]:
    try:
        registration_exact = persistence_registration_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1(
            persistence_registration,
            source_preregistration,
            lifecycle_binding_preregistration,
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
            persistence_configuration,
            expected_registration_hash=expected_registration_hash,
        )
    except (KeyError, TypeError, ValueError):
        registration_exact = False
    if not registration_exact:
        return _result(
            status="UNKNOWN",
            reason="PERSISTENCE_REGISTRATION_EXACT_REBUILD_FAILED",
            facts=_facts(verified=False),
            evidence=None,
        )
    if (
        not _exact_hash(expected_asset_hash)
        or not _exact_hash(expected_write_receipt_hash)
        or not _exact_hash(expected_reopen_receipt_hash)
        or type(checkpoint_asset) is not dict
        or checkpoint_asset.get("asset_hash") != expected_asset_hash
        or not _asset_exact(checkpoint_asset, persistence_registration)
    ):
        return _result(
            status="UNKNOWN",
            reason="CHECKPOINT_ASSET_EXACT_REBUILD_FAILED",
            facts=_facts(verified=False),
            evidence=None,
        )
    if (
        type(write_receipt) is not dict
        or frozenset(write_receipt) != _WRITE_FIELDS
        or write_receipt.get("write_receipt_hash")
        != expected_write_receipt_hash
    ):
        return _result(
            status="UNKNOWN",
            reason="WRITE_RECEIPT_SHAPE_OR_PIN_INVALID",
            facts=_facts(verified=False),
            evidence=None,
        )
    expected_unsigned_write = build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
        persistence_registration,
        checkpoint_asset,
        session_id=write_receipt.get("session_id"),
        written_at_utc=write_receipt.get("written_at_utc"),
    )
    rebuilt_write = assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
        expected_unsigned_write,
        write_receipt.get("signature_base64"),
    )
    if (
        type(rebuilt_write) is not dict
        or not strict_json_contract_equal(write_receipt, rebuilt_write)
        or not _signature_valid(
            write_receipt,
            persistence_provider_public_key_base64,
            persistence_registration["persistence_provider_public_key_sha256"],
        )
    ):
        return _result(
            status="UNKNOWN",
            reason="WRITE_RECEIPT_EXACT_OR_SIGNATURE_INVALID",
            facts=_facts(verified=False),
            evidence=None,
        )
    if (
        type(reopen_receipt) is not dict
        or frozenset(reopen_receipt) != _REOPEN_FIELDS
        or reopen_receipt.get("reopen_receipt_hash")
        != expected_reopen_receipt_hash
    ):
        return _result(
            status="UNKNOWN",
            reason="REOPEN_RECEIPT_SHAPE_OR_PIN_INVALID",
            facts=_facts(verified=False),
            evidence=None,
        )
    expected_unsigned_reopen = build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
        persistence_registration,
        checkpoint_asset,
        write_receipt,
        session_id=reopen_receipt.get("session_id"),
        reopened_at_utc=reopen_receipt.get("reopened_at_utc"),
    )
    rebuilt_reopen = assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
        expected_unsigned_reopen,
        reopen_receipt.get("signature_base64"),
    )
    if (
        type(rebuilt_reopen) is not dict
        or not strict_json_contract_equal(reopen_receipt, rebuilt_reopen)
        or not _signature_valid(
            reopen_receipt,
            persistence_provider_public_key_base64,
            persistence_registration["persistence_provider_public_key_sha256"],
        )
    ):
        return _result(
            status="UNKNOWN",
            reason="REOPEN_RECEIPT_EXACT_OR_SIGNATURE_INVALID",
            facts=_facts(verified=False),
            evidence=None,
        )
    evidence = {
        "asset_created_at_utc": checkpoint_asset["asset_created_at_utc"],
        "checkpoint_asset_hash": checkpoint_asset["asset_hash"],
        "persistence_registration_hash": persistence_registration[
            "registration_hash"
        ],
        "record_hash": write_receipt["record_hash"],
        "reopen_receipt_hash": reopen_receipt["reopen_receipt_hash"],
        "reopen_session_id": reopen_receipt["session_id"],
        "reopened_at_utc": reopen_receipt["reopened_at_utc"],
        "source_common_registry_view_hash": persistence_registration[
            "source_common_registry_view_hash"
        ],
        "source_preregistration_hash": persistence_registration[
            "source_preregistration_hash"
        ],
        "write_receipt_hash": write_receipt["write_receipt_hash"],
        "write_session_id": write_receipt["session_id"],
        "written_at_utc": write_receipt["written_at_utc"],
    }
    return _result(
        status="PASS",
        reason="PASS_SIGNED_WRITE_REOPEN_RECEIPTS",
        facts=_facts(verified=True),
        evidence=evidence,
    )


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
    document: Any,
    *args: Any,
    expected_verification_hash: Any,
    **kwargs: Any,
) -> bool:
    if (
        type(document) is not dict
        or not _exact_hash(expected_verification_hash)
        or document.get("verification_hash") != expected_verification_hash
    ):
        return False
    try:
        rebuilt = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
            *args,
            **kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, rebuilt)
        and compare_digest(
            document["verification_hash"],
            rebuilt["verification_hash"],
        )
    )


__all__ = [
    "EVALUATION_SCHEMA_VERSION",
    "PERSISTENCE_REGISTRATION_V1_IMPLEMENTATION_SHA256",
    "STATIC_FINGERPRINT",
    "VERIFICATION_STATE",
    "assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1",
    "assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1",
    "build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1",
    "build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1",
    "build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1",
]
