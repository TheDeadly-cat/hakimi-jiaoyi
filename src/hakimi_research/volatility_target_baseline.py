"""Prior-window, no-leverage volatility-target research benchmark."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import pandas as pd

from hakimi_research.backtest import RESEARCH_BACKTEST_WARMUP_ROWS
from hakimi_research.models import Portfolio, Signal
from hakimi_research.strategies.base import StrategyBase
from hakimi_research.volatility_comparison import (
    annualization_factor,
    annualized_volatility,
    observed_equity_annualized_volatility,
)


VOLATILITY_TARGET_BASELINE_SCHEMA_VERSION = "prior-window-volatility-target-baseline-v1"
VOLATILITY_TARGET_BASELINE_ID = "PRIOR_WINDOW_VOLATILITY_TARGET_BUY_AND_HOLD"
VOLATILITY_TARGET_METHOD_VERSION = "prior-window-volatility-target-v1"
VOLATILITY_TARGET_STRATEGY_VERSION = "prior-window-volatility-target-buy-hold-v1"
VOLATILITY_TARGET_AUTHORITY_LOCK = {
    "research_simulator_only": True,
    "paper": False,
    "live": False,
    "order": False,
    "parameter_selection": False,
    "profitability_proof": False,
}
_CALIBRATION_CORE_FIELDS = frozenset({
    "schema_version",
    "benchmark_id",
    "method_version",
    "target_role",
    "calibration_role",
    "calibration_strategy_scenario",
    "calibration_strategy_run_hash",
    "calibration_data_hash",
    "calibration_start_time",
    "calibration_end_time",
    "calibration_rows",
    "annualization_factor",
    "target_annualized_volatility",
    "source_annualized_volatility",
    "raw_exposure",
    "applied_exposure",
    "exposure_cap",
    "exposure_capped",
    "calibration_status",
    "blockers",
    "authority",
})


def volatility_target_method_spec() -> dict[str, Any]:
    """Return a fresh preregistered prior-window calibration rule."""

    return {
        "benchmark_id": VOLATILITY_TARGET_BASELINE_ID,
        "method_version": VOLATILITY_TARGET_METHOD_VERSION,
        "strategy_version": VOLATILITY_TARGET_STRATEGY_VERSION,
        "calibration_map": [
            {"target_role": "VALIDATION", "calibration_role": "TRAIN"},
            {"target_role": "FROZEN_TEST", "calibration_role": "VALIDATION"},
        ],
        "cost_scenarios": ["BASE", "DOUBLE_COST", "TRIPLE_COST"],
        "calibration_strategy_scenario": "BASE",
        "warmup_rows": RESEARCH_BACKTEST_WARMUP_ROWS,
        "target_volatility_source": "PRIOR_REGISTERED_STRATEGY_NET_EQUITY",
        "source_volatility_source": "PRIOR_WINDOW_CLOSE_RETURNS_AFTER_WARMUP",
        "exposure_formula": "MIN(EXPOSURE_CAP,TARGET_VOLATILITY/SOURCE_VOLATILITY)",
        "exposure_cap": 1.0,
        "leverage_allowed": False,
        "research_simulator_executable": True,
        "paper_authorized": False,
        "live_authorized": False,
        "order_authorized": False,
        "parameter_selection_allowed": False,
    }


def _number(value: Any, *, label: str, positive: bool = False) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"volatility_target_{label}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise ValueError(f"volatility_target_{label}_invalid")
    return parsed


def _clean(value: float) -> float:
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


def _canonical_hash(value: dict[str, Any]) -> str:
    rendered = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _source_close_observation(
    frame: pd.DataFrame,
    *,
    warmup_rows: int,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    if type(frame) is not pd.DataFrame:
        raise ValueError("volatility_target_calibration_frame_invalid")
    if type(warmup_rows) is not int or warmup_rows < 1:
        raise ValueError("volatility_target_warmup_rows_invalid")
    if (
        "close" not in frame.columns
        or not pd.api.types.is_numeric_dtype(frame["close"].dtype)
        or len(frame) < warmup_rows + 2
    ):
        raise ValueError("volatility_target_calibration_frame_too_short")
    if (
        type(frame.index) is not pd.DatetimeIndex
        or not frame.index.is_unique
        or not frame.index.is_monotonic_increasing
    ):
        raise ValueError("volatility_target_calibration_index_invalid")
    values: list[float] = []
    rows: list[dict[str, Any]] = []
    for position in range(warmup_rows - 1, len(frame)):
        close = float(frame["close"].iloc[position])
        if not math.isfinite(close) or close <= 0:
            raise ValueError("volatility_target_calibration_close_invalid")
        values.append(close)
        rows.append({
            "time": pd.Timestamp(frame.index[position]).isoformat(),
            "close": close,
        })
    returns = [values[index] / values[index - 1] - 1.0 for index in range(1, len(values))]
    factor = annualization_factor(market, timeframe)
    return {
        "data_hash": _canonical_hash({"rows": rows}),
        "times": [str(item) for item in frame.index[warmup_rows:]],
        "annualization_factor": factor,
        "annualized_volatility": annualized_volatility(returns, factor),
        "start_time": rows[1]["time"],
        "end_time": rows[-1]["time"],
        "row_count": len(returns),
    }


def build_prior_window_volatility_target_calibration(
    strategy_record: dict[str, Any],
    calibration_frame: pd.DataFrame,
    *,
    target_role: str,
    calibration_role: str,
    initial_equity: float,
    market: str,
    timeframe: str,
    warmup_rows: int = RESEARCH_BACKTEST_WARMUP_ROWS,
    exposure_cap: float = 1.0,
) -> dict[str, Any]:
    """Calibrate target exposure only from a strictly prior evaluation role."""

    expected_map = {
        "VALIDATION": "TRAIN",
        "FROZEN_TEST": "VALIDATION",
    }
    if (
        type(target_role) is not str
        or type(calibration_role) is not str
        or expected_map.get(target_role) != calibration_role
    ):
        raise ValueError("volatility_target_role_mapping_invalid")
    if (
        type(strategy_record) is not dict
        or strategy_record.get("run_kind") != "REGISTERED_STRATEGY"
        or strategy_record.get("role") != calibration_role
        or strategy_record.get("scenario_id") != "BASE"
    ):
        raise ValueError("volatility_target_strategy_source_invalid")
    cap = _number(exposure_cap, label="exposure_cap", positive=True)
    if cap > 1:
        raise ValueError("volatility_target_exposure_cap_invalid")
    equity = observed_equity_annualized_volatility(
        strategy_record,
        initial_equity=initial_equity,
        market=market,
        timeframe=timeframe,
    )
    source = _source_close_observation(
        calibration_frame,
        warmup_rows=warmup_rows,
        market=market,
        timeframe=timeframe,
    )
    if equity["times"] != source["times"]:
        raise ValueError("volatility_target_calibration_time_grid_mismatch")
    target_volatility = equity["annualized_volatility"]
    source_volatility = source["annualized_volatility"]
    blockers: list[str] = []
    raw_exposure: float | None
    if source_volatility == 0:
        if target_volatility == 0:
            raw_exposure = 0.0
        else:
            raw_exposure = None
            blockers.append("CALIBRATION_SOURCE_VOLATILITY_ZERO")
    else:
        raw_exposure = target_volatility / source_volatility
    applied_exposure = 0.0 if raw_exposure is None else min(cap, raw_exposure)
    core = {
        "schema_version": VOLATILITY_TARGET_BASELINE_SCHEMA_VERSION,
        "benchmark_id": VOLATILITY_TARGET_BASELINE_ID,
        "method_version": VOLATILITY_TARGET_METHOD_VERSION,
        "target_role": target_role,
        "calibration_role": calibration_role,
        "calibration_strategy_scenario": "BASE",
        "calibration_strategy_run_hash": equity["run_hash"],
        "calibration_data_hash": source["data_hash"],
        "calibration_start_time": source["start_time"],
        "calibration_end_time": source["end_time"],
        "calibration_rows": source["row_count"],
        "annualization_factor": source["annualization_factor"],
        "target_annualized_volatility": _clean(target_volatility),
        "source_annualized_volatility": _clean(source_volatility),
        "raw_exposure": None if raw_exposure is None else _clean(raw_exposure),
        "applied_exposure": _clean(applied_exposure),
        "exposure_cap": _clean(cap),
        "exposure_capped": raw_exposure is not None and raw_exposure > cap,
        "calibration_status": "CALIBRATED" if not blockers else "UNKNOWN",
        "blockers": blockers,
        "authority": dict(VOLATILITY_TARGET_AUTHORITY_LOCK),
    }
    return {
        **core,
        "calibration_hash": _canonical_hash(core),
    }


def verify_prior_window_volatility_target_calibration(
    value: Any,
    strategy_record: dict[str, Any],
    calibration_frame: pd.DataFrame,
    **kwargs: Any,
) -> bool:
    if type(value) is not dict:
        raise ValueError("volatility_target_calibration_type_invalid")
    expected = build_prior_window_volatility_target_calibration(
        strategy_record,
        calibration_frame,
        **kwargs,
    )
    if value != expected:
        raise ValueError("volatility_target_calibration_verification_failed")
    return True


class _PriorWindowVolatilityTargetBuyAndHoldStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        position_pct = self.get("position_pct", 0.0)
        if position_pct <= 0:
            return Signal.hold("prior-window volatility target is zero or unavailable")
        if portfolio.position_qty <= 0:
            return Signal.buy(
                "prior-window volatility-target buy-and-hold",
                size_pct=position_pct,
            )
        return Signal.hold("prior-window volatility-target invested")


def build_prior_window_volatility_target_strategy(
    calibration: dict[str, Any],
) -> StrategyBase:
    if type(calibration) is not dict:
        raise ValueError("volatility_target_calibration_type_invalid")
    core = {
        key: value
        for key, value in calibration.items()
        if key != "calibration_hash"
    }
    if (
        set(calibration) != {*_CALIBRATION_CORE_FIELDS, "calibration_hash"}
        or set(core) != _CALIBRATION_CORE_FIELDS
        or calibration.get("schema_version") != VOLATILITY_TARGET_BASELINE_SCHEMA_VERSION
        or calibration.get("benchmark_id") != VOLATILITY_TARGET_BASELINE_ID
        or calibration.get("method_version") != VOLATILITY_TARGET_METHOD_VERSION
        or calibration.get("calibration_hash") != _canonical_hash(core)
        or calibration.get("authority") != VOLATILITY_TARGET_AUTHORITY_LOCK
        or calibration.get("calibration_status") not in {"CALIBRATED", "UNKNOWN"}
        or type(calibration.get("blockers")) is not list
        or (
            calibration.get("calibration_status") == "CALIBRATED"
            and calibration.get("blockers") != []
        )
        or (
            calibration.get("calibration_status") == "UNKNOWN"
            and calibration.get("blockers") == []
        )
    ):
        raise ValueError("volatility_target_calibration_identity_invalid")
    position_pct = _number(
        calibration.get("applied_exposure"),
        label="applied_exposure",
    )
    if not 0 <= position_pct <= 1:
        raise ValueError("volatility_target_applied_exposure_invalid")
    params = {
        "position_pct": position_pct,
        "target_role": calibration["target_role"],
        "calibration_role": calibration["calibration_role"],
        "calibration_hash": calibration["calibration_hash"],
        "calibration_status": calibration["calibration_status"],
        "exposure_cap": calibration["exposure_cap"],
    }
    return _PriorWindowVolatilityTargetBuyAndHoldStrategy(
        params=params,
        name="prior_window_volatility_target_buy_and_hold_benchmark",
        version=VOLATILITY_TARGET_STRATEGY_VERSION,
    )


__all__ = [
    "VOLATILITY_TARGET_AUTHORITY_LOCK",
    "VOLATILITY_TARGET_BASELINE_ID",
    "VOLATILITY_TARGET_BASELINE_SCHEMA_VERSION",
    "VOLATILITY_TARGET_METHOD_VERSION",
    "VOLATILITY_TARGET_STRATEGY_VERSION",
    "build_prior_window_volatility_target_calibration",
    "build_prior_window_volatility_target_strategy",
    "verify_prior_window_volatility_target_calibration",
    "volatility_target_method_spec",
]
