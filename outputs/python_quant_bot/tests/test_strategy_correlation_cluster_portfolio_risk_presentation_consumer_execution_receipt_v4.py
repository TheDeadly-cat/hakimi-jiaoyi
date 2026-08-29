from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_projection_v6 as projection_test_support


class PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.case = projection_test_support.PortfolioRiskProjectionV6Tests(
            "test_exact_local_clear_projects_blocked_frontend_authority"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def _projection(
        self,
        *,
        coupled: bool = False,
        observations: list[dict[str, object]] | None = None,
    ) -> dict:
        if not coupled and observations is None:
            return copy.deepcopy(self.case.projection)
        candidate, context = self.case._bundle(
            coupled=coupled,
            observations=observations,
        )
        return self.case._project(candidate, context)

    def _node(
        self,
        projection: dict,
        preregistration_id: str = "python-to-node-receipt-v4",
    ) -> dict:
        script = r"""
const fs = require('node:fs');
const receipts = require('./exchange_terminal/static/evidence_portfolio_risk_downside_tail_consumer_execution_receipt_v4.js');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const preregistration = receipts.buildPortfolioRiskDownsideTailExecutionPreregistrationV1(payload.preregistration_id);
const receipt = receipts.buildPortfolioRiskDownsideTailConsumerExecutionReceiptV4(payload.projection, preregistration);
const verification = receipts.verifyPortfolioRiskDownsideTailConsumerExecutionReceiptV4(receipt, payload.projection, preregistration);
process.stdout.write(JSON.stringify({ preregistration, receipt, verification }));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(
                {
                    "projection": projection,
                    "preregistration_id": preregistration_id,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_python_clear_projection_produces_exact_local_receipt(self) -> None:
        result = self._node(self._projection())
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["verification"]["local_status"], "PASS")
        self.assertEqual(receipt["verification"]["view_tone"], "bounded")
        self.assertTrue(
            receipt["verification"][
                "source_tail_and_local_state_preserved"
            ]
        )
        self.assertEqual(result["verification"]["status"], "PASS")

    def test_python_tail_block_is_preserved_by_pass_receipt(self) -> None:
        result = self._node(self._projection(coupled=True))
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["verification"]["local_status"], "BLOCK")
        self.assertEqual(
            receipt["verification"]["downside_tail_gate_decision"],
            "BLOCK",
        )
        self.assertEqual(receipt["verification"]["view_tone"], "critical")
        self.assertFalse(receipt["authority"]["paper_authorized"])

    def test_python_exact_unknown_is_preserved_by_pass_receipt(self) -> None:
        result = self._node(self._projection(observations=[]))
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(
            receipt["verification"]["view_source_state"], "UNKNOWN"
        )
        self.assertEqual(receipt["verification"]["local_status"], "UNKNOWN")
        self.assertEqual(receipt["verification"]["view_tone"], "unknown")
        self.assertFalse(receipt["facts"]["formal_registration_bound"])

    def test_resealed_authority_promotion_produces_exact_block_receipt(
        self,
    ) -> None:
        projection = self._projection()
        projection["authority"]["paper_authorized"] = True
        projection = seal_strict_canonical_document(
            projection,
            "projection_hash",
        )
        result = self._node(projection)
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("card_v6_view_model_built", receipt["blockers"])
        self.assertIn(
            "projection_and_descriptor_authority_locked",
            receipt["blockers"],
        )
        self.assertEqual(result["verification"]["status"], "PASS")

    def test_dynamic_preregistration_id_is_bound_without_formal_registration(
        self,
    ) -> None:
        first = self._node(self._projection(), "python-receipt-v4-a")
        second = self._node(self._projection(), "python-receipt-v4-b")
        self.assertNotEqual(
            first["preregistration"]["preregistration_hash"],
            second["preregistration"]["preregistration_hash"],
        )
        self.assertIsNone(
            first["receipt"]["source"]["formal_registration_hash"]
        )
        self.assertFalse(
            first["receipt"]["verification"]["formal_registration_bound"]
        )


if __name__ == "__main__":
    unittest.main()
