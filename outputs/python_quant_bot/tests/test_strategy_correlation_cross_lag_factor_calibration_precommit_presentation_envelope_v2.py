from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2 import (
    ENVELOPE_SCHEMA,
    PRESENTATION_STATUS,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2,
    verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)
from tests import test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5 as consumer_fixtures


class StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case = consumer_fixtures.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV5Tests(
            methodName="test_positive_source_is_verified_local_binding"
        )
        case.setUp()
        self.case = case
        self.consumer = case._consume()

    def _values(self):
        values = self.case._values()
        values["report_consumer"] = self.consumer
        return values

    def _build(self, **overrides):
        values = self._values()
        for key in tuple(values):
            if key in overrides:
                values[key] = overrides.pop(key)
        expected = self.case._expected(values)
        expected["expected_report_consumer_hash"] = (
            ""
            if values["report_consumer"] is None
            else values["report_consumer"].get("verification_hash")
        )
        for key in tuple(expected):
            if key in overrides:
                expected[key] = overrides.pop(key)
        return build_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2(
            values["report_consumer"],
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
        expected = self.case._expected(values)
        expected["expected_report_consumer_hash"] = values["report_consumer"][
            "verification_hash"
        ]
        return verify_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2(
            document,
            values["report_consumer"],
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

    def _block_values(self):
        context = self.case.case._multi_lag_block_context()
        source = self.case.case._evaluate(**context)
        context["source_report"] = context.pop("report")
        consumer = self.case._consume(precommit_gate_v5=source, **context)
        return {"report_consumer": consumer, "precommit_gate_v5": source, **context}

    def test_positive_report_maps_to_local_binding_four_axis(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["display_state"], "LOCAL_BINDING")
        self.assertEqual(
            [
                envelope["source_axis"]["label"],
                envelope["gap_axis"]["label"],
                envelope["maturity_axis"]["label"],
                envelope["permission_axis"]["label"],
            ],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(self._verify(envelope))

    def test_verified_block_maps_to_evidence_block_not_permission(self) -> None:
        values = self._block_values()
        envelope = self._build(**values)
        self.assertEqual(envelope["display_state"], "EVIDENCE_BLOCK")
        self.assertEqual(envelope["maturity_axis"]["state"], "BLOCKED_BY_EVIDENCE")
        self.assertEqual(envelope["permission_axis"]["state"], "LOCKED")

    def test_missing_consumer_is_unknown(self) -> None:
        envelope = self._build(report_consumer=None)
        self.assertEqual(envelope["source_state"], "MISSING")
        self.assertEqual(envelope["display_state"], "UNKNOWN")

    def test_unsupported_consumer_is_distinct(self) -> None:
        source = {"schema_version": "v0", "static_fingerprint": "v0"}
        envelope = self._build(
            report_consumer=source, expected_report_consumer_hash="a" * 64
        )
        self.assertEqual(envelope["source_state"], "UNSUPPORTED")

    def test_expected_consumer_hash_is_bound(self) -> None:
        envelope = self._build(expected_report_consumer_hash="0" * 64)
        self.assertEqual(envelope["source_state"], "INVALID")

    def test_resealed_consumer_tamper_is_invalid(self) -> None:
        source = deepcopy(self.consumer)
        source["verification_state"] = "VERIFIED_BLOCK"
        source = seal_strict_canonical_document(source, "verification_hash")
        self.assertEqual(
            self._build(report_consumer=source)["source_state"], "INVALID"
        )

    def test_complete_context_is_bound(self) -> None:
        observations = self.case.case.case.case.h1_case.fixture._observations(count=39)
        self.assertEqual(
            self._build(observations=observations)["source_state"], "INVALID"
        )

    def test_phase_comb_exposes_coverage_not_per_lag_results(self) -> None:
        envelope = self._build()
        self.assertEqual(
            envelope["phase_comb"]["teeth"],
            [
                {"lag": 1, "coverage": "PREREGISTERED", "result_exposed": False},
                {"lag": 2, "coverage": "PREREGISTERED", "result_exposed": False},
            ],
        )
        self.assertEqual(envelope["phase_comb"]["ceiling"], "0.8")
        self.assertFalse(envelope["phase_comb"]["private_ledger_exposed"])

    def test_envelope_is_aggregate_only(self) -> None:
        envelope = self._build()
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)

        collect(envelope)
        self.assertTrue(
            {"rows", "returns", "factor_return", "beta_by_identity", "folds", "result"}.isdisjoint(keys)
        )
        self.assertTrue(envelope["facts"]["aggregate_only"])

    def test_gap_remains_open_and_no_independence_is_proven(self) -> None:
        envelope = self._build()
        self.assertEqual(envelope["gap_axis"]["state"], "OPEN")
        self.assertTrue(envelope["gap_axis"]["arbitrary_lag_independence_unresolved"])
        self.assertFalse(envelope["facts"]["residual_order_independence_proven"])

    def test_permission_and_mounting_are_permanently_locked(self) -> None:
        for envelope in (self._build(), self._build(report_consumer=None)):
            permission = envelope["permission_axis"]
            authority = envelope["authority"]
            self.assertEqual(permission["state"], "LOCKED")
            self.assertFalse(permission["paper_authorized"])
            self.assertFalse(permission["live_order_allowed"])
            self.assertFalse(authority["presentation_mount_allowed"])
            self.assertFalse(strict_research_authority_invalid(authority))

    def test_copy_contract_contains_no_ready_or_profit_claim(self) -> None:
        rendered = str(self._build()).upper()
        self.assertNotIn("READY", rendered)
        self.assertNotIn("PROFITABLE", rendered)

    def test_resealed_envelope_tamper_is_rejected(self) -> None:
        envelope = self._build()
        tampered = deepcopy(envelope)
        tampered["display_state"] = "READY"
        tampered = seal_strict_canonical_document(tampered, "presentation_hash")
        self.assertFalse(self._verify(tampered))

    def test_determinism_and_denied_external_state(self) -> None:
        denied = AssertionError("external state denied")
        with (
            patch("builtins.open", side_effect=denied),
            patch("time.time", side_effect=denied),
            patch("os.urandom", side_effect=denied),
            patch("random.random", side_effect=denied),
        ):
            first = self._build()
            second = self._build()
        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_schema_fingerprint_and_status_are_exact(self) -> None:
        self.assertEqual(
            ENVELOPE_SCHEMA,
            "strategy-correlation-cross-lag-factor-calibration-precommit-presentation-envelope-v2",
        )
        self.assertEqual(
            STATIC_FINGERPRINT,
            "20260904-cross-lag-factor-calibration-precommit-presentation-envelope-2",
        )
        self.assertEqual(PRESENTATION_STATUS, "UNMOUNTED_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
