from __future__ import annotations

import math
import time
from typing import Any


def now_ms() -> int:
    return int(time.time() * 1000)


def pct(value: float, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except Exception:
        return default


def clean_json_value(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return clean_json_value(value.item())
        except Exception:
            return str(value)
    return value


def flag(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "on", "checked"}


def choice(value: str | None, allowed: set[str], default: str) -> str:
    text = (value or default).upper()
    return text if text in allowed else default


def average(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def human_age_ms(value: Any) -> str:
    try:
        ms = float(value)
    except Exception:
        return "--"
    if not math.isfinite(ms) or ms <= 0:
        return "--"
    if ms < 60_000:
        return f"{max(1, round(ms / 1000))}秒"
    if ms < 3_600_000:
        return f"{round(ms / 60_000)}分钟"
    if ms < 86_400_000:
        return f"{round(ms / 3_600_000)}小时"
    return f"{round(ms / 86_400_000)}天"


def market_source_name(source: Any) -> str:
    text = str(source or "").lower()
    if text == "futu":
        return "Futu OpenD"
    if text == "stock_sqlite_cache":
        return "本地K线库"
    if text == "offline-seed":
        return "离线种子"
    if text == "yahoo":
        return "Yahoo"
    if text == "stooq":
        return "Stooq"
    if text == "okx":
        return "OKX"
    return str(source or "--")


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def safe_volume_ratio(new_values: list[float], old_values: list[float], default: float = 1.0, cap: float = 8.0) -> float:
    old_clean = [float(value) for value in old_values if float(value or 0) > 0]
    new_clean = [float(value) for value in new_values if float(value or 0) > 0]
    if len(old_clean) < 3 or len(new_clean) < 3:
        return default
    old_avg = average(old_clean)
    new_avg = average(new_clean)
    if old_avg <= 0 or new_avg <= 0:
        return default
    return clamp(new_avg / old_avg, 0.05, cap)


def recent_volatility(candles: list[dict[str, float]], window: int = 20) -> float:
    recent = candles[-window:]
    if len(recent) < 2:
        return 0.02
    changes = []
    for previous, current in zip(recent[:-1], recent[1:]):
        previous_close = max(float(previous["close"]), 1e-9)
        changes.append(abs(float(current["close"]) / previous_close - 1))
    return clamp(average(changes) * 1.8, 0.008, 0.12)


def trend_score(closes: list[float]) -> float:
    if len(closes) < 60:
        return 0.0
    ma20 = average(closes[-20:])
    ma60 = average(closes[-60:])
    long_return = closes[-1] / max(closes[-60], 1e-9) - 1
    return clamp(((ma20 / max(ma60, 1e-9) - 1) * 8) + long_return, -1.0, 1.0)
