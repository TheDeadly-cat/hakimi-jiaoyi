from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .execution_authority import authority_violations
from .forward_artifact_io import (
    MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
    read_forward_json_artifact,
)
from .portfolio_forward_local_source_anchor import (
    build_portfolio_forward_local_source_anchor_not_available,
    verify_portfolio_forward_local_source_anchor,
)
from .portfolio_forward_local_source_receipt import (
    PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
    PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
    local_receipt_json_shape_valid,
    verify_portfolio_backup_status,
)


PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION = "portfolio-forward-watchdog-v2"
PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION = "portfolio-forward-watchdog-v3"
PORTFOLIO_FORWARD_WATCHDOG_SOURCE_FACTS_SCHEMA_VERSION = (
    "portfolio-forward-watchdog-source-facts-v1"
)
DEFAULT_WATCHDOG_STATUS_FILE = "portfolio_forward_watchdog_status.json"
DEFAULT_WATCHDOG_ALERT_FILE = "portfolio_forward_watchdog_alerts.jsonl"
OBSERVATION_TASK_NAME = "HakimiTradeV2-PortfolioForwardObservation"
PERFORMANCE_TASK_NAME = "HakimiTradeV2-PortfolioForwardPerformance"
BACKUP_TASK_NAME = "HakimiTradeV2-PortfolioForwardBackup"
REQUIRED_TASK_NAMES = (OBSERVATION_TASK_NAME, PERFORMANCE_TASK_NAME, BACKUP_TASK_NAME)
DEFAULT_STALE_AFTER_MS = 45 * 60 * 1000
DEFAULT_BACKUP_STALE_AFTER_MS = 36 * 60 * 60 * 1000
RUNNING_TASK_RESULT = 0x00041301

PORTFOLIO_FORWARD_WATCHDOG_V3_FIELDS = frozenset({
    "schema_version",
    "status",
    "severity",
    "generated_at",
    "candidate_hash",
    "source_facts",
    "checks",
    "blockers",
    "status_ages_ms",
    "task_checks",
    "tasks",
    "task_names",
    "task_probe_status",
    "task_probe_error",
    "scheduler_status",
    "observation_status",
    "performance_status",
    "backup_status",
    "backup_archive_status",
    "backup_manifest_hash",
    "backup_schema_version",
    "backup_status_hash",
    "local_source_anchor_status",
    "verified_source_anchor",
    "snapshot_hash",
    "monitoring_only",
    "research_only",
    "paper_authorized",
    "live_order_allowed",
    "alert_condition_hash",
    "status_hash",
})

PORTFOLIO_FORWARD_WATCHDOG_V3_SOURCE_FACT_FIELDS = frozenset({
    "schema_version",
    "stale_after_ms",
    "backup_stale_after_ms",
    "active_status",
    "active_candidate_hash",
    "scheduler_status",
    "scheduler_health",
    "scheduler_candidate_hash",
    "scheduler_scheduled_invocation",
    "scheduler_status_age_ms",
    "observation_artifact_present",
    "observation_status",
    "observation_candidate_hash",
    "observation_ledger_status",
    "observation_audit_hash",
    "observation_critical_checks",
    "performance_artifact_present",
    "performance_status",
    "performance_candidate_hash",
    "performance_scheduled_invocation",
    "performance_ledger_status",
    "performance_integrity_checks",
    "performance_generated_at",
    "performance_audit_computed_hash",
    "performance_audit_hash",
    "backup_receipt",
    "backup_archive_verification",
    "task_probe_status",
    "task_probe_error",
    "authority_violation_count",
})

PORTFOLIO_FORWARD_WATCHDOG_V3_ARCHIVE_FACT_FIELDS = frozenset({
    "status",
    "candidate_hash",
    "manifest_hash",
    "local_source_anchor",
})

PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS = frozenset({
    "active_candidate_pass",
    "scheduler_health_pass",
    "scheduler_candidate_matches",
    "scheduler_scheduled_invocation",
    "scheduler_status_fresh",
    "observation_artifact_present",
    "observation_candidate_matches",
    "observation_ledger_pass",
    "observation_critical_checks_pass",
    "performance_artifact_present",
    "performance_candidate_matches",
    "performance_scheduled_invocation",
    "performance_ledger_pass",
    "performance_integrity_checks_pass",
    "performance_timestamp_present",
    "performance_timestamp_not_future",
    "performance_status_fresh",
    "forward_snapshot_hash_valid",
    "forward_snapshot_matches",
    "backup_artifact_present",
    "backup_status_integrity_pass",
    "backup_status_pass",
    "backup_candidate_matches",
    "backup_timestamp_present",
    "backup_timestamp_not_future",
    "backup_status_fresh",
    "backup_archive_verification_pass",
    "backup_archive_candidate_matches",
    "backup_archive_manifest_matches",
    "backup_schema_supported",
    "backup_status_hash_valid",
    "local_source_anchor_consistent",
    "task_probe_pass",
    "observation_task_pass",
    "performance_task_pass",
    "backup_task_pass",
    "no_execution_authority",
})

_TASK_CHECK_FIELDS = frozenset({
    "installed",
    "enabled",
    "state_runnable",
    "last_result_pass",
    "last_run_present",
    "last_run_not_future",
    "last_run_fresh",
})
_LOCAL_SOURCE_ANCHOR_STATUSES = frozenset({
    "VERIFIED",
    "NOT_AVAILABLE",
    "CONTRADICTION",
})


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_not_available_anchor() -> dict[str, Any]:
    return build_portfolio_forward_local_source_anchor_not_available(
        reason="CROSS_ARTIFACT_CHAIN_NOT_AVAILABLE"
    )


def _local_source_anchor_state(
    *,
    backup: dict[str, Any],
    backup_verification: dict[str, Any],
    backup_archive_verification: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Classify the independently re-read archive receipt without trusting claims."""

    backup_schema = str(backup.get("schema_version") or "")
    archive_pass = backup_archive_verification.get("status") == "PASS"
    archive_anchor_raw = backup_archive_verification.get("local_source_anchor")
    archive_anchor_verification = verify_portfolio_forward_local_source_anchor(
        archive_anchor_raw
    )
    archive_anchor = (
        dict(archive_anchor_raw)
        if archive_anchor_verification.get("status") == "PASS"
        else {}
    )

    if backup_schema == PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION:
        if archive_anchor.get("status") == "NOT_AVAILABLE":
            return "NOT_AVAILABLE", archive_anchor
        return "NOT_AVAILABLE", _safe_not_available_anchor()
    if backup_schema != PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION:
        return "CONTRADICTION", _safe_not_available_anchor()

    backup_anchor_raw = backup.get("local_source_anchor")
    backup_anchor_verification = verify_portfolio_forward_local_source_anchor(
        backup_anchor_raw
    )
    if (
        backup_verification.get("status") != "PASS"
        or backup_anchor_verification.get("status") != "PASS"
    ):
        return "CONTRADICTION", _safe_not_available_anchor()
    backup_anchor = dict(backup_anchor_raw)
    backup_anchor_status = str(backup_anchor.get("status") or "")

    if backup_anchor_status == "VERIFIED":
        if (
            archive_pass
            and archive_anchor.get("status") == "VERIFIED"
            and backup_anchor == archive_anchor
        ):
            return "VERIFIED", backup_anchor
        return "CONTRADICTION", _safe_not_available_anchor()

    if backup_anchor_status == "NOT_AVAILABLE":
        if not archive_pass or not archive_anchor:
            return "NOT_AVAILABLE", backup_anchor
        if archive_anchor.get("status") == "NOT_AVAILABLE" and backup_anchor == archive_anchor:
            return "NOT_AVAILABLE", backup_anchor
        return "CONTRADICTION", _safe_not_available_anchor()
    return "CONTRADICTION", _safe_not_available_anchor()


def _artifact_age(payload: dict[str, Any], *, now_ms: int) -> tuple[int | None, bool, bool]:
    generated_at = payload.get("generated_at")
    if (
        isinstance(generated_at, bool)
        or not isinstance(generated_at, int)
        or generated_at <= 0
    ):
        return None, False, False
    future = generated_at > int(now_ms) + 5 * 60 * 1000
    return max(int(now_ms) - generated_at, 0), True, future


def _task_checks(
    snapshot: dict[str, Any],
    *,
    now_ms: int,
    stale_after_ms: int,
) -> dict[str, bool]:
    state = str(snapshot.get("state") or "").upper()
    raw_last_result = snapshot.get("last_task_result")
    last_result = (
        raw_last_result
        if isinstance(raw_last_result, int) and not isinstance(raw_last_result, bool)
        else -1
    )
    raw_last_run_at = snapshot.get("last_run_at_ms")
    last_run_at = (
        raw_last_run_at
        if isinstance(raw_last_run_at, int) and not isinstance(raw_last_run_at, bool)
        else 0
    )
    last_run_age = max(int(now_ms) - last_run_at, 0) if last_run_at > 0 else None
    return {
        "installed": snapshot.get("installed") is True,
        "enabled": snapshot.get("enabled") is True,
        "state_runnable": state in {"READY", "RUNNING"},
        "last_result_pass": last_result == 0 or (state == "RUNNING" and last_result == RUNNING_TASK_RESULT),
        "last_run_present": last_run_at > 0,
        "last_run_not_future": last_run_at <= int(now_ms) + 5 * 60 * 1000,
        "last_run_fresh": last_run_age is not None and last_run_age <= max(int(stale_after_ms), 1),
    }


def _native_integer_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _derive_watchdog_evidence(
    *,
    now_ms: int,
    source_facts: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    task_names: tuple[str, str, str],
) -> dict[str, Any]:
    candidate_hash = str(source_facts.get("active_candidate_hash") or "")
    stale_after_ms = _native_integer_or_none(source_facts.get("stale_after_ms")) or 1
    backup_stale_after_ms = (
        _native_integer_or_none(source_facts.get("backup_stale_after_ms")) or 1
    )
    scheduler_age = source_facts.get("scheduler_status_age_ms")
    performance_age, performance_timestamp_present, performance_from_future = _artifact_age(
        {"generated_at": source_facts.get("performance_generated_at")},
        now_ms=now_ms,
    )
    backup = (
        dict(source_facts.get("backup_receipt") or {})
        if isinstance(source_facts.get("backup_receipt"), dict)
        else {}
    )
    backup_archive_verification = (
        dict(source_facts.get("backup_archive_verification") or {})
        if isinstance(source_facts.get("backup_archive_verification"), dict)
        else {}
    )
    backup_age, backup_timestamp_present, backup_from_future = _artifact_age(
        backup,
        now_ms=now_ms,
    )
    task_checks = {
        name: _task_checks(
            tasks.get(name, {}),
            now_ms=now_ms,
            stale_after_ms=(
                backup_stale_after_ms if index == 2 else stale_after_ms
            ),
        )
        for index, name in enumerate(task_names)
    }
    backup_verification = verify_portfolio_backup_status(backup)
    local_source_anchor_status, verified_source_anchor = _local_source_anchor_state(
        backup=backup,
        backup_verification=backup_verification,
        backup_archive_verification=backup_archive_verification,
    )
    backup_schema_version = str(backup.get("schema_version") or "")
    backup_status_hash = str(backup.get("status_hash") or "")
    observation_critical = dict(source_facts.get("observation_critical_checks") or {})
    performance_integrity = dict(source_facts.get("performance_integrity_checks") or {})
    observation_audit_hash = str(source_facts.get("observation_audit_hash") or "")
    performance_audit_computed_hash = str(
        source_facts.get("performance_audit_computed_hash") or ""
    )
    performance_audit_hash = str(source_facts.get("performance_audit_hash") or "")
    authority_count = _native_integer_or_none(source_facts.get("authority_violation_count"))
    embedded_authority = authority_violations({
        "source_facts": source_facts,
        "tasks": tasks,
    })
    checks = {
        "active_candidate_pass": source_facts.get("active_status") == "PASS"
        and _sha256_hex(candidate_hash),
        "scheduler_health_pass": source_facts.get("scheduler_health") == "PASS",
        "scheduler_candidate_matches": str(source_facts.get("scheduler_candidate_hash") or "")
        == candidate_hash,
        "scheduler_scheduled_invocation": source_facts.get("scheduler_scheduled_invocation")
        is True,
        "scheduler_status_fresh": isinstance(scheduler_age, int)
        and not isinstance(scheduler_age, bool)
        and 0 <= scheduler_age <= max(stale_after_ms, 1),
        "observation_artifact_present": source_facts.get("observation_artifact_present")
        is True,
        "observation_candidate_matches": str(source_facts.get("observation_candidate_hash") or "")
        == candidate_hash,
        "observation_ledger_pass": source_facts.get("observation_ledger_status") == "PASS",
        "observation_critical_checks_pass": bool(observation_critical)
        and all(value is True for value in observation_critical.values()),
        "performance_artifact_present": source_facts.get("performance_artifact_present")
        is True,
        "performance_candidate_matches": str(source_facts.get("performance_candidate_hash") or "")
        == candidate_hash,
        "performance_scheduled_invocation": source_facts.get("performance_scheduled_invocation")
        is True,
        "performance_ledger_pass": source_facts.get("performance_ledger_status") == "PASS",
        "performance_integrity_checks_pass": bool(performance_integrity)
        and all(value is True for value in performance_integrity.values()),
        "performance_timestamp_present": performance_timestamp_present,
        "performance_timestamp_not_future": not performance_from_future,
        "performance_status_fresh": performance_age is not None
        and performance_age <= max(stale_after_ms, 1),
        "forward_snapshot_hash_valid": _sha256_hex(performance_audit_hash)
        and _sha256_hex(performance_audit_computed_hash)
        and performance_audit_computed_hash == performance_audit_hash,
        "forward_snapshot_matches": _sha256_hex(observation_audit_hash)
        and observation_audit_hash == performance_audit_computed_hash,
        "backup_artifact_present": bool(backup),
        "backup_status_integrity_pass": backup_verification.get("status") == "PASS",
        "backup_status_pass": backup.get("status") == "PASS"
        and backup.get("verification_status") == "PASS",
        "backup_candidate_matches": str(backup.get("candidate_hash") or "") == candidate_hash,
        "backup_timestamp_present": backup_timestamp_present,
        "backup_timestamp_not_future": not backup_from_future,
        "backup_status_fresh": backup_age is not None
        and backup_age <= max(backup_stale_after_ms, 1),
        "backup_archive_verification_pass": backup_archive_verification.get("status") == "PASS",
        "backup_archive_candidate_matches": str(
            backup_archive_verification.get("candidate_hash") or ""
        )
        == candidate_hash,
        "backup_archive_manifest_matches": bool(backup.get("manifest_hash"))
        and str(backup_archive_verification.get("manifest_hash") or "")
        == str(backup.get("manifest_hash") or ""),
        "backup_schema_supported": backup_schema_version
        in {
            PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
            PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
        },
        "backup_status_hash_valid": _sha256_hex(backup_status_hash),
        "local_source_anchor_consistent": local_source_anchor_status != "CONTRADICTION",
        "task_probe_pass": source_facts.get("task_probe_status") == "PASS",
        "observation_task_pass": all(task_checks[task_names[0]].values()),
        "performance_task_pass": all(task_checks[task_names[1]].values()),
        "backup_task_pass": all(task_checks[task_names[2]].values()),
        "no_execution_authority": authority_count == 0 and not embedded_authority,
    }
    return {
        "candidate_hash": candidate_hash,
        "checks": checks,
        "status_ages_ms": {
            "scheduler": scheduler_age,
            "performance": performance_age,
            "backup": backup_age,
        },
        "task_checks": task_checks,
        "task_probe_status": str(source_facts.get("task_probe_status") or "BLOCK"),
        "task_probe_error": str(source_facts.get("task_probe_error") or "")[:500],
        "scheduler_status": str(source_facts.get("scheduler_status") or ""),
        "observation_status": str(source_facts.get("observation_status") or ""),
        "performance_status": str(source_facts.get("performance_status") or ""),
        "backup_status": str(backup.get("status") or ""),
        "backup_archive_status": str(backup_archive_verification.get("status") or "BLOCK"),
        "backup_manifest_hash": str(backup.get("manifest_hash") or ""),
        "backup_schema_version": backup_schema_version,
        "backup_status_hash": backup_status_hash,
        "local_source_anchor_status": local_source_anchor_status,
        "verified_source_anchor": verified_source_anchor,
        "snapshot_hash": performance_audit_hash,
    }


def build_portfolio_forward_watchdog_status(
    *,
    now_ms: int,
    active: dict[str, Any],
    scheduler: dict[str, Any],
    observation: dict[str, Any],
    performance: dict[str, Any],
    backup: dict[str, Any],
    backup_verification: dict[str, Any],
    backup_archive_verification: dict[str, Any],
    task_probe: dict[str, Any],
    stale_after_ms: int = DEFAULT_STALE_AFTER_MS,
    backup_stale_after_ms: int = DEFAULT_BACKUP_STALE_AFTER_MS,
    observation_task_name: str = OBSERVATION_TASK_NAME,
    performance_task_name: str = PERFORMANCE_TASK_NAME,
    backup_task_name: str = BACKUP_TASK_NAME,
) -> dict[str, Any]:
    candidate = dict(active.get("candidate") or {})
    registry = dict(active.get("registry") or {})
    candidate_hash = str(candidate.get("candidate_hash") or registry.get("candidate_hash") or "")
    observation_readiness = dict(observation.get("readiness") or {})
    observation_critical = dict(observation_readiness.get("critical_checks") or {})
    observation_audit = dict(observation_readiness.get("ledger_audit") or {})
    performance_readiness = dict(performance.get("readiness") or {})
    performance_integrity = dict(performance_readiness.get("integrity_checks") or {})
    performance_summary = dict(performance.get("performance") or {})
    performance_audit = dict(performance.get("shadow_audit") or {})
    performance_audit_hash = str(performance.get("shadow_audit_hash") or "")
    required_task_names = (observation_task_name, performance_task_name, backup_task_name)
    raw_tasks = task_probe.get("tasks") if isinstance(task_probe.get("tasks"), dict) else {}
    tasks = {
        name: dict(raw_tasks.get(name) or {})
        if isinstance(raw_tasks.get(name), dict)
        else {}
        for name in required_task_names
    }
    authority_paths = authority_violations({
        "active_registry": registry,
        "active_candidate": candidate,
        "scheduler": scheduler,
        "observation": observation,
        "performance": performance,
        "backup": backup,
        "backup_verification": backup_verification,
        "backup_archive_verification": backup_archive_verification,
    })
    archive_anchor_raw = backup_archive_verification.get("local_source_anchor")
    archive_anchor = (
        dict(archive_anchor_raw)
        if isinstance(archive_anchor_raw, dict)
        else _safe_not_available_anchor()
    )
    scheduler_age = _native_integer_or_none(scheduler.get("status_age_ms"))
    if scheduler_age is not None and scheduler_age < 0:
        scheduler_age = None
    performance_generated_at = _native_integer_or_none(performance.get("generated_at"))
    source_facts = {
        "schema_version": PORTFOLIO_FORWARD_WATCHDOG_SOURCE_FACTS_SCHEMA_VERSION,
        "stale_after_ms": max(int(stale_after_ms), 1),
        "backup_stale_after_ms": max(int(backup_stale_after_ms), 1),
        "active_status": str(active.get("status") or ""),
        "active_candidate_hash": candidate_hash,
        "scheduler_status": str(scheduler.get("status") or ""),
        "scheduler_health": str(scheduler.get("health") or ""),
        "scheduler_candidate_hash": str(scheduler.get("candidate_hash") or ""),
        "scheduler_scheduled_invocation": scheduler.get("scheduled_invocation") is True,
        "scheduler_status_age_ms": scheduler_age,
        "observation_artifact_present": bool(observation),
        "observation_status": str(
            observation_readiness.get("status") or observation.get("status") or ""
        ),
        "observation_candidate_hash": str(observation.get("candidate_hash") or ""),
        "observation_ledger_status": str(observation_audit.get("status") or ""),
        "observation_audit_hash": canonical_hash(observation_audit)
        if observation_audit
        else "",
        "observation_critical_checks": observation_critical,
        "performance_artifact_present": bool(performance),
        "performance_status": str(
            performance_readiness.get("status") or performance.get("status") or ""
        ),
        "performance_candidate_hash": str(performance.get("candidate_hash") or ""),
        "performance_scheduled_invocation": performance.get("scheduled_invocation") is True,
        "performance_ledger_status": str(performance_summary.get("status") or ""),
        "performance_integrity_checks": performance_integrity,
        "performance_generated_at": performance_generated_at,
        "performance_audit_computed_hash": canonical_hash(performance_audit)
        if performance_audit
        else "",
        "performance_audit_hash": performance_audit_hash,
        "backup_receipt": dict(backup),
        "backup_archive_verification": {
            "status": str(backup_archive_verification.get("status") or "BLOCK"),
            "candidate_hash": str(backup_archive_verification.get("candidate_hash") or ""),
            "manifest_hash": str(backup_archive_verification.get("manifest_hash") or ""),
            "local_source_anchor": archive_anchor,
        },
        "task_probe_status": str(task_probe.get("status") or "BLOCK"),
        "task_probe_error": str(task_probe.get("error") or "")[:500],
        "authority_violation_count": len(authority_paths),
    }
    derived = _derive_watchdog_evidence(
        now_ms=int(now_ms),
        source_facts=source_facts,
        tasks=tasks,
        task_names=required_task_names,
    )
    checks = derived["checks"]
    blockers = [name for name, passed in checks.items() if not passed]
    if authority_paths:
        blockers.extend(f"execution_authority:{path}" for path in authority_paths)
    status = "PASS" if not blockers else "BLOCK"
    payload = {
        "schema_version": PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION,
        "status": status,
        "severity": "INFO" if status == "PASS" else "CRITICAL",
        "generated_at": int(now_ms),
        "candidate_hash": derived["candidate_hash"],
        "source_facts": source_facts,
        "checks": checks,
        "blockers": list(dict.fromkeys(blockers)),
        "status_ages_ms": derived["status_ages_ms"],
        "task_checks": derived["task_checks"],
        "tasks": tasks,
        "task_names": {
            "observation": observation_task_name,
            "performance": performance_task_name,
            "backup": backup_task_name,
        },
        "task_probe_status": derived["task_probe_status"],
        "task_probe_error": derived["task_probe_error"],
        "scheduler_status": derived["scheduler_status"],
        "observation_status": derived["observation_status"],
        "performance_status": derived["performance_status"],
        "backup_status": derived["backup_status"],
        "backup_archive_status": derived["backup_archive_status"],
        "backup_manifest_hash": derived["backup_manifest_hash"],
        "backup_schema_version": derived["backup_schema_version"],
        "backup_status_hash": derived["backup_status_hash"],
        "local_source_anchor_status": derived["local_source_anchor_status"],
        "verified_source_anchor": derived["verified_source_anchor"],
        "snapshot_hash": derived["snapshot_hash"],
        "monitoring_only": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    alert_condition = {
        "status": status,
        "candidate_hash": derived["candidate_hash"],
        "blockers": payload["blockers"],
        "task_checks": derived["task_checks"],
        "local_source_anchor_status": derived["local_source_anchor_status"],
        "verified_source_anchor_hash": str(
            derived["verified_source_anchor"].get("anchor_hash") or ""
        ),
        "source_facts_hash": canonical_hash(source_facts),
    }
    payload["alert_condition_hash"] = canonical_hash(alert_condition)
    payload["status_hash"] = canonical_hash(payload)
    return payload


def _watchdog_verification_result(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_portfolio_forward_watchdog_status_v2(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Frozen verifier for the historical v2 watchdog artifact."""

    blockers: list[str] = []
    clean = dict(payload or {})
    supplied_hash = str(clean.pop("status_hash", "") or "")
    if payload.get("schema_version") != PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION:
        blockers.append("watchdog_schema_invalid")
    if not supplied_hash or canonical_hash(clean) != supplied_hash:
        blockers.append("watchdog_status_hash_invalid")
    checks_raw = payload.get("checks")
    checks = dict(checks_raw) if isinstance(checks_raw, dict) else {}
    if not isinstance(checks_raw, dict):
        blockers.append("watchdog_checks_invalid")
    expected = "PASS" if checks and all(value is True for value in checks.values()) else "BLOCK"
    if payload.get("status") != expected:
        blockers.append("watchdog_status_inconsistent")
    if authority_violations(payload):
        blockers.append("watchdog_contains_execution_authority")
    return _watchdog_verification_result(blockers)


def _verify_portfolio_forward_watchdog_status_v3(
    payload: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if set(payload) != PORTFOLIO_FORWARD_WATCHDOG_V3_FIELDS:
        blockers.append("watchdog_fields_invalid")
    clean = dict(payload)
    supplied_hash = clean.pop("status_hash", "")
    if not _sha256_hex(supplied_hash) or canonical_hash(clean) != supplied_hash:
        blockers.append("watchdog_status_hash_invalid")
    if payload.get("schema_version") != PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION:
        blockers.append("watchdog_schema_invalid")
    generated_at = payload.get("generated_at")
    if (
        isinstance(generated_at, bool)
        or not isinstance(generated_at, int)
        or generated_at <= 0
        or generated_at > 9_007_199_254_740_991
    ):
        blockers.append("watchdog_generated_at_invalid")
    candidate_hash = payload.get("candidate_hash")
    if not isinstance(candidate_hash, str) or (candidate_hash and not _sha256_hex(candidate_hash)):
        blockers.append("watchdog_candidate_hash_invalid")

    source_facts_raw = payload.get("source_facts")
    source_facts = dict(source_facts_raw) if isinstance(source_facts_raw, dict) else {}
    if set(source_facts) != PORTFOLIO_FORWARD_WATCHDOG_V3_SOURCE_FACT_FIELDS:
        blockers.append("watchdog_source_facts_fields_invalid")
    if (
        source_facts.get("schema_version")
        != PORTFOLIO_FORWARD_WATCHDOG_SOURCE_FACTS_SCHEMA_VERSION
    ):
        blockers.append("watchdog_source_facts_schema_invalid")
    for field in ("stale_after_ms", "backup_stale_after_ms"):
        value = source_facts.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            or value > 9_007_199_254_740_991
        ):
            blockers.append(f"watchdog_source_facts_{field}_invalid")
    for field in (
        "active_status",
        "active_candidate_hash",
        "scheduler_status",
        "scheduler_health",
        "scheduler_candidate_hash",
        "observation_status",
        "observation_candidate_hash",
        "observation_ledger_status",
        "observation_audit_hash",
        "performance_status",
        "performance_candidate_hash",
        "performance_ledger_status",
        "performance_audit_computed_hash",
        "performance_audit_hash",
        "task_probe_status",
        "task_probe_error",
    ):
        value = source_facts.get(field)
        limit = 500 if field == "task_probe_error" else 256
        if not isinstance(value, str) or len(value) > limit:
            blockers.append(f"watchdog_source_facts_{field}_invalid")
    for field in (
        "scheduler_scheduled_invocation",
        "observation_artifact_present",
        "performance_artifact_present",
        "performance_scheduled_invocation",
    ):
        if not isinstance(source_facts.get(field), bool):
            blockers.append(f"watchdog_source_facts_{field}_invalid")
    scheduler_fact_age = source_facts.get("scheduler_status_age_ms")
    if scheduler_fact_age is not None and (
        isinstance(scheduler_fact_age, bool)
        or not isinstance(scheduler_fact_age, int)
        or scheduler_fact_age < 0
    ):
        blockers.append("watchdog_source_facts_scheduler_status_age_ms_invalid")
    performance_generated_at = source_facts.get("performance_generated_at")
    if performance_generated_at is not None and (
        isinstance(performance_generated_at, bool)
        or not isinstance(performance_generated_at, int)
        or performance_generated_at <= 0
    ):
        blockers.append("watchdog_source_facts_performance_generated_at_invalid")
    for field in (
        "observation_critical_checks",
        "performance_integrity_checks",
        "backup_receipt",
        "backup_archive_verification",
    ):
        if not isinstance(source_facts.get(field), dict):
            blockers.append(f"watchdog_source_facts_{field}_invalid")
    for field in ("observation_critical_checks", "performance_integrity_checks"):
        values = source_facts.get(field)
        if isinstance(values, dict) and any(not isinstance(value, bool) for value in values.values()):
            blockers.append(f"watchdog_source_facts_{field}_invalid")
    authority_count = source_facts.get("authority_violation_count")
    if (
        isinstance(authority_count, bool)
        or not isinstance(authority_count, int)
        or authority_count < 0
    ):
        blockers.append("watchdog_source_facts_authority_violation_count_invalid")
    archive_facts_raw = source_facts.get("backup_archive_verification")
    archive_facts = dict(archive_facts_raw) if isinstance(archive_facts_raw, dict) else {}
    if set(archive_facts) != PORTFOLIO_FORWARD_WATCHDOG_V3_ARCHIVE_FACT_FIELDS:
        blockers.append("watchdog_archive_facts_fields_invalid")
    for field in ("status", "candidate_hash", "manifest_hash"):
        if not isinstance(archive_facts.get(field), str):
            blockers.append(f"watchdog_archive_facts_{field}_invalid")
    if not isinstance(archive_facts.get("local_source_anchor"), dict):
        blockers.append("watchdog_archive_facts_local_source_anchor_invalid")

    checks_raw = payload.get("checks")
    checks = dict(checks_raw) if isinstance(checks_raw, dict) else {}
    if set(checks) != PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS:
        blockers.append("watchdog_checks_inventory_invalid")
    if any(not isinstance(value, bool) for value in checks.values()):
        blockers.append("watchdog_check_value_invalid")
    expected_status = (
        "PASS"
        if set(checks) == PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS
        and all(value is True for value in checks.values())
        else "BLOCK"
    )
    if payload.get("status") != expected_status:
        blockers.append("watchdog_status_inconsistent")
    expected_severity = "INFO" if expected_status == "PASS" else "CRITICAL"
    if payload.get("severity") != expected_severity:
        blockers.append("watchdog_severity_inconsistent")

    raw_payload_blockers = payload.get("blockers")
    payload_blockers = (
        list(raw_payload_blockers)
        if isinstance(raw_payload_blockers, list)
        and all(isinstance(item, str) and item and len(item) <= 500 for item in raw_payload_blockers)
        and len(raw_payload_blockers) == len(set(raw_payload_blockers))
        else []
    )
    if payload_blockers != raw_payload_blockers:
        blockers.append("watchdog_blockers_invalid")
    expected_check_blockers = {
        name for name, passed in checks.items() if passed is not True
    }
    actual_check_blockers = {
        item for item in payload_blockers if item in PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS
    }
    if actual_check_blockers != expected_check_blockers:
        blockers.append("watchdog_check_blockers_inconsistent")
    if any(
        item not in PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS
        and not item.startswith("execution_authority:")
        for item in payload_blockers
    ):
        blockers.append("watchdog_blocker_unknown")

    status_ages = payload.get("status_ages_ms")
    status_age_values: dict[str, Any] = {}
    if not isinstance(status_ages, dict) or set(status_ages) != {
        "scheduler",
        "performance",
        "backup",
    }:
        blockers.append("watchdog_status_ages_invalid")
    else:
        status_age_values = dict(status_ages)
        for value in status_ages.values():
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                blockers.append("watchdog_status_age_value_invalid")
                break

    task_names_raw = payload.get("task_names")
    task_names = dict(task_names_raw) if isinstance(task_names_raw, dict) else {}
    if set(task_names) != {"observation", "performance", "backup"}:
        blockers.append("watchdog_task_names_invalid")
    raw_required_task_names = tuple(task_names.get(role) for role in (
        "observation",
        "performance",
        "backup",
    ))
    required_task_names = tuple(
        name if isinstance(name, str) else "" for name in raw_required_task_names
    )
    if (
        any(not name or len(name) > 256 for name in required_task_names)
        or len(set(required_task_names)) != 3
    ):
        blockers.append("watchdog_task_name_values_invalid")
    tasks_raw = payload.get("tasks")
    tasks = dict(tasks_raw) if isinstance(tasks_raw, dict) else {}
    task_checks_raw = payload.get("task_checks")
    task_checks = dict(task_checks_raw) if isinstance(task_checks_raw, dict) else {}
    if set(tasks) != set(required_task_names) or any(
        not isinstance(value, dict) for value in tasks.values()
    ):
        blockers.append("watchdog_tasks_invalid")
    if set(task_checks) != set(required_task_names):
        blockers.append("watchdog_task_checks_invalid")
    else:
        for value in task_checks.values():
            if (
                not isinstance(value, dict)
                or set(value) != _TASK_CHECK_FIELDS
                or any(not isinstance(item, bool) for item in value.values())
            ):
                blockers.append("watchdog_task_check_fields_invalid")
                break
    task_structures_valid = (
        set(tasks) == set(required_task_names)
        and all(isinstance(value, dict) for value in tasks.values())
        and set(task_checks) == set(required_task_names)
        and all(
            isinstance(value, dict)
            and set(value) == _TASK_CHECK_FIELDS
            and all(isinstance(item, bool) for item in value.values())
            for value in task_checks.values()
        )
    )
    derived: dict[str, Any] = {}
    if task_structures_valid and len(set(required_task_names)) == 3:
        derived = _derive_watchdog_evidence(
            now_ms=(
                generated_at
                if isinstance(generated_at, int)
                and not isinstance(generated_at, bool)
                and generated_at > 0
                else 0
            ),
            source_facts=source_facts,
            tasks={name: dict(tasks[name]) for name in required_task_names},
            task_names=required_task_names,
        )
        expected_checks = derived["checks"]
        for name in PORTFOLIO_FORWARD_WATCHDOG_V3_CHECK_FIELDS:
            if checks.get(name) is not expected_checks.get(name):
                blockers.append(f"watchdog_check_semantics_inconsistent:{name}")
        projection_fields = (
            "candidate_hash",
            "status_ages_ms",
            "task_checks",
            "task_probe_status",
            "task_probe_error",
            "scheduler_status",
            "observation_status",
            "performance_status",
            "backup_status",
            "backup_archive_status",
            "backup_manifest_hash",
            "backup_schema_version",
            "backup_status_hash",
            "local_source_anchor_status",
            "verified_source_anchor",
            "snapshot_hash",
        )
        for field in projection_fields:
            if payload.get(field) != derived.get(field):
                blockers.append(f"watchdog_projection_inconsistent:{field}")

    backup_schema_version = payload.get("backup_schema_version")
    schema_supported = backup_schema_version in {
        PORTFOLIO_BACKUP_STATUS_V1_SCHEMA_VERSION,
        PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION,
    }
    if not isinstance(backup_schema_version, str):
        blockers.append("watchdog_backup_schema_version_invalid")
    if checks.get("backup_schema_supported") is not schema_supported:
        blockers.append("watchdog_backup_schema_check_inconsistent")
    backup_status_hash_valid = _sha256_hex(payload.get("backup_status_hash"))
    if checks.get("backup_status_hash_valid") is not backup_status_hash_valid:
        blockers.append("watchdog_backup_status_hash_check_inconsistent")

    local_status = payload.get("local_source_anchor_status")
    if local_status not in _LOCAL_SOURCE_ANCHOR_STATUSES:
        blockers.append("watchdog_local_source_anchor_status_invalid")
    source_anchor = payload.get("verified_source_anchor")
    source_anchor_verification = verify_portfolio_forward_local_source_anchor(source_anchor)
    if source_anchor_verification.get("status") != "PASS":
        blockers.append("watchdog_verified_source_anchor_invalid")
    source_anchor_payload = dict(source_anchor or {}) if isinstance(source_anchor, dict) else {}
    expected_consistency = local_status != "CONTRADICTION"
    if checks.get("local_source_anchor_consistent") is not expected_consistency:
        blockers.append("watchdog_local_source_anchor_check_inconsistent")
    if local_status == "VERIFIED":
        if (
            backup_schema_version != PORTFOLIO_BACKUP_STATUS_SCHEMA_VERSION
            or source_anchor_payload.get("status") != "VERIFIED"
            or source_anchor_payload.get("candidate_hash") != candidate_hash
        ):
            blockers.append("watchdog_verified_source_anchor_binding_invalid")
    elif local_status in {"NOT_AVAILABLE", "CONTRADICTION"}:
        if source_anchor_payload.get("status") != "NOT_AVAILABLE":
            blockers.append("watchdog_unavailable_source_anchor_invalid")

    for field in (
        "task_probe_status",
        "task_probe_error",
        "scheduler_status",
        "observation_status",
        "performance_status",
        "backup_status",
        "backup_archive_status",
        "backup_manifest_hash",
        "backup_status_hash",
        "snapshot_hash",
    ):
        value = payload.get(field)
        limit = 500 if field == "task_probe_error" else 256
        if not isinstance(value, str) or len(value) > limit:
            blockers.append(f"watchdog_{field}_invalid")
    expected_alert_condition = {
        "status": payload.get("status"),
        "candidate_hash": str(candidate_hash or ""),
        "blockers": payload_blockers,
        "task_checks": task_checks,
        "local_source_anchor_status": local_status,
        "verified_source_anchor_hash": str(
            source_anchor_payload.get("anchor_hash") or ""
        ),
        "source_facts_hash": canonical_hash(source_facts),
    }
    if (
        not _sha256_hex(payload.get("alert_condition_hash"))
        or payload.get("alert_condition_hash") != canonical_hash(expected_alert_condition)
    ):
        blockers.append("watchdog_alert_condition_hash_invalid")
    if (
        payload.get("monitoring_only") is not True
        or payload.get("research_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("watchdog_scope_invalid")
    if authority_violations(payload):
        blockers.append("watchdog_contains_execution_authority")
    return _watchdog_verification_result(blockers)


def verify_portfolio_forward_watchdog_status(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _watchdog_verification_result(["watchdog_status_not_object"])
    try:
        if not local_receipt_json_shape_valid(payload):
            return _watchdog_verification_result(["watchdog_status_structure_invalid"])
        schema_version = payload.get("schema_version")
        if schema_version == PORTFOLIO_FORWARD_WATCHDOG_V2_SCHEMA_VERSION:
            return _verify_portfolio_forward_watchdog_status_v2(dict(payload))
        if schema_version == PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION:
            return _verify_portfolio_forward_watchdog_status_v3(dict(payload))
        return _watchdog_verification_result(["watchdog_schema_invalid"])
    except MemoryError:
        return _watchdog_verification_result(["watchdog_verification_memory_exhausted"])
    except (AttributeError, KeyError, OverflowError, RecursionError, TypeError, ValueError):
        return _watchdog_verification_result(["watchdog_status_structure_invalid"])


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def record_portfolio_forward_watchdog_status(
    *,
    status_path: Path | str,
    alert_path: Path | str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    status_file = Path(status_path)
    alert_file = Path(alert_path)
    previous: dict[str, Any] = {}
    previous_artifact = read_forward_json_artifact(
        status_file,
        byte_limit=MAX_PORTFOLIO_FORWARD_CONTROL_ARTIFACT_BYTES,
        size_limit_blocker="watchdog_previous_status_size_limit_exceeded",
    )
    if previous_artifact.status == "PASS":
        decoded = dict(previous_artifact.payload)
        if verify_portfolio_forward_watchdog_status(decoded).get("status") == "PASS":
            previous = decoded
    _atomic_write_json(status_file, payload)

    current_status = str(payload.get("status") or "BLOCK")
    previous_status = str(previous.get("status") or "")
    changed_block = (
        current_status == "BLOCK"
        and str(payload.get("alert_condition_hash") or "")
        != str(previous.get("alert_condition_hash") or "")
    )
    recovered = current_status == "PASS" and previous_status == "BLOCK"
    if changed_block or recovered:
        alert = {
            "schema_version": PORTFOLIO_FORWARD_WATCHDOG_SCHEMA_VERSION,
            "event_type": (
                "PORTFOLIO_FORWARD_WATCHDOG_RECOVERY"
                if recovered
                else "PORTFOLIO_FORWARD_WATCHDOG_ALERT"
            ),
            "generated_at": int(payload.get("generated_at") or 0),
            "candidate_hash": str(payload.get("candidate_hash") or ""),
            "condition_hash": str(payload.get("alert_condition_hash") or ""),
            "blockers": list(payload.get("blockers") or []),
            "monitoring_only": True,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        alert["alert_hash"] = canonical_hash(alert)
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        with alert_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(alert, ensure_ascii=False, sort_keys=True) + "\n")
    return payload
