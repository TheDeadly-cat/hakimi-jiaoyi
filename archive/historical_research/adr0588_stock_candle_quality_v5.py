from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any

from hakimi_research.stock_data_quality import (
    AUTHORITY_LOCK,
    SAFE_ACTION,
    STOCK_DATA_QUALITY_BOUNDARY_VERSION,
    STOCK_MARKET_DATA_GOVERNANCE_VERSION,
    native_epoch_ms,
    native_finite_number,
)
from hakimi_research.stock_metadata import (
    is_stock_symbol,
    normalize_stock_interval,
    stock_meta,
    stock_timezone,
)


STOCK_CANDLE_QUALITY_CONTRACT_VERSION = "stock-candle-quality-v5"
STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION = "stock-candle-temporal-conformance-v2"
DEFAULT_BREAK_THRESHOLD_PCT = 45.0
_REQUIRED_PRICE_FIELDS = ("open", "high", "low", "close")
_SUPPORTED_INTERVALS = {
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "60m",
    "4h",
    "1d",
    "1dutc",
}


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


def _row_timestamp(row: dict[str, Any]) -> Any:
    return row.get("ts") if "ts" in row else row.get("ts_ms")


def _temporal_context(symbol: Any, interval: Any, source: Any) -> dict[str, Any]:
    symbol_valid = type(symbol) is str and bool(symbol) and is_stock_symbol(symbol)
    interval_valid = type(interval) is str and interval.lower() in _SUPPORTED_INTERVALS
    source_valid = type(source) is str and bool(source.strip())
    clean_symbol = _text(stock_meta(symbol).get("symbol")) if symbol_valid else ""
    normalized_interval = normalize_stock_interval(interval)[0] if interval_valid else ""
    timezone_value = stock_timezone(clean_symbol) if clean_symbol else None
    return {
        "valid": symbol_valid and interval_valid and source_valid,
        "symbol": clean_symbol,
        "interval": normalized_interval,
        "source": source.strip().lower() if source_valid else "",
        "timezone": getattr(timezone_value, "key", ""),
        "timezone_object": timezone_value,
    }


def _source_temporal_semantics(source: str, interval: str) -> str:
    daily = interval in {"1d", "1dutc"}
    if not source:
        return "UNVERIFIED"
    known = (
        source in {"futu", "stooq", "test", "synthetic", "synthetic_fixture"}
        or source.startswith("yahoo")
        or source.endswith("_intraday_daily")
    )
    if not known:
        return "UNVERIFIED"
    if daily:
        if source.startswith("yahoo"):
            return "DAILY_UTC_DATE"
        if source in {"futu", "stooq"} or source.endswith("_intraday_daily"):
            return "DAILY_SYMBOL_LOCAL_DATE"
        return "SYNTHETIC_DAILY_UTC_OR_SYMBOL_LOCAL_DATE"
    if source.startswith("yahoo"):
        return "INTRADAY_UTC_DATE"
    return "INTRADAY_SYMBOL_LOCAL_DATE"


def _temporal_conformance(
    rows: list[dict[str, Any]],
    *,
    symbol: Any,
    interval: Any,
    source: Any,
) -> dict[str, Any]:
    context = _temporal_context(symbol, interval, source)
    invalid_rows: list[dict[str, Any]] = []
    semantics: set[str] = set()
    if context["valid"]:
        timezone_value = context["timezone_object"]
        for index, row in enumerate(rows):
            reasons: list[str] = []
            date_value = row.get("date")
            try:
                row_date = (
                    date.fromisoformat(date_value)
                    if type(date_value) is str and date_value
                    else None
                )
            except ValueError:
                row_date = None
            timestamp_ms = native_epoch_ms(_row_timestamp(row))
            row_source_value = row.get("source")
            row_source = (
                row_source_value.strip().lower()
                if type(row_source_value) is str and row_source_value.strip()
                else context["source"]
            )
            row_semantics = _source_temporal_semantics(
                row_source,
                context["interval"],
            )
            semantics.add(row_semantics)
            if row_date is None:
                reasons.append("DATE_REQUIRED_FOR_TEMPORAL_CONFORMANCE")
            if timestamp_ms is None:
                reasons.append("TIMESTAMP_REQUIRED_FOR_TEMPORAL_CONFORMANCE")
            if row_semantics == "UNVERIFIED":
                reasons.append("SOURCE_TIMESTAMP_SEMANTICS_UNVERIFIED")
            if not reasons:
                utc_date = datetime.fromtimestamp(
                    timestamp_ms / 1000,
                    timezone.utc,
                ).date()
                local_date = datetime.fromtimestamp(
                    timestamp_ms / 1000,
                    timezone_value,
                ).date()
                if row_semantics == "DAILY_UTC_DATE":
                    aligned = row_date == utc_date
                elif row_semantics == "DAILY_SYMBOL_LOCAL_DATE":
                    aligned = row_date == local_date
                elif row_semantics == "SYNTHETIC_DAILY_UTC_OR_SYMBOL_LOCAL_DATE":
                    aligned = row_date in {utc_date, local_date}
                elif row_semantics == "INTRADAY_UTC_DATE":
                    aligned = row_date == utc_date
                else:
                    aligned = row_date == local_date
                if not aligned:
                    reasons.append("DATE_TIMESTAMP_TIMEZONE_MISMATCH")
            if reasons:
                invalid_rows.append({"index": index, "reasons": reasons})
    else:
        invalid_rows.append({
            "index": None,
            "reasons": ["SYMBOL_INTERVAL_SOURCE_CONTEXT_REQUIRED"],
        })
    complete = context["valid"] and bool(rows) and not invalid_rows
    return {
        "contract_version": STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
        "governance_version": STOCK_MARKET_DATA_GOVERNANCE_VERSION,
        "status": "PASS" if complete else "BLOCK",
        "complete": complete,
        "symbol": context["symbol"],
        "interval": context["interval"],
        "source": context["source"],
        "timezone": context["timezone"],
        "source_semantics": sorted(semantics),
        "invalid_row_count": len(invalid_rows),
        "invalid_rows": invalid_rows,
        "exchange_calendar_attested": False,
        "authority": dict(AUTHORITY_LOCK),
        "safe_action": SAFE_ACTION,
    }


def _row_quality(row: Any) -> tuple[dict[str, Any] | None, list[str], bool, bool]:
    if type(row) is not dict:
        return None, ["ROW_CONTAINER_NOT_EXACT_DICT"], False, False
    reasons: list[str] = []
    if native_epoch_ms(_row_timestamp(row)) is None:
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
    symbol: str = "",
    interval: str = "",
    source: str = "",
    break_threshold_pct: float = DEFAULT_BREAK_THRESHOLD_PCT,
    minimum_analysis_rows: int = 20,
) -> dict[str, Any]:
    container_valid = type(rows) is list
    native_rows = rows if container_valid else []
    clean_rows: list[dict[str, Any]] = []
    analysis_eligible_rows: list[dict[str, Any]] = []
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
        if completion_known and not incomplete:
            analysis_eligible_rows.append(clean)
        completion_unknown_count += int(not completion_known)
        incomplete_row_count += int(incomplete)
        date_missing_count += int(clean.get("date") in {None, ""})

    temporal_conformance = _temporal_conformance(
        clean_rows,
        symbol=symbol,
        interval=interval,
        source=source,
    )
    temporal_complete = temporal_conformance["complete"] is True
    timestamps = [native_epoch_ms(_row_timestamp(row)) for row in clean_rows]
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
        for index in range(1, len(analysis_eligible_rows)):
            previous_close = float(analysis_eligible_rows[index - 1]["close"])
            current_close = float(analysis_eligible_rows[index]["close"])
            move_pct = (current_close / previous_close - 1) * 100
            if abs(move_pct) < threshold:
                continue
            current = analysis_eligible_rows[index]
            previous = analysis_eligible_rows[index - 1]
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
    candidate_rows = (
        analysis_eligible_rows[segment_start:]
        if structure_complete and temporal_complete
        else []
    )
    latest_break = breaks[-1] if breaks else None
    has_break = latest_break is not None
    analysis_ready = (
        structure_complete
        and temporal_complete
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
    if not temporal_complete:
        warnings.append(
            f"{temporal_conformance['invalid_row_count']} candle temporal conformance issue(s) detected."
        )
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

    if (
        not structure_complete
        or not temporal_complete
        or not clean_rows
        or not candidate_rows
    ):
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
        "governance_version": STOCK_MARKET_DATA_GOVERNANCE_VERSION,
        "status": status,
        "structure_complete": structure_complete,
        "temporal_conformance_complete": temporal_complete,
        "temporal_conformance": temporal_conformance,
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
        "analysis_eligible_row_count": len(analysis_eligible_rows),
        "analysis_excluded_row_count": len(clean_rows) - len(analysis_eligible_rows),
        "analysis_row_count": len(candidate_rows),
        "date_missing_count": date_missing_count,
        "date_timestamp_alignment": "PASS" if temporal_complete else "BLOCK",
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
            "governance_version": STOCK_MARKET_DATA_GOVERNANCE_VERSION,
            "status": "BLOCK",
            "structure_complete": False,
            "temporal_conformance_complete": False,
            "analysis_ready": False,
            "warning": "Invalid candle-quality report container.",
            "authority": dict(AUTHORITY_LOCK),
            "safe_action": SAFE_ACTION,
        }
    return {key: value for key, value in report.items() if key != "analysis_rows"}


__all__ = [
    "DEFAULT_BREAK_THRESHOLD_PCT",
    "STOCK_CANDLE_QUALITY_CONTRACT_VERSION",
    "STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION",
    "analyze_stock_candle_series",
    "stock_candle_quality_public",
]
