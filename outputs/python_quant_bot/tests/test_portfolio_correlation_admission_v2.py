from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.portfolio_admission import (
    build_research_universe_contract,
)
from exchange_terminal.services.portfolio_correlation_admission_v1 import (
    build_portfolio_correlation_admission_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_v2 import (
    COMMON_UNIVERSE_POLICY,
    SCHEMA_VERSION,
    build_portfolio_correlation_admission_v2,
    verify_portfolio_correlation_admission_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from tests.test_portfolio_correlation_admission_v1 import (
    FlippingMapping,
    PortfolioCorrelationAdmissionV1Tests,
)


class PortfolioCorrelationAdmissionV2Tests(unittest.TestCase):
    def _evidence(
        self,
        *,
        correlation: float = 0.10,
        shared_stratum: bool = False,
    ) -> dict:
        case = PortfolioCorrelationAdmissionV1Tests(methodName="runTest")
        return case._evidence(
            correlation=correlation,
            shared_stratum=shared_stratum,
        )

    def _replace_universe(
        self,
        evidence: dict,
        symbols: list[str],
        *,
        selection_basis: str,
    ) -> dict:
        changed = copy.deepcopy(evidence)
        changed["report_document"]["universe_contract"] = (
            build_research_universe_contract(
                benchmark_symbol="SPY",
                tradable_symbols=symbols,
                declared_at="2026-08-01T00:00:00+00:00",
                selection_basis=selection_basis,
            )
        )
        return changed

    def _build(self, evidence: dict) -> dict:
        return build_portfolio_correlation_admission_v2(**evidence)

    def _verify(self, document: dict, evidence: dict) -> dict:
        return verify_portfolio_correlation_admission_v2(
            document,
            **evidence,
        )

    def test_reordered_exact_common_universe_passes_before_v1(self):
        evidence = self._replace_universe(
            self._evidence(),
            ["BBB", "AAA"],
            selection_basis="STATIC_SYNTHETIC_REORDERED_FIXTURE",
        )
        candidate = self._build(evidence)

        self.assertEqual(candidate["schema_version"], SCHEMA_VERSION)
        self.assertEqual(candidate["status"], "PASS")
        self.assertEqual(candidate["common_universe_status"], "PASS")
        self.assertEqual(candidate["v1_admission_status"], "PASS")
        self.assertTrue(candidate["checks"]["common_universe_exact"])
        self.assertEqual(self._verify(candidate, evidence)["status"], "PASS")

    def test_cross_universe_splice_passes_v1_but_blocks_v2_before_v1(self):
        evidence = self._replace_universe(
            self._evidence(),
            ["CCC", "DDD"],
            selection_basis="STATIC_SYNTHETIC_CROSS_UNIVERSE_SPLICE",
        )
        legacy = build_portfolio_correlation_admission_v1(**evidence)
        candidate = self._build(evidence)

        self.assertEqual(legacy["status"], "PASS")
        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "COMMON_UNIVERSE")
        self.assertEqual(candidate["common_universe_status"], "BLOCK")
        self.assertEqual(candidate["v1_admission_status"], "NOT_EVALUATED")
        self.assertIsNone(candidate["checks"]["v1_admission_exact"])
        self.assertEqual(
            candidate["evidence_hashes"]["v1_correlation_admission_hash"],
            "",
        )
        self.assertEqual(self._verify(candidate, evidence)["status"], "PASS")

    def test_subset_and_superset_splices_both_block(self):
        for symbols in (["AAA"], ["AAA", "BBB", "CCC"]):
            with self.subTest(symbols=symbols):
                evidence = self._replace_universe(
                    self._evidence(),
                    symbols,
                    selection_basis="STATIC_SYNTHETIC_CARDINALITY_SPLICE",
                )
                candidate = self._build(evidence)
                self.assertEqual(candidate["status"], "BLOCK")
                self.assertEqual(
                    candidate["first_blocking_tier"],
                    "COMMON_UNIVERSE",
                )
                self.assertEqual(
                    candidate["v1_admission_status"],
                    "NOT_EVALUATED",
                )

    def test_high_correlation_common_universe_delegates_to_v1_block(self):
        evidence = self._evidence(correlation=0.95)
        candidate = self._build(evidence)

        self.assertEqual(candidate["common_universe_status"], "PASS")
        self.assertEqual(candidate["v1_admission_status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "V1_ADMISSION")
        self.assertEqual(candidate["v1_first_blocking_tier"], "COMPLETE_LINK")
        self.assertEqual(
            candidate["blockers"],
            ["portfolio_correlation_admission_v1_blocked"],
        )
        self.assertEqual(self._verify(candidate, evidence)["status"], "PASS")

    def test_missing_universe_blocks_before_preregistration_and_v1(self):
        evidence = self._evidence()
        evidence["report_document"].pop("universe_contract")
        candidate = self._build(evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "REPORT_UNIVERSE")
        self.assertFalse(candidate["checks"]["report_universe_contract_exact"])
        self.assertIsNone(
            candidate["checks"]["correlation_preregistration_exact"]
        )
        self.assertEqual(candidate["v1_admission_status"], "NOT_EVALUATED")

    def test_duplicate_report_symbols_are_not_normalized_into_a_pass(self):
        evidence = self._evidence()
        universe = evidence["report_document"]["universe_contract"]
        universe["tradable_symbols"] = ["AAA", "AAA", "BBB"]
        universe.pop("contract_hash")
        universe["contract_hash"] = strict_canonical_hash(universe)
        candidate = self._build(evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "REPORT_UNIVERSE")
        self.assertFalse(candidate["checks"]["report_universe_contract_exact"])

    def test_non_native_mapping_fails_at_single_snapshot_boundary(self):
        evidence = self._evidence()
        evidence["report_document"] = FlippingMapping(
            evidence["report_document"]
        )
        candidate = self._build(evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "INPUT_SNAPSHOT")
        self.assertFalse(candidate["checks"]["input_snapshot_exact"])
        self.assertEqual(candidate["blockers"], ["evidence_snapshot_failed"])

    def test_authority_promotion_remains_blocked(self):
        evidence = self._evidence()
        evidence["report_document"]["paper_authorized"] = True
        candidate = self._build(evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertFalse(
            candidate["checks"]["evidence_has_no_execution_authority"]
        )
        self.assertFalse(candidate["permissions"]["paper_authorized"])
        self.assertFalse(candidate["permissions"]["live_order_allowed"])

    def test_resealed_candidate_promotion_fails_exact_verification(self):
        evidence = self._evidence()
        candidate = self._build(evidence)
        promoted = copy.deepcopy(candidate)
        promoted["permissions"]["paper_authorized"] = True
        promoted.pop("correlation_admission_v2_hash")
        promoted["correlation_admission_v2_hash"] = strict_canonical_hash(
            promoted
        )

        verification = self._verify(promoted, evidence)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["exact_rebuild"])

    def test_identity_cross_splice_still_blocks_inside_v1(self):
        evidence = self._evidence()
        evidence["strategy_id"] = "strategy-spliced"
        candidate = self._build(evidence)

        self.assertEqual(candidate["common_universe_status"], "PASS")
        self.assertEqual(candidate["v1_admission_status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "V1_ADMISSION")

    def test_candidate_binds_hashes_without_raw_symbol_or_report_content(self):
        evidence = self._evidence()
        candidate = self._build(evidence)

        self.assertEqual(candidate["common_universe_policy"], COMMON_UNIVERSE_POLICY)
        self.assertFalse(candidate["raw_report_embedded"])
        self.assertFalse(candidate["raw_correlation_evidence_embedded"])
        self.assertFalse(candidate["raw_symbol_lists_embedded"])
        self.assertNotIn("AAA", repr(candidate))
        for value in candidate["evidence_hashes"].values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self):
        evidence = self._evidence()
        before = copy.deepcopy(evidence)
        first = self._build(evidence)
        second = self._build(evidence)

        self.assertEqual(first, second)
        self.assertEqual(evidence, before)
        self.assertEqual(self._verify(first, evidence)["status"], "PASS")

    def test_block_candidate_can_verify_integrity_without_promotion(self):
        evidence = self._replace_universe(
            self._evidence(),
            ["CCC", "DDD"],
            selection_basis="STATIC_SYNTHETIC_VERIFIED_BLOCK",
        )
        candidate = self._build(evidence)
        verification = self._verify(candidate, evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["candidate_status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
