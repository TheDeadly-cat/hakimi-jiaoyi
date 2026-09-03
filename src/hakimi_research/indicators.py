from __future__ import annotations

import pandas as pd


def _sma_core(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _ema_core(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def _bollinger_core(close: pd.Series, window: int = 20, std_mult: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std()
    upper = mid + std * std_mult
    lower = mid - std * std_mult
    return upper, mid, lower


def _macd_core(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(close, fast) - ema(close, slow)
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def _rsi_core(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window, min_periods=window).mean()
    zero_loss = loss.eq(0)
    zero_gain = gain.eq(0)
    rs = gain / loss.mask(zero_loss)
    value = 100 - (100 / (1 + rs))
    value = value.mask(zero_loss & gain.gt(0), 100.0)
    return value.mask(zero_loss & zero_gain, 50.0)


def _momentum_core(close: pd.Series, window: int = 20) -> pd.Series:
    return close.pct_change(periods=window)
INDICATOR_SCHEMA_VERSION = "research-indicators-v1"

import math as _math

import numpy as _np


def _indicator_fail(code: str) -> None:
    raise ValueError(code)


def _series_input(value: object, *, label: str) -> pd.Series:
    if type(value) is not pd.Series:
        _indicator_fail(f"research_indicator_{label}_exact_series_required")
    if value.empty:
        _indicator_fail(f"research_indicator_{label}_nonempty_required")
    if not pd.api.types.is_numeric_dtype(value.dtype):
        _indicator_fail(f"research_indicator_{label}_numeric_dtype_required")
    if pd.api.types.is_bool_dtype(value.dtype):
        _indicator_fail(f"research_indicator_{label}_bool_dtype_rejected")
    numeric = value.to_numpy(dtype=float, copy=True)
    if not _np.isfinite(numeric).all():
        _indicator_fail(f"research_indicator_{label}_finite_required")
    if not value.index.is_unique:
        _indicator_fail(f"research_indicator_{label}_unique_index_required")
    if not value.index.is_monotonic_increasing:
        _indicator_fail(f"research_indicator_{label}_ordered_index_required")
    return value.astype("float64").copy(deep=True)


def _window(value: object, *, label: str) -> int:
    if type(value) is not int:
        _indicator_fail(f"research_indicator_{label}_exact_int_required")
    if value <= 0:
        _indicator_fail(f"research_indicator_{label}_positive_required")
    return value


def _positive_number(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        _indicator_fail(f"research_indicator_{label}_exact_native_number_required")
    parsed = float(value)
    if not _math.isfinite(parsed) or parsed <= 0:
        _indicator_fail(f"research_indicator_{label}_finite_positive_required")
    return parsed


def _series_output(value: object, *, index: pd.Index, label: str) -> pd.Series:
    if type(value) is not pd.Series:
        _indicator_fail(f"research_indicator_{label}_exact_series_output_required")
    if not value.index.equals(index):
        _indicator_fail(f"research_indicator_{label}_index_drift")
    numeric = value.to_numpy(dtype=float, copy=True)
    if _np.isinf(numeric).any():
        _indicator_fail(f"research_indicator_{label}_infinite_output_rejected")
    return value.astype("float64").copy(deep=True)


def sma(series: pd.Series, window: int) -> pd.Series:
    source = _series_input(series, label="sma_input")
    result = _sma_core(source, _window(window, label="sma_window"))
    return _series_output(result, index=source.index, label="sma")


def ema(series: pd.Series, window: int) -> pd.Series:
    source = _series_input(series, label="ema_input")
    result = _ema_core(source, _window(window, label="ema_window"))
    return _series_output(result, index=source.index, label="ema")


def bollinger(
    close: pd.Series,
    window: int = 20,
    std_mult: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    source = _series_input(close, label="bollinger_input")
    exact_window = _window(window, label="bollinger_window")
    multiplier = _positive_number(std_mult, label="bollinger_std_mult")
    middle, upper, lower = _bollinger_core(source, exact_window, multiplier)
    return (
        _series_output(middle, index=source.index, label="bollinger_middle"),
        _series_output(upper, index=source.index, label="bollinger_upper"),
        _series_output(lower, index=source.index, label="bollinger_lower"),
    )


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    source = _series_input(close, label="macd_input")
    fast_window = _window(fast, label="macd_fast")
    slow_window = _window(slow, label="macd_slow")
    signal_window = _window(signal, label="macd_signal")
    if fast_window >= slow_window:
        _indicator_fail("research_indicator_macd_fast_must_be_less_than_slow")
    line, signal_line, histogram = _macd_core(
        source,
        fast_window,
        slow_window,
        signal_window,
    )
    return (
        _series_output(line, index=source.index, label="macd_line"),
        _series_output(signal_line, index=source.index, label="macd_signal_line"),
        _series_output(histogram, index=source.index, label="macd_histogram"),
    )


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    source = _series_input(close, label="rsi_input")
    result = _rsi_core(source, _window(window, label="rsi_window"))
    return _series_output(result, index=source.index, label="rsi")


def momentum(close: pd.Series, window: int = 20) -> pd.Series:
    source = _series_input(close, label="momentum_input")
    result = _momentum_core(source, _window(window, label="momentum_window"))
    return _series_output(result, index=source.index, label="momentum")


__all__ = [
    "INDICATOR_SCHEMA_VERSION",
    "sma",
    "ema",
    "bollinger",
    "macd",
    "rsi",
    "momentum",
]