from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from hakimi_research.deterministic_strategy_statistical_correction_benchmark_v2 import (
    LOCK_PATH,
    REPOSITORY_ROOT,
    SOURCE_RELATIVE_PATHS as V2_SOURCE_RELATIVE_PATHS,
    _context,
    _json_bytes,
    _require_receipt,
    _sha256_bytes,
)
from hakimi_research.synthetic_strategy_bootstrap_validation_v3 import (
    build_synthetic_strategy_bootstrap_validation_v3,
    replay_synthetic_strategy_bootstrap_validation_v3,
    verify_synthetic_strategy_bootstrap_validation_v3,
)
from hakimi_research.synthetic_strategy_cscv_pbo_tie_bounds import (
    build_synthetic_strategy_cscv_pbo_tie_bounds_v2,
    verify_synthetic_strategy_cscv_pbo_tie_bounds_v2,
)
from hakimi_research.synthetic_strategy_cscv_pbo_validation import (
    build_synthetic_strategy_cscv_pbo_validation_v2,
    verify_synthetic_strategy_cscv_pbo_validation_v2,
)
from hakimi_research.synthetic_strategy_deflated_sharpe_validation import (
    build_synthetic_strategy_deflated_sharpe_validation_v2,
    verify_synthetic_strategy_deflated_sharpe_validation_v2,
)
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    canonical_sha256,
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_robustness_evidence import (
    verify_synthetic_strategy_robustness_evidence_v2,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v2,
    verify_synthetic_strategy_trial_return_matrix_v2,
)


CONTRACT_VERSION = "deterministic-strategy-statistical-correction-benchmark-v3"
VERIFIER_VERSION = "deterministic-strategy-statistical-correction-benchmark-verifier-v3"
MATERIAL_VERIFIER_VERSION = (
    "deterministic-strategy-statistical-correction-material-verifier-v3"
)
RECEIPT_VERSION = "deterministic-strategy-statistical-correction-benchmark-receipt-v3"
MANIFEST_VERSION = "deterministic-strategy-statistical-correction-benchmark-manifest-v3"
MATURITY = "SYNTHETIC_STATISTICAL_REFERENCE_V3_CONSUMER_ONLY"
REFERENCE_FILE_NAMES = (
    "expected_receipt.json",
    "expected_receipt.md",
    "fixture_manifest.json",
)
REFERENCE_ROOT = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_statistical_correction_benchmark_v3"
)
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_strategy_statistical_correction_benchmark_v3.py",
    "src/hakimi_research/synthetic_strategy_bootstrap_validation_v3.py",
    "src/hakimi_research/bootstrap_confidence_evidence_v2.py",
    *V2_SOURCE_RELATIVE_PATHS,
)
PREDECESSOR_MANIFEST_SHA256 = (
    "b9733a75ebf19607a647d1f7bc3d33a8e91b8c828abb82b5daa8c43c370f9ab1"
)
PREDECESSOR_RECEIPT_SHA256 = (
    "9f072ee64a55af2b8fc624a9336794c370a702880783783f960edf6cc67c9509"
)
EXPECTED_RECEIPT_SHA256 = (
    "3e917119630fbd5f4335c8b8449ea55d80cc7a3a94194f77428dff24e18ab2a2"
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_CLAIMS = {
    "formal_blind_test": False,
    "formal_inference": False,
    "live": False,
    "order": False,
    "paper": False,
    "parameter_selection": False,
    "profitability": False,
    "ranking": False,
    "real_dataset": False,
}
_REPLACED_GAPS = {
    "BOOTSTRAP_CONFIDENCE_INTERVAL_NOT_ESTIMATED",
    "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED",
    "STATISTICAL_REFERENCE_V3_CONSUMER_NOT_ACTIVATED",
}


class DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(ValueError):
    pass


def _require_exact_json(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
                    f"{path}: dict keys must be exact strings"
                )
            _require_exact_json(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, f"{path}[{index}]")
        return
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float and math.isfinite(value):
        return
    raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
        f"{path}: must contain exact finite native JSON values"
    )


def _component_authority_locked(receipts: list[dict[str, Any]]) -> bool:
    return all(
        type(receipt.get("authority")) is dict
        and all(value is False for value in receipt["authority"].values())
        for receipt in receipts
    )


def _build_compact_receipt() -> dict[str, Any]:
    source_bundle = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_context(),
    )
    source_receipt = verify_synthetic_strategy_report_bundle_v2(source_bundle)
    _require_receipt(source_receipt, status="PASS", label="source_bundle")

    matrix_bundle = build_synthetic_strategy_trial_return_matrix_v2(
        source_bundle,
        execute=True,
    )
    matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v2(matrix_bundle)
    _require_receipt(matrix_receipt, status="BLOCK", label="matrix")
    if matrix_receipt.get("state") != "OBSERVED":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "matrix_observation_state_invalid"
        )

    robustness_bundle = matrix_bundle["source_robustness_bundle"]
    robustness_receipt = verify_synthetic_strategy_robustness_evidence_v2(
        robustness_bundle
    )
    _require_receipt(robustness_receipt, status="PASS", label="robustness")

    dsr_bundle = build_synthetic_strategy_deflated_sharpe_validation_v2(
        matrix_bundle,
        execute=True,
    )
    dsr_receipt = verify_synthetic_strategy_deflated_sharpe_validation_v2(
        dsr_bundle
    )
    _require_receipt(dsr_receipt, status="BLOCK", label="deflated_sharpe")
    if dsr_receipt.get("state") != "OBSERVED":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "deflated_sharpe_observation_state_invalid"
        )

    pbo_bundle = build_synthetic_strategy_cscv_pbo_validation_v2(
        matrix_bundle,
        execute=True,
    )
    pbo_receipt = verify_synthetic_strategy_cscv_pbo_validation_v2(pbo_bundle)
    _require_receipt(pbo_receipt, status="BLOCK", label="cscv_pbo")
    if pbo_receipt.get("state") != "GAP":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "cscv_pbo_state_invalid"
        )

    tie_bundle = build_synthetic_strategy_cscv_pbo_tie_bounds_v2(
        pbo_bundle,
        execute=True,
    )
    tie_receipt = verify_synthetic_strategy_cscv_pbo_tie_bounds_v2(tie_bundle)
    _require_receipt(tie_receipt, status="BLOCK", label="cscv_pbo_tie_bounds")
    if tie_receipt.get("state") != "OBSERVED_WITH_GAPS":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "cscv_pbo_tie_bounds_state_invalid"
        )

    bootstrap_bundle = build_synthetic_strategy_bootstrap_validation_v3(
        source_bundle,
        execute=True,
    )
    bootstrap_receipt = verify_synthetic_strategy_bootstrap_validation_v3(
        bootstrap_bundle,
        source_bundle,
    )
    _require_receipt(bootstrap_receipt, status="BLOCK", label="bootstrap_v3")
    if bootstrap_receipt.get("state") != "OBSERVED":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "bootstrap_v3_observation_state_invalid"
        )
    bootstrap_replay = replay_synthetic_strategy_bootstrap_validation_v3(
        bootstrap_bundle,
        source_bundle,
    )
    if bootstrap_replay.get("replay_status") != "EXACT_MATCH":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "bootstrap_v3_replay_failed"
        )

    component_receipts = [
        source_receipt,
        robustness_receipt,
        matrix_receipt,
        dsr_receipt,
        pbo_receipt,
        tie_receipt,
        bootstrap_receipt,
    ]
    if not _component_authority_locked(component_receipts):
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "component_authority_escalation"
        )

    stage_gaps = {
        "robustness_remaining": [
            gap
            for gap in robustness_bundle["gaps"]
            if gap not in _REPLACED_GAPS
        ],
        "deflated_sharpe": list(dsr_receipt["gaps"]),
        "cscv_pbo": list(pbo_receipt["gaps"]),
        "cscv_pbo_tie_bounds": list(tie_receipt["gaps"]),
        "bootstrap_v3": [
            gap
            for gap in bootstrap_receipt["gaps"]
            if gap not in _REPLACED_GAPS
        ],
    }
    remaining_gaps = sorted(
        {
            gap
            for gaps in stage_gaps.values()
            for gap in gaps
            if gap not in _REPLACED_GAPS
        }
        | {"FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN"}
    )
    source_count = source_bundle["executed_run_count"]
    robustness_count = robustness_bundle["executed_run_count"]
    total_count = source_count + robustness_count
    if (
        source_count != 32
        or robustness_count != 147
        or total_count != 179
        or matrix_bundle["source_dependency_bound_run_count"] != 179
        or matrix_bundle["source_git_bound_run_count"] != 0
    ):
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "canonical_source_run_accounting_drifted"
        )

    payload = {
        "schema_version": RECEIPT_VERSION,
        "maturity": MATURITY,
        "status": "BLOCK",
        "consumer_activation_mode": "OPT_IN_V3_ONLY",
        "source_bundle_sha256": source_bundle["bundle_sha256"],
        "robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "trial_matrix_bundle_sha256": matrix_bundle["bundle_sha256"],
        "deflated_sharpe_bundle_sha256": dsr_bundle["bundle_sha256"],
        "cscv_pbo_bundle_sha256": pbo_bundle["bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": tie_bundle["bundle_sha256"],
        "bootstrap_bundle_sha256": bootstrap_bundle["bundle_sha256"],
        "robustness_plan_sha256": robustness_bundle["plan"]["plan_sha256"],
        "trial_matrix_plan_sha256": matrix_bundle["plan"]["plan_sha256"],
        "deflated_sharpe_plan_sha256": dsr_bundle["plan"]["plan_sha256"],
        "cscv_pbo_plan_sha256": pbo_bundle["plan"]["plan_sha256"],
        "cscv_pbo_tie_bounds_plan_sha256": tie_bundle["plan"]["plan_sha256"],
        "bootstrap_plan_sha256": bootstrap_bundle["plan"]["plan_sha256"],
        "bootstrap_source_bundle_sha256": bootstrap_bundle[
            "source_provenance_binding"
        ]["source_bundle_sha256"],
        "run_reproducibility_ledger_sha256": matrix_bundle[
            "source_run_reproducibility_ledger_sha256"
        ],
        "source_executed_run_count": source_count,
        "robustness_executed_run_count": robustness_count,
        "total_executed_run_count": total_count,
        "total_dependency_bound_run_count": matrix_bundle[
            "source_dependency_bound_run_count"
        ],
        "git_bound_run_count": matrix_bundle["source_git_bound_run_count"],
        "matrix_candidate_count": matrix_receipt["trial_count"],
        "deflated_sharpe_diagnostic_count": dsr_receipt[
            "executed_analysis_count"
        ],
        "cscv_pbo_observed_evidence_count": pbo_receipt[
            "observed_evidence_count"
        ],
        "cscv_pbo_gap_evidence_count": pbo_receipt["gap_evidence_count"],
        "cscv_pbo_gap_strategy_ids": list(pbo_receipt["gap_strategy_ids"]),
        "tie_bounds_point_identified_strategy_ids": list(
            tie_receipt["point_identified_strategy_ids"]
        ),
        "tie_bounds_partial_interval_strategy_ids": list(
            tie_receipt["partial_interval_strategy_ids"]
        ),
        "tie_bounds_full_unit_interval_strategy_ids": list(
            tie_receipt["full_unit_interval_strategy_ids"]
        ),
        "tie_bounds_retained_split_count": tie_receipt[
            "retained_split_bound_count"
        ],
        "bootstrap_observed_evidence_count": bootstrap_receipt[
            "observed_evidence_count"
        ],
        "bootstrap_gap_evidence_count": bootstrap_receipt[
            "gap_evidence_count"
        ],
        "bootstrap_paired_observation_count_per_strategy": bootstrap_receipt[
            "paired_observation_count_per_strategy"
        ],
        "bootstrap_replicate_count": bootstrap_receipt["replicate_count"],
        "bootstrap_interval_count_per_strategy": bootstrap_receipt[
            "interval_count_per_strategy"
        ],
        "bootstrap_seed_identity_scope": bootstrap_receipt[
            "seed_identity_scope"
        ],
        "bootstrap_source_provenance_bound": bootstrap_receipt[
            "source_provenance_bound"
        ],
        "bootstrap_source_provenance_affects_seed": bootstrap_receipt[
            "source_provenance_affects_seed"
        ],
        "bootstrap_replay_status": bootstrap_replay["replay_status"],
        "statistical_analysis_run_count": 0,
        "additional_backtest_run_count": 0,
        "full_statistical_reference_applicability_proven": True,
        "statistical_ledger_alignment_proven": True,
        "full_report_alignment_proven": False,
        "run_accounting_additive": True,
        "reference_current_updated": False,
        "report_current_updated": False,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "stage_gaps": stage_gaps,
        "remaining_gaps": remaining_gaps,
        "predecessor_reference": {
            "manifest_sha256": PREDECESSOR_MANIFEST_SHA256,
            "receipt_sha256": PREDECESSOR_RECEIPT_SHA256,
            "modified": False,
        },
        "dependency_lock": {
            "name": LOCK_PATH.name,
            "sha256": _context()["dependency_lock_hash"],
            "fully_pinned": True,
        },
        "authority": dict(_AUTHORITY),
        "claims": dict(_CLAIMS),
        "component_authority_escalation": False,
    }
    receipt = dict(payload)
    receipt["receipt_sha256"] = canonical_sha256(payload)
    return receipt


def _render_receipt_markdown(receipt: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Deterministic Strategy Statistical Correction Reference v3",
            "",
            "## SOURCE",
            "- PURE_SYNTHETIC_IN_MEMORY",
            f"- Source runs: {receipt['total_executed_run_count']}",
            "- Statistical-stage backtest runs: 0",
            f"- Source ledger: `{receipt['run_reproducibility_ledger_sha256']}`",
            f"- Bootstrap v3: `{receipt['bootstrap_bundle_sha256']}`",
            "- Consumer activation: OPT_IN_V3_ONLY",
            "",
            "## GAP",
            *[f"- {gap}" for gap in receipt["remaining_gaps"]],
            "",
            "## MATURITY",
            f"- {receipt['maturity']}",
            "- Full statistical reference applicability proven: TRUE",
            "- Statistical ledger alignment proven: TRUE",
            "- Full report alignment proven: FALSE",
            "",
            "## PERMISSION",
            "- Status: BLOCK",
            "- Formal inference authority: FALSE",
            "- Profitability proven: FALSE",
            "- Paper authority: FALSE",
            "- Live authority: FALSE",
            "- Order-entry authority: FALSE",
            "",
            f"Receipt SHA-256: `{receipt['receipt_sha256']}`",
            "",
        ]
    )


def build_deterministic_strategy_statistical_correction_reference_material_v3() -> (
    dict[str, Any]
):
    receipt = _build_compact_receipt()
    receipt_bytes = _json_bytes(receipt)
    markdown_bytes = _render_receipt_markdown(receipt).encode("utf-8")
    source_files = {
        path: _sha256_bytes((REPOSITORY_ROOT / path).read_bytes())
        for path in SOURCE_RELATIVE_PATHS
    }
    manifest_core = {
        "contract_version": MANIFEST_VERSION,
        "maturity": MATURITY,
        "receipt_schema_version": receipt["schema_version"],
        "receipt_sha256": receipt["receipt_sha256"],
        "source_bundle_sha256": receipt["source_bundle_sha256"],
        "robustness_bundle_sha256": receipt["robustness_bundle_sha256"],
        "trial_matrix_bundle_sha256": receipt["trial_matrix_bundle_sha256"],
        "deflated_sharpe_bundle_sha256": receipt[
            "deflated_sharpe_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": receipt["cscv_pbo_bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": receipt[
            "cscv_pbo_tie_bounds_bundle_sha256"
        ],
        "bootstrap_bundle_sha256": receipt["bootstrap_bundle_sha256"],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "git_bound_run_count": receipt["git_bound_run_count"],
        "additional_backtest_run_count": 0,
        "full_statistical_reference_applicability_proven": True,
        "statistical_ledger_alignment_proven": True,
        "full_report_alignment_proven": False,
        "reference_current_updated": False,
        "report_current_updated": False,
        "predecessor_reference": dict(receipt["predecessor_reference"]),
        "dependency_lock": dict(receipt["dependency_lock"]),
        "source_files": source_files,
        "source_file_count": len(source_files),
        "expected_receipt_file_sha256": _sha256_bytes(receipt_bytes),
        "expected_markdown_file_sha256": _sha256_bytes(markdown_bytes),
        "remaining_gaps": list(receipt["remaining_gaps"]),
        "authority": dict(receipt["authority"]),
        "claims": dict(receipt["claims"]),
    }
    manifest = dict(manifest_core)
    manifest["manifest_sha256"] = canonical_sha256(manifest_core)
    return {
        "receipt": receipt,
        "manifest": manifest,
        "files": {
            "expected_receipt.json": receipt_bytes.decode("utf-8"),
            "expected_receipt.md": markdown_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(manifest).decode("utf-8"),
        },
    }


def verify_deterministic_strategy_statistical_correction_material_v3(
    material: dict[str, Any],
) -> dict[str, Any]:
    if type(material) is not dict:
        raise TypeError("material must be an exact native dict")
    _require_exact_json(material, "material")
    if set(material) != {"receipt", "manifest", "files"}:
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "material_shape_mismatch"
        )
    receipt = material["receipt"]
    manifest = material["manifest"]
    files = material["files"]
    if type(receipt) is not dict or type(manifest) is not dict or type(files) is not dict:
        raise TypeError("material sections must be exact native dicts")
    checks: dict[str, bool] = {}
    receipt_core = dict(receipt)
    receipt_sha256 = receipt_core.pop("receipt_sha256", None)
    checks["receipt_self_hash"] = (
        type(receipt_sha256) is str
        and receipt_sha256 == canonical_sha256(receipt_core)
    )
    checks["receipt_identity_locked"] = (
        receipt_sha256 == EXPECTED_RECEIPT_SHA256
    )
    manifest_core = dict(manifest)
    manifest_sha256 = manifest_core.pop("manifest_sha256", None)
    checks["manifest_self_hash"] = (
        type(manifest_sha256) is str
        and manifest_sha256 == canonical_sha256(manifest_core)
    )
    checks["reference_file_set"] = set(files) == set(REFERENCE_FILE_NAMES)
    checks["receipt_bytes_exact"] = files.get("expected_receipt.json") == (
        _json_bytes(receipt).decode("utf-8")
    )
    checks["markdown_exact"] = files.get("expected_receipt.md") == (
        _render_receipt_markdown(receipt)
    )
    checks["manifest_bytes_exact"] = files.get("fixture_manifest.json") == (
        _json_bytes(manifest).decode("utf-8")
    )
    checks["receipt_file_hash"] = manifest.get(
        "expected_receipt_file_sha256"
    ) == _sha256_bytes(files.get("expected_receipt.json", "").encode("utf-8"))
    checks["markdown_file_hash"] = manifest.get(
        "expected_markdown_file_sha256"
    ) == _sha256_bytes(files.get("expected_receipt.md", "").encode("utf-8"))
    checks["source_closure_bound"] = (
        manifest.get("source_file_count") == len(SOURCE_RELATIVE_PATHS)
        and manifest.get("source_files")
        == {
            path: _sha256_bytes((REPOSITORY_ROOT / path).read_bytes())
            for path in SOURCE_RELATIVE_PATHS
        }
    )
    checks["root_dependency_lock_bound"] = manifest.get("dependency_lock") == {
        "name": LOCK_PATH.name,
        "sha256": _context()["dependency_lock_hash"],
        "fully_pinned": True,
    }
    checks["predecessor_immutable"] = receipt.get("predecessor_reference") == {
        "manifest_sha256": PREDECESSOR_MANIFEST_SHA256,
        "receipt_sha256": PREDECESSOR_RECEIPT_SHA256,
        "modified": False,
    }
    checks["consumer_scope_bound"] = (
        receipt.get("consumer_activation_mode") == "OPT_IN_V3_ONLY"
        and receipt.get("full_statistical_reference_applicability_proven") is True
        and receipt.get("statistical_ledger_alignment_proven") is True
        and receipt.get("full_report_alignment_proven") is False
        and receipt.get("reference_current_updated") is False
        and receipt.get("report_current_updated") is False
    )
    checks["run_accounting_bound"] = (
        receipt.get("total_executed_run_count") == 179
        and receipt.get("total_dependency_bound_run_count") == 179
        and receipt.get("additional_backtest_run_count") == 0
        and receipt.get("run_accounting_additive") is True
    )
    checks["bootstrap_v3_bound"] = (
        receipt.get("bootstrap_seed_identity_scope")
        == "STATISTICAL_SAMPLE_ONLY"
        and receipt.get("bootstrap_source_provenance_bound") is True
        and receipt.get("bootstrap_source_provenance_affects_seed") is False
        and receipt.get("bootstrap_replay_status") == "EXACT_MATCH"
    )
    checks["authority_locked"] = receipt.get("authority") == _AUTHORITY
    checks["claims_locked"] = receipt.get("claims") == _CLAIMS
    checks["status_blocked"] = (
        receipt.get("status") == "BLOCK"
        and receipt.get("formal_inference_claimed") is False
        and receipt.get("decision_threshold") is None
    )
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            f"material_verification_failed:{failed}"
        )
    return {
        "status": "PASS",
        "contract_version": MATERIAL_VERIFIER_VERSION,
        "receipt_sha256": receipt_sha256,
        "manifest_sha256": manifest_sha256,
        "checks": checks,
    }


def _reference_root(value: str | None) -> Path:
    if value is None:
        return REFERENCE_ROOT
    if type(value) is not str or not value:
        raise TypeError("reference_root must be None or a non-empty exact str")
    return Path(value).resolve()


def verify_deterministic_strategy_statistical_correction_reference_v3(
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _reference_root(reference_root)
    expected = build_deterministic_strategy_statistical_correction_reference_material_v3()
    verify_deterministic_strategy_statistical_correction_material_v3(expected)
    if not root.is_dir():
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            "reference_root_missing"
        )
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    checks = {
        "reference_file_set": actual_names == set(REFERENCE_FILE_NAMES),
        "lf_only": all(
            b"\r" not in (root / name).read_bytes()
            for name in REFERENCE_FILE_NAMES
            if (root / name).is_file()
        ),
        "expected_bytes_exact": all(
            (root / name).is_file()
            and (root / name).read_bytes()
            == expected["files"][name].encode("utf-8")
            for name in REFERENCE_FILE_NAMES
        ),
    }
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        raise DeterministicStrategyStatisticalCorrectionBenchmarkV3Error(
            f"reference_verification_failed:{failed}"
        )
    receipt = expected["receipt"]
    manifest = expected["manifest"]
    return {
        "status": "PASS",
        "contract_version": VERIFIER_VERSION,
        "maturity": MATURITY,
        "receipt_sha256": receipt["receipt_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "source_bundle_sha256": receipt["source_bundle_sha256"],
        "robustness_bundle_sha256": receipt["robustness_bundle_sha256"],
        "trial_matrix_bundle_sha256": receipt["trial_matrix_bundle_sha256"],
        "deflated_sharpe_bundle_sha256": receipt[
            "deflated_sharpe_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": receipt["cscv_pbo_bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": receipt[
            "cscv_pbo_tie_bounds_bundle_sha256"
        ],
        "bootstrap_bundle_sha256": receipt["bootstrap_bundle_sha256"],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "additional_backtest_run_count": 0,
        "full_statistical_reference_applicability_proven": True,
        "statistical_ledger_alignment_proven": True,
        "full_report_alignment_proven": False,
        "reference_current_updated": False,
        "report_current_updated": False,
        "checks": checks,
        "authority": dict(_AUTHORITY),
        "claims": dict(_CLAIMS),
    }
