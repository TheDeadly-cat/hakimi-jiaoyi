from __future__ import annotations

import argparse
import json
from pathlib import Path

from hakimi_research.dataset_registry import import_capture, load_snapshot, save_snapshot
from hakimi_research.documents import read_document
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, ResearchReport, replay_report, verify_report
from hakimi_research.product_capabilities import build_product_capability_catalog, supported_cli_commands
from hakimi_research.reporting import save_json_report
from hakimi_research.source_layout import DEFAULT_CONFIG_PATH, default_artifact_root

LEGACY_PAPER_ENABLED = False
LEGACY_OPTIMIZE_ENABLED = False


def command_paper(_args):
    raise RuntimeError("Legacy paper path is archived and permanently disabled in the research-only product.")


def command_optimize(_args):
    raise RuntimeError("Legacy optimize path is archived and permanently disabled in the research-only product.")


def _required(args, *names):
    for name in names:
        if not getattr(args, name):
            raise ValueError("explicit --" + name.replace("_", "-") + " is required")


def command_backtest(args):
    _required(args, "snapshot", "spec")
    report = ExperimentRunner().run(load_snapshot(args.snapshot), ExperimentSpec.load(args.spec))
    path = report.save(Path(args.output_dir) / "reports")
    result = report.document["result"]
    return {"ok": True, "full_report": str(path), "result_hash": report.document["result_hash"],
            "total_return": result["total_return"], "max_drawdown": result["max_drawdown"],
            "fill_count": result["fill_count"], "round_trip_count": result["round_trip_count"],
            "execution_permission": report.document["execution_permission"]}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline, fixed-snapshot BTC-USDT spot / 1h research.")
    parser.add_argument("command", choices=supported_cli_commands())
    parser.add_argument("--capture", help="Local okx-public-capture-v1 JSON; import never downloads data.")
    parser.add_argument("--csv", help="Local OHLCV CSV; requires explicit --metadata.")
    parser.add_argument("--metadata", help="CSV provenance, units, UTC bounds and completion declaration JSON.")
    parser.add_argument("--predecessor", help="Existing immutable snapshot to link as the previous version.")
    parser.add_argument("--snapshot", help="Exact immutable dataset JSON path.")
    parser.add_argument("--spec", help="Explicit research-experiment-spec-v1 JSON with score boundaries.")
    parser.add_argument("--report", help="Existing versioned research-report JSON path.")
    parser.add_argument("--config", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", default=str(default_artifact_root()))
    args = parser.parse_args(argv)
    try:
        if args.config:
            raise ValueError("The formal runner requires --snapshot and --spec; provider configs are legacy preview only.")
        if args.command == "capabilities":
            output = build_product_capability_catalog().to_dict()
        elif args.command == "list-strategies":
            from hakimi_research.strategies.templates import STRATEGY_REGISTRY
            output = {"strategies": sorted(STRATEGY_REGISTRY), "parameter_selection": False}
        elif args.command == "snapshot-import":
            predecessor = load_snapshot(args.predecessor) if args.predecessor else None
            if args.csv:
                _required(args, "metadata")
                if args.capture:
                    raise ValueError("choose either --capture or --csv with --metadata")
                from hakimi_research.dataset_registry import import_csv
                snapshot = import_csv(args.csv, args.metadata, predecessor=predecessor)
            else:
                _required(args, "capture")
                if args.metadata:
                    raise ValueError("--metadata requires --csv")
                snapshot = import_capture(args.capture, predecessor=predecessor)
            path = save_snapshot(snapshot, Path(args.output_dir) / "datasets")
            output = {"ok": True, "snapshot": str(path), "snapshot_id": snapshot.snapshot_id,
                      "quality": snapshot.document["quality"]}
        elif args.command in {"research", "backtest"}:
            output = command_backtest(args)
        elif args.command == "report-show":
            _required(args, "report")
            output = verify_report(read_document(args.report))
        elif args.command == "replay":
            _required(args, "snapshot", "report")
            output = replay_report(load_snapshot(args.snapshot), ResearchReport(read_document(args.report)))
            output["receipt_path"] = str(save_json_report(output, Path(args.output_dir) / "replays", "replay",
                                                         artifact_id=output["receipt_hash"]))
            if not output["replay_verified"]:
                print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
                raise SystemExit(1)
        else:
            raise ValueError("Unsupported formal command")
        print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None
