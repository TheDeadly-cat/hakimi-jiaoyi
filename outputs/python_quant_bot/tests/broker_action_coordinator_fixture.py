"""Synthetic connection/protobuf inputs around real service/control/journal IO."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import time

from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from exchange_terminal.services import terminal_broker_account_control as account_control
from exchange_terminal.services import terminal_broker_candidate_service as candidate
from exchange_terminal.services import terminal_broker_execution_plan as plan
from exchange_terminal.services import terminal_broker_wire_profile as wire
from exchange_terminal.services.terminal_research import TerminalResearchService
from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec_contract
from tests import test_terminal_broker_wire_profile as pf
from tests import test_futu_us_equity_simulate_wire_v2 as cf


NOW, SIM, CASH_EVIDENCE = pf.NOW, pf.SIM, "9" * 64


class Clock:
    def __init__(self, start=None):
        self.start, self.offset = time.monotonic() if start is None else start, 0

    def monotonic(self):
        return time.monotonic()

    def utcnow(self):
        return NOW + timedelta(seconds=time.monotonic() - self.start + self.offset)


def denied(*args, **kwargs):
    raise AssertionError("No market research, SDK or external operation")


class Connection:
    def __init__(self, fixture, channel):
        self.fixture, self.channel = fixture, channel
        self.pending, self.buffer = bytearray(), bytearray()
        self.parts = []
        self.send_error = self.recv_error = None
        self.closed = False

    def connect(self, endpoint, *, timeout):
        assert timeout == 0 and endpoint == {"host": "127.0.0.1", "port": 11111}
        self.fixture.event("connect", channel=self.channel)

    def wait_connected(self, *, timeout):
        assert timeout > 0

    def send(self, data, *, timeout):
        assert timeout == 0
        self.fixture.event("send", channel=self.channel, offered=len(data))
        if self.send_error:
            raise self.send_error
        count = min(len(data), self.parts.pop(0)) if self.parts else len(data)
        self.pending.extend(data[:count])
        if len(self.pending) >= 44:
            header = codec_contract.HEADER.unpack(bytes(self.pending[:44]))
            if len(self.pending) == 44 + header[6]:
                protocol, serial = header[2], header[5]
                action = self.channel + "_init" if protocol == 1001 else next(
                    k for k, v in wire.WIRE_ACTIONS.items() if v == (self.channel, protocol))
                response = self.fixture.responses.get(action)
                if callable(response):
                    response = response(action, serial)
                self.buffer.extend(response if type(response) is bytes else cf.response_frame(action, serial,
                    payload=response if response is not None else self.fixture.response(action)))
                self.pending.clear()
        return count

    def recv(self, maximum, *, timeout):
        if self.recv_error:
            raise self.recv_error
        result = bytes(self.buffer[:maximum]); del self.buffer[:maximum]
        return result

    def peek(self, maximum, *, timeout):
        assert timeout == 0
        return bytes(self.buffer[:maximum])

    def close(self, *, timeout):
        self.closed = True
        self.fixture.event("close", channel=self.channel)


class Fixture:
    def __init__(self, root, *, workspace="workspace-a", evidence="evidence-a", permits=True,
                 initialize=True, record_domain="SYNTHETIC_TEST", wire_bounds_changes=None, endpoint=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        origin = self.root / "synthetic-clock-origin.txt"
        try:
            with origin.open("x", encoding="ascii") as stream:
                stream.write(str(time.monotonic()))
        except FileExistsError:
            pass
        self.clock, self.events, self.connections, self.responses = Clock(float(origin.read_text())), [], {}, {}
        program = self.root / "program"
        program.mkdir(exist_ok=True)
        self.bound = account_control.bind_host_root(self.root / "shared", program_root=program, record_domain=record_domain)
        self.workspace = self.root / workspace
        self.args = pf.fixture()
        if endpoint is not None:
            bounds = deepcopy(self.args["base_plan"]["bounds"])
            bounds["endpoint"] = deepcopy(endpoint)
            self.args["base_plan"] = plan.prepare_acceptance_plan(**{key: self.args[key] for key in
                ("candidate_config", "candidate_intent", "research_resolution", "runtime_identity", "control", "now")},
                bounds=bounds)
            self.args["wire_bounds"]["endpoint"] = deepcopy(endpoint)
        if wire_bounds_changes:
            self.args["wire_bounds"].update(deepcopy(wire_bounds_changes))
        self.service = TerminalResearchService(SimpleNamespace(workspace=self.workspace), denied, lambda: [], denied,
            denied, broker_control_root=self.bound)
        self.service._broker_service = candidate.BrokerCandidateService(self.workspace / "broker-candidates-v2",
            research_resolver=lambda _: deepcopy(self.args["research_resolution"]), clock=self.clock.utcnow)
        if initialize:
            saved = self.service._broker().save(dict(mode=SIM, request_id="fixture-save-config",
                config=deepcopy(self.args["candidate_config"]["config"]),
                research_reference=deepcopy(self.args["candidate_config"]["research"]["reference"])))
            assert saved["config_id"] == self.args["candidate_config"]["id"]
            intent = self.service._broker().prepare_intent(dict(mode=SIM, request_id="fictional-intent-0001",
                config_id=saved["config_id"]))
            assert intent["intent"] == self.args["candidate_intent"]
        self.profile = wire.prepare_wire_profile(**self.args)
        self.codec = cf.make_codec(self.profile, quote_connection_id=None, quote_user_id=None,
            trade_connection_id=None, trade_user_id=None)
        self.operations = []
        for index, action in enumerate(("trade_connect", "trade_init", "trade_submit", "trade_observe", "trade_cancel", "trade_fees")):
            identity = "coordinator-" + action
            frame = b"" if action.endswith("_connect") else cf.request_frame(action, index)
            permit = coordinator.synthetic_test_permit(shared_root=self.bound, profile=self.profile,
                operation_id=identity, action=action, frame=frame, local_revision=0, account_revision=0,
                issued_at=NOW.isoformat(), expires_at=(NOW + timedelta(minutes=10)).isoformat()) if permits else None
            self.operations.append(coordinator.BoundOperation(identity, action, frame, permit,
                broker_order_id="fictional-order-44" if action in {"trade_observe", "trade_cancel", "trade_fees"} else None,
                cash_evidence_id=CASH_EVIDENCE if action == "trade_submit" else None))
        self.subject = coordinator.ActionCoordinator(service=self.service, profile=self.profile, codec=self.codec,
            evidence_directory=self.root / evidence, operations=self.operations,
            connection_factory=self.factory, clock=self.clock)

    def event(self, kind, **fields):
        value = dict(kind=kind, **fields)
        self.events.append(value)
        with (self.root / "wire-events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, sort_keys=True) + "\n")
            stream.flush()

    def factory(self, channel):
        self.event("factory", channel=channel)
        result = Connection(self, channel)
        self.connections[channel] = result
        return result

    @staticmethod
    def response(action):
        if action.endswith("_init"):
            return {"retType": 0, "s2c": {"keepAliveInterval": 30, "connID": 33, "loginUserID": 22}}
        header = {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2}
        if action in {"trade_submit", "trade_cancel"}:
            return {"retType": 0, "s2c": {"header": header, "orderIDEx": "fictional-order-44"}}
        if action == "trade_observe":
            return {"retType": 0, "s2c": {"header": header, "orderList": []}}
        return {"retType": 0, "s2c": {"header": header, "orderFeeList": []}}

    def seed(self):
        journal = self.subject.journal
        head, now = journal.read()["head"], self.clock.utcnow()
        return journal.snapshot(dict(evidence_id=CASH_EVIDENCE, query_started_at=now.isoformat(), observed_at=now.isoformat(),
            covered_head=head, valid_until=(now + timedelta(seconds=60)).isoformat(), cash_available="100", positions=[]),
            expected_head=head, request_id="fixture-cash-snapshot")

    def execute(self, action):
        return self.subject.execute("coordinator-" + action)

    def initialize(self):
        assert self.execute("trade_connect")["status"] == "CONNECTED"
        result = self.execute("trade_init")
        assert result["status"] == "UNKNOWN", result  # Handshake evidence is not an economic ACK.
        assert "trade" in self.subject._initialized, result

    def stop_local(self):
        return self.service.stop_broker_candidate(dict(mode=SIM, request_id="fixture-local-stop", reason="Synthetic test stop"))

    def stop_account(self):
        return self.service.stop_broker_account(dict(mode=SIM, config_id=self.args["candidate_config"]["id"],
            request_id="fixture-account-stop", reason="Synthetic shared stop"))

    def close(self):
        self.subject.close()
        self.service.close()


def network_and_sdk_blockers():
    """Install also inside owned child; no inherited parent patch is assumed."""
    import builtins
    import socket
    original_import = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        if name == "futu" or name.startswith("futu."):
            raise AssertionError("No SDK import")
        return original_import(name, *args, **kwargs)
    builtins.__import__ = no_sdk
    socket.socket.connect = socket.socket.connect_ex = socket.socket.bind = denied
    socket.create_connection = socket.getaddrinfo = denied
