from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3 import (
    PRESENTATION_STATUS,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6 as consumer_v6_tests


class StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        ConsumerCase = consumer_v6_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV6Tests
        self.case = ConsumerCase(
            unittest.defaultTestLoader.getTestCaseNames(ConsumerCase)[0]
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.consumer = self.case._consume()

    def _values(self) -> dict[str, object]:
        return {
            "report_consumer_v6": self.consumer,
            **self.case._values(),
        }

    def _expected(self, values: dict[str, object]) -> dict[str, object]:
        expected = self.case._expected(values)
        expected["expected_report_consumer_v6_hash"] = values[
            "report_consumer_v6"
        ]["verification_hash"]
        return expected

    def _build(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        values = {key: value for key, value in values.items() if not key.startswith("expected_")}
        return build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
            **values,
            **expected,
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {key: value for key, value in overrides.items() if key.startswith("expected_")}
        )
        values = {key: value for key, value in values.items() if not key.startswith("expected_")}
        args = [
            values.pop("report_consumer_v6"),
            values.pop("precommit_gate_v6"),
            values.pop("report_consumer_v5"),
            values.pop("precommit_gate_v5"),
            values.pop("residual_order_gate_v3"),
            values.pop("precommit_gate_v4"),
            values.pop("residual_order_gate_v2"),
            values.pop("precommit_gate_v3"),
            values.pop("residual_order_gate_v1"),
            values.pop("precommit_gate_v2"),
            values.pop("residual_energy_gate"),
            values.pop("precommit_gate_v1"),
            values.pop("beta_stability_gate"),
            values.pop("precommit_declaration"),
            values.pop("source_report"),
            values.pop("replay"),
            values.pop("residualization_registration"),
            values.pop("calibration_observations"),
        ]
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
            document,
            *args,
            **expected,
        )

    def _block_context(self) -> dict[str, object]:
        source = self.case._context("v3")
        consumer = self.case._consume(**source)
        values = {
            "report_consumer_v6": consumer,
            **{
                key: value
                for key, value in source.items()
                if not key.startswith("expected_")
            },
        }
        return {**values, **self._expected(values)}

    def test_positive_consumer_maps_to_local_binding_four_axis(self) -> None:
        result = self._build()
        self.assertEqual(result["display_state"], "LOCAL_BINDING")
        self.assertEqual(
            [
                result["source_axis"]["label"],
                result["gap_axis"]["label"],
                result["maturity_axis"]["label"],
                result["permission_axis"]["label"],
            ],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(self._verify(result))

    def test_verified_block_maps_to_evidence_block(self) -> None:
        context = self._block_context()
        result = self._build(**context)
        self.assertEqual(result["display_state"], "EVIDENCE_BLOCK")
        self.assertEqual(result["maturity_axis"]["state"], "EVIDENCE_BLOCK")
        self.assertEqual(result["permission_axis"]["state"], "LOCKED")
        self.assertTrue(self._verify(result, **context))

    def test_missing_consumer_is_unknown(self) -> None:
        values = self._values()
        expected = self._expected(values)
        values["report_consumer_v6"] = None
        result = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
            **values,
            **expected,
        )
        self.assertEqual(result["display_state"], "UNKNOWN")
        self.assertEqual(result["display_reason"], "MISSING_REPORT_CONSUMER_V6")

    def test_unsupported_consumer_is_distinct(self) -> None:
        values = self._values()
        expected = self._expected(values)
        values["report_consumer_v6"] = {"schema_version": "legacy"}
        result = build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3(
            **values,
            **expected,
        )
        self.assertEqual(result["source_state"], "UNSUPPORTED")

    def test_expected_consumer_hash_is_bound(self) -> None:
        result = self._build(expected_report_consumer_v6_hash="0" * 64)
        self.assertEqual(
            result["display_reason"],
            "EXPECTED_REPORT_CONSUMER_V6_HASH_MISMATCH",
        )

    def test_resealed_consumer_tamper_is_invalid(self) -> None:
        consumer = deepcopy(self.consumer)
        consumer.pop("verification_hash")
        consumer["verification_reason"] = "RESEALED_DRIFT"
        consumer = seal_strict_canonical_document(consumer, "verification_hash")
        result = self._build(
            report_consumer_v6=consumer,
            expected_report_consumer_v6_hash=consumer["verification_hash"],
        )
        self.assertEqual(
            result["display_reason"],
            "REPORT_CONSUMER_V6_OR_CONTEXT_INVALID",
        )

    def test_complete_context_is_bound(self) -> None:
        context = self._block_context()
        result = self._build(
            report_consumer_v6=context["report_consumer_v6"],
            expected_report_consumer_v6_hash=context[
                "expected_report_consumer_v6_hash"
            ],
        )
        self.assertEqual(result["display_state"], "UNKNOWN")

    def test_phase_comb_exposes_three_coverage_teeth_only(self) -> None:
        phase = self._build()["phase_comb"]
        self.assertEqual(
            phase["teeth"],
            [
                {"lag": 1, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 2, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 3, "coverage": "PREREGISTERED", "result_exposed": False},
            ],
        )
        self.assertFalse(phase["private_ledger_exposed"])

    def test_maturity_axis_is_exact_three_lag_aggregate(self) -> None:
        maturity = self._build()["maturity_axis"]
        self.assertEqual(maturity["evaluated_lags"], [1, 2, 3])
        self.assertEqual(maturity["maximum_evaluated_lag"], 3)
        self.assertEqual(
            maturity["observed_maximum"],
            self.consumer[
                "maximum_observed_absolute_three_lag_residual_energy_coupling"
            ],
        )

    def test_envelope_is_aggregate_only(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        for private_key in ('"rows"', '"returns"', '"beta_by_identity"', '"ledger"'):
            self.assertNotIn(private_key, serialized)

    def test_gap_remains_open(self) -> None:
        result = self._build()
        self.assertEqual(result["gap_axis"]["state"], "OPEN")
        self.assertTrue(result["gap_axis"]["arbitrary_lag_independence_unresolved"])
        self.assertFalse(result["facts"]["residual_order_independence_proven"])

    def test_permission_and_mounting_are_locked(self) -> None:
        result = self._build()
        self.assertEqual(result["permission_axis"]["state"], "LOCKED")
        for key, value in result["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_public_copy_contains_no_ready_or_profit_claim(self) -> None:
        result = self._build()
        public_strings = []

        def collect_strings(value) -> None:
            if isinstance(value, str):
                public_strings.append(value)
            elif isinstance(value, dict):
                for item in value.values():
                    collect_strings(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    collect_strings(item)

        collect_strings(result)
        public_copy = " ".join(public_strings).lower()
        self.assertNotRegex(
            public_copy,
            r'\bready\b|\bprofit(?:able|ability)?\b|盈利|收益证明',
        )
        self.assertFalse(result["authority"]["profitability_claim_allowed"])
        self.assertFalse(
            result["permission_axis"]["profitability_claim_allowed"]
        )

    def test_determinism(self) -> None:
        self.assertEqual(self._build(), self._build())

    def test_verifier_rejects_resealed_envelope_tamper(self) -> None:
        result = self._build()
        tampered = deepcopy(result)
        tampered.pop("presentation_hash")
        tampered["permission_axis"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "presentation_hash")
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_and_status_are_exact(self) -> None:
        result = self._build()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["presentation_status"], PRESENTATION_STATUS)


if __name__ == "__main__":
    unittest.main()
