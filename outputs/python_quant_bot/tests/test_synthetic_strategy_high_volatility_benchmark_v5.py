from __future__ import annotations

from copy import deepcopy
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
    build_synthetic_strategy_benchmark_report_v4,
)
from examples.build_synthetic_strategy_benchmark_report_v5 import (  # noqa: E402
    SyntheticStrategyBenchmarkReportV5Error,
    _canonical_sha256 as canonical_v5_sha256,
    build_synthetic_strategy_benchmark_report_v5,
    plan_synthetic_strategy_benchmark_report_v5,
    render_synthetic_strategy_benchmark_report_markdown_v5,
    verify_synthetic_strategy_benchmark_report_v5,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_cscv_pbo_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_deflated_sharpe_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_high_volatility_validation_v1 import (  # noqa: E402
    SyntheticStrategyHighVolatilityValidationError,
    _canonical_sha256 as canonical_high_volatility_sha256,
    build_synthetic_strategy_high_volatility_validation_v1,
    plan_synthetic_strategy_high_volatility_validation_v1,
    render_synthetic_strategy_high_volatility_validation_markdown_v1,
    verify_synthetic_strategy_high_volatility_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (  # noqa: E402
    build_synthetic_strategy_trial_return_matrix_v1,
)


def _reseal_high_volatility_record(record: dict) -> None:
    payload = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = canonical_high_volatility_sha256(payload)


def _reseal_high_volatility_bundle(bundle: dict) -> None:
    payload = {key: value for key, value in bundle.items() if key != "bundle_sha256"}
    bundle["bundle_sha256"] = canonical_high_volatility_sha256(payload)


def _reseal_v5_report(report: dict) -> None:
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    report["report_sha256"] = canonical_v5_sha256(payload)


class SyntheticStrategyHighVolatilityBenchmarkV5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_report_v3 = build_synthetic_strategy_benchmark_report_v3(
            execute=True
        )
        baseline = cls.source_report_v3["source_report_v2"]["source_report_v1"][
            "baseline_bundle"
        ]
        cls.matrix = build_synthetic_strategy_trial_return_matrix_v1(
            baseline, execute=True
        )
        cls.dsr = build_synthetic_strategy_deflated_sharpe_validation_v1(
            cls.matrix, execute=True
        )
        cls.pbo = build_synthetic_strategy_cscv_pbo_validation_v1(
            cls.matrix, execute=True
        )
        cls.source_report_v4 = build_synthetic_strategy_benchmark_report_v4(
            cls.source_report_v3,
            cls.matrix,
            cls.dsr,
            cls.pbo,
            execute=True,
        )
        cls.high_volatility = build_synthetic_strategy_high_volatility_validation_v1(
            execute=True
        )
        cls.report_v5 = build_synthetic_strategy_benchmark_report_v5(
            cls.source_report_v4,
            cls.high_volatility,
            execute=True,
        )

    def test_01_high_volatility_plan_is_preregistered(self) -> None:
        plan = build_synthetic_strategy_high_volatility_validation_v1(execute=False)
        self.assertEqual(
            plan, plan_synthetic_strategy_high_volatility_validation_v1()
        )
        self.assertEqual(plan["planned_run_count"], 7)
        self.assertEqual(plan["planned_analysis_count"], 6)
        self.assertEqual(plan["expected_target_observation_count_per_strategy"], 189)
        self.assertFalse(plan["selection_policy"]["performance_selection_used"])

    def test_02_high_volatility_execute_flag_requires_exact_bool(self) -> None:
        with self.assertRaisesRegex(
            SyntheticStrategyHighVolatilityValidationError,
            "must be exact bool",
        ):
            build_synthetic_strategy_high_volatility_validation_v1(execute=1)

    def test_03_high_volatility_bundle_covers_all_registered_strategies(self) -> None:
        receipt = verify_synthetic_strategy_high_volatility_validation_v1(
            self.high_volatility
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["executed_run_count"], 7)
        self.assertEqual(receipt["observed_target_slice_count"], 6)
        self.assertEqual(receipt["gap_target_slice_count"], 0)
        self.assertEqual(receipt["permission"], "BLOCK")

    def test_04_each_target_slice_has_189_observations(self) -> None:
        for record in self.high_volatility["strategy_records"]:
            target = record["target_regime_observation"]
            self.assertEqual(target["regime_id"], "HIGH_VOLATILITY")
            self.assertEqual(target["status"], "OBSERVED")
            self.assertEqual(target["observation_count"], 189)

    def test_05_runs_remain_unrankable_and_research_only(self) -> None:
        runs = [self.high_volatility["benchmark_run"]] + [
            record["strategy_run"]
            for record in self.high_volatility["strategy_records"]
        ]
        for run in runs:
            manifest = run["result"]["experiment_manifest"]
            self.assertFalse(manifest["evaluation_protocol_verified"])
            self.assertEqual(manifest["ranking_gate"]["status"], "BLOCK")
            self.assertFalse(manifest["ranking_gate"]["input_allowed"])
            self.assertTrue(manifest["research_only"])
            self.assertFalse(manifest["parameter_selection_allowed"])
            self.assertFalse(manifest["paper_authorized"])
            self.assertFalse(manifest["live_order_allowed"])

    def test_06_resealed_target_projection_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.high_volatility)
        record = tampered["strategy_records"][0]
        record["target_regime_observation"]["observation_count"] = 188
        _reseal_high_volatility_record(record)
        _reseal_high_volatility_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyHighVolatilityValidationError,
            "projection mismatch",
        ):
            verify_synthetic_strategy_high_volatility_validation_v1(tampered)

    def test_07_high_volatility_authority_escalation_fails_closed(self) -> None:
        tampered = deepcopy(self.high_volatility)
        tampered["authority"]["paper_authorized"] = True
        _reseal_high_volatility_bundle(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyHighVolatilityValidationError,
            "gaps or authority drifted",
        ):
            verify_synthetic_strategy_high_volatility_validation_v1(tampered)

    def test_08_v5_plan_accounts_for_186_logical_runs(self) -> None:
        plan = build_synthetic_strategy_benchmark_report_v5(execute=False)
        self.assertEqual(plan, plan_synthetic_strategy_benchmark_report_v5())
        self.assertEqual(plan["inherited_source_logical_run_count"], 179)
        self.assertEqual(plan["high_volatility_source_run_count"], 7)
        self.assertEqual(plan["source_logical_run_count"], 186)
        self.assertEqual(plan["composition_planned_run_count"], 0)

    def test_09_v5_report_is_zero_run_composition(self) -> None:
        receipt = verify_synthetic_strategy_benchmark_report_v5(self.report_v5)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["source_logical_run_count"], 186)
        self.assertEqual(receipt["composition_executed_run_count"], 0)
        self.assertEqual(receipt["observed_high_volatility_slice_count"], 6)
        self.assertEqual(receipt["permission"], "BLOCK")

    def test_10_v5_replaces_only_the_historical_high_volatility_gap(self) -> None:
        self.assertIn(
            "HIGH_VOLATILITY_REGIME_COVERAGE_GAP",
            self.source_report_v4["gaps"],
        )
        self.assertNotIn(
            "HIGH_VOLATILITY_REGIME_COVERAGE_GAP", self.report_v5["gaps"]
        )
        self.assertIn(
            "HIGH_VOLATILITY_SYNTHETIC_SCENARIO_ONLY", self.report_v5["gaps"]
        )
        self.assertIn("PARTIAL_CSCV_RANK_TIE_GAP", self.report_v5["gaps"])

    def test_11_v5_strategy_order_matches_matrix(self) -> None:
        matrix_ids = self.source_report_v4["trial_return_matrix"]["plan"][
            "registered_strategy_ids"
        ]
        high_volatility_ids = self.high_volatility["plan"][
            "registered_strategy_ids"
        ]
        self.assertEqual(matrix_ids, high_volatility_ids)

    def test_12_resealed_v5_binding_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.report_v5)
        tampered["bindings"]["high_volatility_bundle_sha256"] = "0" * 64
        _reseal_v5_report(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV5Error,
            "source bindings mismatch",
        ):
            verify_synthetic_strategy_benchmark_report_v5(tampered)

    def test_13_v5_authority_escalation_fails_closed(self) -> None:
        tampered = deepcopy(self.report_v5)
        tampered["authority"]["live_authorized"] = True
        _reseal_v5_report(tampered)
        with self.assertRaisesRegex(
            SyntheticStrategyBenchmarkReportV5Error,
            "gaps or authority drifted",
        ):
            verify_synthetic_strategy_benchmark_report_v5(tampered)

    def test_14_renderers_are_neutral_and_non_current(self) -> None:
        markdowns = (
            render_synthetic_strategy_high_volatility_validation_markdown_v1(
                self.high_volatility
            ),
            render_synthetic_strategy_benchmark_report_markdown_v5(self.report_v5),
        )
        for markdown in markdowns:
            self.assertIn("| SOURCE | PURE_SYNTHETIC_IN_MEMORY |", markdown)
            self.assertIn("| GAP |", markdown)
            self.assertIn("| MATURITY |", markdown)
            self.assertIn("| PERMISSION | BLOCK |", markdown)
            self.assertIn("Non-current", markdown)
            self.assertNotIn("READY", markdown.upper())
        self.assertIn("synthetic scenario only", markdowns[1])


if __name__ == "__main__":
    unittest.main()
