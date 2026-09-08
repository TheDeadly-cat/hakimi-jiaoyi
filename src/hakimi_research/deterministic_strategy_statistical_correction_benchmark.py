from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hakimi_research.source_layout import REPOSITORY_ROOT
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
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_robustness_evidence import (
    verify_synthetic_strategy_robustness_evidence_v2,
)
from hakimi_research.synthetic_strategy_trial_return_matrix import (
    build_synthetic_strategy_trial_return_matrix_v2,
    verify_synthetic_strategy_trial_return_matrix_v2,
)


CONTRACT_VERSION = "deterministic-strategy-statistical-correction-benchmark-v1"
VERIFIER_VERSION = (
    "deterministic-strategy-statistical-correction-benchmark-verifier-v1"
)
MANIFEST_VERSION = (
    "deterministic-strategy-statistical-correction-benchmark-manifest-v1"
)
RECEIPT_VERSION = (
    "deterministic-strategy-statistical-correction-benchmark-receipt-v1"
)
MATURITY = "SYNTHETIC_STATISTICAL_CORRECTION_ONLY"
REFERENCE_ROOT = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_statistical_correction_benchmark_v1"
)
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"
REFERENCE_FILE_NAMES = (
    "expected_receipt.json",
    "expected_receipt.md",
    "fixture_manifest.json",
)
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_strategy_statistical_correction_benchmark.py",
    "src/hakimi_research/synthetic_strategy_report_bundle.py",
    "src/hakimi_research/synthetic_strategy_robustness_evidence.py",
    "src/hakimi_research/synthetic_strategy_trial_return_matrix.py",
    "src/hakimi_research/synthetic_strategy_deflated_sharpe_validation.py",
    "src/hakimi_research/synthetic_strategy_cscv_pbo_validation.py",
    "src/hakimi_research/synthetic_strategy_cscv_pbo_tie_bounds.py",
    "src/hakimi_research/deflated_sharpe_diagnostic.py",
    "src/hakimi_research/cscv_pbo_diagnostic.py",
    "src/hakimi_research/cscv_pbo_tie_bounds.py",
    "src/hakimi_research/trial_return_matrix.py",
    "src/hakimi_research/strategy_family_inventory.py",
    "src/hakimi_research/backtest.py",
    "src/hakimi_research/config.py",
    "src/hakimi_research/distribution_evidence.py",
    "src/hakimi_research/execution.py",
    "src/hakimi_research/experiment_manifest.py",
    "src/hakimi_research/indicators.py",
    "src/hakimi_research/models.py",
    "src/hakimi_research/risk.py",
    "src/hakimi_research/source_layout.py",
    "src/hakimi_research/strategies/base.py",
    "src/hakimi_research/strategies/templates.py",
    "src/hakimi_research/validation_evidence.py",
)
_CLAIMS = {
    "real_dataset": False,
    "formal_blind_test": False,
    "formal_inference": False,
    "profitability": False,
    "ranking": False,
    "parameter_selection": False,
    "paper": False,
    "live": False,
    "order": False,
}
_FORBIDDEN_RECEIPT_TOKENS = (
    b"deflated_sharpe_probability",
    b"pbo_nonpositive_logit_rate",
    b"pbo_nonpositive_logit_lower_bound",
    b"pbo_nonpositive_logit_upper_bound",
    b"strategy_records",
    b"source_matrix_bundle",
    b"source_robustness_bundle",
)


class DeterministicStrategyStatisticalCorrectionBenchmarkError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _reference_root(value: str | None) -> Path:
    if value is None:
        return REFERENCE_ROOT
    if type(value) is not str or not value or value != value.strip():
        raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
            "reference_root_exact_str_required"
        )
    return Path(value).resolve()


def _context() -> dict[str, Any]:
    lock_bytes = LOCK_PATH.read_bytes()
    return {
        "schema_version": "synthetic-strategy-reference-context-v1",
        "git_commit_sha": "0" * 40,
        "git_worktree_clean": False,
        "dependency_lock_hash": _sha256_bytes(lock_bytes),
        "dependency_lock_fully_pinned": True,
        "dependency_lock_name": "requirements.research.lock",
        "runtime_version": "python-3.14",
    }


def _build_compact_receipt() -> dict[str, Any]:
    source_bundle = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_context(),
    )
    source_receipt = verify_synthetic_strategy_report_bundle_v2(source_bundle)
    if source_receipt.get("status") != "PASS":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
            "source_bundle_verification_failed"
        )
    matrix_bundle = build_synthetic_strategy_trial_return_matrix_v2(
        source_bundle,
        execute=True,
    )
    matrix_receipt = verify_synthetic_strategy_trial_return_matrix_v2(
        matrix_bundle
    )
    robustness_bundle = matrix_bundle["source_robustness_bundle"]
    robustness_receipt = verify_synthetic_strategy_robustness_evidence_v2(
        robustness_bundle
    )
    if robustness_receipt.get("status") != "PASS":
        raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
            "robustness_bundle_verification_failed"
        )
    dsr_bundle = build_synthetic_strategy_deflated_sharpe_validation_v2(
        matrix_bundle,
        execute=True,
    )
    dsr_receipt = verify_synthetic_strategy_deflated_sharpe_validation_v2(
        dsr_bundle
    )
    pbo_bundle = build_synthetic_strategy_cscv_pbo_validation_v2(
        matrix_bundle,
        execute=True,
    )
    pbo_receipt = verify_synthetic_strategy_cscv_pbo_validation_v2(
        pbo_bundle
    )
    tie_bounds_bundle = build_synthetic_strategy_cscv_pbo_tie_bounds_v2(
        pbo_bundle,
        execute=True,
    )
    tie_bounds_receipt = (
        verify_synthetic_strategy_cscv_pbo_tie_bounds_v2(
            tie_bounds_bundle
        )
    )
    replaced_robustness_gaps = {
        "DEFLATED_SHARPE_RATIO_NOT_ESTIMATED",
        "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_ESTIMATED",
    }
    stage_gaps = {
        "robustness_remaining": [
            gap
            for gap in robustness_bundle["gaps"]
            if gap not in replaced_robustness_gaps
        ],
        "deflated_sharpe": list(dsr_receipt["gaps"]),
        "cscv_pbo": list(pbo_receipt["gaps"]),
        "cscv_pbo_tie_bounds": list(tie_bounds_receipt["gaps"]),
    }
    receipt_core = {
        "schema_version": RECEIPT_VERSION,
        "maturity": MATURITY,
        "status": "BLOCK",
        "source_bundle_sha256": source_bundle["bundle_sha256"],
        "robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "trial_matrix_bundle_sha256": matrix_bundle["bundle_sha256"],
        "deflated_sharpe_bundle_sha256": dsr_bundle["bundle_sha256"],
        "cscv_pbo_bundle_sha256": pbo_bundle["bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": tie_bounds_bundle[
            "bundle_sha256"
        ],
        "robustness_plan_sha256": robustness_bundle["plan"]["plan_sha256"],
        "trial_matrix_plan_sha256": matrix_bundle["plan"]["plan_sha256"],
        "deflated_sharpe_plan_sha256": dsr_bundle["plan"]["plan_sha256"],
        "cscv_pbo_plan_sha256": pbo_bundle["plan"]["plan_sha256"],
        "cscv_pbo_tie_bounds_plan_sha256": tie_bounds_bundle["plan"][
            "plan_sha256"
        ],
        "run_reproducibility_ledger_sha256": matrix_bundle[
            "source_run_reproducibility_ledger_sha256"
        ],
        "source_executed_run_count": source_bundle["executed_run_count"],
        "robustness_executed_run_count": robustness_bundle[
            "executed_run_count"
        ],
        "total_executed_run_count": (
            source_bundle["executed_run_count"]
            + robustness_bundle["executed_run_count"]
        ),
        "total_dependency_bound_run_count": matrix_receipt[
            "source_dependency_bound_run_count"
        ],
        "git_bound_run_count": matrix_receipt[
            "source_git_bound_run_count"
        ],
        "matrix_dependency_bound_run_count": matrix_receipt[
            "matrix_dependency_bound_run_count"
        ],
        "deflated_sharpe_diagnostic_count": dsr_receipt[
            "executed_analysis_count"
        ],
        "cscv_pbo_observed_evidence_count": pbo_receipt[
            "observed_evidence_count"
        ],
        "cscv_pbo_gap_evidence_count": pbo_receipt[
            "gap_evidence_count"
        ],
        "cscv_pbo_gap_strategy_ids": list(
            pbo_receipt["gap_strategy_ids"]
        ),
        "tie_bounds_point_identified_strategy_ids": list(
            tie_bounds_receipt["point_identified_strategy_ids"]
        ),
        "tie_bounds_partial_interval_strategy_ids": list(
            tie_bounds_receipt["partial_interval_strategy_ids"]
        ),
        "tie_bounds_full_unit_interval_strategy_ids": list(
            tie_bounds_receipt["full_unit_interval_strategy_ids"]
        ),
        "tie_bounds_retained_split_count": tie_bounds_receipt[
            "retained_split_bound_count"
        ],
        "statistical_analysis_run_count": (
            dsr_receipt["executed_run_count"]
            + pbo_receipt["executed_run_count"]
            + tie_bounds_receipt["executed_run_count"]
        ),
        "additional_backtest_run_count": (
            dsr_receipt["additional_backtest_run_count"]
            + pbo_receipt["additional_backtest_run_count"]
            + tie_bounds_receipt["additional_backtest_run_count"]
        ),
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "runtime_mutations": False,
        "stage_gaps": stage_gaps,
        "remaining_gaps": sorted(
            {
                gap
                for gaps in stage_gaps.values()
                for gap in gaps
            }
        ),
        "authority": dict(tie_bounds_receipt["authority"]),
        "claims": dict(_CLAIMS),
    }
    receipt = dict(receipt_core)
    receipt["receipt_sha256"] = _sha256_bytes(
        _canonical_bytes(receipt_core)
    )
    return receipt


def _render_receipt_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Deterministic Synthetic Statistical Correction Benchmark",
        "",
        "## SOURCE",
        "",
        f"- Source bundle SHA-256: `{receipt['source_bundle_sha256']}`",
        (
            "- Robustness bundle SHA-256: "
            f"`{receipt['robustness_bundle_sha256']}`"
        ),
        (
            "- Trial matrix bundle SHA-256: "
            f"`{receipt['trial_matrix_bundle_sha256']}`"
        ),
        (
            "- Deflated Sharpe bundle SHA-256: "
            f"`{receipt['deflated_sharpe_bundle_sha256']}`"
        ),
        (
            "- CSCV-PBO bundle SHA-256: "
            f"`{receipt['cscv_pbo_bundle_sha256']}`"
        ),
        (
            "- Tie-bounds bundle SHA-256: "
            f"`{receipt['cscv_pbo_tie_bounds_bundle_sha256']}`"
        ),
        (
            "- Reconstructed runs: "
            f"{receipt['source_executed_run_count']} source + "
            f"{receipt['robustness_executed_run_count']} robustness = "
            f"{receipt['total_executed_run_count']}."
        ),
        (
            "- Dependency-bound runs: "
            f"{receipt['total_dependency_bound_run_count']}."
        ),
        "- Statistical correction backtest runs: 0",
        "",
        "## GAP",
        "",
        *[f"- `{gap}`" for gap in receipt["remaining_gaps"]],
        "",
        "## MATURITY",
        "",
        "- Status: `BLOCK`",
        "- Maturity: `SYNTHETIC_STATISTICAL_CORRECTION_ONLY`",
        (
            "- PBO coverage: "
            f"{receipt['cscv_pbo_observed_evidence_count']} observed, "
            f"{receipt['cscv_pbo_gap_evidence_count']} gap."
        ),
        (
            "- Tie bounds: "
            f"{len(receipt['tie_bounds_point_identified_strategy_ids'])} point, "
            f"{len(receipt['tie_bounds_partial_interval_strategy_ids'])} partial, "
            f"{len(receipt['tie_bounds_full_unit_interval_strategy_ids'])} full-unit."
        ),
        "- No DSR probability, PBO rate, or interval value is stored here.",
        "- No formal inference or decision threshold is defined.",
        "",
        "## PERMISSION",
        "",
        "- Profitability proven: `false`",
        "- Formal blind test complete: `false`",
        "- Formal inference authorized: `false`",
        "- Ranking authorized: `false`",
        "- Parameter selection authorized: `false`",
        "- Paper authorized: `false`",
        "- Live authorized: `false`",
        "- Order entry authorized: `false`",
        "",
        f"Receipt SHA-256: `{receipt['receipt_sha256']}`",
    ]
    markdown = "\n".join(lines) + "\n"
    for forbidden in ("READY", "SIGNIFICANT", "ACCEPT STRATEGY"):
        if forbidden in markdown:
            raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
                f"neutral_renderer_token_violation:{forbidden}"
            )
    return markdown


def build_deterministic_strategy_statistical_correction_reference_material() -> (
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
        "trial_matrix_bundle_sha256": receipt[
            "trial_matrix_bundle_sha256"
        ],
        "deflated_sharpe_bundle_sha256": receipt[
            "deflated_sharpe_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": receipt["cscv_pbo_bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": receipt[
            "cscv_pbo_tie_bounds_bundle_sha256"
        ],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "git_bound_run_count": receipt["git_bound_run_count"],
        "dependency_lock": {
            "name": LOCK_PATH.name,
            "sha256": _context()["dependency_lock_hash"],
            "fully_pinned": True,
        },
        "source_files": source_files,
        "expected_receipt_file_sha256": _sha256_bytes(receipt_bytes),
        "expected_markdown_file_sha256": _sha256_bytes(markdown_bytes),
        "remaining_gaps": list(receipt["remaining_gaps"]),
        "authority": dict(receipt["authority"]),
        "claims": dict(receipt["claims"]),
    }
    manifest = dict(manifest_core)
    manifest["manifest_sha256"] = _sha256_bytes(
        _canonical_bytes(manifest_core)
    )
    return {
        "receipt": receipt,
        "manifest": manifest,
        "files": {
            "expected_receipt.json": receipt_bytes.decode("utf-8"),
            "expected_receipt.md": markdown_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(manifest).decode("utf-8"),
        },
    }


def verify_deterministic_strategy_statistical_correction_reference(
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _reference_root(reference_root)
    if not root.is_dir():
        raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
            "reference_root_missing"
        )
    material = (
        build_deterministic_strategy_statistical_correction_reference_material()
    )
    file_names = sorted(
        path.name for path in root.iterdir() if path.is_file()
    )
    required_names = sorted(REFERENCE_FILE_NAMES)
    for name in REFERENCE_FILE_NAMES:
        if not (root / name).is_file():
            raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
                f"reference_file_missing:{name}"
            )
    expected_receipt_bytes = (root / "expected_receipt.json").read_bytes()
    expected_markdown_bytes = (root / "expected_receipt.md").read_bytes()
    expected_manifest_bytes = (root / "fixture_manifest.json").read_bytes()
    expected_receipt = json.loads(expected_receipt_bytes.decode("utf-8"))
    expected_manifest = json.loads(expected_manifest_bytes.decode("utf-8"))
    receipt_core = {
        key: value
        for key, value in expected_receipt.items()
        if key != "receipt_sha256"
    }
    manifest_core = {
        key: value
        for key, value in expected_manifest.items()
        if key != "manifest_sha256"
    }
    receipt = material["receipt"]
    manifest = material["manifest"]
    checks = {
        "reference_file_set": file_names == required_names,
        "lf_only": all(
            b"\r" not in (root / name).read_bytes()
            for name in REFERENCE_FILE_NAMES
        ),
        "receipt_exact": expected_receipt == receipt,
        "receipt_bytes_exact": expected_receipt_bytes
        == material["files"]["expected_receipt.json"].encode("utf-8"),
        "markdown_exact": expected_markdown_bytes
        == material["files"]["expected_receipt.md"].encode("utf-8"),
        "manifest_exact": expected_manifest == manifest,
        "manifest_bytes_exact": expected_manifest_bytes
        == material["files"]["fixture_manifest.json"].encode("utf-8"),
        "receipt_self_hash": expected_receipt.get("receipt_sha256")
        == _sha256_bytes(_canonical_bytes(receipt_core)),
        "manifest_self_hash": expected_manifest.get("manifest_sha256")
        == _sha256_bytes(_canonical_bytes(manifest_core)),
        "compact_receipt": len(expected_receipt_bytes) < 32768
        and all(
            token not in expected_receipt_bytes
            for token in _FORBIDDEN_RECEIPT_TOKENS
        ),
        "root_dependency_lock_bound": manifest["dependency_lock"]["sha256"]
        == _context()["dependency_lock_hash"],
        "source_closure_bound": set(manifest["source_files"])
        == set(SOURCE_RELATIVE_PATHS),
        "all_source_runs_dependency_bound": receipt[
            "total_dependency_bound_run_count"
        ]
        == 179,
        "git_gap_retained": receipt["git_bound_run_count"] == 0
        and "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE"
        in receipt["remaining_gaps"],
        "matrix_candidates_bound": receipt[
            "matrix_dependency_bound_run_count"
        ]
        == 18,
        "deflated_sharpe_scope_bound": receipt[
            "deflated_sharpe_diagnostic_count"
        ]
        == 6,
        "pbo_gap_coverage_bound": receipt[
            "cscv_pbo_observed_evidence_count"
        ]
        == 4
        and receipt["cscv_pbo_gap_evidence_count"] == 2
        and receipt["cscv_pbo_gap_strategy_ids"] == ["dual_ma", "grid"],
        "tie_identified_sets_bound": receipt[
            "tie_bounds_point_identified_strategy_ids"
        ]
        == ["bollinger", "macd", "momentum", "rsi"]
        and receipt["tie_bounds_partial_interval_strategy_ids"] == ["grid"]
        and receipt["tie_bounds_full_unit_interval_strategy_ids"]
        == ["dual_ma"]
        and receipt["tie_bounds_retained_split_count"] == 420,
        "zero_statistical_backtests": receipt[
            "statistical_analysis_run_count"
        ]
        == 0
        and receipt["additional_backtest_run_count"] == 0,
        "non_inferential": receipt["formal_inference_claimed"] is False
        and receipt["decision_threshold"] is None
        and receipt["status"] == "BLOCK"
        and receipt["maturity"] == MATURITY,
        "runtime_read_only": receipt["runtime_mutations"] is False,
        "authority_locked": all(
            value is False for value in receipt["authority"].values()
        ),
        "claims_locked": all(
            value is False for value in receipt["claims"].values()
        ),
    }
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        raise DeterministicStrategyStatisticalCorrectionBenchmarkError(
            f"reference_verification_failed:{failed}"
        )
    return {
        "status": "PASS",
        "contract_version": VERIFIER_VERSION,
        "maturity": MATURITY,
        "receipt_sha256": receipt["receipt_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "source_bundle_sha256": receipt["source_bundle_sha256"],
        "robustness_bundle_sha256": receipt["robustness_bundle_sha256"],
        "trial_matrix_bundle_sha256": receipt[
            "trial_matrix_bundle_sha256"
        ],
        "deflated_sharpe_bundle_sha256": receipt[
            "deflated_sharpe_bundle_sha256"
        ],
        "cscv_pbo_bundle_sha256": receipt["cscv_pbo_bundle_sha256"],
        "cscv_pbo_tie_bounds_bundle_sha256": receipt[
            "cscv_pbo_tie_bounds_bundle_sha256"
        ],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "git_bound_run_count": receipt["git_bound_run_count"],
        "matrix_dependency_bound_run_count": receipt[
            "matrix_dependency_bound_run_count"
        ],
        "deflated_sharpe_diagnostic_count": receipt[
            "deflated_sharpe_diagnostic_count"
        ],
        "cscv_pbo_observed_evidence_count": receipt[
            "cscv_pbo_observed_evidence_count"
        ],
        "cscv_pbo_gap_evidence_count": receipt[
            "cscv_pbo_gap_evidence_count"
        ],
        "tie_bounds_retained_split_count": receipt[
            "tie_bounds_retained_split_count"
        ],
        "checks": checks,
        "authority": dict(receipt["authority"]),
        "claims": dict(receipt["claims"]),
    }
