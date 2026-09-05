from __future__ import annotations

import math
from typing import Type

import pandas as pd

from hakimi_research.indicators import bollinger, macd, momentum, rsi, sma
from hakimi_research.models import Portfolio, Signal
from hakimi_research.benchmarks import CashBenchmarkStrategy, BuyAndHoldBenchmarkStrategy
from hakimi_research.strategies.base import StrategyBase


class DualMovingAverageStrategy(StrategyBase):
    name = "dual_ma"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        raw_fast = self.get("fast_window", 20)
        raw_slow = self.get("slow_window", 60)
        if isinstance(raw_fast, bool) or isinstance(raw_slow, bool):
            raise ValueError(
                "Dual MA windows require positive integers with fast_window < slow_window."
            )
        try:
            fast = int(raw_fast)
            slow = int(raw_slow)
            fast_number = float(raw_fast)
            slow_number = float(raw_slow)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Dual MA windows require positive integers with fast_window < slow_window."
            ) from exc
        if (
            not math.isfinite(fast_number)
            or not math.isfinite(slow_number)
            or fast_number != fast
            or slow_number != slow
            or fast <= 0
            or slow <= 0
            or fast >= slow
        ):
            raise ValueError(
                "Dual MA windows require positive integers with fast_window < slow_window."
            )
        size_pct = float(self.get("position_pct", 0.25))
        close = data["close"]
        if len(close) < slow + 2:
            return Signal.hold("not enough data")
        fast_ma = sma(close, fast)
        slow_ma = sma(close, slow)
        crossed_up = fast_ma.iloc[-2] <= slow_ma.iloc[-2] and fast_ma.iloc[-1] > slow_ma.iloc[-1]
        crossed_down = fast_ma.iloc[-2] >= slow_ma.iloc[-2] and fast_ma.iloc[-1] < slow_ma.iloc[-1]
        if crossed_up and portfolio.position_qty <= 0:
            return Signal.buy("fast MA crossed above slow MA", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.03), take_profit_pct=self.get("take_profit_pct", 0.08))
        if crossed_down and portfolio.position_qty > 0:
            return Signal.exit("fast MA crossed below slow MA")
        return Signal.hold("no MA crossover")


class GridStrategy(StrategyBase):
    name = "grid"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        raw_lookback = self.get("lookback", 80)
        raw_grids = self.get("grids", 8)
        if isinstance(raw_lookback, bool) or isinstance(raw_grids, bool):
            raise ValueError(
                "Grid parameters require integer lookback >= 2 and grids >= 4."
            )
        try:
            lookback = int(raw_lookback)
            grids = int(raw_grids)
            lookback_number = float(raw_lookback)
            grids_number = float(raw_grids)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Grid parameters require integer lookback >= 2 and grids >= 4."
            ) from exc
        if (
            not math.isfinite(lookback_number)
            or not math.isfinite(grids_number)
            or lookback_number != lookback
            or grids_number != grids
            or lookback < 2
            or grids < 4
        ):
            raise ValueError(
                "Grid parameters require integer lookback >= 2 and grids >= 4."
            )
        size_pct = float(self.get("position_pct", 0.12))
        close = data["close"]
        if len(close) < lookback:
            return Signal.hold("not enough data")
        recent = close.iloc[-lookback:]
        low = float(recent.min())
        high = float(recent.max())
        step = (high - low) / grids
        price = float(close.iloc[-1])
        if step <= 0:
            return Signal.hold("flat grid")
        level = int((price - low) / step)
        midpoint = grids // 2
        if level <= midpoint - 2:
            return Signal.buy("price near lower grid", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.05))
        if level >= midpoint + 2 and portfolio.position_qty > 0:
            return Signal.sell("price near upper grid", min(size_pct, 1.0))
        return Signal.hold("inside grid")


class BollingerBandStrategy(StrategyBase):
    name = "bollinger"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        raw_window = self.get("window", 20)
        raw_std_mult = self.get("std_mult", 2.0)
        if isinstance(raw_window, bool) or isinstance(raw_std_mult, bool):
            raise ValueError(
                "Bollinger parameters require an integer window >= 2 and a finite positive std_mult."
            )
        try:
            window = int(raw_window)
            window_number = float(raw_window)
            std_mult = float(raw_std_mult)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Bollinger parameters require an integer window >= 2 and a finite positive std_mult."
            ) from exc
        if (
            not math.isfinite(window_number)
            or window_number != window
            or window < 2
            or not math.isfinite(std_mult)
            or std_mult <= 0
        ):
            raise ValueError(
                "Bollinger parameters require an integer window >= 2 and a finite positive std_mult."
            )
        size_pct = float(self.get("position_pct", 0.2))
        close = data["close"]
        if len(close) < window + 2:
            return Signal.hold("not enough data")
        upper, mid, lower = bollinger(close, window, std_mult)
        price = close.iloc[-1]
        if portfolio.position_qty > 0 and price > upper.iloc[-1]:
            return Signal.exit("price above upper Bollinger band")
        if price < lower.iloc[-1]:
            return Signal.buy("price below lower Bollinger band", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.04))
        if portfolio.position_qty > 0 and price > mid.iloc[-1]:
            return Signal.sell("price reverted to Bollinger midline", min(size_pct, 1.0))
        return Signal.hold("inside Bollinger bands")


class MacdStrategy(StrategyBase):
    name = "macd"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        raw_fast = self.get("fast", 12)
        raw_slow = self.get("slow", 26)
        raw_signal = self.get("signal", 9)
        if (
            isinstance(raw_fast, bool)
            or isinstance(raw_slow, bool)
            or isinstance(raw_signal, bool)
        ):
            raise ValueError(
                "MACD periods require positive integers with fast < slow and signal >= 1."
            )
        try:
            fast = int(raw_fast)
            slow = int(raw_slow)
            signal_window = int(raw_signal)
            fast_number = float(raw_fast)
            slow_number = float(raw_slow)
            signal_number = float(raw_signal)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "MACD periods require positive integers with fast < slow and signal >= 1."
            ) from exc
        if (
            not math.isfinite(fast_number)
            or not math.isfinite(slow_number)
            or not math.isfinite(signal_number)
            or fast_number != fast
            or slow_number != slow
            or signal_number != signal_window
            or fast <= 0
            or slow <= 0
            or signal_window <= 0
            or fast >= slow
        ):
            raise ValueError(
                "MACD periods require positive integers with fast < slow and signal >= 1."
            )
        if len(close) < 40:
            return Signal.hold("not enough data")
        line, signal_line, hist = macd(close, fast, slow, signal_window)
        size_pct = float(self.get("position_pct", 0.25))
        crossed_up = line.iloc[-2] <= signal_line.iloc[-2] and line.iloc[-1] > signal_line.iloc[-1]
        crossed_down = line.iloc[-2] >= signal_line.iloc[-2] and line.iloc[-1] < signal_line.iloc[-1]
        if crossed_up and hist.iloc[-1] > 0:
            return Signal.buy("MACD bullish crossover", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.035))
        if crossed_down and portfolio.position_qty > 0:
            return Signal.exit("MACD bearish crossover")
        return Signal.hold("no MACD signal")


class RsiStrategy(StrategyBase):
    name = "rsi"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        window = int(self.get("window", 14))
        raw_oversold = self.get("oversold", 30)
        raw_overbought = self.get("overbought", 70)
        if isinstance(raw_oversold, bool) or isinstance(raw_overbought, bool):
            raise ValueError(
                "RSI thresholds must satisfy 0 <= oversold < overbought <= 100."
            )
        try:
            oversold = float(raw_oversold)
            overbought = float(raw_overbought)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "RSI thresholds must satisfy 0 <= oversold < overbought <= 100."
            ) from exc
        if (
            not math.isfinite(oversold)
            or not math.isfinite(overbought)
            or not 0 <= oversold < overbought <= 100
        ):
            raise ValueError(
                "RSI thresholds must satisfy 0 <= oversold < overbought <= 100."
            )
        if len(close) < window + 3:
            return Signal.hold("not enough data")
        current = rsi(close, window).iloc[-1]
        size_pct = float(self.get("position_pct", 0.15))
        if current < oversold:
            return Signal.buy(f"RSI oversold: {current:.2f}", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.04))
        if current > overbought and portfolio.position_qty > 0:
            return Signal.exit(f"RSI overbought: {current:.2f}")
        return Signal.hold("RSI neutral")


class MomentumStrategy(StrategyBase):
    name = "momentum"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        raw_window = self.get("window", 20)
        raw_threshold = self.get("threshold", 0.015)
        if isinstance(raw_window, bool) or isinstance(raw_threshold, bool):
            raise ValueError(
                "Momentum parameters require a positive integer window and a finite non-negative threshold."
            )
        try:
            window = int(raw_window)
            window_number = float(raw_window)
            threshold = float(raw_threshold)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Momentum parameters require a positive integer window and a finite non-negative threshold."
            ) from exc
        if (
            not math.isfinite(window_number)
            or window_number != window
            or window <= 0
            or not math.isfinite(threshold)
            or threshold < 0
        ):
            raise ValueError(
                "Momentum parameters require a positive integer window and a finite non-negative threshold."
            )
        if len(close) < window + 3:
            return Signal.hold("not enough data")
        mom = momentum(close, window).iloc[-1]
        size_pct = float(self.get("position_pct", 0.22))
        if mom > threshold:
            return Signal.buy(f"positive momentum: {mom:.2%}", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.035))
        if mom < -threshold and portfolio.position_qty > 0:
            return Signal.exit(f"negative momentum: {mom:.2%}")
        return Signal.hold("momentum neutral")


STRATEGY_REGISTRY: dict[str, Type[StrategyBase]] = {
    "cash": CashBenchmarkStrategy,
    "buy_and_hold": BuyAndHoldBenchmarkStrategy,
    "dual_ma": DualMovingAverageStrategy,
    "grid": GridStrategy,
    "bollinger": BollingerBandStrategy,
    "macd": MacdStrategy,
    "rsi": RsiStrategy,
    "momentum": MomentumStrategy,
}


def build_strategy(name: str, params: dict | None = None) -> StrategyBase:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}. Available: {sorted(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](params=params or {})
