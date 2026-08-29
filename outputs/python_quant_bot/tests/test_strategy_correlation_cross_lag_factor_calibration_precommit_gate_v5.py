from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5 import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2 import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4 as k1_fixtures
from tests import test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate as k0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV5Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = k1_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV4Tests(
            methodName="test_triple_guard_is_bound_local_only"
        )
        case.setUp()
        self.case = case
        self.precommit_gate_v3 = case.precommit_gate_v3
        self.residual_order_gate_v1 = case.residual_order_gate
        self.precommit_gate_v2 = case.precommit_gate_v2
        self.residual_energy_gate = case.residual_energy_gate
        self.precommit_gate_v1 = case.precommit_gate_v1
        self.beta_stability_gate = case.beta_stability_gate
        self.declaration = case.declaration
        self.report = case.report
        self.replay = case.replay
        self.registration = case.registration
        self.observations = case.observations
        self.precommit_gate_v4 = case._evaluate()
        self.residual_order_gate_v2 = self._v2_gate(
            self.residual_order_gate_v1,
            self.beta_stability_gate,
            self.replay,
            self.registration,
            self.observations,
        )

    @staticmethod
    def _v2_gate(source, beta_gate, replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2(
            source,
            beta_gate,
            replay,
            registration,
            observations,
            expected_residual_order_gate_v1_hash=source["gate_hash"],
            expected_beta_stability_gate_hash=beta_gate["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _multi_lag_block_context(self):
        k0_case = k0_fixtures.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateTests(
            methodName="test_low_coupling_path_is_stable_candidate"
        )
        k0_case.setUp()
        observations, replay, beta_gate, residual_order_gate_v1 = k0_case._path_gate(
            [1, -1, 1, -1, 1]
        )
        registration = k0_case.registration
        residual_energy_gate = evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
            beta_gate,
            replay,
            registration,
            observations,
            expected_beta_stability_gate_hash=beta_gate["gate_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )
        report = consume_strategy_correlation_cross_lag_factor_calibration_replay(
            replay,
            residualization_registration=registration,
            calibration_observations=observations,
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
            expected_replay_hash=replay["receipt_hash"],
        )
        declaration = self.case.case.h1_case.case._declaration(report)
        precommit_gate_v1 = evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate(
            declaration,
            report,
            replay,
            registration,
            observations,
            expected_declaration_hash=declaration["declaration_hash"],
            expected_report_hash=report["verification_hash"],
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )
        precommit_gate_v2 = self.case.case.h1_case._evaluate(
            precommit_gate_v1=precommit_gate_v1,
            stability_gate=beta_gate,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_gate_v3 = self.case.case._evaluate(
            precommit_gate_v2=precommit_gate_v2,
            residual_energy_gate=residual_energy_gate,
            precommit_gate_v1=precommit_gate_v1,
            beta_stability_gate=beta_gate,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_gate_v4 = self.case._evaluate(
            precommit_gate_v3=precommit_gate_v3,
            residual_order_gate=residual_order_gate_v1,
            precommit_gate_v2=precommit_gate_v2,
            residual_energy_gate=residual_energy_gate,
            precommit_gate_v1=precommit_gate_v1,
            beta_stability_gate=beta_gate,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        residual_order_gate_v2 = self._v2_gate(
            residual_order_gate_v1, beta_gate, replay, registration, observations
        )
        return {
            "precommit_gate_v4": precommit_gate_v4,
            "residual_order_gate_v2": residual_order_gate_v2,
            "precommit_gate_v3": precommit_gate_v3,
            "residual_order_gate_v1": residual_order_gate_v1,
            "precommit_gate_v2": precommit_gate_v2,
            "residual_energy_gate": residual_energy_gate,
            "precommit_gate_v1": precommit_gate_v1,
            "beta_stability_gate": beta_gate,
            "declaration": declaration,
            "report": report,
            "replay": replay,
            "registration": registration,
            "observations": observations,
        }

    def _evaluate(self, precommit_gate_v4=..., residual_order_gate_v2=..., **overrides):
        values = {
            "precommit_gate_v4": self.precommit_gate_v4 if precommit_gate_v4 is ... else precommit_gate_v4,
            "residual_order_gate_v2": self.residual_order_gate_v2 if residual_order_gate_v2 is ... else residual_order_gate_v2,
            "precommit_gate_v3": self.precommit_gate_v3,
            "residual_order_gate_v1": self.residual_order_gate_v1,
            "precommit_gate_v2": self.precommit_gate_v2,
            "residual_energy_gate": self.residual_energy_gate,
            "precommit_gate_v1": self.precommit_gate_v1,
            "beta_stability_gate": self.beta_stability_gate,
            "declaration": self.declaration,
            "report": self.report,
            "replay": self.replay,
            "registration": self.registration,
            "observations": self.observations,
        }
        for key in tuple(values):
            if key in overrides:
                values[key] = overrides.pop(key)
        expected = {
            "expected_precommit_gate_v4_hash": "" if values["precommit_gate_v4"] is None else values["precommit_gate_v4"].get("gate_hash"),
            "expected_residual_order_gate_v2_hash": "" if values["residual_order_gate_v2"] is None else values["residual_order_gate_v2"].get("gate_hash"),
            "expected_precommit_gate_v3_hash": values["precommit_gate_v3"]["gate_hash"],
            "expected_residual_order_gate_v1_hash": values["residual_order_gate_v1"]["gate_hash"],
            "expected_precommit_gate_v2_hash": values["precommit_gate_v2"]["gate_hash"],
            "expected_residual_energy_gate_hash": values["residual_energy_gate"]["gate_hash"],
            "expected_precommit_gate_v1_hash": values["precommit_gate_v1"]["gate_hash"],
            "expected_beta_stability_gate_hash": values["beta_stability_gate"]["gate_hash"],
            "expected_declaration_hash": values["declaration"]["declaration_hash"],
            "expected_report_hash": values["report"]["verification_hash"],
            "expected_replay_hash": values["replay"]["receipt_hash"],
            "expected_registration_hash": values["registration"]["registration_hash"],
            "expected_calibration_observations_hash": values["observations"]["calibration_observations_hash"],
        }
        for key in tuple(expected):
            if key in overrides:
                expected[key] = overrides.pop(key)
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
            values["precommit_gate_v4"],
            values["residual_order_gate_v2"],
            values["precommit_gate_v3"],
            values["residual_order_gate_v1"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            **expected,
        )

    def _verify(self, gate, **context):
        values = {
            "precommit_gate_v4": self.precommit_gate_v4,
            "residual_order_gate_v2": self.residual_order_gate_v2,
            "precommit_gate_v3": self.precommit_gate_v3,
            "residual_order_gate_v1": self.residual_order_gate_v1,
            "precommit_gate_v2": self.precommit_gate_v2,
            "residual_energy_gate": self.residual_energy_gate,
            "precommit_gate_v1": self.precommit_gate_v1,
            "beta_stability_gate": self.beta_stability_gate,
            "declaration": self.declaration,
            "report": self.report,
            "replay": self.replay,
            "registration": self.registration,
            "observations": self.observations,
        }
        values.update(context)
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
            gate,
            values["precommit_gate_v4"],
            values["residual_order_gate_v2"],
            values["precommit_gate_v3"],
            values["residual_order_gate_v1"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            expected_precommit_gate_v4_hash=values["precommit_gate_v4"]["gate_hash"],
            expected_residual_order_gate_v2_hash=values["residual_order_gate_v2"]["gate_hash"],
            expected_precommit_gate_v3_hash=values["precommit_gate_v3"]["gate_hash"],
            expected_residual_order_gate_v1_hash=values["residual_order_gate_v1"]["gate_hash"],
            expected_precommit_gate_v2_hash=values["precommit_gate_v2"]["gate_hash"],
            expected_residual_energy_gate_hash=values["residual_energy_gate"]["gate_hash"],
            expected_precommit_gate_v1_hash=values["precommit_gate_v1"]["gate_hash"],
            expected_beta_stability_gate_hash=values["beta_stability_gate"]["gate_hash"],
            expected_declaration_hash=values["declaration"]["declaration_hash"],
            expected_report_hash=values["report"]["verification_hash"],
            expected_replay_hash=values["replay"]["receipt_hash"],
            expected_registration_hash=values["registration"]["registration_hash"],
            expected_calibration_observations_hash=values["observations"]["calibration_observations_hash"],
        )

    def test_multi_lag_guard_is_bound_local_only(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["gate_decision"], "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED"
        )
        self.assertTrue(self._verify(gate))

    def test_lag_two_block_overrides_positive_v4(self) -> None:
        context = self._multi_lag_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(
            context["precommit_gate_v4"]["gate_decision"],
            "BOUND_LOCAL_ONLY_TRIPLE_STABILITY_GUARDED",
        )
        self.assertEqual(context["residual_order_gate_v2"]["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(
            gate["gate_reason"], "RESIDUAL_MULTI_LAG_ORDER_STABILITY_GATE_BLOCKED"
        )

    def test_missing_sources_are_unknown(self) -> None:
        self.assertEqual(self._evaluate(precommit_gate_v4=None)["source_state"], "MISSING")
        self.assertEqual(self._evaluate(residual_order_gate_v2=None)["source_state"], "MISSING")

    def test_unsupported_sources_are_distinct(self) -> None:
        source = {"schema_version": "v0", "static_fingerprint": "v0"}
        self.assertEqual(
            self._evaluate(
                precommit_gate_v4=source, expected_precommit_gate_v4_hash="a" * 64
            )["source_state"],
            "UNSUPPORTED",
        )
        self.assertEqual(
            self._evaluate(
                residual_order_gate_v2=source,
                expected_residual_order_gate_v2_hash="a" * 64,
            )["source_state"],
            "UNSUPPORTED",
        )

    def test_expected_hashes_are_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_precommit_gate_v4_hash="0" * 64)["source_state"],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_residual_order_gate_v2_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_resealed_source_tampering_is_invalid(self) -> None:
        source = deepcopy(self.residual_order_gate_v2)
        source["maximum_observed_absolute_multi_lag_residual_energy_coupling"] = "1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(
            self._evaluate(residual_order_gate_v2=source)["source_state"], "INVALID"
        )

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.case.h1_case.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )

    def test_cross_gate_hashes_are_bound(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["source_residual_order_gate_v1_hash"],
            self.residual_order_gate_v2["source_residual_order_gate_v1_hash"],
        )
        self.assertEqual(
            gate["source_calibration_observations_hash"],
            self.residual_order_gate_v2["source_calibration_observations_hash"],
        )
        self.assertTrue(gate["facts"]["cross_gate_source_hashes_bound"])

    def test_blockers_are_deduplicated(self) -> None:
        gate = self._evaluate()
        self.assertEqual(len(gate["blockers"]), len(set(gate["blockers"])))
        self.assertEqual(gate["blockers"][-1], "PRECOMMIT_GATE_V5_NOT_ACTIVATED")

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

    def test_guard_is_not_independence_proof_or_authority(self) -> None:
        for gate in (self._evaluate(), self._evaluate(precommit_gate_v4=None)):
            self.assertFalse(gate["facts"]["residual_order_independence_proven"])
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_resealed_v5_tamper_is_rejected(self) -> None:
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

    def test_schema_and_fingerprint_are_exact(self) -> None:
        self.assertEqual(
            GATE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v5",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260902-cross-lag-factor-calibration-precommit-gate-5",
        )
        gate = self._evaluate()
        self.assertEqual(gate["evaluated_lags"], [1, 2])
        self.assertEqual(
            gate["maximum_allowed_absolute_multi_lag_residual_energy_coupling"],
            "0.8",
        )


if __name__ == "__main__":
    unittest.main()
