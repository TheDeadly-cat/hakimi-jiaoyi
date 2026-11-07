"""Explicit v3 test assembly around the original coordinator, journal and worker.

Values, permits and cash are fictional. The ordinary layer uses named JSON
fakes; the separate actual layer requires verified generated protobuf bindings.
The request registry is test bootstrap data, never a second business ledger.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import select
import socket
from threading import Event, Thread
import time
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from exchange_terminal.services import terminal_broker_wire_profile as wire
from exchange_terminal.services.terminal_broker_loopback_socket import pinned_loopback_factory
from tests.broker_action_coordinator_fixture import Fixture, CASH_EVIDENCE, NOW, pf
from tests.broker_quote_worker_fixture import ACTUAL, SYNTHETIC, ObservedSocket, assign_message
from tests import test_futu_us_equity_simulate_wire_v2 as fake
from tests.test_terminal_broker_execution_plan import config
from tests.test_terminal_broker_wire_v3 import v3_codec
from tests.broker_quote_worker_fixture import response_values as old_quote_values


INITIAL_ACTIONS = ("quote_connect", "quote_init", "trade_connect", "trade_init")
QUOTE_ACTIONS = ("quote_runtime", "quote_security", "quote_snapshot", "quote_market_state")
ALL_ACTIONS = INITIAL_ACTIONS + QUOTE_ACTIONS + ("trade_submit",)
IDS = {action: "submit-market-fixture-" + action for action in ALL_ACTIONS}
SERIALS = {action: index + 1 for index, action in enumerate(ALL_ACTIONS) if not action.endswith("_connect")}


def response_values(action, *, market_state=5):
    if action.endswith("_init"):
        return {"retType": 0, "retMsg": "private-fictional-handshake-text", "s2c": {
            "serverVer": 100, "loginUserID": 22, "connID": 11 if action == "quote_init" else 33,
            "connAESKey": "private-fictional-key", "aesCBCiv": "private-fictional-iv", "keepAliveInterval": 30}}
    if action == "quote_market_state":
        return {"retType": 0, "s2c": {"marketInfoList": [{"security": {"market": 11, "code": "TSLA"},
            "name": "EXPLICIT FICTIONAL TSLA", "marketState": market_state}]}}
    if action == "trade_submit":
        return {"retType": 0, "s2c": {"header": {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2},
            "orderID": 44, "orderIDEx": "fictional-order-44"}}
    return old_quote_values(action)


def response_frame(action, *, bindings=None, market_state=5):
    protocol = wire.WIRE_ACTIONS_V3[action][1]
    values = response_values(action, market_state=market_state)
    if bindings is None:
        body = fake.encode(values)
    else:
        message = bindings.response_classes[protocol]()
        assign_message(message, values)
        assert message.IsInitialized(), list(message.FindInitializationErrors())
        body = message.SerializeToString(deterministic=True)
    return codec.pack_plaintext_frame(protocol, SERIALS[action], body)


class SubmitMarketFixture(Fixture):
    def __init__(self, root, *, endpoint=None, layer=SYNTHETIC, runtime_identity=None,
                 bindings=None, initialize=True, evidence="submit-market-evidence", recovery=False):
        assert layer in {SYNTHETIC, ACTUAL}
        assert (layer == ACTUAL) == (runtime_identity is not None and bindings is not None)
        if layer == SYNTHETIC:
            assert runtime_identity is None and bindings is None
        self.layer, self.bindings, self.recovery = layer, bindings, recovery
        self.queries_bound, self.submit_bound = False, False
        self.preparation_error, self.scenario_notes = None, []
        original_fixture = pf.fixture
        terms = config(); terms["limit_price"] = "20.00"
        def args():
            value = original_fixture(terms=terms, runtime_value=runtime_identity)
            value["wire_bounds"]["actions"] = dict(wire.PROTOCOL_LIMITS_V3)
            return value
        def factory(profile):
            if layer == SYNTHETIC:
                return v3_codec(profile)
            session = codec.bind_codec_session(profile, client_version=100, client_id="fictional-client")
            return codec.SimulateCodec.from_verified_bindings(profile, session, bindings)
        with patch.object(pf, "fixture", side_effect=args):
            super().__init__(root, endpoint=endpoint, initialize=initialize, evidence=evidence,
                profile_factory=wire.prepare_wire_profile_v3, codec_factory=factory, initialize_operations=False)
        self.responses = {action: response_frame(action, bindings=bindings) for action in SERIALS}
        if endpoint is not None:
            self.subject.factory = pinned_loopback_factory(endpoint)
        self.committed, self.io_order = {}, []
        begin = self.subject.journal.begin_action
        def observe_commit(*args, **kwargs):
            result = begin(*args, **kwargs)
            if not result["replayed"]:
                identity = result["receipt"]["request_id"]
                original = self.subject.journal.read(identity)["receipt"]
                assert original == result["receipt"]
                self.committed[identity] = original
            return result
        self.subject.journal.begin_action = observe_commit
        original_factory = self.subject.factory
        def observed_factory(channel):
            self.before_io("factory")
            connection = original_factory(channel)
            if endpoint is not None:
                original_open = connection._open_socket
                connection._open_socket = lambda: ObservedSocket(original_open(), self.before_io)
            return connection
        self.subject.factory = observed_factory
        self.registry = self.root / "submit-market-request-registry.json"
        if recovery:
            self._restore_registry()
        else:
            for action in INITIAL_ACTIONS:
                self.register(action, b"" if action.endswith("_connect") else self.encode(action))

    def encode(self, action):
        assert not self.recovery, "Historical recovery must not encode new frames"
        return self.codec.encode_request(self.profile, action, SERIALS[action])

    def register(self, action, frame, *, issued_at=None, expires_at=None,
                 observation=None, session=None, cash_evidence_id=None):
        permit = coordinator.synthetic_test_permit_v3(shared_root=self.bound, profile=self.profile,
            operation_id=IDS[action], action=action, frame=frame, local_revision=0, account_revision=0,
            issued_at=issued_at or NOW.isoformat(), expires_at=expires_at or self.profile.as_dict()["wire_bounds"]["valid_until"],
            submit_observation=observation, session_binding=session)
        operation = coordinator.BoundOperation(IDS[action], action, frame, permit,
            cash_evidence_id=cash_evidence_id, submit_observation=observation)
        self.operations.append(operation); self.subject.register(operation)
        return operation

    def _save_registry(self):
        value = dict(profile_id=self.profile.as_dict()["id"], protocol_layer=self.layer,
            scope="TEST_ONLY_PREBOUND_BYTES_AND_PERMIT_TIMES_NOT_BUSINESS_LEDGER", operations=[
                dict(action=op.action, frame_hex=op.frame.hex(), permit=op.permit.as_dict(),
                     cash_evidence_id=op.cash_evidence_id) for op in self.operations])
        self.registry.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def _restore_registry(self):
        saved = json.loads(self.registry.read_text(encoding="utf-8"))
        assert saved["profile_id"] == self.profile.as_dict()["id"] and saved["protocol_layer"] == self.layer
        assert [row["action"] for row in saved["operations"]] == list(ALL_ACTIONS)
        for row in saved["operations"]:
            action, permit = row["action"], row["permit"]
            observation = session = None
            if action == "trade_submit":
                observation = self.subject.journal.read_submit_observation(IDS[action])
                assert observation is not None
                old = observation.as_dict()["session_binding"]
                session = codec.bind_codec_session(self.profile, **{key: old[key] for key in (
                    "client_version", "client_id", "quote_connection_id", "quote_user_id",
                    "trade_connection_id", "trade_user_id", "broker_order_id")})
                assert session.as_dict() == old
            op = self.register(action, bytes.fromhex(row["frame_hex"]), issued_at=permit["issued_at"],
                expires_at=permit["expires_at"], observation=observation, session=session,
                cash_evidence_id=row["cash_evidence_id"])
            assert op.permit.as_dict() == permit
        self.queries_bound = self.submit_bound = True

    def initialize(self):
        assert not self.recovery
        for action in INITIAL_ACTIONS:
            result = self.execute(action)
            assert result["status"] == ("CONNECTED" if action.endswith("_connect") else "UNKNOWN"), result
        assert self.subject._initialized == {"quote", "trade"}

    def bind_queries(self, *, save=True):
        assert not self.recovery and not self.queries_bound
        for action in QUOTE_ACTIONS:
            if not any(op.action == action for op in self.operations):
                self.bind_next_query(action, save=save)

    def bind_next_query(self, action, *, save=True):
        """Fixed trusted test stage; no INPUT chooses or supplies request bytes."""
        assert not self.recovery and not self.queries_bound
        existing = [op.action for op in self.operations if op.action in QUOTE_ACTIONS]
        assert existing == list(QUOTE_ACTIONS[:len(existing)])
        assert action == QUOTE_ACTIONS[len(existing)]
        self.codec.accepted_session_binding("quote")
        self.codec.accepted_session_binding("trade")
        started = time.monotonic()
        self.register(action, self.encode(action))
        self.scenario_notes.append(dict(kind="FIXED_NEXT_QUERY_BOUND", action=action,
            preparation_seconds=time.monotonic() - started))
        self.queries_bound = len(existing) + 1 == len(QUOTE_ACTIONS)
        if save:
            self._save_registry()

    def query_all(self):
        if not self.queries_bound:
            self.bind_queries()
        return [self.execute(action) for action in QUOTE_ACTIONS]

    def seed(self):
        assert not self.recovery
        state = self.subject.journal.read()
        required = {"quote_init", "trade_init", *QUOTE_ACTIONS}
        assert {row["action"] for row in state["response_facts"].values()} == required
        assert all(row["status"] in {"READ_FACTS_MATCHED", "HANDSHAKE_IDENTITY_MATCHED"}
                   for row in state["response_facts"].values())
        return super().seed()  # Explicit fictional cash, independent of quote facts.

    def prepare_submit(self, *, permit_expires_at=None):
        assert not self.recovery and not self.submit_bound
        session = self.codec.accepted_session_binding("trade")
        self.codec.accepted_session_binding("quote")
        observation = self.subject.journal.prepare_submit_observation(self.profile, session)
        frame = self.encode("trade_submit")
        operation = self.register("trade_submit", frame, issued_at=self.clock.utcnow().isoformat(),
            expires_at=permit_expires_at or observation.as_dict()["expires_at"], observation=observation,
            session=session, cash_evidence_id=CASH_EVIDENCE)
        self.submit_bound = True
        self._save_registry()
        return operation

    def execute(self, action):
        return self.subject.execute(IDS[action])

    def before_io(self, kind):
        # The snapshot was read after durable begin_action and before the write
        # barrier. Do not add journal reads inside local/account stop barriers.
        operation = self.subject._active
        receipt = self.committed[operation.operation_id]
        assert receipt["kind"] == "ACTION"
        assert receipt["payload"]["frame_bytes"] == len(operation.frame)
        assert receipt["payload"]["frame_sha256"] == (sha256(operation.frame).hexdigest() if operation.frame else None)
        self.io_order.append(dict(kind=kind, operation_id=operation.operation_id, receipt_id=receipt["id"]))


class BindStagesBeforeInput:
    """Test-only fixed stages; original serve still accepts only prebound IDs."""
    def __init__(self, fixture, stream, *, expire_bundle=False, prepare=True):
        self.fixture, self.stream = fixture, stream
        self.expire_bundle, self.prepare, self.attempted = expire_bundle, prepare, False

    def readline(self, maximum):
        f = self.fixture
        if not f.recovery:
            if not f.queries_bound and f.subject._initialized == {"quote", "trade"}:
                state = f.subject.journal.read()
                existing = [op.action for op in f.operations if op.action in QUOTE_ACTIONS]
                if not existing or IDS[existing[-1]] in state["actions"]:
                    # Each genuine binding/hash check runs once, before reading
                    # that fixed next operation ID. Four expensive checks must
                    # not consume one worker-message wait as a hidden batch.
                    f.bind_next_query(QUOTE_ACTIONS[len(existing)])
            if not self.attempted and f.queries_bound and self.prepare:
                state = f.subject.journal.read()
                if IDS["quote_market_state"] in state["actions"]:
                    self.attempted = True
                    try:
                        f.seed()
                        operation = f.prepare_submit(permit_expires_at=(f.profile.as_dict()["wire_bounds"]["valid_until"]
                            if self.expire_bundle else None))
                        if self.expire_bundle:
                            expiry = datetime.fromisoformat(operation.submit_observation.as_dict()["expires_at"])
                            f.clock.offset += (expiry - f.clock.utcnow()).total_seconds() + 1
                            assert f.clock.utcnow() < datetime.fromisoformat(operation.permit.as_dict()["expires_at"])
                            f.scenario_notes.append(dict(kind="EXPLICIT_CLOCK_AFTER_BUNDLE_EXPIRY_PERMIT_STILL_FUTURE",
                                bundle_expires_at=expiry.isoformat(), permit_expires_at=operation.permit.as_dict()["expires_at"],
                                injected_now=f.clock.utcnow().isoformat()))
                    except Exception as error:
                        f.preparation_error = type(error).__name__ + ":" + str(error)
        return self.stream.readline(maximum)


class OwnedSubmitPeer:
    """Finite two-channel peer; only this owned listener's dynamic port is used."""
    def __init__(self, responses, *, lifetime=45):
        assert type(lifetime) is int and 0 < lifetime <= 100
        self.responses = dict(responses)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.listener.bind(("127.0.0.1", 0)); self.listener.listen(2); self.listener.setblocking(False)
        host, port = self.listener.getsockname()
        assert host == "127.0.0.1" and port != 11111
        self.endpoint = dict(host=host, port=port)
        self.stop = Event(); self.clients, self.accepted_addresses = [], []
        self.frames, self.sent_frames, self.errors, self.frame_channels = [], [], [], []
        self.expected = set(); self.deadline = time.monotonic() + lifetime
        self.thread = Thread(target=self.run, daemon=True, name="owned-submit-market-peer")
        self.thread.start()

    def run(self):
        buffers, channels = {}, {}
        try:
            while not self.stop.is_set() and time.monotonic() < self.deadline:
                readable, _, _ = select.select([self.listener, *buffers], [], [], .05)
                for connection in readable:
                    if connection is self.listener:
                        client, address = self.listener.accept()
                        assert address[0] == "127.0.0.1" and len(self.clients) < 2
                        client.settimeout(.5)
                        channels[client] = "quote" if not self.clients else "trade"
                        self.clients.append(client); self.accepted_addresses.append(address); buffers[client] = bytearray()
                        continue
                    data = connection.recv(65536)
                    if not data:
                        del buffers[connection]; connection.close(); continue
                    pending = buffers[connection]; pending.extend(data)
                    assert len(pending) <= 65536
                    if len(pending) < 44:
                        continue
                    header = codec.HEADER.unpack(bytes(pending[:44]))
                    protocol, serial, length = header[2], header[5], header[6]
                    assert 0 < length <= 65536 - 44
                    if len(pending) < 44 + length:
                        continue
                    assert len(pending) == 44 + length, "Only one request at a time"
                    frame = bytes(pending); pending.clear()
                    assert frame in self.expected, "Unbound frame reached owned peer"
                    codec.inspect_frame(frame, protocol=protocol, serial=serial)
                    channel = channels[connection]
                    action = channel + "_init" if protocol == 1001 else next(
                        key for key, value in wire.WIRE_ACTIONS_V3.items() if value == (channel, protocol))
                    assert action in self.responses and len(self.frames) < 7
                    self.frames.append(frame); self.frame_channels.append(channel)
                    response = self.responses[action]
                    for offset in range(0, len(response), 17):
                        connection.sendall(response[offset:offset + 17])
                    self.sent_frames.append(response)
        except Exception as error:
            if not self.stop.is_set():
                self.errors.append(repr(error))

    def close(self):
        self.stop.set(); self.listener.close()
        for connection in self.clients:
            connection.close()
        self.thread.join(2)
        assert not self.thread.is_alive()
