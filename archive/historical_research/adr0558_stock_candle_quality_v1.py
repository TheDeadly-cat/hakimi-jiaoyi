from __future__ import annotations

import math
from typing import Any


STOCK_CANDLE_QUALITY_CONTRACT_VERSION = "stock-candle-quality-v1"
DEFAULT_BREAK_THRESHOLD_PCT = 45.0


def _number(value: Any, default: float = 0.0) -> float:
    if type(value) in {int, float}:
        parsed = float(value)
    elif type(value) is str:
        try:
            parsed = float(value)
        except ValueError:
            return default
    else:
        return default
    return parsed if math.isfinite(parsed) else default


def _text(value: Any, default: str = "") -> str:
    return value if type(value) is str else default


def _display(value: Any, default: str) -> str:
    if type(value) is str:
        return value
    if type(value) in {int, float} and math.isfinite(float(value)):
        return str(value)
    return default


def _minimum_rows(value: Any) -> int:
    if type(value) is int:
        return max(2, value)
    if type(value) is float and math.isfinite(value):
        return max(2, int(value))
    return 20


def analyze_stock_candle_series(
    rows: list[dict[str, Any]],
    *,
    break_threshold_pct: float = DEFAULT_BREAK_THRESHOLD_PCT,
    minimum_analysis_rows: int = 20,
) -> dict[str, Any]:
    native_rows = rows if type(rows) is list else []
    clean_rows = [
        dict(row)
        for row in native_rows
        if type(row) is dict and _number(row.get("close")) > 0
    ]
    clean_rows.sort(key=lambda row: (_number(row.get("ts")), _text(row.get("date"))))
    threshold = max(10.0, abs(_number(break_threshold_pct, DEFAULT_BREAK_THRESHOLD_PCT)))
    minimum_rows = _minimum_rows(minimum_analysis_rows)
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
            "date": _display(current.get("date", current.get("ts")), "unknown-date"),
            "previous_date": _display(previous.get("date", previous.get("ts")), "unknown-date"),
            "previous_close": round(previous_close, 6),
            "current_close": round(current_close, 6),
            "move_pct": round(move_pct, 2),
            "previous_source": _text(previous.get("source")),
            "current_source": _text(current.get("source")),
        })

    segment_start = breaks[-1]["index"] if breaks else 0
    analysis_rows = clean_rows[segment_start:]
    latest_break = breaks[-1] if breaks else None
    has_break = latest_break is not None
    analysis_ready = bool(analysis_rows) and (not has_break or len(analysis_rows) >= minimum_rows)
    warning = ""
    if latest_break:
        warning = (
            f"检测到 {latest_break['date']} 相邻收盘 {latest_break['move_pct']:+.2f}% 的价格尺度断点，"
            "需核对复权、拆股或数据源口径。"
        )
    elif not analysis_rows:
        warning = "No exact-native positive-close candle rows."
    if not analysis_rows:
        status = "BLOCK"
    elif has_break and not analysis_ready:
        status = "REVIEW"
    elif has_break:
        status = "DEGRADED"
    else:
        status = "PASS"
    return {
        "contract_version": STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
        "status": status,
        "has_break": has_break,
        "analysis_ready": analysis_ready,
        "break_threshold_pct": threshold,
        "breaks": breaks,
        "latest_break": latest_break,
        "total_rows": len(clean_rows),
        "segment_start": segment_start,
        "segment_rows": len(analysis_rows),
        "minimum_analysis_rows": minimum_rows,
        "warning": warning,
        "analysis_rows": analysis_rows,
    }


def stock_candle_quality_public(report: dict[str, Any]) -> dict[str, Any]:
    if type(report) is not dict:
        return {
            "contract_version": STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
            "status": "BLOCK",
            "analysis_ready": False,
            "warning": "Invalid candle-quality report container.",
        }
    return {key: value for key, value in report.items() if key != "analysis_rows"}


__all__ = [
    "DEFAULT_BREAK_THRESHOLD_PCT",
    "STOCK_CANDLE_QUALITY_CONTRACT_VERSION",
    "analyze_stock_candle_series",
    "stock_candle_quality_public",
]
