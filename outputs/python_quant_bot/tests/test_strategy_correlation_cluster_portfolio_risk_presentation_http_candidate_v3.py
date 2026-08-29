from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest import mock

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_presentation_candidate_v3
    as subject,
)


def _passing_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "status": "PASS",
        "preregistration_exactly_verified": True,
        "preregistration_status": "BLOCKED",
        "blockers": [],
        "checks": {"exact_rebuild_match": True, "authority_locked": True},
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class PortfolioRiskPresentationHttpCandidateV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.v8 = {
            "schema_version": subject.preregistration_v8.SCHEMA_VERSION,
            "static_fingerprint": subject.preregistration_v8.STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "contract_state": "KNOWN",
            "preregistration_hash": "1" * 64,
            "blockers": [
                "provider_trust_unproven",
                "presentation_render_descriptor_independent_review_missing",
                "presentation_consumer_registration_activation_unauthorized",
            ],
            "facts": {
                "local_evidence_closure_count": 2,
                "required_shadow_input_count": 14,
                "implementation_pin_count": 39,
                "closed_local_blocker_count": 5,
                "consumer_fixture_v3_execution_evidence_bound": True,
                "presentation_registration_v1_evidence_bound": True,
                "presentation_registration_v1_activated": False,
                "render_descriptor_independently_reviewed": False,
                "presentation_http_contract_v3_versioned": False,
                "ui_mounted": False,
                "runtime_consumer_bound": False,
                "profitability_proven": False,
            },
            "authority": {
                "descriptive_only": True,
                "presentation_consumer_activation_allowed": False,
                "presentation_mount_allowed": False,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "preregistration_v8_document": self.v8,
            "preregistration_v7_document": {
                "private_marker": "v7-request-secret"
            },
            "registration_evidence_binding_document": {
                "private_marker": "registration-request-secret"
            },
        }
        self.context = {
            "v7_verification_context": {"private_marker": "v7-context-secret"},
            "registration_evidence_binding_verification_context": {
                "private_marker": "registration-context-secret"
            },
            "successor_implementation_sha256": {
                "private_marker": "manifest-context-secret"
            },
        }
        self.verifier = mock.patch.object(
            subject, "_VERIFY_V8", side_effect=_passing_receipt
        )
        self.verifier.start()
        self.addCleanup(self.verifier.stop)

    def _build(self, request: object | None = None, context: object | None = None):
        return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
            self.request if request is None else request,
            v8_verification_context=self.context if context is None else context,
        )

    def test_verified_v8_is_projected_as_known_blocked_candidate(self) -> None:
        response = self._build()
        self.assertEqual(response["state"], subject.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertTrue(response["facts"]["source_preregistration_verified"])
        self.assertTrue(response["facts"]["result_available"])
        self.assertEqual(response["blockers"], ["SOURCE_PREREGISTRATION_BLOCKED"])

    def test_payload_uses_neutral_four_axis_order(self) -> None:
        payload = self._build()["payload"]
        self.assertEqual(payload["axis_order"], list(subject.AXIS_ORDER))
        self.assertEqual(
            [stage["axis"] for stage in payload["stages"]],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(payload["stages"][-1]["state"], "UNAUTHORIZED")
        self.assertEqual(payload["summary"]["public_status"], "BLOCKED")

    def test_payload_preserves_counts_and_remaining_gaps(self) -> None:
        payload = self._build()["payload"]
        self.assertEqual(payload["summary"]["required_shadow_input_count"], 14)
        self.assertEqual(payload["summary"]["implementation_pin_count"], 39)
        self.assertEqual(payload["summary"]["closed_local_blocker_count"], 5)
        self.assertIn(
            "presentation_render_descriptor_independent_review_missing",
            payload["summary"]["remaining_blockers"],
        )
        self.assertFalse(payload["summary"]["registration_activated"])

    def test_transport_is_permanently_unregistered_and_side_effect_free(self) -> None:
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
        self.assertFalse(response["facts"]["route_registered"])

    def test_request_contract_is_exact_and_fail_closed(self) -> None:
        cases = [
            {},
            {**self.request, "unexpected": True},
            {**self.request, "schema_version": "wrong"},
            {**self.request, "preregistration_v8_document": []},
            {**self.request, "preregistration_v7_document": None},
            {**self.request, "registration_evidence_binding_document": "x"},
        ]
        for request in cases:
            with self.subTest(request=request):
                response = self._build(request=request)
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])
                self.assertFalse(response["facts"]["request_contract_valid"])

    def test_verification_context_is_exact_and_not_aliased(self) -> None:
        missing = copy.deepcopy(self.context)
        missing.pop("successor_implementation_sha256")
        extra = copy.deepcopy(self.context)
        extra["compatibility_alias"] = {}
        scalar = copy.deepcopy(self.context)
        scalar["v7_verification_context"] = "alias"
        for context in (missing, extra, scalar):
            with self.subTest(context=context):
                response = self._build(context=context)
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertEqual(response["blockers"], ["VERIFICATION_CONTEXT_INVALID"])

    def test_verifier_failure_and_exception_fail_closed(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_V8",
            return_value={
                "status": "BLOCK",
                "preregistration_exactly_verified": False,
                "blockers": ["exact"],
            },
        ):
            self.assertEqual(self._build()["state"], "UNKNOWN")
        with mock.patch.object(
            subject, "_VERIFY_V8", side_effect=ValueError("synthetic")
        ):
            response = self._build()
            self.assertEqual(response["state"], "UNKNOWN")
            self.assertEqual(
                response["blockers"], ["SOURCE_PREREGISTRATION_VERIFIER_ERROR"]
            )

    def test_unknown_promoted_or_authority_leaking_v8_is_rejected(self) -> None:
        unknown = copy.deepcopy(self.v8)
        unknown["contract_state"] = "UNKNOWN"
        promoted = copy.deepcopy(self.v8)
        promoted["status"] = "PASS"
        leaked = copy.deepcopy(self.v8)
        leaked["authority"]["presentation_mount_allowed"] = True
        for document in (unknown, promoted, leaked):
            request = {**self.request, "preregistration_v8_document": document}
            with self.subTest(document=document):
                response = self._build(request=request)
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])

    def test_request_and_context_values_are_not_echoed(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        for secret in (
            "v7-request-secret",
            "registration-request-secret",
            "v7-context-secret",
            "registration-context-secret",
            "manifest-context-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertFalse(self._build()["lineage"]["request_documents_embedded"])
        self.assertFalse(self._build()["lineage"]["verification_context_embedded"])

    def test_exact_rebuild_is_deterministic_and_tamper_evident(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
                first,
                self.request,
                v8_verification_context=self.context,
            )
        )
        tampered = copy.deepcopy(first)
        tampered["transport"]["registered"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
                tampered,
                self.request,
                v8_verification_context=self.context,
            )
        )

    def test_authority_and_copy_remain_neutral(self) -> None:
        response = self._build()
        self.assertTrue(response["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in response["authority"].items()
                if key != "descriptive_only"
            )
        )
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, json.dumps(response, sort_keys=True).upper())
        self.assertFalse(response["facts"]["profitability_proven"])

    def test_v8_source_hash_pin_matches_current_file(self) -> None:
        path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8.py"
        )
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.V8_IMPLEMENTATION_SHA256,
        )

    def test_candidate_is_absent_from_server_and_common_http_contract(self) -> None:
        identifier = (
            "strategy_correlation_cluster_portfolio_risk_presentation_candidate_v3"
        )
        for path in (
            self.root / "exchange_terminal/server.py",
            self.root / "exchange_terminal/services/http_contract.py",
        ):
            self.assertNotIn(identifier, path.read_text(encoding="utf-8"))

    def test_actual_v8_public_verifier_integration(self) -> None:
        from exchange_terminal.services import (
            strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
            as v8_module,
        )
        from tests import (
            test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8
            as v8_tests,
        )

        case_type = v8_tests.ShadowConsumerPreregistrationV8Tests
        case = case_type(
            methodName=next(name for name in dir(case_type) if name.startswith("test_"))
        )
        case.setUp()
        try:
            v8_document = case._build()
            request = {
                "schema_version": subject.REQUEST_SCHEMA_VERSION,
                "preregistration_v8_document": v8_document,
                "preregistration_v7_document": case.v7,
                "registration_evidence_binding_document": case.registration_evidence,
            }
            context = {
                "v7_verification_context": case.v7_context,
                "registration_evidence_binding_verification_context": (
                    case.evidence_context
                ),
                "successor_implementation_sha256": case.manifest,
            }
            with mock.patch.object(
                subject,
                "_VERIFY_V8",
                v8_module.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8,
            ):
                response = subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
                    request,
                    v8_verification_context=context,
                )
        finally:
            case.doCleanups()
        self.assertEqual(response["state"], "KNOWN_BLOCKED")
        self.assertEqual(response["payload"]["summary"]["implementation_pin_count"], 39)
        self.assertFalse(response["facts"]["transport_registered"])

    def test_api_surface_accepts_no_route_runtime_or_browser_inputs(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3
        )
        self.assertEqual(
            tuple(signature.parameters),
            ("request_payload", "v8_verification_context"),
        )
        self.assertTrue(
            set(signature.parameters).isdisjoint(
                {"route", "runtime", "database", "cache", "browser", "mount"}
            )
        )


if __name__ == "__main__":
    unittest.main()
