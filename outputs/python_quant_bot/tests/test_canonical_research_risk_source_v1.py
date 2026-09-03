from __future__ import annotations

import ast
import hashlib
import math
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.config import RiskConfig  # noqa: E402
from hakimi_research.models import Action, Portfolio, Signal  # noqa: E402
from hakimi_research.risk import RISK_ENGINE_SCHEMA_VERSION, RiskManager  # noqa: E402
from quant_bot import risk as legacy_risk  # noqa: E402


ARCHIVE_PATH = REPO_ROOT / "archive" / "historical_research" / "adr0530_risk.py"
LEGACY_PATH = OUTPUT_ROOT / "quant_bot" / "risk.py"
DETERMINISTIC_PATH = SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
ACTIVE_CONSUMERS = (
    SRC_ROOT / "hakimi_research" / "cli.py",
    SRC_ROOT / "hakimi_research" / "frozen_evaluation.py",
    SRC_ROOT / "hakimi_research" / "backtest.py",
    OUTPUT_ROOT / "exchange_terminal" / "application" / "synthetic_strategy_benchmark_controls_v1.py",
    OUTPUT_ROOT / "exchange_terminal" / "application" / "synthetic_strategy_execution_adversity_v1.py",
    SRC_ROOT / "hakimi_research" / "synthetic_strategy_report_bundle.py",
)


class HostileNumber:
    calls = 0

    def __float__(self) -> float:
        type(self).calls += 1
        return 0.01


class FakeSignal:
    action = Action.BUY
    confidence = 1.0
    size_pct = 0.1
    reason = "fake"
    stop_loss_pct = None
    take_profit_pct = None
    metadata = None


class CanonicalResearchRiskSourceV1Tests(unittest.TestCase):
    def test_schema_and_legacy_identity_are_canonical(self) -> None:
        self.assertEqual(RISK_ENGINE_SCHEMA_VERSION, "research-risk-engine-v1")
        self.assertIs(legacy_risk.RiskManager, RiskManager)

    def test_legacy_module_is_definition_free(self) -> None:
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        self.assertFalse(any(isinstance(node, definitions) for node in ast.walk(tree)))

    def test_historical_implementation_is_byte_preserved(self) -> None:
        self.assertEqual(
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
            "f736087a7264744c225826d148c466cfe2c3a6038bc76c2230ac880521eb3158",
        )

    def test_active_consumers_import_canonical_risk_directly(self) -> None:
        for path in ACTIVE_CONSUMERS:
            source = path.read_text(encoding="utf-8")
            self.assertIn("from hakimi_research.risk import RiskManager", source, path)
            self.assertNotIn("from quant_bot.risk import", source, path)

    def test_deterministic_source_envelope_binds_canonical_risk(self) -> None:
        source = DETERMINISTIC_PATH.read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/risk.py"', source)
        self.assertNotIn('"outputs/python_quant_bot/quant_bot/risk.py"', source)

    def test_config_is_exact_snapshotted_and_frozen(self) -> None:
        source = RiskConfig()
        manager = RiskManager(source)
        original = manager.config.max_position_pct
        source.max_position_pct = 0.9
        self.assertEqual(manager.config.max_position_pct, original)
        with self.assertRaises(FrozenInstanceError):
            manager.config.max_position_pct = 0.8  # type: ignore[misc]
        with self.assertRaises(AttributeError):
            manager.config = source  # type: ignore[assignment]
        with self.assertRaises(ValueError):
            RiskManager(SimpleNamespace(**vars(RiskConfig())))  # type: ignore[arg-type]

    def test_state_setters_preserve_bool_hook_but_reject_aliases(self) -> None:
        manager = RiskManager(RiskConfig())
        manager.trading_halted = True
        self.assertTrue(manager.trading_halted)
        manager.reset_day(1_000)
        self.assertFalse(manager.trading_halted)
        self.assertEqual(manager.day_start_equity, 1_000.0)
        with self.assertRaises((TypeError, ValueError)):
            manager.trading_halted = 1  # type: ignore[assignment]
        with self.assertRaises((TypeError, ValueError)):
            manager.day_start_equity = "1000"  # type: ignore[assignment]

    def test_reset_day_requires_exact_native_nonnegative_equity(self) -> None:
        manager = RiskManager(RiskConfig())
        invalid = ("1000", True, math.nan, math.inf, -1, HostileNumber())
        for value in invalid:
            with self.assertRaises(ValueError):
                manager.reset_day(value)  # type: ignore[arg-type]

    def test_daily_loss_invalid_equity_halts_without_conversion(self) -> None:
        manager = RiskManager(RiskConfig())
        manager.reset_day(1_000)
        HostileNumber.calls = 0
        self.assertFalse(manager.check_daily_loss(HostileNumber()))  # type: ignore[arg-type]
        self.assertTrue(manager.trading_halted)
        self.assertEqual(HostileNumber.calls, 0)

    def test_stop_loss_rejects_hostile_and_string_values(self) -> None:
        manager = RiskManager(RiskConfig())
        HostileNumber.calls = 0
        with self.assertRaises(ValueError):
            manager.effective_stop_loss(HostileNumber())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            manager.effective_stop_loss("0.01")  # type: ignore[arg-type]
        self.assertEqual(HostileNumber.calls, 0)
        self.assertEqual(manager.effective_stop_loss(None), 0.03)

    def test_signal_to_order_requires_canonical_inputs(self) -> None:
        manager = RiskManager(RiskConfig())
        manager.reset_day(1_000)
        portfolio = Portfolio(1_000)
        with self.assertRaises(ValueError):
            manager.signal_to_order("SYNTH", FakeSignal(), portfolio, 100)  # type: ignore[arg-type]
        fake_portfolio = SimpleNamespace(**portfolio.__dict__)
        with self.assertRaises(ValueError):
            manager.signal_to_order(
                "SYNTH",
                Signal.buy("entry", 0.1),
                fake_portfolio,  # type: ignore[arg-type]
                100,
            )

    def test_signal_to_order_rejects_hostile_cost_and_symbol_aliases(self) -> None:
        manager = RiskManager(RiskConfig())
        manager.reset_day(1_000)
        portfolio = Portfolio(1_000)
        HostileNumber.calls = 0
        with self.assertRaises(ValueError):
            manager.signal_to_order(
                "SYNTH",
                Signal.buy("entry", 0.1),
                portfolio,
                100,
                fee_rate=HostileNumber(),  # type: ignore[arg-type]
            )
        with self.assertRaises(ValueError):
            manager.signal_to_order(
                "SYNTH",
                Signal.buy("entry", 0.1),
                portfolio,
                100,
                slippage_pct="0.0",  # type: ignore[arg-type]
            )
        self.assertEqual(HostileNumber.calls, 0)

        class HostileStr(str):
            pass

        with self.assertRaises(ValueError):
            manager.signal_to_order(
                HostileStr("SYNTH"),
                Signal.buy("entry", 0.1),
                portfolio,
                100,
            )

    def test_valid_entry_and_halted_reduction_semantics_remain(self) -> None:
        manager = RiskManager(RiskConfig())
        manager.reset_day(1_000)
        portfolio = Portfolio(1_000)
        entry = manager.signal_to_order(
            "SYNTH",
            Signal.buy("entry", 0.1),
            portfolio,
            100,
        )
        self.assertIsNotNone(entry)
        self.assertIs(entry.action, Action.BUY)

        manager.trading_halted = True
        open_portfolio = Portfolio(1_000, position_qty=2, avg_entry_price=100)
        exit_order = manager.signal_to_order(
            "SYNTH",
            Signal.exit("risk exit"),
            open_portfolio,
            90,
        )
        blocked_entry = manager.signal_to_order(
            "SYNTH",
            Signal.buy("blocked", 0.1),
            open_portfolio,
            90,
        )
        self.assertIsNotNone(exit_order)
        self.assertIs(exit_order.action, Action.SELL)
        self.assertIsNone(blocked_entry)

    def test_protective_exit_requires_canonical_portfolio_and_prices(self) -> None:
        manager = RiskManager(RiskConfig())
        portfolio = Portfolio(1_000, position_qty=1, avg_entry_price=100)
        with self.assertRaises(ValueError):
            manager.enforce_stop_rules(
                "SYNTH",
                SimpleNamespace(**portfolio.__dict__),  # type: ignore[arg-type]
                90,
                0.03,
                None,
            )
        with self.assertRaises(ValueError):
            manager.enforce_stop_rules("SYNTH", portfolio, "90", 0.03, None)  # type: ignore[arg-type]
        order = manager.enforce_stop_rules("SYNTH", portfolio, 90, 0.03, None)
        self.assertIsNotNone(order)
        self.assertIs(order.action, Action.SELL)


if __name__ == "__main__":
    unittest.main()
