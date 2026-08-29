from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_presentation_candidate_v4
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_UNSET = object()


class PresentationHttpCandidateV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        authority = {
            "descriptive_only": True,
            "writer_allowed": False,
            "presentation_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        blockers = [
            "provider_trust_unproven",
            "presentation_http_transport_unregistered_and_unexercised",
            "reviewer_real_world_identity_unproven",
            "external_independent_review_not_completed",
            "external_fixture_artifact_attestation_unproven",
            "fixture_execution_process_identity_unproven",
            "fixture_execution_receipt_signature_missing",
            "stylesheet_dom_browser_execution_unproven",
            "presentation_registration_v2_not_activated",
            "runtime_presentation_consumer_unbound",
        ]
        self.v10 = seal_strict_canonical_document(
            {
                "schema_version": subject.preregistration_v10.SCHEMA_VERSION,
                "static_fingerprint": subject.preregistration_v10.STATIC_FINGERPRINT,
                "status": "BLOCKED",
                "contract_state": "KNOWN",
                "decision": "synthetic-v10",
                "source": {},
                "contract_pins": {},
                "required_shadow_input_schemas": [
                    {"input": f"input-{index}", "schema_version": f"v{index}"}
                    for index in range(14)
                ],
                "required_presentation_evidence_schemas": [
                    subject.preregistration_v10.signed_review_v1.EVIDENCE_SCHEMA_VERSION,
                    subject.preregistration_v10.execution_binding_v2.SCHEMA,
                ],
                "closed_local_blockers": [
                    {"blocker": f"closed-{index}", "closure_verified": True}
                    for index in range(8)
                ],
                "blocker_refinements": [],
                "blockers": blockers,
                "reuse_plan": [],
                "activation_order": list(subject.preregistration_v10.ACTIVATION_ORDER),
                "facts": {
                    "implementation_pin_count": 45,
                    "closed_local_blocker_count": 8,
                    "local_evidence_closure_count": 4,
                    "signed_review_claim_cryptographically_verified": True,
                    "reviewed_descriptor_matches_executed_fixture": True,
                    "render_descriptor_independently_reviewed": False,
                    "execution_binding_v2_exactly_verified": True,
                    "consumer_fixture_v4_execution_evidence_bound": True,
                    "external_fixture_artifact_attestation_verified": False,
                    "fixture_execution_process_identity_authenticated": False,
                    "fixture_execution_receipt_signed": False,
                    "presentation_registration_v2_activated": False,
                    "stylesheet_contract_reviewed": False,
                    "dom_contract_reviewed": False,
                    "browser_visual_review_performed": False,
                    "presentation_http_transport_registered": False,
                    "presentation_http_transport_exercised": False,
                    "ui_mounted": False,
                    "runtime_consumer_bound": False,
                    "current_pointer_written": False,
                    "profitability_proven": False,
                },
                "authority": authority,
            },
            "preregistration_hash",
        )
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "preregistration_v10_document": self.v10,
            "preregistration_v9_document": {},
            "signed_review_evidence_document": {},
            "execution_evidence_binding_v2_document": {},
        }
        self.context = {
            "v9_verification_context": {},
            "signed_review_evidence_verification_context": {},
            "execution_binding_verification_context": {},
            "successor_implementation_sha256": {},
        }
        self.receipt = {
            "status": "PASS",
            "preregistration_exactly_verified": True,
            "preregistration_status": "BLOCKED",
            "checks": {
                "exact_rebuild_match": True,
                "known_blocked_state": True,
                "authority_remains_locked": True,
            },
            "blockers": [],
            "writer_allowed": False,
            "http_route_registration_allowed": False,
            "presentation_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _build(
        self,
        request=_UNSET,
        context=_UNSET,
        receipt=_UNSET,
        side_effect=None,
    ):
        with patch.object(
            subject,
            "_VERIFY_V10",
            return_value=copy.deepcopy(
                self.receipt if receipt is _UNSET else receipt
            ),
            side_effect=side_effect,
        ):
            return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
                copy.deepcopy(self.request if request is _UNSET else request),
                v10_verification_context=copy.deepcopy(
                    self.context if context is _UNSET else context
                ),
            )

    def test_verified_v10_projects_known_blocked_candidate(self) -> None:
        response = self._build()
        self.assertEqual(response["state"], subject.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertEqual(response["blockers"], ["SOURCE_PREREGISTRATION_BLOCKED"])
        self.assertTrue(response["facts"]["source_preregistration_verified"])
        self.assertTrue(response["facts"]["signed_review_claim_bound"])
        self.assertTrue(response["facts"]["execution_binding_v2_bound"])
        self.assertFalse(response["facts"]["external_independent_review_completed"])

    def test_payload_uses_neutral_four_axis_order(self) -> None:
        payload = self._build()["payload"]
        self.assertEqual(payload["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in payload["stages"]],
            list(subject.AXIS_ORDER),
        )
        self.assertEqual(payload["stages"][-1]["state"], "UNAUTHORIZED")
        self.assertNotIn("READY", str(payload))

    def test_payload_preserves_v10_counts_and_calibrated_claims(self) -> None:
        summary = self._build()["payload"]["summary"]
        self.assertEqual(summary["required_shadow_input_count"], 14)
        self.assertEqual(summary["required_presentation_evidence_count"], 2)
        self.assertEqual(summary["implementation_pin_count"], 45)
        self.assertEqual(summary["closed_local_blocker_count"], 8)
        self.assertEqual(summary["local_evidence_closure_count"], 4)
        self.assertTrue(summary["signed_review_claim_verified"])
        self.assertFalse(summary["independent_review_completed"])
        self.assertTrue(summary["execution_binding_v2_verified"])
        self.assertTrue(summary["descriptor_cross_binding_verified"])

    def test_transport_and_authority_are_permanently_locked(self) -> None:
        response = self._build()
        self.assertEqual(
            response["transport"],
            {
                "registered": False,
                "externally_callable": False,
                "method": None,
                "route": None,
                "runtime_reads": False,
                "runtime_mutations": False,
                "cache_reads": False,
                "cache_writes": False,
            },
        )
        self.assertTrue(response["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in response["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_request_contract_is_exact_and_fail_closed(self) -> None:
        missing = copy.deepcopy(self.request)
        missing.pop("signed_review_evidence_document")
        extra = copy.deepcopy(self.request)
        extra["route"] = "/forbidden"
        wrong_schema = copy.deepcopy(self.request)
        wrong_schema["schema_version"] = "v3"
        scalar = copy.deepcopy(self.request)
        scalar["preregistration_v10_document"] = []
        for request in (missing, extra, wrong_schema, scalar, None):
            with self.subTest(request=request):
                response = self._build(request=request)
                self.assertEqual(response["state"], subject.UNKNOWN_STATE)
                self.assertIsNone(response["payload"])

    def test_verification_context_is_exact_and_not_aliased(self) -> None:
        missing = copy.deepcopy(self.context)
        missing.pop("v9_verification_context")
        extra = copy.deepcopy(self.context)
        extra["route_context"] = {}
        scalar = copy.deepcopy(self.context)
        scalar["successor_implementation_sha256"] = []
        for context in (missing, extra, scalar, None):
            with self.subTest(context=context):
                self.assertEqual(
                    self._build(context=context)["state"], subject.UNKNOWN_STATE
                )

    def test_verifier_failure_authority_leak_and_exception_fail_closed(self) -> None:
        failed = copy.deepcopy(self.receipt)
        failed["status"] = "BLOCK"
        leaked = copy.deepcopy(self.receipt)
        leaked["presentation_mount_allowed"] = True
        false_check = copy.deepcopy(self.receipt)
        false_check["checks"]["exact_rebuild_match"] = False
        for receipt in (failed, leaked, false_check):
            with self.subTest(receipt=receipt):
                self.assertEqual(
                    self._build(receipt=receipt)["state"], subject.UNKNOWN_STATE
                )
        self.assertEqual(
            self._build(side_effect=RuntimeError("verifier"))["state"],
            subject.UNKNOWN_STATE,
        )

    def test_source_status_fact_and_authority_promotions_are_rejected(self) -> None:
        mutations = []
        status = copy.deepcopy(self.v10)
        status["status"] = "READY"
        mutations.append(status)
        review = copy.deepcopy(self.v10)
        review["facts"]["render_descriptor_independently_reviewed"] = True
        mutations.append(review)
        mounted = copy.deepcopy(self.v10)
        mounted["authority"]["presentation_mount_allowed"] = True
        mutations.append(mounted)
        for document in mutations:
            document = seal_strict_canonical_document(
                {
                    key: value
                    for key, value in document.items()
                    if key != "preregistration_hash"
                },
                "preregistration_hash",
            )
            request = copy.deepcopy(self.request)
            request["preregistration_v10_document"] = document
            with self.subTest(document=document):
                self.assertEqual(self._build(request=request)["state"], subject.UNKNOWN_STATE)

    def test_activation_order_and_evidence_schema_drift_are_rejected(self) -> None:
        activation = copy.deepcopy(self.v10)
        activation["activation_order"] = list(reversed(activation["activation_order"]))
        evidence = copy.deepcopy(self.v10)
        evidence["required_presentation_evidence_schemas"] = ["legacy"]
        for document in (activation, evidence):
            document = seal_strict_canonical_document(
                {
                    key: value
                    for key, value in document.items()
                    if key != "preregistration_hash"
                },
                "preregistration_hash",
            )
            request = copy.deepcopy(self.request)
            request["preregistration_v10_document"] = document
            self.assertEqual(self._build(request=request)["state"], subject.UNKNOWN_STATE)

    def test_request_documents_and_context_are_not_echoed(self) -> None:
        request = copy.deepcopy(self.request)
        request["signed_review_evidence_document"] = {"sentinel": "review-secret"}
        request["execution_evidence_binding_v2_document"] = {
            "sentinel": "binding-secret"
        }
        context = copy.deepcopy(self.context)
        context["signed_review_evidence_verification_context"] = {
            "sentinel": "context-secret"
        }
        rendered = str(self._build(request=request, context=context))
        self.assertNotIn("review-secret", rendered)
        self.assertNotIn("binding-secret", rendered)
        self.assertNotIn("context-secret", rendered)

    def test_build_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        request_before = copy.deepcopy(self.request)
        context_before = copy.deepcopy(self.context)
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(self.request, request_before)
        self.assertEqual(self.context, context_before)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self) -> None:
        response = self._build()
        with patch.object(subject, "_VERIFY_V10", return_value=self.receipt):
            self.assertTrue(
                subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
                    response,
                    self.request,
                    v10_verification_context=self.context,
                )
            )
            tampered = copy.deepcopy(response)
            tampered["payload"]["summary"]["registration_activated"] = True
            tampered = seal_strict_canonical_document(
                {
                    key: value
                    for key, value in tampered.items()
                    if key != "response_hash"
                },
                "response_hash",
            )
            self.assertFalse(
                subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4(
                    tampered,
                    self.request,
                    v10_verification_context=self.context,
                )
            )

    def test_source_implementation_pins_match_current_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        v10_path = root / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v10.py"
        strict_path = root / "exchange_terminal/services/strict_canonical_json_hash.py"
        self.assertEqual(
            hashlib.sha256(v10_path.read_bytes()).hexdigest(),
            subject.V10_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(strict_path.read_bytes()).hexdigest(),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        )

    def test_api_surface_has_no_route_runtime_or_browser_inputs(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4
        )
        self.assertEqual(
            list(signature.parameters),
            ["request_payload", "v10_verification_context"],
        )
        source = inspect.getsource(subject)
        self.assertNotIn('"READY"', source)
        self.assertNotIn("exchange_terminal.server", source)
        self.assertNotIn("from exchange_terminal.services.http_contract", source)
        self.assertNotIn("app.js", source)


if __name__ == "__main__":
    unittest.main()
