"""Content identity for the code and resources actually shipped and imported."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


BUILD_IDENTITY_FILENAME = "_build_identity.json"
RUNTIME_MANIFEST_FILENAME = "runtime-files.json"


def runtime_file_names(package_root: str | Path) -> set[str] | None:
    root = Path(package_root)
    manifest = root / RUNTIME_MANIFEST_FILENAME
    if not manifest.is_file():
        return None
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if type(document) is not dict or set(document) != {"schema_version", "files"} or document["schema_version"] != "research-runtime-files-v1":
        raise ValueError("runtime source manifest schema invalid")
    names = document["files"]
    if type(names) is not list or any(type(name) is not str for name in names):
        raise ValueError("runtime source manifest files invalid")
    if names != sorted(set(names)) or RUNTIME_MANIFEST_FILENAME not in names:
        raise ValueError("runtime source manifest must be sorted, unique and self-bound")
    for name in names:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError("runtime source manifest path invalid")
        if relative.suffix not in {".py", ".json", ".lock"}:
            raise ValueError("runtime source manifest file type invalid")
        path = root / relative
        if not path.is_file() or any((root / Path(*relative.parts[:count])).is_symlink() for count in range(1, len(relative.parts) + 1)):
            raise ValueError("runtime source manifest file missing or symbolic")
    return set(names)


def package_content_identity(package_root: str | Path) -> dict:
    root = Path(package_root)
    selected = runtime_file_names(root)
    checkout = root.parent.name == "src" and (root.parent.parent / "pyproject.toml").is_file()
    file_hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.name == BUILD_IDENTITY_FILENAME:
            continue
        if path.is_file() and path.suffix in {".py", ".json", ".lock"}:
            if selected is not None and relative.as_posix() not in selected:
                if checkout:
                    continue
                raise ValueError("unexpected file in installed research package")
            if path.is_symlink():
                raise ValueError("source identity does not allow symbolic links")
            file_hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not file_hashes:
        raise ValueError("source identity has no files")
    encoded = json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"content_sha256": hashlib.sha256(encoded).hexdigest(), "file_hashes": file_hashes}
