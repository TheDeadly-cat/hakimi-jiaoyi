from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2 import (
    GATE_SCHEMA,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_report_consumer import (
    consume_strategy_correlation_cross_lag_factor_calibration_replay,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_stability_gate import (
    evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate as g3_fixtures
from tests import test_strategy_correlation_cross_lag_factor_calibration_stability_gate as h0_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = g3_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateTests(
            methodName="test_match_is_bound_local_only"
        )
        case.setUp()
        self.case = case
        self.fixture = case.case.fixture
        self.registration = case.registration
        self.observations = case.observations
        self.replay = case.replay
        self.report = case.report
        self.declaration = case.declaration
        self.precommit_gate_v1 = case._evaluate()
        self.stability_gate = self._stability(
            self.replay, self.registration, self.observations
        )

    @staticmethod
    def _stability(replay, registration, observations):
        return evaluate_strategy_correlation_cross_lag_factor_calibration_stability_gate(
            replay,
            registration,
            observations,
            expected_replay_hash=replay["receipt_hash"],
            expected_registration_hash=registration["registration_hash"],
            expected_calibration_observations_hash=observations[
                "calibration_observations_hash"
            ],
        )

    def _drift_context(self):
        h0_case = h0_fixtures.StrategyCorrelationCrossLagFactorCalibrationStabilityGateTests(
            methodName="test_full_window_match_with_regime_drift_is_blocked"
        )
        h0_case.setUp()
        observations = h0_case._piecewise((0.0, 0.0, 2.0, 2.0))
        registration = h0_case.registration
        replay = h0_case._replay(registration, observations)
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
        declaration = self.case._declaration(report)
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
        stability_gate = self._stability(replay, registration, observations)
        return {
            "precommit_gate_v1": precommit_gate_v1,
            "stability_gate": stability_gate,
            "declaration": declaration,
            "report": report,
            "replay": replay,
            "registration": registration,
            "observations": observations,
        }

    def _source_block_context(self):
        registration, replay, report, declaration = self.case._block_context()
        precommit_gate_v1 = self.case._evaluate(
            declaration,
            report=report,
            replay=replay,
            registration=registration,
        )
        stability_gate = self._stability(replay, registration, self.observations)
        return {
            "precommit_gate_v1": precommit_gate_v1,
            "stability_gate": stability_gate,
            "declaration": declaration,
            "report": report,
            "replay": replay,
            "registration": registration,
            "observations": self.observations,
        }

    def _evaluate(self, **overrides):
        values = {
            "precommit_gate_v1": self.precommit_gate_v1,
            "stability_gate": self.stability_gate,
            "declaration": self.declaration,
            "report": self.report,
            "replay": self.replay,
            "registration": self.registration,
            "observations": self.observations,
        }
        values.update({key: value for key, value in overrides.items() if not key.startswith("expected_")})
        expected = {
            "expected_precommit_gate_v1_hash": "" if values["precommit_gate_v1"] is None else values["precommit_gate_v1"]["gate_hash"],
            "expected_stability_gate_hash": "" if values["stability_gate"] is None else values["stability_gate"]["gate_hash"],
            "expected_declaration_hash": values["declaration"]["declaration_hash"],
            "expected_report_hash": values["report"]["verification_hash"],
            "expected_replay_hash": values["replay"]["receipt_hash"],
            "expected_registration_hash": values["registration"]["registration_hash"],
            "expected_calibration_observations_hash": values["observations"]["calibration_observations_hash"],
        }
        expected.update({key: value for key, value in overrides.items() if key.startswith("expected_")})
        return evaluate_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2(
            values["precommit_gate_v1"],
            values["stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            **expected,
        )

    def _verify(self, gate, **overrides):
        values = {
            "precommit_gate_v1": self.precommit_gate_v1,
            "stability_gate": self.stability_gate,
            "declaration": self.declaration,
            "report": self.report,
            "replay": self.replay,
            "registration": self.registration,
            "observations": self.observations,
        }
        values.update({key: value for key, value in overrides.items() if not key.startswith("expected_")})
        expected = {
            "expected_precommit_gate_v1_hash": "" if values["precommit_gate_v1"] is None else values["precommit_gate_v1"]["gate_hash"],
            "expected_stability_gate_hash": "" if values["stability_gate"] is None else values["stability_gate"]["gate_hash"],
            "expected_declaration_hash": values["declaration"]["declaration_hash"],
            "expected_report_hash": values["report"]["verification_hash"],
            "expected_replay_hash": values["replay"]["receipt_hash"],
            "expected_registration_hash": values["registration"]["registration_hash"],
            "expected_calibration_observations_hash": values["observations"]["calibration_observations_hash"],
        }
        expected.update({key: value for key, value in overrides.items() if key.startswith("expected_")})
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2(
            gate,
            values["precommit_gate_v1"],
            values["stability_gate"],
            values["declaration"],
            values["report"],
            values["replay"],
            values["registration"],
            values["observations"],
            **expected,
        )

    def test_stable_precommit_is_bound_local_only_with_guard(self) -> None:
        gate = self._evaluate()
        self.assertEqual(gate["source_state"], "OBSERVED")
        self.assertEqual(
            gate["gate_decision"], "BOUND_LOCAL_ONLY_STABILITY_GUARDED"
        )
        self.assertTrue(gate["facts"]["cross_gate_source_hashes_bound"])
        self.assertTrue(gate["facts"]["beta_stability_threshold_passed"])
        self.assertTrue(self._verify(gate))

    def test_h0_block_overrides_g3_local_binding(self) -> None:
        context = self._drift_context()
        self.assertEqual(
            context["precommit_gate_v1"]["gate_decision"], "BOUND_LOCAL_ONLY"
        )
        self.assertEqual(context["stability_gate"]["gate_decision"], "BLOCK")
        gate = self._evaluate(**context)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "BETA_STABILITY_GATE_BLOCKED")
        self.assertFalse(gate["facts"]["source_gate_block_relaxed"])
        self.assertTrue(self._verify(gate, **context))

    def test_g3_source_block_remains_blocked(self) -> None:
        context = self._source_block_context()
        gate = self._evaluate(**context)
        self.assertEqual(gate["gate_decision"], "BLOCK")
        self.assertEqual(gate["gate_reason"], "SOURCE_PRECOMMIT_GATE_BLOCKED")
        self.assertFalse(gate["facts"]["source_gate_block_relaxed"])

    def test_missing_precommit_gate_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(precommit_gate_v1=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["PRECOMMIT_GATE_V1_MISSING"])
        self.assertTrue(self._verify(gate, precommit_gate_v1=None))

    def test_missing_stability_gate_has_fixed_unknown_closure(self) -> None:
        gate = self._evaluate(stability_gate=None)
        self.assertEqual(gate["source_state"], "MISSING")
        self.assertEqual(gate["blockers"], ["BETA_STABILITY_GATE_MISSING"])

    def test_unsupported_precommit_gate_is_unknown(self) -> None:
        source = {"schema_version": "candidate-v0", "static_fingerprint": "v0", "gate_hash": "a" * 64}
        gate = self._evaluate(precommit_gate_v1=source)
        self.assertEqual(gate["source_state"], "UNSUPPORTED")

    def test_unsupported_stability_gate_is_unknown(self) -> None:
        source = {"schema_version": "candidate-v0", "static_fingerprint": "v0", "gate_hash": "a" * 64}
        gate = self._evaluate(stability_gate=source)
        self.assertEqual(gate["source_state"], "UNSUPPORTED")

    def test_expected_source_gate_hashes_are_bound(self) -> None:
        self.assertEqual(
            self._evaluate(expected_precommit_gate_v1_hash="0" * 64)["source_state"],
            "INVALID",
        )
        self.assertEqual(
            self._evaluate(expected_stability_gate_hash="0" * 64)["source_state"],
            "INVALID",
        )

    def test_coherently_resealed_precommit_gate_tamper_is_invalid(self) -> None:
        source = deepcopy(self.precommit_gate_v1)
        source["future_evaluation_id"] = "EVAL-2025-02-B"
        source = seal_strict_canonical_document(source, "gate_hash")
        gate = self._evaluate(precommit_gate_v1=source)
        self.assertEqual(gate["source_state"], "INVALID")

    def test_coherently_resealed_stability_gate_tamper_is_invalid(self) -> None:
        source = deepcopy(self.stability_gate)
        source["unstable_identity_count"] = 1
        source = seal_strict_canonical_document(source, "gate_hash")
        gate = self._evaluate(stability_gate=source)
        self.assertEqual(gate["source_state"], "INVALID")

    def test_complete_context_is_bound_for_both_verifiers(self) -> None:
        observations = self.fixture._observations(count=39)
        self.assertEqual(
            self._evaluate(observations=observations)["source_state"], "INVALID"
        )
        registration = self.fixture._registration(betas={"A": "0.5", "B": "0.5"})
        self.assertEqual(
            self._evaluate(registration=registration)["source_state"], "INVALID"
        )

    def test_source_hashes_are_cross_bound(self) -> None:
        gate = self._evaluate()
        self.assertEqual(
            gate["source_replay_hash"], self.precommit_gate_v1["source_replay_hash"]
        )
        self.assertEqual(
            gate["source_replay_hash"], self.stability_gate["source_replay_hash"]
        )
        self.assertEqual(
            gate["source_registration_hash"],
            self.stability_gate["source_registration_hash"],
        )
        self.assertEqual(
            gate["source_calibration_observations_hash"],
            self.stability_gate["source_calibration_observations_hash"],
        )

    def test_blockers_are_deduplicated_without_relaxation(self) -> None:
        gate = self._evaluate()
        self.assertEqual(len(gate["blockers"]), len(set(gate["blockers"])))
        for blocker in self.precommit_gate_v1["blockers"]:
            self.assertIn(blocker, gate["blockers"])
        for blocker in self.stability_gate["blockers"]:
            self.assertIn(blocker, gate["blockers"])
        self.assertEqual(gate["blockers"][-1], "PRECOMMIT_GATE_V2_NOT_ACTIVATED")

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
        self.assertTrue({"rows", "identity_order", "beta_by_identity", "factor_id", "returns", "factor_return"}.isdisjoint(keys))
        self.assertNotIn("COMMON-FACTOR-1", json.dumps(gate, sort_keys=True))

    def test_stability_guard_never_becomes_stability_proof(self) -> None:
        gate = self._evaluate()
        self.assertTrue(gate["facts"]["beta_stability_threshold_passed"])
        self.assertFalse(gate["facts"]["beta_temporal_stability_proven"])
        self.assertFalse(gate["authority"]["beta_temporal_stability_proven"])

    def test_authority_is_permanently_locked(self) -> None:
        for gate in (self._evaluate(), self._evaluate(precommit_gate_v1=None)):
            authority = gate["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["future_evaluation_allowed"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(authority["profitability_claim_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_non_native_and_nonfinite_sources_are_invalid(self) -> None:
        class DictSubclass(dict):
            pass
        self.assertEqual(
            self._evaluate(precommit_gate_v1=DictSubclass(self.precommit_gate_v1))["source_state"],
            "INVALID",
        )
        source = deepcopy(self.stability_gate)
        source["maximum_observed_normalized_beta_drift"] = float("nan")
        self.assertEqual(
            self._evaluate(stability_gate=source, expected_stability_gate_hash=self.stability_gate["gate_hash"])["source_state"],
            "INVALID",
        )

    def test_resealed_v2_gate_tamper_is_rejected(self) -> None:
        gate = self._evaluate()
        for field, value in (("gate_decision", "READY"), ("unstable_identity_count", 1)):
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
            "strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v2",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260826-cross-lag-factor-calibration-precommit-gate-2",
        )
        self.assertEqual(gate["source_precommit_gate_v1_hash"], self.precommit_gate_v1["gate_hash"])
        self.assertEqual(gate["source_stability_gate_hash"], self.stability_gate["gate_hash"])


if __name__ == "__main__":
    unittest.main()
