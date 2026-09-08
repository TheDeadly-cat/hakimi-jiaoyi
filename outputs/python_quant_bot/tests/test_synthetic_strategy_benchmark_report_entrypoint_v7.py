from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v7 import (
    build_synthetic_strategy_benchmark_report_v7,
    plan_synthetic_strategy_benchmark_report_v7,
    render_synthetic_strategy_benchmark_report_markdown_v7,
    render_synthetic_strategy_benchmark_report_plan_markdown_v7,
    verify_synthetic_strategy_benchmark_report_v7,
)
from exchange_terminal.application.synthetic_strategy_return_contribution_concentration_v1 import (
    build_synthetic_strategy_return_contribution_concentration_v1,
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


class SyntheticStrategyBenchmarkReportEntrypointV7Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v6 import (
            SyntheticStrategyBenchmarkReportEntrypointV6Test,
        )

        SyntheticStrategyBenchmarkReportEntrypointV6Test.setUpClass()
        cls.source_report_v6 = (
            SyntheticStrategyBenchmarkReportEntrypointV6Test.report
        )
        cls.shared_matrix = cls.source_report_v6["source_report_v5"][
            "source_report_v4"
        ]["trial_return_matrix"]
        cls.return_contribution_bundle = (
            build_synthetic_strategy_return_contribution_concentration_v1(
                cls.shared_matrix,
                execute=True,
            )
        )
        cls.report = build_synthetic_strategy_benchmark_report_v7(
            cls.source_report_v6,
            cls.return_contribution_bundle,
            execute=True,
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v7(cls.report)

    def test_01_plan_is_zero_run_shared_source_consumer(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v7()
        self.assertEqual(plan["source_logical_run_count"], 186)
        self.assertEqual(plan["concentration_source_reused_run_count"], 147)
        self.assertEqual(plan["planned_concentration_analysis_count"], 6)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertTrue(plan["requires_shared_trial_return_matrix_identity"])
        self.assertFalse(plan["runtime_mutations"])

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v7(execute=value)  # type: ignore[arg-type]

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v7(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v7(
                self.source_report_v6,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v7(
                return_contribution_bundle=self.return_contribution_bundle,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v7(
                self.source_report_v6,
                self.return_contribution_bundle,
                execute=False,
            )

    def test_04_valid_receipt_retains_zero_run_counts(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 186)
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertEqual(
            self.receipt["concentration_executed_analysis_count"], 6
        )
        self.assertEqual(self.receipt["evidence_state"], "GAP")
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(self.receipt["runtime_mutations"])

    def test_05_sources_share_one_exact_matrix_identity(self) -> None:
        concentration_matrix = self.return_contribution_bundle[
            "source_matrix_bundle"
        ]
        self.assertEqual(concentration_matrix, self.shared_matrix)
        self.assertEqual(
            self.report["bindings"][
                "shared_trial_return_matrix_bundle_sha256"
            ],
            self.shared_matrix["bundle_sha256"],
        )
        self.assertEqual(
            self.report["bindings"][
                "return_contribution_bundle_sha256"
            ],
            self.return_contribution_bundle["bundle_sha256"],
        )

    def test_06_partial_concentration_counts_remain_explicit(self) -> None:
        self.assertEqual(self.report["observed_period_concentration_count"], 5)
        self.assertEqual(self.report["gap_period_concentration_count"], 1)
        self.assertEqual(
            self.report["observed_calendar_month_sensitivity_count"], 6
        )
        self.assertEqual(
            self.report["observed_fixed_window_sensitivity_count"], 6
        )
        self.assertEqual(
            self.report["observed_closed_trade_sensitivity_count"], 6
        )
        self.assertEqual(self.report["gap_closed_trade_sensitivity_count"], 0)
        self.assertEqual(
            self.report[
                "observed_positive_closed_trade_concentration_count"
            ],
            4,
        )
        self.assertEqual(
            self.report["gap_positive_closed_trade_concentration_count"], 2
        )

    def test_07_all_source_gaps_are_retained(self) -> None:
        report_gaps = set(self.report["gaps"])
        self.assertTrue(
            set(self.source_report_v6["gaps"]).issubset(report_gaps)
        )
        self.assertTrue(
            set(self.return_contribution_bundle["gaps"]).issubset(report_gaps)
        )
        self.assertIn(
            "PARTIAL_POSITIVE_PERIOD_RETURN_CONCENTRATION_GAP", report_gaps
        )
        self.assertIn(
            "PARTIAL_POSITIVE_CLOSED_TRADE_CONCENTRATION_GAP", report_gaps
        )
        self.assertIn("CALENDAR_MONTH_SYNTHETIC_ONLY", report_gaps)
        self.assertIn("TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY", report_gaps)

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v6_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v7(tampered)

    def test_09_resealed_projection_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["gap_period_concentration_count"] = 0
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v7(tampered)

    def test_10_authority_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v7(tampered)

    def test_11_exact_native_types_are_required(self) -> None:
        class StringAlias(str):
            pass

        class DictAlias(dict):
            pass

        tampered = copy.deepcopy(self.report)
        tampered["report_id"] = StringAlias(tampered["report_id"])
        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v7(tampered)
        with self.assertRaises(TypeError):
            build_synthetic_strategy_benchmark_report_v7(
                DictAlias(self.source_report_v6),
                self.return_contribution_bundle,
                execute=True,
            )

    def test_12_renderers_are_neutral_and_non_current(self) -> None:
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v7(
            self.report
        )
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v7(
            self.report["plan"]
        )
        rendered = report_markdown + plan_markdown
        self.assertIn("SOURCE", rendered)
        self.assertIn("GAP", rendered)
        self.assertIn("MATURITY", rendered)
        self.assertIn("PERMISSION", rendered)
        self.assertIn("NON-CURRENT", rendered)
        self.assertIn("No decision threshold", rendered)
        self.assertIn("simplified execution model", rendered)
        self.assertNotIn("READY", rendered.upper())
        self.assertNotIn("SIGNIFICANT", rendered.upper())
        self.assertNotIn("ACCEPT STRATEGY", rendered.upper())


if __name__ == "__main__":
    unittest.main()
