from __future__ import annotations

import hashlib
import json
import math
from statistics import fmean, pstdev
from typing import Any

from hakimi_research.candle_contract import candle_is_complete


MARKET_REGIME_SCHEMA_VERSION = "causal-market-regime-v1"
DEFAULT_FAST_WINDOW = 20
DEFAULT_SLOW_WINDOW = 100
DEFAULT_SLOPE_WINDOW = 20
DEFAULT_VOLATILITY_WINDOW = 20
DEFAULT_VOLATILITY_BASELINE = 60
DEFAULT_VOLUME_WINDOW = 20


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _completed(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict) or not _completed(raw):
            continue
        try:
            item = {
                "date": str(raw.get("date") or ""),
                "ts_ms": int(raw.get("ts_ms") or raw.get("ts") or 0),
                "open": float(raw.get("open")),
                "high": float(raw.get("high")),
                "low": float(raw.get("low")),
                "close": float(raw.get("close")),
                "volume": float(raw.get("volume") or 0.0),
                "complete": True,
            }
        except (TypeError, ValueError, OverflowError):
            continue
        prices = [item["open"], item["high"], item["low"], item["close"]]
        if (
            not all(math.isfinite(value) and value > 0 for value in prices)
            or not math.isfinite(item["volume"])
            or item["volume"] < 0
            or item["high"] < max(item["open"], item["close"], item["low"])
            or item["low"] > min(item["open"], item["close"], item["high"])
        ):
            continue
        normalized.append(item)
    normalized.sort(key=lambda item: (item["ts_ms"], item["date"]))
    return normalized


def required_regime_rows(
    *,
    slow_window: int = DEFAULT_SLOW_WINDOW,
    slope_window: int = DEFAULT_SLOPE_WINDOW,
    volatility_baseline: int = DEFAULT_VOLATILITY_BASELINE,
) -> int:
    return max(int(slow_window) + int(slope_window), int(volatility_baseline) + 1)


def classify_market_regime(
    rows: list[dict[str, Any]],
    *,
    as_of_index: int | None = None,
    market: str = "stock",
    fast_window: int = DEFAULT_FAST_WINDOW,
    slow_window: int = DEFAULT_SLOW_WINDOW,
    slope_window: int = DEFAULT_SLOPE_WINDOW,
    volatility_window: int = DEFAULT_VOLATILITY_WINDOW,
    volatility_baseline: int = DEFAULT_VOLATILITY_BASELINE,
    volume_window: int = DEFAULT_VOLUME_WINDOW,
) -> dict[str, Any]:
    raw_rows = list(rows or [])
    if as_of_index is not None:
        raw_rows = raw_rows[:max(int(as_of_index) + 1, 0)]
    values = _normalize_rows(raw_rows)
    fast = max(5, int(fast_window))
    slow = max(fast + 1, int(slow_window))
    slope = max(5, int(slope_window))
    short_vol_window = max(5, int(volatility_window))
    long_vol_window = max(short_vol_window + 1, int(volatility_baseline))
    volume = max(5, int(volume_window))
    required = max(required_regime_rows(slow_window=slow, slope_window=slope, volatility_baseline=long_vol_window), volume + 1)
    if len(values) < required:
        return {
            "schema_version": MARKET_REGIME_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": [f"completed_rows:{len(values)}<{required}"],
            "completed_rows": len(values),
            "required_rows": required,
            "observation_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    closes = [row["close"] for row in values]
    current = values[-1]
    fast_ma = _mean(closes[-fast:])
    slow_ma = _mean(closes[-slow:])
    previous_slow_ma = _mean(closes[-slow - slope:-slope])
    slow_slope_pct = slow_ma / max(previous_slow_ma, 1e-12) - 1.0
    short_return = current["close"] / max(closes[-fast - 1], 1e-12) - 1.0
    medium_return = current["close"] / max(closes[-long_vol_window - 1], 1e-12) - 1.0

    daily_returns = [
        closes[index] / max(closes[index - 1], 1e-12) - 1.0
        for index in range(len(closes) - long_vol_window, len(closes))
    ]
    short_returns = daily_returns[-short_vol_window:]
    short_realized_vol = pstdev(short_returns) if len(short_returns) > 1 else 0.0
    baseline_realized_vol = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    volatility_ratio = short_realized_vol / max(baseline_realized_vol, 1e-12)

    true_ranges: list[float] = []
    for index in range(len(values) - short_vol_window, len(values)):
        row = values[index]
        previous_close = values[index - 1]["close"]
        true_ranges.append(max(
            row["high"] - row["low"],
            abs(row["high"] - previous_close),
            abs(row["low"] - previous_close),
        ))
    atr_pct = _mean(true_ranges) / max(current["close"], 1e-12)

    prior_volumes = [row["volume"] for row in values[-volume - 1:-1]]
    average_volume = _mean(prior_volumes)
    volume_ratio = current["volume"] / average_volume if average_volume > 0 else 0.0

    if current["close"] > slow_ma and fast_ma > slow_ma and slow_slope_pct > 0 and medium_return > 0:
        trend = "UP"
    elif current["close"] < slow_ma and fast_ma < slow_ma and slow_slope_pct < 0 and medium_return < 0:
        trend = "DOWN"
    else:
        trend = "RANGE"

    if volatility_ratio >= 1.25:
        volatility = "EXPANDING"
    elif volatility_ratio <= 0.80:
        volatility = "CONTRACTING"
    else:
        volatility = "NORMAL"

    if volume_ratio >= 1.40:
        participation = "ACTIVE"
    elif volume_ratio <= 0.65:
        participation = "QUIET"
    else:
        participation = "NORMAL"

    if trend == "UP":
        long_only_budget_multiplier = 0.70 if volatility == "EXPANDING" else 1.0
    elif trend == "RANGE":
        long_only_budget_multiplier = 0.20 if volatility == "EXPANDING" else 0.35
    else:
        long_only_budget_multiplier = 0.0
    if participation == "QUIET":
        long_only_budget_multiplier *= 0.75

    annualization = math.sqrt(252 if str(market).lower() == "stock" else 365)
    evidence = {
        "close": round(current["close"], 8),
        "fast_ma": round(fast_ma, 8),
        "slow_ma": round(slow_ma, 8),
        "slow_slope_pct": round(slow_slope_pct * 100.0, 6),
        "short_return_pct": round(short_return * 100.0, 6),
        "medium_return_pct": round(medium_return * 100.0, 6),
        "atr_pct": round(atr_pct * 100.0, 6),
        "short_realized_vol_pct": round(short_realized_vol * annualization * 100.0, 6),
        "baseline_realized_vol_pct": round(baseline_realized_vol * annualization * 100.0, 6),
        "volatility_ratio": round(volatility_ratio, 6),
        "volume_ratio": round(volume_ratio, 6),
    }
    result = {
        "schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "status": "PASS",
        "blockers": [],
        "as_of": current["date"],
        "as_of_ts_ms": current["ts_ms"],
        "completed_rows": len(values),
        "required_rows": required,
        "regime_id": f"{trend}_{volatility}",
        "trend": trend,
        "volatility": volatility,
        "participation": participation,
        "long_only_budget_multiplier": round(long_only_budget_multiplier, 4),
        "evidence": evidence,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["regime_hash"] = _canonical_hash(result)
    return result


def summarize_market_regimes(
    rows: list[dict[str, Any]],
    *,
    start_index: int = 0,
    end_index: int | None = None,
    market: str = "stock",
) -> dict[str, Any]:
    values = _normalize_rows(list(rows or []))
    required = required_regime_rows()
    end = len(values) if end_index is None else min(max(int(end_index), 0), len(values))
    start = max(int(start_index), required - 1, 0)
    observations: list[dict[str, Any]] = []
    for index in range(start, end):
        regime = classify_market_regime(values[:index + 1], market=market)
        if regime.get("status") == "PASS":
            observations.append(regime)
    counts: dict[str, int] = {}
    for item in observations:
        regime_id = str(item.get("regime_id") or "UNKNOWN")
        counts[regime_id] = counts.get(regime_id, 0) + 1
    dominant = max(counts, key=counts.get) if counts else ""
    average_budget = _mean([float(item.get("long_only_budget_multiplier") or 0.0) for item in observations])
    payload = {
        "schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "status": "PASS" if observations else "BLOCK",
        "blockers": [] if observations else ["no_regime_observations"],
        "start_index": start,
        "end_index_exclusive": end,
        "observation_count": len(observations),
        "regime_counts": counts,
        "dominant_regime": dominant,
        "average_long_only_budget_multiplier": round(average_budget, 4),
        "latest": observations[-1] if observations else {},
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["summary_hash"] = _canonical_hash(payload)
    return payload


def audit_market_regime_causality(
    rows: list[dict[str, Any]],
    *,
    market: str = "stock",
    checkpoint_ratios: tuple[float, ...] = (0.50, 0.75, 1.0),
) -> dict[str, Any]:
    values = _normalize_rows(list(rows or []))
    required = required_regime_rows()
    input_hash_before = _canonical_hash(values)
    if len(values) < required:
        return {
            "schema_version": MARKET_REGIME_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": [f"completed_rows:{len(values)}<{required}"],
            "checkpoints": [],
        }
    checkpoints: list[dict[str, Any]] = []
    for ratio in checkpoint_ratios:
        index = min(len(values) - 1, max(required - 1, math.ceil(len(values) * float(ratio)) - 1))
        direct = classify_market_regime(values, as_of_index=index, market=market)
        prefix = classify_market_regime(values[:index + 1], market=market)
        repeated = classify_market_regime(values, as_of_index=index, market=market)
        future_mutated = [dict(row) for row in values]
        for future_index in range(index + 1, len(future_mutated)):
            future_mutated[future_index]["close"] *= 10.0
            future_mutated[future_index]["high"] *= 10.0
            future_mutated[future_index]["low"] *= 10.0
            future_mutated[future_index]["open"] *= 10.0
        mutation_result = classify_market_regime(future_mutated, as_of_index=index, market=market)
        expected_hash = str(prefix.get("regime_hash") or "")
        checks = {
            "prefix_match": str(direct.get("regime_hash") or "") == expected_hash,
            "deterministic": str(repeated.get("regime_hash") or "") == expected_hash,
            "future_invariant": str(mutation_result.get("regime_hash") or "") == expected_hash,
        }
        checkpoints.append({
            "ratio": float(ratio),
            "index": index,
            "as_of": prefix.get("as_of", ""),
            "regime_id": prefix.get("regime_id", ""),
            "checks": checks,
            "passed": all(checks.values()),
        })
    input_unchanged = _canonical_hash(values) == input_hash_before
    passed = input_unchanged and all(item["passed"] for item in checkpoints)
    return {
        "schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": [] if passed else ["market_regime_prefix_invariance_failed"],
        "input_unchanged": input_unchanged,
        "checkpoints": checkpoints,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
