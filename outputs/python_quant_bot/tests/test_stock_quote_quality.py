from __future__ import annotations

import sys
import unittest
from pathlib import Path


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.market_data.stock_quote_quality import normalize_stock_quote_quality


class StockQuoteQualityTests(unittest.TestCase):
    def test_previous_close_is_preferred_over_open(self) -> None:
        quote = normalize_stock_quote_quality(
            {
                "source": "yahoo",
                "last": 110,
                "open24h": 100,
                "high24h": 112,
                "low24h": 99,
                "bidPx": 109.9,
                "askPx": 110.1,
                "change24h_pct": 4.76,
                "ts": 1_000,
            },
            previous_close=105,
            change_basis="previous_close",
            provider_change=4.76,
            now_ms=2_000,
        )

        self.assertEqual(quote["change_basis"], "previous_close")
        self.assertEqual(quote["prevClose"], 105)
        self.assertAlmostEqual(quote["change24h_pct"], 4.76, places=2)
        self.assertEqual(quote["quote_quality"]["status"], "PASS")

    def test_missing_previous_close_uses_open_and_degrades(self) -> None:
        quote = normalize_stock_quote_quality(
            {"source": "stooq", "last": 102, "open24h": 100, "high24h": 103, "low24h": 99},
        )

        self.assertEqual(quote["change_basis"], "open")
        self.assertEqual(quote["change24h_pct"], 2.0)
        self.assertEqual(quote["quote_quality"]["status"], "DEGRADED")
        self.assertTrue(any("缺少昨收" in item for item in quote["quote_quality"]["warnings"]))

    def test_extreme_fallback_move_is_quarantined(self) -> None:
        quote = normalize_stock_quote_quality(
            {
                "source": "stock_sqlite_cache",
                "last": 200,
                "open24h": 100,
                "high24h": 210,
                "low24h": 95,
                "ts": 1_000,
            },
            previous_close=100,
            change_basis="local_previous_close",
            now_ms=2_000,
        )

        self.assertTrue(quote["quote_quality"]["quarantined"])
        self.assertEqual(quote["quote_quality"]["status"], "REVIEW")
        self.assertTrue(quote["quote_quality"]["quarantine_reasons"])

    def test_old_timestamp_is_not_reported_ready(self) -> None:
        quote = normalize_stock_quote_quality(
            {
                "source": "yahoo",
                "last": 101,
                "open24h": 100,
                "high24h": 102,
                "low24h": 99,
                "ts": 1_000,
            },
            previous_close=100,
            now_ms=1_000 + 13 * 60 * 60 * 1000,
        )

        self.assertEqual(quote["quote_quality"]["status"], "DEGRADED")
        self.assertTrue(any("超过12小时" in item for item in quote["quote_quality"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
