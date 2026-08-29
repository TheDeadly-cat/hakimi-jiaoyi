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
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8
    as adapter_v8,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
    as presentation_v9,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
    as edge_gate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
    as presentation_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as presentation_cases


class StratifiedMultiWindowEdgeUncertaintyPresentationV9Tests(unittest.TestCase):
    def setUp(self):
        cls = presentation_cases.StratifiedMultiWindowPresentationV8Tests
        self.case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
        self.case.setUp()
        self.presentation_v8 = self.case._build()
        self.presentation_context = {
            "adapter_v7_document": self.case.adapter,
            "adapter_v7_verification_context": self.case.adapter_context,
            "presentation_v7_document": self.case.presentation,
            "presentation_v7_verification_context": self.case.presentation_context,
        }
        self.trade_hash = self.case.gate["source"]["trade_identity_hash"]
        self.partition_hash = self.case.gate["window_summaries"][0][
            "cluster_partition_hash"
        ]
        self.preregistration = self._preregistration()
        self.clear_evidence = self._evidence(sample_count=800)
        self.block_evidence = self._evidence(sample_count=8)
        self.edge_clear = self._edge(self.preregistration, self.clear_evidence)
        self.edge_block = self._edge(self.preregistration, self.block_evidence)
        self.adapter_v8_clear = self._adapter_v8(
            self.case.adapter,
            self.edge_clear,
            self.clear_evidence,
        )
        self.adapter_v8_block = self._adapter_v8(
            self.case.adapter,
            self.edge_block,
            self.block_evidence,
        )

    def _preregistration(self):
        return edge_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1(
            [
                {"symbol": "A", "cluster_id": "cluster-1"},
                {"symbol": "B", "cluster_id": "cluster-1"},
                {"symbol": "C", "cluster_id": "cluster-2"},
            ],
            trade_identity_hash=self.trade_hash,
            cluster_partition_hash=self.partition_hash,
            registration_sequence=100,
            correlation_floor_micros=700_000,
            confidence_z_micros=1_644_854,
            minimum_sample_count=6,
        )

    def _evidence(self, *, sample_count):
        return edge_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_evidence_v1(
            [
                {
                    "left_symbol": "A",
                    "right_symbol": "C",
                    "observed_correlation_micros": 650_000,
                    "sample_count": sample_count,
                },
                {
                    "left_symbol": "B",
                    "right_symbol": "C",
                    "observed_correlation_micros": 500_000,
                    "sample_count": 800,
                },
            ],
            trade_identity_hash=self.trade_hash,
            cluster_partition_hash=self.partition_hash,
            evidence_sequence=101,
        )

    @staticmethod
    def _edge(preregistration, evidence):
        return edge_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            preregistration,
            evidence,
            expected_preregistration_hash=preregistration["preregistration_hash"],
        )

    def _edge_context(self, evidence):
        return {
            "evidence": evidence,
            "expected_preregistration_hash": self.preregistration[
                "preregistration_hash"
            ],
            "preregistration": self.preregistration,
        }

    def _adapter_v8(self, adapter_document, edge_document, evidence):
        with patch.object(
            adapter_v8,
            "_VERIFY_ADAPTER_V7",
            return_value=self.case._adapter_receipt(adapter_document),
        ):
            return adapter_v8.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8(
                adapter_document,
                edge_document,
                adapter_v7_verification_context=self.case.adapter_context,
                edge_gate_v1_verification_context=self._edge_context(evidence),
            )

    @staticmethod
    def _presentation_receipt(document, *, valid=True):
        return {
            "blockers": [] if valid else ["PRESENTATION_V8_EXACT_REBUILD"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_v8_exactly_verified": valid,
            "presentation_v8_hash": document["presentation_v8_hash"] if valid else None,
            "runtime_gate_activation_allowed": False,
            "schema_version": presentation_v8.VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    @staticmethod
    def _adapter_receipt(document, *, valid=True):
        return {
            "adapter_v8_exactly_verified": valid,
            "adapter_v8_hash": document["adapter_v8_hash"] if valid else None,
            "adapter_v8_status": document["status"] if valid else "UNKNOWN",
            "blockers": [] if valid else ["ADAPTER_V8_EXACT_REBUILD"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": adapter_v8.VERIFICATION_SCHEMA_VERSION,
            "source_known": valid,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    def _adapter_context(self, edge_document, evidence, *, adapter_document=None):
        return {
            "adapter_v7_document": (
                self.case.adapter if adapter_document is None else adapter_document
            ),
            "adapter_v7_verification_context": self.case.adapter_context,
            "edge_gate_v1_document": edge_document,
            "edge_gate_v1_verification_context": self._edge_context(evidence),
        }

    def _build(
        self,
        *,
        presentation=None,
        adapter=None,
        presentation_context=None,
        adapter_context=None,
        presentation_receipt=None,
        adapter_receipt=None,
    ):
        presentation_document = (
            self.presentation_v8 if presentation is None else presentation
        )
        adapter_document = self.adapter_v8_clear if adapter is None else adapter
        presentation_context_value = (
            self.presentation_context
            if presentation_context is None
            else presentation_context
        )
        adapter_context_value = (
            self._adapter_context(self.edge_clear, self.clear_evidence)
            if adapter_context is None
            else adapter_context
        )
        expected_presentation_receipt = (
            self._presentation_receipt(presentation_document)
            if presentation_receipt is None
            else presentation_receipt
        )
        expected_adapter_receipt = (
            self._adapter_receipt(adapter_document)
            if adapter_receipt is None
            else adapter_receipt
        )
        with patch.object(
            presentation_v9,
            "_VERIFY_PRESENTATION_V8",
            return_value=expected_presentation_receipt,
        ):
            with patch.object(
                presentation_v9,
                "_VERIFY_ADAPTER_V8",
                return_value=expected_adapter_receipt,
            ):
                return presentation_v9.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
                    presentation_document,
                    adapter_document,
                    presentation_v8_verification_context=presentation_context_value,
                    adapter_v8_verification_context=adapter_context_value,
                )

    def test_two_exact_clear_components_remain_outer_blocked(self):
        result = self._build()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["local_decision"]["joint_status"], "PASS")
        self.assertEqual(result["local_decision"]["adapter_v8_status"], "PASS")
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_edge_block_overrides_presentation_v8_local_pass(self):
        result = self._build(
            adapter=self.adapter_v8_block,
            adapter_context=self._adapter_context(
                self.edge_block,
                self.block_evidence,
            ),
        )
        self.assertEqual(result["local_decision"]["presentation_v8_joint_status"], "PASS")
        self.assertEqual(result["local_decision"]["adapter_v8_status"], "BLOCK")
        self.assertEqual(result["local_decision"]["edge_gate_v1_status"], "BLOCK")
        self.assertEqual(result["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(result["edge_uncertainty_summary"]["uncertainty_overlap_pair_count"], 1)

    def test_presentation_v8_local_block_is_preserved(self):
        blocked = deepcopy(self.presentation_v8)
        blocked["local_decision"]["joint_status"] = "BLOCK"
        blocked["local_decision"]["joint_decision"] = "BLOCK_LOCAL_RESEARCH_COMPONENT"
        blocked["gaps"]["local_blocker_count"] = 1
        blocked.pop("presentation_v8_hash")
        blocked = seal_strict_canonical_document(blocked, "presentation_v8_hash")
        result = self._build(presentation=blocked)
        self.assertEqual(result["local_decision"]["presentation_v8_joint_status"], "BLOCK")
        self.assertEqual(result["local_decision"]["adapter_v8_status"], "PASS")
        self.assertEqual(result["local_decision"]["joint_status"], "BLOCK")

    def test_adapter_v7_document_context_splice_is_unknown(self):
        context = self._adapter_context(self.edge_clear, self.clear_evidence)
        other_adapter = deepcopy(self.case.adapter)
        other_adapter["source"]["anchor_window_id"] = "other"
        other_adapter.pop("adapter_v7_hash")
        other_adapter = seal_strict_canonical_document(other_adapter, "adapter_v7_hash")
        context["adapter_v7_document"] = other_adapter
        result = self._build(adapter_context=context)
        self.assertEqual(result["source"]["state"], "UNKNOWN")
        self.assertIsNone(result["risk_summary"])

    def test_stability_gate_hash_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v8_clear)
        adapter["source"]["stability_gate_v2_hash"] = "0" * 64
        adapter.pop("adapter_v8_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_v8_hash")
        result = self._build(adapter=adapter)
        self.assertEqual(result["source"]["state"], "UNKNOWN")
        self.assertIsNone(result["multi_window_summary"])

    def test_trade_identity_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v8_clear)
        adapter["source"]["trade_identity_hash"] = "f" * 64
        adapter.pop("adapter_v8_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_v8_hash")
        result = self._build(adapter=adapter)
        self.assertEqual(result["source"]["state"], "UNKNOWN")
        self.assertIsNone(result["edge_uncertainty_summary"])

    def test_component_status_decision_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v8_clear)
        adapter["component_states"]["adapter_v7_status"] = "BLOCK"
        adapter["component_states"]["adapter_v7_decision"] = "BLOCK_FORGED"
        adapter.pop("adapter_v8_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_v8_hash")
        result = self._build(adapter=adapter)
        self.assertEqual(result["source"]["state"], "UNKNOWN")
        self.assertIsNone(result["risk_summary"])

    def test_window_count_splice_is_unknown(self):
        adapter = deepcopy(self.adapter_v8_clear)
        adapter["summary"]["registered_window_count"] += 1
        adapter["summary"]["verified_window_count"] += 1
        adapter.pop("adapter_v8_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_v8_hash")
        result = self._build(adapter=adapter)
        self.assertEqual(result["source"]["state"], "UNKNOWN")
        self.assertIsNone(result["multi_window_summary"])

    def test_malformed_receipts_fail_closed_without_partial_summaries(self):
        presentation_receipt = self._presentation_receipt(self.presentation_v8)
        presentation_receipt["route_registered"] = False
        adapter_receipt = self._adapter_receipt(self.adapter_v8_clear)
        adapter_receipt["paper_authorized"] = True
        for result in (
            self._build(presentation_receipt=presentation_receipt),
            self._build(adapter_receipt=adapter_receipt),
        ):
            self.assertEqual(result["source"]["state"], "UNKNOWN")
            self.assertIsNone(result["risk_summary"])
            self.assertIsNone(result["multi_window_summary"])
            self.assertIsNone(result["edge_uncertainty_summary"])

    def test_projection_is_bounded_and_inputs_are_not_mutated(self):
        presentation_before = deepcopy(self.presentation_v8)
        adapter_before = deepcopy(self.adapter_v8_clear)
        result = self._build()
        self.assertEqual(self.presentation_v8, presentation_before)
        self.assertEqual(self.adapter_v8_clear, adapter_before)
        self.assertNotIn("pair_results", result)
        self.assertNotIn("window_summaries", result)
        self.assertNotIn("verification_contexts", result)
        self.assertFalse(result["facts"]["source_documents_embedded"])
        self.assertFalse(result["facts"]["verification_contexts_embedded"])

    def test_axis_order_and_neutral_permission_are_fixed(self):
        result = self._build()
        self.assertEqual(result["axis_order"], list(presentation_v9.AXIS_ORDER))
        self.assertEqual([stage["axis"] for stage in result["stages"]], list(presentation_v9.AXIS_ORDER))
        self.assertEqual(result["stages"][2]["state"], "CANDIDATE")
        self.assertEqual(result["stages"][3]["state"], "NONE")
        self.assertFalse(result["authority"]["http_candidate_creation_allowed"])

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        result = self._build()
        presentation_receipt = self._presentation_receipt(self.presentation_v8)
        adapter_receipt = self._adapter_receipt(self.adapter_v8_clear)
        with patch.object(
            presentation_v9,
            "_VERIFY_PRESENTATION_V8",
            return_value=presentation_receipt,
        ):
            with patch.object(
                presentation_v9,
                "_VERIFY_ADAPTER_V8",
                return_value=adapter_receipt,
            ):
                receipt = presentation_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
                    result,
                    self.presentation_v8,
                    self.adapter_v8_clear,
                    presentation_v8_verification_context=self.presentation_context,
                    adapter_v8_verification_context=self._adapter_context(
                        self.edge_clear,
                        self.clear_evidence,
                    ),
                )
                self.assertEqual(receipt["status"], "PASS")
                promoted = deepcopy(result)
                promoted["authority"]["paper_authorized"] = True
                promoted.pop("presentation_v9_hash")
                promoted = seal_strict_canonical_document(
                    promoted,
                    "presentation_v9_hash",
                )
                rejected = presentation_v9.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9(
                    promoted,
                    self.presentation_v8,
                    self.adapter_v8_clear,
                    presentation_v8_verification_context=self.presentation_context,
                    adapter_v8_verification_context=self._adapter_context(
                        self.edge_clear,
                        self.clear_evidence,
                    ),
                )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["presentation_v9_exactly_verified"])


if __name__ == "__main__":
    unittest.main()
