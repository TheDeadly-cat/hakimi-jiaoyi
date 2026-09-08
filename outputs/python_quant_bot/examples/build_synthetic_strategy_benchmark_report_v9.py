"""Compose non-current benchmark v9 with tie-aware CSCV/PBO bounds.

V9 consumes verified prebuilt v8 and tie-bounds artifacts. It verifies that
the tie-bounds source CSCV bundle is already embedded by v8, so the 147 reused
runs are not counted again. Composition executes no backtest and grants no
trading, profitability, blind-test, or formal-inference authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v8 import (
    plan_synthetic_strategy_benchmark_report_v8,
    verify_synthetic_strategy_benchmark_report_v8,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_tie_bounds_v1 import (
    plan_synthetic_strategy_cscv_pbo_tie_bounds_v1,
    verify_synthetic_strategy_cscv_pbo_tie_bounds_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v9"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v9"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v9"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v9"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_LOCAL_SOURCE_FILES_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_INDEPENDENT_CONTROLS_AND_"
    "TIE_AWARE_PBO_IDENTIFIED_SET_GAPS"
)
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 204
TIE_BOUNDS_SOURCE_REUSED_RUN_COUNT = 147
TIE_BOUNDS_ANALYSIS_COUNT = 6
_REPLACED_GAP = "PARTIAL_CSCV_RANK_TIE_GAP"

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
    source_plan: dict[str, Any], bounds_plan: dict[str, Any]
) -> list[str]:
    source_gaps = source_plan.get("gaps")
    bounds_gaps = bounds_plan.get("gaps")
    if type(source_gaps) is not list or type(bounds_gaps) is not list:
        raise ValueError("v9 source plans must expose exact gap lists")
    if _REPLACED_GAP not in source_gaps:
        raise ValueError("v9 source must retain the rank-tie gap being replaced")
    if any(type(item) is not str for item in source_gaps + bounds_gaps):
        raise TypeError("v9 source gaps must be exact native strings")
    combined = [gap for gap in source_gaps if gap != _REPLACED_GAP]
    return sorted(set(combined).union(bounds_gaps))


def _bundle_references(
    value: Any, bundle_sha256: str
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    if type(value) is dict:
        if value.get("bundle_sha256") == bundle_sha256:
            references.append(value)
        for item in value.values():
            references.extend(_bundle_references(item, bundle_sha256))
    elif type(value) is list:
        for item in value:
            references.extend(_bundle_references(item, bundle_sha256))
    return references


def plan_synthetic_strategy_benchmark_report_v9() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v8()
    bounds_plan = plan_synthetic_strategy_cscv_pbo_tie_bounds_v1()
    _require_exact_json_value(source_plan, path="$.source_report_plan")
    _require_exact_json_value(bounds_plan, path="$.tie_bounds_plan")
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "requires_shared_source_cscv_bundle_identity": True,
        "replaced_gap": _REPLACED_GAP,
        "source_report_plan": copy.deepcopy(source_plan),
        "tie_bounds_plan": copy.deepcopy(bounds_plan),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "tie_bounds_source_reused_run_count": (
            TIE_BOUNDS_SOURCE_REUSED_RUN_COUNT
        ),
        "planned_tie_bounds_analysis_count": TIE_BOUNDS_ANALYSIS_COUNT,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, bounds_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v9(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v9()
    if plan != expected:
        raise ValueError("synthetic benchmark v9 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v8: dict[str, Any],
    tie_bounds_bundle: dict[str, Any],
) -> int:
    if type(source_report_v8) is not dict:
        raise TypeError("source_report_v8 must be an exact native dict")
    if type(tie_bounds_bundle) is not dict:
        raise TypeError("tie_bounds_bundle must be an exact native dict")
    _require_exact_json_value(source_report_v8, path="$.source_report_v8")
    _require_exact_json_value(tie_bounds_bundle, path="$.tie_bounds_bundle")
    verify_synthetic_strategy_benchmark_report_v8(source_report_v8)
    verify_synthetic_strategy_cscv_pbo_tie_bounds_v1(tie_bounds_bundle)

    if source_report_v8["source_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT:
        raise ValueError("v8 logical source run count drifted")
    if (
        tie_bounds_bundle["source_reused_run_count"]
        != TIE_BOUNDS_SOURCE_REUSED_RUN_COUNT
        or tie_bounds_bundle["planned_run_count"] != 0
        or tie_bounds_bundle["executed_run_count"] != 0
        or tie_bounds_bundle["additional_backtest_run_count"] != 0
        or tie_bounds_bundle["executed_analysis_count"]
        != TIE_BOUNDS_ANALYSIS_COUNT
        or tie_bounds_bundle["point_identified_evidence_count"] != 4
        or tie_bounds_bundle["partial_interval_evidence_count"] != 1
        or tie_bounds_bundle["full_unit_interval_evidence_count"] != 1
    ):
        raise ValueError("tie-bounds source accounting or coverage drifted")

    source_cscv = tie_bounds_bundle["source_cscv_bundle"]
    source_cscv_sha256 = tie_bounds_bundle["source_cscv_bundle_sha256"]
    if source_cscv.get("bundle_sha256") != source_cscv_sha256:
        raise ValueError("tie-bounds source CSCV binding drifted")
    references = _bundle_references(source_report_v8, source_cscv_sha256)
    if not references:
        raise ValueError("v8 does not embed the tie-bounds source CSCV bundle")
    if any(reference != source_cscv for reference in references):
        raise ValueError("shared CSCV digest aliases unequal artifacts")

    if source_report_v8["authority"] != _AUTHORITY:
        raise ValueError("benchmark v8 authority must remain denied")
    if tie_bounds_bundle["authority"] != _AUTHORITY:
        raise ValueError("tie-bounds authority must remain denied")
    if source_report_v8["runtime_mutations"] is not False:
        raise ValueError("benchmark v8 runtime mutations must remain false")
    if tie_bounds_bundle["runtime_mutations"] is not False:
        raise ValueError("tie-bounds runtime mutations must remain false")
    if source_report_v8["status"] != STATUS or tie_bounds_bundle["status"] != STATUS:
        raise ValueError("all v9 sources must remain blocked")
    return len(references)


def _compose_report(
    source_report_v8: dict[str, Any],
    tie_bounds_bundle: dict[str, Any],
    plan: dict[str, Any],
    shared_reference_count: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v8": copy.deepcopy(source_report_v8),
        "tie_bounds_bundle": copy.deepcopy(tie_bounds_bundle),
        "bindings": {
            "source_report_v8_sha256": source_report_v8["report_sha256"],
            "source_report_v8_plan_sha256": source_report_v8["plan"][
                "plan_sha256"
            ],
            "tie_bounds_bundle_sha256": tie_bounds_bundle["bundle_sha256"],
            "tie_bounds_plan_sha256": tie_bounds_bundle["plan"][
                "plan_sha256"
            ],
            "shared_source_cscv_bundle_sha256": tie_bounds_bundle[
                "source_cscv_bundle_sha256"
            ],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "tie_bounds_source_reused_run_count": (
            TIE_BOUNDS_SOURCE_REUSED_RUN_COUNT
        ),
        "shared_source_cscv_reference_count": shared_reference_count,
        "tie_bounds_executed_analysis_count": TIE_BOUNDS_ANALYSIS_COUNT,
        "point_identified_evidence_count": tie_bounds_bundle[
            "point_identified_evidence_count"
        ],
        "partial_interval_evidence_count": tie_bounds_bundle[
            "partial_interval_evidence_count"
        ],
        "full_unit_interval_evidence_count": tie_bounds_bundle[
            "full_unit_interval_evidence_count"
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


def build_synthetic_strategy_benchmark_report_v9(
    source_report_v8: dict[str, Any] | None = None,
    tie_bounds_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v8 is not None or tie_bounds_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v9()
    if source_report_v8 is None or tie_bounds_bundle is None:
        raise ValueError("execute=True requires both prebuilt v9 sources")
    shared_reference_count = _verify_sources(
        source_report_v8, tie_bounds_bundle
    )
    plan = plan_synthetic_strategy_benchmark_report_v9()
    return _compose_report(
        source_report_v8,
        tie_bounds_bundle,
        plan,
        shared_reference_count,
    )


def verify_synthetic_strategy_benchmark_report_v9(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v9 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v9(plan)
    source_report_v8 = report.get("source_report_v8")
    tie_bounds_bundle = report.get("tie_bounds_bundle")
    if type(source_report_v8) is not dict or type(tie_bounds_bundle) is not dict:
        raise TypeError("report must embed both exact native v9 sources")
    shared_reference_count = _verify_sources(
        source_report_v8, tie_bounds_bundle
    )
    expected = _compose_report(
        source_report_v8,
        tie_bounds_bundle,
        plan,
        shared_reference_count,
    )
    if report != expected:
        raise ValueError("synthetic benchmark v9 report verification failed")
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v8_sha256": report["bindings"][
            "source_report_v8_sha256"
        ],
        "tie_bounds_bundle_sha256": report["bindings"][
            "tie_bounds_bundle_sha256"
        ],
        "shared_source_cscv_bundle_sha256": report["bindings"][
            "shared_source_cscv_bundle_sha256"
        ],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "tie_bounds_source_reused_run_count": (
            TIE_BOUNDS_SOURCE_REUSED_RUN_COUNT
        ),
        "tie_bounds_executed_analysis_count": TIE_BOUNDS_ANALYSIS_COUNT,
        "point_identified_evidence_count": report[
            "point_identified_evidence_count"
        ],
        "partial_interval_evidence_count": report[
            "partial_interval_evidence_count"
        ],
        "full_unit_interval_evidence_count": report[
            "full_unit_interval_evidence_count"
        ],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v9(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v9(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v9",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v8 logical source runs: {plan['source_logical_run_count']}",
        f"- Reused tie-bounds source runs: {plan['tie_bounds_source_reused_run_count']}",
        f"- Planned tie-bounds analyses: {plan['planned_tie_bounds_analysis_count']}",
        "- Shared CSCV source identity is required; reused runs are not counted twice.",
        "- V9 composition executes no additional backtests.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- Tie-aware PBO values remain synthetic identified sets.",
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


def render_synthetic_strategy_benchmark_report_markdown_v9(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v9(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v9",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v8 logical source runs: {report['source_logical_run_count']}",
        f"- Tie-bounds analyses: {report['tie_bounds_executed_analysis_count']}",
        "- Shared CSCV source identity: VERIFIED WITHOUT DUPLICATE COUNTING",
        "- V9 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            f"- Point-identified PBO diagnostics: {report['point_identified_evidence_count']}/6.",
            f"- Partial PBO identified sets: {report['partial_interval_evidence_count']}/6.",
            f"- Full-unit PBO identified sets: {report['full_unit_interval_evidence_count']}/6.",
            "- No arbitrary tie-break or interval-midpoint PBO is reported.",
            "- A full-unit interval remains explicitly uninformative.",
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
        description="Render the non-current synthetic benchmark v9 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v9(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v9(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
