from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hakimi_research.cscv_pbo_diagnostic import (
    CscvPboDiagnosticError,
    build_cscv_pbo_diagnostic,
    verify_cscv_pbo_diagnostic,
)
from hakimi_research.cscv_pbo_tie_bounds import (
    build_cscv_pbo_tie_bounds,
    verify_cscv_pbo_tie_bounds,
)
from hakimi_research.deflated_sharpe_diagnostic import (
    DeflatedSharpeDiagnosticError,
    build_deflated_sharpe_diagnostic,
    verify_deflated_sharpe_diagnostic,
)
from hakimi_research.trial_return_matrix import (
    build_strategy_trial_return_matrix,
    canonical_trial_return_matrix_sha256,
    verify_strategy_trial_return_matrix,
)


SCHEMA_VERSION = "frozen-statistical-correction-evidence-v1"
RECEIPT_SCHEMA_VERSION = "frozen-statistical-correction-receipt-v1"
_ROLES = {"VALIDATION", "FROZEN_TEST"}
_AUTHORITY = {
    "formal_inference": False,
    "parameter_selection": False,
    "ranking": False,
    "profitability_proven": False,
    "paper_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
}


class FrozenStatisticalCorrectionError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise FrozenStatisticalCorrectionError(f"{path}: {message}")


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = canonical_trial_return_matrix_sha256(value)
    return value


def _dsr_gap_code(detail: str) -> str:
    if "must have positive finite sample variance" in detail:
        return "DSR_TRIAL_RETURN_VARIANCE_NON_POSITIVE"
    if "effective_independent_trial_count: must exceed one" in detail:
        return "DSR_EFFECTIVE_INDEPENDENT_TRIAL_COUNT_NOT_ABOVE_ONE"
    return "DSR_CANONICAL_PRECONDITION_FAILED"


def _pbo_gap_code(detail: str) -> str:
    if "insufficient observations for eight CSCV partitions" in detail:
        return "PBO_INSUFFICIENT_OBSERVATIONS_FOR_EIGHT_PARTITIONS"
    return "PBO_CANONICAL_PRECONDITION_FAILED"


def _diagnostic_gap(code: str, detail: str) -> dict[str, Any]:
    return {
        "state": "GAP",
        "gap_code": code,
        "failure_detail": detail,
        "diagnostic": None,
        "receipt": None,
    }


def _source_cell(record: dict[str, Any], role: str) -> dict[str, Any]:
    if type(record) is not dict:
        _fail("parameter_stability_runs", "each run must be an exact dict")
    cell_id = record.get("cell_id")
    result_value = record.get("result")
    manifest_value = record.get("experiment_manifest")
    if (
        type(cell_id) is not str
        or not cell_id
        or record.get("role") != role
        or type(result_value) is not dict
        or type(manifest_value) is not dict
    ):
        _fail("parameter_stability_runs", "run identity or source shape invalid")
    result = {**deepcopy(result_value), "experiment_manifest": deepcopy(manifest_value)}
    result_sha256 = canonical_trial_return_matrix_sha256(result)
    reproducibility = result_value.get("reproducibility")
    if type(reproducibility) is not dict:
        _fail(f"parameter_stability_runs.{cell_id}", "reproducibility missing")
    dataset_sha256 = reproducibility.get("data_hash")
    run = _seal({
        "run_id": f"FROZEN_PARAMETER_STABILITY:{role}:{cell_id}",
        "evaluation_role": role,
        "dataset_sha256": dataset_sha256,
        "cost_multiplier": 1,
        "fee_rate": float(record.get("fee_rate")),
        "slippage_pct": float(record.get("slippage_pct")),
        "result": result,
        "result_sha256": result_sha256,
    }, "run_sha256")
    observation = _seal({
        "run_id": run["run_id"],
        "phase": "FROZEN_STABILITY",
        "window_id": None,
        "parameter_id": cell_id,
        "status": "OBSERVED",
        "failure_code": None,
        "dataset_sha256": dataset_sha256,
        "result_sha256": result_sha256,
        "source_run_sha256": run["run_sha256"],
        "total_return": result_value.get("total_return"),
        "max_drawdown": result_value.get("max_drawdown"),
        "sharpe_ratio": result_value.get("sharpe_ratio"),
        "trade_count": result_value.get("trades"),
    }, "record_sha256")
    return {
        "trial_id": cell_id,
        "source_observation": observation,
        "source_run": run,
    }


def _build_matrix(
    *,
    role: str,
    strategy_id: str,
    stability_contract: dict[str, Any],
    stability_runs: list[dict[str, Any]],
    stability_summary: dict[str, Any],
    periods_per_year: int,
) -> dict[str, Any]:
    if type(role) is not str or role not in _ROLES:
        _fail("role", "must be an exact supported role")
    if type(strategy_id) is not str or not strategy_id:
        _fail("strategy_id", "must be a non-empty exact str")
    if type(stability_contract) is not dict or type(stability_summary) is not dict:
        _fail("stability_contract", "contracts must be exact dicts")
    if type(stability_runs) is not list:
        _fail("stability_runs", "must be an exact list")
    source_records = sorted(
        (record for record in stability_runs if type(record) is dict and record.get("role") == role),
        key=lambda record: record.get("cell_id", ""),
    )
    if len(source_records) != 21:
        _fail("stability_runs", "must contain exactly 21 runs for the role")
    centers = [record for record in source_records if record.get("is_center") is True]
    if len(centers) != 1:
        _fail("stability_runs", "must contain exactly one preregistered center")
    candidate_cells = [_source_cell(record, role) for record in source_records]
    trial_ids = [cell["trial_id"] for cell in candidate_cells]
    source_plan = {
        "strategy_id": strategy_id,
        "role": role,
        "stability_contract": stability_contract,
    }
    source_run_ledger_sha256 = canonical_trial_return_matrix_sha256(
        [cell["source_run"]["run_sha256"] for cell in candidate_cells]
    )
    summary_hash = stability_summary.get("summary_hash")
    return build_strategy_trial_return_matrix(
        strategy_id=strategy_id,
        search_family_id="FROZEN_PARAMETER_STABILITY",
        observation_class=f"{role}_BASE_PARAMETER_STABILITY",
        source_plan_sha256=canonical_trial_return_matrix_sha256(source_plan),
        source_robustness_bundle_sha256=summary_hash,
        source_run_ledger_sha256=source_run_ledger_sha256,
        preregistered_trial_ids=trial_ids,
        selected_trial_id=centers[0]["cell_id"],
        selection_rule="PREREGISTERED_CENTER_NO_PERFORMANCE_SELECTION",
        evaluation_role=role,
        periods_per_year=periods_per_year,
        candidate_cells=candidate_cells,
    )


def _matrix_projection(matrix: dict[str, Any]) -> dict[str, Any]:
    binding = matrix["source_binding"]
    return {
        "schema_version": matrix["schema_version"],
        "record_sha256": matrix["record_sha256"],
        "matrix_sha256": matrix["matrix_sha256"],
        "source_binding_sha256": binding["source_binding_sha256"],
        "source_run_ledger_sha256": binding["source_run_ledger_sha256"],
        "dataset_sha256": binding["dataset_sha256"],
        "cost_model_sha256": matrix["cost_model"]["cost_model_sha256"],
        "trial_count": matrix["trial_count"],
        "observation_count": matrix["observation_count"],
        "selected_trial_id": matrix["selected_trial_id"],
        "selection_rule": matrix["selection_rule"],
        "periods_per_year": matrix["periods_per_year"],
    }


def build_frozen_statistical_correction_evidence(
    *,
    role: str,
    strategy_id: str,
    stability_contract: dict[str, Any],
    stability_runs: list[dict[str, Any]],
    stability_summary: dict[str, Any],
    periods_per_year: int,
) -> dict[str, Any]:
    matrix = _build_matrix(
        role=role,
        strategy_id=strategy_id,
        stability_contract=stability_contract,
        stability_runs=stability_runs,
        stability_summary=stability_summary,
        periods_per_year=periods_per_year,
    )
    verify_strategy_trial_return_matrix(matrix)

    try:
        dsr_diagnostic = build_deflated_sharpe_diagnostic(matrix)
        dsr_receipt = verify_deflated_sharpe_diagnostic(dsr_diagnostic, matrix)
        dsr = {
            "state": "OBSERVED",
            "gap_code": None,
            "failure_detail": None,
            "diagnostic": dsr_diagnostic,
            "receipt": dsr_receipt,
        }
    except DeflatedSharpeDiagnosticError as exc:
        detail = str(exc)
        dsr = _diagnostic_gap(_dsr_gap_code(detail), detail)

    try:
        pbo_diagnostic = build_cscv_pbo_diagnostic(matrix)
        pbo_receipt = verify_cscv_pbo_diagnostic(pbo_diagnostic, matrix)
        tie_bounds = build_cscv_pbo_tie_bounds(pbo_diagnostic)
        tie_bounds_receipt = verify_cscv_pbo_tie_bounds(tie_bounds, pbo_diagnostic)
        pbo = {
            "state": "OBSERVED",
            "gap_code": None,
            "failure_detail": None,
            "diagnostic": pbo_diagnostic,
            "receipt": pbo_receipt,
            "tie_bounds": tie_bounds,
            "tie_bounds_receipt": tie_bounds_receipt,
        }
    except CscvPboDiagnosticError as exc:
        detail = str(exc)
        pbo = {
            **_diagnostic_gap(_pbo_gap_code(detail), detail),
            "tie_bounds": None,
            "tie_bounds_receipt": None,
        }

    estimable = dsr["state"] == "OBSERVED" and pbo["state"] == "OBSERVED"
    gaps = [
        item
        for item in (dsr["gap_code"], pbo["gap_code"])
        if item is not None
    ]
    gaps.extend([
        "FORMAL_INFERENCE_NOT_AUTHORIZED",
        "FORMAL_BLIND_TEST_NOT_PROVEN",
        "REAL_MARKET_DATA_NOT_USED",
    ])
    core = {
        "schema_version": SCHEMA_VERSION,
        "evidence_state": "OBSERVED_WITH_GAPS" if estimable else "GAP",
        "status": "BLOCK",
        "role": role,
        "strategy_id": strategy_id,
        "trial_matrix": _matrix_projection(matrix),
        "deflated_sharpe": dsr,
        "cscv_pbo": pbo,
        "statistical_corrections_estimable": estimable,
        "additional_backtest_run_count": 0,
        "gaps": gaps,
        "authority": dict(_AUTHORITY),
    }
    return {**core, "evidence_sha256": canonical_trial_return_matrix_sha256(core)}


def verify_frozen_statistical_correction_evidence(
    evidence: dict[str, Any],
    *,
    role: str,
    strategy_id: str,
    stability_contract: dict[str, Any],
    stability_runs: list[dict[str, Any]],
    stability_summary: dict[str, Any],
    periods_per_year: int,
) -> dict[str, Any]:
    if type(evidence) is not dict:
        _fail("evidence", "must be an exact dict")
    expected = build_frozen_statistical_correction_evidence(
        role=role,
        strategy_id=strategy_id,
        stability_contract=stability_contract,
        stability_runs=stability_runs,
        stability_summary=stability_summary,
        periods_per_year=periods_per_year,
    )
    if evidence != expected:
        _fail("evidence", "verification failed")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": evidence["evidence_state"],
        "status": evidence["status"],
        "role": evidence["role"],
        "evidence_sha256": evidence["evidence_sha256"],
        "matrix_sha256": evidence["trial_matrix"]["matrix_sha256"],
        "trial_count": evidence["trial_matrix"]["trial_count"],
        "observation_count": evidence["trial_matrix"]["observation_count"],
        "dsr_state": evidence["deflated_sharpe"]["state"],
        "pbo_state": evidence["cscv_pbo"]["state"],
        "additional_backtest_run_count": evidence["additional_backtest_run_count"],
        "gaps": list(evidence["gaps"]),
        "authority": dict(_AUTHORITY),
    }


__all__ = [
    "RECEIPT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "FrozenStatisticalCorrectionError",
    "build_frozen_statistical_correction_evidence",
    "verify_frozen_statistical_correction_evidence",
]
