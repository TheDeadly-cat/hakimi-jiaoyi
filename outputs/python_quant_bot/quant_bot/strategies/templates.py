from __future__ import annotations

from typing import Type

import pandas as pd

from quant_bot.indicators import bollinger, macd, momentum, rsi, sma
from quant_bot.models import Portfolio, Signal
from quant_bot.strategies.base import StrategyBase


class DualMovingAverageStrategy(StrategyBase):
    name = "dual_ma"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        fast = int(self.get("fast_window", 20))
        slow = int(self.get("slow_window", 60))
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
        lookback = int(self.get("lookback", 80))
        grids = int(self.get("grids", 8))
        size_pct = float(self.get("position_pct", 0.12))
        close = data["close"]
        if len(close) < lookback:
            return Signal.hold("not enough data")
        recent = close.iloc[-lookback:]
        low = float(recent.min())
        high = float(recent.max())
        step = (high - low) / max(grids, 1)
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
        window = int(self.get("window", 20))
        std_mult = float(self.get("std_mult", 2.0))
        size_pct = float(self.get("position_pct", 0.2))
        close = data["close"]
        if len(close) < window + 2:
            return Signal.hold("not enough data")
        upper, mid, lower = bollinger(close, window, std_mult)
        price = close.iloc[-1]
        if price < lower.iloc[-1]:
            return Signal.buy("price below lower Bollinger band", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.04))
        if portfolio.position_qty > 0 and price > mid.iloc[-1]:
            return Signal.sell("price reverted to Bollinger midline", min(size_pct, 1.0))
        if price > upper.iloc[-1] and portfolio.position_qty > 0:
            return Signal.exit("price above upper Bollinger band")
        return Signal.hold("inside Bollinger bands")


class MacdStrategy(StrategyBase):
    name = "macd"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        if len(close) < 40:
            return Signal.hold("not enough data")
        line, signal_line, hist = macd(close, int(self.get("fast", 12)), int(self.get("slow", 26)), int(self.get("signal", 9)))
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
        if len(close) < window + 3:
            return Signal.hold("not enough data")
        current = rsi(close, window).iloc[-1]
        size_pct = float(self.get("position_pct", 0.15))
        oversold = float(self.get("oversold", 30))
        overbought = float(self.get("overbought", 70))
        if current < oversold:
            return Signal.buy(f"RSI oversold: {current:.2f}", size_pct, stop_loss_pct=self.get("stop_loss_pct", 0.04))
        if current > overbought and portfolio.position_qty > 0:
            return Signal.exit(f"RSI overbought: {current:.2f}")
        return Signal.hold("RSI neutral")


class MomentumStrategy(StrategyBase):
    name = "momentum"

    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        window = int(self.get("window", 20))
        threshold = float(self.get("threshold", 0.015))
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
