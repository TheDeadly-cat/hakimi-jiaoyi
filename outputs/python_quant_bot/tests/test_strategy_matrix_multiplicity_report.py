from __future__ import annotations

from copy import deepcopy
import unittest

import run_internal_strategy_matrix as legacy_runner

from exchange_terminal.services.strategy_matrix_multiplicity_report import (
    build_strategy_matrix_multiplicity_report,
    verify_strategy_matrix_multiplicity_report,
)


class StrategyMatrixMultiplicityReportTest(unittest.TestCase):
    def test_legacy_matrix_runner_explicitly_rejects_protocol_v5(self) -> None:
        protocol = {
            "schema_version": (
                legacy_runner.STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION
            ),
        }
        self.assertEqual(
            legacy_runner._legacy_matrix_runner_protocol_ownership_blockers(
                protocol
            ),
            ["strategy_matrix_legacy_runner_protocol_v5_not_owned"],
        )
        self.assertEqual(
            legacy_runner._legacy_matrix_runner_protocol_ownership_blockers({
                "schema_version": "strategy-matrix-protocol-v2",
            }),
            [],
        )
        with self.assertRaisesRegex(
            ValueError,
            "strategy_matrix_legacy_runner_protocol_v5_not_owned",
        ):
            legacy_runner.build_formal_strategy_matrix_report(
                {},
                protocol=protocol,
                claim={},
                completion={},
            )

    def test_legacy_schema7_cannot_become_schema8(self) -> None:
        report = build_strategy_matrix_multiplicity_report({
            "schema_version": 7,
            "status": "PASS",
            "paper_authorized": False,
            "live_order_allowed": False,
        })

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(
            report["next_evidence_required"],
            "VALID_SCHEMA16_RESEARCH_REPORT",
        )
        verification = verify_strategy_matrix_multiplicity_report(report)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "matrix_multiplicity_report_chain_blocked",
            verification["blockers"],
        )
        self.assertFalse(verification["current_writer_activation_allowed"])

    def test_forged_schema16_shape_fails_closed(self) -> None:
        report = build_strategy_matrix_multiplicity_report({
            "schema_version": 16,
            "status": "PASS",
            "batch_run_hash": "1" * 64,
            "correlation_multiplicity_evidence": {
                "status": "PASS",
                "decision_status": "PASS",
            },
            "paper_authorized": False,
            "live_order_allowed": False,
        })

        self.assertEqual(report["status"], "BLOCK")
        self.assertFalse(report["current_admission_allowed"])
        self.assertFalse(report["parameter_selection_allowed"])
        self.assertFalse(report["performance_claim_allowed"])

    def test_envelope_tamper_is_not_replayable(self) -> None:
        report = build_strategy_matrix_multiplicity_report({})
        tampered = deepcopy(report)
        tampered["next_evidence_required"] = "IGNORE_GATE"

        verification = verify_strategy_matrix_multiplicity_report(tampered)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "matrix_multiplicity_report_hash_invalid",
            verification["blockers"],
        )
        self.assertIn(
            "matrix_multiplicity_report_replay_mismatch",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
