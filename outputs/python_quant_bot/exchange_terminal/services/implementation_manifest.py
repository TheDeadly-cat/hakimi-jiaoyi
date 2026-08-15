from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import sys
from typing import Any, Callable, Iterable


IMPLEMENTATION_MANIFEST_SCHEMA_VERSION = "implementation-manifest-v2"
IMPLEMENTATION_VERIFICATION_POLICY = "FULL_CLOSURE_AT_BUILD_EXACT_FILES_AND_RUNTIME_AT_VERIFY"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_within(path: Path, roots: Iterable[Path]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _source_roots(paths: list[Path]) -> list[Path]:
    common = Path(os.path.commonpath([str(path) for path in paths])).resolve()
    if common in paths or common.is_file():
        common = common.parent
    roots = {common}
    for path in paths:
        package_root = path.parent
        while (package_root / "__init__.py").is_file():
            package_root = package_root.parent
        roots.add(package_root.resolve())
    return sorted(roots, key=lambda item: (len(item.parts), str(item)))


def _package_initializers(path: Path, roots: list[Path]) -> set[Path]:
    initializers: set[Path] = set()
    for root in roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        for index in range(1, len(relative.parts)):
            candidate = root.joinpath(*relative.parts[:index], "__init__.py").resolve()
            if candidate.is_file():
                initializers.add(candidate)
    return initializers


def _module_paths(base: Path, roots: list[Path], *, excluded_path: Path | None = None) -> set[Path]:
    candidates = {base.with_suffix(".py").resolve(), (base / "__init__.py").resolve()}
    existing = {
        path
        for path in candidates
        if path.is_file() and _is_within(path, roots) and path != excluded_path
    }
    for path in list(existing):
        existing.update(_package_initializers(path, roots))
    return existing


def _absolute_module_paths(module: str, *, source: Path, roots: list[Path]) -> set[Path]:
    if not module:
        return set()
    parts = module.split(".")
    source_ancestors = [
        parent.resolve()
        for parent in source.parents
        if _is_within(parent.resolve(), roots)
    ]
    search_roots = list(dict.fromkeys([*roots, *source_ancestors]))
    found: set[Path] = set()
    for root in search_roots:
        found.update(_module_paths(root.joinpath(*parts), roots, excluded_path=source.resolve()))
    return found


def _relative_module_paths(module: str, level: int, *, source: Path, roots: list[Path]) -> set[Path]:
    base = source.parent
    for _ in range(max(int(level) - 1, 0)):
        base = base.parent
    if module:
        base = base.joinpath(*module.split("."))
    return _module_paths(base, roots)


def _source_imports(path: Path, roots: list[Path]) -> tuple[set[Path], set[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError(f"unable to parse implementation source: {path}") from exc
    local: set[Path] = set()
    external: set[str] = set()
    standard_library = set(getattr(sys, "stdlib_module_names", set()))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                matches = _absolute_module_paths(alias.name, source=path, roots=roots)
                local.update(matches)
                top_level = alias.name.split(".", 1)[0]
                if not matches and top_level not in standard_library:
                    external.add(top_level)
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "")
            if int(node.level or 0) > 0:
                matches = _relative_module_paths(module, int(node.level), source=path, roots=roots)
                local.update(matches)
                for alias in node.names:
                    if alias.name != "*":
                        child = ".".join(part for part in (module, alias.name) if part)
                        local.update(_relative_module_paths(child, int(node.level), source=path, roots=roots))
                continue
            matches = _absolute_module_paths(module, source=path, roots=roots)
            local.update(matches)
            for alias in node.names:
                if alias.name != "*":
                    child = ".".join(part for part in (module, alias.name) if part)
                    local.update(_absolute_module_paths(child, source=path, roots=roots))
            top_level = module.split(".", 1)[0]
            if module and not matches and top_level not in standard_library and top_level != "__future__":
                external.add(top_level)
    return local, external


def _source_closure(
    source_files: list[Path | str],
    *,
    source_path_allowed: Callable[[Path], bool] | None = None,
) -> tuple[list[Path], list[str]]:
    explicit = [Path(raw_path).resolve() for raw_path in source_files]
    if not explicit:
        return [], []
    roots = _source_roots(explicit)
    pending = list(dict.fromkeys(explicit))
    for path in explicit:
        pending.extend(_package_initializers(path, roots))
    visited: set[Path] = set()
    external: set[str] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        if source_path_allowed is not None:
            try:
                allowed = source_path_allowed(path) is True
            except Exception:
                allowed = False
            if not allowed:
                raise PermissionError("implementation source path is outside the verification policy")
        if not path.is_file():
            raise FileNotFoundError(path)
        if not _is_within(path, roots):
            raise ValueError(f"implementation source escapes declared roots: {path}")
        visited.add(path)
        if path.suffix.lower() != ".py":
            continue
        dependencies, imported_external = _source_imports(path, roots)
        external.update(imported_external)
        pending.extend(dependencies - visited)
    return sorted(visited, key=str), sorted(external)


def _normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", str(name or "")).lower()


def _requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", str(requirement or ""))
    return str(match.group(1) if match else "")


def _unmanaged_module_record(module: str) -> dict[str, str]:
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ModuleNotFoundError, ValueError):
        spec = None
    origin = str(getattr(spec, "origin", "") or "") if spec else ""
    origin_hash = ""
    if origin and origin not in {"built-in", "frozen"}:
        try:
            origin_hash = hashlib.sha256(Path(origin).read_bytes()).hexdigest()
        except OSError:
            origin_hash = ""
    return {
        "module": module,
        "status": "IMPORTABLE_WITHOUT_DISTRIBUTION" if spec else "NOT_INSTALLED",
        "origin": origin,
        "origin_sha256": origin_hash,
    }


def _runtime_base(external_modules: list[str]) -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "sqlite_version": sqlite3.sqlite_version,
        "external_modules": list(external_modules),
    }


def _runtime_manifest(external_modules: list[str]) -> dict[str, Any]:
    package_map = importlib.metadata.packages_distributions()
    pending = [distribution for module in external_modules for distribution in package_map.get(module, [])]
    distributions: dict[str, dict[str, str]] = {}
    while pending:
        requested = pending.pop(0)
        normalized_requested = _normalize_distribution_name(requested)
        if normalized_requested in distributions:
            continue
        try:
            distribution = importlib.metadata.distribution(requested)
        except importlib.metadata.PackageNotFoundError:
            continue
        name = str(distribution.metadata.get("Name") or requested)
        normalized = _normalize_distribution_name(name)
        if normalized in distributions:
            continue
        distributions[normalized] = {"name": name, "version": str(distribution.version or "")}
        for requirement in distribution.requires or []:
            dependency = _requirement_name(requirement)
            if not dependency:
                continue
            try:
                importlib.metadata.version(dependency)
            except importlib.metadata.PackageNotFoundError:
                continue
            pending.append(dependency)

    unmanaged = [
        _unmanaged_module_record(module)
        for module in external_modules
        if not package_map.get(module)
    ]
    return {
        **_runtime_base(external_modules),
        "distributions": [distributions[key] for key in sorted(distributions)],
        "unmanaged_modules": unmanaged,
    }


def _runtime_manifest_from_expected(expected: dict[str, Any]) -> dict[str, Any]:
    external_raw = expected.get("external_modules")
    external_modules = [str(item) for item in external_raw] if isinstance(external_raw, list) else []
    distributions: list[dict[str, str]] = []
    distribution_raw = expected.get("distributions")
    for item in distribution_raw if isinstance(distribution_raw, list) else []:
        row = item if isinstance(item, dict) else {}
        name = str(row.get("name") or "")
        try:
            version = importlib.metadata.version(name) if name else ""
        except importlib.metadata.PackageNotFoundError:
            version = ""
        distributions.append({"name": name, "version": str(version or "")})
    unmanaged_raw = expected.get("unmanaged_modules")
    unmanaged = [
        _unmanaged_module_record(str(item.get("module") or ""))
        for item in unmanaged_raw if isinstance(item, dict)
    ] if isinstance(unmanaged_raw, list) else []
    return {
        **_runtime_base(external_modules),
        "distributions": distributions,
        "unmanaged_modules": unmanaged,
    }


def build_implementation_manifest(
    source_files: list[Path | str],
    *,
    source_path_allowed: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    paths, external_modules = _source_closure(
        source_files,
        source_path_allowed=source_path_allowed,
    )
    files: list[dict[str, Any]] = []
    for path in paths:
        content = path.read_bytes()
        files.append({
            "path": str(path),
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        })
    core = {
        "schema_version": IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
        "verification_policy": IMPLEMENTATION_VERIFICATION_POLICY,
        "files": files,
        "runtime": _runtime_manifest(external_modules),
    }
    return {**core, "fingerprint": _canonical_hash(core)}


def verify_embedded_implementation_manifest(manifest: Any) -> dict[str, Any]:
    """Validate a frozen manifest without comparing it with the current tree."""

    blockers: list[str] = []
    payload = manifest if isinstance(manifest, dict) else {}
    if not isinstance(manifest, dict):
        blockers.append("implementation_manifest_type_invalid")
    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    if payload.get("schema_version") != IMPLEMENTATION_MANIFEST_SCHEMA_VERSION:
        blockers.append("implementation_manifest_schema_invalid")
    if payload.get("verification_policy") != IMPLEMENTATION_VERIFICATION_POLICY:
        blockers.append("implementation_manifest_verification_policy_invalid")
    if not files:
        blockers.append("implementation_manifest_sources_missing")
    seen_paths: set[str] = set()
    for index, item in enumerate(files):
        row = item if isinstance(item, dict) else {}
        path = str(row.get("path") or "").strip()
        size = row.get("size")
        digest = str(row.get("sha256") or "")
        if not path or path in seen_paths:
            blockers.append(f"implementation_manifest_source_path_invalid:{index}")
        seen_paths.add(path)
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            blockers.append(f"implementation_manifest_source_hash_invalid:{index}")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            blockers.append(f"implementation_manifest_source_size_invalid:{index}")
    if not runtime:
        blockers.append("implementation_manifest_runtime_missing")
    else:
        for field in (
            "python_implementation",
            "python_version",
            "platform_system",
            "platform_machine",
            "sqlite_version",
        ):
            if not isinstance(runtime.get(field), str):
                blockers.append(f"implementation_manifest_runtime_field_invalid:{field}")
        external_modules = runtime.get("external_modules")
        if not isinstance(external_modules, list) or not all(
            isinstance(item, str) and item for item in external_modules
        ):
            blockers.append("implementation_manifest_runtime_external_modules_invalid")
        distributions = runtime.get("distributions")
        if not isinstance(distributions, list) or not all(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and bool(item.get("name"))
            and isinstance(item.get("version"), str)
            for item in distributions
        ):
            blockers.append("implementation_manifest_runtime_distributions_invalid")
        unmanaged = runtime.get("unmanaged_modules")
        if not isinstance(unmanaged, list) or not all(
            isinstance(item, dict)
            and all(isinstance(item.get(field), str) for field in (
                "module", "status", "origin", "origin_sha256"
            ))
            and bool(item.get("module"))
            for item in unmanaged
        ):
            blockers.append("implementation_manifest_runtime_unmanaged_modules_invalid")
    core = {
        "schema_version": payload.get("schema_version"),
        "verification_policy": payload.get("verification_policy"),
        "files": files,
        "runtime": runtime,
    }
    fingerprint = str(payload.get("fingerprint") or "")
    if (
        len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
        or _canonical_hash(core) != fingerprint
    ):
        blockers.append("implementation_manifest_fingerprint_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "fingerprint": fingerprint,
        "source_count": len(files),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_implementation_manifest(
    manifest: dict[str, Any],
    *,
    source_path_allowed: Callable[[Path], bool] | None = None,
    source_entrypoints: list[Path | str] | None = None,
) -> dict[str, Any]:
    expected = dict(manifest) if isinstance(manifest, dict) else {}
    embedded_verification = verify_embedded_implementation_manifest(manifest)
    expected_files = list(expected.get("files") or []) if isinstance(expected.get("files"), list) else []
    expected_runtime = dict(expected.get("runtime") or {}) if isinstance(expected.get("runtime"), dict) else {}
    expected_fingerprint = str(expected.get("fingerprint") or "")
    blockers: list[str] = list(embedded_verification.get("blockers") or [])
    current_files: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    path_contract_blocked = False
    for index, item in enumerate(expected_files):
        if not isinstance(item, dict):
            blockers.append(f"implementation_manifest_source_type_invalid:{index}")
            path_contract_blocked = True
            continue
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            blockers.append(f"implementation_manifest_source_path_invalid:{index}")
            path_contract_blocked = True
            continue
        path = Path(raw_path).resolve()
        if source_path_allowed is not None:
            try:
                allowed = source_path_allowed(path) is True
            except Exception:
                allowed = False
            if not allowed:
                blockers.append(f"implementation_source_path_not_allowed:{index}")
                path_contract_blocked = True
                continue
        path_key = str(path)
        if path_key in seen_paths:
            blockers.append(f"implementation_source_duplicate:{path}")
            path_contract_blocked = True
            continue
        seen_paths.add(path_key)
        if source_entrypoints is not None:
            continue
        try:
            content = path.read_bytes()
        except OSError:
            blockers.append(f"implementation_source_unavailable:{path}")
            continue
        row = {
            "path": path_key,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        }
        current_files.append(row)
        if row != item:
            blockers.append(f"implementation_source_changed:{path}")

    if source_entrypoints is not None:
        entrypoints = [Path(item).resolve() for item in source_entrypoints]
        for index, entrypoint in enumerate(entrypoints):
            if str(entrypoint) not in seen_paths:
                blockers.append(f"implementation_manifest_entrypoint_missing:{index}")
                path_contract_blocked = True
        if not path_contract_blocked:
            try:
                current_manifest = build_implementation_manifest(
                    entrypoints,
                    source_path_allowed=source_path_allowed,
                )
            except PermissionError:
                blockers.append("implementation_source_closure_path_not_allowed")
                current_manifest = {}
            except (FileNotFoundError, OSError, ValueError):
                blockers.append("implementation_source_closure_unavailable")
                current_manifest = {}
            current_files = list(current_manifest.get("files") or [])
            current_runtime = dict(current_manifest.get("runtime") or {})
            current_fingerprint = str(current_manifest.get("fingerprint") or "")
            if current_manifest and current_files != expected_files:
                blockers.append("implementation_source_closure_changed")
        else:
            current_runtime = {}
            current_fingerprint = ""
    else:
        current_runtime = _runtime_manifest_from_expected(expected_runtime)
        current_core = {
            "schema_version": IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
            "verification_policy": IMPLEMENTATION_VERIFICATION_POLICY,
            "files": current_files,
            "runtime": current_runtime,
        }
        current_fingerprint = _canonical_hash(current_core)
    if current_runtime != expected_runtime:
        blockers.append("implementation_runtime_changed")
    if current_fingerprint != expected_fingerprint:
        blockers.append("implementation_fingerprint_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "expected_fingerprint": expected_fingerprint,
        "current_fingerprint": current_fingerprint,
        "source_count": len(current_files),
        "runtime": current_runtime,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "IMPLEMENTATION_MANIFEST_SCHEMA_VERSION",
    "IMPLEMENTATION_VERIFICATION_POLICY",
    "build_implementation_manifest",
    "verify_embedded_implementation_manifest",
    "verify_implementation_manifest",
]
