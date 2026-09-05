from __future__ import annotations

import copy
import unittest

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (
    SyntheticStrategyTrialReturnMatrixError,
    build_synthetic_strategy_trial_return_matrix_v1,
    plan_synthetic_strategy_trial_return_matrix_v1,
    render_synthetic_strategy_trial_return_matrix_markdown_v1,
    verify_synthetic_strategy_trial_return_matrix_v1,
)
from hakimi_research.trial_return_matrix import (
    TrialReturnMatrixError,
    build_strategy_trial_return_matrix,
    canonical_trial_return_matrix_sha256,
)


class _TextAlias(str):
    pass


class SyntheticStrategyTrialReturnMatrixV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.plan = plan_synthetic_strategy_trial_return_matrix_v1()
        cls.bundle = build_synthetic_strategy_trial_return_matrix_v1(
            cls.baseline, execute=True
        )
        cls.markdown = render_synthetic_strategy_trial_return_matrix_markdown_v1(
            cls.bundle
        )

    @staticmethod
    def _inputs(matrix: dict) -> dict:
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
        run_payload = {key: value for key, value in run.items() if key != "run_sha256"}
        run["run_sha256"] = canonical_trial_return_matrix_sha256(run_payload)
        observation = cell["source_observation"]
        observation["dataset_sha256"] = run["dataset_sha256"]
        observation["result_sha256"] = run["result_sha256"]
        observation["source_run_sha256"] = run["run_sha256"]
        observation_payload = {
            key: value for key, value in observation.items() if key != "record_sha256"
        }
        observation["record_sha256"] = canonical_trial_return_matrix_sha256(
            observation_payload
        )

    def test_01_plan_reuses_147_runs_and_adds_zero_backtests(self) -> None:
        self.assertEqual(self.plan["source_required_baseline_run_count"], 32)
        self.assertEqual(self.plan["reused_robustness_run_count"], 147)
        self.assertEqual(self.plan["planned_run_count"], 147)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 6)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_execution_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyTrialReturnMatrixError):
                    build_synthetic_strategy_trial_return_matrix_v1(
                        self.baseline, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_and_all_six_matrices_verify(self) -> None:
        receipt = verify_synthetic_strategy_trial_return_matrix_v1(self.bundle)
        self.assertEqual(receipt["state"], "OBSERVED")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["strategy_count"], 6)
        self.assertEqual(receipt["trial_count"], 18)
        self.assertEqual(receipt["observation_count_per_trial"], 169)
        self.assertEqual(receipt["executed_run_count"], 147)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_04_every_matrix_is_aligned_source_bound_and_complete(self) -> None:
        for record in self.bundle["strategy_records"]:
            matrix = record["trial_return_matrix"]
            with self.subTest(strategy_id=matrix["strategy_id"]):
                self.assertEqual(matrix["trial_count"], 3)
                self.assertEqual(matrix["observation_count"], 169)
                self.assertEqual(
                    [row["trial_id"] for row in matrix["candidate_rows"]],
                    matrix["preregistered_trial_ids"],
                )
                self.assertTrue(
                    all(row["period_return_count"] == 169 for row in matrix["candidate_rows"])
                )
                self.assertTrue(
                    all(
                        row["source_observation"]["phase"] == "FROZEN_STABILITY"
                        for row in matrix["candidate_rows"]
                    )
                )
                self.assertTrue(
                    matrix["selected_trial_id"].endswith(":center")
                )

    def test_05_missing_duplicate_and_extra_trials_fail_closed(self) -> None:
        matrix = self.bundle["strategy_records"][0]["trial_return_matrix"]
        for mutation in ("missing", "duplicate", "extra"):
            inputs = self._inputs(matrix)
            if mutation == "missing":
                inputs["candidate_cells"].pop()
            elif mutation == "duplicate":
                inputs["candidate_cells"][1]["trial_id"] = inputs["candidate_cells"][0][
                    "trial_id"
                ]
            else:
                inputs["candidate_cells"].append(copy.deepcopy(inputs["candidate_cells"][-1]))
            with self.subTest(mutation=mutation):
                with self.assertRaises(TrialReturnMatrixError):
                    build_strategy_trial_return_matrix(**inputs)

    def test_06_timestamp_reorder_and_unequal_lengths_fail_closed(self) -> None:
        matrix = self.bundle["strategy_records"][0]["trial_return_matrix"]
        for mutation in ("reorder", "short"):
            inputs = self._inputs(matrix)
            curve = inputs["candidate_cells"][1]["source_run"]["result"]["equity_curve"]
            if mutation == "reorder":
                curve[10], curve[11] = curve[11], curve[10]
            else:
                curve.pop()
            self._reseal_cell(inputs["candidate_cells"][1])
            with self.subTest(mutation=mutation):
                with self.assertRaises(TrialReturnMatrixError):
                    build_strategy_trial_return_matrix(**inputs)

    def test_07_dataset_cost_and_role_mixing_fail_closed(self) -> None:
        matrix = self.bundle["strategy_records"][0]["trial_return_matrix"]
        for mutation in ("dataset", "cost", "role"):
            inputs = self._inputs(matrix)
            run = inputs["candidate_cells"][1]["source_run"]
            if mutation == "dataset":
                run["dataset_sha256"] = "0" * 64
            elif mutation == "cost":
                run["fee_rate"] = 0.123
            else:
                run["evaluation_role"] = "SYNTHETIC_WRONG_ROLE"
            self._reseal_cell(inputs["candidate_cells"][1])
            with self.subTest(mutation=mutation):
                with self.assertRaises(TrialReturnMatrixError):
                    build_strategy_trial_return_matrix(**inputs)

    def test_08_nonfinite_bool_subclass_and_scalar_inputs_fail_closed(self) -> None:
        matrix = self.bundle["strategy_records"][0]["trial_return_matrix"]
        mutations = ("nan", "bool", "subclass", "scalar")
        for mutation in mutations:
            inputs = self._inputs(matrix)
            cell = inputs["candidate_cells"][0]
            if mutation == "nan":
                cell["source_run"]["result"]["equity_curve"][1]["equity"] = float("nan")
            elif mutation == "bool":
                cell["source_run"]["result"]["equity_curve"][1]["equity"] = True
                self._reseal_cell(cell)
            elif mutation == "subclass":
                cell["trial_id"] = _TextAlias(cell["trial_id"])
            else:
                cell["source_run"]["result"]["equity_curve"] = cell["source_run"][
                    "result"
                ]["sharpe_ratio"]
                self._reseal_cell(cell)
            with self.subTest(mutation=mutation):
                with self.assertRaises(TrialReturnMatrixError):
                    build_strategy_trial_return_matrix(**inputs)

    def test_09_nested_matrix_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["strategy_records"][0]["trial_return_matrix"]["candidate_rows"][0][
            "period_returns"
        ][0] = "999"
        with self.assertRaises(SyntheticStrategyTrialReturnMatrixError):
            verify_synthetic_strategy_trial_return_matrix_v1(tampered)

    def test_10_authority_escalation_fails_even_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        payload = {key: value for key, value in tampered.items() if key != "bundle_sha256"}
        tampered["bundle_sha256"] = canonical_trial_return_matrix_sha256(payload)
        with self.assertRaises(SyntheticStrategyTrialReturnMatrixError):
            verify_synthetic_strategy_trial_return_matrix_v1(tampered)

    def test_11_renderer_is_neutral_and_retains_statistical_gaps(self) -> None:
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("not a DSR or PBO result", self.markdown)
        self.assertIn("Formal inference authority: false", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
