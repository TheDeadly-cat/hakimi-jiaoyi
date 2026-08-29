from __future__ import annotations

from contextlib import contextmanager, ExitStack
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7 as adapter_v7,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as multi_window_v8,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9 as binding,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as presentation_binding,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as multi_window_fixture_module,
)
from tests import (
    test_strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as presentation_fixture_module,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7 as adapter_fixture_module


class GeometryBudgetMultiWindowPresentationBindingV9Tests(unittest.TestCase):
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
        presentation_helper = presentation_fixture_module.StrategyCorrelationMatrixGeometryBudgetPresentationBindingTests(
            methodName="test_happy_path_preserves_neutral_presentation_and_zero_authority"
        )
        presentation_bundle = presentation_helper._bundle(
            non_psd=non_psd,
            proposed_notional=proposed_notional,
        )
        presentation_evaluation = presentation_helper._evaluate(presentation_bundle)
        budget_case = presentation_bundle["budget_case"]
        budget_context_source = presentation_bundle["budget_context"]
        anchor_budget = presentation_bundle["direct_budget"]
        anchor_context = {
            "preregistration": budget_case.preregistration,
            "correlation_matrix": budget_case.matrix,
            "complete_link_audit": budget_case.audit,
            "strata_registration": budget_context_source["strata_registration"],
            "strata_gate": budget_context_source["strata_gate"],
            "complete_link_gate": budget_case.complete_link_gate,
            "equity": budget_context_source["equity"],
            "positions": budget_context_source["positions"],
            "proposed_symbol": budget_context_source["proposed_symbol"],
            "proposed_notional": budget_context_source["proposed_notional"],
            "proposed_direction": budget_context_source["proposed_direction"],
            "max_cluster_gross_pct": budget_context_source[
                "max_cluster_gross_pct"
            ],
            "risk_increasing": budget_context_source["risk_increasing"],
        }
        adapter_case = adapter_fixture_module.StratifiedMultiWindowAdapterV7Tests(
            methodName="test_exact_anchor_and_stable_gate_pass_research_only"
        )
        adapter_case.setUp()
        gate_fixture = adapter_case.gate_fixture
        contexts = {"anchor": deepcopy(anchor_context)}
        documents = {"anchor": anchor_budget}
        for window_id, lookback, matrix_digit in (
            ("short", 20, "1"),
            ("long", 120, "3"),
        ):
            context = deepcopy(anchor_context)
            context["correlation_matrix"]["lookback_observations"] = lookback
            context["correlation_matrix"]["matrix_hash"] = matrix_digit * 64
            context["complete_link_audit"]["matrix_hash"] = matrix_digit * 64
            contexts[window_id] = context
            documents[window_id] = gate_fixture._budget(context)
        stability_gate = gate_fixture._evaluate(
            documents=documents,
            contexts=contexts,
        )
        stability_context = adapter_case._gate_context(documents, contexts)
        adapter = adapter_case._evaluate(
            anchor_document=anchor_budget,
            anchor_context=anchor_context,
            gate_document=stability_gate,
            gate_context=stability_context,
        )

        presentation_context = {
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
        adapter_context = {
            "stability_gate_v2_document": stability_gate,
            "stability_gate_v2_verification_context": stability_context,
            "risk_increasing": True,
        }
        multi_window_case = multi_window_fixture_module.StratifiedMultiWindowPresentationV8Tests(
            methodName="test_two_exact_clear_components_remain_outer_blocked_and_unmounted"
        )
        multi_window_case.setUp()
        direct_presentation_context = {
            "budget_v3_document": anchor_budget,
            "budget_v3_verification_context": anchor_context,
            "envelope_v6_document": {},
            "envelope_v6_verification_context": {},
        }
        direct_adapter_context = {
            "anchor_budget_v3_document": anchor_budget,
            "anchor_budget_v3_verification_context": anchor_context,
            "risk_increasing": True,
            "stability_gate_v2_document": stability_gate,
            "stability_gate_v2_verification_context": stability_context,
        }
        direct_multi_window = multi_window_case._build(
            presentation=presentation_bundle["direct_presentation"],
            adapter=adapter,
            presentation_context=direct_presentation_context,
            adapter_context=direct_adapter_context,
        )
        return {
            "presentation_helper": presentation_helper,
            "presentation_bundle": presentation_bundle,
            "presentation_evaluation": presentation_evaluation,
            "presentation_context": presentation_context,
            "adapter_case": adapter_case,
            "adapter": adapter,
            "adapter_context": adapter_context,
            "direct_multi_window": direct_multi_window,
        }

    @contextmanager
    def _boundaries(self, bundle: dict):
        def verify_budget(document, *_args, **_kwargs):
            return bundle["adapter_case"]._budget_receipt(document)

        def verify_gate(document, *_args, **_kwargs):
            return bundle["adapter_case"]._gate_receipt(document)

        with ExitStack() as stack:
            stack.enter_context(
                bundle["presentation_helper"]._envelope_boundary(
                    bundle["presentation_bundle"]
                )
            )
            stack.enter_context(
                patch.object(
                    adapter_v7,
                    "_VERIFY_BUDGET_V3",
                    side_effect=verify_budget,
                )
            )
            stack.enter_context(
                patch.object(
                    adapter_v7,
                    "_VERIFY_STABILITY_GATE_V2",
                    side_effect=verify_gate,
                )
            )
            yield

    def _evaluate(self, bundle: dict, **overrides: object) -> dict:
        values = {
            "presentation_binding_evaluation": bundle["presentation_evaluation"],
            "adapter_v7_document": bundle["adapter"],
            "expected_presentation_binding_evaluation_hash": bundle[
                "presentation_evaluation"
            ]["evaluation_hash"],
            "expected_adapter_v7_hash": bundle["adapter"]["adapter_v7_hash"],
            "presentation_binding_verification_context": bundle[
                "presentation_context"
            ],
            "adapter_v7_verification_context": bundle["adapter_context"],
        }
        values.update(overrides)
        with self._boundaries(bundle):
            return binding.evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
                values["presentation_binding_evaluation"],
                values["adapter_v7_document"],
                expected_presentation_binding_evaluation_hash=values[
                    "expected_presentation_binding_evaluation_hash"
                ],
                expected_adapter_v7_hash=values["expected_adapter_v7_hash"],
                presentation_binding_verification_context=values[
                    "presentation_binding_verification_context"
                ],
                adapter_v7_verification_context=values[
                    "adapter_v7_verification_context"
                ],
            )

    def test_dependency_sources_and_contract_are_pinned(self) -> None:
        self.assertEqual(
            sha256(Path(presentation_binding.__file__).read_bytes()).hexdigest(),
            binding.PRESENTATION_BINDING_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(adapter_v7.__file__).read_bytes()).hexdigest(),
            binding.ADAPTER_V7_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(multi_window_v8.__file__).read_bytes()).hexdigest(),
            binding.MULTI_WINDOW_V8_IMPLEMENTATION_SHA256,
        )

    def test_happy_path_is_neutral_outer_blocked_and_unmounted(self) -> None:
        result = self._evaluate(self._bundle())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["multi_window_verified"])
        self.assertEqual(result["multi_window_status"], "BLOCK")
        self.assertEqual(result["axis_order"], list(binding.NEUTRAL_AXIS_ORDER))
        self.assertFalse(result["mounted"])
        self.assertFalse(result["facts"]["ui_mounted"])
        self.assertFalse(result["facts"]["http_candidate_registered"])
        self.assertFalse(result["authority"]["paper_authorized"])
        self.assertFalse(result["authority"]["live_order_allowed"])

    def test_exact_verifier_accepts_and_rejects_tamper(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        with self._boundaries(bundle):
            receipt = binding.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
                result,
                bundle["presentation_evaluation"],
                bundle["adapter"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_presentation_binding_evaluation_hash=bundle[
                    "presentation_evaluation"
                ]["evaluation_hash"],
                expected_adapter_v7_hash=bundle["adapter"]["adapter_v7_hash"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        self.assertEqual(receipt["status"], "PASS")
        tampered = deepcopy(result)
        tampered["authority"]["paper_authorized"] = True
        with self._boundaries(bundle):
            receipt = binding.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
                tampered,
                bundle["presentation_evaluation"],
                bundle["adapter"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_presentation_binding_evaluation_hash=bundle[
                    "presentation_evaluation"
                ]["evaluation_hash"],
                expected_adapter_v7_hash=bundle["adapter"]["adapter_v7_hash"],
                presentation_binding_verification_context=bundle[
                    "presentation_context"
                ],
                adapter_v7_verification_context=bundle["adapter_context"],
            )
        self.assertEqual(receipt["status"], "BLOCK")

    def test_missing_presentation_binding_never_invokes_adapter_or_multi_window(self) -> None:
        bundle = self._bundle()
        with patch.object(adapter_v7, "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7") as adapter_verify, patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
        ) as consumer:
            result = self._evaluate(
                bundle,
                presentation_binding_evaluation=None,
            )
        adapter_verify.assert_not_called()
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")

    def test_context_aliases_fail_before_multi_window(self) -> None:
        bundle = self._bundle()
        presentation_context = deepcopy(bundle["presentation_context"])
        presentation_context["compatibility_alias"] = True
        adapter_context = deepcopy(bundle["adapter_context"])
        adapter_context["runtime"] = True
        with patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
        ) as consumer:
            first = self._evaluate(
                bundle,
                presentation_binding_verification_context=presentation_context,
            )
            second = self._evaluate(
                bundle,
                adapter_v7_verification_context=adapter_context,
            )
        consumer.assert_not_called()
        self.assertEqual(first["status"], "UNKNOWN")
        self.assertEqual(second["status"], "UNKNOWN")

    def test_non_psd_direct_multi_window_gap_is_blocked_before_adapter(self) -> None:
        bundle = self._bundle(non_psd=True)
        self.assertEqual(bundle["direct_multi_window"]["local_decision"]["joint_status"], "PASS")
        self.assertEqual(bundle["presentation_evaluation"]["status"], "BLOCK")
        with patch.object(
            adapter_v7,
            "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7",
        ) as adapter_verify, patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
        ) as consumer:
            result = self._evaluate(bundle)
        adapter_verify.assert_not_called()
        consumer.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["multi_window_invocation_attempted"])

    def test_predecessor_budget_block_without_strata_rows_remains_unknown(
        self,
    ) -> None:
        bundle = self._bundle(proposed_notional=9000)
        self.assertEqual(bundle["presentation_bundle"]["direct_budget"]["status"], "BLOCK")
        self.assertEqual(
            bundle["presentation_bundle"]["direct_budget"]["portfolio"][
                "dimension_results"
            ],
            [],
        )
        self.assertEqual(
            bundle["adapter_context"]["stability_gate_v2_document"]["status"],
            "UNKNOWN",
        )
        with patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
        ) as consumer:
            result = self._evaluate(bundle)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "ADAPTER_V7_VERIFICATION_FAILED")
        self.assertFalse(result["multi_window_invocation_attempted"])
        self.assertFalse(result["authority"]["current_admission_allowed"])

    def test_rehashed_adapter_forgery_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["adapter"])
        forged["status"] = "BLOCK"
        self._rehash(forged, "adapter_v7_hash", external=True)
        result = self._evaluate(
            bundle,
            adapter_v7_document=forged,
            expected_adapter_v7_hash=forged["adapter_v7_hash"],
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "ADAPTER_V7_DOCUMENT_INVALID")

    def test_adapter_rebuild_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            binding,
            "_PINNED_ADAPTER_EVALUATOR",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "ADAPTER_V7_EXACT_REBUILD_EXCEPTION")

    def test_multi_window_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "MULTI_WINDOW_V8_CONSUMER_EXCEPTION")

    def test_rehashed_multi_window_forgery_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["direct_multi_window"])
        forged["axis_order"] = ["PERMISSION", "MATURITY", "GAP", "SOURCE"]
        self._rehash(forged, "presentation_v8_hash", external=True)
        with patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
            return_value=forged,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "MULTI_WINDOW_V8_DOCUMENT_INVALID")

    def test_presentation_verification_precedes_multi_window_invocation(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_verify = presentation_binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1
        original_build = multi_window_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8

        def observed_verify(*args: object, **kwargs: object) -> bool:
            events.append("presentation")
            return original_verify(*args, **kwargs)

        def observed_build(*args: object, **kwargs: object) -> dict:
            events.append("multi-window")
            return original_build(*args, **kwargs)

        with patch.object(
            presentation_binding,
            "verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1",
            side_effect=observed_verify,
        ), patch.object(
            multi_window_v8,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8",
            side_effect=observed_build,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(events[0], "presentation")
        self.assertLess(events.index("presentation"), events.index("multi-window"))


if __name__ == "__main__":
    unittest.main()
