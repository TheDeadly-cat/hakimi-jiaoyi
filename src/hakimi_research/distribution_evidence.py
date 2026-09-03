from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import math
from typing import Any, Callable


DISTRIBUTION_EVIDENCE_VERSION = "tail-distribution-evidence-v2"
QUANTILE_METHOD = "historical-nearest-rank-lower-tail-v1"

_AUTHORITY_FIELDS = (
    "profitability_proven",
    "blind_test_complete",
    "paper_authorized",
    "live_authorized",
    "order_entry_authorized",
)


class DistributionEvidenceError(ValueError):
    """Raised when a source result or derived distribution artifact is invalid."""


def _fail(path: str, message: str) -> None:
    raise DistributionEvidenceError(f"{path}: {message}")


def _require_exact_native(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "object keys must be exact str values")
            _require_exact_native(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_native(item, f"{path}[{index}]")
        return
    if value_type in (str, int, bool) or value is None:
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "float values must be finite")
        return
    _fail(path, f"unsupported non-native type {value_type.__name__}")


def _canonical_json(value: Any, path: str) -> str:
    _require_exact_native(value, path)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _canonical_copy(value: Any, path: str) -> Any:
    return json.loads(_canonical_json(value, path))


def _canonical_sha256(value: Any, path: str) -> str:
    return hashlib.sha256(_canonical_json(value, path).encode("ascii")).hexdigest()


def _require_dict(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an exact list")
    return value


def _require_text(value: Any, path: str) -> str:
    if type(value) is not str or not value or len(value) > 512:
        _fail(path, "must be a non-empty exact str of at most 512 characters")
    if any(ord(character) < 32 for character in value):
        _fail(path, "must not contain control characters")
    return value


def _number(value: Any, path: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if type(value) not in (int, float):
        _fail(path, "must be an exact int or float")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        _fail(path, "must be finite numeric input")
    if not parsed.is_finite():
        _fail(path, "must be finite")
    if positive and parsed <= 0:
        _fail(path, "must be positive")
    if nonnegative and parsed < 0:
        _fail(path, "must be nonnegative")
    return parsed


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    with localcontext() as context:
        context.prec = 50
        rounded = value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN)
    text = format(rounded, "f").rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    return text


def _parse_time(value: Any, path: str) -> datetime:
    text = _require_text(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        _fail(path, "must be an ISO-8601 timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must include an explicit timezone")
    return parsed.astimezone(timezone.utc)


def _resolve_path(root: Any, source_path: Any) -> Any:
    path = _require_list(source_path, "source_result_path")
    if not path:
        _fail("source_result_path", "must not be empty")
    current = root
    for index, step in enumerate(path):
        step_path = f"source_result_path[{index}]"
        if type(step) is str:
            if type(current) is not dict or step not in current:
                _fail(step_path, "does not resolve in source report")
            current = current[step]
        elif type(step) is int and step >= 0:
            if type(current) is not list or step >= len(current):
                _fail(step_path, "does not resolve in source report")
            current = current[step]
        else:
            _fail(step_path, "must be an exact str key or nonnegative int index")
    return current


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _sample_std(values: list[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    average = _mean(values)
    variance = sum((value - average) ** 2 for value in values) / Decimal(len(values) - 1)
    with localcontext() as context:
        context.prec = 50
        return variance.sqrt()


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _compound(values: list[Decimal]) -> Decimal:
    result = Decimal(1)
    for value in values:
        result *= Decimal(1) + value
    return result - Decimal(1)


def _bucket_returns(
    points: list[tuple[datetime, Decimal, str]],
    key: Callable[[datetime], str],
) -> list[dict[str, Any]]:
    grouped: list[tuple[str, list[Decimal]]] = []
    for instant, equity, _ in points:
        bucket = key(instant)
        if not grouped or grouped[-1][0] != bucket:
            grouped.append((bucket, []))
        grouped[-1][1].append(equity)
    results: list[dict[str, Any]] = []
    prior_close: Decimal | None = None
    for index, (bucket, equities) in enumerate(grouped):
        base = equities[0] if prior_close is None else prior_close
        bucket_return = equities[-1] / base - Decimal(1)
        results.append({
            "period": bucket,
            "return": _decimal_text(bucket_return),
            "partial_start": index == 0,
        })
        prior_close = equities[-1]
    return results


def _distribution_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [Decimal(item["return"]) for item in rows]
    return {
        "count": len(values),
        "positive_count": sum(value > 0 for value in values),
        "negative_count": sum(value < 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "mean": _decimal_text(_mean(values)),
        "median": _decimal_text(_median(values)),
        "minimum": _decimal_text(min(values)),
        "maximum": _decimal_text(max(values)),
    }


def _tail_losses(
    returns: list[Decimal],
    *,
    confidence: Decimal,
    minimum_count: int,
) -> tuple[Decimal | None, Decimal | None]:
    if len(returns) < minimum_count:
        return None, None
    tail_count = max(1, math.ceil(len(returns) * float(Decimal(1) - confidence)))
    tail = sorted(returns)[:tail_count]
    threshold_loss = max(Decimal(0), -tail[-1])
    expected_shortfall = max(Decimal(0), -_mean(tail))
    return threshold_loss, expected_shortfall


def _build_distribution_evidence(
    source_report: dict[str, Any],
    *,
    source_result_path: list[str | int],
    periods_per_year: int,
) -> dict[str, Any]:
    _require_exact_native(source_report, "source_report")
    _require_exact_native(source_result_path, "source_result_path")
    if type(periods_per_year) is not int or periods_per_year <= 0:
        _fail("periods_per_year", "must be an exact positive int")
    source_result = _require_dict(
        _resolve_path(source_report, source_result_path),
        "source_result",
    )
    curve = _require_list(source_result.get("equity_curve"), "source_result.equity_curve")
    if len(curve) < 2:
        _fail("source_result.equity_curve", "requires at least two observations")
    points: list[tuple[datetime, Decimal, str]] = []
    for index, item in enumerate(curve):
        row = _require_dict(item, f"source_result.equity_curve[{index}]")
        instant = _parse_time(row.get("time"), f"source_result.equity_curve[{index}].time")
        equity = _number(row.get("equity"), f"source_result.equity_curve[{index}].equity", positive=True)
        points.append((instant, equity, row["time"]))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            _fail("source_result.equity_curve", "timestamps must be strictly increasing")

    returns = [points[index][1] / points[index - 1][1] - Decimal(1) for index in range(1, len(points))]
    average_return = _mean(returns)
    period_std = _sample_std(returns)
    with localcontext() as context:
        context.prec = 50
        annualization_root = Decimal(periods_per_year).sqrt()
    annualized_volatility = period_std * annualization_root if period_std is not None else None
    negative_returns = [min(value, Decimal(0)) for value in returns]
    downside_sum = sum(value * value for value in negative_returns)
    downside_deviation: Decimal | None = None
    if any(value < 0 for value in returns):
        with localcontext() as context:
            context.prec = 50
            downside_deviation = (downside_sum / Decimal(len(returns))).sqrt()
    sortino = (
        average_return / downside_deviation * annualization_root
        if downside_deviation not in (None, Decimal(0))
        else None
    )

    peak = points[0][1]
    max_drawdown = Decimal(0)
    drawdown_duration = 0
    max_drawdown_duration = 0
    current_drawdown_start: str | None = None
    max_drawdown_start: str | None = None
    max_drawdown_end: str | None = None
    for _, equity, timestamp_text in points:
        if equity >= peak:
            peak = equity
            drawdown_duration = 0
            current_drawdown_start = None
        else:
            if current_drawdown_start is None:
                current_drawdown_start = timestamp_text
            drawdown_duration += 1
            if drawdown_duration > max_drawdown_duration:
                max_drawdown_duration = drawdown_duration
                max_drawdown_start = current_drawdown_start
                max_drawdown_end = timestamp_text
            max_drawdown = max(max_drawdown, Decimal(1) - equity / peak)
    source_cagr = _number(source_result.get("annualized_return"), "source_result.annualized_return")
    calmar = source_cagr / max_drawdown if max_drawdown > 0 else None

    fills = _require_list(source_result.get("fills"), "source_result.fills")
    fill_events: list[tuple[datetime, str, Decimal, Decimal, Decimal]] = []
    closed_pnls: list[Decimal] = []
    total_notional = Decimal(0)
    for index, item in enumerate(fills):
        fill = _require_dict(item, f"source_result.fills[{index}]")
        action = _require_text(fill.get("action"), f"source_result.fills[{index}].action")
        if action not in ("BUY", "SELL"):
            _fail(f"source_result.fills[{index}].action", "must be BUY or SELL")
        quantity = _number(fill.get("quantity"), f"source_result.fills[{index}].quantity", positive=True)
        price = _number(fill.get("price"), f"source_result.fills[{index}].price", positive=True)
        pnl = _number(fill.get("pnl"), f"source_result.fills[{index}].pnl")
        fill_time = _parse_time(fill.get("fill_time"), f"source_result.fills[{index}].fill_time")
        fill_events.append((fill_time, action, quantity, price, pnl))
        total_notional += quantity * price
        if action == "SELL":
            closed_pnls.append(pnl)
    fill_events.sort(key=lambda item: item[0])
    if fill_events and fill_events[-1][0] > points[-1][0]:
        _fail("source_result.fills", "fill_time cannot exceed the equity-curve end")
    position = Decimal(0)
    fill_index = 0
    exposed_periods = 0
    for instant, _, _ in points:
        while fill_index < len(fill_events) and fill_events[fill_index][0] <= instant:
            _, action, quantity, _, _ = fill_events[fill_index]
            position += quantity if action == "BUY" else -quantity
            if position < Decimal("-0.000000000001"):
                _fail("source_result.fills", "position replay became negative")
            if abs(position) <= Decimal("0.000000000001"):
                position = Decimal(0)
            fill_index += 1
        if position > 0:
            exposed_periods += 1

    mean_equity = _mean([item[1] for item in points])
    turnover_ratio = total_notional / mean_equity
    total_fees_value = source_result.get("total_fees")
    total_fees = (
        _number(total_fees_value, "source_result.total_fees")
        if total_fees_value is not None
        else None
    )
    fee_load_ratio = (
        total_fees / total_notional
        if total_fees is not None and total_notional > 0
        else None
    )
    fee_load_gap = (
        "FEE_LOAD_UNAVAILABLE_TOTAL_FEES_MISSING"
        if total_fees is None
        else "FEE_LOAD_UNAVAILABLE_NO_TRADED_NOTIONAL"
        if total_notional <= 0
        else None
    )
    exposure_ratio = Decimal(exposed_periods) / Decimal(len(points))
    wins = [value for value in closed_pnls if value > 0]
    losses = [value for value in closed_pnls if value < 0]
    profit_factor = sum(wins, Decimal(0)) / abs(sum(losses, Decimal(0))) if wins and losses else None
    payoff_ratio = _mean(wins) / abs(_mean(losses)) if wins and losses else None
    trade_expectancy = _mean(closed_pnls) if closed_pnls else None
    win_rate = Decimal(len(wins)) / Decimal(len(closed_pnls)) if closed_pnls else None

    var_95, cvar_95 = _tail_losses(returns, confidence=Decimal("0.95"), minimum_count=20)
    var_99, cvar_99 = _tail_losses(returns, confidence=Decimal("0.99"), minimum_count=100)
    monthly = _bucket_returns(points, lambda instant: instant.strftime("%Y-%m"))
    yearly = _bucket_returns(points, lambda instant: instant.strftime("%Y"))
    monthly_values = [Decimal(item["return"]) for item in monthly]
    positive_months = [value for value in monthly_values if value > 0]
    top_month_share = max(positive_months) / sum(positive_months, Decimal(0)) if positive_months else None
    without_best_month = (
        _compound([value for index, value in enumerate(monthly_values) if index != monthly_values.index(max(monthly_values))])
        if monthly_values
        else None
    )
    top_trade_share = max(wins) / sum(wins, Decimal(0)) if wins else None
    without_best_trade = sum(closed_pnls, Decimal(0)) - max(wins) if wins else None
    positive_returns = [value for value in returns if value > 0]
    positive_return_total = sum(positive_returns, Decimal(0))
    top_period_share = (
        max(positive_returns) / positive_return_total if positive_returns else None
    )
    positive_period_hhi = (
        sum((value / positive_return_total) ** 2 for value in positive_returns)
        if positive_returns
        else None
    )
    without_best_period = (
        _compound([
            value
            for index, value in enumerate(returns)
            if index != returns.index(max(returns))
        ])
        if returns
        else None
    )
    positive_trade_total = sum(wins, Decimal(0))
    positive_trade_hhi = (
        sum((value / positive_trade_total) ** 2 for value in wins)
        if wins
        else None
    )
    fixed_window_length = 21
    if len(returns) > fixed_window_length:
        window_returns = [
            _compound(returns[start : start + fixed_window_length])
            for start in range(len(returns) - fixed_window_length + 1)
        ]
        best_window_index = max(
            range(len(window_returns)),
            key=lambda index: window_returns[index],
        )
        best_fixed_window = {
            "state": "OBSERVED",
            "window_length": fixed_window_length,
            "candidate_count": len(window_returns),
            "start_index": best_window_index,
            "end_index_exclusive": best_window_index + fixed_window_length,
            "start_time": points[best_window_index][2],
            "end_time": points[best_window_index + fixed_window_length][2],
            "compounded_return": _decimal_text(window_returns[best_window_index]),
            "gap_code": None,
        }
    else:
        best_fixed_window = {
            "state": "GAP",
            "window_length": fixed_window_length,
            "candidate_count": 0,
            "start_index": None,
            "end_index_exclusive": None,
            "start_time": None,
            "end_time": None,
            "compounded_return": None,
            "gap_code": "FIXED_21_PERIOD_WINDOW_UNAVAILABLE",
        }

    gaps: list[str] = []
    if downside_deviation is None:
        gaps.append("SORTINO_UNDEFINED_NO_DOWNSIDE")
    if max_drawdown == 0:
        gaps.append("CALMAR_UNDEFINED_NO_DRAWDOWN")
    if not closed_pnls:
        gaps.append("TRADE_DISTRIBUTION_UNAVAILABLE")
    elif not wins or not losses:
        gaps.append("PROFIT_FACTOR_AND_PAYOFF_UNDEFINED_ONE_SIDED_TRADES")
    if var_95 is None:
        gaps.append("TAIL_SAMPLE_LT_20")
    if var_99 is None:
        gaps.append("TAIL_SAMPLE_LT_100")
    if len(monthly) < 2:
        gaps.append("MONTH_BUCKET_COUNT_LT_2")
    if len(yearly) < 2:
        gaps.append("YEAR_BUCKET_COUNT_LT_2")
    if top_month_share is None:
        gaps.append("POSITIVE_MONTH_CONCENTRATION_UNAVAILABLE")
    if top_trade_share is None:
        gaps.append("POSITIVE_TRADE_CONCENTRATION_UNAVAILABLE")
    if top_period_share is None:
        gaps.append("POSITIVE_PERIOD_CONCENTRATION_UNAVAILABLE")
    if fee_load_ratio is None:
        assert fee_load_gap is not None
        gaps.append(fee_load_gap)
    if best_fixed_window["state"] == "GAP":
        gaps.append("FIXED_21_PERIOD_WINDOW_UNAVAILABLE")
    gaps = sorted(set(gaps))

    evidence: dict[str, Any] = {
        "schema_version": DISTRIBUTION_EVIDENCE_VERSION,
        "status": "OBSERVED" if not gaps else "PARTIAL",
        "source_report_sha256": _canonical_sha256(source_report, "source_report"),
        "source_result_path": _canonical_copy(source_result_path, "source_result_path"),
        "source_result_sha256": _canonical_sha256(source_result, "source_result"),
        "periods_per_year": periods_per_year,
        "quantile_method": QUANTILE_METHOD,
        "metrics": {
            "cagr_observation": _decimal_text(source_cagr),
            "annualized_volatility": _decimal_text(annualized_volatility),
            "sortino_ratio": _decimal_text(sortino),
            "calmar_ratio": _decimal_text(calmar),
            "max_drawdown": _decimal_text(max_drawdown),
            "max_drawdown_duration_periods": max_drawdown_duration,
            "max_drawdown_duration_start": max_drawdown_start,
            "max_drawdown_duration_end": max_drawdown_end,
            "profit_factor": _decimal_text(profit_factor),
            "win_rate": _decimal_text(win_rate),
            "payoff_ratio": _decimal_text(payoff_ratio),
            "trade_expectancy": _decimal_text(trade_expectancy),
            "turnover_ratio": _decimal_text(turnover_ratio),
            "fee_load_ratio": _decimal_text(fee_load_ratio),
            "market_exposure_ratio": _decimal_text(exposure_ratio),
            "tail_var_95": _decimal_text(var_95),
            "tail_cvar_95": _decimal_text(cvar_95),
            "tail_var_99": _decimal_text(var_99),
            "tail_cvar_99": _decimal_text(cvar_99),
            "period_return_count": len(returns),
            "closed_trade_count": len(closed_pnls),
        },
        "monthly_returns": monthly,
        "monthly_summary": _distribution_summary(monthly),
        "yearly_returns": yearly,
        "yearly_summary": _distribution_summary(yearly),
        "concentration": {
            "top_positive_period_return_share": _decimal_text(top_period_share),
            "positive_period_return_hhi": _decimal_text(positive_period_hhi),
            "compound_return_without_best_period": _decimal_text(without_best_period),
            "top_positive_month_share": _decimal_text(top_month_share),
            "compound_return_without_best_month": _decimal_text(without_best_month),
            "top_positive_trade_pnl_share": _decimal_text(top_trade_share),
            "positive_trade_pnl_hhi": _decimal_text(positive_trade_hhi),
            "pnl_without_best_trade": _decimal_text(without_best_trade),
            "best_fixed_21_period_window": best_fixed_window,
        },
        "gaps": gaps,
        "authority": {field: False for field in _AUTHORITY_FIELDS},
    }
    evidence["evidence_sha256"] = _canonical_sha256(evidence, "distribution_evidence_without_digest")
    return evidence


def build_distribution_evidence(
    source_report: dict[str, Any],
    *,
    source_result_path: list[str | int],
    periods_per_year: int,
) -> dict[str, Any]:
    """Derive a deterministic tail/distribution artifact from a report-contained result."""

    return _build_distribution_evidence(
        source_report,
        source_result_path=source_result_path,
        periods_per_year=periods_per_year,
    )


def verify_distribution_evidence(
    evidence: dict[str, Any],
    source_report: dict[str, Any],
) -> dict[str, Any]:
    """Recompute the complete artifact and require exact equality."""

    _require_exact_native(evidence, "distribution_evidence")
    value = _require_dict(evidence, "distribution_evidence")
    if value.get("schema_version") != DISTRIBUTION_EVIDENCE_VERSION:
        _fail("distribution_evidence.schema_version", f"must equal {DISTRIBUTION_EVIDENCE_VERSION}")
    authority = _require_dict(value.get("authority"), "distribution_evidence.authority")
    if set(authority) != set(_AUTHORITY_FIELDS):
        _fail("distribution_evidence.authority", "authority fields are incomplete")
    for field in _AUTHORITY_FIELDS:
        if type(authority[field]) is not bool or authority[field] is not False:
            _fail(f"distribution_evidence.authority.{field}", "must be exact false")
    expected = _build_distribution_evidence(
        source_report,
        source_result_path=value.get("source_result_path"),
        periods_per_year=value.get("periods_per_year"),
    )
    if value != expected:
        _fail("distribution_evidence", "does not exactly match recomputed source observations")
    return {
        "state": value["status"],
        "gaps": list(value["gaps"]),
        "period_return_count": value["metrics"]["period_return_count"],
        "closed_trade_count": value["metrics"]["closed_trade_count"],
    }


__all__ = [
    "DISTRIBUTION_EVIDENCE_VERSION",
    "QUANTILE_METHOD",
    "DistributionEvidenceError",
    "build_distribution_evidence",
    "verify_distribution_evidence",
]
