from __future__ import annotations

from datetime import date
from typing import Any

from hakimi_research.market_calendar import (
    build_market_schedule_attestation,
    infer_market_calendar,
)


def build_stock_schedule_fixture(
    rows: list[dict[str, Any]],
    *,
    symbol: str = "AAPL",
    source: str = "futu",
    session_dates: list[str] | None = None,
    coverage_start: str = "",
    coverage_end: str = "",
) -> dict[str, Any]:
    dates = list(session_dates) if type(session_dates) is list else [
        row["date"]
        for row in rows
        if type(row) is dict and type(row.get("date")) is str
    ]
    normalized = sorted({date.fromisoformat(value).isoformat() for value in dates})
    if not normalized:
        raise ValueError("stock_schedule_fixture_dates_required")
    calendar_name = infer_market_calendar(symbol, source=source)
    timezone_name = {
        "XHKG": "Asia/Hong_Kong",
        "XSHG": "Asia/Shanghai",
    }.get(calendar_name, "America/New_York")
    return build_market_schedule_attestation(
        calendar_name=calendar_name,
        timezone_name=timezone_name,
        coverage_start=coverage_start or normalized[0],
        coverage_end=coverage_end or normalized[-1],
        source_class="DETERMINISTIC_TEST_FIXTURE",
        source_name="stock-candle-schedule-fixture",
        source_version="1",
        sessions=[
            {
                "date": value,
                "open_utc": f"{value}T13:30:00+00:00",
                "close_utc": f"{value}T20:00:00+00:00",
                "early_close": False,
            }
            for value in normalized
        ],
    )


__all__ = ["build_stock_schedule_fixture"]
