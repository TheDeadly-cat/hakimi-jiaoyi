from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Callable
import uuid

from .execution_authority import authority_violations
from .forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    read_forward_json_artifact,
)
from .immutable_artifact_bundle import (
    build_content_addressed_bundle_manifest,
    read_bounded_artifact,
    verify_content_addressed_bundle_manifest,
    windows_safe_basename_identity,
)
from .portfolio_backtest_pack import (
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
    MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
    build_internal_backtest_bundle,
    required_internal_backtest_bundle_members,
    verify_internal_backtest_bundle,
    verify_internal_backtest_pack,
)
from .portfolio_backtest_replay import (
    stage_portfolio_backtest_replay_bundle,
    verify_portfolio_backtest_replay_bundle,
)
from .portfolio_data_admission import verify_portfolio_data_admission_audit
from .portfolio_forward import verify_active_candidate_activation
from .portfolio_forward_performance import PortfolioForwardPerformanceLedger
from .portfolio_forward_local_source_anchor import (
    PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION,
    build_portfolio_forward_local_source_anchor,
    build_portfolio_forward_local_source_anchor_not_available,
    portfolio_local_source_observer_projection_from_chain,
    portfolio_local_source_settlement_projection_from_settlements,
    verify_portfolio_forward_local_source_anchor,
)
from .portfolio_forward_local_source_receipt import (
    PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
    PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
    verify_portfolio_backup_status,
)
from .portfolio_forward_watchdog import verify_portfolio_forward_watchdog_status
from .portfolio_robustness import verify_robustness_report
from .portfolio_shadow import PortfolioShadowLedger
from .strict_json_artifact import (
    StrictJsonArtifactError,
    StrictJsonSyntaxError,
    StrictJsonUtf8Error,
    parse_strict_json_object,
)


PORTFOLIO_EVIDENCE_ARCHIVE_V1_SCHEMA_VERSION = "portfolio-evidence-archive-v1"
PORTFOLIO_EVIDENCE_ARCHIVE_V2_SCHEMA_VERSION = "portfolio-evidence-archive-v2"
PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION = "portfolio-evidence-archive-v3"
SUPPORTED_PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSIONS = {
    PORTFOLIO_EVIDENCE_ARCHIVE_V1_SCHEMA_VERSION,
    PORTFOLIO_EVIDENCE_ARCHIVE_V2_SCHEMA_VERSION,
    PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION,
}
DEFAULT_ARCHIVE_DIRECTORY = "portfolio_forward_archives"
DEFAULT_BACKUP_STATUS_FILE = "portfolio_forward_backup_status.json"
DEFAULT_BACKUP_ALERT_FILE = "portfolio_forward_backup_alerts.jsonl"
CRITICAL_DATABASES = (
    "portfolio_shadow.sqlite",
    "portfolio_forward_performance.sqlite",
    "portfolio_experiments.sqlite3",
)
PORTFOLIO_ARCHIVE_BACKTEST_PACK_FILE = "internal_portfolio_backtest_pack_snapshot.json"
PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_ROOT = "reports"
PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_MANIFEST_FILE = "backtest_bundle_manifest.json"
MAX_PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_BYTES = (
    MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES
    + MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES
    + MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES
)
MAX_PORTFOLIO_ARCHIVE_JSON_NESTING = 128
MAX_PORTFOLIO_EVIDENCE_ARCHIVE_MANIFEST_BYTES = 8 * 1024 * 1024
_LOCAL_SOURCE_ANCHOR_MATERIAL_FIELD = "_local_source_anchor_material"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _safe_filename(value: Any) -> str:
    name = str(value or "")
    if windows_safe_basename_identity(name) is None:
        raise ValueError(f"Unsafe archive artifact filename: {name!r}")
    return name


def _safe_bundle_path(bundle_dir: Path, relative_path: str) -> Path:
    candidate = (bundle_dir / str(relative_path or "")).resolve()
    candidate.relative_to(bundle_dir.resolve())
    return candidate


def _sqlite_metadata(path: Path) -> dict[str, Any]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=30)) as connection:
        quick_check = [str(row[0]) for row in connection.execute("PRAGMA quick_check").fetchall()]
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        row_counts = {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
    return {
        "quick_check": quick_check,
        "journal_mode": journal_mode,
        "tables": tables,
        "row_counts": row_counts,
    }


def backup_sqlite_database(source_path: Path | str, destination_path: Path | str) -> dict[str, Any]:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{source.as_posix()}?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True, timeout=30)) as source_connection:
        source_connection.execute("PRAGMA busy_timeout=30000")
        with closing(sqlite3.connect(destination, timeout=30)) as destination_connection:
            source_connection.backup(destination_connection, pages=256, sleep=0.01)
            destination_connection.commit()
            journal_mode = str(destination_connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0])
            if journal_mode.lower() != "delete":
                raise ValueError(f"SQLite backup is not standalone: {source.name}: journal_mode={journal_mode}")
    metadata = _sqlite_metadata(destination)
    if metadata["quick_check"] != ["ok"]:
        raise ValueError(f"SQLite backup integrity failed: {source.name}: {metadata['quick_check']}")
    return {
        "source_name": source.name,
        "archive_path": f"databases/{destination.name}",
        "size": destination.stat().st_size,
        "sha256": file_sha256(destination),
        **metadata,
    }


def _write_verified_bytes(destination: Path, raw: bytes, expected_sha256: str = "") -> dict[str, Any]:
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and actual != expected_sha256:
        raise ValueError(f"Artifact changed during archive capture: {destination.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return {
        "archive_path": destination.as_posix(),
        "size": len(raw),
        "sha256": actual,
    }


def _exact_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    try:
        return parse_strict_json_object(
            raw,
            max_nesting=MAX_PORTFOLIO_ARCHIVE_JSON_NESTING,
        )
    except (StrictJsonUtf8Error, StrictJsonSyntaxError) as exc:
        # Preserve the legacy archive boundary's built-in decode exception type;
        # public archive blockers historically include type(exc).__name__.
        cause = exc.__cause__
        if isinstance(cause, (UnicodeDecodeError, json.JSONDecodeError, ValueError)):
            raise cause
        raise ValueError(str(exc)) from exc
    except StrictJsonArtifactError as exc:
        # Duplicate/non-finite/depth/root failures were plain ValueError here.
        raise ValueError(str(exc)) from exc


def _read_strict_bounded_json(path: Path, *, maximum_bytes: int) -> dict[str, Any]:
    raw = read_bounded_artifact(
        path,
        byte_limit=maximum_bytes,
        size_limit_blocker="portfolio_evidence_archive_json_size_limit_exceeded",
    )
    return _strict_json_object(raw)


def _build_archive_backtest_bundle(
    pack: dict[str, Any],
    detached_artifacts: Any,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    verification = verify_internal_backtest_bundle(pack, detached_artifacts)
    if verification.get("status") != "PASS":
        raise ValueError(
            f"live_backtest_bundle_verification_blocked:{verification.get('blockers')}"
        )
    if not isinstance(detached_artifacts, (list, tuple)):
        raise ValueError("live_backtest_bundle_detached_artifacts_invalid")

    members: dict[str, bytes] = {
        PORTFOLIO_ARCHIVE_BACKTEST_PACK_FILE: _exact_json_bytes(pack),
    }
    roles = {PORTFOLIO_ARCHIVE_BACKTEST_PACK_FILE: "BACKTEST_PACK"}
    supplied_roles: set[str] = set()
    for raw_item in detached_artifacts:
        item = dict(raw_item or {}) if isinstance(raw_item, dict) else {}
        role = str(item.get("role") or "")
        name = _safe_filename(item.get("file"))
        raw = item.get("raw_bytes")
        if role not in {"RESEARCH_REPORT", "STATISTICAL_AUDIT"}:
            raise ValueError(f"live_backtest_bundle_role_invalid:{role}")
        if role in supplied_roles or name in members or not isinstance(raw, bytes):
            raise ValueError(f"live_backtest_bundle_member_invalid:{role}")
        digest = hashlib.sha256(raw).hexdigest()
        if (
            str(item.get("sha256") or "") != digest
            or item.get("byte_length") != len(raw)
        ):
            raise ValueError(f"live_backtest_bundle_member_identity_invalid:{role}")
        supplied_roles.add(role)
        members[name] = raw
        roles[name] = role
    if supplied_roles != {"RESEARCH_REPORT", "STATISTICAL_AUDIT"}:
        raise ValueError("live_backtest_bundle_member_inventory_invalid")

    candidate_hash = str(dict(pack.get("candidate") or {}).get("candidate_hash") or "")
    bindings = {
        "pack_schema_version": str(pack.get("schema_version") or ""),
        "pack_hash": str(pack.get("pack_hash") or ""),
        "evidence_hash": str(pack.get("evidence_hash") or ""),
        "candidate_hash": candidate_hash,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    immutable_manifest = build_content_addressed_bundle_manifest(
        members,
        member_roles=roles,
        bindings=bindings,
        manifest_file=PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_MANIFEST_FILE,
        max_member_count=3,
        max_member_bytes=MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
        max_total_bytes=MAX_PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_BYTES,
    )
    descriptor = {
        "archive_root": PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_ROOT,
        "manifest": immutable_manifest,
    }
    if authority_violations(descriptor):
        raise ValueError("live_backtest_bundle_contains_execution_authority")
    return descriptor, members


def _load_archived_backtest_bundle(
    bundle_dir: Path,
    descriptor: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = dict(descriptor or {}) if isinstance(descriptor, dict) else {}
    if not isinstance(descriptor, dict) or set(payload) != {"archive_root", "manifest"}:
        blockers.append("archive_backtest_bundle_descriptor_invalid")
    archive_root = str(payload.get("archive_root") or "")
    if archive_root != PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_ROOT:
        blockers.append("archive_backtest_bundle_root_invalid")
    immutable_manifest = dict(payload.get("manifest") or {})
    manifest_verification = verify_content_addressed_bundle_manifest(
        immutable_manifest,
        manifest_file=PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_MANIFEST_FILE,
        max_member_count=3,
        max_member_bytes=MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
        max_total_bytes=MAX_PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_BYTES,
    )
    if manifest_verification.get("status") != "PASS":
        blockers.extend(
            f"archive_backtest_bundle:{item}"
            for item in manifest_verification.get("blockers") or []
        )

    records = [dict(item or {}) for item in list(immutable_manifest.get("members") or [])]
    roles = [str(item.get("role") or "") for item in records]
    if sorted(roles) != ["BACKTEST_PACK", "RESEARCH_REPORT", "STATISTICAL_AUDIT"]:
        blockers.append("archive_backtest_bundle_role_inventory_invalid")
    raw_by_role: dict[str, bytes] = {}
    record_by_role: dict[str, dict[str, Any]] = {}
    role_size_limits = {
        "BACKTEST_PACK": MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES,
        "RESEARCH_REPORT": MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
        "STATISTICAL_AUDIT": MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
    }
    for record in records:
        role = str(record.get("role") or "")
        try:
            name = _safe_filename(record.get("file"))
            path = _safe_bundle_path(bundle_dir, f"{archive_root}/{name}")
        except (ValueError, OSError):
            blockers.append(f"archive_backtest_bundle_member_path_invalid:{role}")
            continue
        if role in record_by_role:
            blockers.append(f"archive_backtest_bundle_member_duplicate:{role}")
            continue
        declared_size = record.get("size")
        if (
            isinstance(declared_size, bool)
            or not isinstance(declared_size, int)
            or declared_size < 0
            or declared_size > role_size_limits.get(role, 0)
        ):
            blockers.append(f"archive_backtest_bundle_member_size_invalid:{role}")
            continue
        if not path.is_file():
            blockers.append(f"archive_backtest_bundle_member_missing:{role}")
            continue
        if path.stat().st_size != declared_size:
            blockers.append(f"archive_backtest_bundle_member_size_mismatch:{role}")
            continue
        try:
            raw = read_bounded_artifact(
                path,
                byte_limit=role_size_limits[role],
                size_limit_blocker="archive_backtest_bundle_member_size_limit_exceeded",
            )
        except ValueError as exc:
            blocker = str(getattr(exc, "blocker", "") or type(exc).__name__)
            blockers.append(f"archive_backtest_bundle_member_read_blocked:{role}:{blocker}")
            continue
        if len(raw) != declared_size:
            blockers.append(f"archive_backtest_bundle_member_size_mismatch:{role}")
            continue
        if hashlib.sha256(raw).hexdigest() != str(record.get("sha256") or ""):
            blockers.append(f"archive_backtest_bundle_member_hash_mismatch:{role}")
            continue
        try:
            _strict_json_object(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            blockers.append(f"archive_backtest_bundle_member_json_invalid:{role}")
            continue
        record_by_role[role] = record
        raw_by_role[role] = raw

    pack: dict[str, Any] = {}
    pack_raw = raw_by_role.get("BACKTEST_PACK")
    if pack_raw is None:
        blockers.append("archive_backtest_bundle_pack_missing")
    elif len(pack_raw) > MAX_PORTFOLIO_INTERNAL_BACKTEST_PACK_BYTES:
        blockers.append("archive_backtest_bundle_pack_size_limit_exceeded")
    else:
        try:
            pack = _strict_json_object(pack_raw)
            if _exact_json_bytes(pack) != pack_raw:
                blockers.append("archive_backtest_bundle_pack_serialization_noncanonical")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            blockers.append("archive_backtest_bundle_pack_json_invalid")

    bindings = dict(immutable_manifest.get("bindings") or {})
    expected_binding_fields = {
        "pack_schema_version",
        "pack_hash",
        "evidence_hash",
        "candidate_hash",
        "research_only",
        "paper_authorized",
        "live_order_allowed",
    }
    if set(bindings) != expected_binding_fields:
        blockers.append("archive_backtest_bundle_bindings_invalid")
    if (
        bindings.get("research_only") is not True
        or bindings.get("paper_authorized") is not False
        or bindings.get("live_order_allowed") is not False
        or authority_violations(bindings)
    ):
        blockers.append("archive_backtest_bundle_scope_invalid")
    if pack:
        expected_bindings = {
            "pack_schema_version": str(pack.get("schema_version") or ""),
            "pack_hash": str(pack.get("pack_hash") or ""),
            "evidence_hash": str(pack.get("evidence_hash") or ""),
            "candidate_hash": str(dict(pack.get("candidate") or {}).get("candidate_hash") or ""),
        }
        for key, value in expected_bindings.items():
            if str(bindings.get(key) or "") != value:
                blockers.append(f"archive_backtest_bundle_binding_mismatch:{key}")

    detached_artifacts: list[dict[str, Any]] = []
    if pack:
        required_members = required_internal_backtest_bundle_members(pack)
        if len(required_members) != 2:
            blockers.append("archive_backtest_bundle_required_members_invalid")
        for required in required_members:
            role = str(required.get("role") or "")
            record = record_by_role.get(role) or {}
            raw = raw_by_role.get(role)
            if (
                not record
                or raw is None
                or str(record.get("file") or "") != str(required.get("file") or "")
                or str(record.get("sha256") or "") != str(required.get("sha256") or "")
                or record.get("size") != required.get("byte_length")
            ):
                blockers.append(f"archive_backtest_bundle_required_member_mismatch:{role}")
                continue
            detached_artifacts.append(
                {
                    "role": role,
                    "file": str(record.get("file") or ""),
                    "sha256": str(record.get("sha256") or ""),
                    "byte_length": record.get("size"),
                    "raw_bytes": raw,
                }
            )

    bundle_verification: dict[str, Any] = {}
    if pack and len(detached_artifacts) == 2:
        bundle_verification = verify_internal_backtest_bundle(pack, detached_artifacts)
        if bundle_verification.get("status") != "PASS":
            blockers.extend(
                f"pack_bundle:{item}"
                for item in bundle_verification.get("blockers") or ["verification_blocked"]
            )
    else:
        blockers.append("archive_backtest_bundle_incomplete")
    if authority_violations(payload):
        blockers.append("archive_backtest_bundle_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "pack": pack,
        "detached_artifacts": detached_artifacts,
        "bundle_verification": bundle_verification,
        "bundle_hash": str(immutable_manifest.get("bundle_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _stage_consistent_pack(
    live_report_dir: Path,
    stage_root: Path,
    *,
    generated_at: int,
    max_attempts: int,
) -> tuple[Path, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    last_error = "consistent_pack_capture_failed"
    for attempt in range(1, max(int(max_attempts), 1) + 1):
        attempt_dir = stage_root / f"attempt-{attempt}" / "reports"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        try:
            live_bundle = build_internal_backtest_bundle(
                live_report_dir,
                generated_at=generated_at,
            )
            live_pack = dict(live_bundle.get("pack") or {})
            detached_artifacts = list(live_bundle.get("detached_artifacts") or [])
            backtest_bundle, member_bytes = _build_archive_backtest_bundle(
                live_pack,
                detached_artifacts,
            )
            for name, raw in member_bytes.items():
                _write_verified_bytes(attempt_dir / name, raw)
            active_name = "active_portfolio_candidate.json"
            active_bytes = (live_report_dir / active_name).read_bytes()
            active_destination = attempt_dir / active_name
            if active_destination.exists():
                raise ValueError("snapshot_active_registry_name_collision")
            active_destination.write_bytes(active_bytes)
            for record in dict(live_pack.get("artifacts") or {}).values():
                artifact = dict(record or {})
                name = _safe_filename(artifact.get("file"))
                expected = str(artifact.get("file_sha256") or "")
                raw = (live_report_dir / name).read_bytes()
                destination = attempt_dir / name
                if destination.exists():
                    if (
                        hashlib.sha256(destination.read_bytes()).hexdigest()
                        != hashlib.sha256(raw).hexdigest()
                    ):
                        raise ValueError(f"snapshot_artifact_duplicate_mismatch:{name}")
                else:
                    _write_verified_bytes(destination, raw, expected)
            if live_pack.get("status") != "INTERNAL_BACKTEST_EVIDENCE_READY":
                raise ValueError(f"snapshot_pack_not_ready:{live_pack.get('blockers')}")
            for record in dict(live_pack.get("artifacts") or {}).values():
                artifact = dict(record or {})
                name = _safe_filename(artifact.get("file"))
                if file_sha256(attempt_dir / name) != str(artifact.get("file_sha256") or ""):
                    raise ValueError(f"snapshot_artifact_hash_mismatch:{name}")
            return attempt_dir, live_pack, backtest_bundle, detached_artifacts
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            last_error = str(exc)
            shutil.rmtree(attempt_dir.parent, ignore_errors=True)
            if attempt < max(int(max_attempts), 1):
                time.sleep(0.1)
    raise RuntimeError(last_error)


def _copy_candidate_sources(candidate: dict[str, Any], project_root: Path, source_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    files = list(dict(candidate.get("implementation") or {}).get("files") or [])
    for item in files:
        record = dict(item or {})
        source = Path(str(record.get("path") or "")).resolve()
        relative = source.relative_to(project_root.resolve())
        raw = source.read_bytes()
        expected = str(record.get("sha256") or "")
        actual = hashlib.sha256(raw).hexdigest()
        if not expected or actual != expected:
            raise ValueError(f"Frozen implementation source changed: {relative.as_posix()}")
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        records.append({
            "source_path": relative.as_posix(),
            "archive_path": f"source/{relative.as_posix()}",
            "size": len(raw),
            "sha256": actual,
        })
    if len(records) != len(files) or not records:
        raise ValueError("Frozen implementation source inventory is incomplete")
    return records


def _copy_optional_reports(live_report_dir: Path, archive_report_dir: Path, candidate_hash: str) -> list[str]:
    copied: list[str] = []
    candidates: list[tuple[int, Path, Callable[[dict[str, Any]], dict[str, Any]]]] = []
    for path in live_report_dir.glob("portfolio_data_admission_*.json"):
        candidates.append((path.stat().st_mtime_ns, path, verify_portfolio_data_admission_audit))
    for path in live_report_dir.glob("portfolio_forward_watchdog_status.json"):
        candidates.append((path.stat().st_mtime_ns, path, verify_portfolio_forward_watchdog_status))
    selected_kinds: set[str] = set()
    for _stamp, path, verifier in sorted(candidates, key=lambda item: item[0], reverse=True):
        kind = "data_admission" if path.name.startswith("portfolio_data_admission_") else "watchdog"
        if kind in selected_kinds:
            continue
        try:
            payload = _read_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if str(payload.get("candidate_hash") or "") != candidate_hash:
            continue
        if verifier(payload).get("status") != "PASS":
            continue
        (archive_report_dir / path.name).write_bytes(path.read_bytes())
        copied.append(path.name)
        selected_kinds.add(kind)
    for name in ("portfolio_forward_scheduler_alerts.jsonl", "portfolio_forward_watchdog_alerts.jsonl"):
        source = live_report_dir / name
        if source.exists():
            (archive_report_dir / name).write_bytes(source.read_bytes())
            copied.append(name)
    return copied


def _candidate_archive_verification(report_dir: Path, source_dir: Path) -> dict[str, Any]:
    blockers: list[str] = []
    registry = _read_json(report_dir / "active_portfolio_candidate.json")
    activation = verify_active_candidate_activation(registry)
    if activation.get("status") != "PASS":
        blockers.extend(f"activation:{item}" for item in activation.get("blockers") or [])
    candidate_name = _safe_filename(registry.get("candidate_file"))
    candidate_path = report_dir / candidate_name
    if file_sha256(candidate_path) != str(registry.get("candidate_file_sha256") or ""):
        blockers.append("candidate_file_hash_mismatch")
    candidate = _read_json(candidate_path)
    candidate_payload = dict(candidate)
    candidate_hash = str(candidate_payload.pop("candidate_hash", "") or "")
    if not candidate_hash or canonical_hash(candidate_payload) != candidate_hash:
        blockers.append("candidate_hash_invalid")
    if candidate_hash != str(registry.get("candidate_hash") or ""):
        blockers.append("candidate_registry_hash_mismatch")
    robustness_name = _safe_filename(registry.get("robustness_file"))
    robustness_path = report_dir / robustness_name
    if file_sha256(robustness_path) != str(registry.get("robustness_file_sha256") or ""):
        blockers.append("robustness_file_hash_mismatch")
    robustness = _read_json(robustness_path)
    robustness_verification = verify_robustness_report(robustness, candidate_hash=candidate_hash)
    if robustness_verification.get("status") != "PASS":
        blockers.extend(f"robustness:{item}" for item in robustness_verification.get("blockers") or [])
    source_records = list(dict(candidate.get("implementation") or {}).get("files") or [])
    source_matches = 0
    for item in source_records:
        record = dict(item or {})
        original = Path(str(record.get("path") or ""))
        parts = original.parts
        try:
            marker = parts.index("python_quant_bot")
        except ValueError:
            blockers.append(f"implementation_source_outside_project:{original.name}")
            continue
        relative = Path(*parts[marker + 1:])
        archived = source_dir / relative
        if not archived.exists() or file_sha256(archived) != str(record.get("sha256") or ""):
            blockers.append(f"implementation_source_hash_mismatch:{relative.as_posix()}")
        else:
            source_matches += 1
    if source_matches != len(source_records) or not source_records:
        blockers.append("implementation_source_archive_incomplete")
    if authority_violations({"registry": registry, "candidate": candidate, "robustness": robustness}):
        blockers.append("candidate_archive_contains_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": candidate_hash,
        "source_file_count": len(source_records),
        "source_file_match_count": source_matches,
        "activation_status": activation.get("status"),
        "robustness_status": robustness_verification.get("status"),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _pack_artifact_verification(report_dir: Path, pack: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    checks: dict[str, bool] = {}
    for role, value in dict(pack.get("artifacts") or {}).items():
        record = dict(value or {})
        try:
            name = _safe_filename(record.get("file"))
        except ValueError:
            checks[role] = False
            blockers.append(f"pack_artifact_filename_invalid:{role}")
            continue
        path = report_dir / name
        matches = path.exists() and file_sha256(path) == str(record.get("file_sha256") or "")
        checks[role] = matches
        if not matches:
            blockers.append(f"pack_artifact_hash_mismatch:{role}:{name}")
    return {
        "status": "PASS" if checks and all(checks.values()) and not blockers else "BLOCK",
        "checks": checks,
        "blockers": blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class _ArchiveProjectionPerformanceLedger(PortfolioForwardPerformanceLedger):
    """Cache the summary's settlement read for the local-source projection.

    ``PortfolioForwardPerformanceLedger.summary`` already reads the settlement
    rows before running its semantic audit.  The archive rehearsal needs those
    same verified objects to derive a bounded projection, so retaining that one
    read avoids an anchor-only scan of the restored database.
    """

    def __init__(self, path: Path | str) -> None:
        self._archive_settlement_cache: dict[str, list[dict[str, Any]]] = {}
        super().__init__(path)

    def settlements(self, candidate_hash: str) -> list[dict[str, Any]]:
        clean_hash = str(candidate_hash or "")
        if clean_hash not in self._archive_settlement_cache:
            self._archive_settlement_cache[clean_hash] = super().settlements(clean_hash)
        return [dict(item) for item in self._archive_settlement_cache[clean_hash]]


def _public_restore_rehearsal(payload: Any) -> dict[str, Any]:
    rehearsal = dict(payload or {}) if isinstance(payload, dict) else {}
    rehearsal.pop(_LOCAL_SOURCE_ANCHOR_MATERIAL_FIELD, None)
    return rehearsal


def _local_source_anchor_material(
    *,
    candidate_hash: str,
    observations: dict[str, dict[str, Any]],
    settlements: list[dict[str, Any]],
    shadow_audit: dict[str, Any],
    performance_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return API-rebuildable projections only after deep ledger binding.

    The projection hashes intentionally use the exact rows already embedded in
    forward status artifacts.  The stronger observation-evidence comparison is
    a generation gate and is not widened into the public anchor contract.
    """

    clean_candidate_hash = str(candidate_hash or "")
    if (
        shadow_audit.get("status") != "PASS"
        or performance_summary.get("status") != "PASS"
        or str(shadow_audit.get("candidate_hash") or "") != clean_candidate_hash
        or str(performance_summary.get("candidate_hash") or "") != clean_candidate_hash
    ):
        return {}
    observation_dates = sorted(str(key or "") for key in observations)
    settlement_dates = [str(item.get("settlement_date") or "") for item in settlements]
    if (
        not observation_dates
        or observation_dates != settlement_dates
        or len(observation_dates) != len(set(observation_dates))
        or int(shadow_audit.get("observation_count") or 0) != len(observation_dates)
        or int(shadow_audit.get("valid_observation_count") or 0) != len(observation_dates)
        or int(shadow_audit.get("observation_chain_count") or 0) != len(observation_dates)
        or int(performance_summary.get("settlement_count") or 0) != len(settlement_dates)
        or list(performance_summary.get("unsettled_observation_dates") or [])
        or list(performance_summary.get("unexpected_settlement_dates") or [])
        or list(performance_summary.get("observation_hash_mismatch_dates") or [])
        or list(shadow_audit.get("integrity_violations") or [])
        or list(performance_summary.get("integrity_violations") or [])
    ):
        return {}
    first_date = observation_dates[0]
    last_date = observation_dates[-1]
    if (
        str(shadow_audit.get("first_signal_date") or "") != first_date
        or str(shadow_audit.get("last_signal_date") or "") != last_date
        or str(performance_summary.get("first_settlement_date") or "") != first_date
        or str(performance_summary.get("last_settlement_date") or "") != last_date
    ):
        return {}

    try:
        observer_projection = portfolio_local_source_observer_projection_from_chain(
            list(shadow_audit.get("observation_chain") or [])
        )
        settlement_projection = portfolio_local_source_settlement_projection_from_settlements(
            settlements
        )
    except (TypeError, ValueError, OverflowError):
        return {}
    if (
        [str(item.get("signal_date") or "") for item in observer_projection]
        != observation_dates
        or [str(item.get("date") or "") for item in settlement_projection]
        != observation_dates
    ):
        return {}
    if authority_violations({
        "observations": [dict(observations[date_value]) for date_value in observation_dates],
        "settlements": settlements,
        "shadow_audit": shadow_audit,
        "performance_summary": performance_summary,
    }):
        return {}

    observation_identity_fields = (
        "candidate_hash",
        "signal_date",
        "dataset_hash",
        "observation_hash",
        "decision_hash",
        "capture_contract_hash",
        "risk_snapshot_hash",
        "risk_gate_status",
        "forward_state_contract_hash",
        "observed_at",
    )
    for date_value, observer_row, settlement in zip(
        observation_dates,
        observer_projection,
        settlements,
    ):
        observation = dict(observations.get(date_value) or {})
        current = dict(dict(settlement.get("observation_evidence") or {}).get("current") or {})
        capture = dict(observation.get("capture_contract") or {})
        expected_current = {
            "candidate_hash": clean_candidate_hash,
            "signal_date": date_value,
            "dataset_hash": str(observation.get("dataset_hash") or ""),
            "observation_hash": str(observation.get("observation_hash") or ""),
            "decision_hash": str(observation.get("decision_hash") or ""),
            "capture_contract_hash": str(observation.get("capture_contract_hash") or ""),
            "clock_attestation_hash": str(capture.get("clock_attestation_hash") or ""),
            "risk_snapshot_hash": str(observation.get("risk_snapshot_hash") or ""),
            "risk_gate_status": str(observation.get("risk_gate_status") or ""),
            "forward_state_contract_hash": str(observation.get("forward_state_contract_hash") or ""),
            "observed_at": int(observation.get("observed_at") or 0),
        }
        if (
            str(observation.get("candidate_hash") or "") != clean_candidate_hash
            or str(observation.get("signal_date") or "") != date_value
            or str(settlement.get("candidate_hash") or "") != clean_candidate_hash
            or str(settlement.get("settlement_date") or "") != date_value
            or str(observer_row.get("observation_hash") or "")
            != str(observation.get("observation_hash") or "")
            or any(current.get(field) != expected_current[field] for field in observation_identity_fields)
            or str(current.get("clock_attestation_hash") or "")
            != expected_current["clock_attestation_hash"]
        ):
            return {}
    return {
        "observer_projection": observer_projection,
        "settlement_projection": settlement_projection,
    }


def _local_source_anchor_for_verified_archive(
    *,
    manifest: dict[str, Any],
    manifest_hash: str,
    database_snapshots: list[dict[str, Any]],
    material: dict[str, Any],
) -> dict[str, Any]:
    schema_version = str(manifest.get("schema_version") or "")
    reason = (
        "ARCHIVE_SCHEMA_NOT_SUPPORTED"
        if schema_version != PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION
        else "CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE"
    )
    if schema_version == PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION and material:
        snapshots = {
            str(item.get("source_name") or ""): dict(item)
            for item in database_snapshots
        }
        verified_database_hashes = dict(material.get("database_sha256") or {})
        shadow_database_sha256 = str(
            verified_database_hashes.get("portfolio_shadow.sqlite") or ""
        )
        performance_database_sha256 = str(
            verified_database_hashes.get("portfolio_forward_performance.sqlite") or ""
        )
        if (
            shadow_database_sha256
            != str(dict(snapshots.get("portfolio_shadow.sqlite") or {}).get("sha256") or "")
            or performance_database_sha256
            != str(
                dict(snapshots.get("portfolio_forward_performance.sqlite") or {}).get("sha256")
                or ""
            )
        ):
            material = {}
        try:
            anchor = build_portfolio_forward_local_source_anchor(
                candidate_hash=str(manifest.get("candidate_hash") or ""),
                archive_manifest_hash=str(manifest_hash or ""),
                archive_generated_at=manifest.get("generated_at"),
                observer_projection=material.get("observer_projection"),
                settlement_projection=material.get("settlement_projection"),
                shadow_database_sha256=shadow_database_sha256,
                performance_database_sha256=performance_database_sha256,
            )
            if (
                anchor.get("schema_version")
                == PORTFOLIO_FORWARD_LOCAL_SOURCE_ANCHOR_SCHEMA_VERSION
                and verify_portfolio_forward_local_source_anchor(anchor).get("status") == "PASS"
            ):
                return anchor
        except (TypeError, ValueError, OverflowError):
            pass
    try:
        return build_portfolio_forward_local_source_anchor_not_available(
            reason=reason,
            candidate_hash=str(manifest.get("candidate_hash") or ""),
            archive_manifest_hash=str(manifest_hash or ""),
            archive_generated_at=(
                manifest.get("generated_at")
                if isinstance(manifest.get("generated_at"), int)
                and not isinstance(manifest.get("generated_at"), bool)
                else 0
            ),
        )
    except (TypeError, ValueError, OverflowError):
        return build_portfolio_forward_local_source_anchor_not_available(reason=reason)


def _restore_rehearsal(
    bundle_dir: Path,
    pack: dict[str, Any],
    *,
    detached_artifacts: Any = None,
    expected_database_sha256: dict[str, str] | None = None,
) -> dict[str, Any]:
    report_dir = bundle_dir / "reports"
    database_dir = bundle_dir / "databases"
    source_dir = bundle_dir / "source"
    candidate_verification = _candidate_archive_verification(report_dir, source_dir)
    pack_verification = (
        verify_internal_backtest_bundle(pack, detached_artifacts)
        if detached_artifacts is not None
        else verify_internal_backtest_pack(pack)
    )
    artifact_verification = _pack_artifact_verification(report_dir, pack)
    candidate_hash = str(candidate_verification.get("candidate_hash") or "")
    forward_record = dict(dict(pack.get("artifacts") or {}).get("forward_observation") or {})
    performance_record = dict(dict(pack.get("artifacts") or {}).get("forward_performance") or {})
    forward = _read_json(report_dir / _safe_filename(forward_record.get("file")))
    performance = _read_json(report_dir / _safe_filename(performance_record.get("file")))
    expected_database_hashes = {
        str(name or ""): str(value or "")
        for name, value in dict(expected_database_sha256 or {}).items()
    }
    restored_database_hashes: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="hakimi-portfolio-restore-") as temporary:
        restore_root = Path(temporary)
        shadow_path = restore_root / "portfolio_shadow.sqlite"
        performance_path = restore_root / "portfolio_forward_performance.sqlite"
        shutil.copy2(database_dir / shadow_path.name, shadow_path)
        shutil.copy2(database_dir / performance_path.name, performance_path)
        for restored_path in (shadow_path, performance_path):
            expected_hash = str(expected_database_hashes.get(restored_path.name) or "")
            actual_hash = file_sha256(restored_path)
            if not expected_hash or actual_hash != expected_hash:
                raise ValueError(f"restore_database_hash_mismatch:{restored_path.name}")
            restored_database_hashes[restored_path.name] = actual_hash
        shadow = PortfolioShadowLedger(shadow_path)
        observation_dates = shadow.observation_dates(candidate_hash)
        observations = {
            date: dict(shadow.observation(candidate_hash, date) or {})
            for date in observation_dates
        }
        shadow_audit = shadow.audit(candidate_hash)
        performance_ledger = _ArchiveProjectionPerformanceLedger(performance_path)
        performance_summary = performance_ledger.summary(candidate_hash, observations=observations)
        settlements = performance_ledger.settlements(candidate_hash)
        for restored_path in (shadow_path, performance_path):
            if file_sha256(restored_path) != restored_database_hashes[restored_path.name]:
                raise ValueError(
                    f"restore_database_post_read_hash_mismatch:{restored_path.name}"
                )

    expected_shadow_audit = dict(dict(forward.get("readiness") or {}).get("ledger_audit") or {})
    performance_shadow_audit = dict(performance.get("shadow_audit") or {})
    expected_performance_summary = dict(performance.get("performance") or {})
    checks = {
        "candidate_archive_pass": candidate_verification.get("status") == "PASS",
        "pack_hash_pass": pack_verification.get("status") == "PASS",
        "pack_artifacts_pass": artifact_verification.get("status") == "PASS",
        "shadow_ledger_pass": shadow_audit.get("status") == "PASS",
        "performance_ledger_pass": performance_summary.get("status") == "PASS",
        "forward_status_matches_shadow_backup": canonical_hash(expected_shadow_audit) == canonical_hash(shadow_audit),
        "performance_status_matches_shadow_backup": canonical_hash(performance_shadow_audit) == canonical_hash(shadow_audit),
        "performance_status_matches_performance_backup": canonical_hash(expected_performance_summary)
        == canonical_hash(performance_summary),
        "no_execution_authority": not authority_violations({
            "pack": pack,
            "forward": forward,
            "performance": performance,
        }),
    }
    blockers = [name for name, passed in checks.items() if not passed]
    payload = {
        "status": "PASS" if not blockers else "BLOCK",
        "checks": checks,
        "blockers": blockers,
        "candidate_hash": candidate_hash,
        "source_file_count": int(candidate_verification.get("source_file_count") or 0),
        "observation_count": len(observations),
        "settlement_count": int(performance_summary.get("settlement_count") or 0),
        "outcome_period_count": int(performance_summary.get("outcome_period_count") or 0),
        "shadow_audit_hash": canonical_hash(shadow_audit),
        "performance_summary_hash": canonical_hash(performance_summary),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["rehearsal_hash"] = canonical_hash(payload)
    anchor_material = _local_source_anchor_material(
        candidate_hash=candidate_hash,
        observations=observations,
        settlements=settlements,
        shadow_audit=shadow_audit,
        performance_summary=performance_summary,
    )
    if anchor_material:
        anchor_material["database_sha256"] = restored_database_hashes
    payload[_LOCAL_SOURCE_ANCHOR_MATERIAL_FIELD] = anchor_material
    return payload


def _file_entries(bundle_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for root_name, kind in (
        ("reports", "REPORT"),
        ("databases", "SQLITE"),
        ("source", "SOURCE"),
        ("datasets", "DATASET"),
        ("replay", "REPLAY"),
    ):
        root = bundle_dir / root_name
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(bundle_dir).as_posix()
            records.append({
                "kind": kind,
                "archive_path": relative,
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            })
    return records


def _create_portfolio_evidence_archive_once(
    runtime_dir: Path | str,
    *,
    archive_root: Path | str | None = None,
    generated_at: int | None = None,
    capture_attempt: int = 1,
) -> dict[str, Any]:
    runtime = Path(runtime_dir).resolve()
    live_report_dir = runtime / "reports"
    project_root = runtime.parent
    archive_directory = (
        Path(archive_root).resolve()
        if archive_root
        else runtime / "backups" / DEFAULT_ARCHIVE_DIRECTORY
    )
    archive_directory.mkdir(parents=True, exist_ok=True)
    stamp = int(generated_at if generated_at is not None else time.time_ns() // 1_000_000)
    temporary_bundle = archive_directory / f".pending-{stamp}-{uuid.uuid4().hex}"
    published_bundle: Path | None = None
    temporary_bundle.mkdir(parents=True, exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix="hakimi-pack-stage-") as stage:
            stage_reports, pack, backtest_bundle, detached_artifacts = _stage_consistent_pack(
                live_report_dir,
                Path(stage),
                generated_at=stamp,
                max_attempts=1,
            )
            report_dir = temporary_bundle / "reports"
            shutil.copytree(stage_reports, report_dir)
        candidate_hash = str(dict(pack.get("candidate") or {}).get("candidate_hash") or "")
        _copy_optional_reports(live_report_dir, report_dir, candidate_hash)

        candidate_name = _safe_filename(dict(pack.get("artifacts") or {}).get("candidate", {}).get("file"))
        candidate = _read_json(report_dir / candidate_name)
        source_records = _copy_candidate_sources(candidate, project_root, temporary_bundle / "source")
        bundle_members = list(dict(backtest_bundle.get("manifest") or {}).get("members") or [])
        research_record = next(
            (
                dict(item or {})
                for item in bundle_members
                if dict(item or {}).get("role") == "RESEARCH_REPORT"
            ),
            {},
        )
        research_name = _safe_filename(research_record.get("file"))
        replay_bundle = stage_portfolio_backtest_replay_bundle(
            temporary_bundle,
            source_report_path=report_dir / research_name,
            source_report_archive_path=f"reports/{research_name}",
        )
        database_records = [
            backup_sqlite_database(runtime / name, temporary_bundle / "databases" / name)
            for name in CRITICAL_DATABASES
        ]
        rehearsal_result = _restore_rehearsal(
            temporary_bundle,
            pack,
            detached_artifacts=detached_artifacts,
            expected_database_sha256={
                str(item.get("source_name") or ""): str(item.get("sha256") or "")
                for item in database_records
            },
        )
        rehearsal = _public_restore_rehearsal(rehearsal_result)
        if rehearsal.get("status") != "PASS":
            raise ValueError(f"restore_rehearsal_blocked:{rehearsal.get('blockers')}")
        file_entries = _file_entries(temporary_bundle)
        manifest = {
            "schema_version": PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION,
            "status": "ARCHIVE_READY",
            "generated_at": stamp,
            "generated_at_utc": datetime.fromtimestamp(stamp / 1000.0, tz=timezone.utc).isoformat(),
            "capture_attempt": max(int(capture_attempt), 1),
            "bundle_id": f"{stamp}-{candidate_hash[:12]}",
            "candidate_hash": candidate_hash,
            "backtest_bundle": backtest_bundle,
            "database_snapshots": database_records,
            "source_file_count": len(source_records),
            "backtest_replay": replay_bundle,
            "file_entries": file_entries,
            "restore_rehearsal": rehearsal,
            "retention_policy": "APPEND_ONLY_NO_AUTOMATIC_DELETION",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        manifest["manifest_hash"] = canonical_hash(manifest)
        _atomic_write_json(temporary_bundle / "manifest.json", manifest)
        verification = verify_portfolio_evidence_archive(temporary_bundle)
        if verification.get("status") != "PASS":
            raise ValueError(f"staged_archive_verification_blocked:{verification.get('blockers')}")
        final_bundle = archive_directory / (
            f"portfolio-forward-{stamp}-{candidate_hash[:12]}-{manifest['manifest_hash'][:12]}"
        )
        if final_bundle.exists():
            raise FileExistsError(final_bundle)
        temporary_bundle.replace(final_bundle)
        published_bundle = final_bundle
        published_verification = verify_portfolio_evidence_archive(final_bundle)
        if published_verification.get("status") != "PASS":
            raise ValueError(f"published_archive_verification_blocked:{published_verification.get('blockers')}")
        return {
            "ok": True,
            "status": "ARCHIVED",
            "bundle_path": str(final_bundle),
            "candidate_hash": candidate_hash,
            "manifest_hash": str(manifest.get("manifest_hash") or ""),
            "pack_hash": str(pack.get("pack_hash") or ""),
            "verification": published_verification,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    except Exception:
        shutil.rmtree(temporary_bundle, ignore_errors=True)
        if published_bundle is not None:
            shutil.rmtree(published_bundle, ignore_errors=True)
        raise


def create_portfolio_evidence_archive(
    runtime_dir: Path | str,
    *,
    archive_root: Path | str | None = None,
    generated_at: int | None = None,
    max_attempts: int = 3,
) -> dict[str, Any]:
    stamp = int(generated_at if generated_at is not None else time.time_ns() // 1_000_000)
    attempt_limit = max(int(max_attempts), 1)
    last_error: Exception | None = None
    for attempt in range(1, attempt_limit + 1):
        try:
            return _create_portfolio_evidence_archive_once(
                runtime_dir,
                archive_root=archive_root,
                generated_at=stamp,
                capture_attempt=attempt,
            )
        except Exception as exc:
            last_error = exc
            if attempt < attempt_limit:
                time.sleep(0.25)
    if last_error is None:
        raise RuntimeError("portfolio_evidence_archive_capture_failed")
    raise last_error


def _verify_portfolio_evidence_archive_impl(bundle_dir: Path | str) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    blockers: list[str] = []
    try:
        manifest = _read_strict_bounded_json(
            bundle / "manifest.json",
            maximum_bytes=MAX_PORTFOLIO_EVIDENCE_ARCHIVE_MANIFEST_BYTES,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "BLOCK",
            "blockers": [f"archive_manifest_unavailable:{type(exc).__name__}"],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    clean = dict(manifest)
    expected_hash = str(clean.pop("manifest_hash", "") or "")
    schema_version = str(manifest.get("schema_version") or "")
    replay_required = schema_version in {
        PORTFOLIO_EVIDENCE_ARCHIVE_V2_SCHEMA_VERSION,
        PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION,
    }
    if schema_version not in SUPPORTED_PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSIONS:
        blockers.append("archive_schema_invalid")
    if manifest.get("status") != "ARCHIVE_READY":
        blockers.append("archive_status_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("archive_manifest_hash_invalid")
    entries = list(manifest.get("file_entries") or [])
    if not entries:
        blockers.append("archive_file_inventory_missing")
    declared_paths = [str(dict(item or {}).get("archive_path") or "") for item in entries]
    if len(set(declared_paths)) != len(declared_paths):
        blockers.append("archive_file_inventory_duplicate")
    database_metadata: dict[str, dict[str, Any]] = {}
    for item in entries:
        record = dict(item or {})
        allowed_kinds = {"REPORT", "SQLITE", "SOURCE"}
        if replay_required:
            allowed_kinds.update({"DATASET", "REPLAY"})
        if record.get("kind") not in allowed_kinds:
            blockers.append(f"archive_file_kind_invalid:{record.get('archive_path')}")
        try:
            path = _safe_bundle_path(bundle, str(record.get("archive_path") or ""))
        except (ValueError, OSError):
            blockers.append("archive_file_path_escape")
            continue
        if not path.is_file():
            blockers.append(f"archive_file_missing:{record.get('archive_path')}")
            continue
        if path.stat().st_size != int(record.get("size") or -1):
            blockers.append(f"archive_file_size_mismatch:{record.get('archive_path')}")
        if file_sha256(path) != str(record.get("sha256") or ""):
            blockers.append(f"archive_file_hash_mismatch:{record.get('archive_path')}")
        if record.get("kind") == "SQLITE":
            metadata = _sqlite_metadata(path)
            database_metadata[str(record.get("archive_path") or "")] = metadata
            if metadata.get("quick_check") != ["ok"]:
                blockers.append(f"archive_sqlite_integrity_blocked:{record.get('archive_path')}")
    actual_paths = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    declared_path_set = set(declared_paths)
    if actual_paths != declared_path_set:
        for path in sorted(declared_path_set - actual_paths):
            blockers.append(f"archive_inventory_declared_file_missing:{path}")
        for path in sorted(actual_paths - declared_path_set):
            blockers.append(f"archive_inventory_untracked_file:{path}")
    source_count = sum(1 for item in entries if dict(item or {}).get("kind") == "SOURCE")
    if source_count != int(manifest.get("source_file_count") or 0):
        blockers.append("archive_source_file_count_mismatch")
    entry_by_path = {
        str(dict(item or {}).get("archive_path") or ""): dict(item or {})
        for item in entries
    }
    if replay_required:
        replay_descriptor = dict(manifest.get("backtest_replay") or {})
        expected_replay_kinds = {
            str(replay_descriptor.get("dataset_archive_path") or ""): "DATASET",
            str(replay_descriptor.get("driver_archive_path") or ""): "REPLAY",
            str(replay_descriptor.get("source_report_archive_path") or ""): "REPORT",
        }
        for archive_path, expected_kind in expected_replay_kinds.items():
            if not archive_path or str((entry_by_path.get(archive_path) or {}).get("kind") or "") != expected_kind:
                blockers.append(f"archive_replay_file_kind_mismatch:{expected_kind.lower()}")
        if sum(1 for item in entries if dict(item or {}).get("kind") == "DATASET") != 1:
            blockers.append("archive_replay_dataset_inventory_mismatch")
        if sum(1 for item in entries if dict(item or {}).get("kind") == "REPLAY") != 1:
            blockers.append("archive_replay_driver_inventory_mismatch")
        if schema_version == PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION:
            bundle_manifest = dict(dict(manifest.get("backtest_bundle") or {}).get("manifest") or {})
            research_members = [
                dict(item or {})
                for item in list(bundle_manifest.get("members") or [])
                if dict(item or {}).get("role") == "RESEARCH_REPORT"
            ]
            expected_research_path = (
                f"{PORTFOLIO_ARCHIVE_BACKTEST_BUNDLE_ROOT}/"
                f"{str((research_members[0] if len(research_members) == 1 else {}).get('file') or '')}"
            )
            if (
                len(research_members) != 1
                or str(replay_descriptor.get("source_report_archive_path") or "")
                != expected_research_path
            ):
                blockers.append("archive_replay_research_bundle_binding_mismatch")
    database_snapshots = [dict(item or {}) for item in list(manifest.get("database_snapshots") or [])]
    database_names = [str(item.get("source_name") or "") for item in database_snapshots]
    if sorted(database_names) != sorted(CRITICAL_DATABASES):
        blockers.append("archive_database_inventory_mismatch")
    for snapshot in database_snapshots:
        name = str(snapshot.get("source_name") or "")
        archive_path = str(snapshot.get("archive_path") or "")
        expected_path = f"databases/{name}"
        entry = entry_by_path.get(archive_path) or {}
        if archive_path != expected_path:
            blockers.append(f"archive_database_path_mismatch:{name}")
        if entry.get("kind") != "SQLITE":
            blockers.append(f"archive_database_file_entry_missing:{name}")
        if str(entry.get("sha256") or "") != str(snapshot.get("sha256") or ""):
            blockers.append(f"archive_database_hash_binding_mismatch:{name}")
        if int(entry.get("size") or -1) != int(snapshot.get("size") or -2):
            blockers.append(f"archive_database_size_binding_mismatch:{name}")
        actual_metadata = database_metadata.get(archive_path) or {}
        for key in ("quick_check", "journal_mode", "tables", "row_counts"):
            if actual_metadata.get(key) != snapshot.get(key):
                blockers.append(f"archive_database_metadata_mismatch:{name}:{key}")
    replay_verification: dict[str, Any] = {}
    if replay_required:
        replay_verification = verify_portfolio_backtest_replay_bundle(bundle, replay_descriptor)
        if replay_verification.get("status") != "PASS":
            blockers.extend(
                f"backtest_replay:{item}"
                for item in replay_verification.get("blockers") or ["replay_verification_blocked"]
            )
    rehearsal: dict[str, Any] = {}
    local_source_anchor_material: dict[str, Any] = {}
    try:
        detached_artifacts: Any = None
        backtest_bundle_verification: dict[str, Any] = {}
        if schema_version == PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION:
            backtest_bundle_verification = _load_archived_backtest_bundle(
                bundle,
                manifest.get("backtest_bundle"),
            )
            if backtest_bundle_verification.get("status") != "PASS":
                blockers.extend(backtest_bundle_verification.get("blockers") or [])
            pack = dict(backtest_bundle_verification.get("pack") or {})
            detached_artifacts = backtest_bundle_verification.get("detached_artifacts")
            pack_verification = dict(
                backtest_bundle_verification.get("bundle_verification") or {}
            )
        else:
            pack_path = _safe_bundle_path(
                bundle,
                str(dict(manifest.get("backtest_pack") or {}).get("archive_path") or ""),
            )
            pack = _read_json(pack_path)
            pack_verification = verify_internal_backtest_pack(pack)
            if pack_verification.get("status") != "PASS":
                blockers.extend(
                    f"pack:{item}" for item in pack_verification.get("blockers") or []
                )

        artifact_verification = _pack_artifact_verification(bundle / "reports", pack)
        if artifact_verification.get("status") != "PASS":
            blockers.extend(artifact_verification.get("blockers") or [])
        if (
            schema_version == PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION
            and backtest_bundle_verification.get("status") != "PASS"
        ):
            rehearsal_result: dict[str, Any] = {}
        else:
            rehearsal_result = _restore_rehearsal(
                bundle,
                pack,
                detached_artifacts=detached_artifacts,
                expected_database_sha256={
                    str(item.get("source_name") or ""): str(item.get("sha256") or "")
                    for item in database_snapshots
                },
            )
        local_source_anchor_material = dict(
            rehearsal_result.get(_LOCAL_SOURCE_ANCHOR_MATERIAL_FIELD) or {}
        )
        rehearsal = _public_restore_rehearsal(rehearsal_result)
        recorded_rehearsal = dict(manifest.get("restore_rehearsal") or {})
        if rehearsal.get("status") != "PASS":
            blockers.extend(f"restore:{item}" for item in rehearsal.get("blockers") or [])
        if str(rehearsal.get("rehearsal_hash") or "") != str(recorded_rehearsal.get("rehearsal_hash") or ""):
            blockers.append("restore_rehearsal_hash_mismatch")
        if str(manifest.get("candidate_hash") or "") != str(rehearsal.get("candidate_hash") or ""):
            blockers.append("archive_candidate_hash_mismatch")
        if schema_version != PORTFOLIO_EVIDENCE_ARCHIVE_SCHEMA_VERSION:
            pack_manifest = dict(manifest.get("backtest_pack") or {})
            for key in ("status", "promotion_status", "pack_hash", "evidence_hash"):
                if str(pack_manifest.get(key) or "") != str(pack.get(key) or ""):
                    blockers.append(f"archive_pack_manifest_mismatch:{key}")
        if str(manifest.get("candidate_hash") or "") != str(dict(pack.get("candidate") or {}).get("candidate_hash") or ""):
            blockers.append("archive_pack_candidate_hash_mismatch")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        blockers.append(f"archive_restore_verification_error:{type(exc).__name__}")
        rehearsal = {}
    if authority_violations(manifest):
        blockers.append("archive_contains_execution_authority")
    result = {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": str(manifest.get("candidate_hash") or ""),
        "manifest_hash": expected_hash,
        "file_count": len(entries),
        "restore_rehearsal_status": str(rehearsal.get("status") or "BLOCK"),
        "backtest_replay_status": str(
            replay_verification.get("status")
            or (
                "NOT_REQUIRED_FOR_V1"
                if schema_version == PORTFOLIO_EVIDENCE_ARCHIVE_V1_SCHEMA_VERSION
                else "BLOCK"
            )
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if not blockers:
        result["local_source_anchor"] = _local_source_anchor_for_verified_archive(
            manifest=manifest,
            manifest_hash=expected_hash,
            database_snapshots=database_snapshots,
            material=local_source_anchor_material,
        )
    return result


def verify_portfolio_evidence_archive(bundle_dir: Path | str) -> dict[str, Any]:
    """Verify one archive without allowing memory exhaustion to escape.

    A real process-wide OOM cannot be made recoverable in pure Python, but the
    public verifier still has a stable, path-free fail-closed contract when a
    bounded parser or a later semantic step reports ``MemoryError``.
    """

    try:
        return _verify_portfolio_evidence_archive_impl(bundle_dir)
    except MemoryError:
        return {
            "status": "BLOCK",
            "blockers": ["archive_verification_memory_exhausted"],
            "paper_authorized": False,
            "live_order_allowed": False,
        }


def build_portfolio_backup_status(
    *,
    generated_at: int,
    result: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> dict[str, Any]:
    archive_result = dict(result or {})
    archive_verification = dict(archive_result.get("verification") or {})
    candidate_hash = str(archive_result.get("candidate_hash") or "")
    manifest_hash = str(archive_result.get("manifest_hash") or "")
    pack_hash = str(archive_result.get("pack_hash") or "")
    bundle_path = str(archive_result.get("bundle_path") or "")
    result_blockers = list(dict.fromkeys(
        str(item)[:500]
        for item in list(archive_verification.get("blockers") or [])
        if str(item)
    ))

    raw_anchor = archive_verification.get("local_source_anchor")
    raw_anchor_verification = verify_portfolio_forward_local_source_anchor(raw_anchor)
    if raw_anchor_verification.get("status") == "PASS":
        local_source_anchor = dict(raw_anchor)
    else:
        local_source_anchor = build_portfolio_forward_local_source_anchor_not_available(
            reason="CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE",
            candidate_hash=(
                candidate_hash
                if len(candidate_hash) == 64
                and all(character in "0123456789abcdef" for character in candidate_hash)
                else ""
            ),
            archive_manifest_hash=(
                manifest_hash
                if len(manifest_hash) == 64
                and all(character in "0123456789abcdef" for character in manifest_hash)
                else ""
            ),
            archive_generated_at=(
                int(generated_at)
                if isinstance(generated_at, int)
                and not isinstance(generated_at, bool)
                and generated_at >= 0
                else 0
            ),
        )
        if raw_anchor is not None:
            result_blockers.append("backup_local_source_anchor_invalid")

    anchor_verification = verify_portfolio_forward_local_source_anchor(local_source_anchor)
    anchor_bound = (
        anchor_verification.get("status") == "PASS"
        and str(local_source_anchor.get("candidate_hash") or "") == candidate_hash
        and str(local_source_anchor.get("archive_manifest_hash") or "") == manifest_hash
        and local_source_anchor.get("archive_generated_at") == generated_at
    )
    if archive_verification.get("status") == "PASS" and not anchor_bound:
        result_blockers.append("backup_local_source_anchor_binding_invalid")
    archive_identity_bound = (
        bool(bundle_path)
        and all(
            len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
            for value in (candidate_hash, manifest_hash, pack_hash)
        )
    )
    generated_timestamp_valid = (
        isinstance(generated_at, int)
        and not isinstance(generated_at, bool)
        and 0 < generated_at <= 9_007_199_254_740_991
    )
    if archive_verification.get("status") == "PASS" and not archive_identity_bound:
        result_blockers.append("backup_archive_identity_binding_invalid")
    if archive_verification.get("status") == "PASS" and not generated_timestamp_valid:
        result_blockers.append("backup_generated_at_invalid")
    result_blockers = list(dict.fromkeys(result_blockers))

    success = bool(
        archive_result.get("status") == "ARCHIVED"
        and archive_verification.get("status") == "PASS"
        and anchor_bound
        and archive_identity_bound
        and generated_timestamp_valid
        and not result_blockers
        and error is None
    )
    if not success and not result_blockers:
        result_blockers.append(
            f"backup_capture_failed:{type(error).__name__}"
            if error
            else "backup_result_unavailable"
        )
    payload = {
        "schema_version": PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
        "status": "PASS" if success else "BLOCK",
        "severity": "INFO" if success else "CRITICAL",
        "generated_at": generated_at if generated_timestamp_valid else 0,
        "candidate_hash": candidate_hash,
        "bundle_path": bundle_path,
        "manifest_hash": manifest_hash,
        "pack_hash": pack_hash,
        "verification_status": str(archive_verification.get("status") or "BLOCK"),
        "blockers": result_blockers,
        "error_type": type(error).__name__ if error else "",
        "error": str(error or "")[:500],
        "local_source_anchor": local_source_anchor,
        "backup_only": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    condition = {
        "status": payload["status"],
        "candidate_hash": payload["candidate_hash"],
        "blockers": payload["blockers"],
        "error_type": payload["error_type"],
        "error": payload["error"],
        "local_source_anchor_status": local_source_anchor["status"],
        "local_source_anchor_hash": local_source_anchor["anchor_hash"],
    }
    payload["alert_condition_hash"] = canonical_hash(condition)
    payload["status_hash"] = canonical_hash(payload)
    return payload


def record_portfolio_backup_status(
    *,
    status_path: Path | str,
    alert_path: Path | str,
    payload: dict[str, Any],
) -> None:
    status_file = Path(status_path)
    alert_file = Path(alert_path)
    previous: dict[str, Any] = {}
    previous_artifact = read_forward_json_artifact(
        status_file,
        byte_limit=MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
        size_limit_blocker="backup_previous_status_size_limit_exceeded",
    )
    if previous_artifact.status == "PASS":
        decoded = dict(previous_artifact.payload)
        if verify_portfolio_backup_status(decoded).get("status") == "PASS":
            previous = decoded
    _atomic_write_json(status_file, payload)
    current_status = str(payload.get("status") or "BLOCK")
    changed_block = (
        current_status == "BLOCK"
        and str(payload.get("alert_condition_hash") or "")
        != str(previous.get("alert_condition_hash") or "")
    )
    recovered = current_status == "PASS" and str(previous.get("status") or "") == "BLOCK"
    if not (changed_block or recovered):
        return
    alert = {
        "schema_version": PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
        "event_type": "PORTFOLIO_FORWARD_BACKUP_RECOVERY" if recovered else "PORTFOLIO_FORWARD_BACKUP_ALERT",
        "generated_at": int(payload.get("generated_at") or 0),
        "candidate_hash": str(payload.get("candidate_hash") or ""),
        "condition_hash": str(payload.get("alert_condition_hash") or ""),
        "blockers": list(payload.get("blockers") or []),
        "error_type": str(payload.get("error_type") or ""),
        "error": str(payload.get("error") or ""),
        "backup_only": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    alert["alert_hash"] = canonical_hash(alert)
    alert_file.parent.mkdir(parents=True, exist_ok=True)
    with alert_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(alert, ensure_ascii=False, sort_keys=True) + "\n")
