from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_render_descriptor_review_intake_v1
    as subject,
)


def _v9_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "status": "PASS",
        "preregistration_exactly_verified": True,
        "preregistration_status": "BLOCKED",
        "blockers": [],
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class RenderDescriptorReviewIntakeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.v8 = {
            "preregistration_hash": "1" * 64,
            "source": {
                "evidence_summary_hashes": {
                    "registration_evidence_fixture_descriptor_sha256": "2" * 64
                }
            },
        }
        self.v9 = {
            "schema_version": subject.preregistration_v9.SCHEMA_VERSION,
            "static_fingerprint": subject.preregistration_v9.STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "contract_state": "KNOWN",
            "preregistration_hash": "3" * 64,
            "source": {
                "immutable_v8_preregistration_hash": self.v8[
                    "preregistration_hash"
                ]
            },
            "facts": {
                "presentation_http_contract_v3_versioned": True,
                "presentation_http_transport_registered": False,
                "render_descriptor_independently_reviewed": False,
                "presentation_registration_v1_activated": False,
                "ui_mounted": False,
                "runtime_consumer_bound": False,
                "profitability_proven": False,
            },
            "authority": {
                "descriptive_only": True,
                "http_route_registration_allowed": False,
                "presentation_mount_allowed": False,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.context = {
            "preregistration_v8_document": self.v8,
            "http_candidate_response": {"response_hash": "4" * 64},
            "http_candidate_request": {"schema": "request"},
            "v8_verification_context": {"exact": True},
            "successor_implementation_sha256": {"exact": "5" * 64},
        }
        self.verifier = mock.patch.object(
            subject, "_VERIFY_V9", side_effect=_v9_receipt
        )
        self.verifier.start()
        self.addCleanup(self.verifier.stop)
        self.request = self._request()
        self.claim = {
            "schema_version": subject.CLAIM_SCHEMA_VERSION,
            "review_request_hash": self.request["review_request_hash"],
            "descriptor_sha256": self.request["review_target"][
                "descriptor_sha256"
            ],
            "reviewer_claim_id": "review-claim-alpha",
            "reviewer_process_id": "external-review-process-beta",
            "independence_claimed": True,
            "rubric_results": {
                key: True for key in subject.REVIEW_RUBRIC_KEYS
            },
        }

    def _request(self, **overrides: object):
        arguments = {
            "preregistration_v9_document": self.v9,
            "v9_verification_context": self.context,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
            **arguments
        )

    def _intake(self, **overrides: object):
        arguments = {
            "review_request_document": self.request,
            "review_claim": self.claim,
            "preregistration_v9_document": self.v9,
            "v9_verification_context": self.context,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
            **arguments
        )

    def test_review_request_binds_v9_descriptor_and_http_hashes(self) -> None:
        request = self.request
        self.assertEqual(request["status"], "AWAITING_EXTERNAL_INDEPENDENT_REVIEW")
        self.assertEqual(request["review_target"]["descriptor_sha256"], "2" * 64)
        self.assertEqual(request["review_target"]["preregistration_v9_sha256"], "3" * 64)
        self.assertEqual(request["review_target"]["http_candidate_response_sha256"], "4" * 64)
        self.assertEqual(set(request["rubric"]), set(subject.REVIEW_RUBRIC_KEYS))

    def test_review_request_never_claims_independent_completion(self) -> None:
        self.assertFalse(self.request["facts"]["independent_review_complete"])
        self.assertFalse(self.request["facts"]["reviewer_identity_authenticated"])
        self.assertFalse(self.request["facts"]["attestation_signature_verified"])
        self.assertFalse(self.request["authority"]["review_completion_allowed"])

    def test_request_context_missing_extra_and_scalar_are_unknown(self) -> None:
        missing = copy.deepcopy(self.context)
        missing.pop("http_candidate_response")
        extra = copy.deepcopy(self.context)
        extra["compatibility_alias"] = {}
        scalar = copy.deepcopy(self.context)
        scalar["v8_verification_context"] = "alias"
        for context in (missing, extra, scalar):
            with self.subTest(context=context):
                request = self._request(v9_verification_context=context)
                self.assertEqual(request["status"], "UNKNOWN")
                self.assertIsNone(request["review_target"]["descriptor_sha256"])

    def test_v9_verifier_failure_exception_and_promotion_are_unknown(self) -> None:
        with mock.patch.object(
            subject, "_VERIFY_V9", return_value={"status": "BLOCK", "blockers": []}
        ):
            self.assertEqual(self._request()["status"], "UNKNOWN")
        with mock.patch.object(subject, "_VERIFY_V9", side_effect=ValueError("drift")):
            self.assertEqual(self._request()["status"], "UNKNOWN")
        promoted = copy.deepcopy(self.v9)
        promoted["status"] = "PASS"
        self.assertEqual(
            self._request(preregistration_v9_document=promoted)["status"],
            "UNKNOWN",
        )

    def test_descriptor_hash_missing_or_v8_cross_splice_is_unknown(self) -> None:
        missing = copy.deepcopy(self.context)
        missing["preregistration_v8_document"] = copy.deepcopy(self.v8)
        del missing["preregistration_v8_document"]["source"][
            "evidence_summary_hashes"
        ]["registration_evidence_fixture_descriptor_sha256"]
        splice = copy.deepcopy(self.context)
        splice["preregistration_v8_document"] = copy.deepcopy(self.v8)
        splice["preregistration_v8_document"]["preregistration_hash"] = "6" * 64
        for context in (missing, splice):
            with self.subTest(context=context):
                self.assertEqual(
                    self._request(v9_verification_context=context)["status"],
                    "UNKNOWN",
                )

    def test_malformed_v8_nested_maps_fail_closed_to_unknown(self) -> None:
        malformed_source = copy.deepcopy(self.context)
        malformed_source["preregistration_v8_document"] = copy.deepcopy(self.v8)
        malformed_source["preregistration_v8_document"]["source"] = []
        malformed_evidence = copy.deepcopy(self.context)
        malformed_evidence["preregistration_v8_document"] = copy.deepcopy(self.v8)
        malformed_evidence["preregistration_v8_document"]["source"][
            "evidence_summary_hashes"
        ] = []
        for context in (malformed_source, malformed_evidence):
            with self.subTest(context=context):
                request = self._request(v9_verification_context=context)
                self.assertEqual(request["status"], "UNKNOWN")
                self.assertIsNone(request["review_target"]["descriptor_sha256"])

    def test_request_is_deterministic_verifiable_and_tamper_evident(self) -> None:
        self.assertEqual(self.request, self._request())
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
                self.request,
                self.v9,
                v9_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(self.request)
        tampered["facts"]["independent_review_complete"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
                tampered,
                self.v9,
                v9_verification_context=self.context,
            )
        )

    def test_valid_claim_is_bound_but_remains_unverified(self) -> None:
        intake = self._intake()
        self.assertEqual(
            intake["status"],
            "LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN",
        )
        self.assertEqual(intake["review_state"], "CLAIM_BOUND_UNVERIFIED")
        self.assertTrue(intake["facts"]["review_claim_bound"])
        self.assertFalse(intake["facts"]["independent_review_complete"])

    def test_raw_reviewer_identifiers_and_claim_are_not_embedded(self) -> None:
        intake = self._intake()
        serialized = json.dumps(intake, sort_keys=True)
        self.assertNotIn(self.claim["reviewer_claim_id"], serialized)
        self.assertNotIn(self.claim["reviewer_process_id"], serialized)
        self.assertFalse(intake["source"]["raw_claim_embedded"])
        self.assertRegex(intake["source"]["reviewer_claim_id_sha256"], r"^[0-9a-f]{64}$")

    def test_claim_missing_extra_and_identifier_alias_are_unknown(self) -> None:
        missing = copy.deepcopy(self.claim)
        missing.pop("reviewer_claim_id")
        extra = copy.deepcopy(self.claim)
        extra["signature"] = "forged"
        blank = copy.deepcopy(self.claim)
        blank["reviewer_process_id"] = " "
        numeric = copy.deepcopy(self.claim)
        numeric["reviewer_claim_id"] = 1
        for claim in (missing, extra, blank, numeric):
            with self.subTest(claim=claim):
                self.assertEqual(self._intake(review_claim=claim)["status"], "UNKNOWN")

    def test_claim_hash_cross_splice_and_independence_false_are_unknown(self) -> None:
        request_splice = copy.deepcopy(self.claim)
        request_splice["review_request_hash"] = "7" * 64
        descriptor_splice = copy.deepcopy(self.claim)
        descriptor_splice["descriptor_sha256"] = "8" * 64
        not_independent = copy.deepcopy(self.claim)
        not_independent["independence_claimed"] = False
        for claim in (request_splice, descriptor_splice, not_independent):
            with self.subTest(claim=claim):
                self.assertEqual(self._intake(review_claim=claim)["status"], "UNKNOWN")

    def test_rubric_false_missing_extra_and_bool_alias_are_unknown(self) -> None:
        false_claim = copy.deepcopy(self.claim)
        false_claim["rubric_results"][next(iter(subject.REVIEW_RUBRIC_KEYS))] = False
        missing = copy.deepcopy(self.claim)
        missing["rubric_results"].pop(next(iter(subject.REVIEW_RUBRIC_KEYS)))
        extra = copy.deepcopy(self.claim)
        extra["rubric_results"]["compatibility_alias"] = True
        alias = copy.deepcopy(self.claim)
        alias["rubric_results"][next(iter(subject.REVIEW_RUBRIC_KEYS))] = 1
        for claim in (false_claim, missing, extra, alias):
            with self.subTest(claim=claim):
                self.assertEqual(self._intake(review_claim=claim)["status"], "UNKNOWN")

    def test_request_tamper_prevents_claim_binding(self) -> None:
        request = copy.deepcopy(self.request)
        request["review_target"]["descriptor_sha256"] = "9" * 64
        intake = self._intake(review_request_document=request)
        self.assertEqual(intake["status"], "UNKNOWN")
        self.assertFalse(intake["facts"]["review_request_exactly_verified"])

    def test_malformed_request_review_target_fails_closed_to_unknown(self) -> None:
        request = copy.deepcopy(self.request)
        request["review_target"] = []
        intake = self._intake(review_request_document=request)
        self.assertEqual(intake["status"], "UNKNOWN")
        self.assertFalse(intake["facts"]["review_request_exactly_verified"])
        self.assertFalse(intake["facts"]["review_claim_contract_exact"])

    def test_intake_is_deterministic_verifiable_and_tamper_evident(self) -> None:
        intake = self._intake()
        self.assertEqual(intake, self._intake())
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
                intake,
                self.request,
                self.claim,
                self.v9,
                v9_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(intake)
        tampered["facts"]["independent_review_complete"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
                tampered,
                self.request,
                self.claim,
                self.v9,
                v9_verification_context=self.context,
            )
        )

    def test_all_authority_review_route_mount_current_and_trading_remain_locked(self) -> None:
        for document in (self.request, self._intake()):
            self.assertTrue(document["authority"]["descriptive_only"])
            self.assertTrue(
                all(
                    value is False
                    for key, value in document["authority"].items()
                    if key != "descriptive_only"
                )
            )
            self.assertFalse(document["facts"]["independent_review_complete"])

    def test_v9_implementation_pin_matches_current_file(self) -> None:
        path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9.py"
        )
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.V9_IMPLEMENTATION_SHA256,
        )

    def test_actual_v9_public_verifier_integration_builds_request_and_intake(self) -> None:
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
            as v9_module,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
            as v9_tests,
        )

        case_type = v9_tests.ShadowConsumerPreregistrationV9Tests
        case = case_type(
            methodName=next(name for name in dir(case_type) if name.startswith("test_"))
        )
        case.setUp()
        try:
            case.v8["source"] = {
                "evidence_summary_hashes": {
                    "registration_evidence_fixture_descriptor_sha256": "2" * 64
                }
            }
            v9_document = case._build()
            context = {
                "preregistration_v8_document": case.v8,
                "http_candidate_response": case.response,
                "http_candidate_request": case.request,
                "v8_verification_context": case.context,
                "successor_implementation_sha256": case.manifest,
            }
            with mock.patch.object(
                subject,
                "_VERIFY_V9",
                v9_module.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9,
            ):
                request = subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
                    v9_document,
                    v9_verification_context=context,
                )
                claim = {
                    "schema_version": subject.CLAIM_SCHEMA_VERSION,
                    "review_request_hash": request["review_request_hash"],
                    "descriptor_sha256": request["review_target"]["descriptor_sha256"],
                    "reviewer_claim_id": "external-review-claim",
                    "reviewer_process_id": "external-review-process",
                    "independence_claimed": True,
                    "rubric_results": {
                        key: True for key in subject.REVIEW_RUBRIC_KEYS
                    },
                }
                intake = subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
                    request,
                    claim,
                    v9_document,
                    v9_verification_context=context,
                )
        finally:
            case.doCleanups()
        self.assertEqual(request["status"], "AWAITING_EXTERNAL_INDEPENDENT_REVIEW")
        self.assertEqual(intake["review_state"], "CLAIM_BOUND_UNVERIFIED")
        self.assertFalse(intake["facts"]["independent_review_complete"])

    def test_api_and_source_have_no_signature_runtime_browser_or_ready_promotion(self) -> None:
        request_signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1
        )
        intake_signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1
        )
        self.assertEqual(
            tuple(request_signature.parameters),
            ("preregistration_v9_document", "v9_verification_context"),
        )
        self.assertEqual(
            tuple(intake_signature.parameters),
            (
                "review_request_document",
                "review_claim",
                "preregistration_v9_document",
                "v9_verification_context",
            ),
        )
        source = inspect.getsource(subject)
        self.assertNotIn("selenium", source.lower())
        self.assertNotIn("playwright", source.lower())
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        serialized = json.dumps(self._intake(), sort_keys=True).upper()
        self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
