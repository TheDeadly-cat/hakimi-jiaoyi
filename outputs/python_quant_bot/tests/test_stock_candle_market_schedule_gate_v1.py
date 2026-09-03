from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from _canonical_source import activate_canonical_source


activate_canonical_source()

from tests._stock_schedule_fixture import build_stock_schedule_fixture
from exchange_terminal import server as terminal_server
from exchange_terminal.research import stock_research
from exchange_terminal.services import market_calendar as calendar_service
from exchange_terminal.services.corporate_action_ledger import build_adjustment_evidence
from hakimi_research.stock_candle_quality import (
    STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
    STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION,
    analyze_stock_candle_series,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _row(value: str, close: float = 100.0) -> dict[str, object]:
    return {
        "ts": int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000),
        "date": value,
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1_000.0,
        "complete": True,
        "source": "synthetic_fixture",
    }


def _quality(
    rows: list[dict[str, object]],
    schedule: object,
) -> dict[str, object]:
    return analyze_stock_candle_series(
        rows,
        symbol="AAPL",
        interval="1d",
        source="synthetic_fixture",
        schedule_attestation=schedule,  # type: ignore[arg-type]
        minimum_analysis_rows=2,
    )


class StockCandleMarketScheduleGateV1Tests(unittest.TestCase):
    def test_versions_and_v5_archive_identity(self) -> None:
        self.assertEqual(STOCK_CANDLE_QUALITY_CONTRACT_VERSION, "stock-candle-quality-v6")
        self.assertEqual(STOCK_CANDLE_TEMPORAL_CONTRACT_VERSION, "stock-candle-temporal-conformance-v3")
        archive = REPOSITORY_ROOT / "archive" / "historical_research" / "adr0588_stock_candle_quality_v5.py"
        self.assertEqual(
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "fe24582f7771e1384b31dfc571d46dd8e1561adc4e950bf029fcd15b27ed03cb",
        )

    def test_missing_expected_session_blocks_and_clears_analysis_rows(self) -> None:
        rows = [_row("2026-07-01"), _row("2026-07-03", 101.0)]
        schedule = build_stock_schedule_fixture(
            rows,
            source="synthetic_fixture",
            session_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
        )
        quality = _quality(rows, schedule)

        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["analysis_ready"])
        self.assertEqual(quality["analysis_rows"], [])
        temporal = quality["temporal_conformance"]
        self.assertEqual(temporal["calendar_status"], "BLOCK")
        self.assertEqual(temporal["calendar_conformance"]["missing_dates"], ["2026-07-02"])
        self.assertIn("calendar_sessions_missing:1", temporal["calendar_blockers"])

    def test_exact_matching_schedule_passes_but_never_authorizes_trading(self) -> None:
        rows = [_row("2026-07-01"), _row("2026-07-02", 101.0), _row("2026-07-03", 102.0)]
        quality = _quality(rows, build_stock_schedule_fixture(rows, source="synthetic_fixture"))

        self.assertEqual(quality["status"], "PASS")
        self.assertTrue(quality["temporal_conformance"]["exchange_calendar_attested"])
        self.assertEqual(len(quality["analysis_rows"]), 3)
        self.assertTrue(all(value is False for value in quality["authority"].values()))

    def test_non_session_range_and_tampered_attestations_fail_closed(self) -> None:
        rows = [_row("2026-07-01"), _row("2026-07-02", 101.0), _row("2026-07-03", 102.0)]
        non_session = build_stock_schedule_fixture(
            rows,
            source="synthetic_fixture",
            session_dates=["2026-07-01", "2026-07-03"],
        )
        range_short = build_stock_schedule_fixture(
            rows,
            source="synthetic_fixture",
            session_dates=["2026-07-01", "2026-07-02"],
            coverage_end="2026-07-02",
        )
        tampered = build_stock_schedule_fixture(rows, source="synthetic_fixture")
        tampered["sessions"][0]["close_utc"] = "2026-07-01T19:59:00+00:00"

        self.assertIn("non_session_dates_present:1", _quality(rows, non_session)["temporal_conformance"]["calendar_blockers"])
        self.assertIn("schedule_attestation_range_incomplete", _quality(rows, range_short)["temporal_conformance"]["calendar_blockers"])
        self.assertIn("schedule_attestation_invalid", _quality(rows, tampered)["temporal_conformance"]["calendar_blockers"])
        self.assertIn("schedule_attestation_required", _quality(rows, None)["temporal_conformance"]["calendar_blockers"])

    def test_service_resolver_binds_independent_schedule_to_observed_rows(self) -> None:
        rows = [_row("2026-07-01"), _row("2026-07-03", 101.0)]
        sessions = [
            {
                "date": value,
                "open_utc": f"{value}T13:30:00+00:00",
                "close_utc": f"{value}T20:00:00+00:00",
                "early_close": False,
            }
            for value in ("2026-07-01", "2026-07-02", "2026-07-03")
        ]
        with patch.object(
            calendar_service,
            "_exchange_sessions",
            return_value=(sessions, "fixture", "America/New_York"),
        ):
            schedule = calendar_service.resolve_stock_candle_schedule_attestation(
                benchmark_symbol="AAPL",
                source="synthetic_fixture",
                rows=rows,
            )
        self.assertIsNotNone(schedule)
        self.assertEqual(_quality(rows, schedule)["status"], "BLOCK")

    def test_all_three_consumers_stop_on_missing_session(self) -> None:
        rows = [_row("2026-07-01"), _row("2026-07-03", 101.0)]
        schedule = build_stock_schedule_fixture(
            rows,
            source="synthetic_fixture",
            session_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
        )
        payload = {"rows": rows, "source": "synthetic_fixture", "origin_source": "synthetic_fixture"}
        with (
            patch.object(stock_research, "read_stock_persistent_candle_cache", return_value=payload),
            patch.object(stock_research, "resolve_stock_candle_schedule_attestation", return_value=schedule),
        ):
            research = stock_research.stock_unusual_activity_fast("AAPL", {"last": 101.0, "source": "synthetic_fixture"})
        with (
            patch.object(terminal_server, "market_ai_candles", return_value={"candles": rows, "source": "synthetic_fixture", "bar": "1d"}),
            patch.object(terminal_server, "resolve_stock_candle_schedule_attestation", return_value=schedule),
        ):
            local_ai = terminal_server.local_market_ai_analysis("AAPL", "1d", 101.0, [], {})
        evidence = build_adjustment_evidence(
            symbol="AAPL",
            rows=rows,
            source="synthetic_fixture",
            adjustment_basis="TEST_FIXTURE_CONTRACT",
            schedule_attestation=schedule,
        )

        self.assertFalse(research["ok"])
        self.assertTrue(local_ai["analysis_paused"])
        self.assertFalse(evidence["backtest_eligible"])
        self.assertIn("stock_candle_temporal_quality_block", evidence["blockers"])


if __name__ == "__main__":
    unittest.main()
