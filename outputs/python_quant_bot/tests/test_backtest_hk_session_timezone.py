from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from hakimi_research.stock_metadata import stock_timezone
from exchange_terminal.services.backtest_engine import prepare_backtest_dataset
from exchange_terminal.services.market_calendar import build_market_calendar_contract


def daily_rows(*, symbol="HK.00836", source="futu", local_midnight=True):
    calendar = build_market_calendar_contract(
        calendar_name="XHKG" if symbol.startswith("HK.") else "XNYS",
        start_date="2024-06-19",
        end_date="2024-08-31",
    )
    dates = calendar["expected_dates"][:8]
    if len(dates) != 8:
        raise AssertionError("Real exchange calendar fixture is unavailable")
    zone = stock_timezone(symbol) if local_midnight else timezone.utc
    return [
        {
            "date": session_date,
            "ts_ms": int(datetime.fromisoformat(session_date).replace(tzinfo=zone).timestamp() * 1000),
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0,
            "volume": 1_000.0, "complete": True, "source": source,
        }
        for session_date in dates
    ]


class BacktestHKSessionTimezoneTests(unittest.TestCase):
    @staticmethod
    def prepare(rows, *, symbol="HK.00836", source="futu", market="stock", **kwargs):
        return prepare_backtest_dataset(
            rows, symbol=symbol, source=source, market=market,
            minimum_rows=6, **kwargs,
        )

    def test_futu_hk_local_midnight_passes_without_rewriting_frozen_rows(self):
        rows = daily_rows()
        before = deepcopy(rows)
        prepared = self.prepare(rows)
        self.assertEqual(prepared["status"], "PASS", prepared["manifest"]["blockers"])
        self.assertEqual(prepared["manifest"]["session_date_timezone"], "Asia/Hong_Kong")
        self.assertEqual(prepared["manifest"]["session_date_timestamp_mismatch_count"], 0)
        self.assertEqual(prepared["manifest"]["market_calendar"]["calendar_name"], "XHKG")
        self.assertEqual(prepared["manifest"]["market_calendar"]["status"], "PASS")
        self.assertEqual(rows, before)
        self.assertEqual(
            [(row["date"], row["ts_ms"]) for row in prepared["rows"]],
            [(row["date"], row["ts_ms"]) for row in rows],
        )

    def test_futu_hk_utc_midnight_remains_same_session(self):
        prepared = self.prepare(daily_rows(local_midnight=False))
        self.assertEqual(prepared["status"], "PASS", prepared["manifest"]["blockers"])

    def test_futu_hk_true_date_mismatch_still_blocks_with_both_dates(self):
        rows = daily_rows()
        expected_date = rows[2]["date"]
        rows[2]["ts_ms"] += 86_400_000
        prepared = self.prepare(rows)
        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("session_date_timestamp_mismatch:1", prepared["manifest"]["blockers"])
        example = prepared["manifest"]["session_date_timestamp_mismatch_examples"][0]
        self.assertEqual(example["session_date"], expected_date)
        self.assertEqual(example["timestamp_session_date_utc"], expected_date)
        self.assertNotEqual(example["timestamp_session_date"], expected_date)
        self.assertEqual(example["session_date_timezone"], "Asia/Hong_Kong")

    def test_yahoo_hk_keeps_utc_date_semantics(self):
        for local_midnight, expected in ((False, "PASS"), (True, "BLOCK")):
            with self.subTest(local_midnight=local_midnight):
                prepared = self.prepare(
                    daily_rows(source="yahoo_chart", local_midnight=local_midnight),
                    source="yahoo_chart",
                )
                self.assertEqual(prepared["status"], expected)
                self.assertEqual(prepared["manifest"]["session_date_timezone"], "UTC")
                if local_midnight:
                    self.assertIn("session_date_timestamp_mismatch:8", prepared["manifest"]["blockers"])

    def test_unknown_sources_cannot_claim_futu_local_date_semantics(self):
        for source in ("unknown_vendor", "stock_sqlite_cache", "futu_unverified"):
            with self.subTest(source=source):
                rows = daily_rows(source=source)
                prepared = self.prepare(rows, source=source)
                self.assertEqual(prepared["status"], "BLOCK")
                self.assertIn("session_date_timestamp_mismatch:8", prepared["manifest"]["blockers"])
        rows = daily_rows()
        rows[2]["source"] = "unknown_vendor"
        prepared = self.prepare(rows)
        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("session_date_timestamp_mismatch:1", prepared["manifest"]["blockers"])
        self.assertEqual(prepared["manifest"]["session_date_timestamp_mismatch_examples"][0]["session_date_timezone"], "UTC")

    def test_us_stooq_and_futu_keep_existing_utc_date_contract(self):
        for source in ("stooq", "futu"):
            with self.subTest(source=source):
                rows = daily_rows(symbol="AAPL", source=source, local_midnight=False)
                accepted = self.prepare(rows, symbol="AAPL", source=source)
                self.assertEqual(accepted["status"], "PASS", accepted["manifest"]["blockers"])
                self.assertEqual(accepted["manifest"]["session_date_timezone"], "UTC")
                rows[2]["ts_ms"] -= 86_400_000
                blocked = self.prepare(rows, symbol="AAPL", source=source)
                self.assertEqual(blocked["status"], "BLOCK")
                self.assertIn("session_date_timestamp_mismatch:1", blocked["manifest"]["blockers"])

    def test_crypto_keeps_utc_even_with_futu_label(self):
        start = datetime(2024, 6, 19, tzinfo=timezone.utc)
        for source in ("okx", "futu"):
            with self.subTest(source=source):
                rows = daily_rows(source=source, local_midnight=False)
                for index, row in enumerate(rows):
                    stamp = start + timedelta(days=index)
                    row.update(date=stamp.date().isoformat(), ts_ms=int(stamp.timestamp() * 1000))
                accepted = self.prepare(rows, symbol="BTC-USDT", source=source, market="crypto")
                self.assertEqual(accepted["status"], "PASS", accepted["manifest"]["blockers"])
                self.assertEqual(accepted["manifest"]["session_date_timezone"], "UTC")
                for row in rows:
                    row["ts_ms"] -= 8 * 3_600_000
                blocked = self.prepare(rows, symbol="BTC-USDT", source=source, market="crypto")
                self.assertEqual(blocked["status"], "BLOCK")
                self.assertIn("session_date_timestamp_mismatch:8", blocked["manifest"]["blockers"])

    def test_hk_timezone_does_not_relax_other_v6_gates(self):
        cases = (
            ("identity", {"source": " futu "}, "dataset_identity_contract:source_noncanonical"),
            ("timeframe", {"timeframe": "unknown"}, "timeframe_contract:timeframe_unsupported:unknown"),
            ("incomplete", {}, "historical_incomplete_rows:1"),
            ("boolean", {}, "invalid_ohlcv_rows:1"),
            ("missing_session", {}, "market_calendar:calendar_sessions_missing:1"),
        )
        for case, kwargs, expected in cases:
            with self.subTest(case=case):
                rows = daily_rows()
                if case == "incomplete":
                    rows[2]["complete"] = False
                elif case == "boolean":
                    rows[2]["close"] = True
                elif case == "missing_session":
                    rows.pop(2)
                prepared = self.prepare(rows, **kwargs)
                self.assertEqual(prepared["status"], "BLOCK")
                self.assertIn(expected, prepared["manifest"]["blockers"])


if __name__ == "__main__":
    unittest.main()
