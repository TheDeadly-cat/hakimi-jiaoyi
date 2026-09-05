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


from examples.build_synthetic_strategy_benchmark_report_v1 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v1,
    plan_synthetic_strategy_benchmark_report_v1,
    render_synthetic_strategy_benchmark_report_markdown_v1,
    verify_synthetic_strategy_benchmark_report_plan_v1,
    verify_synthetic_strategy_benchmark_report_v1,
)
from exchange_terminal.application.synthetic_strategy_market_regime_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_market_regime_validation_v1,
    plan_synthetic_strategy_market_regime_validation_v1,
    render_synthetic_strategy_market_regime_validation_markdown_v1,
    verify_synthetic_strategy_market_regime_validation_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v2"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v2"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v2"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
EVIDENCE_STATE = "GAP"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_BENCHMARK_WITH_PARTIAL_REGIME_COVERAGE"

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
    "HIGH_VOLATILITY_REGIME_COVERAGE_GAP",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_SHA_GAP",
]


class SyntheticStrategyBenchmarkReportV2Error(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyBenchmarkReportV2Error(f"{path}: {message}")


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


def plan_synthetic_strategy_benchmark_report_v2() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v1()
    verify_synthetic_strategy_benchmark_report_plan_v1(source_plan)
    regime_plan = plan_synthetic_strategy_market_regime_validation_v1()
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "source_report_plan": source_plan,
        "market_regime_plan": regime_plan,
        "planned_run_count": source_plan["planned_run_count"],
        "executed_run_count": 0,
        "planned_market_analysis_count": regime_plan["planned_analysis_count"],
        "executed_market_analysis_count": 0,
        "additional_backtest_run_count": 0,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def verify_synthetic_strategy_benchmark_report_plan_v2(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        _fail("plan", "must be an exact dict")
    expected = plan_synthetic_strategy_benchmark_report_v2()
    if plan != expected:
        _fail("plan", "must equal the deterministic v2 preregistration")
    return {
        "schema_version": "synthetic-strategy-benchmark-report-plan-receipt-v2",
        "state": "VERIFIED",
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "plan_sha256": plan["plan_sha256"],
        "planned_run_count": plan["planned_run_count"],
        "executed_run_count": 0,
        "planned_market_analysis_count": plan["planned_market_analysis_count"],
        "additional_backtest_run_count": 0,
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def build_synthetic_strategy_benchmark_report_v2(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool or execute is not True:
        raise SyntheticStrategyBenchmarkReportV2Error(
            "execution requires exact execute=True; inspect the v2 plan first"
        )
    plan = plan_synthetic_strategy_benchmark_report_v2()
    verify_synthetic_strategy_benchmark_report_plan_v2(plan)
    source_report = build_synthetic_strategy_benchmark_report_v1(execute=True)
    verify_synthetic_strategy_benchmark_report_v1(source_report)
    market_regime_validation = build_synthetic_strategy_market_regime_validation_v1(
        source_report["baseline_bundle"],
        source_report["robustness_evidence"],
        execute=True,
    )
    regime_receipt = verify_synthetic_strategy_market_regime_validation_v1(
        market_regime_validation,
        source_report["baseline_bundle"],
        source_report["robustness_evidence"],
    )
    bindings = {
        "source_report_plan_sha256": source_report["plan"]["plan_sha256"],
        "source_report_sha256": source_report["report_sha256"],
        "market_regime_plan_sha256": market_regime_validation["plan"]["plan_sha256"],
        "market_regime_bundle_sha256": market_regime_validation["bundle_sha256"],
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "plan": plan,
        "source_report_v1": source_report,
        "market_regime_validation": market_regime_validation,
        "bindings": bindings,
        "planned_run_count": plan["planned_run_count"],
        "executed_run_count": plan["planned_run_count"],
        "market_analysis_count": regime_receipt["strategy_count"],
        "additional_backtest_run_count": 0,
        "observed_regime_slice_count": regime_receipt["observed_slice_count"],
        "gap_regime_slice_count": regime_receipt["gap_slice_count"],
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    report["report_sha256"] = _canonical_sha256(report)
    verify_synthetic_strategy_benchmark_report_v2(report)
    return report


def verify_synthetic_strategy_benchmark_report_v2(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        _fail("report", "must be an exact dict")
    expected_keys = {
        "schema_version",
        "report_id",
        "data_source",
        "evidence_state",
        "status",
        "maturity",
        "plan",
        "source_report_v1",
        "market_regime_validation",
        "bindings",
        "planned_run_count",
        "executed_run_count",
        "market_analysis_count",
        "additional_backtest_run_count",
        "observed_regime_slice_count",
        "gap_regime_slice_count",
        "runtime_mutations",
        "gaps",
        "authority",
        "report_sha256",
    }
    if set(report) != expected_keys:
        _fail("report", f"must contain exactly {sorted(expected_keys)}")
    if report["schema_version"] != REPORT_SCHEMA_VERSION:
        _fail("report.schema_version", f"must equal {REPORT_SCHEMA_VERSION}")
    if report["report_id"] != REPORT_ID or report["data_source"] != DATA_SOURCE:
        _fail("report", "must retain the deterministic synthetic identity")
    if report["evidence_state"] != EVIDENCE_STATE:
        _fail("report.evidence_state", "must remain GAP while high-volatility is absent")
    if report["status"] != STATUS or report["maturity"] != MATURITY:
        _fail("report", "must retain BLOCK and partial-regime maturity")
    if report["runtime_mutations"] is not False:
        _fail("report.runtime_mutations", "must be exact false")
    if report["gaps"] != _gaps() or report["authority"] != _authority():
        _fail("report", "must retain the canonical gaps and all-false authority")
    if report["plan"] != plan_synthetic_strategy_benchmark_report_v2():
        _fail("report.plan", "must equal the deterministic v2 plan")

    source_report = report["source_report_v1"]
    source_receipt = verify_synthetic_strategy_benchmark_report_v1(source_report)
    regime_receipt = verify_synthetic_strategy_market_regime_validation_v1(
        report["market_regime_validation"],
        source_report["baseline_bundle"],
        source_report["robustness_evidence"],
    )
    expected_bindings = {
        "source_report_plan_sha256": source_report["plan"]["plan_sha256"],
        "source_report_sha256": source_report["report_sha256"],
        "market_regime_plan_sha256": report["market_regime_validation"]["plan"][
            "plan_sha256"
        ],
        "market_regime_bundle_sha256": report["market_regime_validation"][
            "bundle_sha256"
        ],
    }
    if type(report["bindings"]) is not dict or report["bindings"] != expected_bindings:
        _fail("report.bindings", "must bind the verified v1 report and regime bundle")
    if report["planned_run_count"] != source_receipt["planned_run_count"]:
        _fail("report.planned_run_count", "must match the verified v1 report")
    if report["executed_run_count"] != source_receipt["executed_run_count"]:
        _fail("report.executed_run_count", "must match the verified v1 report")
    if report["market_analysis_count"] != regime_receipt["strategy_count"]:
        _fail("report.market_analysis_count", "must cover all verified strategies")
    if report["additional_backtest_run_count"] != 0:
        _fail("report.additional_backtest_run_count", "must be zero")
    if (
        report["observed_regime_slice_count"]
        != regime_receipt["observed_slice_count"]
    ):
        _fail("report.observed_regime_slice_count", "must match the regime receipt")
    if report["gap_regime_slice_count"] != regime_receipt["gap_slice_count"]:
        _fail("report.gap_regime_slice_count", "must match the regime receipt")
    without_hash = dict(report)
    report_sha256 = without_hash.pop("report_sha256")
    if type(report_sha256) is not str or report_sha256 != _canonical_sha256(without_hash):
        _fail("report.report_sha256", "must match the canonical v2 report digest")
    return {
        "schema_version": "synthetic-strategy-benchmark-report-receipt-v2",
        "state": "VERIFIED",
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "report_sha256": report_sha256,
        "planned_run_count": report["planned_run_count"],
        "executed_run_count": report["executed_run_count"],
        "market_analysis_count": report["market_analysis_count"],
        "additional_backtest_run_count": 0,
        "observed_regime_slice_count": report["observed_regime_slice_count"],
        "gap_regime_slice_count": report["gap_regime_slice_count"],
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def render_synthetic_strategy_benchmark_report_plan_markdown_v2(
    plan: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_plan_v2(plan)
    return "\n".join(
        [
            "# Synthetic Strategy Benchmark Report Plan v2",
            "",
            "## SOURCE",
            f"- Data source: {DATA_SOURCE}",
            f"- Planned source runs: {receipt['planned_run_count']}",
            f"- Planned market analyses: {receipt['planned_market_analysis_count']}",
            "- Executed runs: 0",
            "- Additional backtest runs: 0",
            "- Runtime mutations: false",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {MATURITY}",
            f"- Evidence state: {EVIDENCE_STATE}",
            "",
            "## PERMISSION",
            f"- Status: {STATUS}",
            "- Profitability proof: false",
            "- Blind-test completion: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Plan SHA-256: `{receipt['plan_sha256']}`",
        ]
    )


def render_synthetic_strategy_benchmark_report_markdown_v2(
    report: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_v2(report)
    source_markdown = render_synthetic_strategy_benchmark_report_markdown_v1(
        report["source_report_v1"]
    )
    regime_markdown = render_synthetic_strategy_market_regime_validation_markdown_v1(
        report["market_regime_validation"],
        report["source_report_v1"]["baseline_bundle"],
        report["source_report_v1"]["robustness_evidence"],
    )
    return "\n".join(
        [
            "# Synthetic Strategy Benchmark Report v2",
            "",
            "## SOURCE",
            f"- Data source: {DATA_SOURCE}",
            f"- Executed source runs: {receipt['executed_run_count']}",
            f"- Market analyses: {receipt['market_analysis_count']}",
            "- Additional backtest runs: 0",
            "- Runtime mutations: false",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            f"- Evidence state: {receipt['evidence_state']}",
            "",
            "## PERMISSION",
            f"- Status: {receipt['status']}",
            "- Profitability proof: false",
            "- Blind-test completion: false",
            "- Paper, live, and order-entry authorization: false",
            "",
            f"Report SHA-256: `{receipt['report_sha256']}`",
            "",
            "## Immutable v1 Source Report",
            "",
            "The nested v1 market-regime gap is retained as historical source state; "
            "the v2 layer adds partial regime evidence without rewriting v1.",
            "",
            source_markdown,
            "",
            "## Market-Regime Validation Layer",
            "",
            regime_markdown,
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render synthetic benchmark v2. The default is a dry plan; --execute "
            "is required for the complete in-memory source and regime analysis."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute the 179 source runs and six zero-backtest regime analyses",
    )
    args = parser.parse_args(argv)
    if args.execute:
        report = build_synthetic_strategy_benchmark_report_v2(execute=True)
        print(render_synthetic_strategy_benchmark_report_markdown_v2(report))
    else:
        plan = plan_synthetic_strategy_benchmark_report_v2()
        print(render_synthetic_strategy_benchmark_report_plan_markdown_v2(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
