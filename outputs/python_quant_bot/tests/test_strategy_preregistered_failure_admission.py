from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    build_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_preregistered_failure_admission import (
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2,
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3,
    STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
    build_strategy_preregistered_failure_admission,
    build_strategy_preregistered_failure_admission_v2,
    build_strategy_preregistered_failure_admission_v3,
)
from exchange_terminal.services.strategy_research import (
    aggregate_validation_variant,
    build_parameter_stability_snapshot,
    canonical_hash,
    freeze_validation_candidates,
)
from exchange_terminal.services.strategy_research_evidence import (
    strategy_research_result_hash,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    build_strategy_research_search_lineage,
)


def hypothesis(strategy_ids: list[str]) -> dict[str, object]:
    return build_strategy_hypothesis_preregistration({
        "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
        "hypothesis_id": "test-admission-v1",
        "research_generation": "TEST_GENERATION",
        "strategy_ids": strategy_ids,
        "mechanism_family": "causal trend persistence",
        "hypothesis_statement": (
            "A completed-bar causal trend state should retain positive benchmark "
            "excess under the frozen research contract."
        ),
        "novelty_statement": (
            "This mechanism does not reuse or retune either previously falsified "
            "strategy family."
        ),
        "mechanism_specific_failure_conditions": [
            "Retire the mechanism if fresh confirmation does not retain positive excess."
        ],
    })


def hypothesis_v2(
    strategy_ids: list[str],
    *,
    metric: str = "median_validation_excess_return_pct",
    operator: str = "LTE",
    threshold: float = 0.0,
) -> dict[str, object]:
    return build_strategy_hypothesis_preregistration({
        "schema_version": (
            STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
        ),
        "hypothesis_id": "test-admission-v2",
        "research_generation": "TEST_GENERATION",
        "strategy_ids": strategy_ids,
        "mechanism_family": "causal trend persistence",
        "hypothesis_statement": (
            "A completed-bar causal trend state should retain positive benchmark "
            "excess under the frozen research contract."
        ),
        "novelty_statement": (
            "This mechanism does not reuse or retune either previously falsified "
            "strategy family."
        ),
        "mechanism_specific_failure_conditions": [{
            "condition_id": "mechanism_metric_failed",
            "evidence_stage": "DEVELOPMENT_SELECTION",
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "required_action": "BLOCK_RESEARCH",
        }],
    })


def hypothesis_v3(strategy_ids: list[str]) -> dict[str, object]:
    source = hypothesis_v2(strategy_ids)
    draft = {
        "schema_version": STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
        "hypothesis_id": "test-admission-v3",
        "research_generation": "TEST_GENERATION",
        "search_family_id": "causal-trend-global-search",
        "strategy_ids": strategy_ids,
        "mechanism_family": source["mechanism"]["family"],
        "hypothesis_statement": source["mechanism"]["hypothesis_statement"],
        "novelty_statement": source["mechanism"]["novelty_statement"],
        "mechanism_specific_failure_conditions": source["failure_contract"][
            "mechanism_specific_conditions"
        ],
    }
    return build_strategy_hypothesis_preregistration(draft)


def cell(strategy_id: str, *, variant_id: str | None = None) -> dict[str, object]:
    return {
        "strategy_id": strategy_id,
        "variant_id": variant_id or f"{strategy_id}:candidate",
        "symbol": "BTC-USDT-SWAP",
        "dataset_status": "PASS",
        "train_ok": True,
        "validation_ok": True,
        "train_return_pct": 8.0,
        "validation_return_pct": 6.0,
        "validation_excess_return_pct": 4.0,
        "validation_trade_count": 4,
        "validation_max_drawdown_pct": 5.0,
        "validation_sharpe": 1.5,
        "validation_drawdown_improvement_pct": 5.0,
        "validation_sharpe_excess": 0.8,
        "validation_risk_efficiency_excess": 0.8,
        "lookahead_status": "PASS",
        "cost_sensitivity_status": "PASS",
        "cost_sensitivity": {
            "status": "PASS",
            "verification_status": "PASS",
            "stage": "DEVELOPMENT_SELECTION",
            "break_even_preserved": True,
            "worst_return_pct": 1.0,
            "blockers": [],
        },
        "fold_stability_status": "PASS",
        "fold_stability": {
            "schema_version": "strategy-fixed-chronological-slice-evidence-v2",
            "verification_status": "PASS",
            "status": "PASS",
            "parameters_refit_per_fold": False,
            "walk_forward_optimization_claim_allowed": False,
            "usable_folds": 3,
            "positive_folds": 2,
            "blockers": [],
        },
    }


def spec(
    strategy_ids: list[str],
    *,
    max_test_candidates: int | None = None,
) -> dict[str, object]:
    variants = []
    for strategy_id in strategy_ids:
        for index, suffix in enumerate(("candidate", "neighbor", "third"), start=1):
            variants.append({
                "strategy_id": strategy_id,
                "variant_id": f"{strategy_id}:{suffix}",
                "variant_label": suffix,
                "params": {"period": index},
                "param_hash": f"param-{strategy_id}-{suffix}",
                "implementation_fingerprint": f"impl-{strategy_id}",
                "risk_profile": {},
                "risk": {},
                "risk_hash": f"risk-{strategy_id}-{suffix}",
            })
    return {
        "strategies": strategy_ids,
        "selection_symbols": ["BTC-USDT-SWAP"],
        "variants": variants,
        "max_test_candidates": (
            len(strategy_ids) if max_test_candidates is None else max_test_candidates
        ),
    }


def build(
    strategy_ids: list[str],
    *,
    plateau_evidence: dict[str, object] | None = None,
    cells: list[dict[str, object]] | None = None,
    max_test_candidates: int | None = None,
) -> dict[str, object]:
    batch_spec = spec(
        strategy_ids,
        max_test_candidates=max_test_candidates,
    )
    selection_cells = cells or [
        cell(str(variant["strategy_id"]), variant_id=str(variant["variant_id"]))
        for variant in batch_spec["variants"]
    ]
    rankings = [
        aggregate_validation_variant(
            variant,
            [
                item for item in selection_cells
                if item["strategy_id"] == variant["strategy_id"]
                and item["variant_id"] == variant["variant_id"]
            ],
            required_symbols=1,
            total_variant_trials=len(batch_spec["variants"]),
        )
        for variant in batch_spec["variants"]
    ]
    rankings.sort(key=lambda row: float(row["adjusted_score"]), reverse=True)
    candidates = freeze_validation_candidates(
        rankings,
        max_candidates=int(batch_spec["max_test_candidates"]),
    )
    return build_strategy_preregistered_failure_admission(
        batch_spec=batch_spec,
        hypothesis_preregistration=hypothesis(strategy_ids),
        parameter_stability=plateau_evidence or build_parameter_stability_snapshot(
            rankings,
            frozen_variants=batch_spec["variants"],
        ),
        selection_cells=selection_cells,
        validation_candidates=candidates,
    )


def build_v2(
    strategy_ids: list[str],
    *,
    sealed_hypothesis: dict[str, object] | None = None,
    metric: str = "median_validation_excess_return_pct",
    operator: str = "LTE",
    threshold: float = 0.0,
    max_test_candidates: int | None = None,
) -> dict[str, object]:
    batch_spec = spec(
        strategy_ids,
        max_test_candidates=max_test_candidates,
    )
    selection_cells = [
        cell(str(variant["strategy_id"]), variant_id=str(variant["variant_id"]))
        for variant in batch_spec["variants"]
    ]
    rankings = [
        aggregate_validation_variant(
            variant,
            [
                item for item in selection_cells
                if item["strategy_id"] == variant["strategy_id"]
                and item["variant_id"] == variant["variant_id"]
            ],
            required_symbols=1,
            total_variant_trials=len(batch_spec["variants"]),
        )
        for variant in batch_spec["variants"]
    ]
    rankings.sort(key=lambda row: float(row["adjusted_score"]), reverse=True)
    candidates = freeze_validation_candidates(
        rankings,
        max_candidates=int(batch_spec["max_test_candidates"]),
    )
    return build_strategy_preregistered_failure_admission_v2(
        batch_spec=batch_spec,
        hypothesis_preregistration=(
            sealed_hypothesis
            or hypothesis_v2(
                strategy_ids,
                metric=metric,
                operator=operator,
                threshold=threshold,
            )
        ),
        parameter_stability=build_parameter_stability_snapshot(
            rankings,
            frozen_variants=batch_spec["variants"],
        ),
        selection_cells=selection_cells,
        validation_candidates=candidates,
    )


class StrategyPreregisteredFailureAdmissionTests(unittest.TestCase):
    def test_v3_bare_or_forged_lineage_cannot_claim_cumulative_admission(self) -> None:
        batch_spec = spec(["dual_ma"])
        batch_spec["search_lineage"] = build_strategy_research_search_lineage(
            search_family_id="causal-trend-global-search",
            prior_registrations=[],
            current_trial_count=len(batch_spec["variants"]),
        )
        selection_cells = [
            cell("dual_ma", variant_id=str(variant["variant_id"]))
            for variant in batch_spec["variants"]
        ]
        rankings = [
            aggregate_validation_variant(
                variant,
                [
                    item for item in selection_cells
                    if item["variant_id"] == variant["variant_id"]
                ],
                required_symbols=1,
                total_variant_trials=len(batch_spec["variants"]),
            )
            for variant in batch_spec["variants"]
        ]
        rankings.sort(
            key=lambda row: float(row["adjusted_score"]),
            reverse=True,
        )
        candidates = freeze_validation_candidates(rankings, max_candidates=1)
        arguments = {
            "batch_spec": batch_spec,
            "hypothesis_preregistration": hypothesis_v3(["dual_ma"]),
            "parameter_stability": build_parameter_stability_snapshot(
                rankings,
                frozen_variants=batch_spec["variants"],
            ),
            "selection_cells": selection_cells,
            "validation_candidates": candidates,
        }

        missing = build_strategy_preregistered_failure_admission_v3(**arguments)
        self.assertEqual(
            missing["schema_version"],
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V3,
        )
        self.assertEqual(missing["status"], "BLOCK")
        self.assertEqual(missing["admitted_variant_ids"], [])
        self.assertIn(
            "strategy_search_registration_context_missing",
            missing["blockers"],
        )

        forged = build_strategy_preregistered_failure_admission_v3(
            **arguments,
            registration_context={
                "ok": True,
                "status": "RUNNING",
                "registration_id": "forged",
                "protocol": {},
                "claim": {},
                "registry_audit": {"status": "PASS"},
            },
        )
        self.assertEqual(forged["status"], "BLOCK")
        self.assertEqual(forged["admitted_variant_ids"], [])
        self.assertIn(
            "strategy_search_registered_protocol_hash_invalid",
            forged["blockers"],
        )

    def test_v2_resolves_every_metric_from_rebuilt_development_evidence(self) -> None:
        cases = (
            ("validation_adjusted_score", "LT", -1_000_000.0),
            ("median_validation_return_pct", "LT", -1_000_000.0),
            ("median_validation_excess_return_pct", "LT", -1_000_000.0),
            ("validation_worst_drawdown_pct", "GT", 1_000_000.0),
            ("validation_trade_count", "LT", -1.0),
            ("minimum_stressed_return_pct", "LT", -1_000_000.0),
            ("minimum_positive_fold_count", "LT", -1.0),
        )
        for metric, operator, threshold in cases:
            with self.subTest(metric=metric):
                admission = build_v2(
                    ["dual_ma"],
                    metric=metric,
                    operator=operator,
                    threshold=threshold,
                )
                mechanism = [
                    check
                    for check in admission["strategies"][0]["checks"]
                    if check.get("condition_kind") == "MECHANISM_SPECIFIC"
                ][0]
                self.assertEqual(admission["status"], "PASS")
                self.assertEqual(mechanism["status"], "PASS")
                self.assertIsInstance(mechanism["metric_value"], float)

    def test_v2_unselected_strategy_is_not_applicable_not_false_pass(self) -> None:
        admission = build_v2(
            ["dual_ma", "rsi"],
            max_test_candidates=1,
        )

        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["admitted_variant_ids"], ["dual_ma:candidate"])
        unselected = admission["strategies"][1]
        mechanism = [
            check for check in unselected["checks"]
            if check.get("condition_kind") == "MECHANISM_SPECIFIC"
        ]
        self.assertEqual([check["status"] for check in mechanism], ["NOT_APPLICABLE"])
        self.assertEqual(unselected["admitted_variant_ids"], [])

    def test_v2_passes_only_resolved_untriggered_mechanism_conditions(self) -> None:
        admission = build_v2(["dual_ma"])

        self.assertEqual(
            admission["schema_version"],
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION_V2,
        )
        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["admitted_variant_ids"], ["dual_ma:candidate"])
        mechanism = [
            check for check in admission["strategies"][0]["checks"]
            if check.get("condition_kind") == "MECHANISM_SPECIFIC"
        ]
        self.assertEqual(len(mechanism), 1)
        self.assertEqual(mechanism[0]["status"], "PASS")
        self.assertIs(mechanism[0]["triggered"], False)
        self.assertGreater(mechanism[0]["metric_value"], 0)
        self.assertEqual(
            [row["status"] for row in admission["future_standard_checks"]],
            ["NOT_DUE", "NOT_DUE"],
        )
        content = dict(admission)
        self.assertEqual(content.pop("admission_hash"), canonical_hash(content))

    def test_v2_triggered_or_unresolved_condition_blocks_entire_batch(self) -> None:
        triggered = build_v2(
            ["dual_ma"],
            metric="validation_adjusted_score",
            operator="GT",
            threshold=0.0,
        )
        self.assertEqual(triggered["status"], "BLOCK")
        self.assertEqual(triggered["admitted_variant_ids"], [])
        self.assertIn(
            "dual_ma:mechanism_condition_triggered:mechanism_metric_failed",
            triggered["blockers"],
        )

        malformed = hypothesis_v2(["dual_ma"])
        malformed["failure_contract"]["mechanism_specific_conditions"][0][
            "metric"
        ] = "self_reported_profit"
        malformed_content = dict(malformed)
        malformed_content.pop("hypothesis_hash")
        malformed["hypothesis_hash"] = canonical_hash(malformed_content)
        unresolved = build_v2(
            ["dual_ma"],
            sealed_hypothesis=malformed,
        )
        self.assertEqual(unresolved["status"], "BLOCK")
        self.assertEqual(unresolved["admitted_variant_ids"], [])
        self.assertIn("mechanism_conditions_unresolved", unresolved["blockers"])

    def test_schema11_result_hash_remains_historical_and_schema12_binds_admission(self) -> None:
        report = {
            "schema_version": 11,
            "batch_spec_hash": "a" * 64,
            "dataset_manifest_hash": "b" * 64,
            "selection_cells": [],
            "validation_rankings": [],
            "frozen_candidates": [],
            "test_cells": [],
            "test_results": [],
            "holdout_cells": [],
            "holdout_results": [],
            "forward_candidates": [],
            "implementation_manifest": {},
        }
        self.assertEqual(
            strategy_research_result_hash(report),
            "0d258b2059e0e2815a329353c4d4046927e737434ccd72eddd16054df1d072b5",
        )
        report["preregistered_failure_admission"] = {"status": "BLOCK"}
        self.assertEqual(
            strategy_research_result_hash(report),
            "0d258b2059e0e2815a329353c4d4046927e737434ccd72eddd16054df1d072b5",
        )
        report["schema_version"] = 12
        schema12_hash = strategy_research_result_hash(report)
        report["preregistered_failure_admission"] = {"status": "PASS"}
        self.assertNotEqual(strategy_research_result_hash(report), schema12_hash)
        report["schema_version"] = 13
        schema13_hash = strategy_research_result_hash(report)
        report["preregistered_failure_admission"] = {"status": "BLOCK"}
        self.assertNotEqual(strategy_research_result_hash(report), schema13_hash)

    def test_pass_is_hash_bound_and_authority_free(self) -> None:
        admission = build(["dual_ma"])

        self.assertEqual(
            admission["schema_version"],
            STRATEGY_PREREGISTERED_FAILURE_ADMISSION_SCHEMA_VERSION,
        )
        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["admission_scope"], "HYPOTHESIS_BATCH")
        self.assertEqual(admission["admitted_variant_ids"], ["dual_ma:candidate"])
        content = dict(admission)
        self.assertEqual(content.pop("admission_hash"), canonical_hash(content))
        for field in (
            "profitability_proven",
            "performance_claim_allowed",
            "parameter_selection_allowed",
            "automatic_paper_activation_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertIs(admission[field], False)

    def test_plateau_review_blocks_entire_hypothesis_batch(self) -> None:
        batch_spec = spec(["dual_ma", "rsi"])
        selection_cells = [
            cell(str(variant["strategy_id"]), variant_id=str(variant["variant_id"]))
            for variant in batch_spec["variants"]
        ]
        for item in selection_cells:
            if item["variant_id"] == "rsi:candidate":
                item.update({
                    "train_return_pct": 24.0,
                    "validation_return_pct": 20.0,
                    "validation_excess_return_pct": 15.0,
                })
            elif str(item["variant_id"]).startswith("rsi:"):
                item.update({
                    "train_return_pct": 4.0,
                    "validation_return_pct": 3.0,
                    "validation_excess_return_pct": 1.0,
                })

        admission = build(
            ["dual_ma", "rsi"],
            cells=selection_cells,
        )

        self.assertEqual(admission["status"], "BLOCK")
        self.assertEqual(admission["strategies"][0]["status"], "PASS")
        self.assertEqual(admission["strategies"][0]["admitted_variant_ids"], [])
        self.assertEqual(admission["admitted_variant_ids"], [])

    def test_recomputes_cost_and_fixed_slice_instead_of_trusting_cell_status(self) -> None:
        cost_cells = [
            cell("dual_ma", variant_id=f"dual_ma:{suffix}")
            for suffix in ("candidate", "neighbor", "third")
        ]
        cost_cells[0]["cost_sensitivity"]["break_even_preserved"] = False
        cost_admission = build(["dual_ma"], cells=cost_cells)
        self.assertEqual(cost_admission["status"], "BLOCK")
        self.assertTrue(cost_admission["strategies"][0]["checks"][1]["triggered"])

        slice_cells = [
            cell("dual_ma", variant_id=f"dual_ma:{suffix}")
            for suffix in ("candidate", "neighbor", "third")
        ]
        slice_cells[0]["fold_stability"]["parameters_refit_per_fold"] = True
        slice_admission = build(["dual_ma"], cells=slice_cells)
        self.assertEqual(slice_admission["status"], "BLOCK")
        self.assertTrue(slice_admission["strategies"][0]["checks"][2]["triggered"])

    def test_only_candidate_cells_are_admission_inputs(self) -> None:
        candidate_cell = cell("dual_ma", variant_id="dual_ma:candidate")
        neighbor_cell = cell("dual_ma", variant_id="dual_ma:neighbor")
        unrelated = deepcopy(cell("dual_ma", variant_id="dual_ma:third"))
        unrelated["cost_sensitivity_status"] = "BLOCK"
        unrelated["cost_sensitivity"]["status"] = "BLOCK"
        unrelated["cost_sensitivity"]["break_even_preserved"] = False

        admission = build(
            ["dual_ma"],
            cells=[candidate_cell, neighbor_cell, unrelated],
        )

        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["admitted_variant_ids"], ["dual_ma:candidate"])

    def test_top_one_does_not_require_candidate_evidence_for_unselected_strategy(self) -> None:
        selection_cells = [
            cell(strategy_id, variant_id=f"{strategy_id}:{suffix}")
            for strategy_id in ("dual_ma", "rsi")
            for suffix in ("candidate", "neighbor", "third")
        ]
        for item in selection_cells:
            if str(item["variant_id"]).startswith("rsi:"):
                item.update({
                    "train_return_pct": 4.0,
                    "validation_return_pct": 3.0,
                    "validation_excess_return_pct": 1.0,
                })
            if item["variant_id"] == "rsi:third":
                item.update({
                    "train_return_pct": 0.1,
                    "validation_return_pct": 0.1,
                    "validation_excess_return_pct": 0.1,
                    "validation_max_drawdown_pct": 24.0,
                    "validation_sharpe": 0.1,
                    "validation_drawdown_improvement_pct": 0.1,
                    "validation_sharpe_excess": 0.1,
                    "validation_risk_efficiency_excess": 0.1,
                })
                item["cost_sensitivity_status"] = "BLOCK"
                item["cost_sensitivity"]["status"] = "BLOCK"
                item["cost_sensitivity"]["break_even_preserved"] = False

        admission = build(
            ["dual_ma", "rsi"],
            cells=selection_cells,
            max_test_candidates=1,
        )

        self.assertEqual(admission["status"], "PASS")
        self.assertEqual(admission["admitted_variant_ids"], ["dual_ma:candidate"])
        self.assertEqual(admission["strategies"][1]["status"], "PASS")
        self.assertEqual(
            [row["status"] for row in admission["strategies"][1]["checks"]],
            ["PASS", "NOT_APPLICABLE", "NOT_APPLICABLE"],
        )


if __name__ == "__main__":
    unittest.main()
