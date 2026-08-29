from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from itertools import combinations
import unittest

from exchange_terminal.services import strategy_correlation_cluster_gate as source_contract
from exchange_terminal.services.strategy_correlation_cluster_common_support_gate_v2 import (
    MAXIMUM_COMMON_OBSERVATIONS,
    MINIMUM_COMMON_OBSERVATIONS,
    build_common_support_correlation_matrix_v2,
    evaluate_correlation_cluster_common_support_gate_v2,
    verify_common_support_correlation_matrix_v2,
    verify_correlation_cluster_common_support_gate_v2,
)


class StrategyCorrelationClusterCommonSupportGateV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbols = ["AAA", "BBB", "CCC"]
        self.preregistration = source_contract.build_correlation_cluster_preregistration([
            {"cluster_id": "alpha", "members": ["AAA"]},
            {"cluster_id": "beta", "members": ["BBB"]},
            {"cluster_id": "gamma", "members": ["CCC"]},
        ])
        self.correlations = {
            pair: 0.10 for pair in combinations(self.symbols, 2)
        }
        self.common_index = self.index(MINIMUM_COMMON_OBSERVATIONS)

    @staticmethod
    def index(count: int, *, offset: int = 0) -> list[str]:
        start = date(2026, 1, 1) + timedelta(days=offset)
        return [(start + timedelta(days=index)).isoformat() for index in range(count)]

    def matrix(
        self,
        correlations: dict[tuple[str, str], float] | None = None,
        common_index: list[str] | None = None,
    ) -> dict[str, object]:
        return build_common_support_correlation_matrix_v2(
            self.symbols,
            correlations or self.correlations,
            common_index or self.common_index,
        )

    def cells(self, statuses: dict[str, str] | None = None) -> list[dict[str, str]]:
        values = statuses or {symbol: "PASS" for symbol in self.symbols}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "fixed-v2",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in values.items()
        ]

    def evaluate(
        self,
        *,
        matrix: dict[str, object] | None = None,
        common_index: list[str] | None = None,
        cells: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        return evaluate_correlation_cluster_common_support_gate_v2(
            self.preregistration,
            matrix or self.matrix(),
            common_index or self.common_index,
            cells or self.cells(),
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )

    def test_v1_can_pass_pair_counts_with_zero_global_common_dates(self) -> None:
        pair_support = {
            pair: set(self.index(40, offset=index * 40))
            for index, pair in enumerate(combinations(self.symbols, 2))
        }
        self.assertEqual(len(set.intersection(*pair_support.values())), 0)
        matrix = source_contract.build_correlation_matrix_contract(
            self.symbols,
            self.correlations,
            overlap_observations={pair: len(values) for pair, values in pair_support.items()},
        )
        result = source_contract.evaluate_correlation_cluster_gate(
            self.preregistration,
            matrix,
            self.cells(),
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("common_observation_index_hash", matrix)

    def test_v2_passes_only_with_one_bound_common_index(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["common_support_verified"])
        self.assertEqual(result["common_observation_count"], 40)
        self.assertEqual(result["source_gate_status"], "PASS")
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertEqual(result["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_matrix_is_deterministic_and_private(self) -> None:
        first = self.matrix()
        second = self.matrix()
        self.assertEqual(first, second)
        self.assertNotIn("overlap_observations", repr(first))
        self.assertNotIn("2026-", repr(first))
        self.assertEqual(first["common_observation_count"], 40)

    def test_index_hash_changes_when_common_dates_change(self) -> None:
        first = self.matrix(common_index=self.index(40, offset=0))
        second = self.matrix(common_index=self.index(40, offset=1))
        self.assertNotEqual(
            first["common_observation_index_hash"],
            second["common_observation_index_hash"],
        )

    def test_common_index_count_bounds_are_exact(self) -> None:
        for count in (MINIMUM_COMMON_OBSERVATIONS - 1, MAXIMUM_COMMON_OBSERVATIONS + 1):
            with self.subTest(count=count):
                with self.assertRaisesRegex(ValueError, "outside registered bounds"):
                    self.matrix(common_index=self.index(count))
        self.assertEqual(
            self.matrix(common_index=self.index(MAXIMUM_COMMON_OBSERVATIONS))[
                "common_observation_count"
            ],
            MAXIMUM_COMMON_OBSERVATIONS,
        )

    def test_common_index_requires_canonical_sorted_unique_dates(self) -> None:
        variants = [
            None,
            list(reversed(self.common_index)),
            [*self.common_index[:-1], self.common_index[-2]],
            [*self.common_index[:-1], "2026-1-01"],
            [*self.common_index[:-1], True],
        ]
        for value in variants:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    build_common_support_correlation_matrix_v2(
                        self.symbols,
                        self.correlations,
                        value,
                    )

    def test_matrix_verifier_binds_the_supplied_common_index(self) -> None:
        matrix = self.matrix()
        valid = verify_common_support_correlation_matrix_v2(
            matrix,
            expected_symbols=self.symbols,
            common_observation_index=self.common_index,
        )
        mismatch = verify_common_support_correlation_matrix_v2(
            matrix,
            expected_symbols=self.symbols,
            common_observation_index=self.index(40, offset=1),
        )
        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(mismatch["status"], "BLOCK")

    def test_gate_blocks_common_index_mismatch_before_source_gate(self) -> None:
        result = self.evaluate(common_index=self.index(40, offset=1))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["first_blocking_tier"], "COMMON_SUPPORT")
        self.assertEqual(result["source_gate_status"], "NOT_EVALUATED")

    def test_matrix_tampering_and_authority_claims_block(self) -> None:
        tampered = deepcopy(self.matrix())
        tampered["pairs"][0]["pearson_correlation"] = 0.20
        authority = deepcopy(self.matrix())
        authority["live_order_allowed"] = True
        for matrix in (tampered, authority):
            with self.subTest(keys=len(matrix)):
                check = verify_common_support_correlation_matrix_v2(
                    matrix,
                    expected_symbols=self.symbols,
                    common_observation_index=self.common_index,
                )
                self.assertEqual(check["status"], "BLOCK")

    def test_matrix_rejects_incomplete_or_nonfinite_correlations(self) -> None:
        incomplete = dict(self.correlations)
        incomplete.pop(next(iter(incomplete)))
        with self.assertRaises(ValueError):
            self.matrix(correlations=incomplete)
        nonfinite = dict(self.correlations)
        nonfinite[next(iter(nonfinite))] = float("nan")
        with self.assertRaises(ValueError):
            self.matrix(correlations=nonfinite)

    def test_source_topology_still_blocks_cross_cluster_threshold(self) -> None:
        correlations = dict(self.correlations)
        correlations[("AAA", "BBB")] = 0.75
        result = self.evaluate(matrix=self.matrix(correlations=correlations))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["first_blocking_tier"], "SOURCE_CLUSTER_GATE")
        self.assertEqual(result["source_first_blocking_tier"], "TOPOLOGY")

    def test_source_cluster_vote_still_blocks(self) -> None:
        result = self.evaluate(cells=self.cells({
            "AAA": "PASS",
            "BBB": "BLOCK",
            "CCC": "BLOCK",
        }))
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_first_blocking_tier"], "CLUSTER_VOTE")

    def test_missing_selection_cell_still_blocks(self) -> None:
        result = self.evaluate(cells=self.cells()[:-1])
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_first_blocking_tier"], "COVERAGE")

    def test_gate_verifier_accepts_exact_output(self) -> None:
        matrix = self.matrix()
        cells = self.cells()
        result = self.evaluate(matrix=matrix, cells=cells)
        self.assertTrue(verify_correlation_cluster_common_support_gate_v2(
            result,
            self.preregistration,
            matrix,
            self.common_index,
            cells,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        ))

    def test_gate_verifier_rejects_tampering(self) -> None:
        matrix = self.matrix()
        cells = self.cells()
        result = self.evaluate(matrix=matrix, cells=cells)
        result["common_observation_count"] += 1
        self.assertFalse(verify_correlation_cluster_common_support_gate_v2(
            result,
            self.preregistration,
            matrix,
            self.common_index,
            cells,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        ))

    def test_gate_output_is_deterministic(self) -> None:
        self.assertEqual(self.evaluate(), self.evaluate())


if __name__ == "__main__":
    unittest.main()
