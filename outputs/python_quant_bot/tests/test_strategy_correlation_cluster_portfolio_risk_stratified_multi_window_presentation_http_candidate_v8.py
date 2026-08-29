from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_candidate_v8
    as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
    as presentation_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as presentation_cases


def _fixture():
    cls = presentation_cases.StratifiedMultiWindowPresentationV8Tests
    case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
    case.setUp()
    return case, case._build()


def _request(document: dict) -> dict:
    return {
        "schema_version": candidate.REQUEST_SCHEMA_VERSION,
        "stratified_multi_window_presentation_v8_document": document,
        "expected_presentation_v8_hash": document["presentation_v8_hash"],
    }


def _context(case) -> dict:
    return {
        "presentation_v7_document": case.presentation,
        "adapter_v7_document": case.adapter,
        "presentation_v7_verification_context": case.presentation_context,
        "adapter_v7_verification_context": case.adapter_context,
    }


def _receipt(document: dict, *, valid: bool = True) -> dict:
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


def _reseal(document: dict) -> dict:
    document.pop("presentation_v8_hash", None)
    return seal_strict_canonical_document(document, "presentation_v8_hash")


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


class StratifiedMultiWindowPresentationHttpCandidateV8Tests(unittest.TestCase):
    def setUp(self):
        self.case, self.presentation = _fixture()
        self.context = _context(self.case)

    def _build(self, document: dict | None = None, *, receipt: dict | None = None):
        source = document if document is not None else self.presentation
        expected_receipt = receipt if receipt is not None else _receipt(source)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=expected_receipt):
            return candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                _request(source),
                presentation_verification_context=self.context,
            )

    def test_exact_multi_window_clear_is_known_but_outer_blocked(self):
        response = self._build()
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "PASS")
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])
        self.assertFalse(response["authority"]["live_order_allowed"])

    def test_multi_window_block_remains_visible_and_adds_blocker(self):
        document = deepcopy(self.presentation)
        document["local_decision"]["adapter_v7_status"] = "BLOCK"
        document["local_decision"]["adapter_v7_decision"] = "BLOCK_MULTI_WINDOW"
        document["local_decision"]["joint_status"] = "BLOCK"
        document["local_decision"]["joint_decision"] = "BLOCK_MULTI_WINDOW"
        document["multi_window_summary"]["any_registered_window_blocked"] = True
        document["gaps"]["multi_window_blocker_count"] = 1
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "BLOCK")
        self.assertIn("MULTI_WINDOW_STABILITY_GATE_BLOCKED", response["blockers"])
        self.assertIn("LOCAL_RESEARCH_GATE_BLOCKED", response["blockers"])

    def test_unknown_source_hides_all_partial_summaries(self):
        document = deepcopy(self.presentation)
        document["facts"]["adapter_v7_exactly_verified"] = False
        document["source"]["state"] = "UNKNOWN"
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        self.assertIsNone(response["lineage"]["presentation_v8_hash"])
        self.assertFalse(response["facts"]["result_available"])

    def test_extra_request_key_fails_before_verifier(self):
        request = _request(self.presentation)
        request["route"] = "/forbidden"
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_substituted_expected_hash_fails_before_verifier(self):
        request = _request(self.presentation)
        request["expected_presentation_v8_hash"] = "0" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                request,
                presentation_verification_context=self.context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_context_shape_is_exact(self):
        context = deepcopy(self.context)
        context["runtime"] = {"forbidden": True}
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
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
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                _request(self.presentation),
                presentation_verification_context=self.context,
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_response_exact_rebuild_detects_permission_mutation(self):
        request = _request(self.presentation)
        receipt = _receipt(self.presentation)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                request,
                presentation_verification_context=self.context,
            )
            self.assertTrue(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                    response,
                    request,
                    presentation_verification_context=self.context,
                )
            )
            mutated = deepcopy(response)
            mutated["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                    mutated,
                    request,
                    presentation_verification_context=self.context,
                )
            )

    def test_projection_is_bounded_aggregate_only(self):
        response = self._build()
        payload = response["payload"]
        self.assertEqual(
            set(payload["multi_window_summary"]),
            {
                "anchor_window_id",
                "any_registered_window_blocked",
                "cluster_partition_stable",
                "minimum_conservative_weighted_effective_strata_count",
                "registered_window_count",
                "strata_topology_stable",
                "verified_window_count",
                "worst_window_maximum_active_stratum_gross_pct",
            },
        )
        projected_keys = _all_keys(payload)
        self.assertNotIn("window_documents", projected_keys)
        self.assertNotIn("positions", projected_keys)
        self.assertNotIn("correlation_matrix", projected_keys)
        self.assertNotIn("verification_context", projected_keys)
        self.assertFalse(payload["facts"]["positions_embedded"])
        self.assertFalse(payload["facts"]["verification_contexts_embedded"])

    def test_resealed_source_permission_promotion_is_unknown(self):
        document = deepcopy(self.presentation)
        document["authority"]["paper_authorized"] = True
        document = _reseal(document)
        response = self._build(document)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_sealed_response_contains_no_floats(self):
        response = self._build()
        self.assertFalse(_contains_float(response))


if __name__ == "__main__":
    unittest.main()
