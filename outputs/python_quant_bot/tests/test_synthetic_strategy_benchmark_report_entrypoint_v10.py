from __future__ import annotations

import copy
import hashlib
import json
import unittest

from examples.build_synthetic_strategy_benchmark_report_v10 import (
    build_synthetic_strategy_benchmark_report_v10,
    plan_synthetic_strategy_benchmark_report_v10,
    render_synthetic_strategy_benchmark_report_markdown_v10,
    render_synthetic_strategy_benchmark_report_plan_markdown_v10,
    verify_synthetic_strategy_benchmark_report_v10,
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


class SyntheticStrategyBenchmarkReportEntrypointV10Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_research_lock_audit_v1 import (
            SyntheticStrategyBenchmarkResearchLockAuditV1Tests,
        )

        if not hasattr(SyntheticStrategyBenchmarkResearchLockAuditV1Tests, "bundle"):
            SyntheticStrategyBenchmarkResearchLockAuditV1Tests.setUpClass()
        cls.source = SyntheticStrategyBenchmarkResearchLockAuditV1Tests.source
        cls.audit = SyntheticStrategyBenchmarkResearchLockAuditV1Tests.bundle
        cls.report = build_synthetic_strategy_benchmark_report_v10(
            cls.source, cls.audit, execute=True
        )
        cls.receipt = verify_synthetic_strategy_benchmark_report_v10(cls.report)

    def test_01_plan_binds_lock_source_and_zero_run_composition(self) -> None:
        plan = plan_synthetic_strategy_benchmark_report_v10()
        self.assertEqual(plan["source_logical_run_count"], 204)
        self.assertEqual(plan["research_lock_source_reused_run_count"], 204)
        self.assertEqual(plan["planned_research_lock_analysis_count"], 1)
        self.assertEqual(plan["composition_planned_run_count"], 0)
        self.assertEqual(plan["composition_executed_run_count"], 0)
        self.assertEqual(plan["additional_backtest_run_count"], 0)
        self.assertRegex(plan["dependency_lock_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(plan["source_manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_02_execute_flag_requires_exact_bool(self) -> None:
        for value in (0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    build_synthetic_strategy_benchmark_report_v10(  # type: ignore[arg-type]
                        execute=value
                    )

    def test_03_execute_requires_both_prebuilt_sources(self) -> None:
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v10(execute=True)
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v10(
                self.source, execute=True
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v10(
                research_lock_audit=self.audit, execute=True
            )
        with self.assertRaises(ValueError):
            build_synthetic_strategy_benchmark_report_v10(
                self.source, self.audit, execute=False
            )

    def test_04_receipt_exposes_narrow_reproducibility_identity(self) -> None:
        self.assertEqual(self.receipt["source_logical_run_count"], 204)
        self.assertEqual(self.receipt["source_module_file_count"], 52)
        self.assertEqual(self.receipt["exact_dependency_pin_count"], 7)
        self.assertEqual(self.receipt["installed_exact_match_count"], 7)
        self.assertTrue(self.receipt["benchmark_lock_fully_version_pinned"])
        self.assertFalse(self.receipt["dependency_artifact_hashes_present"])
        self.assertFalse(self.receipt["full_application_lock_covered"])
        self.assertEqual(self.receipt["composition_executed_run_count"], 0)
        self.assertFalse(any(self.receipt["authority"].values()))

    def test_05_report_bindings_match_audit_exactly(self) -> None:
        bindings = self.report["bindings"]
        self.assertEqual(bindings["source_report_v9_sha256"], self.source["report_sha256"])
        self.assertEqual(
            bindings["research_lock_audit_bundle_sha256"],
            self.audit["bundle_sha256"],
        )
        self.assertEqual(
            bindings["dependency_lock_sha256"], self.audit["dependency_lock_sha256"]
        )
        self.assertEqual(
            bindings["source_manifest_sha256"],
            self.audit["source_manifest"]["source_manifest_sha256"],
        )

    def test_06_lock_gaps_are_replaced_without_overclaim(self) -> None:
        gaps = set(self.report["gaps"])
        self.assertNotIn("DEPENDENCY_LOCK_HASH_GAP", gaps)
        self.assertNotIn("DEPENDENCY_LOCK_NOT_FULLY_PINNED", gaps)
        self.assertIn("DEPENDENCY_ARTIFACT_HASH_GAP", gaps)
        self.assertIn("FULL_APPLICATION_DEPENDENCY_LOCK_GAP", gaps)
        self.assertIn("INSTALLED_ENVIRONMENT_MATCH_NOT_FRESH_INSTALL_PROOF", gaps)
        self.assertIn("SOURCE_COMMIT_SHA_GAP", gaps)

    def test_07_source_logical_runs_are_not_duplicated(self) -> None:
        self.assertEqual(self.report["source_logical_run_count"], 204)
        self.assertEqual(self.report["research_lock_source_reused_run_count"], 204)
        self.assertEqual(self.report["research_lock_executed_analysis_count"], 1)
        self.assertEqual(self.report["composition_executed_run_count"], 0)
        self.assertEqual(self.report["additional_backtest_run_count"], 0)

    def test_08_resealed_source_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["source_report_v9_sha256"] = "0" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v10(tampered)

    def test_09_resealed_lock_binding_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["bindings"]["dependency_lock_sha256"] = "f" * 64
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v10(tampered)

    def test_10_resealed_scope_escalation_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.report)
        tampered["full_application_lock_covered"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v10(tampered)

    def test_11_exact_native_types_and_authority_fail_closed(self) -> None:
        class DictAlias(dict):
            pass

        with self.assertRaises(TypeError):
            verify_synthetic_strategy_benchmark_report_v10(DictAlias(self.report))
        tampered = copy.deepcopy(self.report)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "report_sha256")
        with self.assertRaises(ValueError):
            verify_synthetic_strategy_benchmark_report_v10(tampered)

    def test_12_renderer_is_non_current_and_neutral(self) -> None:
        plan_markdown = render_synthetic_strategy_benchmark_report_plan_markdown_v10(
            plan_synthetic_strategy_benchmark_report_v10()
        )
        report_markdown = render_synthetic_strategy_benchmark_report_markdown_v10(
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
