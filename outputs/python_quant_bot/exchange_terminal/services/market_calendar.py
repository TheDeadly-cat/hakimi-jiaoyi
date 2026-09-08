from __future__ import annotations

from datetime import date
from typing import Any

from hakimi_research.market_calendar import (
    MARKET_CALENDAR_SCHEMA_VERSION,
    MARKET_SCHEDULE_ATTESTATION_VERSION,
    TEST_CALENDAR_NAME,
    build_market_calendar_contract as build_canonical_market_calendar_contract,
    build_market_schedule_attestation,
    canonical_market_calendar_hash,
    infer_market_calendar,
    session_timestamp_ms,
    verify_market_schedule_attestation,
)


def _exchange_sessions(
    calendar_name: str,
    start_date: str,
    end_date: str,
) -> tuple[list[dict[str, Any]], str, str]:
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
    timezone_value = getattr(calendar.tz, "key", None)
    timezone_name = timezone_value if type(timezone_value) is str else str(calendar.tz)
    return sessions, str(exchange_calendars.__version__), timezone_name


def _resolve_market_schedule_attestation(
    calendar_name: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any] | None:
    try:
        if calendar_name == TEST_CALENDAR_NAME:
            fixture = build_canonical_market_calendar_contract(
                calendar_name=calendar_name,
                start_date=start_date,
                end_date=end_date,
            )
            if fixture.get("status") != "PASS":
                return None
            return build_market_schedule_attestation(
                calendar_name=calendar_name,
                timezone_name="America/New_York",
                coverage_start=start_date,
                coverage_end=end_date,
                source_class="DETERMINISTIC_TEST_FIXTURE",
                source_name="deterministic_test_fixture",
                source_version="1",
                sessions=list(fixture.get("schedule") or []),
            )
        sessions, version, timezone_name = _exchange_sessions(
            calendar_name,
            start_date,
            end_date,
        )
        return build_market_schedule_attestation(
            calendar_name=calendar_name,
            timezone_name=timezone_name,
            coverage_start=start_date,
            coverage_end=end_date,
            source_class="THIRD_PARTY_LIBRARY",
            source_name="exchange_calendars",
            source_version=version,
            sessions=sessions,
        )
    except Exception:
        return None


def resolve_stock_candle_schedule_attestation(
    *,
    benchmark_symbol: str,
    source: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if type(benchmark_symbol) is not str or type(source) is not str or type(rows) is not list:
        return None
    observed_dates: list[str] = []
    for row in rows:
        if type(row) is not dict:
            continue
        value = row.get("date")
        if type(value) is not str:
            continue
        try:
            observed_dates.append(date.fromisoformat(value).isoformat())
        except ValueError:
            continue
    if not observed_dates:
        return None
    calendar_name = infer_market_calendar(benchmark_symbol, source=source)
    return _resolve_market_schedule_attestation(
        calendar_name,
        min(observed_dates),
        max(observed_dates),
    )


def build_market_calendar_contract(
    *,
    calendar_name: str,
    start_date: str,
    end_date: str,
    observed_dates: list[str] | None = None,
    observed_sessions: list[dict[str, Any]] | None = None,
    schedule_attestation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_name = calendar_name.strip().upper() if type(calendar_name) is str else ""
    clean_start = start_date if type(start_date) is str else ""
    clean_end = end_date if type(end_date) is str else ""
    attestation = schedule_attestation if type(schedule_attestation) is dict else None
    if clean_name != TEST_CALENDAR_NAME and attestation is None:
        attestation = _resolve_market_schedule_attestation(
            clean_name,
            clean_start,
            clean_end,
        )
    return build_canonical_market_calendar_contract(
        calendar_name=calendar_name,
        start_date=start_date,
        end_date=end_date,
        observed_dates=observed_dates,
        observed_sessions=observed_sessions,
        schedule_attestation=attestation,
    )


__all__ = [
    "MARKET_CALENDAR_SCHEMA_VERSION",
    "MARKET_SCHEDULE_ATTESTATION_VERSION",
    "TEST_CALENDAR_NAME",
    "build_market_calendar_contract",
    "build_market_schedule_attestation",
    "canonical_market_calendar_hash",
    "infer_market_calendar",
    "resolve_stock_candle_schedule_attestation",
    "session_timestamp_ms",
    "verify_market_schedule_attestation",
]
