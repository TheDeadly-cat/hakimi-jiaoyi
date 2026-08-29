from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def strict_native_true(value: Any) -> bool:
    return type(value) is bool and value is True


def strict_native_false(value: Any) -> bool:
    return type(value) is bool and value is False


def strict_nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def strict_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def strict_iso_date(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def strict_utc_second_timestamp(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ) == value
    except ValueError:
        return False


def strict_date_before(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        strict_iso_date(value)
        and strict_iso_date(evidence_cutoff_date)
        and value < evidence_cutoff_date
    )


def strict_timestamp_date_before(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        strict_utc_second_timestamp(value)
        and strict_iso_date(evidence_cutoff_date)
        and value[:10] < evidence_cutoff_date
    )


def strict_locked_fields(document: Any, fields: Any) -> bool:
    if not isinstance(document, dict) or type(fields) not in (list, tuple):
        return False
    if not fields or not all(type(field) is str and bool(field) for field in fields):
        return False
    if len(set(fields)) != len(fields):
        return False
    return all(strict_native_false(document.get(field)) for field in fields)


__all__ = [
    "strict_native_true",
    "strict_native_false",
    "strict_nonempty_string",
    "strict_sha256",
    "strict_iso_date",
    "strict_utc_second_timestamp",
    "strict_date_before",
    "strict_timestamp_date_before",
    "strict_locked_fields",
]
