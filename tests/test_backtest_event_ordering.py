"""Synthetic event-order regressions; OHLC rows never come from a provider."""
from __future__ import annotations

import unittest

import pandas as pd

from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig
from hakimi_research.models import Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase


class TimedSignalStrategy(StrategyBase):
    name = "event_order_fixture"
    version = "v1"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        decision = self.get("decisions", {}).get(str(len(data)), "HOLD")
        if decision == "BUY":
            return Signal.buy("scheduled buy", 0.15, stop_loss_pct=0.03, take_profit_pct=0.08)
        if decision == "HALF":
            return Signal.sell("scheduled half exit", 0.5)
        return Signal.hold("scheduled hold")


def frame(rows: list[tuple[float, ...]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["open", "high", "low", "close", "volume"],
        index=pd.date_range("2024-01-01", periods=len(rows), freq="h", tz="UTC"),
    )


def run_case(rows, decisions, *, fee=0.0, capacity=None) -> dict:
    config = BotConfig(
        market="crypto_spot", symbol="BTC-USDT", timeframe="1h", initial_cash=10000.0,
        execution=ExecutionConfig(fee_rate=fee, slippage_pct=0.0),
        risk=RiskConfig(max_position_pct=1.0, max_single_loss_pct=0.03,
                        max_daily_loss_pct=1.0, min_cash_pct=0.0, max_leverage=1.0),
    )
    candidate = BacktestEngine(
        config, TimedSignalStrategy({"decisions": decisions}), RiskManager(config.risk),
        max_volume_participation_rate=capacity,
    )
    return candidate.run(frame(rows), score_start=1).to_dict()


NORMAL = (100.0, 101.0, 99.0, 100.0, 1000.0)


class BacktestEventOrderingTests(unittest.TestCase):
    def test_existing_gap_stop_cannot_be_moved_by_pending_addition(self):
        report = run_case([NORMAL, NORMAL, (95.0, 96.0, 94.8, 95.0, 1000.0)],
                          {"1": "BUY", "2": "BUY"})
        entry, exit_fill = report["fills"]
        self.assertEqual(entry["quantity"], 15.0)
        self.assertEqual(entry["cash_after"], 8500.0)
        self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL"])
        self.assertEqual(exit_fill["position_before"], 15.0)
        self.assertEqual(exit_fill["quantity"], 15.0)
        self.assertEqual(exit_fill["price"], 95.0)
        self.assertEqual(exit_fill["fill_basis"], "GAP_OPEN")
        self.assertEqual(report["open_position_qty"], 0.0)
        self.assertEqual(report["final_equity"], 9925.0)
        self.assertEqual(report["signals"][1]["execution_disposition"], "CANCELLED_OLD_POSITION_OPEN_PROTECTION")
        self.assertEqual(report["order_count"], 2)
        self.assertEqual(report["equity_curve"][0]["equity"], 10000.0)
        self.assertAlmostEqual(report["return_series"][1]["return"], -0.0075)

    def test_existing_open_target_precedes_later_intrabar_low(self):
        report = run_case([NORMAL, NORMAL, (110.0, 111.0, 96.0, 100.0, 1000.0)],
                          {"1": "BUY"})
        self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL"])
        exit_fill = report["fills"][1]
        self.assertEqual(exit_fill["position_before"], 15.0)
        self.assertEqual(exit_fill["quantity"], 15.0)
        self.assertEqual(exit_fill["price"], 108.0)
        self.assertEqual(exit_fill["fill_basis"], "OPEN_TARGET")
        self.assertEqual(report["ambiguous_intrabar_count"], 0)
        self.assertEqual(report["final_equity"], 10120.0)

    def test_open_target_also_cancels_the_older_pending_buy(self):
        report = run_case([NORMAL, NORMAL, (110.0, 111.0, 96.0, 100.0, 1000.0)],
                          {"1": "BUY", "2": "BUY"})
        self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL"])
        self.assertEqual(report["fills"][1]["quantity"], 15.0)
        self.assertEqual(report["fills"][1]["price"], 108.0)
        self.assertEqual(report["ambiguous_intrabar_count"], 0)
        self.assertEqual(report["signals"][1]["execution_disposition"], "CANCELLED_OLD_POSITION_OPEN_PROTECTION")

    def test_exact_opening_thresholds_trigger_existing_protection(self):
        for price, basis in ((97.0, "GAP_OPEN"), (108.0, "OPEN_TARGET")):
            with self.subTest(opening_price=price):
                report = run_case([NORMAL, NORMAL, (price, price + 1, price - 1, price, 1000.0)],
                                  {"1": "BUY", "2": "BUY"})
                self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL"])
                self.assertEqual(report["fills"][1]["price"], price)
                self.assertEqual(report["fills"][1]["fill_basis"], basis)
                self.assertEqual(report["ambiguous_intrabar_count"], 0)

    def test_unordered_intrabar_double_hit_remains_conservative(self):
        for rows in ([NORMAL, (100.0, 109.0, 96.0, 100.0, 1000.0)],
                     [NORMAL, NORMAL, (100.0, 109.0, 96.0, 100.0, 1000.0)]):
            with self.subTest(position_already_carried=len(rows) == 3):
                report = run_case(rows, {"1": "BUY"})
                self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL"])
                self.assertEqual(report["fills"][1]["price"], 97.0)
                self.assertEqual(report["fills"][1]["fill_basis"], "INTRABAR_STOP")
                self.assertEqual(report["ambiguous_intrabar_count"], 1)

    def test_first_entry_has_no_preexisting_protection_at_the_seed_price(self):
        report = run_case([NORMAL, (95.0, 96.0, 94.8, 95.0, 1000.0)], {"1": "BUY"})
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(report["fills"][0]["position_before"], 0.0)
        self.assertEqual(report["fills"][0]["price"], 95.0)
        self.assertAlmostEqual(report["open_position_qty"], 1500.0 / 95.0)
        self.assertEqual(report["final_equity"], 10000.0)

    def test_no_open_trigger_allows_addition_before_later_intrabar_stop(self):
        report = run_case([NORMAL, NORMAL, (98.0, 99.0, 94.8, 96.0, 1000.0)],
                          {"1": "BUY", "2": "BUY"})
        added_quantity = (8500.0 + 15.0 * 98.0) * 0.15 / 98.0
        combined_quantity = 15.0 + added_quantity
        combined_cost = (1500.0 + added_quantity * 98.0) / combined_quantity
        self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "BUY", "SELL"])
        self.assertAlmostEqual(report["fills"][1]["quantity"], added_quantity)
        self.assertAlmostEqual(report["fills"][2]["quantity"], combined_quantity)
        self.assertAlmostEqual(report["fills"][2]["price"], combined_cost * 0.97)
        self.assertEqual(report["fills"][2]["fill_basis"], "INTRABAR_STOP")
        self.assertEqual(report["ambiguous_intrabar_count"], 0)

    def test_ordinary_partial_exit_then_intrabar_protection_preserves_fees(self):
        report = run_case([NORMAL, NORMAL, (100.0, 101.0, 96.0, 100.0, 1000.0)],
                          {"1": "BUY", "2": "HALF"}, fee=0.001)
        entry, ordinary, protected = report["fills"]
        self.assertEqual([entry["quantity"], ordinary["quantity"], protected["quantity"]], [15.0, 7.5, 7.5])
        self.assertEqual(ordinary["fill_basis"], "NEXT_BAR_OPEN")
        self.assertEqual(protected["fill_basis"], "INTRABAR_STOP")
        self.assertEqual(protected["position_before"], 7.5)
        self.assertEqual(protected["price"], 97.0)
        self.assertAlmostEqual(report["total_fees"], 1.5 + 0.75 + 0.7275)
        self.assertAlmostEqual(report["final_equity"], 9974.5225)
        self.assertEqual(report["round_trip_count"], 1)
        self.assertEqual(report["open_position_qty"], 0.0)
        self.assertAlmostEqual(report["pnl_reconciliation_error"], 0.0)

    def test_partial_open_exit_uses_old_quantity_and_shared_capacity_then_retries_next_bar(self):
        report = run_case([NORMAL, NORMAL, (95.0, 96.0, 94.8, 95.0, 50.0),
                           (94.0, 95.0, 93.0, 94.0, 100.0)],
                          {"1": "BUY", "2": "BUY", "3": "BUY"}, capacity=0.1)
        self.assertEqual([fill["action"] for fill in report["fills"]], ["BUY", "SELL", "SELL"])
        first_exit, final_exit = report["fills"][1:]
        self.assertEqual(first_exit["requested_quantity"], 15.0)
        self.assertEqual(first_exit["quantity"], 5.0)
        self.assertEqual(first_exit["position_after"], 10.0)
        self.assertTrue(first_exit["partial_fill"])
        self.assertEqual(first_exit["capacity_remaining_quantity"], 0.0)
        self.assertEqual(final_exit["position_before"], 10.0)
        self.assertEqual(final_exit["quantity"], 10.0)
        self.assertEqual(final_exit["price"], 94.0)
        self.assertEqual(report["order_count"], 3)
        self.assertEqual(report["orders"][1]["cancelled_quantity"], 10.0)
        self.assertEqual(report["round_trip_count"], 1)
        self.assertEqual(report["final_equity"], 9915.0)
        self.assertAlmostEqual(report["pnl_reconciliation_error"], 0.0)

    def test_rejected_open_exit_still_cancels_pending_signal_without_extra_attempt(self):
        report = run_case([NORMAL, NORMAL, (95.0, 110.0, 94.0, 100.0, 0.0)],
                          {"1": "BUY", "2": "BUY"}, capacity=0.1)
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(report["order_count"], 2)
        self.assertEqual(report["orders"][1]["action"], "SELL")
        self.assertEqual(report["orders"][1]["requested_quantity"], 15.0)
        self.assertEqual(report["orders"][1]["admission_reason"], "VOLUME_CAPACITY_UNAVAILABLE")
        self.assertEqual(report["open_position_qty"], 15.0)
        self.assertEqual(report["ambiguous_intrabar_count"], 0)
        self.assertEqual(report["signals"][1]["execution_disposition"], "CANCELLED_OLD_POSITION_OPEN_PROTECTION")

    def test_reentry_requires_a_fresh_close_signal_for_a_later_bar(self):
        report = run_case([NORMAL, NORMAL, (95.0, 96.0, 94.8, 95.0, 1000.0), NORMAL],
                          {"1": "BUY", "2": "BUY", "3": "BUY"})
        entry, exit_fill, reentry = report["fills"]
        self.assertEqual([entry["action"], exit_fill["action"], reentry["action"]], ["BUY", "SELL", "BUY"])
        self.assertNotEqual(exit_fill["fill_time"], reentry["fill_time"])
        self.assertEqual(reentry["signal_time"], exit_fill["fill_time"])
        self.assertEqual(reentry["position_before"], 0.0)
        self.assertAlmostEqual(reentry["quantity"], 9925.0 * 0.15 / 100.0)
        self.assertIn("FRESH_CLOSE_SIGNAL", report["risk_semantics"]["same_bar_reentry_policy"])


if __name__ == "__main__":
    unittest.main()
