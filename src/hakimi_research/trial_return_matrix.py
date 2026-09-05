from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from typing import Any


SCHEMA_VERSION = "strategy-trial-return-matrix-v1"
RECEIPT_SCHEMA_VERSION = "strategy-trial-return-matrix-receipt-v1"
RETURN_CONVENTION = "SIMPLE_NET_RETURN_FROM_EQUITY_T_OVER_EQUITY_T_MINUS_1"
EVIDENCE_STATE = "OBSERVED"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_TRIAL_RETURN_MATRIX_ONLY"

_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "DEFLATED_SHARPE_RATIO_NOT_COMPUTED",
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_COMPUTED",
    "REAL_MARKET_DATA_NOT_USED",
]
_OBSERVATION_KEYS = {
    "run_id",
    "phase",
    "window_id",
    "parameter_id",
    "status",
    "failure_code",
    "dataset_sha256",
    "result_sha256",
    "source_run_sha256",
    "total_return",
    "max_drawdown",
    "sharpe_ratio",
    "trade_count",
    "record_sha256",
}
_RUN_KEYS = {
    "run_id",
    "evaluation_role",
    "dataset_sha256",
    "cost_multiplier",
    "fee_rate",
    "slippage_pct",
    "result",
    "result_sha256",
    "run_sha256",
}


class TrialReturnMatrixError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise TrialReturnMatrixError(f"{path}: {message}")


def _require_exact_native(value: Any, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "must be finite")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_native(item, f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "keys must be exact str")
            _require_exact_native(item, f"{path}.{key}")
        return
    _fail(path, f"unsupported native type {value_type.__name__}")


def canonical_trial_return_matrix_sha256(value: Any) -> str:
    _require_exact_native(value)
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _require_text(value: Any, path: str) -> str:
    if type(value) is not str or not value:
        _fail(path, "must be a non-empty exact str")
    return value


def _require_hash(value: Any, path: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        _fail(path, "must be a lowercase SHA-256")
    return value


def _require_positive_int(value: Any, path: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(path, "must be a positive exact int")
    return value


def _decimal(value: Any, path: str) -> str:
    if type(value) not in (int, float):
        _fail(path, "must be an exact non-bool number")
    numeric = float(value)
    if not math.isfinite(numeric):
        _fail(path, "must be finite")
    if numeric == 0.0:
        return "0"
    return format(numeric, ".17g")


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    if type(record) is not dict:
        _fail(path, "must be an exact dict")
    digest = _require_hash(record.get(field), f"{path}.{field}")
    payload = {key: value for key, value in record.items() if key != field}
    if canonical_trial_return_matrix_sha256(payload) != digest:
        _fail(f"{path}.{field}", "digest mismatch")


def _normalise_curve(value: Any, path: str) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) < 2:
        _fail(path, "must contain at least two equity observations")
    curve: list[dict[str, Any]] = []
    previous_time: str | None = None
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if type(item) is not dict or set(item) != {"time", "equity"}:
            _fail(item_path, "must contain exactly time and equity")
        timestamp = _require_text(item["time"], f"{item_path}.time")
        equity = item["equity"]
        if type(equity) not in (int, float) or not math.isfinite(float(equity)):
            _fail(f"{item_path}.equity", "must be a finite exact number")
        if float(equity) <= 0.0:
            _fail(f"{item_path}.equity", "must be positive")
        if previous_time is not None and timestamp <= previous_time:
            _fail(f"{item_path}.time", "must be strictly increasing and unique")
        previous_time = timestamp
        curve.append({"time": timestamp, "equity": float(equity)})
    return curve


def _candidate_row(
    cell: dict[str, Any],
    *,
    expected_trial_id: str,
    expected_evaluation_role: str,
    path: str,
) -> tuple[dict[str, Any], list[str], str, dict[str, Any]]:
    if type(cell) is not dict or set(cell) != {
        "trial_id",
        "source_observation",
        "source_run",
    }:
        _fail(path, "must contain exactly trial_id, source_observation, source_run")
    if cell["trial_id"] != expected_trial_id:
        _fail(f"{path}.trial_id", "must preserve preregistered order")

    observation = cell["source_observation"]
    if type(observation) is not dict or set(observation) != _OBSERVATION_KEYS:
        _fail(f"{path}.source_observation", "shape mismatch")
    _verify_seal(observation, "record_sha256", f"{path}.source_observation")
    if (
        observation["phase"] != "FROZEN_STABILITY"
        or observation["window_id"] is not None
        or observation["parameter_id"] != expected_trial_id
    ):
        _fail(f"{path}.source_observation", "identity mismatch")
    if observation["status"] != "OBSERVED" or observation["failure_code"] is not None:
        _fail(f"{path}.source_observation", "failed trials cannot enter the matrix")

    run = cell["source_run"]
    if type(run) is not dict or set(run) != _RUN_KEYS:
        _fail(f"{path}.source_run", "shape mismatch")
    _require_exact_native(run, f"{path}.source_run")
    _verify_seal(run, "run_sha256", f"{path}.source_run")
    if run["run_id"] != observation["run_id"]:
        _fail(f"{path}.source_run.run_id", "must match compact observation")
    if run["evaluation_role"] != expected_evaluation_role:
        _fail(f"{path}.source_run.evaluation_role", "role mismatch")
    dataset_sha256 = _require_hash(run["dataset_sha256"], f"{path}.source_run.dataset_sha256")
    if dataset_sha256 != observation["dataset_sha256"]:
        _fail(f"{path}.source_run.dataset_sha256", "must match compact observation")
    if type(run["cost_multiplier"]) is not int or run["cost_multiplier"] <= 0:
        _fail(f"{path}.source_run.cost_multiplier", "must be a positive exact int")
    if type(run["fee_rate"]) is not float or run["fee_rate"] < 0.0:
        _fail(f"{path}.source_run.fee_rate", "must be a non-negative exact float")
    if type(run["slippage_pct"]) is not float or run["slippage_pct"] < 0.0:
        _fail(f"{path}.source_run.slippage_pct", "must be a non-negative exact float")
    result = run["result"]
    if type(result) is not dict:
        _fail(f"{path}.source_run.result", "must be an exact dict")
    result_sha256 = _require_hash(run["result_sha256"], f"{path}.source_run.result_sha256")
    if canonical_trial_return_matrix_sha256(result) != result_sha256:
        _fail(f"{path}.source_run.result_sha256", "result digest mismatch")
    if result_sha256 != observation["result_sha256"]:
        _fail(f"{path}.source_run.result_sha256", "must match compact observation")
    if run["run_sha256"] != observation["source_run_sha256"]:
        _fail(f"{path}.source_run.run_sha256", "must match compact observation")
    manifest = result.get("experiment_manifest")
    if type(manifest) is not dict or manifest.get("research_only") is not True:
        _fail(f"{path}.source_run.result.experiment_manifest", "research lock missing")
    for field in (
        "live_order_allowed",
        "order_entry_allowed",
        "paper_authorized",
        "result_is_profitability_proof",
    ):
        if manifest.get(field) is not False:
            _fail(f"{path}.source_run.result.experiment_manifest.{field}", "authority escalation")

    curve = _normalise_curve(result.get("equity_curve"), f"{path}.source_run.result.equity_curve")
    times = [item["time"] for item in curve[1:]]
    period_returns = [
        _decimal(
            (current["equity"] / previous["equity"]) - 1.0,
            f"{path}.period_returns[{index}]",
        )
        for index, (previous, current) in enumerate(zip(curve, curve[1:]))
    ]
    cost_model = {
        "cost_multiplier": run["cost_multiplier"],
        "fee_rate": _decimal(run["fee_rate"], f"{path}.source_run.fee_rate"),
        "slippage_pct": _decimal(run["slippage_pct"], f"{path}.source_run.slippage_pct"),
    }
    row = {
        "trial_id": expected_trial_id,
        "source_observation": deepcopy(observation),
        "source_run": deepcopy(run),
        "period_return_count": len(period_returns),
        "period_returns": period_returns,
        "period_returns_sha256": canonical_trial_return_matrix_sha256(period_returns),
    }
    return _seal(row, "row_sha256"), times, dataset_sha256, cost_model


def build_strategy_trial_return_matrix(
    *,
    strategy_id: str,
    search_family_id: str,
    observation_class: str,
    source_plan_sha256: str,
    source_robustness_bundle_sha256: str,
    source_run_ledger_sha256: str,
    preregistered_trial_ids: list[str],
    selected_trial_id: str,
    selection_rule: str,
    evaluation_role: str,
    periods_per_year: int,
    candidate_cells: list[dict[str, Any]],
) -> dict[str, Any]:
    strategy = _require_text(strategy_id, "strategy_id")
    search_family = _require_text(search_family_id, "search_family_id")
    observation = _require_text(observation_class, "observation_class")
    plan_sha256 = _require_hash(source_plan_sha256, "source_plan_sha256")
    robustness_sha256 = _require_hash(
        source_robustness_bundle_sha256, "source_robustness_bundle_sha256"
    )
    ledger_sha256 = _require_hash(source_run_ledger_sha256, "source_run_ledger_sha256")
    selected = _require_text(selected_trial_id, "selected_trial_id")
    selection = _require_text(selection_rule, "selection_rule")
    role = _require_text(evaluation_role, "evaluation_role")
    annualisation = _require_positive_int(periods_per_year, "periods_per_year")
    _require_exact_native(preregistered_trial_ids, "preregistered_trial_ids")
    _require_exact_native(candidate_cells, "candidate_cells")
    if type(preregistered_trial_ids) is not list or len(preregistered_trial_ids) < 2:
        _fail("preregistered_trial_ids", "must contain at least two trials")
    if preregistered_trial_ids != sorted(preregistered_trial_ids):
        _fail("preregistered_trial_ids", "must be lexically sorted")
    if len(set(preregistered_trial_ids)) != len(preregistered_trial_ids):
        _fail("preregistered_trial_ids", "must be unique")
    for index, trial_id in enumerate(preregistered_trial_ids):
        _require_text(trial_id, f"preregistered_trial_ids[{index}]")
    if selected not in preregistered_trial_ids:
        _fail("selected_trial_id", "must be preregistered")
    if type(candidate_cells) is not list or len(candidate_cells) != len(preregistered_trial_ids):
        _fail("candidate_cells", "must cover every preregistered trial exactly once")

    rows: list[dict[str, Any]] = []
    observation_times: list[str] | None = None
    dataset_sha256: str | None = None
    cost_model: dict[str, Any] | None = None
    for index, trial_id in enumerate(preregistered_trial_ids):
        row, times, row_dataset_sha256, row_cost_model = _candidate_row(
            candidate_cells[index],
            expected_trial_id=trial_id,
            expected_evaluation_role=role,
            path=f"candidate_cells[{index}]",
        )
        if observation_times is None:
            observation_times = times
            dataset_sha256 = row_dataset_sha256
            cost_model = row_cost_model
        else:
            if times != observation_times:
                _fail(f"candidate_cells[{index}]", "candidate timestamps are not aligned")
            if row_dataset_sha256 != dataset_sha256:
                _fail(f"candidate_cells[{index}]", "candidate dataset mismatch")
            if row_cost_model != cost_model:
                _fail(f"candidate_cells[{index}]", "candidate cost model mismatch")
        rows.append(row)

    assert observation_times is not None
    assert dataset_sha256 is not None
    assert cost_model is not None
    cost_model = _seal(cost_model, "cost_model_sha256")
    source_binding = {
        "source_plan_sha256": plan_sha256,
        "source_robustness_bundle_sha256": robustness_sha256,
        "source_run_ledger_sha256": ledger_sha256,
        "dataset_sha256": dataset_sha256,
        "candidate_source_run_sha256s": [
            row["source_run"]["run_sha256"] for row in rows
        ],
    }
    _seal(source_binding, "source_binding_sha256")
    matrix_payload = {
        "observation_times": observation_times,
        "candidate_period_returns": [
            {
                "trial_id": row["trial_id"],
                "period_returns": row["period_returns"],
            }
            for row in rows
        ],
    }
    record = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": strategy,
        "search_family_id": search_family,
        "observation_class": observation,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "evaluation_role": role,
        "return_convention": RETURN_CONVENTION,
        "periods_per_year": annualisation,
        "preregistered_trial_ids": list(preregistered_trial_ids),
        "selected_trial_id": selected,
        "selection_rule": selection,
        "source_binding": source_binding,
        "cost_model": cost_model,
        "observation_times": observation_times,
        "observation_times_sha256": canonical_trial_return_matrix_sha256(observation_times),
        "observation_count": len(observation_times),
        "trial_count": len(rows),
        "candidate_rows": rows,
        "matrix_sha256": canonical_trial_return_matrix_sha256(matrix_payload),
        "gaps": list(_GAPS),
        "authority": dict(_AUTHORITY),
    }
    return _seal(record, "record_sha256")


def verify_strategy_trial_return_matrix(record: dict[str, Any]) -> dict[str, Any]:
    if type(record) is not dict:
        _fail("record", "must be an exact dict")
    _require_exact_native(record, "record")
    if record.get("schema_version") != SCHEMA_VERSION:
        _fail("record.schema_version", f"must equal {SCHEMA_VERSION}")
    candidate_rows = record.get("candidate_rows")
    if type(candidate_rows) is not list:
        _fail("record.candidate_rows", "must be an exact list")
    candidate_cells = [
        {
            "trial_id": row.get("trial_id"),
            "source_observation": row.get("source_observation"),
            "source_run": row.get("source_run"),
        }
        for row in candidate_rows
    ]
    source_binding = record.get("source_binding")
    if type(source_binding) is not dict:
        _fail("record.source_binding", "must be an exact dict")
    expected = build_strategy_trial_return_matrix(
        strategy_id=record.get("strategy_id"),
        search_family_id=record.get("search_family_id"),
        observation_class=record.get("observation_class"),
        source_plan_sha256=source_binding.get("source_plan_sha256"),
        source_robustness_bundle_sha256=source_binding.get(
            "source_robustness_bundle_sha256"
        ),
        source_run_ledger_sha256=source_binding.get("source_run_ledger_sha256"),
        preregistered_trial_ids=record.get("preregistered_trial_ids"),
        selected_trial_id=record.get("selected_trial_id"),
        selection_rule=record.get("selection_rule"),
        evaluation_role=record.get("evaluation_role"),
        periods_per_year=record.get("periods_per_year"),
        candidate_cells=candidate_cells,
    )
    if record != expected:
        _fail("record", "must match deterministic source-bound trial matrix")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "record_sha256": record["record_sha256"],
        "matrix_sha256": record["matrix_sha256"],
        "trial_count": record["trial_count"],
        "observation_count": record["observation_count"],
        "gaps": list(_GAPS),
        "authority": dict(_AUTHORITY),
    }
