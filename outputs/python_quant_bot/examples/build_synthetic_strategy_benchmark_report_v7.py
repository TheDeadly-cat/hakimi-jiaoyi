"""Compose non-current benchmark v7 with return-concentration evidence.

V7 is a zero-run consumer of a verified benchmark v6 report and a verified
return-contribution concentration bundle. It does not execute a backtest, call
Git, mutate runtime state, or grant any trading or inference authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v6 import (
    plan_synthetic_strategy_benchmark_report_v6,
    verify_synthetic_strategy_benchmark_report_v6,
)
from exchange_terminal.application.synthetic_strategy_return_contribution_concentration_v1 import (
    plan_synthetic_strategy_return_contribution_concentration_v1,
    verify_synthetic_strategy_return_contribution_concentration_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v7"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v7"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v7"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v7"
DATA_SOURCE = "SYNTHETIC_EVIDENCE_WITH_LOCAL_SOURCE_FILES_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_PROVENANCE_AND_RETURN_CONTRIBUTION_"
    "CONCENTRATION_GAPS"
)
STATUS = "BLOCK"

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
    source_plan: dict[str, Any], concentration_plan: dict[str, Any]
) -> list[str]:
    source_gaps = source_plan.get("gaps")
    concentration_gaps = concentration_plan.get("gaps")
    if type(source_gaps) is not list or type(concentration_gaps) is not list:
        raise ValueError("v7 source plans must expose exact gap lists")
    if any(
        type(item) is not str for item in source_gaps + concentration_gaps
    ):
        raise TypeError("v7 source plan gaps must be exact native strings")
    return sorted(set(source_gaps).union(concentration_gaps))


def plan_synthetic_strategy_benchmark_report_v7() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v6()
    concentration_plan = (
        plan_synthetic_strategy_return_contribution_concentration_v1()
    )
    _require_exact_json_value(source_plan, path="$.source_report_plan")
    _require_exact_json_value(
        concentration_plan, path="$.return_contribution_plan"
    )
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "requires_shared_trial_return_matrix_identity": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "return_contribution_plan": copy.deepcopy(concentration_plan),
        "source_logical_run_count": source_plan["source_logical_run_count"],
        "concentration_source_reused_run_count": concentration_plan[
            "source_required_run_count"
        ],
        "planned_concentration_analysis_count": concentration_plan[
            "planned_analysis_count"
        ],
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, concentration_plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v7(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json_value(plan)
    expected = plan_synthetic_strategy_benchmark_report_v7()
    if plan != expected:
        raise ValueError("synthetic benchmark v7 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _embedded_trial_return_matrix_bundle(
    source_report_v6: dict[str, Any],
) -> dict[str, Any]:
    source_v5 = source_report_v6.get("source_report_v5")
    if type(source_v5) is not dict:
        raise ValueError("v6 must embed its verified v5 source")
    source_v4 = source_v5.get("source_report_v4")
    if type(source_v4) is not dict:
        raise ValueError("v5 must embed its verified v4 source")
    matrix_bundle = source_v4.get("trial_return_matrix")
    if type(matrix_bundle) is not dict:
        raise ValueError("v4 must embed its verified trial return matrix")
    return matrix_bundle


def _verify_sources(
    source_report_v6: dict[str, Any],
    return_contribution_bundle: dict[str, Any],
) -> None:
    if type(source_report_v6) is not dict:
        raise TypeError("source_report_v6 must be an exact native dict")
    if type(return_contribution_bundle) is not dict:
        raise TypeError(
            "return_contribution_bundle must be an exact native dict"
        )
    _require_exact_json_value(source_report_v6, path="$.source_report_v6")
    _require_exact_json_value(
        return_contribution_bundle, path="$.return_contribution_bundle"
    )
    verify_synthetic_strategy_benchmark_report_v6(source_report_v6)
    verify_synthetic_strategy_return_contribution_concentration_v1(
        return_contribution_bundle
    )

    shared_matrix = _embedded_trial_return_matrix_bundle(source_report_v6)
    concentration_matrix = return_contribution_bundle["source_matrix_bundle"]
    if concentration_matrix != shared_matrix:
        raise ValueError(
            "v7 sources must share the exact same trial return matrix artifact"
        )
    if (
        return_contribution_bundle["source_matrix_bundle_sha256"]
        != shared_matrix["bundle_sha256"]
    ):
        raise ValueError("v7 shared matrix SHA-256 binding drifted")

    expected_counts = {
        "source_logical_run_count": (
            source_report_v6["source_logical_run_count"],
            186,
        ),
        "concentration_source_reused_run_count": (
            return_contribution_bundle["source_reused_run_count"],
            147,
        ),
        "concentration_executed_analysis_count": (
            return_contribution_bundle["executed_analysis_count"],
            6,
        ),
        "observed_period_concentration_count": (
            return_contribution_bundle[
                "observed_period_concentration_count"
            ],
            5,
        ),
        "gap_period_concentration_count": (
            return_contribution_bundle["gap_period_concentration_count"],
            1,
        ),
        "observed_calendar_month_sensitivity_count": (
            return_contribution_bundle[
                "observed_calendar_month_sensitivity_count"
            ],
            6,
        ),
        "observed_fixed_window_sensitivity_count": (
            return_contribution_bundle[
                "observed_fixed_window_sensitivity_count"
            ],
            6,
        ),
        "observed_closed_trade_sensitivity_count": (
            return_contribution_bundle[
                "observed_closed_trade_sensitivity_count"
            ],
            6,
        ),
        "gap_closed_trade_sensitivity_count": (
            return_contribution_bundle[
                "gap_closed_trade_sensitivity_count"
            ],
            0,
        ),
        "observed_positive_closed_trade_concentration_count": (
            return_contribution_bundle[
                "observed_positive_closed_trade_concentration_count"
            ],
            4,
        ),
        "gap_positive_closed_trade_concentration_count": (
            return_contribution_bundle[
                "gap_positive_closed_trade_concentration_count"
            ],
            2,
        ),
    }
    for label, (observed, expected) in expected_counts.items():
        if type(observed) is not int or observed != expected:
            raise ValueError(f"{label} drifted from the v7 source boundary")

    if source_report_v6["authority"] != _AUTHORITY:
        raise ValueError("benchmark v6 authority must remain denied")
    if return_contribution_bundle["authority"] != _AUTHORITY:
        raise ValueError("return-contribution authority must remain denied")
    if source_report_v6["runtime_mutations"] is not False:
        raise ValueError("benchmark v6 runtime mutations must remain false")
    if return_contribution_bundle["runtime_mutations"] is not False:
        raise ValueError("return-contribution runtime mutations must remain false")
    if source_report_v6["evidence_state"] != EVIDENCE_STATE:
        raise ValueError("benchmark v6 evidence state must remain GAP")
    if return_contribution_bundle["evidence_state"] != "OBSERVED_WITH_GAPS":
        raise ValueError("return-contribution evidence must retain explicit gaps")
    if (
        source_report_v6["status"] != STATUS
        or return_contribution_bundle["status"] != STATUS
    ):
        raise ValueError("all v7 sources must remain blocked")
    if (
        return_contribution_bundle["planned_run_count"] != 0
        or return_contribution_bundle["executed_run_count"] != 0
        or return_contribution_bundle["additional_backtest_run_count"] != 0
    ):
        raise ValueError("return-contribution consumer must add zero runs")


def _compose_report(
    source_report_v6: dict[str, Any],
    return_contribution_bundle: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    shared_matrix = _embedded_trial_return_matrix_bundle(source_report_v6)
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v6": copy.deepcopy(source_report_v6),
        "return_contribution_bundle": copy.deepcopy(
            return_contribution_bundle
        ),
        "bindings": {
            "source_report_v6_sha256": source_report_v6["report_sha256"],
            "source_report_v6_plan_sha256": source_report_v6["plan"][
                "plan_sha256"
            ],
            "return_contribution_bundle_sha256": return_contribution_bundle[
                "bundle_sha256"
            ],
            "return_contribution_plan_sha256": return_contribution_bundle[
                "plan"
            ]["plan_sha256"],
            "shared_trial_return_matrix_bundle_sha256": shared_matrix[
                "bundle_sha256"
            ],
            "shared_trial_return_matrix_plan_sha256": shared_matrix["plan"][
                "plan_sha256"
            ],
            "critical_source_manifest_sha256": source_report_v6["bindings"][
                "critical_source_manifest_sha256"
            ],
            "dependency_document_sha256": source_report_v6["bindings"][
                "dependency_document_sha256"
            ],
        },
        "source_logical_run_count": source_report_v6[
            "source_logical_run_count"
        ],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "concentration_source_reused_run_count": return_contribution_bundle[
            "source_reused_run_count"
        ],
        "concentration_executed_analysis_count": return_contribution_bundle[
            "executed_analysis_count"
        ],
        "observed_period_concentration_count": return_contribution_bundle[
            "observed_period_concentration_count"
        ],
        "gap_period_concentration_count": return_contribution_bundle[
            "gap_period_concentration_count"
        ],
        "observed_calendar_month_sensitivity_count": return_contribution_bundle[
            "observed_calendar_month_sensitivity_count"
        ],
        "observed_fixed_window_sensitivity_count": return_contribution_bundle[
            "observed_fixed_window_sensitivity_count"
        ],
        "observed_closed_trade_sensitivity_count": return_contribution_bundle[
            "observed_closed_trade_sensitivity_count"
        ],
        "gap_closed_trade_sensitivity_count": return_contribution_bundle[
            "gap_closed_trade_sensitivity_count"
        ],
        "observed_positive_closed_trade_concentration_count": (
            return_contribution_bundle[
                "observed_positive_closed_trade_concentration_count"
            ]
        ),
        "gap_positive_closed_trade_concentration_count": (
            return_contribution_bundle[
                "gap_positive_closed_trade_concentration_count"
            ]
        ),
        "critical_source_module_count": source_report_v6[
            "critical_source_module_count"
        ],
        "requirement_count": source_report_v6["requirement_count"],
        "unpinned_requirement_count": source_report_v6[
            "unpinned_requirement_count"
        ],
        "valid_git_commit_identity_count": source_report_v6[
            "valid_git_commit_identity_count"
        ],
        "fully_pinned_dependency_identity_count": source_report_v6[
            "fully_pinned_dependency_identity_count"
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


def build_synthetic_strategy_benchmark_report_v7(
    source_report_v6: dict[str, Any] | None = None,
    return_contribution_bundle: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if source_report_v6 is not None or return_contribution_bundle is not None:
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v7()
    if source_report_v6 is None or return_contribution_bundle is None:
        raise ValueError("execute=True requires both prebuilt v7 sources")
    _verify_sources(source_report_v6, return_contribution_bundle)
    plan = plan_synthetic_strategy_benchmark_report_v7()
    return _compose_report(source_report_v6, return_contribution_bundle, plan)


def verify_synthetic_strategy_benchmark_report_v7(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json_value(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v7 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v7(plan)
    source_report_v6 = report.get("source_report_v6")
    return_contribution_bundle = report.get("return_contribution_bundle")
    if type(source_report_v6) is not dict or type(return_contribution_bundle) is not dict:
        raise TypeError("report must embed both exact native v7 source artifacts")
    _verify_sources(source_report_v6, return_contribution_bundle)
    expected = _compose_report(
        source_report_v6, return_contribution_bundle, plan
    )
    if report != expected:
        raise ValueError("synthetic benchmark v7 report verification failed")
    receipt_payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "report_sha256": report["report_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "source_report_v6_sha256": report["bindings"][
            "source_report_v6_sha256"
        ],
        "return_contribution_bundle_sha256": report["bindings"][
            "return_contribution_bundle_sha256"
        ],
        "shared_trial_return_matrix_bundle_sha256": report["bindings"][
            "shared_trial_return_matrix_bundle_sha256"
        ],
        "source_logical_run_count": report["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "concentration_executed_analysis_count": report[
            "concentration_executed_analysis_count"
        ],
        "observed_period_concentration_count": report[
            "observed_period_concentration_count"
        ],
        "gap_period_concentration_count": report[
            "gap_period_concentration_count"
        ],
        "observed_positive_closed_trade_concentration_count": report[
            "observed_positive_closed_trade_concentration_count"
        ],
        "gap_positive_closed_trade_concentration_count": report[
            "gap_positive_closed_trade_concentration_count"
        ],
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _with_sha256(receipt_payload, "receipt_sha256")


def render_synthetic_strategy_benchmark_report_plan_markdown_v7(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v7(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v7",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v6 logical source runs: {plan['source_logical_run_count']}",
        f"- Reused concentration source runs: {plan['concentration_source_reused_run_count']}",
        f"- Planned concentration analyses: {plan['planned_concentration_analysis_count']}",
        "- V7 composition executes no additional backtests.",
        "- Both sources must share one exact trial-return-matrix artifact.",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in plan["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {plan['maturity']}",
            "- Concentration evidence remains synthetic and descriptive.",
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


def render_synthetic_strategy_benchmark_report_markdown_v7(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v7(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v7",
        "",
        "NON-CURRENT RESEARCH-ONLY CANDIDATE",
        "",
        "## SOURCE",
        f"- Bound benchmark v6 logical source runs: {report['source_logical_run_count']}",
        f"- Return-contribution analyses: {report['concentration_executed_analysis_count']}",
        "- Shared trial-return-matrix identity: VERIFIED",
        "- V7 composition executed runs: 0",
        "",
        "## GAP",
    ]
    lines.extend(f"- {gap}" for gap in report["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            f"- {report['maturity']}",
            f"- Positive period-return concentration: {report['observed_period_concentration_count']}/6 observed; {report['gap_period_concentration_count']}/6 gap.",
            f"- Best closed-trade sensitivity: {report['observed_closed_trade_sensitivity_count']}/6 observed.",
            f"- Positive closed-trade concentration: {report['observed_positive_closed_trade_concentration_count']}/6 observed; {report['gap_positive_closed_trade_concentration_count']}/6 gap.",
            "- UTC-month and closed-trade evidence is synthetic and bound to the simplified execution model.",
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
        description="Render the non-current synthetic benchmark v7 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v7(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v7(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
