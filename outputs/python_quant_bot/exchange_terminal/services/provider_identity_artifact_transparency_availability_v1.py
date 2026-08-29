from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import provider_identity_auditor_provenance_suite_reproducibility_v1 as source_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 as replay_merkle_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA = "provider-identity-artifact-transparency-availability-registration-v1"
REGISTRATION_RECEIPT_SCHEMA = f"{REGISTRATION_SCHEMA}-receipt"
CHECKPOINT_SCHEMA = "provider-identity-artifact-transparency-checkpoint-v1"
OBSERVER_RECEIPT_SCHEMA = "provider-identity-artifact-availability-observer-receipt-v1"
EVALUATION_SCHEMA = "provider-identity-artifact-transparency-availability-evaluation-v1"
STATIC_FINGERPRINT = "20260822-provider-identity-artifact-transparency-availability-contract-1"
REGISTERED_STATUS = "ARTIFACT_TRANSPARENCY_AVAILABILITY_REGISTERED_RECEIPTS_UNOBSERVED"
VERIFIED_STATUS = (
    "LOCAL_ARTIFACT_CONTENT_AND_SIGNED_TRANSPARENCY_INCLUSION_DUAL_RETRIEVAL_"
    "CLAIMS_VERIFIED_EXTERNAL_LOG_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
LOG_PROTOCOL = "provider-identity-research-artifact-transparency-log-v1"
INCLUSION_PROOF_PROTOCOL = replay_merkle_contract.INCLUSION_PROOF_PROTOCOL
CONSISTENCY_PROOF_PROTOCOL = replay_merkle_contract.CONSISTENCY_PROOF_PROTOCOL
CONTENT_HASH_ALGORITHM = "sha256"
CONTENT_HASH_ENCODING = "lowercase-hex"
CONTENT_ENCODING = "base64url-no-padding"
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_ENCODING = "base64url-no-padding"
EMPTY_DOMAIN = "hakimi.provider-identity.artifact-transparency.empty.v1"
LEAF_DOMAIN = "hakimi.provider-identity.artifact-transparency.leaf.v1"
NODE_DOMAIN = "hakimi.provider-identity.artifact-transparency.node.v1"
CHECKPOINT_SIGNATURE_DOMAIN = "hakimi.provider-identity.artifact-transparency.checkpoint.v1"
OBSERVER_SIGNATURE_DOMAIN_PREFIX = "hakimi.provider-identity.artifact-availability-observer.v1"
RETRIEVAL_METHOD = "independent-content-addressed-fetch-v1"
GENESIS_ROOT_HASH = hashlib.sha256((EMPTY_DOMAIN + "\x00").encode("ascii")).hexdigest()
ROLE_ORDER = ("transparency_log", "observer_a", "observer_b")
OBSERVER_ROLES = frozenset({"observer_a", "observer_b"})
MAX_INT = 2**63 - 1
MAX_ARTIFACTS = 256
MAX_PROOF_LENGTH = 128
MAX_TOTAL_PAYLOAD_BYTES = 16 * 1024 * 1024

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:/+-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")

_ROLE_FIELDS = frozenset(
    {
        "role",
        "entity_id",
        "key_id",
        "public_key_hash",
        "organization_id",
        "control_group_id",
        "beneficial_owner_disclosure_hash",
        "retrieval_run_id",
    }
)
_ARTIFACT_FIELDS = frozenset(
    {
        "artifact_id",
        "artifact_kind",
        "content_hash",
        "size_bytes",
        "media_type",
        "locator_commitment_hash",
        "required",
    }
)
_PAYLOAD_FIELDS = frozenset({"artifact_id", "content_base64url"})
_CHECKPOINT_FIELDS = frozenset(
    {
        "schema",
        "log_id",
        "log_namespace",
        "tree_size",
        "root_hash",
        "issued_at_ms",
        "key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)
_INCLUSION_FIELDS = frozenset({"artifact_id", "leaf_index", "proof"})
_OBSERVER_RESULT_FIELDS = frozenset(
    {
        "artifact_id",
        "locator_commitment_hash",
        "retrieved_content_hash",
        "retrieved_size_bytes",
        "retrieval_succeeded",
    }
)
_OBSERVER_FIELDS = frozenset(
    {
        "schema",
        "registration_receipt_hash",
        "source_reproducibility_evaluation_receipt_hash",
        "artifact_catalog_root_hash",
        "transparency_checkpoint_hash",
        "observer_role",
        "observer_id",
        "observer_organization_id",
        "observer_control_group_id",
        "observer_key_id",
        "retrieval_run_id",
        "retrieval_method",
        "started_at_ms",
        "completed_at_ms",
        "issued_at_ms",
        "artifact_results",
        "result_count",
        "success_count",
        "failure_count",
        "result_transcript_root_hash",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)

_REGISTRATION_FIELDS = frozenset(
    {
        "schema",
        "adapter_id",
        "adapter_implementation_hash",
        "source_reproducibility_registration_receipt_schema",
        "source_reproducibility_evaluation_schema",
        "source_reproducibility_static_fingerprint",
        "source_reproducibility_registration_receipt_hash",
        "source_reproducibility_evaluation_receipt_hash",
        "role_registrations",
        "log_id",
        "log_namespace",
        "artifact_catalog_root_hash",
        "expected_artifact_count",
        "expected_total_payload_bytes",
        "max_artifact_payload_bytes",
        "pinned_checkpoint_tree_size",
        "pinned_checkpoint_root_hash",
        "log_protocol",
        "inclusion_proof_protocol",
        "consistency_proof_protocol",
        "content_hash_algorithm",
        "content_hash_encoding",
        "content_encoding",
        "checkpoint_schema",
        "observer_receipt_schema",
        "signature_algorithm",
        "signature_encoding",
        "empty_domain",
        "leaf_domain",
        "node_domain",
        "checkpoint_signature_domain",
        "observer_signature_domain_prefix",
        "retrieval_method",
        "genesis_root_hash",
        "max_checkpoint_age_ms",
        "max_observer_receipt_age_ms",
        "max_observer_retrieval_duration_ms",
        "max_receipt_issue_delay_ms",
    }
)

_REGISTRATION_CONSTANTS = {
    "schema": REGISTRATION_SCHEMA,
    "source_reproducibility_registration_receipt_schema": source_contract.REGISTRATION_RECEIPT_SCHEMA,
    "source_reproducibility_evaluation_schema": source_contract.EVALUATION_SCHEMA,
    "source_reproducibility_static_fingerprint": source_contract.STATIC_FINGERPRINT,
    "log_protocol": LOG_PROTOCOL,
    "inclusion_proof_protocol": INCLUSION_PROOF_PROTOCOL,
    "consistency_proof_protocol": CONSISTENCY_PROOF_PROTOCOL,
    "content_hash_algorithm": CONTENT_HASH_ALGORITHM,
    "content_hash_encoding": CONTENT_HASH_ENCODING,
    "content_encoding": CONTENT_ENCODING,
    "checkpoint_schema": CHECKPOINT_SCHEMA,
    "observer_receipt_schema": OBSERVER_RECEIPT_SCHEMA,
    "signature_algorithm": SIGNATURE_ALGORITHM,
    "signature_encoding": SIGNATURE_ENCODING,
    "empty_domain": EMPTY_DOMAIN,
    "leaf_domain": LEAF_DOMAIN,
    "node_domain": NODE_DOMAIN,
    "checkpoint_signature_domain": CHECKPOINT_SIGNATURE_DOMAIN,
    "observer_signature_domain_prefix": OBSERVER_SIGNATURE_DOMAIN_PREFIX,
    "retrieval_method": RETRIEVAL_METHOD,
    "genesis_root_hash": GENESIS_ROOT_HASH,
}


def _authority() -> dict[str, bool]:
    return {
        "research_only": True,
        "observation_admission_allowed": False,
        "parameter_selection_allowed": False,
        "promotion_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _registration_facts(registered: bool = False) -> dict[str, bool]:
    return {
        "artifact_scope_preregistered": registered,
        "log_and_observer_roles_separated": registered,
        "artifact_content_observed": False,
        "transparency_checkpoint_observed": False,
        "observer_receipts_observed": False,
        "public_artifact_availability_verified": False,
        "external_log_trust_attested": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _evaluation_facts() -> dict[str, bool]:
    return {
        "source_reproducibility_reverified": False,
        "source_and_new_roles_separated": False,
        "artifact_catalog_root_verified": False,
        "local_artifact_content_hashes_verified": False,
        "local_artifact_sizes_verified": False,
        "transparency_checkpoint_signature_verified": False,
        "all_artifact_inclusion_proofs_verified": False,
        "append_only_consistency_verified": False,
        "observer_a_signature_verified": False,
        "observer_b_signature_verified": False,
        "complete_dual_observer_retrieval_claims_verified": False,
        "dual_observer_result_agreement_verified": False,
        "external_log_trust_attested": False,
        "public_artifact_availability_verified": False,
        "external_persistence_verified": False,
        "external_time_truth_verified": False,
        "auditor_independence_verified": False,
        "suite_completeness_verified": False,
        "profitability_verified": False,
    }


def _registration_evidence() -> dict[str, Any]:
    return {
        "registration_hash": None,
        "source_reproducibility_registration_receipt_hash": None,
        "source_reproducibility_evaluation_receipt_hash": None,
        "artifact_catalog_root_hash": None,
        "expected_artifact_count": None,
        "expected_total_payload_bytes": None,
        "pinned_checkpoint_tree_size": None,
        "pinned_checkpoint_root_hash": None,
    }


def _evaluation_evidence() -> dict[str, Any]:
    return {
        "registration_receipt_hash": None,
        "source_reproducibility_evaluation_receipt_hash": None,
        "artifact_catalog_root_hash": None,
        "artifact_count": None,
        "total_payload_bytes": None,
        "transparency_checkpoint_hash": None,
        "checkpoint_tree_size": None,
        "checkpoint_root_hash": None,
        "observer_a_receipt_hash": None,
        "observer_b_receipt_hash": None,
        "observer_result_transcript_root_hash": None,
        "reference_time_ms": None,
    }


def _sealed_registration(
    *, status: str, reason: str | None, facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": REGISTRATION_RECEIPT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts if facts is not None else _registration_facts(),
            "evidence": evidence if evidence is not None else _registration_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _sealed_evaluation(
    *, status: str, reason: str | None, facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts if facts is not None else _evaluation_facts(),
            "evidence": evidence if evidence is not None else _evaluation_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _strict_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = MAX_INT) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _decode_b64url(value: Any) -> bytes | None:
    if type(value) is not str or _B64URL.fullmatch(value) is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (TypeError, ValueError):
        return None
    if base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != value:
        return None
    return decoded


def _proof(value: Any) -> list[str] | None:
    if type(value) is not list or len(value) > MAX_PROOF_LENGTH:
        return None
    if not all(_strict_hash(item) for item in value):
        return None
    return list(value)


def _normalize_roles(value: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or len(value) != len(ROLE_ORDER):
        return None, "registration_role_registrations_shape_invalid"
    normalized: list[dict[str, Any]] = []
    for index, expected_role in enumerate(ROLE_ORDER):
        item = value[index]
        if type(item) is not dict or set(item) != _ROLE_FIELDS:
            return None, f"registration_role_{index}_shape_invalid"
        if item.get("role") != expected_role:
            return None, f"registration_role_{index}_order_invalid"
        for field in (
            "role", "entity_id", "key_id", "organization_id", "control_group_id"
        ):
            if not _strict_identifier(item.get(field)):
                return None, f"registration_role_{index}_{field}_invalid"
        for field in ("public_key_hash", "beneficial_owner_disclosure_hash"):
            if not _strict_hash(item.get(field)):
                return None, f"registration_role_{index}_{field}_invalid"
        if expected_role in OBSERVER_ROLES:
            if not _strict_identifier(item.get("retrieval_run_id")):
                return None, f"registration_role_{index}_retrieval_run_id_invalid"
        elif item.get("retrieval_run_id") is not None:
            return None, "registration_log_retrieval_run_id_must_be_null"
        normalized.append(copy.deepcopy(item))
    for field in (
        "entity_id", "key_id", "public_key_hash", "organization_id",
        "control_group_id", "beneficial_owner_disclosure_hash",
    ):
        values = [item[field] for item in normalized]
        if len(set(values)) != len(values):
            return None, f"registration_role_{field}s_not_distinct"
    if normalized[1]["retrieval_run_id"] == normalized[2]["retrieval_run_id"]:
        return None, "registration_observer_retrieval_run_ids_not_distinct"
    return normalized, None


def _normalize_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _REGISTRATION_FIELDS:
        return None, "registration_shape_invalid"
    for key, expected in _REGISTRATION_CONSTANTS.items():
        if not strict_json_contract_equal(value.get(key), expected):
            return None, f"registration_{key}_invalid"
    for field in ("adapter_id", "log_id", "log_namespace"):
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    for field in (
        "adapter_implementation_hash",
        "source_reproducibility_registration_receipt_hash",
        "source_reproducibility_evaluation_receipt_hash",
        "artifact_catalog_root_hash",
        "pinned_checkpoint_root_hash",
    ):
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    if not _strict_int(
        value.get("expected_artifact_count"), minimum=1, maximum=MAX_ARTIFACTS
    ):
        return None, "registration_expected_artifact_count_invalid"
    if not _strict_int(
        value.get("expected_total_payload_bytes"),
        minimum=1,
        maximum=MAX_TOTAL_PAYLOAD_BYTES,
    ):
        return None, "registration_expected_total_payload_bytes_invalid"
    if not _strict_int(
        value.get("max_artifact_payload_bytes"),
        minimum=1,
        maximum=MAX_TOTAL_PAYLOAD_BYTES,
    ):
        return None, "registration_max_artifact_payload_bytes_invalid"
    if value["expected_total_payload_bytes"] < value["expected_artifact_count"]:
        return None, "registration_total_payload_below_artifact_count"
    if value["expected_total_payload_bytes"] > (
        value["expected_artifact_count"] * value["max_artifact_payload_bytes"]
    ):
        return None, "registration_total_payload_exceeds_per_artifact_bound"
    if not _strict_int(value.get("pinned_checkpoint_tree_size")):
        return None, "registration_pinned_checkpoint_tree_size_invalid"
    if (
        value["pinned_checkpoint_tree_size"] == 0
        and value["pinned_checkpoint_root_hash"] != GENESIS_ROOT_HASH
    ):
        return None, "registration_genesis_checkpoint_root_invalid"
    for field in (
        "max_checkpoint_age_ms", "max_observer_receipt_age_ms",
        "max_observer_retrieval_duration_ms", "max_receipt_issue_delay_ms",
    ):
        if not _strict_int(value.get(field), minimum=1):
            return None, f"registration_{field}_invalid"
    if value["source_reproducibility_registration_receipt_hash"] == value[
        "source_reproducibility_evaluation_receipt_hash"
    ]:
        return None, "registration_source_receipt_hashes_not_distinct"
    roles, error = _normalize_roles(value.get("role_registrations"))
    if roles is None:
        return None, error
    normalized = copy.deepcopy(value)
    normalized["role_registrations"] = roles
    return normalized, None


def build_provider_identity_artifact_transparency_availability_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_registration(status=UNKNOWN_STATUS, reason=error)
    evidence = _registration_evidence()
    for key in evidence:
        evidence[key] = (
            strict_canonical_hash(normalized)
            if key == "registration_hash"
            else normalized[key]
        )
    return _sealed_registration(
        status=REGISTERED_STATUS,
        reason=None,
        facts=_registration_facts(registered=True),
        evidence=evidence,
    )


def verify_provider_identity_artifact_transparency_availability_registration_v1(
    receipt: Any, *, registration: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    return strict_json_contract_equal(
        receipt,
        build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        ),
    )


def _role_map(registration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["role"]: item for item in registration["role_registrations"]}


def _canonical_bytes(value: dict[str, Any]) -> bytes | None:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None


def _verify_signature(
    *, receipt: dict[str, Any], public_key: Any, expected_hash: str, domain: str,
) -> bool:
    public_bytes = _decode_b64url(public_key)
    signature = _decode_b64url(receipt.get("signature"))
    if public_bytes is None or len(public_bytes) != 32 or signature is None:
        return False
    if hashlib.sha256(public_bytes).hexdigest() != expected_hash:
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    canonical = _canonical_bytes(unsigned)
    if canonical is None:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature, domain.encode("ascii") + b"\x00" + canonical
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True


def _leaf_hash(artifact_record_hash: str) -> str:
    return hashlib.sha256(
        LEAF_DOMAIN.encode("ascii") + b"\x00" + bytes.fromhex(artifact_record_hash)
    ).hexdigest()


def _node_hash(left: str, right: str) -> str:
    return hashlib.sha256(
        NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left)
        + bytes.fromhex(right)
    ).hexdigest()


def _verify_inclusion(
    *, artifact_record_hash: str, leaf_index: int, tree_size: int,
    root_hash: str, proof: list[str],
) -> bool:
    if not 0 <= leaf_index < tree_size:
        return False
    fn = leaf_index
    sn = tree_size - 1
    running = _leaf_hash(artifact_record_hash)
    for sibling in proof:
        if sn == 0:
            return False
        if fn == sn or (fn & 1) == 1:
            running = _node_hash(sibling, running)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            running = _node_hash(running, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and running == root_hash


def _verify_consistency(
    *, old_size: int, new_size: int, old_root: str, new_root: str,
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
            first_root = _node_hash(sibling, first_root)
            second_root = _node_hash(sibling, second_root)
            while fn != 0 and (fn & 1) == 0:
                fn >>= 1
                sn >>= 1
        else:
            second_root = _node_hash(second_root, sibling)
        fn >>= 1
        sn >>= 1
    return (
        fn == 0
        and sn == 0
        and first_root == old_root
        and second_root == new_root
    )


def _normalize_catalog(
    value: Any, *, registration: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or len(value) != registration["expected_artifact_count"]:
        return None, "artifact_catalog_shape_invalid"
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != _ARTIFACT_FIELDS:
            return None, f"artifact_{index}_shape_invalid"
        for field in ("artifact_id", "artifact_kind", "media_type"):
            if not _strict_identifier(item.get(field)):
                return None, f"artifact_{index}_{field}_invalid"
        for field in ("content_hash", "locator_commitment_hash"):
            if not _strict_hash(item.get(field)):
                return None, f"artifact_{index}_{field}_invalid"
        if not _strict_int(
            item.get("size_bytes"),
            minimum=1,
            maximum=registration["max_artifact_payload_bytes"],
        ):
            return None, f"artifact_{index}_size_bytes_invalid"
        if type(item.get("required")) is not bool or item["required"] is not True:
            return None, f"artifact_{index}_required_invalid"
        normalized.append(dict(item))
    identifiers = [item["artifact_id"] for item in normalized]
    if len(set(identifiers)) != len(identifiers):
        return None, "artifact_ids_not_unique"
    if identifiers != sorted(identifiers):
        return None, "artifact_ids_not_canonical"
    if strict_canonical_hash(normalized) != registration["artifact_catalog_root_hash"]:
        return None, "artifact_catalog_root_mismatch"
    if sum(item["size_bytes"] for item in normalized) != registration[
        "expected_total_payload_bytes"
    ]:
        return None, "artifact_catalog_total_size_mismatch"
    return normalized, None


def _validate_payloads(
    value: Any, *, catalog: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or len(value) != len(catalog):
        return None, "artifact_payloads_shape_invalid"
    normalized: list[dict[str, Any]] = []
    for index, (payload, artifact) in enumerate(zip(value, catalog)):
        if type(payload) is not dict or set(payload) != _PAYLOAD_FIELDS:
            return None, f"artifact_payload_{index}_shape_invalid"
        if payload.get("artifact_id") != artifact["artifact_id"]:
            return None, f"artifact_payload_{index}_id_mismatch"
        content = _decode_b64url(payload.get("content_base64url"))
        if content is None:
            return None, f"artifact_payload_{index}_encoding_invalid"
        if len(content) != artifact["size_bytes"]:
            return None, f"artifact_payload_{index}_size_mismatch"
        if hashlib.sha256(content).hexdigest() != artifact["content_hash"]:
            return None, f"artifact_payload_{index}_content_hash_mismatch"
        normalized.append(dict(payload))
    return normalized, None


def _validate_checkpoint(
    value: Any, *, registration: dict[str, Any], public_key: Any,
    reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _CHECKPOINT_FIELDS:
        return None, "checkpoint_shape_invalid"
    log_role = _role_map(registration)["transparency_log"]
    expected = {
        "schema": CHECKPOINT_SCHEMA,
        "log_id": registration["log_id"],
        "log_namespace": registration["log_namespace"],
        "key_id": log_role["key_id"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"checkpoint_{key}_mismatch"
    if not _strict_int(value.get("tree_size"), minimum=1):
        return None, "checkpoint_tree_size_invalid"
    if not _strict_hash(value.get("root_hash")):
        return None, "checkpoint_root_hash_invalid"
    if not _strict_int(value.get("issued_at_ms")):
        return None, "checkpoint_issued_at_ms_invalid"
    if value["issued_at_ms"] > reference_time_ms:
        return None, "checkpoint_issued_in_future"
    if reference_time_ms - value["issued_at_ms"] > registration["max_checkpoint_age_ms"]:
        return None, "checkpoint_age_exceeded"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_hash=log_role["public_key_hash"],
        domain=CHECKPOINT_SIGNATURE_DOMAIN,
    ):
        return None, "checkpoint_signature_invalid"
    return dict(value), None


def _validate_inclusions(
    value: Any, *, catalog: list[dict[str, Any]], checkpoint: dict[str, Any],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or len(value) != len(catalog):
        return None, "inclusion_proofs_shape_invalid"
    normalized: list[dict[str, Any]] = []
    leaf_indices: list[int] = []
    for index, (item, artifact) in enumerate(zip(value, catalog)):
        if type(item) is not dict or set(item) != _INCLUSION_FIELDS:
            return None, f"inclusion_{index}_shape_invalid"
        if item.get("artifact_id") != artifact["artifact_id"]:
            return None, f"inclusion_{index}_artifact_id_mismatch"
        if not _strict_int(item.get("leaf_index")):
            return None, f"inclusion_{index}_leaf_index_invalid"
        proof = _proof(item.get("proof"))
        if proof is None:
            return None, f"inclusion_{index}_proof_invalid"
        if not _verify_inclusion(
            artifact_record_hash=strict_canonical_hash(artifact),
            leaf_index=item["leaf_index"],
            tree_size=checkpoint["tree_size"],
            root_hash=checkpoint["root_hash"],
            proof=proof,
        ):
            return None, f"inclusion_{index}_verification_failed"
        leaf_indices.append(item["leaf_index"])
        normalized.append(
            {"artifact_id": item["artifact_id"], "leaf_index": item["leaf_index"], "proof": proof}
        )
    if len(set(leaf_indices)) != len(leaf_indices):
        return None, "inclusion_leaf_indices_not_unique"
    return normalized, None


def _validate_observer(
    value: Any, *, role: str, registration: dict[str, Any], registration_hash: str,
    source_evaluation_hash: str, catalog: list[dict[str, Any]],
    checkpoint_hash: str, public_key: Any, reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _OBSERVER_FIELDS:
        return None, f"{role}_receipt_shape_invalid"
    observer = _role_map(registration)[role]
    expected = {
        "schema": OBSERVER_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_hash,
        "source_reproducibility_evaluation_receipt_hash": source_evaluation_hash,
        "artifact_catalog_root_hash": registration["artifact_catalog_root_hash"],
        "transparency_checkpoint_hash": checkpoint_hash,
        "observer_role": role,
        "observer_id": observer["entity_id"],
        "observer_organization_id": observer["organization_id"],
        "observer_control_group_id": observer["control_group_id"],
        "observer_key_id": observer["key_id"],
        "retrieval_run_id": observer["retrieval_run_id"],
        "retrieval_method": RETRIEVAL_METHOD,
        "result_count": len(catalog),
        "success_count": len(catalog),
        "failure_count": 0,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"{role}_{key}_mismatch"
    results = value.get("artifact_results")
    if type(results) is not list or len(results) != len(catalog):
        return None, f"{role}_artifact_results_shape_invalid"
    normalized_results: list[dict[str, Any]] = []
    for index, (result, artifact) in enumerate(zip(results, catalog)):
        if type(result) is not dict or set(result) != _OBSERVER_RESULT_FIELDS:
            return None, f"{role}_result_{index}_shape_invalid"
        expected_result = {
            "artifact_id": artifact["artifact_id"],
            "locator_commitment_hash": artifact["locator_commitment_hash"],
            "retrieved_content_hash": artifact["content_hash"],
            "retrieved_size_bytes": artifact["size_bytes"],
            "retrieval_succeeded": True,
        }
        for key, expected_value in expected_result.items():
            if not strict_json_contract_equal(result.get(key), expected_value):
                return None, f"{role}_result_{index}_{key}_mismatch"
        normalized_results.append(dict(result))
    if value.get("result_transcript_root_hash") != strict_canonical_hash(
        normalized_results
    ):
        return None, f"{role}_result_transcript_root_mismatch"
    for field in ("started_at_ms", "completed_at_ms", "issued_at_ms"):
        if not _strict_int(value.get(field)):
            return None, f"{role}_{field}_invalid"
    started = value["started_at_ms"]
    completed = value["completed_at_ms"]
    issued = value["issued_at_ms"]
    if not started <= completed <= issued <= reference_time_ms:
        return None, f"{role}_time_order_invalid"
    if completed - started > registration["max_observer_retrieval_duration_ms"]:
        return None, f"{role}_retrieval_duration_exceeded"
    if issued - completed > registration["max_receipt_issue_delay_ms"]:
        return None, f"{role}_issue_delay_exceeded"
    if reference_time_ms - issued > registration["max_observer_receipt_age_ms"]:
        return None, f"{role}_receipt_age_exceeded"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_hash=observer["public_key_hash"],
        domain=f"{OBSERVER_SIGNATURE_DOMAIN_PREFIX}.{role}",
    ):
        return None, f"{role}_signature_invalid"
    normalized = copy.deepcopy(value)
    normalized["artifact_results"] = normalized_results
    return normalized, None


def evaluate_provider_identity_artifact_transparency_availability_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    source_reproducibility_inputs: Any,
    source_reproducibility_evaluation_receipt: Any,
    artifact_catalog: Any,
    artifact_payloads: Any,
    transparency_checkpoint: Any,
    transparency_log_public_key: Any,
    transparency_inclusion_proofs: Any,
    transparency_consistency_proof: Any,
    observer_a_receipt: Any,
    observer_a_public_key: Any,
    observer_b_receipt: Any,
    observer_b_public_key: Any,
    reference_time_ms: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    if not verify_provider_identity_artifact_transparency_availability_registration_v1(
        registration_receipt, registration=registration
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_receipt_invalid")
    if registration_receipt.get("status") != REGISTERED_STATUS:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_status_invalid")
    if not _strict_int(reference_time_ms):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="reference_time_ms_invalid")
    if type(source_reproducibility_inputs) is not dict or type(
        source_reproducibility_evaluation_receipt
    ) is not dict:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_shape_invalid")
    try:
        source_ok = source_contract.verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1(
            source_reproducibility_evaluation_receipt,
            **source_reproducibility_inputs,
        )
    except Exception:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_verifier_error")
    if source_ok is not True:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_evaluation_not_verified")
    if (
        source_reproducibility_evaluation_receipt.get("schema") != source_contract.EVALUATION_SCHEMA
        or source_reproducibility_evaluation_receipt.get("status") != source_contract.VERIFIED_STATUS
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_evaluation_status_invalid")
    source_registration_receipt = source_reproducibility_inputs.get("registration_receipt")
    source_registration = source_reproducibility_inputs.get("registration")
    if type(source_registration_receipt) is not dict or type(source_registration) is not dict:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_registration_shape_invalid")
    source_registration_hash = source_registration_receipt.get("receipt_hash")
    source_evaluation_hash = source_reproducibility_evaluation_receipt.get("receipt_hash")
    if not _strict_hash(source_registration_hash) or not _strict_hash(source_evaluation_hash):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_receipt_hash_invalid")
    if source_registration_hash != normalized[
        "source_reproducibility_registration_receipt_hash"
    ]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS, reason="source_registration_receipt_hash_mismatch"
        )
    if source_evaluation_hash != normalized["source_reproducibility_evaluation_receipt_hash"]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS, reason="source_evaluation_receipt_hash_mismatch"
        )
    source_roles = source_registration.get("role_registrations")
    if type(source_roles) is not list:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_roles_shape_invalid")
    new_roles = normalized["role_registrations"]
    for field in (
        "entity_id", "key_id", "public_key_hash", "organization_id",
        "control_group_id", "beneficial_owner_disclosure_hash",
    ):
        source_values = {
            item.get(field) for item in source_roles if type(item) is dict
        }
        if any(item[field] in source_values for item in new_roles):
            return _sealed_evaluation(
                status=UNKNOWN_STATUS, reason=f"source_new_role_{field}_collision"
            )
    catalog, error = _normalize_catalog(artifact_catalog, registration=normalized)
    if catalog is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    payloads, error = _validate_payloads(artifact_payloads, catalog=catalog)
    if payloads is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    checkpoint, error = _validate_checkpoint(
        transparency_checkpoint,
        registration=normalized,
        public_key=transparency_log_public_key,
        reference_time_ms=reference_time_ms,
    )
    if checkpoint is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    inclusions, error = _validate_inclusions(
        transparency_inclusion_proofs, catalog=catalog, checkpoint=checkpoint
    )
    if inclusions is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    consistency = _proof(transparency_consistency_proof)
    if consistency is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="consistency_proof_invalid")
    if not _verify_consistency(
        old_size=normalized["pinned_checkpoint_tree_size"],
        new_size=checkpoint["tree_size"],
        old_root=normalized["pinned_checkpoint_root_hash"],
        new_root=checkpoint["root_hash"],
        proof=consistency,
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="consistency_verification_failed")
    registration_hash = registration_receipt.get("receipt_hash")
    if not _strict_hash(registration_hash):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_receipt_hash_invalid")
    checkpoint_hash = strict_canonical_hash(checkpoint)
    observer_a, error = _validate_observer(
        observer_a_receipt,
        role="observer_a",
        registration=normalized,
        registration_hash=registration_hash,
        source_evaluation_hash=source_evaluation_hash,
        catalog=catalog,
        checkpoint_hash=checkpoint_hash,
        public_key=observer_a_public_key,
        reference_time_ms=reference_time_ms,
    )
    if observer_a is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    observer_b, error = _validate_observer(
        observer_b_receipt,
        role="observer_b",
        registration=normalized,
        registration_hash=registration_hash,
        source_evaluation_hash=source_evaluation_hash,
        catalog=catalog,
        checkpoint_hash=checkpoint_hash,
        public_key=observer_b_public_key,
        reference_time_ms=reference_time_ms,
    )
    if observer_b is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    transcript_root = observer_a["result_transcript_root_hash"]
    if observer_b["result_transcript_root_hash"] != transcript_root:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="dual_observer_result_disagreement")
    observer_a_hash = strict_canonical_hash(observer_a)
    observer_b_hash = strict_canonical_hash(observer_b)
    if observer_a_hash == observer_b_hash:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="dual_observer_receipt_reused")
    facts = _evaluation_facts()
    for key in (
        "source_reproducibility_reverified",
        "source_and_new_roles_separated",
        "artifact_catalog_root_verified",
        "local_artifact_content_hashes_verified",
        "local_artifact_sizes_verified",
        "transparency_checkpoint_signature_verified",
        "all_artifact_inclusion_proofs_verified",
        "append_only_consistency_verified",
        "observer_a_signature_verified",
        "observer_b_signature_verified",
        "complete_dual_observer_retrieval_claims_verified",
        "dual_observer_result_agreement_verified",
    ):
        facts[key] = True
    evidence = _evaluation_evidence()
    evidence.update(
        {
            "registration_receipt_hash": registration_hash,
            "source_reproducibility_evaluation_receipt_hash": source_evaluation_hash,
            "artifact_catalog_root_hash": normalized["artifact_catalog_root_hash"],
            "artifact_count": len(catalog),
            "total_payload_bytes": sum(item["size_bytes"] for item in catalog),
            "transparency_checkpoint_hash": checkpoint_hash,
            "checkpoint_tree_size": checkpoint["tree_size"],
            "checkpoint_root_hash": checkpoint["root_hash"],
            "observer_a_receipt_hash": observer_a_hash,
            "observer_b_receipt_hash": observer_b_hash,
            "observer_result_transcript_root_hash": transcript_root,
            "reference_time_ms": reference_time_ms,
        }
    )
    return _sealed_evaluation(
        status=VERIFIED_STATUS, reason=None, facts=facts, evidence=evidence
    )


def verify_provider_identity_artifact_transparency_availability_evaluation_v1(
    receipt: Any, **inputs: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    return strict_json_contract_equal(
        receipt,
        evaluate_provider_identity_artifact_transparency_availability_v1(**inputs),
    )


__all__ = [
    "CHECKPOINT_SCHEMA",
    "CHECKPOINT_SIGNATURE_DOMAIN",
    "CONSISTENCY_PROOF_PROTOCOL",
    "CONTENT_ENCODING",
    "EVALUATION_SCHEMA",
    "GENESIS_ROOT_HASH",
    "INCLUSION_PROOF_PROTOCOL",
    "LEAF_DOMAIN",
    "LOG_PROTOCOL",
    "NODE_DOMAIN",
    "OBSERVER_RECEIPT_SCHEMA",
    "OBSERVER_ROLES",
    "OBSERVER_SIGNATURE_DOMAIN_PREFIX",
    "REGISTERED_STATUS",
    "REGISTRATION_RECEIPT_SCHEMA",
    "REGISTRATION_SCHEMA",
    "RETRIEVAL_METHOD",
    "ROLE_ORDER",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_ENCODING",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "build_provider_identity_artifact_transparency_availability_registration_v1",
    "evaluate_provider_identity_artifact_transparency_availability_v1",
    "verify_provider_identity_artifact_transparency_availability_evaluation_v1",
    "verify_provider_identity_artifact_transparency_availability_registration_v1",
]
