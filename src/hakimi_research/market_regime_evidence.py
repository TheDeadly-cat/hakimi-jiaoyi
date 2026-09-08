from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from typing import Any


SCHEMA_VERSION = "market-regime-evidence-v1"
POLICY_SCHEMA_VERSION = "market-regime-policy-v1"
REGIME_IDS = ("BULL", "BEAR", "RANGE", "HIGH_VOLATILITY")
LOOKBACK_BARS = 20
LABEL_LAG_BARS = 1
PERIODS_PER_YEAR = 252
BULL_THRESHOLD = 0.03
BEAR_THRESHOLD = -0.03
HIGH_VOLATILITY_THRESHOLD = 0.20
NO_OBSERVATIONS_GAP = "NO_OBSERVATIONS_UNDER_PREREGISTERED_POLICY"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class MarketRegimeEvidenceError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise MarketRegimeEvidenceError(f"{path}: {message}")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _require_exact_dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    return value


def _require_exact_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an exact list")
    return value


def _require_exact_str(value: Any, path: str) -> str:
    if type(value) is not str:
        _fail(path, "must be an exact str")
    return value


def _require_sha256(value: Any, path: str) -> str:
    text = _require_exact_str(value, path)
    if _SHA256_PATTERN.fullmatch(text) is None:
        _fail(path, "must be a lowercase SHA-256 digest")
    return text


def _require_exact_float(value: Any, path: str, *, positive: bool) -> float:
    if type(value) is not float or not math.isfinite(value):
        _fail(path, "must be a finite exact float")
    if positive and value <= 0.0:
        _fail(path, "must be positive")
    if not positive and value < 0.0:
        _fail(path, "must be non-negative")
    return value


def _normalise_time(value: Any, path: str) -> str:
    text = _require_exact_str(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(path, f"must be an ISO-8601 timestamp: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        _fail(path, "must be timezone-aware UTC")
    return parsed.isoformat()


def _normalise_market_records(records: Any) -> list[dict[str, Any]]:
    values = _require_exact_list(records, "market_records")
    if len(values) <= LOOKBACK_BARS + LABEL_LAG_BARS:
        _fail("market_records", "does not contain enough rows for the fixed policy")
    normalised: list[dict[str, Any]] = []
    previous_time: str | None = None
    expected_keys = {"time", "open", "high", "low", "close", "volume"}
    for index, item in enumerate(values):
        path = f"market_records[{index}]"
        record = _require_exact_dict(item, path)
        if set(record) != expected_keys:
            _fail(path, f"must contain exactly {sorted(expected_keys)}")
        timestamp = _normalise_time(record["time"], f"{path}.time")
        if previous_time is not None and timestamp <= previous_time:
            _fail(f"{path}.time", "must be strictly increasing and unique")
        previous_time = timestamp
        normalised.append(
            {
                "time": timestamp,
                "open": _require_exact_float(record["open"], f"{path}.open", positive=True),
                "high": _require_exact_float(record["high"], f"{path}.high", positive=True),
                "low": _require_exact_float(record["low"], f"{path}.low", positive=True),
                "close": _require_exact_float(record["close"], f"{path}.close", positive=True),
                "volume": _require_exact_float(record["volume"], f"{path}.volume", positive=False),
            }
        )
    return normalised


def _normalise_equity_curve(curve: Any, path: str) -> list[dict[str, Any]]:
    values = _require_exact_list(curve, path)
    if len(values) < 2:
        _fail(path, "must contain at least two observations")
    normalised: list[dict[str, Any]] = []
    previous_time: str | None = None
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        record = _require_exact_dict(item, item_path)
        if set(record) != {"time", "equity"}:
            _fail(item_path, "must contain exactly time and equity")
        timestamp = _normalise_time(record["time"], f"{item_path}.time")
        if previous_time is not None and timestamp <= previous_time:
            _fail(f"{item_path}.time", "must be strictly increasing and unique")
        previous_time = timestamp
        normalised.append(
            {
                "time": timestamp,
                "equity": _require_exact_float(
                    record["equity"], f"{item_path}.equity", positive=True
                ),
            }
        )
    return normalised


def market_regime_policy_v1() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "classifier_inputs": ["close"],
        "lookback_bars": LOOKBACK_BARS,
        "label_lag_bars": LABEL_LAG_BARS,
        "periods_per_year": PERIODS_PER_YEAR,
        "bull_trailing_return_threshold": BULL_THRESHOLD,
        "bear_trailing_return_threshold": BEAR_THRESHOLD,
        "high_volatility_annualized_threshold": HIGH_VOLATILITY_THRESHOLD,
        "precedence": ["HIGH_VOLATILITY", "BULL", "BEAR", "RANGE"],
        "performance_selection_used": False,
        "threshold_tuning_after_observation": False,
    }


def _label_by_return_time(records: list[dict[str, Any]]) -> dict[str, str]:
    closes = [record["close"] for record in records]
    labels: dict[str, str] = {}
    for index in range(LOOKBACK_BARS, len(records) - LABEL_LAG_BARS):
        daily_returns = [
            closes[position] / closes[position - 1] - 1.0
            for position in range(index - LOOKBACK_BARS + 1, index + 1)
        ]
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum(
            (daily_return - mean_return) ** 2 for daily_return in daily_returns
        ) / len(daily_returns)
        annualized_volatility = math.sqrt(variance) * math.sqrt(PERIODS_PER_YEAR)
        trailing_return = closes[index] / closes[index - LOOKBACK_BARS] - 1.0
        if annualized_volatility >= HIGH_VOLATILITY_THRESHOLD:
            regime_id = "HIGH_VOLATILITY"
        elif trailing_return >= BULL_THRESHOLD:
            regime_id = "BULL"
        elif trailing_return <= BEAR_THRESHOLD:
            regime_id = "BEAR"
        else:
            regime_id = "RANGE"
        return_time = records[index + LABEL_LAG_BARS]["time"]
        labels[return_time] = regime_id
    return labels


def _equity_returns(curve: list[dict[str, Any]]) -> dict[str, float]:
    returns: dict[str, float] = {}
    for index in range(1, len(curve)):
        returns[curve[index]["time"]] = (
            curve[index]["equity"] / curve[index - 1]["equity"] - 1.0
        )
    return returns


def _compound(returns: list[float]) -> float:
    value = 1.0
    for item in returns:
        value *= 1.0 + item
    return round(float(value - 1.0), 12)


def _decimal_string(value: float) -> str:
    if not math.isfinite(value):
        raise MarketRegimeEvidenceError("consumer decimal must be finite")
    if value == 0.0:
        return "0"
    return f"{value:.12f}".rstrip("0").rstrip(".")


def build_market_regime_evidence(
    market_records: list[dict[str, Any]],
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    records = _normalise_market_records(market_records)
    strategy_curve = _normalise_equity_curve(
        strategy_equity_curve, "strategy_equity_curve"
    )
    benchmark_curve = _normalise_equity_curve(
        benchmark_equity_curve, "benchmark_equity_curve"
    )
    dataset_digest = _require_sha256(dataset_sha256, "dataset_sha256")
    strategy_digest = _require_sha256(
        strategy_result_sha256, "strategy_result_sha256"
    )
    benchmark_digest = _require_sha256(
        benchmark_result_sha256, "benchmark_result_sha256"
    )
    observation_kind = _require_exact_str(observation_class, "observation_class")

    policy = market_regime_policy_v1()
    policy_sha256 = _canonical_sha256(policy)
    label_by_time = _label_by_return_time(records)
    strategy_returns = _equity_returns(strategy_curve)
    benchmark_returns = _equity_returns(benchmark_curve)
    common_times = [
        record["time"]
        for record in records
        if record["time"] in label_by_time
        and record["time"] in strategy_returns
        and record["time"] in benchmark_returns
    ]

    observations: list[dict[str, Any]] = []
    slices: list[dict[str, Any]] = []
    gaps: list[str] = []
    for regime_id in REGIME_IDS:
        times = [time for time in common_times if label_by_time[time] == regime_id]
        if not times:
            observation = {
                "regime_id": regime_id,
                "status": "GAP",
                "gap_code": NO_OBSERVATIONS_GAP,
                "observation_count": 0,
                "start_time": None,
                "end_time": None,
                "strategy_total_return": None,
                "benchmark_total_return": None,
                "excess_total_return": None,
                "observation_times_sha256": None,
                "strategy_returns_sha256": None,
                "benchmark_returns_sha256": None,
                "observation_sha256": None,
            }
            gaps.append(f"{regime_id}:{NO_OBSERVATIONS_GAP}")
        else:
            strategy_values = [round(float(strategy_returns[time]), 12) for time in times]
            benchmark_values = [round(float(benchmark_returns[time]), 12) for time in times]
            strategy_total_return = _compound(strategy_values)
            benchmark_total_return = _compound(benchmark_values)
            observation_payload = {
                "regime_id": regime_id,
                "policy_sha256": policy_sha256,
                "dataset_sha256": dataset_digest,
                "strategy_result_sha256": strategy_digest,
                "benchmark_result_sha256": benchmark_digest,
                "observation_times": times,
                "strategy_returns": strategy_values,
                "benchmark_returns": benchmark_values,
                "strategy_total_return": strategy_total_return,
                "benchmark_total_return": benchmark_total_return,
            }
            observation = {
                "regime_id": regime_id,
                "status": "OBSERVED",
                "gap_code": None,
                "observation_count": len(times),
                "start_time": times[0],
                "end_time": times[-1],
                "strategy_total_return": strategy_total_return,
                "benchmark_total_return": benchmark_total_return,
                "excess_total_return": round(
                    strategy_total_return - benchmark_total_return, 12
                ),
                "observation_times_sha256": _canonical_sha256(times),
                "strategy_returns_sha256": _canonical_sha256(strategy_values),
                "benchmark_returns_sha256": _canonical_sha256(benchmark_values),
                "observation_sha256": _canonical_sha256(observation_payload),
            }
        observations.append(observation)
        slices.append(
            {
                "regime_id": regime_id,
                "status": observation["status"],
                "gap_code": observation["gap_code"],
                "observation_sha256": observation["observation_sha256"],
                "strategy_total_return": (
                    None
                    if observation["strategy_total_return"] is None
                    else _decimal_string(observation["strategy_total_return"])
                ),
                "benchmark_total_return": (
                    None
                    if observation["benchmark_total_return"] is None
                    else _decimal_string(observation["benchmark_total_return"])
                ),
            }
        )

    source_binding = {
        "dataset_sha256": dataset_digest,
        "strategy_result_sha256": strategy_digest,
        "benchmark_result_sha256": benchmark_digest,
        "market_records_sha256": _canonical_sha256(records),
        "strategy_equity_curve_sha256": _canonical_sha256(strategy_curve),
        "benchmark_equity_curve_sha256": _canonical_sha256(benchmark_curve),
        "market_row_count": len(records),
        "market_start_time": records[0]["time"],
        "market_end_time": records[-1]["time"],
    }
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "observation_class": observation_kind,
        "status": "GAP" if gaps else "OBSERVED",
        "policy": policy,
        "policy_sha256": policy_sha256,
        "source_binding": source_binding,
        "observations": observations,
        "consumer_view": {"slices": slices},
        "gaps": sorted(gaps),
        "authority": dict(_AUTHORITY),
    }
    evidence["evidence_sha256"] = _canonical_sha256(evidence)
    return evidence


def verify_market_regime_evidence(
    evidence: dict[str, Any],
    market_records: list[dict[str, Any]],
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    value = _require_exact_dict(evidence, "evidence")
    expected = build_market_regime_evidence(
        market_records,
        strategy_equity_curve,
        benchmark_equity_curve,
        dataset_sha256=dataset_sha256,
        strategy_result_sha256=strategy_result_sha256,
        benchmark_result_sha256=benchmark_result_sha256,
        observation_class=observation_class,
    )
    if value != expected:
        _fail("evidence", "does not match the deterministic source-bound evidence")
    observed_count = sum(
        item["status"] == "OBSERVED" for item in value["observations"]
    )
    gap_count = len(value["observations"]) - observed_count
    return {
        "schema_version": "market-regime-evidence-receipt-v1",
        "state": value["status"],
        "evidence_sha256": value["evidence_sha256"],
        "observed_count": observed_count,
        "gap_count": gap_count,
        "observation_count": sum(
            item["observation_count"] for item in value["observations"]
        ),
        "policy_sha256": value["policy_sha256"],
        "authority": dict(_AUTHORITY),
    }
