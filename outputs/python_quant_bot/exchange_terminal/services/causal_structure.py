"""Causal, confirmed-only price structure over a frozen completed OHLC series.

Pivots require a strict unique extreme over their full left/right window. Equal
extremes inside that window are not pivots. Equal prices between separately
confirmed pivots are reported as EQUAL_HIGH/EQUAL_LOW instead of HH/HL/LH/LL.
"""
from __future__ import annotations

import math
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "causal-structure-v1"
LOADED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


def assert_loaded_source_current() -> str:
    if sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_SOURCE_SHA256:
        raise ValueError("causal_structure_source_changed_restart_required")
    return LOADED_SOURCE_SHA256


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(name + "_must_be_positive_integer")
    return value


def _validated_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("structure_completed_rows_required")
    checked: list[dict[str, Any]] = []
    previous_date: date | None = None
    for row in rows:
        if not isinstance(row, dict) or row.get("complete") is not True or row.get("provisional") is not False:
            raise ValueError("structure_row_not_explicitly_completed")
        raw_date = row.get("date")
        if not isinstance(raw_date, str):
            raise ValueError("structure_date_invalid")
        try:
            session_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("structure_date_invalid") from exc
        if previous_date is not None and session_date <= previous_date:
            raise ValueError("structure_dates_not_strictly_ascending")
        previous_date = session_date
        prices: dict[str, float] = {}
        for key in ("open", "high", "low", "close"):
            value = row.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("structure_ohlc_invalid")
            prices[key] = float(value)
        if prices["high"] < max(prices["open"], prices["close"]) or prices["low"] > min(prices["open"], prices["close"]):
            raise ValueError("structure_ohlc_invalid")
        checked.append({"date": raw_date, **prices})
    return checked


def project_causal_structure(
    rows: list[dict[str, Any]], *, left_window: int = 3, right_window: int = 3,
    as_of_index: int | None = None,
) -> dict[str, Any]:
    """Return events observable by as_of_index, never backdating confirmation."""
    checked = _validated_rows(rows)
    left = _positive_int(left_window, "structure_left_window")
    right = _positive_int(right_window, "structure_right_window")
    if as_of_index is None:
        as_of_index = len(checked) - 1
    if isinstance(as_of_index, bool) or not isinstance(as_of_index, int) or not 0 <= as_of_index < len(checked):
        raise ValueError("structure_as_of_index_invalid")

    pivots: list[dict[str, Any]] = []
    breakouts: list[dict[str, Any]] = []
    levels: list[dict[str, Any]] = []
    latest: dict[str, dict[str, Any] | None] = {"HIGH": None, "LOW": None}
    for index in range(as_of_index + 1):
        current = checked[index]
        previous_close = checked[index - 1]["close"] if index else None
        resistance, support = latest["HIGH"], latest["LOW"]
        # Today's close may cross only a level confirmed before this close.
        if previous_close is not None and resistance is not None:
            level = resistance["price"]
            if previous_close <= level < current["close"]:
                breakouts.append({"kind": "BREAK_UP", "index": index, "date": current["date"],
                                  "level": level, "level_pivot_index": resistance["pivot_index"],
                                  "level_confirmed_at_index": resistance["confirmed_at_index"],
                                  "close": current["close"]})
        if previous_close is not None and support is not None:
            level = support["price"]
            if previous_close >= level > current["close"]:
                breakouts.append({"kind": "BREAK_DOWN", "index": index, "date": current["date"],
                                  "level": level, "level_pivot_index": support["pivot_index"],
                                  "level_confirmed_at_index": support["confirmed_at_index"],
                                  "close": current["close"]})

        candidate = index - right
        if candidate >= left:
            sample = checked[candidate - left:index + 1]
            for kind, key in (("HIGH", "high"), ("LOW", "low")):
                price = checked[candidate][key]
                others = [bar[key] for offset, bar in enumerate(sample) if offset != left]
                qualifies = price > max(others) if kind == "HIGH" else price < min(others)
                if not qualifies:
                    continue
                previous = latest[kind]
                if previous is None:
                    classification = "INITIAL_" + kind
                elif price == previous["price"]:
                    classification = "EQUAL_" + kind
                elif kind == "HIGH":
                    classification = "HH" if price > previous["price"] else "LH"
                else:
                    classification = "HL" if price > previous["price"] else "LL"
                event = {"kind": kind, "classification": classification,
                         "pivot_index": candidate, "pivot_date": checked[candidate]["date"],
                         "confirmed_at_index": index, "confirmed_at_date": current["date"],
                         "price": price}
                pivots.append(event)
                latest[kind] = event
        levels.append({"index": index, "date": current["date"],
                       "support": latest["LOW"]["price"] if latest["LOW"] else None,
                       "support_pivot_index": latest["LOW"]["pivot_index"] if latest["LOW"] else None,
                       "resistance": latest["HIGH"]["price"] if latest["HIGH"] else None,
                       "resistance_pivot_index": latest["HIGH"]["pivot_index"] if latest["HIGH"] else None})
    return {"schema_version": SCHEMA_VERSION, "as_of_index": as_of_index,
            "tie_policy": "strict_unique_window;separate_confirmed_equals_explicit",
            "left_window": left, "right_window": right,
            "pivots": pivots, "breakouts": breakouts, "levels": levels}
