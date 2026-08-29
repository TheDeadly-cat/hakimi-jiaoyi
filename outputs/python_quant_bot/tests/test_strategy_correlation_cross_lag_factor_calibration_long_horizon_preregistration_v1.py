from __future__ import annotations

from copy import deepcopy
import json
from unittest.mock import patch
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1 import (
    EVALUATED_LAGS,
    EXTENSION_LAGS,
    INHERITED_LAGS,
    MAXIMUM_EVALUATED_LAG,
    MINIMUM_PAIRS_AT_MAXIMUM_LAG,
    MINIMUM_ROWS_PER_FOLD,
    PROTOCOL_ID,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    TAIL_QUADRATIC_ENERGY_CEILING,
    TAIL_SCORE,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7
    as consumer_v7_tests,
)


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        ConsumerCase = consumer_v7_tests.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV7Tests
        self.case = ConsumerCase(
            unittest.defaultTestLoader.getTestCaseNames(ConsumerCase)[0]
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.consumer = self.case._consume()
        self.preregistered_at_utc = "2026-08-22T00:00:00Z"
        self.evaluation_not_before_date = "2026-10-01"

    def _values(self) -> dict[str, object]:
        return {
            "report_consumer_v7": self.consumer,
            **self.case._values(),
            "preregistered_at_utc": self.preregistered_at_utc,
            "evaluation_not_before_date": self.evaluation_not_before_date,
        }

    def _expected(self, values: dict[str, object]) -> dict[str, object]:
        expected = self.case._expected(values)
        consumer = values.get("report_consumer_v7")
        if not isinstance(consumer, dict) or not isinstance(
            consumer.get("verification_hash"), str
        ):
            consumer = self.consumer
        expected["expected_report_consumer_v7_hash"] = consumer[
            "verification_hash"
        ]
        return expected

    def _build(self, **overrides: object) -> dict[str, object]:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {
                key: value
                for key, value in overrides.items()
                if key.startswith("expected_")
            }
        )
        values = {
            key: value
            for key, value in values.items()
            if not key.startswith("expected_")
        }
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
            **values,
            **expected,
        )

    def _verify(self, document: dict[str, object], **overrides: object) -> bool:
        values = self._values()
        values.update(overrides)
        expected = self._expected(values)
        expected.update(
            {
                key: value
                for key, value in overrides.items()
                if key.startswith("expected_")
            }
        )
        values = {
            key: value
            for key, value in values.items()
            if not key.startswith("expected_")
        }
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1(
            document,
            **values,
            **expected,
        )

    def _block_context(self) -> dict[str, object]:
        source = self.case._omnibus_block_context()
        consumer = self.case._consume(**source)
        values = {
            "report_consumer_v7": consumer,
            **{
                key: value
                for key, value in source.items()
                if not key.startswith("expected_")
            },
            "preregistered_at_utc": self.preregistered_at_utc,
            "evaluation_not_before_date": self.evaluation_not_before_date,
        }
        return {**values, **self._expected(values)}

    def test_positive_source_declares_not_evaluated_protocol(self) -> None:
        result = self._build()
        self.assertEqual(result["source_state"], "VERIFIED")
        self.assertEqual(
            result["preregistration_state"],
            "DECLARED_NOT_EVALUATED",
        )
        self.assertEqual(result["evaluation_status"], "NOT_EVALUATED")
        self.assertTrue(result["facts"]["source_consumer_v7_verified"])
        self.assertTrue(self._verify(result))

    def test_long_horizon_design_is_exact_and_derived(self) -> None:
        result = self._build()
        self.assertEqual(result["protocol_id"], PROTOCOL_ID)
        self.assertEqual(result["minimum_rows_per_fold"], MINIMUM_ROWS_PER_FOLD)
        self.assertEqual(result["evaluated_lags"], list(EVALUATED_LAGS))
        self.assertEqual(result["inherited_lags"], list(INHERITED_LAGS))
        self.assertEqual(result["extension_lags"], list(EXTENSION_LAGS))
        self.assertEqual(result["maximum_evaluated_lag"], MAXIMUM_EVALUATED_LAG)
        self.assertEqual(
            result["minimum_pairs_at_maximum_lag"],
            MINIMUM_PAIRS_AT_MAXIMUM_LAG,
        )
        self.assertEqual(
            MINIMUM_PAIRS_AT_MAXIMUM_LAG,
            MINIMUM_ROWS_PER_FOLD - MAXIMUM_EVALUATED_LAG,
        )
        self.assertEqual(result["tail_score"], TAIL_SCORE)
        self.assertEqual(
            result["maximum_allowed_tail_quadratic_energy"],
            TAIL_QUADRATIC_ENERGY_CEILING,
        )
        self.assertTrue(result["inclusive_ceiling"])

    def test_missing_and_unsupported_source_are_distinct(self) -> None:
        missing = self._build(report_consumer_v7=None)
        self.assertEqual(missing["source_state"], "MISSING")
        unsupported = self._build(
            report_consumer_v7={"schema_version": "legacy"}
        )
        self.assertEqual(unsupported["source_state"], "UNSUPPORTED")

    def test_expected_consumer_hash_is_bound(self) -> None:
        result = self._build(expected_report_consumer_v7_hash="0" * 64)
        self.assertEqual(result["source_state"], "INVALID")
        self.assertEqual(
            result["preregistration_reason"],
            "EXPECTED_REPORT_CONSUMER_V7_HASH_MISMATCH",
        )

    def test_every_context_hash_remains_bound(self) -> None:
        for key in (
            "expected_precommit_gate_v7_hash",
            "expected_report_consumer_v6_hash",
            "expected_omnibus_gate_v1_hash",
            "expected_declaration_hash",
            "expected_report_hash",
            "expected_replay_hash",
            "expected_registration_hash",
            "expected_calibration_observations_hash",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self._build(**{key: "0" * 64})["source_state"],
                    "INVALID",
                )

    def test_source_block_is_monotone_and_not_declared(self) -> None:
        context = self._block_context()
        result = self._build(**context)
        self.assertEqual(result["source_state"], "BLOCKED")
        self.assertEqual(result["preregistration_state"], "UNKNOWN")
        self.assertEqual(result["evaluation_status"], "NOT_EVALUATED")
        self.assertFalse(result["facts"]["long_horizon_protocol_pinned"])
        self.assertTrue(self._verify(result, **context))

    def test_resealed_consumer_tamper_is_invalid(self) -> None:
        consumer = deepcopy(self.consumer)
        consumer.pop("verification_hash")
        consumer["verification_reason"] = "RESEALED_DRIFT"
        consumer = seal_strict_canonical_document(consumer, "verification_hash")
        result = self._build(
            report_consumer_v7=consumer,
            expected_report_consumer_v7_hash=consumer["verification_hash"],
        )
        self.assertEqual(result["source_state"], "INVALID")

    def test_resealed_declaration_tamper_is_invalid(self) -> None:
        declaration = deepcopy(self.case._values()["precommit_declaration"])
        declaration.pop("declaration_hash")
        declaration["future_evaluation_id"] = "EVAL-RESEALED-DRIFT"
        declaration = seal_strict_canonical_document(
            declaration,
            "declaration_hash",
        )
        result = self._build(
            precommit_declaration=declaration,
            expected_declaration_hash=declaration["declaration_hash"],
        )
        self.assertEqual(result["source_state"], "INVALID")

    def test_complete_context_is_bound(self) -> None:
        alternate = self._block_context()
        result = self._build(
            report_consumer_v7=alternate["report_consumer_v7"],
            expected_report_consumer_v7_hash=alternate[
                "expected_report_consumer_v7_hash"
            ],
        )
        self.assertEqual(result["source_state"], "INVALID")

    def test_timing_grammar_is_strict(self) -> None:
        for key, value in (
            ("preregistered_at_utc", "2026-08-22T00:00:00+00:00"),
            ("preregistered_at_utc", "2026-08-22"),
            ("evaluation_not_before_date", "2026-10-01T00:00:00Z"),
            ("evaluation_not_before_date", "2026-10-1"),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(
                    self._build(**{key: value})["source_state"],
                    "INVALID",
                )

    def test_timing_order_is_strict(self) -> None:
        for declared_at, not_before in (
            ("2025-01-01T00:00:00Z", "2026-10-01"),
            ("2026-10-01T00:00:00Z", "2026-10-01"),
            ("2026-11-01T00:00:00Z", "2026-10-01"),
        ):
            with self.subTest(declared_at=declared_at, not_before=not_before):
                result = self._build(
                    preregistered_at_utc=declared_at,
                    evaluation_not_before_date=not_before,
                )
                self.assertEqual(result["source_state"], "INVALID")

    def test_future_id_is_deterministic_and_source_derived(self) -> None:
        result = self._build()
        source_hash = result["source_precommit_declaration_hash"]
        self.assertEqual(
            result["future_evaluation_id"],
            f"LH12-{source_hash[:20].upper()}",
        )
        self.assertEqual(
            result["source_future_evaluation_id"],
            self.case._values()["precommit_declaration"]["future_evaluation_id"],
        )

    def test_external_anchor_is_bound_but_unverified(self) -> None:
        result = self._build()
        self.assertEqual(
            result["source_external_time_anchor_reference_hash"],
            self.case._values()["precommit_declaration"][
                "external_time_anchor_reference_hash"
            ],
        )
        self.assertFalse(result["facts"]["external_time_anchor_verified"])
        self.assertIn("EXTERNAL_TIME_ANCHOR_UNVERIFIED", result["blockers"])

    def test_projection_contains_no_observations_or_results(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        for private_key in (
            '"rows"',
            '"returns"',
            '"beta_by_identity"',
            '"observed_tail_score"',
            '"result"',
        ):
            self.assertNotIn(private_key, serialized)
        self.assertFalse(self._build()["facts"]["observations_collected"])
        self.assertFalse(self._build()["facts"]["result_available"])

    def test_authority_is_permanently_locked(self) -> None:
        result = self._build()
        for key, value in result["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)
        self.assertFalse(result["facts"]["evaluation_activated"])
        self.assertFalse(result["facts"]["residual_order_independence_proven"])

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("pathlib.Path.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._build()
            second = self._build()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_verifier_rejects_resealed_preregistration_tamper(self) -> None:
        result = self._build()
        tampered = deepcopy(result)
        tampered.pop("preregistration_hash")
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(
            tampered,
            "preregistration_hash",
        )
        self.assertFalse(self._verify(tampered))

    def test_schema_fingerprint_and_status_are_exact(self) -> None:
        result = self._build()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(result["preregistration_state"], "DECLARED_NOT_EVALUATED")
        self.assertEqual(result["evaluation_status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
