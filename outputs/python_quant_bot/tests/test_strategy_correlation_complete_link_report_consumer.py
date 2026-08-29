from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
    evaluate_correlation_cluster_gate,
)
from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    verify_strategy_correlation_complete_link_report_extension,
)


class StrategyCorrelationCompleteLinkReportConsumerTests(unittest.TestCase):
    BASE_HASH = "a" * 64

    @staticmethod
    def _hash(value: object) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _sources(ac: float) -> tuple[dict, dict, list[dict]]:
        preregistration = build_correlation_cluster_preregistration(
            [
                {"cluster_id": "CHAIN", "members": ["A", "B", "C"]},
                {"cluster_id": "D", "members": ["D"]},
            ]
        )
        matrix = build_correlation_matrix_contract(
            ["A", "B", "C", "D"],
            {
                ("A", "B"): 0.80,
                ("A", "C"): ac,
                ("A", "D"): 0.10,
                ("B", "C"): 0.80,
                ("B", "D"): 0.10,
                ("C", "D"): 0.10,
            },
        )
        cells = [
            {
                "strategy_id": "S",
                "variant_id": "V",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": "PASS",
            }
            for symbol in ["A", "B", "C", "D"]
        ]
        return preregistration, matrix, cells

    @classmethod
    def _candidate(cls, ac: float) -> dict:
        preregistration, matrix, cells = cls._sources(ac)
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        decision = "PASS" if gate["status"] == "PASS" else "BLOCK"
        blockers = [] if decision == "PASS" else [
            "complete_link_gate_blocked:S:V:RAW_EXCESS"
        ]
        payload = {
            "schema_version": "strategy-research-complete-link-extension-v1",
            "base_report_schema_version": 16,
            "target_report_schema_version": 17,
            "target_protocol_schema_version": "strategy-matrix-protocol-v6",
            "base_report_hash": cls.BASE_HASH,
            "entries": [
                {
                    "strategy_id": "S",
                    "variant_id": "V",
                    "lane": "RAW_EXCESS",
                    "preregistration": preregistration,
                    "correlation_matrix": matrix,
                    "selection_cells": cells,
                    "gate_v2": gate,
                }
            ],
            "decision": decision,
            "decision_blockers": blockers,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        return {**payload, "extension_hash": cls._hash(payload)}

    @classmethod
    def _reseal(cls, document: dict) -> dict:
        payload = {key: value for key, value in document.items() if key != "extension_hash"}
        return {**payload, "extension_hash": cls._hash(payload)}

    def test_consumer_accepts_complete_link_pass_without_enabling_writer(self) -> None:
        candidate = self._candidate(0.80)
        verification = verify_strategy_correlation_complete_link_report_extension(
            candidate,
            expected_base_report_hash=self.BASE_HASH,
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertFalse(verification["writer_available"])
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["current_writer_activation_allowed"])
        self.assertFalse(verification["permissions"]["paper_authorized"])
        self.assertFalse(verification["permissions"]["live_order_allowed"])

    def test_consumer_preserves_valid_chain_link_block_evidence(self) -> None:
        candidate = self._candidate(0.20)
        verification = verify_strategy_correlation_complete_link_report_extension(
            candidate,
            expected_base_report_hash=self.BASE_HASH,
        )

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(
            candidate["decision_blockers"],
            ["complete_link_gate_blocked:S:V:RAW_EXCESS"],
        )

    def test_base_report_hash_mismatch_blocks_before_gate_trust(self) -> None:
        verification = verify_strategy_correlation_complete_link_report_extension(
            self._candidate(0.80),
            expected_base_report_hash="b" * 64,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "complete_link_report_base_hash_mismatch",
            verification["blockers"],
        )

    def test_resealed_v1_gate_substitution_is_rejected(self) -> None:
        candidate = self._candidate(0.20)
        entry = candidate["entries"][0]
        entry["gate_v2"] = evaluate_correlation_cluster_gate(
            entry["preregistration"],
            entry["correlation_matrix"],
            entry["selection_cells"],
            strategy_id="S",
            variant_id="V",
            lane="RAW_EXCESS",
        )
        tampered = self._reseal(candidate)

        verification = verify_strategy_correlation_complete_link_report_extension(
            tampered,
            expected_base_report_hash=self.BASE_HASH,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_resealed_nested_gate_tamper_is_rejected(self) -> None:
        candidate = self._candidate(0.20)
        tampered = copy.deepcopy(candidate)
        tampered["entries"][0]["gate_v2"]["complete_link_audit"][
            "internal_pair_conflicts"
        ] = []
        tampered = self._reseal(tampered)

        verification = verify_strategy_correlation_complete_link_report_extension(
            tampered,
            expected_base_report_hash=self.BASE_HASH,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_authority_alias_is_rejected_even_when_resealed(self) -> None:
        tampered = self._candidate(0.80)
        tampered["paper"] = True
        tampered = self._reseal(tampered)

        verification = verify_strategy_correlation_complete_link_report_extension(
            tampered,
            expected_base_report_hash=self.BASE_HASH,
        )
        self.assertEqual(verification["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
