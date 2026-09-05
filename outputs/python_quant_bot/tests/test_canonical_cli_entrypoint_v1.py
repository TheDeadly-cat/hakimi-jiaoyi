from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_CLI_PATH = REPO_ROOT / "src" / "hakimi_research" / "cli.py"
LEGACY_CLI_PATH = PROJECT_ROOT / "run_bot.py"
LAUNCHER_PATH = REPO_ROOT / "hakimi-research.ps1"

activate_canonical_source()

import run_bot  # noqa: E402
from hakimi_research import cli as canonical_cli  # noqa: E402


CLI_SYMBOLS = (
    "command_backtest",
    "command_optimize",
    "command_paper",
    "main",
)


class CanonicalCliEntrypointV1Tests(unittest.TestCase):
    def test_canonical_cli_owns_logic_and_packaged_resources(self) -> None:
        self.assertEqual(Path(canonical_cli.__file__).resolve(), CANONICAL_CLI_PATH)
        self.assertNotIn("outputs", CANONICAL_CLI_PATH.relative_to(REPO_ROOT).parts)
        self.assertEqual(
            canonical_cli.DEFAULT_CONFIG_PATH,
            REPO_ROOT / "src" / "hakimi_research" / "resources" / "config.example.json",
        )
        with tempfile.TemporaryDirectory() as temporary:
            desired = Path(temporary) / "independent-artifacts"
            with patch.dict(os.environ, {"HAKIMI_RESEARCH_HOME": str(desired)}):
                self.assertEqual(canonical_cli.default_artifact_root(), desired)
                self.assertFalse(desired.exists())

    def test_canonical_cli_has_no_legacy_runtime_import_or_path_activation(self) -> None:
        source = CANONICAL_CLI_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from quant_bot", source)
        self.assertNotIn("import quant_bot", source)
        self.assertNotIn("activate_legacy_project_root", source)
        self.assertNotIn("LEGACY_PROJECT_ROOT", source)
        self.assertNotIn("outputs/python_quant_bot", source)
        self.assertNotIn("build_data_provider", source)
        self.assertNotIn("load_stack", source)
        self.assertIn("ExperimentRunner().run", source)

    def test_legacy_cli_reexports_identical_canonical_objects(self) -> None:
        for symbol in CLI_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(run_bot, symbol), getattr(canonical_cli, symbol))

    def test_legacy_cli_contains_no_command_definitions(self) -> None:
        tree = ast.parse(LEGACY_CLI_PATH.read_text(encoding="utf-8"))
        definitions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(definitions)
        canonical_tree = ast.parse(CANONICAL_CLI_PATH.read_text(encoding="utf-8"))
        canonical_definitions = {
            node.name
            for node in canonical_tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue(set(CLI_SYMBOLS).issubset(canonical_definitions))

    def test_module_entrypoint_capabilities_is_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "hakimi_research", "capabilities"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_version"], "product-capability-catalog-v2")
            self.assertFalse(payload["authority"]["paper_allowed"])
            self.assertFalse(payload["authority"]["live_allowed"])
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_module_entrypoint_strategy_catalog_is_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "hakimi_research", "list-strategies"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("dual_ma", result.stdout)
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_root_launcher_invokes_only_canonical_module(self) -> None:
        source = LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("-m hakimi_research"), 1)
        self.assertNotIn("run_bot.py", source)
        self.assertNotIn("PYTHONPATH", source)
        self.assertNotIn("outputs\\python_quant_bot", source)
        for forbidden in (
            "Start-Process",
            "Invoke-WebRequest",
            "curl ",
            "paper",
            "live",
            "server.py",
            "dashboard_app.py",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
