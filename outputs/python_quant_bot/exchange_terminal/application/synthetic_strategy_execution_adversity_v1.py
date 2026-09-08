from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
from pathlib import Path
from typing import Any

import pandas as pd

from examples.build_synthetic_strategy_benchmark_report_v10 import (
    plan_synthetic_strategy_benchmark_report_v10,
    verify_synthetic_strategy_benchmark_report_v10,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    _frozen_frame,
    _new_config,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    verify_synthetic_strategy_report_bundle_v1,
)
from hakimi_research.trial_return_matrix import (
    TrialReturnMatrixError,
    canonical_trial_return_matrix_sha256,
)
from hakimi_research.backtest import BacktestEngine
from hakimi_research.models import Action, Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase
from hakimi_research.strategies.templates import STRATEGY_REGISTRY
from hakimi_research.frozen_execution_adversity import (
    DropEveryThirdActionableSignal as _DropEveryThirdActionableSignal,
    OneBarSignalReleaseDelay as _OneBarSignalReleaseDelay,
    build_adverse_open_frame as _adverse_open_frame,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-execution-adversity-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-execution-adversity-bundle-v1"
RUN_SCHEMA_VERSION = "synthetic-strategy-execution-adversity-run-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-execution-adversity-receipt-v1"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_EXECUTION_ADVERSITY_ONLY"
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
SOURCE_LOGICAL_RUN_COUNT = 204
ADDITIONAL_RUN_COUNT = 18
TOTAL_LOGICAL_RUN_COUNT = 222
_SCENARIO_IDS = [
    "one_bar_signal_release_delay",
    "drop_every_third_actionable_signal",
    "source_fill_adverse_open_2pct",
]
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "ADVERSE_OPEN_SCHEDULE_SOURCE_FILL_BOUND",
    "DELAY_WRAPPER_SIGNAL_TIME_IS_RELEASE_TIME",
    "LIQUIDITY_CAPACITY_NOT_MODELLED",
    "ORDER_REJECTION_NOT_MODELLED",
    "PARTIAL_FILL_NOT_MODELLED",
    "SIGNAL_DROP_DETERMINISTIC_NOT_EMPIRICAL_FILL_RATE",
    "SOURCE_FILL_SCHEDULED_OPEN_SHOCK_NOT_DYNAMIC_MARKET_IMPACT",
    "SYNTHETIC_EXECUTION_ADVERSITY_ONLY",
]
_SOURCE_EXTENSION_PATHS = [
    "src/hakimi_research/frozen_execution_adversity.py",
    "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_execution_adversity_v1.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v11.py",
]


class SyntheticStrategyExecutionAdversityError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyExecutionAdversityError(f"{path}: {message}")


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _require_canonical(value: Any, path: str) -> None:
    try:
        canonical_trial_return_matrix_sha256(value)
    except TrialReturnMatrixError as exc:
        _fail(path, str(exc))


def _repo_root() -> Path:
    root = Path(__file__).resolve().parents[4]
    if not (root / "outputs" / "python_quant_bot").is_dir():
        _fail("source_root", "repository layout mismatch")
    return root


def _source_extension_manifest() -> dict[str, Any]:
    root = _repo_root()
    files = []
    for relative_path in _SOURCE_EXTENSION_PATHS:
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            _fail(relative_path, "must remain inside repository root")
        if not path.is_file():
            _fail(relative_path, "required source file is missing")
        payload = path.read_bytes()
        files.append(
            {
                "path": relative_path,
                "byte_count": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {
        "schema_version": "benchmark-v11-source-extension-manifest-v1",
        "scope": "EXECUTION_ADVERSITY_AND_V11_CONSUMER",
        "file_count": len(files),
        "files": files,
    }
    return _seal(manifest, "source_extension_manifest_sha256")


def execution_adversity_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": "synthetic-strategy-execution-adversity-policy-v1",
        "source_partition": "FROZEN",
        "source_cost_multiplier": 1,
        "fee_rate": "0.00050000000000000001",
        "slippage_pct": "0.00020000000000000001",
        "scenarios": [
            {
                "scenario_id": "one_bar_signal_release_delay",
                "rule": "BUFFER_EACH_GENERATED_SIGNAL_FOR_ONE_ADDITIONAL_BAR",
                "engine_fill_rule": "RELEASED_SIGNAL_STILL_FILLS_AT_NEXT_BAR_OPEN",
                "performance_selected": False,
            },
            {
                "scenario_id": "drop_every_third_actionable_signal",
                "rule": "REPLACE_EVERY_THIRD_BUY_SELL_OR_EXIT_SIGNAL_WITH_HOLD",
                "drop_index_origin": 1,
                "performance_selected": False,
            },
            {
                "scenario_id": "source_fill_adverse_open_2pct",
                "rule": "AT_SOURCE_NEXT_OPEN_FILL_TIMES_BUY_OPEN_PLUS_2_PERCENT_SELL_OPEN_MINUS_2_PERCENT",
                "ohlc_repair": "EXPAND_HIGH_LOW_TO_INCLUDE_STRESSED_OPEN_AND_UNCHANGED_CLOSE",
                "source_schedule": "BOUND_FROZEN_1X_NEXT_BAR_OPEN_FILLS",
                "performance_selected": False,
            },
        ],
        "partial_fill_modelled": False,
        "liquidity_capacity_modelled": False,
        "order_rejection_modelled": False,
        "dynamic_market_impact_modelled": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "post_observation_policy_tuning": False,
    }
    return _seal(policy, "policy_sha256")


def _find_baseline_bundle(source_report_v10: dict[str, Any]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if type(value) is dict:
            if value.get("schema_version") == "synthetic-strategy-report-bundle-v1":
                matches.append(value)
            for item in value.values():
                visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)

    visit(source_report_v10)
    unique = {item.get("bundle_sha256"): item for item in matches}
    if len(unique) != 1 or None in unique:
        _fail("source_report_v10", "must embed one unique baseline bundle")
    baseline = next(iter(unique.values()))
    try:
        verify_synthetic_strategy_report_bundle_v1(baseline)
    except Exception as exc:
        _fail("source_baseline_bundle", f"verification failed:{type(exc).__name__}:{exc}")
    return baseline


def _strategy_report_map(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        report["strategy_id"]: report for report in baseline["strategy_reports"]
    }


def _base_strategy(
    strategy_id: str, implementation_identity: dict[str, Any]
) -> StrategyBase:
    strategy_type = STRATEGY_REGISTRY.get(strategy_id)
    if strategy_type is None:
        _fail("strategy_id", f"unregistered strategy:{strategy_id}")
    strategy = strategy_type()
    expected = {
        "module": strategy_type.__module__,
        "qualname": strategy_type.__qualname__,
        "declared_version": strategy.version,
        "default_parameters": strategy.params,
    }
    for key, value in expected.items():
        if implementation_identity.get(key) != value:
            _fail(
                f"implementation_identity.{strategy_id}.{key}",
                "registered implementation drifted",
            )
    return strategy


def _implementation_record(
    strategy_id: str,
    source_identity: dict[str, Any],
    executed_strategy: StrategyBase,
) -> dict[str, Any]:
    record = {
        "strategy_id": strategy_id,
        "source_strategy_identity_sha256": source_identity["identity_sha256"],
        "executed_module": type(executed_strategy).__module__,
        "executed_qualname": type(executed_strategy).__qualname__,
        "executed_version": executed_strategy.version,
        "executed_parameters": deepcopy(executed_strategy.params),
        "executed_source_sha256": hashlib.sha256(
            inspect.getsource(type(executed_strategy)).encode("utf-8")
        ).hexdigest(),
    }
    return _seal(record, "implementation_sha256")


def _scenario_metadata(
    scenario_id: str,
    strategy: StrategyBase,
    adverse_events: list[dict[str, Any]],
) -> dict[str, Any]:
    if scenario_id == "one_bar_signal_release_delay":
        if not isinstance(strategy, _OneBarSignalReleaseDelay):
            _fail("scenario", "delay wrapper mismatch")
        metadata_record = {
            "generated_signal_count": strategy.generated_signal_count,
            "released_signal_count": strategy.released_signal_count,
            "unreleased_terminal_signal_count": (
                strategy.generated_signal_count - strategy.released_signal_count
            ),
        }
    elif scenario_id == "drop_every_third_actionable_signal":
        if not isinstance(strategy, _DropEveryThirdActionableSignal):
            _fail("scenario", "drop wrapper mismatch")
        metadata_record = {
            "actionable_signal_count": strategy.actionable_signal_count,
            "dropped_signal_count": strategy.dropped_signal_count,
            "drop_every": 3,
        }
    else:
        metadata_record = {
            "adverse_open_event_count": len(adverse_events),
            "adverse_open_events": adverse_events,
        }
    return _seal(metadata_record, "scenario_metadata_sha256")


def _delta(source: dict[str, Any], stressed: dict[str, Any]) -> dict[str, Any]:
    delta = {
        "total_return_delta": format(
            float(stressed["total_return"]) - float(source["total_return"]),
            ".17g",
        ),
        "max_drawdown_delta": format(
            float(stressed["max_drawdown"]) - float(source["max_drawdown"]),
            ".17g",
        ),
        "trade_count_delta": int(stressed["trades"]) - int(source["trades"]),
        "final_equity_delta": format(
            float(stressed["final_equity"]) - float(source["final_equity"]),
            ".17g",
        ),
        "total_fee_delta": format(
            float(stressed["total_fees"]) - float(source["total_fees"]),
            ".17g",
        ),
    }
    return _seal(delta, "delta_sha256")


def _run_record(
    *,
    strategy_id: str,
    scenario_id: str,
    strategy_report: dict[str, Any],
    source_frame: pd.DataFrame,
    policy_sha256: str,
    dependency_lock_sha256: str,
) -> dict[str, Any]:
    source_run = strategy_report["runs"]["frozen_1x"]
    source_result = source_run["result"]
    source_identity = strategy_report["implementation_identity"]
    base = _base_strategy(strategy_id, source_identity)
    adverse_events: list[dict[str, Any]] = []
    frame = source_frame
    if scenario_id == "one_bar_signal_release_delay":
        strategy: StrategyBase = _OneBarSignalReleaseDelay(
            base, strategy_id, source_identity["identity_sha256"]
        )
    elif scenario_id == "drop_every_third_actionable_signal":
        strategy = _DropEveryThirdActionableSignal(
            base, strategy_id, source_identity["identity_sha256"]
        )
    elif scenario_id == "source_fill_adverse_open_2pct":
        strategy = base
        frame, adverse_events = _adverse_open_frame(source_frame, source_result)
    else:
        _fail("scenario_id", "unknown scenario")
    config = _new_config()
    report = BacktestEngine(
        config,
        strategy,
        RiskManager(config.risk),
        experiment_context={
            "evaluation_role": "FROZEN_EXECUTION_ADVERSITY",
            "evaluation_protocol_hash": policy_sha256,
            "random_seed": 0,
            "dependency_lock_name": "requirements-benchmark-v9.lock",
            "dependency_lock_hash": dependency_lock_sha256,
            "dependency_lock_fully_pinned": True,
        },
    ).run(frame).to_dict()
    result_sha256 = canonical_trial_return_matrix_sha256(report)
    run = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": f"{strategy_id}:{scenario_id}",
        "strategy_id": strategy_id,
        "scenario_id": scenario_id,
        "scenario_policy_sha256": policy_sha256,
        "source_frozen_run_id": source_run["run_id"],
        "source_frozen_run_sha256": source_run["run_sha256"],
        "source_frozen_result_sha256": source_run["result_sha256"],
        "source_frozen_dataset_sha256": source_run["dataset_sha256"],
        "source_frozen_input_dataset_sha256": source_result["reproducibility"][
            "data_hash"
        ],
        "source_strategy_identity_sha256": source_identity["identity_sha256"],
        "implementation": _implementation_record(
            strategy_id, source_identity, strategy
        ),
        "input_dataset_sha256": report["reproducibility"]["data_hash"],
        "input_row_count": report["reproducibility"]["data_rows"],
        "fee_rate": config.execution.fee_rate,
        "slippage_pct": config.execution.slippage_pct,
        "scenario_metadata": _scenario_metadata(
            scenario_id, strategy, adverse_events
        ),
        "result": report,
        "result_sha256": result_sha256,
        "source_result_delta": _delta(source_result, report),
        "runtime_mutations": False,
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(run, "run_sha256")


def _planned_runs(strategy_ids: list[str]) -> list[dict[str, str]]:
    return [
        {
            "run_id": f"{strategy_id}:{scenario_id}",
            "strategy_id": strategy_id,
            "scenario_id": scenario_id,
            "source_frozen_run_id": f"{strategy_id}:frozen_cost_1x",
        }
        for strategy_id in strategy_ids
        for scenario_id in _SCENARIO_IDS
    ]


def plan_synthetic_strategy_execution_adversity_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v10()
    strategy_ids = sorted(STRATEGY_REGISTRY)
    expected_strategy_ids = [
        "bollinger",
        "dual_ma",
        "grid",
        "macd",
        "momentum",
        "rsi",
    ]
    if strategy_ids != expected_strategy_ids:
        _fail("registered_strategy_ids", "expected fixed six-strategy registry")
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_FROZEN_IN_MEMORY",
        "source_report_v10_plan_sha256": source_plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "source_baseline_reused_run_count": 32,
        "registered_strategy_ids": list(strategy_ids),
        "scenario_ids": list(_SCENARIO_IDS),
        "scenario_policy": execution_adversity_policy_v1(),
        "source_extension_manifest": _source_extension_manifest(),
        "planned_runs": _planned_runs(strategy_ids),
        "planned_run_count": ADDITIONAL_RUN_COUNT,
        "executed_run_count": 0,
        "additional_backtest_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "requires_prebuilt_v10_report": True,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": list(_GAPS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(plan, "plan_sha256")


def _compose_bundle(
    source_report_v10: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    baseline = _find_baseline_bundle(source_report_v10)
    frame = _frozen_frame(baseline)
    reports = _strategy_report_map(baseline)
    policy_sha256 = plan["scenario_policy"]["policy_sha256"]
    dependency_lock_sha256 = source_report_v10["bindings"][
        "dependency_lock_sha256"
    ]
    runs = [
        _run_record(
            strategy_id=spec["strategy_id"],
            scenario_id=spec["scenario_id"],
            strategy_report=reports[spec["strategy_id"]],
            source_frame=frame,
            policy_sha256=policy_sha256,
            dependency_lock_sha256=dependency_lock_sha256,
        )
        for spec in plan["planned_runs"]
    ]
    no_event_count = sum(
        run["scenario_id"] == "source_fill_adverse_open_2pct"
        and run["scenario_metadata"]["adverse_open_event_count"] == 0
        for run in runs
    )
    no_drop_count = sum(
        run["scenario_id"] == "drop_every_third_actionable_signal"
        and run["scenario_metadata"]["dropped_signal_count"] == 0
        for run in runs
    )
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": deepcopy(plan),
        "source_report_v10_sha256": source_report_v10["report_sha256"],
        "source_report_v10_plan_sha256": source_report_v10["plan"][
            "plan_sha256"
        ],
        "source_baseline_bundle_sha256": baseline["bundle_sha256"],
        "source_frozen_dataset_sha256": baseline["fixture"][
            "partition_protocol"
        ]["partitions"]["frozen"]["dataset_sha256"],
        "dependency_lock_sha256": dependency_lock_sha256,
        "source_extension_manifest": deepcopy(
            plan["source_extension_manifest"]
        ),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "source_baseline_reused_run_count": 32,
        "planned_run_count": ADDITIONAL_RUN_COUNT,
        "executed_run_count": len(runs),
        "additional_backtest_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "no_adverse_open_event_strategy_count": no_event_count,
        "no_dropped_signal_strategy_count": no_drop_count,
        "runs": runs,
        "runtime_mutations": False,
        "computed_diagnostics": [
            "ONE_ADDITIONAL_BAR_SIGNAL_RELEASE_DELAY",
            "DETERMINISTIC_EVERY_THIRD_ACTIONABLE_SIGNAL_DROP",
            "SOURCE_FILL_BOUND_ADVERSE_OPEN_SHOCK",
            "SOURCE_RESULT_DELTAS",
        ],
        "gaps": list(_GAPS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(bundle, "bundle_sha256")


def build_synthetic_strategy_execution_adversity_v1(
    source_report_v10: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyExecutionAdversityError(
            "execution requires exact execute=True; inspect the plan first"
        )
    try:
        verify_synthetic_strategy_benchmark_report_v10(source_report_v10)
    except Exception as exc:
        _fail("source_report_v10", f"verification failed:{type(exc).__name__}:{exc}")
    return _compose_bundle(
        source_report_v10, plan_synthetic_strategy_execution_adversity_v1()
    )


def verify_synthetic_strategy_execution_adversity_v1(
    bundle: dict[str, Any], source_report_v10: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        _fail("bundle", "must be an exact dict")
    _require_canonical(bundle, "bundle")
    try:
        verify_synthetic_strategy_benchmark_report_v10(source_report_v10)
    except Exception as exc:
        _fail("source_report_v10", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_execution_adversity_v1()
    expected = _compose_bundle(source_report_v10, plan)
    if bundle != expected:
        _fail("bundle", "must match deterministic source-bound adversity execution")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "source_report_v10_sha256": bundle["source_report_v10_sha256"],
        "source_baseline_bundle_sha256": bundle[
            "source_baseline_bundle_sha256"
        ],
        "source_extension_manifest_sha256": bundle[
            "source_extension_manifest"
        ]["source_extension_manifest_sha256"],
        "strategy_count": len(plan["registered_strategy_ids"]),
        "scenario_count": len(plan["scenario_ids"]),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "executed_run_count": ADDITIONAL_RUN_COUNT,
        "additional_backtest_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "runtime_mutations": False,
        "gaps": list(_GAPS),
        "authority": deepcopy(_AUTHORITY),
    }


def replay_synthetic_strategy_execution_adversity_v1(
    bundle: dict[str, Any], source_report_v10: dict[str, Any]
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_execution_adversity_v1(
        bundle, source_report_v10
    )
    replayed = build_synthetic_strategy_execution_adversity_v1(
        source_report_v10, execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic execution mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    return output


def render_synthetic_strategy_execution_adversity_markdown_v1(
    bundle: dict[str, Any], source_report_v10: dict[str, Any]
) -> str:
    receipt = verify_synthetic_strategy_execution_adversity_v1(
        bundle, source_report_v10
    )
    markdown = "\n".join(
        [
            "# Synthetic Strategy Execution Adversity v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_FROZEN_IN_MEMORY",
            f"- Strategies: {receipt['strategy_count']}",
            f"- Scenarios: {receipt['scenario_count']}",
            f"- Additional backtest runs: {receipt['additional_backtest_run_count']}",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            "- Delay, deterministic signal drop, and source-fill adverse open shock are observed.",
            "- Partial fills, liquidity capacity, rejection, and dynamic market impact remain unmodelled.",
            "- Result deltas are descriptive synthetic diagnostics without a decision threshold.",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Formal inference authority: false",
            "- Profitability proof: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Bundle SHA-256: `{receipt['bundle_sha256']}`",
        ]
    )
    for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
        if forbidden in markdown:
            _fail("renderer", f"neutral token violation:{forbidden}")
    return markdown
