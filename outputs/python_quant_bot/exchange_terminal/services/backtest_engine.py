from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from statistics import fmean, pstdev
from typing import Any, Callable

try:
    from market_data.candle_contract import candle_is_complete
except ModuleNotFoundError:
    from exchange_terminal.market_data.candle_contract import candle_is_complete

from .market_calendar import build_market_calendar_contract, infer_market_calendar


DATASET_SCHEMA_VERSION = "backtest-dataset-v4"
EXECUTION_MODEL_VERSION = "signal-close-next-open-ohlc-conservative-v3"
CAUSAL_AUDIT_VERSION = "causal-prefix-invariance-v2"

SignalFunction = Callable[[list[Any], float, bool, float, float], dict[str, Any]]
SignalFactory = Callable[[list[dict[str, Any]]], SignalFunction]
ALLOWED_SIGNAL_ACTIONS = frozenset({"HOLD", "BUY", "ADD", "SELL", "EXIT"})


@dataclass(frozen=True)
class BacktestCosts:
    fee_rate: float = 0.0005
    slippage_bps: float = 0.0

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000.0


def numeric_parameter_contract_issues(
    parameters: dict[str, Any],
    *,
    positive: tuple[str, ...] = (),
    integer: tuple[str, ...] = (),
    minimum: dict[str, float] | None = None,
    maximum: dict[str, float] | None = None,
) -> list[str]:
    positive_names = set(positive)
    integer_names = set(integer)
    minimums = dict(minimum or {})
    maximums = dict(maximum or {})
    issues: list[str] = []
    for name, value in parameters.items():
        if value is None:
            continue
        if isinstance(value, bool):
            issues.append(f"{name}:not_numeric")
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError):
            issues.append(f"{name}:not_numeric")
            continue
        if not math.isfinite(numeric):
            issues.append(f"{name}:not_finite")
        else:
            if name in positive_names and numeric <= 0:
                issues.append(f"{name}:must_be_positive")
            if name in integer_names and not numeric.is_integer():
                issues.append(f"{name}:must_be_integer")
            if name in minimums and numeric < float(minimums[name]):
                issues.append(f"{name}:below_minimum:{minimums[name]}")
            if name in maximums and numeric > float(maximums[name]):
                issues.append(f"{name}:above_maximum:{maximums[name]}")
    return issues


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _invoke_signal(
    signal_fn: SignalFunction,
    history: list[Any],
    price: float,
    has_position: bool,
    entry_price: float,
    last_scale_price: float,
) -> tuple[dict[str, Any] | None, str]:
    try:
        raw = signal_fn(history, price, has_position, entry_price, last_scale_price)
    except Exception as exc:
        return None, f"strategy_signal_exception:{type(exc).__name__}:{str(exc)[:160]}"
    if not isinstance(raw, dict):
        return None, "strategy_signal_not_object"
    action = str(raw.get("action") or "").strip().upper()
    if action not in ALLOWED_SIGNAL_ACTIONS:
        return None, f"strategy_signal_action_invalid:{action or 'MISSING'}"
    return {
        **raw,
        "action": action,
        "reason": str(raw.get("reason") or ""),
    }, ""


def _periods_per_year(market: str, timeframe: str) -> int:
    market_days = 252 if str(market or "").strip().lower() == "stock" else 365
    minutes_per_day = 390 if market_days == 252 else 24 * 60
    normalized = str(timeframe or "").strip().lower().replace(" ", "")
    try:
        if normalized.endswith("m"):
            minutes = float(normalized[:-1])
            return max(int(round(market_days * minutes_per_day / minutes)), 1) if minutes > 0 else market_days
        if normalized.endswith("h"):
            hours = float(normalized[:-1])
            return max(int(round(market_days * minutes_per_day / (hours * 60))), 1) if hours > 0 else market_days
        if normalized.endswith("w"):
            weeks = float(normalized[:-1])
            return max(int(round(52 / weeks)), 1) if weeks > 0 else market_days
    except (TypeError, ValueError, OverflowError):
        return market_days
    return market_days


def _timestamp_ms(row: dict[str, Any]) -> int:
    for key in ("ts_ms", "ts", "time"):
        value = row.get(key)
        if value not in (None, ""):
            try:
                numeric = int(float(value))
                return numeric * 1000 if 0 < numeric < 10_000_000_000 else numeric
            except (TypeError, ValueError, OverflowError):
                return 0
    text = str(row.get("date") or "").strip()
    if not text:
        return 0
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        return 0


def _is_complete(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def _session_date(row: dict[str, Any], ts_ms: int) -> str:
    text = str(row.get("date") or "").strip()
    if text:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()
        except (TypeError, ValueError, OverflowError):
            return ""
    try:
        return datetime.fromtimestamp(ts_ms / 1000, timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _daily_gap_policy(symbol: str, market: str, timeframe: str) -> tuple[str, int]:
    normalized_timeframe = str(timeframe or "").strip().lower().replace(" ", "")
    if normalized_timeframe not in {"1d", "1dutc", "d", "day", "daily"}:
        return "", 0
    market_kind = str(market or "").strip().lower()
    if market_kind not in {"stock", "crypto"}:
        clean_symbol = str(symbol or "").upper()
        market_kind = "crypto" if "-USDT" in clean_symbol or clean_symbol.endswith("-SWAP") else "stock"
    if market_kind == "stock":
        # Weekends, exchange holidays, and short holiday clusters are expected.
        return market_kind, 10 * 86_400_000
    # A two-day timestamp jump means at least one missing 24/7 daily bar.
    return market_kind, int(1.5 * 86_400_000)


def prepare_backtest_dataset(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    source: str,
    timeframe: str = "1D",
    minimum_rows: int = 120,
    market: str = "",
    daily_continuity_policy: str = "STRICT",
) -> dict[str, Any]:
    """Validate and fingerprint every OHLCV row without silently repairing history."""

    market_kind, maximum_allowed_gap_ms = _daily_gap_policy(symbol, market, timeframe)
    continuity_policy = str(daily_continuity_policy or "").strip().upper()
    continuity_deferred = continuity_policy == "DEFER_TO_PORTFOLIO_LIFECYCLE"
    normalized: list[dict[str, Any]] = []
    normalized_session_dates: list[str] = []
    invalid_rows: list[int] = []
    incomplete_rows: list[int] = []
    incomplete_timestamps: list[tuple[int, int]] = []
    session_date_timestamp_mismatches: list[dict[str, Any]] = []
    for index, raw in enumerate(rows or []):
        if not isinstance(raw, dict):
            invalid_rows.append(index)
            continue
        if not _is_complete(raw):
            incomplete_rows.append(index)
            incomplete_timestamps.append((index, _timestamp_ms(raw)))
            continue
        raw_numeric_values = (
            raw.get("ts_ms", raw.get("ts", raw.get("time"))),
            raw.get("open", raw.get("close")),
            raw.get("high"),
            raw.get("low"),
            raw.get("close"),
            raw.get("volume", raw.get("volume_quote", raw.get("vol"))),
        )
        if any(isinstance(value, bool) for value in raw_numeric_values if value is not None):
            invalid_rows.append(index)
            continue
        ts_ms = _timestamp_ms(raw)
        session_date = _session_date(raw, ts_ms)
        try:
            close = float(raw.get("close"))
            open_price = float(raw.get("open", close))
            high = float(raw.get("high", max(open_price, close)))
            low = float(raw.get("low", min(open_price, close)))
            volume = float(raw.get("volume", raw.get("volume_quote", raw.get("vol", 0.0))) or 0.0)
        except (TypeError, ValueError, OverflowError):
            invalid_rows.append(index)
            continue
        values = (open_price, high, low, close, volume)
        valid = (
            ts_ms > 0
            and bool(session_date)
            and all(math.isfinite(value) for value in values)
            and min(open_price, high, low, close) > 0
            and volume >= 0
            and math.isfinite(close * volume)
            and high >= max(open_price, close, low)
            and low <= min(open_price, close, high)
        )
        if not valid:
            invalid_rows.append(index)
            continue
        if maximum_allowed_gap_ms > 0:
            try:
                timestamp_session_date = datetime.fromtimestamp(ts_ms / 1000, timezone.utc).date().isoformat()
            except (TypeError, ValueError, OverflowError, OSError):
                timestamp_session_date = ""
            if timestamp_session_date != session_date:
                session_date_timestamp_mismatches.append({
                    "index": index,
                    "session_date": session_date,
                    "timestamp_session_date_utc": timestamp_session_date,
                    "ts_ms": ts_ms,
                })
        normalized.append({
            "date": session_date if maximum_allowed_gap_ms > 0 else str(raw.get("date") or session_date),
            "ts_ms": ts_ms,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "complete": True,
        })
        normalized_session_dates.append(session_date)

    timestamps = [row["ts_ms"] for row in normalized]
    duplicate_count = len(timestamps) - len(set(timestamps))
    ordered = all(current > previous for previous, current in zip(timestamps, timestamps[1:]))
    trading_dates = normalized_session_dates if maximum_allowed_gap_ms > 0 else []
    duplicate_trading_date_count = (
        len(trading_dates) - len(set(trading_dates))
        if maximum_allowed_gap_ms > 0 else 0
    )
    chronological_rows = sorted(normalized, key=lambda item: int(item["ts_ms"]))
    observed_gaps = [
        {
            "from": previous["date"],
            "to": current["date"],
            "gap_ms": int(current["ts_ms"] - previous["ts_ms"]),
            "gap_days": round((current["ts_ms"] - previous["ts_ms"]) / 86_400_000, 4),
        }
        for previous, current in zip(chronological_rows, chronological_rows[1:])
        if int(current["ts_ms"]) > int(previous["ts_ms"])
    ]
    excessive_gaps = [
        item for item in observed_gaps
        if (
            not continuity_deferred
            and maximum_allowed_gap_ms > 0
            and int(item["gap_ms"]) > maximum_allowed_gap_ms
        )
    ]
    maximum_gap_ms = max((int(item["gap_ms"]) for item in observed_gaps), default=0)
    source_text = str(source or "").strip()
    source_lower = source_text.lower()
    synthetic_source = any(token in source_lower for token in ("quick_preview", "preview_seed", "offline-seed", "synthetic"))
    latest_complete_ts = max(timestamps, default=0)
    historical_incomplete_rows = [
        index for index, ts_ms in incomplete_timestamps
        if ts_ms <= 0 or (latest_complete_ts > 0 and ts_ms <= latest_complete_ts)
    ]
    trailing_incomplete_rows = [
        index for index, ts_ms in incomplete_timestamps
        if ts_ms > latest_complete_ts > 0
    ]
    market_calendar: dict[str, Any] = {}
    if market_kind == "stock" and normalized and not continuity_deferred:
        market_calendar = build_market_calendar_contract(
            calendar_name=infer_market_calendar(symbol, source=source_text),
            start_date=normalized[0]["date"],
            end_date=normalized[-1]["date"],
            observed_dates=normalized_session_dates,
        )
    blockers: list[str] = []
    warnings: list[str] = []
    if continuity_policy not in {"STRICT", "DEFER_TO_PORTFOLIO_LIFECYCLE"}:
        blockers.append(f"daily_continuity_policy_invalid:{continuity_policy or 'MISSING'}")
    if invalid_rows:
        blockers.append(f"invalid_ohlcv_rows:{len(invalid_rows)}")
    if duplicate_count:
        blockers.append(f"duplicate_timestamps:{duplicate_count}")
    if duplicate_trading_date_count:
        blockers.append(f"duplicate_trading_dates:{duplicate_trading_date_count}")
    if session_date_timestamp_mismatches:
        blockers.append(f"session_date_timestamp_mismatch:{len(session_date_timestamp_mismatches)}")
    if normalized and not ordered:
        blockers.append("timestamps_not_strictly_increasing")
    if excessive_gaps:
        blockers.append(f"temporal_gaps_exceed_policy:{len(excessive_gaps)}")
    if historical_incomplete_rows:
        blockers.append(f"historical_incomplete_rows:{len(historical_incomplete_rows)}")
    if market_calendar and market_calendar.get("status") != "PASS":
        blockers.extend(
            f"market_calendar:{item}"
            for item in market_calendar.get("blockers") or ["calendar_contract_blocked"]
        )
    if synthetic_source:
        blockers.append("synthetic_or_preview_source")
    if trailing_incomplete_rows:
        warnings.append(f"excluded_trailing_incomplete_rows:{len(trailing_incomplete_rows)}")
    if continuity_deferred:
        warnings.append("daily_continuity_deferred_to_portfolio_lifecycle")
    if len(normalized) < max(int(minimum_rows), 1):
        blockers.append(f"insufficient_rows:{len(normalized)}")

    canonical_rows = [
        [row["ts_ms"], row["open"], row["high"], row["low"], row["close"], row["volume"]]
        for row in normalized
    ]
    full_hash = _canonical_hash(canonical_rows)
    first_ts = timestamps[0] if timestamps else 0
    last_ts = timestamps[-1] if timestamps else 0
    manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "hash_scope": "FULL_OHLCV",
        "symbol": str(symbol or "").upper(),
        "timeframe": timeframe,
        "source": source_text,
        "row_count": len(normalized),
        "input_row_count": len(rows or []),
        "first_ts_ms": first_ts,
        "last_ts_ms": last_ts,
        "first": normalized[0]["date"] if normalized else "",
        "last": normalized[-1]["date"] if normalized else "",
        "data_hash": full_hash,
        "ordered": ordered,
        "duplicate_count": duplicate_count,
        "duplicate_trading_date_count": duplicate_trading_date_count,
        "session_date_timestamp_mismatch_count": len(session_date_timestamp_mismatches),
        "session_date_timestamp_mismatch_examples": session_date_timestamp_mismatches[:5],
        "invalid_row_count": len(invalid_rows),
        "excluded_incomplete_count": len(incomplete_rows),
        "historical_incomplete_count": len(historical_incomplete_rows),
        "historical_incomplete_examples": historical_incomplete_rows[:5],
        "trailing_incomplete_count": len(trailing_incomplete_rows),
        "market": market_kind,
        "daily_continuity_policy": continuity_policy,
        "market_calendar": {
            "schema_version": market_calendar.get("schema_version", ""),
            "status": market_calendar.get("status", "NOT_APPLICABLE"),
            "calendar_name": market_calendar.get("calendar_name", ""),
            "provider": market_calendar.get("provider", ""),
            "provider_version": market_calendar.get("provider_version", ""),
            "start": market_calendar.get("start", ""),
            "end": market_calendar.get("end", ""),
            "session_count": market_calendar.get("session_count", 0),
            "missing_dates": list(market_calendar.get("missing_dates") or []),
            "unexpected_dates": list(market_calendar.get("unexpected_dates") or []),
            "schedule_hash": market_calendar.get("schedule_hash", ""),
            "contract_hash": market_calendar.get("contract_hash", ""),
            "blockers": list(market_calendar.get("blockers") or []),
        } if market_calendar else {
            "status": "NOT_APPLICABLE",
            "calendar_name": "",
            "blockers": [],
        },
        "maximum_gap_ms": maximum_gap_ms,
        "maximum_gap_days": round(maximum_gap_ms / 86_400_000, 4) if maximum_gap_ms else 0.0,
        "maximum_allowed_gap_ms": maximum_allowed_gap_ms,
        "maximum_allowed_gap_days": round(maximum_allowed_gap_ms / 86_400_000, 4) if maximum_allowed_gap_ms else 0.0,
        "temporal_gap_count": len(excessive_gaps),
        "temporal_gap_examples": excessive_gaps[:5],
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "warnings": warnings,
    }
    return {"status": manifest["status"], "rows": normalized, "manifest": manifest}


def _max_drawdown(values: list[float]) -> float:
    peak = values[0] if values else 0.0
    result = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            result = max(result, (peak - value) / peak)
    return result


def _sharpe(values: list[float], periods_per_year: int) -> float:
    returns = [current / previous - 1 for previous, current in zip(values, values[1:]) if previous > 0]
    if len(returns) < 5:
        return 0.0
    deviation = pstdev(returns)
    return fmean(returns) / deviation * math.sqrt(periods_per_year) if deviation > 0 else 0.0


def run_causal_long_only_backtest(
    *,
    rows: list[dict[str, Any]],
    symbol: str,
    source: str,
    signal_fn: SignalFunction,
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    startup_candles: int,
    fee_rate: float = 0.0005,
    slippage_bps: float = 0.0,
    leverage: float = 1.0,
    initial_cash: float = 10_000.0,
    market: str = "crypto",
    timeframe: str = "1D",
    evaluation_start_index: int | None = None,
    signal_input: str = "CLOSES",
) -> dict[str, Any]:
    safety_contract = {
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    numeric_issues = numeric_parameter_contract_issues(
        {
            "position_pct": position_pct,
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "startup_candles": startup_candles,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "leverage": leverage,
            "initial_cash": initial_cash,
            "evaluation_start_index": evaluation_start_index,
        },
        positive=("initial_cash", "position_pct", "leverage"),
        integer=("startup_candles", "evaluation_start_index"),
        minimum={
            "take_profit_pct": 0.0,
            "stop_loss_pct": 0.0,
            "startup_candles": 2.0,
            "fee_rate": 0.0,
            "slippage_bps": 0.0,
            "evaluation_start_index": 0.0,
        },
        maximum={
            "position_pct": 100.0,
            "take_profit_pct": 1000.0,
            "stop_loss_pct": 100.0,
            "fee_rate": 0.02,
            "slippage_bps": 500.0,
        },
    )
    if numeric_issues:
        return {
            "ok": False,
            "error": "Backtest numeric parameter contract failed: " + ", ".join(numeric_issues),
            "symbol": symbol,
            "source": source,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }
    clean_position_pct = float(position_pct)
    clean_take_profit_pct = float(take_profit_pct)
    clean_stop_loss_pct = float(stop_loss_pct)
    clean_fee_rate = float(fee_rate)
    clean_slippage_bps = float(slippage_bps)
    clean_leverage = float(leverage)
    clean_initial_cash = float(initial_cash)
    startup = max(int(float(startup_candles)), 2)
    prepared = prepare_backtest_dataset(
        rows,
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        minimum_rows=startup + 2,
        market=market,
    )
    manifest = prepared["manifest"]
    clean_rows = prepared["rows"]
    if manifest["status"] != "PASS":
        return {
            "ok": False,
            "error": "回测数据完整性门槛未通过",
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }
    if abs(clean_leverage - 1.0) > 1e-9:
        return {
            "ok": False,
            "error": "当前因果回测内核仅支持 1 倍现金账户；杠杆需等待保证金与强平模型。",
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }

    if len(clean_rows) <= startup + 1:
        return {
            "ok": False,
            "error": f"有效样本 {len(clean_rows)} 根，无法覆盖 {startup} 根预热和下一根成交",
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }

    costs = BacktestCosts(
        fee_rate=clean_fee_rate,
        slippage_bps=clean_slippage_bps,
    )
    allocation = clean_position_pct / 100.0
    cash = clean_initial_cash
    quantity = 0.0
    entry_price = 0.0
    cost_basis = 0.0
    last_scale_price = 0.0
    total_fees = 0.0
    turnover = 0.0
    closed_wins = 0
    closed_losses = 0
    ambiguous_intrabar_count = 0
    exposure_bars = 0
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []
    raw_equity_values: list[float] = [clean_initial_cash]
    closes = [float(row["close"]) for row in clean_rows]
    clean_signal_input = str(signal_input or "CLOSES").upper()
    if clean_signal_input not in {"CLOSES", "BARS"}:
        return {
            "ok": False,
            "error": f"Unsupported signal input mode: {clean_signal_input}",
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }

    def signal_history(end_index: int) -> list[Any]:
        if clean_signal_input == "BARS":
            return [dict(row) for row in clean_rows[:end_index + 1]]
        return closes[:end_index + 1]

    def signal_failure(error: str, signal_date: str) -> dict[str, Any]:
        return {
            "ok": False,
            "error": f"Strategy signal contract failed: {error}",
            "signal_date": signal_date,
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            "partial_order_events": list(trades),
            **safety_contract,
        }

    def execute_entry(action: str, signal: dict[str, Any], row: dict[str, Any]) -> None:
        nonlocal cash, quantity, entry_price, cost_basis, last_scale_price, total_fees, turnover
        if (
            cash <= 1e-12
            or (action == "BUY" and quantity > 0)
            or (action == "ADD" and quantity <= 0)
        ):
            return
        equity_open = cash + quantity * float(row["open"])
        current_notional = quantity * float(row["open"])
        remaining_target = max(equity_open * allocation - current_notional, 0.0)
        budget = min(cash * (0.45 if action == "ADD" else 1.0), remaining_target)
        if budget <= 1e-12:
            return
        execution_price = float(row["open"]) * (1 + costs.slippage_rate)
        notional = budget / (1 + costs.fee_rate)
        fee = notional * costs.fee_rate
        filled_quantity = notional / execution_price
        old_notional = entry_price * quantity
        quantity += filled_quantity
        entry_price = (old_notional + execution_price * filled_quantity) / max(quantity, 1e-12)
        cost_basis += notional + fee
        cash -= notional + fee
        last_scale_price = execution_price
        total_fees += fee
        turnover += notional
        trades.append({
            "signal_date": signal.get("signal_date", ""),
            "date": row["date"],
            "side": action,
            "price": round(execution_price, 6),
            "quantity": round(filled_quantity, 10),
            "fee": round(fee, 6),
            "reason": signal.get("reason", ""),
            "fill_basis": "NEXT_BAR_OPEN",
        })

    def execute_exit(reason: str, row: dict[str, Any], raw_price: float, fill_basis: str, signal_date: str = "") -> None:
        nonlocal cash, quantity, entry_price, cost_basis, last_scale_price, total_fees, turnover, closed_wins, closed_losses
        if quantity <= 0:
            return
        execution_price = max(float(raw_price) * (1 - costs.slippage_rate), 1e-12)
        notional = quantity * execution_price
        fee = notional * costs.fee_rate
        net_proceeds = notional - fee
        pnl = net_proceeds - cost_basis
        cash += net_proceeds
        total_fees += fee
        turnover += notional
        closed_wins += int(pnl > 0)
        closed_losses += int(pnl <= 0)
        trades.append({
            "signal_date": signal_date,
            "date": row["date"],
            "side": "SELL",
            "price": round(execution_price, 6),
            "quantity": round(quantity, 10),
            "fee": round(fee, 6),
            "pnl": round(pnl, 2),
            "reason": reason,
            "fill_basis": fill_basis,
        })
        quantity = 0.0
        entry_price = 0.0
        cost_basis = 0.0
        last_scale_price = 0.0

    evaluation_start = startup if evaluation_start_index is None else max(startup, int(float(evaluation_start_index)))
    if evaluation_start >= len(clean_rows):
        return {
            "ok": False,
            "error": "Evaluation window starts after the available dataset.",
            "symbol": symbol,
            "source": source,
            "dataset_manifest": manifest,
            "execution_model": EXECUTION_MODEL_VERSION,
            **safety_contract,
        }

    signal_index = evaluation_start - 1
    initial_signal, initial_error = _invoke_signal(
        signal_fn,
        signal_history(signal_index),
        closes[signal_index],
        False,
        0.0,
        0.0,
    )
    if initial_error:
        return signal_failure(initial_error, clean_rows[signal_index]["date"])
    pending_signal: dict[str, Any] = {
        **dict(initial_signal or {}),
        "signal_date": clean_rows[signal_index]["date"],
    }

    for index in range(evaluation_start, len(clean_rows)):
        row = clean_rows[index]
        open_price = float(row["open"])
        action = str(pending_signal.get("action") or "HOLD").upper()
        if action in {"SELL", "EXIT"}:
            execute_exit(str(pending_signal.get("reason") or "策略退出"), row, open_price, "NEXT_BAR_OPEN", str(pending_signal.get("signal_date") or ""))
        elif action in {"BUY", "ADD"}:
            execute_entry(action, pending_signal, row)

        if quantity > 0:
            stop_price = entry_price * (1 - clean_stop_loss_pct / 100.0) if clean_stop_loss_pct > 0 else 0.0
            target_price = entry_price * (1 + clean_take_profit_pct / 100.0) if clean_take_profit_pct > 0 else 0.0
            stop_hit = bool(stop_price and (open_price <= stop_price or float(row["low"]) <= stop_price))
            target_hit = bool(target_price and (open_price >= target_price or float(row["high"]) >= target_price))
            if stop_hit and target_hit:
                ambiguous_intrabar_count += 1
            if stop_hit:
                raw_exit = open_price if open_price <= stop_price else stop_price
                execute_exit("固定止损", row, raw_exit, "GAP_OPEN" if open_price <= stop_price else "INTRABAR_STOP")
            elif target_hit:
                execute_exit("固定止盈", row, target_price, "INTRABAR_TARGET")

        mark_equity = cash + quantity * float(row["close"])
        raw_equity_values.append(mark_equity)
        exposure_bars += int(quantity > 0)
        equity_curve.append({"date": row["date"], "ts_ms": row["ts_ms"], "equity": round(mark_equity, 2)})
        next_signal, next_error = _invoke_signal(
            signal_fn,
            signal_history(index),
            closes[index],
            quantity > 0,
            entry_price,
            last_scale_price,
        )
        if next_error:
            return signal_failure(next_error, row["date"])
        pending_signal = {
            **dict(next_signal or {}),
            "signal_date": row["date"],
        }

    equity_values = raw_equity_values
    final_equity = equity_values[-1] if equity_values else clean_initial_cash
    total_return = final_equity / clean_initial_cash - 1
    elapsed_ms = max(clean_rows[-1]["ts_ms"] - clean_rows[evaluation_start]["ts_ms"], 86_400_000)
    elapsed_years = elapsed_ms / (365.2425 * 86_400_000)
    annualized = (1 + total_return) ** (1 / elapsed_years) - 1 if total_return > -1 and elapsed_years > 0 else -1.0
    closed_count = closed_wins + closed_losses
    periods_per_year = _periods_per_year(market, timeframe)
    pending_action = str(pending_signal.get("action") or "HOLD").upper()
    return {
        "ok": True,
        "symbol": symbol,
        "source": source,
        "data_points": len(clean_rows),
        "dataset_manifest": manifest,
        "execution_model": EXECUTION_MODEL_VERSION,
        "execution_assumptions": {
            "signal_time": "BAR_CLOSE",
            "entry_exit_time": "NEXT_BAR_OPEN",
            "intrabar_priority": "STOP_BEFORE_TARGET",
            "open_position_at_end": "MARK_TO_MARKET",
            "leverage_supported": False,
            "warmup_context_excluded_from_results": evaluation_start > startup,
            "signal_input": clean_signal_input,
            "periods_per_year": periods_per_year,
            "initial_entry_cash_budget_fraction": 1.0,
            "add_cash_budget_fraction": 0.45,
        },
        "evaluation_window": {
            "start_index": evaluation_start,
            "start": clean_rows[evaluation_start]["date"],
            "end": clean_rows[-1]["date"],
            "context_rows": evaluation_start,
            "evaluated_rows": len(clean_rows) - evaluation_start,
        },
        "fee_rate": round(costs.fee_rate, 8),
        "slippage_bps": round(costs.slippage_bps, 4),
        "initial_cash": round(clean_initial_cash, 2),
        "final_cash": round(cash, 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return * 100, 2),
        "annualized_pct": round(annualized * 100, 2),
        "max_drawdown_pct": round(_max_drawdown(equity_values) * 100, 2),
        "win_rate_pct": round(closed_wins / max(closed_count, 1) * 100, 2),
        "sharpe": round(_sharpe(equity_values, periods_per_year), 2),
        "trade_count": closed_count,
        "order_event_count": len(trades),
        "total_fees": round(total_fees, 4),
        "turnover": round(turnover, 2),
        "exposure_pct": round(exposure_bars / max(len(equity_curve), 1) * 100, 2),
        "open_position": {
            "quantity": round(quantity, 10),
            "entry_price": round(entry_price, 6),
            "cost_basis": round(cost_basis, 2),
            "unrealized_pnl": round(quantity * float(clean_rows[-1]["close"]) - cost_basis, 2) if quantity > 0 else 0.0,
        },
        "ambiguous_intrabar_count": ambiguous_intrabar_count,
        "pending_signal_at_end": pending_action if pending_action != "HOLD" else "",
        "trades": trades,
        "equity_curve": equity_curve,
        **safety_contract,
    }


def causal_prefix_invariance_check(
    *,
    rows: list[dict[str, Any]],
    symbol: str,
    source: str,
    signal_factory: SignalFactory,
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    startup_candles: int,
    fee_rate: float = 0.0005,
    slippage_bps: float = 0.0,
    leverage: float = 1.0,
    initial_cash: float = 10_000.0,
    market: str = "crypto",
    timeframe: str = "1D",
    signal_input: str = "CLOSES",
    checkpoint_ratios: tuple[float, ...] = (0.35, 0.6, 0.8),
) -> dict[str, Any]:
    numeric_issues = numeric_parameter_contract_issues(
        {
            "position_pct": position_pct,
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "startup_candles": startup_candles,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "leverage": leverage,
            "initial_cash": initial_cash,
        },
        positive=("position_pct", "leverage", "initial_cash"),
        integer=("startup_candles",),
        minimum={
            "take_profit_pct": 0.0,
            "stop_loss_pct": 0.0,
            "startup_candles": 2.0,
            "fee_rate": 0.0,
            "slippage_bps": 0.0,
        },
        maximum={
            "position_pct": 100.0,
            "take_profit_pct": 1000.0,
            "stop_loss_pct": 100.0,
            "fee_rate": 0.02,
            "slippage_bps": 500.0,
        },
    )
    if numeric_issues:
        return {
            "version": CAUSAL_AUDIT_VERSION,
            "status": "BLOCK",
            "checks": [],
            "issues": ["numeric_parameter_contract:" + item for item in numeric_issues],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    startup = int(float(startup_candles))
    prepared = prepare_backtest_dataset(
        rows,
        symbol=symbol,
        source=source,
        timeframe=timeframe,
        minimum_rows=startup + 4,
        market=market,
    )
    manifest = prepared["manifest"]
    clean_rows = list(prepared["rows"])
    if manifest["status"] != "PASS":
        return {
            "version": CAUSAL_AUDIT_VERSION,
            "status": "BLOCK",
            "checks": [],
            "issues": ["dataset_integrity_block"],
            "dataset_manifest": manifest,
        }

    available = len(clean_rows) - startup
    checkpoint_counts = sorted({
        min(len(clean_rows) - 1, startup + max(2, int(available * float(ratio))))
        for ratio in checkpoint_ratios
        if 0 < float(ratio) < 1
    })
    checkpoint_counts = [count for count in checkpoint_counts if startup + 1 < count < len(clean_rows)]
    if not checkpoint_counts:
        return {
            "version": CAUSAL_AUDIT_VERSION,
            "status": "BLOCK",
            "checks": [],
            "issues": ["insufficient_rows_for_prefix_checkpoints"],
            "dataset_manifest": manifest,
        }

    def run(run_rows: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            signal = signal_factory([dict(row) for row in run_rows])
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Strategy signal factory failed: {type(exc).__name__}:{str(exc)[:160]}",
            }
        if not callable(signal):
            return {"ok": False, "error": "Strategy signal factory did not return a callable."}
        return run_causal_long_only_backtest(
            rows=run_rows,
            symbol=symbol,
            source=source,
            signal_fn=signal,
            position_pct=position_pct,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            startup_candles=startup,
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
            leverage=leverage,
            initial_cash=initial_cash,
            market=market,
            timeframe=timeframe,
            signal_input=signal_input,
        )

    full_report = run(clean_rows)
    if not full_report.get("ok"):
        return {
            "version": CAUSAL_AUDIT_VERSION,
            "status": "BLOCK",
            "checks": [],
            "issues": ["full_backtest_not_runnable"],
            "dataset_manifest": manifest,
        }

    full_curve = list(full_report.get("equity_curve") or [])
    full_trades = list(full_report.get("trades") or [])
    checks: list[dict[str, Any]] = []
    issues: list[str] = []
    for count in checkpoint_counts:
        prefix_rows = clean_rows[:count]
        closes = [float(row["close"]) for row in prefix_rows]
        price = closes[-1]
        entry_price = price * 0.97
        state_results: list[dict[str, Any]] = []
        for state_name, has_position, entry, last_scale in (
            ("flat", False, 0.0, 0.0),
            ("positioned", True, entry_price, entry_price),
        ):
            if str(signal_input or "CLOSES").upper() == "BARS":
                full_input = [dict(row) for row in prefix_rows]
                prefix_input = [dict(row) for row in prefix_rows]
                repeated_input = [dict(row) for row in prefix_rows]
            else:
                full_input = list(closes)
                prefix_input = list(closes)
                repeated_input = list(closes)
            input_hash = _canonical_hash(full_input)
            try:
                full_fn = signal_factory([dict(row) for row in clean_rows])
                prefix_fn = signal_factory([dict(row) for row in prefix_rows])
                repeated_fn = signal_factory([dict(row) for row in clean_rows])
            except Exception as exc:
                issues.append(f"signal_factory_exception:{count}:{state_name}:{type(exc).__name__}")
                state_results.append({
                    "state": state_name,
                    "context_match": False,
                    "deterministic": False,
                    "input_unchanged": True,
                })
                continue
            if not all(callable(item) for item in (full_fn, prefix_fn, repeated_fn)):
                issues.append(f"signal_factory_not_callable:{count}:{state_name}")
                state_results.append({
                    "state": state_name,
                    "context_match": False,
                    "deterministic": False,
                    "input_unchanged": True,
                })
                continue
            full_signal, full_error = _invoke_signal(full_fn, full_input, price, has_position, entry, last_scale)
            prefix_signal, prefix_error = _invoke_signal(prefix_fn, prefix_input, price, has_position, entry, last_scale)
            repeated_signal, repeated_error = _invoke_signal(repeated_fn, repeated_input, price, has_position, entry, last_scale)
            signal_errors = [error for error in (full_error, prefix_error, repeated_error) if error]
            if signal_errors:
                issues.extend(f"signal_contract:{count}:{state_name}:{error}" for error in signal_errors)
            context_match = _canonical_hash(full_signal) == _canonical_hash(prefix_signal)
            deterministic = _canonical_hash(full_signal) == _canonical_hash(repeated_signal)
            input_unchanged = all(_canonical_hash(item) == input_hash for item in (full_input, prefix_input, repeated_input))
            state_results.append({
                "state": state_name,
                "context_match": context_match,
                "deterministic": deterministic,
                "input_unchanged": input_unchanged,
            })
            if not context_match:
                issues.append(f"signal_context_mismatch:{count}:{state_name}")
            if not deterministic:
                issues.append(f"signal_nondeterministic:{count}:{state_name}")
            if not input_unchanged:
                issues.append(f"signal_mutated_history:{count}:{state_name}")

        prefix_report = run(prefix_rows)
        prefix_curve = list(prefix_report.get("equity_curve") or []) if prefix_report.get("ok") else []
        prefix_trades = list(prefix_report.get("trades") or []) if prefix_report.get("ok") else []
        curve_match = bool(prefix_report.get("ok")) and full_curve[:len(prefix_curve)] == prefix_curve
        trade_match = bool(prefix_report.get("ok")) and full_trades[:len(prefix_trades)] == prefix_trades
        if not prefix_report.get("ok"):
            issues.append(f"prefix_backtest_not_runnable:{count}")
        if not curve_match:
            issues.append(f"equity_prefix_mismatch:{count}")
        if not trade_match:
            issues.append(f"trade_prefix_mismatch:{count}")
        checks.append({
            "prefix_rows": count,
            "prefix_end": str(prefix_rows[-1].get("date") or ""),
            "signal_states": state_results,
            "equity_prefix_match": curve_match,
            "trade_prefix_match": trade_match,
            "prefix_run_ok": bool(prefix_report.get("ok")),
        })

    return {
        "version": CAUSAL_AUDIT_VERSION,
        "status": "PASS" if not issues else "BLOCK",
        "checkpoint_count": len(checks),
        "checks": checks,
        "issues": list(dict.fromkeys(issues)),
        "dataset_hash": manifest.get("data_hash", ""),
        "dataset_rows": manifest.get("row_count", 0),
        "signal_input": str(signal_input or "CLOSES").upper(),
    }
