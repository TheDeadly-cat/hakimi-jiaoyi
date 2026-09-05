"""Exact, analytical-only volatility-matched research comparisons."""

from __future__ import annotations

import math
import re
from typing import Any


VOLATILITY_MATCHED_COMPARISON_SCHEMA_VERSION = (
    "ex-post-volatility-matched-comparison-v2"
)
VOLATILITY_MATCHED_COMPARISON_ID = "ENGINE_BUY_AND_HOLD_EX_POST_VOLATILITY_MATCH"
VOLATILITY_MATCHED_METHOD_VERSION = "ex-post-volatility-match-v2"
VOLATILITY_MATCHED_ACTIVITY_FLOOR = 1e-12
COMPARISON_AUTHORITY_LOCK = {
    "tradable": False,
    "parameter_selection": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def annualization_factor(market: str, timeframe: str) -> int:
    """Return the canonical Backtest V2 periods-per-year factor."""

    if (
        type(market) is not str
        or not market
        or market != market.strip()
        or type(timeframe) is not str
        or not timeframe
        or timeframe != timeframe.strip()
    ):
        raise ValueError("volatility_comparison_market_timeframe_invalid")
    normalized_market = market.lower()
    normalized_timeframe = timeframe.lower()
    market_days = 252 if normalized_market == "stock" else 365
    minutes_per_day = 390 if normalized_market == "stock" else 24 * 60
    if normalized_timeframe.endswith("m"):
        raw = normalized_timeframe[:-1]
        if not raw.isdigit() or int(raw) < 1:
            raise ValueError("volatility_comparison_timeframe_invalid")
        return int(market_days * minutes_per_day / int(raw))
    if normalized_timeframe.endswith("h"):
        raw = normalized_timeframe[:-1]
        if not raw.isdigit() or int(raw) < 1:
            raise ValueError("volatility_comparison_timeframe_invalid")
        return int(market_days * minutes_per_day / (int(raw) * 60))
    return market_days


def volatility_match_method_spec() -> dict[str, Any]:
    """Return a fresh preregistered analytical method specification."""

    return {
        "comparison_id": VOLATILITY_MATCHED_COMPARISON_ID,
        "method_version": VOLATILITY_MATCHED_METHOD_VERSION,
        "benchmark_id": "ENGINE_BUY_AND_HOLD",
        "roles": ["VALIDATION", "FROZEN_TEST"],
        "cost_scenarios": ["BASE", "DOUBLE_COST", "TRIPLE_COST"],
        "equity_return_definition": "INITIAL_EQUITY_ANCHOR_THEN_SIMPLE_RETURN",
        "volatility_estimator": "SAMPLE_STD_DDOF_1_X_SQRT_ANNUALIZATION_FACTOR",
        "scale_policy": "UNBOUNDED_LINEAR_EX_POST_ANALYTICAL_ONLY",
        "activity_floor_annualized_volatility": "0.000000000001",
        "zero_target_policy": "GAP_NOT_ZERO_FILLED",
        "interpretation": "ANALYTICAL_ONLY_NOT_TRADABLE",
        "tradable": False,
        "parameter_selection_allowed": False,
    }


def _number(value: Any, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"volatility_comparison_{label}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise ValueError(f"volatility_comparison_{label}_invalid")
    return parsed


def _clean(value: float) -> float:
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


def _equity_returns(
    record: dict[str, Any],
    *,
    initial_equity: float,
    label: str,
) -> tuple[list[float], list[str], str]:
    if type(record) is not dict:
        raise ValueError(f"volatility_comparison_{label}_record_invalid")
    result = record.get("result")
    if type(result) is not dict:
        raise ValueError(f"volatility_comparison_{label}_result_invalid")
    reproducibility = result.get("reproducibility")
    if type(reproducibility) is not dict:
        raise ValueError(f"volatility_comparison_{label}_reproducibility_invalid")
    run_hash = reproducibility.get("run_hash")
    if type(run_hash) is not str or _HASH_PATTERN.fullmatch(run_hash) is None:
        raise ValueError(f"volatility_comparison_{label}_run_hash_invalid")
    curve = result.get("equity_curve")
    if type(curve) is not list or len(curve) < 2:
        raise ValueError(f"volatility_comparison_{label}_equity_curve_invalid")
    previous_equity = _number(
        initial_equity,
        label="initial_equity",
        positive=True,
    )
    previous_time = ""
    returns: list[float] = []
    times: list[str] = []
    for point in curve:
        if type(point) is not dict or set(point) != {"time", "equity"}:
            raise ValueError(f"volatility_comparison_{label}_equity_point_invalid")
        timestamp = point["time"]
        if (
            type(timestamp) is not str
            or not timestamp
            or (previous_time and timestamp <= previous_time)
        ):
            raise ValueError(f"volatility_comparison_{label}_equity_time_invalid")
        equity = _number(point["equity"], label="equity", positive=True)
        simple_return = equity / previous_equity - 1.0
        if not math.isfinite(simple_return) or simple_return <= -1:
            raise ValueError(f"volatility_comparison_{label}_return_invalid")
        returns.append(simple_return)
        times.append(timestamp)
        previous_equity = equity
        previous_time = timestamp
    return returns, times, run_hash


def _annualized_volatility(returns: list[float], factor: int) -> float:
    if type(returns) is not list or len(returns) < 2:
        raise ValueError("volatility_comparison_returns_invalid")
    if type(factor) is not int or factor < 1:
        raise ValueError("volatility_comparison_annualization_factor_invalid")
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(max(variance, 0.0)) * math.sqrt(factor)


def annualized_volatility(returns: list[float], factor: int) -> float:
    """Return canonical annualized volatility for exact finite simple returns."""

    if type(returns) is not list:
        raise ValueError("volatility_comparison_returns_invalid")
    parsed: list[float] = []
    for item in returns:
        value = _number(item, label="return")
        if value <= -1:
            raise ValueError("volatility_comparison_return_invalid")
        parsed.append(value)
    return _clean(_annualized_volatility(parsed, factor))


def observed_equity_annualized_volatility(
    record: dict[str, Any],
    *,
    initial_equity: float,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    """Expose a bound equity-grid volatility observation for prior-window calibration."""

    returns, times, run_hash = _equity_returns(
        record,
        initial_equity=initial_equity,
        label="observed",
    )
    factor = annualization_factor(market, timeframe)
    return {
        "run_hash": run_hash,
        "times": list(times),
        "annualization_factor": factor,
        "annualized_volatility": annualized_volatility(returns, factor),
    }


def _compound(returns: list[float]) -> float:
    value = 1.0
    for item in returns:
        value *= 1.0 + item
    return value - 1.0


def build_volatility_matched_comparison(
    strategy_record: dict[str, Any],
    benchmark_record: dict[str, Any],
    *,
    initial_equity: float,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    """Build one ex-post same-volatility observation without execution claims."""

    if type(strategy_record) is not dict or type(benchmark_record) is not dict:
        raise ValueError("volatility_comparison_record_type_invalid")
    role = strategy_record.get("role")
    scenario_id = strategy_record.get("scenario_id")
    if type(role) is not str or type(scenario_id) is not str:
        raise ValueError("volatility_comparison_strategy_identity_invalid")
    if (
        strategy_record.get("run_kind") != "REGISTERED_STRATEGY"
        or benchmark_record.get("run_kind") != "FIXED_BENCHMARK"
        or benchmark_record.get("benchmark_id") != "ENGINE_BUY_AND_HOLD"
        or benchmark_record.get("role") != role
        or benchmark_record.get("scenario_id") != scenario_id
    ):
        raise ValueError("volatility_comparison_source_binding_invalid")

    strategy_returns, strategy_times, strategy_run_hash = _equity_returns(
        strategy_record,
        initial_equity=initial_equity,
        label="strategy",
    )
    benchmark_returns, benchmark_times, benchmark_run_hash = _equity_returns(
        benchmark_record,
        initial_equity=initial_equity,
        label="benchmark",
    )
    if strategy_times != benchmark_times:
        raise ValueError("volatility_comparison_time_grid_mismatch")
    factor = annualization_factor(market, timeframe)
    strategy_volatility = _annualized_volatility(strategy_returns, factor)
    benchmark_volatility = _annualized_volatility(benchmark_returns, factor)
    blockers: list[str] = []
    scale_factor: float | None
    matched_returns: list[float] | None
    if strategy_volatility <= VOLATILITY_MATCHED_ACTIVITY_FLOOR:
        scale_factor = None
        matched_returns = None
        blockers.append(
            "TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR"
        )
    elif benchmark_volatility <= VOLATILITY_MATCHED_ACTIVITY_FLOOR:
        scale_factor = None
        matched_returns = None
        blockers.append("SOURCE_BENCHMARK_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR")
    else:
        scale_factor = strategy_volatility / benchmark_volatility
        candidate = [item * scale_factor for item in benchmark_returns]
        if any(not math.isfinite(item) or item <= -1 for item in candidate):
            matched_returns = None
            blockers.append("SCALED_RETURN_AT_OR_BELOW_MINUS_ONE")
        else:
            matched_returns = candidate

    matched_volatility = None
    matched_return = None
    difference = None
    if matched_returns is not None:
        matched_volatility = _annualized_volatility(matched_returns, factor)
        matched_return = _compound(matched_returns)
        difference = _compound(strategy_returns) - matched_return
    return {
        "schema_version": VOLATILITY_MATCHED_COMPARISON_SCHEMA_VERSION,
        "comparison_id": VOLATILITY_MATCHED_COMPARISON_ID,
        "method_version": VOLATILITY_MATCHED_METHOD_VERSION,
        "role": role,
        "scenario_id": scenario_id,
        "strategy_run_hash": strategy_run_hash,
        "benchmark_id": "ENGINE_BUY_AND_HOLD",
        "benchmark_run_hash": benchmark_run_hash,
        "annualization_factor": factor,
        "activity_floor_annualized_volatility": VOLATILITY_MATCHED_ACTIVITY_FLOOR,
        "strategy_observed_annualized_volatility": _clean(strategy_volatility),
        "benchmark_observed_annualized_volatility": _clean(benchmark_volatility),
        "scale_factor": None if scale_factor is None else _clean(scale_factor),
        "matched_benchmark_annualized_volatility": (
            None if matched_volatility is None else _clean(matched_volatility)
        ),
        "strategy_curve_total_return": _clean(_compound(strategy_returns)),
        "matched_benchmark_curve_total_return": (
            None if matched_return is None else _clean(matched_return)
        ),
        "strategy_minus_matched_benchmark_curve_total_return": (
            None if difference is None else _clean(difference)
        ),
        "comparison_status": "OBSERVED" if not blockers else "GAP",
        "blockers": blockers,
        "interpretation": "ANALYTICAL_ONLY_NOT_TRADABLE",
        "authority": dict(COMPARISON_AUTHORITY_LOCK),
    }


def verify_volatility_matched_comparison(
    value: Any,
    strategy_record: dict[str, Any],
    benchmark_record: dict[str, Any],
    *,
    initial_equity: float,
    market: str,
    timeframe: str,
) -> bool:
    if type(value) is not dict:
        raise ValueError("volatility_comparison_value_type_invalid")
    expected = build_volatility_matched_comparison(
        strategy_record,
        benchmark_record,
        initial_equity=initial_equity,
        market=market,
        timeframe=timeframe,
    )
    if value != expected:
        raise ValueError("volatility_comparison_verification_failed")
    return True


__all__ = [
    "COMPARISON_AUTHORITY_LOCK",
    "VOLATILITY_MATCHED_COMPARISON_ID",
    "VOLATILITY_MATCHED_COMPARISON_SCHEMA_VERSION",
    "VOLATILITY_MATCHED_ACTIVITY_FLOOR",
    "VOLATILITY_MATCHED_METHOD_VERSION",
    "annualization_factor",
    "annualized_volatility",
    "build_volatility_matched_comparison",
    "observed_equity_annualized_volatility",
    "verify_volatility_matched_comparison",
    "volatility_match_method_spec",
]
