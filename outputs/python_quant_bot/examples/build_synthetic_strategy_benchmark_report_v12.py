"""Compose non-current benchmark v12 with input-pathology evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v11 import (
    plan_synthetic_strategy_benchmark_report_v11,
    verify_synthetic_strategy_benchmark_report_v11,
)
from exchange_terminal.application.synthetic_strategy_input_pathology_v1 import (
    plan_synthetic_strategy_input_pathology_v1,
    verify_synthetic_strategy_input_pathology_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v12"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v12"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v12"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v12"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_INPUT_PATHOLOGY_GATE"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_BENCHMARK_WITH_INPUT_PATHOLOGY_AND_REMAINING_GAPS"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 222
TOTAL_LOGICAL_RUN_COUNT = 222
_REPLACED_GAP = "LIQUIDITY_CAPACITY_NOT_MODELLED"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must contain finite native floats")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    raise TypeError(f"{path} must use exact native JSON types")


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


def _combined_gaps(
    source_plan: dict[str, Any], pathology_plan: dict[str, Any]
) -> list[str]:
    if _REPLACED_GAP not in source_plan["gaps"]:
        raise ValueError("v12 source must retain the liquidity-capacity gap")
    retained = [gap for gap in source_plan["gaps"] if gap != _REPLACED_GAP]
    return sorted(set(retained).union(pathology_plan["gaps"]))


def plan_synthetic_strategy_benchmark_report_v12() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v11()
    pathology_plan = plan_synthetic_strategy_input_pathology_v1()
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "replaced_gap": _REPLACED_GAP,
        "source_report_plan": copy.deepcopy(source_plan),
        "input_pathology_plan": copy.deepcopy(pathology_plan),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "pathology_evaluation_count": pathology_plan[
            "pathology_evaluation_count"
        ],
        "capacity_probe_count": pathology_plan["capacity_probe_count"],
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_module_file_count": pathology_plan[
            "source_module_file_count"
        ],
        "dependency_lock_sha256": source_plan["dependency_lock_sha256"],
        "source_extension_manifest_sha256": pathology_plan[
            "source_extension_manifest"
        ]["source_extension_manifest_sha256"],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, pathology_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v12(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json(plan)
    expected = plan_synthetic_strategy_benchmark_report_v12()
    if plan != expected:
        raise ValueError("synthetic benchmark v12 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v11: dict[str, Any], pathology_bundle: dict[str, Any]
) -> None:
    if type(source_report_v11) is not dict or type(pathology_bundle) is not dict:
        raise TypeError("v12 sources must be exact native dicts")
    _require_exact_json(source_report_v11, path="$.source_report_v11")
    _require_exact_json(pathology_bundle, path="$.pathology_bundle")
    verify_synthetic_strategy_benchmark_report_v11(source_report_v11)
    verify_synthetic_strategy_input_pathology_v1(
        pathology_bundle, source_report_v11
    )
    if (
        source_report_v11["total_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT
        or pathology_bundle["source_logical_run_count"]
        != SOURCE_LOGICAL_RUN_COUNT
        or pathology_bundle["source_report_v11_sha256"]
        != source_report_v11["report_sha256"]
        or pathology_bundle["additional_backtest_run_count"] != 0
        or pathology_bundle["total_logical_run_count"] != TOTAL_LOGICAL_RUN_COUNT
    ):
        raise ValueError("v12 source binding or run accounting drifted")
    if source_report_v11["authority"] != _AUTHORITY:
        raise ValueError("benchmark v11 authority must remain denied")
    if pathology_bundle["authority"] != _AUTHORITY:
        raise ValueError("input-pathology authority must remain denied")


def _compose_report(
    source_report_v11: dict[str, Any],
    pathology_bundle: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v11": copy.deepcopy(source_report_v11),
        "input_pathology_bundle": copy.deepcopy(pathology_bundle),
        "bindings": {
            "source_report_v11_sha256": source_report_v11["report_sha256"],
            "source_report_v11_plan_sha256": source_report_v11["plan"][
                "plan_sha256"
            ],
            "input_pathology_bundle_sha256": pathology_bundle["bundle_sha256"],
            "input_pathology_plan_sha256": pathology_bundle["plan"][
                "plan_sha256"
            ],
            "source_baseline_bundle_sha256": pathology_bundle[
                "source_baseline_bundle_sha256"
            ],
            "dependency_lock_sha256": pathology_bundle[
                "dependency_lock_sha256"
            ],
            "source_extension_manifest_sha256": pathology_bundle[
                "source_extension_manifest"
            ]["source_extension_manifest_sha256"],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "pathology_evaluation_count": pathology_bundle[
            "pathology_evaluation_count"
        ],
        "capacity_probe_count": pathology_bundle["capacity_probe_count"],
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "source_module_file_count": plan["source_module_file_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": copy.deepcopy(plan["gaps"]),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "report_sha256")


def build_synthetic_strategy_benchmark_report_v12(
    source_report_v11: dict[str, Any] | None = None,
    pathology_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v11 is not None or pathology_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v12()
    if source_report_v11 is None or pathology_bundle is None:
        raise ValueError("execute=True requires both prebuilt v12 sources")
    _verify_sources(source_report_v11, pathology_bundle)
    return _compose_report(
        source_report_v11,
        pathology_bundle,
        plan_synthetic_strategy_benchmark_report_v12(),
    )


def verify_synthetic_strategy_benchmark_report_v12(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v12 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v12(plan)
    source_report_v11 = report.get("source_report_v11")
    pathology_bundle = report.get("input_pathology_bundle")
    if type(source_report_v11) is not dict or type(pathology_bundle) is not dict:
        raise TypeError("report must embed both exact native v12 sources")
    _verify_sources(source_report_v11, pathology_bundle)
    expected = _compose_report(source_report_v11, pathology_bundle, plan)
    if report != expected:
        raise ValueError("synthetic benchmark v12 report verification failed")
    return _seal(
        {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "report_id": REPORT_ID,
            "report_sha256": report["report_sha256"],
            "plan_sha256": plan["plan_sha256"],
            "source_report_v11_sha256": report["bindings"][
                "source_report_v11_sha256"
            ],
            "input_pathology_bundle_sha256": report["bindings"][
                "input_pathology_bundle_sha256"
            ],
            "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
            "pathology_evaluation_count": report[
                "pathology_evaluation_count"
            ],
            "capacity_probe_count": report["capacity_probe_count"],
            "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
            "source_module_file_count": report["source_module_file_count"],
            "composition_executed_run_count": 0,
            "additional_backtest_run_count": 0,
            "evidence_state": EVIDENCE_STATE,
            "maturity": MATURITY,
            "status": STATUS,
            "authority": copy.deepcopy(_AUTHORITY),
            "runtime_mutations": False,
        },
        "receipt_sha256",
    )


def render_synthetic_strategy_benchmark_report_plan_markdown_v12(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v12(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v12",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited logical runs: {plan['source_logical_run_count']}",
        f"- Input-pathology evaluations: {plan['pathology_evaluation_count']}",
        f"- Static capacity probes: {plan['capacity_probe_count']}",
        "- V12 composition executes no additional backtests.",
        "",
        "## GAP",
        *[f"- {gap}" for gap in plan["gaps"]],
        "",
        "## MATURITY",
        f"- {plan['maturity']}",
        "- Input pathology and capacity evidence remains pure synthetic.",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    return "\n".join(lines) + "\n"


def render_synthetic_strategy_benchmark_report_markdown_v12(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v12(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v12",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited logical runs: {report['source_logical_run_count']}",
        f"- Input-pathology evaluations: {report['pathology_evaluation_count']}",
        f"- Static capacity probes: {report['capacity_probe_count']}",
        "- New backtest runs: 0",
        "",
        "## GAP",
        *[f"- {gap}" for gap in report["gaps"]],
        "",
        "## MATURITY",
        f"- {report['maturity']}",
        "- Missing interval and invalid OHLC probes fail closed before research use.",
        "- Static participation capacity is not partial-fill or rejection execution.",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    return "\n".join(lines) + "\n"


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the non-current synthetic benchmark v12 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v12(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v12(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
