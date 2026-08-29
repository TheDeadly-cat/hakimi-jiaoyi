from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_candidate_v7 as http_v7,
)
from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_presentation_http_candidate_v8 as candidate,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as presentation_binding,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_v7 as http_v7_fixture_module,
)
from tests import (
    test_strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as presentation_binding_fixture_module,
)


class StrategyCorrelationMatrixGeometryBudgetPresentationHttpCandidateV8Tests(
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
        helper = presentation_binding_fixture_module.StrategyCorrelationMatrixGeometryBudgetPresentationBindingTests(
            methodName="test_happy_path_preserves_neutral_presentation_and_zero_authority"
        )
        presentation_bundle = helper._bundle(
            non_psd=non_psd,
            proposed_notional=proposed_notional,
        )
        presentation_evaluation = helper._evaluate(presentation_bundle)
        request = {
            "schema_version": candidate.REQUEST_SCHEMA_VERSION,
            "geometry_budget_presentation_binding_evaluation": (
                presentation_evaluation
            ),
            "expected_geometry_budget_presentation_binding_evaluation_hash": (
                presentation_evaluation["evaluation_hash"]
            ),
        }
        context = {
            "presentation_binding_preregistration": presentation_bundle[
                "presentation_preregistration"
            ],
            "budget_binding_preregistration": presentation_bundle[
                "budget_preregistration"
            ],
            "budget_binding_evaluation": presentation_bundle["budget_evaluation"],
            "envelope_v6_document": presentation_bundle["envelope"],
            "expected_evaluation_hash": presentation_evaluation["evaluation_hash"],
            "expected_presentation_binding_preregistration_hash": presentation_bundle[
                "presentation_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_preregistration_hash": presentation_bundle[
                "budget_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_evaluation_hash": presentation_bundle[
                "budget_evaluation"
            ]["evaluation_hash"],
            "budget_binding_verification_context": presentation_bundle[
                "budget_context"
            ],
            "envelope_v6_verification_context": presentation_bundle[
                "envelope_context"
            ],
        }
        return {
            "helper": helper,
            "presentation_bundle": presentation_bundle,
            "presentation_evaluation": presentation_evaluation,
            "request": request,
            "context": context,
        }

    def _build(self, bundle: dict, **overrides: object) -> dict:
        request = overrides.get("request", bundle["request"])
        context = overrides.get("context", bundle["context"])
        with bundle["helper"]._envelope_boundary(bundle["presentation_bundle"]):
            return candidate.build_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
                request,
                presentation_binding_verification_context=context,
            )

    def _real_v7_response(self, bundle: dict) -> dict:
        presentation = bundle["presentation_evaluation"]["presentation_document"]
        v7_request = candidate._v7_request(presentation)
        v7_context = candidate._derived_presentation_verification_context(
            bundle["context"]
        )
        with bundle["helper"]._envelope_boundary(bundle["presentation_bundle"]):
            return http_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7(
                v7_request,
                presentation_verification_context=v7_context,
            )

    def test_dependency_sources_and_contract_are_pinned(self) -> None:
        self.assertEqual(
            sha256(Path(presentation_binding.__file__).read_bytes()).hexdigest(),
            candidate.PRESENTATION_BINDING_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(http_v7.__file__).read_bytes()).hexdigest(),
            candidate.HTTP_V7_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            presentation_binding.BINDING_CONTRACT_HASH,
            candidate._CONTRACT_MANIFEST["presentation_binding"]["contract_hash"],
        )

    def test_happy_response_is_known_blocked_and_unregistered(self) -> None:
        response = self._build(self._bundle())
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["interface_status"], candidate.INTERFACE_STATUS)
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "PASS")
        self.assertFalse(response["authority"]["route_registration_allowed"])
        self.assertFalse(response["authority"]["paper_authorized"])
        self.assertFalse(response["authority"]["live_order_allowed"])

    def test_extra_request_key_fails_before_binding_verifier(self) -> None:
        bundle = self._bundle()
        request = deepcopy(bundle["request"])
        request["compatibility_alias"] = True
        with patch.object(
            presentation_binding,
            "verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1",
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
            presentation_binding,
            "verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1",
        ) as verifier:
            response = self._build(bundle, context=context)
        verifier.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_missing_presentation_binding_evaluation_never_invokes_http_v7(self) -> None:
        bundle = self._bundle()
        request = deepcopy(bundle["request"])
        request["geometry_budget_presentation_binding_evaluation"] = None
        with patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
        ) as consumer:
            response = self._build(bundle, request=request)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_rehashed_binding_evaluation_forgery_never_invokes_http_v7(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["presentation_evaluation"])
        forged["status"] = "BLOCK"
        self._rehash(forged, "evaluation_hash", external=False)
        request = deepcopy(bundle["request"])
        request["geometry_budget_presentation_binding_evaluation"] = forged
        request[
            "expected_geometry_budget_presentation_binding_evaluation_hash"
        ] = forged["evaluation_hash"]
        context = deepcopy(bundle["context"])
        context["expected_evaluation_hash"] = forged["evaluation_hash"]
        with patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
        ) as consumer:
            response = self._build(bundle, request=request, context=context)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)

    def test_non_psd_direct_http_gap_is_blocked_before_http_v7(self) -> None:
        bundle = self._bundle(non_psd=True)
        http_fixture = http_v7_fixture_module.StratifiedPresentationHttpCandidateV7Tests(
            methodName="test_exact_local_clear_is_known_but_outer_blocked"
        )
        direct = http_fixture._build(
            bundle["presentation_bundle"]["direct_presentation"]
        )
        self.assertEqual(direct["state"], http_v7.KNOWN_BLOCKED_STATE)
        self.assertEqual(direct["payload"]["local_decision"]["joint_status"], "PASS")
        with patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
        ) as consumer:
            response = self._build(bundle)
        consumer.assert_not_called()
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIsNone(response["payload"])

    def test_verified_budget_block_remains_known_blocked(self) -> None:
        bundle = self._bundle(proposed_notional=9000)
        response = self._build(bundle)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(response["payload"]["status"], "BLOCK")
        self.assertEqual(response["payload"]["local_decision"]["joint_status"], "BLOCK")

    def test_http_v7_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
            side_effect=RuntimeError("synthetic failure"),
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIn("HTTP_V7_CONSUMER_EXCEPTION", response["blockers"])
        self.assertIsNone(response["payload"])

    def test_rehashed_forged_http_v7_response_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = self._real_v7_response(bundle)
        forged = deepcopy(forged)
        forged["authority"]["route_registration_allowed"] = True
        self._rehash(forged, "response_hash", external=True)
        with patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
            return_value=forged,
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.UNKNOWN_STATE)
        self.assertIn("HTTP_V7_RESPONSE_INVALID", response["blockers"])

    def test_response_exact_verifier_accepts_and_rejects_tamper(self) -> None:
        bundle = self._bundle()
        response = self._build(bundle)
        with bundle["helper"]._envelope_boundary(bundle["presentation_bundle"]):
            self.assertTrue(
                candidate.verify_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
                    response,
                    bundle["request"],
                    presentation_binding_verification_context=bundle["context"],
                )
            )
            tampered = deepcopy(response)
            tampered["authority"]["paper_authorized"] = True
            self.assertFalse(
                candidate.verify_strategy_correlation_matrix_geometry_budget_presentation_http_candidate_response_v8(
                    tampered,
                    bundle["request"],
                    presentation_binding_verification_context=bundle["context"],
                )
            )

    def test_binding_verification_precedes_http_v7_invocation(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_verify = (
            presentation_binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1
        )
        original_http = (
            http_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7
        )

        def observed_verify(*args: object, **kwargs: object) -> bool:
            events.append("binding")
            return original_verify(*args, **kwargs)

        def observed_http(*args: object, **kwargs: object) -> dict:
            events.append("http")
            return original_http(*args, **kwargs)

        with patch.object(
            presentation_binding,
            "verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1",
            side_effect=observed_verify,
        ), patch.object(
            http_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_http_candidate_response_v7",
            side_effect=observed_http,
        ):
            response = self._build(bundle)
        self.assertEqual(response["state"], candidate.KNOWN_BLOCKED_STATE)
        self.assertEqual(events[0], "binding")
        self.assertLess(events.index("binding"), events.index("http"))


if __name__ == "__main__":
    unittest.main()
