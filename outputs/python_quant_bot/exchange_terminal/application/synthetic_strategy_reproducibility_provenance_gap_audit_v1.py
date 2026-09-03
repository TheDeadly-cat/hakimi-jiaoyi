from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


PYTHON_QUANT_BOT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PYTHON_QUANT_BOT_ROOT.parents[1]
for import_root in (PYTHON_QUANT_BOT_ROOT, WORKSPACE_ROOT / "src"):
    import_path = str(import_root)
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


from examples.build_synthetic_strategy_benchmark_report_v5 import (  # noqa: E402
    verify_synthetic_strategy_benchmark_report_v5,
)
from hakimi_research.experiment_manifest import (  # noqa: E402
    _requirements_fully_pinned,
)


PLAN_SCHEMA_VERSION = "synthetic-strategy-reproducibility-provenance-gap-audit-plan-v1"
BUNDLE_SCHEMA_VERSION = "synthetic-strategy-reproducibility-provenance-gap-audit-bundle-v1"
RECEIPT_SCHEMA_VERSION = "synthetic-strategy-reproducibility-provenance-gap-audit-receipt-v1"
DATA_SOURCE = "LOCAL_SOURCE_FILES_READ_ONLY"
EVIDENCE_STATE = "GAP"
MATURITY = "SOURCE_FINGERPRINTS_WITH_UNPINNED_DEPENDENCY_AND_NO_COMMIT_IDENTITY"
STATUS = "BLOCK"
DEPENDENCY_DOCUMENT = "outputs/python_quant_bot/requirements.txt"

_SOURCE_MODULES = (
    "examples.build_synthetic_strategy_benchmark_report_v3",
    "examples.build_synthetic_strategy_benchmark_report_v4",
    "examples.build_synthetic_strategy_benchmark_report_v5",
    "exchange_terminal.application.synthetic_strategy_cscv_pbo_validation_v1",
    "exchange_terminal.application.synthetic_strategy_deflated_sharpe_validation_v1",
    "exchange_terminal.application.synthetic_strategy_high_volatility_validation_v1",
    "exchange_terminal.application.synthetic_strategy_market_regime_validation_v1",
    "exchange_terminal.application.synthetic_strategy_report_bundle_v1",
    "exchange_terminal.application.synthetic_strategy_robustness_evidence_v1",
    "exchange_terminal.application.synthetic_strategy_trial_return_matrix_v1",
    "hakimi_research.cscv_pbo_diagnostic",
    "hakimi_research.deflated_sharpe_diagnostic",
    "hakimi_research.market_regime_evidence",
    "hakimi_research.trial_return_matrix",
    "quant_bot.backtest",
    "hakimi_research.experiment_manifest",
    "quant_bot.risk",
    "quant_bot.strategies.templates",
)

_GAPS = (
    "DEPENDENCY_LOCK_HASH_GAP",
    "DEPENDENCY_LOCK_NOT_FULLY_PINNED",
    "PROVENANCE_AUDIT_NOT_REPRODUCIBILITY_COMPLETION",
    "SOURCE_COMMIT_SHA_GAP",
    "SOURCE_WORKTREE_IDENTITY_REQUIRES_AUTHORIZED_SNAPSHOT",
)

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
_MODULE_NAME_RE = re.compile(
    r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+"
)


class SyntheticStrategyReproducibilityProvenanceGapAuditError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise SyntheticStrategyReproducibilityProvenanceGapAuditError(
        f"{path}: {message}"
    )


def _gaps() -> list[str]:
    return list(_GAPS)


def _authority() -> dict[str, bool]:
    return dict(_AUTHORITY)


def _assert_exact_json(value: Any, path: str) -> None:
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                _fail(path, "contains a non-native string key")
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
    _fail(path, "must contain exact finite JSON-native values")


def _canonical_sha256(value: dict[str, Any] | list[Any]) -> str:
    _assert_exact_json(value, "canonical_payload")
    payload = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    return {**record, field: _canonical_sha256(record)}


def _verify_seal(record: dict[str, Any], field: str, path: str) -> None:
    digest = record.get(field)
    if type(digest) is not str or _SHA256_RE.fullmatch(digest) is None:
        _fail(f"{path}.{field}", "must be an exact lowercase SHA-256 string")
    payload = {key: value for key, value in record.items() if key != field}
    if digest != _canonical_sha256(payload):
        _fail(f"{path}.{field}", "digest mismatch")


def _relative_source_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError as exc:
        raise SyntheticStrategyReproducibilityProvenanceGapAuditError(
            f"source_path: {resolved} escapes the workspace"
        ) from exc
    return relative.as_posix()


def _source_path_for_module(module_name: str) -> Path:
    if (
        type(module_name) is not str
        or _MODULE_NAME_RE.fullmatch(module_name) is None
    ):
        _fail("source_module", "must be a preregistered native module name")
    if module_name.startswith("hakimi_research."):
        source_root = WORKSPACE_ROOT / "src"
    elif module_name.startswith(("examples.", "exchange_terminal.", "quant_bot.")):
        source_root = PYTHON_QUANT_BOT_ROOT
    else:
        _fail(module_name, "is outside preregistered source namespaces")
    path = source_root.joinpath(*module_name.split(".")).with_suffix(".py")
    resolved = path.resolve()
    if not resolved.is_file():
        _fail(module_name, "does not resolve to a current source file")
    return resolved


def _critical_source_manifest() -> dict[str, Any]:
    files = []
    seen_paths: set[str] = set()
    for module_name in _SOURCE_MODULES:
        path = _source_path_for_module(module_name)
        relative_path = _relative_source_path(path)
        if relative_path in seen_paths:
            _fail(module_name, "duplicates a preregistered source path")
        seen_paths.add(relative_path)
        payload = path.read_bytes()
        files.append(
            {
                "module": module_name,
                "path": relative_path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "byte_count": len(payload),
            }
        )
    files.sort(key=lambda item: item["module"])
    payload = {
        "scope": "PREREGISTERED_CRITICAL_SOURCE_MODULES",
        "module_count": len(files),
        "files": files,
    }
    return _seal(payload, "source_manifest_sha256")


def _dependency_audit() -> dict[str, Any]:
    path = WORKSPACE_ROOT / DEPENDENCY_DOCUMENT
    payload = path.read_bytes()
    text = payload.decode("utf-8", errors="strict")
    unpinned_entries = []
    requirement_count = 0
    exact_pin_count = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        requirement_count += 1
        if "==" in line:
            exact_pin_count += 1
        else:
            unpinned_entries.append(
                {"line_number": line_number, "requirement": line}
            )
    fully_pinned = _requirements_fully_pinned(text)
    if fully_pinned or not unpinned_entries:
        _fail("requirements.txt", "v1 GAP audit requires the observed unpinned state")
    return {
        "path": DEPENDENCY_DOCUMENT,
        "document_kind": "DEPENDENCY_SPEC_NOT_LOCK",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_count": len(payload),
        "requirement_count": requirement_count,
        "exact_pin_count": exact_pin_count,
        "unpinned_count": len(unpinned_entries),
        "unpinned_entries": unpinned_entries,
        "dependency_lock_fully_pinned": False,
        "dependency_lock_identity_state": "GAP",
    }


def _walk_dicts(value: Any):
    if type(value) is dict:
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif type(value) is list:
        for child in value:
            yield from _walk_dicts(child)


def _run_manifest_audit(source_report_v5: dict[str, Any]) -> dict[str, Any]:
    manifest_by_hash: dict[str, dict[str, Any]] = {}
    fingerprint_by_run_hash: dict[str, dict[str, Any]] = {}
    for document in _walk_dicts(source_report_v5):
        manifest = document.get("experiment_manifest")
        reproducibility = document.get("reproducibility")
        if type(manifest) is not dict or type(reproducibility) is not dict:
            continue
        if manifest.get("schema_version") != "reproducible-experiment-manifest-v1":
            continue
        manifest_hash = manifest.get("manifest_hash")
        run_hash = reproducibility.get("run_hash")
        strategy_fingerprint = reproducibility.get("strategy_code_fingerprint")
        if (
            type(manifest_hash) is not str
            or _SHA256_RE.fullmatch(manifest_hash) is None
            or type(run_hash) is not str
            or _SHA256_RE.fullmatch(run_hash) is None
            or type(strategy_fingerprint) is not str
            or _SHA256_RE.fullmatch(strategy_fingerprint) is None
        ):
            _fail("source_report_v5", "contains an invalid embedded manifest identity")
        if manifest.get("source_run_hash") != run_hash:
            _fail("source_report_v5", "manifest and reproducibility run hashes differ")
        manifest_projection = {
            "manifest_hash": manifest_hash,
            "source_run_hash": run_hash,
            "git_commit_sha": manifest.get("git_commit_sha"),
            "git_worktree_clean": manifest.get("git_worktree_clean"),
            "dependency_lock_name": manifest.get("dependency_lock_name"),
            "dependency_lock_hash": manifest.get("dependency_lock_hash"),
            "dependency_lock_fully_pinned": manifest.get(
                "dependency_lock_fully_pinned"
            ),
            "status": manifest.get("status"),
            "classification": manifest.get("classification"),
            "blockers": deepcopy(manifest.get("blockers")),
            "ranking_gate_status": manifest.get("ranking_gate", {}).get("status"),
            "ranking_input_allowed": manifest.get("ranking_gate", {}).get(
                "input_allowed"
            ),
        }
        existing_manifest = manifest_by_hash.get(manifest_hash)
        if existing_manifest is not None and existing_manifest != manifest_projection:
            _fail("source_report_v5", "manifest hash aliases conflicting projections")
        manifest_by_hash[manifest_hash] = manifest_projection

        fingerprint_projection = {
            "run_hash": run_hash,
            "strategy_code_fingerprint": strategy_fingerprint,
            "param_hash": reproducibility.get("param_hash"),
            "risk_hash": reproducibility.get("risk_hash"),
            "config_hash": reproducibility.get("config_hash"),
            "data_hash": reproducibility.get("data_hash"),
            "execution_model": reproducibility.get("execution_model"),
            "strategy_version": reproducibility.get("strategy_version"),
        }
        existing_fingerprint = fingerprint_by_run_hash.get(run_hash)
        if (
            existing_fingerprint is not None
            and existing_fingerprint != fingerprint_projection
        ):
            _fail("source_report_v5", "run hash aliases conflicting fingerprints")
        fingerprint_by_run_hash[run_hash] = fingerprint_projection

    manifests = sorted(manifest_by_hash.values(), key=lambda item: item["manifest_hash"])
    fingerprints = sorted(
        fingerprint_by_run_hash.values(), key=lambda item: item["run_hash"]
    )
    if len(manifests) < 7 or len(manifests) != len(fingerprints):
        _fail("source_report_v5", "embedded run-manifest coverage is incomplete")

    required_blockers = {
        "dependency_lock_hash_missing_or_invalid",
        "dependency_lock_name_missing_or_invalid",
        "dependency_lock_not_fully_pinned",
        "git_commit_sha_missing_or_invalid",
        "git_worktree_not_clean",
    }
    for index, manifest in enumerate(manifests):
        blockers = manifest["blockers"]
        if type(blockers) is not list or not required_blockers.issubset(set(blockers)):
            _fail(f"manifests[{index}]", "does not retain required provenance blockers")
        if (
            manifest["git_commit_sha"] != ""
            or manifest["git_worktree_clean"] is not False
            or manifest["dependency_lock_name"] != ""
            or manifest["dependency_lock_hash"] != ""
            or manifest["dependency_lock_fully_pinned"] is not False
            or manifest["status"] != "BLOCK"
            or manifest["classification"] != "REPRODUCIBILITY_INCOMPLETE"
            or manifest["ranking_gate_status"] != "BLOCK"
            or manifest["ranking_input_allowed"] is not False
        ):
            _fail(f"manifests[{index}]", "provenance GAP state drifted")

    payload = {
        "collection_policy": "RECURSIVE_UNIQUE_EMBEDDED_RESULT_MANIFESTS",
        "logical_source_run_count": source_report_v5["source_logical_run_count"],
        "unique_run_manifest_count": len(manifests),
        "unique_strategy_fingerprint_count": len(
            {item["strategy_code_fingerprint"] for item in fingerprints}
        ),
        "valid_git_commit_identity_count": sum(
            1
            for item in manifests
            if type(item["git_commit_sha"]) is str
            and _GIT_SHA_RE.fullmatch(item["git_commit_sha"]) is not None
        ),
        "clean_worktree_identity_count": sum(
            1 for item in manifests if item["git_worktree_clean"] is True
        ),
        "fully_pinned_dependency_identity_count": sum(
            1
            for item in manifests
            if item["dependency_lock_fully_pinned"] is True
            and type(item["dependency_lock_hash"]) is str
            and _SHA256_RE.fullmatch(item["dependency_lock_hash"]) is not None
        ),
        "manifests": manifests,
        "strategy_fingerprints": fingerprints,
    }
    return _seal(payload, "run_manifest_audit_sha256")


def _plan_payload_v1() -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "data_source": DATA_SOURCE,
        "source_modules": list(_SOURCE_MODULES),
        "critical_source_manifest": _critical_source_manifest(),
        "dependency_audit": _dependency_audit(),
        "source_commit_collection_policy": "DO_NOT_CALL_GIT_IN_SYNTHETIC_AUDIT",
        "run_manifest_collection_policy": (
            "RECURSIVE_UNIQUE_EMBEDDED_RESULT_MANIFESTS"
        ),
        "requires_prebuilt_benchmark_v5": True,
        "requires_exact_execute_true": True,
        "runtime_mutations": False,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "gaps": _gaps(),
        "authority": _authority(),
    }


def plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
) -> dict[str, Any]:
    payload = _plan_payload_v1()
    return {**payload, "plan_sha256": _canonical_sha256(payload)}


def verify_synthetic_strategy_reproducibility_provenance_gap_audit_plan_v1(
    plan: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(plan, "plan")
    expected = plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1()
    if plan != expected:
        _fail("plan", "does not match current preregistered source fingerprints")
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "PASS",
        "plan_sha256": plan["plan_sha256"],
        "critical_source_module_count": plan["critical_source_manifest"][
            "module_count"
        ],
        "dependency_lock_fully_pinned": False,
        "runtime_mutations": False,
        "authority": _authority(),
    }


def build_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
    source_report_v5: dict[str, Any] | None = None,
    *,
    execute: bool = False,
) -> dict[str, Any]:
    if type(execute) is not bool:
        _fail("execute", "must be exact bool")
    plan = plan_synthetic_strategy_reproducibility_provenance_gap_audit_v1()
    if not execute:
        if source_report_v5 is not None:
            _fail("source_report_v5", "dry plan must not accept an unverified source")
        return plan
    if type(source_report_v5) is not dict:
        _fail("source_report_v5", "must be an exact dict")
    _assert_exact_json(source_report_v5, "source_report_v5")
    verify_synthetic_strategy_benchmark_report_v5(source_report_v5)
    run_manifest_audit = _run_manifest_audit(source_report_v5)

    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "data_source": DATA_SOURCE,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "status": STATUS,
        "plan": plan,
        "source_report_v5_sha256": source_report_v5["report_sha256"],
        "source_report_v5_plan_sha256": source_report_v5["plan"]["plan_sha256"],
        "source_logical_run_count": source_report_v5["source_logical_run_count"],
        "critical_source_manifest": deepcopy(plan["critical_source_manifest"]),
        "dependency_audit": deepcopy(plan["dependency_audit"]),
        "run_manifest_audit": run_manifest_audit,
        "valid_git_commit_identity_count": run_manifest_audit[
            "valid_git_commit_identity_count"
        ],
        "fully_pinned_dependency_identity_count": run_manifest_audit[
            "fully_pinned_dependency_identity_count"
        ],
        "runtime_mutations": False,
        "gaps": _gaps(),
        "authority": _authority(),
    }
    bundle = _seal(payload, "bundle_sha256")
    verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
        bundle, source_report_v5
    )
    return bundle


def verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
    bundle: dict[str, Any],
    source_report_v5: dict[str, Any],
) -> dict[str, Any]:
    _assert_exact_json(bundle, "bundle")
    _assert_exact_json(source_report_v5, "source_report_v5")
    required_keys = {
        "schema_version",
        "data_source",
        "evidence_state",
        "maturity",
        "status",
        "plan",
        "source_report_v5_sha256",
        "source_report_v5_plan_sha256",
        "source_logical_run_count",
        "critical_source_manifest",
        "dependency_audit",
        "run_manifest_audit",
        "valid_git_commit_identity_count",
        "fully_pinned_dependency_identity_count",
        "runtime_mutations",
        "gaps",
        "authority",
        "bundle_sha256",
    }
    if set(bundle) != required_keys:
        _fail("bundle", "fields do not match the contract")
    if (
        bundle["schema_version"] != BUNDLE_SCHEMA_VERSION
        or bundle["data_source"] != DATA_SOURCE
    ):
        _fail("bundle", "identity mismatch")
    if (
        bundle["evidence_state"] != EVIDENCE_STATE
        or bundle["maturity"] != MATURITY
        or bundle["status"] != STATUS
    ):
        _fail("bundle", "must remain GAP/BLOCK")
    if bundle["gaps"] != _gaps() or bundle["authority"] != _authority():
        _fail("bundle", "gaps or authority drifted")
    if bundle["runtime_mutations"] is not False:
        _fail("bundle.runtime_mutations", "must be exact false")
    verify_synthetic_strategy_reproducibility_provenance_gap_audit_plan_v1(
        bundle["plan"]
    )
    verify_synthetic_strategy_benchmark_report_v5(source_report_v5)
    if (
        bundle["source_report_v5_sha256"] != source_report_v5["report_sha256"]
        or bundle["source_report_v5_plan_sha256"]
        != source_report_v5["plan"]["plan_sha256"]
        or bundle["source_logical_run_count"]
        != source_report_v5["source_logical_run_count"]
    ):
        _fail("bundle", "benchmark v5 source binding mismatch")

    plan = bundle["plan"]
    if bundle["critical_source_manifest"] != plan["critical_source_manifest"]:
        _fail("bundle.critical_source_manifest", "current source binding mismatch")
    if bundle["dependency_audit"] != plan["dependency_audit"]:
        _fail("bundle.dependency_audit", "current dependency audit mismatch")
    expected_run_audit = _run_manifest_audit(source_report_v5)
    if bundle["run_manifest_audit"] != expected_run_audit:
        _fail("bundle.run_manifest_audit", "embedded manifest audit mismatch")
    if (
        bundle["valid_git_commit_identity_count"] != 0
        or bundle["fully_pinned_dependency_identity_count"] != 0
        or expected_run_audit["valid_git_commit_identity_count"] != 0
        or expected_run_audit["fully_pinned_dependency_identity_count"] != 0
    ):
        _fail("bundle", "provenance GAP was incorrectly closed")
    _verify_seal(bundle, "bundle_sha256", "bundle")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "bundle_sha256": bundle["bundle_sha256"],
        "critical_source_module_count": bundle["critical_source_manifest"][
            "module_count"
        ],
        "requirement_count": bundle["dependency_audit"]["requirement_count"],
        "unpinned_requirement_count": bundle["dependency_audit"][
            "unpinned_count"
        ],
        "unique_run_manifest_count": bundle["run_manifest_audit"][
            "unique_run_manifest_count"
        ],
        "valid_git_commit_identity_count": 0,
        "fully_pinned_dependency_identity_count": 0,
        "evidence_state": EVIDENCE_STATE,
        "maturity": MATURITY,
        "permission": STATUS,
        "authority": _authority(),
    }


def render_synthetic_strategy_reproducibility_provenance_gap_audit_markdown_v1(
    bundle: dict[str, Any],
    source_report_v5: dict[str, Any],
) -> str:
    receipt = verify_synthetic_strategy_reproducibility_provenance_gap_audit_v1(
        bundle, source_report_v5
    )
    return "\n".join(
        (
            "# Synthetic Strategy Reproducibility Provenance GAP Audit v1",
            "",
            "Non-current, read-only provenance audit. It does not call Git.",
            "",
            "| Stage | Value |",
            "| --- | --- |",
            f"| SOURCE | {DATA_SOURCE} |",
            f"| GAP | {', '.join(bundle['gaps'])} |",
            f"| MATURITY | {MATURITY} |",
            f"| PERMISSION | {STATUS} |",
            "",
            (
                "- Critical source modules fingerprinted: "
                f"{receipt['critical_source_module_count']}"
            ),
            f"- Requirements entries: {receipt['requirement_count']}",
            (
                "- Unpinned requirements entries: "
                f"{receipt['unpinned_requirement_count']}"
            ),
            (
                "- Unique embedded run manifests audited: "
                f"{receipt['unique_run_manifest_count']}"
            ),
            "- Valid Git commit identities: 0",
            "- Fully pinned dependency identities: 0",
            "- Formal reproducibility completion: not established",
            "- Paper/live/order entry: not authorized",
            f"- Bundle SHA-256: `{bundle['bundle_sha256']}`",
        )
    )
