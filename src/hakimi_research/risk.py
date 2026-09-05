from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from hakimi_research.config import RiskConfig
from hakimi_research.models import Action, Order, Portfolio, Signal

logger = logging.getLogger(__name__)


def _finite_number(value: object, *, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number.")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be a finite number.")
    return parsed


class _RiskManagerCore:
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
        try:
            max_loss = _finite_number(
                self.config.max_single_loss_pct,
                label="Maximum single-loss percentage",
            )
        except ValueError as exc:
            raise ValueError("Maximum single-loss percentage must be finite and in [0, 1].") from exc
        if not math.isfinite(max_loss) or not 0 <= max_loss <= 1:
            raise ValueError("Maximum single-loss percentage must be finite and in [0, 1].")
        if stop_loss_pct is None:
            return max_loss
        try:
            parsed_stop = abs(_finite_number(stop_loss_pct, label="Stop-loss percentage"))
        except ValueError as exc:
            raise ValueError("Stop-loss percentage must be finite.") from exc
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

    def enforce_stop_rules(
        self,
        symbol: str,
        portfolio: Portfolio,
        price: float,
        stop_loss_pct: float | None,
        take_profit_pct: float | None,
    ) -> Order | None:
        position_qty = _finite_number(
            portfolio.position_qty,
            label="Protective-exit position quantity",
        )
        avg_entry_price = _finite_number(
            portfolio.avg_entry_price,
            label="Protective-exit average entry price",
        )
        if position_qty < 0 or avg_entry_price < 0:
            raise ValueError("Protective exit requires a non-negative position and average entry price.")
        if position_qty == 0:
            return None
        if avg_entry_price <= 0:
            raise ValueError("Protective exit requires a positive average entry price for an open position.")

        parsed_price = _finite_number(price, label="Protective-exit market price")
        if parsed_price <= 0:
            raise ValueError("Protective-exit market price must be positive.")
        effective_stop = self.effective_stop_loss(stop_loss_pct)
        effective_take_profit: float | None = None
        if take_profit_pct is not None:
            try:
                effective_take_profit = abs(
                    _finite_number(take_profit_pct, label="Take-profit percentage")
                )
            except ValueError as exc:
                raise ValueError("Take-profit percentage must be finite.") from exc

        pnl_pct = (parsed_price - avg_entry_price) / avg_entry_price
        if not math.isfinite(pnl_pct):
            raise ValueError("Protective exit derived a non-finite return percentage.")
        if pnl_pct <= -effective_stop:
            return Order(symbol, Action.SELL, position_qty, parsed_price, f"stop loss {pnl_pct:.2%}")
        if effective_take_profit is not None and pnl_pct >= effective_take_profit:
            return Order(symbol, Action.SELL, position_qty, parsed_price, f"take profit {pnl_pct:.2%}")
        return None


RISK_ENGINE_SCHEMA_VERSION = "research-risk-engine-v2"


@dataclass(frozen=True)
class _RiskConfigSnapshot:
    max_position_pct: float
    max_single_loss_pct: float
    max_daily_loss_pct: float
    max_leverage: float
    min_cash_pct: float


def _fail(code: str) -> None:
    raise ValueError(code)


def _native_number(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    if type(value) not in (int, float):
        _fail(f"research_risk_{label}_exact_native_number_required")
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail(f"research_risk_{label}_finite_required")
    if minimum is not None:
        if minimum_inclusive and parsed < minimum:
            _fail(f"research_risk_{label}_below_minimum")
        if not minimum_inclusive and parsed <= minimum:
            _fail(f"research_risk_{label}_must_exceed_minimum")
    if maximum is not None and parsed > maximum:
        _fail(f"research_risk_{label}_above_maximum")
    return parsed


def _exact_symbol(value: object) -> str:
    if type(value) is not str or not value:
        _fail("research_risk_symbol_exact_nonempty_str_required")
    return value


def _optional_native_number(value: object, *, label: str) -> float | None:
    if value is None:
        return None
    return _native_number(value, label=label)


def _snapshot_config(config: RiskConfig) -> _RiskConfigSnapshot:
    if type(config) is not RiskConfig:
        _fail("research_risk_exact_canonical_config_required")
    try:
        max_position_pct = _native_number(
            config.max_position_pct,
            label="max_position_pct",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
    except ValueError as exc:
        raise ValueError("Maximum position percentage must be a finite number in (0, 1].") from exc
    try:
        max_single_loss_pct = _native_number(
            config.max_single_loss_pct,
            label="max_single_loss_pct",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
    except ValueError as exc:
        raise ValueError("Maximum single-loss percentage must be a finite number in (0, 1].") from exc
    try:
        max_daily_loss_pct = _native_number(
            config.max_daily_loss_pct,
            label="max_daily_loss_pct",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
    except ValueError as exc:
        raise ValueError("Maximum daily-loss percentage must be a finite number in (0, 1].") from exc
    try:
        max_leverage = _native_number(
            config.max_leverage,
            label="max_leverage",
            minimum=0.0,
            minimum_inclusive=False,
        )
    except ValueError as exc:
        raise ValueError("Maximum leverage must be a finite positive number.") from exc
    try:
        min_cash_pct = _native_number(
            config.min_cash_pct,
            label="min_cash_pct",
            minimum=0.0,
            maximum=1.0,
        )
    except ValueError as exc:
        raise ValueError("Minimum cash percentage must be a finite number in [0, 1].") from exc
    return _RiskConfigSnapshot(
        max_position_pct=max_position_pct,
        max_single_loss_pct=max_single_loss_pct,
        max_daily_loss_pct=max_daily_loss_pct,
        max_leverage=max_leverage,
        min_cash_pct=min_cash_pct,
    )


class RiskManager(_RiskManagerCore):
    def __init__(self, config: RiskConfig):
        super().__init__(_snapshot_config(config))  # type: ignore[arg-type]

    def describe_semantics(self) -> dict:
        """Expose actual controls without implying account loss guarantees."""
        return {
            "schema_version": RISK_ENGINE_SCHEMA_VERSION,
            "stop_loss": {
                "config_key": "max_single_loss_pct",
                "meaning": "MAXIMUM_STOP_PRICE_DISTANCE_FROM_AVERAGE_ENTRY",
                "maximum_price_distance_pct": self.config.max_single_loss_pct,
                "requested_and_effective_values": "PER_BUY_SIGNAL_IN_SIGNALS_LEDGER",
                "account_loss_guarantee": False,
                "gap_slippage_and_capacity_can_exceed_distance": True,
            },
            "daily_loss": {
                "config_key": "max_daily_loss_pct",
                "meaning": "NEW_BUY_ADMISSION_HALT_FROM_UTC_DAY_START_EQUITY",
                "threshold_pct": self.config.max_daily_loss_pct,
                "continuous_position_liquidation": False,
                "hold_and_sell_remain_available": True,
            },
            "leverage": {
                "requested": self.config.max_leverage, "effective": 1.0,
                "supported": False,
                "policy": "SPOT_CASH_ONLY_REQUEST_NOT_APPLIED",
                "borrowing_margin_and_liquidation": "UNSUPPORTED",
            },
            "max_position_pct": self.config.max_position_pct,
            "min_cash_pct": self.config.min_cash_pct,
        }

    def __setattr__(self, name: str, value: object) -> None:
        if name == "config":
            if "config" in self.__dict__:
                raise AttributeError("research_risk_config_snapshot_is_immutable")
            if type(value) is not _RiskConfigSnapshot:
                raise TypeError("research_risk_internal_snapshot_required")
        elif name == "day_start_equity":
            if value is not None:
                value = _native_number(
                    value,
                    label="day_start_equity",
                    minimum=0.0,
                )
        elif name == "trading_halted":
            if type(value) is not bool:
                raise TypeError("research_risk_trading_halted_exact_bool_required")
        super().__setattr__(name, value)

    def reset_day(self, equity: float) -> None:
        parsed_equity = _native_number(
            equity,
            label="reset_equity",
            minimum=0.0,
        )
        super().reset_day(parsed_equity)

    def check_daily_loss(self, equity: float) -> bool:
        try:
            parsed_equity = _native_number(
                equity,
                label="daily_equity",
                minimum=0.0,
            )
        except ValueError:
            self.trading_halted = True
            return False
        return super().check_daily_loss(parsed_equity)

    def effective_stop_loss(self, stop_loss_pct: float | None) -> float:
        parsed_stop = _optional_native_number(
            stop_loss_pct,
            label="stop_loss_pct",
        )
        return super().effective_stop_loss(parsed_stop)

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
        exact_symbol = _exact_symbol(symbol)
        if type(signal) is not Signal:
            _fail("research_risk_exact_canonical_signal_required")
        if type(portfolio) is not Portfolio:
            _fail("research_risk_exact_canonical_portfolio_required")
        parsed_price = _native_number(
            price,
            label="market_price",
            minimum=0.0,
            minimum_inclusive=False,
        )
        parsed_fee = _native_number(
            fee_rate,
            label="fee_rate",
            minimum=0.0,
            maximum=1.0,
        )
        parsed_slippage = _native_number(
            slippage_pct,
            label="slippage_pct",
            minimum=0.0,
            maximum=1.0,
        )
        return super().signal_to_order(
            exact_symbol,
            signal,
            portfolio,
            parsed_price,
            fee_rate=parsed_fee,
            slippage_pct=parsed_slippage,
        )

    def enforce_stop_rules(
        self,
        symbol: str,
        portfolio: Portfolio,
        price: float,
        stop_loss_pct: float | None,
        take_profit_pct: float | None,
    ) -> Order | None:
        exact_symbol = _exact_symbol(symbol)
        if type(portfolio) is not Portfolio:
            _fail("research_risk_exact_canonical_portfolio_required")
        try:
            parsed_price = _native_number(
                price,
                label="protective_price",
                minimum=0.0,
                minimum_inclusive=False,
            )
        except ValueError as exc:
            raise ValueError("Protective-exit market price must be a finite positive number.") from exc
        try:
            parsed_stop = _optional_native_number(
                stop_loss_pct,
                label="protective_stop_loss_pct",
            )
        except ValueError as exc:
            raise ValueError("Stop-loss percentage must be a finite number in (0, 1].") from exc
        try:
            parsed_take = _optional_native_number(
                take_profit_pct,
                label="protective_take_profit_pct",
            )
        except ValueError as exc:
            raise ValueError("Take-profit percentage must be a finite number in (0, 1].") from exc
        return super().enforce_stop_rules(
            exact_symbol,
            portfolio,
            parsed_price,
            parsed_stop,
            parsed_take,
        )


__all__ = ["RISK_ENGINE_SCHEMA_VERSION", "RiskManager"]
