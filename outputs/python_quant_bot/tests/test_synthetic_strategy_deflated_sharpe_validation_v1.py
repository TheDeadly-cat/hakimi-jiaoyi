from __future__ import annotations

import copy
import math
import unittest
from statistics import NormalDist, mean, stdev

from exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1 import (
    SyntheticStrategyDeflatedSharpeValidationError,
    build_synthetic_strategy_deflated_sharpe_validation_v1,
    plan_synthetic_strategy_deflated_sharpe_validation_v1,
    render_synthetic_strategy_deflated_sharpe_validation_markdown_v1,
    replay_synthetic_strategy_deflated_sharpe_validation_v1,
    verify_synthetic_strategy_deflated_sharpe_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (
    build_synthetic_strategy_trial_return_matrix_v1,
)
from hakimi_research.deflated_sharpe_diagnostic import (
    EULER_MASCHERONI,
    DeflatedSharpeDiagnosticError,
    build_deflated_sharpe_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    build_strategy_trial_return_matrix,
    canonical_trial_return_matrix_sha256,
)


class _TextAlias(str):
    pass


class SyntheticStrategyDeflatedSharpeValidationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.matrix_bundle = build_synthetic_strategy_trial_return_matrix_v1(
            cls.baseline, execute=True
        )
        cls.plan = plan_synthetic_strategy_deflated_sharpe_validation_v1()
        cls.bundle = build_synthetic_strategy_deflated_sharpe_validation_v1(
            cls.matrix_bundle, execute=True
        )
        cls.markdown = (
            render_synthetic_strategy_deflated_sharpe_validation_markdown_v1(
                cls.bundle
            )
        )

    @staticmethod
    def _matrix_inputs(matrix: dict) -> dict:
        binding = matrix["source_binding"]
        return {
            "strategy_id": matrix["strategy_id"],
            "search_family_id": matrix["search_family_id"],
            "observation_class": matrix["observation_class"],
            "source_plan_sha256": binding["source_plan_sha256"],
            "source_robustness_bundle_sha256": binding[
                "source_robustness_bundle_sha256"
            ],
            "source_run_ledger_sha256": binding["source_run_ledger_sha256"],
            "preregistered_trial_ids": list(matrix["preregistered_trial_ids"]),
            "selected_trial_id": matrix["selected_trial_id"],
            "selection_rule": matrix["selection_rule"],
            "evaluation_role": matrix["evaluation_role"],
            "periods_per_year": matrix["periods_per_year"],
            "candidate_cells": [
                {
                    "trial_id": row["trial_id"],
                    "source_observation": copy.deepcopy(row["source_observation"]),
                    "source_run": copy.deepcopy(row["source_run"]),
                }
                for row in matrix["candidate_rows"]
            ],
        }

    @staticmethod
    def _reseal_cell(cell: dict) -> None:
        run = cell["source_run"]
        run["result_sha256"] = canonical_trial_return_matrix_sha256(run["result"])
        run["run_sha256"] = canonical_trial_return_matrix_sha256(
            {key: value for key, value in run.items() if key != "run_sha256"}
        )
        observation = cell["source_observation"]
        observation["result_sha256"] = run["result_sha256"]
        observation["source_run_sha256"] = run["run_sha256"]
        observation["record_sha256"] = canonical_trial_return_matrix_sha256(
            {
                key: value
                for key, value in observation.items()
                if key != "record_sha256"
            }
        )

    @staticmethod
    def _pearson(left: list[float], right: list[float]) -> float:
        left_mean = mean(left)
        right_mean = mean(right)
        left_delta = [value - left_mean for value in left]
        right_delta = [value - right_mean for value in right]
        return sum(
            left_value * right_value
            for left_value, right_value in zip(left_delta, right_delta)
        ) / math.sqrt(
            sum(value**2 for value in left_delta)
            * sum(value**2 for value in right_delta)
        )

    def test_01_plan_adds_six_analyses_and_zero_backtest_runs(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_analysis_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyDeflatedSharpeValidationError):
                    build_synthetic_strategy_deflated_sharpe_validation_v1(
                        self.matrix_bundle, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_and_all_six_diagnostics_verify(self) -> None:
        receipt = verify_synthetic_strategy_deflated_sharpe_validation_v1(
            self.bundle
        )
        self.assertEqual(receipt["state"], "OBSERVED")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["executed_analysis_count"], 6)
        self.assertEqual(receipt["source_reused_run_count"], 147)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertFalse(receipt["formal_inference_claimed"])
        self.assertIsNone(receipt["decision_threshold"])

    def test_04_diagnostics_retain_all_trials_and_selected_center(self) -> None:
        for record in self.bundle["strategy_records"]:
            diagnostic = record["deflated_sharpe_diagnostic"]
            with self.subTest(strategy_id=record["strategy_id"]):
                self.assertEqual(diagnostic["trial_count"], 3)
                self.assertEqual(diagnostic["observation_count"], 169)
                self.assertEqual(len(diagnostic["trial_statistics"]), 3)
                self.assertEqual(len(diagnostic["pairwise_correlations"]), 3)
                self.assertTrue(diagnostic["selected_trial_id"].endswith(":center"))
                probability = float(diagnostic["deflated_sharpe_probability"])
                self.assertGreaterEqual(probability, 0.0)
                self.assertLessEqual(probability, 1.0)

    def test_05_policy_locks_paper_equations_and_non_inferential_scope(self) -> None:
        policy = self.plan["policy"]
        self.assertEqual(
            policy["implied_independent_trials_formula"],
            "N=RHO_BAR+(1-RHO_BAR)*M",
        )
        self.assertIn("PHI_INV", policy["expected_maximum_formula"])
        self.assertIn("KURTOSIS", policy["deflated_sharpe_formula"])
        self.assertEqual(
            policy["candidate_sharpe_dispersion"],
            "SAMPLE_VARIANCE_ACROSS_ALL_PREREGISTERED_TRIALS_DDOF_1",
        )
        self.assertFalse(policy["formal_inference_claimed"])
        self.assertIsNone(policy["decision_threshold"])

    def test_06_independent_formula_recalculation_matches_each_diagnostic(self) -> None:
        for source_record, output_record in zip(
            self.matrix_bundle["strategy_records"], self.bundle["strategy_records"]
        ):
            matrix = source_record["trial_return_matrix"]
            diagnostic = output_record["deflated_sharpe_diagnostic"]
            series = [
                [float(value) for value in row["period_returns"]]
                for row in matrix["candidate_rows"]
            ]
            sharpes = [mean(values) / stdev(values) for values in series]
            sharpe_std = stdev(sharpes)
            correlations = [
                self._pearson(series[left], series[right])
                for left in range(3)
                for right in range(left + 1, 3)
            ]
            average_correlation = mean(correlations)
            independent_trials = average_correlation + (
                1.0 - average_correlation
            ) * 3
            normal = NormalDist()
            threshold = sharpe_std * (
                (1.0 - EULER_MASCHERONI)
                * normal.inv_cdf(1.0 - 1.0 / independent_trials)
                + EULER_MASCHERONI
                * normal.inv_cdf(1.0 - 1.0 / (independent_trials * math.e))
            )
            selected_index = matrix["preregistered_trial_ids"].index(
                matrix["selected_trial_id"]
            )
            selected = series[selected_index]
            selected_mean = mean(selected)
            selected_sharpe = selected_mean / stdev(selected)
            deviations = [value - selected_mean for value in selected]
            second = sum(value**2 for value in deviations) / len(selected)
            skewness = (
                sum(value**3 for value in deviations) / len(selected)
            ) / second**1.5
            kurtosis = (
                sum(value**4 for value in deviations) / len(selected)
            ) / second**2
            adjustment = (
                1.0
                - skewness * selected_sharpe
                + ((kurtosis - 1.0) / 4.0) * selected_sharpe**2
            )
            statistic = (
                (selected_sharpe - threshold)
                * math.sqrt(len(selected) - 1)
                / math.sqrt(adjustment)
            )
            probability = normal.cdf(statistic)
            with self.subTest(strategy_id=matrix["strategy_id"]):
                self.assertAlmostEqual(
                    float(diagnostic["average_pairwise_correlation"]),
                    average_correlation,
                    places=12,
                )
                self.assertAlmostEqual(
                    float(diagnostic["effective_independent_trial_count"]),
                    independent_trials,
                    places=12,
                )
                self.assertAlmostEqual(
                    float(diagnostic["expected_maximum_non_annualised_sharpe"]),
                    threshold,
                    places=12,
                )
                self.assertAlmostEqual(
                    float(diagnostic["deflated_sharpe_probability"]),
                    probability,
                    places=12,
                )

    def test_07_zero_variance_candidate_fails_closed(self) -> None:
        source_matrix = self.matrix_bundle["strategy_records"][0][
            "trial_return_matrix"
        ]
        inputs = self._matrix_inputs(source_matrix)
        cell = inputs["candidate_cells"][0]
        curve = cell["source_run"]["result"]["equity_curve"]
        constant = curve[0]["equity"]
        for point in curve:
            point["equity"] = constant
        self._reseal_cell(cell)
        degenerate_matrix = build_strategy_trial_return_matrix(**inputs)
        with self.assertRaises(DeflatedSharpeDiagnosticError):
            build_deflated_sharpe_diagnostic(degenerate_matrix)

    def test_08_exact_native_subclass_is_rejected(self) -> None:
        matrix = copy.deepcopy(
            self.matrix_bundle["strategy_records"][0]["trial_return_matrix"]
        )
        matrix["selected_trial_id"] = _TextAlias(matrix["selected_trial_id"])
        with self.assertRaises(DeflatedSharpeDiagnosticError):
            build_deflated_sharpe_diagnostic(matrix)

    def test_09_nested_diagnostic_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["strategy_records"][0]["deflated_sharpe_diagnostic"][
            "deflated_sharpe_probability"
        ] = "1"
        with self.assertRaises(SyntheticStrategyDeflatedSharpeValidationError):
            verify_synthetic_strategy_deflated_sharpe_validation_v1(tampered)

    def test_10_authority_escalation_fails_even_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        tampered["bundle_sha256"] = canonical_trial_return_matrix_sha256(
            {
                key: value
                for key, value in tampered.items()
                if key != "bundle_sha256"
            }
        )
        with self.assertRaises(SyntheticStrategyDeflatedSharpeValidationError):
            verify_synthetic_strategy_deflated_sharpe_validation_v1(tampered)

    def test_11_replay_is_exact_and_executes_zero_backtests(self) -> None:
        receipt = replay_synthetic_strategy_deflated_sharpe_validation_v1(
            self.bundle
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["replayed_analysis_count"], 6)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_12_renderer_is_neutral_and_retains_pbo_gap(self) -> None:
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("PROBABILITY_OF_BACKTEST_OVERFITTING_GAP", self.markdown)
        self.assertIn("without a decision threshold", self.markdown)
        self.assertIn("Formal inference authority: false", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
