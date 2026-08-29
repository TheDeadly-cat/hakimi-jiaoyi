from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import BollingerBandStrategy


class BollingerParameterDomainV1Tests(unittest.TestCase):
    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    @staticmethod
    def strategy(window: object, std_mult: object) -> BollingerBandStrategy:
        return BollingerBandStrategy(
            params={
                "window": window,
                "std_mult": std_mult,
                "position_pct": 0.2,
            }
        )

    def test_negative_multiplier_is_rejected_without_mutating_portfolio(self) -> None:
        data = self.frame(([90.0, 110.0] * 15) + [100.0])
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0)
        before = Portfolio(**portfolio.__dict__)

        with self.assertRaisesRegex(ValueError, "finite positive std_mult"):
            self.strategy(20, -2.0).generate_signal(data, portfolio)

        self.assertEqual(portfolio, before)

    def test_non_positive_non_finite_and_malformed_multipliers_are_rejected(self) -> None:
        multipliers = (
            0.0,
            -2.0,
            float("nan"),
            float("inf"),
            float("-inf"),
            True,
            "bad",
            None,
        )
        data = self.frame([100.0] * 30)
        for std_mult in multipliers:
            with self.subTest(std_mult=std_mult):
                with self.assertRaisesRegex(ValueError, "finite positive std_mult"):
                    self.strategy(20, std_mult).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_small_non_positive_fractional_and_malformed_windows_are_rejected(self) -> None:
        windows = (
            1,
            0,
            -1,
            2.5,
            True,
            float("nan"),
            float("inf"),
            "bad",
            None,
        )
        data = self.frame([100.0] * 30)
        for window in windows:
            with self.subTest(window=window):
                with self.assertRaisesRegex(ValueError, "integer window >= 2"):
                    self.strategy(window, 2.0).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_parameters_are_rejected_before_warmup_hold(self) -> None:
        short_data = self.frame([100.0] * 5)

        with self.assertRaisesRegex(ValueError, "finite positive std_mult"):
            self.strategy(20, -2.0).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid = self.strategy(20, 2.0).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "not enough data")

    def test_valid_numeric_strings_keep_neutral_prices_inside_bands(self) -> None:
        data = self.frame(([90.0, 110.0] * 15) + [100.0])

        signal = self.strategy("20", "2.0").generate_signal(
            data,
            Portfolio(cash=1_000.0),
        )

        self.assertEqual(signal.action, Action.HOLD)
        self.assertEqual(signal.reason, "inside Bollinger bands")

    def test_valid_lower_entry_and_upper_exit_semantics_are_preserved(self) -> None:
        lower_break = self.frame([100.0] * 24 + [50.0])
        upper_break = self.frame([100.0] * 24 + [200.0])
        strategy = self.strategy(20, 2.0)

        entry = strategy.generate_signal(lower_break, Portfolio(cash=1_000.0))
        exit_signal = strategy.generate_signal(
            upper_break,
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0),
        )

        self.assertEqual(entry.action, Action.BUY)
        self.assertEqual(exit_signal.action, Action.EXIT)


if __name__ == "__main__":
    unittest.main()
