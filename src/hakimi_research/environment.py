"""Read-only runtime evidence. Hashing a lock never proves an environment match."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

from hakimi_research.source_identity import BUILD_IDENTITY_FILENAME, package_content_identity
from hakimi_research.source_layout import CANONICAL_DEPENDENCY_LOCK, PACKAGE_ROOT, REPOSITORY_ROOT


_PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)")


def git_state(root: str | Path | None) -> dict:
    state = {"commit": "", "status": "UNKNOWN", "query_errors": []}
    if root is None:
        state["query_errors"] = ["not_a_source_checkout"]
        return state
    results = {}
    for name, arguments in (
        ("commit", ["rev-parse", "HEAD"]),
        ("worktree", ["status", "--porcelain", "--untracked-files=all"]),
    ):
        try:
            completed = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=False, timeout=3)
            if completed.returncode == 0:
                results[name] = completed.stdout.strip()
            else:
                state["query_errors"].append(f"{name}_query_failed")
        except (OSError, subprocess.SubprocessError, UnicodeError):
            state["query_errors"].append(f"{name}_query_failed")
    commit = results.get("commit", "")
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        state["commit"] = commit
    elif "commit_query_failed" not in state["query_errors"]:
        state["query_errors"].append("commit_invalid")
    if state["commit"] and "worktree" in results:
        state["status"] = "DIRTY" if results["worktree"] else "CLEAN"
    return state


def verify_dependency_environment(lock_path: str | Path) -> dict:
    result = {
        "status": "UNKNOWN", "lock_sha256": "", "lock_name": Path(lock_path).name,
        "lock_fully_pinned": False, "packages": {}, "missing": [], "mismatched": [],
        "errors": [], "verification_scope": "installed_distribution_versions_against_lock",
        "python_version": platform.python_version(), "python_supported": sys.version_info >= (3, 11),
    }
    try:
        raw = Path(lock_path).read_bytes()
        result["lock_sha256"] = hashlib.sha256(raw).hexdigest()
        lines = raw.decode("utf-8").splitlines()
    except (OSError, UnicodeError):
        result["errors"] = ["dependency_lock_unreadable"]
        return result
    expected = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _PIN.fullmatch(line)
        if not match:
            result["errors"].append("dependency_lock_not_exact_pins")
            continue
        name, version = match.groups()
        name = re.sub(r"[-_.]+", "-", name).lower()
        if name in expected:
            result["errors"].append("dependency_lock_duplicate_package")
        expected[name] = version
    if result["errors"] or not expected:
        result["status"] = "INVALID_LOCK"
        return result
    result["lock_fully_pinned"] = True
    for name, required in sorted(expected.items()):
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
            result["missing"].append(name)
        except (OSError, ValueError):
            installed = None
            result["errors"].append(f"package_metadata_unreadable:{name}")
        if name not in result["missing"] and (type(installed) is not str or not installed.strip()):
            error = f"package_metadata_unreadable:{name}"
            if error not in result["errors"]:
                result["errors"].append(error)
        result["packages"][name] = {"required": required, "installed": installed}
        if type(installed) is str and installed != required:
            result["mismatched"].append(name)
    if result["errors"]:
        result["status"] = "UNKNOWN"
    elif result["missing"] or result["mismatched"] or not result["python_supported"]:
        result["status"] = "MISMATCH"
    else:
        result["status"] = "VERIFIED"
    return result


def build_runtime_provenance(
    project_root: str | Path | None = None,
    *,
    package_root: str | Path | None = None,
    dependency_lock: str | Path | None = None,
) -> dict:
    source_root = Path(package_root) if package_root is not None else PACKAGE_ROOT
    checkout = project_root if project_root is not None else REPOSITORY_ROOT
    environment = verify_dependency_environment(dependency_lock or CANONICAL_DEPENDENCY_LOCK)
    source = {"status": "UNKNOWN", "content_sha256": "", "git": git_state(checkout)}
    try:
        identity = package_content_identity(source_root)
        source["content_sha256"] = identity["content_sha256"]
        source["file_hashes"] = identity["file_hashes"]
        source_is_checkout = (REPOSITORY_ROOT is not None and source_root.resolve() ==
                              (Path(REPOSITORY_ROOT) / "src" / "hakimi_research").resolve())
        source["status"] = "CONTENT_HASHED" if source_is_checkout else "BUILD_MISSING"
        build_path = source_root / BUILD_IDENTITY_FILENAME
        if build_path.is_file():
            build = json.loads(build_path.read_text(encoding="utf-8"))
            valid_build = (
                type(build) is dict and build.get("schema_version") == "research-build-source-v1"
                and build.get("content_sha256") == identity["content_sha256"]
                and build.get("file_hashes") == identity["file_hashes"]
            )
            source["status"] = "BUILD_VERIFIED" if valid_build else "BUILD_MISMATCH"
            source["build_receipt"] = build
        elif not source_is_checkout:
            source["error"] = "build_receipt_missing_for_installed_package"
    except (OSError, ValueError, TypeError):
        source["status"] = "UNKNOWN"
        source["error"] = "source_identity_unreadable"
    receipt = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "machine": platform.node(), "platform": platform.platform(),
        "python_executable": sys.executable, "package_location": str(source_root.resolve()),
    }
    return {
        "schema_version": "research-runtime-evidence-v1",
        "input_integrity": {"status": "NOT_CHECKED"},
        "dependency_lock": {
            "sha256": environment["lock_sha256"], "name": environment["lock_name"],
            "fully_pinned": environment["lock_fully_pinned"],
        },
        "environment_verified": environment,
        "source_identity": source,
        "replay_verified": {"status": "NOT_RUN"},
        "statistical_status": {"status": "NOT_ASSESSED"},
        "execution_permission": {
            "research_only": True, "paper_authorized": False,
            "live_order_allowed": False, "order_entry_allowed": False,
        },
        "machine_receipt": receipt,
    }
