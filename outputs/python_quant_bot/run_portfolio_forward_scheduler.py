from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from exchange_terminal.services.portfolio_forward import load_active_portfolio_candidate
from exchange_terminal.services.portfolio_forward_scheduler import (
    DEFAULT_SCHEDULER_ALERT_FILE,
    DEFAULT_SCHEDULER_LOCK_FILE,
    DEFAULT_SCHEDULER_STATUS_FILE,
    ForwardSchedulerLock,
    build_forward_scheduler_decision,
    build_forward_scheduler_attempt_evidence,
    build_forward_scheduler_status,
    load_forward_scheduler_job_chain_origin,
    load_forward_scheduler_status,
    record_forward_scheduler_status,
    verify_forward_scheduler_attempt_evidence,
)
from exchange_terminal.services.portfolio_shadow import (
    PortfolioShadowLedger,
    seal_forward_status_artifact,
    verify_forward_status_artifact,
)
from exchange_terminal.services.trusted_clock import attest_utc_clock


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("HAKIMI_RUNTIME_DIR") or PROJECT_ROOT / "runtime").resolve()
REPORT_DIR = RUNTIME_DIR / "reports"


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_hex(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def valid_date(value: Any) -> bool:
    try:
        return date.fromisoformat(str(value or "")).isoformat() == str(value or "")
    except ValueError:
        return False


def compact_ledger_audit(audit: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": str(audit.get("status") or "").upper(),
        "candidate_hash": str(audit.get("candidate_hash") or ""),
        "ledger_audit_hash": canonical_hash(audit),
        "observation_chain_hash": str(audit.get("observation_chain_hash") or ""),
        "observation_chain_count": int(audit.get("observation_chain_count") or 0),
        "last_signal_date": str(audit.get("last_signal_date") or ""),
        "latest_observation_hash": str(audit.get("latest_observation_hash") or ""),
    }
    result["snapshot_hash"] = canonical_hash(result)
    return result


def parse_json_output(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
    return {}


def emit(payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(rendered)
    except UnicodeEncodeError:
        print(json.dumps(payload, ensure_ascii=True, indent=2))


def write_parent_sealed_attempt_artifact(
    *,
    candidate_hash: str,
    observer: dict[str, Any],
    child_artifact: dict[str, Any],
    child_artifact_verified: bool,
    post_audit: dict[str, Any],
    attempt_evidence: dict[str, Any],
) -> dict[str, Any]:
    allowed_child_fields = {
        "clock_attestation",
        "frozen_dataset_last",
        "current_dataset_last",
        "latest_observation_receipt",
        "latest_observation_change",
        "incremental_plan",
        "work_summary",
        "records",
        "readiness",
        "ledger",
    }
    payload = (
        {key: child_artifact[key] for key in allowed_child_fields if key in child_artifact}
        if child_artifact_verified
        else {}
    )
    plan = dict(payload.get("incremental_plan") or {}) if isinstance(payload.get("incremental_plan"), dict) else {}
    work = dict(payload.get("work_summary") or {}) if isinstance(payload.get("work_summary"), dict) else {}
    records = (
        [dict(item) for item in payload.get("records") or [] if isinstance(item, dict)]
        if isinstance(payload.get("records"), list)
        else []
    )
    ledger = dict(payload.get("ledger") or {}) if isinstance(payload.get("ledger"), dict) else {}
    post_ledger = dict(observer.get("post_ledger") or {})
    ledger.update({
        "candidate_hash": candidate_hash,
        "last_signal_date": str(post_ledger.get("last_signal_date") or ""),
        "latest_observation_hash": str(post_ledger.get("latest_observation_hash") or ""),
        "forward_audit": dict(post_audit),
    })
    payload.update({
        "ok": observer.get("ok") is True,
        "status": str(observer.get("status") or "OBSERVER_FAILED"),
        "generated_at": int(observer.get("finished_at_ms") or 0),
        "candidate_hash": candidate_hash,
        "scheduler_job_id": str(observer.get("job_id") or ""),
        "scheduler_previous_receipt_hash": str(attempt_evidence.get("previous_receipt_hash") or ""),
        "incremental_plan": plan,
        "work_summary": work,
        "records": records,
        "ledger": ledger,
        "blockers": [str(item) for item in observer.get("blockers") or [] if str(item)],
        "scheduler_attempt_evidence": dict(attempt_evidence),
    })
    sealed = seal_forward_status_artifact(payload)
    path = REPORT_DIR / f"portfolio_forward_status_{candidate_hash[:12]}.json"
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(sealed, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the research-only portfolio forward observer when its official window is due.")
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runner-timeout", type=int, default=600)
    parser.add_argument("--clock-timeout", type=float, default=2.5)
    args = parser.parse_args()

    status_path = REPORT_DIR / DEFAULT_SCHEDULER_STATUS_FILE
    alert_path = REPORT_DIR / DEFAULT_SCHEDULER_ALERT_FILE
    if args.dry_run:
        active = load_active_portfolio_candidate(REPORT_DIR)
        recorded = load_forward_scheduler_status(status_path, now_ms=now_ms())
        preview_ok = active.get("status") == "PASS" and recorded.get("health") == "PASS"
        payload = build_forward_scheduler_status({
            "ok": preview_ok,
            "status": f"DRY_RUN_{recorded.get('status') or 'NOT_RUN'}",
            "severity": "INFO" if preview_ok else "ERROR",
            "generated_at": now_ms(),
            "candidate_hash": str((active.get("candidate") or {}).get("candidate_hash") or ""),
            "active_candidate_status": str(active.get("status") or "UNKNOWN"),
            "active_candidate_blockers": list(active.get("blockers") or []),
            "recorded_scheduler": recorded,
            "scheduled_invocation": False,
            "dry_run": True,
            "persistence": "READ_ONLY_NO_FILES_OR_DATABASES_CREATED",
        })
        emit(payload)
        return 0 if preview_ok else 5

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lock = ForwardSchedulerLock(
        RUNTIME_DIR / DEFAULT_SCHEDULER_LOCK_FILE,
        now_ms=now_ms,
    )
    lock_result = lock.acquire()
    if not lock_result.get("ok"):
        payload = {
            "ok": lock_result.get("status") == "BUSY",
            "status": f"SCHEDULER_{lock_result.get('status') or 'LOCK_BLOCK'}",
            "severity": "INFO" if lock_result.get("status") == "BUSY" else "ERROR",
            "generated_at": now_ms(),
            "lock": lock_result,
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        emit(payload)
        return 0 if lock_result.get("status") == "BUSY" else 2

    try:
        active = load_active_portfolio_candidate(REPORT_DIR)
        if active.get("status") != "PASS":
            payload = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": False,
                    "status": "ACTIVE_CANDIDATE_BLOCKED",
                    "severity": "ERROR",
                    "generated_at": now_ms(),
                    "blockers": list(active.get("blockers") or []),
                    "active_candidate": dict(active.get("registry") or {}),
                    "scheduled_invocation": bool(args.scheduled),
                },
            )
            emit(payload)
            return 3

        candidate = dict(active.get("candidate") or {})
        candidate_hash = str(candidate.get("candidate_hash") or "")
        activation = dict(active.get("activation_verification") or {})
        candidate_activation_registry_hash = str(activation.get("registry_hash") or "")
        candidate_activated_at = int(activation.get("activated_at") or 0)
        clock = attest_utc_clock(timeout_seconds=max(float(args.clock_timeout), 0.1))
        if clock.get("status") != "PASS":
            payload = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    "ok": False,
                    "status": "CLOCK_ATTESTATION_BLOCKED",
                    "severity": "ERROR",
                    "generated_at": now_ms(),
                    "candidate_hash": candidate_hash,
                    "candidate_activation_registry_hash": candidate_activation_registry_hash,
                    "candidate_activated_at": candidate_activated_at,
                    "blockers": list(clock.get("blockers") or []),
                    "clock_attestation": clock,
                    "scheduled_invocation": bool(args.scheduled),
                },
            )
            emit(payload)
            return 4

        ledger = PortfolioShadowLedger(RUNTIME_DIR / "portfolio_shadow.sqlite")

        def scheduler_decision() -> dict[str, Any]:
            return build_forward_scheduler_decision(
                candidate=candidate,
                attested_now_ms=int(clock.get("attested_now_ms") or 0),
                observed_dates=ledger.observation_dates(candidate_hash),
                capture_event_dates=ledger.capture_event_dates(candidate_hash),
                ledger_audit=ledger.audit(candidate_hash),
            )

        decision = scheduler_decision()
        base = {
            "generated_at": now_ms(),
            "candidate_hash": candidate_hash,
            "candidate_activation_registry_hash": candidate_activation_registry_hash,
            "candidate_activated_at": candidate_activated_at,
            "candidate_file": str(Path(active.get("candidate_path") or "").name),
            "scheduled_invocation": bool(args.scheduled),
            "clock_attestation": clock,
            "decision": decision,
            "blockers": list(decision.get("blockers") or []),
        }
        if decision.get("action") != "RUN_OBSERVER":
            payload = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    **base,
                    "ok": decision.get("status") not in {"FORWARD_LEDGER_BLOCKED", "SCHEDULER_DECISION_BLOCKED"},
                    "status": str(decision.get("status") or "UNKNOWN"),
                    "severity": str(decision.get("severity") or "INFO"),
                },
            )
            emit(payload)
            return 0 if payload.get("ok") else 5

        chain_origin = load_forward_scheduler_job_chain_origin(
            status_path,
            candidate_hash=candidate_hash,
            candidate_activation_registry_hash=candidate_activation_registry_hash,
            candidate_activated_at=candidate_activated_at,
        )
        if chain_origin.get("status") != "PASS":
            payload = record_forward_scheduler_status(
                status_path=status_path,
                alert_path=alert_path,
                payload={
                    **base,
                    "ok": False,
                    "status": "SCHEDULER_JOB_CHAIN_ORIGIN_BLOCKED",
                    "severity": "ERROR",
                    "blockers": list(chain_origin.get("blockers") or ["scheduler_job_chain_origin_invalid"]),
                },
            )
            emit(payload)
            return 5
        previous_receipt_hash = str(chain_origin.get("previous_receipt_hash") or "")
        pre_audit = ledger.audit(candidate_hash)
        pre_ledger = compact_ledger_audit(pre_audit)
        due_signal_dates = sorted({str(item) for item in decision.get("due_signal_dates") or [] if str(item)})
        due_signal_dates_hash = canonical_hash(due_signal_dates)
        started_at = now_ms()
        job_id = canonical_hash({
            "candidate_hash": candidate_hash,
            "candidate_activation_registry_hash": candidate_activation_registry_hash,
            "candidate_activated_at": candidate_activated_at,
            "scheduled_decision_hash": str(decision.get("schedule_decision_hash") or ""),
            "due_signal_dates_hash": due_signal_dates_hash,
            "previous_receipt_hash": previous_receipt_hash,
            "started_at_ms": started_at,
            "nonce_ns": time.time_ns(),
        })

        def failed_observer_attempt(
            *,
            finished_at_ms: int,
            process_state: str,
            return_code: int,
            status: str,
            blocker: str,
        ) -> dict[str, Any]:
            return {
                "ok": False,
                "job_id": job_id,
                "observer_job_id": "",
                "scheduler_previous_receipt_hash": "",
                "candidate_activation_registry_hash": candidate_activation_registry_hash,
                "candidate_activated_at": candidate_activated_at,
                "scheduled_decision_hash": str(decision.get("schedule_decision_hash") or ""),
                "due_signal_dates": due_signal_dates,
                "due_signal_dates_hash": due_signal_dates_hash,
                "started_at_ms": started_at,
                "finished_at_ms": finished_at_ms,
                "process_state": process_state,
                "return_code": return_code,
                "status": status,
                "reason": blocker,
                "blockers": [blocker],
                "observer_artifact_hash": "",
                "observer_artifact_verified": False,
                "observer_evidence_consistent": False,
                "observer_candidate_hash": "",
                "incremental_plan_hash": canonical_hash({}),
                "work_summary_hash": canonical_hash({}),
                "records_hash": canonical_hash([]),
                "processed_count": 0,
                "record_count": 0,
                "processed_signal_dates": [],
                "pre_ledger": pre_ledger,
                "duration_ms": finished_at_ms - started_at,
            }

        command = [
            sys.executable,
            str(PROJECT_ROOT / "run_portfolio_shadow_observation.py"),
            "--scheduler-job-id",
            job_id,
            "--scheduler-previous-receipt-hash",
            previous_receipt_hash,
        ]
        creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
        child_environment = {
            key: value
            for key, value in os.environ.items()
            if not any(
                marker in key.upper()
                for marker in ("API_KEY", "SECRET", "PASSPHRASE", "PASSWORD", "TOKEN")
            )
        }
        child_environment.update({
            "HAKIMI_SKIP_LOCAL_AI_ENV": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        observer_payload: dict[str, Any] = {}
        artifact_payload: dict[str, Any] = {}
        artifact_verification: dict[str, Any] = {"status": "BLOCK"}
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=child_environment,
                timeout=max(int(args.runner_timeout), 30),
                creationflags=creation_flags,
                check=False,
            )
            finished_at = now_ms()
            observer_payload = parse_json_output(completed.stdout)
            observer_ok = completed.returncode == 0 and observer_payload.get("ok") is True
            artifact_payload = dict(observer_payload)
            artifact_payload.pop("status_artifact", None)
            artifact_verification = verify_forward_status_artifact(
                artifact_payload,
                candidate_hash=candidate_hash,
            ) if artifact_payload else {"status": "BLOCK"}
            records_raw = observer_payload.get("records")
            records = list(records_raw) if isinstance(records_raw, list) else []
            incremental_plan_valid = isinstance(observer_payload.get("incremental_plan"), dict)
            incremental_plan = (
                dict(observer_payload.get("incremental_plan") or {})
                if isinstance(observer_payload.get("incremental_plan"), dict)
                else {}
            )
            work_summary_valid = isinstance(observer_payload.get("work_summary"), dict)
            work_summary = (
                dict(observer_payload.get("work_summary") or {})
                if isinstance(observer_payload.get("work_summary"), dict)
                else {}
            )
            processed_count = work_summary.get("processed_count")
            processed_count_valid = (
                isinstance(processed_count, int)
                and not isinstance(processed_count, bool)
                and processed_count >= 0
            )
            processed_count = int(processed_count) if processed_count_valid else 0
            processed_signal_dates = [
                str(item.get("signal_date") or "")
                for item in records
                if isinstance(item, dict)
            ]
            records_valid = (
                isinstance(records_raw, list)
                and len(processed_signal_dates) == len(records)
                and all(valid_date(item) for item in processed_signal_dates)
            )
            record_count = len(records) if records_valid else 0
            if not records_valid:
                processed_signal_dates = []
            observer_job_id = str(observer_payload.get("scheduler_job_id") or "")
            if not sha256_hex(observer_job_id):
                observer_job_id = ""
            observer_previous_receipt_hash = str(
                observer_payload.get("scheduler_previous_receipt_hash") or ""
            )
            observer_previous_receipt_hash_valid = (
                not observer_previous_receipt_hash
                or sha256_hex(observer_previous_receipt_hash)
            )
            if not observer_previous_receipt_hash_valid:
                observer_previous_receipt_hash = ""
            observer_artifact_hash = str(observer_payload.get("artifact_hash") or "")
            if not sha256_hex(observer_artifact_hash):
                observer_artifact_hash = ""
            observer_status = str(observer_payload.get("status") or "OUTPUT_INVALID")
            structured_block = (
                observer_payload.get("ok") is False
                and observer_status in {
                    "BLOCK",
                    "CLOCK_ATTESTATION_BLOCKED",
                    "INCREMENTAL_OBSERVATION_PLAN_BLOCKED",
                    "FORWARD_VALIDATION_BLOCKED",
                }
            )
            observer = {
                "ok": observer_ok,
                "job_id": job_id,
                "observer_job_id": observer_job_id,
                "scheduler_previous_receipt_hash": observer_previous_receipt_hash,
                "candidate_activation_registry_hash": candidate_activation_registry_hash,
                "candidate_activated_at": candidate_activated_at,
                "scheduled_decision_hash": str(decision.get("schedule_decision_hash") or ""),
                "due_signal_dates": due_signal_dates,
                "due_signal_dates_hash": due_signal_dates_hash,
                "started_at_ms": started_at,
                "finished_at_ms": finished_at,
                "process_state": "EXITED",
                "return_code": int(completed.returncode),
                "status": observer_status,
                "reason": str(observer_payload.get("reason") or ""),
                "blockers": list(
                    observer_payload.get("blockers")
                    or dict(observer_payload.get("dataset_manifest") or {}).get("blockers")
                    or dict(observer_payload.get("frozen_dataset_manifest") or {}).get("blockers")
                    or []
                ),
                "observer_artifact_hash": observer_artifact_hash,
                "observer_artifact_verified": artifact_verification.get("status") == "PASS",
                "observer_evidence_consistent": structured_block or (
                    incremental_plan_valid and work_summary_valid and processed_count_valid and records_valid
                ),
                "observer_candidate_hash": str(observer_payload.get("candidate_hash") or ""),
                "incremental_plan_hash": canonical_hash(incremental_plan),
                "work_summary_hash": canonical_hash(work_summary),
                "records_hash": canonical_hash(records),
                "processed_count": processed_count,
                "record_count": record_count,
                "processed_signal_dates": processed_signal_dates,
                "pre_ledger": pre_ledger,
                "duration_ms": finished_at - started_at,
            }
            observer["observer_evidence_consistent"] = bool(
                observer.get("observer_evidence_consistent") is True
                and observer.get("observer_artifact_verified") is True
                and observer_previous_receipt_hash_valid
                and observer_previous_receipt_hash == previous_receipt_hash
            )
            if observer.get("observer_evidence_consistent") is not True:
                observer.update({
                    "incremental_plan_hash": canonical_hash({}),
                    "work_summary_hash": canonical_hash({}),
                    "records_hash": canonical_hash([]),
                    "processed_count": 0,
                    "record_count": 0,
                    "processed_signal_dates": [],
                })
        except subprocess.TimeoutExpired:
            finished_at = now_ms()
            observer_ok = False
            observer = failed_observer_attempt(
                finished_at_ms=finished_at,
                process_state="TIMED_OUT",
                return_code=-1,
                status="OBSERVER_TIMEOUT",
                blocker="observer_timeout",
            )
        except OSError as exc:
            finished_at = now_ms()
            observer_ok = False
            observer = failed_observer_attempt(
                finished_at_ms=finished_at,
                process_state="LAUNCH_FAILED",
                return_code=-1,
                status="OBSERVER_LAUNCH_FAILED",
                blocker=f"observer_launch_failed:{type(exc).__name__}",
            )
        except Exception as exc:
            finished_at = now_ms()
            observer_ok = False
            return_code = int(getattr(locals().get("completed"), "returncode", -1))
            observer = failed_observer_attempt(
                finished_at_ms=finished_at,
                process_state="EXITED",
                return_code=return_code,
                status="OBSERVER_OUTPUT_INVALID",
                blocker=f"observer_output_invalid:{type(exc).__name__}",
            )

        post_audit = ledger.audit(candidate_hash)
        post_ledger = compact_ledger_audit(post_audit)
        post_active = load_active_portfolio_candidate(REPORT_DIR)
        post_activation = dict(post_active.get("activation_verification") or {})
        post_candidate_hash = str((post_active.get("candidate") or {}).get("candidate_hash") or "")
        post_activation_registry_hash = str(post_activation.get("registry_hash") or "")
        post_activated_at = int(post_activation.get("activated_at") or 0)
        artifact_ledger = observer_payload.get("ledger")
        artifact_forward_audit = (
            dict(artifact_ledger.get("forward_audit") or {})
            if isinstance(artifact_ledger, dict)
            else {}
        )
        observer.update({
            "post_candidate_hash": post_candidate_hash,
            "post_activation_registry_hash": post_activation_registry_hash,
            "post_activated_at": post_activated_at,
            "post_ledger": post_ledger,
            "observer_artifact_post_ledger_match": bool(
                observer.get("observer_artifact_verified") is True
                and artifact_forward_audit
                and canonical_hash(artifact_forward_audit) == post_ledger["ledger_audit_hash"]
            ),
        })
        attempt_evidence = build_forward_scheduler_attempt_evidence(
            {
                "candidate_hash": candidate_hash,
                "observer": observer,
            },
            previous_receipt_hash=previous_receipt_hash,
        )
        attempt_verification = verify_forward_scheduler_attempt_evidence(
            attempt_evidence,
            candidate_hash=candidate_hash,
        )
        if attempt_verification.get("status") != "PASS":
            raise RuntimeError("scheduler_attempt_evidence_invalid")
        write_parent_sealed_attempt_artifact(
            candidate_hash=candidate_hash,
            observer=observer,
            child_artifact=artifact_payload,
            child_artifact_verified=observer.get("observer_evidence_consistent") is True,
            post_audit=post_audit,
            attempt_evidence=attempt_evidence,
        )
        post_decision = scheduler_decision()
        retry_required = observer_ok and post_decision.get("action") == "RUN_OBSERVER"
        payload = record_forward_scheduler_status(
            status_path=status_path,
            alert_path=alert_path,
            payload={
                **base,
                "ok": observer_ok,
                "status": "OBSERVER_RETRY_REQUIRED" if retry_required else "OBSERVER_COMPLETED" if observer_ok else "OBSERVER_FAILED",
                "severity": "DUE" if retry_required else "INFO" if observer_ok else "ERROR",
                "decision": post_decision,
                "blockers": list(post_decision.get("blockers") or []) if observer_ok else list(dict.fromkeys([
                    str(observer.get("reason") or observer.get("status") or "observer_failed"),
                    *[str(item) for item in observer.get("blockers") or [] if str(item)],
                ])),
                "observer_invoked": True,
                "observer": observer,
            },
        )
        emit(payload)
        return 0 if payload.get("ok") else 6
    except Exception as exc:
        payload = record_forward_scheduler_status(
            status_path=status_path,
            alert_path=alert_path,
            payload={
                "ok": False,
                "status": "SCHEDULER_UNHANDLED_ERROR",
                "severity": "ERROR",
                "generated_at": now_ms(),
                "blockers": [type(exc).__name__],
                "scheduled_invocation": bool(args.scheduled),
            },
        )
        emit(payload)
        return 7
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
