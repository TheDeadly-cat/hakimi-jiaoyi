from copy import deepcopy
import json
import re
import unittest

from tests import test_strategy_correlation_cluster_stability as fixtures

from exchange_terminal.services.strategy_correlation_cluster_stability_projection import (
    build_strategy_correlation_cluster_stability_public_summary,
    verify_strategy_correlation_cluster_stability_public_summary,
)


class StrategyCorrelationClusterStabilityProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StrategyCorrelationClusterStabilityTests(
            methodName="runTest"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def _values(self, rho=0.98, **kwargs):
        return self.fixture._fixture(rho=rho, **kwargs)

    def _summary(self, values, **overrides):
        uncertainty, preregistration, matrix, cells, complete_link, stability = values
        arguments = {
            "source_uncertainty_audit": uncertainty,
            "complete_link_gate": complete_link,
            "preregistration": preregistration,
            "correlation_matrix": matrix,
            "selection_cells": cells,
            "strategy_id": "S",
            "variant_id": "V",
            "lane": "RAW_EXCESS",
        }
        arguments.update(overrides)
        return build_strategy_correlation_cluster_stability_public_summary(
            stability,
            **arguments,
        )

    def _verify(self, values, document):
        uncertainty, preregistration, matrix, cells, complete_link, stability = values
        return verify_strategy_correlation_cluster_stability_public_summary(
            document,
            stability_gate=stability,
            source_uncertainty_audit=uncertainty,
            complete_link_gate=complete_link,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

    def test_valid_pass_is_observed_but_consumer_only(self):
        values = self._values()
        summary = self._summary(values)

        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["stability_decision"], "PASS")
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_GATE_PASS")
        self.assertEqual(summary["maturity"]["writer"], "NOT_IMPLEMENTED")
        self.assertFalse(summary["permission"]["current_admission_allowed"])

    def test_valid_block_remains_observed_block_evidence(self):
        values = self._values(rho=0.80)
        summary = self._summary(values)
        verification = self._verify(values, summary)

        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["status"], "STABILITY_EVIDENCE_BLOCKED")
        self.assertEqual(summary["gap"]["stability_decision"], "BLOCK")
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_GATE_BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["stability_decision"], "BLOCK")

    def test_mismatched_external_identity_projects_unknown(self):
        values = self._values()
        summary = self._summary(values, strategy_id="DIFFERENT")

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")
        self.assertEqual(summary["maturity"]["status"], "UNKNOWN")
        self.assertEqual(summary["maturity"]["current"], "NOT_ACTIVATED")

    def test_invalid_gate_projects_unknown_without_throwing(self):
        values = list(self._values())
        values[-1] = {}

        summary = self._summary(tuple(values))

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertFalse(summary["permission"]["paper_authorized"])

    def test_tampered_summary_cannot_upgrade_writer_or_current(self):
        values = self._values()
        summary = self._summary(values)
        summary["maturity"]["writer"] = "AVAILABLE"
        summary["gap"]["current_activation_status"] = "ACTIVATED"

        verification = self._verify(values, summary)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["current_admission_allowed"])

    def test_type_alias_and_authority_escalation_are_rejected(self):
        values = self._values()
        summary = self._summary(values)
        alias = deepcopy(summary)
        alias["permission"]["descriptive_only"] = 1
        escalated = deepcopy(summary)
        escalated["permission"]["live_order_allowed"] = True

        alias_verification = self._verify(values, alias)
        escalated_verification = self._verify(values, escalated)

        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", escalated_verification["blockers"])

    def test_public_summary_redacts_identifiers_hashes_and_statistics(self):
        summary = self._summary(self._values())
        serialized = json.dumps(summary, sort_keys=True)

        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        for forbidden in (
            '"strategy_id":',
            '"variant_id":',
            "RAW_EXCESS",
            "cluster-ab",
            "pair_results",
            "correlation_matrix",
            "adjusted_absolute_interval_lower",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
