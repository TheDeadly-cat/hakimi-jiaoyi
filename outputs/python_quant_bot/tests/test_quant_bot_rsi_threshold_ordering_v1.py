from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import RsiStrategy


class RsiThresholdOrderingV1Tests(unittest.TestCase):
    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    @staticmethod
    def strategy(oversold: object, overbought: object) -> RsiStrategy:
        return RsiStrategy(
            params={
                "window": 14,
                "oversold": oversold,
                "overbought": overbought,
                "position_pct": 0.2,
            }
        )

    def test_crossed_thresholds_are_rejected_without_mutating_portfolio(self) -> None:
        data = self.frame([100.0] * 30)
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0)
        before = Portfolio(**portfolio.__dict__)

        with self.assertRaisesRegex(ValueError, "0 <= oversold < overbought <= 100"):
            self.strategy(80.0, 20.0).generate_signal(data, portfolio)

        self.assertEqual(portfolio, before)

    def test_out_of_range_and_equal_thresholds_are_rejected(self) -> None:
        cases = (
            (-1.0, 70.0),
            (30.0, 101.0),
            (30.0, 30.0),
            (100.0, 100.0),
            (120.0, 130.0),
        )
        data = self.frame([100.0] * 30)
        for oversold, overbought in cases:
            with self.subTest(oversold=oversold, overbought=overbought):
                with self.assertRaisesRegex(ValueError, "0 <= oversold < overbought <= 100"):
                    self.strategy(oversold, overbought).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_non_finite_boolean_and_non_numeric_thresholds_are_rejected(self) -> None:
        cases = (
            (float("nan"), 70.0),
            (30.0, float("inf")),
            (True, 70.0),
            (30.0, False),
            ("bad", 70.0),
            (30.0, None),
        )
        data = self.frame([100.0] * 30)
        for oversold, overbought in cases:
            with self.subTest(oversold=oversold, overbought=overbought):
                with self.assertRaisesRegex(ValueError, "0 <= oversold < overbought <= 100"):
                    self.strategy(oversold, overbought).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_thresholds_are_rejected_before_warmup_hold(self) -> None:
        short_data = self.frame([100.0] * 5)

        with self.assertRaisesRegex(ValueError, "0 <= oversold < overbought <= 100"):
            self.strategy(80.0, 20.0).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid_signal = self.strategy(30.0, 70.0).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid_signal.action, Action.HOLD)
        self.assertEqual(valid_signal.reason, "not enough data")

    def test_valid_thresholds_preserve_neutral_entry_and_exit_semantics(self) -> None:
        strategy = self.strategy("30", "70")
        flat_data = self.frame([100.0] * 30)
        falling_data = self.frame([float(value) for value in range(30, 0, -1)])
        rising_data = self.frame([float(value) for value in range(1, 31)])

        neutral = strategy.generate_signal(flat_data, Portfolio(cash=1_000.0))
        entry = strategy.generate_signal(falling_data, Portfolio(cash=1_000.0))
        exit_signal = strategy.generate_signal(
            rising_data,
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=10.0),
        )

        self.assertEqual(neutral.action, Action.HOLD)
        self.assertEqual(entry.action, Action.BUY)
        self.assertEqual(exit_signal.action, Action.EXIT)


if __name__ == "__main__":
    unittest.main()
