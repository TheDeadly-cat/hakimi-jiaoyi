"""Rerun exact existing specs, compare recorded paths, and export review evidence.

Run with the accepted ordinary-wheel interpreter. Original files are read only;
network is denied by run_offline_cli.py. Public views are explicitly derived
documents, never relabelled or modified canonical reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from hakimi_research.documents import digest, read_document
from hakimi_research.experiment import verify_report
from hakimi_research.reporting import save_json_report


ROOT = Path(__file__).resolve().parents[1]
METRICS = ("total_return", "max_drawdown", "final_equity", "final_cash", "fill_count",
           "round_trip_count", "total_fees", "buy_fees", "sell_fees", "realized_pnl",
           "unrealized_pnl", "open_position_qty", "exposure_ratio")
EXPECTED_CELLS = {(strategy, "base", factor) for strategy in ("cash", "buy_and_hold", "dual_ma", "rsi")
                  for factor in (1, 2, 3)} | {
    ("dual_ma", "adjacent-18-54", 1), ("dual_ma", "adjacent-22-66", 1),
    ("rsi", "adjacent-13", 1), ("rsi", "adjacent-15", 1)}


def validate_study(study):
    attempts = study.get("attempts", [])
    if study.get("planned_attempt_count") != 16 or study.get("actual_attempt_count") != 16 or len(attempts) != 16:
        raise ValueError("complete_16_cell_study_required")
    keys, hashes = set(), set()
    for attempt in attempts:
        if type(attempt.get("cost_factor")) is not int or attempt.get("returncode") != 0:
            raise ValueError("successful_exact_cost_cells_required")
        key = (attempt.get("strategy"), attempt.get("cell"), attempt["cost_factor"])
        spec_hash = attempt.get("spec_hash")
        if key in keys or spec_hash in hashes or type(spec_hash) is not str or not re.fullmatch("[0-9a-f]{64}", spec_hash):
            raise ValueError("unique_cells_and_spec_hashes_required")
        keys.add(key)
        hashes.add(spec_hash)
    if keys != EXPECTED_CELLS:
        raise ValueError("original_16_cell_matrix_required")
    return attempts


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def report_path(attempt):
    return Path(json.loads(attempt["stdout"])["full_report"])


def run(command):
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return json.loads(completed.stdout)


def rerun(study_path, snapshot_path, output):
    original = read_document(study_path)
    validate_study(original)
    snapshot_hash = file_hash(snapshot_path)
    attempts, protected = [], {str(study_path): file_hash(study_path), str(snapshot_path): snapshot_hash}
    for attempt in original["attempts"]:
        old_path = report_path(attempt)
        protected[str(old_path)] = file_hash(old_path)
        old = verify_report(read_document(old_path))
        spec = read_document(attempt["spec_path"])
        protected[attempt["spec_path"]] = file_hash(attempt["spec_path"])
        if digest(spec) != attempt["spec_hash"] or spec != old["spec"]:
            raise ValueError("original_spec_identity_changed")
        local_spec = save_json_report(spec, output / "specs", "spec", artifact_id=digest(spec))
        result = run([sys.executable, "-B", str(ROOT / "tools/run_offline_cli.py"), "research",
                      "--snapshot", str(snapshot_path), "--spec", str(local_spec), "--output-dir", str(output)])
        attempts.append({**{k: attempt[k] for k in ("strategy", "cell", "cost_factor", "spec_hash")},
                         "spec_path": local_spec, "returncode": 0, "stdout": json.dumps(result), "stderr": "",
                         "original_report": str(old_path), "network_policy": "PYTHON_SOCKET_AUDIT_DENY"})
    if any(file_hash(path) != expected for path, expected in protected.items()):
        raise ValueError("an_original_input_was_modified")
    core = {"schema_version": "current-build-study-v1", "snapshot_id": original["snapshot_id"],
            "snapshot_file_sha256": snapshot_hash, "original_study_file_sha256": file_hash(study_path),
            "planned_attempt_count": 16, "actual_attempt_count": len(attempts), "attempts": attempts,
            "originals_unchanged": True, "specs_unchanged": True, "data_previously_viewed": True,
            "parameter_selection": False, "confirmation_evaluation": False,
            "live_allowed": False, "order_allowed": False}
    path = save_json_report(core, output, "study", artifact_id=digest(core))
    return {"study": path, "count": len(attempts)}


def changed_rows(before, after):
    """Retain complete differing records; equal final returns cannot hide paths."""
    return [{"index": index, "old": before[index] if index < len(before) else None,
             "current": after[index] if index < len(after) else None}
            for index in range(max(len(before), len(after)))
            if (before[index] if index < len(before) else None) != (after[index] if index < len(after) else None)]


def compare(old, current):
    if old["spec"] != current["spec"] or old["dataset"]["data_hash"] != current["dataset"]["data_hash"]:
        raise ValueError("cross_version_comparison_requires_identical_spec_and_data")
    before, after = old["result"], current["result"]
    changes = {name: changed_rows(before.get(name, []), after.get(name, []))
               for name in ("orders", "fills", "equity_curve", "return_series")}
    economic_fills = lambda result: [{key: fill.get(key) for key in (
        "action", "quantity", "price", "fee", "pnl", "fill_time", "cash_after", "position_after")}
        for fill in result.get("fills", [])]
    economic_changes = {"fills": changed_rows(economic_fills(before), economic_fills(after)),
                        "equity_curve": changes["equity_curve"], "return_series": changes["return_series"]}
    return {"old_report_hash": old["report_hash"], "current_report_hash": current["report_hash"],
            "old_result_hash": old["result_hash"], "current_result_hash": current["result_hash"],
            "old_source_sha256": old.get("provenance", {}).get("source_identity", {}).get("content_sha256"),
            "current_source_sha256": current.get("provenance", {}).get("source_identity", {}).get("content_sha256"),
            "old_execution_model": before.get("execution_model"), "current_execution_model": after.get("execution_model"),
            "same_spec_and_data": True,
            "metric_deltas": {name: after[name] - before[name] for name in METRICS},
            "changed_record_counts": {name: len(rows) for name, rows in changes.items()},
            "economic_path_changed": any(economic_changes.values()),
            "economic_changed_record_counts": {name: len(rows) for name, rows in economic_changes.items()},
            "changed_records": changes,
            "explanation": ("Recorded records differ; inspect event pairs and the separate economic-path flag against execution-model-v6 opening-protection rules."
                            if any(changes.values()) else
                            "No recorded order/fill/equity/return path changed in this cell. Source/model identity may still differ; this does not establish global version equivalence.")}


def projection(report):
    source = report["provenance"]["source_identity"]
    public_source = {k: source[k] for k in ("status", "content_sha256", "file_hashes") if k in source}
    if "build_receipt" in source:
        build = source["build_receipt"]
        public_source["build_receipt"] = {k: build[k] for k in (
            "schema_version", "content_sha256", "file_hashes", "build_definition_sha256") if k in build}
        public_source["build_receipt"]["git"] = {k: build.get("git", {}).get(k) for k in ("commit", "status")}
    # Select data values explicitly, excluding local Git/path/machine receipts.
    return {"schema_version": "research-review-projection-v1", "source_report_hash": report["report_hash"],
            "result_hash": report["result_hash"], "computation_id": report["computation_id"],
            "spec": report["spec"], "spec_hash": report["spec_hash"], "dataset": report["dataset"],
            "metrics": {name: report["result"][name] for name in METRICS},
            "execution_model": report["result"].get("execution_model"),
            "fills": report["result"]["fills"], "orders": report["result"].get("orders", []),
            "source_identity": public_source,
            "environment_verified": report["evidence"]["environment_verified"],
            "execution_permission": report["execution_permission"],
            "scope": "Derived review projection. Canonical full report and raw snapshot are preserved locally under their original hashes."}


def export(study_path, snapshot_path, replay_path, output):
    study, replay = read_document(study_path), read_document(replay_path)
    attempts = validate_study(study)
    if replay["status"] != "PASS" or replay["count"] != 16 or replay["snapshot_id"] != study["snapshot_id"]:
        raise ValueError("matching_complete_second_environment_replay_required")
    expected_hashes = {file_hash(report_path(attempt)) for attempt in attempts}
    receipt_index = {row["original_file_sha256"]: row for row in replay["receipts"]}
    if (len(expected_hashes) != 16 or len(replay["receipts"]) != 16
            or set(receipt_index) != expected_hashes or replay.get("originals_unchanged") is not True):
        raise ValueError("exact_16_report_replay_set_required")
    rows = []
    for attempt in study["attempts"]:
        path = report_path(attempt)
        current, old = verify_report(read_document(path)), verify_report(read_document(attempt["original_report"]))
        if current["spec_hash"] != attempt["spec_hash"]:
            raise ValueError("study_report_spec_mismatch")
        receipt = receipt_index[file_hash(path)]
        if not all(receipt[k] is True for k in ("computation_matches", "source_matches", "environment_verified", "replay_verified")):
            raise ValueError("same_version_replay_not_verified")
        canonical_receipt = read_document(receipt["receipt_path"])
        receipt_core = {key: value for key, value in canonical_receipt.items() if key != "receipt_hash"}
        if (digest(receipt_core) != receipt["receipt_hash"]
                or canonical_receipt["receipt_hash"] != receipt["receipt_hash"]
                or canonical_receipt["original_report_hash"] != current["report_hash"]
                or canonical_receipt["original_result_hash"] != current["result_hash"]
                or canonical_receipt["replayed_result_hash"] != current["result_hash"]
                or canonical_receipt["snapshot_id"] != study["snapshot_id"]
                or not all(canonical_receipt[key] is True for key in (
                    "result_matches", "source_matches", "environment_verified", "replay_verified"))):
            raise ValueError("canonical_replay_receipt_mismatch")
        ledger = run([sys.executable, "-B", str(ROOT / "scripts/reconcile_research_ledger.py"),
                      "--report", str(path), "--snapshot", str(snapshot_path)])
        if ledger["status"] != "PASS":
            raise ValueError("ledger_reconciliation_failed")
        view = projection(current)
        view["ledger_reconciliation"] = ledger
        view["reconciliation_script_sha256"] = file_hash(ROOT / "scripts/reconcile_research_ledger.py")
        view["same_version_replay"] = {k: receipt[k] for k in (
            "original_file_sha256", "receipt_hash", "computation_matches", "source_matches", "environment_verified", "replay_verified")}
        view["cross_version_comparison"] = compare(old, current)
        published = save_json_report(view, output / "cells", "cell", artifact_id=digest(view))
        rows.append({**{k: attempt[k] for k in ("strategy", "cell", "cost_factor", "spec_hash")},
                     "review_file": "cells/" + Path(published).name, "review_sha256": file_hash(published),
                     "report_hash": current["report_hash"], **view["metrics"],
                     "changed_record_counts": view["cross_version_comparison"]["changed_record_counts"],
                     "ledger_checks": ledger["checks"], "ledger_status": ledger["status"], "replay_verified": True})
    result = {"schema_version": "current-build-study-review-v1", "snapshot_id": study["snapshot_id"],
              "snapshot_file_sha256": file_hash(snapshot_path), "cell_count": len(rows), "rows": rows,
              "original_specs_and_snapshot_unchanged": True, "data_previously_viewed": True,
              "source_change": "Opening protection precedes pending signals; no same-bar reentry after such protection; opening targets precede ambiguous intrabar ranges.",
              "limitations": ["One previously viewed month; 16 dependent cells, not16 independent market observations.",
                              "Public projections omit raw provider data and local machine paths; hashes link retained canonical originals.",
                              "Arithmetic reconciliation does not establish correct event ordering; separate numeric event regressions cover that property."]}
    destination = save_json_report(result, output, "review", artifact_id=digest(result))
    return {"review": destination, "count": len(rows), "ledger_checks": sum(row["ledger_checks"] for row in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rerun", "export"))
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export" and args.replay is None:
        parser.error("export requires --replay")
    answer = rerun(args.study, args.snapshot, args.output_dir) if args.command == "rerun" else export(
        args.study, args.snapshot, args.replay, args.output_dir)
    print(json.dumps(answer, ensure_ascii=False))
