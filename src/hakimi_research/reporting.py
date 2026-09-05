from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


_ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _publish_without_replace(staged: Path, destination: Path, encoded: bytes) -> None:
    """Atomically create a hard link; never replace existing evidence.

    Unsupported filesystems fail closed. Existing identical bytes make retries
    idempotent; there is no fallback that writes an incomplete final file.
    """
    try:
        os.link(staged, destination)
    except FileExistsError:
        if destination.read_bytes() != encoded:
            raise FileExistsError("report artifact already exists with different content") from None


def save_json_report(
    payload: dict,
    directory: str | Path,
    prefix: str,
    *,
    artifact_id: str = "",
) -> str:
    if type(payload) is not dict:
        raise ValueError("report payload must be an object")
    if type(prefix) is not str or _PREFIX_RE.fullmatch(prefix) is None:
        raise ValueError("report prefix is invalid")
    if type(artifact_id) is not str or (artifact_id and _ARTIFACT_ID_RE.fullmatch(artifact_id) is None):
        raise ValueError("report artifact_id is invalid")
    # Serialize before filesystem changes. Stable bytes make retry deterministic.
    encoded = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    stamp = artifact_id or hashlib.sha256(encoded).hexdigest()
    destination_dir = Path(directory)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{prefix}_{stamp}.json"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.staging-", suffix=".tmp", dir=destination_dir
    )
    staged = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if staged.read_bytes() != encoded:
            raise OSError("report staging verification failed")
        _publish_without_replace(staged, destination, encoded)
        # POSIX directory fsync persists the new entry. Windows publication is
        # atomic but this API does not promise power-failure durability.
        if os.name != "nt":
            directory_fd = os.open(destination_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        staged.unlink(missing_ok=True)
    return str(destination)
