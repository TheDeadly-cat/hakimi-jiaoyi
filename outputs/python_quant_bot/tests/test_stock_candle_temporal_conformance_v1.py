from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from _canonical_source import activate_canonical_source


activate_canonical_source()

from tests._stock_schedule_fixture import build_stock_schedule_fixture
from exchange_terminal.market_data import futu as futu_module
from exchange_terminal.services.corporate_action_ledger import (
    build_adjustment_evidence,
)
from hakimi_research.stock_candle_quality import (
    STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
    analyze_stock_candle_series,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _row(
    timestamp: datetime,
    declared_date: str,
    *,
    source: str,
    index: int = 0,
) -> dict[str, object]:
    close = 100.0 + index
    return {
        "ts": int(timestamp.timestamp() * 1000),
        "date": declared_date,
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1_000.0 + index,
        "complete": True,
        "source": source,
    }


class StockCandleTemporalConformanceV1Tests(unittest.TestCase):
    def test_invalid_futu_time_never_fabricates_current_timestamp(self) -> None:
        with patch.object(
            futu_module,
            "now_ms",
            side_effect=AssertionError("now_ms must not be used as provider time"),
        ):
            missing = futu_module.parse_futu_time_key("", "AAPL")
            invalid = futu_module.parse_futu_time_key("not-a-provider-time", "AAPL")
        quote = futu_module.normalize_futu_quote(
            {
                "last_price": 100.0,
                "open_price": 99.0,
                "high_price": 101.0,
                "low_price": 98.0,
                "update_time": "invalid",
            },
            "AAPL",
        )

        self.assertEqual(missing, 0)
        self.assertEqual(invalid, 0)
        self.assertEqual(quote["ts"], 0)

    def test_stooq_daily_parser_uses_symbol_timezone_not_host_timezone(self) -> None:
        source = (
            PROJECT_ROOT
            / "exchange_terminal"
            / "market_data"
            / "stock_candles_io.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            'time.mktime(time.strptime(date_text, "%Y-%m-%d"))',
            source,
        )
        self.assertIn('datetime.strptime(date_text, "%Y-%m-%d").replace(', source)
        self.assertIn("tzinfo=stock_timezone(symbol)", source)

    def test_shifted_daily_dates_block_analysis_and_backtest_eligibility(self) -> None:
        start = datetime(2026, 8, 3, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        rows = [
            _row(
                start + timedelta(days=index),
                ((start + timedelta(days=index)).date() + timedelta(days=1)).isoformat(),
                source="futu",
                index=index,
            )
            for index in range(20)
        ]

        quality = analyze_stock_candle_series(
            rows,
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=build_stock_schedule_fixture(rows),
        )
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=rows,
            source="futu",
            schedule_attestation=build_stock_schedule_fixture(rows),
        )

        self.assertTrue(quality["structure_complete"])
        self.assertFalse(quality["temporal_conformance_complete"])
        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["analysis_ready"])
        self.assertEqual(quality["analysis_rows"], [])
        self.assertEqual(
            quality["temporal_conformance"]["invalid_row_count"],
            20,
        )
        self.assertFalse(evidence["backtest_eligible"])
        self.assertIn("stock_candle_temporal_quality_block", evidence["blockers"])

    def test_daily_utc_and_symbol_local_date_semantics_are_both_explicit(self) -> None:
        yahoo_timestamp = datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc)
        futu_timestamp = datetime(
            2026,
            8,
            31,
            0,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        )
        yahoo_rows = [_row(yahoo_timestamp, "2026-08-31", source="yahoo_adjusted")]
        futu_rows = [_row(futu_timestamp, "2026-08-31", source="futu")]
        yahoo = analyze_stock_candle_series(
            yahoo_rows,
            symbol="AAPL",
            interval="1d",
            source="yahoo_adjusted",
            schedule_attestation=build_stock_schedule_fixture(yahoo_rows, source="yahoo_adjusted"),
        )
        futu = analyze_stock_candle_series(
            futu_rows,
            symbol="AAPL",
            interval="1d",
            source="futu",
            schedule_attestation=build_stock_schedule_fixture(futu_rows),
        )

        for quality in (yahoo, futu):
            self.assertEqual(quality["status"], "PASS")
            self.assertTrue(quality["temporal_conformance_complete"])
            temporal = quality["temporal_conformance"]
            self.assertEqual(
                temporal["contract_version"],
                STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
            )
            self.assertTrue(temporal["exchange_calendar_attested"])
            self.assertTrue(
                all(value is False for value in temporal["authority"].values())
            )
        self.assertEqual(
            yahoo["temporal_conformance"]["source_semantics"],
            ["DAILY_UTC_DATE"],
        )
        self.assertEqual(
            futu["temporal_conformance"]["source_semantics"],
            ["DAILY_SYMBOL_LOCAL_DATE"],
        )

    def test_missing_context_and_unknown_source_semantics_fail_closed(self) -> None:
        timestamp = datetime(
            2026,
            8,
            31,
            16,
            0,
            tzinfo=ZoneInfo("America/New_York"),
        )
        row = _row(timestamp, "2026-08-31", source="mystery_provider")
        missing_context = analyze_stock_candle_series([row])
        unknown_source = analyze_stock_candle_series(
            [row],
            symbol="AAPL",
            interval="1d",
            source="mystery_provider",
        )

        self.assertEqual(missing_context["status"], "BLOCK")
        self.assertEqual(
            missing_context["temporal_conformance"]["invalid_rows"][0]["reasons"],
            ["SYMBOL_INTERVAL_SOURCE_CONTEXT_REQUIRED"],
        )
        self.assertEqual(unknown_source["status"], "BLOCK")
        self.assertIn(
            "SOURCE_TIMESTAMP_SEMANTICS_UNVERIFIED",
            unknown_source["temporal_conformance"]["invalid_rows"][0]["reasons"],
        )

    def test_hostile_temporal_context_types_do_not_run_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapText(str):
            def strip(self, chars: str | None = None) -> str:
                calls.append("text.strip")
                return "AAPL"

            def lower(self) -> str:
                calls.append("text.lower")
                return "1d"

        timestamp = datetime(2026, 8, 31, tzinfo=timezone.utc)
        row = _row(timestamp, "2026-08-31", source="futu")
        quality = analyze_stock_candle_series(
            [row],
            symbol=TrapText("AAPL"),
            interval=TrapText("1d"),
            source=TrapText("futu"),
        )
        parsed = futu_module.parse_futu_time_key(TrapText("2026-08-31"), "AAPL")

        self.assertEqual(quality["status"], "BLOCK")
        self.assertEqual(parsed, 0)
        self.assertEqual(calls, [])

    def test_all_active_consumers_bind_symbol_interval_and_source(self) -> None:
        consumers = (
            PROJECT_ROOT / "exchange_terminal" / "research" / "stock_research.py",
            PROJECT_ROOT / "exchange_terminal" / "services" / "corporate_action_ledger.py",
            PROJECT_ROOT / "exchange_terminal" / "server.py",
        )
        for path in consumers:
            source = path.read_text(encoding="utf-8")
            self.assertIn("symbol=", source, path.name)
            self.assertIn("interval=", source, path.name)
            self.assertIn("source=", source, path.name)
            self.assertIn("temporal_conformance_complete", source, path.name)
            self.assertIn("schedule_attestation=", source, path.name)


if __name__ == "__main__":
    unittest.main()
