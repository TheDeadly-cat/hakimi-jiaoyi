from __future__ import annotations

import ast
import hashlib
import math
import sys
import unittest
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.models import Action, Portfolio, Signal  # noqa: E402
from hakimi_research.strategies import (  # noqa: E402
    STRATEGY_BASE_SCHEMA_VERSION,
    STRATEGY_REGISTRY,
    DualMovingAverageStrategy,
    StrategyBase,
    build_strategy,
)
from quant_bot import strategies as legacy_package  # noqa: E402
from quant_bot.strategies import base as legacy_base  # noqa: E402
from quant_bot.strategies import templates as legacy_templates  # noqa: E402


ARCHIVE_ROOT = REPO_ROOT / "archive" / "historical_research"
LEGACY_ROOT = OUTPUT_ROOT / "quant_bot" / "strategies"
DETERMINISTIC_PATH = SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
ROBUSTNESS_PATH = (
    SRC_ROOT / "hakimi_research" / "synthetic_strategy_robustness_evidence.py"
)
ROBUSTNESS_WRAPPER_PATH = (
    OUTPUT_ROOT
    / "exchange_terminal"
    / "application"
    / "synthetic_strategy_robustness_evidence_v1.py"
)
ROBUSTNESS_ARCHIVE_PATH = (
    ARCHIVE_ROOT / "adr0572_synthetic_strategy_robustness_evidence_v1.py"
)
ACTIVE_CONSUMERS = (
    SRC_ROOT / "hakimi_research" / "cli.py",
    SRC_ROOT / "hakimi_research" / "backtest.py",
    SRC_ROOT / "hakimi_research" / "frozen_evaluation.py",
    SRC_ROOT / "hakimi_research" / "strategy_family_inventory.py",
    OUTPUT_ROOT / "exchange_terminal" / "application" / "synthetic_strategy_benchmark_controls_v1.py",
    OUTPUT_ROOT / "exchange_terminal" / "application" / "synthetic_strategy_high_volatility_validation_v1.py",
    OUTPUT_ROOT / "exchange_terminal" / "application" / "synthetic_strategy_execution_adversity_v1.py",
    SRC_ROOT / "hakimi_research" / "synthetic_strategy_report_bundle.py",
    ROBUSTNESS_PATH,
    ROBUSTNESS_WRAPPER_PATH,
)


class HostileStr(str):
    pass


class HostileDict(dict):
    pass


class MutatingStrategy(StrategyBase):
    def generate_signal(self, data, portfolio):
        data.iloc[0, 0] = -1.0
        portfolio.cash = 0.0
        return Signal.hold("mutating fixture")


class BadOutputStrategy(StrategyBase):
    def generate_signal(self, data, portfolio):
        return SimpleNamespace(action=Action.HOLD)


class CanonicalResearchStrategiesSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(STRATEGY_BASE_SCHEMA_VERSION, "research-strategy-base-v1")
        self.assertIs(legacy_base.StrategyBase, StrategyBase)
        self.assertIs(legacy_templates.STRATEGY_REGISTRY, STRATEGY_REGISTRY)
        self.assertIs(legacy_package.STRATEGY_REGISTRY, STRATEGY_REGISTRY)
        self.assertIs(legacy_templates.DualMovingAverageStrategy, DualMovingAverageStrategy)
        self.assertIs(legacy_package.build_strategy, build_strategy)

    def test_legacy_modules_are_definition_free(self) -> None:
        for path in (
            LEGACY_ROOT / "base.py",
            LEGACY_ROOT / "templates.py",
            LEGACY_ROOT / "__init__.py",
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_historical_implementations_are_byte_preserved(self) -> None:
        expected = {
            "adr0533_strategy_base.py": "b99fec8939ae0d914b8341b6de3fc5316e89ea799f02ba2136a49544a3869e69",
            "adr0533_strategy_templates.py": "7ce6269e5da960b5315365b076744381fd82c7efadb6e09a1a62c4b7d54c3de6",
            "adr0533_strategy_init.py": "9822754ec67747e39d92aa9d22fc1f2364db231a93c03f96a81e28f73f31b4f2",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ARCHIVE_ROOT / name).read_bytes()).hexdigest(), digest)

    def test_robustness_source_is_canonical_and_legacy_wrapper_is_definition_free(self) -> None:
        wrapper_tree = ast.parse(
            ROBUSTNESS_WRAPPER_PATH.read_text(encoding="utf-8")
        )
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(
            any(isinstance(node, definitions) for node in ast.walk(wrapper_tree))
        )
        canonical_source = ROBUSTNESS_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "def build_synthetic_strategy_robustness_evidence_v2(",
            canonical_source,
        )
        self.assertEqual(
            hashlib.sha256(ROBUSTNESS_ARCHIVE_PATH.read_bytes()).hexdigest(),
            "acf563efb0ffccc259e7753ada4b0ea636b0fe166b69c82e337b21c6cfde2c00",
        )

    def test_active_consumers_use_canonical_strategy_imports(self) -> None:
        for path in ACTIVE_CONSUMERS:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("from quant_bot.strategies", source, path)
            self.assertNotIn("import quant_bot.strategies", source, path)

    def test_deterministic_source_envelope_binds_base_and_templates(self) -> None:
        source = DETERMINISTIC_PATH.read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/strategies/base.py"', source)
        self.assertIn('"src/hakimi_research/strategies/templates.py"', source)
        self.assertNotIn('"outputs/python_quant_bot/quant_bot/strategies/templates.py"', source)

    def test_registry_is_read_only_and_contains_only_existing_six(self) -> None:
        self.assertIsInstance(STRATEGY_REGISTRY, MappingProxyType)
        self.assertEqual(
            set(STRATEGY_REGISTRY),
            {"dual_ma", "grid", "bollinger", "macd", "rsi", "momentum"},
        )
        self.assertNotIn("ensemble", STRATEGY_REGISTRY)
        with self.assertRaises(TypeError):
            STRATEGY_REGISTRY["dual_ma"] = StrategyBase  # type: ignore[index]

    def test_strategy_params_are_exact_detached_views(self) -> None:
        source = {"fast_window": 5, "slow_window": 20, "nested": {"value": 1}}
        strategy = DualMovingAverageStrategy(params=source)
        source["nested"]["value"] = 9
        self.assertEqual(strategy.params["nested"]["value"], 1)
        view = strategy.params
        view["fast_window"] = 7
        self.assertEqual(strategy.params["fast_window"], 5)
        with self.assertRaises(AttributeError):
            strategy.params = {}  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            strategy.name = "changed"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            strategy.version = "v2"  # type: ignore[misc]

    def test_strategy_identity_and_params_reject_subclasses_cycles_and_nonfinite(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        invalid = (
            lambda: StrategyBase(name=HostileStr("base")),
            lambda: StrategyBase(version=HostileStr("v1")),
            lambda: StrategyBase(params=HostileDict()),
            lambda: StrategyBase(params={"value": math.nan}),
            lambda: StrategyBase(params={"value": (1, 2)}),
            lambda: StrategyBase(params=cyclic),
        )
        for factory in invalid:
            with self.assertRaises(ValueError):
                factory()

    def test_build_strategy_preserves_keys_and_rejects_aliases(self) -> None:
        self.assertIsInstance(build_strategy("dual_ma"), DualMovingAverageStrategy)
        with self.assertRaises(ValueError):
            build_strategy(HostileStr("dual_ma"))
        with self.assertRaises(ValueError):
            build_strategy("dual_ma", HostileDict())
        with self.assertRaisesRegex(ValueError, "Unknown strategy"):
            build_strategy("unknown")

    def test_generate_signal_uses_canonical_copies_and_output(self) -> None:
        frame = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC"),
        )
        portfolio = Portfolio(1_000)
        signal = MutatingStrategy().generate_signal(frame, portfolio)
        self.assertIs(signal.action, Action.HOLD)
        self.assertEqual(frame.iloc[0, 0], 100.0)
        self.assertEqual(portfolio.cash, 1_000.0)
        with self.assertRaises(ValueError):
            MutatingStrategy().generate_signal(FrameSubclass(frame), portfolio)
        with self.assertRaises(ValueError):
            MutatingStrategy().generate_signal(frame, SimpleNamespace(cash=1_000.0))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            BadOutputStrategy().generate_signal(frame, portfolio)


class FrameSubclass(pd.DataFrame):
    pass


if __name__ == "__main__":
    unittest.main()
