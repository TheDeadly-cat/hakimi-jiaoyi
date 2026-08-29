from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3
    as evidence_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
    as registration_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v3 as receipt_test_support


class PortfolioRiskPresentationConsumerExecutionEvidenceV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.receipt_case = (
            receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV3Tests(
                "test_python_pass_projection_produces_exact_local_node_receipt"
            )
        )
        self.receipt_case.setUp()
        self.addCleanup(self.receipt_case.doCleanups)

    def _registration(self) -> dict:
        return registration_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            registration_v4.expected_presentation_consumer_implementation_sha256_v4()
        )

    def _binding(self, registration: dict) -> dict:
        return {
            "schema_version": registration["schema_version"],
            "static_fingerprint": registration["static_fingerprint"],
            "implementation_sha256": (
                receipt_test_support.REGISTRATION_V4_IMPLEMENTATION_SHA256
            ),
            "registration_hash": registration["registration_hash"],
        }

    def _bundle(self, adapter_status: str = "PASS") -> tuple[dict, dict, dict]:
        projection = self.receipt_case._projection(adapter_status)
        registration = self._registration()
        node_result = self.receipt_case._node(
            projection,
            self._binding(registration),
        )
        return node_result["receipt"], projection, registration

    def _build(
        self,
        receipt: dict,
        projection: dict,
        registration: dict,
    ) -> dict:
        return evidence_v3.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
            receipt,
            projection,
            registration,
        )

    def test_public_versions_and_receipt_implementation_pin_are_exact(self) -> None:
        self.assertTrue(evidence_v3.SCHEMA_VERSION.endswith("evidence-v3"))
        self.assertEqual(
            evidence_v3.RECEIPT_V3_SCHEMA_VERSION,
            "portfolio-risk-joint-evidence-consumer-execution-receipt-v3",
        )
        self.assertEqual(
            evidence_v3.RECEIPT_V3_IMPLEMENTATION_SHA256,
            "9a90650656f63cd8026fcee224ed4e3d690ced6a7d8bd2970772c653e55c2acb",
        )
        self.assertEqual(
            evidence_v3.STAGE_ORDER,
            ("SOURCE", "GAP", "MATURITY", "PERMISSION"),
        )

    def test_local_pass_receipt_builds_cross_bound_python_evidence(self) -> None:
        receipt, projection, registration = self._bundle("PASS")
        evidence = self._build(receipt, projection, registration)
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["verification"]["local_joint_gate_status"],
            "PASS",
        )
        self.assertTrue(
            evidence["verification"]["local_joint_gate_passed"]
        )
        self.assertEqual(
            evidence["source"]["receipt_v3_hash"],
            receipt["receipt_hash"],
        )
        self.assertEqual(
            evidence["source"]["projection_v5_hash"],
            projection["projection_hash"],
        )
        self.assertEqual(
            evidence["source"]["registration_v4_hash"],
            registration["registration_hash"],
        )

    def test_local_block_receipt_remains_block_inside_pass_evidence(self) -> None:
        receipt, projection, registration = self._bundle("BLOCK")
        evidence = self._build(receipt, projection, registration)
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["verification"]["local_joint_gate_status"],
            "BLOCK",
        )
        self.assertFalse(
            evidence["verification"]["local_joint_gate_passed"]
        )
        self.assertFalse(evidence["authority"]["paper_authorized"])

    def test_resealed_receipt_authority_promotion_blocks_evidence(self) -> None:
        receipt, projection, registration = self._bundle()
        tampered = copy.deepcopy(receipt)
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "receipt_hash")
        evidence = self._build(tampered, projection, registration)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("receipt_v3_authority_locked", evidence["blockers"])
        self.assertFalse(evidence["authority"]["paper_authorized"])

    def test_projection_substitution_breaks_receipt_hash_edge(self) -> None:
        receipt, _, registration = self._bundle("PASS")
        alternate_projection = self.receipt_case._projection("BLOCK")
        evidence = self._build(
            receipt,
            alternate_projection,
            registration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v3_to_projection_v5_hash_bound",
            evidence["blockers"],
        )

    def test_registration_hash_substitution_breaks_receipt_edge(self) -> None:
        receipt, projection, registration = self._bundle()
        tampered = copy.deepcopy(receipt)
        tampered["source"]["registration_hash"] = "f" * 64
        tampered = seal_strict_canonical_document(tampered, "receipt_hash")
        evidence = self._build(tampered, projection, registration)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v3_to_registration_v4_hash_bound",
            evidence["blockers"],
        )

    def test_dependency_pin_substitution_blocks_evidence(self) -> None:
        receipt, projection, registration = self._bundle()
        tampered = copy.deepcopy(receipt)
        tampered["source"]["consumer_implementation_sha256"] = "f" * 64
        tampered = seal_strict_canonical_document(tampered, "receipt_hash")
        evidence = self._build(tampered, projection, registration)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v3_dependency_pins_exact",
            evidence["blockers"],
        )

    def test_local_gate_state_substitution_blocks_cross_binding(self) -> None:
        receipt, projection, registration = self._bundle("PASS")
        tampered = copy.deepcopy(receipt)
        tampered["verification"]["local_joint_gate_status"] = "BLOCK"
        tampered["verification"]["local_joint_gate_passed"] = False
        tampered["verification"]["view_status_label"] = "LOCAL GATE BLOCK"
        tampered = seal_strict_canonical_document(tampered, "receipt_hash")
        evidence = self._build(tampered, projection, registration)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "local_joint_gate_state_cross_bound",
            evidence["blockers"],
        )

    def test_resealed_legacy_receipt_schema_is_not_promoted(self) -> None:
        receipt, projection, registration = self._bundle()
        legacy = copy.deepcopy(receipt)
        legacy["schema_version"] = (
            "portfolio-risk-weighted-diversification-"
            "fixture-execution-receipt-v2"
        )
        legacy = seal_strict_canonical_document(legacy, "receipt_hash")
        evidence = self._build(legacy, projection, registration)
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v3_schema_and_fingerprint_exact",
            evidence["blockers"],
        )
        self.assertEqual(
            evidence["source"]["receipt_v3_schema_version"],
            "UNKNOWN",
        )

    def test_public_verifier_accepts_exact_evidence_and_rejects_tamper(
        self,
    ) -> None:
        receipt, projection, registration = self._bundle()
        evidence = self._build(receipt, projection, registration)
        verification = evidence_v3.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
            evidence,
            receipt,
            projection,
            registration,
        )
        self.assertEqual(verification["status"], "PASS")
        tampered = copy.deepcopy(evidence)
        tampered["authority"]["presentation_mount_allowed"] = True
        tampered = seal_strict_canonical_document(tampered, "evidence_hash")
        verification = evidence_v3.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3(
            tampered,
            receipt,
            projection,
            registration,
        )
        self.assertEqual(verification["status"], "BLOCK")

    def test_evidence_calibrates_process_identity_and_embeds_no_documents(
        self,
    ) -> None:
        receipt, projection, registration = self._bundle()
        evidence = self._build(receipt, projection, registration)
        self.assertEqual(evidence["status"], "PASS")
        self.assertTrue(
            evidence["facts"]["local_python_contract_execution_observed"]
        )
        self.assertTrue(
            evidence["facts"]["receipt_reports_local_node_execution"]
        )
        self.assertFalse(
            evidence["facts"]["independent_node_process_witnessed"]
        )
        self.assertFalse(
            evidence["facts"]["node_process_identity_authenticated"]
        )
        self.assertFalse(evidence["facts"]["receipt_signature_verified"])
        self.assertFalse(evidence["facts"]["projection_semantics_replayed"])
        self.assertFalse(evidence["facts"]["receipt_document_embedded"])
        self.assertFalse(evidence["facts"]["projection_document_embedded"])
        self.assertFalse(
            evidence["facts"]["registration_document_embedded"]
        )
        self.assertFalse(evidence["facts"]["profitability_proven"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(evidence), promotion)


if __name__ == "__main__":
    unittest.main()
