from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v5 as projection_v5
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v5 as candidate_test_support
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskPresentationConsumerCrossRuntimeV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = pathlib.Path(__file__).resolve().parents[1]
        self.case = candidate_test_support.PresentationHttpCandidateV5Tests(
            "test_valid_composition_projects_known_blocked_candidate"
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def _projection(self, adapter_status: str = "PASS") -> dict:
        if adapter_status == "PASS":
            candidate = self.case._build()
            request = copy.deepcopy(self.case.request)
            adapter_context = copy.deepcopy(self.case.adapter_context)
        else:
            adapter_document, adapter_context = self.case._adapter_bundle(
                adapter_status=adapter_status
            )
            request = copy.deepcopy(self.case.request)
            request["portfolio_risk_adapter_v5_document"] = adapter_document
            candidate = self.case._build(
                request=request, adapter_context=adapter_context
            )
        context = {
            "request_payload": request,
            "v4_verification_context": copy.deepcopy(self.case.v4_case.context),
            "adapter_v5_verification_context": adapter_context,
        }
        return projection_v5.project_strategy_correlation_cluster_portfolio_risk_projection_v5(
            candidate,
            presentation_candidate_v5_verification_context=context,
        )

    def _node(self, projection: dict) -> dict:
        script = r"""
const fs = require('node:fs');
const card = require('./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_card_v5.js');
const consumer = require('./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_consumer_fixture_v5.js');
const projection = JSON.parse(fs.readFileSync(0, 'utf8'));
const view = card.buildPortfolioRiskJointEvidenceViewModelV5(projection);
const descriptor = consumer.buildPortfolioRiskJointEvidencePresentationConsumerFixtureV5(projection);
process.stdout.write(JSON.stringify({
  seal_verified: card.verifyPortfolioRiskProjectionSealV5(projection),
  view,
  descriptor,
  descriptor_verified: consumer.verifyPortfolioRiskJointEvidencePresentationConsumerFixtureV5(descriptor, projection)
}));
"""
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(projection, separators=(",", ":"), sort_keys=True),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_python_pass_projection_builds_known_blocked_node_descriptor(self) -> None:
        result = self._node(self._projection("PASS"))
        self.assertTrue(result["seal_verified"])
        self.assertEqual(result["view"]["contract_state"], "KNOWN_BLOCKED")
        self.assertEqual(result["view"]["tone"], "bounded")
        self.assertEqual(result["descriptor"]["status"], "BLOCK")
        self.assertEqual(result["descriptor"]["mount"]["mode"], "UNMOUNTED")
        self.assertTrue(result["descriptor_verified"])

    def test_python_block_projection_remains_gap_and_unauthorized_in_node(self) -> None:
        result = self._node(self._projection("BLOCK"))
        self.assertEqual(result["view"]["tone"], "gap")
        self.assertEqual(result["view"]["status_label"], "LOCAL GATE BLOCK")
        self.assertEqual(result["view"]["stages"][3]["state"], "UNAUTHORIZED")
        self.assertFalse(result["descriptor"]["authority"]["presentation_mount_allowed"])

    def test_resealed_wrong_schema_is_not_accepted_by_node_card(self) -> None:
        projection = self._projection("PASS")
        projection["schema_version"] = (
            "strategy-correlation-cluster-portfolio-risk-projection-v4"
        )
        projection = seal_strict_canonical_document(projection, "projection_hash")
        result = self._node(projection)
        self.assertFalse(result["seal_verified"])
        self.assertEqual(result["view"]["contract_state"], "UNKNOWN")
        self.assertEqual(
            result["descriptor"]["decision"],
            "UNKNOWN_PROJECTION_V5_RENDER_DESCRIPTOR_FAIL_CLOSED",
        )


if __name__ == "__main__":
    unittest.main()
