"""Content identity for the code and resources actually shipped and imported."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


BUILD_IDENTITY_FILENAME = "_build_identity.json"


def package_content_identity(package_root: str | Path) -> dict:
    root = Path(package_root)
    file_hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.name == BUILD_IDENTITY_FILENAME:
            continue
        if path.is_file() and path.suffix in {".py", ".json", ".lock"}:
            if path.is_symlink():
                raise ValueError("source identity does not allow symbolic links")
            file_hashes[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not file_hashes:
        raise ValueError("source identity has no files")
    encoded = json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"content_sha256": hashlib.sha256(encoded).hexdigest(), "file_hashes": file_hashes}
