from __future__ import annotations

import math
from typing import Any


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def temporal_data_split(
    rows: list[dict[str, Any]],
    *,
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
    minimum_segment_rows: int = 120,
    train_end_index: int | None = None,
    validation_end_index: int | None = None,
) -> dict[str, Any]:
    total = len(rows)
    if train_end_index is None or validation_end_index is None:
        train_end = int(total * train_ratio)
        validation_end = int(total * (train_ratio + validation_ratio))
        split_mode = "ROW_RATIO"
    else:
        train_end = max(0, min(int(train_end_index), total))
        validation_end = max(train_end, min(int(validation_end_index), total))
        split_mode = "CALENDAR_BOUNDARIES"
    segments = {
        "train": rows[:train_end],
        "validation": rows[train_end:validation_end],
        "test": rows[validation_end:],
    }
    boundaries = {
        "train": (0, train_end),
        "validation": (train_end, validation_end),
        "test": (validation_end, total),
    }
    metadata: dict[str, Any] = {}
    blockers: list[str] = []
    for name, segment in segments.items():
        count = len(segment)
        metadata[name] = {
            "count": count,
            "start_index": boundaries[name][0],
            "end_index": boundaries[name][1],
            "start": str(segment[0].get("date") or segment[0].get("ts") or "") if segment else "",
            "end": str(segment[-1].get("date") or segment[-1].get("ts") or "") if segment else "",
        }
        if count < minimum_segment_rows:
            blockers.append(f"{name} segment has {count} rows; requires {minimum_segment_rows}")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "total_rows": total,
        "minimum_segment_rows": minimum_segment_rows,
        "split_mode": split_mode,
        "segments": metadata,
        "rows": segments,
        "blockers": blockers,
    }


def chronological_folds(
    rows: list[dict[str, Any]],
    *,
    fold_count: int = 3,
    minimum_fold_rows: int = 120,
) -> dict[str, Any]:
    total = len(rows)
    safe_folds = max(2, min(int(fold_count or 3), 6))
    fold_size = total // safe_folds if safe_folds else 0
    folds: list[dict[str, Any]] = []
    blockers: list[str] = []
    for index in range(safe_folds):
        start = index * fold_size
        end = total if index == safe_folds - 1 else (index + 1) * fold_size
        fold_rows = rows[start:end]
        if len(fold_rows) < minimum_fold_rows:
            blockers.append(f"fold {index + 1} has {len(fold_rows)} rows; requires {minimum_fold_rows}")
        folds.append({
            "fold": index + 1,
            "rows": fold_rows,
            "count": len(fold_rows),
            "start_index": start,
            "end_index": end,
            "start": str(fold_rows[0].get("date") or fold_rows[0].get("ts") or "") if fold_rows else "",
            "end": str(fold_rows[-1].get("date") or fold_rows[-1].get("ts") or "") if fold_rows else "",
        })
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "folds": folds,
        "blockers": blockers,
        "minimum_fold_rows": minimum_fold_rows,
    }


def summarize_walk_forward(fold_reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = fold_reports if isinstance(fold_reports, list) else []
    usable: list[dict[str, Any]] = []
    invalid_values = False
    incomplete_rows = not isinstance(fold_reports, list)
    for item in rows:
        if not isinstance(item, dict) or item.get("ok") is not True:
            incomplete_rows = True
            continue
        total_return = _finite_number(item.get("total_return_pct"))
        max_drawdown = _finite_number(item.get("max_drawdown_pct"))
        trade_count = item.get("trade_count")
        valid_trade_count = (
            isinstance(trade_count, int)
            and not isinstance(trade_count, bool)
            and trade_count >= 0
        )
        if total_return is None or max_drawdown is None or not valid_trade_count:
            invalid_values = True
            continue
        usable.append(item)
    positive = [item for item in usable if _finite_number(item.get("total_return_pct")) > 0]
    complete = not incomplete_rows and not invalid_values and len(usable) == len(rows)
    total_trades = sum(item["trade_count"] for item in usable) if complete else None
    worst_drawdown = (
        max(_finite_number(item["max_drawdown_pct"]) for item in usable)
        if complete and usable
        else None
    )
    blockers: list[str] = []
    if incomplete_rows:
        blockers.append("时间折叠证据不完整")
    if invalid_values:
        blockers.append("可用时间折叠收益、回撤或交易数缺失/非有限")
    if len(usable) < 3:
        blockers.append("至少需要 3 个可用的时间顺序验证窗口")
    if len(positive) < 2:
        blockers.append("至少需要 2 个窗口取得正收益")
    if total_trades is not None and total_trades < 6:
        blockers.append("滚动验证累计闭合交易少于 6 笔")
    if worst_drawdown is not None and worst_drawdown >= 25:
        blockers.append(f"滚动验证最差回撤 {worst_drawdown:.2f}% 超过 25%")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "evaluation_mode": "FIXED_PARAMETER_CHRONOLOGICAL_SLICES",
        "parameters_refit_per_fold": False,
        "walk_forward_optimization_claim_allowed": False,
        "fold_count": len(rows),
        "usable_folds": len(usable),
        "positive_folds": len(positive),
        "total_trades": total_trades,
        "worst_drawdown_pct": round(worst_drawdown, 2) if worst_drawdown is not None else None,
        "blockers": blockers,
        "folds": rows,
    }


def summarize_cost_sensitivity(
    baseline: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_return = _finite_number(baseline.get("total_return_pct")) if isinstance(baseline, dict) else None
    scenario_rows = scenarios if isinstance(scenarios, list) else []
    usable: list[dict[str, Any]] = []
    invalid_usable_values = False
    for item in scenario_rows:
        if not isinstance(item, dict) or item.get("ok") is not True:
            continue
        scenario_return = _finite_number(item.get("total_return_pct"))
        scenario_drawdown = _finite_number(item.get("max_drawdown_pct"))
        if scenario_return is None or scenario_drawdown is None:
            invalid_usable_values = True
            continue
        usable.append(item)
    complete = bool(scenario_rows) and len(usable) == len(scenario_rows) and not invalid_usable_values
    worst_return = min((_finite_number(item.get("total_return_pct")) for item in usable), default=None) if complete else None
    worst_drawdown = max((_finite_number(item.get("max_drawdown_pct")) for item in usable), default=None) if complete else None
    degradation = baseline_return - worst_return if baseline_return is not None and worst_return is not None else None
    allowed_degradation = max(5.0, abs(baseline_return) * 0.75) if baseline_return is not None else None
    blockers: list[str] = []
    if baseline_return is None:
        blockers.append("基准收益缺失或非有限")
    if not complete:
        blockers.append("费用滑点压力场景不完整")
    if invalid_usable_values:
        blockers.append("可用压力场景收益或回撤缺失/非有限")
    if worst_return is not None and worst_return <= 0:
        blockers.append(f"压力成本下最差收益 {worst_return:.2f}% 未保持正值")
    if degradation is not None and allowed_degradation is not None and degradation > allowed_degradation:
        blockers.append(f"压力成本使收益恶化 {degradation:.2f}%，超过容忍值 {allowed_degradation:.2f}%")
    if worst_drawdown is not None and worst_drawdown >= 30:
        blockers.append(f"压力场景最差回撤 {worst_drawdown:.2f}% 超过 30%")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "baseline_return_pct": round(baseline_return, 2) if baseline_return is not None else None,
        "worst_return_pct": round(worst_return, 2) if worst_return is not None else None,
        "break_even_preserved": (
            worst_return > 0
            if baseline_return is not None and complete and worst_return is not None
            else None
        ),
        "minimum_stressed_return_pct": 0.0,
        "return_degradation_pct": round(degradation, 2) if degradation is not None else None,
        "allowed_degradation_pct": round(allowed_degradation, 2) if allowed_degradation is not None else None,
        "worst_drawdown_pct": round(worst_drawdown, 2) if worst_drawdown is not None else None,
        "blockers": blockers,
        "scenarios": scenario_rows,
    }
