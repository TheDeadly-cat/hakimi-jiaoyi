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
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
    as presentation_v10,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
    as presentation_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9 as adapter_cases


class StratifiedMultiWindowEdgeCommonObservationBasisPresentationV10Tests(
    unittest.TestCase
):
    def setUp(self):
        cls = adapter_cases.StratifiedMultiWindowEdgeCommonObservationBasisAdapterV9Tests
        self.case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
        self.case.setUp()
        self.presentation_v9 = self.case.case._build()
        self.adapter_v9_clear = self.case._build()
        self.adapter_v9_block = self.case._build(
            basis_document=self.case.basis_block,
            basis_context=self.case.basis_context_block,
        )
        self.presentation_context = {
            "adapter_v8_document": self.case.case.adapter_v8_clear,
            "adapter_v8_verification_context": self.case.adapter_context,
            "presentation_v8_document": self.case.case.presentation_v8,
            "presentation_v8_verification_context": self.case.case.presentation_context,
        }
        self.adapter_context_clear = {
            "adapter_v8_document": self.case.adapter_clear,
            "adapter_v8_verification_context": self.case.adapter_context,
            "common_observation_basis_gate_v1_document": self.case.basis_clear,
            "common_observation_basis_gate_v1_verification_context": self.case.basis_context_clear,
        }
        self.adapter_context_block = {
            "adapter_v8_document": self.case.adapter_clear,
            "adapter_v8_verification_context": self.case.adapter_context,
            "common_observation_basis_gate_v1_document": self.case.basis_block,
            "common_observation_basis_gate_v1_verification_context": self.case.basis_context_block,
        }

    @staticmethod
    def _presentation_receipt(document, *, valid=True):
        return {
            "blockers": [] if valid else ["PRESENTATION_V9_EXACT_REBUILD_FAILED"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_v9_exactly_verified": valid,
            "presentation_v9_hash": document["presentation_v9_hash"] if valid else None,
            "runtime_gate_activation_allowed": False,
            "schema_version": presentation_v9.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    @staticmethod
    def _adapter_receipt(document, *, valid=True):
        return {
            "adapter_v9_exactly_verified": valid,
            "adapter_v9_hash": document["adapter_v9_hash"] if valid else None,
            "adapter_v9_status": document["status"] if valid else "UNKNOWN",
            "blockers": [] if valid else ["ADAPTER_V9_EXACT_REBUILD_FAILED"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": adapter_v9.VERIFICATION_SCHEMA_VERSION,
            "source_known": valid,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    @staticmethod
    def _reseal(document, hash_key):
        document.pop(hash_key, None)
        return seal_strict_canonical_document(document, hash_key)

    def _build(
        self,
        *,
        presentation_document=None,
        adapter_document=None,
        presentation_context=None,
        adapter_context=None,
        presentation_receipt=None,
        adapter_receipt=None,
    ):
        presentation_value = (
            self.presentation_v9
            if presentation_document is None
            else presentation_document
        )
        adapter_value = (
            self.adapter_v9_clear if adapter_document is None else adapter_document
        )
        presentation_context_value = (
            self.presentation_context
            if presentation_context is None
            else presentation_context
        )
        adapter_context_value = (
            self.adapter_context_clear if adapter_context is None else adapter_context
        )
        presentation_receipt_value = (
            self._presentation_receipt(presentation_value)
            if presentation_receipt is None
            else presentation_receipt
        )
        adapter_receipt_value = (
            self._adapter_receipt(adapter_value)
            if adapter_receipt is None
            else adapter_receipt
        )
        with patch.object(
            presentation_v10,
            "_VERIFY_PRESENTATION_V9",
            return_value=presentation_receipt_value,
        ):
            with patch.object(
                presentation_v10,
                "_VERIFY_ADAPTER_V9",
                return_value=adapter_receipt_value,
            ):
                return presentation_v10.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
                    presentation_value,
                    adapter_value,
                    presentation_v9_verification_context=presentation_context_value,
                    adapter_v9_verification_context=adapter_context_value,
                )

    def test_two_exact_clear_components_remain_outer_blocked(self):
        document = self._build()
        self.assertEqual(document["local_decision"]["joint_status"], "PASS")
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["common_observation_summary"]["common_sample_count"], 800)
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])

    def test_adapter_v9_basis_block_overrides_presentation_v9_pass(self):
        document = self._build(
            adapter_document=self.adapter_v9_block,
            adapter_context=self.adapter_context_block,
        )
        self.assertEqual(document["local_decision"]["presentation_v9_joint_status"], "PASS")
        self.assertEqual(document["local_decision"]["adapter_v9_status"], "BLOCK")
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(document["gaps"]["common_observation_basis_blocker_count"], 1)

    def test_presentation_v9_local_block_is_preserved(self):
        presentation = deepcopy(self.presentation_v9)
        presentation["local_decision"]["joint_status"] = "BLOCK"
        presentation["local_decision"]["joint_decision"] = "BLOCK_SYNTHETIC_P9"
        presentation["gaps"]["local_blocker_count"] = 1
        presentation = self._reseal(presentation, "presentation_v9_hash")
        document = self._build(presentation_document=presentation)
        self.assertEqual(document["local_decision"]["presentation_v9_joint_status"], "BLOCK")
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")

    def test_shared_adapter_v8_document_context_splice_is_unknown(self):
        adapter_context = deepcopy(self.adapter_context_clear)
        adapter_context["adapter_v8_document"] = self.case.case.adapter_v8_block
        document = self._build(adapter_context=adapter_context)
        self.assertEqual(document["facts"]["cross_bindings_verified"], False)
        self.assertIsNone(document["risk_summary"])
        self.assertIsNone(document["common_observation_summary"])

    def test_adapter_v8_hash_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v9_clear)
        adapter["source"]["adapter_v8_hash"] = "5" * 64
        adapter = self._reseal(adapter, "adapter_v9_hash")
        document = self._build(adapter_document=adapter)
        self.assertIsNone(document["multi_window_summary"])

    def test_edge_gate_hash_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v9_clear)
        adapter["source"]["edge_gate_v1_hash"] = "6" * 64
        adapter = self._reseal(adapter, "adapter_v9_hash")
        document = self._build(adapter_document=adapter)
        self.assertIsNone(document["edge_uncertainty_summary"])

    def test_trade_identity_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v9_clear)
        adapter["source"]["trade_identity_hash"] = "7" * 64
        adapter = self._reseal(adapter, "adapter_v9_hash")
        document = self._build(adapter_document=adapter)
        self.assertEqual(document["source"]["state"], "UNKNOWN")

    def test_adapter_component_status_decision_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v9_clear)
        adapter["component_states"]["adapter_v8_status"] = "BLOCK"
        adapter["component_states"]["adapter_v8_decision"] = "BLOCK_SPLICE"
        adapter = self._reseal(adapter, "adapter_v9_hash")
        document = self._build(adapter_document=adapter)
        self.assertIsNone(document["risk_summary"])

    def test_edge_summary_count_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v9_clear)
        adapter["summary"]["edge_verified_pair_count"] += 1
        adapter = self._reseal(adapter, "adapter_v9_hash")
        document = self._build(adapter_document=adapter)
        self.assertIsNone(document["edge_uncertainty_summary"])

    def test_malformed_receipts_hide_every_summary(self):
        receipt = self._adapter_receipt(self.adapter_v9_clear)
        receipt["route_registered"] = False
        document = self._build(adapter_receipt=receipt)
        self.assertIsNone(document["risk_summary"])
        self.assertIsNone(document["multi_window_summary"])
        self.assertIsNone(document["edge_uncertainty_summary"])
        self.assertIsNone(document["common_observation_summary"])

    def test_projection_is_bounded_and_inputs_are_not_mutated(self):
        presentation = deepcopy(self.presentation_v9)
        adapter = deepcopy(self.adapter_v9_clear)
        presentation_context = deepcopy(self.presentation_context)
        adapter_context = deepcopy(self.adapter_context_clear)
        before = deepcopy((presentation, adapter, presentation_context, adapter_context))
        document = self._build(
            presentation_document=presentation,
            adapter_document=adapter,
            presentation_context=presentation_context,
            adapter_context=adapter_context,
        )
        self.assertEqual(
            set(document["common_observation_summary"]),
            {
                "all_pair_sample_counts_match",
                "common_sample_count",
                "edge_pair_count",
                "minimum_common_sample_count",
                "pair_count_matching_common_sample_count",
                "provenance_declaration_only",
                "raw_samples_recomputed",
            },
        )
        self.assertNotIn("pair_results", document)
        self.assertNotIn("sample_ids", document)
        self.assertNotIn("verification_context", document)
        self.assertEqual(
            (presentation, adapter, presentation_context, adapter_context), before
        )

    def test_exact_verifier_rejects_permission_promotion(self):
        document = self._build()
        with patch.object(
            presentation_v10,
            "_VERIFY_PRESENTATION_V9",
            return_value=self._presentation_receipt(self.presentation_v9),
        ):
            with patch.object(
                presentation_v10,
                "_VERIFY_ADAPTER_V9",
                return_value=self._adapter_receipt(self.adapter_v9_clear),
            ):
                receipt = presentation_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
                    document,
                    self.presentation_v9,
                    self.adapter_v9_clear,
                    presentation_v9_verification_context=self.presentation_context,
                    adapter_v9_verification_context=self.adapter_context_clear,
                )
                self.assertTrue(receipt["presentation_v10_exactly_verified"])
                mutated = deepcopy(document)
                mutated["authority"]["paper_authorized"] = True
                rejected = presentation_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10(
                    mutated,
                    self.presentation_v9,
                    self.adapter_v9_clear,
                    presentation_v9_verification_context=self.presentation_context,
                    adapter_v9_verification_context=self.adapter_context_clear,
                )
        self.assertFalse(rejected["presentation_v10_exactly_verified"])


if __name__ == "__main__":
    unittest.main()
