"""Build an offline view from verified projections and reviewed local notes."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import quote

SCORE_START = "2023-01-04T00:00:00Z"
SCORE_END = "2026-09-01T00:00:00Z"
INPUT_START = "2023-01-01T00:00:00Z"
SOURCES = {"0.2.1": "48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5",
           "0.2.2": "f657a07534061e7d03d2922b1fc1a69eeea04751a7a6201ac961ee55e76cf767"}
METHODS = {"cash": "现金", "buy_hold_full": "100% 初始买入持有", "buy_hold_25pct": "25% 初始买入持有",
           "dual_ma": "Dual MA", "rsi": "RSI", "D0": "D0 · 当前 Dual MA", "D1": "D1 · 取消固定止盈",
           "R0": "R0 · 当前 RSI", "R1": "R1 · 每个超卖事件一次入场意图"}
METRICS = (("total_return", "总收益", "pct"), ("max_drawdown", "最大回撤", "pct"),
           ("max_drawdown_duration_hours", "回撤最长持续小时", "number"),
           ("duration_weighted_close_exposure", "实际平均收盘敞口", "pct"),
           ("fill_count", "成交", "count"), ("round_trip_count", "完整交易", "count"),
           ("total_fees", "手续费 USDT", "money"), ("fee_plus_slippage_cost", "费用与滑点 USDT", "money"))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError("duplicate_JSON_key")
        value[key] = item
    return value


def _constant(value):
    raise ValueError("nonfinite_JSON_number")


def read(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    if type(value) is not dict:
        raise ValueError("JSON_object_required")
    canonical(value)  # Reject overflowed/nonfinite values anywhere in the input.
    return value


def same(left, right, reason):
    if canonical(left) != canonical(right):
        raise ValueError(reason)


def escape(value):
    text = html.escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")
    for char in ("\\", "`", "[", "]", "(", ")", "*", "_", "|", "#"):
        text = text.replace(char, "\\" + char)
    return text


def formatted(value, kind="number"):
    if value is None:
        return "不可估计 / 未提供"
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite_numeric_metric_required")
    if kind == "count":
        if type(value) is not int or value < 0:
            raise ValueError("nonnegative_integer_count_required")
        return str(value)
    if kind == "pct":
        return f"{value * 100:.3f}%"
    if kind == "pp":
        return f"{value * 100:.3f}"
    return f"{value:,.2f}"


def _safe_file(parent, relative):
    if type(relative) is not str:
        raise ValueError("relative_source_filename_required")
    target = (parent / relative).resolve()
    if not target.is_relative_to(parent.resolve()) or not target.is_file():
        raise ValueError("source_projection_outside_family_or_missing")
    return target


def _permissions(value):
    if any(value.get(key) is not False for key in ("paper_allowed", "live_allowed", "order_allowed")):
        raise ValueError("research_execution_permissions_changed")
    if value.get("research_only") is not True:
        raise ValueError("research_only_evidence_required")


def _scope(plan):
    if (plan.get("mode") != "CONTINUOUS_HISTORY" or plan.get("score_start") != SCORE_START
            or plan.get("score_end") != SCORE_END or plan.get("initial_cash") != 10000
            or plan.get("input_start") != INPUT_START or plan.get("input_end_exclusive") != SCORE_END
            or plan.get("fee_rate") != .0008 or plan.get("slippage_pct") != .0005):
        raise ValueError("research_range_mode_initialization_or_cost_scope_mismatch")
    _permissions({"research_only": True, **plan})


def _trace_scope(trace, plan, factor, source):
    spec = trace["spec"]
    if (trace.get("mode") != "CONTINUOUS_HISTORY" or trace.get("plan_hash") != digest(plan)
            or spec["score_start"] != SCORE_START or spec["score_end"] != SCORE_END
            or spec["initial_cash"] != 10000 or spec["fee_rate"] != .0008 * factor
            or spec["slippage_pct"] != .0005 * factor or spec["end_policy"] != "MARK_TO_MARKET"
            or spec["purpose"] != "DESCRIPTIVE_FIXED_PARAMETERS"
            or trace["source_identity"]["status"] != "BUILD_VERIFIED"
            or trace["source_identity"]["content_sha256"] != source
            or trace["dataset"]["start"] != INPUT_START or trace["dataset"]["end_exclusive"] != SCORE_END):
        raise ValueError("projection_mode_range_cost_or_source_mismatch")
    if spec["snapshot_id"] != trace["dataset"]["snapshot_id"]:
        raise ValueError("projection_snapshot_identity_mismatch")
    _permissions(trace["execution_permission"])


def _strategy_scope(trace, plan, label):
    methods = [method for method in plan["methods"] if method["label"] == label]
    if len(methods) != 1:
        raise ValueError("exact_planned_method_required")
    method = methods[0]
    same(trace["spec"]["strategy"], {"name": method["name"], "params": method["params"]}, "trace_strategy_differs_from_frozen_plan")


def _named_digest(path, value, prefix):
    if path.stem.startswith(prefix + "_") and path.stem != prefix + "_" + digest(value):
        raise ValueError("canonical_document_filename_hash_mismatch")


def _periods(rows, expected_count, *, comparisons=False):
    if len(rows) != expected_count or rows[0]["score_start"] != SCORE_START or rows[-1]["score_end"] != SCORE_END:
        raise ValueError("period_count_or_range_mismatch")
    for previous, current in zip(rows, rows[1:]):
        if previous["score_end"] != current["score_start"] or previous["closing_equity"] != current["opening_equity"]:
            raise ValueError("continuous_period_boundary_mismatch")
    if len({row["slice_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate_period_id")
    for row in rows:
        if datetime.fromisoformat(row["score_end"]) <= datetime.fromisoformat(row["score_start"]):
            raise ValueError("nonpositive_period")
        for key, _, kind in METRICS:
            if key in row:
                formatted(row[key], kind)
        if comparisons:
            if row["return_difference_vs_reset"] != row["total_return"] - row["reset_total_return"]:
                raise ValueError("reset_comparison_difference_mismatch")
            if row["reset_opening_cash"] != 10000 or row["reset_opening_position_qty"] != 0:
                raise ValueError("reset_comparison_initialization_mismatch")


def load_continuous(path):
    summary = read(path)
    _named_digest(path, summary, "summary")
    if summary.get("schema_version") != "continuous-history-summary-v1" or summary.get("status") != "COMPLETED":
        raise ValueError("completed_continuous_summary_required")
    _permissions(summary)
    plan = summary["plan"]
    _scope(plan)
    if (summary["plan_hash"] != digest(plan) or plan["initialization_count"] != 1
            or plan["cost_factors"] != [1, 2, 3] or plan["planned_trajectories"] != 15):
        raise ValueError("continuous_plan_identity_or_initialization_mismatch")
    expected = {(method, cost) for method in ("cash", "buy_hold_full", "buy_hold_25pct", "dual_ma", "rsi") for cost in (1, 2, 3)}
    rows = summary["trajectories"]
    if (len(rows) != 15 or summary["completed_trajectories"] != 15
            or {(row["method"], row["cost_factor"]) for row in rows} != expected
            or summary["runtime_source_sha256"] != SOURCES["0.2.1"]):
        raise ValueError("continuous_matrix_or_source_mismatch")
    loaded = []
    for row in rows:
        projection_path = _safe_file(path.parent, row["projection_file"])
        if sha(projection_path) != row["projection_sha256"]:
            raise ValueError("continuous_projection_file_hash_mismatch")
        trace = read(projection_path)
        _named_digest(projection_path, trace, "trace")
        _trace_scope(trace, plan, row["cost_factor"], SOURCES["0.2.1"])
        _strategy_scope(trace, plan, row["method"])
        if (trace["schema_version"] != "continuous-history-trace-projection-v1"
                or trace["method"] != row["method"] or trace["cost_factor"] != row["cost_factor"]
                or trace["report_hash"] != row["report_hash"] or trace["initialization_count"] != 1
                or trace["forced_end_liquidation"] is not False):
            raise ValueError("continuous_projection_identity_mismatch")
        same(trace["metrics"], row["metrics"], "continuous_summary_vs_projection_metric_mismatch")
        if trace["dataset"]["snapshot_id"] != summary["snapshot_id"] or trace["dataset"]["data_hash"] != summary["data_hash"]:
            raise ValueError("continuous_summary_dataset_mismatch")
        _periods(trace["monthly"], 44)
        _periods(trace["quarterly"], 15)
        _periods(trace["reset_comparisons"], 16, comparisons=True)
        for key, _, kind in METRICS:
            formatted(row["metrics"][key], kind)
        if len(trace["fills"]) != row["metrics"]["fill_count"] or len(trace["round_trips"]) != row["metrics"]["round_trip_count"]:
            raise ValueError("continuous_trade_count_mismatch")
        loaded.append({"row": row, "trace": trace, "path": projection_path})
    return {"summary": summary, "path": path, "traces": loaded, "version": "0.2.1"}


def load_diagnostics(path, continuous, root=None):
    summary = read(path)
    if summary.get("schema_version") != "strategy-diagnostics-summary-v1" or summary.get("mode") != "CONTINUOUS_HISTORY":
        raise ValueError("diagnostic_continuous_summary_required")
    _permissions(summary)
    plan = summary["plan"]
    _scope(plan)
    if (summary["plan_hash"] != digest(plan) or summary["source_content_sha256"] != SOURCES["0.2.2"]
            or plan["cost_factors"] != [0, 1, 2, 3] or plan["budget"]["primary_trajectories"] != 16):
        raise ValueError("diagnostic_plan_or_source_identity_mismatch")
    rows = summary["rows"]
    expected = {(method, cost) for method in ("D0", "D1", "R0", "R1") for cost in (0, 1, 2, 3)}
    if (summary["planned_cells"] != 16 or summary["completed_cells"] != 16 or len(rows) != 16
            or {(row["method"], row["cost_factor"]) for row in rows} != expected):
        raise ValueError("diagnostic_matrix_mismatch")
    loaded, by_key = [], {(row["method"], row["cost_factor"]): row for row in rows}
    refs = {(value["row"]["method"], value["row"]["cost_factor"]): value for value in continuous["traces"]}
    for row in rows:
        projection_path = _safe_file(path.parent, row["projection_file"])
        if sha(projection_path) != row["projection_file_sha256"]:
            raise ValueError("diagnostic_projection_file_hash_mismatch")
        trace = read(projection_path)
        _named_digest(projection_path, trace, "trace")
        _trace_scope(trace, plan, row["cost_factor"], SOURCES["0.2.2"])
        _strategy_scope(trace, plan, row["method"])
        if (trace["schema_version"] != "strategy-diagnostics-trace-projection-v1"
                or row["status"] != "COMPLETED" or trace["report_hash"] != row["report_hash"]
                or trace["report_file_sha256"] != row["report_file_sha256"]):
            raise ValueError("diagnostic_projection_identity_mismatch")
        for key, value in trace["metrics"].items():
            same(value, row[key], "diagnostic_summary_vs_projection_metric_mismatch:" + key)
        same(trace["periods"], row["periods"], "diagnostic_period_summary_mismatch")
        same(trace["monthly"], row["monthly"], "diagnostic_monthly_summary_mismatch")
        _periods(trace["monthly"], 44)
        _periods(trace["periods"], 16)
        if trace["dataset"]["snapshot_id"] != continuous["summary"]["snapshot_id"] or trace["dataset"]["data_hash"] != continuous["summary"]["data_hash"]:
            raise ValueError("diagnostic_and_continuous_input_mismatch")
        for key, _, kind in METRICS:
            formatted(row[key], kind)
        if len(trace["fills"]) != row["fill_count"] or len(trace["round_trips"]) != row["round_trip_count"]:
            raise ValueError("diagnostic_trade_count_mismatch")
        for label, reference in row["reference_reports"].items():
            actual = refs[(label, row["cost_factor"])]["row"]
            if (reference["report_hash"] != actual["report_hash"]
                    or reference["total_return"] != actual["metrics"]["total_return"]
                    or reference["cost_factor"] != row["cost_factor"]
                    or reference["score_start"] != SCORE_START or reference["score_end"] != SCORE_END
                    or reference["source_content_sha256"] != SOURCES["0.2.1"]):
                raise ValueError("diagnostic_reference_scope_or_value_mismatch")
        if row["cost_factor"] == 0:
            if row["reference_reports"] or row["return_minus_buy_hold_25pct"] is not None:
                raise ValueError("zero_cost_cannot_invent_missing_canonical_reference")
        else:
            if set(row["reference_reports"]) != {"cash", "buy_hold_25pct"}:
                raise ValueError("both_same_cost_reference_reports_required")
            if row["return_minus_buy_hold_25pct"] != row["total_return"] - row["reference_reports"]["buy_hold_25pct"]["total_return"]:
                raise ValueError("buy_hold_reference_difference_mismatch")
        paired = row["paired_change"]
        if row["method"] in {"D1", "R1"}:
            baseline = by_key[({"D1": "D0", "R1": "R0"}[row["method"]], row["cost_factor"])]
            if not paired or paired["baseline_report_hash"] != baseline["report_hash"]:
                raise ValueError("paired_baseline_identity_mismatch")
            for key, _, _ in METRICS:
                if paired[key] != row[key] - baseline[key]:
                    raise ValueError("paired_summary_difference_mismatch")
        elif paired is not None:
            raise ValueError("baseline_cannot_have_variant_difference")
        loaded.append({"row": row, "trace": trace, "path": projection_path})
    if len(summary["baseline_021_economic_equivalence"]) != 6 or any(
            item["all_equal"] is not True for item in summary["baseline_021_economic_equivalence"]):
        raise ValueError("six_unchanged_baseline_economic_equivalences_required")
    replay_path = path.parent / "replay-summary.json"
    replay = read(replay_path)
    if (sha(replay_path) != summary["replay"]["receipt_file_sha256"]
            or replay.get("schema_version") != "strategy-diagnostics-replay-public-v1"
            or replay.get("privacy") != "MACHINE_RECEIPT_OMITTED_ORIGINAL_IDENTITIES_REFERENCED_SEPARATE_PUBLIC_PROJECTION"
            or summary["replay"].get("receipt_scope") != "SANITIZED_PUBLIC_PROJECTION_NOT_CANONICAL_ORIGINAL"
            or replay.get("projection_hash") != digest({key: value for key, value in replay.items() if key != "projection_hash"})
            or replay.get("verified") != 16 or len(replay.get("receipts", [])) != 16
            or replay.get("planned") != 16 or replay.get("source_content_sha256") != SOURCES["0.2.2"]
            or replay["plan_hash"] != summary["plan_hash"]
            or not re.fullmatch(r"[0-9a-f]{64}", replay.get("original_summary_file_sha256", ""))
            or replay["original_summary_file_sha256"] != summary["replay"]["original_private_receipt_file_sha256"]
            or {entry["replay"]["original_report_hash"] for entry in replay["receipts"]} != {row["report_hash"] for row in rows}
            or any(entry["replay"]["replay_verified"] is not True or entry["ledger"]["status"] != "PASS" for entry in replay["receipts"])):
        raise ValueError("diagnostic_replay_identity_or_scope_mismatch")
    if {(entry["method"], entry["cost_factor"]) for entry in replay["receipts"]} != expected:
        raise ValueError("diagnostic_replay_matrix_mismatch")
    for entry in replay["receipts"]:
        public = entry["replay"]
        row = by_key[(entry["method"], entry["cost_factor"])]
        if (public.get("schema_version") != "research-replay-public-projection-v1"
                or public.get("projection_hash") != digest({key: value for key, value in public.items() if key != "projection_hash"})
                or not re.fullmatch(r"[0-9a-f]{64}", public.get("original_receipt_hash", ""))
                or "receipt_hash" in public or "machine_receipt" in public.get("replay_provenance", {})
                or public["original_report_hash"] != row["report_hash"]
                or entry["report_file_sha256"] != row["report_file_sha256"]):
            raise ValueError("diagnostic_public_replay_projection_binding_mismatch")
    bundle = {"summary": summary, "path": path, "traces": loaded, "version": "0.2.2", "replay_path": replay_path,
              "replay_projection_identity": {key: replay[key] for key in
                    ("schema_version", "projection_hash", "original_summary_file_sha256")}}
    if "input_lineage" in summary:
        if root is None:
            raise ValueError("repository_root_required_for_input_lineage")
        entry = summary["input_lineage"]
        lineage_path = _safe_file(root, entry["file_relative_to_repository"])
        lineage = read(lineage_path)
        if (sha(lineage_path) != entry["file_sha256"] or lineage["snapshot_id"] != continuous["summary"]["snapshot_id"]
                or lineage["snapshot_file_sha256"] != entry["snapshot_file_sha256"]
                or lineage["canonical_values_changed"] is not False):
            raise ValueError("diagnostic_input_lineage_identity_mismatch")
        bundle["lineage_path"] = lineage_path
    return bundle


def load_forward(path):
    value = read(path)
    if (value.get("schema_version") != "forward-reliability-coverage-v1"
            or value.get("report_hash") != digest({key: item for key, item in value.items() if key != "report_hash"})
            or value.get("state_policy") != "FLAT_REFERENCE_OBSERVATION" or value.get("order_allowed") is not False):
        raise ValueError("forward_coverage_identity_or_mode_mismatch")
    rows = value["rows"]
    first, end, as_of = (datetime.fromisoformat(value[key]) for key in ("window_start", "window_end_exclusive", "as_of_utc"))
    plan_ids = {row["plan_hash"] for row in rows}
    pairs = {(datetime.fromisoformat(row["cutoff"]), row["plan_hash"]) for row in rows}
    expected_pairs = {(first + timedelta(hours=offset), plan_id) for offset in range(72) for plan_id in plan_ids}
    strategy_pairs = {(row["plan_hash"], row["strategy"]) for row in rows}
    if (end - first != timedelta(hours=72) or len(rows) != 144 or len(plan_ids) != 2
            or pairs != expected_pairs or len(strategy_pairs) != 2
            or {row["strategy"] for row in rows} != {"dual_ma", "rsi"}):
        raise ValueError("forward_fixed_plan_denominator_mismatch")
    counts = Counter()
    for row in rows:
        cutoff = datetime.fromisoformat(row["cutoff"])
        elapsed = as_of >= cutoff + timedelta(seconds=300)
        observation = row["observation"]
        if row["elapsed"] is not elapsed or not first <= cutoff < end:
            raise ValueError("forward_elapsed_range_mismatch")
        if elapsed:
            if row["status"] not in {"ON_TIME", "LATE", "MISSING", "FAILED"}:
                raise ValueError("forward_future_status_in_elapsed_denominator")
            counts[row["status"]] += 1
        elif cutoff > as_of:
            if row["status"] != "PLANNED":
                raise ValueError("forward_future_hour_misclassified")
        elif row["status"] != ("ON_TIME" if observation else "PENDING"):
            # The producer can record a real signal before the deadline;
            # unobserved active hours are pending, not future or missing.
            # Conflicting failure/missing evidence during this interval must
            # stop the view; never relabel that evidence as a success.
            raise ValueError("forward_active_hour_misclassified")
        if row["status"] in {"ON_TIME", "LATE"} and (not observation or observation["timing_status"] != row["status"]):
            raise ValueError("forward_success_status_without_matching_observation")
        if observation:
            available = datetime.fromisoformat(observation["signal_available_at"])
            eligible = available.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            if (not cutoff <= available <= as_of
                    or observation["cutoff"] != row["cutoff"] or observation["plan_hash"] != row["plan_hash"]
                    or observation["reference_execution_performed"] is not False
                    or datetime.fromisoformat(observation["reference_execution_eligible_at"]) != eligible):
                raise ValueError("forward_observation_or_signal_timing_mismatch")
    counts = {key: counts[key] for key in ("ON_TIME", "LATE", "MISSING", "FAILED")}
    same(counts, value["counts"], "forward_summary_vs_rows_count_mismatch")
    if (value["planned_strategy_hours"] != 144 or value["elapsed_strategy_hours"] != sum(counts.values())
            or value["elapsed_hours"] * 2 != sum(counts.values())
            or value["future_strategy_hours"] != sum(row["status"] == "PLANNED" for row in rows)
            or value["pending_strategy_hours"] != sum(row["status"] == "PENDING" for row in rows)):
        raise ValueError("forward_summary_denominator_mismatch")
    return {"summary": value, "path": path}


def load_verification(path, continuous):
    value = read(path)
    if (value.get("schema_version") != "continuous-history-independent-verification-v1"
            or value.get("status") != "PASS" or value.get("verified_trajectories") != 15
            or value.get("plan_hash") != continuous["summary"]["plan_hash"]
            or len(value["receipts"]) != 15):
        raise ValueError("matching_complete_continuous_replay_receipt_required")
    expected = {trace["row"]["report_hash"] for trace in continuous["traces"]}
    if {row["original_report_hash"] for row in value["receipts"]} != expected or any(
            row["replay"]["replay_verified"] is not True or row["independent_decimal_ledger"]["status"] != "PASS"
            for row in value["receipts"]):
        raise ValueError("continuous_replay_report_set_or_status_mismatch")
    return {"summary": value, "path": path}


def _link(text, path, output):
    relative = os.path.relpath(path, output.parent).replace(os.sep, "/")
    return "[" + escape(text) + "](" + quote(relative, safe="/._-") + ")"


def _number(value, kind, path, output):
    return _link(formatted(value, kind), path, output)


def render(continuous, diagnostics, forward, verification, output, inputs_path, narrative_sources=None):
    narrative_sources = narrative_sources or {}
    scope = continuous["summary"]["plan"]
    lines = ["# 哈基米只读研究视图", "", "当前研究限定为 BTC-USDT 现货 1h、固定规则、历史描述与独立空仓前向信号。账户、paper、live 和订单权限保持关闭。", "",
             "本页是固定证据生成的研究快照；当前发布与版本状态以 " + _link("CURRENT_STATUS.md", output.parent.parent / "CURRENT_STATUS.md", output) + " 为准。", "",
             "本视图不判定或执行版本发布；当前发布状态见上方 CURRENT_STATUS.md。性能：本轮未应用优化。", "",
             "数值从规范 JSON 生成，每个表内数字可点击回查原始投影。百分数显示三位小数，金额显示两位；空值显示不可估计 / 未提供。", "",
             "## 一次初始化的连续历史 · 0.2.1", "",
             f"评分区间 {_link(SCORE_START + ' 至 ' + SCORE_END + '（右端不含）', continuous['path'], output)}，只在起点初始化 {_number(scope['initial_cash'], 'money', continuous['path'], output)} USDT。跨月、季度保留同一条资金与持仓路径。", "",
             "25% 买入持有表示初始买入比例，之后不再平衡；价格上涨会使实际敞口高于 25%。所有数据已被查看，连续历史也不构成新的独立盲测。", ""]
    if verification:
        lines.append("独立重放：" + _number(verification["summary"]["verified_trajectories"], "count", verification["path"], output) + " / 15；逐项账本核验见同一证据。")
    else:
        lines.append("独立重放：待完整验收回执，不能由已生成轨迹数量推定通过。")
    headers = ["方法", "成本倍数"] + [label for _, label, _ in METRICS]
    def table(items, diagnostic=False):
        current_headers = headers + (["相对现金（百分点）", "相对 25% 初始买入持有（百分点）"] if diagnostic else [])
        result = ["", "| " + " | ".join(current_headers) + " |", "| " + " | ".join(["---"] * len(current_headers)) + " |"]
        for item in items:
            row, path = item["row"], item["path"]
            metrics = row if diagnostic else row["metrics"]
            cells = [_link(METHODS[row["method"]], path, output), _number(row["cost_factor"], "count", path, output)]
            cells += [_number(metrics[key], kind, path, output) for key, _, kind in METRICS]
            if diagnostic:
                cells += [_number(row[key], "pp", path, output) for key in ("return_minus_cash", "return_minus_buy_hold_25pct")]
            result.append("| " + " | ".join(cells) + " |")
        return result
    lines += table(continuous["traces"])
    lines += ["", "基础单边手续费 0.08%、滑点 0.05%；2× / 3× 同时放大这两项。成交次数包括每一笔成交，完整交易只数已结束的回合；期末持仓按市值计价，未虚构平仓。", "",
              "## 连续路径与逐窗重置的同区间对照 · 正常成本", "",
              "下表在连续路径上事后切片，并与原先每窗重新投入 10,000 USDT、空仓开始的结果比较。两种初始化语义不同；不相加或复利拼接 reset 收益。差异涉及携带仓位、成本与保护状态、挂起信号、完整指标历史及日内风控基准。", "",
              "| 区间 | 方法 | 连续切片收益 | 重置收益 | 差值（百分点） | 连续成交 | 重置成交 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for item in continuous["traces"]:
        if item["row"]["method"] not in {"dual_ma", "rsi"} or item["row"]["cost_factor"] != 1:
            continue
        for row in item["trace"]["reset_comparisons"]:
            cells = [_link(row["slice_id"], item["path"], output), METHODS[item["row"]["method"]]]
            cells += [_number(row[key], kind, item["path"], output) for key, kind in
                      (("total_return", "pct"), ("reset_total_return", "pct"), ("return_difference_vs_reset", "pp"),
                       ("fill_count", "count"), ("reset_fill_count", "count"))]
            lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## 单因素失效诊断 · 0.2.2", "",
              "此表单独标记新构建及规则版本，与上方 0.2.1 表不混排。D1 只取消固定止盈；R1 只限制每个连续超卖事件的一次入场意图。RSI 仍使用原有简单滚动均值定义。0 成本是重新执行的诊断，不是把费用加回收益，也不能用于晋级。", ""]
    if diagnostics:
        lines += table(diagnostics["traces"], True)
        lines += ["", "| 配对变体 | 成本倍数 | 收益差（百分点） | 回撤差（百分点） | 敞口差（百分点） | 费用与滑点差 USDT |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for item in diagnostics["traces"]:
            row = item["row"]
            if row["paired_change"] is None:
                continue
            pair = row["paired_change"]
            cells = [_link(row["method"] + " / " + pair["baseline"], diagnostics["path"], output),
                     _number(row["cost_factor"], "count", diagnostics["path"], output)]
            cells += [_number(pair[key], kind, diagnostics["path"], output) for key, kind in
                      (("total_return", "pp"), ("max_drawdown", "pp"), ("duration_weighted_close_exposure", "pp"), ("fee_plus_slippage_cost", "money"))]
            lines.append("| " + " | ".join(cells) + " |")
        if "strategy_conclusion" in narrative_sources:
            lines += ["", "**本轮结论：两个变体均未晋级，本轮停止追加调参，保留机制诊断。** 详见 "
                      + _link("本轮停止决定与机制解释", narrative_sources["strategy_conclusion"], output) + "。"]
    else:
        lines.append("诊断规范摘要尚未提供；暂不显示结果。")
    lines += ["", "少亏、降低敞口或少数已查看月份贡献的收益，均不能单独证明优势。此视图不自动选优、不晋级执行权限。"]
    if "performance_scope" in narrative_sources:
        lines += ["", "本轮实际性能测量仅覆盖受验收的 0.2.1 构建；新增 0.2.2 未测。未应用性能优化，也没有优化提速结论。详见 "
                  + _link("重复测量、冷暖口径与适用范围", narrative_sources["performance_scope"], output) + "。"]
    lines += ["", "## 前向观察覆盖 · 空仓参考信号", ""]
    f = forward["summary"]
    lines.append("观察时点：" + _link(f["as_of_utc"], forward["path"], output) + "。这些是 FLAT_REFERENCE_OBSERVATION 信号，未连续持仓，没有前向 PnL。")
    lines += ["", "| 计划策略小时 | 已到期策略小时 | 准时 | 迟到 | 缺失 | 失败 | 未来计划小时 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    numbers = [f["planned_strategy_hours"], f["elapsed_strategy_hours"], *[f["counts"][key] for key in ("ON_TIME", "LATE", "MISSING", "FAILED")], f["future_strategy_hours"]]
    lines.append("| " + " | ".join(_number(value, "count", forward["path"], output) for value in numbers) + " |")
    missing = sorted({row["cutoff"] for row in f["rows"] if row["status"] == "MISSING"})
    lines += ["", "缺失 cutoff：" + ("、".join(_link(value, forward["path"], output) for value in missing) if missing else "无已观察到的缺失。"), "",
              "72 小时验收状态：" + _link(f["soak_acceptance"], forward["path"], output) + "。未来 PLANNED 小时不进入失败分母；后续补录不会覆盖原 MISSING。", "",
              "ON_TIME 只表示 300 秒标准。新信号实际可用之后的下一个小时开盘才是参考成交资格时间；投影不提供成交价。既有仓位早已生效的保护条件不因新信号规则而被删除。", "",
              "## 证据与范围", "",
              "完整输入文件及 SHA256、规范报告身份、构建来源和生成命令见 " + _link("输入索引", inputs_path, output) + "。", "",
              "此工具只读取本地 JSON 及已审阅的 Markdown 来源并生成视图，不导入运行引擎、Provider、账户模块或管理路由；不收集市场数据，不运行回测，不更新部署。"]
    return "\n".join(lines) + "\n"


def build(root, continuous_path, diagnostic_path, forward_path, verification_path, output, inputs_path, *, require_complete=False):
    # Callers can use Windows short names or lexical aliases even without the
    # CLI. Use one canonical representation for containment and relative links.
    root, continuous_path, diagnostic_path, forward_path, verification_path, output, inputs_path = (
        Path(path).resolve() if path is not None else None
        for path in (root, continuous_path, diagnostic_path, forward_path, verification_path, output, inputs_path)
    )
    paths = [continuous_path, forward_path] + ([diagnostic_path] if diagnostic_path else []) + ([verification_path] if verification_path else [])
    if any(not path.is_relative_to(root) for path in paths + [output, inputs_path]):
        raise ValueError("view_inputs_and_outputs_must_stay_in_repository")
    continuous = load_continuous(continuous_path)
    diagnostics = load_diagnostics(diagnostic_path, continuous, root) if diagnostic_path else None
    forward = load_forward(forward_path)
    verification = load_verification(verification_path, continuous) if verification_path else None
    if require_complete and (diagnostics is None or verification is None):
        raise ValueError("complete_research_view_requires_diagnostics_and_continuous_replay")
    narrative_sources = {}
    candidates = {"performance_scope": root / "docs/research-evidence/performance-repeat-20260906/README.md"}
    if diagnostic_path:
        candidates["strategy_conclusion"] = diagnostic_path.parent / "README.md"
    for name, path in candidates.items():
        if path.is_file():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("narrative_source_must_stay_in_repository")
            if not path.read_text(encoding="utf-8").strip():
                raise ValueError("nonempty_narrative_source_required")
            narrative_sources[name] = path
        elif require_complete:
            raise ValueError("complete_research_view_requires_narrative_sources:" + name)
    entries = []
    for family, bundle in (("continuous", continuous), ("diagnostics", diagnostics), ("forward", forward), ("continuous_verification", verification)):
        if bundle is None:
            continue
        entries.append({"family": family, "kind": "summary", "path": bundle["path"].relative_to(root).as_posix(),
                        "file_sha256": sha(bundle["path"]), "schema_version": bundle["summary"]["schema_version"]})
        for trace in bundle.get("traces", []):
            entries.append({"family": family, "kind": "projection", "path": trace["path"].relative_to(root).as_posix(),
                            "file_sha256": sha(trace["path"]), "report_hash": trace["row"]["report_hash"],
                            "method": trace["row"]["method"], "cost_factor": trace["row"]["cost_factor"],
                            "runtime_source_sha256": trace["trace"]["source_identity"]["content_sha256"]})
        if "replay_path" in bundle:
            replay_path = bundle["replay_path"]
            entries.append({"family": family, "kind": "independent_replay_public_projection", "path": replay_path.relative_to(root).as_posix(),
                            "file_sha256": sha(replay_path), **bundle["replay_projection_identity"]})
        if "lineage_path" in bundle:
            lineage_path = bundle["lineage_path"]
            entries.append({"family": family, "kind": "input_derivation", "path": lineage_path.relative_to(root).as_posix(),
                            "file_sha256": sha(lineage_path)})
    command = ["python", "-B", "tools/build_research_view.py", "--root", ".", "--continuous", continuous_path.relative_to(root).as_posix(),
               "--forward", forward_path.relative_to(root).as_posix(), "--output", output.relative_to(root).as_posix(),
               "--inputs-index", inputs_path.relative_to(root).as_posix()]
    if diagnostic_path:
        command += ["--diagnostics", diagnostic_path.relative_to(root).as_posix()]
    if verification_path:
        command += ["--continuous-verification", verification_path.relative_to(root).as_posix()]
    if require_complete:
        command += ["--require-complete"]
    index = {"schema_version": "research-view-inputs-v1", "generator_sha256": sha(__file__), "command_argv": command,
             "inputs": entries, "source_versions": SOURCES, "continuous_trajectories": 15,
             "diagnostic_trajectories": 16 if diagnostics else None, "continuous_replay_verified": 15 if verification else None,
             "forward_as_of": forward["summary"]["as_of_utc"], "forward_72_hour_window_complete": forward["summary"]["window_elapsed"],
             "optimization_applied": False, "release_status": "SEE_CURRENT_STATUS", "order_allowed": False}
    for name, path in narrative_sources.items():
        entries.append({"family": name, "kind": "reviewed_narrative_source", "path": path.relative_to(root).as_posix(),
                        "file_sha256": sha(path)})
    markdown = render(continuous, diagnostics, forward, verification, output, inputs_path, narrative_sources)
    index["rendered_markdown_sha256"] = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8", newline="\n")
    inputs_path.write_text(json.dumps(index, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--continuous", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--forward", type=Path, required=True)
    parser.add_argument("--continuous-verification", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inputs-index", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    values = {key: value.resolve() if isinstance(value, Path) else value for key, value in vars(args).items()}
    result = build(values["root"], values["continuous"], values["diagnostics"], values["forward"], values["continuous_verification"],
                   values["output"], values["inputs_index"], require_complete=args.require_complete)
    print(json.dumps({"output": str(args.output), "verified_input_files": len(result["inputs"]),
                      "markdown_sha256": result["rendered_markdown_sha256"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
