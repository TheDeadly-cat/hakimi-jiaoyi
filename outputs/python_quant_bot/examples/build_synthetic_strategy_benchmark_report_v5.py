from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable


PYTHON_QUANT_BOT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PYTHON_QUANT_BOT_ROOT.parents[1]
for import_root in (PYTHON_QUANT_BOT_ROOT, WORKSPACE_ROOT / "src"):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from examples.build_synthetic_strategy_benchmark_report_v4 import (  # noqa: E402
    plan_synthetic_strategy_benchmark_report_v4,
    verify_synthetic_strategy_benchmark_report_v4,
)
from exchange_terminal.application.synthetic_strategy_high_volatility_validation_v1 import (  # noqa: E402
    plan_synthetic_strategy_high_volatility_validation_v1,
    verify_synthetic_strategy_high_volatility_validation_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v5"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v5"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v5"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v5"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_REGIME_BOOTSTRAP_DSR_AND_PARTIAL_PBO_DIAGNOSTICS"
)
STATUS = "BLOCK"

_GAPS = (
    "DEPENDENCY_LOCK_HASH_GAP",
    "ENSEMBLE_STRATEGY_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "HIGH_VOLATILITY_SYNTHETIC_SCENARIO_ONLY",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "ODD_THREE_TRIAL_MEDIAN_BOUNDARY_SENSITIVITY",
    "PARTIAL_CSCV_RANK_TIE_GAP",
    "REAL_DATASET_GAP",
    "SOURCE_COMMIT_SHA_GAP",
    "THREE_TRIAL_RANK_RESOLUTION_LIMIT",
    "THREE_TRIAL_SYNTHETIC_DIAGNOSTIC_ONLY",
    "TRAILING_OBSERVATION_EXCLUDED_FOR_EQUAL_CSCV_PARTITIONS",
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyBenchmarkReportV5Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise SyntheticStrategyBenchmarkReportV5Error(message)


def _gaps() -> list[str]:
    return list(_GAPS)


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _assert_exact_json(value: Any, path: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail(f"{path} contains a non-native string key")
            _assert_exact_json(child, f"{path}.{key}")
        return
    if type(value) is list:
        for index, child in enumerate(value):
            _assert_exact_json(child, f"{path}[{index}]")
        return
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    _fail(f"{path} must contain exact finite JSON-native values")


def _canonical_sha256(value: dict[str, Any]) -> str:
    _assert_exact_json(value, "canonical_payload")
    payload = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _call_verifier(
    label: str,
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
    artifact: dict[str, Any],
) -> None:
    try:
        receipt = verifier(artifact)
    except Exception as exc:
        raise SyntheticStrategyBenchmarkReportV5Error(
            f"{label} failed verification: {type(exc).__name__}: {exc}"
        ) from exc
    if type(receipt) is not dict:
        _fail(f"{label} verifier did not return an exact dict receipt")


def _plan_payload_v5() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v4()
    high_volatility_plan = plan_synthetic_strategy_high_volatility_validation_v1()
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "source_report_plan": source_plan,
        "high_volatility_validation_plan": high_volatility_plan,
        "inherited_source_logical_run_count": source_plan[
            "source_logical_run_count"
        ],
        "high_volatility_source_run_count": high_volatility_plan[
            "planned_run_count"
        ],
        "source_logical_run_count": (
            source_plan["source_logical_run_count"]
            + high_volatility_plan["planned_run_count"]
        ),
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_high_volatility_analysis_count": high_volatility_plan[
            "planned_analysis_count"
        ],
        "requires_prebuilt_sources": True,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def plan_synthetic_strategy_benchmark_report_v5() -> dict[str, Any]:
    payload = _plan_payload_v5()
    return {**payload, "plan_sha256": _canonical_sha256(payload)}


def verify_synthetic_strategy_benchmark_report_plan_v5(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(plan, "plan")
    if plan != plan_synthetic_strategy_benchmark_report_v5():
        _fail("benchmark report v5 plan does not match deterministic preregistration")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "PASS",
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_planned_run_count": 0,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def _verified_sources(
    source_report_v4: dict[str, Any],
    high_volatility_validation: dict[str, Any],
) -> dict[str, Any]:
    for label, verifier, artifact in (
        ("source_report_v4", verify_synthetic_strategy_benchmark_report_v4, source_report_v4),
        (
            "high_volatility_validation",
            verify_synthetic_strategy_high_volatility_validation_v1,
            high_volatility_validation,
        ),
    ):
        if type(artifact) is not dict:
            _fail(f"{label} must be an exact dict")
        _assert_exact_json(artifact, label)
        _call_verifier(label, verifier, artifact)

    source_strategy_ids = source_report_v4["trial_return_matrix"]["plan"][
        "registered_strategy_ids"
    ]
    high_volatility_strategy_ids = high_volatility_validation["plan"][
        "registered_strategy_ids"
    ]
    if source_strategy_ids != high_volatility_strategy_ids:
        _fail("v4 and high-volatility validation strategy order mismatch")
    if "HIGH_VOLATILITY_REGIME_COVERAGE_GAP" not in source_report_v4["gaps"]:
        _fail("v4 source no longer exposes the historical high-volatility gap")
    if (
        high_volatility_validation["observed_target_slice_count"]
        != len(source_strategy_ids)
        or high_volatility_validation["gap_target_slice_count"] != 0
    ):
        _fail("high-volatility validation does not cover every registered strategy")
    if source_report_v4["source_logical_run_count"] != 179:
        _fail("v4 logical source run count drifted")
    if high_volatility_validation["executed_run_count"] != 7:
        _fail("high-volatility source run count drifted")
    if high_volatility_validation["executed_analysis_count"] != 6:
        _fail("high-volatility analysis count drifted")
    if (
        source_report_v4["runtime_mutations"] is not False
        or high_volatility_validation["runtime_mutations"] is not False
    ):
        _fail("a source reported runtime mutations")
    return {
        "strategy_ids": source_strategy_ids,
        "high_volatility_observed_count": high_volatility_validation[
            "observed_target_slice_count"
        ],
        "high_volatility_gap_count": high_volatility_validation[
            "gap_target_slice_count"
        ],
    }


def build_synthetic_strategy_benchmark_report_v5(
    source_report_v4: dict[str, Any] | None = None,
    high_volatility_validation: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        _fail("execute must be exact bool")
    plan = plan_synthetic_strategy_benchmark_report_v5()
    if not execute:
        if source_report_v4 is not None or high_volatility_validation is not None:
            _fail("dry plan must not silently accept unverified source artifacts")
        return plan
    if type(source_report_v4) is not dict or type(high_volatility_validation) is not dict:
        _fail("composition requires both exact-dict prebuilt sources")

    verified = _verified_sources(source_report_v4, high_volatility_validation)
    bindings = {
        "source_report_v4_sha256": source_report_v4["report_sha256"],
        "source_report_v4_plan_sha256": source_report_v4["plan"]["plan_sha256"],
        "high_volatility_bundle_sha256": high_volatility_validation[
            "bundle_sha256"
        ],
        "high_volatility_plan_sha256": high_volatility_validation["plan"][
            "plan_sha256"
        ],
        "high_volatility_fixture_sha256": high_volatility_validation[
            "fixture_sha256"
        ],
        "high_volatility_dataset_sha256": high_volatility_validation["fixture"][
            "dataset_sha256"
        ],
    }
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "plan": plan,
        "source_report_v4": deepcopy(source_report_v4),
        "high_volatility_validation": deepcopy(high_volatility_validation),
        "bindings": bindings,
        "inherited_source_logical_run_count": source_report_v4[
            "source_logical_run_count"
        ],
        "high_volatility_source_run_count": high_volatility_validation[
            "executed_run_count"
        ],
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "inherited_market_analysis_count": source_report_v4[
            "market_analysis_count"
        ],
        "high_volatility_analysis_count": high_volatility_validation[
            "executed_analysis_count"
        ],
        "observed_high_volatility_slice_count": verified[
            "high_volatility_observed_count"
        ],
        "gap_high_volatility_slice_count": verified["high_volatility_gap_count"],
        "observed_deflated_sharpe_diagnostic_count": source_report_v4[
            "observed_deflated_sharpe_diagnostic_count"
        ],
        "observed_cscv_pbo_diagnostic_count": source_report_v4[
            "observed_cscv_pbo_diagnostic_count"
        ],
        "gap_cscv_pbo_diagnostic_count": source_report_v4[
            "gap_cscv_pbo_diagnostic_count"
        ],
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    report = {**payload, "report_sha256": _canonical_sha256(payload)}
    verify_synthetic_strategy_benchmark_report_v5(report)
    return report


def verify_synthetic_strategy_benchmark_report_v5(
    report: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(report, "report")
    required_keys = {
        "schema_version",
        "report_id",
        "data_source",
        "plan",
        "source_report_v4",
        "high_volatility_validation",
        "bindings",
        "inherited_source_logical_run_count",
        "high_volatility_source_run_count",
        "source_logical_run_count",
        "composition_executed_run_count",
        "additional_backtest_run_count",
        "inherited_market_analysis_count",
        "high_volatility_analysis_count",
        "observed_high_volatility_slice_count",
        "gap_high_volatility_slice_count",
        "observed_deflated_sharpe_diagnostic_count",
        "observed_cscv_pbo_diagnostic_count",
        "gap_cscv_pbo_diagnostic_count",
        "runtime_mutations",
        "evidence_state",
        "maturity",
        "status",
        "gaps",
        "authority",
        "report_sha256",
    }
    if set(report) != required_keys:
        _fail("benchmark report v5 fields do not match the contract")
    if (
        report["schema_version"] != REPORT_SCHEMA_VERSION
        or report["report_id"] != REPORT_ID
        or report["data_source"] != DATA_SOURCE
    ):
        _fail("benchmark report v5 identity mismatch")
    if (
        report["evidence_state"] != EVIDENCE_STATE
        or report["maturity"] != MATURITY
        or report["status"] != STATUS
    ):
        _fail("benchmark report v5 state must remain GAP/BLOCK")
    if report["gaps"] != _gaps() or report["authority"] != _authority():
        _fail("benchmark report v5 gaps or authority drifted")
    if report["runtime_mutations"] is not False:
        _fail("benchmark report v5 runtime_mutations must be exact false")
    verify_synthetic_strategy_benchmark_report_plan_v5(report["plan"])
    verified = _verified_sources(
        report["source_report_v4"], report["high_volatility_validation"]
    )

    source = report["source_report_v4"]
    high_volatility = report["high_volatility_validation"]
    expected_bindings = {
        "source_report_v4_sha256": source["report_sha256"],
        "source_report_v4_plan_sha256": source["plan"]["plan_sha256"],
        "high_volatility_bundle_sha256": high_volatility["bundle_sha256"],
        "high_volatility_plan_sha256": high_volatility["plan"]["plan_sha256"],
        "high_volatility_fixture_sha256": high_volatility["fixture_sha256"],
        "high_volatility_dataset_sha256": high_volatility["fixture"][
            "dataset_sha256"
        ],
    }
    if report["bindings"] != expected_bindings:
        _fail("benchmark report v5 source bindings mismatch")

    expected_counts = {
        "inherited_source_logical_run_count": 179,
        "high_volatility_source_run_count": 7,
        "source_logical_run_count": 186,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "inherited_market_analysis_count": source["market_analysis_count"],
        "high_volatility_analysis_count": high_volatility[
            "executed_analysis_count"
        ],
        "observed_high_volatility_slice_count": verified[
            "high_volatility_observed_count"
        ],
        "gap_high_volatility_slice_count": verified["high_volatility_gap_count"],
        "observed_deflated_sharpe_diagnostic_count": source[
            "observed_deflated_sharpe_diagnostic_count"
        ],
        "observed_cscv_pbo_diagnostic_count": source[
            "observed_cscv_pbo_diagnostic_count"
        ],
        "gap_cscv_pbo_diagnostic_count": source[
            "gap_cscv_pbo_diagnostic_count"
        ],
    }
    for key, expected in expected_counts.items():
        if report[key] != expected:
            _fail(f"benchmark report v5 {key} mismatch")
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    if report["report_sha256"] != _canonical_sha256(payload):
        _fail("benchmark report v5 report_sha256 mismatch")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "report_sha256": report["report_sha256"],
        "source_logical_run_count": report["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "observed_high_volatility_slice_count": report[
            "observed_high_volatility_slice_count"
        ],
        "gap_high_volatility_slice_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "permission": STATUS,
        "authority": _authority(),
    }


def render_synthetic_strategy_benchmark_report_plan_markdown_v5(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v5(plan)
    return "\n".join(
        (
            "# Synthetic Strategy Benchmark Report v5 Plan",
            "",
            "Non-current candidate. Prebuilt source composition only.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {DATA_SOURCE} |",
            f"| GAP | {', '.join(plan['gaps'])} |",
            f"| MATURITY | {MATURITY} |",
            f"| PERMISSION | {STATUS} |",
            "",
            f"- Logical source runs: {plan['source_logical_run_count']}",
            "- Composition planned backtest runs: 0",
            "- Runtime mutations: false",
            "- Paper/live/order entry: not authorized",
        )
    )


def render_synthetic_strategy_benchmark_report_markdown_v5(
    report: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_v5(report)
    return "\n".join(
        (
            "# Synthetic Strategy Benchmark Report v5",
            "",
            "Non-current candidate. No current pointer is changed by this artifact.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {DATA_SOURCE} |",
            f"| GAP | {', '.join(report['gaps'])} |",
            f"| MATURITY | {MATURITY} |",
            f"| PERMISSION | {STATUS} |",
            "",
            f"- Logical source runs: {receipt['source_logical_run_count']}",
            "- Composition added backtest runs: 0",
            (
                "- HIGH_VOLATILITY synthetic scenario coverage: "
                f"{receipt['observed_high_volatility_slice_count']}/6 observed"
            ),
            "- Coverage limitation: synthetic scenario only",
            "- Formal inference: not authorized",
            "- Paper/live/order entry: not authorized",
            f"- Report SHA-256: `{report['report_sha256']}`",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render the non-current v5 plan. Executed composition requires verified "
            "prebuilt v4 and high-volatility artifacts through the Python API."
        )
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    plan = plan_synthetic_strategy_benchmark_report_v5()
    text = (
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
        if args.format == "json"
        else render_synthetic_strategy_benchmark_report_plan_markdown_v5(plan)
    )
    if args.output is None:
        sys.stdout.write(text + "\n")
    else:
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
