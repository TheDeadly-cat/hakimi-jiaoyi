from __future__ import annotations

import os
import tempfile
import json
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.market_data import futu as futu_market
from exchange_terminal.market_data import futu_quotes, stock_candles, stock_candles_io
from exchange_terminal.market_data.provider_health import ProviderHealthRegistry, provider_health_for_scope
from exchange_terminal.services.market_data_service import MarketDataService
from exchange_terminal.services.stock_history_service import StockHistoryPrewarmService


class ProviderHealthTests(unittest.TestCase):
    def test_failure_circuit_and_recovery(self) -> None:
        clock = {"now": 1_000}
        registry = ProviderHealthRegistry(
            now_ms=lambda: clock["now"],
            failure_threshold=2,
            cooldown_ms=5_000,
        )

        registry.record("yahoo", "history", success=False, latency_ms=120, error="timeout", scope="AAPL")
        self.assertTrue(registry.allowed("yahoo", "history", "AAPL")[0])
        registry.record("yahoo", "history", success=False, latency_ms=140, error="timeout", scope="AAPL")
        allowed, retry_after_ms = registry.allowed("yahoo", "history", "AAPL")
        self.assertFalse(allowed)
        self.assertEqual(retry_after_ms, 5_000)

        clock["now"] += 5_001
        self.assertTrue(registry.allowed("yahoo", "history", "AAPL")[0])
        registry.record("yahoo", "history", success=True, latency_ms=80, scope="AAPL")
        provider = registry.snapshot(["yahoo"])["providers"]["yahoo"]
        self.assertEqual(provider["status"], "HEALTHY")
        self.assertEqual(provider["calls"], 3)
        self.assertEqual(provider["average_latency_ms"], 113.33)

    def test_scoped_health_ignores_unrelated_symbol_failure(self) -> None:
        registry = ProviderHealthRegistry(now_ms=lambda: 1_000)
        registry.record("yahoo", "history", success=True, latency_ms=80, scope="MSFT|15m|regular")
        registry.record("yahoo", "history", success=False, latency_ms=120, error="404", scope="PSTG|1d|regular")
        snapshot = registry.snapshot(["yahoo"])

        current = provider_health_for_scope(snapshot, "yahoo", "history", "MSFT|15m|regular")

        self.assertEqual(snapshot["providers"]["yahoo"]["status"], "DEGRADED")
        self.assertEqual(current["status"], "HEALTHY")
        self.assertEqual(current["scope"], "MSFT|15M|REGULAR")


class FutuRuntimeTests(unittest.TestCase):
    def test_futu_sdk_import_uses_runtime_appdata_and_restores_environment(self) -> None:
        original_import = __import__
        sentinel = object()
        observed: dict[str, str] = {}

        def controlled_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "futu":
                observed["appdata"] = str(os.environ.get("appdata") or "")
                return sentinel
            return original_import(name, globals, locals, fromlist, level)

        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_appdata = Path(temp_dir) / "futu-appdata"
            with patch.dict(os.environ, {"FUTU_PY_APPDATA": str(runtime_appdata)}, clear=False):
                previous_appdata = os.environ.get("appdata")
                with patch("builtins.__import__", side_effect=controlled_import):
                    loaded, message = futu_market.import_futu_sdk()
                restored_appdata = os.environ.get("appdata")

            self.assertIs(loaded, sentinel)
            self.assertEqual(message, "futu-api installed")
            self.assertEqual(Path(observed["appdata"]), runtime_appdata)
            self.assertTrue(runtime_appdata.exists())
            self.assertEqual(restored_appdata, previous_appdata)


class StockCandleCoverageTests(unittest.TestCase):
    def test_futu_history_reads_later_pages_before_taking_latest_limit(self) -> None:
        class Frame:
            def __init__(self, records: list[dict[str, object]]) -> None:
                self.records = records

            def to_dict(self, orientation: str) -> list[dict[str, object]]:
                self.assert_orientation = orientation
                return self.records

        class QuoteContext:
            def __init__(self, **_kwargs: object) -> None:
                self.calls: list[object] = []

            def request_history_kline(self, _code: str, **kwargs: object) -> tuple[int, Frame, object]:
                page_key = kwargs.get("page_req_key")
                self.calls.append(page_key)
                if page_key is None:
                    return 0, Frame([
                        {"time_key": "2026-07-28", "open": 98, "high": 101, "low": 97, "close": 100, "volume": 10},
                        {"time_key": "2026-07-29", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 11},
                    ]), "page-2"
                return 0, Frame([
                    {"time_key": "2026-07-30", "open": 101, "high": 103, "low": 100, "close": 102, "volume": 12},
                    {"time_key": "2026-07-31", "open": 102, "high": 104, "low": 101, "close": 103, "volume": 13},
                ]), None

            def close(self) -> None:
                return None

        class Futu:
            RET_OK = 0
            OpenQuoteContext = QuoteContext

        with (
            patch.object(futu_quotes, "futu_status_snapshot", return_value={"opend_online": True}),
            patch.object(futu_quotes, "import_futu_sdk", return_value=(Futu, "")),
            patch.object(futu_quotes, "provider_call_allowed", return_value=(True, 0)),
            patch.object(futu_quotes, "record_provider_call"),
            patch.object(futu_quotes, "futu_history_window", return_value=("2026-07-01", "2026-08-01")),
            patch.object(futu_quotes, "stock_candle_stale_warning", return_value=""),
        ):
            result = futu_quotes.read_futu_stock_candles("AAPL", limit=3, interval="1d", session="all")

        self.assertTrue(result["ok"])
        self.assertEqual([row["date"] for row in result["rows"]], ["2026-07-29", "2026-07-30", "2026-07-31"])
        self.assertTrue(all(row["complete"] is True for row in result["rows"]))

    def test_stock_completion_contract_is_causal_for_daily_and_intraday_rows(self) -> None:
        timezone = stock_candles.stock_timezone("AAPL")
        daily_ts = int(datetime(2026, 8, 3, 9, 30, tzinfo=timezone).timestamp() * 1000)
        before_close = int(datetime(2026, 8, 3, 15, 59, tzinfo=timezone).timestamp() * 1000)
        after_buffer = int(datetime(2026, 8, 3, 16, 20, tzinfo=timezone).timestamp() * 1000)
        intraday_ts = int(datetime(2026, 8, 3, 10, 0, tzinfo=timezone).timestamp() * 1000)

        self.assertFalse(stock_candles.stock_candle_complete_at(
            "AAPL", "1d", daily_ts, "2026-08-03", at_ms=before_close
        ))
        self.assertTrue(stock_candles.stock_candle_complete_at(
            "AAPL", "1d", daily_ts, "2026-08-03", at_ms=after_buffer
        ))
        self.assertFalse(stock_candles.stock_candle_complete_at(
            "AAPL", "15m", intraday_ts, "2026-08-03", at_ms=intraday_ts + 14 * 60_000
        ))
        self.assertTrue(stock_candles.stock_candle_complete_at(
            "AAPL", "15m", intraday_ts, "2026-08-03", at_ms=intraday_ts + 15 * 60_000
        ))

    def test_aggregate_stock_rows_requires_every_child_to_be_complete(self) -> None:
        rows = [
            {"ts": 0, "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 10, "complete": True},
            {"ts": 60_000, "open": 100.5, "high": 102, "low": 100, "close": 101.5, "volume": 12, "complete": False},
        ]

        aggregated = stock_candles.aggregate_stock_rows(rows, 5 * 60_000)

        self.assertEqual(len(aggregated), 1)
        self.assertIs(aggregated[0]["complete"], False)
        self.assertIs(aggregated[0]["provisional"], True)

    def test_sqlite_cache_preserves_incomplete_candle_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            rows = [{
                "ts": stamp,
                "date": "2026-08-01",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
                "session": "regular",
                "complete": False,
            }]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "all", rows, "futu")
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "all")

            self.assertIsNotNone(cached)
            self.assertFalse(bool(cached["rows"][0]["complete"]))

    def test_sqlite_cache_does_not_promote_string_false_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            rows = [{
                "ts": stamp,
                "date": "2026-08-01",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
                "session": "regular",
                "complete": "false",
            }]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "all", rows, "futu")
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "all")

            self.assertIsNotNone(cached)
            self.assertEqual(cached["rows"][0]["complete"], 0)

    def test_daily_cache_keeps_one_authoritative_row_per_trading_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            yahoo = [{
                "ts": stamp - 60_000,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
                "complete": True,
            }]
            futu = [{
                **yahoo[0],
                "ts": stamp,
                "close": 101.5,
                "complete": False,
            }]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "all", yahoo, "yahoo")
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "all", futu, "futu")
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "all")

            self.assertEqual(len(cached["rows"]), 1)
            self.assertEqual(cached["rows"][0]["source"], "futu")
            self.assertEqual(cached["rows"][0]["close"], 101.5)
            self.assertFalse(bool(cached["rows"][0]["complete"]))

    def test_daily_cache_rejects_lower_priority_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            futu = [{
                "ts": stamp,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101.5,
                "volume": 10,
                "complete": True,
            }]
            yahoo = [{**futu[0], "close": 90.0}]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", futu, "futu"), 1)
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", yahoo, "yahoo_adjusted"), 0)
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "regular")

            self.assertEqual(cached["rows"][0]["source"], "futu")
            self.assertEqual(cached["rows"][0]["close"], 101.5)

    def test_higher_priority_provider_cannot_rewrite_verified_completed_daily_vintage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            yahoo = [{
                "ts": stamp,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101.5,
                "volume": 10,
                "complete": True,
            }]
            futu = [{**yahoo[0], "close": 95.0}]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", yahoo, "yahoo_adjusted"), 1)
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", futu, "futu"), 0)
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "regular")

            self.assertEqual(cached["rows"][0]["source"], "yahoo_adjusted")
            self.assertEqual(cached["rows"][0]["close"], 101.5)

    def test_adjusted_yahoo_replaces_unverified_yahoo_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            row = {
                "ts": stamp,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
                "complete": True,
            }
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", [row], "yahoo")
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", [{**row, "close": 100.5}], "yahoo_adjusted")
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "regular")

            self.assertEqual(cached["rows"][0]["source"], "yahoo_adjusted")
            self.assertEqual(cached["adjustment_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
            self.assertEqual(cached["corporate_action_coverage"], "EMBEDDED_PROVIDER_CONTRACT")

    def test_completed_daily_row_is_immutable_for_same_source_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            row = {
                "ts": stamp,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 10,
                "complete": True,
            }
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", [row], "yahoo_adjusted"), 1)
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", [{**row, "close": 99}], "yahoo_adjusted"), 0)
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "regular")

            self.assertEqual(cached["rows"][0]["close"], 101)

    def test_adjusted_daily_append_is_chain_linked_to_the_frozen_cache_vintage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            original = [
                {
                    "ts": stamp + index * 86_400_000,
                    "date": f"2026-07-{27 + index:02d}",
                    "open": close - 1,
                    "high": close + 1,
                    "low": close - 2,
                    "close": close,
                    "volume": 1_000,
                    "complete": True,
                }
                for index, close in enumerate((100.0, 101.0, 102.0))
            ]
            rebased = [
                {**original[1], "open": 99.0, "high": 101.0, "low": 98.0, "close": 99.99},
                {**original[2], "open": 99.99, "high": 101.97, "low": 99.0, "close": 100.98},
                {
                    "ts": stamp + 3 * 86_400_000,
                    "date": "2026-07-30",
                    "open": 101.0,
                    "high": 103.0,
                    "low": 100.0,
                    "close": 102.0,
                    "volume": 1_100,
                    "complete": True,
                },
            ]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", original, "yahoo_adjusted")
                prepared = stock_candles_io.prepare_stock_candle_cache_rows(
                    "AAPL", "1d", "regular", rebased, "yahoo_adjusted"
                )
                stock_candles_io.upsert_stock_candle_cache(
                    "AAPL", "1d", "regular", prepared["rows"], "yahoo_adjusted", prepared=True
                )
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 10, "1d", "regular")

            self.assertTrue(prepared["chain_linked"])
            self.assertEqual([row["close"] for row in cached["rows"][:3]], [100.0, 101.0, 102.0])
            self.assertAlmostEqual(cached["rows"][3]["close"], 103.0303, places=4)
            self.assertAlmostEqual(
                cached["rows"][3]["close"] * cached["rows"][3]["volume"],
                102.0 * 1_100.0,
                places=2,
            )

    def test_legacy_yahoo_adjusted_volume_migration_preserves_frozen_ohlc_vintage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            legacy = [
                {
                    "ts": stamp + index * 86_400_000,
                    "date": f"2026-07-{27 + index:02d}",
                    "open": close - 1,
                    "high": close + 1,
                    "low": close - 2,
                    "close": close,
                    "volume": 1_000.0,
                    "complete": True,
                }
                for index, close in enumerate((90.0, 92.0, 94.0))
            ]
            refreshed = [
                {
                    **row,
                    "open": row["open"] / 2,
                    "high": row["high"] / 2,
                    "low": row["low"] / 2,
                    "close": row["close"] / 2,
                    "volume": 2_200.0 + index * 200.0,
                    "source": "yahoo_adjusted",
                }
                for index, row in enumerate(legacy)
            ]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache(
                    "AAPL", "1d", "regular", legacy, "yahoo_adjusted"
                )
                migrated = stock_candles_io.migrate_legacy_yahoo_adjusted_volume_cache(
                    "AAPL", refreshed
                )
                repeated = stock_candles_io.migrate_legacy_yahoo_adjusted_volume_cache(
                    "AAPL", refreshed
                )
                cached = stock_candles_io.read_stock_persistent_candle_cache(
                    "AAPL", 10, "1d", "regular"
                )

            self.assertEqual(migrated["status"], "PASS")
            self.assertEqual(migrated["updated_rows"], 3)
            self.assertAlmostEqual(migrated["price_scale"], 2.0)
            self.assertNotEqual(migrated["before_hash"], migrated["after_hash"])
            self.assertEqual(repeated["status"], "ALREADY_APPLIED")
            self.assertEqual([row["close"] for row in cached["rows"]], [90.0, 92.0, 94.0])
            self.assertEqual([row["volume"] for row in cached["rows"]], [1_100.0, 1_200.0, 1_300.0])

    def test_legacy_yahoo_adjusted_volume_migration_rejects_nonuniform_price_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            legacy = [
                {
                    "ts": stamp + index * 86_400_000,
                    "date": f"2026-07-{29 + index:02d}",
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": 1_000.0,
                    "complete": True,
                }
                for index, close in enumerate((90.0, 100.0))
            ]
            refreshed = [
                {**legacy[0], "close": 45.0, "volume": 2_000.0, "source": "yahoo_adjusted"},
                {**legacy[1], "close": 60.0, "volume": 2_000.0, "source": "yahoo_adjusted"},
            ]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "stock_payload_needs_session_refresh", return_value=False),
                patch.object(stock_candles_io, "stock_candle_stale_warning", return_value=""),
            ):
                stock_candles_io.upsert_stock_candle_cache(
                    "AAPL", "1d", "regular", legacy, "yahoo_adjusted"
                )
                migrated = stock_candles_io.migrate_legacy_yahoo_adjusted_volume_cache(
                    "AAPL", refreshed
                )
                cached = stock_candles_io.read_stock_persistent_candle_cache(
                    "AAPL", 10, "1d", "regular"
                )

            self.assertEqual(migrated["status"], "BLOCK")
            self.assertEqual(migrated["blockers"], ["daily_adjustment_vintage_overlap_is_not_uniform"])
            self.assertEqual([row["volume"] for row in cached["rows"]], [1_000.0, 1_000.0])

    def test_non_uniform_adjusted_history_revision_is_rejected_before_append(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            original = [
                {
                    "ts": stamp + index * 86_400_000,
                    "date": f"2026-07-{27 + index:02d}",
                    "open": close,
                    "high": close + 1,
                    "low": close - 1,
                    "close": close,
                    "volume": 1_000,
                    "complete": True,
                }
                for index, close in enumerate((100.0, 101.0, 102.0))
            ]
            revised = [
                {**original[1], "close": 90.0},
                {**original[2], "close": 100.0},
                {**original[2], "ts": stamp + 3 * 86_400_000, "date": "2026-07-30", "close": 103.0},
            ]
            with patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", original, "futu")
                with self.assertRaisesRegex(ValueError, "overlap_is_not_uniform"):
                    stock_candles_io.prepare_stock_candle_cache_rows(
                        "AAPL", "1d", "regular", revised, "futu"
                    )

    def test_yahoo_daily_ohlc_uses_adjusted_close_ratio(self) -> None:
        payload = {
            "chart": {
                "result": [{
                    "timestamp": [1_735_689_600],
                    "indicators": {
                        "quote": [{
                            "open": [95.0],
                            "high": [105.0],
                            "low": [90.0],
                            "close": [100.0],
                            "volume": [1_000.0],
                        }],
                        "adjclose": [{"adjclose": [90.0]}],
                    },
                    "events": {},
                }],
            },
        }

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        with patch.object(stock_candles_io.urllib.request, "urlopen", return_value=Response()):
            result = stock_candles_io.fetch_yahoo_stock_candles("AAPL", 10, "1d", "5y")

        self.assertTrue(result["ok"])
        self.assertEqual(result["cache_source"], "yahoo_adjusted")
        self.assertEqual(result["adjustment_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertAlmostEqual(result["rows"][0]["open"], 85.5)
        self.assertAlmostEqual(result["rows"][0]["close"], 90.0)
        self.assertAlmostEqual(result["rows"][0]["volume"], 1_000.0 / 0.9)
        self.assertAlmostEqual(
            result["rows"][0]["close"] * result["rows"][0]["volume"],
            100.0 * 1_000.0,
        )
        self.assertEqual(result["rows"][0]["source"], "yahoo_adjusted")
        self.assertIs(result["rows"][0]["complete"], True)

    def test_incomplete_provider_response_cannot_poison_revision_ledger(self) -> None:
        primary = stock_candles_io.build_market_data_snapshot(
            symbol="AAPL",
            provider="futu",
            rows=[{
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 1_000,
                "complete": True,
            }],
            adjustment_basis="FORWARD_ADJUSTED_QFQ",
        )
        ledger = Mock()
        ledger.latest_snapshot.return_value = {
            "scope_key": "PROVIDER_OBSERVATION|AAPL|futu|1d|regular||",
            "state_status": "PASS",
            "blocking_event_hash": "",
            "updated_at": 1000,
            "snapshot": primary,
        }
        with (
            patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger),
            patch.object(stock_candles_io, "fetch_yahoo_stock_candles", return_value={
                "ok": True,
                "source": "yahoo",
                "rows": [{
                    "date": "2026-07-31",
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "volume": 1_000,
                }],
            }),
        ):
            result = stock_candles_io.audit_stock_daily_sources("AAPL")

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["blockers"], ["independent_yahoo_completed_rows_missing"])
        ledger.record_snapshot.assert_not_called()
        ledger.record_cross_source.assert_not_called()

    def test_source_audit_propagates_revision_review_status(self) -> None:
        row = {
            "date": "2026-07-31",
            "open": 100,
            "high": 102,
            "low": 99,
            "close": 101,
            "volume": 1_000,
            "complete": True,
        }
        primary = stock_candles_io.build_market_data_snapshot(
            symbol="AAPL",
            provider="futu",
            rows=[row],
            adjustment_basis="FORWARD_ADJUSTED_QFQ",
        )
        ledger = Mock()
        ledger.latest_snapshot.return_value = {
            "scope_key": "PROVIDER_OBSERVATION|AAPL|futu|1d|regular||",
            "state_status": "PASS",
            "blocking_event_hash": "",
            "updated_at": 1000,
            "snapshot": primary,
        }
        ledger.record_snapshot.return_value = {"status": "REVIEW", "classification": "CONTRACT_REVISION"}
        ledger.record_cross_source.side_effect = lambda evidence: {**evidence, "status": "PASS"}
        with (
            patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger),
            patch.object(stock_candles_io, "fetch_yahoo_stock_candles", return_value={
                "ok": True,
                "source": "yahoo",
                "rows": [{**row, "source": "yahoo_adjusted"}],
                "adjustment_basis": "FORWARD_ADJUSTED_TOTAL_RETURN",
            }),
        ):
            result = stock_candles_io.audit_stock_daily_sources("AAPL")

        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["secondary_revision"]["status"], "REVIEW")
        self.assertEqual(result["cross_source"]["status"], "PASS")

    def test_narrow_provider_window_cannot_replace_full_revision_snapshot(self) -> None:
        rows = [
            {
                "date": f"2026-07-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index in range(5)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = stock_candles_io.MarketDataRevisionLedger(Path(temp_dir) / "revisions.sqlite", lambda: 1000)
            with patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger):
                stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )
                narrowed = stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows[-2:],
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                    observation_scope="QUERY_WINDOW",
                )
                latest = ledger.latest_snapshot(symbol="AAPL", provider="futu")

        self.assertEqual(narrowed["classification"], "WINDOW_SUBSET_IGNORED")
        self.assertEqual(narrowed["status"], "REVIEW")
        self.assertEqual(narrowed["observed_window"]["row_count"], 2)
        self.assertEqual(latest["snapshot"]["row_count"], 5)

    def test_complete_unchanged_query_window_passes_without_inheriting_review(self) -> None:
        rows = [
            {
                "date": f"2026-07-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index in range(5)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = stock_candles_io.MarketDataRevisionLedger(Path(temp_dir) / "revisions.sqlite", lambda: 1000)
            with patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger):
                stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )
                unchanged = stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                    observation_scope="QUERY_WINDOW",
                )

        self.assertEqual(unchanged["classification"], "WINDOW_UNCHANGED")
        self.assertEqual(unchanged["status"], "PASS")
        self.assertEqual(unchanged["merged_history_row_count"], 5)

    def test_narrow_window_with_new_date_extends_full_revision_snapshot(self) -> None:
        rows = [
            {
                "date": f"2026-07-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index in range(5)
        ]
        appended = {
            **rows[-1],
            "date": "2026-07-25",
            "open": 105,
            "high": 107,
            "low": 104,
            "close": 106,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = stock_candles_io.MarketDataRevisionLedger(Path(temp_dir) / "revisions.sqlite", lambda: 1000)
            with patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger):
                stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )
                extended = stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=[*rows[-2:], appended],
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                    observation_scope="QUERY_WINDOW",
                )
                latest = ledger.latest_snapshot(symbol="AAPL", provider="futu")

        self.assertEqual(extended["classification"], "APPEND_ONLY")
        self.assertEqual(latest["snapshot"]["row_count"], 6)

    def test_authoritative_full_truncation_remains_blocked(self) -> None:
        rows = [
            {
                "date": f"2026-07-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index in range(5)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = stock_candles_io.MarketDataRevisionLedger(Path(temp_dir) / "revisions.sqlite", lambda: 1000)
            with patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger):
                stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )
                truncated = stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows[-2:],
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )

        self.assertEqual(truncated["status"], "BLOCK")
        self.assertEqual(truncated["classification"], "HISTORICAL_ROWS_REMOVED")
        self.assertIn("completed_rows_removed:3", truncated["blockers"])

    def test_query_window_can_enrich_contract_without_removing_known_history(self) -> None:
        rows = [
            {
                "date": f"2026-07-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index in range(5)
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = stock_candles_io.MarketDataRevisionLedger(Path(temp_dir) / "revisions.sqlite", lambda: 1000)
            with patch.object(stock_candles_io, "MARKET_DATA_REVISION_LEDGER", ledger):
                stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows,
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                )
                enriched = stock_candles_io.record_stock_revision_snapshot(
                    symbol="AAPL", provider="futu", rows=rows[-2:],
                    adjustment_basis="FORWARD_ADJUSTED_QFQ",
                    corporate_actions_hash="empty-actions-hash",
                    observation_scope="QUERY_WINDOW",
                )
                latest = ledger.latest_snapshot(symbol="AAPL", provider="futu")

        self.assertEqual(enriched["status"], "PASS")
        self.assertEqual(enriched["classification"], "CONTRACT_METADATA_ENRICHMENT")
        self.assertEqual(enriched["observed_window"]["row_count"], 2)
        self.assertEqual(enriched["merged_history_row_count"], 5)
        self.assertEqual(latest["snapshot"]["row_count"], 5)
        self.assertEqual(latest["snapshot"]["corporate_actions_hash"], "empty-actions-hash")

    def test_adjusted_yahoo_prices_are_canonical_at_sub_tick_precision(self) -> None:
        left = stock_candles_io._canonical_adjusted_price(222.44309097566543)
        right = stock_candles_io._canonical_adjusted_price(222.44310665442717)

        self.assertEqual(left, 222.4431)
        self.assertEqual(left, right)

    def test_sqlite_coverage_reports_range_sources_and_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            rows = [
                {"ts": 1_700_000_000_000, "date": "2023-11-14", "open": 100, "high": 103, "low": 99, "close": 102, "volume": 10, "session": "regular"},
                {"ts": 1_700_086_400_000, "date": "2023-11-15", "open": 102, "high": 104, "low": 101, "close": 103, "volume": 12, "session": "regular"},
            ]
            with patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path):
                self.assertEqual(stock_candles_io.upsert_stock_candle_cache("AAPL", "1d", "regular", rows, "futu"), 2)
                coverage = stock_candles_io.stock_candle_cache_coverage("AAPL", "1d", "regular")

            self.assertTrue(coverage["available"])
            self.assertEqual(coverage["row_count"], 2)
            self.assertEqual(coverage["first_date"], "2023-11-14")
            self.assertEqual(coverage["latest_date"], "2023-11-15")
            self.assertEqual(coverage["source_counts"], {"futu": 2})
            self.assertEqual(coverage["session_counts"], {"regular": 2})

    def test_sqlite_all_session_cache_can_serve_session_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            rows = [
                {"ts": stamp - 120_000, "date": "2026-08-01", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 10, "session": "pre"},
                {"ts": stamp - 60_000, "date": "2026-08-01", "open": 101, "high": 102, "low": 100, "close": 101.5, "volume": 12, "session": "regular"},
            ]
            with patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1m", "all", rows, "yahoo")
                cached = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 100, "1m", "pre")

            self.assertIsNotNone(cached)
            self.assertEqual(cached["derived_from_session"], "all")
            self.assertEqual(len(cached["rows"]), 1)
            self.assertEqual(cached["rows"][0]["session"], "pre")

    def test_intraday_history_older_than_five_days_is_rejected(self) -> None:
        day_ms = 24 * 60 * 60 * 1000
        latest = 2_000_000_000_000
        rows = [{"ts": latest, "close": 100}]

        with patch.object(stock_candles, "now_ms", return_value=latest + 4 * day_ms):
            self.assertEqual(stock_candles.stock_candle_stale_warning(rows, "1m", "AAPL"), "")
        with patch.object(stock_candles, "now_ms", return_value=latest + 6 * day_ms):
            self.assertIn("stale stock candles", stock_candles.stock_candle_stale_warning(rows, "1m", "AAPL"))

    def test_completed_regular_session_cache_does_not_expire_every_45_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock-candles.sqlite3"
            stamp = int(time.time() * 1000)
            rows = [{
                "ts": stamp - 2 * 60 * 60 * 1000,
                "date": "2026-08-01",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
                "volume": 10,
                "session": "regular",
            }]
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp - 120_000),
            ):
                stock_candles_io.upsert_stock_candle_cache("AAPL", "1m", "regular", rows, "yahoo")
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_session_from_ts", return_value="post"),
            ):
                completed = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 100, "1m", "regular")
            with (
                patch.object(stock_candles_io, "STOCK_CANDLE_CACHE_DB", db_path),
                patch.object(stock_candles_io, "now_ms", return_value=stamp),
                patch.object(stock_candles_io, "stock_session_from_ts", return_value="regular"),
            ):
                live = stock_candles_io.read_stock_persistent_candle_cache("AAPL", 100, "1m", "regular")

            self.assertEqual(completed["warning"], "")
            self.assertEqual(live["warning"], "stale stock cache")


class MarketSessionSnapshotTests(unittest.TestCase):
    @staticmethod
    def _service(quote: dict) -> MarketDataService:
        return MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: quote,
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "正常盘"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [{"ts": 99_000, "open": 100, "high": 104, "low": 99, "close": 103, "volume": 10}],
                "source": "futu",
                "realtime": True,
                "fallback": False,
            },
            okx_first=lambda *_args: {},
        )

    @staticmethod
    def _after_hours_quote() -> dict:
        return {
            "source": "futu",
            "status": "ONLINE",
            "last": 103,
            "ts": 99_000,
            "market_session": {
                "provider_confirmed": True,
                "phase": "post",
                "status": "LIVE_SESSION",
                "analysis_ready": True,
                "execution_eligible": False,
                "active_session": "post",
                "active_price": 102.5,
            },
        }

    def test_regular_chart_during_after_hours_is_ready_last_session(self) -> None:
        snapshot = self._service(self._after_hours_quote()).snapshot("AAPL", bar="1d", session="regular")

        self.assertEqual(snapshot["data_quality"]["status"], "READY")
        self.assertFalse(snapshot["data_quality"]["realtime"])
        self.assertEqual(snapshot["market_session"]["session_relation"], "LAST_SESSION")

    def test_after_hours_quote_cannot_increase_paper_risk(self) -> None:
        context = self._service(self._after_hours_quote()).execution_context("AAPL", requested_price=103)

        self.assertFalse(context["data_quality"]["can_increase_risk"])
        self.assertTrue(any("正常盘" in reason for reason in context["data_quality"]["blocking_reasons"]))


class StockHistoryPrewarmTests(unittest.TestCase):
    def test_preview_seed_is_never_marked_ready(self) -> None:
        service = StockHistoryPrewarmService(
            read_candles=lambda *_args, **_kwargs: {
                "ok": True,
                "source": "offline-seed",
                "rows": [{"date": "2026-07-31", "close": 100}],
                "warning": "offline seed, not live market data",
            },
            cache_coverage=lambda *_args: {"available": False, "row_count": 0},
            futu_status=lambda *_args: {"opend_online": False},
            max_workers=1,
        )
        try:
            service.start(["PSTG"])
            deadline = time.time() + 2
            status = service.status()
            while status["counts"]["ERROR"] < 1 and time.time() < deadline:
                time.sleep(0.01)
                status = service.status()
            self.assertEqual(status["counts"]["ERROR"], 1)
            self.assertIn("offline seed", status["jobs"][0]["error"])
        finally:
            service.shutdown(wait=True)

    def test_external_provider_can_prewarm_while_futu_is_offline(self) -> None:
        service = StockHistoryPrewarmService(
            read_candles=lambda *_args, **_kwargs: {
                "ok": True,
                "source": "yahoo",
                "rows": [{"date": "2026-07-31", "close": 100}],
            },
            cache_coverage=lambda *_args: {"available": False, "row_count": 0},
            futu_status=lambda *_args: {"opend_online": False},
            max_workers=1,
        )
        try:
            service.start(["AAPL"])
            deadline = time.time() + 2
            status = service.status()
            while status["counts"]["READY"] < 1 and time.time() < deadline:
                time.sleep(0.01)
                status = service.status()
            self.assertEqual(status["counts"]["READY"], 1)
            self.assertEqual(status["jobs"][0]["source"], "yahoo")
            self.assertFalse(status["jobs"][0]["futu_online"])
        finally:
            service.shutdown(wait=True)

    def test_complete_recent_coverage_skips_provider_call(self) -> None:
        calls: list[str] = []
        service = StockHistoryPrewarmService(
            read_candles=lambda symbol, *_args, **_kwargs: calls.append(symbol) or {"ok": True, "rows": []},
            cache_coverage=lambda symbol, *_args: {
                "available": True,
                "symbol": symbol,
                "row_count": 520,
                "latest_date": "2026-07-31",
                "data_age_ms": 60_000,
                "source_counts": {"futu": 520},
            },
            futu_status=lambda *_args: {"opend_online": True},
            max_workers=1,
        )
        try:
            started = service.start(["AAPL"], interval="1d", session="regular", limit=520)
            self.assertEqual(started["queued_now"], 0)
            self.assertEqual(started["skipped_now"], 1)
            self.assertEqual(started["counts"]["READY"], 1)
            self.assertTrue(started["jobs"][0]["cache_hit"])
            self.assertEqual(calls, [])
        finally:
            service.shutdown(wait=True)

    def test_queue_is_bounded_deduplicated_and_read_only(self) -> None:
        calls: list[str] = []

        def read_candles(symbol: str, *_args, **_kwargs) -> dict:
            calls.append(symbol)
            return {"ok": True, "source": "futu", "rows": [{"date": "2026-07-31", "close": 100}]}

        service = StockHistoryPrewarmService(
            read_candles=read_candles,
            cache_coverage=lambda symbol, *_args: {"row_count": 520, "latest_date": "2026-07-31", "symbol": symbol},
            futu_status=lambda *_args: {"opend_online": True},
            max_workers=2,
        )
        try:
            started = service.start(["AAPL", "NVDA", "AAPL"])
            self.assertEqual(started["queued_now"], 2)
            deadline = time.time() + 2
            status = service.status()
            while status["counts"]["READY"] < 2 and time.time() < deadline:
                time.sleep(0.01)
                status = service.status()
            self.assertEqual(status["counts"]["READY"], 2)
            self.assertEqual(sorted(calls), ["AAPL", "NVDA"])
            self.assertFalse(status["live_trading_allowed"])
            self.assertEqual(service.start(["AAPL"])["skipped_now"], 1)
        finally:
            service.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
