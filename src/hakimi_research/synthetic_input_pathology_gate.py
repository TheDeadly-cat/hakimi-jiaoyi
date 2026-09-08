"""Pure research gate for deterministic market-input pathology probes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from typing import Any


POLICY_SCHEMA_VERSION = "synthetic-input-pathology-policy-v1"
EVALUATION_SCHEMA_VERSION = "synthetic-input-pathology-evaluation-v1"

_RECORD_KEYS = {"time", "open", "high", "low", "close", "volume"}
_PROBE_KEYS = {"probe_id", "strategy_id", "time", "requested_quantity"}


class SyntheticInputPathologyGateError(ValueError):
    """Raised when an input uses an invalid or ambiguous contract shape."""


def _fail(path: str, message: str) -> None:
    raise SyntheticInputPathologyGateError(f"{path}: {message}")


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "float must be finite")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "dict keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    _fail(path, "value must use exact native JSON types")


def _sha256_json(value: Any) -> str:
    _require_exact_json(value)
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = deepcopy(unsigned)
    result[field] = _sha256_json(unsigned)
    return result


def synthetic_input_pathology_policy_v1() -> dict[str, Any]:
    payload = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "required_record_keys": sorted(_RECORD_KEYS),
        "expected_interval_seconds": 86400,
        "require_timezone_aware": True,
        "require_strictly_increasing_time": True,
        "require_positive_prices": True,
        "require_positive_volume": True,
        "require_ohlc_envelope": True,
        "capacity_model": "BAR_VOLUME_X_MAX_PARTICIPATION",
        "max_participation_rate": "0.01",
        "partial_fill_execution_modelled": False,
        "order_rejection_execution_modelled": False,
        "runtime_mutations": False,
    }
    return _seal(payload, "policy_sha256")


def _parse_time(value: Any, path: str) -> datetime:
    if type(value) is not str or not value:
        _fail(path, "time must be a non-empty exact native string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(path, f"invalid ISO-8601 time:{exc}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "time must be timezone-aware")
    return parsed


def _number(value: Any, path: str) -> Decimal:
    if type(value) not in (int, float):
        _fail(path, "value must be an exact native int or float")
    if type(value) is float and not math.isfinite(value):
        _fail(path, "value must be finite")
    return Decimal(str(value))


def _positive_decimal_text(value: Any, path: str) -> Decimal:
    if type(value) is not str or not value:
        _fail(path, "value must be a non-empty exact native decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        _fail(path, f"invalid decimal:{exc}")
    if not parsed.is_finite() or parsed <= 0:
        _fail(path, "decimal must be finite and positive")
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def evaluate_synthetic_input_pathology_gate_v1(
    records: list[dict[str, Any]],
    policy: dict[str, Any],
    capacity_probes: list[dict[str, Any]],
) -> dict[str, Any]:
    if type(records) is not list or not records:
        _fail("records", "must be a non-empty exact native list")
    if type(policy) is not dict:
        _fail("policy", "must be an exact native dict")
    if type(capacity_probes) is not list:
        _fail("capacity_probes", "must be an exact native list")
    _require_exact_json(records, path="records")
    _require_exact_json(policy, path="policy")
    _require_exact_json(capacity_probes, path="capacity_probes")
    expected_policy = synthetic_input_pathology_policy_v1()
    if policy != expected_policy:
        _fail("policy", "must match the preregistered v1 policy")

    times: list[datetime] = []
    record_by_time: dict[str, dict[str, Any]] = {}
    issue_codes: set[str] = set()
    missing_interval_count = 0
    cadence_violation_count = 0
    ohlc_violation_count = 0
    nonpositive_price_count = 0
    nonpositive_volume_count = 0

    for index, record in enumerate(records):
        path = f"records[{index}]"
        if type(record) is not dict or set(record) != _RECORD_KEYS:
            _fail(path, "record must contain the exact v1 OHLCV key set")
        parsed_time = _parse_time(record["time"], f"{path}.time")
        times.append(parsed_time)
        if record["time"] in record_by_time:
            issue_codes.add("DUPLICATE_TIMESTAMP")
            cadence_violation_count += 1
        record_by_time[record["time"]] = record
        open_price = _number(record["open"], f"{path}.open")
        high_price = _number(record["high"], f"{path}.high")
        low_price = _number(record["low"], f"{path}.low")
        close_price = _number(record["close"], f"{path}.close")
        volume = _number(record["volume"], f"{path}.volume")
        prices = (open_price, high_price, low_price, close_price)
        if any(price <= 0 for price in prices):
            issue_codes.add("NONPOSITIVE_PRICE")
            nonpositive_price_count += 1
        if volume <= 0:
            issue_codes.add("NONPOSITIVE_VOLUME")
            nonpositive_volume_count += 1
        if not (
            low_price <= open_price <= high_price
            and low_price <= close_price <= high_price
            and low_price <= high_price
        ):
            issue_codes.add("OHLC_ENVELOPE_VIOLATION")
            ohlc_violation_count += 1

    expected_seconds = policy["expected_interval_seconds"]
    for previous, current in zip(times, times[1:]):
        delta_seconds = int((current - previous).total_seconds())
        if delta_seconds == expected_seconds:
            continue
        cadence_violation_count += 1
        if delta_seconds > expected_seconds:
            issue_codes.add("MISSING_INTERVAL")
            missing_interval_count += max(1, delta_seconds // expected_seconds - 1)
        else:
            issue_codes.add("NON_INCREASING_OR_SHORT_INTERVAL")

    max_participation = _positive_decimal_text(
        policy["max_participation_rate"],
        "policy.max_participation_rate",
    )
    assessments: list[dict[str, Any]] = []
    seen_probe_ids: set[str] = set()
    insufficient_capacity_count = 0
    for index, probe in enumerate(capacity_probes):
        path = f"capacity_probes[{index}]"
        if type(probe) is not dict or set(probe) != _PROBE_KEYS:
            _fail(path, "probe must contain the exact v1 key set")
        for field in ("probe_id", "strategy_id", "time"):
            if type(probe[field]) is not str or not probe[field]:
                _fail(f"{path}.{field}", "must be a non-empty exact native string")
        if probe["probe_id"] in seen_probe_ids:
            _fail(f"{path}.probe_id", "must be unique")
        seen_probe_ids.add(probe["probe_id"])
        _parse_time(probe["time"], f"{path}.time")
        if probe["time"] not in record_by_time:
            _fail(f"{path}.time", "must bind an observed record")
        requested = _positive_decimal_text(
            probe["requested_quantity"], f"{path}.requested_quantity"
        )
        observed_volume = _number(
            record_by_time[probe["time"]]["volume"], f"{path}.observed_volume"
        )
        available = observed_volume * max_participation
        supported = available >= requested
        if not supported:
            insufficient_capacity_count += 1
            issue_codes.add("INSUFFICIENT_STATIC_CAPACITY")
        unfilled = max(Decimal("0"), requested - available)
        assessment = {
            "probe_id": probe["probe_id"],
            "strategy_id": probe["strategy_id"],
            "time": probe["time"],
            "requested_quantity": _decimal_text(requested),
            "observed_volume": _decimal_text(observed_volume),
            "max_participation_rate": _decimal_text(max_participation),
            "available_quantity_upper_bound": _decimal_text(available),
            "uncovered_quantity": _decimal_text(unfilled),
            "capacity_ratio": _decimal_text(available / requested),
            "capacity_supported": supported,
            "partial_fill_created": False,
            "order_rejection_created": False,
        }
        assessments.append(_seal(assessment, "assessment_sha256"))

    data_issue_codes = {
        "DUPLICATE_TIMESTAMP",
        "MISSING_INTERVAL",
        "NON_INCREASING_OR_SHORT_INTERVAL",
        "NONPOSITIVE_PRICE",
        "NONPOSITIVE_VOLUME",
        "OHLC_ENVELOPE_VIOLATION",
    }
    data_accepted = not bool(issue_codes.intersection(data_issue_codes))
    capacity_accepted = insufficient_capacity_count == 0
    payload = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "policy_sha256": policy["policy_sha256"],
        "records_sha256": _sha256_json(records),
        "record_count": len(records),
        "start_time": records[0]["time"],
        "end_time": records[-1]["time"],
        "expected_interval_seconds": expected_seconds,
        "data_accepted": data_accepted,
        "capacity_accepted": capacity_accepted,
        "accepted": data_accepted and capacity_accepted,
        "issue_codes": sorted(issue_codes),
        "missing_interval_count": missing_interval_count,
        "cadence_violation_count": cadence_violation_count,
        "ohlc_violation_count": ohlc_violation_count,
        "nonpositive_price_count": nonpositive_price_count,
        "nonpositive_volume_count": nonpositive_volume_count,
        "capacity_probe_count": len(capacity_probes),
        "insufficient_capacity_probe_count": insufficient_capacity_count,
        "capacity_assessments": assessments,
        "partial_fill_execution_modelled": False,
        "order_rejection_execution_modelled": False,
        "runtime_mutations": False,
    }
    return _seal(payload, "evaluation_sha256")
