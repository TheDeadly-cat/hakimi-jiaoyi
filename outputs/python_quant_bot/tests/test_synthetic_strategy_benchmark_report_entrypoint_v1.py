from __future__ import annotations

import copy
import io
import unittest
from contextlib import redirect_stdout

from examples.build_synthetic_strategy_benchmark_report_v1 import (
    SyntheticStrategyBenchmarkReportError,
    build_synthetic_strategy_benchmark_report_v1,
    main,
    plan_synthetic_strategy_benchmark_report_v1,
    render_synthetic_strategy_benchmark_report_markdown_v1,
    render_synthetic_strategy_benchmark_report_plan_markdown_v1,
    verify_synthetic_strategy_benchmark_report_plan_v1,
    verify_synthetic_strategy_benchmark_report_v1,
)


class SyntheticStrategyBenchmarkReportEntrypointV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = plan_synthetic_strategy_benchmark_report_v1()
        cls.report = build_synthetic_strategy_benchmark_report_v1(execute=True)
        cls.markdown = render_synthetic_strategy_benchmark_report_markdown_v1(
            cls.report
        )

    def test_01_plan_composes_all_179_runs_without_mutation(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_plan_v1(self.plan)
        self.assertEqual(receipt["state"], "VERIFIED")
        self.assertEqual(self.plan["baseline_plan"]["planned_run_count"], 32)
        self.assertEqual(self.plan["robustness_plan"]["planned_run_count"], 147)
        self.assertEqual(receipt["planned_run_count"], 179)
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertFalse(receipt["runtime_mutations"])

    def test_02_execution_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyBenchmarkReportError):
                    build_synthetic_strategy_benchmark_report_v1(execute=value)  # type: ignore[arg-type]

    def test_03_complete_report_and_nested_evidence_verify(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_v1(self.report)
        self.assertEqual(receipt["state"], "VERIFIED")
        self.assertEqual(receipt["planned_run_count"], 179)
        self.assertEqual(receipt["executed_run_count"], 179)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["maturity"], "SYNTHETIC_BENCHMARK_ONLY")

    def test_04_bindings_lock_plans_and_both_evidence_objects(self) -> None:
        self.assertEqual(
            set(self.report["bindings"]),
            {
                "baseline_plan_sha256",
                "baseline_bundle_sha256",
                "robustness_plan_sha256",
                "robustness_evidence_sha256",
            },
        )
        for digest in self.report["bindings"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_05_authority_remains_false_and_gaps_are_explicit(self) -> None:
        self.assertTrue(self.report["authority"])
        self.assertTrue(all(value is False for value in self.report["authority"].values()))
        self.assertIn("REAL_DATASET_GAP", self.report["gaps"])
        self.assertIn("FORMAL_FROZEN_BLIND_TEST_GAP", self.report["gaps"])
        self.assertIn("MARKET_REGIME_ANALYSIS_GAP", self.report["gaps"])

    def test_06_renderer_is_neutral_and_contains_both_sections(self) -> None:
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("Frozen and Cost-Stress Evidence", self.markdown)
        self.assertIn("Walk-Forward, Stability, and Multiplicity Evidence", self.markdown)
        self.assertNotIn("READY", self.markdown)

    def test_07_default_cli_only_renders_the_dry_plan(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([])
        rendered = output.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("Report Plan v1", rendered)
        self.assertIn("Planned runs: 179", rendered)
        self.assertIn("Executed runs: 0", rendered)
        self.assertNotIn("Frozen and Cost-Stress Evidence", rendered)

    def test_08_outer_digest_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["report_sha256"] = "0" * 64
        with self.assertRaises(SyntheticStrategyBenchmarkReportError):
            verify_synthetic_strategy_benchmark_report_v1(tampered)

    def test_09_authority_escalation_fails_before_outer_digest(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        with self.assertRaises(SyntheticStrategyBenchmarkReportError):
            verify_synthetic_strategy_benchmark_report_v1(tampered)

    def test_10_rendering_is_deterministic(self) -> None:
        self.assertEqual(
            self.markdown,
            render_synthetic_strategy_benchmark_report_markdown_v1(self.report),
        )
        self.assertEqual(
            render_synthetic_strategy_benchmark_report_plan_markdown_v1(self.plan),
            render_synthetic_strategy_benchmark_report_plan_markdown_v1(self.plan),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
