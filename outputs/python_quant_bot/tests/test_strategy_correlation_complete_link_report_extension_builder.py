from copy import deepcopy
import unittest

from tests import test_strategy_correlation_research_evidence as source_fixtures
from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    verify_strategy_correlation_complete_link_report_extension,
)
from exchange_terminal.services.strategy_correlation_complete_link_report_extension_builder import (
    build_strategy_correlation_complete_link_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


class StrategyCorrelationCompleteLinkReportExtensionBuilderTests(
    unittest.TestCase
):
    def setUp(self):
        self.source = source_fixtures.StrategyCorrelationResearchEvidenceTests(
            "test_full_research_selection_rebuilds_positive_evidence_without_verifier_mock"
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)

    def _evidence(self, *, passed=True):
        return self.source._build(
            self.source._cells(),
            self.source._rankings(passed=passed),
        )

    def _build(self, evidence):
        return build_strategy_correlation_complete_link_report_extension(
            evidence,
            source_protocol=self.source.chain["protocol"],
        )

    def test_verified_pass_builds_deterministic_self_verified_extension(self):
        evidence = self._evidence()
        evidence_before = deepcopy(evidence)
        first = self._build(evidence)
        second = self._build(evidence)
        verification = verify_strategy_correlation_complete_link_report_extension(
            first,
            expected_base_report_hash=evidence["evidence_hash"],
        )
        self.assertTrue(strict_json_contract_equal(first, second))
        self.assertTrue(strict_json_contract_equal(evidence, evidence_before))
        self.assertEqual(first["base_report_hash"], evidence["evidence_hash"])
        self.assertEqual(first["decision"], "PASS")
        self.assertEqual(first["entries"][0]["gate_v2"]["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertFalse(first["writer_available"])
        self.assertFalse(first["current_admission_allowed"])
        self.assertFalse(first["permissions"]["paper_authorized"])
        self.assertFalse(first["permissions"]["live_order_allowed"])

    def test_verified_negative_evidence_builds_descriptive_block(self):
        evidence = self._evidence(passed=False)
        extension = self._build(evidence)
        verification = verify_strategy_correlation_complete_link_report_extension(
            extension,
            expected_base_report_hash=evidence["evidence_hash"],
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["decision_status"], "BLOCK")
        self.assertEqual(extension["decision"], "BLOCK")
        self.assertEqual(extension["entries"][0]["gate_v2"]["status"], "BLOCK")
        self.assertEqual(len(extension["decision_blockers"]), 1)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")

    def test_invalid_source_evidence_or_protocol_never_builds_extension(self):
        evidence = self._evidence()
        bad_hash = deepcopy(evidence)
        bad_hash["evidence_hash"] = "0" * 64
        bad_protocol = deepcopy(self.source.chain["protocol"])
        bad_protocol["schema_version"] = "drifted"
        cases = (
            (None, self.source.chain["protocol"]),
            (evidence, None),
            (bad_hash, self.source.chain["protocol"]),
            (evidence, bad_protocol),
        )
        for source_evidence, source_protocol in cases:
            with self.subTest(
                evidence_type=type(source_evidence).__name__,
                protocol_type=type(source_protocol).__name__,
            ):
                with self.assertRaises(ValueError):
                    build_strategy_correlation_complete_link_report_extension(
                        source_evidence,
                        source_protocol=source_protocol,
                    )

    def test_resealed_output_alias_or_authority_escalation_is_rejected(self):
        evidence = self._evidence()
        extension = self._build(evidence)
        alias = deepcopy(extension)
        alias["target_report_schema_version"] = 17.0
        alias = seal_strict_canonical_document(alias, "extension_hash")
        escalated = deepcopy(extension)
        escalated["permissions"]["live_order_allowed"] = True
        escalated = seal_strict_canonical_document(escalated, "extension_hash")
        for document in (alias, escalated):
            verification = verify_strategy_correlation_complete_link_report_extension(
                document,
                expected_base_report_hash=evidence["evidence_hash"],
            )
            self.assertEqual(verification["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
