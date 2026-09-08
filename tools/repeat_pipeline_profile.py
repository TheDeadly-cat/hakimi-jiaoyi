"""Six predeclared measurements of the unchanged accepted offline pipeline.

Three children measure fresh Python module imports. One further child imports
the runtime once and measures three sequential warm-import calls. No operating
system file cache is cleared, and no runtime validation or calculation changes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

SOURCE = "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5"
WHEEL = "b93952ddee0d16424292e75e5a3e7b0dfe10ac06d12f1333fa276922d08649fb"
MODULES = ("dataset_registry", "documents", "experiment", "reporting")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)


def no_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("repeat_profile_offline_network_denied")


def check_runtime():
    # Called only by the orchestrator, or after a cold sample has finished.
    from hakimi_research.environment import build_runtime_provenance
    provenance = build_runtime_provenance()
    if (provenance["source_identity"].get("status") != "BUILD_VERIFIED"
            or provenance["source_identity"].get("content_sha256") != SOURCE
            or provenance["environment_verified"].get("status") != "VERIFIED"):
        raise ValueError("accepted_021_runtime_and_dependencies_required")
    return provenance


def freeze(root, public):
    provenance = check_runtime()
    plan_path = public / "plan.json"
    if plan_path.exists():
        plan = validate_plan(root, plan_path)
        return {"plan": str(plan_path), "plan_hash": digest(plan), "existing_plan_preserved": True}
    old = read(next((root / "artifacts/multiwindow-study-ci33969915599").glob("multiwindow_run_*.json")))
    attempt = next(a for a in old["attempts"] if a["window_id"] == "2025-Q4" and a["method"] == "dual_ma" and a["cost_factor"] == 1)
    report = read(attempt["report_path"])
    snapshot_path, spec_path = Path(attempt["snapshot_path"]), Path(attempt["spec_path"])
    snapshot, spec = read(snapshot_path), read(spec_path)
    assert report["evidence"]["source_identity"]["content_sha256"] == SOURCE
    assert len(snapshot["candles"]) == 2280 and report["result"]["scoring"]["scored_bar_count"] == 2208
    plan = {"schema_version": "repeat-pipeline-profile-plan-v1",
            "frozen_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "planned_samples": 6, "cold_import_samples": 3, "warm_import_samples": 3,
            "matrix": ["COLD_IMPORT_FRESH_PROCESS"] * 3 + ["WARM_IMPORT_SAME_PROCESS"] * 3,
            "warmup_policy": "IMPORT_RUNTIME_MODULES_ONCE_BEFORE_THREE_SEQUENTIAL_SAMPLES_NO_UNRECORDED_FULL_PIPELINE_WARMUP",
            "method": "dual_ma", "cost_factor": 1, "window_id": "2025-Q4",
            "snapshot_relative_path": snapshot_path.relative_to(root).as_posix(), "snapshot_file_sha256": sha(snapshot_path),
            "snapshot_id": snapshot["snapshot_id"], "data_hash": snapshot["data_hash"],
            "spec_relative_path": spec_path.relative_to(root).as_posix(), "spec_file_sha256": sha(spec_path),
            "spec_hash": report["spec_hash"], "spec": spec, "expected_result_hash": report["result_hash"],
            "input_hours": 2280, "scored_hours": 2208,
            "source_content_sha256": SOURCE, "accepted_windows_wheel_sha256": WHEEL,
            "accepted_ci_run": 33969915599, "source_identity": provenance["source_identity"],
            "environment_verified": provenance["environment_verified"],
            "profile_tool_sha256": sha(root / "tools/profile_research_pipeline.py"),
            "repeat_tool_sha256": sha(Path(__file__)),
            "optimization_applied": False, "runtime_cache_added": False,
            "os_page_cache_cleared": False, "ordinary_os_and_desktop_load_isolated": False,
            "speedup_comparison": "NONE_BASELINE_DISTRIBUTION_ONLY",
            "selection_policy": "RETAIN_ALL_SIX_SAMPLES_REPORT_N_MEDIAN_MIN_MAX_NEVER_SELECT_FASTEST",
            "paper_allowed": False, "live_allowed": False, "order_allowed": False, "research_only": True}
    write_new(plan_path, plan)
    write_new(public / "plan-freeze.json", {"plan_hash": digest(plan), "plan_file_sha256": sha(plan_path),
        "frozen_at": plan["frozen_at"], "sample_results_existed": False})
    return {"plan": str(plan_path), "plan_hash": digest(plan), "frozen_at": plan["frozen_at"]}


def validate_plan(root, plan_path):
    plan = read(plan_path)
    receipt = read(plan_path.parent / "plan-freeze.json")
    if receipt["plan_hash"] != digest(plan) or receipt["plan_file_sha256"] != sha(plan_path) or receipt["sample_results_existed"] is not False:
        raise ValueError("repeat_profile_frozen_plan_changed")
    if (plan["schema_version"] != "repeat-pipeline-profile-plan-v1" or plan["planned_samples"] != 6
            or plan["cold_import_samples"] != 3 or plan["warm_import_samples"] != 3
            or plan["source_content_sha256"] != SOURCE or plan["optimization_applied"] is not False
            or plan["repeat_tool_sha256"] != sha(Path(__file__))):
        raise ValueError("fixed_six_sample_unchanged_tool_plan_required")
    for key in ("snapshot", "spec"):
        if sha(root / plan[key + "_relative_path"]) != plan[key + "_file_sha256"]:
            raise ValueError("repeat_profile_input_changed")
    if sha(root / "tools/profile_research_pipeline.py") != plan["profile_tool_sha256"]:
        raise ValueError("canonical_profile_tool_changed")
    return plan


def load_profile(root):
    spec = importlib.util.spec_from_file_location("unchanged_canonical_pipeline_profile", root / "tools/profile_research_pipeline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(root, plan_path, local, public, mode, start_index):
    # All code before profile() on the cold path is standard library only.
    plan = validate_plan(root, plan_path)
    profiler = load_profile(root)
    count = 1 if mode == "COLD_IMPORT_FRESH_PROCESS" else 3
    imported_before_preload = any(name.startswith("hakimi_research") for name in sys.modules)
    if imported_before_preload:
        raise ValueError("fresh_worker_must_not_preimport_research_runtime")
    if mode == "WARM_IMPORT_SAME_PROCESS":
        for name in MODULES:
            importlib.import_module("hakimi_research." + name)
    rows = []
    for offset in range(count):
        index = start_index + offset
        before = {name: "hakimi_research." + name in sys.modules for name in MODULES}
        if (any(before.values()) if mode == "COLD_IMPORT_FRESH_PROCESS" else not all(before.values())):
            raise ValueError("declared_module_cache_state_mismatch")
        started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        outcome = profiler.profile(root / plan["snapshot_relative_path"], root / plan["spec_relative_path"], local / f"sample-{index}")
        ended = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        profile_path = Path(outcome["profile"])
        profile = read(profile_path)
        report = read(outcome["report"])
        replay_path = local / f"sample-{index}" / "receipts" / profile["receipt_file"]
        replay = read(replay_path)
        if (not all(profile[k] for k in ("decisions_and_results_exact", "source_matches", "environment_matches", "replay_verified"))
                or profile["source_identity"]["content_sha256"] != SOURCE
                or profile["environment_verified"] != plan["environment_verified"]
                or report["result_hash"] != plan["expected_result_hash"]
                or replay["original_result_hash"] != replay["replayed_result_hash"]
                or replay["original_result_hash"] != plan["expected_result_hash"]
                or profile["snapshot_file_sha256"] != plan["snapshot_file_sha256"]
                or profile["spec_file_sha256"] != plan["spec_file_sha256"]):
            raise ValueError("sample_exact_identity_or_replay_mismatch")
        destination = public / profile_path.name
        with destination.open("xb") as stream:
            stream.write(profile_path.read_bytes())
        record = {"sample_index": index, "mode": mode, "process_id": os.getpid(), "modules_loaded_before": before,
                  "started_at": started, "ended_at": ended, "profile_file": destination.name,
                  "profile_file_sha256": sha(destination), "profile": profile,
                  "canonical_result_hash": report["result_hash"], "report_file_sha256": sha(outcome["report"]),
                  "replay_receipt_hash": replay["receipt_hash"], "replay_receipt_file_sha256": sha(replay_path),
                  "exact_replay_verified": True}
        write_new(public / f"sample-{index}.json", record)
        rows.append(record)
    return {"worker_process_id": os.getpid(), "completed_samples": len(rows), "sample_indices": [r["sample_index"] for r in rows]}


def process_observation():
    """Only count Python processes and IDs; do not publish their command lines."""
    if os.name != "nt":
        return {"status": "UNAVAILABLE_NON_WINDOWS", "python_processes": None}
    command = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe' } | Select-Object ProcessId,ParentProcessId,Name) | ConvertTo-Json -Compress"
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True,
                            encoding="utf-8", timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        return {"status": "PROCESS_OBSERVATION_FAILED", "python_processes": None}
    values = json.loads(result.stdout or "[]")
    if type(values) is dict:
        values = [values]
    return {"status": "OBSERVED", "python_processes": values, "measurement_orchestrator_process_id": os.getpid()}


def run(root, public, research_load_status):
    plan_path = public / "plan.json"
    plan = validate_plan(root, plan_path)
    check_runtime()
    if (public / "summary.json").exists():
        summary = read(public / "summary.json")
        if summary["plan_hash"] != digest(plan) or summary["completed_samples"] != 6:
            raise ValueError("completed_profile_summary_mismatch")
        return {"summary": str(public / "summary.json"), "existing_measurements_preserved": True}
    if list(public.glob("sample-*.json")) or (public / "run-started.json").exists():
        raise ValueError("partial_measurement_group_retained_do_not_silently_resample")
    local = Path(tempfile.mkdtemp(prefix="hakimi-repeat-profile-20260906-"))
    start_observation = process_observation()
    write_new(public / "run-started.json", {"plan_hash": digest(plan), "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "research_load_status": research_load_status, "process_observation": start_observation})
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONUTF8"], environment["PYTHONIOENCODING"] = "1", "utf-8"
    workers = []
    for mode, index in [("COLD_IMPORT_FRESH_PROCESS", 1), ("COLD_IMPORT_FRESH_PROCESS", 2), ("COLD_IMPORT_FRESH_PROCESS", 3), ("WARM_IMPORT_SAME_PROCESS", 4)]:
        print(json.dumps({"event": "WORKER_STARTED", "mode": mode, "first_sample": index}), flush=True)
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "worker", "--root", str(root),
                   "--public", str(public.resolve()), "--local", str(local), "--mode", mode, "--start-index", str(index)]
        child = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        if child.returncode:
            write_new(public / f"worker-failed-{index}.json", {"first_sample": index, "mode": mode,
                "exit_code": child.returncode, "error_type": "WORKER_FAILED_SEE_LOCAL_COMMAND_OUTPUT", "no_resampling": True})
            raise RuntimeError("measurement_worker_failed:" + child.stderr[-3000:])
        workers.append(json.loads(child.stdout))
        print(json.dumps({"event": "WORKER_COMPLETED", **workers[-1]}), flush=True)
    records = [read(public / f"sample-{index}.json") for index in range(1, 7)]
    cold, warm = records[:3], records[3:]
    if len({r["process_id"] for r in cold}) != 3 or len({r["process_id"] for r in warm}) != 1:
        raise ValueError("cold_and_warm_process_grouping_invalid")
    groups = []
    for label, samples in [("COLD_IMPORT_FRESH_PROCESS", cold), ("WARM_IMPORT_SAME_PROCESS", warm)]:
        fields = ["total_observed_seconds", *samples[0]["profile"]["timings"]]
        metrics = {}
        for field in fields:
            values = [r["profile"][field] if field == "total_observed_seconds" else r["profile"]["timings"][field] for r in samples]
            metrics[field] = {"n": len(values), "median": statistics.median(values), "minimum": min(values), "maximum": max(values), "all_samples": values}
        groups.append({"mode": label, "n": 3, "metrics": metrics})
    summary = {"schema_version": "repeat-pipeline-profile-summary-v1", "plan_hash": digest(plan),
               "status": "PASS", "completed_samples": 6, "exact_replays_verified": 6, "groups": groups,
               "sample_files": [f"sample-{i}.json" for i in range(1, 7)],
               "sample_file_sha256": {f"sample-{i}.json": sha(public / f"sample-{i}.json") for i in range(1, 7)},
               "source_content_sha256": SOURCE, "snapshot_id": plan["snapshot_id"], "spec_hash": plan["spec_hash"],
               "environment_verified": plan["environment_verified"], "canonical_result_hash": plan["expected_result_hash"],
               "research_load_status": research_load_status, "process_observation_before": start_observation,
               "process_observation_after": process_observation(), "optimization_applied": False,
               "runtime_cache_added": False, "os_page_cache_cleared": False,
               "ordinary_os_and_desktop_load_isolated": False, "speedup_comparison": "NONE_BASELINE_DISTRIBUTION_ONLY",
               "measurement_limits": ["Cold refers only to fresh Python runtime module import, never cleared OS file cache.",
                   "Warm means three sequential profiles in one process after explicit runtime import; no discarded full-pipeline warmup sample.",
                   "All samples include full validation, canonical execution, persistence and full replay with exact computation identity.",
                   "This is one-machine baseline variability, not a cold-vs-warm causal speedup or optimized-vs-original comparison.",
                   "Ordinary desktop/OS load is not isolated; process inventory cannot prove hardware isolation."],
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    write_new(public / "summary.json", summary)
    return {"summary": str(public / "summary.json"), "completed_samples": 6, "exact_replays": 6,
            "local_full_reports_retained": str(local)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["freeze", "run", "worker"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--local", type=Path)
    parser.add_argument("--mode", choices=["COLD_IMPORT_FRESH_PROCESS", "WARM_IMPORT_SAME_PROCESS"])
    parser.add_argument("--start-index", type=int)
    parser.add_argument("--research-load-status", choices=["OTHER_RESEARCH_PROCESSES_CONFIRMED_TERMINAL", "PARALLEL_RESEARCH_LOAD_NOT_ISOLATED"])
    args = parser.parse_args()
    sys.addaudithook(no_network)
    if args.phase == "freeze":
        result = freeze(args.root.resolve(), args.public)
    elif args.phase == "worker":
        result = worker(args.root.resolve(), args.public / "plan.json", args.local, args.public, args.mode, args.start_index)
    else:
        if args.research_load_status is None:
            parser.error("run requires --research-load-status")
        result = run(args.root.resolve(), args.public, args.research_load_status)
    print(json.dumps(result, ensure_ascii=False), flush=True)
