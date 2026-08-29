from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import math
from typing import Any

import pandas as pd

from hakimi_research.source_layout import activate_legacy_project_root


activate_legacy_project_root()

from quant_bot.backtest import BacktestEngine  # noqa: E402
from quant_bot.config import BotConfig  # noqa: E402
from quant_bot.experiment_manifest import (  # noqa: E402
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)
from quant_bot.models import Portfolio, Signal  # noqa: E402
from quant_bot.risk import RiskManager  # noqa: E402
from quant_bot.strategies.base import StrategyBase  # noqa: E402
from quant_bot.strategies.templates import build_strategy  # noqa: E402


PROTOCOL_SCHEMA_VERSION = "frozen-evaluation-protocol-v1"
REPORT_SCHEMA_VERSION = "frozen-evaluation-report-v1"
MARKDOWN_REPORT_VERSION = "frozen-evaluation-markdown-v1"
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
BENCHMARKS = (
    ("CASH", "cash-benchmark-v1"),
    ("ENGINE_BUY_AND_HOLD", "engine-buy-and-hold-v1"),
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
    "WALK_FORWARD_NOT_BOUND_TO_ADR0509",
    "PARAMETER_STABILITY_NOT_BOUND_TO_ADR0509",
    "MULTIPLE_TESTING_LINEAGE_NOT_BOUND_TO_ADR0509",
    "MARKET_REGIME_SLICES_NOT_BOUND_TO_ADR0509",
    "TAIL_AND_DISTRIBUTION_METRICS_NOT_AVAILABLE",
)


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


def build_frozen_evaluation_protocol(
    data: pd.DataFrame,
    config: BotConfig,
    *,
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
            "dataset_hash": canonical_payload_hash(dataset_payload),
            "row_count": len(index),
            "start_time": pd.Timestamp(index[0]).isoformat(),
            "end_time": pd.Timestamp(index[-1]).isoformat(),
            "hash_scope": dataset_payload["hash_scope"],
        },
        "config": {
            "config_hash": canonical_payload_hash(config_payload),
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "initial_cash": float(config.initial_cash),
        },
        "strategy": {
            "name": strategy.name,
            "version": strategy.version,
            "params_hash": canonical_payload_hash(config.strategy.params),
        },
        "partition_plan": {
            "order": ["TRAIN", "PURGE", "VALIDATION", "EMBARGO", "FROZEN_TEST"],
            "windows": windows,
            "minimum_evaluation_rows": MIN_EVALUATION_ROWS,
            "minimum_gap_rows": MIN_GAP_ROWS,
        },
        "cost_scenarios": cost_scenarios,
        "benchmarks": [
            {"benchmark_id": benchmark_id, "version": version}
            for benchmark_id, version in BENCHMARKS
        ],
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
        "partition_plan",
        "cost_scenarios",
        "benchmarks",
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


class _CashBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        return Signal.hold("cash benchmark")


class _EngineBuyAndHoldBenchmarkStrategy(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if portfolio.position_qty <= 0:
            return Signal.buy("engine buy-and-hold benchmark", size_pct=1.0)
        return Signal.hold("engine buy-and-hold invested")


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
) -> dict[str, Any]:
    run_config = deepcopy(config)
    run_config.execution.fee_rate = scenario["fee_rate"]
    run_config.execution.slippage_pct = scenario["slippage_pct"]
    context = dict(experiment_context or {})
    context.update({
        "evaluation_role": role,
        "evaluation_protocol_hash": protocol_hash,
        "evaluation_protocol_verified": True,
        "random_seed": random_seed,
    })
    report = BacktestEngine(
        config=run_config,
        strategy=strategy,
        risk_manager=RiskManager(run_config.risk),
        experiment_context=context,
    ).run(data)
    payload = report.to_dict()
    manifest = payload.pop("experiment_manifest")
    if not verify_reproducible_experiment_manifest(manifest, payload):
        raise ValueError("frozen_evaluation_nested_manifest_invalid")
    return {
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


def _strategy_for_config(config: BotConfig) -> StrategyBase:
    return build_strategy(config.strategy.name, config.strategy.params)


def _benchmark_strategy(benchmark_id: str) -> StrategyBase:
    if benchmark_id == "CASH":
        return _CashBenchmarkStrategy(name="cash_benchmark", version="cash-benchmark-v1")
    if benchmark_id == "ENGINE_BUY_AND_HOLD":
        return _EngineBuyAndHoldBenchmarkStrategy(
            name="engine_buy_and_hold_benchmark",
            version="engine-buy-and-hold-v1",
        )
    raise ValueError("frozen_evaluation_benchmark_invalid")


def build_frozen_evaluation_report(
    protocol: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
    *,
    experiment_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verify_frozen_evaluation_protocol(protocol, data, config)
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
            ))

    benchmark_config = deepcopy(config)
    benchmark_config.risk.max_position_pct = 1.0
    benchmark_config.risk.max_single_loss_pct = 1.0
    benchmark_config.risk.max_daily_loss_pct = 1.0
    benchmark_config.risk.max_leverage = 1.0
    benchmark_config.risk.min_cash_pct = 0.0
    benchmark_runs: list[dict[str, Any]] = []
    for role in ("VALIDATION", "FROZEN_TEST"):
        frame = _partition_frame(data, protocol, role)
        for benchmark_id, _version in BENCHMARKS:
            record = _run_record(
                role=role,
                scenario=scenarios["BASE"],
                data=frame,
                config=benchmark_config,
                strategy=_benchmark_strategy(benchmark_id),
                protocol_hash=protocol["protocol_hash"],
                random_seed=random_seed,
                experiment_context=experiment_context,
                run_kind="FIXED_BENCHMARK",
            )
            record["benchmark_id"] = benchmark_id
            benchmark_runs.append(record)

    nested_reproducibility_blocked = any(
        record["experiment_manifest"]["status"] != "PASS"
        for record in [*strategy_runs, *benchmark_runs]
    )
    blockers = list(STRUCTURAL_BLOCKERS)
    if nested_reproducibility_blocked:
        blockers.append("NESTED_EXPERIMENT_REPRODUCIBILITY_BLOCK")
    core = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evidence_scope": EVIDENCE_SCOPE,
        "protocol_id": protocol["protocol_id"],
        "protocol_hash": protocol["protocol_hash"],
        "dataset_hash": protocol["dataset"]["dataset_hash"],
        "strategy": dict(protocol["strategy"]),
        "strategy_runs": strategy_runs,
        "benchmark_runs": benchmark_runs,
        "quality_gate": {
            "status": "BLOCK",
            "blockers": blockers,
            "nested_experiment_reproducibility_pass": not nested_reproducibility_blocked,
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
) -> bool:
    verify_frozen_evaluation_protocol(protocol, data, config)
    _require_native_json(report, path="report")
    if type(report) is not dict:
        raise ValueError("frozen_evaluation_report_type_invalid")
    expected_keys = {
        "schema_version",
        "evidence_scope",
        "protocol_id",
        "protocol_hash",
        "dataset_hash",
        "strategy",
        "strategy_runs",
        "benchmark_runs",
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
            or manifest["evaluation_role"] != record["role"]
            or manifest["evaluation_protocol_hash"] != protocol["protocol_hash"]
            or manifest["evaluation_protocol_verified"] is not True
            or manifest["parameter_selection_allowed"] is not False
            or manifest["paper_authorized"] is not False
            or manifest["live_order_allowed"] is not False
            or manifest["order_entry_allowed"] is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_strategy_run_verification_failed")
    if observed_strategy_runs != expected_strategy_runs:
        raise ValueError("frozen_evaluation_strategy_run_matrix_incomplete")

    expected_benchmark_runs = {
        (role, benchmark_id)
        for role in ("VALIDATION", "FROZEN_TEST")
        for benchmark_id, _version in BENCHMARKS
    }
    observed_benchmark_runs: set[tuple[str, str]] = set()
    benchmark_versions = dict(BENCHMARKS)
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
        }
        if type(record) is not dict or set(record) != required:
            raise ValueError("frozen_evaluation_benchmark_run_shape_invalid")
        identity = (record["role"], record["benchmark_id"])
        if identity in observed_benchmark_runs or identity not in expected_benchmark_runs:
            raise ValueError("frozen_evaluation_benchmark_run_identity_invalid")
        observed_benchmark_runs.add(identity)
        manifest = record["experiment_manifest"]
        if (
            record["run_kind"] != "FIXED_BENCHMARK"
            or record["scenario_id"] != "BASE"
            or record["strategy_version"] != benchmark_versions[record["benchmark_id"]]
            or manifest["evaluation_role"] != record["role"]
            or manifest["evaluation_protocol_hash"] != protocol["protocol_hash"]
            or manifest["evaluation_protocol_verified"] is not True
            or manifest["parameter_selection_allowed"] is not False
            or manifest["paper_authorized"] is not False
            or manifest["live_order_allowed"] is not False
            or manifest["order_entry_allowed"] is not False
            or not verify_reproducible_experiment_manifest(manifest, record["result"])
        ):
            raise ValueError("frozen_evaluation_benchmark_run_verification_failed")
    if observed_benchmark_runs != expected_benchmark_runs:
        raise ValueError("frozen_evaluation_benchmark_run_matrix_incomplete")

    nested_blocked = any(
        record["experiment_manifest"]["status"] != "PASS"
        for record in [*report["strategy_runs"], *report["benchmark_runs"]]
    )
    expected_blockers = list(STRUCTURAL_BLOCKERS)
    if nested_blocked:
        expected_blockers.append("NESTED_EXPERIMENT_REPRODUCIBILITY_BLOCK")
    expected_quality_gate = {
        "status": "BLOCK",
        "blockers": expected_blockers,
        "nested_experiment_reproducibility_pass": not nested_blocked,
        "frozen_test_is_blind": False,
        "frozen_test_single_consumption_proven": False,
        "natural_forward_evidence": False,
    }
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
    identity = (
        _markdown_cell(record["benchmark_id"], field="benchmark_id")
        if benchmark
        else _markdown_cell(record["scenario_id"], field="scenario_id")
    )
    role = _markdown_cell(record["role"], field="role")
    return " | ".join([
        "",
        role,
        identity,
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


def render_frozen_evaluation_markdown(
    report: dict[str, Any],
    protocol: dict[str, Any],
    data: pd.DataFrame,
    config: BotConfig,
) -> str:
    """Render verified ADR0509 evidence without writing or granting authority."""

    verify_frozen_evaluation_report(report, protocol, data, config)
    role_order = {"TRAIN": 0, "VALIDATION": 1, "FROZEN_TEST": 2}
    scenario_order = {"BASE": 0, "DOUBLE_COST": 1, "TRIPLE_COST": 2}
    benchmark_order = {"CASH": 0, "ENGINE_BUY_AND_HOLD": 1}
    strategy_runs = sorted(
        report["strategy_runs"],
        key=lambda item: (
            role_order[item["role"]],
            scenario_order[item["scenario_id"]],
        ),
    )
    benchmark_runs = sorted(
        report["benchmark_runs"],
        key=lambda item: (
            role_order[item["role"]],
            benchmark_order[item["benchmark_id"]],
        ),
    )
    dataset = protocol["dataset"]
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
        f"- Config SHA-256: `{_markdown_cell(source_config['config_hash'], field='config_hash')}`",
        f"- Strategy: `{_markdown_cell(strategy['name'], field='strategy_name')}`",
        f"- Strategy version: `{_markdown_cell(strategy['version'], field='strategy_version')}`",
        f"- Parameter SHA-256: `{_markdown_cell(strategy['params_hash'], field='params_hash')}`",
        f"- Symbol: `{_markdown_cell(source_config['symbol'], field='symbol')}`",
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
        "- Frozen Test is blind: `false`",
        "- Frozen Test single consumption proven: `false`",
        "- Natural-forward evidence: `false`",
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
        "### Fixed benchmark observations",
        "",
        "| Role | Benchmark | Fee rate | Slippage | Total return | Annualized return | Sharpe | Max drawdown | Final equity | Total fees | Trades | Win rate | Ambiguous intrabar |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    lines.extend(
        _markdown_observation_row(record, benchmark=True)
        for record in benchmark_runs
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
