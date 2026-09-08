"""Preregistered no-selection parameter-stability observations."""

from __future__ import annotations

import hashlib
import json
import math
from statistics import median
from typing import Any


PARAMETER_STABILITY_METHOD_VERSION = "dual-ma-fixed-perturbation-matrix-v1"
PARAMETER_STABILITY_CELL_SCHEMA_VERSION = "parameter-stability-cell-v1"
PARAMETER_STABILITY_SUMMARY_SCHEMA_VERSION = "parameter-stability-summary-v1"
PARAMETER_STABILITY_AUTHORITY_LOCK = {
    "parameter_selection": False,
    "ranking": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}

_PARAMETER_FIELDS = frozenset({
    "fast_window",
    "slow_window",
    "position_pct",
    "stop_loss_pct",
    "take_profit_pct",
})


def fixed_parameter_stability_method_spec() -> dict[str, Any]:
    """Return a fresh preregistered dual-MA perturbation rule."""

    return {
        "method_version": PARAMETER_STABILITY_METHOD_VERSION,
        "supported_strategy": "dual_ma",
        "roles": ["VALIDATION", "FROZEN_TEST"],
        "cost_scenario": "BASE",
        "timing_fast_perturbations": [-0.2, 0.0, 0.2],
        "timing_slow_perturbations": [-0.2, -0.1, 0.0, 0.1, 0.2],
        "risk_parameters": ["position_pct", "stop_loss_pct", "take_profit_pct"],
        "risk_perturbations": [-0.2, 0.2],
        "expected_cell_count": 21,
        "nested_manifest_role": "UNCLASSIFIED",
        "all_cells_retained": True,
        "selected_cell_id": None,
        "parameter_selection_allowed": False,
        "ranking_allowed": False,
    }


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ratio(value: Any, *, field: str) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"parameter_stability_{field}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 < parsed <= 1:
        raise ValueError(f"parameter_stability_{field}_invalid")
    return parsed


def _validate_base_params(base_params: dict[str, Any]) -> dict[str, Any]:
    if type(base_params) is not dict or set(base_params) != _PARAMETER_FIELDS:
        raise ValueError("parameter_stability_base_params_invalid")
    fast = base_params["fast_window"]
    slow = base_params["slow_window"]
    if (
        type(fast) is not int
        or type(slow) is not int
        or fast < 2
        or slow < 3
        or fast >= slow
    ):
        raise ValueError("parameter_stability_window_params_invalid")
    return {
        "fast_window": fast,
        "slow_window": slow,
        "position_pct": _ratio(base_params["position_pct"], field="position_pct"),
        "stop_loss_pct": _ratio(base_params["stop_loss_pct"], field="stop_loss_pct"),
        "take_profit_pct": _ratio(base_params["take_profit_pct"], field="take_profit_pct"),
    }


def _cell(
    *,
    cell_id: str,
    segment: str,
    is_center: bool,
    axes: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    core = {
        "schema_version": PARAMETER_STABILITY_CELL_SCHEMA_VERSION,
        "cell_id": cell_id,
        "segment": segment,
        "is_center": is_center,
        "axes": axes,
        "params": params,
        "params_hash": _canonical_hash(params),
    }
    return {
        **core,
        "cell_hash": _canonical_hash(core),
    }


def build_dual_ma_parameter_stability_cells(
    base_params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build all cells around the frozen center without selecting any result."""

    base = _validate_base_params(base_params)
    method = fixed_parameter_stability_method_spec()
    cells: list[dict[str, Any]] = []
    for fast_pct in method["timing_fast_perturbations"]:
        fast = int(round(base["fast_window"] * (1.0 + fast_pct)))
        for slow_pct in method["timing_slow_perturbations"]:
            slow = int(round(base["slow_window"] * (1.0 + slow_pct)))
            if fast >= slow:
                raise ValueError("parameter_stability_generated_window_order_invalid")
            params = {
                **base,
                "fast_window": fast,
                "slow_window": slow,
            }
            cells.append(_cell(
                cell_id=f"TIMING_F{fast:02d}_S{slow:02d}",
                segment="TIMING_GRID",
                is_center=(fast_pct == 0 and slow_pct == 0),
                axes={
                    "fast_window_pct": fast_pct,
                    "slow_window_pct": slow_pct,
                    "risk_parameter": None,
                    "risk_parameter_pct": None,
                },
                params=params,
            ))
    for parameter in method["risk_parameters"]:
        for perturbation in method["risk_perturbations"]:
            params = {
                **base,
                parameter: round(base[parameter] * (1.0 + perturbation), 12),
            }
            direction = "M20" if perturbation < 0 else "P20"
            cells.append(_cell(
                cell_id=f"RISK_{parameter.upper()}_{direction}",
                segment="RISK_OAT",
                is_center=False,
                axes={
                    "fast_window_pct": None,
                    "slow_window_pct": None,
                    "risk_parameter": parameter,
                    "risk_parameter_pct": perturbation,
                },
                params=params,
            ))
    if (
        len(cells) != method["expected_cell_count"]
        or len({item["cell_id"] for item in cells}) != len(cells)
        or len({item["params_hash"] for item in cells}) != len(cells)
        or sum(item["is_center"] for item in cells) != 1
    ):
        raise ValueError("parameter_stability_cell_matrix_invalid")
    return cells


def verify_dual_ma_parameter_stability_cells(
    value: Any,
    base_params: dict[str, Any],
) -> bool:
    if type(value) is not list:
        raise ValueError("parameter_stability_cells_exact_list_required")
    if value != build_dual_ma_parameter_stability_cells(base_params):
        raise ValueError("parameter_stability_cells_verification_failed")
    return True


def _metric(record: dict[str, Any], field: str) -> float:
    result = record.get("result")
    if type(result) is not dict:
        raise ValueError("parameter_stability_summary_result_invalid")
    value = result.get(field)
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"parameter_stability_summary_{field}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"parameter_stability_summary_{field}_invalid")
    return parsed


def _clean(value: float) -> float:
    rounded = round(float(value), 12)
    return 0.0 if rounded == 0 else rounded


def build_parameter_stability_summary(
    runs: list[dict[str, Any]],
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize all observations while leaving selected_cell_id null."""

    if type(runs) is not list or type(cells) is not list:
        raise ValueError("parameter_stability_summary_input_type_invalid")
    if any(
        type(item) is not dict
        or type(item.get("cell_id")) is not str
        or type(item.get("is_center")) is not bool
        for item in cells
    ):
        raise ValueError("parameter_stability_summary_cells_invalid")
    cell_ids = [item["cell_id"] for item in cells]
    roles = ["VALIDATION", "FROZEN_TEST"]
    expected = {(role, cell_id) for role in roles for cell_id in cell_ids}
    observed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in runs:
        if (
            type(record) is not dict
            or type(record.get("result")) is not dict
            or type(record.get("experiment_manifest")) is not dict
            or type(record["experiment_manifest"].get("ranking_gate")) is not dict
        ):
            raise ValueError("parameter_stability_summary_run_invalid")
        identity = (record.get("role"), record.get("cell_id"))
        if identity in observed or identity not in expected:
            raise ValueError("parameter_stability_summary_run_identity_invalid")
        observed[identity] = record
    if set(observed) != expected:
        raise ValueError("parameter_stability_summary_matrix_incomplete")
    center_id = next(item["cell_id"] for item in cells if item["is_center"])
    role_summaries: list[dict[str, Any]] = []
    for role in roles:
        records = [observed[(role, cell_id)] for cell_id in cell_ids]
        returns = [_metric(record, "total_return") for record in records]
        drawdowns = [_metric(record, "max_drawdown") for record in records]
        center_return = _metric(observed[(role, center_id)], "total_return")
        role_summaries.append({
            "role": role,
            "observed_cell_count": len(records),
            "center_cell_id": center_id,
            "center_total_return": _clean(center_return),
            "median_total_return": _clean(median(returns)),
            "minimum_total_return": _clean(min(returns)),
            "maximum_total_return": _clean(max(returns)),
            "maximum_absolute_deviation_from_center": _clean(
                max(abs(item - center_return) for item in returns)
            ),
            "median_max_drawdown": _clean(median(drawdowns)),
            "timing_grid_complete": sum(
                record["segment"] == "TIMING_GRID" for record in records
            ) == 15,
            "risk_oat_complete": sum(
                record["segment"] == "RISK_OAT" for record in records
            ) == 6,
            "center_not_on_timing_boundary": True,
            "all_nested_manifests_non_rankable": all(
                record["experiment_manifest"]["ranking_gate"]["input_allowed"] is False
                for record in records
            ),
        })
    core = {
        "schema_version": PARAMETER_STABILITY_SUMMARY_SCHEMA_VERSION,
        "method_version": PARAMETER_STABILITY_METHOD_VERSION,
        "cell_count": len(cells),
        "role_summaries": role_summaries,
        "all_cells_retained": True,
        "selected_cell_id": None,
        "parameter_selection_performed": False,
        "ranking_performed": False,
        "authority": dict(PARAMETER_STABILITY_AUTHORITY_LOCK),
    }
    return {
        **core,
        "summary_hash": _canonical_hash(core),
    }


__all__ = [
    "PARAMETER_STABILITY_AUTHORITY_LOCK",
    "PARAMETER_STABILITY_CELL_SCHEMA_VERSION",
    "PARAMETER_STABILITY_METHOD_VERSION",
    "PARAMETER_STABILITY_SUMMARY_SCHEMA_VERSION",
    "build_dual_ma_parameter_stability_cells",
    "build_parameter_stability_summary",
    "fixed_parameter_stability_method_spec",
    "verify_dual_ma_parameter_stability_cells",
]
