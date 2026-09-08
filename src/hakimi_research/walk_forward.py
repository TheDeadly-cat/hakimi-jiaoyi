"""Deterministic fixed-parameter walk-forward research contracts."""

from __future__ import annotations

import hashlib
import json
import math
from statistics import median
from typing import Any

import pandas as pd


WALK_FORWARD_METHOD_VERSION = "fixed-parameter-walk-forward-v1"
WALK_FORWARD_SCHEDULE_SCHEMA_VERSION = "fixed-parameter-walk-forward-schedule-v1"
WALK_FORWARD_SUMMARY_SCHEMA_VERSION = "fixed-parameter-walk-forward-summary-v1"
WALK_FORWARD_AUTHORITY_LOCK = {
    "parameter_selection": False,
    "ranking": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}


def fixed_walk_forward_method_spec() -> dict[str, Any]:
    """Return a fresh preregistered two-fold rolling schedule rule."""

    return {
        "method_version": WALK_FORWARD_METHOD_VERSION,
        "fold_count": 2,
        "calibration_rows": 35,
        "purge_rows": 1,
        "evaluation_rows": 35,
        "first_calibration_start": 0,
        "fold_step_rows": 36,
        "required_rows": 107,
        "cost_scenarios": ["BASE", "DOUBLE_COST", "TRIPLE_COST"],
        "strategy_params_source": "FROZEN_PROTOCOL_FIXED_NO_FITTING",
        "calibration_action": "NONE_FIXED_PARAMETERS",
        "nested_manifest_role": "UNCLASSIFIED",
        "parameter_selection_allowed": False,
        "ranking_allowed": False,
    }


def _frame_hash(frame: pd.DataFrame) -> str:
    rows = [
        [
            str(index),
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            float(row.get("volume", 0.0) or 0.0),
        ]
        for index, row in frame.iterrows()
    ]
    encoded = json.dumps(
        rows,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _window(
    data: pd.DataFrame,
    *,
    name: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    frame = data.iloc[start:end]
    if frame.empty:
        raise ValueError("walk_forward_window_empty")
    return {
        "name": name,
        "start_position": start,
        "end_position_exclusive": end,
        "row_count": end - start,
        "start_time": pd.Timestamp(frame.index[0]).isoformat(),
        "end_time": pd.Timestamp(frame.index[-1]).isoformat(),
        "data_hash": _frame_hash(frame),
    }


def build_fixed_walk_forward_schedule(data: pd.DataFrame) -> dict[str, Any]:
    """Build the fixed two-fold schedule without fitting or selecting parameters."""

    if type(data) is not pd.DataFrame:
        raise ValueError("walk_forward_data_exact_dataframe_required")
    required_columns = {"open", "high", "low", "close", "volume"}
    if (
        not required_columns.issubset(data.columns)
        or any(
            not pd.api.types.is_numeric_dtype(data[column].dtype)
            for column in required_columns
        )
    ):
        raise ValueError("walk_forward_data_columns_invalid")
    if (
        type(data.index) is not pd.DatetimeIndex
        or not data.index.is_unique
        or not data.index.is_monotonic_increasing
    ):
        raise ValueError("walk_forward_data_index_invalid")
    method = fixed_walk_forward_method_spec()
    if len(data) < method["required_rows"]:
        raise ValueError("walk_forward_data_too_short")
    folds: list[dict[str, Any]] = []
    for index in range(method["fold_count"]):
        calibration_start = method["first_calibration_start"] + index * method["fold_step_rows"]
        calibration_end = calibration_start + method["calibration_rows"]
        purge_end = calibration_end + method["purge_rows"]
        evaluation_end = purge_end + method["evaluation_rows"]
        folds.append({
            "fold_id": f"WF{index + 1:02d}",
            "calibration": _window(
                data,
                name="CALIBRATION",
                start=calibration_start,
                end=calibration_end,
            ),
            "purge": _window(
                data,
                name="PURGE",
                start=calibration_end,
                end=purge_end,
            ),
            "evaluation": _window(
                data,
                name="EVALUATION",
                start=purge_end,
                end=evaluation_end,
            ),
        })
    core = {
        "schema_version": WALK_FORWARD_SCHEDULE_SCHEMA_VERSION,
        "method_version": WALK_FORWARD_METHOD_VERSION,
        "source_row_count": len(data),
        "required_rows": method["required_rows"],
        "unused_tail_rows": len(data) - method["required_rows"],
        "folds": folds,
        "authority": dict(WALK_FORWARD_AUTHORITY_LOCK),
    }
    encoded = json.dumps(
        core,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **core,
        "schedule_hash": hashlib.sha256(encoded).hexdigest(),
    }


def verify_fixed_walk_forward_schedule(value: Any, data: pd.DataFrame) -> bool:
    if type(value) is not dict:
        raise ValueError("walk_forward_schedule_exact_dict_required")
    if value != build_fixed_walk_forward_schedule(data):
        raise ValueError("walk_forward_schedule_verification_failed")
    return True


def _metric(record: dict[str, Any], field: str) -> float:
    result = record.get("result")
    if type(result) is not dict:
        raise ValueError("walk_forward_summary_result_invalid")
    value = result.get(field)
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"walk_forward_summary_{field}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"walk_forward_summary_{field}_invalid")
    return parsed


def _clean(value: float) -> float:
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


def build_fixed_walk_forward_summary(
    runs: list[dict[str, Any]],
    schedule: dict[str, Any],
) -> dict[str, Any]:
    """Summarize every fixed fold without ranking or selecting results."""

    if type(runs) is not list or type(schedule) is not dict:
        raise ValueError("walk_forward_summary_input_type_invalid")
    fold_ids = [item["fold_id"] for item in schedule.get("folds", [])]
    if fold_ids != ["WF01", "WF02"]:
        raise ValueError("walk_forward_summary_schedule_invalid")
    scenario_ids = ["BASE", "DOUBLE_COST", "TRIPLE_COST"]
    expected = {(fold_id, scenario_id) for fold_id in fold_ids for scenario_id in scenario_ids}
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in runs:
        if type(record) is not dict:
            raise ValueError("walk_forward_summary_run_invalid")
        if type(record.get("result")) is not dict or type(
            record.get("experiment_manifest")
        ) is not dict:
            raise ValueError("walk_forward_summary_run_invalid")
        identity = (record.get("fold_id"), record.get("scenario_id"))
        if identity in observed or identity not in expected:
            raise ValueError("walk_forward_summary_run_identity_invalid")
        observed[identity] = record
    if set(observed) != expected:
        raise ValueError("walk_forward_summary_matrix_incomplete")
    summaries: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        records = [observed[(fold_id, scenario_id)] for fold_id in fold_ids]
        returns = [_metric(record, "total_return") for record in records]
        drawdowns = [_metric(record, "max_drawdown") for record in records]
        summaries.append({
            "scenario_id": scenario_id,
            "fold_count": len(records),
            "fold_ids": list(fold_ids),
            "median_total_return": _clean(median(returns)),
            "minimum_total_return": _clean(min(returns)),
            "maximum_total_return": _clean(max(returns)),
            "median_max_drawdown": _clean(median(drawdowns)),
            "nested_reproducibility_pass": all(
                record["experiment_manifest"].get("status") == "PASS"
                for record in records
            ),
        })
    core = {
        "schema_version": WALK_FORWARD_SUMMARY_SCHEMA_VERSION,
        "method_version": WALK_FORWARD_METHOD_VERSION,
        "schedule_hash": schedule["schedule_hash"],
        "scenario_summaries": summaries,
        "parameter_selection_performed": False,
        "ranking_performed": False,
        "authority": dict(WALK_FORWARD_AUTHORITY_LOCK),
    }
    encoded = json.dumps(
        core,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **core,
        "summary_hash": hashlib.sha256(encoded).hexdigest(),
    }


__all__ = [
    "WALK_FORWARD_AUTHORITY_LOCK",
    "WALK_FORWARD_METHOD_VERSION",
    "WALK_FORWARD_SCHEDULE_SCHEMA_VERSION",
    "WALK_FORWARD_SUMMARY_SCHEMA_VERSION",
    "build_fixed_walk_forward_schedule",
    "build_fixed_walk_forward_summary",
    "fixed_walk_forward_method_spec",
    "verify_fixed_walk_forward_schedule",
]
