from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_replay import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_stability_gate import (
    FOLD_COUNT,
    GATE_SCHEMA,
    MAX_NORMALIZED_BETA_DRIFT,
    MIN_ROWS_PER_FOLD,
    NORMALIZATION_FLOOR,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate,
    verify_strategy_correlation_cross_lag_factor_calibration_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_replay as g0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationStabilityGateTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        fixture = g0_fixtures.StrategyCorrelationCrossLagFactorCalibrationReplayTests(
            methodName="test_exact_ols_match_is_observed"
        )
        self.fixture = fixture
        self.registration = fixture._registration()
        self.observations = fixture._observations()
        self.replay = self._replay(self.registration, self.observations)

    @staticmethod
    def _replay(registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_replay(
            registration,
            observations,
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _piecewise(self, a_betas, b_betas=(2.0, 2.0, 2.0, 2.0)):
        observations = deepcopy(self.fixture._observations())
        pattern = (-2.0, -1.0, 1.0, 2.0)
        fold_size = len(observations["rows"]) // 4
        for index, row in enumerate(observations["rows"]):
            factor = pattern[index % len(pattern)]
            fold_index = min(index // fold_size, 3)
            row["factor_return"] = factor
            row["returns"]["A"] = a_betas[fold_index] * factor
            row["returns"]["B"] = b_betas[fold_index] * factor
        return seal_strict_canonical_document(
            observations, "calibration_observations_hash"
        )

    def _evaluate(
        self,
        replay=...,
        *,
        registration=None,
        observations=None,
        expected_replay_hash=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
    ):
        replay = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_replay_hash is None:
            expected_replay_hash = "" if replay is None else replay["receipt_hash"]
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        return evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate(
            replay,
            registration,
            observations,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _verify(self, gate, replay=..., **overrides):
        replay = self.replay if replay is ... else replay
        registration = overrides.pop("registration", self.registration)
        observations = overrides.pop("observations", self.observations)
        if "expected_replay_hash" in overrides:
            expected_replay_hash = overrides.pop("expected_replay_hash")
        else:
            expected_replay_hash = "" if replay is None else replay["receipt_hash"]
        expected_registration_hash = overrides.pop(
            "expected_registration_hash", registration["registration_hash"]
        )
        expected_observations_hash = overrides.pop(
            "expected_observations_hash",
            observations["calibration_observations_hash"],
        )
        self.assertFalse(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_stability_gate(
            gate,
            replay,
            registration,
            observations,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def test_constant_beta_fixture_is_stable_candidate(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["source_state"], "OBSERVED")
        self.assertEqual(gate["gate_decision"], "STABLE_CANDIDATE")
        self.assertEqual(gate["unstable_identity_count"], 0)
        self.assertEqual(gate["maximum_observed_normalized_beta_drift"], "0")
        self.assertTrue(self._verify(gate))

    def test_full_window_match_with_regime_drift_is_blocked(self) -> None:
        observations = self._piecewise((0.0, 0.0, 2.0, 2.0))
        replay = self._replay(self.registration, observations)
        self.assertEqual(replay["replay_decision"], "MATCH")
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["maximum_observed_normalized_beta_drift"], "1")
        self.assertEqual(gate["unstable_identity_count"], 1)
        self.assertIn(
            "CALIBRATION_BETA_TEMPORAL_INSTABILITY_DETECTED", gate["blockers"]
        )
        self.assertTrue(self._verify(gate, replay, observations=observations))

    def test_source_calibration_block_is_monotone(self) -> None:
        registration = self.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        replay = self._replay(registration, self.observations)
        self.assertEqual(replay["replay_decision"], "BLOCK")
        gate = self._evaluate(replay, registration=registration)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_CALIBRATION_REPLAY_BLOCKED")
        self.assertFalse(gate["facts"]["source_gate_block_relaxed"])

    def test_missing_source_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["gate_decision"], "UNKNOWN")
        self.assertEqual(gate["blockers"], ["G0_CALIBRATION_REPLAY_MISSING"])
        self.assertTrue(self._verify(gate, None))

    def test_unsupported_source_has_fixed_unknown_closure(self) -> None:
        replay = {"schema_version": "candidate-v0", "static_fingerprint": "v0"}
        gate = self._evaluate(replay, expected_replay_hash="a" * 64)
        self.assertEqual(gate["source_state"], "UNSUPPORTED")

    def test_expected_replay_hash_is_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_replay_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_resealed_source_tamper_is_invalid(self) -> None:
        replay = deepcopy(self.replay)
        replay["max_abs_beta_error"] = "0.1"
        replay = seal_strict_canonical_document(replay, "receipt_hash")
        gate = self._evaluate(replay)
        self.assertEqual(gate["source_state"], "INVALID")

    def test_registration_and_observation_contexts_are_bound(self) -> None:
        registration = self.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        self.assertEqual(
            self._evaluate(registration=registration)["source_state"], "INVALID"
        )
        observations = self.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )

    def test_remainder_rows_are_partitioned_deterministically(self) -> None:
        observations = self.fixture._observations(count=21)
        replay = self._replay(self.registration, observations)
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["gate_decision"], "STABLE_CANDIDATE")
        self.assertEqual(gate["minimum_observed_fold_rows"], 5)
        self.assertEqual(gate["maximum_observed_fold_rows"], 6)

    def test_minimum_fold_size_is_contract_fixed(self) -> None:
        self.assertEqual(FOLD_COUNT, 4)
        self.assertEqual(MIN_ROWS_PER_FOLD, 5)
        self.assertEqual(NORMALIZATION_FLOOR, 0.25)
        self.assertEqual(MAX_NORMALIZED_BETA_DRIFT, 0.5)

    def test_unidentified_fold_blocks_even_when_full_window_matches(self) -> None:
        observations = self._piecewise((1.0, 1.0, 1.0, 1.0))
        for row in observations["rows"][:10]:
            row["factor_return"] = 0.0
            row["returns"]["A"] = 0.0
            row["returns"]["B"] = 0.0
        observations = seal_strict_canonical_document(
            observations, "calibration_observations_hash"
        )
        replay = self._replay(self.registration, observations)
        self.assertEqual(replay["replay_decision"], "MATCH")
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["unidentified_fold_count"], 1)
        self.assertEqual(gate["gate_reason"], "FOLD_FACTOR_IDENTIFICATION_INSUFFICIENT")

    def test_threshold_boundary_is_inclusive(self) -> None:
        observations = self._piecewise((0.5, 0.5, 1.5, 1.5))
        replay = self._replay(self.registration, observations)
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["maximum_observed_normalized_beta_drift"], "0.5")
        self.assertEqual(gate["gate_decision"], "STABLE_CANDIDATE")

    def test_above_threshold_blocks(self) -> None:
        observations = self._piecewise((0.49, 0.49, 1.51, 1.51))
        replay = self._replay(self.registration, observations)
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["maximum_observed_normalized_beta_drift"], "0.51")
        self.assertEqual(gate["gate_decision"], "BLOCK")

    def test_sign_reversal_blocks_and_is_counted(self) -> None:
        observations = self._piecewise((-1.0, -1.0, 3.0, 3.0))
        replay = self._replay(self.registration, observations)
        gate = self._evaluate(replay, observations=observations)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["sign_reversal_count"], 2)

    def test_projection_is_aggregate_only(self) -> None:
        gate = self._evaluate()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(gate)
        self.assertTrue(
            {
                "rows",
                "identity_order",
                "beta_by_identity",
                "factor_id",
                "factor_source_hash",
                "returns",
                "factor_return",
            }.isdisjoint(keys)
        )
        self.assertNotIn("COMMON-FACTOR-1", json.dumps(gate, sort_keys=True))

    def test_private_ledger_hash_changes_with_fold_path(self) -> None:
        stable = self._evaluate()
        observations = self._piecewise((0.5, 0.5, 1.5, 1.5))
        replay = self._replay(self.registration, observations)
        boundary = self._evaluate(replay, observations=observations)
        self.assertNotEqual(
            stable["private_fold_beta_ledger_hash"],
            boundary["private_fold_beta_ledger_hash"],
        )

    def test_authority_is_permanently_locked(self) -> None:
        for gate in (self._evaluate(), self._evaluate(None)):
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["beta_temporal_stability_proven"])
            self.assertFalse(authority["future_evaluation_allowed"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_inputs_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._evaluate(DictSubclass(self.replay))["source_state"], "INVALID"
        )
        observations = deepcopy(self.observations)
        observations["rows"][0]["factor_return"] = float("nan")
        self.assertEqual(
            self._evaluate(
                self.replay,
                observations=observations,
                expected_observations_hash=self.observations[
                    "calibration_observations_hash"
                ],
            )["source_state"],
            "INVALID",
        )

    def test_resealed_gate_tamper_is_rejected(self) -> None:
        gate = self._evaluate()
        for field, value in (
            ("gate_decision", "READY"),
            ("unstable_identity_count", 1),
        ):
            tampered = deepcopy(gate)
            tampered[field] = value
            tampered = seal_strict_canonical_document(tampered, "gate_hash")
            self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("pathlib.Path.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._evaluate()
            second = self._evaluate()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_and_fingerprint_are_exact(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-stability-gate-candidate-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260825-cross-lag-factor-calibration-stability-gate-1",
        )
        self.assertEqual(gate["fold_count"], 4)
        self.assertEqual(gate["minimum_rows_per_fold"], 5)
        self.assertEqual(gate["normalization_floor"], "0.25")
        self.assertEqual(gate["maximum_allowed_normalized_beta_drift"], "0.5")


if __name__ == "__main__":
    unittest.main()
