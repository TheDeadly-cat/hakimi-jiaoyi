from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4 as registration_v4
import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_projection_v5 as projection_v5
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v5 as candidate_test_support
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


REGISTRATION_V4_IMPLEMENTATION_SHA256 = (
    "b7b0b8faf64d34796b6ae97e6594ea08a0fcd930272fa4841e4a7bd0ebecd897"
)


class PortfolioRiskPresentationConsumerExecutionReceiptV3Tests(
    unittest.TestCase
):
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
                request=request,
                adapter_context=adapter_context,
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

    def _registration_binding(self) -> dict:
        manifest = (
            registration_v4.expected_presentation_consumer_implementation_sha256_v4()
        )
        registration = (
            registration_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
                manifest
            )
        )
        verification = (
            registration_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
                registration,
                manifest,
            )
        )
        self.assertEqual(verification["status"], "PASS")
        return {
            "schema_version": registration["schema_version"],
            "static_fingerprint": registration["static_fingerprint"],
            "implementation_sha256": REGISTRATION_V4_IMPLEMENTATION_SHA256,
            "registration_hash": registration["registration_hash"],
        }

    def _node(self, projection: dict, registration_binding: dict) -> dict:
        script = r"""
const fs = require("node:fs");
const receipts = require("./exchange_terminal/static/evidence_portfolio_risk_joint_evidence_consumer_execution_receipt_v3.js");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const receipt = receipts.buildPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
  payload.projection,
  payload.registration_binding
);
const verification = receipts.verifyPortfolioRiskJointEvidenceConsumerExecutionReceiptV3(
  receipt,
  payload.projection,
  payload.registration_binding
);
process.stdout.write(JSON.stringify({ receipt, verification }));
"""
        payload = {
            "projection": projection,
            "registration_binding": registration_binding,
        }
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=self.root,
            input=json.dumps(payload, separators=(",", ":"), sort_keys=True),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_python_pass_projection_produces_exact_local_node_receipt(self) -> None:
        binding = self._registration_binding()
        result = self._node(self._projection("PASS"), binding)
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(
            receipt["verification"]["local_joint_gate_status"],
            "PASS",
        )
        self.assertTrue(receipt["verification"]["local_joint_gate_passed"])
        self.assertEqual(
            receipt["source"]["registration_hash"],
            binding["registration_hash"],
        )
        self.assertEqual(result["verification"]["status"], "PASS")

    def test_python_block_projection_is_preserved_by_pass_receipt(self) -> None:
        result = self._node(
            self._projection("BLOCK"),
            self._registration_binding(),
        )
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(
            receipt["verification"]["local_joint_gate_status"],
            "BLOCK",
        )
        self.assertFalse(receipt["verification"]["local_joint_gate_passed"])
        self.assertFalse(receipt["authority"]["paper_authorized"])
        self.assertFalse(
            receipt["authority"]["presentation_mount_allowed"]
        )

    def test_resealed_authority_promotion_is_recorded_as_block(self) -> None:
        projection = self._projection("PASS")
        projection["authority"]["paper_authorized"] = True
        projection = seal_strict_canonical_document(
            projection,
            "projection_hash",
        )
        result = self._node(projection, self._registration_binding())
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn(
            "projection_and_descriptor_authority_locked",
            receipt["blockers"],
        )
        self.assertFalse(receipt["authority"]["paper_authorized"])
        self.assertEqual(result["verification"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
