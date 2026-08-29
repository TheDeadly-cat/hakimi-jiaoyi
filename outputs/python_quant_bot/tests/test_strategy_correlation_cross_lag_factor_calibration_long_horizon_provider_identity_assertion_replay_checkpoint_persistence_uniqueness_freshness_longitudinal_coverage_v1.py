from __future__ import annotations

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1 as subject
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1 as source_contract


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _registration() -> dict[str, object]:
    return {
        "schema": subject.REGISTRATION_SCHEMA,
        "window_id": "synthetic-window-v1",
        "adapter_id": "synthetic-longitudinal-coverage-adapter-v1",
        "adapter_implementation_hash": _hash("coverage-adapter"),
        "source_evaluation_schema": source_contract.EVALUATION_SCHEMA,
        "source_evaluation_static_fingerprint": source_contract.STATIC_FINGERPRINT,
        "source_evidence_registration_receipt_hash": _hash("source-registration"),
        "replay_registry_id": "synthetic-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.identity-replay",
        "assertion_receipt_hash": _hash("assertion-a"),
        "assertion_leaf_index": 0,
        "start_tree_size": 1,
        "end_tree_size": 3,
        "checkpoint_step": 1,
        "expected_evaluation_count": 3,
        "max_reference_time_gap_ms": 100,
        "checkpoint_sequence_policy": subject.CHECKPOINT_SEQUENCE_POLICY,
        "segment_handoff_policy": subject.SEGMENT_HANDOFF_POLICY,
        "assertion_stability_policy": subject.ASSERTION_STABILITY_POLICY,
        "witness_stability_policy": subject.WITNESS_STABILITY_POLICY,
        "reference_time_policy": subject.REFERENCE_TIME_POLICY,
    }


def _item(
    tree_size: int,
    *,
    previous_segment: object,
    reference_time_ms: int,
    scan_completed_at_ms: int,
) -> dict[str, object]:
    binding_hash = _hash(f"binding-{tree_size}")
    previous_binding_hash = (
        previous_segment["binding"]["receipt_hash"]
        if isinstance(previous_segment, dict)
        else None
    )
    current_segment = {
        "binding": {"receipt_hash": binding_hash},
        "synthetic_tree_size": tree_size,
    }
    lineage_evaluation = {
        "receipt_hash": _hash(f"lineage-{tree_size}"),
        "evidence": {
            "current_binding_receipt_hash": binding_hash,
            "previous_binding_receipt_hash": previous_binding_hash,
        },
    }
    evidence = {
        "registration_receipt_hash": _hash("source-registration"),
        "lineage_receipt_hash": lineage_evaluation["receipt_hash"],
        "occurrence_receipt_hash": _hash(f"occurrence-{tree_size}"),
        "time_receipt_hash": _hash(f"time-{tree_size}"),
        "replay_registry_id": "synthetic-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.identity-replay",
        "checkpoint_tree_size": tree_size,
        "checkpoint_root_hash": _hash(f"root-{tree_size}"),
        "checkpoint_hash": _hash(f"checkpoint-{tree_size}"),
        "assertion_receipt_hash": _hash("assertion-a"),
        "assertion_leaf_index": 0,
        "occurrence_count_claim": 1,
        "occurrence_leaf_indices_claim": [0],
        "scan_completed_at_ms_claim": scan_completed_at_ms,
        "reference_time_ms_claim": reference_time_ms,
        "occurrence_provider_id": "synthetic-occurrence-provider-v1",
        "time_authority_id": "synthetic-time-authority-v1",
    }
    evaluation = {
        "status": source_contract.VERIFIED_STATUS,
        "receipt_hash": _hash(f"source-evaluation-{tree_size}"),
        "evidence": evidence,
        "facts": {
            "complete_scan_claim_verified": True,
            "exactly_one_occurrence_claim_verified": True,
            "time_window_claim_verified": True,
            "assertion_uniqueness_verified": False,
            "freshness_verified": False,
            "replay_absence_verified": False,
            "complete_history_verified": False,
        },
        "authority": {
            "assertion_uniqueness_verified": False,
            "freshness_verified": False,
            "paper_allowed": False,
            "live_allowed": False,
        },
    }
    inputs = {
        "lineage_evaluation": lineage_evaluation,
        "current_segment": current_segment,
        "previous_segment": previous_segment,
        "evidence_registration": {},
        "evidence_registration_receipt": {
            "receipt_hash": _hash("source-registration")
        },
        "occurrence_receipt": {},
        "occurrence_provider_public_key": "synthetic-occurrence-public-key",
        "time_receipt": {},
        "time_authority_public_key": "synthetic-time-public-key",
    }
    return {"evaluation": evaluation, "inputs": inputs}


def _fixture() -> dict[str, object]:
    registration = _registration()
    registration_receipt = subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
        registration
    )
    first = _item(
        1,
        previous_segment=None,
        reference_time_ms=1_000,
        scan_completed_at_ms=990,
    )
    second = _item(
        2,
        previous_segment=copy.deepcopy(first["inputs"]["current_segment"]),
        reference_time_ms=1_050,
        scan_completed_at_ms=1_040,
    )
    third = _item(
        3,
        previous_segment=copy.deepcopy(second["inputs"]["current_segment"]),
        reference_time_ms=1_100,
        scan_completed_at_ms=1_090,
    )
    return {
        "registration": registration,
        "registration_receipt": registration_receipt,
        "items": [first, second, third],
    }


def _evaluate(fixture: dict[str, object], *, source_ok: bool = True) -> dict[str, object]:
    with patch.object(
        subject.source_contract,
        "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1",
        return_value=source_ok,
    ):
        return subject.evaluate_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_v1(
            registration=fixture["registration"],
            registration_receipt=fixture["registration_receipt"],
            evaluation_items=fixture["items"],
        )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceUniquenessFreshnessLongitudinalCoverageV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_window(self) -> None:
        fixture = _fixture()
        self.assertEqual(fixture["registration_receipt"]["status"], subject.REGISTERED_STATUS)
        self.assertTrue(
            subject.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        registration = _registration()
        registration["extra"] = True
        self.assertEqual(
            subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(registration)["status"],
            subject.UNKNOWN_STATUS,
        )

    def test_registration_rejects_bool_int_alias(self) -> None:
        registration = _registration()
        registration["start_tree_size"] = True
        self.assertEqual(
            subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(registration)["reason"],
            "registration_start_tree_size_invalid",
        )

    def test_registration_requires_at_least_three_evaluations(self) -> None:
        registration = _registration()
        registration["end_tree_size"] = 2
        registration["expected_evaluation_count"] = 2
        self.assertEqual(
            subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(registration)["reason"],
            "registration_end_tree_size_invalid",
        )

    def test_registration_count_must_match_range(self) -> None:
        registration = _registration()
        registration["expected_evaluation_count"] = 4
        self.assertEqual(
            subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(registration)["reason"],
            "registration_evaluation_count_range_mismatch",
        )

    def test_registration_leaf_must_exist_at_window_start(self) -> None:
        registration = _registration()
        registration["assertion_leaf_index"] = 1
        self.assertEqual(
            subject.build_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(registration)["reason"],
            "registration_assertion_leaf_index_invalid",
        )

    def test_registration_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["status"] = "TAMPERED"
        self.assertFalse(
            subject.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_complete_bounded_prefix_verifies_without_authority(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["preregistered_window_complete"])
        self.assertTrue(result["facts"]["segment_handoffs_exact"])
        self.assertTrue(result["facts"]["bounded_prefix_only"])
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertFalse(result["facts"]["replay_absence_verified"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_evaluation_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        with patch.object(
            subject.source_contract,
            "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1",
            return_value=True,
        ):
            self.assertTrue(
                subject.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1(
                    result,
                    registration=fixture["registration"],
                    registration_receipt=fixture["registration_receipt"],
                    evaluation_items=fixture["items"],
                )
            )

    def test_evaluation_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        result["authority"]["assertion_uniqueness_verified"] = True
        with patch.object(
            subject.source_contract,
            "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1",
            return_value=True,
        ):
            self.assertFalse(
                subject.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1(
                    result,
                    registration=fixture["registration"],
                    registration_receipt=fixture["registration_receipt"],
                    evaluation_items=fixture["items"],
                )
            )

    def test_source_evaluations_are_reverified(self) -> None:
        self.assertEqual(_evaluate(_fixture(), source_ok=False)["reason"], "item_0_source_evaluation_unverified")

    def test_evaluation_item_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["items"][0]["extra"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "item_0_evaluation_item_shape_invalid")

    def test_source_input_fields_are_exact(self) -> None:
        fixture = _fixture()
        del fixture["items"][0]["inputs"]["time_receipt"]
        self.assertEqual(_evaluate(fixture)["reason"], "item_0_source_evaluation_inputs_fields_invalid")

    def test_source_status_must_be_verified(self) -> None:
        fixture = _fixture()
        fixture["items"][0]["evaluation"]["status"] = source_contract.UNKNOWN_STATUS
        self.assertEqual(_evaluate(fixture)["reason"], "item_0_source_evaluation_unverified")

    def test_batch_count_must_match_registration(self) -> None:
        fixture = _fixture()
        fixture["items"].pop()
        self.assertEqual(_evaluate(fixture)["reason"], "evaluation_batch_count_mismatch")

    def test_tree_size_sequence_is_exact(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["checkpoint_tree_size"] = 3
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_checkpoint_tree_size_mismatch")

    def test_tree_size_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["checkpoint_tree_size"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_checkpoint_tree_size_mismatch")

    def test_registry_identity_is_stable(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["replay_registry_id"] = "other-registry-v1"
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_replay_registry_id_mismatch")

    def test_assertion_digest_is_stable(self) -> None:
        fixture = _fixture()
        fixture["items"][2]["evaluation"]["evidence"]["assertion_receipt_hash"] = _hash("assertion-b")
        self.assertEqual(_evaluate(fixture)["reason"], "item_2_source_assertion_receipt_hash_mismatch")

    def test_assertion_leaf_index_is_stable_and_typed(self) -> None:
        fixture = _fixture()
        fixture["items"][2]["evaluation"]["evidence"]["assertion_leaf_index"] = False
        self.assertEqual(_evaluate(fixture)["reason"], "item_2_source_assertion_leaf_index_mismatch")

    def test_source_registration_receipt_is_stable(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["inputs"]["evidence_registration_receipt"]["receipt_hash"] = _hash("other-registration")
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_registration_receipt_hash_mismatch")

    def test_occurrence_provider_identity_is_stable(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["occurrence_provider_id"] = "other-occurrence-provider-v1"
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_provider_identity_drift")

    def test_time_authority_identity_is_stable(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["time_authority_id"] = "other-time-authority-v1"
        self.assertEqual(_evaluate(fixture)["reason"], "time_authority_identity_drift")

    def test_single_occurrence_claim_is_required(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["occurrence_count_claim"] = 2
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_occurrence_count_claim_mismatch")

    def test_source_truth_fields_must_remain_false(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["facts"]["assertion_uniqueness_verified"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_assertion_uniqueness_verified_must_remain_false")

    def test_source_authority_must_remain_negative(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["authority"]["paper_allowed"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_authority_not_negative")

    def test_segment_handoff_must_be_exact(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["inputs"]["previous_segment"]["synthetic_tree_size"] = 99
        self.assertEqual(_evaluate(fixture)["reason"], "segment_handoff_mismatch")

    def test_lineage_previous_binding_must_match_prior_current(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["inputs"]["lineage_evaluation"]["evidence"]["previous_binding_receipt_hash"] = _hash("wrong-binding")
        self.assertEqual(_evaluate(fixture)["reason"], "lineage_previous_binding_mismatch")

    def test_scan_time_must_increase(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["scan_completed_at_ms_claim"] = 990
        self.assertEqual(_evaluate(fixture)["reason"], "scan_time_not_strictly_increasing")

    def test_reference_time_must_increase(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["reference_time_ms_claim"] = 1_000
        fixture["items"][1]["evaluation"]["evidence"]["scan_completed_at_ms_claim"] = 999
        self.assertEqual(_evaluate(fixture)["reason"], "reference_time_not_strictly_increasing")

    def test_reference_time_gap_is_preregistered(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["reference_time_ms_claim"] = 1_101
        fixture["items"][1]["evaluation"]["evidence"]["scan_completed_at_ms_claim"] = 1_090
        self.assertEqual(_evaluate(fixture)["reason"], "reference_time_gap_exceeds_registration")

    def test_reference_time_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["reference_time_ms_claim"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "item_1_source_reference_time_ms_claim_invalid")

    def test_checkpoint_hash_cannot_be_reused(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["checkpoint_hash"] = fixture["items"][0]["evaluation"]["evidence"]["checkpoint_hash"]
        self.assertEqual(_evaluate(fixture)["reason"], "checkpoint_hash_reused")

    def test_occurrence_receipt_hash_cannot_be_reused(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["evidence"]["occurrence_receipt_hash"] = fixture["items"][0]["evaluation"]["evidence"]["occurrence_receipt_hash"]
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_receipt_hash_reused")

    def test_source_evaluation_receipt_hash_cannot_be_reused(self) -> None:
        fixture = _fixture()
        fixture["items"][1]["evaluation"]["receipt_hash"] = fixture["items"][0]["evaluation"]["receipt_hash"]
        self.assertEqual(_evaluate(fixture)["reason"], "source_evaluation_receipt_hash_reused")

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_unknown_never_exposes_batch_or_authority(self) -> None:
        result = subject.evaluate_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_v1(
            registration=None,
            registration_receipt=None,
            evaluation_items=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn('"evaluation_items":', serialized)
        self.assertNotIn('"current_segment":', serialized)


if __name__ == "__main__":
    unittest.main()
