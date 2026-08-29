from __future__ import annotations

import unittest

import pandas as pd

from quant_bot.indicators import bollinger
from quant_bot.models import Action, Portfolio
from quant_bot.strategies.templates import BollingerBandStrategy


class BollingerExitPrecedenceV1Tests(unittest.TestCase):
    @staticmethod
    def strategy() -> BollingerBandStrategy:
        return BollingerBandStrategy(
            params={"window": 20, "std_mult": 2.0, "position_pct": 0.2}
        )

    @staticmethod
    def open_portfolio() -> Portfolio:
        return Portfolio(cash=1_000.0, position_qty=10.0, avg_entry_price=100.0)

    @staticmethod
    def frame(values: list[float]) -> pd.DataFrame:
        return pd.DataFrame({"close": pd.Series(values, dtype="float64")})

    @staticmethod
    def bands(data: pd.DataFrame) -> tuple[float, float, float, float]:
        upper, middle, lower = bollinger(data["close"], 20, 2.0)
        return (
            float(data["close"].iloc[-1]),
            float(upper.iloc[-1]),
            float(middle.iloc[-1]),
            float(lower.iloc[-1]),
        )

    def test_upper_band_break_has_priority_and_exits_full_position(self) -> None:
        data = self.frame([100.0] * 24 + [200.0])
        price, upper, middle, _lower = self.bands(data)
        portfolio = self.open_portfolio()
        before = Portfolio(**portfolio.__dict__)

        signal = self.strategy().generate_signal(data, portfolio)

        self.assertGreater(price, upper)
        self.assertGreater(upper, middle)
        self.assertEqual(signal.action, Action.EXIT)
        self.assertIn("upper Bollinger band", signal.reason)
        self.assertEqual(portfolio, before)

    def test_midline_reversion_below_upper_remains_partial_sell(self) -> None:
        data = self.frame(([90.0, 110.0] * 12) + [105.0])
        price, upper, middle, _lower = self.bands(data)

        signal = self.strategy().generate_signal(data, self.open_portfolio())

        self.assertGreater(price, middle)
        self.assertLess(price, upper)
        self.assertEqual(signal.action, Action.SELL)
        self.assertEqual(signal.size_pct, 0.2)
        self.assertIn("midline", signal.reason)

    def test_lower_band_entry_semantics_are_unchanged(self) -> None:
        data = self.frame(([90.0, 110.0] * 12) + [70.0])
        price, _upper, _middle, lower = self.bands(data)
        flat = Portfolio(cash=1_000.0, position_qty=0.0, avg_entry_price=0.0)

        signal = self.strategy().generate_signal(data, flat)

        self.assertLess(price, lower)
        self.assertEqual(signal.action, Action.BUY)
        self.assertEqual(signal.size_pct, 0.2)

    def test_upper_band_break_without_position_does_not_emit_sell(self) -> None:
        data = self.frame([100.0] * 24 + [200.0])
        flat = Portfolio(cash=1_000.0, position_qty=0.0, avg_entry_price=0.0)

        signal = self.strategy().generate_signal(data, flat)

        self.assertEqual(signal.action, Action.HOLD)

    def test_warmup_contract_remains_hold(self) -> None:
        data = self.frame([100.0] * 21)

        signal = self.strategy().generate_signal(data, self.open_portfolio())

        self.assertEqual(signal.action, Action.HOLD)
        self.assertEqual(signal.reason, "not enough data")


if __name__ == "__main__":
    unittest.main()
