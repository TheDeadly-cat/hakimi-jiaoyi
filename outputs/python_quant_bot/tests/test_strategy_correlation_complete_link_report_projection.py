from copy import deepcopy
import json
import re
import unittest

from exchange_terminal.services.strategy_correlation_complete_link_report_projection import (
    PUBLIC_SUMMARY_SCHEMA_VERSION,
    build_strategy_correlation_complete_link_report_public_summary,
    verify_strategy_correlation_complete_link_report_public_summary,
)
from tests import test_strategy_correlation_complete_link_report_consumer as source_fixtures


class StrategyCorrelationCompleteLinkReportProjectionTests(unittest.TestCase):
    def _summary(self, correlation: float):
        source = (
            source_fixtures.StrategyCorrelationCompleteLinkReportConsumerTests
            ._candidate(correlation)
        )
        summary = build_strategy_correlation_complete_link_report_public_summary(
            source,
            expected_base_report_hash=(
                source_fixtures.StrategyCorrelationCompleteLinkReportConsumerTests
                .BASE_HASH
            ),
        )
        return source, summary

    @staticmethod
    def _verify(source, summary):
        return verify_strategy_correlation_complete_link_report_public_summary(
            summary,
            source_extension=source,
            expected_base_report_hash=(
                source_fixtures.StrategyCorrelationCompleteLinkReportConsumerTests
                .BASE_HASH
            ),
        )

    def test_verified_pass_projects_neutral_consumer_evidence(self):
        source, summary = self._summary(0.80)
        verification = self._verify(source, summary)

        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA_VERSION)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["decision"], "PASS")
        self.assertEqual(
            summary["gap"]["status"],
            "FORMAL_REGISTRY_AND_WRITER_PENDING",
        )
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_EVIDENCE_PASS")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_verified_block_remains_descriptive_block_evidence(self):
        source, summary = self._summary(0.20)
        verification = self._verify(source, summary)

        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["decision"], "BLOCK")
        self.assertEqual(summary["gap"]["status"], "COMPLETE_LINK_DECISION_BLOCK")
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_EVIDENCE_BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")

    def test_invalid_source_projects_unknown(self):
        summary = build_strategy_correlation_complete_link_report_public_summary(
            {},
            expected_base_report_hash=(
                source_fixtures.StrategyCorrelationCompleteLinkReportConsumerTests
                .BASE_HASH
            ),
        )

        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "SOURCE_INVALID")
        self.assertIsNone(summary["gap"]["decision"])
        self.assertEqual(summary["maturity"]["status"], "UNKNOWN")
        self.assertEqual(summary["maturity"]["current"], "NOT_ACTIVATED")

    def test_tamper_type_alias_and_authority_escalation_are_rejected(self):
        source, summary = self._summary(0.80)
        decision = deepcopy(summary)
        decision["gap"]["decision"] = "BLOCK"
        alias = deepcopy(summary)
        alias["source"]["target_report_schema_version"] = 17.0
        authority = deepcopy(summary)
        authority["permission"]["paper_authorized"] = True

        for label, candidate in (
            ("decision", decision),
            ("alias", alias),
            ("authority", authority),
        ):
            with self.subTest(label=label):
                verification = self._verify(source, candidate)
                self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation",
            self._verify(source, authority)["blockers"],
        )

    def test_public_summary_redacts_source_hashes_identities_and_raw_gates(self):
        _, summary = self._summary(0.80)
        serialized = json.dumps(summary, sort_keys=True)
        forbidden_fields = {
            "extension_hash",
            "base_report_hash",
            "strategy_id",
            "variant_id",
            "lane",
            "preregistration",
            "correlation_matrix",
            "selection_cells",
            "gate_v2",
            "complete_link_audit",
            "decision_blockers",
        }

        def field_names(value):
            names = set()
            if isinstance(value, dict):
                names.update(value)
                for child in value.values():
                    names.update(field_names(child))
            elif isinstance(value, list):
                for child in value:
                    names.update(field_names(child))
            return names

        self.assertTrue(forbidden_fields.isdisjoint(field_names(summary)))
        self.assertIsNone(re.search(r"[0-9a-f]{64}", serialized))
        self.assertTrue(all(value is False for value in summary["redaction"].values()))


if __name__ == "__main__":
    unittest.main()
