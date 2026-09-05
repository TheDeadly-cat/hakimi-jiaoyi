"""Describe the complete prespecified matrix without choosing a winning cell."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import pandas as pd

from hakimi_research.dataset_registry import load_snapshot
from hakimi_research.documents import digest, read_document
from hakimi_research.experiment import verify_report
from hakimi_research.reporting import save_json_report


def _states(frame):
    trend = frame["close"].shift(1) / frame["close"].shift(25) - 1
    volatility = frame["close"].pct_change().rolling(24, min_periods=24).std().shift(1)
    labels = {}
    for timestamp in frame.index:
        if pd.isna(trend.loc[timestamp]) or pd.isna(volatility.loc[timestamp]):
            labels[timestamp] = "INSUFFICIENT_CONTEXT"
        elif volatility.loc[timestamp] >= 0.01:
            labels[timestamp] = "HIGH_VOL"
        elif trend.loc[timestamp] >= 0.02:
            labels[timestamp] = "UP"
        elif trend.loc[timestamp] <= -0.02:
            labels[timestamp] = "DOWN"
        else:
            labels[timestamp] = "RANGE"
    return labels


def _publish_markdown(path, content):
    encoded = content.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".markdown-", dir=path.parent)
    staged = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(staged, path)
        except FileExistsError:
            if path.read_bytes() != encoded:
                raise
    finally:
        staged.unlink(missing_ok=True)


def summarize(study_path: Path, snapshot_path: Path, output: Path):
    study = read_document(study_path)
    snapshot = load_snapshot(snapshot_path)
    if study["snapshot_id"] != snapshot.snapshot_id or study["planned_attempt_count"] != 16 or len(study["attempts"]) != 16:
        raise ValueError("complete_prespecified_16_cell_study_required")
    labels = _states(snapshot.frame())
    rows, slices, reports = [], [], []
    for attempt in study["attempts"]:
        if attempt["returncode"] != 0:
            raise ValueError("failed_study_cell_must_be_resolved_or_reported_explicitly")
        path = Path(json.loads(attempt["stdout"])["full_report"])
        report = verify_report(read_document(path))
        reports.append(report)
        result, spec = report["result"], report["spec"]
        rows.append({"strategy": attempt["strategy"], "cell": attempt["cell"], "cost_factor": attempt["cost_factor"],
                     "spec_hash": report["spec_hash"], "report_hash": report["report_hash"], "report": str(path),
                     "computation_id": report["computation_id"],
                     **{key: result[key] for key in ("total_return", "max_drawdown", "final_equity", "fill_count",
                        "round_trip_count", "total_fees", "buy_fees", "sell_fees", "realized_pnl", "unrealized_pnl",
                        "open_position_qty", "exposure_ratio", "statistical_status")}})
        if attempt["cell"] != "base" or attempt["cost_factor"] != 1:
            continue
        buckets = {label: {"returns": [], "pnl": [], "exposure": []} for label in ("HIGH_VOL", "UP", "DOWN", "RANGE")}
        points = result["equity_curve"]
        for previous, current in zip(points, points[1:]):
            label = labels[pd.Timestamp(current["bar_time"])]
            if label not in buckets:
                raise ValueError("state_context_insufficient_at_score")
            buckets[label]["returns"].append(current["equity"] / previous["equity"] - 1)
            buckets[label]["pnl"].append(current["equity"] - previous["equity"])
            buckets[label]["exposure"].append(current["position_value"] / current["equity"])
        if abs(sum(sum(bucket["pnl"]) for bucket in buckets.values()) - (result["final_equity"] - spec["initial_cash"])) > 1e-7:
            raise ValueError("state_pnl_contribution_does_not_reconcile")
        for label, bucket in buckets.items():
            count = len(bucket["returns"])
            slices.append({"strategy": attempt["strategy"], "state": label, "bar_count": count,
                           "mean_observed_bar_return": sum(bucket["returns"]) / count if count else None,
                           "pnl_contribution_usdt": sum(bucket["pnl"]),
                           "mean_close_exposure": sum(bucket["exposure"]) / count if count else None,
                           "status": "INSUFFICIENT_EVIDENCE" if count < 30 else "DESCRIPTIVE_DEPENDENT_OBSERVATIONS"})
    cash = next(row for row in rows if row["strategy"] == "cash" and row["cost_factor"] == 1)
    passive = {row["cost_factor"]: row for row in rows if row["strategy"] == "buy_and_hold"}
    for row in rows:
        row["return_minus_cash"] = row["total_return"] - cash["total_return"]
        row["return_minus_same_cost_buy_hold"] = row["total_return"] - passive[row["cost_factor"]]["total_return"]
    summary = {"schema_version": "descriptive-study-summary-v1", "snapshot_id": snapshot.snapshot_id,
               "dataset_quality": snapshot.document["quality"], "planned_attempt_count": 16, "completed_attempt_count": len(rows),
               "rows": rows, "state_slices": slices,
               "state_rules": {"prior_bars": 24, "high_vol_sample_std_threshold": 0.01, "trend_return_threshold": 0.02,
                               "timing": "ONLY_PRIOR_COMPLETED_BARS", "disjoint_slice_strategy_simulation": False},
               "source_report_hashes": [r["report_hash"] for r in reports],
               "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "data_previously_viewed": True, "parameter_selection": False, "confirmation_evaluation": False,
               "execution_permission": reports[0]["execution_permission"],
               "limits": ["One historical month; overlapping observations are dependent; no confirmation evidence.",
                          "Costs and next-open OHLC fills are approximations, not executable quotes.",
                          "Cash has no trades by design; Buy-and-Hold has an open marked position, not completed round trips.",
                          "Benchmark exposure differs; raw return differences are descriptive, not risk-adjusted superiority.",
                          "Final holdings are not liquidated; all16 cells and all negative or inactive results are retained."]}
    output.mkdir(parents=True, exist_ok=True)
    identity = digest(summary)
    json_path = save_json_report(summary, output, "summary", artifact_id=identity)
    lines = ["# BTC-USDT 现货 1h：固定快照描述性研究", "",
             "已执行全部16个预先列出的研究单元；没有选优、调参晋级或确认评估。数据在扩展计划前已被查看。", "",
             "输入744根完整小时线；评分为2026-08-04至2026-09-01（右端不含），672根；预热72根不交易。", "",
             "| 方法 | 单元 | 成本倍数 | 收益 | 最大回撤 | 成交/完整交易 | 累计费用 USDT | 平均收盘敞口 |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['strategy']} | {row['cell']} | {row['cost_factor']} | {row['total_return']:.3%} | {row['max_drawdown']:.3%} | {row['fill_count']}/{row['round_trip_count']} | {row['total_fees']:.4f} | {row['exposure_ratio']:.2%} |")
    lines += ["", "现金零成交是基准定义；买入持有仅在评分开始买入，期末持仓按市值记账，不虚构卖出。完整JSON包含现金、持仓、成交、费用、已实现/未实现损益、参数和证据状态。", "",
              "## 预定义状态切片", "", "状态只使用上一根及更早的24根完成线；高波动优先，否则按±2%趋势分类。收益贡献按实际净值变化相加，不把不连续状态拼成另一条可交易策略。", "",
              "| 方法 | 状态 | 小时数 | 损益贡献 USDT | 证据状态 |", "|---|---|---:|---:|---|"]
    for row in slices:
        lines.append(f"| {row['strategy']} | {row['state']} | {row['bar_count']} | {row['pnl_contribution_usdt']:.4f} | {row['status']} |")
    lines += ["", "## 限制与下一问题", "", "一个月的历史、相关性很高的小时收益和少量完整交易不足以支持稳定优势。不同方法敞口不同，表中收益差不能直接解释成风险调整后的胜负。", "",
              "下一问题是扩大预先声明的历史覆盖后，计算、成本敏感性与状态差异是否仍然一致；本次不据此扩展参数搜索或授予账户执行权限。", "",
              f"数据快照：`{snapshot.snapshot_id}`。全部细项和报告路径见 `{Path(json_path).name}`。",
              "独立账本对账与第二安装环境重放记录单独保存；本摘要不把尚未读取的重放结果自动写成通过。", ""]
    md_path = output / ("summary_" + identity + ".md")
    _publish_markdown(md_path, "\n".join(lines))
    print(json.dumps({"summary": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.study, args.snapshot, args.output_dir)
