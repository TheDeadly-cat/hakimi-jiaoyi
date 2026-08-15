from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .immutable_artifact_bundle import (
    ArtifactBundleError,
    read_bounded_artifact,
    windows_safe_basename_identity,
)
from .strict_json_artifact import StrictJsonArtifactError, parse_strict_json_object


MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES = 256 * 1024
MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class ForwardArtifactRead:
    """Path-free result for one bounded, no-link, strict-object JSON read."""

    status: str
    payload: dict[str, Any]
    raw: bytes
    blocker: str


def windows_safe_artifact_basename(value: Any) -> str | None:
    """Return the exact basename when it has one portable Windows identity."""

    return value if windows_safe_basename_identity(value) is not None else None


def read_forward_json_artifact(
    path: Path | str,
    *,
    byte_limit: int,
    size_limit_blocker: str = "portfolio_forward_artifact_size_limit_exceeded",
    max_nesting: int = 128,
) -> ForwardArtifactRead:
    """Read an exact artifact without exposing its path through failure details."""

    raw = b""
    try:
        raw = read_bounded_artifact(
            path,
            byte_limit=byte_limit,
            size_limit_blocker=size_limit_blocker,
        )
        payload = parse_strict_json_object(raw, max_nesting=max_nesting)
    except ArtifactBundleError as exc:
        missing = isinstance(exc.__cause__, FileNotFoundError)
        return ForwardArtifactRead(
            status="MISSING" if missing else "BLOCK",
            payload={},
            raw=b"",
            blocker=str(exc.blocker or "portfolio_forward_artifact_unreadable"),
        )
    except StrictJsonArtifactError as exc:
        return ForwardArtifactRead(
            status="BLOCK",
            payload={},
            # Retaining the already bounded exact bytes lets callers preserve
            # an established digest-mismatch priority without reopening the
            # file.  No bytes are returned when the read itself failed.
            raw=raw,
            blocker=str(exc) or "portfolio_forward_artifact_json_invalid",
        )
    except MemoryError:
        return ForwardArtifactRead(
            status="BLOCK",
            payload={},
            raw=b"",
            blocker="portfolio_forward_artifact_memory_exhausted",
        )
    except RecursionError:
        return ForwardArtifactRead(
            status="BLOCK",
            payload={},
            raw=b"",
            blocker="portfolio_forward_artifact_nesting_invalid",
        )
    except (OSError, UnicodeError):
        return ForwardArtifactRead(
            status="BLOCK",
            payload={},
            raw=b"",
            blocker="portfolio_forward_artifact_unreadable",
        )
    return ForwardArtifactRead(
        status="PASS",
        payload=payload,
        raw=raw,
        blocker="",
    )


__all__ = [
    "ForwardArtifactRead",
    "MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES",
    "MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES",
    "read_forward_json_artifact",
    "windows_safe_artifact_basename",
]
