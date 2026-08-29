from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1 as subject
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1 as coverage_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1 as signed_claim_contract


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _fixture() -> dict[str, object]:
    source_registration_hash = _hash("source-registration")
    source_receipt_hash = _hash("source-evaluation-last")
    checkpoint_hash = _hash("checkpoint-last")
    signed_claim = {
        "status": signed_claim_contract.VERIFIED_STATUS,
        "receipt_hash": source_receipt_hash,
        "evidence": {
            "registration_receipt_hash": source_registration_hash,
            "replay_registry_id": "synthetic-registry-v1",
            "checkpoint_tree_size": 3,
            "checkpoint_hash": checkpoint_hash,
            "assertion_receipt_hash": _hash("assertion-a"),
            "assertion_leaf_index": 0,
            "scan_completed_at_ms_claim": 1_220,
            "reference_time_ms_claim": 1_230,
            "occurrence_provider_id": "synthetic-occurrence-provider-v1",
            "time_authority_id": "synthetic-time-authority-v1",
        },
        "facts": {
            "complete_scan_claim_verified": True,
            "exactly_one_occurrence_claim_verified": True,
            "time_window_claim_verified": True,
            "assertion_uniqueness_verified": False,
            "freshness_verified": False,
            "replay_absence_verified": False,
            "complete_history_verified": False,
        },
        "authority": {"paper_allowed": False, "live_allowed": False},
    }
    coverage = {
        "status": coverage_contract.VERIFIED_STATUS,
        "receipt_hash": _hash("coverage-evaluation"),
        "evidence": {
            "source_evidence_registration_receipt_hash": source_registration_hash,
            "coverage_registration_receipt_hash": _hash("coverage-registration"),
            "replay_registry_id": "synthetic-registry-v1",
            "assertion_receipt_hash": _hash("assertion-a"),
            "assertion_leaf_index": 0,
            "evaluation_count": 3,
            "start_tree_size": 1,
            "end_tree_size": 3,
            "maximum_observed_reference_time_gap_ms": 100,
            "first_source_evaluation_receipt_hash": _hash("source-evaluation-first"),
            "last_source_evaluation_receipt_hash": source_receipt_hash,
            "first_checkpoint_hash": _hash("checkpoint-first"),
            "last_checkpoint_hash": checkpoint_hash,
            "occurrence_provider_id": "synthetic-occurrence-provider-v1",
            "time_authority_id": "synthetic-time-authority-v1",
        },
        "facts": {
            "signed_single_occurrence_claim_prefix_verified": True,
            "bounded_prefix_only": True,
            "assertion_uniqueness_verified": False,
            "freshness_verified": False,
            "replay_absence_verified": False,
            "complete_history_verified": False,
        },
        "authority": {"paper_allowed": False, "live_allowed": False},
    }
    return {"signed_claim": signed_claim, "signed_inputs": {}, "coverage": coverage, "coverage_context": {}}


def _build(fixture: dict[str, object], *, signed_ok: bool = True, coverage_ok: bool = True) -> dict[str, object]:
    with patch.object(subject.signed_claim_contract, "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1", return_value=signed_ok), patch.object(subject.coverage_contract, "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1", return_value=coverage_ok):
        return subject.build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
            fixture["signed_claim"], fixture["signed_inputs"], fixture["coverage"], fixture["coverage_context"],
            expected_signed_claim_evaluation_hash=fixture["signed_claim"]["receipt_hash"],
            expected_longitudinal_coverage_evaluation_hash=fixture["coverage"]["receipt_hash"],
        )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityUniquenessFreshnessPresentationEnvelopeV1Tests(unittest.TestCase):
    def test_verified_sources_build_four_axis_envelope(self) -> None:
        result = _build(_fixture())
        self.assertEqual(result["display_state"], subject.POSITIVE_DISPLAY_STATE)
        self.assertEqual([axis["axis"] for axis in result["axes"]], list(subject.AXIS_ORDER))
        self.assertEqual(result["axes"][2]["state"], "BOUNDED PREFIX")

    def test_summary_exposes_bounded_claims_only(self) -> None:
        result = _build(_fixture())
        self.assertEqual(result["summary"]["coverage_evaluation_count"], 3)
        self.assertEqual(result["summary"]["coverage_start_tree_size"], 1)
        self.assertEqual(result["summary"]["coverage_end_tree_size"], 3)
        self.assertEqual(result["summary"]["maximum_reference_time_gap_ms"], 100)

    def test_truth_and_permissions_remain_negative(self) -> None:
        result = _build(_fixture())
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertFalse(result["facts"]["freshness_verified"])
        self.assertFalse(result["facts"]["replay_absence_verified"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_expected_signed_claim_hash_is_required(self) -> None:
        fixture = _fixture()
        result = subject.build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
            fixture["signed_claim"], fixture["signed_inputs"], fixture["coverage"], fixture["coverage_context"],
            expected_signed_claim_evaluation_hash=None,
            expected_longitudinal_coverage_evaluation_hash=fixture["coverage"]["receipt_hash"],
        )
        self.assertEqual(result["blockers"], ["EXPECTED_SIGNED_CLAIM_EVALUATION_HASH_INVALID"])

    def test_expected_coverage_hash_is_required(self) -> None:
        fixture = _fixture()
        result = subject.build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
            fixture["signed_claim"], fixture["signed_inputs"], fixture["coverage"], fixture["coverage_context"],
            expected_signed_claim_evaluation_hash=fixture["signed_claim"]["receipt_hash"],
            expected_longitudinal_coverage_evaluation_hash=None,
        )
        self.assertEqual(result["blockers"], ["EXPECTED_LONGITUDINAL_COVERAGE_EVALUATION_HASH_INVALID"])

    def test_signed_claim_verifier_is_required(self) -> None:
        self.assertEqual(_build(_fixture(), signed_ok=False)["blockers"], ["SIGNED_CLAIM_EVALUATION_UNVERIFIED"])

    def test_coverage_verifier_is_required(self) -> None:
        self.assertEqual(_build(_fixture(), coverage_ok=False)["blockers"], ["LONGITUDINAL_COVERAGE_EVALUATION_UNVERIFIED"])

    def test_source_statuses_are_required(self) -> None:
        fixture = _fixture()
        fixture["signed_claim"]["status"] = signed_claim_contract.UNKNOWN_STATUS
        self.assertEqual(_build(fixture)["display_state"], subject.UNKNOWN_DISPLAY_STATE)
        fixture = _fixture()
        fixture["coverage"]["status"] = coverage_contract.UNKNOWN_STATUS
        self.assertEqual(_build(fixture)["display_state"], subject.UNKNOWN_DISPLAY_STATE)

    def test_source_registration_binding_is_exact(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["source_evidence_registration_receipt_hash"] = _hash("other-registration")
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_REGISTRATION_BINDING_MISMATCH"])

    def test_latest_signed_claim_binding_is_exact(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["last_source_evaluation_receipt_hash"] = _hash("other-source")
        self.assertEqual(_build(fixture)["blockers"], ["LATEST_SIGNED_CLAIM_BINDING_MISMATCH"])

    def test_latest_checkpoint_binding_is_exact(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["last_checkpoint_hash"] = _hash("other-checkpoint")
        self.assertEqual(_build(fixture)["blockers"], ["LATEST_CHECKPOINT_BINDING_MISMATCH"])

    def test_registry_and_assertion_bindings_are_exact(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["replay_registry_id"] = "other-registry-v1"
        self.assertEqual(_build(fixture)["blockers"], ["REPLAY_REGISTRY_BINDING_MISMATCH"])
        fixture = _fixture()
        fixture["coverage"]["evidence"]["assertion_receipt_hash"] = _hash("assertion-b")
        self.assertEqual(_build(fixture)["blockers"], ["ASSERTION_HASH_BINDING_MISMATCH"])

    def test_assertion_leaf_binding_rejects_bool_alias(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["assertion_leaf_index"] = False
        self.assertEqual(_build(fixture)["display_state"], subject.UNKNOWN_DISPLAY_STATE)

    def test_witness_bindings_are_exact(self) -> None:
        fixture = _fixture()
        fixture["coverage"]["evidence"]["occurrence_provider_id"] = "other-provider-v1"
        self.assertEqual(_build(fixture)["blockers"], ["OCCURRENCE_PROVIDER_BINDING_MISMATCH"])
        fixture = _fixture()
        fixture["coverage"]["evidence"]["time_authority_id"] = "other-time-v1"
        self.assertEqual(_build(fixture)["blockers"], ["TIME_AUTHORITY_BINDING_MISMATCH"])

    def test_source_truth_promotion_is_rejected(self) -> None:
        fixture = _fixture()
        fixture["signed_claim"]["facts"]["assertion_uniqueness_verified"] = True
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_TRUTH_PROMOTION_REJECTED"])
        fixture = _fixture()
        fixture["coverage"]["facts"]["freshness_verified"] = True
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_TRUTH_PROMOTION_REJECTED"])

    def test_source_authority_promotion_is_rejected(self) -> None:
        fixture = _fixture()
        fixture["signed_claim"]["authority"]["paper_allowed"] = True
        self.assertEqual(_build(fixture)["blockers"], ["SOURCE_AUTHORITY_PROMOTION_REJECTED"])

    def test_envelope_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        result = _build(fixture)
        with patch.object(subject.signed_claim_contract, "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1", return_value=True), patch.object(subject.coverage_contract, "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1", return_value=True):
            self.assertTrue(subject.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
                result, fixture["signed_claim"], fixture["signed_inputs"], fixture["coverage"], fixture["coverage_context"],
                expected_signed_claim_evaluation_hash=fixture["signed_claim"]["receipt_hash"],
                expected_longitudinal_coverage_evaluation_hash=fixture["coverage"]["receipt_hash"],
            ))

    def test_envelope_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        result = _build(fixture)
        result["authority"]["paper_authorized"] = True
        with patch.object(subject.signed_claim_contract, "verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1", return_value=True), patch.object(subject.coverage_contract, "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1", return_value=True):
            self.assertFalse(subject.verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
                result, fixture["signed_claim"], fixture["signed_inputs"], fixture["coverage"], fixture["coverage_context"],
                expected_signed_claim_evaluation_hash=fixture["signed_claim"]["receipt_hash"],
                expected_longitudinal_coverage_evaluation_hash=fixture["coverage"]["receipt_hash"],
            ))

    def test_envelope_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_build(fixture), _build(fixture))

    def test_unknown_envelope_never_exposes_source_inputs(self) -> None:
        result = subject.build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
            None, None, None, None,
            expected_signed_claim_evaluation_hash=None,
            expected_longitudinal_coverage_evaluation_hash=None,
        )
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn('"signed_claim_evaluation_inputs":', serialized)
        self.assertNotIn('"longitudinal_coverage_evaluation_context":', serialized)
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
