"""Socket boundary units plus real TCP against an owned dynamic-port peer."""
import errno
import select
import socket
import time
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_loopback_socket as adapter
from tests.broker_loopback_server_fixture import OwnedLoopbackServer, endpoint_guard
from tests import test_futu_us_equity_simulate_wire_v2 as frames


class FakeSocket:
    def __init__(self):
        self.calls, self.receive = [], []
        self.connect_result, self.error = 0, 0
        self.send_result = None
        self.close_error = None

    def setblocking(self, value): self.calls.append(("blocking", value))
    def connect_ex(self, endpoint):
        self.calls.append(("connect", endpoint)); return self.connect_result
    def getsockopt(self, *args): self.calls.append(("error", args)); return self.error
    def send(self, value):
        self.calls.append(("send", value))
        if isinstance(self.send_result, Exception): raise self.send_result
        return len(value) if self.send_result is None else self.send_result
    def recv(self, maximum, *flags):
        self.calls.append(("recv", maximum, flags))
        value = self.receive.pop(0)
        if isinstance(value, Exception): raise value
        return value
    def close(self):
        self.calls.append(("close",))
        if self.close_error: raise self.close_error


class LoopbackSocketBoundaryTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket, "socket", side_effect=AssertionError("unit test cannot create a real fd"))
        guard.start(); self.addCleanup(guard.stop)
        self.endpoint = dict(host="127.0.0.1", port=49177)  # Never connected; injected fd only.
        self.fd = FakeSocket()
        self.subject = adapter.LoopbackWireConnection(self.endpoint)
        self.subject._open_socket = lambda: self.fd

    def connected(self):
        self.subject.connect(self.endpoint, timeout=0)
        self.subject.wait_connected(timeout=1)
        return self.subject

    def test_import_construction_factory_and_invalid_endpoints_do_no_io(self):
        bound = adapter.pinned_loopback_factory(self.endpoint)
        self.endpoint["port"] += 1
        self.assertEqual(bound("trade")._endpoint, ("127.0.0.1", 49177))
        with self.assertRaises(adapter.LoopbackSocketError): bound("other")
        for endpoint in ({"host": "localhost", "port": 49177}, {"host": "::1", "port": 49177},
                         {"host": "0.0.0.0", "port": 49177}, {"host": "192.0.2.1", "port": 49177},
                         {"host": "127.0.0.1", "port": True}, {"host": "127.0.0.1", "port": 0}):
            with self.subTest(endpoint=endpoint), self.assertRaises(adapter.LoopbackSocketError):
                adapter.LoopbackWireConnection(endpoint)
        self.assertEqual(self.fd.calls, [])

    def test_nonblocking_connect_once_and_endpoint_cannot_change(self):
        with self.assertRaises(adapter.LoopbackSocketError):
            self.subject.connect(dict(self.endpoint, port=49178), timeout=0)
        self.connected()
        self.assertEqual(self.fd.calls, [("blocking", False), ("connect", ("127.0.0.1", 49177))])
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.connect(self.endpoint, timeout=0)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.wait_connected(timeout=1)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "connect"]), 1)

    def test_pending_connection_checks_so_error_once_without_reconnect(self):
        self.fd.connect_result = errno.EINPROGRESS
        self.subject.connect(self.endpoint, timeout=0)
        with patch.object(select, "select", return_value=([], [self.fd], [])) as wait:
            self.subject.wait_connected(timeout=.1)
        self.assertEqual(wait.call_count, 1)
        self.assertEqual([x[0] for x in self.fd.calls], ["blocking", "connect", "error"])

    def test_injected_connect_error_and_wait_timeout_never_retry(self):
        self.fd.connect_result = errno.ECONNREFUSED
        with self.assertRaises(OSError): self.subject.connect(self.endpoint, timeout=0)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.connect(self.endpoint, timeout=0)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "connect"]), 1)
        other = adapter.LoopbackWireConnection(self.endpoint)
        other._open_socket = lambda: self.fd
        self.fd.connect_result = errno.EINPROGRESS
        other.connect(self.endpoint, timeout=0)
        with patch.object(select, "select", return_value=([], [], [])) as wait:
            with self.assertRaises(TimeoutError): other.wait_connected(timeout=.01)
        self.assertEqual(wait.call_count, 1)
        with self.assertRaises(adapter.LoopbackSocketError): other.wait_connected(timeout=.01)

    def test_injected_async_connection_error_is_not_success(self):
        self.fd.connect_result, self.fd.error = errno.EINPROGRESS, errno.ECONNREFUSED
        self.subject.connect(self.endpoint, timeout=0)
        with patch.object(select, "select", return_value=([], [], [self.fd])):
            with self.assertRaises(OSError): self.subject.wait_connected(timeout=.1)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.send(b"x", timeout=0)

    def test_injected_short_write_and_would_block_are_single_os_attempts(self):
        self.connected(); self.fd.send_result = 3
        self.assertEqual(self.subject.send(b"abcdefgh", timeout=0), 3)
        self.fd.send_result = BlockingIOError(errno.EWOULDBLOCK, "injected would block")
        with self.assertRaises(BlockingIOError): self.subject.send(b"remaining", timeout=0)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "send"]), 2)
        self.assertFalse(any(x[0] == "recv" for x in self.fd.calls))

    def test_peek_would_block_is_not_eof_and_real_empty_is_remembered(self):
        self.connected()
        self.fd.receive = [BlockingIOError(errno.EWOULDBLOCK, "injected idle"), b"x", b""]
        self.assertEqual(self.subject.peek(1, timeout=0), b"")
        self.assertFalse(self.subject._peer_eof)
        self.assertEqual(self.subject.send(b"one", timeout=0), 3)
        self.assertEqual(self.subject.peek(1, timeout=0), b"x")
        self.assertEqual(self.subject.peek(1, timeout=0), b"")
        self.assertTrue(self.subject._peer_eof)
        before = list(self.fd.calls)
        self.assertEqual(self.subject.peek(1, timeout=0), b"")
        self.assertEqual(self.subject.recv(5, timeout=.1), b"")
        with self.assertRaises(ConnectionError): self.subject.send(b"two", timeout=0)
        self.assertEqual(self.fd.calls, before)

    def test_bounded_receive_waits_outside_send_and_preserves_short_bytes(self):
        self.connected(); self.fd.receive = [b"ab", b""]
        with patch.object(select, "select", return_value=([self.fd], [], [])) as wait:
            self.assertEqual(self.subject.recv(20, timeout=.1), b"ab")
            self.assertEqual(self.subject.recv(20, timeout=.1), b"")
        self.assertEqual(wait.call_count, 2)
        self.assertTrue(self.subject._peer_eof)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "recv"]), 2)

    def test_expired_wait_does_not_read_or_renew_timeout(self):
        self.connected()
        values = iter((10, 10.5, 11))
        self.subject._clock = lambda: next(values)
        with patch.object(select, "select", return_value=([self.fd], [], [])) as wait:
            with self.assertRaises(TimeoutError): self.subject.recv(4, timeout=1)
        self.assertEqual(wait.call_count, 1)
        self.assertEqual(wait.call_args.args[-1], .5)
        self.assertFalse(any(x[0] == "recv" for x in self.fd.calls))

    def test_invalid_bounds_and_blocking_begins_never_enter_os(self):
        for timeout in (None, True, float("nan"), float("inf"), -1, .01):
            with self.subTest(timeout=timeout), self.assertRaises(adapter.LoopbackSocketError):
                self.subject.connect(self.endpoint, timeout=timeout)
        self.assertEqual(self.fd.calls, [])
        self.connected(); before = list(self.fd.calls)
        for maximum in (0, True, 65537):
            with self.assertRaises(adapter.LoopbackSocketError): self.subject.recv(maximum, timeout=1)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.recv(1, timeout=16)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.peek(2, timeout=0)
        self.assertEqual(self.fd.calls, before)

    def test_close_is_idempotent_and_never_reconnects_or_sends(self):
        self.connected()
        self.subject.close(timeout=0); self.subject.close(timeout=1)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "close"]), 1)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.connect(self.endpoint, timeout=0)
        with self.assertRaises(adapter.LoopbackSocketError): self.subject.send(b"x", timeout=0)

    def test_failed_close_remains_unconfirmed_without_retry(self):
        self.connected(); self.fd.close_error = OSError("injected close failure")
        with self.assertRaises(OSError): self.subject.close(timeout=1)
        with self.assertRaisesRegex(adapter.LoopbackSocketError, "close_unconfirmed"):
            self.subject.close(timeout=1)
        self.assertEqual(len([x for x in self.fd.calls if x[0] == "close"]), 1)


class RealLoopbackSocketTests(unittest.TestCase):
    def setup_peer(self, **kwargs):
        peer = OwnedLoopbackServer(**kwargs)
        self.addCleanup(peer.close)
        guard = endpoint_guard(peer.endpoint)
        self.addCleanup(guard.close)
        connection = adapter.LoopbackWireConnection(peer.endpoint)
        self.addCleanup(lambda: connection.close(timeout=1))
        connection.connect(peer.endpoint, timeout=0)
        connection.wait_connected(timeout=1)
        self.assertTrue(peer.accepted.wait(1))
        return peer, connection

    def test_real_idle_peek_and_fragmented_reply_preserve_exact_bytes(self):
        peer, connection = self.setup_peer(fragmented=True)
        self.assertEqual(connection.peek(1, timeout=0), b"")
        self.assertFalse(connection._peer_eof)
        request = frames.request_frame("trade_init", 1)
        self.assertEqual(connection.send(request, timeout=0), len(request))
        expected = frames.response_frame("trade_init", 1)
        result = bytearray(); deadline = time.monotonic() + 2
        while len(result) < len(expected):
            result.extend(connection.recv(len(expected) - len(result), timeout=min(1, deadline - time.monotonic())))
        self.assertEqual(bytes(result), expected)
        self.assertEqual(peer.frames, [request])
        self.assertEqual(peer.errors, [])

    def test_real_eof_does_not_erase_complete_response_and_blocks_next_send(self):
        peer, connection = self.setup_peer(fin_after="trade_init")
        request = frames.request_frame("trade_init", 1)
        connection.send(request, timeout=0)
        expected = frames.response_frame("trade_init", 1)
        result = bytearray()
        while len(result) < len(expected): result.extend(connection.recv(len(expected) - len(result), timeout=1))
        self.assertTrue(peer.fin_sent.wait(1))
        self.assertTrue(select.select([connection._socket], [], [], 1)[0])
        self.assertEqual(connection.peek(1, timeout=0), b"")
        self.assertTrue(connection._peer_eof)
        self.assertEqual(bytes(result), expected)
        with self.assertRaises(ConnectionError): connection.send(request, timeout=0)
        self.assertEqual(peer.frames, [request])

    def test_real_recv_timeout_has_one_connection_and_no_invented_bytes(self):
        peer, connection = self.setup_peer(stall_on="trade_init")
        connection.send(frames.request_frame("trade_init", 1), timeout=0)
        self.assertTrue(peer.frame_received.wait(1))
        start = time.monotonic()
        with self.assertRaises(TimeoutError): connection.recv(44, timeout=.05)
        self.assertLess(time.monotonic() - start, .5)
        self.assertFalse(connection._peer_eof)
        self.assertEqual(len(peer.clients), 1)


if __name__ == "__main__":
    unittest.main()
