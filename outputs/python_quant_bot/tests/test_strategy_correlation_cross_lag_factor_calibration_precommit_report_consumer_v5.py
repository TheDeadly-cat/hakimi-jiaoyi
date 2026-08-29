from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5 import (
    REPORT_SCHEMA,
    STATIC_FINGERPRINT,
    consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5 as v5_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV5Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = v5_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV5Tests(
            methodName="test_multi_lag_guard_is_bound_local_only"
        )
        case.setUp()
        self.case = case
        self.source = case._evaluate()

    def _values(self):
        return {
            "precommit_gate_v5": self.source,
            "precommit_gate_v4": self.case.precommit_gate_v4,
            "residual_order_gate_v2": self.case.residual_order_gate_v2,
            "precommit_gate_v3": self.case.precommit_gate_v3,
            "residual_order_gate_v1": self.case.residual_order_gate_v1,
            "precommit_gate_v2": self.case.precommit_gate_v2,
            "residual_energy_gate": self.case.residual_energy_gate,
            "precommit_gate_v1": self.case.precommit_gate_v1,
            "beta_stability_gate": self.case.beta_stability_gate,
            "declaration": self.case.declaration,
            "source_report": self.case.report,
            "replay": self.case.replay,
            "registration": self.case.registration,
            "observations": self.case.observations,
        }

    @staticmethod
    def _expected(values):
        return {
            "expected_precommit_gate_v5_hash": "" if values["precommit_gate_v5"] is None else values["precommit_gate_v5"].get("gate_hash"),
            "expected_precommit_gate_v4_hash": values["precommit_gate_v4"]["gate_hash"],
            "expected_residual_order_gate_v2_hash": values["residual_order_gate_v2"]["gate_hash"],
            "expected_precommit_gate_v3_hash": values["precommit_gate_v3"]["gate_hash"],
            "expected_residual_order_gate_v1_hash": values["residual_order_gate_v1"]["gate_hash"],
            "expected_precommit_gate_v2_hash": values["precommit_gate_v2"]["gate_hash"],
            "expected_residual_energy_gate_hash": values["residual_energy_gate"]["gate_hash"],
            "expected_precommit_gate_v1_hash": values["precommit_gate_v1"]["gate_hash"],
            "expected_beta_stability_gate_hash": values["beta_stability_gate"]["gate_hash"],
            "expected_declaration_hash": values["declaration"]["declaration_hash"],
            "expected_source_report_hash": values["source_report"]["verification_hash"],
            "expected_replay_hash": values["replay"]["receipt_hash"],
            "expected_registration_hash": values["registration"]["registration_hash"],
            "expected_calibration_observations_hash": values["observations"]["calibration_observations_hash"],
        }

    def _consume(self, **overrides):
        values = self._values()
        for key in tuple(values):
            if key in overrides:
                values[key] = overrides.pop(key)
        expected = self._expected(values)
        for key in tuple(expected):
            if key in overrides:
                expected[key] = overrides.pop(key)
        return consume_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5(
            values["precommit_gate_v5"],
            values["precommit_gate_v4"],
            values["residual_order_gate_v2"],
            values["precommit_gate_v3"],
            values["residual_order_gate_v1"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["source_report"],
            values["replay"],
            values["registration"],
            values["observations"],
            **expected,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5(
            document,
            values["precommit_gate_v5"],
            values["precommit_gate_v4"],
            values["residual_order_gate_v2"],
            values["precommit_gate_v3"],
            values["residual_order_gate_v1"],
            values["precommit_gate_v2"],
            values["residual_energy_gate"],
            values["precommit_gate_v1"],
            values["beta_stability_gate"],
            values["declaration"],
            values["source_report"],
            values["replay"],
            values["registration"],
            values["observations"],
            **self._expected(values),
        )

    def test_positive_source_is_verified_local_binding(self) -> None:
        report = self._consume()
        self.assertEqual(report["verification_state"], "VERIFIED_LOCAL_BINDING")
        self.assertEqual(
            report["source_gate_decision"],
            "BOUND_LOCAL_ONLY_MULTI_LAG_STABILITY_GUARDED",
        )
        self.assertTrue(self._verify(report))

    def test_block_source_is_verified_block(self) -> None:
        context = self.case._multi_lag_block_context()
        source = self.case._evaluate(**context)
        context["source_report"] = context.pop("report")
        report = self._consume(precommit_gate_v5=source, **context)
        self.assertEqual(source["gate_decision"], "BLOCK")
        self.assertEqual(report["verification_state"], "VERIFIED_BLOCK")
        self.assertEqual(report["verification_reason"], "PRECOMMIT_V5_BLOCK_VERIFIED")

    def test_missing_source_is_unknown(self) -> None:
        report = self._consume(precommit_gate_v5=None)
        self.assertEqual(report["source_state"], "MISSING")
        self.assertEqual(report["verification_state"], "UNKNOWN")
        self.assertEqual(report["blockers"], ["PRECOMMIT_GATE_V5_MISSING"])

    def test_unsupported_source_is_distinct(self) -> None:
        source = {"schema_version": "v0", "static_fingerprint": "v0"}
        report = self._consume(
            precommit_gate_v5=source,
            expected_precommit_gate_v5_hash="a" * 64,
        )
        self.assertEqual(report["source_state"], "UNSUPPORTED")

    def test_expected_source_hash_is_bound(self) -> None:
        report = self._consume(expected_precommit_gate_v5_hash="0" * 64)
        self.assertEqual(report["source_state"], "INVALID")

    def test_coherently_resealed_source_tamper_is_invalid(self) -> None:
        source = deepcopy(self.source)
        source["maximum_observed_absolute_multi_lag_residual_energy_coupling"] = "1"
        source = seal_strict_canonical_document(source, "gate_hash")
        self.assertEqual(
            self._consume(precommit_gate_v5=source)["source_state"], "INVALID"
        )

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.case.case.h1_case.fixture._observations(count=39)
        self.assertEqual(
            self._consume(observations=observations)["source_state"], "INVALID"
        )

    def test_public_report_is_aggregate_only(self) -> None:
        report = self._consume()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(report)
        self.assertTrue(
            {"rows", "returns", "factor_return", "beta_by_identity", "folds", "lags"}.isdisjoint(keys)
        )
        self.assertTrue(report["facts"]["aggregate_only"])

    def test_public_aggregate_fields_are_exactly_bound(self) -> None:
        report = self._consume()
        self.assertEqual(report["evaluated_lags"], [1, 2])
        self.assertEqual(
            report["maximum_allowed_absolute_multi_lag_residual_energy_coupling"],
            "0.8",
        )
        self.assertEqual(report["source_gate_hash"], self.source["gate_hash"])
        self.assertEqual(
            report["source_calibration_observations_hash"],
            self.source["source_calibration_observations_hash"],
        )

    def test_verified_is_not_independence_or_profitability_proof(self) -> None:
        report = self._consume()
        self.assertFalse(report["facts"]["residual_order_independence_proven"])
        self.assertNotIn("READY", str(report))
        self.assertFalse(report["authority"]["profitability_claim_allowed"])

    def test_authority_is_permanently_locked(self) -> None:
        for report in (self._consume(), self._consume(precommit_gate_v5=None)):
            authority = report["authority"]
            self.assertTrue(authority["descriptive_only"])
            self.assertFalse(authority["current_admission_allowed"])
            self.assertFalse(authority["presentation_mount_allowed"])
            self.assertFalse(authority["paper_authorized"])
            self.assertFalse(authority["live_order_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_resealed_report_tamper_is_rejected(self) -> None:
        report = self._consume()
        tampered = deepcopy(report)
        tampered["verification_state"] = "READY"
        tampered = seal_strict_canonical_document(tampered, "verification_hash")
        self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._consume()
            second = self._consume()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_and_fingerprint_are_exact(self) -> None:
        self.assertEqual(
            REPORT_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-report-consumer-verification-v5",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260903-cross-lag-factor-calibration-precommit-report-consumer-5",
        )


if __name__ == "__main__":
    unittest.main()
