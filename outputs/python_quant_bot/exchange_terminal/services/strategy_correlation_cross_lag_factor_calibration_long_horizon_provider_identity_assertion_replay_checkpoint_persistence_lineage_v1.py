from __future__ import annotations

import re
from typing import Any

from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 import (
    GENESIS_ROOT_HASH,
)
from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_binding_v1 import (
    verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


LINEAGE_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-lineage-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20261001-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-lineage-1"
)
VERIFIED_STATUS = (
    "GENESIS_OR_PREVIOUS_PERSISTED_CHECKPOINT_CONTENT_BOUND_"
    "EXTERNAL_TRUST_AND_DURABILITY_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SEGMENT_FIELDS = frozenset(
    {
        "binding",
        "replay_evaluation",
        "replay_inputs",
        "persistence_evaluation",
        "persistence_inputs",
    }
)


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _authority() -> dict[str, bool]:
    return {
        "pinned_checkpoint_authoritative": False,
        "durable_write_verified": False,
        "durable_reopen_verified": False,
        "complete_history_verified": False,
        "replay_registry_checked": False,
        "replay_absence_verified": False,
        "assertion_uniqueness_verified": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _facts(*, verified: bool, genesis: bool) -> dict[str, bool]:
    return {
        "current_binding_verified": verified,
        "previous_binding_verified": verified and not genesis,
        "genesis_anchor_verified": verified and genesis,
        "previous_pinned_asset_content_verified": verified and not genesis,
        "lineage_segment_verified": verified,
        "tree_size_monotonic": verified,
        "local_history_to_registered_genesis_verified": verified and genesis,
        "complete_history_verified": False,
        "external_replay_registry_trust_attested": False,
        "external_persistence_provider_trust_attested": False,
        "external_durability_attested": False,
        "external_time_attested": False,
        "assertion_uniqueness_verified": False,
        "replay_absence_verified": False,
    }


def _empty_evidence() -> dict[str, Any]:
    return {
        "lineage_mode": None,
        "current_binding_receipt_hash": None,
        "previous_binding_receipt_hash": None,
        "replay_registration_receipt_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "previous_asset_hash": None,
        "previous_tree_size": None,
        "previous_root_hash": None,
        "current_asset_hash": None,
        "current_tree_size": None,
        "current_root_hash": None,
        "current_checkpoint_hash": None,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema": LINEAGE_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason": reason,
        "evidence": _empty_evidence(),
        "facts": _facts(verified=False, genesis=False),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _exact_segment(value: Any) -> bool:
    return type(value) is dict and set(value) == _SEGMENT_FIELDS


def _verify_segment(segment: dict[str, Any]) -> bool:
    try:
        return verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(
            segment["binding"],
            replay_evaluation=segment["replay_evaluation"],
            replay_inputs=segment["replay_inputs"],
            persistence_evaluation=segment["persistence_evaluation"],
            persistence_inputs=segment["persistence_inputs"],
        )
    except Exception:
        return False


def evaluate_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(
    *,
    current_segment: Any,
    previous_segment: Any = None,
) -> dict[str, Any]:
    if not _exact_segment(current_segment):
        return _unknown("current_segment_shape_invalid")
    if previous_segment is not None and not _exact_segment(previous_segment):
        return _unknown("previous_segment_shape_invalid")
    if not _verify_segment(current_segment):
        return _unknown("current_binding_unverified")
    if previous_segment is not None and not _verify_segment(previous_segment):
        return _unknown("previous_binding_unverified")

    current_binding = current_segment.get("binding")
    current_replay = current_segment.get("replay_evaluation")
    current_persistence_inputs = current_segment.get("persistence_inputs")
    if not all(type(value) is dict for value in (current_binding, current_replay, current_persistence_inputs)):
        return _unknown("current_lineage_evidence_shape_invalid")
    current_binding_evidence = current_binding.get("evidence")
    current_replay_evidence = current_replay.get("evidence")
    current_asset = current_persistence_inputs.get("checkpoint_asset")
    if not all(type(value) is dict for value in (current_binding_evidence, current_replay_evidence, current_asset)):
        return _unknown("current_lineage_evidence_missing")
    current_size = current_binding_evidence.get("checkpoint_tree_size")
    if type(current_size) is not int or current_size < 1:
        return _unknown("current_checkpoint_tree_size_invalid")

    genesis = previous_segment is None
    if genesis:
        if current_asset.get("previous_pinned_asset_hash") is not None:
            return _unknown("genesis_previous_asset_hash_not_null")
        if type(current_replay_evidence.get("pinned_tree_size")) is not int or current_replay_evidence.get("pinned_tree_size") != 0:
            return _unknown("genesis_pinned_tree_size_invalid")
        if current_replay_evidence.get("pinned_root_hash") != GENESIS_ROOT_HASH:
            return _unknown("genesis_pinned_root_hash_mismatch")
        previous_binding_hash = None
        previous_asset_hash = None
        previous_size = 0
        previous_root = GENESIS_ROOT_HASH
        lineage_mode = "REGISTERED_GENESIS"
    else:
        previous_binding = previous_segment.get("binding")
        previous_persistence_inputs = previous_segment.get("persistence_inputs")
        if type(previous_binding) is not dict or type(previous_persistence_inputs) is not dict:
            return _unknown("previous_lineage_evidence_shape_invalid")
        previous_evidence = previous_binding.get("evidence")
        previous_asset = previous_persistence_inputs.get("checkpoint_asset")
        if type(previous_evidence) is not dict or type(previous_asset) is not dict:
            return _unknown("previous_lineage_evidence_missing")
        previous_binding_hash = previous_binding.get("receipt_hash")
        previous_asset_hash = previous_evidence.get("asset_hash")
        previous_size = previous_evidence.get("checkpoint_tree_size")
        previous_root = previous_evidence.get("checkpoint_root_hash")
        if not _strict_sha256(previous_binding_hash) or not _strict_sha256(previous_asset_hash):
            return _unknown("previous_lineage_hash_invalid")
        if current_asset.get("previous_pinned_asset_hash") != previous_asset_hash:
            return _unknown("previous_pinned_asset_hash_mismatch")
        if not strict_json_contract_equal(current_replay_evidence.get("pinned_tree_size"), previous_size):
            return _unknown("previous_pinned_tree_size_mismatch")
        if current_replay_evidence.get("pinned_root_hash") != previous_root:
            return _unknown("previous_pinned_root_hash_mismatch")
        for field in ("replay_registry_id", "replay_registry_namespace", "replay_registration_receipt_hash"):
            if not strict_json_contract_equal(current_binding_evidence.get(field), previous_evidence.get(field)):
                return _unknown(f"lineage_{field}_mismatch")
        if type(previous_size) is not int or previous_size < 1 or previous_size >= current_size:
            return _unknown("checkpoint_tree_size_not_strictly_increasing")
        if previous_asset.get("asset_hash") != previous_asset_hash:
            return _unknown("previous_asset_content_hash_mismatch")
        lineage_mode = "PREVIOUS_PERSISTED_ASSET"

    evidence = {
        "lineage_mode": lineage_mode,
        "current_binding_receipt_hash": current_binding["receipt_hash"],
        "previous_binding_receipt_hash": previous_binding_hash,
        "replay_registration_receipt_hash": current_binding_evidence["replay_registration_receipt_hash"],
        "replay_registry_id": current_binding_evidence["replay_registry_id"],
        "replay_registry_namespace": current_binding_evidence["replay_registry_namespace"],
        "previous_asset_hash": previous_asset_hash,
        "previous_tree_size": previous_size,
        "previous_root_hash": previous_root,
        "current_asset_hash": current_binding_evidence["asset_hash"],
        "current_tree_size": current_size,
        "current_root_hash": current_binding_evidence["checkpoint_root_hash"],
        "current_checkpoint_hash": current_binding_evidence["checkpoint_hash"],
    }
    document = {
        "schema": LINEAGE_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": VERIFIED_STATUS,
        "reason": "adjacent_persisted_checkpoint_lineage_verified_external_trust_and_durability_unproven",
        "evidence": evidence,
        "facts": _facts(verified=True, genesis=genesis),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(
    lineage: Any,
    *,
    current_segment: Any,
    previous_segment: Any = None,
) -> bool:
    if type(lineage) is not dict or not _strict_sha256(lineage.get("receipt_hash")):
        return False
    expected = evaluate_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(
        current_segment=current_segment,
        previous_segment=previous_segment,
    )
    if expected.get("status") != VERIFIED_STATUS:
        return False
    return strict_json_contract_equal(lineage, expected)


__all__ = [
    "LINEAGE_SCHEMA",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "evaluate_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1",
    "verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1",
]
