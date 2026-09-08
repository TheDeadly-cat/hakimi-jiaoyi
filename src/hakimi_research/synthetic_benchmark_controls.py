from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
)


POLICY_SCHEMA_VERSION = "synthetic-benchmark-control-policy-v1"
NO_SKILL_SCHEMA_VERSION = "synthetic-no-skill-control-distribution-v1"
VOLATILITY_SCHEMA_VERSION = "synthetic-volatility-matched-buy-and-hold-v1"
COMPARISON_SCHEMA_VERSION = "synthetic-strategy-control-comparison-v1"
NO_SKILL_PATH_COUNT = 16
NO_SKILL_SEED_IDS = tuple(
    f"hash-no-skill-seed-{index:02d}" for index in range(NO_SKILL_PATH_COUNT)
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticBenchmarkControlError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticBenchmarkControlError(f"{path}: {message}")


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _decimal(value: float, path: str) -> str:
    if type(value) is not float or not math.isfinite(value):
        _fail(path, "must be a finite exact float")
    if value == 0.0:
        return "0"
    return format(value, ".17g")


def _number(value: Any, path: str) -> float:
    if type(value) not in (int, float):
        _fail(path, "must be an exact non-bool number")
    numeric = float(value)
    if not math.isfinite(numeric):
        _fail(path, "must be finite")
    return numeric


def _period_returns(result: dict[str, Any], path: str) -> tuple[list[str], list[float]]:
    if type(result) is not dict:
        _fail(path, "must be an exact result dict")
    curve = result.get("equity_curve")
    if type(curve) is not list or len(curve) < 3:
        _fail(f"{path}.equity_curve", "must contain at least three points")
    times: list[str] = []
    equities: list[float] = []
    previous_time: str | None = None
    for index, point in enumerate(curve):
        point_path = f"{path}.equity_curve[{index}]"
        if type(point) is not dict or set(point) != {"time", "equity"}:
            _fail(point_path, "must contain exactly time and equity")
        timestamp = point["time"]
        if type(timestamp) is not str or not timestamp:
            _fail(f"{point_path}.time", "must be a non-empty exact str")
        if previous_time is not None and timestamp <= previous_time:
            _fail(f"{point_path}.time", "must be strictly increasing")
        previous_time = timestamp
        equity = _number(point["equity"], f"{point_path}.equity")
        if equity <= 0.0:
            _fail(f"{point_path}.equity", "must be positive")
        times.append(timestamp)
        equities.append(equity)
    returns = [
        current / previous - 1.0
        for previous, current in zip(equities, equities[1:])
    ]
    if any(not math.isfinite(value) or value <= -1.0 for value in returns):
        _fail(f"{path}.equity_curve", "produced invalid simple returns")
    return times[1:], returns


def _sample_std(values: list[float], path: str) -> float:
    if type(values) is not list or len(values) < 2:
        _fail(path, "requires at least two values")
    center = math.fsum(values) / len(values)
    variance = math.fsum((value - center) ** 2 for value in values) / (
        len(values) - 1
    )
    if not math.isfinite(variance) or variance < 0.0:
        _fail(path, "sample variance must be finite and non-negative")
    return math.sqrt(variance)


def _compound(values: list[float], path: str) -> float:
    if type(values) is not list or not values:
        _fail(path, "must contain returns")
    growth = 1.0
    for index, value in enumerate(values):
        if type(value) is not float or not math.isfinite(value) or value <= -1.0:
            _fail(f"{path}[{index}]", "return must be finite and greater than -1")
        growth *= 1.0 + value
    if not math.isfinite(growth) or growth <= 0.0:
        _fail(path, "invalid compounded growth")
    return growth - 1.0


def _type7_quantile(values: list[float], probability: float, path: str) -> float:
    if not values:
        _fail(path, "requires values")
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def synthetic_benchmark_control_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_partition": "FROZEN",
        "source_data": "VERIFIED_SYNTHETIC_BASELINE_FIXTURE",
        "execution_model": "SOURCE_BACKTEST_NEXT_BAR_OPEN",
        "cost_model": "SOURCE_BASE_FEE_AND_SLIPPAGE_1X",
        "position_fraction": "0.25",
        "simple_ma_rule": {
            "lookback": 20,
            "entry": "CLOSE_T>MEAN(CLOSE_T-19..CLOSE_T)",
            "exit": "CLOSE_T<=MEAN(CLOSE_T-19..CLOSE_T)",
        },
        "simple_breakout_rule": {
            "lookback": 20,
            "entry": "CLOSE_T>MAX(CLOSE_T-20..CLOSE_T-1)",
            "exit": "CLOSE_T<MIN(CLOSE_T-20..CLOSE_T-1)",
        },
        "no_skill_rule": {
            "path_count": NO_SKILL_PATH_COUNT,
            "seed_ids": list(NO_SKILL_SEED_IDS),
            "action_digest": "SHA256(SEED_ID|SIGNAL_TIME|WINDOW_LENGTH)",
            "action_bucket": "DIGEST_BYTE_0_MOD_3:BUY_EXIT_HOLD",
            "all_paths_retained": True,
            "selected_path_id": None,
            "summary_quantiles": "TYPE7_MIN_Q25_MEDIAN_Q75_MAX",
        },
        "equal_volatility_projection": {
            "target": "EACH_REGISTERED_STRATEGY_FROZEN_1X_REALISED_VOLATILITY",
            "source": "BUY_AND_HOLD_FROZEN_1X_PERIOD_RETURNS",
            "multiplier": "STRATEGY_SAMPLE_VOLATILITY/BUY_AND_HOLD_SAMPLE_VOLATILITY",
            "projection": "BUY_AND_HOLD_SIMPLE_RETURN_T*MULTIPLIER",
            "financing_model": "NOT_MODELLED",
            "margin_model": "NOT_MODELLED",
            "executable_claim": False,
        },
        "comparison_metric": "TOTAL_RETURN_ARITHMETIC_DIFFERENCE",
        "ranking_performed": False,
        "parameter_search_performed": False,
        "post_frozen_tuning": False,
        "decision_threshold": None,
        "formal_inference_claimed": False,
    }
    return _seal(policy, "policy_sha256")


def build_no_skill_control_distribution(
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_trial_return_matrix_sha256(runs)
    if type(runs) is not list or len(runs) != NO_SKILL_PATH_COUNT:
        _fail("runs", f"must contain exactly {NO_SKILL_PATH_COUNT} paths")
    path_records: list[dict[str, Any]] = []
    values: list[float] = []
    for index, seed_id in enumerate(NO_SKILL_SEED_IDS):
        run = runs[index]
        expected_control_id = f"hash_no_skill_{index:02d}"
        if (
            type(run) is not dict
            or run.get("control_id") != expected_control_id
            or run.get("seed_id") != seed_id
        ):
            _fail(f"runs[{index}]", "path identity or order mismatch")
        result = run.get("result")
        if type(result) is not dict:
            _fail(f"runs[{index}].result", "must be an exact dict")
        total_return = _number(
            result.get("total_return"), f"runs[{index}].result.total_return"
        )
        values.append(total_return)
        path_records.append(
            _seal(
                {
                    "control_id": expected_control_id,
                    "seed_id": seed_id,
                    "source_run_sha256": run.get("run_sha256"),
                    "total_return": _decimal(
                        total_return, f"runs[{index}].total_return"
                    ),
                },
                "path_record_sha256",
            )
        )
    summary = {
        "minimum": _decimal(min(values), "summary.minimum"),
        "q25_type7": _decimal(
            _type7_quantile(values, 0.25, "summary.q25"), "summary.q25"
        ),
        "median_type7": _decimal(
            _type7_quantile(values, 0.5, "summary.median"), "summary.median"
        ),
        "q75_type7": _decimal(
            _type7_quantile(values, 0.75, "summary.q75"), "summary.q75"
        ),
        "maximum": _decimal(max(values), "summary.maximum"),
    }
    _seal(summary, "summary_sha256")
    distribution = {
        "schema_version": NO_SKILL_SCHEMA_VERSION,
        "evidence_state": "OBSERVED",
        "policy_sha256": synthetic_benchmark_control_policy_v1()["policy_sha256"],
        "path_count": NO_SKILL_PATH_COUNT,
        "selected_path_id": None,
        "all_paths_retained": True,
        "path_records": path_records,
        "summary": summary,
        "interpretation": "SYNTHETIC_NO_SKILL_CONTROL_DISTRIBUTION_ONLY",
        "authority": dict(_AUTHORITY),
    }
    return _seal(distribution, "distribution_sha256")


def verify_no_skill_control_distribution(
    distribution: dict[str, Any], runs: list[dict[str, Any]]
) -> dict[str, Any]:
    if type(distribution) is not dict:
        _fail("distribution", "must be an exact dict")
    canonical_trial_return_matrix_sha256(distribution)
    expected = build_no_skill_control_distribution(runs)
    if distribution != expected:
        _fail("distribution", "must match all source-bound no-skill paths")
    return {
        "state": "OBSERVED",
        "distribution_sha256": distribution["distribution_sha256"],
        "path_count": NO_SKILL_PATH_COUNT,
        "selected_path_id": None,
        "all_paths_retained": True,
        "authority": dict(_AUTHORITY),
    }


def build_volatility_matched_buy_and_hold_projection(
    strategy_report: dict[str, Any], buy_and_hold_run: dict[str, Any]
) -> dict[str, Any]:
    canonical_trial_return_matrix_sha256(strategy_report)
    canonical_trial_return_matrix_sha256(buy_and_hold_run)
    strategy_id = strategy_report.get("strategy_id")
    if type(strategy_id) is not str or not strategy_id:
        _fail("strategy_report.strategy_id", "must be a non-empty exact str")
    runs = strategy_report.get("runs")
    if type(runs) is not dict or type(runs.get("frozen_1x")) is not dict:
        _fail("strategy_report.runs.frozen_1x", "missing")
    strategy_run = runs["frozen_1x"]
    strategy_times, strategy_returns = _period_returns(
        strategy_run.get("result"), "strategy_run.result"
    )
    benchmark_times, benchmark_returns = _period_returns(
        buy_and_hold_run.get("result"), "buy_and_hold_run.result"
    )
    if strategy_times != benchmark_times:
        _fail("observation_times", "strategy and buy-and-hold must align")
    strategy_vol = _sample_std(strategy_returns, "strategy_returns") * math.sqrt(252.0)
    benchmark_vol = _sample_std(benchmark_returns, "benchmark_returns") * math.sqrt(252.0)
    if benchmark_vol <= 0.0:
        _fail("benchmark_volatility", "must be positive")
    multiplier = strategy_vol / benchmark_vol
    projected_returns = [value * multiplier for value in benchmark_returns]
    if any(value <= -1.0 or not math.isfinite(value) for value in projected_returns):
        _fail("projected_returns", "linear scaling produced invalid return")
    projected_vol = _sample_std(projected_returns, "projected_returns") * math.sqrt(252.0)
    source_binding = {
        "strategy_report_sha256": strategy_report.get("report_sha256"),
        "strategy_frozen_run_sha256": strategy_run.get("run_sha256"),
        "buy_and_hold_run_sha256": buy_and_hold_run.get("run_sha256"),
        "observation_times_sha256": canonical_trial_return_matrix_sha256(
            strategy_times
        ),
        "strategy_returns_sha256": canonical_trial_return_matrix_sha256(
            [_decimal(value, "strategy_return") for value in strategy_returns]
        ),
        "buy_and_hold_returns_sha256": canonical_trial_return_matrix_sha256(
            [_decimal(value, "buy_and_hold_return") for value in benchmark_returns]
        ),
    }
    _seal(source_binding, "source_binding_sha256")
    projection = {
        "schema_version": VOLATILITY_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "evidence_state": "OBSERVED_WITH_GAPS",
        "policy_sha256": synthetic_benchmark_control_policy_v1()["policy_sha256"],
        "source_binding": source_binding,
        "observation_count": len(strategy_returns),
        "strategy_annualised_sample_volatility": _decimal(
            strategy_vol, "strategy_volatility"
        ),
        "buy_and_hold_annualised_sample_volatility": _decimal(
            benchmark_vol, "buy_and_hold_volatility"
        ),
        "scaling_multiplier": _decimal(multiplier, "scaling_multiplier"),
        "projected_annualised_sample_volatility": _decimal(
            projected_vol, "projected_volatility"
        ),
        "strategy_curve_compounded_return": _decimal(
            _compound(strategy_returns, "strategy_returns"),
            "strategy_curve_compounded_return",
        ),
        "buy_and_hold_curve_compounded_return": _decimal(
            _compound(benchmark_returns, "benchmark_returns"),
            "buy_and_hold_curve_compounded_return",
        ),
        "volatility_matched_buy_and_hold_compounded_return": _decimal(
            _compound(projected_returns, "projected_returns"),
            "volatility_matched_buy_and_hold_compounded_return",
        ),
        "executable_claim": False,
        "financing_modelled": False,
        "margin_modelled": False,
        "interpretation": "EX_POST_SYNTHETIC_VOLATILITY_MATCHED_PROJECTION_ONLY",
        "authority": dict(_AUTHORITY),
    }
    return _seal(projection, "projection_sha256")


def verify_volatility_matched_buy_and_hold_projection(
    projection: dict[str, Any],
    strategy_report: dict[str, Any],
    buy_and_hold_run: dict[str, Any],
) -> dict[str, Any]:
    if type(projection) is not dict:
        _fail("projection", "must be an exact dict")
    canonical_trial_return_matrix_sha256(projection)
    expected = build_volatility_matched_buy_and_hold_projection(
        strategy_report, buy_and_hold_run
    )
    if projection != expected:
        _fail("projection", "must match deterministic source-bound projection")
    return {
        "state": "OBSERVED_WITH_GAPS",
        "strategy_id": projection["strategy_id"],
        "projection_sha256": projection["projection_sha256"],
        "observation_count": projection["observation_count"],
        "executable_claim": False,
        "authority": dict(_AUTHORITY),
    }


def build_strategy_control_comparison(
    *,
    strategy_report: dict[str, Any],
    cash_run: dict[str, Any],
    buy_and_hold_run: dict[str, Any],
    simple_ma_run: dict[str, Any],
    simple_breakout_run: dict[str, Any],
    no_skill_distribution: dict[str, Any],
    volatility_projection: dict[str, Any],
) -> dict[str, Any]:
    inputs = [
        strategy_report,
        cash_run,
        buy_and_hold_run,
        simple_ma_run,
        simple_breakout_run,
        no_skill_distribution,
        volatility_projection,
    ]
    canonical_trial_return_matrix_sha256(inputs)
    strategy_id = strategy_report.get("strategy_id")
    strategy_run = strategy_report.get("runs", {}).get("frozen_1x")
    if type(strategy_id) is not str or type(strategy_run) is not dict:
        _fail("strategy_report", "missing strategy identity or frozen run")
    strategy_return = _number(
        strategy_run.get("result", {}).get("total_return"),
        "strategy_report.frozen_1x.total_return",
    )
    controls = {
        "cash": _number(cash_run.get("result", {}).get("total_return"), "cash"),
        "buy_and_hold": _number(
            buy_and_hold_run.get("result", {}).get("total_return"),
            "buy_and_hold",
        ),
        "simple_ma": _number(
            simple_ma_run.get("result", {}).get("total_return"), "simple_ma"
        ),
        "simple_breakout": _number(
            simple_breakout_run.get("result", {}).get("total_return"),
            "simple_breakout",
        ),
        "hash_no_skill_median": float(
            no_skill_distribution["summary"]["median_type7"]
        ),
        "volatility_matched_buy_and_hold": float(
            volatility_projection[
                "volatility_matched_buy_and_hold_compounded_return"
            ]
        ),
    }
    source_binding = {
        "strategy_report_sha256": strategy_report.get("report_sha256"),
        "strategy_frozen_run_sha256": strategy_run.get("run_sha256"),
        "cash_run_sha256": cash_run.get("run_sha256"),
        "buy_and_hold_run_sha256": buy_and_hold_run.get("run_sha256"),
        "simple_ma_run_sha256": simple_ma_run.get("run_sha256"),
        "simple_breakout_run_sha256": simple_breakout_run.get("run_sha256"),
        "no_skill_distribution_sha256": no_skill_distribution.get(
            "distribution_sha256"
        ),
        "volatility_projection_sha256": volatility_projection.get(
            "projection_sha256"
        ),
    }
    _seal(source_binding, "source_binding_sha256")
    comparison = {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "evidence_state": "OBSERVED_WITH_GAPS",
        "policy_sha256": synthetic_benchmark_control_policy_v1()["policy_sha256"],
        "source_binding": source_binding,
        "strategy_frozen_total_return": _decimal(
            strategy_return, "strategy_frozen_total_return"
        ),
        "control_total_returns": {
            key: _decimal(value, f"control_total_returns.{key}")
            for key, value in controls.items()
        },
        "strategy_minus_control_return_deltas": {
            key: _decimal(strategy_return - value, f"return_deltas.{key}")
            for key, value in controls.items()
        },
        "ranking_performed": False,
        "decision_threshold": None,
        "interpretation": "DESCRIPTIVE_SYNTHETIC_CONTROL_COMPARISON_ONLY",
        "authority": dict(_AUTHORITY),
    }
    return _seal(comparison, "comparison_sha256")


def verify_strategy_control_comparison(
    comparison: dict[str, Any], **inputs: Any
) -> dict[str, Any]:
    if type(comparison) is not dict:
        _fail("comparison", "must be an exact dict")
    canonical_trial_return_matrix_sha256(comparison)
    expected = build_strategy_control_comparison(**inputs)
    if comparison != expected:
        _fail("comparison", "must match deterministic source-bound comparison")
    return {
        "state": "OBSERVED_WITH_GAPS",
        "strategy_id": comparison["strategy_id"],
        "comparison_sha256": comparison["comparison_sha256"],
        "control_count": len(comparison["control_total_returns"]),
        "ranking_performed": False,
        "decision_threshold": None,
        "authority": dict(_AUTHORITY),
    }
