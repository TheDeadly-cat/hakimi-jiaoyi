from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
    "command_capabilities",
    "command_frozen_benchmark",
    "command_strategy_family_benchmark",
    "command_strategy_research_dossier",
    "command_strategy_robustness_benchmark",
    "command_strategy_statistical_correction_benchmark",
    "command_list_strategies",
    "command_optimize",
    "command_paper",
    "load_stack",
    "main",
)


class CanonicalCliEntrypointV1Tests(unittest.TestCase):
    def test_canonical_cli_owns_logic_and_stable_project_paths(self) -> None:
        self.assertEqual(Path(canonical_cli.__file__).resolve(), CANONICAL_CLI_PATH)
        self.assertNotIn("outputs", CANONICAL_CLI_PATH.relative_to(REPO_ROOT).parts)
        self.assertEqual(canonical_cli.DEFAULT_CONFIG_PATH, PROJECT_ROOT / "config.example.json")
        self.assertEqual(canonical_cli.REPORT_DIR, PROJECT_ROOT / "runtime" / "reports")

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

    def test_module_entrypoint_frozen_benchmark_is_deterministic_and_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "hakimi_research", "frozen-benchmark"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["maturity"], "SYNTHETIC_FIXTURE_ONLY")
            self.assertEqual(payload["quality_status"], "BLOCK")
            self.assertTrue(all(payload["checks"].values()))
            self.assertTrue(all(value is False for value in payload["authority"].values()))
            self.assertTrue(all(value is False for value in payload["claims"].values()))
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_module_entrypoint_strategy_family_benchmark_is_deterministic_and_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-m", "hakimi_research", "strategy-family-benchmark"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["executed_run_count"], 32)
            self.assertEqual(payload["dependency_bound_run_count"], 32)
            self.assertEqual(payload["git_clean_run_count"], 0)
            self.assertEqual(payload["ensemble_status"], "GAP")
            self.assertTrue(all(payload["checks"].values()))
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_module_entrypoint_strategy_robustness_benchmark_is_deterministic_and_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "hakimi_research",
                    "strategy-robustness-benchmark",
                ],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["maturity"], "SYNTHETIC_ROBUSTNESS_ONLY")
            self.assertEqual(payload["source_executed_run_count"], 32)
            self.assertEqual(payload["robustness_executed_run_count"], 147)
            self.assertEqual(payload["total_dependency_bound_run_count"], 179)
            self.assertEqual(payload["git_bound_run_count"], 0)
            self.assertTrue(all(payload["checks"].values()))
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_module_entrypoint_strategy_research_dossier_is_deterministic_and_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "hakimi_research",
                    "strategy-research-dossier",
                ],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertTrue(payload["full_report_alignment_proven"])
            self.assertTrue(
                payload["full_rebuild_required_for_semantic_revalidation"]
            )
            self.assertFalse(payload["runtime_mutations"])
            self.assertTrue(
                all(value is False for value in payload["authority"].values())
            )
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_module_entrypoint_strategy_statistical_correction_benchmark_is_deterministic_and_side_effect_free(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "hakimi_research",
                    "strategy-statistical-correction-benchmark",
                ],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(
                payload["maturity"],
                "SYNTHETIC_STATISTICAL_CORRECTION_ONLY",
            )
            self.assertEqual(payload["total_executed_run_count"], 179)
            self.assertEqual(payload["total_dependency_bound_run_count"], 179)
            self.assertEqual(payload["git_bound_run_count"], 0)
            self.assertEqual(payload["matrix_dependency_bound_run_count"], 18)
            self.assertEqual(payload["deflated_sharpe_diagnostic_count"], 6)
            self.assertEqual(payload["cscv_pbo_observed_evidence_count"], 4)
            self.assertEqual(payload["cscv_pbo_gap_evidence_count"], 2)
            self.assertEqual(payload["tie_bounds_retained_split_count"], 420)
            self.assertTrue(all(payload["checks"].values()))
            self.assertFalse((Path(temp_dir) / "runtime").exists())

    def test_canonical_cli_does_not_inject_legacy_source_root(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        script = (
            "import json,sys;"
            "import hakimi_research.cli;"
            "print(json.dumps([item for item in sys.path if item]))"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-c", script],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved_paths = {Path(item).resolve() for item in json.loads(result.stdout)}
        self.assertNotIn(PROJECT_ROOT.resolve(), resolved_paths)

    def test_root_launcher_invokes_only_canonical_module(self) -> None:
        source = LAUNCHER_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("-m hakimi_research"), 1)
        self.assertNotIn("run_bot.py", source)
        self.assertNotIn("legacyProjectRoot", source)
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
