from __future__ import annotations

import math
from datetime import date
from typing import Any

from hakimi_research.stock_data_quality import (
    AUTHORITY_LOCK,
    SAFE_ACTION,
    STOCK_DATA_QUALITY_BOUNDARY_VERSION,
    native_epoch_ms,
    native_finite_number,
)


STOCK_CANDLE_QUALITY_CONTRACT_VERSION = "stock-candle-quality-v2"
DEFAULT_BREAK_THRESHOLD_PCT = 45.0
_REQUIRED_PRICE_FIELDS = ("open", "high", "low", "close")


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
    return 20


def _row_quality(row: Any) -> tuple[dict[str, Any] | None, list[str], bool, bool]:
    if type(row) is not dict:
        return None, ["ROW_CONTAINER_NOT_EXACT_DICT"], False, False
    reasons: list[str] = []
    if native_epoch_ms(row.get("ts")) is None:
        reasons.append("TIMESTAMP_INVALID")
    prices: dict[str, float] = {}
    for field in _REQUIRED_PRICE_FIELDS:
        value = native_finite_number(row.get(field))
        if value is None or value <= 0:
            reasons.append(f"{field.upper()}_INVALID")
        else:
            prices[field] = value
    volume = native_finite_number(row.get("volume"))
    if volume is None or volume < 0:
        reasons.append("VOLUME_INVALID")
    if len(prices) == len(_REQUIRED_PRICE_FIELDS):
        if prices["high"] < max(prices["open"], prices["low"], prices["close"]):
            reasons.append("HIGH_BELOW_OHLC_MAX")
        if prices["low"] > min(prices["open"], prices["high"], prices["close"]):
            reasons.append("LOW_ABOVE_OHLC_MIN")
    date_value = row.get("date")
    date_missing = date_value is None or (
        type(date_value) is str and date_value == ""
    )
    if not date_missing:
        if type(date_value) is not str:
            reasons.append("DATE_NOT_EXACT_STRING")
        else:
            try:
                date.fromisoformat(date_value)
            except ValueError:
                reasons.append("DATE_NOT_ISO8601")
    complete_value = row.get("complete")
    completion_known = type(complete_value) is bool
    if complete_value is not None and not completion_known:
        reasons.append("COMPLETE_NOT_EXACT_BOOL")
    provisional_value = row.get("provisional")
    if provisional_value is not None and type(provisional_value) is not bool:
        reasons.append("PROVISIONAL_NOT_EXACT_BOOL")
    source_value = row.get("source")
    if source_value is not None and type(source_value) is not str:
        reasons.append("SOURCE_NOT_EXACT_STRING")
    clean = dict(row) if not reasons else None
    incomplete = completion_known and complete_value is False
    return clean, reasons, completion_known, incomplete


def analyze_stock_candle_series(
    rows: list[dict[str, Any]],
    *,
    break_threshold_pct: float = DEFAULT_BREAK_THRESHOLD_PCT,
    minimum_analysis_rows: int = 20,
) -> dict[str, Any]:
    container_valid = type(rows) is list
    native_rows = rows if container_valid else []
    clean_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    completion_unknown_count = 0
    incomplete_row_count = 0
    date_missing_count = 0
    for index, row in enumerate(native_rows):
        clean, reasons, completion_known, incomplete = _row_quality(row)
        if reasons:
            invalid_rows.append({"index": index, "reasons": reasons})
            continue
        assert clean is not None
        clean_rows.append(clean)
        completion_unknown_count += int(not completion_known)
        incomplete_row_count += int(incomplete)
        date_missing_count += int(clean.get("date") in {None, ""})

    timestamps = [native_epoch_ms(row.get("ts")) for row in clean_rows]
    duplicate_timestamp_count = len(timestamps) - len(set(timestamps))
    out_of_order = any(
        current is None or previous is None or current <= previous
        for previous, current in zip(timestamps, timestamps[1:])
    )
    structure_complete = (
        container_valid
        and not invalid_rows
        and duplicate_timestamp_count == 0
        and not out_of_order
        and len(clean_rows) == len(native_rows)
    )
    threshold = max(10.0, abs(_number(break_threshold_pct, DEFAULT_BREAK_THRESHOLD_PCT)))
    minimum_rows = _minimum_rows(minimum_analysis_rows)
    breaks: list[dict[str, Any]] = []
    if structure_complete:
        for index in range(1, len(clean_rows)):
            previous_close = float(clean_rows[index - 1]["close"])
            current_close = float(clean_rows[index]["close"])
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
    candidate_rows = clean_rows[segment_start:] if structure_complete else []
    latest_break = breaks[-1] if breaks else None
    has_break = latest_break is not None
    analysis_ready = (
        structure_complete
        and bool(candidate_rows)
        and (not has_break or len(candidate_rows) >= minimum_rows)
    )
    warnings: list[str] = []
    if not container_valid:
        warnings.append("Candle rows container is not an exact list.")
    if invalid_rows:
        warnings.append(f"{len(invalid_rows)} candle row(s) failed OHLCV structure validation.")
    if duplicate_timestamp_count:
        warnings.append(f"{duplicate_timestamp_count} duplicate candle timestamp(s) detected.")
    if out_of_order:
        warnings.append("Candle timestamps are not strictly increasing in source order.")
    if latest_break:
        warnings.append(
            f"检测到 {latest_break['date']} 相邻收盘 {latest_break['move_pct']:+.2f}% 的价格尺度断点，"
            "需核对复权、拆股或数据源口径。"
        )
    if completion_unknown_count:
        warnings.append(f"{completion_unknown_count} candle row(s) lack exact completion evidence.")
    if incomplete_row_count:
        warnings.append(f"{incomplete_row_count} candle row(s) are explicitly incomplete.")
    if date_missing_count:
        warnings.append(f"{date_missing_count} candle row(s) lack an ISO calendar date.")
    if not clean_rows and not warnings:
        warnings.append("No exact-native complete OHLCV candle rows.")

    if not structure_complete or not clean_rows:
        status = "BLOCK"
    elif has_break and not analysis_ready:
        status = "REVIEW"
    elif has_break or completion_unknown_count or incomplete_row_count or date_missing_count:
        status = "DEGRADED"
    else:
        status = "PASS"
    return {
        "contract_version": STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
        "quality_boundary_version": STOCK_DATA_QUALITY_BOUNDARY_VERSION,
        "status": status,
        "structure_complete": structure_complete,
        "has_break": has_break,
        "analysis_ready": analysis_ready,
        "break_threshold_pct": threshold,
        "breaks": breaks,
        "latest_break": latest_break,
        "input_row_count": len(native_rows),
        "total_rows": len(clean_rows),
        "valid_row_count": len(clean_rows),
        "invalid_row_count": len(invalid_rows),
        "invalid_rows": invalid_rows,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "timestamps_strictly_increasing": not out_of_order,
        "completion_unknown_count": completion_unknown_count,
        "incomplete_row_count": incomplete_row_count,
        "date_missing_count": date_missing_count,
        "date_timestamp_alignment": "UNVERIFIED_WITHOUT_SYMBOL_TIMEZONE_CONTRACT",
        "segment_start": segment_start,
        "segment_rows": len(candidate_rows),
        "minimum_analysis_rows": minimum_rows,
        "warning": " / ".join(warnings),
        "analysis_rows": candidate_rows,
        "authority": dict(AUTHORITY_LOCK),
        "safe_action": SAFE_ACTION,
    }


def stock_candle_quality_public(report: dict[str, Any]) -> dict[str, Any]:
    if type(report) is not dict:
        return {
            "contract_version": STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
            "quality_boundary_version": STOCK_DATA_QUALITY_BOUNDARY_VERSION,
            "status": "BLOCK",
            "structure_complete": False,
            "analysis_ready": False,
            "warning": "Invalid candle-quality report container.",
            "authority": dict(AUTHORITY_LOCK),
            "safe_action": SAFE_ACTION,
        }
    return {key: value for key, value in report.items() if key != "analysis_rows"}


__all__ = [
    "DEFAULT_BREAK_THRESHOLD_PCT",
    "STOCK_CANDLE_QUALITY_CONTRACT_VERSION",
    "analyze_stock_candle_series",
    "stock_candle_quality_public",
]
