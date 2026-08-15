from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Any
import uuid


def json_artifact_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def publish_json_artifact_no_clobber(
    output_path: Path | str,
    payload: dict[str, Any],
    *,
    failure_blocker: str = "json_artifact_publication_failed",
) -> dict[str, Any]:
    """Publish deterministic JSON bytes without replacing an existing target."""

    output = Path(output_path).resolve()
    raw = json_artifact_bytes(payload)
    file_sha256 = hashlib.sha256(raw).hexdigest()
    byte_length = len(raw)
    if output.exists():
        try:
            existing = output.read_bytes()
        except OSError:
            existing = b""
        identical = existing == raw
        return {
            "status": "EXISTING_IDENTICAL" if identical else "BLOCK",
            "blockers": [] if identical else [f"{failure_blocker}:target_conflict"],
            "published": False,
            "path": str(output),
            "file_sha256": file_sha256,
            "byte_length": byte_length,
        }

    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    result: dict[str, Any] | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError:
            try:
                existing = output.read_bytes()
            except OSError:
                existing = b""
            identical = existing == raw
            result = {
                "status": "EXISTING_IDENTICAL" if identical else "BLOCK",
                "blockers": [] if identical else [f"{failure_blocker}:target_conflict"],
                "published": False,
                "path": str(output),
                "file_sha256": file_sha256,
                "byte_length": byte_length,
            }
    except OSError:
        result = {
            "status": "BLOCK",
            "blockers": [failure_blocker],
            "published": False,
            "path": str(output),
            "file_sha256": file_sha256,
            "byte_length": byte_length,
        }
    try:
        temporary.unlink(missing_ok=True)
    except OSError:
        return {
            "status": "BLOCK",
            "blockers": ["temporary_cleanup_failed"],
            "published": False,
            "path": str(output),
            "file_sha256": file_sha256,
            "byte_length": byte_length,
        }
    if result is not None:
        return result

    try:
        persisted = output.read_bytes()
    except OSError:
        persisted = b""
    if persisted != raw:
        return {
            "status": "BLOCK",
            "blockers": [f"{failure_blocker}:post_publish_mismatch"],
            "published": False,
            "path": str(output),
            "file_sha256": file_sha256,
            "byte_length": byte_length,
        }
    return {
        "status": "PUBLISHED",
        "blockers": [],
        "published": True,
        "path": str(output),
        "file_sha256": file_sha256,
        "byte_length": byte_length,
    }
