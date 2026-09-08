"""Replay every recorded study cell from a second installed environment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from hakimi_research.documents import digest, read_document
from hakimi_research.reporting import save_json_report


def replay(study_path: Path, snapshot: Path, output: Path):
    study = read_document(study_path)
    if study["planned_attempt_count"] != len(study["attempts"]):
        raise ValueError("incomplete_study")
    snapshot_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    receipts = []
    for attempt in study["attempts"]:
        report = Path(json.loads(attempt["stdout"])["full_report"])
        before = hashlib.sha256(report.read_bytes()).hexdigest()
        command = [sys.executable, "-B", str(Path(__file__).with_name("run_offline_cli.py")), "replay",
                   "--snapshot", str(snapshot), "--report", str(report), "--output-dir", str(output)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        if result["replay_verified"] is not True or result["result_matches"] is not True or result["source_matches"] is not True:
            raise ValueError("replay_not_verified")
        if hashlib.sha256(report.read_bytes()).hexdigest() != before:
            raise ValueError("original_report_modified")
        receipts.append({"strategy": attempt["strategy"], "cell": attempt["cell"], "cost_factor": attempt["cost_factor"],
                         "original_report": str(report), "original_file_sha256": before,
                         "receipt_path": result["receipt_path"], "receipt_hash": result["receipt_hash"],
                         "computation_matches": result["result_matches"], "source_matches": result["source_matches"],
                         "environment_verified": result["environment_verified"], "replay_verified": True})
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != snapshot_hash:
        raise ValueError("original_snapshot_modified")
    summary = {"schema_version": "descriptive-study-replay-v1", "status": "PASS", "count": len(receipts),
               "python": sys.executable, "snapshot_file_sha256": snapshot_hash, "snapshot_id": study["snapshot_id"],
               "receipts": receipts, "network_policy": "PYTHON_SOCKET_AUDIT_DENY", "originals_unchanged": True}
    path = save_json_report(summary, output, "study_replay", artifact_id=digest(summary))
    print(json.dumps({"receipt": str(path), "count": len(receipts), "status": "PASS"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    replay(args.study, args.snapshot, args.output_dir)
