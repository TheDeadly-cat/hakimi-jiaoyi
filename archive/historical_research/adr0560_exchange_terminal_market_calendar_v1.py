from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any


MARKET_CALENDAR_SCHEMA_VERSION = "exchange-session-calendar-v1"
TEST_CALENDAR_NAME = "WEEKDAY_FIXTURE"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def infer_market_calendar(
    benchmark_symbol: str,
    *,
    source: str = "",
    explicit: str = "",
) -> str:
    supplied = str(explicit or "").strip().upper()
    if supplied:
        return supplied
    clean_source = str(source or "").strip().lower()
    if clean_source in {"test", "fixture", "unit_test"} or "test_fixture" in clean_source:
        return TEST_CALENDAR_NAME
    symbol = str(benchmark_symbol or "").strip().upper()
    if symbol.startswith("HK."):
        return "XHKG"
    return "XNYS"


def _valid_date(value: Any) -> str:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


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


def _exchange_sessions(calendar_name: str, start_date: str, end_date: str) -> tuple[list[dict[str, Any]], str]:
    import exchange_calendars as exchange_calendars

    calendar = exchange_calendars.get_calendar(calendar_name)
    schedule = calendar.schedule.loc[start_date:end_date]
    early_closes = {
        value.strftime("%Y-%m-%d")
        for value in calendar.early_closes
        if start_date <= value.strftime("%Y-%m-%d") <= end_date
    }
    sessions: list[dict[str, Any]] = []
    for session_label, row in schedule.iterrows():
        session_date = session_label.strftime("%Y-%m-%d")
        sessions.append({
            "date": session_date,
            "open_utc": row["open"].isoformat(),
            "close_utc": row["close"].isoformat(),
            "early_close": session_date in early_closes,
        })
    return sessions, str(exchange_calendars.__version__)


def build_market_calendar_contract(
    *,
    calendar_name: str,
    start_date: str,
    end_date: str,
    observed_dates: list[str] | None = None,
) -> dict[str, Any]:
    clean_name = str(calendar_name or "").strip().upper()
    clean_start = _valid_date(start_date)
    clean_end = _valid_date(end_date)
    blockers: list[str] = []
    warnings: list[str] = []
    sessions: list[dict[str, Any]] = []
    provider = "exchange_calendars"
    provider_version = ""
    if not clean_start or not clean_end or clean_start > clean_end:
        blockers.append("invalid_calendar_range")
    elif clean_name == TEST_CALENDAR_NAME:
        provider = "deterministic_test_fixture"
        provider_version = "1"
        sessions = _weekday_sessions(clean_start, clean_end)
    else:
        try:
            sessions, provider_version = _exchange_sessions(clean_name, clean_start, clean_end)
        except Exception as exc:
            blockers.append(f"calendar_provider_unavailable:{clean_name}:{type(exc).__name__}")

    expected_dates = [str(item["date"]) for item in sessions]
    expected = set(expected_dates)
    observed = sorted({_valid_date(item) for item in observed_dates or [] if _valid_date(item)})
    missing_dates = sorted(expected.difference(observed)) if observed_dates is not None else []
    unexpected_dates = sorted(set(observed).difference(expected)) if observed_dates is not None else []
    if observed_dates is not None and missing_dates:
        blockers.append(f"calendar_sessions_missing:{len(missing_dates)}")
    if observed_dates is not None and unexpected_dates:
        blockers.append(f"non_session_dates_present:{len(unexpected_dates)}")
    if not sessions and not blockers:
        blockers.append("calendar_has_no_sessions")
    early_close_dates = [str(item["date"]) for item in sessions if item.get("early_close")]
    schedule_hash = _canonical_hash(sessions)
    payload = {
        "schema_version": MARKET_CALENDAR_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "warnings": warnings,
        "calendar_name": clean_name,
        "provider": provider,
        "provider_version": provider_version,
        "start": clean_start,
        "end": clean_end,
        "session_count": len(sessions),
        "expected_dates": expected_dates,
        "missing_dates": missing_dates,
        "unexpected_dates": unexpected_dates,
        "early_close_dates": early_close_dates,
        "schedule": sessions,
        "schedule_hash": schedule_hash,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["contract_hash"] = _canonical_hash(payload)
    return payload


def session_timestamp_ms(session_date: str) -> int:
    return int(datetime.combine(date.fromisoformat(session_date), datetime.min.time(), timezone.utc).timestamp() * 1000)
