from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import DualMovingAverageStrategy


class DualMaParameterDomainV1Tests(unittest.TestCase):
    @staticmethod
    def strategy(fast: object, slow: object) -> DualMovingAverageStrategy:
        return DualMovingAverageStrategy(
            params={
                "fast_window": fast,
                "slow_window": slow,
                "position_pct": 0.2,
            }
        )

    @staticmethod
    def bearish_crossover_frame() -> pd.DataFrame:
        prices = [100.0 + index for index in range(100)]
        prices += [198.0 - 2.0 * index for index in range(1, 21)]
        return pd.DataFrame({"close": pd.Series(prices, dtype="float64")})

    @classmethod
    def bullish_crossover_frame(cls) -> pd.DataFrame:
        bearish = cls.bearish_crossover_frame()["close"]
        return pd.DataFrame({"close": 300.0 - bearish})

    def test_reversed_and_equal_windows_are_rejected_without_portfolio_mutation(self) -> None:
        data = self.bearish_crossover_frame()
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=150.0)
        before = Portfolio(**portfolio.__dict__)

        for fast, slow in ((60, 20), (20, 20)):
            with self.subTest(fast=fast, slow=slow):
                with self.assertRaisesRegex(ValueError, "fast_window < slow_window"):
                    self.strategy(fast, slow).generate_signal(data, portfolio)

        self.assertEqual(portfolio, before)

    def test_non_positive_fractional_boolean_and_malformed_windows_are_rejected(self) -> None:
        cases = (
            (0, 60),
            (-1, 60),
            (1.5, 60),
            (True, 60),
            (20, 0),
            (20, 60.5),
            (20, False),
            (float("nan"), 60),
            (20, float("inf")),
            ("bad", 60),
            (20, None),
        )
        data = self.bearish_crossover_frame()
        for fast, slow in cases:
            with self.subTest(fast=fast, slow=slow):
                with self.assertRaisesRegex(ValueError, "positive integers"):
                    self.strategy(fast, slow).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_windows_are_rejected_before_valid_warmup_hold(self) -> None:
        short_data = pd.DataFrame(
            {"close": pd.Series([100.0] * 10, dtype="float64")}
        )

        with self.assertRaisesRegex(ValueError, "fast_window < slow_window"):
            self.strategy(60, 20).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid = self.strategy(20, 60).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "not enough data")

    def test_valid_windows_preserve_bearish_full_exit(self) -> None:
        signal = self.strategy(20, 60).generate_signal(
            self.bearish_crossover_frame(),
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=150.0),
        )

        self.assertEqual(signal.action, Action.EXIT)
        self.assertIn("crossed below", signal.reason)

    def test_valid_numeric_string_windows_preserve_bullish_entry(self) -> None:
        signal = self.strategy("20", "60").generate_signal(
            self.bullish_crossover_frame(),
            Portfolio(cash=1_000.0),
        )

        self.assertEqual(signal.action, Action.BUY)
        self.assertIn("crossed above", signal.reason)


if __name__ == "__main__":
    unittest.main()
