"""Synthetic SQLite fixtures only; no real runtime, broker, provider or model."""
from hashlib import sha256
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("terminal_market_data_under_test",
    Path(__file__).parents[1] / "exchange_terminal/services/terminal_market_data.py")
market = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(market)


class TerminalMarketDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def database(self, kind="crypto", rows=None, *, completion=True, path=None):
        names = {"crypto": ("market_history_cache.sqlite", "market_daily_candles", "complete"),
                 "stock": ("stock_candles_cache.sqlite", "stock_candles", "complete"),
                 "btc": ("jiaoyiguowangshuju/btc_daily_prices.sqlite", "btc_daily_prices", "confirmed")}
        name, table, complete_field = names[kind]
        path = path or self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        fields = ["symbol TEXT", "trading_date TEXT", "ts_ms INTEGER", "open REAL", "high REAL", "low REAL", "close REAL", "volume REAL", "source TEXT"]
        columns = [f.split()[0] for f in fields]
        if completion:
            fields.append(complete_field + " INTEGER")
            columns.append(complete_field)
        if kind == "stock":
            fields.extend(["interval TEXT", "query_session TEXT", "fetched_at INTEGER"])
            columns.extend(["interval", "query_session", "fetched_at"])
        if kind == "crypto":
            fields.append("fetched_at INTEGER")
            columns.append("fetched_at")
        connection.execute("CREATE TABLE " + table + " (" + ",".join(fields) + ")")
        for index, row in enumerate(rows if rows is not None else [{}]):
            payload = {"symbol": "AAPL" if kind == "stock" else "BTC-USDT", "trading_date": f"2024-01-{index+2:02d}",
                       "ts_ms": 1704153600000 + index * 86400000, "open": 10, "high": 12, "low": 9, "close": 11,
                       "volume": 100, "source": "futu" if kind == "stock" else "okx_history_candles",
                       complete_field: 1, "interval": "1d", "query_session": "regular", "fetched_at": 1705000000000, **row}
            connection.execute("INSERT INTO " + table + " (" + ",".join(columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")",
                               [payload[c] for c in columns])
        connection.commit()
        connection.close()
        return path

    def read(self, symbol="BTC-USDT", **kwargs):
        return market.TerminalMarketReader(self.root)(symbol, **kwargs)

    def test_completed_crypto_cache_is_review_not_authenticated(self):
        self.database(rows=[{}, {"complete": 0}, {"complete": None}, {"complete": "false"}])
        result = self.read()
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["excluded_incomplete_count"], 3)
        self.assertEqual(result["meta"]["unknown_completion_count"], 1)
        self.assertEqual(result["quality"]["status"], "REVIEW")
        self.assertFalse(result["quality"]["source_authenticated"])
        self.assertFalse(result["quality"]["core_us_equity_import_allowed"])
        self.assertFalse(result["quality"]["order_allowed"])
        self.assertTrue(result["rows"][0]["complete"])
        self.assertFalse(result["rows"][0]["provisional"])

    def test_stock_selection_never_mixes_provider_groups_or_adjustment_basis(self):
        self.database("stock", [{"source": "futu"}, {"source": "yahoo_adjusted"}, {"source": "futu"}])
        result = self.read("AAPL")
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual({r["source"] for r in result["rows"]}, {"futu"})
        self.assertEqual(result["meta"]["source_lineage"], ["futu"])
        self.assertEqual(result["meta"]["price_basis"], "FORWARD_ADJUSTED_QFQ")
        self.assertFalse(result["quality"]["core_us_equity_import_allowed"])

    def test_btc_original_database_is_selected_without_generic_merge(self):
        self.database("btc", [{"source": "okx"}, {"source": "okx", "confirmed": 0}])
        self.database("crypto", [{"close": 10.5}])
        result = self.read()
        self.assertEqual(result["meta"]["origin_reference"], "runtime/jiaoyiguowangshuju/btc_daily_prices.sqlite")
        self.assertEqual(result["meta"]["completion_evidence_field"], "confirmed")
        self.assertEqual(result["excluded_incomplete_count"], 1)
        self.assertEqual(result["rows"][0]["source"], "okx")

    def test_existing_btc_runtime_cache_fallback_is_explicit(self):
        self.database("btc", path=self.root / "btc_daily_prices_cache.sqlite")
        result = self.read()
        self.assertEqual(result["meta"]["origin_reference"], "runtime/btc_daily_prices_cache.sqlite")
        self.assertEqual(result["quality"]["status"], "REVIEW")

    def test_nonempty_wal_blocks_before_sqlite_open_and_does_not_fallback(self):
        db = self.database("btc")
        self.database("crypto")
        Path(str(db) + "-wal").write_bytes(b"pending state")
        with patch.object(market.sqlite3, "connect", side_effect=AssertionError("must not open")):
            result = self.read()
        self.assertEqual(result["quality"]["status"], "BLOCK")
        self.assertIn("DATABASE_PENDING_JOURNAL", result["quality"]["blockers"])
        self.assertEqual(result["rows"], [])

    def test_rollback_journal_also_blocks(self):
        db = self.database("stock")
        Path(str(db) + "-journal").write_bytes(b"pending rollback")
        result = self.read("AAPL")
        self.assertEqual(result["quality"]["blockers"], ["DATABASE_PENDING_JOURNAL"])

    def test_missing_completion_column_is_not_repaired_or_assumed_complete(self):
        db = self.database(completion=False)
        before = db.read_bytes()
        result = self.read()
        self.assertEqual(result["quality"]["blockers"], ["COMPLETION_EVIDENCE_COLUMN_MISSING"])
        self.assertEqual(db.read_bytes(), before)

    def test_missing_or_unknown_completion_is_excluded_not_promoted(self):
        self.database(rows=[{"complete": None}, {"complete": "not known"}])
        result = self.read()
        self.assertEqual(result["quality"]["status"], "BLOCK")
        self.assertEqual(result["excluded_incomplete_count"], 2)
        self.assertEqual(result["meta"]["unknown_completion_count"], 2)

    def test_invalid_ohlcv_and_duplicate_dates_block_without_silent_repair(self):
        self.database(rows=[{}, {"high": 1}, {"trading_date": "2024-01-02"}])
        result = self.read()
        self.assertEqual(result["quality"]["status"], "BLOCK")
        self.assertIn("INVALID_DAILY_ROWS_PRESENT", result["quality"]["blockers"])
        self.assertIn("DAILY_DATES_OR_TIMESTAMPS_NOT_UNIQUE_ORDERED", result["quality"]["blockers"])
        self.assertEqual(result["rows"], [])

    def test_nonfinite_prices_are_blocked(self):
        self.database(rows=[{"close": float("inf"), "high": float("inf")}])
        result = self.read()
        self.assertIn("INVALID_DAILY_ROWS_PRESENT", result["quality"]["blockers"])

    def test_limit_is_bounded_and_changes_selected_snapshot_identity(self):
        self.database(rows=[{}, {}, {}, {}])
        self.assertEqual(len(self.read(limit=2)["rows"]), 2)
        self.assertNotEqual(self.read(limit=2)["digest"], self.read(limit=3)["digest"])
        for value in (0, -1, 5001, True, 1.5, "2"):
            with self.assertRaisesRegex(ValueError, "limit_must_be"):
                self.read(limit=value)

    def test_symbol_injection_is_rejected_before_any_sql(self):
        with patch.object(market.sqlite3, "connect", side_effect=AssertionError("must not open")):
            for symbol in ("BTC-USDT' OR 1=1 --", "../AAPL", "AAPL;DROP", "", "A" * 41):
                with self.assertRaisesRegex(ValueError, "symbol_invalid"):
                    self.read(symbol)

    def test_digest_ignores_read_clock_but_includes_database_file_identity(self):
        db = self.database(rows=[{}])
        one = market.TerminalMarketReader(self.root, now_ms=lambda: 1)("BTC-USDT")
        two = market.TerminalMarketReader(self.root, now_ms=lambda: 9999999999999)("BTC-USDT")
        self.assertEqual(one["digest"], two["digest"])
        self.assertEqual(one["meta"]["file_identity"]["sha256"], sha256(db.read_bytes()).hexdigest())
        connection = sqlite3.connect(db)
        connection.execute("UPDATE market_daily_candles SET fetched_at=fetched_at+1")
        connection.commit();connection.close()
        self.assertNotEqual(one["digest"], self.read()["digest"])

    def test_catalog_is_local_deduplicated_and_does_not_touch_database_bytes(self):
        crypto = self.database(rows=[{}, {"symbol": "ETH-USDT"}])
        stock = self.database("stock", [{}, {"symbol": "HK.00700"}, {"interval": "1m", "symbol": "MSFT"}])
        btc = self.database("btc")
        before = {p.relative_to(self.root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        reader = market.TerminalMarketReader(self.root)
        self.assertEqual(reader.list_symbols(), ["AAPL", "BTC-USDT", "ETH-USDT", "HK.00700"])
        self.assertEqual(next(row for row in reader.catalog()["items"] if row["symbol"] == "HK.00700")["asset_class"], "HK_EQUITY")
        reader("AAPL");reader("BTC-USDT")
        after = {p.relative_to(self.root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_preview_seed_source_is_blocked_not_relabelled(self):
        self.database("stock", [{"source": "offline-seed"}])
        result = self.read("AAPL")
        self.assertIn("PREVIEW_OR_SYNTHETIC_SOURCE_NOT_MARKET_HISTORY", result["quality"]["blockers"])
        self.assertEqual(result["meta"]["source_lineage"], ["offline-seed"])

    def test_metadata_movement_during_read_is_blocked(self):
        db = self.database()
        original = market._state(db)
        changed = ((1, 2, 3, 4, 5), None, None)
        with patch.object(market, "_state", side_effect=[original, changed]):
            result = market.TerminalMarketReader(self.root, btc_paths=[])("BTC-USDT")
        self.assertEqual(result["quality"]["blockers"], ["DATABASE_CHANGED_DURING_READ"])

    def test_missing_provider_is_not_invented(self):
        self.database(rows=[{"source": ""}])
        result = self.read()
        self.assertEqual(result["quality"]["blockers"], ["SOURCE_LINEAGE_INVALID"])
        self.assertEqual(result["rows"], [])

    def test_explicit_stock_source_selects_exact_group_without_fallback_or_mix(self):
        self.database("stock", [{"source": "futu"}, {"source": "yahoo_adjusted"}, {"source": "futu"}])
        reader = market.TerminalMarketReader(self.root)
        initial = reader("AAPL")
        choices = initial["available_sources"]
        self.assertEqual(len(choices), 2)
        yahoo = next(row for row in choices if row["provider"] == "yahoo_adjusted")
        selected = reader("AAPL", source_id=yahoo["source_id"])
        self.assertEqual(selected["source_id"], yahoo["source_id"])
        self.assertEqual({r["source"] for r in selected["rows"]}, {"yahoo_adjusted"})
        self.assertEqual(selected["meta"]["price_basis"], "FORWARD_ADJUSTED_TOTAL_RETURN")
        self.assertEqual(selected["meta"]["session"], "regular")
        self.assertEqual(yahoo["coverage"]["row_count"], 1)
        self.assertNotEqual(selected["digest"], initial["digest"])

    def test_unknown_source_id_blocks_instead_of_using_default(self):
        self.database("stock")
        reader = market.TerminalMarketReader(self.root)
        result = reader("AAPL", source_id="terminal-cache:" + "0" * 64)
        self.assertEqual(result["quality"]["blockers"], ["REQUESTED_SOURCE_UNAVAILABLE"])
        self.assertEqual(result["rows"], [])
        self.assertEqual(len(result["available_sources"]), 1)
        self.assertEqual(reader("AAPL", source_id="untrusted arbitrary path")["quality"]["blockers"], ["SOURCE_SELECTION_INVALID"])

    def test_btc_primary_stays_default_but_generic_source_can_be_explicit(self):
        self.database("btc", [{"source": "okx"}])
        self.database("crypto", [{"source": "okx_history_candles"}])
        reader = market.TerminalMarketReader(self.root)
        primary = reader("BTC-USDT")
        self.assertEqual(primary["meta"]["origin_reference"], "runtime/jiaoyiguowangshuju/btc_daily_prices.sqlite")
        generic = next(row for row in primary["available_sources"] if row["source_reference"] == "runtime/market_history_cache.sqlite")
        selected = reader("BTC-USDT", source_id=generic["source_id"])
        self.assertEqual(selected["meta"]["origin_reference"], "runtime/market_history_cache.sqlite")
        self.assertEqual(selected["rows"][0]["source"], "okx_history_candles")

    def test_other_database_change_does_not_change_chosen_snapshot_digest(self):
        self.database("btc", [{"source": "okx"}])
        other = self.database("crypto")
        reader = market.TerminalMarketReader(self.root)
        first = reader("BTC-USDT")
        connection = sqlite3.connect(other)
        connection.execute("UPDATE market_daily_candles SET fetched_at=fetched_at+100")
        connection.commit();connection.close()
        second = reader("BTC-USDT")
        self.assertEqual(first["digest"], second["digest"])
        self.assertEqual(first["source_id"], second["source_id"])

    def test_incomplete_selected_group_never_falls_back_to_completed_default(self):
        self.database("stock", [{"source": "futu"}, {"source": "yahoo_adjusted", "complete": 0}])
        reader = market.TerminalMarketReader(self.root)
        choice = next(row for row in reader.sources("AAPL") if row["provider"] == "yahoo_adjusted")
        result = reader("AAPL", source_id=choice["source_id"])
        self.assertEqual(result["quality"]["status"], "BLOCK")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["source_id"], choice["source_id"])
        self.assertEqual(result["excluded_incomplete_count"], 1)

    def test_marked_synthetic_or_preview_sources_block_but_plain_fixture_provider_is_unverified(self):
        self.database("stock", [{"source": name} for name in (
            "quick_preview", "quote_preview_seed", "offline-seed", "synthetic", "fixture-provider")])
        reader = market.TerminalMarketReader(self.root)
        for choice in reader.sources("AAPL"):
            with self.subTest(provider=choice["provider"]):
                result = reader("AAPL", source_id=choice["source_id"])
                self.assertEqual(result["meta"]["source_lineage"], [choice["provider"]])
                if choice["provider"] == "fixture-provider":
                    self.assertEqual(result["quality"]["status"], "REVIEW")
                    self.assertFalse(result["quality"]["source_authenticated"])
                else:
                    self.assertEqual(result["quality"]["status"], "BLOCK")
                    self.assertIn("PREVIEW_OR_SYNTHETIC_SOURCE_NOT_MARKET_HISTORY", result["quality"]["blockers"])


if __name__ == "__main__":
    unittest.main()
