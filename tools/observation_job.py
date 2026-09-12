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
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import uuid

WRAPPER_SHA256 = "213e855414e125b419c0153f189b01415bb22d68e0f3f168c21e5014ac4472da"
PLAN_SHA256 = "f2a02318846a8bd9ed80c667920d9b6c8fc7b27a1b27b70010f9422d0bf0b3d3"
SOURCE_SHA256 = "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5"
ENVIRONMENT_SHA256 = "eb9a19e1db1204b430c9f35f380d107f858fc3263703eabc2e1bd64e315d376e"
UTC = timezone.utc
EXECUTION_TIMEOUT_SECONDS = 300
CLEANUP_TIMEOUT_SECONDS = 5
OUTPUT_LIMIT_BYTES = 4 * 1024 * 1024

# The isolated bootstrap cannot spawn the observer until its parent puts it in
# the owned job. -I -S excludes site startup hooks; stdin is only a launch gate.
_OWNED_BOOTSTRAP = '''import os, sys
if os.read(0, 1) != b"R":
    raise SystemExit(125)
import subprocess
raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW))
'''


class _WindowsJob:
    """Unnamed, non-inheritable job; only descendants of our gated child join."""
    def __init__(self):
        import ctypes as c
        from ctypes import wintypes as w

        class BasicLimits(c.Structure):
            _fields_ = [("process_time", c.c_longlong), ("job_time", c.c_longlong),
                        ("flags", w.DWORD), ("minimum_working_set", c.c_size_t),
                        ("maximum_working_set", c.c_size_t), ("active_limit", w.DWORD),
                        ("affinity", c.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class IoCounters(c.Structure):
            _fields_ = [(name, c.c_ulonglong) for name in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class ExtendedLimits(c.Structure):
            _fields_ = [("basic", BasicLimits), ("io", IoCounters),
                        ("process_memory", c.c_size_t), ("job_memory", c.c_size_t),
                        ("peak_process_memory", c.c_size_t), ("peak_job_memory", c.c_size_t)]

        class Accounting(c.Structure):
            _fields_ = [("user_time", c.c_longlong), ("kernel_time", c.c_longlong),
                        ("period_user_time", c.c_longlong), ("period_kernel_time", c.c_longlong),
                        ("page_faults", w.DWORD), ("total_processes", w.DWORD),
                        ("active_processes", w.DWORD), ("terminated_processes", w.DWORD)]

        class ProcessIds(c.Structure):
            _fields_ = [("assigned", w.DWORD), ("returned", w.DWORD), ("ids", c.c_size_t * 4096)]

        self.c, self.accounting, self.process_ids = c, Accounting, ProcessIds
        self.api = c.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([w.LPVOID, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, c.c_int, w.LPVOID, w.DWORD], w.BOOL),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "QueryInformationJobObject": ([w.HANDLE, c.c_int, w.LPVOID, w.DWORD, c.POINTER(w.DWORD)], w.BOOL),
            "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "IsProcessInJob": ([w.HANDLE, w.HANDLE, c.POINTER(w.BOOL)], w.BOOL),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
            "CloseHandle": ([w.HANDLE], w.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.api.CreateJobObjectW(None, None)
        self._check(self.handle)
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway
        try:
            self._check(self.api.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)))
        except BaseException:
            self.close()
            raise

    def _check(self, result):
        if not result:
            raise self.c.WinError(self.c.get_last_error())

    def assign(self, process):
        # This is the live handle returned by Popen, never a discovered PID.
        self._check(self.api.AssignProcessToJobObject(self.handle, int(process._handle)))

    def active_count(self):
        value = self.accounting()
        self._check(self.api.QueryInformationJobObject(self.handle, 1, self.c.byref(value), self.c.sizeof(value), None))
        return value.active_processes

    def terminate(self):
        self._check(self.api.TerminateJobObject(self.handle, 1))

    def retain_process_handles(self):
        """Keep wait-only handles for job members while termination cancels I/O."""
        from ctypes import wintypes
        members = self.process_ids()
        self._check(self.api.QueryInformationJobObject(self.handle, 3, self.c.byref(members), self.c.sizeof(members), None))
        if members.returned != members.assigned or members.returned > 4096:
            raise OSError("owned_job_process_list_incomplete")
        handles = []
        try:
            for pid in members.ids[:members.returned]:
                handle = self.api.OpenProcess(0x101000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
                if not handle and self.c.get_last_error() == 87:
                    continue  # already exited before opening; no action by PID
                self._check(handle)
                try:
                    ours = wintypes.BOOL()
                    self._check(self.api.IsProcessInJob(handle, self.handle, self.c.byref(ours)))
                    if ours.value:
                        handles.append(handle)
                        handle = None
                finally:
                    if handle:
                        self.api.CloseHandle(handle)
            return handles
        except BaseException:
            self.release_process_handles(handles)
            raise

    def wait_for_exits(self, handles, deadline):
        for handle in handles:
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            if self.api.WaitForSingleObject(handle, remaining_ms) != 0:
                return False
        return True

    def release_process_handles(self, handles):
        for handle in handles:
            self.api.CloseHandle(handle)

    def close(self):
        if self.handle:
            self._check(self.api.CloseHandle(self.handle))
            self.handle = None


def _run_owned_windows(argv, root, *, environment, timeout_seconds, output_limit_bytes, cleanup_seconds):
    if os.name != "nt":
        raise OSError("owned_observation_executor_requires_windows_job_objects")
    started = time.monotonic()
    deadline = started + timeout_seconds
    job = _WindowsJob()
    process = None
    owned_process_handles = []
    readers = []
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    seen = {"stdout": 0, "stderr": 0}
    output_lock = threading.Lock()
    exceeded, read_failed = threading.Event(), threading.Event()
    outcome = "EXITED"
    cleanup_confirmed = False
    cleanup_deadline = None

    def read_stream(name, stream):
        try:
            while True:
                block = stream.read(65536)
                if not block:
                    return
                with output_lock:
                    seen[name] += len(block)
                    remaining = output_limit_bytes - sum(len(value) for value in captured.values())
                    captured[name].extend(block[:remaining])
                    if len(block) > remaining:
                        exceeded.set()
                        # Keep draining while termination cancels pending writes;
                        # retain no extra bytes and never wait beyond cleanup.
        except (OSError, ValueError):
            read_failed.set()

    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", _OWNED_BOOTSTRAP, *argv],
            cwd=root, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0, close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        job.assign(process)  # failure leaves the bootstrap gated; no observer starts
        for name in ("stdout", "stderr"):
            thread = threading.Thread(target=read_stream, args=(name, getattr(process, name)), daemon=True)
            thread.start()
            readers.append(thread)
        process.stdin.write(b"R")
        process.stdin.close()
        while process.poll() is None:
            if exceeded.is_set():
                outcome = "OUTPUT_LIMIT"
                break
            if read_failed.is_set():
                outcome = "OUTPUT_READ_FAILED"
                break
            if time.monotonic() >= deadline:
                outcome = "TIMED_OUT"
                break
            exceeded.wait(min(0.02, max(0, deadline - time.monotonic())))
        if exceeded.is_set():
            outcome = "OUTPUT_LIMIT"
        active = job.active_count()
        cleanup_deadline = time.monotonic() + cleanup_seconds
        if active:
            if outcome == "EXITED":
                outcome = "LEFTOVER_DESCENDANTS"
            owned_process_handles = job.retain_process_handles()
            job.terminate()
        while job.active_count() and time.monotonic() < cleanup_deadline:
            time.sleep(0.01)
        cleanup_confirmed = job.active_count() == 0 and job.wait_for_exits(owned_process_handles, cleanup_deadline)
        if cleanup_confirmed:
            process.wait(timeout=max(0.001, cleanup_deadline - time.monotonic()))
        for thread in readers:
            thread.join(timeout=max(0, cleanup_deadline - time.monotonic()))
        if any(thread.is_alive() for thread in readers) or not cleanup_confirmed:
            outcome = "CLEANUP_NOT_CONFIRMED"
            cleanup_confirmed = False
        elif exceeded.is_set():
            outcome = "OUTPUT_LIMIT"
        elif read_failed.is_set():
            outcome = "OUTPUT_READ_FAILED"
    finally:
        # Closing this private handle also covers abrupt launcher termination.
        # A failed assignment can only leave our still-gated bootstrap, which has
        # no children and can safely be terminated through its original handle.
        job.close()
        job.release_process_handles(owned_process_handles)
        if process is not None:
            if process.poll() is None:
                process.kill()
                try:
                    remaining = (cleanup_deadline or time.monotonic() + cleanup_seconds) - time.monotonic()
                    process.wait(timeout=max(0.001, remaining))
                except subprocess.TimeoutExpired:
                    cleanup_confirmed = False
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            if not any(thread.is_alive() for thread in readers):
                process.stdout.close()
                process.stderr.close()
    with output_lock:
        raw = {name: bytes(value) for name, value in captured.items()}
        counts = dict(seen)
    decoded = {}
    for name, value in raw.items():
        try:
            decoded[name] = value.decode("utf-8")
        except UnicodeError:
            decoded[name] = value.decode("utf-8", errors="replace")
            if outcome == "EXITED":
                outcome = "OUTPUT_ENCODING_INVALID"
    bounds = {"ownership": "WINDOWS_JOB_BEFORE_OBSERVER_START_NO_BREAKAWAY", "outcome": outcome,
              "timeout_seconds": timeout_seconds, "cleanup_seconds": cleanup_seconds,
              "output_limit_bytes_combined": output_limit_bytes, "bytes_seen": counts,
              "bytes_retained": {name: len(value) for name, value in raw.items()},
              "captured_sha256": {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()},
              "output_truncated": exceeded.is_set(), "cleanup_confirmed": cleanup_confirmed,
              "owned_process_handles_waited": len(owned_process_handles),
              "elapsed_monotonic_seconds": time.monotonic() - started}
    return SimpleNamespace(returncode=process.returncode, stdout=decoded["stdout"], stderr=decoded["stderr"], bounds=bounds)


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


def execute(argv, root, *, timeout_seconds=EXECUTION_TIMEOUT_SECONDS,
            output_limit_bytes=OUTPUT_LIMIT_BYTES, cleanup_seconds=CLEANUP_TIMEOUT_SECONDS):
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 600 or type(cleanup_seconds) not in (int, float)
            or not math.isfinite(cleanup_seconds) or not 0 < cleanup_seconds <= 10
            or type(output_limit_bytes) is not int or not 1 <= output_limit_bytes <= OUTPUT_LIMIT_BYTES):
        raise ValueError("invalid_owned_process_bounds")
    if type(argv) is not list or not argv or any(type(arg) is not str or not arg or "\0" in arg for arg in argv):
        raise ValueError("invalid_child_arguments")
    environment = {key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return _run_owned_windows(argv, root, environment=environment, timeout_seconds=timeout_seconds,
                              output_limit_bytes=output_limit_bytes, cleanup_seconds=cleanup_seconds)


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
    start = sealed({"schema_version": "observation-job-start-v2", "attempt_id": attempt_id,
                    "launcher_function_started_at": stamp(started), "input_cutoff": stamp(cutoff),
                    "scheduler_event_at": scheduler_event_at, "trigger_evidence": "CALLER_SUPPLIED_SCHEDULER_EVENT" if scheduler_event_at else "PROCESS_START_ONLY",
                    "underlying_trigger_kind": "SCHEDULED" if scheduler_event_at else "MANUAL",
                    "purpose": "DETERMINISTIC_PROCESS_WITHOUT_INVENTED_SCHEDULER_CLOCK", "launcher_sha256": file_hash(Path(__file__)),
                    "frozen_wrapper_sha256": WRAPPER_SHA256, "frozen_plan_sha256": PLAN_SHA256, "order_allowed": False,
                    "execution_bounds": {"timeout_seconds": EXECUTION_TIMEOUT_SECONDS,
                                         "cleanup_seconds": CLEANUP_TIMEOUT_SECONDS,
                                         "combined_output_limit_bytes": OUTPUT_LIMIT_BYTES,
                                         "ownership": "WINDOWS_JOB_BEFORE_OBSERVER_START_NO_BREAKAWAY"}})
    write_new(directory / "started.json", start)
    end = {"schema_version": "observation-job-end-v2", "attempt_id": attempt_id, "started_receipt_hash": start["receipt_hash"],
           "input_cutoff": stamp(cutoff), "health": "FAILED_PREFLIGHT", "result_valid": False,
           "child_launch_boundary_at": None, "child_wait_completed_at": None, "child_exit_code": None, "child_execution_bounds": None,
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
                latest_completion = launch + timedelta(seconds=EXECUTION_TIMEOUT_SECONDS + CLEANUP_TIMEOUT_SECONDS + 30)
                if launch.replace(minute=0, second=0, microsecond=0) != cutoff or latest_completion >= cutoff + timedelta(hours=1):
                    raise ValueError("hour_changed_or_insufficient_frozen_wrapper_budget")
                end["child_launch_boundary_at"] = stamp(launch)
                stage = "EXECUTE"
                child = execute(command(root, scheduler_event_at), root)
                completed = now()
                end.update(child_wait_completed_at=stamp(completed), child_exit_code=child.returncode)
                end["stdout_sha256"] = hashlib.sha256(child.stdout.encode("utf-8")).hexdigest()
                end["stderr_sha256"] = hashlib.sha256(child.stderr.encode("utf-8")).hexdigest()
                bounds = getattr(child, "bounds", None)
                end["child_execution_bounds"] = bounds
                if bounds is not None and (bounds["outcome"] != "EXITED" or not bounds["cleanup_confirmed"]):
                    end["health"] = "CHILD_" + bounds["outcome"]
                    raise ValueError("child_execution_boundary_failed")
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
        elif stage == "EXECUTE" and end["child_exit_code"] is None and end["health"] == "FAILED_PREFLIGHT":
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
