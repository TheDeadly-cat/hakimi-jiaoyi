from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8
    as adapter_v8,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
    as edge_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as presentation_cases


class StratifiedMultiWindowEdgeUncertaintyAdapterV8Tests(unittest.TestCase):
    def setUp(self):
        cls = presentation_cases.StratifiedMultiWindowPresentationV8Tests
        self.case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
        self.case.setUp()
        self.adapter = self.case.adapter
        self.adapter_context = self.case.adapter_context
        self.partition_hash = self.case.gate["window_summaries"][0][
            "cluster_partition_hash"
        ]
        self.trade_hash = self.case.gate["source"]["trade_identity_hash"]
        self.preregistration = self._preregistration()
        self.clear_evidence = self._evidence(sample_count=800)
        self.block_evidence = self._evidence(sample_count=8)
        self.edge_clear = self._edge(self.preregistration, self.clear_evidence)
        self.edge_block = self._edge(self.preregistration, self.block_evidence)

    def _preregistration(self, *, trade_hash=None, partition_hash=None):
        return edge_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1(
            [
                {"symbol": "A", "cluster_id": "cluster-1"},
                {"symbol": "B", "cluster_id": "cluster-1"},
                {"symbol": "C", "cluster_id": "cluster-2"},
            ],
            trade_identity_hash=self.trade_hash if trade_hash is None else trade_hash,
            cluster_partition_hash=(
                self.partition_hash if partition_hash is None else partition_hash
            ),
            registration_sequence=100,
            correlation_floor_micros=700_000,
            confidence_z_micros=1_644_854,
            minimum_sample_count=6,
        )

    def _evidence(
        self,
        *,
        sample_count,
        trade_hash=None,
        partition_hash=None,
    ):
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
            trade_identity_hash=self.trade_hash if trade_hash is None else trade_hash,
            cluster_partition_hash=(
                self.partition_hash if partition_hash is None else partition_hash
            ),
            evidence_sequence=101,
        )

    @staticmethod
    def _edge(preregistration, evidence):
        return edge_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            preregistration,
            evidence,
            expected_preregistration_hash=preregistration["preregistration_hash"],
        )

    @staticmethod
    def _edge_context(preregistration, evidence):
        return {
            "evidence": evidence,
            "expected_preregistration_hash": preregistration[
                "preregistration_hash"
            ],
            "preregistration": preregistration,
        }

    @staticmethod
    def _edge_receipt(document, preregistration, evidence):
        return edge_gate.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            document,
            preregistration,
            evidence,
            expected_preregistration_hash=preregistration[
                "preregistration_hash"
            ],
        )

    def _evaluate(
        self,
        *,
        adapter=None,
        edge=None,
        adapter_context=None,
        edge_context=None,
        adapter_receipt=None,
        edge_receipt=None,
    ):
        adapter_document = self.adapter if adapter is None else adapter
        edge_document = self.edge_clear if edge is None else edge
        adapter_context_value = (
            self.adapter_context if adapter_context is None else adapter_context
        )
        edge_context_value = (
            self._edge_context(self.preregistration, self.clear_evidence)
            if edge_context is None
            else edge_context
        )
        expected_adapter_receipt = (
            self.case._adapter_receipt(adapter_document)
            if adapter_receipt is None
            else adapter_receipt
        )
        expected_edge_receipt = (
            self._edge_receipt(
                edge_document,
                edge_context_value["preregistration"],
                edge_context_value["evidence"],
            )
            if edge_receipt is None
            else edge_receipt
        )
        with patch.object(
            adapter_v8,
            "_VERIFY_ADAPTER_V7",
            return_value=expected_adapter_receipt,
        ):
            with patch.object(
                adapter_v8,
                "_VERIFY_EDGE_GATE_V1",
                return_value=expected_edge_receipt,
            ):
                return adapter_v8.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8(
                    adapter_document,
                    edge_document,
                    adapter_v7_verification_context=adapter_context_value,
                    edge_gate_v1_verification_context=edge_context_value,
                )

    def test_two_exact_clear_components_pass_research_only(self):
        result = self._evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["component_states"]["adapter_v7_status"], "PASS")
        self.assertEqual(result["component_states"]["edge_gate_v1_status"], "PASS")
        self.assertEqual(result["summary"]["registered_window_count"], 3)
        self.assertEqual(result["summary"]["edge_verified_pair_count"], 2)
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_edge_uncertainty_block_overrides_adapter_v7_pass(self):
        result = self._evaluate(
            edge=self.edge_block,
            edge_context=self._edge_context(
                self.preregistration,
                self.block_evidence,
            ),
        )
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["component_states"]["adapter_v7_status"], "PASS")
        self.assertEqual(result["component_states"]["edge_gate_v1_status"], "BLOCK")
        self.assertIn("EDGE_UNCERTAINTY_GATE_V1_BLOCKED", result["blockers"])
        self.assertEqual(result["summary"]["uncertainty_overlap_pair_count"], 1)

    def test_adapter_v7_block_is_preserved_when_edge_clears(self):
        blocked_adapter = self.case._adapter_document(self.case.gate, "BLOCK")
        result = self._evaluate(adapter=blocked_adapter)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["component_states"]["adapter_v7_status"], "BLOCK")
        self.assertEqual(result["component_states"]["edge_gate_v1_status"], "PASS")
        self.assertIn("ADAPTER_V7_BLOCKED", result["blockers"])

    def test_trade_identity_splice_is_unknown_without_summary(self):
        other_trade = "f" * 64
        preregistration = self._preregistration(trade_hash=other_trade)
        evidence = self._evidence(sample_count=800, trade_hash=other_trade)
        edge_document = self._edge(preregistration, evidence)
        result = self._evaluate(
            edge=edge_document,
            edge_context=self._edge_context(preregistration, evidence),
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["summary"]["edge_verified_pair_count"])
        self.assertIn("TRADE_IDENTITY_SPLICE", result["blockers"])

    def test_partition_hash_splice_is_unknown_without_summary(self):
        other_partition = "e" * 64
        preregistration = self._preregistration(partition_hash=other_partition)
        evidence = self._evidence(
            sample_count=800,
            partition_hash=other_partition,
        )
        edge_document = self._edge(preregistration, evidence)
        result = self._evaluate(
            edge=edge_document,
            edge_context=self._edge_context(preregistration, evidence),
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("EDGE_GATE_PARTITION_HASH_SPLICE", result["blockers"])

    def test_adapter_gate_hash_splice_is_unknown(self):
        context = deepcopy(self.adapter_context)
        gate_document = deepcopy(context["stability_gate_v2_document"])
        gate_document["stability_gate_v2_hash"] = "0" * 64
        context["stability_gate_v2_document"] = gate_document
        result = self._evaluate(adapter_context=context)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("STABILITY_GATE_V2_HASH_SPLICE", result["blockers"])

    def test_non_single_partition_source_is_unknown(self):
        context = deepcopy(self.adapter_context)
        gate_document = deepcopy(context["stability_gate_v2_document"])
        gate_document["window_summaries"][0]["cluster_partition_hash"] = "9" * 64
        gate_document["summary"]["cluster_partition_stable"] = False
        gate_document["summary"]["unique_partition_count"] = 2
        gate_document.pop("stability_gate_v2_hash")
        gate_document = seal_strict_canonical_document(
            gate_document,
            "stability_gate_v2_hash",
        )
        context["stability_gate_v2_document"] = gate_document
        adapter_document = deepcopy(self.adapter)
        adapter_document["source"]["stability_gate_v2_hash"] = gate_document[
            "stability_gate_v2_hash"
        ]
        adapter_document.pop("adapter_v7_hash")
        adapter_document = seal_strict_canonical_document(
            adapter_document,
            "adapter_v7_hash",
        )
        result = self._evaluate(
            adapter=adapter_document,
            adapter_context=context,
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn(
            "STABILITY_GATE_PARTITION_NOT_SINGLE_AND_STABLE",
            result["blockers"],
        )

    def test_malformed_adapter_receipt_is_unknown(self):
        receipt = self.case._adapter_receipt(self.adapter)
        receipt["route_registered"] = False
        result = self._evaluate(adapter_receipt=receipt)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("ADAPTER_V7_EXACT_REBUILD_FAILED", result["blockers"])

    def test_malformed_edge_receipt_is_unknown(self):
        receipt = self._edge_receipt(
            self.edge_clear,
            self.preregistration,
            self.clear_evidence,
        )
        receipt["paper_authorized"] = True
        result = self._evaluate(edge_receipt=receipt)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("EDGE_GATE_V1_EXACT_REBUILD_FAILED", result["blockers"])

    def test_exact_unknown_edge_source_hides_all_partial_summaries(self):
        bad_evidence = deepcopy(self.clear_evidence)
        bad_evidence["evidence_sequence"] = 100
        bad_evidence.pop("evidence_hash")
        bad_evidence = seal_strict_canonical_document(bad_evidence, "evidence_hash")
        unknown_edge = self._edge(self.preregistration, bad_evidence)
        result = self._evaluate(
            edge=unknown_edge,
            edge_context=self._edge_context(self.preregistration, bad_evidence),
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertTrue(all(value is None for value in result["summary"].values()))
        self.assertIsNone(result["source"]["trade_identity_hash"])

    def test_output_is_bounded_and_inputs_are_not_mutated(self):
        adapter_before = deepcopy(self.adapter)
        edge_before = deepcopy(self.edge_clear)
        result = self._evaluate()
        self.assertEqual(self.adapter, adapter_before)
        self.assertEqual(self.edge_clear, edge_before)
        self.assertNotIn("pair_results", result)
        self.assertNotIn("window_summaries", result)
        self.assertNotIn("source_documents", result)
        self.assertFalse(result["facts"]["source_documents_embedded"])
        self.assertFalse(result["facts"]["verification_contexts_embedded"])

    def test_exact_verifier_rejects_resealed_permission_promotion(self):
        result = self._evaluate()
        adapter_receipt = self.case._adapter_receipt(self.adapter)
        edge_receipt = self._edge_receipt(
            self.edge_clear,
            self.preregistration,
            self.clear_evidence,
        )
        with patch.object(
            adapter_v8,
            "_VERIFY_ADAPTER_V7",
            return_value=adapter_receipt,
        ):
            with patch.object(
                adapter_v8,
                "_VERIFY_EDGE_GATE_V1",
                return_value=edge_receipt,
            ):
                receipt = adapter_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8(
                    result,
                    self.adapter,
                    self.edge_clear,
                    adapter_v7_verification_context=self.adapter_context,
                    edge_gate_v1_verification_context=self._edge_context(
                        self.preregistration,
                        self.clear_evidence,
                    ),
                )
                self.assertEqual(receipt["status"], "PASS")
                promoted = deepcopy(result)
                promoted["authority"]["paper_authorized"] = True
                promoted.pop("adapter_v8_hash")
                promoted = seal_strict_canonical_document(
                    promoted,
                    "adapter_v8_hash",
                )
                rejected = adapter_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_adapter_v8(
                    promoted,
                    self.adapter,
                    self.edge_clear,
                    adapter_v7_verification_context=self.adapter_context,
                    edge_gate_v1_verification_context=self._edge_context(
                        self.preregistration,
                        self.clear_evidence,
                    ),
                )
        self.assertEqual(rejected["status"], "BLOCK")
        self.assertFalse(rejected["adapter_v8_exactly_verified"])


if __name__ == "__main__":
    unittest.main()
