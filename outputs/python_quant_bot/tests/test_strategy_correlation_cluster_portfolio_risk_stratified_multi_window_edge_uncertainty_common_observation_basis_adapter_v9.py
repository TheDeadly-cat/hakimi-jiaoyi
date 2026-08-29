from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
_TESTS_DIR = str(Path(__file__).resolve().parent)
for _import_path in (_PROJECT_ROOT, _TESTS_DIR):
    if _import_path not in sys.path:
        sys.path.insert(0, _import_path)

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
    as adapter_v9,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8
    as adapter_v8,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1
    as basis_gate,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9 as presentation_cases


class StratifiedMultiWindowEdgeCommonObservationBasisAdapterV9Tests(
    unittest.TestCase
):
    def setUp(self):
        cls = presentation_cases.StratifiedMultiWindowEdgeUncertaintyPresentationV9Tests
        self.case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
        self.case.setUp()
        self.adapter_clear = self.case.adapter_v8_clear
        self.edge_clear = self.case.edge_clear
        self.edge_evidence = self.case.clear_evidence
        self.basis_preregistration = basis_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_preregistration_v1(
            trade_identity_hash=self.case.trade_hash,
            cluster_partition_hash=self.case.partition_hash,
            edge_preregistration_hash=self.case.preregistration[
                "preregistration_hash"
            ],
            observation_policy_hash="3" * 64,
            registration_sequence=self.case.preregistration["registration_sequence"],
            minimum_common_sample_count=30,
        )
        self.basis_evidence_clear = self._basis_evidence(common_sample_count=800)
        self.basis_clear = self._basis_document(self.basis_evidence_clear)
        self.basis_evidence_block = self._basis_evidence(common_sample_count=799)
        self.basis_block = self._basis_document(self.basis_evidence_block)
        self.adapter_context = {
            "adapter_v7_document": self.case.case.adapter,
            "adapter_v7_verification_context": self.case.case.adapter_context,
            "edge_gate_v1_document": self.edge_clear,
            "edge_gate_v1_verification_context": self.case._edge_context(
                self.edge_evidence
            ),
        }
        self.basis_context_clear = self._basis_context(self.basis_evidence_clear)
        self.basis_context_block = self._basis_context(self.basis_evidence_block)

    def _basis_evidence(self, *, common_sample_count):
        return basis_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_evidence_v1(
            trade_identity_hash=self.case.trade_hash,
            cluster_partition_hash=self.case.partition_hash,
            edge_evidence_hash=self.edge_evidence["evidence_hash"],
            observation_policy_hash="3" * 64,
            common_sample_set_hash="4" * 64,
            common_sample_count=common_sample_count,
            evidence_sequence=self.edge_evidence["evidence_sequence"],
        )

    def _basis_document(self, evidence):
        return basis_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
            self.basis_preregistration,
            evidence,
            self.edge_clear,
            edge_preregistration=self.case.preregistration,
            edge_evidence=self.edge_evidence,
            expected_preregistration_hash=self.basis_preregistration[
                "preregistration_hash"
            ],
        )

    def _basis_context(self, evidence, *, edge_document=None):
        return {
            "basis_evidence": evidence,
            "basis_preregistration": self.basis_preregistration,
            "edge_evidence": self.edge_evidence,
            "edge_gate_v1_document": (
                self.edge_clear if edge_document is None else edge_document
            ),
            "edge_preregistration": self.case.preregistration,
            "expected_basis_preregistration_hash": self.basis_preregistration[
                "preregistration_hash"
            ],
        }

    @staticmethod
    def _adapter_receipt(document, *, valid=True):
        return {
            "adapter_v8_exactly_verified": valid,
            "adapter_v8_hash": document["adapter_v8_hash"] if valid else None,
            "adapter_v8_status": document["status"] if valid else "UNKNOWN",
            "blockers": [] if valid else ["ADAPTER_V8_EXACT_REBUILD_FAILED"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": adapter_v8.VERIFICATION_SCHEMA_VERSION,
            "source_known": valid,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    @staticmethod
    def _basis_receipt(document, *, valid=True):
        return {
            "blockers": [] if valid else ["BASIS_GATE_EXACT_REBUILD_FAILED"],
            "common_observation_basis_gate_v1_exactly_verified": valid,
            "common_observation_basis_gate_v1_hash": (
                document["common_observation_basis_gate_v1_hash"] if valid else None
            ),
            "current_admission_allowed": False,
            "gate_decision": document["decision"] if valid else "UNKNOWN",
            "gate_status": document["status"] if valid else "UNKNOWN",
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": basis_gate.VERIFICATION_SCHEMA_VERSION,
            "source_known": valid,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    def _build(
        self,
        *,
        adapter_document=None,
        basis_document=None,
        adapter_context=None,
        basis_context=None,
        adapter_receipt=None,
        basis_receipt=None,
    ):
        adapter_value = self.adapter_clear if adapter_document is None else adapter_document
        basis_value = self.basis_clear if basis_document is None else basis_document
        adapter_context_value = (
            self.adapter_context if adapter_context is None else adapter_context
        )
        basis_context_value = (
            self.basis_context_clear if basis_context is None else basis_context
        )
        adapter_receipt_value = (
            self._adapter_receipt(adapter_value)
            if adapter_receipt is None
            else adapter_receipt
        )
        basis_receipt_value = (
            self._basis_receipt(basis_value)
            if basis_receipt is None
            else basis_receipt
        )
        with patch.object(
            adapter_v9,
            "_VERIFY_ADAPTER_V8",
            return_value=adapter_receipt_value,
        ):
            with patch.object(
                adapter_v9,
                "_VERIFY_BASIS_GATE_V1",
                return_value=basis_receipt_value,
            ):
                return adapter_v9.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9(
                    adapter_value,
                    basis_value,
                    adapter_v8_verification_context=adapter_context_value,
                    common_observation_basis_gate_v1_verification_context=basis_context_value,
                )

    def test_two_exact_clear_components_pass_locally(self):
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["blockers"], [])
        self.assertEqual(document["summary"]["common_sample_count"], 800)
        self.assertFalse(document["authority"]["paper_authorized"])

    def test_basis_block_overrides_adapter_v8_pass(self):
        document = self._build(
            basis_document=self.basis_block,
            basis_context=self.basis_context_block,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["component_states"]["adapter_v8_status"], "PASS")
        self.assertIn(
            "COMMON_OBSERVATION_BASIS_GATE_V1_BLOCKED", document["blockers"]
        )

    def test_adapter_v8_block_is_preserved(self):
        adapter_block = deepcopy(self.adapter_clear)
        adapter_block["status"] = "BLOCK"
        adapter_block["decision"] = "BLOCK_SYNTHETIC_ADAPTER_V8"
        adapter_block["blockers"] = ["SYNTHETIC_ADAPTER_V8_BLOCK"]
        adapter_block.pop("adapter_v8_hash")
        from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document

        adapter_block = seal_strict_canonical_document(adapter_block, "adapter_v8_hash")
        document = self._build(adapter_document=adapter_block)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("ADAPTER_V8_BLOCKED", document["blockers"])

    def test_shared_edge_document_context_splice_is_unknown(self):
        basis_context = deepcopy(self.basis_context_clear)
        basis_context["edge_gate_v1_document"] = self.case.edge_block
        document = self._build(basis_context=basis_context)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_edge_evidence_hash_splice_is_unknown(self):
        basis_document = deepcopy(self.basis_clear)
        basis_document["source"]["edge_evidence_hash"] = "5" * 64
        basis_document.pop("common_observation_basis_gate_v1_hash")
        from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document

        basis_document = seal_strict_canonical_document(
            basis_document, "common_observation_basis_gate_v1_hash"
        )
        document = self._build(basis_document=basis_document)
        self.assertEqual(document["status"], "UNKNOWN")

    def test_edge_preregistration_hash_splice_is_unknown(self):
        basis_document = deepcopy(self.basis_clear)
        basis_document["source"]["edge_preregistration_hash"] = "6" * 64
        basis_document.pop("common_observation_basis_gate_v1_hash")
        from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document

        basis_document = seal_strict_canonical_document(
            basis_document, "common_observation_basis_gate_v1_hash"
        )
        document = self._build(basis_document=basis_document)
        self.assertEqual(document["status"], "UNKNOWN")

    def test_trade_identity_splice_is_unknown(self):
        basis_document = deepcopy(self.basis_clear)
        basis_document["source"]["trade_identity_hash"] = "7" * 64
        basis_document.pop("common_observation_basis_gate_v1_hash")
        from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document

        basis_document = seal_strict_canonical_document(
            basis_document, "common_observation_basis_gate_v1_hash"
        )
        document = self._build(basis_document=basis_document)
        self.assertEqual(document["status"], "UNKNOWN")

    def test_edge_component_status_decision_splice_is_unknown(self):
        adapter_document = deepcopy(self.adapter_clear)
        adapter_document["component_states"]["edge_gate_v1_status"] = "BLOCK"
        adapter_document["component_states"]["edge_gate_v1_decision"] = "BLOCK_SPLICE"
        adapter_document.pop("adapter_v8_hash")
        from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document

        adapter_document = seal_strict_canonical_document(
            adapter_document, "adapter_v8_hash"
        )
        document = self._build(adapter_document=adapter_document)
        self.assertEqual(document["status"], "UNKNOWN")

    def test_malformed_receipts_hide_summary(self):
        adapter_receipt = self._adapter_receipt(self.adapter_clear)
        adapter_receipt["route_registered"] = False
        document = self._build(adapter_receipt=adapter_receipt)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])
        self.assertIsNone(document["source"]["common_sample_set_hash"])

    def test_projection_is_bounded_and_epistemically_calibrated(self):
        document = self._build()
        self.assertEqual(
            set(document["summary"]),
            {
                "blocked_pair_count",
                "common_sample_count",
                "confidence_z_micros",
                "correlation_floor_micros",
                "edge_pair_count",
                "edge_verified_pair_count",
                "insufficient_sample_pair_count",
                "maximum_confidence_upper_correlation_micros",
                "minimum_common_sample_count",
                "observed_breach_pair_count",
                "pair_count_matching_common_sample_count",
                "registered_window_count",
                "uncertainty_overlap_pair_count",
                "verified_window_count",
            },
        )
        self.assertFalse(document["facts"]["raw_samples_recomputed"])
        self.assertTrue(document["facts"]["provenance_declaration_only"])
        self.assertNotIn("pair_results", document)
        self.assertNotIn("verification_context", document)

    def test_inputs_are_not_mutated(self):
        adapter_document = deepcopy(self.adapter_clear)
        basis_document = deepcopy(self.basis_clear)
        adapter_context = deepcopy(self.adapter_context)
        basis_context = deepcopy(self.basis_context_clear)
        before = deepcopy(
            (adapter_document, basis_document, adapter_context, basis_context)
        )
        self._build(
            adapter_document=adapter_document,
            basis_document=basis_document,
            adapter_context=adapter_context,
            basis_context=basis_context,
        )
        self.assertEqual(
            (adapter_document, basis_document, adapter_context, basis_context),
            before,
        )

    def test_exact_verifier_rejects_permission_promotion(self):
        document = self._build()
        with patch.object(
            adapter_v9,
            "_VERIFY_ADAPTER_V8",
            return_value=self._adapter_receipt(self.adapter_clear),
        ):
            with patch.object(
                adapter_v9,
                "_VERIFY_BASIS_GATE_V1",
                return_value=self._basis_receipt(self.basis_clear),
            ):
                receipt = adapter_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9(
                    document,
                    self.adapter_clear,
                    self.basis_clear,
                    adapter_v8_verification_context=self.adapter_context,
                    common_observation_basis_gate_v1_verification_context=self.basis_context_clear,
                )
                self.assertTrue(receipt["adapter_v9_exactly_verified"])
                mutated = deepcopy(document)
                mutated["authority"]["paper_authorized"] = True
                rejected = adapter_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9(
                    mutated,
                    self.adapter_clear,
                    self.basis_clear,
                    adapter_v8_verification_context=self.adapter_context,
                    common_observation_basis_gate_v1_verification_context=self.basis_context_clear,
                )
        self.assertFalse(rejected["adapter_v9_exactly_verified"])


if __name__ == "__main__":
    unittest.main()
