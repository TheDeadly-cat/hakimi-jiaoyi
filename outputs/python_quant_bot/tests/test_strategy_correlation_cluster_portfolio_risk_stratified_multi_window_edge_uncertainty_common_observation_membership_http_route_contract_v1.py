from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_candidate_v11
    as candidate,
)
from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_route_contract_v1
    as route_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_v11
    as candidate_test,
)


def _candidate_fixture(*, membership_status: str = "PASS") -> tuple[dict, dict, dict]:
    document = candidate_test._document(membership_status=membership_status)
    request = candidate_test._request(document)
    context = candidate_test._context()
    with patch.object(
        candidate,
        "_VERIFY_PRESENTATION",
        return_value=candidate_test._receipt(document),
    ):
        response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
            request,
            presentation_verification_context=context,
        )
    return response, request, context


def _request(candidate_response: dict) -> dict:
    return {
        "schema_version": route_contract.REQUEST_SCHEMA_VERSION,
        "expected_candidate_v11_hash": candidate_response["source_hash"],
        "candidate_v11_response": candidate_response,
    }


def _context(candidate_request: dict, presentation_context: dict) -> dict:
    return {
        "candidate_v11_request_payload": candidate_request,
        "candidate_v11_presentation_verification_context": presentation_context,
    }


class MembershipHttpRouteContractV1Tests(unittest.TestCase):
    def test_exact_candidate_produces_known_unregistered_route_contract(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        request = _request(candidate_response)
        context = _context(candidate_request, presentation_context)
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=True) as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                request, candidate_verification_context=context
            )
        self.assertEqual(document["state"], route_contract.KNOWN_STATE)
        self.assertEqual(document["status"], "BLOCK")
        self.assertFalse(any(document["authority"].values()))
        self.assertEqual(document["payload"]["transport"]["http_method"], "POST")
        self.assertEqual(
            document["payload"]["transport"]["proposed_route_path"],
            route_contract.PROPOSED_ROUTE_PATH,
        )
        self.assertIs(document["payload"]["transport"]["registered"], False)
        self.assertEqual(document["payload"]["registration_evidence"]["status"], "ABSENT")
        verifier.assert_called_once()

    def test_membership_block_is_preserved_at_current_route_scope(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture(
            membership_status="BLOCK"
        )
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=True):
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertIn("CANDIDATE_V11_MEMBERSHIP_BLOCK", document["blockers"])
        self.assertIn(
            "CANDIDATE_V11_MEMBERSHIP_BLOCK", document["payload"]["blockers"]
        )

    def test_unknown_candidate_hides_route_payload(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        candidate_response["state"] = candidate.UNKNOWN_STATE
        candidate_response.pop("source_hash")
        candidate_response = seal_strict_canonical_document(
            candidate_response, "source_hash"
        )
        with patch.object(route_contract, "_VERIFY_CANDIDATE") as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        self.assertIsNone(document["payload"])
        verifier.assert_not_called()

    def test_extra_request_key_fails_before_candidate_verifier(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        request = _request(candidate_response)
        request["compatibility"] = True
        with patch.object(route_contract, "_VERIFY_CANDIDATE") as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                request,
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_substituted_candidate_hash_fails_before_verifier(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        request = _request(candidate_response)
        request["expected_candidate_v11_hash"] = "0" * 64
        with patch.object(route_contract, "_VERIFY_CANDIDATE") as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                request,
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_candidate_verification_context_shape_is_exact(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        context = _context(candidate_request, presentation_context)
        context["legacy_route"] = {}
        with patch.object(route_contract, "_VERIFY_CANDIDATE") as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response), candidate_verification_context=context
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_candidate_verifier_false_fails_closed(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=False):
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        self.assertIsNone(document["payload"])

    def test_candidate_verifier_exception_fails_closed(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        with patch.object(
            route_contract,
            "_VERIFY_CANDIDATE",
            side_effect=RuntimeError("synthetic"),
        ):
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        self.assertIsNone(document["payload"])

    def test_resealed_candidate_authority_promotion_fails_before_verifier(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        candidate_response["authority"]["live_order_allowed"] = True
        candidate_response.pop("source_hash")
        candidate_response = seal_strict_canonical_document(
            candidate_response, "source_hash"
        )
        with patch.object(route_contract, "_VERIFY_CANDIDATE") as verifier:
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        self.assertEqual(document["state"], route_contract.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_route_contract_embeds_no_candidate_payload_or_context(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=True):
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                _request(candidate_response),
                candidate_verification_context=_context(
                    candidate_request, presentation_context
                ),
            )
        rendered = json.dumps(document["payload"], sort_keys=True)
        self.assertNotIn("aggregate_summaries", rendered)
        self.assertNotIn("presentation_verification_context", rendered)
        self.assertNotIn("candidate_v11_response", rendered)
        self.assertIs(document["payload"]["facts"]["candidate_payload_embedded"], False)

    def test_resealed_route_activation_mutation_fails_exact_rebuild(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        request = _request(candidate_response)
        context = _context(candidate_request, presentation_context)
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=True):
            document = route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                request, candidate_verification_context=context
            )
            document["payload"]["transport"]["registered"] = True
            document["payload"].pop("source_hash")
            document["payload"] = seal_strict_canonical_document(
                document["payload"], "source_hash"
            )
            document.pop("source_hash")
            document = seal_strict_canonical_document(document, "source_hash")
            self.assertFalse(
                route_contract.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                    document,
                    request,
                    candidate_verification_context=context,
                )
            )

    def test_inputs_are_not_mutated(self) -> None:
        candidate_response, candidate_request, presentation_context = _candidate_fixture()
        request = _request(candidate_response)
        context = _context(candidate_request, presentation_context)
        before_request = copy.deepcopy(request)
        before_context = copy.deepcopy(context)
        with patch.object(route_contract, "_VERIFY_CANDIDATE", return_value=True):
            route_contract.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_route_contract_v1(
                request, candidate_verification_context=context
            )
        self.assertEqual(request, before_request)
        self.assertEqual(context, before_context)


if __name__ == "__main__":
    unittest.main()
