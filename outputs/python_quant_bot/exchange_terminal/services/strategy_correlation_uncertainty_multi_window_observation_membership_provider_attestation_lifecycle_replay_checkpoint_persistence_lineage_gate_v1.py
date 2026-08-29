"""Verify one persisted common-view checkpoint lineage segment.

The gate supports a preregistered source-pin anchor or one exact previous
ADR0355-bound asset. It reruns every supplied ADR0355 segment, binds asset
hashes and checkpoint root/tree content, and requires strict tree growth.
Complete history, external durability, and authoritative pinning stay false.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1
    as persistence_binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-replay-checkpoint-persistence-lineage-"
    "gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-multi-window-lifecycle-replay-checkpoint-"
    "persistence-lineage-gate-v1-synthetic-unmounted-lock-1"
)
PERSISTENCE_BINDING_V1_IMPLEMENTATION_SHA256 = (
    "7dcdca13d6d658dc9963d5cc5f4dea47575d42305831dfbe301a4db6ee90e522"
)
REGISTERED_SOURCE_PIN_MODE = "REGISTERED_SOURCE_PIN"
PREVIOUS_PERSISTED_ASSET_MODE = "PREVIOUS_PERSISTED_ASSET"
_SEGMENT_FIELDS = frozenset(
    {
        "binding_gate_document",
        "expected_binding_gate_hash",
        "persistence_evaluation",
        "persistence_inputs",
        "source_gate_document",
        "source_inputs",
    }
)
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
_BASE_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "EXTERNAL_PERSISTENCE_PROVIDER_AUTHORITY_UNPROVEN",
    "REAL_STORAGE_DURABILITY_UNPROVEN",
    "AUTHORITATIVE_FUTURE_PIN_UNPROVEN",
    "COMPLETE_PERSISTED_CHECKPOINT_HISTORY_UNPROVEN",
    "LONGITUDINAL_COVERAGE_UNPROVEN",
    "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
    "PAPER_LIVE_UNAUTHORIZED",
)
_STABLE_LINEAGE_FIELDS = (
    "lifecycle_receipt_hashes",
    "occurrence_auditor_id",
    "occurrence_auditor_key_id",
    "occurrence_auditor_public_key_sha256",
    "persistence_namespace",
    "persistence_provider_id",
    "persistence_provider_key_id",
    "persistence_provider_public_key_sha256",
    "replay_registry_id",
    "replay_registry_key_id",
    "replay_registry_namespace",
    "replay_registry_public_key_sha256",
    "study_identity_hash",
    "window_order_hash",
)
_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contract": {
        "schema_version": persistence_binding_v1.SCHEMA_VERSION,
        "implementation_sha256": PERSISTENCE_BINDING_V1_IMPLEMENTATION_SHA256,
        "exact_verifier_required_per_segment": True,
    },
    "modes": {
        REGISTERED_SOURCE_PIN_MODE: (
            "NULL_PREVIOUS_ASSET_AND_PREREGISTERED_SOURCE_PIN_CONTENT"
        ),
        PREVIOUS_PERSISTED_ASSET_MODE: (
            "EXACT_PREVIOUS_ASSET_HASH_ROOT_TREE_AND_STABLE_ROLE_LINEAGE"
        ),
    },
    "strict_tree_growth_required": True,
    "complete_history_claimed": False,
    "external_durability_claimed": False,
    "authoritative_pin_claimed": False,
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _native_nonnegative_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value >= 0


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


def _segment_exact(segment: Any) -> bool:
    if type(segment) is not dict or frozenset(segment) != _SEGMENT_FIELDS:
        return False
    try:
        return persistence_binding_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_binding_gate_v1(
            segment["binding_gate_document"],
            segment["source_gate_document"],
            segment["source_inputs"],
            segment["persistence_evaluation"],
            segment["persistence_inputs"],
            expected_gate_hash=segment["expected_binding_gate_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False


def _binding_facts_valid(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != persistence_binding_v1.SCHEMA_VERSION
        or document.get("static_fingerprint")
        != persistence_binding_v1.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or type(document.get("facts")) is not dict
        or type(document.get("authority")) is not dict
        or any(value is not False for value in document["authority"].values())
    ):
        return False
    facts = document["facts"]
    return bool(
        facts.get("asset_source_common_view_bound") is True
        and facts.get("persistence_receipts_exactly_verified") is True
        and facts.get("source_replay_binding_gate_verified") is True
        and facts.get("persisted_checkpoint_lineage_verified") is False
        and facts.get("durable_checkpoint_publication_verified") is False
        and facts.get("authoritative_future_pin_verified") is False
        and facts.get("longitudinal_checkpoint_coverage_verified") is False
    )


def _segment_record(segment: dict[str, Any]) -> dict[str, Any] | None:
    gate = segment["binding_gate_document"]
    source_inputs = segment["source_inputs"]
    persistence_inputs = segment["persistence_inputs"]
    source_preregistration = source_inputs["preregistration"]
    expected_rows = source_preregistration["expected_replay_bindings"]
    common = expected_rows[0]
    asset = persistence_inputs["checkpoint_asset"]
    registration = persistence_inputs["persistence_registration"]
    if (
        not _binding_facts_valid(gate)
        or gate.get("gate_hash") != segment.get("expected_binding_gate_hash")
        or gate.get("source", {}).get("checkpoint_asset_hash")
        != asset.get("asset_hash")
        or gate.get("source", {}).get("replay_binding_preregistration_hash")
        != source_preregistration.get("preregistration_hash")
        or gate.get("source", {}).get("persistence_registration_hash")
        != registration.get("registration_hash")
        or type(expected_rows) is not list
        or not expected_rows
    ):
        return None
    lifecycle_receipt_hashes = [
        row.get("lifecycle_receipt_hash") for row in expected_rows
    ]
    if (
        not all(_exact_hash(value) for value in lifecycle_receipt_hashes)
        or len(set(lifecycle_receipt_hashes)) != len(lifecycle_receipt_hashes)
    ):
        return None
    record = {
        "asset_created_at_utc": asset["asset_created_at_utc"],
        "asset_hash": asset["asset_hash"],
        "binding_gate_hash": gate["gate_hash"],
        "binding_status": gate["status"],
        "checkpoint_root_hash": common["checkpoint_root_hash"],
        "checkpoint_tree_size": common["checkpoint_tree_size"],
        "lifecycle_receipt_hashes": lifecycle_receipt_hashes,
        "occurrence_auditor_id": common["occurrence_auditor_id"],
        "occurrence_auditor_key_id": common["occurrence_auditor_key_id"],
        "occurrence_auditor_public_key_sha256": common[
            "occurrence_auditor_public_key_sha256"
        ],
        "persistence_namespace": registration["persistence_namespace"],
        "persistence_provider_id": registration["persistence_provider_id"],
        "persistence_provider_key_id": registration[
            "persistence_provider_key_id"
        ],
        "persistence_provider_public_key_sha256": registration[
            "persistence_provider_public_key_sha256"
        ],
        "persistence_registration_hash": registration["registration_hash"],
        "previous_asset_hash": asset["previous_persisted_asset_hash"],
        "previous_checkpoint_hash": common["previous_checkpoint_hash"],
        "previous_checkpoint_root_hash": common[
            "previous_checkpoint_root_hash"
        ],
        "previous_checkpoint_tree_size": common[
            "previous_checkpoint_tree_size"
        ],
        "replay_binding_preregistration_hash": source_preregistration[
            "preregistration_hash"
        ],
        "replay_registry_id": common["replay_registry_id"],
        "replay_registry_key_id": common["replay_registry_key_id"],
        "replay_registry_namespace": common["replay_registry_namespace"],
        "replay_registry_public_key_sha256": common[
            "replay_registry_public_key_sha256"
        ],
        "study_identity_hash": source_preregistration["study_identity_hash"],
        "window_order_hash": source_preregistration["window_order_hash"],
    }
    if (
        not _exact_hash(record["asset_hash"])
        or not _exact_hash(record["binding_gate_hash"])
        or not _exact_hash(record["checkpoint_root_hash"])
        or not _native_nonnegative_int(record["checkpoint_tree_size"])
        or not _exact_hash(record["previous_checkpoint_root_hash"])
        or not _native_nonnegative_int(record["previous_checkpoint_tree_size"])
        or record["previous_checkpoint_tree_size"]
        >= record["checkpoint_tree_size"]
        or _utc(record["asset_created_at_utc"]) is None
    ):
        return None
    return record


def _facts(mode: str | None, *, verified: bool) -> dict[str, Any]:
    return {
        "authoritative_future_pin_verified": False,
        "complete_persisted_checkpoint_history_verified": False,
        "current_binding_exactly_verified": verified,
        "durable_checkpoint_publication_verified": False,
        "external_persistence_provider_authority_verified": False,
        "longitudinal_checkpoint_coverage_verified": False,
        "paper_authorized": False,
        "persisted_checkpoint_lineage_segment_verified": verified,
        "previous_binding_exactly_verified": (
            verified and mode == PREVIOUS_PERSISTED_ASSET_MODE
        ),
        "previous_persisted_asset_lineage_verified": (
            verified and mode == PREVIOUS_PERSISTED_ASSET_MODE
        ),
        "profitability_proven": False,
        "registered_source_pin_anchor_verified": (
            verified and mode == REGISTERED_SOURCE_PIN_MODE
        ),
        "runtime_mutations_performed": False,
        "synthetic_only": True,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "activation_blockers": list(_BASE_BLOCKERS),
            "authority": deepcopy(_AUTHORITY),
            "facts": _facts(None, verified=False),
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "lineage_mode": None,
            "reason_code": "UNKNOWN_PERSISTED_CHECKPOINT_LINEAGE",
            "schema_version": SCHEMA_VERSION,
            "source": None,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
        },
        "gate_hash",
    )


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
    current_segment: Any,
    previous_segment: Any = None,
) -> dict[str, Any]:
    if not _segment_exact(current_segment):
        return _unknown("CURRENT_PERSISTENCE_BINDING_EXACT_REBUILD_FAILED")
    current = _segment_record(current_segment)
    if current is None:
        return _unknown("CURRENT_PERSISTENCE_BINDING_FACTS_INVALID")

    if previous_segment is None:
        mode = REGISTERED_SOURCE_PIN_MODE
        if current["previous_asset_hash"] is not None:
            return _unknown("REGISTERED_SOURCE_PIN_REQUIRES_NULL_PREVIOUS_ASSET")
        anchor = {
            "previous_checkpoint_hash": current["previous_checkpoint_hash"],
            "previous_checkpoint_root_hash": current[
                "previous_checkpoint_root_hash"
            ],
            "previous_checkpoint_tree_size": current[
                "previous_checkpoint_tree_size"
            ],
            "replay_registry_id": current["replay_registry_id"],
            "replay_registry_namespace": current["replay_registry_namespace"],
        }
        previous = None
        lineage_anchor_hash = strict_canonical_hash(anchor)
    else:
        mode = PREVIOUS_PERSISTED_ASSET_MODE
        if not _segment_exact(previous_segment):
            return _unknown("PREVIOUS_PERSISTENCE_BINDING_EXACT_REBUILD_FAILED")
        previous = _segment_record(previous_segment)
        if previous is None:
            return _unknown("PREVIOUS_PERSISTENCE_BINDING_FACTS_INVALID")
        if current["previous_asset_hash"] != previous["asset_hash"]:
            return _unknown("PREVIOUS_PERSISTED_ASSET_HASH_MISMATCH")
        if (
            current["previous_checkpoint_tree_size"]
            != previous["checkpoint_tree_size"]
            or current["previous_checkpoint_root_hash"]
            != previous["checkpoint_root_hash"]
        ):
            return _unknown("PREVIOUS_CHECKPOINT_CONTENT_MISMATCH")
        if current["checkpoint_tree_size"] <= previous["checkpoint_tree_size"]:
            return _unknown("CHECKPOINT_TREE_SIZE_NOT_STRICTLY_INCREASING")
        if any(current[field] != previous[field] for field in _STABLE_LINEAGE_FIELDS):
            return _unknown("PERSISTED_CHECKPOINT_STABLE_LINEAGE_DRIFT")
        previous_created = _utc(previous["asset_created_at_utc"])
        current_created = _utc(current["asset_created_at_utc"])
        if (
            previous_created is None
            or current_created is None
            or not previous_created < current_created
        ):
            return _unknown("PERSISTED_ASSET_TIME_NOT_STRICTLY_INCREASING")
        lineage_anchor_hash = previous["asset_hash"]

    gate_blockers = (
        ["PERSISTENCE_SOURCE_BINDING_GATE_V1_BLOCKED"]
        if current["binding_status"] == "BLOCK"
        else []
    )
    status = "BLOCK" if gate_blockers else "PASS"
    document = {
        "activation_blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": _facts(mode, verified=True),
        "gate_blockers": gate_blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "lineage_mode": mode,
        "reason_code": (
            "BLOCK_PERSISTED_CHECKPOINT_LINEAGE"
            if status == "BLOCK"
            else "PASS_PERSISTED_CHECKPOINT_LINEAGE"
        ),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "current_asset_hash": current["asset_hash"],
            "current_binding_gate_hash": current["binding_gate_hash"],
            "lineage_anchor_hash": lineage_anchor_hash,
            "persistence_binding_v1_implementation_sha256": (
                PERSISTENCE_BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "previous_asset_hash": (
                previous["asset_hash"] if previous is not None else None
            ),
            "previous_binding_gate_hash": (
                previous["binding_gate_hash"] if previous is not None else None
            ),
            "study_identity_hash": current["study_identity_hash"],
            "window_order_hash": current["window_order_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "current_checkpoint_tree_size": current["checkpoint_tree_size"],
            "lineage_segment_count": 1,
            "previous_checkpoint_tree_size": current[
                "previous_checkpoint_tree_size"
            ],
            "reverified_persisted_asset_count": (
                2 if previous is not None else 1
            ),
        },
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
    document: Any,
    current_segment: Any,
    previous_segment: Any = None,
    *,
    expected_gate_hash: Any,
) -> bool:
    if (
        type(document) is not dict
        or not _exact_hash(expected_gate_hash)
        or document.get("gate_hash") != expected_gate_hash
    ):
        return False
    try:
        rebuilt = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1(
            current_segment,
            previous_segment,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, rebuilt)
        and compare_digest(document["gate_hash"], rebuilt["gate_hash"])
    )


__all__ = [
    "GATE_CONTRACT_HASH",
    "PERSISTENCE_BINDING_V1_IMPLEMENTATION_SHA256",
    "PREVIOUS_PERSISTED_ASSET_MODE",
    "REGISTERED_SOURCE_PIN_MODE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_lineage_gate_v1",
]
