from __future__ import annotations

import copy
import io
import unittest
from contextlib import redirect_stdout

from examples.build_synthetic_strategy_benchmark_report_v2 import (
    SyntheticStrategyBenchmarkReportV2Error,
    build_synthetic_strategy_benchmark_report_v2,
    main,
    plan_synthetic_strategy_benchmark_report_v2,
    render_synthetic_strategy_benchmark_report_markdown_v2,
    verify_synthetic_strategy_benchmark_report_plan_v2,
    verify_synthetic_strategy_benchmark_report_v2,
)


class SyntheticStrategyBenchmarkReportEntrypointV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = plan_synthetic_strategy_benchmark_report_v2()
        cls.report = build_synthetic_strategy_benchmark_report_v2(execute=True)
        cls.markdown = render_synthetic_strategy_benchmark_report_markdown_v2(
            cls.report
        )

    def test_01_plan_is_dry_and_composes_v1_plus_six_analyses(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_plan_v2(self.plan)
        self.assertEqual(receipt["state"], "VERIFIED")
        self.assertEqual(receipt["evidence_state"], "GAP")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["planned_run_count"], 179)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertEqual(receipt["planned_market_analysis_count"], 6)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)

    def test_02_execution_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyBenchmarkReportV2Error):
                    build_synthetic_strategy_benchmark_report_v2(  # type: ignore[arg-type]
                        execute=value
                    )

    def test_03_report_and_both_nested_layers_verify(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_v2(self.report)
        self.assertEqual(receipt["state"], "VERIFIED")
        self.assertEqual(receipt["evidence_state"], "GAP")
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["executed_run_count"], 179)
        self.assertEqual(receipt["market_analysis_count"], 6)

    def test_04_bindings_lock_v1_and_market_regime_layers(self) -> None:
        self.assertEqual(
            set(self.report["bindings"]),
            {
                "source_report_plan_sha256",
                "source_report_sha256",
                "market_regime_plan_sha256",
                "market_regime_bundle_sha256",
            },
        )
        for digest in self.report["bindings"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_05_v1_is_immutable_and_top_level_gap_is_refined(self) -> None:
        self.assertEqual(
            self.report["source_report_v1"]["schema_version"],
            "synthetic-strategy-benchmark-report-v1",
        )
        self.assertIn("MARKET_REGIME_ANALYSIS_GAP", self.report["source_report_v1"]["gaps"])
        self.assertNotIn("MARKET_REGIME_ANALYSIS_GAP", self.report["gaps"])
        self.assertIn("HIGH_VOLATILITY_REGIME_COVERAGE_GAP", self.report["gaps"])

    def test_06_regime_counts_are_bound_without_new_backtests(self) -> None:
        self.assertEqual(self.report["observed_regime_slice_count"], 18)
        self.assertEqual(self.report["gap_regime_slice_count"], 6)
        self.assertEqual(self.report["additional_backtest_run_count"], 0)
        self.assertEqual(
            self.report["market_regime_validation"]["executed_run_count"], 0
        )

    def test_07_authority_remains_all_false(self) -> None:
        self.assertTrue(self.report["authority"])
        self.assertTrue(all(value is False for value in self.report["authority"].values()))

    def test_08_renderer_is_neutral_and_discloses_immutable_v1(self) -> None:
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("Immutable v1 Source Report", self.markdown)
        self.assertIn("Market-Regime Validation Layer", self.markdown)
        self.assertNotIn("READY", self.markdown)

    def test_09_default_cli_only_renders_the_v2_plan(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([])
        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Report Plan v2", rendered)
        self.assertIn("Executed runs: 0", rendered)
        self.assertNotIn("Immutable v1 Source Report", rendered)

    def test_10_tamper_fails_closed_and_rendering_is_deterministic(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        with self.assertRaises(SyntheticStrategyBenchmarkReportV2Error):
            verify_synthetic_strategy_benchmark_report_v2(tampered)
        tampered = copy.deepcopy(self.report)
        tampered["report_sha256"] = "0" * 64
        with self.assertRaises(SyntheticStrategyBenchmarkReportV2Error):
            verify_synthetic_strategy_benchmark_report_v2(tampered)
        self.assertEqual(
            self.markdown,
            render_synthetic_strategy_benchmark_report_markdown_v2(self.report),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
