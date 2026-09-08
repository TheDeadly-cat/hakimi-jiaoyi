from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Final

import pandas as pd


SCHEMA_VERSION: Final = "dataset-calendar-conformance-v1"
_TIME_FIELDS: Final = (
    "timezone",
    "trading_calendar",
    "bar_timestamp_semantics",
    "session_policy",
)


def _fail(code: str) -> None:
    raise ValueError(f"dataset_calendar_conformance_{code}")


def _require_native_json(value: Any, *, path: str = "root") -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"{path}_nonfinite")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_native_json(item, path=f"{path}_{index}")
        return
    if type(value) is dict:
        for key in value:
            if type(key) is not str:
                _fail(f"{path}_key_type")
        for key, item in value.items():
            _require_native_json(item, path=f"{path}_{key}")
        return
    _fail(f"{path}_native_json_required")


def _time_contract(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("time_contract_exact_dict_required")
    for key in value:
        if type(key) is not str:
            _fail("time_contract_key_type")
    if set(value) != set(_TIME_FIELDS):
        _fail("time_contract_fields_invalid")
    _require_native_json(value, path="time_contract")
    for key in _TIME_FIELDS:
        item = value[key]
        if type(item) is not str or not item or item != item.strip():
            _fail(f"time_contract_{key}_exact_text_required")
    return value


def _canonical_hash(value: Any) -> str:
    _require_native_json(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _timestamps(index: Any) -> tuple[pd.DatetimeIndex, list[str]]:
    if type(index) is not pd.DatetimeIndex:
        _fail("index_exact_datetime_index_required")
    if (
        index.empty
        or index.tz is None
        or index.hasnans
        or not index.is_monotonic_increasing
        or not index.is_unique
    ):
        _fail("index_invalid")
    return index, [pd.Timestamp(item).isoformat() for item in index]


def build_dataset_calendar_conformance(
    index: Any,
    *,
    time_contract: Any,
    timeframe: str,
    source_kind: str,
) -> dict[str, Any]:
    native_index, observed = _timestamps(index)
    contract = _time_contract(time_contract)
    if type(timeframe) is not str or not timeframe or timeframe != timeframe.strip():
        _fail("timeframe_exact_text_required")
    if type(source_kind) is not str or not source_kind or source_kind != source_kind.strip():
        _fail("source_kind_exact_text_required")

    blockers: list[str] = []
    expected: list[str] = []
    provider = "EXTERNAL_SCHEDULE_ATTESTATION_REQUIRED"
    provider_version = "UNAVAILABLE"
    synthetic_daily = (
        source_kind == "SYNTHETIC_FIXTURE"
        and contract["trading_calendar"] == "SYNTHETIC_DAILY"
        and contract["session_policy"] == "SYNTHETIC_FIXED_DAILY"
        and contract["bar_timestamp_semantics"] == "PERIOD_END"
        and contract["timezone"] == "UTC"
        and timeframe.lower() == "1d"
        and str(native_index.tz) == "UTC"
    )
    if synthetic_daily:
        provider = "DETERMINISTIC_SYNTHETIC_DAILY"
        provider_version = "1"
        cursor = pd.Timestamp(native_index[0])
        end = pd.Timestamp(native_index[-1])
        while cursor <= end:
            expected.append(cursor.isoformat())
            cursor += pd.Timedelta(days=1)
    else:
        blockers.append("EXTERNAL_SCHEDULE_ATTESTATION_REQUIRED")

    expected_set = set(expected)
    observed_set = set(observed)
    missing = sorted(expected_set.difference(observed_set))
    unexpected = sorted(observed_set.difference(expected_set)) if expected else []
    if missing:
        blockers.append(f"CALENDAR_TIMESTAMPS_MISSING:{len(missing)}")
    if unexpected:
        blockers.append(f"NON_CALENDAR_TIMESTAMPS_PRESENT:{len(unexpected)}")
    if expected and len(expected) != len(observed) and not (missing or unexpected):
        blockers.append("CALENDAR_OBSERVATION_COUNT_MISMATCH")

    core = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "calendar_name": contract["trading_calendar"],
        "provider": provider,
        "provider_version": provider_version,
        "timezone": contract["timezone"],
        "timeframe": timeframe,
        "bar_timestamp_semantics": contract["bar_timestamp_semantics"],
        "session_policy": contract["session_policy"],
        "start_time": observed[0],
        "end_time": observed[-1],
        "observed_count": len(observed),
        "expected_count": len(expected),
        "missing_timestamps": missing,
        "unexpected_timestamps": unexpected,
        "observed_schedule_hash": _canonical_hash(observed),
        "expected_schedule_hash": _canonical_hash(expected),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {
        **core,
        "conformance_hash": _canonical_hash(core),
    }


def verify_dataset_calendar_conformance(
    value: Any,
    index: Any,
    *,
    time_contract: Any,
    timeframe: str,
    source_kind: str,
) -> bool:
    _require_native_json(value, path="conformance")
    if type(value) is not dict:
        _fail("value_exact_dict_required")
    expected = build_dataset_calendar_conformance(
        index,
        time_contract=time_contract,
        timeframe=timeframe,
        source_kind=source_kind,
    )
    if value != expected:
        _fail("verification_failed")
    return True
