from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from quant_bot.config import BotConfig
from quant_bot.models import Action, Fill, Order, Portfolio

logger = logging.getLogger(__name__)
LIVE_TRADING_HARD_BLOCK = True
_LOCAL_EXECUTION_MODES = frozenset({"paper", "backtest"})
_LOCAL_EXECUTION_BROKERS = frozenset({"paper"})


class BrokerBase:
    def submit_order(self, order: Order, portfolio: Portfolio) -> Fill:
        raise NotImplementedError


@dataclass
class PaperBroker(BrokerBase):
    fee_rate: float = 0.0008
    slippage_pct: float = 0.0005

    def submit_order(self, order: Order, portfolio: Portfolio) -> Fill:
        if order.action not in {Action.BUY, Action.SELL}:
            raise ValueError("PaperBroker only accepts BUY and SELL orders.")
        numeric = {
            "fee_rate": self.fee_rate,
            "slippage_pct": self.slippage_pct,
            "order_price": order.price,
            "order_quantity": order.quantity,
            "portfolio_cash": portfolio.cash,
            "portfolio_position_qty": portfolio.position_qty,
            "portfolio_avg_entry_price": portfolio.avg_entry_price,
            "portfolio_realized_pnl": portfolio.realized_pnl,
            "portfolio_entry_fees": portfolio.entry_fees,
        }
        try:
            parsed = {name: float(value) for name, value in numeric.items()}
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("PaperBroker requires numeric order, account, fee, and slippage values.") from exc
        if any(not math.isfinite(value) for value in parsed.values()):
            raise ValueError("PaperBroker requires finite order, account, fee, and slippage values.")
        fee_rate = parsed["fee_rate"]
        slippage_pct = parsed["slippage_pct"]
        order_price = parsed["order_price"]
        order_quantity = parsed["order_quantity"]
        cash = parsed["portfolio_cash"]
        position_qty = parsed["portfolio_position_qty"]
        avg_entry_price = parsed["portfolio_avg_entry_price"]
        realized_pnl = parsed["portfolio_realized_pnl"]
        entry_fees = parsed["portfolio_entry_fees"]
        if not 0 <= fee_rate < 1 or not 0 <= slippage_pct < 1:
            raise ValueError("PaperBroker fee and slippage must be in [0, 1).")
        if (
            order_price <= 0
            or order_quantity <= 0
            or cash < 0
            or position_qty < 0
            or avg_entry_price < 0
            or entry_fees < 0
        ):
            raise ValueError("PaperBroker received an invalid order or account state.")
        fill_price = order_price * (1 + slippage_pct if order.action == Action.BUY else 1 - slippage_pct)
        if not math.isfinite(fill_price) or fill_price <= 0:
            raise ValueError("PaperBroker execution price is invalid.")
        pnl = 0.0
        filled_quantity = order_quantity
        if order.action == Action.BUY:
            all_in_unit_cost = fill_price * (1 + fee_rate)
            if not math.isfinite(all_in_unit_cost) or all_in_unit_cost <= 0:
                raise ValueError("PaperBroker derived an invalid all-in unit cost.")
            filled_quantity = min(order_quantity, cash / all_in_unit_cost)
            if filled_quantity <= 0:
                raise ValueError("PaperBroker cannot fill a buy order without available cash.")
            notional = filled_quantity * fill_price
            fee = notional * fee_rate
            new_position_qty = position_qty + filled_quantity
            new_value = position_qty * avg_entry_price + notional
            new_avg_entry_price = new_value / new_position_qty
            new_cash = cash - notional - fee
            new_entry_fees = entry_fees + fee
            prospective = (filled_quantity, notional, fee, new_position_qty, new_avg_entry_price, new_cash, new_entry_fees)
            if any(not math.isfinite(value) for value in prospective) or new_cash < -1e-9:
                raise ValueError("PaperBroker buy fill would create an invalid account state.")
            portfolio.position_qty = new_position_qty
            portfolio.avg_entry_price = new_avg_entry_price
            portfolio.cash = max(0.0, new_cash)
            portfolio.entry_fees = new_entry_fees
        else:
            position_before = position_qty
            filled_quantity = min(order_quantity, position_before)
            if filled_quantity <= 0:
                raise ValueError("PaperBroker cannot fill a sell order without an open position.")
            notional = filled_quantity * fill_price
            fee = notional * fee_rate
            entry_fee_share = entry_fees * filled_quantity / position_before
            pnl = (fill_price - avg_entry_price) * filled_quantity - fee - entry_fee_share
            new_position_qty = position_qty - filled_quantity
            new_entry_fees = max(0.0, entry_fees - entry_fee_share)
            new_cash = cash + notional - fee
            new_realized_pnl = realized_pnl + pnl
            prospective = (
                filled_quantity,
                notional,
                fee,
                entry_fee_share,
                pnl,
                new_position_qty,
                new_entry_fees,
                new_cash,
                new_realized_pnl,
            )
            if any(not math.isfinite(value) for value in prospective) or new_cash < -1e-9:
                raise ValueError("PaperBroker sell fill would create an invalid account state.")
            portfolio.position_qty = max(0.0, new_position_qty)
            portfolio.entry_fees = new_entry_fees
            portfolio.cash = max(0.0, new_cash)
            portfolio.realized_pnl = new_realized_pnl
            if portfolio.position_qty <= 1e-12:
                portfolio.position_qty = 0.0
                portfolio.avg_entry_price = 0.0
                portfolio.entry_fees = 0.0
        fill = Fill(order.symbol, order.action, filled_quantity, fill_price, fee, pnl, order.reason)
        logger.info("PAPER FILL %s", fill)
        return fill


def _canonical_selector(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Execution {field_name} must be a non-empty string.")
    if value != value.strip():
        raise ValueError(f"Execution {field_name} must not contain surrounding whitespace.")
    return value.lower()


def build_broker(config: BotConfig) -> BrokerBase:
    mode = _canonical_selector(config.mode, field_name="mode")
    broker = _canonical_selector(config.execution.broker, field_name="broker")
    live_trading_enabled = config.execution.live_trading_enabled
    if not isinstance(live_trading_enabled, bool):
        raise ValueError("Execution live_trading_enabled must be boolean.")
    if mode == "live" or broker == "ccxt" or live_trading_enabled:
        raise RuntimeError("Live trading hard wall is enabled. Only paper and backtest modes are allowed.")
    if mode not in _LOCAL_EXECUTION_MODES:
        raise ValueError(f"Unsupported execution mode: {config.mode!r}.")
    if broker not in _LOCAL_EXECUTION_BROKERS:
        raise ValueError(f"Unsupported execution broker: {config.execution.broker!r}.")
    return PaperBroker(config.execution.fee_rate, config.execution.slippage_pct)
