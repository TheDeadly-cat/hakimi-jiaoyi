from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from . import strategy_correlation_common_support_calendar_provider_composition_v1 as composition_source
from .execution_authority import authority_violations

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised by dependency-absence tests
    InvalidSignature = Exception  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-attestation-registration-v1"
)
ATTESTATION_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-attestation-receipt-v1"
)
SCHEMA_VERSION = "strategy-correlation-provider-dataset-content-attestation-verification-v1"
STATIC_FINGERPRINT = "20260822-strategy-correlation-provider-dataset-content-attestation-1"
KEY_ROLE = "PROVIDER_DATASET_CONTENT_ATTESTATION"
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "RFC8785_JCS_UTF8"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
ATTESTATION_SCOPE = "ALL_COMPOSED_DATASET_DATA_AND_MANIFEST_HASHES"
VERIFICATION_STATE = (
    "REGISTERED_PROVIDER_DATASET_KEY_SIGNATURE_VERIFIED_"
    "EXTERNAL_KEY_CONTROL_AND_DATA_ISSUANCE_TRUST_UNPROVEN"
)

_KEY_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,63}$")
_COMPOSITION_CONTEXT_KEYS = {
    "derivation_receipt",
    "matrix_replay",
    "calendar_session_verification",
    "calendar_verification_bundle",
    "provider_identity_verification",
    "provider_verification_bundle",
}
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _valid_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _decode_base64(value: Any, expected_length: int, label: str) -> bytes:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{label}_base64_invalid")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"{label}_base64_invalid") from error
    if (
        len(decoded) != expected_length
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        raise ValueError(f"{label}_base64_invalid")
    return decoded


def _utc(value: Any, label: str) -> datetime:
    if type(value) is not str or value != value.strip():
        raise ValueError(f"{label}_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise ValueError(f"{label}_invalid") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{label}_invalid")
    return parsed


def _composition_verified(document: Any, context: Any) -> bool:
    if type(context) is not dict or set(context) != _COMPOSITION_CONTEXT_KEYS:
        return False
    try:
        check = composition_source.verify_correlation_common_support_calendar_provider_composition_v1(
            document,
            context["derivation_receipt"],
            context["matrix_replay"],
            context["calendar_session_verification"],
            context["calendar_verification_bundle"],
            context["provider_identity_verification"],
            context["provider_verification_bundle"],
        )
    except (KeyError, MemoryError, RecursionError, TypeError, ValueError):
        return False
    return check["status"] == "PASS"


def _source_role_public_keys(composition_context: dict[str, Any]) -> tuple[bytes, bytes]:
    try:
        registry_key_base64 = composition_context["provider_verification_bundle"][
            "identity_assertion_receipt"
        ]["registry_public_key_base64"]
        timestamp_key_base64 = composition_context["calendar_verification_bundle"][
            "batch_verification_context"
        ]["signature_verification_context"]["attestation_receipt"][
            "public_key_base64"
        ]
    except (KeyError, TypeError) as error:
        raise ValueError("source_role_public_key_context_invalid") from error
    registry_key = _decode_base64(
        registry_key_base64,
        32,
        "identity_registry_public_key",
    )
    timestamp_key = _decode_base64(
        timestamp_key_base64,
        32,
        "timestamp_adapter_public_key",
    )
    if registry_key == timestamp_key:
        raise ValueError("source_role_public_key_collision")
    return registry_key, timestamp_key


def build_provider_dataset_content_attestation_registration_v1(
    composition_document: dict[str, Any],
    composition_context: dict[str, Any],
    *,
    provider_dataset_key_id: str,
    provider_dataset_public_key_base64: str,
    declared_at_utc: str,
    valid_from_utc: str,
    valid_until_utc: str,
) -> dict[str, Any]:
    if _authority_invalid([composition_document, composition_context]):
        raise ValueError("dataset_attestation_registration_authority_invalid")
    if not _composition_verified(composition_document, composition_context):
        raise ValueError("dataset_attestation_source_composition_invalid")
    if (
        composition_document.get("schema_version")
        != composition_source.SCHEMA_VERSION
        or composition_document.get("static_fingerprint")
        != composition_source.STATIC_FINGERPRINT
        or composition_document.get("status") != "PASS"
        or composition_document.get("facts", {}).get(
            "dataset_content_attested_by_provider"
        )
        is not False
    ):
        raise ValueError("dataset_attestation_source_contract_mismatch")
    if type(provider_dataset_key_id) is not str or not _KEY_ID_RE.fullmatch(
        provider_dataset_key_id
    ):
        raise ValueError("provider_dataset_key_id_invalid")
    dataset_key = _decode_base64(
        provider_dataset_public_key_base64,
        32,
        "provider_dataset_public_key",
    )
    registry_key, timestamp_key = _source_role_public_keys(composition_context)
    if dataset_key in {registry_key, timestamp_key}:
        raise ValueError("provider_dataset_key_role_collision")
    declared = _utc(declared_at_utc, "declared_at_utc")
    valid_from = _utc(valid_from_utc, "valid_from_utc")
    valid_until = _utc(valid_until_utc, "valid_until_utc")
    if not declared <= valid_from < valid_until:
        raise ValueError("provider_dataset_key_validity_window_invalid")

    dataset_key_hash = hashlib.sha256(dataset_key).hexdigest()
    registry_key_hash = hashlib.sha256(registry_key).hexdigest()
    timestamp_key_hash = hashlib.sha256(timestamp_key).hexdigest()
    key_binding = {
        "key_role": KEY_ROLE,
        "provider_dataset_key_id": provider_dataset_key_id,
        "provider_dataset_public_key_sha256": dataset_key_hash,
        "provider_id_hash": composition_document["provider_id_hash"],
        "source_provider_identity_verification_hash": composition_document[
            "source_provider_identity_verification_hash"
        ],
        "source_provider_identity_document_hash": composition_document[
            "source_provider_identity_document_hash"
        ],
    }
    facts = {
        "source_composition_verified": True,
        "provider_identity_lineage_bound": True,
        "provider_dataset_key_shape_verified": True,
        "source_role_keys_distinct": True,
        "provider_dataset_key_role_separation_verified": True,
        "external_provider_dataset_key_control_verified": False,
        "external_registration_time_verified": False,
        "provider_dataset_signing_allowed": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "provider_dataset_signing_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }
    body = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_state": (
            "PROVIDER_DATASET_KEY_REGISTERED_EXTERNAL_CONTROL_UNPROVEN"
        ),
        "source_composition_hash": composition_document["composition_hash"],
        "source_composition_schema": composition_source.SCHEMA_VERSION,
        "source_provider_identity_verification_hash": composition_document[
            "source_provider_identity_verification_hash"
        ],
        "source_provider_identity_document_hash": composition_document[
            "source_provider_identity_document_hash"
        ],
        "provider_id_hash": composition_document["provider_id_hash"],
        "dataset_count": composition_document["dataset_count"],
        "dataset_provider_binding_hash": composition_document[
            "dataset_provider_binding_hash"
        ],
        "key_role": KEY_ROLE,
        "provider_dataset_key_id": provider_dataset_key_id,
        "provider_dataset_public_key_sha256": dataset_key_hash,
        "provider_dataset_key_binding_hash": _sha256(key_binding),
        "identity_registry_public_key_sha256": registry_key_hash,
        "timestamp_adapter_public_key_sha256": timestamp_key_hash,
        "excluded_source_role_key_count": 2,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "declared_at_utc": declared_at_utc,
        "valid_from_utc": valid_from_utc,
        "valid_until_utc": valid_until_utc,
        "facts": facts,
        "authority": authority,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "registration_hash": _sha256(body)}


def verify_provider_dataset_content_attestation_registration_v1(
    document: Any,
    composition_document: Any,
    composition_context: Any,
    provider_dataset_public_key_base64: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    if (
        type(document) is not dict
        or _authority_invalid(document)
        or not _valid_sha256(expected_registration_hash)
        or document.get("registration_hash") != expected_registration_hash
    ):
        return False
    try:
        rebuilt = build_provider_dataset_content_attestation_registration_v1(
            composition_document,
            composition_context,
            provider_dataset_key_id=document["provider_dataset_key_id"],
            provider_dataset_public_key_base64=provider_dataset_public_key_base64,
            declared_at_utc=document["declared_at_utc"],
            valid_from_utc=document["valid_from_utc"],
            valid_until_utc=document["valid_until_utc"],
        )
    except (
        ArithmeticError,
        KeyError,
        MemoryError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        return False
    return document == rebuilt


_UNSIGNED_KEYS = {
    "schema_version",
    "static_fingerprint",
    "attestation_scope",
    "provider_dataset_key_id",
    "provider_id_hash",
    "registration_hash",
    "composition_hash",
    "matrix_replay_hash",
    "completed_price_input_hash",
    "common_support_matrix_hash",
    "dataset_count",
    "dataset_provider_binding_hash",
    "issued_at_utc",
    "valid_until_utc",
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "receipt_content_sha256",
}


def build_unsigned_provider_dataset_content_attestation_v1(
    registration: dict[str, Any],
    composition_document: dict[str, Any],
    *,
    issued_at_utc: str,
) -> dict[str, Any]:
    issued = _utc(issued_at_utc, "issued_at_utc")
    valid_from = _utc(registration.get("valid_from_utc"), "valid_from_utc")
    valid_until = _utc(registration.get("valid_until_utc"), "valid_until_utc")
    if not valid_from <= issued <= valid_until:
        raise ValueError("dataset_attestation_issued_time_invalid")
    if (
        registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or registration.get("source_composition_hash")
        != composition_document.get("composition_hash")
        or registration.get("provider_id_hash")
        != composition_document.get("provider_id_hash")
        or registration.get("dataset_count")
        != composition_document.get("dataset_count")
        or registration.get("dataset_provider_binding_hash")
        != composition_document.get("dataset_provider_binding_hash")
    ):
        raise ValueError("dataset_attestation_registration_source_mismatch")
    body = {
        "schema_version": ATTESTATION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "attestation_scope": ATTESTATION_SCOPE,
        "provider_dataset_key_id": registration["provider_dataset_key_id"],
        "provider_id_hash": composition_document["provider_id_hash"],
        "registration_hash": registration["registration_hash"],
        "composition_hash": composition_document["composition_hash"],
        "matrix_replay_hash": composition_document["source_matrix_replay_hash"],
        "completed_price_input_hash": composition_document[
            "source_completed_price_input_hash"
        ],
        "common_support_matrix_hash": composition_document[
            "source_common_support_matrix_hash"
        ],
        "dataset_count": composition_document["dataset_count"],
        "dataset_provider_binding_hash": composition_document[
            "dataset_provider_binding_hash"
        ],
        "issued_at_utc": issued_at_utc,
        "valid_until_utc": registration["valid_until_utc"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
    }
    return {**body, "receipt_content_sha256": _sha256(body)}


def assemble_provider_dataset_content_attestation_receipt_v1(
    unsigned_receipt: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    if type(unsigned_receipt) is not dict or set(unsigned_receipt) != _UNSIGNED_KEYS:
        raise ValueError("unsigned_dataset_attestation_contract_invalid")
    body = {
        key: value
        for key, value in unsigned_receipt.items()
        if key != "receipt_content_sha256"
    }
    if unsigned_receipt["receipt_content_sha256"] != _sha256(body):
        raise ValueError("unsigned_dataset_attestation_content_hash_invalid")
    signature = _decode_base64(signature_base64, 64, "dataset_attestation_signature")
    signature_sha256 = hashlib.sha256(signature).hexdigest()
    attestation_body = {
        **unsigned_receipt,
        "signature_sha256": signature_sha256,
    }
    return {
        **attestation_body,
        "signature_base64": signature_base64,
        "attestation_hash": _sha256(attestation_body),
    }


_RECEIPT_KEYS = _UNSIGNED_KEYS | {
    "signature_base64",
    "signature_sha256",
    "attestation_hash",
}


def evaluate_provider_dataset_content_attestation_v1(
    composition_document: dict[str, Any],
    composition_context: dict[str, Any],
    registration: dict[str, Any],
    provider_dataset_public_key_base64: str,
    attestation_receipt: dict[str, Any],
    *,
    expected_registration_hash: str,
    expected_attestation_hash: str,
) -> dict[str, Any]:
    if _authority_invalid([
        composition_document,
        composition_context,
        registration,
        attestation_receipt,
    ]):
        raise ValueError("dataset_attestation_authority_invalid")
    if not verify_provider_dataset_content_attestation_registration_v1(
        registration,
        composition_document,
        composition_context,
        provider_dataset_public_key_base64,
        expected_registration_hash=expected_registration_hash,
    ):
        raise ValueError("dataset_attestation_registration_invalid")
    if (
        type(attestation_receipt) is not dict
        or set(attestation_receipt) != _RECEIPT_KEYS
        or not _valid_sha256(expected_attestation_hash)
        or attestation_receipt.get("attestation_hash")
        != expected_attestation_hash
    ):
        raise ValueError("dataset_attestation_receipt_invalid")
    unsigned = build_unsigned_provider_dataset_content_attestation_v1(
        registration,
        composition_document,
        issued_at_utc=attestation_receipt["issued_at_utc"],
    )
    if any(attestation_receipt.get(key) != value for key, value in unsigned.items()):
        raise ValueError("dataset_attestation_source_binding_mismatch")
    assembled = assemble_provider_dataset_content_attestation_receipt_v1(
        unsigned,
        attestation_receipt["signature_base64"],
    )
    if attestation_receipt != assembled:
        raise ValueError("dataset_attestation_receipt_seal_invalid")
    public_key_raw = _decode_base64(
        provider_dataset_public_key_base64,
        32,
        "provider_dataset_public_key",
    )
    if (
        hashlib.sha256(public_key_raw).hexdigest()
        != registration["provider_dataset_public_key_sha256"]
        or Ed25519PublicKey is None
    ):
        raise ValueError("provider_dataset_public_key_invalid")
    signature = _decode_base64(
        attestation_receipt["signature_base64"],
        64,
        "dataset_attestation_signature",
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(
            signature,
            bytes.fromhex(attestation_receipt["receipt_content_sha256"]),
        )
    except (InvalidSignature, ValueError) as error:
        raise ValueError("dataset_attestation_signature_invalid") from error

    facts = {
        "source_composition_verified": True,
        "provider_dataset_key_registration_verified": True,
        "provider_dataset_key_role_separation_verified": True,
        "receipt_structure_verified": True,
        "receipt_content_hash_verified": True,
        "all_dataset_hashes_bound": True,
        "provider_dataset_signature_verified": True,
        "provider_dataset_content_claim_verified": True,
        "external_provider_dataset_key_control_verified": False,
        "external_provider_data_issuance_verified": False,
        "replay_registry_checked": False,
        "observation_admission_allowed": False,
        "profitability_verified": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "observation_admission_allowed": False,
        "provider_dataset_attestation_use_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source_state": "VERIFIED",
        "verification_state": VERIFICATION_STATE,
        "source_composition_hash": composition_document["composition_hash"],
        "source_registration_hash": registration["registration_hash"],
        "source_attestation_hash": attestation_receipt["attestation_hash"],
        "provider_id_hash": registration["provider_id_hash"],
        "provider_dataset_key_id": registration["provider_dataset_key_id"],
        "provider_dataset_public_key_sha256": registration[
            "provider_dataset_public_key_sha256"
        ],
        "dataset_count": registration["dataset_count"],
        "dataset_provider_binding_hash": registration[
            "dataset_provider_binding_hash"
        ],
        "receipt_content_sha256": attestation_receipt[
            "receipt_content_sha256"
        ],
        "signature_sha256": attestation_receipt["signature_sha256"],
        "issued_at_utc": attestation_receipt["issued_at_utc"],
        "valid_until_utc": attestation_receipt["valid_until_utc"],
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "facts": facts,
        "blockers": [
            "external_provider_dataset_key_control_unproven",
            "external_provider_data_issuance_unproven",
            "replay_registry_unchecked",
            "observation_admission_locked",
        ],
        "authority": authority,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "verification_hash": _sha256(body)}


def verify_provider_dataset_content_attestation_v1(
    document: Any,
    composition_document: Any,
    composition_context: Any,
    registration: Any,
    provider_dataset_public_key_base64: Any,
    attestation_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_attestation_hash: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = evaluate_provider_dataset_content_attestation_v1(
            composition_document,
            composition_context,
            registration,
            provider_dataset_public_key_base64,
            attestation_receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )
    except (
        ArithmeticError,
        KeyError,
        MemoryError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        return False
    return document == rebuilt


__all__ = [
    "ATTESTATION_RECEIPT_SCHEMA_VERSION",
    "ATTESTATION_SCOPE",
    "KEY_ROLE",
    "RECEIPT_ENCODING",
    "REGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_MESSAGE_FORMAT",
    "STATIC_FINGERPRINT",
    "VERIFICATION_STATE",
    "assemble_provider_dataset_content_attestation_receipt_v1",
    "build_provider_dataset_content_attestation_registration_v1",
    "build_unsigned_provider_dataset_content_attestation_v1",
    "evaluate_provider_dataset_content_attestation_v1",
    "verify_provider_dataset_content_attestation_registration_v1",
    "verify_provider_dataset_content_attestation_v1",
]
