from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .execution_authority import authority_violations
from .portfolio_forward_local_source_anchor import (
    MAX_SAFE_INTEGER,
    verify_portfolio_forward_local_source_anchor,
)


PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION = "portfolio-forward-backup-status-v1"
PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION = "portfolio-forward-backup-status-v2"

MAX_LOCAL_RECEIPT_NESTING = 32
MAX_LOCAL_RECEIPT_NODES = 4_096
MAX_LOCAL_RECEIPT_CONTAINER_ITEMS = 1_024
MAX_LOCAL_RECEIPT_TEXT_UNITS = 262_144

PORTFOLIO_BACKUP_STATUS_V2_FIELDS = frozenset({
    "schema_version",
    "status",
    "severity",
    "generated_at",
    "candidate_hash",
    "bundle_path",
    "manifest_hash",
    "pack_hash",
    "verification_status",
    "blockers",
    "error_type",
    "error",
    "local_source_anchor",
    "backup_only",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "alert_condition_hash",
    "status_hash",
})


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_integer(value: Any, *, minimum: int = 0) -> int | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > MAX_SAFE_INTEGER
    ):
        return None
    return value


def local_receipt_json_shape_valid(payload: Any) -> bool:
    """Bound an already-decoded receipt before hashing or recursive scans.

    Runtime artifacts originate as JSON, so cycles, custom mappings, non-finite
    floats, and non-string object keys are never valid receipt data. The
    iterative walk keeps malformed deep inputs on a stable fail-closed path.
    """

    stack: list[tuple[Any, int]] = [(payload, 1)]
    node_count = 0
    text_units = 0
    while stack:
        value, depth = stack.pop()
        node_count += 1
        if node_count > MAX_LOCAL_RECEIPT_NODES or depth > MAX_LOCAL_RECEIPT_NESTING:
            return False
        if type(value) is dict:
            if len(value) > MAX_LOCAL_RECEIPT_CONTAINER_ITEMS:
                return False
            for key, child in value.items():
                if type(key) is not str:
                    return False
                text_units += len(key)
                if text_units > MAX_LOCAL_RECEIPT_TEXT_UNITS:
                    return False
                stack.append((child, depth + 1))
        elif type(value) is list:
            if len(value) > MAX_LOCAL_RECEIPT_CONTAINER_ITEMS:
                return False
            stack.extend((child, depth + 1) for child in value)
        elif type(value) is str:
            text_units += len(value)
            if text_units > MAX_LOCAL_RECEIPT_TEXT_UNITS:
                return False
        elif value is None or type(value) is bool:
            continue
        elif type(value) is int:
            if abs(value) > MAX_SAFE_INTEGER:
                return False
        elif type(value) is float:
            if not math.isfinite(value):
                return False
        else:
            return False
    return True


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 500:
            return None
        result.append(item)
    return result if len(result) == len(set(result)) else None


def _verification_result(blockers: list[str], *, expected_hash: str = "") -> dict[str, Any]:
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "expected_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_portfolio_backup_status_v1(payload: dict[str, Any]) -> dict[str, Any]:
    """Frozen verifier for the historical v1 receipt."""

    blockers: list[str] = []
    clean = dict(payload or {})
    expected_hash = str(clean.pop("status_hash", "") or "")
    if payload.get("schema_version") != PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION:
        blockers.append("backup_status_schema_invalid")
    if not expected_hash or canonical_hash(clean) != expected_hash:
        blockers.append("backup_status_hash_invalid")
    if payload.get("status") not in {"PASS", "BLOCK"}:
        blockers.append("backup_status_invalid")
    legacy_blockers = payload.get("blockers")
    if not isinstance(legacy_blockers, list):
        blockers.append("backup_status_blockers_invalid")
        legacy_blockers_present = True
    else:
        legacy_blockers_present = bool(legacy_blockers)
    semantic_pass = (
        bool(payload.get("candidate_hash"))
        and bool(payload.get("bundle_path"))
        and bool(payload.get("manifest_hash"))
        and bool(payload.get("pack_hash"))
        and payload.get("verification_status") == "PASS"
        and not legacy_blockers_present
        and not str(payload.get("error_type") or "")
        and not str(payload.get("error") or "")
    )
    expected_status = "PASS" if semantic_pass else "BLOCK"
    if payload.get("status") != expected_status:
        blockers.append("backup_status_semantics_inconsistent")
    expected_severity = "INFO" if expected_status == "PASS" else "CRITICAL"
    if payload.get("severity") != expected_severity:
        blockers.append("backup_status_severity_inconsistent")
    if payload.get("backup_only") is not True or payload.get("research_only") is not True:
        blockers.append("backup_status_scope_invalid")
    if authority_violations(payload):
        blockers.append("backup_status_contains_execution_authority")
    return _verification_result(blockers, expected_hash=expected_hash)


def _verify_portfolio_backup_status_v2(payload: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if set(payload) != PORTFOLIO_BACKUP_STATUS_V2_FIELDS:
        blockers.append("backup_status_fields_invalid")
    clean = dict(payload)
    expected_hash = clean.pop("status_hash", "")
    if not _sha256_hex(expected_hash) or canonical_hash(clean) != expected_hash:
        blockers.append("backup_status_hash_invalid")
    if payload.get("schema_version") != PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION:
        blockers.append("backup_status_schema_invalid")
    generated_at = _safe_integer(payload.get("generated_at"), minimum=1)
    if generated_at is None:
        blockers.append("backup_status_generated_at_invalid")

    status = payload.get("status")
    if status not in {"PASS", "BLOCK"}:
        blockers.append("backup_status_invalid")
    raw_blockers = _string_list(payload.get("blockers"))
    if raw_blockers is None:
        blockers.append("backup_status_blockers_invalid")
        raw_blockers = []
    error_type = payload.get("error_type")
    error = payload.get("error")
    if not isinstance(error_type, str) or len(error_type) > 500:
        blockers.append("backup_status_error_type_invalid")
        error_type = ""
    if not isinstance(error, str) or len(error) > 500:
        blockers.append("backup_status_error_invalid")
        error = ""
    if not isinstance(payload.get("bundle_path"), str):
        blockers.append("backup_status_bundle_path_invalid")
    if payload.get("verification_status") not in {"PASS", "BLOCK"}:
        blockers.append("backup_status_verification_status_invalid")
    for field in ("candidate_hash", "manifest_hash", "pack_hash"):
        value = payload.get(field)
        if value and not _sha256_hex(value):
            blockers.append(f"backup_status_{field}_invalid")

    anchor = payload.get("local_source_anchor")
    anchor_verification = verify_portfolio_forward_local_source_anchor(anchor)
    if anchor_verification.get("status") != "PASS":
        blockers.append("backup_status_local_source_anchor_invalid")
    anchor_payload = dict(anchor or {}) if isinstance(anchor, dict) else {}
    anchor_status = str(anchor_payload.get("status") or "")
    if anchor_status not in {"VERIFIED", "NOT_AVAILABLE"}:
        blockers.append("backup_status_local_source_anchor_status_invalid")

    semantic_pass = (
        _sha256_hex(payload.get("candidate_hash"))
        and bool(payload.get("bundle_path"))
        and _sha256_hex(payload.get("manifest_hash"))
        and _sha256_hex(payload.get("pack_hash"))
        and payload.get("verification_status") == "PASS"
        and not raw_blockers
        and not error_type
        and not error
        and anchor_verification.get("status") == "PASS"
        and str(anchor_payload.get("candidate_hash") or "")
        == str(payload.get("candidate_hash") or "")
        and str(anchor_payload.get("archive_manifest_hash") or "")
        == str(payload.get("manifest_hash") or "")
        and anchor_payload.get("archive_generated_at") == generated_at
    )
    expected_status = "PASS" if semantic_pass else "BLOCK"
    if status != expected_status:
        blockers.append("backup_status_semantics_inconsistent")
    expected_severity = "INFO" if expected_status == "PASS" else "CRITICAL"
    if payload.get("severity") != expected_severity:
        blockers.append("backup_status_severity_inconsistent")

    expected_condition = {
        "status": status,
        "candidate_hash": str(payload.get("candidate_hash") or ""),
        "blockers": raw_blockers,
        "error_type": error_type,
        "error": error,
        "local_source_anchor_status": anchor_status,
        "local_source_anchor_hash": str(anchor_payload.get("anchor_hash") or ""),
    }
    if (
        not _sha256_hex(payload.get("alert_condition_hash"))
        or payload.get("alert_condition_hash") != canonical_hash(expected_condition)
    ):
        blockers.append("backup_status_alert_condition_hash_invalid")
    if (
        payload.get("backup_only") is not True
        or payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("backup_status_scope_invalid")
    if authority_violations(payload):
        blockers.append("backup_status_contains_execution_authority")
    return _verification_result(blockers, expected_hash=str(expected_hash or ""))


def verify_portfolio_backup_status(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _verification_result(["backup_status_not_object"])
    try:
        if not local_receipt_json_shape_valid(payload):
            return _verification_result(["backup_status_structure_invalid"])
        schema_version = payload.get("schema_version")
        if schema_version == PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION:
            return _verify_portfolio_backup_status_v1(dict(payload))
        if schema_version == PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION:
            return _verify_portfolio_backup_status_v2(dict(payload))
        return _verification_result(["backup_status_schema_invalid"])
    except MemoryError:
        return _verification_result(["backup_status_verification_memory_exhausted"])
    except (AttributeError, KeyError, OverflowError, RecursionError, TypeError, ValueError):
        return _verification_result(["backup_status_structure_invalid"])
