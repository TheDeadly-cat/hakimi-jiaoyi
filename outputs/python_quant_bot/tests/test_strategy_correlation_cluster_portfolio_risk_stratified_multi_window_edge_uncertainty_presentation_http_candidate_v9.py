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

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_candidate_v9
    as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9
    as presentation_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9 as presentation_cases


def _fixture():
    cls = presentation_cases.StratifiedMultiWindowEdgeUncertaintyPresentationV9Tests
    case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
    case.setUp()
    return case, case._build()


def _request(document: dict) -> dict:
    return {
        "schema_version": candidate.REQUEST_SCHEMA_VERSION,
        "stratified_multi_window_edge_uncertainty_presentation_v9_document": document,
        "expected_presentation_v9_hash": document["presentation_v9_hash"],
    }


def _context(case, *, adapter_document=None, edge_document=None, evidence=None) -> dict:
    adapter = case.adapter_v8_clear if adapter_document is None else adapter_document
    edge = case.edge_clear if edge_document is None else edge_document
    edge_evidence = case.clear_evidence if evidence is None else evidence
    return {
        "presentation_v8_document": case.presentation_v8,
        "adapter_v8_document": adapter,
        "presentation_v8_verification_context": case.presentation_context,
        "adapter_v8_verification_context": case._adapter_context(edge, edge_evidence),
    }


def _receipt(document: dict, *, valid: bool = True) -> dict:
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


def _reseal(document: dict) -> dict:
    document.pop("presentation_v9_hash", None)
    return seal_strict_canonical_document(document, "presentation_v9_hash")


def _contains_float(value) -> bool:
    if type(value) is float:
        return True
    if type(value) is list:
        return any(_contains_float(item) for item in value)
    if type(value) is dict:
        return any(_contains_float(item) for item in value.values())
    return False


def _all_keys(value) -> set[str]:
    if type(value) is list:
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    if type(value) is dict:
        keys = set(value)
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    return set()


class StratifiedMultiWindowEdgeUncertaintyPresentationHttpCandidateV9Tests(
    unittest.TestCase
):
    def setUp(self):
        self.case, self.presentation = _fixture()
        self.context = _context(self.case)
        self.blocked_presentation = self.case._build(
            adapter=self.case.adapter_v8_block,
            adapter_context=self.case._adapter_context(
                self.case.edge_block,
                self.case.block_evidence,
            ),
        )
        self.blocked_context = _context(
            self.case,
            adapter_document=self.case.adapter_v8_block,
            edge_document=self.case.edge_block,
            evidence=self.case.block_evidence,
        )

    def _build(self, document=None, *, context=None, receipt=None):
        source = self.presentation if document is None else document
        context_value = self.context if context is None else context
        expected_receipt = _receipt(source) if receipt is None else receipt
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=expected_receipt):
            return candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                _request(source),
                presentation_verification_context=context_value,
            )

    def test_exact_edge_clear_is_known_but_outer_blocked(self):
        response = self._build()
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "PASS")
        self.assertEqual(response["payload"]["edge_uncertainty_summary"]["blocked_pair_count"], 0)
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])
        self.assertFalse(response["authority"]["live_order_allowed"])

    def test_edge_uncertainty_block_remains_visible_and_adds_blocker(self):
        response = self._build(
            self.blocked_presentation,
            context=self.blocked_context,
        )
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["edge_gate_v1_status"], "BLOCK")
        self.assertGreater(
            response["payload"]["edge_uncertainty_summary"]["blocked_pair_count"],
            0,
        )
        self.assertIn("CROSS_CLUSTER_EDGE_UNCERTAINTY_GATE_BLOCKED", response["blockers"])
        self.assertIn("LOCAL_RESEARCH_GATE_BLOCKED", response["blockers"])

    def test_unknown_source_hides_all_partial_summaries(self):
        document = deepcopy(self.presentation)
        document["facts"]["cross_bindings_verified"] = False
        document["source"]["state"] = "UNKNOWN"
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        self.assertIsNone(response["lineage"]["presentation_v9_hash"])
        self.assertFalse(response["facts"]["result_available"])

    def test_extra_request_key_fails_before_verifier(self):
        request = _request(self.presentation)
        request["route"] = "/forbidden"
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_substituted_expected_hash_fails_before_verifier(self):
        request = _request(self.presentation)
        request["expected_presentation_v9_hash"] = "0" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_context_shape_is_exact(self):
        context = deepcopy(self.context)
        context["runtime"] = {"forbidden": True}
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                _request(self.presentation),
                presentation_verification_context=context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_malformed_verification_receipt_cannot_unlock_payload(self):
        receipt = _receipt(self.presentation)
        receipt["route_registered"] = False
        response = self._build(receipt=receipt)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_verifier_exception_is_unknown_without_partial_payload(self):
        with patch.object(candidate, "_VERIFY_PRESENTATION", side_effect=ValueError("synthetic")):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                _request(self.presentation),
                presentation_verification_context=self.context,
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_response_exact_rebuild_detects_permission_mutation(self):
        request = _request(self.presentation)
        receipt = _receipt(self.presentation)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                request,
                presentation_verification_context=self.context,
            )
            self.assertTrue(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                    response,
                    request,
                    presentation_verification_context=self.context,
                )
            )
            mutated = deepcopy(response)
            mutated["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_http_candidate_response_v9(
                    mutated,
                    request,
                    presentation_verification_context=self.context,
                )
            )

    def test_projection_is_bounded_aggregate_only_and_float_free(self):
        response = self._build()
        payload = response["payload"]
        self.assertEqual(set(payload["edge_uncertainty_summary"]), {
            "blocked_pair_count",
            "cluster_partition_hash",
            "confidence_z_micros",
            "correlation_floor_micros",
            "insufficient_sample_pair_count",
            "maximum_confidence_upper_correlation_micros",
            "observed_breach_pair_count",
            "uncertainty_overlap_pair_count",
            "verified_pair_count",
        })
        projected_keys = _all_keys(payload)
        for forbidden in (
            "edge_pair_results",
            "pair_results",
            "window_documents",
            "positions",
            "correlation_matrix",
            "verification_context",
        ):
            self.assertNotIn(forbidden, projected_keys)
        self.assertFalse(payload["facts"]["positions_embedded"])
        self.assertFalse(payload["facts"]["verification_contexts_embedded"])
        self.assertFalse(_contains_float(response))

    def test_resealed_source_permission_promotion_is_unknown(self):
        document = deepcopy(self.presentation)
        document["authority"]["paper_authorized"] = True
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_inputs_are_not_mutated(self):
        document = deepcopy(self.presentation)
        context = deepcopy(self.context)
        document_before = deepcopy(document)
        context_before = deepcopy(context)
        response = self._build(document, context=context)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(document, document_before)
        self.assertEqual(context, context_before)


if __name__ == "__main__":
    unittest.main()
