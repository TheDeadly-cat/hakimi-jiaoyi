from __future__ import annotations

import base64
import hashlib
import re
from datetime import date, datetime, time, timezone
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - dependency failure is tested by patching
    InvalidSignature = ValueError
    Ed25519PublicKey = None

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1 import (
    IDENTITY_ATTESTATION_RECEIPT_ENCODING,
    IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM,
    REGISTRATION_STATE as SOURCE_REGISTRATION_STATE,
    SCHEMA_VERSION as SOURCE_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1,
)


ASSERTION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-assertion-receipt-candidate-v1"
)
RECEIPT_STATIC_FINGERPRINT = (
    "20260924-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-assertion-receipt-1"
)
SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-assertion-verification-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260924-cross-lag-factor-calibration-long-horizon-"
    "provider-identity-assertion-verifier-1"
)
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
MERKLE_HASH_FORMAT = "SHA256_DOMAIN_SEPARATED_POWER_OF_TWO_V1"
POSITIVE_STATE = (
    "IDENTITY_ASSERTION_SIGNATURE_AND_MEMBERSHIP_VERIFIED_"
    "EXTERNAL_TRUST_UNPROVEN"
)

VERIFIED_BLOCKERS = (
    "IDENTITY_REGISTRY_TRUST_ROOT_NOT_EXTERNALLY_ATTESTED",
    "IDENTITY_ASSERTION_REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
    "IDENTITY_ASSERTION_REPLAY_REGISTRY_NOT_CHECKED",
    "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
    "LONG_HORIZON_EVALUATION_NOT_ACTIVATED",
)

_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_REGISTRATION_CONTEXT_KEYS = frozenset(
    {
        "anchor_adapter_registration_v1",
        "anchor_registration_verification_context",
        "long_horizon_preregistration_v1",
        "observation_protocol_v1",
        "provider_identity_registration_values",
        "source_verification_context",
    }
)
_REGISTRATION_VALUE_KEYS = frozenset(
    {
        "declared_at_utc",
        "expected_anchor_registration_hash",
        "identity_adapter_id",
        "identity_adapter_implementation_sha256",
        "identity_adapter_static_fingerprint",
        "identity_attestation_receipt_encoding",
        "identity_attestation_signature_algorithm",
        "identity_registry_id",
        "identity_registry_snapshot_id",
        "identity_registry_snapshot_sha256",
        "identity_registry_trust_root_sha256",
        "provider_identity_document_sha256",
        "provider_subject_id",
    }
)
_SIGNED_RECEIPT_KEYS = frozenset(
    {
        "asserted_at_utc",
        "future_evaluation_id",
        "identity_adapter_id",
        "identity_assertion_id",
        "identity_registry_id",
        "identity_registry_snapshot_id",
        "identity_registry_snapshot_sha256",
        "identity_registry_trust_root_sha256",
        "membership_leaf_index",
        "membership_proof",
        "membership_tree_size",
        "merkle_hash_format",
        "provider_id",
        "provider_identity_document_sha256",
        "provider_identity_registration_hash",
        "provider_receipt_trust_root_sha256",
        "provider_subject_id",
        "receipt_encoding",
        "schema_version",
        "signature_algorithm",
        "signature_message_format",
        "static_fingerprint",
        "valid_until_utc",
    }
)
_RECEIPT_KEYS = _SIGNED_RECEIPT_KEYS | {
    "assertion_content_sha256",
    "assertion_hash",
    "registry_public_key_base64",
    "registry_signature_base64",
    "registry_signature_sha256",
}
_PROOF_ENTRY_KEYS = frozenset({"direction", "sibling_sha256"})


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_provider_identity_verified": False,
        "future_evaluation_allowed": False,
        "identity_assertion_use_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "provider_identity_admission_allowed": False,
    }


def _facts(
    *,
    registration_verified: bool = False,
    receipt_seal_verified: bool = False,
    source_bindings_verified: bool = False,
    chronology_claim_valid: bool = False,
    content_hash_verified: bool = False,
    registry_key_match: bool = False,
    registry_signature_verified: bool = False,
    membership_verified: bool = False,
) -> dict[str, bool]:
    return {
        "assertion_chronology_claim_valid": chronology_claim_valid,
        "assertion_content_hash_verified": content_hash_verified,
        "assertion_receipt_seal_verified": receipt_seal_verified,
        "evaluation_activated": False,
        "external_identity_registry_authenticity_proven": False,
        "external_registration_time_verified": False,
        "identity_registry_key_match": registry_key_match,
        "identity_registry_signature_verified": registry_signature_verified,
        "provider_identity_verified": False,
        "replay_registry_checked": False,
        "result_available": False,
        "snapshot_membership_verified": membership_verified,
        "source_bindings_verified": source_bindings_verified,
        "source_registration_verified": registration_verified,
    }


def _ascii_id(value: Any) -> bool:
    return type(value) is str and _ASCII_ID.fullmatch(value) is not None


def _utc_second(value: Any) -> datetime | None:
    if type(value) is not str or _UTC_SECOND.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    return parsed if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value else None


def _iso_date(value: Any) -> date | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _safe_count(document: Any, key: str) -> int | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is int and type(value) is not bool and value >= 0 else None


def _strict_base64(value: Any, expected_length: int) -> bytes | None:
    if type(value) is not str:
        return None
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        return None
    if len(decoded) != expected_length:
        return None
    return decoded if base64.b64encode(decoded).decode("ascii") == value else None


def _merkle_leaf(document_sha256: str) -> str:
    return hashlib.sha256(b"\x00" + bytes.fromhex(document_sha256)).hexdigest()


def _merkle_parent(left_sha256: str, right_sha256: str) -> str:
    return hashlib.sha256(
        b"\x01" + bytes.fromhex(left_sha256) + bytes.fromhex(right_sha256)
    ).hexdigest()


def _proof_hash(receipt: Any) -> str | None:
    if type(receipt) is not dict or type(receipt.get("membership_proof")) is not list:
        return None
    try:
        return strict_canonical_hash(receipt["membership_proof"])
    except (TypeError, ValueError):
        return None


def _source_state(registration: Any) -> str:
    value = _safe_text(registration, "source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _unknown(
    reason: str,
    registration: Any,
    receipt: Any,
    *,
    expected_registration_hash: Any = None,
    expected_assertion_hash: Any = None,
    registration_verified: bool = False,
    receipt_seal_verified: bool = False,
    source_bindings_verified: bool = False,
    chronology_claim_valid: bool = False,
    content_hash_verified: bool = False,
    registry_key_match: bool = False,
    registry_signature_verified: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "asserted_at_utc": _safe_text(receipt, "asserted_at_utc"),
        "assertion_content_sha256": _safe_text(
            receipt, "assertion_content_sha256"
        ),
        "assertion_hash": (
            expected_assertion_hash if strict_sha256(expected_assertion_hash) else None
        ),
        "assertion_id": _safe_text(receipt, "identity_assertion_id"),
        "authority": _authority(),
        "blockers": [reason],
        "facts": _facts(
            registration_verified=registration_verified,
            receipt_seal_verified=receipt_seal_verified,
            source_bindings_verified=source_bindings_verified,
            chronology_claim_valid=chronology_claim_valid,
            content_hash_verified=content_hash_verified,
            registry_key_match=registry_key_match,
            registry_signature_verified=registry_signature_verified,
        ),
        "future_evaluation_id": _safe_text(receipt, "future_evaluation_id"),
        "identity_adapter_id": _safe_text(receipt, "identity_adapter_id"),
        "identity_assertion_verification_state": "UNKNOWN",
        "identity_registry_id": _safe_text(receipt, "identity_registry_id"),
        "identity_registry_snapshot_id": _safe_text(
            receipt, "identity_registry_snapshot_id"
        ),
        "identity_registry_snapshot_sha256": _safe_text(
            receipt, "identity_registry_snapshot_sha256"
        ),
        "identity_registry_trust_root_sha256": _safe_text(
            receipt, "identity_registry_trust_root_sha256"
        ),
        "membership_leaf_index": _safe_count(receipt, "membership_leaf_index"),
        "membership_proof_count": (
            len(receipt["membership_proof"])
            if type(receipt) is dict and type(receipt.get("membership_proof")) is list
            else None
        ),
        "membership_proof_hash": _proof_hash(receipt),
        "membership_tree_size": _safe_count(receipt, "membership_tree_size"),
        "merkle_hash_format": _safe_text(receipt, "merkle_hash_format"),
        "provider_id": _safe_text(receipt, "provider_id"),
        "provider_identity_document_sha256": _safe_text(
            receipt, "provider_identity_document_sha256"
        ),
        "provider_receipt_trust_root_sha256": _safe_text(
            receipt, "provider_receipt_trust_root_sha256"
        ),
        "provider_subject_id": _safe_text(receipt, "provider_subject_id"),
        "receipt_encoding": _safe_text(receipt, "receipt_encoding"),
        "registry_signature_sha256": _safe_text(
            receipt, "registry_signature_sha256"
        ),
        "schema_version": SCHEMA_VERSION,
        "signature_algorithm": _safe_text(receipt, "signature_algorithm"),
        "signature_message_format": _safe_text(
            receipt, "signature_message_format"
        ),
        "source_provider_identity_registration_hash": (
            expected_registration_hash
            if strict_sha256(expected_registration_hash)
            else None
        ),
        "source_provider_identity_registration_schema": _safe_text(
            registration, "schema_version"
        ),
        "source_state": _source_state(registration),
        "static_fingerprint": STATIC_FINGERPRINT,
        "valid_until_utc": _safe_text(receipt, "valid_until_utc"),
        "verification_reason": reason,
    }
    return seal_strict_canonical_document(document, "verification_hash")


def evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
    provider_identity_registration_v1: Any,
    provider_identity_registration_verification_context: Any,
    identity_assertion_receipt: Any,
    *,
    expected_provider_identity_registration_hash: Any,
    expected_identity_assertion_hash: Any,
) -> dict[str, Any]:
    registration = provider_identity_registration_v1
    receipt = identity_assertion_receipt
    if not strict_sha256(expected_provider_identity_registration_hash):
        return _unknown(
            "EXPECTED_PROVIDER_IDENTITY_REGISTRATION_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    if not strict_sha256(expected_identity_assertion_hash):
        return _unknown(
            "EXPECTED_IDENTITY_ASSERTION_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    if (
        type(registration) is not dict
        or registration.get("registration_hash")
        != expected_provider_identity_registration_hash
    ):
        return _unknown(
            "SOURCE_PROVIDER_IDENTITY_REGISTRATION_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    if registration.get("schema_version") != SOURCE_REGISTRATION_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_PROVIDER_IDENTITY_REGISTRATION_SCHEMA_UNSUPPORTED",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    context = provider_identity_registration_verification_context
    if type(context) is not dict or set(context) != _REGISTRATION_CONTEXT_KEYS:
        return _unknown(
            "PROVIDER_IDENTITY_REGISTRATION_VERIFICATION_CONTEXT_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    registration_values = context.get("provider_identity_registration_values")
    if (
        type(registration_values) is not dict
        or set(registration_values) != _REGISTRATION_VALUE_KEYS
    ):
        return _unknown(
            "PROVIDER_IDENTITY_REGISTRATION_VALUES_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    try:
        registration_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
                registration,
                context["anchor_adapter_registration_v1"],
                context["observation_protocol_v1"],
                context["long_horizon_preregistration_v1"],
                context["source_verification_context"],
                context["anchor_registration_verification_context"],
                **registration_values,
            )
        )
    except Exception:
        registration_verified = False
    if not registration_verified:
        return _unknown(
            "SOURCE_PROVIDER_IDENTITY_REGISTRATION_NOT_VERIFIED",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
        )
    if (
        registration.get("registration_state") != SOURCE_REGISTRATION_STATE
        or registration.get("source_state") != "VERIFIED"
        or registration.get("facts", {}).get("provider_identity_verified") is not False
    ):
        return _unknown(
            "SOURCE_PROVIDER_IDENTITY_REGISTRATION_STATE_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
        )
    if type(receipt) is not dict or set(receipt) != _RECEIPT_KEYS:
        return _unknown(
            "IDENTITY_ASSERTION_RECEIPT_FIELDS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
        )
    if receipt.get("assertion_hash") != expected_identity_assertion_hash:
        return _unknown(
            "IDENTITY_ASSERTION_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
        )
    try:
        sealed = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "assertion_hash"},
            "assertion_hash",
        )
    except (TypeError, ValueError):
        sealed = None
    if sealed is None or not strict_json_contract_equal(receipt, sealed):
        return _unknown(
            "IDENTITY_ASSERTION_RECEIPT_SEAL_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
        )
    if (
        receipt.get("schema_version") != ASSERTION_RECEIPT_SCHEMA_VERSION
        or receipt.get("static_fingerprint") != RECEIPT_STATIC_FINGERPRINT
        or receipt.get("signature_algorithm")
        != IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM
        or receipt.get("receipt_encoding") != IDENTITY_ATTESTATION_RECEIPT_ENCODING
        or receipt.get("signature_message_format") != SIGNATURE_MESSAGE_FORMAT
        or receipt.get("merkle_hash_format") != MERKLE_HASH_FORMAT
    ):
        return _unknown(
            "IDENTITY_ASSERTION_RECEIPT_IDENTITY_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
        )

    source_bindings = {
        "future_evaluation_id": "future_evaluation_id",
        "identity_adapter_id": "identity_adapter_id",
        "identity_registry_id": "identity_registry_id",
        "identity_registry_snapshot_id": "identity_registry_snapshot_id",
        "identity_registry_snapshot_sha256": "identity_registry_snapshot_sha256",
        "identity_registry_trust_root_sha256": "identity_registry_trust_root_sha256",
        "provider_id": "provider_id",
        "provider_identity_document_sha256": "provider_identity_document_sha256",
        "provider_receipt_trust_root_sha256": "provider_receipt_trust_root_sha256",
        "provider_subject_id": "provider_subject_id",
    }
    if receipt.get("provider_identity_registration_hash") != expected_provider_identity_registration_hash or any(
        receipt.get(receipt_key) != registration.get(registration_key)
        for receipt_key, registration_key in source_bindings.items()
    ):
        return _unknown(
            "IDENTITY_ASSERTION_SOURCE_BINDINGS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
        )
    if not _ascii_id(receipt.get("identity_assertion_id")):
        return _unknown(
            "IDENTITY_ASSERTION_ID_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
        )

    asserted_at = _utc_second(receipt.get("asserted_at_utc"))
    valid_until = _utc_second(receipt.get("valid_until_utc"))
    registered_at = _utc_second(registration.get("declared_at_utc"))
    evaluation_date = _iso_date(registration.get("evaluation_not_before_date"))
    evaluation_at = (
        datetime.combine(evaluation_date, time.min, tzinfo=timezone.utc)
        if evaluation_date is not None
        else None
    )
    if (
        asserted_at is None
        or valid_until is None
        or registered_at is None
        or evaluation_at is None
    ):
        return _unknown(
            "IDENTITY_ASSERTION_TIME_FIELDS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
        )
    if (
        asserted_at < registered_at
        or asserted_at >= evaluation_at
        or valid_until <= asserted_at
        or valid_until < evaluation_at
    ):
        return _unknown(
            "IDENTITY_ASSERTION_CHRONOLOGY_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
        )

    tree_size = receipt.get("membership_tree_size")
    leaf_index = receipt.get("membership_leaf_index")
    proof = receipt.get("membership_proof")
    if (
        type(tree_size) is not int
        or type(tree_size) is bool
        or tree_size < 1
        or tree_size > 1_048_576
        or tree_size & (tree_size - 1)
        or type(leaf_index) is not int
        or type(leaf_index) is bool
        or leaf_index < 0
        or leaf_index >= tree_size
        or type(proof) is not list
        or len(proof) != tree_size.bit_length() - 1
    ):
        return _unknown(
            "IDENTITY_ASSERTION_MERKLE_TREE_SHAPE_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
        )
    for level, entry in enumerate(proof):
        expected_direction = "LEFT" if ((leaf_index >> level) & 1) else "RIGHT"
        if (
            type(entry) is not dict
            or set(entry) != _PROOF_ENTRY_KEYS
            or entry.get("direction") != expected_direction
            or not strict_sha256(entry.get("sibling_sha256"))
        ):
            return _unknown(
                "IDENTITY_ASSERTION_MERKLE_PROOF_INVALID",
                registration,
                receipt,
                expected_registration_hash=expected_provider_identity_registration_hash,
                expected_assertion_hash=expected_identity_assertion_hash,
                registration_verified=True,
                receipt_seal_verified=True,
                source_bindings_verified=True,
                chronology_claim_valid=True,
            )

    content_hash = receipt.get("assertion_content_sha256")
    signature_hash = receipt.get("registry_signature_sha256")
    if not strict_sha256(content_hash) or not strict_sha256(signature_hash):
        return _unknown(
            "IDENTITY_ASSERTION_CRYPTO_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
        )
    signed_payload = {key: receipt[key] for key in _SIGNED_RECEIPT_KEYS}
    if strict_canonical_hash(signed_payload) != content_hash:
        return _unknown(
            "IDENTITY_ASSERTION_CONTENT_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
        )
    public_key_bytes = _strict_base64(receipt.get("registry_public_key_base64"), 32)
    signature_bytes = _strict_base64(receipt.get("registry_signature_base64"), 64)
    if public_key_bytes is None or signature_bytes is None:
        return _unknown(
            "IDENTITY_ASSERTION_CRYPTO_ENCODING_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
        )
    if hashlib.sha256(public_key_bytes).hexdigest() != registration.get(
        "identity_registry_trust_root_sha256"
    ):
        return _unknown(
            "IDENTITY_REGISTRY_PUBLIC_KEY_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
        )
    if hashlib.sha256(signature_bytes).hexdigest() != signature_hash:
        return _unknown(
            "IDENTITY_ASSERTION_SIGNATURE_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
            registry_key_match=True,
        )
    if Ed25519PublicKey is None:
        return _unknown(
            "CRYPTOGRAPHY_DEPENDENCY_UNAVAILABLE",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
            registry_key_match=True,
        )
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            signature_bytes, bytes.fromhex(content_hash)
        )
    except (InvalidSignature, ValueError, TypeError):
        return _unknown(
            "IDENTITY_ASSERTION_SIGNATURE_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
            registry_key_match=True,
        )

    current_hash = _merkle_leaf(receipt["provider_identity_document_sha256"])
    for entry in proof:
        sibling = entry["sibling_sha256"]
        current_hash = (
            _merkle_parent(sibling, current_hash)
            if entry["direction"] == "LEFT"
            else _merkle_parent(current_hash, sibling)
        )
    if current_hash != registration.get("identity_registry_snapshot_sha256"):
        return _unknown(
            "IDENTITY_ASSERTION_SNAPSHOT_MEMBERSHIP_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_provider_identity_registration_hash,
            expected_assertion_hash=expected_identity_assertion_hash,
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
            registry_key_match=True,
            registry_signature_verified=True,
        )

    document: dict[str, Any] = {
        "asserted_at_utc": receipt["asserted_at_utc"],
        "assertion_content_sha256": content_hash,
        "assertion_hash": expected_identity_assertion_hash,
        "assertion_id": receipt["identity_assertion_id"],
        "authority": _authority(),
        "blockers": list(VERIFIED_BLOCKERS),
        "facts": _facts(
            registration_verified=True,
            receipt_seal_verified=True,
            source_bindings_verified=True,
            chronology_claim_valid=True,
            content_hash_verified=True,
            registry_key_match=True,
            registry_signature_verified=True,
            membership_verified=True,
        ),
        "future_evaluation_id": receipt["future_evaluation_id"],
        "identity_adapter_id": receipt["identity_adapter_id"],
        "identity_assertion_verification_state": POSITIVE_STATE,
        "identity_registry_id": receipt["identity_registry_id"],
        "identity_registry_snapshot_id": receipt["identity_registry_snapshot_id"],
        "identity_registry_snapshot_sha256": receipt[
            "identity_registry_snapshot_sha256"
        ],
        "identity_registry_trust_root_sha256": receipt[
            "identity_registry_trust_root_sha256"
        ],
        "membership_leaf_index": leaf_index,
        "membership_proof_count": len(proof),
        "membership_proof_hash": strict_canonical_hash(proof),
        "membership_tree_size": tree_size,
        "merkle_hash_format": MERKLE_HASH_FORMAT,
        "provider_id": receipt["provider_id"],
        "provider_identity_document_sha256": receipt[
            "provider_identity_document_sha256"
        ],
        "provider_receipt_trust_root_sha256": receipt[
            "provider_receipt_trust_root_sha256"
        ],
        "provider_subject_id": receipt["provider_subject_id"],
        "receipt_encoding": IDENTITY_ATTESTATION_RECEIPT_ENCODING,
        "registry_signature_sha256": signature_hash,
        "schema_version": SCHEMA_VERSION,
        "signature_algorithm": IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "source_provider_identity_registration_hash": (
            expected_provider_identity_registration_hash
        ),
        "source_provider_identity_registration_schema": (
            SOURCE_REGISTRATION_SCHEMA_VERSION
        ),
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "valid_until_utc": receipt["valid_until_utc"],
        "verification_reason": (
            "IDENTITY_ASSERTION_CRYPTOGRAPHICALLY_VERIFIED_"
            "EXTERNAL_REGISTRY_TRUST_UNPROVEN"
        ),
    }
    return seal_strict_canonical_document(document, "verification_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
    document: Any,
    provider_identity_registration_v1: Any,
    provider_identity_registration_verification_context: Any,
    identity_assertion_receipt: Any,
    *,
    expected_provider_identity_registration_hash: Any,
    expected_identity_assertion_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
            provider_identity_registration_v1,
            provider_identity_registration_verification_context,
            identity_assertion_receipt,
            expected_provider_identity_registration_hash=(
                expected_provider_identity_registration_hash
            ),
            expected_identity_assertion_hash=expected_identity_assertion_hash,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, rebuilt)
