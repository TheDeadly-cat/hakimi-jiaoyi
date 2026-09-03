"""Compose non-current benchmark v8 with independent control evidence.

V8 consumes a verified benchmark v7 report and a verified benchmark-controls
bundle. It binds their shared 32-run baseline without counting those runs
twice. The composition itself executes no backtest, mutates no runtime state,
and grants no trading, profitability, blind-test, or inference authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v7 import (
    plan_synthetic_strategy_benchmark_report_v7,
    verify_synthetic_strategy_benchmark_report_v7,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (
    plan_synthetic_strategy_benchmark_controls_v1,
    verify_synthetic_strategy_benchmark_controls_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v8"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v8"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v8"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v8"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_LOCAL_SOURCE_FILES_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_PROVENANCE_CONCENTRATION_AND_"
    "INDEPENDENT_CONTROL_GAPS"
)
STATUS = "BLOCK"

INHERITED_SOURCE_LOGICAL_RUN_COUNT = 186
SHARED_BASELINE_REUSED_RUN_COUNT = 32
INDEPENDENT_CONTROL_RUN_COUNT = 18
TOTAL_SOURCE_LOGICAL_RUN_COUNT = 204
CONTROL_ANALYSIS_COUNT = 13
_EXPECTED_CONTROL_IDS = [
    "simple_ma",
    "simple_breakout",
    *[f"hash_no_skill_{index:02d}" for index in range(16)],
]

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
    source_plan: dict[str, Any], controls_plan: dict[str, Any]
) -> list[str]:
    source_gaps = source_plan.get("gaps")
    control_gaps = controls_plan.get("gaps")
    if type(source_gaps) is not list or type(control_gaps) is not list:
        raise ValueError("v8 source plans must expose exact gap lists")
    if any(type(item) is not str for item in source_gaps + control_gaps):
        raise TypeError("v8 source plan gaps must be exact native strings")
    return sorted(set(source_gaps).union(control_gaps))


def _baseline_references(
    value: Any, baseline_sha256: str
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    if type(value) is dict:
        if value.get("bundle_sha256") == baseline_sha256:
            references.append(value)
        for item in value.values():
            references.extend(_baseline_references(item, baseline_sha256))
    elif type(value) is list:
        for item in value:
            references.extend(_baseline_references(item, baseline_sha256))
    return references


def plan_synthetic_strategy_benchmark_report_v8() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v7()
    controls_plan = plan_synthetic_strategy_benchmark_controls_v1()
    _require_exact_json_value(source_plan, path="$.source_report_plan")
    _require_exact_json_value(controls_plan, path="$.benchmark_controls_plan")
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "requires_shared_baseline_bundle_identity": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "benchmark_controls_plan": copy.deepcopy(controls_plan),
        "inherited_source_logical_run_count": (
            INHERITED_SOURCE_LOGICAL_RUN_COUNT
        ),
        "shared_baseline_reused_run_count": SHARED_BASELINE_REUSED_RUN_COUNT,
        "independent_control_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "source_logical_run_count": TOTAL_SOURCE_LOGICAL_RUN_COUNT,
        "planned_control_analysis_count": CONTROL_ANALYSIS_COUNT,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, controls_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v8(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v8()
    if plan != expected:
        raise ValueError("synthetic benchmark v8 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": TOTAL_SOURCE_LOGICAL_RUN_COUNT,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v7: dict[str, Any],
    benchmark_controls_bundle: dict[str, Any],
) -> int:
    if type(source_report_v7) is not dict:
        raise TypeError("source_report_v7 must be an exact native dict")
    if type(benchmark_controls_bundle) is not dict:
        raise TypeError(
            "benchmark_controls_bundle must be an exact native dict"
        )
    _require_exact_json_value(source_report_v7, path="$.source_report_v7")
    _require_exact_json_value(
        benchmark_controls_bundle, path="$.benchmark_controls_bundle"
    )
    verify_synthetic_strategy_benchmark_report_v7(source_report_v7)
    verify_synthetic_strategy_benchmark_controls_v1(
        benchmark_controls_bundle
    )

    if (
        source_report_v7["source_logical_run_count"]
        != INHERITED_SOURCE_LOGICAL_RUN_COUNT
    ):
        raise ValueError("v7 logical source run count drifted")
    expected_control_counts = {
        "source_reused_run_count": SHARED_BASELINE_REUSED_RUN_COUNT,
        "planned_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "executed_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "additional_backtest_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "executed_analysis_count": CONTROL_ANALYSIS_COUNT,
    }
    for field, expected in expected_control_counts.items():
        if benchmark_controls_bundle.get(field) != expected:
            raise ValueError(f"benchmark controls {field} drifted")

    runs = benchmark_controls_bundle.get("control_runs")
    if type(runs) is not list or [run.get("control_id") for run in runs] != (
        _EXPECTED_CONTROL_IDS
    ):
        raise ValueError("independent control run identity or order drifted")

    baseline = benchmark_controls_bundle.get("source_baseline_bundle")
    if type(baseline) is not dict:
        raise TypeError("controls must embed an exact native baseline bundle")
    baseline_sha256 = benchmark_controls_bundle.get(
        "source_baseline_bundle_sha256"
    )
    if (
        type(baseline_sha256) is not str
        or baseline.get("bundle_sha256") != baseline_sha256
    ):
        raise ValueError("control baseline SHA-256 binding drifted")
    references = _baseline_references(source_report_v7, baseline_sha256)
    if not references:
        raise ValueError("v7 does not embed the control source baseline")
    if any(reference != baseline for reference in references):
        raise ValueError("shared baseline digest aliases unequal artifacts")

    if source_report_v7["authority"] != _AUTHORITY:
        raise ValueError("benchmark v7 authority must remain denied")
    if benchmark_controls_bundle["authority"] != _AUTHORITY:
        raise ValueError("benchmark controls authority must remain denied")
    if source_report_v7["runtime_mutations"] is not False:
        raise ValueError("benchmark v7 runtime mutations must remain false")
    if benchmark_controls_bundle["runtime_mutations"] is not False:
        raise ValueError("benchmark controls runtime mutations must remain false")
    if source_report_v7["status"] != STATUS:
        raise ValueError("benchmark v7 must remain blocked")
    if benchmark_controls_bundle["status"] != STATUS:
        raise ValueError("benchmark controls must remain blocked")
    return len(references)


def _compose_report(
    source_report_v7: dict[str, Any],
    benchmark_controls_bundle: dict[str, Any],
    plan: dict[str, Any],
    baseline_reference_count: int,
) -> dict[str, Any]:
    baseline = benchmark_controls_bundle["source_baseline_bundle"]
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v7": copy.deepcopy(source_report_v7),
        "benchmark_controls_bundle": copy.deepcopy(
            benchmark_controls_bundle
        ),
        "bindings": {
            "source_report_v7_sha256": source_report_v7["report_sha256"],
            "source_report_v7_plan_sha256": source_report_v7["plan"][
                "plan_sha256"
            ],
            "benchmark_controls_bundle_sha256": benchmark_controls_bundle[
                "bundle_sha256"
            ],
            "benchmark_controls_plan_sha256": benchmark_controls_bundle[
                "plan"
            ]["plan_sha256"],
            "shared_baseline_bundle_sha256": baseline["bundle_sha256"],
        },
        "inherited_source_logical_run_count": (
            INHERITED_SOURCE_LOGICAL_RUN_COUNT
        ),
        "shared_baseline_reused_run_count": SHARED_BASELINE_REUSED_RUN_COUNT,
        "shared_baseline_reference_count": baseline_reference_count,
        "independent_control_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "source_logical_run_count": TOTAL_SOURCE_LOGICAL_RUN_COUNT,
        "control_executed_analysis_count": CONTROL_ANALYSIS_COUNT,
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


def build_synthetic_strategy_benchmark_report_v8(
    source_report_v7: dict[str, Any] | None = None,
    benchmark_controls_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v7 is not None or benchmark_controls_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v8()
    if source_report_v7 is None or benchmark_controls_bundle is None:
        raise ValueError("execute=True requires both prebuilt v8 sources")
    baseline_reference_count = _verify_sources(
        source_report_v7, benchmark_controls_bundle
    )
    plan = plan_synthetic_strategy_benchmark_report_v8()
    return _compose_report(
        source_report_v7,
        benchmark_controls_bundle,
        plan,
        baseline_reference_count,
    )


def verify_synthetic_strategy_benchmark_report_v8(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v8 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v8(plan)
    source_report_v7 = report.get("source_report_v7")
    benchmark_controls_bundle = report.get("benchmark_controls_bundle")
    if (
        type(source_report_v7) is not dict
        or type(benchmark_controls_bundle) is not dict
    ):
        raise TypeError("report must embed both exact native v8 sources")
    baseline_reference_count = _verify_sources(
        source_report_v7, benchmark_controls_bundle
    )
    expected = _compose_report(
        source_report_v7,
        benchmark_controls_bundle,
        plan,
        baseline_reference_count,
    )
    if report != expected:
        raise ValueError("synthetic benchmark v8 report verification failed")
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v7_sha256": report["bindings"][
            "source_report_v7_sha256"
        ],
        "benchmark_controls_bundle_sha256": report["bindings"][
            "benchmark_controls_bundle_sha256"
        ],
        "shared_baseline_bundle_sha256": report["bindings"][
            "shared_baseline_bundle_sha256"
        ],
        "inherited_source_logical_run_count": (
            INHERITED_SOURCE_LOGICAL_RUN_COUNT
        ),
        "shared_baseline_reused_run_count": SHARED_BASELINE_REUSED_RUN_COUNT,
        "independent_control_run_count": INDEPENDENT_CONTROL_RUN_COUNT,
        "source_logical_run_count": TOTAL_SOURCE_LOGICAL_RUN_COUNT,
        "control_executed_analysis_count": CONTROL_ANALYSIS_COUNT,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v8(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v8(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v8",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited benchmark v7 logical runs: {plan['inherited_source_logical_run_count']}",
        f"- Independent control runs: {plan['independent_control_run_count']}",
        f"- Total logical source runs: {plan['source_logical_run_count']}",
        "- The shared 32-run baseline is identity-checked and not counted twice.",
        "- V8 composition executes no additional backtests.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- No-skill and equal-volatility evidence remains synthetic and descriptive.",
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


def render_synthetic_strategy_benchmark_report_markdown_v8(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v8(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v8",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Inherited benchmark v7 logical runs: {report['inherited_source_logical_run_count']}",
        f"- Independent control runs: {report['independent_control_run_count']}",
        f"- Total logical source runs: {report['source_logical_run_count']}",
        f"- Control analyses: {report['control_executed_analysis_count']}",
        "- Shared baseline identity: VERIFIED WITHOUT DUPLICATE COUNTING",
        "- V8 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            "- All 16 no-skill paths are retained; no random path is selected.",
            "- Equal-volatility buy-and-hold is a descriptive projection without financing or margin modelling.",
            "- No ranking threshold or formal inference is established.",
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
        description="Render the non-current synthetic benchmark v8 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v8(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v8(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
