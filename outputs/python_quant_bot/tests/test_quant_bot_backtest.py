from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import tempfile
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.execution import PaperBroker, build_broker
from quant_bot.models import Action, Order, Portfolio, Signal
from quant_bot.risk import RiskManager
from quant_bot.strategies.base import StrategyBase


def price_frame(count: int = 140) -> pd.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    index = pd.DatetimeIndex([start + timedelta(days=offset) for offset in range(count)])
    close = [100 + offset * 0.1 for offset in range(count)]
    return pd.DataFrame({
        "open": [value - 0.05 for value in close],
        "high": [value + 1 for value in close],
        "low": [value - 1 for value in close],
        "close": close,
        "volume": [1_000 + offset for offset in range(count)],
    }, index=index)


class OneShotStrategy(StrategyBase):
    name = "one_shot"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if len(data) == 30 and portfolio.position_qty <= 0:
            return Signal.buy("close signal", 0.25)
        if len(data) == 31 and portfolio.position_qty > 0:
            return Signal.exit("next close exit")
        return Signal.hold()


class IntrabarConflictStrategy(StrategyBase):
    name = "intrabar_conflict"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if len(data) == 30 and portfolio.position_qty <= 0:
            return Signal.buy("conflict entry", 0.25, stop_loss_pct=0.05, take_profit_pct=0.05)
        return Signal.hold()


class BuyAndHoldStrategy(StrategyBase):
    name = "buy_and_hold"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if len(data) == 30 and portfolio.position_qty <= 0:
            return Signal.buy("persistent position", 1.0)
        return Signal.hold()


class QuantBotBacktestTests(unittest.TestCase):
    def config(self) -> BotConfig:
        config = BotConfig(market="stock", symbol="AAPL", timeframe="1d")
        config.execution.fee_rate = 0.0
        config.execution.slippage_pct = 0.0
        return config

    def test_cli_backtest_signals_at_close_and_fills_next_open(self) -> None:
        frame = price_frame()
        config = self.config()
        report = BacktestEngine(config, OneShotStrategy(), RiskManager(config.risk)).run(frame)

        self.assertEqual(report.execution_model, "signal-close-next-open-ohlc-conservative-v3")
        self.assertEqual(report.fills[0]["signal_time"], str(frame.index[29]))
        self.assertEqual(report.fills[0]["fill_time"], str(frame.index[30]))
        self.assertEqual(report.fills[0]["fill_basis"], "NEXT_BAR_OPEN")
        self.assertAlmostEqual(report.fills[0]["price"], frame.iloc[30]["open"], places=8)
        self.assertEqual(report.reproducibility["hash_scope"], "FULL_OHLCV")
        self.assertEqual(report.reproducibility["data_rows"], len(frame))
        self.assertTrue(report.reproducibility["run_hash"])

    def test_cli_backtest_uses_stop_first_when_one_bar_hits_both(self) -> None:
        frame = price_frame()
        frame.iloc[30, frame.columns.get_loc("open")] = 103.0
        frame.iloc[30, frame.columns.get_loc("high")] = 120.0
        frame.iloc[30, frame.columns.get_loc("low")] = 80.0
        config = self.config()
        report = BacktestEngine(config, IntrabarConflictStrategy(), RiskManager(config.risk)).run(frame)

        self.assertEqual(report.ambiguous_intrabar_count, 1)
        self.assertEqual(report.fills[1]["fill_basis"], "INTRABAR_STOP")

    def test_paper_broker_realized_pnl_includes_entry_and_exit_fees(self) -> None:
        portfolio = Portfolio(cash=1_000)
        broker = PaperBroker(fee_rate=0.01, slippage_pct=0.0)
        broker.submit_order(Order("AAPL", Action.BUY, 1, 100, "entry"), portfolio)
        fill = broker.submit_order(Order("AAPL", Action.SELL, 1, 100, "exit"), portfolio)

        self.assertAlmostEqual(fill.pnl, -2.0, places=8)
        self.assertAlmostEqual(portfolio.realized_pnl, -2.0, places=8)
        self.assertEqual(portfolio.entry_fees, 0.0)

    def test_paper_broker_affordability_includes_the_actual_fee_rate(self) -> None:
        portfolio = Portfolio(cash=1_000)
        broker = PaperBroker(fee_rate=0.01, slippage_pct=0.0)
        order = Order("AAPL", Action.BUY, 20, 100, "oversized")

        fill = broker.submit_order(order, portfolio)

        self.assertAlmostEqual(fill.quantity, 1_000 / 101, places=8)
        self.assertEqual(order.quantity, 20)
        self.assertGreaterEqual(portfolio.cash, -1e-9)
        self.assertAlmostEqual(portfolio.cash, 0.0, places=8)

    def test_paper_broker_rejects_unsupported_actions_without_mutating_account(self) -> None:
        portfolio = Portfolio(cash=1_000)
        before = Portfolio(**portfolio.__dict__)

        with self.assertRaisesRegex(ValueError, "only accepts BUY and SELL"):
            PaperBroker().submit_order(Order("AAPL", Action.HOLD, 1, 100, "invalid"), portfolio)

        self.assertEqual(portfolio, before)

    def test_risk_sizing_preserves_the_cash_floor_after_costs(self) -> None:
        config = self.config()
        config.risk.max_position_pct = 1.0
        config.risk.min_cash_pct = 0.05
        config.execution.fee_rate = 0.01
        config.execution.slippage_pct = 0.01
        portfolio = Portfolio(cash=10_000)
        risk = RiskManager(config.risk)
        order = risk.signal_to_order(
            "AAPL",
            Signal.buy("entry", 1.0),
            portfolio,
            100.0,
            fee_rate=config.execution.fee_rate,
            slippage_pct=config.execution.slippage_pct,
        )

        self.assertIsNotNone(order)
        PaperBroker(config.execution.fee_rate, config.execution.slippage_pct).submit_order(order, portfolio)
        self.assertGreaterEqual(portfolio.cash, 500.0 - 1e-8)

    def test_halted_risk_still_allows_position_reduction(self) -> None:
        config = self.config()
        risk = RiskManager(config.risk)
        risk.trading_halted = True
        portfolio = Portfolio(cash=1_000, position_qty=10, avg_entry_price=100)

        exit_order = risk.signal_to_order("AAPL", Signal.exit("risk exit"), portfolio, 90.0)
        buy_order = risk.signal_to_order("AAPL", Signal.buy("blocked", 0.1), portfolio, 90.0)

        self.assertIsNotNone(exit_order)
        self.assertEqual(exit_order.action, Action.SELL)
        self.assertIsNone(buy_order)

    def test_daily_loss_baseline_resets_to_the_previous_session_close(self) -> None:
        frame = price_frame(80)
        closes = [100.0 * (0.99 ** index) for index in range(len(frame))]
        frame["open"] = closes
        frame["high"] = [value * 1.001 for value in closes]
        frame["low"] = [value * 0.999 for value in closes]
        frame["close"] = closes
        config = self.config()
        config.risk.max_position_pct = 1.0
        config.risk.min_cash_pct = 0.0
        config.risk.max_single_loss_pct = 1.0
        config.risk.max_daily_loss_pct = 0.05
        risk = RiskManager(config.risk)

        report = BacktestEngine(config, BuyAndHoldStrategy(), risk).run(frame)

        self.assertFalse(risk.trading_halted)
        self.assertEqual(report.trades, 1)

    def test_daily_string_index_cannot_hide_duplicate_sessions(self) -> None:
        frame = price_frame(40)
        labels = [timestamp.isoformat() for timestamp in frame.index]
        labels[31] = labels[30].replace("00:00:00", "12:00:00")
        frame.index = labels

        with self.assertRaisesRegex(ValueError, "duplicate trading sessions"):
            BacktestEngine(self.config(), OneShotStrategy(), RiskManager(self.config().risk)).run(frame)

    def test_cli_backtest_rejects_invalid_ohlcv_and_numeric_configuration(self) -> None:
        invalid_frame = price_frame()
        invalid_frame.iloc[50, invalid_frame.columns.get_loc("close")] = float("nan")
        config = self.config()
        with self.assertRaisesRegex(ValueError, "finite OHLCV"):
            BacktestEngine(config, OneShotStrategy(), RiskManager(config.risk)).run(invalid_frame)

        invalid_config = self.config()
        invalid_config.initial_cash = float("nan")
        with self.assertRaisesRegex(ValueError, "numeric configuration"):
            BacktestEngine(invalid_config, OneShotStrategy(), RiskManager(invalid_config.risk)).run(price_frame())

    def test_cli_backtest_run_hash_binds_capital_and_risk_contract(self) -> None:
        baseline = self.config()
        changed_capital = self.config()
        changed_capital.initial_cash = baseline.initial_cash * 2
        changed_risk = self.config()
        changed_risk.risk.max_position_pct = baseline.risk.max_position_pct / 2

        reports = [
            BacktestEngine(config, OneShotStrategy(), RiskManager(config.risk)).run(price_frame())
            for config in (baseline, changed_capital, changed_risk)
        ]
        hashes = {report.reproducibility["run_hash"] for report in reports}

        self.assertEqual(len(hashes), 3)
        self.assertTrue(all(report.reproducibility["risk_hash"] for report in reports))

    def test_standalone_live_broker_is_permanently_blocked(self) -> None:
        config = self.config()
        config.mode = "live"
        config.execution.broker = "ccxt"
        config.execution.live_trading_enabled = True

        with self.assertRaisesRegex(RuntimeError, "Live trading hard wall"):
            build_broker(config)

    def test_config_loader_forces_paper_even_when_file_requests_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unsafe.json"
            path.write_text(
                '{"mode":"live","execution":{"broker":"ccxt","live_trading_enabled":true}}',
                encoding="utf-8",
            )
            config = BotConfig.from_file(path)

        self.assertEqual(config.mode, "paper")
        self.assertEqual(config.execution.broker, "paper")
        self.assertFalse(config.execution.live_trading_enabled)

    def test_legacy_dashboard_has_no_live_toggle_or_ccxt_selector(self) -> None:
        source = (PROJECT_ROOT / "dashboard_app.py").read_text(encoding="utf-8")
        self.assertNotIn("允许实盘下单", source)
        self.assertNotIn('["paper", "ccxt"]', source)


if __name__ == "__main__":
    unittest.main()
