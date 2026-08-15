from __future__ import annotations

import logging
import time

from quant_bot.config import BotConfig
from quant_bot.data import MarketDataProvider
from quant_bot.execution import BrokerBase
from quant_bot.models import Action, Portfolio
from quant_bot.risk import RiskManager
from quant_bot.strategies.base import StrategyBase

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, config: BotConfig, data_provider: MarketDataProvider, strategy: StrategyBase, risk_manager: RiskManager, broker: BrokerBase):
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.risk = risk_manager
        self.broker = broker
        self.portfolio = Portfolio(cash=config.initial_cash)
        self.active_stop_loss: float | None = None
        self.active_take_profit: float | None = None
        self.last_price: float | None = None
        self._risk_session = ""
        self._last_equity = float(config.initial_cash)

    def run_once(self) -> None:
        data = self.data_provider.get_latest(self.config.symbol, self.config.timeframe, self.config.data.history_limit)
        price = float(data["close"].iloc[-1])
        self.last_price = price
        session = str(data.index[-1])[:10] if len(data.index) else "UNSPECIFIED"
        if session != self._risk_session:
            self.risk.reset_day(self._last_equity)
            self._risk_session = session
        forced_order = self.risk.enforce_stop_rules(self.config.symbol, self.portfolio, price, self.active_stop_loss, self.active_take_profit)
        if forced_order is not None:
            fill = self.broker.submit_order(forced_order, self.portfolio)
            logger.info("risk fill=%s equity=%.2f", fill, self.portfolio.equity(price))
            if self.portfolio.position_qty <= 0:
                self.active_stop_loss = None
                self.active_take_profit = None
            self._last_equity = self.portfolio.equity(price)
            return

        signal = self.strategy.generate_signal(data, self.portfolio)
        order = self.risk.signal_to_order(
            self.config.symbol,
            signal,
            self.portfolio,
            price,
            fee_rate=self.config.execution.fee_rate,
            slippage_pct=self.config.execution.slippage_pct,
        )
        logger.info("signal=%s reason=%s price=%.4f equity=%.2f", signal.action, signal.reason, price, self.portfolio.equity(price))
        if order:
            fill = self.broker.submit_order(order, self.portfolio)
            logger.info("fill=%s equity=%.2f", fill, self.portfolio.equity(price))
            if order.action == Action.BUY:
                self.active_stop_loss = self.risk.effective_stop_loss(signal.stop_loss_pct)
                self.active_take_profit = signal.take_profit_pct
            elif self.portfolio.position_qty <= 0:
                self.active_stop_loss = None
                self.active_take_profit = None
        self._last_equity = self.portfolio.equity(price)

    def run(self, cycles: int | None = None) -> None:
        count = 0
        logger.info("Trading engine started: mode=%s strategy=%s symbol=%s", self.config.mode, self.strategy.name, self.config.symbol)
        while cycles is None or count < cycles:
            try:
                self.run_once()
            except Exception:
                logger.exception("engine cycle failed")
            count += 1
            if cycles is not None and count >= cycles:
                break
            time.sleep(max(1, self.config.execution.poll_seconds))
