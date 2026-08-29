from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import strategy_correlation_cluster_gate as cluster_contract
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7 as presentation_v7,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as binding,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_complete_link_binding_v1 as complete_binding,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as budget_binding,
)
from exchange_terminal.services import strategy_correlation_matrix_geometry_gate_v1 as geometry
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from tests import (
    test_strategy_correlation_cluster_effective_bet_budget_v3 as budget_fixture_module,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7 as presentation_fixture_module,
)


class StrategyCorrelationMatrixGeometryBudgetPresentationBindingTests(unittest.TestCase):
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
        budget_case = budget_fixture_module.StrategyCorrelationClusterEffectiveBetBudgetV3Tests(
            methodName="test_balanced_active_exposure_in_separate_strata_passes"
        )
        budget_case.setUp()
        if non_psd:
            budget_case.matrix = cluster_contract.build_correlation_matrix_contract(
                budget_case.matrix["symbols"],
                {
                    ("A", "B"): 0.7,
                    ("A", "C"): 0.7,
                    ("B", "C"): -0.1,
                },
            )
            budget_case.audit = build_correlation_cluster_complete_link_audit(
                budget_case.preregistration,
                budget_case.matrix,
            )
            budget_case.complete_link_gate = budget_case._complete_link_gate(
                budget_case.cells
            )

        direct_budget, registration, strata_gate, complete_link_gate, kwargs = (
            budget_case._evaluate(shared=False)
        )
        if proposed_notional != kwargs["proposed_notional"]:
            kwargs = dict(kwargs)
            kwargs["proposed_notional"] = proposed_notional
            direct_budget = budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
                budget_case.preregistration,
                budget_case.matrix,
                budget_case.audit,
                strata_registration=registration,
                strata_gate=strata_gate,
                complete_link_gate=complete_link_gate,
                **kwargs,
            )

        geometry_preregistration = (
            geometry.build_strategy_correlation_matrix_geometry_preregistration_v1(
                budget_case.matrix["symbols"]
            )
        )
        geometry_gate = geometry.evaluate_strategy_correlation_matrix_geometry_gate_v1(
            geometry_preregistration,
            budget_case.matrix,
            expected_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
        )
        complete_preregistration = complete_binding.build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
            geometry_preregistration,
            budget_case.preregistration,
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=budget_case.preregistration[
                "preregistration_hash"
            ],
        )
        complete_evaluation = complete_binding.evaluate_strategy_correlation_matrix_geometry_complete_link_binding_v1(
            complete_preregistration,
            geometry_preregistration,
            geometry_gate,
            budget_case.preregistration,
            budget_case.matrix,
            budget_case.cells,
            expected_binding_preregistration_hash=complete_preregistration[
                "preregistration_hash"
            ],
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=budget_case.preregistration[
                "preregistration_hash"
            ],
            strategy_id=complete_link_gate["strategy_id"],
            variant_id=complete_link_gate["variant_id"],
            lane=complete_link_gate["lane"],
        )
        budget_preregistration = budget_binding.build_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
            complete_preregistration,
            geometry_preregistration,
            budget_case.preregistration,
            registration,
            expected_geometry_complete_link_binding_preregistration_hash=(
                complete_preregistration["preregistration_hash"]
            ),
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=budget_case.preregistration[
                "preregistration_hash"
            ],
            expected_strata_registration_hash=registration["registration_hash"],
        )
        budget_evaluation = budget_binding.evaluate_strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1(
            budget_preregistration,
            complete_preregistration,
            geometry_preregistration,
            geometry_gate,
            complete_evaluation,
            budget_case.preregistration,
            budget_case.matrix,
            budget_case.cells,
            registration,
            strata_gate,
            expected_budget_binding_preregistration_hash=budget_preregistration[
                "preregistration_hash"
            ],
            expected_geometry_complete_link_binding_preregistration_hash=(
                complete_preregistration["preregistration_hash"]
            ),
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=budget_case.preregistration[
                "preregistration_hash"
            ],
            expected_strata_registration_hash=registration["registration_hash"],
            expected_geometry_complete_link_binding_evaluation_hash=(
                complete_evaluation["evaluation_hash"]
            ),
            strategy_id=complete_link_gate["strategy_id"],
            variant_id=complete_link_gate["variant_id"],
            lane=complete_link_gate["lane"],
            **kwargs,
        )
        budget_context = {
            "budget_binding_preregistration": budget_preregistration,
            "geometry_complete_link_binding_preregistration": (
                complete_preregistration
            ),
            "geometry_preregistration": geometry_preregistration,
            "geometry_gate_document": geometry_gate,
            "geometry_complete_link_binding_evaluation": complete_evaluation,
            "cluster_preregistration": budget_case.preregistration,
            "correlation_matrix": budget_case.matrix,
            "selection_cells": budget_case.cells,
            "strata_registration": registration,
            "strata_gate": strata_gate,
            "expected_evaluation_hash": budget_evaluation["evaluation_hash"],
            "expected_budget_binding_preregistration_hash": budget_preregistration[
                "preregistration_hash"
            ],
            "expected_geometry_complete_link_binding_preregistration_hash": (
                complete_preregistration["preregistration_hash"]
            ),
            "expected_geometry_preregistration_hash": geometry_preregistration[
                "preregistration_hash"
            ],
            "expected_cluster_preregistration_hash": budget_case.preregistration[
                "preregistration_hash"
            ],
            "expected_strata_registration_hash": registration["registration_hash"],
            "expected_geometry_complete_link_binding_evaluation_hash": (
                complete_evaluation["evaluation_hash"]
            ),
            "strategy_id": complete_link_gate["strategy_id"],
            "variant_id": complete_link_gate["variant_id"],
            "lane": complete_link_gate["lane"],
            **kwargs,
        }

        presentation_case = presentation_fixture_module.StrategyCorrelationClusterPortfolioRiskStratifiedPresentationV7Tests(
            methodName="test_exact_joint_local_clear_remains_unmounted_and_unauthorized"
        )
        presentation_case.setUp()
        envelope = presentation_case.v6_fixture.envelope
        envelope_context = presentation_case.v6_context
        direct_budget_context = {
            "preregistration": budget_case.preregistration,
            "correlation_matrix": budget_case.matrix,
            "complete_link_audit": budget_case.audit,
            "strata_registration": registration,
            "strata_gate": strata_gate,
            "complete_link_gate": complete_link_gate,
            **kwargs,
        }
        direct_presentation = presentation_case._build(
            direct_budget,
            direct_budget_context,
        )
        presentation_preregistration = binding.build_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
            budget_preregistration,
            expected_budget_binding_preregistration_hash=budget_preregistration[
                "preregistration_hash"
            ],
        )
        return {
            "budget_case": budget_case,
            "direct_budget": direct_budget,
            "direct_presentation": direct_presentation,
            "budget_preregistration": budget_preregistration,
            "budget_evaluation": budget_evaluation,
            "budget_context": budget_context,
            "envelope": envelope,
            "envelope_context": envelope_context,
            "presentation_case": presentation_case,
            "presentation_preregistration": presentation_preregistration,
        }

    @staticmethod
    def _envelope_boundary(bundle: dict):
        return patch.object(
            presentation_v7.envelope_v6.adapter_v6,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
            side_effect=bundle[
                "presentation_case"
            ].v6_fixture._verify_adapter_v6_boundary,
        )

    def _evaluate(self, bundle: dict, **overrides: object) -> dict:
        values = {
            "presentation_binding_preregistration": bundle[
                "presentation_preregistration"
            ],
            "budget_binding_preregistration": bundle["budget_preregistration"],
            "budget_binding_evaluation": bundle["budget_evaluation"],
            "envelope_v6_document": bundle["envelope"],
            "expected_presentation_binding_preregistration_hash": bundle[
                "presentation_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_preregistration_hash": bundle[
                "budget_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_evaluation_hash": bundle[
                "budget_evaluation"
            ]["evaluation_hash"],
            "budget_binding_verification_context": bundle["budget_context"],
            "envelope_v6_verification_context": bundle["envelope_context"],
        }
        values.update(overrides)
        with self._envelope_boundary(bundle):
            return binding.evaluate_strategy_correlation_matrix_geometry_budget_presentation_binding_v1(
                values["presentation_binding_preregistration"],
                values["budget_binding_preregistration"],
                values["budget_binding_evaluation"],
                values["envelope_v6_document"],
                expected_presentation_binding_preregistration_hash=values[
                    "expected_presentation_binding_preregistration_hash"
                ],
                expected_budget_binding_preregistration_hash=values[
                    "expected_budget_binding_preregistration_hash"
                ],
                expected_budget_binding_evaluation_hash=values[
                    "expected_budget_binding_evaluation_hash"
                ],
                budget_binding_verification_context=values[
                    "budget_binding_verification_context"
                ],
                envelope_v6_verification_context=values[
                    "envelope_v6_verification_context"
                ],
            )

    def test_dependency_sources_and_contract_are_pinned(self) -> None:
        self.assertEqual(
            sha256(Path(budget_binding.__file__).read_bytes()).hexdigest(),
            binding.BUDGET_BINDING_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(presentation_v7.__file__).read_bytes()).hexdigest(),
            binding.PRESENTATION_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            budget_binding.BINDING_CONTRACT_HASH,
            binding._CONTRACT_MANIFEST["budget_binding"]["contract_hash"],
        )

    def test_preregistration_is_unmounted_and_exact(self) -> None:
        bundle = self._bundle()
        document = bundle["presentation_preregistration"]
        self.assertEqual(document["status"], "PREREGISTERED_UNMOUNTED")
        self.assertFalse(document["mounted"])
        self.assertEqual(document["neutral_axis_order"], list(binding.NEUTRAL_AXIS_ORDER))
        self.assertTrue(
            binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
                document,
                bundle["budget_preregistration"],
                expected_presentation_binding_preregistration_hash=document[
                    "preregistration_hash"
                ],
                expected_budget_binding_preregistration_hash=bundle[
                    "budget_preregistration"
                ]["preregistration_hash"],
            )
        )

    def test_preregistration_tamper_is_rejected(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["presentation_preregistration"])
        tampered["mounted"] = True
        self.assertFalse(
            binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
                tampered,
                bundle["budget_preregistration"],
                expected_presentation_binding_preregistration_hash=bundle[
                    "presentation_preregistration"
                ]["preregistration_hash"],
                expected_budget_binding_preregistration_hash=bundle[
                    "budget_preregistration"
                ]["preregistration_hash"],
            )
        )

    def test_happy_path_preserves_neutral_presentation_and_zero_authority(self) -> None:
        result = self._evaluate(self._bundle())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["presentation_verified"])
        self.assertEqual(result["axis_order"], list(binding.NEUTRAL_AXIS_ORDER))
        self.assertEqual(result["presentation_status"], "BLOCK")
        self.assertEqual(
            result["presentation_decision"],
            "EXACT_JOINT_LOCAL_CLEAR_PROJECTED_UNMOUNTED",
        )
        self.assertFalse(result["current_admission_allowed"])
        self.assertFalse(result["permissions"]["presentation_activation"])
        self.assertFalse(result["permissions"]["http_registration"])
        self.assertFalse(result["permissions"]["paper"])
        self.assertFalse(result["permissions"]["live"])

    def test_exact_evaluation_verifier_accepts_and_rejects_tamper(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        kwargs = {
            "expected_presentation_binding_preregistration_hash": bundle[
                "presentation_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_preregistration_hash": bundle[
                "budget_preregistration"
            ]["preregistration_hash"],
            "expected_budget_binding_evaluation_hash": bundle[
                "budget_evaluation"
            ]["evaluation_hash"],
            "budget_binding_verification_context": bundle["budget_context"],
            "envelope_v6_verification_context": bundle["envelope_context"],
        }
        with self._envelope_boundary(bundle):
            self.assertTrue(
                binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1(
                    result,
                    bundle["presentation_preregistration"],
                    bundle["budget_preregistration"],
                    bundle["budget_evaluation"],
                    bundle["envelope"],
                    expected_evaluation_hash=result["evaluation_hash"],
                    **kwargs,
                )
            )
        tampered = deepcopy(result)
        tampered["current_admission_allowed"] = True
        with self._envelope_boundary(bundle):
            self.assertFalse(
                binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1(
                    tampered,
                    bundle["presentation_preregistration"],
                    bundle["budget_preregistration"],
                    bundle["budget_evaluation"],
                    bundle["envelope"],
                    expected_evaluation_hash=result["evaluation_hash"],
                    **kwargs,
                )
            )

    def test_missing_budget_binding_evaluation_never_invokes_presentation(self) -> None:
        bundle = self._bundle()
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
        ) as consumer:
            result = self._evaluate(bundle, budget_binding_evaluation=None)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["presentation_invocation_attempted"])

    def test_rehashed_budget_binding_tamper_never_invokes_presentation(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["budget_evaluation"])
        tampered["status"] = "BLOCK"
        self._rehash(tampered, "evaluation_hash", external=False)
        context = deepcopy(bundle["budget_context"])
        context["expected_evaluation_hash"] = tampered["evaluation_hash"]
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
        ) as consumer:
            result = self._evaluate(
                bundle,
                budget_binding_evaluation=tampered,
                expected_budget_binding_evaluation_hash=tampered["evaluation_hash"],
                budget_binding_verification_context=context,
            )
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "GEOMETRY_BOUND_BUDGET_EVALUATION_INVALID"
        )

    def test_context_alias_or_extra_key_never_invokes_presentation(self) -> None:
        bundle = self._bundle()
        context = deepcopy(bundle["budget_context"])
        context["compatibility_alias"] = True
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
        ) as consumer:
            result = self._evaluate(
                bundle,
                budget_binding_verification_context=context,
            )
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")

    def test_non_psd_direct_projection_gap_is_blocked_before_presentation(self) -> None:
        bundle = self._bundle(non_psd=True)
        self.assertEqual(bundle["direct_budget"]["status"], "PASS")
        self.assertEqual(
            bundle["direct_presentation"]["local_decision"]["joint_status"],
            "PASS",
        )
        self.assertEqual(bundle["budget_evaluation"]["status"], "BLOCK")
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
        ) as consumer:
            result = self._evaluate(bundle)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_BOUND_BUDGET_EVALUATION_DID_NOT_PASS",
        )

    def test_verified_budget_block_is_projected_neutrally(self) -> None:
        bundle = self._bundle(proposed_notional=9000)
        self.assertEqual(bundle["budget_evaluation"]["status"], "PASS")
        self.assertEqual(
            bundle["budget_evaluation"]["effective_budget_status"], "BLOCK"
        )
        result = self._evaluate(bundle)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["presentation_status"], "BLOCK")
        self.assertTrue(result["presentation_verified"])
        self.assertFalse(result["current_admission_allowed"])

    def test_presentation_consumer_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "PRESENTATION_V7_CONSUMER_EXCEPTION")
        self.assertIsNone(result["presentation_document"])

    def test_rehashed_forged_presentation_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["direct_presentation"])
        forged["axis_order"] = ["PERMISSION", "MATURITY", "GAP", "SOURCE"]
        self._rehash(forged, "presentation_v7_hash", external=True)
        with patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
            return_value=forged,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "PRESENTATION_V7_DOCUMENT_INVALID")
        self.assertFalse(result["presentation_verified"])

    def test_budget_verification_precedes_presentation_invocation(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_budget_verify = (
            budget_binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1
        )
        original_presentation = (
            presentation_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
        )

        def observed_budget(*args: object, **kwargs: object) -> bool:
            events.append("budget")
            return original_budget_verify(*args, **kwargs)

        def observed_presentation(*args: object, **kwargs: object) -> dict:
            events.append("presentation")
            return original_presentation(*args, **kwargs)

        with patch.object(
            budget_binding,
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1",
            side_effect=observed_budget,
        ), patch.object(
            presentation_v7,
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7",
            side_effect=observed_presentation,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(events[0], "budget")
        self.assertLess(events.index("budget"), events.index("presentation"))


if __name__ == "__main__":
    unittest.main()
