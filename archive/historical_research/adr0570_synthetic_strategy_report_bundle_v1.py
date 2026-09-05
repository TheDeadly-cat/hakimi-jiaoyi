from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
import hashlib
import json
import math
from typing import Any, Callable

import pandas as pd

from exchange_terminal.application.strategy_family_inventory_adapter_v1 import (
    build_current_strategy_family_inventory,
)
from hakimi_research.distribution_evidence import (
    build_distribution_evidence,
    verify_distribution_evidence,
)
from hakimi_research.strategy_family_inventory import verify_strategy_family_inventory
from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig
from hakimi_research.models import Action
from hakimi_research.risk import RiskManager
from hakimi_research.strategies import STRATEGY_REGISTRY, build_strategy
from hakimi_research.strategies.base import Portfolio, Signal, StrategyBase


SCHEMA_VERSION = "synthetic-strategy-report-bundle-v1"
REPORT_SCHEMA_VERSION = "synthetic-strategy-baseline-report-v1"
PLAN_SCHEMA_VERSION = "synthetic-strategy-report-plan-v1"
FIXTURE_ID = "deterministic-composite-stock-daily-v1"
PERIODS_PER_YEAR = 252
BASE_FEE_RATE = 0.0005
BASE_SLIPPAGE_PCT = 0.0002
STRESS_MULTIPLIERS = (1, 2, 3)

_STRATEGY_IDS = ("bollinger", "dual_ma", "grid", "macd", "momentum", "rsi")
_FAMILY_MEMBERS = {
    "RANGE": ("bollinger", "grid", "rsi"),
    "TREND": ("dual_ma", "macd", "momentum"),
    "ENSEMBLE": (),
}
_AUTHORITY = {
    "profitability_proven": False,
    "blind_test_complete": False,
    "paper_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
}
_MANDATORY_GAPS = (
    "REAL_MARKET_DATA_NOT_USED",
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "WALK_FORWARD_NOT_EXECUTED",
    "PARAMETER_STABILITY_NOT_EXECUTED",
    "MULTIPLE_TESTING_NOT_EXECUTED",
    "ENSEMBLE_STRATEGY_NOT_IMPLEMENTED",
    "DEPENDENCY_LOCK_NOT_BOUND",
    "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE",
)
_REPORT_GAPS = (
    "SYNTHETIC_DATA_ONLY",
    "WALK_FORWARD_NOT_EXECUTED",
    "PARAMETER_STABILITY_NOT_EXECUTED",
    "MULTIPLE_TESTING_NOT_EXECUTED",
)
_RESULT_KEYS = {
    "total_return",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "sharpe_ratio",
    "trades",
    "final_equity",
    "equity_curve",
    "fills",
    "total_fees",
    "ambiguous_intrabar_count",
    "execution_model",
    "reproducibility",
    "experiment_manifest",
}


class SyntheticStrategyReportBundleError(ValueError):
    pass


class _CashBenchmark(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        del data, portfolio
        return Signal(action=Action.HOLD, reason="cash benchmark")


class _BuyAndHoldBenchmark(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        if len(data) == 30 and portfolio.position_qty <= 0:
            return Signal(
                action=Action.BUY,
                confidence=1.0,
                size_pct=0.35,
                reason="preregistered synthetic buy-and-hold entry",
            )
        return Signal(action=Action.HOLD, reason="buy-and-hold benchmark")


def _require_native(value: Any, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (bool, int, str):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise SyntheticStrategyReportBundleError(f"{path} must be finite")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_native(item, f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise SyntheticStrategyReportBundleError(f"{path} keys must be exact str")
            _require_native(item, f"{path}.{key}")
        return
    raise SyntheticStrategyReportBundleError(
        f"{path} must contain exact native JSON values, got {value_type.__name__}"
    )


def canonical_sha256(value: Any) -> str:
    _require_native(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _to_native(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_native(asdict(value))
    if isinstance(value, Enum):
        return _to_native(value.value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if type(value) is dict:
        return {str(key): _to_native(item) for key, item in value.items()}
    if type(value) in (list, tuple):
        return [_to_native(item) for item in value]
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise SyntheticStrategyReportBundleError("backtest emitted non-finite float")
        return value
    if hasattr(value, "item"):
        return _to_native(value.item())
    raise SyntheticStrategyReportBundleError(
        f"cannot canonicalize producer value of type {type(value).__name__}"
    )


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        raise SyntheticStrategyReportBundleError(f"duplicate seal field: {field}")
    record[field] = canonical_sha256(record)
    return record


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        raise SyntheticStrategyReportBundleError(f"{path}.{field} is invalid")
    payload = {key: value for key, value in record.items() if key != field}
    if canonical_sha256(payload) != digest:
        raise SyntheticStrategyReportBundleError(f"{path}.{field} mismatch")


def _expect_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise SyntheticStrategyReportBundleError(f"{path} keys mismatch")


def _authority() -> dict[str, bool]:
    return deepcopy(_AUTHORITY)


def _family_for_strategy(strategy_id: str) -> str:
    for family_id in ("RANGE", "TREND"):
        if strategy_id in _FAMILY_MEMBERS[family_id]:
            return family_id
    raise SyntheticStrategyReportBundleError(f"unmapped strategy: {strategy_id}")


def _planned_runs() -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for strategy_id in _STRATEGY_IDS:
        family_id = _family_for_strategy(strategy_id)
        for role, multiplier in (
            ("TRAIN_BASELINE", 1),
            ("VALIDATION_BASELINE", 1),
            ("FROZEN_COST_1X", 1),
            ("FROZEN_COST_2X", 2),
            ("FROZEN_COST_3X", 3),
        ):
            runs.append(
                {
                    "run_id": f"{strategy_id}:{role.lower()}",
                    "subject_type": "REGISTERED_STRATEGY",
                    "subject_id": strategy_id,
                    "family_id": family_id,
                    "evaluation_role": role,
                    "cost_multiplier": multiplier,
                }
            )
    for benchmark_id in ("cash", "buy_and_hold"):
        runs.append(
            {
                "run_id": f"benchmark:{benchmark_id}:frozen_cost_1x",
                "subject_type": "BENCHMARK",
                "subject_id": benchmark_id,
                "family_id": "BENCHMARK",
                "evaluation_role": "FROZEN_COST_1X",
                "cost_multiplier": 1,
            }
        )
    return runs


def plan_synthetic_strategy_report_bundle_v1() -> dict[str, Any]:
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "registered_strategy_ids": list(_STRATEGY_IDS),
        "family_members": {
            key: list(value) for key, value in _FAMILY_MEMBERS.items()
        },
        "planned_runs": _planned_runs(),
        "planned_run_count": 32,
        "executed_run_count": 0,
        "runtime_mutations": False,
        "requires_exact_execute_true": True,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "selection_policy": {
            "parameter_search": "NOT_EXECUTED",
            "parameters": "REGISTERED_STRATEGY_DEFAULTS",
            "frozen_selection_count": 0,
            "frozen_evaluation_batch_count": 1,
            "post_frozen_parameter_changes_allowed": False,
        },
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def _close_at(index: int) -> float:
    if index < 200:
        value = 100.0 + 2.8 * math.sin(index / 6.0) + 1.1 * math.sin(index / 17.0)
    elif index < 210:
        value = 101.0 + 0.08 * (index - 200) + 0.7 * math.sin(index / 3.0)
    elif index < 390:
        offset = index - 210
        value = 101.5 + 0.11 * offset + 2.0 * math.sin(offset / 8.0)
    elif index < 400:
        value = 121.0 - 0.12 * (index - 390) + 0.8 * math.sin(index / 2.0)
    else:
        offset = index - 400
        if offset < 70:
            value = 120.0 + 0.16 * offset + 3.2 * math.sin(offset / 5.0)
        elif offset < 135:
            value = 131.0 - 0.19 * (offset - 70) + 3.8 * math.sin(offset / 4.0)
        else:
            value = 119.0 + 4.3 * math.sin(offset / 5.5) + 1.4 * math.sin(offset / 2.3)
    return round(value, 10)


def _build_frame() -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=600, freq="D", tz="UTC", name="time")
    rows: list[dict[str, float]] = []
    previous_close = _close_at(0)
    for offset in range(600):
        close = _close_at(offset)
        open_price = round(previous_close + 0.18 * math.sin(offset / 3.0), 10)
        spread = 0.55 + 0.12 * abs(math.sin(offset / 4.0))
        high = round(max(open_price, close) + spread, 10)
        low = round(min(open_price, close) - spread * 1.05, 10)
        volume = round(1000.0 + (offset % 37) * 13.0 + 90.0 * abs(math.sin(offset / 9.0)), 10)
        rows.append(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
        previous_close = close
    return pd.DataFrame(rows, index=index)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for timestamp, row in frame.iterrows():
        output.append(
            {
                "time": pd.Timestamp(timestamp).isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )
    return output


def _build_fixture() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    frame = _build_frame()
    frames = {
        "train": frame.iloc[0:200].copy(deep=True),
        "purge": frame.iloc[200:210].copy(deep=True),
        "validation": frame.iloc[210:390].copy(deep=True),
        "embargo": frame.iloc[390:400].copy(deep=True),
        "frozen": frame.iloc[400:600].copy(deep=True),
    }
    partitions: dict[str, Any] = {}
    for partition_id, partition_frame in frames.items():
        partition_records = _records(partition_frame)
        partitions[partition_id] = {
            "partition_id": partition_id.upper(),
            "start_time": partition_records[0]["time"],
            "end_time": partition_records[-1]["time"],
            "row_count": len(partition_records),
            "dataset_sha256": canonical_sha256(partition_records),
        }
    full_records = _records(frame)
    fixture = {
        "fixture_id": FIXTURE_ID,
        "source": "PURE_SYNTHETIC_IN_MEMORY",
        "market": "stock",
        "symbol": "SYNTH",
        "timeframe": "1d",
        "periods_per_year": PERIODS_PER_YEAR,
        "randomness": "NONE",
        "row_count": len(full_records),
        "records": full_records,
        "dataset_sha256": canonical_sha256(full_records),
        "partition_protocol": {
            "train_slice": [0, 200],
            "purge_slice": [200, 210],
            "validation_slice": [210, 390],
            "embargo_slice": [390, 400],
            "frozen_slice": [400, 600],
            "purge_rows": 10,
            "embargo_rows": 10,
            "partitions": partitions,
        },
    }
    fixture["partition_protocol"]["protocol_sha256"] = canonical_sha256(
        fixture["partition_protocol"]
    )
    return frames, _seal(fixture, "fixture_sha256")


def _cost_contract() -> dict[str, Any]:
    contract = {
        "schema_version": "synthetic-cost-stress-v1",
        "base_fee_rate": BASE_FEE_RATE,
        "base_slippage_pct": BASE_SLIPPAGE_PCT,
        "stress_multipliers": list(STRESS_MULTIPLIERS),
        "stress_rule": "MULTIPLY_FEE_AND_SLIPPAGE_TOGETHER",
    }
    return _seal(contract, "cost_contract_sha256")


def _strategy_identity(strategy_id: str) -> dict[str, Any]:
    strategy = build_strategy(strategy_id)
    strategy_type = type(strategy)
    identity = {
        "strategy_id": strategy_id,
        "module": strategy_type.__module__,
        "qualname": strategy_type.__qualname__,
        "declared_version": str(strategy.version),
        "default_parameters": _to_native(strategy.params),
    }
    return _seal(identity, "identity_sha256")


def _new_config(fee_rate: float, slippage_pct: float) -> BotConfig:
    config = BotConfig(
        name="hakimi-pure-synthetic-report",
        mode="backtest",
        market="stock",
        symbol="SYNTH",
        timeframe="1d",
        initial_cash=10000.0,
    )
    config.data.provider = "synthetic"
    config.data.csv_path = ""
    config.data.use_cache = False
    config.execution.fee_rate = fee_rate
    config.execution.slippage_pct = slippage_pct
    config.execution.live_trading_enabled = False
    return config


def _run_backtest(
    *,
    run_id: str,
    evaluation_role: str,
    frame: pd.DataFrame,
    dataset_sha256: str,
    cost_multiplier: int,
    strategy_factory: Callable[[], StrategyBase],
    protocol_sha256: str,
) -> dict[str, Any]:
    fee_rate = BASE_FEE_RATE * cost_multiplier
    slippage_pct = BASE_SLIPPAGE_PCT * cost_multiplier
    config = _new_config(fee_rate, slippage_pct)
    context = {
        "evaluation_role": evaluation_role,
        "evaluation_protocol_hash": protocol_sha256,
        "evaluation_protocol_verified": False,
        "git_commit_sha": "",
        "git_worktree_clean": False,
        "dependency_lock_name": "",
        "dependency_lock_hash": "",
        "dependency_lock_fully_pinned": False,
    }
    report = BacktestEngine(
        config,
        strategy_factory(),
        RiskManager(config.risk),
        experiment_context=context,
    ).run(frame.copy(deep=True))
    result = _to_native(asdict(report))
    if set(result) != _RESULT_KEYS:
        raise SyntheticStrategyReportBundleError("BacktestReport shape drifted")
    run = {
        "run_id": run_id,
        "evaluation_role": evaluation_role,
        "dataset_sha256": dataset_sha256,
        "cost_multiplier": cost_multiplier,
        "fee_rate": fee_rate,
        "slippage_pct": slippage_pct,
        "result": result,
        "result_sha256": canonical_sha256(result),
    }
    return _seal(run, "run_sha256")


def _distribution_binding(strategy_id: str, frozen_run: dict[str, Any]) -> dict[str, Any]:
    source_report = {
        "schema_version": "synthetic-distribution-source-v1",
        "fixture_id": FIXTURE_ID,
        "strategy_id": strategy_id,
        "evaluation_role": "FROZEN_COST_1X",
        "result": deepcopy(frozen_run["result"]),
    }
    evidence = build_distribution_evidence(
        source_report,
        source_result_path=["result"],
        periods_per_year=PERIODS_PER_YEAR,
    )
    binding = {
        "source_report": source_report,
        "source_report_sha256": canonical_sha256(source_report),
        "evidence": evidence,
    }
    return _seal(binding, "binding_sha256")


def _build_strategy_report(
    strategy_id: str,
    frames: dict[str, pd.DataFrame],
    fixture: dict[str, Any],
) -> dict[str, Any]:
    partitions = fixture["partition_protocol"]["partitions"]
    protocol_sha256 = fixture["partition_protocol"]["protocol_sha256"]
    run_specs = (
        ("train", "TRAIN_BASELINE", 1),
        ("validation", "VALIDATION_BASELINE", 1),
        ("frozen_1x", "FROZEN_COST_1X", 1),
        ("frozen_2x", "FROZEN_COST_2X", 2),
        ("frozen_3x", "FROZEN_COST_3X", 3),
    )
    runs: dict[str, Any] = {}
    for run_key, role, multiplier in run_specs:
        partition_id = "frozen" if run_key.startswith("frozen") else run_key
        runs[run_key] = _run_backtest(
            run_id=f"{strategy_id}:{role.lower()}",
            evaluation_role=role,
            frame=frames[partition_id],
            dataset_sha256=partitions[partition_id]["dataset_sha256"],
            cost_multiplier=multiplier,
            strategy_factory=lambda strategy_id=strategy_id: build_strategy(strategy_id),
            protocol_sha256=protocol_sha256,
        )
    distribution = _distribution_binding(strategy_id, runs["frozen_1x"])
    distribution_gaps = distribution["evidence"].get("gaps", [])
    if type(distribution_gaps) is not list:
        distribution_gaps = []
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": _family_for_strategy(strategy_id),
        "implementation_identity": _strategy_identity(strategy_id),
        "selection_policy": {
            "parameter_search": "NOT_EXECUTED",
            "parameters": "REGISTERED_STRATEGY_DEFAULTS",
            "frozen_used_for_selection": False,
            "post_frozen_parameter_changes_allowed": False,
        },
        "runs": runs,
        "frozen_distribution": distribution,
        "gaps": list(_REPORT_GAPS) + [str(item) for item in distribution_gaps],
        "status": "PARTIAL",
        "observation_class": "SYNTHETIC_OBSERVATION_ONLY",
        "authority": _authority(),
    }
    return _seal(report, "report_sha256")


def _build_benchmarks(
    frames: dict[str, pd.DataFrame], fixture: dict[str, Any]
) -> dict[str, Any]:
    frozen_hash = fixture["partition_protocol"]["partitions"]["frozen"]["dataset_sha256"]
    protocol_hash = fixture["partition_protocol"]["protocol_sha256"]
    factories: dict[str, Callable[[], StrategyBase]] = {
        "cash": lambda: _CashBenchmark(name="cash", version="v1"),
        "buy_and_hold": lambda: _BuyAndHoldBenchmark(name="buy_and_hold", version="v1"),
    }
    benchmarks: dict[str, Any] = {}
    for benchmark_id, factory in factories.items():
        benchmarks[benchmark_id] = _run_backtest(
            run_id=f"benchmark:{benchmark_id}:frozen_cost_1x",
            evaluation_role="FROZEN_COST_1X",
            frame=frames["frozen"],
            dataset_sha256=frozen_hash,
            cost_multiplier=1,
            strategy_factory=factory,
            protocol_sha256=protocol_hash,
        )
    return benchmarks


def _family_summary() -> list[dict[str, Any]]:
    return [
        {
            "family_id": "RANGE",
            "strategy_ids": list(_FAMILY_MEMBERS["RANGE"]),
            "report_count": 3,
            "status": "PARTIAL",
            "gap_code": None,
        },
        {
            "family_id": "TREND",
            "strategy_ids": list(_FAMILY_MEMBERS["TREND"]),
            "report_count": 3,
            "status": "PARTIAL",
            "gap_code": None,
        },
        {
            "family_id": "ENSEMBLE",
            "strategy_ids": [],
            "report_count": 0,
            "status": "GAP",
            "gap_code": "ENSEMBLE_STRATEGY_NOT_IMPLEMENTED",
        },
    ]


def build_synthetic_strategy_report_bundle_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyReportBundleError(
            "execution requires exact execute=True; inspect the plan first"
        )
    plan = plan_synthetic_strategy_report_bundle_v1()
    frames, fixture = _build_fixture()
    inventory = build_current_strategy_family_inventory()
    if inventory["registered_strategy_ids"] != list(_STRATEGY_IDS):
        raise SyntheticStrategyReportBundleError("strategy registry drifted from preregistration")
    reports = [
        _build_strategy_report(strategy_id, frames, fixture)
        for strategy_id in _STRATEGY_IDS
    ]
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "plan": plan,
        "fixture": fixture,
        "cost_contract": _cost_contract(),
        "strategy_inventory": inventory,
        "benchmarks": _build_benchmarks(frames, fixture),
        "strategy_reports": reports,
        "family_summary": _family_summary(),
        "executed_run_count": 32,
        "runtime_mutations": False,
        "gaps": list(_MANDATORY_GAPS),
        "status": "BLOCK",
        "maturity": "SYNTHETIC_BASELINE_ONLY",
        "authority": _authority(),
    }
    return _seal(bundle, "bundle_sha256")


def _verify_run(
    run: dict[str, Any],
    *,
    expected_run_id: str,
    expected_role: str,
    expected_dataset_sha256: str,
    expected_multiplier: int,
    path: str,
) -> None:
    _expect_keys(
        run,
        {
            "run_id",
            "evaluation_role",
            "dataset_sha256",
            "cost_multiplier",
            "fee_rate",
            "slippage_pct",
            "result",
            "result_sha256",
            "run_sha256",
        },
        path,
    )
    if run["run_id"] != expected_run_id or run["evaluation_role"] != expected_role:
        raise SyntheticStrategyReportBundleError(f"{path} identity mismatch")
    if run["dataset_sha256"] != expected_dataset_sha256:
        raise SyntheticStrategyReportBundleError(f"{path} dataset mismatch")
    if type(run["cost_multiplier"]) is not int or run["cost_multiplier"] != expected_multiplier:
        raise SyntheticStrategyReportBundleError(f"{path} cost multiplier mismatch")
    if run["fee_rate"] != BASE_FEE_RATE * expected_multiplier:
        raise SyntheticStrategyReportBundleError(f"{path} fee mismatch")
    if run["slippage_pct"] != BASE_SLIPPAGE_PCT * expected_multiplier:
        raise SyntheticStrategyReportBundleError(f"{path} slippage mismatch")
    if type(run["result"]) is not dict or set(run["result"]) != _RESULT_KEYS:
        raise SyntheticStrategyReportBundleError(f"{path} result shape mismatch")
    if canonical_sha256(run["result"]) != run["result_sha256"]:
        raise SyntheticStrategyReportBundleError(f"{path} result digest mismatch")
    manifest = run["result"]["experiment_manifest"]
    if type(manifest) is not dict:
        raise SyntheticStrategyReportBundleError(f"{path} manifest missing")
    if manifest.get("research_only") is not True:
        raise SyntheticStrategyReportBundleError(f"{path} research lock missing")
    for field in ("live_order_allowed", "order_entry_allowed", "paper_authorized"):
        if manifest.get(field) is not False:
            raise SyntheticStrategyReportBundleError(f"{path} authority escalation")
    if manifest.get("result_is_profitability_proof") is not False:
        raise SyntheticStrategyReportBundleError(f"{path} profitability escalation")
    _verify_seal(run, "run_sha256", path)


def _verify_bundle(bundle: dict[str, Any]) -> None:
    _require_native(bundle)
    _expect_keys(
        bundle,
        {
            "schema_version",
            "plan",
            "fixture",
            "cost_contract",
            "strategy_inventory",
            "benchmarks",
            "strategy_reports",
            "family_summary",
            "executed_run_count",
            "runtime_mutations",
            "gaps",
            "status",
            "maturity",
            "authority",
            "bundle_sha256",
        },
        "$",
    )
    if bundle["schema_version"] != SCHEMA_VERSION:
        raise SyntheticStrategyReportBundleError("schema version mismatch")
    if bundle["plan"] != plan_synthetic_strategy_report_bundle_v1():
        raise SyntheticStrategyReportBundleError("plan mismatch")
    _, expected_fixture = _build_fixture()
    if bundle["fixture"] != expected_fixture:
        raise SyntheticStrategyReportBundleError("fixture mismatch")
    if bundle["cost_contract"] != _cost_contract():
        raise SyntheticStrategyReportBundleError("cost contract mismatch")
    inventory_receipt = verify_strategy_family_inventory(bundle["strategy_inventory"])
    if inventory_receipt.get("status") != "GAP":
        raise SyntheticStrategyReportBundleError("strategy inventory status drifted")
    if bundle["strategy_inventory"] != build_current_strategy_family_inventory():
        raise SyntheticStrategyReportBundleError("current strategy registry mismatch")
    if bundle["executed_run_count"] != 32 or type(bundle["executed_run_count"]) is not int:
        raise SyntheticStrategyReportBundleError("executed run count mismatch")
    if bundle["runtime_mutations"] is not False:
        raise SyntheticStrategyReportBundleError("runtime mutation claim escalated")
    if bundle["authority"] != _AUTHORITY:
        raise SyntheticStrategyReportBundleError("bundle authority mismatch")
    if bundle["status"] != "BLOCK" or bundle["maturity"] != "SYNTHETIC_BASELINE_ONLY":
        raise SyntheticStrategyReportBundleError("maturity mismatch")
    if bundle["gaps"] != list(_MANDATORY_GAPS):
        raise SyntheticStrategyReportBundleError("bundle gaps mismatch")
    if bundle["family_summary"] != _family_summary():
        raise SyntheticStrategyReportBundleError("family summary mismatch")

    partitions = bundle["fixture"]["partition_protocol"]["partitions"]
    reports = bundle["strategy_reports"]
    if type(reports) is not list or [item.get("strategy_id") for item in reports] != list(_STRATEGY_IDS):
        raise SyntheticStrategyReportBundleError("strategy report membership mismatch")
    expected_run_specs = {
        "train": ("TRAIN_BASELINE", "train", 1),
        "validation": ("VALIDATION_BASELINE", "validation", 1),
        "frozen_1x": ("FROZEN_COST_1X", "frozen", 1),
        "frozen_2x": ("FROZEN_COST_2X", "frozen", 2),
        "frozen_3x": ("FROZEN_COST_3X", "frozen", 3),
    }
    for report in reports:
        _expect_keys(
            report,
            {
                "schema_version",
                "strategy_id",
                "family_id",
                "implementation_identity",
                "selection_policy",
                "runs",
                "frozen_distribution",
                "gaps",
                "status",
                "observation_class",
                "authority",
                "report_sha256",
            },
            "$.strategy_reports[]",
        )
        strategy_id = report["strategy_id"]
        if report["schema_version"] != REPORT_SCHEMA_VERSION:
            raise SyntheticStrategyReportBundleError("strategy report schema mismatch")
        if report["family_id"] != _family_for_strategy(strategy_id):
            raise SyntheticStrategyReportBundleError("strategy family mismatch")
        if report["implementation_identity"] != _strategy_identity(strategy_id):
            raise SyntheticStrategyReportBundleError("strategy identity mismatch")
        if report["selection_policy"] != {
            "parameter_search": "NOT_EXECUTED",
            "parameters": "REGISTERED_STRATEGY_DEFAULTS",
            "frozen_used_for_selection": False,
            "post_frozen_parameter_changes_allowed": False,
        }:
            raise SyntheticStrategyReportBundleError("selection policy mismatch")
        if set(report["runs"]) != set(expected_run_specs):
            raise SyntheticStrategyReportBundleError("strategy run set mismatch")
        for run_key, (role, partition_id, multiplier) in expected_run_specs.items():
            _verify_run(
                report["runs"][run_key],
                expected_run_id=f"{strategy_id}:{role.lower()}",
                expected_role=role,
                expected_dataset_sha256=partitions[partition_id]["dataset_sha256"],
                expected_multiplier=multiplier,
                path=f"$.strategy_reports[{strategy_id}].runs.{run_key}",
            )
        binding = report["frozen_distribution"]
        _expect_keys(
            binding,
            {"source_report", "source_report_sha256", "evidence", "binding_sha256"},
            "$.strategy_reports[].frozen_distribution",
        )
        expected_source = {
            "schema_version": "synthetic-distribution-source-v1",
            "fixture_id": FIXTURE_ID,
            "strategy_id": strategy_id,
            "evaluation_role": "FROZEN_COST_1X",
            "result": report["runs"]["frozen_1x"]["result"],
        }
        if binding["source_report"] != expected_source:
            raise SyntheticStrategyReportBundleError("distribution source mismatch")
        if binding["source_report_sha256"] != canonical_sha256(expected_source):
            raise SyntheticStrategyReportBundleError("distribution source digest mismatch")
        distribution_receipt = verify_distribution_evidence(
            binding["evidence"], binding["source_report"]
        )
        distribution_state = distribution_receipt.get("state")
        if (
            distribution_state not in {"OBSERVED", "PARTIAL"}
            or distribution_state != binding["evidence"].get("status")
        ):
            raise SyntheticStrategyReportBundleError("distribution evidence did not verify")
        _verify_seal(binding, "binding_sha256", "$.strategy_reports[].frozen_distribution")
        if report["status"] != "PARTIAL" or report["observation_class"] != "SYNTHETIC_OBSERVATION_ONLY":
            raise SyntheticStrategyReportBundleError("strategy report maturity mismatch")
        if report["authority"] != _AUTHORITY:
            raise SyntheticStrategyReportBundleError("strategy report authority mismatch")
        for gap in _REPORT_GAPS:
            if gap not in report["gaps"]:
                raise SyntheticStrategyReportBundleError(f"missing report gap: {gap}")
        _verify_seal(report, "report_sha256", "$.strategy_reports[]")

    benchmarks = bundle["benchmarks"]
    if type(benchmarks) is not dict or set(benchmarks) != {"cash", "buy_and_hold"}:
        raise SyntheticStrategyReportBundleError("benchmark set mismatch")
    frozen_hash = partitions["frozen"]["dataset_sha256"]
    for benchmark_id, run in benchmarks.items():
        _verify_run(
            run,
            expected_run_id=f"benchmark:{benchmark_id}:frozen_cost_1x",
            expected_role="FROZEN_COST_1X",
            expected_dataset_sha256=frozen_hash,
            expected_multiplier=1,
            path=f"$.benchmarks.{benchmark_id}",
        )
    _verify_seal(bundle, "bundle_sha256", "$")


def verify_synthetic_strategy_report_bundle_v1(bundle: dict[str, Any]) -> dict[str, Any]:
    try:
        _verify_bundle(bundle)
    except Exception as exc:
        return {
            "status": "BLOCK",
            "blockers": [f"BUNDLE_VERIFICATION_FAILED:{type(exc).__name__}:{exc}"],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "verified_run_count": 32,
        "replay_status": "NOT_EXECUTED",
        "authority": _authority(),
    }


def replay_synthetic_strategy_report_bundle_v1(bundle: dict[str, Any]) -> dict[str, Any]:
    structural = verify_synthetic_strategy_report_bundle_v1(bundle)
    if structural["status"] != "PASS":
        return structural
    replayed = build_synthetic_strategy_report_bundle_v1(execute=True)
    if replayed["bundle_sha256"] != bundle["bundle_sha256"] or replayed != bundle:
        return {
            "status": "BLOCK",
            "blockers": ["DETERMINISTIC_REPLAY_MISMATCH"],
            "expected_bundle_sha256": bundle["bundle_sha256"],
            "actual_bundle_sha256": replayed["bundle_sha256"],
            "authority": _authority(),
        }
    return {
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "replay_status": "EXACT_MATCH",
        "replayed_run_count": 32,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def _percent(value: Any) -> str:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        return "GAP"
    return f"{float(value) * 100.0:.4f}%"


def render_synthetic_strategy_report_bundle_markdown_v1(bundle: dict[str, Any]) -> str:
    receipt = verify_synthetic_strategy_report_bundle_v1(bundle)
    if receipt["status"] != "PASS":
        raise SyntheticStrategyReportBundleError("refusing to render unverified bundle")
    lines = [
        "# Pure Synthetic Strategy Baseline",
        "",
        "> Every number below is SYNTHETIC_OBSERVATION_ONLY. It is not evidence of real-market performance or permission to trade.",
        "",
        "## SOURCE",
        "",
        f"- Fixture: `{bundle['fixture']['fixture_id']}`",
        f"- Dataset SHA-256: `{bundle['fixture']['dataset_sha256']}`",
        f"- Bundle SHA-256: `{bundle['bundle_sha256']}`",
        "- Data source: pure deterministic in-memory OHLCV; no network, cache, database, or runtime artifact.",
        "- Protocol: Train 200 rows -> Purge 10 -> Validation 180 -> Embargo 10 -> Frozen 200.",
        "- Runs: 32 preregistered and executed in one synthetic evaluation batch.",
        "",
        "### Frozen benchmarks",
        "",
        "| Benchmark | Total return | Max drawdown | Observation class |",
        "| --- | ---: | ---: | --- |",
    ]
    for benchmark_id in ("cash", "buy_and_hold"):
        result = bundle["benchmarks"][benchmark_id]["result"]
        lines.append(
            f"| {benchmark_id} | {_percent(result['total_return'])} | "
            f"{_percent(result['max_drawdown'])} | SYNTHETIC_OBSERVATION_ONLY |"
        )
    lines.extend(
        [
            "",
            "### Registered strategy observations",
            "",
            "| Family | Strategy | Train | Validation | Frozen 1x | Frozen 2x | Frozen 3x |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for report in bundle["strategy_reports"]:
        runs = report["runs"]
        lines.append(
            f"| {report['family_id']} | {report['strategy_id']} | "
            f"{_percent(runs['train']['result']['total_return'])} | "
            f"{_percent(runs['validation']['result']['total_return'])} | "
            f"{_percent(runs['frozen_1x']['result']['total_return'])} | "
            f"{_percent(runs['frozen_2x']['result']['total_return'])} | "
            f"{_percent(runs['frozen_3x']['result']['total_return'])} |"
        )
    lines.extend(["", "## GAP", ""])
    lines.extend(f"- `{gap}`" for gap in bundle["gaps"])
    lines.extend(
        [
            "",
            "- `ENSEMBLE` has no registered implementation and no report was fabricated.",
            "- Frozen observations are synthetic and do not constitute a formal blind test.",
            "",
            "## MATURITY",
            "",
            "- Bundle status: `BLOCK`",
            "- Maturity: `SYNTHETIC_BASELINE_ONLY`",
            "- RANGE reports: `PARTIAL`",
            "- TREND reports: `PARTIAL`",
            "- ENSEMBLE report: `GAP`",
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
        raise SyntheticStrategyReportBundleError("neutral renderer token violation")
    return markdown
