"""Frozen adapters for exact, partial tail and distribution evidence."""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any

import pandas as pd

from hakimi_research.backtest import RESEARCH_BACKTEST_WARMUP_ROWS
from hakimi_research.distribution_evidence import (
    DISTRIBUTION_EVIDENCE_VERSION,
    build_distribution_evidence,
)
from hakimi_research.experiment_manifest import canonical_payload_hash
from hakimi_research.frozen_market_regime import canonical_backtest_frame_hash
from hakimi_research.volatility_comparison import annualization_factor


FROZEN_DISTRIBUTION_POLICY_VERSION = "frozen-tail-distribution-policy-v2"
FROZEN_DISTRIBUTION_ANALYSIS_SCHEMA_VERSION = (
    "frozen-tail-distribution-analysis-v2"
)
FROZEN_DISTRIBUTION_SCOPE = "DESCRIPTIVE_PARTIAL_NOT_INFERENCE_NOT_SIGNAL"
FROZEN_DISTRIBUTION_ROLES = ("VALIDATION", "FROZEN_TEST")
FROZEN_DISTRIBUTION_SCENARIOS = ("BASE", "DOUBLE_COST", "TRIPLE_COST")
FROZEN_DISTRIBUTION_AUTHORITY_LOCK = {
    "formal_inference": False,
    "signal": False,
    "parameter_selection": False,
    "ranking": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}

_REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def frozen_distribution_policy_spec() -> dict[str, Any]:
    """Return a fresh, fixed adapter policy for the canonical producer."""

    return {
        "policy_version": FROZEN_DISTRIBUTION_POLICY_VERSION,
        "analysis_schema_version": FROZEN_DISTRIBUTION_ANALYSIS_SCHEMA_VERSION,
        "source_evidence_version": DISTRIBUTION_EVIDENCE_VERSION,
        "roles": list(FROZEN_DISTRIBUTION_ROLES),
        "cost_scenarios": list(FROZEN_DISTRIBUTION_SCENARIOS),
        "initial_equity_anchor": "PARTITION_ROW_BEFORE_BACKTEST_ACTIVE_WINDOW",
        "period_return_definition": "INITIAL_EQUITY_ANCHOR_THEN_SIMPLE_RETURN",
        "tail_var_95_minimum_observations": 20,
        "tail_var_99_minimum_observations": 100,
        "fixed_concentration_window_length": 21,
        "unknown_metric_policy": "NULL_WITH_EXPLICIT_GAP_NEVER_ZERO_FILL",
        "classification_scope": FROZEN_DISTRIBUTION_SCOPE,
        "formal_inference_allowed": False,
        "performance_selection_allowed": False,
        "ranking_allowed": False,
        "signal_allowed": False,
    }


def _validated_policy(policy: Any) -> dict[str, Any]:
    core = frozen_distribution_policy_spec()
    expected = {**core, "spec_hash": canonical_payload_hash(core)}
    if type(policy) is not dict or policy != expected:
        raise ValueError("frozen_distribution_policy_invalid")
    return expected


def _number(value: Any, *, label: str, positive: bool = False) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"frozen_distribution_{label}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise ValueError(f"frozen_distribution_{label}_invalid")
    return parsed


def _validated_frame(frame: Any) -> tuple[str, str, str]:
    if type(frame) is not pd.DataFrame:
        raise ValueError("frozen_distribution_frame_type_invalid")
    if any(column not in frame.columns for column in _REQUIRED_COLUMNS):
        raise ValueError("frozen_distribution_frame_columns_invalid")
    if (
        type(frame.index) is not pd.DatetimeIndex
        or frame.index.tz is None
        or not frame.index.is_monotonic_increasing
        or not frame.index.is_unique
        or frame.index.hasnans
        or len(frame) <= RESEARCH_BACKTEST_WARMUP_ROWS
    ):
        raise ValueError("frozen_distribution_frame_index_invalid")
    return (
        canonical_backtest_frame_hash(frame),
        str(frame.index[0]),
        str(frame.index[-1]),
    )


def _validated_source_run(
    source_run: Any,
    *,
    role: str,
    scenario_id: str,
    frame: pd.DataFrame,
    frame_hash: str,
    frame_start: str,
    frame_end: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if type(source_run) is not dict:
        raise ValueError("frozen_distribution_source_run_invalid")
    if (
        source_run.get("run_kind") != "REGISTERED_STRATEGY"
        or source_run.get("role") != role
        or source_run.get("scenario_id") != scenario_id
    ):
        raise ValueError("frozen_distribution_source_run_identity_invalid")
    result = source_run.get("result")
    manifest = source_run.get("experiment_manifest")
    if type(result) is not dict or type(manifest) is not dict:
        raise ValueError("frozen_distribution_source_run_shape_invalid")
    reproducibility = result.get("reproducibility")
    curve = result.get("equity_curve")
    if type(reproducibility) is not dict or type(curve) is not list:
        raise ValueError("frozen_distribution_source_result_invalid")
    run_hash = reproducibility.get("run_hash")
    if type(run_hash) is not str or _HASH_PATTERN.fullmatch(run_hash) is None:
        raise ValueError("frozen_distribution_source_run_hash_invalid")
    if (
        reproducibility.get("hash_scope") != "FULL_OHLCV"
        or reproducibility.get("data_rows") != len(frame)
        or reproducibility.get("data_hash") != frame_hash
        or reproducibility.get("data_start") != frame_start
        or reproducibility.get("data_end") != frame_end
    ):
        raise ValueError("frozen_distribution_source_data_binding_invalid")
    expected_times = [
        str(timestamp)
        for timestamp in frame.index[RESEARCH_BACKTEST_WARMUP_ROWS:]
    ]
    if len(curve) != len(expected_times):
        raise ValueError("frozen_distribution_equity_curve_length_invalid")
    for point, expected_time in zip(curve, expected_times, strict=True):
        if (
            type(point) is not dict
            or set(point) != {"time", "equity"}
            or point.get("time") != expected_time
        ):
            raise ValueError("frozen_distribution_equity_curve_grid_invalid")
        _number(point.get("equity"), label="equity", positive=True)
    return result, curve, run_hash


def build_frozen_distribution_analysis(
    frame: pd.DataFrame,
    source_run: dict[str, Any],
    *,
    role: str,
    scenario_id: str,
    policy: dict[str, Any],
    initial_equity: float,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    """Build one exact adapter analysis while retaining insufficient-sample gaps."""

    if type(role) is not str or role not in FROZEN_DISTRIBUTION_ROLES:
        raise ValueError("frozen_distribution_role_invalid")
    if (
        type(scenario_id) is not str
        or scenario_id not in FROZEN_DISTRIBUTION_SCENARIOS
    ):
        raise ValueError("frozen_distribution_scenario_invalid")
    method = _validated_policy(policy)
    initial = _number(initial_equity, label="initial_equity", positive=True)
    factor = annualization_factor(market, timeframe)
    frame_hash, frame_start, frame_end = _validated_frame(frame)
    result, curve, run_hash = _validated_source_run(
        source_run,
        role=role,
        scenario_id=scenario_id,
        frame=frame,
        frame_hash=frame_hash,
        frame_start=frame_start,
        frame_end=frame_end,
    )
    anchor = {
        "time": str(frame.index[RESEARCH_BACKTEST_WARMUP_ROWS - 1]),
        "equity": initial,
    }
    projected_result = deepcopy(result)
    projected_result["equity_curve"] = [anchor, *deepcopy(curve)]
    source_binding = {
        "role": role,
        "scenario_id": scenario_id,
        "frame_data_hash": frame_hash,
        "frame_row_count": len(frame),
        "source_run_hash": canonical_payload_hash(source_run),
        "source_result_hash": canonical_payload_hash(result),
        "source_experiment_manifest_hash": canonical_payload_hash(
            source_run["experiment_manifest"]
        ),
        "source_reproducibility_run_hash": run_hash,
        "source_equity_curve_hash": canonical_payload_hash(curve),
        "initial_equity_anchor": anchor,
        "projected_result_hash": canonical_payload_hash(projected_result),
    }
    source_envelope = {
        "source_binding": source_binding,
        "projected_result": projected_result,
    }
    evidence = build_distribution_evidence(
        source_envelope,
        source_result_path=["projected_result"],
        periods_per_year=factor,
    )
    if evidence["metrics"]["period_return_count"] != len(curve):
        raise ValueError("frozen_distribution_period_return_coverage_invalid")
    metric_states = {
        field: "UNKNOWN" if value is None else "OBSERVED"
        for field, value in evidence["metrics"].items()
        if field not in {"period_return_count", "closed_trade_count"}
    }
    core = {
        "schema_version": FROZEN_DISTRIBUTION_ANALYSIS_SCHEMA_VERSION,
        "role": role,
        "scenario_id": scenario_id,
        "classification_scope": FROZEN_DISTRIBUTION_SCOPE,
        "policy_version": FROZEN_DISTRIBUTION_POLICY_VERSION,
        "policy_spec_hash": method["spec_hash"],
        "source_binding": source_binding,
        "distribution_evidence": evidence,
        "metric_states": metric_states,
        "coverage": {
            "expected_period_return_count": len(curve),
            "period_return_count": evidence["metrics"]["period_return_count"],
            "all_source_observations_retained": True,
            "insufficient_sample_gaps_retained": (
                "TAIL_SAMPLE_LT_20" in evidence["gaps"]
                and "TAIL_SAMPLE_LT_100" in evidence["gaps"]
            ),
        },
        "authority": dict(FROZEN_DISTRIBUTION_AUTHORITY_LOCK),
    }
    return {**core, "analysis_hash": canonical_payload_hash(core)}


def verify_frozen_distribution_analysis(
    analysis: Any,
    frame: pd.DataFrame,
    source_run: dict[str, Any],
    *,
    role: str,
    scenario_id: str,
    policy: dict[str, Any],
    initial_equity: float,
    market: str,
    timeframe: str,
) -> bool:
    if type(analysis) is not dict:
        raise ValueError("frozen_distribution_analysis_invalid")
    expected = build_frozen_distribution_analysis(
        frame,
        source_run,
        role=role,
        scenario_id=scenario_id,
        policy=policy,
        initial_equity=initial_equity,
        market=market,
        timeframe=timeframe,
    )
    if analysis != expected:
        raise ValueError("frozen_distribution_analysis_verification_failed")
    return True


__all__ = [
    "FROZEN_DISTRIBUTION_ANALYSIS_SCHEMA_VERSION",
    "FROZEN_DISTRIBUTION_AUTHORITY_LOCK",
    "FROZEN_DISTRIBUTION_POLICY_VERSION",
    "FROZEN_DISTRIBUTION_ROLES",
    "FROZEN_DISTRIBUTION_SCENARIOS",
    "FROZEN_DISTRIBUTION_SCOPE",
    "build_frozen_distribution_analysis",
    "frozen_distribution_policy_spec",
    "verify_frozen_distribution_analysis",
]
