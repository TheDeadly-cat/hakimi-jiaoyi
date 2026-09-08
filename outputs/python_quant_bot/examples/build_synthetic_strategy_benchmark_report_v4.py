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


from examples.build_synthetic_strategy_benchmark_report_v3 import (  # noqa: E402
    plan_synthetic_strategy_benchmark_report_v3,
    verify_synthetic_strategy_benchmark_report_v3,
)
from exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1 import (  # noqa: E402
    plan_synthetic_strategy_cscv_pbo_validation_v1,
    verify_synthetic_strategy_cscv_pbo_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1 import (  # noqa: E402
    plan_synthetic_strategy_deflated_sharpe_validation_v1,
    verify_synthetic_strategy_deflated_sharpe_validation_v1,
)
from exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1 import (  # noqa: E402
    plan_synthetic_strategy_trial_return_matrix_v1,
    verify_synthetic_strategy_trial_return_matrix_v1,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v4"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v4"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v4"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v4"
DATA_SOURCE = "PURE_SYNTHETIC_IN_MEMORY"
EVIDENCE_STATE = "GAP"
MATURITY = (
    "SYNTHETIC_BENCHMARK_WITH_PARTIAL_REGIME_BOOTSTRAP_DSR_AND_PBO_DIAGNOSTICS"
)
STATUS = "BLOCK"

_GAPS = (
    "DEPENDENCY_LOCK_HASH_GAP",
    "ENSEMBLE_STRATEGY_GAP",
    "FORMAL_FROZEN_BLIND_TEST_GAP",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "HIGH_VOLATILITY_REGIME_COVERAGE_GAP",
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


class SyntheticStrategyBenchmarkReportV4Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise SyntheticStrategyBenchmarkReportV4Error(message)


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
        raise SyntheticStrategyBenchmarkReportV4Error(
            f"{label} failed verification: {type(exc).__name__}: {exc}"
        ) from exc
    if type(receipt) is not dict:
        _fail(f"{label} verifier did not return an exact dict receipt")


def _plan_payload_v4() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v3()
    matrix_plan = plan_synthetic_strategy_trial_return_matrix_v1()
    dsr_plan = plan_synthetic_strategy_deflated_sharpe_validation_v1()
    pbo_plan = plan_synthetic_strategy_cscv_pbo_validation_v1()
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "source_report_plan": source_plan,
        "trial_return_matrix_plan": matrix_plan,
        "deflated_sharpe_plan": dsr_plan,
        "cscv_pbo_plan": pbo_plan,
        "source_logical_run_count": source_plan["planned_run_count"],
        "source_reused_baseline_run_count": matrix_plan[
            "source_required_baseline_run_count"
        ],
        "source_reused_robustness_run_count": matrix_plan[
            "reused_robustness_run_count"
        ],
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "planned_market_analysis_count": source_plan[
            "planned_market_analysis_count"
        ],
        "planned_bootstrap_analysis_count": source_plan[
            "planned_bootstrap_analysis_count"
        ],
        "planned_deflated_sharpe_analysis_count": dsr_plan[
            "planned_analysis_count"
        ],
        "planned_cscv_pbo_analysis_count": pbo_plan["planned_analysis_count"],
        "requires_prebuilt_sources": True,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def plan_synthetic_strategy_benchmark_report_v4() -> dict[str, Any]:
    payload = _plan_payload_v4()
    return {**payload, "plan_sha256": _canonical_sha256(payload)}


def verify_synthetic_strategy_benchmark_report_plan_v4(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(plan, "plan")
    expected = plan_synthetic_strategy_benchmark_report_v4()
    if plan != expected:
        _fail("benchmark report v4 plan does not match deterministic preregistration")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "PASS",
        "plan_sha256": plan["plan_sha256"],
        "composition_planned_run_count": 0,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def _verified_sources(
    source_report_v3: dict[str, Any],
    trial_return_matrix: dict[str, Any],
    deflated_sharpe_validation: dict[str, Any],
    cscv_pbo_validation: dict[str, Any],
) -> dict[str, Any]:
    sources = (
        ("source_report_v3", verify_synthetic_strategy_benchmark_report_v3, source_report_v3),
        (
            "trial_return_matrix",
            verify_synthetic_strategy_trial_return_matrix_v1,
            trial_return_matrix,
        ),
        (
            "deflated_sharpe_validation",
            verify_synthetic_strategy_deflated_sharpe_validation_v1,
            deflated_sharpe_validation,
        ),
        (
            "cscv_pbo_validation",
            verify_synthetic_strategy_cscv_pbo_validation_v1,
            cscv_pbo_validation,
        ),
    )
    for label, verifier, artifact in sources:
        if type(artifact) is not dict:
            _fail(f"{label} must be an exact dict")
        _assert_exact_json(artifact, label)
        _call_verifier(label, verifier, artifact)

    try:
        baseline_bundle = source_report_v3["source_report_v2"]["source_report_v1"][
            "baseline_bundle"
        ]
        robustness_bundle = trial_return_matrix["source_robustness_bundle"]
        matrix_baseline_bundle = robustness_bundle["source_bundle"]
        dsr_source_matrix = deflated_sharpe_validation["source_matrix_bundle"]
        pbo_source_matrix = cscv_pbo_validation["source_matrix_bundle"]
    except (KeyError, TypeError) as exc:
        raise SyntheticStrategyBenchmarkReportV4Error(
            "prebuilt sources are missing a canonical source binding"
        ) from exc

    if _canonical_sha256(baseline_bundle) != _canonical_sha256(
        matrix_baseline_bundle
    ):
        _fail("v3 and trial return matrix do not share the exact baseline bundle")
    if baseline_bundle["bundle_sha256"] != robustness_bundle["source_bundle_sha256"]:
        _fail("v3 baseline digest does not match the robustness source digest")
    if (
        source_report_v3["bindings"]["source_baseline_bundle_sha256"]
        != baseline_bundle["bundle_sha256"]
    ):
        _fail("v3 baseline binding drifted")
    if (
        trial_return_matrix["source_robustness_bundle_sha256"]
        != robustness_bundle["bundle_sha256"]
    ):
        _fail("trial return matrix robustness binding drifted")

    matrix_sha256 = trial_return_matrix["bundle_sha256"]
    if deflated_sharpe_validation["source_matrix_bundle_sha256"] != matrix_sha256:
        _fail("deflated Sharpe validation does not bind the shared matrix")
    if cscv_pbo_validation["source_matrix_bundle_sha256"] != matrix_sha256:
        _fail("CSCV/PBO validation does not bind the shared matrix")
    if _canonical_sha256(dsr_source_matrix) != _canonical_sha256(
        trial_return_matrix
    ):
        _fail("deflated Sharpe validation embeds a different matrix")
    if _canonical_sha256(pbo_source_matrix) != _canonical_sha256(
        trial_return_matrix
    ):
        _fail("CSCV/PBO validation embeds a different matrix")

    strategy_ids = trial_return_matrix["plan"]["registered_strategy_ids"]
    if (
        deflated_sharpe_validation["plan"]["registered_strategy_ids"]
        != strategy_ids
        or cscv_pbo_validation["plan"]["registered_strategy_ids"]
        != strategy_ids
    ):
        _fail("diagnostic strategy order does not match the shared matrix")
    for label, artifact in (
        ("trial_return_matrix", trial_return_matrix),
        ("deflated_sharpe_validation", deflated_sharpe_validation),
        ("cscv_pbo_validation", cscv_pbo_validation),
    ):
        record_ids = [record["strategy_id"] for record in artifact["strategy_records"]]
        if record_ids != strategy_ids:
            _fail(f"{label} strategy record order drifted")

    expected_plan = plan_synthetic_strategy_benchmark_report_v4()
    if (
        source_report_v3["planned_run_count"]
        != expected_plan["source_logical_run_count"]
        or source_report_v3["executed_run_count"]
        != expected_plan["source_logical_run_count"]
    ):
        _fail("v3 logical source run count drifted")
    if (
        trial_return_matrix["planned_run_count"]
        != expected_plan["source_reused_robustness_run_count"]
        or trial_return_matrix["executed_run_count"]
        != expected_plan["source_reused_robustness_run_count"]
    ):
        _fail("trial return matrix reused run count drifted")
    for label, artifact in (
        ("source_report_v3", source_report_v3),
        ("trial_return_matrix", trial_return_matrix),
        ("deflated_sharpe_validation", deflated_sharpe_validation),
        ("cscv_pbo_validation", cscv_pbo_validation),
    ):
        if artifact["additional_backtest_run_count"] != 0:
            _fail(f"{label} unexpectedly added backtest runs")
        if artifact["runtime_mutations"] is not False:
            _fail(f"{label} reported runtime mutations")
    for label, artifact in (
        ("deflated_sharpe_validation", deflated_sharpe_validation),
        ("cscv_pbo_validation", cscv_pbo_validation),
    ):
        if artifact["planned_run_count"] != 0 or artifact["executed_run_count"] != 0:
            _fail(f"{label} must remain a zero-backtest analysis")

    dsr_count = deflated_sharpe_validation["executed_analysis_count"]
    pbo_count = cscv_pbo_validation["executed_analysis_count"]
    pbo_observed = cscv_pbo_validation["observed_evidence_count"]
    pbo_gap = cscv_pbo_validation["gap_evidence_count"]
    if dsr_count != len(strategy_ids):
        _fail("deflated Sharpe diagnostic coverage is incomplete")
    if pbo_count != len(strategy_ids) or pbo_observed + pbo_gap != pbo_count:
        _fail("CSCV/PBO diagnostic coverage accounting drifted")
    if pbo_observed != 4 or pbo_gap != 2:
        _fail("CSCV/PBO partial coverage must remain four observed and two GAP")

    return {
        "baseline_bundle": baseline_bundle,
        "robustness_bundle": robustness_bundle,
        "strategy_ids": strategy_ids,
        "dsr_count": dsr_count,
        "pbo_count": pbo_count,
        "pbo_observed": pbo_observed,
        "pbo_gap": pbo_gap,
    }


def build_synthetic_strategy_benchmark_report_v4(
    source_report_v3: dict[str, Any] | None = None,
    trial_return_matrix: dict[str, Any] | None = None,
    deflated_sharpe_validation: dict[str, Any] | None = None,
    cscv_pbo_validation: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        _fail("execute must be exact bool")
    plan = plan_synthetic_strategy_benchmark_report_v4()
    artifacts = (
        source_report_v3,
        trial_return_matrix,
        deflated_sharpe_validation,
        cscv_pbo_validation,
    )
    if not execute:
        if any(artifact is not None for artifact in artifacts):
            _fail("dry plan must not silently accept unverified source artifacts")
        return plan
    if any(type(artifact) is not dict for artifact in artifacts):
        _fail("composition requires all four exact-dict prebuilt sources")

    assert source_report_v3 is not None
    assert trial_return_matrix is not None
    assert deflated_sharpe_validation is not None
    assert cscv_pbo_validation is not None
    verified = _verified_sources(
        source_report_v3,
        trial_return_matrix,
        deflated_sharpe_validation,
        cscv_pbo_validation,
    )
    baseline_bundle = verified["baseline_bundle"]
    robustness_bundle = verified["robustness_bundle"]
    bindings = {
        "source_report_v3_sha256": source_report_v3["report_sha256"],
        "source_report_v3_plan_sha256": source_report_v3["plan"]["plan_sha256"],
        "shared_baseline_bundle_sha256": baseline_bundle["bundle_sha256"],
        "source_robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "trial_return_matrix_bundle_sha256": trial_return_matrix["bundle_sha256"],
        "trial_return_matrix_plan_sha256": trial_return_matrix["plan"][
            "plan_sha256"
        ],
        "deflated_sharpe_bundle_sha256": deflated_sharpe_validation[
            "bundle_sha256"
        ],
        "deflated_sharpe_plan_sha256": deflated_sharpe_validation["plan"][
            "plan_sha256"
        ],
        "deflated_sharpe_source_matrix_bundle_sha256": deflated_sharpe_validation[
            "source_matrix_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": cscv_pbo_validation["bundle_sha256"],
        "cscv_pbo_plan_sha256": cscv_pbo_validation["plan"]["plan_sha256"],
        "cscv_pbo_source_matrix_bundle_sha256": cscv_pbo_validation[
            "source_matrix_bundle_sha256"
        ],
    }
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "data_source": DATA_SOURCE,
        "plan": plan,
        "source_report_v3": deepcopy(source_report_v3),
        "trial_return_matrix": deepcopy(trial_return_matrix),
        "deflated_sharpe_validation": deepcopy(deflated_sharpe_validation),
        "cscv_pbo_validation": deepcopy(cscv_pbo_validation),
        "bindings": bindings,
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "market_analysis_count": source_report_v3["market_analysis_count"],
        "bootstrap_analysis_count": source_report_v3["bootstrap_analysis_count"],
        "deflated_sharpe_analysis_count": verified["dsr_count"],
        "cscv_pbo_analysis_count": verified["pbo_count"],
        "observed_deflated_sharpe_diagnostic_count": verified["dsr_count"],
        "gap_deflated_sharpe_diagnostic_count": 0,
        "observed_cscv_pbo_diagnostic_count": verified["pbo_observed"],
        "gap_cscv_pbo_diagnostic_count": verified["pbo_gap"],
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    report = {**payload, "report_sha256": _canonical_sha256(payload)}
    verify_synthetic_strategy_benchmark_report_v4(report)
    return report


def verify_synthetic_strategy_benchmark_report_v4(
    report: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(report, "report")
    required_keys = {
        "schema_version",
        "report_id",
        "data_source",
        "plan",
        "source_report_v3",
        "trial_return_matrix",
        "deflated_sharpe_validation",
        "cscv_pbo_validation",
        "bindings",
        "source_logical_run_count",
        "composition_executed_run_count",
        "additional_backtest_run_count",
        "market_analysis_count",
        "bootstrap_analysis_count",
        "deflated_sharpe_analysis_count",
        "cscv_pbo_analysis_count",
        "observed_deflated_sharpe_diagnostic_count",
        "gap_deflated_sharpe_diagnostic_count",
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
        _fail("benchmark report v4 fields do not match the contract")
    if report["schema_version"] != REPORT_SCHEMA_VERSION:
        _fail("benchmark report v4 schema_version mismatch")
    if report["report_id"] != REPORT_ID or report["data_source"] != DATA_SOURCE:
        _fail("benchmark report v4 identity mismatch")
    if (
        report["evidence_state"] != EVIDENCE_STATE
        or report["maturity"] != MATURITY
        or report["status"] != STATUS
    ):
        _fail("benchmark report v4 state must remain GAP/BLOCK")
    if report["gaps"] != _gaps() or report["authority"] != _authority():
        _fail("benchmark report v4 gaps or authority drifted")
    if report["runtime_mutations"] is not False:
        _fail("benchmark report v4 runtime_mutations must be exact false")
    verify_synthetic_strategy_benchmark_report_plan_v4(report["plan"])

    verified = _verified_sources(
        report["source_report_v3"],
        report["trial_return_matrix"],
        report["deflated_sharpe_validation"],
        report["cscv_pbo_validation"],
    )
    source_report_v3 = report["source_report_v3"]
    matrix = report["trial_return_matrix"]
    dsr = report["deflated_sharpe_validation"]
    pbo = report["cscv_pbo_validation"]
    expected_bindings = {
        "source_report_v3_sha256": source_report_v3["report_sha256"],
        "source_report_v3_plan_sha256": source_report_v3["plan"]["plan_sha256"],
        "shared_baseline_bundle_sha256": verified["baseline_bundle"][
            "bundle_sha256"
        ],
        "source_robustness_bundle_sha256": verified["robustness_bundle"][
            "bundle_sha256"
        ],
        "trial_return_matrix_bundle_sha256": matrix["bundle_sha256"],
        "trial_return_matrix_plan_sha256": matrix["plan"]["plan_sha256"],
        "deflated_sharpe_bundle_sha256": dsr["bundle_sha256"],
        "deflated_sharpe_plan_sha256": dsr["plan"]["plan_sha256"],
        "deflated_sharpe_source_matrix_bundle_sha256": dsr[
            "source_matrix_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": pbo["bundle_sha256"],
        "cscv_pbo_plan_sha256": pbo["plan"]["plan_sha256"],
        "cscv_pbo_source_matrix_bundle_sha256": pbo[
            "source_matrix_bundle_sha256"
        ],
    }
    if report["bindings"] != expected_bindings:
        _fail("benchmark report v4 source bindings mismatch")

    plan = report["plan"]
    expected_counts = {
        "source_logical_run_count": plan["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "market_analysis_count": source_report_v3["market_analysis_count"],
        "bootstrap_analysis_count": source_report_v3["bootstrap_analysis_count"],
        "deflated_sharpe_analysis_count": verified["dsr_count"],
        "cscv_pbo_analysis_count": verified["pbo_count"],
        "observed_deflated_sharpe_diagnostic_count": verified["dsr_count"],
        "gap_deflated_sharpe_diagnostic_count": 0,
        "observed_cscv_pbo_diagnostic_count": verified["pbo_observed"],
        "gap_cscv_pbo_diagnostic_count": verified["pbo_gap"],
    }
    for key, expected in expected_counts.items():
        if report[key] != expected:
            _fail(f"benchmark report v4 {key} mismatch")

    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    if report["report_sha256"] != _canonical_sha256(payload):
        _fail("benchmark report v4 report_sha256 mismatch")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "report_sha256": report["report_sha256"],
        "source_logical_run_count": report["source_logical_run_count"],
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "observed_deflated_sharpe_diagnostic_count": report[
            "observed_deflated_sharpe_diagnostic_count"
        ],
        "observed_cscv_pbo_diagnostic_count": report[
            "observed_cscv_pbo_diagnostic_count"
        ],
        "gap_cscv_pbo_diagnostic_count": report[
            "gap_cscv_pbo_diagnostic_count"
        ],
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "permission": STATUS,
        "authority": _authority(),
    }


def render_synthetic_strategy_benchmark_report_plan_markdown_v4(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v4(plan)
    gap_text = ", ".join(plan["gaps"])
    return "\n".join(
        (
            "# Synthetic Strategy Benchmark Report v4 Plan",
            "",
            "Non-current candidate. This plan composes prebuilt in-memory evidence only.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {plan['data_source']} |",
            f"| GAP | {gap_text} |",
            f"| MATURITY | {plan['maturity']} |",
            f"| PERMISSION | {plan['status']} |",
            "",
            f"- Logical source runs: {plan['source_logical_run_count']}",
            "- Composition planned backtest runs: 0",
            "- Runtime mutations: false",
            "- Formal inference: not authorized",
            "- Paper/live/order entry: not authorized",
        )
    )


def render_synthetic_strategy_benchmark_report_markdown_v4(
    report: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_v4(report)
    gap_text = ", ".join(report["gaps"])
    return "\n".join(
        (
            "# Synthetic Strategy Benchmark Report v4",
            "",
            "Non-current candidate. No current pointer is changed by this artifact.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {report['data_source']} |",
            f"| GAP | {gap_text} |",
            f"| MATURITY | {report['maturity']} |",
            f"| PERMISSION | {report['status']} |",
            "",
            f"- Logical source runs: {receipt['source_logical_run_count']}",
            "- Composition added backtest runs: 0",
            (
                "- Deflated Sharpe diagnostic coverage: "
                f"{receipt['observed_deflated_sharpe_diagnostic_count']}/6 observed"
            ),
            (
                "- CSCV/PBO diagnostic coverage: "
                f"{receipt['observed_cscv_pbo_diagnostic_count']}/6 observed, "
                f"{receipt['gap_cscv_pbo_diagnostic_count']}/6 GAP"
            ),
            "- Formal inference: not authorized",
            "- Paper/live/order entry: not authorized",
            f"- Report SHA-256: `{report['report_sha256']}`",
            (
                "- Shared matrix SHA-256: `"
                f"{report['bindings']['trial_return_matrix_bundle_sha256']}`"
            ),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render the non-current v4 composition plan. Executed composition requires "
            "four verified prebuilt in-memory artifacts through the Python API."
        )
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    plan = plan_synthetic_strategy_benchmark_report_v4()
    if args.format == "json":
        text = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        text = render_synthetic_strategy_benchmark_report_plan_markdown_v4(plan)
    if args.output is None:
        sys.stdout.write(text + "\n")
    else:
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
