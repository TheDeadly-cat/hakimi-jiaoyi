"""Explicit pinned-loopback TCP IO, not broker authority or protocol admission.

No socket is created by construction/import and no default factory is installed.
The trusted caller supplies the endpoint and still owns authorization, journal,
frame validation and hard worker deadlines. Each connect/send/recv/peek performs
at most one underlying IO attempt; there is no DNS, sendall, reconnect or queue.
"""
from contextlib import contextmanager
import errno
import math
import select
import socket
from threading import Lock
import time


MAX_BYTES = 65536
_PENDING = frozenset(getattr(errno, name) for name in
    ("EINPROGRESS", "EWOULDBLOCK", "EALREADY", "WSAEINPROGRESS", "WSAEWOULDBLOCK", "WSAEALREADY")
    if hasattr(errno, name))


class LoopbackSocketError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise LoopbackSocketError(reason)


def _endpoint(value):
    _require(type(value) is dict and set(value) == {"host", "port"}
        and type(value["host"]) is str and value["host"] == "127.0.0.1"
        and type(value["port"]) is int and 1 <= value["port"] <= 65535,
        "explicit_ipv4_loopback_endpoint_required")
    return value["host"], value["port"]


def _timeout(value, *, wait=False, cleanup=False):
    _require(type(value) in (int, float) and math.isfinite(value), "finite_timeout_required")
    if wait:
        _require(0 < value <= 15, "bounded_wait_required")
    elif cleanup:
        _require(0 <= value <= 5, "bounded_cleanup_required")
    else:
        _require(value == 0, "nonblocking_begin_required")
    return value


class LoopbackWireConnection:
    """One owned IPv4 socket, permanently pinned to one explicit endpoint.

    The fd stays nonblocking throughout. Waiting is only in wait_connected and
    recv, which ScopedTransport calls outside its actual-write stop barrier.
    The process supervisor remains responsible for an unresponsive OS call.
    """
    def __init__(self, endpoint, *, clock=time.monotonic):
        self._endpoint = _endpoint(endpoint)
        _require(callable(clock), "monotonic_clock_required")
        self._clock = clock
        self._socket = None
        self._state = "NEW"
        self._waited = False
        self._peer_eof = False
        self._close_failed = False
        self._lock = Lock()

    @contextmanager
    def _exclusive(self):
        _require(self._lock.acquire(blocking=False), "socket_busy_no_queue")
        try:
            yield
        finally:
            self._lock.release()

    def _connected(self):
        _require(self._state == "CONNECTED" and self._waited and self._socket is not None,
                 "connected_socket_required")
        return self._socket

    @staticmethod
    def _open_socket():
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _wait(self, timeout, *, writing):
        deadline = self._clock() + _timeout(timeout, wait=True)
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise TimeoutError("socket_wait_expired")
        fd = self._socket
        readable, writable, exceptional = select.select([] if writing else [fd],
            [fd] if writing else [], [fd], remaining)
        if self._clock() >= deadline or not (writable if writing else readable) and not exceptional:
            raise TimeoutError("socket_wait_expired")
        if writing:
            error = fd.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error:
                raise OSError(error, "loopback_connect_failed")
            _require(fd in writable, "connection_completion_unconfirmed")

    def connect(self, endpoint, *, timeout):
        _timeout(timeout)
        _require(_endpoint(endpoint) == self._endpoint, "pinned_endpoint_changed")
        with self._exclusive():
            _require(self._state == "NEW", "one_connection_attempt_only")
            self._state = "CONNECTING"
            try:
                self._socket = self._open_socket()
                self._socket.setblocking(False)
                result = self._socket.connect_ex(self._endpoint)
                _require(type(result) is int, "connect_result_invalid")
                if result == 0:
                    self._state = "CONNECTED"
                elif result not in _PENDING:
                    raise OSError(result, "loopback_connect_failed")
            except Exception:
                # Caller owns cleanup. Failure never authorizes a fresh fd or
                # another connection attempt on this connection object.
                self._state = "FAILED"
                raise

    def wait_connected(self, *, timeout):
        _timeout(timeout, wait=True)
        with self._exclusive():
            _require(self._state in {"CONNECTING", "CONNECTED"} and not self._waited,
                     "one_connection_wait_only")
            self._waited = True
            try:
                if self._state == "CONNECTING":
                    self._wait(timeout, writing=True)
                    self._state = "CONNECTED"
            except Exception:
                self._state = "FAILED"
                raise

    def send(self, data, *, timeout):
        _timeout(timeout)
        _require(type(data) is bytes and 0 < len(data) <= MAX_BYTES, "bounded_send_bytes_required")
        with self._exclusive():
            fd = self._connected()
            if self._peer_eof:
                raise ConnectionError("peer_eof_before_send")
            # BlockingIOError and interrupted/failed sends propagate once. The
            # caller conservatively records UNKNOWN; never retry implicitly.
            written = fd.send(data)
            _require(type(written) is int and 0 < written <= len(data), "send_count_invalid")
            return written

    def recv(self, maximum, *, timeout):
        _timeout(timeout, wait=True)
        _require(type(maximum) is int and 1 <= maximum <= MAX_BYTES, "bounded_receive_required")
        with self._exclusive():
            fd = self._connected()
            if self._peer_eof:
                return b""
            self._wait(timeout, writing=False)
            data = fd.recv(maximum)
            _require(type(data) is bytes and len(data) <= maximum, "receive_bytes_invalid")
            if not data:
                self._peer_eof = True
            return data

    def peek(self, maximum, *, timeout):
        _timeout(timeout)
        _require(type(maximum) is int and maximum == 1, "one_byte_peek_required")
        with self._exclusive():
            fd = self._connected()
            if self._peer_eof:
                return b""
            try:
                data = fd.recv(1, socket.MSG_PEEK)
            except BlockingIOError:
                return b""  # No currently visible data; NOT proof of EOF.
            _require(type(data) is bytes and len(data) <= 1, "peek_bytes_invalid")
            if not data:
                # Preserve a complete frame already read before FIN. Returning
                # b'' satisfies the no-trailing-bytes check, while a subsequent
                # send is refused without entering the OS send operation.
                self._peer_eof = True
            return data

    def close(self, *, timeout):
        _timeout(timeout, cleanup=True)
        with self._exclusive():
            if self._state == "CLOSED":
                _require(not self._close_failed, "socket_close_unconfirmed")
                return
            fd, self._socket = self._socket, None
            self._state = "CLOSED"
            if fd is not None:
                try:
                    # No shutdown RPC, lingering option, flush loop or wait.
                    fd.close()
                except Exception:
                    self._close_failed = True
                    raise


def pinned_loopback_factory(endpoint):
    """Explicit dependency constructor; this function grants no permission."""
    pinned = _endpoint(endpoint)

    def factory(channel):
        _require(channel in {"quote", "trade"}, "explicit_channel_required")
        return LoopbackWireConnection(dict(host=pinned[0], port=pinned[1]))

    return factory
