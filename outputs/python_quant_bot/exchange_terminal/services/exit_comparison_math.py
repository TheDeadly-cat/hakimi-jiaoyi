"""Independent, preregistered exit comparisons for one fixed BUY cohort.

These are isolated trade samples, not a portfolio replay. Entry fills are kept
exactly as recorded; no cash, reinvestment, or equity curve is synthesized.
"""
from __future__ import annotations

import math
from datetime import date
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Any

from .causal_structure import (
    LOADED_SOURCE_SHA256 as CAUSAL_SOURCE_SHA256,
    _validated_rows, assert_loaded_source_current as assert_structure_source_current,
    project_causal_structure,
)
from .indicator_math import (
    LOADED_SOURCE_SHA256 as INDICATOR_SOURCE_SHA256,
    atr, assert_loaded_source_current as assert_indicator_source_current,
)


SCHEMA_VERSION = "exit-comparison-math-v1"
RULES = ("fixed_pct", "atr_trailing", "confirmed_structure")
SEGMENTS = ("TRAIN", "VALIDATION", "TEST")
LOADED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


def assert_loaded_source_current() -> str:
    if sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_SOURCE_SHA256:
        raise ValueError("exit_comparison_source_changed_restart_required")
    return LOADED_SOURCE_SHA256


def _number(value: Any, name: str, *, minimum: float = 0.0, maximum: float | None = None,
            strict_minimum: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + "_invalid")
    result = float(value)
    if result < minimum or (strict_minimum and result == minimum) or (maximum is not None and result > maximum):
        raise ValueError(name + "_invalid")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(name + "_invalid")
    return value


def _day(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ValueError(name + "_invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(name + "_invalid") from exc


def _specification(spec: Any, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, tuple[int, int]]]:
    if not isinstance(spec, dict) or not isinstance(spec.get("split"), dict) or not isinstance(spec.get("costs"), dict):
        raise ValueError("exit_comparison_spec_invalid")
    split = spec["split"]
    if set(split) != set(SEGMENTS):
        raise ValueError("exit_comparison_three_segments_required")
    sessions = [date.fromisoformat(row["date"]) for row in rows]
    intervals: dict[str, tuple[int, int]] = {}
    normalized_split: dict[str, dict[str, str]] = {}
    previous_end: date | None = None
    for name in SEGMENTS:
        boundary = split[name]
        if not isinstance(boundary, dict):
            raise ValueError("exit_comparison_split_invalid")
        start = _day(boundary.get("start_date"), name + "_start_date")
        end = _day(boundary.get("end_date"), name + "_end_date")
        if end < start or (previous_end is not None and start <= previous_end):
            raise ValueError("exit_comparison_split_overlap_or_order_invalid")
        if start < sessions[0] or end > sessions[-1]:
            raise ValueError("exit_comparison_split_outside_frozen_rows")
        included = [i for i, session in enumerate(sessions) if start <= session <= end]
        if not included:
            raise ValueError("exit_comparison_empty_segment")
        intervals[name] = (included[0], included[-1])
        normalized_split[name] = {"start_date": start.isoformat(), "end_date": end.isoformat()}
        previous_end = end
    fixed_pct = _number(spec.get("fixed_stop_pct"), "fixed_stop_pct", minimum=0, maximum=100, strict_minimum=True)
    emergency_pct = _number(spec.get("emergency_stop_pct"), "emergency_stop_pct", minimum=0, maximum=100, strict_minimum=True)
    normalized = {
        "split": normalized_split,
        "fixed_stop_pct": fixed_pct,
        "atr_window": _positive_int(spec.get("atr_window"), "atr_window"),
        "atr_mult": _number(spec.get("atr_mult"), "atr_mult", strict_minimum=True),
        "structure_left_window": _positive_int(spec.get("structure_left_window"), "structure_left_window"),
        "structure_right_window": _positive_int(spec.get("structure_right_window"), "structure_right_window"),
        "emergency_stop_pct": emergency_pct,
        "max_hold_bars": _positive_int(spec.get("max_hold_bars"), "max_hold_bars"),
        "costs": {"fee_rate": _number(spec["costs"].get("fee_rate"), "fee_rate", maximum=1),
                  "slippage_bps": _number(spec["costs"].get("slippage_bps"), "slippage_bps", maximum=10000)},
    }
    return normalized, intervals


def _cohort(reference_trades: Any, rows: list[dict[str, Any]],
            intervals: dict[str, tuple[int, int]]) -> list[dict[str, Any]]:
    if not isinstance(reference_trades, (list, tuple)) or not reference_trades:
        raise ValueError("exit_comparison_buy_cohort_required")
    row_index = {row["date"]: index for index, row in enumerate(rows)}
    entries: list[dict[str, Any]] = []
    for ordinal, record in enumerate(reference_trades):
        if not isinstance(record, dict) or record.get("side") != "BUY":
            raise ValueError("exit_comparison_buy_only_reject_add_and_other_sides")
        if record.get("fill_basis") != "NEXT_BAR_OPEN":
            raise ValueError("exit_comparison_native_next_open_buy_required")
        session = record.get("date")
        if session not in row_index:
            raise ValueError("exit_comparison_entry_outside_frozen_rows")
        index = row_index[session]
        segment = next((name for name, (start, end) in intervals.items() if start <= index <= end), None)
        if segment is None:
            raise ValueError("exit_comparison_entry_outside_preregistered_split")
        price = _number(record.get("price"), "entry_price", strict_minimum=True)
        quantity = _number(record.get("quantity"), "entry_quantity", strict_minimum=True)
        fee = _number(record.get("fee"), "entry_fee")
        entries.append({"sample_id": f"BUY-{ordinal + 1:04d}-{index}", "index": index,
                        "date": session, "segment": segment, "side": "BUY",
                        "price": price, "quantity": quantity, "fee": fee,
                        "signal_date": record.get("signal_date", ""),
                        "fill_basis": "NEXT_BAR_OPEN"})
    return entries


def _unavailable(reason: str, entry_fee: float) -> dict[str, Any]:
    return {"status": "UNAVAILABLE", "reason": reason, "exit": None, "threshold_trace": [],
            "net_return_pct": None, "net_pnl": None,
            "fees": {"entry": entry_fee, "exit": None, "total": None},
            "mae_pct": None, "mfe_pct": None, "duration_bars": None,
            "censor": None}


def _simulate(
    rule: str, entry: dict[str, Any], rows: list[dict[str, Any]],
    segment_end: int, spec: dict[str, Any], atr_values: list[float | None],
    support_levels: list[float | None],
) -> dict[str, Any]:
    start = entry["index"]
    entry_price, quantity, entry_fee = entry["price"], entry["quantity"], entry["fee"]
    emergency = entry_price * (1 - spec["emergency_stop_pct"] / 100)
    high_water_close = entry_price
    if rule == "fixed_pct":
        rule_threshold = entry_price * (1 - spec["fixed_stop_pct"] / 100)
    elif rule == "atr_trailing":
        if start == 0 or atr_values[start - 1] is None:
            return _unavailable("ATR_NOT_AVAILABLE_BEFORE_ENTRY", entry_fee)
        rule_threshold = entry_price - spec["atr_mult"] * atr_values[start - 1]
    else:
        support = support_levels[start - 1] if start else None
        if support is None:
            return _unavailable("NO_CONFIRMED_SUPPORT_BEFORE_ENTRY", entry_fee)
        if support >= entry_price:
            return _unavailable("CONFIRMED_SUPPORT_NOT_BELOW_ENTRY", entry_fee)
        rule_threshold = support

    observation_end = min(segment_end, start + spec["max_hold_bars"] - 1)
    trace: list[dict[str, Any]] = []
    lowest = highest = entry_price
    for index in range(start, observation_end + 1):
        row = rows[index]
        known_at = index if index == start else index - 1
        if index > start:
            if rule == "atr_trailing":
                high_water_close = max(high_water_close, rows[index - 1]["close"])
                previous_atr = atr_values[index - 1]
                if previous_atr is not None:
                    rule_threshold = max(rule_threshold, high_water_close - spec["atr_mult"] * previous_atr)
            elif rule == "confirmed_structure":
                previous_support = support_levels[index - 1]
                if previous_support is not None:
                    rule_threshold = max(rule_threshold, previous_support)
        threshold = max(emergency, rule_threshold)
        if row["open"] <= threshold:
            trigger, raw_price = "GAP_OPEN", row["open"]
        elif row["low"] <= threshold:
            trigger, raw_price = "INTRABAR_STOP", threshold
        else:
            trigger, raw_price = None, None
        trace.append({"index": index, "date": row["date"], "known_at_index": known_at,
                      "known_at_date": rows[known_at]["date"], "rule_threshold": rule_threshold,
                      "emergency_threshold": emergency, "effective_threshold": threshold,
                      "threshold": threshold, "open": row["open"], "low": row["low"],
                      "trigger": trigger})
        if trigger is not None:
            # The exit bar's high/low ordering is unknown. Only its fill point is
            # observed for excursion statistics; post-fill extremes are excluded.
            lowest = min(lowest, raw_price)
            highest = max(highest, raw_price)
            fill_price = raw_price * (1 - spec["costs"]["slippage_bps"] / 10000)
            exit_fee = fill_price * quantity * spec["costs"]["fee_rate"]
            basis = entry_price * quantity + entry_fee
            net_pnl = fill_price * quantity - exit_fee - basis
            exit_record = {"index": index, "date": row["date"], "raw_price": raw_price,
                           "price": fill_price, "quantity": quantity, "fee": exit_fee,
                           "fill_basis": trigger}
            return {"status": "EXITED", "reason": trigger, "exit": exit_record,
                    "threshold_trace": trace, "net_return_pct": 100 * net_pnl / basis,
                    "net_pnl": net_pnl,
                    "fees": {"entry": entry_fee, "exit": exit_fee, "total": entry_fee + exit_fee},
                    "mae_pct": 100 * (lowest / entry_price - 1),
                    "mfe_pct": 100 * (highest / entry_price - 1),
                    "duration_bars": index - start + 1, "censor": None}
        lowest = min(lowest, row["low"])
        highest = max(highest, row["high"])
    boundary = "SEGMENT_END" if segment_end <= start + spec["max_hold_bars"] - 1 else "MAX_HOLD_BARS"
    last = rows[observation_end]
    return {"status": "CENSORED", "reason": boundary, "exit": None,
            "threshold_trace": trace, "net_return_pct": None, "net_pnl": None,
            "fees": {"entry": entry_fee, "exit": None, "total": None},
            "mae_pct": 100 * (lowest / entry_price - 1),
            "mfe_pct": 100 * (highest / entry_price - 1),
            "duration_bars": observation_end - start + 1,
            "censor": {"reason": boundary, "index": observation_end, "date": last["date"]}}


def _summary(samples: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    summaries: dict[str, Any] = {rule: {} for rule in RULES}
    segment_stats: dict[str, Any] = {}
    for segment in SEGMENTS:
        members = [sample for sample in samples if sample["segment"] == segment]
        for rule in RULES:
            outcomes = [sample["outcomes"][rule] for sample in members]
            exited = [outcome for outcome in outcomes if outcome["status"] == "EXITED"]
            returns = [outcome["net_return_pct"] for outcome in exited]
            losses = sum(value < 0 for value in returns)
            summaries[rule][segment] = {"sample_count": len(members), "exited_count": len(exited),
                                         "censored_count": sum(outcome["status"] == "CENSORED" for outcome in outcomes),
                                         "unavailable_count": sum(outcome["status"] == "UNAVAILABLE" for outcome in outcomes),
                                         "mean_net_return_pct_exited_only": sum(returns) / len(returns) if exited else None,
                                         "median_net_return_pct_exited_only": median(returns) if exited else None,
                                         "worst_net_return_pct_exited_only": min(returns) if exited else None,
                                         "loss_count_exited_only": losses,
                                         "loss_rate_exited_only": losses / len(exited) if exited else None,
                                         "mean_duration_bars_exited_only":
                                             sum(outcome["duration_bars"] for outcome in exited) / len(exited) if exited else None,
                                         "mean_total_fee_exited_only":
                                             sum(outcome["fees"]["total"] for outcome in exited) / len(exited) if exited else None,
                                         "mean_mae_pct_exited_only":
                                             sum(outcome["mae_pct"] for outcome in exited) / len(exited) if exited else None,
                                         "mean_mfe_pct_exited_only":
                                             sum(outcome["mfe_pct"] for outcome in exited) / len(exited) if exited else None}
        paired: dict[str, Any] = {}
        for left, right in (("fixed_pct", "atr_trailing"), ("fixed_pct", "confirmed_structure"),
                            ("atr_trailing", "confirmed_structure")):
            differences = [sample["outcomes"][right]["net_return_pct"] - sample["outcomes"][left]["net_return_pct"]
                           for sample in members if sample["outcomes"][left]["status"] == "EXITED"
                           and sample["outcomes"][right]["status"] == "EXITED"]
            paired[left + "_vs_" + right] = {"paired_exited_count": len(differences),
                                              "excluded_censored_or_unavailable_count": len(members) - len(differences),
                                              "right_minus_left_mean_net_return_pct_points":
                                              sum(differences) / len(differences) if differences else None}
        segment_stats[segment] = {"sample_count": len(members), "paired": paired}
    return summaries, segment_stats


def compare_exit_rules(rows: list[dict[str, Any]], reference_trades: list[dict[str, Any]],
                       spec: dict[str, Any]) -> dict[str, Any]:
    """Compare three exits on the same BUY entries, within fixed date segments."""
    assert_loaded_source_current()
    assert_structure_source_current()
    assert_indicator_source_current()
    checked = _validated_rows(rows)
    normalized, intervals = _specification(spec, checked)
    entries = _cohort(reference_trades, checked, intervals)
    structure = project_causal_structure(rows, left_window=normalized["structure_left_window"],
                                         right_window=normalized["structure_right_window"])
    atr_values = atr(checked, normalized["atr_window"])
    support_levels = [level["support"] for level in structure["levels"]]
    samples: list[dict[str, Any]] = []
    exit_paths: list[dict[str, Any]] = []
    for entry in entries:
        segment = entry["segment"]
        outcomes = {rule: _simulate(rule, entry, checked, intervals[segment][1], normalized,
                                    atr_values, support_levels) for rule in RULES}
        samples.append({"sample_id": entry["sample_id"], "segment": segment,
                        "entry": entry.copy(), "outcomes": outcomes})
        for rule, outcome in outcomes.items():
            exit_paths.append({"sample_id": entry["sample_id"], "entry": entry.copy(),
                               "segment": segment, "rule": rule, "status": outcome["status"],
                               "reason": outcome["reason"], "threshold_trace": outcome["threshold_trace"],
                               "exit": outcome["exit"], "censor": outcome["censor"]})
    structure_marks = ([{"type": "PIVOT", **pivot} for pivot in structure["pivots"]] +
                       [{"type": "BREAKOUT", **breakout, "confirmed_at_index": breakout["index"],
                         "confirmed_at_date": breakout["date"], "price": breakout["close"]}
                        for breakout in structure["breakouts"]])
    structure_marks.sort(key=lambda mark: (mark["confirmed_at_index"], mark["type"], mark.get("pivot_index", -1)))
    summaries, segment_stats = _summary(samples)
    return {"schema_version": SCHEMA_VERSION, "spec": normalized,
            "methodology": {"atr_trailing": "Highest completed close since entry minus multiplier times previous completed simple-rolling ATR; never same-bar high or Wilder ATR.",
                            "paired_statistics": "Only entries with both rule outcomes EXITED are paired; censored or unavailable entries are excluded, so means do not establish an overall rule advantage.",
                            "excursions": "Full held bars and exit fill point only; unknown post-exit intrabar extremes excluded."},
            "source_sha256": {"exit_comparison_math": LOADED_SOURCE_SHA256,
                              "causal_structure": CAUSAL_SOURCE_SHA256,
                              "indicator_math": INDICATOR_SOURCE_SHA256},
            "cohort_count": len(entries), "structure": structure, "structure_marks": structure_marks,
            "samples": samples, "exit_paths": exit_paths,
            "summaries": summaries, "segment_stats": segment_stats,
            "portfolio_equity_curve": None}
