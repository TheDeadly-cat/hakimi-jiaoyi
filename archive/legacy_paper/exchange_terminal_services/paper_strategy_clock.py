from __future__ import annotations

from typing import Any

try:
    from market_data.candle_contract import candle_is_complete
except ModuleNotFoundError:
    from exchange_terminal.market_data.candle_contract import candle_is_complete


PAPER_STRATEGY_CLOCK_VERSION = "completed-bar-first-observed-next-bar-v1"
DEFAULT_MAX_DOWNTIME_MS = 15 * 60 * 1000


def _timestamp_ms(row: dict[str, Any]) -> int:
    for key in ("ts_ms", "ts", "time"):
        value = row.get(key)
        if value not in (None, ""):
            if isinstance(value, bool):
                return 0
            try:
                numeric = int(float(value))
                return numeric * 1000 if 0 < numeric < 10_000_000_000 else numeric
            except (TypeError, ValueError, OverflowError):
                return 0
    return 0


def _is_complete(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def normalize_strategy_bars(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: dict[int, dict[str, Any]] = {}
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        ts_ms = _timestamp_ms(raw)
        try:
            if isinstance(raw.get("close"), bool) or isinstance(raw.get("open"), bool):
                continue
            close = float(raw.get("close") or 0.0)
            open_price = float(raw.get("open") or close)
        except (TypeError, ValueError, OverflowError):
            continue
        if ts_ms <= 0 or close <= 0 or open_price <= 0:
            continue
        normalized[ts_ms] = {
            **raw,
            "ts_ms": ts_ms,
            "open": open_price,
            "close": close,
            "complete": _is_complete(raw),
        }
    return [normalized[key] for key in sorted(normalized)]


def paper_clock_transition(
    *,
    rows: list[dict[str, Any]],
    now_ms: int,
    last_poll_ms: int,
    last_seen_bar_ts: int,
    last_signal_bar_ts: int,
    pending_signal: dict[str, Any] | None,
    execution_ready: bool,
    max_downtime_ms: int = DEFAULT_MAX_DOWNTIME_MS,
) -> dict[str, Any]:
    bars = normalize_strategy_bars(rows)
    complete_bars = [row for row in bars if row["complete"]]
    if not bars or not complete_bars:
        return {
            "status": "DATA_BLOCK",
            "bars": bars,
            "latest_bar_ts": bars[-1]["ts_ms"] if bars else 0,
            "latest_complete_bar": None,
            "pending_expired": False,
            "execution_bar": None,
            "signal_bar": None,
            "missed_signal_bar": None,
        }

    latest_bar = bars[-1]
    latest_complete = complete_bars[-1]
    pending = dict(pending_signal) if isinstance(pending_signal, dict) else {}
    raw_pending_bar_ts = pending.get("signal_bar_ts")
    try:
        pending_bar_ts = 0 if isinstance(raw_pending_bar_ts, bool) else int(raw_pending_bar_ts or 0)
    except (TypeError, ValueError, OverflowError):
        pending_bar_ts = 0
    downtime_ms = max(int(now_ms) - int(last_poll_ms), 0) if last_poll_ms else 0
    pending_expired = bool(pending and last_poll_ms and downtime_ms > max(int(max_downtime_ms), 0))
    execution_bar = None
    if pending and not pending_expired and execution_ready is True:
        execution_bar = next((row for row in bars if int(row["ts_ms"]) > pending_bar_ts), None)

    signal_bar = None
    missed_signal_bar = None
    latest_complete_ts = int(latest_complete["ts_ms"])
    if last_signal_bar_ts <= 0:
        status = "COLD_SYNC"
    elif latest_complete_ts > int(last_signal_bar_ts):
        unseen_complete_bars = [
            row for row in complete_bars
            if int(row["ts_ms"]) > int(last_signal_bar_ts)
        ]
        transition_observed = bool(
            len(unseen_complete_bars) == 1
            and last_poll_ms
            and downtime_ms <= max(int(max_downtime_ms), 0)
            and int(last_seen_bar_ts) > 0
            and latest_complete_ts >= int(last_seen_bar_ts)
        )
        if transition_observed:
            signal_bar = latest_complete
            status = "NEW_COMPLETED_BAR"
        else:
            missed_signal_bar = latest_complete
            status = "MISSED_COMPLETED_BAR"
    elif execution_bar:
        status = "PENDING_EXECUTION_READY"
    elif pending_expired:
        status = "PENDING_EXPIRED"
    else:
        status = "WAITING"

    return {
        "status": status,
        "bars": bars,
        "latest_bar_ts": int(latest_bar["ts_ms"]),
        "latest_complete_bar": latest_complete,
        "pending_expired": pending_expired,
        "downtime_ms": downtime_ms,
        "execution_bar": execution_bar,
        "signal_bar": signal_bar,
        "missed_signal_bar": missed_signal_bar,
    }
