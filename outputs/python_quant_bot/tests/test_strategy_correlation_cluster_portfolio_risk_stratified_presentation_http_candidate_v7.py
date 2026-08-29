from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_candidate_v7
    as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
    as presentation_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _dimension(status: str = "PASS") -> dict:
    return {
        "active_stratum_count": 2,
        "dimension_id": "asset-family",
        "diversification_status": status,
        "dominant_stratum_id": "technology",
        "dominant_stratum_share_of_active_gross_pct": 50.0,
        "gross_limit_status": status,
        "maximum_stratum_gross_pct": 25.0,
        "over_limit_stratum_count": 0 if status == "PASS" else 1,
        "status": status,
        "weighted_effective_strata_count": 2.0,
    }


def _presentation(*, local_status: str = "PASS", source_known: bool = True) -> dict:
    source_state = "EXACT_V6_AND_BUDGET_V3" if source_known else "UNKNOWN"
    dimension_results = [_dimension(local_status)] if source_known else []
    document = {
        "authority": {"live_order_allowed": False},
        "axis_order": list(candidate.AXIS_ORDER),
        "decision": (
            "EXACT_JOINT_LOCAL_CLEAR_PROJECTED_UNMOUNTED"
            if source_known and local_status == "PASS"
            else "EXACT_JOINT_LOCAL_BLOCK_PROJECTED_UNMOUNTED"
            if source_known
            else "UNKNOWN_SOURCE_PROJECTED_UNMOUNTED"
        ),
        "facts": {
            "budget_v3_exactly_verified": source_known,
            "joint_local_research_decision_made": source_known,
            "source_documents_embedded": False,
            "v6_envelope_exactly_verified": source_known,
            "verification_contexts_embedded": False,
        },
        "gaps": {
            "local_blocker_count": 0 if local_status == "PASS" else 1,
            "stratified_budget_blocker_count": 0 if local_status == "PASS" else 1,
        },
        "local_decision": {
            "joint_decision": (
                "PASS_LOCAL_RESEARCH_COMPONENTS"
                if local_status == "PASS"
                else "BLOCK_STRATIFIED_EFFECTIVE_BET_BUDGET"
            ),
            "joint_status": local_status if source_known else "UNKNOWN",
            "portfolio_risk_v6_decision": "PASS_LOCAL_RESEARCH_COMPONENTS",
            "portfolio_risk_v6_status": "PASS" if source_known else "UNKNOWN",
            "stratified_budget_decision": (
                "PASS_PREREGISTERED_STRATA_EFFECTIVE_BET_BUDGET"
                if local_status == "PASS"
                else "BLOCK_PREREGISTERED_STRATA_EFFECTIVE_BET_BUDGET"
            ),
            "stratified_budget_status": local_status if source_known else "UNKNOWN",
        },
        "policy": {"risk_reduction_is_not_execution_authority": True},
        "risk_summary": {
            "active_dimension_count": 1 if source_known else None,
            "conservative_weighted_effective_strata_count": 2.0 if source_known else None,
            "dimension_results": dimension_results,
            "maximum_active_stratum_gross_pct": 25.0 if source_known else None,
            "total_active_gross_pct": 50.0 if source_known else None,
            "v2_weighted_effective_cluster_count": 2.0 if source_known else None,
            "weighted_diversification_gate_applied": True if source_known else None,
        },
        "schema_version": presentation_v7.SCHEMA_VERSION,
        "source": {"state": source_state},
        "stages": [
            {
                "axis": "SOURCE",
                "detail": source_state,
                "state": "KNOWN" if source_known else "UNKNOWN",
            },
            {
                "axis": "GAP",
                "detail": "LOCAL_RESEARCH_GATES_CLEAR_GOVERNANCE_GAPS_REMAIN",
                "state": "CLEAR_WITH_GOVERNANCE_GAPS",
            },
            {
                "axis": "MATURITY",
                "detail": "UNMOUNTED_PRESENTATION_CANDIDATE",
                "state": "CANDIDATE",
            },
            {
                "axis": "PERMISSION",
                "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
                "state": "NONE",
            },
        ],
        "static_fingerprint": presentation_v7.STATIC_FINGERPRINT,
        "status": "BLOCK",
    }
    return seal_strict_canonical_document(document, "presentation_v7_hash")


def _request(presentation: dict) -> dict:
    return {
        "schema_version": candidate.REQUEST_SCHEMA_VERSION,
        "stratified_presentation_v7_document": presentation,
        "expected_presentation_v7_hash": presentation["presentation_v7_hash"],
    }


def _context() -> dict:
    return {
        "envelope_v6_document": {"fixture": "v6"},
        "budget_v3_document": {"fixture": "budget-v3"},
        "envelope_v6_verification_context": {"fixture": "v6-context"},
        "budget_v3_verification_context": {"fixture": "budget-context"},
    }


def _receipt(presentation: dict, *, valid: bool = True) -> dict:
    return {
        "blockers": [] if valid else ["PRESENTATION_V7_EXACT_REBUILD"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_decision": presentation["decision"] if valid else "UNKNOWN",
        "presentation_status": "BLOCK" if valid else "UNKNOWN",
        "presentation_v7_hash": presentation["presentation_v7_hash"] if valid else None,
        "runtime_gate_activation_allowed": False,
        "schema_version": presentation_v7.VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if valid else "BLOCK",
        "writer_allowed": False,
    }


def _contains_float(value) -> bool:
    if type(value) is float:
        return True
    if type(value) is list:
        return any(_contains_float(item) for item in value)
    if type(value) is dict:
        return any(_contains_float(item) for item in value.values())
    return False


class StratifiedPresentationHttpCandidateV7Tests(unittest.TestCase):
    def _build(self, presentation: dict, *, receipt: dict | None = None) -> dict:
        expected_receipt = receipt if receipt is not None else _receipt(presentation)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=expected_receipt):
            return candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                _request(presentation),
                presentation_verification_context=_context(),
            )

    def test_exact_local_clear_is_known_but_outer_blocked(self):
        presentation = _presentation()
        response = self._build(presentation)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "PASS")
        self.assertEqual(
            response["payload"]["risk_summary"]["conservative_weighted_effective_strata_count"],
            "2",
        )
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])
        self.assertFalse(response["authority"]["live_order_allowed"])
        self.assertFalse(_contains_float(response))

    def test_budget_block_overrides_local_clear_and_remains_visible(self):
        presentation = _presentation(local_status="BLOCK")
        response = self._build(presentation)
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "BLOCK")
        self.assertIn("LOCAL_RESEARCH_GATE_BLOCKED", response["blockers"])
        self.assertEqual(response["payload"]["risk_summary"]["dimension_results"][0]["status"], "BLOCK")

    def test_exact_unknown_source_hides_all_partial_metrics(self):
        presentation = _presentation(source_known=False)
        response = self._build(presentation)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        self.assertIsNone(response["lineage"]["presentation_v7_hash"])
        self.assertFalse(response["facts"]["result_available"])

    def test_extra_request_key_fails_before_verifier(self):
        presentation = _presentation()
        request = _request(presentation)
        request["route"] = "/forbidden"
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                request,
                presentation_verification_context=_context(),
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_substituted_expected_hash_fails_closed(self):
        presentation = _presentation()
        request = _request(presentation)
        request["expected_presentation_v7_hash"] = "0" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                request,
                presentation_verification_context=_context(),
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_malformed_verification_receipt_cannot_unlock_payload(self):
        presentation = _presentation()
        receipt = _receipt(presentation)
        receipt["route_registered"] = False
        response = self._build(presentation, receipt=receipt)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_response_exact_rebuild_detects_mutation(self):
        presentation = _presentation()
        request = _request(presentation)
        context = _context()
        receipt = _receipt(presentation)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                request,
                presentation_verification_context=context,
            )
            self.assertTrue(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                    response,
                    request,
                    presentation_verification_context=context,
                )
            )
            mutated = deepcopy(response)
            mutated["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                    mutated,
                    request,
                    presentation_verification_context=context,
                )
            )

    def test_context_shape_is_exact(self):
        presentation = _presentation()
        context = _context()
        context["runtime"] = {"forbidden": True}
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                _request(presentation),
                presentation_verification_context=context,
            )
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])


if __name__ == "__main__":
    unittest.main()
