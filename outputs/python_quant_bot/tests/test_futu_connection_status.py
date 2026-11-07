from __future__ import annotations

import ast
from contextlib import ExitStack
from datetime import datetime, timedelta
import importlib.util
import os
from pathlib import Path
import sys
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("HAKIMI_SKIP_LOCAL_AI_ENV", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.market_data import futu, futu_context, futu_deep, futu_quotes
from hakimi_research.stock_quote_quality import normalize_stock_quote_quality


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, _orientation):
        return self.rows

    def head(self, _limit):
        return self


class FakeQuoteContext:
    def __init__(self, result=(-1, "Connect timeout"), *, error=None, setter_error=False):
        self.result, self.error, self.setter_error = result, error, setter_error
        self.timeout = None
        self.closed = 0
        self.calls = []

    def set_sync_query_connect_timeout(self, timeout):
        if self.setter_error:
            raise RuntimeError("timeout setup failed")
        self.timeout = timeout

    def get_market_snapshot(self, _codes):
        self.calls.append("snapshot")
        if self.error:
            raise self.error
        return self.result

    def get_global_state(self):
        self.calls.append("global_state")
        if self.error:
            raise self.error
        return self.result

    def get_market_state(self, _codes):
        self.calls.append("market_state")
        return 0, FakeFrame([])

    def request_history_kline(self, *_args, **_kwargs):
        self.calls.append("history")
        if self.error:
            raise self.error
        return -1, "Connect timeout", None

    def close(self):
        self.closed += 1


class FutuConnectionTests(unittest.TestCase):
    def setUp(self):
        self.original_cache = dict(futu.FUTU_STATUS_CACHE)
        self.addCleanup(lambda: (futu.FUTU_STATUS_CACHE.clear(), futu.FUTU_STATUS_CACHE.update(self.original_cache)))
        futu.reset_futu_status_cache()
        self.env = patch.dict(os.environ, {"HAKIMI_LOCAL_ONLY": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.constructor_args = []

    def sdk(self, context):
        def create(**kwargs):
            self.constructor_args.append(kwargs)
            if kwargs.get("is_async_connect") is not True:
                raise AssertionError("synchronous constructor can retry indefinitely")
            return context
        return SimpleNamespace(RET_OK=0, OpenQuoteContext=create)

    def ready_transport(self):
        futu.update_futu_status_cache(online=True, message="TCP reachable", sdk_installed=True)

    def quote_patches(self, context):
        stack = ExitStack()
        stack.enter_context(patch.object(futu_quotes, "futu_status_snapshot", return_value={"opend_online": True}))
        stack.enter_context(patch.object(futu_quotes, "import_futu_sdk", return_value=(self.sdk(context), "")))
        stack.enter_context(patch.object(futu_quotes, "provider_call_allowed", return_value=(True, 0)))
        stack.enter_context(patch.object(futu_quotes, "record_provider_call"))
        return stack

    def test_constructor_is_async_and_connection_wait_has_fixed_upper_bound(self):
        context = FakeQuoteContext()
        returned = futu_context.open_futu_quote_context(self.sdk(context), host="127.0.0.1", port=11111)
        self.assertIs(returned, context)
        self.assertEqual(context.timeout, 5.0)
        self.assertEqual(self.constructor_args, [{"host": "127.0.0.1", "port": 11111, "is_async_connect": True}])
        returned.close()
        self.assertEqual(context.closed, 1)

    def test_setup_exception_closes_created_context(self):
        context = FakeQuoteContext(setter_error=True)
        with self.assertRaisesRegex(RuntimeError, "timeout setup failed"):
            futu_context.open_futu_quote_context(self.sdk(context), host="127.0.0.1", port=11111)
        self.assertEqual(context.closed, 1)

    def test_installed_sdk_pending_connection_loop_honors_configured_bound_without_network(self):
        spec = importlib.util.find_spec("futu")
        if spec is None:
            self.skipTest("Optional installed SDK source unavailable; no SDK is imported or connected.")
        source = Path(spec.origin).parent / "common" / "open_context_base.py"
        module = ast.parse(source.read_text(encoding="utf-8-sig"))
        cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "OpenContextBase")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_get_sync_query_processor")
        clock = [0.0]
        class Clock:
            @staticmethod
            def now():
                return datetime(2026, 1, 1) + timedelta(seconds=clock[0])
        def sleep(seconds):
            clock[0] += seconds
            if clock[0] > 5.1:
                raise AssertionError("SDK connection loop exceeded configured bound")
        namespace = {"datetime": Clock, "sleep": sleep, "RET_OK": 0, "RET_ERROR": -1,
                     "ContextStatus": SimpleNamespace(CLOSED="CLOSED")}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
        context = FakeQuoteContext()
        futu_context.open_futu_quote_context(self.sdk(context), host="127.0.0.1", port=11111)
        owner = SimpleNamespace(_lock=RLock(), _status="CONNECTING",
                                _sync_query_connect_timeout=context.timeout, can_send_proto=lambda _proto: False)
        processor = namespace["_get_sync_query_processor"](owner, lambda: (0, "", b"", 0, 0), lambda _data: None)
        self.assertEqual(processor(), (-1, "Connect timeout", None))
        self.assertGreaterEqual(round(clock[0], 6), 5.0)
        self.assertLessEqual(clock[0], 5.05)
        context.close()

    def test_tcp_reachable_does_not_claim_quote_readiness_or_login(self):
        with patch.object(futu, "import_futu_sdk", return_value=(object(), "")), \
                patch.object(futu, "futu_socket_online", return_value=(True, "TCP reachable")):
            result = futu.futu_status_snapshot(force=True)
        self.assertTrue(result["opend_online"])
        self.assertEqual(result["transport_status"], "REACHABLE")
        self.assertEqual(result["login_status"], "UNKNOWN")
        self.assertEqual(result["quote_status"], "UNKNOWN")
        self.assertEqual(next(row for row in result["steps"] if row["label"] == "行情通道")["state"], "unknown")

    def test_local_protection_is_distinct_from_offline_and_performs_no_probe(self):
        with patch.dict(os.environ, {"HAKIMI_LOCAL_ONLY": "1"}), \
                patch.object(futu, "import_futu_sdk") as importer, \
                patch.object(futu, "futu_socket_online") as probe:
            result = futu.futu_status_snapshot(force=True)
        importer.assert_not_called()
        probe.assert_not_called()
        self.assertEqual(result["transport_status"], "BLOCKED_LOCAL_MODE")
        self.assertEqual(result["login_status"], "UNKNOWN")
        self.assertEqual(result["quote_status"], "UNKNOWN")

    def test_explicit_refresh_checks_only_quote_login_boolean_and_closes_context(self):
        class QuoteLoginOnly(dict):
            def get(self, key, *args):
                if key != "qot_logined":
                    raise AssertionError("only quote login may be inspected")
                return super().get(key, *args)
        state = QuoteLoginOnly(qot_logined=True, trd_logined="fixture-private-trade", user_id="fixture-private-user")
        context = FakeQuoteContext((0, state))
        with patch.object(futu, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                patch.object(futu, "futu_socket_online", return_value=(True, "TCP reachable")), \
                patch.object(futu, "now_ms", return_value=1234567000):
            result = futu.futu_status_snapshot(force=True)
        self.assertEqual(result["login_status"], "LOGGED_IN")
        self.assertEqual(result["login_checked_at"], 1234567000)
        self.assertEqual(result["login_error_type"], "NONE")
        self.assertEqual(result["quote_status"], "UNKNOWN")
        self.assertEqual(context.calls, ["global_state"])
        self.assertEqual(context.timeout, 5.0)
        self.assertEqual(context.closed, 1)
        for forbidden in ("qot_logined", "trd_logined", "user_id", "fixture-private"):
            self.assertNotIn(forbidden, repr(result))
            self.assertNotIn(forbidden, repr(futu.FUTU_STATUS_CACHE))

    def test_explicit_refresh_false_and_malformed_login_state_are_distinct(self):
        for value, expected in ((False, "NOT_LOGGED_IN"), (None, "UNKNOWN"), ("1", "UNKNOWN"),
                                ("false", "UNKNOWN"), (1, "UNKNOWN")):
            with self.subTest(value=value):
                context = FakeQuoteContext((0, {"qot_logined": value}))
                with patch.object(futu, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                        patch.object(futu, "futu_socket_online", return_value=(True, "TCP reachable")):
                    result = futu.futu_status_snapshot(force=True)
                self.assertEqual(result["login_status"], expected)
                self.assertEqual(result["login_error_type"], "NONE" if value is False else "INVALID_LOGIN_STATE")
                self.assertGreater(result["login_checked_at"], 0)
                self.assertEqual(context.closed, 1)

    def test_ordinary_poll_does_not_query_login_even_when_tcp_cache_expires(self):
        self.ready_transport()
        futu.FUTU_STATUS_CACHE.update(time=0, login_status="LOGGED_IN", login_checked_at=123)
        with patch.object(futu, "import_futu_sdk", return_value=(object(), "")), \
                patch.object(futu, "futu_socket_online", return_value=(True, "TCP reachable")), \
                patch.object(futu, "open_futu_quote_context") as opener:
            result = futu.futu_status_snapshot()
        opener.assert_not_called()
        self.assertEqual(result["login_status"], "LOGGED_IN")
        self.assertEqual(result["login_checked_at"], 123)

    def test_login_check_failure_preserves_transport_but_never_keeps_confirmed_login(self):
        for context, expected in ((FakeQuoteContext((-1, "Connect timeout fixture-private-user")), "TIMEOUT"),
                                  (FakeQuoteContext(error=RuntimeError("SDK failure fixture-private-user")), "SDK_ERROR")):
            with self.subTest(error=expected):
                futu.FUTU_STATUS_CACHE.update(login_status="LOGGED_IN", login_checked_at=123)
                with patch.object(futu, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                        patch.object(futu, "futu_socket_online", return_value=(True, "TCP reachable")):
                    result = futu.futu_status_snapshot(force=True)
                self.assertEqual(result["transport_status"], "REACHABLE")
                self.assertEqual(result["login_status"], "UNKNOWN")
                self.assertEqual(result["login_error_type"], expected)
                self.assertNotIn("fixture-private-user", repr(result))
                self.assertEqual(context.closed, 1)

    def test_quote_success_or_nonlogin_error_does_not_overwrite_confirmed_login(self):
        self.ready_transport()
        futu.FUTU_STATUS_CACHE.update(login_status="LOGGED_IN", login_checked_at=123)
        for success, error in ((True, None), (False, "No permission"), (False, "Connect timeout"), (False, "other")):
            futu.update_futu_quote_status(success=success, error=error)
            self.assertEqual(futu.FUTU_STATUS_CACHE["login_status"], "LOGGED_IN")
            self.assertEqual(futu.FUTU_STATUS_CACHE["login_checked_at"], 123)
        futu.update_futu_quote_status(success=False, error="Please login first")
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_status"], "NOT_LOGGED_IN")
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_checked_at"], 0)
        futu.update_futu_quote_status(success=True)
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_status"], "NOT_LOGGED_IN")

    def test_disconnection_and_local_protection_clear_login_without_querying(self):
        for protected in (False, True):
            with self.subTest(local_only=protected):
                self.ready_transport()
                futu.FUTU_STATUS_CACHE.update(login_status="LOGGED_IN", login_checked_at=123)
                with patch.dict(os.environ, {"HAKIMI_LOCAL_ONLY": "1" if protected else "0"}), \
                        patch.object(futu, "import_futu_sdk", return_value=(object(), "")), \
                        patch.object(futu, "futu_socket_online", return_value=(False, "TCP unavailable")), \
                        patch.object(futu, "open_futu_quote_context") as opener:
                    result = futu.futu_status_snapshot(force=True)
                opener.assert_not_called()
                self.assertEqual(result["login_status"], "UNKNOWN")
                self.assertEqual(result["login_checked_at"], 0)

    def test_login_result_cannot_restore_state_after_concurrent_disconnect(self):
        self.ready_transport()
        context = FakeQuoteContext()
        def disconnect_before_result():
            futu.update_futu_status_cache(online=False, message="TCP unavailable")
            return 0, {"qot_logined": True}
        context.get_global_state = disconnect_before_result
        with patch.object(futu, "open_futu_quote_context", return_value=context):
            futu.check_futu_quote_login(self.sdk(context))
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_status"], "UNKNOWN")
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_checked_at"], 0)
        self.assertEqual(context.closed, 1)

    def test_permission_refusal_preserves_transport_and_closes_context(self):
        self.ready_transport()
        context = FakeQuoteContext((-1, "No permission for market snapshot"))
        with self.quote_patches(context):
            self.assertEqual(futu_quotes.read_futu_quotes(["AAPL"]), {})
        self.assertEqual(context.closed, 1)
        self.assertEqual(context.calls, ["snapshot"])
        self.assertTrue(futu.FUTU_STATUS_CACHE["online"])
        self.assertEqual(futu.FUTU_STATUS_CACHE["transport_status"], "REACHABLE")
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "ERROR")
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_error_type"], "PERMISSION_DENIED")

    def test_connection_timeout_returns_and_closes_without_retrying(self):
        self.ready_transport()
        context = FakeQuoteContext()
        with self.quote_patches(context):
            self.assertEqual(futu_quotes.read_futu_quotes(["AAPL"]), {})
        self.assertEqual(context.timeout, 5.0)
        self.assertEqual(context.calls, ["snapshot"])
        self.assertEqual(context.closed, 1)
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_error_type"], "TIMEOUT")
        self.assertTrue(futu.FUTU_STATUS_CACHE["online"])

    def test_request_exception_closes_context(self):
        context = FakeQuoteContext(error=RuntimeError("fixture request error"))
        with self.quote_patches(context):
            self.assertEqual(futu_quotes.read_futu_quotes(["AAPL"]), {})
        self.assertEqual(context.closed, 1)

    def test_deep_snapshot_failure_does_not_start_optional_queries_or_subscriptions(self):
        self.ready_transport()
        context = FakeQuoteContext((-1, "No permission for snapshot"))
        with patch.object(futu_deep, "futu_status_snapshot", return_value={"opend_online": True}), \
                patch.object(futu_deep, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                patch.dict(futu_deep.FUTU_DEEP_CACHE, {}, clear=True):
            result = futu_deep.read_futu_deep_stock("AAPL", force=True)
        self.assertFalse(result["ok"])
        self.assertEqual(context.calls, ["snapshot"])
        self.assertEqual(context.closed, 1)
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_error_type"], "PERMISSION_DENIED")
        self.assertTrue(futu.FUTU_STATUS_CACHE["online"])

    def test_history_request_failure_closes_context(self):
        context = FakeQuoteContext(error=RuntimeError("fixture history error"))
        with self.quote_patches(context):
            result = futu_quotes.read_futu_stock_candles("AAPL", limit=3)
        self.assertFalse(result["ok"])
        self.assertEqual(context.calls, ["history"])
        self.assertEqual(context.closed, 1)

    def test_valid_snapshot_records_quote_success_without_claiming_login_or_all_entitlements(self):
        self.ready_transport()
        context = FakeQuoteContext((0, FakeFrame([{"code": "US.AAPL", "last_price": 100,
                                                  "update_time": "2026-10-20 10:00:00"}])))
        with self.quote_patches(context):
            self.assertTrue(futu_quotes.read_futu_quotes(["AAPL"]))
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "READY")
        self.assertEqual(futu.FUTU_STATUS_CACHE["login_status"], "UNKNOWN")
        self.assertEqual(context.closed, 1)

    def test_transport_loss_invalidates_previous_quote_success(self):
        self.ready_transport()
        futu.update_futu_quote_status(success=True)
        futu.update_futu_status_cache(online=False, message="TCP unavailable")
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "UNKNOWN")
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_updated_at"], 0)

    def test_error_categories_do_not_return_provider_account_details(self):
        for message, expected in (("No permission user_id=123456", "PERMISSION_DENIED"),
                                  ("Please login first user_id=123456", "LOGIN_REQUIRED"),
                                  ("Connect timeout", "TIMEOUT"), ("RSA unavailable", "SDK_ERROR")):
            code, description = futu_context.classify_futu_error(message)
            self.assertEqual(code, expected)
            self.assertNotIn("123456", description)
            self.assertNotIn("user_id", description)

    def test_wrong_symbol_empty_code_and_nonfinite_prices_never_mark_snapshot_ready(self):
        bad_rows = [{"code": "US.MSFT", "last_price": 100}, {"code": "", "last_price": 100},
                    {"last_price": 100}, {"code": [], "last_price": 100}]
        bad_rows += [{"code": "US.AAPL", "last_price": value}
                     for value in (float("nan"), float("inf"), -float("inf"), "NaN", "inf", 0, -1, None, True)]
        for row in bad_rows:
            with self.subTest(row=row):
                self.ready_transport()
                futu.update_futu_quote_status(success=True)
                context = FakeQuoteContext((0, FakeFrame([row])))
                with self.quote_patches(context):
                    self.assertEqual(futu_quotes.read_futu_quotes(["AAPL"]), {})
                self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "ERROR")
                self.assertTrue(futu.FUTU_STATUS_CACHE["online"])
                self.assertEqual(context.calls, ["snapshot"])
                self.assertEqual(context.closed, 1)

    def test_mixed_snapshot_only_returns_the_exact_requested_symbol(self):
        rows = [{"code": "US.MSFT", "last_price": 999, "update_time": "2026-10-20 10:00:00"},
                {"code": "US.AAPL", "last_price": 100, "update_time": "2026-10-20 10:00:00"}]
        context = FakeQuoteContext((0, FakeFrame(rows)))
        with self.quote_patches(context):
            result = futu_quotes.read_futu_quotes(["AAPL"])
        self.assertEqual(list(result), ["AAPL"])
        self.assertEqual(result["AAPL"]["last"], 100)
        self.assertEqual(result["AAPL"]["futu_code"], "US.AAPL")
        self.assertEqual(context.closed, 1)

    def test_deep_wrong_symbol_or_invalid_price_stops_before_optional_queries(self):
        for code, price in (("US.MSFT", 100), ("", 100), ("US.AAPL", float("nan")),
                            ("US.AAPL", float("inf")), ("US.AAPL", 0), ("US.AAPL", True)):
            with self.subTest(code=code, price=price):
                self.ready_transport()
                futu.update_futu_quote_status(success=True)
                context = FakeQuoteContext((0, FakeFrame([{"code": code, "last_price": price,
                                                          "update_time": "2026-10-20 10:00:00"}])))
                with patch.object(futu_deep, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                        patch.dict(futu_deep.FUTU_DEEP_CACHE, {}, clear=True):
                    result = futu_deep.read_futu_deep_stock("AAPL", force=True)
                self.assertFalse(result["ok"])
                self.assertEqual(result["status"]["quote_status"], "ERROR")
                self.assertEqual(context.calls, ["snapshot"])
                self.assertEqual(context.closed, 1)

    def test_deep_exception_after_previous_ready_returns_updated_error_status(self):
        self.ready_transport()
        futu.update_futu_quote_status(success=True)
        self.assertEqual(futu.futu_status_snapshot()["quote_status"], "READY")
        with patch.object(futu_deep, "import_futu_sdk", return_value=(object(), "")), \
                patch.object(futu_deep, "open_futu_quote_context", side_effect=TimeoutError("Connect timeout")), \
                patch.dict(futu_deep.FUTU_DEEP_CACHE, {}, clear=True):
            result = futu_deep.read_futu_deep_stock("AAPL", force=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"]["quote_status"], "ERROR")
        self.assertEqual(result["status"]["quote_error_type"], "TIMEOUT")
        self.assertEqual(result["status"]["transport_status"], "REACHABLE")

    def test_missing_or_invalid_provider_time_stays_unknown_and_session_is_stale(self):
        for value in (None, "", "unparseable", "2026-99-99", True):
            with self.subTest(value=value), patch.object(futu, "now_ms", return_value=1792504800000):
                self.assertEqual(futu.parse_futu_time_key(value, "AAPL"), 0)
                quote = futu.normalize_futu_quote({"code": "US.AAPL", "last_price": 100,
                    "prev_close_price": 99, "update_time": value, "market_state": "MORNING"}, "AAPL")
                self.assertEqual(quote["ts"], 0)
                self.assertEqual(quote["timestamp_status"], "UNKNOWN")
                self.assertEqual(quote["status"], "STALE")
                self.assertEqual(quote["date"], "")
                self.assertEqual(quote["time"], "")
                # Delivery's canonical session contract distinguishes invalid
                # timestamps explicitly; retain its stricter admission gate.
                self.assertEqual(quote["market_session"]["status"], "TIME_INVALID")
                self.assertFalse(quote["market_session"]["analysis_ready"])
                self.assertFalse(quote["market_session"]["execution_eligible"])
                normalized = normalize_stock_quote_quality(quote, now_ms=1792504800000)
                self.assertEqual(normalized["quote_quality"]["status"], "REVIEW")
                self.assertFalse(normalized["quote_quality"]["time_quality"]["current"])
                self.assertIsNone(normalized["quote_quality"]["age_ms"])

    def test_futu_fractional_time_preserves_exact_milliseconds_in_market_timezones(self):
        cases = [
            ("AAPL", "2026-10-20 07:57:21.051", "2026-10-20T07:57:21-04:00", 51),
            ("AAPL", "2026-01-20 07:57:21.001", "2026-01-20T07:57:21-05:00", 1),
            ("HK.00700", "2026-10-20 16:08:00.999", "2026-10-20T16:08:00+08:00", 999),
        ]
        for symbol, source_time, whole_second, milliseconds in cases:
            with self.subTest(symbol=symbol, source_time=source_time):
                expected = int(datetime.fromisoformat(whole_second).timestamp()) * 1000 + milliseconds
                self.assertEqual(futu.parse_futu_time_key(source_time, symbol), expected)

    def test_fractional_support_preserves_existing_formats_and_invalid_time_rejection(self):
        self.assertEqual(futu.parse_futu_time_key("2026-10-20 16:08:00", "HK.00700"),
                         int(datetime.fromisoformat("2026-10-20T16:08:00+08:00").timestamp()) * 1000)
        self.assertEqual(futu.parse_futu_time_key("2026-10-20", "AAPL"),
                         int(datetime.fromisoformat("2026-10-20T00:00:00-04:00").timestamp()) * 1000)
        for value in ("2026-10-20 07:57:21.bad", "2026-13-20 07:57:21.051",
                      "2026-10-20 07:57:21.051Z", "2026-10-20 07:57:21.051 trailing"):
            with self.subTest(value=value):
                self.assertEqual(futu.parse_futu_time_key(value, "AAPL"), 0)

    def test_snapshot_with_provider_milliseconds_is_timestamped_and_quote_ready(self):
        self.ready_transport()
        context = FakeQuoteContext((0, FakeFrame([{
            "code": "US.AAPL", "last_price": 100, "prev_close_price": 99,
            "update_time": "2026-10-20 07:57:21.051",
        }])))
        expected = int(datetime.fromisoformat("2026-10-20T07:57:21-04:00").timestamp()) * 1000 + 51
        with self.quote_patches(context):
            result = futu_quotes.read_futu_quotes(["AAPL"])
        self.assertEqual(result["AAPL"]["ts"], expected)
        self.assertEqual(result["AAPL"]["timestamp_status"], "KNOWN")
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "READY")
        self.assertEqual(context.closed, 1)

    def test_real_quote_normalization_does_not_turn_unknown_time_into_ready(self):
        self.ready_transport()
        futu.update_futu_quote_status(success=True)
        context = FakeQuoteContext((0, FakeFrame([{"code": "US.AAPL", "last_price": 100}])))
        context.get_market_state = lambda _codes: (0, FakeFrame([{"code": "US.AAPL", "market_state": "MORNING"}]))
        with self.quote_patches(context):
            result = futu_quotes.read_futu_quotes(["AAPL"])
        self.assertEqual(result["AAPL"]["timestamp_status"], "UNKNOWN")
        self.assertEqual(result["AAPL"]["market_session"]["status"], "TIME_INVALID")
        self.assertFalse(result["AAPL"]["market_session"]["analysis_ready"])
        self.assertFalse(result["AAPL"]["market_session"]["execution_eligible"])
        self.assertEqual(futu.FUTU_STATUS_CACHE["quote_status"], "ERROR")
        self.assertEqual(context.closed, 1)

    def test_history_rejects_invalid_time_before_epoch_session_or_completion(self):
        context = FakeQuoteContext()
        context.request_history_kline = lambda *_args, **_kwargs: (
            0, FakeFrame([{"time_key": None, "close": 100}]), None)
        with self.quote_patches(context), patch.object(futu_quotes, "stock_session_from_ts") as session, \
                patch.object(futu_quotes, "stock_candle_complete_at") as completion:
            result = futu_quotes.read_futu_stock_candles("AAPL", limit=3)
        self.assertFalse(result["ok"])
        self.assertEqual(result["rows"], [])
        self.assertIn("timestamp", result["error"])
        session.assert_not_called()
        completion.assert_not_called()
        self.assertEqual(context.closed, 1)

    def test_unknown_quote_time_cannot_append_a_fresh_candle(self):
        rows = [{"ts": 1, "date": "2026-10-19", "close": 100}]
        with patch.object(futu_quotes, "stock_session_from_ts") as session:
            result = futu_quotes.augment_futu_candles_with_snapshot(
                "AAPL", rows, "1m", "all", 10,
                quote_reader=lambda _symbol: {"source": "futu", "last": 100, "ts": 0})
        self.assertIs(result, rows)
        session.assert_not_called()

    def test_deep_unknown_snapshot_time_is_not_ready_and_stops_optional_requests(self):
        self.ready_transport()
        context = FakeQuoteContext((0, FakeFrame([{"code": "US.AAPL", "last_price": 100}])))
        with patch.object(futu_deep, "import_futu_sdk", return_value=(self.sdk(context), "")), \
                patch.dict(futu_deep.FUTU_DEEP_CACHE, {}, clear=True):
            result = futu_deep.read_futu_deep_stock("AAPL", force=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["timestamp_status"], "UNKNOWN")
        self.assertEqual(result["status"]["quote_status"], "ERROR")
        self.assertEqual(context.calls, ["snapshot"])
        self.assertEqual(context.closed, 1)


if __name__ == "__main__":
    unittest.main()
