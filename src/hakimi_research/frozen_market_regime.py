"""Deterministic trailing market-regime analysis for Frozen research evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

import pandas as pd

from hakimi_research.backtest import RESEARCH_BACKTEST_WARMUP_ROWS
from hakimi_research.experiment_manifest import canonical_payload_hash
from hakimi_research.volatility_comparison import (
    annualization_factor,
    annualized_volatility,
)


MARKET_REGIME_POLICY_VERSION = "fixed-trailing-market-regime-v1"
MARKET_REGIME_ANALYSIS_SCHEMA_VERSION = "fixed-trailing-market-regime-analysis-v1"
MARKET_REGIME_CLASSIFICATION_SCOPE = "EX_POST_DESCRIPTIVE_NOT_SIGNAL"
MARKET_REGIME_ROLES = ("VALIDATION", "FROZEN_TEST")
MARKET_REGIME_SCENARIO_ID = "BASE"
MARKET_REGIME_LOOKBACK_ROWS = 5
MARKET_REGIME_DIRECTION_THRESHOLD = 0.005
MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD = 0.2
MARKET_REGIME_TAXONOMY = (
    ("UP_LOW", "UP", "LOW"),
    ("UP_HIGH", "UP", "HIGH"),
    ("DOWN_LOW", "DOWN", "LOW"),
    ("DOWN_HIGH", "DOWN", "HIGH"),
    ("RANGE_LOW", "RANGE", "LOW"),
    ("RANGE_HIGH", "RANGE", "HIGH"),
)
MARKET_REGIME_AUTHORITY_LOCK = {
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


def _number(value: Any, *, label: str, positive: bool = False) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"frozen_market_regime_{label}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise ValueError(f"frozen_market_regime_{label}_invalid")
    return parsed


def _clean(value: float) -> float:
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


def _compound(values: list[float]) -> float:
    compounded = 1.0
    for value in values:
        compounded *= 1.0 + value
    return _clean(compounded - 1.0)


def canonical_backtest_frame_hash(frame: pd.DataFrame) -> str:
    rows = [
        [
            str(timestamp),
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            float(row.get("volume", 0.0) or 0.0),
        ]
        for timestamp, row in frame.iterrows()
    ]
    encoded = json.dumps(
        rows,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fixed_market_regime_policy_spec() -> dict[str, Any]:
    """Return a fresh fixed, non-selecting trailing classifier contract."""

    return {
        "policy_version": MARKET_REGIME_POLICY_VERSION,
        "analysis_schema_version": MARKET_REGIME_ANALYSIS_SCHEMA_VERSION,
        "roles": list(MARKET_REGIME_ROLES),
        "cost_scenario": MARKET_REGIME_SCENARIO_ID,
        "classifier_inputs": ["close"],
        "lookback_rows": MARKET_REGIME_LOOKBACK_ROWS,
        "direction_return_definition": "CURRENT_CLOSE_OVER_CLOSE_5_ROWS_AGO_MINUS_ONE",
        "direction_threshold": MARKET_REGIME_DIRECTION_THRESHOLD,
        "direction_boundary_rule": "UP_STRICT_GT_DOWN_STRICT_LT_ELSE_RANGE",
        "volatility_return_definition": "FIVE_TRAILING_SIMPLE_CLOSE_RETURNS",
        "volatility_estimator": "SAMPLE_STD_DDOF_1_X_SQRT_ANNUALIZATION_FACTOR",
        "annualized_volatility_threshold": (
            MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD
        ),
        "volatility_boundary_rule": "HIGH_GREATER_THAN_OR_EQUAL_ELSE_LOW",
        "strategy_return_definition": "INITIAL_EQUITY_ANCHOR_THEN_SIMPLE_RETURN",
        "market_return_definition": "CURRENT_CLOSE_OVER_PREVIOUS_CLOSE_MINUS_ONE",
        "taxonomy": [
            {
                "regime_id": regime_id,
                "direction": direction,
                "volatility_band": volatility_band,
            }
            for regime_id, direction, volatility_band in MARKET_REGIME_TAXONOMY
        ],
        "classification_scope": MARKET_REGIME_CLASSIFICATION_SCOPE,
        "trailing_only": True,
        "performance_selection_allowed": False,
        "ranking_allowed": False,
        "signal_allowed": False,
    }


def _validated_policy(policy: Any) -> dict[str, Any]:
    core = fixed_market_regime_policy_spec()
    expected = {**core, "spec_hash": canonical_payload_hash(core)}
    if type(policy) is not dict or policy != expected:
        raise ValueError("frozen_market_regime_policy_invalid")
    return expected


def _validated_frame(frame: Any) -> tuple[list[float], pd.DatetimeIndex, str]:
    if type(frame) is not pd.DataFrame:
        raise ValueError("frozen_market_regime_frame_type_invalid")
    if any(column not in frame.columns for column in _REQUIRED_COLUMNS):
        raise ValueError("frozen_market_regime_frame_columns_invalid")
    if type(frame.index) is not pd.DatetimeIndex:
        raise ValueError("frozen_market_regime_frame_index_invalid")
    if (
        frame.index.tz is None
        or not frame.index.is_monotonic_increasing
        or not frame.index.is_unique
        or frame.index.hasnans
    ):
        raise ValueError("frozen_market_regime_frame_index_invalid")
    if len(frame) <= RESEARCH_BACKTEST_WARMUP_ROWS:
        raise ValueError("frozen_market_regime_frame_too_short")
    closes: list[float] = []
    for _timestamp, row in frame.loc[:, _REQUIRED_COLUMNS].iterrows():
        try:
            values = {
                column: _number(float(row[column]), label=f"frame_{column}")
                for column in _REQUIRED_COLUMNS
            }
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("frozen_market_regime_frame_numeric_invalid") from exc
        if (
            min(values["open"], values["high"], values["low"], values["close"])
            <= 0
            or values["volume"] < 0
            or values["high"] < max(values["open"], values["close"])
            or values["low"] > min(values["open"], values["close"])
            or values["high"] < values["low"]
        ):
            raise ValueError("frozen_market_regime_frame_ohlcv_invalid")
        closes.append(values["close"])
    return closes, frame.index, canonical_backtest_frame_hash(frame)


def _validated_source_run(
    source_run: Any,
    *,
    role: str,
    frame: pd.DataFrame,
    frame_hash: str,
) -> tuple[list[dict[str, Any]], str]:
    if type(source_run) is not dict:
        raise ValueError("frozen_market_regime_source_run_invalid")
    if (
        source_run.get("run_kind") != "REGISTERED_STRATEGY"
        or source_run.get("role") != role
        or source_run.get("scenario_id") != MARKET_REGIME_SCENARIO_ID
    ):
        raise ValueError("frozen_market_regime_source_run_identity_invalid")
    result = source_run.get("result")
    manifest = source_run.get("experiment_manifest")
    if type(result) is not dict or type(manifest) is not dict:
        raise ValueError("frozen_market_regime_source_run_shape_invalid")
    reproducibility = result.get("reproducibility")
    curve = result.get("equity_curve")
    if type(reproducibility) is not dict or type(curve) is not list:
        raise ValueError("frozen_market_regime_source_result_invalid")
    run_hash = reproducibility.get("run_hash")
    if type(run_hash) is not str or _HASH_PATTERN.fullmatch(run_hash) is None:
        raise ValueError("frozen_market_regime_source_run_hash_invalid")
    if (
        reproducibility.get("hash_scope") != "FULL_OHLCV"
        or reproducibility.get("data_rows") != len(frame)
        or reproducibility.get("data_hash") != frame_hash
        or reproducibility.get("data_start") != str(frame.index[0])
        or reproducibility.get("data_end") != str(frame.index[-1])
    ):
        raise ValueError("frozen_market_regime_source_data_binding_invalid")
    expected_times = [
        str(timestamp)
        for timestamp in frame.index[RESEARCH_BACKTEST_WARMUP_ROWS:]
    ]
    if len(curve) != len(expected_times):
        raise ValueError("frozen_market_regime_equity_curve_length_invalid")
    for point, expected_time in zip(curve, expected_times, strict=True):
        if (
            type(point) is not dict
            or set(point) != {"time", "equity"}
            or point.get("time") != expected_time
        ):
            raise ValueError("frozen_market_regime_equity_curve_grid_invalid")
        _number(point.get("equity"), label="equity", positive=True)
    return curve, run_hash


def build_fixed_market_regime_analysis(
    frame: pd.DataFrame,
    source_run: dict[str, Any],
    *,
    role: str,
    policy: dict[str, Any],
    initial_equity: float,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    """Build one source-bound descriptive analysis without fitting or signaling."""

    if type(role) is not str or role not in MARKET_REGIME_ROLES:
        raise ValueError("frozen_market_regime_role_invalid")
    method = _validated_policy(policy)
    initial = _number(initial_equity, label="initial_equity", positive=True)
    factor = annualization_factor(market, timeframe)
    closes, index, frame_hash = _validated_frame(frame)
    curve, run_hash = _validated_source_run(
        source_run,
        role=role,
        frame=frame,
        frame_hash=frame_hash,
    )

    observations: list[dict[str, Any]] = []
    previous_equity = initial
    for offset, point in enumerate(curve):
        position = RESEARCH_BACKTEST_WARMUP_ROWS + offset
        trailing_close_return = closes[position] / closes[
            position - MARKET_REGIME_LOOKBACK_ROWS
        ] - 1.0
        close_returns = [
            closes[current] / closes[current - 1] - 1.0
            for current in range(
                position - MARKET_REGIME_LOOKBACK_ROWS + 1,
                position + 1,
            )
        ]
        trailing_volatility = annualized_volatility(close_returns, factor)
        if trailing_close_return > MARKET_REGIME_DIRECTION_THRESHOLD:
            direction = "UP"
        elif trailing_close_return < -MARKET_REGIME_DIRECTION_THRESHOLD:
            direction = "DOWN"
        else:
            direction = "RANGE"
        volatility_band = (
            "HIGH"
            if trailing_volatility >= MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD
            else "LOW"
        )
        equity = _number(point["equity"], label="equity", positive=True)
        strategy_return = equity / previous_equity - 1.0
        market_return = closes[position] / closes[position - 1] - 1.0
        regime_id = f"{direction}_{volatility_band}"
        observations.append({
            "timestamp": pd.Timestamp(index[position]).isoformat(),
            "regime_id": regime_id,
            "direction": direction,
            "volatility_band": volatility_band,
            "trailing_close_return": _clean(trailing_close_return),
            "trailing_annualized_volatility": _clean(trailing_volatility),
            "strategy_return": _clean(strategy_return),
            "market_return": _clean(market_return),
        })
        previous_equity = equity

    slices: list[dict[str, Any]] = []
    for regime_id, direction, volatility_band in MARKET_REGIME_TAXONOMY:
        members = [
            item for item in observations if item["regime_id"] == regime_id
        ]
        strategy_returns = [item["strategy_return"] for item in members]
        market_returns = [item["market_return"] for item in members]
        slices.append({
            "regime_id": regime_id,
            "direction": direction,
            "volatility_band": volatility_band,
            "status": "OBSERVED" if members else "NO_OBSERVATIONS",
            "observation_count": len(members),
            "start_time": members[0]["timestamp"] if members else None,
            "end_time": members[-1]["timestamp"] if members else None,
            "observation_timestamps_hash": (
                canonical_payload_hash([item["timestamp"] for item in members])
                if members
                else None
            ),
            "strategy_compounded_return": (
                _compound(strategy_returns) if members else None
            ),
            "strategy_mean_return": (
                _clean(sum(strategy_returns) / len(strategy_returns))
                if members
                else None
            ),
            "market_compounded_return": (
                _compound(market_returns) if members else None
            ),
        })

    populated_count = sum(item["observation_count"] > 0 for item in slices)
    core = {
        "schema_version": MARKET_REGIME_ANALYSIS_SCHEMA_VERSION,
        "role": role,
        "scenario_id": MARKET_REGIME_SCENARIO_ID,
        "classification_scope": MARKET_REGIME_CLASSIFICATION_SCOPE,
        "policy_version": MARKET_REGIME_POLICY_VERSION,
        "policy_spec_hash": method["spec_hash"],
        "source_binding": {
            "frame_hash_scope": "BACKTEST_FULL_OHLCV_V1",
            "frame_data_hash": frame_hash,
            "frame_row_count": len(frame),
            "frame_start_time": str(frame.index[0]),
            "frame_end_time": str(frame.index[-1]),
            "source_run_hash": canonical_payload_hash(source_run),
            "source_result_hash": canonical_payload_hash(source_run["result"]),
            "source_experiment_manifest_hash": canonical_payload_hash(
                source_run["experiment_manifest"]
            ),
            "source_reproducibility_run_hash": run_hash,
            "equity_curve_hash": canonical_payload_hash(curve),
            "initial_equity": initial,
            "market": market,
            "timeframe": timeframe,
            "annualization_factor": factor,
        },
        "taxonomy": [item["regime_id"] for item in method["taxonomy"]],
        "observations": observations,
        "regime_slices": slices,
        "coverage": {
            "expected_observation_count": len(frame) - RESEARCH_BACKTEST_WARMUP_ROWS,
            "observation_count": len(observations),
            "taxonomy_cell_count": len(MARKET_REGIME_TAXONOMY),
            "populated_cell_count": populated_count,
            "empty_cell_count": len(MARKET_REGIME_TAXONOMY) - populated_count,
            "all_observations_classified": len(observations) == len(curve),
            "all_taxonomy_cells_present": len(slices) == len(MARKET_REGIME_TAXONOMY),
            "trailing_only": True,
        },
        "authority": dict(MARKET_REGIME_AUTHORITY_LOCK),
    }
    return {
        **core,
        "analysis_hash": canonical_payload_hash(core),
    }


def verify_fixed_market_regime_analysis(
    analysis: Any,
    frame: pd.DataFrame,
    source_run: dict[str, Any],
    *,
    role: str,
    policy: dict[str, Any],
    initial_equity: float,
    market: str,
    timeframe: str,
) -> bool:
    if type(analysis) is not dict:
        raise ValueError("frozen_market_regime_analysis_invalid")
    expected = build_fixed_market_regime_analysis(
        frame,
        source_run,
        role=role,
        policy=policy,
        initial_equity=initial_equity,
        market=market,
        timeframe=timeframe,
    )
    if analysis != expected:
        raise ValueError("frozen_market_regime_analysis_verification_failed")
    return True


__all__ = [
    "MARKET_REGIME_ANALYSIS_SCHEMA_VERSION",
    "MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD",
    "MARKET_REGIME_AUTHORITY_LOCK",
    "MARKET_REGIME_CLASSIFICATION_SCOPE",
    "MARKET_REGIME_DIRECTION_THRESHOLD",
    "MARKET_REGIME_LOOKBACK_ROWS",
    "MARKET_REGIME_POLICY_VERSION",
    "MARKET_REGIME_ROLES",
    "MARKET_REGIME_SCENARIO_ID",
    "MARKET_REGIME_TAXONOMY",
    "build_fixed_market_regime_analysis",
    "canonical_backtest_frame_hash",
    "fixed_market_regime_policy_spec",
    "verify_fixed_market_regime_analysis",
]
