from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate import (
    FOLD_COUNT,
    GATE_SCHEMA,
    MAX_ABSOLUTE_LAG_ONE_RESIDUAL_ENERGY_COUPLING,
    MIN_ROWS_PER_FOLD,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_stability_gate as h0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateTests(
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

    def _ordered_path(self, pair_values):
        if len(pair_values) != 5:
            raise ValueError("five residual pair values required")
        observations = deepcopy(self.case.fixture._observations())
        rows = observations["rows"]
        self.assertEqual(len(rows), 40)
        for fold_index in range(4):
            fold = rows[fold_index * 10 : (fold_index + 1) * 10]
            for pair_index, residual in enumerate(pair_values):
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

    def _source(self, observations):
        replay = self.case._replay(self.registration, observations)
        beta_gate = self.case._evaluate(
            replay, registration=self.registration, observations=observations
        )
        return replay, beta_gate

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
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
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
        return verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
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

    def _path_gate(self, pair_values):
        observations = self._ordered_path(pair_values)
        replay, beta_gate = self._source(observations)
        gate = self._evaluate(
            beta_gate, replay=replay, observations=observations
        )
        return observations, replay, beta_gate, gate

    def test_energy_stable_persistent_residual_gap_is_blocked(self) -> None:
        observations, replay, beta_gate, gate = self._path_gate([1, 1, 1, 1, 1])
        energy_gate = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            beta_gate,
            replay,
            self.registration,
            observations,
            expected_beta_stability_gate_hash=beta_gate["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=self.registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )
        self.assertEqual(beta_gate["gate_decision"], "STABLE_CANDIDATE")
        self.assertEqual(
            energy_gate["gate_decision"], "RESIDUAL_ENERGY_STABLE_CANDIDATE"
        )
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(
            gate["maximum_observed_absolute_lag_one_residual_energy_coupling"],
            "1",
        )

    def test_low_coupling_path_is_stable_candidate(self) -> None:
        observations, replay, beta_gate, gate = self._path_gate([1, -1, 1, -1, 1])
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ORDER_STABLE_CANDIDATE")
        self.assertLess(
            Decimal(
                gate[
                    "maximum_observed_absolute_lag_one_residual_energy_coupling"
                ]
            ),
            MAX_ABSOLUTE_LAG_ONE_RESIDUAL_ENERGY_COUPLING,
        )
        self.assertTrue(
            self._verify(
                gate, beta_gate, replay=replay, observations=observations
            )
        )

    def test_threshold_boundary_is_inclusive(self) -> None:
        _, _, _, gate = self._path_gate([1, 1, 0, 0, 1])
        self.assertEqual(
            gate["maximum_observed_absolute_lag_one_residual_energy_coupling"],
            "0.8",
        )
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ORDER_STABLE_CANDIDATE")

    def test_all_zero_residual_order_is_defined_stable(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["gate_decision"], "RESIDUAL_ORDER_STABLE_CANDIDATE")
        self.assertEqual(gate["zero_lag_energy_identity_fold_count"], 8)
        self.assertEqual(
            gate["maximum_observed_absolute_lag_one_residual_energy_coupling"],
            "0",
        )

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
        self.assertEqual(
            self._evaluate(expected_registration_hash="0" * 64)["source_state"],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_observations_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_coherently_resealed_h0_tamper_is_invalid(self) -> None:
        source = deepcopy(self.beta_stability_gate)
        source["maximum_observed_normalized_beta_drift"] = "0.1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(source)["source_state"], "INVALID")

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )

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
                "returns",
                "factor_return",
                "folds",
            }.isdisjoint(keys)
        )

    def test_candidate_is_not_independence_proof_or_authority(self) -> None:
        for gate in (self._evaluate(), self._evaluate(None)):
            self.assertFalse(gate["facts"]["residual_order_independence_proven"])
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_source_is_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._evaluate(DictSubclass(self.beta_stability_gate))["source_state"],
            "INVALID",
        )

    def test_resealed_gate_tamper_is_rejected(self) -> None:
        gate = self._evaluate()
        tampered = deepcopy(gate)
        tampered["gate_decision"] = "READY"
        tampered = seal_strict_canonical_document(tampered, "gate_hash")
        self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._evaluate()
            second = self._evaluate()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_fingerprint_and_fold_contract_are_exact(self) -> None:
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-residual-order-stability-gate-candidate-v1",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260830-cross-lag-factor-calibration-residual-order-stability-gate-1",
        )
        gate = self._evaluate()
        self.assertEqual(FOLD_COUNT, 4)
        self.assertEqual(MIN_ROWS_PER_FOLD, 5)
        self.assertEqual(
            gate["maximum_allowed_absolute_lag_one_residual_energy_coupling"],
            "0.8",
        )


if __name__ == "__main__":
    unittest.main()
