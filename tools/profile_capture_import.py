"""Time canonical raw-capture import in a fresh offline process."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("capture_import_profile_network_access_denied")


def profile(capture_path, expected_snapshot_path, output):
    started = time.perf_counter()
    registry = importlib.import_module("hakimi_research.dataset_registry")
    documents = importlib.import_module("hakimi_research.documents")
    reporting = importlib.import_module("hakimi_research.reporting")
    imports = time.perf_counter() - started
    before_hash = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    started = time.perf_counter()
    snapshot = registry.import_capture(capture_path)
    import_seconds = time.perf_counter() - started
    started = time.perf_counter()
    saved = registry.save_snapshot(snapshot, output / "datasets")
    save_seconds = time.perf_counter() - started
    expected = registry.load_snapshot(expected_snapshot_path)
    if snapshot.snapshot_id != expected.snapshot_id or snapshot.document["data_hash"] != expected.document["data_hash"]:
        raise ValueError("canonical_capture_import_changed_snapshot")
    if hashlib.sha256(capture_path.read_bytes()).hexdigest() != before_hash:
        raise ValueError("original_capture_modified")
    environment = importlib.import_module("hakimi_research.environment").build_runtime_provenance()
    receipt = {"schema_version": "capture-import-profile-v1",
               "capture_file_sha256": before_hash, "snapshot_id": snapshot.snapshot_id,
               "data_hash": snapshot.document["data_hash"], "evidence_kind": snapshot.document["evidence_kind"],
               "input_rows": len(snapshot.document["candles"]), "quality": snapshot.document["quality"],
               "timings": {"import_modules_seconds": imports, "canonical_capture_read_parse_import_seconds": import_seconds,
                           "canonical_snapshot_verify_serialize_save_seconds": save_seconds},
               "snapshot_matches_original": True, "original_capture_unchanged": True,
               "source_identity": environment["source_identity"], "environment_verified": environment["environment_verified"],
               "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "network_policy": "PYTHON_SOCKET_AUDIT_DENY", "optimization_applied": False,
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False,
               "measurement_limits": ["Fresh-process raw capture import measurement; generation or network acquisition of the capture is excluded.",
                                      "Snapshot identity checks against the original occur after the measured import/save stages.",
                                      "Normal canonical input validation and publication checks remain enabled; this sample makes no cross-platform throughput claim."]}
    path = reporting.save_json_report(receipt, output, "capture_import_profile", artifact_id=documents.digest(receipt))
    return {"profile": path, "snapshot": str(saved), "snapshot_matches_original": True, "timings": receipt["timings"]}


if __name__ == "__main__":
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--expected-snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(profile(args.capture, args.expected_snapshot, args.output_dir), ensure_ascii=False))
