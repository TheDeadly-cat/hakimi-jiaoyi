from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.indicators import rsi
from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import RsiStrategy


class RsiZeroDenominatorSemanticsV1Tests(unittest.TestCase):
    @staticmethod
    def strategy() -> RsiStrategy:
        return RsiStrategy(
            params={"window": 14, "oversold": 30.0, "overbought": 70.0}
        )

    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    def test_monotonic_gain_is_rsi_100_and_open_position_exits(self) -> None:
        data = self.frame([float(value) for value in range(1, 31)])
        open_portfolio = Portfolio(
            cash=1_000.0,
            position_qty=1.0,
            avg_entry_price=10.0,
        )
        flat_portfolio = Portfolio(
            cash=1_000.0,
            position_qty=0.0,
            avg_entry_price=0.0,
        )

        value = rsi(data["close"], 14).iloc[-1]
        open_signal = self.strategy().generate_signal(data, open_portfolio)
        flat_signal = self.strategy().generate_signal(data, flat_portfolio)

        self.assertEqual(value, 100.0)
        self.assertEqual(open_signal.action, Action.EXIT)
        self.assertIn("100.00", open_signal.reason)
        self.assertEqual(flat_signal.action, Action.HOLD)

    def test_flat_window_is_neutral_rsi_50(self) -> None:
        data = self.frame([100.0] * 30)

        value = rsi(data["close"], 14).iloc[-1]
        signal = self.strategy().generate_signal(
            data,
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0),
        )

        self.assertEqual(value, 50.0)
        self.assertEqual(signal.action, Action.HOLD)
        self.assertEqual(signal.reason, "RSI neutral")

    def test_monotonic_loss_remains_rsi_zero(self) -> None:
        close = pd.Series(
            [float(value) for value in range(30, 0, -1)],
            dtype="float64",
        )

        value = rsi(close, 14).iloc[-1]

        self.assertEqual(value, 0.0)

    def test_warmup_rows_remain_unknown(self) -> None:
        close = pd.Series(
            [float(value) for value in range(1, 16)],
            dtype="float64",
        )

        values = rsi(close, 14)

        self.assertTrue(values.iloc[:14].isna().all())
        self.assertEqual(values.iloc[14], 100.0)

    def test_mixed_window_is_bounded_and_input_is_not_mutated(self) -> None:
        close = pd.Series(
            [100.0, 103.0, 101.0, 104.0, 102.0] * 6,
            dtype="float64",
            name="close",
        )
        before = close.copy(deep=True)

        value = rsi(close, 14).iloc[-1]

        self.assertFalse(pd.isna(value))
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 100.0)
        pd.testing.assert_series_equal(close, before)


if __name__ == "__main__":
    unittest.main()
