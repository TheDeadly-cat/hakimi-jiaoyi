from __future__ import annotations

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_binding_v1 as subject


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _fixture() -> dict[str, object]:
    replay_registration = {"schema": "replay-registration", "id": "same-source"}
    replay_registration_receipt = {"receipt_hash": _hash("replay-registration")}
    replay_evaluation = {
        "receipt_hash": _hash("replay-evaluation"),
        "evidence": {
            "registration_receipt_hash": replay_registration_receipt["receipt_hash"],
            "replay_registry_id": "registry-v1",
            "replay_registry_namespace": "hakimi.registry",
            "pinned_tree_size": 3,
            "pinned_root_hash": _hash("pinned-root"),
            "checkpoint_tree_size": 7,
            "checkpoint_root_hash": _hash("checkpoint-root"),
            "checkpoint_hash": _hash("checkpoint"),
        },
    }
    asset = {
        "asset_hash": _hash("asset"),
        "previous_pinned_asset_hash": _hash("previous-asset"),
        "source_replay_verifier_receipt_hash": replay_evaluation["receipt_hash"],
        "replay_registry_id": "registry-v1",
        "replay_registry_namespace": "hakimi.registry",
        "tree_size": 7,
        "root_hash": _hash("checkpoint-root"),
        "checkpoint_hash": _hash("checkpoint"),
    }
    persistence_registration_receipt = {
        "receipt_hash": _hash("persistence-registration"),
        "source_replay_registration": {
            "replay_registration_receipt_hash": replay_registration_receipt["receipt_hash"]
        },
    }
    persistence_evaluation = {
        "receipt_hash": _hash("persistence-evaluation"),
        "evidence": {
            "persistence_registration_receipt_hash": persistence_registration_receipt["receipt_hash"],
            "asset_hash": asset["asset_hash"],
            "previous_pinned_asset_hash": asset["previous_pinned_asset_hash"],
            "source_replay_verifier_receipt_hash": replay_evaluation["receipt_hash"],
            "replay_registry_id": asset["replay_registry_id"],
            "replay_registry_namespace": asset["replay_registry_namespace"],
            "tree_size": asset["tree_size"],
            "root_hash": asset["root_hash"],
            "checkpoint_hash": asset["checkpoint_hash"],
        },
    }
    replay_inputs = {
        "registration": replay_registration,
        "registration_receipt": replay_registration_receipt,
        "replay_receipt": {},
        "replay_registry_public_key": "public-key",
        "pinned_checkpoint": {},
    }
    persistence_inputs = {
        "replay_registration": copy.deepcopy(replay_registration),
        "replay_registration_receipt": copy.deepcopy(replay_registration_receipt),
        "persistence_configuration": {},
        "persistence_registration_receipt": persistence_registration_receipt,
        "persistence_provider_public_key": "public-key",
        "checkpoint_asset": asset,
        "write_receipt": {},
        "reopen_receipt": {},
    }
    return {
        "replay_evaluation": replay_evaluation,
        "replay_inputs": replay_inputs,
        "persistence_evaluation": persistence_evaluation,
        "persistence_inputs": persistence_inputs,
    }


def _evaluate(fixture: dict[str, object], *, replay_ok: bool = True, persistence_ok: bool = True) -> dict[str, object]:
    with patch.object(subject, "verify_provider_identity_assertion_replay_receipt_evaluation_v1", return_value=replay_ok), patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1", return_value=persistence_ok):
        return subject.evaluate_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(
            replay_evaluation=fixture["replay_evaluation"],
            replay_inputs=fixture["replay_inputs"],
            persistence_evaluation=fixture["persistence_evaluation"],
            persistence_inputs=fixture["persistence_inputs"],
        )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceBindingV1Tests(unittest.TestCase):
    def test_valid_binding_is_sealed_and_authority_negative(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["schema"], subject.BINDING_SCHEMA)
        self.assertEqual(result["status"], subject.BOUND_STATUS)
        self.assertTrue(result["facts"]["source_replay_evaluation_verified"])
        self.assertTrue(result["facts"]["persistence_asset_bound"])
        self.assertFalse(result["facts"]["external_durability_attested"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_both_verifiers_are_called(self) -> None:
        fixture = _fixture()
        with patch.object(subject, "verify_provider_identity_assertion_replay_receipt_evaluation_v1", return_value=True) as replay_verify, patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1", return_value=True) as persistence_verify:
            result = subject.evaluate_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(replay_evaluation=fixture["replay_evaluation"], replay_inputs=fixture["replay_inputs"], persistence_evaluation=fixture["persistence_evaluation"], persistence_inputs=fixture["persistence_inputs"])
        self.assertEqual(result["status"], subject.BOUND_STATUS)
        replay_verify.assert_called_once()
        persistence_verify.assert_called_once()

    def test_binding_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_binding_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture(); binding = _evaluate(fixture)
        with patch.object(subject, "verify_provider_identity_assertion_replay_receipt_evaluation_v1", return_value=True), patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1", return_value=True):
            self.assertTrue(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(binding, replay_evaluation=fixture["replay_evaluation"], replay_inputs=fixture["replay_inputs"], persistence_evaluation=fixture["persistence_evaluation"], persistence_inputs=fixture["persistence_inputs"]))

    def test_binding_verifier_rejects_tampering(self) -> None:
        fixture = _fixture(); binding = _evaluate(fixture); binding["facts"]["external_durability_attested"] = True
        with patch.object(subject, "verify_provider_identity_assertion_replay_receipt_evaluation_v1", return_value=True), patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1", return_value=True):
            self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(binding, replay_evaluation=fixture["replay_evaluation"], replay_inputs=fixture["replay_inputs"], persistence_evaluation=fixture["persistence_evaluation"], persistence_inputs=fixture["persistence_inputs"]))

    def test_binding_verifier_rejects_bool_int_alias(self) -> None:
        fixture = _fixture(); binding = _evaluate(fixture); binding["authority"]["live_allowed"] = 0
        with patch.object(subject, "verify_provider_identity_assertion_replay_receipt_evaluation_v1", return_value=True), patch.object(subject, "verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1", return_value=True):
            self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_binding_v1(binding, replay_evaluation=fixture["replay_evaluation"], replay_inputs=fixture["replay_inputs"], persistence_evaluation=fixture["persistence_evaluation"], persistence_inputs=fixture["persistence_inputs"]))

    def test_replay_input_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["replay_inputs"].pop("pinned_checkpoint")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(); fixture["replay_inputs"]["legacy"] = True
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_input_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"].pop("reopen_receipt")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(); fixture["persistence_inputs"]["path"] = "forbidden"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_evaluations_require_strict_receipt_hashes(self) -> None:
        for target in ("replay_evaluation", "persistence_evaluation"):
            with self.subTest(target=target):
                fixture = _fixture(); fixture[target]["receipt_hash"] = "bad"
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_replay_verifier_failure_is_unknown(self) -> None:
        self.assertEqual(_evaluate(_fixture(), replay_ok=False)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_verifier_failure_is_unknown(self) -> None:
        self.assertEqual(_evaluate(_fixture(), persistence_ok=False)["status"], subject.UNKNOWN_STATUS)

    def test_replay_registration_lineage_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["replay_registration"]["id"] = "other"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_replay_registration_receipt_lineage_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["replay_registration_receipt"]["receipt_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_replay_evaluation_registration_hash_is_bound(self) -> None:
        fixture = _fixture(); fixture["replay_evaluation"]["evidence"]["registration_receipt_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_registration_source_lineage_is_bound(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["persistence_registration_receipt"]["source_replay_registration"]["replay_registration_receipt_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_source_replay_evaluation_hash_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["source_replay_verifier_receipt_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_registry_id_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["replay_registry_id"] = "other-registry"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_registry_namespace_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["replay_registry_namespace"] = "other.namespace"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_tree_size_binding_is_type_sensitive(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["tree_size"] = True
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_root_hash_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["root_hash"] = _hash("other-root")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_hash_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_inputs"]["checkpoint_asset"]["checkpoint_hash"] = _hash("other-checkpoint")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_evaluation_asset_hash_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_evaluation"]["evidence"]["asset_hash"] = _hash("other-asset")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_evaluation_source_hash_is_exact(self) -> None:
        fixture = _fixture(); fixture["persistence_evaluation"]["evidence"]["source_replay_verifier_receipt_hash"] = _hash("other")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_evaluation_checkpoint_fields_are_exact(self) -> None:
        for field, value in (("tree_size", 8), ("root_hash", _hash("other-root")), ("checkpoint_hash", _hash("other-checkpoint"))):
            with self.subTest(field=field):
                fixture = _fixture(); fixture["persistence_evaluation"]["evidence"][field] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_previous_pin_content_and_authority_remain_unproven(self) -> None:
        result = _evaluate(_fixture())
        self.assertFalse(result["facts"]["previous_pinned_asset_content_verified"])
        self.assertFalse(result["authority"]["pinned_checkpoint_authoritative"])
        self.assertFalse(result["authority"]["replay_registry_checked"])

    def test_unknown_never_exposes_authority_or_input_bundles(self) -> None:
        fixture = _fixture(); fixture["replay_inputs"] = None
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["facts"].values()))
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn("public-key", serialized)
        self.assertNotIn("write_receipt", serialized)
        self.assertNotIn("reopen_receipt", serialized)


if __name__ == "__main__":
    unittest.main()
