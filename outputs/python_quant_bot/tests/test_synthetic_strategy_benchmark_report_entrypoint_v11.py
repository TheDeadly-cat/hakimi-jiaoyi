from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v11 import (
    build_synthetic_strategy_benchmark_report_v11,
    plan_synthetic_strategy_benchmark_report_v11,
    render_synthetic_strategy_benchmark_report_markdown_v11,
    render_synthetic_strategy_benchmark_report_plan_markdown_v11,
    verify_synthetic_strategy_benchmark_report_v11,
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


class SyntheticStrategyBenchmarkReportEntrypointV11Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_execution_adversity_v1 import (
            SyntheticStrategyExecutionAdversityV1Tests,
        )

        if not hasattr(SyntheticStrategyExecutionAdversityV1Tests, "bundle"):
            SyntheticStrategyExecutionAdversityV1Tests.setUpClass()
        cls.source = SyntheticStrategyExecutionAdversityV1Tests.source
        cls.adversity = SyntheticStrategyExecutionAdversityV1Tests.bundle
        cls.report = build_synthetic_strategy_benchmark_report_v11(
            cls.source, cls.adversity, execute=True
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v11(cls.report)

    def test_01_plan_accounts_for_222_runs_and_zero_composition(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v11()
        self.assertEqual(plan["source_logical_run_count"], 204)
        self.assertEqual(plan["execution_adversity_additional_run_count"], 18)
        self.assertEqual(plan["total_logical_run_count"], 222)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertEqual(plan["source_module_file_count"], 54)
        self.assertEqual(
            plan["replaced_gap"], "TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY"
        )

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v11(  # type: ignore[arg-type]
                        execute=value
                    )

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v11(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v11(
                self.source, execute=True
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v11(
                adversity_bundle=self.adversity, execute=True
            )

    def test_04_receipt_retains_denied_non_current_state(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 204)
        self.assertEqual(
            self.receipt["execution_adversity_additional_run_count"], 18
        )
        self.assertEqual(self.receipt["total_logical_run_count"], 222)
        self.assertEqual(self.receipt["scenario_count"], 3)
        self.assertEqual(self.receipt["strategy_count"], 6)
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_05_source_and_adversity_bindings_are_exact(self) -> None:
        bindings = self.report["bindings"]
        self.assertEqual(
            bindings["source_report_v10_sha256"], self.source["report_sha256"]
        )
        self.assertEqual(
            bindings["execution_adversity_bundle_sha256"],
            self.adversity["bundle_sha256"],
        )
        self.assertEqual(
            bindings["dependency_lock_sha256"],
            self.source["bindings"]["dependency_lock_sha256"],
        )

    def test_06_execution_gap_is_refined_without_capability_overclaim(self) -> None:
        gaps = set(self.report["gaps"])
        self.assertNotIn("TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY", gaps)
        self.assertIn("SYNTHETIC_EXECUTION_ADVERSITY_ONLY", gaps)
        self.assertIn("PARTIAL_FILL_NOT_MODELLED", gaps)
        self.assertIn("LIQUIDITY_CAPACITY_NOT_MODELLED", gaps)
        self.assertIn("ORDER_REJECTION_NOT_MODELLED", gaps)
        self.assertIn("REAL_DATASET_GAP", gaps)

    def test_07_composition_does_not_duplicate_source_runs(self) -> None:
        self.assertEqual(
            self.report["total_logical_run_count"],
            self.report["source_logical_run_count"]
            + self.report["execution_adversity_additional_run_count"],
        )
        self.assertEqual(self.report["composition_executed_run_count"], 0)
        self.assertEqual(self.report["additional_backtest_run_count"], 0)

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v10_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v11(tampered)

    def test_09_resealed_run_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["total_logical_run_count"] = 240
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v11(tampered)

    def test_10_resealed_adversity_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["execution_adversity_bundle_sha256"] = "f" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v11(tampered)

    def test_11_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v11(DictAlias(self.report))
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v11(tampered)

    def test_12_renderer_is_non_current_and_neutral(self) -> None:
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v11(
            plan_synthetic_strategy_benchmark_report_v11()
        )
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v11(
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
