from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import pandas as pd


PYTHON_QUANT_BOT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PYTHON_QUANT_BOT_ROOT.parents[1]
for import_root in (PYTHON_QUANT_BOT_ROOT, WORKSPACE_ROOT / "src"):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (  # noqa: E402
    _BuyAndHoldBenchmark,
    _records,
    _run_backtest,
    plan_synthetic_strategy_report_bundle_v1,
)
from hakimi_research.market_regime_evidence import (  # noqa: E402
    build_market_regime_evidence,
    market_regime_policy_v1,
    verify_market_regime_evidence,
)
from hakimi_research.strategies.templates import build_strategy


PLAN_SCHEMA_VERSION = "synthetic-strategy-high-volatility-validation-plan-v1"
FIXTURE_SCHEMA_VERSION = "synthetic-high-volatility-fixture-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-high-volatility-validation-bundle-v1"
RECORD_SCHEMA_VERSION = "synthetic-strategy-high-volatility-validation-record-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-high-volatility-validation-receipt-v1"
FIXTURE_ID = "deterministic-alternating-high-volatility-stock-daily-v1"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
TARGET_REGIME_ID = "HIGH_VOLATILITY"
OBSERVATION_CLASS = "SYNTHETIC_HIGH_VOLATILITY_SCENARIO"
EVALUATION_ROLE = "SYNTHETIC_HIGH_VOLATILITY_SCENARIO"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_HIGH_VOLATILITY_SCENARIO_ONLY"
STATUS = "BLOCK"
ROW_COUNT = 220
EXPECTED_TARGET_OBSERVATION_COUNT = 189

_GAPS = (
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "HIGH_VOLATILITY_SYNTHETIC_SCENARIO_ONLY",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "REAL_DATASET_GAP",
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyHighVolatilityValidationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyHighVolatilityValidationError(f"{path}: {message}")


def _gaps() -> list[str]:
    return list(_GAPS)


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _assert_exact_json(value: Any, path: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail(path, "contains a non-native string key")
            _assert_exact_json(child, f"{path}.{key}")
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _assert_exact_json(child, f"{path}[{index}]")
        return
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    _fail(path, "must contain exact finite JSON-native values")


def _canonical_sha256(value: dict[str, Any] | list[Any]) -> str:
    _assert_exact_json(value, "canonical_payload")
    payload = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    return {**record, field: _canonical_sha256(record)}


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    digest = record.get(field)
    if type(digest) is not str or len(digest) != 64:
        _fail(f"{path}.{field}", "must be an exact SHA-256 string")
    payload = {key: value for key, value in record.items() if key != field}
    if digest != _canonical_sha256(payload):
        _fail(f"{path}.{field}", "digest mismatch")


def _build_frame() -> pd.DataFrame:
    index = pd.date_range(
        "2022-01-01",
        periods=ROW_COUNT,
        freq="D",
        tz="UTC",
        name="time",
    )
    rows: list[dict[str, float]] = []
    close = 100.0
    for position in range(ROW_COUNT):
        prior = close
        close = prior * (1.06 if position % 2 == 0 else 0.94)
        rows.append(
            {
                "open": float(prior),
                "high": float(max(prior, close) * 1.01),
                "low": float(min(prior, close) * 0.99),
                "close": float(close),
                "volume": float(1000 + (position % 5) * 10),
            }
        )
    return pd.DataFrame(rows, index=index)


def _build_fixture() -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = _build_frame()
    records = _records(frame)
    dataset_sha256 = _canonical_sha256(records)
    payload = {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "source": DATA_SOURCE,
        "market": "stock",
        "symbol": "SYNTH-HIGH-VOL",
        "timeframe": "1d",
        "periods_per_year": 252,
        "randomness": "NONE",
        "row_count": ROW_COUNT,
        "start_time": records[0]["time"],
        "end_time": records[-1]["time"],
        "generation_policy": {
            "initial_close": "100",
            "even_index_simple_return": "0.06",
            "odd_index_simple_return": "-0.06",
            "high_low_envelope_fraction": "0.01",
            "base_volume": 1000,
            "volume_cycle_length": 5,
            "volume_cycle_increment": 10,
            "post_observation_tuning": False,
        },
        "records": records,
        "dataset_sha256": dataset_sha256,
    }
    return frame, _seal(payload, "fixture_sha256")


def _fixture_contract(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in fixture.items()
        if key != "records"
    }


def _family_for_strategy(strategy_id: str) -> str:
    baseline_plan = plan_synthetic_strategy_report_bundle_v1()
    matches = [
        family_id
        for family_id, members in baseline_plan["family_members"].items()
        if strategy_id in members
    ]
    if len(matches) != 1:
        _fail("strategy_id", f"{strategy_id} must map to one registered family")
    return matches[0]


def _planned_runs(strategy_ids: list[str]) -> list[dict[str, Any]]:
    runs = [
        {
            "run_id": "benchmark:buy_and_hold:high_volatility_1x",
            "subject_type": "BENCHMARK",
            "subject_id": "buy_and_hold",
            "evaluation_role": EVALUATION_ROLE,
            "cost_multiplier": 1,
        }
    ]
    runs.extend(
        {
            "run_id": f"{strategy_id}:high_volatility_1x",
            "subject_type": "REGISTERED_STRATEGY",
            "subject_id": strategy_id,
            "family_id": _family_for_strategy(strategy_id),
            "evaluation_role": EVALUATION_ROLE,
            "cost_multiplier": 1,
        }
        for strategy_id in strategy_ids
    )
    return runs


def _plan_payload_v1() -> dict[str, Any]:
    baseline_plan = plan_synthetic_strategy_report_bundle_v1()
    strategy_ids = list(baseline_plan["registered_strategy_ids"])
    _, fixture = _build_fixture()
    planned_runs = _planned_runs(strategy_ids)
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": DATA_SOURCE,
        "fixture_contract": _fixture_contract(fixture),
        "registered_strategy_ids": strategy_ids,
        "planned_runs": planned_runs,
        "planned_run_count": len(planned_runs),
        "executed_run_count": 0,
        "planned_analysis_count": len(strategy_ids),
        "executed_analysis_count": 0,
        "target_regime_id": TARGET_REGIME_ID,
        "expected_target_observation_count_per_strategy": (
            EXPECTED_TARGET_OBSERVATION_COUNT
        ),
        "market_regime_policy": market_regime_policy_v1(),
        "selection_policy": {
            "parameter_search": "NOT_EXECUTED",
            "parameters": "REGISTERED_STRATEGY_DEFAULTS",
            "performance_selection_used": False,
            "post_observation_tuning": False,
        },
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def plan_synthetic_strategy_high_volatility_validation_v1() -> dict[str, Any]:
    payload = _plan_payload_v1()
    return {**payload, "plan_sha256": _canonical_sha256(payload)}


def verify_synthetic_strategy_high_volatility_validation_plan_v1(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(plan, "plan")
    expected = plan_synthetic_strategy_high_volatility_validation_v1()
    if plan != expected:
        _fail("plan", "does not match deterministic preregistration")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "PASS",
        "plan_sha256": plan["plan_sha256"],
        "planned_run_count": plan["planned_run_count"],
        "planned_analysis_count": plan["planned_analysis_count"],
        "runtime_mutations": False,
        "authority": _authority(),
    }


def _verify_run(
    run: dict[str, Any],
    *,
    expected_run_id: str,
    dataset_sha256: str,
    protocol_sha256: str,
    path: str,
) -> None:
    _assert_exact_json(run, path)
    expected_keys = {
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
    if set(run) != expected_keys:
        _fail(path, "run fields do not match the contract")
    if run["run_id"] != expected_run_id:
        _fail(f"{path}.run_id", "identity mismatch")
    if run["evaluation_role"] != EVALUATION_ROLE:
        _fail(f"{path}.evaluation_role", "must remain the synthetic scenario role")
    if run["dataset_sha256"] != dataset_sha256:
        _fail(f"{path}.dataset_sha256", "fixture binding mismatch")
    if run["cost_multiplier"] != 1:
        _fail(f"{path}.cost_multiplier", "must remain one")
    if run["result_sha256"] != _canonical_sha256(run["result"]):
        _fail(f"{path}.result_sha256", "result digest mismatch")
    _verify_seal(run, "run_sha256", path)

    result = run["result"]
    manifest = result.get("experiment_manifest")
    reproducibility = result.get("reproducibility")
    if type(manifest) is not dict or type(reproducibility) is not dict:
        _fail(f"{path}.result", "must contain manifest and reproducibility records")
    if manifest.get("evaluation_role") != EVALUATION_ROLE:
        _fail(f"{path}.result.experiment_manifest", "role binding mismatch")
    if manifest.get("evaluation_protocol_hash") != protocol_sha256:
        _fail(f"{path}.result.experiment_manifest", "protocol binding mismatch")
    if manifest.get("evaluation_protocol_verified") is not False:
        _fail(f"{path}.result.experiment_manifest", "must remain unrankable")
    ranking_gate = manifest.get("ranking_gate")
    if (
        type(ranking_gate) is not dict
        or ranking_gate.get("status") != "BLOCK"
        or ranking_gate.get("input_allowed") is not False
    ):
        _fail(f"{path}.result.experiment_manifest", "ranking gate must remain BLOCK")
    denied_fields = {
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    for field, expected in denied_fields.items():
        if manifest.get(field) is not expected:
            _fail(f"{path}.result.experiment_manifest.{field}", "authority escalated")
    if manifest.get("research_only") is not True:
        _fail(f"{path}.result.experiment_manifest.research_only", "must be true")
    if reproducibility.get("data_rows") != ROW_COUNT:
        _fail(f"{path}.result.reproducibility.data_rows", "row count mismatch")


def _build_record(
    fixture: dict[str, Any],
    strategy_id: str,
    strategy_run: dict[str, Any],
    benchmark_run: dict[str, Any],
) -> dict[str, Any]:
    evidence = build_market_regime_evidence(
        fixture["records"],
        strategy_run["result"]["equity_curve"],
        benchmark_run["result"]["equity_curve"],
        dataset_sha256=fixture["dataset_sha256"],
        strategy_result_sha256=strategy_run["result_sha256"],
        benchmark_result_sha256=benchmark_run["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    receipt = verify_market_regime_evidence(
        evidence,
        fixture["records"],
        strategy_run["result"]["equity_curve"],
        benchmark_run["result"]["equity_curve"],
        dataset_sha256=fixture["dataset_sha256"],
        strategy_result_sha256=strategy_run["result_sha256"],
        benchmark_result_sha256=benchmark_run["result_sha256"],
        observation_class=OBSERVATION_CLASS,
    )
    target = next(
        observation
        for observation in evidence["observations"]
        if observation["regime_id"] == TARGET_REGIME_ID
    )
    if (
        target["status"] != "OBSERVED"
        or target["observation_count"] != EXPECTED_TARGET_OBSERVATION_COUNT
    ):
        _fail(strategy_id, "target high-volatility slice was not fully observed")
    payload = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "family_id": _family_for_strategy(strategy_id),
        "strategy_run": deepcopy(strategy_run),
        "strategy_run_sha256": strategy_run["run_sha256"],
        "benchmark_run_sha256": benchmark_run["run_sha256"],
        "market_regime_evidence": evidence,
        "market_regime_receipt": receipt,
        "target_regime_observation": deepcopy(target),
        "target_regime_state": "OBSERVED",
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    return _seal(payload, "record_sha256")


def build_synthetic_strategy_high_volatility_validation_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        _fail("execute", "must be exact bool")
    plan = plan_synthetic_strategy_high_volatility_validation_v1()
    if not execute:
        return plan

    frame, fixture = _build_fixture()
    benchmark_run = _run_backtest(
        run_id="benchmark:buy_and_hold:high_volatility_1x",
        evaluation_role=EVALUATION_ROLE,
        frame=frame,
        dataset_sha256=fixture["dataset_sha256"],
        cost_multiplier=1,
        strategy_factory=_BuyAndHoldBenchmark,
        protocol_sha256=plan["plan_sha256"],
    )
    strategy_records = []
    for strategy_id in plan["registered_strategy_ids"]:
        strategy_run = _run_backtest(
            run_id=f"{strategy_id}:high_volatility_1x",
            evaluation_role=EVALUATION_ROLE,
            frame=frame,
            dataset_sha256=fixture["dataset_sha256"],
            cost_multiplier=1,
            strategy_factory=lambda strategy_id=strategy_id: build_strategy(strategy_id),
            protocol_sha256=plan["plan_sha256"],
        )
        strategy_records.append(
            _build_record(fixture, strategy_id, strategy_run, benchmark_run)
        )

    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "plan": plan,
        "fixture": fixture,
        "fixture_sha256": fixture["fixture_sha256"],
        "benchmark_run": benchmark_run,
        "benchmark_run_sha256": benchmark_run["run_sha256"],
        "planned_run_count": plan["planned_run_count"],
        "executed_run_count": plan["planned_run_count"],
        "additional_backtest_run_count": plan["planned_run_count"],
        "executed_analysis_count": len(strategy_records),
        "target_regime_id": TARGET_REGIME_ID,
        "observed_target_slice_count": len(strategy_records),
        "gap_target_slice_count": 0,
        "strategy_records": strategy_records,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    bundle = _seal(payload, "bundle_sha256")
    verify_synthetic_strategy_high_volatility_validation_v1(bundle)
    return bundle


def verify_synthetic_strategy_high_volatility_validation_v1(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(bundle, "bundle")
    required_keys = {
        "schema_version",
        "data_source",
        "evidence_state",
        "maturity",
        "status",
        "plan",
        "fixture",
        "fixture_sha256",
        "benchmark_run",
        "benchmark_run_sha256",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "executed_analysis_count",
        "target_regime_id",
        "observed_target_slice_count",
        "gap_target_slice_count",
        "strategy_records",
        "runtime_mutations",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if set(bundle) != required_keys:
        _fail("bundle", "fields do not match the contract")
    if (
        bundle["schema_version"] != BUNDLE_SCHEMA_VERSION
        or bundle["data_source"] != DATA_SOURCE
    ):
        _fail("bundle", "identity mismatch")
    if (
        bundle["evidence_state"] != EVIDENCE_STATE
        or bundle["maturity"] != MATURITY
        or bundle["status"] != STATUS
    ):
        _fail("bundle", "must remain GAP/BLOCK synthetic scenario evidence")
    if bundle["gaps"] != _gaps() or bundle["authority"] != _authority():
        _fail("bundle", "gaps or authority drifted")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    verify_synthetic_strategy_high_volatility_validation_plan_v1(bundle["plan"])

    _, expected_fixture = _build_fixture()
    if bundle["fixture"] != expected_fixture:
        _fail("bundle.fixture", "does not match deterministic fixture")
    if bundle["fixture_sha256"] != expected_fixture["fixture_sha256"]:
        _fail("bundle.fixture_sha256", "binding mismatch")
    plan = bundle["plan"]
    if (
        bundle["planned_run_count"] != plan["planned_run_count"]
        or bundle["executed_run_count"] != plan["planned_run_count"]
        or bundle["additional_backtest_run_count"] != plan["planned_run_count"]
    ):
        _fail("bundle", "scenario run accounting drifted")
    _verify_run(
        bundle["benchmark_run"],
        expected_run_id="benchmark:buy_and_hold:high_volatility_1x",
        dataset_sha256=expected_fixture["dataset_sha256"],
        protocol_sha256=plan["plan_sha256"],
        path="bundle.benchmark_run",
    )
    if bundle["benchmark_run_sha256"] != bundle["benchmark_run"]["run_sha256"]:
        _fail("bundle.benchmark_run_sha256", "binding mismatch")

    strategy_records = bundle["strategy_records"]
    strategy_ids = plan["registered_strategy_ids"]
    if type(strategy_records) is not list or len(strategy_records) != len(strategy_ids):
        _fail("bundle.strategy_records", "coverage mismatch")
    for index, (strategy_id, record) in enumerate(zip(strategy_ids, strategy_records)):
        path = f"bundle.strategy_records[{index}]"
        if type(record) is not dict:
            _fail(path, "must be an exact dict")
        _verify_seal(record, "record_sha256", path)
        expected_record_keys = {
            "schema_version",
            "strategy_id",
            "family_id",
            "strategy_run",
            "strategy_run_sha256",
            "benchmark_run_sha256",
            "market_regime_evidence",
            "market_regime_receipt",
            "target_regime_observation",
            "target_regime_state",
            "evidence_state",
            "maturity",
            "status",
            "gaps",
            "authority",
            "record_sha256",
        }
        if set(record) != expected_record_keys:
            _fail(path, "record fields do not match the contract")
        if (
            record["schema_version"] != RECORD_SCHEMA_VERSION
            or record["strategy_id"] != strategy_id
            or record["family_id"] != _family_for_strategy(strategy_id)
        ):
            _fail(path, "strategy identity mismatch")
        if (
            record["evidence_state"] != EVIDENCE_STATE
            or record["maturity"] != MATURITY
            or record["status"] != STATUS
            or record["gaps"] != _gaps()
            or record["authority"] != _authority()
        ):
            _fail(path, "state or authority drifted")
        _verify_run(
            record["strategy_run"],
            expected_run_id=f"{strategy_id}:high_volatility_1x",
            dataset_sha256=expected_fixture["dataset_sha256"],
            protocol_sha256=plan["plan_sha256"],
            path=f"{path}.strategy_run",
        )
        if record["strategy_run_sha256"] != record["strategy_run"]["run_sha256"]:
            _fail(f"{path}.strategy_run_sha256", "binding mismatch")
        if record["benchmark_run_sha256"] != bundle["benchmark_run_sha256"]:
            _fail(f"{path}.benchmark_run_sha256", "binding mismatch")
        evidence = record["market_regime_evidence"]
        receipt = verify_market_regime_evidence(
            evidence,
            expected_fixture["records"],
            record["strategy_run"]["result"]["equity_curve"],
            bundle["benchmark_run"]["result"]["equity_curve"],
            dataset_sha256=expected_fixture["dataset_sha256"],
            strategy_result_sha256=record["strategy_run"]["result_sha256"],
            benchmark_result_sha256=bundle["benchmark_run"]["result_sha256"],
            observation_class=OBSERVATION_CLASS,
        )
        if record["market_regime_receipt"] != receipt:
            _fail(f"{path}.market_regime_receipt", "receipt mismatch")
        target = next(
            observation
            for observation in evidence["observations"]
            if observation["regime_id"] == TARGET_REGIME_ID
        )
        if record["target_regime_observation"] != target:
            _fail(f"{path}.target_regime_observation", "projection mismatch")
        if (
            record["target_regime_state"] != "OBSERVED"
            or target["status"] != "OBSERVED"
            or target["observation_count"] != EXPECTED_TARGET_OBSERVATION_COUNT
        ):
            _fail(path, "target high-volatility coverage drifted")

    if (
        bundle["executed_analysis_count"] != len(strategy_ids)
        or bundle["target_regime_id"] != TARGET_REGIME_ID
        or bundle["observed_target_slice_count"] != len(strategy_ids)
        or bundle["gap_target_slice_count"] != 0
    ):
        _fail("bundle", "target coverage accounting drifted")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "strategy_count": len(strategy_ids),
        "executed_run_count": bundle["executed_run_count"],
        "executed_analysis_count": bundle["executed_analysis_count"],
        "observed_target_slice_count": bundle["observed_target_slice_count"],
        "gap_target_slice_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "permission": STATUS,
        "authority": _authority(),
    }


def render_synthetic_strategy_high_volatility_validation_markdown_v1(
    bundle: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_high_volatility_validation_v1(bundle)
    rows = [
        "| Strategy | HIGH_VOLATILITY | Observations |",
        "| --- | --- | ---: |",
    ]
    for record in bundle["strategy_records"]:
        target = record["target_regime_observation"]
        rows.append(
            f"| {record['strategy_id']} | {target['status']} | "
            f"{target['observation_count']} |"
        )
    return "\n".join(
        (
            "# Synthetic Strategy High-Volatility Validation v1",
            "",
            "Non-current, synthetic scenario-only evidence.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {DATA_SOURCE} |",
            f"| GAP | {', '.join(bundle['gaps'])} |",
            f"| MATURITY | {MATURITY} |",
            f"| PERMISSION | {STATUS} |",
            "",
            *rows,
            "",
            f"- Scenario runs: {receipt['executed_run_count']}",
            f"- Target slices observed: {receipt['observed_target_slice_count']}/6",
            "- Formal inference: not authorized",
            "- Paper/live/order entry: not authorized",
            f"- Bundle SHA-256: `{bundle['bundle_sha256']}`",
        )
    )
