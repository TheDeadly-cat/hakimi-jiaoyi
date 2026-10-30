"""Offline access-gate tests: fake clock and transport, no actual market data."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import json
from threading import Barrier, Event
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.terminal_public_daily_access import (
    CHECK_STOCK, CHECK_UPDATE, PublicDailyAccess, PublicDailyAccessError,
)


SESSION = "local-session-0123456789abcdef"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/NDAQ?period1=1700000000&period2=1800000000&interval=1d&events=div%2Csplits&includePrePost=false"


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


def payload(operation="explicit-check-0001"):
    return {"operation_id": operation, "symbol": "NDAQ", "history_sessions": 60}


class PublicDailyAccessTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.fetcher = Mock(return_value=b'{"fixture":"not actual market data"}')
        self.gate = PublicDailyAccess(SESSION, fetcher=self.fetcher, clock=self.clock)
        self.socket = patch("socket.socket.connect", side_effect=AssertionError("No network in permission tests")).start()
        self.addCleanup(patch.stopall)

    def run_request(self, gate=None, data=None, action=CHECK_STOCK, url=URL):
        gate = gate or self.gate
        data = data or payload()
        return gate.run_once(SESSION, action, data, lambda: gate.fetch(url))

    def test_new_instance_is_disabled_and_no_default_fetcher_exists(self):
        self.assertEqual(self.gate.status()["state"], "DISABLED")
        self.assertEqual(self.gate.status()["allowed_actions"], [])
        with self.assertRaisesRegex(PublicDailyAccessError, "PERMISSION_REQUIRED"):
            self.run_request()
        with self.assertRaisesRegex(PublicDailyAccessError, "CONTEXT_REQUIRED"):
            self.gate.fetch(URL)
        with self.assertRaises(ValueError):
            PublicDailyAccess(SESSION, fetcher=None)
        with self.assertRaises(TypeError):
            PublicDailyAccess(SESSION)
        self.fetcher.assert_not_called()
        self.socket.assert_not_called()

    def test_one_explicit_check_consumes_once_and_does_not_leak_binding(self):
        data = payload()
        permission = self.gate.allow_once(SESSION, CHECK_STOCK, data)
        self.assertEqual(permission["state"], "AVAILABLE_ONCE")
        self.assertEqual(permission["actual_attempts"], 0)
        self.assertEqual(permission["unconsumed_authorizations"], 1)
        self.assertEqual(self.run_request(), self.fetcher.return_value)
        self.fetcher.assert_called_once_with(URL)
        state = self.gate.status()
        self.assertEqual(state["state"], "DISABLED")
        self.assertEqual(state["actual_attempts"], 1)
        self.assertEqual(state["consumed_authorizations"], 1)
        self.assertEqual(state["last_outcome"], "REQUEST_COMPLETED")
        for secret in (SESSION, data["operation_id"], data["symbol"], "fingerprint", "token", "ticket"):
            self.assertNotIn(secret, json.dumps(state))
        self.assertFalse(state["broker_allowed"])
        self.assertFalse(state["model_requests_allowed"])
        self.assertFalse(state["background_collection_allowed"])
        with self.assertRaisesRegex(PublicDailyAccessError, "CONSUMED"):
            self.run_request()
        with self.assertRaisesRegex(PublicDailyAccessError, "NOT_REUSABLE"):
            self.gate.allow_once(SESSION, CHECK_STOCK, data)
        self.assertEqual(self.fetcher.call_count, 1)

    def test_repeated_grant_is_idempotent_without_extending_queue_expiry(self):
        data = payload()
        self.gate.allow_once(SESSION, CHECK_STOCK, data)
        self.clock.value = 219
        self.gate.allow_once(SESSION, CHECK_STOCK, dict(reversed(list(data.items()))))
        self.assertEqual(self.gate.status()["unconsumed_authorizations"], 1)
        self.clock.value = 220
        operation = Mock()
        with self.assertRaisesRegex(PublicDailyAccessError, "EXPIRED"):
            self.gate.run_once(SESSION, CHECK_STOCK, data, operation)
        operation.assert_not_called()
        self.assertEqual(self.gate.status()["expired_unconsumed_authorizations"], 1)
        self.assertEqual(self.gate.status()["actual_attempts"], 0)
        with self.assertRaisesRegex(PublicDailyAccessError, "NOT_REUSABLE"):
            self.gate.allow_once(SESSION, CHECK_STOCK, data)
        self.fetcher.assert_not_called()

    def test_session_action_payload_and_operation_bindings_cannot_be_changed(self):
        data = payload()
        self.gate.allow_once(SESSION, CHECK_STOCK, data)
        variants = [("another-session-0123456789", CHECK_STOCK, data, "SESSION_MISMATCH"),
            (SESSION, CHECK_STOCK, {**data, "history_sessions": 20}, "PAYLOAD_MISMATCH"),
            (SESSION, CHECK_STOCK, {**data, "symbol": "AAPL"}, "PAYLOAD_MISMATCH"),
            (SESSION, CHECK_STOCK, payload("different-check-0002"), "PERMISSION_REQUIRED"),
            (SESSION, CHECK_UPDATE, {"operation_id":data["operation_id"],"input_id":"canon-" + "a" * 32}, "PAYLOAD_MISMATCH"),
            (SESSION, "terminal_run_task", data, "ACTION_NOT_ALLOWED")]
        operation = Mock()
        for session, action, changed, error in variants:
            with self.subTest(error=error), self.assertRaisesRegex(PublicDailyAccessError, error):
                self.gate.run_once(session, action, changed, operation)
        operation.assert_not_called()
        self.fetcher.assert_not_called()
        self.assertEqual(self.gate.status()["actual_attempts"], 0)
        self.run_request(data=dict(reversed(list(data.items()))))
        self.fetcher.assert_called_once()

    def test_strict_request_shape_cannot_smuggle_url_session_or_extra_scope(self):
        for data in ({**payload(),"url":URL}, {**payload(),"history_sessions":True},
                     {**payload(),"symbol":"../NDAQ"}, {**payload(),"session_id":SESSION},
                     {"operation_id":"x","symbol":"NDAQ","history_sessions":60}):
            with self.subTest(data=data), self.assertRaises(PublicDailyAccessError):
                self.gate.allow_once(SESSION, CHECK_STOCK, data)
        with self.assertRaises(PublicDailyAccessError):
            self.gate.allow_once(SESSION, CHECK_UPDATE, {"operation_id":"explicit-update-001","input_id":"a" * 24})
        self.assertEqual(self.gate.status()["unconsumed_authorizations"], 0)
        self.fetcher.assert_not_called()

    def test_only_fixed_https_yahoo_daily_query_and_bound_stock_are_forwarded(self):
        urls = [URL.replace("https:","http:"), URL.replace("query1.finance.yahoo.com","example.invalid"),
            URL.replace("query1.finance.yahoo.com","user@query1.finance.yahoo.com"),
            URL.replace("query1.finance.yahoo.com","query1.finance.yahoo.com:443"),
            URL.replace("/v8/finance/chart/","/v8/other/"), URL.replace("/NDAQ?","/AAPL?"),
            URL.replace("interval=1d","interval=1m"), URL.replace("includePrePost=false","includePrePost=true"),
            URL + "&token=not-permitted", URL + "&interval=1d", URL + "#fragment", "\n" + URL,
            URL.replace("events=div%2Csplits","events=splits"), URL.replace("period1=1700000000","period1=1900000000")]
        for index, url in enumerate(urls):
            data = payload(f"invalid-url-{index:04d}")
            self.gate.allow_once(SESSION, CHECK_STOCK, data)
            with self.subTest(url=url), self.assertRaisesRegex(PublicDailyAccessError, "URL_NOT_ALLOWED"):
                self.run_request(data=data, url=url)
        self.fetcher.assert_not_called()
        self.assertEqual(self.gate.status()["actual_attempts"], 0)
        data = {"operation_id":"explicit-update-0001","input_id":"canon-" + "a" * 32}
        self.gate.allow_once(SESSION, CHECK_UPDATE, data)
        self.run_request(action=CHECK_UPDATE, data=data)
        self.fetcher.assert_called_once_with(URL)

    def test_single_transport_exception_is_counted_without_retry_or_refund(self):
        self.fetcher.side_effect = OSError("fake unavailable source")
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        with self.assertRaises(OSError):
            self.run_request()
        state = self.gate.status()
        self.assertEqual(state["actual_attempts"], 1)
        self.assertEqual(state["last_outcome"], "FAILED_AFTER_REQUEST")
        self.assertEqual(state["requests_in_flight"], 0)
        self.assertFalse(state["automatic_retry"])
        with self.assertRaisesRegex(PublicDailyAccessError, "CONSUMED"):
            self.run_request()
        self.fetcher.assert_called_once()

    def test_second_fetch_in_same_operation_cannot_retry_even_after_caught_failure(self):
        self.fetcher.side_effect = OSError("fake source failure")
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        def operation():
            with self.assertRaises(OSError):
                self.gate.fetch(URL)
            with self.assertRaisesRegex(PublicDailyAccessError, "ALREADY_ATTEMPTED"):
                self.gate.fetch(URL)
        self.gate.run_once(SESSION, CHECK_STOCK, payload(), operation)
        self.fetcher.assert_called_once()
        self.assertEqual(self.gate.status()["actual_attempts"], 1)
        self.assertEqual(self.gate.status()["last_outcome"], "FAILED_AFTER_REQUEST")
        self.assertEqual(self.gate.request_status(SESSION, CHECK_STOCK, payload())["transport_outcome"], "FAILED")

    def test_revoke_unused_and_preparing_authorization_has_zero_transport_io(self):
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        self.gate.revoke()
        with self.assertRaisesRegex(PublicDailyAccessError, "REVOKED"):
            self.run_request()
        data = payload("preparing-check-0002")
        self.gate.allow_once(SESSION, CHECK_STOCK, data)
        def operation():
            status = self.gate.revoke()
            self.assertEqual(status["state"], "REVOKED_PREPARING")
            self.assertEqual(status["actual_attempts"], 0)
            self.gate.fetch(URL)
        with self.assertRaisesRegex(PublicDailyAccessError, "REVOKED"):
            self.gate.run_once(SESSION, CHECK_STOCK, data, operation)
        self.fetcher.assert_not_called()

    def test_revoke_inflight_does_not_claim_to_cancel_or_discard_returned_source(self):
        entered, release = Event(), Event()
        def fetch(url):
            entered.set()
            if not release.wait(3):
                raise AssertionError("test release missing")
            return b"retained response after revocation"
        gate = PublicDailyAccess(SESSION, fetcher=fetch, clock=self.clock)
        gate.allow_once(SESSION, CHECK_STOCK, payload())
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.run_request, gate)
            try:
                self.assertTrue(entered.wait(3))
                status = gate.revoke()
                self.assertEqual(status["state"], "REVOKED_IN_FLIGHT")
                self.assertEqual(status["actual_attempts"], 1)
                self.assertEqual(status["requests_in_flight"], 1)
                self.assertEqual(status["unconsumed_authorizations"], 0)
                self.assertFalse(status["request_cancellation_supported"])
            finally:
                release.set()
            self.assertEqual(future.result(3), b"retained response after revocation")
        self.assertEqual(gate.status()["state"], "DISABLED")
        self.assertEqual(gate.status()["last_outcome"], "COMPLETED_AFTER_REVOCATION")

    def test_concurrent_same_operation_consumes_once(self):
        start = Barrier(3)
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        def worker():
            start.wait(3)
            try:
                self.run_request()
                return "requested"
            except PublicDailyAccessError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker) for _ in range(2)]
            start.wait(3)
            outcomes = [future.result(3) for future in futures]
        self.assertEqual(sorted(outcomes), ["PUBLIC_DAILY_PERMISSION_CONSUMED", "requested"])
        self.fetcher.assert_called_once()
        self.assertEqual(self.gate.status()["actual_attempts"], 1)

    def test_request_context_is_thread_isolated_and_cannot_survive_operation_end(self):
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        saved_context = []
        def operation():
            saved_context.append(copy_context())
            with ThreadPoolExecutor(max_workers=1) as executor:
                with self.assertRaisesRegex(PublicDailyAccessError, "CONTEXT_REQUIRED"):
                    executor.submit(self.gate.fetch, URL).result(3)
                with self.assertRaisesRegex(PublicDailyAccessError, "THREAD_MISMATCH"):
                    executor.submit(saved_context[0].run, self.gate.fetch, URL).result(3)
            return self.gate.fetch(URL)
        self.gate.run_once(SESSION, CHECK_STOCK, payload(), operation)
        with self.assertRaisesRegex(PublicDailyAccessError, "CONTEXT_EXPIRED"):
            saved_context[0].run(self.gate.fetch, URL)
        with self.assertRaisesRegex(PublicDailyAccessError, "CONTEXT_REQUIRED"):
            self.gate.fetch(URL)
        self.fetcher.assert_called_once()

    def test_expiry_during_preparation_blocks_before_transport_and_read_status_is_stable(self):
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        before = self.gate.status()
        self.assertEqual(self.gate.status(), before)
        def operation():
            self.clock.value = 220
            return self.gate.fetch(URL)
        with self.assertRaisesRegex(PublicDailyAccessError, "EXPIRED"):
            self.gate.run_once(SESSION, CHECK_STOCK, payload(), operation)
        self.assertEqual(self.gate.status()["actual_attempts"], 0)
        self.assertEqual(self.gate.status()["last_outcome"], "FAILED_WITHOUT_REQUEST")
        self.fetcher.assert_not_called()

    def test_per_request_status_keeps_other_operations_attempts_separate_and_never_grants(self):
        first, second = payload(), payload("second-check-0002")
        self.gate.allow_once(SESSION, CHECK_STOCK, first)
        self.gate.allow_once(SESSION, CHECK_STOCK, second)
        self.run_request(data=first)
        self.assertEqual(self.gate.request_status(SESSION, CHECK_STOCK, first)["actual_attempts"], 1)
        before = self.gate.request_status(SESSION, CHECK_STOCK, second)
        self.assertEqual(before["actual_attempts"], 0)
        self.assertFalse(before["consumed"])
        self.assertEqual(self.gate.request_status(SESSION, CHECK_STOCK, second), before)
        with self.assertRaisesRegex(PublicDailyAccessError, "PAYLOAD_MISMATCH"):
            self.gate.request_status(SESSION, CHECK_STOCK, {**second,"symbol":"AAPL"})
        self.gate.revoke()
        self.assertTrue(self.gate.request_status(SESSION, CHECK_STOCK, second)["revoked"])
        self.fetcher.assert_called_once()

    def test_restart_and_close_cannot_restore_authorization_and_tombstones_are_bounded(self):
        self.gate.allow_once(SESSION, CHECK_STOCK, payload())
        restarted = PublicDailyAccess(SESSION, fetcher=self.fetcher, clock=self.clock)
        with self.assertRaisesRegex(PublicDailyAccessError, "PERMISSION_REQUIRED"):
            self.run_request(restarted)
        self.gate.close()
        with self.assertRaisesRegex(PublicDailyAccessError, "CLOSED"):
            self.run_request()
        with self.assertRaisesRegex(PublicDailyAccessError, "CLOSED"):
            self.gate.allow_once(SESSION, CHECK_STOCK, payload("new-check-0003"))
        limited = PublicDailyAccess(SESSION, fetcher=self.fetcher, clock=self.clock, max_records=1)
        limited.allow_once(SESSION, CHECK_STOCK, payload())
        limited.revoke()
        with self.assertRaisesRegex(PublicDailyAccessError, "CAPACITY_REACHED"):
            limited.allow_once(SESSION, CHECK_STOCK, payload("new-check-0004"))
        self.fetcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
