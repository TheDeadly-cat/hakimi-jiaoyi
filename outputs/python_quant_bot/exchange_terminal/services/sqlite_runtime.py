from __future__ import annotations

from pathlib import Path
import sqlite3


class RuntimeReadOnlyError(PermissionError):
    """Raised before a persistent service can mutate a read-only runtime."""


def connect_runtime_sqlite(
    db_path: Path | str,
    *,
    read_only: bool = False,
    timeout: float = 15,
) -> sqlite3.Connection:
    path = Path(db_path)
    if read_only:
        resolved = path.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"read_only_database_missing:{resolved}")
        connection = sqlite3.connect(
            f"{resolved.as_uri()}?mode=ro&immutable=1",
            uri=True,
            timeout=timeout,
        )
        connection.execute("PRAGMA query_only=ON")
        return connection

    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=timeout)


def require_runtime_writable(*, read_only: bool, service: str) -> None:
    if read_only:
        raise RuntimeReadOnlyError(f"{service}_runtime_read_only")
