from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import median
from typing import Any

from hakimi_research.candle_contract import candle_is_complete
from .backtest_engine import numeric_parameter_contract_issues, run_causal_long_only_backtest


BENCHMARK_SCHEMA_VERSION = "strategy-benchmark-v7"


def _number(value: Any) -> float:
    try:
        result = float(value or 0.0)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _median(values: list[Any]) -> float:
    usable = [_number(value) for value in values]
    return float(median(usable)) if usable else 0.0


def _finite_native(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _nonnegative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _selection_cell_usable(cell: dict[str, Any]) -> bool:
    if not isinstance(cell, dict) or cell.get("dataset_status") != "PASS" or cell.get("baseline_ok") is not True:
        return False
    for field in (
        "validation_return_pct",
        "test_return_pct",
        "test_excess_return_pct",
        "test_max_drawdown_pct",
        "test_sharpe",
    ):
        if not _finite_native(cell.get(field)):
            return False
    return _nonnegative_integer(cell.get("test_trade_count"))


def _completed(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def _daily_date(row: dict[str, Any]) -> date | None:
    text = str(row.get("date") or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def align_completed_daily_payloads(
    payloads: dict[str, dict[str, Any]],
    *,
    max_endpoint_skew_days: int = 3,
    max_boundary_skew_days: int = 7,
    required_start: str = "",
    required_as_of: str = "",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Align a cross-symbol daily batch before any strategy comparison."""
    blockers: list[str] = []
    endpoints: dict[str, date] = {}
    starts: dict[str, date] = {}
    completed_counts: dict[str, int] = {}
    normalized_rows: dict[str, list[tuple[date, dict[str, Any]]]] = {}
    for symbol, payload in payloads.items():
        usable: list[tuple[date, dict[str, Any]]] = []
        invalid_dates = 0
        for raw in list(payload.get("rows") or []):
            row = dict(raw)
            if not _completed(row):
                continue
            trading_date = _daily_date(row)
            if trading_date is None:
                invalid_dates += 1
                continue
            usable.append((trading_date, row))
        usable.sort(key=lambda item: item[0])
        normalized_rows[symbol] = usable
        completed_counts[symbol] = len(usable)
        if usable:
            starts[symbol] = usable[0][0]
            endpoints[symbol] = usable[-1][0]
        else:
            blockers.append(f"{symbol}:no_completed_daily_rows")
        if invalid_dates:
            blockers.append(f"{symbol}:invalid_daily_dates:{invalid_dates}")

    target_start: date | None = None
    if required_start:
        try:
            target_start = date.fromisoformat(str(required_start)[:10])
        except ValueError:
            blockers.append(f"invalid_required_start:{required_start}")
    elif starts:
        target_start = max(starts.values())

    target: date | None = None
    if required_as_of:
        try:
            target = date.fromisoformat(str(required_as_of)[:10])
        except ValueError:
            blockers.append(f"invalid_required_as_of:{required_as_of}")
    elif endpoints:
        target = min(endpoints.values())

    endpoint_skew = 0
    if endpoints:
        endpoint_skew = (max(endpoints.values()) - min(endpoints.values())).days
        if endpoint_skew > max(0, int(max_endpoint_skew_days)):
            blockers.append(
                f"endpoint_skew_days:{endpoint_skew}>{max(0, int(max_endpoint_skew_days))}"
            )
    if target is not None and required_as_of:
        for symbol, endpoint in endpoints.items():
            if endpoint < target:
                blockers.append(f"{symbol}:endpoint_before_required_as_of:{endpoint.isoformat()}<{target.isoformat()}")
    if target_start is not None and required_start:
        for symbol, first_date in starts.items():
            if first_date > target_start:
                blockers.append(f"{symbol}:starts_after_required_start:{first_date.isoformat()}>{target_start.isoformat()}")
    if target_start is not None and target is not None and target_start >= target:
        blockers.append(f"invalid_common_window:{target_start.isoformat()}>={target.isoformat()}")

    aligned: dict[str, dict[str, Any]] = {}
    aligned_counts: dict[str, int] = {}
    aligned_starts: dict[str, str] = {}
    aligned_endpoints: dict[str, str] = {}
    candidate_rows: dict[str, list[tuple[date, dict[str, Any]]]] = {}
    effective_start = target_start
    effective_end = target
    if not blockers and target_start is not None and target is not None:
        for symbol, payload in payloads.items():
            rows = [
                (trading_date, row) for trading_date, row in normalized_rows[symbol]
                if target_start <= trading_date <= target
            ]
            if not rows:
                blockers.append(f"{symbol}:no_rows_at_common_as_of")
                continue
            first_date = rows[0][0]
            endpoint = rows[-1][0]
            if required_start and first_date != target_start:
                blockers.append(f"{symbol}:missing_required_start:{target_start.isoformat()}")
            elif (first_date - target_start).days > max(0, int(max_boundary_skew_days)):
                blockers.append(
                    f"{symbol}:start_boundary_skew_days:{(first_date - target_start).days}"
                    f">{max(0, int(max_boundary_skew_days))}"
                )
            if required_as_of and endpoint != target:
                blockers.append(f"{symbol}:missing_common_as_of:{target.isoformat()}")
            elif (target - endpoint).days > max(0, int(max_endpoint_skew_days)):
                blockers.append(
                    f"{symbol}:end_boundary_skew_days:{(target - endpoint).days}"
                    f">{max(0, int(max_endpoint_skew_days))}"
                )
            candidate_rows[symbol] = rows
        if not blockers and len(candidate_rows) == len(payloads):
            effective_start = max(rows[0][0] for rows in candidate_rows.values())
            effective_end = min(rows[-1][0] for rows in candidate_rows.values())
            if effective_start >= effective_end:
                blockers.append(
                    f"invalid_effective_common_window:{effective_start.isoformat()}>={effective_end.isoformat()}"
                )
            else:
                for symbol, payload in payloads.items():
                    rows = [
                        row for trading_date, row in candidate_rows[symbol]
                        if effective_start <= trading_date <= effective_end
                    ]
                    if not rows:
                        blockers.append(f"{symbol}:no_rows_in_effective_common_window")
                        continue
                    first_date = _daily_date(rows[0])
                    endpoint = _daily_date(rows[-1])
                    if first_date is None or endpoint is None:
                        blockers.append(f"{symbol}:effective_boundary_invalid")
                        continue
                    if (first_date - effective_start).days > max(0, int(max_boundary_skew_days)):
                        blockers.append(f"{symbol}:effective_start_boundary_too_late")
                    if (effective_end - endpoint).days > max(0, int(max_endpoint_skew_days)):
                        blockers.append(f"{symbol}:effective_end_boundary_too_early")
                    aligned[symbol] = {**payload, "rows": rows}
                    aligned_counts[symbol] = len(rows)
                    aligned_starts[symbol] = first_date.isoformat()
                    aligned_endpoints[symbol] = endpoint.isoformat()

    status = "PASS" if not blockers and len(aligned) == len(payloads) and bool(payloads) else "BLOCK"
    if status == "BLOCK":
        aligned = {}
    report = {
        "schema_version": "daily-batch-alignment-v2",
        "status": status,
        "common_start": effective_start.isoformat() if effective_start else "",
        "common_as_of": effective_end.isoformat() if effective_end else "",
        "required_start": str(required_start or ""),
        "required_as_of": str(required_as_of or ""),
        "max_endpoint_skew_days": max(0, int(max_endpoint_skew_days)),
        "max_boundary_skew_days": max(0, int(max_boundary_skew_days)),
        "endpoint_skew_days": endpoint_skew,
        "original_starts": {symbol: value.isoformat() for symbol, value in starts.items()},
        "original_endpoints": {symbol: value.isoformat() for symbol, value in endpoints.items()},
        "original_completed_rows": completed_counts,
        "aligned_starts": aligned_starts,
        "aligned_endpoints": aligned_endpoints,
        "aligned_completed_rows": aligned_counts,
        "blockers": list(dict.fromkeys(blockers)),
    }
    return aligned, report


def build_calendar_split_schedule(
    payloads: dict[str, dict[str, Any]],
    *,
    train_ratio: float = 0.50,
    validation_ratio: float = 0.25,
    minimum_segment_rows: int = 120,
) -> dict[str, Any]:
    blockers: list[str] = []
    numeric_issues = numeric_parameter_contract_issues(
        {
            "train_ratio": train_ratio,
            "validation_ratio": validation_ratio,
            "minimum_segment_rows": minimum_segment_rows,
        },
        positive=("minimum_segment_rows",),
        integer=("minimum_segment_rows",),
        minimum={"train_ratio": 0.20, "validation_ratio": 0.10},
        maximum={"train_ratio": 0.70, "validation_ratio": 0.40},
    )
    if numeric_issues:
        return {
            "schema_version": "calendar-split-v1",
            "status": "BLOCK",
            "train_ratio": train_ratio,
            "validation_ratio": validation_ratio,
            "minimum_segment_rows": minimum_segment_rows,
            "blockers": [f"numeric_parameter_contract:{issue}" for issue in numeric_issues],
            "symbol_boundaries": {},
        }
    if not payloads:
        return {
            "schema_version": "calendar-split-v1",
            "status": "BLOCK",
            "blockers": ["no_aligned_payloads"],
            "symbol_boundaries": {},
        }
    starts: dict[str, date] = {}
    ends: dict[str, date] = {}
    normalized: dict[str, list[tuple[date, dict[str, Any]]]] = {}
    for symbol, payload in payloads.items():
        rows = []
        for raw in list(payload.get("rows") or []):
            row = dict(raw)
            if not _completed(row):
                continue
            trading_date = _daily_date(row)
            if trading_date is not None:
                rows.append((trading_date, row))
        rows.sort(key=lambda item: item[0])
        normalized[symbol] = rows
        if not rows:
            blockers.append(f"{symbol}:no_completed_daily_rows")
            continue
        starts[symbol] = rows[0][0]
        ends[symbol] = rows[-1][0]
    if blockers:
        return {
            "schema_version": "calendar-split-v1",
            "status": "BLOCK",
            "blockers": blockers,
            "symbol_boundaries": {},
        }
    common_start = max(starts.values())
    common_end = min(ends.values())
    if len(set(starts.values())) != 1 or len(set(ends.values())) != 1:
        blockers.append("payloads_are_not_pre_aligned")
    span_days = (common_end - common_start).days
    safe_train_ratio = float(train_ratio)
    safe_validation_ratio = float(validation_ratio)
    if safe_train_ratio + safe_validation_ratio >= 0.90:
        blockers.append("invalid_calendar_split_ratios")
    train_end = common_start + timedelta(days=int(span_days * safe_train_ratio))
    validation_end = common_start + timedelta(days=int(span_days * (safe_train_ratio + safe_validation_ratio)))
    symbol_boundaries: dict[str, dict[str, Any]] = {}
    for symbol, rows in normalized.items():
        train_end_index = sum(trading_date <= train_end for trading_date, _row in rows)
        validation_end_index = sum(trading_date <= validation_end for trading_date, _row in rows)
        counts = {
            "train": train_end_index,
            "validation": validation_end_index - train_end_index,
            "test": len(rows) - validation_end_index,
        }
        for name, count in counts.items():
            if count < int(minimum_segment_rows):
                blockers.append(f"{symbol}:{name}_rows:{count}<{int(minimum_segment_rows)}")
        symbol_boundaries[symbol] = {
            "train_end_index": train_end_index,
            "validation_end_index": validation_end_index,
            "counts": counts,
            "row_count": len(rows),
        }
    return {
        "schema_version": "calendar-split-v1",
        "status": "PASS" if not blockers else "BLOCK",
        "common_start": common_start.isoformat(),
        "common_end": common_end.isoformat(),
        "train_end": train_end.isoformat(),
        "validation_end": validation_end.isoformat(),
        "train_ratio": safe_train_ratio,
        "validation_ratio": safe_validation_ratio,
        "minimum_segment_rows": int(minimum_segment_rows),
        "span_days": span_days,
        "symbol_boundaries": symbol_boundaries,
        "blockers": list(dict.fromkeys(blockers)),
    }


def buy_and_hold_report(
    *,
    rows: list[dict[str, Any]],
    symbol: str,
    source: str,
    position_pct: float,
    startup_candles: int,
    fee_rate: float,
    slippage_bps: float,
    market: str,
    evaluation_start_index: int | None = None,
) -> dict[str, Any]:
    def signal(
        _closes: list[float],
        _price: float,
        has_position: bool,
        _entry_price: float,
        _last_scale_price: float,
    ) -> dict[str, str]:
        return {"action": "HOLD", "reason": "buy_and_hold"} if has_position else {
            "action": "BUY",
            "reason": "buy_and_hold_entry",
        }

    return run_causal_long_only_backtest(
        rows=rows,
        symbol=symbol,
        source=source,
        signal_fn=signal,
        position_pct=position_pct,
        take_profit_pct=0.0,
        stop_loss_pct=0.0,
        startup_candles=startup_candles,
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        leverage=1.0,
        market=market,
        timeframe="1D",
        evaluation_start_index=evaluation_start_index,
    )


def aggregate_strategy_selection(
    strategy_id: str,
    cells: list[dict[str, Any]],
    *,
    strategy_trials: int,
    required_symbols: int,
) -> dict[str, Any]:
    usable = [cell for cell in cells if _selection_cell_usable(cell)]
    temporal_pass = [cell for cell in usable if cell.get("temporal_status") == "PASS"]
    walk_forward_pass = [cell for cell in usable if cell.get("walk_forward_status") == "PASS"]
    lookahead_pass = [cell for cell in usable if cell.get("lookahead_status") == "PASS"]
    validation_positive = [cell for cell in usable if _number(cell.get("validation_return_pct")) > 0]
    test_positive = [cell for cell in usable if _number(cell.get("test_return_pct")) > 0]
    excess_positive = [cell for cell in usable if _number(cell.get("test_excess_return_pct")) > 0]
    cost_pass = [cell for cell in usable if cell.get("cost_sensitivity_status") == "PASS"]
    total_test_trades = sum(cell["test_trade_count"] for cell in usable)
    worst_test_drawdown = max((_number(cell.get("test_max_drawdown_pct")) for cell in usable), default=100.0)
    median_validation_return = _median([cell.get("validation_return_pct") for cell in usable])
    median_test_return = _median([cell.get("test_return_pct") for cell in usable])
    median_test_excess = _median([cell.get("test_excess_return_pct") for cell in usable])
    median_test_drawdown = _median([cell.get("test_max_drawdown_pct") for cell in usable])
    median_test_sharpe = _median([cell.get("test_sharpe") for cell in usable])

    minimum_positive = max(1, math.ceil(required_symbols * 0.60))
    minimum_cost_pass = max(1, math.ceil(required_symbols * 0.75))
    blockers: list[str] = []
    if len(usable) < required_symbols:
        blockers.append(f"usable_symbols:{len(usable)}<{required_symbols}")
    if len(temporal_pass) < minimum_positive:
        blockers.append(f"temporal_pass_symbols:{len(temporal_pass)}<{minimum_positive}")
    if len(walk_forward_pass) < minimum_positive:
        blockers.append(f"walk_forward_pass_symbols:{len(walk_forward_pass)}<{minimum_positive}")
    if len(lookahead_pass) < required_symbols:
        blockers.append(f"lookahead_pass_symbols:{len(lookahead_pass)}<{required_symbols}")
    if len(validation_positive) < minimum_positive:
        blockers.append(f"validation_positive_symbols:{len(validation_positive)}<{minimum_positive}")
    if len(test_positive) < minimum_positive:
        blockers.append(f"test_positive_symbols:{len(test_positive)}<{minimum_positive}")
    if len(excess_positive) < minimum_positive:
        blockers.append(f"test_excess_positive_symbols:{len(excess_positive)}<{minimum_positive}")
    if len(cost_pass) < minimum_cost_pass:
        blockers.append(f"cost_pass_symbols:{len(cost_pass)}<{minimum_cost_pass}")
    if median_test_return <= 0:
        blockers.append("median_test_return_not_positive")
    if median_test_excess <= 0:
        blockers.append("median_test_excess_not_positive")
    if total_test_trades < required_symbols * 2:
        blockers.append(f"test_closed_trades:{total_test_trades}<{required_symbols * 2}")
    if worst_test_drawdown >= 25:
        blockers.append(f"worst_test_drawdown:{worst_test_drawdown:.2f}>=25")

    raw_score = (
        median_validation_return * 0.40
        + median_test_return * 1.25
        + median_test_excess * 1.50
        + median_test_sharpe * 3.0
        - median_test_drawdown * 0.60
    )
    trial_penalty = math.sqrt(2.0 * math.log(max(int(strategy_trials), 1))) * 1.5
    adjusted_score = raw_score - trial_penalty
    if adjusted_score <= 0:
        blockers.append("multiple_trial_adjusted_score_not_positive")
    return {
        "strategy_id": strategy_id,
        "status": "PASS" if not blockers else "BLOCK",
        "eligible_for_confirmation": not blockers,
        "raw_score": round(raw_score, 4),
        "multiple_trial_penalty": round(trial_penalty, 4),
        "adjusted_score": round(adjusted_score, 4),
        "strategy_trials": int(strategy_trials),
        "usable_symbols": len(usable),
        "temporal_pass_symbols": len(temporal_pass),
        "walk_forward_pass_symbols": len(walk_forward_pass),
        "lookahead_pass_symbols": len(lookahead_pass),
        "validation_positive_symbols": len(validation_positive),
        "test_positive_symbols": len(test_positive),
        "test_excess_positive_symbols": len(excess_positive),
        "cost_pass_symbols": len(cost_pass),
        "total_test_trades": total_test_trades,
        "median_validation_return_pct": round(median_validation_return, 4),
        "median_test_return_pct": round(median_test_return, 4),
        "median_test_excess_return_pct": round(median_test_excess, 4),
        "median_test_drawdown_pct": round(median_test_drawdown, 4),
        "worst_test_drawdown_pct": round(worst_test_drawdown, 4),
        "median_test_sharpe": round(median_test_sharpe, 4),
        "blockers": blockers,
    }


def confirmation_summary(strategy_id: str, cells: list[dict[str, Any]], required_symbols: int) -> dict[str, Any]:
    blockers: list[str] = []
    passed = 0
    for cell in cells:
        symbol = str(cell.get("symbol") or "UNKNOWN")
        cell_blockers: list[str] = []
        if cell.get("dataset_status") != "PASS" or cell.get("baseline_ok") is not True:
            cell_blockers.append("data_or_backtest_block")
        if cell.get("temporal_status") != "PASS":
            cell_blockers.append("temporal_validation_block")
        if cell.get("walk_forward_status") != "PASS":
            cell_blockers.append("walk_forward_block")
        if cell.get("lookahead_status") != "PASS":
            cell_blockers.append("lookahead_check_block")
        if not _finite_native(cell.get("test_return_pct")):
            cell_blockers.append("test_return_missing_or_nonfinite")
        elif _number(cell.get("test_return_pct")) <= 0:
            cell_blockers.append("test_return_not_positive")
        if not _finite_native(cell.get("test_excess_return_pct")):
            cell_blockers.append("test_excess_missing_or_nonfinite")
        elif _number(cell.get("test_excess_return_pct")) <= 0:
            cell_blockers.append("test_excess_not_positive")
        if not _nonnegative_integer(cell.get("test_trade_count")):
            cell_blockers.append("test_trade_count_missing_or_invalid")
        elif cell.get("test_trade_count") < 2:
            cell_blockers.append("test_trades_below_2")
        if not _finite_native(cell.get("test_max_drawdown_pct")):
            cell_blockers.append("test_drawdown_missing_or_nonfinite")
        if not _finite_native(cell.get("test_sharpe")):
            cell_blockers.append("test_sharpe_missing_or_nonfinite")
        if cell.get("cost_sensitivity_status") != "PASS":
            cell_blockers.append("cost_sensitivity_block")
        if cell_blockers:
            blockers.extend(f"{symbol}:{reason}" for reason in cell_blockers)
        else:
            passed += 1
    if len(cells) < required_symbols:
        blockers.append(f"confirmation_symbols:{len(cells)}<{required_symbols}")
    if passed < required_symbols:
        blockers.append(f"confirmation_passed:{passed}<{required_symbols}")
    return {
        "strategy_id": strategy_id,
        "status": "PASS" if not blockers else "BLOCK",
        "forward_candidate": not blockers,
        "confirmation_symbols": len(cells),
        "passed_symbols": passed,
        "blockers": list(dict.fromkeys(blockers)),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
