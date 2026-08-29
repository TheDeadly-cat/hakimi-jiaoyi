from __future__ import annotations

import unittest

from quant_bot.config import RiskConfig
from quant_bot.models import Action, Portfolio
from quant_bot.risk import RiskManager


class ProtectiveExitContractV1Tests(unittest.TestCase):
    @staticmethod
    def manager(max_single_loss_pct: object = 0.03) -> RiskManager:
        config = RiskConfig()
        config.max_single_loss_pct = max_single_loss_pct  # type: ignore[assignment]
        return RiskManager(config)

    @staticmethod
    def open_portfolio(**overrides: object) -> Portfolio:
        values: dict[str, object] = {
            "cash": 1_000.0,
            "position_qty": 2.0,
            "avg_entry_price": 100.0,
        }
        values.update(overrides)
        return Portfolio(**values)  # type: ignore[arg-type]

    def test_configured_single_loss_is_mandatory_when_signal_omits_stop(self) -> None:
        risk = self.manager(0.03)
        portfolio = self.open_portfolio()

        self.assertIsNone(risk.enforce_stop_rules("TEST", portfolio, 98.0, None, None))
        order = risk.enforce_stop_rules("TEST", portfolio, 96.0, None, None)

        self.assertIsNotNone(order)
        assert order is not None
        self.assertEqual(order.action, Action.SELL)
        self.assertEqual(order.quantity, 2.0)
        self.assertEqual(order.price, 96.0)

    def test_wider_signal_stop_cannot_bypass_configured_loss_cap(self) -> None:
        order = self.manager(0.03).enforce_stop_rules(
            "TEST",
            self.open_portfolio(),
            96.0,
            0.50,
            None,
        )

        self.assertIsNotNone(order)
        assert order is not None
        self.assertIn("stop loss", order.reason)

    def test_tighter_signal_stop_remains_effective(self) -> None:
        order = self.manager(0.03).enforce_stop_rules(
            "TEST",
            self.open_portfolio(),
            98.5,
            0.01,
            None,
        )

        self.assertIsNotNone(order)

    def test_invalid_market_price_is_rejected_without_mutating_portfolio(self) -> None:
        risk = self.manager()
        for price in (float("nan"), float("inf"), float("-inf"), 0.0, -1.0, True, "bad"):
            portfolio = self.open_portfolio()
            before = Portfolio(**portfolio.__dict__)
            with self.subTest(price=price):
                with self.assertRaisesRegex(ValueError, "Protective-exit market price"):
                    risk.enforce_stop_rules("TEST", portfolio, price, 0.03, 0.10)  # type: ignore[arg-type]
                self.assertEqual(portfolio, before)

    def test_invalid_open_position_contract_is_rejected(self) -> None:
        cases = (
            {"position_qty": float("nan")},
            {"position_qty": float("inf")},
            {"position_qty": -1.0},
            {"avg_entry_price": float("nan")},
            {"avg_entry_price": float("inf")},
            {"avg_entry_price": 0.0},
            {"avg_entry_price": -1.0},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.manager().enforce_stop_rules(
                        "TEST",
                        self.open_portfolio(**overrides),
                        90.0,
                        0.03,
                        0.10,
                    )

    def test_invalid_stop_and_take_profit_thresholds_are_rejected(self) -> None:
        for stop in (float("nan"), float("inf"), True, "bad"):
            with self.subTest(stop=stop):
                with self.assertRaisesRegex(ValueError, "Stop-loss percentage"):
                    self.manager().enforce_stop_rules(
                        "TEST", self.open_portfolio(), 90.0, stop, None  # type: ignore[arg-type]
                    )
        for take_profit in (float("nan"), float("inf"), True, "bad"):
            with self.subTest(take_profit=take_profit):
                with self.assertRaisesRegex(ValueError, "Take-profit percentage"):
                    self.manager().enforce_stop_rules(
                        "TEST", self.open_portfolio(), 110.0, 0.03, take_profit  # type: ignore[arg-type]
                    )

    def test_invalid_global_single_loss_contract_is_rejected(self) -> None:
        for maximum in (float("nan"), float("inf"), -0.01, 1.01, True, "bad"):
            with self.subTest(maximum=maximum):
                with self.assertRaisesRegex(ValueError, "Maximum single-loss percentage"):
                    self.manager(maximum).enforce_stop_rules(
                        "TEST", self.open_portfolio(), 90.0, 0.03, None
                    )

    def test_valid_take_profit_and_flat_portfolio_semantics_are_preserved(self) -> None:
        risk = self.manager()
        order = risk.enforce_stop_rules("TEST", self.open_portfolio(), 111.0, 0.03, 0.10)
        flat = Portfolio(cash=1_000.0, position_qty=0.0, avg_entry_price=0.0)

        self.assertIsNotNone(order)
        assert order is not None
        self.assertEqual(order.action, Action.SELL)
        self.assertIn("take profit", order.reason)
        self.assertIsNone(risk.enforce_stop_rules("TEST", flat, 100.0, 0.03, 0.10))


if __name__ == "__main__":
    unittest.main()
