from __future__ import annotations

import copy
import math
import statistics
import unittest

from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    SyntheticStrategyBenchmarkControlsError,
    build_synthetic_strategy_benchmark_controls_v1,
    plan_synthetic_strategy_benchmark_controls_v1,
    render_synthetic_strategy_benchmark_controls_markdown_v1,
    replay_synthetic_strategy_benchmark_controls_v1,
    verify_synthetic_strategy_benchmark_controls_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    build_synthetic_strategy_report_bundle_v1,
    canonical_sha256,
)


def _reseal(record: dict, field: str) -> None:
    record[field] = canonical_sha256(
        {key: value for key, value in record.items() if key != field}
    )


class SyntheticStrategyBenchmarkControlsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = build_synthetic_strategy_report_bundle_v1(execute=True)
        cls.plan = plan_synthetic_strategy_benchmark_controls_v1()
        cls.bundle = build_synthetic_strategy_benchmark_controls_v1(
            cls.source, execute=True
        )
        cls.receipt = verify_synthetic_strategy_benchmark_controls_v1(
            cls.bundle
        )
        cls.markdown = render_synthetic_strategy_benchmark_controls_markdown_v1(
            cls.bundle
        )

    def test_01_plan_preregisters_eighteen_control_runs(self) -> None:
        self.assertEqual(self.plan["source_required_run_count"], 32)
        self.assertEqual(self.plan["planned_run_count"], 18)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 18)
        self.assertEqual(len(self.plan["planned_control_runs"]), 18)
        self.assertEqual(
            {item["subject_type"] for item in self.plan["planned_control_runs"]},
            {"BENCHMARK_CONTROL"},
        )
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_execute_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyBenchmarkControlsError):
                    build_synthetic_strategy_benchmark_controls_v1(
                        self.source, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_counts_and_authority_verify(self) -> None:
        self.assertEqual(self.receipt["state"], "OBSERVED_WITH_GAPS")
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertEqual(self.receipt["source_reused_run_count"], 32)
        self.assertEqual(self.receipt["executed_run_count"], 18)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 18)
        self.assertEqual(self.receipt["direct_control_run_count"], 2)
        self.assertEqual(self.receipt["no_skill_path_count"], 16)
        self.assertEqual(self.receipt["volatility_projection_count"], 6)
        self.assertEqual(self.receipt["strategy_comparison_count"], 6)
        self.assertFalse(self.receipt["runtime_mutations"])

    def test_04_controls_use_same_frozen_dataset_and_cost(self) -> None:
        frozen_hash = self.source["fixture"]["partition_protocol"]["partitions"][
            "frozen"
        ]["dataset_sha256"]
        for run in self.bundle["control_runs"]:
            with self.subTest(control_id=run["control_id"]):
                self.assertEqual(run["dataset_sha256"], frozen_hash)
                self.assertEqual(run["fee_rate"], 0.0005)
                self.assertEqual(run["slippage_pct"], 0.0002)
                self.assertEqual(run["cost_multiplier"], 1)
                self.assertFalse(
                    run["result"]["experiment_manifest"][
                        "result_is_profitability_proof"
                    ]
                )

    def test_05_registered_candidates_are_not_relabelled_controls(self) -> None:
        control_ids = {run["control_id"] for run in self.bundle["control_runs"]}
        registered_ids = set(self.source["plan"]["registered_strategy_ids"])
        self.assertTrue(control_ids.isdisjoint(registered_ids))
        self.assertEqual(
            {run["subject_type"] for run in self.bundle["control_runs"]},
            {"BENCHMARK_CONTROL"},
        )
        self.assertEqual(
            self.bundle["plan"]["reused_benchmark_ids"],
            ["cash", "buy_and_hold"],
        )

    def test_06_all_no_skill_paths_are_retained_without_selection(self) -> None:
        distribution = self.bundle["no_skill_distribution"]
        self.assertEqual(distribution["path_count"], 16)
        self.assertEqual(len(distribution["path_records"]), 16)
        self.assertTrue(distribution["all_paths_retained"])
        self.assertIsNone(distribution["selected_path_id"])
        self.assertEqual(
            len({item["seed_id"] for item in distribution["path_records"]}), 16
        )

    def test_07_no_skill_median_matches_independent_calculation(self) -> None:
        values = [
            float(run["result"]["total_return"])
            for run in self.bundle["control_runs"]
            if run["control_kind"] == "HASH_NO_SKILL"
        ]
        self.assertEqual(len(values), 16)
        self.assertAlmostEqual(
            float(self.bundle["no_skill_distribution"]["summary"]["median_type7"]),
            statistics.median(values),
            places=12,
        )

    def test_08_equal_volatility_projection_matches_strategy_volatility(self) -> None:
        for projection in self.bundle["volatility_matched_projections"]:
            with self.subTest(strategy_id=projection["strategy_id"]):
                self.assertEqual(projection["observation_count"], 169)
                self.assertAlmostEqual(
                    float(projection["strategy_annualised_sample_volatility"]),
                    float(projection["projected_annualised_sample_volatility"]),
                    places=12,
                )
                self.assertFalse(projection["executable_claim"])
                self.assertFalse(projection["financing_modelled"])
                self.assertFalse(projection["margin_modelled"])

    def test_09_comparisons_include_all_six_controls_without_ranking(self) -> None:
        expected_controls = {
            "cash",
            "buy_and_hold",
            "simple_ma",
            "simple_breakout",
            "hash_no_skill_median",
            "volatility_matched_buy_and_hold",
        }
        for comparison in self.bundle["strategy_control_comparisons"]:
            with self.subTest(strategy_id=comparison["strategy_id"]):
                self.assertEqual(
                    set(comparison["control_total_returns"]), expected_controls
                )
                self.assertEqual(
                    set(comparison["strategy_minus_control_return_deltas"]),
                    expected_controls,
                )
                self.assertFalse(comparison["ranking_performed"])
                self.assertIsNone(comparison["decision_threshold"])

    def test_10_return_deltas_recalculate_independently(self) -> None:
        for comparison in self.bundle["strategy_control_comparisons"]:
            strategy_return = float(comparison["strategy_frozen_total_return"])
            for control_id, control_return in comparison[
                "control_total_returns"
            ].items():
                with self.subTest(
                    strategy_id=comparison["strategy_id"], control_id=control_id
                ):
                    self.assertAlmostEqual(
                        float(
                            comparison["strategy_minus_control_return_deltas"][
                                control_id
                            ]
                        ),
                        strategy_return - float(control_return),
                        places=12,
                    )

    def test_11_resealed_control_identity_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        run = tampered["control_runs"][0]
        run["control_id"] = "dual_ma"
        _reseal(run, "run_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyBenchmarkControlsError):
            verify_synthetic_strategy_benchmark_controls_v1(tampered)

    def test_12_resealed_projection_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        projection = tampered["volatility_matched_projections"][0]
        projection["scaling_multiplier"] = "999"
        _reseal(projection, "projection_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyBenchmarkControlsError):
            verify_synthetic_strategy_benchmark_controls_v1(tampered)

    def test_13_authority_escalation_fails_even_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyBenchmarkControlsError):
            verify_synthetic_strategy_benchmark_controls_v1(tampered)

    def test_14_replay_and_renderer_remain_neutral(self) -> None:
        replay = replay_synthetic_strategy_benchmark_controls_v1(self.bundle)
        self.assertEqual(replay["replay_status"], "EXACT_MATCH")
        self.assertEqual(replay["replayed_run_count"], 18)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("no random path is selected", self.markdown)
        self.assertIn("without financing or margin modelling", self.markdown)
        for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
            self.assertNotIn(forbidden, self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
