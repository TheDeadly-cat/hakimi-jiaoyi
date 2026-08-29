from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

from . import strategy_correlation_provider_dataset_key_lifecycle_gate_v1 as lifecycle_source
from .execution_authority import authority_violations

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised by dependency-absence tests
    InvalidSignature = Exception  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment]


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-replay-registration-v1"
)
PINNED_CHECKPOINT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-replay-pinned-checkpoint-v1"
)
CHECKPOINT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-replay-checkpoint-v1"
)
OCCURRENCE_AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-replay-occurrence-audit-v1"
)
SCHEMA_VERSION = (
    "strategy-correlation-provider-dataset-key-lifecycle-replay-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-dataset-key-lifecycle-replay-gate-1"
)
REPLAY_REGISTRY_KEY_ROLE = "PROVIDER_DATASET_KEY_LIFECYCLE_REPLAY_REGISTRY"
OCCURRENCE_AUDITOR_KEY_ROLE = (
    "PROVIDER_DATASET_KEY_LIFECYCLE_OCCURRENCE_AUDITOR"
)
SIGNATURE_ALGORITHM = "ED25519"
RECEIPT_ENCODING = "RFC8785_JCS_UTF8"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
LOG_PROTOCOL = "DOMAIN_SEPARATED_BINARY_MERKLE_APPEND_ONLY_V1"
SCAN_POLICY = "FULL_PINNED_CHECKPOINT_INDEX_SCAN_V1"
CARDINALITY_POLICY = "EXACTLY_ONE_OCCURRENCE_CLAIM_V1"
EMPTY_DOMAIN = "hakimi.strategy-correlation.dataset-key-lifecycle-replay.empty.v1"
LEAF_DOMAIN = "hakimi.strategy-correlation.dataset-key-lifecycle-replay.leaf.v1"
NODE_DOMAIN = "hakimi.strategy-correlation.dataset-key-lifecycle-replay.node.v1"
CHECKPOINT_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.dataset-key-lifecycle-replay.checkpoint.v1"
)
OCCURRENCE_SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.dataset-key-lifecycle-replay.occurrence.v1"
)
GENESIS_COMMITMENT = "GENESIS"
GENESIS_ROOT_HASH = hashlib.sha256(
    (EMPTY_DOMAIN + "\x00").encode("ascii")
).hexdigest()
VERIFICATION_STATE = (
    "SIGNED_APPEND_ONLY_CHECKPOINT_INCLUSION_AND_EXACTLY_ONE_OCCURRENCE_"
    "CLAIM_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN"
)

_MAX_TREE_SIZE = (1 << 63) - 1
_MAX_PROOF_LENGTH = 128
_MAX_FRESHNESS_SECONDS = 366 * 24 * 60 * 60
_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{2,127}$")
_LIFECYCLE_CONTEXT_KEYS = {
    "attestation_document",
    "attestation_context",
    "lifecycle_registration",
    "governance_public_key_base64",
    "lifecycle_receipt",
    "expected_registration_hash",
    "expected_lifecycle_receipt_hash",
    "reference_time_utc",
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


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = _MAX_TREE_SIZE) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _strict_freshness(value: Any) -> bool:
    return _strict_int(value, minimum=1, maximum=_MAX_FRESHNESS_SECONDS)


def _proof(value: Any) -> list[str] | None:
    if (
        type(value) is not list
        or len(value) > _MAX_PROOF_LENGTH
        or not all(_valid_sha256(item) for item in value)
    ):
        return None
    return list(value)


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


def hash_lifecycle_replay_leaf_v1(lifecycle_receipt_hash: str) -> str:
    if not _valid_sha256(lifecycle_receipt_hash):
        raise ValueError("lifecycle_receipt_hash_invalid")
    payload = (
        LEAF_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(lifecycle_receipt_hash)
    )
    return hashlib.sha256(payload).hexdigest()


def hash_lifecycle_replay_node_v1(left_hash: str, right_hash: str) -> str:
    if not _valid_sha256(left_hash) or not _valid_sha256(right_hash):
        raise ValueError("lifecycle_replay_node_hash_invalid")
    payload = (
        NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left_hash)
        + bytes.fromhex(right_hash)
    )
    return hashlib.sha256(payload).hexdigest()


def _verify_inclusion(
    *,
    lifecycle_receipt_hash: str,
    leaf_index: int,
    tree_size: int,
    root_hash: str,
    proof: list[str],
) -> bool:
    if not 0 <= leaf_index < tree_size:
        return False
    fn = leaf_index
    sn = tree_size - 1
    running = hash_lifecycle_replay_leaf_v1(lifecycle_receipt_hash)
    for sibling in proof:
        if sn == 0:
            return False
        if fn == sn or (fn & 1) == 1:
            running = hash_lifecycle_replay_node_v1(sibling, running)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            running = hash_lifecycle_replay_node_v1(running, sibling)
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
            first_root = hash_lifecycle_replay_node_v1(sibling, first_root)
            second_root = hash_lifecycle_replay_node_v1(sibling, second_root)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            second_root = hash_lifecycle_replay_node_v1(second_root, sibling)
        fn >>= 1
        sn >>= 1

    return (
        fn == 0
        and sn == 0
        and first_root == old_root
        and second_root == new_root
    )


def _lifecycle_verified(document: Any, context: Any) -> bool:
    if type(context) is not dict or set(context) != _LIFECYCLE_CONTEXT_KEYS:
        return False
    try:
        return lifecycle_source.verify_provider_dataset_key_lifecycle_gate_v1(
            document,
            context["attestation_document"],
            context["attestation_context"],
            context["lifecycle_registration"],
            context["governance_public_key_base64"],
            context["lifecycle_receipt"],
            expected_registration_hash=context["expected_registration_hash"],
            expected_lifecycle_receipt_hash=context[
                "expected_lifecycle_receipt_hash"
            ],
            reference_time_utc=context["reference_time_utc"],
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
    lifecycle_document: Any,
    lifecycle_context: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not _lifecycle_verified(lifecycle_document, lifecycle_context):
        raise ValueError("lifecycle_replay_source_invalid")
    if (
        type(lifecycle_document) is not dict
        or lifecycle_document.get("schema_version") != lifecycle_source.SCHEMA_VERSION
        or lifecycle_document.get("static_fingerprint")
        != lifecycle_source.STATIC_FINGERPRINT
        or lifecycle_document.get("status") != "PASS"
        or lifecycle_document.get("verification_state")
        != lifecycle_source.VERIFICATION_STATE
        or lifecycle_document.get("permissions") != _PERMISSIONS
        or lifecycle_document.get("current_writer_activation_allowed") is not False
        or lifecycle_document.get("current_admission_allowed") is not False
        or lifecycle_document.get("facts", {}).get(
            "lifecycle_receipt_replay_registry_checked"
        )
        is not False
    ):
        raise ValueError("lifecycle_replay_source_contract_mismatch")
    lifecycle_registration = lifecycle_context.get("lifecycle_registration")
    lifecycle_receipt = lifecycle_context.get("lifecycle_receipt")
    attestation_context = lifecycle_context.get("attestation_context")
    if (
        type(lifecycle_registration) is not dict
        or type(lifecycle_receipt) is not dict
        or type(attestation_context) is not dict
        or lifecycle_registration.get("registration_hash")
        != lifecycle_document.get("lifecycle_registration_hash")
        or lifecycle_receipt.get("lifecycle_receipt_hash")
        != lifecycle_document.get("lifecycle_governance_receipt_hash")
        or lifecycle_registration.get("governance_public_key_sha256")
        != lifecycle_document.get("governance_public_key_sha256")
        or lifecycle_document.get("reference_time_utc")
        != lifecycle_context.get("reference_time_utc")
    ):
        raise ValueError("lifecycle_replay_source_lineage_mismatch")
    attestation_registration = attestation_context.get("registration")
    if type(attestation_registration) is not dict:
        raise ValueError("lifecycle_replay_attestation_registration_invalid")
    return lifecycle_registration, lifecycle_receipt, attestation_registration


def build_provider_dataset_key_lifecycle_replay_registration_v1(
    lifecycle_document: dict[str, Any],
    lifecycle_context: dict[str, Any],
    *,
    replay_registry_id: str,
    replay_registry_namespace: str,
    adapter_id: str,
    adapter_implementation_hash: str,
    replay_registry_key_id: str,
    replay_registry_public_key_base64: str,
    occurrence_auditor_id: str,
    occurrence_auditor_key_id: str,
    occurrence_auditor_public_key_base64: str,
    declared_at_utc: str,
    max_checkpoint_age_seconds: int,
    max_scan_age_seconds: int,
    max_occurrence_receipt_issue_delay_seconds: int,
) -> dict[str, Any]:
    if _authority_invalid([lifecycle_document, lifecycle_context]):
        raise ValueError("lifecycle_replay_registration_authority_invalid")
    lifecycle_registration, lifecycle_receipt, attestation_registration = (
        _source_contract(lifecycle_document, lifecycle_context)
    )
    identifiers = (
        replay_registry_id,
        replay_registry_namespace,
        adapter_id,
        replay_registry_key_id,
        occurrence_auditor_id,
        occurrence_auditor_key_id,
    )
    if not all(_strict_id(value) for value in identifiers):
        raise ValueError("lifecycle_replay_identifier_invalid")
    role_ids = {
        lifecycle_registration["provider_dataset_key_id"],
        lifecycle_registration["governance_key_id"],
        replay_registry_key_id,
        occurrence_auditor_key_id,
    }
    if len(role_ids) != 4:
        raise ValueError("lifecycle_replay_key_id_role_collision")
    if not _valid_sha256(adapter_implementation_hash):
        raise ValueError("lifecycle_replay_adapter_implementation_hash_invalid")

    replay_registry_key = _decode_base64(
        replay_registry_public_key_base64,
        32,
        "replay_registry_public_key",
    )
    occurrence_auditor_key = _decode_base64(
        occurrence_auditor_public_key_base64,
        32,
        "occurrence_auditor_public_key",
    )
    replay_registry_key_hash = hashlib.sha256(replay_registry_key).hexdigest()
    occurrence_auditor_key_hash = hashlib.sha256(
        occurrence_auditor_key
    ).hexdigest()
    upstream_key_hashes = {
        lifecycle_registration.get("provider_dataset_public_key_sha256"),
        lifecycle_registration.get("governance_public_key_sha256"),
        attestation_registration.get("identity_registry_public_key_sha256"),
        attestation_registration.get("timestamp_adapter_public_key_sha256"),
    }
    if (
        len(upstream_key_hashes) != 4
        or not all(_valid_sha256(value) for value in upstream_key_hashes)
    ):
        raise ValueError("lifecycle_replay_upstream_key_roles_invalid")
    if (
        replay_registry_key_hash in upstream_key_hashes
        or occurrence_auditor_key_hash in upstream_key_hashes
        or replay_registry_key_hash == occurrence_auditor_key_hash
    ):
        raise ValueError("lifecycle_replay_public_key_role_collision")
    freshness_values = (
        max_checkpoint_age_seconds,
        max_scan_age_seconds,
        max_occurrence_receipt_issue_delay_seconds,
    )
    if not all(_strict_freshness(value) for value in freshness_values):
        raise ValueError("lifecycle_replay_freshness_policy_invalid")
    source_declared = _utc(
        lifecycle_registration.get("declared_at_utc"),
        "source_lifecycle_declared_at_utc",
    )
    source_receipt_issued = _utc(
        lifecycle_receipt.get("issued_at_utc"),
        "source_lifecycle_receipt_issued_at_utc",
    )
    declared = _utc(declared_at_utc, "declared_at_utc")
    if not source_declared <= declared <= source_receipt_issued:
        raise ValueError("lifecycle_replay_registration_time_invalid")

    facts = {
        "source_lifecycle_gate_reverified": True,
        "source_lifecycle_receipt_bound": True,
        "replay_registry_key_role_separation_verified": True,
        "occurrence_auditor_key_role_separation_verified": True,
        "append_only_protocol_preregistered": True,
        "full_scan_cardinality_policy_preregistered": True,
        "external_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "durable_checkpoint_publication_verified": False,
        "replay_gate_use_allowed": False,
    }
    authority = {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
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
            "LIFECYCLE_REPLAY_CONSUMER_REGISTERED_EXTERNAL_REGISTRY_UNPROVEN"
        ),
        "source_lifecycle_schema": lifecycle_source.SCHEMA_VERSION,
        "source_lifecycle_verification_hash": lifecycle_document[
            "verification_hash"
        ],
        "source_lifecycle_registration_hash": lifecycle_document[
            "lifecycle_registration_hash"
        ],
        "source_lifecycle_receipt_hash": lifecycle_document[
            "lifecycle_governance_receipt_hash"
        ],
        "source_lifecycle_receipt_issued_at_utc": lifecycle_receipt[
            "issued_at_utc"
        ],
        "source_lifecycle_reference_time_utc": lifecycle_document[
            "reference_time_utc"
        ],
        "provider_id_hash": lifecycle_document["provider_id_hash"],
        "provider_dataset_key_id": lifecycle_document[
            "provider_dataset_key_id"
        ],
        "provider_dataset_public_key_sha256": lifecycle_document[
            "provider_dataset_public_key_sha256"
        ],
        "replay_registry_id": replay_registry_id,
        "replay_registry_namespace": replay_registry_namespace,
        "adapter_id": adapter_id,
        "adapter_implementation_hash": adapter_implementation_hash,
        "replay_registry_key_role": REPLAY_REGISTRY_KEY_ROLE,
        "replay_registry_key_id": replay_registry_key_id,
        "replay_registry_public_key_sha256": replay_registry_key_hash,
        "occurrence_auditor_id": occurrence_auditor_id,
        "occurrence_auditor_key_role": OCCURRENCE_AUDITOR_KEY_ROLE,
        "occurrence_auditor_key_id": occurrence_auditor_key_id,
        "occurrence_auditor_public_key_sha256": occurrence_auditor_key_hash,
        "excluded_upstream_key_count": 4,
        "log_protocol": LOG_PROTOCOL,
        "scan_policy": SCAN_POLICY,
        "cardinality_policy": CARDINALITY_POLICY,
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


def verify_provider_dataset_key_lifecycle_replay_registration_v1(
    document: Any,
    lifecycle_document: Any,
    lifecycle_context: Any,
    replay_registry_public_key_base64: Any,
    occurrence_auditor_public_key_base64: Any,
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
        rebuilt = build_provider_dataset_key_lifecycle_replay_registration_v1(
            lifecycle_document,
            lifecycle_context,
            replay_registry_id=document["replay_registry_id"],
            replay_registry_namespace=document["replay_registry_namespace"],
            adapter_id=document["adapter_id"],
            adapter_implementation_hash=document["adapter_implementation_hash"],
            replay_registry_key_id=document["replay_registry_key_id"],
            replay_registry_public_key_base64=(
                replay_registry_public_key_base64
            ),
            occurrence_auditor_id=document["occurrence_auditor_id"],
            occurrence_auditor_key_id=document["occurrence_auditor_key_id"],
            occurrence_auditor_public_key_base64=(
                occurrence_auditor_public_key_base64
            ),
            declared_at_utc=document["declared_at_utc"],
            max_checkpoint_age_seconds=document["max_checkpoint_age_seconds"],
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


_PINNED_CHECKPOINT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "replay_registry_id",
    "replay_registry_namespace",
    "tree_size",
    "root_hash",
    "checkpoint_hash",
    "pin_hash",
}


def build_pinned_lifecycle_replay_checkpoint_v1(
    registration: dict[str, Any],
    *,
    tree_size: int,
    root_hash: str,
    checkpoint_hash: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or not _valid_sha256(registration.get("registration_hash"))
    ):
        raise ValueError("lifecycle_replay_registration_contract_invalid")
    if not _strict_int(tree_size, maximum=_MAX_TREE_SIZE):
        raise ValueError("pinned_checkpoint_tree_size_invalid")
    if not _valid_sha256(root_hash):
        raise ValueError("pinned_checkpoint_root_hash_invalid")
    if tree_size == 0:
        if root_hash != GENESIS_ROOT_HASH or checkpoint_hash != GENESIS_COMMITMENT:
            raise ValueError("pinned_checkpoint_genesis_invalid")
    elif not _valid_sha256(checkpoint_hash):
        raise ValueError("pinned_checkpoint_hash_invalid")
    body = {
        "schema_version": PINNED_CHECKPOINT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
        "tree_size": tree_size,
        "root_hash": root_hash,
        "checkpoint_hash": checkpoint_hash,
    }
    return {**body, "pin_hash": _sha256(body)}


_UNSIGNED_CHECKPOINT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "replay_registry_id",
    "replay_registry_namespace",
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


def build_unsigned_lifecycle_replay_checkpoint_v1(
    registration: dict[str, Any],
    pinned_checkpoint: dict[str, Any],
    *,
    tree_size: int,
    root_hash: str,
    issued_at_utc: str,
) -> dict[str, Any]:
    if (
        type(registration) is not dict
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or type(pinned_checkpoint) is not dict
        or set(pinned_checkpoint) != _PINNED_CHECKPOINT_KEYS
        or pinned_checkpoint.get("schema_version")
        != PINNED_CHECKPOINT_SCHEMA_VERSION
        or pinned_checkpoint.get("registration_hash")
        != registration.get("registration_hash")
    ):
        raise ValueError("lifecycle_replay_checkpoint_source_invalid")
    pin_body = {
        key: value
        for key, value in pinned_checkpoint.items()
        if key != "pin_hash"
    }
    if pinned_checkpoint["pin_hash"] != _sha256(pin_body):
        raise ValueError("pinned_checkpoint_seal_invalid")
    if (
        not _strict_int(tree_size, minimum=1, maximum=_MAX_TREE_SIZE)
        or tree_size <= pinned_checkpoint["tree_size"]
    ):
        raise ValueError("lifecycle_replay_checkpoint_tree_size_invalid")
    if not _valid_sha256(root_hash):
        raise ValueError("lifecycle_replay_checkpoint_root_hash_invalid")
    _utc(issued_at_utc, "checkpoint_issued_at_utc")
    body = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
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


def assemble_lifecycle_replay_checkpoint_v1(
    unsigned_checkpoint: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    return _assemble_signed_receipt(
        unsigned_checkpoint,
        _UNSIGNED_CHECKPOINT_KEYS,
        signature_base64,
        signature_label="lifecycle_replay_checkpoint_signature",
        receipt_hash_field="checkpoint_hash",
    )


_CHECKPOINT_KEYS = _UNSIGNED_CHECKPOINT_KEYS | {
    "signature_base64",
    "signature_sha256",
    "checkpoint_hash",
}


_UNSIGNED_AUDIT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_hash",
    "source_lifecycle_verification_hash",
    "source_lifecycle_receipt_hash",
    "replay_registry_id",
    "replay_registry_namespace",
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
    "signature_algorithm",
    "receipt_encoding",
    "signature_message_format",
    "signature_domain",
    "receipt_content_sha256",
}


def build_unsigned_lifecycle_replay_occurrence_audit_v1(
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
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or type(checkpoint) is not dict
        or set(checkpoint) != _CHECKPOINT_KEYS
        or checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION
        or checkpoint.get("registration_hash")
        != registration.get("registration_hash")
        or not _valid_sha256(checkpoint.get("checkpoint_hash"))
    ):
        raise ValueError("lifecycle_replay_occurrence_source_invalid")
    inclusion = _proof(inclusion_proof)
    consistency = _proof(consistency_proof)
    if inclusion is None or consistency is None:
        raise ValueError("lifecycle_replay_occurrence_proof_invalid")
    tree_size = checkpoint["tree_size"]
    integer_values = (
        occurrence_leaf_index,
        scan_start_index,
        scan_end_index_exclusive,
        index_snapshot_record_count,
        occurrence_count,
    )
    if not all(_strict_int(value, maximum=_MAX_TREE_SIZE) for value in integer_values):
        raise ValueError("lifecycle_replay_occurrence_integer_invalid")
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
        raise ValueError("lifecycle_replay_occurrence_cardinality_shape_invalid")
    if not _valid_sha256(index_snapshot_root_hash):
        raise ValueError("lifecycle_replay_index_snapshot_root_hash_invalid")
    checkpoint_issued = _utc(
        checkpoint["issued_at_utc"],
        "checkpoint_issued_at_utc",
    )
    scan_completed = _utc(scan_completed_at_utc, "scan_completed_at_utc")
    audit_issued = _utc(audit_issued_at_utc, "audit_issued_at_utc")
    reference_time = _utc(reference_time_utc, "reference_time_utc")
    if not checkpoint_issued <= scan_completed <= audit_issued <= reference_time:
        raise ValueError("lifecycle_replay_occurrence_time_order_invalid")
    body = {
        "schema_version": OCCURRENCE_AUDIT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registration["registration_hash"],
        "source_lifecycle_verification_hash": registration[
            "source_lifecycle_verification_hash"
        ],
        "source_lifecycle_receipt_hash": registration[
            "source_lifecycle_receipt_hash"
        ],
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
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
        "occurrence_auditor_key_id": registration["occurrence_auditor_key_id"],
        "occurrence_auditor_public_key_sha256": registration[
            "occurrence_auditor_public_key_sha256"
        ],
        "scan_policy": SCAN_POLICY,
        "cardinality_policy": CARDINALITY_POLICY,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "receipt_encoding": RECEIPT_ENCODING,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": OCCURRENCE_SIGNATURE_DOMAIN,
    }
    return {**body, "receipt_content_sha256": _sha256(body)}


def assemble_lifecycle_replay_occurrence_audit_v1(
    unsigned_audit: dict[str, Any],
    signature_base64: str,
) -> dict[str, Any]:
    return _assemble_signed_receipt(
        unsigned_audit,
        _UNSIGNED_AUDIT_KEYS,
        signature_base64,
        signature_label="lifecycle_replay_occurrence_signature",
        receipt_hash_field="occurrence_audit_hash",
    )


_AUDIT_KEYS = _UNSIGNED_AUDIT_KEYS | {
    "signature_base64",
    "signature_sha256",
    "occurrence_audit_hash",
}


def _verify_signature(
    *,
    public_key_base64: Any,
    expected_public_key_hash: str,
    signature_base64: Any,
    receipt_content_sha256: str,
    label: str,
) -> None:
    public_key = _decode_base64(public_key_base64, 32, f"{label}_public_key")
    if (
        hashlib.sha256(public_key).hexdigest() != expected_public_key_hash
        or Ed25519PublicKey is None
    ):
        raise ValueError(f"{label}_public_key_invalid")
    signature = _decode_base64(signature_base64, 64, f"{label}_signature")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            bytes.fromhex(receipt_content_sha256),
        )
    except (InvalidSignature, ValueError) as error:
        raise ValueError(f"{label}_signature_invalid") from error


def evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
    lifecycle_document: dict[str, Any],
    lifecycle_context: dict[str, Any],
    replay_registration: dict[str, Any],
    replay_registry_public_key_base64: str,
    occurrence_auditor_public_key_base64: str,
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
        [lifecycle_document, lifecycle_context, replay_registration]
    ):
        raise ValueError("lifecycle_replay_gate_authority_invalid")
    _, source_lifecycle_receipt, _ = _source_contract(
        lifecycle_document,
        lifecycle_context,
    )
    if not verify_provider_dataset_key_lifecycle_replay_registration_v1(
        replay_registration,
        lifecycle_document,
        lifecycle_context,
        replay_registry_public_key_base64,
        occurrence_auditor_public_key_base64,
        expected_registration_hash=expected_registration_hash,
    ):
        raise ValueError("lifecycle_replay_registration_invalid")
    if (
        type(pinned_checkpoint) is not dict
        or set(pinned_checkpoint) != _PINNED_CHECKPOINT_KEYS
        or not _valid_sha256(expected_pinned_checkpoint_hash)
        or pinned_checkpoint.get("pin_hash") != expected_pinned_checkpoint_hash
    ):
        raise ValueError("lifecycle_replay_pinned_checkpoint_invalid")
    expected_pin = build_pinned_lifecycle_replay_checkpoint_v1(
        replay_registration,
        tree_size=pinned_checkpoint["tree_size"],
        root_hash=pinned_checkpoint["root_hash"],
        checkpoint_hash=pinned_checkpoint["checkpoint_hash"],
    )
    if pinned_checkpoint != expected_pin:
        raise ValueError("lifecycle_replay_pinned_checkpoint_seal_invalid")
    if (
        type(checkpoint) is not dict
        or set(checkpoint) != _CHECKPOINT_KEYS
        or not _valid_sha256(expected_checkpoint_hash)
        or checkpoint.get("checkpoint_hash") != expected_checkpoint_hash
    ):
        raise ValueError("lifecycle_replay_checkpoint_invalid")
    unsigned_checkpoint = build_unsigned_lifecycle_replay_checkpoint_v1(
        replay_registration,
        pinned_checkpoint,
        tree_size=checkpoint["tree_size"],
        root_hash=checkpoint["root_hash"],
        issued_at_utc=checkpoint["issued_at_utc"],
    )
    rebuilt_checkpoint = assemble_lifecycle_replay_checkpoint_v1(
        unsigned_checkpoint,
        checkpoint["signature_base64"],
    )
    if checkpoint != rebuilt_checkpoint:
        raise ValueError("lifecycle_replay_checkpoint_seal_invalid")
    _verify_signature(
        public_key_base64=replay_registry_public_key_base64,
        expected_public_key_hash=replay_registration[
            "replay_registry_public_key_sha256"
        ],
        signature_base64=checkpoint["signature_base64"],
        receipt_content_sha256=checkpoint["receipt_content_sha256"],
        label="lifecycle_replay_checkpoint",
    )
    inclusion = _proof(inclusion_proof)
    consistency = _proof(consistency_proof)
    if inclusion is None or consistency is None:
        raise ValueError("lifecycle_replay_proof_invalid")
    source_receipt_hash = source_lifecycle_receipt["lifecycle_receipt_hash"]
    if not _verify_inclusion(
        lifecycle_receipt_hash=source_receipt_hash,
        leaf_index=occurrence_audit.get("occurrence_leaf_index", -1),
        tree_size=checkpoint["tree_size"],
        root_hash=checkpoint["root_hash"],
        proof=inclusion,
    ):
        raise ValueError("lifecycle_replay_inclusion_proof_invalid")
    if not _verify_consistency(
        old_size=pinned_checkpoint["tree_size"],
        new_size=checkpoint["tree_size"],
        old_root=pinned_checkpoint["root_hash"],
        new_root=checkpoint["root_hash"],
        proof=consistency,
    ):
        raise ValueError("lifecycle_replay_consistency_proof_invalid")
    if (
        type(occurrence_audit) is not dict
        or set(occurrence_audit) != _AUDIT_KEYS
        or not _valid_sha256(expected_occurrence_audit_hash)
        or occurrence_audit.get("occurrence_audit_hash")
        != expected_occurrence_audit_hash
    ):
        raise ValueError("lifecycle_replay_occurrence_audit_invalid")
    unsigned_audit = build_unsigned_lifecycle_replay_occurrence_audit_v1(
        replay_registration,
        checkpoint,
        inclusion,
        consistency,
        occurrence_leaf_index=occurrence_audit["occurrence_leaf_index"],
        scan_start_index=occurrence_audit["scan_start_index"],
        scan_end_index_exclusive=occurrence_audit[
            "scan_end_index_exclusive"
        ],
        index_snapshot_record_count=occurrence_audit[
            "index_snapshot_record_count"
        ],
        occurrence_count=occurrence_audit["occurrence_count"],
        occurrence_leaf_indices=occurrence_audit["occurrence_leaf_indices"],
        index_snapshot_root_hash=occurrence_audit[
            "index_snapshot_root_hash"
        ],
        scan_completed_at_utc=occurrence_audit["scan_completed_at_utc"],
        audit_issued_at_utc=occurrence_audit["audit_issued_at_utc"],
        reference_time_utc=occurrence_audit["reference_time_utc"],
    )
    rebuilt_audit = assemble_lifecycle_replay_occurrence_audit_v1(
        unsigned_audit,
        occurrence_audit["signature_base64"],
    )
    if occurrence_audit != rebuilt_audit:
        raise ValueError("lifecycle_replay_occurrence_audit_seal_invalid")
    _verify_signature(
        public_key_base64=occurrence_auditor_public_key_base64,
        expected_public_key_hash=replay_registration[
            "occurrence_auditor_public_key_sha256"
        ],
        signature_base64=occurrence_audit["signature_base64"],
        receipt_content_sha256=occurrence_audit["receipt_content_sha256"],
        label="lifecycle_replay_occurrence",
    )
    occurrence_index = occurrence_audit["occurrence_leaf_index"]
    if (
        occurrence_audit["scan_start_index"] != 0
        or occurrence_audit["scan_end_index_exclusive"]
        != checkpoint["tree_size"]
        or occurrence_audit["index_snapshot_record_count"]
        != checkpoint["tree_size"]
    ):
        raise ValueError("lifecycle_replay_complete_scan_claim_invalid")
    if (
        occurrence_audit["occurrence_count"] != 1
        or occurrence_audit["occurrence_leaf_indices"] != [occurrence_index]
    ):
        raise ValueError("lifecycle_replay_exactly_one_occurrence_claim_invalid")
    if (
        occurrence_audit["source_lifecycle_verification_hash"]
        != lifecycle_document["verification_hash"]
        or occurrence_audit["source_lifecycle_receipt_hash"]
        != source_receipt_hash
    ):
        raise ValueError("lifecycle_replay_occurrence_source_mismatch")

    source_receipt_issued = _utc(
        source_lifecycle_receipt["issued_at_utc"],
        "source_lifecycle_receipt_issued_at_utc",
    )
    checkpoint_issued = _utc(
        checkpoint["issued_at_utc"],
        "checkpoint_issued_at_utc",
    )
    scan_completed = _utc(
        occurrence_audit["scan_completed_at_utc"],
        "scan_completed_at_utc",
    )
    audit_issued = _utc(
        occurrence_audit["audit_issued_at_utc"],
        "audit_issued_at_utc",
    )
    reference_time = _utc(reference_time_utc, "reference_time_utc")
    if (
        reference_time_utc != lifecycle_document["reference_time_utc"]
        or reference_time_utc != occurrence_audit["reference_time_utc"]
        or not source_receipt_issued
        <= checkpoint_issued
        <= scan_completed
        <= audit_issued
        <= reference_time
    ):
        raise ValueError("lifecycle_replay_reference_time_mismatch")
    if (
        (reference_time - checkpoint_issued).total_seconds()
        > replay_registration["max_checkpoint_age_seconds"]
    ):
        raise ValueError("lifecycle_replay_checkpoint_age_exceeded")
    if (
        (reference_time - scan_completed).total_seconds()
        > replay_registration["max_scan_age_seconds"]
    ):
        raise ValueError("lifecycle_replay_scan_age_exceeded")
    if (
        (audit_issued - scan_completed).total_seconds()
        > replay_registration["max_occurrence_receipt_issue_delay_seconds"]
    ):
        raise ValueError("lifecycle_replay_occurrence_issue_delay_exceeded")

    facts = {
        "source_lifecycle_gate_reverified": True,
        "source_lifecycle_receipt_bound": True,
        "source_lifecycle_replay_registry_checked": False,
        "replay_registry_key_role_separation_verified": True,
        "occurrence_auditor_key_role_separation_verified": True,
        "signed_replay_registry_evidence_checked": True,
        "checkpoint_signature_verified": True,
        "lifecycle_receipt_inclusion_verified": True,
        "append_only_consistency_verified": True,
        "occurrence_audit_signature_verified": True,
        "complete_scan_claim_verified": True,
        "exactly_one_occurrence_claim_verified": True,
        "checkpoint_and_scan_window_verified": True,
        "external_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "durable_checkpoint_publication_verified": False,
        "global_lifecycle_receipt_uniqueness_verified": False,
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
        "source_lifecycle_verification_hash": lifecycle_document[
            "verification_hash"
        ],
        "source_lifecycle_registration_hash": lifecycle_document[
            "lifecycle_registration_hash"
        ],
        "source_lifecycle_receipt_hash": source_receipt_hash,
        "replay_registration_hash": replay_registration["registration_hash"],
        "pinned_checkpoint_hash": pinned_checkpoint["pin_hash"],
        "checkpoint_hash": checkpoint["checkpoint_hash"],
        "occurrence_audit_hash": occurrence_audit["occurrence_audit_hash"],
        "provider_id_hash": lifecycle_document["provider_id_hash"],
        "provider_dataset_key_id": lifecycle_document[
            "provider_dataset_key_id"
        ],
        "replay_registry_id": replay_registration["replay_registry_id"],
        "replay_registry_namespace": replay_registration[
            "replay_registry_namespace"
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
            "external_replay_registry_authority_unproven",
            "external_occurrence_auditor_authority_unproven",
            "durable_checkpoint_publication_unproven",
            "global_lifecycle_receipt_uniqueness_unproven",
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


def verify_provider_dataset_key_lifecycle_replay_gate_v1(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
            *args,
            **kwargs,
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
    "CARDINALITY_POLICY",
    "CHECKPOINT_SCHEMA_VERSION",
    "CHECKPOINT_SIGNATURE_DOMAIN",
    "EMPTY_DOMAIN",
    "GENESIS_COMMITMENT",
    "GENESIS_ROOT_HASH",
    "LEAF_DOMAIN",
    "LOG_PROTOCOL",
    "NODE_DOMAIN",
    "OCCURRENCE_AUDIT_SCHEMA_VERSION",
    "OCCURRENCE_AUDITOR_KEY_ROLE",
    "OCCURRENCE_SIGNATURE_DOMAIN",
    "PINNED_CHECKPOINT_SCHEMA_VERSION",
    "REGISTRATION_SCHEMA_VERSION",
    "REPLAY_REGISTRY_KEY_ROLE",
    "SCAN_POLICY",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_STATE",
    "assemble_lifecycle_replay_checkpoint_v1",
    "assemble_lifecycle_replay_occurrence_audit_v1",
    "build_pinned_lifecycle_replay_checkpoint_v1",
    "build_provider_dataset_key_lifecycle_replay_registration_v1",
    "build_unsigned_lifecycle_replay_checkpoint_v1",
    "build_unsigned_lifecycle_replay_occurrence_audit_v1",
    "evaluate_provider_dataset_key_lifecycle_replay_gate_v1",
    "hash_lifecycle_replay_leaf_v1",
    "hash_lifecycle_replay_node_v1",
    "verify_provider_dataset_key_lifecycle_replay_gate_v1",
    "verify_provider_dataset_key_lifecycle_replay_registration_v1",
]
