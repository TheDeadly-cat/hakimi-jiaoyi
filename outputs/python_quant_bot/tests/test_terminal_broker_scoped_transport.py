"""Fake connections only. No production gate, SDK import or shared journal claim."""
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256
import threading
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_scoped_transport as transport
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_terminal_broker_execution_plan import NOW
from tests.test_futu_us_equity_simulate_wire_v2 import (
    make_profile, make_codec, request_frame, response_frame, request_payload,
)


class FakeClock:
    def __init__(self):
        self.value = 100.0
        self.utc_offset = 0

    def monotonic(self):
        return self.value

    def utcnow(self):
        return NOW + timedelta(seconds=self.value - 100 + self.utc_offset)


class FixturePermit:
    """Explicit fake authorization; never returned by a production factory."""
    def __init__(self, profile):
        value = profile.as_dict()
        self.profile_id = value["id"]
        self.scopes = value["deduplication"]
        self.replayed = False
        self.revision = 0


class FixtureGate:
    def __init__(self):
        self.lock = threading.Lock()
        self.held = False
        self.stopped = False
        self.revision = 0
        self.contexts = []
        self.after = None
        self.enter_error = None
        self.exit_error = None

    @contextmanager
    def barrier(self, context, permit):
        with self.lock:
            self.held = True
            try:
                if self.enter_error:
                    raise self.enter_error
                assert not permit.replayed, "fixture replay never dispatches"
                assert not self.stopped and permit.revision == self.revision, "fixture stop/revision changed"
                assert context["profile_id"] == permit.profile_id
                assert context["account_scope_id"] == permit.scopes["account_scope_id"]
                assert context["intent_scope_id"] == permit.scopes["intent_scope_id"]
                assert context["mode"] == "OFFICIAL_SIMULATION"
                self.contexts.append(dict(context))
                yield
                if self.exit_error:
                    raise self.exit_error
            finally:
                self.held = False

    before_connect = barrier
    before_write = barrier

    def after_write(self, context, permit, written):
        assert not self.held
        if self.after:
            self.after(context, permit, written)


class Sink:
    def __init__(self):
        self.records = []
        self.fail = False

    def write(self, record):
        if self.fail:
            raise OSError("fixture sink unavailable")
        self.records.append(record)


class FakeConnection:
    def __init__(self, clock, gate):
        self.clock, self.gate = clock, gate
        self.connects = 0
        self.sent = bytearray()
        self.buffer = bytearray()
        self.parts = []
        self.read_parts = []
        self.responses = []
        self.requests = []
        self.send_calls = self.recv_calls = 0
        self.closed = False
        self.send_error = self.recv_error = self.close_error = None
        self.connect_delay = self.send_delay = self.recv_delay = 0
        self.block_receive = None
        self.block_connect = None
        self.close_delay = 0
        self.close_timeouts = []

    def connect(self, endpoint, *, timeout):
        assert self.gate.held and timeout == 0
        assert endpoint == {"host": "127.0.0.1", "port": 11111}
        self.connects += 1
    def wait_connected(self, *, timeout):
        assert not self.gate.held and timeout > 0
        if self.block_connect:
            entered, release = self.block_connect
            entered.set()
            assert release.wait(2)
        self.clock.value += self.connect_delay

    def send(self, data, *, timeout):
        assert self.gate.held and timeout == 0
        self.send_calls += 1
        self.clock.value += self.send_delay
        if self.send_error:
            raise self.send_error
        count = min(len(data), self.parts.pop(0)) if self.parts else len(data)
        self.sent.extend(data[:count])
        if len(self.sent) >= 44:
            body = codec.HEADER.unpack(bytes(self.sent[:44]))[6]
            if len(self.sent) == 44 + body:
                self.requests.append(bytes(self.sent)); self.sent.clear()
                if self.responses:
                    self.buffer.extend(self.responses.pop(0))
        return count

    def recv(self, maximum, *, timeout):
        assert not self.gate.held and timeout > 0
        self.recv_calls += 1
        if self.block_receive:
            entered, release = self.block_receive
            entered.set()
            assert release.wait(2), "test release missing"
        self.clock.value += self.recv_delay
        if self.recv_error:
            raise self.recv_error
        count = min(maximum, len(self.buffer), self.read_parts.pop(0) if self.read_parts else maximum)
        result = bytes(self.buffer[:count]); del self.buffer[:count]
        return result

    def peek(self, maximum, *, timeout):
        assert timeout == 0 and maximum == 1
        return bytes(self.buffer[:maximum])

    def close(self, *, timeout):
        assert 0 <= timeout <= 5
        self.closed = True
        self.close_timeouts.append(timeout)
        self.clock.value += self.close_delay
        if self.close_error:
            raise self.close_error


class ScopedTransportTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.create_connection", "sqlite3.connect", "subprocess.Popen"):
            blocked = patch(name, side_effect=AssertionError("fake transport only"))
            blocked.start(); self.addCleanup(blocked.stop)
        self.reset_fixture()

    def reset_fixture(self):
        self.profile = make_profile()
        self.clock, self.gate, self.sink = FakeClock(), FixtureGate(), Sink()
        self.connections = {}
        self.permit = FixturePermit(self.profile)
        self.codec = make_codec(self.profile, quote_connection_id=None, quote_user_id=None,
                                trade_connection_id=None, trade_user_id=None)
        self.subject = self.new_subject()

    def factory(self, channel):
        value = FakeConnection(self.clock, self.gate)
        self.connections[channel] = value
        return value

    def new_subject(self):
        return transport.ScopedTransport(self.profile, factory=self.factory, clock=self.clock,
                                         gate=self.gate, sink=self.sink, codec=self.codec)

    def connect(self, channel="trade"):
        value = self.subject.connect(channel, self.permit, 250)
        self.assertEqual(value.status, "CONNECTED_NOT_INITIALIZED")
        return self.connections[channel]

    def initialized(self, channel="trade", interval=30):
        connection = self.connect(channel)
        connection.responses.append(response_frame(channel + "_init", payload={"retType": 0,
                                   "s2c": {"keepAliveInterval": interval,
                                           "connID": 11 if channel == "quote" else 33, "loginUserID": 22}}))
        outcome = self.subject.exchange(channel, channel + "_init", request_frame(channel + "_init"), self.permit, 250)
        self.assertEqual(outcome.status, "RESPONSE_RECEIVED")
        return connection

    def exchange(self, connection, action="trade_submit", serial=2, payload=None, response=None):
        channel = wire.WIRE_ACTIONS[action][0]
        connection.responses.append(response if response is not None else response_frame(action, serial))
        return self.subject.exchange(channel, action, request_frame(action, serial, payload), self.permit, 250)

    def test_no_default_factory_or_production_gate_and_all_permissions_false(self):
        with self.assertRaises(TypeError):
            transport.ScopedTransport(self.profile)
        self.assertFalse(any(self.profile.as_dict()["permissions"].values()))
        self.assertFalse(self.subject.budget_snapshot()["persistent_journal"])
        self.assertFalse(self.subject.budget_snapshot()["permissions_granted"])

    def test_two_channels_handshake_and_scoped_response_do_not_claim_acceptance(self):
        trade, quote = self.initialized(), self.initialized("quote")
        value = self.exchange(trade)
        self.assertEqual(value.status, "RESPONSE_RECEIVED")
        self.assertEqual(value.economic_acceptance, "NOT_INFERRED")
        self.assertEqual(value.bytes_written, len(request_frame("trade_submit", 2)))
        self.assertFalse(value.automatic_retry)
        self.assertEqual(trade.connects, quote.connects, 1)
        expected = {"profile_id", "intent_scope_id", "account_scope_id", "mode", "channel", "action",
                    "frame_sha256", "serial", "offset", "total_bytes", "deadline"}
        self.assertTrue(all(set(c) == expected for c in self.gate.contexts))

    def test_stop_before_connect_never_constructs_connection(self):
        self.gate.stopped = True
        value = self.subject.connect("trade", self.permit, 250)
        self.assertEqual(value.status, "NOT_WRITTEN")
        self.assertEqual(self.connections, {})
        self.assertEqual(self.subject.budget_snapshot()["local_action_counts"]["trade_connect"], 1)

    def test_stop_before_send_and_changed_permit_never_write(self):
        for change in ("stop", "revision", "profile", "scope", "replayed"):
            self.reset_fixture()
            connection = self.initialized()
            before = connection.send_calls
            if change == "stop": self.gate.stopped = True
            elif change == "revision": self.gate.revision += 1
            elif change == "profile": self.permit.profile_id = "0" * 64
            elif change == "scope": self.permit.scopes = {**self.permit.scopes, "intent_scope_id": "0" * 64}
            else: self.permit.replayed = True
            value = self.exchange(connection)
            self.assertEqual(value.status, "NOT_WRITTEN")
            self.assertEqual(connection.send_calls, before)

    def test_partial_write_rechecks_same_frame_scope_and_stop_blocks_continuation(self):
        connection = self.initialized(); connection.parts = [9]
        self.gate.after = lambda *_: setattr(self.gate, "stopped", True)
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_written, 9)
        self.assertEqual(value.possible_bytes_written, 9)
        self.assertTrue(connection.closed)
        self.assertEqual(len(connection.requests), 1)  # handshake only
        again = self.subject.exchange("trade", "trade_submit", request_frame("trade_submit", 2), self.permit, 250)
        self.assertEqual(again.status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, 2)

    def test_every_partial_send_has_original_frame_hash_and_monotonic_offsets(self):
        connection = self.initialized(); connection.parts = [3, 11, 5]
        value = self.exchange(connection)
        self.assertEqual(value.status, "RESPONSE_RECEIVED")
        contexts = [c for c in self.gate.contexts if c["action"] == "trade_submit"]
        self.assertEqual([c["offset"] for c in contexts], [0, 3, 14, 19])
        self.assertEqual({c["frame_sha256"] for c in contexts}, {sha256(request_frame("trade_submit", 2)).hexdigest()})
        self.assertEqual(self.subject.budget_snapshot()["local_action_counts"]["trade_submit"], 1)

    def test_send_exception_and_after_write_failure_are_unknown_never_refunded_or_retried(self):
        connection = self.initialized(); connection.send_error = OSError("unknown bytes written")
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_written, 0)
        self.assertEqual(value.possible_bytes_written, len(request_frame("trade_submit", 2)))
        self.assertTrue(connection.closed)

    def test_journal_progress_callback_failure_after_full_write_is_unknown(self):
        connection = self.initialized()
        def fail(*_): raise OSError("fixture persistence error")
        self.gate.after = fail
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_written, len(request_frame("trade_submit", 2)))
        self.assertEqual(connection.recv_calls, 2)  # only handshake header/body

    def test_barrier_exit_failure_retains_known_partial_write_count(self):
        connection = self.initialized(); connection.parts = [7]
        self.gate.exit_error = OSError("fixture barrier release failed")
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_written, 7)
        self.assertEqual(value.possible_bytes_written, 7)
        self.assertEqual(connection.send_calls, 2)

    def test_response_wait_does_not_hold_stop_lock_and_has_no_queue(self):
        connection = self.initialized()
        entered, release = threading.Event(), threading.Event()
        connection.block_receive = entered, release
        result = []
        thread = threading.Thread(target=lambda: result.append(self.exchange(connection)))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.gate.lock.acquire(timeout=0.2))
            self.gate.stopped = True; self.gate.lock.release()
            with self.assertRaisesRegex(transport.TransportError, "busy_no_queue"):
                self.subject.exchange("trade", "trade_submit", request_frame("trade_submit", 3), self.permit, 250)
            with self.assertRaisesRegex(transport.TransportError, "busy_no_queue"):
                self.subject.close(105)
        finally:
            release.set(); thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].status, "RESPONSE_RECEIVED")  # already dispatched response is retained
        again = self.exchange(connection, "trade_observe", 3)
        self.assertEqual(again.status, "NOT_WRITTEN")

    def test_fragmented_header_and_body_are_bounded_and_reassembled(self):
        connection = self.initialized(); connection.read_parts = [1, 2, 5, 7, 3]
        value = self.exchange(connection)
        self.assertEqual(value.status, "RESPONSE_RECEIVED")
        self.assertEqual(value.bytes_received, len(response_frame("trade_submit", 2)))

    def test_response_oversize_header_is_rejected_before_body_read(self):
        connection = self.initialized(); before = connection.recv_calls
        header = codec.HEADER.pack(b"F", b"T", 2202, 0, 0, 2, 0x7fffffff, bytes(20), bytes(8))
        value = self.exchange(connection, response=header)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(connection.recv_calls - before, 1)
        self.assertEqual(value.bytes_received, 44)

    def test_trailing_frame_wrong_serial_protocol_and_hash_close_without_callback(self):
        good = response_frame("trade_submit", 2)
        frames = [good + good, response_frame("trade_submit", 3), response_frame("trade_fees", 2),
                  good[:-1] + b"x", b"XX" + good[2:]]
        for frame in frames:
            self.reset_fixture(); connection = self.initialized()
            value = self.exchange(connection, response=frame)
            self.assertEqual(value.status, "UNKNOWN")
            self.assertTrue(connection.closed)
            self.assertFalse(value.automatic_retry)

    def test_unsolicited_data_before_next_request_never_sends(self):
        connection = self.initialized(); before = connection.send_calls
        connection.buffer.extend(b"push")
        value = self.exchange(connection)
        self.assertEqual(value.status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, before)
        self.assertEqual(value.error, "unsolicited_or_trailing_data")

    def test_local_caps_prevent_reconnect_rehandshake_and_extra_observation(self):
        connection = self.initialized()
        again = self.subject.connect("trade", self.permit, 250)
        self.assertEqual(again.status, "NOT_WRITTEN")
        self.assertEqual(connection.connects, 1)
        self.reset_fixture(); connection = self.initialized()
        for serial in range(2, 7):
            self.assertEqual(self.exchange(connection, "trade_observe", serial).status, "RESPONSE_RECEIVED")
        self.assertEqual(self.exchange(connection, "trade_observe", 7).status, "NOT_WRITTEN")
        self.assertEqual(self.subject.budget_snapshot()["local_action_counts"]["trade_observe"], 5)

    def test_zero_budget_protocols_and_wrong_channel_never_write(self):
        for action in ("trade_heartbeat", "trade_unlock", "trade_subscribe", "trade_reconnect", "application_retry"):
            self.reset_fixture(); connection = self.initialized(); before = connection.send_calls
            frame = codec.pack_plaintext_frame(wire.WIRE_ACTIONS[action][1] or 9999, 2, b"{}").__bytes__()
            value = self.subject.exchange("trade", action, frame, self.permit, 250)
            self.assertEqual(value.status, "NOT_WRITTEN")
            self.assertEqual(connection.send_calls, before)

    def test_scope_escape_blocks_before_write(self):
        connection = self.initialized(); before = connection.send_calls
        payload = request_payload("trade_submit", 2); payload["c2s"]["header"]["trdEnv"] = 1
        value = self.exchange(connection, payload=payload)
        self.assertEqual(value.status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, before)

    def test_nonblocking_would_block_is_unknown_without_hidden_send_retry(self):
        connection = self.initialized(); connection.send_error = BlockingIOError("would block")
        before = connection.send_calls
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(connection.send_calls - before, 1)
        self.assertTrue(value.cleanup_confirmed)

    def test_connect_wait_is_outside_barrier_and_stop_prevents_first_frame(self):
        entered, release = threading.Event(), threading.Event()
        def factory(channel):
            connection = self.factory(channel)
            connection.block_connect = entered, release
            return connection
        self.subject._factory = factory
        results = []
        thread = threading.Thread(target=lambda: results.append(self.subject.connect("trade", self.permit, 250)))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertTrue(self.gate.lock.acquire(timeout=0.2))
            self.gate.stopped = True; self.gate.lock.release()
        finally:
            release.set(); thread.join(2)
        self.assertEqual(results[0].status, "CONNECTED_NOT_INITIALIZED")
        connection = self.connections["trade"]
        result = self.exchange(connection, "trade_init", 1)
        self.assertEqual(result.status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, 0)

    def test_connect_timeout_and_partial_deadline_expiry_do_not_retry(self):
        self.clock.value = 300
        value = self.subject.connect("trade", self.permit, 400)
        self.assertEqual(value.status, "NOT_WRITTEN")
        self.assertEqual(self.connections, {})
        self.reset_fixture(); connection = self.initialized(); connection.parts = [2]; connection.send_delay = 16
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_written, 2)
        self.assertEqual(connection.send_calls, 2)

    def test_late_response_is_unknown_not_renewed_by_completion(self):
        connection = self.initialized(); connection.recv_delay = 16
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.bytes_received, 44)

    def test_missing_handshake_interval_and_short_interval_stop_without_heartbeat(self):
        connection = self.connect()
        connection.responses.append(response_frame("trade_init", payload={"retType": 0, "s2c": {}}))
        value = self.subject.exchange("trade", "trade_init", request_frame("trade_init"), self.permit, 250)
        self.assertEqual(value.status, "UNKNOWN")
        self.reset_fixture(); connection = self.initialized(interval=1); self.clock.value += 2
        self.assertEqual(self.exchange(connection).status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, 1)

    def test_delayed_short_handshake_cannot_start_new_keepalive_period(self):
        connection = self.connect(); connection.recv_delay = 1
        connection.responses.append(response_frame("trade_init", payload={"retType": 0,
                                    "s2c": {"keepAliveInterval": 1}}))
        value = self.subject.exchange("trade", "trade_init", request_frame("trade_init"), self.permit, 250)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(value.error, "handshake_interval_already_elapsed")
        self.assertTrue(connection.closed)

    def test_wire_and_evidence_limits_remain_bounded_with_final_outcome(self):
        self.profile = make_profile(max_wire_bytes=8192, max_frame_bytes=1024,
                                    max_output_bytes=24576, max_observation_records=3)
        self.codec = make_codec(self.profile); self.permit = FixturePermit(self.profile)
        self.subject = self.new_subject()
        connection = self.connect()
        connection.responses.append(response_frame("trade_init"))
        value = self.subject.exchange("trade", "trade_init", request_frame("trade_init"), self.permit, 250)
        self.assertEqual(value.status, "UNKNOWN")
        budget = self.subject.budget_snapshot()
        self.assertLessEqual(budget["conservative_wire_bytes"], 8192)
        self.assertLessEqual(budget["output_bytes"], 8192)
        self.assertLessEqual(budget["observation_records"], 3)
        self.subject.close(105)
        final = self.subject.final_summary()
        self.assertEqual(final["status"], "UNKNOWN_PRESENT")
        self.assertLessEqual(self.subject.budget_snapshot()["output_bytes"], 24576)

    def test_sink_failure_before_write_and_cleanup_error_are_not_success(self):
        connection = self.initialized(); before = connection.send_calls
        self.sink.fail = True
        value = self.exchange(connection)
        self.assertEqual(value.status, "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, before)
        self.reset_fixture(); connection = self.initialized(); connection.close_error = OSError("close unknown")
        closed = self.subject.close(105)
        self.assertTrue(closed["closed"])
        self.assertFalse(closed["cleanup_confirmed"])

    def test_cleanup_failure_is_preserved_in_action_and_final_receipts(self):
        connection = self.initialized(); connection.close_error = OSError("fixture close failure")
        connection.recv_error = TimeoutError("fixture late response")
        value = self.exchange(connection)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertFalse(value.cleanup_confirmed)
        self.assertFalse(self.subject.close(105)["cleanup_confirmed"])
        self.assertFalse(self.subject.final_summary()["cleanup_confirmed"])

    def test_cleanup_deadline_is_shared_across_channels_without_new_allowance(self):
        trade, quote = self.initialized(), self.initialized("quote")
        trade.close_delay = 3
        trade.recv_error = TimeoutError("fixture failure")
        self.exchange(trade)
        quote.close_delay = 3
        quote.recv_error = TimeoutError("fixture failure")
        result = self.exchange(quote, "quote_runtime", 2)
        self.assertEqual(trade.close_timeouts, [5])
        self.assertEqual(quote.close_timeouts, [2])
        self.assertFalse(result.cleanup_confirmed)

    def test_zero_body_header_stops_after_one_header_read(self):
        connection = self.initialized(); before = connection.recv_calls
        raw = codec.HEADER.pack(b"F", b"T", 2202, 0, 0, 2, 0, bytes(20), bytes(8))
        value = self.exchange(connection, response=raw)
        self.assertEqual(value.status, "UNKNOWN")
        self.assertEqual(connection.recv_calls - before, 1)

    def test_complete_finite_action_set_preserves_final_summary_budget(self):
        self.initialized("quote"); self.initialized("trade")
        serial = {"quote": 2, "trade": 2}
        for action, limit in wire.PROTOCOL_LIMITS.items():
            channel, protocol = wire.WIRE_ACTIONS[action]
            if not limit or protocol in (None, 1001): continue
            for _ in range(limit):
                value = self.exchange(self.connections[channel], action, serial[channel])
                self.assertEqual(value.status, "RESPONSE_RECEIVED", action)
                serial[channel] += 1
        self.assertEqual(self.subject.budget_snapshot()["observation_records"], 50)
        self.subject.close(105)
        summary = self.subject.final_summary()
        self.assertEqual(summary["status"], "TRANSPORT_CLOSED")
        before = self.subject.budget_snapshot()
        self.assertEqual(self.subject.final_summary(), summary)
        self.assertEqual(self.subject.budget_snapshot(), before)
        self.assertLessEqual(before["output_bytes"], self.profile.as_dict()["wire_bounds"]["max_output_bytes"])

    def test_ordinary_output_exhaustion_cannot_consume_final_reserve(self):
        self.initialized()
        while True:
            try: self.subject._emit("fixture_log_flood", b"x" * 8000)
            except transport.TransportError: break
        remaining = 112 * 1024 - self.subject.budget_snapshot()["output_bytes"]
        if remaining > 256:
            self.subject._emit("fixture_log_flood", b"x" * (remaining - 256))
        before = self.connections["trade"].send_calls
        # This next action either has its acknowledgement slot reserved before
        # IO, or is refused immediately. Neither can consume final-summary bytes.
        try:
            result = self.exchange(self.connections["trade"])
            self.assertEqual(result.status, "NOT_WRITTEN")
        except transport.TransportError as error:
            self.assertEqual(str(error), "ordinary_output_budget_exhausted")
        self.assertEqual(self.connections["trade"].send_calls, before)
        self.subject.close(105)
        final = self.subject.final_summary()
        self.assertIn(final["status"], ("TRANSPORT_CLOSED", "UNKNOWN_PRESENT"))
        self.assertLessEqual(self.subject.budget_snapshot()["output_bytes"], 128 * 1024)

    def test_closed_transport_never_resumes_or_constructs_new_channels(self):
        connection = self.initialized()
        self.assertTrue(self.subject.close(105)["cleanup_confirmed"])
        self.assertTrue(connection.closed)
        with self.assertRaisesRegex(transport.TransportError, "unavailable"):
            self.subject.connect("quote", self.permit, 250)

    def test_clock_before_profile_creation_rejected_at_construction_and_connect(self):
        self.clock.utc_offset = -1
        with self.assertRaisesRegex(transport.TransportError, "clock_before_profile_creation"):
            self.new_subject()
        result = self.subject.connect("trade", self.permit, 250)
        self.assertEqual(result.status, "NOT_WRITTEN")
        self.assertEqual(result.error, "clock_before_profile_creation")
        self.assertEqual(self.connections, {})

    def test_clock_rollback_between_partial_writes_stops_and_still_releases_handle(self):
        connection = self.initialized(); connection.parts = [7]
        self.gate.after = lambda *_: setattr(self.clock, "utc_offset", -1)
        result = self.exchange(connection)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.error, "clock_before_profile_creation")
        self.assertEqual(result.bytes_written, 7)
        self.assertEqual(connection.send_calls, 2)
        self.assertTrue(result.cleanup_confirmed)
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
