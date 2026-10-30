"""Read retained SQLite records without creating sidecars beside their source."""
from __future__ import annotations

from contextlib import closing
import hashlib
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Any


class LegacyRecordSnapshotChangedError(RuntimeError):
    """The source changed while a retained-record snapshot was being read."""


def _file_identity(path: Path) -> tuple[int, int, int, str] | None:
    try:
        with path.open("rb") as handle:
            before = path.stat()
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
            after = path.stat()
    except FileNotFoundError:
        return None
    identity_before = (before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise LegacyRecordSnapshotChangedError("legacy_record_snapshot_changed_retry")
    return (*identity_after, digest)


def _source_identity(path: Path) -> tuple[tuple[int, int, int, str], tuple[int, int, int, str] | None]:
    database = _file_identity(path)
    if database is None:
        raise FileNotFoundError(f"legacy_record_database_missing:{path}")
    return database, _file_identity(Path(str(path) + "-wal"))


def read_legacy_record_snapshot(
    db_path: Path | str, sql: str, params: tuple[Any, ...] = ()
) -> list[sqlite3.Row]:
    """Read a stable committed snapshot and leave source files byte-identical.

    An immutable connection avoids SQLite creating WAL/SHM files for a closed
    archive. A nonempty WAL must instead be replayed beside a private temporary
    copy: immutable reads ignore it, while ordinary mode=ro can write source SHM.
    Source changes are surfaced as retryable errors rather than partial exports.
    """
    path = Path(db_path).expanduser().resolve()
    before = _source_identity(path)
    wal_identity = before[1]

    def select(snapshot: Path, *, immutable: bool) -> list[sqlite3.Row]:
        uri = f"{snapshot.as_uri()}?mode=ro" + ("&immutable=1" if immutable else "")
        with closing(sqlite3.connect(uri, uri=True, timeout=15)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            return connection.execute(sql, params).fetchall()

    if wal_identity is not None and wal_identity[1] > 0:
        with tempfile.TemporaryDirectory(prefix="hakimi-record-snapshot-") as directory:
            snapshot = Path(directory) / "records.sqlite3"
            shutil.copyfile(path, snapshot)
            shutil.copyfile(Path(str(path) + "-wal"), Path(str(snapshot) + "-wal"))
            copied = _source_identity(snapshot)
            if (copied[0][1], copied[0][3]) != (before[0][1], before[0][3]) or (
                copied[1] is None or (copied[1][1], copied[1][3]) != (wal_identity[1], wal_identity[3])
            ):
                raise LegacyRecordSnapshotChangedError("legacy_record_snapshot_changed_retry")
            if _source_identity(path) != before:
                raise LegacyRecordSnapshotChangedError("legacy_record_snapshot_changed_retry")
            records = select(snapshot, immutable=False)
    else:
        records = select(path, immutable=True)
    if _source_identity(path) != before:
        raise LegacyRecordSnapshotChangedError("legacy_record_snapshot_changed_retry")
    return records
