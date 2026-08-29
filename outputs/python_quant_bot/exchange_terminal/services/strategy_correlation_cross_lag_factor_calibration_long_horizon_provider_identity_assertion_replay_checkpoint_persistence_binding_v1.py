from __future__ import annotations

import re
from typing import Any

from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_receipt_verifier_v1 import (
    verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1,
)
from .strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_receipt_verifier_v1 import (
    verify_provider_identity_assertion_replay_receipt_evaluation_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


BINDING_SCHEMA = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-assertion-replay-checkpoint-persistence-binding-candidate-v1"
)
STATIC_FINGERPRINT = (
    "20260930-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "assertion-replay-checkpoint-persistence-binding-1"
)
BOUND_STATUS = (
    "REPLAY_EVALUATION_AND_PERSISTED_ASSET_BOUND_"
    "EXTERNAL_TRUST_AND_DURABILITY_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REPLAY_INPUT_FIELDS = frozenset(
    {
        "registration",
        "registration_receipt",
        "replay_receipt",
        "replay_registry_public_key",
        "pinned_checkpoint",
    }
)
_PERSISTENCE_INPUT_FIELDS = frozenset(
    {
        "replay_registration",
        "replay_registration_receipt",
        "persistence_configuration",
        "persistence_registration_receipt",
        "persistence_provider_public_key",
        "checkpoint_asset",
        "write_receipt",
        "reopen_receipt",
    }
)


def _strict_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _authority() -> dict[str, bool]:
    return {
        "pinned_checkpoint_authoritative": False,
        "durable_write_verified": False,
        "durable_reopen_verified": False,
        "replay_registry_checked": False,
        "replay_absence_verified": False,
        "assertion_uniqueness_verified": False,
        "provider_identity_verified": False,
        "observation_admitted": False,
        "parameter_selection_authority": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _facts(*, bound: bool) -> dict[str, bool]:
    return {
        "replay_evaluation_verified": bound,
        "persistence_evaluation_verified": bound,
        "source_registration_lineage_verified": bound,
        "source_replay_evaluation_verified": bound,
        "current_checkpoint_fields_bound": bound,
        "persistence_asset_bound": bound,
        "previous_pinned_asset_content_verified": False,
        "external_replay_registry_trust_attested": False,
        "external_persistence_provider_trust_attested": False,
        "external_durability_attested": False,
        "external_time_attested": False,
        "assertion_uniqueness_verified": False,
        "replay_absence_verified": False,
    }


def _empty_evidence() -> dict[str, Any]:
    return {
        "replay_evaluation_receipt_hash": None,
        "persistence_evaluation_receipt_hash": None,
        "replay_registration_receipt_hash": None,
        "persistence_registration_receipt_hash": None,
        "asset_hash": None,
        "previous_pinned_asset_hash": None,
        "replay_registry_id": None,
        "replay_registry_namespace": None,
        "pinned_tree_size": None,
        "pinned_root_hash": None,
        "checkpoint_tree_size": None,
        "checkpoint_root_hash": None,
        "checkpoint_hash": None,
    }


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "schema": BINDING_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "reason": reason,
        "evidence": _empty_evidence(),
        "facts": _facts(bound=False),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def _exact_bundle(value: Any, fields: frozenset[str]) -> bool:
    return type(value) is dict and set(value) == fields


def evaluate_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(
    *,
    replay_evaluation: Any,
    replay_inputs: Any,
    persistence_evaluation: Any,
    persistence_inputs: Any,
) -> dict[str, Any]:
    if type(replay_evaluation) is not dict or not _strict_sha256(replay_evaluation.get("receipt_hash")):
        return _unknown("replay_evaluation_invalid")
    if type(persistence_evaluation) is not dict or not _strict_sha256(persistence_evaluation.get("receipt_hash")):
        return _unknown("persistence_evaluation_invalid")
    if not _exact_bundle(replay_inputs, _REPLAY_INPUT_FIELDS):
        return _unknown("replay_inputs_shape_invalid")
    if not _exact_bundle(persistence_inputs, _PERSISTENCE_INPUT_FIELDS):
        return _unknown("persistence_inputs_shape_invalid")

    try:
        replay_verified = verify_provider_identity_assertion_replay_receipt_evaluation_v1(
            replay_evaluation,
            registration=replay_inputs["registration"],
            registration_receipt=replay_inputs["registration_receipt"],
            replay_receipt=replay_inputs["replay_receipt"],
            replay_registry_public_key=replay_inputs["replay_registry_public_key"],
            pinned_checkpoint=replay_inputs["pinned_checkpoint"],
        )
    except Exception:
        replay_verified = False
    if not replay_verified:
        return _unknown("replay_evaluation_unverified")

    try:
        persistence_verified = verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1(
            persistence_evaluation,
            replay_registration=persistence_inputs["replay_registration"],
            replay_registration_receipt=persistence_inputs["replay_registration_receipt"],
            persistence_configuration=persistence_inputs["persistence_configuration"],
            persistence_registration_receipt=persistence_inputs["persistence_registration_receipt"],
            persistence_provider_public_key=persistence_inputs["persistence_provider_public_key"],
            checkpoint_asset=persistence_inputs["checkpoint_asset"],
            write_receipt=persistence_inputs["write_receipt"],
            reopen_receipt=persistence_inputs["reopen_receipt"],
        )
    except Exception:
        persistence_verified = False
    if not persistence_verified:
        return _unknown("persistence_evaluation_unverified")

    if not strict_json_contract_equal(
        replay_inputs["registration"],
        persistence_inputs["replay_registration"],
    ):
        return _unknown("source_replay_registration_lineage_mismatch")
    if not strict_json_contract_equal(
        replay_inputs["registration_receipt"],
        persistence_inputs["replay_registration_receipt"],
    ):
        return _unknown("source_replay_registration_receipt_lineage_mismatch")

    replay_evidence = replay_evaluation.get("evidence")
    persistence_evidence = persistence_evaluation.get("evidence")
    asset = persistence_inputs.get("checkpoint_asset")
    persistence_registration = persistence_inputs.get("persistence_registration_receipt")
    if not all(type(value) is dict for value in (replay_evidence, persistence_evidence, asset, persistence_registration)):
        return _unknown("binding_evidence_shape_invalid")

    replay_registration_receipt_hash = replay_inputs["registration_receipt"].get("receipt_hash") if type(replay_inputs["registration_receipt"]) is dict else None
    if replay_evidence.get("registration_receipt_hash") != replay_registration_receipt_hash:
        return _unknown("replay_evaluation_registration_receipt_hash_mismatch")
    source_registration = persistence_registration.get("source_replay_registration")
    if type(source_registration) is not dict or source_registration.get("replay_registration_receipt_hash") != replay_registration_receipt_hash:
        return _unknown("persistence_registration_source_lineage_mismatch")

    if asset.get("source_replay_verifier_receipt_hash") != replay_evaluation["receipt_hash"]:
        return _unknown("asset_source_replay_evaluation_hash_mismatch")
    current_bindings = {
        "replay_registry_id": "replay_registry_id",
        "replay_registry_namespace": "replay_registry_namespace",
        "tree_size": "checkpoint_tree_size",
        "root_hash": "checkpoint_root_hash",
        "checkpoint_hash": "checkpoint_hash",
    }
    for asset_field, replay_field in current_bindings.items():
        if not strict_json_contract_equal(asset.get(asset_field), replay_evidence.get(replay_field)):
            return _unknown(f"asset_{asset_field}_replay_evaluation_mismatch")

    persistence_bindings = {
        "asset_hash": asset.get("asset_hash"),
        "previous_pinned_asset_hash": asset.get("previous_pinned_asset_hash"),
        "replay_registry_id": asset.get("replay_registry_id"),
        "replay_registry_namespace": asset.get("replay_registry_namespace"),
        "tree_size": asset.get("tree_size"),
        "root_hash": asset.get("root_hash"),
        "checkpoint_hash": asset.get("checkpoint_hash"),
        "source_replay_verifier_receipt_hash": replay_evaluation["receipt_hash"],
    }
    for field, expected in persistence_bindings.items():
        if not strict_json_contract_equal(persistence_evidence.get(field), expected):
            return _unknown(f"persistence_evaluation_{field}_mismatch")
    persistence_registration_hash = persistence_inputs["persistence_registration_receipt"].get("receipt_hash")
    if persistence_evidence.get("persistence_registration_receipt_hash") != persistence_registration_hash:
        return _unknown("persistence_evaluation_registration_receipt_hash_mismatch")

    evidence = {
        "replay_evaluation_receipt_hash": replay_evaluation["receipt_hash"],
        "persistence_evaluation_receipt_hash": persistence_evaluation["receipt_hash"],
        "replay_registration_receipt_hash": replay_registration_receipt_hash,
        "persistence_registration_receipt_hash": persistence_registration_hash,
        "asset_hash": asset["asset_hash"],
        "previous_pinned_asset_hash": asset.get("previous_pinned_asset_hash"),
        "replay_registry_id": asset["replay_registry_id"],
        "replay_registry_namespace": asset["replay_registry_namespace"],
        "pinned_tree_size": replay_evidence.get("pinned_tree_size"),
        "pinned_root_hash": replay_evidence.get("pinned_root_hash"),
        "checkpoint_tree_size": asset["tree_size"],
        "checkpoint_root_hash": asset["root_hash"],
        "checkpoint_hash": asset["checkpoint_hash"],
    }
    document = {
        "schema": BINDING_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": BOUND_STATUS,
        "reason": "replay_evaluation_and_persisted_asset_bound_external_trust_and_durability_unproven",
        "evidence": evidence,
        "facts": _facts(bound=True),
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "receipt_hash")


def verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(
    binding: Any,
    *,
    replay_evaluation: Any,
    replay_inputs: Any,
    persistence_evaluation: Any,
    persistence_inputs: Any,
) -> bool:
    if type(binding) is not dict or not _strict_sha256(binding.get("receipt_hash")):
        return False
    expected = evaluate_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(
        replay_evaluation=replay_evaluation,
        replay_inputs=replay_inputs,
        persistence_evaluation=persistence_evaluation,
        persistence_inputs=persistence_inputs,
    )
    if expected.get("status") != BOUND_STATUS:
        return False
    return strict_json_contract_equal(binding, expected)


__all__ = [
    "BINDING_SCHEMA",
    "BOUND_STATUS",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "evaluate_provider_identity_assertion_replay_checkpoint_persistence_binding_v1",
    "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1",
]
