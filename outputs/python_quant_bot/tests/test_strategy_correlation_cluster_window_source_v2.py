from __future__ import annotations

import copy
from itertools import combinations
import math
import unittest

from exchange_terminal.services import strategy_correlation_cluster_gate as legacy
from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class StrategyCorrelationClusterWindowSourceV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.clusters = [
            {"cluster_id": "tech", "members": ["A", "B"]},
            {"cluster_id": "rates", "members": ["C"]},
        ]
        self.preregistration = (
            subject.build_correlation_cluster_window_source_preregistration_v2(
                window_id="short",
                lookback_observations=20,
                clusters=self.clusters,
            )
        )
        self.expected_hash = self.preregistration["preregistration_v2_hash"]
        self.correlations = {
            ("A", "B"): 0.90,
            ("A", "C"): 0.10,
            ("B", "C"): 0.10,
        }

    def matrix(self, correlations=None, *, overlaps=20):
        return subject.build_correlation_cluster_window_matrix_v2(
            self.preregistration,
            self.correlations if correlations is None else correlations,
            overlap_observations=overlaps,
        )

    @staticmethod
    def cells(statuses=None):
        statuses = statuses or {"A": "PASS", "B": "PASS", "C": "PASS"}
        return [
            {
                "strategy_id": "trend",
                "variant_id": "fixed-v2",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": status,
            }
            for symbol, status in statuses.items()
        ]

    def evaluate(self, *, matrix=None, cells=None):
        return subject.evaluate_correlation_cluster_window_independent_ticket_gate_v2(
            self.preregistration,
            self.matrix() if matrix is None else matrix,
            self.cells() if cells is None else cells,
            expected_preregistration_v2_hash=self.expected_hash,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )

    def test_legacy_v1_cannot_bind_short_window_but_v2_binds_it_exactly(self):
        legacy_preregistration = legacy.build_correlation_cluster_preregistration(
            self.clusters
        )
        legacy_correlations = {
            pair: self.correlations[pair]
            for pair in combinations(legacy_preregistration["symbols"], 2)
        }
        legacy_matrix = legacy.build_correlation_matrix_contract(
            legacy_preregistration["symbols"],
            legacy_correlations,
            overlap_observations=20,
        )
        matrix = self.matrix()
        self.assertEqual(legacy_matrix["lookback_observations"], 60)
        self.assertEqual(matrix["lookback_observations"], 20)
        self.assertEqual(matrix["minimum_pair_overlap"], 14)

    def test_correlated_symbols_count_as_one_effective_ticket(self):
        gate = self.evaluate()
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["raw_passing_symbol_ticket_count"], 3)
        self.assertEqual(gate["effective_independent_ticket_count"], 2)
        self.assertEqual(gate["discounted_correlated_ticket_count"], 1)
        self.assertEqual(gate["required_independent_cluster_votes"], 2)
        self.assertFalse(gate["facts"]["correlated_symbols_counted_as_independent"])
        self.assertFalse(gate["authority"]["current_admission_allowed"])

    def test_only_correlated_cluster_passes_and_gate_blocks(self):
        gate = self.evaluate(
            cells=self.cells({"A": "PASS", "B": "PASS", "C": "BLOCK"})
        )
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "CLUSTER_VOTE")
        self.assertEqual(gate["raw_passing_symbol_ticket_count"], 2)
        self.assertEqual(gate["effective_independent_ticket_count"], 1)

    def test_cross_cluster_absolute_threshold_conflict_blocks_topology(self):
        for correlation in (0.75, -0.90):
            with self.subTest(correlation=correlation):
                values = dict(self.correlations)
                values[("A", "C")] = correlation
                gate = self.evaluate(matrix=self.matrix(values))
                self.assertEqual(gate["status"], "BLOCK")
                self.assertEqual(gate["first_blocking_tier"], "TOPOLOGY")
                self.assertIn(
                    "CROSS_CLUSTER_THRESHOLD_CONFLICT",
                    {row["reason"] for row in gate["topology_conflicts"]},
                )

    def test_internal_complete_link_gap_blocks_topology(self):
        values = dict(self.correlations)
        values[("A", "B")] = 0.74
        gate = self.evaluate(matrix=self.matrix(values))
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "TOPOLOGY")
        self.assertEqual(
            gate["topology_conflicts"][0]["reason"],
            "INTERNAL_PAIR_BELOW_COMPLETE_LINK_THRESHOLD",
        )

    def test_overlap_floor_blocks_and_overlap_above_lookback_is_rejected(self):
        gate = self.evaluate(matrix=self.matrix(overlaps=13))
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "COVERAGE")
        with self.assertRaisesRegex(
            subject.CorrelationWindowSourceContractError,
            "within the preregistered lookback",
        ):
            self.matrix(overlaps=21)

    def test_pair_coverage_duplicate_and_nonfinite_values_fail_closed(self):
        missing = dict(self.correlations)
        missing.pop(("B", "C"))
        duplicate = dict(self.correlations)
        duplicate[("B", "A")] = 0.90
        nonfinite = dict(self.correlations)
        nonfinite[("A", "B")] = math.nan
        for values in (missing, duplicate, nonfinite):
            with self.subTest(values=values):
                with self.assertRaises(subject.CorrelationWindowSourceContractError):
                    self.matrix(values)

    def test_expected_preregistration_hash_and_resealed_drift_are_rejected(self):
        valid = subject.verify_correlation_cluster_window_source_preregistration_v2(
            self.preregistration,
            expected_preregistration_v2_hash=self.expected_hash,
        )
        wrong_pin = subject.verify_correlation_cluster_window_source_preregistration_v2(
            self.preregistration,
            expected_preregistration_v2_hash="0" * 64,
        )
        tampered = copy.deepcopy(self.preregistration)
        tampered.pop("preregistration_v2_hash")
        tampered["minimum_pair_overlap"] = 1
        tampered = seal_strict_canonical_document(tampered, "preregistration_v2_hash")
        resealed = subject.verify_correlation_cluster_window_source_preregistration_v2(
            tampered,
            expected_preregistration_v2_hash=tampered["preregistration_v2_hash"],
        )
        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(wrong_pin["status"], "BLOCK")
        self.assertEqual(resealed["status"], "BLOCK")

    def test_exact_gate_verifier_rejects_resealed_promotion_and_authority(self):
        gate = self.evaluate()
        valid = subject.verify_correlation_cluster_window_independent_ticket_gate_v2(
            gate,
            self.preregistration,
            self.matrix(),
            self.cells(),
            expected_preregistration_v2_hash=self.expected_hash,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )
        variants = []
        for mutate in (
            lambda item: item.__setitem__("effective_independent_ticket_count", 99),
            lambda item: item["authority"].__setitem__("paper_authorized", True),
        ):
            changed = copy.deepcopy(gate)
            changed.pop("gate_v2_hash")
            mutate(changed)
            variants.append(seal_strict_canonical_document(changed, "gate_v2_hash"))
        self.assertEqual(valid["status"], "PASS")
        for changed in variants:
            with self.subTest(changed=changed["gate_v2_hash"]):
                receipt = subject.verify_correlation_cluster_window_independent_ticket_gate_v2(
                    changed,
                    self.preregistration,
                    self.matrix(),
                    self.cells(),
                    expected_preregistration_v2_hash=self.expected_hash,
                    strategy_id="trend",
                    variant_id="fixed-v2",
                    lane="RAW_EXCESS",
                )
                self.assertEqual(receipt["status"], "BLOCK")

    def test_unhashable_pseudo_statuses_fail_closed_at_source_tier(self):
        for pseudo_status in ({}, []):
            with self.subTest(pseudo_status=type(pseudo_status).__name__):
                cells = self.cells()
                cells[0]["gate_status"] = pseudo_status
                gate = self.evaluate(cells=cells)
                self.assertEqual(gate["status"], "UNKNOWN")
                self.assertEqual(gate["first_blocking_tier"], "SOURCE")
                self.assertEqual(
                    gate["decision"],
                    "BLOCK_WINDOW_SOURCE_UNVERIFIED",
                )

    def test_unknown_sources_and_input_mutation_fail_closed(self):
        preregistration_before = copy.deepcopy(self.preregistration)
        correlations_before = copy.deepcopy(self.correlations)
        gate = subject.evaluate_correlation_cluster_window_independent_ticket_gate_v2(
            None,
            None,
            None,
            expected_preregistration_v2_hash=None,
            strategy_id="trend",
            variant_id="fixed-v2",
            lane="RAW_EXCESS",
        )
        self.matrix()
        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(gate["decision"], "BLOCK_WINDOW_SOURCE_UNVERIFIED")
        self.assertTrue(all(value is False for key, value in gate["authority"].items() if key != "descriptive_only"))
        self.assertEqual(self.preregistration, preregistration_before)
        self.assertEqual(self.correlations, correlations_before)


if __name__ == "__main__":
    unittest.main()
