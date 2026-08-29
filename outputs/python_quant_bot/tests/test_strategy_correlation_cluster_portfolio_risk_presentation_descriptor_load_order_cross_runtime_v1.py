from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v3 as receipt_test_support


class PortfolioRiskPresentationDescriptorLoadOrderCrossRuntimeV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.root = pathlib.Path(__file__).resolve().parents[1]
        self.receipt_case = (
            receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV3Tests(
                "test_python_pass_projection_produces_exact_local_node_receipt"
            )
        )
        self.receipt_case.setUp()
        self.addCleanup(self.receipt_case.doCleanups)

    def _node(self, projection: dict, swap_order: bool = False) -> dict:
        script = r"""
const fs = require("node:fs");
const consumer = require("./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js");
const review = require("./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_descriptor_load_order_review_candidate_v1.js");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const descriptor = consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(payload.projection);
const stylesheet = fs.readFileSync(
  "./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_card_v5.css",
  "utf8"
);
const javascriptOrder = review.EXPECTED_JAVASCRIPT_LOAD_ORDER.slice();
if (payload.swap_order) {
  [javascriptOrder[1], javascriptOrder[2]] = [javascriptOrder[2], javascriptOrder[1]];
}
const document = review.buildPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
  payload.projection,
  descriptor,
  stylesheet,
  {...review.EXPECTED_ASSET_MANIFEST},
  javascriptOrder,
  review.EXPECTED_STYLESHEET_LOAD_ORDER.slice()
);
const verification = review.verifyPortfolioRiskDescriptorLoadOrderStaticReviewCandidateV1(
  document,
  payload.projection,
  descriptor,
  stylesheet,
  {...review.EXPECTED_ASSET_MANIFEST},
  javascriptOrder,
  review.EXPECTED_STYLESHEET_LOAD_ORDER.slice()
);
process.stdout.write(JSON.stringify({descriptor,document,verification}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(
                {
                    "projection": projection,
                    "swap_order": swap_order,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_python_pass_projection_has_static_review_pass_only(self) -> None:
        result = self._node(self.receipt_case._projection("PASS"))
        self.assertEqual(result["document"]["status"], "PASS")
        self.assertEqual(result["verification"]["status"], "PASS")
        self.assertEqual(result["descriptor"]["mount"]["mode"], "UNMOUNTED")
        self.assertFalse(
            result["document"]["facts"]["browser_visual_review_performed"]
        )
        self.assertFalse(result["document"]["facts"]["ui_mounted"])
        self.assertFalse(
            result["document"]["authority"]["presentation_mount_allowed"]
        )

    def test_python_block_projection_remains_valid_static_review(self) -> None:
        result = self._node(self.receipt_case._projection("BLOCK"))
        self.assertEqual(result["document"]["status"], "PASS")
        self.assertEqual(
            result["descriptor"]["presentation"]["view_model"]["status_label"],
            "LOCAL GATE BLOCK",
        )
        self.assertFalse(result["document"]["authority"]["paper_authorized"])

    def test_swapped_card_consumer_order_blocks_review(self) -> None:
        result = self._node(
            self.receipt_case._projection("PASS"),
            swap_order=True,
        )
        self.assertEqual(result["document"]["status"], "BLOCK")
        self.assertIn(
            "javascript_dependency_load_order_exact",
            result["document"]["blockers"],
        )
        self.assertEqual(result["verification"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
