"""Freeze and record offline, flat-reference signals; no provider or order path."""
from __future__ import annotations

import argparse
import base64
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import inspect
import io
import json
from pathlib import Path
import re

from hakimi_research.dataset_registry import DatasetSnapshot, HOUR, load_snapshot, utc_text, utc_time, verify_snapshot
from hakimi_research.documents import canonical_bytes, digest, parse_document, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.experiment import ExperimentSpec, required_context
from hakimi_research.models import Portfolio
from hakimi_research.reporting import save_json_report
from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.strategies.templates import build_strategy

STATE_POLICY = "FLAT_REFERENCE_OBSERVATION"
PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
_SPEC_FIELDS = {"name", "strategy", "state_policy", "reference_portfolio", "context_rows", "first_cutoff"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _observer_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _runtime() -> dict:
    evidence = build_runtime_provenance()
    source = evidence["source_identity"]
    environment = evidence["environment_verified"]
    if REPOSITORY_ROOT is not None or source["status"] != "BUILD_VERIFIED":
        raise ValueError("forward_requires_verified_installed_build")
    if environment["status"] != "VERIFIED":
        raise ValueError("forward_requires_verified_environment")
    if type(source["content_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", source["content_sha256"]):
        raise ValueError("forward_source_hash_invalid")
    return {
        "source_sha256": source["content_sha256"],
        "environment_sha256": digest({
            "python_version": environment["python_version"],
            "packages": environment["packages"],
            "lock_sha256": evidence["dependency_lock"]["sha256"],
        }),
        "observer_sha256": _observer_hash(),
    }


def _spec(document: dict) -> dict:
    value = parse_document(canonical_bytes(document))
    if set(value) != _SPEC_FIELDS or value["state_policy"] != STATE_POLICY:
        raise ValueError("forward_plan_fields_or_state_invalid")
    if type(value["name"]) is not str or not value["name"].strip():
        raise ValueError("forward_plan_name_required")
    strategy = value["strategy"]
    if type(strategy) is not dict or strategy.get("name") not in {"dual_ma", "rsi"}:
        raise ValueError("forward_supports_stateless_dual_ma_or_rsi_only")
    first_cutoff = utc_time(value["first_cutoff"])
    if value["first_cutoff"] != utc_text(first_cutoff):
        raise ValueError("forward_canonical_cutoff_seconds_required")
    # Reuse the formal public parameter contract without constructing an engine.
    ExperimentSpec.from_document({
        "schema_version": "research-experiment-spec-v1", "name": value["name"],
        "snapshot_id": "0" * 64, "strategy": strategy,
        "score_start": utc_text(first_cutoff - HOUR), "score_end": value["first_cutoff"],
        "initial_cash": 10000, "fee_rate": 0, "slippage_pct": 0, "risk": {"max_leverage": 1},
        "end_policy": "MARK_TO_MARKET", "purpose": "SYNTHETIC_REGRESSION",
    })
    reference = value["reference_portfolio"]
    if type(reference) is not dict or set(reference) != {"cash", "position_qty", "avg_entry_price", "realized_pnl", "entry_fees"}:
        raise ValueError("forward_explicit_flat_reference_required")
    portfolio = Portfolio(**reference)
    if portfolio.cash <= 0 or any(reference[name] != 0 for name in reference if name != "cash"):
        raise ValueError("forward_reference_must_be_flat_without_prior_pnl")
    rows = value["context_rows"]
    if type(rows) is not int or not required_context(strategy["name"], strategy["params"]) <= rows <= 10000:
        raise ValueError("forward_fixed_context_rows_invalid")
    return value


def _strategy_hash(spec: dict) -> str:
    strategy = build_strategy(**spec["strategy"])
    return digest({"declaration": spec["strategy"], "version": strategy.version,
                   "class_source_sha256": hashlib.sha256(inspect.getsource(type(strategy)).encode("utf-8")).hexdigest()})


def freeze_plan(spec: dict, directory: str | Path) -> Path:
    spec = _spec(spec)
    runtime = _runtime()
    frozen_at = _now()
    if utc_time(spec["first_cutoff"]) <= utc_time(frozen_at, aligned=False):
        raise ValueError("forward_first_cutoff_must_follow_actual_freeze_time")
    core = {"schema_version": "forward-observation-plan-v1", "spec": spec,
            "frozen_at_utc": frozen_at, **runtime, "strategy_hash": _strategy_hash(spec),
            "execution_permission": dict(PERMISSIONS)}
    plan = {**core, "plan_hash": digest(core)}
    return Path(save_json_report(plan, directory, "forward_plan", artifact_id=plan["plan_hash"]))


def _plan(document: dict) -> dict:
    plan = parse_document(canonical_bytes(document))
    core = {key: value for key, value in plan.items() if key != "plan_hash"}
    if set(core) != {"schema_version", "spec", "frozen_at_utc", "source_sha256", "environment_sha256",
                     "observer_sha256", "strategy_hash", "execution_permission"}:
        raise ValueError("forward_plan_fields_invalid")
    if plan.get("schema_version") != "forward-observation-plan-v1" or plan.get("plan_hash") != digest(core):
        raise ValueError("forward_plan_integrity_invalid")
    spec = _spec(plan["spec"])
    if (canonical_bytes(plan["execution_permission"]) != canonical_bytes(PERMISSIONS)
            or utc_time(plan["frozen_at_utc"], aligned=False) >= utc_time(spec["first_cutoff"])):
        raise ValueError("forward_plan_authority_or_freeze_invalid")
    if any(plan[key] != value for key, value in _runtime().items()) or plan["strategy_hash"] != _strategy_hash(spec):
        raise ValueError("forward_frozen_source_environment_or_observer_mismatch")
    return plan


def _inputs(plan: dict, snapshot: DatasetSnapshot, cutoff: str) -> dict:
    cutoff_time = utc_time(cutoff)
    if cutoff != utc_text(cutoff_time):
        raise ValueError("forward_canonical_cutoff_seconds_required")
    if cutoff_time < utc_time(plan["spec"]["first_cutoff"]):
        raise ValueError("forward_cutoff_precedes_frozen_plan")
    document = verify_snapshot(snapshot.document)
    count = plan["spec"]["context_rows"]
    if (utc_time(document["end_exclusive"]) != cutoff_time
            or utc_time(document["as_of"], aligned=False) != cutoff_time
            or utc_time(document["start"]) != cutoff_time - count * HOUR
            or len(document["candles"]) != count
            or document["quality"]["rejected_uncompleted_rows"] != 0):
        raise ValueError("forward_exact_completed_context_required")
    # Older raw page rows may be outside the declared context. Future/current
    # bars are forbidden even when the snapshot projection would exclude them.
    for page in document["pages"]:
        raw = parse_document(base64.b64decode(page["raw_base64"], validate=True))
        if any(int(row[0]) >= int(cutoff_time.timestamp() * 1000) for row in raw["data"]):
            raise ValueError("forward_future_raw_row_rejected")
    if "csv_input" in document:
        raw_csv = base64.b64decode(document["csv_input"]["raw_base64"], validate=True).decode("utf-8-sig")
        if any(utc_time(row["time"]) >= cutoff_time for row in csv.DictReader(io.StringIO(raw_csv))):
            raise ValueError("forward_future_raw_row_rejected")
    retrieved = max(utc_time(item["retrieved_at"], aligned=False) for item in document["source_receipts"])
    return {"snapshot_id": document["snapshot_id"], "data_hash": document["data_hash"],
            "start": document["start"], "end_exclusive": document["end_exclusive"], "context_rows": count,
            "older_raw_rows_excluded": document["quality"]["excluded_outside_range_rows"],
            "input_available_at": utc_text(retrieved), "evidence_kind": document["evidence_kind"],
            "source_authentication": document["source_authentication"]}


def _time_check(plan: dict, inputs: dict, cutoff: str, recorded_at: str) -> float:
    now = utc_time(recorded_at, aligned=False)
    if now < utc_time(cutoff) or now < utc_time(plan["frozen_at_utc"], aligned=False):
        raise ValueError("forward_future_cutoff_or_freeze_rejected")
    if utc_time(inputs["input_available_at"], aligned=False) > now:
        raise ValueError("forward_input_retrieval_after_observation")
    return float((now - utc_time(cutoff)).total_seconds())


def _signal(plan: dict, snapshot: DatasetSnapshot) -> dict:
    strategy = build_strategy(**plan["spec"]["strategy"])
    portfolio = Portfolio(**plan["spec"]["reference_portfolio"])
    signal = strategy.generate_signal(snapshot.frame(), portfolio)
    return {**asdict(signal), "action": signal.action.value}


def _record(plan, inputs, signal, cutoff, recorded_at, backfill) -> dict:
    if type(backfill) is not bool:
        raise ValueError("forward_backfill_exact_bool_required")
    delay = _time_check(plan, inputs, cutoff, recorded_at)
    core = {"schema_version": "forward-observation-v1", "plan_hash": plan["plan_hash"],
            "cutoff": cutoff, "recorded_at_utc": recorded_at, "signal_available_at": recorded_at,
            "timing_status": "BACKFILL" if backfill else "ON_TIME" if delay <= 300 else "LATE",
            "backfill": backfill, "lateness_seconds": delay,
            "input": inputs, "input_hash": digest(inputs), "signal": signal, "output_hash": digest(signal),
            **{key: plan[key] for key in ("source_sha256", "environment_sha256", "observer_sha256", "strategy_hash")},
            "state_policy": STATE_POLICY, "reference_portfolio": plan["spec"]["reference_portfolio"],
            "position_state_observed": False, "execution_permission": dict(PERMISSIONS)}
    return {**core, "record_hash": digest(core)}


def replay(plan: dict, snapshot: DatasetSnapshot, observation: dict) -> dict:
    plan = _plan(plan)
    core = {key: value for key, value in observation.items() if key != "record_hash"}
    if observation.get("record_hash") != digest(core):
        raise ValueError("forward_observation_integrity_invalid")
    inputs = _inputs(plan, snapshot, observation["cutoff"])
    expected = _record(plan, inputs, _signal(plan, snapshot), observation["cutoff"],
                       observation["recorded_at_utc"], observation["backfill"])
    if canonical_bytes(observation) != canonical_bytes(expected):
        raise ValueError("forward_observation_replay_mismatch")
    return {"status": "VERIFIED", "record_hash": observation["record_hash"],
            "original_recorded_at_utc": observation["recorded_at_utc"],
            "original_timing_status": observation["timing_status"], "new_observation_created": False}


def observe(plan: dict, snapshot: DatasetSnapshot, cutoff: str, directory: str | Path, *, backfill=False) -> Path:
    plan = _plan(plan)
    inputs = _inputs(plan, snapshot, cutoff)
    _time_check(plan, inputs, cutoff, _now())
    identity = digest({"plan_hash": plan["plan_hash"], "cutoff": cutoff})
    destination = Path(directory) / f"forward_observation_{identity}.json"
    if destination.exists():
        existing = read_document(destination)
        try:
            if type(backfill) is not bool or existing["backfill"] is not backfill:
                raise ValueError("backfill_intent_changed")
            replay(plan, snapshot, existing)
        except (KeyError, ValueError, TypeError) as exc:
            raise FileExistsError("forward_existing_observation_conflict") from exc
        return destination
    signal = _signal(plan, snapshot)
    record = _record(plan, inputs, signal, cutoff, _now(), backfill)
    return Path(save_json_report(record, directory, "forward_observation", artifact_id=identity))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-plan")
    freeze.add_argument("--spec", type=Path, required=True)
    freeze.add_argument("--output-dir", type=Path, required=True)
    for name in ("observe", "replay"):
        sub = commands.add_parser(name)
        sub.add_argument("--plan", type=Path, required=True)
        sub.add_argument("--snapshot", type=Path, required=True)
        if name == "observe":
            sub.add_argument("--cutoff", required=True)
            sub.add_argument("--output-dir", type=Path, required=True)
            sub.add_argument("--backfill", action="store_true")
        else:
            sub.add_argument("--observation", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze-plan":
        output = {"plan": str(freeze_plan(read_document(args.spec), args.output_dir))}
    elif args.command == "observe":
        output = {"observation": str(observe(read_document(args.plan), load_snapshot(args.snapshot),
                                             args.cutoff, args.output_dir, backfill=args.backfill))}
    else:
        output = replay(read_document(args.plan), load_snapshot(args.snapshot), read_document(args.observation))
    print(json.dumps(output, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
