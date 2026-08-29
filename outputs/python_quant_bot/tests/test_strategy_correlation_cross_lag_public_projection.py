from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_public_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_public_summary,
    verify_strategy_correlation_cross_lag_public_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cross_lag_protocol_binding import (
    StrategyCorrelationCrossLagProtocolBindingTests,
)


class StrategyCorrelationCrossLagPublicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = StrategyCorrelationCrossLagProtocolBindingTests()
        self.fixture.setUp()
        self.assessment = self.fixture._build()

    def _values(self):
        return {
            "binding_assessment": self.assessment,
            **self.fixture._values(),
            "expected_binding_assessment_hash": self.assessment["binding_assessment_hash"],
        }

    def _build(self, **overrides):
        values = self._values()
        values.update(overrides)
        return build_strategy_correlation_cross_lag_public_summary(
            values.pop("binding_assessment"),
            **values,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_public_summary(
            document,
            values.pop("binding_assessment"),
            **values,
        )

    def _block_context(self, seed):
        rows, evaluation, receipt = self.fixture._observed(block=True, seed=seed)
        context = {
            "aligned_observations": rows,
            "evaluation": evaluation,
            "consumer_receipt": receipt,
            "expected_evaluation_hash": evaluation["evaluation_hash"],
            "expected_consumer_receipt_hash": receipt["verification_hash"],
        }
        assessment = self.fixture._build(**context)
        context["binding_assessment"] = assessment
        context["expected_binding_assessment_hash"] = assessment["binding_assessment_hash"]
        return context

    def _assert_locked(self, summary):
        self.assertTrue(summary["authority"]["descriptive_only"])
        for key, value in summary["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)
        self.assertEqual(summary["permission_axis"], "LOCKED")

    def test_valid_pass_maps_to_four_neutral_axes(self):
        summary = self._build()
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["verification_schema_version"], PUBLIC_SUMMARY_VERIFICATION_SCHEMA)
        self.assertEqual(summary["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(summary["public_state"], "OBSERVED_PASS")
        self.assertEqual(summary["source_axis"], "VERIFIED_C2")
        self.assertEqual(summary["gap_axis"], "SEQUENCE_ORDER_UNATTESTED")
        self.assertEqual(summary["maturity_axis"], "CANDIDATE_PROTOCOL_BOUND_NOT_FORMAL")
        self.assertEqual(
            summary["blockers"],
            [
                "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
                "CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED",
            ],
        )
        self._assert_locked(summary)

    def test_valid_dependence_remains_visible_as_public_block(self):
        context = self._block_context(20260911)
        summary = self._build(**context)
        self.assertEqual(summary["public_state"], "OBSERVED_BLOCK")
        self.assertEqual(summary["gap_axis"], "CROSS_LAG_DEPENDENCE_OBSERVED")
        self.assertEqual(summary["blockers"][0], "CROSS_LAG_DEPENDENCE_DETECTED")
        self.assertGreater(summary["dependent_test_count"], 0)
        self._assert_locked(summary)

    def test_valid_pass_and_block_exactly_verify(self):
        self.assertTrue(self._verify(self._build()))
        context = self._block_context(20260912)
        summary = self._build(**context)
        self.assertTrue(self._verify(summary, **context))

    def test_missing_is_distinct_from_invalid_supplied(self):
        missing = self._build(binding_assessment=None)
        invalid = self._build(binding_assessment=[])
        self.assertEqual(missing["public_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["public_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_assessment_hash_mismatch_fails_closed(self):
        summary = self._build(expected_binding_assessment_hash="f" * 64)
        self.assertEqual(summary["public_state"], "UNKNOWN")

    def test_other_valid_evaluation_or_receipt_context_fails_closed(self):
        rows, evaluation, receipt = self.fixture._observed(block=True, seed=20260913)
        for field, value in (("evaluation", evaluation), ("consumer_receipt", receipt)):
            with self.subTest(field=field):
                summary = self._build(aligned_observations=rows, **{field: value})
                self.assertEqual(summary["public_state"], "UNKNOWN")

    def test_coherently_resealed_nondefault_assessment_tamper_fails_closed(self):
        context = self._block_context(20260914)
        assessment = copy.deepcopy(context["binding_assessment"])
        self.assertGreater(assessment["dependent_test_count"], 0)
        assessment["dependent_test_count"] = 0
        assessment.pop("binding_assessment_hash")
        assessment = seal_strict_canonical_document(assessment, "binding_assessment_hash")
        summary = self._build(
            **{
                **context,
                "binding_assessment": assessment,
                "expected_binding_assessment_hash": assessment["binding_assessment_hash"],
            }
        )
        self.assertEqual(summary["public_state"], "UNKNOWN")

    def test_resealed_state_reason_and_count_drift_fail_closed(self):
        for field, value in (
            ("assessment_state", "OBSERVED_BLOCK_CANDIDATE_PROTOCOL"),
            ("gate_reason", "DRIFTED_REASON"),
            ("lag_test_count", 999),
        ):
            with self.subTest(field=field):
                assessment = copy.deepcopy(self.assessment)
                assessment[field] = value
                assessment.pop("binding_assessment_hash")
                assessment = seal_strict_canonical_document(assessment, "binding_assessment_hash")
                summary = self._build(
                    binding_assessment=assessment,
                    expected_binding_assessment_hash=assessment["binding_assessment_hash"],
                )
                self.assertEqual(summary["public_state"], "UNKNOWN")

    def test_authority_aliases_fail_closed(self):
        for value in (0, "", "false", True):
            with self.subTest(value=value):
                assessment = copy.deepcopy(self.assessment)
                assessment["authority"]["paper_authorized"] = value
                assessment.pop("binding_assessment_hash")
                assessment = seal_strict_canonical_document(assessment, "binding_assessment_hash")
                summary = self._build(
                    binding_assessment=assessment,
                    expected_binding_assessment_hash=assessment["binding_assessment_hash"],
                )
                self.assertEqual(summary["public_state"], "UNKNOWN")

    def test_extra_untrusted_source_field_is_not_reflected(self):
        assessment = copy.deepcopy(self.assessment)
        assessment["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        assessment.pop("binding_assessment_hash")
        assessment = seal_strict_canonical_document(assessment, "binding_assessment_hash")
        summary = self._build(
            binding_assessment=assessment,
            expected_binding_assessment_hash=assessment["binding_assessment_hash"],
        )
        self.assertEqual(summary["public_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", str(summary))

    def test_c2_verifier_exception_fails_closed(self):
        with patch(
            "exchange_terminal.services.strategy_correlation_cross_lag_public_projection.verify_strategy_correlation_cross_lag_protocol_binding_assessment",
            side_effect=RuntimeError("adversarial verifier fault"),
        ):
            summary = self._build()
        self.assertEqual(summary["public_state"], "UNKNOWN")
        self._assert_locked(summary)

    def test_public_summary_is_aggregate_only(self):
        summary = self._build()
        forbidden = {
            "stratum_assignment",
            "identity_set",
            "symbols",
            "cluster_members",
            "lag_results",
            "aligned_observations",
            "returns",
            "return_series",
            "local_path",
            "url",
            "callback",
        }
        self.assertFalse(forbidden.intersection(summary))

    def test_resealed_public_state_tamper_does_not_verify(self):
        summary = self._build()
        tampered = copy.deepcopy(summary)
        tampered["public_state"] = "OBSERVED_BLOCK"
        tampered.pop("public_summary_hash")
        tampered = seal_strict_canonical_document(tampered, "public_summary_hash")
        self.assertFalse(self._verify(tampered))

    def test_resealed_permission_tamper_does_not_verify(self):
        summary = self._build()
        tampered = copy.deepcopy(summary)
        tampered["authority"]["current_admission_allowed"] = True
        tampered.pop("public_summary_hash")
        tampered = seal_strict_canonical_document(tampered, "public_summary_hash")
        self.assertFalse(self._verify(tampered))

    def test_non_mapping_summary_never_verifies(self):
        self.assertFalse(self._verify([]))

    def test_summary_contains_no_promotional_or_execution_state(self):
        summary = self._build()
        values = {value for value in summary.values() if isinstance(value, str)}
        self.assertNotIn("READY", values)
        self.assertNotIn("AUTHORIZED", values)
        self.assertNotIn("EXECUTABLE", values)


if __name__ == "__main__":
    unittest.main()
