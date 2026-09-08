"""One explicit public-capture cycle for two frozen, no-order observation plans."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from hakimi_research.dataset_registry import HOUR, load_snapshot, utc_text, utc_time
from hakimi_research.documents import digest, read_document
from hakimi_research.reporting import save_json_report


def _now():
    return utc_time(datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), aligned=False)


def _runtime_python(root):
    expected = root / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")
    if Path(sys.executable).resolve() != expected.resolve():
        raise ValueError("forward_cycle_requires_this_deployment_installed_python")


def _observer(root):
    path = root / "tools/observe_forward.py"
    spec = importlib.util.spec_from_file_location("deployed_forward_observer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hour(root, cutoff):
    return root / "forward/cycles" / cutoff.strftime("%Y%m%dT%H0000Z")


def _collect(root, start, cutoff, hour):
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", str(root / "tools/collect_btc_snapshot.py"),
         "--start", utc_text(start), "--end", utc_text(cutoff), "--output-dir", str(hour)],
        cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    if result.returncode:
        raise RuntimeError("forward_public_capture_failed:" + result.stderr[-1500:])
    return json.loads(result.stdout)


def _input(root, cutoff):
    hour = _hour(root, cutoff)
    receipt_path = hour / "forward_input_fixed.json"
    if not receipt_path.exists():
        # An existing incomplete directory indicates a prior/in-flight attempt.
        # Fail closed instead of refetching and mixing input versions.
        hour.mkdir(parents=True, exist_ok=False)
        captured = _collect(root, cutoff - 72 * HOUR, cutoff, hour)
        files = {}
        for kind in ("capture", "snapshot"):
            path = Path(captured[kind]).resolve()
            if not path.is_relative_to(hour.resolve()):
                raise ValueError("forward_capture_output_outside_cycle")
            files[kind] = {"path": path.relative_to(root).as_posix(),
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        core = {"schema_version": "forward-cycle-input-v1", "cutoff": utc_text(cutoff), "files": files}
        save_json_report({**core, "input_receipt_hash": digest(core)}, hour, "forward_input", artifact_id="fixed")
    receipt = read_document(receipt_path)
    core = {key: value for key, value in receipt.items() if key != "input_receipt_hash"}
    if (receipt.get("input_receipt_hash") != digest(core)
            or receipt.get("schema_version") != "forward-cycle-input-v1"
            or receipt.get("cutoff") != utc_text(cutoff)):
        raise ValueError("forward_cycle_input_receipt_invalid")
    paths = {}
    for kind in ("capture", "snapshot"):
        item = receipt["files"][kind]
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(hour.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("forward_cycle_original_input_changed")
        paths[kind] = path
    snapshot = load_snapshot(paths["snapshot"])
    if (utc_time(snapshot.document["start"]) != cutoff - 72 * HOUR
            or utc_time(snapshot.document["end_exclusive"]) != cutoff):
        raise ValueError("forward_cycle_context_mismatch")
    return snapshot, receipt_path


def run_cycle(deployment: Path, runtime_root: Path | None = None) -> dict:
    root = (runtime_root or deployment.resolve().parent.parent).resolve()
    _runtime_python(root)
    observer = _observer(root)
    configuration = read_document(deployment)
    first = utc_time(configuration["first_cutoff"])
    plans = [observer._plan(read_document(Path(item["plan"]))) for item in configuration["plans"]]
    if (len(plans) != 2 or {plan["spec"]["strategy"]["name"] for plan in plans} != {"dual_ma", "rsi"}
            or any(plan["spec"]["context_rows"] != 72 or utc_time(plan["spec"]["first_cutoff"]) != first for plan in plans)):
        raise ValueError("forward_cycle_requires_two_fixed_72_row_plans_with_same_first_cutoff")
    cutoff = _now().floor("h")
    if cutoff < first:
        return {"status": "NOT_DUE", "first_cutoff": utc_text(first), "observations": 0, "captures": 0}
    snapshot, input_path = _input(root, cutoff)
    records = []
    for plan in plans:
        path = observer.observe(plan, snapshot, utc_text(cutoff), _hour(root, cutoff) / "observations")
        record = read_document(path)
        verified = observer.replay(plan, snapshot, record)
        if verified["status"] != "VERIFIED":
            raise ValueError("forward_cycle_replay_failed")
        records.append({"plan_hash": plan["plan_hash"], "strategy": plan["spec"]["strategy"]["name"],
                        "record": str(path), "record_hash": record["record_hash"], "timing_status": record["timing_status"]})
    absent = []
    previous = first
    while previous < cutoff:
        missing = [plan["plan_hash"] for plan in plans if not (_hour(root, previous) / "observations" /
                   ("forward_observation_" + digest({"plan_hash": plan["plan_hash"], "cutoff": utc_text(previous)}) + ".json")).is_file()]
        if missing:
            absent.append({"cutoff": utc_text(previous), "missing_plan_hashes": missing})
        previous += HOUR
    summary = {"status": "RECORDED_AND_REPLAYED", "cutoff": utc_text(cutoff), "observations": len(records),
               "replays_verified": len(records), "input_receipt": str(input_path), "records": records,
               "prior_absences": absent, "automatic_backfill": False, "order_allowed": False}
    save_json_report(summary, _hour(root, cutoff), "forward_cycle", artifact_id="fixed")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_cycle(args.deployment, args.runtime_root), ensure_ascii=True, allow_nan=False))
