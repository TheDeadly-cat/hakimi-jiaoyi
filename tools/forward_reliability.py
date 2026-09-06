"""Append-only scheduler receipts and coverage around the frozen forward driver.

No market/strategy/portfolio implementation lives here. Only ``run`` invokes the
existing fixed public-data driver. ``report`` replays local records offline.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

HOUR = timedelta(hours=1)
UTC = timezone.utc


def now():
    return datetime.now(UTC)


def stamp(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() != timedelta(0):
        raise ValueError("UTC_timestamp_required")
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_JSON_key")
        result[key] = value
    return result


def read(path):
    result = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_JSON")))
    if type(result) is not dict:
        raise ValueError("JSON_object_required")
    return result


def write_new(path, value):
    """Publish complete bytes atomically without replacing prior evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".staging-", suffix=".tmp", dir=path.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(staged, path)
        except FileExistsError:
            if path.read_bytes() != encoded:
                raise FileExistsError("append_only_evidence_conflict") from None
    finally:
        staged.unlink(missing_ok=True)
    return path


def seal(value, key):
    return {**value, key: digest(value)}


def verified_seal(value, key):
    if value.get(key) != digest({k: v for k, v in value.items() if k != key}):
        raise ValueError("receipt_integrity_invalid:" + key)
    return value


def load_plan(path):
    plan = read(path)
    start, end = timestamp(plan["start_cutoff"]), timestamp(plan["end_cutoff_exclusive"])
    if (plan["schema_version"] != "forward-reliability-plan-v1"
            or start.minute or start.second or start.microsecond
            or end - start != 72 * HOUR or plan["planned_hours"] != 72
            or plan["timely_seconds"] != 300 or plan["scheduled_minute"] != 1
            or len(plan["plans"]) != 2
            or {p["strategy"] for p in plan["plans"]} != {"dual_ma", "rsi"}
            or len({p["plan_hash"] for p in plan["plans"]}) != 2
            or plan["automatic_backfill"] is not False or plan["order_allowed"] is not False
            or plan["state_policy"] != "FLAT_REFERENCE_OBSERVATION"):
        raise ValueError("fixed_72_hour_two_strategy_reliability_plan_required")
    return plan


def _observer(root):
    spec = importlib.util.spec_from_file_location("reliability_frozen_observer", root / "tools/observe_forward.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_runtime(root, plan):
    expected = root / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")
    if Path(sys.executable).resolve() != expected.resolve():
        raise ValueError("fixed_deployment_installed_python_required")
    for name, sha in plan["runtime_tools"].items():
        target = (root / name).resolve()
        if not target.is_relative_to(root) or file_hash(target) != sha:
            raise ValueError("frozen_runtime_tool_changed:" + name)
    from hakimi_research.environment import build_runtime_provenance
    from hakimi_research.source_layout import REPOSITORY_ROOT
    provenance = build_runtime_provenance()
    source = provenance["source_identity"]
    environment = provenance["environment_verified"]
    environment_hash = digest({"python_version": environment.get("python_version"),
                               "packages": environment.get("packages"),
                               "lock_sha256": provenance["dependency_lock"]["sha256"]})
    if (REPOSITORY_ROOT is not None or source["status"] != "BUILD_VERIFIED"
            or environment["status"] != "VERIFIED"
            or source["content_sha256"] != plan["source_sha256"]
            or environment_hash != plan["environment_sha256"]):
        raise ValueError("frozen_source_or_dependency_environment_changed")
    return {"source_status": source["status"], "source_sha256": source["content_sha256"],
            "environment_status": environment["status"], "environment_sha256": environment_hash,
            "runtime_tools_verified": dict(plan["runtime_tools"])}


@contextmanager
def cutoff_lock(path):
    """OS-owned lock: process death releases it; the lock file is never deleted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    acquired = False
    try:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except (OSError, BlockingIOError):
            pass
        yield acquired
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _hour(root, cutoff):
    return root / "forward/cycles" / cutoff.strftime("%Y%m%dT%H0000Z")


def _originals(root, cutoff):
    hour = _hour(root, cutoff)
    return {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(hour.rglob("*")) if path.is_file()}


def time_fields(record):
    """Derive fields only from recorded clocks; never infer from filesystem mtime."""
    close = timestamp(record["cutoff"])
    received = record.get("input", {}).get("input_available_at")
    available = record.get("signal_available_at")
    if received is not None and timestamp(received) < close:
        raise ValueError("data_received_before_completed_input")
    if available is not None:
        signal_time = timestamp(available)
        if signal_time < close or (received is not None and signal_time < timestamp(received)):
            raise ValueError("signal_availability_precedes_input")
        eligible = stamp(signal_time.replace(minute=0, second=0, microsecond=0) + HOUR)
    else:
        eligible = None
    return {"bar_close_time": stamp(close), "data_received_at": received,
            "signal_available_at": available, "reference_execution_eligible_at": eligible,
            "reference_execution_policy": "FIRST_HOURLY_OPEN_STRICTLY_AFTER_SIGNAL_AVAILABILITY",
            "data_received_at_evidence": "ORIGINAL_INPUT_RECEIPT_CLOCK" if received else "UNAVAILABLE",
            "signal_available_at_evidence": "ORIGINAL_OBSERVER_CLOCK" if available else "UNAVAILABLE",
            "reference_execution_price": None, "reference_execution_performed": False}


def _record_projection(path, record, item, plan):
    verified_seal(record, "record_hash")
    verified_seal({**record["input"], "input_hash": record["input_hash"]}, "input_hash")
    if (record["plan_hash"] != item["plan_hash"]
            or type(record["backfill"]) is not bool or record["output_hash"] != digest(record["signal"])
            or record["signal_available_at"] != record["recorded_at_utc"]
            or record["source_sha256"] != plan["source_sha256"]
            or record["environment_sha256"] != plan["environment_sha256"]
            or record["state_policy"] != "FLAT_REFERENCE_OBSERVATION"
            or record["execution_permission"] != {"research_only": True, "paper_allowed": False,
                                                   "live_allowed": False, "order_allowed": False}
            or record["position_state_observed"] is not False):
        raise ValueError("observation_identity_or_permission_changed")
    fields = time_fields(record)
    delay = (timestamp(record["signal_available_at"]) - timestamp(record["cutoff"])).total_seconds()
    expected = "BACKFILL" if record["backfill"] else "ON_TIME" if delay <= plan["timely_seconds"] else "LATE"
    if record["timing_status"] != expected or record["lateness_seconds"] != delay:
        raise ValueError("observation_timing_mismatch")
    return {"strategy": item["strategy"], "plan_hash": item["plan_hash"], "record_hash": record["record_hash"],
            "record_file_sha256": file_hash(path), "record_file": path.name, "cutoff": record["cutoff"],
            "timing_status": expected, "backfill": record["backfill"], "lateness_seconds": delay,
            "snapshot_id": record["input"]["snapshot_id"], "input_hash": record["input_hash"], **fields}


def inventory(root, plan):
    """Read-only full local replay with the original frozen observer and snapshots."""
    from hakimi_research.dataset_registry import load_snapshot
    observer = _observer(root)
    deployment = read(root / "forward/deployment-plans.json")
    frozen = {value["plan_hash"]: observer._plan(value)
              for item in deployment["plans"] for value in [read(Path(item["plan"]))]}
    if set(frozen) != {item["plan_hash"] for item in plan["plans"]}:
        raise ValueError("deployment_plans_changed")
    result, issues = [], []
    for hour in sorted((root / "forward/cycles").glob("*")):
        for item in plan["plans"]:
            try:
                cutoff = datetime.strptime(hour.name, "%Y%m%dT%H0000Z").replace(tzinfo=UTC)
            except ValueError:
                continue
            identity = digest({"plan_hash": item["plan_hash"], "cutoff": stamp(cutoff)})
            path = hour / "observations" / ("forward_observation_" + identity + ".json")
            if not path.is_file():
                continue
            try:
                record = read(path)
                if record["cutoff"] != stamp(cutoff):
                    raise ValueError("observation_cutoff_mismatch")
                projection = _record_projection(path, record, item, plan)
                input_receipt = verified_seal(read(hour / "forward_input_fixed.json"), "input_receipt_hash")
                if input_receipt["cutoff"] != stamp(cutoff):
                    raise ValueError("input_cutoff_mismatch")
                for entry in input_receipt["files"].values():
                    target = (root / entry["path"]).resolve()
                    if not target.is_relative_to(hour.resolve()) or file_hash(target) != entry["sha256"]:
                        raise ValueError("original_input_bytes_changed")
                snapshot = load_snapshot(root / input_receipt["files"]["snapshot"]["path"])
                replay = observer.replay(frozen[item["plan_hash"]], snapshot, record)
                if replay["status"] != "VERIFIED":
                    raise ValueError("original_observer_replay_failed")
                projection["replay_status"] = "VERIFIED"
                result.append(projection)
            except (ValueError, KeyError, OSError, TypeError) as exc:
                issues.append({"cutoff": stamp(cutoff), "plan_hash": item["plan_hash"],
                               "strategy": item["strategy"], "reason": str(exc)[:200]})
    return result, issues


def attempts(receipt_root):
    result = []
    for start_path in sorted((receipt_root / "attempts").glob("*/started.json")):
        directory = start_path.parent
        start = verified_seal(read(start_path), "receipt_hash")
        end_path = directory / "ended.json"
        end = verified_seal(read(end_path), "receipt_hash") if end_path.is_file() else None
        if end and end["started_receipt_hash"] != start["receipt_hash"]:
            raise ValueError("attempt_parent_receipt_mismatch")
        result.append({"start": start, "end": end})
    return sorted(result, key=lambda value: (value["start"]["actual_started_at"], value["start"]["attempt_id"]))


def _saved_reports(receipt_root, plan):
    reports = []
    for path in sorted((receipt_root / "reports").glob("coverage_*.json")):
        report = verified_seal(read(path), "report_hash")
        if report["plan_hash"] != digest(plan):
            raise ValueError("coverage_plan_changed_in_existing_receipt_root")
        reports.append(report)
    return reports


def _bind_plan(receipt_root, plan, *, create=False):
    target = receipt_root / "plan.json"
    if target.exists():
        if canonical(read(target)) != canonical(plan):
            raise ValueError("immutable_reliability_plan_changed")
    elif create:
        try:
            write_new(target, plan)
        except FileExistsError:
            if canonical(read(target)) != canonical(plan):
                raise ValueError("immutable_reliability_plan_changed") from None


def build_coverage(plan, records, problems, receipt_attempts, previous_reports, as_of):
    first = timestamp(plan["start_cutoff"])
    previous_missing = {(row["cutoff"], row["plan_hash"]) for report in previous_reports
                        for row in report["rows"] if row["status"] == "MISSING"}
    lookup = {(record["cutoff"], record["plan_hash"]): record for record in records if not record["backfill"]}
    if len(lookup) != sum(not record["backfill"] for record in records):
        raise ValueError("duplicate_canonical_observation")
    faulty = {(item["cutoff"], item["plan_hash"]): item for item in problems}
    rows, backfills = [], [record for record in records if record["backfill"]]
    for offset in range(plan["planned_hours"]):
        cutoff = first + offset * HOUR
        cutoff_text = stamp(cutoff)
        elapsed = as_of >= cutoff + timedelta(seconds=plan["timely_seconds"])
        for item in plan["plans"]:
            key = (cutoff_text, item["plan_hash"])
            record = lookup.get(key)
            related = [attempt for attempt in receipt_attempts if attempt["start"]["input_cutoff"] == cutoff_text]
            failed = [attempt for attempt in related if attempt["end"] and attempt["end"]["status"] == "FAILED"]
            # Missing once observed is retained even if a later tool incorrectly
            # publishes a non-backfill observation for the same old hour.
            status = ("PLANNED" if cutoff > as_of else "PENDING" if not elapsed and not record
                      else "MISSING" if key in previous_missing else "FAILED" if key in faulty
                      else record["timing_status"] if record else "FAILED" if failed else "MISSING")
            row = {"cutoff": cutoff_text, "strategy": item["strategy"], "plan_hash": item["plan_hash"],
                   "status": status, "elapsed": elapsed, "scheduled_trigger_at": stamp(cutoff + timedelta(minutes=1)),
                   "deadline": stamp(cutoff + timedelta(seconds=300)), "observation": record,
                   "attempt_ids": [attempt["start"]["attempt_id"] for attempt in related],
                   "execution_receipt_status": "CAPTURED" if related else "UNAVAILABLE",
                   "original_missing_preserved": key in previous_missing,
                   "failure": faulty.get(key)}
            rows.append(row)
    elapsed_rows = [row for row in rows if row["elapsed"]]
    counts = dict(Counter(row["status"] for row in elapsed_rows))
    for status in ("ON_TIME", "LATE", "MISSING", "FAILED"):
        counts.setdefault(status, 0)
    missing = [{"cutoff": row["cutoff"], "plan_hash": row["plan_hash"], "strategy": row["strategy"]}
               for row in elapsed_rows if row["status"] == "MISSING"]
    relevant_attempts = [attempt for attempt in receipt_attempts
                         if first <= timestamp(attempt["start"]["input_cutoff"]) < first + 72 * HOUR]
    terminal = [attempt["end"] for attempt in relevant_attempts if attempt["end"]]
    complete = len(elapsed_rows) == 144 and as_of >= timestamp(plan["end_cutoff_exclusive"])
    report = {"schema_version": "forward-reliability-coverage-v1", "plan_hash": digest(plan),
              "as_of_utc": stamp(as_of), "window_start": plan["start_cutoff"],
              "window_end_exclusive": plan["end_cutoff_exclusive"], "planned_hours": 72,
              "planned_strategy_hours": 144, "elapsed_hours": len(elapsed_rows) // 2,
              "elapsed_strategy_hours": len(elapsed_rows), "counts": counts,
              "future_strategy_hours": sum(row["status"] == "PLANNED" for row in rows),
              "pending_strategy_hours": sum(row["status"] == "PENDING" for row in rows),
              "observed_fraction": ((counts["ON_TIME"] + counts["LATE"]) / len(elapsed_rows)) if elapsed_rows else None,
              "on_time_fraction": counts["ON_TIME"] / len(elapsed_rows) if elapsed_rows else None,
              "window_elapsed": complete, "soak_acceptance": "WINDOW_ELAPSED_REVIEW_REQUIRED" if complete else "INCOMPLETE_72_HOURS",
              "prior_missing_strategy_hours": len(previous_missing),
              "new_missing": [item for item in missing if (item["cutoff"], item["plan_hash"]) not in previous_missing],
              "missing": missing, "backfill_observations_separate": backfills,
              "execution_receipts": {"attempts": len(relevant_attempts), "ended": len(terminal),
                                     "unfinished_start_receipts": len(relevant_attempts) - len(terminal),
                                     "duplicate_triggers": sum(item["classification"].startswith("DUPLICATE") for item in terminal),
                                     "retries": sum(item["classification"].startswith("RETRY") for item in terminal),
                                     "recoveries": sum(item.get("recovery", False) for item in terminal),
                                     "notification_decisions": dict(Counter(item["notification"]["decision"] for item in terminal)),
                                     "notification_delivery": "UNAVAILABLE_UNLESS_SEPARATELY_ACKNOWLEDGED"},
              "first_nonmanual_execution_receipt": next((attempt for attempt in relevant_attempts
                    if attempt["start"]["trigger_kind"] == "SCHEDULED" and attempt["end"]
                    and attempt["end"]["status"] == "RECORDED_AND_REPLAYED"), None),
              "historical_trigger_start_end_exit_evidence": "UNAVAILABLE_FOR_UNWRAPPED_CYCLES",
              "state_policy": "FLAT_REFERENCE_OBSERVATION", "performance_or_holdings_observed": False,
              "automatic_backfill": False, "order_allowed": False, "rows": rows,
              "excluded_manual_first_observations": [record for record in records
                   if record["cutoff"] == plan["manual_first_cutoff_excluded"]]}
    return seal(report, "report_hash")


def report(root, plan, receipt_root, output_dir=None, scheduler_history=None):
    _bind_plan(receipt_root, plan)
    runtime = verify_runtime(root, plan)
    records, problems = inventory(root, plan)
    result = build_coverage(plan, records, problems, attempts(receipt_root), _saved_reports(receipt_root, plan), now())
    # Put runtime verification inside the immutable report identity.
    result.pop("report_hash")
    result["runtime_verification"] = runtime
    result["replays_verified"] = len(records)
    result["validation_failures"] = problems
    if scheduler_history is not None:
        history = read(scheduler_history)
        result["historical_scheduler_evidence"] = {"source_file_sha256": file_hash(scheduler_history), **history}
        for row in result["rows"]:
            matches = [entry for entry in history["cycles"] if entry["cutoff"] == row["cutoff"]]
            if matches:
                row["historical_scheduler_evidence"] = matches[0]
                if not row["attempt_ids"]:
                    row["execution_receipt_status"] = ("HISTORICAL_TRIGGER_AND_TERMINAL_COMMAND"
                        if matches[0]["driver_exit_code"] is not None else "TRIGGER_WITHOUT_EXECUTION_EVIDENCE")
        result["first_nonmanual_historical_evidence"] = next((entry for entry in history["cycles"]
                      if entry["trigger_at"] is not None and entry["driver_exit_code"] == 0), None)
    result = seal(result, "report_hash")
    if output_dir is not None:
        write_new(output_dir / ("coverage_" + result["report_hash"] + ".json"), result)
    return result


def _execute(root):
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", str(root / "tools/run_forward_cycle.py"),
                           "--deployment", str(root / "forward/deployment-plans.json"),
                           "--runtime-root", str(root)], cwd=root, env=environment,
                          capture_output=True, text=True, encoding="utf-8", timeout=240)


def run(root, plan, receipt_root, *, trigger_kind, trigger_at=None):
    started = now()
    cutoff = started.replace(minute=0, second=0, microsecond=0)
    if trigger_kind not in {"SCHEDULED", "MANUAL"} or (trigger_kind == "SCHEDULED" and trigger_at is None):
        raise ValueError("scheduled_trigger_requires_actual_scheduler_timestamp")
    if trigger_at is not None and timestamp(trigger_at) > started:
        raise ValueError("trigger_cannot_postdate_actual_start")
    _bind_plan(receipt_root, plan, create=True)
    attempt_id = started.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex
    directory = receipt_root / "attempts" / attempt_id
    start = seal({"schema_version": "forward-execution-start-v1", "attempt_id": attempt_id,
                  "plan_hash": digest(plan), "trigger_kind": trigger_kind, "trigger_at": trigger_at,
                  "trigger_evidence": "CALLER_SUPPLIED_SCHEDULER_EVENT" if trigger_at else "UNAVAILABLE",
                  "actual_started_at": stamp(started), "input_cutoff": stamp(cutoff),
                  "scheduled_trigger_at": stamp(cutoff + timedelta(minutes=1)),
                  "wrapper_sha256": file_hash(__file__), "order_allowed": False}, "receipt_hash")
    write_new(directory / "started.json", start)
    end = {"schema_version": "forward-execution-end-v1", "attempt_id": attempt_id,
           "started_receipt_hash": start["receipt_hash"], "plan_hash": digest(plan),
           "input_cutoff": stamp(cutoff), "status": "FAILED", "classification": "FIRST_ATTEMPT",
           "exit_code": None, "child_started_at": None, "child_ended_at": None,
           "records": [], "observations": 0, "replays_verified": 0, "recovery": False,
           "original_bytes_preserved": None, "automatic_backfill": False, "order_allowed": False,
           "notification": {"decision": "NOTIFY", "reasons": [], "delivery_status": "NOT_RECORDED"}}
    try:
        with cutoff_lock(receipt_root / "locks" / (cutoff.strftime("%Y%m%dT%H0000Z") + ".lock")) as acquired:
            if not acquired:
                end.update(status="DUPLICATE_IN_FLIGHT", classification="DUPLICATE_IN_FLIGHT")
                end["notification"].update(decision="DONT_NOTIFY", reasons=["another_attempt_owns_cutoff_lock"])
            else:
                prior = [attempt for attempt in attempts(receipt_root) if attempt["start"]["attempt_id"] != attempt_id]
                if any(attempt["start"]["plan_hash"] != digest(plan) for attempt in prior):
                    raise ValueError("prior_execution_reliability_plan_changed")
                previous_reports = _saved_reports(receipt_root, plan)
                same = [attempt for attempt in prior if attempt["start"]["input_cutoff"] == stamp(cutoff)
                        and (not attempt["end"] or attempt["end"]["status"] != "DUPLICATE_IN_FLIGHT")]
                existing = _hour(root, cutoff) / "forward_cycle_fixed.json"
                end["classification"] = ("DUPLICATE_VERIFY" if existing.is_file() else "RETRY" if same else "FIRST_ATTEMPT")
                end["runtime_verification"] = verify_runtime(root, plan)
                # The unchanged child chooses its own actual hour. Leave enough
                # budget, then fail if clocks drift; never force an old cutoff.
                before_child = now()
                if (before_child.replace(minute=0, second=0, microsecond=0) != cutoff
                        or before_child >= cutoff + timedelta(minutes=55)):
                    raise ValueError("current_hour_changed_or_insufficient_time_budget")
                originals = _originals(root, cutoff)
                end["child_started_at"] = stamp(now())
                child = _execute(root)
                end["child_ended_at"] = stamp(now())
                end["exit_code"] = child.returncode
                for name, value in (("stdout", child.stdout), ("stderr", child.stderr)):
                    path = directory / (name + ".txt")
                    with path.open("x", encoding="utf-8", newline="") as handle:
                        handle.write(value)
                    end[name + "_sha256"] = file_hash(path)
                end["original_bytes_preserved"] = all((root / name).is_file() and file_hash(root / name) == sha
                                                       for name, sha in originals.items())
                if end["original_bytes_preserved"] is not True:
                    raise ValueError("original_cycle_bytes_changed")
                if child.returncode:
                    raise ValueError("frozen_driver_failed")
                cycle = json.loads(child.stdout)
                if (cycle["status"] != "RECORDED_AND_REPLAYED" or cycle["cutoff"] != stamp(cutoff)
                        or cycle["observations"] != 2 or cycle["replays_verified"] != 2
                        or cycle["order_allowed"] is not False or cycle["automatic_backfill"] is not False):
                    raise ValueError("frozen_driver_contract_mismatch")
                projected = []
                for value in cycle["records"]:
                    item = next(item for item in plan["plans"] if item["plan_hash"] == value["plan_hash"])
                    path = Path(value["record"]).resolve()
                    if not path.is_relative_to(_hour(root, cutoff).resolve()):
                        raise ValueError("driver_record_outside_current_cycle")
                    projection = _record_projection(path, read(path), item, plan)
                    if projection["record_hash"] != value["record_hash"] or projection["backfill"]:
                        raise ValueError("driver_record_identity_or_backfill_invalid")
                    projected.append(projection)
                if len({item["plan_hash"] for item in projected}) != 2:
                    raise ValueError("driver_must_return_both_plans")
                end.update(status="RECORDED_AND_REPLAYED", records=projected, observations=2, replays_verified=2)
                prior_real = [attempt for attempt in prior if not attempt["end"]
                              or attempt["end"]["status"] != "DUPLICATE_IN_FLIGHT"]
                end["recovery"] = bool(prior_real and (not prior_real[-1]["end"] or prior_real[-1]["end"]["status"] == "FAILED"))
                reasons = []
                if any(item["timing_status"] == "LATE" for item in projected) and end["classification"] != "DUPLICATE_VERIFY":
                    reasons.append("late_observation")
                if end["recovery"]:
                    reasons.append("recovered_after_failed_or_unfinished_attempt")
                known_missing = {(row["cutoff"], row["plan_hash"])
                                 for prior_report in previous_reports
                                 for row in prior_report["rows"] if row["status"] == "MISSING"}
                known_missing.update((item["cutoff"], item["plan_hash"])
                                     for attempt in prior if attempt["end"]
                                     for item in attempt["end"].get("new_missing", []))
                end["new_missing"] = [{"cutoff": absence["cutoff"], "plan_hash": plan_hash}
                    for absence in cycle.get("prior_absences", [])
                    if timestamp(plan["start_cutoff"]) <= timestamp(absence["cutoff"]) < timestamp(plan["end_cutoff_exclusive"])
                    for plan_hash in absence["missing_plan_hashes"]
                    if (absence["cutoff"], plan_hash) not in known_missing]
                if end["new_missing"]:
                    reasons.append("new_missing_strategy_hours")
                end["notification"].update(decision="NOTIFY" if reasons else "DONT_NOTIFY", reasons=reasons)
    except Exception as exc:
        if isinstance(exc, subprocess.TimeoutExpired):
            end["child_ended_at"] = stamp(now())
        end["error"] = {"type": type(exc).__name__, "message": str(exc)[:400]}
        end["notification"].update(decision="NOTIFY", reasons=["capture_or_validation_failed"])
    end["actual_ended_at"] = stamp(now())
    end = seal(end, "receipt_hash")
    write_new(directory / "ended.json", end)
    return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "report"))
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--trigger-kind", choices=("SCHEDULED", "MANUAL"))
    parser.add_argument("--trigger-at")
    parser.add_argument("--scheduler-history", type=Path)
    args = parser.parse_args()
    root = args.runtime_root.resolve()
    plan = load_plan(args.plan)
    receipt_root = args.receipt_root or root / "forward/reliability"
    if args.command == "run":
        result = run(root, plan, receipt_root, trigger_kind=args.trigger_kind, trigger_at=args.trigger_at)
    else:
        result = report(root, plan, receipt_root, args.output_dir or receipt_root / "reports", args.scheduler_history)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    if result.get("status") == "FAILED" or result.get("validation_failures"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
