"""Versioned fixed benchmark strategies for research-only comparisons."""

from __future__ import annotations

import hashlib

import pandas as pd

from hakimi_research.models import Portfolio, Signal
from hakimi_research.strategies.base import StrategyBase


FIXED_BASELINE_MATRIX_VERSION = "fixed-baseline-matrix-v1"
BENCHMARKS = (
    ("CASH", "cash-benchmark-v1"),
    ("ENGINE_BUY_AND_HOLD", "engine-buy-and-hold-v1"),
    ("FIXED_DUAL_MA", "fixed-dual-ma-5-20-v1"),
    ("FIXED_BREAKOUT", "fixed-breakout-20-v1"),
    ("HASH_NO_SKILL", "hash-no-skill-v1"),
)


def _validate_random_seed(random_seed: int) -> int:
    if type(random_seed) is not int or not 0 <= random_seed <= 2_147_483_647:
        raise ValueError("fixed_baseline_random_seed_invalid")
    return random_seed


def fixed_benchmark_specs(random_seed: int) -> list[dict[str, object]]:
    """Return fresh exact-native preregistered benchmark definitions."""

    seed = _validate_random_seed(random_seed)
    return [
        {
            "benchmark_id": "CASH",
            "strategy_name": "cash_benchmark",
            "version": "cash-benchmark-v1",
            "params": {},
        },
        {
            "benchmark_id": "ENGINE_BUY_AND_HOLD",
            "strategy_name": "engine_buy_and_hold_benchmark",
            "version": "engine-buy-and-hold-v1",
            "params": {},
        },
        {
            "benchmark_id": "FIXED_DUAL_MA",
            "strategy_name": "fixed_dual_ma_benchmark",
            "version": "fixed-dual-ma-5-20-v1",
            "params": {
                "fast_window": 5,
                "slow_window": 20,
                "position_pct": 1.0,
            },
        },
        {
            "benchmark_id": "FIXED_BREAKOUT",
            "strategy_name": "fixed_breakout_benchmark",
            "version": "fixed-breakout-20-v1",
            "params": {
                "lookback": 20,
                "position_pct": 1.0,
            },
        },
        {
            "benchmark_id": "HASH_NO_SKILL",
            "strategy_name": "hash_no_skill_benchmark",
            "version": "hash-no-skill-v1",
            "params": {
                "random_seed": seed,
                "bucket_modulus": 4,
                "buy_bucket": 0,
                "exit_bucket": 1,
                "position_pct": 1.0,
            },
        },
    ]


class _CashBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        return Signal.hold("cash benchmark")


class _EngineBuyAndHoldBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if portfolio.position_qty <= 0:
            return Signal.buy("engine buy-and-hold benchmark", size_pct=1.0)
        return Signal.hold("engine buy-and-hold invested")


class _FixedDualMovingAverageBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        fast_window = self.get("fast_window", 5)
        slow_window = self.get("slow_window", 20)
        position_pct = self.get("position_pct", 1.0)
        close = data["close"]
        if len(close) < slow_window:
            return Signal.hold("fixed dual MA warmup")
        fast_value = float(close.iloc[-fast_window:].mean())
        slow_value = float(close.iloc[-slow_window:].mean())
        if fast_value > slow_value and portfolio.position_qty <= 0:
            return Signal.buy("fixed dual MA above", size_pct=position_pct)
        if fast_value <= slow_value and portfolio.position_qty > 0:
            return Signal.exit("fixed dual MA below or equal")
        return Signal.hold("fixed dual MA unchanged")


class _FixedBreakoutBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        lookback = self.get("lookback", 20)
        position_pct = self.get("position_pct", 1.0)
        if len(data) < lookback + 1:
            return Signal.hold("fixed breakout warmup")
        prior = data.iloc[-(lookback + 1):-1]
        current_close = float(data["close"].iloc[-1])
        prior_high = float(prior["high"].max())
        prior_low = float(prior["low"].min())
        if current_close > prior_high and portfolio.position_qty <= 0:
            return Signal.buy("fixed breakout above prior high", size_pct=position_pct)
        if current_close < prior_low and portfolio.position_qty > 0:
            return Signal.exit("fixed breakout below prior low")
        return Signal.hold("fixed breakout unchanged")


class _HashNoSkillBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        seed = self.get("random_seed", 0)
        modulus = self.get("bucket_modulus", 4)
        buy_bucket = self.get("buy_bucket", 0)
        exit_bucket = self.get("exit_bucket", 1)
        position_pct = self.get("position_pct", 1.0)
        timestamp = pd.Timestamp(data.index[-1]).isoformat()
        digest = hashlib.sha256(f"{seed}|{timestamp}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % modulus
        if bucket == buy_bucket and portfolio.position_qty <= 0:
            return Signal.buy("hash no-skill buy bucket", size_pct=position_pct)
        if bucket == exit_bucket and portfolio.position_qty > 0:
            return Signal.exit("hash no-skill exit bucket")
        return Signal.hold("hash no-skill hold bucket")


def build_fixed_benchmark(benchmark_id: str, random_seed: int) -> StrategyBase:
    """Build one benchmark only from its exact preregistered identity."""

    if type(benchmark_id) is not str:
        raise ValueError("fixed_baseline_benchmark_id_invalid")
    specs = {
        item["benchmark_id"]: item
        for item in fixed_benchmark_specs(random_seed)
    }
    if benchmark_id not in specs:
        raise ValueError("fixed_baseline_benchmark_id_invalid")
    spec = specs[benchmark_id]
    strategy_types = {
        "CASH": _CashBenchmarkStrategy,
        "ENGINE_BUY_AND_HOLD": _EngineBuyAndHoldBenchmarkStrategy,
        "FIXED_DUAL_MA": _FixedDualMovingAverageBenchmarkStrategy,
        "FIXED_BREAKOUT": _FixedBreakoutBenchmarkStrategy,
        "HASH_NO_SKILL": _HashNoSkillBenchmarkStrategy,
    }
    return strategy_types[benchmark_id](
        params=spec["params"],
        name=spec["strategy_name"],
        version=spec["version"],
    )


__all__ = [
    "BENCHMARKS",
    "FIXED_BASELINE_MATRIX_VERSION",
    "build_fixed_benchmark",
    "fixed_benchmark_specs",
]
