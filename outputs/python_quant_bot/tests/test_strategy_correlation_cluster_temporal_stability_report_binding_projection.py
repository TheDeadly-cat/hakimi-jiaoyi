from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_cluster_temporal_stability_report_binding as binding_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_binding_projection import (
    build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary,
    verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary,
)


class StrategyCorrelationClusterTemporalStabilityReportBindingProjectionTests(
    unittest.TestCase
):
    def setUp(self):
        self.binding_case = (
            binding_fixtures.StrategyCorrelationClusterTemporalStabilityReportBindingTests(
                methodName="test_valid_pass_report_is_candidate_bound_but_not_formal"
            )
        )
        self.binding_case.setUp()

    def tearDown(self):
        self.binding_case.tearDown()

    def _inputs(self, *, low_effective_sample=False, **overrides):
        arguments = self.binding_case._arguments(
            low_effective_sample=low_effective_sample,
            **overrides,
        )
        assessment = self.binding_case._assessment(**deepcopy(arguments))
        return {"binding_assessment": assessment, **arguments}

    def test_not_supplied_is_distinct_from_unknown(self):
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary()
        self.assertEqual(summary["source"]["status"], "NOT_SUPPLIED")
        self.assertEqual(summary["source"]["candidate_binding_status"], "NOT_SUPPLIED")
        self.assertEqual(summary["gap"]["status"], "CANDIDATE_BINDING_NOT_SUPPLIED")

    def test_valid_pass_report_projects_candidate_bound_not_formal(self):
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **self._inputs()
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["candidate_binding_status"], "CANDIDATE_BOUND")
        self.assertEqual(summary["source"]["report21_decision"], "PASS")
        self.assertEqual(summary["maturity"]["status"], "CANDIDATE_BOUND_NOT_FORMAL")
        self.assertEqual(
            summary["gap"]["formal_registration_report_binding"],
            "NOT_ESTABLISHED",
        )

    def test_valid_block_report_is_still_candidate_bound(self):
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **self._inputs(low_effective_sample=True)
        )
        self.assertEqual(summary["source"]["candidate_binding_status"], "CANDIDATE_BOUND")
        self.assertEqual(summary["source"]["report21_decision"], "BLOCK")
        self.assertEqual(summary["maturity"]["status"], "CANDIDATE_BOUND_NOT_FORMAL")

    def test_valid_blocked_assessment_projects_candidate_blocked(self):
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **self._inputs(expected_report_identity_set_hash="c" * 64)
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["candidate_binding_status"], "BLOCK")
        self.assertEqual(summary["gap"]["status"], "CANDIDATE_BINDING_BLOCKED")
        self.assertEqual(summary["maturity"]["status"], "CANDIDATE_BLOCKED")

    def test_invalid_supplied_assessment_projects_unknown(self):
        inputs = self._inputs()
        assessment = deepcopy(inputs["binding_assessment"])
        assessment["candidate_bound"] = False
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")
        inputs["binding_assessment"] = assessment
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **inputs
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["source"]["candidate_binding_status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "CANDIDATE_BINDING_UNKNOWN")

    def test_tampered_summary_cannot_claim_formal_or_current(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **inputs
        )
        summary["maturity"]["formal_binding"] = "ESTABLISHED"
        summary["gap"]["current_activation_status"] = "ACTIVATED"
        verification = verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            summary,
            **inputs,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["formal_registration_report_binding"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_native_alias_and_authority_escalation_are_rejected(self):
        inputs = self._inputs()
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **inputs
        )
        alias = deepcopy(summary)
        alias["permission"]["candidate_binding_activation_allowed"] = 0
        escalated = deepcopy(summary)
        escalated["permission"]["live_order_allowed"] = True
        alias_verification = verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            alias,
            **inputs,
        )
        escalated_verification = verify_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            escalated,
            **inputs,
        )
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation", escalated_verification["blockers"]
        )

    def test_public_summary_redacts_private_binding_evidence(self):
        summary = build_strategy_correlation_cluster_temporal_stability_report_binding_public_summary(
            **self._inputs()
        )
        serialized = json.dumps(summary, sort_keys=True)
        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        for forbidden in (
            '"assessment_hash":',
            '"protocol_registration_hash":',
            '"report21_extension_hash":',
            '"report_identity_set_hash":',
            '"binding_id":',
            '"facts":',
            '"blockers":',
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
