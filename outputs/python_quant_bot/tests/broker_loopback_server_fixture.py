"""Finite synthetic TCP peer on a listener held by this test for its lifetime."""
import builtins
from contextlib import ExitStack
import json
import socket
from threading import Event, Lock, Thread
import time
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services.terminal_broker_wire_profile import WIRE_ACTIONS
from tests import test_futu_us_equity_simulate_wire_v2 as frames
from tests.broker_action_coordinator_fixture import Fixture


class OwnedLoopbackServer:
    def __init__(self, *, fragmented=False, fin_after=None, eof_on_accept=False, stall_on=None):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.listener.settimeout(.05)
        host, port = self.listener.getsockname()
        assert host == "127.0.0.1" and port != 11111
        self.endpoint = dict(host=host, port=port)
        self.fragmented, self.fin_after = fragmented, fin_after
        self.eof_on_accept, self.stall_on = eof_on_accept, stall_on
        self.stop, self.accepted, self.frame_received, self.fin_sent = Event(), Event(), Event(), Event()
        self.frames, self.partial, self.errors, self.clients = [], [], [], []
        self.received_chunks = []  # Actual recv bytes, including an unfinished frame before peer death.
        self.replies = {}
        self.expected = None
        self._lock = Lock()
        self._bytes = 0
        self._deadline = time.monotonic() + 20
        self._threads = []
        thread = Thread(target=self._accept, daemon=True, name="owned-loopback-accept")
        self._threads.append(thread); thread.start()

    def _count(self, length):
        with self._lock:
            self._bytes += length
            assert self._bytes <= 384 * 1024, "bounded synthetic peer byte budget"

    def _accept(self):
        try:
            while not self.stop.is_set() and time.monotonic() < self._deadline:
                if len(self.clients) >= 2:
                    self.stop.wait(.01)
                    continue
                try:
                    connection, peer = self.listener.accept()
                except TimeoutError:
                    continue
                assert peer[0] == "127.0.0.1"
                connection.settimeout(.05)
                with self._lock:
                    self.clients.append(connection)
                self.accepted.set()
                thread = Thread(target=self._serve, args=(connection,), daemon=True, name="owned-loopback-peer")
                self._threads.append(thread); thread.start()
        except Exception as error:
            if not self.stop.is_set():
                self.errors.append(repr(error))

    def _read(self, connection, count):
        value = bytearray()
        while len(value) < count and not self.stop.is_set() and time.monotonic() < self._deadline:
            try:
                part = connection.recv(count - len(value))
            except TimeoutError:
                continue
            except OSError:
                # A killed Windows peer may reset instead of sending FIN. The
                # already received prefix is still an observed fact in either case.
                if value:
                    self.partial.append(bytes(value))
                raise
            if not part:
                if value:
                    self.partial.append(bytes(value))
                return None
            self._count(len(part)); value.extend(part)
            self.received_chunks.append(bytes(part))
        return bytes(value) if len(value) == count else None

    def _send(self, connection, value):
        # Explicit finite server fragmentation, not a client retry or an SDK.
        parts = [value[i:i + 3] for i in range(0, len(value), 3)] if self.fragmented else [value]
        for part in parts:
            if self.stop.is_set():
                return
            self._count(len(part))
            connection.sendall(part)
            if self.fragmented:
                self.stop.wait(.001)

    def _serve(self, connection):
        try:
            if self.eof_on_accept:
                connection.shutdown(socket.SHUT_WR)
                self.fin_sent.set()
            for _ in range(16):
                header = self._read(connection, 44)
                if header is None:
                    return
                parsed = codec.HEADER.unpack(header)
                protocol, serial, length = parsed[2], parsed[5], parsed[6]
                assert 0 < length <= 65536 - 44
                body = self._read(connection, length)
                if body is None:
                    self.partial.append(header)
                    return
                frame = header + body
                if self.expected is not None:
                    assert frame in self.expected, "peer received an unbound frame"
                self.frames.append(frame)
                self.frame_received.set()
                action = "trade_init" if protocol == 1001 else next(k for k, v in WIRE_ACTIONS.items() if v == ("trade", protocol))
                if action == self.stall_on:
                    self.stop.wait(max(0, self._deadline - time.monotonic()))
                    return
                payload = self.replies.get(action)
                response = payload if type(payload) is bytes else frames.response_frame(action, serial,
                    payload=payload if payload is not None else Fixture.response(action))
                self._send(connection, response)
                if action == self.fin_after:
                    connection.shutdown(socket.SHUT_WR)
                    self.fin_sent.set()
        except (OSError, StopIteration) as error:
            if not self.stop.is_set():
                self.errors.append(repr(error))
        except Exception as error:
            self.errors.append(repr(error))
        finally:
            connection.close()

    def close(self):
        self.stop.set()
        self.listener.close()
        for connection in self.clients:
            connection.close()
        deadline = time.monotonic() + 2
        for thread in tuple(self._threads):
            thread.join(max(0, deadline - time.monotonic()))
        assert not any(t.is_alive() for t in self._threads), "owned local server thread not stopped"


def endpoint_guard(endpoint):
    """Allow only this already-listening peer; no DNS, other ports or SDK."""
    stack = ExitStack()
    allowed = (endpoint["host"], endpoint["port"])
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    original_import = builtins.__import__

    def connect(sock, address):
        assert address == allowed, "only the owned listener endpoint is allowed"
        return original_connect(sock, address)

    def connect_ex(sock, address):
        assert address == allowed, "only the owned listener endpoint is allowed"
        return original_connect_ex(sock, address)

    def no_sdk(name, *args, **kwargs):
        assert name != "futu" and not name.startswith("futu."), "no SDK"
        return original_import(name, *args, **kwargs)

    def denied(*args, **kwargs):
        raise AssertionError("No DNS, high-level connection helper or extra listener")

    stack.enter_context(patch.object(socket.socket, "connect", connect))
    stack.enter_context(patch.object(socket.socket, "connect_ex", connect_ex))
    stack.enter_context(patch.object(socket, "getaddrinfo", denied))
    stack.enter_context(patch.object(socket, "create_connection", denied))
    stack.enter_context(patch.object(socket.socket, "bind", denied))
    stack.enter_context(patch.object(builtins, "__import__", no_sdk))
    return stack
