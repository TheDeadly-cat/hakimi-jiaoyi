from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate import (
    FOLD_COUNT,
    GATE_SCHEMA,
    MAX_NORMALIZED_RESIDUAL_ENERGY_DISPERSION,
    MIN_ROWS_PER_FOLD,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_stability_gate as h0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationResidualEnergyStabilityGateTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = h0_fixtures.StrategyCorrelationCrossLagFactorCalibrationStabilityGateTests(
            methodName="test_constant_beta_fixture_is_stable_candidate"
        )
        case.setUp()
        self.case = case
        self.registration = case.registration
        self.observations = case.observations
        self.replay = case.replay
        self.beta_stability_gate = case._evaluate()

    def _source(self, observations, registration=None):
        registration = self.registration if registration is None else registration
        replay = self.case._replay(registration, observations)
        beta_gate = self.case._evaluate(
            replay, registration=registration, observations=observations
        )
        return replay, beta_gate

    def _residual_energy_path(self, fold_mse):
        if len(fold_mse) != 4:
            raise ValueError("four fold MSE values required")
        patterns = {
            0: [0, 0, 0, 0, 0],
            1: [1, 1, 1, 1, 1],
            5: [5, 0, 0, 0, 0],
            81: [9, 9, 9, 9, 9],
        }
        observations = deepcopy(self.case.fixture._observations())
        rows = observations["rows"]
        self.assertEqual(len(rows), 40)
        for fold_index in range(4):
            fold = rows[fold_index * 10 : (fold_index + 1) * 10]
            residual_pairs = patterns[fold_mse[fold_index]]
            for pair_index, residual in enumerate(residual_pairs):
                left = fold[pair_index * 2]
                right = fold[pair_index * 2 + 1]
                left["factor_return"] = -1.0
                right["factor_return"] = 1.0
                left["returns"]["A"] = -1.0 + residual
                right["returns"]["A"] = 1.0 + residual
                left["returns"]["B"] = -2.0
                right["returns"]["B"] = 2.0
        return seal_strict_canonical_document(
            observations, "calibration_observations_hash"
        )

    def _evaluate(
        self,
        beta_stability_gate=...,
        *,
        replay=...,
        registration=None,
        observations=None,
        expected_beta_gate_hash=None,
        expected_replay_hash=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
    ):
        beta_stability_gate = (
            self.beta_stability_gate
            if beta_stability_gate is ...
            else beta_stability_gate
        )
        replay = self.replay if replay is ... else replay
        registration = self.registration if registration is None else registration
        observations = self.observations if observations is None else observations
        if expected_beta_gate_hash is None:
            expected_beta_gate_hash = (
                "" if beta_stability_gate is None else beta_stability_gate["gate_hash"]
            )
        if expected_replay_hash is None:
            expected_replay_hash = "" if replay is None else replay["receipt_hash"]
        if expected_registration_hash is None:
            expected_registration_hash = registration["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = observations[
                "calibration_observations_hash"
            ]
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            beta_stability_gate,
            replay,
            registration,
            observations,
            expected_beta_stability_gate_hash=expected_beta_gate_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _verify(self, gate, beta_stability_gate=..., **overrides):
        beta_stability_gate = (
            self.beta_stability_gate
            if beta_stability_gate is ...
            else beta_stability_gate
        )
        replay = overrides.pop("replay", self.replay)
        registration = overrides.pop("registration", self.registration)
        observations = overrides.pop("observations", self.observations)
        return verify_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            gate,
            beta_stability_gate,
            replay,
            registration,
            observations,
            expected_beta_stability_gate_hash=overrides.pop(
                "expected_beta_gate_hash",
                "" if beta_stability_gate is None else beta_stability_gate["gate_hash"],
            ),
            expected_replay_hash=overrides.pop(
                "expected_replay_hash", "" if replay is None else replay["receipt_hash"]
            ),
            expected_registration_hash=overrides.pop(
                "expected_registration_hash", registration["registration_hash"]
            ),
            expected_calibration_observations_hash=overrides.pop(
                "expected_observations_hash",
                observations["calibration_observations_hash"],
            ),
        )

    def _path_gate(self, fold_mse):
        observations = self._residual_energy_path(fold_mse)
        replay, beta_gate = self._source(observations)
        gate = self._evaluate(
            beta_gate, replay=replay, observations=observations
        )
        return observations, replay, beta_gate, gate

    def test_equal_nonzero_residual_energy_is_stable_candidate(self) -> None:
        observations, replay, beta_gate, gate = self._path_gate([1, 1, 1, 1])
        self.assertEqual(replay["replay_decision"], "MATCH")
        self.assertEqual(beta_gate["gate_decision"], "STABLE_CANDIDATE")
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ENERGY_STABLE_CANDIDATE")
        self.assertEqual(
            gate["maximum_observed_normalized_residual_energy_dispersion"], "0"
        )
        self.assertEqual(gate["zero_residual_identity_count"], 1)
        self.assertTrue(
            self._verify(
                gate,
                beta_gate,
                replay=replay,
                observations=observations,
            )
        )

    def test_beta_stable_residual_energy_regime_shift_is_blocked(self) -> None:
        _, replay, beta_gate, gate = self._path_gate([1, 1, 81, 81])
        self.assertEqual(replay["replay_decision"], "MATCH")
        self.assertEqual(beta_gate["gate_decision"], "STABLE_CANDIDATE")
        self.assertEqual(beta_gate["maximum_observed_normalized_beta_drift"], "0")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertGreater(
            Decimal(gate["maximum_observed_normalized_residual_energy_dispersion"]),
            MAX_NORMALIZED_RESIDUAL_ENERGY_DISPERSION,
        )
        self.assertIn(
            "CALIBRATION_RESIDUAL_ENERGY_INSTABILITY_DETECTED", gate["blockers"]
        )

    def test_all_zero_residual_energy_is_defined_stable(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ENERGY_STABLE_CANDIDATE")
        self.assertEqual(gate["zero_residual_identity_count"], 2)
        self.assertEqual(
            gate["maximum_observed_normalized_residual_energy_dispersion"], "0"
        )

    def test_threshold_boundary_is_inclusive(self) -> None:
        _, _, _, gate = self._path_gate([1, 5, 5, 5])
        self.assertEqual(
            gate["maximum_observed_normalized_residual_energy_dispersion"], "0.75"
        )
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ENERGY_STABLE_CANDIDATE")

    def test_above_threshold_blocks(self) -> None:
        _, _, _, gate = self._path_gate([0, 5, 5, 5])
        self.assertEqual(
            gate["maximum_observed_normalized_residual_energy_dispersion"], "1"
        )
        self.assertEqual(gate["gate_decision"], "BLOCK")

    def test_source_h0_block_is_monotone(self) -> None:
        observations = self.case._piecewise((0.0, 0.0, 2.0, 2.0))
        replay, beta_gate = self._source(observations)
        gate = self._evaluate(beta_gate, replay=replay, observations=observations)
        self.assertEqual(beta_gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_BETA_STABILITY_GATE_BLOCKED")
        self.assertFalse(gate["facts"]["source_gate_block_relaxed"])

    def test_missing_h0_gate_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["gate_decision"], "UNKNOWN")
        self.assertEqual(gate["blockers"], ["H0_BETA_STABILITY_GATE_MISSING"])
        self.assertTrue(self._verify(gate, None))

    def test_unsupported_h0_gate_is_distinct(self) -> None:
        source = {"schema_version": "candidate-v0", "static_fingerprint": "v0"}
        gate = self._evaluate(source, expected_beta_gate_hash="a" * 64)
        self.assertEqual(gate["source_state"], "UNSUPPORTED")

    def test_expected_source_hashes_are_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_beta_gate_hash="0" * 64)["source_state"],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_replay_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_coherently_resealed_h0_tamper_is_invalid(self) -> None:
        source = deepcopy(self.beta_stability_gate)
        source["maximum_observed_normalized_beta_drift"] = "0.1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(source)["source_state"], "INVALID")

    def test_registration_and_observation_contexts_are_bound(self) -> None:
        registration = self.case.fixture._registration(
            betas={"A": "0.5", "B": "0.5"}
        )
        self.assertEqual(
            self._evaluate(registration=registration)["source_state"], "INVALID"
        )
        observations = self.case.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )

    def test_source_hashes_are_cross_bound(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["source_beta_stability_gate_hash"],
            self.beta_stability_gate["gate_hash"],
        )
        self.assertEqual(gate["source_replay_hash"], self.replay["receipt_hash"])
        self.assertTrue(gate["facts"]["source_hashes_cross_bound"])

    def test_remainder_rows_follow_fixed_count_partition(self) -> None:
        observations = self.case.fixture._observations(count=21)
        replay, beta_gate = self._source(observations)
        gate = self._evaluate(beta_gate, replay=replay, observations=observations)
        self.assertEqual(gate["minimum_observed_fold_rows"], 5)
        self.assertEqual(gate["maximum_observed_fold_rows"], 6)

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
                "full_window_residual_mse",
                "folds",
            }.isdisjoint(keys)
        )

    def test_private_ledger_changes_with_residual_path(self) -> None:
        stable = self._evaluate()
        _, _, _, nonzero = self._path_gate([1, 1, 1, 1])
        self.assertNotEqual(
            stable["private_fold_residual_energy_ledger_hash"],
            nonzero["private_fold_residual_energy_ledger_hash"],
        )

    def test_authority_is_locked_and_non_proof(self) -> None:
        for gate in (self._evaluate(), self._evaluate(None)):
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["residual_energy_temporal_stability_proven"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_inputs_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._evaluate(DictSubclass(self.beta_stability_gate))["source_state"],
            "INVALID",
        )
        observations = deepcopy(self.observations)
        observations["rows"][0]["returns"]["A"] = float("nan")
        self.assertEqual(
            self._evaluate(
                observations=observations,
                expected_observations_hash=self.observations[
                    "calibration_observations_hash"
                ],
            )["source_state"],
            "INVALID",
        )

    def test_resealed_i0_gate_tamper_is_rejected(self) -> None:
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

    def test_schema_threshold_and_fingerprint_are_exact(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-residual-energy-stability-gate-candidate-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260828-cross-lag-factor-calibration-residual-energy-stability-gate-1",
        )
        self.assertEqual(FOLD_COUNT, 4)
        self.assertEqual(MIN_ROWS_PER_FOLD, 5)
        self.assertEqual(MAX_NORMALIZED_RESIDUAL_ENERGY_DISPERSION, Decimal("0.75"))
        self.assertEqual(
            gate["maximum_allowed_normalized_residual_energy_dispersion"],
            "0.75",
        )


if __name__ == "__main__":
    unittest.main()
