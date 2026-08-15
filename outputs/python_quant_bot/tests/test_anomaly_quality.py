from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal import server


class AnomalyQualityTests(unittest.TestCase):
    def test_extreme_cached_stock_move_is_quarantined(self) -> None:
        quote = {
            "symbol": "TEST",
            "last": 200.0,
            "high24h": 210.0,
            "low24h": 100.0,
            "change24h_pct": 100.0,
            "volCcy24h": 1_000_000,
            "source": "stock_sqlite_cache",
        }
        with patch.object(server, "read_stock_quotes_cached", return_value=[quote]):
            rows = server.build_stock_anomaly_rows(limit=8, allow_network=True)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["data_quarantined"])
        self.assertEqual(row["severity"], "REVIEW")
        self.assertLessEqual(row["score"], 67)
        self.assertGreater(row["raw_score"], row["score"])
        self.assertEqual(row["watch_priority"]["label"], "C 数据待核")

        cards = server.market_sync_cards(rows)
        self.assertEqual(cards[2]["value"], "0")
        self.assertIn("待核 1", cards[3]["value"])

    def test_high_score_fallback_is_pending_not_trusted_high(self) -> None:
        row = {
            "market_type": "stock",
            "change24h_pct": 6.5,
            "score": 94,
            "raw_score": 94,
            "severity": "HIGH",
            "data_quality": {"fallback": True},
            "watch_priority": {"level": "C"},
        }

        cards = server.market_sync_cards([row])

        self.assertEqual(cards[2]["value"], "0")
        self.assertIn("待核 1", cards[3]["value"])

    def test_cached_high_score_builder_uses_review_severity(self) -> None:
        quote = {
            "symbol": "TEST",
            "last": 106.5,
            "high24h": 106.5,
            "low24h": 100.0,
            "change24h_pct": 6.5,
            "volCcy24h": 1_000_000,
            "source": "stock_sqlite_cache",
        }
        with patch.object(server, "read_stock_quotes_cached", return_value=[quote]):
            row = server.build_stock_anomaly_rows(limit=8, allow_network=True)[0]

        self.assertFalse(row["data_quarantined"])
        self.assertEqual(row["severity"], "REVIEW")
        self.assertEqual(row["severity_label"], "高分待核")
        self.assertGreaterEqual(row["score"], 68)

    def test_quarantined_external_quote_cannot_enter_b_queue(self) -> None:
        quote = {
            "symbol": "TEST",
            "last": 150.0,
            "high24h": 151.0,
            "low24h": 99.0,
            "change24h_pct": 50.0,
            "volCcy24h": 1_000_000,
            "source": "yahoo",
            "quote_quality": {
                "quarantined": True,
                "quarantine_reasons": ["涨跌幅超过45%，需核对复权、拆股和昨收基准"],
            },
        }
        with patch.object(server, "read_stock_quotes_cached", return_value=[quote]):
            row = server.build_stock_anomaly_rows(limit=8, allow_network=True)[0]

        self.assertTrue(row["data_quarantined"])
        self.assertEqual(row["watch_priority"]["level"], "C")
        self.assertEqual(row["watch_priority"]["label"], "C 数据待核")

    def test_closed_futu_anomaly_cannot_enter_a_queue(self) -> None:
        quote = {
            "symbol": "AAPL",
            "last": 110.0,
            "high24h": 111.0,
            "low24h": 99.0,
            "change24h_pct": 10.0,
            "volCcy24h": 1_000_000,
            "source": "futu",
            "status": "ONLINE",
            "ts": 99_000,
            "quote_quality": {"status": "READY", "fallback": False},
            "market_session": {
                "status": "LAST_SESSION",
                "phase": "closed",
                "is_open": False,
                "provider_confirmed": True,
            },
        }
        with patch.object(server, "now_ms", return_value=100_000):
            row = server.build_stock_anomaly_rows(limit=8, stock_rows=[quote])[0]

        self.assertEqual(row["data_quality"]["status"], "LAST_SESSION")
        self.assertEqual(row["data_quality"]["label"], "Futu最近时段")
        self.assertFalse(row["data_quality"]["realtime"])
        self.assertEqual(row["watch_priority"]["level"], "B")


if __name__ == "__main__":
    unittest.main()
