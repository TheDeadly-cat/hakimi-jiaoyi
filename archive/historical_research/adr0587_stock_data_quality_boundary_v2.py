from __future__ import annotations

import math
from types import MappingProxyType
from typing import Any


STOCK_DATA_QUALITY_BOUNDARY_VERSION = "stock-data-quality-boundary-v2"
STOCK_MARKET_DATA_GOVERNANCE_VERSION = "stock-market-data-governance-v1"
OBSERVATION_TIME_CONTRACT_VERSION = "stock-observation-time-v1"
DEFAULT_MAX_FUTURE_SKEW_MS = 5_000
MAX_EPOCH_MS = 253_402_300_799_000
SAFE_ACTION = "SOURCE -> GAP -> MATURITY -> PERMISSION"
AUTHORITY_LOCK = MappingProxyType({
    "parameter_selection": False,
    "ranking": False,
    "paper": False,
    "live": False,
    "order": False,
    "profitability_proof": False,
})


def native_finite_number(value: Any) -> float | None:
    if type(value) not in {int, float}:
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def native_epoch_ms(value: Any) -> int | None:
    if type(value) is int:
        parsed = value
    elif type(value) is float and math.isfinite(value) and value.is_integer():
        parsed = int(value)
    else:
        return None
    if parsed <= 0 or parsed > MAX_EPOCH_MS:
        return None
    return parsed


def observation_time_quality(
    observed_at_ms: Any,
    *,
    now_ms: Any,
    max_age_ms: int,
    max_future_skew_ms: int = DEFAULT_MAX_FUTURE_SKEW_MS,
) -> dict[str, Any]:
    clean_max_age = max_age_ms if type(max_age_ms) is int and max_age_ms >= 0 else 0
    clean_future_skew = (
        max_future_skew_ms
        if type(max_future_skew_ms) is int and max_future_skew_ms >= 0
        else DEFAULT_MAX_FUTURE_SKEW_MS
    )
    observed = native_epoch_ms(observed_at_ms)
    now_value = native_epoch_ms(now_ms)
    age_ms: int | None = None
    future_offset_ms = 0
    if observed is None:
        missing = observed_at_ms is None or (
            type(observed_at_ms) in {int, float} and float(observed_at_ms) == 0.0
        )
        status = "MISSING_TIMESTAMP" if missing else "INVALID_TIMESTAMP"
    elif now_value is None:
        status = "INVALID_NOW"
    else:
        delta = now_value - observed
        if delta < -clean_future_skew:
            status = "FUTURE_TIMESTAMP"
            future_offset_ms = -delta
        else:
            age_ms = max(0, delta)
            future_offset_ms = max(0, -delta)
            status = "STALE" if age_ms > clean_max_age else "CURRENT"
    timestamp_valid = status in {"CURRENT", "STALE"}
    return {
        "contract_version": OBSERVATION_TIME_CONTRACT_VERSION,
        "quality_boundary_version": STOCK_DATA_QUALITY_BOUNDARY_VERSION,
        "status": status,
        "observed_at_ms": observed,
        "now_ms": now_value,
        "age_ms": age_ms,
        "future_offset_ms": future_offset_ms,
        "max_age_ms": clean_max_age,
        "max_future_skew_ms": clean_future_skew,
        "timestamp_valid": timestamp_valid,
        "current": status == "CURRENT",
        "stale": status == "STALE",
        "future": status == "FUTURE_TIMESTAMP",
        "authority": dict(AUTHORITY_LOCK),
        "safe_action": SAFE_ACTION,
    }


__all__ = [
    "AUTHORITY_LOCK",
    "DEFAULT_MAX_FUTURE_SKEW_MS",
    "MAX_EPOCH_MS",
    "OBSERVATION_TIME_CONTRACT_VERSION",
    "SAFE_ACTION",
    "STOCK_DATA_QUALITY_BOUNDARY_VERSION",
    "native_epoch_ms",
    "native_finite_number",
    "observation_time_quality",
]
