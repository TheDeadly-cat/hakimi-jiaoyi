from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal import server


def okx_row(ts_ms: int, complete: bool = True) -> list[str]:
    return [
        str(ts_ms), "100", "102", "99", "101", "1000", "0", "0", "1" if complete else "0",
    ]


class MarketHistoryCacheTests(unittest.TestCase):
    def test_crypto_cache_preserves_incomplete_candle_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "market-history.sqlite3"
            row = {
                "date": "2026-07-31",
                "ts_ms": 1_785_456_000_000,
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 1000,
                "complete": False,
            }
            with patch.object(server, "MARKET_HISTORY_CACHE_DB", db_path):
                server.upsert_market_history_cache("BTC-USDT", [row], "okx_history_candles")
                cached = server.read_market_history_cache("BTC-USDT", 10)

            self.assertEqual(len(cached["rows"]), 1)
            self.assertFalse(bool(cached["rows"][0]["complete"]))

    def test_okx_history_paginates_backwards_with_after_cursor(self) -> None:
        calls: list[dict[str, str]] = []
        pages = {
            "": [okx_row(6000), okx_row(5000), okx_row(4000)],
            "4000": [okx_row(3000), okx_row(2000), okx_row(1000)],
        }

        def reader(_path: str, query: dict[str, str]) -> list[list[str]]:
            calls.append(dict(query))
            return pages.get(query.get("after", ""), [])

        with patch.object(server, "okx_rows", side_effect=reader):
            rows = server.fetch_okx_daily_history("BTC-USDT", 6)

        self.assertEqual([row["ts_ms"] for row in rows], [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000, 6_000_000])
        self.assertEqual(calls[1]["after"], "4000")
        self.assertNotIn("before", calls[1])

    def test_data_reliability_treats_partial_cache_as_watch_and_ai_as_optional(self) -> None:
        checks = {
            "okx_ticker": (True, 4, "", {"last": "100"}),
            "okx_history": (True, 5, "", [["row"]]),
            "btc_local": (True, 0, "", {"rows": [{"date": "2026-01-01"}], "source": "fixture"}),
            "futu_status": (True, 0, "", {"opend_online": True, "message": "online"}),
        }
        cache_rows = [
            {"symbol": f"S{index}", "status": "READY" if index < 6 else "MISSING"}
            for index in range(10)
        ]

        with (
            patch.object(server, "timed_check", side_effect=lambda label, _fn: checks[label]),
            patch.object(
                server,
                "market_history_cache_status",
                return_value={"rows": cache_rows, "path": "market-history.sqlite", "summary": "READY 6 / MISSING 4"},
            ),
            patch.object(
                server,
                "STOCK_QUOTE_CACHE",
                {"time": server.now_ms(), "rows": [{"symbol": "AAPL"}]},
            ),
            patch.object(server, "deepseek_status", return_value={"configured": False, "model": "fixture", "thinking": "disabled"}),
        ):
            without_ai = server.data_reliability_center()

        with (
            patch.object(server, "timed_check", side_effect=lambda label, _fn: checks[label]),
            patch.object(
                server,
                "market_history_cache_status",
                return_value={"rows": cache_rows, "path": "market-history.sqlite", "summary": "READY 6 / MISSING 4"},
            ),
            patch.object(
                server,
                "STOCK_QUOTE_CACHE",
                {"time": server.now_ms(), "rows": [{"symbol": "AAPL"}]},
            ),
            patch.object(server, "deepseek_status", return_value={"configured": True, "model": "fixture", "thinking": "disabled"}),
        ):
            with_ai = server.data_reliability_center()

        rows = {row["id"]: row for row in without_ai["rows"]}
        self.assertEqual(rows["market_history_cache"]["status"], "WATCH")
        self.assertEqual(rows["deepseek_research"]["status"], "OPTIONAL")
        self.assertFalse(rows["deepseek_research"]["required"])
        self.assertEqual(without_ai["score"], with_ai["score"])
        self.assertEqual(without_ai["incidents"], with_ai["incidents"])
        self.assertNotIn("DeepSeek", " ".join(item["source"] for item in without_ai["incidents"]))


if __name__ == "__main__":
    unittest.main()
