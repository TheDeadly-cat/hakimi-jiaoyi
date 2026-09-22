"""Offline bundle inspection and explicit isolated installation; never broker dispatch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import venv


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_bundle(root):
    root = Path(root).resolve()
    manifest_path = root / "preview-manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("manifest_regular_file_required")
    manifest = json.loads(manifest_path.read_bytes())
    core = {key: value for key, value in manifest.items() if key != "build_id"}
    if manifest.get("schema_version") != "supervised-preview-bundle-v1" or manifest.get("kind") not in {"research", "windows-futu"}:
        raise ValueError("preview_manifest_schema_invalid")
    if manifest.get("build_id") != "supervised-" + manifest["kind"] + "-" + sha(canonical(core)):
        raise ValueError("preview_build_identity_mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("preview_files_missing")
    for name, expected in files.items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", name) or ".." in PurePosixPath(name).parts:
            raise ValueError("preview_file_path_invalid")
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root) or sha(path.read_bytes()) != expected:
            raise ValueError("preview_file_identity_mismatch:" + name)
    for field in ("wheel", "observation_summary"):
        if field in manifest and manifest[field] not in files:
            raise ValueError("preview_reference_not_bound:" + field)
    return manifest


def clean_environment():
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    env.update(PYTHONNOUSERSITE="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    return env


def environment_python(runtime, kind):
    return runtime / ("research-env" if kind == "research" else "futu-env") / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def inspect_installation(root, manifest, runtime):
    if runtime is None:
        return {"status": "NOT_CHECKED", "reason": "Pass --runtime-root to check an installation; no account or database is read."}
    runtime = Path(runtime).resolve()
    python = environment_python(runtime, manifest["kind"])
    receipt = runtime / (manifest["kind"] + "-installation.json")
    if not python.is_file() or not receipt.is_file():
        return {"status": "NOT_INSTALLED", "runtime_root": str(runtime)}
    record = json.loads(receipt.read_bytes())
    if record.get("build_id") != manifest["build_id"]:
        return {"status": "DIFFERENT_BUILD", "runtime_root": str(runtime), "installed_build_id": record.get("build_id")}
    if manifest["kind"] == "research":
        code = "import json; from hakimi_research.environment import build_runtime_provenance; p=build_runtime_provenance(); print(json.dumps({'source':p['source_identity']['status'],'source_sha256':p['source_identity']['content_sha256'],'dependencies':p['environment_verified']['status'],'execution_permission':p['execution_permission']}))"
    else:
        lock = (root / "requirements.futu-sdk.lock").read_text(encoding="utf-8")
        pins = dict(line.split("==") for line in lock.splitlines() if line.strip() and not line.startswith("#"))
        code = "import json,importlib.metadata; pins=" + repr(pins) + "; actual={k:importlib.metadata.version(k) for k in pins}; print(json.dumps({'dependencies':'VERIFIED' if actual==pins else 'MISMATCH','packages':actual,'sdk_imported':False,'account_connected':False}))"
    completed = subprocess.run([str(python), "-I", "-B", "-c", code], cwd=runtime, env=clean_environment(), text=True, capture_output=True, timeout=30)
    if completed.returncode:
        return {"status": "FAILED", "runtime_root": str(runtime), "error": completed.stderr[-3000:]}
    actual = json.loads(completed.stdout)
    good = actual["dependencies"] == "VERIFIED"
    if manifest["kind"] == "research":
        good = good and actual["source"] == "BUILD_VERIFIED" and actual["source_sha256"] == manifest["research_source_sha256"]
    return {"status": "VERIFIED" if good else "MISMATCH", "runtime_root": str(runtime), "actual": actual}


def show_status(root, runtime=None):
    manifest = verify_bundle(root)
    sample = json.loads((root / "evidence/amd-research-summary.json").read_bytes())
    history = sample["comparison"]
    retained_health = None
    if "observation_summary" in manifest:
        observation = json.loads((root / manifest["observation_summary"]).read_bytes())
        retained_health = {name: observation.get(name) for name in
            ("checked_at", "window", "window_elapsed", "reliability_acceptance", "current_counts", "deadline_counts")}
        retained_health["latest_watch_evidence_time"] = observation.get("latest_retained_watch", {}).get("checked_at")
        retained_health["scheduler_evidence_time"] = observation.get("scheduler", {}).get("checked_at")
        retained_health["retained_task_states"] = [{name: task.get(name) for name in ("task_name", "state", "enabled", "next_run_at")}
            for task in observation.get("scheduler", {}).get("tasks", [])]
    event_diagnostics = None
    if "evidence/equity-events/reference-results.json" in manifest["files"]:
        reference = json.loads((root / "evidence/equity-events/reference-results.json").read_bytes())
        prepared = json.loads((root / "evidence/equity-events/prepared-inputs.json").read_bytes())
        event_diagnostics = {"scope": reference["scope"], "new_price_windows": prepared["new_price_windows"],
            "schedule_sources_obtained": prepared["schedule_sources_obtained"],
            "schedule_sources_missing": prepared["schedule_sources_missing"],
            "same_period_reference": [{"cost_multiplier": row["cost_multiplier"],
                "A_return": row["diagnostics"]["A_metrics"]["total_return"],
                "B_return": row["diagnostics"]["B_metrics"]["total_return"],
                "buy_hold_return": row["aligned_buy_and_hold"]["total_return"]} for row in reference["cells"]],
            "not_a_ten_event_market_result": True, "rerun_by_status_command": False}
    completed_study = None
    if "evidence/equity-events/study-final-results.json" in manifest["files"]:
        study = json.loads((root / "evidence/equity-events/study-final-results.json").read_bytes())
        completed_study = {name: study[name] for name in
            ("completed_at", "scope", "event_coverage", "company_count", "independent_sample_count", "reports_verified", "C_D")}
        completed_study['events'] = [{"quarter": event['fiscal_quarter'], "status": event['status'],
            "reason": event.get('reason'), "cost_cases": [{"cost_multiplier": cell['cost_multiplier'],
                "A_return": cell['diagnostics']['A_metrics']['total_return'],
                "B_return": cell['diagnostics']['B_metrics']['total_return'],
                "aligned_buy_hold_return": cell['aligned_buy_and_hold']['total_return'],
                "blocked_buy_intents": cell['diagnostics']['actual_blocked_B_buy_intents']}
                for cell in event['cells']]} for event in study['events']]
        completed_study.update(rerun_by_status_command=False, profitability_verified=False,
                               raw_market_data_included=False)
    preflight = None
    if "evidence/futu-preflight-20260920.json" in manifest["files"]:
        retained = json.loads((root / "evidence/futu-preflight-20260920.json").read_bytes())
        preflight = {name: retained.get(name) for name in
            ("status", "observed_gate", "orders_sent", "accounting_verified", "order_authorization_created", "source_scope", "boundary")}
        preflight["evidence_time"] = max((query["completed_at"] for query in retained.get("queries", [])), default=None)
        preflight["cleanup_confirmed"] = retained.get("execution_bounds", {}).get("cleanup_confirmed")
        preflight["rerun_by_status_command"] = False
    first_preflight = preflight
    if "evidence/futu-readonly-followup.json" in manifest["files"]:
        retained = json.loads((root / "evidence/futu-readonly-followup.json").read_bytes())
        preflight = {name: retained[name] for name in ("status", "orders_sent", "cancel_calls",
            "authorization_created", "stable_read_completed", "initial_order_gate", "instrument_verified",
            "market_state", "regular_session_open")}
        preflight.update(evidence_time=retained['finished_at'], rerun_by_status_command=False,
                         account_state_checked_now=False, accounting_verified=False)
        preflight['evidence_adapter_matches_bundled_tool'] = (
            manifest['files'].get('tools/futu_simulation_adapter.py') == retained['source_sha256']['futu_simulation_adapter.py']
            if manifest['kind'] == 'windows-futu' else None)
    return {
        "build_id": manifest["build_id"], "kind": manifest["kind"], "bundle_integrity": "VERIFIED",
        "formal_release": "v0.2.1 (unchanged; this is a separate supervised preview)",
        "version": manifest["version"], "source": manifest["source"],
        "research_source_sha256": manifest.get("research_source_sha256"), "wheel_sha256": manifest.get("wheel_sha256"),
        "installation": inspect_installation(root, manifest, runtime),
        "historical_sample": {"evidence_time": sample["completed_at"], "snapshot_id": sample["snapshot_id"],
            "source": sample["source_admission"]["normalization"]["source"],
            "score_start": history["common_parameters"]["score_start_session"],
            "score_end": history["common_parameters"]["score_end_session"],
            "A": history["A"]["metrics"], "B": history["B"]["metrics"],
            "conclusion": sample["conclusion"], "rerun_by_status_command": False,
            "original_buy_hold_has_different_scoring_start": True, "raw_market_data_included": False},
        "order_test": {"status": "NOT_RUN_BY_PREVIEW", "separate_operation_authorization_required": True,
            "historical_evidence": "evidence/futu-readonly.json", "fees_accounting": "NOT_VERIFIED",
            "latest_retained_preflight": preflight, "first_preflight_preserved": first_preflight},
        "additional_event_research": event_diagnostics,
        "completed_fixed_event_study": completed_study,
        "runtime_health": {"live_processes_accounts_databases": "NOT_CHECKED", "monitor_started": False,
            "historical_status_file": "evidence/CURRENT_STATUS.md",
            "retained_observation_summary": manifest.get("observation_summary", "NOT_INCLUDED"),
            "retained_health": retained_health,
            "interpretation": "Bundled evidence is frozen history, not a current account, scheduler or unattended-health check."},
        "unverified": ["Official simulation order lifecycle", "Provider fees and settlement originals", "Live trading and profitability", "Human financial-field approval", "Unattended operation"],
    }


def install(root, runtime, *, wheelhouse=None, allow_downloads=False):
    manifest = verify_bundle(root)
    kind = manifest["kind"]
    if kind == "windows-futu" and os.name != "nt":
        raise ValueError("futu_job_toolkit_requires_windows")
    runtime = Path(runtime).resolve()
    if runtime.is_relative_to(root.resolve()):
        raise ValueError("runtime_must_be_outside_immutable_bundle")
    if wheelhouse is None and not allow_downloads:
        raise ValueError("supply_wheelhouse_or_explicit_allow_package_downloads")
    if wheelhouse is not None and not Path(wheelhouse).is_dir():
        raise ValueError("wheelhouse_directory_missing")
    python = environment_python(runtime, kind)
    env_root = python.parent.parent
    receipt = runtime / (kind + "-installation.json")
    if env_root.exists() or receipt.exists():
        raise ValueError("installation_destination_exists_use_new_runtime_root")
    runtime.mkdir(parents=True, exist_ok=True)
    log = runtime / (kind + "-installation.log")
    if log.exists():
        raise ValueError("installation_log_exists_use_new_runtime_root")
    with log.open("x", encoding="utf-8") as stream:
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(env_root)
        command = [str(python), "-I", "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir"]
        if wheelhouse is not None:
            command += ["--no-index", "--find-links", str(Path(wheelhouse).resolve())]
        lock_name = "requirements.research.lock" if kind == "research" else "requirements.futu-sdk.lock"
        commands = [[*command, "-r", str(root / lock_name)]]
        if kind == "research":
            commands.append([*command, "--no-deps", str(root / manifest["wheel"])])
        commands.append([str(python), "-I", "-m", "pip", "check"])
        for argv in commands:
            stream.write("COMMAND " + json.dumps(argv) + "\n"); stream.flush()
            completed = subprocess.run(argv, cwd=runtime, env=clean_environment(), stdout=stream, stderr=subprocess.STDOUT, timeout=900)
            if completed.returncode:
                raise RuntimeError("installation_failed_see_log:" + str(log))
        # Never import Futu or execute a tool as an installation side effect.
        if kind == "research":
            completed = subprocess.run([str(python), "-I", "-B", "-m", "hakimi_research.equity_cli", "capabilities"], cwd=runtime, env=clean_environment(), stdout=stream, stderr=subprocess.STDOUT, timeout=30)
            if completed.returncode:
                raise RuntimeError("research_cli_smoke_failed_see_log:" + str(log))
    verify_bundle(root)
    record = {"schema_version": "supervised-preview-installation-v1", "build_id": manifest["build_id"],
        "kind": kind, "editable": False, "pythonpath_used": False, "system_site_packages": False,
        "account_connected": False, "monitor_started": False, "order_sent": False}
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2); stream.write("\n")
    result = inspect_installation(root, manifest, runtime)
    if result["status"] != "VERIFIED":
        raise RuntimeError("installation_identity_verification_failed:" + str(receipt))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "install"), nargs="?", default="status")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--allow-package-downloads", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        if args.command == "install":
            if args.runtime_root is None:
                parser.error("install requires an explicit --runtime-root")
            output = install(root, args.runtime_root, wheelhouse=args.wheelhouse, allow_downloads=args.allow_package_downloads)
        else:
            output = show_status(root, args.runtime_root)
        print(json.dumps(output, indent=2, ensure_ascii=True, allow_nan=False))
        return 1 if output.get("installation", {}).get("status") in {"FAILED", "MISMATCH", "DIFFERENT_BUILD"} else 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
