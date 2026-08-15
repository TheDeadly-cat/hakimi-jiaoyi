from __future__ import annotations

from typing import Any


_TRUE_VALUES = frozenset({"1", "true", "yes", "complete", "completed", "confirmed", "closed", "final"})
_FALSE_VALUES = frozenset({"0", "false", "no", "incomplete", "partial", "provisional", "open"})


def explicit_boolean(value: Any) -> bool | None:
    if type(value) is bool:
        return value
    if type(value) is int and value in {0, 1}:
        return value == 1
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return None


def candle_is_complete(row: dict[str, Any], *, default_if_missing: bool = False) -> bool:
    if not isinstance(row, dict):
        return False
    for field in ("complete", "confirm", "confirmed"):
        if field in row:
            return explicit_boolean(row.get(field)) is True
    if "provisional" in row:
        return explicit_boolean(row.get("provisional")) is False
    return default_if_missing is True
