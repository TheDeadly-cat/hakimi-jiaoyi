from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any


MARKET_CALENDAR_SCHEMA_VERSION = "exchange-session-calendar-v2"
MARKET_SCHEDULE_ATTESTATION_VERSION = "market-schedule-attestation-v1"
TEST_CALENDAR_NAME = "WEEKDAY_FIXTURE"
SESSION_FIELDS = {"date", "open_utc", "close_utc", "early_close"}
SOURCE_CLASSES = {
    "DETERMINISTIC_TEST_FIXTURE",
    "THIRD_PARTY_LIBRARY",
    "OFFICIAL_EXCHANGE_DOCUMENT",
}
AUTHORITY_LOCK = MappingProxyType({
    "parameter_selection": False,
    "ranking": False,
    "paper": False,
    "live": False,
    "order": False,
    "profitability_proof": False,
})


def _require_native_json(value: Any, *, path: str = "root") -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"market_calendar_nonfinite:{path}")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_native_json(item, path=f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"market_calendar_key_type:{path}")
            _require_native_json(item, path=f"{path}.{key}")
        return
    raise ValueError(f"market_calendar_native_json_required:{path}")


def canonical_market_calendar_hash(value: Any) -> str:
    _require_native_json(value)
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _clean_text(value: Any, *, upper: bool = False, lower: bool = False) -> str:
    if type(value) is not str or not value or value != value.strip():
        return ""
    if upper:
        return value.upper()
    if lower:
        return value.lower()
    return value


def _valid_date(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return ""


def _utc_timestamp(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return ""
    return parsed.astimezone(timezone.utc).isoformat()


def _normalize_sessions(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise ValueError("market_calendar_sessions_exact_list_required")
    sessions: list[dict[str, Any]] = []
    previous_date = ""
    for index, raw in enumerate(value):
        if type(raw) is not dict or set(raw) != SESSION_FIELDS:
            raise ValueError(f"market_calendar_session_shape:{index}")
        session_date = _valid_date(raw["date"])
        open_utc = _utc_timestamp(raw["open_utc"])
        close_utc = _utc_timestamp(raw["close_utc"])
        early_close = raw["early_close"]
        if (
            not session_date
            or not open_utc
            or not close_utc
            or type(early_close) is not bool
        ):
            raise ValueError(f"market_calendar_session_value:{index}")
        if previous_date and session_date <= previous_date:
            raise ValueError(f"market_calendar_session_order:{index}")
        if datetime.fromisoformat(open_utc) >= datetime.fromisoformat(close_utc):
            raise ValueError(f"market_calendar_session_window:{index}")
        sessions.append({
            "date": session_date,
            "open_utc": open_utc,
            "close_utc": close_utc,
            "early_close": early_close,
        })
        previous_date = session_date
    if not sessions:
        raise ValueError("market_calendar_sessions_empty")
    return sessions


def infer_market_calendar(
    benchmark_symbol: str,
    *,
    source: str = "",
    explicit: str = "",
) -> str:
    if type(explicit) is not str or type(source) is not str or type(benchmark_symbol) is not str:
        return "UNVERIFIED"
    supplied = explicit.strip().upper()
    if supplied:
        return supplied
    clean_source = source.strip().lower()
    if clean_source in {"test", "fixture", "unit_test"} or "test_fixture" in clean_source:
        return TEST_CALENDAR_NAME
    symbol = benchmark_symbol.strip().upper()
    if not symbol:
        return "UNVERIFIED"
    if symbol.startswith("HK."):
        return "XHKG"
    if symbol.startswith(("SH.", "SZ.")):
        return "XSHG"
    return "XNYS"


def build_market_schedule_attestation(
    *,
    calendar_name: str,
    timezone_name: str,
    coverage_start: str,
    coverage_end: str,
    source_class: str,
    source_name: str,
    source_version: str,
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    clean_name = _clean_text(calendar_name, upper=True)
    clean_timezone = _clean_text(timezone_name)
    clean_start = _valid_date(coverage_start)
    clean_end = _valid_date(coverage_end)
    clean_source_class = _clean_text(source_class, upper=True)
    clean_source_name = _clean_text(source_name)
    clean_source_version = _clean_text(source_version)
    if (
        not clean_name
        or not clean_timezone
        or not clean_start
        or not clean_end
        or clean_start > clean_end
        or clean_source_class not in SOURCE_CLASSES
        or not clean_source_name
        or not clean_source_version
    ):
        raise ValueError("market_calendar_attestation_identity_invalid")
    normalized_sessions = _normalize_sessions(sessions)
    if (
        normalized_sessions[0]["date"] < clean_start
        or normalized_sessions[-1]["date"] > clean_end
    ):
        raise ValueError("market_calendar_attestation_coverage_invalid")
    schedule_hash = canonical_market_calendar_hash(normalized_sessions)
    source_artifact_sha256 = canonical_market_calendar_hash({
        "calendar_name": clean_name,
        "source_class": clean_source_class,
        "source_name": clean_source_name,
        "source_version": clean_source_version,
        "coverage_start": clean_start,
        "coverage_end": clean_end,
        "schedule_hash": schedule_hash,
    })
    core = {
        "schema_version": MARKET_SCHEDULE_ATTESTATION_VERSION,
        "calendar_name": clean_name,
        "timezone": clean_timezone,
        "coverage_start": clean_start,
        "coverage_end": clean_end,
        "source_class": clean_source_class,
        "source_name": clean_source_name,
        "source_version": clean_source_version,
        "source_artifact_sha256": source_artifact_sha256,
        "session_count": len(normalized_sessions),
        "sessions": normalized_sessions,
        "schedule_hash": schedule_hash,
        "official_source_claimed": clean_source_class == "OFFICIAL_EXCHANGE_DOCUMENT",
        "official_source_verified": False,
        "external_truth_verified": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return {**core, "attestation_hash": canonical_market_calendar_hash(core)}


def verify_market_schedule_attestation(value: Any) -> bool:
    _require_native_json(value, path="attestation")
    if type(value) is not dict:
        raise ValueError("market_calendar_attestation_exact_dict_required")
    required = {
        "schema_version",
        "calendar_name",
        "timezone",
        "coverage_start",
        "coverage_end",
        "source_class",
        "source_name",
        "source_version",
        "source_artifact_sha256",
        "session_count",
        "sessions",
        "schedule_hash",
        "official_source_claimed",
        "official_source_verified",
        "external_truth_verified",
        "research_only",
        "paper_authorized",
        "live_order_allowed",
        "attestation_hash",
    }
    if set(value) != required or value.get("schema_version") != MARKET_SCHEDULE_ATTESTATION_VERSION:
        raise ValueError("market_calendar_attestation_shape_invalid")
    sessions = _normalize_sessions(value["sessions"])
    identity_valid = (
        _clean_text(value["calendar_name"], upper=True) == value["calendar_name"]
        and bool(_clean_text(value["timezone"]))
        and _valid_date(value["coverage_start"]) == value["coverage_start"]
        and _valid_date(value["coverage_end"]) == value["coverage_end"]
        and value["coverage_start"] <= value["coverage_end"]
        and value["source_class"] in SOURCE_CLASSES
        and bool(_clean_text(value["source_name"]))
        and bool(_clean_text(value["source_version"]))
        and sessions[0]["date"] >= value["coverage_start"]
        and sessions[-1]["date"] <= value["coverage_end"]
    )
    if not identity_valid:
        raise ValueError("market_calendar_attestation_identity_invalid")
    core = {key: item for key, item in value.items() if key != "attestation_hash"}
    expected_source_hash = canonical_market_calendar_hash({
        "calendar_name": value["calendar_name"],
        "source_class": value["source_class"],
        "source_name": value["source_name"],
        "source_version": value["source_version"],
        "coverage_start": value["coverage_start"],
        "coverage_end": value["coverage_end"],
        "schedule_hash": value["schedule_hash"],
    })
    if (
        value["sessions"] != sessions
        or value["session_count"] != len(sessions)
        or value["schedule_hash"] != canonical_market_calendar_hash(sessions)
        or value["source_artifact_sha256"] != expected_source_hash
        or value["official_source_claimed"]
        != (value["source_class"] == "OFFICIAL_EXCHANGE_DOCUMENT")
        or value["official_source_verified"] is not False
        or value["external_truth_verified"] is not False
        or value["research_only"] is not True
        or value["paper_authorized"] is not False
        or value["live_order_allowed"] is not False
        or value["attestation_hash"] != canonical_market_calendar_hash(core)
    ):
        raise ValueError("market_calendar_attestation_verification_failed")
    return True


def _weekday_sessions(start_date: str, end_date: str) -> list[dict[str, Any]]:
    current = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    sessions: list[dict[str, Any]] = []
    while current <= end:
        if current.weekday() < 5:
            sessions.append({
                "date": current.isoformat(),
                "open_utc": f"{current.isoformat()}T14:30:00+00:00",
                "close_utc": f"{current.isoformat()}T21:00:00+00:00",
                "early_close": False,
            })
        current += timedelta(days=1)
    return sessions


def build_market_calendar_contract(
    *,
    calendar_name: str,
    start_date: str,
    end_date: str,
    observed_dates: list[str] | None = None,
    observed_sessions: list[dict[str, Any]] | None = None,
    schedule_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_name = _clean_text(calendar_name, upper=True)
    clean_start = _valid_date(start_date)
    clean_end = _valid_date(end_date)
    blockers: list[str] = []
    warnings: list[str] = []
    attestation: dict[str, Any] = {}
    if not clean_name or not clean_start or not clean_end or clean_start > clean_end:
        blockers.append("invalid_calendar_range")
    elif clean_name == TEST_CALENDAR_NAME:
        sessions = _weekday_sessions(clean_start, clean_end)
        try:
            attestation = build_market_schedule_attestation(
                calendar_name=clean_name,
                timezone_name="America/New_York",
                coverage_start=clean_start,
                coverage_end=clean_end,
                source_class="DETERMINISTIC_TEST_FIXTURE",
                source_name="deterministic_test_fixture",
                source_version="1",
                sessions=sessions,
            )
        except ValueError:
            blockers.append("calendar_has_no_sessions")
    elif type(schedule_attestation) is dict:
        try:
            verify_market_schedule_attestation(schedule_attestation)
            attestation = dict(schedule_attestation)
        except ValueError:
            blockers.append("schedule_attestation_invalid")
        if attestation and attestation["calendar_name"] != clean_name:
            blockers.append("schedule_attestation_calendar_mismatch")
        if attestation and (
            attestation["coverage_start"] > clean_start
            or attestation["coverage_end"] < clean_end
        ):
            blockers.append("schedule_attestation_range_incomplete")
    else:
        blockers.append("schedule_attestation_required")

    sessions = [
        dict(item)
        for item in attestation.get("sessions", [])
        if clean_start <= item["date"] <= clean_end
    ] if attestation and clean_start and clean_end else []
    if not sessions and not blockers:
        blockers.append("calendar_has_no_sessions")
    expected_dates = [item["date"] for item in sessions]
    expected_set = set(expected_dates)
    observed: list[str] = []
    duplicate_observed_date_count = 0
    invalid_observed_date_count = 0
    if observed_dates is not None:
        if type(observed_dates) is not list:
            blockers.append("observed_dates_exact_list_required")
        else:
            for item in observed_dates:
                clean = _valid_date(item)
                if clean:
                    observed.append(clean)
                else:
                    invalid_observed_date_count += 1
            duplicate_observed_date_count = len(observed) - len(set(observed))
            if invalid_observed_date_count:
                blockers.append(f"observed_dates_invalid:{invalid_observed_date_count}")
            if duplicate_observed_date_count:
                blockers.append(f"duplicate_observed_dates:{duplicate_observed_date_count}")
            if observed != sorted(observed):
                blockers.append("observed_dates_not_ordered")
    observed_unique = sorted(set(observed))
    missing_dates = (
        sorted(expected_set.difference(observed_unique))
        if observed_dates is not None
        else []
    )
    unexpected_dates = (
        sorted(set(observed_unique).difference(expected_set))
        if observed_dates is not None
        else []
    )
    if missing_dates:
        blockers.append(f"calendar_sessions_missing:{len(missing_dates)}")
    if unexpected_dates:
        blockers.append(f"non_session_dates_present:{len(unexpected_dates)}")

    early_close_dates = [item["date"] for item in sessions if item["early_close"]]
    session_mismatches: list[dict[str, Any]] = []
    if observed_sessions is not None:
        try:
            normalized_observed_sessions = _normalize_sessions(observed_sessions)
        except ValueError:
            normalized_observed_sessions = []
            blockers.append("observed_sessions_invalid")
        expected_by_date = {item["date"]: item for item in sessions}
        for item in normalized_observed_sessions:
            expected = expected_by_date.get(item["date"])
            if expected is not None and item != expected:
                session_mismatches.append({
                    "date": item["date"],
                    "expected": expected,
                    "observed": item,
                })
        if session_mismatches:
            blockers.append(f"session_window_mismatch:{len(session_mismatches)}")
    early_close_observation_complete = not early_close_dates or (
        observed_sessions is not None and not session_mismatches
    )
    if observed_dates is not None and early_close_dates and observed_sessions is None:
        warnings.append("early_close_session_window_unobserved")

    source_class = attestation.get("source_class", "")
    if blockers:
        research_admission_status = "BLOCK"
    elif source_class == "DETERMINISTIC_TEST_FIXTURE":
        research_admission_status = "TEST_ONLY"
    elif not early_close_observation_complete:
        research_admission_status = "RESEARCH_ONLY_WITH_UNOBSERVED_EARLY_CLOSE"
    else:
        research_admission_status = "RESEARCH_ONLY"
    admission_blockers = [] if research_admission_status != "BLOCK" else list(blockers)
    core = {
        "schema_version": MARKET_CALENDAR_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": warnings,
        "research_admission_status": research_admission_status,
        "admission_blockers": admission_blockers,
        "calendar_name": clean_name,
        "provider": attestation.get("source_name", ""),
        "provider_version": attestation.get("source_version", ""),
        "source_class": source_class,
        "official_source_claimed": attestation.get("official_source_claimed", False),
        "official_source_verified": False,
        "external_truth_verified": False,
        "start": clean_start,
        "end": clean_end,
        "session_count": len(sessions),
        "expected_dates": expected_dates,
        "observed_date_count": len(observed),
        "duplicate_observed_date_count": duplicate_observed_date_count,
        "invalid_observed_date_count": invalid_observed_date_count,
        "missing_dates": missing_dates,
        "unexpected_dates": unexpected_dates,
        "early_close_dates": early_close_dates,
        "early_close_observation_complete": early_close_observation_complete,
        "session_window_mismatches": session_mismatches,
        "schedule": sessions,
        "schedule_hash": attestation.get(
            "schedule_hash",
            canonical_market_calendar_hash([]),
        ),
        "schedule_attestation_hash": attestation.get("attestation_hash", ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "authority": dict(AUTHORITY_LOCK),
    }
    return {**core, "contract_hash": canonical_market_calendar_hash(core)}


def session_timestamp_ms(session_date: str) -> int:
    clean_date = _valid_date(session_date)
    if not clean_date:
        return 0
    return int(
        datetime.combine(
            date.fromisoformat(clean_date),
            datetime.min.time(),
            timezone.utc,
        ).timestamp()
        * 1000
    )


__all__ = [
    "AUTHORITY_LOCK",
    "MARKET_CALENDAR_SCHEMA_VERSION",
    "MARKET_SCHEDULE_ATTESTATION_VERSION",
    "SOURCE_CLASSES",
    "TEST_CALENDAR_NAME",
    "build_market_calendar_contract",
    "build_market_schedule_attestation",
    "canonical_market_calendar_hash",
    "infer_market_calendar",
    "session_timestamp_ms",
    "verify_market_schedule_attestation",
]
