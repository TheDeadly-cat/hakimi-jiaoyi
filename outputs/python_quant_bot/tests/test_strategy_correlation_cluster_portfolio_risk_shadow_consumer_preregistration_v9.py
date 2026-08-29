from __future__ import annotations

import copy
import inspect
import json
import unittest
from unittest import mock

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
    as subject,
)


def _v8_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "status": "PASS",
        "preregistration_exactly_verified": True,
        "preregistration_status": "BLOCKED",
        "blockers": [],
        "checks": {"exact_rebuild_match": True},
    }


class ShadowConsumerPreregistrationV9Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v8 = {
            "schema_version": subject.preregistration_v8.SCHEMA_VERSION,
            "static_fingerprint": subject.preregistration_v8.STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "contract_state": "KNOWN",
            "preregistration_hash": "1" * 64,
            "contract_pins": {"v8": True},
            "required_shadow_input_schemas": [
                {"input": f"input-{index}", "schema_version": f"v{index}"}
                for index in range(14)
            ],
            "closed_local_blockers": [
                {"blocker": f"closed-{index}", "closure_verified": True}
                for index in range(5)
            ],
            "blocker_refinements": [
                {
                    "source_blocker": "presentation",
                    "remaining_requirements": [
                        subject._HTTP_VERSION_BLOCKER,
                        "presentation_render_descriptor_independent_review_missing",
                    ],
                }
            ],
            "blockers": [
                "provider_trust_unproven",
                subject._HTTP_VERSION_BLOCKER,
                "presentation_render_descriptor_independent_review_missing",
            ],
            "reuse_plan": [{"capability": "V8", "decision": "REUSE"}],
            "activation_order": [
                subject._HTTP_VERSION_ACTIVATION_STEP,
                "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
                "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
            ],
            "facts": {
                "required_shadow_input_count": 14,
                "implementation_pin_count": 39,
                "closed_local_blocker_count": 5,
                "local_evidence_closure_count": 2,
            },
            "authority": {
                "descriptive_only": True,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.request = {
            "schema_version": subject.http_candidate_v3.REQUEST_SCHEMA_VERSION,
            "preregistration_v8_document": self.v8,
            "preregistration_v7_document": {"schema": "v7"},
            "registration_evidence_binding_document": {"schema": "evidence"},
        }
        self.context = {
            "v7_verification_context": {"exact": True},
            "registration_evidence_binding_verification_context": {"exact": True},
            "successor_implementation_sha256": {"exact": "2" * 64},
        }
        self.response = {
            "schema_version": subject.http_candidate_v3.RESPONSE_SCHEMA_VERSION,
            "static_fingerprint": subject.http_candidate_v3.STATIC_FINGERPRINT,
            "interface_status": "UNREGISTERED_CANDIDATE",
            "state": "KNOWN_BLOCKED",
            "response_hash": "3" * 64,
            "payload": {
                "schema_version": subject.http_candidate_v3.PAYLOAD_SCHEMA_VERSION,
                "presentation_status": "UNMOUNTED_HTTP_CANDIDATE",
                "axis_order": list(subject.http_candidate_v3.AXIS_ORDER),
                "stages": [
                    {"axis": axis, "state": "UNAUTHORIZED" if axis == "PERMISSION" else "KNOWN"}
                    for axis in subject.http_candidate_v3.AXIS_ORDER
                ],
                "summary": {
                    "contract_state": "KNOWN",
                    "public_status": "BLOCKED",
                    "implementation_pin_count": 39,
                    "closed_local_blocker_count": 5,
                    "registration_activated": False,
                },
            },
            "facts": {
                "source_preregistration_verified": True,
                "route_registered": False,
                "runtime_mutations_performed": False,
                "profitability_proven": False,
            },
            "lineage": {
                "source_preregistration_hash": self.v8["preregistration_hash"],
                "source_preregistration_implementation_sha256": (
                    subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256[
                        "shadow_preregistration_v8"
                    ]
                ),
                "request_documents_embedded": False,
                "verification_context_embedded": False,
            },
            "transport": {
                "registered": False,
                "externally_callable": False,
                "method": None,
                "route": None,
                "runtime_reads": False,
                "runtime_mutations": False,
                "cache_reads": False,
                "cache_writes": False,
            },
            "authority": {
                "descriptive_only": True,
                "route_registration_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "blockers": ["SOURCE_PREREGISTRATION_BLOCKED"],
        }
        self.response = subject.seal_strict_canonical_document(
            self.response, "response_hash"
        )
        self.manifest = copy.deepcopy(
            subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
        )
        self.v8_verifier = mock.patch.object(
            subject, "_VERIFY_V8", side_effect=_v8_receipt
        )
        self.http_verifier = mock.patch.object(
            subject, "_VERIFY_HTTP_CANDIDATE", return_value=True
        )
        self.v8_verifier.start()
        self.http_verifier.start()
        self.addCleanup(self.v8_verifier.stop)
        self.addCleanup(self.http_verifier.stop)

    def _build(self, **overrides: object):
        arguments = {
            "preregistration_v8_document": self.v8,
            "http_candidate_response": self.response,
            "http_candidate_request": self.request,
            "v8_verification_context": self.context,
            "successor_implementation_sha256": self.manifest,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
            **arguments
        )

    def test_valid_v9_is_known_but_stays_blocked(self) -> None:
        document = self._build()
        self.assertEqual(document["contract_state"], "KNOWN")
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(document["facts"]["presentation_http_contract_v3_versioned"])
        self.assertFalse(document["facts"]["presentation_http_transport_registered"])

    def test_manifest_layers_39_plus_2_as_41(self) -> None:
        document = self._build()
        self.assertEqual(document["facts"]["predecessor_implementation_pin_count"], 39)
        self.assertEqual(document["facts"]["successor_implementation_pin_count"], 2)
        self.assertEqual(document["facts"]["implementation_pin_count"], 41)
        self.assertEqual(
            {item["artifact_id"] for item in document["source"]["new_artifacts"]},
            set(self.manifest),
        )

    def test_http_version_blocker_closes_and_transport_gate_replaces_it(self) -> None:
        document = self._build()
        self.assertNotIn(subject._HTTP_VERSION_BLOCKER, document["blockers"])
        self.assertIn(subject._HTTP_TRANSPORT_BLOCKER, document["blockers"])
        self.assertEqual(len(document["closed_local_blockers"]), 6)
        self.assertEqual(document["facts"]["local_http_contract_closure_count"], 1)

    def test_inputs_and_five_predecessor_closures_are_preserved(self) -> None:
        document = self._build()
        self.assertEqual(
            document["required_shadow_input_schemas"],
            self.v8["required_shadow_input_schemas"],
        )
        self.assertEqual(
            document["closed_local_blockers"][:5],
            self.v8["closed_local_blockers"],
        )

    def test_completed_http_version_step_is_removed_only_when_known(self) -> None:
        document = self._build()
        self.assertNotIn(subject._HTTP_VERSION_ACTIVATION_STEP, document["activation_order"])
        self.assertIn(
            "INDEPENDENTLY_REVIEW_ADR0192_RENDER_DESCRIPTOR",
            document["activation_order"],
        )

    def test_transport_route_mount_current_and_trading_remain_locked(self) -> None:
        document = self._build()
        self.assertFalse(document["facts"]["presentation_http_transport_exercised"])
        self.assertFalse(document["facts"]["server_route_registered"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertTrue(document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_manifest_missing_extra_drift_and_scalar_alias_are_unknown(self) -> None:
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing.pop("shadow_preregistration_v8")
        variants.append(missing)
        extra = copy.deepcopy(self.manifest)
        extra["legacy"] = "4" * 64
        variants.append(extra)
        drift = copy.deepcopy(self.manifest)
        drift["presentation_http_candidate_v3"] = "5" * 64
        variants.append(drift)
        alias = copy.deepcopy(self.manifest)
        alias["shadow_preregistration_v8"] = 1
        variants.append(alias)
        for manifest in variants:
            with self.subTest(manifest=manifest):
                self.assertEqual(
                    self._build(successor_implementation_sha256=manifest)[
                        "contract_state"
                    ],
                    "UNKNOWN",
                )

    def test_context_missing_extra_and_scalar_alias_are_unknown(self) -> None:
        missing = copy.deepcopy(self.context)
        missing.pop("successor_implementation_sha256")
        extra = copy.deepcopy(self.context)
        extra["compatibility_alias"] = {}
        scalar = copy.deepcopy(self.context)
        scalar["v7_verification_context"] = "alias"
        for context in (missing, extra, scalar):
            with self.subTest(context=context):
                self.assertEqual(
                    self._build(v8_verification_context=context)["contract_state"],
                    "UNKNOWN",
                )

    def test_v8_verifier_failure_and_status_promotion_are_unknown(self) -> None:
        with mock.patch.object(
            subject,
            "_VERIFY_V8",
            return_value={"status": "BLOCK", "blockers": ["exact"]},
        ):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")
        promoted = copy.deepcopy(self.v8)
        promoted["status"] = "PASS"
        request = copy.deepcopy(self.request)
        request["preregistration_v8_document"] = promoted
        self.assertEqual(
            self._build(
                preregistration_v8_document=promoted,
                http_candidate_request=request,
            )["contract_state"],
            "UNKNOWN",
        )

    def test_http_verifier_false_and_exception_are_unknown(self) -> None:
        with mock.patch.object(subject, "_VERIFY_HTTP_CANDIDATE", return_value=False):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")
        with mock.patch.object(
            subject, "_VERIFY_HTTP_CANDIDATE", side_effect=ValueError("drift")
        ):
            self.assertEqual(self._build()["contract_state"], "UNKNOWN")

    def test_request_v8_cross_splice_is_unknown(self) -> None:
        request = copy.deepcopy(self.request)
        request["preregistration_v8_document"] = copy.deepcopy(self.v8)
        request["preregistration_v8_document"]["preregistration_hash"] = "6" * 64
        self.assertEqual(
            self._build(http_candidate_request=request)["contract_state"],
            "UNKNOWN",
        )

    def test_response_lineage_cross_splice_is_unknown(self) -> None:
        response = copy.deepcopy(self.response)
        response["lineage"]["source_preregistration_hash"] = "7" * 64
        self.assertEqual(
            self._build(http_candidate_response=response)["contract_state"],
            "UNKNOWN",
        )

    def test_response_hash_tamper_is_unknown_even_if_upstream_accepts(self) -> None:
        response = copy.deepcopy(self.response)
        response["response_hash"] = "8" * 64
        self.assertEqual(
            self._build(http_candidate_response=response)["contract_state"],
            "UNKNOWN",
        )

    def test_transport_or_response_status_promotion_is_unknown(self) -> None:
        routed = copy.deepcopy(self.response)
        routed["transport"]["registered"] = True
        promoted = copy.deepcopy(self.response)
        promoted["state"] = "OBSERVED"
        for response in (routed, promoted):
            with self.subTest(response=response):
                self.assertEqual(
                    self._build(http_candidate_response=response)["contract_state"],
                    "UNKNOWN",
                )

    def test_response_authority_leak_is_unknown(self) -> None:
        response = copy.deepcopy(self.response)
        response["authority"]["route_registration_allowed"] = True
        self.assertEqual(
            self._build(http_candidate_response=response)["contract_state"],
            "UNKNOWN",
        )

    def test_build_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        inputs = copy.deepcopy((self.v8, self.response, self.request, self.context))
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual((self.v8, self.response, self.request, self.context), inputs)

    def test_public_verifier_accepts_rebuild_and_rejects_tamper(self) -> None:
        document = self._build()
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
            document,
            self.v8,
            self.response,
            self.request,
            v8_verification_context=self.context,
            successor_implementation_sha256=self.manifest,
        )
        self.assertEqual(receipt["status"], "PASS")
        tampered = copy.deepcopy(document)
        tampered["facts"]["server_route_registered"] = True
        rejected = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
            tampered,
            self.v8,
            self.response,
            self.request,
            v8_verification_context=self.context,
            successor_implementation_sha256=self.manifest,
        )
        self.assertEqual(rejected["status"], "BLOCK")

    def test_actual_v8_and_http_candidate_build_known_blocked_v9(self) -> None:
        from exchange_terminal.interfaces.http import (
            strategy_correlation_cluster_portfolio_risk_presentation_candidate_v3
            as candidate,
        )
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
                "schema_version": candidate.REQUEST_SCHEMA_VERSION,
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
                candidate,
                "_VERIFY_V8",
                v8_module.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8,
            ):
                response = candidate.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3(
                    request,
                    v8_verification_context=context,
                )
            with mock.patch.object(
                subject,
                "_VERIFY_V8",
                v8_module.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8,
            ), mock.patch.object(
                subject,
                "_VERIFY_HTTP_CANDIDATE",
                candidate.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v3,
            ):
                document = subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
                    v8_document,
                    response,
                    request,
                    v8_verification_context=context,
                    successor_implementation_sha256=dict(
                        subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
                    ),
                )
                verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9(
                    document,
                    v8_document,
                    response,
                    request,
                    v8_verification_context=context,
                    successor_implementation_sha256=dict(
                        subject.EXPECTED_SUCCESSOR_IMPLEMENTATION_SHA256
                    ),
                )
        finally:
            case.doCleanups()
        self.assertEqual(document["contract_state"], "KNOWN")
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(document["facts"]["implementation_pin_count"], 41)
        self.assertFalse(document["facts"]["presentation_http_transport_registered"])

    def test_api_and_source_have_no_route_runtime_browser_or_ready_promotion(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
        )
        self.assertEqual(
            tuple(signature.parameters),
            (
                "preregistration_v8_document",
                "http_candidate_response",
                "http_candidate_request",
                "v8_verification_context",
                "successor_implementation_sha256",
            ),
        )
        source = inspect.getsource(subject)
        self.assertNotIn("runtime/", source.lower())
        self.assertNotIn("selenium", source.lower())
        self.assertNotIn("playwright", source.lower())
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        self.assertNotIn(forbidden, json.dumps(self._build(), sort_keys=True).upper())


if __name__ == "__main__":
    unittest.main()
