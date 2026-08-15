from __future__ import annotations

import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.market_data.stock_candle_quality import analyze_stock_candle_series
from exchange_terminal.market_data.stock_candles import stock_payload_has_due_incomplete_daily, with_stock_freshness
from exchange_terminal.research.stock_research import stock_daily_swing_fast, stock_unusual_activity_fast
from exchange_terminal import server as terminal_server


def candle(day: int, close: float, *, source: str = "futu") -> dict[str, float | int | str]:
    return {
        "ts": day * 86_400_000,
        "date": f"2026-06-{day:02d}",
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": 1_000_000 + day,
        "source": source,
    }


class StockCandleQualityTests(unittest.TestCase):
    def test_completed_daily_futu_history_is_not_labeled_realtime(self) -> None:
        friday_close = int(datetime(2026, 7, 31, 16, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        sunday = int(datetime(2026, 8, 2, 12, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        with patch("exchange_terminal.market_data.stock_candles.now_ms", return_value=sunday):
            result = with_stock_freshness({
                "source": "futu",
                "rows": [{"ts": friday_close, "close": 100, "complete": True}],
            }, "1d", "AAPL")

        self.assertFalse(result["realtime"])
        self.assertFalse(result["in_progress"])

    def test_provisional_daily_futu_bar_can_be_labeled_realtime(self) -> None:
        intraday = int(datetime(2026, 7, 31, 14, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        with patch("exchange_terminal.market_data.stock_candles.now_ms", return_value=intraday + 5_000):
            result = with_stock_freshness({
                "source": "futu",
                "rows": [{"ts": intraday, "close": 100, "complete": False, "provisional": True}],
            }, "1d", "AAPL")

        self.assertTrue(result["realtime"])
        self.assertTrue(result["in_progress"])

    def test_incomplete_daily_row_becomes_refresh_due_after_regular_close(self) -> None:
        after_close = int(datetime(2026, 7, 31, 17, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        before_close = int(datetime(2026, 7, 31, 15, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        payload = {"rows": [{"date": "2026-07-31", "close": 100, "complete": False}]}

        self.assertTrue(stock_payload_has_due_incomplete_daily(payload, "1d", "AAPL", at_ms=after_close))
        self.assertFalse(stock_payload_has_due_incomplete_daily(payload, "1d", "AAPL", at_ms=before_close))

    def test_completed_only_refreshes_a_due_incomplete_daily_row(self) -> None:
        after_close = int(datetime(2026, 7, 31, 17, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)
        start = datetime(2026, 2, 2, 16, 0, tzinfo=ZoneInfo("America/New_York"))
        rows = []
        current = start
        while len(rows) < 120:
            if current.weekday() < 5:
                index = len(rows)
                rows.append({
                    "ts": int(current.timestamp() * 1000),
                    "date": current.date().isoformat(),
                    "open": 100 + index,
                    "high": 102 + index,
                    "low": 99 + index,
                    "close": 101 + index,
                    "volume": 1_000_000,
                    "complete": True,
                })
            current += timedelta(days=1)
        rows[-1] = {**rows[-1], "date": "2026-07-31", "ts": after_close, "complete": False}
        refreshed = [dict(row) for row in rows]
        refreshed[-1]["complete"] = True
        persistent = {"ok": True, "source": "stock_sqlite_cache", "origin_source": "futu", "warning": "", "rows": rows}
        futu_payload = {"ok": True, "source": "futu", "rows": refreshed}
        with (
            patch("exchange_terminal.server.read_stock_candle_cache", return_value=None),
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value=persistent),
            patch("exchange_terminal.server.stock_candle_stale_warning", return_value=""),
            patch("exchange_terminal.market_data.stock_candles.now_ms", return_value=after_close),
            patch("exchange_terminal.server.futu_status_snapshot", return_value={"opend_online": True}),
            patch("exchange_terminal.server.read_futu_stock_candles", return_value=futu_payload) as futu_reader,
            patch("exchange_terminal.server.cache_stock_candles", side_effect=lambda _symbol, _interval, _session, payload: payload),
        ):
            result = terminal_server.read_stock_candles("AAPL", 120, "1d", "all", completed_only=True)

        futu_reader.assert_called_once_with("AAPL", 120, "1d", "regular", include_snapshot=False)
        self.assertTrue(result["rows"][-1]["complete"])
        self.assertEqual(result["rows"][-1]["date"], "2026-07-31")

    def test_completed_daily_research_history_reuses_sqlite_without_futu_snapshot(self) -> None:
        stamp = int(time.time() * 1000)
        rows = [{
            "ts": stamp - (120 - index) * 86_400_000,
            "date": f"2026-{(index // 28) + 1:02d}-{(index % 28) + 1:02d}",
            "open": 100 + index,
            "high": 101 + index,
            "low": 99 + index,
            "close": 100.5 + index,
            "volume": 1_000 + index,
            "complete": True,
        } for index in range(120)]
        persistent = {
            "ok": True,
            "source": "stock_sqlite_cache",
            "origin_source": "futu",
            "warning": "stock cache behind current session",
            "rows": rows,
        }
        with (
            patch("exchange_terminal.server.read_stock_candle_cache", return_value=None),
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value=persistent),
            patch("exchange_terminal.server.stock_candle_stale_warning", return_value=""),
            patch("exchange_terminal.server.futu_status_snapshot") as status_reader,
            patch("exchange_terminal.server.read_futu_stock_candles") as futu_reader,
        ):
            result = terminal_server.read_stock_candles(
                "AAPL",
                120,
                "1d",
                "all",
                completed_only=True,
            )

        status_reader.assert_not_called()
        futu_reader.assert_not_called()
        self.assertTrue(result["completed_only"])
        self.assertEqual(result["retrieval_source"], "stock_sqlite_cache")
        self.assertEqual(result["origin_source"], "futu")
        self.assertEqual(result["warning"], "")

    def test_backtest_history_reports_origin_and_retrieval_sources_separately(self) -> None:
        rows = [candle(day, 100 + day) for day in range(1, 25)]
        with (
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value={
            "rows": rows,
            "source": "stock_sqlite_cache",
            "origin_source": "futu",
            "origin_sources": ["futu"],
            "retrieval_source": "stock_sqlite_cache",
            }) as persistent_reader,
            patch("exchange_terminal.server.read_stock_candles") as live_reader,
            patch("exchange_terminal.server.attest_stock_candle_cache", return_value={"status": "PASS"}),
            patch("exchange_terminal.server.attest_stock_backtest_rows", return_value={"status": "PASS"}),
            patch("exchange_terminal.server.stock_data_revision_summary", return_value={"latest_cross_source": []}),
        ):
            result = terminal_server.backtest_market_rows("AAPL", 24, dataset_lineage_id="experiment-test")

        persistent_reader.assert_called_once_with("AAPL", 24, "1d", "regular")
        live_reader.assert_not_called()
        self.assertEqual(result["source"], "futu")
        self.assertEqual(result["retrieval_source"], "stock_sqlite_cache")
        self.assertEqual(result["origin_sources"], ["futu"])

    def test_interactive_backtest_preview_does_not_write_revision_attestations(self) -> None:
        rows = [candle(day, 100 + day) for day in range(1, 25)]
        with (
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value={
                "rows": rows,
                "source": "stock_sqlite_cache",
                "origin_source": "futu",
                "origin_sources": ["futu"],
                "retrieval_source": "stock_sqlite_cache",
            }),
            patch("exchange_terminal.server.read_stock_candles") as live_reader,
            patch("exchange_terminal.server.attest_stock_candle_cache") as cache_attestation,
            patch("exchange_terminal.server.attest_stock_backtest_rows") as dataset_attestation,
            patch("exchange_terminal.server.stock_data_revision_summary", return_value={"latest_cross_source": []}),
        ):
            result = terminal_server.backtest_market_rows("AAPL", 24)

        live_reader.assert_not_called()
        cache_attestation.assert_not_called()
        dataset_attestation.assert_not_called()
        self.assertEqual(result["data_revision_evidence"]["status"], "REVIEW")
        self.assertEqual(
            result["data_revision_evidence"]["backtest_dataset"]["classification"],
            "INTERACTIVE_DATASET_NOT_FROZEN",
        )

    def test_daily_all_session_maps_to_regular_history_partition(self) -> None:
        self.assertEqual(terminal_server.normalize_stock_history_session("1d", "all"), "regular")
        self.assertEqual(terminal_server.normalize_stock_history_session("1Dutc", "all"), "regular")
        self.assertEqual(terminal_server.normalize_stock_history_session("1m", "all"), "all")

    def test_offline_seed_never_fabricates_bid_ask_depth(self) -> None:
        quote = terminal_server.stock_seed_quote("AAPL")

        self.assertEqual(quote["bidPx"], 0.0)
        self.assertEqual(quote["askPx"], 0.0)

    def test_intraday_source_arbitration_prefers_newer_external_rows(self) -> None:
        stamp = int(time.time() * 1000)
        futu_payload = {
            "ok": True,
            "source": "futu",
            "rows": [{"ts": stamp - 48 * 60 * 60 * 1000, "date": "2026-07-29", "close": 100, "session": "regular"}],
        }
        yahoo_payload = {
            "ok": True,
            "source": "yahoo",
            "rows": [{"ts": stamp - 2 * 60 * 60 * 1000, "date": "2026-07-31", "close": 103, "session": "regular"}],
        }
        with (
            patch("exchange_terminal.server.read_stock_candle_cache", return_value=None),
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value=None),
            patch("exchange_terminal.server.futu_status_snapshot", return_value={"opend_online": True}),
            patch("exchange_terminal.server.read_futu_stock_candles", return_value=futu_payload),
            patch("exchange_terminal.server.read_external_stock_candles", return_value=yahoo_payload),
            patch("exchange_terminal.server.cache_stock_candles", side_effect=lambda _symbol, _interval, _session, payload: payload),
        ):
            result = terminal_server.read_stock_candles("AAPL", 260, "15m", "regular", force=True)

        self.assertEqual(result["source"], "yahoo")
        self.assertEqual(result["source_arbitration"]["selected"], "yahoo")
        self.assertGreater(result["source_arbitration"]["external_latest_ts"], result["source_arbitration"]["futu_latest_ts"])

    def test_forced_refresh_labels_persistent_cache_fallback(self) -> None:
        persistent = {
            "ok": True,
            "source": "stock_sqlite_cache",
            "origin_source": "futu",
            "warning": "",
            "rows": [{
                "ts": 1_785_504_600_000,
                "date": "2026-07-31",
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 101,
                "volume": 1_000,
                "complete": True,
            }],
        }
        with (
            patch("exchange_terminal.server.read_stock_persistent_candle_cache", return_value=persistent),
            patch("exchange_terminal.server.stock_payload_needs_session_refresh", return_value=False),
            patch("exchange_terminal.server.stock_payload_has_due_incomplete_daily", return_value=False),
            patch("exchange_terminal.server.futu_status_snapshot", return_value={"opend_online": False, "message": "offline"}),
            patch("exchange_terminal.server.ALLOW_STOCK_FALLBACK", False),
            patch("exchange_terminal.server.ALLOW_STOCK_HISTORY_FALLBACK", False),
        ):
            result = terminal_server.read_stock_candles("AAPL", 120, "1d", "regular", force=True)

        self.assertTrue(result["forced"])
        self.assertTrue(result["refresh_failed"])
        self.assertEqual(result["warning"], "forced stock refresh failed; using local cache")
        self.assertEqual(result["refresh_error"], "offline")

    def test_all_intraday_cache_fans_out_current_session_rows(self) -> None:
        stamp = int(time.time() * 1000)
        rows = [
            {"ts": stamp - 120_000, "date": "2026-08-01", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 10, "session": "pre"},
            {"ts": stamp - 60_000, "date": "2026-08-01", "open": 101, "high": 102, "low": 100, "close": 101.5, "volume": 12, "session": "regular"},
        ]
        keys = [terminal_server.stock_candle_cache_key("AAPL", "1m", session) for session in ("all", "pre", "regular")]
        for key in keys:
            terminal_server.STOCK_CANDLE_CACHE.pop(key, None)
        try:
            with patch("exchange_terminal.server.upsert_stock_candle_cache", return_value=2):
                result = terminal_server.cache_stock_candles("AAPL", "1m", "all", {
                    "ok": True,
                    "source": "yahoo",
                    "rows": rows,
                })

            self.assertEqual(result["session_cache_partitions"], {"pre": 1, "regular": 1})
            self.assertEqual(terminal_server.STOCK_CANDLE_CACHE[keys[1]]["payload"]["session"], "pre")
            self.assertEqual(terminal_server.STOCK_CANDLE_CACHE[keys[2]]["payload"]["session"], "regular")
        finally:
            for key in keys:
                terminal_server.STOCK_CANDLE_CACHE.pop(key, None)

    def test_daily_cache_records_raw_provider_observation_before_accepted_merge(self) -> None:
        rows = [
            {
                "ts": 1_775_000_000_000 + index * 86_400_000,
                "date": f"2026-04-{20 + index:02d}",
                "open": 100 + index,
                "high": 102 + index,
                "low": 99 + index,
                "close": 101 + index,
                "volume": 1_000 + index,
                "complete": True,
                "source": "futu",
                "session": "regular",
            }
            for index in range(2)
        ]
        payload = {
            "ok": True,
            "source": "futu",
            "rows": rows,
            "adjustment_basis": "FORWARD_ADJUSTED_QFQ",
            "adjustment_evidence": {"corporate_actions_hash": "actions-hash"},
        }
        order: list[str] = []
        key = terminal_server.stock_candle_cache_key("AAPL", "1d", "regular")
        terminal_server.STOCK_CANDLE_CACHE.pop(key, None)
        try:
            with (
                patch("exchange_terminal.server.stock_candle_stale_warning", return_value=""),
                patch("exchange_terminal.server.enrich_stock_series_contract", return_value=payload),
                patch("exchange_terminal.server.record_stock_revision_snapshot", side_effect=lambda **_kwargs: order.append("provider") or {"status": "PASS"}) as recorder,
                patch("exchange_terminal.server.prepare_stock_candle_cache_rows", side_effect=lambda *_args: order.append("prepare") or {"rows": rows}),
                patch("exchange_terminal.server.upsert_stock_candle_cache", return_value=2),
                patch("exchange_terminal.server.attest_stock_candle_cache", return_value={"status": "PASS"}),
            ):
                result = terminal_server.cache_stock_candles("AAPL", "1d", "regular", payload)

            self.assertEqual(order[:2], ["provider", "prepare"])
            self.assertEqual(recorder.call_args.kwargs["rows"], rows)
            self.assertEqual(recorder.call_args.kwargs["provider"], "futu")
            self.assertEqual(recorder.call_args.kwargs["corporate_actions_hash"], "actions-hash")
            self.assertEqual(recorder.call_args.kwargs["observation_scope"], "QUERY_WINDOW")
            self.assertEqual(result["provider_revision_evidence"]["status"], "PASS")
        finally:
            terminal_server.STOCK_CANDLE_CACHE.pop(key, None)

    def test_normal_series_remains_ready(self) -> None:
        report = analyze_stock_candle_series([candle(day, 100 + day) for day in range(1, 25)])

        self.assertFalse(report["has_break"])
        self.assertTrue(report["analysis_ready"])
        self.assertEqual(report["segment_rows"], 24)

    def test_large_price_scale_break_starts_new_segment(self) -> None:
        rows = [candle(day, 180 + day) for day in range(1, 24)] + [candle(24, 580)]
        report = analyze_stock_candle_series(rows)

        self.assertTrue(report["has_break"])
        self.assertFalse(report["analysis_ready"])
        self.assertEqual(report["segment_rows"], 1)
        self.assertEqual(report["analysis_rows"][0]["close"], 580)

    @patch("exchange_terminal.research.stock_research.read_stock_persistent_candle_cache")
    def test_daily_swing_pauses_instead_of_reporting_corrupt_trend(self, cache_reader) -> None:
        rows = [candle(day, 176 + day) for day in range(1, 24)] + [candle(24, 539)]
        cache_reader.return_value = {"rows": rows, "source": "stock_sqlite_cache", "origin_source": "futu"}
        quote = {"last": 539, "change24h_pct": -7.43, "source": "futu", "prevClose": 582.25}

        result = stock_daily_swing_fast("WDC", quote, {"volume_ratio": 1.0})

        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "复权断点待核")
        self.assertNotIn("196", result["summary"])
        self.assertIn("暂停20/60日趋势", result["summary"])

    @patch("exchange_terminal.research.stock_research.read_stock_persistent_candle_cache")
    def test_unusual_activity_uses_quote_change_after_latest_break(self, cache_reader) -> None:
        rows = [candle(day, 176 + day) for day in range(1, 24)] + [candle(24, 539)]
        cache_reader.return_value = {"rows": rows, "source": "stock_sqlite_cache", "origin_source": "futu"}
        quote = {
            "last": 539,
            "open24h": 582.0,
            "high24h": 585.0,
            "low24h": 532.0,
            "change24h_pct": -7.43,
            "source": "futu",
            "prevClose": 582.25,
            "quote_quality": {"previous_close": 582.25, "quarantined": False},
        }

        result = stock_unusual_activity_fast("WDC", quote)

        self.assertAlmostEqual(result["change_pct"], -7.43, places=2)
        self.assertLess(abs(result["gap_pct"]), 1)
        self.assertIn("日线复权断点待核", result["flags"])
        self.assertNotIn("+176", result["headline"])

    @patch("exchange_terminal.research.stock_research.read_stock_persistent_candle_cache")
    def test_quarantined_quote_cannot_restore_corrupt_break_change(self, cache_reader) -> None:
        rows = [candle(day, 176 + day) for day in range(1, 24)] + [candle(24, 539)]
        cache_reader.return_value = {"rows": rows, "source": "stock_sqlite_cache", "origin_source": "futu"}
        quote = {
            "last": 539,
            "open24h": 552,
            "high24h": 555,
            "low24h": 537,
            "change24h_pct": 169.67,
            "source": "stock_sqlite_cache",
            "prevClose": 199.7,
            "quote_quality": {"previous_close": 199.7, "quarantined": True},
        }

        result = stock_unusual_activity_fast("WDC", quote)

        self.assertEqual(result["change_pct"], 0)
        self.assertEqual(result["gap_pct"], 0)
        self.assertNotIn("+169", result["headline"])

    @patch("exchange_terminal.server.market_ai_candles")
    def test_market_ai_pauses_on_unverified_daily_scale_break(self, candle_reader) -> None:
        rows = [candle(day, 176 + day) for day in range(1, 24)] + [candle(24, 539)]
        candle_reader.return_value = {"candles": rows, "source": "futu", "bar": "1d"}

        result = terminal_server.local_market_ai_analysis("WDC", "1Dutc", 539, [], {}, rows)

        self.assertTrue(result["analysis_paused"])
        self.assertEqual(result["trend_state"], "复权断点待核")
        self.assertEqual(result["long_plan"]["win_rate_pct"], 0)
        self.assertEqual(result["short_plan"]["win_rate_pct"], 0)
        self.assertNotIn("窗口涨跌", " ".join(result["evidence"]))

    @patch("exchange_terminal.server.read_stock_candles")
    def test_market_ai_stock_daily_uses_regular_cache_partition(self, candle_reader) -> None:
        candle_reader.return_value = {"rows": [candle(day, 100 + day) for day in range(1, 25)], "source": "futu"}

        result = terminal_server.market_ai_candles("WDC", "1Dutc", 120)

        candle_reader.assert_called_once_with("WDC", 120, "1d", "regular")
        self.assertEqual(result["source"], "futu")
        self.assertEqual(len(result["candles"]), 24)


if __name__ == "__main__":
    unittest.main()
