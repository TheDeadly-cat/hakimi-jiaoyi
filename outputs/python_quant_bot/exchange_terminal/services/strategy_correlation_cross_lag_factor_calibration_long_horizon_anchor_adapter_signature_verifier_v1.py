from __future__ import annotations

import base64
import hashlib
import re
from datetime import date, datetime, timezone
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised through dependency patching
    InvalidSignature = ValueError
    Ed25519PublicKey = None

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import strict_sha256
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1 import (
    SCHEMA_VERSION as REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    EXTERNAL_ATTESTATION_SCHEMA,
)


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-"
    "anchor-adapter-signature-verification-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260919-cross-lag-factor-calibration-long-horizon-"
    "anchor-adapter-signature-verifier-1"
)
RECEIPT_STATIC_FINGERPRINT = (
    "20260919-cross-lag-factor-calibration-long-horizon-"
    "external-time-attestation-receipt-1"
)
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
POSITIVE_STATE = "SIGNATURE_VERIFIED_REPLAY_REGISTRY_UNCHECKED"

_ASCII_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UTC_SECOND = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_REGISTRATION_CONTEXT_KEYS = frozenset(
    {
        "adapter_id",
        "adapter_implementation_sha256",
        "adapter_static_fingerprint",
        "declared_at_utc",
        "expected_observation_protocol_hash",
        "expected_preregistration_hash",
        "provider_id",
        "receipt_encoding",
        "signature_algorithm",
        "trust_root_sha256",
    }
)
_SIGNED_RECEIPT_KEYS = frozenset(
    {
        "adapter_id",
        "adapter_static_fingerprint",
        "batch_first_observation_date",
        "batch_last_observation_date",
        "future_evaluation_id",
        "observation_batch_hash",
        "provider_id",
        "provider_receipt_id",
        "provider_timestamp_utc",
        "receipt_encoding",
        "registration_hash",
        "schema_version",
        "signature_algorithm",
        "signature_message_format",
        "source_external_time_anchor_reference_hash",
        "static_fingerprint",
        "trust_root_sha256",
    }
)
_RECEIPT_KEYS = _SIGNED_RECEIPT_KEYS | {
    "attestation_hash",
    "public_key_base64",
    "receipt_content_sha256",
    "signature_base64",
    "signature_sha256",
}


def _authority() -> dict[str, bool]:
    return {
        "adapter_use_allowed": False,
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "external_authenticity_proven": False,
        "external_registration_time_verified": False,
        "future_evaluation_allowed": False,
        "future_observation_collection_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
    }


def _facts(
    *,
    registration_verified: bool = False,
    receipt_structure_verified: bool = False,
    trust_root_key_match: bool = False,
    signature_verified: bool = False,
    receipt_time_claim_valid: bool = False,
) -> dict[str, bool]:
    return {
        "batch_content_verified": False,
        "batch_hash_bound": signature_verified,
        "external_authenticity_proven": False,
        "external_registration_time_verified": False,
        "observation_admitted": False,
        "provider_identity_verified": False,
        "provider_key_possession_verified": signature_verified,
        "receipt_signature_verified": signature_verified,
        "receipt_structure_verified": receipt_structure_verified,
        "receipt_time_claim_valid": receipt_time_claim_valid,
        "registration_verified": registration_verified,
        "replay_registry_checked": False,
        "result_available": False,
        "trust_root_key_match": trust_root_key_match,
    }


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


def _ascii_id(value: Any) -> bool:
    return type(value) is str and _ASCII_ID.fullmatch(value) is not None


def _strict_base64(value: Any, expected_length: int) -> bytes | None:
    if type(value) is not str:
        return None
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error):
        return None
    if len(decoded) != expected_length:
        return None
    if base64.b64encode(decoded).decode("ascii") != value:
        return None
    return decoded


def _safe_text(document: Any, key: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(key)
    return value if type(value) is str else None


def _source_state(registration: Any) -> str:
    if type(registration) is not dict:
        return "UNKNOWN"
    value = registration.get("source_state")
    return value if value in {"VERIFIED", "BLOCKED", "UNKNOWN"} else "UNKNOWN"


def _unknown(
    reason: str,
    registration: Any,
    receipt: Any,
    *,
    expected_registration_hash: Any = None,
    expected_attestation_hash: Any = None,
    registration_verified: bool = False,
    receipt_structure_verified: bool = False,
    trust_root_key_match: bool = False,
    receipt_time_claim_valid: bool = False,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "adapter_id": _safe_text(receipt, "adapter_id"),
        "adapter_static_fingerprint": _safe_text(
            receipt, "adapter_static_fingerprint"
        ),
        "attestation_hash": (
            expected_attestation_hash if strict_sha256(expected_attestation_hash) else None
        ),
        "authority": _authority(),
        "batch_first_observation_date": _safe_text(
            receipt, "batch_first_observation_date"
        ),
        "batch_last_observation_date": _safe_text(
            receipt, "batch_last_observation_date"
        ),
        "blockers": [reason],
        "facts": _facts(
            registration_verified=registration_verified,
            receipt_structure_verified=receipt_structure_verified,
            trust_root_key_match=trust_root_key_match,
            receipt_time_claim_valid=receipt_time_claim_valid,
        ),
        "future_evaluation_id": _safe_text(receipt, "future_evaluation_id"),
        "observation_batch_hash": _safe_text(receipt, "observation_batch_hash"),
        "provider_id": _safe_text(receipt, "provider_id"),
        "provider_receipt_id": _safe_text(receipt, "provider_receipt_id"),
        "provider_timestamp_utc": _safe_text(receipt, "provider_timestamp_utc"),
        "receipt_content_sha256": _safe_text(receipt, "receipt_content_sha256"),
        "receipt_schema_version": _safe_text(receipt, "schema_version"),
        "schema_version": SCHEMA_VERSION,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_sha256": _safe_text(receipt, "signature_sha256"),
        "source_external_time_anchor_reference_hash": _safe_text(
            receipt, "source_external_time_anchor_reference_hash"
        ),
        "source_registration_hash": (
            expected_registration_hash
            if strict_sha256(expected_registration_hash)
            else None
        ),
        "source_registration_schema": _safe_text(registration, "schema_version"),
        "source_state": _source_state(registration),
        "static_fingerprint": STATIC_FINGERPRINT,
        "trust_root_sha256": _safe_text(receipt, "trust_root_sha256"),
        "verification_state": "UNKNOWN",
    }
    return seal_strict_canonical_document(document, "verification_hash")


def evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
    registration_v1: Any,
    observation_protocol_v1: Any,
    long_horizon_preregistration_v1: Any,
    source_verification_context: Any,
    registration_verification_context: Any,
    attestation_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_attestation_hash: Any,
) -> dict[str, Any]:
    registration = registration_v1
    receipt = attestation_receipt
    if not strict_sha256(expected_registration_hash):
        return _unknown(
            "EXPECTED_REGISTRATION_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if not strict_sha256(expected_attestation_hash):
        return _unknown(
            "EXPECTED_ATTESTATION_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if type(registration) is not dict:
        return _unknown(
            "SOURCE_REGISTRATION_NOT_OBJECT",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if registration.get("registration_hash") != expected_registration_hash:
        return _unknown(
            "SOURCE_REGISTRATION_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        return _unknown(
            "SOURCE_REGISTRATION_SCHEMA_UNSUPPORTED",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if (
        type(registration_verification_context) is not dict
        or set(registration_verification_context) != _REGISTRATION_CONTEXT_KEYS
    ):
        return _unknown(
            "REGISTRATION_VERIFICATION_CONTEXT_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    try:
        registration_verified = (
            verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
                registration,
                observation_protocol_v1,
                long_horizon_preregistration_v1,
                source_verification_context,
                **dict(registration_verification_context),
            )
        )
    except Exception:
        registration_verified = False
    if not registration_verified:
        return _unknown(
            "SOURCE_REGISTRATION_NOT_VERIFIED",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    if (
        registration.get("source_state") != "VERIFIED"
        or registration.get("registration_state")
        != "DECLARED_NOT_EXTERNALLY_TIME_ATTESTED"
    ):
        return _unknown(
            "SOURCE_REGISTRATION_NOT_DECLARED",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if registration.get("signature_algorithm") != "ED25519":
        return _unknown(
            "REGISTERED_ALGORITHM_NOT_SUPPORTED_BY_ADAPTER",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if Ed25519PublicKey is None:
        return _unknown(
            "CRYPTOGRAPHY_DEPENDENCY_UNAVAILABLE",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if type(receipt) is not dict or set(receipt) != _RECEIPT_KEYS:
        return _unknown(
            "ATTESTATION_RECEIPT_FIELDS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if receipt.get("attestation_hash") != expected_attestation_hash:
        return _unknown(
            "ATTESTATION_HASH_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    try:
        sealed = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "attestation_hash"},
            "attestation_hash",
        )
    except (TypeError, ValueError):
        sealed = None
    if sealed is None or not strict_json_contract_equal(receipt, sealed):
        return _unknown(
            "ATTESTATION_SEAL_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if (
        receipt.get("schema_version") != EXTERNAL_ATTESTATION_SCHEMA
        or receipt.get("static_fingerprint") != RECEIPT_STATIC_FINGERPRINT
        or receipt.get("signature_message_format") != SIGNATURE_MESSAGE_FORMAT
    ):
        return _unknown(
            "ATTESTATION_IDENTITY_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if not _ascii_id(receipt.get("provider_receipt_id")):
        return _unknown(
            "PROVIDER_RECEIPT_ID_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if (
        receipt.get("registration_hash") != expected_registration_hash
        or receipt.get("adapter_id") != registration.get("adapter_id")
        or receipt.get("adapter_static_fingerprint")
        != registration.get("adapter_static_fingerprint")
        or receipt.get("provider_id") != registration.get("provider_id")
        or receipt.get("trust_root_sha256") != registration.get("trust_root_sha256")
        or receipt.get("signature_algorithm") != registration.get("signature_algorithm")
        or receipt.get("receipt_encoding") != registration.get("receipt_encoding")
        or receipt.get("future_evaluation_id")
        != registration.get("future_evaluation_id")
        or receipt.get("source_external_time_anchor_reference_hash")
        != registration.get("source_external_time_anchor_reference_hash")
    ):
        return _unknown(
            "ATTESTATION_SOURCE_BINDINGS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if not strict_sha256(receipt.get("observation_batch_hash")):
        return _unknown(
            "OBSERVATION_BATCH_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )

    first_date = _iso_date(receipt.get("batch_first_observation_date"))
    last_date = _iso_date(receipt.get("batch_last_observation_date"))
    evaluation_not_before = _iso_date(registration.get("evaluation_not_before_date"))
    provider_timestamp = _utc_second(receipt.get("provider_timestamp_utc"))
    declared_at = _utc_second(registration.get("declared_at_utc"))
    if (
        first_date is None
        or last_date is None
        or evaluation_not_before is None
        or provider_timestamp is None
        or declared_at is None
    ):
        return _unknown(
            "ATTESTATION_TIME_FIELDS_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if first_date < evaluation_not_before or last_date < first_date:
        return _unknown(
            "OBSERVATION_DATE_WINDOW_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )
    if provider_timestamp.date() < last_date or provider_timestamp < declared_at:
        return _unknown(
            "PROVIDER_TIMESTAMP_ORDER_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
        )

    signed_payload = {key: receipt[key] for key in _SIGNED_RECEIPT_KEYS}
    receipt_content_sha256 = strict_canonical_hash(signed_payload)
    if receipt.get("receipt_content_sha256") != receipt_content_sha256:
        return _unknown(
            "RECEIPT_CONTENT_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
            receipt_structure_verified=True,
            receipt_time_claim_valid=True,
        )
    public_key = _strict_base64(receipt.get("public_key_base64"), 32)
    signature = _strict_base64(receipt.get("signature_base64"), 64)
    if public_key is None or signature is None:
        return _unknown(
            "ATTESTATION_CRYPTO_ENCODING_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
            receipt_structure_verified=True,
            receipt_time_claim_valid=True,
        )
    if hashlib.sha256(public_key).hexdigest() != registration.get(
        "trust_root_sha256"
    ):
        return _unknown(
            "PUBLIC_KEY_TRUST_ROOT_MISMATCH",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
            receipt_structure_verified=True,
            receipt_time_claim_valid=True,
        )
    if hashlib.sha256(signature).hexdigest() != receipt.get("signature_sha256"):
        return _unknown(
            "SIGNATURE_HASH_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
            receipt_structure_verified=True,
            trust_root_key_match=True,
            receipt_time_claim_valid=True,
        )
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            bytes.fromhex(receipt_content_sha256),
        )
    except (InvalidSignature, ValueError):
        return _unknown(
            "ATTESTATION_SIGNATURE_INVALID",
            registration,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
            registration_verified=True,
            receipt_structure_verified=True,
            trust_root_key_match=True,
            receipt_time_claim_valid=True,
        )

    document: dict[str, Any] = {
        "adapter_id": receipt.get("adapter_id"),
        "adapter_static_fingerprint": receipt.get("adapter_static_fingerprint"),
        "attestation_hash": expected_attestation_hash,
        "authority": _authority(),
        "batch_first_observation_date": receipt.get("batch_first_observation_date"),
        "batch_last_observation_date": receipt.get("batch_last_observation_date"),
        "blockers": [
            "REPLAY_REGISTRY_NOT_CHECKED",
            "OBSERVATION_BATCH_CONTENT_NOT_VERIFIED",
            "PROVIDER_IDENTITY_NOT_EXTERNALLY_ESTABLISHED",
            "REGISTRATION_TIME_NOT_EXTERNALLY_ATTESTED",
        ],
        "facts": _facts(
            registration_verified=True,
            receipt_structure_verified=True,
            trust_root_key_match=True,
            signature_verified=True,
            receipt_time_claim_valid=True,
        ),
        "future_evaluation_id": receipt.get("future_evaluation_id"),
        "observation_batch_hash": receipt.get("observation_batch_hash"),
        "provider_id": receipt.get("provider_id"),
        "provider_receipt_id": receipt.get("provider_receipt_id"),
        "provider_timestamp_utc": receipt.get("provider_timestamp_utc"),
        "receipt_content_sha256": receipt_content_sha256,
        "receipt_schema_version": EXTERNAL_ATTESTATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_sha256": receipt.get("signature_sha256"),
        "source_external_time_anchor_reference_hash": receipt.get(
            "source_external_time_anchor_reference_hash"
        ),
        "source_registration_hash": expected_registration_hash,
        "source_registration_schema": REGISTRATION_SCHEMA_VERSION,
        "source_state": "VERIFIED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "trust_root_sha256": receipt.get("trust_root_sha256"),
        "verification_state": POSITIVE_STATE,
    }
    return seal_strict_canonical_document(document, "verification_hash")


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
    document: Any,
    *args: Any,
    **expected: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        rebuilt = evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
            *args,
            **expected,
        )
        return strict_json_contract_equal(document, rebuilt)
    except Exception:
        return False
