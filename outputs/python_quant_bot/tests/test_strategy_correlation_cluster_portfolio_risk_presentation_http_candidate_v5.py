from __future__ import annotations

import contextlib
import copy
import hashlib
import inspect
import json
import pathlib
import unittest
from unittest import mock

import exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v4 as v4_source
import exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v5 as subject
import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v5 as adapter_source
import tests.test_strategy_correlation_cluster_portfolio_risk_adapter_v5 as adapter_test_support
import tests.test_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_v4 as v4_test_support
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PresentationHttpCandidateV5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v4_case = v4_test_support.PresentationHttpCandidateV4Tests(
            "test_verified_v10_projects_known_blocked_candidate"
        )
        self.v4_case.setUp()
        self.adapter_case = adapter_test_support.PortfolioRiskAdapterV5Tests(
            "test_both_components_pass_joint_research_gate"
        )
        self.adapter_case.setUp()

        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            mock.patch.object(
                v4_source,
                "_VERIFY_V10",
                side_effect=lambda *args, **kwargs: copy.deepcopy(self.v4_case.receipt),
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                adapter_source,
                self._dependency_name("portfolio_risk_adapter_v4"),
                side_effect=lambda document, *args, **kwargs: (
                    self.adapter_case._adapter_receipt(document)
                ),
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                adapter_source,
                self._dependency_name("multi_window_stability_gate_v1"),
                side_effect=lambda document, *args, **kwargs: (
                    self.adapter_case._stability_receipt(document)
                ),
            )
        )

        self.adapter_document, self.adapter_context = self._adapter_bundle()
        self.request = {
            "schema_version": subject.REQUEST_SCHEMA_VERSION,
            "presentation_candidate_v4_request": copy.deepcopy(self.v4_case.request),
            "portfolio_risk_adapter_v5_document": copy.deepcopy(
                self.adapter_document
            ),
        }

    @staticmethod
    def _dependency_name(token: str) -> str:
        names = []
        for name, value in vars(adapter_source).items():
            module = str(getattr(value, "__module__", ""))
            identity = (name + " " + module).lower()
            if (
                callable(value)
                and "verify" in identity
                and token in identity
                and module != adapter_source.__name__
            ):
                names.append(name)
        unique = sorted(set(names))
        if len(unique) != 1:
            raise AssertionError((token, unique))
        return unique[0]

    def _adapter_bundle(
        self, adapter_status: str = "PASS", stability_status: str = "PASS"
    ) -> tuple[dict, dict]:
        adapter_document = (
            copy.deepcopy(self.adapter_case.adapter_v4)
            if adapter_status == "PASS"
            else self.adapter_case._adapter_v4(adapter_status)
        )
        stability_document = (
            copy.deepcopy(self.adapter_case.stability_gate)
            if stability_status == "PASS"
            else self.adapter_case._stability_gate(stability_status)
        )
        context = {
            "adapter_v4_document": copy.deepcopy(adapter_document),
            "stability_gate_document": copy.deepcopy(stability_document),
            "adapter_v4_verification_context": copy.deepcopy(
                self.adapter_case.adapter_context
            ),
            "stability_gate_verification_context": copy.deepcopy(
                self.adapter_case.stability_context
            ),
        }
        document = adapter_source.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v5(
            copy.deepcopy(adapter_document),
            copy.deepcopy(stability_document),
            adapter_v4_verification_context=copy.deepcopy(
                self.adapter_case.adapter_context
            ),
            stability_gate_verification_context=copy.deepcopy(
                self.adapter_case.stability_context
            ),
        )
        return document, context

    def _build(
        self,
        request: dict | None = None,
        v4_context: dict | None = None,
        adapter_context: dict | None = None,
    ) -> dict:
        return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5(
            copy.deepcopy(self.request if request is None else request),
            v4_verification_context=copy.deepcopy(
                self.v4_case.context if v4_context is None else v4_context
            ),
            adapter_v5_verification_context=copy.deepcopy(
                self.adapter_context if adapter_context is None else adapter_context
            ),
        )

    def _verify(self, document: dict) -> bool:
        return subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5(
            copy.deepcopy(document),
            copy.deepcopy(self.request),
            v4_verification_context=copy.deepcopy(self.v4_case.context),
            adapter_v5_verification_context=copy.deepcopy(self.adapter_context),
        )

    def test_valid_composition_projects_known_blocked_candidate(self) -> None:
        response = self._build()
        self.assertEqual(response["state"], "KNOWN_BLOCKED")
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertTrue(response["facts"]["source_presentation_v4_exactly_verified"])
        self.assertTrue(response["facts"]["portfolio_risk_adapter_v5_exactly_verified"])
        self.assertTrue(response["facts"]["joint_risk_gate_passed"])
        self.assertTrue(self._verify(response))

    def test_adapter_block_is_projected_without_permission_promotion(self) -> None:
        document, context = self._adapter_bundle(adapter_status="BLOCK")
        request = copy.deepcopy(self.request)
        request["portfolio_risk_adapter_v5_document"] = document
        response = self._build(request=request, adapter_context=context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(response["state"], "KNOWN_BLOCKED")
        self.assertFalse(response["facts"]["joint_risk_gate_passed"])
        self.assertEqual(
            response["payload"]["source"]["joint_portfolio_risk"]["status"],
            "BLOCK",
        )
        self.assertFalse(response["payload"]["summary"]["joint_risk_gate_passed"])
        self.assertIn("PORTFOLIO_RISK_ADAPTER_V5_NOT_PASS", response["blockers"])
        self.assertEqual(response["payload"]["stages"][3]["state"], "UNAUTHORIZED")

    def test_payload_uses_neutral_four_axis_order(self) -> None:
        payload = self._build()["payload"]
        self.assertEqual(payload["axis_order"], ["SOURCE", "GAP", "MATURITY", "PERMISSION"])
        self.assertEqual(
            [stage["axis"] for stage in payload["stages"]], payload["axis_order"]
        )
        self.assertEqual(payload["stages"][1]["state"], "PRESENT")
        self.assertEqual(payload["stages"][3]["state"], "UNAUTHORIZED")

    def test_payload_preserves_v4_counts_and_adds_calibrated_joint_facts(self) -> None:
        v4_response = self.v4_case._build()
        payload = self._build()["payload"]
        count_keys = (
            "required_shadow_input_count",
            "required_presentation_evidence_count",
            "implementation_pin_count",
            "closed_local_blocker_count",
            "remaining_blocker_count",
        )
        for key in count_keys:
            self.assertEqual(payload["summary"][key], v4_response["payload"]["summary"][key])
        self.assertTrue(payload["summary"]["multi_window_stability_gate_verified"])
        self.assertTrue(payload["summary"]["anchor_window_budget_and_context_bound"])
        self.assertTrue(payload["summary"]["trade_identity_cross_bound"])
        self.assertFalse(payload["facts"]["runtime_consumer_bound"])
        self.assertFalse(payload["facts"]["profitability_proven"])

    def test_request_contract_is_exact_and_fail_closed(self) -> None:
        for key in tuple(self.request):
            malformed = copy.deepcopy(self.request)
            malformed.pop(key)
            self.assertEqual(self._build(request=malformed)["state"], "UNKNOWN")
        extra = copy.deepcopy(self.request)
        extra["adapter_v5_status"] = "PASS"
        self.assertEqual(self._build(request=extra)["state"], "UNKNOWN")
        alias = copy.deepcopy(self.request)
        alias["portfolio_risk_adapter_v5_document"] = "PASS"
        self.assertEqual(self._build(request=alias)["state"], "UNKNOWN")

    def test_verification_contexts_are_exact_and_not_aliased(self) -> None:
        for key in tuple(self.adapter_context):
            malformed = copy.deepcopy(self.adapter_context)
            malformed.pop(key)
            self.assertEqual(self._build(adapter_context=malformed)["state"], "UNKNOWN")
        extra_adapter = copy.deepcopy(self.adapter_context)
        extra_adapter["joint_gate_passed"] = True
        self.assertEqual(self._build(adapter_context=extra_adapter)["state"], "UNKNOWN")
        extra_v4 = copy.deepcopy(self.v4_case.context)
        extra_v4["source_verified"] = True
        self.assertEqual(self._build(v4_context=extra_v4)["state"], "UNKNOWN")

    def test_verifier_failure_authority_leak_and_exception_fail_closed(self) -> None:
        with mock.patch.object(subject, "_VERIFY_V4", return_value=False):
            self.assertEqual(self._build()["state"], "UNKNOWN")

        receipt = adapter_source.verify_strategy_correlation_cluster_portfolio_risk_adapter_v5(
            copy.deepcopy(self.adapter_document),
            copy.deepcopy(self.adapter_context["adapter_v4_document"]),
            copy.deepcopy(self.adapter_context["stability_gate_document"]),
            adapter_v4_verification_context=copy.deepcopy(
                self.adapter_context["adapter_v4_verification_context"]
            ),
            stability_gate_verification_context=copy.deepcopy(
                self.adapter_context["stability_gate_verification_context"]
            ),
        )
        leaked = copy.deepcopy(receipt)
        leaked["writer_allowed"] = True
        with mock.patch.object(subject, "_VERIFY_ADAPTER_V5", return_value=leaked):
            self.assertEqual(self._build()["state"], "UNKNOWN")
        with mock.patch.object(subject, "_VERIFY_ADAPTER_V5", side_effect=RuntimeError("x")):
            self.assertEqual(self._build()["state"], "UNKNOWN")

    def test_source_status_fact_and_authority_promotions_are_rejected(self) -> None:
        authority_promoted = copy.deepcopy(self.adapter_document)
        promotable = [
            key for key, value in authority_promoted["authority"].items() if value is False
        ]
        self.assertTrue(promotable)
        authority_promoted["authority"][promotable[0]] = True
        authority_promoted = seal_strict_canonical_document(
            authority_promoted, "adapter_v5_hash"
        )
        request = copy.deepcopy(self.request)
        request["portfolio_risk_adapter_v5_document"] = authority_promoted
        self.assertEqual(self._build(request=request)["state"], "UNKNOWN")

        fact_promoted = copy.deepcopy(self.adapter_document)
        fact_promoted["facts"]["runtime_assets_accessed"] = True
        fact_promoted = seal_strict_canonical_document(fact_promoted, "adapter_v5_hash")
        request["portfolio_risk_adapter_v5_document"] = fact_promoted
        self.assertEqual(self._build(request=request)["state"], "UNKNOWN")

        v4_promoted = self.v4_case._build()
        v4_promoted["transport"]["registered"] = True
        v4_promoted = seal_strict_canonical_document(v4_promoted, "response_hash")
        with mock.patch.object(subject, "_BUILD_V4", return_value=v4_promoted), mock.patch.object(
            subject, "_VERIFY_V4", return_value=True
        ):
            self.assertEqual(self._build()["state"], "UNKNOWN")

    def test_request_documents_and_contexts_are_not_echoed(self) -> None:
        response = self._build()

        def keys(value: object) -> set[str]:
            if isinstance(value, dict):
                found = set(value)
                for item in value.values():
                    found.update(keys(item))
                return found
            if isinstance(value, list):
                found: set[str] = set()
                for item in value:
                    found.update(keys(item))
                return found
            return set()

        forbidden = {
            "presentation_candidate_v4_request",
            "portfolio_risk_adapter_v5_document",
            "adapter_v4_document",
            "stability_gate_document",
            "adapter_v4_verification_context",
            "stability_gate_verification_context",
            "correlation_matrix",
            "positions",
        }
        self.assertTrue(forbidden.isdisjoint(keys(response)))
        self.assertFalse(response["lineage"]["request_documents_embedded"])
        self.assertFalse(response["lineage"]["verification_contexts_embedded"])

    def test_build_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        request = copy.deepcopy(self.request)
        v4_context = copy.deepcopy(self.v4_case.context)
        adapter_context = copy.deepcopy(self.adapter_context)
        snapshots = copy.deepcopy((request, v4_context, adapter_context))
        first = self._build(request, v4_context, adapter_context)
        second = self._build(request, v4_context, adapter_context)
        self.assertEqual(first, second)
        self.assertEqual((request, v4_context, adapter_context), snapshots)

    def test_transport_and_authority_are_permanently_locked(self) -> None:
        response = self._build()
        self.assertEqual(response["transport"]["registered"], False)
        self.assertEqual(response["transport"]["externally_callable"], False)
        self.assertIsNone(response["transport"]["method"])
        self.assertIsNone(response["transport"]["route"])
        self.assertTrue(response["authority"]["descriptive_only"])
        for key, value in response["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self) -> None:
        response = self._build()
        self.assertTrue(self._verify(response))
        tampered = copy.deepcopy(response)
        tampered["payload"]["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "response_hash")
        self.assertFalse(self._verify(tampered))

    def test_dependency_pins_match_current_source_files(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        paths = {
            subject.V4_IMPLEMENTATION_SHA256: pathlib.Path(v4_source.__file__),
            subject.ADAPTER_V5_IMPLEMENTATION_SHA256: pathlib.Path(adapter_source.__file__),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256: (
                root / "exchange_terminal/services/strict_canonical_json_hash.py"
            ),
        }
        for expected, path in paths.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_api_surface_has_no_route_runtime_browser_or_precomputed_inputs(self) -> None:
        signatures = (
            inspect.signature(
                subject.build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5
            ),
            inspect.signature(
                subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5
            ),
        )
        forbidden = (
            "route",
            "runtime",
            "browser",
            "cache",
            "order",
            "paper",
            "live",
            "adapter_v5_status",
            "joint_risk_gate_passed",
        )
        for signature in signatures:
            rendered = str(signature).lower()
            for token in forbidden:
                self.assertNotIn(token, rendered)


if __name__ == "__main__":
    unittest.main()
