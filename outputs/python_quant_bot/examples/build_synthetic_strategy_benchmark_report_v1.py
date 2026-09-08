from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


_APP_ROOT = Path(__file__).resolve().parents[1]
_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_RESEARCH_SOURCE_ROOT = _REPOSITORY_ROOT / "src"
for _source_root in (_APP_ROOT, _RESEARCH_SOURCE_ROOT):
    _source_root_text = str(_source_root)
    if _source_root_text not in sys.path:
        sys.path.insert(0, _source_root_text)


from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (  # noqa: E402
    build_synthetic_strategy_report_bundle_v1,
    plan_synthetic_strategy_report_bundle_v1,
    render_synthetic_strategy_report_bundle_markdown_v1,
    verify_synthetic_strategy_report_bundle_v1,
)
from exchange_terminal.application.synthetic_strategy_robustness_evidence_v1 import (  # noqa: E402
    build_synthetic_strategy_robustness_evidence_v1,
    plan_synthetic_strategy_robustness_evidence_v1,
    render_synthetic_strategy_robustness_markdown_v1,
    verify_synthetic_strategy_robustness_evidence_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v1"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v1"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v1"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
MATURITY = "SYNTHETIC_BENCHMARK_ONLY"
STATUS = "BLOCK"

_AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "BOOTSTRAP_CONFIDENCE_INTERVAL_GAP",
    "DEFLATED_SHARPE_RATIO_GAP",
    "DEPENDENCY_LOCK_HASH_GAP",
    "ENSEMBLE_STRATEGY_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "MARKET_REGIME_ANALYSIS_GAP",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_SHA_GAP",
]


class SyntheticStrategyBenchmarkReportError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyBenchmarkReportError(f"{path}: {message}")


def _require_exact_dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        _fail(path, f"must contain exactly {sorted(expected)}")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _gaps() -> list[str]:
    return list(_GAPS)


def plan_synthetic_strategy_benchmark_report_v1() -> dict[str, Any]:
    baseline_plan = plan_synthetic_strategy_report_bundle_v1()
    robustness_plan = plan_synthetic_strategy_robustness_evidence_v1()
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "status": STATUS,
        "maturity": MATURITY,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "planned_run_count": (
            baseline_plan["planned_run_count"] + robustness_plan["planned_run_count"]
        ),
        "executed_run_count": 0,
        "baseline_plan": baseline_plan,
        "robustness_plan": robustness_plan,
        "authority": _authority(),
        "gaps": _gaps(),
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def verify_synthetic_strategy_benchmark_report_plan_v1(
    plan: dict[str, Any],
) -> dict[str, Any]:
    value = _require_exact_dict(plan, "plan")
    expected = plan_synthetic_strategy_benchmark_report_v1()
    if value != expected:
        _fail("plan", "does not match the deterministic preregistered plan")
    return {
        "schema_version": "synthetic-strategy-benchmark-report-plan-receipt-v1",
        "state": "VERIFIED",
        "plan_sha256": value["plan_sha256"],
        "planned_run_count": value["planned_run_count"],
        "executed_run_count": 0,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def build_synthetic_strategy_benchmark_report_v1(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBenchmarkReportError(
            "execution requires exact execute=True; inspect the plan first"
        )

    plan = plan_synthetic_strategy_benchmark_report_v1()
    verify_synthetic_strategy_benchmark_report_plan_v1(plan)

    baseline_bundle = build_synthetic_strategy_report_bundle_v1(execute=True)
    verify_synthetic_strategy_report_bundle_v1(baseline_bundle)
    robustness_evidence = build_synthetic_strategy_robustness_evidence_v1(
        baseline_bundle,
        execute=True,
    )
    verify_synthetic_strategy_robustness_evidence_v1(robustness_evidence)

    bindings = {
        "baseline_plan_sha256": plan["baseline_plan"]["plan_sha256"],
        "baseline_bundle_sha256": _canonical_sha256(baseline_bundle),
        "robustness_plan_sha256": plan["robustness_plan"]["plan_sha256"],
        "robustness_evidence_sha256": _canonical_sha256(robustness_evidence),
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "status": STATUS,
        "maturity": MATURITY,
        "runtime_mutations": False,
        "planned_run_count": plan["planned_run_count"],
        "executed_run_count": plan["planned_run_count"],
        "plan": plan,
        "baseline_bundle": baseline_bundle,
        "robustness_evidence": robustness_evidence,
        "bindings": bindings,
        "authority": _authority(),
        "gaps": _gaps(),
    }
    report["report_sha256"] = _canonical_sha256(report)
    verify_synthetic_strategy_benchmark_report_v1(report)
    return report


def verify_synthetic_strategy_benchmark_report_v1(
    report: dict[str, Any],
) -> dict[str, Any]:
    value = _require_exact_dict(report, "report")
    _require_exact_keys(
        value,
        {
            "schema_version",
            "report_id",
            "data_source",
            "status",
            "maturity",
            "runtime_mutations",
            "planned_run_count",
            "executed_run_count",
            "plan",
            "baseline_bundle",
            "robustness_evidence",
            "bindings",
            "authority",
            "gaps",
            "report_sha256",
        },
        "report",
    )
    if value["schema_version"] != REPORT_SCHEMA_VERSION:
        _fail("report.schema_version", f"must equal {REPORT_SCHEMA_VERSION}")
    if value["report_id"] != REPORT_ID:
        _fail("report.report_id", f"must equal {REPORT_ID}")
    if value["data_source"] != DATA_SOURCE:
        _fail("report.data_source", f"must equal {DATA_SOURCE}")
    if value["status"] != STATUS or value["maturity"] != MATURITY:
        _fail("report", "must remain BLOCK and SYNTHETIC_BENCHMARK_ONLY")
    if value["runtime_mutations"] is not False:
        _fail("report.runtime_mutations", "must be exact false")
    if value["authority"] != _authority():
        _fail("report.authority", "must retain the all-false authority contract")
    if value["gaps"] != _gaps():
        _fail("report.gaps", "must retain the canonical unresolved-gap list")

    plan_receipt = verify_synthetic_strategy_benchmark_report_plan_v1(value["plan"])
    planned_run_count = plan_receipt["planned_run_count"]
    if type(value["planned_run_count"]) is not int:
        _fail("report.planned_run_count", "must be an exact int")
    if type(value["executed_run_count"]) is not int:
        _fail("report.executed_run_count", "must be an exact int")
    if value["planned_run_count"] != planned_run_count:
        _fail("report.planned_run_count", "must match the verified plan")
    if value["executed_run_count"] != planned_run_count:
        _fail("report.executed_run_count", "must equal the complete planned run count")

    verify_synthetic_strategy_report_bundle_v1(value["baseline_bundle"])
    verify_synthetic_strategy_robustness_evidence_v1(value["robustness_evidence"])
    bindings = _require_exact_dict(value["bindings"], "report.bindings")
    _require_exact_keys(
        bindings,
        {
            "baseline_plan_sha256",
            "baseline_bundle_sha256",
            "robustness_plan_sha256",
            "robustness_evidence_sha256",
        },
        "report.bindings",
    )
    expected_bindings = {
        "baseline_plan_sha256": value["plan"]["baseline_plan"]["plan_sha256"],
        "baseline_bundle_sha256": _canonical_sha256(value["baseline_bundle"]),
        "robustness_plan_sha256": value["plan"]["robustness_plan"]["plan_sha256"],
        "robustness_evidence_sha256": _canonical_sha256(value["robustness_evidence"]),
    }
    if bindings != expected_bindings:
        _fail("report.bindings", "must match the verified plan and evidence digests")

    report_without_hash = dict(value)
    report_sha256 = report_without_hash.pop("report_sha256")
    if type(report_sha256) is not str:
        _fail("report.report_sha256", "must be an exact str")
    if report_sha256 != _canonical_sha256(report_without_hash):
        _fail("report.report_sha256", "does not match the canonical report digest")

    return {
        "schema_version": "synthetic-strategy-benchmark-report-receipt-v1",
        "state": "VERIFIED",
        "report_sha256": report_sha256,
        "planned_run_count": planned_run_count,
        "executed_run_count": value["executed_run_count"],
        "runtime_mutations": False,
        "status": STATUS,
        "maturity": MATURITY,
        "authority": _authority(),
        "gaps": _gaps(),
    }


def render_synthetic_strategy_benchmark_report_plan_markdown_v1(
    plan: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_plan_v1(plan)
    return "\n".join(
        [
            "# Synthetic Strategy Benchmark Report Plan v1",
            "",
            "## SOURCE",
            f"- Data source: {DATA_SOURCE}",
            f"- Planned runs: {receipt['planned_run_count']}",
            "- Executed runs: 0",
            "- Runtime mutations: false",
            "",
            "## GAP",
            *[f"- {gap}" for gap in _gaps()],
            "",
            "## MATURITY",
            f"- {MATURITY}",
            "- Status: BLOCK",
            "",
            "## PERMISSION",
            "- Research-only planning",
            "- Profitability proof: false",
            "- Blind-test completion: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Plan SHA-256: `{receipt['plan_sha256']}`",
        ]
    )


def render_synthetic_strategy_benchmark_report_markdown_v1(
    report: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_v1(report)
    baseline_markdown = render_synthetic_strategy_report_bundle_markdown_v1(
        report["baseline_bundle"]
    )
    robustness_markdown = render_synthetic_strategy_robustness_markdown_v1(
        report["robustness_evidence"]
    )
    return "\n".join(
        [
            "# Synthetic Strategy Benchmark Report v1",
            "",
            "## SOURCE",
            f"- Data source: {DATA_SOURCE}",
            f"- Planned runs: {receipt['planned_run_count']}",
            f"- Executed runs: {receipt['executed_run_count']}",
            "- Runtime mutations: false",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Status: {receipt['status']}",
            "",
            "## PERMISSION",
            "- Research-only synthetic evidence",
            "- Profitability proof: false",
            "- Blind-test completion: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Report SHA-256: `{receipt['report_sha256']}`",
            "",
            "## Frozen and Cost-Stress Evidence",
            "",
            baseline_markdown,
            "",
            "## Walk-Forward, Stability, and Multiplicity Evidence",
            "",
            robustness_markdown,
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a deterministic synthetic research benchmark. The default is a "
            "dry plan; --execute is required for the complete in-memory run."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute all 179 pure synthetic in-memory research runs",
    )
    args = parser.parse_args(argv)
    if args.execute:
        report = build_synthetic_strategy_benchmark_report_v1(execute=True)
        print(render_synthetic_strategy_benchmark_report_markdown_v1(report))
    else:
        plan = plan_synthetic_strategy_benchmark_report_v1()
        print(render_synthetic_strategy_benchmark_report_plan_markdown_v1(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
