from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math
import unittest

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
    evaluate_correlation_cluster_gate,
    verify_correlation_cluster_preregistration,
    verify_correlation_matrix_contract,
)


class StrategyCorrelationClusterGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "mega_cap_tech", "members": ["AAPL", "MSFT", "NVDA"]},
            {"cluster_id": "rates", "members": ["TLT"]},
            {"cluster_id": "gold", "members": ["GLD"]},
        ])

    def matrix(self, overrides: dict[tuple[str, str], float] | None = None):
        symbols = self.preregistration["symbols"]
        correlations = {pair: 0.10 for pair in combinations(symbols, 2)}
        correlations.update({
            tuple(sorted(("AAPL", "MSFT"))): 0.92,
            tuple(sorted(("AAPL", "NVDA"))): 0.88,
            tuple(sorted(("MSFT", "NVDA"))): 0.90,
        })
        correlations.update(overrides or {})
        return build_correlation_matrix_contract(symbols, correlations)

    def cells(self, statuses: dict[str, str], lane: str = "RAW_EXCESS"):
        return [
            {
                "strategy_id": "trend",
                "variant_id": "fixed-v1",
                "symbol": symbol,
                "lane": lane,
                "gate_status": status,
            }
            for symbol, status in statuses.items()
        ]

    def evaluate(self, cells, matrix=None, preregistration=None, lane="RAW_EXCESS"):
        return evaluate_correlation_cluster_gate(
            preregistration or self.preregistration,
            matrix or self.matrix(),
            cells,
            strategy_id="trend",
            variant_id="fixed-v1",
            lane=lane,
        )

    def test_legacy_symbol_majority_passes_but_cluster_vote_blocks(self) -> None:
        statuses = {
            "AAPL": "PASS", "MSFT": "PASS", "NVDA": "PASS",
            "TLT": "BLOCK", "GLD": "BLOCK",
        }
        positive_symbol_votes = sum(status == "PASS" for status in statuses.values())
        self.assertGreaterEqual(positive_symbol_votes, math.ceil(len(statuses) * 0.60))
        result = self.evaluate(self.cells(statuses))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["first_blocking_tier"], "CLUSTER_VOTE")
        self.assertEqual(result["passing_cluster_count"], 1)
        self.assertEqual(result["required_cluster_votes"], 2)

    def test_two_of_three_clusters_pass_but_activation_remains_false(self) -> None:
        result = self.evaluate(self.cells({
            "AAPL": "PASS", "MSFT": "PASS", "NVDA": "PASS",
            "TLT": "PASS", "GLD": "BLOCK",
        }))
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertTrue(result["requires_new_report_schema"])
        self.assertEqual(result["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_risk_adjusted_lane_requires_every_cluster_member(self) -> None:
        result = self.evaluate(self.cells({
            "AAPL": "PASS", "MSFT": "PASS", "NVDA": "BLOCK",
            "TLT": "PASS", "GLD": "BLOCK",
        }, lane="RISK_ADJUSTED"), lane="RISK_ADJUSTED")
        self.assertEqual(result["status"], "BLOCK")
        tech = next(item for item in result["cluster_results"] if item["cluster_id"] == "mega_cap_tech")
        self.assertEqual(tech["status"], "BLOCK")

    def test_absolute_threshold_is_inclusive_for_positive_and_negative_pairs(self) -> None:
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "a", "members": ["AAPL"]},
            {"cluster_id": "b", "members": ["MSFT"]},
            {"cluster_id": "c", "members": ["GLD"]},
        ])
        base = {pair: 0.10 for pair in combinations(preregistration["symbols"], 2)}
        cells = self.cells({"AAPL": "PASS", "MSFT": "PASS", "GLD": "PASS"})
        for correlation in (0.75, -0.90):
            with self.subTest(correlation=correlation):
                values = dict(base)
                values[("AAPL", "MSFT")] = correlation
                matrix = build_correlation_matrix_contract(preregistration["symbols"], values)
                result = self.evaluate(cells, matrix=matrix, preregistration=preregistration)
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["first_blocking_tier"], "TOPOLOGY")

    def test_preregistration_is_a_canonical_exact_partition(self) -> None:
        reversed_contract = build_correlation_cluster_preregistration([
            {"cluster_id": "rates", "members": ["TLT"]},
            {"cluster_id": "mega_cap_tech", "members": ["NVDA", "MSFT", "AAPL"]},
            {"cluster_id": "gold", "members": ["GLD"]},
        ])
        self.assertEqual(reversed_contract, self.preregistration)
        with self.assertRaisesRegex(ValueError, "exactly one cluster"):
            build_correlation_cluster_preregistration([
                {"cluster_id": "one", "members": ["AAPL"]},
                {"cluster_id": "two", "members": ["AAPL"]},
            ])

    def test_tampered_preregistration_contract_blocks(self) -> None:
        tampered = deepcopy(self.preregistration)
        tampered["absolute_pearson_threshold"] = 0.80
        check = verify_correlation_cluster_preregistration(tampered)
        self.assertEqual(check["status"], "BLOCK")
        self.assertIn("preregistration_contract_invalid", check["blockers"])

    def test_matrix_hash_and_authority_claims_block(self) -> None:
        tampered = deepcopy(self.matrix())
        tampered["pairs"][0]["pearson_correlation"] = 0.74
        check = verify_correlation_matrix_contract(
            tampered,
            expected_symbols=self.preregistration["symbols"],
        )
        self.assertEqual(check["status"], "BLOCK")
        authority = deepcopy(self.matrix())
        authority["live_order_allowed"] = True
        check = verify_correlation_matrix_contract(
            authority,
            expected_symbols=self.preregistration["symbols"],
        )
        self.assertIn("execution_authority_invalid", check["blockers"])

    def test_missing_duplicate_and_pseudo_status_cells_block(self) -> None:
        valid = self.cells({
            "AAPL": "PASS", "MSFT": "PASS", "NVDA": "PASS",
            "TLT": "PASS", "GLD": "PASS",
        })
        variants = [
            valid[:-1],
            [*valid, deepcopy(valid[0])],
            [{**cell, "gate_status": True} if index == 0 else cell for index, cell in enumerate(valid)],
            [{**cell, "gate_status": {}} if index == 0 else cell for index, cell in enumerate(valid)],
            [{**cell, "lane": []} if index == 0 else cell for index, cell in enumerate(valid)],
        ]
        for cells in variants:
            with self.subTest(cells=len(cells)):
                result = self.evaluate(cells)
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["first_blocking_tier"], "COVERAGE")
        invalid_expected = verify_correlation_matrix_contract(
            self.matrix(),
            expected_symbols=[{}],
        )
        self.assertEqual(invalid_expected["status"], "BLOCK")
        invalid_lane = evaluate_correlation_cluster_gate(
            self.preregistration,
            self.matrix(),
            valid,
            strategy_id="trend",
            variant_id="fixed-v1",
            lane={},
        )
        self.assertEqual(invalid_lane["status"], "BLOCK")
        self.assertEqual(invalid_lane["first_blocking_tier"], "PREREGISTRATION")


if __name__ == "__main__":
    unittest.main()
