from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src"
for import_root in (APP_ROOT, SOURCE_ROOT):
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)

from examples.build_synthetic_strategy_benchmark_report_v2 import (  # noqa: E402
    build_synthetic_strategy_benchmark_report_v2,
    plan_synthetic_strategy_benchmark_report_v2,
    render_synthetic_strategy_benchmark_report_markdown_v2,
    verify_synthetic_strategy_benchmark_report_v2,
)
from exchange_terminal.application.synthetic_strategy_bootstrap_validation_v1 import (  # noqa: E402
    build_synthetic_strategy_bootstrap_validation_v1,
    plan_synthetic_strategy_bootstrap_validation_v1,
    render_synthetic_strategy_bootstrap_validation_markdown_v1,
    verify_synthetic_strategy_bootstrap_validation_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v3"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v3"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v3"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_BENCHMARK_WITH_PARTIAL_REGIME_AND_BOOTSTRAP_CONFIDENCE"
STATUS = "BLOCK"

AUTHORITY = {
    "blind_test_complete": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}

GAPS = [
    "DEFLATED_SHARPE_RATIO_GAP",
    "DEPENDENCY_LOCK_HASH_GAP",
    "ENSEMBLE_STRATEGY_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "HIGH_VOLATILITY_REGIME_COVERAGE_GAP",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_GAP",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_SHA_GAP",
]


class SyntheticStrategyBenchmarkReportV3Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise SyntheticStrategyBenchmarkReportV3Error(message)


def _assert_exact_json(value: Any, path: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail(f"{path} keys must be exact str")
            _assert_exact_json(child, f"{path}.{key}")
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _assert_exact_json(child, f"{path}[{index}]")
        return
    if type(value) in {str, int, float, bool, type(None)}:
        return
    _fail(f"{path} must contain exact-native JSON values")


def _canonical_sha256(value: dict[str, Any]) -> str:
    _assert_exact_json(value, "hash_payload")
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _plan_payload_v3() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v2()
    bootstrap_plan = plan_synthetic_strategy_bootstrap_validation_v1()
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "source_report_plan": source_plan,
        "bootstrap_plan": bootstrap_plan,
        "planned_run_count": source_plan["planned_run_count"],
        "additional_backtest_run_count": 0,
        "planned_market_analysis_count": source_plan["planned_market_analysis_count"],
        "planned_bootstrap_analysis_count": bootstrap_plan["planned_analysis_count"],
        "executed_run_count": 0,
        "executed_market_analysis_count": 0,
        "executed_bootstrap_analysis_count": 0,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(GAPS),
        "authority": dict(AUTHORITY),
    }


def plan_synthetic_strategy_benchmark_report_v3() -> dict[str, Any]:
    payload = _plan_payload_v3()
    return {**payload, "plan_sha256": _canonical_sha256(payload)}


def verify_synthetic_strategy_benchmark_report_plan_v3(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(plan, "plan")
    expected = plan_synthetic_strategy_benchmark_report_v3()
    if plan != expected:
        _fail("benchmark report v3 plan does not match the registered plan")
    return {
        "valid": True,
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "planned_run_count": plan["planned_run_count"],
        "planned_bootstrap_analysis_count": plan[
            "planned_bootstrap_analysis_count"
        ],
        "additional_backtest_run_count": 0,
        "runtime_mutations": False,
    }


def _canonical_baseline_bundle(source_report: dict[str, Any]) -> dict[str, Any]:
    try:
        source_report_v1 = source_report["source_report_v1"]
        baseline_bundle = source_report_v1["baseline_bundle"]
    except (KeyError, TypeError) as exc:
        raise SyntheticStrategyBenchmarkReportV3Error(
            "source report v2 is missing the canonical v1 baseline bundle"
        ) from exc
    if type(source_report_v1) is not dict or type(baseline_bundle) is not dict:
        _fail("canonical v1 baseline bundle path must contain exact dict values")
    return baseline_bundle


def build_synthetic_strategy_benchmark_report_v3(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        _fail("execute must be exact bool")
    if execute is not True:
        return plan_synthetic_strategy_benchmark_report_v3()

    plan = plan_synthetic_strategy_benchmark_report_v3()
    source_report = build_synthetic_strategy_benchmark_report_v2(execute=True)
    try:
        verify_synthetic_strategy_benchmark_report_v2(source_report)
    except Exception as exc:
        raise SyntheticStrategyBenchmarkReportV3Error(
            "source benchmark report v2 failed verification"
        ) from exc

    baseline_bundle = _canonical_baseline_bundle(source_report)
    bootstrap_bundle = build_synthetic_strategy_bootstrap_validation_v1(
        baseline_bundle,
        execute=True,
    )
    try:
        verify_synthetic_strategy_bootstrap_validation_v1(
            bootstrap_bundle,
            baseline_bundle,
        )
    except Exception as exc:
        raise SyntheticStrategyBenchmarkReportV3Error(
            "bootstrap validation bundle failed verification"
        ) from exc

    if source_report["additional_backtest_run_count"] != 0:
        _fail("source report v2 unexpectedly added backtest runs")
    if bootstrap_bundle["planned_run_count"] != 0:
        _fail("bootstrap validation unexpectedly planned backtest runs")
    if bootstrap_bundle["executed_run_count"] != 0:
        _fail("bootstrap validation unexpectedly executed backtest runs")
    if source_report["runtime_mutations"] is not False:
        _fail("source report v2 reported runtime mutations")
    if bootstrap_bundle["runtime_mutations"] is not False:
        _fail("bootstrap validation reported runtime mutations")

    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "plan": plan,
        "source_report_v2": source_report,
        "bootstrap_validation": bootstrap_bundle,
        "bindings": {
            "source_report_v2_sha256": source_report["report_sha256"],
            "source_report_v2_plan_sha256": source_report["plan"]["plan_sha256"],
            "source_baseline_bundle_sha256": baseline_bundle["bundle_sha256"],
            "bootstrap_bundle_sha256": bootstrap_bundle["bundle_sha256"],
            "bootstrap_plan_sha256": bootstrap_bundle["plan"]["plan_sha256"],
        },
        "planned_run_count": source_report["planned_run_count"],
        "executed_run_count": source_report["executed_run_count"],
        "additional_backtest_run_count": bootstrap_bundle["executed_run_count"],
        "market_analysis_count": source_report["market_analysis_count"],
        "bootstrap_analysis_count": bootstrap_bundle["executed_analysis_count"],
        "observed_bootstrap_evidence_count": bootstrap_bundle[
            "observed_evidence_count"
        ],
        "gap_bootstrap_evidence_count": bootstrap_bundle["gap_evidence_count"],
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": list(GAPS),
        "authority": dict(AUTHORITY),
    }
    report = {**payload, "report_sha256": _canonical_sha256(payload)}
    verify_synthetic_strategy_benchmark_report_v3(report)
    return report


def verify_synthetic_strategy_benchmark_report_v3(
    report: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(report, "report")
    required_keys = {
        "schema_version",
        "report_id",
        "data_source",
        "plan",
        "source_report_v2",
        "bootstrap_validation",
        "bindings",
        "planned_run_count",
        "executed_run_count",
        "additional_backtest_run_count",
        "market_analysis_count",
        "bootstrap_analysis_count",
        "observed_bootstrap_evidence_count",
        "gap_bootstrap_evidence_count",
        "runtime_mutations",
        "evidence_state",
        "maturity",
        "status",
        "gaps",
        "authority",
        "report_sha256",
    }
    if set(report) != required_keys:
        _fail("benchmark report v3 fields do not match the contract")
    if report["schema_version"] != REPORT_SCHEMA_VERSION:
        _fail("benchmark report v3 schema_version mismatch")
    if report["report_id"] != REPORT_ID:
        _fail("benchmark report v3 report_id mismatch")
    if report["data_source"] != DATA_SOURCE:
        _fail("benchmark report v3 data_source mismatch")
    if report["evidence_state"] != EVIDENCE_STATE:
        _fail("benchmark report v3 evidence_state must remain GAP")
    if report["maturity"] != MATURITY or report["status"] != STATUS:
        _fail("benchmark report v3 maturity or status mismatch")
    if report["gaps"] != GAPS:
        _fail("benchmark report v3 gaps mismatch")
    if report["authority"] != AUTHORITY:
        _fail("benchmark report v3 authority must remain denied")
    if report["runtime_mutations"] is not False:
        _fail("benchmark report v3 runtime_mutations must be false")

    verify_synthetic_strategy_benchmark_report_plan_v3(report["plan"])
    source_report = report["source_report_v2"]
    try:
        verify_synthetic_strategy_benchmark_report_v2(source_report)
    except Exception as exc:
        raise SyntheticStrategyBenchmarkReportV3Error(
            "source benchmark report v2 failed verification"
        ) from exc
    baseline_bundle = _canonical_baseline_bundle(source_report)
    bootstrap_bundle = report["bootstrap_validation"]
    try:
        verify_synthetic_strategy_bootstrap_validation_v1(
            bootstrap_bundle,
            baseline_bundle,
        )
    except Exception as exc:
        raise SyntheticStrategyBenchmarkReportV3Error(
            "bootstrap validation bundle failed verification"
        ) from exc

    expected_bindings = {
        "source_report_v2_sha256": source_report["report_sha256"],
        "source_report_v2_plan_sha256": source_report["plan"]["plan_sha256"],
        "source_baseline_bundle_sha256": baseline_bundle["bundle_sha256"],
        "bootstrap_bundle_sha256": bootstrap_bundle["bundle_sha256"],
        "bootstrap_plan_sha256": bootstrap_bundle["plan"]["plan_sha256"],
    }
    if report["bindings"] != expected_bindings:
        _fail("benchmark report v3 source bindings mismatch")
    if report["planned_run_count"] != report["plan"]["planned_run_count"]:
        _fail("benchmark report v3 planned_run_count mismatch")
    if report["planned_run_count"] != source_report["planned_run_count"]:
        _fail("benchmark report v3 source planned_run_count mismatch")
    if report["executed_run_count"] != source_report["executed_run_count"]:
        _fail("benchmark report v3 executed_run_count mismatch")
    if report["additional_backtest_run_count"] != 0:
        _fail("bootstrap integration must not add backtest runs")
    if bootstrap_bundle["planned_run_count"] != 0:
        _fail("bootstrap bundle must not plan backtest runs")
    if bootstrap_bundle["executed_run_count"] != 0:
        _fail("bootstrap bundle must not execute backtest runs")
    if report["market_analysis_count"] != source_report["market_analysis_count"]:
        _fail("benchmark report v3 market analysis count mismatch")
    if report["bootstrap_analysis_count"] != bootstrap_bundle[
        "executed_analysis_count"
    ]:
        _fail("benchmark report v3 bootstrap analysis count mismatch")
    if report["bootstrap_analysis_count"] != report["plan"][
        "planned_bootstrap_analysis_count"
    ]:
        _fail("benchmark report v3 bootstrap plan was not fully executed")
    if report["observed_bootstrap_evidence_count"] != bootstrap_bundle[
        "observed_evidence_count"
    ]:
        _fail("benchmark report v3 observed bootstrap count mismatch")
    if report["gap_bootstrap_evidence_count"] != bootstrap_bundle[
        "gap_evidence_count"
    ]:
        _fail("benchmark report v3 gap bootstrap count mismatch")
    if source_report["runtime_mutations"] is not False:
        _fail("source report v2 runtime_mutations must be false")
    if bootstrap_bundle["runtime_mutations"] is not False:
        _fail("bootstrap bundle runtime_mutations must be false")

    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    expected_sha256 = _canonical_sha256(payload)
    if report["report_sha256"] != expected_sha256:
        _fail("benchmark report v3 report_sha256 mismatch")
    return {
        "valid": True,
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_sha256": expected_sha256,
        "source_report_v2_sha256": source_report["report_sha256"],
        "bootstrap_bundle_sha256": bootstrap_bundle["bundle_sha256"],
        "executed_run_count": report["executed_run_count"],
        "additional_backtest_run_count": 0,
        "bootstrap_analysis_count": report["bootstrap_analysis_count"],
        "runtime_mutations": False,
        "status": STATUS,
    }


def render_synthetic_strategy_benchmark_report_plan_markdown_v3(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v3(plan)
    gap_text = ", ".join(plan["gaps"])
    return "\n".join(
        [
            "# Deterministic Synthetic Strategy Benchmark Plan v3",
            "",
            f"- SOURCE: {plan['data_source']}",
            f"- GAP: {gap_text}",
            f"- MATURITY: {plan['maturity']}",
            f"- PERMISSION: {plan['status']}",
            f"- Planned source backtest runs: {plan['planned_run_count']}",
            "- Additional bootstrap backtest runs: 0",
            f"- Planned market analyses: {plan['planned_market_analysis_count']}",
            f"- Planned bootstrap analyses: {plan['planned_bootstrap_analysis_count']}",
            "- Formal inference claimed: false",
            "- Profitability, blind-test, paper, live, and order authority: false",
            "",
        ]
    )


def render_synthetic_strategy_benchmark_report_markdown_v3(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v3(report)
    baseline_bundle = _canonical_baseline_bundle(report["source_report_v2"])
    gap_text = ", ".join(report["gaps"])
    source_markdown = render_synthetic_strategy_benchmark_report_markdown_v2(
        report["source_report_v2"]
    ).rstrip()
    bootstrap_markdown = render_synthetic_strategy_bootstrap_validation_markdown_v1(
        report["bootstrap_validation"],
        baseline_bundle,
    ).rstrip()
    return "\n".join(
        [
            "# Deterministic Synthetic Strategy Benchmark Report v3",
            "",
            f"- SOURCE: {report['data_source']}",
            f"- GAP: {gap_text}",
            f"- MATURITY: {report['maturity']}",
            f"- PERMISSION: {report['status']}",
            f"- Executed source backtest runs: {report['executed_run_count']}",
            "- Additional bootstrap backtest runs: 0",
            f"- Market analyses: {report['market_analysis_count']}",
            f"- Bootstrap analyses: {report['bootstrap_analysis_count']}",
            "- Bootstrap intervals are descriptive synthetic evidence only.",
            "- No formal inference, significance, profitability, blind-test, paper, live, or order authority is claimed.",
            "",
            "## Source benchmark report v2",
            "",
            source_markdown,
            "",
            "## Paired moving-block bootstrap evidence",
            "",
            bootstrap_markdown,
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic synthetic strategy benchmark report v3."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the pure in-memory synthetic source and bootstrap analyses.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    artifact = build_synthetic_strategy_benchmark_report_v3(execute=args.execute)
    if args.format == "markdown":
        if args.execute:
            text = render_synthetic_strategy_benchmark_report_markdown_v3(artifact)
        else:
            text = render_synthetic_strategy_benchmark_report_plan_markdown_v3(
                artifact
            )
    else:
        text = json.dumps(artifact, ensure_ascii=True, indent=2, sort_keys=True) + "\n"

    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
