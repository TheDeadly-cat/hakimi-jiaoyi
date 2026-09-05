"""Explicit cash and single-entry spot benchmarks for the canonical engine."""
from __future__ import annotations

import math

from hakimi_research.models import Signal
from hakimi_research.strategies.base import StrategyBase

BUY_AND_HOLD_POLICY = "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET"
STANDARD_RISK_POLICY = "STANDARD_STRATEGY_RISK"


class CashBenchmarkStrategy(StrategyBase):
    def __init__(self, params: dict | None = None):
        if params is not None and (type(params) is not dict or params):
            raise ValueError("cash_benchmark_accepts_no_parameters")
        super().__init__({}, name="cash", version="cash-benchmark-v2")

    def generate_signal(self, data, portfolio):
        return Signal.hold("cash benchmark: hold initial cash throughout score")


class BuyAndHoldBenchmarkStrategy(StrategyBase):
    def __init__(self, params: dict | None = None):
        params = {} if params is None else params
        if type(params) is not dict or set(params) != {"target_position_pct"}:
            raise ValueError("buy_and_hold_requires_explicit_target_position_pct")
        target = params["target_position_pct"]
        if type(target) not in (int, float) or not math.isfinite(target) or not 0 < target <= 1:
            raise ValueError("buy_and_hold_target_position_pct_invalid")
        super().__init__({"target_position_pct": float(target)}, name="buy_and_hold", version="buy-and-hold-benchmark-v2")
        self._initial_decision_seen = False

    def generate_signal(self, data, portfolio):
        if not self._initial_decision_seen:
            self._initial_decision_seen = True
            return Signal.buy("buy-and-hold: single score-start entry attempt", self.get("target_position_pct", 1.0))
        return Signal.hold("buy-and-hold: no adding, reentry, stop, or target; mark at score end")
