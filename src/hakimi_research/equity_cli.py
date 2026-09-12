"""Offline stock research and point-in-time event tools; no broker or network."""
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from hakimi_research.documents import digest, read_document
from hakimi_research.equity_dataset import build_equity_snapshot, load_equity_snapshot, save_equity_snapshot
from hakimi_research.equity_events import (build_equity_event, save_equity_event, select_event_versions,
                                           event_session_eligibility, verify_equity_event)
from hakimi_research.equity_research import (EquityExperimentRunner, EquityExperimentSpec, EquityResearchReport,
                                             replay_equity_report, verify_equity_report, PERMISSIONS)
from hakimi_research.reporting import save_json_report
from hakimi_research.source_layout import default_artifact_root


def _deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("equity_cli_offline_network_denied")


def _align_selected_event(event, snapshot):
    """Do not rename the first covered session as the first post-event session."""
    available = datetime.fromisoformat(event["availability"]["available_at"].replace("Z", "+00:00"))
    calendar = snapshot["calendar"]
    available_date = available.astimezone(ZoneInfo(calendar["timezone"])).date()
    lag = snapshot["bar_availability_lag_seconds"]
    if available_date < date.fromisoformat(calendar["coverage_start"]):
        # The missing earlier calendar could contain the actual observation
        # session. Retain the event identity, but offer no replacement session.
        result = event_session_eligibility(event, [], lag)
        result["reason"] = "EVENT_AVAILABILITY_PRECEDES_CALENDAR_COVERAGE"
        return result
    return event_session_eligibility(event, snapshot["sessions"], lag)


def main(argv=None):
    sys.addaudithook(_deny_network)
    parser = argparse.ArgumentParser(description="美股正股日线与事件时间研究（离线预览；禁止账户和订单操作）")
    parser.add_argument("command", choices=("capabilities", "snapshot-import", "research", "replay", "report-show", "event-import", "event-eligibility"))
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--source-text", type=Path)
    parser.add_argument("--event-dir", type=Path)
    parser.add_argument("--as-of", help="Explicit UTC time ending in Z for point-in-time version selection.")
    parser.add_argument("--output-dir", type=Path, default=default_artifact_root() / "equities")
    args = parser.parse_args(argv)
    def required(*names):
        if any(getattr(args, name) is None for name in names):
            raise ValueError("required_arguments:" + ",".join("--" + name.replace("_", "-") for name in names))
    try:
        if args.command == "capabilities":
            output = {"status": "EXPERIMENTAL", "market": "US_COMMON_STOCK", "timeframe": "REGULAR_SESSION_DAILY",
                      "economic_scope": "STABLE_IDENTITY_DECLARED_ACTION_FREE_WINDOWS",
                      "event_scope": "EVIDENCE_BACKED_FIELDS_AND_POINT_IN_TIME_CALENDAR_ALIGNMENT",
                      "data_authentication": "NOT_ESTABLISHED_BY_IMPORT", "broker_integration": "NOT_RUN",
                      "quantity_policy": "FRACTIONAL_SHARES_RESEARCH_APPROXIMATION", "execution_permission": dict(PERMISSIONS)}
        elif args.command == "snapshot-import":
            required("csv", "metadata")
            snapshot = build_equity_snapshot(args.csv.read_bytes(), args.metadata.read_bytes())
            path = save_equity_snapshot(snapshot, args.output_dir / "datasets")
            output = {"snapshot": str(path), "snapshot_id": snapshot.snapshot_id, "security": snapshot.document["security"],
                      "sessions": len(snapshot.document["sessions"]), "research_admission": snapshot.document["research_admission"]}
        elif args.command == "research":
            required("snapshot", "spec")
            report = EquityExperimentRunner().run(load_equity_snapshot(args.snapshot), EquityExperimentSpec.load(args.spec))
            path = report.save(args.output_dir / "reports")
            result = report.document["result"]
            output = {"full_report": str(path), "report_hash": report.document["report_hash"], "result_hash": report.document["result_hash"],
                      "total_return": result["total_return"], "max_drawdown": result["max_drawdown"],
                      "fill_count": result["fill_count"], "execution_permission": dict(PERMISSIONS)}
        elif args.command == "report-show":
            required("report")
            output = verify_equity_report(read_document(args.report))
        elif args.command == "replay":
            required("snapshot", "report")
            output = replay_equity_report(load_equity_snapshot(args.snapshot), EquityResearchReport(read_document(args.report)))
            output["receipt_path"] = str(save_json_report(output, args.output_dir / "replays", "equity_replay", artifact_id=output["receipt_hash"]))
            if not output["replay_verified"]:
                print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
                raise SystemExit(1)
        elif args.command == "event-import":
            required("source_text", "metadata", "event_dir")
            event = build_equity_event(args.source_text.read_bytes(), read_document(args.metadata))
            path = save_equity_event(event, args.event_dir)
            output = {"event": str(path), "event_id": event["event_id"], "event_hash": event["event_hash"],
                      "availability": event["availability"], "execution_permission": dict(PERMISSIONS)}
        else:
            required("event_dir", "snapshot", "as_of")
            if not args.event_dir.is_dir():
                raise ValueError("event_ledger_directory_missing")
            snapshot = load_equity_snapshot(args.snapshot)
            events = []
            for path in sorted(args.event_dir.glob("event_*.json")):
                if path.is_symlink() or not path.is_file():
                    raise ValueError("event_ledger_regular_files_required")
                event = verify_equity_event(read_document(path))
                if path.name != "event_" + event["event_hash"] + ".json":
                    raise ValueError("event_ledger_filename_identity_mismatch")
                events.append(event)
            selected = select_event_versions(events, args.as_of)
            rows = [_align_selected_event(event, snapshot.document)
                    for event in selected if event["security_id"] == snapshot.document["security"]["security_id"]]
            core = {"schema_version": "equity-event-calendar-alignment-v1", "snapshot_id": snapshot.snapshot_id,
                    "as_of": args.as_of, "selected_event_hashes": [event["event_hash"] for event in selected
                        if event["security_id"] == snapshot.document["security"]["security_id"]],
                    "rows": rows, "scope": "CALENDAR_TIMING_ONLY_NOT_A_STRATEGY_RESULT_OR_ORDER_APPROVAL",
                    "execution_permission": dict(PERMISSIONS)}
            output = {**core, "alignment_hash": digest(core)}
            output["report_path"] = str(save_json_report(output, args.output_dir / "events", "event_alignment", artifact_id=output["alignment_hash"]))
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
