from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.synthetic_strategy_report_bundle import (
    build_synthetic_strategy_report_bundle_v2,
    verify_synthetic_strategy_report_bundle_v2,
)
from hakimi_research.synthetic_strategy_robustness_evidence import (
    build_synthetic_strategy_robustness_evidence_v2,
    verify_synthetic_strategy_robustness_evidence_v2,
)


CONTRACT_VERSION = "deterministic-strategy-robustness-benchmark-v1"
VERIFIER_VERSION = "deterministic-strategy-robustness-benchmark-verifier-v1"
MANIFEST_VERSION = "deterministic-strategy-robustness-benchmark-manifest-v1"
RECEIPT_VERSION = "deterministic-strategy-robustness-benchmark-receipt-v1"
MATURITY = "SYNTHETIC_ROBUSTNESS_ONLY"
REFERENCE_ROOT = (
    REPOSITORY_ROOT
    / "examples"
    / "deterministic_strategy_robustness_benchmark_v1"
)
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"
REFERENCE_FILE_NAMES = (
    "expected_receipt.json",
    "expected_receipt.md",
    "fixture_manifest.json",
)
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_strategy_robustness_benchmark.py",
    "src/hakimi_research/synthetic_strategy_robustness_evidence.py",
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
    "src/hakimi_research/source_layout.py",
    "src/hakimi_research/strategies/base.py",
    "src/hakimi_research/strategies/templates.py",
    "src/hakimi_research/validation_evidence.py",
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


class DeterministicStrategyRobustnessBenchmarkError(ValueError):
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
        raise DeterministicStrategyRobustnessBenchmarkError(
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
        raise DeterministicStrategyRobustnessBenchmarkError(
            "source_bundle_verification_failed"
        )
    robustness_bundle = build_synthetic_strategy_robustness_evidence_v2(
        source_bundle,
        execute=True,
    )
    robustness_receipt = verify_synthetic_strategy_robustness_evidence_v2(
        robustness_bundle
    )
    if robustness_receipt.get("status") != "PASS":
        raise DeterministicStrategyRobustnessBenchmarkError(
            "robustness_bundle_verification_failed"
        )
    ledger = robustness_bundle["run_reproducibility_ledger"]
    receipt_core = {
        "schema_version": RECEIPT_VERSION,
        "maturity": MATURITY,
        "status": "BLOCK",
        "source_schema_version": source_bundle["schema_version"],
        "robustness_schema_version": robustness_bundle["schema_version"],
        "source_bundle_sha256": source_bundle["bundle_sha256"],
        "robustness_bundle_sha256": robustness_bundle["bundle_sha256"],
        "robustness_plan_sha256": robustness_bundle["plan"]["plan_sha256"],
        "run_reproducibility_ledger_sha256": ledger["ledger_sha256"],
        "source_executed_run_count": source_bundle["executed_run_count"],
        "robustness_executed_run_count": robustness_bundle[
            "executed_run_count"
        ],
        "total_executed_run_count": (
            source_bundle["executed_run_count"]
            + robustness_bundle["executed_run_count"]
        ),
        "source_dependency_bound_run_count": source_receipt[
            "dependency_bound_run_count"
        ],
        "robustness_dependency_bound_run_count": robustness_receipt[
            "dependency_bound_run_count"
        ],
        "total_dependency_bound_run_count": (
            source_receipt["dependency_bound_run_count"]
            + robustness_receipt["dependency_bound_run_count"]
        ),
        "git_bound_run_count": (
            source_receipt["git_bound_run_count"]
            + robustness_receipt["git_bound_run_count"]
        ),
        "evaluation_role_counts": dict(ledger["evaluation_role_counts"]),
        "registered_strategy_ids": list(
            robustness_bundle["plan"]["registered_strategy_ids"]
        ),
        "completed_evidence": list(robustness_bundle["completed_evidence"]),
        "gaps": list(robustness_bundle["gaps"]),
        "runtime_mutations": False,
        "authority": dict(robustness_bundle["authority"]),
        "claims": dict(_CLAIMS),
    }
    receipt = dict(receipt_core)
    receipt["receipt_sha256"] = _sha256_bytes(_canonical_bytes(receipt_core))
    return receipt


def _render_receipt_markdown(receipt: dict[str, Any]) -> str:
    lines = [
        "# Deterministic Synthetic Strategy Robustness Benchmark",
        "",
        "## SOURCE",
        "",
        f"- Source bundle SHA-256: `{receipt['source_bundle_sha256']}`",
        f"- Robustness bundle SHA-256: `{receipt['robustness_bundle_sha256']}`",
        f"- Robustness plan SHA-256: `{receipt['robustness_plan_sha256']}`",
        (
            "- Run reproducibility ledger SHA-256: "
            f"`{receipt['run_reproducibility_ledger_sha256']}`"
        ),
        (
            "- Executed runs: "
            f"{receipt['source_executed_run_count']} source + "
            f"{receipt['robustness_executed_run_count']} robustness = "
            f"{receipt['total_executed_run_count']}."
        ),
        (
            "- Dependency-bound runs: "
            f"{receipt['total_dependency_bound_run_count']}."
        ),
        (
            "- Robustness evaluation roles: "
            f"TRAIN {receipt['evaluation_role_counts']['TRAIN']}, "
            f"VALIDATION {receipt['evaluation_role_counts']['VALIDATION']}, "
            f"FROZEN_TEST {receipt['evaluation_role_counts']['FROZEN_TEST']}."
        ),
        "",
        "## GAP",
        "",
        *[f"- `{gap}`" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        "",
        "- Status: `BLOCK`",
        "- Maturity: `SYNTHETIC_ROBUSTNESS_ONLY`",
        "- Evidence is deterministic, pure synthetic, and in-memory.",
        "- FROZEN_TEST is a synthetic protocol role, not a formal blind test.",
        "",
        "## PERMISSION",
        "",
        "- Profitability proven: `false`",
        "- Formal blind test complete: `false`",
        "- Ranking authorized: `false`",
        "- Parameter selection authorized: `false`",
        "- Paper authorized: `false`",
        "- Live authorized: `false`",
        "- Order entry authorized: `false`",
        "",
        f"Receipt SHA-256: `{receipt['receipt_sha256']}`",
    ]
    markdown = "\n".join(lines) + "\n"
    if "READY" in markdown:
        raise DeterministicStrategyRobustnessBenchmarkError(
            "neutral_renderer_token_violation"
        )
    return markdown


def build_deterministic_strategy_robustness_reference_material() -> dict[str, Any]:
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
        "robustness_plan_sha256": receipt["robustness_plan_sha256"],
        "run_reproducibility_ledger_sha256": receipt[
            "run_reproducibility_ledger_sha256"
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
        "gaps": list(receipt["gaps"]),
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


def verify_deterministic_strategy_robustness_reference(
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = _reference_root(reference_root)
    if not root.is_dir():
        raise DeterministicStrategyRobustnessBenchmarkError(
            "reference_root_missing"
        )
    material = build_deterministic_strategy_robustness_reference_material()
    file_names = sorted(
        path.name for path in root.iterdir() if path.is_file()
    )
    required_names = sorted(REFERENCE_FILE_NAMES)
    for name in REFERENCE_FILE_NAMES:
        if not (root / name).is_file():
            raise DeterministicStrategyRobustnessBenchmarkError(
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
        and not {
            "source_bundle",
            "strategy_evidence",
            "run_reproducibility_ledger",
        }.intersection(expected_receipt),
        "root_dependency_lock_bound": manifest["dependency_lock"]["sha256"]
        == _context()["dependency_lock_hash"],
        "source_closure_bound": set(manifest["source_files"])
        == set(SOURCE_RELATIVE_PATHS),
        "all_nested_runs_dependency_bound": receipt[
            "total_dependency_bound_run_count"
        ]
        == 179,
        "git_gap_retained": receipt["git_bound_run_count"] == 0
        and "SOURCE_COMMIT_NOT_BOUND_FOR_UNCOMMITTED_SLICE"
        in receipt["gaps"],
        "role_counts_bound": receipt["evaluation_role_counts"]
        == {"TRAIN": 54, "VALIDATION": 54, "FROZEN_TEST": 39},
        "strategy_scope_bound": receipt["registered_strategy_ids"]
        == ["bollinger", "dual_ma", "grid", "macd", "momentum", "rsi"],
        "dependency_gap_closed": "DEPENDENCY_LOCK_NOT_BOUND"
        not in receipt["gaps"],
        "status_blocked": receipt["status"] == "BLOCK"
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
        raise DeterministicStrategyRobustnessBenchmarkError(
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
        "robustness_plan_sha256": receipt["robustness_plan_sha256"],
        "run_reproducibility_ledger_sha256": receipt[
            "run_reproducibility_ledger_sha256"
        ],
        "source_executed_run_count": receipt["source_executed_run_count"],
        "robustness_executed_run_count": receipt[
            "robustness_executed_run_count"
        ],
        "total_executed_run_count": receipt["total_executed_run_count"],
        "total_dependency_bound_run_count": receipt[
            "total_dependency_bound_run_count"
        ],
        "git_bound_run_count": receipt["git_bound_run_count"],
        "evaluation_role_counts": dict(receipt["evaluation_role_counts"]),
        "checks": checks,
        "authority": dict(receipt["authority"]),
        "claims": dict(receipt["claims"]),
    }
