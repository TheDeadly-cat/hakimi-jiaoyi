from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from . import strategy_correlation_provider_dataset_content_attestation_v1 as attestation_source
from .execution_authority import authority_violations

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised by dependency-absence tests
    InvalidSignature = Exception  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-registration-v1"
)
GOVERNANCE_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-governance-receipt-v1"
)
SCHEMA_VERSION = "strategy-correlation-provider-dataset-key-lifecycle-gate-v1"
STATIC_FINGERPRINT = "20260822-strategy-correlation-provider-dataset-key-lifecycle-gate-1"
GOVERNANCE_KEY_ROLE = "PROVIDER_DATASET_KEY_LIFECYCLE_GOVERNANCE"
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "RFC8785_JCS_UTF8"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
SIGNATURE_DOMAIN = "hakimi.strategy-correlation.provider-dataset-key-lifecycle.v1"
LIFECYCLE_SCOPE = (
    "DATASET_KEY_PROVIDER_BINDING_CUSTODY_ROTATION_AND_REVOCATION_STATUS"
)
GENESIS_COMMITMENT = "GENESIS"
VERIFICATION_STATE = (
    "SIGNED_DATASET_KEY_BINDING_NONREVOCATION_AND_CUSTODY_CLAIMS_VERIFIED_"
    "EXTERNAL_GOVERNANCE_TRUST_UNPROVEN"
)

_MAX_EPOCH = 1_000_000
_MAX_FRESHNESS_SECONDS = 366 * 24 * 60 * 60
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,95}$")
_ATTESTATION_CONTEXT_KEYS = {
    "composition_document",
    "composition_context",
    "registration",
    "provider_dataset_public_key_base64",
    "attestation_receipt",
    "expected_registration_hash",
    "expected_attestation_hash",
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


def _strict_id(value: Any) -> bool:
    return type(value) is str and _ID_RE.fullmatch(value) is not None


def _strict_bool(value: Any) -> bool:
    return type(value) is bool


def _strict_epoch(value: Any) -> bool:
    return type(value) is int and 0 <= value <= _MAX_EPOCH


def _strict_freshness_seconds(value: Any) -> bool:
    return type(value) is int and 1 <= value <= _MAX_FRESHNESS_SECONDS


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


def _attestation_verified(document: Any, context: Any) -> bool:
    if type(context) is not dict or set(context) != _ATTESTATION_CONTEXT_KEYS:
        return False
    try:
        return attestation_source.verify_provider_dataset_content_attestation_v1(
            document,
            context["composition_document"],
            context["composition_context"],
            context["registration"],
            context["provider_dataset_public_key_base64"],
            context["attestation_receipt"],
            expected_registration_hash=context["expected_registration_hash"],
            expected_attestation_hash=context["expected_attestation_hash"],
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


def _source_contract(
    attestation_document: Any,
    attestation_context: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _attestation_verified(attestation_document, attestation_context):
        raise ValueError("dataset_key_lifecycle_source_attestation_invalid")
    if (
        type(attestation_document) is not dict
        or attestation_document.get("schema_version") != attestation_source.SCHEMA_VERSION
        or attestation_document.get("static_fingerprint")
        != attestation_source.STATIC_FINGERPRINT
        or attestation_document.get("source_state") != "VERIFIED"
        or attestation_document.get("verification_state")
        != attestation_source.VERIFICATION_STATE
        or attestation_document.get("permissions") != _PERMISSIONS
        or attestation_document.get("current_writer_activation_allowed") is not False
        or attestation_document.get("current_admission_allowed") is not False
    ):
        raise ValueError("dataset_key_lifecycle_source_contract_mismatch")
    source_registration = attestation_context.get("registration")
    source_receipt = attestation_context.get("attestation_receipt")
    if (
        type(source_registration) is not dict
        or type(source_receipt) is not dict
        or source_registration.get("schema_version")
        != attestation_source.REGISTRATION_SCHEMA_VERSION
        or source_receipt.get("schema_version")
        != attestation_source.ATTESTATION_RECEIPT_SCHEMA_VERSION
        or source_registration.get("registration_hash")
        != attestation_document.get("source_registration_hash")
        or source_receipt.get("attestation_hash")
        != attestation_document.get("source_attestation_hash")
        or source_registration.get("provider_dataset_key_id")
        != attestation_document.get("provider_dataset_key_id")
        or source_registration.get("provider_dataset_public_key_sha256")
        != attestation_document.get("provider_dataset_public_key_sha256")
    ):
        raise ValueError("dataset_key_lifecycle_source_lineage_mismatch")
    return source_registration, source_receipt


def build_provider_dataset_key_lifecycle_registration_v1(
    attestation_document: dict[str, Any],
    attestation_context: dict[str, Any],
    *,
    governance_key_id: str,
    governance_public_key_base64: str,
    key_epoch: int,
    previous_provider_dataset_key_id: str,
    previous_provider_dataset_key_commitment: str,
    rotation_policy_id: str,
    rotation_policy_hash: str,
    revocation_registry_id: str,
    custody_policy_id: str,
    custody_policy_hash: str,
    declared_at_utc: str,
    max_receipt_age_seconds: int,
    max_revocation_snapshot_age_seconds: int,
    max_receipt_issue_delay_seconds: int,
) -> dict[str, Any]:
    if _authority_invalid([attestation_document, attestation_context]):
        raise ValueError("dataset_key_lifecycle_registration_authority_invalid")
    source_registration, source_receipt = _source_contract(
        attestation_document,
        attestation_context,
    )
    if not _strict_id(governance_key_id):
        raise ValueError("governance_key_id_invalid")
    if governance_key_id == source_registration["provider_dataset_key_id"]:
        raise ValueError("governance_key_id_role_collision")
    governance_key = _decode_base64(
        governance_public_key_base64,
        32,
        "governance_public_key",
    )
    governance_key_hash = hashlib.sha256(governance_key).hexdigest()
    excluded_key_hashes = {
        source_registration.get("provider_dataset_public_key_sha256"),
        source_registration.get("identity_registry_public_key_sha256"),
        source_registration.get("timestamp_adapter_public_key_sha256"),
    }
    if not all(_valid_sha256(value) for value in excluded_key_hashes):
        raise ValueError("source_role_key_hash_invalid")
    if governance_key_hash in excluded_key_hashes:
        raise ValueError("governance_key_role_collision")
    if not _strict_epoch(key_epoch):
        raise ValueError("provider_dataset_key_epoch_invalid")
    if key_epoch == 0:
        if (
            previous_provider_dataset_key_id != GENESIS_COMMITMENT
            or previous_provider_dataset_key_commitment != GENESIS_COMMITMENT
        ):
            raise ValueError("provider_dataset_key_genesis_commitment_invalid")
    elif (
        not _strict_id(previous_provider_dataset_key_id)
        or previous_provider_dataset_key_id
        in {
            source_registration["provider_dataset_key_id"],
            governance_key_id,
        }
        or not _valid_sha256(previous_provider_dataset_key_commitment)
        or previous_provider_dataset_key_commitment in excluded_key_hashes
        or previous_provider_dataset_key_commitment == governance_key_hash
    ):
        raise ValueError("provider_dataset_key_rotation_commitment_invalid")
    policy_ids = (rotation_policy_id, revocation_registry_id, custody_policy_id)
    if not all(_strict_id(value) for value in policy_ids):
        raise ValueError("dataset_key_lifecycle_policy_id_invalid")
    if len(set(policy_ids + (governance_key_id,))) != 4:
        raise ValueError("dataset_key_lifecycle_policy_role_collision")
    if (
        not _valid_sha256(rotation_policy_hash)
        or not _valid_sha256(custody_policy_hash)
        or rotation_policy_hash == custody_policy_hash
    ):
        raise ValueError("dataset_key_lifecycle_policy_hash_invalid")
    freshness_values = (
        max_receipt_age_seconds,
        max_revocation_snapshot_age_seconds,
        max_receipt_issue_delay_seconds,
    )
    if not all(_strict_freshness_seconds(value) for value in freshness_values):
        raise ValueError("dataset_key_lifecycle_freshness_policy_invalid")

    source_declared = _utc(source_registration.get("declared_at_utc"), "source_declared_at_utc")
    source_valid_from = _utc(
        source_registration.get("valid_from_utc"),
        "provider_dataset_key_valid_from_utc",
    )
    source_valid_until = _utc(
        source_registration.get("valid_until_utc"),
        "provider_dataset_key_valid_until_utc",
    )
    source_issued = _utc(source_receipt.get("issued_at_utc"), "source_attestation_issued_at_utc")
    declared = _utc(declared_at_utc, "declared_at_utc")
    if not (
        source_declared <= declared <= source_issued
        and source_valid_from <= source_issued <= source_valid_until
    ):
        raise ValueError("dataset_key_lifecycle_registration_time_invalid")

    facts = {
        "source_attestation_reverified": True,
        "provider_identity_and_dataset_key_bound": True,
        "governance_key_shape_verified": True,
        "governance_key_role_separation_verified": True,
        "rotation_chain_shape_verified": True,
        "freshness_policy_preregistered": True,
        "external_governance_key_control_verified": False,
        "external_revocation_registry_verified": False,
        "external_provider_dataset_key_custody_verified": False,
        "lifecycle_gate_use_allowed": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "provider_dataset_attestation_use_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }
    body = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_state": (
            "PROVIDER_DATASET_KEY_LIFECYCLE_POLICY_REGISTERED_"
            "EXTERNAL_GOVERNANCE_UNPROVEN"
        ),
        "source_attestation_schema": attestation_source.SCHEMA_VERSION,
        "source_attestation_verification_hash": attestation_document[
            "verification_hash"
        ],
        "source_attestation_hash": attestation_document[
            "source_attestation_hash"
        ],
        "source_dataset_registration_hash": attestation_document[
            "source_registration_hash"
        ],
        "provider_id_hash": attestation_document["provider_id_hash"],
        "provider_dataset_key_id": attestation_document[
            "provider_dataset_key_id"
        ],
        "provider_dataset_public_key_sha256": attestation_document[
            "provider_dataset_public_key_sha256"
        ],
        "provider_dataset_key_binding_hash": source_registration[
            "provider_dataset_key_binding_hash"
        ],
        "provider_dataset_key_valid_from_utc": source_registration[
            "valid_from_utc"
        ],
        "provider_dataset_key_valid_until_utc": source_registration[
            "valid_until_utc"
        ],
        "source_attestation_issued_at_utc": source_receipt["issued_at_utc"],
        "governance_key_role": GOVERNANCE_KEY_ROLE,
        "governance_key_id": governance_key_id,
        "governance_public_key_sha256": governance_key_hash,
        "excluded_source_role_key_count": 3,
        "key_epoch": key_epoch,
        "previous_provider_dataset_key_id": previous_provider_dataset_key_id,
        "previous_provider_dataset_key_commitment": (
            previous_provider_dataset_key_commitment
        ),
        "rotation_policy_id": rotation_policy_id,
        "rotation_policy_hash": rotation_policy_hash,
        "revocation_registry_id": revocation_registry_id,
        "custody_policy_id": custody_policy_id,
        "custody_policy_hash": custody_policy_hash,
        "declared_at_utc": declared_at_utc,
        "max_receipt_age_seconds": max_receipt_age_seconds,
        "max_revocation_snapshot_age_seconds": (
            max_revocation_snapshot_age_seconds
        ),
        "max_receipt_issue_delay_seconds": max_receipt_issue_delay_seconds,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
        "facts": facts,
        "authority": authority,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "registration_hash": _sha256(body)}


def verify_provider_dataset_key_lifecycle_registration_v1(
    document: Any,
    attestation_document: Any,
    attestation_context: Any,
    governance_public_key_base64: Any,
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
        rebuilt = build_provider_dataset_key_lifecycle_registration_v1(
            attestation_document,
            attestation_context,
            governance_key_id=document["governance_key_id"],
            governance_public_key_base64=governance_public_key_base64,
            key_epoch=document["key_epoch"],
            previous_provider_dataset_key_id=document[
                "previous_provider_dataset_key_id"
            ],
            previous_provider_dataset_key_commitment=document[
                "previous_provider_dataset_key_commitment"
            ],
            rotation_policy_id=document["rotation_policy_id"],
            rotation_policy_hash=document["rotation_policy_hash"],
            revocation_registry_id=document["revocation_registry_id"],
            custody_policy_id=document["custody_policy_id"],
            custody_policy_hash=document["custody_policy_hash"],
            declared_at_utc=document["declared_at_utc"],
            max_receipt_age_seconds=document["max_receipt_age_seconds"],
            max_revocation_snapshot_age_seconds=document[
                "max_revocation_snapshot_age_seconds"
            ],
            max_receipt_issue_delay_seconds=document[
                "max_receipt_issue_delay_seconds"
            ],
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


_UNSIGNED_RECEIPT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "lifecycle_scope",
    "registration_hash",
    "source_attestation_verification_hash",
    "source_attestation_hash",
    "source_dataset_registration_hash",
    "provider_id_hash",
    "provider_dataset_key_id",
    "provider_dataset_public_key_sha256",
    "provider_dataset_key_valid_from_utc",
    "provider_dataset_key_valid_until_utc",
    "governance_key_role",
    "governance_key_id",
    "governance_public_key_sha256",
    "key_epoch",
    "previous_provider_dataset_key_id",
    "previous_provider_dataset_key_commitment",
    "rotation_policy_id",
    "rotation_policy_hash",
    "revocation_registry_id",
    "revocation_snapshot_hash",
    "revocation_snapshot_at_utc",
    "provider_dataset_key_revoked",
    "provider_key_binding_claimed",
    "provider_dataset_key_custody_claimed",
    "custody_policy_id",
    "custody_policy_hash",
    "custody_domains_separated",
    "audit_completed_at_utc",
    "issued_at_utc",
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "signature_domain",
    "receipt_content_sha256",
}


def build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1(
    registration: dict[str, Any],
    *,
    revocation_snapshot_hash: str,
    revocation_snapshot_at_utc: str,
    provider_dataset_key_revoked: bool,
    provider_key_binding_claimed: bool,
    provider_dataset_key_custody_claimed: bool,
    custody_domains_separated: bool,
    audit_completed_at_utc: str,
    issued_at_utc: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or registration.get("static_fingerprint") != STATIC_FINGERPRINT
        or registration.get("governance_key_role") != GOVERNANCE_KEY_ROLE
        or not _valid_sha256(registration.get("registration_hash"))
    ):
        raise ValueError("dataset_key_lifecycle_registration_contract_invalid")
    if not _valid_sha256(revocation_snapshot_hash):
        raise ValueError("revocation_snapshot_hash_invalid")
    claims = (
        provider_dataset_key_revoked,
        provider_key_binding_claimed,
        provider_dataset_key_custody_claimed,
        custody_domains_separated,
    )
    if not all(_strict_bool(value) for value in claims):
        raise ValueError("dataset_key_lifecycle_boolean_claim_invalid")
    valid_from = _utc(
        registration.get("provider_dataset_key_valid_from_utc"),
        "provider_dataset_key_valid_from_utc",
    )
    valid_until = _utc(
        registration.get("provider_dataset_key_valid_until_utc"),
        "provider_dataset_key_valid_until_utc",
    )
    source_issued = _utc(
        registration.get("source_attestation_issued_at_utc"),
        "source_attestation_issued_at_utc",
    )
    snapshot_at = _utc(revocation_snapshot_at_utc, "revocation_snapshot_at_utc")
    completed_at = _utc(audit_completed_at_utc, "audit_completed_at_utc")
    issued_at = _utc(issued_at_utc, "issued_at_utc")
    if not (
        valid_from
        <= source_issued
        <= snapshot_at
        <= completed_at
        <= issued_at
        <= valid_until
    ):
        raise ValueError("dataset_key_lifecycle_receipt_time_order_invalid")
    body = {
        "schema_version": GOVERNANCE_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "lifecycle_scope": LIFECYCLE_SCOPE,
        "registration_hash": registration["registration_hash"],
        "source_attestation_verification_hash": registration[
            "source_attestation_verification_hash"
        ],
        "source_attestation_hash": registration["source_attestation_hash"],
        "source_dataset_registration_hash": registration[
            "source_dataset_registration_hash"
        ],
        "provider_id_hash": registration["provider_id_hash"],
        "provider_dataset_key_id": registration["provider_dataset_key_id"],
        "provider_dataset_public_key_sha256": registration[
            "provider_dataset_public_key_sha256"
        ],
        "provider_dataset_key_valid_from_utc": registration[
            "provider_dataset_key_valid_from_utc"
        ],
        "provider_dataset_key_valid_until_utc": registration[
            "provider_dataset_key_valid_until_utc"
        ],
        "governance_key_role": GOVERNANCE_KEY_ROLE,
        "governance_key_id": registration["governance_key_id"],
        "governance_public_key_sha256": registration[
            "governance_public_key_sha256"
        ],
        "key_epoch": registration["key_epoch"],
        "previous_provider_dataset_key_id": registration[
            "previous_provider_dataset_key_id"
        ],
        "previous_provider_dataset_key_commitment": registration[
            "previous_provider_dataset_key_commitment"
        ],
        "rotation_policy_id": registration["rotation_policy_id"],
        "rotation_policy_hash": registration["rotation_policy_hash"],
        "revocation_registry_id": registration["revocation_registry_id"],
        "revocation_snapshot_hash": revocation_snapshot_hash,
        "revocation_snapshot_at_utc": revocation_snapshot_at_utc,
        "provider_dataset_key_revoked": provider_dataset_key_revoked,
        "provider_key_binding_claimed": provider_key_binding_claimed,
        "provider_dataset_key_custody_claimed": (
            provider_dataset_key_custody_claimed
        ),
        "custody_policy_id": registration["custody_policy_id"],
        "custody_policy_hash": registration["custody_policy_hash"],
        "custody_domains_separated": custody_domains_separated,
        "audit_completed_at_utc": audit_completed_at_utc,
        "issued_at_utc": issued_at_utc,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
    }
    return {**body, "receipt_content_sha256": _sha256(body)}


def assemble_provider_dataset_key_lifecycle_governance_receipt_v1(
    unsigned_receipt: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    if (
        type(unsigned_receipt) is not dict
        or set(unsigned_receipt) != _UNSIGNED_RECEIPT_KEYS
    ):
        raise ValueError("unsigned_dataset_key_lifecycle_receipt_contract_invalid")
    body = {
        key: value
        for key, value in unsigned_receipt.items()
        if key != "receipt_content_sha256"
    }
    if unsigned_receipt["receipt_content_sha256"] != _sha256(body):
        raise ValueError("unsigned_dataset_key_lifecycle_content_hash_invalid")
    signature = _decode_base64(
        signature_base64,
        64,
        "dataset_key_lifecycle_signature",
    )
    sealed_body = {
        **unsigned_receipt,
        "signature_sha256": hashlib.sha256(signature).hexdigest(),
    }
    return {
        **sealed_body,
        "signature_base64": signature_base64,
        "lifecycle_receipt_hash": _sha256(sealed_body),
    }


_RECEIPT_KEYS = _UNSIGNED_RECEIPT_KEYS | {
    "signature_base64",
    "signature_sha256",
    "lifecycle_receipt_hash",
}


def evaluate_provider_dataset_key_lifecycle_gate_v1(
    attestation_document: dict[str, Any],
    attestation_context: dict[str, Any],
    lifecycle_registration: dict[str, Any],
    governance_public_key_base64: str,
    lifecycle_receipt: dict[str, Any],
    *,
    expected_registration_hash: str,
    expected_lifecycle_receipt_hash: str,
    reference_time_utc: str,
) -> dict[str, Any]:
    if _authority_invalid(
        [attestation_document, attestation_context, lifecycle_registration]
    ):
        raise ValueError("dataset_key_lifecycle_gate_authority_invalid")
    if not verify_provider_dataset_key_lifecycle_registration_v1(
        lifecycle_registration,
        attestation_document,
        attestation_context,
        governance_public_key_base64,
        expected_registration_hash=expected_registration_hash,
    ):
        raise ValueError("dataset_key_lifecycle_registration_invalid")
    if (
        type(lifecycle_receipt) is not dict
        or set(lifecycle_receipt) != _RECEIPT_KEYS
        or not _valid_sha256(expected_lifecycle_receipt_hash)
        or lifecycle_receipt.get("lifecycle_receipt_hash")
        != expected_lifecycle_receipt_hash
    ):
        raise ValueError("dataset_key_lifecycle_receipt_invalid")
    unsigned = build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1(
        lifecycle_registration,
        revocation_snapshot_hash=lifecycle_receipt["revocation_snapshot_hash"],
        revocation_snapshot_at_utc=lifecycle_receipt[
            "revocation_snapshot_at_utc"
        ],
        provider_dataset_key_revoked=lifecycle_receipt[
            "provider_dataset_key_revoked"
        ],
        provider_key_binding_claimed=lifecycle_receipt[
            "provider_key_binding_claimed"
        ],
        provider_dataset_key_custody_claimed=lifecycle_receipt[
            "provider_dataset_key_custody_claimed"
        ],
        custody_domains_separated=lifecycle_receipt[
            "custody_domains_separated"
        ],
        audit_completed_at_utc=lifecycle_receipt["audit_completed_at_utc"],
        issued_at_utc=lifecycle_receipt["issued_at_utc"],
    )
    if any(lifecycle_receipt.get(key) != value for key, value in unsigned.items()):
        raise ValueError("dataset_key_lifecycle_receipt_source_binding_mismatch")
    assembled = assemble_provider_dataset_key_lifecycle_governance_receipt_v1(
        unsigned,
        lifecycle_receipt["signature_base64"],
    )
    if lifecycle_receipt != assembled:
        raise ValueError("dataset_key_lifecycle_receipt_seal_invalid")
    governance_public_key = _decode_base64(
        governance_public_key_base64,
        32,
        "governance_public_key",
    )
    if (
        hashlib.sha256(governance_public_key).hexdigest()
        != lifecycle_registration["governance_public_key_sha256"]
        or Ed25519PublicKey is None
    ):
        raise ValueError("dataset_key_lifecycle_governance_public_key_invalid")
    signature = _decode_base64(
        lifecycle_receipt["signature_base64"],
        64,
        "dataset_key_lifecycle_signature",
    )
    try:
        Ed25519PublicKey.from_public_bytes(governance_public_key).verify(
            signature,
            bytes.fromhex(lifecycle_receipt["receipt_content_sha256"]),
        )
    except (InvalidSignature, ValueError) as error:
        raise ValueError("dataset_key_lifecycle_governance_signature_invalid") from error

    snapshot_at = _utc(
        lifecycle_receipt["revocation_snapshot_at_utc"],
        "revocation_snapshot_at_utc",
    )
    completed_at = _utc(
        lifecycle_receipt["audit_completed_at_utc"],
        "audit_completed_at_utc",
    )
    issued_at = _utc(lifecycle_receipt["issued_at_utc"], "issued_at_utc")
    reference_time = _utc(reference_time_utc, "reference_time_utc")
    valid_until = _utc(
        lifecycle_registration["provider_dataset_key_valid_until_utc"],
        "provider_dataset_key_valid_until_utc",
    )
    if not issued_at <= reference_time <= valid_until:
        raise ValueError("dataset_key_lifecycle_reference_time_invalid")
    if (
        (issued_at - completed_at).total_seconds()
        > lifecycle_registration["max_receipt_issue_delay_seconds"]
    ):
        raise ValueError("dataset_key_lifecycle_receipt_issue_delay_exceeded")
    if (
        (reference_time - issued_at).total_seconds()
        > lifecycle_registration["max_receipt_age_seconds"]
    ):
        raise ValueError("dataset_key_lifecycle_receipt_age_exceeded")
    if (
        (reference_time - snapshot_at).total_seconds()
        > lifecycle_registration["max_revocation_snapshot_age_seconds"]
    ):
        raise ValueError("dataset_key_lifecycle_revocation_snapshot_age_exceeded")
    if lifecycle_receipt["provider_dataset_key_revoked"] is not False:
        raise ValueError("provider_dataset_key_revoked")
    if lifecycle_receipt["provider_key_binding_claimed"] is not True:
        raise ValueError("provider_dataset_key_binding_claim_denied")
    if lifecycle_receipt["provider_dataset_key_custody_claimed"] is not True:
        raise ValueError("provider_dataset_key_custody_claim_denied")
    if lifecycle_receipt["custody_domains_separated"] is not True:
        raise ValueError("provider_dataset_key_custody_domain_separation_denied")

    facts = {
        "source_attestation_reverified": True,
        "provider_dataset_key_lineage_bound": True,
        "governance_key_role_separation_verified": True,
        "governance_receipt_structure_verified": True,
        "governance_receipt_signature_verified": True,
        "rotation_epoch_and_previous_commitment_bound": True,
        "fresh_non_revocation_claim_verified": True,
        "provider_key_binding_claim_verified": True,
        "provider_dataset_key_custody_claim_verified": True,
        "custody_domain_separation_claim_verified": True,
        "external_governance_authority_verified": False,
        "external_provider_dataset_key_control_verified": False,
        "external_revocation_registry_durability_verified": False,
        "lifecycle_receipt_replay_registry_checked": False,
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
        "status": "PASS",
        "verification_state": VERIFICATION_STATE,
        "source_attestation_verification_hash": attestation_document[
            "verification_hash"
        ],
        "source_attestation_hash": attestation_document[
            "source_attestation_hash"
        ],
        "source_dataset_registration_hash": attestation_document[
            "source_registration_hash"
        ],
        "lifecycle_registration_hash": lifecycle_registration[
            "registration_hash"
        ],
        "lifecycle_governance_receipt_hash": lifecycle_receipt[
            "lifecycle_receipt_hash"
        ],
        "provider_id_hash": lifecycle_registration["provider_id_hash"],
        "provider_dataset_key_id": lifecycle_registration[
            "provider_dataset_key_id"
        ],
        "provider_dataset_public_key_sha256": lifecycle_registration[
            "provider_dataset_public_key_sha256"
        ],
        "governance_key_role": GOVERNANCE_KEY_ROLE,
        "governance_key_id": lifecycle_registration["governance_key_id"],
        "governance_public_key_sha256": lifecycle_registration[
            "governance_public_key_sha256"
        ],
        "key_epoch": lifecycle_registration["key_epoch"],
        "previous_provider_dataset_key_id": lifecycle_registration[
            "previous_provider_dataset_key_id"
        ],
        "previous_provider_dataset_key_commitment": lifecycle_registration[
            "previous_provider_dataset_key_commitment"
        ],
        "rotation_policy_id": lifecycle_registration["rotation_policy_id"],
        "rotation_policy_hash": lifecycle_registration["rotation_policy_hash"],
        "revocation_registry_id": lifecycle_registration[
            "revocation_registry_id"
        ],
        "revocation_snapshot_hash": lifecycle_receipt[
            "revocation_snapshot_hash"
        ],
        "revocation_snapshot_at_utc": lifecycle_receipt[
            "revocation_snapshot_at_utc"
        ],
        "custody_policy_id": lifecycle_registration["custody_policy_id"],
        "custody_policy_hash": lifecycle_registration["custody_policy_hash"],
        "governance_receipt_issued_at_utc": lifecycle_receipt["issued_at_utc"],
        "reference_time_utc": reference_time_utc,
        "signature_sha256": lifecycle_receipt["signature_sha256"],
        "facts": facts,
        "blockers": [
            "external_governance_authority_unproven",
            "external_provider_dataset_key_control_unproven",
            "external_revocation_registry_durability_unproven",
            "lifecycle_receipt_replay_registry_unchecked",
            "observation_admission_locked",
        ],
        "authority": authority,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "verification_hash": _sha256(body)}


def verify_provider_dataset_key_lifecycle_gate_v1(
    document: Any,
    attestation_document: Any,
    attestation_context: Any,
    lifecycle_registration: Any,
    governance_public_key_base64: Any,
    lifecycle_receipt: Any,
    *,
    expected_registration_hash: Any,
    expected_lifecycle_receipt_hash: Any,
    reference_time_utc: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = evaluate_provider_dataset_key_lifecycle_gate_v1(
            attestation_document,
            attestation_context,
            lifecycle_registration,
            governance_public_key_base64,
            lifecycle_receipt,
            expected_registration_hash=expected_registration_hash,
            expected_lifecycle_receipt_hash=expected_lifecycle_receipt_hash,
            reference_time_utc=reference_time_utc,
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
    "GENESIS_COMMITMENT",
    "GOVERNANCE_KEY_ROLE",
    "GOVERNANCE_RECEIPT_SCHEMA_VERSION",
    "LIFECYCLE_SCOPE",
    "RECEIPT_ENCODING",
    "REGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_MESSAGE_FORMAT",
    "STATIC_FINGERPRINT",
    "VERIFICATION_STATE",
    "assemble_provider_dataset_key_lifecycle_governance_receipt_v1",
    "build_provider_dataset_key_lifecycle_registration_v1",
    "build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1",
    "evaluate_provider_dataset_key_lifecycle_gate_v1",
    "verify_provider_dataset_key_lifecycle_gate_v1",
    "verify_provider_dataset_key_lifecycle_registration_v1",
]
