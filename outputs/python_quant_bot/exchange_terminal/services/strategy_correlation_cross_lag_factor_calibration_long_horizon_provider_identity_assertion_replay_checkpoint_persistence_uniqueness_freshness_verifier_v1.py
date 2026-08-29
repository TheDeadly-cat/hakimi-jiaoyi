from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1 as lineage_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_registration_v1 as registration_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


EVALUATION_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-uniqueness-freshness-"
    "evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20261002-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-uniqueness-freshness-verifier-1"
)
VERIFIED_STATUS = (
    "SIGNED_COMPLETE_OCCURRENCE_CARDINALITY_AND_TIME_WINDOW_CLAIMS_VERIFIED_"
    "EXTERNAL_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
MAX_TREE_SIZE = 2**63 - 1
MAX_TIME_MS = 2**63 - 1

_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_OCCURRENCE_FIELDS = frozenset(
    {
        "schema",
        "lineage_receipt_hash",
        "current_binding_receipt_hash",
        "replay_registration_receipt_hash",
        "replay_registry_id",
        "replay_registry_namespace",
        "checkpoint_tree_size",
        "checkpoint_root_hash",
        "checkpoint_hash",
        "assertion_receipt_hash",
        "assertion_leaf_index",
        "scan_start_index",
        "scan_end_index_exclusive",
        "index_snapshot_record_count",
        "index_snapshot_root_hash",
        "occurrence_count",
        "occurrence_leaf_indices",
        "scan_completed_at_ms",
        "provider_id",
        "occurrence_namespace",
        "key_id",
        "scan_policy",
        "cardinality_policy",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)
_TIME_FIELDS = frozenset(
    {
        "schema",
        "lineage_receipt_hash",
        "occurrence_receipt_hash",
        "checkpoint_hash",
        "checkpoint_issued_at_ms",
        "scan_completed_at_ms",
        "reference_time_ms",
        "max_checkpoint_age_ms",
        "max_occurrence_to_reference_delay_ms",
        "authority_id",
        "time_namespace",
        "key_id",
        "time_window_policy",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
        "replay_registry_checked": False,
        "pinned_checkpoint_authoritative": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "lineage_evaluation_verified": False,
        "evidence_registration_verified": False,
        "upstream_role_separation_verified": False,
        "occurrence_signature_verified": False,
        "time_signature_verified": False,
        "occurrence_receipt_bound_to_lineage": False,
        "complete_scan_claim_verified": False,
        "exactly_one_occurrence_claim_verified": False,
        "time_window_claim_verified": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _evidence() -> dict[str, Any]:
    return {
        "lineage_receipt_hash": None,
        "registration_receipt_hash": None,
        "occurrence_receipt_hash": None,
        "time_receipt_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "checkpoint_tree_size": None,
        "checkpoint_root_hash": None,
        "checkpoint_hash": None,
        "assertion_receipt_hash": None,
        "assertion_leaf_index": None,
        "occurrence_count_claim": None,
        "occurrence_leaf_indices_claim": None,
        "scan_completed_at_ms_claim": None,
        "reference_time_ms_claim": None,
        "checkpoint_age_ms_claim": None,
        "occurrence_to_reference_delay_ms_claim": None,
        "occurrence_provider_id": None,
        "time_authority_id": None,
    }


def _sealed(
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts or _facts(),
            "evidence": evidence or _evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = MAX_TREE_SIZE) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode_b64url(value: Any) -> bytes | None:
    if type(value) is not str or not value or "=" in value or _B64URL.fullmatch(value) is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError):
        return None
    if base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != value:
        return None
    return decoded


def _verify_signature(
    *,
    receipt: dict[str, Any],
    public_key: Any,
    expected_public_key_hash: str,
    domain: str,
) -> bool:
    public_key_bytes = _decode_b64url(public_key)
    signature = _decode_b64url(receipt.get("signature"))
    if public_key_bytes is None or len(public_key_bytes) != 32 or signature is None:
        return False
    if hashlib.sha256(public_key_bytes).hexdigest() != expected_public_key_hash:
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    message = domain.encode("ascii") + b"\x00" + _canonical_bytes(unsigned)
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, message)
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def _extract_source(
    *,
    lineage_evaluation: Any,
    current_segment: Any,
    previous_segment: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(lineage_evaluation) is not dict or type(current_segment) is not dict:
        return None, "lineage_inputs_shape_invalid"
    try:
        verified = lineage_contract.verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(
            lineage_evaluation,
            current_segment=current_segment,
            previous_segment=previous_segment,
        )
    except (KeyError, TypeError, ValueError):
        verified = False
    if not verified or lineage_evaluation.get("status") != lineage_contract.VERIFIED_STATUS:
        return None, "lineage_evaluation_unverified"
    evidence = lineage_evaluation.get("evidence")
    replay_inputs = current_segment.get("replay_inputs")
    persistence_inputs = current_segment.get("persistence_inputs")
    binding = current_segment.get("binding")
    if not all(type(value) is dict for value in (evidence, replay_inputs, persistence_inputs, binding)):
        return None, "lineage_source_shape_invalid"
    replay_registration = replay_inputs.get("registration")
    replay_registration_receipt = replay_inputs.get("registration_receipt")
    replay_receipt = replay_inputs.get("replay_receipt")
    persistence_configuration = persistence_inputs.get("persistence_configuration")
    persistence_registration_receipt = persistence_inputs.get("persistence_registration_receipt")
    if not all(
        type(value) is dict
        for value in (
            replay_registration,
            replay_registration_receipt,
            replay_receipt,
            persistence_configuration,
            persistence_registration_receipt,
        )
    ):
        return None, "lineage_nested_source_shape_invalid"
    checkpoint = replay_receipt.get("checkpoint")
    if type(checkpoint) is not dict:
        return None, "lineage_checkpoint_shape_invalid"
    source = {
        "lineage_receipt_hash": lineage_evaluation.get("receipt_hash"),
        "current_binding_receipt_hash": binding.get("receipt_hash"),
        "replay_registration_receipt_hash": replay_registration_receipt.get("receipt_hash"),
        "persistence_registration_receipt_hash": persistence_registration_receipt.get("receipt_hash"),
        "replay_registry_id": evidence.get("replay_registry_id"),
        "replay_registry_namespace": evidence.get("replay_registry_namespace"),
        "checkpoint_tree_size": evidence.get("current_tree_size"),
        "checkpoint_root_hash": evidence.get("current_root_hash"),
        "checkpoint_hash": evidence.get("current_checkpoint_hash"),
        "checkpoint_issued_at_ms": checkpoint.get("issued_at_ms"),
        "assertion_receipt_hash": replay_receipt.get("assertion_receipt_hash"),
        "assertion_leaf_index": replay_receipt.get("leaf_index"),
        "upstream_key_ids": {
            replay_registration.get("provider_receipt_signing_key_id"),
            replay_registration.get("identity_registry_trust_root_key_id"),
            replay_registration.get("replay_registry_trust_root_key_id"),
            persistence_configuration.get("persistence_provider_key_id"),
        },
        "upstream_key_hashes": {
            replay_registration.get("provider_receipt_signing_public_key_hash"),
            replay_registration.get("identity_registry_trust_root_public_key_hash"),
            replay_registration.get("replay_registry_trust_root_public_key_hash"),
            persistence_configuration.get("persistence_provider_public_key_hash"),
        },
    }
    hash_fields = (
        "lineage_receipt_hash",
        "current_binding_receipt_hash",
        "replay_registration_receipt_hash",
        "persistence_registration_receipt_hash",
        "checkpoint_root_hash",
        "checkpoint_hash",
        "assertion_receipt_hash",
    )
    if any(not _strict_hash(source[field]) for field in hash_fields):
        return None, "lineage_source_hash_invalid"
    if source["current_binding_receipt_hash"] != evidence.get("current_binding_receipt_hash"):
        return None, "lineage_binding_receipt_hash_mismatch"
    if strict_canonical_hash(checkpoint) != source["checkpoint_hash"]:
        return None, "lineage_checkpoint_hash_mismatch"
    if not _strict_int(source["checkpoint_tree_size"], minimum=1):
        return None, "lineage_checkpoint_tree_size_invalid"
    if not _strict_int(source["assertion_leaf_index"]):
        return None, "lineage_assertion_leaf_index_invalid"
    if source["assertion_leaf_index"] >= source["checkpoint_tree_size"]:
        return None, "lineage_assertion_leaf_index_out_of_range"
    if not _strict_int(source["checkpoint_issued_at_ms"], minimum=1, maximum=MAX_TIME_MS):
        return None, "lineage_checkpoint_issued_at_ms_invalid"
    if (
        type(source["replay_registry_id"]) is not str
        or type(source["replay_registry_namespace"]) is not str
    ):
        return None, "lineage_registry_identity_invalid"
    if any(type(value) is not str for value in source["upstream_key_ids"]):
        return None, "lineage_upstream_key_ids_invalid"
    if any(not _strict_hash(value) for value in source["upstream_key_hashes"]):
        return None, "lineage_upstream_key_hashes_invalid"
    return source, None


def _validate_occurrence(
    value: Any,
    *,
    registration: dict[str, Any],
    source: dict[str, Any],
    public_key: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _OCCURRENCE_FIELDS:
        return None, "occurrence_receipt_shape_invalid"
    exact = {
        "schema": registration_contract.OCCURRENCE_RECEIPT_SCHEMA,
        "lineage_receipt_hash": source["lineage_receipt_hash"],
        "current_binding_receipt_hash": source["current_binding_receipt_hash"],
        "replay_registration_receipt_hash": source["replay_registration_receipt_hash"],
        "replay_registry_id": source["replay_registry_id"],
        "replay_registry_namespace": source["replay_registry_namespace"],
        "checkpoint_tree_size": source["checkpoint_tree_size"],
        "checkpoint_root_hash": source["checkpoint_root_hash"],
        "checkpoint_hash": source["checkpoint_hash"],
        "assertion_receipt_hash": source["assertion_receipt_hash"],
        "assertion_leaf_index": source["assertion_leaf_index"],
        "scan_start_index": 0,
        "scan_end_index_exclusive": source["checkpoint_tree_size"],
        "index_snapshot_record_count": source["checkpoint_tree_size"],
        "occurrence_count": 1,
        "occurrence_leaf_indices": [source["assertion_leaf_index"]],
        "provider_id": registration["occurrence_provider_id"],
        "occurrence_namespace": registration["occurrence_namespace"],
        "key_id": registration["occurrence_provider_key_id"],
        "scan_policy": registration_contract.SCAN_POLICY,
        "cardinality_policy": registration_contract.CARDINALITY_POLICY,
        "signature_algorithm": registration_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": registration_contract.SIGNATURE_ENCODING,
    }
    for field, expected in exact.items():
        if value.get(field) != expected or type(value.get(field)) is not type(expected):
            return None, f"occurrence_{field}_mismatch"
    if not _strict_hash(value.get("index_snapshot_root_hash")):
        return None, "occurrence_index_snapshot_root_hash_invalid"
    if not _strict_int(value.get("scan_completed_at_ms"), minimum=1, maximum=MAX_TIME_MS):
        return None, "occurrence_scan_completed_at_ms_invalid"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_public_key_hash=registration["occurrence_provider_public_key_hash"],
        domain=registration_contract.OCCURRENCE_SIGNATURE_DOMAIN,
    ):
        return None, "occurrence_signature_invalid"
    return value, None


def _validate_time(
    value: Any,
    *,
    registration: dict[str, Any],
    source: dict[str, Any],
    occurrence: dict[str, Any],
    public_key: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _TIME_FIELDS:
        return None, "time_receipt_shape_invalid"
    occurrence_hash = strict_canonical_hash(occurrence)
    exact = {
        "schema": registration_contract.TIME_RECEIPT_SCHEMA,
        "lineage_receipt_hash": source["lineage_receipt_hash"],
        "occurrence_receipt_hash": occurrence_hash,
        "checkpoint_hash": source["checkpoint_hash"],
        "checkpoint_issued_at_ms": source["checkpoint_issued_at_ms"],
        "scan_completed_at_ms": occurrence["scan_completed_at_ms"],
        "max_checkpoint_age_ms": registration["max_checkpoint_age_ms"],
        "max_occurrence_to_reference_delay_ms": registration[
            "max_occurrence_to_reference_delay_ms"
        ],
        "authority_id": registration["time_authority_id"],
        "time_namespace": registration["time_namespace"],
        "key_id": registration["time_authority_key_id"],
        "time_window_policy": registration_contract.TIME_WINDOW_POLICY,
        "signature_algorithm": registration_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": registration_contract.SIGNATURE_ENCODING,
    }
    for field, expected in exact.items():
        if value.get(field) != expected or type(value.get(field)) is not type(expected):
            return None, f"time_{field}_mismatch"
    reference = value.get("reference_time_ms")
    if not _strict_int(reference, minimum=1, maximum=MAX_TIME_MS):
        return None, "time_reference_time_ms_invalid"
    issued = source["checkpoint_issued_at_ms"]
    scanned = occurrence["scan_completed_at_ms"]
    if not issued <= scanned <= reference:
        return None, "time_order_invalid"
    if reference - issued > registration["max_checkpoint_age_ms"]:
        return None, "time_checkpoint_age_exceeds_registration"
    if reference - scanned > registration["max_occurrence_to_reference_delay_ms"]:
        return None, "time_occurrence_delay_exceeds_registration"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_public_key_hash=registration["time_authority_public_key_hash"],
        domain=registration_contract.TIME_SIGNATURE_DOMAIN,
    ):
        return None, "time_signature_invalid"
    return value, None


def evaluate_provider_identity_assertion_uniqueness_freshness_evidence_v1(
    *,
    lineage_evaluation: Any,
    current_segment: Any,
    previous_segment: Any = None,
    evidence_registration: Any,
    evidence_registration_receipt: Any,
    occurrence_receipt: Any,
    occurrence_provider_public_key: Any,
    time_receipt: Any,
    time_authority_public_key: Any,
) -> dict[str, Any]:
    source, reason = _extract_source(
        lineage_evaluation=lineage_evaluation,
        current_segment=current_segment,
        previous_segment=previous_segment,
    )
    if source is None:
        return _sealed(status=UNKNOWN_STATUS, reason=reason)
    if not registration_contract.verify_provider_identity_assertion_uniqueness_freshness_registration_v1(
        evidence_registration_receipt,
        registration=evidence_registration,
    ):
        return _sealed(status=UNKNOWN_STATUS, reason="evidence_registration_unverified")
    if evidence_registration_receipt.get("status") != registration_contract.REGISTERED_STATUS:
        return _sealed(status=UNKNOWN_STATUS, reason="evidence_registration_not_registered")
    registration = evidence_registration
    if (
        registration["source_replay_registration_receipt_hash"]
        != source["replay_registration_receipt_hash"]
    ):
        return _sealed(status=UNKNOWN_STATUS, reason="source_replay_registration_mismatch")
    if (
        registration["source_persistence_registration_receipt_hash"]
        != source["persistence_registration_receipt_hash"]
    ):
        return _sealed(status=UNKNOWN_STATUS, reason="source_persistence_registration_mismatch")
    witness_ids = {
        registration["occurrence_provider_key_id"],
        registration["time_authority_key_id"],
    }
    witness_hashes = {
        registration["occurrence_provider_public_key_hash"],
        registration["time_authority_public_key_hash"],
    }
    if witness_ids & source["upstream_key_ids"]:
        return _sealed(status=UNKNOWN_STATUS, reason="witness_key_id_role_collision")
    if witness_hashes & source["upstream_key_hashes"]:
        return _sealed(status=UNKNOWN_STATUS, reason="witness_key_hash_role_collision")
    occurrence, reason = _validate_occurrence(
        occurrence_receipt,
        registration=registration,
        source=source,
        public_key=occurrence_provider_public_key,
    )
    if occurrence is None:
        return _sealed(status=UNKNOWN_STATUS, reason=reason)
    time_claim, reason = _validate_time(
        time_receipt,
        registration=registration,
        source=source,
        occurrence=occurrence,
        public_key=time_authority_public_key,
    )
    if time_claim is None:
        return _sealed(status=UNKNOWN_STATUS, reason=reason)
    facts = _facts()
    facts.update(
        {
            "lineage_evaluation_verified": True,
            "evidence_registration_verified": True,
            "upstream_role_separation_verified": True,
            "occurrence_signature_verified": True,
            "time_signature_verified": True,
            "occurrence_receipt_bound_to_lineage": True,
            "complete_scan_claim_verified": True,
            "exactly_one_occurrence_claim_verified": True,
            "time_window_claim_verified": True,
        }
    )
    reference = time_claim["reference_time_ms"]
    evidence = _evidence()
    evidence.update(
        {
            "lineage_receipt_hash": source["lineage_receipt_hash"],
            "registration_receipt_hash": evidence_registration_receipt["receipt_hash"],
            "occurrence_receipt_hash": strict_canonical_hash(occurrence),
            "time_receipt_hash": strict_canonical_hash(time_claim),
            "replay_registry_id": source["replay_registry_id"],
            "replay_registry_namespace": source["replay_registry_namespace"],
            "checkpoint_tree_size": source["checkpoint_tree_size"],
            "checkpoint_root_hash": source["checkpoint_root_hash"],
            "checkpoint_hash": source["checkpoint_hash"],
            "assertion_receipt_hash": source["assertion_receipt_hash"],
            "assertion_leaf_index": source["assertion_leaf_index"],
            "occurrence_count_claim": occurrence["occurrence_count"],
            "occurrence_leaf_indices_claim": occurrence["occurrence_leaf_indices"],
            "scan_completed_at_ms_claim": occurrence["scan_completed_at_ms"],
            "reference_time_ms_claim": reference,
            "checkpoint_age_ms_claim": reference - source["checkpoint_issued_at_ms"],
            "occurrence_to_reference_delay_ms_claim": (
                reference - occurrence["scan_completed_at_ms"]
            ),
            "occurrence_provider_id": registration["occurrence_provider_id"],
            "time_authority_id": registration["time_authority_id"],
        }
    )
    return _sealed(
        status=VERIFIED_STATUS,
        reason=None,
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1(
    evaluation: Any,
    **inputs: Any,
) -> bool:
    if type(evaluation) is not dict:
        return False
    try:
        expected = evaluate_provider_identity_assertion_uniqueness_freshness_evidence_v1(
            **inputs
        )
    except (KeyError, TypeError, ValueError):
        return False
    return evaluation == expected
