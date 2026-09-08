"""Sixteen frozen, paired continuous histories through the installed core.

Original reset-window diagnostics are read before new rules are run. No searches,
new matching logic, fee add-backs, account routes, or indicator changes occur.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time

import pandas as pd

from hakimi_research.dataset_registry import load_snapshot
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, ResearchReport, replay_report, verify_report
from hakimi_research.indicators import rsi
from hakimi_research.reporting import save_json_report
from run_continuous_study import calendar_slices, slice_result, reconcile_period_returns, frozen_write
from run_multiwindow_study import summarize_result, deny_network


SOURCE = "f657a07534061e7d03d2922b1fc1a69eeea04751a7a6201ac961ee55e76cf767"
OLD_SOURCE = "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5"
WHEEL = "78d6047c47f980ed0767e6ed52cd239b0ebd815327af19e9ce9f9e20a8cdfd89"
PLAN_HASH = "2115cde2317142d3511fae0b4e5a32fc1e136e110f2ceb70adfb4b0c863bd514"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def save(value, directory, prefix):
    return Path(save_json_report(value, directory, prefix, artifact_id=digest(value)))


def require_runtime():
    provenance = build_runtime_provenance()
    if (provenance["source_identity"].get("status") != "BUILD_VERIFIED"
            or provenance["source_identity"].get("content_sha256") != SOURCE
            or provenance["environment_verified"].get("status") != "VERIFIED"):
        raise ValueError("accepted_022_diagnostic_installed_runtime_required")
    return provenance


def validate_plan(plan):
    if digest(plan) != PLAN_HASH:
        raise ValueError("frozen_diagnostic_plan_identity_changed")
    expected = [
        {"label": "D0", "name": "dual_ma", "params": {"fast_window": 20, "slow_window": 60, "position_pct": .25, "stop_loss_pct": .03, "take_profit_pct": .08}, "spec_schema": "research-experiment-spec-v1"},
        {"label": "D1", "name": "dual_ma", "params": {"fast_window": 20, "slow_window": 60, "position_pct": .25, "stop_loss_pct": .03, "fixed_take_profit_policy": "DISABLED"}, "spec_schema": "research-experiment-spec-v2"},
        {"label": "R0", "name": "rsi", "params": {"window": 14, "oversold": 30, "overbought": 70, "position_pct": .25, "stop_loss_pct": .03}, "spec_schema": "research-experiment-spec-v1"},
        {"label": "R1", "name": "rsi", "params": {"window": 14, "oversold": 30, "overbought": 70, "position_pct": .25, "stop_loss_pct": .03, "oversold_entry_policy": "ONCE_PER_EVENT"}, "spec_schema": "research-experiment-spec-v2"},
    ]
    if (plan.get("schema_version") != "strategy-diagnostics-plan-v1" or plan.get("methods") != expected
            or plan.get("cost_factors") != [0, 1, 2, 3] or plan.get("mode") != "CONTINUOUS_HISTORY"
            or plan.get("score_start") != "2023-01-04T00:00:00Z" or plan.get("score_end") != "2026-09-01T00:00:00Z"
            or plan.get("initial_cash") != 10000 or plan.get("budget", {}).get("primary_trajectories") != 16):
        raise ValueError("frozen_four_configuration_sixteen_trajectory_budget_required")
    if any(plan.get(key) is not False for key in ("paper_allowed", "live_allowed", "order_allowed")):
        raise ValueError("execution_permissions_must_remain_false")
    return plan


def episode_diagnostics(report, data):
    """Whole-bar price envelopes, explicitly not executable excursions."""
    result = report["result"]
    orders = {o["order_id"]: o for o in result["orders"]}
    event_ids, current_id, active = {}, 0, False
    if report["spec"]["strategy"]["name"] == "rsi":
        for stamp, value in rsi(data["close"], 14).items():
            if math.isfinite(value) and value < 30:
                if not active:
                    current_id += 1
                active = True
                event_ids[pd.Timestamp(stamp)] = current_id
            elif math.isfinite(value):
                active = False
    episodes, current, last_stop, prior_stop_event = [], None, None, None
    reentry_count = reentry_24h = same_event_reentry = repeated_buys = 0
    exit_reasons = Counter()
    for fill in result["fills"]:
        stamp = pd.Timestamp(fill["fill_time"])
        if fill["action"] == "BUY":
            event = event_ids.get(pd.Timestamp(fill["signal_time"]))
            if fill["position_before"] > 0:
                repeated_buys += 1
            else:
                if last_stop is not None:
                    reentry_count += 1
                    reentry_24h += (stamp - last_stop).total_seconds() <= 24 * 3600
                    same_event_reentry += event is not None and event == prior_stop_event
                    last_stop = None
                current = {"entry_time": fill["fill_time"], "first_entry_price": fill["price"],
                           "entry_event": event, "buy_fills": 0, "exit_time": None, "exit_reason": None}
            current["buy_fills"] += 1
        elif fill["position_after"] == 0 and current is not None:
            reason = orders[fill["order_id"]]["reason"]
            current.update(exit_time=fill["fill_time"], exit_reason=reason)
            exit_reasons[reason] += 1
            if "stop" in reason:
                # The event known immediately before this protective bar may
                # differ from the first-entry event after later additions.
                last_stop = stamp
                prior_stop_event = event_ids.get(stamp - pd.Timedelta(hours=1))
            episodes.append(current)
            current = None
    if current is not None:
        episodes.append(current)
    for episode in episodes:
        end = pd.Timestamp(episode["exit_time"] or report["spec"]["score_end"])
        bars = data.loc[(data.index >= pd.Timestamp(episode["entry_time"])) & (data.index <= end)]
        reference = episode["first_entry_price"]
        episode["holding_hours_or_terminal_age"] = (end - pd.Timestamp(episode["entry_time"])).total_seconds() / 3600
        episode["whole_bar_favorable_envelope_pct"] = float(bars["high"].max()) / reference - 1
        episode["whole_bar_adverse_envelope_pct"] = float(bars["low"].min()) / reference - 1
    return {"exit_reasons": dict(exit_reasons), "episodes": episodes,
            "repeated_buy_fills_with_existing_position": repeated_buys,
            "first_reentries_after_stop": reentry_count, "first_reentries_within_24h_after_stop": reentry_24h,
            "reentries_in_same_continuous_oversold_event": same_event_reentry,
            "median_holding_hours_or_terminal_age": statistics.median(e["holding_hours_or_terminal_age"] for e in episodes) if episodes else None,
            "median_whole_bar_favorable_envelope_pct": statistics.median(e["whole_bar_favorable_envelope_pct"] for e in episodes) if episodes else None,
            "median_whole_bar_adverse_envelope_pct": statistics.median(e["whole_bar_adverse_envelope_pct"] for e in episodes) if episodes else None,
            "envelope_definition": "FULL_ENTRY_THROUGH_EXIT_BAR_HIGH_LOW_RELATIVE_TO_FIRST_FILL_PRICE_INCLUDES_UNOBSERVABLE_BEFORE_ENTRY_AFTER_EXIT_EXTREMES_NOT_EXECUTABLE_MFE_MAE",
            "holding_clock": "HOURLY_FILL_LABEL_DIFFERENCE_NOT_ACTUAL_INTRABAR_DURATION"}


def analyze_original(root, output):
    run = read_document(next((root / "artifacts/multiwindow-study-ci33969915599").glob("multiwindow_run_*.json")))
    rows, data_cache = [], {}
    selected = [a for a in run["attempts"] if a["method"] in {"dual_ma", "rsi"} and a["cost_factor"] == 1]
    selected.append(next(a for a in run["attempts"] if a["method"] == "cash" and a["cost_factor"] == 1))
    for attempt in selected:
        report = verify_report(read_document(attempt["report_path"]))
        if report["evidence"]["source_identity"]["content_sha256"] != OLD_SOURCE:
            raise ValueError("original_report_source_identity_changed")
        path = attempt["snapshot_path"]
        if path not in data_cache:
            data_cache[path] = load_snapshot(path).frame()
        rows.append({"window_id": attempt["window_id"], "method": attempt["method"], "cost_factor": 1,
                     "report_file_sha256": sha(attempt["report_path"]), **summarize_result(report),
                     **episode_diagnostics(report, data_cache[path])})
    selections = []
    for method in ("dual_ma", "rsi"):
        group = [r for r in rows if r["method"] == method]
        for criterion, predicate in (("LOSS", lambda r: r["net_pnl"] < 0), ("PROFIT", lambda r: r["net_pnl"] > 0),
                                     ("NO_FILL", lambda r: r["fill_count"] == 0),
                                     ("PROTECTIVE_BOUNDARY", lambda r: any("stop" in key for key in r["exit_reasons"]))):
            candidate = next((r for r in group if predicate(r)), None)
            selections.append({"method": method, "criterion": criterion, "selection_policy": "FIRST_CHRONOLOGICAL_MATCH_NOT_WORST_WINDOW",
                               "window_id": candidate["window_id"] if candidate else None,
                               "report_hash": candidate["report_hash"] if candidate else None,
                               "status": "AVAILABLE" if candidate else "NO_MATCH_IN_FULL_BASELINE_MATRIX"})
    payload = {"schema_version": "strategy-original-failure-diagnostics-v1", "analyzed_at": now(),
               "scope": "ALL_32_BASELINE_NORMAL_COST_RESET_STRATEGY_REPORTS_AND_ONE_CASH_NO_FILL_CONTROL",
               "variant_results_available": False, "original_source_content_sha256": OLD_SOURCE,
               "rows": rows, "samples": selections, "all_negative_results_retained": True,
               "limitation": "OHLC envelopes include unknown pre-entry/post-exit prices. They are descriptive, not obtainable PnL or event ordering."}
    frozen_write(output / "original-analysis.json", payload)
    return {"original_analysis": str((output / "original-analysis.json").resolve()), "report_count": len(rows)}


def make_spec(plan, snapshot, method, factor):
    return ExperimentSpec.from_document({"schema_version": method["spec_schema"],
        "name": f"diagnostic-continuous-{method['label']}-cost-{factor}x", "snapshot_id": snapshot.snapshot_id,
        "strategy": {"name": method["name"], "params": method["params"]},
        "score_start": plan["score_start"], "score_end": plan["score_end"], "initial_cash": plan["initial_cash"],
        "fee_rate": plan["fee_rate"] * factor, "slippage_pct": plan["slippage_pct"] * factor, "risk": plan["risk"],
        "end_policy": "MARK_TO_MARKET", "purpose": "DESCRIPTIVE_FIXED_PARAMETERS", "execution_policy": "STANDARD_STRATEGY_RISK"})


def validate_manifest(manifest, *, partial=False):
    """Labels do not establish identity: bind every row to the frozen matrix."""
    if manifest.get("schema_version") != "strategy-diagnostics-run-v1":
        raise ValueError("diagnostic_run_schema_invalid")
    plan = validate_plan(manifest.get("plan"))
    if manifest.get("plan_hash") != digest(plan) or manifest.get("source_content_sha256") != SOURCE or manifest.get("wheel_sha256") != WHEEL:
        raise ValueError("diagnostic_run_plan_source_or_wheel_mismatch")
    expected = {(m["label"], cost) for m in plan["methods"] for cost in plan["cost_factors"]}
    cells = manifest.get("cells")
    if type(cells) is not list or not cells or (not partial and len(cells) != 16):
        raise ValueError("diagnostic_run_cell_count_invalid")
    keys = []
    for cell in cells:
        if type(cell) is not dict or type(cell.get("method")) is not str or type(cell.get("cost_factor")) is not int:
            raise ValueError("diagnostic_cell_key_exact_types_required")
        key = cell["method"], cell["cost_factor"]
        if key not in expected:
            raise ValueError("diagnostic_cell_outside_frozen_matrix")
        if (cell.get("status") != "COMPLETED" or cell.get("source_content_sha256") != SOURCE
                or cell.get("wheel_sha256") != WHEEL or cell.get("plan_hash") != digest(plan)):
            raise ValueError("diagnostic_cell_status_or_identity_invalid")
        keys.append(key)
    if len(set(keys)) != len(keys) or (not partial and set(keys) != expected):
        raise ValueError("diagnostic_cells_not_exact_unique_matrix")
    for field in ("snapshot_path", "snapshot_file_sha256"):
        if any(type(c.get(field)) is not str or not c[field] for c in cells) or len({c[field] for c in cells}) != 1:
            raise ValueError("diagnostic_cells_do_not_share_exact_snapshot_identity")
    return plan, dict(zip(keys, cells))


def bound_snapshot(manifest, plan):
    cell = manifest["cells"][0]
    if sha(cell["snapshot_path"]) != cell["snapshot_file_sha256"]:
        raise ValueError("diagnostic_snapshot_bytes_changed")
    snapshot = load_snapshot(cell["snapshot_path"])
    if snapshot.document["start"] != plan["input_start"] or snapshot.document["end_exclusive"] != plan["input_end_exclusive"]:
        raise ValueError("diagnostic_snapshot_bounds_changed")
    return snapshot


def bound_report(cell, plan, snapshot):
    if sha(cell["report_path"]) != cell["report_file_sha256"]:
        raise ValueError("diagnostic_report_bytes_changed")
    report = verify_report(read_document(cell["report_path"]))
    method = next(m for m in plan["methods"] if m["label"] == cell["method"])
    expected = make_spec(plan, snapshot, method, cell["cost_factor"]).document
    if (report["report_hash"] != cell["report_hash"] or canonical_bytes(report["spec"]) != canonical_bytes(expected)
            or canonical_bytes(read_document(cell["spec_path"])) != canonical_bytes(expected)
            or report["evidence"]["source_identity"].get("status") != "BUILD_VERIFIED"
            or report["evidence"]["source_identity"].get("content_sha256") != SOURCE
            or report["evidence"]["environment_verified"].get("status") != "VERIFIED"):
        raise ValueError("diagnostic_report_spec_or_runtime_binding_failed")
    return report


def replay_matrix(summary, manifest, cells):
    if (summary.get("schema_version") != "strategy-diagnostics-replay-v1" or summary.get("plan_hash") != manifest["plan_hash"]
            or summary.get("source_content_sha256") != SOURCE or type(summary.get("verified")) is not int
            or summary["verified"] != 16 or type(summary.get("planned")) is not int or summary["planned"] != 16):
        raise ValueError("full_matching_replay_receipt_required")
    receipts = summary.get("receipts")
    if type(receipts) is not list or len(receipts) != 16:
        raise ValueError("diagnostic_replay_count_invalid")
    keys = []
    for receipt in receipts:
        if type(receipt.get("method")) is not str or type(receipt.get("cost_factor")) is not int:
            raise ValueError("diagnostic_replay_key_exact_types_required")
        keys.append((receipt["method"], receipt["cost_factor"]))
        if type(receipt.get("ledger", {}).get("checks")) is not int or receipt["ledger"]["checks"] <= 0:
            raise ValueError("diagnostic_replay_ledger_count_invalid")
    if len(set(keys)) != 16 or set(keys) != set(cells):
        raise ValueError("diagnostic_replay_matrix_mismatch")
    if type(summary.get("independent_ledger_checks")) is not int or summary["independent_ledger_checks"] != sum(r["ledger"]["checks"] for r in receipts):
        raise ValueError("diagnostic_replay_ledger_sum_mismatch")
    return dict(zip(keys, receipts))


def bound_replay_receipt(receipt, cell, report, snapshot):
    replayed, audit = receipt["replay"], receipt["ledger"]
    if (replayed.get("receipt_hash") != digest({k: v for k, v in replayed.items() if k != "receipt_hash"})
            or any(replayed.get(key) is not True for key in ("result_matches", "source_matches", "environment_verified", "replay_verified"))
            or replayed.get("original_report_hash") != report["report_hash"]
            or replayed.get("original_result_hash") != report["result_hash"]
            or replayed.get("replayed_result_hash") != report["result_hash"]
            or canonical_bytes(replayed.get("execution_permission")) != canonical_bytes(report["execution_permission"])
            or replayed.get("snapshot_id") != snapshot.snapshot_id
            or replayed.get("replay_provenance", {}).get("source_identity", {}).get("content_sha256") != SOURCE
            or replayed.get("replay_provenance", {}).get("source_identity", {}).get("status") != "BUILD_VERIFIED"
            or replayed.get("replay_provenance", {}).get("environment_verified", {}).get("status") != "VERIFIED"
            or receipt.get("report_file_sha256") != cell["report_file_sha256"]
            or audit.get("status") != "PASS" or audit.get("failures") != []
            or audit.get("report_hash") != report["report_hash"] or audit.get("snapshot_id") != snapshot.snapshot_id):
        raise ValueError("diagnostic_replay_report_or_runtime_binding_failed")


def public_replay_projection(summary, original_summary_file_sha256):
    """Derive a separately sealed public view; never mutate canonical receipts."""
    public = json.loads(canonical_bytes(summary))
    for receipt in public["receipts"]:
        replayed = receipt["replay"]
        replayed["original_receipt_hash"] = replayed.pop("receipt_hash")
        replayed["schema_version"] = "research-replay-public-projection-v1"
        replayed["replay_provenance"].pop("machine_receipt", None)
        replayed["projection_hash"] = digest(replayed)
    public["schema_version"] = "strategy-diagnostics-replay-public-v1"
    public["original_summary_file_sha256"] = original_summary_file_sha256
    public["privacy"] = "MACHINE_RECEIPT_OMITTED_ORIGINAL_IDENTITIES_REFERENCED_SEPARATE_PUBLIC_PROJECTION"
    encoded = canonical_bytes(public).decode("utf-8")
    if '"machine_receipt"' in encoded or re.search(r"[A-Za-z]:[\\/]|/(?:Users|home|tmp)/", encoded):
        raise ValueError("public_replay_contains_machine_identity_or_absolute_path")
    public["projection_hash"] = digest(public)
    return public


def audit_behavior(report, data, end):
    """Check decisions on the known development prefix before reading metrics."""
    strategy = report["spec"]["strategy"]
    signals = [s for s in report["result"]["signals"] if pd.Timestamp(s["time"]) < pd.Timestamp(end)]
    checks, intents = 0, 0
    if strategy["params"].get("fixed_take_profit_policy") == "DISABLED":
        for signal in signals:
            if signal["action"] == "BUY":
                if signal["requested_take_profit_pct"] is not None or signal["requested_stop_loss_pct"] != .03:
                    raise ValueError("disabled_target_or_retained_stop_semantics_failed")
                checks += 1
                intents += 1
        if any("take profit" in order["reason"] for order in report["result"]["orders"] if pd.Timestamp(order["bar_time"]) < pd.Timestamp(end)):
            raise ValueError("disabled_target_still_executed")
    elif strategy["params"].get("oversold_entry_policy") == "ONCE_PER_EVENT":
        values = rsi(data["close"], 14)
        consumed = False
        for signal in signals:
            value = values.loc[pd.Timestamp(signal["time"])]
            if math.isfinite(value) and value >= 30:
                consumed = False
            expected_buy = math.isfinite(value) and value < 30 and not consumed
            if (signal["action"] == "BUY") != expected_buy:
                raise ValueError("one_intent_per_observed_event_semantics_failed")
            if expected_buy:
                consumed = True
                intents += 1
            checks += 1
    return {"status": "PASS", "score_end_exclusive": end, "decisions_inspected": len(signals),
            "policy_checks": checks, "entry_intents": intents,
            "scope": "EXISTING_CANONICAL_REPORT_CAUSAL_PREFIX_NO_EXTRA_RESEARCH_RUN_OR_RULE_SELECTION"}


def run(plan_path, snapshot_path, original_path, output):
    require_runtime()
    plan, original = validate_plan(read_document(plan_path)), read_document(original_path)
    if original.get("variant_results_available") is not False or len(original.get("rows", [])) != 33:
        raise ValueError("completed_prevariant_original_diagnostics_required")
    snapshot = load_snapshot(snapshot_path)
    if snapshot.document["start"] != plan["input_start"] or snapshot.document["end_exclusive"] != plan["input_end_exclusive"]:
        raise ValueError("exact_full_continuous_input_required")
    receipts = []
    for method in plan["methods"]:
        for factor in plan["cost_factors"]:
            key, started = f"{method['label']}-{factor}x", now()
            path = output / "cells" / f"{key}.json"
            spec = make_spec(plan, snapshot, method, factor)
            if path.exists():
                cell = read_document(path)
                report = verify_report(read_document(cell["report_path"]))
                if cell["plan_hash"] != digest(plan) or sha(cell["report_path"]) != cell["report_file_sha256"] or report["spec"] != spec.document:
                    raise ValueError("frozen_cell_conflicts")
                receipts.append(cell)
                continue
            attempt_path = output / "attempts" / f"{key}-{time.time_ns()}.json"
            print(json.dumps({"event": "STARTED", "cell": key, "at": started}), flush=True)
            clock = time.perf_counter()
            try:
                report = ExperimentRunner().run(snapshot, spec)
                report_path = report.save(output / "reports")
                spec_path = save(spec.document, output / "specs", "spec")
                cell = {"method": method["label"], "cost_factor": factor, "status": "COMPLETED", "started_at": started,
                        "ended_at": now(), "elapsed_seconds": time.perf_counter() - clock, "plan_hash": digest(plan),
                        "snapshot_path": str(snapshot_path.resolve()), "snapshot_file_sha256": sha(snapshot_path),
                        "report_path": str(report_path.resolve()), "report_hash": report.document["report_hash"],
                        "report_file_sha256": sha(report_path), "spec_path": str(spec_path.resolve()),
                        "source_content_sha256": SOURCE, "wheel_sha256": WHEEL}
                frozen_write(path, cell)
                frozen_write(attempt_path, cell)
                receipts.append(cell)
                print(json.dumps({"event": "COMPLETED", "cell": key, "elapsed_seconds": cell["elapsed_seconds"]}), flush=True)
            except Exception as error:
                frozen_write(attempt_path, {"method": method["label"], "cost_factor": factor, "status": "FAILED",
                    "started_at": started, "ended_at": now(), "plan_hash": digest(plan), "error_type": type(error).__name__, "error": str(error)})
                raise
    manifest = {"schema_version": "strategy-diagnostics-run-v1", "plan_hash": digest(plan), "plan": plan,
                "original_analysis_file_sha256": sha(original_path), "cells": receipts,
                "source_content_sha256": SOURCE, "wheel_sha256": WHEEL, "tool_sha256": sha(__file__)}
    frozen_write(output / "run.json", manifest)
    return {"completed": len(receipts), "run": str((output / "run.json").resolve())}


def replay(root, run_path, output, *, available_plan=None):
    require_runtime()
    if available_plan is not None:
        plan = validate_plan(read_document(available_plan))
        expected = [(m["label"], c) for m in plan["methods"] for c in plan["cost_factors"]]
        cells = [read_document(run_path / f"{m}-{c}x.json") for m, c in expected if (run_path / f"{m}-{c}x.json").is_file()]
        if not cells or any(cell["plan_hash"] != digest(plan) for cell in cells):
            raise ValueError("available_cells_must_match_frozen_full_budget")
        manifest = {"schema_version": "strategy-diagnostics-run-v1", "cells": cells, "plan": plan,
                    "plan_hash": digest(plan), "source_content_sha256": SOURCE, "wheel_sha256": WHEEL}
    else:
        manifest = read_document(run_path)
    plan, cell_map = validate_manifest(manifest, partial=available_plan is not None)
    ledger_path = root / "scripts/reconcile_research_ledger.py"
    module_spec = importlib.util.spec_from_file_location("diagnostic_independent_ledger", ledger_path)
    ledger = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(ledger)
    snapshot = bound_snapshot(manifest, plan)
    receipts = []
    if available_plan is None and len(manifest["cells"]) != 16:
        raise ValueError("complete_sixteen_cell_matrix_required")
    for cell in manifest["cells"]:
        key = f"{cell['method']}-{cell['cost_factor']}x"
        receipt_path = output / "receipts" / f"{key}.json"
        if sha(cell["report_path"]) != cell["report_file_sha256"]:
            raise ValueError("original_report_bytes_changed")
        report = bound_report(cell, plan, snapshot)
        if receipt_path.exists():
            receipt = read_document(receipt_path)
            if receipt["replay"]["original_report_hash"] != report["report_hash"] or receipt["ledger"]["status"] != "PASS" or not receipt["replay"]["replay_verified"]:
                raise ValueError("existing_replay_receipt_conflicts")
            recorded_replay = receipt["replay"]
            if (recorded_replay["receipt_hash"] != digest({k: v for k, v in recorded_replay.items() if k != "receipt_hash"})
                    or recorded_replay["original_result_hash"] != report["result_hash"]
                    or recorded_replay["snapshot_id"] != snapshot.snapshot_id
                    or recorded_replay["replay_provenance"]["source_identity"]["content_sha256"] != SOURCE
                    or receipt["report_file_sha256"] != cell["report_file_sha256"]
                    or canonical_bytes(receipt["ledger"]) != canonical_bytes(ledger.reconcile(report, snapshot.document))):
                raise ValueError("existing_replay_identity_or_ledger_changed")
        else:
            print(json.dumps({"event": "REPLAY_STARTED", "cell": key}), flush=True)
            verified = replay_report(snapshot, ResearchReport(report))
            audit = ledger.reconcile(report, snapshot.document)
            if not verified["replay_verified"] or audit["status"] != "PASS":
                raise ValueError("canonical_replay_or_independent_ledger_failed")
            receipt = {"method": cell["method"], "cost_factor": cell["cost_factor"], "replay": verified, "ledger": audit,
                       "report_file_sha256": sha(cell["report_path"]), "ledger_tool_sha256": sha(ledger_path)}
            frozen_write(receipt_path, receipt)
        bound_replay_receipt(receipt, cell, report, snapshot)
        receipts.append(receipt)
        print(json.dumps({"event": "REPLAY_VERIFIED", "cell": key, "ledger_checks": receipt["ledger"]["checks"]}), flush=True)
    summary = {"schema_version": "strategy-diagnostics-replay-v1", "plan_hash": manifest["plan_hash"],
               "verified": len(receipts), "planned": 16, "independent_ledger_checks": sum(r["ledger"]["checks"] for r in receipts),
               "receipts": receipts, "source_content_sha256": SOURCE}
    if len(receipts) == 16:
        receipt_path = output / "replay-summary.json"
        frozen_write(receipt_path, summary)
    else:
        receipt_path = save(summary, output, "partial-replay")
    return {"verified": len(receipts), "planned": 16, "ledger_checks": summary["independent_ledger_checks"], "receipt": str(receipt_path.resolve())}


def publish(root, run_path, replay_path, output):
    manifest, replay_summary = read_document(run_path), read_document(replay_path)
    plan, cells = validate_manifest(manifest)
    replay_receipts = replay_matrix(replay_summary, manifest, cells)
    snapshot = bound_snapshot(manifest, plan)
    rows, economic_equal = [], []
    data = snapshot.frame()
    for cell in manifest["cells"]:
        report = bound_report(cell, plan, snapshot)
        bound_replay_receipt(replay_receipts[(cell["method"], cell["cost_factor"])], cell, report, snapshot)
        if sha(cell["report_path"]) != cell["report_file_sha256"]:
            raise ValueError("canonical_report_bytes_changed")
        behavior = {"development_history_first": audit_behavior(report, data, "2025-01-01T00:00:00Z"),
                    "full_history_after_development": audit_behavior(report, data, plan["score_end"])}
        result = report["result"]
        monthly = calendar_slices(report, 1)
        periods = [slice_result(report, w["score_start"], w["score_end"], w["window_id"]) for w in plan["periods"]]
        whole = slice_result(report, plan["score_start"], plan["score_end"], "FULL_CONTINUOUS_HISTORY")
        positive = sorted((p["net_pnl"] for p in monthly if p["net_pnl"] > 0), reverse=True)
        refs = {}
        if cell["cost_factor"] != 0:
            for label in ("cash", "buy_hold_25pct"):
                reference_cell = read_document(root / "artifacts/continuous-history-20260906/cells" / f"{label}-{cell['cost_factor']}x.json")
                reference = verify_report(read_document(reference_cell["report_path"]))
                refs[label] = {"report_hash": reference["report_hash"], "report_file_sha256": sha(reference_cell["report_path"]),
                               "total_return": reference["result"]["total_return"], "cost_factor": cell["cost_factor"],
                               "source_content_sha256": reference["evidence"]["source_identity"]["content_sha256"],
                               "score_start": reference["spec"]["score_start"], "score_end": reference["spec"]["score_end"]}
        row = {"method": cell["method"], "cost_factor": cell["cost_factor"], "status": "COMPLETED",
               **summarize_result(report), **whole, "round_trip_count": result["round_trip_count"],
               "source_content_sha256": SOURCE, "report_file_sha256": cell["report_file_sha256"],
               "turnover_notional_over_initial_cash": whole["turnover_notional"] / plan["initial_cash"],
               "top_three_positive_month_pnl_share": sum(positive[:3]) / sum(positive) if positive else None,
               "positive_month_count": len(positive), "losing_month_count": sum(p["net_pnl"] < 0 for p in monthly),
               "periods": periods, "monthly": monthly, "reference_reports": refs,
               "return_minus_cash": result["total_return"],
               "return_minus_buy_hold_25pct": result["total_return"] - refs["buy_hold_25pct"]["total_return"] if refs else None,
               "zero_cost_reference_limitation": "NO_CANONICAL_SAME_COST_BUY_HOLD_REPORT" if not refs else None,
               "behavior_checks": behavior,
               "period_reconciliation": {"monthly": reconcile_period_returns(monthly, result), "old_reset_intervals": reconcile_period_returns(periods, result)}}
        projection = {"schema_version": "strategy-diagnostics-trace-projection-v1", "mode": "CONTINUOUS_HISTORY",
                      "plan_hash": manifest["plan_hash"], "spec": report["spec"], "dataset": report["dataset"],
                      "strategy_spec": report["strategy_spec"], "metrics": {k: v for k, v in row.items() if k not in {"periods", "monthly"}},
                      "monthly": monthly, "periods": periods, "orders": result["orders"], "fills": result["fills"],
                      "round_trips": result["round_trips"], "accounting": result["accounting"],
                      "equity_curve_hash": digest(result["equity_curve"]), "signals_hash": digest(result["signals"]),
                      "report_hash": report["report_hash"], "report_file_sha256": cell["report_file_sha256"],
                      "source_identity": report["evidence"]["source_identity"], "execution_permission": report["execution_permission"]}
        projection_path = save(projection, output / "traces", "trace")
        row["projection_file"] = projection_path.relative_to(output).as_posix()
        row["projection_file_sha256"] = sha(projection_path)
        if cell["method"] in {"D0", "R0"} and cell["cost_factor"] != 0:
            label = "dual_ma" if cell["method"] == "D0" else "rsi"
            old_cell = read_document(root / "artifacts/continuous-history-20260906/cells" / f"{label}-{cell['cost_factor']}x.json")
            old = verify_report(read_document(old_cell["report_path"]))
            fields = [k for k in result if k != "reproducibility"]
            equal = {k: canonical_bytes(result[k]) == canonical_bytes(old["result"][k]) for k in fields}
            if not all(equal.values()):
                raise ValueError("unchanged_strategy_economic_baseline_diverged:" + str([k for k, v in equal.items() if not v]))
            economic_equal.append({"method": cell["method"], "cost_factor": cell["cost_factor"],
                                  "old_report_hash": old["report_hash"], "new_report_hash": report["report_hash"],
                                  "compared_fields": fields, "all_equal": True,
                                  "excluded_identity": "REPRODUCIBILITY_CONTAINS_EXPECTED_CHANGED_STRATEGY_CLASS_SOURCE_FINGERPRINT"})
        rows.append(row)
    by_key = {(r["method"], r["cost_factor"]): r for r in rows}
    for row in rows:
        normal = by_key[(row["method"], 1)]
        row["cost_change_from_normal"] = {key: row[key] - normal[key] for key in
            ("total_return", "total_fees", "fee_plus_slippage_cost", "turnover_notional_over_initial_cash", "fill_count", "duration_weighted_close_exposure")}
        baseline_label = {"D1": "D0", "R1": "R0"}.get(row["method"])
        row["paired_change"] = None
        if baseline_label:
            baseline = by_key[(baseline_label, row["cost_factor"])]
            fields = ("total_return", "max_drawdown", "max_drawdown_duration_hours", "duration_weighted_close_exposure",
                      "total_fees", "fee_plus_slippage_cost", "turnover_notional_over_initial_cash", "fill_count", "round_trip_count")
            row["paired_change"] = {"baseline": baseline_label, "baseline_report_hash": baseline["report_hash"],
                                    **{key: row[key] - baseline[key] for key in fields},
                                    "periods": [{"slice_id": a["slice_id"], "return_difference": a["total_return"] - b["total_return"],
                                                 "exposure_difference": a["duration_weighted_close_exposure"] - b["duration_weighted_close_exposure"],
                                                 "pnl_difference": a["net_pnl"] - b["net_pnl"]} for a, b in zip(row["periods"], baseline["periods"])]}
    lineage_path = next((root / "docs/research-evidence/continuous-history-20260906").glob("input_derivation_*.json"))
    lineage = read_document(lineage_path)
    if lineage["snapshot_file_sha256"] != manifest["cells"][0]["snapshot_file_sha256"] or lineage["canonical_values_changed"] is not False:
        raise ValueError("shared_continuous_input_lineage_mismatch")
    original_replay_sha = sha(replay_path)
    public_replay = public_replay_projection(replay_summary, original_replay_sha)
    frozen_write(output / "replay-summary.json", public_replay)
    summary = {"schema_version": "strategy-diagnostics-summary-v1", "mode": "CONTINUOUS_HISTORY", "plan": plan,
               "plan_hash": manifest["plan_hash"], "planned_cells": 16, "completed_cells": len(rows), "rows": rows,
               "baseline_021_economic_equivalence": economic_equal, "source_content_sha256": SOURCE, "wheel_sha256": WHEEL,
               "input_lineage": {"file_relative_to_repository": lineage_path.relative_to(root).as_posix(),
                                 "file_sha256": sha(lineage_path), "snapshot_id": lineage["snapshot_id"],
                                 "snapshot_file_sha256": lineage["snapshot_file_sha256"], "source_kind": lineage["source_kind"]},
               "replay": {"verified": 16, "receipt_file_sha256": sha(output / "replay-summary.json"),
                          "receipt_scope": "SANITIZED_PUBLIC_PROJECTION_NOT_CANONICAL_ORIGINAL",
                          "original_private_receipt_file_sha256": original_replay_sha,
                          "independent_ledger_checks": replay_summary["independent_ledger_checks"]},
               "all_negative_results_retained": True, "zero_cost_is_diagnostic_only": True, "history_previously_viewed": True,
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    frozen_write(output / "summary.json", summary)
    return {"summary": str((output / "summary.json").resolve()), "completed": len(rows), "baseline_equivalences": len(economic_equal)}


if __name__ == "__main__":
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    original = sub.add_parser("analyze-original")
    original.add_argument("--root", type=Path, required=True)
    original.add_argument("--output-dir", type=Path, required=True)
    research = sub.add_parser("run")
    research.add_argument("--plan", type=Path, required=True)
    research.add_argument("--snapshot", type=Path, required=True)
    research.add_argument("--original-analysis", type=Path, required=True)
    research.add_argument("--output-dir", type=Path, required=True)
    check = sub.add_parser("replay")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--run", type=Path, required=True)
    check.add_argument("--available-plan", type=Path, help="Bounded replay of currently completed cells in --run directory; reuse receipts when final full manifest arrives.")
    check.add_argument("--output-dir", type=Path, required=True)
    view = sub.add_parser("publish")
    view.add_argument("--root", type=Path, required=True)
    view.add_argument("--run", type=Path, required=True)
    view.add_argument("--replay", type=Path, required=True)
    view.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "analyze-original":
        answer = analyze_original(args.root, args.output_dir)
    elif args.command == "run":
        answer = run(args.plan, args.snapshot, args.original_analysis, args.output_dir)
    elif args.command == "replay":
        answer = replay(args.root, args.run, args.output_dir, available_plan=args.available_plan)
    else:
        answer = publish(args.root, args.run, args.replay, args.output_dir)
    print(json.dumps(answer, ensure_ascii=False))
