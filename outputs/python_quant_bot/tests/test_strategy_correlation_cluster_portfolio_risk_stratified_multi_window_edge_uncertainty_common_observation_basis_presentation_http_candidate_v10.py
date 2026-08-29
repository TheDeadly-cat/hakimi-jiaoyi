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
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_candidate_v10
    as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
    as presentation_v10,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10 as presentation_cases


def _fixture():
    cls = presentation_cases.StratifiedMultiWindowEdgeCommonObservationBasisPresentationV10Tests
    case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
    case.setUp()
    return case, case._build()


def _request(document):
    return {
        "expected_presentation_v10_hash": document["presentation_v10_hash"],
        "schema_version": candidate.REQUEST_SCHEMA_VERSION,
        "stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10_document": document,
    }


def _context(case, *, adapter_document=None, adapter_context=None):
    return {
        "adapter_v9_document": (
            case.adapter_v9_clear if adapter_document is None else adapter_document
        ),
        "adapter_v9_verification_context": (
            case.adapter_context_clear if adapter_context is None else adapter_context
        ),
        "presentation_v9_document": case.presentation_v9,
        "presentation_v9_verification_context": case.presentation_context,
    }


def _receipt(document, *, valid=True):
    return {
        "blockers": [] if valid else ["PRESENTATION_V10_EXACT_REBUILD_FAILED"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_v10_exactly_verified": valid,
        "presentation_v10_hash": document["presentation_v10_hash"] if valid else None,
        "runtime_gate_activation_allowed": False,
        "schema_version": presentation_v10.VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if valid else "BLOCK",
        "writer_allowed": False,
    }


def _reseal(document):
    document.pop("presentation_v10_hash", None)
    return seal_strict_canonical_document(document, "presentation_v10_hash")


def _contains_float(value):
    if type(value) is float:
        return True
    if type(value) is list:
        return any(_contains_float(item) for item in value)
    if type(value) is dict:
        return any(_contains_float(item) for item in value.values())
    return False


def _all_keys(value):
    if type(value) is list:
        keys = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    if type(value) is dict:
        keys = set(value)
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    return set()


class CommonObservationBasisPresentationHttpCandidateV10Tests(unittest.TestCase):
    def setUp(self):
        self.case, self.presentation = _fixture()
        self.context = _context(self.case)
        self.blocked_presentation = self.case._build(
            adapter_document=self.case.adapter_v9_block,
            adapter_context=self.case.adapter_context_block,
        )
        self.blocked_context = _context(
            self.case,
            adapter_document=self.case.adapter_v9_block,
            adapter_context=self.case.adapter_context_block,
        )

    def _build(self, document=None, *, context=None, receipt=None):
        source = self.presentation if document is None else document
        context_value = self.context if context is None else context
        receipt_value = _receipt(source) if receipt is None else receipt
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt_value):
            return candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                _request(source),
                presentation_verification_context=context_value,
            )

    def test_exact_common_basis_clear_is_known_but_outer_blocked(self):
        response = self._build()
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "PASS")
        self.assertEqual(response["payload"]["common_observation_summary"]["common_sample_count"], 800)
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])

    def test_basis_block_remains_visible_and_adds_blocker(self):
        response = self._build(
            self.blocked_presentation,
            context=self.blocked_context,
        )
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(
            response["payload"]["local_decision"][
                "common_observation_basis_gate_v1_status"
            ],
            "BLOCK",
        )
        self.assertIn("COMMON_OBSERVATION_BASIS_GATE_BLOCKED", response["blockers"])
        self.assertIn("LOCAL_RESEARCH_GATE_BLOCKED", response["blockers"])

    def test_unknown_source_hides_every_partial_summary(self):
        document = deepcopy(self.presentation)
        document["facts"]["cross_bindings_verified"] = False
        document["source"]["state"] = "UNKNOWN"
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        self.assertIsNone(response["lineage"]["presentation_v10_hash"])
        self.assertFalse(response["facts"]["result_available"])

    def test_extra_request_key_fails_before_verifier(self):
        request = _request(self.presentation)
        request["route"] = "/forbidden"
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_substituted_expected_hash_fails_before_verifier(self):
        request = _request(self.presentation)
        request["expected_presentation_v10_hash"] = "0" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_context_shape_is_exact(self):
        context = deepcopy(self.context)
        context["runtime"] = {"forbidden": True}
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                _request(self.presentation),
                presentation_verification_context=context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_malformed_receipt_cannot_unlock_payload(self):
        receipt = _receipt(self.presentation)
        receipt["route_registered"] = False
        response = self._build(receipt=receipt)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_verifier_exception_is_unknown_without_partial_payload(self):
        with patch.object(candidate, "_VERIFY_PRESENTATION", side_effect=ValueError("synthetic")):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                _request(self.presentation),
                presentation_verification_context=self.context,
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_response_exact_rebuild_detects_permission_mutation(self):
        request = _request(self.presentation)
        receipt = _receipt(self.presentation)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                request,
                presentation_verification_context=self.context,
            )
            self.assertTrue(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                    response,
                    request,
                    presentation_verification_context=self.context,
                )
            )
            mutated = deepcopy(response)
            mutated["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_http_candidate_response_v10(
                    mutated,
                    request,
                    presentation_verification_context=self.context,
                )
            )

    def test_projection_is_bounded_aggregate_only_and_float_free(self):
        response = self._build()
        payload = response["payload"]
        self.assertEqual(
            set(payload["common_observation_summary"]),
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
        keys = _all_keys(payload)
        for forbidden in (
            "pair_results",
            "sample_ids",
            "window_documents",
            "positions",
            "correlation_matrix",
            "verification_context",
        ):
            self.assertNotIn(forbidden, keys)
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
        before = deepcopy((document, context))
        response = self._build(document, context=context)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual((document, context), before)


if __name__ == "__main__":
    unittest.main()
