from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
import uuid

from .market_calendar import build_market_calendar_contract, infer_market_calendar
from .portfolio_shadow import verify_forward_observation_change, verify_latest_forward_observation_receipt


PORTFOLIO_FORWARD_SCHEDULER_SCHEMA_VERSION = "portfolio-forward-scheduler-v1"
PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION = "portfolio-forward-scheduler-status-v2"
PORTFOLIO_FORWARD_DASHBOARD_SCHEMA_VERSION = "portfolio-forward-dashboard-v4"
FORWARD_OBSERVER_JOB_RECEIPT_SCHEMA_VERSION = "portfolio-forward-observer-job-receipt-v1"
FORWARD_OBSERVER_ATTEMPT_EVIDENCE_SCHEMA_VERSION = "portfolio-forward-scheduler-attempt-evidence-v1"
RECENT_OBSERVER_JOB_LIMIT = 2
DEFAULT_SCHEDULER_STATUS_FILE = "portfolio_forward_scheduler_status.json"
DEFAULT_SCHEDULER_ALERT_FILE = "portfolio_forward_scheduler_alerts.jsonl"
DEFAULT_SCHEDULER_LOCK_FILE = "portfolio_forward_scheduler.lock"
CAPTURE_FINALIZATION_DELAY_MS = 5 * 60 * 1000
CAPTURE_DEADLINE_SAFETY_MS = 5 * 60 * 1000
SCHEDULER_STALE_AFTER_MS = 45 * 60 * 1000

_OBSERVER_ATTEMPT_CLAIM_FIELDS = (
    "job_id",
    "observer_job_id",
    "candidate_hash",
    "candidate_activation_registry_hash",
    "candidate_activated_at",
    "scheduled_decision_hash",
    "due_signal_dates",
    "due_signal_dates_hash",
    "started_at_ms",
    "finished_at_ms",
    "duration_ms",
    "process_state",
    "return_code",
    "observer_ok",
    "observer_status",
    "observer_blockers",
    "observer_artifact_hash",
    "observer_artifact_verified",
    "observer_artifact_post_ledger_match",
    "observer_evidence_consistent",
    "observer_candidate_hash",
    "post_candidate_hash",
    "post_activation_registry_hash",
    "post_activated_at",
    "incremental_plan_hash",
    "work_summary_hash",
    "records_hash",
    "processed_count",
    "record_count",
    "processed_signal_dates",
    "pre_ledger",
    "post_ledger",
    "previous_receipt_hash",
    "outcome",
    "reconciliation_required",
    "failure_reasons",
    "observation_only",
    "simulation_only",
    "paper_authorized",
    "live_order_allowed",
)


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_hex(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _timestamp_ms(value: Any) -> int:
    try:
        return int(datetime.fromisoformat(str(value or "")).astimezone(timezone.utc).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def _valid_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 10:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def build_forward_scheduler_decision(
    *,
    candidate: dict[str, Any],
    attested_now_ms: int,
    observed_dates: list[str],
    capture_event_dates: list[str],
    ledger_audit: dict[str, Any],
    calendar_name: str = "",
    finalization_delay_ms: int = CAPTURE_FINALIZATION_DELAY_MS,
    deadline_safety_ms: int = CAPTURE_DEADLINE_SAFETY_MS,
) -> dict[str, Any]:
    blockers: list[str] = []
    candidate_hash = str(candidate.get("candidate_hash") or "")
    candidate_last = _valid_date(candidate.get("dataset_last"))
    if not candidate_hash:
        blockers.append("candidate_hash_missing")
    if not candidate_last:
        blockers.append("candidate_dataset_last_invalid")
    if (
        candidate.get("research_only") is not True
        or candidate.get("paper_authorized") is not False
        or candidate.get("live_order_allowed") is not False
    ):
        blockers.append("candidate_execution_authority_invalid")
    now_ms = int(attested_now_ms or 0)
    if now_ms <= 0:
        blockers.append("attested_now_invalid")
    ledger_status = str(ledger_audit.get("status") or "MISSING").upper()
    ledger_candidate_hash = str(ledger_audit.get("candidate_hash") or "")
    if ledger_status == "BLOCK":
        blockers.append("forward_ledger_already_blocked")
    elif ledger_status != "PASS":
        blockers.append(f"forward_ledger_not_verified:{ledger_status}")
    if ledger_candidate_hash != candidate_hash:
        blockers.append("forward_ledger_candidate_identity_mismatch")

    benchmark = str((candidate.get("spec") or {}).get("benchmark_symbol") or "SPY")
    resolved_calendar = infer_market_calendar(benchmark, explicit=calendar_name)
    calendar: dict[str, Any] = {}
    schedule: list[dict[str, Any]] = []
    if not blockers or blockers == ["forward_ledger_already_blocked"]:
        now_date = datetime.fromtimestamp(max(now_ms, 0) / 1000.0, tz=timezone.utc).date()
        calendar = build_market_calendar_contract(
            calendar_name=resolved_calendar,
            start_date=candidate_last,
            end_date=(now_date + timedelta(days=21)).isoformat(),
        )
        if calendar.get("status") != "PASS":
            blockers.extend(f"calendar:{item}" for item in calendar.get("blockers") or ["calendar_blocked"])
        schedule = [
            dict(item) for item in calendar.get("schedule") or []
            if str(item.get("date") or "") > candidate_last
        ]
        if len(schedule) < 2:
            blockers.append("calendar_has_no_complete_capture_window")

    accounted_dates = {
        clean for clean in (
            _valid_date(item) for item in [*observed_dates, *capture_event_dates]
        ) if clean
    }
    windows: list[dict[str, Any]] = []
    delay_ms = max(int(finalization_delay_ms), 0)
    safety_ms = max(int(deadline_safety_ms), 0)
    for session, next_session in zip(schedule, schedule[1:]):
        signal_date = str(session.get("date") or "")
        close_ms = _timestamp_ms(session.get("close_utc"))
        next_open_ms = _timestamp_ms(next_session.get("open_utc"))
        not_before_ms = close_ms + delay_ms
        deadline_ms = next_open_ms - safety_ms
        if not close_ms or not next_open_ms or deadline_ms <= not_before_ms:
            blockers.append(f"capture_window_invalid:{signal_date}")
            continue
        windows.append({
            "signal_date": signal_date,
            "session_close_ms": close_ms,
            "capture_not_before_ms": not_before_ms,
            "capture_deadline_ms": deadline_ms,
            "next_session_date": str(next_session.get("date") or ""),
            "accounted": signal_date in accounted_dates,
        })

    due_windows = [
        item for item in windows
        if not item["accounted"] and item["capture_not_before_ms"] <= now_ms < item["capture_deadline_ms"]
    ]
    overdue_windows = [
        item for item in windows
        if not item["accounted"] and now_ms >= item["capture_deadline_ms"]
    ]
    finalizing_windows = [
        item for item in windows
        if not item["accounted"] and item["session_close_ms"] <= now_ms < item["capture_not_before_ms"]
    ]

    if "forward_ledger_already_blocked" in blockers:
        status = "FORWARD_LEDGER_BLOCKED"
        action = "NONE"
        severity = "CRITICAL"
        due_dates: list[str] = []
    elif blockers:
        status = "SCHEDULER_DECISION_BLOCKED"
        action = "NONE"
        severity = "ERROR"
        due_dates = []
    elif overdue_windows:
        status = "OVERDUE_CAPTURE_AUDIT_REQUIRED"
        action = "RUN_OBSERVER"
        severity = "CRITICAL"
        due_dates = [str(item["signal_date"]) for item in overdue_windows]
    elif due_windows:
        status = "CAPTURE_WINDOW_OPEN"
        action = "RUN_OBSERVER"
        severity = "DUE"
        due_dates = [str(item["signal_date"]) for item in due_windows]
    elif finalizing_windows:
        status = "WAITING_FOR_BAR_FINALIZATION"
        action = "NONE"
        severity = "INFO"
        due_dates = [str(item["signal_date"]) for item in finalizing_windows]
    else:
        status = "UP_TO_DATE"
        action = "NONE"
        severity = "INFO"
        due_dates = []

    future_checks = [
        int(item["capture_not_before_ms"])
        for item in windows
        if not item["accounted"] and int(item["capture_not_before_ms"]) > now_ms
    ]
    pending_windows = [dict(item) for item in windows if not item["accounted"]]
    next_window = min(
        pending_windows,
        key=lambda item: (int(item["capture_not_before_ms"]), str(item["signal_date"])),
        default={},
    )
    next_window.pop("accounted", None)
    payload = {
        "schema_version": PORTFOLIO_FORWARD_SCHEDULER_SCHEMA_VERSION,
        "status": status,
        "action": action,
        "severity": severity,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_hash": candidate_hash,
        "candidate_dataset_last": candidate_last,
        "calendar_name": resolved_calendar,
        "calendar_contract_hash": str(calendar.get("contract_hash") or ""),
        "calendar_schedule_hash": str(calendar.get("schedule_hash") or ""),
        "attested_now_ms": now_ms,
        "accounted_date_count": len(accounted_dates),
        "due_signal_dates": due_dates,
        "overdue_signal_dates": [str(item["signal_date"]) for item in overdue_windows],
        "next_check_at_ms": min(future_checks) if future_checks else 0,
        "next_capture_window": next_window,
        "finalization_delay_ms": delay_ms,
        "deadline_safety_ms": safety_ms,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["schedule_decision_hash"] = _canonical_hash(payload)
    return payload


def _strict_int(value: Any, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if minimum is not None and value < minimum:
        return None
    return value


def _verify_job_ledger_snapshot(snapshot: Any) -> list[str]:
    payload = dict(snapshot) if isinstance(snapshot, dict) else {}
    blockers: list[str] = []
    required = {
        "status",
        "candidate_hash",
        "ledger_audit_hash",
        "observation_chain_hash",
        "observation_chain_count",
        "last_signal_date",
        "latest_observation_hash",
        "snapshot_hash",
    }
    if not payload or set(payload) != required:
        return ["observer_job_ledger_snapshot_invalid"]
    if str(payload.get("status") or "").upper() not in {"PASS", "BLOCK"}:
        blockers.append("observer_job_ledger_status_invalid")
    if not str(payload.get("candidate_hash") or ""):
        blockers.append("observer_job_ledger_candidate_missing")
    for field in ("ledger_audit_hash", "observation_chain_hash"):
        if not _sha256_hex(payload.get(field)):
            blockers.append(f"observer_job_{field}_invalid")
    count = _strict_int(payload.get("observation_chain_count"), minimum=0)
    if count is None:
        blockers.append("observer_job_ledger_count_invalid")
        count = -1
    last_date = _valid_date(payload.get("last_signal_date"))
    latest_hash = str(payload.get("latest_observation_hash") or "")
    if count == 0:
        if str(payload.get("last_signal_date") or "") or latest_hash:
            blockers.append("observer_job_empty_ledger_watermark_invalid")
    elif not last_date or not _sha256_hex(latest_hash):
        blockers.append("observer_job_ledger_watermark_invalid")
    expected_hash = str(payload.get("snapshot_hash") or "")
    clean = dict(payload)
    clean.pop("snapshot_hash", None)
    if not _sha256_hex(expected_hash) or expected_hash != _canonical_hash(clean):
        blockers.append("observer_job_ledger_snapshot_hash_invalid")
    return list(dict.fromkeys(blockers))


def _derive_observer_job_outcome(receipt: dict[str, Any]) -> tuple[str, bool, list[str]]:
    failures: list[str] = []
    process_state = str(receipt.get("process_state") or "")
    if process_state == "TIMED_OUT":
        failures.append("observer_timeout")
    elif process_state == "LAUNCH_FAILED":
        failures.append("observer_launch_failed")
    if receipt.get("observer_artifact_verified") is not True:
        failures.append("observer_artifact_unverified")
    if receipt.get("observer_artifact_post_ledger_match") is not True:
        failures.append("observer_artifact_ledger_mismatch")
    if receipt.get("observer_evidence_consistent") is not True:
        failures.append("observer_evidence_inconsistent")
    if str(receipt.get("observer_job_id") or "") != str(receipt.get("job_id") or ""):
        failures.append("observer_job_echo_mismatch")
    candidate_hash = str(receipt.get("candidate_hash") or "")
    activation_hash = str(receipt.get("candidate_activation_registry_hash") or "")
    activated_at = receipt.get("candidate_activated_at")
    if str(receipt.get("observer_candidate_hash") or "") != candidate_hash:
        failures.append("observer_candidate_echo_mismatch")
    if str(receipt.get("post_candidate_hash") or "") != candidate_hash:
        failures.append("active_candidate_drift")
    if (
        str(receipt.get("post_activation_registry_hash") or "") != activation_hash
        or receipt.get("post_activated_at") != activated_at
    ):
        failures.append("candidate_activation_drift")
    pre_ledger = dict(receipt.get("pre_ledger") or {})
    post_ledger = dict(receipt.get("post_ledger") or {})
    if (
        str(pre_ledger.get("candidate_hash") or "") != candidate_hash
        or str(post_ledger.get("candidate_hash") or "") != candidate_hash
    ):
        failures.append("observer_ledger_candidate_mismatch")
    if (
        str(pre_ledger.get("status") or "").upper() != "PASS"
        or str(post_ledger.get("status") or "").upper() != "PASS"
    ):
        failures.append("observer_ledger_audit_not_pass")
    if failures:
        return "FAILED", True, list(dict.fromkeys(failures))

    observer_ok = receipt.get("observer_ok") is True
    return_code = receipt.get("return_code")
    observer_status = str(receipt.get("observer_status") or "").upper()
    processed_count = receipt.get("processed_count")
    record_count = receipt.get("record_count")
    blockers = list(receipt.get("observer_blockers") or [])
    pre_count = pre_ledger.get("observation_chain_count")
    post_count = post_ledger.get("observation_chain_count")
    ledger_unchanged = pre_ledger == post_ledger

    if (
        observer_ok
        and return_code == 0
        and observer_status == "FORWARD_OBSERVATIONS_UPDATED"
        and isinstance(processed_count, int)
        and not isinstance(processed_count, bool)
        and processed_count > 0
        and record_count == processed_count
        and isinstance(pre_count, int)
        and isinstance(post_count, int)
        and post_count - pre_count == processed_count
        and not blockers
    ):
        return "PROCESSED_NEW_BARS", False, []
    if (
        observer_ok
        and return_code == 0
        and observer_status == "WAITING_FOR_NEW_COMPLETED_BAR"
        and processed_count == 0
        and record_count == 0
        and ledger_unchanged
        and not blockers
    ):
        return "NO_NEW_BAR", False, []
    if (
        observer_ok
        and return_code == 0
        and observer_status == "UP_TO_DATE_INCREMENTAL"
        and processed_count == 0
        and record_count == 0
        and ledger_unchanged
        and not blockers
    ):
        return "NO_WORK_ALREADY_ACCOUNTED", False, []
    if (
        not observer_ok
        and isinstance(return_code, int)
        and not isinstance(return_code, bool)
        and return_code != 0
        and observer_status in {
            "BLOCK",
            "CLOCK_ATTESTATION_BLOCKED",
            "INCREMENTAL_OBSERVATION_PLAN_BLOCKED",
            "FORWARD_VALIDATION_BLOCKED",
        }
        and processed_count == 0
        and record_count == 0
        and ledger_unchanged
    ):
        return "BLOCKED", False, []
    return "FAILED", True, ["observer_outcome_evidence_inconsistent"]


def build_forward_observer_job_receipt(
    scheduler_payload: dict[str, Any],
    *,
    sequence: int,
    previous_receipt_hash: str,
) -> dict[str, Any]:
    observer = dict(scheduler_payload.get("observer") or {})
    candidate_hash = str(scheduler_payload.get("candidate_hash") or "")
    due_dates_raw = observer.get("due_signal_dates")
    due_dates = [str(item) for item in due_dates_raw] if isinstance(due_dates_raw, list) else []
    receipt = {
        "schema_version": FORWARD_OBSERVER_JOB_RECEIPT_SCHEMA_VERSION,
        "sequence": int(sequence),
        "job_id": str(observer.get("job_id") or ""),
        "observer_job_id": str(observer.get("observer_job_id") or ""),
        "candidate_hash": candidate_hash,
        "candidate_activation_registry_hash": str(observer.get("candidate_activation_registry_hash") or ""),
        "candidate_activated_at": observer.get("candidate_activated_at"),
        "scheduled_decision_hash": str(observer.get("scheduled_decision_hash") or ""),
        "due_signal_dates": due_dates,
        "due_signal_dates_hash": str(observer.get("due_signal_dates_hash") or ""),
        "started_at_ms": observer.get("started_at_ms"),
        "finished_at_ms": observer.get("finished_at_ms"),
        "duration_ms": observer.get("duration_ms"),
        "process_state": str(observer.get("process_state") or ""),
        "return_code": observer.get("return_code"),
        "observer_ok": observer.get("ok"),
        "observer_status": str(observer.get("status") or ""),
        "observer_blockers": [str(item) for item in observer.get("blockers") or [] if str(item)],
        "observer_artifact_hash": str(observer.get("observer_artifact_hash") or ""),
        "observer_artifact_verified": observer.get("observer_artifact_verified"),
        "observer_artifact_post_ledger_match": observer.get("observer_artifact_post_ledger_match"),
        "observer_evidence_consistent": observer.get("observer_evidence_consistent"),
        "observer_candidate_hash": str(observer.get("observer_candidate_hash") or ""),
        "post_candidate_hash": str(observer.get("post_candidate_hash") or ""),
        "post_activation_registry_hash": str(observer.get("post_activation_registry_hash") or ""),
        "post_activated_at": observer.get("post_activated_at"),
        "incremental_plan_hash": str(observer.get("incremental_plan_hash") or ""),
        "work_summary_hash": str(observer.get("work_summary_hash") or ""),
        "records_hash": str(observer.get("records_hash") or ""),
        "processed_count": observer.get("processed_count"),
        "record_count": observer.get("record_count"),
        "processed_signal_dates": list(observer.get("processed_signal_dates") or []),
        "pre_ledger": dict(observer.get("pre_ledger") or {}),
        "post_ledger": dict(observer.get("post_ledger") or {}),
        "previous_receipt_hash": str(previous_receipt_hash or ""),
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    outcome, reconciliation_required, failure_reasons = _derive_observer_job_outcome(receipt)
    receipt["outcome"] = outcome
    receipt["reconciliation_required"] = reconciliation_required
    receipt["failure_reasons"] = failure_reasons
    receipt["receipt_hash"] = _canonical_hash(receipt)
    return receipt


def verify_forward_observer_job_receipt(
    receipt: Any,
    *,
    candidate_hash: str,
) -> dict[str, Any]:
    payload = dict(receipt) if isinstance(receipt, dict) else {}
    blockers: list[str] = []
    if payload.get("schema_version") != FORWARD_OBSERVER_JOB_RECEIPT_SCHEMA_VERSION:
        blockers.append("observer_job_receipt_schema_invalid")
    sequence = _strict_int(payload.get("sequence"), minimum=1)
    if sequence is None:
        blockers.append("observer_job_sequence_invalid")
        sequence = 0
    observer_job_id = str(payload.get("observer_job_id") or "")
    if not _sha256_hex(payload.get("job_id")) or (observer_job_id and not _sha256_hex(observer_job_id)):
        blockers.append("observer_job_identity_invalid")
    if not candidate_hash or str(payload.get("candidate_hash") or "") != candidate_hash:
        blockers.append("observer_job_candidate_mismatch")
    if not _sha256_hex(payload.get("candidate_activation_registry_hash")):
        blockers.append("observer_job_activation_hash_invalid")
    if _strict_int(payload.get("candidate_activated_at"), minimum=1) is None:
        blockers.append("observer_job_activated_at_invalid")
    if not _sha256_hex(payload.get("scheduled_decision_hash")):
        blockers.append("observer_job_decision_hash_invalid")
    due_dates = payload.get("due_signal_dates")
    if (
        not isinstance(due_dates, list)
        or not due_dates
        or any(not _valid_date(item) for item in due_dates)
        or due_dates != sorted(set(due_dates))
    ):
        blockers.append("observer_job_due_dates_invalid")
        due_dates = []
    if not _sha256_hex(payload.get("due_signal_dates_hash")) or str(
        payload.get("due_signal_dates_hash") or ""
    ) != _canonical_hash(due_dates):
        blockers.append("observer_job_due_dates_hash_invalid")
    started_at = _strict_int(payload.get("started_at_ms"), minimum=1)
    finished_at = _strict_int(payload.get("finished_at_ms"), minimum=1)
    duration = _strict_int(payload.get("duration_ms"), minimum=0)
    if started_at is None or finished_at is None or duration is None or finished_at < started_at or duration != finished_at - started_at:
        blockers.append("observer_job_timing_invalid")
    process_state = str(payload.get("process_state") or "")
    return_code = _strict_int(payload.get("return_code"))
    if process_state not in {"EXITED", "TIMED_OUT", "LAUNCH_FAILED"} or return_code is None:
        blockers.append("observer_job_process_state_invalid")
    if not isinstance(payload.get("observer_ok"), bool):
        blockers.append("observer_job_ok_invalid")
    if not str(payload.get("observer_status") or ""):
        blockers.append("observer_job_status_missing")
    if not isinstance(payload.get("observer_blockers"), list) or any(
        not isinstance(item, str) or not item for item in payload.get("observer_blockers") or []
    ):
        blockers.append("observer_job_blockers_invalid")
    artifact_hash = str(payload.get("observer_artifact_hash") or "")
    if payload.get("observer_artifact_verified") is True:
        if not _sha256_hex(artifact_hash):
            blockers.append("observer_job_artifact_hash_invalid")
    elif payload.get("observer_artifact_verified") is not False or (artifact_hash and not _sha256_hex(artifact_hash)):
        blockers.append("observer_job_artifact_verification_invalid")
    if not isinstance(payload.get("observer_artifact_post_ledger_match"), bool):
        blockers.append("observer_job_artifact_ledger_match_invalid")
    if not isinstance(payload.get("observer_evidence_consistent"), bool):
        blockers.append("observer_job_evidence_consistency_invalid")
    for field in (
        "incremental_plan_hash",
        "work_summary_hash",
        "records_hash",
    ):
        if not _sha256_hex(payload.get(field)):
            blockers.append(f"observer_job_{field}_invalid")
    post_activation_hash = str(payload.get("post_activation_registry_hash") or "")
    if post_activation_hash and not _sha256_hex(post_activation_hash):
        blockers.append("observer_job_post_activation_hash_invalid")
    if not isinstance(payload.get("observer_candidate_hash"), str) or not isinstance(payload.get("post_candidate_hash"), str):
        blockers.append("observer_job_candidate_echo_invalid")
    if _strict_int(payload.get("post_activated_at"), minimum=0) is None:
        blockers.append("observer_job_post_activated_at_invalid")
    processed_count = _strict_int(payload.get("processed_count"), minimum=0)
    record_count = _strict_int(payload.get("record_count"), minimum=0)
    signal_dates = payload.get("processed_signal_dates")
    if processed_count is None or record_count is None:
        blockers.append("observer_job_counts_invalid")
    if (
        not isinstance(signal_dates, list)
        or any(not _valid_date(item) for item in signal_dates)
        or len(signal_dates) != record_count
    ):
        blockers.append("observer_job_signal_dates_invalid")
    blockers.extend(_verify_job_ledger_snapshot(payload.get("pre_ledger")))
    blockers.extend(_verify_job_ledger_snapshot(payload.get("post_ledger")))
    previous_hash = str(payload.get("previous_receipt_hash") or "")
    if (sequence == 1 and previous_hash) or (sequence > 1 and not _sha256_hex(previous_hash)):
        blockers.append("observer_job_previous_receipt_hash_invalid")
    if (
        payload.get("observation_only") is not True
        or payload.get("simulation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("observer_job_execution_authority_invalid")
    expected_outcome, expected_reconciliation, expected_failures = _derive_observer_job_outcome(payload)
    if payload.get("outcome") != expected_outcome:
        blockers.append("observer_job_outcome_invalid")
    if payload.get("reconciliation_required") is not expected_reconciliation:
        blockers.append("observer_job_reconciliation_flag_invalid")
    if payload.get("failure_reasons") != expected_failures:
        blockers.append("observer_job_failure_reasons_invalid")
    expected_hash = str(payload.get("receipt_hash") or "")
    clean = dict(payload)
    clean.pop("receipt_hash", None)
    if not _sha256_hex(expected_hash) or expected_hash != _canonical_hash(clean):
        blockers.append("observer_job_receipt_hash_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt": payload if not blockers else {},
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_forward_scheduler_attempt_evidence(
    scheduler_payload: dict[str, Any],
    *,
    previous_receipt_hash: str,
) -> dict[str, Any]:
    """Seal the parent scheduler's complete, receipt-relevant attempt claims."""
    receipt = build_forward_observer_job_receipt(
        scheduler_payload,
        sequence=2 if previous_receipt_hash else 1,
        previous_receipt_hash=previous_receipt_hash,
    )
    attempt = {
        "schema_version": FORWARD_OBSERVER_ATTEMPT_EVIDENCE_SCHEMA_VERSION,
        **{field: receipt.get(field) for field in _OBSERVER_ATTEMPT_CLAIM_FIELDS},
    }
    attempt["attempt_hash"] = _canonical_hash(attempt)
    return attempt


def verify_forward_scheduler_attempt_evidence(
    attempt_evidence: Any,
    *,
    candidate_hash: str,
) -> dict[str, Any]:
    payload = dict(attempt_evidence) if isinstance(attempt_evidence, dict) else {}
    blockers: list[str] = []
    required = {"schema_version", "attempt_hash", *_OBSERVER_ATTEMPT_CLAIM_FIELDS}
    if set(payload) != required:
        blockers.append("scheduler_attempt_evidence_shape_invalid")
    if payload.get("schema_version") != FORWARD_OBSERVER_ATTEMPT_EVIDENCE_SCHEMA_VERSION:
        blockers.append("scheduler_attempt_evidence_schema_invalid")
    expected_hash = str(payload.get("attempt_hash") or "")
    clean = dict(payload)
    clean.pop("attempt_hash", None)
    if not _sha256_hex(expected_hash) or expected_hash != _canonical_hash(clean):
        blockers.append("scheduler_attempt_evidence_hash_invalid")

    previous_hash = str(payload.get("previous_receipt_hash") or "")
    receipt = {
        "schema_version": FORWARD_OBSERVER_JOB_RECEIPT_SCHEMA_VERSION,
        "sequence": 2 if previous_hash else 1,
        **{field: payload.get(field) for field in _OBSERVER_ATTEMPT_CLAIM_FIELDS},
    }
    receipt["receipt_hash"] = _canonical_hash(receipt)
    receipt_verification = verify_forward_observer_job_receipt(
        receipt,
        candidate_hash=candidate_hash,
    )
    if receipt_verification.get("status") != "PASS":
        blockers.extend(receipt_verification.get("blockers") or [])
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "evidence": payload if not blockers else {},
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_recent_observer_jobs(
    scheduler_status: Any,
    *,
    candidate_hash: str,
) -> dict[str, Any]:
    payload = dict(scheduler_status) if isinstance(scheduler_status, dict) else {}
    keys = {"recent_observer_jobs", "recent_observer_jobs_hash", "observer_job_chain_head_hash"}
    present = {key for key in keys if key in payload}
    if not present:
        return {"status": "NOT_CHECKED", "blockers": [], "jobs": [], "paper_authorized": False, "live_order_allowed": False}
    blockers: list[str] = []
    if present != keys:
        blockers.append("recent_observer_jobs_declaration_incomplete")
    raw_jobs = payload.get("recent_observer_jobs")
    if not isinstance(raw_jobs, list) or len(raw_jobs) > RECENT_OBSERVER_JOB_LIMIT:
        blockers.append("recent_observer_jobs_invalid")
        raw_jobs = []
    jobs = [dict(item) for item in raw_jobs if isinstance(item, dict)]
    if len(jobs) != len(raw_jobs):
        blockers.append("recent_observer_job_invalid")
    for job in jobs:
        verification = verify_forward_observer_job_receipt(job, candidate_hash=candidate_hash)
        blockers.extend(verification.get("blockers") or [])
    if len(jobs) == 1:
        if jobs[0].get("sequence") != 1 or str(jobs[0].get("previous_receipt_hash") or ""):
            blockers.append("recent_observer_job_genesis_invalid")
    elif len(jobs) == 2:
        older, newer = jobs
        older_sequence = _strict_int(older.get("sequence"), minimum=1)
        newer_sequence = _strict_int(newer.get("sequence"), minimum=1)
        if older_sequence is None or newer_sequence != older_sequence + 1:
            blockers.append("recent_observer_job_sequence_discontinuity")
        if str(newer.get("previous_receipt_hash") or "") != str(older.get("receipt_hash") or ""):
            blockers.append("recent_observer_job_chain_broken")
        newer_started_at = _strict_int(newer.get("started_at_ms"), minimum=1)
        older_finished_at = _strict_int(older.get("finished_at_ms"), minimum=1)
        if newer_started_at is None or older_finished_at is None or newer_started_at < older_finished_at:
            blockers.append("recent_observer_job_time_order_invalid")
        if (
            str(newer.get("candidate_activation_registry_hash") or "")
            != str(older.get("candidate_activation_registry_hash") or "")
            or newer.get("candidate_activated_at") != older.get("candidate_activated_at")
        ):
            blockers.append("recent_observer_job_activation_chain_mismatch")
        if dict(older.get("post_ledger") or {}) != dict(newer.get("pre_ledger") or {}):
            blockers.append("recent_observer_job_ledger_chain_mismatch")
    jobs_hash = str(payload.get("recent_observer_jobs_hash") or "")
    if not _sha256_hex(jobs_hash) or jobs_hash != _canonical_hash(jobs):
        blockers.append("recent_observer_jobs_hash_invalid")
    expected_head = str(jobs[-1].get("receipt_hash") or "") if jobs else ""
    if str(payload.get("observer_job_chain_head_hash") or "") != expected_head:
        blockers.append("observer_job_chain_head_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "jobs": jobs if not blockers else [],
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_forward_scheduler_status(payload: dict[str, Any]) -> dict[str, Any]:
    result = {
        **dict(payload),
        "schema_version": PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result.setdefault("recent_observer_jobs", [])
    result.setdefault("recent_observer_jobs_hash", _canonical_hash(result["recent_observer_jobs"]))
    result.setdefault("observer_job_chain_head_hash", "")
    result.pop("status_hash", None)
    alert_condition = {
        "status": str(result.get("status") or ""),
        "severity": str(result.get("severity") or "INFO").upper(),
        "candidate_hash": str(result.get("candidate_hash") or ""),
        "blockers": list(result.get("blockers") or []),
        "due_signal_dates": list((result.get("decision") or {}).get("due_signal_dates") or []),
        "overdue_signal_dates": list((result.get("decision") or {}).get("overdue_signal_dates") or []),
        "observer_status": str((result.get("observer") or {}).get("status") or ""),
    }
    result["alert_condition_hash"] = _canonical_hash(alert_condition)
    result["status_hash"] = _canonical_hash(result)
    return result


def _verify_scheduler_status_integrity(payload: Any) -> dict[str, Any]:
    status = dict(payload) if isinstance(payload, dict) else {}
    if not status:
        return {"status": "NOT_CHECKED", "blockers": [], "jobs": []}
    blockers: list[str] = []
    schema_version = str(status.get("schema_version") or "")
    if schema_version not in {
        PORTFOLIO_FORWARD_SCHEDULER_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION,
    }:
        blockers.append("previous_scheduler_status_schema_invalid")
    expected_hash = str(status.get("status_hash") or "")
    clean = dict(status)
    clean.pop("status_hash", None)
    if not _sha256_hex(expected_hash) or expected_hash != _canonical_hash(clean):
        blockers.append("previous_scheduler_status_hash_invalid")
    if (
        status.get("observation_only") is not True
        or status.get("paper_authorized") is not False
        or status.get("live_order_allowed") is not False
    ):
        blockers.append("previous_scheduler_status_authority_invalid")
    history = verify_recent_observer_jobs(
        status,
        candidate_hash=str(status.get("candidate_hash") or ""),
    )
    if (
        schema_version == PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION
        and history.get("status") == "NOT_CHECKED"
    ):
        blockers.append("previous_scheduler_observer_job_history_missing")
    if history.get("status") == "BLOCK":
        blockers.extend(history.get("blockers") or [])
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "jobs": list(history.get("jobs") or []),
    }


def load_forward_scheduler_job_chain_origin(
    status_path: Path | str,
    *,
    candidate_hash: str,
    candidate_activation_registry_hash: str,
    candidate_activated_at: int,
) -> dict[str, Any]:
    """Read only the verified chain head needed before starting an observer job."""
    if (
        not str(candidate_hash or "")
        or not _sha256_hex(candidate_activation_registry_hash)
        or _strict_int(candidate_activated_at, minimum=1) is None
    ):
        return {
            "status": "BLOCK",
            "blockers": ["scheduler_job_chain_current_identity_invalid"],
            "previous_receipt_hash": "",
            "origin": "BLOCKED",
        }
    try:
        payload = json.loads(Path(status_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("scheduler_status_not_an_object")
    except FileNotFoundError:
        return {
            "status": "PASS",
            "blockers": [],
            "previous_receipt_hash": "",
            "origin": "GENESIS",
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "BLOCK",
            "blockers": [f"scheduler_job_chain_origin_unreadable:{type(exc).__name__}"],
            "previous_receipt_hash": "",
            "origin": "BLOCKED",
        }

    integrity = _verify_scheduler_status_integrity(payload)
    if integrity.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "blockers": list(integrity.get("blockers") or ["scheduler_job_chain_origin_invalid"]),
            "previous_receipt_hash": "",
            "origin": "BLOCKED",
        }
    jobs = list(integrity.get("jobs") or [])
    if str(payload.get("candidate_hash") or "") != str(candidate_hash or "") or not jobs:
        return {
            "status": "PASS",
            "blockers": [],
            "previous_receipt_hash": "",
            "origin": "GENESIS",
        }
    latest = dict(jobs[-1])
    if (
        str(latest.get("candidate_activation_registry_hash") or "")
        != str(candidate_activation_registry_hash or "")
        or latest.get("candidate_activated_at") != candidate_activated_at
    ):
        return {
            "status": "PASS",
            "blockers": [],
            "previous_receipt_hash": "",
            "origin": "GENESIS",
        }
    if latest.get("reconciliation_required") is True:
        return {
            "status": "BLOCK",
            "blockers": ["scheduler_job_chain_reconciliation_required"],
            "previous_receipt_hash": "",
            "origin": "BLOCKED",
        }
    head = str(latest.get("receipt_hash") or "")
    if not _sha256_hex(head):
        return {
            "status": "BLOCK",
            "blockers": ["scheduler_job_chain_head_invalid"],
            "previous_receipt_hash": "",
            "origin": "BLOCKED",
        }
    return {
        "status": "PASS",
        "blockers": [],
        "previous_receipt_hash": head,
        "origin": "CONTINUE",
    }


def record_forward_scheduler_status(
    *,
    status_path: Path | str,
    alert_path: Path | str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    status_file = Path(status_path)
    alerts_file = Path(alert_path)
    previous: dict[str, Any] = {}
    previous_read_blocker = ""
    try:
        previous = json.loads(status_file.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
            previous_read_blocker = "previous_scheduler_status_not_object"
    except FileNotFoundError:
        previous = {}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        previous = {}
        previous_read_blocker = f"previous_scheduler_status_unreadable:{type(exc).__name__}"

    current = dict(payload)
    current_candidate = str(current.get("candidate_hash") or "")
    history_blockers: list[str] = [previous_read_blocker] if previous_read_blocker else []
    previous_integrity = _verify_scheduler_status_integrity(previous)
    if previous_integrity.get("status") == "BLOCK":
        history_blockers.extend(previous_integrity.get("blockers") or [])
    previous_jobs = list(previous_integrity.get("jobs") or [])
    recent_jobs: list[dict[str, Any]] = []
    same_candidate = bool(
        current_candidate
        and previous
        and str(previous.get("candidate_hash") or "") == current_candidate
        and previous_integrity.get("status") == "PASS"
    )
    if same_candidate:
        recent_jobs = previous_jobs
        if previous_jobs:
            current_activation_hash = str(current.get("candidate_activation_registry_hash") or "")
            current_activated_at = current.get("candidate_activated_at")
            latest_previous = previous_jobs[-1]
            if (
                not _sha256_hex(current_activation_hash)
                or _strict_int(current_activated_at, minimum=1) is None
            ):
                history_blockers.append("current_candidate_activation_identity_missing")
                recent_jobs = []
            elif (
                current_activation_hash != str(latest_previous.get("candidate_activation_registry_hash") or "")
                or current_activated_at != latest_previous.get("candidate_activated_at")
            ):
                recent_jobs = []

    observer_invoked = current.get("observer_invoked") is True
    if current.get("observer") and not observer_invoked:
        history_blockers.append("observer_present_without_invocation_marker")
    if observer_invoked:
        if history_blockers:
            history_blockers.append("observer_job_chain_origin_unverified")
        else:
            previous_hash = str(recent_jobs[-1].get("receipt_hash") or "") if recent_jobs else ""
            observer = dict(current.get("observer") or {})
            artifact_verified = observer.get("observer_artifact_verified") is True
            echoed_previous_hash = str(observer.get("scheduler_previous_receipt_hash") or "")
            if artifact_verified and echoed_previous_hash != previous_hash:
                history_blockers.append("observer_job_previous_receipt_echo_mismatch")
        if not history_blockers:
            sequence = int(recent_jobs[-1].get("sequence") or 0) + 1 if recent_jobs else 1
            receipt = build_forward_observer_job_receipt(
                current,
                sequence=sequence,
                previous_receipt_hash=previous_hash,
            )
            receipt_verification = verify_forward_observer_job_receipt(
                receipt,
                candidate_hash=current_candidate,
            )
            if receipt_verification.get("status") != "PASS":
                history_blockers.extend(receipt_verification.get("blockers") or ["observer_job_receipt_invalid"])
            else:
                recent_jobs = [*recent_jobs, receipt][-RECENT_OBSERVER_JOB_LIMIT:]
                current["reconciliation_required"] = receipt.get("reconciliation_required") is True
                if receipt.get("reconciliation_required") is True:
                    history_blockers.append("observer_job_reconciliation_required")

    current["recent_observer_jobs"] = recent_jobs
    current["recent_observer_jobs_hash"] = _canonical_hash(recent_jobs)
    current["observer_job_chain_head_hash"] = (
        str(recent_jobs[-1].get("receipt_hash") or "") if recent_jobs else ""
    )
    history_verification = verify_recent_observer_jobs(current, candidate_hash=current_candidate)
    if history_verification.get("status") == "BLOCK":
        history_blockers.extend(history_verification.get("blockers") or [])
    if history_blockers:
        current["ok"] = False
        current["severity"] = "ERROR"
        reported = current.get("blockers") if isinstance(current.get("blockers"), list) else []
        current["blockers"] = list(dict.fromkeys([
            *[str(item) for item in reported if str(item)],
            *[str(item) for item in history_blockers if str(item)],
        ]))
        current["reconciliation_required"] = True
    result = build_forward_scheduler_status(current)
    _atomic_write_json(status_file, result)

    severity = str(result.get("severity") or "INFO").upper()
    alert_identity = {
        "status": str(result.get("status") or ""),
        "severity": severity,
        "candidate_hash": str(result.get("candidate_hash") or ""),
        "condition_hash": str(result.get("alert_condition_hash") or ""),
    }
    previous_identity = {
        "status": str(previous.get("status") or ""),
        "severity": str(previous.get("severity") or "INFO").upper(),
        "candidate_hash": str(previous.get("candidate_hash") or ""),
        "condition_hash": str(previous.get("alert_condition_hash") or ""),
    }
    if severity in {"CRITICAL", "ERROR"} and alert_identity != previous_identity:
        alert = {
            "schema_version": PORTFOLIO_FORWARD_SCHEDULER_SCHEMA_VERSION,
            "event_type": "PORTFOLIO_FORWARD_SCHEDULER_ALERT",
            "generated_at": int(result.get("generated_at") or 0),
            **alert_identity,
            "blockers": list(result.get("blockers") or []),
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        alert["alert_hash"] = _canonical_hash(alert)
        alerts_file.parent.mkdir(parents=True, exist_ok=True)
        with alerts_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(alert, ensure_ascii=False, sort_keys=True) + "\n")
    return result


def load_forward_scheduler_status(
    status_path: Path | str,
    *,
    now_ms: int,
    stale_after_ms: int = SCHEDULER_STALE_AFTER_MS,
) -> dict[str, Any]:
    path = Path(status_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("scheduler_status_not_an_object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "NOT_INSTALLED_OR_NOT_RUN",
            "health": "MISSING",
            "blockers": [f"scheduler_status_unavailable:{type(exc).__name__}"],
            "status_path": str(path),
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    expected_hash = str(payload.get("status_hash") or "")
    hash_payload = dict(payload)
    hash_payload.pop("status_hash", None)
    blockers: list[str] = []
    schema_version = str(payload.get("schema_version") or "")
    if schema_version not in {
        PORTFOLIO_FORWARD_SCHEDULER_SCHEMA_VERSION,
        PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION,
    }:
        blockers.append("scheduler_status_schema_invalid")
    if not expected_hash or _canonical_hash(hash_payload) != expected_hash:
        blockers.append("scheduler_status_hash_mismatch")
    if (
        payload.get("observation_only") is not True
        or payload.get("paper_authorized") is not False
        or payload.get("live_order_allowed") is not False
    ):
        blockers.append("scheduler_status_has_execution_authority")
    history_verification = verify_recent_observer_jobs(
        payload,
        candidate_hash=str(payload.get("candidate_hash") or ""),
    )
    if (
        schema_version == PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION
        and history_verification.get("status") == "NOT_CHECKED"
    ):
        blockers.append("scheduler_observer_job_history_missing")
    if history_verification.get("status") == "BLOCK":
        blockers.extend(history_verification.get("blockers") or [])
    try:
        generated_at = int(payload.get("generated_at") or 0)
    except (TypeError, ValueError):
        generated_at = 0
        blockers.append("scheduler_generated_at_invalid")
    if generated_at < 0:
        generated_at = 0
        blockers.append("scheduler_generated_at_invalid")
    if generated_at > int(now_ms) + 5_000:
        blockers.append("scheduler_generated_at_from_future")
    age_ms = max(int(now_ms) - generated_at, 0) if generated_at else 0
    severity = str(payload.get("severity") or "INFO").upper()
    status_name = str(payload.get("status") or "").upper()
    allowed_success_statuses = {
        "UP_TO_DATE",
        "WAITING_FOR_BAR_FINALIZATION",
        "OBSERVER_COMPLETED",
        "OBSERVER_RETRY_REQUIRED",
    }
    dry_run_status = payload.get("dry_run") is True and status_name.startswith("DRY_RUN_")
    if payload.get("ok") is not True:
        blockers.append("scheduler_status_not_ok")
    if status_name not in allowed_success_statuses and not dry_run_status:
        blockers.append("scheduler_status_not_successful")
    if severity not in {"INFO", "DUE"}:
        blockers.append("scheduler_severity_not_successful")
    reported_raw = payload.get("blockers")
    if reported_raw is None:
        reported_blockers: list[str] = []
    elif isinstance(reported_raw, list):
        reported_blockers = [str(item) for item in reported_raw if str(item)]
    else:
        reported_blockers = []
        blockers.append("scheduler_blockers_invalid")
    if blockers:
        health = "BLOCK"
    elif reported_blockers:
        health = "BLOCK"
    elif severity in {"CRITICAL", "ERROR"}:
        health = "ALERT"
    elif payload.get("dry_run") is True:
        health = "DRY_RUN"
    elif payload.get("scheduled_invocation") is not True:
        health = "MANUAL_ONLY"
    elif not generated_at or age_ms > max(int(stale_after_ms), 1):
        health = "STALE"
    else:
        health = "PASS"
    return {
        **payload,
        "generated_at": generated_at,
        "health": health,
        "blockers": list(dict.fromkeys([*reported_blockers, *blockers])),
        "status_age_ms": age_ms if generated_at else None,
        "status_path": str(path),
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _optional_nonnegative_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _clean_date_list(values: Any, blockers: list[str], label: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        blockers.append(f"{label}_not_a_list")
        return []
    result: list[str] = []
    for value in values:
        clean = _valid_date(value)
        if not clean:
            blockers.append(f"{label}_invalid")
            continue
        result.append(clean)
    return list(dict.fromkeys(result))


def build_forward_observer_artifact_evidence(
    artifact: Any,
    *,
    candidate_hash: str,
) -> dict[str, Any]:
    """Verify and privately project the parent-sealed scheduler attempt."""
    payload = dict(artifact) if isinstance(artifact, dict) else {}
    raw_attempt = payload.get("scheduler_attempt_evidence")
    if raw_attempt is None:
        return {"status": "NOT_CHECKED", "blockers": [], "evidence": {}}
    verification = verify_forward_scheduler_attempt_evidence(
        raw_attempt,
        candidate_hash=candidate_hash,
    )
    if verification.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "blockers": list(verification.get("blockers") or ["scheduler_attempt_evidence_invalid"]),
            "evidence": {},
        }
    attempt = dict(verification.get("evidence") or {})
    blockers: list[str] = []
    if str(payload.get("candidate_hash") or "") != str(attempt.get("candidate_hash") or ""):
        blockers.append("scheduler_attempt_artifact_candidate_mismatch")
    if str(payload.get("scheduler_job_id") or "") != str(attempt.get("job_id") or ""):
        blockers.append("scheduler_attempt_artifact_job_mismatch")
    if str(payload.get("scheduler_previous_receipt_hash") or "") != str(
        attempt.get("previous_receipt_hash") or ""
    ):
        blockers.append("scheduler_attempt_artifact_previous_head_mismatch")
    if payload.get("ok") is not attempt.get("observer_ok"):
        blockers.append("scheduler_attempt_artifact_ok_mismatch")
    if str(payload.get("status") or "") != str(attempt.get("observer_status") or ""):
        blockers.append("scheduler_attempt_artifact_status_mismatch")
    plan_raw = payload.get("incremental_plan")
    work_raw = payload.get("work_summary")
    records_raw = payload.get("records")
    plan = dict(plan_raw) if isinstance(plan_raw, dict) else {}
    work = dict(work_raw) if isinstance(work_raw, dict) else {}
    records = [dict(item) for item in records_raw] if (
        isinstance(records_raw, list) and all(isinstance(item, dict) for item in records_raw)
    ) else []
    if not isinstance(plan_raw, dict):
        blockers.append("scheduler_attempt_artifact_plan_invalid")
    if not isinstance(work_raw, dict):
        blockers.append("scheduler_attempt_artifact_work_invalid")
    if not isinstance(records_raw, list) or len(records) != len(records_raw):
        blockers.append("scheduler_attempt_artifact_records_invalid")
    if _canonical_hash(plan) != str(attempt.get("incremental_plan_hash") or ""):
        blockers.append("scheduler_attempt_artifact_plan_hash_mismatch")
    if _canonical_hash(work) != str(attempt.get("work_summary_hash") or ""):
        blockers.append("scheduler_attempt_artifact_work_hash_mismatch")
    if _canonical_hash(records) != str(attempt.get("records_hash") or ""):
        blockers.append("scheduler_attempt_artifact_records_hash_mismatch")
    processed_signal_dates = [str(item.get("signal_date") or "") for item in records]
    if processed_signal_dates != list(attempt.get("processed_signal_dates") or []):
        blockers.append("scheduler_attempt_artifact_processed_dates_mismatch")
    if len(records) != attempt.get("record_count"):
        blockers.append("scheduler_attempt_artifact_record_count_mismatch")
    ledger = payload.get("ledger")
    forward_audit = (
        dict(ledger.get("forward_audit") or {})
        if isinstance(ledger, dict) and isinstance(ledger.get("forward_audit"), dict)
        else {}
    )
    if not forward_audit:
        blockers.append("scheduler_attempt_artifact_post_audit_missing")
    elif _canonical_hash(forward_audit) != str(
        (attempt.get("post_ledger") or {}).get("ledger_audit_hash") or ""
    ):
        blockers.append("scheduler_attempt_artifact_post_audit_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "evidence": (
            {field: attempt.get(field) for field in _OBSERVER_ATTEMPT_CLAIM_FIELDS}
            if not blockers
            else {}
        ),
    }


def _verify_latest_observer_job_artifact_binding(
    latest_receipt: dict[str, Any],
    artifact_evidence: Any,
) -> dict[str, Any]:
    result = dict(artifact_evidence) if isinstance(artifact_evidence, dict) else {}
    if result.get("status") == "NOT_CHECKED":
        return {"status": "NOT_CHECKED", "blockers": []}
    if result.get("status") != "PASS" or not isinstance(result.get("evidence"), dict):
        blockers = list(result.get("blockers") or []) if isinstance(result.get("blockers"), list) else []
        return {
            "status": "BLOCK",
            "blockers": list(dict.fromkeys([*blockers, "recent_observer_job_artifact_evidence_missing"])),
        }
    evidence = dict(result.get("evidence") or {})
    expected = {field: latest_receipt.get(field) for field in _OBSERVER_ATTEMPT_CLAIM_FIELDS}
    if evidence != expected:
        return {
            "status": "BLOCK",
            "blockers": ["recent_observer_job_artifact_evidence_mismatch"],
        }
    return {"status": "PASS", "blockers": []}


def build_forward_observation_dashboard(
    forward_status: dict[str, Any],
    *,
    now_ms: int,
    live_trading_hard_block: bool,
    observer_artifact_evidence: Any = None,
) -> dict[str, Any]:
    """Project verified forward evidence into a small, execution-free UI contract."""
    forward = dict(forward_status or {})
    scheduler = dict(forward.get("scheduler") or {})
    decision = dict(scheduler.get("decision") or {})
    observation = dict(forward.get("observation") or {})
    plan = dict(observation.get("incremental_plan") or {})
    work = dict(observation.get("work_summary") or {})
    ledger = dict(observation.get("ledger") or {})
    scheduler_observer = dict(scheduler.get("observer") or {})
    experiment_registry = dict(forward.get("experiment_registry") or {})
    readiness = dict(forward.get("readiness") or {})
    contract_blockers: list[str] = []
    latest_receipt_raw = observation.get("latest_observation_receipt")
    if latest_receipt_raw is None:
        latest_receipt_raw = {}
    elif not isinstance(latest_receipt_raw, dict):
        contract_blockers.append("latest_observation_receipt_invalid")
        latest_receipt_raw = {}
    latest_change_raw = observation.get("latest_observation_change")
    if latest_change_raw is None:
        latest_change_raw = {}
    elif not isinstance(latest_change_raw, dict):
        contract_blockers.append("latest_observation_change_invalid")
        latest_change_raw = {}
    latest_record: dict[str, Any] = {}
    latest_change: dict[str, Any] = {}

    if (
        forward.get("read_only") is not True
        or forward.get("paper_authorized") is not False
        or forward.get("live_order_allowed") is not False
    ):
        contract_blockers.append("forward_execution_authority_invalid")
    if live_trading_hard_block is not True:
        contract_blockers.append("live_trading_hard_block_missing")
    if scheduler and (
        scheduler.get("observation_only") is not True
        or scheduler.get("paper_authorized") is not False
        or scheduler.get("live_order_allowed") is not False
    ):
        contract_blockers.append("scheduler_execution_authority_invalid")
    if observation and (
        observation.get("observation_only") is not True
        or observation.get("simulation_only") is not True
        or observation.get("paper_authorized") is not False
        or observation.get("live_order_allowed") is not False
    ):
        contract_blockers.append("observation_execution_authority_invalid")
    if plan and (
        plan.get("observation_only") is not True
        or plan.get("simulation_only") is not True
        or plan.get("paper_authorized") is not False
        or plan.get("live_order_allowed") is not False
    ):
        contract_blockers.append("incremental_plan_execution_authority_invalid")
    if plan:
        expected_plan_hash = str(plan.get("plan_hash") or "")
        plan_hash_payload = dict(plan)
        plan_hash_payload.pop("plan_hash", None)
        if not expected_plan_hash or _canonical_hash(plan_hash_payload) != expected_plan_hash:
            contract_blockers.append("incremental_plan_hash_invalid")
        if str(plan.get("status") or "").upper() == "PASS":
            ledger_audit_hash = str(plan.get("ledger_audit_hash") or "")
            revision_evidence_hash = str(plan.get("data_revision_evidence_hash") or "")
            forward_audit = ledger.get("forward_audit")
            if not ledger_audit_hash:
                contract_blockers.append("incremental_plan_ledger_audit_hash_missing")
            if not revision_evidence_hash:
                contract_blockers.append("incremental_plan_revision_evidence_hash_missing")
            if not isinstance(forward_audit, dict):
                contract_blockers.append("forward_ledger_audit_evidence_missing")
            elif _canonical_hash(forward_audit) != ledger_audit_hash:
                contract_blockers.append("forward_ledger_audit_hash_mismatch")
            elif str(plan.get("ledger_audit_status") or "").upper() != str(forward_audit.get("status") or "").upper():
                contract_blockers.append("forward_ledger_audit_status_mismatch")

    candidate_hash = str(forward.get("candidate_hash") or "")
    identities = [
        str(value or "")
        for value in (
            scheduler.get("candidate_hash"),
            observation.get("candidate_hash"),
            plan.get("candidate_hash"),
            ledger.get("candidate_hash"),
        )
        if str(value or "")
    ]
    if candidate_hash and any(value != candidate_hash for value in identities):
        contract_blockers.append("forward_candidate_identity_mismatch")
    recent_jobs_verification = verify_recent_observer_jobs(
        scheduler,
        candidate_hash=candidate_hash,
    )
    if recent_jobs_verification.get("status") == "BLOCK":
        contract_blockers.extend(recent_jobs_verification.get("blockers") or [])
    verified_recent_jobs = list(recent_jobs_verification.get("jobs") or [])
    attempt_status = (
        str(observer_artifact_evidence.get("status") or "NOT_CHECKED")
        if isinstance(observer_artifact_evidence, dict)
        else "NOT_CHECKED"
    )
    if attempt_status == "BLOCK":
        contract_blockers.extend(
            list(observer_artifact_evidence.get("blockers") or [])
            if isinstance(observer_artifact_evidence, dict)
            else ["scheduler_attempt_evidence_invalid"]
        )
        verified_recent_jobs = []
    elif attempt_status == "PASS":
        if scheduler.get("schema_version") != PORTFOLIO_FORWARD_SCHEDULER_STATUS_SCHEMA_VERSION:
            contract_blockers.append("scheduler_attempt_requires_v2_status")
            verified_recent_jobs = []
        elif recent_jobs_verification.get("status") != "PASS" or not verified_recent_jobs:
            contract_blockers.append("scheduler_attempt_latest_receipt_missing")
            verified_recent_jobs = []
    elif attempt_status == "NOT_CHECKED":
        verified_recent_jobs = []
    else:
        contract_blockers.append("scheduler_attempt_evidence_status_invalid")
        verified_recent_jobs = []
    if attempt_status == "PASS" and verified_recent_jobs:
        binding = _verify_latest_observer_job_artifact_binding(
            verified_recent_jobs[-1],
            observer_artifact_evidence,
        )
        if binding.get("status") != "PASS":
            contract_blockers.extend(binding.get("blockers") or [])
            verified_recent_jobs = []

    due_dates = _clean_date_list(
        decision.get("due_signal_dates"), contract_blockers, "due_signal_dates"
    )
    overdue_dates = _clean_date_list(
        decision.get("overdue_signal_dates"), contract_blockers, "overdue_signal_dates"
    )
    latest_completed = _valid_date(observation.get("current_dataset_last"))
    last_accounted = _valid_date(ledger.get("last_signal_date"))
    frozen_last = _valid_date(observation.get("frozen_dataset_last"))
    latest_receipt_verification = verify_latest_forward_observation_receipt(
        latest_receipt_raw,
        candidate_hash=candidate_hash,
        expected_signal_date=last_accounted,
        ledger_audit=ledger.get("forward_audit"),
    )
    if latest_receipt_verification.get("status") == "BLOCK":
        contract_blockers.extend(latest_receipt_verification.get("blockers") or [])
    elif latest_receipt_verification.get("status") == "PASS":
        latest_record = dict(latest_receipt_verification.get("receipt") or {})
    latest_change_verification = verify_forward_observation_change(
        latest_change_raw,
        candidate_hash=candidate_hash,
        expected_current_signal_date=last_accounted,
        ledger_audit=ledger.get("forward_audit"),
    )
    if latest_change_verification.get("status") == "BLOCK":
        contract_blockers.extend(latest_change_verification.get("blockers") or [])
    elif latest_change_verification.get("status") == "PASS":
        latest_change = dict(latest_change_verification.get("change") or {})
    if str(latest_change.get("status") or "") == "VERIFIED":
        change_current = dict(latest_change.get("current") or {})
        if latest_receipt_verification.get("status") != "PASS":
            contract_blockers.append("latest_observation_change_receipt_missing")
        elif (
            str(change_current.get("signal_date") or "") != str(latest_record.get("signal_date") or "")
            or str(change_current.get("observation_hash") or "") != str(latest_record.get("observation_hash") or "")
        ):
            contract_blockers.append("latest_observation_change_receipt_mismatch")
    latest_observation = _valid_date(latest_record.get("signal_date")) or last_accounted
    for raw, clean, label in (
        (observation.get("current_dataset_last"), latest_completed, "current_dataset_last"),
        (ledger.get("last_signal_date"), last_accounted, "last_accounted_date"),
        (latest_record.get("signal_date"), _valid_date(latest_record.get("signal_date")), "latest_record_date"),
    ):
        if raw and not clean:
            contract_blockers.append(f"{label}_invalid")
    try:
        as_of_date = datetime.fromtimestamp(int(now_ms) / 1000.0, tz=timezone.utc).date()
    except (OSError, OverflowError, TypeError, ValueError):
        as_of_date = None
        contract_blockers.append("dashboard_as_of_invalid")
    if as_of_date and latest_completed and date.fromisoformat(latest_completed) > as_of_date:
        contract_blockers.append("current_dataset_last_from_future")
    if latest_completed and last_accounted and last_accounted > latest_completed:
        contract_blockers.append("last_accounted_after_current_dataset")
    if latest_completed and latest_observation and latest_observation > latest_completed:
        contract_blockers.append("latest_observation_after_current_dataset")
    if frozen_last and latest_completed and frozen_last > latest_completed:
        contract_blockers.append("current_dataset_precedes_frozen_baseline")

    count_fields = {
        "eligible_count": _optional_nonnegative_int(work.get("eligible_count")),
        "processing_count": _optional_nonnegative_int(work.get("processing_count")),
        "processed_count": _optional_nonnegative_int(work.get("processed_count")),
        "skipped_recorded_count": _optional_nonnegative_int(work.get("skipped_recorded_count")),
        "skipped_classified_count": _optional_nonnegative_int(work.get("skipped_classified_count")),
        "deferred_unrecorded_count": _optional_nonnegative_int(work.get("deferred_unrecorded_count")),
    }
    for key, value in count_fields.items():
        if key in work and value is None:
            contract_blockers.append(f"work_summary_{key}_invalid")
    skipped_count = None
    if count_fields["skipped_recorded_count"] is not None or count_fields["skipped_classified_count"] is not None:
        skipped_count = int(count_fields["skipped_recorded_count"] or 0) + int(
            count_fields["skipped_classified_count"] or 0
        )

    forward_blockers = [str(item) for item in forward.get("blockers") or [] if str(item)]
    scheduler_blockers = [str(item) for item in scheduler.get("blockers") or [] if str(item)]
    decision_blockers = [str(item) for item in decision.get("blockers") or [] if str(item)]
    plan_blockers = [str(item) for item in plan.get("blockers") or [] if str(item)]
    blockers = list(dict.fromkeys([
        *contract_blockers,
        *forward_blockers,
        *scheduler_blockers,
        *decision_blockers,
        *plan_blockers,
    ]))

    forward_state = str(forward.get("status") or "UNKNOWN").upper()
    scheduler_health = str(scheduler.get("health") or "MISSING").upper()
    scheduler_state = str(decision.get("status") or scheduler.get("status") or "UNKNOWN").upper()
    observer_state = str(observation.get("status") or scheduler_observer.get("status") or "NOT_RUN").upper()
    schedule_action = str(decision.get("action") or "NONE").upper()
    plan_state = str(plan.get("status") or "").upper()
    experiment_state = str(experiment_registry.get("status") or "UNKNOWN").upper()
    requires_complete_evidence = forward_state not in {
        "BLOCK",
        "UNKNOWN",
        "WAITING_FOR_FIRST_OBSERVATION",
        "WAITING_FOR_NEW_COMPLETED_BAR",
    }
    if candidate_hash and scheduler_health != "MISSING" and str(scheduler.get("candidate_hash") or "") != candidate_hash:
        contract_blockers.append("scheduler_candidate_identity_missing_or_mismatched")
    if requires_complete_evidence:
        if not observation:
            contract_blockers.append("forward_observation_evidence_missing")
        if not plan:
            contract_blockers.append("incremental_plan_evidence_missing")
        if not ledger:
            contract_blockers.append("forward_ledger_evidence_missing")
        if not readiness:
            contract_blockers.append("forward_readiness_evidence_missing")
        else:
            readiness_hash = str(readiness.get("readiness_hash") or "")
            readiness_payload = dict(readiness)
            readiness_payload.pop("readiness_hash", None)
            if not readiness_hash or _canonical_hash(readiness_payload) != readiness_hash:
                contract_blockers.append("forward_readiness_hash_invalid")
            if str(readiness.get("candidate_hash") or "") != candidate_hash:
                contract_blockers.append("forward_readiness_candidate_identity_mismatch")
            if (
                readiness.get("research_only") is not True
                or readiness.get("automatic_paper_activation_allowed") is not False
                or readiness.get("paper_authorized") is not False
                or readiness.get("live_order_allowed") is not False
            ):
                contract_blockers.append("forward_readiness_execution_authority_invalid")
            readiness_audit = readiness.get("ledger_audit")
            if not isinstance(readiness_audit, dict):
                contract_blockers.append("forward_readiness_ledger_audit_missing")
            elif str(plan.get("ledger_audit_hash") or "") != _canonical_hash(readiness_audit):
                contract_blockers.append("forward_readiness_ledger_audit_hash_mismatch")
    allowed_scheduler_health = {"PASS", "BLOCK", "ALERT", "DRY_RUN", "MANUAL_ONLY", "STALE", "MISSING"}
    if scheduler_health not in allowed_scheduler_health:
        contract_blockers.append("scheduler_health_invalid")
        blockers = list(dict.fromkeys([*contract_blockers, *blockers]))
    observer_failed = observer_state in {
        "OBSERVER_FAILED",
        "OBSERVER_TIMEOUT",
        "FORWARD_VALIDATION_BLOCKED",
        "INCREMENTAL_OBSERVATION_PLAN_BLOCKED",
    }
    if (
        contract_blockers
        or scheduler_health in {"BLOCK", "ALERT"}
        or forward_state == "BLOCK"
        or plan_state == "BLOCK"
        or experiment_state == "BLOCK"
        or scheduler_state in {"FORWARD_LEDGER_BLOCKED", "SCHEDULER_DECISION_BLOCKED"}
        or (bool([*forward_blockers, *scheduler_blockers, *decision_blockers, *plan_blockers]) and scheduler_health != "MISSING")
    ):
        status = "BLOCK"
    elif scheduler_health == "MISSING":
        status = "PAUSED" if candidate_hash else "UNKNOWN"
    elif scheduler_health in {"STALE", "MANUAL_ONLY", "DRY_RUN"} or observer_failed:
        status = "PAUSED"
    elif due_dates or overdue_dates or schedule_action == "RUN_OBSERVER":
        status = "DUE"
    elif forward_state in {"WAITING_FOR_FIRST_OBSERVATION", "WAITING_FOR_NEW_COMPLETED_BAR"} or scheduler_state == "WAITING_FOR_BAR_FINALIZATION":
        status = "WAITING"
    elif not candidate_hash:
        status = "UNKNOWN"
    else:
        status = "UP_TO_DATE"

    next_window = dict(decision.get("next_capture_window") or {})
    next_check_at = _optional_nonnegative_int(decision.get("next_check_at_ms"))
    heartbeat_at = _optional_nonnegative_int(scheduler.get("generated_at"))
    heartbeat_age = (
        max(int(now_ms) - heartbeat_at, 0)
        if heartbeat_at is not None and heartbeat_at > 0 and int(now_ms) > 0
        else None
    )
    observation_generated_at = _optional_nonnegative_int(observation.get("generated_at"))
    if scheduler.get("generated_at") is not None and heartbeat_at is None:
        contract_blockers.append("scheduler_heartbeat_invalid")
    if heartbeat_at is not None and heartbeat_at > int(now_ms) + 5_000:
        contract_blockers.append("scheduler_heartbeat_from_future")
    if observation_generated_at is not None and observation_generated_at > int(now_ms) + 5_000:
        contract_blockers.append("observer_timestamp_from_future")
    if observation.get("generated_at") is not None and observation_generated_at is None:
        contract_blockers.append("observer_timestamp_invalid")

    if next_window:
        window_signal_date = _valid_date(next_window.get("signal_date"))
        window_next_session = _valid_date(next_window.get("next_session_date"))
        window_close = _optional_nonnegative_int(next_window.get("session_close_ms"))
        window_not_before = _optional_nonnegative_int(next_window.get("capture_not_before_ms"))
        window_deadline = _optional_nonnegative_int(next_window.get("capture_deadline_ms"))
        if not window_signal_date or not window_next_session:
            contract_blockers.append("next_capture_window_date_invalid")
        if (
            window_close is None
            or window_not_before is None
            or window_deadline is None
            or not (window_close < window_not_before < window_deadline)
        ):
            contract_blockers.append("next_capture_window_timing_invalid")
        if window_signal_date and window_next_session and window_signal_date >= window_next_session:
            contract_blockers.append("next_capture_window_session_order_invalid")
        if not decision.get("calendar_contract_hash") or not decision.get("calendar_schedule_hash"):
            contract_blockers.append("next_capture_window_calendar_identity_missing")
    elif scheduler_health == "PASS" and schedule_action == "NONE":
        contract_blockers.append("next_capture_window_missing")
    if "next_check_at_ms" in decision and next_check_at is None:
        contract_blockers.append("next_check_at_invalid")
    if (
        scheduler_health == "PASS"
        and schedule_action == "NONE"
        and (next_check_at is None or next_check_at <= int(now_ms))
    ):
        contract_blockers.append("next_check_at_already_elapsed")
    blockers = list(dict.fromkeys([
        *contract_blockers,
        *forward_blockers,
        *scheduler_blockers,
        *decision_blockers,
        *plan_blockers,
    ]))
    if contract_blockers:
        status = "BLOCK"
    if status == "BLOCK":
        next_action = "先处理阻断原因；不得回填或重算旧观察"
    elif status == "PAUSED":
        next_action = "恢复只读调度或观察任务后再继续；不得补写旧样本"
    elif status == "DUE":
        next_action = "等待只读调度器处理已到窗口；不把调度触发当成新样本"
    elif status == "WAITING":
        next_action = "等待下一根完成 K 线或确认延迟结束"
    elif status == "UP_TO_DATE":
        next_action = "继续自然前向观察；等待下一交易日"
    else:
        next_action = "等待候选、调度和首个可信观察证据"

    skipped_known = (
        plan_state == "PASS"
        and str(plan.get("ledger_audit_status") or "").upper() == "PASS"
        and skipped_count is not None
    )
    pending_state = (
        "OVERDUE" if overdue_dates
        else "DUE" if due_dates or schedule_action == "RUN_OBSERVER"
        else "FINALIZING" if scheduler_state == "WAITING_FOR_BAR_FINALIZATION"
        else "NONE" if scheduler_health in {"PASS", "MANUAL_ONLY"}
        else "UNKNOWN"
    )
    pending_dates = list(dict.fromkeys([*overdue_dates, *due_dates]))
    next_check_mode = (
        "NOW" if schedule_action == "RUN_OBSERVER"
        else "AT" if next_check_at is not None and next_check_at > 0
        else "UNKNOWN"
    )
    target_symbols_raw = latest_record.get("target_symbols")
    if target_symbols_raw is None:
        target_symbols: list[str] = []
    elif isinstance(target_symbols_raw, list):
        target_symbols = [str(item) for item in target_symbols_raw if str(item)]
    else:
        target_symbols = []
        contract_blockers.append("latest_record_target_symbols_invalid")
        blockers = list(dict.fromkeys([*contract_blockers, *blockers]))
        status = "BLOCK"
        next_action = "先处理阻断原因；不得回填或重算旧观察"

    change_previous = dict(latest_change.get("previous") or {})
    change_current = dict(latest_change.get("current") or {})
    change_target_set = dict(latest_change.get("target_set") or {})
    change_risk = dict(latest_change.get("risk_gate_status") or {})
    change_status = (
        str(latest_change.get("status") or "")
        if latest_change_verification.get("status") == "PASS"
        else str(latest_change_verification.get("status") or "NOT_CHECKED")
    )

    permissions = {
        "read_only": True,
        "observation_only": True,
        "simulation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_hard_block": live_trading_hard_block is True,
    }
    latest_verified_job = verified_recent_jobs[-1] if verified_recent_jobs else {}
    return {
        "schema_version": PORTFOLIO_FORWARD_DASHBOARD_SCHEMA_VERSION,
        "status": status,
        "as_of_ms": int(now_ms) if int(now_ms) > 0 else 0,
        "candidate_hash": candidate_hash,
        "service": {
            "status": scheduler_health,
            "last_heartbeat_at_ms": heartbeat_at,
            "heartbeat_age_ms": heartbeat_age,
        },
        "observer": {
            "status": observer_state,
            "last_run_at_ms": _optional_nonnegative_int(observation.get("generated_at")),
            "last_job_status": str(
                latest_verified_job.get("observer_status")
                or scheduler_observer.get("status")
                or ""
            ),
            "last_job_duration_ms": _optional_nonnegative_int(
                latest_verified_job.get("duration_ms")
                if latest_verified_job
                else scheduler_observer.get("duration_ms")
            ),
            "mode": str(work.get("mode") or plan.get("mode") or "INCREMENTAL"),
        },
        "data": {
            "frozen_last_date": frozen_last,
            "latest_completed_date": latest_completed,
            "last_accounted_date": last_accounted,
            "latest_observation_date": latest_observation,
            **count_fields,
            "skipped_count": skipped_count,
        },
        "latest_completed_bar": {
            "known": bool(latest_completed),
            "bar": "1D",
            "date": latest_completed,
            "basis": "aligned_current_dataset_last" if latest_completed else "unknown",
        },
        "pending": {
            "known": pending_state != "UNKNOWN",
            "state": pending_state,
            "dates": pending_dates,
            "count": len(pending_dates) if pending_state != "UNKNOWN" else None,
        },
        "skipped": {
            "known": skipped_known,
            "total": skipped_count if skipped_known else None,
            "recorded": count_fields["skipped_recorded_count"] if skipped_known else None,
            "classified": count_fields["skipped_classified_count"] if skipped_known else None,
            "basis": "ledger_audit_pass" if skipped_known else "unknown",
        },
        "next_check": {
            "mode": next_check_mode,
            "at_ms": next_check_at if next_check_mode == "AT" else None,
        },
        "pause": {
            "paused": status in {"PAUSED", "BLOCK"},
            "reason": next_action if status in {"PAUSED", "BLOCK"} else "",
            "blockers": blockers,
        },
        "schedule": {
            "status": scheduler_state,
            "action": schedule_action,
            "due_signal_dates": due_dates,
            "overdue_signal_dates": overdue_dates,
            "next_check_at_ms": next_check_at,
            "next_capture_window": next_window,
        },
        "latest_observation": {
            "known": latest_receipt_verification.get("status") == "PASS",
            "source": "VERIFIED_LEDGER_RECEIPT" if latest_receipt_verification.get("status") == "PASS" else "",
            "signal_date": latest_observation,
            "target_symbols": target_symbols,
            "target_allocation_pct": latest_record.get("target_allocation_pct"),
            "reason": str(latest_record.get("reason") or ""),
            "risk_status": str(latest_record.get("risk_gate_status") or ledger.get("latest_risk_status") or ""),
            "record_status": str(latest_record.get("record_status") or ""),
            "observed_at": _optional_nonnegative_int(latest_record.get("observed_at")),
            "decision_hash": str(latest_record.get("decision_hash") or ""),
            "observation_hash": str(latest_record.get("observation_hash") or ""),
            "receipt_hash": str(latest_record.get("receipt_hash") or ""),
        },
        "latest_observation_change": {
            "known": change_status == "VERIFIED",
            "status": change_status or "NOT_CHECKED",
            "source": "VERIFIED_LEDGER_CHANGE" if change_status in {"VERIFIED", "NOT_ENOUGH_OBSERVATIONS"} else "",
            "candidate_hash": str(latest_change.get("candidate_hash") or candidate_hash),
            "previous_signal_date": _valid_date(change_previous.get("signal_date")),
            "current_signal_date": _valid_date(change_current.get("signal_date")),
            "previous_observation_hash": str(change_previous.get("observation_hash") or ""),
            "current_observation_hash": str(change_current.get("observation_hash") or ""),
            "target_set_changed": change_target_set.get("changed"),
            "added_symbols": list(change_target_set.get("added") or []),
            "removed_symbols": list(change_target_set.get("removed") or []),
            "retained_symbols": list(change_target_set.get("retained") or []),
            "risk_status_before": str(change_risk.get("before") or ""),
            "risk_status_after": str(change_risk.get("after") or ""),
            "risk_changed": change_risk.get("changed"),
            "change_hash": str(latest_change.get("change_hash") or ""),
            "descriptive_only": True,
            "direction_signal_allowed": False,
            "performance_claim_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "recent_observer_jobs": [
            {
                "known": True,
                "source": "VERIFIED_SCHEDULER_JOB_RECEIPT",
                "job_id": str(job.get("job_id") or ""),
                "candidate_hash": str(job.get("candidate_hash") or ""),
                "outcome": str(job.get("outcome") or ""),
                "started_at_ms": _optional_nonnegative_int(job.get("started_at_ms")),
                "finished_at_ms": _optional_nonnegative_int(job.get("finished_at_ms")),
                "duration_ms": _optional_nonnegative_int(job.get("duration_ms")),
                "observer_status": str(job.get("observer_status") or ""),
                "processed_count": _optional_nonnegative_int(job.get("processed_count")),
                "pre_last_signal_date": _valid_date((job.get("pre_ledger") or {}).get("last_signal_date")),
                "post_last_signal_date": _valid_date((job.get("post_ledger") or {}).get("last_signal_date")),
                "reconciliation_required": job.get("reconciliation_required") is True,
                "receipt_hash": str(job.get("receipt_hash") or ""),
                "descriptive_only": True,
                "direction_signal_allowed": False,
                "performance_claim_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            for job in verified_recent_jobs
        ],
        "progress": dict(readiness.get("progress") or {}),
        "experiment_status": experiment_state,
        "blockers": blockers,
        "next_action": next_action,
        "permissions": permissions,
        **permissions,
    }


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class ForwardSchedulerLock:
    def __init__(
        self,
        path: Path | str,
        *,
        now_ms: Callable[[], int],
        pid_exists: Callable[[int], bool] = _pid_exists,
    ) -> None:
        self.path = Path(path)
        self.now_ms = now_ms
        self.pid_exists = pid_exists
        self.token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            payload = {
                "pid": os.getpid(),
                "token": self.token,
                "created_at": int(self.now_ms()),
            }
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(descriptor, json.dumps(payload, sort_keys=True).encode("utf-8"))
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                self.acquired = True
                return {"ok": True, "status": "ACQUIRED", "lock": payload}
            except FileExistsError:
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, ValueError, json.JSONDecodeError):
                    return {"ok": False, "status": "LOCK_OWNER_UNVERIFIED", "lock": {}}
                existing_pid = int(existing.get("pid") or 0)
                if self.pid_exists(existing_pid):
                    return {"ok": False, "status": "BUSY", "lock": existing}
                stale = self.path.with_name(f"{self.path.name}.stale.{int(self.now_ms())}")
                try:
                    self.path.replace(stale)
                except OSError:
                    return {"ok": False, "status": "LOCK_RECOVERY_FAILED", "lock": existing}
        return {"ok": False, "status": "LOCK_ACQUIRE_FAILED", "lock": {}}

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            existing = json.loads(self.path.read_text(encoding="utf-8"))
            if str(existing.get("token") or "") == self.token:
                self.path.unlink(missing_ok=True)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        self.acquired = False
