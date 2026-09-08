from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from typing import Any


SCHEMA_VERSION = "paired-moving-block-bootstrap-confidence-evidence-v1"
POLICY_SCHEMA_VERSION = "paired-moving-block-bootstrap-policy-v1"
REPLICATE_COUNT = 1000
BLOCK_LENGTH = 5
MINIMUM_OBSERVATION_COUNT = 60
CONFIDENCE_LEVEL = "0.95"
LOWER_QUANTILE = 0.025
UPPER_QUANTILE = 0.975
SEED_NAMESPACE = "hakimi-paired-moving-block-bootstrap-v1"
INSUFFICIENT_OBSERVATIONS_GAP = "INSUFFICIENT_PAIRED_OBSERVATIONS"

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class BootstrapConfidenceEvidenceError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise BootstrapConfidenceEvidenceError(f"{path}: {message}")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _require_exact_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an exact list")
    return value


def _require_exact_dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    return value


def _require_sha256(value: Any, path: str) -> str:
    if type(value) is not str or _SHA256_PATTERN.fullmatch(value) is None:
        _fail(path, "must be a lowercase SHA-256 digest in an exact str")
    return value


def _normalise_time(value: Any, path: str) -> str:
    if type(value) is not str:
        _fail(path, "must be an exact str")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(path, f"must be ISO-8601: {exc}")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        _fail(path, "must be timezone-aware UTC")
    return parsed.isoformat()


def _normalise_curve(value: Any, path: str) -> list[dict[str, Any]]:
    curve = _require_exact_list(value, path)
    if len(curve) < 2:
        _fail(path, "must contain at least two observations")
    normalised: list[dict[str, Any]] = []
    previous_time: str | None = None
    for index, item in enumerate(curve):
        item_path = f"{path}[{index}]"
        record = _require_exact_dict(item, item_path)
        if set(record) != {"time", "equity"}:
            _fail(item_path, "must contain exactly time and equity")
        timestamp = _normalise_time(record["time"], f"{item_path}.time")
        if previous_time is not None and timestamp <= previous_time:
            _fail(f"{item_path}.time", "must be strictly increasing and unique")
        previous_time = timestamp
        equity = record["equity"]
        if type(equity) is not float or not math.isfinite(equity) or equity <= 0.0:
            _fail(f"{item_path}.equity", "must be a positive finite exact float")
        normalised.append({"time": timestamp, "equity": equity})
    return normalised


def paired_moving_block_bootstrap_policy_v1() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "method": "PAIRED_MOVING_BLOCK_BOOTSTRAP",
        "block_length": BLOCK_LENGTH,
        "replicate_count": REPLICATE_COUNT,
        "minimum_observation_count": MINIMUM_OBSERVATION_COUNT,
        "confidence_level": CONFIDENCE_LEVEL,
        "lower_quantile": "0.025",
        "upper_quantile": "0.975",
        "quantile_method": "LINEAR_TYPE_7",
        "seed_derivation": "SHA256_SOURCE_BOUND_BLOCK_START_V1",
        "seed_namespace": SEED_NAMESPACE,
        "paired_sampling": True,
        "statistics": [
            "STRATEGY_TOTAL_RETURN",
            "BUY_AND_HOLD_TOTAL_RETURN",
            "STRATEGY_MINUS_BUY_AND_HOLD_TOTAL_RETURN",
        ],
        "formal_inference_claimed": False,
        "performance_selection_used": False,
        "post_observation_policy_tuning": False,
    }


def _returns_by_time(curve: list[dict[str, Any]]) -> dict[str, float]:
    return {
        curve[index]["time"]: curve[index]["equity"] / curve[index - 1]["equity"] - 1.0
        for index in range(1, len(curve))
    }


def _compound(values: list[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + value
    return round(float(result - 1.0), 12)


def _decimal(value: float) -> str:
    if not math.isfinite(value):
        raise BootstrapConfidenceEvidenceError("interval value must be finite")
    if value == 0.0:
        return "0"
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _quantile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return round(float(ordered[lower_index]), 12)
    fraction = position - lower_index
    return round(
        float(
            ordered[lower_index]
            + (ordered[upper_index] - ordered[lower_index]) * fraction
        ),
        12,
    )


def _sample_indices(
    observation_count: int, seed_material_sha256: str, replicate_index: int
) -> list[int]:
    indices: list[int] = []
    maximum_start = observation_count - BLOCK_LENGTH
    block_index = 0
    while len(indices) < observation_count:
        material = (
            f"{seed_material_sha256}:{replicate_index}:{block_index}"
        ).encode("ascii")
        digest = hashlib.sha256(material).digest()
        start = int.from_bytes(digest[:8], "big") % (maximum_start + 1)
        indices.extend(range(start, start + BLOCK_LENGTH))
        block_index += 1
    return indices[:observation_count]


def _interval(
    metric_id: str, point_estimate: float, distribution: list[float]
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "status": "OBSERVED",
        "gap_code": None,
        "point_estimate": _decimal(point_estimate),
        "lower_bound": _decimal(_quantile(distribution, LOWER_QUANTILE)),
        "median": _decimal(_quantile(distribution, 0.5)),
        "upper_bound": _decimal(_quantile(distribution, UPPER_QUANTILE)),
        "distribution_sha256": _canonical_sha256(
            [round(float(value), 12) for value in distribution]
        ),
    }


def build_bootstrap_confidence_evidence(
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    strategy_curve = _normalise_curve(strategy_equity_curve, "strategy_equity_curve")
    benchmark_curve = _normalise_curve(benchmark_equity_curve, "benchmark_equity_curve")
    dataset_digest = _require_sha256(dataset_sha256, "dataset_sha256")
    strategy_digest = _require_sha256(
        strategy_result_sha256, "strategy_result_sha256"
    )
    benchmark_digest = _require_sha256(
        benchmark_result_sha256, "benchmark_result_sha256"
    )
    if type(observation_class) is not str or not observation_class:
        _fail("observation_class", "must be a non-empty exact str")

    strategy_returns_by_time = _returns_by_time(strategy_curve)
    benchmark_returns_by_time = _returns_by_time(benchmark_curve)
    common_times = sorted(set(strategy_returns_by_time) & set(benchmark_returns_by_time))
    strategy_returns = [strategy_returns_by_time[time] for time in common_times]
    benchmark_returns = [benchmark_returns_by_time[time] for time in common_times]
    policy = paired_moving_block_bootstrap_policy_v1()
    policy_sha256 = _canonical_sha256(policy)
    source_binding = {
        "dataset_sha256": dataset_digest,
        "strategy_result_sha256": strategy_digest,
        "benchmark_result_sha256": benchmark_digest,
        "strategy_equity_curve_sha256": _canonical_sha256(strategy_curve),
        "benchmark_equity_curve_sha256": _canonical_sha256(benchmark_curve),
        "common_observation_times_sha256": _canonical_sha256(common_times),
        "paired_observation_count": len(common_times),
        "start_time": common_times[0] if common_times else None,
        "end_time": common_times[-1] if common_times else None,
    }
    sample_summary = {
        "paired_observation_count": len(common_times),
        "strategy_total_return": _decimal(_compound(strategy_returns))
        if strategy_returns
        else None,
        "benchmark_total_return": _decimal(_compound(benchmark_returns))
        if benchmark_returns
        else None,
        "strategy_minus_benchmark_total_return": (
            _decimal(_compound(strategy_returns) - _compound(benchmark_returns))
            if strategy_returns
            else None
        ),
    }

    gaps: list[str] = []
    intervals: list[dict[str, Any]] = []
    replicate_count = 0
    seed_material_sha256: str | None = None
    if len(common_times) < MINIMUM_OBSERVATION_COUNT:
        gaps.append(INSUFFICIENT_OBSERVATIONS_GAP)
        evidence_state = "GAP"
    else:
        evidence_state = "OBSERVED"
        seed_material_sha256 = _canonical_sha256(
            {
                "namespace": SEED_NAMESPACE,
                "policy_sha256": policy_sha256,
                "dataset_sha256": dataset_digest,
                "strategy_result_sha256": strategy_digest,
                "benchmark_result_sha256": benchmark_digest,
            }
        )
        strategy_distribution: list[float] = []
        benchmark_distribution: list[float] = []
        difference_distribution: list[float] = []
        for replicate_index in range(REPLICATE_COUNT):
            indices = _sample_indices(
                len(common_times), seed_material_sha256, replicate_index
            )
            sampled_strategy = [strategy_returns[index] for index in indices]
            sampled_benchmark = [benchmark_returns[index] for index in indices]
            strategy_total = _compound(sampled_strategy)
            benchmark_total = _compound(sampled_benchmark)
            strategy_distribution.append(strategy_total)
            benchmark_distribution.append(benchmark_total)
            difference_distribution.append(round(strategy_total - benchmark_total, 12))
        replicate_count = REPLICATE_COUNT
        strategy_point = _compound(strategy_returns)
        benchmark_point = _compound(benchmark_returns)
        intervals = [
            _interval(
                "STRATEGY_TOTAL_RETURN", strategy_point, strategy_distribution
            ),
            _interval(
                "BUY_AND_HOLD_TOTAL_RETURN", benchmark_point, benchmark_distribution
            ),
            _interval(
                "STRATEGY_MINUS_BUY_AND_HOLD_TOTAL_RETURN",
                round(strategy_point - benchmark_point, 12),
                difference_distribution,
            ),
        ]

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "observation_class": observation_class,
        "evidence_state": evidence_state,
        "policy": policy,
        "policy_sha256": policy_sha256,
        "source_binding": source_binding,
        "seed_material_sha256": seed_material_sha256,
        "replicate_count": replicate_count,
        "sample_summary": sample_summary,
        "intervals": intervals,
        "gaps": gaps,
        "authority": dict(_AUTHORITY),
    }
    evidence["evidence_sha256"] = _canonical_sha256(evidence)
    return evidence


def verify_bootstrap_confidence_evidence(
    evidence: dict[str, Any],
    strategy_equity_curve: list[dict[str, Any]],
    benchmark_equity_curve: list[dict[str, Any]],
    *,
    dataset_sha256: str,
    strategy_result_sha256: str,
    benchmark_result_sha256: str,
    observation_class: str,
) -> dict[str, Any]:
    if type(evidence) is not dict:
        _fail("evidence", "must be an exact dict")
    expected = build_bootstrap_confidence_evidence(
        strategy_equity_curve,
        benchmark_equity_curve,
        dataset_sha256=dataset_sha256,
        strategy_result_sha256=strategy_result_sha256,
        benchmark_result_sha256=benchmark_result_sha256,
        observation_class=observation_class,
    )
    if evidence != expected:
        _fail("evidence", "must match deterministic source-bound bootstrap evidence")
    return {
        "schema_version": "paired-moving-block-bootstrap-confidence-receipt-v1",
        "state": evidence["evidence_state"],
        "evidence_sha256": evidence["evidence_sha256"],
        "paired_observation_count": evidence["source_binding"][
            "paired_observation_count"
        ],
        "replicate_count": evidence["replicate_count"],
        "interval_count": len(evidence["intervals"]),
        "policy_sha256": evidence["policy_sha256"],
        "gaps": list(evidence["gaps"]),
        "authority": dict(_AUTHORITY),
    }
