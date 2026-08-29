from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import MacdStrategy


class MacdParameterDomainV1Tests(unittest.TestCase):
    @staticmethod
    def strategy(fast: object, slow: object, signal: object) -> MacdStrategy:
        return MacdStrategy(
            params={
                "fast": fast,
                "slow": slow,
                "signal": signal,
                "position_pct": 0.2,
            }
        )

    @staticmethod
    def bearish_crossover_frame() -> pd.DataFrame:
        prices = [100.0 + index for index in range(100)] + [196.0]
        return pd.DataFrame({"close": pd.Series(prices, dtype="float64")})

    @classmethod
    def bullish_crossover_frame(cls) -> pd.DataFrame:
        bearish = cls.bearish_crossover_frame()["close"]
        return pd.DataFrame({"close": 300.0 - bearish})

    def test_reversed_and_equal_periods_are_rejected_without_portfolio_mutation(self) -> None:
        data = self.bearish_crossover_frame()
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=150.0)
        before = Portfolio(**portfolio.__dict__)

        for fast, slow in ((26, 12), (12, 12)):
            with self.subTest(fast=fast, slow=slow):
                with self.assertRaisesRegex(ValueError, "fast < slow"):
                    self.strategy(fast, slow, 9).generate_signal(data, portfolio)

        self.assertEqual(portfolio, before)

    def test_non_positive_fractional_boolean_and_malformed_fast_slow_are_rejected(self) -> None:
        cases = (
            (0, 26),
            (-1, 26),
            (1.5, 26),
            (True, 26),
            (12, 0),
            (12, 26.5),
            (12, False),
            (float("nan"), 26),
            (12, float("inf")),
            ("bad", 26),
            (12, None),
        )
        data = self.bearish_crossover_frame()
        for fast, slow in cases:
            with self.subTest(fast=fast, slow=slow):
                with self.assertRaisesRegex(ValueError, "positive integers"):
                    self.strategy(fast, slow, 9).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_signal_periods_are_rejected(self) -> None:
        signal_periods = (
            0,
            -1,
            1.5,
            True,
            float("nan"),
            float("inf"),
            "bad",
            None,
        )
        data = self.bearish_crossover_frame()
        for signal_period in signal_periods:
            with self.subTest(signal=signal_period):
                with self.assertRaisesRegex(ValueError, "signal >= 1"):
                    self.strategy(12, 26, signal_period).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_periods_are_rejected_before_valid_warmup_hold(self) -> None:
        short_data = pd.DataFrame(
            {"close": pd.Series([100.0] * 10, dtype="float64")}
        )

        with self.assertRaisesRegex(ValueError, "fast < slow"):
            self.strategy(26, 12, 9).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid = self.strategy(12, 26, 9).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "not enough data")

    def test_valid_periods_preserve_bearish_full_exit(self) -> None:
        signal = self.strategy(12, 26, 9).generate_signal(
            self.bearish_crossover_frame(),
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=150.0),
        )

        self.assertEqual(signal.action, Action.EXIT)
        self.assertIn("bearish crossover", signal.reason)

    def test_valid_numeric_string_periods_preserve_bullish_entry(self) -> None:
        signal = self.strategy("12", "26", "9").generate_signal(
            self.bullish_crossover_frame(),
            Portfolio(cash=1_000.0),
        )

        self.assertEqual(signal.action, Action.BUY)
        self.assertIn("bullish crossover", signal.reason)


if __name__ == "__main__":
    unittest.main()
