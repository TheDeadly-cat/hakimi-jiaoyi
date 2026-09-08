from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


DOMAIN_MODEL_SCHEMA_VERSION = "research-domain-models-v1"
_MAX_METADATA_DEPTH = 32


def _fail(code: str) -> None:
    raise ValueError(code)


def _exact_text(value: Any, *, label: str, nonempty: bool = False) -> str:
    if type(value) is not str:
        _fail(f"research_domain_{label}_exact_str_required")
    if nonempty and not value:
        _fail(f"research_domain_{label}_nonempty_required")
    return value


def _finite_number(
    value: Any,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
) -> float:
    if type(value) not in (int, float):
        _fail(f"research_domain_{label}_exact_native_number_required")
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail(f"research_domain_{label}_finite_required")
    if minimum is not None:
        if minimum_inclusive and parsed < minimum:
            _fail(f"research_domain_{label}_below_minimum")
        if not minimum_inclusive and parsed <= minimum:
            _fail(f"research_domain_{label}_must_exceed_minimum")
    if maximum is not None and parsed > maximum:
        _fail(f"research_domain_{label}_above_maximum")
    return parsed


def _optional_fraction(value: Any, *, label: str) -> float | None:
    if value is None:
        return None
    return _finite_number(
        value,
        label=label,
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
    )


def _clone_metadata_value(
    value: Any,
    *,
    path: str,
    active_container_ids: set[int],
    depth: int,
) -> Any:
    if depth > _MAX_METADATA_DEPTH:
        _fail("research_domain_metadata_depth_exceeded")
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"research_domain_{path}_finite_required")
        return value
    if type(value) is list:
        identity = id(value)
        if identity in active_container_ids:
            _fail("research_domain_metadata_cycle_rejected")
        active_container_ids.add(identity)
        try:
            return [
                _clone_metadata_value(
                    item,
                    path=f"{path}_{index}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_container_ids.remove(identity)
    if type(value) is dict:
        identity = id(value)
        if identity in active_container_ids:
            _fail("research_domain_metadata_cycle_rejected")
        active_container_ids.add(identity)
        try:
            cloned: dict[str, Any] = {}
            for key, item in value.items():
                exact_key = _exact_text(key, label="metadata_key", nonempty=True)
                cloned[exact_key] = _clone_metadata_value(
                    item,
                    path=f"{path}_{exact_key}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                )
            return cloned
        finally:
            active_container_ids.remove(identity)
    _fail(f"research_domain_{path}_exact_json_value_required")


def _exact_action(value: Any, *, label: str = "action") -> "Action":
    if type(value) is not Action:
        _fail(f"research_domain_{label}_exact_action_required")
    return value


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass(frozen=True)
class Signal:
    action: Action
    confidence: float = 0.0
    size_pct: float = 0.0
    reason: str = ""
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _exact_action(self.action))
        object.__setattr__(
            self,
            "confidence",
            _finite_number(self.confidence, label="signal_confidence", minimum=0.0, maximum=1.0),
        )
        object.__setattr__(
            self,
            "size_pct",
            _finite_number(self.size_pct, label="signal_size_pct", minimum=0.0, maximum=1.0),
        )
        object.__setattr__(self, "reason", _exact_text(self.reason, label="signal_reason"))
        object.__setattr__(
            self,
            "stop_loss_pct",
            _optional_fraction(self.stop_loss_pct, label="signal_stop_loss_pct"),
        )
        object.__setattr__(
            self,
            "take_profit_pct",
            _optional_fraction(self.take_profit_pct, label="signal_take_profit_pct"),
        )
        if self.metadata is None:
            return
        if type(self.metadata) is not dict:
            _fail("research_domain_metadata_exact_dict_required")
        object.__setattr__(
            self,
            "metadata",
            _clone_metadata_value(
                self.metadata,
                path="metadata",
                active_container_ids=set(),
                depth=0,
            ),
        )

    @classmethod
    def buy(cls, reason: str, size_pct: float, confidence: float = 1.0, **kwargs: Any) -> "Signal":
        return cls(Action.BUY, confidence=confidence, size_pct=size_pct, reason=reason, **kwargs)

    @classmethod
    def sell(cls, reason: str, size_pct: float, confidence: float = 1.0, **kwargs: Any) -> "Signal":
        return cls(Action.SELL, confidence=confidence, size_pct=size_pct, reason=reason, **kwargs)

    @classmethod
    def exit(cls, reason: str) -> "Signal":
        return cls(Action.EXIT, confidence=1.0, size_pct=1.0, reason=reason)

    @classmethod
    def hold(cls, reason: str = "no signal") -> "Signal":
        return cls(Action.HOLD, confidence=0.0, size_pct=0.0, reason=reason)


@dataclass
class Portfolio:
    cash: float
    position_qty: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0
    entry_fees: float = 0.0

    def __post_init__(self) -> None:
        self.cash = _finite_number(self.cash, label="portfolio_cash", minimum=0.0)
        self.position_qty = _finite_number(
            self.position_qty,
            label="portfolio_position_qty",
            minimum=0.0,
        )
        self.avg_entry_price = _finite_number(
            self.avg_entry_price,
            label="portfolio_avg_entry_price",
            minimum=0.0,
        )
        self.realized_pnl = _finite_number(self.realized_pnl, label="portfolio_realized_pnl")
        self.entry_fees = _finite_number(
            self.entry_fees,
            label="portfolio_entry_fees",
            minimum=0.0,
        )

    def equity(self, price: float) -> float:
        parsed_price = _finite_number(price, label="portfolio_equity_price", minimum=0.0)
        cash = _finite_number(self.cash, label="portfolio_cash", minimum=0.0)
        quantity = _finite_number(
            self.position_qty,
            label="portfolio_position_qty",
            minimum=0.0,
        )
        return cash + quantity * parsed_price

    def position_value(self, price: float) -> float:
        parsed_price = _finite_number(price, label="portfolio_value_price", minimum=0.0)
        quantity = _finite_number(
            self.position_qty,
            label="portfolio_position_qty",
            minimum=0.0,
        )
        return quantity * parsed_price


@dataclass(frozen=True)
class Order:
    symbol: str
    action: Action
    quantity: float
    price: float
    reason: str
    is_live: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _exact_text(self.symbol, label="order_symbol", nonempty=True))
        action = _exact_action(self.action, label="order_action")
        if action not in (Action.BUY, Action.SELL):
            _fail("Research domain Order only accepts BUY and SELL actions.")
        object.__setattr__(self, "action", action)
        object.__setattr__(
            self,
            "quantity",
            _finite_number(
                self.quantity,
                label="order_quantity",
                minimum=0.0,
                minimum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "price",
            _finite_number(
                self.price,
                label="order_price",
                minimum=0.0,
                minimum_inclusive=False,
            ),
        )
        object.__setattr__(self, "reason", _exact_text(self.reason, label="order_reason"))
        if type(self.is_live) is not bool:
            _fail("research_domain_order_is_live_exact_bool_required")
        if self.is_live is not False:
            _fail("research_domain_live_order_forbidden")


@dataclass(frozen=True)
class Fill:
    symbol: str
    action: Action
    quantity: float
    price: float
    fee: float
    pnl: float
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _exact_text(self.symbol, label="fill_symbol", nonempty=True))
        action = _exact_action(self.action, label="fill_action")
        if action not in (Action.BUY, Action.SELL):
            _fail("research_domain_fill_action_buy_or_sell_required")
        object.__setattr__(self, "action", action)
        object.__setattr__(
            self,
            "quantity",
            _finite_number(
                self.quantity,
                label="fill_quantity",
                minimum=0.0,
                minimum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "price",
            _finite_number(
                self.price,
                label="fill_price",
                minimum=0.0,
                minimum_inclusive=False,
            ),
        )
        object.__setattr__(self, "fee", _finite_number(self.fee, label="fill_fee", minimum=0.0))
        object.__setattr__(self, "pnl", _finite_number(self.pnl, label="fill_pnl"))
        object.__setattr__(self, "reason", _exact_text(self.reason, label="fill_reason"))


__all__ = [
    "DOMAIN_MODEL_SCHEMA_VERSION",
    "Action",
    "Signal",
    "Portfolio",
    "Order",
    "Fill",
]

