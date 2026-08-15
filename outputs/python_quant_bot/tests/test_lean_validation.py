from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.validation_receipts import canonical_hash
from run_lean_validation import PROFILES, build_plan, describe_plan, isolated_environment, run


class LeanValidationTests(unittest.TestCase):
    def test_every_profile_is_targeted_and_never_contains_full_discovery(self) -> None:
        for profile in PROFILES:
            with self.subTest(profile=profile):
                plan = build_plan(profile)
                self.assertTrue(plan)
                flattened = " ".join(part for check in plan for part in check.command).lower()
                self.assertNotIn("discover", flattened)
                self.assertNotIn("tests/test_", flattened)
                self.assertFalse(describe_plan(profile)["full_regression_included"])

    def test_core_plan_deduplicates_checks(self) -> None:
        ids = [check.check_id for check in build_plan("core")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("python-safety-contracts", ids)
        self.assertIn("python-market-contracts", ids)
        self.assertIn("python-research-guards", ids)
        self.assertIn("frontend-stock-quote-guard-tests", ids)

    def test_forward_artifact_io_closure_is_in_research_and_critical_syntax(self) -> None:
        plan = {check.check_id: check for check in build_plan("research")}
        research_command = set(plan["python-research-guards"].command)
        syntax_command = set(plan["python-critical-syntax"].command)

        self.assertIn(
            "tests.test_forward_artifact_io.ForwardArtifactIoTests",
            research_command,
        )
        self.assertTrue({
            "exchange_terminal/services/forward_artifact_io.py",
            "exchange_terminal/services/portfolio_forward.py",
            "exchange_terminal/services/portfolio_forward_scheduler.py",
            "exchange_terminal/services/portfolio_shadow.py",
            "exchange_terminal/services/portfolio_active_research_source.py",
            "exchange_terminal/services/portfolio_evidence_archive.py",
            "exchange_terminal/services/portfolio_forward_watchdog.py",
            "run_portfolio_evidence_archive.py",
            "run_portfolio_forward_scheduler.py",
            "run_portfolio_forward_watchdog.py",
            "run_portfolio_shadow_observation.py",
        }.issubset(syntax_command))

    def test_single_look_activation_is_locked_into_research_profile(self) -> None:
        plan = {check.check_id: check for check in build_plan("research")}
        research_command = set(plan["python-research-guards"].command)

        self.assertIn(
            "tests.test_portfolio_forward_single_look.PortfolioForwardSingleLookTests",
            research_command,
        )

    def test_isolated_environment_never_uses_project_runtime_or_local_ai_env(self) -> None:
        runtime = Path("C:/temporary/hakimi-lean-test")
        env = isolated_environment(runtime)

        self.assertEqual(env["HAKIMI_TEST_MODE"], "1")
        self.assertEqual(env["HAKIMI_SKIP_LOCAL_AI_ENV"], "1")
        self.assertEqual(env["HAKIMI_RUNTIME_READ_ONLY"], "1")
        self.assertEqual(Path(env["HAKIMI_RUNTIME_DIR"]), runtime.resolve())
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_isolated_environment_strips_inherited_credentials(self) -> None:
        sentinels = {
            "OKX_SECRET": "must-not-propagate",
            "OKX_API_KEY": "must-not-propagate",
            "OKX_PASSWORD": "must-not-propagate",
            "PYTHONPATH": "must-not-affect-validation",
            "NODE_OPTIONS": "--inspect",
            "HAKIMI_UNSAFE_OVERRIDE": "1",
        }
        with patch.dict(os.environ, sentinels, clear=False):
            env = isolated_environment(Path("C:/temporary/hakimi-lean-credential-test"))

        for key in sentinels:
            self.assertNotIn(key, env)

    def test_frontend_profile_reuses_exact_pass_receipts_without_subprocesses(self) -> None:
        expected_check_count = len(build_plan("frontend"))
        manifest = {
            "manifest_sha256": "a" * 64,
            "manifest_size_bytes": 123,
            "file_count": 4,
            "total_size_bytes": 456,
        }
        toolchain: dict[str, object] = {"node": {"version": "v-test"}}
        toolchain["sha256"] = canonical_hash(toolchain)
        completed = subprocess.CompletedProcess([], 0, stdout="PASS\n", stderr="")
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_lean_validation.build_controlled_input_manifest",
            return_value=manifest,
        ), patch(
            "run_lean_validation.build_toolchain_fingerprint",
            return_value=toolchain,
        ), patch(
            "run_lean_validation.subprocess.run",
            return_value=completed,
        ) as execute:
            cache = Path(directory) / "receipts"
            first = run("frontend", receipt_cache=cache, fresh=True)
            first_calls = execute.call_count
            second = run("frontend", receipt_cache=cache)

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["executed_check_count"], expected_check_count)
        self.assertEqual(first["reused_check_count"], 0)
        self.assertEqual(second["status"], "PASS")
        self.assertEqual(second["executed_check_count"], 0)
        self.assertEqual(second["reused_check_count"], expected_check_count)
        self.assertEqual(execute.call_count, first_calls)
        self.assertTrue(all(row["execution"] == "REUSED" for row in second["results"]))

    def test_dry_run_never_creates_the_receipt_cache(self) -> None:
        manifest = {
            "manifest_sha256": "c" * 64,
            "manifest_size_bytes": 123,
            "file_count": 4,
            "total_size_bytes": 456,
        }
        toolchain: dict[str, object] = {"node": {"version": "v-test"}}
        toolchain["sha256"] = canonical_hash(toolchain)
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_lean_validation.build_controlled_input_manifest",
            return_value=manifest,
        ), patch(
            "run_lean_validation.build_toolchain_fingerprint",
            return_value=toolchain,
        ):
            cache = Path(directory) / "not-created"
            payload = run("frontend", dry_run=True, receipt_cache=cache)
            exists = cache.exists()

        self.assertEqual(payload["status"], "DRY_RUN")
        self.assertFalse(exists)
        self.assertTrue(all(row["execution"] == "WOULD_RUN" for row in payload["results"]))


if __name__ == "__main__":
    unittest.main()
