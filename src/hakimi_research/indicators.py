from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def bollinger(close: pd.Series, window: int = 20, std_mult: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std()
    upper = mid + std * std_mult
    lower = mid - std * std_mult
    return upper, mid, lower


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(close, fast) - ema(close, slow)
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window, min_periods=window).mean()
    zero_loss = loss.eq(0)
    zero_gain = gain.eq(0)
    rs = gain / loss.mask(zero_loss)
    value = 100 - (100 / (1 + rs))
    value = value.mask(zero_loss & gain.gt(0), 100.0)
    return value.mask(zero_loss & zero_gain, 50.0)


def momentum(close: pd.Series, window: int = 20) -> pd.Series:
    return close.pct_change(periods=window)
