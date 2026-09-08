from __future__ import annotations

from copy import deepcopy
import math
from statistics import mean, stdev
from typing import Any, Callable

import pandas as pd

from hakimi_research.synthetic_strategy_report_bundle import (
    PERIODS_PER_YEAR,
    _CashBenchmark,
    _build_frame,
    _build_fixture,
    _family_for_strategy,
    _records,
    _run_backtest,
    build_synthetic_strategy_report_bundle_v1,
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
    verify_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.distribution_evidence import build_distribution_evidence
from hakimi_research.validation_evidence import (
    build_validation_evidence,
    verify_validation_evidence,
)
from hakimi_research.strategies import build_strategy


SCHEMA_VERSION = "synthetic-strategy-robustness-evidence-v1"
PLAN_SCHEMA_VERSION = "synthetic-strategy-robustness-plan-v1"
STRATEGY_EVIDENCE_SCHEMA_VERSION = "synthetic-strategy-robustness-record-v1"
REFERENCE_SCHEMA_VERSION = "synthetic-strategy-robustness-evidence-v2"
REFERENCE_PLAN_SCHEMA_VERSION = "synthetic-strategy-robustness-plan-v2"
RUN_REPRODUCIBILITY_LEDGER_SCHEMA_VERSION = (
    "synthetic-strategy-robustness-run-reproducibility-ledger-v1"
)

_STRATEGY_IDS = ("bollinger", "dual_ma", "grid", "macd", "momentum", "rsi")
_AUTHORITY = {
    "profitability_proven": False,
    "blind_test_complete": False,
    "paper_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
}
_WINDOWS = (
    {
        "window_id": "wf-01",
        "train": (0, 99),
        "validation": (105, 204),
        "frozen_test": (210, 309),
        "purge_bars": 5,
        "embargo_bars": 5,
    },
    {
        "window_id": "wf-02",
        "train": (50, 149),
        "validation": (155, 254),
        "frozen_test": (260, 359),
        "purge_bars": 5,
        "embargo_bars": 5,
    },
    {
        "window_id": "wf-03",
        "train": (90, 189),
        "validation": (195, 294),
        "frozen_test": (300, 399),
        "purge_bars": 5,
        "embargo_bars": 5,
    },
)
_PARAMETERS = {
    "bollinger": {
        "center": {"window": 20, "std_mult": 2.0, "position_pct": 0.2},
        "neighbor-high": {"window": 24, "std_mult": 2.2, "position_pct": 0.2},
        "neighbor-low": {"window": 16, "std_mult": 1.8, "position_pct": 0.2},
    },
    "dual_ma": {
        "center": {"fast_window": 20, "slow_window": 60, "position_pct": 0.25},
        "neighbor-high": {"fast_window": 24, "slow_window": 72, "position_pct": 0.25},
        "neighbor-low": {"fast_window": 16, "slow_window": 48, "position_pct": 0.25},
    },
    "grid": {
        "center": {"lookback": 80, "grids": 8, "position_pct": 0.12},
        "neighbor-high": {"lookback": 96, "grids": 10, "position_pct": 0.12},
        "neighbor-low": {"lookback": 64, "grids": 6, "position_pct": 0.12},
    },
    "macd": {
        "center": {"fast": 12, "slow": 26, "signal": 9, "position_pct": 0.25},
        "neighbor-high": {"fast": 14, "slow": 30, "signal": 10, "position_pct": 0.25},
        "neighbor-low": {"fast": 10, "slow": 22, "signal": 8, "position_pct": 0.25},
    },
    "momentum": {
        "center": {"window": 20, "threshold": 0.015, "position_pct": 0.22},
        "neighbor-high": {"window": 24, "threshold": 0.018, "position_pct": 0.22},
        "neighbor-low": {"window": 16, "threshold": 0.012, "position_pct": 0.22},
    },
    "rsi": {
        "center": {"window": 14, "oversold": 30, "overbought": 70, "position_pct": 0.15},
        "neighbor-high": {"window": 16, "oversold": 32, "overbought": 68, "position_pct": 0.15},
        "neighbor-low": {"window": 12, "oversold": 28, "overbought": 72, "position_pct": 0.15},
    },
}
_COMPLETED_EVIDENCE = (
    "WALK_FORWARD_EXECUTED",
    "PARAMETER_STABILITY_EXECUTED",
    "MULTIPLE_TESTING_LEDGER_COMPLETE",
    "BONFERRONI_AND_BH_DIAGNOSTICS_COMPUTED",
)
_GAPS = (
    "REAL_MARKET_DATA_NOT_USED",
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "MARKET_REGIME_ANALYSIS_NOT_EXECUTED",
    "ENSEMBLE_STRATEGY_NOT_IMPLEMENTED",
    "DEPENDENCY_LOCK_NOT_BOUND",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
    "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED",
    "BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED",
    "OVERLAPPING_WALK_FORWARD_WINDOWS_NO_INDEPENDENCE_CLAIM",
)
_REFERENCE_COMPLETED_EVIDENCE = (
    *_COMPLETED_EVIDENCE,
    "DEPENDENCY_LOCK_BOUND_TO_ALL_ROBUSTNESS_RUNS",
)
_REFERENCE_GAPS = tuple(
    gap for gap in _GAPS if gap != "DEPENDENCY_LOCK_NOT_BOUND"
)


class SyntheticStrategyRobustnessError(ValueError):
    pass


def _authority() -> dict[str, bool]:
    return deepcopy(_AUTHORITY)


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        raise SyntheticStrategyRobustnessError(f"duplicate seal field: {field}")
    record[field] = canonical_sha256(record)
    return record


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        raise SyntheticStrategyRobustnessError(f"{path}.{field} is invalid")
    payload = {key: value for key, value in record.items() if key != field}
    if canonical_sha256(payload) != digest:
        raise SyntheticStrategyRobustnessError(f"{path}.{field} mismatch")


def _decimal(value: float | int) -> str:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise SyntheticStrategyRobustnessError("non-finite observation")
    if numeric == 0.0:
        return "0"
    return f"{numeric:.12f}".rstrip("0").rstrip(".")


def _parameter_id(strategy_id: str, variant_id: str) -> str:
    return f"{strategy_id}:{variant_id}"


def _variants(strategy_id: str) -> list[dict[str, Any]]:
    output = []
    for variant_id, parameters in sorted(_PARAMETERS[strategy_id].items()):
        output.append(
            {
                "parameter_id": _parameter_id(strategy_id, variant_id),
                "variant_id": variant_id,
                "parameters": deepcopy(parameters),
                "parameters_sha256": canonical_sha256(parameters),
                "frozen_selection_allowed": False,
            }
        )
    return output


def _planned_runs() -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    for window in _WINDOWS:
        planned.append(
            {
                "run_id": f"benchmark:{window['window_id']}:cash:test",
                "subject_id": "cash",
                "window_id": window["window_id"],
                "phase": "TEST_BENCHMARK",
                "parameter_id": None,
            }
        )
    for strategy_id in _STRATEGY_IDS:
        for window in _WINDOWS:
            for variant in _variants(strategy_id):
                for phase in ("TRAIN", "VALIDATION"):
                    planned.append(
                        {
                            "run_id": (
                                f"{strategy_id}:{window['window_id']}:"
                                f"{variant['variant_id']}:{phase.lower()}"
                            ),
                            "subject_id": strategy_id,
                            "window_id": window["window_id"],
                            "phase": phase,
                            "parameter_id": variant["parameter_id"],
                        }
                    )
            planned.append(
                {
                    "run_id": f"{strategy_id}:{window['window_id']}:selected:test",
                    "subject_id": strategy_id,
                    "window_id": window["window_id"],
                    "phase": "TEST",
                    "parameter_id": "SELECTED_BY_VALIDATION",
                }
            )
        for variant in _variants(strategy_id):
            planned.append(
                {
                    "run_id": f"{strategy_id}:frozen:{variant['variant_id']}:stability",
                    "subject_id": strategy_id,
                    "window_id": None,
                    "phase": "FROZEN_STABILITY",
                    "parameter_id": variant["parameter_id"],
                }
            )
    return planned


def plan_synthetic_strategy_robustness_evidence_v1() -> dict[str, Any]:
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "source_schema_version": "synthetic-strategy-report-bundle-v1",
        "registered_strategy_ids": list(_STRATEGY_IDS),
        "windows": [
            {
                "window_id": item["window_id"],
                "train": list(item["train"]),
                "validation": list(item["validation"]),
                "frozen_test": list(item["frozen_test"]),
                "purge_bars": item["purge_bars"],
                "embargo_bars": item["embargo_bars"],
            }
            for item in _WINDOWS
        ],
        "parameter_variants": {
            strategy_id: _variants(strategy_id) for strategy_id in _STRATEGY_IDS
        },
        "selection_policy": {
            "window_selection_metric": "VALIDATION_TOTAL_RETURN",
            "tie_breakers": ["LOWER_MAX_DRAWDOWN", "LEXICAL_PARAMETER_ID"],
            "formal_selected_parameter": "CENTER_REGISTERED_DEFAULT",
            "frozen_used_for_selection": False,
            "post_frozen_parameter_changes_allowed": False,
        },
        "stability_policy": {
            "evaluation_partition": "FROZEN_SYNTHETIC",
            "max_abs_degradation": "0.05",
            "minimum_neighbor_count": 2,
            "minimum_stable_neighbor_count": 1,
        },
        "multiplicity_policy": {
            "preregistered_parameter_trial_count_per_strategy": 3,
            "diagnostic_methods": ["BONFERRONI", "BENJAMINI_HOCHBERG"],
            "formal_inference_claimed": False,
        },
        "planned_runs": _planned_runs(),
        "planned_run_count": 147,
        "executed_run_count": 0,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def plan_synthetic_strategy_robustness_evidence_v2() -> dict[str, Any]:
    plan = plan_synthetic_strategy_robustness_evidence_v1()
    plan.pop("plan_sha256")
    plan["schema_version"] = REFERENCE_PLAN_SCHEMA_VERSION
    plan["source_schema_version"] = "synthetic-strategy-report-bundle-v2"
    plan["source_reproducibility_context_required"] = True
    return _seal(plan, "plan_sha256")


def _frame_slice(frame: pd.DataFrame, period: tuple[int, int]) -> pd.DataFrame:
    return frame.iloc[period[0] : period[1] + 1].copy(deep=True)


def _dataset_sha256(frame: pd.DataFrame) -> str:
    return canonical_sha256(_records(frame))


def _performance_projection(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in result.items()
        if key not in {"reproducibility", "experiment_manifest"}
    }


def _compact_observation(
    *,
    run: dict[str, Any],
    phase: str,
    window_id: str | None,
    parameter_id: str | None,
) -> dict[str, Any]:
    result = run["result"]
    record = {
        "run_id": run["run_id"],
        "phase": phase,
        "window_id": window_id,
        "parameter_id": parameter_id,
        "status": "OBSERVED",
        "failure_code": None,
        "dataset_sha256": run["dataset_sha256"],
        "result_sha256": run["result_sha256"],
        "source_run_sha256": run["run_sha256"],
        "total_return": _decimal(result["total_return"]),
        "max_drawdown": _decimal(result["max_drawdown"]),
        "sharpe_ratio": _decimal(result["sharpe_ratio"]),
        "trade_count": int(result["trades"]),
    }
    return _seal(record, "record_sha256")


def _failed_observation(
    *,
    run_id: str,
    phase: str,
    window_id: str | None,
    parameter_id: str | None,
    dataset_sha256: str,
    failure_code: str,
) -> dict[str, Any]:
    record = {
        "run_id": run_id,
        "phase": phase,
        "window_id": window_id,
        "parameter_id": parameter_id,
        "status": "FAILED",
        "failure_code": failure_code,
        "dataset_sha256": dataset_sha256,
        "result_sha256": None,
        "source_run_sha256": None,
        "total_return": None,
        "max_drawdown": None,
        "sharpe_ratio": None,
        "trade_count": None,
    }
    return _seal(record, "record_sha256")


def _manifest_evaluation_role(phase: str) -> str:
    try:
        return {
            "TRAIN": "TRAIN",
            "VALIDATION": "VALIDATION",
            "TEST": "FROZEN_TEST",
            "TEST_BENCHMARK": "FROZEN_TEST",
            "FROZEN_STABILITY": "FROZEN_TEST",
        }[phase]
    except KeyError as exc:
        raise SyntheticStrategyRobustnessError(
            f"unknown robustness evaluation phase: {phase}"
        ) from exc


def _execute_observation(
    *,
    run_id: str,
    phase: str,
    window_id: str | None,
    parameter_id: str | None,
    frame: pd.DataFrame,
    strategy_factory: Callable[[], Any],
    plan_sha256: str,
    experiment_context: dict[str, Any] | None = None,
    run_capture: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    dataset_sha256 = _dataset_sha256(frame)
    try:
        run = _run_backtest(
            run_id=run_id,
            evaluation_role=f"SYNTHETIC_ROBUSTNESS_{phase}",
            frame=frame,
            dataset_sha256=dataset_sha256,
            cost_multiplier=1,
            strategy_factory=strategy_factory,
            protocol_sha256=plan_sha256,
            experiment_context=experiment_context,
            manifest_evaluation_role=(
                _manifest_evaluation_role(phase)
                if experiment_context is not None
                else None
            ),
        )
    except Exception as exc:
        record = _failed_observation(
            run_id=run_id,
            phase=phase,
            window_id=window_id,
            parameter_id=parameter_id,
            dataset_sha256=dataset_sha256,
            failure_code=f"{phase}_EXECUTION_{type(exc).__name__}",
        )
        _capture_observation(run_capture, record, None)
        return record, None
    record = _compact_observation(
        run=run,
        phase=phase,
        window_id=window_id,
        parameter_id=parameter_id,
    )
    _capture_observation(run_capture, record, run)
    return record, run


def _capture_observation(
    run_capture: dict[str, dict[str, Any]] | None,
    record: dict[str, Any],
    run: dict[str, Any] | None,
) -> None:
    if run_capture is None:
        return
    run_id = record["run_id"]
    if run_id in run_capture:
        raise SyntheticStrategyRobustnessError(f"duplicate captured run: {run_id}")
    run_capture[run_id] = {
        "observation": deepcopy(record),
        "run": deepcopy(run),
    }


def _period_returns(result: dict[str, Any]) -> list[float]:
    equities = [float(item["equity"]) for item in result["equity_curve"]]
    returns: list[float] = []
    for prior, current in zip(equities, equities[1:]):
        if prior > 0:
            returns.append((current / prior) - 1.0)
    return returns


def _normal_approximation_pvalue(samples: list[float]) -> float:
    if len(samples) < 2:
        return 1.0
    dispersion = stdev(samples)
    if dispersion == 0.0:
        return 1.0
    statistic = mean(samples) / (dispersion / math.sqrt(len(samples)))
    return min(1.0, max(0.0, math.erfc(abs(statistic) / math.sqrt(2.0))))


def _multiplicity_diagnostics(
    strategy_id: str,
    validation_runs: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    raw: list[tuple[str, float, int]] = []
    for parameter_id in sorted(validation_runs):
        samples: list[float] = []
        for run in validation_runs[parameter_id]:
            samples.extend(_period_returns(run["result"]))
        raw.append((parameter_id, _normal_approximation_pvalue(samples), len(samples)))
    count = len(raw)
    bonferroni = {parameter_id: min(1.0, pvalue * count) for parameter_id, pvalue, _ in raw}
    order = sorted(range(count), key=lambda index: (raw[index][1], raw[index][0]))
    bh_values = [1.0] * count
    running = 1.0
    for reverse_position in range(count - 1, -1, -1):
        index = order[reverse_position]
        rank = reverse_position + 1
        running = min(running, raw[index][1] * count / rank)
        bh_values[index] = min(1.0, running)
    trials = []
    for index, (parameter_id, pvalue, sample_count) in enumerate(raw):
        trials.append(
            {
                "parameter_id": parameter_id,
                "period_return_count": sample_count,
                "two_sided_normal_approximation_p": _decimal(pvalue),
                "bonferroni_adjusted_p": _decimal(bonferroni[parameter_id]),
                "benjamini_hochberg_adjusted_p": _decimal(bh_values[index]),
            }
        )
    diagnostics = {
        "schema_version": "synthetic-multiplicity-diagnostics-v1",
        "strategy_id": strategy_id,
        "trial_count": count,
        "trials": trials,
        "status": "PARTIAL",
        "interpretation": "SYNTHETIC_DIAGNOSTIC_ONLY_NOT_FORMAL_INFERENCE",
        "gaps": [
            "OVERLAPPING_WINDOWS_NO_INDEPENDENCE_CLAIM",
            "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED",
            "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED",
            "BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED",
        ],
        "authority": _authority(),
    }
    return _seal(diagnostics, "diagnostics_sha256")


def _distance_fraction(center: dict[str, Any], neighbor: dict[str, Any]) -> str:
    distances = []
    for key, center_value in center.items():
        if key == "position_pct":
            continue
        neighbor_value = float(neighbor[key])
        base = abs(float(center_value))
        distances.append(abs(neighbor_value - float(center_value)) / base if base else 0.0)
    return _decimal(max(distances, default=0.0))


def _trial_aggregate(
    strategy_id: str,
    parameter_id: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    relevant = [
        {
            "window_id": record["window_id"],
            "status": record["status"],
            "failure_code": record["failure_code"],
            "result_sha256": record["result_sha256"],
            "total_return": record["total_return"],
        }
        for record in records
        if record["phase"] == "VALIDATION" and record["parameter_id"] == parameter_id
    ]
    return {
        "schema_version": "synthetic-parameter-trial-aggregate-v1",
        "strategy_id": strategy_id,
        "parameter_id": parameter_id,
        "validation_observations": relevant,
    }


def _market_regime_gaps() -> dict[str, Any]:
    return {
        "slices": [
            {
                "regime_id": regime_id,
                "status": "GAP",
                "strategy_total_return": None,
                "benchmark_total_return": None,
                "observation_sha256": None,
                "gap_code": "MARKET_REGIME_NOT_EXECUTED_IN_THIS_SLICE",
            }
            for regime_id in ("BULL", "BEAR", "RANGE", "HIGH_VOLATILITY")
        ]
    }


def _build_strategy_evidence(
    *,
    strategy_id: str,
    source_report: dict[str, Any],
    source_bundle: dict[str, Any],
    full_frame: pd.DataFrame,
    frozen_frame: pd.DataFrame,
    benchmark_runs: dict[str, dict[str, Any]],
    plan: dict[str, Any],
    experiment_context: dict[str, Any] | None = None,
    run_capture: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    variants = _variants(strategy_id)
    variant_by_id = {item["parameter_id"]: item for item in variants}
    run_ledger: list[dict[str, Any]] = []
    validation_full_runs: dict[str, list[dict[str, Any]]] = {
        item["parameter_id"]: [] for item in variants
    }
    walk_forward_windows: list[dict[str, Any]] = []

    for window in _WINDOWS:
        validation_candidates: list[tuple[str, dict[str, Any]]] = []
        for variant in variants:
            for phase, period in (
                ("TRAIN", window["train"]),
                ("VALIDATION", window["validation"]),
            ):
                run_id = (
                    f"{strategy_id}:{window['window_id']}:"
                    f"{variant['variant_id']}:{phase.lower()}"
                )
                record, full_run = _execute_observation(
                    run_id=run_id,
                    phase=phase,
                    window_id=window["window_id"],
                    parameter_id=variant["parameter_id"],
                    frame=_frame_slice(full_frame, period),
                    strategy_factory=lambda strategy_id=strategy_id, params=deepcopy(variant["parameters"]): build_strategy(strategy_id, params),
                    plan_sha256=plan["plan_sha256"],
                    experiment_context=experiment_context,
                    run_capture=run_capture,
                )
                run_ledger.append(record)
                if phase == "VALIDATION" and full_run is not None:
                    validation_candidates.append((variant["parameter_id"], full_run))
                    validation_full_runs[variant["parameter_id"]].append(full_run)

        benchmark_run = benchmark_runs[window["window_id"]]
        if not validation_candidates:
            walk_forward_windows.append(
                {
                    "window_id": window["window_id"],
                    "train": {"start_index": window["train"][0], "end_index": window["train"][1]},
                    "validation": {"start_index": window["validation"][0], "end_index": window["validation"][1]},
                    "frozen_test": {"start_index": window["frozen_test"][0], "end_index": window["frozen_test"][1]},
                    "purge_bars": window["purge_bars"],
                    "embargo_bars": window["embargo_bars"],
                    "selected_parameter_id": _parameter_id(strategy_id, "center"),
                    "strategy_total_return": None,
                    "benchmark_total_return": None,
                    "strategy_result_sha256": None,
                    "benchmark_result_sha256": None,
                    "status": "FAILED",
                    "failure_code": "NO_OBSERVED_VALIDATION_CANDIDATE",
                }
            )
            continue

        selected_id, _ = min(
            validation_candidates,
            key=lambda item: (
                -float(item[1]["result"]["total_return"]),
                float(item[1]["result"]["max_drawdown"]),
                item[0],
            ),
        )
        selected_variant = variant_by_id[selected_id]
        test_record, test_run = _execute_observation(
            run_id=f"{strategy_id}:{window['window_id']}:selected:test",
            phase="TEST",
            window_id=window["window_id"],
            parameter_id=selected_id,
            frame=_frame_slice(full_frame, window["frozen_test"]),
            strategy_factory=lambda strategy_id=strategy_id, params=deepcopy(selected_variant["parameters"]): build_strategy(strategy_id, params),
            plan_sha256=plan["plan_sha256"],
            experiment_context=experiment_context,
            run_capture=run_capture,
        )
        run_ledger.append(test_record)
        if test_run is None:
            walk_forward_windows.append(
                {
                    "window_id": window["window_id"],
                    "train": {"start_index": window["train"][0], "end_index": window["train"][1]},
                    "validation": {"start_index": window["validation"][0], "end_index": window["validation"][1]},
                    "frozen_test": {"start_index": window["frozen_test"][0], "end_index": window["frozen_test"][1]},
                    "purge_bars": window["purge_bars"],
                    "embargo_bars": window["embargo_bars"],
                    "selected_parameter_id": selected_id,
                    "strategy_total_return": None,
                    "benchmark_total_return": None,
                    "strategy_result_sha256": None,
                    "benchmark_result_sha256": None,
                    "status": "FAILED",
                    "failure_code": test_record["failure_code"],
                }
            )
            continue
        walk_forward_windows.append(
            {
                "window_id": window["window_id"],
                "train": {"start_index": window["train"][0], "end_index": window["train"][1]},
                "validation": {"start_index": window["validation"][0], "end_index": window["validation"][1]},
                "frozen_test": {"start_index": window["frozen_test"][0], "end_index": window["frozen_test"][1]},
                "purge_bars": window["purge_bars"],
                "embargo_bars": window["embargo_bars"],
                "selected_parameter_id": selected_id,
                "strategy_total_return": _decimal(test_run["result"]["total_return"]),
                "benchmark_total_return": _decimal(benchmark_run["result"]["total_return"]),
                "strategy_result_sha256": test_run["result_sha256"],
                "benchmark_result_sha256": benchmark_run["result_sha256"],
                "status": "OBSERVED",
                "failure_code": None,
            }
        )

    frozen_runs: dict[str, dict[str, Any] | None] = {}
    for variant in variants:
        record, full_run = _execute_observation(
            run_id=f"{strategy_id}:frozen:{variant['variant_id']}:stability",
            phase="FROZEN_STABILITY",
            window_id=None,
            parameter_id=variant["parameter_id"],
            frame=frozen_frame,
            strategy_factory=lambda strategy_id=strategy_id, params=deepcopy(variant["parameters"]): build_strategy(strategy_id, params),
            plan_sha256=plan["plan_sha256"],
            experiment_context=experiment_context,
            run_capture=run_capture,
        )
        run_ledger.append(record)
        frozen_runs[variant["parameter_id"]] = full_run

    center_id = _parameter_id(strategy_id, "center")
    center_run = frozen_runs[center_id]
    if center_run is None:
        raise SyntheticStrategyRobustnessError(f"center stability run failed for {strategy_id}")
    source_center = source_report["runs"]["frozen_1x"]["result"]
    center_projection_sha256 = canonical_sha256(_performance_projection(center_run["result"]))
    source_projection_sha256 = canonical_sha256(_performance_projection(source_center))
    if center_projection_sha256 != source_projection_sha256:
        raise SyntheticStrategyRobustnessError(f"explicit center drifted from source default for {strategy_id}")

    frozen_cash = source_bundle["benchmarks"]["cash"]["result"]
    cash_return = float(frozen_cash["total_return"])
    center_excess = float(center_run["result"]["total_return"]) - cash_return
    neighbors = []
    for variant in variants:
        if variant["parameter_id"] == center_id:
            continue
        neighbor_run = frozen_runs[variant["parameter_id"]]
        if neighbor_run is None:
            neighbors.append(
                {
                    "parameter_id": variant["parameter_id"],
                    "distance_fraction": _distance_fraction(_PARAMETERS[strategy_id]["center"], variant["parameters"]),
                    "frozen_excess_return": None,
                    "result_sha256": None,
                    "status": "FAILED",
                    "failure_code": "FROZEN_STABILITY_EXECUTION_FAILED",
                }
            )
        else:
            neighbors.append(
                {
                    "parameter_id": variant["parameter_id"],
                    "distance_fraction": _distance_fraction(_PARAMETERS[strategy_id]["center"], variant["parameters"]),
                    "frozen_excess_return": _decimal(float(neighbor_run["result"]["total_return"]) - cash_return),
                    "result_sha256": neighbor_run["result_sha256"],
                    "status": "OBSERVED",
                    "failure_code": None,
                }
            )
    neighbors.sort(key=lambda item: item["parameter_id"])

    run_ledger_sha256 = canonical_sha256(run_ledger)
    parameter_ids = sorted(variant_by_id)
    trial_outcomes = []
    for parameter_id in parameter_ids:
        aggregate = _trial_aggregate(strategy_id, parameter_id, run_ledger)
        relevant = aggregate["validation_observations"]
        failed = any(item["status"] != "OBSERVED" for item in relevant) or len(relevant) != len(_WINDOWS)
        if failed:
            trial_outcomes.append(
                {
                    "trial_id": parameter_id,
                    "status": "FAILED",
                    "result_sha256": None,
                    "failure_code": "INCOMPLETE_VALIDATION_TRIAL",
                    "decision_status": None,
                    "decision_blockers": [],
                }
            )
        else:
            trial_outcomes.append(
                {
                    "trial_id": parameter_id,
                    "status": "OBSERVED",
                    "result_sha256": canonical_sha256(aggregate),
                    "failure_code": None,
                    "decision_status": "BLOCK",
                    "decision_blockers": ["NO_PROFITABILITY_AUTHORITY", "SYNTHETIC_DATA_ONLY"],
                }
            )

    formal_lineage = {
        "producer_id": "strategy_research_search_lineage_v2",
        "producer_schema_version": SCHEMA_VERSION,
        "search_family_id": f"{strategy_id}-default-neighborhood-v1",
        "current_trial_count": 3,
        "prior_registration_count": 0,
        "cumulative_trial_count": 3,
        "lineage_sha256": canonical_sha256(
            {"strategy_id": strategy_id, "plan_sha256": plan["plan_sha256"]}
        ),
        "artifact_sha256": run_ledger_sha256,
    }
    multiple_testing = {
        "preregistered_trial_ids": parameter_ids,
        "producer_report_sha256": run_ledger_sha256,
        "selected_parameter_id": center_id,
        "selection_rule": "PREREGISTERED_CENTER_DEFAULT_NO_POST_HOC_SELECTION",
        "trial_outcomes": trial_outcomes,
    }
    parameter_stability = {
        "selected_parameter_id": center_id,
        "selected_result_sha256": center_run["result_sha256"],
        "selected_frozen_excess_return": _decimal(center_excess),
        "neighbors": neighbors,
        "max_abs_degradation": "0.05",
        "minimum_neighbor_count": 2,
        "minimum_stable_neighbor_count": 1,
    }
    distribution = build_distribution_evidence(
        source_report,
        source_result_path=["runs", "frozen_1x", "result"],
        periods_per_year=PERIODS_PER_YEAR,
    )
    validation_evidence = build_validation_evidence(
        source_report,
        experiment_id=f"synthetic-robustness-{strategy_id}-v1",
        formal_search_lineage=formal_lineage,
        distribution_evidence=distribution,
        walk_forward={"windows": walk_forward_windows},
        parameter_stability=parameter_stability,
        multiple_testing=multiple_testing,
        market_regimes=_market_regime_gaps(),
    )
    validation_receipt = verify_validation_evidence(validation_evidence, source_report)
    diagnostics = _multiplicity_diagnostics(strategy_id, validation_full_runs)
    center_binding = {
        "source_implicit_default_projection_sha256": source_projection_sha256,
        "explicit_center_projection_sha256": center_projection_sha256,
        "exact_match": True,
    }
    record = {
        "schema_version": STRATEGY_EVIDENCE_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": _family_for_strategy(strategy_id),
        "parameter_variants": variants,
        "center_binding": center_binding,
        "run_ledger": run_ledger,
        "run_ledger_sha256": run_ledger_sha256,
        "multiplicity_diagnostics": diagnostics,
        "validation_evidence": validation_evidence,
        "validation_receipt": validation_receipt,
        "status": "PARTIAL",
        "observation_class": "SYNTHETIC_OBSERVATION_ONLY",
        "authority": _authority(),
    }
    return _seal(record, "record_sha256")


def _verify_bound_manifest(
    manifest: dict[str, Any],
    *,
    context: dict[str, Any],
    plan_sha256: str,
) -> None:
    canonical_sha256(manifest)
    if (
        type(manifest) is not dict
        or manifest.get("dependency_lock_hash") != context["dependency_lock_hash"]
        or manifest.get("dependency_lock_name") != context["dependency_lock_name"]
        or manifest.get("dependency_lock_fully_pinned") is not True
        or manifest.get("git_commit_sha") != context["git_commit_sha"]
        or manifest.get("git_worktree_clean") is not False
        or manifest.get("evaluation_role") not in {
            "TRAIN",
            "VALIDATION",
            "FROZEN_TEST",
        }
        or manifest.get("evaluation_protocol_hash") != plan_sha256
        or manifest.get("evaluation_protocol_verified") is not True
        or type(manifest.get("blockers")) is not list
        or "git_worktree_not_clean" not in manifest["blockers"]
    ):
        raise SyntheticStrategyRobustnessError(
            "robustness run reproducibility manifest mismatch"
        )


def _build_run_reproducibility_ledger(
    run_capture: dict[str, dict[str, Any]],
    *,
    context: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(run_capture) is not dict or len(run_capture) != 147:
        raise SyntheticStrategyRobustnessError(
            "run capture is incomplete for reproducibility binding"
        )
    expected_run_ids = sorted(item["run_id"] for item in plan["planned_runs"])
    if sorted(run_capture) != expected_run_ids:
        raise SyntheticStrategyRobustnessError(
            "reproducibility run membership drifted from plan"
        )
    records = []
    role_counts = {"TRAIN": 0, "VALIDATION": 0, "FROZEN_TEST": 0}
    for run_id in expected_run_ids:
        captured = run_capture[run_id]
        run = captured.get("run")
        if type(run) is not dict:
            raise SyntheticStrategyRobustnessError(
                f"missing successful run for reproducibility binding: {run_id}"
            )
        manifest = run.get("result", {}).get("experiment_manifest")
        if type(manifest) is not dict:
            raise SyntheticStrategyRobustnessError(
                f"missing experiment manifest for robustness run: {run_id}"
            )
        _verify_bound_manifest(
            manifest,
            context=context,
            plan_sha256=plan["plan_sha256"],
        )
        role_counts[manifest["evaluation_role"]] += 1
        records.append(
            _seal(
                {
                    "run_id": run_id,
                    "experiment_manifest": deepcopy(manifest),
                },
                "record_sha256",
            )
        )
    if role_counts != {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39}:
        raise SyntheticStrategyRobustnessError(
            "reproducibility evaluation-role counts drifted"
        )
    return _seal(
        {
            "schema_version": RUN_REPRODUCIBILITY_LEDGER_SCHEMA_VERSION,
            "source_context_sha256": canonical_sha256(context),
            "plan_sha256": plan["plan_sha256"],
            "run_count": 147,
            "dependency_bound_run_count": 147,
            "git_bound_run_count": 0,
            "evaluation_role_counts": role_counts,
            "records": records,
        },
        "ledger_sha256",
    )


def _verify_run_reproducibility_ledger(
    ledger: dict[str, Any],
    *,
    context: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    if type(ledger) is not dict or set(ledger) != {
        "schema_version",
        "source_context_sha256",
        "plan_sha256",
        "run_count",
        "dependency_bound_run_count",
        "git_bound_run_count",
        "evaluation_role_counts",
        "records",
        "ledger_sha256",
    }:
        raise SyntheticStrategyRobustnessError(
            "run reproducibility ledger shape mismatch"
        )
    _verify_seal(ledger, "ledger_sha256", "run_reproducibility_ledger")
    if (
        ledger["schema_version"] != RUN_REPRODUCIBILITY_LEDGER_SCHEMA_VERSION
        or ledger["source_context_sha256"] != canonical_sha256(context)
        or ledger["plan_sha256"] != plan["plan_sha256"]
        or type(ledger["run_count"]) is not int
        or ledger["run_count"] != 147
        or type(ledger["dependency_bound_run_count"]) is not int
        or ledger["dependency_bound_run_count"] != 147
        or type(ledger["git_bound_run_count"]) is not int
        or ledger["git_bound_run_count"] != 0
        or ledger["evaluation_role_counts"]
        != {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39}
    ):
        raise SyntheticStrategyRobustnessError(
            "run reproducibility ledger semantics mismatch"
        )
    records = ledger["records"]
    if type(records) is not list or len(records) != 147:
        raise SyntheticStrategyRobustnessError(
            "run reproducibility record count mismatch"
        )
    expected_run_ids = sorted(item["run_id"] for item in plan["planned_runs"])
    if [item.get("run_id") for item in records] != expected_run_ids:
        raise SyntheticStrategyRobustnessError(
            "run reproducibility record membership mismatch"
        )
    role_counts = {"TRAIN": 0, "VALIDATION": 0, "FROZEN_TEST": 0}
    for record in records:
        if type(record) is not dict or set(record) != {
            "run_id",
            "experiment_manifest",
            "record_sha256",
        }:
            raise SyntheticStrategyRobustnessError(
                "run reproducibility record shape mismatch"
            )
        _verify_seal(record, "record_sha256", "run_reproducibility_ledger.records[]")
        manifest = record["experiment_manifest"]
        _verify_bound_manifest(
            manifest,
            context=context,
            plan_sha256=plan["plan_sha256"],
        )
        role_counts[manifest["evaluation_role"]] += 1
    if role_counts != ledger["evaluation_role_counts"]:
        raise SyntheticStrategyRobustnessError(
            "run reproducibility role-count mismatch"
        )


def _build_synthetic_strategy_robustness_evidence_v1(
    source_bundle: dict[str, Any],
    *,
    execute: bool,
    run_capture: dict[str, dict[str, Any]] | None,
    plan: dict[str, Any] | None = None,
    source_verifier: Callable[[dict[str, Any]], dict[str, Any]] = (
        verify_synthetic_strategy_report_bundle_v1
    ),
    bundle_schema_version: str = SCHEMA_VERSION,
    experiment_context: dict[str, Any] | None = None,
    completed_evidence: tuple[str, ...] = _COMPLETED_EVIDENCE,
    gaps: tuple[str, ...] = _GAPS,
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyRobustnessError(
            "execution requires exact execute=True; inspect the plan first"
        )
    source_receipt = source_verifier(source_bundle)
    if source_receipt.get("status") != "PASS":
        raise SyntheticStrategyRobustnessError("source bundle did not verify")
    if experiment_context is not None:
        if (
            type(experiment_context) is not dict
            or source_bundle.get("reproducibility_context")
            != experiment_context
        ):
            raise SyntheticStrategyRobustnessError(
                "source reproducibility context mismatch"
            )
    plan = (
        plan_synthetic_strategy_robustness_evidence_v1()
        if plan is None
        else deepcopy(plan)
    )
    effective_run_capture = run_capture
    if experiment_context is not None and effective_run_capture is None:
        effective_run_capture = {}
    full_frame = _build_frame()
    fixture_frames, expected_fixture = _build_fixture()
    if source_bundle["fixture"] != expected_fixture:
        raise SyntheticStrategyRobustnessError("source fixture drifted")

    benchmark_ledger = []
    benchmark_runs: dict[str, dict[str, Any]] = {}
    for window in _WINDOWS:
        record, run = _execute_observation(
            run_id=f"benchmark:{window['window_id']}:cash:test",
            phase="TEST_BENCHMARK",
            window_id=window["window_id"],
            parameter_id=None,
            frame=_frame_slice(full_frame, window["frozen_test"]),
            strategy_factory=lambda: _CashBenchmark(name="cash", version="v1"),
            plan_sha256=plan["plan_sha256"],
            experiment_context=experiment_context,
            run_capture=effective_run_capture,
        )
        benchmark_ledger.append(record)
        if run is None:
            raise SyntheticStrategyRobustnessError("cash benchmark execution failed")
        benchmark_runs[window["window_id"]] = run

    source_reports = {
        report["strategy_id"]: report for report in source_bundle["strategy_reports"]
    }
    strategy_evidence = [
        _build_strategy_evidence(
            strategy_id=strategy_id,
            source_report=source_reports[strategy_id],
            source_bundle=source_bundle,
            full_frame=full_frame,
            frozen_frame=fixture_frames["frozen"],
            benchmark_runs=benchmark_runs,
            plan=plan,
            experiment_context=experiment_context,
            run_capture=effective_run_capture,
        )
        for strategy_id in _STRATEGY_IDS
    ]
    executed_run_count = len(benchmark_ledger) + sum(
        len(item["run_ledger"]) for item in strategy_evidence
    )
    if executed_run_count != plan["planned_run_count"]:
        raise SyntheticStrategyRobustnessError("executed run count drifted")
    if (
        effective_run_capture is not None
        and len(effective_run_capture) != executed_run_count
    ):
        raise SyntheticStrategyRobustnessError("captured run count drifted")
    bundle = {
        "schema_version": bundle_schema_version,
        "source_bundle": deepcopy(source_bundle),
        "source_bundle_sha256": source_bundle["bundle_sha256"],
        "plan": plan,
        "benchmark_ledger": benchmark_ledger,
        "strategy_evidence": strategy_evidence,
        "completed_evidence": list(completed_evidence),
        "gaps": list(gaps),
        "executed_run_count": executed_run_count,
        "runtime_mutations": False,
        "status": "BLOCK",
        "maturity": "SYNTHETIC_ROBUSTNESS_ONLY",
        "authority": _authority(),
    }
    if experiment_context is not None:
        if effective_run_capture is None:
            raise SyntheticStrategyRobustnessError(
                "missing run capture for reproducibility ledger"
            )
        bundle["reproducibility_context"] = deepcopy(experiment_context)
        bundle["run_reproducibility_ledger"] = (
            _build_run_reproducibility_ledger(
                effective_run_capture,
                context=experiment_context,
                plan=plan,
            )
        )
    return _seal(bundle, "bundle_sha256")


def build_synthetic_strategy_robustness_evidence_v1(
    source_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    return _build_synthetic_strategy_robustness_evidence_v1(
        source_bundle,
        execute=execute,
        run_capture=None,
    )


def build_synthetic_strategy_robustness_evidence_with_run_capture_v1(
    source_bundle: dict[str, Any], *, execute: bool = False
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    run_capture: dict[str, dict[str, Any]] = {}
    bundle = _build_synthetic_strategy_robustness_evidence_v1(
        source_bundle,
        execute=execute,
        run_capture=run_capture,
    )
    return bundle, deepcopy(run_capture)


def build_synthetic_strategy_robustness_evidence_v2(
    source_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(source_bundle) is not dict:
        raise SyntheticStrategyRobustnessError(
            "source bundle must be an exact dict"
        )
    return _build_synthetic_strategy_robustness_evidence_v1(
        source_bundle,
        execute=execute,
        run_capture=None,
        plan=plan_synthetic_strategy_robustness_evidence_v2(),
        source_verifier=verify_synthetic_strategy_report_bundle_v2,
        bundle_schema_version=REFERENCE_SCHEMA_VERSION,
        experiment_context=source_bundle.get("reproducibility_context"),
        completed_evidence=_REFERENCE_COMPLETED_EVIDENCE,
        gaps=_REFERENCE_GAPS,
    )


def build_synthetic_strategy_robustness_evidence_with_run_capture_v2(
    source_bundle: dict[str, Any], *, execute: bool = False
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if type(source_bundle) is not dict:
        raise SyntheticStrategyRobustnessError(
            "source bundle must be an exact dict"
        )
    run_capture: dict[str, dict[str, Any]] = {}
    bundle = _build_synthetic_strategy_robustness_evidence_v1(
        source_bundle,
        execute=execute,
        run_capture=run_capture,
        plan=plan_synthetic_strategy_robustness_evidence_v2(),
        source_verifier=verify_synthetic_strategy_report_bundle_v2,
        bundle_schema_version=REFERENCE_SCHEMA_VERSION,
        experiment_context=source_bundle.get("reproducibility_context"),
        completed_evidence=_REFERENCE_COMPLETED_EVIDENCE,
        gaps=_REFERENCE_GAPS,
    )
    return bundle, deepcopy(run_capture)


def _verify_record(record: dict[str, Any], source_report: dict[str, Any]) -> None:
    if record.get("schema_version") != STRATEGY_EVIDENCE_SCHEMA_VERSION:
        raise SyntheticStrategyRobustnessError("strategy evidence schema mismatch")
    strategy_id = record.get("strategy_id")
    if strategy_id not in _STRATEGY_IDS:
        raise SyntheticStrategyRobustnessError("unknown strategy evidence")
    if record.get("family_id") != _family_for_strategy(strategy_id):
        raise SyntheticStrategyRobustnessError("strategy family mismatch")
    if record.get("parameter_variants") != _variants(strategy_id):
        raise SyntheticStrategyRobustnessError("parameter variants mismatch")
    ledger = record.get("run_ledger")
    if type(ledger) is not list or len(ledger) != 24:
        raise SyntheticStrategyRobustnessError("run ledger count mismatch")
    if len({item.get("run_id") for item in ledger}) != len(ledger):
        raise SyntheticStrategyRobustnessError("duplicate run identifier")
    for item in ledger:
        _verify_seal(item, "record_sha256", "run_ledger[]")
    if canonical_sha256(ledger) != record.get("run_ledger_sha256"):
        raise SyntheticStrategyRobustnessError("run ledger digest mismatch")
    if record["validation_evidence"]["formal_search_lineage"]["artifact_sha256"] != record["run_ledger_sha256"]:
        raise SyntheticStrategyRobustnessError("formal lineage artifact mismatch")
    receipt = verify_validation_evidence(record["validation_evidence"], source_report)
    if receipt != record.get("validation_receipt"):
        raise SyntheticStrategyRobustnessError("validation receipt mismatch")
    if record.get("center_binding", {}).get("exact_match") is not True:
        raise SyntheticStrategyRobustnessError("center binding mismatch")
    _verify_seal(record["multiplicity_diagnostics"], "diagnostics_sha256", "multiplicity_diagnostics")
    if record.get("authority") != _AUTHORITY:
        raise SyntheticStrategyRobustnessError("strategy evidence authority mismatch")
    if record.get("status") != "PARTIAL" or record.get("observation_class") != "SYNTHETIC_OBSERVATION_ONLY":
        raise SyntheticStrategyRobustnessError("strategy evidence maturity mismatch")
    _verify_seal(record, "record_sha256", "strategy_evidence[]")


def _verify_bundle(
    bundle: dict[str, Any],
    *,
    schema_version: str = SCHEMA_VERSION,
    expected_plan: dict[str, Any] | None = None,
    source_verifier: Callable[[dict[str, Any]], dict[str, Any]] = (
        verify_synthetic_strategy_report_bundle_v1
    ),
    expected_completed_evidence: tuple[str, ...] = _COMPLETED_EVIDENCE,
    expected_gaps: tuple[str, ...] = _GAPS,
    require_reproducibility_ledger: bool = False,
) -> None:
    canonical_sha256(bundle)
    if bundle.get("schema_version") != schema_version:
        raise SyntheticStrategyRobustnessError("bundle schema mismatch")
    plan = (
        plan_synthetic_strategy_robustness_evidence_v1()
        if expected_plan is None
        else expected_plan
    )
    if bundle.get("plan") != plan:
        raise SyntheticStrategyRobustnessError("plan mismatch")
    source_bundle = bundle.get("source_bundle")
    if type(source_bundle) is not dict:
        raise SyntheticStrategyRobustnessError("source bundle missing")
    if source_verifier(source_bundle).get("status") != "PASS":
        raise SyntheticStrategyRobustnessError("source bundle failed verification")
    if bundle.get("source_bundle_sha256") != source_bundle["bundle_sha256"]:
        raise SyntheticStrategyRobustnessError("source bundle digest mismatch")
    benchmark_ledger = bundle.get("benchmark_ledger")
    if type(benchmark_ledger) is not list or len(benchmark_ledger) != 3:
        raise SyntheticStrategyRobustnessError("benchmark ledger mismatch")
    for item in benchmark_ledger:
        _verify_seal(item, "record_sha256", "benchmark_ledger[]")
    reports = {item["strategy_id"]: item for item in source_bundle["strategy_reports"]}
    evidence = bundle.get("strategy_evidence")
    if type(evidence) is not list or [item.get("strategy_id") for item in evidence] != list(_STRATEGY_IDS):
        raise SyntheticStrategyRobustnessError("strategy evidence membership mismatch")
    for item in evidence:
        _verify_record(item, reports[item["strategy_id"]])
    if bundle.get("executed_run_count") != 147 or type(bundle.get("executed_run_count")) is not int:
        raise SyntheticStrategyRobustnessError("executed run count mismatch")
    if bundle.get("completed_evidence") != list(expected_completed_evidence):
        raise SyntheticStrategyRobustnessError("completed evidence mismatch")
    if bundle.get("gaps") != list(expected_gaps):
        raise SyntheticStrategyRobustnessError("gap set mismatch")
    if bundle.get("runtime_mutations") is not False:
        raise SyntheticStrategyRobustnessError("runtime mutation escalation")
    if bundle.get("status") != "BLOCK" or bundle.get("maturity") != "SYNTHETIC_ROBUSTNESS_ONLY":
        raise SyntheticStrategyRobustnessError("bundle maturity mismatch")
    if bundle.get("authority") != _AUTHORITY:
        raise SyntheticStrategyRobustnessError("bundle authority mismatch")
    if require_reproducibility_ledger:
        context = bundle.get("reproducibility_context")
        if (
            type(context) is not dict
            or context != source_bundle.get("reproducibility_context")
        ):
            raise SyntheticStrategyRobustnessError(
                "bundle reproducibility context mismatch"
            )
        _verify_run_reproducibility_ledger(
            bundle.get("run_reproducibility_ledger"),
            context=context,
            plan=plan,
        )
    elif (
        "reproducibility_context" in bundle
        or "run_reproducibility_ledger" in bundle
    ):
        raise SyntheticStrategyRobustnessError(
            "v1 bundle contains undeclared reproducibility fields"
        )
    _verify_seal(bundle, "bundle_sha256", "$")


def verify_synthetic_strategy_robustness_evidence_v1(
    bundle: dict[str, Any]
) -> dict[str, Any]:
    try:
        _verify_bundle(bundle)
    except Exception as exc:
        return {
            "status": "BLOCK",
            "blockers": [f"ROBUSTNESS_VERIFICATION_FAILED:{type(exc).__name__}:{exc}"],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "verified_run_count": 147,
        "verified_strategy_count": 6,
        "replay_status": "NOT_EXECUTED",
        "authority": _authority(),
    }


def verify_synthetic_strategy_robustness_evidence_v2(
    bundle: dict[str, Any]
) -> dict[str, Any]:
    try:
        _verify_bundle(
            bundle,
            schema_version=REFERENCE_SCHEMA_VERSION,
            expected_plan=plan_synthetic_strategy_robustness_evidence_v2(),
            source_verifier=verify_synthetic_strategy_report_bundle_v2,
            expected_completed_evidence=_REFERENCE_COMPLETED_EVIDENCE,
            expected_gaps=_REFERENCE_GAPS,
            require_reproducibility_ledger=True,
        )
    except Exception as exc:
        return {
            "status": "BLOCK",
            "blockers": [
                f"ROBUSTNESS_REFERENCE_VERIFICATION_FAILED:{type(exc).__name__}:{exc}"
            ],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "verified_run_count": 147,
        "verified_strategy_count": 6,
        "dependency_bound_run_count": 147,
        "git_bound_run_count": 0,
        "replay_status": "NOT_EXECUTED",
        "authority": _authority(),
    }


def replay_synthetic_strategy_robustness_evidence_v1(
    bundle: dict[str, Any]
) -> dict[str, Any]:
    structural = verify_synthetic_strategy_robustness_evidence_v1(bundle)
    if structural["status"] != "PASS":
        return structural
    replayed = build_synthetic_strategy_robustness_evidence_v1(
        bundle["source_bundle"], execute=True
    )
    if replayed != bundle:
        return {
            "status": "BLOCK",
            "blockers": ["DETERMINISTIC_ROBUSTNESS_REPLAY_MISMATCH"],
            "expected_bundle_sha256": bundle["bundle_sha256"],
            "actual_bundle_sha256": replayed["bundle_sha256"],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "replay_status": "EXACT_MATCH",
        "replayed_run_count": 147,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def replay_synthetic_strategy_robustness_evidence_v2(
    bundle: dict[str, Any]
) -> dict[str, Any]:
    structural = verify_synthetic_strategy_robustness_evidence_v2(bundle)
    if structural["status"] != "PASS":
        return structural
    replayed = build_synthetic_strategy_robustness_evidence_v2(
        bundle["source_bundle"], execute=True
    )
    if replayed != bundle:
        return {
            "status": "BLOCK",
            "blockers": ["DETERMINISTIC_ROBUSTNESS_REFERENCE_REPLAY_MISMATCH"],
            "expected_bundle_sha256": bundle["bundle_sha256"],
            "actual_bundle_sha256": replayed["bundle_sha256"],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "replay_status": "EXACT_MATCH",
        "replayed_run_count": 147,
        "dependency_bound_run_count": 147,
        "git_bound_run_count": 0,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def _render_synthetic_strategy_robustness_markdown(
    bundle: dict[str, Any],
    *,
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
    title: str,
) -> str:
    receipt = verifier(bundle)
    if receipt["status"] != "PASS":
        raise SyntheticStrategyRobustnessError("refusing to render unverified evidence")
    lines = [
        title,
        "",
        "> Counts and diagnostics below are SYNTHETIC_OBSERVATION_ONLY. They do not establish real-market performance or trading permission.",
        "",
        "## SOURCE",
        "",
        f"- Source bundle SHA-256: `{bundle['source_bundle_sha256']}`",
        f"- Robustness bundle SHA-256: `{bundle['bundle_sha256']}`",
        "- Executed runs: 147 pure in-memory synthetic observations.",
        "- Walk-forward: three ordered windows with five-bar purge and embargo.",
        "- Parameter trials: center plus two preregistered neighbors per strategy.",
        "- Frozen data was not used for window selection.",
        "",
        "### Structural evidence",
        "",
        "| Family | Strategy | WF observed | WF failed | Stable neighbors | Trials observed | Trials failed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in bundle["strategy_evidence"]:
        evidence_receipt = item["validation_receipt"]
        lines.append(
            f"| {item['family_id']} | {item['strategy_id']} | "
            f"{evidence_receipt['walk_forward']['observed_count']} | "
            f"{evidence_receipt['walk_forward']['failed_count']} | "
            f"{evidence_receipt['parameter_stability']['stable_count']} | "
            f"{evidence_receipt['multiple_testing']['observed_count']} | "
            f"{evidence_receipt['multiple_testing']['failed_count']} |"
        )
    lines.extend(["", "## GAP", ""])
    lines.extend(f"- `{gap}`" for gap in bundle["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            "",
            "- Bundle status: `BLOCK`",
            "- Maturity: `SYNTHETIC_ROBUSTNESS_ONLY`",
            "- Walk-forward execution: `OBSERVED`",
            "- Parameter stability execution: `OBSERVED_OR_GAP_PRESERVED`",
            "- Multiple-testing ledger: `OBSERVED`",
            "- Market-regime evidence: `GAP`",
            "- Ensemble implementation: `GAP`",
            "",
            "## PERMISSION",
            "",
            "- Profitability proven: `false`",
            "- Formal blind test complete: `false`",
            "- Paper authorized: `false`",
            "- Live authorized: `false`",
            "- Order entry authorized: `false`",
            "",
        ]
    )
    markdown = "\n".join(lines)
    if "READY" in markdown:
        raise SyntheticStrategyRobustnessError("neutral renderer token violation")
    return markdown


def render_synthetic_strategy_robustness_markdown_v1(
    bundle: dict[str, Any]
) -> str:
    return _render_synthetic_strategy_robustness_markdown(
        bundle,
        verifier=verify_synthetic_strategy_robustness_evidence_v1,
        title="# Pure Synthetic Robustness Evidence",
    )


def render_synthetic_strategy_robustness_markdown_v2(
    bundle: dict[str, Any]
) -> str:
    return _render_synthetic_strategy_robustness_markdown(
        bundle,
        verifier=verify_synthetic_strategy_robustness_evidence_v2,
        title="# Pure Synthetic Robustness Evidence v2",
    )


def build_default_synthetic_strategy_robustness_evidence_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyRobustnessError(
            "execution requires exact execute=True; inspect both plans first"
        )
    source = build_synthetic_strategy_report_bundle_v1(execute=True)
    return build_synthetic_strategy_robustness_evidence_v1(source, execute=True)


def build_default_synthetic_strategy_robustness_evidence_v2(
    *,
    execute: bool = False,
    reproducibility_context: dict[str, Any],
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyRobustnessError(
            "execution requires exact execute=True; inspect both v2 plans first"
        )
    source = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=reproducibility_context,
    )
    return build_synthetic_strategy_robustness_evidence_v2(
        source,
        execute=True,
    )
