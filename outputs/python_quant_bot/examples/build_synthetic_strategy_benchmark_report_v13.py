"""Bind report v12 and the v2 statistical reference behind an alignment gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from examples.build_synthetic_strategy_benchmark_report_v12 import (
    plan_synthetic_strategy_benchmark_report_v12,
    verify_synthetic_strategy_benchmark_report_v12,
)
from hakimi_research.deterministic_strategy_statistical_correction_benchmark_v2 import (
    REFERENCE_FILE_NAMES,
    REFERENCE_ROOT,
    _verify_reference_material,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-plan-v13"
REPORT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-v13"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-benchmark-report-receipt-v13"
REPORT_ID = "deterministic-synthetic-strategy-benchmark-v13"
DATA_SOURCE = "SYNTHETIC_PARALLEL_EVIDENCE_ALIGNMENT_GATE"
EVIDENCE_STATE = "GAP"
MATURITY = "SYNTHETIC_FULL_REPORT_WITH_UNALIGNED_STATISTICAL_REFERENCE"
STATUS = "BLOCK"
SOURCE_LOGICAL_RUN_COUNT = 222
STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT = 179
_LEGACY_BOOTSTRAP_PLAN_SCHEMA = (
    "synthetic-strategy-bootstrap-validation-plan-v1"
)
_ALIGNMENT_GAPS = (
    "FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN",
    "LEGACY_BOOTSTRAP_V1_TRANSITIVE_ONLY",
    "OVERLAPPING_RUN_ACCOUNTING_NOT_ADDITIVE",
    "STATISTICAL_REFERENCE_V2_PARALLEL_LINEAGE_ONLY",
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}


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


def _sha256_json(value: Any) -> str:
    _require_exact_json(value)
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = copy.deepcopy(unsigned)
    result[field] = _sha256_json(unsigned)
    return result


def load_statistical_reference_material_v2(
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
    _require_exact_json(material, path="$.statistical_reference_material_v2")
    verification = _verify_reference_material(reference_root, material)
    if verification.get("status") != "PASS":
        raise ValueError("statistical reference v2 verification failed")
    return material


def _bootstrap_plan_schemas(value: Any) -> list[str]:
    schemas: list[str] = []
    if type(value) is dict:
        for key, item in value.items():
            if key == "bootstrap_plan" and type(item) is dict:
                schema = item.get("schema_version")
                if type(schema) is not str:
                    raise TypeError("bootstrap plan schema must be an exact string")
                schemas.append(schema)
            schemas.extend(_bootstrap_plan_schemas(item))
    elif type(value) is list:
        for item in value:
            schemas.extend(_bootstrap_plan_schemas(item))
    return schemas


def _reference_binding(material: dict[str, Any]) -> dict[str, Any]:
    receipt = material["receipt"]
    manifest = material["manifest"]
    payload = {
        "receipt_schema_version": receipt["schema_version"],
        "receipt_sha256": receipt["receipt_sha256"],
        "manifest_contract_version": manifest["contract_version"],
        "manifest_sha256": manifest["manifest_sha256"],
        "source_bundle_sha256": receipt["source_bundle_sha256"],
        "robustness_bundle_sha256": receipt["robustness_bundle_sha256"],
        "trial_matrix_bundle_sha256": receipt[
            "trial_matrix_bundle_sha256"
        ],
        "bootstrap_bundle_sha256": receipt["bootstrap_bundle_sha256"],
        "run_reproducibility_ledger_sha256": receipt[
            "run_reproducibility_ledger_sha256"
        ],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "git_bound_run_count": receipt["git_bound_run_count"],
        "source_file_count": manifest["source_file_count"],
        "bootstrap_observed_evidence_count": receipt[
            "bootstrap_observed_evidence_count"
        ],
        "bootstrap_paired_observation_count_per_strategy": receipt[
            "bootstrap_paired_observation_count_per_strategy"
        ],
        "bootstrap_replicate_count": receipt["bootstrap_replicate_count"],
        "bootstrap_interval_count_per_strategy": receipt[
            "bootstrap_interval_count_per_strategy"
        ],
        "additional_backtest_run_count": receipt[
            "additional_backtest_run_count"
        ],
        "formal_inference_claimed": receipt["formal_inference_claimed"],
        "decision_threshold": receipt["decision_threshold"],
        "maturity": receipt["maturity"],
        "status": receipt["status"],
    }
    return _seal(payload, "binding_sha256")


def _combined_gaps(
    source_plan: dict[str, Any], material: dict[str, Any]
) -> list[str]:
    return sorted(
        set(source_plan["gaps"])
        .union(material["receipt"]["remaining_gaps"])
        .union(_ALIGNMENT_GAPS)
    )


def plan_synthetic_strategy_benchmark_report_v13() -> dict[str, Any]:
    source_plan = plan_synthetic_strategy_benchmark_report_v12()
    material = load_statistical_reference_material_v2()
    bootstrap_schemas = _bootstrap_plan_schemas(source_plan)
    if bootstrap_schemas != [_LEGACY_BOOTSTRAP_PLAN_SCHEMA]:
        raise ValueError("v13 source plan legacy Bootstrap boundary drifted")
    binding = _reference_binding(material)
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "requires_exact_execute_true": True,
        "requires_prebuilt_sources": True,
        "source_report_plan": copy.deepcopy(source_plan),
        "statistical_reference_binding_plan": copy.deepcopy(binding),
        "legacy_bootstrap_plan_schemas": list(bootstrap_schemas),
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "statistical_reference_executed_run_count": (
            STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        ),
        "combined_total_logical_run_count": None,
        "run_accounting_additive": False,
        "source_alignment_proven": False,
        "statistical_reference_applied_to_source_report": False,
        "bootstrap_v2_replaces_legacy_v1": False,
        "composition_planned_run_count": 0,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_report_module_file_count": source_plan[
            "source_module_file_count"
        ],
        "statistical_reference_source_file_count": binding[
            "source_file_count"
        ],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _combined_gaps(source_plan, material),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "plan_sha256")


def verify_synthetic_strategy_benchmark_report_plan_v13(
    plan: dict[str, Any],
) -> dict[str, Any]:
    if type(plan) is not dict:
        raise TypeError("plan must be an exact native dict")
    _require_exact_json(plan)
    expected = plan_synthetic_strategy_benchmark_report_v13()
    if plan != expected:
        raise ValueError("synthetic benchmark v13 plan verification failed")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_sha256": plan["plan_sha256"],
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "statistical_reference_executed_run_count": (
            STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        ),
        "source_alignment_proven": False,
        "composition_executed_run_count": 0,
        "runtime_mutations": False,
        "status": STATUS,
    }


def _verify_sources(
    source_report_v12: dict[str, Any],
    statistical_reference_material_v2: dict[str, Any],
) -> dict[str, Any]:
    if type(source_report_v12) is not dict:
        raise TypeError("source_report_v12 must be an exact native dict")
    if type(statistical_reference_material_v2) is not dict:
        raise TypeError(
            "statistical_reference_material_v2 must be an exact native dict"
        )
    _require_exact_json(source_report_v12, path="$.source_report_v12")
    _require_exact_json(
        statistical_reference_material_v2,
        path="$.statistical_reference_material_v2",
    )
    verify_synthetic_strategy_benchmark_report_v12(source_report_v12)
    reference_verification = _verify_reference_material(
        REFERENCE_ROOT,
        statistical_reference_material_v2,
    )
    if reference_verification.get("status") != "PASS":
        raise ValueError("statistical reference verification failed")
    if source_report_v12["total_logical_run_count"] != SOURCE_LOGICAL_RUN_COUNT:
        raise ValueError("v12 logical run count drifted")
    if source_report_v12["authority"] != _AUTHORITY:
        raise ValueError("v12 authority must remain denied")
    if source_report_v12["runtime_mutations"] is not False:
        raise ValueError("v12 runtime mutations must remain false")
    schemas = _bootstrap_plan_schemas(source_report_v12["plan"])
    if schemas != [_LEGACY_BOOTSTRAP_PLAN_SCHEMA]:
        raise ValueError("v12 legacy Bootstrap boundary drifted")
    receipt = statistical_reference_material_v2["receipt"]
    if (
        receipt["total_executed_run_count"]
        != STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        or receipt["additional_backtest_run_count"] != 0
        or receipt["formal_inference_claimed"] is not False
        or receipt["decision_threshold"] is not None
        or receipt["status"] != "BLOCK"
        or any(value is not False for value in receipt["authority"].values())
        or any(value is not False for value in receipt["claims"].values())
    ):
        raise ValueError("statistical reference boundary drifted")
    return reference_verification


def _compose_report(
    source_report_v12: dict[str, Any],
    statistical_reference_material_v2: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    receipt = statistical_reference_material_v2["receipt"]
    manifest = statistical_reference_material_v2["manifest"]
    binding = _reference_binding(statistical_reference_material_v2)
    payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "plan": copy.deepcopy(plan),
        "source_report_v12": copy.deepcopy(source_report_v12),
        "statistical_reference_v2": {
            "receipt": copy.deepcopy(receipt),
            "manifest": copy.deepcopy(manifest),
        },
        "bindings": {
            "source_report_v12_sha256": source_report_v12["report_sha256"],
            "source_report_v12_plan_sha256": source_report_v12["plan"][
                "plan_sha256"
            ],
            "statistical_reference_binding_sha256": binding[
                "binding_sha256"
            ],
            "statistical_reference_receipt_sha256": receipt[
                "receipt_sha256"
            ],
            "statistical_reference_manifest_sha256": manifest[
                "manifest_sha256"
            ],
            "statistical_reference_source_bundle_sha256": receipt[
                "source_bundle_sha256"
            ],
            "statistical_reference_bootstrap_bundle_sha256": receipt[
                "bootstrap_bundle_sha256"
            ],
            "statistical_reference_run_ledger_sha256": receipt[
                "run_reproducibility_ledger_sha256"
            ],
        },
        "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
        "statistical_reference_executed_run_count": (
            STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
        ),
        "combined_total_logical_run_count": None,
        "run_accounting_additive": False,
        "source_alignment_proven": False,
        "statistical_reference_applied_to_source_report": False,
        "bootstrap_v2_replaces_legacy_v1": False,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "source_report_module_file_count": plan[
            "source_report_module_file_count"
        ],
        "statistical_reference_source_file_count": plan[
            "statistical_reference_source_file_count"
        ],
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": copy.deepcopy(plan["gaps"]),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "report_sha256")


def build_synthetic_strategy_benchmark_report_v13(
    source_report_v12: dict[str, Any] | None = None,
    statistical_reference_material_v2: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        if (
            source_report_v12 is not None
            or statistical_reference_material_v2 is not None
        ):
            raise ValueError("plan-only mode does not accept prebuilt artifacts")
        return plan_synthetic_strategy_benchmark_report_v13()
    if source_report_v12 is None or statistical_reference_material_v2 is None:
        raise ValueError("execute=True requires both prebuilt v13 sources")
    _verify_sources(source_report_v12, statistical_reference_material_v2)
    return _compose_report(
        source_report_v12,
        statistical_reference_material_v2,
        plan_synthetic_strategy_benchmark_report_v13(),
    )


def verify_synthetic_strategy_benchmark_report_v13(
    report: dict[str, Any],
) -> dict[str, Any]:
    if type(report) is not dict:
        raise TypeError("report must be an exact native dict")
    _require_exact_json(report)
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unexpected synthetic benchmark v13 report schema")
    plan = report.get("plan")
    if type(plan) is not dict:
        raise TypeError("report plan must be an exact native dict")
    verify_synthetic_strategy_benchmark_report_plan_v13(plan)
    source = report.get("source_report_v12")
    embedded_reference = report.get("statistical_reference_v2")
    if type(source) is not dict or type(embedded_reference) is not dict:
        raise TypeError("report must embed both exact native v13 sources")
    expected_material = load_statistical_reference_material_v2()
    if embedded_reference != {
        "receipt": expected_material["receipt"],
        "manifest": expected_material["manifest"],
    }:
        raise ValueError("embedded statistical reference v2 drifted")
    _verify_sources(source, expected_material)
    expected = _compose_report(source, expected_material, plan)
    if report != expected:
        raise ValueError("synthetic benchmark v13 report verification failed")
    binding = expected["bindings"]
    return _seal(
        {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "report_id": REPORT_ID,
            "report_sha256": report["report_sha256"],
            "plan_sha256": plan["plan_sha256"],
            "source_report_v12_sha256": binding[
                "source_report_v12_sha256"
            ],
            "statistical_reference_receipt_sha256": binding[
                "statistical_reference_receipt_sha256"
            ],
            "statistical_reference_manifest_sha256": binding[
                "statistical_reference_manifest_sha256"
            ],
            "statistical_reference_bootstrap_bundle_sha256": binding[
                "statistical_reference_bootstrap_bundle_sha256"
            ],
            "source_logical_run_count": SOURCE_LOGICAL_RUN_COUNT,
            "statistical_reference_executed_run_count": (
                STATISTICAL_REFERENCE_EXECUTED_RUN_COUNT
            ),
            "combined_total_logical_run_count": None,
            "run_accounting_additive": False,
            "source_alignment_proven": False,
            "statistical_reference_applied_to_source_report": False,
            "bootstrap_v2_replaces_legacy_v1": False,
            "composition_executed_run_count": 0,
            "additional_backtest_run_count": 0,
            "evidence_state": EVIDENCE_STATE,
            "maturity": MATURITY,
            "status": STATUS,
            "authority": copy.deepcopy(_AUTHORITY),
            "runtime_mutations": False,
        },
        "receipt_sha256",
    )


def render_synthetic_strategy_benchmark_report_plan_markdown_v13(
    plan: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_plan_v13(plan)
    lines = [
        "# Synthetic Strategy Benchmark Plan v13",
        "",
        "NON-CURRENT RESEARCH-ONLY ALIGNMENT GATE",
        "",
        "## SOURCE",
        f"- Full report v12 logical runs: {plan['source_logical_run_count']}",
        (
            "- Statistical reference v2 executed runs: "
            f"{plan['statistical_reference_executed_run_count']}"
        ),
        "- The two run counts overlap and are not additive.",
        "- V13 composition executes no additional backtests.",
        "",
        "## GAP",
        *[f"- {gap}" for gap in plan["gaps"]],
        "",
        "## MATURITY",
        f"- {plan['maturity']}",
        "- Source alignment proven: FALSE",
        "- Statistical reference applied to v12: FALSE",
        "- Bootstrap-v2 replaces legacy Bootstrap-v1: FALSE",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    return "\n".join(lines) + "\n"


def render_synthetic_strategy_benchmark_report_markdown_v13(
    report: dict[str, Any],
) -> str:
    verify_synthetic_strategy_benchmark_report_v13(report)
    lines = [
        "# Synthetic Strategy Benchmark Report v13",
        "",
        "NON-CURRENT RESEARCH-ONLY ALIGNMENT GATE",
        "",
        "## SOURCE",
        f"- Bound full report v12: `{report['bindings']['source_report_v12_sha256']}`",
        (
            "- Bound statistical reference v2 receipt: `"
            f"{report['bindings']['statistical_reference_receipt_sha256']}`"
        ),
        (
            "- Bound Bootstrap-v2 bundle: `"
            f"{report['bindings']['statistical_reference_bootstrap_bundle_sha256']}`"
        ),
        "- New backtest runs: 0",
        "- Full-report and reference run counts are not summed.",
        "",
        "## GAP",
        *[f"- {gap}" for gap in report["gaps"]],
        "",
        "## MATURITY",
        f"- {report['maturity']}",
        "- Source alignment proven: FALSE",
        "- Statistical reference applied to v12: FALSE",
        "- Bootstrap-v2 replaces legacy Bootstrap-v1: FALSE",
        "",
        "## PERMISSION",
        "- Paper authority: FALSE",
        "- Live authority: FALSE",
        "- Order-entry authority: FALSE",
        "- Formal inference authority: FALSE",
        "- Profitability proven: FALSE",
    ]
    return "\n".join(lines) + "\n"


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the non-current synthetic benchmark v13 plan."
    )
    parser.parse_args()
    plan = build_synthetic_strategy_benchmark_report_v13(execute=False)
    print(render_synthetic_strategy_benchmark_report_plan_markdown_v13(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
