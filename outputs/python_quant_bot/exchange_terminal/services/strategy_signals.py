from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable


SIGNAL_ENGINE_VERSION = "causal-long-only-signals-v6"


_CAPABILITIES: dict[str, dict[str, Any]] = {
    "dual_ma": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "bollinger": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "macd": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "rsi": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "momentum": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "livermore": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "turtle": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "darvas": {"backtest_supported": True, "paper_clock_supported": True, "model": "single_position", "signal_input": "CLOSES"},
    "volume_trend": {
        "backtest_supported": True,
        "paper_clock_supported": False,
        "model": "single_position",
        "signal_input": "BARS",
        "paper_blocker": "Volume trend remains research-only until its OHLCV paper-clock path passes independent validation.",
    },
    "trend_pullback": {
        "backtest_supported": True,
        "new_research_allowed": False,
        "paper_clock_supported": False,
        "model": "single_position",
        "signal_input": "BARS",
        "paper_blocker": "Trend pullback is falsified for this research generation; historical evidence replay only. Any new mechanism requires a new strategy ID and fresh preregistration, and this ID has no paper-clock authority.",
    },
    "squeeze_breakout": {
        "backtest_supported": True,
        "new_research_allowed": False,
        "paper_clock_supported": False,
        "model": "single_position",
        "signal_input": "BARS",
        "paper_blocker": "Squeeze breakout is falsified for this research generation; historical evidence replay only. Any new mechanism requires a new strategy ID and fresh preregistration, and this ID has no paper-clock authority.",
    },
    "grid": {
        "backtest_supported": False,
        "paper_clock_supported": False,
        "model": "multi_order_grid",
        "signal_input": "CLOSES",
        "blocker": "A grid strategy requires persistent levels, working orders, partial fills, and inventory accounting.",
    },
    "martingale": {
        "backtest_supported": False,
        "paper_clock_supported": False,
        "model": "bounded_scale_in",
        "signal_input": "CLOSES",
        "blocker": "Martingale requires an enforced layer count and aggregate risk budget before validation.",
    },
    "anti_martingale": {
        "backtest_supported": False,
        "paper_clock_supported": False,
        "model": "bounded_scale_in",
        "signal_input": "CLOSES",
        "blocker": "Anti-martingale requires an enforced layer count and scale-in exposure model before validation.",
    },
}


def strategy_validation_capability(strategy_id: str) -> dict[str, Any]:
    clean_id = str(strategy_id or "").strip().lower()
    capability = _CAPABILITIES.get(clean_id)
    if capability is None:
        return {
            "strategy_id": clean_id,
            "known": False,
            "backtest_supported": False,
            "new_research_allowed": False,
            "paper_clock_supported": False,
            "model": "unknown",
            "signal_input": "UNKNOWN",
            "blocker": "Unknown strategy id; implicit fallback is forbidden.",
            "signal_engine_version": SIGNAL_ENGINE_VERSION,
        }
    return {
        "strategy_id": clean_id,
        "known": True,
        **capability,
        "new_research_allowed": bool(
            capability.get("new_research_allowed", capability["backtest_supported"])
        ),
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
    }


def validated_strategy_ids() -> list[str]:
    return [strategy_id for strategy_id, capability in _CAPABILITIES.items() if capability["backtest_supported"]]


def new_research_strategy_ids() -> list[str]:
    """Return strategy ids eligible for a genuinely new preregistered hypothesis."""
    return [
        strategy_id
        for strategy_id, capability in _CAPABILITIES.items()
        if capability["backtest_supported"]
        and capability.get("new_research_allowed", True)
    ]


def assert_new_research_allowed(strategy_ids: list[str]) -> None:
    normalized = list(dict.fromkeys(
        str(strategy_id or "").strip().lower()
        for strategy_id in strategy_ids
        if str(strategy_id or "").strip()
    ))
    falsified = [
        strategy_id
        for strategy_id in normalized
        if strategy_id in _CAPABILITIES
        and _CAPABILITIES[strategy_id]["backtest_supported"]
        and not _CAPABILITIES[strategy_id].get("new_research_allowed", True)
    ]
    if falsified:
        raise ValueError(
            "falsified_strategy_requires_new_id_and_fresh_preregistration:"
            + ",".join(falsified)
        )


def strategy_signal_input(strategy_id: str) -> str:
    capability = strategy_validation_capability(strategy_id)
    return str(capability.get("signal_input") or "UNKNOWN").upper()


def strategy_startup_candles_for_params(
    strategy_id: str,
    params: dict[str, Any] | None = None,
) -> int:
    """Return the deterministic warmup used by research and server wrappers."""

    del strategy_id
    frozen = dict(params or {})
    numeric_windows = [
        int(float(value))
        for key, value in frozen.items()
        if any(token in str(key) for token in ("window", "slow", "fast", "lookback", "period"))
        and str(value).replace(".", "", 1).isdigit()
    ]
    return max(80, max(numeric_windows) + 5) if numeric_windows else 80


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ema_series(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (max(int(span), 1) + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * float(value) + (1.0 - alpha) * result[-1])
    return result


def _macd_state(closes: list[float], fast: int, slow: int, signal: int) -> tuple[float, float, float, float]:
    fast_series = _ema_series(closes, fast)
    slow_series = _ema_series(closes, slow)
    macd_series = [fast_value - slow_value for fast_value, slow_value in zip(fast_series, slow_series)]
    signal_series = _ema_series(macd_series, signal)
    if len(macd_series) < 2 or len(signal_series) < 2:
        return 0.0, 0.0, 0.0, 0.0
    return macd_series[-2], signal_series[-2], macd_series[-1], signal_series[-1]


def rolling_strategy_signal(
    strategy_id: str,
    closes: list[float],
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_id = str(strategy_id or "").strip().lower()
    capability = strategy_validation_capability(clean_id)
    if not capability["known"]:
        return {"action": "HOLD", "reason": "unsupported_strategy", "validation_blocker": capability["blocker"]}
    if not capability["backtest_supported"]:
        return {"action": "HOLD", "reason": "unvalidated_stateful_strategy", "validation_blocker": capability["blocker"]}
    if capability.get("signal_input") != "CLOSES":
        return {
            "action": "HOLD",
            "reason": "signal_input_mismatch",
            "validation_blocker": f"{clean_id} requires {capability.get('signal_input')} history.",
        }

    values = [float(value) for value in closes]
    settings = dict(params or {})
    if len(values) < 30 or price <= 0:
        return {"action": "HOLD", "reason": "insufficient_history"}

    if clean_id == "dual_ma":
        fast_window = max(2, int(settings.get("fast_window") or 20))
        slow_window = max(fast_window + 1, int(settings.get("slow_window") or 60))
        if len(values) < slow_window:
            return {"action": "HOLD", "reason": "insufficient_history"}
        fast = _average(values[-fast_window:])
        slow = _average(values[-slow_window:])
        if fast > slow and not has_position:
            return {"action": "BUY", "reason": "fast_ma_above_slow_ma"}
        if fast < slow and has_position:
            return {"action": "EXIT", "reason": "fast_ma_below_slow_ma"}

    elif clean_id == "bollinger":
        window = max(10, int(settings.get("window") or 20))
        std_mult = max(0.5, float(settings.get("std_mult") or 2.0))
        recent = values[-window:]
        mid = _average(recent)
        band = _average([(value - mid) ** 2 for value in recent]) ** 0.5 * std_mult
        if price < mid - band and not has_position:
            return {"action": "BUY", "reason": "close_below_lower_band"}
        if price > mid and has_position:
            return {"action": "EXIT", "reason": "close_reverted_above_mid_band"}

    elif clean_id == "macd":
        fast = max(2, int(settings.get("fast") or 12))
        slow = max(fast + 1, int(settings.get("slow") or 26))
        signal_window = max(2, int(settings.get("signal") or 9))
        previous_macd, previous_signal, current_macd, current_signal = _macd_state(values, fast, slow, signal_window)
        histogram = current_macd - current_signal
        previous_histogram = previous_macd - previous_signal
        if current_macd > current_signal and histogram > 0 and histogram >= previous_histogram and not has_position:
            return {"action": "BUY", "reason": "macd_bullish_and_strengthening"}
        if current_macd < current_signal and has_position:
            return {"action": "EXIT", "reason": "macd_bearish_cross"}

    elif clean_id == "rsi":
        window = max(5, int(settings.get("window") or 14))
        oversold = float(settings.get("oversold") or 30)
        overbought = float(settings.get("overbought") or 70)
        if len(values) < window + 1:
            return {"action": "HOLD", "reason": "insufficient_history"}
        changes = [current - previous for previous, current in zip(values[-window - 1:-1], values[-window:])]
        gains = [max(change, 0.0) for change in changes]
        losses = [abs(min(change, 0.0)) for change in changes]
        average_loss = _average(losses)
        rsi = 100.0 if average_loss <= 1e-12 else 100.0 - 100.0 / (1.0 + _average(gains) / average_loss)
        if rsi < oversold and not has_position:
            return {"action": "BUY", "reason": f"rsi_oversold:{rsi:.2f}"}
        if rsi > overbought and has_position:
            return {"action": "EXIT", "reason": f"rsi_overbought:{rsi:.2f}"}

    elif clean_id == "livermore":
        pivot_window = max(20, int(settings.get("pivot_window") or 60))
        confirm_pct = max(0.0, float(settings.get("confirm_pct") or 0.006))
        if len(values) < pivot_window + 1:
            return {"action": "HOLD", "reason": "insufficient_history"}
        pivot_high = max(values[-pivot_window - 1:-1])
        defensive_window = min(30, pivot_window)
        pivot_low = min(values[-defensive_window - 1:-1])
        if not has_position and price > pivot_high * (1.0 + confirm_pct):
            return {"action": "BUY", "reason": "livermore_pivot_breakout"}
        if has_position and price < pivot_low * 0.995:
            return {"action": "EXIT", "reason": "livermore_defensive_pivot_break"}

    elif clean_id == "turtle":
        entry_window = max(10, int(settings.get("entry_window") or 20))
        exit_window = max(5, int(settings.get("exit_window") or 10))
        if len(values) < max(entry_window, exit_window) + 1:
            return {"action": "HOLD", "reason": "insufficient_history"}
        entry_high = max(values[-entry_window - 1:-1])
        exit_low = min(values[-exit_window - 1:-1])
        if not has_position and price > entry_high:
            return {"action": "BUY", "reason": "turtle_entry_channel_breakout"}
        if has_position and price < exit_low:
            return {"action": "EXIT", "reason": "turtle_exit_channel_break"}

    elif clean_id == "darvas":
        box_window = max(20, int(settings.get("box_window") or 40))
        confirm_pct = max(0.0, float(settings.get("confirm_pct") or 0.004))
        if len(values) < box_window + 1:
            return {"action": "HOLD", "reason": "insufficient_history"}
        box_high = max(values[-box_window - 1:-1])
        box_low = min(values[-box_window - 1:-1])
        if not has_position and price > box_high * (1.0 + confirm_pct):
            return {"action": "BUY", "reason": "darvas_box_breakout"}
        if has_position and price < box_low:
            return {"action": "EXIT", "reason": "darvas_box_failure"}

    elif clean_id == "momentum":
        window = max(5, int(settings.get("window") or 20))
        threshold = max(0.0, float(settings.get("threshold") or 0.015))
        if len(values) < window + 1:
            return {"action": "HOLD", "reason": "insufficient_history"}
        momentum = price / max(values[-window - 1], 1e-12) - 1.0
        if momentum > threshold and not has_position:
            return {"action": "BUY", "reason": f"momentum_breakout:{momentum:.6f}"}
        if momentum < -threshold and has_position:
            return {"action": "EXIT", "reason": f"momentum_reversal:{momentum:.6f}"}

    return {"action": "HOLD", "reason": "no_signal"}


def _normalized_bars(bars: list[dict[str, Any]]) -> list[dict[str, float]] | None:
    normalized: list[dict[str, float]] = []
    for row in bars:
        try:
            item = {
                "open": float(row.get("open")),
                "high": float(row.get("high")),
                "low": float(row.get("low")),
                "close": float(row.get("close")),
                "volume": float(row.get("volume")),
            }
        except (AttributeError, TypeError, ValueError):
            return None
        if (
            not all(math.isfinite(value) for value in item.values())
            or
            min(item["open"], item["high"], item["low"], item["close"]) <= 0
            or item["volume"] < 0
            or item["high"] < max(item["open"], item["close"], item["low"])
            or item["low"] > min(item["open"], item["close"], item["high"])
        ):
            return None
        normalized.append(item)
    return normalized


def _average_true_range(values: list[dict[str, float]], window: int) -> float:
    true_ranges: list[float] = []
    for index in range(len(values) - window, len(values)):
        previous_close = values[index - 1]["close"]
        row = values[index]
        true_ranges.append(max(
            row["high"] - row["low"],
            abs(row["high"] - previous_close),
            abs(row["low"] - previous_close),
        ))
    return _average(true_ranges)


def _trend_pullback_signal(
    values: list[dict[str, float]],
    *,
    has_position: bool,
    entry_price: float,
    settings: dict[str, Any],
) -> dict[str, Any]:
    trend_window = max(60, int(settings.get("trend_window") or 100))
    fast_window = max(10, int(settings.get("fast_window") or 20))
    breakout_window = max(10, int(settings.get("breakout_window") or 20))
    exit_window = max(5, int(settings.get("exit_window") or 10))
    volume_window = max(10, int(settings.get("volume_window") or 20))
    atr_window = max(5, int(settings.get("atr_window") or 14))
    required = max(
        trend_window + 1,
        fast_window + 1,
        breakout_window + 1,
        exit_window + 1,
        volume_window + 1,
        atr_window + 1,
    )
    if len(values) < required:
        return {"action": "HOLD", "reason": "insufficient_history"}

    current = values[-1]
    previous = values[-2]
    closes = [row["close"] for row in values]
    fast_ma = _average(closes[-fast_window:])
    previous_fast_ma = _average(closes[-fast_window - 1:-1])
    trend_ma = _average(closes[-trend_window:])
    previous_trend_ma = _average(closes[-trend_window - 1:-1])
    prior_breakout_high = max(row["high"] for row in values[-breakout_window - 1:-1])
    prior_exit_low = min(row["low"] for row in values[-exit_window - 1:-1])
    average_volume = _average([row["volume"] for row in values[-volume_window - 1:-1]])
    volume_ratio = current["volume"] / average_volume if average_volume > 0 else 0.0
    atr = _average_true_range(values, atr_window)
    atr_pct = atr / max(current["close"], 1e-12)
    extension_atr = (current["close"] - fast_ma) / max(atr, 1e-12)

    trend_aligned = current["close"] > trend_ma and fast_ma > trend_ma
    trend_rising = trend_ma > previous_trend_ma
    volatility_valid = 0.008 <= atr_pct <= 0.08
    not_overextended = extension_atr <= 2.0
    breakout = current["close"] > prior_breakout_high and volume_ratio >= 1.10
    pullback_touched = (
        previous["low"] <= previous_fast_ma * 1.005
        and previous["close"] >= previous_trend_ma * 0.98
    )
    pullback_reclaimed = (
        pullback_touched
        and current["close"] > fast_ma
        and current["close"] > current["open"]
        and volume_ratio >= 0.85
    )
    evidence = {
        "close": round(current["close"], 8),
        "fast_ma": round(fast_ma, 8),
        "trend_ma": round(trend_ma, 8),
        "previous_trend_ma": round(previous_trend_ma, 8),
        "prior_breakout_high": round(prior_breakout_high, 8),
        "prior_exit_low": round(prior_exit_low, 8),
        "volume_ratio": round(volume_ratio, 4),
        "atr": round(atr, 8),
        "atr_pct": round(atr_pct, 6),
        "extension_atr": round(extension_atr, 4),
    }

    if has_position:
        atr_stop = entry_price > 0 and current["close"] < entry_price - 2.0 * atr
        fast_break_confirmed = current["close"] < fast_ma and previous["close"] < previous_fast_ma
        structure_break = current["close"] < prior_exit_low
        regime_break = current["close"] < trend_ma
        exit_checks = {
            "atr_stop": atr_stop,
            "fast_break_confirmed": fast_break_confirmed,
            "structure_break": structure_break,
            "regime_break": regime_break,
        }
        if any(exit_checks.values()):
            reason = next(
                name for name in ("atr_stop", "regime_break", "structure_break", "fast_break_confirmed")
                if exit_checks[name]
            )
            return {
                "action": "EXIT",
                "reason": f"trend_pullback_{reason}",
                "evidence": evidence,
                "checks": exit_checks,
            }
        return {
            "action": "HOLD",
            "reason": "trend_pullback_position_intact",
            "evidence": evidence,
            "checks": exit_checks,
        }

    entry_checks = {
        "trend_aligned": trend_aligned,
        "trend_rising": trend_rising,
        "volatility_valid": volatility_valid,
        "not_overextended": not_overextended,
        "breakout": breakout,
        "pullback_reclaimed": pullback_reclaimed,
    }
    if (
        trend_aligned
        and trend_rising
        and volatility_valid
        and not_overextended
        and (breakout or pullback_reclaimed)
    ):
        return {
            "action": "BUY",
            "reason": "trend_pullback_breakout" if breakout else "trend_pullback_reclaim",
            "evidence": evidence,
            "checks": entry_checks,
        }
    return {
        "action": "HOLD",
        "reason": "trend_pullback_wait",
        "evidence": evidence,
        "checks": entry_checks,
    }


def _squeeze_breakout_signal(
    values: list[dict[str, float]],
    *,
    has_position: bool,
    entry_price: float,
    settings: dict[str, Any],
) -> dict[str, Any]:
    atr_short_window = max(3, int(settings.get("atr_short_window") or 10))
    atr_long_window = max(atr_short_window + 5, int(settings.get("atr_long_window") or 50))
    volume_short_window = max(3, int(settings.get("volume_short_window") or 10))
    volume_long_window = max(volume_short_window + 5, int(settings.get("volume_long_window") or 50))
    breakout_window = max(10, int(settings.get("breakout_window") or 20))
    trend_window = max(30, int(settings.get("trend_window") or 100))
    exit_window = max(5, int(settings.get("exit_window") or 15))
    squeeze_atr_ratio = max(0.1, float(settings.get("squeeze_atr_ratio") or 0.70))
    volume_contraction_ratio = max(0.1, float(settings.get("volume_contraction_ratio") or 0.75))
    range_expansion_ratio = max(1.0, float(settings.get("range_expansion_ratio") or 1.40))
    volume_expansion_ratio = max(1.0, float(settings.get("volume_expansion_ratio") or 1.35))
    max_breakout_atr = max(0.25, float(settings.get("max_breakout_atr") or 2.0))
    atr_stop_mult = max(0.5, float(settings.get("atr_stop_mult") or 2.5))
    required = max(
        atr_long_window + 2,
        volume_long_window + 1,
        breakout_window + 1,
        trend_window + 2,
        exit_window + 1,
    )
    if len(values) < required:
        return {"action": "HOLD", "reason": "insufficient_history"}

    current = values[-1]
    previous = values[-2]
    prior = values[:-1]
    closes = [row["close"] for row in values]
    short_atr = _average_true_range(prior, atr_short_window)
    long_atr = _average_true_range(prior, atr_long_window)
    short_volume = _average([row["volume"] for row in prior[-volume_short_window:]])
    long_volume = _average([row["volume"] for row in prior[-volume_long_window:]])
    prior_breakout_high = max(row["high"] for row in prior[-breakout_window:])
    prior_exit_low = min(row["low"] for row in prior[-exit_window:])
    trend_ma = _average(closes[-trend_window - 1:-1])
    previous_trend_ma = _average(closes[-trend_window - 2:-2])
    current_range = max(
        current["high"] - current["low"],
        abs(current["high"] - previous["close"]),
        abs(current["low"] - previous["close"]),
    )
    atr_compression = short_atr / max(long_atr, 1e-12)
    volume_contraction = short_volume / max(long_volume, 1e-12)
    range_expansion = current_range / max(short_atr, 1e-12)
    volume_expansion = current["volume"] / max(short_volume, 1e-12)
    breakout_extension_atr = (
        current["close"] - prior_breakout_high
    ) / max(short_atr, 1e-12)
    evidence = {
        "close": round(current["close"], 8),
        "prior_breakout_high": round(prior_breakout_high, 8),
        "prior_exit_low": round(prior_exit_low, 8),
        "trend_ma": round(trend_ma, 8),
        "previous_trend_ma": round(previous_trend_ma, 8),
        "short_atr": round(short_atr, 8),
        "long_atr": round(long_atr, 8),
        "atr_compression_ratio": round(atr_compression, 6),
        "volume_contraction_ratio": round(volume_contraction, 6),
        "range_expansion_ratio": round(range_expansion, 6),
        "volume_expansion_ratio": round(volume_expansion, 6),
        "breakout_extension_atr": round(breakout_extension_atr, 6),
    }

    if has_position:
        exit_checks = {
            "atr_stop": entry_price > 0 and current["close"] < entry_price - atr_stop_mult * long_atr,
            "structure_break": current["close"] < prior_exit_low,
            "trend_break": current["close"] < trend_ma and trend_ma <= previous_trend_ma,
        }
        if any(exit_checks.values()):
            reason = next(
                name for name in ("atr_stop", "structure_break", "trend_break")
                if exit_checks[name]
            )
            return {
                "action": "EXIT",
                "reason": f"squeeze_breakout_{reason}",
                "evidence": evidence,
                "checks": exit_checks,
            }
        return {
            "action": "HOLD",
            "reason": "squeeze_breakout_position_intact",
            "evidence": evidence,
            "checks": exit_checks,
        }

    entry_checks = {
        "atr_compressed": atr_compression <= squeeze_atr_ratio,
        "volume_contracted": volume_contraction <= volume_contraction_ratio,
        "price_breakout": current["close"] > prior_breakout_high,
        "range_expanded": range_expansion >= range_expansion_ratio,
        "volume_expanded": volume_expansion >= volume_expansion_ratio,
        "positive_close": current["close"] > current["open"],
        "trend_guard": current["close"] > trend_ma,
        "not_overextended": 0 < breakout_extension_atr <= max_breakout_atr,
    }
    if all(entry_checks.values()):
        return {
            "action": "BUY",
            "reason": "squeeze_breakout_confirmed",
            "evidence": evidence,
            "checks": entry_checks,
        }
    return {
        "action": "HOLD",
        "reason": "squeeze_breakout_wait",
        "evidence": evidence,
        "checks": entry_checks,
    }


def rolling_bar_strategy_signal(
    strategy_id: str,
    bars: list[dict[str, Any]],
    price: float,
    has_position: bool,
    entry_price: float = 0.0,
    last_scale_price: float = 0.0,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del last_scale_price
    clean_id = str(strategy_id or "").strip().lower()
    capability = strategy_validation_capability(clean_id)
    if not capability["known"]:
        return {"action": "HOLD", "reason": "unsupported_strategy", "validation_blocker": capability["blocker"]}
    if not capability["backtest_supported"]:
        return {"action": "HOLD", "reason": "unvalidated_stateful_strategy", "validation_blocker": capability["blocker"]}
    if capability.get("signal_input") != "BARS":
        return {
            "action": "HOLD",
            "reason": "signal_input_mismatch",
            "validation_blocker": f"{clean_id} requires {capability.get('signal_input')} history.",
        }
    if clean_id not in {"volume_trend", "trend_pullback", "squeeze_breakout"}:
        return {"action": "HOLD", "reason": "unsupported_bar_strategy"}

    values = _normalized_bars(list(bars or []))
    if values is None:
        return {"action": "HOLD", "reason": "invalid_bar_history"}
    settings = dict(params or {})
    if clean_id == "trend_pullback":
        return _trend_pullback_signal(
            values,
            has_position=has_position,
            entry_price=float(entry_price or 0.0),
            settings=settings,
        )
    if clean_id == "squeeze_breakout":
        return _squeeze_breakout_signal(
            values,
            has_position=has_position,
            entry_price=float(entry_price or 0.0),
            settings=settings,
        )

    trend_window = max(30, int(settings.get("trend_window") or 100))
    fast_window = max(5, int(settings.get("fast_window") or 20))
    breakout_window = max(10, int(settings.get("breakout_window") or 40))
    exit_window = max(5, int(settings.get("exit_window") or 20))
    volume_window = max(5, int(settings.get("volume_window") or 20))
    atr_window = max(5, int(settings.get("atr_window") or 14))
    volume_ratio_threshold = max(0.5, float(settings.get("volume_ratio") or 1.1))
    min_atr_pct = max(0.0, float(settings.get("min_atr_pct") or 0.01))
    max_atr_pct = max(min_atr_pct, float(settings.get("max_atr_pct") or 0.08))
    max_extension_pct = max(0.0, float(settings.get("max_extension_pct") or 0.12))
    required = max(trend_window, fast_window, breakout_window + 1, exit_window + 1, volume_window + 1, atr_window + 1)
    if len(values) < required or price <= 0:
        return {"action": "HOLD", "reason": "insufficient_history"}

    closes = [row["close"] for row in values]
    current = values[-1]
    fast_ma = _average(closes[-fast_window:])
    trend_ma = _average(closes[-trend_window:])
    prior_high = max(row["high"] for row in values[-breakout_window - 1:-1])
    prior_exit_low = min(row["low"] for row in values[-exit_window - 1:-1])
    prior_volumes = [row["volume"] for row in values[-volume_window - 1:-1]]
    average_volume = _average(prior_volumes)
    volume_ratio = current["volume"] / average_volume if average_volume > 0 else 0.0
    atr_pct = _average_true_range(values, atr_window) / max(current["close"], 1e-12)
    extension_pct = current["close"] / max(fast_ma, 1e-12) - 1.0
    evidence = {
        "close": round(current["close"], 8),
        "prior_breakout_high": round(prior_high, 8),
        "fast_ma": round(fast_ma, 8),
        "trend_ma": round(trend_ma, 8),
        "volume_ratio": round(volume_ratio, 4),
        "atr_pct": round(atr_pct, 6),
        "extension_pct": round(extension_pct, 6),
    }

    if has_position:
        if current["close"] < prior_exit_low:
            return {"action": "EXIT", "reason": "volume_trend_structure_break", "evidence": evidence}
        return {"action": "HOLD", "reason": "volume_trend_position_intact", "evidence": evidence}

    entry_checks = {
        "price_breakout": current["close"] > prior_high,
        "trend_aligned": fast_ma > trend_ma and current["close"] > trend_ma,
        "volume_confirmed": volume_ratio >= volume_ratio_threshold,
        "volatility_valid": min_atr_pct <= atr_pct <= max_atr_pct,
        "not_overextended": extension_pct <= max_extension_pct,
    }
    if all(entry_checks.values()):
        return {
            "action": "BUY",
            "reason": "volume_trend_breakout",
            "evidence": evidence,
            "checks": entry_checks,
        }
    return {
        "action": "HOLD",
        "reason": "volume_trend_wait",
        "evidence": evidence,
        "checks": entry_checks,
    }


def build_strategy_signal_fn(
    strategy_id: str,
    params: dict[str, Any] | None = None,
) -> Callable[[list[Any], float, bool, float, float], dict[str, Any]]:
    frozen_params = json.loads(json.dumps(dict(params or {}), ensure_ascii=True, sort_keys=True, default=str))
    signal_input = strategy_signal_input(strategy_id)

    def signal(
        history: list[Any],
        price: float,
        has_position: bool,
        entry_price: float,
        last_scale_price: float,
    ) -> dict[str, Any]:
        if signal_input == "BARS":
            return rolling_bar_strategy_signal(
                strategy_id,
                history,
                price,
                has_position,
                entry_price,
                last_scale_price,
                params=frozen_params,
            )
        return rolling_strategy_signal(
            strategy_id,
            history,
            price,
            has_position,
            entry_price,
            last_scale_price,
            params=frozen_params,
        )

    return signal


def strategy_signal_fingerprint(strategy_id: str, params: dict[str, Any]) -> str:
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    payload = {
        "strategy_id": str(strategy_id or "").lower(),
        "params": params,
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "source_hash": source_hash,
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
