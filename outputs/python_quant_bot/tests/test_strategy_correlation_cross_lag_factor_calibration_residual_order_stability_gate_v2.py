from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    EVALUATED_LAGS,
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
    verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate as k0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = k0_fixtures.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateTests(
            methodName="test_all_zero_residual_order_is_defined_stable"
        )
        case.setUp()
        self.case = case
        self.beta_stability_gate = case.beta_stability_gate
        self.replay = case.replay
        self.registration = case.registration
        self.observations = case.observations
        self.residual_order_gate_v1 = case._evaluate()

    def _evaluate(self, residual_order_gate_v1=..., **overrides):
        source = (
            self.residual_order_gate_v1
            if residual_order_gate_v1 is ...
            else residual_order_gate_v1
        )
        beta_gate = overrides.pop("beta_stability_gate", self.beta_stability_gate)
        replay = overrides.pop("replay", self.replay)
        registration = overrides.pop("registration", self.registration)
        observations = overrides.pop("observations", self.observations)
        expected_source_hash = overrides.pop(
            "expected_residual_order_gate_v1_hash",
            "" if source is None else source.get("gate_hash"),
        )
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            source,
            beta_gate,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v1_hash=expected_source_hash,
            expected_beta_stability_gate_hash=overrides.pop(
                "expected_beta_stability_gate_hash", beta_gate["gate_hash"]
            ),
            expected_replay_hash=overrides.pop(
                "expected_replay_hash", replay["receipt_hash"]
            ),
            expected_registration_hash=overrides.pop(
                "expected_registration_hash", registration["registration_hash"]
            ),
            expected_calibration_observations_hash=overrides.pop(
                "expected_calibration_observations_hash",
                observations["calibration_observations_hash"],
            ),
        )

    def _verify(self, gate, **context):
        source = context.get("residual_order_gate_v1", self.residual_order_gate_v1)
        beta_gate = context.get("beta_stability_gate", self.beta_stability_gate)
        replay = context.get("replay", self.replay)
        registration = context.get("registration", self.registration)
        observations = context.get("observations", self.observations)
        return verify_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            gate,
            source,
            beta_gate,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v1_hash=(
                "" if source is None else source["gate_hash"]
            ),
            expected_beta_stability_gate_hash=beta_gate["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _path(self, pair_values):
        observations, replay, beta_gate, source = self.case._path_gate(pair_values)
        gate = self._evaluate(
            source,
            beta_stability_gate=beta_gate,
            replay=replay,
            observations=observations,
        )
        return observations, replay, beta_gate, source, gate

    def test_lag_one_cancellation_lag_two_periodicity_is_blocked(self) -> None:
        _, _, _, source, gate = self._path([1, -1, 1, -1, 1])
        self.assertEqual(source["gate_decision"], "RESIDUAL_ORDER_STABLE_CANDIDATE")
        self.assertEqual(
            source["maximum_observed_absolute_lag_one_residual_energy_coupling"],
            "0.1111111111111111111111111111",
        )
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(
            gate["maximum_observed_absolute_multi_lag_residual_energy_coupling"],
            "1",
        )

    def test_zero_residuals_are_defined_stable(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["gate_decision"], "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE"
        )
        self.assertEqual(gate["zero_lag_energy_identity_fold_lag_count"], 16)
        self.assertTrue(self._verify(gate))

    def test_threshold_boundary_is_inclusive(self) -> None:
        _, _, _, source, gate = self._path([1, 1, 0, 0, 1])
        self.assertEqual(source["gate_decision"], "RESIDUAL_ORDER_STABLE_CANDIDATE")
        self.assertEqual(
            gate["maximum_observed_absolute_multi_lag_residual_energy_coupling"],
            "0.8",
        )
        self.assertEqual(
            gate["gate_decision"], "RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE"
        )

    def test_source_v1_block_is_monotone(self) -> None:
        _, replay, beta_gate, source = self.case._path_gate([1, 1, 1, 1, 1])
        gate = self._evaluate(
            source, beta_stability_gate=beta_gate, replay=replay,
            observations=self.case._ordered_path([1, 1, 1, 1, 1])
        )
        self.assertEqual(source["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_RESIDUAL_ORDER_GATE_V1_BLOCKED")

    def test_missing_source_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["RESIDUAL_ORDER_GATE_V1_MISSING"])

    def test_unsupported_source_is_distinct(self) -> None:
        source = {"schema_version": "v0", "static_fingerprint": "v0"}
        gate = self._evaluate(
            source, expected_residual_order_gate_v1_hash="a" * 64
        )
        self.assertEqual(gate["source_state"], "UNSUPPORTED")

    def test_expected_hashes_are_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_residual_order_gate_v1_hash="0" * 64)[
                "source_state"
            ],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_replay_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_coherently_resealed_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.residual_order_gate_v1)
        source["gate_reason"] = "RESEALED"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(source)["source_state"], "INVALID")

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.case.fixture._observations(count=39)
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
            {"rows", "returns", "factor_return", "beta_by_identity", "folds"}.isdisjoint(keys)
        )

    def test_candidate_is_not_independence_proof_or_authority(self) -> None:
        for gate in (self._evaluate(), self._evaluate(None)):
            self.assertFalse(gate["facts"]["residual_order_independence_proven"])
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_source_is_invalid(self) -> None:
        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._evaluate(DictSubclass(self.residual_order_gate_v1))["source_state"],
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

    def test_schema_fingerprint_and_lags_are_exact(self) -> None:
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-residual-order-stability-gate-candidate-v2",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260901-cross-lag-factor-calibration-residual-order-stability-gate-2",
        )
        self.assertEqual(EVALUATED_LAGS, (1, 2))
        gate = self._evaluate()
        self.assertEqual(gate["evaluated_lags"], [1, 2])
        self.assertEqual(
            gate["maximum_allowed_absolute_multi_lag_residual_energy_coupling"],
            "0.8",
        )


if __name__ == "__main__":
    unittest.main()
