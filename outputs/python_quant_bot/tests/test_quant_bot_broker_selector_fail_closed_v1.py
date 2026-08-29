from __future__ import annotations

import unittest

from quant_bot.config import BotConfig
from quant_bot.execution import PaperBroker, build_broker


class BrokerSelectorFailClosedV1Tests(unittest.TestCase):
    @staticmethod
    def config(
        *,
        mode: object = "paper",
        broker: object = "paper",
        live_trading_enabled: object = False,
    ) -> BotConfig:
        config = BotConfig()
        config.mode = mode  # type: ignore[assignment]
        config.execution.broker = broker  # type: ignore[assignment]
        config.execution.live_trading_enabled = live_trading_enabled  # type: ignore[assignment]
        config.execution.fee_rate = 0.0123
        config.execution.slippage_pct = 0.0045
        return config

    def test_registered_local_selectors_build_only_paper_broker(self) -> None:
        for mode in ("paper", "backtest", "PAPER", "BACKTEST"):
            with self.subTest(mode=mode):
                broker = build_broker(self.config(mode=mode))
                self.assertIsInstance(broker, PaperBroker)
                self.assertEqual(broker.fee_rate, 0.0123)
                self.assertEqual(broker.slippage_pct, 0.0045)

    def test_unknown_broker_cannot_fall_back_to_paper(self) -> None:
        for broker_name in ("papre", "alpaca", "synthetic"):
            with self.subTest(broker=broker_name):
                with self.assertRaisesRegex(ValueError, "Unsupported execution broker"):
                    build_broker(self.config(broker=broker_name))

    def test_unknown_mode_cannot_fall_back_to_paper(self) -> None:
        for mode in ("staging", "research", "simulation"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "Unsupported execution mode"):
                    build_broker(self.config(mode=mode))

    def test_every_explicit_live_indicator_hits_the_permanent_hard_wall(self) -> None:
        cases = (
            ("live", "paper", False),
            ("LIVE", "paper", False),
            ("paper", "ccxt", False),
            ("paper", "CCXT", False),
            ("paper", "paper", True),
            ("backtest", "paper", True),
        )
        for mode, broker_name, enabled in cases:
            with self.subTest(mode=mode, broker=broker_name, enabled=enabled):
                with self.assertRaisesRegex(RuntimeError, "Live trading hard wall"):
                    build_broker(
                        self.config(
                            mode=mode,
                            broker=broker_name,
                            live_trading_enabled=enabled,
                        )
                    )

    def test_malformed_selector_types_are_rejected(self) -> None:
        cases = (
            (None, "paper", "mode must be a non-empty string"),
            (1, "paper", "mode must be a non-empty string"),
            ("paper", None, "broker must be a non-empty string"),
            ("paper", 1, "broker must be a non-empty string"),
        )
        for mode, broker_name, message in cases:
            with self.subTest(mode=mode, broker=broker_name):
                with self.assertRaisesRegex(ValueError, message):
                    build_broker(self.config(mode=mode, broker=broker_name))

    def test_non_boolean_live_flag_is_rejected(self) -> None:
        for enabled in (None, 0, 1, "false"):
            with self.subTest(enabled=enabled):
                with self.assertRaisesRegex(ValueError, "live_trading_enabled must be boolean"):
                    build_broker(self.config(live_trading_enabled=enabled))

    def test_surrounding_whitespace_is_not_silently_normalized(self) -> None:
        cases = ((" paper", "paper", "mode"), ("paper", "paper ", "broker"))
        for mode, broker_name, field_name in cases:
            with self.subTest(mode=mode, broker=broker_name):
                with self.assertRaisesRegex(ValueError, f"{field_name} must not contain surrounding whitespace"):
                    build_broker(self.config(mode=mode, broker=broker_name))


if __name__ == "__main__":
    unittest.main()
