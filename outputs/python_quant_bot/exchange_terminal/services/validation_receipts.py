from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Iterable
from uuid import uuid4


VALIDATION_RECEIPT_SCHEMA = "hakimi.verification-receipt/v1"
VALIDATION_RECEIPT_TYPE = "local.readonly-verification"
VALIDATION_POLICY_VERSION = "hakimi-validation-policy-v1"
VALIDATION_PREDICATE_TYPE = "https://hakimi.local/verification-receipt/v1"
IN_TOTO_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
CONTROLLED_INPUT_MANIFEST_SCHEMA = "hakimi-controlled-engineering-inputs-v1"

_SOURCE_SUFFIXES = {".py", ".js", ".css", ".html"}
_ELECTRON_SUFFIXES = {".js", ".html", ".json"}
_ELECTRON_JSON_ALLOWLIST = {"package.json", "package-lock.json"}
_PROTECTED_DATA_SUFFIXES = {
    ".db",
    ".db-shm",
    ".db-wal",
    ".log",
    ".sqlite",
    ".sqlite3",
    ".sqlite3-shm",
    ".sqlite3-wal",
}
_EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "backups",
    "cache",
    "caches",
    "logs",
    "node_modules",
    "screenshots",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNITTEST_COUNT_RE = re.compile(r"\bRan\s+(\d+)\s+tests?\b", re.IGNORECASE)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_descriptor(value: bytes) -> dict[str, Any]:
    return {
        "digest": {"sha256": hashlib.sha256(value).hexdigest()},
        "size_bytes": len(value),
    }


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    name = relative.name.lower()
    suffix = path.suffix.lower()
    directory_parts = relative.parts[:-1]
    if (
        name.startswith(".env")
        or name == "config.local.json"
        or suffix in _PROTECTED_DATA_SUFFIXES
        or (
            suffix == ".json"
            and name.startswith(("runtime", "cache", "log", "screenshot"))
        )
    ):
        return True
    return any(
        part.lower() in _EXCLUDED_DIRECTORY_NAMES
        or part.lower().startswith("runtime")
        for part in directory_parts
    )


def controlled_engineering_files(project_root: Path) -> list[Path]:
    root = project_root.resolve()
    workspace_root = root.parent.parent
    electron_root = root.parent / "hakimi_trade_electron"
    candidates: set[Path] = set()

    for path in root.glob("*.py"):
        if path.is_file():
            candidates.add(path.resolve())
    requirements = root / "requirements.txt"
    if requirements.is_file():
        candidates.add(requirements.resolve())

    for source_root, suffixes in (
        (root / "exchange_terminal", _SOURCE_SUFFIXES),
        (root / "tests", {".py"}),
        (electron_root, _ELECTRON_SUFFIXES),
    ):
        if not source_root.is_dir():
            continue
        for path in source_root.rglob("*"):
            suffix = path.suffix.lower()
            if (
                suffix not in suffixes
                or _is_excluded(path, workspace_root)
                or (
                    source_root == electron_root
                    and suffix == ".json"
                    and path.name.lower() not in _ELECTRON_JSON_ALLOWLIST
                )
            ):
                continue
            if path.is_file():
                candidates.add(path.resolve())

    return sorted(
        candidates,
        key=lambda path: path.relative_to(workspace_root).as_posix().casefold(),
    )


def build_controlled_input_manifest(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    workspace_root = root.parent.parent
    rows: list[dict[str, Any]] = []
    total_size = 0
    for path in controlled_engineering_files(root):
        relative = path.relative_to(workspace_root).as_posix()
        size = path.stat().st_size
        total_size += size
        rows.append({
            "path": relative,
            "size_bytes": size,
            "sha256": file_sha256(path),
        })
    manifest_payload = {
        "schema": CONTROLLED_INPUT_MANIFEST_SCHEMA,
        "workspace_root": str(workspace_root),
        "files": rows,
    }
    manifest_bytes = canonical_json_bytes(manifest_payload)
    return {
        **manifest_payload,
        "file_count": len(rows),
        "total_size_bytes": total_size,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_size_bytes": len(manifest_bytes),
    }


def manifest_subject(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "controlled-source-test-dependency-manifest",
        "digest": {"sha256": str(manifest.get("manifest_sha256") or "")},
        "size_bytes": int(manifest.get("manifest_size_bytes") or 0),
        "file_count": int(manifest.get("file_count") or 0),
        "total_input_size_bytes": int(manifest.get("total_size_bytes") or 0),
    }


def _python_dependency_fingerprint() -> dict[str, Any]:
    versions: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = str(distribution.metadata.get("Name") or "").strip().lower()
        if name:
            versions[name] = str(distribution.version or "")
    rows = [
        {"name": name, "version": versions[name]}
        for name in sorted(versions)
    ]
    return {
        "distribution_count": len(rows),
        "sha256": canonical_hash(rows),
    }


def _executable_version(executable: str, argument: str) -> str:
    if not executable:
        return ""
    try:
        completed = subprocess.run(
            [executable, argument],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return str(completed.stdout or completed.stderr or "").strip()


def build_toolchain_fingerprint(*, node_executable: str = "", npm_executable: str = "") -> dict[str, Any]:
    python_dependencies = _python_dependency_fingerprint()
    toolchain = {
        "python": {
            "executable": str(Path(sys.executable).resolve()),
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "dependency_fingerprint": python_dependencies,
        },
        "node": {
            "executable": str(Path(node_executable).resolve()) if node_executable else "",
            "version": _executable_version(node_executable, "--version"),
        },
        "npm": {
            "executable": str(Path(npm_executable).resolve()) if npm_executable else "",
            "version": _executable_version(npm_executable, "--version"),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }
    toolchain["sha256"] = canonical_hash(toolchain)
    return toolchain


def safe_environment_policy() -> dict[str, Any]:
    return {
        "runtime_mode": "READ_ONLY",
        "test_mode": True,
        "local_ai_env_loading": False,
        "credential_inheritance": "NONE_STRICT_ALLOWLIST",
        "host_environment_allowlist": ["COMSPEC", "SYSTEMROOT", "WINDIR"],
        "behavior_environment": "FIXED_BY_RUNNER",
        "fixed_directory_variables": [
            "APPDATA",
            "HAKIMI_RUNTIME_DIR",
            "LOCALAPPDATA",
            "PYTHONPYCACHEPREFIX",
            "TEMP",
            "TMP",
        ],
        "runtime_dir": "<TEMP_RUNTIME>",
        "python_bytecode": "ISOLATED_OR_DISABLED",
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_validation_action(
    *,
    check_id: str,
    argv: Iterable[str],
    cwd: Path,
    manifest: dict[str, Any],
    toolchain: dict[str, Any],
    result_contract: str,
    minimum_tests: int = 0,
    namespace: str = "hakimi-lean-validation",
    full_regression_included: bool = False,
    extra_inputs: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    subject = manifest_subject(manifest)
    payload = {
        "check_id": str(check_id or "").strip(),
        "namespace": str(namespace or "").strip(),
        "argv": [str(part) for part in argv],
        "cwd": str(cwd.resolve()),
        "environment_policy": safe_environment_policy(),
        "result_contract": str(result_contract or "").strip(),
        "minimum_tests": int(minimum_tests),
        "full_regression_included": bool(full_regression_included),
        "verifier": {
            "id": "hakimi-local-verifier",
            "policy_version": VALIDATION_POLICY_VERSION,
            "toolchain": toolchain,
        },
        "inputs": [subject, *[dict(item) for item in extra_inputs]],
    }
    encoded = canonical_json_bytes(payload)
    return {
        **payload,
        "digest": {"sha256": hashlib.sha256(encoded).hexdigest()},
        "size_bytes": len(encoded),
    }


def result_from_process(
    *,
    action: dict[str, Any],
    exit_code: int,
    stdout: str,
    stderr: str,
    duration_sec: float,
) -> dict[str, Any]:
    combined = f"{stdout}\n{stderr}"
    matches = list(_UNITTEST_COUNT_RE.finditer(combined))
    match = matches[-1] if matches else None
    result: dict[str, Any] = {
        "status": "PASS" if type(exit_code) is int and exit_code == 0 else "FAIL",
        "exit_code": int(exit_code),
        "duration_sec": round(float(duration_sec), 3),
        "stdout": bytes_descriptor(stdout.encode("utf-8")),
        "stderr": bytes_descriptor(stderr.encode("utf-8")),
        "safety": {
            "mode": "READ_ONLY",
            "runtime_mutations_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    if str(action.get("result_contract") or "") == "unittest":
        result.update({
            "tests_run": int(match.group(1)) if match else 0,
            "failures": 0 if exit_code == 0 else None,
            "errors": 0 if exit_code == 0 else None,
        })
    return result


def create_validation_receipt(
    *,
    action: dict[str, Any],
    result: dict[str, Any],
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    subject = [dict(item) for item in action.get("inputs", []) if isinstance(item, dict)]
    receipt: dict[str, Any] = {
        "_type": IN_TOTO_STATEMENT_TYPE,
        "subject": subject,
        "predicateType": VALIDATION_PREDICATE_TYPE,
        "predicate": {
            "schema": VALIDATION_RECEIPT_SCHEMA,
            "receipt_type": VALIDATION_RECEIPT_TYPE,
            "scope": {
                "namespace": str(action.get("namespace") or ""),
                "policy_version": VALIDATION_POLICY_VERSION,
                "targeted": action.get("full_regression_included") is not True,
                "full_regression_included": action.get("full_regression_included") is True,
            },
            "action": dict(action),
            "run": {
                "invocation_id": str(uuid4()),
                "started_at": str(started_at or ""),
                "finished_at": str(finished_at or ""),
                "execution": "EXECUTED",
            },
            "result": dict(result),
        },
    }
    unsealed = canonical_json_bytes(receipt)
    receipt["seal"] = {
        "algorithm": "sha256",
        "hash": hashlib.sha256(unsealed).hexdigest(),
        "payload_size_bytes": len(unsealed),
    }
    return receipt


def _valid_sha256(value: Any) -> bool:
    return bool(_SHA256_RE.fullmatch(str(value or "").strip().lower()))


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _valid_bytes_descriptor(value: Any) -> bool:
    descriptor = dict(value) if isinstance(value, dict) else {}
    digest = dict(descriptor.get("digest")) if isinstance(descriptor.get("digest"), dict) else {}
    return (
        _valid_sha256(digest.get("sha256"))
        and type(descriptor.get("size_bytes")) is int
        and descriptor.get("size_bytes") >= 0
    )


def verify_validation_receipt(
    value: Any,
    *,
    expected_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = dict(value) if isinstance(value, dict) else {}
    blockers: list[str] = []
    predicate = dict(receipt.get("predicate")) if isinstance(receipt.get("predicate"), dict) else {}
    action = dict(predicate.get("action")) if isinstance(predicate.get("action"), dict) else {}
    result = dict(predicate.get("result")) if isinstance(predicate.get("result"), dict) else {}
    run = dict(predicate.get("run")) if isinstance(predicate.get("run"), dict) else {}
    seal = dict(receipt.get("seal")) if isinstance(receipt.get("seal"), dict) else {}

    if receipt.get("_type") != IN_TOTO_STATEMENT_TYPE:
        blockers.append("validation_receipt_statement_type_invalid")
    if receipt.get("predicateType") != VALIDATION_PREDICATE_TYPE:
        blockers.append("validation_receipt_predicate_type_invalid")
    if predicate.get("schema") != VALIDATION_RECEIPT_SCHEMA:
        blockers.append("validation_receipt_schema_invalid")
    if predicate.get("receipt_type") != VALIDATION_RECEIPT_TYPE:
        blockers.append("validation_receipt_type_invalid")

    argv = action.get("argv") if isinstance(action.get("argv"), list) else []
    verifier = dict(action.get("verifier")) if isinstance(action.get("verifier"), dict) else {}
    toolchain = dict(verifier.get("toolchain")) if isinstance(verifier.get("toolchain"), dict) else {}
    toolchain_clean = dict(toolchain)
    toolchain_hash = str(toolchain_clean.pop("sha256", "") or "").lower()
    if (
        not str(action.get("check_id") or "").strip()
        or not str(action.get("namespace") or "").strip()
        or not argv
        or any(not isinstance(part, str) or not part for part in argv)
        or not Path(str(action.get("cwd") or "")).is_absolute()
    ):
        blockers.append("validation_action_identity_invalid")
    if action.get("environment_policy") != safe_environment_policy():
        blockers.append("validation_environment_policy_invalid")
    if (
        verifier.get("id") != "hakimi-local-verifier"
        or verifier.get("policy_version") != VALIDATION_POLICY_VERSION
        or not _valid_sha256(toolchain_hash)
        or canonical_hash(toolchain_clean) != toolchain_hash
    ):
        blockers.append("validation_toolchain_identity_invalid")

    action_clean = dict(action)
    action_digest = str(dict(action_clean.pop("digest", {})).get("sha256") or "").lower()
    action_size = action_clean.pop("size_bytes", None)
    action_bytes = canonical_json_bytes(action_clean)
    if not _valid_sha256(action_digest) or hashlib.sha256(action_bytes).hexdigest() != action_digest:
        blockers.append("validation_action_digest_invalid")
    if type(action_size) is not int or action_size != len(action_bytes):
        blockers.append("validation_action_size_invalid")
    if expected_action is not None and canonical_json_bytes(action) != canonical_json_bytes(expected_action):
        blockers.append("validation_action_current_context_mismatch")

    subjects = receipt.get("subject") if isinstance(receipt.get("subject"), list) else []
    if subjects != action.get("inputs") or not subjects:
        blockers.append("validation_subject_mismatch")
    for subject in subjects:
        clean = dict(subject) if isinstance(subject, dict) else {}
        digest = str(dict(clean.get("digest", {})).get("sha256") or "").lower()
        if (
            not clean.get("name")
            or not _valid_sha256(digest)
            or type(clean.get("size_bytes")) is not int
            or clean.get("size_bytes") < 0
        ):
            blockers.append("validation_subject_identity_invalid")
            break

    contract = str(action.get("result_contract") or "")
    if result.get("status") != "PASS" or type(result.get("exit_code")) is not int or result.get("exit_code") != 0:
        blockers.append("validation_result_not_pass")
    minimum_tests_value = action.get("minimum_tests")
    if type(minimum_tests_value) is not int or minimum_tests_value < 0:
        blockers.append("validation_minimum_tests_invalid")
        minimum_tests = 0
    else:
        minimum_tests = minimum_tests_value
    if contract == "unittest":
        if (
            type(result.get("tests_run")) is not int
            or result.get("tests_run") < max(minimum_tests, 1)
            or result.get("failures") != 0
            or result.get("errors") != 0
        ):
            blockers.append("validation_unittest_result_invalid")
    elif contract != "exit-zero":
        blockers.append("validation_result_contract_invalid")
    if (
        type(result.get("duration_sec")) not in {int, float}
        or isinstance(result.get("duration_sec"), bool)
        or result.get("duration_sec") < 0
        or not _valid_bytes_descriptor(result.get("stdout"))
        or not _valid_bytes_descriptor(result.get("stderr"))
    ):
        blockers.append("validation_process_result_descriptor_invalid")

    safety = dict(result.get("safety")) if isinstance(result.get("safety"), dict) else {}
    if (
        safety.get("mode") != "READ_ONLY"
        or safety.get("runtime_mutations_allowed") is not False
        or safety.get("paper_authorized") is not False
        or safety.get("live_order_allowed") is not False
    ):
        blockers.append("validation_receipt_authority_invalid")
    if run.get("execution") != "EXECUTED" or not run.get("invocation_id"):
        blockers.append("validation_run_identity_invalid")
    started = _parse_time(run.get("started_at"))
    finished = _parse_time(run.get("finished_at"))
    if started is None or finished is None or finished < started:
        blockers.append("validation_run_time_invalid")

    unsealed = dict(receipt)
    unsealed.pop("seal", None)
    unsealed_bytes = canonical_json_bytes(unsealed)
    seal_hash = str(seal.get("hash") or "").lower()
    if (
        seal.get("algorithm") != "sha256"
        or not _valid_sha256(seal_hash)
        or hashlib.sha256(unsealed_bytes).hexdigest() != seal_hash
        or seal.get("payload_size_bytes") != len(unsealed_bytes)
    ):
        blockers.append("validation_receipt_seal_invalid")

    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "check_id": str(action.get("check_id") or ""),
        "action_digest": action_digest,
        "receipt_hash": seal_hash,
        "tests_run": int(result.get("tests_run") or 0),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def receipt_path(cache_dir: Path, action: dict[str, Any]) -> Path:
    check_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(action.get("check_id") or "check")).strip("-")
    digest = str(dict(action.get("digest", {})).get("sha256") or "")
    return cache_dir.resolve() / f"{check_id}-{digest}.receipt.json"


def load_validation_receipt(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("validation receipt must be a JSON object")
    return payload


def write_validation_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def prune_receipts(cache_dir: Path, check_id: str, *, keep: int = 8) -> None:
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(check_id or "check")).strip("-")
    rows = sorted(
        cache_dir.glob(f"{safe_id}-*.receipt.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    for path in rows[max(int(keep), 1):]:
        path.unlink(missing_ok=True)


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
