from __future__ import annotations

from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from _canonical_source import activate_canonical_source


activate_canonical_source()

from tests._stock_schedule_fixture import build_stock_schedule_fixture
from hakimi_research.stock_candle_quality import analyze_stock_candle_series
from hakimi_research.stock_data_quality import (
    AUTHORITY_LOCK,
    STOCK_DATA_QUALITY_BOUNDARY_VERSION,
    observation_time_quality,
)
from hakimi_research.stock_quote_quality import normalize_stock_quote_quality
from hakimi_research.stock_session import build_stock_session_contract


def _epoch(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _valid_candles(count: int = 20) -> list[dict[str, object]]:
    start = datetime(2026, 8, 3, 16, 0, tzinfo=ZoneInfo("America/New_York"))
    rows: list[dict[str, object]] = []
    current = start
    while len(rows) < count:
        if current.weekday() < 5:
            index = len(rows)
            close = 100.0 + index
            rows.append({
                "ts": _epoch(current),
                "date": current.date().isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000.0 + index,
                "complete": True,
                "source": "futu",
            })
        current += timedelta(days=1)
    return rows


def _quality(rows: list[dict[str, object]]) -> dict[str, object]:
    return analyze_stock_candle_series(
        rows,
        symbol="AAPL",
        interval="1d",
        source="futu",
        schedule_attestation=build_stock_schedule_fixture(rows),
    )


class StockDataQualityBoundaryV2Tests(unittest.TestCase):
    def test_shared_time_contract_rejects_future_and_invalid_native_types(self) -> None:
        now = 1_788_200_000_000
        future = observation_time_quality(
            now + 60_000,
            now_ms=now,
            max_age_ms=120_000,
        )
        invalid = observation_time_quality(
            str(now),
            now_ms=now,
            max_age_ms=120_000,
        )

        self.assertEqual(STOCK_DATA_QUALITY_BOUNDARY_VERSION, "stock-data-quality-boundary-v3")
        self.assertEqual(future["status"], "FUTURE_TIMESTAMP")
        self.assertEqual(future["future_offset_ms"], 60_000)
        self.assertIsNone(future["age_ms"])
        self.assertEqual(invalid["status"], "INVALID_TIMESTAMP")
        self.assertTrue(all(value is False for value in future["authority"].values()))
        with self.assertRaises(TypeError):
            AUTHORITY_LOCK["paper"] = True  # type: ignore[index]

    def test_provider_open_phase_on_weekend_is_not_live_session(self) -> None:
        weekend = datetime(2026, 8, 30, 14, 0, tzinfo=ZoneInfo("America/New_York"))
        stamp = _epoch(weekend)
        result = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": stamp},
            market_state="MORNING",
            now_ms_value=stamp,
        )

        self.assertEqual(result["provider_phase"], "regular")
        self.assertEqual(result["inferred_phase"], "closed")
        self.assertFalse(result["session_consistent"])
        self.assertEqual(result["status"], "SESSION_MISMATCH")
        self.assertFalse(result["analysis_ready"])
        self.assertFalse(result["execution_eligible"])

    def test_future_quote_timestamp_blocks_session_freshness(self) -> None:
        now = datetime(2026, 8, 31, 11, 0, tzinfo=ZoneInfo("America/New_York"))
        now_ms = _epoch(now)
        result = build_stock_session_contract(
            "AAPL",
            {"source": "futu", "last": 100.0, "ts": now_ms + 86_400_000},
            market_state="MORNING",
            now_ms_value=now_ms,
        )

        self.assertEqual(result["time_quality"]["status"], "FUTURE_TIMESTAMP")
        self.assertEqual(result["status"], "TIME_INVALID")
        self.assertIsNone(result["quote_age_ms"])
        self.assertFalse(result["analysis_ready"])

    def test_invalid_ohlcv_rows_cannot_be_cleaned_into_pass(self) -> None:
        rows = _valid_candles()
        rows[3] = {
            **rows[3],
            "high": 90.0,
            "low": 110.0,
            "volume": -1.0,
        }
        result = _quality(rows)

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["structure_complete"])
        self.assertFalse(result["analysis_ready"])
        self.assertEqual(result["invalid_row_count"], 1)
        self.assertEqual(result["analysis_rows"], [])
        reasons = set(result["invalid_rows"][0]["reasons"])
        self.assertIn("HIGH_BELOW_OHLC_MAX", reasons)
        self.assertIn("LOW_ABOVE_OHLC_MIN", reasons)
        self.assertIn("VOLUME_INVALID", reasons)

    def test_duplicate_and_out_of_order_timestamps_block_analysis(self) -> None:
        duplicate_rows = _valid_candles()
        duplicate_rows[5]["ts"] = duplicate_rows[4]["ts"]
        out_of_order_rows = _valid_candles()
        out_of_order_rows[4], out_of_order_rows[5] = (
            out_of_order_rows[5],
            out_of_order_rows[4],
        )

        duplicate = _quality(duplicate_rows)
        out_of_order = _quality(out_of_order_rows)

        self.assertEqual(duplicate["duplicate_timestamp_count"], 1)
        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertFalse(out_of_order["timestamps_strictly_increasing"])
        self.assertEqual(out_of_order["status"], "BLOCK")

    def test_valid_complete_candles_remain_pass_and_non_authorizing(self) -> None:
        result = _quality(_valid_candles())

        self.assertEqual(result["contract_version"], "stock-candle-quality-v6")
        self.assertEqual(result["quality_boundary_version"], STOCK_DATA_QUALITY_BOUNDARY_VERSION)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["structure_complete"])
        self.assertTrue(result["analysis_ready"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_future_crossed_book_quote_is_quarantined(self) -> None:
        now = 1_788_200_000_000
        quote = normalize_stock_quote_quality(
            {
                "source": "futu",
                "last": 100.0,
                "open24h": 99.0,
                "high24h": 101.0,
                "low24h": 98.0,
                "bidPx": 105.0,
                "askPx": 95.0,
                "ts": now + 86_400_000,
            },
            previous_close=99.0,
            now_ms=now,
        )
        quality = quote["quote_quality"]

        self.assertEqual(quality["contract_version"], "stock-quote-quality-v4")
        self.assertEqual(quality["status"], "REVIEW")
        self.assertTrue(quality["quarantined"])
        self.assertEqual(quality["book_status"], "CROSSED")
        self.assertEqual(quality["time_quality"]["status"], "FUTURE_TIMESTAMP")
        self.assertIsNone(quality["age_ms"])
        self.assertGreaterEqual(len(quality["quarantine_reasons"]), 2)

    def test_missing_time_and_book_are_explicitly_degraded(self) -> None:
        quote = normalize_stock_quote_quality(
            {
                "source": "yahoo",
                "last": 100.0,
                "open24h": 99.0,
                "high24h": 101.0,
                "low24h": 98.0,
            },
            previous_close=99.0,
            now_ms=1_788_200_000_000,
        )
        quality = quote["quote_quality"]

        self.assertEqual(quality["status"], "DEGRADED")
        self.assertFalse(quality["quote_complete"])
        self.assertEqual(quality["book_status"], "NOT_SUPPLIED")
        self.assertEqual(quality["time_quality"]["status"], "MISSING_TIMESTAMP")

    def test_hostile_subclasses_never_control_quality_normalization(self) -> None:
        calls: list[str] = []

        class TrapInt(int):
            def __float__(self) -> float:
                calls.append("int.__float__")
                return 1_788_200_000_000.0

        class TrapText(str):
            def lower(self) -> str:
                calls.append("text.lower")
                return "futu"

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return 100.0

        class TrapDate:
            def __eq__(self, other: object) -> bool:
                calls.append("date.__eq__")
                return other == ""

        time_quality = observation_time_quality(
            TrapInt(1_788_200_000_000),
            now_ms=1_788_200_000_000,
            max_age_ms=120_000,
        )
        candle = analyze_stock_candle_series(
            [TrapDict()],
            symbol="AAPL",
            interval="1d",
            source="futu",
        )
        hostile_date_row = _valid_candles(1)[0]
        hostile_date_row["date"] = TrapDate()
        hostile_date = analyze_stock_candle_series(
            [hostile_date_row],
            symbol="AAPL",
            interval="1d",
            source="futu",
        )
        quote = normalize_stock_quote_quality({"source": TrapText("futu"), "last": 100.0})

        self.assertEqual(time_quality["status"], "INVALID_TIMESTAMP")
        self.assertEqual(candle["status"], "BLOCK")
        self.assertEqual(hostile_date["status"], "BLOCK")
        self.assertEqual(quote["quote_quality"]["status"], "DEGRADED")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
