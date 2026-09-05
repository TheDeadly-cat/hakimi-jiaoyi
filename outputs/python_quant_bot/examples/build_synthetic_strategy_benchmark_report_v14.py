"""Align report v12 with the canonical statistical reference v3."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v12 import (
    REPORT_SCHEMA_VERSION as SOURCE_REPORT_SCHEMA_VERSION,
    plan_synthetic_strategy_benchmark_report_v12,
    verify_synthetic_strategy_benchmark_report_v12,
)
from hakimi_research.deterministic_strategy_statistical_correction_benchmark_v3 import (
    EXPECTED_RECEIPT_SHA256,
    REFERENCE_FILE_NAMES,
    REFERENCE_ROOT,
    verify_deterministic_strategy_statistical_correction_material_v3,
)
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256
from hakimi_research.synthetic_strategy_statistical_applicability_proof import (
    OUTCOME_BUNDLE_SCHEMA_VERSION,
    plan_synthetic_strategy_statistical_applicability_proof_v2,
    verify_synthetic_strategy_statistical_applicability_proof_v2,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v14"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v14"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v14"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v14"
DATA_SOURCE = "PURE_SYNTHETIC_PREBUILT_STATISTICAL_ALIGNMENT"
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
MATURITY = "SYNTHETIC_FULL_REPORT_STATISTICAL_SOURCE_ALIGNED_ONLY"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 222
STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT = 179
APPLICABILITY_SOURCE_EXECUTED_RUN_COUNT = 358

_RESOLVED_GAPS = {
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "STATISTICAL_LEDGER_ALIGNMENT_NOT_PROVEN",
    "STATISTICAL_REFERENCE_V3_CONSUMER_NOT_ACTIVATED",
}
_ALIGNMENT_GAPS = {
    "EXTERNAL_STATISTICAL_APPLICABILITY_PROOF_REQUIRED",
    "LEGACY_V12_STATISTICAL_EVIDENCE_SUPERSEDED_BY_V3",
    "SYNTHETIC_FULL_REPORT_ALIGNMENT_ONLY",
}
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


class SyntheticStrategyBenchmarkReportV14Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise SyntheticStrategyBenchmarkReportV14Error(message)


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must contain finite native floats")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    raise TypeError(f"{path} must use exact native JSON types")


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = copy.deepcopy(unsigned)
    result[field] = canonical_sha256(unsigned)
    return result


def load_statistical_reference_material_v3(
    reference_root: Path = REFERENCE_ROOT,
) -> dict[str, Any]:
    if type(reference_root) is not type(REFERENCE_ROOT):
        raise TypeError("reference_root must use the configured exact Path type")
    files = {
        name: (reference_root / name).read_text(encoding="utf-8")
        for name in REFERENCE_FILE_NAMES
    }
    material = {
        "receipt": json.loads(files["expected_receipt.json"]),
        "manifest": json.loads(files["fixture_manifest.json"]),
        "files": files,
    }
    verify_deterministic_strategy_statistical_correction_material_v3(material)
    return material


def _combined_plan_gaps(
    source_plan: dict[str, Any],
    applicability_plan: dict[str, Any],
    statistical_receipt: dict[str, Any],
) -> list[str]:
    return sorted(
        set(source_plan["gaps"])
        | set(applicability_plan["gaps"])
        | set(statistical_receipt["remaining_gaps"])
    )


def _aligned_report_gaps(plan: dict[str, Any]) -> list[str]:
    gaps = set(plan["gaps"])
    if not _RESOLVED_GAPS.issubset(gaps):
        _fail("v14 resolved-gap prerequisites drifted")
    return sorted((gaps - _RESOLVED_GAPS) | _ALIGNMENT_GAPS)


def plan_synthetic_strategy_benchmark_report_v14() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v12()
    applicability_plan = (
        plan_synthetic_strategy_statistical_applicability_proof_v2()
    )
    material = load_statistical_reference_material_v3()
    receipt = material["receipt"]
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "requires_external_applicability_proof_for_verification": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "statistical_applicability_plan": copy.deepcopy(applicability_plan),
        "statistical_reference_v3": {
            "receipt_sha256": receipt["receipt_sha256"],
            "manifest_sha256": material["manifest"]["manifest_sha256"],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "statistical_reference_executed_run_count": (
            STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        ),
        "applicability_source_executed_run_count": (
            APPLICABILITY_SOURCE_EXECUTED_RUN_COUNT
        ),
        "combined_total_logical_run_count": None,
        "run_accounting_additive": False,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "legacy_v12_statistical_evidence_superseded": False,
        "statistical_reference_v3_applied": False,
        "bootstrap_v3_replaces_legacy_v1": False,
        "full_report_alignment_proven": False,
        "data_source": DATA_SOURCE,
        "evidence_state": "PLANNED",
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_plan_gaps(source_plan, applicability_plan, receipt),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v14(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json(plan)
    if plan != plan_synthetic_strategy_benchmark_report_v14():
        _fail("synthetic benchmark v14 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "full_report_alignment_proven": False,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _v12_legacy_trial_matrix(report: dict[str, Any]) -> dict[str, Any]:
    current = report
    for version in range(11, 3, -1):
        key = f"source_report_v{version}"
        current = current.get(key)
        if type(current) is not dict:
            _fail(f"v12 legacy report chain missing {key}")
    matrix = current.get("trial_return_matrix")
    if type(matrix) is not dict:
        _fail("v12 legacy trial-return matrix missing")
    return matrix


def _require_denied_authority(value: Any, *, label: str) -> None:
    if value != _AUTHORITY:
        _fail(f"{label} authority must remain denied")


def _verify_alignment_sources(
    source_report_v12: dict[str, Any],
    statistical_applicability_proof_v2: dict[str, Any],
    statistical_reference_material_v3: dict[str, Any],
) -> dict[str, Any]:
    for label, value in (
        ("source_report_v12", source_report_v12),
        ("statistical_applicability_proof_v2", statistical_applicability_proof_v2),
        ("statistical_reference_material_v3", statistical_reference_material_v3),
    ):
        if type(value) is not dict:
            raise TypeError(f"{label} must be an exact native dict")
        _require_exact_json(value, path=f"$.{label}")

    source_receipt = verify_synthetic_strategy_benchmark_report_v12(
        source_report_v12
    )
    applicability_receipt = (
        verify_synthetic_strategy_statistical_applicability_proof_v2(
            statistical_applicability_proof_v2
        )
    )
    material_receipt = (
        verify_deterministic_strategy_statistical_correction_material_v3(
            statistical_reference_material_v3
        )
    )
    if source_report_v12.get("schema_version") != SOURCE_REPORT_SCHEMA_VERSION:
        _fail("unexpected v12 source report schema")
    if source_report_v12.get("total_logical_run_count") != SOURCE_LOGICAL_RUN_COUNT:
        _fail("v12 source logical-run count drifted")
    if source_report_v12.get("status") != STATUS:
        _fail("v12 source status drifted")
    if source_report_v12.get("runtime_mutations") is not False:
        _fail("v12 source runtime mutations must remain false")
    _require_denied_authority(
        source_report_v12.get("authority"), label="v12 source"
    )

    proof = statistical_applicability_proof_v2
    if proof.get("schema_version") != OUTCOME_BUNDLE_SCHEMA_VERSION:
        _fail("unexpected statistical applicability proof schema")
    if proof.get("status") != STATUS or proof.get("runtime_mutations") is not False:
        _fail("statistical applicability proof boundary drifted")
    _require_denied_authority(proof.get("authority"), label="applicability proof")
    expected_true = (
        "matrix_outcome_applicability_proven",
        "dsr_numerical_applicability_proven",
        "pbo_numerical_applicability_proven",
        "tie_bounds_numerical_applicability_proven",
        "bootstrap_numerical_applicability_proven",
        "full_statistical_numerical_applicability_proven",
        "bootstrap_seed_identity_policy_proven",
        "bootstrap_source_provenance_binding_preserved",
        "canonical_reproducibility_ledger_verified",
    )
    if any(proof.get(field) is not True for field in expected_true):
        _fail("statistical applicability prerequisites are incomplete")
    for field in (
        "full_statistical_reference_applicability_proven",
        "statistical_ledger_alignment_proven",
        "full_report_alignment_proven",
        "run_accounting_additive",
        "formal_inference_claimed",
    ):
        if proof.get(field) is not False:
            _fail(f"upstream applicability field must remain false:{field}")

    legacy_matrix = _v12_legacy_trial_matrix(source_report_v12)
    if legacy_matrix != proof.get("legacy_matrix_bundle"):
        _fail("v12 legacy trial matrix does not match applicability proof")
    legacy_robustness = legacy_matrix.get("source_robustness_bundle")
    if type(legacy_robustness) is not dict:
        _fail("legacy robustness source missing from v12 matrix")
    legacy_baseline = legacy_robustness.get("source_bundle")
    if type(legacy_baseline) is not dict:
        _fail("legacy baseline source missing from v12 matrix")
    if source_report_v12["bindings"].get(
        "source_baseline_bundle_sha256"
    ) != legacy_baseline.get("bundle_sha256"):
        _fail("v12 baseline binding does not match legacy matrix lineage")

    canonical_matrix = proof.get("canonical_matrix_bundle")
    if type(canonical_matrix) is not dict:
        _fail("canonical applicability matrix missing")
    canonical_robustness = canonical_matrix.get("source_robustness_bundle")
    if type(canonical_robustness) is not dict:
        _fail("canonical robustness source missing")
    canonical_baseline = canonical_robustness.get("source_bundle")
    if type(canonical_baseline) is not dict:
        _fail("canonical baseline source missing")

    receipt = statistical_reference_material_v3["receipt"]
    manifest = statistical_reference_material_v3["manifest"]
    _require_denied_authority(receipt.get("authority"), label="v3 reference")
    if any(value is not False for value in receipt.get("claims", {}).values()):
        _fail("v3 statistical claims must remain denied")
    if (
        receipt.get("receipt_sha256") != EXPECTED_RECEIPT_SHA256
        or receipt.get("status") != STATUS
        or receipt.get("full_statistical_reference_applicability_proven") is not True
        or receipt.get("statistical_ledger_alignment_proven") is not True
        or receipt.get("full_report_alignment_proven") is not False
    ):
        _fail("v3 statistical reference boundary drifted")

    stages = proof.get("bindings", {}).get("stages")
    bootstrap = proof.get("bindings", {}).get("bootstrap")
    if type(stages) is not dict or type(bootstrap) is not dict:
        _fail("applicability stage bindings missing")
    expected_digests = {
        "source_bundle_sha256": canonical_baseline.get("bundle_sha256"),
        "robustness_bundle_sha256": canonical_robustness.get("bundle_sha256"),
        "trial_matrix_bundle_sha256": stages.get("matrix", {}).get(
            "canonical_bundle_sha256"
        ),
        "deflated_sharpe_bundle_sha256": stages.get("dsr", {}).get(
            "canonical_bundle_sha256"
        ),
        "cscv_pbo_bundle_sha256": stages.get("pbo", {}).get(
            "canonical_bundle_sha256"
        ),
        "cscv_pbo_tie_bounds_bundle_sha256": stages.get("tie", {}).get(
            "canonical_bundle_sha256"
        ),
        "bootstrap_bundle_sha256": bootstrap.get("canonical_bundle_sha256"),
        "run_reproducibility_ledger_sha256": proof.get("bindings", {}).get(
            "canonical_run_reproducibility_ledger_sha256"
        ),
    }
    for field, expected in expected_digests.items():
        if type(expected) is not str or receipt.get(field) != expected:
            _fail(f"v3 statistical digest does not align:{field}")
    if canonical_matrix.get(
        "source_run_reproducibility_ledger_sha256"
    ) != expected_digests["run_reproducibility_ledger_sha256"]:
        _fail("canonical matrix run-ledger binding drifted")

    binding = {
        "source_report_v12_sha256": source_report_v12["report_sha256"],
        "source_report_v12_plan_sha256": source_report_v12["plan"][
            "plan_sha256"
        ],
        "legacy_baseline_bundle_sha256": legacy_baseline["bundle_sha256"],
        "legacy_robustness_bundle_sha256": legacy_robustness["bundle_sha256"],
        "legacy_trial_matrix_bundle_sha256": legacy_matrix["bundle_sha256"],
        "statistical_applicability_proof_bundle_sha256": proof["bundle_sha256"],
        "statistical_applicability_proof_plan_sha256": proof["plan"][
            "plan_sha256"
        ],
        "statistical_reference_v3_receipt_sha256": receipt["receipt_sha256"],
        "statistical_reference_v3_manifest_sha256": manifest["manifest_sha256"],
        **expected_digests,
        "v12_source_receipt_sha256": source_receipt["receipt_sha256"],
        "applicability_receipt_bundle_sha256": applicability_receipt[
            "bundle_sha256"
        ],
        "material_verification_receipt_sha256": material_receipt[
            "receipt_sha256"
        ],
    }
    return _seal(binding, "alignment_binding_sha256")


def _compose_report(
    source_report_v12: dict[str, Any],
    statistical_reference_material_v3: dict[str, Any],
    alignment_binding: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v12": copy.deepcopy(source_report_v12),
        "statistical_reference_v3": {
            "receipt": copy.deepcopy(statistical_reference_material_v3["receipt"]),
            "manifest": copy.deepcopy(statistical_reference_material_v3["manifest"]),
        },
        "alignment_binding": copy.deepcopy(alignment_binding),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "statistical_reference_executed_run_count": (
            STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        ),
        "applicability_source_executed_run_count": (
            APPLICABILITY_SOURCE_EXECUTED_RUN_COUNT
        ),
        "combined_total_logical_run_count": None,
        "run_accounting_additive": False,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "legacy_v12_statistical_evidence_superseded": True,
        "statistical_reference_v3_applied": True,
        "bootstrap_v3_replaces_legacy_v1": True,
        "full_report_alignment_proven": True,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _aligned_report_gaps(plan),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "report_sha256")


def build_synthetic_strategy_benchmark_report_v14(
    source_report_v12: dict[str, Any] | None = None,
    statistical_applicability_proof_v2: dict[str, Any] | None = None,
    statistical_reference_material_v3: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    sources = (
        source_report_v12,
        statistical_applicability_proof_v2,
        statistical_reference_material_v3,
    )
    if execute is False:
        if any(source is not None for source in sources):
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v14()
    if any(source is None for source in sources):
        raise ValueError("execute=True requires all three prebuilt v14 sources")
    alignment = _verify_alignment_sources(
        source_report_v12,  # type: ignore[arg-type]
        statistical_applicability_proof_v2,  # type: ignore[arg-type]
        statistical_reference_material_v3,  # type: ignore[arg-type]
    )
    return _compose_report(
        source_report_v12,  # type: ignore[arg-type]
        statistical_reference_material_v3,  # type: ignore[arg-type]
        alignment,
        plan_synthetic_strategy_benchmark_report_v14(),
    )


def verify_synthetic_strategy_benchmark_report_v14(
    report: dict[str, Any],
    statistical_applicability_proof_v2: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    if type(statistical_applicability_proof_v2) is not dict:
        raise TypeError("external applicability proof must be an exact native dict")
    _require_exact_json(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        _fail("unexpected synthetic benchmark v14 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v14(plan)
    source = report.get("source_report_v12")
    embedded_reference = report.get("statistical_reference_v3")
    if type(source) is not dict or type(embedded_reference) is not dict:
        raise TypeError("v14 report must embed exact source and reference dicts")
    material = load_statistical_reference_material_v3()
    if embedded_reference != {
        "receipt": material["receipt"],
        "manifest": material["manifest"],
    }:
        _fail("embedded statistical reference v3 drifted")
    alignment = _verify_alignment_sources(
        source, statistical_applicability_proof_v2, material
    )
    if report.get("alignment_binding") != alignment:
        _fail("external applicability proof does not match report binding")
    expected = _compose_report(source, material, alignment, plan)
    if report != expected:
        _fail("synthetic benchmark v14 report verification failed")
    return _seal(
        {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "report_id": REPORT_ID,
            "report_sha256": report["report_sha256"],
            "plan_sha256": plan["plan_sha256"],
            "alignment_binding_sha256": alignment["alignment_binding_sha256"],
            "source_report_v12_sha256": alignment["source_report_v12_sha256"],
            "statistical_applicability_proof_bundle_sha256": alignment[
                "statistical_applicability_proof_bundle_sha256"
            ],
            "statistical_reference_v3_receipt_sha256": alignment[
                "statistical_reference_v3_receipt_sha256"
            ],
            "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
            "statistical_reference_executed_run_count": (
                STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
            ),
            "combined_total_logical_run_count": None,
            "run_accounting_additive": False,
            "composition_executed_run_count": 0,
            "additional_backtest_run_count": 0,
            "legacy_v12_statistical_evidence_superseded": True,
            "statistical_reference_v3_applied": True,
            "bootstrap_v3_replaces_legacy_v1": True,
            "full_report_alignment_proven": True,
            "formal_inference_claimed": False,
            "decision_threshold": None,
            "evidence_state": EVIDENCE_STATE,
            "maturity": MATURITY,
            "status": STATUS,
            "authority": copy.deepcopy(_AUTHORITY),
            "runtime_mutations": False,
        },
        "receipt_sha256",
    )


def render_synthetic_strategy_benchmark_report_plan_markdown_v14(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v14(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v14",
        "",
        "NON-CURRENT RESEARCH-ONLY FULL-REPORT ALIGNMENT",
        "",
        "## SOURCE",
        f"- Full report v12 logical runs: {plan['source_logical_run_count']}",
        (
            "- Statistical reference v3 executed runs: "
            f"{plan['statistical_reference_executed_run_count']}"
        ),
        "- Composition backtest runs: 0",
        "- Source counts overlap and are not additive.",
        "",
        "## GAP",
        *[f"- {gap}" for gap in plan["gaps"]],
        "",
        "## MATURITY",
        f"- {plan['maturity']}",
        "- Full report alignment proven: FALSE (plan only)",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    return "\n".join(lines) + "\n"


def render_synthetic_strategy_benchmark_report_markdown_v14(
    report: dict[str, Any],
    statistical_applicability_proof_v2: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_benchmark_report_v14(
        report, statistical_applicability_proof_v2
    )
    lines = [
        "# Synthetic Strategy Benchmark Report v14",
        "",
        "NON-CURRENT RESEARCH-ONLY FULL-REPORT ALIGNMENT",
        "",
        "## SOURCE",
        f"- Bound full report v12: `{receipt['source_report_v12_sha256']}`",
        (
            "- Bound statistical reference v3: `"
            f"{receipt['statistical_reference_v3_receipt_sha256']}`"
        ),
        "- New backtest runs: 0",
        "- Legacy v12 statistical evidence is superseded, not equated.",
        "",
        "## GAP",
        *[f"- {gap}" for gap in report["gaps"]],
        "",
        "## MATURITY",
        f"- {receipt['maturity']}",
        "- Statistical reference v3 applied: TRUE",
        "- Bootstrap-v3 replaces legacy Bootstrap-v1: TRUE",
        "- Full report alignment proven: TRUE (synthetic source lineage only)",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    markdown = "\n".join(lines) + "\n"
    if "READY" in markdown or "Profitability proven: TRUE" in markdown:
        _fail("neutral renderer token violation")
    return markdown


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the non-current synthetic benchmark v14 plan."
    )
    parser.parse_args()
    plan = plan_synthetic_strategy_benchmark_report_v14()
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v14(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
