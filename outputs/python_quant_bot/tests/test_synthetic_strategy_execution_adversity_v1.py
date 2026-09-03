from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application.synthetic_strategy_execution_adversity_v1 import (
    SyntheticStrategyExecutionAdversityError,
    build_synthetic_strategy_execution_adversity_v1,
    plan_synthetic_strategy_execution_adversity_v1,
    render_synthetic_strategy_execution_adversity_markdown_v1,
    replay_synthetic_strategy_execution_adversity_v1,
    verify_synthetic_strategy_execution_adversity_v1,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = canonical_trial_return_matrix_sha256(unsigned)


class SyntheticStrategyExecutionAdversityV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v10 import (
            SyntheticStrategyBenchmarkReportEntrypointV10Test,
        )

        if not hasattr(SyntheticStrategyBenchmarkReportEntrypointV10Test, "report"):
            SyntheticStrategyBenchmarkReportEntrypointV10Test.setUpClass()
        cls.source = SyntheticStrategyBenchmarkReportEntrypointV10Test.report
        cls.plan = plan_synthetic_strategy_execution_adversity_v1()
        cls.bundle = build_synthetic_strategy_execution_adversity_v1(
            cls.source, execute=True
        )
        cls.receipt = verify_synthetic_strategy_execution_adversity_v1(
            cls.bundle, cls.source
        )
        cls.markdown = render_synthetic_strategy_execution_adversity_markdown_v1(
            cls.bundle, cls.source
        )

    def test_01_plan_preregisters_three_scenarios_and_18_runs(self) -> None:
        self.assertEqual(len(self.plan["registered_strategy_ids"]), 6)
        self.assertEqual(len(self.plan["scenario_ids"]), 3)
        self.assertEqual(self.plan["planned_run_count"], 18)
        self.assertEqual(self.plan["additional_backtest_run_count"], 18)
        self.assertEqual(self.plan["source_logical_run_count"], 204)
        self.assertEqual(self.plan["total_logical_run_count"], 222)
        policy = self.plan["scenario_policy"]
        self.assertFalse(policy["partial_fill_modelled"])
        self.assertFalse(policy["liquidity_capacity_modelled"])
        self.assertFalse(policy["order_rejection_modelled"])

    def test_02_execution_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyExecutionAdversityError):
                    build_synthetic_strategy_execution_adversity_v1(
                        self.source, execute=value  # type: ignore[arg-type]
                    )

    def test_03_bundle_has_complete_strategy_scenario_cartesian_product(self) -> None:
        expected = [
            (strategy_id, scenario_id)
            for strategy_id in self.plan["registered_strategy_ids"]
            for scenario_id in self.plan["scenario_ids"]
        ]
        observed = [
            (run["strategy_id"], run["scenario_id"])
            for run in self.bundle["runs"]
        ]
        self.assertEqual(observed, expected)
        self.assertEqual(self.receipt["executed_run_count"], 18)
        self.assertEqual(self.receipt["total_logical_run_count"], 222)

    def test_04_delay_and_drop_reuse_exact_source_dataset(self) -> None:
        for run in self.bundle["runs"]:
            self.assertEqual(
                run["source_frozen_dataset_sha256"],
                self.bundle["source_frozen_dataset_sha256"],
            )
            if run["scenario_id"] == "source_fill_adverse_open_2pct":
                continue
            self.assertEqual(
                run["input_dataset_sha256"],
                run["source_frozen_input_dataset_sha256"],
            )
            self.assertEqual(run["input_row_count"], 200)

    def test_05_delay_wrapper_retains_one_terminal_signal(self) -> None:
        for run in self.bundle["runs"]:
            if run["scenario_id"] != "one_bar_signal_release_delay":
                continue
            metadata = run["scenario_metadata"]
            self.assertEqual(metadata["unreleased_terminal_signal_count"], 1)
            self.assertEqual(
                metadata["generated_signal_count"],
                metadata["released_signal_count"] + 1,
            )

    def test_06_drop_counts_follow_exact_every_third_rule(self) -> None:
        for run in self.bundle["runs"]:
            if run["scenario_id"] != "drop_every_third_actionable_signal":
                continue
            metadata = run["scenario_metadata"]
            self.assertEqual(
                metadata["dropped_signal_count"],
                metadata["actionable_signal_count"] // 3,
            )

    def test_07_adverse_open_events_have_directional_two_percent_shock(self) -> None:
        for run in self.bundle["runs"]:
            if run["scenario_id"] != "source_fill_adverse_open_2pct":
                continue
            metadata = run["scenario_metadata"]
            self.assertEqual(
                metadata["adverse_open_event_count"],
                len(metadata["adverse_open_events"]),
            )
            for event in metadata["adverse_open_events"]:
                source_open = float(event["source_open"])
                stressed_open = float(event["stressed_open"])
                expected = 1.02 if event["source_action"] == "BUY" else 0.98
                self.assertAlmostEqual(stressed_open / source_open, expected, places=14)

    def test_08_result_deltas_match_independent_source_subtraction(self) -> None:
        for run in self.bundle["runs"]:
            strategy_report = next(
                item
                for item in self.source["source_report_v9"]["source_report_v8"][
                    "benchmark_controls_bundle"
                ]["source_baseline_bundle"]["strategy_reports"]
                if item["strategy_id"] == run["strategy_id"]
            )
            source_result = strategy_report["runs"]["frozen_1x"]["result"]
            delta = run["source_result_delta"]
            self.assertAlmostEqual(
                float(delta["total_return_delta"]),
                float(run["result"]["total_return"])
                - float(source_result["total_return"]),
                places=14,
            )
            self.assertEqual(
                delta["trade_count_delta"],
                int(run["result"]["trades"]) - int(source_result["trades"]),
            )

    def test_09_source_extension_manifest_hashes_both_files(self) -> None:
        root = Path(__file__).resolve().parents[3]
        manifest = self.bundle["source_extension_manifest"]
        self.assertEqual(manifest["file_count"], 3)
        for record in manifest["files"]:
            payload = (root / record["path"]).read_bytes()
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_10_resealed_result_delta_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        run = tampered["runs"][0]
        run["source_result_delta"]["trade_count_delta"] = 999
        _reseal(run["source_result_delta"], "delta_sha256")
        _reseal(run, "run_sha256")
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyExecutionAdversityError):
            verify_synthetic_strategy_execution_adversity_v1(
                tampered, self.source
            )

    def test_11_authority_escalation_fails_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyExecutionAdversityError):
            verify_synthetic_strategy_execution_adversity_v1(
                tampered, self.source
            )

    def test_12_replay_and_renderer_remain_neutral(self) -> None:
        receipt = replay_synthetic_strategy_execution_adversity_v1(
            self.bundle, self.source
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["executed_run_count"], 18)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("Partial fills", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
