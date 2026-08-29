from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_receipt_v4 as receipt_test_support


class PortfolioRiskPresentationConsumerExecutionEvidenceV4Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        case = receipt_test_support.PortfolioRiskPresentationConsumerExecutionReceiptV4Tests(
            "test_python_clear_projection_produces_exact_local_receipt"
        )
        case.setUp()
        cls.addClassCleanup(case.doCleanups)
        cls._bundles = {}
        for name, projection in (
            ("CLEAR", case._projection()),
            ("TAIL_BLOCK", case._projection(coupled=True)),
            ("EXACT_UNKNOWN", case._projection(observations=[])),
        ):
            node_result = case._node(projection)
            cls._bundles[name] = (
                node_result["receipt"],
                node_result["verification"],
                projection,
                node_result["preregistration"],
            )

    def _bundle(self, name: str = "CLEAR") -> tuple[dict, dict, dict, dict]:
        return copy.deepcopy(self._bundles[name])

    def _build(
        self,
        receipt: dict,
        receipt_verification: dict,
        projection: dict,
        preregistration: dict,
    ) -> dict:
        return evidence_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
            receipt,
            receipt_verification,
            projection,
            preregistration,
        )

    def test_public_versions_and_implementation_pins_are_exact(self) -> None:
        self.assertTrue(evidence_v4.SCHEMA_VERSION.endswith("evidence-v4"))
        self.assertEqual(
            evidence_v4.RECEIPT_V4_SCHEMA_VERSION,
            "portfolio-risk-downside-tail-consumer-execution-receipt-v4",
        )
        self.assertEqual(
            evidence_v4.RECEIPT_V4_IMPLEMENTATION_SHA256,
            "cfc312b5971953e0d2cfa35e691f7aba826266b66bb7a54e4dfeab5d0b3cae39",
        )
        self.assertEqual(
            evidence_v4.PROJECTION_V6_IMPLEMENTATION_SHA256,
            "ec136f1cc713f443581f835116610c0210d0fe2faeb638ee815d93709e1566d6",
        )
        self.assertEqual(
            evidence_v4.STAGE_ORDER,
            ("SOURCE", "GAP", "MATURITY", "PERMISSION"),
        )

    def test_clear_receipt_builds_cross_bound_summary_evidence(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["verification"]["execution_semantic_state"],
            "CLEAR",
        )
        self.assertEqual(evidence["verification"]["local_status"], "PASS")
        self.assertEqual(
            evidence["source"]["receipt_v4_hash"],
            receipt["receipt_hash"],
        )
        self.assertEqual(
            evidence["source"]["receipt_v4_verification_hash"],
            verification["verification_hash"],
        )
        self.assertEqual(
            evidence["source"]["projection_v6_hash"],
            projection["projection_hash"],
        )
        self.assertEqual(
            evidence["source"]["execution_preregistration_v1_hash"],
            preregistration["preregistration_hash"],
        )

    def test_tail_block_is_preserved_inside_pass_evidence(self) -> None:
        receipt, verification, projection, preregistration = self._bundle(
            "TAIL_BLOCK"
        )
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["verification"]["execution_semantic_state"],
            "TAIL_BLOCK",
        )
        self.assertEqual(evidence["verification"]["local_status"], "BLOCK")
        self.assertFalse(evidence["authority"]["paper_authorized"])

    def test_exact_unknown_is_preserved_without_becoming_failure_or_pass(self) -> None:
        receipt, verification, projection, preregistration = self._bundle(
            "EXACT_UNKNOWN"
        )
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(
            evidence["verification"]["execution_semantic_state"],
            "EXACT_UNKNOWN",
        )
        self.assertEqual(
            evidence["verification"]["local_status"],
            "UNKNOWN",
        )
        self.assertEqual(
            evidence["verification"]["downside_tail_gate_decision"],
            "UNKNOWN",
        )
        self.assertFalse(evidence["authority"]["current_admission_allowed"])

    def test_resealed_preregistration_authority_promotion_blocks(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        preregistration["authority"]["paper_authorized"] = True
        preregistration = seal_strict_canonical_document(
            preregistration,
            "preregistration_hash",
        )
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "execution_preregistration_v1_authority_locked",
            evidence["blockers"],
        )
        self.assertIn(
            "receipt_v4_to_preregistration_v1_hash_bound",
            evidence["blockers"],
        )

    def test_resealed_receipt_authority_promotion_blocks(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        receipt["authority"]["presentation_mount_allowed"] = True
        receipt = seal_strict_canonical_document(receipt, "receipt_hash")
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn("receipt_v4_authority_locked", evidence["blockers"])
        self.assertFalse(evidence["authority"]["presentation_mount_allowed"])

    def test_resealed_dependency_pin_or_extra_source_field_blocks(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        receipt["source"]["consumer_implementation_sha256"] = "f" * 64
        receipt["source"]["unregistered_extra"] = "not-accepted"
        receipt = seal_strict_canonical_document(receipt, "receipt_hash")
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v4_dependency_source_exact",
            evidence["blockers"],
        )

    def test_formal_registration_insertion_remains_blocked(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        receipt["source"]["formal_registration_schema_version"] = (
            "unregistered-formal-registration-v7"
        )
        receipt["source"]["formal_registration_hash"] = "f" * 64
        receipt = seal_strict_canonical_document(receipt, "receipt_hash")
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "formal_registration_remains_explicitly_absent",
            evidence["blockers"],
        )
        self.assertIsNone(
            evidence["source"]["formal_registration_schema_version"]
        )

    def test_projection_substitution_breaks_receipt_hash_edge(self) -> None:
        receipt, verification, _, preregistration = self._bundle("CLEAR")
        _, _, alternate_projection, _ = self._bundle("TAIL_BLOCK")
        evidence = self._build(
            receipt,
            verification,
            alternate_projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v4_to_projection_v6_hash_bound",
            evidence["blockers"],
        )

    def test_resealed_receipt_verification_hash_edge_substitution_blocks(
        self,
    ) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        verification["receipt_hash"] = "f" * 64
        verification = seal_strict_canonical_document(
            verification,
            "verification_hash",
        )
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v4_verification_hash_and_receipt_edge_exact",
            evidence["blockers"],
        )

    def test_resealed_local_state_alias_blocks_semantic_cross_binding(
        self,
    ) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        receipt["verification"]["local_status"] = "CLEAR"
        receipt = seal_strict_canonical_document(receipt, "receipt_hash")
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "clear_tail_block_or_exact_unknown_state_cross_bound",
            evidence["blockers"],
        )
        self.assertEqual(
            evidence["verification"]["execution_semantic_state"],
            "UNVERIFIED",
        )

    def test_resealed_legacy_receipt_schema_is_not_promoted(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        receipt["schema_version"] = (
            "portfolio-risk-joint-evidence-consumer-execution-receipt-v3"
        )
        receipt = seal_strict_canonical_document(receipt, "receipt_hash")
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertIn(
            "receipt_v4_schema_and_fingerprint_exact",
            evidence["blockers"],
        )
        self.assertEqual(
            evidence["source"]["receipt_v4_schema_version"],
            "UNKNOWN",
        )

    def test_public_verifier_accepts_exact_evidence_and_rejects_tamper(
        self,
    ) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
        checked = evidence_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
            evidence,
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(checked["status"], "PASS")
        self.assertEqual(checked["execution_semantic_state"], "CLEAR")
        tampered = copy.deepcopy(evidence)
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "evidence_hash")
        checked = evidence_v4.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4(
            tampered,
            receipt,
            verification,
            projection,
            preregistration,
        )
        self.assertEqual(checked["status"], "BLOCK")
        self.assertEqual(checked["execution_semantic_state"], "UNVERIFIED")

    def test_evidence_is_summary_only_and_calibrates_non_authority(self) -> None:
        receipt, verification, projection, preregistration = self._bundle()
        evidence = self._build(
            receipt,
            verification,
            projection,
            preregistration,
        )
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
            evidence["facts"]["receipt_implementation_runtime_verified"]
        )
        self.assertFalse(evidence["facts"]["receipt_document_embedded"])
        self.assertFalse(
            evidence["facts"]["receipt_verification_document_embedded"]
        )
        self.assertFalse(evidence["facts"]["projection_document_embedded"])
        self.assertFalse(
            evidence["facts"]["execution_preregistration_document_embedded"]
        )
        self.assertFalse(evidence["facts"]["formal_registration_bound"])
        self.assertFalse(evidence["facts"]["profitability_proven"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(evidence), promotion)


if __name__ == "__main__":
    unittest.main()
