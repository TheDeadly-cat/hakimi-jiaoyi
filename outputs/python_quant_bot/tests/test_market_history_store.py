from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal import server
from exchange_terminal.market_data.candle_contract import candle_is_complete
from exchange_terminal.services.market_history_store import (
    MarketHistoryStore,
    build_history_dataset_evidence,
    normalize_history_candle,
)


BASE_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)


def candle(
    index: int,
    *,
    close: float = 101.0,
    complete: object = True,
    source: str = "okx_history_candles",
) -> dict[str, object]:
    stamp = BASE_DATE + timedelta(days=index)
    return {
        "date": stamp.strftime("%Y-%m-%d"),
        "ts_ms": int(stamp.timestamp() * 1000),
        "open": 100.0,
        "high": max(102.0, close),
        "low": min(99.0, close),
        "close": close,
        "volume": 1_000.0,
        "complete": complete,
        "source": source,
    }


def okx_row(index: int, *, complete: bool = True) -> list[str]:
    row = candle(index, complete=complete)
    return [
        str(row["ts_ms"]),
        str(row["open"]),
        str(row["high"]),
        str(row["low"]),
        str(row["close"]),
        str(row["volume"]),
        "0",
        "0",
        "1" if complete else "0",
    ]


class MarketHistoryStoreTests(unittest.TestCase):
    def test_production_history_report_uses_after_cursor(self) -> None:
        calls: list[dict[str, str]] = []
        cursor = str(candle(3)["ts_ms"])
        pages = {
            "": [okx_row(5), okx_row(4), okx_row(3)],
            cursor: [okx_row(2), okx_row(1), okx_row(0)],
        }

        def reader(_path: str, query: dict[str, str]) -> tuple[list[list[str]], str]:
            calls.append(dict(query))
            return pages.get(query.get("after", ""), []), ""

        with patch.object(server, "okx_rows_with_error", side_effect=reader):
            rows, source, attempts = server.fetch_daily_history_with_report("BTC-USDT", 6)

        self.assertEqual(len(rows), 6)
        self.assertEqual(source, "okx_history_candles")
        self.assertEqual(calls[1].get("after"), cursor)
        self.assertNotIn("before", calls[1])
        self.assertEqual(len(attempts), 2)

    def test_completion_contract_preserves_false_and_confirmed_zero(self) -> None:
        false_row = candle(0, complete="false")
        normalized_false = normalize_history_candle(false_row, require_utc_date=True)
        self.assertIsNotNone(normalized_false)
        self.assertFalse(normalized_false["complete"])
        self.assertFalse(candle_is_complete(false_row))

        confirmed_row = dict(candle(1))
        confirmed_row.pop("complete")
        confirmed_row["confirmed"] = 0
        normalized_confirmed = server.normalize_backtest_candle(confirmed_row)
        self.assertIsNotNone(normalized_confirmed)
        self.assertFalse(normalized_confirmed["complete"])
        self.assertFalse(candle_is_complete(confirmed_row))

    def test_invalid_prices_nonfinite_values_and_date_mismatch_are_rejected(self) -> None:
        invalid_rows = [
            {**candle(0), "close": math.nan},
            {**candle(1), "volume": math.inf},
            {**candle(2), "high": 99.5},
            {**candle(3), "low": 101.5},
            {**candle(4), "date": "2025-02-01"},
            {**candle(5), "complete": "maybe"},
        ]
        for row in invalid_rows:
            self.assertIsNone(normalize_history_candle(row, require_utc_date=True))

    def test_lower_priority_incomplete_row_cannot_replace_completed_okx_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite", now_ms=lambda: 10)
            first = store.upsert("BTC-USDT", [candle(0)], "okx_history_candles")
            second = store.upsert(
                "BTC-USDT",
                [candle(0, close=88.0, complete="false", source="binance_spot_klines")],
                "binance_spot_klines",
            )
            cached = store.read("BTC-USDT", 10)
            revisions = store.revision_summary("BTC-USDT")

        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["rejected"], 1)
        self.assertEqual(cached["rows"][0]["close"], 101.0)
        self.assertTrue(cached["rows"][0]["complete"])
        self.assertEqual(cached["rows"][0]["source"], "okx_history_candles")
        self.assertEqual(revisions["rejected"], 1)
        self.assertEqual(revisions["rows"][0]["action"], "REJECTED")

    def test_completed_row_replaces_incomplete_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite", now_ms=lambda: 20)
            store.upsert(
                "BTC-USDT",
                [candle(0, close=100.0, complete=False, source="binance_spot_klines")],
                "binance_spot_klines",
            )
            report = store.upsert("BTC-USDT", [candle(0, close=101.0)], "okx_history_candles")
            cached = store.read("BTC-USDT", 10)

        self.assertEqual(report["updated"], 1)
        self.assertEqual(cached["rows"][0]["close"], 101.0)
        self.assertTrue(cached["rows"][0]["complete"])

    def test_lower_priority_incomplete_revision_cannot_replace_incomplete_okx_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite")
            store.upsert(
                "BTC-USDT", [candle(0, close=100.0, complete=False)], "okx_history_candles"
            )
            report = store.upsert(
                "BTC-USDT",
                [candle(0, close=88.0, complete=False, source="binance_spot_klines")],
                "binance_spot_klines",
            )
            cached = store.read("BTC-USDT", 10)

        self.assertEqual(report["rejected"], 1)
        self.assertEqual(cached["rows"][0]["close"], 100.0)
        self.assertFalse(cached["rows"][0]["complete"])

    def test_read_only_store_refuses_write_without_creating_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.sqlite"
            report = MarketHistoryStore(db_path, read_only=True).upsert(
                "BTC-USDT", [candle(0)], "okx_history_candles"
            )
            self.assertEqual(report["status"], "BLOCK")
            self.assertEqual(report["stored"], 0)
            self.assertFalse(db_path.exists())

    def test_corrupt_database_fails_closed_for_reads_and_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.sqlite"
            db_path.write_bytes(b"not-a-sqlite-database")
            store = MarketHistoryStore(db_path)
            read_result = store.read("BTC-USDT", 10)
            write_result = store.upsert("BTC-USDT", [candle(0)], "okx_history_candles")

        self.assertEqual(read_result["status"], "BLOCK")
        self.assertEqual(read_result["rows"], [])
        self.assertEqual(write_result["status"], "BLOCK")
        self.assertIn("market_history_database_write_failed", write_result["blockers"])

    def test_concurrent_writes_are_serialized_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite")
            with ThreadPoolExecutor(max_workers=8) as pool:
                reports = list(pool.map(
                    lambda index: store.upsert(
                        "BTC-USDT", [candle(index)], "okx_history_candles"
                    ),
                    range(32),
                ))
            cached = store.read("BTC-USDT", 100)

        self.assertTrue(
            all(report["stored"] == 1 for report in reports),
            [report for report in reports if report["stored"] != 1],
        )
        self.assertEqual(len(cached["rows"]), 32)
        self.assertEqual(cached["manifest"]["complete_count"], 32)

    def test_manifest_hash_is_stable_for_idempotent_refetch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite", now_ms=lambda: 100)
            store.upsert("BTC-USDT", [candle(index) for index in range(3)], "okx_history_candles")
            first = store.read("BTC-USDT", 10)["manifest"]
            store.upsert("BTC-USDT", [candle(index) for index in range(3)], "okx_history_candles")
            second = store.read("BTC-USDT", 10)["manifest"]

        self.assertEqual(first["data_hash"], second["data_hash"])

    def test_ready_status_counts_only_completed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MarketHistoryStore(Path(temp_dir) / "history.sqlite")
            rows = [candle(index) for index in range(239)]
            rows.extend(candle(300 + index, complete=False) for index in range(20))
            store.upsert("BTC-USDT", rows, "okx_history_candles")
            partial = store.read("BTC-USDT", 500)["manifest"]
            store.upsert("BTC-USDT", [candle(239)], "okx_history_candles")
            ready = store.read("BTC-USDT", 500)["manifest"]

        self.assertEqual(partial["status"], "PARTIAL")
        self.assertEqual(partial["complete_count"], 239)
        self.assertEqual(ready["status"], "READY")
        self.assertEqual(ready["complete_count"], 240)

    def test_dataset_evidence_binds_lineage_and_rejects_blocked_cache_admission(self) -> None:
        rows = [candle(index) for index in range(3)]
        frozen = build_history_dataset_evidence(
            symbol="BTC-USDT",
            rows=rows,
            source="okx_history_candles",
            dataset_lineage_id="matrix:g49:BTC-USDT",
            cache_manifest={"status": "READY", "data_hash": "a" * 64},
            cache_admitted=True,
        )
        blocked = build_history_dataset_evidence(
            symbol="BTC-USDT",
            rows=rows,
            source="okx_history_candles",
            dataset_lineage_id="matrix:g49:BTC-USDT",
            cache_manifest={"status": "BLOCK"},
            cache_admitted=True,
        )

        self.assertEqual(frozen["status"], "PASS")
        self.assertEqual(len(frozen["lineage_hash"]), 64)
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("blocked_market_history_cache_admitted", blocked["blockers"])

    def test_backtest_excludes_blocked_cache_and_binds_only_fresh_rows(self) -> None:
        poisoned = candle(0, close=77.0)
        fresh = candle(1, close=101.0)
        with (
            patch.object(server, "read_local_btc_daily", return_value={"rows": []}),
            patch.object(
                server,
                "read_market_history_cache",
                return_value={
                    "status": "BLOCK",
                    "rows": [poisoned],
                    "manifest": {"status": "BLOCK", "invalid_count": 1},
                    "path": "fixture.sqlite",
                },
            ),
            patch.object(server, "fetch_okx_daily_history", return_value=[fresh]),
            patch.object(server, "upsert_market_history_cache", return_value=1),
        ):
            result = server.backtest_market_rows(
                "BTC-USDT", 1, dataset_lineage_id="matrix:g49:BTC-USDT"
            )

        self.assertEqual([row["close"] for row in result["rows"]], [101.0])
        self.assertIn("blocked market history cache was excluded", result["warning"])
        self.assertEqual(result["market_history_evidence"]["status"], "PASS")
        self.assertFalse(result["market_history_evidence"]["cache_admitted"])

    def test_backtest_uses_completed_local_row_without_repeated_refresh(self) -> None:
        complete = candle(0)
        incomplete = candle(1, close=102.0, complete=False)
        with (
            patch.object(
                server,
                "read_local_btc_daily",
                return_value={"rows": [complete, incomplete], "source": "local_sqlite"},
            ),
            patch.object(
                server,
                "read_market_history_cache",
                return_value={"status": "MISSING", "rows": [], "manifest": {}},
            ),
            patch.object(server, "now_ms", return_value=int(BASE_DATE.timestamp() * 1000) + 86_400_000),
            patch.object(server, "fetch_okx_daily_history") as fetch_history,
        ):
            result = server.backtest_market_rows(
                "BTC-USDT", 1, dataset_lineage_id="matrix:g49:BTC-USDT"
            )

        fetch_history.assert_not_called()
        self.assertEqual(len(result["rows"]), 1)
        self.assertTrue(result["rows"][0]["complete"])
        self.assertEqual(result["rows"][0]["date"], complete["date"])

    def test_merge_never_allows_incomplete_row_to_hide_completed_row(self) -> None:
        complete = candle(0, close=101.0)
        incomplete = candle(0, close=88.0, complete=False)

        merged = server.merge_backtest_history([complete], [incomplete], limit=10)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["close"], 101.0)
        self.assertTrue(merged[0]["complete"])

    def test_cache_status_marks_invalid_external_history_as_blocked(self) -> None:
        invalid = {**candle(1), "close": math.nan}
        empty_stats = {
            "symbol": "BTC-USDT",
            "rows": 0,
            "complete_rows": 0,
            "incomplete_rows": 0,
            "invalid_rows": 0,
            "first": "",
            "last": "",
            "fetched_at": 0,
            "source": "missing",
            "sources": [],
            "data_hash": "",
            "status": "MISSING",
        }
        with (
            patch.object(server, "history_cache_symbols", return_value=["BTC-USDT"]),
            patch.object(server, "market_history_cache_stats", return_value=empty_stats),
            patch.object(
                server,
                "read_local_btc_daily",
                return_value={"rows": [candle(0), invalid], "source": "local_sqlite"},
            ),
            patch.object(
                server,
                "read_market_history_cache",
                return_value={"status": "MISSING", "rows": []},
            ),
            patch.object(server, "now_ms", return_value=int(BASE_DATE.timestamp() * 1000)),
        ):
            status = server.market_history_cache_status()

        self.assertEqual(status["rows"][0]["status"], "BLOCK")
        self.assertEqual(status["rows"][0]["priority"], "P0")
        self.assertEqual(status["rows"][0]["invalid_rows"], 1)
        self.assertIn("BLOCK 1", status["summary"])


if __name__ == "__main__":
    unittest.main()
