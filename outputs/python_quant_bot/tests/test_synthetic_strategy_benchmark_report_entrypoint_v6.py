from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v6 import (
    build_synthetic_strategy_benchmark_report_v6,
    plan_synthetic_strategy_benchmark_report_v6,
    render_synthetic_strategy_benchmark_report_markdown_v6,
    render_synthetic_strategy_benchmark_report_plan_markdown_v6,
    verify_synthetic_strategy_benchmark_report_v6,
)
from exchange_terminal.application.synthetic_strategy_reproducibility_provenance_gap_audit_v1 import (
    build_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
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


class SyntheticStrategyBenchmarkReportEntrypointV6Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_high_volatility_benchmark_v5 import (
            SyntheticStrategyHighVolatilityBenchmarkV5Test,
        )

        SyntheticStrategyHighVolatilityBenchmarkV5Test.setUpClass()
        cls.source_report_v5 = (
            SyntheticStrategyHighVolatilityBenchmarkV5Test.report_v5
        )
        cls.provenance_audit = (
            build_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
                cls.source_report_v5,
                execute=True,
            )
        )
        cls.report = build_synthetic_strategy_benchmark_report_v6(
            cls.source_report_v5,
            cls.provenance_audit,
            execute=True,
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v6(cls.report)

    def test_01_plan_is_zero_run_consumer(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v6()
        self.assertEqual(plan["source_logical_run_count"], 186)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertTrue(plan["requires_prebuilt_sources"])
        self.assertFalse(plan["runtime_mutations"])

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v6(execute=value)  # type: ignore[arg-type]

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v6(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v6(
                self.source_report_v5,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v6(
                provenance_audit=self.provenance_audit,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v6(
                self.source_report_v5,
                self.provenance_audit,
                execute=False,
            )

    def test_04_valid_receipt_retains_zero_run_counts(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 186)
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertFalse(self.receipt["runtime_mutations"])
        self.assertEqual(self.receipt["evidence_state"], "GAP")
        self.assertEqual(self.receipt["status"], "BLOCK")

    def test_05_report_binds_v5_without_recounting_runs(self) -> None:
        self.assertEqual(self.report["source_logical_run_count"], 186)
        self.assertEqual(self.report["composition_executed_run_count"], 0)
        self.assertEqual(self.report["additional_backtest_run_count"], 0)
        self.assertEqual(
            self.report["bindings"]["source_report_v5_sha256"],
            self.source_report_v5["report_sha256"],
        )
        self.assertEqual(
            self.report["bindings"]["source_report_v5_plan_sha256"],
            self.source_report_v5["plan"]["plan_sha256"],
        )

    def test_06_provenance_counts_remain_explicit_gaps(self) -> None:
        self.assertEqual(self.report["critical_source_module_count"], 18)
        self.assertEqual(self.report["requirement_count"], 14)
        self.assertEqual(self.report["exact_pin_count"], 1)
        self.assertEqual(self.report["unpinned_requirement_count"], 13)
        self.assertEqual(self.report["valid_git_commit_identity_count"], 0)
        self.assertEqual(self.report["clean_worktree_identity_count"], 0)
        self.assertEqual(self.report["fully_pinned_dependency_identity_count"], 0)

    def test_07_all_source_gaps_are_retained(self) -> None:
        report_gaps = set(self.report["gaps"])
        self.assertTrue(set(self.source_report_v5["gaps"]).issubset(report_gaps))
        self.assertTrue(set(self.provenance_audit["gaps"]).issubset(report_gaps))
        self.assertIn("DEPENDENCY_LOCK_NOT_FULLY_PINNED", report_gaps)
        self.assertIn("PROVENANCE_AUDIT_NOT_REPRODUCIBILITY_COMPLETION", report_gaps)
        self.assertIn(
            "SOURCE_WORKTREE_IDENTITY_REQUIRES_AUTHORIZED_SNAPSHOT",
            report_gaps,
        )

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v5_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v6(tampered)

    def test_09_resealed_dependency_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        audit = tampered["provenance_audit"]
        audit["dependency_audit"]["unpinned_count"] = 12
        _reseal(audit, "bundle_sha256")
        tampered["bindings"]["provenance_audit_bundle_sha256"] = audit[
            "bundle_sha256"
        ]
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v6(tampered)

    def test_10_authority_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v6(tampered)

    def test_11_exact_native_types_are_required(self) -> None:
        class StringAlias(str):
            pass

        class DictAlias(dict):
            pass

        tampered = copy.deepcopy(self.report)
        tampered["report_id"] = StringAlias(tampered["report_id"])
        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v6(tampered)
        with self.assertRaises(TypeError):
            build_synthetic_strategy_benchmark_report_v6(
                DictAlias(self.source_report_v5),
                self.provenance_audit,
                execute=True,
            )

    def test_12_renderers_are_neutral_and_non_current(self) -> None:
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v6(
            self.report
        )
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v6(
            self.report["plan"]
        )
        rendered = report_markdown + plan_markdown
        self.assertIn("SOURCE", rendered)
        self.assertIn("GAP", rendered)
        self.assertIn("MATURITY", rendered)
        self.assertIn("PERMISSION", rendered)
        self.assertIn("NON-CURRENT", rendered)
        self.assertIn("Formal reproducibility is not established.", rendered)
        self.assertNotIn("READY", rendered.upper())
        self.assertNotIn("profit", rendered.lower().replace("profitability proven", ""))


if __name__ == "__main__":
    unittest.main()
