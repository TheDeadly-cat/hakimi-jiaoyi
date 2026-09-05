"""Compose non-current benchmark v11 with execution-adversity evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v10 import (
    plan_synthetic_strategy_benchmark_report_v10,
    verify_synthetic_strategy_benchmark_report_v10,
)
from exchange_terminal.application.synthetic_strategy_execution_adversity_v1 import (
    plan_synthetic_strategy_execution_adversity_v1,
    verify_synthetic_strategy_execution_adversity_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v11"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v11"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v11"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v11"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_EXECUTION_ADVERSITY"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_BENCHMARK_WITH_EXECUTION_ADVERSITY_AND_REMAINING_GAPS"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 204
ADDITIONAL_RUN_COUNT = 18
TOTAL_LOGICAL_RUN_COUNT = 222
_REPLACED_GAP = "TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


def _require_exact_json_value(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must contain only finite native floats")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json_value(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} keys must be exact native strings")
            _require_exact_json_value(item, path=f"{path}.{key}")
        return
    raise TypeError(f"{path} must use exact native JSON value types")


def _sha256_json(value: Any) -> str:
    _require_exact_json_value(value)
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _with_sha256(payload: dict[str, Any], field: str) -> dict[str, Any]:
    _require_exact_json_value(payload)
    result = copy.deepcopy(payload)
    result[field] = _sha256_json(payload)
    return result


def _combined_gaps(
    source_plan: dict[str, Any], adversity_plan: dict[str, Any]
) -> list[str]:
    source_gaps = source_plan["gaps"]
    adversity_gaps = adversity_plan["gaps"]
    if _REPLACED_GAP not in source_gaps:
        raise ValueError("v11 source must retain the execution-model gap")
    retained = [gap for gap in source_gaps if gap != _REPLACED_GAP]
    return sorted(set(retained).union(adversity_gaps))


def plan_synthetic_strategy_benchmark_report_v11() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v10()
    adversity_plan = plan_synthetic_strategy_execution_adversity_v1()
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "replaced_gap": _REPLACED_GAP,
        "source_report_plan": copy.deepcopy(source_plan),
        "execution_adversity_plan": copy.deepcopy(adversity_plan),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "execution_adversity_additional_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_module_file_count": (
            source_plan["research_lock_audit_plan"]["source_manifest"][
                "module_file_count"
            ]
            + adversity_plan["source_extension_manifest"]["file_count"]
        ),
        "dependency_lock_sha256": source_plan["dependency_lock_sha256"],
        "source_extension_manifest_sha256": adversity_plan[
            "source_extension_manifest"
        ]["source_extension_manifest_sha256"],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, adversity_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v11(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v11()
    if plan != expected:
        raise ValueError("synthetic benchmark v11 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v10: dict[str, Any], adversity_bundle: dict[str, Any]
) -> None:
    if type(source_report_v10) is not dict or type(adversity_bundle) is not dict:
        raise TypeError("v11 sources must be exact native dicts")
    _require_exact_json_value(source_report_v10, path="$.source_report_v10")
    _require_exact_json_value(adversity_bundle, path="$.adversity_bundle")
    verify_synthetic_strategy_benchmark_report_v10(source_report_v10)
    verify_synthetic_strategy_execution_adversity_v1(
        adversity_bundle, source_report_v10
    )
    if (
        source_report_v10["source_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT
        or adversity_bundle["source_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT
        or adversity_bundle["source_report_v10_sha256"]
        != source_report_v10["report_sha256"]
        or adversity_bundle["executed_run_count"] != ADDITIONAL_RUN_COUNT
        or adversity_bundle["additional_backtest_run_count"]
        != ADDITIONAL_RUN_COUNT
        or adversity_bundle["total_logical_run_count"] != TOTAL_LOGICAL_RUN_COUNT
    ):
        raise ValueError("v11 source binding or run accounting drifted")
    if source_report_v10["authority"] != _AUTHORITY:
        raise ValueError("benchmark v10 authority must remain denied")
    if adversity_bundle["authority"] != _AUTHORITY:
        raise ValueError("execution-adversity authority must remain denied")
    if (
        source_report_v10["runtime_mutations"] is not False
        or adversity_bundle["runtime_mutations"] is not False
    ):
        raise ValueError("v11 sources must not mutate runtime state")


def _compose_report(
    source_report_v10: dict[str, Any],
    adversity_bundle: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v10": copy.deepcopy(source_report_v10),
        "execution_adversity_bundle": copy.deepcopy(adversity_bundle),
        "bindings": {
            "source_report_v10_sha256": source_report_v10["report_sha256"],
            "source_report_v10_plan_sha256": source_report_v10["plan"][
                "plan_sha256"
            ],
            "execution_adversity_bundle_sha256": adversity_bundle[
                "bundle_sha256"
            ],
            "execution_adversity_plan_sha256": adversity_bundle["plan"][
                "plan_sha256"
            ],
            "source_baseline_bundle_sha256": adversity_bundle[
                "source_baseline_bundle_sha256"
            ],
            "dependency_lock_sha256": adversity_bundle[
                "dependency_lock_sha256"
            ],
            "source_extension_manifest_sha256": adversity_bundle[
                "source_extension_manifest"
            ]["source_extension_manifest_sha256"],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "execution_adversity_additional_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "source_module_file_count": plan["source_module_file_count"],
        "scenario_count": len(adversity_bundle["plan"]["scenario_ids"]),
        "strategy_count": len(
            adversity_bundle["plan"]["registered_strategy_ids"]
        ),
        "no_adverse_open_event_strategy_count": adversity_bundle[
            "no_adverse_open_event_strategy_count"
        ],
        "no_dropped_signal_strategy_count": adversity_bundle[
            "no_dropped_signal_strategy_count"
        ],
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
    return _with_sha256(payload, "report_sha256")


def build_synthetic_strategy_benchmark_report_v11(
    source_report_v10: dict[str, Any] | None = None,
    adversity_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v10 is not None or adversity_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v11()
    if source_report_v10 is None or adversity_bundle is None:
        raise ValueError("execute=True requires both prebuilt v11 sources")
    _verify_sources(source_report_v10, adversity_bundle)
    return _compose_report(
        source_report_v10,
        adversity_bundle,
        plan_synthetic_strategy_benchmark_report_v11(),
    )


def verify_synthetic_strategy_benchmark_report_v11(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v11 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v11(plan)
    source_report_v10 = report.get("source_report_v10")
    adversity_bundle = report.get("execution_adversity_bundle")
    if type(source_report_v10) is not dict or type(adversity_bundle) is not dict:
        raise TypeError("report must embed both exact native v11 sources")
    _verify_sources(source_report_v10, adversity_bundle)
    expected = _compose_report(source_report_v10, adversity_bundle, plan)
    if report != expected:
        raise ValueError("synthetic benchmark v11 report verification failed")
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v10_sha256": report["bindings"][
            "source_report_v10_sha256"
        ],
        "execution_adversity_bundle_sha256": report["bindings"][
            "execution_adversity_bundle_sha256"
        ],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "execution_adversity_additional_run_count": ADDITIONAL_RUN_COUNT,
        "total_logical_run_count": TOTAL_LOGICAL_RUN_COUNT,
        "source_module_file_count": report["source_module_file_count"],
        "scenario_count": report["scenario_count"],
        "strategy_count": report["strategy_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v11(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v11(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v11",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited benchmark v10 logical runs: {plan['source_logical_run_count']}",
        f"- Planned execution-adversity runs: {plan['execution_adversity_additional_run_count']}",
        f"- Total logical runs: {plan['total_logical_run_count']}",
        "- V11 composition executes no additional backtests.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- Execution adversity remains pure synthetic evidence.",
            "",
            "## PERMISSION",
            "- Paper authority: FALSE",
            "- Live authority: FALSE",
            "- Order-entry authority: FALSE",
            "- Formal inference authority: FALSE",
            "- Profitability proven: FALSE",
        ]
    )
    return "\n".join(lines) + "\n"


def render_synthetic_strategy_benchmark_report_markdown_v11(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v11(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v11",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited benchmark v10 logical runs: {report['source_logical_run_count']}",
        f"- Execution-adversity runs: {report['execution_adversity_additional_run_count']}",
        f"- Total logical runs: {report['total_logical_run_count']}",
        f"- Strategies: {report['strategy_count']}; scenarios: {report['scenario_count']}",
        "- V11 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            "- Additional delay, deterministic signal-drop, and adverse-open scenarios are observed.",
            "- Partial fills, capacity, rejection, and dynamic market impact remain unmodelled.",
            "- No decision threshold or formal inference is established.",
            "",
            "## PERMISSION",
            "- Paper authority: FALSE",
            "- Live authority: FALSE",
            "- Order-entry authority: FALSE",
            "- Formal inference authority: FALSE",
            "- Profitability proven: FALSE",
        ]
    )
    return "\n".join(lines) + "\n"


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the non-current synthetic benchmark v11 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v11(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v11(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
