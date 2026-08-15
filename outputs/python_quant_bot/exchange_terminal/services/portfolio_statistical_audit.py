from __future__ import annotations

import hashlib
import json
import math
import random
from statistics import fmean, pstdev
from typing import Any


PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION = "portfolio-statistical-audit-v3"
DEFAULT_RESAMPLE_COUNT = 5_000
DEFAULT_BLOCK_LENGTH = 5
DEFAULT_MINIMUM_OBSERVATIONS = 120
MIN_RESAMPLE_COUNT = 100
MAX_RESAMPLE_COUNT = 50_000
MAX_BLOCK_LENGTH = 1_024
DEFAULT_CONFIDENCE_LEVEL = 0.90
DEFAULT_REQUIRED_POSITIVE_PROBABILITY = 0.95
DEFAULT_REQUIRED_ADJUSTED_PROBABILITY = 0.90
STATISTICAL_AUDIT_CONTENT_FIELDS = (
    "schema_version",
    "status",
    "conclusion",
    "blockers",
    "input_binding",
    "config",
    "stages",
    "checks",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
)


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def statistical_audit_content(report: dict[str, Any]) -> dict[str, Any]:
    return {key: report.get(key) for key in STATISTICAL_AUDIT_CONTENT_FIELDS}


def _number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def statistical_bootstrap_budget_blockers(
    *,
    resample_count: Any,
    block_length: Any,
    sample_size: Any | None = None,
) -> list[str]:
    """Validate bounded bootstrap work before any resampling loop starts."""

    blockers: list[str] = []
    if (
        isinstance(resample_count, bool)
        or not isinstance(resample_count, int)
        or resample_count < MIN_RESAMPLE_COUNT
    ):
        blockers.append("bootstrap_resample_count_invalid")
    elif resample_count > MAX_RESAMPLE_COUNT:
        blockers.append(
            f"bootstrap_resample_count_exceeds_budget:{resample_count}>{MAX_RESAMPLE_COUNT}"
        )

    block_length_valid = (
        not isinstance(block_length, bool)
        and isinstance(block_length, int)
        and block_length >= 1
    )
    if not block_length_valid:
        blockers.append("bootstrap_block_length_invalid")
    elif block_length > MAX_BLOCK_LENGTH:
        blockers.append(
            f"bootstrap_block_length_exceeds_budget:{block_length}>{MAX_BLOCK_LENGTH}"
        )

    if sample_size is not None:
        sample_size_valid = (
            not isinstance(sample_size, bool)
            and isinstance(sample_size, int)
            and sample_size >= 0
        )
        if not sample_size_valid:
            blockers.append("bootstrap_sample_size_invalid")
        elif block_length_valid and block_length > sample_size:
            blockers.append(
                f"bootstrap_block_length_exceeds_sample_size:{block_length}>{sample_size}"
            )
    return list(dict.fromkeys(blockers))


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * min(max(float(probability), 0.0), 1.0)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _curve_returns(report: dict[str, Any]) -> tuple[list[str], list[float], list[str]]:
    blockers: list[str] = []
    initial_cash = _number(report.get("initial_cash"), -1.0)
    if initial_cash <= 0:
        blockers.append("initial_cash_invalid")
    curve = list(report.get("equity_curve") or [])
    if not curve:
        blockers.append("equity_curve_missing")
        return [], [], blockers

    dates: list[str] = []
    equities: list[float] = []
    for index, item in enumerate(curve):
        row = item if isinstance(item, dict) else {}
        session_date = str(row.get("date") or "")
        equity = _number(row.get("equity"), -1.0)
        if not session_date:
            blockers.append(f"equity_date_missing:{index}")
        if equity <= 0:
            blockers.append(f"equity_value_invalid:{index}")
        dates.append(session_date)
        equities.append(equity)
    if len(set(dates)) != len(dates):
        blockers.append("equity_dates_not_unique")
    if dates != sorted(dates):
        blockers.append("equity_dates_not_ordered")
    if blockers:
        return dates, [], list(dict.fromkeys(blockers))

    values = [initial_cash, *equities]
    returns = [current / previous - 1.0 for previous, current in zip(values[:-1], values[1:])]
    if any(not math.isfinite(item) for item in returns):
        blockers.append("equity_returns_not_finite")
    return dates, returns, list(dict.fromkeys(blockers))


def _paired_metrics(strategy_returns: list[float], benchmark_returns: list[float]) -> dict[str, float]:
    active = [strategy - benchmark for strategy, benchmark in zip(strategy_returns, benchmark_returns)]
    mean_active = fmean(active) if active else 0.0
    tracking_error = pstdev(active) if len(active) > 1 else 0.0
    strategy_compound = math.prod(1.0 + item for item in strategy_returns) - 1.0
    benchmark_compound = math.prod(1.0 + item for item in benchmark_returns) - 1.0
    return {
        "annualized_mean_active_return_pct": mean_active * 252.0 * 100.0,
        "annualized_tracking_error_pct": tracking_error * math.sqrt(252.0) * 100.0,
        "information_ratio": mean_active / tracking_error * math.sqrt(252.0) if tracking_error > 0 else 0.0,
        "strategy_compound_return_pct": strategy_compound * 100.0,
        "benchmark_compound_return_pct": benchmark_compound * 100.0,
        "compound_excess_return_pct": (strategy_compound - benchmark_compound) * 100.0,
        "active_positive_day_pct": sum(item > 0 for item in active) / max(len(active), 1) * 100.0,
    }


def _selection_adjusted_probability(probability: float, trial_count: int) -> float:
    one_sided_probability = min(max(float(probability), 0.0), 1.0)
    adjusted_p_value = min((1.0 - one_sided_probability) * max(int(trial_count), 1), 1.0)
    return 1.0 - adjusted_p_value


def audit_paired_equity_curve_stage(
    *,
    stage: str,
    strategy_report: dict[str, Any],
    benchmark_report: dict[str, Any],
    resample_count: int,
    block_length: int,
    minimum_observations: int,
    confidence_level: float,
    required_positive_probability: float,
    required_adjusted_probability: float,
    selection_trial_count: int,
    seed: int,
) -> dict[str, Any]:
    strategy_dates, strategy_returns, strategy_blockers = _curve_returns(strategy_report)
    benchmark_dates, benchmark_returns, benchmark_blockers = _curve_returns(benchmark_report)
    blockers = [
        *[f"strategy:{item}" for item in strategy_blockers],
        *[f"benchmark:{item}" for item in benchmark_blockers],
    ]
    if strategy_dates != benchmark_dates:
        blockers.append("strategy_benchmark_dates_mismatch")
    if len(strategy_returns) != len(benchmark_returns):
        blockers.append("strategy_benchmark_return_count_mismatch")
    observation_count = min(len(strategy_returns), len(benchmark_returns))
    if observation_count < minimum_observations:
        blockers.append(f"observations:{observation_count}<{minimum_observations}")
    blockers.extend(
        statistical_bootstrap_budget_blockers(
            resample_count=resample_count,
            block_length=block_length,
            sample_size=observation_count if not blockers else None,
        )
    )

    if blockers:
        content = {
            "stage": stage,
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "observation_count": observation_count,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return {**content, "stage_hash": _canonical_hash(content)}

    observed = _paired_metrics(strategy_returns, benchmark_returns)
    rng = random.Random(seed)
    information_ratios: list[float] = []
    compound_excess_returns: list[float] = []
    annualized_active_returns: list[float] = []
    sample_size = len(strategy_returns)
    for _ in range(resample_count):
        indexes: list[int] = []
        while len(indexes) < sample_size:
            start = rng.randrange(sample_size)
            indexes.extend((start + offset) % sample_size for offset in range(block_length))
        indexes = indexes[:sample_size]
        metrics = _paired_metrics(
            [strategy_returns[index] for index in indexes],
            [benchmark_returns[index] for index in indexes],
        )
        information_ratios.append(metrics["information_ratio"])
        compound_excess_returns.append(metrics["compound_excess_return_pct"])
        annualized_active_returns.append(metrics["annualized_mean_active_return_pct"])

    tail = (1.0 - confidence_level) / 2.0
    positive_probability = sum(item > 0 for item in compound_excess_returns) / resample_count
    positive_information_ratio_probability = sum(item > 0 for item in information_ratios) / resample_count
    adjusted_probability = _selection_adjusted_probability(positive_probability, selection_trial_count)
    adjusted_information_ratio_probability = _selection_adjusted_probability(
        positive_information_ratio_probability,
        selection_trial_count,
    )
    intervals = {
        "annualized_mean_active_return_pct": [
            _quantile(annualized_active_returns, tail),
            _quantile(annualized_active_returns, 1.0 - tail),
        ],
        "information_ratio": [
            _quantile(information_ratios, tail),
            _quantile(information_ratios, 1.0 - tail),
        ],
        "compound_excess_return_pct": [
            _quantile(compound_excess_returns, tail),
            _quantile(compound_excess_returns, 1.0 - tail),
        ],
    }
    checks = {
        "minimum_observations": observation_count >= minimum_observations,
        "observed_compound_excess_positive": observed["compound_excess_return_pct"] > 0,
        "observed_information_ratio_positive": observed["information_ratio"] > 0,
        "bootstrap_positive_probability": positive_probability >= required_positive_probability,
        "bootstrap_information_ratio_probability": (
            positive_information_ratio_probability >= required_positive_probability
        ),
        "selection_adjusted_probability": adjusted_probability >= required_adjusted_probability,
        "selection_adjusted_information_ratio_probability": (
            adjusted_information_ratio_probability >= required_adjusted_probability
        ),
        "compound_excess_interval_lower_positive": intervals["compound_excess_return_pct"][0] > 0,
        "information_ratio_interval_lower_positive": intervals["information_ratio"][0] > 0,
    }
    stage_blockers = [name for name, passed in checks.items() if not passed]
    rounded_observed = {key: round(value, 8) for key, value in observed.items()}
    rounded_intervals = {
        key: [round(value, 8) for value in values]
        for key, values in intervals.items()
    }
    content = {
        "stage": stage,
        "status": "PASS" if not stage_blockers else "BLOCK",
        "blockers": stage_blockers,
        "observation_count": observation_count,
        "first_date": strategy_dates[0],
        "last_date": strategy_dates[-1],
        "observed": rounded_observed,
        "bootstrap": {
            "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
            "resample_count": resample_count,
            "block_length": block_length,
            "confidence_level": confidence_level,
            "seed": seed,
            "compound_excess_positive_probability": round(positive_probability, 8),
            "information_ratio_positive_probability": round(positive_information_ratio_probability, 8),
            "selection_trial_count": selection_trial_count,
            "selection_adjusted_compound_excess_probability": round(adjusted_probability, 8),
            "selection_adjusted_information_ratio_probability": round(
                adjusted_information_ratio_probability,
                8,
            ),
            "intervals": rounded_intervals,
        },
        "checks": checks,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**content, "stage_hash": _canonical_hash(content)}


def audit_portfolio_research_statistics(
    research_report: dict[str, Any],
    *,
    generated_at: int = 0,
    resample_count: int = DEFAULT_RESAMPLE_COUNT,
    block_length: int = DEFAULT_BLOCK_LENGTH,
    minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    required_positive_probability: float = DEFAULT_REQUIRED_POSITIVE_PROBABILITY,
    required_adjusted_probability: float = DEFAULT_REQUIRED_ADJUSTED_PROBABILITY,
) -> dict[str, Any]:
    clean_resamples = max(int(resample_count), 100)
    clean_block_length = max(int(block_length), 1)
    clean_minimum_observations = max(int(minimum_observations), 2)
    clean_confidence = min(max(float(confidence_level), 0.50), 0.999)
    clean_required_probability = min(max(float(required_positive_probability), 0.50), 1.0)
    clean_required_adjusted = min(max(float(required_adjusted_probability), 0.50), 1.0)
    spec = dict(research_report.get("spec") or {})
    manifest = dict(research_report.get("dataset_manifest") or {})
    candidate = dict(research_report.get("frozen_candidate") or {})
    selection_trial_count = max(int(_number(spec.get("trial_count"), 1.0)), 1)
    config = {
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": clean_resamples,
        "block_length": clean_block_length,
        "minimum_observations": clean_minimum_observations,
        "confidence_level": clean_confidence,
        "required_positive_probability": clean_required_probability,
        "required_selection_adjusted_probability": clean_required_adjusted,
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": selection_trial_count,
    }
    input_binding = {
        "batch_run_hash": str(research_report.get("batch_run_hash") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
        "dataset_hash": str(manifest.get("data_hash") or ""),
        "spec_hash": str(research_report.get("spec_hash") or ""),
        "validation_run_hash": str((research_report.get("validation") or {}).get("run_hash") or ""),
        "validation_benchmark_run_hash": str(
            (research_report.get("validation_benchmark") or {}).get("benchmark_run_hash") or ""
        ),
        "test_run_hash": str((research_report.get("test") or {}).get("run_hash") or ""),
        "test_benchmark_run_hash": str(
            (research_report.get("test_benchmark") or {}).get("benchmark_run_hash") or ""
        ),
    }
    input_binding["binding_hash"] = _canonical_hash(input_binding)
    seed_material = {
        "schema_version": PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "input_binding": input_binding,
        "config": config,
    }
    seed_root = _canonical_hash(seed_material)

    authority_blockers: list[str] = []
    if research_report.get("research_only") is not True:
        authority_blockers.append("source_not_research_only")
    if research_report.get("paper_authorized") is not False:
        authority_blockers.append("source_contains_paper_authority")
    if research_report.get("live_order_allowed") is not False:
        authority_blockers.append("source_contains_live_authority")
    binding_blockers: list[str] = []
    for key in (
        "batch_run_hash",
        "candidate_hash",
        "dataset_hash",
        "spec_hash",
        "validation_run_hash",
        "validation_benchmark_run_hash",
        "test_run_hash",
        "test_benchmark_run_hash",
    ):
        if not input_binding[key]:
            binding_blockers.append(f"input_binding_missing:{key}")

    stages: dict[str, dict[str, Any]] = {}
    for stage in ("validation", "test"):
        stage_seed = int(_canonical_hash({"seed_root": seed_root, "stage": stage})[:16], 16)
        stages[stage] = audit_paired_equity_curve_stage(
            stage=stage,
            strategy_report=dict(research_report.get(stage) or {}),
            benchmark_report=dict(research_report.get(f"{stage}_benchmark") or {}),
            resample_count=clean_resamples,
            block_length=clean_block_length,
            minimum_observations=clean_minimum_observations,
            confidence_level=clean_confidence,
            required_positive_probability=clean_required_probability,
            required_adjusted_probability=clean_required_adjusted,
            selection_trial_count=selection_trial_count,
            seed=stage_seed,
        )

    blockers = [
        *authority_blockers,
        *binding_blockers,
        *[
            f"{stage}:{item}"
            for stage, audit in stages.items()
            for item in list(audit.get("blockers") or [])
        ],
    ]
    checks = {
        "input_authority_is_research_only": not authority_blockers,
        "input_binding_complete": not binding_blockers,
        "validation_statistical_evidence_pass": stages["validation"].get("status") == "PASS",
        "test_statistical_evidence_pass": stages["test"].get("status") == "PASS",
        "zero_execution_authority": True,
    }
    content = {
        "schema_version": PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
        "status": "PASS" if not blockers and all(checks.values()) else "BLOCK",
        "conclusion": (
            "STATISTICAL_PROMOTION_EVIDENCE_PASS"
            if not blockers and all(checks.values())
            else "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE"
        ),
        "blockers": list(dict.fromkeys(blockers)),
        "input_binding": input_binding,
        "config": config,
        "stages": stages,
        "checks": checks,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {
        **content,
        "generated_at": int(generated_at),
        "audit_hash": _canonical_hash(content),
    }


def verify_portfolio_statistical_audit_semantics(
    audit: dict[str, Any],
    research_report: dict[str, Any],
) -> dict[str, Any]:
    report = dict(audit or {})
    source = dict(research_report or {})
    blockers: list[str] = []
    supplied_generated_at = report.get("generated_at")
    if type(supplied_generated_at) is not int or supplied_generated_at <= 0:
        blockers.append("statistical_audit_generated_at_invalid")
        generated_at = 0
    else:
        generated_at = supplied_generated_at

    try:
        expected = audit_portfolio_research_statistics(source, generated_at=generated_at)
    except (TypeError, ValueError, OverflowError) as exc:
        expected = {}
        blockers.append(f"statistical_audit_recomputation_failed:{type(exc).__name__}")

    for field in STATISTICAL_AUDIT_CONTENT_FIELDS:
        if _canonical_hash(report.get(field)) != _canonical_hash(expected.get(field)):
            blockers.append(f"statistical_audit_semantic_mismatch:{field}")
    if str(report.get("audit_hash") or "") != str(expected.get("audit_hash") or ""):
        blockers.append("statistical_audit_semantic_hash_mismatch")
    if report.get("research_only") is not True:
        blockers.append("statistical_audit_research_only_invalid")
    if report.get("paper_authorized") is not False:
        blockers.append("statistical_audit_paper_authority_invalid")
    if report.get("live_order_allowed") is not False:
        blockers.append("statistical_audit_live_authority_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "claim_status": str(report.get("status") or "BLOCK"),
        "expected_status": str(expected.get("status") or "BLOCK"),
        "expected_conclusion": str(expected.get("conclusion") or ""),
        "expected_audit_hash": str(expected.get("audit_hash") or ""),
        "recomputed_from_frozen_research": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
