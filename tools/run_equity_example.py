"""Run a copied synthetic example against the current installed research wheel.

Standard library only. Child interpreters use isolated mode, never a source
checkout or PYTHONPATH. No dependencies are installed and no data is downloaded.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


class ExampleFailure(Exception):
    def __init__(self, stage, reason):
        self.stage, self.reason = stage, reason
        super().__init__(stage + ":" + reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")


def require(condition, stage, reason):
    if not condition:
        raise ExampleFailure(stage, reason)


def read(path):
    return json.loads(path.read_bytes())


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def run_json(argv, *, stage, output, environment):
    try:
        process = subprocess.run(argv, cwd=output, env=environment, capture_output=True,
                                 text=True, encoding="utf-8", timeout=180)
    except subprocess.TimeoutExpired as exc:
        raise ExampleFailure(stage, "TIMEOUT") from exc
    require(process.returncode == 0, stage, "CHILD_EXIT_" + str(process.returncode))
    try:
        result = json.loads(process.stdout)
    except (ValueError, TypeError) as exc:
        raise ExampleFailure(stage, "CHILD_JSON_INVALID") from exc
    require(type(result) is dict, stage, "CHILD_OBJECT_REQUIRED")
    return result


def artifact(value, output, stage):
    path = Path(value).resolve()
    try:
        relative = path.relative_to(output).as_posix()
    except ValueError as exc:
        raise ExampleFailure(stage, "ARTIFACT_OUTSIDE_OUTPUT") from exc
    require(path.is_file() and not path.is_symlink(), stage, "ARTIFACT_NOT_REGULAR_FILE")
    return path, {"path": relative, "sha256": sha(path.read_bytes())}


def freeze_summary(summary, output):
    summary = {**summary, "summary_hash": sha(canonical(summary))}
    encoded = (json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    # Publish without replacing previous evidence, including concurrent runs.
    target = output / ("equity_example_" + summary["summary_hash"] + ".json")
    descriptor, name = tempfile.mkstemp(prefix=".equity-example-", suffix=".tmp", dir=output)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            require(target.read_bytes() == encoded, "summary", "EXISTING_CONTENT_DIFFERS")
    finally:
        temporary.unlink(missing_ok=True)
    return summary


def execute(args):
    examples, output, ledger_script = args.examples_root.resolve(), args.output_dir.resolve(), args.ledger_script.resolve()
    require(ledger_script.is_file(), "inputs", "LEDGER_SCRIPT_REQUIRED")
    paths = {
        "equity_research/synthetic_daily.csv": examples / "equity_research/synthetic_daily.csv",
        "equity_research/synthetic_daily.manifest.json": examples / "equity_research/synthetic_daily.manifest.json",
        "equity_research/example.spec.json": examples / "equity_research/example.spec.json",
        "equity_events/synthetic_earnings.txt": examples / "equity_events/synthetic_earnings.txt",
        "equity_events/synthetic_earnings.metadata.json": examples / "equity_events/synthetic_earnings.metadata.json",
    }
    require(all(path.is_file() and not path.is_symlink() for path in paths.values()), "inputs", "EXAMPLE_REGULAR_FILES_REQUIRED")
    before = {name: sha(path.read_bytes()) for name, path in paths.items()}
    metadata = read(paths["equity_research/synthetic_daily.manifest.json"])
    spec = read(paths["equity_research/example.spec.json"])
    event_metadata = read(paths["equity_events/synthetic_earnings.metadata.json"])
    require(metadata["evidence_kind"] == "SYNTHETIC_TEST" and spec["purpose"] == "SYNTHETIC_REGRESSION",
            "inputs", "SYNTHETIC_FIXTURE_ONLY")
    require(event_metadata["source"]["kind"] == "SYNTHETIC_FIXTURE", "inputs", "SYNTHETIC_EVENT_ONLY")
    output.mkdir(parents=True, exist_ok=True)
    environment = {key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    interpreter = [sys.executable, "-I", "-B"]
    install_probe = """import importlib.metadata, importlib.util, json, pathlib, sysconfig
origin = pathlib.Path(importlib.util.find_spec('hakimi_research').origin).resolve()
distribution = importlib.metadata.distribution('hakimi-research')
direct = json.loads(distribution.read_text('direct_url.json') or '{}')
roots = [pathlib.Path(sysconfig.get_path(name)).resolve() for name in ('purelib', 'platlib')]
installed = any(origin.is_relative_to(root) for root in roots)
editable = direct.get('dir_info', {}).get('editable', False)
print(json.dumps({'inside_installation': installed, 'editable': editable, 'version': distribution.version}))
"""
    installation = run_json([*interpreter, "-c", install_probe], stage="installed-wheel", output=output, environment=environment)
    require(installation["inside_installation"] is True and installation["editable"] is False,
            "installed-wheel", "NON_EDITABLE_INSTALLED_PACKAGE_REQUIRED")
    def cli(command, *options):
        return run_json([*interpreter, "-m", "hakimi_research.equity_cli", command,
                         *map(str, options), "--output-dir", str(output)], stage=command, output=output, environment=environment)
    imported = cli("snapshot-import", "--csv", paths["equity_research/synthetic_daily.csv"],
                   "--metadata", paths["equity_research/synthetic_daily.manifest.json"])
    require(imported["snapshot_id"] == spec["snapshot_id"], "snapshot-import", "FIXED_SPEC_SNAPSHOT_ID_MISMATCH")
    require(imported["research_admission"]["allowed"] is True, "snapshot-import", "SNAPSHOT_NOT_ADMITTED")
    snapshot_path, snapshot_artifact = artifact(imported["snapshot"], output, "snapshot-import")
    snapshot = read(snapshot_path)
    research = cli("research", "--snapshot", snapshot_path, "--spec", paths["equity_research/example.spec.json"])
    report_path, report_artifact = artifact(research["full_report"], output, "research")
    replay = cli("replay", "--snapshot", snapshot_path, "--report", report_path)
    require(all(replay[key] is True for key in ("result_matches", "source_matches", "environment_verified", "replay_verified")),
            "replay", "EXACT_REPLAY_NOT_VERIFIED")
    require(replay["replay_provenance"]["source_identity"]["status"] == "BUILD_VERIFIED",
            "replay", "INSTALLED_BUILD_RECEIPT_NOT_VERIFIED")
    _, replay_artifact = artifact(replay["receipt_path"], output, "replay")
    ledger = run_json([*interpreter, str(ledger_script), "--report", str(report_path), "--snapshot", str(snapshot_path),
                       "--output-dir", str(output / "ledger")], stage="independent-ledger", output=output, environment=environment)
    require(ledger["status"] == "PASS" and ledger["failures"] == [] and ledger["project_numerical_engine_imported"] is False,
            "independent-ledger", "DECIMAL_RECONCILIATION_FAILED")
    require(ledger["report_hash"] == research["report_hash"] and ledger["snapshot_id"] == imported["snapshot_id"],
            "independent-ledger", "LEDGER_INPUT_IDENTITY_MISMATCH")
    _, ledger_artifact = artifact(output / "ledger" / ("ledger_" + ledger["receipt_sha256"] + ".json"), output, "independent-ledger")
    event_dir = output / "event-ledger"
    event = cli("event-import", "--source-text", paths["equity_events/synthetic_earnings.txt"],
                "--metadata", paths["equity_events/synthetic_earnings.metadata.json"], "--event-dir", event_dir)
    _, event_artifact = artifact(event["event"], output, "event-import")
    alignment = cli("event-eligibility", "--event-dir", event_dir, "--snapshot", snapshot_path, "--as-of", args.event_as_of)
    require(alignment["snapshot_id"] == imported["snapshot_id"] and alignment["selected_event_hashes"] == [event["event_hash"]]
            and len(alignment["rows"]) == 1, "event-eligibility", "ONE_MATCHING_EVENT_REQUIRED")
    row = alignment["rows"][0]
    available = stamp(event["availability"]["available_at"])
    sessions = snapshot["sessions"]
    observation = next((session for session in sessions if stamp(session["open_utc"]) >= available), None)
    require(observation is not None, "event-eligibility", "NO_FULL_POST_EVENT_SESSION")
    confirmation = stamp(observation["close_utc"]) + timedelta(seconds=snapshot["bar_availability_lag_seconds"])
    entry = next((session for session in sessions[sessions.index(observation) + 1:] if stamp(session["open_utc"]) > confirmation), None)
    require(entry is not None and row["status"] == "READY" and row["observation_session"] == observation
            and stamp(row["confirmation_available_at"]) == confirmation and row["entry_session"] == entry
            and stamp(row["earliest_entry_at"]) == stamp(entry["open_utc"])
            and stamp(row["available_at"]) == available and row["order_allowed"] is False,
            "event-eligibility", "POST_AVAILABILITY_TIME_BOUNDARY_MISMATCH")
    _, alignment_artifact = artifact(alignment["report_path"], output, "event-eligibility")
    permissions = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    require(all(result["execution_permission"] == permissions for result in (research, replay, event, alignment)),
            "permissions", "EXECUTION_PERMISSION_CHANGED")
    require(before == {name: sha(path.read_bytes()) for name, path in paths.items()}, "inputs", "EXAMPLE_FILES_CHANGED")
    summary = {
        "schema_version": "synthetic-equity-example-result-v1", "status": "PASS", "evidence_kind": "SYNTHETIC_TEST",
        "scope": "INSTALLED_WHEEL_ACCOUNTING_AND_EVENT_CLOCK_ONLY_NOT_MARKET_OR_STRATEGY_VALIDATION",
        "inputs_sha256": before, "ledger_script_sha256": sha(ledger_script.read_bytes()),
        "tool_sha256": sha(Path(__file__).read_bytes()), "source_checkout_imported": False, "network_used": False,
        "installation": installation,
        "snapshot_id": imported["snapshot_id"], "security_id": snapshot["security"]["security_id"],
        "sessions": len(sessions), "report_hash": research["report_hash"], "result_hash": research["result_hash"],
        "research": {key: research[key] for key in ("total_return", "max_drawdown", "fill_count")},
        "replay": {key: replay[key] for key in ("result_matches", "source_matches", "environment_verified", "replay_verified")},
        "installed_source_content_sha256": replay["replay_provenance"]["source_identity"]["content_sha256"],
        "independent_ledger": {key: ledger[key] for key in ("status", "checks", "score_bars", "fill_count",
            "maximum_absolute_numeric_error", "reconciled_buy_fees", "reconciled_sell_fees", "project_numerical_engine_imported")},
        "event_clock": {"event_hash": event["event_hash"], "available_at": row["available_at"],
                        "available_at_kind": row["available_at_kind"], "observation_session": observation["date"],
                        "confirmation_available_at": row["confirmation_available_at"], "entry_session": entry["date"],
                        "earliest_entry_at": row["earliest_entry_at"], "status": "CALENDAR_TIMING_ONLY"},
        "artifacts": {"snapshot": snapshot_artifact, "research": report_artifact, "replay": replay_artifact,
                      "independent_ledger": ledger_artifact, "event": event_artifact, "alignment": alignment_artifact},
        "execution_permission": permissions,
    }
    return freeze_summary(summary, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run copied fictional equity inputs against this Python's installed hakimi-research wheel.")
    parser.add_argument("--examples-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ledger-script", type=Path, required=True)
    parser.add_argument("--event-as-of", default="2024-11-29T18:08:00Z")
    args = parser.parse_args(argv)
    try:
        summary = execute(args)
    except ExampleFailure as exc:
        print(json.dumps({"status": "FAIL", "evidence_kind": "SYNTHETIC_TEST", "stage": exc.stage, "reason": exc.reason}))
        return 1
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        # Failures intentionally omit exception text that may contain local paths.
        print(json.dumps({"status": "FAIL", "evidence_kind": "SYNTHETIC_TEST", "stage": "example", "reason": type(exc).__name__}))
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
