from __future__ import annotations

import copy
import unittest

from examples.build_synthetic_strategy_benchmark_report_v3 import (
    GAPS,
    PLAN_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    SyntheticStrategyBenchmarkReportV3Error,
    build_synthetic_strategy_benchmark_report_v3,
    plan_synthetic_strategy_benchmark_report_v3,
    render_synthetic_strategy_benchmark_report_markdown_v3,
    render_synthetic_strategy_benchmark_report_plan_markdown_v3,
    verify_synthetic_strategy_benchmark_report_plan_v3,
    verify_synthetic_strategy_benchmark_report_v3,
)
from exchange_terminal.application.synthetic_strategy_bootstrap_validation_v1 import (
    verify_synthetic_strategy_bootstrap_validation_v1,
)


class SyntheticStrategyBenchmarkReportEntrypointV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = plan_synthetic_strategy_benchmark_report_v3()
        cls.report = build_synthetic_strategy_benchmark_report_v3(execute=True)

    def test_01_plan_reuses_179_runs_and_adds_zero_backtests(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_plan_v3(self.plan)
        self.assertTrue(receipt["valid"])
        self.assertEqual(self.plan["schema_version"], PLAN_SCHEMA_VERSION)
        self.assertEqual(self.plan["planned_run_count"], 179)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_market_analysis_count"], 6)
        self.assertEqual(self.plan["planned_bootstrap_analysis_count"], 6)
        self.assertEqual(self.plan["executed_run_count"], 0)
        self.assertFalse(self.plan["runtime_mutations"])

    def test_02_dry_plan_is_default_and_execute_requires_exact_bool(self) -> None:
        self.assertEqual(build_synthetic_strategy_benchmark_report_v3(), self.plan)
        with self.assertRaises(SyntheticStrategyBenchmarkReportV3Error):
            build_synthetic_strategy_benchmark_report_v3(execute=1)  # type: ignore[arg-type]

    def test_03_report_and_receipt_verify(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_v3(self.report)
        self.assertTrue(receipt["valid"])
        self.assertEqual(self.report["schema_version"], REPORT_SCHEMA_VERSION)
        self.assertEqual(receipt["report_sha256"], self.report["report_sha256"])
        self.assertEqual(receipt["status"], "BLOCK")

    def test_04_source_v2_and_bootstrap_bundle_are_consumer_verified(self) -> None:
        source_v2 = self.report["source_report_v2"]
        baseline = source_v2["source_report_v1"]["baseline_bundle"]
        receipt = verify_synthetic_strategy_bootstrap_validation_v1(
            self.report["bootstrap_validation"],
            baseline,
        )
        bootstrap = self.report["bootstrap_validation"]
        self.assertEqual(
            receipt["schema_version"],
            "synthetic-strategy-bootstrap-validation-receipt-v1",
        )
        self.assertEqual(receipt["bundle_sha256"], bootstrap["bundle_sha256"])
        self.assertEqual(receipt["state"], bootstrap["evidence_state"])
        self.assertEqual(receipt["strategy_count"], len(bootstrap["strategy_records"]))
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertFalse(receipt["runtime_mutations"])
        self.assertEqual(
            bootstrap["schema_version"],
            "synthetic-strategy-bootstrap-validation-bundle-v1",
        )

    def test_05_counts_prove_six_analyses_and_zero_added_runs(self) -> None:
        self.assertEqual(self.report["planned_run_count"], 179)
        self.assertEqual(self.report["executed_run_count"], 179)
        self.assertEqual(self.report["additional_backtest_run_count"], 0)
        self.assertEqual(self.report["market_analysis_count"], 6)
        self.assertEqual(self.report["bootstrap_analysis_count"], 6)
        self.assertEqual(self.report["observed_bootstrap_evidence_count"], 6)
        self.assertEqual(self.report["gap_bootstrap_evidence_count"], 0)
        self.assertFalse(self.report["runtime_mutations"])

    def test_06_bindings_lock_source_baseline_and_bootstrap_hashes(self) -> None:
        source_v2 = self.report["source_report_v2"]
        baseline = source_v2["source_report_v1"]["baseline_bundle"]
        bootstrap = self.report["bootstrap_validation"]
        self.assertEqual(
            self.report["bindings"],
            {
                "source_report_v2_sha256": source_v2["report_sha256"],
                "source_report_v2_plan_sha256": source_v2["plan"]["plan_sha256"],
                "source_baseline_bundle_sha256": baseline["bundle_sha256"],
                "bootstrap_bundle_sha256": bootstrap["bundle_sha256"],
                "bootstrap_plan_sha256": bootstrap["plan"]["plan_sha256"],
            },
        )

    def test_07_only_bootstrap_gap_is_closed_and_inference_stays_denied(self) -> None:
        self.assertNotIn("BOOTSTRAP_CONFIDENCE_INTERVAL_GAP", self.report["gaps"])
        self.assertIn("NO_FORMAL_INFERENCE_AUTHORITY", self.report["gaps"])
        self.assertEqual(self.report["gaps"], GAPS)
        self.assertEqual(self.report["evidence_state"], "GAP")
        self.assertEqual(self.report["status"], "BLOCK")
        self.assertTrue(all(value is False for value in self.report["authority"].values()))

    def test_08_nested_bootstrap_authority_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bootstrap_validation"]["authority"]["profitability_proven"] = True
        with self.assertRaises(SyntheticStrategyBenchmarkReportV3Error):
            verify_synthetic_strategy_benchmark_report_v3(tampered)

    def test_09_binding_or_report_hash_tamper_fails_closed(self) -> None:
        binding_tamper = copy.deepcopy(self.report)
        binding_tamper["bindings"]["bootstrap_bundle_sha256"] = "0" * 64
        with self.assertRaises(SyntheticStrategyBenchmarkReportV3Error):
            verify_synthetic_strategy_benchmark_report_v3(binding_tamper)

        hash_tamper = copy.deepcopy(self.report)
        hash_tamper["report_sha256"] = "f" * 64
        with self.assertRaises(SyntheticStrategyBenchmarkReportV3Error):
            verify_synthetic_strategy_benchmark_report_v3(hash_tamper)

    def test_10_renderers_are_neutral_and_non_authorizing(self) -> None:
        rendered_plan = render_synthetic_strategy_benchmark_report_plan_markdown_v3(
            self.plan
        )
        rendered_report = render_synthetic_strategy_benchmark_report_markdown_v3(
            self.report
        )
        for rendered in (rendered_plan, rendered_report):
            upper = rendered.upper()
            self.assertIn("SOURCE:", upper)
            self.assertIn("GAP:", upper)
            self.assertIn("MATURITY:", upper)
            self.assertIn("PERMISSION: BLOCK", upper)
            self.assertNotIn("READY", upper)
            self.assertNotIn("SIGNIFICANT", upper)
        self.assertIn("Additional bootstrap backtest runs: 0", rendered_report)
        self.assertIn("No formal inference", rendered_report)


if __name__ == "__main__":
    unittest.main()
