from __future__ import annotations

import ast
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from enum import Enum
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.models import (  # noqa: E402
    DOMAIN_MODEL_SCHEMA_VERSION,
    Action,
    Fill,
    Order,
    Portfolio,
    Signal,
)
from quant_bot import models as legacy_models  # noqa: E402


LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "models.py"
ACTIVE_CONSUMERS = (
    SRC_ROOT / "hakimi_research" / "frozen_evaluation.py",
    SRC_ROOT / "hakimi_research" / "strategies" / "base.py",
    SRC_ROOT / "hakimi_research" / "strategies" / "templates.py",
    SRC_ROOT / "hakimi_research" / "execution.py",
    SRC_ROOT / "hakimi_research" / "risk.py",
    SRC_ROOT / "hakimi_research" / "backtest.py",
)


class HostileStr(str):
    pass


class HostileFloat(float):
    pass


class HostileDict(dict):
    pass


class DuplicateAction(str, Enum):
    BUY = "BUY"


class CanonicalResearchModelsSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(DOMAIN_MODEL_SCHEMA_VERSION, "research-domain-models-v1")
        for name in ("Action", "Signal", "Portfolio", "Order", "Fill"):
            self.assertIs(getattr(legacy_models, name), globals()[name])

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (
            ast.ClassDef,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        )
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_active_consumers_import_canonical_models_directly(self) -> None:
        for path in ACTIVE_CONSUMERS:
            source = path.read_text(encoding="utf-8")
            self.assertIn("from hakimi_research.models import", source, path)
            self.assertNotIn("from quant_bot.models import", source, path)

    def test_signal_factories_normalize_native_numbers(self) -> None:
        signal = Signal.buy("entry", 1, confidence=1, stop_loss_pct=0.1)
        self.assertIs(signal.action, Action.BUY)
        self.assertEqual(signal.size_pct, 1.0)
        self.assertEqual(signal.confidence, 1.0)
        self.assertEqual(Signal.exit("exit").size_pct, 1.0)
        self.assertIs(Signal.hold().action, Action.HOLD)

    def test_signal_rejects_plain_or_duplicate_actions(self) -> None:
        with self.assertRaises(ValueError):
            Signal("BUY")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            Signal(DuplicateAction.BUY)  # type: ignore[arg-type]

    def test_signal_rejects_nonfinite_out_of_range_and_hostile_values(self) -> None:
        invalid_factories = (
            lambda: Signal(Action.BUY, confidence=float("nan")),
            lambda: Signal(Action.BUY, confidence=1.01),
            lambda: Signal(Action.BUY, size_pct=-0.01),
            lambda: Signal(Action.BUY, size_pct=1.01),
            lambda: Signal(Action.BUY, reason=HostileStr("reason")),
            lambda: Signal(Action.BUY, confidence=HostileFloat(0.5)),
            lambda: Signal(Action.BUY, stop_loss_pct=0.0),
        )
        for factory in invalid_factories:
            with self.subTest(factory=factory):
                with self.assertRaises(ValueError):
                    factory()

    def test_signal_is_frozen_and_metadata_is_detached(self) -> None:
        metadata = {"source": "fixture", "nested": [{"value": 1.0}]}
        signal = Signal(Action.HOLD, metadata=metadata)
        metadata["source"] = "mutated"
        metadata["nested"][0]["value"] = 2.0
        self.assertEqual(signal.metadata, {"source": "fixture", "nested": [{"value": 1.0}]})
        with self.assertRaises(FrozenInstanceError):
            signal.action = Action.BUY  # type: ignore[misc]

    def test_metadata_rejects_cycles_nonfinite_and_subclasses(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        invalid = (
            cyclic,
            {"value": float("inf")},
            HostileDict({"source": "fixture"}),
            {HostileStr("key"): "value"},
            {"value": (1, 2)},
        )
        for metadata in invalid:
            with self.subTest(metadata=type(metadata).__name__):
                with self.assertRaises(ValueError):
                    Signal(Action.HOLD, metadata=metadata)  # type: ignore[arg-type]

    def test_portfolio_normalizes_native_numbers_and_remains_mutable(self) -> None:
        portfolio = Portfolio(cash=1_000, position_qty=2, avg_entry_price=10)
        self.assertEqual(portfolio.equity(12), 1_024.0)
        self.assertEqual(portfolio.position_value(12), 24.0)
        portfolio.cash = 900.0
        self.assertEqual(portfolio.cash, 900.0)

    def test_portfolio_rejects_invalid_initial_state_and_prices(self) -> None:
        invalid = (
            lambda: Portfolio(float("nan")),
            lambda: Portfolio(-1),
            lambda: Portfolio(1_000, position_qty=-1),
            lambda: Portfolio(HostileFloat(1_000)),
        )
        for factory in invalid:
            with self.assertRaises(ValueError):
                factory()
        with self.assertRaises(ValueError):
            Portfolio(1_000).equity(float("inf"))

    def test_order_is_research_only_and_frozen(self) -> None:
        order = Order("SYNTH", Action.BUY, 1, 100, "entry")
        self.assertFalse(order.is_live)
        self.assertEqual(order.quantity, 1.0)
        with self.assertRaises(FrozenInstanceError):
            order.price = 101.0  # type: ignore[misc]
        invalid = (
            lambda: Order("SYNTH", Action.BUY, -1, 100, "entry"),
            lambda: Order("SYNTH", Action.BUY, 1, float("nan"), "entry"),
            lambda: Order("SYNTH", Action.HOLD, 1, 100, "entry"),
            lambda: Order("SYNTH", Action.BUY, 1, 100, "entry", is_live=True),
            lambda: Order(HostileStr("SYNTH"), Action.BUY, 1, 100, "entry"),
        )
        for factory in invalid:
            with self.assertRaises(ValueError):
                factory()

    def test_fill_is_validated_and_frozen(self) -> None:
        fill = Fill("SYNTH", Action.SELL, 1, 100, 0, -2, "exit")
        self.assertEqual(fill.fee, 0.0)
        self.assertEqual(fill.pnl, -2.0)
        with self.assertRaises(FrozenInstanceError):
            fill.fee = 1.0  # type: ignore[misc]
        invalid = (
            lambda: Fill("SYNTH", Action.BUY, 0, 100, 0, 0, "entry"),
            lambda: Fill("SYNTH", Action.BUY, 1, 100, -1, 0, "entry"),
            lambda: Fill("SYNTH", Action.EXIT, 1, 100, 0, 0, "entry"),
            lambda: Fill("SYNTH", Action.BUY, 1, 100, 0, math.inf, "entry"),
        )
        for factory in invalid:
            with self.assertRaises(ValueError):
                factory()


if __name__ == "__main__":
    unittest.main()
