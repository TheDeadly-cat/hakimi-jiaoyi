"""Deterministic launcher for the pinned read-only observer; no task registration.

An OS task provides process-start evidence, not an independently observed scheduler
event. Without --scheduler-event-at the frozen wrapper is deliberately MANUAL.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

WRAPPER_SHA256 = "213e855414e125b419c0153f189b01415bb22d68e0f3f168c21e5014ac4472da"
PLAN_SHA256 = "f2a02318846a8bd9ed80c667920d9b6c8fc7b27a1b27b70010f9422d0bf0b3d3"
SOURCE_SHA256 = "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5"
ENVIRONMENT_SHA256 = "eb9a19e1db1204b430c9f35f380d107f858fc3263703eabc2e1bd64e315d376e"
UTC = timezone.utc


def now():
    return datetime.now(UTC)


def stamp(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(UTC)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                    allow_nan=False, separators=(",", ":")).encode("ascii")).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(value):
    return dict(value, receipt_hash=digest(value))


def verify_seal(value):
    if not isinstance(value, dict) or value.get("receipt_hash") != digest({k: v for k, v in value.items() if k != "receipt_hash"}):
        raise ValueError("invalid_receipt_seal")
    return value


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("document_too_large")
    return json.loads(raw)


def write_new(path, value):
    """Publish an entire receipt atomically without replacing an existing name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ("." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="ascii", newline="\n") as stream:
            json.dump(value, stream, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def job_lock(path):
    """One launcher at a time; the frozen wrapper retains its own cutoff lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                except OSError:
                    pass
            else:
                import fcntl
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except BlockingIOError:
                    pass
            yield acquired
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def verify_deployment(root):
    wrapper = root / "tools/forward_reliability.py"
    plan_path = root / "forward/reliability-plan-20260906.json"
    plan = read_json(plan_path)
    if file_hash(wrapper) != WRAPPER_SHA256 or digest(plan) != PLAN_SHA256:
        raise ValueError("frozen_deployment_identity_changed")
    if plan.get("source_sha256") != SOURCE_SHA256 or plan.get("environment_sha256") != ENVIRONMENT_SHA256:
        raise ValueError("frozen_source_or_environment_plan_changed")
    if plan.get("order_allowed") is not False or plan.get("automatic_backfill") is not False:
        raise ValueError("frozen_plan_boundary_changed")
    python = root / "venv/Scripts/python.exe"
    if not python.is_file():
        raise ValueError("deployed_python_missing")
    return plan


def command(root, scheduler_event_at):
    argv = [str(root / "venv/Scripts/python.exe"), "-B", str(root / "tools/forward_reliability.py"), "run",
            "--runtime-root", str(root), "--plan", str(root / "forward/reliability-plan-20260906.json"),
            "--trigger-kind", "SCHEDULED" if scheduler_event_at else "MANUAL"]
    if scheduler_event_at:
        argv += ["--trigger-at", scheduler_event_at]
    return argv


def execute(argv, root):
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # The pinned wrapper owns its bounded collector timeout. Do not kill its
    # parent alone and leave a collector running without its original lock.
    return subprocess.run(argv, cwd=root, env=environment, capture_output=True,
                          text=True, encoding="utf-8", creationflags=flags)


def absences(cycle, allowed_plans):
    result = set()
    for item in cycle.get("prior_absences", []):
        missing_at = timestamp(item["cutoff"])
        if stamp(missing_at) != item["cutoff"] or missing_at >= timestamp(cycle["cutoff"]):
            raise ValueError("invalid_prior_absence_cutoff")
        for plan_hash in item["missing_plan_hashes"]:
            if plan_hash not in allowed_plans:
                raise ValueError("unrecognized_missing_plan")
            result.add((item["cutoff"], plan_hash))
    return result


def previous_absences(root, cutoff, allowed_plans):
    """Use existing driver data as baseline, including an already-recorded hour."""
    latest = None
    for path in sorted((root / "forward/cycles").glob("*/forward_cycle_fixed.json")):
        cycle = read_json(path)
        candidate = timestamp(cycle["cutoff"])
        if candidate <= cutoff and (latest is None or candidate > latest[0]):
            latest = (candidate, cycle, path)
    return (absences(latest[1], allowed_plans), file_hash(latest[2])) if latest else (set(), None)


def prior_attempts(job_root, current_id):
    result = []
    for path in sorted((job_root / "attempts").glob("*/started.json")):
        start = verify_seal(read_json(path))
        if start["attempt_id"] == current_id:
            continue
        end_path = path.parent / "ended.json"
        end = verify_seal(read_json(end_path)) if end_path.exists() else None
        if end and end["started_receipt_hash"] != start["receipt_hash"]:
            raise ValueError("prior_receipt_binding_mismatch")
        result.append((start, end))
    return result


def validate_result(value, cutoff, plan, completed):
    verify_seal(value)
    allowed = {p["plan_hash"] for p in plan["plans"]}
    if (value.get("plan_hash") != PLAN_SHA256 or value.get("input_cutoff") != stamp(cutoff)
            or value.get("status") != "RECORDED_AND_REPLAYED" or value.get("exit_code") != 0
            or value.get("observations") != 2 or value.get("replays_verified") != 2
            or value.get("order_allowed") is not False or value.get("automatic_backfill") is not False
            or value.get("original_bytes_preserved") is not True):
        raise ValueError("invalid_current_cutoff_result")
    verification = value.get("runtime_verification", {})
    if (verification.get("source_sha256") != SOURCE_SHA256 or verification.get("environment_sha256") != ENVIRONMENT_SHA256
            or verification.get("source_status") != "BUILD_VERIFIED" or verification.get("environment_status") != "VERIFIED"):
        raise ValueError("unverified_child_runtime")
    records = value.get("records", [])
    if len(records) != 2 or {r.get("plan_hash") for r in records} != allowed:
        raise ValueError("invalid_result_plan_set")
    for record in records:
        signal_at = timestamp(record["signal_available_at"])
        if (record.get("cutoff") != stamp(cutoff) or record.get("backfill") is not False
                or not cutoff <= signal_at <= completed
                or record.get("timing_status") != ("ON_TIME" if signal_at <= cutoff + timedelta(seconds=300) else "LATE")):
            raise ValueError("invalid_result_clock_or_timing")
    return value


def run(root, job_root, *, scheduler_event_at=None):
    started, monotonic_start = now(), time.monotonic()
    if scheduler_event_at is not None:
        timestamp(scheduler_event_at)  # Reject arbitrary non-clock text before persisting it.
    root, job_root = root.resolve(), job_root.resolve()
    if job_root == root or job_root.is_relative_to(root):
        raise ValueError("job_receipts_must_be_outside_frozen_deployment")
    cutoff = started.replace(minute=0, second=0, microsecond=0)
    attempt_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex
    directory = job_root / "attempts" / attempt_id
    start = sealed({"schema_version": "observation-job-start-v1", "attempt_id": attempt_id,
                    "launcher_function_started_at": stamp(started), "input_cutoff": stamp(cutoff),
                    "scheduler_event_at": scheduler_event_at, "trigger_evidence": "CALLER_SUPPLIED_SCHEDULER_EVENT" if scheduler_event_at else "PROCESS_START_ONLY",
                    "underlying_trigger_kind": "SCHEDULED" if scheduler_event_at else "MANUAL",
                    "purpose": "DETERMINISTIC_PROCESS_WITHOUT_INVENTED_SCHEDULER_CLOCK", "launcher_sha256": file_hash(Path(__file__)),
                    "frozen_wrapper_sha256": WRAPPER_SHA256, "frozen_plan_sha256": PLAN_SHA256, "order_allowed": False})
    write_new(directory / "started.json", start)
    end = {"schema_version": "observation-job-end-v1", "attempt_id": attempt_id, "started_receipt_hash": start["receipt_hash"],
           "input_cutoff": stamp(cutoff), "health": "FAILED_PREFLIGHT", "result_valid": False,
           "child_launch_boundary_at": None, "child_wait_completed_at": None, "child_exit_code": None,
           "prior_unfinished_attempts": [], "new_unfinished_attempts": [], "new_missing_strategy_hours": [], "order_allowed": False,
           "notification": {"decision": "NOTIFY", "reasons": [], "delivery_status": "NOT_SENT_BY_THIS_TOOL"}}
    stage = "PREFLIGHT"
    try:
        if scheduler_event_at and timestamp(scheduler_event_at) > started:
            raise ValueError("scheduler_event_cannot_postdate_process_start")
        plan = verify_deployment(root)
        allowed = {p["plan_hash"] for p in plan["plans"]}
        with job_lock(job_root / "launcher.lock") as acquired:
            if not acquired:
                end.update(health="DUPLICATE_IN_FLIGHT")
                end["notification"].update(decision="DONT_NOTIFY", reasons=["launcher_lock_owned"])
            else:
                prior = prior_attempts(job_root, attempt_id)
                end["prior_unfinished_attempts"] = [s["attempt_id"] for s, e in prior if e is None]
                acknowledged_unfinished = {a for s, e in prior if e for a in e.get("prior_unfinished_attempts", [])}
                end["new_unfinished_attempts"] = sorted(set(end["prior_unfinished_attempts"]) - acknowledged_unfinished)
                baseline, baseline_hash = previous_absences(root, cutoff, allowed)
                end["previous_driver_sha256"] = baseline_hash
                launch = now()
                if launch.replace(minute=0, second=0, microsecond=0) != cutoff or launch.minute >= 55:
                    raise ValueError("hour_changed_or_insufficient_frozen_wrapper_budget")
                end["child_launch_boundary_at"] = stamp(launch)
                stage = "EXECUTE"
                child = execute(command(root, scheduler_event_at), root)
                completed = now()
                end.update(child_wait_completed_at=stamp(completed), child_exit_code=child.returncode)
                end["stdout_sha256"] = hashlib.sha256(child.stdout.encode("utf-8")).hexdigest()
                end["stderr_sha256"] = hashlib.sha256(child.stderr.encode("utf-8")).hexdigest()
                if child.returncode:
                    end["health"] = "CHILD_TERMINATED" if child.returncode < 0 else "CHILD_FAILED"
                    raise ValueError("child_nonzero_exit")
                stage = "VALIDATE"
                if len(child.stdout.encode("utf-8")) > 4 * 1024 * 1024:
                    raise ValueError("child_output_too_large")
                value = verify_seal(json.loads(child.stdout))
                if value.get("status") == "DUPLICATE_IN_FLIGHT":
                    if value.get("input_cutoff") != stamp(cutoff) or value.get("plan_hash") != PLAN_SHA256 or value.get("order_allowed") is not False:
                        raise ValueError("invalid_duplicate_receipt")
                    end.update(health="DUPLICATE_IN_FLIGHT", frozen_receipt_hash=value["receipt_hash"])
                    end["notification"].update(decision="DONT_NOTIFY", reasons=["frozen_cutoff_lock_owned"])
                else:
                    validate_result(value, cutoff, plan, completed)
                    cycle_path = root / "forward/cycles" / cutoff.strftime("%Y%m%dT%H0000Z") / "forward_cycle_fixed.json"
                    cycle = read_json(cycle_path)
                    if (cycle.get("cutoff") != stamp(cutoff) or cycle.get("status") != "RECORDED_AND_REPLAYED"
                            or cycle.get("observations") != 2 or cycle.get("replays_verified") != 2 or cycle.get("order_allowed") is not False
                            or cycle.get("automatic_backfill") is not False):
                        raise ValueError("driver_result_mismatch")
                    new_missing = absences(cycle, allowed) - baseline
                    end["new_missing_strategy_hours"] = [{"cutoff": c, "plan_hash": p} for c, p in sorted(new_missing)]
                    duplicate = value.get("classification") == "DUPLICATE_VERIFY"
                    late = any(r["timing_status"] == "LATE" for r in value["records"])
                    end.update(health="DUPLICATE_VERIFY" if duplicate else "LATE" if late else "RESULT_VALID", result_valid=True,
                               frozen_receipt_hash=value["receipt_hash"], current_driver_sha256=file_hash(cycle_path),
                               records=[{k: r[k] for k in ("plan_hash", "cutoff", "record_hash", "signal_available_at", "timing_status")} for r in value["records"]])
                    reasons = (["late_observation"] if late and not duplicate else [])
                    if new_missing:
                        reasons.append("new_missing_strategy_hours_including_outside_frozen_window")
                    if end["new_unfinished_attempts"]:
                        reasons.append("prior_start_without_end")
                    prior_ends = [e for s, e in prior if e is not None and e["health"] != "DUPLICATE_IN_FLIGHT"]
                    if prior_ends and prior_ends[-1]["result_valid"] is False:
                        reasons.append("recovered_after_failed_result")
                    end["notification"].update(decision="NOTIFY" if reasons else "DONT_NOTIFY", reasons=reasons)
    except Exception as exc:
        if stage == "VALIDATE":
            end["health"] = "EXIT_ZERO_RESULT_INVALID"
        elif stage == "EXECUTE" and end["child_exit_code"] is None:
            end["health"] = "CHILD_START_OR_WAIT_FAILED"
        # Never copy exception text or child stderr into user-facing receipts.
        end["error"] = {"type": type(exc).__name__, "stage": stage}
        end["notification"].update(decision="NOTIFY", reasons=[end["health"].lower()])
    end["launcher_record_ended_at"] = stamp(now())
    end["launcher_elapsed_monotonic_seconds"] = time.monotonic() - monotonic_start
    end = sealed(end)
    write_new(directory / "ended.json", end)
    return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--job-root", type=Path, required=True)
    parser.add_argument("--scheduler-event-at", help="Actual caller-observed scheduler event; never a nominal or reconstructed time")
    args = parser.parse_args()
    try:
        result = run(args.runtime_root, args.job_root, scheduler_event_at=args.scheduler_event_at)
    except Exception as exc:
        print(json.dumps({"health": "LAUNCHER_RECEIPT_FAILURE", "error_type": type(exc).__name__, "order_allowed": False}))
        return 1
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return 0 if result["result_valid"] or result["health"] == "DUPLICATE_IN_FLIGHT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
