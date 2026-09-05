"""Run a predeclared fixed matrix through the installed canonical runner, offline."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from hakimi_research.dataset_registry import load_snapshot, utc_time
from hakimi_research.documents import canonical_bytes, digest, read_document
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, ResearchReport, replay_report, verify_report
from hakimi_research.reporting import save_json_report


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("offline_study_network_access_denied")


def validate_plan(plan):
    if plan.get("schema_version") != "multiwindow-study-plan-v1":
        raise ValueError("multiwindow_plan_schema_invalid")
    locks = {"parameter_selection": False, "confirmation_evaluation": False, "research_only": True,
             "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    if any(plan.get(key) is not expected for key, expected in locks.items()):
        raise ValueError("fixed_research_only_plan_required")
    if plan["missing_window_policy"] != "RETAIN_ALL_CELLS_AS_UNAVAILABLE_NO_SHORTENING":
        raise ValueError("missing_windows_must_remain_visible")
    if type(plan["context_hours"]) is not int or plan["context_hours"] < 62:
        raise ValueError("fixed_strategy_context_required")
    labels = [m["label"] for m in plan["methods"]]
    if len(set(labels)) != len(labels) or len(labels) != 5:
        raise ValueError("five_distinct_prespecified_method_labels_required")
    if [m["name"] for m in plan["methods"]] != ["cash", "buy_and_hold", "buy_and_hold", "dual_ma", "rsi"]:
        raise ValueError("fixed_cash_buy_hold_dual_ma_rsi_required")
    if plan["cost_factors"] != [1, 2, 3]:
        raise ValueError("three_prespecified_cost_factors_required")
    windows = plan["windows"]
    if not windows or len({w["window_id"] for w in windows}) != len(windows):
        raise ValueError("distinct_windows_required")
    previous_end = None
    for window in windows:
        start, end = utc_time(window["score_start"]), utc_time(window["score_end"])
        if start >= end or (previous_end is not None and start < previous_end):
            raise ValueError("chronological_nonoverlapping_windows_required")
        if window["split"] not in {"DEVELOPMENT_HISTORY", "VALIDATION_HISTORY_NOT_BLIND", "PREVIOUSLY_VIEWED_HISTORY"}:
            raise ValueError("explicit_historical_split_required")
        if start >= utc_time("2026-08-01T00:00:00Z") and window["split"] != "PREVIOUSLY_VIEWED_HISTORY":
            raise ValueError("august_2026_is_previously_viewed")
        previous_end = end
    return plan


def cell_spec(plan, window, method, factor, snapshot):
    passive = method["name"] == "buy_and_hold"
    risk = {**plan["risk"], **({"max_position_pct": 1, "min_cash_pct": 0} if passive else {})}
    value = {"schema_version": "research-experiment-spec-v1",
             "name": f"{window['window_id']}-{method['label']}-cost-{factor}x",
             "snapshot_id": snapshot.snapshot_id,
             "strategy": {"name": method["name"], "params": method["params"]},
             "score_start": window["score_start"], "score_end": window["score_end"],
             "initial_cash": plan["initial_cash"], "fee_rate": plan["fee_rate"] * factor,
             "slippage_pct": plan["slippage_pct"] * factor, "risk": risk,
             "end_policy": "MARK_TO_MARKET", "purpose": "DESCRIPTIVE_FIXED_PARAMETERS",
             "execution_policy": "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET" if passive else "STANDARD_STRATEGY_RISK"}
    return ExperimentSpec.from_document(value)


def _seconds(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def duration_weighted_exposure(points):
    """Actual recorded close exposures weighted by their scored interval duration.

    This is a discrete OHLC statistic, not an invented intrabar holding duration.
    An intrabar entry and exit can have zero closing exposure but nonzero risk.
    """
    duration = weighted = invested = 0.0
    for previous, current in zip(points, points[1:]):
        seconds = _seconds(current["time"]) - _seconds(previous["time"])
        if seconds <= 0 or current["equity"] <= 0:
            raise ValueError("positive_duration_and_equity_required_for_exposure")
        exposure = current["position_value"] / current["equity"]
        duration += seconds
        weighted += seconds * exposure
        invested += seconds * (current["position_qty"] > 0)
    if duration == 0:
        raise ValueError("scored_intervals_required")
    return {"duration_weighted_close_exposure": weighted / duration,
            "duration_weighted_invested_close_fraction": invested / duration,
            "scored_seconds": duration,
            "exposure_definition": "SUM_INTERVAL_SECONDS_TIMES_RECORDED_CLOSE_POSITION_VALUE_OVER_EQUITY_DIVIDED_BY_TOTAL_SECONDS",
            "intrabar_continuous_exposure": "UNOBSERVABLE_FROM_HOURLY_OHLC"}


def summarize_result(report):
    result, spec = report["result"], report["spec"]
    orders = {order["order_id"]: order for order in result["orders"]}
    slippage = sum(abs(fill["price"] - orders[fill["order_id"]]["reference_price"]) * fill["quantity"]
                   for fill in result["fills"])
    curve = result["equity_curve"]
    first_fill = next((fill for fill in result["fills"] if fill["action"] == "BUY"), None)
    return {**{key: result[key] for key in ("total_return", "max_drawdown", "final_equity", "fill_count",
             "round_trip_count", "total_fees", "open_position_qty", "realized_pnl", "unrealized_pnl")},
            **duration_weighted_exposure(curve),
            "slippage_cost_vs_recorded_reference": slippage,
            "fee_plus_slippage_cost": result["total_fees"] + slippage,
            "requested_initial_allocation_fraction": spec["strategy"]["params"].get("target_position_pct", spec["strategy"]["params"].get("position_pct", 0)),
            "first_fill_time": first_fill["fill_time"] if first_fill else None,
            "first_fill_notional_over_initial_cash": first_fill["price"] * first_fill["quantity"] / spec["initial_cash"] if first_fill else 0,
            "first_scored_close_exposure": curve[1]["position_value"] / curve[1]["equity"],
            "net_pnl": result["final_equity"] - spec["initial_cash"],
            "report_hash": report["report_hash"], "spec_hash": report["spec_hash"],
            "computation_id": report["computation_id"],
            "source_content_sha256": report["evidence"]["source_identity"].get("content_sha256"),
            "statistical_status": result["statistical_status"]}


def aggregate_rows(rows, plan):
    groups = []
    for method in plan["methods"]:
        for factor in plan["cost_factors"]:
            for split in ("ALL_HISTORY", "DEVELOPMENT_HISTORY", "VALIDATION_HISTORY_NOT_BLIND", "PREVIOUSLY_VIEWED_HISTORY"):
                selected = [r for r in rows if r["method"] == method["label"] and r["cost_factor"] == factor
                            and (split == "ALL_HISTORY" or r["split"] == split)]
                if not selected:
                    continue
                good = [r for r in selected if r["status"] == "COMPLETED"]
                positive = [r for r in good if r["net_pnl"] > 0]
                profit = sum(r["net_pnl"] for r in positive)
                abs_pnl = sum(abs(r["net_pnl"]) for r in good)
                ranked_profit = sorted(positive, key=lambda r: r["net_pnl"], reverse=True)
                groups.append({"method": method["label"], "cost_factor": factor, "split": split,
                    "planned_windows": len(selected), "completed_windows": len(good),
                    "unavailable_or_failed_windows": [r["window_id"] for r in selected if r["status"] != "COMPLETED"],
                    "losing_windows": [r["window_id"] for r in good if r["net_pnl"] < 0],
                    "underperformed_equal_requested_allocation_buy_hold_windows": [r["window_id"] for r in good if r.get("return_minus_buy_hold_25pct") is not None and r["return_minus_buy_hold_25pct"] < 0],
                    "inactive_windows": [r["window_id"] for r in good if r["fill_count"] == 0],
                    "sum_independently_reset_window_pnl": sum(r["net_pnl"] for r in good),
                    "median_window_return": _median([r["total_return"] for r in good]),
                    "worst_window_return": min((r["total_return"] for r in good), default=None),
                    "largest_window_drawdown": max((r["max_drawdown"] for r in good), default=None),
                    "total_fees": sum(r["total_fees"] for r in good),
                    "fee_plus_slippage_cost": sum(r["fee_plus_slippage_cost"] for r in good),
                    "top_one_positive_window_profit_share": ranked_profit[0]["net_pnl"] / profit if profit else None,
                    "top_three_positive_window_profit_share": sum(r["net_pnl"] for r in ranked_profit[:3]) / profit if profit else None,
                    "largest_absolute_window_pnl_share": max((abs(r["net_pnl"]) for r in good), default=0) / abs_pnl if abs_pnl else None,
                    "profit_concentration_status": "DESCRIPTIVE_POSITIVE_PNL_CONTRIBUTION" if profit else "NO_POSITIVE_WINDOW_PNL",
                    "all_loss_windows_retained": True})
    return groups


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def publish_markdown(path, text):
    encoded = text.encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".summary-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != encoded:
                raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def markdown(summary):
    lines = ["# 固定策略多窗口研究", "", f"计划 `{summary['plan_hash']}`；完成 {summary['completed_cells']}/{summary['planned_cells']} 个单元。",
             "", "每个窗口重新以10,000 USDT空仓开始；窗口损益之和不表示一条连续可交易净值。验证期是按时间划分的历史，未经盲测；2026年8月明确是已查看历史。",
             "", "25%买入持有仅匹配请求的起始资金配置，实际成交时间和持续敞口可能不同。敞口使用实际账本收盘市值按区间秒数加权，无法观测小时内连续敞口。",
             "", "| 方法 | 成本 | 完成窗口 | 亏损窗口 | 最差窗口收益 | 最大窗口回撤 | 费用+滑点 USDT | 最大盈利窗口占正收益 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for group in summary["groups"]:
        if group["split"] != "ALL_HISTORY":
            continue
        fmt = lambda value: "不可计算" if value is None else f"{value:.2%}"
        lines.append(f"| {group['method']} | {group['cost_factor']}x | {group['completed_windows']}/{group['planned_windows']} | {len(group['losing_windows'])} | {fmt(group['worst_window_return'])} | {fmt(group['largest_window_drawdown'])} | {group['fee_plus_slippage_cost']:.2f} | {fmt(group['top_one_positive_window_profit_share'])} |")
    lines += ["", "## 窗口结果（所有成本和失败记录均保留）", "",
              "| 窗口 | 方法 | 成本 | 状态 | 收益 | 回撤 | 平均收盘敞口 | 成交/完整交易 | 费用 USDT |", "|---|---|---:|---|---:|---:|---:|---:|---:|"]
    for row in summary["rows"]:
        if row["status"] != "COMPLETED":
            lines.append(f"| {row['window_id']} | {row['method']} | {row['cost_factor']} | {row['status']} | — | — | — | — | — |")
        else:
            lines.append(f"| {row['window_id']} | {row['method']} | {row['cost_factor']} | 完成 | {row['total_return']:.2%} | {row['max_drawdown']:.2%} | {row['duration_weighted_close_exposure']:.2%} | {row['fill_count']}/{row['round_trip_count']} | {row['total_fees']:.2f} |")
    lines += ["", "JSON同时保留逐窗口对照差、成本变化、亏损/不活跃窗口、正收益集中度、规约/报告/快照/源码身份。没有选择冠军或搜索参数；历史相关性、OHLC成交近似与市场来源限制仍适用。", ""]
    return "\n".join(lines)


def run(plan_path, snapshot_paths, output):
    plan = validate_plan(read_document(plan_path))
    plan_hash = digest(plan)
    snapshots, rejected = [], []
    for path in snapshot_paths:
        try:
            snapshot = load_snapshot(path)
            if snapshot.document["evidence_kind"] == "SYNTHETIC_TEST":
                raise ValueError("real_history_snapshot_required")
            snapshots.append((snapshot, path))
        except (ValueError, OSError) as error:
            rejected.append({"file_sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
                             "error_type": type(error).__name__, "error_code": str(error).split(":")[0]})
    rows, attempts = [], []
    for window in plan["windows"]:
        candidates = [(s, p) for s, p in snapshots
                      if (utc_time(window["score_start"]) - utc_time(s.document["start"])).total_seconds() >= plan["context_hours"] * 3600
                      and utc_time(s.document["end_exclusive"]) >= utc_time(window["score_end"])]
        selected = min(candidates, key=lambda pair: len(pair[0].document["candles"])) if candidates else None
        for method in plan["methods"]:
            for factor in plan["cost_factors"]:
                row = {**window, "method": method["label"], "cost_factor": factor, "status": "UNAVAILABLE_DATA"}
                attempt = {**row}
                if selected is not None:
                    snapshot, snapshot_path = selected
                    row["snapshot_id"] = snapshot.snapshot_id
                    attempt["snapshot_path"] = str(snapshot_path.resolve())
                    try:
                        spec = cell_spec(plan, window, method, factor, snapshot)
                        spec_path = save_json_report(spec.document, output / "specs", "spec", artifact_id=digest(spec.document))
                        report = ExperimentRunner().run(snapshot, spec)
                        report_path = report.save(output / "reports")
                        checked = verify_report(report.document)
                        row.update(status="COMPLETED", **summarize_result(checked))
                        attempt.update(status="COMPLETED", report_path=str(report_path.resolve()), spec_path=str(Path(spec_path).resolve()))
                    except (ValueError, OSError, RuntimeError) as error:
                        row.update(status="FAILED", error_type=type(error).__name__, error_code=str(error).split(":")[0])
                        attempt.update(row)
                rows.append(row)
                attempts.append(attempt)
                # Every completed/failed cell is durable before the next one starts.
                save_json_report({"plan_hash": plan_hash, "row": row, "attempt": attempt}, output / "attempts", "cell", artifact_id=digest({"plan_hash": plan_hash, "row": row, "attempt": attempt}))
    by_key = {(r["window_id"], r["method"], r["cost_factor"]): r for r in rows}
    for row in rows:
        if row["status"] != "COMPLETED":
            continue
        for benchmark in ("cash", "buy_hold_full", "buy_hold_25pct"):
            reference = by_key.get((row["window_id"], benchmark, row["cost_factor"]))
            row["return_minus_" + benchmark] = row["total_return"] - reference["total_return"] if reference and reference["status"] == "COMPLETED" else None
        base = by_key.get((row["window_id"], row["method"], 1))
        row["return_change_from_base_cost"] = row["total_return"] - base["total_return"] if base and base["status"] == "COMPLETED" else None
    summary = {"schema_version": "multiwindow-study-summary-v1", "plan_hash": plan_hash, "plan": plan,
               "planned_cells": len(rows), "completed_cells": sum(r["status"] == "COMPLETED" for r in rows),
               "rows": rows, "groups": aggregate_rows(rows, plan), "rejected_inputs": rejected,
               "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "replay_status": "NOT_RUN_SEPARATE_RECEIPTS_REQUIRED", "network_policy": "PYTHON_SOCKET_AUDIT_DENY",
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    identity = digest(summary)
    path = save_json_report(summary, output, "multiwindow_summary", artifact_id=identity)
    manifest = {"schema_version": "multiwindow-study-run-v1", "plan_hash": plan_hash, "summary_hash": identity,
                "summary_path": str(Path(path).resolve()), "attempts": attempts}
    run_path = save_json_report(manifest, output, "multiwindow_run", artifact_id=digest(manifest))
    md_path = output / f"multiwindow_summary_{identity}.md"
    publish_markdown(md_path, markdown(summary))
    return {"summary": path, "markdown": str(md_path), "run": run_path, "completed": summary["completed_cells"], "planned": len(rows)}


def replay(run_path, output):
    run_doc = read_document(run_path)
    if run_doc.get("schema_version") != "multiwindow-study-run-v1":
        raise ValueError("multiwindow_run_schema_invalid")
    summary = read_document(run_doc["summary_path"])
    if digest(summary) != run_doc["summary_hash"] or summary["plan_hash"] != run_doc["plan_hash"]:
        raise ValueError("multiwindow_summary_identity_mismatch")
    def key(row):
        return row["window_id"], row["method"], row["cost_factor"]
    rows = {key(row): row for row in summary["rows"]}
    if len(rows) != len(summary["rows"]) or len(run_doc["attempts"]) != len(rows) or {key(a) for a in run_doc["attempts"]} != set(rows):
        raise ValueError("multiwindow_replay_complete_unique_matrix_required")
    receipts = []
    cache = {}
    original_snapshots = {}
    for attempt in run_doc["attempts"]:
        row = rows[key(attempt)]
        if attempt["status"] != row["status"]:
            raise ValueError("multiwindow_attempt_status_mismatch")
        if attempt["status"] != "COMPLETED":
            receipts.append({"window_id": attempt["window_id"], "method": attempt["method"], "cost_factor": attempt["cost_factor"], "status": "NOT_RUN_ORIGINAL_CELL_INCOMPLETE"})
            continue
        snapshot_path, report_path = Path(attempt["snapshot_path"]), Path(attempt["report_path"])
        before = hashlib.sha256(report_path.read_bytes()).hexdigest()
        if snapshot_path not in cache:
            cache[snapshot_path] = load_snapshot(snapshot_path)
            original_snapshots[snapshot_path] = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        report = verify_report(read_document(report_path))
        if report["report_hash"] != row["report_hash"] or cache[snapshot_path].snapshot_id != row["snapshot_id"]:
            raise ValueError("multiwindow_replay_input_identity_mismatch")
        receipt = replay_report(cache[snapshot_path], ResearchReport(report))
        path = save_json_report(receipt, output / "receipts", "replay", artifact_id=receipt["receipt_hash"])
        if hashlib.sha256(report_path.read_bytes()).hexdigest() != before:
            raise ValueError("original_report_modified")
        receipts.append({"window_id": attempt["window_id"], "method": attempt["method"], "cost_factor": attempt["cost_factor"],
                         "status": "VERIFIED" if receipt["replay_verified"] else "UNVERIFIED", "receipt_hash": receipt["receipt_hash"],
                         "receipt_file": Path(path).name, "report_file_sha256": before,
                         **{key: receipt[key] for key in ("result_matches", "source_matches", "environment_verified", "replay_verified")}})
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != expected for path, expected in original_snapshots.items()):
        raise ValueError("original_snapshot_modified")
    core = {"schema_version": "multiwindow-study-replay-v1", "plan_hash": run_doc["plan_hash"],
            "summary_hash": run_doc["summary_hash"], "receipts": receipts,
            "verified_count": sum(r["status"] == "VERIFIED" for r in receipts), "planned_count": len(receipts)}
    path = save_json_report(core, output, "multiwindow_replay", artifact_id=digest(core))
    return {"receipt": path, "verified": core["verified_count"], "planned": core["planned_count"]}


if __name__ == "__main__":
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    research = commands.add_parser("run")
    research.add_argument("--plan", type=Path, required=True)
    research.add_argument("--snapshot", type=Path, action="append", default=[])
    research.add_argument("--snapshot-directory", type=Path, help="Read only dataset_*.json files recursively.")
    research.add_argument("--output-dir", type=Path, required=True)
    replay_parser = commands.add_parser("replay")
    replay_parser.add_argument("--run", type=Path, required=True)
    replay_parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        paths = args.snapshot + (sorted(args.snapshot_directory.rglob("dataset_*.json")) if args.snapshot_directory else [])
        result = run(args.plan, list(dict.fromkeys(paths)), args.output_dir)
    else:
        result = replay(args.run, args.output_dir)
    print(json.dumps(result, ensure_ascii=False))
