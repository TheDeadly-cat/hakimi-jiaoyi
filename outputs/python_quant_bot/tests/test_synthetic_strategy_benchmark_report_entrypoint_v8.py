from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v8 import (
    build_synthetic_strategy_benchmark_report_v8,
    plan_synthetic_strategy_benchmark_report_v8,
    render_synthetic_strategy_benchmark_report_markdown_v8,
    render_synthetic_strategy_benchmark_report_plan_markdown_v8,
    verify_synthetic_strategy_benchmark_report_v8,
)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = _sha256_json(unsigned)


class SyntheticStrategyBenchmarkReportEntrypointV8Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_controls_v1 import (
            SyntheticStrategyBenchmarkControlsV1Tests,
        )
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v7 import (
            SyntheticStrategyBenchmarkReportEntrypointV7Test,
        )

        SyntheticStrategyBenchmarkReportEntrypointV7Test.setUpClass()
        SyntheticStrategyBenchmarkControlsV1Tests.setUpClass()
        cls.source_report_v7 = (
            SyntheticStrategyBenchmarkReportEntrypointV7Test.report
        )
        cls.controls = SyntheticStrategyBenchmarkControlsV1Tests.bundle
        cls.report = build_synthetic_strategy_benchmark_report_v8(
            cls.source_report_v7,
            cls.controls,
            execute=True,
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v8(cls.report)

    def test_01_plan_preregisters_deduplicated_204_run_ledger(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v8()
        self.assertEqual(plan["inherited_source_logical_run_count"], 186)
        self.assertEqual(plan["shared_baseline_reused_run_count"], 32)
        self.assertEqual(plan["independent_control_run_count"], 18)
        self.assertEqual(plan["source_logical_run_count"], 204)
        self.assertEqual(plan["planned_control_analysis_count"], 13)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertTrue(plan["requires_shared_baseline_bundle_identity"])
        self.assertFalse(plan["runtime_mutations"])

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v8(  # type: ignore[arg-type]
                        execute=value
                    )

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v8(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v8(
                self.source_report_v7,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v8(
                benchmark_controls_bundle=self.controls,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v8(
                self.source_report_v7,
                self.controls,
                execute=False,
            )

    def test_04_receipt_retains_denied_zero_run_composition(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 204)
        self.assertEqual(self.receipt["independent_control_run_count"], 18)
        self.assertEqual(self.receipt["control_executed_analysis_count"], 13)
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertEqual(self.receipt["evidence_state"], "GAP")
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(self.receipt["runtime_mutations"])
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_05_shared_baseline_is_bound_without_duplicate_counting(self) -> None:
        baseline = self.controls["source_baseline_bundle"]
        self.assertEqual(
            self.report["bindings"]["shared_baseline_bundle_sha256"],
            baseline["bundle_sha256"],
        )
        self.assertGreaterEqual(self.report["shared_baseline_reference_count"], 1)
        self.assertEqual(
            self.report["source_logical_run_count"],
            self.report["inherited_source_logical_run_count"]
            + self.report["independent_control_run_count"],
        )
        self.assertNotEqual(
            self.report["source_logical_run_count"],
            186 + 32 + 18,
        )

    def test_06_independent_control_identity_is_complete(self) -> None:
        expected = [
            "simple_ma",
            "simple_breakout",
            *[f"hash_no_skill_{index:02d}" for index in range(16)],
        ]
        self.assertEqual(
            [run["control_id"] for run in self.controls["control_runs"]],
            expected,
        )
        distribution = self.controls["no_skill_distribution"]
        self.assertEqual(distribution["path_count"], 16)
        self.assertEqual(len(distribution["path_records"]), 16)
        self.assertTrue(distribution["all_paths_retained"])
        self.assertIsNone(distribution["selected_path_id"])
        self.assertEqual(len(self.controls["volatility_matched_projections"]), 6)
        self.assertEqual(len(self.controls["strategy_control_comparisons"]), 6)

    def test_07_all_source_gaps_are_retained(self) -> None:
        report_gaps = set(self.report["gaps"])
        self.assertTrue(set(self.source_report_v7["gaps"]).issubset(report_gaps))
        self.assertTrue(set(self.controls["gaps"]).issubset(report_gaps))
        self.assertIn("NO_SKILL_16_PATH_SYNTHETIC_DISTRIBUTION_ONLY", report_gaps)
        self.assertIn("EQUAL_VOLATILITY_PROJECTION_NOT_EXECUTABLE", report_gaps)
        self.assertIn("FORMAL_FROZEN_BLIND_TEST_GAP", report_gaps)

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v7_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v8(tampered)

    def test_09_resealed_run_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["source_logical_run_count"] = 236
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v8(tampered)

    def test_10_resealed_control_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["benchmark_controls_bundle_sha256"] = "f" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v8(tampered)

    def test_11_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v8(DictAlias(self.report))
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v8(tampered)

    def test_12_renderer_is_non_current_and_neutral(self) -> None:
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v8(
            plan_synthetic_strategy_benchmark_report_v8()
        )
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v8(
            self.report
        )
        for markdown in (plan_markdown, report_markdown):
            self.assertIn("NON-CURRENT RESEARCH-ONLY CANDIDATE", markdown)
            self.assertLess(markdown.index("## SOURCE"), markdown.index("## GAP"))
            self.assertLess(markdown.index("## GAP"), markdown.index("## MATURITY"))
            self.assertLess(
                markdown.index("## MATURITY"), markdown.index("## PERMISSION")
            )
            self.assertIn("Profitability proven: FALSE", markdown)
            self.assertNotIn("Profitability proven: TRUE", markdown)


if __name__ == "__main__":
    unittest.main()
