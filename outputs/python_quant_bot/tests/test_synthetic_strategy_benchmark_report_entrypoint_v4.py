from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


PYTHON_QUANT_BOT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PYTHON_QUANT_BOT_ROOT.parents[1]
for import_root in (PYTHON_QUANT_BOT_ROOT, WORKSPACE_ROOT / "src"):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from examples.build_synthetic_strategy_benchmark_report_v3 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v3,
)
from examples.build_synthetic_strategy_benchmark_report_v4 import (  # noqa: E402
    SyntheticStrategyBenchmarkReportV4Error,
    _canonical_sha256,
    build_synthetic_strategy_benchmark_report_v4,
    plan_synthetic_strategy_benchmark_report_v4,
    render_synthetic_strategy_benchmark_report_markdown_v4,
    render_synthetic_strategy_benchmark_report_plan_markdown_v4,
    verify_synthetic_strategy_benchmark_report_v4,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_cscv_pbo_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_deflated_sharpe_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (  # noqa: E402
    build_synthetic_strategy_trial_return_matrix_v1,
)


def _reseal_report(report: dict) -> None:
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    report["report_sha256"] = _canonical_sha256(payload)


class SyntheticStrategyBenchmarkReportEntrypointV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_report_v3 = build_synthetic_strategy_benchmark_report_v3(
            execute=True
        )
        baseline_bundle = cls.source_report_v3["source_report_v2"][
            "source_report_v1"
        ]["baseline_bundle"]
        cls.trial_return_matrix = build_synthetic_strategy_trial_return_matrix_v1(
            baseline_bundle,
            execute=True,
        )
        cls.deflated_sharpe_validation = (
            build_synthetic_strategy_deflated_sharpe_validation_v1(
                cls.trial_return_matrix,
                execute=True,
            )
        )
        cls.cscv_pbo_validation = build_synthetic_strategy_cscv_pbo_validation_v1(
            cls.trial_return_matrix,
            execute=True,
        )
        cls.report = build_synthetic_strategy_benchmark_report_v4(
            cls.source_report_v3,
            cls.trial_return_matrix,
            cls.deflated_sharpe_validation,
            cls.cscv_pbo_validation,
            execute=True,
        )

    def test_01_dry_run_is_zero_backtest_composition_plan(self) -> None:
        plan = build_synthetic_strategy_benchmark_report_v4(execute=False)
        self.assertEqual(plan, plan_synthetic_strategy_benchmark_report_v4())
        self.assertEqual(plan["source_logical_run_count"], 179)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertFalse(plan["runtime_mutations"])

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "execute must be exact bool",
        ):
            build_synthetic_strategy_benchmark_report_v4(execute=1)

    def test_03_execution_requires_all_prebuilt_sources(self) -> None:
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "requires all four exact-dict prebuilt sources",
        ):
            build_synthetic_strategy_benchmark_report_v4(execute=True)

    def test_04_valid_report_has_zero_composition_runs(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_v4(self.report)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["source_logical_run_count"], 179)
        self.assertEqual(receipt["composition_executed_run_count"], 0)
        self.assertEqual(receipt["additional_backtest_run_count"], 0)
        self.assertEqual(receipt["permission"], "BLOCK")

    def test_05_shared_baseline_and_matrix_are_hash_bound(self) -> None:
        baseline_sha256 = self.source_report_v3["source_report_v2"][
            "source_report_v1"
        ]["baseline_bundle"]["bundle_sha256"]
        robustness = self.trial_return_matrix["source_robustness_bundle"]
        matrix_sha256 = self.trial_return_matrix["bundle_sha256"]
        self.assertEqual(baseline_sha256, robustness["source_bundle_sha256"])
        self.assertEqual(
            matrix_sha256,
            self.deflated_sharpe_validation["source_matrix_bundle_sha256"],
        )
        self.assertEqual(
            matrix_sha256,
            self.cscv_pbo_validation["source_matrix_bundle_sha256"],
        )

    def test_06_same_sources_produce_same_report_identity(self) -> None:
        rebuilt = build_synthetic_strategy_benchmark_report_v4(
            self.source_report_v3,
            self.trial_return_matrix,
            self.deflated_sharpe_validation,
            self.cscv_pbo_validation,
            execute=True,
        )
        self.assertEqual(rebuilt["report_sha256"], self.report["report_sha256"])
        self.assertEqual(rebuilt, self.report)

    def test_07_pbo_partial_gap_is_not_promoted(self) -> None:
        self.assertEqual(self.report["observed_cscv_pbo_diagnostic_count"], 4)
        self.assertEqual(self.report["gap_cscv_pbo_diagnostic_count"], 2)
        self.assertIn("PARTIAL_CSCV_RANK_TIE_GAP", self.report["gaps"])
        self.assertEqual(self.report["evidence_state"], "GAP")
        self.assertEqual(self.report["status"], "BLOCK")

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.report)
        tampered["bindings"]["trial_return_matrix_bundle_sha256"] = "0" * 64
        _reseal_report(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "source bindings mismatch",
        ):
            verify_synthetic_strategy_benchmark_report_v4(tampered)

    def test_09_resealed_diagnostic_count_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.report)
        tampered["observed_cscv_pbo_diagnostic_count"] = 5
        _reseal_report(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "observed_cscv_pbo_diagnostic_count mismatch",
        ):
            verify_synthetic_strategy_benchmark_report_v4(tampered)

    def test_10_authority_escalation_fails_closed(self) -> None:
        tampered = deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal_report(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "gaps or authority drifted",
        ):
            verify_synthetic_strategy_benchmark_report_v4(tampered)

    def test_11_native_type_subclasses_fail_closed(self) -> None:
        class StringAlias(str):
            pass

        tampered = deepcopy(self.report)
        tampered["report_id"] = StringAlias(tampered["report_id"])
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV4Error,
            "exact finite JSON-native values",
        ):
            verify_synthetic_strategy_benchmark_report_v4(tampered)

    def test_12_renderer_is_neutral_and_non_current(self) -> None:
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v4(
            self.report
        )
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v4(
            plan_synthetic_strategy_benchmark_report_v4()
        )
        for markdown in (report_markdown, plan_markdown):
            self.assertIn("| SOURCE | PURE_SYNTHETIC_IN_MEMORY |", markdown)
            self.assertIn("| GAP |", markdown)
            self.assertIn("| MATURITY |", markdown)
            self.assertIn("| PERMISSION | BLOCK |", markdown)
            self.assertIn("Non-current candidate", markdown)
            self.assertNotIn("READY", markdown.upper())
        self.assertIn("4/6 observed, 2/6 GAP", report_markdown)
        self.assertNotIn("PROBABILITY_OF_BACKTEST_OVERFITTING_GAP", report_markdown)


if __name__ == "__main__":
    unittest.main()
