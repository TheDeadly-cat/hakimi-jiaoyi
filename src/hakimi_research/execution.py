from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from hakimi_research.models import Action, Fill, Order, Portfolio


EXECUTION_SIMULATOR_SCHEMA_VERSION = "research-execution-simulator-v3"
EXECUTION_ADMISSION_SCHEMA_VERSION = "research-execution-admission-v1"

logger = logging.getLogger(__name__)


def _fail(code: str) -> None:
    raise ValueError(code)


def _finite_native_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float):
        _fail(f"research_execution_{label}_exact_native_number_required")
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail(f"research_execution_{label}_finite_required")
    return parsed


@dataclass(frozen=True)
class ResearchExecutionAdmission:
    status: str
    reason: str
    symbol: str
    action: str
    requested_quantity: float
    executable_quantity: float
    available_volume: float | None
    volume_capacity_quantity: float | None
    minimum_executable_quantity: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXECUTION_ADMISSION_SCHEMA_VERSION,
            "status": self.status,
            "reason": self.reason,
            "symbol": self.symbol,
            "action": self.action,
            "requested_quantity": self.requested_quantity,
            "executable_quantity": self.executable_quantity,
            "available_volume": self.available_volume,
            "volume_capacity_quantity": self.volume_capacity_quantity,
            "minimum_executable_quantity": self.minimum_executable_quantity,
        }


@dataclass(frozen=True)
class ResearchExecutionSimulator:
    fee_rate: float = 0.0008
    slippage_pct: float = 0.0005
    max_volume_participation_rate: float | None = None
    minimum_executable_quantity: float | None = None

    def __post_init__(self) -> None:
        fee_rate = _finite_native_number(self.fee_rate, label="fee_rate")
        slippage_pct = _finite_native_number(self.slippage_pct, label="slippage_pct")
        if not 0 <= fee_rate < 1 or not 0 <= slippage_pct < 1:
            _fail("ResearchExecutionSimulator fee and slippage must be in [0, 1).")
        participation = self.max_volume_participation_rate
        if participation is not None:
            participation = _finite_native_number(
                participation,
                label="max_volume_participation_rate",
            )
            if not 0 < participation <= 1:
                _fail(
                    "ResearchExecutionSimulator volume participation must be in (0, 1]."
                )
        minimum = self.minimum_executable_quantity
        if minimum is not None:
            minimum = _finite_native_number(
                minimum,
                label="minimum_executable_quantity",
            )
            if minimum <= 0:
                _fail(
                    "ResearchExecutionSimulator minimum executable quantity must be positive."
                )
        object.__setattr__(self, "fee_rate", fee_rate)
        object.__setattr__(self, "slippage_pct", slippage_pct)
        object.__setattr__(self, "max_volume_participation_rate", participation)
        object.__setattr__(self, "minimum_executable_quantity", minimum)

    def assess_order(
        self,
        order: Order,
        portfolio: Portfolio,
        *,
        available_volume: float | None = None,
    ) -> ResearchExecutionAdmission:
        """Return a non-mutating research admission decision for one order."""

        if type(order) is not Order:
            _fail("research_execution_exact_canonical_order_required")
        if type(portfolio) is not Portfolio:
            _fail("research_execution_exact_canonical_portfolio_required")
        if order.is_live is not False:
            _fail("research_execution_live_order_forbidden")
        if order.action not in (Action.BUY, Action.SELL):
            _fail("ResearchExecutionSimulator only accepts BUY and SELL orders.")

        order_price = _finite_native_number(order.price, label="order_price")
        order_quantity = _finite_native_number(order.quantity, label="order_quantity")
        cash = _finite_native_number(portfolio.cash, label="portfolio_cash")
        position_qty = _finite_native_number(
            portfolio.position_qty,
            label="portfolio_position_qty",
        )
        _finite_native_number(
            portfolio.avg_entry_price,
            label="portfolio_avg_entry_price",
        )
        _finite_native_number(portfolio.realized_pnl, label="portfolio_realized_pnl")
        _finite_native_number(portfolio.entry_fees, label="portfolio_entry_fees")
        if order_price <= 0 or order_quantity <= 0 or cash < 0 or position_qty < 0:
            _fail("ResearchExecutionSimulator received an invalid order or account state.")

        volume: float | None = None
        capacity_quantity = math.inf
        if self.max_volume_participation_rate is not None:
            if available_volume is None:
                _fail("research_execution_available_volume_required")
            volume = _finite_native_number(available_volume, label="available_volume")
            if volume < 0:
                _fail("research_execution_nonnegative_available_volume_required")
            capacity_quantity = volume * self.max_volume_participation_rate
            if not math.isfinite(capacity_quantity) or capacity_quantity < 0:
                _fail("research_execution_volume_capacity_invalid")

        fill_price = order_price * (
            1 + self.slippage_pct if order.action is Action.BUY else 1 - self.slippage_pct
        )
        if not math.isfinite(fill_price) or fill_price <= 0:
            _fail("ResearchExecutionSimulator execution price is invalid.")
        if order.action is Action.BUY:
            all_in_unit_cost = fill_price * (1 + self.fee_rate)
            executable = min(
                order_quantity,
                capacity_quantity,
                cash / all_in_unit_cost,
            )
            zero_reason = "BUYING_POWER_UNAVAILABLE"
        else:
            executable = min(order_quantity, capacity_quantity, position_qty)
            zero_reason = "POSITION_UNAVAILABLE"

        status = "ACCEPTED"
        reason = "NONE"
        if executable <= 0:
            status = "REJECTED"
            reason = "VOLUME_CAPACITY_UNAVAILABLE" if capacity_quantity == 0 else zero_reason
        elif (
            self.minimum_executable_quantity is not None
            and executable < self.minimum_executable_quantity
        ):
            status = "REJECTED"
            reason = "MINIMUM_EXECUTABLE_QUANTITY_NOT_MET"
        return ResearchExecutionAdmission(
            status=status,
            reason=reason,
            symbol=order.symbol,
            action=order.action.value,
            requested_quantity=order_quantity,
            executable_quantity=executable,
            available_volume=volume,
            volume_capacity_quantity=(
                None if math.isinf(capacity_quantity) else capacity_quantity
            ),
            minimum_executable_quantity=self.minimum_executable_quantity,
        )

    def submit_order(
        self,
        order: Order,
        portfolio: Portfolio,
        *,
        available_volume: float | None = None,
    ) -> Fill:
        admission = self.assess_order(
            order,
            portfolio,
            available_volume=available_volume,
        )
        if admission.status == "REJECTED":
            _fail(f"research_execution_order_rejected:{admission.reason}")
        if type(order) is not Order:
            _fail("research_execution_exact_canonical_order_required")
        if type(portfolio) is not Portfolio:
            _fail("research_execution_exact_canonical_portfolio_required")
        if order.is_live is not False:
            _fail("research_execution_live_order_forbidden")
        if order.action not in (Action.BUY, Action.SELL):
            _fail("ResearchExecutionSimulator only accepts BUY and SELL orders.")

        order_price = _finite_native_number(order.price, label="order_price")
        order_quantity = _finite_native_number(order.quantity, label="order_quantity")
        cash = _finite_native_number(portfolio.cash, label="portfolio_cash")
        position_qty = _finite_native_number(
            portfolio.position_qty,
            label="portfolio_position_qty",
        )
        avg_entry_price = _finite_native_number(
            portfolio.avg_entry_price,
            label="portfolio_avg_entry_price",
        )
        realized_pnl = _finite_native_number(
            portfolio.realized_pnl,
            label="portfolio_realized_pnl",
        )
        entry_fees = _finite_native_number(
            portfolio.entry_fees,
            label="portfolio_entry_fees",
        )
        if (
            order_price <= 0
            or order_quantity <= 0
            or cash < 0
            or position_qty < 0
            or avg_entry_price < 0
            or entry_fees < 0
        ):
            _fail("ResearchExecutionSimulator received an invalid order or account state.")

        capacity_quantity = math.inf
        if self.max_volume_participation_rate is not None:
            if available_volume is None:
                _fail("research_execution_available_volume_required")
            volume = _finite_native_number(
                available_volume,
                label="available_volume",
            )
            if volume <= 0:
                _fail("research_execution_positive_available_volume_required")
            capacity_quantity = volume * self.max_volume_participation_rate
            if not math.isfinite(capacity_quantity) or capacity_quantity <= 0:
                _fail("research_execution_volume_capacity_invalid")

        fill_price = order_price * (
            1 + self.slippage_pct if order.action is Action.BUY else 1 - self.slippage_pct
        )
        if not math.isfinite(fill_price) or fill_price <= 0:
            _fail("ResearchExecutionSimulator execution price is invalid.")

        pnl = 0.0
        filled_quantity = min(order_quantity, capacity_quantity)
        new_cash = cash
        new_position_qty = position_qty
        new_avg_entry_price = avg_entry_price
        new_realized_pnl = realized_pnl
        new_entry_fees = entry_fees

        if order.action is Action.BUY:
            all_in_unit_cost = fill_price * (1 + self.fee_rate)
            if not math.isfinite(all_in_unit_cost) or all_in_unit_cost <= 0:
                _fail("ResearchExecutionSimulator derived an invalid all-in unit cost.")
            filled_quantity = min(filled_quantity, cash / all_in_unit_cost)
            if filled_quantity <= 0:
                _fail("ResearchExecutionSimulator cannot fill a buy order without available cash.")
            notional = filled_quantity * fill_price
            fee = notional * self.fee_rate
            new_position_qty = position_qty + filled_quantity
            new_value = position_qty * avg_entry_price + notional
            new_avg_entry_price = new_value / new_position_qty
            new_cash = cash - notional - fee
            new_entry_fees = entry_fees + fee
            prospective = (
                filled_quantity,
                notional,
                fee,
                new_position_qty,
                new_avg_entry_price,
                new_cash,
                new_entry_fees,
            )
            if any(not math.isfinite(value) for value in prospective) or new_cash < -1e-9:
                _fail("ResearchExecutionSimulator buy fill would create an invalid account state.")
            new_cash = max(0.0, new_cash)
        else:
            position_before = position_qty
            filled_quantity = min(filled_quantity, position_before)
            if filled_quantity <= 0:
                _fail("ResearchExecutionSimulator cannot fill a sell order without an open position.")
            notional = filled_quantity * fill_price
            fee = notional * self.fee_rate
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
                _fail("ResearchExecutionSimulator sell fill would create an invalid account state.")
            new_cash = max(0.0, new_cash)
            new_position_qty = max(0.0, new_position_qty)
            if new_position_qty == 0:
                new_position_qty = 0.0
                new_avg_entry_price = 0.0
                new_entry_fees = 0.0

        fill = Fill(
            order.symbol,
            order.action,
            filled_quantity,
            fill_price,
            fee,
            pnl,
            order.reason,
        )

        portfolio.cash = new_cash
        portfolio.position_qty = new_position_qty
        portfolio.avg_entry_price = new_avg_entry_price
        portfolio.realized_pnl = new_realized_pnl
        portfolio.entry_fees = new_entry_fees

        logger.info("RESEARCH SIMULATED FILL %s", fill)
        return fill


__all__ = [
    "EXECUTION_ADMISSION_SCHEMA_VERSION",
    "EXECUTION_SIMULATOR_SCHEMA_VERSION",
    "ResearchExecutionAdmission",
    "ResearchExecutionSimulator",
]
