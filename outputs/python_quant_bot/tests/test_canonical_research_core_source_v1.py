from __future__ import annotations

import ast
import hashlib
import importlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _canonical_source import activate_canonical_source


REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
CANONICAL_ROOT = REPO_ROOT / "src" / "hakimi_research"

activate_canonical_source()


BASELINE_LOGICAL_HASHES = {
    "experiment_manifest.py": "9b77e81fd18659a8e39ced8978f5c24c358c85b9c7f1b1e7b49da2e204a60b53",
    "indicators.py": "e9ce117348204d297a2a8151c74105b3eb465ac003a0b1aa2464d0aad5a0e413",
    "logging_setup.py": "771a29df4ffc630445ec32edb4062eeaaf32797df9db65ffeb20d374952e8fc7",
    "reporting.py": "a0f7885f3e2cb56cf30e9a7213a7ec011a74e3826b8cd31d01a4bed2b8e08f42",
    "strategies/__init__.py": "cc2a5f5e4aa38e342472f72b02e6700e256ffbde72065c78128d5bbf806ff5aa",
    "strategies/templates.py": "148a2dce4fe1dce163e01ec3a3d1d174a23e0689e402b7d47ff18818dbb5bc30",
}
# Historical identities remain recorded. Runtime evidence and atomic persistence
# evolved after the import-only migration. Strategy registration now includes
# explicit cash/buy-and-hold baselines and lazy exports that avoid import cycles;
# current behavior is covered below and by the accounting benchmark tests.
EVOLVED_MODULES = {
    "experiment_manifest.py", "reporting.py",
    "strategies/__init__.py", "strategies/templates.py",
}

PUBLIC_SYMBOLS = {
    "models": (
        "DOMAIN_MODEL_SCHEMA_VERSION",
        "Action",
        "Signal",
        "Portfolio",
        "Order",
        "Fill",
    ),
    "config": (
        "CONFIG_SCHEMA_VERSION",
        "DataConfig",
        "StrategyConfig",
        "RiskConfig",
        "ExecutionConfig",
        "LoggingConfig",
        "BotConfig",
        "validate_research_config",
    ),
    "indicators": ("sma", "ema", "bollinger", "macd", "rsi", "momentum"),
    "execution": (
        "EXECUTION_SIMULATOR_SCHEMA_VERSION",
        "ResearchExecutionSimulator",
    ),
    "risk": ("RISK_ENGINE_SCHEMA_VERSION", "RiskManager"),
    "backtest": (
        "BACKTEST_SCHEMA_VERSION",
        "BacktestEngine",
        "BacktestReport",
    ),
    "data": (
        "MARKET_DATA_SCHEMA_VERSION",
        "OKX_COMPLETED_CANDLE_SCHEMA_VERSION",
        "OKX_SPOT_VOLUME_UNIT",
        "MarketDataProvider",
        "SyntheticDataProvider",
        "CsvDataProvider",
        "OkxPublicDataProvider",
        "build_data_provider",
        "okx_bar",
        "validate_market_data_frame",
        "market_data_fingerprint",
        "parse_okx_completed_candle_rows",
    ),
    "logging_setup": ("setup_logging",),
    "reporting": ("save_json_report",),
    "experiment_manifest": (
        "SCHEMA_VERSION",
        "canonical_payload_hash",
        "build_local_experiment_context",
        "build_reproducible_experiment_manifest",
        "verify_reproducible_experiment_manifest",
    ),
}


def _logical_hash(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class CanonicalResearchCoreSourceV1Tests(unittest.TestCase):
    def test_migration_is_exact_except_for_canonical_import_paths(self) -> None:
        for relative, expected_hash in BASELINE_LOGICAL_HASHES.items():
            if relative in EVOLVED_MODULES:
                continue
            with self.subTest(relative=relative):
                source = (CANONICAL_ROOT / relative).read_text(encoding="utf-8")
                restored = source.replace(
                    "from hakimi_research.",
                    "from quant_bot.",
                )
                self.assertEqual(_logical_hash(restored), expected_hash)

    def test_evolved_legacy_aliases_fail_closed_and_preserve_reports(self) -> None:
        from quant_bot.experiment_manifest import build_local_experiment_context
        from quant_bot.reporting import save_json_report
        def git_failure(arguments, **kwargs):
            if "rev-parse" in arguments:
                return subprocess.CompletedProcess(arguments, 0, "a" * 40, "")
            return subprocess.CompletedProcess(arguments, 1, "", "failed")
        with patch("hakimi_research.environment.subprocess.run", side_effect=git_failure):
            context = build_local_experiment_context(REPO_ROOT)
        self.assertIsNone(context["git_worktree_clean"])
        self.assertEqual(context["provenance"]["source_identity"]["git"]["status"], "UNKNOWN")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(save_json_report({"value": 1}, directory, "legacy", artifact_id="fixed"))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                save_json_report({"value": 2}, directory, "legacy", artifact_id="fixed")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(Path(save_json_report({"value": 1}, directory, "legacy", artifact_id="fixed")), path)

    def test_evolved_strategy_exports_preserve_rules_and_require_explicit_benchmark_target(self) -> None:
        from hakimi_research import strategies
        from hakimi_research.benchmarks import CashBenchmarkStrategy, BuyAndHoldBenchmarkStrategy
        from hakimi_research.strategies.templates import STRATEGY_REGISTRY, build_strategy
        from quant_bot.strategies import build_strategy as legacy_builder

        self.assertIs(strategies.build_strategy, build_strategy)
        self.assertIs(strategies.STRATEGY_REGISTRY, STRATEGY_REGISTRY)
        self.assertIs(legacy_builder, build_strategy)
        self.assertEqual(set(STRATEGY_REGISTRY), {"cash", "buy_and_hold", "dual_ma", "grid", "bollinger", "macd", "rsi", "momentum"})
        self.assertIs(type(build_strategy("cash", {})), CashBenchmarkStrategy)
        self.assertIs(type(build_strategy("buy_and_hold", {"target_position_pct": 1.0})), BuyAndHoldBenchmarkStrategy)
        with self.assertRaisesRegex(ValueError, "explicit_target_position_pct"):
            build_strategy("buy_and_hold", {})
        with self.assertRaisesRegex(ValueError, "no_parameters"):
            build_strategy("cash", {"position_pct": 1.0})

    def test_legacy_modules_reexport_identical_canonical_objects(self) -> None:
        for module_name, symbols in PUBLIC_SYMBOLS.items():
            with self.subTest(module=module_name):
                canonical = importlib.import_module(f"hakimi_research.{module_name}")
                legacy = importlib.import_module(f"quant_bot.{module_name}")
                self.assertTrue(
                    Path(canonical.__file__).resolve().is_relative_to(
                        CANONICAL_ROOT.resolve()
                    )
                )
                for symbol in symbols:
                    self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_strategy_modules_reexport_identical_canonical_objects(self) -> None:
        modules = {
            "base": ("StrategyBase",),
            "templates": (
                "DualMovingAverageStrategy",
                "GridStrategy",
                "BollingerBandStrategy",
                "MacdStrategy",
                "RsiStrategy",
                "MomentumStrategy",
                "STRATEGY_REGISTRY",
                "build_strategy",
            ),
        }
        for module_name, symbols in modules.items():
            with self.subTest(module=module_name):
                canonical = importlib.import_module(
                    f"hakimi_research.strategies.{module_name}"
                )
                legacy = importlib.import_module(
                    f"quant_bot.strategies.{module_name}"
                )
                for symbol in symbols:
                    self.assertIs(getattr(legacy, symbol), getattr(canonical, symbol))

    def test_compatibility_wrappers_define_no_runtime_behavior(self) -> None:
        wrapper_paths = [
            PROJECT_ROOT / "quant_bot" / f"{module_name}.py"
            for module_name in PUBLIC_SYMBOLS
        ]
        wrapper_paths.extend(
            [
                PROJECT_ROOT / "quant_bot" / "strategies" / "__init__.py",
                PROJECT_ROOT / "quant_bot" / "strategies" / "base.py",
                PROJECT_ROOT / "quant_bot" / "strategies" / "templates.py",
                PROJECT_ROOT
                / "exchange_terminal"
                / "application"
                / "health_contract.py",
            ]
        )
        for path in wrapper_paths:
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                definitions = {
                    node.name
                    for node in tree.body
                    if isinstance(
                        node,
                        (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                    )
                }
                self.assertFalse(definitions)

    def test_archived_runtime_consumers_are_not_dependencies_of_canonical_source(self) -> None:
        for path in CANONICAL_ROOT.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("quant_bot.engine", source, path)
            self.assertNotIn("quant_bot.optimizer", source, path)
        frozen_source = (CANONICAL_ROOT / "frozen_evaluation.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("quant_bot", frozen_source)
        self.assertNotIn("activate_legacy_project_root", frozen_source)
        importlib.import_module("hakimi_research.frozen_evaluation")
        canonical = importlib.import_module("hakimi_research.health_contract")
        legacy = importlib.import_module(
            "exchange_terminal.application.health_contract"
        )
        self.assertIs(
            legacy.build_runtime_health_payload,
            canonical.build_runtime_health_payload,
        )
        self.assertIs(
            legacy.build_research_disabled_payload,
            canonical.build_research_disabled_payload,
        )


if __name__ == "__main__":
    unittest.main()
