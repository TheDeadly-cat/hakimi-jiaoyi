"""Explicit quote-only test assembly; actual protobuf is a separate dependency.

The ordinary test layer uses named JSON protocol fakes. The private probe must
supply VerifiedProtobufBindings plus the independently checked package identity;
it cannot fall back to fake classes. No order, claim or cash snapshot is made.
"""
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import socket
from threading import Event, Thread
import time
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as wire_codec
from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from exchange_terminal.services.terminal_broker_loopback_socket import pinned_loopback_factory
from exchange_terminal.services.terminal_broker_wire_profile import WIRE_ACTIONS
from tests.broker_action_coordinator_fixture import Fixture, NOW, pf
from tests import test_futu_us_equity_simulate_wire_v2 as fake_frames


SYNTHETIC = "SYNTHETIC_JSON_PROTOCOL_ONLY"
ACTUAL = "ACTUAL_PINNED_PROTOBUF_SYNTHETIC_VALUES"
QUOTE_ACTIONS = ("quote_runtime", "quote_security", "quote_snapshot")
SERIALS = {"quote_init": 1, "quote_runtime": 2, "quote_security": 3, "quote_snapshot": 4}
IDS = {name: "quote-fixture-" + name for name in ("quote_connect", "quote_init", *QUOTE_ACTIONS)}


def response_values(action, *, wrong_security=False):
    security = {"market": 11, "code": "WRONG" if wrong_security else "TSLA"}
    if action == "quote_init":
        value = dict(serverVer=100, loginUserID=22, connID=11,
                     connAESKey="explicit-synthetic-secret", keepAliveInterval=30)
    elif action == "quote_runtime":
        value = dict(marketHK=6, marketUS=3, marketSH=6, marketSZ=6, marketHKFuture=6,
                     qotLogined=True, trdLogined=False, serverVer=100, serverBuildNo=1,
                     time=int(NOW.timestamp()), connID=11, programStatus={"type": 10})
    elif action == "quote_security":
        value = {"staticInfoList": [{"basic": dict(security=security, id=99, lotSize=1,
            secType=3, name="EXPLICIT SYNTHETIC TSLA", listTime="2010-06-29", delisting=False, exchType=2)}]}
    elif action == "quote_snapshot":
        value = {"snapshotList": [{"basic": dict(security=security, type=3, isSuspend=False,
            listTime="2010-06-29", lotSize=1, priceSpread=.01, updateTime="2026-10-30 04:00:00",
            highPrice=21.0, openPrice=20.0, lowPrice=19.0, lastClosePrice=20.0,
            curPrice=20.0, volume=10, turnover=200.0, turnoverRate=1.0,
            updateTimestamp=float(NOW.timestamp()), askPrice=20.01, bidPrice=20.0, secStatus=1)}]}
    else:
        raise AssertionError("quote-only response required")
    return {"retType": 0, "s2c": value}


def assign_message(message, values):
    """Build synthetic values in actual generated message fields, without SDK APIs."""
    for name, value in values.items():
        descriptor = message.DESCRIPTOR.fields_by_name[name]
        if descriptor.is_repeated:
            field = getattr(message, name)
            for element in value:
                if descriptor.message_type is None:
                    field.append(element)
                else:
                    assign_message(field.add(), element)
        elif descriptor.message_type is not None:
            nested = getattr(message, name)
            nested.SetInParent()
            assign_message(nested, value)
        else:
            setattr(message, name, value)


def response_frame(action, *, bindings=None, wrong_security=False):
    values = response_values(action, wrong_security=wrong_security)
    protocol, serial = WIRE_ACTIONS[action][1], SERIALS[action]
    if bindings is None:
        return fake_frames.response_frame(action, serial, payload=values)
    message = bindings.response_classes[protocol]()
    assign_message(message, values)
    assert message.IsInitialized()
    return wire_codec.pack_plaintext_frame(protocol, serial, message.SerializeToString(deterministic=True))


class QuoteFixture(Fixture):
    def __init__(self, root, *, endpoint, layer, runtime_identity=None, bindings=None,
                 initialize=True, evidence="quote-evidence", recovery=False):
        assert layer in {SYNTHETIC, ACTUAL}
        assert (layer == ACTUAL) == (runtime_identity is not None and bindings is not None)
        if layer == SYNTHETIC:
            assert runtime_identity is None and bindings is None
        original_profile_fixture = pf.fixture
        if layer == ACTUAL:
            # Reuse the candidate/service/control setup with an actual checked
            # package identity. No tiny synthetic SDK inventory is promoted.
            with patch.object(pf, "fixture", side_effect=lambda: original_profile_fixture(runtime_value=runtime_identity)):
                super().__init__(root, endpoint=endpoint, initialize=initialize, evidence=evidence)
        else:
            super().__init__(root, endpoint=endpoint, initialize=initialize, evidence=evidence)
        self.subject.close()  # No transport/evidence/action exists in the initial setup.
        self.layer, self.bindings = layer, bindings
        if layer == ACTUAL:
            session = wire_codec.bind_codec_session(self.profile, client_version=100, client_id="fictional-client")
            self.codec = wire_codec.SimulateCodec.from_verified_bindings(self.profile, session, bindings)
            assert all(cls is bindings.request_classes[protocol] for protocol, cls in self.codec._requests.items())
        else:
            self.codec = fake_frames.make_codec(self.profile, quote_connection_id=None, quote_user_id=None,
                trade_connection_id=None, trade_user_id=None, broker_order_id=None)
        self.operations = []
        self.subject = coordinator.ActionCoordinator(service=self.service, profile=self.profile, codec=self.codec,
            evidence_directory=self.root / evidence, connection_factory=pinned_loopback_factory(endpoint), clock=self.clock)
        self.committed, self.io_order = {}, []
        begin = self.subject.journal.begin_action
        def observe_commit(*args, **kwargs):
            result = begin(*args, **kwargs)
            if not result["replayed"]:
                identity = result["receipt"]["request_id"]
                observed = self.subject.journal.read(identity)["receipt"]
                assert observed == result["receipt"]
                self.committed[identity] = observed
            return result
        self.subject.journal.begin_action = observe_commit
        original_factory = self.subject.factory
        def factory(channel):
            self.before_io("factory")
            connection = original_factory(channel)
            original_open = connection._open_socket
            def open_socket():
                return ObservedSocket(original_open(), self.before_io)
            connection._open_socket = open_socket
            return connection
        self.subject.factory = factory
        self.registry = self.root / "quote-request-registry.json"
        self.queries_bound = False
        self.register("quote_connect", b"")
        self.register("quote_init", self.encode("quote_init"))
        if recovery:
            saved = json.loads(self.registry.read_text(encoding="utf-8"))
            assert set(saved) == {"profile_id", "protocol_layer", "frames"}
            assert saved["profile_id"] == self.profile.as_dict()["id"] and saved["protocol_layer"] == layer
            assert set(saved["frames"]) == set(QUOTE_ACTIONS)
            for action in QUOTE_ACTIONS:
                # These bytes are checked again against each original ACTION by
                # ActionCoordinator.read; no session is invented on recovery.
                self.register(action, bytes.fromhex(saved["frames"][action]))
            self.queries_bound = True

    def encode(self, action):
        return (self.codec.encode_request(self.profile, action, SERIALS[action]) if self.layer == ACTUAL
                else fake_frames.request_frame(action, SERIALS[action]))

    def register(self, action, frame):
        permit = coordinator.synthetic_test_permit(shared_root=self.bound, profile=self.profile,
            operation_id=IDS[action], action=action, frame=frame, local_revision=0, account_revision=0,
            issued_at=NOW.isoformat(), expires_at=(NOW + timedelta(minutes=10)).isoformat())
        operation = coordinator.BoundOperation(IDS[action], action, frame, permit)
        self.operations.append(operation)
        self.subject.register(operation)

    def bind_queries(self, *, save=True):
        assert not self.queries_bound
        assert self.codec.session_binding().as_dict()["quote_connection_id"] == 11
        assert self.codec.session_binding().as_dict()["quote_user_id"] == 22
        for action in QUOTE_ACTIONS:
            self.register(action, self.encode(action))
        self.queries_bound = True
        if save:
            body = dict(profile_id=self.profile.as_dict()["id"], protocol_layer=self.layer,
                frames={operation.action: operation.frame.hex() for operation in self.operations
                        if operation.action in QUOTE_ACTIONS})
            with self.registry.open("x", encoding="utf-8") as stream:
                json.dump(body, stream, sort_keys=True)

    def execute(self, action):
        return self.subject.execute(IDS[action])

    def seed(self):
        raise AssertionError("Quote-only fixture must never create a cash snapshot")

    def before_io(self, kind):
        # No journal lock is acquired in the actual-write barrier. These are
        # immutable observations read back after begin_action returned.
        operation = self.subject._active
        receipt = self.committed[operation.operation_id]
        assert receipt["kind"] == "ACTION"
        assert receipt["payload"]["frame_bytes"] == len(operation.frame)
        assert receipt["payload"]["frame_sha256"] == (sha256(operation.frame).hexdigest() if operation.frame else None)
        self.io_order.append(dict(kind=kind, operation_id=operation.operation_id, receipt_id=receipt["id"]))


class ObservedSocket:
    def __init__(self, fd, before_io):
        self.fd, self.before_io = fd, before_io

    def __getattr__(self, name):
        return getattr(self.fd, name)

    def connect_ex(self, endpoint):
        self.before_io("connect")
        return self.fd.connect_ex(endpoint)

    def send(self, data):
        self.before_io("send")
        return self.fd.send(data)


class BindQueriesBeforeInput:
    """Trusted test bootstrap binds the fixed next stage before reading stdin.

    No user payload builds bytes. The unchanged worker still receives only a
    prebound operation ID and calls the unchanged coordinator directly.
    """
    def __init__(self, fixture, stream):
        self.fixture, self.stream = fixture, stream

    def readline(self, maximum):
        if not self.fixture.queries_bound and "quote" in self.fixture.subject._initialized:
            self.fixture.bind_queries()
        return self.stream.readline(maximum)


class OwnedQuotePeer:
    """One finite quote-only listener, owning its OS handle until close."""
    def __init__(self, responses, *, lifetime=45):
        assert type(lifetime) is int and 0 < lifetime <= 100
        self.responses = dict(responses)
        assert set(self.responses) == {1001, 1002, 3202, 3203}
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(.05)
        host, port = self.listener.getsockname()
        assert host == "127.0.0.1" and port != 11111
        self.endpoint = dict(host=host, port=port)
        self.stop, self.accepted = Event(), Event()
        self.frames, self.sent_frames, self.errors, self.clients = [], [], [], []
        self.accepted_addresses = []
        self.expected = set()
        self.deadline = time.monotonic() + lifetime
        self.thread = Thread(target=self.run, daemon=True, name="owned-quote-peer")
        self.thread.start()

    def read(self, connection, amount):
        value = bytearray()
        while len(value) < amount and not self.stop.is_set() and time.monotonic() < self.deadline:
            try:
                part = connection.recv(amount - len(value))
            except TimeoutError:
                continue
            if not part:
                return None
            value.extend(part)
        return bytes(value) if len(value) == amount else None

    def run(self):
        try:
            while not self.stop.is_set() and time.monotonic() < self.deadline:
                try:
                    connection, address = self.listener.accept()
                except TimeoutError:
                    continue
                assert address[0] == "127.0.0.1"
                self.clients.append(connection)
                self.accepted_addresses.append(address)
                assert len(self.clients) <= 1, "Original-ID recovery must not open a second connection"
                connection.settimeout(.05)
                self.accepted.set()
                try:
                    for _ in range(4):
                        header = self.read(connection, 44)
                        if header is None:
                            break
                        unpacked = wire_codec.HEADER.unpack(header)
                        protocol, serial, length = unpacked[2], unpacked[5], unpacked[6]
                        assert protocol in self.responses and 0 < length <= 65536 - 44
                        body = self.read(connection, length)
                        assert body is not None
                        frame = header + body
                        assert frame in self.expected, "Unbound request reached actual peer"
                        wire_codec.inspect_frame(frame, protocol=protocol, serial=serial)
                        self.frames.append(frame)
                        response = self.responses[protocol]
                        assert len(response) <= 65536
                        # Response fragmentation is server-only, finite and
                        # unrelated to client send retry semantics.
                        for offset in range(0, len(response), 17):
                            connection.sendall(response[offset:offset + 17])
                        self.sent_frames.append(response)
                finally:
                    connection.close()
        except Exception as error:
            if not self.stop.is_set():
                self.errors.append(repr(error))

    def close(self):
        self.stop.set()
        self.listener.close()
        for connection in self.clients:
            connection.close()
        self.thread.join(2)
        assert not self.thread.is_alive()


def retained_response(directory, action):
    """Read the actual retained response bytes, never reconstruct a response."""
    matches = []
    for path in sorted(Path(directory).glob("frame-*.bin")):
        header, _, raw = path.read_bytes().partition(b"\n")
        value = json.loads(header)
        if value["kind"] == "response_frame" and value.get("action") == action:
            matches.append(raw)
    assert len(matches) == 1
    return matches[0]
