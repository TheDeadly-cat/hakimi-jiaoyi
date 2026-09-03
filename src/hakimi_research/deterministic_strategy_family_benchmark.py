from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    render_synthetic_strategy_report_bundle_markdown_v2,
    verify_synthetic_strategy_report_bundle_v2,
)


CONTRACT_VERSION = "deterministic-strategy-family-benchmark-v1"
VERIFIER_VERSION = "deterministic-strategy-family-benchmark-verifier-v1"
MANIFEST_VERSION = "deterministic-strategy-family-benchmark-manifest-v1"
MATURITY = "SYNTHETIC_BASELINE_ONLY"
REFERENCE_ROOT = REPOSITORY_ROOT / "examples" / "deterministic_strategy_family_benchmark_v1"
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"
REFERENCE_FILE_NAMES = (
    "expected_bundle.json",
    "expected_bundle.md",
    "fixture_manifest.json",
)
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_strategy_family_benchmark.py",
    "src/hakimi_research/synthetic_strategy_report_bundle.py",
    "src/hakimi_research/strategy_family_inventory.py",
    "src/hakimi_research/backtest.py",
    "src/hakimi_research/config.py",
    "src/hakimi_research/distribution_evidence.py",
    "src/hakimi_research/execution.py",
    "src/hakimi_research/experiment_manifest.py",
    "src/hakimi_research/indicators.py",
    "src/hakimi_research/models.py",
    "src/hakimi_research/risk.py",
    "src/hakimi_research/strategies/base.py",
    "src/hakimi_research/strategies/templates.py",
)
_CLAIMS = {
    "real_dataset": False,
    "formal_blind_test": False,
    "profitability": False,
    "ranking": False,
    "parameter_selection": False,
    "paper": False,
    "live": False,
    "order": False,
}


class DeterministicStrategyFamilyBenchmarkError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
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
        raise DeterministicStrategyFamilyBenchmarkError("reference_root_exact_str_required")
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


def build_deterministic_strategy_family_reference_material() -> dict[str, Any]:
    bundle = build_synthetic_strategy_report_bundle_v2(
        execute=True,
        reproducibility_context=_context(),
    )
    receipt = verify_synthetic_strategy_report_bundle_v2(bundle)
    if receipt.get("status") != "PASS":
        raise DeterministicStrategyFamilyBenchmarkError("bundle_verification_failed")
    markdown = render_synthetic_strategy_report_bundle_markdown_v2(bundle)
    bundle_bytes = _json_bytes(bundle)
    markdown_bytes = (markdown.rstrip("\n") + "\n").encode("utf-8")
    source_files = {
        path: _sha256_bytes((REPOSITORY_ROOT / path).read_bytes())
        for path in SOURCE_RELATIVE_PATHS
    }
    runs = [
        *bundle["benchmarks"].values(),
        *[
            run
            for report in bundle["strategy_reports"]
            for run in report["runs"].values()
        ],
    ]
    family_counts = {
        item["family_id"]: item["report_count"]
        for item in bundle["family_summary"]
    }
    manifest_core = {
        "contract_version": MANIFEST_VERSION,
        "maturity": MATURITY,
        "bundle_schema_version": bundle["schema_version"],
        "bundle_sha256": bundle["bundle_sha256"],
        "plan_sha256": bundle["plan"]["plan_sha256"],
        "fixture_sha256": bundle["fixture"]["fixture_sha256"],
        "dataset_sha256": bundle["fixture"]["dataset_sha256"],
        "executed_run_count": bundle["executed_run_count"],
        "dependency_bound_run_count": sum(
            run["result"]["experiment_manifest"]["dependency_lock_hash"]
            == _context()["dependency_lock_hash"]
            for run in runs
        ),
        "git_clean_run_count": sum(
            run["result"]["experiment_manifest"]["git_worktree_clean"] is True
            for run in runs
        ),
        "family_report_counts": family_counts,
        "ensemble_status": next(
            item["status"]
            for item in bundle["family_summary"]
            if item["family_id"] == "ENSEMBLE"
        ),
        "dependency_lock": {
            "name": LOCK_PATH.name,
            "sha256": _context()["dependency_lock_hash"],
            "fully_pinned": True,
        },
        "source_files": source_files,
        "expected_bundle_file_sha256": _sha256_bytes(bundle_bytes),
        "expected_markdown_file_sha256": _sha256_bytes(markdown_bytes),
        "gaps": list(bundle["gaps"]),
        "authority": dict(bundle["authority"]),
        "claims": dict(_CLAIMS),
    }
    manifest = dict(manifest_core)
    manifest["manifest_sha256"] = _sha256_bytes(_canonical_bytes(manifest_core))
    return {
        "bundle": bundle,
        "manifest": manifest,
        "files": {
            "expected_bundle.json": bundle_bytes.decode("utf-8"),
            "expected_bundle.md": markdown_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(manifest).decode("utf-8"),
        },
    }


def verify_deterministic_strategy_family_reference(
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _reference_root(reference_root)
    material = build_deterministic_strategy_family_reference_material()
    expected_bundle_bytes = (root / "expected_bundle.json").read_bytes()
    expected_markdown_bytes = (root / "expected_bundle.md").read_bytes()
    expected_manifest_bytes = (root / "fixture_manifest.json").read_bytes()
    expected_bundle = json.loads(expected_bundle_bytes.decode("utf-8"))
    expected_manifest = json.loads(expected_manifest_bytes.decode("utf-8"))
    manifest = material["manifest"]
    manifest_core = {
        key: value for key, value in expected_manifest.items() if key != "manifest_sha256"
    }
    checks = {
        "reference_file_set": all((root / name).is_file() for name in REFERENCE_FILE_NAMES),
        "lf_only": all(b"\r" not in (root / name).read_bytes() for name in REFERENCE_FILE_NAMES),
        "bundle_exact": expected_bundle == material["bundle"],
        "bundle_bytes_exact": expected_bundle_bytes
        == material["files"]["expected_bundle.json"].encode("utf-8"),
        "markdown_exact": expected_markdown_bytes
        == material["files"]["expected_bundle.md"].encode("utf-8"),
        "manifest_exact": expected_manifest == manifest,
        "manifest_bytes_exact": expected_manifest_bytes
        == material["files"]["fixture_manifest.json"].encode("utf-8"),
        "manifest_self_hash": expected_manifest.get("manifest_sha256")
        == _sha256_bytes(_canonical_bytes(manifest_core)),
        "root_dependency_lock_bound": manifest["dependency_lock"]["sha256"]
        == _context()["dependency_lock_hash"],
        "all_nested_runs_dependency_bound": manifest["dependency_bound_run_count"] == 32,
        "git_gap_retained": manifest["git_clean_run_count"] == 0
        and "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE" in manifest["gaps"],
        "family_scope_bound": manifest["family_report_counts"]
        == {"RANGE": 3, "TREND": 3, "ENSEMBLE": 0},
        "ensemble_gap_retained": manifest["ensemble_status"] == "GAP"
        and "ENSEMBLE_STRATEGY_NOT_IMPLEMENTED" in manifest["gaps"],
        "authority_locked": all(value is False for value in manifest["authority"].values()),
        "claims_locked": all(value is False for value in manifest["claims"].values()),
    }
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        raise DeterministicStrategyFamilyBenchmarkError(
            f"reference_verification_failed:{failed}"
        )
    return {
        "status": "PASS",
        "contract_version": VERIFIER_VERSION,
        "maturity": MATURITY,
        "bundle_sha256": manifest["bundle_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "executed_run_count": manifest["executed_run_count"],
        "dependency_bound_run_count": manifest["dependency_bound_run_count"],
        "git_clean_run_count": manifest["git_clean_run_count"],
        "family_report_counts": manifest["family_report_counts"],
        "ensemble_status": manifest["ensemble_status"],
        "checks": checks,
        "authority": dict(manifest["authority"]),
        "claims": dict(manifest["claims"]),
    }
