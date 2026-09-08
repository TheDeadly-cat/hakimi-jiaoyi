from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from _canonical_source import activate_canonical_source


activate_canonical_source()

from exchange_terminal.research import stock_research
from hakimi_research.stock_quote_quality import (
    STOCK_QUOTE_BOOK_COHERENCE_VERSION,
    STOCK_QUOTE_QUALITY_CONTRACT_VERSION,
    normalize_stock_quote_quality,
)
from tests._stock_schedule_fixture import build_stock_schedule_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
NOW_MS = 1_800_000_000_000


def _quote(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": "futu",
        "last": 100.0,
        "open24h": 99.0,
        "high24h": 101.0,
        "low24h": 98.0,
        "bidPx": 99.9,
        "askPx": 100.1,
        "ts": NOW_MS,
    }
    payload.update(overrides)
    return normalize_stock_quote_quality(
        payload,
        previous_close=99.0,
        change_basis="previous_close",
        now_ms=NOW_MS,
    )


def _break_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = datetime(2026, 4, 6, 16, 0, tzinfo=timezone.utc)
    while len(rows) < 21:
        if current.weekday() < 5:
            index = len(rows)
            close = 300.0 if index == 20 else 100.0 + index * 0.01
            rows.append({
                "ts": int(current.timestamp() * 1000),
                "date": current.date().isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000.0,
                "complete": True,
                "source": "synthetic_fixture",
            })
        current += timedelta(days=1)
    return rows


class StockQuoteBookCoherenceV1Tests(unittest.TestCase):
    def test_versions_and_v3_archive_identity(self) -> None:
        self.assertEqual(STOCK_QUOTE_QUALITY_CONTRACT_VERSION, "stock-quote-quality-v4")
        self.assertEqual(STOCK_QUOTE_BOOK_COHERENCE_VERSION, "stock-quote-book-coherence-v1")
        archive = REPOSITORY_ROOT / "archive" / "historical_research" / "adr0589_stock_quote_quality_v3.py"
        self.assertEqual(
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            "a2ea01edb2ce18bb65860c9635708e667209238c9633e97968dc64f743612135",
        )

    def test_exact_native_coherent_book_remains_pass_and_non_authorizing(self) -> None:
        quote = _quote()
        quality = quote["quote_quality"]

        self.assertEqual(quality["status"], "PASS")
        self.assertEqual(quality["book_coherence_status"], "PASS")
        self.assertTrue(quality["quote_complete"])
        self.assertEqual(quality["numeric_input_status"], "NATIVE")
        self.assertTrue(all(value is False for value in quality["authority"].values()))

    def test_unknown_scope_off_envelope_book_degrades_and_loses_completeness(self) -> None:
        quality = _quote(bidPx=1.0, askPx=2.0)["quote_quality"]

        self.assertEqual(quality["book_status"], "VALID")
        self.assertEqual(quality["book_coherence_status"], "DEGRADED")
        self.assertIn("BOOK_MIDPOINT_OUTSIDE_DAILY_ENVELOPE", quality["book_coherence_issues"])
        self.assertEqual(quality["status"], "DEGRADED")
        self.assertFalse(quality["quote_complete"])
        self.assertFalse(quality["quarantined"])

    def test_regular_scope_off_envelope_book_is_quarantined(self) -> None:
        quality = _quote(bidPx=1.0, askPx=2.0, last_price_scope="REGULAR")["quote_quality"]

        self.assertEqual(quality["book_coherence_status"], "REVIEW")
        self.assertEqual(quality["status"], "REVIEW")
        self.assertTrue(quality["quarantined"])
        self.assertFalse(quality["quote_complete"])

    def test_spread_wider_than_daily_range_is_not_complete(self) -> None:
        quality = _quote(bidPx=1.0, askPx=199.0)["quote_quality"]

        self.assertIn("BOOK_SPREAD_EXCEEDS_DAILY_RANGE", quality["book_coherence_issues"])
        self.assertEqual(quality["status"], "DEGRADED")
        self.assertFalse(quality["quote_complete"])

    def test_numeric_strings_are_displayable_but_not_complete(self) -> None:
        payload = {
            "source": "futu",
            "last": "100.0",
            "open24h": "99.0",
            "high24h": "101.0",
            "low24h": "98.0",
            "bidPx": "99.9",
            "askPx": "100.1",
            "ts": NOW_MS,
        }
        quote = normalize_stock_quote_quality(
            payload,
            previous_close="99.0",
            change_basis="previous_close",
            now_ms=NOW_MS,
        )
        quality = quote["quote_quality"]

        self.assertEqual(quality["status"], "DEGRADED")
        self.assertFalse(quality["quote_complete"])
        self.assertEqual(quality["numeric_input_status"], "COERCED")
        self.assertEqual(
            set(quality["numeric_coercion_fields"]),
            {"askPx", "bidPx", "high24h", "last", "low24h", "open24h", "previous_close"},
        )

    def test_hostile_subclasses_do_not_run_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapNumber(float):
            def __float__(self) -> float:
                calls.append("number.__float__")
                return 100.0

        class TrapText(str):
            def lower(self) -> str:
                calls.append("text.lower")
                return "futu"

            def strip(self, chars: str | None = None) -> str:
                calls.append("text.strip")
                return "100"

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return 100.0

        nested = _quote(last=TrapNumber(100.0), bidPx=TrapText("99.9"))
        container = normalize_stock_quote_quality(TrapDict())

        self.assertFalse(nested["quote_quality"]["quote_complete"])
        self.assertFalse(container["quote_quality"]["quote_complete"])
        self.assertEqual(calls, [])

    def test_stock_research_consumer_refuses_incoherent_quote_ohlc(self) -> None:
        rows = _break_rows()
        schedule = build_stock_schedule_fixture(rows, source="synthetic_fixture")
        payload = {"rows": rows, "source": "synthetic_fixture", "origin_source": "synthetic_fixture"}
        quote = _quote(bidPx=1.0, askPx=2.0)
        with (
            patch.object(stock_research, "read_stock_persistent_candle_cache", return_value=payload),
            patch.object(stock_research, "resolve_stock_candle_schedule_attestation", return_value=schedule),
        ):
            result = stock_research.stock_unusual_activity_fast("AAPL", quote)

        self.assertFalse(quote["quote_quality"]["quote_complete"])
        self.assertEqual(result["gap_pct"], 0.0)
        self.assertEqual(result["change_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
