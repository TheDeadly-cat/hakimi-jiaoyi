from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import MomentumStrategy


class MomentumParameterDomainV1Tests(unittest.TestCase):
    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    @staticmethod
    def strategy(window: object, threshold: object) -> MomentumStrategy:
        return MomentumStrategy(
            params={
                "window": window,
                "threshold": threshold,
                "position_pct": 0.2,
            }
        )

    def test_negative_threshold_is_rejected_without_mutating_portfolio(self) -> None:
        data = self.frame([100.0] * 30)
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0)
        before = Portfolio(**portfolio.__dict__)

        with self.assertRaisesRegex(ValueError, "positive integer window"):
            self.strategy(20, -0.01).generate_signal(data, portfolio)

        self.assertEqual(portfolio, before)

    def test_non_positive_fractional_and_malformed_windows_are_rejected(self) -> None:
        windows = (0, -1, 1.5, True, float("nan"), float("inf"), "bad", None)
        data = self.frame([100.0] * 30)
        for window in windows:
            with self.subTest(window=window):
                with self.assertRaisesRegex(ValueError, "positive integer window"):
                    self.strategy(window, 0.01).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_non_finite_boolean_and_non_numeric_thresholds_are_rejected(self) -> None:
        thresholds = (
            float("nan"),
            float("inf"),
            float("-inf"),
            -0.01,
            True,
            "bad",
            None,
        )
        data = self.frame([100.0] * 30)
        for threshold in thresholds:
            with self.subTest(threshold=threshold):
                with self.assertRaisesRegex(ValueError, "finite non-negative threshold"):
                    self.strategy(20, threshold).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_parameters_are_rejected_before_warmup_hold(self) -> None:
        short_data = self.frame([100.0] * 5)

        with self.assertRaisesRegex(ValueError, "positive integer window"):
            self.strategy(0, -0.01).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid = self.strategy(20, 0.01).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "not enough data")

    def test_zero_threshold_on_flat_prices_remains_neutral(self) -> None:
        signal = self.strategy(20, 0.0).generate_signal(
            self.frame([100.0] * 30),
            Portfolio(cash=1_000.0),
        )

        self.assertEqual(signal.action, Action.HOLD)
        self.assertEqual(signal.reason, "momentum neutral")

    def test_valid_numeric_strings_preserve_entry_and_exit_semantics(self) -> None:
        strategy = self.strategy("20", "0.05")
        rising = self.frame([float(value) for value in range(1, 31)])
        falling = self.frame([float(value) for value in range(30, 0, -1)])

        entry = strategy.generate_signal(rising, Portfolio(cash=1_000.0))
        exit_signal = strategy.generate_signal(
            falling,
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=20.0),
        )

        self.assertEqual(entry.action, Action.BUY)
        self.assertEqual(exit_signal.action, Action.EXIT)


if __name__ == "__main__":
    unittest.main()
