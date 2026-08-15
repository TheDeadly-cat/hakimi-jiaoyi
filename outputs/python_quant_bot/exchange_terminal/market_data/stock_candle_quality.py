from __future__ import annotations

import math
from typing import Any


DEFAULT_BREAK_THRESHOLD_PCT = 45.0


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def analyze_stock_candle_series(
    rows: list[dict[str, Any]],
    *,
    break_threshold_pct: float = DEFAULT_BREAK_THRESHOLD_PCT,
    minimum_analysis_rows: int = 20,
) -> dict[str, Any]:
    clean_rows = [dict(row) for row in rows if _number(row.get("close")) > 0]
    clean_rows.sort(key=lambda row: (_number(row.get("ts")), str(row.get("date") or "")))
    threshold = max(10.0, abs(_number(break_threshold_pct, DEFAULT_BREAK_THRESHOLD_PCT)))
    breaks: list[dict[str, Any]] = []

    for index in range(1, len(clean_rows)):
        previous_close = _number(clean_rows[index - 1].get("close"))
        current_close = _number(clean_rows[index].get("close"))
        if previous_close <= 0 or current_close <= 0:
            continue
        move_pct = (current_close / previous_close - 1) * 100
        if abs(move_pct) < threshold:
            continue
        current = clean_rows[index]
        previous = clean_rows[index - 1]
        breaks.append({
            "index": index,
            "date": str(current.get("date") or current.get("ts") or "未知日期"),
            "previous_date": str(previous.get("date") or previous.get("ts") or "未知日期"),
            "previous_close": round(previous_close, 6),
            "current_close": round(current_close, 6),
            "move_pct": round(move_pct, 2),
            "previous_source": str(previous.get("source") or ""),
            "current_source": str(current.get("source") or ""),
        })

    segment_start = breaks[-1]["index"] if breaks else 0
    analysis_rows = clean_rows[segment_start:]
    latest_break = breaks[-1] if breaks else None
    has_break = bool(latest_break)
    analysis_ready = bool(analysis_rows) and (not has_break or len(analysis_rows) >= max(2, int(minimum_analysis_rows)))
    warning = ""
    if latest_break:
        warning = (
            f"检测到 {latest_break['date']} 相邻收盘 {latest_break['move_pct']:+.2f}% 的价格尺度断点，"
            "需核对复权、拆股或数据源口径。"
        )
    status = "REVIEW" if has_break and not analysis_ready else "DEGRADED" if has_break else "READY"
    return {
        "status": status,
        "has_break": has_break,
        "analysis_ready": analysis_ready,
        "break_threshold_pct": threshold,
        "breaks": breaks,
        "latest_break": latest_break,
        "total_rows": len(clean_rows),
        "segment_start": segment_start,
        "segment_rows": len(analysis_rows),
        "minimum_analysis_rows": max(2, int(minimum_analysis_rows)),
        "warning": warning,
        "analysis_rows": analysis_rows,
    }


def stock_candle_quality_public(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "analysis_rows"}
