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

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1
    as preregistration,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_intake_v1
    as review,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _preregistration() -> dict:
    return preregistration.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1()


def _request(source: dict) -> dict:
    return review.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
        source
    )


def _claim(request: dict) -> dict:
    return {
        "schema_version": review.CLAIM_SCHEMA_VERSION,
        "review_request_hash": request["review_request_hash"],
        "reviewer_claim_id": "external-reviewer-1",
        "reviewer_process_id": "isolated-source-review-1",
        "independence_claimed": True,
        "observed_source_hashes": copy.deepcopy(
            request["review_target"]["source_baseline_pins"]
        ),
        "rubric_results": {key: True for key in review.REVIEW_RUBRIC_KEYS},
    }


def _intake(request: dict, claim: dict, source: dict) -> dict:
    return review.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
        request, claim, source
    )


def _reseal(document: dict, hash_field: str) -> dict:
    result = copy.deepcopy(document)
    result.pop(hash_field, None)
    return seal_strict_canonical_document(result, hash_field)


class MembershipSourceBaselineReviewIntakeV1Tests(unittest.TestCase):
    def test_exact_review_request_awaits_external_review(self) -> None:
        source = _preregistration()
        request = _request(source)
        self.assertEqual(request["status"], "AWAITING_EXTERNAL_INDEPENDENT_REVIEW")
        self.assertEqual(request["review_state"], "REQUESTED_UNAUTHENTICATED")
        self.assertTrue(
            review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
                request, source
            )
        )
        self.assertIs(request["facts"]["source_baseline_authenticated"], False)

    def test_malformed_preregistration_produces_unknown_request(self) -> None:
        source = _preregistration()
        source["status"] = "PASS"
        source = _reseal(source, "preregistration_hash")
        with patch.object(review, "_VERIFY_PREREGISTRATION") as verifier:
            request = _request(source)
        self.assertEqual(request["status"], "UNKNOWN")
        self.assertEqual(request["review_target"]["source_paths"], [])
        verifier.assert_not_called()

    def test_preregistration_verifier_exception_produces_unknown(self) -> None:
        source = _preregistration()
        with patch.object(
            review,
            "_VERIFY_PREREGISTRATION",
            side_effect=RuntimeError("synthetic"),
        ):
            request = _request(source)
        self.assertEqual(request["status"], "UNKNOWN")
        self.assertIn("MOUNT_PREREGISTRATION_UNVERIFIED", request["blockers"])

    def test_review_request_embeds_no_source_content_and_locks_authority(self) -> None:
        request = _request(_preregistration())
        rendered = json.dumps(request, sort_keys=True)
        self.assertNotIn("source_contents", request["review_target"])
        self.assertNotIn("from __future__ import annotations", rendered)
        self.assertNotIn("def create_app", rendered)
        self.assertIs(request["source"]["raw_source_content_embedded"], False)
        self.assertIs(
            request["facts"]["source_content_review_observed_by_system"], False
        )
        self.assertIs(request["authority"]["descriptive_only"], True)
        for key, value in request["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_exact_claim_binds_but_remains_unauthenticated(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        intake = _intake(request, claim, source)
        self.assertEqual(
            intake["status"],
            "LOCAL_SOURCE_BASELINE_REVIEW_CLAIM_BOUND_AUTHENTICATION_ABSENT",
        )
        self.assertEqual(intake["review_state"], "CLAIM_BOUND_UNAUTHENTICATED")
        self.assertIs(intake["facts"]["review_claim_bound"], True)
        self.assertIs(intake["facts"]["source_baseline_authenticated"], False)
        self.assertIs(intake["facts"]["independent_review_complete"], False)
        self.assertTrue(
            review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
                intake, request, claim, source
            )
        )

    def test_observed_hash_mismatch_is_unknown(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        claim["observed_source_hashes"]["server_sha256"] = "0" * 64
        intake = _intake(request, claim, source)
        self.assertEqual(intake["status"], "UNKNOWN")
        self.assertIs(intake["facts"]["review_claim_bound"], False)

    def test_false_rubric_result_is_unknown(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        claim["rubric_results"]["proposed_route_absent_from_server"] = False
        intake = _intake(request, claim, source)
        self.assertEqual(intake["status"], "UNKNOWN")
        self.assertIn("SOURCE_BASELINE_REVIEW_CLAIM_INVALID", intake["blockers"])

    def test_extra_claim_field_is_unknown(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        claim["compatibility"] = True
        intake = _intake(request, claim, source)
        self.assertEqual(intake["status"], "UNKNOWN")

    def test_review_request_hash_substitution_is_unknown(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        claim["review_request_hash"] = "0" * 64
        intake = _intake(request, claim, source)
        self.assertEqual(intake["status"], "UNKNOWN")

    def test_raw_reviewer_identifiers_are_not_embedded(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        intake = _intake(request, claim, source)
        rendered = json.dumps(intake, sort_keys=True)
        self.assertNotIn(claim["reviewer_claim_id"], rendered)
        self.assertNotIn(claim["reviewer_process_id"], rendered)
        self.assertIs(intake["source"]["raw_reviewer_identifiers_embedded"], False)

    def test_resealed_authentication_promotion_fails_exact_rebuild(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        intake = _intake(request, claim, source)
        intake["facts"]["source_baseline_authenticated"] = True
        intake = _reseal(intake, "intake_hash")
        self.assertFalse(
            review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
                intake, request, claim, source
            )
        )

    def test_inputs_are_not_mutated(self) -> None:
        source = _preregistration()
        request = _request(source)
        claim = _claim(request)
        before_source = copy.deepcopy(source)
        before_request = copy.deepcopy(request)
        before_claim = copy.deepcopy(claim)
        _intake(request, claim, source)
        self.assertEqual(source, before_source)
        self.assertEqual(request, before_request)
        self.assertEqual(claim, before_claim)


if __name__ == "__main__":
    unittest.main()
