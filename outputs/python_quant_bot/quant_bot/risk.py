from __future__ import annotations

import logging
import math

from quant_bot.config import RiskConfig
from quant_bot.models import Action, Order, Portfolio, Signal

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config
        self.day_start_equity: float | None = None
        self.trading_halted = False

    def reset_day(self, equity: float) -> None:
        try:
            parsed_equity = float(equity)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Daily risk baseline equity must be a finite non-negative number.") from exc
        if not math.isfinite(parsed_equity) or parsed_equity < 0:
            raise ValueError("Daily risk baseline equity must be a finite non-negative number.")
        self.day_start_equity = parsed_equity
        self.trading_halted = False

    def check_daily_loss(self, equity: float) -> bool:
        try:
            parsed_equity = float(equity)
            max_daily_loss_pct = float(self.config.max_daily_loss_pct)
        except (TypeError, ValueError, OverflowError):
            self.trading_halted = True
            logger.error("Daily risk rejected a non-numeric equity or loss limit.")
            return False
        if (
            not math.isfinite(parsed_equity)
            or parsed_equity < 0
            or not math.isfinite(max_daily_loss_pct)
            or not 0 <= max_daily_loss_pct <= 1
        ):
            self.trading_halted = True
            logger.error("Daily risk rejected an invalid equity or loss limit.")
            return False
        if self.day_start_equity is None:
            self.reset_day(parsed_equity)
            return True
        drawdown = (self.day_start_equity - parsed_equity) / max(self.day_start_equity, 1)
        if drawdown > 0 and drawdown >= max_daily_loss_pct:
            self.trading_halted = True
            logger.warning("Daily loss circuit breaker triggered: %.2f%%", drawdown * 100)
            return False
        return True

    def effective_stop_loss(self, stop_loss_pct: float | None) -> float:
        max_loss = float(self.config.max_single_loss_pct)
        if not math.isfinite(max_loss) or not 0 <= max_loss <= 1:
            raise ValueError("Maximum single-loss percentage must be finite and in [0, 1].")
        if stop_loss_pct is None:
            return max_loss
        parsed_stop = abs(float(stop_loss_pct))
        if not math.isfinite(parsed_stop):
            raise ValueError("Stop-loss percentage must be finite.")
        return min(parsed_stop, max_loss)

    def signal_to_order(
        self,
        symbol: str,
        signal: Signal,
        portfolio: Portfolio,
        price: float,
        *,
        fee_rate: float = 0.0,
        slippage_pct: float = 0.0,
    ) -> Order | None:
        numeric = {
            "price": price,
            "cash": portfolio.cash,
            "position_qty": portfolio.position_qty,
            "signal_size_pct": signal.size_pct,
            "fee_rate": fee_rate,
            "slippage_pct": slippage_pct,
        }
        try:
            parsed = {name: float(value) for name, value in numeric.items()}
            valid_numeric = all(math.isfinite(value) for value in parsed.values())
        except (TypeError, ValueError, OverflowError):
            valid_numeric = False
            parsed = {}
        if (
            not valid_numeric
            or parsed["price"] <= 0
            or parsed["cash"] < 0
            or parsed["position_qty"] < 0
        ):
            logger.error("Risk rejected invalid signal/account numeric contract: %s", numeric)
            return None
        price = parsed["price"]
        cash = parsed["cash"]
        position_qty = parsed["position_qty"]
        size_pct = parsed["signal_size_pct"]
        fee_rate = parsed["fee_rate"]
        slippage_pct = parsed["slippage_pct"]
        if signal.action == Action.HOLD:
            return None

        if signal.action == Action.EXIT:
            if position_qty <= 0:
                return None
            return Order(symbol=symbol, action=Action.SELL, quantity=position_qty, price=price, reason=signal.reason)

        if signal.action == Action.SELL:
            if position_qty <= 0:
                return None
            qty = min(position_qty, position_qty * max(0.0, min(size_pct, 1.0)))
            if qty <= 0:
                return None
            return Order(symbol=symbol, action=Action.SELL, quantity=qty, price=price, reason=signal.reason)

        if signal.action == Action.BUY:
            try:
                max_position_pct = float(self.config.max_position_pct)
                min_cash_pct = float(self.config.min_cash_pct)
            except (TypeError, ValueError, OverflowError):
                logger.error("Risk rejected non-numeric position or cash limits.")
                return None
            if (
                not math.isfinite(max_position_pct)
                or not math.isfinite(min_cash_pct)
                or not 0 <= max_position_pct <= 1
                or not 0 <= min_cash_pct <= 1
                or not 0 <= fee_rate < 1
                or not 0 <= slippage_pct < 1
                or size_pct <= 0
            ):
                logger.error("Risk rejected invalid position, cash, or execution limits.")
                return None
            equity = cash + position_qty * price
            if not math.isfinite(equity) or equity < 0:
                logger.error("Risk rejected a non-finite account equity.")
                return None
            if self.trading_halted or not self.check_daily_loss(equity):
                return None
            max_position_value = equity * max_position_pct
            requested_value = equity * min(size_pct, max_position_pct)
            current_position_value = position_qty * price
            available_value = max(0.0, max_position_value - current_position_value)
            cash_floor = equity * min_cash_pct
            maximum_cash_debit = max(0.0, cash - cash_floor)
            reference_notional = min(requested_value, available_value, maximum_cash_debit)
            execution_price = price * (1.0 + slippage_pct)
            all_in_unit_cost = execution_price * (1.0 + fee_rate)
            quantity = min(
                reference_notional / price,
                maximum_cash_debit / max(all_in_unit_cost, 1e-12),
            )
            if not math.isfinite(quantity) or quantity <= 0:
                return None
            return Order(symbol=symbol, action=Action.BUY, quantity=quantity, price=price, reason=signal.reason)
        return None

    def enforce_stop_rules(self, symbol: str, portfolio: Portfolio, price: float, stop_loss_pct: float | None, take_profit_pct: float | None) -> Order | None:
        if portfolio.position_qty <= 0 or portfolio.avg_entry_price <= 0:
            return None
        pnl_pct = (price - portfolio.avg_entry_price) / portfolio.avg_entry_price
        if stop_loss_pct is not None and pnl_pct <= -abs(stop_loss_pct):
            return Order(symbol, Action.SELL, portfolio.position_qty, price, f"stop loss {pnl_pct:.2%}")
        if take_profit_pct is not None and pnl_pct >= abs(take_profit_pct):
            return Order(symbol, Action.SELL, portfolio.position_qty, price, f"take profit {pnl_pct:.2%}")
        return None
