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
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


def _document(*, membership_status: str = "PASS") -> dict:
    return {
        "schema_version": candidate.PRESENTATION_SCHEMA_VERSION,
        "static_fingerprint": candidate.PRESENTATION_STATIC_FINGERPRINT,
        "presentation_v11_hash": "a" * 64,
        "status": "BLOCK",
        "decision": "EXACT_PRESENTATION_V11_AUTHORITY_UNCHANGED",
        "authority": {
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "descriptive_only": True,
            "formal_registry_activation_allowed": False,
            "http_candidate_creation_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_only": True,
            "research_only": True,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
        },
        "source": {
            "presentation_v10_hash": "b" * 64,
            "adapter_v10_hash": "c" * 64,
            "membership_gate_v2_hash": "d" * 64,
            "preregistration_hash": "e" * 64,
            "evidence_hash": "f" * 64,
            "scheme_hash": "1" * 64,
        },
        "local_decision": {
            "joint_status": "PASS",
            "joint_decision": "OBSERVE_ONLY",
            "adapter_v10_status": "PASS",
            "common_observation_membership_gate_v2_status": membership_status,
        },
        "risk_summary": {
            "cluster_count": 3,
            "gross_risk_ratio": 0.25,
        },
        "multi_window_summary": {
            "window_count": 2,
            "minimum_window_count": 2,
        },
        "edge_uncertainty_summary": {
            "edge_count": 4,
            "uncertainty_ratio": 0.125,
        },
        "common_observation_summary": {
            "eligible_edge_count": 4,
            "common_observation_count": 12,
        },
        "membership_summary": {
            "all_pair_membership_hashes_match_common": membership_status == "PASS",
            "eligible_edge_count": 4,
            "membership_match_count": 4 if membership_status == "PASS" else 3,
            "pair_commitments": ["secret-pair"],
            "raw_observation_ids": ["obs-1", "obs-2"],
        },
        "facts": {
            "membership_commitment_only": True,
            "raw_observation_identifiers_exposed": False,
            "raw_observation_samples_recomputed": False,
            "presentation_consumer_registered": False,
        },
        "gaps": {
            "presentation_blocker_count": 4,
            "presentation_blockers": list(candidate.PRESENTATION_GOVERNANCE_BLOCKERS),
        },
        "stages": [
            {"axis": "SOURCE", "detail": "PRESENTATION_V11_EXACT", "state": "KNOWN"},
            {"axis": "GAP", "detail": "CONSUMER_ABSENT", "state": "BLOCKED"},
            {"axis": "MATURITY", "detail": "UNMOUNTED", "state": "CANDIDATE"},
            {"axis": "PERMISSION", "detail": "NO_AUTHORITY", "state": "NONE"},
        ],
    }


def _request(document: dict) -> dict:
    return {
        "schema_version": candidate.REQUEST_SCHEMA_VERSION,
        "expected_presentation_v11_hash": document["presentation_v11_hash"],
        "stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11_document": document,
    }


def _context() -> dict:
    return {
        "presentation_v10_document": {"source_hash": "2" * 64},
        "adapter_v10_document": {"source_hash": "3" * 64},
        "presentation_v10_verification_context": {"case": "synthetic"},
        "adapter_v10_verification_context": {"case": "synthetic"},
    }


def _receipt(document: dict, *, valid: bool = True) -> dict:
    result = {
        "schema_version": candidate.PRESENTATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS",
        "blockers": [],
        "presentation_v11_exactly_verified": True,
        "presentation_v11_hash": document["presentation_v11_hash"],
        "presentation_consumer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
    if not valid:
        result["presentation_v11_exactly_verified"] = False
    return result


class MembershipPresentationHttpCandidateV11Tests(unittest.TestCase):
    def test_known_clear_projection_is_still_outer_blocked(self) -> None:
        document = _document()
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=_receipt(document)) as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.KNOWN_STATE)
        self.assertEqual(response["status"], "BLOCK")
        self.assertEqual(response["interface"], "UNREGISTERED_CANDIDATE")
        self.assertFalse(any(response["authority"].values()))
        self.assertIn("membership", response["payload"]["aggregate_summaries"])
        self.assertEqual(
            response["payload"]["gaps"]["source_snapshot"]["gaps"][
                "presentation_blockers"
            ],
            list(candidate.PRESENTATION_GOVERNANCE_BLOCKERS),
        )
        self.assertEqual(
            response["payload"]["gaps"]["candidate_current"]["blockers"],
            response["blockers"],
        )
        self.assertIs(response["payload"]["facts"]["source_gap_snapshot_current"], False)
        verifier.assert_called_once()

    def test_membership_block_remains_visible(self) -> None:
        document = _document(membership_status="BLOCK")
        document["presentation_v11_hash"] = "4" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=_receipt(document)):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.KNOWN_STATE)
        self.assertIn("COMMON_OBSERVATION_MEMBERSHIP_BLOCK", response["blockers"])
        self.assertIn(
            "COMMON_OBSERVATION_MEMBERSHIP_BLOCK",
            response["payload"]["gaps"]["candidate_current"]["blockers"],
        )
        self.assertEqual(
            response["payload"]["local_decision"][
                "common_observation_membership_gate_v2_status"
            ],
            "BLOCK",
        )

    def test_unknown_source_hides_every_summary(self) -> None:
        document = _document()
        document["status"] = "UNKNOWN"
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        self.assertNotIn("aggregate_summaries", response)
        verifier.assert_not_called()

    def test_extra_request_key_fails_before_verifier(self) -> None:
        document = _document()
        request = _request(document)
        request["compatibility"] = True
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                request, presentation_verification_context=_context()
            )
            substituted_document = _document()
            substituted_document["gaps"]["presentation_blockers"][0] = "AAPL"
            substituted_document["presentation_v11_hash"] = "7" * 64
            substituted_response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(substituted_document), presentation_verification_context=_context()
            )
            self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
            self.assertEqual(substituted_response["state"], candidate.UNKNOWN_STATE)
            verifier.assert_not_called()

    def test_substituted_expected_hash_fails_before_verifier(self) -> None:
        document = _document()
        request = _request(document)
        request["expected_presentation_v11_hash"] = "5" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                request, presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_context_shape_is_exact(self) -> None:
        document = _document()
        context = _context()
        context["legacy_adapter"] = {}
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=context
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        verifier.assert_not_called()

    def test_malformed_verification_receipt_fails_closed(self) -> None:
        document = _document()
        receipt = _receipt(document)
        receipt["extra"] = "compatibility"
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_verifier_exception_fails_closed(self) -> None:
        document = _document()
        with patch.object(candidate, "_VERIFY_PRESENTATION", side_effect=RuntimeError("synthetic")):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_response_permission_mutation_breaks_exact_rebuild(self) -> None:
        document = _document()
        request = _request(document)
        context = _context()
        receipt = _receipt(document)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=receipt):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                request, presentation_verification_context=context
            )
            response["payload"]["stages"]["permission"]["status"] = "AUTHORIZED"
            self.assertFalse(
                candidate.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                    response, request, presentation_verification_context=context
                )
            )

    def test_projection_is_bounded_float_free_and_contains_no_raw_membership(self) -> None:
        document = _document()
        document["risk_summary"]["raw_samples"] = [0.1, 0.2]
        document["risk_summary"]["symbol"] = "AAPL"
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=_receipt(document)):
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        payload = response["payload"]
        rendered = json.dumps(payload, sort_keys=True)
        aggregate_rendered = json.dumps(payload["aggregate_summaries"], sort_keys=True)
        self.assertNotIn("secret-pair", rendered)
        self.assertNotIn("obs-1", rendered)
        self.assertNotIn("AAPL", rendered)
        self.assertNotIn("raw_samples", aggregate_rendered)
        self.assertNotIn("raw_observation_ids", aggregate_rendered)
        self.assertEqual(
            payload["gaps"]["source_snapshot"]["gaps"]["presentation_blockers"],
            list(candidate.PRESENTATION_GOVERNANCE_BLOCKERS),
        )
        self.assertNotEqual(
            payload["gaps"]["source_snapshot"]["gaps"]["presentation_blockers"],
            payload["gaps"]["candidate_current"]["blockers"],
        )
        self.assertIs(payload["facts"]["raw_samples_recomputed"], False)
        self.assertIs(payload["facts"]["raw_observation_ids_embedded"], False)

        def has_float(value: object) -> bool:
            if type(value) is float:
                return True
            if isinstance(value, dict):
                return any(has_float(item) for item in value.values())
            if isinstance(value, list):
                return any(has_float(item) for item in value)
            return False

        self.assertFalse(has_float(payload))
        self.assertEqual(
            payload["aggregate_summaries"]["risk"]["gross_risk_ratio"], "0.25"
        )
        unicode_sample = {"schema_version": "synthetic-v1", "label": "哈基米"}
        self.assertTrue(
            strict_json_contract_equal(
                candidate._sealed(unicode_sample),
                seal_strict_canonical_document(unicode_sample, "source_hash"),
            )
        )

    def test_resealed_authority_promotion_is_unknown_before_verifier(self) -> None:
        document = _document()
        document["authority"]["live_order_allowed"] = True
        document["presentation_v11_hash"] = "6" * 64
        with patch.object(candidate, "_VERIFY_PRESENTATION") as verifier:
            response = candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                _request(document), presentation_verification_context=_context()
            )
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])
        verifier.assert_not_called()

    def test_inputs_are_not_mutated(self) -> None:
        document = _document()
        request = _request(document)
        context = _context()
        before_request = copy.deepcopy(request)
        before_context = copy.deepcopy(context)
        with patch.object(candidate, "_VERIFY_PRESENTATION", return_value=_receipt(document)):
            candidate.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_http_candidate_response_v11(
                request, presentation_verification_context=context
            )
        self.assertEqual(request, before_request)
        self.assertEqual(context, before_context)


if __name__ == "__main__":
    unittest.main()
