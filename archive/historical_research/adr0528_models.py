from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass
class Signal:
    action: Action
    confidence: float = 0.0
    size_pct: float = 0.0
    reason: str = ""
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    metadata: dict[str, Any] | None = None

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

    def equity(self, price: float) -> float:
        return self.cash + self.position_qty * price

    def position_value(self, price: float) -> float:
        return self.position_qty * price


@dataclass
class Order:
    symbol: str
    action: Action
    quantity: float
    price: float
    reason: str
    is_live: bool = False


@dataclass
class Fill:
    symbol: str
    action: Action
    quantity: float
    price: float
    fee: float
    pnl: float
    reason: str
