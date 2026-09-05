from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from _canonical_source import activate_canonical_source


activate_canonical_source()

from tests._stock_schedule_fixture import build_stock_schedule_fixture
from exchange_terminal import server as terminal_server
from exchange_terminal.research import stock_research
from exchange_terminal.services.corporate_action_ledger import (
    build_adjustment_evidence,
)
from hakimi_research.stock_candle_quality import (
    STOCK_CANDLE_QUALITY_CONTRACT_VERSION,
    analyze_stock_candle_series,
)
from hakimi_research.stock_data_quality import STOCK_DATA_QUALITY_BOUNDARY_VERSION


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_MISSING = object()


def _rows(count: int = 30, *, complete: object = True) -> list[dict[str, object]]:
    current = datetime(2026, 7, 1, 16, 0, tzinfo=ZoneInfo("America/New_York"))
    rows: list[dict[str, object]] = []
    while len(rows) < count:
        if current.weekday() < 5:
            index = len(rows)
            close = 100.0 + index
            row: dict[str, object] = {
                "ts": int(current.timestamp() * 1000),
                "date": current.date().isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000.0 + index,
                "source": "futu",
            }
            if complete is not _MISSING:
                row["complete"] = complete
            rows.append(row)
        current += timedelta(days=1)
    return rows


def _quality(rows: list[dict[str, object]]) -> dict[str, object]:
    return analyze_stock_candle_series(
        rows,
        symbol="AAPL",
        interval="1d",
        source="futu",
        schedule_attestation=build_stock_schedule_fixture(rows),
        minimum_analysis_rows=20,
    )


class StockCandleCompletionGateV1Tests(unittest.TestCase):
    def test_versions_and_predecessor_archives_are_exact(self) -> None:
        self.assertEqual(STOCK_DATA_QUALITY_BOUNDARY_VERSION, "stock-data-quality-boundary-v3")
        self.assertEqual(STOCK_CANDLE_QUALITY_CONTRACT_VERSION, "stock-candle-quality-v6")
        expected = {
            "adr0587_stock_data_quality_boundary_v2.py": "be0e836598c84972cfa538f7f9f4b2dce6ab697ed384b51e13bbbdea8eb968c2",
            "adr0587_stock_candle_quality_v4.py": "4ccd9d7bb71d06c2121be8b93926c0e632722e416d58e7de70256ac7468af1a5",
            "adr0588_stock_candle_quality_v5.py": "fe24582f7771e1384b31dfc571d46dd8e1561adc4e950bf029fcd15b27ed03cb",
        }
        root = REPOSITORY_ROOT / "archive" / "historical_research"
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)

    def test_all_explicitly_incomplete_rows_block_analysis(self) -> None:
        quality = _quality(_rows(30, complete=False))
        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["analysis_ready"])
        self.assertEqual(quality["incomplete_row_count"], 30)
        self.assertEqual(quality["analysis_eligible_row_count"], 0)
        self.assertEqual(quality["analysis_excluded_row_count"], 30)
        self.assertEqual(quality["analysis_rows"], [])

    def test_missing_completion_evidence_blocks_analysis(self) -> None:
        quality = _quality(_rows(30, complete=_MISSING))
        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["analysis_ready"])
        self.assertEqual(quality["completion_unknown_count"], 30)
        self.assertEqual(quality["analysis_rows"], [])

    def test_mixed_series_blocks_when_expected_sessions_are_not_complete(self) -> None:
        rows = _rows(32)
        rows[10].pop("complete")
        rows[-1]["complete"] = False
        quality = _quality(rows)
        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["analysis_ready"])
        self.assertEqual(quality["analysis_eligible_row_count"], 30)
        self.assertEqual(quality["analysis_excluded_row_count"], 2)
        self.assertEqual(quality["analysis_row_count"], 0)
        self.assertEqual(quality["analysis_rows"], [])
        self.assertEqual(
            len(quality["temporal_conformance"]["calendar_conformance"]["missing_dates"]),
            2,
        )

    def test_non_boolean_completion_is_structurally_invalid(self) -> None:
        quality = _quality(_rows(30, complete=1))
        self.assertEqual(quality["status"], "BLOCK")
        self.assertFalse(quality["structure_complete"])
        self.assertIn("COMPLETE_NOT_EXACT_BOOL", quality["invalid_rows"][0]["reasons"])

    def test_research_consumers_refuse_all_incomplete_series(self) -> None:
        rows = _rows(30, complete=False)
        payload = {"rows": rows, "source": "futu", "origin_source": "futu"}
        quote = {"last": 129.0, "source": "futu", "change24h_pct": 1.0}
        with patch.object(stock_research, "read_stock_persistent_candle_cache", return_value=payload):
            unusual = stock_research.stock_unusual_activity_fast("AAPL", quote)
            swing = stock_research.stock_daily_swing_fast(
                "AAPL",
                quote,
                {"volume_ratio": 1.0},
            )
        self.assertFalse(unusual["ok"])
        self.assertFalse(swing["ok"])

    def test_local_ai_refuses_all_incomplete_series(self) -> None:
        rows = _rows(30, complete=False)
        with patch.object(
            terminal_server,
            "market_ai_candles",
            return_value={"candles": rows, "source": "futu", "bar": "1d"},
        ):
            result = terminal_server.local_market_ai_analysis(
                "AAPL",
                "1d",
                129.0,
                [],
                {},
            )
        self.assertFalse(result["ok"])
        self.assertTrue(result["analysis_paused"])
        self.assertEqual(result["candle_count"], 0)

    def test_backtest_admission_blocks_incomplete_and_unknown_rows(self) -> None:
        cases = (
            (_rows(30, complete=False), "stock_candle_contains_incomplete_rows"),
            (_rows(30, complete=_MISSING), "stock_candle_completion_evidence_missing"),
        )
        for rows, blocker in cases:
            with self.subTest(blocker=blocker):
                evidence = build_adjustment_evidence(
                    symbol="AAPL",
                    rows=rows,
                    source="futu",
                    adjustment_basis="TEST_FIXTURE_CONTRACT",
                )
                self.assertFalse(evidence["backtest_eligible"])
                self.assertIn(blocker, evidence["blockers"])


if __name__ == "__main__":
    unittest.main()
