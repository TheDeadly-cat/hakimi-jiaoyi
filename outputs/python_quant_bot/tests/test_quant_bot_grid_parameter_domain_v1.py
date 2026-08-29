from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import GridStrategy


class GridParameterDomainV1Tests(unittest.TestCase):
    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    @staticmethod
    def strategy(lookback: object, grids: object) -> GridStrategy:
        return GridStrategy(
            params={
                "lookback": lookback,
                "grids": grids,
                "position_pct": 0.2,
            }
        )

    def test_zero_lookback_is_rejected_instead_of_expanding_to_full_history(self) -> None:
        data = self.frame(([100.0] * 10) + ([50.0] * 20))
        portfolio = Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=100.0)
        before = Portfolio(**portfolio.__dict__)

        with self.assertRaisesRegex(ValueError, "lookback >= 2"):
            self.strategy(0, 8).generate_signal(data, portfolio)

        valid = self.strategy(20, 8).generate_signal(
            data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "flat grid")
        self.assertEqual(portfolio, before)

    def test_small_non_positive_fractional_and_malformed_lookbacks_are_rejected(self) -> None:
        lookbacks = (
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
        for lookback in lookbacks:
            with self.subTest(lookback=lookback):
                with self.assertRaisesRegex(ValueError, "lookback >= 2"):
                    self.strategy(lookback, 8).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_one_sided_non_positive_fractional_and_malformed_grid_counts_are_rejected(self) -> None:
        grid_counts = (
            3,
            2,
            1,
            0,
            -1,
            4.5,
            True,
            float("nan"),
            float("inf"),
            "bad",
            None,
        )
        data = self.frame([100.0] * 30)
        for grids in grid_counts:
            with self.subTest(grids=grids):
                with self.assertRaisesRegex(ValueError, "grids >= 4"):
                    self.strategy(20, grids).generate_signal(
                        data,
                        Portfolio(cash=1_000.0),
                    )

    def test_invalid_parameters_are_rejected_before_valid_warmup_hold(self) -> None:
        short_data = self.frame([100.0] * 5)

        with self.assertRaisesRegex(ValueError, "lookback >= 2"):
            self.strategy(0, 8).generate_signal(
                short_data,
                Portfolio(cash=1_000.0),
            )

        valid = self.strategy(20, 8).generate_signal(
            short_data,
            Portfolio(cash=1_000.0),
        )
        self.assertEqual(valid.action, Action.HOLD)
        self.assertEqual(valid.reason, "not enough data")

    def test_valid_numeric_strings_preserve_lower_grid_entry(self) -> None:
        lower = self.frame(([100.0] * 19) + [50.0])

        signal = self.strategy("20", "8").generate_signal(
            lower,
            Portfolio(cash=1_000.0),
        )

        self.assertEqual(signal.action, Action.BUY)
        self.assertIn("lower grid", signal.reason)

    def test_valid_upper_reduction_and_flat_grid_hold_are_preserved(self) -> None:
        upper = self.frame(([50.0] * 19) + [100.0])
        flat = self.frame([100.0] * 20)
        strategy = self.strategy(20, 8)

        reduction = strategy.generate_signal(
            upper,
            Portfolio(cash=1_000.0, position_qty=1.0, avg_entry_price=50.0),
        )
        neutral = strategy.generate_signal(flat, Portfolio(cash=1_000.0))

        self.assertEqual(reduction.action, Action.SELL)
        self.assertEqual(reduction.size_pct, 0.2)
        self.assertEqual(neutral.action, Action.HOLD)
        self.assertEqual(neutral.reason, "flat grid")


if __name__ == "__main__":
    unittest.main()
