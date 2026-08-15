from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable


RUNTIME_BUILD_SCHEMA_VERSION = "hakimi-runtime-build-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def build_runtime_source_manifest(
    project_root: Path | str,
    source_roots: Iterable[Path | str],
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    blockers: list[str] = []
    files: list[dict[str, Any]] = []
    seen: set[Path] = set()

    for raw_root in source_roots:
        source_root = Path(raw_root).resolve()
        if not _is_within(source_root, project):
            blockers.append(f"runtime_source_root_outside_project:{source_root}")
            continue
        if not source_root.is_dir():
            blockers.append(f"runtime_source_root_unavailable:{source_root}")
            continue
        for raw_path in source_root.rglob("*.py"):
            path = raw_path.resolve()
            if path in seen:
                continue
            seen.add(path)
            if not _is_within(path, source_root) or not _is_within(path, project):
                blockers.append(f"runtime_source_path_escape:{path}")
                continue
            try:
                content = path.read_bytes()
            except OSError:
                blockers.append(f"runtime_source_unavailable:{path}")
                continue
            files.append({
                "path": path.relative_to(project).as_posix(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            })

    files.sort(key=lambda item: str(item.get("path") or ""))
    if not files:
        blockers.append("runtime_source_files_missing")
    core = {
        "schema_version": RUNTIME_BUILD_SCHEMA_VERSION,
        "files": files,
    }
    return {
        **core,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "source_count": len(files),
        "fingerprint": _canonical_hash(core),
    }


class RuntimeBuildGuard:
    def __init__(
        self,
        *,
        project_root: Path | str,
        source_roots: Iterable[Path | str],
        cache_ttl_ms: int = 2_000,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.source_roots = tuple(Path(item).resolve() for item in source_roots)
        self.cache_ttl_ms = max(int(cache_ttl_ms), 0)
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.loaded_at = int(self.now_ms())
        self.loaded_manifest = build_runtime_source_manifest(self.project_root, self.source_roots)
        self._current_manifest = dict(self.loaded_manifest)
        self._current_scanned_at = self.loaded_at
        self._lock = threading.Lock()

    def snapshot(self, *, force: bool = False) -> dict[str, Any]:
        stamp = int(self.now_ms())
        with self._lock:
            if force or stamp - self._current_scanned_at >= self.cache_ttl_ms:
                self._current_manifest = build_runtime_source_manifest(self.project_root, self.source_roots)
                self._current_scanned_at = stamp
            current = dict(self._current_manifest)
            scanned_at = int(self._current_scanned_at)

        loaded = self.loaded_manifest
        loaded_ok = loaded.get("status") == "PASS"
        current_ok = current.get("status") == "PASS"
        source_changed = (
            str(loaded.get("fingerprint") or "") != str(current.get("fingerprint") or "")
            or int(loaded.get("source_count") or 0) != int(current.get("source_count") or 0)
        )
        blockers = [
            *(f"loaded:{item}" for item in list(loaded.get("blockers") or [])),
            *(f"disk:{item}" for item in list(current.get("blockers") or [])),
        ]
        if loaded_ok and current_ok and source_changed:
            blockers.append("runtime_source_tree_changed_after_start")
        restart_required = not loaded_ok or not current_ok or source_changed
        status = "PASS" if not restart_required else (
            "RESTART_REQUIRED" if loaded_ok else "BLOCK"
        )
        return {
            "schema_version": RUNTIME_BUILD_SCHEMA_VERSION,
            "status": status,
            "blockers": list(dict.fromkeys(blockers)),
            "process_id": os.getpid(),
            "loaded_at": self.loaded_at,
            "scanned_at": scanned_at,
            "cache_age_ms": max(stamp - scanned_at, 0),
            "loaded_fingerprint": str(loaded.get("fingerprint") or ""),
            "disk_fingerprint": str(current.get("fingerprint") or ""),
            "loaded_source_count": int(loaded.get("source_count") or 0),
            "disk_source_count": int(current.get("source_count") or 0),
            "source_changed_after_start": source_changed,
            "restart_required": restart_required,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
