from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
BOT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for candidate in (str(SRC_ROOT), str(BOT_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from exchange_terminal.research import stock_research  # noqa: E402
from hakimi_research.market_calendar import (  # noqa: E402
    build_market_schedule_attestation,
)
from hakimi_research.stock_candle_quality import (  # noqa: E402
    STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
    STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
    analyze_stock_candle_series,
)
from hakimi_research.stock_data_quality import (  # noqa: E402
    STOCK_MARKET_DATA_GOVERNANCE_VERSION,
)
from hakimi_research.stock_quote_quality import (  # noqa: E402
    STOCK_QUOTE_QUALITY_CONTRACT_VERSION,
    normalize_stock_quote_quality,
)
from hakimi_research.stock_session import (  # noqa: E402
    STOCK_SESSION_CONTRACT_VERSION,
    build_stock_session_contract,
)


NY = ZoneInfo("America/New_York")


def _epoch(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _schedule(start: str, end: str, session_dates: list[str]) -> dict[str, object]:
    return build_market_schedule_attestation(
        calendar_name="XNYS",
        timezone_name="America/New_York",
        coverage_start=start,
        coverage_end=end,
        source_class="DETERMINISTIC_TEST_FIXTURE",
        source_name="adr0562-stock-governance",
        source_version="1",
        sessions=[
            {
                "date": session_date,
                "open_utc": f"{session_date}T13:30:00+00:00",
                "close_utc": f"{session_date}T20:00:00+00:00",
                "early_close": False,
            }
            for session_date in session_dates
        ],
    )


def _candle(timestamp: datetime, declared_date: str, *, close: float = 100.0) -> dict[str, object]:
    return {
        "ts": _epoch(timestamp),
        "date": declared_date,
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1_000.0,
        "complete": True,
        "source": "futu",
    }


class StockMarketDataGovernanceV1Tests(unittest.TestCase):
    def test_three_contracts_share_one_versioned_governance_boundary(self) -> None:
        self.assertEqual(
            STOCK_MARKET_DATA_GOVERNANCE_VERSION,
            "stock-market-data-governance-v1",
        )
        self.assertEqual(STOCK_SESSION_CONTRACT_VERSION, "stock-session-v3")
        self.assertEqual(STOCK_CANDLE_QUALITY_CONTRACT_VERSION, "stock-candle-quality-v6")
        self.assertEqual(
            STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
            "stock-candle-temporal-conformance-v3",
        )
        self.assertEqual(STOCK_QUOTE_QUALITY_CONTRACT_VERSION, "stock-quote-quality-v4")

    def test_open_session_requires_attested_schedule_coverage(self) -> None:
        regular = datetime(2026, 9, 8, 11, 0, tzinfo=NY)
        stamp = _epoch(regular)
        missing = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": stamp},
            market_state="MORNING",
            now_ms_value=stamp,
        )
        verified = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": stamp},
            market_state="MORNING",
            now_ms_value=stamp,
            schedule_attestation=_schedule("2026-09-08", "2026-09-08", ["2026-09-08"]),
        )

        self.assertEqual(missing["status"], "CALENDAR_UNVERIFIED")
        self.assertFalse(missing["analysis_ready"])
        self.assertFalse(missing["session_truth_verified"])
        self.assertEqual(verified["status"], "LIVE_SESSION")
        self.assertTrue(verified["analysis_ready"])
        self.assertTrue(verified["calendar_schedule_verified"])
        self.assertTrue(verified["session_schedule_bound"])
        self.assertFalse(verified["session_truth_verified"])

    def test_attested_non_trading_date_rejects_provider_open_claim(self) -> None:
        holiday = datetime(2026, 9, 7, 11, 0, tzinfo=NY)
        stamp = _epoch(holiday)
        result = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": stamp},
            market_state="MORNING",
            now_ms_value=stamp,
            schedule_attestation=_schedule(
                "2026-09-07",
                "2026-09-08",
                ["2026-09-08"],
            ),
        )

        self.assertEqual(result["calendar_quality"]["status"], "NON_TRADING_DATE")
        self.assertEqual(result["status"], "SESSION_MISMATCH")
        self.assertFalse(result["analysis_ready"])
        self.assertFalse(result["session_consistent"])

    def test_real_provider_daily_dates_use_provider_specific_timezone_semantics(self) -> None:
        timestamp = datetime(2026, 8, 31, 0, 30, tzinfo=timezone.utc)
        wrong_futu_rows = [_candle(timestamp, "2026-08-31")]
        wrong_futu = analyze_stock_candle_series(
            wrong_futu_rows,
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=_schedule("2026-08-31", "2026-08-31", ["2026-08-31"]),
        )
        correct_futu_row = _candle(timestamp, "2026-08-30")
        correct_futu = analyze_stock_candle_series(
            [correct_futu_row],
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=_schedule("2026-08-30", "2026-08-30", ["2026-08-30"]),
        )
        yahoo_row = {**_candle(timestamp, "2026-08-31"), "source": "yahoo_adjusted"}
        yahoo = analyze_stock_candle_series(
            [yahoo_row],
            symbol="AAPL",
            interval="1d",
            source="yahoo_adjusted",
            schedule_attestation=_schedule("2026-08-31", "2026-08-31", ["2026-08-31"]),
        )

        self.assertEqual(wrong_futu["status"], "BLOCK")
        self.assertIn(
            "DATE_TIMESTAMP_TIMEZONE_MISMATCH",
            wrong_futu["temporal_conformance"]["invalid_rows"][0]["reasons"],
        )
        self.assertEqual(correct_futu["status"], "PASS")
        self.assertEqual(yahoo["status"], "PASS")

    def test_quote_open_envelope_has_no_epsilon_false_acceptance(self) -> None:
        now = 1_788_200_000_000
        for open_price in (100.000001, 98.999999):
            with self.subTest(open_price=open_price):
                quote = normalize_stock_quote_quality(
                    {
                        "source": "futu",
                        "last": 99.5,
                        "open24h": open_price,
                        "high24h": 100.0,
                        "low24h": 99.0,
                        "bidPx": 99.4,
                        "askPx": 99.6,
                        "ts": now,
                    },
                    previous_close=99.5,
                    now_ms=now,
                )
                quality = quote["quote_quality"]
                self.assertEqual(quality["status"], "REVIEW")
                self.assertTrue(quality["quarantined"])
                self.assertFalse(quality["quote_complete"])
                self.assertEqual(quality["price_envelope_status"], "INVALID")

    def test_last_outside_daily_range_requires_explicit_compatible_scope(self) -> None:
        now = 1_788_200_000_000
        base = {
            "source": "futu",
            "last": 100.1,
            "open24h": 99.5,
            "high24h": 100.0,
            "low24h": 99.0,
            "bidPx": 100.0,
            "askPx": 100.2,
            "ts": now,
        }
        unknown = normalize_stock_quote_quality(
            base,
            previous_close=99.5,
            now_ms=now,
        )
        regular = normalize_stock_quote_quality(
            {**base, "last_price_scope": "REGULAR"},
            previous_close=99.5,
            now_ms=now,
        )

        self.assertEqual(unknown["quote_quality"]["status"], "DEGRADED")
        self.assertFalse(unknown["quote_quality"]["quote_complete"])
        self.assertFalse(unknown["quote_quality"]["quarantined"])
        self.assertEqual(regular["quote_quality"]["status"], "REVIEW")
        self.assertTrue(regular["quote_quality"]["quarantined"])

    def test_research_consumer_refuses_incomplete_quote_ohlc(self) -> None:
        rows: list[dict[str, object]] = []
        current = datetime(2026, 7, 6, 16, 0, tzinfo=NY)
        while len(rows) < 21:
            if current.weekday() < 5:
                close = 200.0 if len(rows) == 20 else 100.0 + len(rows) * 0.01
                rows.append(_candle(current, current.date().isoformat(), close=close))
            current += timedelta(days=1)
        now = 1_788_200_000_000
        quote = normalize_stock_quote_quality(
            {
                "source": "futu",
                "last": 100.4,
                "open24h": 100.2,
                "high24h": 100.0,
                "low24h": 99.0,
                "bidPx": 100.3,
                "askPx": 100.5,
                "vol24h": 2_000.0,
                "ts": now,
            },
            previous_close=99.5,
            now_ms=now,
        )
        payload = {
            "rows": rows,
            "source": "futu",
            "origin_source": "futu",
            "latest_at": "synthetic",
        }
        with patch.object(
            stock_research,
            "read_stock_persistent_candle_cache",
            return_value=payload,
        ):
            result = stock_research.stock_unusual_activity_fast("AAPL", quote)

        self.assertTrue(result["ok"])
        self.assertEqual(result["gap_pct"], 0.0)
        self.assertEqual(result["recent_volume"], 1_000.0)
        self.assertTrue(quote["quote_quality"]["quarantined"])

    def test_all_contracts_remain_research_only_and_non_authorizing(self) -> None:
        now = 1_788_200_000_000
        session = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": now},
            market_state="MORNING",
            now_ms_value=now,
        )
        candle_rows = [_candle(datetime(2026, 8, 31, tzinfo=NY), "2026-08-31")]
        candle = analyze_stock_candle_series(
            candle_rows,
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=_schedule("2026-08-31", "2026-08-31", ["2026-08-31"]),
        )
        quote = normalize_stock_quote_quality(
            {
                "source": "futu",
                "last": 100.0,
                "open24h": 100.0,
                "high24h": 101.0,
                "low24h": 99.0,
                "bidPx": 99.9,
                "askPx": 100.1,
                "ts": now,
            },
            previous_close=99.0,
            now_ms=now,
        )
        for payload in (session, candle, quote["quote_quality"]):
            self.assertEqual(
                payload["governance_version"],
                STOCK_MARKET_DATA_GOVERNANCE_VERSION,
            )
            self.assertTrue(all(value is False for value in payload["authority"].values()))


if __name__ == "__main__":
    unittest.main()
