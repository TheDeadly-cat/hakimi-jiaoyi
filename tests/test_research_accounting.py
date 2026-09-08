"""Independent synthetic accounting examples; never contacts a data provider."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import math
import unittest

import pandas as pd

from hakimi_research.backtest import (
    BacktestEngine, EX_POST_CAPACITY_MODEL_VERSION, METRIC_SEMANTICS_VERSION,
    build_backtest_reproducibility,
)
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig
from hakimi_research.benchmarks import BUY_AND_HOLD_POLICY, BuyAndHoldBenchmarkStrategy, CashBenchmarkStrategy
from hakimi_research.execution import ResearchExecutionSimulator
from hakimi_research.models import Action, Order, Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase


class ScriptedStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        action = self.get("actions", {}).get(str(len(data)), "HOLD")
        if action == "BUY":
            return Signal.buy("synthetic buy", self.get("size", 1.0), stop_loss_pct=self.get("stop", 0.5))
        if action == "HALF":
            return Signal.sell("synthetic half exit", 0.5)
        if action == "EXIT":
            return Signal.exit("synthetic final exit")
        return Signal.hold("synthetic cash")


def candles(count: int, *, close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {"open": [100.0] * count, "high": [101.0] * count,
         "low": [min(99.0, close)] * count, "close": [close] * count,
         "volume": [1000.0] * count},
        index=pd.date_range("2024-01-01", periods=count, freq="h", tz="UTC"),
    )


def engine(actions=None, *, fee=0.0, stop=0.5, size=1.0, cap=None, leverage=1.0):
    config = BotConfig(
        initial_cash=10000.0, timeframe="1h",
        risk=RiskConfig(max_position_pct=1.0, min_cash_pct=0.0, max_single_loss_pct=stop,
                        max_daily_loss_pct=0.5, max_leverage=leverage),
        execution=ExecutionConfig(fee_rate=fee, slippage_pct=0.0),
    )
    strategy = ScriptedStrategy({"actions": actions or {}, "stop": 0.5, "size": size})
    return BacktestEngine(config, strategy, RiskManager(config.risk), max_volume_participation_rate=cap)


class ResearchAccountingTests(unittest.TestCase):
    def test_first_loss_and_flat_second_bar_have_one_percent_drawdown(self):
        data = candles(3, close=99.0)
        report = engine({"1": "BUY"}).run(data, score_start=1).to_dict()
        self.assertEqual([point["equity"] for point in report["equity_curve"]], [10000.0, 9900.0, 9900.0])
        self.assertAlmostEqual(report["total_return"], -0.01)
        self.assertAlmostEqual(report["max_drawdown"], 0.01)
        self.assertAlmostEqual(report["return_series"][0]["return"], -0.01)
        self.assertEqual(report["return_series"][1]["return"], 0.0)

    def test_first_loss_and_partial_recovery_keep_original_peak(self):
        data = candles(3, close=99.0)
        data.loc[data.index[-1], "close"] = 99.5
        report = engine({"1": "BUY"}).run(data, score_start=1).to_dict()
        self.assertAlmostEqual(report["total_return"], -0.005)
        self.assertAlmostEqual(report["max_drawdown"], 0.01)
        compounded = math.prod(1 + row["return"] for row in report["return_series"]) - 1
        self.assertAlmostEqual(compounded, report["total_return"])

    def test_same_price_round_trip_includes_both_fees(self):
        report = engine({"1": "BUY", "2": "EXIT"}, fee=0.01).run(candles(3), score_start=1).to_dict()
        expected_end = 10000.0 * 0.99 / 1.01
        self.assertAlmostEqual(report["final_equity"], expected_end)
        self.assertAlmostEqual(report["realized_pnl"], expected_end - 10000.0)
        self.assertAlmostEqual(report["total_fees"], 10000.0 - expected_end)
        self.assertEqual(report["unrealized_pnl"], 0.0)
        self.assertEqual(report["round_trip_count"], 1)
        self.assertEqual(report["fill_count"], 2)
        self.assertEqual(report["win_rate"], 0.0)
        self.assertAlmostEqual(report["buy_fees"] + report["sell_fees"], report["total_fees"])
        self.assertGreater(report["buy_fees"], 0.0)
        self.assertGreater(report["sell_fees"], 0.0)

    def test_partial_exits_are_one_complete_round_trip(self):
        report = engine({"1": "BUY", "2": "HALF", "3": "EXIT"}, fee=0.01).run(candles(4), score_start=1).to_dict()
        self.assertEqual(report["signal_count"], 3)
        self.assertEqual(report["order_count"], 3)
        self.assertEqual(report["fill_count"], 3)
        self.assertEqual(report["trades"], report["fill_count"])
        self.assertEqual(report["round_trip_count"], 1)
        bought, first_exit, final_exit = report["fills"]
        self.assertAlmostEqual(bought["quantity"], first_exit["quantity"] + final_exit["quantity"])
        self.assertAlmostEqual(report["total_fees"], sum(fill["fee"] for fill in report["fills"]))
        self.assertAlmostEqual(report["round_trips"][0]["realized_pnl"], report["realized_pnl"])
        self.assertAlmostEqual(report["pnl_reconciliation_error"], 0.0)

    def test_tiny_remaining_quantity_keeps_its_material_market_value(self):
        portfolio = Portfolio(cash=10000.0)
        simulator = ResearchExecutionSimulator(fee_rate=0.0, slippage_pct=0.0)
        simulator.submit_order(Order("SYNTH", Action.BUY, 2e-12, 2e15, "small units"), portfolio)
        simulator.submit_order(Order("SYNTH", Action.SELL, 1.5e-12, 2e15, "partial exit"), portfolio)
        self.assertGreater(portfolio.position_qty, 0.0)
        self.assertAlmostEqual(portfolio.position_value(2e15), 1000.0)
        self.assertAlmostEqual(portfolio.equity(2e15), 10000.0)

    def test_partial_exit_with_open_remainder_allocates_entry_fees(self):
        report = engine({"1": "BUY", "2": "HALF"}, fee=0.01).run(candles(3), score_start=1).to_dict()
        self.assertEqual(report["round_trip_count"], 0)
        self.assertIsNone(report["win_rate"])
        self.assertGreater(report["unallocated_entry_fees"], 0.0)
        self.assertAlmostEqual(report["unrealized_pnl"], -report["unallocated_entry_fees"])
        self.assertAlmostEqual(report["final_equity"] - 10000.0, report["realized_pnl"] + report["unrealized_pnl"])

    def test_end_mark_does_not_invent_liquidation_or_exit_fee(self):
        report = engine({"1": "BUY"}, fee=0.01).run(candles(2), score_start=1).to_dict()
        self.assertEqual(report["fill_count"], 1)
        self.assertGreater(report["open_position_qty"], 0)
        self.assertEqual(report["end_position_policy"], "MARK_TO_MARKET_NO_FORCED_LIQUIDATION")
        self.assertAlmostEqual(report["final_equity"] - 10000.0, -report["total_fees"])
        self.assertAlmostEqual(report["unrealized_pnl"], -report["total_fees"])
        self.assertAlmostEqual(report["exposure_ratio"], 1.0)

    def test_cash_and_short_sample_are_explicitly_not_estimable(self):
        report = engine().run(candles(4), score_start=1).to_dict()
        self.assertIsNone(report["annualized_return"])
        self.assertIsNone(report["sharpe_ratio"])
        self.assertIsNone(report["win_rate"])
        self.assertEqual(report["statistical_status"]["annualized_return"], "SHORT_SAMPLE")
        self.assertEqual(report["statistical_status"]["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(report["signal_count"], 0)
        self.assertEqual(report["decision_count"], 3)
        self.assertEqual(report["exposure_ratio"], 0.0)
        json.dumps(report, allow_nan=False)

    def test_zero_variance_is_null_after_minimum_sample(self):
        report = engine().run(candles(31), score_start=1).to_dict()
        self.assertEqual(report["annualized_return"], 0.0)
        self.assertIsNone(report["sharpe_ratio"])
        self.assertEqual(report["statistical_status"]["sharpe_ratio"], "ZERO_VARIANCE")

    def test_annualization_counts_first_scored_interval(self):
        data = candles(31)
        data["close"] = [100.0] + [100.0 + i / 1000 for i in range(1, 31)]
        report = engine({"1": "BUY"}).run(data, score_start=1).to_dict()
        expected = (report["final_equity"] / 10000.0) ** (8760 / 30) - 1
        self.assertAlmostEqual(report["annualized_return"], expected)
        self.assertAlmostEqual(report["statistical_status"]["elapsed_years"], 30 / 8760)
        self.assertEqual(report["scoring"]["end_time"], str(data.index[-1] + pd.Timedelta(hours=1)))

    def test_warmup_does_not_trade_and_end_is_exclusive(self):
        data = candles(80)
        report = engine({"1": "BUY", "60": "BUY", "62": "EXIT"}).run(data, score_start=60, score_end=62).to_dict()
        self.assertEqual(report["scoring"]["warmup_rows"], 60)
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(len(report["return_series"]), 2)
        self.assertEqual(report["fills"][0]["signal_time"], str(data.index[59]))
        self.assertEqual(report["equity_curve"][0]["equity"], 10000.0)

    def test_score_range_is_in_result_identity(self):
        data = candles(32)
        candidate = engine()
        one = candidate.run(data, score_start=30, score_end=31).to_dict()
        two = candidate.run(data, score_start=30, score_end=32).to_dict()
        self.assertNotEqual(one["reproducibility"]["run_hash"], two["reproducibility"]["run_hash"])
        independent = build_backtest_reproducibility(data, candidate.config, candidate.strategy, score_start=30, score_end=31)
        self.assertEqual(one["reproducibility"], independent)
        self.assertEqual(one["metric_semantics_version"], METRIC_SEMANTICS_VERSION)

    def test_future_change_does_not_change_earlier_decisions_or_fills(self):
        original = candles(5)
        changed = original.copy(deep=True)
        changed.loc[changed.index[4], ["open", "high", "low", "close"]] = [80.0, 90.0, 70.0, 85.0]
        before = engine({"1": "BUY", "2": "HALF", "4": "EXIT"}).run(original, score_start=1).to_dict()
        after = engine({"1": "BUY", "2": "HALF", "4": "EXIT"}).run(changed, score_start=1).to_dict()
        self.assertEqual(before["signals"], after["signals"])
        self.assertEqual(before["fills"][:2], after["fills"][:2])
        self.assertEqual(before["equity_curve"][:4], after["equity_curve"][:4])

    def test_shared_capacity_exhaustion_does_not_grant_stop_new_volume(self):
        data = candles(2, close=99.0)
        data["low"] = 90.0
        data["volume"] = 10.0
        report = engine({"1": "BUY"}, cap=0.1, stop=0.02).run(data, score_start=1).to_dict()
        self.assertEqual(report["execution_model"], EX_POST_CAPACITY_MODEL_VERSION)
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(report["order_count"], 2)
        self.assertEqual(report["orders"][1]["admission_reason"], "VOLUME_CAPACITY_UNAVAILABLE")
        self.assertEqual(report["open_position_qty"], 1.0)
        self.assertIn("EX_POST_VOLUME_CAPACITY", report["fills"][0]["fill_basis"])
        self.assertEqual(report["orders"][0]["cancelled_quantity"], 99.0)

    def test_shared_capacity_partial_stop_and_next_bar_reset(self):
        data = candles(3, close=99.0)
        data["low"] = 90.0
        data["volume"] = [1000.0, 30.0, 10.0]
        report = engine({"1": "BUY"}, cap=0.1, stop=0.02, size=0.02).run(data, score_start=1).to_dict()
        first_bar = [fill for fill in report["fills"] if fill["fill_time"] == str(data.index[1])]
        self.assertEqual(sum(fill["quantity"] for fill in first_bar), 3.0)
        self.assertEqual(report["fill_count"], 3)
        self.assertEqual(report["round_trip_count"], 1)
        self.assertEqual(report["open_position_qty"], 0.0)
        self.assertAlmostEqual(report["pnl_reconciliation_error"], 0.0)

    def test_zero_volume_cancels_without_creating_a_fill(self):
        data = candles(2)
        data["volume"] = 0.0
        report = engine({"1": "BUY"}, cap=0.1).run(data, score_start=1).to_dict()
        self.assertEqual(report["fill_count"], 0)
        self.assertEqual(report["order_count"], 1)
        self.assertEqual(report["final_equity"], 10000.0)

    def test_requested_effective_stops_and_unsupported_leverage_are_visible(self):
        report = engine({"1": "BUY"}, stop=0.02, leverage=2.0).run(candles(2), score_start=1).to_dict()
        self.assertEqual(report["signals"][0]["requested_stop_loss_pct"], 0.5)
        self.assertEqual(report["signals"][0]["effective_stop_loss_pct"], 0.02)
        self.assertFalse(report["risk_semantics"]["stop_loss"]["account_loss_guarantee"])
        self.assertFalse(report["risk_semantics"]["daily_loss"]["continuous_position_liquidation"])
        self.assertFalse(report["risk_semantics"]["leverage"]["supported"])
        self.assertEqual(report["risk_semantics"]["leverage"]["effective"], 1.0)

    def test_report_ledger_is_detached_and_sealed(self):
        report = engine({"1": "BUY"}).run(candles(2), score_start=1)
        ledger = report.orders
        ledger[0]["filled_quantity"] = 999999.0
        self.assertNotEqual(report.orders[0]["filled_quantity"], 999999.0)
        with self.assertRaises(FrozenInstanceError):
            report.accounting = {}

    def test_buy_and_hold_enters_once_without_stops_and_restarts_fresh(self):
        data = candles(6)
        data.loc[data.index[2]:, ["open", "high", "low", "close"]] = [50.0, 60.0, 40.0, 45.0]
        config = engine(fee=0.01, stop=0.02).config
        benchmark = BuyAndHoldBenchmarkStrategy({"target_position_pct": 1.0})
        candidate = BacktestEngine(config, benchmark, RiskManager(config.risk), benchmark_policy=BUY_AND_HOLD_POLICY)
        report = candidate.run(data, score_start=1).to_dict()
        repeated = candidate.run(data, score_start=1).to_dict()
        self.assertEqual(report, repeated)
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(report["order_count"], 1)
        self.assertEqual(report["signals"][0]["action"], "BUY")
        self.assertTrue(all(signal["action"] == "HOLD" for signal in report["signals"][1:]))
        self.assertEqual(report["fills"][0]["fill_time"], str(data.index[1]))
        self.assertAlmostEqual(report["final_equity"], 10000.0 / 1.01 * 0.45)
        self.assertFalse(report["risk_semantics"]["protective_exits_enabled"])
        self.assertIsNone(report["signals"][0]["effective_stop_loss_pct"])
        self.assertEqual(report["sell_fees"], 0.0)
        self.assertAlmostEqual(report["buy_fees"], report["total_fees"])

    def test_buy_and_hold_empty_initial_capacity_is_not_retried(self):
        data = candles(4)
        data.loc[data.index[1], "volume"] = 0.0
        config = engine().config
        candidate = BacktestEngine(config, BuyAndHoldBenchmarkStrategy({"target_position_pct": 1.0}),
                                   RiskManager(config.risk), benchmark_policy=BUY_AND_HOLD_POLICY,
                                   max_volume_participation_rate=0.1)
        result = candidate.run(data, score_start=1).to_dict()
        self.assertEqual(result["order_count"], 1)
        self.assertEqual(result["fill_count"], 0)

    def test_policy_cannot_disable_protection_for_a_normal_strategy(self):
        config = engine().config
        with self.assertRaisesRegex(ValueError, "exact_strategy_and_explicit_policy"):
            BacktestEngine(config, ScriptedStrategy(), RiskManager(config.risk), benchmark_policy=BUY_AND_HOLD_POLICY)
        with self.assertRaisesRegex(ValueError, "exact_strategy_and_explicit_policy"):
            BacktestEngine(config, BuyAndHoldBenchmarkStrategy({"target_position_pct": 1.0}), RiskManager(config.risk))
        config.risk.min_cash_pct = 0.1
        with self.assertRaisesRegex(ValueError, "explicit_full_spot_capacity_risk"):
            BacktestEngine(config, BuyAndHoldBenchmarkStrategy({"target_position_pct": 1.0}),
                           RiskManager(config.risk), benchmark_policy=BUY_AND_HOLD_POLICY)

    def test_cash_benchmark_uses_same_engine_and_has_no_fills(self):
        config = engine().config
        candidate = BacktestEngine(config, CashBenchmarkStrategy(), RiskManager(config.risk))
        report = candidate.run(candles(4), score_start=1).to_dict()
        self.assertEqual(report["fill_count"], 0)
        self.assertEqual(report["total_return"], 0.0)
        self.assertEqual(report["buy_fees"], report["sell_fees"])
        self.assertIsNone(report["sharpe_ratio"])


if __name__ == "__main__":
    unittest.main()
