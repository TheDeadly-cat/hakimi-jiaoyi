"""Focused offline checks for derived structures, peer alignment and source cards."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import indicator_math
from exchange_terminal.services import terminal_insights as insights
from exchange_terminal.services.terminal_research import TerminalResearchService, _seal
from exchange_terminal.services.quant_workspace import _READ_RESOURCES


GROUPS = [{"symbol": "AAA", "market": "US", "quote": "USD", "sector": "Test group"},
          {"symbol": "BBB", "market": "US", "quote": "USD", "sector": "Test group"}]


def frozen(symbol="AAA", start="2024-01-02", end="2024-06-28", rate=.01):
    schedule = insights._schedule({"calendar_name": "XNYS"}, date.fromisoformat(start), date.fromisoformat(end))
    rows = []
    for i, session in enumerate(schedule):
        price = 100 + rate * i + (i % 14 if i % 28 < 14 else 14 - i % 14)
        rows.append({"date": session["date"], "ts_ms": 1704153600000 + i * 86400000,
                     "open": price, "high": price + 2, "low": price - 2, "close": price + .5,
                     "volume": 1000, "complete": True, "provisional": False, "source": "fixture-author"})
    return _seal({"schema_version": "hakimi-terminal-input-v1", "symbol": symbol, "bar": "1D",
                  "meta": {"asset_class": "US_EQUITY", "currency": "USD", "price_basis": "RAW",
                           "session": "REGULAR", "source_lineage": ["fixture-author"]},
                  "quality": {"status": "REVIEW", "source_authenticated": False}, "rows": rows})


def reseal(item):
    return _seal({key: value for key, value in item.items() if key != "id"})


class TerminalInsightsTests(unittest.TestCase):
    def test_complete_weeks_months_only_and_confirmation_not_pivot_date(self):
        item = frozen(start="2024-01-03")
        result = insights.structure_frames(item, "2024-03-20", GROUPS[0])
        frames = {frame["frame"]: frame for frame in result["frames"]}
        self.assertEqual(frames["1D"]["last_completed_date"], "2024-03-20")
        self.assertEqual(frames["1W"]["last_completed_date"], "2024-03-15")
        self.assertEqual(frames["1M"]["last_completed_date"], "2024-02-29")
        self.assertEqual(len(frames["1W"]["excluded_periods"]), 2)
        for frame in frames.values():
            self.assertEqual(frame["as_of_close_date"], "2024-03-20")
            if frame["support"]:
                self.assertAlmostEqual(frame["distance_to_support_pct"],
                                       (result["as_of_close"] / frame["support"]["price"] - 1) * 100)
        for frame in frames.values():
            for event in frame.get("confirmed_events", []):
                self.assertLess(event["pivot_date"], event["confirmed_at_date"])
                self.assertLessEqual(event["confirmed_at_date"], result["as_of"])

    def test_holiday_shortened_week_closes_on_last_exchange_session(self):
        item = frozen()
        frames = insights.structure_frames(item, "2024-03-28", GROUPS[0])["frames"]
        self.assertEqual(frames[1]["last_completed_date"], "2024-03-28")
        self.assertEqual(frames[2]["last_completed_date"], "2024-03-28")

    def test_historical_prefix_ignores_future_price_changes(self):
        item = frozen()
        altered = deepcopy(item)
        for row in altered["rows"]:
            if row["date"] > "2024-03-20":
                for key in ("open", "high", "low", "close"):
                    row[key] *= 100
        altered = reseal(altered)
        self.assertEqual(insights.structure_frames(item, "2024-03-20", GROUPS[0]),
                         insights.structure_frames(altered, "2024-03-20", GROUPS[0]))

    def test_missing_session_cannot_be_collapsed_into_week_or_pivot(self):
        item = frozen()
        item["rows"].pop(35)
        with self.assertRaisesRegex(ValueError, "缺少应有交易日"):
            insights.structure_frames(item, "2024-03-20", GROUPS[0])

    def test_confirmed_rising_pivots_do_not_hide_a_later_support_break(self):
        item = frozen()
        prices = [100,102,105,110,105,103,101,98,102,104,109,115,110,108,105,
                  103,107,110,113,120,115,113,110,108,112,114,118,123,115,90]
        item["rows"] = item["rows"][:len(prices)]
        for row, price in zip(item["rows"], prices):
            row.update(open=price, high=price + 1, low=price - 1, close=price)
        end = item["rows"][-1]["date"]
        daily = insights.structure_frames(item, end, GROUPS[0])["frames"][0]
        self.assertEqual(daily["pivot_pattern"], "上升组合 HH / HL")
        self.assertEqual(daily["structure_break"]["kind"], "BELOW_SUPPORT")
        self.assertEqual(daily["structure_break"]["date"], end)
        self.assertIn("跌破支撑", daily["state"])
        self.assertLess(daily["support"]["confirmed_at_date"], end)

    def test_unknown_calendar_and_unfinished_rows_do_not_get_structure(self):
        item = frozen()
        item["meta"]["asset_class"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "缺少可核对"):
            insights.structure_frames(item, "2024-03-20", {})
        item["rows"][2]["complete"] = False
        with self.assertRaisesRegex(ValueError, "not_explicitly_completed"):
            insights.structure_frames(item, "2024-03-20", GROUPS[0])

    def test_no_future_exchange_close_is_accepted_even_if_provider_marks_complete(self):
        item = frozen(end="2024-01-03")
        schedule = insights._schedule({"calendar_name": "XNYS"}, date(2024, 1, 1), date(2024, 1, 31))
        schedule[0]["close_utc"] = "2999-01-01T00:00:00+00:00"
        with patch.object(insights, "_schedule", return_value=schedule):
            with self.assertRaisesRegex(ValueError, "尚未收盘"):
                insights.structure_frames(item, "2024-01-03", GROUPS[0])

    def test_crypto_utc_daily_anchor_is_verified_before_aggregation(self):
        item = frozen()
        item["meta"].update(asset_class="CRYPTO", timezone="UTC")
        item["symbol"] = "BTC-USDT"
        rows = []
        for index in range(95):
            day = date(2024, 1, 1) + timedelta(days=index)
            rows.append({"date": day.isoformat(), "ts_ms": int(datetime.combine(day, datetime.min.time(), timezone.utc).timestamp() * 1000),
                         "open": 100, "high": 102, "low": 99, "close": 101, "complete": True, "provisional": False})
        item["rows"] = rows
        frames = insights.structure_frames(item, "2024-04-04", {})["frames"]
        self.assertEqual(frames[1]["last_completed_date"], "2024-03-31")
        self.assertEqual(frames[2]["last_completed_date"], "2024-03-31")
        item["rows"][0]["ts_ms"] += 8 * 3600000
        with self.assertRaisesRegex(ValueError, "UTC 日界线"):
            insights.structure_frames(item, "2024-04-04", {})

    def test_peer_prices_are_same_window_and_configuration_is_not_verified_industry(self):
        first, second = frozen(), frozen("BBB", rate=.4)
        result = insights.compare_peers([first, second], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in GROUPS})
        self.assertEqual(result["baseline_symbol"], "AAA")
        self.assertEqual(result["group_status"], "PROJECT_CONFIG_GROUP")
        self.assertIs(result["historical_membership_verified"], False)
        self.assertEqual(result["rows"][0]["symbol"], "BBB")
        self.assertEqual(result["rows"][0]["rank"], 1)
        for row in result["rows"]:
            self.assertEqual(row["series"][0]["value"], 100)
            self.assertAlmostEqual(row["series"][-1]["value"] - 100, row["price_change_pct"])
            self.assertEqual(row["correlation"]["status"], "PASS")

    def test_no_silent_intersection_or_forward_fill_for_peer_gap(self):
        first, second = frozen(), frozen("BBB")
        second["rows"] = [row for row in second["rows"] if row["date"] != "2024-03-12"]
        with self.assertRaisesRegex(ValueError, "不完整或未对齐"):
            insights.compare_peers([first, second], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in GROUPS})

    def test_different_sources_basis_session_and_currency_are_rejected(self):
        first = frozen()
        for key, value in (("price_basis", "ADJUSTED"), ("session", "EXTENDED"),
                           ("currency", "HKD"), ("source_lineage", ["another-provider"])):
            with self.subTest(key=key):
                second = frozen("BBB")
                second["meta"][key] = value
                with self.assertRaises(ValueError):
                    insights.compare_peers([first, second], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in GROUPS})

    def test_duplicate_security_and_short_correlation_history(self):
        first, second = frozen(), frozen("BBB")
        with self.assertRaisesRegex(ValueError, "同一标的"):
            insights.compare_peers([first, first], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in GROUPS})
        result = insights.compare_peers([first, second], "2024-03-01", "2024-03-05", {g["symbol"]: g for g in GROUPS})
        self.assertEqual(result["rows"][0]["correlation"]["status"], "BLOCK")
        self.assertIsNone(result["rows"][0]["correlation"]["correlation"])

    def test_different_groups_remain_explicit_user_selection(self):
        groups = deepcopy(GROUPS)
        groups[1]["sector"] = "Another group"
        result = insights.compare_peers([frozen(), frozen("BBB")], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in groups})
        self.assertEqual(result["group_status"], "USER_SELECTION")
        self.assertIsNone(result["group"])

    def test_invalid_availability_lag_is_rejected_for_structures_and_peers(self):
        for value in (-1, float("nan"), float("inf"), True, "10"):
            with self.subTest(value=value):
                first, second = frozen(), frozen("BBB")
                first["meta"]["bar_availability_lag_seconds"] = value
                with self.assertRaisesRegex(ValueError, "可用延迟"):
                    insights.structure_frames(first, "2024-03-20", GROUPS[0])
                with self.assertRaisesRegex(ValueError, "可用延迟"):
                    insights.compare_peers([first, second], "2024-03-01", "2024-04-30", {g["symbol"]: g for g in GROUPS})

    def test_future_bar_does_not_return_available_card_values(self):
        item = frozen(end="2024-01-03")
        terminal = Mock()
        terminal._input.return_value = item
        service = insights.TerminalInsightsService(terminal, lambda: GROUPS)
        schedule = insights._schedule({"calendar_name": "XNYS"}, date(2024, 1, 1), date(2024, 1, 31))
        schedule[0]["close_utc"] = "2999-01-01T00:00:00+00:00"
        with patch.object(insights, "_schedule", return_value=schedule):
            result = service.read("terminal_insights", item["id"] + "/2024-01-03")
        self.assertEqual(result["status"], "STRUCTURE_UNAVAILABLE")
        self.assertTrue(all(card["status"] == "DATA_UNAVAILABLE" and card["value"] is None for card in result["cards"]))

    def test_cards_use_existing_math_and_document_sma_not_wilder(self):
        rows = frozen()["rows"]
        cards = {card["key"]: card for card in insights.indicator_cards(rows)}
        self.assertEqual(cards["atr"]["value"], indicator_math.atr(rows)[-1])
        self.assertEqual(cards["rsi"]["value"], indicator_math.rsi([row["close"] for row in rows])[-1])
        self.assertIn("SMA", cards["rsi"]["formula"])
        self.assertIn("非 Wilder", cards["atr"]["limitation"])
        short = {card["key"]: card for card in insights.indicator_cards(rows[:3])}
        self.assertEqual(short["atr"]["status"], "WARMUP")
        self.assertIsNone(short["atr"]["value"])

    def test_service_reads_preserve_all_original_files_and_do_not_fetch_or_run(self):
        with tempfile.TemporaryDirectory(prefix="hakimi-insights-") as folder:
            core = Mock(workspace=Path(folder))
            reader, runner = Mock(), Mock()
            service = TerminalResearchService(core, reader, Mock(), runner, Mock(), group_reader=lambda: GROUPS)
            items = [frozen(), frozen("BBB")]
            for item in items:
                service._write(Path(folder) / "terminal-inputs" / (item["id"] + ".json"), item)
            before = {str(path): path.read_bytes() for path in Path(folder).rglob("*") if path.is_file()}
            self.assertIn("terminal_insights", _READ_RESOURCES)
            self.assertIn("terminal_peers", _READ_RESOURCES)
            catalog = service.read("terminal_insights")
            self.assertEqual(catalog["status"], "CATALOG")
            result = service.read("terminal_insights", items[0]["id"] + "/2024-03-20")
            self.assertEqual(result["status"], "REVIEW")
            self.assertFalse(result["order_authorized"])
            self.assertEqual(result["cards"][0]["bar_date"], "2024-03-20")
            peers = service.read("terminal_peers", "2024-03-01/2024-04-30/" + ",".join(item["id"] for item in items))
            self.assertEqual(peers["new_economic_runs"], 0)
            with self.assertRaises(ValueError):
                service.read("terminal_insights", "../2024-03-20")
            self.assertEqual(before, {str(path): path.read_bytes() for path in Path(folder).rglob("*") if path.is_file()})
            reader.assert_not_called()
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
