from __future__ import annotations

from typing import Any


CANDLE_COMPLETENESS_CONTRACT_VERSION = "candle-completeness-v1"

_TRUE_VALUES = frozenset({"1", "true", "yes", "complete", "completed", "confirmed", "closed", "final"})
_FALSE_VALUES = frozenset({"0", "false", "no", "incomplete", "partial", "provisional", "open"})


def explicit_boolean(value: Any) -> bool | None:
    if type(value) is bool:
        return value
    if type(value) is int and value in {0, 1}:
        return value == 1
    if type(value) is str:
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return None


def candle_is_complete(row: dict[str, Any], *, default_if_missing: bool = False) -> bool:
    if type(row) is not dict or type(default_if_missing) is not bool:
        return False
    for field in ("complete", "confirm", "confirmed"):
        if field in row:
            return explicit_boolean(row.get(field)) is True
    if "provisional" in row:
        return explicit_boolean(row.get("provisional")) is False
    return default_if_missing


__all__ = [
    "CANDLE_COMPLETENESS_CONTRACT_VERSION",
    "candle_is_complete",
    "explicit_boolean",
]
