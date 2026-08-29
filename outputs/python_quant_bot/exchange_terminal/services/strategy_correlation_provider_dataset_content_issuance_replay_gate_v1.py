from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from . import strategy_correlation_provider_dataset_content_attestation_v1 as content_source
from . import strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as lifecycle_replay_source
from .execution_authority import authority_violations

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised by dependency-absence tests
    InvalidSignature = Exception  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-issuance-replay-registration-v1"
)
PINNED_CHECKPOINT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-issuance-replay-pinned-checkpoint-v1"
)
CHECKPOINT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-issuance-replay-checkpoint-v1"
)
OCCURRENCE_AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-issuance-replay-occurrence-audit-v1"
)
SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-content-issuance-replay-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-dataset-content-issuance-replay-gate-1"
)
REPLAY_REGISTRY_KEY_ROLE = lifecycle_replay_source.REPLAY_REGISTRY_KEY_ROLE
OCCURRENCE_AUDITOR_KEY_ROLE = (
    lifecycle_replay_source.OCCURRENCE_AUDITOR_KEY_ROLE
)
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "RFC8785_JCS_UTF8"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
LOG_PROTOCOL = "DOMAIN_SEPARATED_BINARY_MERKLE_APPEND_ONLY_V1"
SCAN_POLICY = "FULL_PINNED_CHECKPOINT_INDEX_SCAN_V1"
CARDINALITY_POLICY = "EXACTLY_ONE_CONTENT_IDENTITY_OCCURRENCE_CLAIM_V1"
CONTENT_IDENTITY_POLICY = (
    "ATTESTATION_HASH_PLUS_FUTURE_EVALUATION_ID_HASH_V1"
)
EMPTY_DOMAIN = (
    "hakimi.strategy-correlation.dataset-content-issuance-replay.empty.v1"
)
LEAF_DOMAIN = (
    "hakimi.strategy-correlation.dataset-content-issuance-replay.leaf.v1"
)
NODE_DOMAIN = (
    "hakimi.strategy-correlation.dataset-content-issuance-replay.node.v1"
)
CHECKPOINT_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.dataset-content-issuance-replay.checkpoint.v1"
)
OCCURRENCE_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.dataset-content-issuance-replay.occurrence.v1"
)
GENESIS_COMMITMENT = "GENESIS"
GENESIS_ROOT_HASH = hashlib.sha256(
    (EMPTY_DOMAIN + "\x00").encode("ascii")
).hexdigest()
VERIFICATION_STATE = (
    "SIGNED_CONTENT_ISSUANCE_CHECKPOINT_INCLUSION_AND_EXACTLY_ONE_"
    "OCCURRENCE_CLAIM_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN"
)

_MAX_TREE_SIZE = (1 << 63) - 1
_MAX_PROOF_LENGTH = 128
_MAX_FRESHNESS_SECONDS = 366 * 24 * 60 * 60
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{2,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ATTESTATION_CONTEXT_KEYS = {
    "composition_document",
    "composition_context",
    "registration",
    "provider_dataset_public_key_base64",
    "attestation_receipt",
    "expected_registration_hash",
    "expected_attestation_hash",
}
_LIFECYCLE_REPLAY_CONTEXT_KEYS = {
    "lifecycle_document",
    "lifecycle_context",
    "replay_registration",
    "replay_registry_public_key_base64",
    "occurrence_auditor_public_key_base64",
    "pinned_checkpoint",
    "checkpoint",
    "inclusion_proof",
    "consistency_proof",
    "occurrence_audit",
    "expected_registration_hash",
    "expected_pinned_checkpoint_hash",
    "expected_checkpoint_hash",
    "expected_occurrence_audit_hash",
    "reference_time_utc",
}
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_REGISTRATION_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_state",
    "source_attestation_schema",
    "source_attestation_verification_hash",
    "source_attestation_registration_hash",
    "source_attestation_hash",
    "source_composition_hash",
    "future_evaluation_id_hash",
    "source_lifecycle_replay_schema",
    "source_lifecycle_replay_verification_hash",
    "source_lifecycle_replay_registration_hash",
    "source_lifecycle_replay_checkpoint_hash",
    "source_lifecycle_replay_occurrence_audit_hash",
    "source_lifecycle_replay_audit_issued_at_utc",
    "source_lifecycle_replay_reference_time_utc",
    "provider_id_hash",
    "provider_dataset_key_id",
    "provider_dataset_public_key_sha256",
    "replay_registry_id",
    "source_lifecycle_replay_registry_namespace",
    "content_replay_registry_namespace",
    "adapter_id",
    "adapter_implementation_hash",
    "replay_registry_key_role",
    "replay_registry_key_id",
    "replay_registry_public_key_sha256",
    "occurrence_auditor_id",
    "occurrence_auditor_key_role",
    "occurrence_auditor_key_id",
    "occurrence_auditor_public_key_sha256",
    "log_protocol",
    "scan_policy",
    "cardinality_policy",
    "content_identity_policy",
    "empty_domain",
    "leaf_domain",
    "node_domain",
    "checkpoint_signature_domain",
    "occurrence_signature_domain",
    "genesis_root_hash",
    "declared_at_utc",
    "max_checkpoint_age_seconds",
    "max_scan_age_seconds",
    "max_occurrence_receipt_issue_delay_seconds",
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "facts",
    "authority",
    "permissions",
    "registration_hash",
}
_PINNED_CHECKPOINT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "replay_registry_id",
    "content_replay_registry_namespace",
    "tree_size",
    "root_hash",
    "checkpoint_hash",
    "pin_hash",
}
_UNSIGNED_CHECKPOINT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "source_attestation_hash",
    "future_evaluation_id_hash",
    "content_issuance_leaf_hash",
    "replay_registry_id",
    "content_replay_registry_namespace",
    "adapter_id",
    "adapter_implementation_hash",
    "tree_size",
    "root_hash",
    "previous_tree_size",
    "previous_root_hash",
    "previous_checkpoint_hash",
    "pinned_checkpoint_hash",
    "issued_at_utc",
    "replay_registry_key_role",
    "replay_registry_key_id",
    "replay_registry_public_key_sha256",
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "signature_domain",
    "receipt_content_sha256",
}
_CHECKPOINT_KEYS = _UNSIGNED_CHECKPOINT_KEYS | {
    "signature_sha256",
    "signature_base64",
    "checkpoint_hash",
}
_UNSIGNED_AUDIT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "source_attestation_verification_hash",
    "source_attestation_hash",
    "source_lifecycle_replay_verification_hash",
    "future_evaluation_id_hash",
    "content_issuance_leaf_hash",
    "replay_registry_id",
    "content_replay_registry_namespace",
    "checkpoint_hash",
    "checkpoint_tree_size",
    "checkpoint_root_hash",
    "pinned_checkpoint_hash",
    "occurrence_leaf_index",
    "inclusion_proof_hash",
    "consistency_proof_hash",
    "scan_start_index",
    "scan_end_index_exclusive",
    "index_snapshot_record_count",
    "occurrence_count",
    "occurrence_leaf_indices",
    "index_snapshot_root_hash",
    "scan_completed_at_utc",
    "audit_issued_at_utc",
    "reference_time_utc",
    "occurrence_auditor_id",
    "occurrence_auditor_key_role",
    "occurrence_auditor_key_id",
    "occurrence_auditor_public_key_sha256",
    "scan_policy",
    "cardinality_policy",
    "content_identity_policy",
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "signature_domain",
    "receipt_content_sha256",
}
_AUDIT_KEYS = _UNSIGNED_AUDIT_KEYS | {
    "signature_sha256",
    "signature_base64",
    "occurrence_audit_hash",
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
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _strict_id(value: Any) -> bool:
    return type(value) is str and _ID_RE.fullmatch(value) is not None


def _strict_int(
    value: Any,
    *,
    minimum: int = 0,
    maximum: int,
) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _strict_freshness(value: Any) -> bool:
    return _strict_int(
        value,
        minimum=1,
        maximum=_MAX_FRESHNESS_SECONDS,
    )


def _utc(value: Any, label: str) -> datetime:
    if type(value) is not str or _UTC_RE.fullmatch(value) is None:
        raise ValueError(f"{label}_invalid")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as error:
        raise ValueError(f"{label}_invalid") from error


def _decode_base64(value: Any, expected_length: int, label: str) -> bytes:
    if type(value) is not str:
        raise ValueError(f"{label}_invalid")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"{label}_invalid") from error
    if (
        len(decoded) != expected_length
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        raise ValueError(f"{label}_invalid")
    return decoded


def _proof(value: Any) -> list[str] | None:
    if (
        type(value) is not list
        or len(value) > _MAX_PROOF_LENGTH
        or not all(_valid_sha256(item) for item in value)
    ):
        return None
    return list(value)


def _verify_signature(
    *,
    public_key_base64: Any,
    expected_public_key_hash: Any,
    signature_base64: Any,
    receipt_content_sha256: Any,
    label: str,
) -> None:
    public_key_raw = _decode_base64(
        public_key_base64,
        32,
        f"{label}_public_key",
    )
    if (
        not _valid_sha256(expected_public_key_hash)
        or hashlib.sha256(public_key_raw).hexdigest()
        != expected_public_key_hash
        or not _valid_sha256(receipt_content_sha256)
        or Ed25519PublicKey is None
    ):
        raise ValueError(f"{label}_public_key_invalid")
    signature = _decode_base64(
        signature_base64,
        64,
        f"{label}_signature",
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(
            signature,
            bytes.fromhex(receipt_content_sha256),
        )
    except (InvalidSignature, ValueError) as error:
        raise ValueError(f"{label}_signature_invalid") from error


def _assemble_signed_receipt(
    unsigned_receipt: dict[str, Any],
    unsigned_keys: set[str],
    signature_base64: str,
    *,
    signature_label: str,
    receipt_hash_field: str,
) -> dict[str, Any]:
    if type(unsigned_receipt) is not dict or set(unsigned_receipt) != unsigned_keys:
        raise ValueError(f"unsigned_{signature_label}_contract_invalid")
    body = {
        key: value
        for key, value in unsigned_receipt.items()
        if key != "receipt_content_sha256"
    }
    if unsigned_receipt["receipt_content_sha256"] != _sha256(body):
        raise ValueError(f"unsigned_{signature_label}_content_hash_invalid")
    signature = _decode_base64(signature_base64, 64, signature_label)
    sealed_body = {
        **unsigned_receipt,
        "signature_sha256": hashlib.sha256(signature).hexdigest(),
    }
    return {
        **sealed_body,
        "signature_base64": signature_base64,
        receipt_hash_field: _sha256(sealed_body),
    }


def _attestation_verified(document: Any, context: Any) -> bool:
    if (
        type(context) is not dict
        or set(context) != _ATTESTATION_CONTEXT_KEYS
    ):
        return False
    try:
        return content_source.verify_provider_dataset_content_attestation_v1(
            document,
            **context,
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


def _lifecycle_replay_verified(document: Any, context: Any) -> bool:
    if (
        type(context) is not dict
        or set(context) != _LIFECYCLE_REPLAY_CONTEXT_KEYS
    ):
        return False
    try:
        return lifecycle_replay_source.verify_provider_dataset_key_lifecycle_replay_gate_v1(
            document,
            **context,
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
    lifecycle_replay_document: Any,
    lifecycle_replay_context: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not _attestation_verified(attestation_document, attestation_context):
        raise ValueError("content_issuance_replay_attestation_source_invalid")
    if not _lifecycle_replay_verified(
        lifecycle_replay_document,
        lifecycle_replay_context,
    ):
        raise ValueError("content_issuance_replay_lifecycle_source_invalid")
    if (
        type(attestation_document) is not dict
        or attestation_document.get("schema_version")
        != content_source.SCHEMA_VERSION
        or attestation_document.get("static_fingerprint")
        != content_source.STATIC_FINGERPRINT
        or attestation_document.get("source_state") != "VERIFIED"
        or attestation_document.get("verification_state")
        != content_source.VERIFICATION_STATE
        or attestation_document.get("permissions") != _PERMISSIONS
        or attestation_document.get("current_writer_activation_allowed")
        is not False
        or attestation_document.get("current_admission_allowed") is not False
        or attestation_document.get("facts", {}).get("replay_registry_checked")
        is not False
    ):
        raise ValueError("content_issuance_replay_attestation_contract_mismatch")
    if (
        type(lifecycle_replay_document) is not dict
        or lifecycle_replay_document.get("schema_version")
        != lifecycle_replay_source.SCHEMA_VERSION
        or lifecycle_replay_document.get("static_fingerprint")
        != lifecycle_replay_source.STATIC_FINGERPRINT
        or lifecycle_replay_document.get("status") != "PASS"
        or lifecycle_replay_document.get("verification_state")
        != lifecycle_replay_source.VERIFICATION_STATE
        or lifecycle_replay_document.get("permissions") != _PERMISSIONS
        or lifecycle_replay_document.get("current_writer_activation_allowed")
        is not False
        or lifecycle_replay_document.get("current_admission_allowed") is not False
    ):
        raise ValueError("content_issuance_replay_lifecycle_contract_mismatch")

    attestation_receipt = attestation_context.get("attestation_receipt")
    attestation_registration = attestation_context.get("registration")
    composition_document = attestation_context.get("composition_document")
    lifecycle_context = lifecycle_replay_context.get("lifecycle_context")
    replay_registration = lifecycle_replay_context.get("replay_registration")
    replay_occurrence_audit = lifecycle_replay_context.get("occurrence_audit")
    if (
        type(attestation_receipt) is not dict
        or type(attestation_registration) is not dict
        or type(composition_document) is not dict
        or type(lifecycle_context) is not dict
        or type(replay_registration) is not dict
        or type(replay_occurrence_audit) is not dict
        or lifecycle_context.get("attestation_document")
        != attestation_document
        or lifecycle_context.get("attestation_context") != attestation_context
        or attestation_receipt.get("attestation_hash")
        != attestation_document.get("source_attestation_hash")
        or attestation_registration.get("registration_hash")
        != attestation_document.get("source_registration_hash")
        or composition_document.get("composition_hash")
        != attestation_document.get("source_composition_hash")
        or replay_registration.get("registration_hash")
        != lifecycle_replay_document.get("replay_registration_hash")
        or replay_occurrence_audit.get("occurrence_audit_hash")
        != lifecycle_replay_document.get("occurrence_audit_hash")
        or replay_registration.get("provider_dataset_key_id")
        != attestation_document.get("provider_dataset_key_id")
        or replay_registration.get("provider_dataset_public_key_sha256")
        != attestation_document.get("provider_dataset_public_key_sha256")
        or lifecycle_replay_document.get("provider_id_hash")
        != attestation_document.get("provider_id_hash")
        or lifecycle_replay_document.get("provider_dataset_key_id")
        != attestation_document.get("provider_dataset_key_id")
        or lifecycle_replay_document.get("reference_time_utc")
        != lifecycle_replay_context.get("reference_time_utc")
        or not _valid_sha256(
            composition_document.get("future_evaluation_id_hash")
        )
    ):
        raise ValueError("content_issuance_replay_source_lineage_mismatch")
    return (
        attestation_receipt,
        composition_document,
        replay_registration,
        replay_occurrence_audit,
    )


def hash_provider_dataset_content_issuance_leaf_v1(
    attestation_hash: str,
    future_evaluation_id_hash: str,
) -> str:
    if (
        not _valid_sha256(attestation_hash)
        or not _valid_sha256(future_evaluation_id_hash)
    ):
        raise ValueError("content_issuance_identity_hash_invalid")
    payload = (
        LEAF_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(attestation_hash)
        + bytes.fromhex(future_evaluation_id_hash)
    )
    return hashlib.sha256(payload).hexdigest()


def hash_provider_dataset_content_issuance_node_v1(
    left_hash: str,
    right_hash: str,
) -> str:
    if not _valid_sha256(left_hash) or not _valid_sha256(right_hash):
        raise ValueError("content_issuance_node_hash_invalid")
    payload = (
        NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left_hash)
        + bytes.fromhex(right_hash)
    )
    return hashlib.sha256(payload).hexdigest()


def _verify_inclusion(
    *,
    attestation_hash: str,
    future_evaluation_id_hash: str,
    leaf_index: int,
    tree_size: int,
    root_hash: str,
    proof: list[str],
) -> bool:
    if not 0 <= leaf_index < tree_size:
        return False
    fn = leaf_index
    sn = tree_size - 1
    running = hash_provider_dataset_content_issuance_leaf_v1(
        attestation_hash,
        future_evaluation_id_hash,
    )
    for sibling in proof:
        if sn == 0:
            return False
        if fn == sn or (fn & 1) == 1:
            running = hash_provider_dataset_content_issuance_node_v1(
                sibling,
                running,
            )
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            running = hash_provider_dataset_content_issuance_node_v1(
                running,
                sibling,
            )
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
            first_root = hash_provider_dataset_content_issuance_node_v1(
                sibling,
                first_root,
            )
            second_root = hash_provider_dataset_content_issuance_node_v1(
                sibling,
                second_root,
            )
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            second_root = hash_provider_dataset_content_issuance_node_v1(
                second_root,
                sibling,
            )
        fn >>= 1
        sn >>= 1

    return (
        fn == 0
        and sn == 0
        and first_root == old_root
        and second_root == new_root
    )


def build_provider_dataset_content_issuance_replay_registration_v1(
    attestation_document: dict[str, Any],
    attestation_context: dict[str, Any],
    lifecycle_replay_document: dict[str, Any],
    lifecycle_replay_context: dict[str, Any],
    *,
    content_replay_registry_namespace: str,
    adapter_id: str,
    adapter_implementation_hash: str,
    declared_at_utc: str,
    max_checkpoint_age_seconds: int,
    max_scan_age_seconds: int,
    max_occurrence_receipt_issue_delay_seconds: int,
) -> dict[str, Any]:
    if _authority_invalid(
        [
            attestation_document,
            attestation_context,
            lifecycle_replay_document,
            lifecycle_replay_context,
        ]
    ):
        raise ValueError("content_issuance_replay_registration_authority_invalid")
    (
        attestation_receipt,
        composition_document,
        replay_registration,
        replay_occurrence_audit,
    ) = _source_contract(
        attestation_document,
        attestation_context,
        lifecycle_replay_document,
        lifecycle_replay_context,
    )
    if (
        not _strict_id(content_replay_registry_namespace)
        or not _strict_id(adapter_id)
        or content_replay_registry_namespace
        == replay_registration["replay_registry_namespace"]
    ):
        raise ValueError("content_issuance_replay_identifier_invalid")
    if not _valid_sha256(adapter_implementation_hash):
        raise ValueError(
            "content_issuance_replay_adapter_implementation_hash_invalid"
        )
    freshness_values = (
        max_checkpoint_age_seconds,
        max_scan_age_seconds,
        max_occurrence_receipt_issue_delay_seconds,
    )
    source_freshness_values = (
        replay_registration["max_checkpoint_age_seconds"],
        replay_registration["max_scan_age_seconds"],
        replay_registration["max_occurrence_receipt_issue_delay_seconds"],
    )
    if (
        not all(_strict_freshness(value) for value in freshness_values)
        or any(
            value > source_value
            for value, source_value in zip(
                freshness_values,
                source_freshness_values,
                strict=True,
            )
        )
    ):
        raise ValueError("content_issuance_replay_freshness_policy_invalid")

    attestation_issued = _utc(
        attestation_receipt["issued_at_utc"],
        "source_attestation_issued_at_utc",
    )
    attestation_valid_until = _utc(
        attestation_document["valid_until_utc"],
        "source_attestation_valid_until_utc",
    )
    source_audit_issued = _utc(
        replay_occurrence_audit["audit_issued_at_utc"],
        "source_lifecycle_replay_audit_issued_at_utc",
    )
    reference_time = _utc(
        lifecycle_replay_document["reference_time_utc"],
        "source_lifecycle_replay_reference_time_utc",
    )
    declared = _utc(declared_at_utc, "declared_at_utc")
    if not (
        attestation_issued
        <= source_audit_issued
        <= declared
        <= reference_time
        <= attestation_valid_until
    ):
        raise ValueError("content_issuance_replay_registration_time_invalid")

    facts = {
        "source_dataset_content_attestation_reverified": True,
        "source_dataset_key_lifecycle_replay_reverified": True,
        "provider_dataset_key_lineage_bound": True,
        "future_evaluation_identity_bound": True,
        "existing_replay_registry_key_role_reused": True,
        "existing_occurrence_auditor_key_role_reused": True,
        "content_replay_namespace_separated": True,
        "append_only_protocol_preregistered": True,
        "full_scan_cardinality_policy_preregistered": True,
        "external_content_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "external_provider_data_issuance_verified": False,
        "durable_checkpoint_publication_verified": False,
        "replay_gate_use_allowed": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "observation_admission_allowed": False,
        "provider_dataset_attestation_use_allowed": False,
        "replay_absence_verified": False,
        "global_uniqueness_verified": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }
    body = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_state": (
            "CONTENT_ISSUANCE_REPLAY_CONSUMER_REGISTERED_EXTERNAL_REGISTRY_UNPROVEN"
        ),
        "source_attestation_schema": content_source.SCHEMA_VERSION,
        "source_attestation_verification_hash": attestation_document[
            "verification_hash"
        ],
        "source_attestation_registration_hash": attestation_document[
            "source_registration_hash"
        ],
        "source_attestation_hash": attestation_document[
            "source_attestation_hash"
        ],
        "source_composition_hash": attestation_document[
            "source_composition_hash"
        ],
        "future_evaluation_id_hash": composition_document[
            "future_evaluation_id_hash"
        ],
        "source_lifecycle_replay_schema": lifecycle_replay_source.SCHEMA_VERSION,
        "source_lifecycle_replay_verification_hash": lifecycle_replay_document[
            "verification_hash"
        ],
        "source_lifecycle_replay_registration_hash": lifecycle_replay_document[
            "replay_registration_hash"
        ],
        "source_lifecycle_replay_checkpoint_hash": lifecycle_replay_document[
            "checkpoint_hash"
        ],
        "source_lifecycle_replay_occurrence_audit_hash": (
            lifecycle_replay_document["occurrence_audit_hash"]
        ),
        "source_lifecycle_replay_audit_issued_at_utc": replay_occurrence_audit[
            "audit_issued_at_utc"
        ],
        "source_lifecycle_replay_reference_time_utc": (
            lifecycle_replay_document["reference_time_utc"]
        ),
        "provider_id_hash": attestation_document["provider_id_hash"],
        "provider_dataset_key_id": attestation_document[
            "provider_dataset_key_id"
        ],
        "provider_dataset_public_key_sha256": attestation_document[
            "provider_dataset_public_key_sha256"
        ],
        "replay_registry_id": replay_registration["replay_registry_id"],
        "source_lifecycle_replay_registry_namespace": replay_registration[
            "replay_registry_namespace"
        ],
        "content_replay_registry_namespace": (
            content_replay_registry_namespace
        ),
        "adapter_id": adapter_id,
        "adapter_implementation_hash": adapter_implementation_hash,
        "replay_registry_key_role": REPLAY_REGISTRY_KEY_ROLE,
        "replay_registry_key_id": replay_registration[
            "replay_registry_key_id"
        ],
        "replay_registry_public_key_sha256": replay_registration[
            "replay_registry_public_key_sha256"
        ],
        "occurrence_auditor_id": replay_registration[
            "occurrence_auditor_id"
        ],
        "occurrence_auditor_key_role": OCCURRENCE_AUDITOR_KEY_ROLE,
        "occurrence_auditor_key_id": replay_registration[
            "occurrence_auditor_key_id"
        ],
        "occurrence_auditor_public_key_sha256": replay_registration[
            "occurrence_auditor_public_key_sha256"
        ],
        "log_protocol": LOG_PROTOCOL,
        "scan_policy": SCAN_POLICY,
        "cardinality_policy": CARDINALITY_POLICY,
        "content_identity_policy": CONTENT_IDENTITY_POLICY,
        "empty_domain": EMPTY_DOMAIN,
        "leaf_domain": LEAF_DOMAIN,
        "node_domain": NODE_DOMAIN,
        "checkpoint_signature_domain": CHECKPOINT_SIGNATURE_DOMAIN,
        "occurrence_signature_domain": OCCURRENCE_SIGNATURE_DOMAIN,
        "genesis_root_hash": GENESIS_ROOT_HASH,
        "declared_at_utc": declared_at_utc,
        "max_checkpoint_age_seconds": max_checkpoint_age_seconds,
        "max_scan_age_seconds": max_scan_age_seconds,
        "max_occurrence_receipt_issue_delay_seconds": (
            max_occurrence_receipt_issue_delay_seconds
        ),
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "facts": facts,
        "authority": authority,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "registration_hash": _sha256(body)}


def verify_provider_dataset_content_issuance_replay_registration_v1(
    document: Any,
    attestation_document: Any,
    attestation_context: Any,
    lifecycle_replay_document: Any,
    lifecycle_replay_context: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    if (
        type(document) is not dict
        or set(document) != _REGISTRATION_KEYS
        or _authority_invalid(document)
        or not _valid_sha256(expected_registration_hash)
        or document.get("registration_hash") != expected_registration_hash
    ):
        return False
    try:
        rebuilt = build_provider_dataset_content_issuance_replay_registration_v1(
            attestation_document,
            attestation_context,
            lifecycle_replay_document,
            lifecycle_replay_context,
            content_replay_registry_namespace=document[
                "content_replay_registry_namespace"
            ],
            adapter_id=document["adapter_id"],
            adapter_implementation_hash=document[
                "adapter_implementation_hash"
            ],
            declared_at_utc=document["declared_at_utc"],
            max_checkpoint_age_seconds=document[
                "max_checkpoint_age_seconds"
            ],
            max_scan_age_seconds=document["max_scan_age_seconds"],
            max_occurrence_receipt_issue_delay_seconds=document[
                "max_occurrence_receipt_issue_delay_seconds"
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


def build_pinned_provider_dataset_content_issuance_checkpoint_v1(
    registration: dict[str, Any],
    *,
    tree_size: int,
    root_hash: str,
    checkpoint_hash: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or set(registration) != _REGISTRATION_KEYS
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or not _valid_sha256(registration.get("registration_hash"))
    ):
        raise ValueError("content_issuance_replay_registration_contract_invalid")
    registration_body = {
        key: value
        for key, value in registration.items()
        if key != "registration_hash"
    }
    if registration["registration_hash"] != _sha256(registration_body):
        raise ValueError("content_issuance_replay_registration_seal_invalid")
    if not _strict_int(tree_size, maximum=_MAX_TREE_SIZE):
        raise ValueError("content_issuance_pinned_tree_size_invalid")
    if not _valid_sha256(root_hash):
        raise ValueError("content_issuance_pinned_root_hash_invalid")
    if tree_size == 0:
        if root_hash != GENESIS_ROOT_HASH or checkpoint_hash != GENESIS_COMMITMENT:
            raise ValueError("content_issuance_pinned_genesis_invalid")
    elif not _valid_sha256(checkpoint_hash):
        raise ValueError("content_issuance_pinned_checkpoint_hash_invalid")
    body = {
        "schema_version": PINNED_CHECKPOINT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "replay_registry_id": registration["replay_registry_id"],
        "content_replay_registry_namespace": registration[
            "content_replay_registry_namespace"
        ],
        "tree_size": tree_size,
        "root_hash": root_hash,
        "checkpoint_hash": checkpoint_hash,
    }
    return {**body, "pin_hash": _sha256(body)}


def build_unsigned_provider_dataset_content_issuance_checkpoint_v1(
    registration: dict[str, Any],
    pinned_checkpoint: dict[str, Any],
    *,
    tree_size: int,
    root_hash: str,
    issued_at_utc: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or set(registration) != _REGISTRATION_KEYS
        or type(pinned_checkpoint) is not dict
        or set(pinned_checkpoint) != _PINNED_CHECKPOINT_KEYS
        or pinned_checkpoint.get("schema_version")
        != PINNED_CHECKPOINT_SCHEMA_VERSION
        or pinned_checkpoint.get("registration_hash")
        != registration.get("registration_hash")
    ):
        raise ValueError("content_issuance_checkpoint_source_invalid")
    pin_body = {
        key: value
        for key, value in pinned_checkpoint.items()
        if key != "pin_hash"
    }
    if pinned_checkpoint["pin_hash"] != _sha256(pin_body):
        raise ValueError("content_issuance_pinned_checkpoint_seal_invalid")
    if (
        not _strict_int(tree_size, minimum=1, maximum=_MAX_TREE_SIZE)
        or tree_size <= pinned_checkpoint["tree_size"]
    ):
        raise ValueError("content_issuance_checkpoint_tree_size_invalid")
    if not _valid_sha256(root_hash):
        raise ValueError("content_issuance_checkpoint_root_hash_invalid")
    issued = _utc(issued_at_utc, "content_issuance_checkpoint_issued_at_utc")
    declared = _utc(registration["declared_at_utc"], "declared_at_utc")
    if issued < declared:
        raise ValueError("content_issuance_checkpoint_time_invalid")
    leaf_hash = hash_provider_dataset_content_issuance_leaf_v1(
        registration["source_attestation_hash"],
        registration["future_evaluation_id_hash"],
    )
    body = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "source_attestation_hash": registration["source_attestation_hash"],
        "future_evaluation_id_hash": registration[
            "future_evaluation_id_hash"
        ],
        "content_issuance_leaf_hash": leaf_hash,
        "replay_registry_id": registration["replay_registry_id"],
        "content_replay_registry_namespace": registration[
            "content_replay_registry_namespace"
        ],
        "adapter_id": registration["adapter_id"],
        "adapter_implementation_hash": registration[
            "adapter_implementation_hash"
        ],
        "tree_size": tree_size,
        "root_hash": root_hash,
        "previous_tree_size": pinned_checkpoint["tree_size"],
        "previous_root_hash": pinned_checkpoint["root_hash"],
        "previous_checkpoint_hash": pinned_checkpoint["checkpoint_hash"],
        "pinned_checkpoint_hash": pinned_checkpoint["pin_hash"],
        "issued_at_utc": issued_at_utc,
        "replay_registry_key_role": REPLAY_REGISTRY_KEY_ROLE,
        "replay_registry_key_id": registration["replay_registry_key_id"],
        "replay_registry_public_key_sha256": registration[
            "replay_registry_public_key_sha256"
        ],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": CHECKPOINT_SIGNATURE_DOMAIN,
    }
    return {**body, "receipt_content_sha256": _sha256(body)}


def assemble_provider_dataset_content_issuance_checkpoint_v1(
    unsigned_checkpoint: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    return _assemble_signed_receipt(
        unsigned_checkpoint,
        _UNSIGNED_CHECKPOINT_KEYS,
        signature_base64,
        signature_label="content_issuance_checkpoint_signature",
        receipt_hash_field="checkpoint_hash",
    )


def build_unsigned_provider_dataset_content_issuance_occurrence_audit_v1(
    registration: dict[str, Any],
    checkpoint: dict[str, Any],
    inclusion_proof: list[str],
    consistency_proof: list[str],
    *,
    occurrence_leaf_index: int,
    scan_start_index: int,
    scan_end_index_exclusive: int,
    index_snapshot_record_count: int,
    occurrence_count: int,
    occurrence_leaf_indices: list[int],
    index_snapshot_root_hash: str,
    scan_completed_at_utc: str,
    audit_issued_at_utc: str,
    reference_time_utc: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or set(registration) != _REGISTRATION_KEYS
        or type(checkpoint) is not dict
        or set(checkpoint) != _CHECKPOINT_KEYS
        or checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or checkpoint.get("registration_hash")
        != registration.get("registration_hash")
        or not _valid_sha256(checkpoint.get("checkpoint_hash"))
    ):
        raise ValueError("content_issuance_occurrence_source_invalid")
    inclusion = _proof(inclusion_proof)
    consistency = _proof(consistency_proof)
    if inclusion is None or consistency is None:
        raise ValueError("content_issuance_occurrence_proof_invalid")
    tree_size = checkpoint["tree_size"]
    integer_values = (
        occurrence_leaf_index,
        scan_start_index,
        scan_end_index_exclusive,
        index_snapshot_record_count,
        occurrence_count,
    )
    if not all(
        _strict_int(value, maximum=_MAX_TREE_SIZE)
        for value in integer_values
    ):
        raise ValueError("content_issuance_occurrence_integer_invalid")
    if (
        not occurrence_leaf_index < tree_size
        or not 0 <= scan_start_index <= scan_end_index_exclusive <= tree_size
        or index_snapshot_record_count > tree_size
        or occurrence_count > tree_size
        or type(occurrence_leaf_indices) is not list
        or len(occurrence_leaf_indices) != occurrence_count
        or not all(
            _strict_int(index, maximum=tree_size - 1)
            for index in occurrence_leaf_indices
        )
        or occurrence_leaf_indices != sorted(set(occurrence_leaf_indices))
    ):
        raise ValueError("content_issuance_occurrence_cardinality_shape_invalid")
    if not _valid_sha256(index_snapshot_root_hash):
        raise ValueError("content_issuance_index_snapshot_root_hash_invalid")
    checkpoint_issued = _utc(
        checkpoint["issued_at_utc"],
        "content_issuance_checkpoint_issued_at_utc",
    )
    scan_completed = _utc(
        scan_completed_at_utc,
        "content_issuance_scan_completed_at_utc",
    )
    audit_issued = _utc(
        audit_issued_at_utc,
        "content_issuance_audit_issued_at_utc",
    )
    reference_time = _utc(reference_time_utc, "reference_time_utc")
    if not checkpoint_issued <= scan_completed <= audit_issued <= reference_time:
        raise ValueError("content_issuance_occurrence_time_order_invalid")
    body = {
        "schema_version": OCCURRENCE_AUDIT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "source_attestation_verification_hash": registration[
            "source_attestation_verification_hash"
        ],
        "source_attestation_hash": registration["source_attestation_hash"],
        "source_lifecycle_replay_verification_hash": registration[
            "source_lifecycle_replay_verification_hash"
        ],
        "future_evaluation_id_hash": registration[
            "future_evaluation_id_hash"
        ],
        "content_issuance_leaf_hash": checkpoint[
            "content_issuance_leaf_hash"
        ],
        "replay_registry_id": registration["replay_registry_id"],
        "content_replay_registry_namespace": registration[
            "content_replay_registry_namespace"
        ],
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "checkpoint_tree_size": tree_size,
        "checkpoint_root_hash": checkpoint["root_hash"],
        "pinned_checkpoint_hash": checkpoint["pinned_checkpoint_hash"],
        "occurrence_leaf_index": occurrence_leaf_index,
        "inclusion_proof_hash": _sha256(inclusion),
        "consistency_proof_hash": _sha256(consistency),
        "scan_start_index": scan_start_index,
        "scan_end_index_exclusive": scan_end_index_exclusive,
        "index_snapshot_record_count": index_snapshot_record_count,
        "occurrence_count": occurrence_count,
        "occurrence_leaf_indices": list(occurrence_leaf_indices),
        "index_snapshot_root_hash": index_snapshot_root_hash,
        "scan_completed_at_utc": scan_completed_at_utc,
        "audit_issued_at_utc": audit_issued_at_utc,
        "reference_time_utc": reference_time_utc,
        "occurrence_auditor_id": registration["occurrence_auditor_id"],
        "occurrence_auditor_key_role": OCCURRENCE_AUDITOR_KEY_ROLE,
        "occurrence_auditor_key_id": registration[
            "occurrence_auditor_key_id"
        ],
        "occurrence_auditor_public_key_sha256": registration[
            "occurrence_auditor_public_key_sha256"
        ],
        "scan_policy": SCAN_POLICY,
        "cardinality_policy": CARDINALITY_POLICY,
        "content_identity_policy": CONTENT_IDENTITY_POLICY,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": OCCURRENCE_SIGNATURE_DOMAIN,
    }
    return {**body, "receipt_content_sha256": _sha256(body)}


def assemble_provider_dataset_content_issuance_occurrence_audit_v1(
    unsigned_audit: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    return _assemble_signed_receipt(
        unsigned_audit,
        _UNSIGNED_AUDIT_KEYS,
        signature_base64,
        signature_label="content_issuance_occurrence_signature",
        receipt_hash_field="occurrence_audit_hash",
    )


def evaluate_provider_dataset_content_issuance_replay_gate_v1(
    attestation_document: dict[str, Any],
    attestation_context: dict[str, Any],
    lifecycle_replay_document: dict[str, Any],
    lifecycle_replay_context: dict[str, Any],
    replay_registration: dict[str, Any],
    pinned_checkpoint: dict[str, Any],
    checkpoint: dict[str, Any],
    inclusion_proof: list[str],
    consistency_proof: list[str],
    occurrence_audit: dict[str, Any],
    *,
    expected_registration_hash: str,
    expected_pinned_checkpoint_hash: str,
    expected_checkpoint_hash: str,
    expected_occurrence_audit_hash: str,
    reference_time_utc: str,
) -> dict[str, Any]:
    if _authority_invalid(
        [
            attestation_document,
            attestation_context,
            lifecycle_replay_document,
            lifecycle_replay_context,
            replay_registration,
            pinned_checkpoint,
            checkpoint,
            occurrence_audit,
        ]
    ):
        raise ValueError("content_issuance_replay_gate_authority_invalid")
    (
        attestation_receipt,
        composition_document,
        source_replay_registration,
        source_replay_occurrence_audit,
    ) = _source_contract(
        attestation_document,
        attestation_context,
        lifecycle_replay_document,
        lifecycle_replay_context,
    )
    if not verify_provider_dataset_content_issuance_replay_registration_v1(
        replay_registration,
        attestation_document,
        attestation_context,
        lifecycle_replay_document,
        lifecycle_replay_context,
        expected_registration_hash=expected_registration_hash,
    ):
        raise ValueError("content_issuance_replay_registration_invalid")
    if (
        type(pinned_checkpoint) is not dict
        or set(pinned_checkpoint) != _PINNED_CHECKPOINT_KEYS
        or not _valid_sha256(expected_pinned_checkpoint_hash)
        or pinned_checkpoint.get("pin_hash")
        != expected_pinned_checkpoint_hash
    ):
        raise ValueError("content_issuance_replay_pinned_checkpoint_invalid")
    expected_pin = (
        build_pinned_provider_dataset_content_issuance_checkpoint_v1(
            replay_registration,
            tree_size=pinned_checkpoint["tree_size"],
            root_hash=pinned_checkpoint["root_hash"],
            checkpoint_hash=pinned_checkpoint["checkpoint_hash"],
        )
    )
    if pinned_checkpoint != expected_pin:
        raise ValueError(
            "content_issuance_replay_pinned_checkpoint_seal_invalid"
        )
    if (
        type(checkpoint) is not dict
        or set(checkpoint) != _CHECKPOINT_KEYS
        or not _valid_sha256(expected_checkpoint_hash)
        or checkpoint.get("checkpoint_hash") != expected_checkpoint_hash
    ):
        raise ValueError("content_issuance_replay_checkpoint_invalid")
    unsigned_checkpoint = (
        build_unsigned_provider_dataset_content_issuance_checkpoint_v1(
            replay_registration,
            pinned_checkpoint,
            tree_size=checkpoint["tree_size"],
            root_hash=checkpoint["root_hash"],
            issued_at_utc=checkpoint["issued_at_utc"],
        )
    )
    rebuilt_checkpoint = (
        assemble_provider_dataset_content_issuance_checkpoint_v1(
            unsigned_checkpoint,
            checkpoint["signature_base64"],
        )
    )
    if checkpoint != rebuilt_checkpoint:
        raise ValueError("content_issuance_replay_checkpoint_seal_invalid")
    _verify_signature(
        public_key_base64=lifecycle_replay_context[
            "replay_registry_public_key_base64"
        ],
        expected_public_key_hash=replay_registration[
            "replay_registry_public_key_sha256"
        ],
        signature_base64=checkpoint["signature_base64"],
        receipt_content_sha256=checkpoint["receipt_content_sha256"],
        label="content_issuance_replay_checkpoint",
    )
    if (
        replay_registration["replay_registry_key_id"]
        != source_replay_registration["replay_registry_key_id"]
        or replay_registration["replay_registry_public_key_sha256"]
        != source_replay_registration["replay_registry_public_key_sha256"]
        or replay_registration["occurrence_auditor_key_id"]
        != source_replay_registration["occurrence_auditor_key_id"]
        or replay_registration["occurrence_auditor_public_key_sha256"]
        != source_replay_registration[
            "occurrence_auditor_public_key_sha256"
        ]
    ):
        raise ValueError("content_issuance_replay_key_lineage_mismatch")

    inclusion = _proof(inclusion_proof)
    consistency = _proof(consistency_proof)
    if inclusion is None or consistency is None:
        raise ValueError("content_issuance_replay_proof_invalid")
    if (
        type(occurrence_audit) is not dict
        or set(occurrence_audit) != _AUDIT_KEYS
        or not _valid_sha256(expected_occurrence_audit_hash)
        or occurrence_audit.get("occurrence_audit_hash")
        != expected_occurrence_audit_hash
    ):
        raise ValueError("content_issuance_replay_occurrence_audit_invalid")
    occurrence_index = occurrence_audit["occurrence_leaf_index"]
    if not _verify_inclusion(
        attestation_hash=attestation_receipt["attestation_hash"],
        future_evaluation_id_hash=composition_document[
            "future_evaluation_id_hash"
        ],
        leaf_index=occurrence_index,
        tree_size=checkpoint["tree_size"],
        root_hash=checkpoint["root_hash"],
        proof=inclusion,
    ):
        raise ValueError("content_issuance_replay_inclusion_proof_invalid")
    if not _verify_consistency(
        old_size=pinned_checkpoint["tree_size"],
        new_size=checkpoint["tree_size"],
        old_root=pinned_checkpoint["root_hash"],
        new_root=checkpoint["root_hash"],
        proof=consistency,
    ):
        raise ValueError("content_issuance_replay_consistency_proof_invalid")
    unsigned_audit = (
        build_unsigned_provider_dataset_content_issuance_occurrence_audit_v1(
            replay_registration,
            checkpoint,
            inclusion,
            consistency,
            occurrence_leaf_index=occurrence_index,
            scan_start_index=occurrence_audit["scan_start_index"],
            scan_end_index_exclusive=occurrence_audit[
                "scan_end_index_exclusive"
            ],
            index_snapshot_record_count=occurrence_audit[
                "index_snapshot_record_count"
            ],
            occurrence_count=occurrence_audit["occurrence_count"],
            occurrence_leaf_indices=occurrence_audit[
                "occurrence_leaf_indices"
            ],
            index_snapshot_root_hash=occurrence_audit[
                "index_snapshot_root_hash"
            ],
            scan_completed_at_utc=occurrence_audit[
                "scan_completed_at_utc"
            ],
            audit_issued_at_utc=occurrence_audit["audit_issued_at_utc"],
            reference_time_utc=occurrence_audit["reference_time_utc"],
        )
    )
    rebuilt_audit = (
        assemble_provider_dataset_content_issuance_occurrence_audit_v1(
            unsigned_audit,
            occurrence_audit["signature_base64"],
        )
    )
    if occurrence_audit != rebuilt_audit:
        raise ValueError("content_issuance_replay_occurrence_audit_seal_invalid")
    _verify_signature(
        public_key_base64=lifecycle_replay_context[
            "occurrence_auditor_public_key_base64"
        ],
        expected_public_key_hash=replay_registration[
            "occurrence_auditor_public_key_sha256"
        ],
        signature_base64=occurrence_audit["signature_base64"],
        receipt_content_sha256=occurrence_audit["receipt_content_sha256"],
        label="content_issuance_replay_occurrence",
    )
    if (
        occurrence_audit["scan_start_index"] != 0
        or occurrence_audit["scan_end_index_exclusive"]
        != checkpoint["tree_size"]
        or occurrence_audit["index_snapshot_record_count"]
        != checkpoint["tree_size"]
    ):
        raise ValueError("content_issuance_replay_complete_scan_claim_invalid")
    if (
        occurrence_audit["occurrence_count"] != 1
        or occurrence_audit["occurrence_leaf_indices"] != [occurrence_index]
    ):
        raise ValueError(
            "content_issuance_replay_exactly_one_occurrence_claim_invalid"
        )
    expected_leaf_hash = hash_provider_dataset_content_issuance_leaf_v1(
        attestation_receipt["attestation_hash"],
        composition_document["future_evaluation_id_hash"],
    )
    if (
        occurrence_audit["index_snapshot_root_hash"] != checkpoint["root_hash"]
        or occurrence_audit["content_issuance_leaf_hash"]
        != expected_leaf_hash
        or checkpoint["content_issuance_leaf_hash"] != expected_leaf_hash
    ):
        raise ValueError("content_issuance_replay_index_snapshot_mismatch")
    if (
        occurrence_audit["source_attestation_verification_hash"]
        != attestation_document["verification_hash"]
        or occurrence_audit["source_attestation_hash"]
        != attestation_receipt["attestation_hash"]
        or occurrence_audit["source_lifecycle_replay_verification_hash"]
        != lifecycle_replay_document["verification_hash"]
        or occurrence_audit["future_evaluation_id_hash"]
        != composition_document["future_evaluation_id_hash"]
    ):
        raise ValueError("content_issuance_replay_occurrence_source_mismatch")

    source_replay_audit_issued = _utc(
        source_replay_occurrence_audit["audit_issued_at_utc"],
        "source_lifecycle_replay_audit_issued_at_utc",
    )
    declared = _utc(replay_registration["declared_at_utc"], "declared_at_utc")
    checkpoint_issued = _utc(
        checkpoint["issued_at_utc"],
        "content_issuance_checkpoint_issued_at_utc",
    )
    scan_completed = _utc(
        occurrence_audit["scan_completed_at_utc"],
        "content_issuance_scan_completed_at_utc",
    )
    audit_issued = _utc(
        occurrence_audit["audit_issued_at_utc"],
        "content_issuance_audit_issued_at_utc",
    )
    reference_time = _utc(reference_time_utc, "reference_time_utc")
    if (
        reference_time_utc != lifecycle_replay_document["reference_time_utc"]
        or reference_time_utc != occurrence_audit["reference_time_utc"]
        or not source_replay_audit_issued
        <= declared
        <= checkpoint_issued
        <= scan_completed
        <= audit_issued
        <= reference_time
    ):
        raise ValueError("content_issuance_replay_reference_time_mismatch")
    if (
        (reference_time - checkpoint_issued).total_seconds()
        > replay_registration["max_checkpoint_age_seconds"]
    ):
        raise ValueError("content_issuance_replay_checkpoint_age_exceeded")
    if (
        (reference_time - scan_completed).total_seconds()
        > replay_registration["max_scan_age_seconds"]
    ):
        raise ValueError("content_issuance_replay_scan_age_exceeded")
    if (
        (audit_issued - scan_completed).total_seconds()
        > replay_registration["max_occurrence_receipt_issue_delay_seconds"]
    ):
        raise ValueError(
            "content_issuance_replay_occurrence_issue_delay_exceeded"
        )

    facts = {
        "source_dataset_content_attestation_reverified": True,
        "source_dataset_key_lifecycle_replay_reverified": True,
        "provider_dataset_key_lineage_bound": True,
        "future_evaluation_identity_bound": True,
        "content_replay_namespace_separated": True,
        "existing_replay_registry_key_role_reused": True,
        "existing_occurrence_auditor_key_role_reused": True,
        "checkpoint_signature_verified": True,
        "content_identity_inclusion_verified": True,
        "append_only_consistency_verified": True,
        "occurrence_audit_signature_verified": True,
        "complete_scan_claim_verified": True,
        "exactly_one_content_identity_occurrence_claim_verified": True,
        "index_snapshot_matches_checkpoint_root": True,
        "checkpoint_and_scan_window_verified": True,
        "external_content_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "external_provider_data_issuance_verified": False,
        "durable_checkpoint_publication_verified": False,
        "global_content_issuance_uniqueness_verified": False,
        "runtime_consumption_replay_enforcement_verified": False,
        "future_replay_absence_verified": False,
        "observation_admission_allowed": False,
        "profitability_verified": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "observation_admission_allowed": False,
        "provider_dataset_attestation_use_allowed": False,
        "replay_absence_verified": False,
        "global_uniqueness_verified": False,
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
        "source_attestation_hash": attestation_receipt["attestation_hash"],
        "source_composition_hash": composition_document["composition_hash"],
        "future_evaluation_id_hash": composition_document[
            "future_evaluation_id_hash"
        ],
        "source_lifecycle_replay_verification_hash": (
            lifecycle_replay_document["verification_hash"]
        ),
        "source_lifecycle_replay_registration_hash": (
            lifecycle_replay_document["replay_registration_hash"]
        ),
        "content_replay_registration_hash": replay_registration[
            "registration_hash"
        ],
        "pinned_checkpoint_hash": pinned_checkpoint["pin_hash"],
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "occurrence_audit_hash": occurrence_audit["occurrence_audit_hash"],
        "content_issuance_leaf_hash": expected_leaf_hash,
        "provider_id_hash": attestation_document["provider_id_hash"],
        "provider_dataset_key_id": attestation_document[
            "provider_dataset_key_id"
        ],
        "replay_registry_id": replay_registration["replay_registry_id"],
        "content_replay_registry_namespace": replay_registration[
            "content_replay_registry_namespace"
        ],
        "checkpoint_tree_size": checkpoint["tree_size"],
        "checkpoint_root_hash": checkpoint["root_hash"],
        "previous_checkpoint_tree_size": pinned_checkpoint["tree_size"],
        "previous_checkpoint_root_hash": pinned_checkpoint["root_hash"],
        "occurrence_leaf_index": occurrence_index,
        "occurrence_count_claim": occurrence_audit["occurrence_count"],
        "scan_completed_at_utc": occurrence_audit["scan_completed_at_utc"],
        "checkpoint_issued_at_utc": checkpoint["issued_at_utc"],
        "reference_time_utc": reference_time_utc,
        "replay_registry_signature_sha256": checkpoint["signature_sha256"],
        "occurrence_auditor_signature_sha256": occurrence_audit[
            "signature_sha256"
        ],
        "facts": facts,
        "blockers": [
            "external_content_replay_registry_authority_unproven",
            "external_occurrence_auditor_authority_unproven",
            "external_provider_data_issuance_unproven",
            "durable_checkpoint_publication_unproven",
            "global_content_issuance_uniqueness_unproven",
            "runtime_consumption_replay_enforcement_missing",
            "future_replay_absence_unproven",
            "observation_admission_locked",
        ],
        "authority": authority,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "verification_hash": _sha256(body)}


def verify_provider_dataset_content_issuance_replay_gate_v1(
    document: Any,
    attestation_document: Any,
    attestation_context: Any,
    lifecycle_replay_document: Any,
    lifecycle_replay_context: Any,
    replay_registration: Any,
    pinned_checkpoint: Any,
    checkpoint: Any,
    inclusion_proof: Any,
    consistency_proof: Any,
    occurrence_audit: Any,
    *,
    expected_registration_hash: Any,
    expected_pinned_checkpoint_hash: Any,
    expected_checkpoint_hash: Any,
    expected_occurrence_audit_hash: Any,
    reference_time_utc: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = evaluate_provider_dataset_content_issuance_replay_gate_v1(
            attestation_document,
            attestation_context,
            lifecycle_replay_document,
            lifecycle_replay_context,
            replay_registration,
            pinned_checkpoint,
            checkpoint,
            inclusion_proof,
            consistency_proof,
            occurrence_audit,
            expected_registration_hash=expected_registration_hash,
            expected_pinned_checkpoint_hash=expected_pinned_checkpoint_hash,
            expected_checkpoint_hash=expected_checkpoint_hash,
            expected_occurrence_audit_hash=expected_occurrence_audit_hash,
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
