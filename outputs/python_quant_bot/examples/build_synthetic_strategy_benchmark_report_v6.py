"""Compose the non-current synthetic benchmark v6 with provenance gap evidence.

This module is a zero-run consumer. It does not execute backtests, call Git, or
promote any paper, live, order-entry, profitability, blind-test, or formal
inference authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v5 import (
    plan_synthetic_strategy_benchmark_report_v5,
    verify_synthetic_strategy_benchmark_report_v5,
)
from exchange_terminal.application.synthetic_strategy_reproducibility_provenance_gap_audit_v1 import (
    plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
    verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v6"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v6"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v6"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v6"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_LOCAL_SOURCE_FILES_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_REGIME_BOOTSTRAP_DSR_PARTIAL_PBO_"
    "AND_PROVENANCE_GAP_AUDIT"
)
STATUS = "BLOCK"
PREREGISTERED_REQUIREMENT_COUNT = 14
PREREGISTERED_EXACT_PIN_COUNT = 1
PREREGISTERED_UNPINNED_REQUIREMENT_COUNT = 13

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
    source_plan: dict[str, Any], audit_plan: dict[str, Any]
) -> list[str]:
    source_gaps = source_plan.get("gaps")
    audit_gaps = audit_plan.get("gaps")
    if type(source_gaps) is not list or type(audit_gaps) is not list:
        raise ValueError("source plans must expose exact gap lists")
    if any(type(item) is not str for item in source_gaps + audit_gaps):
        raise TypeError("source plan gaps must be exact native strings")
    return sorted(set(source_gaps).union(audit_gaps))


def plan_synthetic_strategy_benchmark_report_v6() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v5()
    audit_plan = plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1()
    _require_exact_json_value(source_plan, path="$.source_report_plan")
    _require_exact_json_value(audit_plan, path="$.provenance_audit_plan")

    dependency_audit = audit_plan["dependency_audit"]
    critical_manifest = audit_plan["critical_source_manifest"]
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "provenance_audit_plan": copy.deepcopy(audit_plan),
        "source_logical_run_count": source_plan["source_logical_run_count"],
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "critical_source_module_count": critical_manifest["module_count"],
        "requirement_count": dependency_audit["requirement_count"],
        "exact_pin_count": dependency_audit["exact_pin_count"],
        "unpinned_requirement_count": dependency_audit["unpinned_count"],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, audit_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v6(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v6()
    if plan != expected:
        raise ValueError("synthetic benchmark v6 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v5: dict[str, Any],
    provenance_audit: dict[str, Any],
) -> None:
    if type(source_report_v5) is not dict:
        raise TypeError("source_report_v5 must be an exact native dict")
    if type(provenance_audit) is not dict:
        raise TypeError("provenance_audit must be an exact native dict")
    _require_exact_json_value(source_report_v5, path="$.source_report_v5")
    _require_exact_json_value(provenance_audit, path="$.provenance_audit")

    verify_synthetic_strategy_benchmark_report_v5(source_report_v5)
    verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
        provenance_audit,
        source_report_v5,
    )

    if source_report_v5["source_logical_run_count"] != 186:
        raise ValueError("benchmark v5 must retain exactly 186 logical source runs")
    if provenance_audit["source_logical_run_count"] != 186:
        raise ValueError("provenance audit logical source count drifted")
    if (
        provenance_audit["source_report_v5_sha256"]
        != source_report_v5["report_sha256"]
    ):
        raise ValueError("provenance audit source report binding drifted")
    if (
        provenance_audit["source_report_v5_plan_sha256"]
        != source_report_v5["plan"]["plan_sha256"]
    ):
        raise ValueError("provenance audit source plan binding drifted")

    critical_manifest = provenance_audit["critical_source_manifest"]
    dependency_audit = provenance_audit["dependency_audit"]
    run_manifest_audit = provenance_audit["run_manifest_audit"]
    expected_counts = {
        "critical_source_module_count": (critical_manifest["module_count"], 18),
        "requirement_count": (
            dependency_audit["requirement_count"],
            PREREGISTERED_REQUIREMENT_COUNT,
        ),
        "exact_pin_count": (
            dependency_audit["exact_pin_count"],
            PREREGISTERED_EXACT_PIN_COUNT,
        ),
        "unpinned_requirement_count": (
            dependency_audit["unpinned_count"],
            PREREGISTERED_UNPINNED_REQUIREMENT_COUNT,
        ),
        "valid_git_commit_identity_count": (
            run_manifest_audit["valid_git_commit_identity_count"],
            0,
        ),
        "fully_pinned_dependency_identity_count": (
            run_manifest_audit["fully_pinned_dependency_identity_count"],
            0,
        ),
    }
    for label, (observed, expected) in expected_counts.items():
        if type(observed) is not int or observed != expected:
            raise ValueError(f"{label} drifted from the preregistered v6 boundary")

    if source_report_v5["authority"] != _AUTHORITY:
        raise ValueError("benchmark v5 authority must remain denied")
    if provenance_audit["authority"] != _AUTHORITY:
        raise ValueError("provenance audit authority must remain denied")
    if source_report_v5["runtime_mutations"] is not False:
        raise ValueError("benchmark v5 runtime mutations must remain false")
    if provenance_audit["runtime_mutations"] is not False:
        raise ValueError("provenance audit runtime mutations must remain false")
    if source_report_v5["evidence_state"] != EVIDENCE_STATE:
        raise ValueError("benchmark v5 evidence state must remain GAP")
    if provenance_audit["evidence_state"] != EVIDENCE_STATE:
        raise ValueError("provenance audit evidence state must remain GAP")
    if source_report_v5["status"] != STATUS or provenance_audit["status"] != STATUS:
        raise ValueError("all v6 sources must remain blocked")


def _compose_report(
    source_report_v5: dict[str, Any],
    provenance_audit: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    critical_manifest = provenance_audit["critical_source_manifest"]
    dependency_audit = provenance_audit["dependency_audit"]
    run_manifest_audit = provenance_audit["run_manifest_audit"]
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v5": copy.deepcopy(source_report_v5),
        "provenance_audit": copy.deepcopy(provenance_audit),
        "bindings": {
            "source_report_v5_sha256": source_report_v5["report_sha256"],
            "source_report_v5_plan_sha256": source_report_v5["plan"]["plan_sha256"],
            "provenance_audit_bundle_sha256": provenance_audit["bundle_sha256"],
            "provenance_audit_plan_sha256": provenance_audit["plan"][
                "plan_sha256"
            ],
            "critical_source_manifest_sha256": critical_manifest[
                "source_manifest_sha256"
            ],
            "dependency_document_sha256": dependency_audit["sha256"],
        },
        "source_logical_run_count": source_report_v5["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "critical_source_module_count": critical_manifest["module_count"],
        "requirement_count": dependency_audit["requirement_count"],
        "exact_pin_count": dependency_audit["exact_pin_count"],
        "unpinned_requirement_count": dependency_audit["unpinned_count"],
        "unique_run_manifest_count": run_manifest_audit[
            "unique_run_manifest_count"
        ],
        "unique_strategy_fingerprint_count": run_manifest_audit[
            "unique_strategy_fingerprint_count"
        ],
        "valid_git_commit_identity_count": run_manifest_audit[
            "valid_git_commit_identity_count"
        ],
        "clean_worktree_identity_count": run_manifest_audit[
            "clean_worktree_identity_count"
        ],
        "fully_pinned_dependency_identity_count": run_manifest_audit[
            "fully_pinned_dependency_identity_count"
        ],
        "observed_high_volatility_slice_count": source_report_v5[
            "observed_high_volatility_slice_count"
        ],
        "observed_deflated_sharpe_diagnostic_count": source_report_v5[
            "observed_deflated_sharpe_diagnostic_count"
        ],
        "observed_cscv_pbo_diagnostic_count": source_report_v5[
            "observed_cscv_pbo_diagnostic_count"
        ],
        "gap_cscv_pbo_diagnostic_count": source_report_v5[
            "gap_cscv_pbo_diagnostic_count"
        ],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": copy.deepcopy(plan["gaps"]),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "report_sha256")


def build_synthetic_strategy_benchmark_report_v6(
    source_report_v5: dict[str, Any] | None = None,
    provenance_audit: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v5 is not None or provenance_audit is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v6()
    if source_report_v5 is None or provenance_audit is None:
        raise ValueError("execute=True requires both prebuilt v6 sources")

    _verify_sources(source_report_v5, provenance_audit)
    plan = plan_synthetic_strategy_benchmark_report_v6()
    return _compose_report(source_report_v5, provenance_audit, plan)


def verify_synthetic_strategy_benchmark_report_v6(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v6 report schema")

    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v6(plan)

    source_report_v5 = report.get("source_report_v5")
    provenance_audit = report.get("provenance_audit")
    if type(source_report_v5) is not dict or type(provenance_audit) is not dict:
        raise TypeError("report must embed both exact native source artifacts")
    _verify_sources(source_report_v5, provenance_audit)

    expected = _compose_report(source_report_v5, provenance_audit, plan)
    if report != expected:
        raise ValueError("synthetic benchmark v6 report verification failed")

    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v5_sha256": report["bindings"][
            "source_report_v5_sha256"
        ],
        "provenance_audit_bundle_sha256": report["bindings"][
            "provenance_audit_bundle_sha256"
        ],
        "critical_source_manifest_sha256": report["bindings"][
            "critical_source_manifest_sha256"
        ],
        "dependency_document_sha256": report["bindings"][
            "dependency_document_sha256"
        ],
        "source_logical_run_count": report["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "critical_source_module_count": report["critical_source_module_count"],
        "requirement_count": report["requirement_count"],
        "unpinned_requirement_count": report["unpinned_requirement_count"],
        "valid_git_commit_identity_count": 0,
        "fully_pinned_dependency_identity_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v6(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v6(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v6",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Prebuilt benchmark v5 logical source runs: {plan['source_logical_run_count']}",
        f"- Read-only critical source modules: {plan['critical_source_module_count']}",
        f"- Dependency declarations: {plan['requirement_count']}",
        "- Composition executes no additional backtests.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- Formal reproducibility is not established.",
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


def render_synthetic_strategy_benchmark_report_markdown_v6(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v6(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v6",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v5 logical source runs: {report['source_logical_run_count']}",
        f"- Read-only critical source modules: {report['critical_source_module_count']}",
        f"- Unique embedded run manifests: {report['unique_run_manifest_count']}",
        f"- Dependency declarations: {report['requirement_count']}",
        f"- Exact pins: {report['exact_pin_count']}",
        f"- Unpinned declarations: {report['unpinned_requirement_count']}",
        "- v6 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            "- Formal reproducibility is not established.",
            "- Source commit identity still requires an authorized snapshot.",
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
        description="Render the non-current synthetic benchmark v6 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v6(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v6(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
