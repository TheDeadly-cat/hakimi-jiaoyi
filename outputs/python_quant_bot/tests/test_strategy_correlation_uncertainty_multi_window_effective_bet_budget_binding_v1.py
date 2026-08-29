from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as budget_binding,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as uncertainty_gate,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1 as subject,
)
from tests import (
    test_strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as budget_fixtures,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as uncertainty_fixtures,
)


def _canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


class StrategyCorrelationUncertaintyMultiWindowEffectiveBetBudgetBindingV1Tests(
    unittest.TestCase
):
    def _budget_bundle(
        self,
        *,
        risk_increasing: bool = True,
        proposed_notional: float | None = None,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        fixture = budget_fixtures.StrategyCorrelationMatrixGeometryEffectiveBetBudgetBindingTests(
            methodName="test_happy_path_preserves_budget_and_zero_authority"
        )
        bundle = fixture._bundle()
        self.addCleanup(bundle["case"].doCleanups)
        budget_inputs: dict[str, object] = {"risk_increasing": risk_increasing}
        if proposed_notional is not None:
            budget_inputs["proposed_notional"] = proposed_notional
        evaluation = fixture._evaluate(bundle, budget_inputs=budget_inputs)
        kwargs = dict(bundle["kwargs"])
        kwargs.update(budget_inputs)
        context = {
            "budget_binding_preregistration": bundle["budget_preregistration"],
            "geometry_complete_link_binding_preregistration": bundle[
                "upstream_preregistration"
            ],
            "geometry_preregistration": bundle["geometry_preregistration"],
            "geometry_gate_document": bundle["geometry_gate"],
            "geometry_complete_link_binding_evaluation": bundle[
                "upstream_evaluation"
            ],
            "cluster_preregistration": bundle["case"].preregistration,
            "correlation_matrix": bundle["case"].matrix,
            "selection_cells": bundle["case"].cells,
            "strata_registration": bundle["registration"],
            "strata_gate": bundle["strata_gate"],
            "expected_evaluation_hash": evaluation["evaluation_hash"],
            "expected_budget_binding_preregistration_hash": bundle[
                "budget_preregistration"
            ]["preregistration_hash"],
            "expected_geometry_complete_link_binding_preregistration_hash": bundle[
                "upstream_preregistration"
            ]["preregistration_hash"],
            "expected_geometry_preregistration_hash": bundle[
                "geometry_preregistration"
            ]["preregistration_hash"],
            "expected_cluster_preregistration_hash": bundle[
                "case"
            ].preregistration["preregistration_hash"],
            "expected_strata_registration_hash": bundle["registration"][
                "registration_hash"
            ],
            "expected_geometry_complete_link_binding_evaluation_hash": bundle[
                "upstream_evaluation"
            ]["evaluation_hash"],
            "strategy_id": bundle["complete_link_gate"]["strategy_id"],
            "variant_id": bundle["complete_link_gate"]["variant_id"],
            "lane": bundle["complete_link_gate"]["lane"],
            "equity": kwargs["equity"],
            "positions": kwargs["positions"],
            "proposed_symbol": kwargs["proposed_symbol"],
            "proposed_notional": kwargs["proposed_notional"],
            "proposed_direction": kwargs["proposed_direction"],
            "max_cluster_gross_pct": kwargs["max_cluster_gross_pct"],
            "risk_increasing": kwargs["risk_increasing"],
        }
        return bundle, evaluation, context

    def _uncertainty_bundle(
        self,
        budget_bundle: dict[str, object],
        *,
        blocked: bool,
    ) -> tuple[dict[str, object], dict[str, object]]:
        fixture = uncertainty_fixtures.StrategyCorrelationUncertaintyMultiWindowClusterGateV1Tests(
            methodName="test_every_window_confirmed_low_preserves_separate_clusters"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        symbols = list(budget_bundle["case"].preregistration["symbols"])
        clusters = deepcopy(
            budget_bundle["case"].preregistration["clusters"]
        )
        first = fixture._low_audit(clusters, (1, 2, 3))
        if blocked:
            methods = uncertainty_fixtures.FixtureCase
            base = methods._normal(11)
            second = fixture._audit(
                {
                    "A": base,
                    "B": methods._correlated(base, 0.98, 12),
                    "C": methods._normal(13),
                },
                clusters,
            )
        else:
            second = fixture._low_audit(clusters, (4, 5, 6))
        preregistration, window_audits, audit_hashes = fixture._context(
            symbols,
            clusters,
            [first, second],
        )
        gate = fixture._evaluate(
            (preregistration, window_audits, audit_hashes)
        )
        self.assertEqual(gate["status"], "BLOCK" if blocked else "PASS")
        return gate, {
            "uncertainty_preregistration": preregistration,
            "window_audits": window_audits,
            "expected_gate_hash": gate["gate_hash"],
            "expected_preregistration_hash": preregistration[
                "preregistration_hash"
            ],
            "expected_window_audit_hashes": audit_hashes,
        }

    @staticmethod
    def _preregistration_contexts(
        gate_context: dict[str, object],
        budget_context: dict[str, object],
    ) -> tuple[dict[str, object], dict[str, object]]:
        uncertainty_preregistration = gate_context[
            "uncertainty_preregistration"
        ]
        uncertainty_context = {
            "expected_symbols": uncertainty_preregistration[
                "expected_symbols"
            ],
            "expected_clusters": uncertainty_preregistration[
                "expected_clusters"
            ],
            "expected_windows": uncertainty_preregistration[
                "expected_windows"
            ],
            "expected_preregistration_hash": gate_context[
                "expected_preregistration_hash"
            ],
        }
        budget_keys = subject._BUDGET_PREREGISTRATION_CONTEXT_KEYS
        return uncertainty_context, {
            key: budget_context[key] for key in budget_keys
        }

    def _context(
        self,
        *,
        blocked: bool = False,
        risk_increasing: bool = True,
        proposed_notional: float | None = None,
    ) -> dict[str, object]:
        budget_bundle, budget_evaluation, budget_context = self._budget_bundle(
            risk_increasing=risk_increasing,
            proposed_notional=proposed_notional,
        )
        gate, gate_context = self._uncertainty_bundle(
            budget_bundle,
            blocked=blocked,
        )
        uncertainty_prereg_context, budget_prereg_context = (
            self._preregistration_contexts(gate_context, budget_context)
        )
        preregistration = subject.build_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
            gate_context["uncertainty_preregistration"],
            budget_context["budget_binding_preregistration"],
            uncertainty_preregistration_verification_context=(
                uncertainty_prereg_context
            ),
            budget_preregistration_verification_context=budget_prereg_context,
        )
        self.assertIsNotNone(preregistration)
        return {
            "preregistration": preregistration,
            "uncertainty_gate": gate,
            "budget_evaluation": budget_evaluation,
            "uncertainty_gate_context": gate_context,
            "budget_evaluation_context": budget_context,
            "uncertainty_preregistration_context": uncertainty_prereg_context,
            "budget_preregistration_context": budget_prereg_context,
        }

    @staticmethod
    def _evaluate(context: dict[str, object]) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1(
            context["preregistration"],
            context["uncertainty_gate"],
            context["budget_evaluation"],
            expected_preregistration_hash=context["preregistration"][
                "preregistration_hash"
            ],
            uncertainty_gate_verification_context=context[
                "uncertainty_gate_context"
            ],
            budget_evaluation_verification_context=context[
                "budget_evaluation_context"
            ],
        )
        if result is None:
            raise AssertionError("binding evaluation unexpectedly returned None")
        return result

    def test_dependency_source_pins_match_reviewed_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            subject.UNCERTAINTY_GATE_SOURCE_SHA256: root
            / "exchange_terminal"
            / "services"
            / "strategy_correlation_uncertainty_multi_window_cluster_gate_v1.py",
            subject.GEOMETRY_BUDGET_BINDING_SOURCE_SHA256: root
            / "exchange_terminal"
            / "services"
            / "strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1.py",
        }
        for expected, path in paths.items():
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)
        self.assertEqual(
            budget_binding.EFFECTIVE_BUDGET_IMPLEMENTATION_SHA256,
            subject.EFFECTIVE_BUDGET_V3_SOURCE_SHA256,
        )

    def test_preregistration_exactly_binds_shared_cluster_partition(self) -> None:
        context = self._context()
        preregistration = context["preregistration"]

        self.assertEqual(preregistration["status"], "PREREGISTERED_UNMOUNTED")
        self.assertTrue(preregistration["facts"]["shared_cluster_partition_exact"])
        self.assertFalse(preregistration["facts"]["dynamic_reclustering_allowed"])
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
                preregistration,
                context["uncertainty_gate_context"][
                    "uncertainty_preregistration"
                ],
                context["budget_evaluation_context"][
                    "budget_binding_preregistration"
                ],
                expected_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
                uncertainty_preregistration_verification_context=context[
                    "uncertainty_preregistration_context"
                ],
                budget_preregistration_verification_context=context[
                    "budget_preregistration_context"
                ],
            )
        )

    def test_all_window_low_gate_releases_exact_research_budget(self) -> None:
        result = self._evaluate(self._context())

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["reason_code"],
            "UNCERTAINTY_CLUSTER_BOUND_EFFECTIVE_BUDGET_VERIFIED",
        )
        self.assertEqual(result["uncertainty_gate_status"], "PASS")
        self.assertEqual(result["effective_budget_status"], "PASS")
        self.assertEqual(
            result["effective_budget_decision"],
            "PASS_STRATIFIED_RESEARCH_BUDGET",
        )
        self.assertTrue(result["facts"]["budget_evaluation_exactly_verified"])

    def test_uncertainty_block_vetoes_risk_increase_before_budget_verifier(self) -> None:
        context = self._context(blocked=True)
        with patch.object(
            budget_binding,
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1",
        ) as verifier:
            result = self._evaluate(context)

        verifier.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["reason_code"],
            "CROSS_CLUSTER_DEPENDENCE_REQUIRES_REPREREGISTRATION",
        )
        self.assertFalse(result["facts"]["budget_verification_attempted"])
        self.assertIsNone(result["trusted_effective_budget_document"])

    def test_resealed_uncertainty_promotion_is_unknown_before_budget(self) -> None:
        context = self._context(blocked=True)
        forged = deepcopy(context["uncertainty_gate"])
        forged["status"] = "PASS"
        forged["cross_cluster_dependence_edge_count"] = 0
        unsigned = dict(forged)
        unsigned.pop("gate_hash")
        forged["gate_hash"] = _canonical_hash(unsigned)
        context["uncertainty_gate"] = forged
        context["uncertainty_gate_context"]["expected_gate_hash"] = forged[
            "gate_hash"
        ]
        with patch.object(
            budget_binding,
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1",
        ) as verifier:
            result = self._evaluate(context)

        verifier.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "UNCERTAINTY_CLUSTER_GATE_INVALID")

    def test_budget_evaluation_tamper_fails_after_uncertainty_pass(self) -> None:
        context = self._context()
        forged = deepcopy(context["budget_evaluation"])
        forged["current_admission_allowed"] = True
        unsigned = dict(forged)
        unsigned.pop("evaluation_hash")
        forged["evaluation_hash"] = _canonical_hash(unsigned)
        context["budget_evaluation"] = forged
        context["budget_evaluation_context"]["expected_evaluation_hash"] = forged[
            "evaluation_hash"
        ]

        result = self._evaluate(context)

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_BOUND_EFFECTIVE_BUDGET_INVALID",
        )

    def test_verified_budget_block_is_preserved_without_permission(self) -> None:
        result = self._evaluate(self._context(proposed_notional=9000.0))

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["effective_budget_status"], "BLOCK")
        self.assertEqual(result["effective_budget_decision"], "BLOCK")
        self.assertFalse(result["authority"]["current_admission_allowed"])

    def test_exact_risk_reduction_survives_uncertainty_block(self) -> None:
        result = self._evaluate(
            self._context(blocked=True, risk_increasing=False)
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["reason_code"],
            "EXACT_RISK_REDUCTION_PRESERVED_UNDER_UNCERTAINTY_BLOCK",
        )
        self.assertEqual(result["effective_budget_decision"], "RISK_REDUCTION_PATH")
        self.assertFalse(result["facts"]["risk_increasing"])

    def test_partition_drift_cannot_build_binding_preregistration(self) -> None:
        context = self._context()
        uncertainty_preregistration = deepcopy(
            context["uncertainty_gate_context"]["uncertainty_preregistration"]
        )
        uncertainty_preregistration["expected_clusters"] = [
            {"cluster_id": "all", "members": ["A", "B", "C"]}
        ]
        uncertainty_preregistration[
            "cluster_partition_hash"
        ] = _canonical_hash(uncertainty_preregistration["expected_clusters"])
        unsigned = dict(uncertainty_preregistration)
        unsigned.pop("preregistration_hash")
        uncertainty_preregistration["preregistration_hash"] = _canonical_hash(
            unsigned
        )
        uncertainty_context = deepcopy(
            context["uncertainty_preregistration_context"]
        )
        uncertainty_context["expected_clusters"] = uncertainty_preregistration[
            "expected_clusters"
        ]
        uncertainty_context[
            "expected_preregistration_hash"
        ] = uncertainty_preregistration["preregistration_hash"]

        preregistration = subject.build_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
            uncertainty_preregistration,
            context["budget_evaluation_context"][
                "budget_binding_preregistration"
            ],
            uncertainty_preregistration_verification_context=uncertainty_context,
            budget_preregistration_verification_context=context[
                "budget_preregistration_context"
            ],
        )

        self.assertIsNone(preregistration)

    def test_context_expansion_fails_closed_before_evaluation_verifiers(self) -> None:
        context = self._context()
        context["uncertainty_gate_context"]["extra"] = True
        with patch.object(
            uncertainty_gate,
            "verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1",
        ) as uncertainty_verifier, patch.object(
            budget_binding,
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1",
        ) as budget_verifier:
            result = self._evaluate(context)

        uncertainty_verifier.assert_not_called()
        budget_verifier.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "VERIFICATION_CONTEXT_NOT_EXACT")

    def test_evaluation_verifier_rebuilds_and_rejects_authority_promotion(self) -> None:
        context = self._context()
        result = self._evaluate(context)
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_evaluation_v1(
                result,
                context["preregistration"],
                context["uncertainty_gate"],
                context["budget_evaluation"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_preregistration_hash=context["preregistration"][
                    "preregistration_hash"
                ],
                uncertainty_gate_verification_context=context[
                    "uncertainty_gate_context"
                ],
                budget_evaluation_verification_context=context[
                    "budget_evaluation_context"
                ],
            )
        )
        forged = deepcopy(result)
        forged["authority"]["writer_allowed"] = True
        unsigned = dict(forged)
        unsigned.pop("evaluation_hash")
        forged["evaluation_hash"] = _canonical_hash(unsigned)
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_evaluation_v1(
                forged,
                context["preregistration"],
                context["uncertainty_gate"],
                context["budget_evaluation"],
                expected_evaluation_hash=forged["evaluation_hash"],
                expected_preregistration_hash=context["preregistration"][
                    "preregistration_hash"
                ],
                uncertainty_gate_verification_context=context[
                    "uncertainty_gate_context"
                ],
                budget_evaluation_verification_context=context[
                    "budget_evaluation_context"
                ],
            )
        )

    def test_uncertainty_verification_precedes_budget_verification(self) -> None:
        context = self._context()
        events: list[str] = []
        original_uncertainty = (
            uncertainty_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1
        )
        original_budget = (
            budget_binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1
        )

        def observed_uncertainty(*args: object, **kwargs: object) -> bool:
            events.append("uncertainty")
            return original_uncertainty(*args, **kwargs)

        def observed_budget(*args: object, **kwargs: object) -> bool:
            events.append("budget")
            return original_budget(*args, **kwargs)

        with patch.object(
            uncertainty_gate,
            "verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1",
            side_effect=observed_uncertainty,
        ), patch.object(
            budget_binding,
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1",
            side_effect=observed_budget,
        ):
            result = self._evaluate(context)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(events, ["uncertainty", "budget"])

    def test_output_excludes_window_audits_and_all_authority_stays_locked(self) -> None:
        result = self._evaluate(self._context())
        serialized = json.dumps(result, sort_keys=True)

        self.assertNotIn('"window_audits":', serialized)
        self.assertNotIn("completed_price_input", serialized)
        self.assertNotIn("price_rows", serialized)
        self.assertFalse(result["facts"]["raw_window_audits_embedded"])
        self.assertTrue(
            all(
                value is False
                for key, value in result["authority"].items()
                if key != "research_evidence_only"
            )
        )


if __name__ == "__main__":
    unittest.main()
