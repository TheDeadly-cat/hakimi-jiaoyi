from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3 import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2 as h1_fixtures
from tests import test_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate as i0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        h1_case = h1_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV2Tests(
            methodName="test_complete_context_is_bound_for_both_verifiers"
        )
        h1_case.setUp()
        self.h1_case = h1_case
        self.precommit_gate_v1 = h1_case.precommit_gate_v1
        self.beta_stability_gate = h1_case.stability_gate
        self.declaration = h1_case.declaration
        self.report = h1_case.report
        self.replay = h1_case.replay
        self.registration = h1_case.registration
        self.observations = h1_case.observations
        self.precommit_gate_v2 = h1_case._evaluate()
        self.residual_energy_gate = self._residual_gate(
            self.beta_stability_gate,
            self.replay,
            self.registration,
            self.observations,
        )

    @staticmethod
    def _residual_gate(beta_gate, replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate(
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

    def _residual_block_context(self):
        i0_case = i0_fixtures.StrategyCorrelationCrossLagFactorCalibrationResidualEnergyStabilityGateTests(
            methodName="test_beta_stable_residual_energy_regime_shift_is_blocked"
        )
        i0_case.setUp()
        observations, replay, beta_gate, residual_gate = i0_case._path_gate(
            [1, 1, 81, 81]
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
        declaration = self.h1_case.case._declaration(report)
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
        precommit_gate_v2 = self.h1_case._evaluate(
            precommit_gate_v1=precommit_gate_v1,
            stability_gate=beta_gate,
            declaration=declaration,
            report=report,
            replay=replay,
            registration=registration,
            observations=observations,
        )
        return {
            "precommit_gate_v2": precommit_gate_v2,
            "residual_energy_gate": residual_gate,
            "precommit_gate_v1": precommit_gate_v1,
            "beta_stability_gate": beta_gate,
            "declaration": declaration,
            "report": report,
            "replay": replay,
            "registration": registration,
            "observations": observations,
        }

    def _source_block_context(self):
        context = self.h1_case._source_block_context()
        residual_gate = self._residual_gate(
            context["stability_gate"],
            context["replay"],
            context["registration"],
            context["observations"],
        )
        precommit_gate_v2 = self.h1_case._evaluate(**context)
        return {
            "precommit_gate_v2": precommit_gate_v2,
            "residual_energy_gate": residual_gate,
            "precommit_gate_v1": context["precommit_gate_v1"],
            "beta_stability_gate": context["stability_gate"],
            "declaration": context["declaration"],
            "report": context["report"],
            "replay": context["replay"],
            "registration": context["registration"],
            "observations": context["observations"],
        }

    def _evaluate(
        self,
        precommit_gate_v2=...,
        residual_energy_gate=...,
        *,
        precommit_gate_v1=...,
        beta_stability_gate=...,
        declaration=...,
        report=...,
        replay=...,
        registration=...,
        observations=...,
        expected_precommit_gate_v2_hash=None,
        expected_residual_energy_gate_hash=None,
        expected_precommit_gate_v1_hash=None,
        expected_beta_stability_gate_hash=None,
        expected_declaration_hash=None,
        expected_report_hash=None,
        expected_replay_hash=None,
        expected_registration_hash=None,
        expected_observations_hash=None,
    ):
        values = {
            "precommit_gate_v2": self.precommit_gate_v2 if precommit_gate_v2 is ... else precommit_gate_v2,
            "residual_energy_gate": self.residual_energy_gate if residual_energy_gate is ... else residual_energy_gate,
            "precommit_gate_v1": self.precommit_gate_v1 if precommit_gate_v1 is ... else precommit_gate_v1,
            "beta_stability_gate": self.beta_stability_gate if beta_stability_gate is ... else beta_stability_gate,
            "declaration": self.declaration if declaration is ... else declaration,
            "report": self.report if report is ... else report,
            "replay": self.replay if replay is ... else replay,
            "registration": self.registration if registration is ... else registration,
            "observations": self.observations if observations is ... else observations,
        }
        expected_precommit_gate_v2_hash = (
            ("" if values["precommit_gate_v2"] is None else values["precommit_gate_v2"]["gate_hash"])
            if expected_precommit_gate_v2_hash is None else expected_precommit_gate_v2_hash
        )
        expected_residual_energy_gate_hash = (
            ("" if values["residual_energy_gate"] is None else values["residual_energy_gate"]["gate_hash"])
            if expected_residual_energy_gate_hash is None else expected_residual_energy_gate_hash
        )
        if expected_precommit_gate_v1_hash is None:
            expected_precommit_gate_v1_hash = values["precommit_gate_v1"]["gate_hash"]
        if expected_beta_stability_gate_hash is None:
            expected_beta_stability_gate_hash = values["beta_stability_gate"]["gate_hash"]
        if expected_declaration_hash is None:
            expected_declaration_hash = values["declaration"]["declaration_hash"]
        if expected_report_hash is None:
            expected_report_hash = values["report"]["verification_hash"]
        if expected_replay_hash is None:
            expected_replay_hash = values["replay"]["receipt_hash"]
        if expected_registration_hash is None:
            expected_registration_hash = values["registration"]["registration_hash"]
        if expected_observations_hash is None:
            expected_observations_hash = values["observations"]["calibration_observations_hash"]
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            expected_precommit_gate_v2_hash=expected_precommit_gate_v2_hash,
            expected_residual_energy_gate_hash=expected_residual_energy_gate_hash,
            expected_precommit_gate_v1_hash=expected_precommit_gate_v1_hash,
            expected_beta_stability_gate_hash=expected_beta_stability_gate_hash,
            expected_declaration_hash=expected_declaration_hash,
            expected_report_hash=expected_report_hash,
            expected_replay_hash=expected_replay_hash,
            expected_registration_hash=expected_registration_hash,
            expected_calibration_observations_hash=expected_observations_hash,
        )

    def _verify(self, gate, **context):
        defaults = {
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
        defaults.update(context)
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3(
            gate,
            defaults["precommit_gate_v2"],
            defaults["residual_energy_gate"],
            defaults["precommit_gate_v1"],
            defaults["beta_stability_gate"],
            defaults["declaration"],
            defaults["report"],
            defaults["replay"],
            defaults["registration"],
            defaults["observations"],
            expected_precommit_gate_v2_hash=defaults["precommit_gate_v2"]["gate_hash"],
            expected_residual_energy_gate_hash=defaults["residual_energy_gate"]["gate_hash"],
            expected_precommit_gate_v1_hash=defaults["precommit_gate_v1"]["gate_hash"],
            expected_beta_stability_gate_hash=defaults["beta_stability_gate"]["gate_hash"],
            expected_declaration_hash=defaults["declaration"]["declaration_hash"],
            expected_report_hash=defaults["report"]["verification_hash"],
            expected_replay_hash=defaults["replay"]["receipt_hash"],
            expected_registration_hash=defaults["registration"]["registration_hash"],
            expected_calibration_observations_hash=defaults["observations"]["calibration_observations_hash"],
        )

    def test_dual_stable_composition_is_bound_local_only(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["gate_decision"], "BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED")
        self.assertEqual(gate["source_state"], "OBSERVED")
        self.assertTrue(self._verify(gate))

    def test_residual_energy_block_overrides_h1_local_binding(self) -> None:
        context = self._residual_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(context["precommit_gate_v2"]["gate_decision"], "BOUND_LOCAL_ONLY_STABILITY_GUARDED")
        self.assertEqual(context["residual_energy_gate"]["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "RESIDUAL_ENERGY_STABILITY_GATE_BLOCKED")

    def test_h1_source_block_remains_block(self) -> None:
        context = self._source_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_PRECOMMIT_GATE_V2_BLOCKED")

    def test_missing_h1_gate_is_unknown(self) -> None:
        gate = self._evaluate(precommit_gate_v2=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["PRECOMMIT_GATE_V2_MISSING"])

    def test_missing_i0_gate_is_unknown(self) -> None:
        gate = self._evaluate(residual_energy_gate=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["RESIDUAL_ENERGY_STABILITY_GATE_MISSING"])

    def test_unsupported_sources_are_distinct(self) -> None:
        h1 = {"schema_version": "v0", "static_fingerprint": "v0"}
        self.assertEqual(self._evaluate(precommit_gate_v2=h1, expected_precommit_gate_v2_hash="a" * 64)["source_state"], "UNSUPPORTED")
        i0 = {"schema_version": "v0", "static_fingerprint": "v0"}
        self.assertEqual(self._evaluate(residual_energy_gate=i0, expected_residual_energy_gate_hash="a" * 64)["source_state"], "UNSUPPORTED")

    def test_expected_source_hashes_are_bound(self) -> None:
        self.assertEqual(self._evaluate(expected_precommit_gate_v2_hash="0" * 64)["source_state"], "INVALID")
        self.assertEqual(self._evaluate(expected_residual_energy_gate_hash="0" * 64)["source_state"], "INVALID")

    def test_coherently_resealed_h1_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v2)
        source["maximum_observed_normalized_beta_drift"] = "0.1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(precommit_gate_v2=source)["source_state"], "INVALID")

    def test_coherently_resealed_i0_tamper_is_invalid(self) -> None:
        source = deepcopy(self.residual_energy_gate)
        source["maximum_observed_normalized_residual_energy_dispersion"] = "1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(self._evaluate(residual_energy_gate=source)["source_state"], "INVALID")

    def test_complete_context_is_bound(self) -> None:
        observations = self.h1_case.fixture._observations(count=39)
        self.assertEqual(self._evaluate(observations=observations)["source_state"], "INVALID")

    def test_source_hashes_are_cross_bound(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["source_beta_stability_gate_hash"], self.beta_stability_gate["gate_hash"])
        self.assertEqual(gate["source_beta_stability_gate_hash"], self.residual_energy_gate["source_beta_stability_gate_hash"])
        self.assertEqual(gate["source_replay_hash"], self.residual_energy_gate["source_replay_hash"])
        self.assertTrue(gate["facts"]["cross_gate_source_hashes_bound"])

    def test_blockers_are_deduplicated_in_source_order(self) -> None:
        gate = self._evaluate()
        self.assertEqual(len(gate["blockers"]), len(set(gate["blockers"])))
        self.assertEqual(gate["blockers"][-1], "PRECOMMIT_GATE_V3_NOT_ACTIVATED")

    def test_projection_is_aggregate_only(self) -> None:
        gate = self._evaluate()
        keys = set()
        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values(): collect(nested)
            elif type(value) is list:
                for nested in value: collect(nested)
        collect(gate)
        self.assertTrue({"rows", "identity_order", "beta_by_identity", "returns", "factor_return", "folds"}.isdisjoint(keys))

    def test_dual_stability_is_not_proven(self) -> None:
        gate = self._evaluate()
        self.assertFalse(gate["facts"]["beta_temporal_stability_proven"])
        self.assertFalse(gate["facts"]["residual_energy_temporal_stability_proven"])
        self.assertFalse(gate["facts"]["external_time_anchor_verified"])

    def test_authority_is_permanently_locked(self) -> None:
        for gate in (self._evaluate(), self._evaluate(precommit_gate_v2=None)):
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_sources_are_invalid(self) -> None:
        class DictSubclass(dict): pass
        self.assertEqual(self._evaluate(precommit_gate_v2=DictSubclass(self.precommit_gate_v2))["source_state"], "INVALID")
        source = deepcopy(self.residual_energy_gate)
        source["unstable_identity_count"] = float("nan")
        self.assertEqual(self._evaluate(residual_energy_gate=source)["source_state"], "INVALID")

    def test_resealed_v3_gate_tamper_is_rejected(self) -> None:
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
        self.assertEqual(GATE_SCHEMA, "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v3")
        self.assertEqual(STATIC_FINGERPRINT, "20260829-cross-lag-factor-calibration-precommit-gate-3")
        gate = self._evaluate()
        self.assertEqual(gate["fold_count"], 4)
        self.assertEqual(gate["maximum_allowed_normalized_beta_drift"], "0.5")
        self.assertEqual(gate["maximum_allowed_normalized_residual_energy_dispersion"], "0.75")


if __name__ == "__main__":
    unittest.main()
