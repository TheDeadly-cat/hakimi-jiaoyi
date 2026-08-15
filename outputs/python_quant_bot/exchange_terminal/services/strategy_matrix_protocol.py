from __future__ import annotations

from contextlib import contextmanager
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any, Callable, Iterator

from .implementation_manifest import (
    IMPLEMENTATION_MANIFEST_SCHEMA_VERSION,
    IMPLEMENTATION_VERIFICATION_POLICY,
    verify_embedded_implementation_manifest,
    verify_implementation_manifest,
)
from .research_exposure import prior_symbol_exposure
from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable
from .strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    verify_strategy_hypothesis_preregistration,
)
from .strategy_cost_stress import COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION
from .strategy_chronological_slice import (
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
)
from .strategy_frozen_evaluation_replay import (
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
)
from .strategy_preregistered_failure_admission import (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    _build_strategy_preregistered_failure_admission_v3_from_live_registry,
)
from .strategy_research_protocol_artifact import (
    verify_bound_strategy_research_protocol_artifact,
    verify_strategy_research_protocol_artifact_binding,
)
from .strategy_research_search_lineage import (
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
    build_strategy_research_registry_anchor,
    build_strategy_research_search_lineage,
    normalize_search_family_id,
    verify_strategy_research_registry_anchor,
    verify_strategy_research_search_lineage,
)
from .trusted_clock import verify_trusted_clock_attestation


STRATEGY_MATRIX_PROTOCOL_LEGACY_VERSION = "strategy-matrix-protocol-v1"
STRATEGY_MATRIX_PROTOCOL_VERSION = "strategy-matrix-protocol-v2"
STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION = "strategy-matrix-protocol-v3"
STRATEGY_MATRIX_EXPOSURE_VERSION = "strategy-matrix-exposure-audit-v1"
STRATEGY_MATRIX_REGISTRY_VERSION = "strategy-matrix-registry-v1"
STRATEGY_MATRIX_CLAIM_VERSION = "strategy-matrix-single-use-claim-v1"
STRATEGY_MATRIX_CLAIM_VERSION_V2 = "strategy-matrix-single-use-claim-v2"
STRATEGY_MATRIX_COMPLETION_VERSION = "strategy-matrix-completion-v1"
STRATEGY_MATRIX_SOURCE_SNAPSHOT_VERSION = "strategy-matrix-source-snapshot-v1"
STRATEGY_RESEARCH_CANONICAL_REGISTRY_BASENAME = (
    "strategy_research_registrations.sqlite3"
)
_NESTED_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS = frozenset({
    6,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
})
_HYPOTHESIS_BOUND_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS = frozenset({
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION,
})


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _embedded_hash_matches(payload: Any, field: str) -> bool:
    if not isinstance(payload, dict):
        return False
    clean = dict(payload)
    expected = str(clean.pop(field, "") or "")
    return bool(expected) and canonical_hash(clean) == expected


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def verify_strategy_research_canonical_registry_path(
    registry_path: Path | str,
    *,
    active_runtime_root: Path | str | None,
) -> dict[str, Any]:
    """Verify the one externally anchored schema-14 research registry path."""

    blockers: list[str] = []
    raw_path = Path(registry_path)
    raw_root = Path(active_runtime_root) if active_runtime_root is not None else None
    if raw_root is None:
        blockers.append("strategy_research_active_runtime_root_missing")
        expected = None
    elif not raw_root.is_absolute():
        blockers.append("strategy_research_active_runtime_root_relative")
        expected = None
    else:
        expected = raw_root / STRATEGY_RESEARCH_CANONICAL_REGISTRY_BASENAME
    if not raw_path.is_absolute():
        blockers.append("strategy_research_registry_path_relative")
    if any(part in {".", ".."} for part in raw_path.parts):
        blockers.append("strategy_research_registry_path_alias")
    if raw_root is not None and any(
        part in {".", ".."} for part in raw_root.parts
    ):
        blockers.append("strategy_research_active_runtime_root_alias")

    def lexical(path: Path) -> str:
        return os.path.normcase(os.path.normpath(str(path)))

    if expected is not None and lexical(raw_path) != lexical(expected):
        blockers.append("strategy_research_registry_path_noncanonical")
    try:
        resolved_path = raw_path.resolve(strict=False)
        resolved_root = raw_root.resolve(strict=False) if raw_root is not None else None
        resolved_expected = (
            resolved_root / STRATEGY_RESEARCH_CANONICAL_REGISTRY_BASENAME
            if resolved_root is not None
            else None
        )
    except OSError:
        blockers.append("strategy_research_registry_path_unresolvable")
        resolved_path = raw_path
        resolved_root = raw_root
        resolved_expected = expected
    if (
        expected is not None
        and resolved_expected is not None
        and lexical(resolved_path) != lexical(resolved_expected)
    ):
        blockers.append("strategy_research_registry_path_resolved_mismatch")
    if (
        raw_root is not None
        and resolved_root is not None
        and lexical(raw_root) != lexical(resolved_root)
    ):
        blockers.append("strategy_research_active_runtime_root_reparse")

    paths_to_check: list[Path] = []
    if raw_root is not None:
        paths_to_check.append(raw_root)
    if expected is not None:
        paths_to_check.append(expected)
    for candidate in paths_to_check:
        if not candidate.exists() and not candidate.is_symlink():
            continue
        try:
            is_junction = bool(
                getattr(candidate, "is_junction", lambda: False)()
            )
            attributes = int(
                getattr(candidate.lstat(), "st_file_attributes", 0) or 0
            )
        except OSError:
            blockers.append("strategy_research_registry_path_metadata_unavailable")
            continue
        if candidate.is_symlink() or is_junction or attributes & 0x400:
            blockers.append("strategy_research_registry_path_reparse_point")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "active_runtime_root": (
            str(resolved_root) if resolved_root is not None else ""
        ),
        "canonical_registry_path": (
            str(resolved_expected) if resolved_expected is not None else ""
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_nested_strategy_research_variants(
    batch_spec: dict[str, Any],
) -> list[str]:
    """Validate the frozen pre-selection trial registry for every nested run."""

    raw_variants = batch_spec.get("variants")
    if not isinstance(raw_variants, list):
        return ["matrix_protocol_variants_type_invalid"]
    if not raw_variants:
        return ["matrix_protocol_variants_missing"]

    strategies = [
        str(item).strip().lower()
        for item in _sequence(batch_spec.get("strategies"))
        if isinstance(item, str) and item.strip()
    ]
    strategy_set = set(strategies)
    seen_variant_ids: set[str] = set()
    covered_strategies: set[str] = set()
    blockers: list[str] = []
    required_fields = {
        "strategy_id",
        "variant_label",
        "variant_id",
        "params",
        "param_hash",
        "implementation_fingerprint",
        "risk_profile",
        "risk",
        "risk_hash",
    }
    for index, raw_variant in enumerate(raw_variants):
        identity = f"index-{index}"
        if not isinstance(raw_variant, dict):
            blockers.append(f"matrix_protocol_variant_type_invalid:{identity}")
            continue
        missing = sorted(required_fields - set(raw_variant))
        if missing:
            blockers.append(
                f"matrix_protocol_variant_fields_missing:{identity}:"
                + ",".join(missing)
            )

        strategy_id = str(raw_variant.get("strategy_id") or "").strip().lower()
        variant_id = str(raw_variant.get("variant_id") or "").strip()
        variant_label = str(raw_variant.get("variant_label") or "").strip()
        if not strategy_id or strategy_id not in strategy_set:
            blockers.append(f"matrix_protocol_variant_strategy_invalid:{identity}")
        else:
            covered_strategies.add(strategy_id)
        if not variant_id:
            blockers.append(f"matrix_protocol_variant_id_invalid:{identity}")
        elif variant_id in seen_variant_ids:
            blockers.append(f"matrix_protocol_variant_id_duplicate:{variant_id}")
        else:
            seen_variant_ids.add(variant_id)
            identity = variant_id
        if not variant_label:
            blockers.append(f"matrix_protocol_variant_label_invalid:{identity}")

        params = raw_variant.get("params")
        if not isinstance(params, dict):
            blockers.append(f"matrix_protocol_variant_params_invalid:{identity}")
        elif str(raw_variant.get("param_hash") or "") != canonical_hash(params):
            blockers.append(f"matrix_protocol_variant_param_hash_invalid:{identity}")
        if not str(raw_variant.get("implementation_fingerprint") or "").strip():
            blockers.append(
                f"matrix_protocol_variant_implementation_fingerprint_invalid:{identity}"
            )

        risk = raw_variant.get("risk")
        risk_profile = raw_variant.get("risk_profile")
        if not isinstance(risk, dict):
            blockers.append(f"matrix_protocol_variant_risk_invalid:{identity}")
        if not isinstance(risk_profile, dict):
            blockers.append(f"matrix_protocol_variant_risk_profile_invalid:{identity}")
            continue
        if (
            risk_profile.get("version") != "strategy-risk-profile-v1"
            or str(risk_profile.get("strategy_id") or "").strip().lower()
            != strategy_id
            or not str(risk_profile.get("profile_id") or "").strip()
            or not str(risk_profile.get("rationale") or "").strip()
            or risk_profile.get("risk") != risk
        ):
            blockers.append(
                f"matrix_protocol_variant_risk_profile_contract_invalid:{identity}"
            )
        profile_content = {
            key: value for key, value in risk_profile.items() if key != "risk_hash"
        }
        risk_hash = str(raw_variant.get("risk_hash") or "")
        if (
            not _valid_sha256(risk_hash)
            or str(risk_profile.get("risk_hash") or "") != risk_hash
            or canonical_hash(profile_content) != risk_hash
        ):
            blockers.append(f"matrix_protocol_variant_risk_hash_invalid:{identity}")

    missing_strategies = sorted(strategy_set - covered_strategies)
    if missing_strategies:
        blockers.append(
            "matrix_protocol_variant_strategy_coverage_missing:"
            + ",".join(missing_strategies)
        )
    return list(dict.fromkeys(blockers))


def _strict_positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _verify_embedded_implementation_manifest(manifest: Any) -> dict[str, Any]:
    return verify_embedded_implementation_manifest(manifest)


def build_implementation_source_snapshot(manifest: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for index, item in enumerate(_sequence(manifest.get("files"))):
        row = _mapping(item)
        path = Path(str(row.get("path") or "")).resolve()
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"implementation source unavailable at snapshot:{path}") from exc
        digest = hashlib.sha256(raw).hexdigest()
        if digest != str(row.get("sha256") or "") or len(raw) != row.get("size"):
            raise ValueError(f"implementation source changed before snapshot:{path}")
        records.append({
            "index": index,
            "path": str(path),
            "sha256": digest,
            "size": len(raw),
            "content_base64": base64.b64encode(raw).decode("ascii"),
        })
    if not records:
        raise ValueError("implementation source snapshot is empty")
    snapshot = {
        "schema_version": STRATEGY_MATRIX_SOURCE_SNAPSHOT_VERSION,
        "implementation_fingerprint": str(manifest.get("fingerprint") or ""),
        "files": records,
        "file_count": len(records),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    snapshot["snapshot_hash"] = canonical_hash(snapshot)
    return snapshot


def verify_implementation_source_snapshot(
    snapshot: Any,
    *,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(snapshot)
    records = _sequence(payload.get("files"))
    manifest_files = _sequence(manifest.get("files"))
    if payload.get("schema_version") != STRATEGY_MATRIX_SOURCE_SNAPSHOT_VERSION:
        blockers.append("implementation_source_snapshot_schema_invalid")
    if not _embedded_hash_matches(payload, "snapshot_hash"):
        blockers.append("implementation_source_snapshot_hash_invalid")
    if str(payload.get("implementation_fingerprint") or "") != str(manifest.get("fingerprint") or ""):
        blockers.append("implementation_source_snapshot_fingerprint_mismatch")
    if payload.get("file_count") != len(records) or len(records) != len(manifest_files) or not records:
        blockers.append("implementation_source_snapshot_count_mismatch")
    for index, expected in enumerate(manifest_files):
        if index >= len(records):
            break
        record = _mapping(records[index])
        expected_row = _mapping(expected)
        try:
            raw = base64.b64decode(str(record.get("content_base64") or ""), validate=True)
        except (ValueError, UnicodeError):
            raw = b""
            blockers.append(f"implementation_source_snapshot_encoding_invalid:{index}")
        if (
            record.get("index") != index
            or str(record.get("path") or "") != str(expected_row.get("path") or "")
            or str(record.get("sha256") or "") != str(expected_row.get("sha256") or "")
            or record.get("size") != expected_row.get("size")
            or len(raw) != expected_row.get("size")
            or hashlib.sha256(raw).hexdigest() != str(expected_row.get("sha256") or "")
        ):
            blockers.append(f"implementation_source_snapshot_file_mismatch:{index}")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("implementation_source_snapshot_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "snapshot_hash": str(payload.get("snapshot_hash") or ""),
        "file_count": len(records),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_holdout_exposure_audit(
    exposure: Any,
    *,
    expected_symbols: set[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(exposure)
    symbols_raw = payload.get("symbols")
    exposed_raw = payload.get("exposed_symbols")
    symbols = {
        str(symbol or "").strip().upper()
        for symbol in _sequence(symbols_raw)
        if str(symbol or "").strip()
    }
    if not isinstance(exposure, dict):
        blockers.append("holdout_exposure_audit_type_invalid")
    if not _embedded_hash_matches(payload, "audit_hash"):
        blockers.append("holdout_exposure_audit_hash_invalid")
    if symbols != expected_symbols:
        blockers.append("holdout_exposure_symbol_mismatch")
    if not isinstance(exposed_raw, list):
        blockers.append("holdout_exposed_symbols_type_invalid")
    if (
        payload.get("status") != "PASS"
        or payload.get("evaluated_before_data_load") is not True
        or _sequence(exposed_raw)
    ):
        blockers.append("holdout_not_blind")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("holdout_exposure_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "audit_hash": str(payload.get("audit_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _matrix_report_exposure(report_dir: Path) -> dict[str, list[dict[str, Any]]]:
    exposure: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(report_dir.glob("strategy_matrix_*.json")):
        payload = _read_json(path)
        if not payload:
            continue
        manifests = payload.get("dataset_manifest") if isinstance(payload.get("dataset_manifest"), list) else []
        cells = [
            *list(payload.get("selection_cells") or []),
            *list(payload.get("confirmation_cells") or []),
        ]
        symbols = {
            str(item.get("symbol") or "").upper()
            for item in [*manifests, *cells]
            if isinstance(item, dict) and str(item.get("symbol") or "").strip()
        }
        for symbol in sorted(symbols):
            exposure.setdefault(symbol, []).append({
                "kind": "STRATEGY_MATRIX_REPORT",
                "path": str(path.resolve()),
                "batch_run_hash": str(payload.get("batch_run_hash") or ""),
            })
    return exposure


def _sqlite_symbol_exposure(runtime_dir: Path, symbols: list[str]) -> dict[str, list[dict[str, Any]]]:
    wanted = set(symbols)
    exposure: dict[str, list[dict[str, Any]]] = {}
    database_paths = {
        path
        for pattern in ("*.sqlite", "*.sqlite3", "*.db")
        for path in runtime_dir.rglob(pattern)
        if path.is_file()
    }
    for path in sorted(database_paths):
        try:
            connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=3)
        except sqlite3.Error:
            continue
        try:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (table_name,) in tables:
                safe_table = str(table_name).replace('"', '""')
                columns = connection.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
                for column in columns:
                    column_name = str(column[1] or "")
                    if "symbol" not in column_name.lower():
                        continue
                    safe_column = column_name.replace('"', '""')
                    for symbol in sorted(wanted):
                        try:
                            row = connection.execute(
                                f'SELECT 1 FROM "{safe_table}" '
                                f'WHERE UPPER(TRIM(CAST("{safe_column}" AS TEXT))) = ? LIMIT 1',
                                (symbol,),
                            ).fetchone()
                        except sqlite3.Error:
                            break
                        if row:
                            exposure.setdefault(symbol, []).append({
                                "kind": "RUNTIME_SQLITE",
                                "path": str(path.resolve()),
                                "location": f"{table_name}.{column_name}",
                            })
        finally:
            connection.close()
    return exposure


def _service_log_exposure(runtime_dir: Path, symbols: list[str]) -> dict[str, list[dict[str, Any]]]:
    exposure: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(runtime_dir.rglob("service_*.log")):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for symbol in symbols:
            escaped = re.escape(symbol)
            patterns = (
                rf"(?:[?&]symbol=){escaped}(?:[&\s]|$)",
                rf'"symbol"\s*:\s*"{escaped}"',
            )
            if not any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in patterns):
                continue
            exposure.setdefault(symbol, []).append({
                "kind": "SERVICE_REQUEST_LOG",
                "path": str(path.resolve()),
            })
    return exposure


def audit_strategy_matrix_holdout_exposure(
    report_dir: Path | str,
    runtime_dir: Path | str,
    symbols: list[str],
) -> dict[str, Any]:
    reports = Path(report_dir)
    runtime = Path(runtime_dir)
    normalized = sorted({str(symbol or "").strip().upper() for symbol in symbols if str(symbol or "").strip()})
    evidence: dict[str, list[dict[str, Any]]] = {}

    prior = prior_symbol_exposure(reports)
    matrix = _matrix_report_exposure(reports)
    sqlite_hits = _sqlite_symbol_exposure(runtime, normalized)
    log_hits = _service_log_exposure(runtime, normalized)
    for symbol in normalized:
        rows: list[dict[str, Any]] = []
        rows.extend({"kind": "PRIOR_RESEARCH_REPORT", **item} for item in prior.get(symbol, []))
        rows.extend(matrix.get(symbol, []))
        rows.extend(sqlite_hits.get(symbol, []))
        rows.extend(log_hits.get(symbol, []))
        if rows:
            evidence[symbol] = rows

    exposed = sorted(evidence)
    payload = {
        "schema_version": STRATEGY_MATRIX_EXPOSURE_VERSION,
        "status": "PASS" if normalized and not exposed else "BLOCK",
        "evaluated_before_data_load": True,
        "symbols": normalized,
        "exposed_symbols": exposed,
        "evidence": evidence,
        "blockers": (
            [f"holdout_previously_exposed:{symbol}" for symbol in exposed]
            if exposed
            else ([] if normalized else ["holdout_symbols_missing"])
        ),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["audit_hash"] = canonical_hash(payload)
    return payload


def build_strategy_matrix_protocol(
    *,
    registration_id: str,
    research_generation: str,
    batch_spec: dict[str, Any],
    implementation_manifest: dict[str, Any],
    exposure_audit: dict[str, Any],
    registration_clock_attestation: dict[str, Any],
    expires_at_ms: int,
    registry_path: Path | str,
    protocol_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registered_at_ms = int(registration_clock_attestation.get("attested_now_ms") or 0)
    source_snapshot = build_implementation_source_snapshot(implementation_manifest)
    payload = {
        "schema_version": (
            STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION
            if protocol_artifact is not None
            else STRATEGY_MATRIX_PROTOCOL_VERSION
        ),
        "registration_id": str(registration_id or "").strip(),
        "research_generation": str(research_generation or "").strip(),
        "registry_path": str(Path(registry_path).resolve()),
        "selection_test_policy": "BLIND_ONCE",
        "single_use": True,
        "registered_at_ms": registered_at_ms,
        "expires_at_ms": int(expires_at_ms),
        "registration_clock_attestation": dict(registration_clock_attestation or {}),
        "batch_spec": dict(batch_spec or {}),
        "batch_spec_hash": canonical_hash(batch_spec or {}),
        "implementation_manifest": dict(implementation_manifest or {}),
        "implementation_fingerprint": str(implementation_manifest.get("fingerprint") or ""),
        "implementation_source_snapshot": source_snapshot,
        "holdout_exposure_audit": dict(exposure_audit or {}),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if protocol_artifact is not None:
        payload["protocol_artifact"] = dict(protocol_artifact)
    payload["protocol_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_matrix_protocol(
    protocol: Any,
    *,
    verification_at_ms: int = 0,
    enforce_not_expired: bool = False,
    verify_current_implementation: bool = True,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(protocol, dict):
        blockers.append("matrix_protocol_type_invalid")
        protocol = {}
    clean = dict(protocol)
    expected_hash = str(clean.pop("protocol_hash", "") or "")
    protocol_schema = str(protocol.get("schema_version") or "")
    if protocol_schema not in {
        STRATEGY_MATRIX_PROTOCOL_LEGACY_VERSION,
        STRATEGY_MATRIX_PROTOCOL_VERSION,
    STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION,
    }:
        blockers.append("matrix_protocol_schema_invalid")
    if not str(protocol.get("registration_id") or ""):
        blockers.append("matrix_protocol_registration_id_missing")
    if not str(protocol.get("research_generation") or ""):
        blockers.append("matrix_protocol_generation_missing")
    registry_path = str(protocol.get("registry_path") or "").strip()
    if not registry_path or not Path(registry_path).is_absolute():
        blockers.append("matrix_protocol_registry_path_invalid")
    if protocol.get("selection_test_policy") != "BLIND_ONCE" or protocol.get("single_use") is not True:
        blockers.append("matrix_protocol_single_use_policy_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("matrix_protocol_hash_invalid")
    if protocol_schema == STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION:
        artifact_binding_verification = verify_strategy_research_protocol_artifact_binding(
            protocol.get("protocol_artifact")
        )
        blockers.extend(
            f"matrix_protocol_artifact:{item}"
            for item in artifact_binding_verification.get("blockers") or []
        )
    else:
        artifact_binding_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if "protocol_artifact" in protocol:
            blockers.append("matrix_protocol_legacy_has_artifact_binding")

    registered_at_ms = protocol.get("registered_at_ms")
    expires_at_ms = protocol.get("expires_at_ms")
    if (
        isinstance(registered_at_ms, bool)
        or not isinstance(registered_at_ms, int)
        or registered_at_ms <= 0
        or isinstance(expires_at_ms, bool)
        or not isinstance(expires_at_ms, int)
        or expires_at_ms <= registered_at_ms
    ):
        blockers.append("matrix_protocol_time_window_invalid")
    elif enforce_not_expired and int(verification_at_ms or _now_ms()) > expires_at_ms:
        blockers.append("matrix_protocol_expired")

    clock = protocol.get("registration_clock_attestation")
    clock_verification = verify_trusted_clock_attestation(clock if isinstance(clock, dict) else {})
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_protocol_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    if isinstance(registered_at_ms, int) and abs(
        registered_at_ms - int((clock or {}).get("attested_now_ms") or 0)
    ) > 5_000:
        blockers.append("matrix_protocol_clock_timestamp_mismatch")

    batch_spec = _mapping(protocol.get("batch_spec"))
    if str(batch_spec.get("schema_version") or "") != "strategy-benchmark-v7":
        blockers.append("matrix_protocol_batch_schema_invalid")
    if str(protocol.get("batch_spec_hash") or "") != canonical_hash(batch_spec):
        blockers.append("matrix_protocol_batch_hash_invalid")
    report_schema_version = batch_spec.get("report_schema_version")
    variants_value = batch_spec.get("variants")
    variant_count = len(variants_value) if isinstance(variants_value, list) else 0
    search_lineage_present = "search_lineage" in batch_spec
    search_lineage_verification = (
        verify_strategy_research_search_lineage(
            batch_spec.get("search_lineage"),
            expected_current_trial_count=variant_count,
        )
        if search_lineage_present else {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "lineage_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    )
    if search_lineage_present and search_lineage_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_protocol_search_lineage:{item}"
            for item in search_lineage_verification.get("blockers") or []
        )
    if (
        report_schema_version == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
        and not search_lineage_present
    ):
        blockers.append("matrix_protocol_search_lineage_required")
    if (
        report_schema_version == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
        and batch_spec.get("workflow") != "NESTED_VARIANT_RESEARCH"
    ):
        blockers.append("matrix_protocol_search_lineage_workflow_invalid")
    if batch_spec.get("workflow") == "NESTED_VARIANT_RESEARCH":
        blockers.extend(_verify_nested_strategy_research_variants(batch_spec))
        if report_schema_version not in _NESTED_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS:
            blockers.append("matrix_protocol_research_report_schema_invalid")
        if (
            report_schema_version
            == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            and Path(registry_path).name
            != STRATEGY_RESEARCH_CANONICAL_REGISTRY_BASENAME
        ):
            blockers.append("matrix_protocol_search_lineage_registry_noncanonical")
        if (
            report_schema_version
            != STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            and search_lineage_present
        ):
            blockers.append("matrix_protocol_legacy_report_has_search_lineage")
        if report_schema_version in _HYPOTHESIS_BOUND_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS:
            hypothesis = batch_spec.get("hypothesis_preregistration")
            hypothesis_verification = verify_strategy_hypothesis_preregistration(
                hypothesis,
                expected_strategy_ids=[
                    str(item or "") for item in _sequence(batch_spec.get("strategies"))
                ],
                expected_research_generation=str(
                    batch_spec.get("research_generation") or ""
                ),
                expected_schema_version=(
                    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                    if report_schema_version
                    == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
                    else (
                        STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
                        if report_schema_version
                        == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                        else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION
                    )
                ),
            )
            blockers.extend(
                f"matrix_protocol_hypothesis:{item}"
                for item in hypothesis_verification.get("blockers") or []
            )
            if str(batch_spec.get("hypothesis_preregistration_hash") or "") != str(
                _mapping(hypothesis).get("hypothesis_hash") or ""
            ):
                blockers.append("matrix_protocol_hypothesis_hash_binding_mismatch")
            if (
                report_schema_version
                == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            ):
                search_lineage_verification = (
                    verify_strategy_research_search_lineage(
                        batch_spec.get("search_lineage"),
                        expected_search_family_id=str(
                            _mapping(hypothesis).get("search_family_id") or ""
                        ),
                        expected_current_trial_count=variant_count,
                    )
                )
                blockers.extend(
                    f"matrix_protocol_search_lineage:{item}"
                    for item in search_lineage_verification.get("blockers") or []
                )
        else:
            hypothesis_verification = {
                "status": "NOT_REQUIRED",
                "blockers": [],
                "hypothesis_hash": "",
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            if (
                "hypothesis_preregistration" in batch_spec
                or "hypothesis_preregistration_hash" in batch_spec
            ):
                blockers.append("matrix_protocol_legacy_schema_has_hypothesis_contract")
    else:
        hypothesis_verification = {
            "status": "NOT_APPLICABLE",
            "blockers": [],
            "hypothesis_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    selection_raw = batch_spec.get("selection_symbols")
    confirmation_raw = batch_spec.get("confirmation_symbols")
    strategies_raw = batch_spec.get("strategies")
    if not isinstance(selection_raw, list):
        blockers.append("matrix_protocol_selection_symbols_type_invalid")
    if not isinstance(confirmation_raw, list):
        blockers.append("matrix_protocol_confirmation_symbols_type_invalid")
    if not isinstance(strategies_raw, list):
        blockers.append("matrix_protocol_strategies_type_invalid")
    selection_symbols = {
        str(symbol or "").strip().upper()
        for symbol in _sequence(selection_raw)
        if str(symbol or "").strip()
    }
    confirmation_symbols = {
        str(symbol or "").strip().upper()
        for symbol in _sequence(confirmation_raw)
        if str(symbol or "").strip()
    }
    if not selection_symbols:
        blockers.append("matrix_protocol_selection_symbols_missing")
    if not confirmation_symbols:
        blockers.append("matrix_protocol_confirmation_symbols_missing")
    if selection_symbols & confirmation_symbols:
        blockers.append("matrix_protocol_symbol_roles_overlap")
    if not _sequence(strategies_raw):
        blockers.append("matrix_protocol_strategies_missing")
    if len(selection_symbols) != len(_sequence(selection_raw)):
        blockers.append("matrix_protocol_selection_symbols_not_unique")
    if len(confirmation_symbols) != len(_sequence(confirmation_raw)):
        blockers.append("matrix_protocol_confirmation_symbols_not_unique")
    if (
        batch_spec.get("research_only") is not True
        or batch_spec.get("paper_authorized") is not False
        or batch_spec.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_protocol_batch_has_execution_authority")
    split_policy = _mapping(batch_spec.get("split_policy"))
    if (
        split_policy.get("schema_version") != "calendar-split-v1"
        or split_policy.get("train_ratio") != 0.50
        or split_policy.get("validation_ratio") != 0.25
        or split_policy.get("minimum_segment_rows") != 120
    ):
        blockers.append("matrix_protocol_split_policy_invalid")
    data_policy = _mapping(batch_spec.get("data_policy"))
    if (
        data_policy.get("timeframe") != "1D"
        or data_policy.get("completed_candles_only") is not True
        or data_policy.get("max_endpoint_skew_days") != 3
        or data_policy.get("frozen_stock_revision_evidence_required") is not True
        or data_policy.get("exact_dataset_snapshot_required") is not True
    ):
        blockers.append("matrix_protocol_data_policy_invalid")
    if protocol_schema in {
        STRATEGY_MATRIX_PROTOCOL_VERSION,
        STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION,
    } and (
        data_policy.get("alignment_schema_version") != "daily-batch-alignment-v2"
        or data_policy.get("max_boundary_skew_days") != 7
    ):
        blockers.append("matrix_protocol_alignment_policy_invalid")

    exposure = _mapping(protocol.get("holdout_exposure_audit"))
    exposure_verification = _verify_holdout_exposure_audit(
        exposure,
        expected_symbols=confirmation_symbols,
    )
    blockers.extend(
        f"matrix_protocol_exposure:{item}"
        for item in exposure_verification.get("blockers") or []
    )

    implementation = _mapping(protocol.get("implementation_manifest"))
    implementation_verification = (
        verify_implementation_manifest(implementation)
        if verify_current_implementation
        else _verify_embedded_implementation_manifest(implementation)
    )
    if implementation_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_protocol_implementation:{item}"
            for item in implementation_verification.get("blockers") or ["verification_blocked"]
        )
    if str(protocol.get("implementation_fingerprint") or "") != str(implementation.get("fingerprint") or ""):
        blockers.append("matrix_protocol_implementation_fingerprint_mismatch")
    source_snapshot_verification = verify_implementation_source_snapshot(
        protocol.get("implementation_source_snapshot"),
        manifest=implementation,
    )
    blockers.extend(
        f"matrix_protocol_source_snapshot:{item}"
        for item in source_snapshot_verification.get("blockers") or []
    )

    if (
        protocol.get("research_only") is not True
        or protocol.get("paper_authorized") is not False
        or protocol.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_protocol_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "registration_id": str(protocol.get("registration_id") or ""),
        "protocol_hash": expected_hash,
        "batch_spec_hash": str(protocol.get("batch_spec_hash") or ""),
        "implementation_verification": implementation_verification,
        "source_snapshot_verification": source_snapshot_verification,
        "hypothesis_preregistration_verification": hypothesis_verification,
        "exposure_verification": exposure_verification,
        "clock_verification": clock_verification,
        "artifact_binding_verification": artifact_binding_verification,
        "search_lineage_verification": search_lineage_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _strategy_research_protocol_artifact_required(protocol: dict[str, Any]) -> bool:
    batch_spec = _mapping(protocol.get("batch_spec"))
    return (
        batch_spec.get("workflow") == "NESTED_VARIANT_RESEARCH"
        and batch_spec.get("report_schema_version")
        in _HYPOTHESIS_BOUND_STRATEGY_RESEARCH_REPORT_SCHEMA_VERSIONS
    )


def _verify_required_strategy_research_protocol_artifact(
    protocol: dict[str, Any],
) -> dict[str, Any]:
    if not _strategy_research_protocol_artifact_required(protocol):
        return {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if protocol.get("schema_version") != STRATEGY_MATRIX_PROTOCOL_ARTIFACT_VERSION:
        return {
            "status": "BLOCK",
            "blockers": ["matrix_protocol_artifact_binding_required"],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    return verify_bound_strategy_research_protocol_artifact(protocol)


def _strategy_research_lineage_claim_required(protocol: dict[str, Any]) -> bool:
    batch_spec = _mapping(protocol.get("batch_spec"))
    return (
        batch_spec.get("workflow") == "NESTED_VARIANT_RESEARCH"
        and batch_spec.get("report_schema_version")
        == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
    )


def verify_strategy_matrix_claim(
    claim: Any,
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(claim)
    protocol_verification = verify_strategy_matrix_protocol(
        protocol,
        verify_current_implementation=False,
    )
    if protocol_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_claim_protocol:{item}"
            for item in protocol_verification.get("blockers") or []
        )
    if not isinstance(claim, dict):
        blockers.append("matrix_claim_type_invalid")
    lineage_claim_required = _strategy_research_lineage_claim_required(protocol)
    expected_claim_schema = (
        STRATEGY_MATRIX_CLAIM_VERSION_V2
        if lineage_claim_required
        else STRATEGY_MATRIX_CLAIM_VERSION
    )
    if payload.get("schema_version") != expected_claim_schema:
        blockers.append("matrix_claim_schema_invalid")
    if payload.get("status") != "CLAIMED_FOR_SINGLE_RUN":
        blockers.append("matrix_claim_status_invalid")
    if not _embedded_hash_matches(payload, "claim_hash"):
        blockers.append("matrix_claim_hash_invalid")
    if str(payload.get("registration_id") or "") != str(protocol.get("registration_id") or ""):
        blockers.append("matrix_claim_registration_mismatch")
    if str(payload.get("protocol_hash") or "") != str(protocol.get("protocol_hash") or ""):
        blockers.append("matrix_claim_protocol_hash_mismatch")
    if str(payload.get("implementation_fingerprint") or "") != str(
        protocol.get("implementation_fingerprint") or ""
    ):
        blockers.append("matrix_claim_implementation_mismatch")

    registered_at = _strict_positive_int(payload.get("registered_at_ms"))
    started_at = _strict_positive_int(payload.get("started_at_ms"))
    protocol_registered_at = _strict_positive_int(protocol.get("registered_at_ms"))
    expires_at = _strict_positive_int(protocol.get("expires_at_ms"))
    if registered_at is None or started_at is None:
        blockers.append("matrix_claim_timestamp_invalid")
    elif (
        protocol_registered_at is None
        or expires_at is None
        or registered_at != protocol_registered_at
        or started_at < registered_at
        or started_at > expires_at
    ):
        blockers.append("matrix_claim_temporal_order_invalid")

    clock = _mapping(payload.get("clock_attestation"))
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_claim_clock:{item}"
            for item in clock_verification.get("blockers") or []
        )
    if started_at is not None and abs(started_at - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("matrix_claim_clock_timestamp_mismatch")

    batch_spec = _mapping(protocol.get("batch_spec"))
    confirmation_symbols = {
        str(symbol or "").strip().upper()
        for symbol in _sequence(batch_spec.get("confirmation_symbols"))
        if str(symbol or "").strip()
    }
    exposure_verification = _verify_holdout_exposure_audit(
        payload.get("holdout_exposure_audit"),
        expected_symbols=confirmation_symbols,
    )
    blockers.extend(
        f"matrix_claim_exposure:{item}"
        for item in exposure_verification.get("blockers") or []
    )
    if lineage_claim_required:
        registry_anchor_verification = verify_strategy_research_registry_anchor(
            payload.get("search_lineage_registry_anchor"),
            search_lineage=batch_spec.get("search_lineage"),
            expected_registration_id=str(protocol.get("registration_id") or ""),
            expected_protocol_hash=str(protocol.get("protocol_hash") or ""),
        )
        blockers.extend(
            f"matrix_claim_search_lineage:{item}"
            for item in registry_anchor_verification.get("blockers") or []
        )
    else:
        registry_anchor_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "anchor_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if "search_lineage_registry_anchor" in payload:
            blockers.append("matrix_claim_legacy_has_search_lineage_anchor")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_claim_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "claim_hash": str(payload.get("claim_hash") or ""),
        "protocol_verification": protocol_verification,
        "clock_verification": clock_verification,
        "exposure_verification": exposure_verification,
        "search_lineage_registry_anchor_verification": (
            registry_anchor_verification
        ),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_strategy_matrix_completion(
    completion: Any,
    *,
    protocol: dict[str, Any],
    claim: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = _mapping(completion)
    claim_verification = verify_strategy_matrix_claim(claim, protocol=protocol)
    if claim_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_completion_claim:{item}"
            for item in claim_verification.get("blockers") or []
        )
    if not isinstance(completion, dict):
        blockers.append("matrix_completion_type_invalid")
    if payload.get("schema_version") != STRATEGY_MATRIX_COMPLETION_VERSION:
        blockers.append("matrix_completion_schema_invalid")
    if payload.get("status") != "COMPLETED":
        blockers.append("matrix_completion_status_invalid")
    if not _embedded_hash_matches(payload, "completion_hash"):
        blockers.append("matrix_completion_hash_invalid")
    if str(payload.get("registration_id") or "") != str(protocol.get("registration_id") or ""):
        blockers.append("matrix_completion_registration_mismatch")
    if str(payload.get("protocol_hash") or "") != str(protocol.get("protocol_hash") or ""):
        blockers.append("matrix_completion_protocol_hash_mismatch")
    if str(payload.get("claim_hash") or "") != str(claim.get("claim_hash") or ""):
        blockers.append("matrix_completion_claim_hash_mismatch")
    if not _valid_sha256(payload.get("result_hash")):
        blockers.append("matrix_completion_result_hash_invalid")
    if not _valid_sha256(payload.get("dataset_manifest_hash")):
        blockers.append("matrix_completion_dataset_hash_invalid")

    started_at = _strict_positive_int(claim.get("started_at_ms"))
    completed_at = _strict_positive_int(payload.get("completed_at_ms"))
    if started_at is None or completed_at is None or completed_at < started_at:
        blockers.append("matrix_completion_temporal_order_invalid")
    clock = _mapping(payload.get("clock_attestation"))
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"matrix_completion_clock:{item}"
            for item in clock_verification.get("blockers") or []
        )
    if completed_at is not None and abs(completed_at - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("matrix_completion_clock_timestamp_mismatch")
    if (
        payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("matrix_completion_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "completion_hash": str(payload.get("completion_hash") or ""),
        "claim_verification": claim_verification,
        "clock_verification": clock_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_matrix_completion(
    *,
    protocol: dict[str, Any],
    claim: dict[str, Any],
    result_hash: str,
    dataset_manifest_hash: str,
    clock_attestation: dict[str, Any],
) -> dict[str, Any]:
    """Build the deterministic completion receipt used before and inside commit.

    The function is intentionally pure so a runner can seal and fully verify its
    final report before the registry consumes the single-use claim. ``complete``
    calls this same builder inside its transaction and therefore cannot issue a
    receipt different from the pre-committed report when all inputs are equal.
    """

    completion = {
        "schema_version": STRATEGY_MATRIX_COMPLETION_VERSION,
        "status": "COMPLETED",
        "registration_id": str(protocol.get("registration_id") or ""),
        "protocol_hash": str(protocol.get("protocol_hash") or ""),
        "claim_hash": str(claim.get("claim_hash") or ""),
        "result_hash": str(result_hash),
        "dataset_manifest_hash": str(dataset_manifest_hash),
        "completed_at_ms": int(clock_attestation.get("attested_now_ms") or 0),
        "clock_attestation": dict(clock_attestation or {}),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    completion["completion_hash"] = canonical_hash(completion)
    return completion


class StrategyMatrixRegistrationStore:
    def __init__(
        self,
        *,
        db_path: Path | str,
        now_ms: Callable[[], int] = _now_ms,
        read_only: bool = False,
        canonical_runtime_root: Path | str | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.canonical_runtime_root = (
            Path(canonical_runtime_root)
            if canonical_runtime_root is not None
            else None
        )
        self.now_ms = now_ms
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if self.canonical_runtime_root is not None:
            preflight = verify_strategy_research_canonical_registry_path(
                self.db_path,
                active_runtime_root=self.canonical_runtime_root,
            )
            if preflight.get("status") != "PASS":
                raise ValueError(
                    "strategy_research_registry_path_preflight:"
                    + ",".join(
                        str(item) for item in preflight.get("blockers") or []
                    )
                )
        if not self.read_only:
            self._initialize()
            if self.canonical_runtime_root is not None:
                postflight = verify_strategy_research_canonical_registry_path(
                    self.db_path,
                    active_runtime_root=self.canonical_runtime_root,
                )
                if postflight.get("status") != "PASS":
                    raise ValueError(
                        "strategy_research_registry_path_postflight:"
                        + ",".join(
                            str(item) for item in postflight.get("blockers") or []
                        )
                    )

    @contextmanager
    def _connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        if write:
            require_runtime_writable(read_only=self.read_only, service="strategy_matrix_registry")
        connection = connect_runtime_sqlite(
            self.db_path,
            read_only=self.read_only,
            timeout=15,
        )
        connection.row_factory = sqlite3.Row
        if write:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
            if write:
                connection.commit()
        except Exception:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect(write=True) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS strategy_matrix_registrations (
                    registration_id TEXT PRIMARY KEY,
                    protocol_hash TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL,
                    protocol_json TEXT NOT NULL,
                    claim_json TEXT NOT NULL DEFAULT '{}',
                    completion_json TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS strategy_matrix_registration_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    event_hash TEXT UNIQUE NOT NULL
                );
                """
            )

    @staticmethod
    def _event_core(
        *, registration_id: str, event_type: str, event_time: int,
        previous_event_hash: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": STRATEGY_MATRIX_REGISTRY_VERSION,
            "registration_id": registration_id,
            "event_type": event_type,
            "event_time": int(event_time),
            "previous_event_hash": previous_event_hash,
            "payload": payload,
        }

    def _append_event(
        self, connection: sqlite3.Connection, *, registration_id: str,
        event_type: str, event_time: int, payload: dict[str, Any],
    ) -> dict[str, Any]:
        previous = connection.execute(
            "SELECT event_hash FROM strategy_matrix_registration_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = str(previous["event_hash"] or "") if previous else ""
        core = self._event_core(
            registration_id=registration_id,
            event_type=event_type,
            event_time=event_time,
            previous_event_hash=previous_hash,
            payload=payload,
        )
        event_hash = canonical_hash(core)
        cursor = connection.execute(
            """
            INSERT INTO strategy_matrix_registration_events(
                registration_id, event_type, event_time, previous_event_hash, payload_json, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                registration_id,
                event_type,
                int(event_time),
                previous_hash,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                event_hash,
            ),
        )
        return {**core, "seq": int(cursor.lastrowid), "event_hash": event_hash}

    def _audit_connection(self, connection: sqlite3.Connection) -> dict[str, Any]:
        blockers: list[str] = []
        previous_hash = ""
        last_event: dict[str, str] = {}
        events_by_registration: dict[str, list[tuple[str, dict[str, Any], int]]] = {}
        for row in connection.execute("SELECT * FROM strategy_matrix_registration_events ORDER BY seq"):
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                payload = {}
                blockers.append(f"matrix_registry_event_payload_invalid:{row['seq']}")
            if not isinstance(payload, dict):
                payload = {}
                blockers.append(f"matrix_registry_event_payload_type_invalid:{row['seq']}")
            registration_id = str(row["registration_id"] or "")
            event_type = str(row["event_type"] or "")
            event_time = int(row["event_time"] or 0)
            core = self._event_core(
                registration_id=registration_id,
                event_type=event_type,
                event_time=event_time,
                previous_event_hash=str(row["previous_event_hash"] or ""),
                payload=payload,
            )
            if str(row["previous_event_hash"] or "") != previous_hash:
                blockers.append(f"matrix_registry_event_chain_invalid:{row['seq']}")
            if canonical_hash(core) != str(row["event_hash"] or ""):
                blockers.append(f"matrix_registry_event_hash_invalid:{row['seq']}")
            previous_hash = str(row["event_hash"] or "")
            last_event[registration_id] = event_type
            events_by_registration.setdefault(registration_id, []).append((event_type, payload, event_time))

        expected_sequence = {
            "REGISTERED": ["REGISTERED"],
            "RUNNING": ["REGISTERED", "CLAIMED"],
            "COMPLETED": ["REGISTERED", "CLAIMED", "COMPLETED"],
        }
        registration_ids: set[str] = set()

        expected_events = {
            "REGISTERED": "REGISTERED",
            "RUNNING": "CLAIMED",
            "COMPLETED": "COMPLETED",
        }
        for row in connection.execute("SELECT * FROM strategy_matrix_registrations ORDER BY created_at"):
            registration_id = str(row["registration_id"] or "")
            registration_ids.add(registration_id)
            try:
                protocol = json.loads(str(row["protocol_json"] or "{}"))
            except json.JSONDecodeError:
                protocol = {}
                blockers.append(f"matrix_registry_protocol_invalid:{registration_id}")
            clean = dict(protocol)
            protocol_hash = str(clean.pop("protocol_hash", "") or "")
            if protocol_hash != str(row["protocol_hash"] or "") or canonical_hash(clean) != protocol_hash:
                blockers.append(f"matrix_registry_protocol_hash_invalid:{registration_id}")
            protocol_verification = verify_strategy_matrix_protocol(
                protocol,
                verify_current_implementation=False,
            )
            if str(Path(str(protocol.get("registry_path") or "")).resolve()) != str(self.db_path.resolve()):
                blockers.append(f"matrix_registry_path_mismatch:{registration_id}")
            if protocol_verification.get("status") != "PASS":
                blockers.extend(
                    f"matrix_registry_protocol_invalid:{registration_id}:{item}"
                    for item in protocol_verification.get("blockers") or []
                )
            try:
                claim = json.loads(str(row["claim_json"] or "{}"))
            except json.JSONDecodeError:
                claim = {}
                blockers.append(f"matrix_registry_claim_json_invalid:{registration_id}")
            try:
                completion = json.loads(str(row["completion_json"] or "{}"))
            except json.JSONDecodeError:
                completion = {}
                blockers.append(f"matrix_registry_completion_json_invalid:{registration_id}")
            if not isinstance(claim, dict):
                claim = {}
                blockers.append(f"matrix_registry_claim_type_invalid:{registration_id}")
            if not isinstance(completion, dict):
                completion = {}
                blockers.append(f"matrix_registry_completion_type_invalid:{registration_id}")
            status = str(row["status"] or "")
            if last_event.get(registration_id) != expected_events.get(status):
                blockers.append(f"matrix_registry_status_event_mismatch:{registration_id}")
            sequence = [item[0] for item in events_by_registration.get(registration_id, [])]
            if sequence != expected_sequence.get(status):
                blockers.append(f"matrix_registry_event_sequence_invalid:{registration_id}")
            events = events_by_registration.get(registration_id, [])
            if events:
                registered_event = events[0]
                if (
                    registered_event[1].get("protocol_hash") != protocol_hash
                    or registered_event[2] != int(protocol.get("registered_at_ms") or 0)
                ):
                    blockers.append(f"matrix_registry_registered_event_mismatch:{registration_id}")
            if int(row["created_at"] or 0) != int(protocol.get("registered_at_ms") or 0):
                blockers.append(f"matrix_registry_created_at_mismatch:{registration_id}")
            if status == "REGISTERED":
                if claim or completion:
                    blockers.append(f"matrix_registry_registered_receipts_present:{registration_id}")
                expected_updated_at = int(protocol.get("registered_at_ms") or 0)
            elif status in {"RUNNING", "COMPLETED"}:
                claim_verification = verify_strategy_matrix_claim(claim, protocol=protocol)
                if claim_verification.get("status") != "PASS":
                    blockers.extend(
                        f"matrix_registry_claim_invalid:{registration_id}:{item}"
                        for item in claim_verification.get("blockers") or []
                    )
                if len(events) >= 2 and (
                    events[1][1].get("claim_hash") != claim.get("claim_hash")
                    or events[1][1].get("protocol_hash") != protocol_hash
                    or events[1][2] != int(claim.get("started_at_ms") or 0)
                ):
                    blockers.append(f"matrix_registry_claim_event_mismatch:{registration_id}")
                expected_updated_at = int(claim.get("started_at_ms") or 0)
                if status == "RUNNING" and completion:
                    blockers.append(f"matrix_registry_running_completion_present:{registration_id}")
                if status == "COMPLETED":
                    completion_verification = verify_strategy_matrix_completion(
                        completion,
                        protocol=protocol,
                        claim=claim,
                    )
                    if completion_verification.get("status") != "PASS":
                        blockers.extend(
                            f"matrix_registry_completion_invalid:{registration_id}:{item}"
                            for item in completion_verification.get("blockers") or []
                        )
                    if len(events) >= 3 and (
                        events[2][1].get("completion_hash") != completion.get("completion_hash")
                        or events[2][1].get("result_hash") != completion.get("result_hash")
                        or events[2][1].get("dataset_manifest_hash") != completion.get("dataset_manifest_hash")
                        or events[2][2] != int(completion.get("completed_at_ms") or 0)
                    ):
                        blockers.append(f"matrix_registry_completion_event_mismatch:{registration_id}")
                    expected_updated_at = int(completion.get("completed_at_ms") or 0)
            else:
                expected_updated_at = 0
                blockers.append(f"matrix_registry_status_invalid:{registration_id}")
            if int(row["updated_at"] or 0) != expected_updated_at:
                blockers.append(f"matrix_registry_updated_at_mismatch:{registration_id}")
        for registration_id in sorted(set(events_by_registration) - registration_ids):
            blockers.append(f"matrix_registry_orphan_events:{registration_id}")
        return {
            "schema_version": STRATEGY_MATRIX_REGISTRY_VERSION,
            "status": "PASS" if not blockers else "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "event_count": int(connection.execute(
                "SELECT COUNT(*) FROM strategy_matrix_registration_events"
            ).fetchone()[0]),
            "tail_event_hash": previous_hash,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def _derive_search_lineage_connection(
        self,
        connection: sqlite3.Connection,
        *,
        search_family_id: str,
        current_trial_count: int,
    ) -> dict[str, Any]:
        """Rebuild one family ledger from prior REGISTERED events in seq order."""

        try:
            family_id = normalize_search_family_id(search_family_id)
        except ValueError as exc:
            return {
                "status": "BLOCK",
                "blockers": [str(exc)],
                "lineage": None,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        if (
            isinstance(current_trial_count, bool)
            or not isinstance(current_trial_count, int)
            or current_trial_count < 1
        ):
            return {
                "status": "BLOCK",
                "blockers": ["strategy_search_current_trial_count_invalid"],
                "lineage": None,
                "paper_authorized": False,
                "live_order_allowed": False,
            }

        prior: list[dict[str, Any]] = []
        blockers: list[str] = []
        rows = connection.execute(
            """
            SELECT r.registration_id, r.protocol_hash, r.protocol_json,
                   e.event_hash AS registered_event_hash, e.seq
            FROM strategy_matrix_registration_events AS e
            JOIN strategy_matrix_registrations AS r
              ON r.registration_id = e.registration_id
            WHERE e.event_type = 'REGISTERED'
            ORDER BY e.seq
            """
        ).fetchall()
        for row in rows:
            registration_id = str(row["registration_id"] or "")
            try:
                protocol = json.loads(str(row["protocol_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                blockers.append(
                    f"strategy_search_prior_protocol_json_invalid:{registration_id}"
                )
                continue
            batch_spec = _mapping(_mapping(protocol).get("batch_spec"))
            lineage = batch_spec.get("search_lineage")
            controlled_research = (
                batch_spec.get("workflow") == "NESTED_VARIANT_RESEARCH"
                or isinstance(lineage, dict)
            )
            if not controlled_research:
                continue
            variants = batch_spec.get("variants")
            prior_current_trials = len(variants) if isinstance(variants, list) else 0
            if prior_current_trials < 1:
                blockers.append(
                    f"strategy_search_prior_trial_count_invalid:{registration_id}"
                )
                continue
            prior_report_schema_version = batch_spec.get("report_schema_version")
            if (
                isinstance(prior_report_schema_version, bool)
                or not isinstance(prior_report_schema_version, int)
                or not 3 <= prior_report_schema_version
                <= STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
            ):
                blockers.append(
                    f"strategy_search_prior_report_schema_invalid:{registration_id}"
                )
                continue
            if isinstance(lineage, dict):
                try:
                    prior_family = normalize_search_family_id(
                        lineage.get("search_family_id")
                    )
                except ValueError:
                    blockers.append(
                        f"strategy_search_prior_family_invalid:{registration_id}"
                    )
                    continue
                verification = verify_strategy_research_search_lineage(
                    lineage,
                    expected_search_family_id=prior_family,
                    expected_current_trial_count=prior_current_trials,
                    expected_prior_registrations=prior,
                )
                if verification.get("status") != "PASS":
                    blockers.extend(
                        f"strategy_search_prior_lineage:{registration_id}:{item}"
                        for item in verification.get("blockers") or []
                    )
                    continue
                prior_lineage_mode = "BOUND"
            else:
                prior_family = None
                prior_lineage_mode = "LEGACY_UNSCOPED"
            cumulative_trial_count = sum(
                int(item["current_trial_count"]) for item in prior
            ) + prior_current_trials
            prior.append({
                "registration_id": registration_id,
                "protocol_hash": str(row["protocol_hash"] or ""),
                "registered_event_hash": str(
                    row["registered_event_hash"] or ""
                ),
                "search_family_id": prior_family,
                "report_schema_version": prior_report_schema_version,
                "lineage_mode": prior_lineage_mode,
                "current_trial_count": prior_current_trials,
                "cumulative_trial_count": cumulative_trial_count,
            })

        if blockers:
            return {
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "lineage": None,
                "prior_registration_count": len(prior),
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        try:
            lineage = build_strategy_research_search_lineage(
                search_family_id=family_id,
                prior_registrations=prior,
                current_trial_count=current_trial_count,
            )
        except ValueError as exc:
            return {
                "status": "BLOCK",
                "blockers": [str(exc)],
                "lineage": None,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        return {
            "status": "PASS",
            "blockers": [],
            "lineage": lineage,
            "prior_registration_count": len(prior),
            "registry_audited": True,
            "transactionally_registered": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def derive_search_lineage(
        self,
        *,
        search_family_id: str,
        current_trial_count: int,
    ) -> dict[str, Any]:
        """Plan a lineage snapshot; ``register`` re-derives it under BEGIN IMMEDIATE."""

        with self._lock, self._connect() as connection:
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "status": "BLOCK",
                    "blockers": [
                        f"matrix_registry_integrity:{item}"
                        for item in audit.get("blockers") or []
                    ],
                    "lineage": None,
                    "registry_audit": audit,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            return self._derive_search_lineage_connection(
                connection,
                search_family_id=search_family_id,
                current_trial_count=current_trial_count,
            )

    def _verify_search_lineage_live_connection(
        self,
        connection: sqlite3.Connection,
        *,
        registration_id: str,
    ) -> dict[str, Any]:
        clean_id = str(registration_id or "").strip()
        canonical_path_verification = (
            verify_strategy_research_canonical_registry_path(
                self.db_path,
                active_runtime_root=self.canonical_runtime_root,
            )
        )
        audit = self._audit_connection(connection)
        blockers: list[str] = []
        blockers.extend(
            f"strategy_search_live_registry_path:{item}"
            for item in canonical_path_verification.get("blockers") or []
        )
        blockers.extend(
            f"strategy_search_live_registry_integrity:{item}"
            for item in audit.get("blockers") or []
        )
        row = connection.execute(
            "SELECT * FROM strategy_matrix_registrations WHERE registration_id = ?",
            (clean_id,),
        ).fetchone()
        if row is None:
            blockers.append("strategy_search_live_registration_not_found")
            protocol: dict[str, Any] = {}
            claim: dict[str, Any] = {}
        else:
            try:
                raw_protocol = json.loads(str(row["protocol_json"] or "{}"))
                raw_claim = json.loads(str(row["claim_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                raw_protocol, raw_claim = {}, {}
                blockers.append("strategy_search_live_registration_json_invalid")
            protocol = _mapping(raw_protocol)
            claim = _mapping(raw_claim)
            if str(row["status"] or "") != "RUNNING":
                blockers.append("strategy_search_live_registration_not_running")
            if str(row["protocol_hash"] or "") != str(
                protocol.get("protocol_hash") or ""
            ):
                blockers.append("strategy_search_live_protocol_row_mismatch")
        if protocol and not _strategy_research_lineage_claim_required(protocol):
            blockers.append("strategy_search_live_protocol_not_schema14")
        protocol_verification = verify_strategy_matrix_protocol(
            protocol,
            verify_current_implementation=False,
        )
        blockers.extend(
            f"strategy_search_live_protocol:{item}"
            for item in protocol_verification.get("blockers") or []
        )
        claim_verification = verify_strategy_matrix_claim(
            claim,
            protocol=protocol,
        )
        blockers.extend(
            f"strategy_search_live_claim:{item}"
            for item in claim_verification.get("blockers") or []
        )
        events = connection.execute(
            """
            SELECT event_type, previous_event_hash, payload_json, event_hash
            FROM strategy_matrix_registration_events
            WHERE registration_id = ?
            ORDER BY seq
            """,
            (clean_id,),
        ).fetchall()
        if [str(item["event_type"] or "") for item in events] != [
            "REGISTERED",
            "CLAIMED",
        ]:
            blockers.append("strategy_search_live_registration_events_invalid")
        registered_event = events[0] if len(events) >= 1 else None
        claimed_event = events[1] if len(events) >= 2 else None
        try:
            registered_payload = (
                json.loads(str(registered_event["payload_json"] or "{}"))
                if registered_event is not None
                else {}
            )
            claimed_payload = (
                json.loads(str(claimed_event["payload_json"] or "{}"))
                if claimed_event is not None
                else {}
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            registered_payload, claimed_payload = {}, {}
            blockers.append("strategy_search_live_event_payload_invalid")
        protocol_hash = str(protocol.get("protocol_hash") or "")
        claim_hash = str(claim.get("claim_hash") or "")
        if _mapping(registered_payload).get("protocol_hash") != protocol_hash:
            blockers.append("strategy_search_live_registered_event_mismatch")
        if (
            _mapping(claimed_payload).get("protocol_hash") != protocol_hash
            or _mapping(claimed_payload).get("claim_hash") != claim_hash
        ):
            blockers.append("strategy_search_live_claimed_event_mismatch")
        anchor = _mapping(claim.get("search_lineage_registry_anchor"))
        if registered_event is not None and anchor.get(
            "registered_event_hash"
        ) != str(registered_event["event_hash"] or ""):
            blockers.append("strategy_search_live_registered_anchor_mismatch")
        if claimed_event is not None and anchor.get(
            "registry_audit_tail_event_hash"
        ) != str(claimed_event["previous_event_hash"] or ""):
            blockers.append("strategy_search_live_claim_previous_tail_mismatch")
        anchor_verification = verify_strategy_research_registry_anchor(
            anchor,
            search_lineage=_mapping(
                _mapping(protocol.get("batch_spec")).get("search_lineage")
            ),
            expected_registration_id=clean_id,
            expected_protocol_hash=protocol_hash,
            expected_active_runtime_root=str(
                canonical_path_verification.get("active_runtime_root") or ""
            ),
            expected_canonical_registry_path=str(
                canonical_path_verification.get("canonical_registry_path") or ""
            ),
        )
        blockers.extend(
            f"strategy_search_live_anchor:{item}"
            for item in anchor_verification.get("blockers") or []
        )
        lineage = _mapping(
            _mapping(protocol.get("batch_spec")).get("search_lineage")
        )
        live_binding = {
            "schema_version": "strategy-search-live-registry-verification-v1",
            "status": "LIVE_REGISTRY_VERIFIED" if not blockers else "BLOCK",
            "registration_id": clean_id,
            "protocol_hash": protocol_hash,
            "claim_hash": claim_hash,
            "registry_anchor_hash": str(anchor.get("anchor_hash") or ""),
            "registered_event_hash": (
                str(registered_event["event_hash"] or "")
                if registered_event is not None
                else ""
            ),
            "claimed_event_hash": (
                str(claimed_event["event_hash"] or "")
                if claimed_event is not None
                else ""
            ),
            "cumulative_trial_count": lineage.get("cumulative_trial_count"),
            "registry_audit_event_count": audit.get("event_count"),
            "registry_audit_tail_event_hash": str(
                audit.get("tail_event_hash") or ""
            ),
            "blockers": list(dict.fromkeys(blockers)),
            "descriptive_only": True,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        registration_context = {
            "ok": not blockers,
            "status": "RUNNING" if row is not None else "NOT_FOUND",
            "registration_id": clean_id,
            "protocol": protocol,
            "claim": claim,
            "completion": {},
            "registry_audit": audit,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return {
            "ok": not blockers,
            "status": "PASS" if not blockers else "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "cumulative_trial_count": lineage.get("cumulative_trial_count"),
            "live_registry_binding": live_binding,
            "registration_context": registration_context,
            "registry_audit": audit,
            "canonical_path_verification": canonical_path_verification,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def verify_search_lineage_live(
        self,
        registration_id: str,
    ) -> dict[str, Any]:
        """Live schema-14 pre-data gate; immutable read-only stores are forbidden."""

        if self.read_only:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": ["strategy_search_live_registry_connection_required"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN")
            return self._verify_search_lineage_live_connection(
                connection,
                registration_id=registration_id,
            )

    def build_search_lineage_admission(
        self,
        registration_id: str,
        *,
        parameter_stability: dict[str, Any],
        selection_cells: list[dict[str, Any]],
        validation_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build schema-14 freeze admission only while the canonical DB is live."""

        if self.read_only:
            return {
                "schema_version": (
                    "strategy-preregistered-failure-admission-v3"
                ),
                "status": "BLOCK",
                "admitted_variant_ids": [],
                "blockers": ["strategy_search_live_registry_connection_required"],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN")
            live = self._verify_search_lineage_live_connection(
                connection,
                registration_id=registration_id,
            )
            if live.get("status") != "PASS":
                return {
                    "schema_version": (
                        "strategy-preregistered-failure-admission-v3"
                    ),
                    "status": "BLOCK",
                    "admitted_variant_ids": [],
                    "blockers": list(
                        live.get("blockers")
                        or [
                            "strategy_search_lineage_live_registry_verification_required"
                        ]
                    ),
                    "live_registry_verification": live,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            context = _mapping(live.get("registration_context"))
            protocol = _mapping(context.get("protocol"))
            batch_spec = _mapping(protocol.get("batch_spec"))
            return _build_strategy_preregistered_failure_admission_v3_from_live_registry(
                batch_spec=batch_spec,
                hypothesis_preregistration=_mapping(
                    batch_spec.get("hypothesis_preregistration")
                ),
                parameter_stability=parameter_stability,
                selection_cells=selection_cells,
                validation_candidates=validation_candidates,
                registration_context=context,
                live_registry_binding=_mapping(
                    live.get("live_registry_binding")
                ),
            )

    def register(self, protocol: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_matrix_registry")
        verification = verify_strategy_matrix_protocol(protocol)
        if str(Path(str(protocol.get("registry_path") or "")).resolve()) != str(self.db_path.resolve()):
            verification = {
                **verification,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys([
                    *(verification.get("blockers") or []),
                    "matrix_protocol_registry_path_mismatch",
                ])),
            }
        canonical_path_verification = {
            "status": "NOT_REQUIRED",
            "blockers": [],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if _strategy_research_lineage_claim_required(protocol):
            canonical_path_verification = (
                verify_strategy_research_canonical_registry_path(
                    self.db_path,
                    active_runtime_root=self.canonical_runtime_root,
                )
            )
            if canonical_path_verification.get("status") != "PASS":
                verification = {
                    **verification,
                    "status": "BLOCK",
                    "blockers": list(dict.fromkeys([
                        *(verification.get("blockers") or []),
                        *[
                            f"matrix_protocol_registry_authority:{item}"
                            for item in canonical_path_verification.get(
                                "blockers"
                            ) or []
                        ],
                    ])),
                }
        artifact_verification = _verify_required_strategy_research_protocol_artifact(protocol)
        if artifact_verification.get("status") == "BLOCK":
            verification = {
                **verification,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys([
                    *(verification.get("blockers") or []),
                    *[
                        f"matrix_protocol_artifact:{item}"
                        for item in artifact_verification.get("blockers") or []
                    ],
                ])),
            }
        if verification.get("status") != "PASS":
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": verification.get("blockers") or [],
                "protocol_verification": verification,
                "canonical_path_verification": canonical_path_verification,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        registration_id = str(protocol.get("registration_id") or "")
        registered_at = int(protocol.get("registered_at_ms") or 0)
        with self._lock, self._connect(write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"matrix_registry_integrity:{item}" for item in audit.get("blockers") or []],
                    "registry_audit": audit,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            artifact_verification = _verify_required_strategy_research_protocol_artifact(protocol)
            if artifact_verification.get("status") == "BLOCK":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [
                        f"matrix_protocol_artifact:{item}"
                        for item in artifact_verification.get("blockers") or []
                    ],
                    "artifact_verification": artifact_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            existing = connection.execute(
                "SELECT protocol_hash, status FROM strategy_matrix_registrations WHERE registration_id = ?",
                (registration_id,),
            ).fetchone()
            if existing:
                same = str(existing["protocol_hash"] or "") == str(protocol.get("protocol_hash") or "")
                return {
                    "ok": same,
                    "status": str(existing["status"] or "") if same else "BLOCK",
                    "blockers": [] if same else ["matrix_registration_id_conflict"],
                    "registration_id": registration_id,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            batch_spec = _mapping(protocol.get("batch_spec"))
            report_schema_version = batch_spec.get("report_schema_version")
            search_lineage = batch_spec.get("search_lineage")
            if (
                report_schema_version
                == STRATEGY_RESEARCH_SEARCH_LINEAGE_REPORT_SCHEMA_VERSION
                or search_lineage is not None
            ):
                variants = batch_spec.get("variants")
                current_trial_count = (
                    len(variants) if isinstance(variants, list) else 0
                )
                family_id = (
                    search_lineage.get("search_family_id")
                    if isinstance(search_lineage, dict) else ""
                )
                derived = self._derive_search_lineage_connection(
                    connection,
                    search_family_id=str(family_id or ""),
                    current_trial_count=current_trial_count,
                )
                if derived.get("status") != "PASS":
                    return {
                        "ok": False,
                        "status": "BLOCK",
                        "blockers": [
                            f"matrix_registry_search_lineage:{item}"
                            for item in derived.get("blockers") or []
                        ],
                        "search_lineage_verification": derived,
                        "paper_authorized": False,
                        "live_order_allowed": False,
                    }
                expected_lineage = derived.get("lineage")
                if search_lineage != expected_lineage:
                    return {
                        "ok": False,
                        "status": "BLOCK",
                        "blockers": [
                            "matrix_registry_search_lineage_transaction_mismatch"
                        ],
                        "expected_search_lineage": expected_lineage,
                        "paper_authorized": False,
                        "live_order_allowed": False,
                    }
            event = self._append_event(
                connection,
                registration_id=registration_id,
                event_type="REGISTERED",
                event_time=registered_at,
                payload={"protocol_hash": str(protocol.get("protocol_hash") or "")},
            )
            connection.execute(
                """
                INSERT INTO strategy_matrix_registrations(
                    registration_id, protocol_hash, status, protocol_json, created_at, updated_at
                ) VALUES (?, ?, 'REGISTERED', ?, ?, ?)
                """,
                (
                    registration_id,
                    str(protocol.get("protocol_hash") or ""),
                    json.dumps(protocol, ensure_ascii=False, sort_keys=True),
                    registered_at,
                    registered_at,
                ),
            )
        return {
            "ok": True,
            "status": "REGISTERED",
            "registration_id": registration_id,
            "protocol_hash": str(protocol.get("protocol_hash") or ""),
            "search_lineage_registered": (
                _mapping(protocol.get("batch_spec")).get("search_lineage")
                is not None
            ),
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def claim(
        self,
        registration_id: str,
        *,
        clock_attestation: dict[str, Any],
        exposure_audit: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_matrix_registry")
        clean_id = str(registration_id or "").strip()
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        if clock_verification.get("status") != "PASS":
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": [f"matrix_claim_clock:{item}" for item in clock_verification.get("blockers") or []],
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        started_at = int(clock_attestation.get("attested_now_ms") or 0)
        with self._lock, self._connect(write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            row = connection.execute(
                "SELECT * FROM strategy_matrix_registrations WHERE registration_id = ?",
                (clean_id,),
            ).fetchone()
            if audit.get("status") != "PASS" or not row:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": (
                        [f"matrix_registry_integrity:{item}" for item in audit.get("blockers") or []]
                        if audit.get("status") != "PASS" else ["matrix_registration_not_found"]
                    ),
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            if str(row["status"] or "") != "REGISTERED":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"matrix_registration_already_consumed:{row['status']}"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            protocol = json.loads(str(row["protocol_json"] or "{}"))
            if str(Path(str(protocol.get("registry_path") or "")).resolve()) != str(self.db_path.resolve()):
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["matrix_protocol_registry_path_mismatch"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            if _strategy_research_lineage_claim_required(protocol):
                canonical_path_verification = (
                    verify_strategy_research_canonical_registry_path(
                        self.db_path,
                        active_runtime_root=self.canonical_runtime_root,
                    )
                )
                if canonical_path_verification.get("status") != "PASS":
                    return {
                        "ok": False,
                        "status": "BLOCK",
                        "blockers": [
                            f"matrix_claim_registry_authority:{item}"
                            for item in canonical_path_verification.get(
                                "blockers"
                            ) or []
                        ],
                        "canonical_path_verification": (
                            canonical_path_verification
                        ),
                        "paper_authorized": False,
                        "live_order_allowed": False,
                    }
            protocol_verification = verify_strategy_matrix_protocol(
                protocol,
                verification_at_ms=started_at,
                enforce_not_expired=True,
            )
            if protocol_verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": protocol_verification.get("blockers") or [],
                    "protocol_verification": protocol_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            artifact_verification = _verify_required_strategy_research_protocol_artifact(protocol)
            if artifact_verification.get("status") == "BLOCK":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [
                        f"matrix_claim_artifact:{item}"
                        for item in artifact_verification.get("blockers") or []
                    ],
                    "artifact_verification": artifact_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            lineage_claim_required = _strategy_research_lineage_claim_required(
                protocol
            )
            search_lineage_registry_anchor: dict[str, Any] | None = None
            if lineage_claim_required:
                registered_event = connection.execute(
                    """
                    SELECT event_hash
                    FROM strategy_matrix_registration_events
                    WHERE registration_id = ? AND event_type = 'REGISTERED'
                    ORDER BY seq
                    LIMIT 1
                    """,
                    (clean_id,),
                ).fetchone()
                try:
                    search_lineage_registry_anchor = (
                        build_strategy_research_registry_anchor(
                            registration_id=clean_id,
                            protocol_hash=str(row["protocol_hash"] or ""),
                            registered_event_hash=(
                                str(registered_event["event_hash"] or "")
                                if registered_event is not None
                                else ""
                            ),
                            registry_audit_tail_event_hash=str(
                                audit.get("tail_event_hash") or ""
                            ),
                            active_runtime_root=str(
                                canonical_path_verification.get(
                                    "active_runtime_root"
                                )
                                or ""
                            ),
                            canonical_registry_path=str(
                                canonical_path_verification.get(
                                    "canonical_registry_path"
                                )
                                or ""
                            ),
                            search_lineage=_mapping(
                                _mapping(protocol.get("batch_spec")).get(
                                    "search_lineage"
                                )
                            ),
                        )
                    )
                except ValueError as exc:
                    return {
                        "ok": False,
                        "status": "BLOCK",
                        "blockers": [
                            f"matrix_claim_search_lineage_anchor:{exc}"
                        ],
                        "paper_authorized": False,
                        "live_order_allowed": False,
                    }
            claim = {
                "schema_version": (
                    STRATEGY_MATRIX_CLAIM_VERSION_V2
                    if lineage_claim_required
                    else STRATEGY_MATRIX_CLAIM_VERSION
                ),
                "status": "CLAIMED_FOR_SINGLE_RUN",
                "registration_id": clean_id,
                "protocol_hash": str(row["protocol_hash"] or ""),
                "registered_at_ms": int(protocol.get("registered_at_ms") or 0),
                "started_at_ms": started_at,
                "clock_attestation": dict(clock_attestation),
                "holdout_exposure_audit": dict(exposure_audit or {}),
                "implementation_fingerprint": str(protocol.get("implementation_fingerprint") or ""),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            if search_lineage_registry_anchor is not None:
                claim["search_lineage_registry_anchor"] = (
                    search_lineage_registry_anchor
                )
            claim["claim_hash"] = canonical_hash(claim)
            claim_verification = verify_strategy_matrix_claim(claim, protocol=protocol)
            if claim_verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": claim_verification.get("blockers") or [],
                    "claim_verification": claim_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            event = self._append_event(
                connection,
                registration_id=clean_id,
                event_type="CLAIMED",
                event_time=started_at,
                payload={"claim_hash": claim["claim_hash"], "protocol_hash": str(row["protocol_hash"] or "")},
            )
            connection.execute(
                """
                UPDATE strategy_matrix_registrations
                SET status = 'RUNNING', claim_json = ?, updated_at = ?
                WHERE registration_id = ? AND status = 'REGISTERED'
                """,
                (json.dumps(claim, ensure_ascii=False, sort_keys=True), started_at, clean_id),
            )
        return {
            "ok": True,
            "status": "CLAIMED",
            "registration_id": clean_id,
            "protocol": protocol,
            "claim": claim,
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def complete(
        self,
        registration_id: str,
        *,
        result_hash: str,
        dataset_manifest_hash: str,
        clock_attestation: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_matrix_registry")
        clean_id = str(registration_id or "").strip()
        blockers: list[str] = []
        if not _valid_sha256(result_hash):
            blockers.append("matrix_completion_result_hash_invalid")
        if not _valid_sha256(dataset_manifest_hash):
            blockers.append("matrix_completion_dataset_hash_invalid")
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        if clock_verification.get("status") != "PASS":
            blockers.extend(f"matrix_completion_clock:{item}" for item in clock_verification.get("blockers") or [])
        if blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": blockers,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        completed_at = int(clock_attestation.get("attested_now_ms") or 0)
        with self._lock, self._connect(write=True) as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            row = connection.execute(
                "SELECT * FROM strategy_matrix_registrations WHERE registration_id = ?",
                (clean_id,),
            ).fetchone()
            if audit.get("status") != "PASS" or not row or str(row["status"] or "") != "RUNNING":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": (
                        [f"matrix_registry_integrity:{item}" for item in audit.get("blockers") or []]
                        if audit.get("status") != "PASS"
                        else ["matrix_registration_not_running"]
                    ),
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            claim = json.loads(str(row["claim_json"] or "{}"))
            protocol = json.loads(str(row["protocol_json"] or "{}"))
            protocol_verification = verify_strategy_matrix_protocol(protocol)
            if protocol_verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [
                        f"matrix_completion_protocol:{item}"
                        for item in protocol_verification.get("blockers") or []
                    ],
                    "protocol_verification": protocol_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            claim_verification = verify_strategy_matrix_claim(claim, protocol=protocol)
            if claim_verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [
                        f"matrix_completion_claim:{item}"
                        for item in claim_verification.get("blockers") or []
                    ],
                    "claim_verification": claim_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            completion = build_strategy_matrix_completion(
                protocol=protocol,
                claim=claim,
                result_hash=result_hash,
                dataset_manifest_hash=dataset_manifest_hash,
                clock_attestation=clock_attestation,
            )
            completion_verification = verify_strategy_matrix_completion(
                completion,
                protocol=protocol,
                claim=claim,
            )
            if completion_verification.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": completion_verification.get("blockers") or [],
                    "completion_verification": completion_verification,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            event = self._append_event(
                connection,
                registration_id=clean_id,
                event_type="COMPLETED",
                event_time=completed_at,
                payload={
                    "completion_hash": completion["completion_hash"],
                    "result_hash": result_hash,
                    "dataset_manifest_hash": dataset_manifest_hash,
                },
            )
            connection.execute(
                """
                UPDATE strategy_matrix_registrations
                SET status = 'COMPLETED', completion_json = ?, updated_at = ?
                WHERE registration_id = ? AND status = 'RUNNING'
                """,
                (json.dumps(completion, ensure_ascii=False, sort_keys=True), completed_at, clean_id),
            )
        return {
            "ok": True,
            "status": "COMPLETED",
            "registration_id": clean_id,
            "completion": completion,
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def get(self, registration_id: str) -> dict[str, Any]:
        clean_id = str(registration_id or "").strip()
        with self._lock, self._connect() as connection:
            audit = self._audit_connection(connection)
            row = connection.execute(
                "SELECT * FROM strategy_matrix_registrations WHERE registration_id = ?",
                (clean_id,),
            ).fetchone()
        if not row:
            return {
                "ok": False,
                "status": "NOT_FOUND",
                "registration_id": clean_id,
                "registry_audit": audit,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        try:
            protocol = json.loads(str(row["protocol_json"] or "{}"))
            claim = json.loads(str(row["claim_json"] or "{}"))
            completion = json.loads(str(row["completion_json"] or "{}"))
        except json.JSONDecodeError:
            protocol, claim, completion = {}, {}, {}
        return {
            "ok": audit.get("status") == "PASS",
            "status": str(row["status"] or "") if audit.get("status") == "PASS" else "BLOCK",
            "registration_id": clean_id,
            "protocol": protocol if isinstance(protocol, dict) else {},
            "claim": claim if isinstance(claim, dict) else {},
            "completion": completion if isinstance(completion, dict) else {},
            "registry_audit": audit,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def audit(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            return self._audit_connection(connection)
