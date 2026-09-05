from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

import pandas as pd

from _canonical_source import activate_canonical_source


REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_PATH = (
    REPO_ROOT
    / "outputs"
    / "python_quant_bot"
    / "quant_bot"
    / "strategies"
    / "base.py"
)

activate_canonical_source()

from hakimi_research.models import Action, Portfolio, Signal  # noqa: E402
from hakimi_research.strategies.base import (  # noqa: E402
    STRATEGY_BASE_SCHEMA_VERSION,
    StrategyBase,
)
from quant_bot.strategies import base as legacy_base  # noqa: E402


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


class FrameSubclass(pd.DataFrame):
    pass


class CanonicalResearchStrategyBaseHardeningV1Tests(unittest.TestCase):
    def test_schema_wrapper_identity_and_definition_free_boundary(self) -> None:
        self.assertEqual(
            STRATEGY_BASE_SCHEMA_VERSION,
            "research-strategy-base-v1",
        )
        self.assertIs(legacy_base.StrategyBase, StrategyBase)
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_params_and_identity_are_detached_read_only_native_values(self) -> None:
        source = {"window": 5, "nested": {"value": 1}}
        strategy = StrategyBase(source, name="fixture", version="v1")
        source["nested"]["value"] = 9
        self.assertEqual(strategy.params, {"window": 5, "nested": {"value": 1}})
        view = strategy.params
        view["window"] = 99
        self.assertEqual(strategy.params["window"], 5)
        with self.assertRaises(AttributeError):
            strategy.params = {}  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            strategy.name = "changed"  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            strategy.version = "v2"  # type: ignore[misc]

    def test_identity_and_params_reject_aliases_cycles_and_nonfinite_values(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        invalid = (
            lambda: StrategyBase(name=HostileStr("fixture")),
            lambda: StrategyBase(version=HostileStr("v1")),
            lambda: StrategyBase(params=HostileDict()),
            lambda: StrategyBase(params={"value": math.nan}),
            lambda: StrategyBase(params={"value": (1, 2)}),
            lambda: StrategyBase(params=cyclic),
        )
        for factory in invalid:
            with self.subTest(factory=factory):
                with self.assertRaises(ValueError):
                    factory()

    def test_generate_signal_gets_canonical_copies_and_must_return_signal(self) -> None:
        frame = pd.DataFrame(
            {"close": [100.0, 101.0]},
            index=pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC"),
        )
        portfolio = Portfolio(1_000)
        signal = MutatingStrategy(name="mutator").generate_signal(frame, portfolio)
        self.assertIs(signal.action, Action.HOLD)
        self.assertEqual(frame.iloc[0, 0], 100.0)
        self.assertEqual(portfolio.cash, 1_000.0)
        with self.assertRaises(ValueError):
            MutatingStrategy(name="mutator").generate_signal(
                FrameSubclass(frame),
                portfolio,
            )
        with self.assertRaises(ValueError):
            MutatingStrategy(name="mutator").generate_signal(
                frame,
                SimpleNamespace(cash=1_000.0),  # type: ignore[arg-type]
            )
        with self.assertRaises(ValueError):
            BadOutputStrategy(name="bad-output").generate_signal(frame, portfolio)


if __name__ == "__main__":
    unittest.main()
