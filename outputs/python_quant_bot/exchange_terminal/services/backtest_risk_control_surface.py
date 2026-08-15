from __future__ import annotations

import math
from collections import deque
from typing import Any


BACKTEST_RISK_CONTROL_SURFACE_SCHEMA_VERSION = "backtest-risk-control-surface-v1"
BACKTEST_RISK_CONTROL_GRID: dict[str, tuple[float | int, ...]] = {
    "position_pct": (12, 20, 35, 50, 70),
    "take_profit_pct": (1.2, 1.8, 2.6, 3.8, 5.5),
    "stop_loss_pct": (0.7, 1.1, 1.6, 2.4),
}
_AXES = tuple(BACKTEST_RISK_CONTROL_GRID)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _axis_index(axis: str, value: Any) -> int | None:
    parsed = _finite_number(value)
    if parsed is None:
        return None
    for index, expected in enumerate(BACKTEST_RISK_CONTROL_GRID[axis]):
        if parsed == float(expected):
            return index
    return None


def _grid_key(row: dict[str, Any]) -> tuple[int, int, int] | None:
    indexes = tuple(_axis_index(axis, row.get(axis)) for axis in _AXES)
    if any(index is None for index in indexes):
        return None
    return indexes  # type: ignore[return-value]


def _cell_id(key: tuple[int, int, int]) -> str:
    values = [BACKTEST_RISK_CONTROL_GRID[axis][key[index]] for index, axis in enumerate(_AXES)]
    return "|".join(f"{axis}={value}" for axis, value in zip(_AXES, values))


def _expected_keys() -> list[tuple[int, int, int]]:
    return [
        (position_index, take_index, stop_index)
        for position_index in range(len(BACKTEST_RISK_CONTROL_GRID["position_pct"]))
        for take_index in range(len(BACKTEST_RISK_CONTROL_GRID["take_profit_pct"]))
        for stop_index in range(len(BACKTEST_RISK_CONTROL_GRID["stop_loss_pct"]))
    ]


def _neighbors(key: tuple[int, int, int]) -> list[tuple[tuple[int, int, int], str]]:
    result: list[tuple[tuple[int, int, int], str]] = []
    for axis_index, axis in enumerate(_AXES):
        for step in (-1, 1):
            candidate = list(key)
            candidate[axis_index] += step
            if 0 <= candidate[axis_index] < len(BACKTEST_RISK_CONTROL_GRID[axis]):
                result.append(((candidate[0], candidate[1], candidate[2]), axis))
    return result


def _public_cell(row: dict[str, Any], key: tuple[int, int, int]) -> dict[str, Any]:
    score = _finite_number(row.get("score"))
    total_return = _finite_number(row.get("total_return_pct"))
    max_drawdown = _finite_number(row.get("max_drawdown_pct"))
    trade_count = _native_nonnegative_int(row.get("trade_count"))
    quality_usable = (
        row.get("ok") is True
        and score is not None
        and total_return is not None
        and max_drawdown is not None
        and max_drawdown >= 0
        and trade_count is not None
        and trade_count > 0
    )
    return {
        "cell_id": _cell_id(key),
        "position_pct": BACKTEST_RISK_CONTROL_GRID["position_pct"][key[0]],
        "take_profit_pct": BACKTEST_RISK_CONTROL_GRID["take_profit_pct"][key[1]],
        "stop_loss_pct": BACKTEST_RISK_CONTROL_GRID["stop_loss_pct"][key[2]],
        "score": score,
        "total_return_pct": total_return,
        "max_drawdown_pct": max_drawdown,
        "trade_count": trade_count,
        "run_ok": row.get("ok") is True,
        "quality_usable": quality_usable,
    }


def build_backtest_risk_control_surface(candidates: Any) -> dict[str, Any]:
    """Describe the existing same-dataset risk-control grid without selecting parameters."""
    rows = candidates if isinstance(candidates, list) else []
    expected_keys = _expected_keys()
    expected_key_set = set(expected_keys)
    mapped: dict[tuple[int, int, int], dict[str, Any]] = {}
    blockers: list[str] = []

    if not isinstance(candidates, list):
        blockers.append("risk_control_surface_candidates_not_a_list")
    for row in rows:
        if not isinstance(row, dict):
            blockers.append("risk_control_surface_candidate_not_an_object")
            continue
        key = _grid_key(row)
        if key is None or key not in expected_key_set:
            blockers.append("risk_control_surface_candidate_outside_frozen_grid")
            continue
        if key in mapped:
            blockers.append("risk_control_surface_duplicate_grid_cell")
            continue
        mapped[key] = _public_cell(row, key)

    missing_count = len(expected_key_set - set(mapped))
    cells = [mapped[key] for key in expected_keys if key in mapped]
    invalid_metric_count = sum(
        1
        for cell in cells
        if cell["score"] is None
        or cell["total_return_pct"] is None
        or cell["max_drawdown_pct"] is None
        or cell["max_drawdown_pct"] < 0
        or cell["trade_count"] is None
    )
    if missing_count:
        blockers.append("risk_control_surface_grid_coverage_incomplete")
    if invalid_metric_count:
        blockers.append("risk_control_surface_cell_metrics_invalid")

    scored = [cell for cell in cells if cell["score"] is not None]
    usable = [cell for cell in cells if cell["quality_usable"] is True]
    best_key: tuple[int, int, int] | None = None
    best_cell: dict[str, Any] | None = None
    if scored:
        best_key = max(
            (key for key in expected_keys if key in mapped and mapped[key]["score"] is not None),
            key=lambda key: (mapped[key]["score"], -expected_keys.index(key)),
        )
        best_cell = mapped[best_key]

    score_tolerance: float | None = None
    near_best_scored_keys: set[tuple[int, int, int]] = set()
    near_best_usable_keys: set[tuple[int, int, int]] = set()
    direct_support: dict[str, int] = {axis: 0 for axis in _AXES}
    connected_keys: set[tuple[int, int, int]] = set()
    if best_key is not None and best_cell is not None:
        best_score = float(best_cell["score"])
        score_tolerance = max(abs(best_score) * 0.25, 1.0)
        near_best_scored_keys = {
            key
            for key, cell in mapped.items()
            if cell["score"] is not None and best_score - float(cell["score"]) <= score_tolerance
        }
        near_best_usable_keys = {
            key for key in near_best_scored_keys if mapped[key]["quality_usable"] is True
        }
        for neighbor, axis in _neighbors(best_key):
            if neighbor in near_best_usable_keys:
                direct_support[axis] += 1
        if best_key in near_best_usable_keys:
            queue: deque[tuple[int, int, int]] = deque([best_key])
            connected_keys.add(best_key)
            while queue:
                current = queue.popleft()
                for neighbor, _axis in _neighbors(current):
                    if neighbor in near_best_usable_keys and neighbor not in connected_keys:
                        connected_keys.add(neighbor)
                        queue.append(neighbor)

    structural_blockers = {
        "risk_control_surface_candidates_not_a_list",
        "risk_control_surface_candidate_not_an_object",
        "risk_control_surface_candidate_outside_frozen_grid",
        "risk_control_surface_duplicate_grid_cell",
        "risk_control_surface_cell_metrics_invalid",
    }
    supported_axis_count = sum(1 for count in direct_support.values() if count > 0)
    if not rows and isinstance(candidates, list):
        status = "NOT_AVAILABLE"
        blockers = ["risk_control_surface_not_available"]
    elif any(blocker in structural_blockers for blocker in blockers):
        status = "BLOCK"
    elif missing_count:
        status = "INCOMPLETE_GRID"
    elif best_cell is None:
        status = "BLOCK"
        blockers.append("risk_control_surface_no_finite_scores")
    elif float(best_cell["score"]) <= 0:
        status = "NON_POSITIVE_SURFACE"
        blockers.append("risk_control_surface_best_score_not_positive")
    elif best_cell["quality_usable"] is not True:
        status = "HIGHEST_SCORE_CELL_UNUSABLE"
        blockers.append("risk_control_surface_highest_score_cell_metrics_unusable")
    elif len(connected_keys) >= 3 and supported_axis_count >= 2:
        status = "LOCAL_PLATEAU"
    else:
        status = "PEAK_ONLY"
        blockers.append("risk_control_surface_peak_without_multiaxis_neighborhood")

    return {
        "schema_version": BACKTEST_RISK_CONTROL_SURFACE_SCHEMA_VERSION,
        "status": status,
        "scope": "SAME_DATASET_DEVELOPMENT_GRID",
        "topology_basis": "ONE_FROZEN_GRID_STEP_PER_AXIS",
        "grid_axis_order": list(_AXES),
        "grid_axes": {axis: list(values) for axis, values in BACKTEST_RISK_CONTROL_GRID.items()},
        "expected_cell_count": len(expected_keys),
        "received_candidate_count": len(rows),
        "mapped_cell_count": len(cells),
        "missing_cell_count": missing_count,
        "invalid_metric_count": invalid_metric_count,
        "scored_cell_count": len(scored),
        "usable_cell_count": len(usable),
        "highest_score_cell": dict(best_cell) if best_cell is not None else None,
        "score_tolerance": score_tolerance,
        "score_tolerance_basis": "MAX_25_PERCENT_OF_BEST_ABSOLUTE_OR_1_POINT",
        "near_best_scored_cell_count": len(near_best_scored_keys),
        "near_best_usable_cell_count": len(near_best_usable_keys),
        "direct_adjacent_near_best_usable_count": sum(direct_support.values()),
        "axis_support": direct_support,
        "supported_axis_count": supported_axis_count,
        "connected_near_best_cell_count": len(connected_keys),
        "connected_near_best_cell_ids": [
            _cell_id(key) for key in expected_keys if key in connected_keys
        ],
        "cells": cells,
        "blockers": list(dict.fromkeys(blockers)),
        "risk_control_parameters_only": True,
        "signal_parameter_stability_checked": False,
        "numeric_parameter_distance_checked": False,
        "same_dataset_grid": True,
        "selection_bias_corrected": False,
        "out_of_sample_parameter_validation": False,
        "frozen_research_evidence": False,
        "research_only": True,
        "descriptive_only": True,
        "parameter_selection_allowed": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "automatic_paper_activation_allowed": False,
        "execution_allowed": False,
        "order_submission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "BACKTEST_RISK_CONTROL_GRID",
    "BACKTEST_RISK_CONTROL_SURFACE_SCHEMA_VERSION",
    "build_backtest_risk_control_surface",
]
