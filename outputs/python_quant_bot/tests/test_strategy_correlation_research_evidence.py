from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_multiplicity_report import (
    verify_strategy_correlation_multiplicity_report_evidence,
)
from exchange_terminal.services.strategy_correlation_research_evidence import (
    build_strategy_correlation_research_multiplicity_evidence,
)
from tests import test_strategy_correlation_multiplicity_report as multiplicity_report_tests


class StrategyCorrelationResearchEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        source_case = multiplicity_report_tests.StrategyCorrelationMultiplicityReportTests(
            "test_positive_chain_is_valid_but_still_requires_schema8_envelope"
        )
        source_case.setUp()
        self.addCleanup(source_case.doCleanups)
        self.chain = source_case._chain(gate_pass=True)
        registration = self.chain["protocol"][
            "correlation_multiplicity_protocol_registration"
        ]
        self.evaluation = registration["source_protocol_registration"]["evaluations"][0]
        self.symbols = registration["source_protocol_registration"]["preregistration"][
            "symbols"
        ]

    def _cells(self) -> list[dict]:
        return [
            {
                "symbol": symbol,
                "strategy_id": self.evaluation["strategy_id"],
                "variant_id": self.evaluation["variant_id"],
                "dataset_status": "PASS",
                "train_ok": True,
                "validation_ok": True,
                "train_return_pct": 3.0,
                "validation_return_pct": 4.0,
                "validation_excess_return_pct": 2.0,
                "validation_trade_count": 3,
                "validation_max_drawdown_pct": 4.0,
                "validation_sharpe": 1.5,
                "validation_drawdown_improvement_pct": 5.0,
                "validation_sharpe_excess": 0.5,
                "validation_risk_efficiency_excess": 0.25,
                "fold_stability_status": "PASS",
                "cost_sensitivity_status": "PASS",
                "lookahead_status": "PASS",
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            for symbol in self.symbols
        ]

    def _rankings(self, *, passed: bool = True) -> list[dict]:
        return [{
            "strategy_id": self.evaluation["strategy_id"],
            "variant_id": self.evaluation["variant_id"],
            "status": "PASS" if passed else "BLOCK",
            "eligible_for_test": passed,
            "selection_lane": self.evaluation["lane"] if passed else "NONE",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }]

    def _build(self, cells: list[dict], rankings: list[dict]) -> dict:
        return build_strategy_correlation_research_multiplicity_evidence(
            self.chain["protocol"],
            self.chain["gate"]["matrix_replay"],
            cells,
            rankings,
        )

    def test_full_research_selection_rebuilds_positive_evidence_without_verifier_mock(self) -> None:
        evidence = self._build(self._cells(), self._rankings())
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            evidence,
            protocol=self.chain["protocol"],
        )
        self.assertEqual(verification["status"], "PASS", verification["blockers"])
        self.assertEqual(evidence["decision_status"], "PASS")
        self.assertFalse(evidence["permissions"]["paper_authorized"])
        self.assertFalse(evidence["permissions"]["live_order_allowed"])

    def test_blocked_global_ranking_stays_valid_but_blocks_decision(self) -> None:
        evidence = self._build(self._cells(), self._rankings(passed=False))
        verification = verify_strategy_correlation_multiplicity_report_evidence(
            evidence,
            protocol=self.chain["protocol"],
        )
        self.assertEqual(verification["status"], "PASS", verification["blockers"])
        self.assertEqual(evidence["decision_status"], "BLOCK")

    def test_missing_or_duplicate_selection_identity_is_rejected(self) -> None:
        cells = self._cells()
        with self.assertRaisesRegex(ValueError, "selection_cell_coverage_invalid"):
            self._build(cells[:-1], self._rankings())
        with self.assertRaisesRegex(ValueError, "selection_cell_identity_invalid"):
            self._build([*cells, deepcopy(cells[0])], self._rankings())

    def test_authority_alias_is_rejected_before_projection(self) -> None:
        cells = self._cells()
        cells[0]["paper_authorized"] = True
        with self.assertRaisesRegex(ValueError, "selection_authority_invalid"):
            self._build(cells, self._rankings())

    def test_matrix_replay_must_match_registered_alignment_source(self) -> None:
        matrix = deepcopy(self.chain["gate"]["matrix_replay"])
        matrix["completed_price_input"]["selection_alignment_input_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "matrix_replay_invalid"):
            build_strategy_correlation_research_multiplicity_evidence(
                self.chain["protocol"],
                matrix,
                self._cells(),
                self._rankings(),
            )


if __name__ == "__main__":
    unittest.main()
