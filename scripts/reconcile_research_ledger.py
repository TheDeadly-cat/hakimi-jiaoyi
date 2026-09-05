"""Independent Decimal ledger reconciliation; standard library only.

Consumes existing JSON reports/snapshots. Does not import or run the research
engine, generate signals, fetch data, or modify either input.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import tempfile


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("finite_number_required")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("finite_number_required")
    return result


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def reconcile(report: dict, snapshot: dict) -> dict:
    with localcontext() as ctx:
        ctx.prec = 50
        return _reconcile(report, snapshot)


def _reconcile(report, snapshot):
    checks, failures = [], []
    maximum_error = Decimal(0)

    def check(label, actual, expected):
        nonlocal maximum_error
        observed, target = number(actual), number(expected)
        error = abs(observed - target)
        maximum_error = max(maximum_error, error)
        tolerance = Decimal("1e-8") + max(abs(observed), abs(target)) * Decimal("1e-10")
        checks.append(label)
        if error > tolerance:
            failures.append({"field": label, "observed": str(observed), "expected": str(target),
                             "absolute_error": str(error), "tolerance": str(tolerance)})

    def condition(label, valid):
        checks.append(label)
        if not valid:
            failures.append({"field": label, "error": "condition_failed"})

    spec, result = report["spec"], report["result"]
    condition("snapshot_identity", report["dataset"]["snapshot_id"] == snapshot["snapshot_id"] == spec["snapshot_id"])
    condition("normalized_data_identity", report["dataset"]["data_hash"] == snapshot["data_hash"])
    start, end = stamp(spec["score_start"]), stamp(spec["score_end"])
    bars = [row for row in snapshot["candles"] if start <= stamp(row[0]) < end]
    condition("hourly_score_interval_count", len(bars) == int((end - start).total_seconds() / 3600))
    condition("equity_observation_count", len(result["equity_curve"]) == len(bars) + 1)
    condition("return_observation_count", len(result["return_series"]) == len(bars))
    if not bars or len(result["equity_curve"]) != len(bars) + 1 or len(result["return_series"]) != len(bars):
        raise ValueError("scored_equity_or_return_shape_invalid")
    fills = result["fills"]
    by_bar = {}
    score_bar_times = {stamp(row[0]) for row in bars}
    for fill in fills:
        at = stamp(fill["fill_time"])
        condition("fill_inside_score", at in score_bar_times)
        by_bar.setdefault(at, []).append(fill)
    cash = initial = number(spec["initial_cash"])
    position = cost = entry_fees = realized = buy_fees = sell_fees = Decimal(0)
    previous = peak = initial
    maximum_drawdown = exposure_sum = Decimal(0)
    round_trips = 0
    fee_rate = number(spec["fee_rate"])
    check("initial_equity", result["equity_curve"][0]["equity"], initial)
    for index, row in enumerate(bars):
        at, close = stamp(row[0]), number(row[4])
        for fill in by_bar.get(at, []):
            qty, price, fee = (number(fill[key]) for key in ("quantity", "price", "fee"))
            condition("positive_fill_quantity_and_price", qty > 0 and price > 0 and fee >= 0)
            check("fill_fee_model", fee, qty * price * fee_rate)
            check("fill_position_before", fill["position_before"], position)
            if fill["action"] == "BUY":
                cash -= qty * price + fee
                position += qty
                cost += qty * price
                entry_fees += fee
                buy_fees += fee
                check("buy_fill_realized_pnl", fill["pnl"], 0)
            elif fill["action"] == "SELL":
                condition("sell_within_inventory", Decimal(0) < qty <= position + Decimal("1e-12"))
                if position <= 0:
                    raise ValueError("sell_without_inventory")
                share = min(qty / position, Decimal(1))
                allocated_cost, allocated_fee = cost * share, entry_fees * share
                pnl = qty * price - fee - allocated_cost - allocated_fee
                cash += qty * price - fee
                position -= qty
                cost -= allocated_cost
                entry_fees -= allocated_fee
                realized += pnl
                sell_fees += fee
                check("sell_fill_realized_pnl", fill["pnl"], pnl)
                # Treat a reported exact flat state only as rounding if the
                # independent remainder is immaterial in quote value.
                if number(fill["position_after"]) == 0 and abs(position * price) < Decimal("1e-8"):
                    position = cost = entry_fees = Decimal(0)
                    round_trips += 1
            else:
                raise ValueError("unsupported_fill_action")
            check("fill_cash_after", fill["cash_after"], cash)
            check("fill_position_after", fill["position_after"], position)
            check("fill_cumulative_realized", fill["realized_pnl_after"], realized)
        market_value = position * close
        equity = cash + market_value
        point = result["equity_curve"][index + 1]
        condition("equity_mark_time", stamp(point["time"]) == at + timedelta(hours=1))
        check("bar_equity", point["equity"], equity)
        check("bar_cash", point["cash"], cash)
        check("bar_position", point["position_qty"], position)
        check("bar_market_value", point["position_value"], market_value)
        if previous > 0:
            check("period_return", result["return_series"][index]["return"], equity / previous - 1)
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, 1 - equity / peak)
        exposure_sum += market_value / equity if equity > 0 else 0
        previous = equity
    unrealized = position * number(bars[-1][4]) - cost - entry_fees
    for field, expected in {
        "final_equity": previous, "final_cash": cash, "open_position_qty": position,
        "total_fees": buy_fees + sell_fees, "realized_pnl": realized, "unrealized_pnl": unrealized,
        "unallocated_entry_fees": entry_fees, "total_return": previous / initial - 1,
        "max_drawdown": maximum_drawdown, "fill_count": len(fills), "round_trip_count": round_trips,
        "exposure_ratio": exposure_sum / len(bars),
    }.items():
        check(field, result[field], expected)
    check("net_pnl_conservation", previous - initial, realized + unrealized)
    absent_fee_fields = []
    for field, expected in (("buy_fees", buy_fees), ("sell_fees", sell_fees)):
        if field in result:
            check(field, result[field], expected)
        else:
            absent_fee_fields.append(field)
    return {
        "schema_version": "independent-decimal-ledger-reconciliation-v1",
        "status": "FAIL" if failures else "PASS", "checks": len(checks), "failures": failures,
        "report_hash": report["report_hash"], "snapshot_id": snapshot["snapshot_id"],
        "score_bars": len(bars), "fill_count": len(fills),
        "maximum_absolute_numeric_error": str(maximum_error),
        "reconciled_buy_fees": str(buy_fees), "reconciled_sell_fees": str(sell_fees),
        "legacy_report_fee_fields_absent": absent_fee_fields,
        "scope": "Read-only Decimal reconciliation of recorded fills, cash, inventory, fees, PnL, equity, returns, drawdown and exposure. No strategy or market-effectiveness assessment.",
        "project_numerical_engine_imported": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    report_bytes, snapshot_bytes = args.report.read_bytes(), args.snapshot.read_bytes()
    result = reconcile(json.loads(report_bytes, parse_float=Decimal), json.loads(snapshot_bytes, parse_float=Decimal))
    result["report_file_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    result["snapshot_file_sha256"] = hashlib.sha256(snapshot_bytes).hexdigest()
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        target = args.output_dir / f"ledger_{result['receipt_sha256']}.json"
        content = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
        with tempfile.NamedTemporaryFile(dir=args.output_dir, prefix=".ledger-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != content:
                    raise
        finally:
            temporary.unlink()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
