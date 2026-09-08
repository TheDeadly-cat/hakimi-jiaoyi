from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from exchange_terminal.application.synthetic_strategy_benchmark_research_lock_audit_v1 import (
    SyntheticStrategyBenchmarkResearchLockAuditError,
    build_synthetic_strategy_benchmark_research_lock_audit_v1,
    plan_synthetic_strategy_benchmark_research_lock_audit_v1,
    render_synthetic_strategy_benchmark_research_lock_audit_markdown_v1,
    replay_synthetic_strategy_benchmark_research_lock_audit_v1,
    verify_synthetic_strategy_benchmark_research_lock_audit_v1,
)
from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


def _reseal(payload: dict[str, object], field: str) -> None:
    unsigned = {key: value for key, value in payload.items() if key != field}
    payload[field] = canonical_trial_return_matrix_sha256(unsigned)


class SyntheticStrategyBenchmarkResearchLockAuditV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from tests.test_synthetic_strategy_benchmark_report_entrypoint_v9 import (
            SyntheticStrategyBenchmarkReportEntrypointV9Test,
        )

        if not hasattr(SyntheticStrategyBenchmarkReportEntrypointV9Test, "report"):
            SyntheticStrategyBenchmarkReportEntrypointV9Test.setUpClass()
        cls.source = SyntheticStrategyBenchmarkReportEntrypointV9Test.report
        cls.plan = plan_synthetic_strategy_benchmark_research_lock_audit_v1()
        cls.bundle = build_synthetic_strategy_benchmark_research_lock_audit_v1(
            cls.source, execute=True
        )
        cls.receipt = verify_synthetic_strategy_benchmark_research_lock_audit_v1(
            cls.bundle, cls.source
        )
        cls.markdown = render_synthetic_strategy_benchmark_research_lock_audit_markdown_v1(
            cls.bundle, cls.source
        )

    def test_01_plan_binds_source_lock_platform_and_zero_runs(self) -> None:
        self.assertEqual(self.plan["source_logical_run_count"], 204)
        self.assertEqual(self.plan["planned_run_count"], 0)
        self.assertEqual(self.plan["additional_backtest_run_count"], 0)
        self.assertEqual(self.plan["planned_analysis_count"], 1)
        self.assertEqual(self.plan["source_manifest"]["module_file_count"], 53)
        self.assertEqual(self.plan["lock_manifest"]["exact_pin_count"], 7)
        self.assertTrue(self.plan["benchmark_lock_scope_complete"])
        self.assertFalse(self.plan["full_application_lock_scope_complete"])
        self.assertFalse(self.plan["dependency_artifact_hashes_present"])

    def test_02_audit_requires_exact_true(self) -> None:
        for value in (False, 0, 1, "true", None):
            with self.subTest(value=value):
                with self.assertRaises(SyntheticStrategyBenchmarkResearchLockAuditError):
                    build_synthetic_strategy_benchmark_research_lock_audit_v1(
                        self.source, execute=value  # type: ignore[arg-type]
                    )

    def test_03_receipt_has_exact_lock_and_environment_counts(self) -> None:
        self.assertEqual(self.receipt["source_module_file_count"], 53)
        self.assertEqual(self.receipt["exact_pin_count"], 7)
        self.assertEqual(self.receipt["installed_exact_match_count"], 7)
        self.assertTrue(self.receipt["benchmark_lock_fully_version_pinned"])
        self.assertFalse(self.receipt["dependency_artifact_hashes_present"])
        self.assertFalse(self.receipt["full_application_lock_covered"])
        self.assertEqual(self.receipt["executed_run_count"], 0)
        self.assertEqual(self.receipt["additional_backtest_run_count"], 0)

    def test_04_all_source_file_hashes_match_independent_bytes(self) -> None:
        root = Path(__file__).resolve().parents[3]
        files = self.bundle["source_manifest"]["files"]
        self.assertEqual(len(files), 53)
        for record in files:
            payload = (root / record["path"]).read_bytes()
            self.assertEqual(record["byte_count"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())

    def test_05_lock_is_exactly_pinned_and_byte_bound(self) -> None:
        root = Path(__file__).resolve().parents[3]
        manifest = self.bundle["dependency_lock_manifest"]
        payload = (root / manifest["path"]).read_bytes()
        self.assertEqual(
            manifest["dependency_lock_sha256"], hashlib.sha256(payload).hexdigest()
        )
        self.assertEqual(len(manifest["pins"]), 7)
        self.assertTrue(manifest["all_requirements_exactly_version_pinned"])
        self.assertTrue(
            all(pin["name"] and pin["version"] for pin in manifest["pins"])
        )

    def test_06_installed_resolution_matches_every_pin_exactly(self) -> None:
        resolution = self.bundle["installed_resolution"]
        self.assertTrue(resolution["all_locked_versions_installed_exactly"])
        self.assertEqual(resolution["record_count"], 7)
        self.assertEqual(resolution["exact_match_count"], 7)
        self.assertEqual(resolution["missing_distribution_count"], 0)
        self.assertEqual(resolution["mismatch_count"], 0)
        for record in resolution["records"]:
            self.assertEqual(record["locked_version"], record["installed_version"])

    def test_07_old_lock_gaps_are_precisely_replaced(self) -> None:
        gaps = set(self.bundle["gaps"])
        self.assertNotIn("DEPENDENCY_LOCK_HASH_GAP", gaps)
        self.assertNotIn("DEPENDENCY_LOCK_NOT_FULLY_PINNED", gaps)
        self.assertIn("BENCHMARK_LOCK_PLATFORM_SPECIFIC", gaps)
        self.assertIn("DEPENDENCY_ARTIFACT_HASH_GAP", gaps)
        self.assertIn("FULL_APPLICATION_DEPENDENCY_LOCK_GAP", gaps)
        self.assertIn("INSTALLED_ENVIRONMENT_MATCH_NOT_FRESH_INSTALL_PROOF", gaps)

    def test_08_v9_source_identity_is_exactly_bound(self) -> None:
        self.assertEqual(
            self.bundle["source_report_v9_sha256"], self.source["report_sha256"]
        )
        self.assertEqual(
            self.bundle["source_report_v9_plan_sha256"],
            self.source["plan"]["plan_sha256"],
        )
        self.assertEqual(self.bundle["source_logical_run_count"], 204)

    def test_09_resealed_lock_identity_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["dependency_lock_sha256"] = "0" * 64
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyBenchmarkResearchLockAuditError):
            verify_synthetic_strategy_benchmark_research_lock_audit_v1(
                tampered, self.source
            )

    def test_10_audit_does_not_call_subprocess_or_git(self) -> None:
        with patch.object(
            subprocess,
            "run",
            side_effect=AssertionError("subprocess forbidden"),
        ):
            replayed = build_synthetic_strategy_benchmark_research_lock_audit_v1(
                self.source, execute=True
            )
        self.assertEqual(replayed, self.bundle)

    def test_11_authority_escalation_fails_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["authority"]["paper_authorized"] = True
        _reseal(tampered, "bundle_sha256")
        with self.assertRaises(SyntheticStrategyBenchmarkResearchLockAuditError):
            verify_synthetic_strategy_benchmark_research_lock_audit_v1(
                tampered, self.source
            )

    def test_12_replay_and_renderer_remain_neutral(self) -> None:
        receipt = replay_synthetic_strategy_benchmark_research_lock_audit_v1(
            self.bundle, self.source
        )
        self.assertEqual(receipt["replay_status"], "EXACT_MATCH")
        self.assertEqual(receipt["executed_run_count"], 0)
        self.assertIn("## SOURCE", self.markdown)
        self.assertIn("## GAP", self.markdown)
        self.assertIn("## MATURITY", self.markdown)
        self.assertIn("## PERMISSION", self.markdown)
        self.assertIn("not a fresh-install reproduction proof", self.markdown)
        self.assertNotIn("READY", self.markdown)
        self.assertNotIn("SIGNIFICANT", self.markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
