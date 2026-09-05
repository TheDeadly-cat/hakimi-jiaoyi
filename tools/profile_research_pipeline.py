"""Measure the complete installed offline pipeline without changing decisions."""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import importlib
import json
from pathlib import Path
import platform
import pstats
import sys
import time


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("offline_profile_network_access_denied")


def profile(snapshot_path, spec_path, output, *, hotspots=False):
    timings = {}
    started = time.perf_counter()

    def measure(name, function):
        before = time.perf_counter()
        result = function()
        timings[name] = time.perf_counter() - before
        return result

    def import_runtime():
        return {key: importlib.import_module("hakimi_research." + key)
                for key in ("dataset_registry", "documents", "experiment", "reporting")}

    modules = measure("import_runtime_seconds", import_runtime)
    documents, experiments = modules["documents"], modules["experiment"]
    snapshot_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    spec_hash = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    snapshot = measure("snapshot_read_parse_verify_seconds", lambda: modules["dataset_registry"].load_snapshot(snapshot_path))
    spec = measure("spec_read_parse_validate_seconds", lambda: experiments.ExperimentSpec.load(spec_path))
    profiler = cProfile.Profile() if hotspots else None

    def execute():
        if profiler:
            profiler.enable()
        try:
            return experiments.ExperimentRunner().run(snapshot, spec)
        finally:
            if profiler:
                profiler.disable()

    report = measure("research_execution_inclusive_seconds", execute)
    encoded = measure("report_serialization_seconds", lambda: documents.canonical_bytes(report.document))
    saved = measure("report_verify_serialize_atomic_save_seconds", lambda: report.save(output / "reports"))
    original = measure("saved_report_read_verify_seconds", lambda: experiments.verify_report(documents.read_document(saved)))
    replay = measure("canonical_replay_inclusive_seconds", lambda: experiments.replay_report(snapshot, experiments.ResearchReport(original)))
    receipt_path = measure("replay_receipt_save_seconds", lambda: modules["reporting"].save_json_report(
        replay, output / "receipts", "replay", artifact_id=replay["receipt_hash"]))
    elapsed = time.perf_counter() - started
    if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != snapshot_hash or hashlib.sha256(spec_path.read_bytes()).hexdigest() != spec_hash:
        raise ValueError("profiling_modified_original_input")
    if documents.canonical_bytes(documents.read_document(saved)) != encoded:
        raise ValueError("serialized_saved_report_differs")
    calls = []
    if profiler:
        stats = pstats.Stats(profiler)
        for (filename, lineno, name), (primitive, total, own, cumulative, _) in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:20]:
            calls.append({"module_file": Path(filename).name, "line": lineno, "function": name,
                          "primitive_calls": primitive, "total_calls": total,
                          "own_seconds": own, "cumulative_seconds": cumulative})
    core = {"schema_version": "research-pipeline-profile-v1", "timings": timings,
            "total_observed_seconds": elapsed, "timed_stage_sum_seconds": sum(timings.values()),
            "snapshot_id": snapshot.snapshot_id, "snapshot_file_sha256": snapshot_hash,
            "spec_hash": report.document["spec_hash"], "spec_file_sha256": spec_hash,
            "report_hash": report.document["report_hash"], "serialized_report_bytes": len(encoded),
            "source_identity": report.document["evidence"]["source_identity"],
            "environment_verified": report.document["evidence"]["environment_verified"],
            "execution_model": report.document["result"]["execution_model"],
            "scored_bar_count": len(report.document["result"]["return_series"]),
            "python_version": platform.python_version(), "platform": platform.system(),
            "profile_instrumentation_enabled": hotspots, "execution_hotspots": calls,
            "decisions_and_results_exact": replay["result_matches"],
            "source_matches": replay["source_matches"], "environment_matches": replay["environment_verified"],
            "replay_verified": replay["replay_verified"], "receipt_hash": replay["receipt_hash"],
            "receipt_file": Path(receipt_path).name,
            "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "optimization_applied": False, "network_policy": "PYTHON_SOCKET_AUDIT_DENY",
            "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False,
            "measurement_limits": [
                "Run this command in a fresh process for cold-import timing; repeat commands for independent timing samples.",
                "Canonical runner time includes its own repeated snapshot checks, frame construction, execution and provenance; no validation was bypassed.",
                "Canonical save verifies and serializes again; serialization is separately measured rather than removed from the production path.",
                "Canonical replay includes report verification and another complete runner invocation; inner cumulative hotspot times overlap and must not be summed.",
                "Optional cProfile instrumented execution time is not comparable to uninstrumented throughput.",
                "No isolated load or cross-platform performance promise; timing samples do not prove optimization gains.",
                "Exact result identity includes complete orders, fills, signals and equity. No floating tolerance or threshold rule changed."]}
    identity = documents.digest(core)
    path = modules["reporting"].save_json_report(core, output, "pipeline_profile", artifact_id=identity)
    return {"profile": path, "report": str(saved), "replay_verified": replay["replay_verified"], "timings": timings}


if __name__ == "__main__":
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--hotspots", action="store_true", help="Instrument the execution stage with cProfile; timing overhead is disclosed.")
    args = parser.parse_args()
    result = profile(args.snapshot, args.spec, args.output_dir, hotspots=args.hotspots)
    print(json.dumps(result, ensure_ascii=False))
