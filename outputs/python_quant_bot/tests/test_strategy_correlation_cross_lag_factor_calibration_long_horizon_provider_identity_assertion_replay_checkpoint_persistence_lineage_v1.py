from __future__ import annotations

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1 as subject
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 import GENESIS_ROOT_HASH


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _segment(label: str, *, tree_size: int, root_hash: str, pinned_size: int, pinned_root: str, previous_asset_hash: str | None) -> dict[str, object]:
    asset_hash = _hash(f"{label}-asset")
    registration_hash = _hash("shared-registration")
    return {
        "binding": {
            "receipt_hash": _hash(f"{label}-binding"),
            "evidence": {
                "asset_hash": asset_hash,
                "replay_registration_receipt_hash": registration_hash,
                "replay_registry_id": "registry-v1",
                "replay_registry_namespace": "hakimi.registry",
                "checkpoint_tree_size": tree_size,
                "checkpoint_root_hash": root_hash,
                "checkpoint_hash": _hash(f"{label}-checkpoint"),
            },
        },
        "replay_evaluation": {
            "receipt_hash": _hash(f"{label}-replay"),
            "evidence": {
                "pinned_tree_size": pinned_size,
                "pinned_root_hash": pinned_root,
            },
        },
        "replay_inputs": {},
        "persistence_evaluation": {},
        "persistence_inputs": {
            "checkpoint_asset": {
                "asset_hash": asset_hash,
                "previous_pinned_asset_hash": previous_asset_hash,
            }
        },
    }


def _fixture() -> dict[str, object]:
    previous_root = _hash("previous-root")
    previous = _segment("previous", tree_size=3, root_hash=previous_root, pinned_size=0, pinned_root=GENESIS_ROOT_HASH, previous_asset_hash=None)
    current = _segment("current", tree_size=7, root_hash=_hash("current-root"), pinned_size=3, pinned_root=previous_root, previous_asset_hash=previous["binding"]["evidence"]["asset_hash"])
    genesis = _segment("first", tree_size=1, root_hash=_hash("first-root"), pinned_size=0, pinned_root=GENESIS_ROOT_HASH, previous_asset_hash=None)
    return {"previous": previous, "current": current, "genesis": genesis}


def _evaluate(current: dict[str, object], previous: dict[str, object] | None, *, current_ok: bool = True, previous_ok: bool = True) -> dict[str, object]:
    results = [current_ok] if previous is None else [current_ok, previous_ok]
    with patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1", side_effect=results):
        return subject.evaluate_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(current_segment=current, previous_segment=previous)


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceLineageV1Tests(unittest.TestCase):
    def test_previous_asset_lineage_is_verified_but_authority_negative(self) -> None:
        fixture = _fixture(); result = _evaluate(fixture["current"], fixture["previous"])
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["previous_pinned_asset_content_verified"])
        self.assertTrue(result["facts"]["tree_size_monotonic"])
        self.assertFalse(result["facts"]["complete_history_verified"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_registered_genesis_lineage_is_verified(self) -> None:
        result = _evaluate(_fixture()["genesis"], None)
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["genesis_anchor_verified"])
        self.assertTrue(result["facts"]["local_history_to_registered_genesis_verified"])
        self.assertFalse(result["facts"]["previous_pinned_asset_content_verified"])

    def test_binding_verifier_is_called_for_both_segments(self) -> None:
        fixture = _fixture()
        with patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1", return_value=True) as verifier:
            result = subject.evaluate_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(current_segment=fixture["current"], previous_segment=fixture["previous"])
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertEqual(verifier.call_count, 2)

    def test_lineage_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"]), _evaluate(fixture["current"], fixture["previous"]))

    def test_lineage_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture(); lineage = _evaluate(fixture["current"], fixture["previous"])
        with patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1", return_value=True):
            self.assertTrue(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(lineage, current_segment=fixture["current"], previous_segment=fixture["previous"]))

    def test_lineage_verifier_rejects_tampering(self) -> None:
        fixture = _fixture(); lineage = _evaluate(fixture["current"], fixture["previous"]); lineage["facts"]["external_durability_attested"] = True
        with patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1", return_value=True):
            self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(lineage, current_segment=fixture["current"], previous_segment=fixture["previous"]))

    def test_lineage_verifier_rejects_bool_int_alias(self) -> None:
        fixture = _fixture(); lineage = _evaluate(fixture["current"], fixture["previous"]); lineage["authority"]["live_allowed"] = 0
        with patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1", return_value=True):
            self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1(lineage, current_segment=fixture["current"], previous_segment=fixture["previous"]))

    def test_current_segment_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["current"]["legacy"] = True
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_previous_segment_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["previous"].pop("replay_inputs")
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_current_binding_must_verify(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"], current_ok=False)["status"], subject.UNKNOWN_STATUS)

    def test_previous_binding_must_verify(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"], previous_ok=False)["status"], subject.UNKNOWN_STATUS)

    def test_current_evidence_shape_is_required(self) -> None:
        fixture = _fixture(); fixture["current"]["binding"]["evidence"] = None
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_previous_evidence_shape_is_required(self) -> None:
        fixture = _fixture(); fixture["previous"]["binding"]["evidence"] = None
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_previous_asset_hash_must_match_content(self) -> None:
        fixture = _fixture(); fixture["current"]["persistence_inputs"]["checkpoint_asset"]["previous_pinned_asset_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_pinned_tree_size_must_match_previous_content(self) -> None:
        fixture = _fixture(); fixture["current"]["replay_evaluation"]["evidence"]["pinned_tree_size"] = 2
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_pinned_root_must_match_previous_content(self) -> None:
        fixture = _fixture(); fixture["current"]["replay_evaluation"]["evidence"]["pinned_root_hash"] = _hash("other-root")
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_registry_id_lineage_is_exact(self) -> None:
        fixture = _fixture(); fixture["previous"]["binding"]["evidence"]["replay_registry_id"] = "other-registry"
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_registry_namespace_lineage_is_exact(self) -> None:
        fixture = _fixture(); fixture["previous"]["binding"]["evidence"]["replay_registry_namespace"] = "other.namespace"
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_registration_lineage_is_exact(self) -> None:
        fixture = _fixture(); fixture["previous"]["binding"]["evidence"]["replay_registration_receipt_hash"] = _hash("other-registration")
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_tree_size_must_be_strictly_increasing(self) -> None:
        for value in (3, 2):
            with self.subTest(value=value):
                fixture = _fixture(); fixture["current"]["binding"]["evidence"]["checkpoint_tree_size"] = value
                self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_tree_size_comparison_is_type_sensitive(self) -> None:
        fixture = _fixture(); fixture["previous"]["binding"]["evidence"]["checkpoint_tree_size"] = True
        self.assertEqual(_evaluate(fixture["current"], fixture["previous"])["status"], subject.UNKNOWN_STATUS)

    def test_genesis_requires_null_previous_asset_hash(self) -> None:
        fixture = _fixture(); fixture["genesis"]["persistence_inputs"]["checkpoint_asset"]["previous_pinned_asset_hash"] = _hash("unexpected")
        self.assertEqual(_evaluate(fixture["genesis"], None)["status"], subject.UNKNOWN_STATUS)

    def test_genesis_requires_native_zero_tree_size(self) -> None:
        for value in (False, 1):
            with self.subTest(value=value):
                fixture = _fixture(); fixture["genesis"]["replay_evaluation"]["evidence"]["pinned_tree_size"] = value
                self.assertEqual(_evaluate(fixture["genesis"], None)["status"], subject.UNKNOWN_STATUS)

    def test_genesis_requires_registered_root(self) -> None:
        fixture = _fixture(); fixture["genesis"]["replay_evaluation"]["evidence"]["pinned_root_hash"] = _hash("false-genesis")
        self.assertEqual(_evaluate(fixture["genesis"], None)["status"], subject.UNKNOWN_STATUS)

    def test_unknown_never_exposes_authority_or_segments(self) -> None:
        result = _evaluate(None, None)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["facts"].values()))
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn('"binding":', serialized)
        self.assertNotIn('"replay_inputs":', serialized)
        self.assertNotIn('"persistence_inputs":', serialized)


if __name__ == "__main__":
    unittest.main()
