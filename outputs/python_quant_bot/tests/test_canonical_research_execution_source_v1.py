from __future__ import annotations

import ast
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.execution import (  # noqa: E402
    EXECUTION_ADMISSION_SCHEMA_VERSION,
    EXECUTION_SIMULATOR_SCHEMA_VERSION,
    ResearchExecutionSimulator,
)
from hakimi_research.models import Action, Order, Portfolio  # noqa: E402
from quant_bot import execution as legacy_execution  # noqa: E402


LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "execution.py"
BACKTEST_PATH = SRC_ROOT / "hakimi_research" / "backtest.py"


class HostileNumber:
    calls = 0

    def __float__(self) -> float:
        type(self).calls += 1
        return 0.0


class HostileFloat(float):
    calls = 0

    def __float__(self) -> float:
        type(self).calls += 1
        return super().__float__()


class CanonicalResearchExecutionSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(
            EXECUTION_SIMULATOR_SCHEMA_VERSION,
            "research-execution-simulator-v3",
        )
        self.assertEqual(
            EXECUTION_ADMISSION_SCHEMA_VERSION,
            "research-execution-admission-v1",
        )
        self.assertIs(
            legacy_execution.ResearchExecutionSimulator,
            ResearchExecutionSimulator,
        )

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_active_backtest_imports_canonical_execution_directly(self) -> None:
        source = BACKTEST_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from hakimi_research.execution import ResearchExecutionSimulator",
            source,
        )
        self.assertNotIn("from quant_bot.execution import", source)

    def test_configuration_is_normalized_and_frozen(self) -> None:
        simulator = ResearchExecutionSimulator(fee_rate=0, slippage_pct=0)
        self.assertEqual(simulator.fee_rate, 0.0)
        self.assertEqual(simulator.slippage_pct, 0.0)
        self.assertIsNone(simulator.max_volume_participation_rate)
        self.assertIsNone(simulator.minimum_executable_quantity)
        with self.assertRaises(FrozenInstanceError):
            simulator.fee_rate = 0.1  # type: ignore[misc]

    def test_configuration_rejects_non_native_nonfinite_and_out_of_range(self) -> None:
        HostileNumber.calls = 0
        invalid = (
            lambda: ResearchExecutionSimulator(fee_rate="0.0"),
            lambda: ResearchExecutionSimulator(fee_rate=True),
            lambda: ResearchExecutionSimulator(fee_rate=float("nan")),
            lambda: ResearchExecutionSimulator(slippage_pct=math.inf),
            lambda: ResearchExecutionSimulator(fee_rate=-0.01),
            lambda: ResearchExecutionSimulator(slippage_pct=1.0),
            lambda: ResearchExecutionSimulator(fee_rate=HostileNumber()),
            lambda: ResearchExecutionSimulator(max_volume_participation_rate=True),
            lambda: ResearchExecutionSimulator(max_volume_participation_rate=0),
            lambda: ResearchExecutionSimulator(max_volume_participation_rate=1.1),
            lambda: ResearchExecutionSimulator(minimum_executable_quantity=True),
            lambda: ResearchExecutionSimulator(minimum_executable_quantity=0),
        )
        for factory in invalid:
            with self.assertRaises(ValueError):
                factory()
        self.assertEqual(HostileNumber.calls, 0)

    def test_volume_participation_cap_creates_atomic_partial_fill(self) -> None:
        portfolio = Portfolio(10_000)
        order = Order("SYNTH", Action.BUY, 10, 100, "capacity entry")
        fill = ResearchExecutionSimulator(
            fee_rate=0,
            slippage_pct=0,
            max_volume_participation_rate=0.1,
        ).submit_order(
            order,
            portfolio,
            available_volume=20,
        )
        self.assertEqual(order.quantity, 10.0)
        self.assertEqual(fill.quantity, 2.0)
        self.assertEqual(portfolio.position_qty, 2.0)
        self.assertEqual(portfolio.cash, 9_800.0)

    def test_minimum_quantity_admission_rejects_without_mutation(self) -> None:
        portfolio = Portfolio(10_000)
        order = Order("SYNTH", Action.BUY, 10, 100, "capacity entry")
        simulator = ResearchExecutionSimulator(
            fee_rate=0,
            slippage_pct=0,
            max_volume_participation_rate=0.1,
            minimum_executable_quantity=3,
        )
        before = dict(portfolio.__dict__)
        decision = simulator.assess_order(
            order,
            portfolio,
            available_volume=20,
        )
        self.assertEqual(decision.status, "REJECTED")
        self.assertEqual(decision.reason, "MINIMUM_EXECUTABLE_QUANTITY_NOT_MET")
        self.assertEqual(decision.executable_quantity, 2.0)
        self.assertEqual(decision.to_dict()["schema_version"], EXECUTION_ADMISSION_SCHEMA_VERSION)
        self.assertEqual(portfolio.__dict__, before)
        with self.assertRaisesRegex(ValueError, "MINIMUM_EXECUTABLE_QUANTITY_NOT_MET"):
            simulator.submit_order(order, portfolio, available_volume=20)
        self.assertEqual(portfolio.__dict__, before)

    def test_minimum_quantity_admission_accepts_exact_floor(self) -> None:
        portfolio = Portfolio(10_000)
        decision = ResearchExecutionSimulator(
            fee_rate=0,
            slippage_pct=0,
            max_volume_participation_rate=0.1,
            minimum_executable_quantity=2,
        ).assess_order(
            Order("SYNTH", Action.BUY, 10, 100, "capacity entry"),
            portfolio,
            available_volume=20,
        )
        self.assertEqual(decision.status, "ACCEPTED")
        self.assertEqual(decision.reason, "NONE")

    def test_volume_cap_requires_positive_native_available_volume(self) -> None:
        simulator = ResearchExecutionSimulator(
            max_volume_participation_rate=0.1,
        )
        for value in (None, 0, -1, True, "20"):
            with self.subTest(value=value):
                portfolio = Portfolio(10_000)
                before = dict(portfolio.__dict__)
                with self.assertRaises(ValueError):
                    simulator.submit_order(
                        Order("SYNTH", Action.BUY, 10, 100, "capacity entry"),
                        portfolio,
                        available_volume=value,  # type: ignore[arg-type]
                    )
                self.assertEqual(portfolio.__dict__, before)

    def test_valid_buy_is_atomic_and_fee_aware(self) -> None:
        portfolio = Portfolio(1_000)
        fill = ResearchExecutionSimulator(fee_rate=0.01, slippage_pct=0).submit_order(
            Order("SYNTH", Action.BUY, 2, 100, "entry"),
            portfolio,
        )
        self.assertEqual(fill.quantity, 2.0)
        self.assertEqual(fill.fee, 2.0)
        self.assertEqual(portfolio.cash, 798.0)
        self.assertEqual(portfolio.position_qty, 2.0)
        self.assertEqual(portfolio.entry_fees, 2.0)

    def test_valid_sell_preserves_realized_fee_semantics(self) -> None:
        portfolio = Portfolio(
            cash=798,
            position_qty=2,
            avg_entry_price=100,
            entry_fees=2,
        )
        fill = ResearchExecutionSimulator(fee_rate=0.01, slippage_pct=0).submit_order(
            Order("SYNTH", Action.SELL, 2, 110, "exit"),
            portfolio,
        )
        self.assertEqual(fill.fee, 2.2)
        self.assertAlmostEqual(fill.pnl, 15.8)
        self.assertEqual(portfolio.position_qty, 0.0)
        self.assertEqual(portfolio.avg_entry_price, 0.0)
        self.assertEqual(portfolio.entry_fees, 0.0)

    def test_structural_fake_order_and_portfolio_are_rejected_without_mutation(self) -> None:
        fake_order = SimpleNamespace(
            symbol="SYNTH",
            action=Action.BUY,
            quantity=1.0,
            price=100.0,
            reason="fake live",
            is_live=True,
        )
        fake_portfolio = SimpleNamespace(
            cash=1_000.0,
            position_qty=0.0,
            avg_entry_price=0.0,
            realized_pnl=0.0,
            entry_fees=0.0,
        )
        before = dict(vars(fake_portfolio))
        with self.assertRaises(ValueError):
            ResearchExecutionSimulator().submit_order(fake_order, fake_portfolio)
        self.assertEqual(vars(fake_portfolio), before)

        canonical_order = Order("SYNTH", Action.BUY, 1, 100, "entry")
        with self.assertRaises(ValueError):
            ResearchExecutionSimulator().submit_order(canonical_order, fake_portfolio)
        self.assertEqual(vars(fake_portfolio), before)

    def test_mutated_portfolio_hostile_number_is_rejected_without_conversion(self) -> None:
        HostileFloat.calls = 0
        portfolio = Portfolio(1_000)
        portfolio.cash = HostileFloat(1_000)
        with self.assertRaises(ValueError):
            ResearchExecutionSimulator().submit_order(
                Order("SYNTH", Action.BUY, 1, 100, "entry"),
                portfolio,
            )
        self.assertEqual(HostileFloat.calls, 0)

    def test_fill_failure_occurs_before_portfolio_commit(self) -> None:
        portfolio = Portfolio(1_000)
        before = dict(portfolio.__dict__)
        with patch(
            "hakimi_research.execution.Fill",
            side_effect=ValueError("synthetic Fill failure"),
        ):
            with self.assertRaisesRegex(ValueError, "synthetic Fill failure"):
                ResearchExecutionSimulator(fee_rate=0, slippage_pct=0).submit_order(
                    Order("SYNTH", Action.BUY, 1, 100, "entry"),
                    portfolio,
                )
        self.assertEqual(portfolio.__dict__, before)


if __name__ == "__main__":
    unittest.main()
