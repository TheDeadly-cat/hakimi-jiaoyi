from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_portfolio_runtime_task as runtime_task


class PortfolioRuntimeTaskTests(unittest.TestCase):
    def test_target_allowlist_rejects_paths_and_unlisted_scripts(self) -> None:
        with self.assertRaisesRegex(ValueError, "target_not_allowed"):
            runtime_task.resolve_target("..\\run_internal_portfolio_research.py")
        with self.assertRaisesRegex(ValueError, "target_not_allowed"):
            runtime_task.resolve_target("run_internal_portfolio_research.py")

    def test_task_prefix_contract_rejects_shell_metacharacters(self) -> None:
        self.assertEqual(runtime_task.validate_task_prefix("HakimiTradeV2-G45"), "HakimiTradeV2-G45")
        with self.assertRaisesRegex(ValueError, "task_prefix_invalid"):
            runtime_task.validate_task_prefix("Hakimi;Remove-Item")

    def test_launcher_binds_isolated_runtime_before_target_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_dir = Path(temporary) / "runtime-g45"
            argv = [
                "run_portfolio_runtime_task.py",
                "--runtime-dir",
                str(runtime_dir),
                "--task-prefix",
                "HakimiTradeV2-G45",
                "--target",
                "run_portfolio_forward_scheduler.py",
                "--",
                "--help",
            ]
            captured: dict[str, object] = {}

            def fake_run_path(path: str, *, run_name: str) -> None:
                captured.update({
                    "path": path,
                    "run_name": run_name,
                    "argv": list(os.sys.argv),
                    "runtime": os.environ.get("HAKIMI_RUNTIME_DIR"),
                    "read_only": os.environ.get("HAKIMI_RUNTIME_READ_ONLY"),
                    "live_block": os.environ.get("LIVE_TRADING_HARD_BLOCK"),
                    "task_prefix": os.environ.get("HAKIMI_PORTFOLIO_TASK_PREFIX"),
                })

            with patch.dict(os.environ, {}, clear=False), patch.object(os.sys, "argv", argv), patch.object(
                runtime_task.runpy,
                "run_path",
                fake_run_path,
            ):
                self.assertEqual(runtime_task.main(), 0)

        self.assertEqual(Path(str(captured["runtime"])), runtime_dir.resolve())
        self.assertEqual(captured["read_only"], "1")
        self.assertEqual(captured["live_block"], "true")
        self.assertEqual(captured["task_prefix"], "HakimiTradeV2-G45")
        self.assertEqual(captured["argv"][1:], ["--help"])
        self.assertEqual(captured["run_name"], "__main__")


if __name__ == "__main__":
    unittest.main()
