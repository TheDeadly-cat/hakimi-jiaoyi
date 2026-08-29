from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4 import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3 as j0_fixtures
from tests import test_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate as i0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV4Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = j0_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV3Tests(
            methodName="test_dual_stable_composition_is_bound_local_only"
        )
        case.setUp()
        self.case = case
        self.precommit_gate_v2 = case.precommit_gate_v2
        self.residual_energy_gate = case.residual_energy_gate
        self.precommit_gate_v1 = case.precommit_gate_v1
        self.beta_stability_gate = case.beta_stability_gate
        self.declaration = case.declaration
        self.report = case.report
        self.replay = case.replay
        self.registration = case.registration
        self.observations = case.observations
        self.precommit_gate_v3 = case._evaluate()
        self.residual_order_gate = self._order_gate(
            self.beta_stability_gate,
            self.replay,
            self.registration,
            self.observations,
        )

    @staticmethod
    def _order_gate(beta_gate, replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate(
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

    def _order_block_context(self):
        i0_case = i0_fixtures.StrategyCorrelationCrossLagFactorCalibrationResidualEnergyStabilityGateTests(
            methodName="test_equal_nonzero_residual_energy_is_stable_candidate"
        )
        i0_case.setUp()
        observations, replay, beta_gate, residual_energy_gate = i0_case._path_gate(
            [1, 1, 1, 1]
        )
        registration = i0_case.registration
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
        declaration = self.case.h1_case.case._declaration(report)
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
        precommit_gate_v2 = self.case.h1_case._evaluate(
            precommit_gate_v1=precommit_gate_v1,
            stability_gate=beta_gate,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        precommit_gate_v3 = self.case._evaluate(
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
        residual_order_gate = self._order_gate(
            beta_gate, replay, registration, observations
        )
        return {
            "precommit_gate_v3": precommit_gate_v3,
            "residual_order_gate": residual_order_gate,
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

    def _j0_block_context(self):
        context = self.case._residual_block_context()
        precommit_gate_v3 = self.case._evaluate(**context)
        residual_order_gate = self._order_gate(
            context["beta_stability_gate"],
            context["replay"],
            context["registration"],
            context["observations"],
        )
        return {
            "precommit_gate_v3": precommit_gate_v3,
            "residual_order_gate": residual_order_gate,
            **context,
        }

    def _evaluate(
        self,
        precommit_gate_v3=...,
        residual_order_gate=...,
        **overrides,
    ):
        values = {
            "precommit_gate_v3": self.precommit_gate_v3 if precommit_gate_v3 is ... else precommit_gate_v3,
            "residual_order_gate": self.residual_order_gate if residual_order_gate is ... else residual_order_gate,
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
            "expected_precommit_gate_v3_hash": "" if values["precommit_gate_v3"] is None else values["precommit_gate_v3"].get("gate_hash"),
            "expected_residual_order_gate_hash": "" if values["residual_order_gate"] is None else values["residual_order_gate"].get("gate_hash"),
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
        if overrides:
            raise TypeError(f"unexpected overrides: {sorted(overrides)}")
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
            values["precommit_gate_v3"],
            values["residual_order_gate"],
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
            "precommit_gate_v3": self.precommit_gate_v3,
            "residual_order_gate": self.residual_order_gate,
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
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4(
            gate,
            values["precommit_gate_v3"],
            values["residual_order_gate"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            expected_precommit_gate_v3_hash=values["precommit_gate_v3"]["gate_hash"],
            expected_residual_order_gate_hash=values["residual_order_gate"]["gate_hash"],
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

    def test_triple_guard_is_bound_local_only(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["gate_decision"], "BOUND_LOCAL_ONLY_TRIPLE_STABILITY_GUARDED"
        )
        self.assertEqual(gate["source_state"], "OBSERVED")
        self.assertTrue(self._verify(gate))

    def test_order_block_overrides_j0_local_binding(self) -> None:
        context = self._order_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(
            context["precommit_gate_v3"]["gate_decision"],
            "BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED",
        )
        self.assertEqual(context["residual_order_gate"]["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(
            gate["gate_reason"], "RESIDUAL_ORDER_STABILITY_GATE_BLOCKED"
        )

    def test_j0_block_remains_monotone(self) -> None:
        context = self._j0_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(context["precommit_gate_v3"]["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_PRECOMMIT_GATE_V3_BLOCKED")

    def test_missing_j0_gate_is_unknown(self) -> None:
        gate = self._evaluate(precommit_gate_v3=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["PRECOMMIT_GATE_V3_MISSING"])

    def test_missing_order_gate_is_unknown(self) -> None:
        gate = self._evaluate(residual_order_gate=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(
            gate["blockers"], ["RESIDUAL_ORDER_STABILITY_GATE_MISSING"]
        )

    def test_unsupported_sources_are_distinct(self) -> None:
        j0 = {"schema_version": "v0", "static_fingerprint": "v0"}
        self.assertEqual(
            self._evaluate(
                precommit_gate_v3=j0,
                expected_precommit_gate_v3_hash="a" * 64,
            )["source_state"],
            "UNSUPPORTED",
        )
        order = {"schema_version": "v0", "static_fingerprint": "v0"}
        self.assertEqual(
            self._evaluate(
                residual_order_gate=order,
                expected_residual_order_gate_hash="a" * 64,
            )["source_state"],
            "UNSUPPORTED",
        )

    def test_expected_source_hashes_are_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_precommit_gate_v3_hash="0" * 64)[
                "source_state"
            ],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_residual_order_gate_hash="0" * 64)[
                "source_state"
            ],
            "INVALID",
        )

    def test_coherently_resealed_j0_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v3)
        source["gate_reason"] = "RESEALED"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(precommit_gate_v3=source)["source_state"], "INVALID")

    def test_coherently_resealed_order_tamper_is_invalid(self) -> None:
        source = deepcopy(self.residual_order_gate)
        source["maximum_observed_absolute_lag_one_residual_energy_coupling"] = "1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(
            self._evaluate(residual_order_gate=source)["source_state"], "INVALID"
        )

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.h1_case.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )

    def test_cross_gate_hashes_are_bound(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["source_beta_stability_gate_hash"],
            self.residual_order_gate["source_beta_stability_gate_hash"],
        )
        self.assertEqual(
            gate["source_calibration_observations_hash"],
            self.residual_order_gate["source_calibration_observations_hash"],
        )
        self.assertTrue(gate["facts"]["cross_gate_source_hashes_bound"])

    def test_blockers_are_deduplicated_in_source_order(self) -> None:
        gate = self._evaluate()
        self.assertEqual(len(gate["blockers"]), len(set(gate["blockers"])))
        self.assertEqual(gate["blockers"][-1], "PRECOMMIT_GATE_V4_NOT_ACTIVATED")

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

    def test_triple_guard_is_not_proof_or_authority(self) -> None:
        for gate in (self._evaluate(), self._evaluate(precommit_gate_v3=None)):
            self.assertFalse(gate["facts"]["beta_temporal_stability_proven"])
            self.assertFalse(
                gate["facts"]["residual_energy_temporal_stability_proven"]
            )
            self.assertFalse(gate["facts"]["residual_order_independence_proven"])
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_resealed_v4_gate_tamper_is_rejected(self) -> None:
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
            "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v4",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260831-cross-lag-factor-calibration-precommit-gate-4",
        )
        gate = self._evaluate()
        self.assertEqual(gate["fold_count"], 4)
        self.assertEqual(
            gate["maximum_allowed_absolute_lag_one_residual_energy_coupling"],
            "0.8",
        )


if __name__ == "__main__":
    unittest.main()
