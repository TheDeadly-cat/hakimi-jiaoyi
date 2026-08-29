from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
    evaluate_correlation_cluster_gate_v2,
    verify_correlation_cluster_complete_link_audit,
    verify_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
    evaluate_correlation_cluster_gate,
)


class StrategyCorrelationClusterCompleteLinkTests(unittest.TestCase):
    @staticmethod
    def _preregistration() -> dict:
        return build_correlation_cluster_preregistration(
            [
                {"cluster_id": "CHAIN", "members": ["A", "B", "C"]},
                {"cluster_id": "D", "members": ["D"]},
            ]
        )

    @staticmethod
    def _matrix(*, ac: float, ac_overlap: int = 60) -> dict:
        correlations = {
            ("A", "B"): 0.80,
            ("A", "C"): ac,
            ("A", "D"): 0.10,
            ("B", "C"): 0.80,
            ("B", "D"): 0.10,
            ("C", "D"): 0.10,
        }
        overlaps = {pair: 60 for pair in correlations}
        overlaps[("A", "C")] = ac_overlap
        return build_correlation_matrix_contract(
            ["A", "B", "C", "D"],
            correlations,
            overlap_observations=overlaps,
        )

    @staticmethod
    def _cells() -> list[dict]:
        return [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": "PASS",
            }
            for symbol in ["A", "B", "C", "D"]
        ]

    def test_chain_linkage_passes_v1_but_blocks_v2(self) -> None:
        preregistration = self._preregistration()
        matrix = self._matrix(ac=0.20)
        cells = self._cells()
        legacy = evaluate_correlation_cluster_gate(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

        self.assertEqual(legacy["status"], "PASS")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(gate["first_blocking_tier"], "CLUSTER_COMPLETE_LINK")
        conflicts = gate["complete_link_audit"]["internal_pair_conflicts"]
        self.assertEqual(
            [(item["left_symbol"], item["right_symbol"]) for item in conflicts],
            [("A", "C")],
        )
        self.assertFalse(gate["current_admission_allowed"])
        self.assertFalse(gate["current_writer_activation_allowed"])
        self.assertFalse(gate["permissions"]["paper_authorized"])
        self.assertFalse(gate["permissions"]["live_order_allowed"])

    def test_complete_link_and_exact_threshold_pass_v2_without_authority(self) -> None:
        preregistration = self._preregistration()
        matrix = self._matrix(ac=0.75)
        cells = self._cells()
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )

        self.assertEqual(gate["status"], "PASS")
        self.assertIsNone(gate["first_blocking_tier"])
        self.assertFalse(gate["current_admission_allowed"])
        self.assertFalse(gate["current_writer_activation_allowed"])
        self.assertEqual(
            verify_correlation_cluster_gate_v2(
                gate,
                preregistration=preregistration,
                correlation_matrix=matrix,
                selection_cells=cells,
                strategy_id="S",
                variant_id="V",
                lane="RAW_EXCESS",
            )["status"],
            "PASS",
        )

    def test_internal_pair_overlap_is_fail_closed(self) -> None:
        preregistration = self._preregistration()
        matrix = self._matrix(ac=0.90, ac_overlap=39)
        audit = build_correlation_cluster_complete_link_audit(
            preregistration,
            matrix,
        )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn(
            "cluster_internal_pair_overlap_insufficient",
            audit["blockers"],
        )
        self.assertIn(
            "internal_pair_overlap_insufficient",
            audit["internal_pair_conflicts"][0]["blockers"],
        )
        self.assertEqual(
            verify_correlation_cluster_complete_link_audit(
                audit,
                preregistration=preregistration,
                correlation_matrix=matrix,
            )["status"],
            "PASS",
        )

    def test_resealed_nested_tamper_fails_exact_rebuild(self) -> None:
        preregistration = self._preregistration()
        matrix = self._matrix(ac=0.20)
        cells = self._cells()
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        tampered = copy.deepcopy(gate)
        tampered["complete_link_audit"]["internal_pair_conflicts"] = []

        verification = verify_correlation_cluster_gate_v2(
            tampered,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "correlation_cluster_gate_v2_contract_invalid",
            verification["blockers"],
        )

    def test_authority_alias_tamper_fails_exact_rebuild(self) -> None:
        preregistration = self._preregistration()
        matrix = self._matrix(ac=0.80)
        cells = self._cells()
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        tampered = copy.deepcopy(gate)
        tampered["paper"] = True

        verification = verify_correlation_cluster_gate_v2(
            tampered,
            preregistration=preregistration,
            correlation_matrix=matrix,
            selection_cells=cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        self.assertEqual(verification["status"], "BLOCK")
