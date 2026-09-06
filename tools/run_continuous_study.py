"""One canonical Runner call per continuous historical trajectory; no new engine.

Freeze and verify the plan before running. Parent OKX captures remain unchanged;
the joined input is an honestly labelled derived CSV with an external lineage
receipt, because editing overlapping raw HTTP pages would misstate provenance.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import time

from hakimi_research.dataset_registry import build_csv_snapshot, load_snapshot, save_snapshot, utc_time
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.environment import build_runtime_provenance
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, ResearchReport, replay_report, verify_report
from hakimi_research.reporting import save_json_report

SOURCE = "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5"
WHEEL = "b93952ddee0d16424292e75e5a3e7b0dfe10ac06d12f1333fa276922d08649fb"


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("continuous_history_offline_network_denied")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_runtime():
    provenance = build_runtime_provenance()
    if (provenance["source_identity"].get("status") != "BUILD_VERIFIED"
            or provenance["source_identity"].get("content_sha256") != SOURCE
            or provenance["environment_verified"].get("status") != "VERIFIED"):
        raise ValueError("accepted_021_installed_runtime_required")
    return provenance


def save(value, directory, prefix):
    return Path(save_json_report(value, directory, prefix, artifact_id=digest(value)))


def frozen_write(path, value):
    """Creation is exclusive; an identical retry is harmless, a changed plan fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with path.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError:
        if path.read_bytes() != encoded:
            raise ValueError("existing_frozen_document_differs")


def validate_plan(plan):
    if (plan.get("schema_version") != "continuous-history-plan-v1"
            or plan.get("mode") != "CONTINUOUS_HISTORY"
            or plan.get("score_start") != "2023-01-04T00:00:00Z"
            or plan.get("score_end") != "2026-09-01T00:00:00Z"
            or plan.get("initial_cash") != 10000
            or plan.get("initialization_count") != 1
            or plan.get("cost_factors") != [1, 2, 3]
            or plan.get("planned_trajectories") != 15
            or plan.get("source_content_sha256") != SOURCE
            or len(plan.get("parents", [])) != 16
            or plan.get("chunking") != "NONE_ONE_FULL_RUNNER_CALL_PER_TRAJECTORY"):
        raise ValueError("fixed_continuous_history_plan_required")
    expected = {"research_only": True, "paper_allowed": False, "live_allowed": False,
                "order_allowed": False, "parameter_selection": False, "confirmation_evaluation": False}
    if any(plan.get(key) is not value for key, value in expected.items()):
        raise ValueError("continuous_research_only_locks_required")
    if [m["label"] for m in plan["methods"]] != ["cash", "buy_hold_full", "buy_hold_25pct", "dual_ma", "rsi"]:
        raise ValueError("five_fixed_methods_required")
    return plan


def require_frozen_plan(plan_path, output):
    plan = validate_plan(read_document(plan_path))
    receipts = [read_document(p) for p in output.glob("plan_freeze_*.json")]
    matching = [r for r in receipts if r.get("plan_hash") == digest(plan)]
    if (len(matching) != 1 or matching[0].get("plan_file_sha256") != sha(plan_path)
            or matching[0].get("results_existed_at_freeze") is not False):
        raise ValueError("unchanged_prefrozen_plan_receipt_required")
    return plan


def require_bound_input(plan_path, snapshot_path, output):
    plan = require_frozen_plan(plan_path, output)
    receipts = [read_document(p) for p in output.glob("input_derivation_*.json")]
    matching = [r for r in receipts if r.get("plan_hash") == digest(plan)]
    if len(matching) != 1:
        raise ValueError("single_bound_input_derivation_required")
    receipt = matching[0]
    if receipt.get("snapshot_file_sha256") != sha(snapshot_path):
        raise ValueError("continuous_bound_input_file_changed")
    snapshot = load_snapshot(snapshot_path)
    document = snapshot.document
    expected = {"parents": plan["parents"], "parent_count": 16, "input_hours": 32136,
                "equal_overlap_rows": 1080, "scored_hours": 32064, "gaps": 0,
                "canonical_values_changed": False, "raw_http_pages_modified": False,
                "snapshot_id": snapshot.snapshot_id, "data_hash": document["data_hash"]}
    if (any(receipt.get(k) != value for k, value in expected.items())
            or document["start"] != plan["input_start"]
            or document["end_exclusive"] != plan["input_end_exclusive"]):
        raise ValueError("continuous_derivation_binding_mismatch")
    return plan, snapshot


def freeze(root, plan_path, output):
    require_runtime()
    if list(output.glob("plan_freeze_*.json")):
        existing = require_frozen_plan(plan_path, output)
        return {"plan_hash": digest(existing), "parents": len(existing["parents"]),
                "frozen_at": existing["frozen_at"], "existing_plan_preserved": True}
    if list((output / "cells").glob("*.json")):
        raise ValueError("cannot_claim_new_plan_freeze_after_results")
    prior_plan = read_document(root / "docs/studies/multiwindow-plan-20260905.json")
    old_run_path = next((root / "artifacts/multiwindow-study-ci33969915599").glob("multiwindow_run_*.json"))
    old_run = read_document(old_run_path)
    old_summary_path = Path(old_run["summary_path"])
    old_summary = read_document(old_summary_path)
    if digest(prior_plan) != old_run["plan_hash"] or digest(old_summary) != old_run["summary_hash"]:
        raise ValueError("original_reset_plan_or_summary_mismatch")
    parents = []
    for window in prior_plan["windows"]:
        attempts = [a for a in old_run["attempts"] if a["window_id"] == window["window_id"]]
        paths = {a["snapshot_path"] for a in attempts}
        if len(attempts) != 15 or len(paths) != 1 or any(a["status"] != "COMPLETED" for a in attempts):
            raise ValueError("complete_original_reset_inputs_required")
        path = Path(paths.pop())
        snapshot = load_snapshot(path).document
        if snapshot["evidence_kind"] != "PUBLIC_HTTP_CAPTURE":
            raise ValueError("original_public_capture_required")
        parents.append({"window_id": window["window_id"], "snapshot_id": snapshot["snapshot_id"],
                        "data_hash": snapshot["data_hash"], "file_sha256": sha(path),
                        "path_relative_to_repository": path.relative_to(root).as_posix(),
                        "start": snapshot["start"], "end_exclusive": snapshot["end_exclusive"],
                        "as_of": snapshot["as_of"],
                        "source_receipt_hashes": [r["source_receipt_hash"] for r in snapshot["source_receipts"]],
                        "retrieved_at_min": min(r["retrieved_at"] for r in snapshot["source_receipts"]),
                        "retrieved_at_max": max(r["retrieved_at"] for r in snapshot["source_receipts"])})
    created = (read_document(plan_path)["frozen_at"] if plan_path.exists()
               else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    plan = {**{k: prior_plan[k] for k in ("methods", "risk", "initial_cash", "fee_rate", "slippage_pct", "cost_factors",
              "input_start", "input_end_exclusive", "context_hours", "research_only", "paper_allowed", "live_allowed",
              "order_allowed", "parameter_selection", "confirmation_evaluation")},
            "schema_version": "continuous-history-plan-v1", "mode": "CONTINUOUS_HISTORY", "frozen_at": created,
            "score_start": prior_plan["windows"][0]["score_start"], "score_end": prior_plan["windows"][-1]["score_end"],
            "initialization_count": 1, "portfolio_initialization": "FLAT_10000_ONCE_AT_SCORE_START",
            "chunking": "NONE_ONE_FULL_RUNNER_CALL_PER_TRAJECTORY", "planned_trajectories": 15,
            "source_content_sha256": SOURCE, "accepted_windows_wheel_sha256": WHEEL,
            "accepted_ci_run": 33969915599, "accepted_checkout": "a6771ec89603999d55c6193a4fa7846ec3115d40",
            "reset_plan_hash": digest(prior_plan), "reset_summary_hash": digest(old_summary),
            "reset_run_file_sha256": sha(old_run_path), "parents": parents,
            "reset_comparison_windows": prior_plan["windows"],
            "context_policy": {"initial_context_rows": 72, "trading_in_context": False,
                "per_decision_history": "ENTIRE_INPUT_PREFIX_THROUGH_CURRENT_CLOSE",
                "sma": "UNCHANGED_FIXED_ROLLING_20_AND_60_SIMPLE_MEANS",
                "rsi": "UNCHANGED_14_SIMPLE_ROLLING_MEAN_GAINS_AND_LOSSES_NOT_WILDER",
                "recursive_indicators": "NONE_NO_TRUNCATION_OR_RESEEDING_POLICY_INTRODUCED"},
            "boundary_policy": "CALENDAR_SLICES_ARE_POSTHOC_ONLY_NO_CASH_POSITION_COST_PROTECTION_OR_PENDING_RESET",
            "daily_risk": "UNCHANGED_UTC_DAY_START_PREVIOUS_CLOSE_EQUITY_RESET_ONLY",
            "end_policy": "MARK_TO_MARKET_NO_FORCED_LIQUIDATION",
            "slice_policy": "MONTHS_QUARTERS_AND_EXACT_OLD_RESET_INTERVALS_FROM_SAME_CANONICAL_EQUITY_AND_FILLS",
            "return_reconciliation": "PRODUCT_OF_ADJACENT_BOUNDARY_EQUITY_RATIOS_EQUALS_FINAL_OVER_INITIAL",
            "source_derivation": "VERIFY_PARENT_RAW_BYTES_DEDUP_EQUAL_CANONICAL_ROWS_DERIVED_CSV_IMPORTED_UNVERIFIED",
            "all_history_status": "PREVIOUSLY_VIEWED_HISTORY_NO_NEW_BLIND_CONFIRMATION",
            "parameter_trials": 0, "optimization_applied": False}
    validate_plan(plan)
    frozen_write(plan_path, plan)
    save({"schema_version": "continuous-plan-freeze-receipt-v1", "plan_hash": digest(plan),
          "plan_file_sha256": sha(plan_path), "frozen_at": created,
          "results_existed_at_freeze": bool(list((output / "cells").glob("*.json"))),
          "source_content_sha256": SOURCE}, output, "plan_freeze")
    return {"plan_hash": digest(plan), "parents": len(parents), "frozen_at": created}


def merge_parent_rows(documents, start, end):
    rows, overlaps = {}, 0
    for document in documents:
        for row in document["candles"]:
            if row[0] in rows:
                if canonical_bytes(rows[row[0]]) != canonical_bytes(row):
                    raise ValueError("parent_overlap_values_differ")
                overlaps += 1
            else:
                rows[row[0]] = row
    selected = [rows[t] for t in sorted(rows) if start <= t < end]
    first, last = utc_time(start), utc_time(end)
    if len(selected) != int((last - first).total_seconds() / 3600):
        raise ValueError("combined_hourly_coverage_incomplete")
    for i, row in enumerate(selected):
        if utc_time(row[0]) != first + timedelta(hours=i):
            raise ValueError("combined_hourly_coverage_not_contiguous")
    return selected, overlaps


def combine(root, plan_path, output):
    require_runtime()
    plan = require_frozen_plan(plan_path, output)
    documents = []
    for parent in plan["parents"]:
        path = root / parent["path_relative_to_repository"]
        if sha(path) != parent["file_sha256"]:
            raise ValueError("parent_snapshot_file_changed")
        document = load_snapshot(path).document
        if document["snapshot_id"] != parent["snapshot_id"] or document["data_hash"] != parent["data_hash"]:
            raise ValueError("parent_snapshot_identity_changed")
        documents.append(document)
    rows, overlaps = merge_parent_rows(documents, plan["input_start"], plan["input_end_exclusive"])
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["time", "open", "high", "low", "close", "volume"])
    writer.writerows(rows)
    metadata = {"market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT", "timeframe": "1h",
                "source": "LOCAL_CANONICAL_JOIN_OF_VERIFIED_OKX_SNAPSHOTS_PLAN_" + digest(plan),
                "retrieved_at": max(p["retrieved_at_max"] for p in plan["parents"]),
                "as_of": plan["input_end_exclusive"], "volume_unit": "base_currency", "quote_unit": "USDT",
                "timezone": "UTC", "start": plan["input_start"], "end_exclusive": plan["input_end_exclusive"],
                "completed_bars_only": True}
    snapshot = build_csv_snapshot(stream.getvalue().encode("utf-8"), metadata)
    if canonical_bytes(snapshot.document["candles"]) != canonical_bytes(rows):
        raise ValueError("derived_csv_changed_canonical_market_values")
    path = save_snapshot(snapshot, output / "datasets")
    receipt = {"schema_version": "continuous-input-derivation-v1", "plan_hash": digest(plan),
               "snapshot_id": snapshot.snapshot_id, "data_hash": snapshot.document["data_hash"],
               "snapshot_file_sha256": sha(path), "parents": plan["parents"],
               "parent_count": len(documents), "input_hours": len(rows), "equal_overlap_rows": overlaps,
               "scored_hours": len(rows) - plan["context_hours"], "gaps": 0,
               "canonical_values_changed": False, "raw_http_pages_modified": False,
               "source_kind": "DERIVED_CSV_IMPORTED_UNVERIFIED_WITH_VERIFIED_LOCAL_PARENT_LINKS",
               "provider_truth": "NOT_CRYPTOGRAPHICALLY_AUTHENTICATED", "network_access": False}
    receipt_path = save(receipt, output, "input_derivation")
    return {"snapshot_path": str(path.resolve()), "receipt": str(receipt_path.resolve()), "snapshot_id": snapshot.snapshot_id}


def make_spec(plan, snapshot, method, factor):
    passive = method["name"] == "buy_and_hold"
    return ExperimentSpec.from_document({"schema_version": "research-experiment-spec-v1",
        "name": f"continuous-{method['label']}-cost-{factor}x", "snapshot_id": snapshot.snapshot_id,
        "strategy": {"name": method["name"], "params": method["params"]},
        "score_start": plan["score_start"], "score_end": plan["score_end"], "initial_cash": plan["initial_cash"],
        "fee_rate": plan["fee_rate"] * factor, "slippage_pct": plan["slippage_pct"] * factor,
        "risk": {**plan["risk"], **({"max_position_pct": 1, "min_cash_pct": 0} if passive else {})},
        "end_policy": "MARK_TO_MARKET", "purpose": "DESCRIPTIVE_FIXED_PARAMETERS",
        "execution_policy": "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET" if passive else "STANDARD_STRATEGY_RISK"})


def _dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def drawdown_stats(points):
    peak = points[0]["equity"]
    peak_time = _dt(points[0]["time"])
    maximum, longest = 0.0, 0.0
    underwater = False
    for point in points[1:]:
        value, now = point["equity"], _dt(point["time"])
        if value >= peak:
            if underwater:
                longest = max(longest, (now - peak_time).total_seconds() / 3600)
            peak, peak_time, underwater = value, now, False
        else:
            underwater = True
            maximum = max(maximum, 1 - value / peak)
            longest = max(longest, (now - peak_time).total_seconds() / 3600)
    return {"max_drawdown": maximum, "max_drawdown_duration_hours": longest,
            "terminal_underwater_hours": (_dt(points[-1]["time"]) - peak_time).total_seconds() / 3600
            if points[-1]["equity"] < peak else 0,
            "duration_policy": "ELAPSED_FROM_LAST_PEAK_TO_RECOVERY_OR_UNRECOVERED_END"}


def slice_result(report, start, end, label):
    """Measure existing ledger/equity only. Never submit an order or reset state."""
    result = report["result"]
    first, last = _dt(start), _dt(end)
    points = [p for p in result["equity_curve"] if first <= _dt(p["time"]) <= last]
    if not points or _dt(points[0]["time"]) != first or _dt(points[-1]["time"]) != last:
        raise ValueError("slice_requires_exact_existing_equity_boundaries")
    fills = [f for f in result["fills"] if first <= _dt(f["fill_time"]) < last]
    orders = {o["order_id"]: o for o in result["orders"]}
    fees = sum(f["fee"] for f in fills)
    slippage = sum(abs(f["price"] - orders[f["order_id"]]["reference_price"]) * f["quantity"] for f in fills)
    seconds = [(_dt(p["time"]) - _dt(previous["time"])).total_seconds() for previous, p in zip(points, points[1:])]
    if not seconds or any(s <= 0 for s in seconds) or any(p["equity"] <= 0 for p in points):
        raise ValueError("positive_equity_and_slice_duration_required")
    duration = sum(seconds)
    closed = [t for t in result["round_trips"] if first <= _dt(t["exit_time"]) < last]
    return {"slice_id": label, "score_start": start, "score_end": end,
            "opening_equity": points[0]["equity"], "closing_equity": points[-1]["equity"],
            "opening_cash": points[0]["cash"], "opening_position_qty": points[0]["position_qty"],
            "closing_cash": points[-1]["cash"], "closing_position_qty": points[-1]["position_qty"],
            "net_pnl": points[-1]["equity"] - points[0]["equity"],
            "total_return": points[-1]["equity"] / points[0]["equity"] - 1,
            **drawdown_stats(points), "drawdown_context": "SLICE_OPEN_EQUITY_PEAK_RESET_FOR_DESCRIPTOR_ONLY",
            "duration_weighted_close_exposure": sum(s * p["position_value"] / p["equity"] for s, p in zip(seconds, points[1:])) / duration,
            "duration_weighted_invested_close_fraction": sum(s * (p["position_qty"] > 0) for s, p in zip(seconds, points[1:])) / duration,
            "exposure_policy": "RECORDED_CLOSE_MARKS_NOT_OBSERVABLE_INTRABAR_EXPOSURE",
            "scored_hours": duration / 3600, "fill_count": len(fills), "closed_round_trips": len(closed),
            "total_fees": fees, "slippage_cost_vs_recorded_reference": slippage,
            "fee_plus_slippage_cost": fees + slippage,
            "turnover_notional": sum(f["price"] * f["quantity"] for f in fills),
            "fill_order_ids": [f["order_id"] for f in fills],
            "round_trip_ids_closed": [t["round_trip_id"] for t in closed],
            "trades_entered_before_slice_and_closed_inside": [t["round_trip_id"] for t in closed if _dt(t["entry_time"]) < first]}


def calendar_slices(report, months):
    start, end = _dt(report["spec"]["score_start"]), _dt(report["spec"]["score_end"])
    cursor, rows = start, []
    while cursor < end:
        month0 = ((cursor.month - 1) // months + 1) * months
        year, month0 = cursor.year + month0 // 12, month0 % 12
        boundary = min(datetime(year, month0 + 1, 1, tzinfo=timezone.utc), end)
        label = f"{cursor.year}-{cursor.month:02d}" if months == 1 else f"{cursor.year}-Q{(cursor.month - 1) // 3 + 1}"
        rows.append(slice_result(report, cursor.isoformat().replace("+00:00", "Z"), boundary.isoformat().replace("+00:00", "Z"), label))
        cursor = boundary
    return rows


def reconcile_period_returns(rows, result):
    with localcontext() as context:
        context.prec = 50
        ratio = Decimal(1)
        for previous, current in zip(rows, rows[1:]):
            if previous["score_end"] != current["score_start"] or previous["closing_equity"] != current["opening_equity"]:
                raise ValueError("period_boundaries_are_not_same_continuous_equity")
        for row in rows:
            ratio *= Decimal(str(row["closing_equity"])) / Decimal(str(row["opening_equity"]))
        target = Decimal(str(result["final_equity"])) / Decimal(str(result["equity_curve"][0]["equity"]))
        error = abs(ratio - target)
        float_product = math.prod(1 + row["total_return"] for row in rows)
        if error > Decimal("1e-40") or abs(float_product - (1 + result["total_return"])) > 1e-11:
            raise ValueError("continuous_period_return_product_does_not_reconcile")
        if sum(row["fill_count"] for row in rows) != result["fill_count"]:
            raise ValueError("period_fill_partition_mismatch")
        return {"status": "PASS", "periods": len(rows), "decimal_ratio_product": str(ratio),
                "final_over_initial": str(target), "decimal_absolute_error": str(error),
                "float_return_product_absolute_error": abs(float_product - (1 + result["total_return"]))}


def projection(report, plan, method, factor, reset_rows):
    result = report["result"]
    monthly, quarterly = calendar_slices(report, 1), calendar_slices(report, 3)
    comparisons = []
    for window in plan["reset_comparison_windows"]:
        row = slice_result(report, window["score_start"], window["score_end"], window["window_id"])
        old = next(r for r in reset_rows if r["window_id"] == window["window_id"] and r["method"] == method and r["cost_factor"] == factor)
        row.update(reset_report_hash=old["report_hash"], reset_total_return=old["total_return"],
                   return_difference_vs_reset=row["total_return"] - old["total_return"],
                   reset_fill_count=old["fill_count"], reset_fees=old["total_fees"],
                   reset_opening_cash=10000, reset_opening_position_qty=0,
                   difference_mechanisms=["CARRIED_CAPITAL_AND_POSITION_COSTS_PROTECTION_PENDING_VS_FLAT_REINITIALIZATION",
                       "FULL_PREFIX_FIXED_INDICATORS_VS_72_ROW_CONTEXT", "DIFFERENT_DAY_START_EQUITY_AND_ENTRY_ELIGIBILITY",
                       "PASSIVE_POLICY_ENTERS_ONCE_FOR_WHOLE_TRAJECTORY_NOT_ONCE_PER_WINDOW"])
        comparisons.append(row)
    whole = slice_result(report, plan["score_start"], plan["score_end"], "FULL_CONTINUOUS_HISTORY")
    positive = sorted((r["net_pnl"] for r in monthly if r["net_pnl"] > 0), reverse=True)
    positive_total = sum(positive)
    metrics = {k: result[k] for k in ("total_return", "max_drawdown", "final_equity", "final_cash", "fill_count", "round_trip_count",
              "total_fees", "realized_pnl", "unrealized_pnl", "open_position_qty", "unallocated_entry_fees", "end_mark_price")}
    return {"schema_version": "continuous-history-trace-projection-v1", "mode": "CONTINUOUS_HISTORY",
            "method": method, "cost_factor": factor, "plan_hash": digest(plan),
            "report_hash": report["report_hash"], "result_hash": report["result_hash"], "spec_hash": report["spec_hash"],
            "spec": report["spec"], "dataset": report["dataset"], "source_identity": report["evidence"]["source_identity"],
            "metrics": {**whole, **metrics, "positive_month_count": len(positive),
                "losing_month_count": sum(r["net_pnl"] < 0 for r in monthly),
                "top_three_positive_month_pnl_share": sum(positive[:3]) / positive_total if positive_total else None},
            "monthly": monthly, "quarterly": quarterly, "reset_comparisons": comparisons,
            "period_return_reconciliation": {"monthly": reconcile_period_returns(monthly, result),
                "quarterly": reconcile_period_returns(quarterly, result),
                "old_reset_intervals": reconcile_period_returns(comparisons, result)},
            "fills": result["fills"], "orders": result["orders"], "round_trips": result["round_trips"],
            "canonical_equity_curve_hash": digest(result["equity_curve"]), "canonical_signals_hash": digest(result["signals"]),
            "canonical_equity_point_count": len(result["equity_curve"]),
            "initialization_count": 1, "forced_end_liquidation": False, "accounting": result["accounting"],
            "risk_semantics": result["risk_semantics"], "execution_permission": report["execution_permission"],
            "limitations": ["Previously viewed historical data, not independent confirmation or live performance.",
                "Monthly and quarterly slices are descriptors of one ledger, never restarts or independent trials.",
                "Derived CSV identity is linked to verified local OKX capture parents; no new provider authentication.",
                "OHLC close exposure and mark-to-market omit unobserved intrabar paths."]}


def run(root, plan_path, snapshot_path, output, public):
    require_runtime()
    plan, snapshot = require_bound_input(plan_path, snapshot_path, output)
    old_summary = read_document(next((root / "artifacts/multiwindow-study-ci33969915599").glob("multiwindow_summary_*.json")))
    if digest(old_summary) != plan["reset_summary_hash"]:
        raise ValueError("original_reset_summary_changed")
    rows = []
    for method in plan["methods"]:
        for factor in plan["cost_factors"]:
            spec = make_spec(plan, snapshot, method, factor)
            key = f"{method['label']}-{factor}x"
            receipt_path = output / "cells" / f"{key}.json"
            if receipt_path.exists():
                receipt = read_document(receipt_path)
                report = verify_report(read_document(receipt["report_path"]))
                if report["spec"] != spec.document or receipt["plan_hash"] != digest(plan) or sha(receipt["report_path"]) != receipt["report_file_sha256"]:
                    raise ValueError("existing_continuous_cell_conflicts")
            else:
                started = time.perf_counter()
                print(json.dumps({"event": "STARTED", "cell": key}), flush=True)
                report = ExperimentRunner().run(snapshot, spec).document
                report_path = ResearchReport(report).save(output / "reports")
                spec_path = save(spec.document, output / "specs", "spec")
                receipt = {"method": method["label"], "cost_factor": factor, "plan_hash": digest(plan),
                           "report_path": str(report_path.resolve()), "spec_path": str(spec_path.resolve()),
                           "report_file_sha256": sha(report_path), "elapsed_seconds": time.perf_counter() - started,
                           "snapshot_path": str(snapshot_path.resolve()), "report_hash": report["report_hash"],
                           "spec_hash": report["spec_hash"], "runtime_source_sha256": SOURCE}
                frozen_write(receipt_path, receipt)
            view = projection(report, plan, method["label"], factor, old_summary["rows"])
            view_path = save(view, public, "trace")
            rows.append({"method": method["label"], "cost_factor": factor, "report_hash": report["report_hash"],
                         "projection_file": view_path.name, "projection_sha256": sha(view_path), "metrics": view["metrics"]})
            print(json.dumps({"event": "COMPLETED", "cell": key, "elapsed_seconds": receipt["elapsed_seconds"]}), flush=True)
    summary = {"schema_version": "continuous-history-summary-v1", "plan_hash": digest(plan), "plan": plan,
               "status": "COMPLETED", "trajectories": rows, "completed_trajectories": len(rows),
               "snapshot_id": snapshot.snapshot_id, "data_hash": snapshot.document["data_hash"],
               "runtime_source_sha256": SOURCE, "independent_replay_status": "SEPARATE_RECEIPT_REQUIRED",
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    path = save(summary, public, "summary")
    return {"summary": str(path), "completed": len(rows)}


def replay_and_reconcile(root, plan_path, snapshot_path, output, public):
    provenance = require_runtime()
    plan, snapshot = require_bound_input(plan_path, snapshot_path, output)
    module_spec = importlib.util.spec_from_file_location("independent_ledger_continuous", root / "scripts/reconcile_research_ledger.py")
    ledger = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(ledger)
    rows = []
    for method in plan["methods"]:
        for factor in plan["cost_factors"]:
            key = f"{method['label']}-{factor}x"
            attempt = read_document(output / "cells" / f"{key}.json")
            report = verify_report(read_document(attempt["report_path"]))
            if report["spec"] != make_spec(plan, snapshot, method, factor).document or sha(attempt["report_path"]) != attempt["report_file_sha256"]:
                raise ValueError("replay_original_cell_changed")
            local_path = output / "replay" / f"{key}.json"
            if local_path.exists():
                row = read_document(local_path)
                if row["original_report_hash"] != report["report_hash"] or row["plan_hash"] != digest(plan):
                    raise ValueError("replay_receipt_changed")
            else:
                print(json.dumps({"event": "REPLAY_STARTED", "cell": key}), flush=True)
                checked = replay_report(snapshot, ResearchReport(report))
                accounting = ledger.reconcile(report, snapshot.document)
                if not checked["replay_verified"] or accounting["status"] != "PASS":
                    raise ValueError("continuous_replay_or_accounting_failed")
                row = {"method": method["label"], "cost_factor": factor, "plan_hash": digest(plan),
                       "original_report_hash": report["report_hash"], "report_file_sha256": sha(attempt["report_path"]),
                       "replay": checked, "independent_decimal_ledger": accounting}
                frozen_write(local_path, row)
            rows.append(row)
            print(json.dumps({"event": "REPLAY_VERIFIED", "cell": key, "checks": row["independent_decimal_ledger"]["checks"]}), flush=True)
    receipt = {"schema_version": "continuous-history-independent-verification-v1", "status": "PASS", "plan_hash": digest(plan),
               "verified_trajectories": len(rows), "independent_numeric_checks": sum(r["independent_decimal_ledger"]["checks"] for r in rows),
               "receipts": rows, "replay_provenance": provenance, "ledger_tool_sha256": sha(root / "scripts/reconcile_research_ledger.py"),
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    # Provenance can contain installation paths; publish only runtime evidence and
    # result identity, with exact local receipts retained separately.
    for row in receipt["receipts"]:
        row["replay"].pop("replay_provenance", None)
        row["replay"].pop("receipt_hash", None)
    receipt.pop("replay_provenance")
    receipt["replay_environment_verified"] = provenance["environment_verified"]
    receipt["replay_source_identity"] = provenance["source_identity"]
    path = save(receipt, public, "verification")
    return {"verification": str(path), "verified": len(rows), "checks": receipt["independent_numeric_checks"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["freeze", "combine", "run", "replay"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    sys.addaudithook(deny_network)
    if args.phase == "freeze":
        result = freeze(args.root.resolve(), args.plan, args.output)
    elif args.phase == "combine":
        result = combine(args.root.resolve(), args.plan, args.output)
    elif args.phase == "run":
        result = run(args.root.resolve(), args.plan, args.snapshot, args.output, args.public)
    else:
        result = replay_and_reconcile(args.root.resolve(), args.plan, args.snapshot, args.output, args.public)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
