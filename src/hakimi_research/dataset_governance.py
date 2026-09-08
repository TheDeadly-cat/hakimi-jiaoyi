from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Final


SCHEMA_VERSION: Final = "dataset-governance-v1"
DECLARATION_FIELDS: Final = (
    "schema_version",
    "dataset_id",
    "source",
    "time",
    "adjustment",
    "population",
    "limitations",
)
_BOUND_FIELDS: Final = (*DECLARATION_FIELDS, "dataset_binding", "governance_hash")
_SOURCE_FIELDS: Final = (
    "provider_id",
    "source_kind",
    "retrieved_at",
    "source_manifest_sha256",
)
_TIME_FIELDS: Final = (
    "timezone",
    "trading_calendar",
    "bar_timestamp_semantics",
    "session_policy",
)
_ADJUSTMENT_FIELDS: Final = (
    "basis",
    "corporate_action_source",
    "dividend_treatment",
)
_POPULATION_FIELDS: Final = (
    "policy",
    "survivorship_bias_status",
    "delisting_policy",
    "universe_snapshot_sha256",
)
_BINDING_FIELDS: Final = (
    "dataset_hash",
    "market",
    "symbol",
    "timeframe",
    "row_count",
    "start_time",
    "end_time",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_KINDS = {
    "SYNTHETIC_FIXTURE",
    "AUTHORITATIVE_MARKET_DATA",
    "LICENSED_MARKET_DATA",
    "PUBLIC_MARKET_DATA",
}
_ADJUSTMENT_BASES = {
    "UNADJUSTED",
    "SPLIT_ADJUSTED",
    "TOTAL_RETURN_ADJUSTED",
    "NOT_APPLICABLE",
}
_POPULATION_POLICIES = {
    "POINT_IN_TIME",
    "SINGLE_INSTRUMENT_WITH_DELISTING_POLICY",
    "SYNTHETIC_FIXED_SINGLE_INSTRUMENT",
}
_SURVIVORSHIP_STATUSES = {"MITIGATED", "NOT_APPLICABLE"}


def _fail(code: str) -> None:
    raise ValueError(f"dataset_governance_{code}")


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


def _record(
    value: Any,
    expected_fields: tuple[str, ...],
    *,
    field: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{field}_exact_dict_required")
    for key in value:
        if type(key) is not str:
            _fail(f"{field}_key_type")
    if set(value) != set(expected_fields):
        _fail(f"{field}_fields_invalid")
    return value


def _text(record: dict[str, Any], key: str, *, field: str) -> str:
    value = record.get(key)
    if type(value) is not str or not value or value != value.strip():
        _fail(f"{field}_{key}_exact_text_required")
    return value


def _sha256(value: Any, *, field: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{field}_sha256_invalid")
    return value


def canonical_dataset_governance_hash(value: Any) -> str:
    _require_native_json(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_retrieved_at(value: str) -> None:
    if not value.endswith("Z"):
        _fail("source_retrieved_at_utc_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("dataset_governance_source_retrieved_at_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        _fail("source_retrieved_at_utc_required")


def bind_dataset_governance(
    declaration: Any,
    *,
    dataset_hash: str,
    market: str,
    symbol: str,
    timeframe: str,
    row_count: int,
    start_time: str,
    end_time: str,
    dataset_timezone: str,
) -> dict[str, Any]:
    declaration_record = _record(
        declaration,
        DECLARATION_FIELDS,
        field="declaration",
    )
    _require_native_json(declaration_record, path="declaration")
    if declaration_record["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version_invalid")
    _text(declaration_record, "dataset_id", field="declaration")

    source = _record(
        declaration_record["source"],
        _SOURCE_FIELDS,
        field="source",
    )
    provider_id = _text(source, "provider_id", field="source")
    source_kind = _text(source, "source_kind", field="source")
    retrieved_at = _text(source, "retrieved_at", field="source")
    _validate_retrieved_at(retrieved_at)
    _sha256(source["source_manifest_sha256"], field="source_manifest")
    if source_kind not in _SOURCE_KINDS:
        _fail("source_kind_invalid")

    time_contract = _record(
        declaration_record["time"],
        _TIME_FIELDS,
        field="time",
    )
    declared_timezone = _text(time_contract, "timezone", field="time")
    _text(time_contract, "trading_calendar", field="time")
    _text(time_contract, "bar_timestamp_semantics", field="time")
    _text(time_contract, "session_policy", field="time")
    if type(dataset_timezone) is not str or declared_timezone != dataset_timezone:
        _fail("time_timezone_dataset_mismatch")

    adjustment = _record(
        declaration_record["adjustment"],
        _ADJUSTMENT_FIELDS,
        field="adjustment",
    )
    adjustment_basis = _text(adjustment, "basis", field="adjustment")
    corporate_action_source = _text(
        adjustment,
        "corporate_action_source",
        field="adjustment",
    )
    dividend_treatment = _text(
        adjustment,
        "dividend_treatment",
        field="adjustment",
    )
    if adjustment_basis not in _ADJUSTMENT_BASES:
        _fail("adjustment_basis_invalid")

    population = _record(
        declaration_record["population"],
        _POPULATION_FIELDS,
        field="population",
    )
    population_policy = _text(population, "policy", field="population")
    survivorship_status = _text(
        population,
        "survivorship_bias_status",
        field="population",
    )
    delisting_policy = _text(
        population,
        "delisting_policy",
        field="population",
    )
    universe_hash = _sha256(
        population["universe_snapshot_sha256"],
        field="population_universe_snapshot",
    )
    if population_policy not in _POPULATION_POLICIES:
        _fail("population_policy_invalid")
    if survivorship_status not in _SURVIVORSHIP_STATUSES:
        _fail("population_survivorship_status_invalid")

    limitations = declaration_record["limitations"]
    if (
        type(limitations) is not list
        or not limitations
        or any(type(item) is not str or not item or item != item.strip() for item in limitations)
        or limitations != sorted(set(limitations))
    ):
        _fail("limitations_invalid")

    facts = {
        "dataset_hash": _sha256(dataset_hash, field="dataset"),
        "market": market,
        "symbol": symbol,
        "timeframe": timeframe,
        "row_count": row_count,
        "start_time": start_time,
        "end_time": end_time,
    }
    _record(facts, _BINDING_FIELDS, field="dataset_binding")
    for key in ("market", "symbol", "timeframe", "start_time", "end_time"):
        _text(facts, key, field="dataset_binding")
    if type(row_count) is not int or type(row_count) is bool or row_count <= 0:
        _fail("dataset_binding_row_count_invalid")

    if source_kind == "SYNTHETIC_FIXTURE":
        if provider_id == "UNKNOWN":
            _fail("synthetic_provider_unknown")
        if adjustment_basis != "NOT_APPLICABLE":
            _fail("synthetic_adjustment_must_be_not_applicable")
        if corporate_action_source != "NOT_APPLICABLE" or dividend_treatment != "NOT_APPLICABLE":
            _fail("synthetic_corporate_action_must_be_not_applicable")
        if population_policy != "SYNTHETIC_FIXED_SINGLE_INSTRUMENT":
            _fail("synthetic_population_policy_invalid")
        if survivorship_status != "NOT_APPLICABLE" or delisting_policy != "NOT_APPLICABLE":
            _fail("synthetic_population_claim_invalid")
        if universe_hash != canonical_dataset_governance_hash([symbol]):
            _fail("synthetic_universe_snapshot_mismatch")
        required_limitations = {"NOT_REAL_MARKET_DATA", "SYNTHETIC_FIXTURE_ONLY"}
        if not required_limitations.issubset(set(limitations)):
            _fail("synthetic_limitations_missing")
    else:
        if market == "synthetic":
            _fail("real_source_cannot_claim_synthetic_market")
        if population_policy == "SYNTHETIC_FIXED_SINGLE_INSTRUMENT":
            _fail("real_source_population_policy_invalid")
        if adjustment_basis == "NOT_APPLICABLE" and market == "stock":
            _fail("stock_adjustment_basis_required")

    core = {
        **deepcopy(declaration_record),
        "dataset_binding": facts,
    }
    return {
        **core,
        "governance_hash": canonical_dataset_governance_hash(core),
    }


def dataset_governance_declaration(value: Any) -> dict[str, Any]:
    bound = _record(value, _BOUND_FIELDS, field="bound")
    _require_native_json(bound, path="bound")
    return {key: deepcopy(bound[key]) for key in DECLARATION_FIELDS}


def verify_dataset_governance(
    value: Any,
    *,
    dataset_hash: str,
    market: str,
    symbol: str,
    timeframe: str,
    row_count: int,
    start_time: str,
    end_time: str,
    dataset_timezone: str,
) -> bool:
    declaration = dataset_governance_declaration(value)
    expected = bind_dataset_governance(
        declaration,
        dataset_hash=dataset_hash,
        market=market,
        symbol=symbol,
        timeframe=timeframe,
        row_count=row_count,
        start_time=start_time,
        end_time=end_time,
        dataset_timezone=dataset_timezone,
    )
    if value != expected:
        _fail("verification_failed")
    return True
