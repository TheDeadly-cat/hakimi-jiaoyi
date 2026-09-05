from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import inspect
from typing import Any, Callable

import pandas as pd

from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (
    BASE_FEE_RATE,
    BASE_SLIPPAGE_PCT,
    canonical_sha256,
    plan_synthetic_strategy_report_bundle_v1,
    verify_synthetic_strategy_report_bundle_v1,
)
from hakimi_research.synthetic_benchmark_controls import (
    NO_SKILL_PATH_COUNT,
    NO_SKILL_SEED_IDS,
    SyntheticBenchmarkControlError,
    build_no_skill_control_distribution,
    build_strategy_control_comparison,
    build_volatility_matched_buy_and_hold_projection,
    synthetic_benchmark_control_policy_v1,
    verify_no_skill_control_distribution,
    verify_strategy_control_comparison,
    verify_volatility_matched_buy_and_hold_projection,
)
from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig
from hakimi_research.models import Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-controls-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-benchmark-controls-bundle-v1"
RUN_SCHEMA_VERSION = "synthetic-strategy-benchmark-control-run-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-controls-receipt-v1"
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_BENCHMARK_CONTROLS_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "EQUAL_VOLATILITY_PROJECTION_NOT_EXECUTABLE",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "NO_SKILL_16_PATH_SYNTHETIC_DISTRIBUTION_ONLY",
    "REAL_DATASET_GAP",
    "REGISTERED_STRATEGIES_NOT_CONTROL_BENCHMARKS",
    "SIMPLE_CONTROL_PARAMETERS_NOT_OPTIMISED",
    "VOLATILITY_PROJECTION_FINANCING_AND_MARGIN_NOT_MODELLED",
]
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


class SyntheticStrategyBenchmarkControlsError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyBenchmarkControlsError(f"{path}: {message}")


def _verify_core_control_contract(
    path: str,
    verifier: Callable[..., None],
    *args: Any,
    **kwargs: Any,
) -> None:
    try:
        verifier(*args, **kwargs)
    except SyntheticBenchmarkControlError as exc:
        _fail(path, str(exc))


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_sha256(record)
    return record


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    if type(record) is not dict:
        _fail(path, "must be an exact dict")
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        _fail(f"{path}.{field}", "must be a SHA-256")
    payload = {key: value for key, value in record.items() if key != field}
    if canonical_sha256(payload) != digest:
        _fail(f"{path}.{field}", "digest mismatch")


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _gaps() -> list[str]:
    return list(_GAPS)


class _SimpleMovingAverageControl(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        if len(close) < 20:
            return Signal.hold("simple MA control warmup")
        average = float(close.iloc[-20:].mean())
        current = float(close.iloc[-1])
        if current > average and portfolio.position_qty <= 0:
            return Signal.buy("simple MA control above mean", 0.25)
        if current <= average and portfolio.position_qty > 0:
            return Signal.exit("simple MA control below mean")
        return Signal.hold("simple MA control unchanged")


class _SimpleBreakoutControl(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        close = data["close"]
        if len(close) < 21:
            return Signal.hold("simple breakout control warmup")
        prior = close.iloc[-21:-1]
        current = float(close.iloc[-1])
        if current > float(prior.max()) and portfolio.position_qty <= 0:
            return Signal.buy("simple breakout control new high", 0.25)
        if current < float(prior.min()) and portfolio.position_qty > 0:
            return Signal.exit("simple breakout control new low")
        return Signal.hold("simple breakout control unchanged")


class _HashNoSkillControl(StrategyBase):
    def generate_signal(self, data: pd.DataFrame, portfolio: Portfolio) -> Signal:
        seed_id = self.params.get("seed_id")
        if type(seed_id) is not str or seed_id not in NO_SKILL_SEED_IDS:
            raise ValueError("hash no-skill control requires a preregistered seed")
        signal_time = str(data.index[-1])
        payload = f"{seed_id}|{signal_time}|{len(data)}".encode("utf-8")
        bucket = hashlib.sha256(payload).digest()[0] % 3
        if bucket == 0 and portfolio.position_qty <= 0:
            return Signal.buy("hash no-skill control BUY bucket", 0.25)
        if bucket == 1 and portfolio.position_qty > 0:
            return Signal.exit("hash no-skill control EXIT bucket")
        return Signal.hold("hash no-skill control HOLD bucket")


def _implementation_identity(
    control_id: str,
    control_kind: str,
    strategy_type: type[StrategyBase],
    seed_id: str | None,
) -> dict[str, Any]:
    identity = {
        "control_id": control_id,
        "control_kind": control_kind,
        "module": strategy_type.__module__,
        "qualname": strategy_type.__qualname__,
        "version": "v1",
        "seed_id": seed_id,
        "class_source_sha256": hashlib.sha256(
            inspect.getsource(strategy_type).encode("utf-8")
        ).hexdigest(),
    }
    return _seal(identity, "identity_sha256")


def _run_specs() -> list[dict[str, Any]]:
    specs = [
        {
            "run_id": "benchmark_control:simple_ma:frozen_cost_1x",
            "control_id": "simple_ma",
            "control_kind": "SIMPLE_MOVING_AVERAGE",
            "seed_id": None,
        },
        {
            "run_id": "benchmark_control:simple_breakout:frozen_cost_1x",
            "control_id": "simple_breakout",
            "control_kind": "SIMPLE_BREAKOUT",
            "seed_id": None,
        },
    ]
    specs.extend(
        {
            "run_id": f"benchmark_control:hash_no_skill_{index:02d}:frozen_cost_1x",
            "control_id": f"hash_no_skill_{index:02d}",
            "control_kind": "HASH_NO_SKILL",
            "seed_id": seed_id,
        }
        for index, seed_id in enumerate(NO_SKILL_SEED_IDS)
    )
    return specs


def _strategy_type(control_kind: str) -> type[StrategyBase]:
    mapping = {
        "SIMPLE_MOVING_AVERAGE": _SimpleMovingAverageControl,
        "SIMPLE_BREAKOUT": _SimpleBreakoutControl,
        "HASH_NO_SKILL": _HashNoSkillControl,
    }
    try:
        return mapping[control_kind]
    except KeyError:
        _fail("control_kind", "unknown control implementation")


def plan_synthetic_strategy_benchmark_controls_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_report_bundle_v1()
    run_specs = _run_specs()
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_IN_MEMORY",
        "source_baseline_plan_sha256": source_plan["plan_sha256"],
        "source_required_run_count": source_plan["planned_run_count"],
        "reused_benchmark_ids": ["cash", "buy_and_hold"],
        "planned_control_runs": [
            {
                **spec,
                "subject_type": "BENCHMARK_CONTROL",
                "evaluation_role": "FROZEN_BENCHMARK_CONTROL_1X",
                "cost_multiplier": 1,
                "implementation_identity": _implementation_identity(
                    spec["control_id"],
                    spec["control_kind"],
                    _strategy_type(spec["control_kind"]),
                    spec["seed_id"],
                ),
            }
            for spec in run_specs
        ],
        "planned_run_count": len(run_specs),
        "executed_run_count": 0,
        "additional_backtest_run_count": len(run_specs),
        "planned_no_skill_distribution_count": 1,
        "planned_volatility_projection_count": 6,
        "planned_strategy_comparison_count": 6,
        "policy": synthetic_benchmark_control_policy_v1(),
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(plan, "plan_sha256")


def _frozen_frame(source_bundle: dict[str, Any]) -> pd.DataFrame:
    fixture = source_bundle["fixture"]
    frozen_slice = fixture["partition_protocol"]["frozen_slice"]
    if frozen_slice != [400, 600]:
        _fail("source_bundle.fixture", "frozen slice drifted")
    records = fixture["records"][frozen_slice[0] : frozen_slice[1]]
    frame = pd.DataFrame(
        [
            {
                "open": record["open"],
                "high": record["high"],
                "low": record["low"],
                "close": record["close"],
                "volume": record["volume"],
            }
            for record in records
        ],
        index=pd.DatetimeIndex(
            pd.to_datetime([record["time"] for record in records], utc=True),
            name="time",
        ),
    )
    if len(frame) != 200:
        _fail("source_bundle.fixture", "frozen row count drifted")
    return frame


def _new_config() -> BotConfig:
    config = BotConfig(
        name="hakimi-synthetic-benchmark-controls",
        mode="backtest",
        market="stock",
        symbol="SYNTH",
        timeframe="1d",
        initial_cash=10000.0,
    )
    config.data.provider = "synthetic"
    config.data.csv_path = ""
    config.data.use_cache = False
    config.execution.fee_rate = BASE_FEE_RATE
    config.execution.slippage_pct = BASE_SLIPPAGE_PCT
    config.execution.live_trading_enabled = False
    return config


def _factory(spec: dict[str, Any]) -> Callable[[], StrategyBase]:
    strategy_type = _strategy_type(spec["control_kind"])
    seed_id = spec["seed_id"]
    return lambda: strategy_type(
        params={} if seed_id is None else {"seed_id": seed_id},
        name=spec["control_id"],
        version="v1",
    )


def _run_control(
    spec: dict[str, Any],
    frame: pd.DataFrame,
    dataset_sha256: str,
    protocol_sha256: str,
) -> dict[str, Any]:
    config = _new_config()
    report = BacktestEngine(
        config,
        _factory(spec)(),
        RiskManager(config.risk),
        experiment_context={
            "evaluation_role": "FROZEN_BENCHMARK_CONTROL_1X",
            "evaluation_protocol_hash": protocol_sha256,
            "evaluation_protocol_verified": False,
            "git_commit_sha": "",
            "git_worktree_clean": False,
            "dependency_lock_name": "",
            "dependency_lock_hash": "",
            "dependency_lock_fully_pinned": False,
        },
    ).run(frame.copy(deep=True))
    result = asdict(report)
    if type(result) is not dict or set(result) != _RESULT_KEYS:
        _fail("control_run.result", "backtest report shape drifted")
    canonical_sha256(result)
    run = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": spec["run_id"],
        "subject_type": "BENCHMARK_CONTROL",
        "control_id": spec["control_id"],
        "control_kind": spec["control_kind"],
        "seed_id": spec["seed_id"],
        "evaluation_role": "FROZEN_BENCHMARK_CONTROL_1X",
        "dataset_sha256": dataset_sha256,
        "cost_multiplier": 1,
        "fee_rate": BASE_FEE_RATE,
        "slippage_pct": BASE_SLIPPAGE_PCT,
        "policy_sha256": synthetic_benchmark_control_policy_v1()["policy_sha256"],
        "implementation_identity": _implementation_identity(
            spec["control_id"],
            spec["control_kind"],
            _strategy_type(spec["control_kind"]),
            spec["seed_id"],
        ),
        "result": result,
        "result_sha256": canonical_sha256(result),
    }
    return _seal(run, "run_sha256")


def build_synthetic_strategy_benchmark_controls_v1(
    source_baseline_bundle: dict[str, Any], *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBenchmarkControlsError(
            "execution requires exact execute=True; inspect the plan first"
        )
    if verify_synthetic_strategy_report_bundle_v1(source_baseline_bundle).get("status") != "PASS":
        _fail("source_baseline_bundle", "source did not verify")
    plan = plan_synthetic_strategy_benchmark_controls_v1()
    frame = _frozen_frame(source_baseline_bundle)
    frozen_partition = source_baseline_bundle["fixture"]["partition_protocol"][
        "partitions"
    ]["frozen"]
    protocol_sha256 = source_baseline_bundle["fixture"]["partition_protocol"][
        "protocol_sha256"
    ]
    specs = _run_specs()
    runs = [
        _run_control(
            spec,
            frame,
            frozen_partition["dataset_sha256"],
            protocol_sha256,
        )
        for spec in specs
    ]
    run_by_id = {run["control_id"]: run for run in runs}
    no_skill_runs = [
        run_by_id[f"hash_no_skill_{index:02d}"]
        for index in range(NO_SKILL_PATH_COUNT)
    ]
    no_skill_distribution = build_no_skill_control_distribution(no_skill_runs)
    cash_run = source_baseline_bundle["benchmarks"]["cash"]
    buy_and_hold_run = source_baseline_bundle["benchmarks"]["buy_and_hold"]
    projections = [
        build_volatility_matched_buy_and_hold_projection(
            report, buy_and_hold_run
        )
        for report in source_baseline_bundle["strategy_reports"]
    ]
    projection_by_strategy = {
        item["strategy_id"]: item for item in projections
    }
    comparisons = [
        build_strategy_control_comparison(
            strategy_report=report,
            cash_run=cash_run,
            buy_and_hold_run=buy_and_hold_run,
            simple_ma_run=run_by_id["simple_ma"],
            simple_breakout_run=run_by_id["simple_breakout"],
            no_skill_distribution=no_skill_distribution,
            volatility_projection=projection_by_strategy[report["strategy_id"]],
        )
        for report in source_baseline_bundle["strategy_reports"]
    ]
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_baseline_bundle": deepcopy(source_baseline_bundle),
        "source_baseline_bundle_sha256": source_baseline_bundle["bundle_sha256"],
        "source_reused_run_count": source_baseline_bundle["executed_run_count"],
        "planned_run_count": len(runs),
        "executed_run_count": len(runs),
        "additional_backtest_run_count": len(runs),
        "control_runs": runs,
        "no_skill_distribution": no_skill_distribution,
        "volatility_matched_projections": projections,
        "strategy_control_comparisons": comparisons,
        "executed_analysis_count": 13,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    _seal(bundle, "bundle_sha256")
    verify_synthetic_strategy_benchmark_controls_v1(bundle)
    return bundle


def _verify_control_run(
    run: dict[str, Any], planned: dict[str, Any], dataset_sha256: str
) -> None:
    expected_keys = {
        "schema_version",
        "run_id",
        "subject_type",
        "control_id",
        "control_kind",
        "seed_id",
        "evaluation_role",
        "dataset_sha256",
        "cost_multiplier",
        "fee_rate",
        "slippage_pct",
        "policy_sha256",
        "implementation_identity",
        "result",
        "result_sha256",
        "run_sha256",
    }
    if type(run) is not dict or set(run) != expected_keys:
        _fail("control_run", "shape mismatch")
    _verify_seal(run, "run_sha256", "control_run")
    if run["schema_version"] != RUN_SCHEMA_VERSION:
        _fail("control_run.schema_version", "schema mismatch")
    for field in (
        "run_id",
        "subject_type",
        "control_id",
        "control_kind",
        "seed_id",
        "evaluation_role",
        "cost_multiplier",
        "implementation_identity",
    ):
        if run[field] != planned[field]:
            _fail(f"control_run.{field}", "plan mismatch")
    if (
        run["dataset_sha256"] != dataset_sha256
        or run["fee_rate"] != BASE_FEE_RATE
        or run["slippage_pct"] != BASE_SLIPPAGE_PCT
        or run["policy_sha256"]
        != synthetic_benchmark_control_policy_v1()["policy_sha256"]
    ):
        _fail("control_run", "source/cost/policy binding mismatch")
    result = run["result"]
    if type(result) is not dict or set(result) != _RESULT_KEYS:
        _fail("control_run.result", "shape mismatch")
    if canonical_sha256(result) != run["result_sha256"]:
        _fail("control_run.result_sha256", "digest mismatch")
    manifest = result["experiment_manifest"]
    if type(manifest) is not dict or manifest.get("research_only") is not True:
        _fail("control_run.result.experiment_manifest", "research lock missing")
    for field in (
        "live_order_allowed",
        "order_entry_allowed",
        "paper_authorized",
        "result_is_profitability_proof",
    ):
        if manifest.get(field) is not False:
            _fail(f"control_run.result.experiment_manifest.{field}", "authority escalation")


def verify_synthetic_strategy_benchmark_controls_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    canonical_sha256(bundle)
    expected_keys = {
        "schema_version",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_baseline_bundle",
        "source_baseline_bundle_sha256",
        "source_reused_run_count",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "control_runs",
        "no_skill_distribution",
        "volatility_matched_projections",
        "strategy_control_comparisons",
        "executed_analysis_count",
        "runtime_mutations",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if type(bundle) is not dict or set(bundle) != expected_keys:
        _fail("bundle", "shape mismatch")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    if bundle["schema_version"] != BUNDLE_SCHEMA_VERSION:
        _fail("bundle.schema_version", "schema mismatch")
    if bundle["plan"] != plan_synthetic_strategy_benchmark_controls_v1():
        _fail("bundle.plan", "must equal deterministic preregistration")
    source = bundle["source_baseline_bundle"]
    if verify_synthetic_strategy_report_bundle_v1(source).get("status") != "PASS":
        _fail("bundle.source_baseline_bundle", "verification failed")
    if bundle["source_baseline_bundle_sha256"] != source["bundle_sha256"]:
        _fail("bundle.source_baseline_bundle_sha256", "source mismatch")
    if (
        bundle["source_reused_run_count"] != 32
        or bundle["planned_run_count"] != 18
        or bundle["executed_run_count"] != 18
        or bundle["additional_backtest_run_count"] != 18
        or bundle["executed_analysis_count"] != 13
    ):
        _fail("bundle", "run or analysis accounting drifted")
    runs = bundle["control_runs"]
    planned_runs = bundle["plan"]["planned_control_runs"]
    if type(runs) is not list or len(runs) != 18:
        _fail("bundle.control_runs", "must contain 18 runs")
    dataset_sha256 = source["fixture"]["partition_protocol"]["partitions"][
        "frozen"
    ]["dataset_sha256"]
    for run, planned in zip(runs, planned_runs):
        _verify_control_run(run, planned, dataset_sha256)
    run_by_id = {run["control_id"]: run for run in runs}
    no_skill_runs = [
        run_by_id[f"hash_no_skill_{index:02d}"]
        for index in range(NO_SKILL_PATH_COUNT)
    ]
    _verify_core_control_contract(
        "bundle.no_skill_distribution",
        verify_no_skill_control_distribution,
        bundle["no_skill_distribution"],
        no_skill_runs,
    )
    reports = source["strategy_reports"]
    report_by_id = {report["strategy_id"]: report for report in reports}
    projections = bundle["volatility_matched_projections"]
    if type(projections) is not list or [p.get("strategy_id") for p in projections] != [
        report["strategy_id"] for report in reports
    ]:
        _fail("bundle.volatility_matched_projections", "membership mismatch")
    buy_and_hold_run = source["benchmarks"]["buy_and_hold"]
    for projection in projections:
        _verify_core_control_contract(
            "bundle.volatility_matched_projections",
            verify_volatility_matched_buy_and_hold_projection,
            projection,
            report_by_id[projection["strategy_id"]],
            buy_and_hold_run,
        )
    projection_by_id = {p["strategy_id"]: p for p in projections}
    comparisons = bundle["strategy_control_comparisons"]
    if type(comparisons) is not list or [c.get("strategy_id") for c in comparisons] != [
        report["strategy_id"] for report in reports
    ]:
        _fail("bundle.strategy_control_comparisons", "membership mismatch")
    for comparison in comparisons:
        strategy_id = comparison["strategy_id"]
        _verify_core_control_contract(
            "bundle.strategy_control_comparisons",
            verify_strategy_control_comparison,
            comparison,
            strategy_report=report_by_id[strategy_id],
            cash_run=source["benchmarks"]["cash"],
            buy_and_hold_run=buy_and_hold_run,
            simple_ma_run=run_by_id["simple_ma"],
            simple_breakout_run=run_by_id["simple_breakout"],
            no_skill_distribution=bundle["no_skill_distribution"],
            volatility_projection=projection_by_id[strategy_id],
        )
    if (
        bundle["evidence_state"] != EVIDENCE_STATE
        or bundle["status"] != STATUS
        or bundle["maturity"] != MATURITY
        or bundle["runtime_mutations"] is not False
        or bundle["gaps"] != _gaps()
        or bundle["authority"] != _authority()
    ):
        _fail("bundle", "maturity or authority drifted")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "bundle_sha256": bundle["bundle_sha256"],
        "source_reused_run_count": 32,
        "executed_run_count": 18,
        "additional_backtest_run_count": 18,
        "direct_control_run_count": 2,
        "no_skill_path_count": 16,
        "volatility_projection_count": 6,
        "strategy_comparison_count": 6,
        "executed_analysis_count": 13,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def replay_synthetic_strategy_benchmark_controls_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_benchmark_controls_v1(bundle)
    replayed = build_synthetic_strategy_benchmark_controls_v1(
        bundle["source_baseline_bundle"], execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic control replay mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    output["replayed_run_count"] = 18
    return output


def render_synthetic_strategy_benchmark_controls_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_controls_v1(bundle)
    run_by_id = {run["control_id"]: run for run in bundle["control_runs"]}
    rows = [
        "| Control | Frozen total return | Role |",
        "| --- | ---: | --- |",
        f"| cash | {bundle['source_baseline_bundle']['benchmarks']['cash']['result']['total_return']} | REUSED_CONTROL |",
        f"| buy_and_hold | {bundle['source_baseline_bundle']['benchmarks']['buy_and_hold']['result']['total_return']} | REUSED_CONTROL |",
        f"| simple_ma | {run_by_id['simple_ma']['result']['total_return']} | INDEPENDENT_CONTROL |",
        f"| simple_breakout | {run_by_id['simple_breakout']['result']['total_return']} | INDEPENDENT_CONTROL |",
        f"| hash_no_skill_median | {bundle['no_skill_distribution']['summary']['median_type7']} | 16_PATH_DISTRIBUTION |",
    ]
    markdown = "\n".join(
        [
            "# Synthetic Strategy Benchmark Controls v1",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            "- Reuses the verified 32-run baseline and its exact Frozen partition.",
            "- Executes 18 additional Frozen 1x benchmark-control runs: two fixed rules and sixteen hash-derived no-skill paths.",
            "- Registered strategies are comparison subjects, not relabelled controls.",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['state']}",
            "- All no-skill paths are retained; no random path is selected.",
            "- Equal-volatility buy-and-hold values are ex-post descriptive projections without financing or margin modelling.",
            "- No ranking, decision threshold, or formal inference is produced.",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Formal inference authority: false",
            "- Profitability proof: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            *rows,
            "",
            f"Bundle SHA-256: `{receipt['bundle_sha256']}`",
        ]
    )
    for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
        if forbidden in markdown:
            _fail("renderer", f"neutral token violation:{forbidden}")
    return markdown
