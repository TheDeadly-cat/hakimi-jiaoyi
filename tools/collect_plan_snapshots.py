"""Explicitly capture each predeclared BTC spot window; preserve failed attempts."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import io
import json
from pathlib import Path
import re

from collect_btc_snapshot import collect
from hakimi_research.dataset_registry import load_snapshot
from hakimi_research.documents import digest, read_document
from hakimi_research.reporting import save_json_report


def collect_plan(plan_path, output):
    plan = read_document(plan_path)
    if plan.get("parameter_selection") is not False or plan.get("context_hours") != 72:
        raise ValueError("fixed_72_hour_context_plan_required")
    plan_hash = digest(plan)
    receipts = []
    frozen = {"plan": plan, "plan_sha256": plan_hash,
              "plan_file_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
              "collector_sha256": hashlib.sha256(Path(__file__).with_name("collect_btc_snapshot.py").read_bytes()).hexdigest()}
    save_json_report(frozen, output, "frozen_capture_plan", artifact_id=plan_hash)
    for window in plan["windows"]:
        label = window["window_id"]
        if type(label) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", label) is None:
            raise ValueError("window_id_must_be_a_single_portable_directory_name")
        directory = output / label
        start = (datetime.fromisoformat(window["score_start"].replace("Z", "+00:00")) - timedelta(hours=72)).isoformat().replace("+00:00", "Z")
        end = window["score_end"]
        prior = sorted((directory / "datasets").glob("dataset_*.json")) if (directory / "datasets").exists() else []
        if prior:
            admitted = [path for path in prior if load_snapshot(path).document["start"] == start
                        and load_snapshot(path).document["end_exclusive"] == end]
            if len(admitted) != 1:
                raise ValueError("existing_window_snapshots_ambiguous")
            snapshot = load_snapshot(admitted[0])
            receipt = {"window": label, "status": "REUSED_VERIFIED", "snapshot": str(admitted[0]),
                       "snapshot_id": snapshot.snapshot_id, "quality": snapshot.document["quality"]}
        else:
            buffer = io.StringIO()
            receipt = {"window": label, "start": start, "end_exclusive": end,
                       "started_at": datetime.now(timezone.utc).isoformat()}
            try:
                with redirect_stdout(buffer):
                    collect(start, end, directory)
                receipt.update(json.loads(buffer.getvalue()), status="CAPTURED")
            except Exception as error:
                receipt.update(status="FAILED", error_type=type(error).__name__, error=str(error))
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            save_json_report(receipt, directory / "attempts", "capture_attempt", artifact_id=digest(receipt))
        receipts.append(receipt)
        print(json.dumps({"window": label, "status": receipt["status"], "quality": receipt.get("quality"),
                          "error": receipt.get("error")}), flush=True)
    result = {"schema_version": "planned-public-capture-v1", "plan_sha256": plan_hash,
              "window_count": len(receipts), "receipts": receipts,
              "all_windows_admitted": all(row["status"] != "FAILED" for row in receipts)}
    saved = save_json_report(result, output, "capture_index", artifact_id=digest(result))
    print(json.dumps({"index": saved, "all_windows_admitted": result["all_windows_admitted"]}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    result = collect_plan(arguments.plan, arguments.output_dir)
    raise SystemExit(0 if result["all_windows_admitted"] else 1)
