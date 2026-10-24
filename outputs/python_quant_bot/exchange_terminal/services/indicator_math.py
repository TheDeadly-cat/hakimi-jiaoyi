"""Versioned, causal indicator definitions shared by current terminal consumers.

Missing/non-finite observations break a window; they are never forward filled.
EMA restarts at the first finite observation after a gap. RSI and ATR use simple
rolling averages, not Wilder smoothing. Archived engines retain their own code.
"""
from __future__ import annotations

import math
from hashlib import sha256
from pathlib import Path
from typing import Any


FORMULA_VERSION = "hakimi-indicators-v1"
LOADED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
CONTRACT = {
    "version": FORMULA_VERSION,
    "sma": "full-window-arithmetic-mean",
    "ema": "alpha-2/(n+1)-first-value-seed-reset-after-gap",
    "bollinger": "sma-population-standard-deviation-ddof0",
    "macd": "ema-fast-minus-slow-signal-ema-unscaled-histogram",
    "rsi": "simple-rolling-gains-losses-flat50-no-loss100-no-gain0",
    "atr": "simple-rolling-true-range-requires-previous-close",
    "missing": "null-no-fill-full-window-required",
}


def assert_loaded_source_current() -> str:
    if sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_SOURCE_SHA256:
        raise ValueError("indicator_source_changed_restart_required")
    return LOADED_SOURCE_SHA256


def _window(window: int) -> int:
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise ValueError("indicator_window_must_be_positive_integer")
    return window


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def sma(values, window: int) -> list[float | None]:
    window = _window(window)
    values = [_finite(value) for value in values]
    result = []
    for index in range(len(values)):
        sample = values[max(0, index + 1 - window):index + 1]
        result.append(_finite(sum(sample) / window) if len(sample) == window and None not in sample else None)
    return result


def ema(values, window: int) -> list[float | None]:
    alpha = 2.0 / (_window(window) + 1.0)
    result, previous = [], None
    for raw in values:
        value = _finite(raw)
        previous = None if value is None else value if previous is None else _finite(alpha * value + (1 - alpha) * previous)
        result.append(previous)
    return result


def bollinger(values, window: int = 20, std_mult: float = 2.0):
    window = _window(window)
    if _finite(std_mult) is None or std_mult < 0:
        raise ValueError("indicator_band_multiplier_invalid")
    values = [_finite(value) for value in values]
    mids = sma(values, window)
    result = []
    for index, mid in enumerate(mids):
        if mid is None:
            result.append(None)
            continue
        sample = values[index + 1 - window:index + 1]
        band = math.sqrt(sum((value - mid) * (value - mid) for value in sample) / window) * std_mult
        upper, lower = _finite(mid + band), _finite(mid - band)
        result.append({"upper": upper, "mid": mid, "lower": lower}
                      if upper is not None and lower is not None else None)
    return result


def macd(values, fast: int = 12, slow: int = 26, signal: int = 9):
    values = list(values)
    fast_values, slow_values = ema(values, fast), ema(values, slow)
    line = [None if a is None or b is None else _finite(a - b) for a, b in zip(fast_values, slow_values)]
    signal_line = ema(line, signal)
    hist = [None if a is None or b is None else _finite(a - b) for a, b in zip(line, signal_line)]
    return line, signal_line, hist


def rsi(values, window: int = 14):
    window = _window(window)
    values = [_finite(value) for value in values]
    changes = [None if index == 0 or value is None or values[index - 1] is None
               else value - values[index - 1] for index, value in enumerate(values)]
    gains = sma([None if change is None else max(change, 0.0) for change in changes], window)
    losses = sma([None if change is None else max(-change, 0.0) for change in changes], window)
    result = []
    for gain, loss in zip(gains, losses):
        if gain is None or loss is None:
            result.append(None)
        elif loss == 0:
            result.append(50.0 if gain == 0 else 100.0)
        else:
            result.append(100.0 - 100.0 / (1.0 + gain / loss))
    return result


def momentum(values, window: int = 20):
    window = _window(window)
    values = [_finite(value) for value in values]
    return [None if index < window or None in values[max(0, index - window):index + 1]
            or values[index - window] == 0
            else _finite(value / values[index - window] - 1.0) for index, value in enumerate(values)]


def atr(rows, window: int = 14):
    _window(window)
    result, previous_close = [], None
    for row in rows:
        high, low, close = (_finite(row.get(key)) for key in ("high", "low", "close"))
        valid = high is not None and low is not None and close is not None and high >= close >= low
        result.append(max(high - low, abs(high - previous_close), abs(low - previous_close))
                      if valid and previous_close is not None else None)
        previous_close = close if valid else None
    return sma(result, window)
