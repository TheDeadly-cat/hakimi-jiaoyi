from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v9 import (
    build_synthetic_strategy_benchmark_report_v9,
    plan_synthetic_strategy_benchmark_report_v9,
    render_synthetic_strategy_benchmark_report_markdown_v9,
    render_synthetic_strategy_benchmark_report_plan_markdown_v9,
    verify_synthetic_strategy_benchmark_report_v9,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_tie_bounds_v1 import (
    build_synthetic_strategy_cscv_pbo_tie_bounds_v1,
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


def _find_schema(value: object, schema_version: str) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    if type(value) is dict:
        if value.get("schema_version") == schema_version:
            matches.append(value)
        for item in value.values():
            matches.extend(_find_schema(item, schema_version))
    elif type(value) is list:
        for item in value:
            matches.extend(_find_schema(item, schema_version))
    return matches


class SyntheticStrategyBenchmarkReportEntrypointV9Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v8 import (
            SyntheticStrategyBenchmarkReportEntrypointV8Test,
        )

        SyntheticStrategyBenchmarkReportEntrypointV8Test.setUpClass()
        cls.source_report_v8 = (
            SyntheticStrategyBenchmarkReportEntrypointV8Test.report
        )
        matches = _find_schema(
            cls.source_report_v8,
            "synthetic-strategy-cscv-pbo-validation-bundle-v1",
        )
        unique = {item["bundle_sha256"]: item for item in matches}
        if len(unique) != 1:
            raise AssertionError("v8 must embed one unique CSCV v1 bundle")
        cls.source_cscv = next(iter(unique.values()))
        cls.tie_bounds = build_synthetic_strategy_cscv_pbo_tie_bounds_v1(
            cls.source_cscv, execute=True
        )
        cls.report = build_synthetic_strategy_benchmark_report_v9(
            cls.source_report_v8,
            cls.tie_bounds,
            execute=True,
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v9(cls.report)

    def test_01_plan_is_zero_run_gap_replacement_consumer(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v9()
        self.assertEqual(plan["source_logical_run_count"], 204)
        self.assertEqual(plan["tie_bounds_source_reused_run_count"], 147)
        self.assertEqual(plan["planned_tie_bounds_analysis_count"], 6)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertEqual(plan["replaced_gap"], "PARTIAL_CSCV_RANK_TIE_GAP")
        self.assertNotIn("PARTIAL_CSCV_RANK_TIE_GAP", plan["gaps"])
        self.assertFalse(plan["runtime_mutations"])

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v9(  # type: ignore[arg-type]
                        execute=value
                    )

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v9(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v9(
                self.source_report_v8,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v9(
                tie_bounds_bundle=self.tie_bounds,
                execute=True,
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v9(
                self.source_report_v8,
                self.tie_bounds,
                execute=False,
            )

    def test_04_receipt_retains_204_runs_and_denied_authority(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 204)
        self.assertEqual(self.receipt["tie_bounds_source_reused_run_count"], 147)
        self.assertEqual(self.receipt["tie_bounds_executed_analysis_count"], 6)
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)
        self.assertEqual(self.receipt["evidence_state"], "GAP")
        self.assertEqual(self.receipt["status"], "BLOCK")
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_05_shared_cscv_source_is_not_counted_again(self) -> None:
        self.assertEqual(
            self.report["bindings"]["shared_source_cscv_bundle_sha256"],
            self.source_cscv["bundle_sha256"],
        )
        self.assertGreaterEqual(
            self.report["shared_source_cscv_reference_count"], 1
        )
        self.assertEqual(self.report["source_logical_run_count"], 204)
        self.assertNotEqual(self.report["source_logical_run_count"], 204 + 147)

    def test_06_point_partial_and_full_bounds_remain_distinct(self) -> None:
        self.assertEqual(self.report["point_identified_evidence_count"], 4)
        self.assertEqual(self.report["partial_interval_evidence_count"], 1)
        self.assertEqual(self.report["full_unit_interval_evidence_count"], 1)
        records = {
            record["strategy_id"]: record
            for record in self.tie_bounds["strategy_records"]
        }
        grid = records["grid"]["tie_bounds_diagnostic"]
        dual = records["dual_ma"]["tie_bounds_diagnostic"]
        self.assertAlmostEqual(
            float(grid["pbo_nonpositive_logit_lower_bound"]), 48 / 70, places=14
        )
        self.assertEqual(float(grid["pbo_nonpositive_logit_upper_bound"]), 1.0)
        self.assertEqual(float(dual["pbo_nonpositive_logit_lower_bound"]), 0.0)
        self.assertEqual(float(dual["pbo_nonpositive_logit_upper_bound"]), 1.0)

    def test_07_source_gaps_are_retained_with_precise_replacement(self) -> None:
        source_gaps = set(self.source_report_v8["gaps"])
        report_gaps = set(self.report["gaps"])
        self.assertNotIn("PARTIAL_CSCV_RANK_TIE_GAP", report_gaps)
        self.assertTrue(
            (source_gaps - {"PARTIAL_CSCV_RANK_TIE_GAP"}).issubset(report_gaps)
        )
        self.assertIn("PARTIAL_PBO_IDENTIFIED_SET_REMAINS", report_gaps)
        self.assertIn("FULL_UNIT_PBO_IDENTIFIED_SET_REMAINS", report_gaps)
        self.assertIn(
            "TIE_AWARE_PBO_IDENTIFIED_SET_SYNTHETIC_ONLY", report_gaps
        )

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v8_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v9(tampered)

    def test_09_resealed_run_count_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["source_logical_run_count"] = 351
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v9(tampered)

    def test_10_resealed_tie_bundle_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["tie_bounds_bundle_sha256"] = "f" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v9(tampered)

    def test_11_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v9(DictAlias(self.report))
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v9(tampered)

    def test_12_renderer_is_non_current_and_neutral(self) -> None:
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v9(
            plan_synthetic_strategy_benchmark_report_v9()
        )
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v9(
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
