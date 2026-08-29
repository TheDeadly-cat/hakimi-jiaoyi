from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_candidate_v8
    as http_v8,
)
from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9
    as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9
    as multi_window_binding,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_v8
    as http_v8_fixture_module,
)
from tests.test_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 import (
    GeometryBudgetMultiWindowPresentationBindingV9Tests,
)


class GeometryBudgetMultiWindowPresentationHttpCandidateV9Tests(
    unittest.TestCase
):
    @staticmethod
    def _rehash(document: dict, field: str, *, external: bool) -> None:
        unsigned = deepcopy(document)
        unsigned.pop(field, None)
        document[field] = sha256(
            json.dumps(
                unsigned,
                ensure_ascii=not external,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8" if external else "ascii")
        ).hexdigest()

    def _bundle(
        self,
        *,
        non_psd: bool = False,
        proposed_notional: int = 2500,
    ) -> dict:
        helper = GeometryBudgetMultiWindowPresentationBindingV9Tests(
            methodName="test_happy_path_is_neutral_outer_blocked_and_unmounted"
        )
        source = helper._bundle(
            non_psd=non_psd,
            proposed_notional=proposed_notional,
        )
        evaluation = helper._evaluate(source)
        request = {
            "schema_version": candidate.REQUEST_SCHEMA_VERSION,
            "geometry_budget_multi_window_presentation_binding_evaluation": (
                evaluation
            ),
            "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash": (
                evaluation["evaluation_hash"]
            ),
        }
        context = {
            "presentation_binding_evaluation": source["presentation_evaluation"],
            "adapter_v7_document": source["adapter"],
            "expected_evaluation_hash": evaluation["evaluation_hash"],
            "expected_presentation_binding_evaluation_hash": source[
                "presentation_evaluation"
            ]["evaluation_hash"],
            "expected_adapter_v7_hash": source["adapter"]["adapter_v7_hash"],
            "presentation_binding_verification_context": source[
                "presentation_context"
            ],
            "adapter_v7_verification_context": source["adapter_context"],
        }
        return {
            "helper": helper,
            "source": source,
            "evaluation": evaluation,
            "request": request,
            "context": context,
        }

    def _build(self, bundle: dict, **overrides: object) -> dict:
        request = overrides.get("request", bundle["request"])
        context = overrides.get("context", bundle["context"])
        with bundle["helper"]._boundaries(bundle["source"]):
            return candidate.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
                request,
                multi_window_binding_verification_context=context,
            )

    def _real_v8_response(self, bundle: dict) -> dict:
        multi_window_document = bundle["evaluation"]["multi_window_document"]
        request = candidate._v8_request(multi_window_document)
        context = candidate._derived_http_v8_verification_context(
            bundle["context"]
        )
        with bundle["helper"]._boundaries(bundle["source"]):
            return http_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8(
                request,
                presentation_verification_context=context,
            )

    def test_dependency_sources_and_contract_are_pinned(self) -> None:
        self.assertEqual(
            sha256(Path(multi_window_binding.__file__).read_bytes()).hexdigest(),
            candidate.MULTI_WINDOW_BINDING_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(http_v8.__file__).read_bytes()).hexdigest(),
            candidate.HTTP_V8_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            multi_window_binding.CONTRACT_HASH,
            candidate._CONTRACT_MANIFEST["multi_window_binding"]["contract_hash"],
        )

    def test_happy_response_is_known_blocked_and_unregistered(self) -> None:
        bundle = self._bundle()
        response = self._build(bundle)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["interface_status"], candidate.INTERFACE_STATUS)
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertEqual(
            response["payload"]["local_decision"]["joint_status"], "PASS"
        )
        self.assertEqual(
            response["lineage"]["multi_window_binding_evaluation_hash"],
            bundle["evaluation"]["evaluation_hash"],
        )
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])
        self.assertFalse(response["authority"]["live_order_allowed"])

    def test_extra_request_key_fails_before_binding_verifier(self) -> None:
        bundle = self._bundle()
        request = deepcopy(bundle["request"])
        request["compatibility_alias"] = True
        with patch.object(
            multi_window_binding,
            "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
        ) as verifier:
            response = self._build(bundle, request=request)
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_extra_context_key_fails_before_binding_verifier(self) -> None:
        bundle = self._bundle()
        context = deepcopy(bundle["context"])
        context["runtime"] = {"forbidden": True}
        with patch.object(
            multi_window_binding,
            "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
        ) as verifier:
            response = self._build(bundle, context=context)
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_missing_binding_evaluation_never_invokes_http_v8(self) -> None:
        bundle = self._bundle()
        request = deepcopy(bundle["request"])
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ] = None
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
        ) as consumer:
            response = self._build(bundle, request=request)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_rehashed_binding_forgery_never_invokes_http_v8(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["evaluation"])
        forged["status"] = "BLOCK"
        self._rehash(forged, "evaluation_hash", external=False)
        request = deepcopy(bundle["request"])
        request[
            "geometry_budget_multi_window_presentation_binding_evaluation"
        ] = forged
        request[
            "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash"
        ] = forged["evaluation_hash"]
        context = deepcopy(bundle["context"])
        context["expected_evaluation_hash"] = forged["evaluation_hash"]
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
        ) as consumer:
            response = self._build(bundle, request=request, context=context)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_non_psd_direct_http_gap_is_blocked_before_http_v8(self) -> None:
        bundle = self._bundle(non_psd=True)
        fixture = http_v8_fixture_module.StratifiedMultiWindowPresentationHttpCandidateV8Tests(
            methodName="test_exact_multi_window_clear_is_known_but_outer_blocked"
        )
        fixture.setUp()
        direct = fixture._build(bundle["source"]["direct_multi_window"])
        self.assertEqual(direct["state"], http_v8.KNOWN_BLOCKED_STATE)
        self.assertIsNotNone(direct["payload"])
        self.assertEqual(bundle["evaluation"]["status"], "BLOCK")
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
        ) as consumer:
            response = self._build(bundle)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_predecessor_block_without_strata_rows_never_invokes_http_v8(
        self,
    ) -> None:
        bundle = self._bundle(proposed_notional=9000)
        self.assertEqual(bundle["evaluation"]["status"], "UNKNOWN")
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
        ) as consumer:
            response = self._build(bundle)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_http_v8_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
            side_effect=RuntimeError("synthetic failure"),
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIn("HTTP_V8_CONSUMER_EXCEPTION", response["blockers"])
        self.assertIsNone(response["payload"])

    def test_rehashed_forged_http_v8_response_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(self._real_v8_response(bundle))
        forged["authority"]["route_registration_allowed"] = True
        self._rehash(forged, "response_hash", external=True)
        with patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
            return_value=forged,
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIn("HTTP_V8_RESPONSE_INVALID", response["blockers"])

    def test_response_exact_verifier_accepts_and_rejects_tamper(self) -> None:
        bundle = self._bundle()
        response = self._build(bundle)
        with bundle["helper"]._boundaries(bundle["source"]):
            self.assertTrue(
                candidate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
                    response,
                    bundle["request"],
                    multi_window_binding_verification_context=bundle["context"],
                )
            )
            tampered = deepcopy(response)
            tampered["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_response_v9(
                    tampered,
                    bundle["request"],
                    multi_window_binding_verification_context=bundle["context"],
                )
            )

    def test_binding_verification_precedes_http_v8_invocation(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_verify = multi_window_binding.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9
        original_http = http_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8

        def observed_verify(*args: object, **kwargs: object) -> dict:
            events.append("binding")
            return original_verify(*args, **kwargs)

        def observed_http(*args: object, **kwargs: object) -> dict:
            events.append("http")
            return original_http(*args, **kwargs)

        with patch.object(
            multi_window_binding,
            "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9",
            side_effect=observed_verify,
        ), patch.object(
            http_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_http_candidate_response_v8",
            side_effect=observed_http,
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(events[0], "binding")
        self.assertLess(events.index("binding"), events.index("http"))


if __name__ == "__main__":
    unittest.main()
