"""Compose non-current benchmark v10 with a research dependency lock audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v9 import (
    plan_synthetic_strategy_benchmark_report_v9,
    verify_synthetic_strategy_benchmark_report_v9,
)
from exchange_terminal.application.synthetic_strategy_benchmark_research_lock_audit_v1 import (
    plan_synthetic_strategy_benchmark_research_lock_audit_v1,
    verify_synthetic_strategy_benchmark_research_lock_audit_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v10"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v10"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v10"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v10"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_LOCAL_SOURCE_LOCK_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_BENCHMARK_WITH_RESEARCH_LOCK_AND_REPRODUCIBILITY_GAPS"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 204

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


def plan_synthetic_strategy_benchmark_report_v10() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v9()
    audit_plan = plan_synthetic_strategy_benchmark_research_lock_audit_v1()
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "research_lock_audit_plan": copy.deepcopy(audit_plan),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "research_lock_source_reused_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "planned_research_lock_analysis_count": 1,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "dependency_lock_sha256": audit_plan["lock_manifest"][
            "dependency_lock_sha256"
        ],
        "source_manifest_sha256": audit_plan["source_manifest"][
            "source_manifest_sha256"
        ],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(audit_plan["gaps"]),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v10(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v10()
    if plan != expected:
        raise ValueError("synthetic benchmark v10 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v9: dict[str, Any], research_lock_audit: dict[str, Any]
) -> None:
    if type(source_report_v9) is not dict:
        raise TypeError("source_report_v9 must be an exact native dict")
    if type(research_lock_audit) is not dict:
        raise TypeError("research_lock_audit must be an exact native dict")
    _require_exact_json_value(source_report_v9, path="$.source_report_v9")
    _require_exact_json_value(research_lock_audit, path="$.research_lock_audit")
    verify_synthetic_strategy_benchmark_report_v9(source_report_v9)
    verify_synthetic_strategy_benchmark_research_lock_audit_v1(
        research_lock_audit, source_report_v9
    )
    if source_report_v9["source_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT:
        raise ValueError("v9 logical source run count drifted")
    if (
        research_lock_audit["source_report_v9_sha256"]
        != source_report_v9["report_sha256"]
        or research_lock_audit["source_logical_run_count"]
        != SOURCE_LOGICAL_RUN_COUNT
        or research_lock_audit["executed_run_count"] != 0
        or research_lock_audit["additional_backtest_run_count"] != 0
        or research_lock_audit["executed_analysis_count"] != 1
    ):
        raise ValueError("research-lock source binding or accounting drifted")
    if (
        research_lock_audit["benchmark_lock_fully_version_pinned"] is not True
        or research_lock_audit["dependency_artifact_hashes_present"] is not False
        or research_lock_audit["full_application_lock_covered"] is not False
    ):
        raise ValueError("research-lock scope boundary drifted")
    if source_report_v9["authority"] != _AUTHORITY:
        raise ValueError("benchmark v9 authority must remain denied")
    if research_lock_audit["authority"] != _AUTHORITY:
        raise ValueError("research-lock audit authority must remain denied")
    if (
        source_report_v9["runtime_mutations"] is not False
        or research_lock_audit["runtime_mutations"] is not False
    ):
        raise ValueError("v10 sources must not mutate runtime state")


def _compose_report(
    source_report_v9: dict[str, Any],
    research_lock_audit: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v9": copy.deepcopy(source_report_v9),
        "research_lock_audit": copy.deepcopy(research_lock_audit),
        "bindings": {
            "source_report_v9_sha256": source_report_v9["report_sha256"],
            "source_report_v9_plan_sha256": source_report_v9["plan"][
                "plan_sha256"
            ],
            "research_lock_audit_bundle_sha256": research_lock_audit[
                "bundle_sha256"
            ],
            "research_lock_audit_plan_sha256": research_lock_audit["plan"][
                "plan_sha256"
            ],
            "dependency_lock_sha256": research_lock_audit[
                "dependency_lock_sha256"
            ],
            "source_manifest_sha256": research_lock_audit["source_manifest"][
                "source_manifest_sha256"
            ],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "research_lock_source_reused_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "research_lock_executed_analysis_count": 1,
        "source_module_file_count": research_lock_audit["source_manifest"][
            "module_file_count"
        ],
        "exact_dependency_pin_count": research_lock_audit[
            "dependency_lock_manifest"
        ]["exact_pin_count"],
        "installed_exact_match_count": research_lock_audit[
            "installed_resolution"
        ]["exact_match_count"],
        "benchmark_lock_fully_version_pinned": True,
        "dependency_artifact_hashes_present": False,
        "full_application_lock_covered": False,
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


def build_synthetic_strategy_benchmark_report_v10(
    source_report_v9: dict[str, Any] | None = None,
    research_lock_audit: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v9 is not None or research_lock_audit is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v10()
    if source_report_v9 is None or research_lock_audit is None:
        raise ValueError("execute=True requires both prebuilt v10 sources")
    _verify_sources(source_report_v9, research_lock_audit)
    return _compose_report(
        source_report_v9,
        research_lock_audit,
        plan_synthetic_strategy_benchmark_report_v10(),
    )


def verify_synthetic_strategy_benchmark_report_v10(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v10 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v10(plan)
    source_report_v9 = report.get("source_report_v9")
    research_lock_audit = report.get("research_lock_audit")
    if type(source_report_v9) is not dict or type(research_lock_audit) is not dict:
        raise TypeError("report must embed both exact native v10 sources")
    _verify_sources(source_report_v9, research_lock_audit)
    expected = _compose_report(source_report_v9, research_lock_audit, plan)
    if report != expected:
        raise ValueError("synthetic benchmark v10 report verification failed")
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v9_sha256": report["bindings"][
            "source_report_v9_sha256"
        ],
        "research_lock_audit_bundle_sha256": report["bindings"][
            "research_lock_audit_bundle_sha256"
        ],
        "dependency_lock_sha256": report["bindings"][
            "dependency_lock_sha256"
        ],
        "source_manifest_sha256": report["bindings"][
            "source_manifest_sha256"
        ],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "source_module_file_count": report["source_module_file_count"],
        "exact_dependency_pin_count": report["exact_dependency_pin_count"],
        "installed_exact_match_count": report["installed_exact_match_count"],
        "benchmark_lock_fully_version_pinned": True,
        "dependency_artifact_hashes_present": False,
        "full_application_lock_covered": False,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v10(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v10(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v10",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v9 logical source runs: {plan['source_logical_run_count']}",
        f"- Bound source files: {plan['research_lock_audit_plan']['source_manifest']['module_file_count']}",
        f"- Exact benchmark dependency pins: {plan['research_lock_audit_plan']['lock_manifest']['exact_pin_count']}",
        "- V10 composition executes no additional backtests.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- The lock is benchmark-specific and platform-specific.",
            "- Artifact hashes and full-application lock coverage remain absent.",
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


def render_synthetic_strategy_benchmark_report_markdown_v10(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v10(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v10",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v9 logical source runs: {report['source_logical_run_count']}",
        f"- SHA-bound source files: {report['source_module_file_count']}",
        f"- Exact benchmark dependency pins: {report['exact_dependency_pin_count']}",
        f"- Exact installed-version matches: {report['installed_exact_match_count']}",
        "- V10 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            "- The benchmark scope has a dependency lock hash and exact version pins.",
            "- Package artifact hashes and full-application lock coverage remain absent.",
            "- Installed-version matching is not fresh-install reproduction proof.",
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
        description="Render the non-current synthetic benchmark v10 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v10(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v10(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
