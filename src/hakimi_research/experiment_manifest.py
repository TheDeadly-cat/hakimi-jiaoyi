from __future__ import annotations

import hashlib
import json
import math
import platform
from pathlib import Path
import re
import subprocess
from typing import Any


SCHEMA_VERSION = "reproducible-experiment-manifest-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_EXPERIMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_EVALUATION_ROLES = frozenset({"UNCLASSIFIED", "TRAIN", "VALIDATION", "FROZEN_TEST"})
_RANKING_ROLES = frozenset({"VALIDATION", "FROZEN_TEST"})
_MANIFEST_FIELDS = frozenset({
    "schema_version",
    "status",
    "classification",
    "experiment_id",
    "git_commit_sha",
    "git_worktree_clean",
    "strategy_name",
    "strategy_version",
    "config_hash",
    "dataset_hash",
    "dependency_lock_hash",
    "dependency_lock_fully_pinned",
    "dependency_lock_name",
    "start_time",
    "end_time",
    "symbol",
    "timeframe",
    "fee_model",
    "slippage_model",
    "random_seed",
    "runtime_version",
    "evaluation_role",
    "evaluation_protocol_hash",
    "evaluation_protocol_verified",
    "source_run_hash",
    "result_hash",
    "blockers",
    "ranking_gate",
    "research_only",
    "parameter_selection_allowed",
    "paper_authorized",
    "live_order_allowed",
    "order_entry_allowed",
    "result_is_profitability_proof",
    "manifest_hash",
})
_NATIVE_PATH_TYPE = type(Path())


def _is_exact_native_json(value: Any) -> bool:
    if value is None or type(value) in (bool, int, str):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_is_exact_native_json(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_exact_native_json(item)
            for key, item in value.items()
        )
    return False


def canonical_payload_hash(payload: Any) -> str:
    if not _is_exact_native_json(payload):
        return ""
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return ""
    return hashlib.sha256(encoded).hexdigest()


def _native_text(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _valid_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _requirements_fully_pinned(text: str) -> bool:
    if type(text) is not str:
        return False
    requirements = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "-"))
    ]
    return bool(requirements) and all(
        "==" in requirement
        and not any(operator in requirement for operator in (">=", "<=", "~=", "!=", ">", "<"))
        for requirement in requirements
    )


def _git_output(root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def build_local_experiment_context(project_root: str | Path) -> dict[str, Any]:
    if type(project_root) is str:
        if not project_root or project_root != project_root.strip():
            raise ValueError("experiment_manifest_project_root_invalid")
        root = Path(project_root).resolve()
    elif type(project_root) is _NATIVE_PATH_TYPE:
        root = project_root.resolve()
    else:
        raise ValueError("experiment_manifest_project_root_exact_native_required")
    git_commit_sha = _git_output(root, "rev-parse", "HEAD")
    git_status = _git_output(root, "status", "--porcelain", "--untracked-files=normal")
    git_worktree_clean = bool(git_commit_sha) and not git_status

    dependency_path = next(
        (
            candidate
            for candidate in (
                root / "requirements.research.lock",
                root / "requirements.lock",
                root / "requirements.txt",
            )
            if candidate.is_file()
        ),
        None,
    )
    dependency_lock_hash = ""
    dependency_lock_fully_pinned = False
    dependency_lock_name = ""
    if dependency_path is not None:
        dependency_bytes = dependency_path.read_bytes()
        dependency_text = dependency_bytes.decode("utf-8", errors="strict")
        dependency_lock_hash = hashlib.sha256(dependency_bytes).hexdigest()
        dependency_lock_fully_pinned = _requirements_fully_pinned(dependency_text)
        dependency_lock_name = dependency_path.name

    return {
        "git_commit_sha": git_commit_sha,
        "git_worktree_clean": git_worktree_clean,
        "dependency_lock_hash": dependency_lock_hash,
        "dependency_lock_fully_pinned": dependency_lock_fully_pinned,
        "dependency_lock_name": dependency_lock_name,
        "random_seed": 0,
        "runtime_version": f"{platform.python_implementation()} {platform.python_version()}",
        "evaluation_role": "UNCLASSIFIED",
        "evaluation_protocol_hash": "",
        "evaluation_protocol_verified": False,
    }


def _reproducibility_blockers(document: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if document.get("schema_version") != SCHEMA_VERSION:
        blockers.append("manifest_schema_invalid")
    if type(document.get("experiment_id")) is not str or _EXPERIMENT_ID_RE.fullmatch(
        document["experiment_id"]
    ) is None:
        blockers.append("experiment_id_invalid")
    if type(document.get("git_commit_sha")) is not str or _GIT_SHA_RE.fullmatch(
        document["git_commit_sha"]
    ) is None:
        blockers.append("git_commit_sha_missing_or_invalid")
    if document.get("git_worktree_clean") is not True:
        blockers.append("git_worktree_not_clean")
    for field in (
        "strategy_name",
        "strategy_version",
        "dependency_lock_name",
        "start_time",
        "end_time",
        "symbol",
        "timeframe",
        "runtime_version",
    ):
        if not _native_text(document.get(field)):
            blockers.append(f"{field}_missing_or_invalid")
    for field in (
        "config_hash",
        "dataset_hash",
        "dependency_lock_hash",
        "source_run_hash",
        "result_hash",
    ):
        if not _valid_sha256(document.get(field)):
            blockers.append(f"{field}_missing_or_invalid")
    if document.get("dependency_lock_fully_pinned") is not True:
        blockers.append("dependency_lock_not_fully_pinned")
    if type(document.get("random_seed")) is not int:
        blockers.append("random_seed_invalid")
    for field in ("fee_model", "slippage_model"):
        model = document.get(field)
        if (
            type(model) is not dict
            or set(model) != {"kind", "rate"}
            or model.get("kind") != "proportional"
            or not _native_text(model.get("rate"))
        ):
            blockers.append(f"{field}_invalid")
    if document.get("evaluation_role") not in _EVALUATION_ROLES:
        blockers.append("evaluation_role_invalid")
    authority_locks = {
        "research_only": True,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    for field, expected in authority_locks.items():
        if document.get(field) is not expected:
            blockers.append(f"{field}_lock_invalid")
    return sorted(set(blockers))


def _ranking_blockers(document: dict[str, Any], blockers: list[str]) -> list[str]:
    ranking_blockers = list(blockers)
    role = document.get("evaluation_role")
    if role == "TRAIN":
        ranking_blockers.append("training_result_not_rankable")
    elif role not in _RANKING_ROLES:
        ranking_blockers.append("evaluation_role_not_rankable")
    if role in _RANKING_ROLES:
        if not _valid_sha256(document.get("evaluation_protocol_hash")):
            ranking_blockers.append("evaluation_protocol_hash_missing_or_invalid")
        if document.get("evaluation_protocol_verified") is not True:
            ranking_blockers.append("evaluation_protocol_not_verified")
    return sorted(set(ranking_blockers))


def build_reproducible_experiment_manifest(
    *,
    result_payload: dict[str, Any],
    reproducibility: dict[str, Any],
    strategy_name: str,
    strategy_version: str,
    symbol: str,
    timeframe: str,
    fee_rate: float,
    slippage_pct: float,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if type(result_payload) is not dict or not _is_exact_native_json(result_payload):
        raise ValueError("experiment_manifest_result_payload_exact_native_required")
    if type(reproducibility) is not dict or not _is_exact_native_json(reproducibility):
        raise ValueError("experiment_manifest_reproducibility_exact_native_required")
    for field, value in (
        ("strategy_name", strategy_name),
        ("strategy_version", strategy_version),
        ("symbol", symbol),
        ("timeframe", timeframe),
    ):
        if type(value) is not str:
            raise ValueError(f"experiment_manifest_{field}_exact_str_required")
    for field, value in (("fee_rate", fee_rate), ("slippage_pct", slippage_pct)):
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise ValueError(f"experiment_manifest_{field}_exact_finite_number_required")
    if context is not None and (
        type(context) is not dict or not _is_exact_native_json(context)
    ):
        raise ValueError("experiment_manifest_context_exact_native_required")
    clean_context = dict(context) if context is not None else {}
    result_hash = canonical_payload_hash(result_payload)
    source_run_hash = reproducibility.get("run_hash")
    identity_hash = canonical_payload_hash({
        "source_run_hash": source_run_hash,
        "result_hash": result_hash,
    })
    experiment_id = clean_context.get("experiment_id")
    if type(experiment_id) is not str or not experiment_id:
        experiment_id = f"hexp-{identity_hash[:20]}" if identity_hash else ""
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCK",
        "classification": "REPRODUCIBILITY_INCOMPLETE",
        "experiment_id": experiment_id,
        "git_commit_sha": clean_context.get("git_commit_sha", ""),
        "git_worktree_clean": clean_context.get("git_worktree_clean", False),
        "strategy_name": strategy_name,
        "strategy_version": strategy_version,
        "config_hash": reproducibility.get("config_hash", ""),
        "dataset_hash": reproducibility.get("data_hash", ""),
        "dependency_lock_hash": clean_context.get("dependency_lock_hash", ""),
        "dependency_lock_fully_pinned": clean_context.get(
            "dependency_lock_fully_pinned", False
        ),
        "dependency_lock_name": clean_context.get("dependency_lock_name", ""),
        "start_time": reproducibility.get("data_start", ""),
        "end_time": reproducibility.get("data_end", ""),
        "symbol": symbol,
        "timeframe": timeframe,
        "fee_model": {
            "kind": "proportional",
            "rate": format(float(fee_rate), ".17g"),
        },
        "slippage_model": {
            "kind": "proportional",
            "rate": format(float(slippage_pct), ".17g"),
        },
        "random_seed": clean_context.get("random_seed", 0),
        "runtime_version": clean_context.get(
            "runtime_version",
            f"{platform.python_implementation()} {platform.python_version()}",
        ),
        "evaluation_role": clean_context.get("evaluation_role", "UNCLASSIFIED"),
        "evaluation_protocol_hash": clean_context.get("evaluation_protocol_hash", ""),
        "evaluation_protocol_verified": clean_context.get(
            "evaluation_protocol_verified", False
        ),
        "source_run_hash": source_run_hash,
        "result_hash": result_hash,
        "blockers": [],
        "ranking_gate": {
            "status": "BLOCK",
            "input_allowed": False,
            "blockers": [],
        },
        "research_only": True,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
        "manifest_hash": "",
    }
    blockers = _reproducibility_blockers(document)
    ranking_blockers = _ranking_blockers(document, blockers)
    document["blockers"] = blockers
    document["status"] = "PASS" if not blockers else "BLOCK"
    document["classification"] = (
        "REPRODUCIBILITY_COMPLETE"
        if not blockers
        else "REPRODUCIBILITY_INCOMPLETE"
    )
    document["ranking_gate"] = {
        "status": "PASS" if not ranking_blockers else "BLOCK",
        "input_allowed": not ranking_blockers,
        "blockers": ranking_blockers,
    }
    document["manifest_hash"] = canonical_payload_hash({
        key: value for key, value in document.items() if key != "manifest_hash"
    })
    return document


def verify_reproducible_experiment_manifest(
    manifest: Any,
    result_payload: Any,
) -> bool:
    if (
        type(manifest) is not dict
        or not _is_exact_native_json(manifest)
        or set(manifest) != _MANIFEST_FIELDS
    ):
        return False
    if type(result_payload) is not dict or not _is_exact_native_json(result_payload):
        return False
    if manifest.get("result_hash") != canonical_payload_hash(result_payload):
        return False
    expected_manifest_hash = canonical_payload_hash({
        key: value for key, value in manifest.items() if key != "manifest_hash"
    })
    if not expected_manifest_hash or manifest.get("manifest_hash") != expected_manifest_hash:
        return False
    blockers = _reproducibility_blockers(manifest)
    if manifest.get("blockers") != blockers:
        return False
    expected_status = "PASS" if not blockers else "BLOCK"
    expected_classification = (
        "REPRODUCIBILITY_COMPLETE"
        if not blockers
        else "REPRODUCIBILITY_INCOMPLETE"
    )
    if (
        manifest.get("status") != expected_status
        or manifest.get("classification") != expected_classification
    ):
        return False
    ranking_blockers = _ranking_blockers(manifest, blockers)
    return manifest.get("ranking_gate") == {
        "status": "PASS" if not ranking_blockers else "BLOCK",
        "input_allowed": not ranking_blockers,
        "blockers": ranking_blockers,
    }


__all__ = [
    "SCHEMA_VERSION",
    "build_local_experiment_context",
    "build_reproducible_experiment_manifest",
    "canonical_payload_hash",
    "verify_reproducible_experiment_manifest",
]
