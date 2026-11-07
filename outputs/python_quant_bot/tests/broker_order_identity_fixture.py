"""Explicit fictional ACK -> original-ID followups, with no production authority.

The W3 fixture is reused without edits. Registry data contains only prebound
bytes/permits; identity is restored from the original journal, never that file.
"""
from datetime import datetime
from hashlib import sha256
import json
import select
import socket
from threading import Event, Thread
import time

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests import broker_submit_market_fixture as previous
from tests.broker_quote_worker_fixture import assign_message
from tests import test_futu_us_equity_simulate_wire_v2 as fake


ACTUAL, SYNTHETIC = previous.ACTUAL, previous.SYNTHETIC
FOLLOWUPS = ("observe_before_cancel", "cancel", "observe_after_cancel")
ACTION = {**{name: name for name in previous.ALL_ACTIONS},
    "observe_before_cancel": "trade_observe", "cancel": "trade_cancel", "observe_after_cancel": "trade_observe"}
IDS = {**previous.IDS, **{name: "order-identity-fixture-" + name for name in FOLLOWUPS}}
SERIALS = {**previous.SERIALS, **{name: 10 + index for index, name in enumerate(FOLLOWUPS)}}
FLOW = ("quote_connect", "quote_init", *previous.QUOTE_ACTIONS,
        "trade_connect", "trade_init", "trade_submit", *FOLLOWUPS)
REGISTRY_ORDER = (*previous.ALL_ACTIONS, *FOLLOWUPS)
ORDER_ID = "fictional-order-44"


def response_values(name, *, foreign_order=False):
    if name not in FOLLOWUPS:
        return previous.response_values(name)
    header = {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2}
    if name == "cancel":
        # Numeric S2C.orderID is required by the pinned generated message.
        # It does not replace the original opaque orderIDEx authority.
        return {"retType": 0, "s2c": {"header": header, "orderID": 44, "orderIDEx": ORDER_ID}}
    row = dict(trdSide=1, orderType=1, orderStatus=10 if name == "observe_before_cancel" else 14,
        orderID=45 if foreign_order else 44, orderIDEx="foreign-order-45" if foreign_order else ORDER_ID,
        code="TSLA", name="EXPLICIT FICTIONAL TSLA", qty=3.0, price=20.0,
        createTime="2026-10-30 04:00:00", updateTime="2026-10-30 04:00:01",
        fillQty=1.0, fillAvgPrice=20.0, secMarket=2, currency=2, trdMarket=2,
        timeInForce=0, fillOutsideRTH=False, session=1)
    return {"retType": 0, "s2c": {"header": header, "orderList": [row]}}


def response_frame(name, *, bindings=None, foreign_order=False):
    protocol = wire.WIRE_ACTIONS_V3[ACTION[name]][1]
    values = response_values(name, foreign_order=foreign_order)
    if bindings is None:
        body = fake.encode(values)
    else:
        message = bindings.response_classes[protocol]()
        assign_message(message, values)
        assert message.IsInitialized(), list(message.FindInitializationErrors())
        body = message.SerializeToString(deterministic=True)
    return codec.pack_plaintext_frame(protocol, SERIALS[name], body)


class OrderIdentityFixture(previous.SubmitMarketFixture):
    def __init__(self, *args, **kwargs):
        self.followups_bound = []
        super().__init__(*args, **kwargs)
        self.registry = self.root / "order-identity-request-registry.json"
        self.responses["trade_observe"] = lambda action, serial: response_frame(
            "observe_before_cancel" if serial == SERIALS["observe_before_cancel"] else "observe_after_cancel",
            bindings=self.bindings)
        self.responses["trade_cancel"] = response_frame("cancel", bindings=self.bindings)

    def bind_next_query(self, action, *, save=True):
        """Quote requests need only their real accepted quote handshake.

        Worker tests deliberately initialize trade after these four reads, so
        followup writes fit the unchanged 30-second trade keepalive deadline.
        """
        assert not self.recovery and not self.queries_bound
        existing = [op.action for op in self.operations if op.action in previous.QUOTE_ACTIONS]
        assert existing == list(previous.QUOTE_ACTIONS[:len(existing)])
        assert action == previous.QUOTE_ACTIONS[len(existing)]
        self.codec.accepted_session_binding("quote")
        started = time.monotonic()
        self.register(action, self.encode(action))
        self.scenario_notes.append(dict(kind="FIXED_NEXT_QUOTE_BOUND_BEFORE_TRADE_INIT", action=action,
            preparation_seconds=time.monotonic() - started))
        self.queries_bound = len(existing) + 1 == len(previous.QUOTE_ACTIONS)
        if save:
            self._save_registry()

    def bind_followup(self, name):
        assert not self.recovery and name == FOLLOWUPS[len(self.followups_bound)]
        identity = self.subject.journal.read_acknowledged_order(self.profile)
        adopted = self.codec.acknowledged_order_identity()
        assert identity is not None and adopted is not None
        assert identity.as_dict() == adopted.as_dict(), "Original coordinator must adopt persisted ACK first"
        started = time.monotonic()
        frame = self.codec.encode_request(self.profile, ACTION[name], SERIALS[name])
        operation = self._register_followup(name, frame, broker_order_id=identity.as_dict()["broker_order_id"],
            issued_at=self.clock.utcnow().isoformat(), expires_at=self.profile.as_dict()["wire_bounds"]["valid_until"])
        self.scenario_notes.append(dict(kind="FIXED_FOLLOWUP_FROM_ORIGINAL_JOURNAL_IDENTITY", name=name,
            identity_id=identity.as_dict()["id"], preparation_seconds=time.monotonic() - started))
        self._save_registry()
        return operation

    def _register_followup(self, name, frame, *, broker_order_id, issued_at, expires_at):
        permit = coordinator.synthetic_test_permit_v3(shared_root=self.bound, profile=self.profile,
            operation_id=IDS[name], action=ACTION[name], frame=frame, local_revision=0, account_revision=0,
            issued_at=issued_at, expires_at=expires_at)
        operation = coordinator.BoundOperation(IDS[name], ACTION[name], frame, permit,
            broker_order_id=broker_order_id)
        self.subject.register(operation); self.operations.append(operation); self.followups_bound.append(name)
        return operation

    def _save_registry(self):
        registry = self.root / "order-identity-request-registry.json"
        names = {identity: name for name, identity in IDS.items()}
        value = dict(profile_id=self.profile.as_dict()["id"], protocol_layer=self.layer,
            scope="TEST_ONLY_PREBOUND_BYTES_AND_PERMIT_TIMES_NOT_IDENTITY_AUTHORITY", operations=[
                dict(name=names[op.operation_id], operation_id=op.operation_id, action=op.action,
                    frame_hex=op.frame.hex(), permit=op.permit.as_dict(), broker_order_id=op.broker_order_id,
                    cash_evidence_id=op.cash_evidence_id) for op in self.operations])
        registry.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def _restore_registry(self):
        self.registry = self.root / "order-identity-request-registry.json"
        saved = json.loads(self.registry.read_text(encoding="utf-8"))
        assert saved["profile_id"] == self.profile.as_dict()["id"] and saved["protocol_layer"] == self.layer
        rows = saved["operations"]
        assert [row["name"] for row in rows] == list(REGISTRY_ORDER[:len(rows)])
        identity = self.subject.journal.read_acknowledged_order(self.profile)
        assert identity is not None
        for row in rows:
            name, permit = row["name"], row["permit"]
            assert row["operation_id"] == IDS[name] and row["action"] == ACTION[name]
            frame = bytes.fromhex(row["frame_hex"])
            if name in FOLLOWUPS:
                assert row["broker_order_id"] == identity.as_dict()["broker_order_id"]
                operation = self._register_followup(name, frame, broker_order_id=row["broker_order_id"],
                    issued_at=permit["issued_at"], expires_at=permit["expires_at"])
            else:
                observation = session = None
                if name == "trade_submit":
                    observation = self.subject.journal.read_submit_observation(IDS[name])
                    assert observation is not None
                    original = observation.as_dict()["session_binding"]
                    session = codec.bind_codec_session(self.profile, **{key: original[key] for key in (
                        "client_version", "client_id", "quote_connection_id", "quote_user_id",
                        "trade_connection_id", "trade_user_id", "broker_order_id")})
                    assert session.as_dict() == original
                operation = self.register(name, frame, issued_at=permit["issued_at"], expires_at=permit["expires_at"],
                    observation=observation, session=session, cash_evidence_id=row["cash_evidence_id"])
            assert operation.permit.as_dict() == permit
        self.queries_bound = self.submit_bound = True
        assert self.codec.session_binding().as_dict()["broker_order_id"] is None
        assert self.codec.acknowledged_order_identity() is None

    def execute(self, name):
        return self.subject.execute(IDS[name])

    def inject_confirmed_quote_loss(self):
        """Explicit test state injection, NOT a production EOF detection path."""
        assert not self.recovery and self.codec.acknowledged_order_identity() is not None
        identity_before = self.codec.acknowledged_order_identity().as_dict()
        session_before = self.codec.session_binding().as_dict()
        transport = self.subject._transport
        connection = transport._connections["quote"]
        original_socket = connection._socket
        before_fd = original_socket.fileno()
        assert before_fd >= 0
        # Close this already owned connection directly to model a CONFIRMED
        # loss. Do not change/consume/reset the transport's cleanup allowance.
        connection.close(timeout=self.profile.as_dict()["wire_bounds"]["cleanup_timeout_seconds"])
        assert original_socket.fileno() == -1 and connection._state == "CLOSED"
        self.subject._connected.discard("quote")
        self.subject._initialized.discard("quote")
        transport._ready.discard("quote")
        assert self.subject._connected == self.subject._initialized == {"trade"}
        assert self.codec.session_binding().as_dict() == session_before
        assert self.codec.acknowledged_order_identity().as_dict() == identity_before
        self.scenario_notes.append(dict(kind="EXPLICIT_CONFIRMED_QUOTE_LOSS_TEST_INJECTION_NOT_FIN_DETECTOR",
            original_quote_fd=before_fd, closed_quote_fd=original_socket.fileno(),
            accepted_identity_unchanged=True, quote_live=False, trade_live=True))


class BindOrderStagesBeforeInput:
    """One fixed prepared stage at a time, original worker protocol unchanged."""
    def __init__(self, fixture, stream, *, quote_loss_after_ack=False):
        self.fixture, self.stream, self.submit_attempted = fixture, stream, False
        self.quote_loss_after_ack, self.loss_injected = quote_loss_after_ack, False

    def readline(self, maximum):
        f = self.fixture
        if not f.recovery:
            state = f.subject.journal.read()
            if not f.queries_bound and "quote" in f.subject._initialized:
                existing = [op.action for op in f.operations if op.action in previous.QUOTE_ACTIONS]
                if not existing or IDS[existing[-1]] in state["actions"]:
                    f.bind_next_query(previous.QUOTE_ACTIONS[len(existing)])
            if f.queries_bound and not self.submit_attempted and f.subject._initialized == {"quote", "trade"}:
                self.submit_attempted = True
                try:
                    f.seed(); f.prepare_submit()
                except Exception as error:
                    f.preparation_error = type(error).__name__ + ":" + str(error)
            if f.submit_bound and len(f.followups_bound) < len(FOLLOWUPS):
                previous_name = f.followups_bound[-1] if f.followups_bound else "trade_submit"
                if IDS[previous_name] in state["actions"]:
                    try:
                        if self.quote_loss_after_ack and not self.loss_injected:
                            f.inject_confirmed_quote_loss()
                            self.loss_injected = True
                        f.bind_followup(FOLLOWUPS[len(f.followups_bound)])
                    except Exception as error:
                        f.preparation_error = type(error).__name__ + ":" + str(error)
        return self.stream.readline(maximum)


class OwnedOrderIdentityPeer:
    """W4-only finite listener; never widens the prior peer's 100-second cap."""
    def __init__(self, responses, *, lifetime=45):
        assert type(lifetime) is int and 0 < lifetime <= 150
        self.responses = {(wire.WIRE_ACTIONS_V3[ACTION[name]][1], SERIALS[name]): frame
                          for name, frame in responses.items()}
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        self.listener.bind(("127.0.0.1", 0)); self.listener.listen(2); self.listener.setblocking(False)
        host, port = self.listener.getsockname()
        assert host == "127.0.0.1" and port != 11111
        self.endpoint = dict(host=host, port=port)
        self.stop = Event(); self.clients, self.accepted_addresses = [], []
        self.frames, self.sent_frames, self.frame_channels, self.errors, self.closed_channels = [], [], [], [], []
        self.expected = set(); self.deadline = time.monotonic() + lifetime
        self.thread = Thread(target=self.run, daemon=True, name="owned-order-identity-peer")
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
                        self.closed_channels.append(channels[connection])
                        del buffers[connection]; connection.close(); continue
                    pending = buffers[connection]; pending.extend(data)
                    assert len(pending) <= 65536
                    if len(pending) < 44:
                        continue
                    header = codec.HEADER.unpack(bytes(pending[:44])); protocol, serial, length = header[2], header[5], header[6]
                    assert 0 < length <= 65536 - 44
                    if len(pending) < 44 + length:
                        continue
                    assert len(pending) == 44 + length
                    frame = bytes(pending); pending.clear()
                    assert frame in self.expected, "Unbound frame reached owned peer"
                    codec.inspect_frame(frame, protocol=protocol, serial=serial)
                    assert (protocol, serial) in self.responses and len(self.frames) < 10
                    expected_channel = next(wire.WIRE_ACTIONS_V3[ACTION[name]][0] for name, number in SERIALS.items() if number == serial)
                    assert channels[connection] == expected_channel
                    self.frames.append(frame); self.frame_channels.append(channels[connection])
                    response = self.responses[(protocol, serial)]
                    for offset in range(0, len(response), 17):
                        connection.sendall(response[offset:offset + 17])
                    self.sent_frames.append(response)
        except Exception as error:
            if not self.stop.is_set():
                self.errors.append(repr(error))

    def close(self):
        self.stop.set(); self.listener.close()
        for connection in self.clients: connection.close()
        self.thread.join(2)
        assert not self.thread.is_alive()
