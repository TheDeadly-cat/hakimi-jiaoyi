from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

import pandas as pd

from exchange_terminal.domain import contracts
from quant_bot import engine as engine_module
from quant_bot.engine import TradingEngine
from quant_bot.models import Action, Fill, Order, Signal


class _SyntheticDataProvider:
    def __init__(self) -> None:
        self.frame = pd.DataFrame(
            [{"close": 100.0}],
            index=[pd.Timestamp("2026-08-25T00:00:00Z")],
        )

    def get_latest(self, symbol: str, timeframe: str, lookback: int):
        return self.frame.copy(deep=True)


class _SyntheticStrategy:
    name = "Synthetic Strategy"
    version = "reservation-v1"

    def __init__(self, signal: Signal | None = None) -> None:
        self.signal = signal or Signal.buy(
            "synthetic reservation",
            size_pct=0.1,
        )

    def generate_signal(self, data, portfolio):
        return self.signal


class _SyntheticRiskManager:
    def reset_day(self, equity: float) -> None:
        return None

    def enforce_stop_rules(
        self,
        symbol,
        portfolio,
        price,
        stop_loss,
        take_profit,
    ):
        return None

    def signal_to_order(
        self,
        symbol,
        signal,
        portfolio,
        price,
        *,
        fee_rate,
        slippage_pct,
    ):
        if signal.action == Action.HOLD:
            return None
        return Order(
            symbol=symbol,
            action=signal.action,
            quantity=1.0,
            price=price,
            reason=signal.reason,
        )

    def effective_stop_loss(self, value):
        return value


class _SyntheticBroker:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.before_submit = None

    def submit_order(self, order, portfolio):
        self.calls += 1
        if self.before_submit is not None:
            self.before_submit(order)
        if self.fail:
            raise TimeoutError("synthetic ambiguous broker outcome")
        return Fill(
            symbol=order.symbol,
            action=order.action,
            quantity=order.quantity,
            price=order.price,
            fee=0.0,
            pnl=0.0,
            reason=order.reason,
        )


class TradingEngineDecisionReservationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        config = SimpleNamespace(
            initial_cash=10_000.0,
            name="synthetic-engine",
            symbol="TEST-USDT",
            timeframe="1h",
            mode="research_only",
            logging=SimpleNamespace(
                log_dir=str(Path(self.temporary.name) / "logs")
            ),
            data=SimpleNamespace(history_limit=20),
            execution=SimpleNamespace(
                fee_rate=0.0,
                slippage_pct=0.0,
                poll_seconds=1,
            ),
        )
        self.broker = _SyntheticBroker()
        self.engine = TradingEngine(
            config,
            _SyntheticDataProvider(),
            _SyntheticStrategy(),
            _SyntheticRiskManager(),
            self.broker,
        )

    def test_engine_uses_the_canonical_domain_decision_id(self) -> None:
        self.assertIs(
            engine_module.build_candle_decision_id,
            contracts.build_candle_decision_id,
        )
        self.assertEqual(
            engine_module.build_candle_decision_id(
                strategy=" My Strategy ",
                symbol=" BTC-USDT ",
                timeframe=" 1H ",
                candle_close_time="close",
                action="buy",
                strategy_version="v2",
            ),
            (
                "strategy:my strategy|symbol:btc-usdt|timeframe:1h|"
                "candle:close|action:BUY|version:v2"
            ),
        )

    def test_reservation_is_persisted_before_broker_submission(self) -> None:
        persist = Mock()
        self.engine._persist_decision_state = persist

        def assert_reserved(order) -> None:
            self.assertEqual(persist.call_count, 1)
            reservation = self.engine._decision_state.get(
                self.engine._decision_scope
            )
            self.assertIsInstance(reservation, str)
            self.assertIn("|action:BUY|", reservation)

        self.broker.before_submit = assert_reserved
        self.engine.run_once()
        self.assertEqual(self.broker.calls, 1)
        persist.assert_called_once_with()

    def test_persistence_failure_blocks_broker_and_restores_memory(self) -> None:
        self.engine._persist_decision_state = Mock(
            side_effect=OSError("synthetic persistence failure")
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "failed to reserve candle decision",
        ):
            self.engine.run_once()
        self.assertEqual(self.broker.calls, 0)
        self.assertNotIn(
            self.engine._decision_scope,
            self.engine._decision_state,
        )

    def test_persistence_failure_restores_a_previous_scope_value(self) -> None:
        previous = "old-bar:old-decision"
        self.engine._decision_state[self.engine._decision_scope] = previous
        self.engine._persist_decision_state = Mock(
            side_effect=OSError("synthetic persistence failure")
        )
        with self.assertRaises(RuntimeError):
            self.engine._reserve_decision("new-bar", "new-decision")
        self.assertEqual(
            self.engine._decision_state[self.engine._decision_scope],
            previous,
        )

    def test_ambiguous_broker_failure_retains_reservation_and_blocks_retry(
        self,
    ) -> None:
        self.engine._persist_decision_state = Mock()
        self.broker.fail = True
        with self.assertRaisesRegex(
            TimeoutError,
            "synthetic ambiguous broker outcome",
        ):
            self.engine.run_once()
        reservation = self.engine._decision_state.get(
            self.engine._decision_scope
        )
        self.assertIsInstance(reservation, str)
        self.assertEqual(self.broker.calls, 1)

        self.broker.fail = False
        self.engine.run_once()
        self.assertEqual(self.broker.calls, 1)
        self.assertEqual(
            self.engine._decision_state[self.engine._decision_scope],
            reservation,
        )

    def test_hold_signal_does_not_reserve_or_submit(self) -> None:
        self.engine.strategy = _SyntheticStrategy(Signal.hold())
        persist = Mock()
        self.engine._persist_decision_state = persist
        self.engine.run_once()
        persist.assert_not_called()
        self.assertEqual(self.broker.calls, 0)
        self.assertEqual(self.engine._decision_state, {})


if __name__ == "__main__":
    unittest.main()
