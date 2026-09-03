from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import math
from typing import Any

import pandas as pd

from hakimi_research.backtest import (
    BacktestEngine,
    build_backtest_reproducibility,
)
from hakimi_research.benchmarks import (  # noqa: E402
    BENCHMARKS,
    FIXED_BASELINE_MATRIX_VERSION,
    build_fixed_benchmark,
    fixed_benchmark_specs,
)
from hakimi_research.config import BotConfig  # noqa: E402
from hakimi_research.experiment_manifest import (  # noqa: E402
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)
from hakimi_research.dataset_governance import (  # noqa: E402
    bind_dataset_governance,
    dataset_governance_declaration,
)
from hakimi_research.dataset_calendar_conformance import (  # noqa: E402
    build_dataset_calendar_conformance,
)
from hakimi_research.bootstrap_confidence_evidence import (  # noqa: E402
    INSUFFICIENT_OBSERVATIONS_GAP as BOOTSTRAP_INSUFFICIENT_OBSERVATIONS_GAP,
    MINIMUM_OBSERVATION_COUNT as BOOTSTRAP_MINIMUM_OBSERVATION_COUNT,
    build_bootstrap_confidence_evidence,
    verify_bootstrap_confidence_evidence,
)
from hakimi_research.frozen_execution_adversity import (  # noqa: E402
    SCENARIO_IDS as EXECUTION_ADVERSITY_SCENARIO_IDS,
    WRAPPER_VERSION as EXECUTION_ADVERSITY_WRAPPER_VERSION,
    build_execution_adversity_delta,
    build_execution_adversity_metadata,
    build_liquidity_capacity_summary,
    build_liquidity_rejection_evidence,
    execution_adversity_policy_v2,
    execution_adversity_observation_status,
    prepare_execution_adversity_inputs,
    verify_execution_adversity_metadata,
    verify_liquidity_capacity_summary,
    verify_liquidity_rejection_evidence,
)
from hakimi_research.models import Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase
from hakimi_research.strategies.templates import build_strategy
from hakimi_research.volatility_comparison import (  # noqa: E402
    annualization_factor,
    build_volatility_matched_comparison,
    volatility_match_method_spec,
)
from hakimi_research.volatility_target_baseline import (  # noqa: E402
    build_prior_window_volatility_target_calibration,
    build_prior_window_volatility_target_strategy,
    volatility_target_method_spec,
)
from hakimi_research.walk_forward import (  # noqa: E402
    build_fixed_walk_forward_schedule,
    build_fixed_walk_forward_summary,
    fixed_walk_forward_method_spec,
)
from hakimi_research.parameter_stability import (  # noqa: E402
    build_dual_ma_parameter_stability_cells,
    build_parameter_stability_summary,
    fixed_parameter_stability_method_spec,
)
from hakimi_research.multiple_testing import (  # noqa: E402
    build_multiple_testing_ledger,
    multiple_testing_policy_spec,
)
from hakimi_research.frozen_market_regime import (  # noqa: E402
    build_fixed_market_regime_analysis,
    fixed_market_regime_policy_spec,
)
from hakimi_research.frozen_distribution import (  # noqa: E402
    build_frozen_distribution_analysis,
    frozen_distribution_policy_spec,
)
from hakimi_research.frozen_statistical_correction import (  # noqa: E402
    build_frozen_statistical_correction_evidence,
    verify_frozen_statistical_correction_evidence,
)
from hakimi_research.frozen_experiment_provenance import (  # noqa: E402
    build_frozen_experiment_provenance_ledger,
    verified_multiple_testing_receipt_hashes,
)


PROTOCOL_SCHEMA_VERSION = "frozen-evaluation-protocol-v17"
REPORT_SCHEMA_VERSION = "frozen-evaluation-report-v22"
MARKDOWN_REPORT_VERSION = "frozen-evaluation-markdown-v22"
EXPERIMENT_CONTEXT_SCHEMA_VERSION = "frozen-experiment-context-v1"
EVIDENCE_SCOPE = (
    "LOCAL_FIXED_SPLIT_RESEARCH_ONLY_NOT_BLIND_NOT_NATURAL_FORWARD_"
    "NO_SINGLE_CONSUMPTION_PROOF"
)
REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
MIN_EVALUATION_ROWS = 35
MIN_GAP_ROWS = 1
COST_SCENARIOS = (
    ("BASE", 1),
    ("DOUBLE_COST", 2),
    ("TRIPLE_COST", 3),
)
AUTHORITY_LOCK = {
    "parameter_selection": False,
    "ranking": False,
    "profitability_proof": False,
    "paper": False,
    "live": False,
    "order": False,
}
STRUCTURAL_BLOCKERS = [
    "BLIND_HOLDOUT_NOT_PROVEN",
    "EXTERNAL_PREREGISTRATION_RECEIPT_MISSING",
    "SINGLE_CONSUMPTION_NOT_ENFORCED",
    "NOT_NATURAL_FORWARD_EVIDENCE",
]
STANDARD_REPORT_COVERAGE_GAPS = (
    "WALK_FORWARD_REAL_MARKET_AND_LONG_HORIZON_NOT_AVAILABLE",
    "PARAMETER_STABILITY_ONLY_DUAL_MA_SYNTHETIC_GRID",
    "MULTIPLE_TESTING_CORRECTIONS_NOT_ESTIMABLE_TWO_SYNTHETIC_FOLDS",
    "MARKET_REGIME_SLICES_ONLY_SYNTHETIC_FIXED_THRESHOLDS",
    "TAIL_DISTRIBUTION_ONLY_TEN_SYNTHETIC_OBSERVATIONS",
    "BOOTSTRAP_CONFIDENCE_ONLY_NINE_PAIRED_SYNTHETIC_OBSERVATIONS",
    "RETURN_CONTRIBUTION_FIXED_21_PERIOD_WINDOW_UNAVAILABLE",
    "DSR_NON_POSITIVE_TRIAL_VARIANCE_AND_PBO_INSUFFICIENT_OBSERVATIONS",
    "EXECUTION_ADVERSITY_PARTIAL_FILL_REMAINDER_LIFECYCLE_NOT_MODELLED",
)
_EXPERIMENT_CONTEXT_BASE_FIELDS = frozenset({
    "git_commit_sha",
    "git_worktree_clean",
    "dependency_lock_hash",
    "dependency_lock_fully_pinned",
    "dependency_lock_name",
    "runtime_version",
})


def _require_native_json(value: Any, *, path: str = "root") -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path}_non_finite")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_native_json(item, path=f"{path}_{index}")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path}_key_invalid")
            _require_native_json(item, path=f"{path}_{key}")
        return
    raise ValueError(f"{path}_native_json_invalid")


def _finite_rate(value: Any, *, field: str) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"frozen_evaluation_{field}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 <= parsed < 1:
        raise ValueError(f"frozen_evaluation_{field}_invalid")
    return parsed


def _normalized_experiment_context(
    value: Any,
    *,
    random_seed: int,
) -> dict[str, Any]:
    _require_native_json(value, path="experiment_context")
    if type(value) is not dict:
        raise ValueError("frozen_evaluation_experiment_context_type_invalid")
    allowed_fields = (
        _EXPERIMENT_CONTEXT_BASE_FIELDS
        | frozenset({"random_seed"})
    )
    if set(value) not in {
        _EXPERIMENT_CONTEXT_BASE_FIELDS,
        allowed_fields,
    }:
        raise ValueError("frozen_evaluation_experiment_context_fields_invalid")
    if "random_seed" in value and value["random_seed"] != random_seed:
        raise ValueError("frozen_evaluation_experiment_context_seed_mismatch")
    context = {
        **value,
        "random_seed": random_seed,
    }
    git_sha = context["git_commit_sha"]
    dependency_hash = context["dependency_lock_hash"]
    if (
        type(git_sha) is not str
        or len(git_sha) not in {40, 64}
        or git_sha != git_sha.lower()
        or any(character not in "0123456789abcdef" for character in git_sha)
    ):
        raise ValueError("frozen_evaluation_experiment_context_git_sha_invalid")
    if (
        type(dependency_hash) is not str
        or len(dependency_hash) != 64
        or dependency_hash != dependency_hash.lower()
        or any(
            character not in "0123456789abcdef"
            for character in dependency_hash
        )
    ):
        raise ValueError(
            "frozen_evaluation_experiment_context_dependency_hash_invalid"
        )
    for field in (
        "git_worktree_clean",
        "dependency_lock_fully_pinned",
    ):
        if type(context[field]) is not bool:
            raise ValueError(
                f"frozen_evaluation_experiment_context_{field}_invalid"
            )
    for field in ("dependency_lock_name", "runtime_version"):
        item = context[field]
        if type(item) is not str or not item or item != item.strip():
            raise ValueError(
                f"frozen_evaluation_experiment_context_{field}_invalid"
            )
    return context


def _experiment_context_binding(
    value: Any,
    *,
    random_seed: int,
) -> dict[str, Any]:
    context = _normalized_experiment_context(value, random_seed=random_seed)
    return {
        "schema_version": EXPERIMENT_CONTEXT_SCHEMA_VERSION,
        "context": context,
        "context_hash": canonical_payload_hash(context),
    }


def _normalized_dataset(data: Any) -> tuple[dict[str, Any], pd.DatetimeIndex]:
    if type(data) is not pd.DataFrame:
        raise ValueError("frozen_evaluation_dataset_type_invalid")
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("frozen_evaluation_dataset_columns_invalid")
    if type(data.index) is not pd.DatetimeIndex:
        raise ValueError("frozen_evaluation_dataset_index_invalid")
    if data.index.tz is None or not data.index.is_monotonic_increasing or not data.index.is_unique:
        raise ValueError("frozen_evaluation_dataset_index_invalid")
    if data.index.hasnans:
        raise ValueError("frozen_evaluation_dataset_index_invalid")

    rows: list[list[str]] = []
    for timestamp, row in data.loc[:, REQUIRED_COLUMNS].iterrows():
        numeric: dict[str, float] = {}
        for column in REQUIRED_COLUMNS:
            try:
                parsed = float(row[column])
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("frozen_evaluation_dataset_numeric_invalid") from exc
            if not math.isfinite(parsed):
                raise ValueError("frozen_evaluation_dataset_numeric_invalid")
            numeric[column] = parsed
        if (
            numeric["open"] <= 0
            or numeric["high"] <= 0
            or numeric["low"] <= 0
            or numeric["close"] <= 0
            or numeric["volume"] < 0
            or numeric["high"] < max(numeric["open"], numeric["close"])
            or numeric["low"] > min(numeric["open"], numeric["close"])
            or numeric["high"] < numeric["low"]
        ):
            raise ValueError("frozen_evaluation_dataset_ohlcv_invalid")
        rows.append([
            pd.Timestamp(timestamp).isoformat(),
            *(format(numeric[column], ".17g") for column in REQUIRED_COLUMNS),
        ])
    payload = {
        "hash_scope": "FULL_OHLCV_CANONICAL_DECIMAL_TEXT_V1",
        "columns": ["timestamp", *REQUIRED_COLUMNS],
        "rows": rows,
    }
    return payload, data.index


def _window(index: pd.DatetimeIndex, name: str, start: int, end: int) -> dict[str, Any]:
    return {
        "name": name,
        "start_position": start,
        "end_position_exclusive": end,
        "row_count": end - start,
        "start_time": pd.Timestamp(index[start]).isoformat(),
        "end_time": pd.Timestamp(index[end - 1]).isoformat(),
    }


def _validate_config(config: Any) -> tuple[dict[str, Any], StrategyBase, float, float]:
    if type(config) is not BotConfig:
        raise ValueError("frozen_evaluation_config_type_invalid")
    if config.mode != "backtest" or config.execution.live_trading_enabled is not False:
        raise ValueError("frozen_evaluation_config_authority_invalid")
    fee_rate = _finite_rate(config.execution.fee_rate, field="fee_rate")
    slippage_pct = _finite_rate(config.execution.slippage_pct, field="slippage_pct")
    if fee_rate * 3 >= 1 or slippage_pct * 3 >= 1:
        raise ValueError("frozen_evaluation_cost_stress_out_of_range")
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    if type(strategy.name) is not str or not strategy.name:
        raise ValueError("frozen_evaluation_strategy_name_invalid")
    if type(strategy.version) is not str or not strategy.version:
        raise ValueError("frozen_evaluation_strategy_version_invalid")
    config_payload = asdict(config)
    _require_native_json(config_payload, path="config")
    return config_payload, strategy, fee_rate, slippage_pct


def _protocol_benchmark_specs(random_seed: int) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for definition in fixed_benchmark_specs(random_seed):
        core = {
            "matrix_version": FIXED_BASELINE_MATRIX_VERSION,
            **definition,
        }
        specs.append({
            **core,
            "spec_hash": canonical_payload_hash(core),
        })
    return specs


def _protocol_comparison_methods() -> list[dict[str, Any]]:
    core = volatility_match_method_spec()
    return [{
        **core,
        "spec_hash": canonical_payload_hash(core),
    }]


def _protocol_execution_baseline_methods() -> list[dict[str, Any]]:
    core = volatility_target_method_spec()
    return [{
        **core,
        "spec_hash": canonical_payload_hash(core),
    }]


def _protocol_walk_forward(data: pd.DataFrame) -> dict[str, Any]:
    method_core = fixed_walk_forward_method_spec()
    return {
        "method": {
            **method_core,
            "spec_hash": canonical_payload_hash(method_core),
        },
        "schedule": build_fixed_walk_forward_schedule(data),
    }


def _protocol_parameter_stability(
    strategy_name: str,
    base_params: dict[str, Any],
) -> dict[str, Any]:
    method_core = fixed_parameter_stability_method_spec()
    if strategy_name != method_core["supported_strategy"]:
        raise ValueError("frozen_evaluation_parameter_stability_strategy_unsupported")
    cells = build_dual_ma_parameter_stability_cells(base_params)
    method = {
        **method_core,
        "base_params_hash": canonical_payload_hash(base_params),
    }
    method["spec_hash"] = canonical_payload_hash(method)
    matrix_core = {
        "method_spec_hash": method["spec_hash"],
        "cells": cells,
    }
    return {
        "method": method,
        "cells": cells,
        "matrix_hash": canonical_payload_hash(matrix_core),
    }


def _protocol_multiple_testing_policy() -> dict[str, Any]:
    core = multiple_testing_policy_spec()
    return {
        **core,
        "spec_hash": canonical_payload_hash(core),
    }


def _protocol_market_regime_policy() -> dict[str, Any]:
    core = fixed_market_regime_policy_spec()
    return {
        **core,
        "spec_hash": canonical_payload_hash(core),
    }


def _protocol_tail_distribution_policy() -> dict[str, Any]:
    core = frozen_distribution_policy_spec()
    return {
        **core,
        "spec_hash": canonical_payload_hash(core),
    }


def build_frozen_evaluation_protocol(
    data: pd.DataFrame,
    config: BotConfig,
    *,
    dataset_governance: dict[str, Any],
    experiment_context: dict[str, Any],
    train_rows: int,
    purge_rows: int,
    validation_rows: int,
    embargo_rows: int,
    frozen_test_rows: int,
    random_seed: int = 0,
) -> dict[str, Any]:
    counts = {
        "train_rows": train_rows,
        "purge_rows": purge_rows,
        "validation_rows": validation_rows,
        "embargo_rows": embargo_rows,
        "frozen_test_rows": frozen_test_rows,
    }
    if any(type(value) is not int for value in counts.values()):
        raise ValueError("frozen_evaluation_partition_count_invalid")
    if type(random_seed) is not int or not 0 <= random_seed <= 2_147_483_647:
        raise ValueError("frozen_evaluation_random_seed_invalid")
    if min(train_rows, validation_rows, frozen_test_rows) < MIN_EVALUATION_ROWS:
        raise ValueError("frozen_evaluation_partition_too_short")
    if min(purge_rows, embargo_rows) < MIN_GAP_ROWS:
        raise ValueError("frozen_evaluation_gap_too_short")

    dataset_payload, index = _normalized_dataset(data)
    if sum(counts.values()) != len(index):
        raise ValueError("frozen_evaluation_partition_total_mismatch")
    config_payload, strategy, fee_rate, slippage_pct = _validate_config(config)
    dataset_hash = canonical_payload_hash(dataset_payload)
    start_time = pd.Timestamp(index[0]).isoformat()
    end_time = pd.Timestamp(index[-1]).isoformat()
    governance = bind_dataset_governance(
        dataset_governance,
        dataset_hash=dataset_hash,
        market=config.market,
        symbol=config.symbol,
        timeframe=config.timeframe,
        row_count=len(index),
        start_time=start_time,
        end_time=end_time,
        dataset_timezone=str(index.tz),
    )
    calendar_conformance = build_dataset_calendar_conformance(
        index,
        time_contract=governance["time"],
        timeframe=config.timeframe,
        source_kind=governance["source"]["source_kind"],
    )
    if calendar_conformance["status"] != "PASS":
        raise ValueError(
            "frozen_evaluation_dataset_calendar_conformance_failed:"
            + ",".join(calendar_conformance["blockers"])
        )

    train_end = train_rows
    purge_end = train_end + purge_rows
    validation_end = purge_end + validation_rows
    embargo_end = validation_end + embargo_rows
    frozen_end = embargo_end + frozen_test_rows
    windows = [
        _window(index, "TRAIN", 0, train_end),
        _window(index, "PURGE", train_end, purge_end),
        _window(index, "VALIDATION", purge_end, validation_end),
        _window(index, "EMBARGO", validation_end, embargo_end),
        _window(index, "FROZEN_TEST", embargo_end, frozen_end),
    ]
    cost_scenarios = [
        {
            "scenario_id": scenario_id,
            "multiplier": multiplier,
            "fee_rate": fee_rate * multiplier,
            "slippage_pct": slippage_pct * multiplier,
        }
        for scenario_id, multiplier in COST_SCENARIOS
    ]
    core = {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "dataset": {
            "dataset_hash": dataset_hash,
            "row_count": len(index),
            "start_time": start_time,
            "end_time": end_time,
            "hash_scope": dataset_payload["hash_scope"],
            "governance": governance,
            "calendar_conformance": calendar_conformance,
        },
        "config": {
            "config_hash": canonical_payload_hash(config_payload),
            "market": config.market,
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "initial_cash": float(config.initial_cash),
        },
        "strategy": {
            "name": strategy.name,
            "version": strategy.version,
            "params_hash": canonical_payload_hash(config.strategy.params),
        },
        "experiment_context": _experiment_context_binding(
            experiment_context,
            random_seed=random_seed,
        ),
        "partition_plan": {
            "order": ["TRAIN", "PURGE", "VALIDATION", "EMBARGO", "FROZEN_TEST"],
            "windows": windows,
            "minimum_evaluation_rows": MIN_EVALUATION_ROWS,
            "minimum_gap_rows": MIN_GAP_ROWS,
        },
        "cost_scenarios": cost_scenarios,
        "benchmarks": _protocol_benchmark_specs(random_seed),
        "comparison_methods": _protocol_comparison_methods(),
        "execution_baseline_methods": _protocol_execution_baseline_methods(),
        "execution_adversity": execution_adversity_policy_v2(),
        "walk_forward": _protocol_walk_forward(data),
        "parameter_stability": _protocol_parameter_stability(
            strategy.name,
            config.strategy.params,
        ),
        "multiple_testing_policy": _protocol_multiple_testing_policy(),
        "market_regime_policy": _protocol_market_regime_policy(),
        "tail_distribution_policy": _protocol_tail_distribution_policy(),
        "policy": {
            "train_rankable": False,
            "validation_role_only": True,
            "frozen_test_role_only": True,
            "blind_holdout_proven": False,
            "external_preregistration_receipt_present": False,
            "single_consumption_enforced": False,
            "natural_forward_evidence": False,
            "random_seed": random_seed,
        },
        "authority": dict(AUTHORITY_LOCK),
    }
    protocol_hash = canonical_payload_hash(core)
    return {
        **core,
        "protocol_id": f"hfep-{protocol_hash[:20]}",
        "protocol_hash": protocol_hash,
    }


def verify_frozen_evaluation_protocol(
    protocol: Any,
    data: pd.DataFrame,
    config: BotConfig,
    *,
    experiment_context: dict[str, Any],
) -> bool:
    _require_native_json(protocol, path="protocol")
    if type(protocol) is not dict:
        raise ValueError("frozen_evaluation_protocol_type_invalid")
    expected_keys = {
        "schema_version",
        "evidence_scope",
        "dataset",
        "config",
        "strategy",
        "experiment_context",
        "partition_plan",
        "cost_scenarios",
        "benchmarks",
        "comparison_methods",
        "execution_baseline_methods",
        "execution_adversity",
        "walk_forward",
        "parameter_stability",
        "multiple_testing_policy",
        "market_regime_policy",
        "tail_distribution_policy",
        "policy",
        "authority",
        "protocol_id",
        "protocol_hash",
    }
    if set(protocol) != expected_keys:
        raise ValueError("frozen_evaluation_protocol_schema_invalid")
    try:
        windows = protocol["partition_plan"]["windows"]
        rebuilt = build_frozen_evaluation_protocol(
            data,
            config,
            dataset_governance=dataset_governance_declaration(
                protocol["dataset"]["governance"]
            ),
            experiment_context=experiment_context,
            train_rows=windows[0]["row_count"],
            purge_rows=windows[1]["row_count"],
            validation_rows=windows[2]["row_count"],
            embargo_rows=windows[3]["row_count"],
            frozen_test_rows=windows[4]["row_count"],
            random_seed=protocol["policy"]["random_seed"],
        )
    except (IndexError, KeyError, TypeError) as exc:
        raise ValueError("frozen_evaluation_protocol_shape_invalid") from exc
    if protocol != rebuilt:
        raise ValueError("frozen_evaluation_protocol_verification_failed")
    return True


def _partition_frame(
    data: pd.DataFrame,
    protocol: dict[str, Any],
    role: str,
) -> pd.DataFrame:
    window = next(
        item for item in protocol["partition_plan"]["windows"] if item["name"] == role
    )
    return data.iloc[window["start_position"]:window["end_position_exclusive"]].copy()


def _scenario_map(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["scenario_id"]: item for item in protocol["cost_scenarios"]}


def _run_record(
    *,
    role: str,
    scenario: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
    strategy: StrategyBase,
    protocol_hash: str,
    random_seed: int,
    experiment_context: dict[str, Any] | None,
    run_kind: str,
    manifest_evaluation_role: str | None = None,
    max_volume_participation_rate: float | None = None,
    provenance_expectations: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    run_config = deepcopy(config)
    run_config.execution.fee_rate = scenario["fee_rate"]
    run_config.execution.slippage_pct = scenario["slippage_pct"]
    context = dict(experiment_context or {})
    context.update({
        "evaluation_role": (
            role if manifest_evaluation_role is None else manifest_evaluation_role
        ),
        "evaluation_protocol_hash": protocol_hash,
        "evaluation_protocol_verified": True,
        "random_seed": random_seed,
    })
    expected_reproducibility = build_backtest_reproducibility(
        data,
        run_config,
        strategy,
        experiment_context=context,
        max_volume_participation_rate=max_volume_participation_rate,
    )
    report = BacktestEngine(
        config=run_config,
        strategy=strategy,
        risk_manager=RiskManager(run_config.risk),
        experiment_context=context,
        max_volume_participation_rate=max_volume_participation_rate,
    ).run(data)
    payload = report.to_dict()
    manifest = payload.pop("experiment_manifest")
    if not verify_reproducible_experiment_manifest(manifest, payload):
        raise ValueError("frozen_evaluation_nested_manifest_invalid")
    record = {
        "run_kind": run_kind,
        "role": role,
        "scenario_id": scenario["scenario_id"],
        "fee_rate": scenario["fee_rate"],
        "slippage_pct": scenario["slippage_pct"],
        "strategy_name": strategy.name,
        "strategy_version": strategy.version,
        "result": payload,
        "experiment_manifest": manifest,
    }
    provenance_expectations[id(record)] = expected_reproducibility
    return record


def _strategy_for_config(config: BotConfig) -> StrategyBase:
    return build_strategy(config.strategy.name, config.strategy.params)


def build_frozen_evaluation_report(
    protocol: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
    *,
    experiment_context: dict[str, Any],
) -> dict[str, Any]:
    verify_frozen_evaluation_protocol(
        protocol,
        data,
        config,
        experiment_context=experiment_context,
    )
    experiment_context = dict(protocol["experiment_context"]["context"])
    provenance_expectations: dict[int, dict[str, Any]] = {}
    scenarios = _scenario_map(protocol)
    random_seed = protocol["policy"]["random_seed"]
    strategy_runs: list[dict[str, Any]] = []
    for role, scenario_ids in (
        ("TRAIN", ("BASE",)),
        ("VALIDATION", ("BASE", "DOUBLE_COST", "TRIPLE_COST")),
        ("FROZEN_TEST", ("BASE", "DOUBLE_COST", "TRIPLE_COST")),
    ):
        frame = _partition_frame(data, protocol, role)
        for scenario_id in scenario_ids:
            strategy_runs.append(_run_record(
                role=role,
                scenario=scenarios[scenario_id],
                data=frame,
                config=config,
                strategy=_strategy_for_config(config),
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="REGISTERED_STRATEGY",
                provenance_expectations=provenance_expectations,
            ))

    strategy_by_role = {
        record["role"]: record
        for record in strategy_runs
        if record["scenario_id"] == "BASE"
    }
    adversity_policy = protocol["execution_adversity"]
    base_scenario = scenarios[adversity_policy["source_cost_scenario"]]
    execution_adversity_runs: list[dict[str, Any]] = []
    for role in adversity_policy["roles"]:
        source_record = strategy_by_role[role]
        source_frame = _partition_frame(data, protocol, role)
        for scenario_spec in adversity_policy["scenarios"]:
            scenario_id = scenario_spec["scenario_id"]
            stressed_strategy, stressed_frame, adverse_events = (
                prepare_execution_adversity_inputs(
                    scenario_id,
                    _strategy_for_config(config),
                    source_frame,
                    source_record["result"],
                )
            )
            record = _run_record(
                role=role,
                scenario={
                    "scenario_id": scenario_id,
                    "fee_rate": base_scenario["fee_rate"],
                    "slippage_pct": base_scenario["slippage_pct"],
                },
                data=stressed_frame,
                config=config,
                strategy=stressed_strategy,
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="REGISTERED_EXECUTION_ADVERSITY",
                provenance_expectations=provenance_expectations,
            )
            scenario_metadata = build_execution_adversity_metadata(
                scenario_id,
                stressed_strategy,
                adverse_events,
            )
            record.update({
                "source_scenario_id": "BASE",
                "source_result_hash": source_record["experiment_manifest"][
                    "result_hash"
                ],
                "scenario_policy_hash": adversity_policy["policy_hash"],
                "scenario_metadata": scenario_metadata,
                "observation_status": execution_adversity_observation_status(
                    scenario_metadata,
                    source_record["result"],
                ),
                "source_result_delta": build_execution_adversity_delta(
                    source_record["result"],
                    record["result"],
                ),
                "source_input_dataset_hash": source_record["result"][
                    "reproducibility"
                ]["data_hash"],
                "stressed_input_dataset_hash": record["result"][
                    "reproducibility"
                ]["data_hash"],
                "unmodelled_gaps": list(adversity_policy["unmodelled_gaps"]),
            })
            execution_adversity_runs.append(record)
    execution_adversity_observation_complete = all(
        record["observation_status"] == "OBSERVED"
        for record in execution_adversity_runs
    )

    benchmark_config = deepcopy(config)
    benchmark_config.risk.max_position_pct = 1.0
    benchmark_config.risk.max_single_loss_pct = 1.0
    benchmark_config.risk.max_daily_loss_pct = 1.0
    benchmark_config.risk.max_leverage = 1.0
    benchmark_config.risk.min_cash_pct = 0.0
    benchmark_runs: list[dict[str, Any]] = []
    for role in ("VALIDATION", "FROZEN_TEST"):
        frame = _partition_frame(data, protocol, role)
        for spec in protocol["benchmarks"]:
            for scenario_id, _multiplier in COST_SCENARIOS:
                strategy = build_fixed_benchmark(spec["benchmark_id"], random_seed)
                if (
                    strategy.name != spec["strategy_name"]
                    or strategy.version != spec["version"]
                    or strategy.params != spec["params"]
                ):
                    raise ValueError("frozen_evaluation_benchmark_factory_drift")
                record = _run_record(
                    role=role,
                    scenario=scenarios[scenario_id],
                    data=frame,
                    config=benchmark_config,
                    strategy=strategy,
                    protocol_hash=protocol["protocol_hash"],
                    random_seed=random_seed,
                    experiment_context=experiment_context,
                    run_kind="FIXED_BENCHMARK",
                    provenance_expectations=provenance_expectations,
                )
                record["benchmark_id"] = spec["benchmark_id"]
                record["benchmark_spec_hash"] = spec["spec_hash"]
                record["benchmark_params"] = strategy.params
                benchmark_runs.append(record)

    bootstrap_confidence_evidence: list[dict[str, Any]] = []
    for role in ("VALIDATION", "FROZEN_TEST"):
        source_strategy = next(
            record
            for record in strategy_runs
            if record["role"] == role and record["scenario_id"] == "BASE"
        )
        source_benchmark = next(
            record
            for record in benchmark_runs
            if record["role"] == role
            and record["scenario_id"] == "BASE"
            and record["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
        )
        strategy_result_hash = source_strategy["experiment_manifest"]["result_hash"]
        benchmark_result_hash = source_benchmark["experiment_manifest"]["result_hash"]
        observation_class = f"FROZEN_EVALUATION_{role}_BASE"
        bootstrap_confidence_evidence.append({
            "role": role,
            "scenario_id": "BASE",
            "benchmark_id": "ENGINE_BUY_AND_HOLD",
            "strategy_result_hash": strategy_result_hash,
            "benchmark_result_hash": benchmark_result_hash,
            "dataset_hash": protocol["dataset"]["dataset_hash"],
            "observation_class": observation_class,
            "evidence": build_bootstrap_confidence_evidence(
                source_strategy["result"]["equity_curve"],
                source_benchmark["result"]["equity_curve"],
                dataset_sha256=protocol["dataset"]["dataset_hash"],
                strategy_result_sha256=strategy_result_hash,
                benchmark_result_sha256=benchmark_result_hash,
                observation_class=observation_class,
            ),
        })
    bootstrap_confidence_matrix_complete = len(bootstrap_confidence_evidence) == 2
    bootstrap_confidence_observation_complete = all(
        record["evidence"]["evidence_state"] == "OBSERVED"
        for record in bootstrap_confidence_evidence
    )

    liquidity_probe = adversity_policy["liquidity_capacity_probe"]
    liquidity_capacity_runs: list[dict[str, Any]] = []
    for role in liquidity_probe["roles"]:
        source_record = next(
            record
            for record in benchmark_runs
            if record["role"] == role
            and record["scenario_id"] == liquidity_probe["source_cost_scenario"]
            and record["benchmark_id"] == liquidity_probe["source_benchmark_id"]
        )
        frame = _partition_frame(data, protocol, role)
        strategy = build_fixed_benchmark(
            liquidity_probe["source_benchmark_id"],
            random_seed,
        )
        record = _run_record(
            role=role,
            scenario={
                "scenario_id": liquidity_probe["scenario_id"],
                "fee_rate": scenarios["BASE"]["fee_rate"],
                "slippage_pct": scenarios["BASE"]["slippage_pct"],
            },
            data=frame,
            config=benchmark_config,
            strategy=strategy,
            protocol_hash=protocol["protocol_hash"],
            random_seed=random_seed,
            experiment_context=experiment_context,
            run_kind="REGISTERED_LIQUIDITY_CAPACITY_PROBE",
            max_volume_participation_rate=liquidity_probe[
                "max_volume_participation_rate"
            ],
            provenance_expectations=provenance_expectations,
        )
        record.update({
            "source_scenario_id": liquidity_probe["source_cost_scenario"],
            "source_benchmark_id": liquidity_probe["source_benchmark_id"],
            "source_result_hash": source_record["experiment_manifest"][
                "result_hash"
            ],
            "scenario_policy_hash": adversity_policy["policy_hash"],
            "source_result_delta": build_execution_adversity_delta(
                source_record["result"],
                record["result"],
            ),
            "source_input_dataset_hash": source_record["result"][
                "reproducibility"
            ]["data_hash"],
            "stressed_input_dataset_hash": record["result"][
                "reproducibility"
            ]["data_hash"],
            "liquidity_capacity_summary": build_liquidity_capacity_summary(
                record["result"],
                max_volume_participation_rate=liquidity_probe[
                    "max_volume_participation_rate"
                ],
            ),
            "unmodelled_gaps": list(adversity_policy["unmodelled_gaps"]),
        })
        liquidity_capacity_runs.append(record)
    liquidity_capacity_partial_fill_observed = all(
        record["liquidity_capacity_summary"]["status"] == "OBSERVED"
        for record in liquidity_capacity_runs
    )

    liquidity_rejection_probe = adversity_policy["liquidity_rejection_probe"]
    liquidity_rejection_evidence = [
        build_liquidity_rejection_evidence(
            next(
                record
                for record in liquidity_capacity_runs
                if record["role"] == role
                and record["scenario_id"]
                == liquidity_rejection_probe["source_capacity_scenario_id"]
            ),
            probe=liquidity_rejection_probe,
            policy_hash=adversity_policy["policy_hash"],
            initial_cash=protocol["config"]["initial_cash"],
        )
        for role in liquidity_rejection_probe["roles"]
    ]
    liquidity_rejection_observed = all(
        item["decision"]["status"] == "REJECTED"
        for item in liquidity_rejection_evidence
    )

    comparison_spec = protocol["comparison_methods"][0]
    strategy_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in strategy_runs
        if record["role"] in comparison_spec["roles"]
    }
    benchmark_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in benchmark_runs
        if record["benchmark_id"] == comparison_spec["benchmark_id"]
    }
    volatility_matched_comparisons: list[dict[str, Any]] = []
    for role in comparison_spec["roles"]:
        for scenario_id in comparison_spec["cost_scenarios"]:
            identity = (role, scenario_id)
            comparison = build_volatility_matched_comparison(
                strategy_by_identity[identity],
                benchmark_by_identity[identity],
                initial_equity=protocol["config"]["initial_cash"],
                market=protocol["config"]["market"],
                timeframe=protocol["config"]["timeframe"],
            )
            comparison["method_spec_hash"] = comparison_spec["spec_hash"]
            volatility_matched_comparisons.append(comparison)

    volatility_comparison_matrix_complete = (
        len(volatility_matched_comparisons)
        == len(comparison_spec["roles"])
        * len(comparison_spec["cost_scenarios"])
    )
    volatility_comparison_observation_complete = all(
        item["comparison_status"] == "OBSERVED"
        for item in volatility_matched_comparisons
    )

    execution_spec = protocol["execution_baseline_methods"][0]
    all_strategy_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in strategy_runs
    }
    volatility_target_benchmark_runs: list[dict[str, Any]] = []
    for mapping in execution_spec["calibration_map"]:
        target_role = mapping["target_role"]
        calibration_role = mapping["calibration_role"]
        calibration = build_prior_window_volatility_target_calibration(
            all_strategy_by_identity[(calibration_role, "BASE")],
            _partition_frame(data, protocol, calibration_role),
            target_role=target_role,
            calibration_role=calibration_role,
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
            warmup_rows=execution_spec["warmup_rows"],
            exposure_cap=execution_spec["exposure_cap"],
        )
        strategy = build_prior_window_volatility_target_strategy(calibration)
        target_frame = _partition_frame(data, protocol, target_role)
        for scenario_id in execution_spec["cost_scenarios"]:
            record = _run_record(
                role=target_role,
                scenario=scenarios[scenario_id],
                data=target_frame,
                config=benchmark_config,
                strategy=strategy,
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="PREREGISTERED_VOLATILITY_TARGET_BENCHMARK",
                provenance_expectations=provenance_expectations,
            )
            record["benchmark_id"] = execution_spec["benchmark_id"]
            record["method_spec_hash"] = execution_spec["spec_hash"]
            record["calibration"] = calibration
            record["benchmark_params"] = strategy.params
            volatility_target_benchmark_runs.append(record)

    volatility_target_baseline_complete = all(
        record["calibration"]["calibration_status"] == "CALIBRATED"
        for record in volatility_target_benchmark_runs
    )

    walk_forward_contract = protocol["walk_forward"]
    walk_forward_method = walk_forward_contract["method"]
    walk_forward_schedule = walk_forward_contract["schedule"]
    walk_forward_runs: list[dict[str, Any]] = []
    for fold in walk_forward_schedule["folds"]:
        evaluation = fold["evaluation"]
        evaluation_frame = data.iloc[
            evaluation["start_position"]:evaluation["end_position_exclusive"]
        ].copy()
        for scenario_id in walk_forward_method["cost_scenarios"]:
            record = _run_record(
                role="WALK_FORWARD_EVAL",
                scenario=scenarios[scenario_id],
                data=evaluation_frame,
                config=config,
                strategy=_strategy_for_config(config),
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="FIXED_PARAMETER_WALK_FORWARD",
                manifest_evaluation_role=walk_forward_method["nested_manifest_role"],
                provenance_expectations=provenance_expectations,
            )
            record["fold_id"] = fold["fold_id"]
            record["method_spec_hash"] = walk_forward_method["spec_hash"]
            record["schedule_hash"] = walk_forward_schedule["schedule_hash"]
            record["calibration_window"] = dict(fold["calibration"])
            record["purge_window"] = dict(fold["purge"])
            record["evaluation_window"] = dict(fold["evaluation"])
            walk_forward_runs.append(record)
    walk_forward_summary = build_fixed_walk_forward_summary(
        walk_forward_runs,
        walk_forward_schedule,
    )
    walk_forward_complete = len(walk_forward_runs) == 6

    stability_contract = protocol["parameter_stability"]
    stability_method = stability_contract["method"]
    parameter_stability_runs: list[dict[str, Any]] = []
    for role in stability_method["roles"]:
        frame = _partition_frame(data, protocol, role)
        scenario = scenarios[stability_method["cost_scenario"]]
        for cell in stability_contract["cells"]:
            record = _run_record(
                role=role,
                scenario=scenario,
                data=frame,
                config=config,
                strategy=build_strategy(config.strategy.name, cell["params"]),
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="PARAMETER_STABILITY_OBSERVATION",
                manifest_evaluation_role=stability_method["nested_manifest_role"],
                provenance_expectations=provenance_expectations,
            )
            record["cell_id"] = cell["cell_id"]
            record["segment"] = cell["segment"]
            record["is_center"] = cell["is_center"]
            record["axes"] = dict(cell["axes"])
            record["params"] = dict(cell["params"])
            record["params_hash"] = cell["params_hash"]
            record["cell_hash"] = cell["cell_hash"]
            record["method_spec_hash"] = stability_method["spec_hash"]
            record["matrix_hash"] = stability_contract["matrix_hash"]
            parameter_stability_runs.append(record)
    parameter_stability_summary = build_parameter_stability_summary(
        parameter_stability_runs,
        stability_contract["cells"],
    )
    parameter_stability_complete = len(parameter_stability_runs) == 42
    statistical_correction_evidence = [
        build_frozen_statistical_correction_evidence(
            role=role,
            strategy_id=protocol["strategy"]["name"],
            stability_contract=stability_contract,
            stability_runs=parameter_stability_runs,
            stability_summary=parameter_stability_summary,
            periods_per_year=annualization_factor(
                protocol["config"]["market"],
                protocol["config"]["timeframe"],
            ),
        )
        for role in ("VALIDATION", "FROZEN_TEST")
    ]
    statistical_correction_matrix_complete = (
        len(statistical_correction_evidence) == 2
    )
    statistical_correction_estimable = all(
        record["statistical_corrections_estimable"] is True
        for record in statistical_correction_evidence
    )
    all_run_records = [
        *strategy_runs,
        *execution_adversity_runs,
        *liquidity_capacity_runs,
        *benchmark_runs,
        *volatility_target_benchmark_runs,
        *walk_forward_runs,
        *parameter_stability_runs,
    ]
    expected_reproducibility_by_record_hash: dict[str, dict[str, Any]] = {}
    for record in all_run_records:
        expected_reproducibility = provenance_expectations.pop(id(record), None)
        if expected_reproducibility is None:
            raise ValueError("frozen_evaluation_provenance_expectation_missing")
        record_hash = canonical_payload_hash(record)
        if record_hash in expected_reproducibility_by_record_hash:
            raise ValueError("frozen_evaluation_provenance_record_duplicate")
        expected_reproducibility_by_record_hash[record_hash] = (
            expected_reproducibility
        )
    if provenance_expectations:
        raise ValueError("frozen_evaluation_provenance_expectation_orphaned")
    experiment_provenance = build_frozen_experiment_provenance_ledger(
        all_run_records,
        expected_reproducibility_by_record_hash,
        expected_context=protocol["experiment_context"]["context"],
        protocol_hash=protocol["protocol_hash"],
        symbol=protocol["config"]["symbol"],
        timeframe=protocol["config"]["timeframe"],
    )
    observation_provenance_receipts = (
        verified_multiple_testing_receipt_hashes(
            experiment_provenance,
            all_run_records,
            expected_context=protocol["experiment_context"]["context"],
            protocol_hash=protocol["protocol_hash"],
            symbol=protocol["config"]["symbol"],
            timeframe=protocol["config"]["timeframe"],
        )
    )
    multiple_testing_ledger = build_multiple_testing_ledger(
        stability_contract,
        parameter_stability_runs,
        parameter_stability_summary,
        walk_forward_contract,
        walk_forward_summary,
        observation_provenance_receipts=observation_provenance_receipts,
    )
    market_regime_analysis = [
        build_fixed_market_regime_analysis(
            _partition_frame(data, protocol, role),
            all_strategy_by_identity[(role, "BASE")],
            role=role,
            policy=protocol["market_regime_policy"],
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
        )
        for role in protocol["market_regime_policy"]["roles"]
    ]
    market_regime_slices_complete = (
        len(market_regime_analysis)
        == len(protocol["market_regime_policy"]["roles"])
        and all(
            item["coverage"]["observation_count"]
            == item["coverage"]["expected_observation_count"]
            and item["coverage"]["all_observations_classified"] is True
            and item["coverage"]["all_taxonomy_cells_present"] is True
            for item in market_regime_analysis
        )
    )
    tail_distribution_analysis = [
        build_frozen_distribution_analysis(
            _partition_frame(data, protocol, role),
            all_strategy_by_identity[(role, scenario_id)],
            role=role,
            scenario_id=scenario_id,
            policy=protocol["tail_distribution_policy"],
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
        )
        for role in protocol["tail_distribution_policy"]["roles"]
        for scenario_id in protocol["tail_distribution_policy"]["cost_scenarios"]
    ]
    tail_distribution_analyses_complete = (
        len(tail_distribution_analysis)
        == len(protocol["tail_distribution_policy"]["roles"])
        * len(protocol["tail_distribution_policy"]["cost_scenarios"])
        and all(
            item["coverage"]["period_return_count"]
            == item["coverage"]["expected_period_return_count"]
            and item["coverage"]["all_source_observations_retained"] is True
            and item["coverage"]["insufficient_sample_gaps_retained"] is True
            for item in tail_distribution_analysis
        )
    )

    nested_reproducibility_blocked = any(
        record["experiment_manifest"]["status"] != "PASS"
        for record in [
            *strategy_runs,
            *execution_adversity_runs,
            *liquidity_capacity_runs,
            *benchmark_runs,
            *volatility_target_benchmark_runs,
            *walk_forward_runs,
            *parameter_stability_runs,
        ]
    )
    blockers = list(STRUCTURAL_BLOCKERS)
    if nested_reproducibility_blocked:
        blockers.append("NESTED_EXPERIMENT_REPRODUCIBILITY_BLOCK")
    if (
        protocol["dataset"]["governance"]["source"]["source_kind"]
        == "SYNTHETIC_FIXTURE"
    ):
        blockers.append("SYNTHETIC_FIXTURE_DATASET_GOVERNANCE")
    if not volatility_comparison_observation_complete:
        blockers.append("VOLATILITY_MATCHED_COMPARISON_OBSERVATION_INCOMPLETE")
    if not liquidity_rejection_observed:
        blockers.append("LIQUIDITY_REJECTION_PROBE_INCOMPLETE")
    if not execution_adversity_observation_complete:
        blockers.append("EXECUTION_ADVERSITY_TARGET_SOURCE_ACTIVITY_INSUFFICIENT")
    if not bootstrap_confidence_observation_complete:
        blockers.append("BOOTSTRAP_CONFIDENCE_INSUFFICIENT_PAIRED_OBSERVATIONS")
    if not statistical_correction_estimable:
        blockers.append("FROZEN_STATISTICAL_CORRECTIONS_UNESTIMABLE")
    core = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "protocol_id": protocol["protocol_id"],
        "protocol_hash": protocol["protocol_hash"],
        "dataset_hash": protocol["dataset"]["dataset_hash"],
        "dataset_governance_hash": protocol["dataset"]["governance"]["governance_hash"],
        "dataset_calendar_conformance_hash": protocol["dataset"]["calendar_conformance"]["conformance_hash"],
        "strategy": dict(protocol["strategy"]),
        "strategy_runs": strategy_runs,
        "execution_adversity_runs": execution_adversity_runs,
        "liquidity_capacity_runs": liquidity_capacity_runs,
        "liquidity_rejection_evidence": liquidity_rejection_evidence,
        "benchmark_runs": benchmark_runs,
        "bootstrap_confidence_evidence": bootstrap_confidence_evidence,
        "volatility_matched_comparisons": volatility_matched_comparisons,
        "volatility_target_benchmark_runs": volatility_target_benchmark_runs,
        "walk_forward_runs": walk_forward_runs,
        "walk_forward_summary": walk_forward_summary,
        "parameter_stability_runs": parameter_stability_runs,
        "parameter_stability_summary": parameter_stability_summary,
        "statistical_correction_evidence": statistical_correction_evidence,
        "experiment_provenance": experiment_provenance,
        "multiple_testing_ledger": multiple_testing_ledger,
        "market_regime_analysis": market_regime_analysis,
        "tail_distribution_analysis": tail_distribution_analysis,
        "quality_gate": {
            "status": "BLOCK",
            "blockers": blockers,
            "nested_experiment_reproducibility_pass": not nested_reproducibility_blocked,
            "volatility_matched_comparison_matrix_complete": (
                volatility_comparison_matrix_complete
            ),
            "volatility_matched_comparison_observation_complete": (
                volatility_comparison_observation_complete
            ),
            "volatility_target_execution_baseline_complete": volatility_target_baseline_complete,
            "execution_adversity_matrix_complete": (
                len(execution_adversity_runs)
                == len(adversity_policy["roles"])
                * len(adversity_policy["scenarios"])
            ),
            "execution_adversity_observation_complete": (
                execution_adversity_observation_complete
            ),
            "liquidity_capacity_matrix_complete": (
                len(liquidity_capacity_runs) == len(liquidity_probe["roles"])
            ),
            "liquidity_capacity_partial_fill_observed": (
                liquidity_capacity_partial_fill_observed
            ),
            "liquidity_rejection_probe_matrix_complete": (
                len(liquidity_rejection_evidence)
                == len(liquidity_rejection_probe["roles"])
            ),
            "liquidity_rejection_observed": liquidity_rejection_observed,
            "bootstrap_confidence_matrix_complete": (
                bootstrap_confidence_matrix_complete
            ),
            "bootstrap_confidence_observation_complete": (
                bootstrap_confidence_observation_complete
            ),
            "walk_forward_fixed_schedule_complete": walk_forward_complete,
            "parameter_stability_matrix_complete": parameter_stability_complete,
            "statistical_correction_matrix_complete": (
                statistical_correction_matrix_complete
            ),
            "statistical_correction_estimable": statistical_correction_estimable,
            "multiple_testing_lineage_complete": (
                multiple_testing_ledger["observation_count"] == 42
            ),
            "market_regime_slices_complete": market_regime_slices_complete,
            "tail_distribution_analyses_complete": tail_distribution_analyses_complete,
            "return_contribution_concentration_matrix_complete": (
                len(tail_distribution_analysis) == 6
                and all(
                    set(item["distribution_evidence"]["concentration"])
                    == {
                        "top_positive_period_return_share",
                        "positive_period_return_hhi",
                        "compound_return_without_best_period",
                        "top_positive_month_share",
                        "compound_return_without_best_month",
                        "top_positive_trade_pnl_share",
                        "positive_trade_pnl_hhi",
                        "pnl_without_best_trade",
                        "best_fixed_21_period_window",
                    }
                    for item in tail_distribution_analysis
                )
            ),
            "frozen_test_is_blind": False,
            "frozen_test_single_consumption_proven": False,
            "natural_forward_evidence": False,
        },
        "authority": dict(AUTHORITY_LOCK),
    }
    report_hash = canonical_payload_hash(core)
    report = {
        **core,
        "report_id": f"hfer-{report_hash[:20]}",
        "report_hash": report_hash,
    }
    _require_native_json(report, path="report")
    return report


def verify_frozen_evaluation_report(
    report: Any,
    protocol: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
    *,
    experiment_context: dict[str, Any],
) -> bool:
    verify_frozen_evaluation_protocol(
        protocol,
        data,
        config,
        experiment_context=experiment_context,
    )
    _require_native_json(report, path="report")
    if type(report) is not dict:
        raise ValueError("frozen_evaluation_report_type_invalid")
    expected_keys = {
        "schema_version",
        "evidence_scope",
        "protocol_id",
        "protocol_hash",
        "dataset_hash",
        "dataset_governance_hash",
        "dataset_calendar_conformance_hash",
        "strategy",
        "strategy_runs",
        "execution_adversity_runs",
        "liquidity_capacity_runs",
        "liquidity_rejection_evidence",
        "benchmark_runs",
        "bootstrap_confidence_evidence",
        "volatility_matched_comparisons",
        "volatility_target_benchmark_runs",
        "walk_forward_runs",
        "walk_forward_summary",
        "parameter_stability_runs",
        "parameter_stability_summary",
        "statistical_correction_evidence",
        "experiment_provenance",
        "multiple_testing_ledger",
        "market_regime_analysis",
        "tail_distribution_analysis",
        "quality_gate",
        "authority",
        "report_id",
        "report_hash",
    }
    if set(report) != expected_keys:
        raise ValueError("frozen_evaluation_report_schema_invalid")
    if (
        report["schema_version"] != REPORT_SCHEMA_VERSION
        or report["evidence_scope"] != EVIDENCE_SCOPE
        or report["protocol_id"] != protocol["protocol_id"]
        or report["protocol_hash"] != protocol["protocol_hash"]
        or report["dataset_hash"] != protocol["dataset"]["dataset_hash"]
        or report["dataset_governance_hash"]
        != protocol["dataset"]["governance"]["governance_hash"]
        or report["dataset_calendar_conformance_hash"]
        != protocol["dataset"]["calendar_conformance"]["conformance_hash"]
        or report["strategy"] != protocol["strategy"]
        or report["authority"] != AUTHORITY_LOCK
    ):
        raise ValueError("frozen_evaluation_report_binding_invalid")

    expected_strategy_runs = {
        ("TRAIN", "BASE"),
        ("VALIDATION", "BASE"),
        ("VALIDATION", "DOUBLE_COST"),
        ("VALIDATION", "TRIPLE_COST"),
        ("FROZEN_TEST", "BASE"),
        ("FROZEN_TEST", "DOUBLE_COST"),
        ("FROZEN_TEST", "TRIPLE_COST"),
    }
    observed_strategy_runs: set[tuple[str, str]] = set()
    scenarios = _scenario_map(protocol)
    for record in report["strategy_runs"]:
        if type(record) is not dict or set(record) != {
            "run_kind",
            "role",
            "scenario_id",
            "fee_rate",
            "slippage_pct",
            "strategy_name",
            "strategy_version",
            "result",
            "experiment_manifest",
        }:
            raise ValueError("frozen_evaluation_strategy_run_shape_invalid")
        if (
            type(record["role"]) is not str
            or type(record["scenario_id"]) is not str
            or type(record["result"]) is not dict
            or type(record["experiment_manifest"]) is not dict
        ):
            raise ValueError("frozen_evaluation_strategy_run_shape_invalid")
        identity = (record["role"], record["scenario_id"])
        if identity in observed_strategy_runs or identity not in expected_strategy_runs:
            raise ValueError("frozen_evaluation_strategy_run_identity_invalid")
        observed_strategy_runs.add(identity)
        scenario = scenarios[record["scenario_id"]]
        manifest = record["experiment_manifest"]
        if (
            record["run_kind"] != "REGISTERED_STRATEGY"
            or record["fee_rate"] != scenario["fee_rate"]
            or record["slippage_pct"] != scenario["slippage_pct"]
            or record["strategy_name"] != protocol["strategy"]["name"]
            or record["strategy_version"] != protocol["strategy"]["version"]
            or manifest.get("evaluation_role") != record["role"]
            or manifest.get("evaluation_protocol_hash") != protocol["protocol_hash"]
            or manifest.get("evaluation_protocol_verified") is not True
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_strategy_run_verification_failed")
    if observed_strategy_runs != expected_strategy_runs:
        raise ValueError("frozen_evaluation_strategy_run_matrix_incomplete")

    adversity_policy = protocol["execution_adversity"]
    expected_adversity_runs = {
        (role, scenario_id)
        for role in adversity_policy["roles"]
        for scenario_id in EXECUTION_ADVERSITY_SCENARIO_IDS
    }
    strategy_by_role = {
        record["role"]: record
        for record in report["strategy_runs"]
        if record["scenario_id"] == "BASE"
    }
    observed_adversity_runs: set[tuple[str, str]] = set()
    adversity_required = {
        "run_kind",
        "role",
        "scenario_id",
        "fee_rate",
        "slippage_pct",
        "strategy_name",
        "strategy_version",
        "result",
        "experiment_manifest",
        "source_scenario_id",
        "source_result_hash",
        "scenario_policy_hash",
        "scenario_metadata",
        "observation_status",
        "source_result_delta",
        "source_input_dataset_hash",
        "stressed_input_dataset_hash",
        "unmodelled_gaps",
    }
    base_scenario = scenarios[adversity_policy["source_cost_scenario"]]
    for record in report["execution_adversity_runs"]:
        if type(record) is not dict or set(record) != adversity_required:
            raise ValueError("frozen_evaluation_execution_adversity_shape_invalid")
        identity = (record["role"], record["scenario_id"])
        if identity in observed_adversity_runs or identity not in expected_adversity_runs:
            raise ValueError("frozen_evaluation_execution_adversity_identity_invalid")
        observed_adversity_runs.add(identity)
        source_record = strategy_by_role[record["role"]]
        manifest = record["experiment_manifest"]
        expected_version = (
            EXECUTION_ADVERSITY_WRAPPER_VERSION
            if record["scenario_id"] in {
                "one_bar_signal_release_delay",
                "drop_every_third_actionable_signal",
            }
            else protocol["strategy"]["version"]
        )
        if (
            record["run_kind"] != "REGISTERED_EXECUTION_ADVERSITY"
            or record["source_scenario_id"] != "BASE"
            or record["fee_rate"] != base_scenario["fee_rate"]
            or record["slippage_pct"] != base_scenario["slippage_pct"]
            or record["strategy_name"] != protocol["strategy"]["name"]
            or record["strategy_version"] != expected_version
            or record["source_result_hash"]
            != source_record["experiment_manifest"]["result_hash"]
            or record["scenario_policy_hash"] != adversity_policy["policy_hash"]
            or record["source_input_dataset_hash"]
            != source_record["result"]["reproducibility"]["data_hash"]
            or record["stressed_input_dataset_hash"]
            != record["result"]["reproducibility"]["data_hash"]
            or record["unmodelled_gaps"] != adversity_policy["unmodelled_gaps"]
            or manifest.get("evaluation_role") != record["role"]
            or manifest.get("evaluation_protocol_hash") != protocol["protocol_hash"]
            or manifest.get("evaluation_protocol_verified") is not True
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
            or record["source_result_delta"]
            != build_execution_adversity_delta(
                source_record["result"],
                record["result"],
            )
            or not verify_execution_adversity_metadata(record["scenario_metadata"])
            or record["observation_status"]
            != execution_adversity_observation_status(
                record["scenario_metadata"],
                source_record["result"],
            )
        ):
            raise ValueError("frozen_evaluation_execution_adversity_verification_failed")
        if (
            record["scenario_id"]
            in {"one_bar_signal_release_delay", "drop_every_third_actionable_signal"}
            and record["stressed_input_dataset_hash"]
            != record["source_input_dataset_hash"]
        ):
            raise ValueError("frozen_evaluation_execution_adversity_dataset_drift")
    if observed_adversity_runs != expected_adversity_runs:
        raise ValueError("frozen_evaluation_execution_adversity_matrix_incomplete")

    liquidity_probe = adversity_policy["liquidity_capacity_probe"]
    expected_liquidity_runs = {
        (role, liquidity_probe["scenario_id"])
        for role in liquidity_probe["roles"]
    }
    observed_liquidity_runs: set[tuple[str, str]] = set()
    liquidity_required = {
        "run_kind",
        "role",
        "scenario_id",
        "fee_rate",
        "slippage_pct",
        "strategy_name",
        "strategy_version",
        "result",
        "experiment_manifest",
        "source_scenario_id",
        "source_benchmark_id",
        "source_result_hash",
        "scenario_policy_hash",
        "source_result_delta",
        "source_input_dataset_hash",
        "stressed_input_dataset_hash",
        "liquidity_capacity_summary",
        "unmodelled_gaps",
    }
    liquidity_source_scenario = scenarios[liquidity_probe["source_cost_scenario"]]
    for record in report["liquidity_capacity_runs"]:
        if type(record) is not dict or set(record) != liquidity_required:
            raise ValueError("frozen_evaluation_liquidity_capacity_shape_invalid")
        identity = (record["role"], record["scenario_id"])
        if identity in observed_liquidity_runs or identity not in expected_liquidity_runs:
            raise ValueError("frozen_evaluation_liquidity_capacity_identity_invalid")
        observed_liquidity_runs.add(identity)
        source_record = next(
            (
                candidate
                for candidate in report["benchmark_runs"]
                if type(candidate) is dict
                and candidate.get("role") == record["role"]
                and candidate.get("scenario_id")
                == liquidity_probe["source_cost_scenario"]
                and candidate.get("benchmark_id")
                == liquidity_probe["source_benchmark_id"]
            ),
            None,
        )
        if source_record is None:
            raise ValueError("frozen_evaluation_liquidity_capacity_source_missing")
        manifest = record["experiment_manifest"]
        if (
            record["run_kind"] != "REGISTERED_LIQUIDITY_CAPACITY_PROBE"
            or record["source_scenario_id"]
            != liquidity_probe["source_cost_scenario"]
            or record["source_benchmark_id"]
            != liquidity_probe["source_benchmark_id"]
            or record["fee_rate"] != liquidity_source_scenario["fee_rate"]
            or record["slippage_pct"]
            != liquidity_source_scenario["slippage_pct"]
            or record["strategy_name"] != source_record["strategy_name"]
            or record["strategy_version"] != source_record["strategy_version"]
            or record["source_result_hash"]
            != source_record["experiment_manifest"]["result_hash"]
            or record["scenario_policy_hash"] != adversity_policy["policy_hash"]
            or record["source_input_dataset_hash"]
            != source_record["result"]["reproducibility"]["data_hash"]
            or record["stressed_input_dataset_hash"]
            != record["result"]["reproducibility"]["data_hash"]
            or record["stressed_input_dataset_hash"]
            != record["source_input_dataset_hash"]
            or record["result"]["reproducibility"].get(
                "max_volume_participation_rate"
            )
            != liquidity_probe["max_volume_participation_rate"]
            or record["unmodelled_gaps"] != adversity_policy["unmodelled_gaps"]
            or record["source_result_delta"]
            != build_execution_adversity_delta(
                source_record["result"],
                record["result"],
            )
            or manifest.get("evaluation_role") != record["role"]
            or manifest.get("evaluation_protocol_hash") != protocol["protocol_hash"]
            or manifest.get("evaluation_protocol_verified") is not True
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
            or not verify_liquidity_capacity_summary(
                record["liquidity_capacity_summary"],
                record["result"],
                max_volume_participation_rate=liquidity_probe[
                    "max_volume_participation_rate"
                ],
            )
            or record["liquidity_capacity_summary"]["status"] != "OBSERVED"
        ):
            raise ValueError("frozen_evaluation_liquidity_capacity_verification_failed")
    if observed_liquidity_runs != expected_liquidity_runs:
        raise ValueError("frozen_evaluation_liquidity_capacity_matrix_incomplete")

    liquidity_rejection_probe = adversity_policy["liquidity_rejection_probe"]
    expected_rejection_roles = set(liquidity_rejection_probe["roles"])
    observed_rejection_roles: set[str] = set()
    for evidence in report["liquidity_rejection_evidence"]:
        if type(evidence) is not dict or type(evidence.get("role")) is not str:
            raise ValueError("frozen_evaluation_liquidity_rejection_shape_invalid")
        role = evidence["role"]
        if role in observed_rejection_roles or role not in expected_rejection_roles:
            raise ValueError("frozen_evaluation_liquidity_rejection_identity_invalid")
        observed_rejection_roles.add(role)
        source_record = next(
            record
            for record in report["liquidity_capacity_runs"]
            if record["role"] == role
            and record["scenario_id"]
            == liquidity_rejection_probe["source_capacity_scenario_id"]
        )
        if not verify_liquidity_rejection_evidence(
            evidence,
            source_record,
            probe=liquidity_rejection_probe,
            policy_hash=adversity_policy["policy_hash"],
            initial_cash=protocol["config"]["initial_cash"],
        ):
            raise ValueError("frozen_evaluation_liquidity_rejection_invalid")
    if observed_rejection_roles != expected_rejection_roles:
        raise ValueError("frozen_evaluation_liquidity_rejection_matrix_incomplete")

    expected_benchmark_runs = {
        (role, benchmark_id, scenario_id)
        for role in ("VALIDATION", "FROZEN_TEST")
        for benchmark_id, _version in BENCHMARKS
        for scenario_id, _multiplier in COST_SCENARIOS
    }
    observed_benchmark_runs: set[tuple[str, str, str]] = set()
    benchmark_specs = {
        item["benchmark_id"]: item
        for item in protocol["benchmarks"]
    }
    for record in report["benchmark_runs"]:
        required = {
            "run_kind",
            "role",
            "scenario_id",
            "fee_rate",
            "slippage_pct",
            "strategy_name",
            "strategy_version",
            "result",
            "experiment_manifest",
            "benchmark_id",
            "benchmark_spec_hash",
            "benchmark_params",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("frozen_evaluation_benchmark_run_shape_invalid")
        if (
            type(record["role"]) is not str
            or type(record["benchmark_id"]) is not str
            or type(record["scenario_id"]) is not str
            or type(record["result"]) is not dict
            or type(record["experiment_manifest"]) is not dict
            or type(record["benchmark_params"]) is not dict
        ):
            raise ValueError("frozen_evaluation_benchmark_run_shape_invalid")
        identity = (
            record["role"],
            record["benchmark_id"],
            record["scenario_id"],
        )
        if identity in observed_benchmark_runs or identity not in expected_benchmark_runs:
            raise ValueError("frozen_evaluation_benchmark_run_identity_invalid")
        observed_benchmark_runs.add(identity)
        manifest = record["experiment_manifest"]
        spec = benchmark_specs[record["benchmark_id"]]
        scenario = scenarios[record["scenario_id"]]
        reproducibility = record["result"].get("reproducibility")
        if (
            record["run_kind"] != "FIXED_BENCHMARK"
            or record["fee_rate"] != scenario["fee_rate"]
            or record["slippage_pct"] != scenario["slippage_pct"]
            or record["strategy_name"] != spec["strategy_name"]
            or record["strategy_version"] != spec["version"]
            or record["benchmark_spec_hash"] != spec["spec_hash"]
            or record["benchmark_params"] != spec["params"]
            or type(reproducibility) is not dict
            or reproducibility.get("param_hash")
            != canonical_payload_hash(spec["params"])
            or reproducibility.get("random_seed") != protocol["policy"]["random_seed"]
            or manifest.get("evaluation_role") != record["role"]
            or manifest.get("evaluation_protocol_hash") != protocol["protocol_hash"]
            or manifest.get("evaluation_protocol_verified") is not True
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_benchmark_run_verification_failed")
    if observed_benchmark_runs != expected_benchmark_runs:
        raise ValueError("frozen_evaluation_benchmark_run_matrix_incomplete")

    expected_bootstrap_records = {
        ("VALIDATION", "BASE", "ENGINE_BUY_AND_HOLD"),
        ("FROZEN_TEST", "BASE", "ENGINE_BUY_AND_HOLD"),
    }
    observed_bootstrap_records: set[tuple[str, str, str]] = set()
    bootstrap_required = {
        "role",
        "scenario_id",
        "benchmark_id",
        "strategy_result_hash",
        "benchmark_result_hash",
        "dataset_hash",
        "observation_class",
        "evidence",
    }
    strategy_base_by_role = {
        record["role"]: record
        for record in report["strategy_runs"]
        if record["scenario_id"] == "BASE"
        and record["role"] in {"VALIDATION", "FROZEN_TEST"}
    }
    buy_and_hold_base_by_role = {
        record["role"]: record
        for record in report["benchmark_runs"]
        if record["scenario_id"] == "BASE"
        and record["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
    }
    for record in report["bootstrap_confidence_evidence"]:
        if type(record) is not dict or set(record) != bootstrap_required:
            raise ValueError("frozen_evaluation_bootstrap_confidence_shape_invalid")
        if (
            type(record["role"]) is not str
            or type(record["scenario_id"]) is not str
            or type(record["benchmark_id"]) is not str
            or type(record["strategy_result_hash"]) is not str
            or type(record["benchmark_result_hash"]) is not str
            or type(record["dataset_hash"]) is not str
            or type(record["observation_class"]) is not str
            or type(record["evidence"]) is not dict
        ):
            raise ValueError("frozen_evaluation_bootstrap_confidence_shape_invalid")
        identity = (record["role"], record["scenario_id"], record["benchmark_id"])
        if identity in observed_bootstrap_records or identity not in expected_bootstrap_records:
            raise ValueError("frozen_evaluation_bootstrap_confidence_identity_invalid")
        observed_bootstrap_records.add(identity)
        source_strategy = strategy_base_by_role[record["role"]]
        source_benchmark = buy_and_hold_base_by_role[record["role"]]
        expected_observation_class = f"FROZEN_EVALUATION_{record['role']}_BASE"
        if (
            record["strategy_result_hash"]
            != source_strategy["experiment_manifest"]["result_hash"]
            or record["benchmark_result_hash"]
            != source_benchmark["experiment_manifest"]["result_hash"]
            or record["dataset_hash"] != protocol["dataset"]["dataset_hash"]
            or record["observation_class"] != expected_observation_class
        ):
            raise ValueError("frozen_evaluation_bootstrap_confidence_binding_invalid")
        receipt = verify_bootstrap_confidence_evidence(
            record["evidence"],
            source_strategy["result"]["equity_curve"],
            source_benchmark["result"]["equity_curve"],
            dataset_sha256=record["dataset_hash"],
            strategy_result_sha256=record["strategy_result_hash"],
            benchmark_result_sha256=record["benchmark_result_hash"],
            observation_class=record["observation_class"],
        )
        evidence = record["evidence"]
        if (
            receipt["state"] != evidence["evidence_state"]
            or receipt["paired_observation_count"]
            != evidence["sample_summary"]["paired_observation_count"]
            or receipt["replicate_count"] != evidence["replicate_count"]
            or receipt["interval_count"] != len(evidence["intervals"])
            or receipt["gaps"] != evidence["gaps"]
            or any(value is not False for value in receipt["authority"].values())
        ):
            raise ValueError("frozen_evaluation_bootstrap_confidence_verification_failed")
        if evidence["sample_summary"]["paired_observation_count"] < BOOTSTRAP_MINIMUM_OBSERVATION_COUNT:
            if (
                evidence["evidence_state"] != "GAP"
                or evidence["replicate_count"] != 0
                or evidence["intervals"] != []
                or evidence["gaps"] != [BOOTSTRAP_INSUFFICIENT_OBSERVATIONS_GAP]
            ):
                raise ValueError("frozen_evaluation_bootstrap_confidence_gap_invalid")
    if observed_bootstrap_records != expected_bootstrap_records:
        raise ValueError("frozen_evaluation_bootstrap_confidence_matrix_incomplete")

    execution_spec = protocol["execution_baseline_methods"][0]
    expected_target_identities = {
        (mapping["target_role"], scenario_id)
        for mapping in execution_spec["calibration_map"]
        for scenario_id in execution_spec["cost_scenarios"]
    }
    calibration_by_target = {
        mapping["target_role"]: mapping["calibration_role"]
        for mapping in execution_spec["calibration_map"]
    }
    all_strategy_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in report["strategy_runs"]
    }
    observed_target_identities: set[tuple[str, str]] = set()
    for record in report["volatility_target_benchmark_runs"]:
        required = {
            "run_kind",
            "role",
            "scenario_id",
            "fee_rate",
            "slippage_pct",
            "strategy_name",
            "strategy_version",
            "result",
            "experiment_manifest",
            "benchmark_id",
            "method_spec_hash",
            "calibration",
            "benchmark_params",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("frozen_evaluation_volatility_target_run_shape_invalid")
        if (
            type(record["role"]) is not str
            or type(record["scenario_id"]) is not str
            or type(record["result"]) is not dict
            or type(record["experiment_manifest"]) is not dict
            or type(record["calibration"]) is not dict
            or type(record["benchmark_params"]) is not dict
        ):
            raise ValueError("frozen_evaluation_volatility_target_run_shape_invalid")
        identity = (record["role"], record["scenario_id"])
        if identity in observed_target_identities or identity not in expected_target_identities:
            raise ValueError("frozen_evaluation_volatility_target_run_identity_invalid")
        observed_target_identities.add(identity)
        calibration_role = calibration_by_target[record["role"]]
        expected_calibration = build_prior_window_volatility_target_calibration(
            all_strategy_by_identity[(calibration_role, "BASE")],
            _partition_frame(data, protocol, calibration_role),
            target_role=record["role"],
            calibration_role=calibration_role,
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
            warmup_rows=execution_spec["warmup_rows"],
            exposure_cap=execution_spec["exposure_cap"],
        )
        expected_strategy = build_prior_window_volatility_target_strategy(
            expected_calibration
        )
        scenario = scenarios[record["scenario_id"]]
        reproducibility = record["result"].get("reproducibility")
        manifest = record["experiment_manifest"]
        if (
            record["run_kind"] != "PREREGISTERED_VOLATILITY_TARGET_BENCHMARK"
            or record["fee_rate"] != scenario["fee_rate"]
            or record["slippage_pct"] != scenario["slippage_pct"]
            or record["benchmark_id"] != execution_spec["benchmark_id"]
            or record["method_spec_hash"] != execution_spec["spec_hash"]
            or record["calibration"] != expected_calibration
            or record["strategy_name"] != expected_strategy.name
            or record["strategy_version"] != expected_strategy.version
            or record["benchmark_params"] != expected_strategy.params
            or type(reproducibility) is not dict
            or reproducibility.get("param_hash")
            != canonical_payload_hash(expected_strategy.params)
            or reproducibility.get("random_seed") != protocol["policy"]["random_seed"]
            or manifest.get("evaluation_role") != record["role"]
            or manifest.get("evaluation_protocol_hash") != protocol["protocol_hash"]
            or manifest.get("evaluation_protocol_verified") is not True
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_volatility_target_run_verification_failed")
    if observed_target_identities != expected_target_identities:
        raise ValueError("frozen_evaluation_volatility_target_run_matrix_incomplete")

    comparison_spec = protocol["comparison_methods"][0]
    expected_comparison_identities = {
        (role, scenario_id)
        for role in comparison_spec["roles"]
        for scenario_id in comparison_spec["cost_scenarios"]
    }
    strategy_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in report["strategy_runs"]
        if record["role"] in comparison_spec["roles"]
    }
    benchmark_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in report["benchmark_runs"]
        if record["benchmark_id"] == comparison_spec["benchmark_id"]
    }
    observed_comparison_identities: set[tuple[str, str]] = set()
    for comparison in report["volatility_matched_comparisons"]:
        if (
            type(comparison) is not dict
            or type(comparison.get("role")) is not str
            or type(comparison.get("scenario_id")) is not str
        ):
            raise ValueError("frozen_evaluation_volatility_comparison_shape_invalid")
        identity = (comparison["role"], comparison["scenario_id"])
        if (
            identity in observed_comparison_identities
            or identity not in expected_comparison_identities
        ):
            raise ValueError("frozen_evaluation_volatility_comparison_identity_invalid")
        observed_comparison_identities.add(identity)
        expected = build_volatility_matched_comparison(
            strategy_by_identity[identity],
            benchmark_by_identity[identity],
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
        )
        expected["method_spec_hash"] = comparison_spec["spec_hash"]
        if comparison != expected:
            raise ValueError("frozen_evaluation_volatility_comparison_verification_failed")
    if observed_comparison_identities != expected_comparison_identities:
        raise ValueError("frozen_evaluation_volatility_comparison_matrix_incomplete")

    walk_forward_contract = protocol["walk_forward"]
    walk_forward_method = walk_forward_contract["method"]
    walk_forward_schedule = walk_forward_contract["schedule"]
    expected_walk_forward_identities = {
        (fold["fold_id"], scenario_id)
        for fold in walk_forward_schedule["folds"]
        for scenario_id in walk_forward_method["cost_scenarios"]
    }
    folds_by_id = {
        fold["fold_id"]: fold
        for fold in walk_forward_schedule["folds"]
    }
    observed_walk_forward_identities: set[tuple[str, str]] = set()
    for record in report["walk_forward_runs"]:
        required = {
            "run_kind",
            "role",
            "scenario_id",
            "fee_rate",
            "slippage_pct",
            "strategy_name",
            "strategy_version",
            "result",
            "experiment_manifest",
            "fold_id",
            "method_spec_hash",
            "schedule_hash",
            "calibration_window",
            "purge_window",
            "evaluation_window",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("frozen_evaluation_walk_forward_run_shape_invalid")
        if (
            type(record["fold_id"]) is not str
            or type(record["scenario_id"]) is not str
            or type(record["result"]) is not dict
            or type(record["experiment_manifest"]) is not dict
            or type(record["calibration_window"]) is not dict
            or type(record["purge_window"]) is not dict
            or type(record["evaluation_window"]) is not dict
        ):
            raise ValueError("frozen_evaluation_walk_forward_run_shape_invalid")
        identity = (record["fold_id"], record["scenario_id"])
        if (
            identity in observed_walk_forward_identities
            or identity not in expected_walk_forward_identities
        ):
            raise ValueError("frozen_evaluation_walk_forward_run_identity_invalid")
        observed_walk_forward_identities.add(identity)
        fold = folds_by_id[record["fold_id"]]
        scenario = scenarios[record["scenario_id"]]
        reproducibility = record["result"].get("reproducibility")
        manifest = record["experiment_manifest"]
        ranking_gate = manifest.get("ranking_gate")
        if (
            record["run_kind"] != "FIXED_PARAMETER_WALK_FORWARD"
            or record["role"] != "WALK_FORWARD_EVAL"
            or record["fee_rate"] != scenario["fee_rate"]
            or record["slippage_pct"] != scenario["slippage_pct"]
            or record["strategy_name"] != protocol["strategy"]["name"]
            or record["strategy_version"] != protocol["strategy"]["version"]
            or record["method_spec_hash"] != walk_forward_method["spec_hash"]
            or record["schedule_hash"] != walk_forward_schedule["schedule_hash"]
            or record["calibration_window"] != fold["calibration"]
            or record["purge_window"] != fold["purge"]
            or record["evaluation_window"] != fold["evaluation"]
            or type(reproducibility) is not dict
            or reproducibility.get("data_hash") != fold["evaluation"]["data_hash"]
            or reproducibility.get("param_hash") != protocol["strategy"]["params_hash"]
            or manifest.get("evaluation_role") != "UNCLASSIFIED"
            or type(ranking_gate) is not dict
            or ranking_gate.get("input_allowed") is not False
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_walk_forward_run_verification_failed")
    if observed_walk_forward_identities != expected_walk_forward_identities:
        raise ValueError("frozen_evaluation_walk_forward_run_matrix_incomplete")
    expected_walk_forward_summary = build_fixed_walk_forward_summary(
        report["walk_forward_runs"],
        walk_forward_schedule,
    )
    if report["walk_forward_summary"] != expected_walk_forward_summary:
        raise ValueError("frozen_evaluation_walk_forward_summary_invalid")

    stability_contract = protocol["parameter_stability"]
    stability_method = stability_contract["method"]
    cells_by_id = {
        cell["cell_id"]: cell
        for cell in stability_contract["cells"]
    }
    expected_stability_identities = {
        (role, cell_id)
        for role in stability_method["roles"]
        for cell_id in cells_by_id
    }
    observed_stability_identities: set[tuple[str, str]] = set()
    for record in report["parameter_stability_runs"]:
        required = {
            "run_kind",
            "role",
            "scenario_id",
            "fee_rate",
            "slippage_pct",
            "strategy_name",
            "strategy_version",
            "result",
            "experiment_manifest",
            "cell_id",
            "segment",
            "is_center",
            "axes",
            "params",
            "params_hash",
            "cell_hash",
            "method_spec_hash",
            "matrix_hash",
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("frozen_evaluation_parameter_stability_run_shape_invalid")
        if (
            type(record["role"]) is not str
            or type(record["cell_id"]) is not str
            or type(record["result"]) is not dict
            or type(record["experiment_manifest"]) is not dict
            or type(record["axes"]) is not dict
            or type(record["params"]) is not dict
        ):
            raise ValueError("frozen_evaluation_parameter_stability_run_shape_invalid")
        identity = (record["role"], record["cell_id"])
        if identity in observed_stability_identities or identity not in expected_stability_identities:
            raise ValueError("frozen_evaluation_parameter_stability_run_identity_invalid")
        observed_stability_identities.add(identity)
        cell = cells_by_id[record["cell_id"]]
        scenario = scenarios[stability_method["cost_scenario"]]
        expected_strategy = build_strategy(config.strategy.name, cell["params"])
        reproducibility = record["result"].get("reproducibility")
        manifest = record["experiment_manifest"]
        ranking_gate = manifest.get("ranking_gate")
        if (
            record["run_kind"] != "PARAMETER_STABILITY_OBSERVATION"
            or record["scenario_id"] != stability_method["cost_scenario"]
            or record["fee_rate"] != scenario["fee_rate"]
            or record["slippage_pct"] != scenario["slippage_pct"]
            or record["strategy_name"] != expected_strategy.name
            or record["strategy_version"] != expected_strategy.version
            or record["segment"] != cell["segment"]
            or record["is_center"] is not cell["is_center"]
            or record["axes"] != cell["axes"]
            or record["params"] != cell["params"]
            or record["params_hash"] != cell["params_hash"]
            or record["cell_hash"] != cell["cell_hash"]
            or record["method_spec_hash"] != stability_method["spec_hash"]
            or record["matrix_hash"] != stability_contract["matrix_hash"]
            or type(reproducibility) is not dict
            or reproducibility.get("param_hash") != cell["params_hash"]
            or manifest.get("evaluation_role") != "UNCLASSIFIED"
            or type(ranking_gate) is not dict
            or ranking_gate.get("input_allowed") is not False
            or manifest.get("parameter_selection_allowed") is not False
            or manifest.get("paper_authorized") is not False
            or manifest.get("live_order_allowed") is not False
            or manifest.get("order_entry_allowed") is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_parameter_stability_run_verification_failed")
    if observed_stability_identities != expected_stability_identities:
        raise ValueError("frozen_evaluation_parameter_stability_run_matrix_incomplete")
    expected_stability_summary = build_parameter_stability_summary(
        report["parameter_stability_runs"],
        stability_contract["cells"],
    )
    if report["parameter_stability_summary"] != expected_stability_summary:
        raise ValueError("frozen_evaluation_parameter_stability_summary_invalid")
    expected_statistical_correction = [
        build_frozen_statistical_correction_evidence(
            role=role,
            strategy_id=protocol["strategy"]["name"],
            stability_contract=stability_contract,
            stability_runs=report["parameter_stability_runs"],
            stability_summary=report["parameter_stability_summary"],
            periods_per_year=annualization_factor(
                protocol["config"]["market"],
                protocol["config"]["timeframe"],
            ),
        )
        for role in ("VALIDATION", "FROZEN_TEST")
    ]
    if report["statistical_correction_evidence"] != expected_statistical_correction:
        raise ValueError("frozen_evaluation_statistical_correction_invalid")
    for role, evidence in zip(
        ("VALIDATION", "FROZEN_TEST"),
        report["statistical_correction_evidence"],
    ):
        verify_frozen_statistical_correction_evidence(
            evidence,
            role=role,
            strategy_id=protocol["strategy"]["name"],
            stability_contract=stability_contract,
            stability_runs=report["parameter_stability_runs"],
            stability_summary=report["parameter_stability_summary"],
            periods_per_year=annualization_factor(
                protocol["config"]["market"],
                protocol["config"]["timeframe"],
            ),
        )
    expected_multiple_testing_ledger = build_multiple_testing_ledger(
        stability_contract,
        report["parameter_stability_runs"],
        report["parameter_stability_summary"],
        protocol["walk_forward"],
        report["walk_forward_summary"],
        observation_provenance_receipts=(
            verified_multiple_testing_receipt_hashes(
                report["experiment_provenance"],
                [
                    *report["strategy_runs"],
                    *report["execution_adversity_runs"],
                    *report["liquidity_capacity_runs"],
                    *report["benchmark_runs"],
                    *report["volatility_target_benchmark_runs"],
                    *report["walk_forward_runs"],
                    *report["parameter_stability_runs"],
                ],
                expected_context=protocol["experiment_context"]["context"],
                protocol_hash=protocol["protocol_hash"],
                symbol=protocol["config"]["symbol"],
                timeframe=protocol["config"]["timeframe"],
            )
        ),
    )
    if report["multiple_testing_ledger"] != expected_multiple_testing_ledger:
        raise ValueError("frozen_evaluation_multiple_testing_ledger_invalid")

    strategy_by_identity = {
        (record["role"], record["scenario_id"]): record
        for record in report["strategy_runs"]
    }
    expected_market_regime_analysis = [
        build_fixed_market_regime_analysis(
            _partition_frame(data, protocol, role),
            strategy_by_identity[(role, "BASE")],
            role=role,
            policy=protocol["market_regime_policy"],
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
        )
        for role in protocol["market_regime_policy"]["roles"]
    ]
    if report["market_regime_analysis"] != expected_market_regime_analysis:
        raise ValueError("frozen_evaluation_market_regime_analysis_invalid")

    expected_tail_distribution_analysis = [
        build_frozen_distribution_analysis(
            _partition_frame(data, protocol, role),
            strategy_by_identity[(role, scenario_id)],
            role=role,
            scenario_id=scenario_id,
            policy=protocol["tail_distribution_policy"],
            initial_equity=protocol["config"]["initial_cash"],
            market=protocol["config"]["market"],
            timeframe=protocol["config"]["timeframe"],
        )
        for role in protocol["tail_distribution_policy"]["roles"]
        for scenario_id in protocol["tail_distribution_policy"]["cost_scenarios"]
    ]
    if report["tail_distribution_analysis"] != expected_tail_distribution_analysis:
        raise ValueError("frozen_evaluation_tail_distribution_analysis_invalid")

    nested_blocked = any(
        record["experiment_manifest"]["status"] != "PASS"
        for record in [
            *report["strategy_runs"],
            *report["execution_adversity_runs"],
            *report["liquidity_capacity_runs"],
            *report["benchmark_runs"],
            *report["volatility_target_benchmark_runs"],
            *report["walk_forward_runs"],
            *report["parameter_stability_runs"],
        ]
    )
    expected_blockers = list(STRUCTURAL_BLOCKERS)
    if nested_blocked:
        expected_blockers.append("NESTED_EXPERIMENT_REPRODUCIBILITY_BLOCK")
    expected_quality_gate = {
        "status": "BLOCK",
        "blockers": expected_blockers,
        "nested_experiment_reproducibility_pass": not nested_blocked,
        "volatility_matched_comparison_matrix_complete": (
            len(report["volatility_matched_comparisons"])
            == len(comparison_spec["roles"])
            * len(comparison_spec["cost_scenarios"])
        ),
        "volatility_matched_comparison_observation_complete": all(
            item["comparison_status"] == "OBSERVED"
            for item in report["volatility_matched_comparisons"]
        ),
        "volatility_target_execution_baseline_complete": all(
            record["calibration"]["calibration_status"] == "CALIBRATED"
            for record in report["volatility_target_benchmark_runs"]
        ),
        "execution_adversity_matrix_complete": (
            len(report["execution_adversity_runs"])
            == len(protocol["execution_adversity"]["roles"])
            * len(protocol["execution_adversity"]["scenarios"])
        ),
        "execution_adversity_observation_complete": all(
            record["observation_status"] == "OBSERVED"
            for record in report["execution_adversity_runs"]
        ),
        "liquidity_capacity_matrix_complete": (
            len(report["liquidity_capacity_runs"])
            == len(protocol["execution_adversity"]["liquidity_capacity_probe"]["roles"])
        ),
        "liquidity_capacity_partial_fill_observed": all(
            record["liquidity_capacity_summary"]["status"] == "OBSERVED"
            for record in report["liquidity_capacity_runs"]
        ),
        "liquidity_rejection_probe_matrix_complete": (
            len(report["liquidity_rejection_evidence"])
            == len(protocol["execution_adversity"]["liquidity_rejection_probe"]["roles"])
        ),
        "liquidity_rejection_observed": all(
            record["decision"]["status"] == "REJECTED"
            for record in report["liquidity_rejection_evidence"]
        ),
        "bootstrap_confidence_matrix_complete": (
            len(report["bootstrap_confidence_evidence"]) == 2
        ),
        "bootstrap_confidence_observation_complete": all(
            record["evidence"]["evidence_state"] == "OBSERVED"
            for record in report["bootstrap_confidence_evidence"]
        ),
        "walk_forward_fixed_schedule_complete": (
            len(report["walk_forward_runs"]) == 6
        ),
        "parameter_stability_matrix_complete": (
            len(report["parameter_stability_runs"]) == 42
        ),
        "statistical_correction_matrix_complete": (
            len(report["statistical_correction_evidence"]) == 2
        ),
        "statistical_correction_estimable": all(
            record["statistical_corrections_estimable"] is True
            for record in report["statistical_correction_evidence"]
        ),
        "multiple_testing_lineage_complete": (
            report["multiple_testing_ledger"]["observation_count"] == 42
        ),
        "market_regime_slices_complete": (
            len(report["market_regime_analysis"])
            == len(protocol["market_regime_policy"]["roles"])
            and all(
                item["coverage"]["observation_count"]
                == item["coverage"]["expected_observation_count"]
                and item["coverage"]["all_observations_classified"] is True
                and item["coverage"]["all_taxonomy_cells_present"] is True
                for item in report["market_regime_analysis"]
            )
        ),
        "tail_distribution_analyses_complete": (
            len(report["tail_distribution_analysis"])
            == len(protocol["tail_distribution_policy"]["roles"])
            * len(protocol["tail_distribution_policy"]["cost_scenarios"])
            and all(
                item["coverage"]["period_return_count"]
                == item["coverage"]["expected_period_return_count"]
                and item["coverage"]["all_source_observations_retained"] is True
                and item["coverage"]["insufficient_sample_gaps_retained"] is True
                for item in report["tail_distribution_analysis"]
            )
        ),
        "return_contribution_concentration_matrix_complete": (
            len(report["tail_distribution_analysis"]) == 6
            and all(
                set(item["distribution_evidence"]["concentration"])
                == {
                    "top_positive_period_return_share",
                    "positive_period_return_hhi",
                    "compound_return_without_best_period",
                    "top_positive_month_share",
                    "compound_return_without_best_month",
                    "top_positive_trade_pnl_share",
                    "positive_trade_pnl_hhi",
                    "pnl_without_best_trade",
                    "best_fixed_21_period_window",
                }
                for item in report["tail_distribution_analysis"]
            )
        ),
        "frozen_test_is_blind": False,
        "frozen_test_single_consumption_proven": False,
        "natural_forward_evidence": False,
    }
    if (
        protocol["dataset"]["governance"]["source"]["source_kind"]
        == "SYNTHETIC_FIXTURE"
    ):
        expected_quality_gate["blockers"].append(
            "SYNTHETIC_FIXTURE_DATASET_GOVERNANCE"
        )
    if not expected_quality_gate[
        "volatility_matched_comparison_observation_complete"
    ]:
        expected_quality_gate["blockers"].append(
            "VOLATILITY_MATCHED_COMPARISON_OBSERVATION_INCOMPLETE"
        )
    if not expected_quality_gate["liquidity_rejection_observed"]:
        expected_quality_gate["blockers"].append(
            "LIQUIDITY_REJECTION_PROBE_INCOMPLETE"
        )
    if not expected_quality_gate["execution_adversity_observation_complete"]:
        expected_quality_gate["blockers"].append(
            "EXECUTION_ADVERSITY_TARGET_SOURCE_ACTIVITY_INSUFFICIENT"
        )
    if not expected_quality_gate["bootstrap_confidence_observation_complete"]:
        expected_quality_gate["blockers"].append(
            "BOOTSTRAP_CONFIDENCE_INSUFFICIENT_PAIRED_OBSERVATIONS"
        )
    if not expected_quality_gate["statistical_correction_estimable"]:
        expected_quality_gate["blockers"].append(
            "FROZEN_STATISTICAL_CORRECTIONS_UNESTIMABLE"
        )
    if report["quality_gate"] != expected_quality_gate:
        raise ValueError("frozen_evaluation_quality_gate_invalid")
    core = {key: value for key, value in report.items() if key not in {"report_id", "report_hash"}}
    expected_hash = canonical_payload_hash(core)
    if (
        report["report_hash"] != expected_hash
        or report["report_id"] != f"hfer-{expected_hash[:20]}"
    ):
        raise ValueError("frozen_evaluation_report_hash_invalid")
    return True


def _markdown_cell(value: Any, *, field: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"frozen_evaluation_markdown_{field}_invalid")
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _markdown_metric(result: dict[str, Any], field: str) -> float:
    value = result.get(field)
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"frozen_evaluation_markdown_{field}_invalid")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"frozen_evaluation_markdown_{field}_invalid")
    return parsed


def _markdown_observation_row(record: dict[str, Any], *, benchmark: bool) -> str:
    result = record["result"]
    trades = result.get("trades")
    if type(trades) is not int or type(trades) is bool or trades < 0:
        raise ValueError("frozen_evaluation_markdown_trades_invalid")
    ambiguous = result.get("ambiguous_intrabar_count")
    if type(ambiguous) is not int or type(ambiguous) is bool or ambiguous < 0:
        raise ValueError("frozen_evaluation_markdown_ambiguous_intrabar_count_invalid")
    role = _markdown_cell(record["role"], field="role")
    cells = [
        "",
        role,
    ]
    if benchmark:
        cells.extend([
            _markdown_cell(record["benchmark_id"], field="benchmark_id"),
            _markdown_cell(record["scenario_id"], field="scenario_id"),
        ])
    else:
        cells.append(_markdown_cell(record["scenario_id"], field="scenario_id"))
    cells.extend([
        format(_markdown_metric(record, "fee_rate"), ".6f"),
        format(_markdown_metric(record, "slippage_pct"), ".6f"),
        f"{_markdown_metric(result, 'total_return') * 100:.4f}%",
        f"{_markdown_metric(result, 'annualized_return') * 100:.4f}%",
        format(_markdown_metric(result, "sharpe_ratio"), ".4f"),
        f"{_markdown_metric(result, 'max_drawdown') * 100:.4f}%",
        format(_markdown_metric(result, "final_equity"), ".4f"),
        format(_markdown_metric(result, "total_fees"), ".4f"),
        str(trades),
        f"{_markdown_metric(result, 'win_rate') * 100:.4f}%",
        str(ambiguous),
        "",
    ])
    return " | ".join(cells)


def _markdown_comparison_value(record: dict[str, Any], field: str, *, percent: bool) -> str:
    value = record.get(field)
    if value is None:
        return "UNKNOWN"
    parsed = _markdown_metric(record, field)
    return f"{parsed * 100:.4f}%" if percent else format(parsed, ".6f")


def _markdown_volatility_comparison_row(record: dict[str, Any]) -> str:
    return " | ".join([
        "",
        _markdown_cell(record["role"], field="comparison_role"),
        _markdown_cell(record["scenario_id"], field="comparison_scenario"),
        _markdown_comparison_value(
            record,
            "strategy_observed_annualized_volatility",
            percent=True,
        ),
        _markdown_comparison_value(
            record,
            "benchmark_observed_annualized_volatility",
            percent=True,
        ),
        _markdown_comparison_value(record, "scale_factor", percent=False),
        _markdown_comparison_value(
            record,
            "matched_benchmark_annualized_volatility",
            percent=True,
        ),
        _markdown_comparison_value(
            record,
            "matched_benchmark_curve_total_return",
            percent=True,
        ),
        _markdown_comparison_value(
            record,
            "strategy_minus_matched_benchmark_curve_total_return",
            percent=True,
        ),
        _markdown_cell(record["comparison_status"], field="comparison_status"),
        _markdown_cell(
            ", ".join(record["blockers"]) if record["blockers"] else "NONE",
            field="comparison_blockers",
        ),
        "",
    ])


def _markdown_volatility_target_row(record: dict[str, Any]) -> str:
    calibration = record["calibration"]
    result = record["result"]
    return " | ".join([
        "",
        _markdown_cell(record["role"], field="volatility_target_role"),
        _markdown_cell(
            calibration["calibration_role"],
            field="volatility_target_calibration_role",
        ),
        _markdown_cell(record["scenario_id"], field="volatility_target_scenario"),
        f"{_markdown_metric(calibration, 'target_annualized_volatility') * 100:.4f}%",
        f"{_markdown_metric(calibration, 'source_annualized_volatility') * 100:.4f}%",
        f"{_markdown_metric(calibration, 'applied_exposure') * 100:.4f}%",
        str(calibration["exposure_capped"]).lower(),
        f"{_markdown_metric(result, 'total_return') * 100:.4f}%",
        _markdown_cell(
            calibration["calibration_status"],
            field="volatility_target_calibration_status",
        ),
        "",
    ])


def _markdown_walk_forward_row(record: dict[str, Any]) -> str:
    result = record["result"]
    manifest = record["experiment_manifest"]
    return " | ".join([
        "",
        _markdown_cell(record["fold_id"], field="walk_forward_fold_id"),
        _markdown_cell(record["scenario_id"], field="walk_forward_scenario_id"),
        _markdown_cell(
            record["calibration_window"]["start_time"],
            field="walk_forward_calibration_start",
        ),
        _markdown_cell(
            record["calibration_window"]["end_time"],
            field="walk_forward_calibration_end",
        ),
        _markdown_cell(
            record["evaluation_window"]["start_time"],
            field="walk_forward_evaluation_start",
        ),
        _markdown_cell(
            record["evaluation_window"]["end_time"],
            field="walk_forward_evaluation_end",
        ),
        f"{_markdown_metric(result, 'total_return') * 100:.4f}%",
        f"{_markdown_metric(result, 'max_drawdown') * 100:.4f}%",
        _markdown_cell(manifest["evaluation_role"], field="walk_forward_manifest_role"),
        str(manifest["ranking_gate"]["input_allowed"]).lower(),
        "",
    ])


def _markdown_walk_forward_summary_row(record: dict[str, Any]) -> str:
    return " | ".join([
        "",
        _markdown_cell(record["scenario_id"], field="walk_forward_summary_scenario"),
        str(record["fold_count"]),
        f"{_markdown_metric(record, 'median_total_return') * 100:.4f}%",
        f"{_markdown_metric(record, 'minimum_total_return') * 100:.4f}%",
        f"{_markdown_metric(record, 'maximum_total_return') * 100:.4f}%",
        f"{_markdown_metric(record, 'median_max_drawdown') * 100:.4f}%",
        str(record["nested_reproducibility_pass"]).lower(),
        "",
    ])


def _markdown_parameter_stability_risk_row(record: dict[str, Any]) -> str:
    result = record["result"]
    return " | ".join([
        "",
        _markdown_cell(record["role"], field="stability_role"),
        _markdown_cell(record["axes"]["risk_parameter"], field="stability_parameter"),
        f"{_markdown_metric(record['axes'], 'risk_parameter_pct') * 100:.0f}%",
        f"{_markdown_metric(result, 'total_return') * 100:.4f}%",
        f"{_markdown_metric(result, 'max_drawdown') * 100:.4f}%",
        "false",
        "",
    ])


def _markdown_parameter_stability_summary_row(record: dict[str, Any]) -> str:
    return " | ".join([
        "",
        _markdown_cell(record["role"], field="stability_summary_role"),
        str(record["observed_cell_count"]),
        f"{_markdown_metric(record, 'center_total_return') * 100:.4f}%",
        f"{_markdown_metric(record, 'median_total_return') * 100:.4f}%",
        f"{_markdown_metric(record, 'maximum_absolute_deviation_from_center') * 100:.4f}%",
        str(record["timing_grid_complete"]).lower(),
        str(record["risk_oat_complete"]).lower(),
        str(record["all_nested_manifests_non_rankable"]).lower(),
        "",
    ])


def _markdown_market_regime_row(
    analysis: dict[str, Any],
    regime_slice: dict[str, Any],
) -> str:
    def percent(value: Any) -> str:
        return "UNKNOWN" if value is None else f"{float(value) * 100:.4f}%"

    return (
        "| "
        + " | ".join([
            _markdown_cell(analysis["role"], field="market_regime_role"),
            _markdown_cell(regime_slice["regime_id"], field="market_regime_id"),
            str(regime_slice["observation_count"]),
            _markdown_cell(regime_slice["status"], field="market_regime_status"),
            percent(regime_slice["strategy_compounded_return"]),
            percent(regime_slice["market_compounded_return"]),
        ])
        + " |"
    )


def _markdown_tail_distribution_row(analysis: dict[str, Any]) -> str:
    metrics = analysis["distribution_evidence"]["metrics"]

    def number(value: Any) -> str:
        return "UNKNOWN" if value is None else str(value)

    def percent(value: Any) -> str:
        return "UNKNOWN" if value is None else f"{float(value) * 100:.4f}%"

    return (
        "| "
        + " | ".join([
            _markdown_cell(analysis["role"], field="distribution_role"),
            _markdown_cell(analysis["scenario_id"], field="distribution_scenario"),
            _markdown_cell(
                analysis["distribution_evidence"]["status"],
                field="distribution_status",
            ),
            str(metrics["period_return_count"]),
            str(metrics["closed_trade_count"]),
            percent(metrics["annualized_volatility"]),
            number(metrics["sortino_ratio"]),
            number(metrics["calmar_ratio"]),
            percent(metrics["max_drawdown"]),
            str(metrics["max_drawdown_duration_periods"]),
            number(metrics["turnover_ratio"]),
            percent(metrics["market_exposure_ratio"]),
            percent(metrics["tail_var_95"]),
            percent(metrics["tail_cvar_95"]),
            ", ".join(analysis["distribution_evidence"]["gaps"]),
        ])
        + " |"
    )


def render_frozen_evaluation_markdown(
    report: dict[str, Any],
    protocol: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
    *,
    experiment_context: dict[str, Any],
) -> str:
    """Render verified ADR0509 evidence without writing or granting authority."""

    verify_frozen_evaluation_report(
        report,
        protocol,
        data,
        config,
        experiment_context=experiment_context,
    )
    role_order = {"TRAIN": 0, "VALIDATION": 1, "FROZEN_TEST": 2}
    scenario_order = {"BASE": 0, "DOUBLE_COST": 1, "TRIPLE_COST": 2}
    benchmark_order = {
        item["benchmark_id"]: index
        for index, item in enumerate(protocol["benchmarks"])
    }
    strategy_runs = sorted(
        report["strategy_runs"],
        key=lambda item: (
            role_order[item["role"]],
            scenario_order[item["scenario_id"]],
        ),
    )
    adversity_order = {
        scenario_id: index
        for index, scenario_id in enumerate(EXECUTION_ADVERSITY_SCENARIO_IDS)
    }
    execution_adversity_runs = sorted(
        report["execution_adversity_runs"],
        key=lambda item: (
            role_order[item["role"]],
            adversity_order[item["scenario_id"]],
        ),
    )
    liquidity_capacity_runs = sorted(
        report["liquidity_capacity_runs"],
        key=lambda item: role_order[item["role"]],
    )
    liquidity_rejection_evidence = sorted(
        report["liquidity_rejection_evidence"],
        key=lambda item: role_order[item["role"]],
    )
    benchmark_runs = sorted(
        report["benchmark_runs"],
        key=lambda item: (
            role_order[item["role"]],
            benchmark_order[item["benchmark_id"]],
            scenario_order[item["scenario_id"]],
        ),
    )
    bootstrap_confidence_records = sorted(
        report["bootstrap_confidence_evidence"],
        key=lambda item: role_order[item["role"]],
    )
    statistical_correction_records = sorted(
        report["statistical_correction_evidence"],
        key=lambda item: role_order[item["role"]],
    )
    volatility_comparisons = sorted(
        report["volatility_matched_comparisons"],
        key=lambda item: (
            role_order[item["role"]],
            scenario_order[item["scenario_id"]],
        ),
    )
    volatility_target_runs = sorted(
        report["volatility_target_benchmark_runs"],
        key=lambda item: (
            role_order[item["role"]],
            scenario_order[item["scenario_id"]],
        ),
    )
    walk_forward_runs = sorted(
        report["walk_forward_runs"],
        key=lambda item: (
            item["fold_id"],
            scenario_order[item["scenario_id"]],
        ),
    )
    parameter_stability_runs = sorted(
        report["parameter_stability_runs"],
        key=lambda item: (
            role_order[item["role"]],
            item["segment"],
            item["cell_id"],
        ),
    )
    dataset = protocol["dataset"]
    governance = dataset["governance"]
    calendar_conformance = dataset["calendar_conformance"]
    source_config = protocol["config"]
    strategy = protocol["strategy"]
    quality = report["quality_gate"]
    lines = [
        "# Hakimi Frozen Evaluation Report",
        "",
        f"Renderer: `{MARKDOWN_REPORT_VERSION}`",
        "",
        "## SOURCE",
        "",
        f"- Report ID: `{_markdown_cell(report['report_id'], field='report_id')}`",
        f"- Report SHA-256: `{_markdown_cell(report['report_hash'], field='report_hash')}`",
        f"- Protocol ID: `{_markdown_cell(protocol['protocol_id'], field='protocol_id')}`",
        f"- Protocol SHA-256: `{_markdown_cell(protocol['protocol_hash'], field='protocol_hash')}`",
        f"- Dataset SHA-256: `{_markdown_cell(dataset['dataset_hash'], field='dataset_hash')}`",
        f"- Dataset governance SHA-256: `{_markdown_cell(governance['governance_hash'], field='dataset_governance_hash')}`",
        f"- Calendar conformance SHA-256: `{_markdown_cell(calendar_conformance['conformance_hash'], field='calendar_conformance_hash')}`",
        f"- Calendar conformance: `{_markdown_cell(calendar_conformance['status'], field='calendar_conformance_status')}` / `{_markdown_cell(calendar_conformance['provider'], field='calendar_provider')}`",
        f"- Dataset ID: `{_markdown_cell(governance['dataset_id'], field='dataset_id')}`",
        f"- Source: `{_markdown_cell(governance['source']['source_kind'], field='source_kind')}` / `{_markdown_cell(governance['source']['provider_id'], field='provider_id')}`",
        f"- Time contract: `{_markdown_cell(governance['time']['timezone'], field='timezone')}` / `{_markdown_cell(governance['time']['trading_calendar'], field='trading_calendar')}`",
        f"- Adjustment basis: `{_markdown_cell(governance['adjustment']['basis'], field='adjustment_basis')}`",
        f"- Population: `{_markdown_cell(governance['population']['policy'], field='population_policy')}` / survivorship `{_markdown_cell(governance['population']['survivorship_bias_status'], field='survivorship_bias_status')}`",
        f"- Config SHA-256: `{_markdown_cell(source_config['config_hash'], field='config_hash')}`",
        f"- Strategy: `{_markdown_cell(strategy['name'], field='strategy_name')}`",
        f"- Strategy version: `{_markdown_cell(strategy['version'], field='strategy_version')}`",
        f"- Parameter SHA-256: `{_markdown_cell(strategy['params_hash'], field='params_hash')}`",
        f"- Symbol: `{_markdown_cell(source_config['symbol'], field='symbol')}`",
        f"- Market: `{_markdown_cell(source_config['market'], field='market')}`",
        f"- Timeframe: `{_markdown_cell(source_config['timeframe'], field='timeframe')}`",
        f"- Dataset rows: `{dataset['row_count']}`",
        f"- Dataset interval: `{_markdown_cell(dataset['start_time'], field='start_time')}` to `{_markdown_cell(dataset['end_time'], field='end_time')}`",
        "",
        "| Partition | Rows | Start | End |",
        "| --- | ---: | --- | --- |",
    ]
    for window in protocol["partition_plan"]["windows"]:
        lines.append(
            "| "
            + " | ".join([
                _markdown_cell(window["name"], field="partition_name"),
                str(window["row_count"]),
                _markdown_cell(window["start_time"], field="partition_start"),
                _markdown_cell(window["end_time"], field="partition_end"),
            ])
            + " |"
        )
    lines.extend([
        "",
        "## GAP",
        "",
        f"- Quality gate: `{_markdown_cell(quality['status'], field='quality_status')}`",
        "- Structural blockers:",
    ])
    lines.extend(
        f"  - `{_markdown_cell(blocker, field='blocker')}`"
        for blocker in quality["blockers"]
    )
    lines.append("- Standard-report coverage gaps:")
    lines.extend(f"  - `{gap}`" for gap in STANDARD_REPORT_COVERAGE_GAPS)
    lines.extend([
        "",
        "## MATURITY",
        "",
        f"- Evidence scope: `{_markdown_cell(report['evidence_scope'], field='evidence_scope')}`",
        f"- Nested reproducibility checks complete: `{str(quality['nested_experiment_reproducibility_pass']).lower()}`",
        f"- Volatility-matched analytical comparison matrix complete: `{str(quality['volatility_matched_comparison_matrix_complete']).lower()}`",
        f"- Volatility-matched analytical observations complete: `{str(quality['volatility_matched_comparison_observation_complete']).lower()}`",
        f"- Prior-window volatility-target execution baseline complete: `{str(quality['volatility_target_execution_baseline_complete']).lower()}`",
        f"- Registered execution-adversity matrix complete: `{str(quality['execution_adversity_matrix_complete']).lower()}`",
        f"- Target execution-adversity observations complete: `{str(quality['execution_adversity_observation_complete']).lower()}`",
        f"- Fixed liquidity-capacity probe matrix complete: `{str(quality['liquidity_capacity_matrix_complete']).lower()}`",
        f"- Fixed liquidity-capacity partial fill observed: `{str(quality['liquidity_capacity_partial_fill_observed']).lower()}`",
        f"- Paired moving-block Bootstrap matrix complete: `{str(quality['bootstrap_confidence_matrix_complete']).lower()}`",
        f"- Bootstrap observation sufficiency complete: `{str(quality['bootstrap_confidence_observation_complete']).lower()}`",
        f"- Fixed-parameter walk-forward schedule complete: `{str(quality['walk_forward_fixed_schedule_complete']).lower()}`",
        f"- Parameter-stability matrix complete: `{str(quality['parameter_stability_matrix_complete']).lower()}`",
        f"- Frozen statistical-correction matrix complete: `{str(quality['statistical_correction_matrix_complete']).lower()}`",
        f"- DSR and CSCV-PBO estimable: `{str(quality['statistical_correction_estimable']).lower()}`",
        f"- Multiple-testing lineage complete: `{str(quality['multiple_testing_lineage_complete']).lower()}`",
        f"- Fixed trailing market-regime slices complete: `{str(quality['market_regime_slices_complete']).lower()}`",
        f"- Partial tail/distribution analyses complete: `{str(quality['tail_distribution_analyses_complete']).lower()}`",
        f"- Return-contribution concentration matrix complete: `{str(quality['return_contribution_concentration_matrix_complete']).lower()}`",
        "- Volatility-matched comparator tradable: `false`",
        "- Volatility-target benchmark execution scope: `RESEARCH_SIMULATOR_ONLY`",
        "- Frozen Test is blind: `false`",
        "- Frozen Test single consumption proven: `false`",
        "- Natural-forward evidence: `false`",
        f"- Walk-forward unused tail rows: `{protocol['walk_forward']['schedule']['unused_tail_rows']}`",
        "",
        "### Registered strategy observations",
        "",
        "| Role | Cost scenario | Fee rate | Slippage | Total return | Annualized return | Sharpe | Max drawdown | Final equity | Total fees | Trades | Win rate | Ambiguous intrabar |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    lines.extend(
        _markdown_observation_row(record, benchmark=False)
        for record in strategy_runs
    )
    lines.extend([
        "",
        "### Registered execution-adversity observations",
        "",
        "Target-strategy scenarios are synthetic diagnostics only. Observation status states whether target source activity was sufficient. Dynamic market impact, shared intrabar volume budgets, and partial-fill remainder lifecycle remain unmodelled.",
        "",
        "| Role | Scenario | Observation | Total return | Max drawdown | Trades | Return delta | Drawdown delta | Trade delta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    lines.extend(
        "| "
        + " | ".join([
            _markdown_cell(record["role"], field="execution_adversity_role"),
            _markdown_cell(record["scenario_id"], field="execution_adversity_scenario"),
            _markdown_cell(record["observation_status"], field="execution_adversity_observation"),
            f"{float(record['result']['total_return']) * 100:.4f}%",
            f"{float(record['result']['max_drawdown']) * 100:.4f}%",
            str(record["result"]["trades"]),
            f"{float(record['source_result_delta']['total_return_delta']) * 100:.4f}%",
            f"{float(record['source_result_delta']['max_drawdown_delta']) * 100:.4f}%",
            str(record["source_result_delta"]["trade_count_delta"]),
        ])
        + " |"
        for record in execution_adversity_runs
    )
    lines.extend([
        "",
        "### Fixed liquidity-capacity execution probe",
        "",
        "This fixed benchmark probe demonstrates one-shot volume-capped partial fills only. It is not target-strategy robustness evidence, and it does not model remainder lifecycle or a shared intrabar volume budget.",
        "",
        "| Role | Source benchmark | Scenario | Max participation | Fills | Partial fills | Requested quantity | Filled quantity | Minimum fill ratio | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    lines.extend(
        "| "
        + " | ".join([
            _markdown_cell(record["role"], field="liquidity_capacity_role"),
            _markdown_cell(record["source_benchmark_id"], field="liquidity_capacity_source"),
            _markdown_cell(record["scenario_id"], field="liquidity_capacity_scenario"),
            f"{float(record['liquidity_capacity_summary']['max_volume_participation_rate']) * 100:.4f}%",
            str(record["liquidity_capacity_summary"]["fill_count"]),
            str(record["liquidity_capacity_summary"]["partial_fill_count"]),
            f"{float(record['liquidity_capacity_summary']['requested_quantity_total']):.8f}",
            f"{float(record['liquidity_capacity_summary']['filled_quantity_total']):.8f}",
            f"{float(record['liquidity_capacity_summary']['minimum_fill_ratio']):.8f}",
            _markdown_cell(record["liquidity_capacity_summary"]["status"], field="liquidity_capacity_status"),
        ])
        + " |"
        for record in liquidity_capacity_runs
    )
    lines.extend([
        "",
        "### Fixed liquidity-rejection admission probe",
        "",
        "This source-bound research admission probe demonstrates deterministic rejection below a preregistered minimum executable quantity. It does not submit an order, mutate a portfolio, model remainder lifecycle, or authorize paper/live/order execution.",
        "",
        "| Role | Source benchmark | Scenario | Max participation | Minimum quantity | Executable quantity | Decision | Reason |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ])
    lines.extend(
        "| "
        + " | ".join([
            _markdown_cell(record["role"], field="liquidity_rejection_role"),
            _markdown_cell(record["source_benchmark_id"], field="liquidity_rejection_source"),
            _markdown_cell(record["scenario_id"], field="liquidity_rejection_scenario"),
            f"{float(record['decision']['volume_capacity_quantity']) / float(record['decision']['available_volume']) * 100:.8f}%",
            f"{float(record['decision']['minimum_executable_quantity']):.8f}",
            f"{float(record['decision']['executable_quantity']):.12f}",
            _markdown_cell(record["decision"]["status"], field="liquidity_rejection_status"),
            _markdown_cell(record["decision"]["reason"], field="liquidity_rejection_reason"),
        ])
        + " |"
        for record in liquidity_rejection_evidence
    )
    lines.extend([
        "",
        "### Paired moving-block Bootstrap confidence evidence",
        "",
        "The policy is preregistered at 1,000 paired moving-block replicates, but replicates execute only when the minimum paired-observation threshold is met. GAP records contain no confidence intervals and make no formal-inference, profitability, paper, live, or order claim.",
        "",
        "| Role | Benchmark | State | Paired observations | Minimum | Executed replicates | Intervals | Gaps |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ])
    lines.extend(
        "| "
        + " | ".join([
            _markdown_cell(record["role"], field="bootstrap_role"),
            _markdown_cell(record["benchmark_id"], field="bootstrap_benchmark"),
            _markdown_cell(record["evidence"]["evidence_state"], field="bootstrap_state"),
            str(record["evidence"]["sample_summary"]["paired_observation_count"]),
            str(record["evidence"]["policy"]["minimum_observation_count"]),
            str(record["evidence"]["replicate_count"]),
            str(len(record["evidence"]["intervals"])),
            _markdown_cell(
                ", ".join(record["evidence"]["gaps"]) or "NONE",
                field="bootstrap_gaps",
            ),
        ])
        + " |"
        for record in bootstrap_confidence_records
    )
    lines.extend([
        "",
        "### Fixed benchmark observations",
        "",
        "| Role | Benchmark | Cost scenario | Fee rate | Slippage | Total return | Annualized return | Sharpe | Max drawdown | Final equity | Total fees | Trades | Win rate | Ambiguous intrabar |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    lines.extend(
        _markdown_observation_row(record, benchmark=True)
        for record in benchmark_runs
    )
    lines.extend([
        "",
        "### Prior-window volatility-target research-simulator benchmark",
        "",
        "Method: `prior-window-volatility-target-v1`; leverage allowed: `false`; paper/live/order authorization: `false`.",
        "",
        "| Role | Calibration role | Cost scenario | Target ann. volatility | Source ann. volatility | Applied exposure | Exposure capped | Total return | Calibration status |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
    ])
    lines.extend(
        _markdown_volatility_target_row(record)
        for record in volatility_target_runs
    )
    lines.extend([
        "",
        "### Ex-post volatility-matched analytical comparisons",
        "",
        "Method: `ex-post-volatility-match-v2`; zero-target policy: `GAP_NOT_ZERO_FILLED`; interpretation: `ANALYTICAL_ONLY_NOT_TRADABLE`.",
        "",
        "| Role | Cost scenario | Strategy observed ann. volatility | Buy-hold observed ann. volatility | Scale | Matched buy-hold ann. volatility | Matched buy-hold curve return | Strategy minus matched curve return | Status | GAP reason |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ])
    lines.extend(
        _markdown_volatility_comparison_row(record)
        for record in volatility_comparisons
    )
    lines.extend([
        "",
        "### Fixed-parameter walk-forward observations",
        "",
        "Method: `fixed-parameter-walk-forward-v1`; fitting: `NONE_FIXED_PARAMETERS`; nested manifest role: `UNCLASSIFIED`; ranking: `false`.",
        "",
        "| Fold | Cost scenario | Calibration start | Calibration end | Evaluation start | Evaluation end | Total return | Max drawdown | Manifest role | Ranking input |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ])
    lines.extend(
        _markdown_walk_forward_row(record)
        for record in walk_forward_runs
    )
    lines.extend([
        "",
        "#### Walk-forward scenario summary",
        "",
        "| Cost scenario | Folds | Median total return | Minimum total return | Maximum total return | Median max drawdown | Nested reproducibility |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    lines.extend(
        _markdown_walk_forward_summary_row(record)
        for record in report["walk_forward_summary"]["scenario_summaries"]
    )
    stability_cells = protocol["parameter_stability"]["cells"]
    timing_fast_values = sorted({
        cell["params"]["fast_window"]
        for cell in stability_cells
        if cell["segment"] == "TIMING_GRID"
    })
    timing_slow_values = sorted({
        cell["params"]["slow_window"]
        for cell in stability_cells
        if cell["segment"] == "TIMING_GRID"
    })
    stability_lookup = {
        (record["role"], record["cell_id"]): record
        for record in parameter_stability_runs
    }
    lines.extend([
        "",
        "### Parameter-stability observations",
        "",
        "Method: `dual-ma-fixed-perturbation-matrix-v1`; all cells retained: `true`; selected cell: `null`; ranking: `false`.",
    ])
    for role in ("VALIDATION", "FROZEN_TEST"):
        lines.extend([
            "",
            f"#### {role} timing-grid total return",
            "",
            "| Fast \\ Slow | " + " | ".join(str(value) for value in timing_slow_values) + " |",
            "| ---: | " + " | ".join("---:" for _value in timing_slow_values) + " |",
        ])
        for fast in timing_fast_values:
            values: list[str] = []
            for slow in timing_slow_values:
                cell = next(
                    item
                    for item in stability_cells
                    if item["segment"] == "TIMING_GRID"
                    and item["params"]["fast_window"] == fast
                    and item["params"]["slow_window"] == slow
                )
                result = stability_lookup[(role, cell["cell_id"])]["result"]
                values.append(f"{_markdown_metric(result, 'total_return') * 100:.4f}%")
            lines.append(f"| {fast} | " + " | ".join(values) + " |")
    lines.extend([
        "",
        "#### Risk parameter one-at-a-time observations",
        "",
        "| Role | Parameter | Perturbation | Total return | Max drawdown | Ranking input |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ])
    lines.extend(
        _markdown_parameter_stability_risk_row(record)
        for record in parameter_stability_runs
        if record["segment"] == "RISK_OAT"
    )
    lines.extend([
        "",
        "#### Parameter-stability summary",
        "",
        "| Role | Cells | Center return | Median return | Max absolute deviation | Timing grid complete | Risk OAT complete | All non-rankable |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ])
    lines.extend(
        _markdown_parameter_stability_summary_row(record)
        for record in report["parameter_stability_summary"]["role_summaries"]
    )
    lines.extend([
        "",
        "### Frozen statistical-correction evidence",
        "",
        "The two matrices reuse all 21 preregistered BASE parameter-stability cells per role and add zero backtests. DSR and CSCV-PBO remain GAP when their canonical preconditions are not met; no threshold, significance, ranking, or profitability decision is inferred.",
        "",
        "| Role | Trials | Period observations | DSR state | DSR gap | CSCV-PBO state | CSCV-PBO gap | Additional backtests |",
        "| --- | ---: | ---: | --- | --- | --- | --- | ---: |",
    ])
    lines.extend(
        "| "
        + " | ".join([
            _markdown_cell(record["role"], field="statistical_role"),
            str(record["trial_matrix"]["trial_count"]),
            str(record["trial_matrix"]["observation_count"]),
            _markdown_cell(record["deflated_sharpe"]["state"], field="dsr_state"),
            _markdown_cell(record["deflated_sharpe"]["gap_code"] or "NONE", field="dsr_gap"),
            _markdown_cell(record["cscv_pbo"]["state"], field="pbo_state"),
            _markdown_cell(record["cscv_pbo"]["gap_code"] or "NONE", field="pbo_gap"),
            str(record["additional_backtest_run_count"]),
        ])
        + " |"
        for record in statistical_correction_records
    )
    ledger = report["multiple_testing_ledger"]
    lines.extend([
        "",
        "### Multiple-testing lineage ledger",
        "",
        f"- Ledger status: `{_markdown_cell(ledger['ledger_status'], field='ledger_status')}`",
        f"- Trial family: `{_markdown_cell(ledger['family']['family_id'], field='trial_family')}`",
        f"- Trials: `{ledger['family']['trial_count']}`",
        f"- Retained observations: `{ledger['observation_count']}`",
        f"- Synthetic Frozen observations: `{ledger['synthetic_frozen_observation_count']}`",
        "- Formal Frozen consumption count: `UNKNOWN`",
        "- Single consumption proven: `false`",
        "- External preregistration receipt present: `false`",
        "- Selected trial: `null`",
        "- Parameter selection performed: `false`",
        "- Ranking performed: `false`",
        "",
        "| Correction | Status | Value | Blockers |",
        "| --- | --- | --- | --- |",
    ])
    for correction in ledger["corrections"]:
        lines.append(
            "| "
            + " | ".join([
                _markdown_cell(correction["correction_id"], field="correction_id"),
                _markdown_cell(correction["status"], field="correction_status"),
                "UNKNOWN" if correction["value"] is None else str(correction["value"]),
                ", ".join(
                    _markdown_cell(item, field="correction_blocker")
                    for item in correction["blockers"]
                ),
            ])
            + " |"
        )
    lines.extend([
        "",
        "### Fixed trailing market-regime analysis",
        "",
        "Method: `fixed-trailing-market-regime-v1`; scope: `EX_POST_DESCRIPTIVE_NOT_SIGNAL`; classifier inputs: `close`; signal, selection, and ranking: `false`.",
        "",
        "| Role | Regime | Observations | Status | Strategy compounded return | Market compounded return |",
        "| --- | --- | ---: | --- | ---: | ---: |",
    ])
    for analysis in report["market_regime_analysis"]:
        lines.extend(
            _markdown_market_regime_row(analysis, regime_slice)
            for regime_slice in analysis["regime_slices"]
        )
    lines.extend([
        "",
        "### Partial tail and distribution analysis",
        "",
        "Method: `frozen-tail-distribution-policy-v1`; scope: `DESCRIPTIVE_PARTIAL_NOT_INFERENCE_NOT_SIGNAL`; unknown metrics remain `UNKNOWN` with explicit gaps.",
        "",
        "| Role | Cost scenario | State | Returns | Closed trades | Ann. volatility | Sortino | Calmar | Max drawdown | Drawdown duration | Turnover | Exposure | VaR 95 | CVaR 95 | Gaps |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    lines.extend(
        _markdown_tail_distribution_row(analysis)
        for analysis in report["tail_distribution_analysis"]
    )
    lines.extend([
        "",
        "### Return-contribution concentration",
        "",
        "Single-period, calendar-month, and realised SELL-fill concentration reuse the same source-bound distribution evidence. The fixed 21-period window remains GAP when the sample is too short; no separate duplicate diagnostics chain is used.",
        "",
        "| Role | Cost scenario | Top positive period share | Positive period HHI | Return without best period | Top positive month share | Top positive SELL-fill share | Positive SELL-fill HHI | Fixed 21-period window | Gaps |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ])
    for analysis in report["tail_distribution_analysis"]:
        evidence = analysis["distribution_evidence"]
        concentration = evidence["concentration"]
        fixed_window = concentration["best_fixed_21_period_window"]
        lines.append(
            "| "
            + " | ".join([
                _markdown_cell(analysis["role"], field="concentration_role"),
                _markdown_cell(analysis["scenario_id"], field="concentration_scenario"),
                _markdown_cell(concentration["top_positive_period_return_share"] or "UNKNOWN", field="top_period_share"),
                _markdown_cell(concentration["positive_period_return_hhi"] or "UNKNOWN", field="period_hhi"),
                _markdown_cell(concentration["compound_return_without_best_period"] or "UNKNOWN", field="without_best_period"),
                _markdown_cell(concentration["top_positive_month_share"] or "UNKNOWN", field="top_month_share"),
                _markdown_cell(concentration["top_positive_trade_pnl_share"] or "UNKNOWN", field="top_trade_share"),
                _markdown_cell(concentration["positive_trade_pnl_hhi"] or "UNKNOWN", field="trade_hhi"),
                _markdown_cell(fixed_window["state"], field="fixed_window_state"),
                _markdown_cell(", ".join(evidence["gaps"]), field="concentration_gaps"),
            ])
            + " |"
        )
    lines.extend([
        "",
        "## PERMISSION",
        "",
        "| Capability | Allowed |",
        "| --- | --- |",
    ])
    lines.extend(f"| `{name}` | `false` |" for name in AUTHORITY_LOCK)
    lines.extend([
        "",
        "This is descriptive research evidence only. It is not a profitability claim, a formal blind-test result, or permission for paper, live, or order execution.",
        "",
    ])
    return "\n".join(lines)
