"""Source-bound synthetic input-pathology and static-capacity evidence."""

from __future__ import annotations

import copy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from examples.build_synthetic_strategy_benchmark_report_v11 import (
    plan_synthetic_strategy_benchmark_report_v11,
    verify_synthetic_strategy_benchmark_report_v11,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    _new_config,
)
from exchange_terminal.application.synthetic_strategy_execution_adversity_v1 import (
    _find_baseline_bundle,
    _frozen_frame,
    _strategy_report_map,
)
from hakimi_research.synthetic_input_pathology_gate import (
    SyntheticInputPathologyGateError,
    evaluate_synthetic_input_pathology_gate_v1,
    synthetic_input_pathology_policy_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-input-pathology-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-input-pathology-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-input-pathology-receipt-v1"
EVIDENCE_STATE = "GAP"
MATURITY = "PURE_SYNTHETIC_INPUT_PATHOLOGY_AND_STATIC_CAPACITY_DIAGNOSTIC"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 222
TOTAL_LOGICAL_RUN_COUNT = 222
PATHOLOGY_EVALUATION_COUNT = 4
MUTATION_INDEX = 100
SCENARIO_IDS = [
    "source_frozen_control",
    "missing_internal_bar",
    "ohlc_envelope_breach",
    "insufficient_static_volume_capacity",
]
EXPECTED_STRATEGY_IDS = [
    "bollinger",
    "dual_ma",
    "grid",
    "macd",
    "momentum",
    "rsi",
]

_GAPS = [
    "CAPACITY_PROBE_MAX_POSITION_NOT_ACTUAL_ORDER_INTENT",
    "MISSING_INTERVAL_AND_OHLC_PATHOLOGY_SYNTHETIC_ONLY",
    "ORDER_REJECTION_NOT_MODELLED",
    "PARTIAL_FILL_NOT_MODELLED",
    "STATIC_VOLUME_PARTICIPATION_CAPACITY_ONLY",
    "VENUE_DEPTH_LOT_SIZE_AND_QUEUE_NOT_MODELLED",
    "VOLUME_UNIT_SEMANTICS_SYNTHETIC_ONLY",
]

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyInputPathologyError(ValueError):
    """Raised when source-bound pathology evidence fails closed."""


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyInputPathologyError(f"{path}: {message}")


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "float must be finite")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "dict keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    _fail(path, "value must use exact native JSON types")


def _sha256_json(value: Any) -> str:
    _require_exact_json(value)
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = copy.deepcopy(unsigned)
    result[field] = _sha256_json(unsigned)
    return result


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _source_extension_manifest() -> dict[str, Any]:
    root = _repo_root()
    paths = [
        "src/hakimi_research/synthetic_input_pathology_gate.py",
        "outputs/python_quant_bot/exchange_terminal/application/synthetic_strategy_input_pathology_v1.py",
        "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v12.py",
    ]
    files = []
    for relative_path in paths:
        payload = (root / relative_path).read_bytes()
        files.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return _seal(
        {"schema_version": "source-extension-manifest-v12", "file_count": 3, "files": files},
        "source_extension_manifest_sha256",
    )


def _frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        timestamp = pd.Timestamp(index)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        records.append(
            {
                "time": timestamp.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )
    return records


def _scenario(
    scenario_id: str,
    mutation: dict[str, Any],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    return _seal(
        {
            "scenario_id": scenario_id,
            "mutation": mutation,
            "evaluation": evaluation,
            "runtime_mutations": False,
            "authority": copy.deepcopy(_AUTHORITY),
        },
        "scenario_sha256",
    )


def plan_synthetic_strategy_input_pathology_v1() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v11()
    strategy_ids = source_plan["execution_adversity_plan"][
        "registered_strategy_ids"
    ]
    if strategy_ids != EXPECTED_STRATEGY_IDS:
        _fail("strategy_ids", "expected the fixed six-strategy source registry")
    source_manifest = _source_extension_manifest()
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": "PURE_SYNTHETIC_FROZEN_IN_MEMORY",
        "requires_exact_execute_true": True,
        "requires_prebuilt_v11_report": True,
        "source_report_v11_plan_sha256": source_plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "pathology_evaluation_count": PATHOLOGY_EVALUATION_COUNT,
        "capacity_probe_count": len(strategy_ids),
        "additional_backtest_run_count": 0,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "registered_strategy_ids": list(strategy_ids),
        "scenario_ids": list(SCENARIO_IDS),
        "mutation_index": MUTATION_INDEX,
        "policy": synthetic_input_pathology_policy_v1(),
        "source_extension_manifest": source_manifest,
        "source_module_file_count": source_plan["source_module_file_count"]
        + source_manifest["file_count"],
        "gaps": list(_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
    }
    return _seal(payload, "plan_sha256")


def _compose_bundle(
    source_report_v11: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    source_report_v10 = source_report_v11["source_report_v10"]
    baseline = _find_baseline_bundle(source_report_v10)
    frame = _frozen_frame(baseline)
    records = _frame_records(frame)
    if len(records) != 200:
        _fail("source_frozen", "expected the preregistered 200-row partition")
    strategy_reports = _strategy_report_map(baseline)
    engine_hashes = {
        strategy_reports[strategy_id]["runs"]["frozen_1x"]["result"][
            "reproducibility"
        ]["data_hash"]
        for strategy_id in EXPECTED_STRATEGY_IDS
    }
    if len(engine_hashes) != 1:
        _fail("source_frozen", "engine input hashes drifted across strategies")
    source_engine_hash = next(iter(engine_hashes))
    policy = plan["policy"]

    try:
        control = evaluate_synthetic_input_pathology_gate_v1(records, policy, [])
        missing_records = copy.deepcopy(records)
        removed = missing_records.pop(MUTATION_INDEX)
        missing = evaluate_synthetic_input_pathology_gate_v1(
            missing_records, policy, []
        )
        ohlc_records = copy.deepcopy(records)
        original_high = ohlc_records[MUTATION_INDEX]["high"]
        ohlc_records[MUTATION_INDEX]["high"] = (
            min(
                ohlc_records[MUTATION_INDEX]["open"],
                ohlc_records[MUTATION_INDEX]["close"],
            )
            * 0.5
        )
        ohlc = evaluate_synthetic_input_pathology_gate_v1(
            ohlc_records, policy, []
        )
        capacity_records = copy.deepcopy(records)
        config = _new_config()
        close_price = Decimal(str(capacity_records[MUTATION_INDEX]["close"]))
        probe_notional = Decimal(str(config.initial_cash)) * Decimal(
            str(config.risk.max_position_pct)
        )
        requested_quantity = probe_notional / close_price
        max_participation = Decimal(policy["max_participation_rate"])
        original_volume = capacity_records[MUTATION_INDEX]["volume"]
        capacity_records[MUTATION_INDEX]["volume"] = float(
            requested_quantity * Decimal("0.5") / max_participation
        )
        probe_time = capacity_records[MUTATION_INDEX]["time"]
        probes = [
            {
                "probe_id": f"{strategy_id}:max_position_capacity_probe",
                "strategy_id": strategy_id,
                "time": probe_time,
                "requested_quantity": format(requested_quantity, "f"),
            }
            for strategy_id in EXPECTED_STRATEGY_IDS
        ]
        capacity = evaluate_synthetic_input_pathology_gate_v1(
            capacity_records, policy, probes
        )
    except SyntheticInputPathologyGateError as exc:
        _fail("core_gate", str(exc))

    if not control["accepted"] or control["issue_codes"]:
        _fail("source_frozen_control", "source Frozen frame must pass")
    if missing["issue_codes"] != ["MISSING_INTERVAL"]:
        _fail("missing_internal_bar", "must identify one missing interval")
    if ohlc["issue_codes"] != ["OHLC_ENVELOPE_VIOLATION"]:
        _fail("ohlc_envelope_breach", "must identify the OHLC violation")
    if (
        capacity["data_accepted"] is not True
        or capacity["capacity_accepted"] is not False
        or capacity["insufficient_capacity_probe_count"]
        != len(EXPECTED_STRATEGY_IDS)
    ):
        _fail("insufficient_static_volume_capacity", "capacity probe drifted")

    scenarios = [
        _scenario("source_frozen_control", {"kind": "NONE"}, control),
        _scenario(
            "missing_internal_bar",
            {
                "kind": "DROP_INTERNAL_RECORD",
                "record_index": MUTATION_INDEX,
                "removed_time": removed["time"],
            },
            missing,
        ),
        _scenario(
            "ohlc_envelope_breach",
            {
                "kind": "LOWER_HIGH_BELOW_OPEN_AND_CLOSE",
                "record_index": MUTATION_INDEX,
                "time": ohlc_records[MUTATION_INDEX]["time"],
                "source_high": format(Decimal(str(original_high)), "f"),
                "mutated_high": format(
                    Decimal(str(ohlc_records[MUTATION_INDEX]["high"])), "f"
                ),
            },
            ohlc,
        ),
        _scenario(
            "insufficient_static_volume_capacity",
            {
                "kind": "SET_VOLUME_TO_HALF_MAX_POSITION_CAPACITY",
                "record_index": MUTATION_INDEX,
                "time": probe_time,
                "source_volume": format(Decimal(str(original_volume)), "f"),
                "mutated_volume": format(
                    Decimal(str(capacity_records[MUTATION_INDEX]["volume"])),
                    "f",
                ),
                "probe_notional": format(probe_notional, "f"),
                "max_participation_rate": policy["max_participation_rate"],
            },
            capacity,
        ),
    ]
    frozen_partition = baseline["fixture"]["partition_protocol"]["partitions"][
        "frozen"
    ]
    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "plan": copy.deepcopy(plan),
        "source_report_v11_sha256": source_report_v11["report_sha256"],
        "source_report_v11_plan_sha256": source_report_v11["plan"][
            "plan_sha256"
        ],
        "source_baseline_bundle_sha256": baseline["bundle_sha256"],
        "source_frozen_partition_dataset_sha256": frozen_partition[
            "dataset_sha256"
        ],
        "source_frozen_engine_input_sha256": source_engine_hash,
        "source_frozen_row_count": frozen_partition["row_count"],
        "dependency_lock_sha256": source_report_v11["bindings"][
            "dependency_lock_sha256"
        ],
        "source_extension_manifest": copy.deepcopy(
            plan["source_extension_manifest"]
        ),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "pathology_evaluation_count": len(scenarios),
        "capacity_probe_count": len(probes),
        "additional_backtest_run_count": 0,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "scenarios": scenarios,
        "gaps": list(_GAPS),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
    }
    return _seal(payload, "bundle_sha256")


def build_synthetic_strategy_input_pathology_v1(
    source_report_v11: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v11 is not None:
            raise ValueError("plan-only mode does not accept a source report")
        return plan_synthetic_strategy_input_pathology_v1()
    if source_report_v11 is None:
        raise ValueError("execute=True requires a prebuilt v11 report")
    try:
        verify_synthetic_strategy_benchmark_report_v11(source_report_v11)
    except Exception as exc:
        _fail("source_report_v11", f"verification failed:{type(exc).__name__}:{exc}")
    return _compose_bundle(
        source_report_v11, plan_synthetic_strategy_input_pathology_v1()
    )


def verify_synthetic_strategy_input_pathology_v1(
    bundle: dict[str, Any], source_report_v11: dict[str, Any]
) -> dict[str, Any]:
    if type(bundle) is not dict:
        raise TypeError("bundle must be an exact native dict")
    _require_exact_json(bundle, path="bundle")
    try:
        verify_synthetic_strategy_benchmark_report_v11(source_report_v11)
    except Exception as exc:
        _fail("source_report_v11", f"verification failed:{type(exc).__name__}:{exc}")
    plan = plan_synthetic_strategy_input_pathology_v1()
    expected = _compose_bundle(source_report_v11, plan)
    if bundle != expected:
        _fail("bundle", "must match deterministic source-bound pathology evidence")
    return _seal(
        {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "bundle_sha256": bundle["bundle_sha256"],
            "source_report_v11_sha256": bundle["source_report_v11_sha256"],
            "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
            "pathology_evaluation_count": PATHOLOGY_EVALUATION_COUNT,
            "capacity_probe_count": len(EXPECTED_STRATEGY_IDS),
            "additional_backtest_run_count": 0,
            "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
            "evidence_state": EVIDENCE_STATE,
            "maturity": MATURITY,
            "status": STATUS,
            "authority": copy.deepcopy(_AUTHORITY),
            "runtime_mutations": False,
        },
        "receipt_sha256",
    )


def replay_synthetic_strategy_input_pathology_v1(
    bundle: dict[str, Any], source_report_v11: dict[str, Any]
) -> dict[str, Any]:
    receipt = verify_synthetic_strategy_input_pathology_v1(
        bundle, source_report_v11
    )
    replayed = build_synthetic_strategy_input_pathology_v1(
        source_report_v11, execute=True
    )
    if replayed != bundle:
        _fail("replay", "deterministic pathology replay mismatch")
    output = dict(receipt)
    output["replay_status"] = "EXACT_MATCH"
    return output


def render_synthetic_strategy_input_pathology_markdown_v1(
    bundle: dict[str, Any], source_report_v11: dict[str, Any]
) -> str:
    receipt = verify_synthetic_strategy_input_pathology_v1(
        bundle, source_report_v11
    )
    lines = [
        "# Synthetic Strategy Input Pathology v1",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Pathology evaluations: {receipt['pathology_evaluation_count']}",
        f"- Static capacity probes: {receipt['capacity_probe_count']}",
        "- New backtest runs: 0",
        "",
        "## GAP",
        *[f"- {gap}" for gap in bundle["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Missing interval and OHLC envelope probes fail closed.",
        "- Static capacity is an upper-bound diagnostic, not an execution model.",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    markdown = "\n".join(lines) + "\n"
    for forbidden in ("Profitability proven: TRUE", "Paper authority: TRUE"):
        if forbidden in markdown:
            _fail("renderer", f"neutral token violation:{forbidden}")
    return markdown
