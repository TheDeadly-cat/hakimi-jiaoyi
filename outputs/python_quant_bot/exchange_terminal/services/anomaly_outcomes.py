from __future__ import annotations

import math
from typing import Any


OUTCOME_META = {
    "NO_BASELINE": {"label": "无历史基线", "tone": "flat"},
    "EXCLUDED": {"label": "数据不纳入", "tone": "down"},
    "WATCH_ONLY": {"label": "仅观察", "tone": "flat"},
    "PENDING": {"label": "等待验证", "tone": "flat"},
    "MONITORING": {"label": "观察中", "tone": "flat"},
    "CONFIRMED": {"label": "方向已确认", "tone": "up"},
    "INVALIDATED": {"label": "方向已失效", "tone": "down"},
    "NO_FOLLOW_THROUGH": {"label": "无后续跟随", "tone": "down"},
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def anomaly_signal_bias(event: dict[str, Any]) -> str:
    direction = str(event.get("direction") or "")
    if direction == "偏多突破":
        return "LONG"
    if direction == "偏空下破":
        return "SHORT"
    return "WATCH"


def _eligible(event: dict[str, Any]) -> bool:
    quality = event.get("data_quality") if isinstance(event.get("data_quality"), dict) else {}
    priority = event.get("watch_priority") if isinstance(event.get("watch_priority"), dict) else {}
    level = str(priority.get("level") or "C").upper()
    return bool(
        level in {"A", "B"}
        and not event.get("data_quarantined")
        and not quality.get("quarantined")
        and not quality.get("fallback")
    )


def _evaluation_windows(event: dict[str, Any]) -> tuple[int, int]:
    market_type = str(event.get("market_type") or "").lower()
    if market_type.startswith("stock"):
        return 30 * 60 * 1000, 24 * 60 * 60 * 1000
    return 15 * 60 * 1000, 6 * 60 * 60 * 1000


def evaluate_anomaly_outcome(
    event: dict[str, Any],
    current_price: Any,
    evaluated_at_ms: int,
    *,
    min_horizon_ms: int | None = None,
    max_horizon_ms: int | None = None,
) -> dict[str, Any]:
    entry_price = _number(event.get("entry_price"))
    price = _number(current_price)
    first_seen = int(_number(event.get("first_seen")))
    default_min, default_max = _evaluation_windows(event)
    min_horizon = default_min if min_horizon_ms is None else max(0, int(min_horizon_ms))
    max_horizon = default_max if max_horizon_ms is None else max(min_horizon, int(max_horizon_ms))
    elapsed_ms = max(0, int(evaluated_at_ms) - first_seen) if first_seen else 0
    bias = anomaly_signal_bias(event)

    if entry_price <= 0:
        state = "NO_BASELINE"
        reason = "旧事件没有可信的首次价格，不回填推测值。"
    elif not _eligible(event):
        state = "EXCLUDED"
        reason = "数据源或观察优先级未通过，不进入后验统计。"
    elif bias == "WATCH":
        state = "WATCH_ONLY"
        reason = "事件没有明确多空方向，仅保留为行情观察。"
    elif price <= 0 or not first_seen:
        state = "PENDING"
        reason = "等待可用的后续价格。"
    elif elapsed_ms < min_horizon:
        state = "PENDING"
        reason = "尚未达到最短观察窗口。"
    else:
        raw_return_pct = (price - entry_price) / entry_price * 100
        directional_return_pct = raw_return_pct if bias == "LONG" else -raw_return_pct
        range_pct = abs(_number(event.get("range24h_pct")))
        threshold_pct = max(0.35, min(2.0, range_pct * 0.12))
        if directional_return_pct >= threshold_pct:
            state = "CONFIRMED"
            reason = "后续价格沿事件方向扩展，达到当前波动阈值。"
        elif directional_return_pct <= -threshold_pct:
            state = "INVALIDATED"
            reason = "后续价格反向运行，当前事件方向失效。"
        elif elapsed_ms >= max_horizon:
            state = "NO_FOLLOW_THROUGH"
            reason = "观察窗口结束，价格没有形成足够的方向跟随。"
        else:
            state = "MONITORING"
            reason = "已进入观察窗口，但尚未达到确认或失效阈值。"

    raw_return = (price - entry_price) / entry_price * 100 if entry_price > 0 and price > 0 else 0.0
    directional_return = raw_return if bias == "LONG" else -raw_return if bias == "SHORT" else 0.0
    range_pct = abs(_number(event.get("range24h_pct")))
    threshold = max(0.35, min(2.0, range_pct * 0.12))
    meta = OUTCOME_META[state]
    return {
        "state": state,
        "label": meta["label"],
        "tone": meta["tone"],
        "bias": bias,
        "entry_price": round(entry_price, 8),
        "current_price": round(price, 8),
        "raw_return_pct": round(raw_return, 2),
        "directional_return_pct": round(directional_return, 2),
        "threshold_pct": round(threshold, 2),
        "elapsed_ms": elapsed_ms,
        "evaluated_at": int(evaluated_at_ms),
        "counts_toward_stats": state in {"CONFIRMED", "INVALIDATED", "NO_FOLLOW_THROUGH"},
        "reason": reason,
    }


def anomaly_outcome_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    states = [str((event.get("outcome") or {}).get("state") or "NO_BASELINE") for event in events]
    confirmed = states.count("CONFIRMED")
    invalidated = states.count("INVALIDATED")
    no_follow = states.count("NO_FOLLOW_THROUGH")
    resolved = confirmed + invalidated + no_follow
    monitoring = states.count("PENDING") + states.count("MONITORING")
    excluded = states.count("EXCLUDED") + states.count("WATCH_ONLY")
    no_baseline = states.count("NO_BASELINE")
    sample_sufficient = resolved >= 5
    confirmation_rate = round(confirmed / resolved * 100, 1) if resolved else None
    false_signal_rate = round((invalidated + no_follow) / resolved * 100, 1) if resolved else None
    if resolved:
        summary = (
            f"后验完成 {resolved} 条：确认 {confirmed}，失效 {invalidated}，无跟随 {no_follow}"
            + (f"；方向确认率 {confirmation_rate:.1f}%" if sample_sufficient else "；样本少于5条，暂不展示确认率")
        )
    elif monitoring:
        summary = (
            f"已建立 {monitoring} 条可评估基线，等待观察窗口"
            + (f"；另有 {no_baseline} 条旧事件不回填价格" if no_baseline else "")
        )
    elif no_baseline:
        summary = "后验评估刚启用；旧事件没有首次价格，从新事件开始积累可信样本。"
    else:
        summary = "后验样本正在积累，达到观察窗口后再判断确认或失效。"
    return {
        "resolved": resolved,
        "confirmed": confirmed,
        "invalidated": invalidated,
        "no_follow_through": no_follow,
        "monitoring": monitoring,
        "excluded": excluded,
        "no_baseline": no_baseline,
        "sample_sufficient": sample_sufficient,
        "direction_confirmation_rate_pct": confirmation_rate,
        "false_signal_rate_pct": false_signal_rate,
        "summary": summary,
        "note": "方向确认率只描述已完成的规则样本，不代表未来胜率。",
    }
