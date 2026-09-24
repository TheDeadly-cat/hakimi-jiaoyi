"""Execute the already-frozen ten-event C/D development study entirely offline."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_dataset import EquitySnapshot
from hakimi_research.equity_events import save_equity_event
from hakimi_research.equity_research import verify_equity_report
from scripts.reconcile_research_ledger import reconcile
from tools.equity_content_protocol import validate_approval
from tools.equity_content_study import FROZEN_PROTOCOL_HASH, event_context, replay_cell, run_cell, tool_identity
from tools.verify_announcement_review import recheck


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def run(args):
    for original_root in (args.original_root, args.source_root, args.packet.parent):
        if args.output.resolve().is_relative_to(original_root.resolve()):
            raise ValueError("content_output_must_be_separate_from_originals")
    protocol = read(args.protocol)
    if protocol["protocol_hash"] != FROZEN_PROTOCOL_HASH or digest({k: v for k, v in protocol.items() if k != "protocol_hash"}) != FROZEN_PROTOCOL_HASH:
        raise ValueError("content_original_frozen_protocol_changed")
    packet, approval, study = read(args.packet), read(args.approval), read(args.study)
    if packet["packet_hash"] != protocol["candidate_packet_hash"] or len(validate_approval(packet, approval)) != 10:
        raise ValueError("content_original_ten_reviewed_rows_required")
    source_review = recheck(args.packet, args.source_root, approval)
    if len(study["events"]) != 10 or len(packet["events"]) != 10:
        raise ValueError("content_original_ten_events_required")
    for old, frozen in zip(study["events"], protocol["windows"]):
        if any(old[k] != frozen[k] for k in ("fiscal_quarter", "event_id", "score_start", "score_end", "snapshot_start", "status")):
            raise ValueError("content_window_or_exclusion_changed")
    texts = {c["plain_text_sha256"]: (args.packet.parent / (c["fiscal_quarter"] + ".txt")).read_text(encoding="utf-8")
             for c in packet["events"]}
    # Preserve the full original report/snapshot population, not just new inputs.
    original_files = [args.packet, args.approval, args.protocol, args.study]
    original_files += list(args.source_root.glob("*")) + list(args.packet.parent.glob("*"))
    report_paths = {}
    for phase in ("actual-study-first", "actual-study-final"):
        files = list((args.original_root / phase).rglob("*.json"))
        original_files += files
        for path in files:
            if path.name.startswith("equity_research_"):
                identity = path.stem.removeprefix("equity_research_")
                if identity in report_paths:
                    raise ValueError("content_duplicate_original_report")
                report_paths[identity] = path
    before = {str(p.resolve()): sha(p) for p in original_files if p.is_file()}
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "inputs-before.private.json", before)
    write(args.output / "source-recheck.private.json", source_review)
    # New canonical event ledger: old candidate and HTML bytes stay unchanged.
    for candidate in packet["events"]:
        context = event_context(packet, approval, texts, event_id=candidate["event_id"])
        for event in context["events"]:
            save_equity_event(event, args.output / "events")
    cells, excluded = [], []
    for old in study["events"]:
        quarter = old["fiscal_quarter"]
        if old["status"] != "COMPLETED":
            excluded.append({"fiscal_quarter": quarter, "status": old["status"], "economic_reports": 0})
            continue
        candidate = next(c for c in packet["events"] if c["fiscal_quarter"] == quarter)
        for old_cell in old["cells"]:
            original_path = report_paths[old_cell["report_hashes"]["A"]]
            original = verify_equity_report(read(original_path))
            snapshot_path = original_path.parents[2] / "snapshot" / ("equity_dataset_" + original["dataset"]["snapshot_id"] + ".json")
            snapshot = EquitySnapshot(read(snapshot_path))
            spec = original["spec"]
            if (spec["score_start_session"], spec["score_end_session"]) != (old["score_start"], old["score_end"]):
                raise ValueError("content_reference_scoring_changed")
            reports = {}
            directory = args.output / quarter / ("cost-" + str(old_cell["cost_multiplier"]))
            for variant in ("C", "D"):
                report = run_cell(snapshot, spec, packet, approval, texts, event_id=candidate["event_id"], variant=variant)
                replay = replay_cell(report, snapshot, spec, packet, approval, texts)
                ledger = reconcile(report, snapshot.document)
                if not replay["replay_verified"] or ledger["status"] != "PASS":
                    raise ValueError("content_replay_or_independent_ledger_failed")
                write(directory / variant / ("content_research_" + report["report_hash"] + ".json"), report)
                write(directory / variant / "replay.private.json", replay)
                write(directory / variant / "ledger.private.json", ledger)
                reports[variant] = report
            disabled = run_cell(snapshot, spec, packet, approval, texts, event_id=candidate["event_id"], variant="D_DISABLED")
            equal = canonical_bytes(disabled["result"]) == canonical_bytes(reports["C"]["result"])
            if not equal:
                raise ValueError("content_disabled_D_not_byte_identical_C")
            write(directory / "disabled-content.private.json", {"disabled_result_hash": disabled["result_hash"],
                "C_result_hash": reports["C"]["result_hash"], "byte_identical": equal})
            metrics = ("total_return", "final_equity", "max_drawdown", "total_fees", "fill_count", "round_trip_count",
                       "exposure_ratio", "realized_pnl", "unrealized_pnl", "open_position_qty", "ambiguous_intrabar_count")
            result = {"fiscal_quarter": quarter, "cost_multiplier": old_cell["cost_multiplier"],
                "snapshot_id": snapshot.snapshot_id, "score_start": old["score_start"], "score_end": old["score_end"],
                "reference_report_hash": original["report_hash"], "reference_spec_hash": digest(spec),
                "report_hashes": {k: r["report_hash"] for k, r in reports.items()},
                "metrics": {k: {m: r["result"][m] for m in metrics} for k, r in reports.items()},
                "buy_counts": {k: sum(f["action"] == "BUY" for f in r["result"]["fills"]) for k, r in reports.items()},
                "C_entry_at": reports["C"]["effective_entry"]["execution_at"] if reports["C"]["effective_entry"] else None,
                "D_entry_at": reports["D"]["effective_entry"]["execution_at"] if reports["D"]["effective_entry"] else None,
                "D_minus_C_return": reports["D"]["result"]["total_return"] - reports["C"]["result"]["total_return"],
                "content_changed_entry": reports["D"]["effective_entry"] != reports["C"]["effective_entry"],
                "disabled_D_byte_identical_C": equal,
                "exit_bases": {k: [f["fill_basis"] for f in r["result"]["fills"] if f["action"] == "SELL"] for k, r in reports.items()}}
            cells.append(result)
    if len(cells) != 14 or len(excluded) != 3:
        raise ValueError("content_fixed_sample_or_cost_coverage_mismatch")
    if any(sha(path) != expected for path, expected in before.items()):
        raise ValueError("content_original_bytes_changed")
    summary = {"schema_version": "fixed-equity-content-study-v1", "completed_at": datetime.now(timezone.utc).isoformat(),
        "protocol_hash": FROZEN_PROTOCOL_HASH, "packet_hash": packet["packet_hash"], "approval_hash": digest(approval),
        "reviewed_fields_rows": 10, "company_count": 1, "admitted_events": 7, "excluded_events": excluded,
        "economic_reports": 28, "replay_verified_reports": 28, "independent_ledger_passes": 28,
        "disabled_content_checks": 14, "cells": cells, "tool_identity": tool_identity(),
        "driver_sha256": sha(Path(__file__)), "independent_ledger_script_sha256": sha(ROOT / "scripts/reconcile_research_ledger.py"),
        "engine_provenance": report["provenance"], "original_files_unchanged": len(before),
        "old_reports_reexecuted": 0, "new_external_requests": 0, "order_allowed": False,
        "purpose": "ALREADY_SEEN_ONE_COMPANY_DEVELOPMENT_NOT_CONFIRMATION",
        "caveats": report["limitations"]}
    summary["study_hash"] = digest(summary)
    write(args.output / "study.private.json", summary)
    return summary


def offline(event, arguments):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname"}:
        raise RuntimeError("content_study_network_forbidden")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original-root", "source-root", "packet", "approval", "protocol", "study", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    sys.addaudithook(offline)
    result = run(parser.parse_args())
    print(json.dumps({k: result[k] for k in ("study_hash", "economic_reports", "replay_verified_reports", "independent_ledger_passes",
                                          "disabled_content_checks", "original_files_unchanged", "new_external_requests")}, indent=2))
