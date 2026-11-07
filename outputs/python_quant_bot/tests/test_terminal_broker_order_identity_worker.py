"""Original worker and owned TCP: persisted ACK identity drives later actions.

CI uses explicit JSON fakes. The separately admitted private probe requires the
actual verified protobuf classes and reuses these checks, never a fake fallback.
"""
from hashlib import sha256
import json
from pathlib import Path
import time
import unittest

from exchange_terminal.services import terminal_broker_worker_supervisor as supervisor
from tests.broker_loopback_server_fixture import endpoint_guard
from tests.broker_quote_worker_fixture import retained_response
from tests.broker_order_identity_fixture import (
    ACTUAL, SYNTHETIC, ACTION, IDS, SERIALS, FLOW, FOLLOWUPS, ORDER_ID,
    OrderIdentityFixture, OwnedOrderIdentityPeer, response_frame,
)
from tests import broker_submit_market_fixture as previous
from tests import test_terminal_broker_worker_supervisor as worker_fixture
from tests.test_terminal_broker_submit_market_worker import SubmitMarketChainChecks, TERMINAL, CANONICAL


class OrderIdentityChainChecks:
    actual_context = None
    setUp = SubmitMarketChainChecks.setUp
    poll = SubmitMarketChainChecks.poll
    finish = SubmitMarketChainChecks.finish
    assert_public_facts = SubmitMarketChainChecks.assert_public_facts

    def prepare(self, *, foreign_order=False):
        responses = {name: response_frame(name, bindings=self.bindings,
            foreign_order=foreign_order and name == "observe_before_cancel") for name in SERIALS}
        self.peer = OwnedOrderIdentityPeer(responses, lifetime=150 if self.context else 45)
        self.addCleanup(self.peer.close)
        guard = endpoint_guard(self.peer.endpoint); self.addCleanup(guard.close)
        self.fixture = OrderIdentityFixture(self.root, endpoint=self.peer.endpoint, layer=self.layer,
            runtime_identity=self.runtime_identity, bindings=self.bindings, evidence="parent-read-only")
        self.addCleanup(self.fixture.close)
        self.assertIsNone(self.fixture.codec.session_binding().as_dict()["broker_order_id"])
        self.assertIsNone(self.fixture.codec.acknowledged_order_identity())
        # Parent checks only original pre-submit expected bytes. No order ID is
        # supplied or guessed to construct followups before the child's ACK.
        for channel in ("quote", "trade"):
            self.fixture.codec.accept_handshake(self.fixture.profile, channel, SERIALS[channel + "_init"],
                responses[channel + "_init"])
        self.peer.expected = {op.frame for op in self.fixture.operations if op.frame}
        self.peer.expected.update(self.fixture.encode(name) for name in (*previous.QUOTE_ACTIONS, "trade_submit"))
        self.recovering = set()

    def launch(self, name, *, recovery=False, quote_loss_after_ack=False):
        prelude = self.context["child_prelude"](self.peer.endpoint, self.root) if self.context else ""
        script = "\n".join([
            "import sys,argparse,json", "from pathlib import Path", "RUNTIME_IDENTITY=PROTOBUF_BINDINGS=ACTUAL_PROOF=None", prelude,
            "sys.path[:0]=" + repr([str(CANONICAL), str(TERMINAL)]),
            "from tests.broker_order_identity_fixture import OrderIdentityFixture,BindOrderStagesBeforeInput",
            "from tests.broker_loopback_server_fixture import endpoint_guard",
            "from exchange_terminal.services.terminal_broker_worker_entrypoint import serve",
            "p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()",
            "endpoint=" + repr(self.peer.endpoint), "guard=endpoint_guard(endpoint)",
            "f=OrderIdentityFixture(" + repr(str(self.root)) + ",endpoint=endpoint,layer=" + repr(self.layer) +
                ",runtime_identity=RUNTIME_IDENTITY,bindings=PROTOBUF_BINDINGS,initialize=False,evidence=" +
                repr(name + "-evidence") + ",recovery=" + repr(recovery) + ")",
            "initial_order_id=f.codec.session_binding().as_dict()['broker_order_id']",
            "assert initial_order_id is None and f.codec.acknowledged_order_identity() is None",
            "if callable(ACTUAL_PROOF): ACTUAL_PROOF.stage('order_identity_fixture_bound')",
            "try: result=serve(run_id=a.run_id,request_id=a.request_id,coordinator=f.subject,input_stream=BindOrderStagesBeforeInput(f,sys.stdin.buffer,quote_loss_after_ack=" + repr(quote_loss_after_ack) + "))",
            "finally:", " f.close();guard.close()",
            " adopted=f.codec.acknowledged_order_identity()",
            " proof=dict(protocol_layer=f.layer,initial_broker_order_id=initial_order_id,final_broker_order_id=f.codec.session_binding().as_dict()['broker_order_id'],adopted_identity_id=adopted.as_dict()['id'] if adopted else None,io_order=f.io_order,preparation_error=f.preparation_error,scenario_notes=f.scenario_notes,private_flags=dict(isolated=sys.flags.isolated,no_site=sys.flags.no_site,dont_write_bytecode=sys.flags.dont_write_bytecode),actual_loader=ACTUAL_PROOF() if callable(ACTUAL_PROOF) else ACTUAL_PROOF)",
            " with (f.root/" + repr(name + "-report.json") + ").open('x',encoding='utf-8') as stream: json.dump(proof,stream,sort_keys=True)",
            "raise SystemExit(result)",
        ])
        path = self.worker.fixtures.path / (name + ".py"); path.write_text(script, encoding="utf-8")
        interpreter = Path(self.context["interpreter"]) if self.context else self.worker.interpreter
        spec = supervisor.make_test_spec(interpreter=interpreter, interpreter_sha256=sha256(interpreter.read_bytes()).hexdigest(),
            entrypoint=path, entrypoint_sha256=sha256(path.read_bytes()).hexdigest(), fixture_parent=self.worker.fixtures)
        if self.context:
            self.context["authorize_child_command"](spec, "order-fixture-run", "order-fixture-request", self.worker.outputs.path / name)
        handle = supervisor.launch(spec, output_parent=self.worker.outputs, run_dir=self.worker.outputs.path / name,
            run_id="order-fixture-run", request_id="order-fixture-request",
            limits=worker_fixture.limits(wall_seconds=90 if self.context else 8, cleanup_seconds=1))
        self.worker.handles.append(handle); self.sequence[id(handle)] = 0
        if recovery: self.recovering.add(id(handle))
        self.assertEqual(self.poll(handle, initial=True)["kind"], "READY")
        return handle

    def allow_original_followup_frame(self, name):
        """Read prebound test bytes; journal identity, not registry data, is authority.

        The parent does not re-encode three requests after ACK: those repeated
        hash checks would consume the real keepalive while the child waits.
        """
        identity = self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile)
        self.assertIsNotNone(identity)
        self.fixture.codec.accept_acknowledged_order(self.fixture.profile, identity)
        started = time.monotonic(); deadline = started + (15 if self.context else 4)
        row = None
        while time.monotonic() < deadline:
            try:
                saved = json.loads(self.fixture.registry.read_text(encoding="utf-8"))
                row = next((value for value in saved["operations"] if value["operation_id"] == IDS[name]), None)
                if row is not None: break
            except (FileNotFoundError, json.JSONDecodeError):
                pass  # Only a bounded wait for this owned bootstrap's write.
            time.sleep(.01)
        self.assertIsNotNone(row, "Fixed next request was not prepared in the bounded test stage")
        self.assertEqual(saved["profile_id"], self.fixture.profile.as_dict()["id"])
        self.assertEqual(saved["protocol_layer"], self.layer)
        self.assertEqual(row["name"], name); self.assertEqual(row["action"], ACTION[name])
        self.assertEqual(row["broker_order_id"], identity.as_dict()["broker_order_id"])
        frame, permit = bytes.fromhex(row["frame_hex"]), row["permit"]
        self.assertEqual(permit["operation_id"], IDS[name]); self.assertEqual(permit["action"], ACTION[name])
        self.assertEqual(permit["profile_id"], saved["profile_id"])
        self.assertEqual(permit["frame_bytes"], len(frame)); self.assertEqual(permit["frame_sha256"], sha256(frame).hexdigest())
        info = self.fixture.codec.validate_request(self.fixture.profile, ACTION[name], frame)
        self.assertEqual(info.serial, SERIALS[name])
        self.peer.expected.add(frame)
        self.scenario_notes.append(dict(kind="PARENT_READ_ORIGINAL_FRAME_WITH_JOURNAL_IDENTITY_NO_REENCODING",
            name=name, identity_id=identity.as_dict()["id"], seconds=time.monotonic() - started))

    def send(self, handle, name=None):
        if name in FOLLOWUPS and id(handle) not in self.recovering:
            self.allow_original_followup_frame(name)
        self.sequence[id(handle)] += 1
        result = handle.reply(dict(schema_version="hakimi-broker-worker-message-v1", run_id="order-fixture-run",
            request_id="order-fixture-request", sequence=self.sequence[id(handle)], kind="INPUT" if name else "STOP",
            payload={"operation_id": IDS[name]} if name else {}))
        self.assertEqual(result["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")
        return self.poll(handle)

    def submit(self, handle):
        for name in FLOW[:9]:
            result = self.send(handle, name)
            self.assertEqual(result["kind"], "EVIDENCE")
            self.assertEqual(result["payload"]["status"], "CONNECTED" if name.endswith("_connect") else
                "ACKNOWLEDGED" if name == "trade_submit" else "UNKNOWN")
        identity = self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile)
        self.assertEqual(identity.as_dict()["broker_order_id"], ORDER_ID)
        return identity

    def facts_for(self, state, name):
        return [row for row in state["response_facts"].values() if row["request_id"] == IDS[name]]

    def assert_ack_is_not_economic_finality(self, state, name):
        facts = self.facts_for(state, name)[0]
        self.assertFalse(facts["facts"]["order_terminal_confirmed"])
        self.assertIsNone(facts["facts"]["fees_final"])

    def test_original_ack_identity_drives_observe_cancel_observe_and_read_only_recovery(self):
        self.prepare(); first = self.launch("first"); identity = self.submit(first)
        reserved = self.fixture.subject.journal.read()["financial"]["cash_reserved"]
        for name in FOLLOWUPS:
            result = self.send(first, name)
            self.assertEqual(result["kind"], "EVIDENCE")
            self.assertEqual(result["payload"]["status"], "ACKNOWLEDGED" if name == "cancel" else "UNKNOWN")
        self.finish(first)
        state = self.assert_public_facts(10)
        self.assertEqual(len(state["actions"]), 12); self.assertEqual(state["epoch"], 1)
        self.assertEqual(state["financial"]["cash_reserved"], reserved)
        self.assert_ack_is_not_economic_finality(state, "trade_submit")
        self.assert_ack_is_not_economic_finality(state, "cancel")
        for name, status in (("observe_before_cancel", 10), ("observe_after_cancel", 14)):
            fact = self.facts_for(state, name)[0]
            self.assertEqual(fact["status"], "READ_FACTS_MATCHED")
            self.assertEqual(fact["facts"]["broker_order_id"], ORDER_ID)
            self.assertEqual(fact["facts"]["broker_status_code"], status)
            self.assertEqual(fact["facts"]["filled_quantity"], "1.0")
            for key in ("filled_notional", "fees", "fees_final"): self.assertIsNone(fact["facts"][key])
            self.assertFalse(fact["derived"]["exact_notional"])
        self.assertEqual(self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile).as_dict(), identity.as_dict())
        self.assertEqual((len(self.peer.clients), len(self.peer.frames)), (2, 10)); self.assertEqual(self.peer.errors, [])
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertIsNone(proof["preparation_error"]); self.assertIsNone(proof["initial_broker_order_id"])
        self.assertEqual(proof["final_broker_order_id"], ORDER_ID)
        self.assertEqual(proof["adopted_identity_id"], identity.as_dict()["id"])
        before = self.fixture.subject.journal.path.read_bytes(); registry = self.fixture.registry.read_bytes()
        frames_before = list(self.peer.frames)
        second = self.launch("recovery", recovery=True)
        for name in FLOW:
            response = self.send(second, name)
            self.assertEqual(response["kind"], "EVIDENCE")
            if name in ("trade_submit", "cancel"): self.assertEqual(response["payload"]["status"], "ACKNOWLEDGED")
        self.finish(second)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.fixture.registry.read_bytes(), registry)
        self.assertEqual(self.peer.frames, frames_before); self.assertEqual(len(self.peer.clients), 2)
        self.assertFalse((self.root / "recovery-evidence").exists())
        proof = json.loads((self.root / "recovery-report.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["io_order"], []); self.assertIsNone(proof["final_broker_order_id"])
        self.assertIsNone(proof["adopted_identity_id"])

    def test_shared_stop_after_ack_preserves_original_identity_without_followup_send(self):
        self.prepare(); first = self.launch("first"); identity = self.submit(first)
        original = self.fixture.subject.journal.read(IDS["trade_submit"])["receipt"]
        self.fixture.stop_account()
        result = self.send(first, "observe_before_cancel")
        self.assertEqual(result["kind"], "EVIDENCE"); self.assertEqual(result["payload"]["status"], "UNKNOWN")
        self.finish(first)
        state = self.assert_public_facts(7)
        self.assertNotIn(IDS["observe_before_cancel"], state["actions"])
        self.assertEqual(self.fixture.subject.journal.read(IDS["trade_submit"])["receipt"], original)
        self.assertEqual(self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile).as_dict(), identity.as_dict())
        self.assertEqual((len(self.peer.clients), len(self.peer.frames)), (2, 7)); self.assertEqual(self.peer.errors, [])

    def test_foreign_order_response_is_retained_without_replacing_original_ack_identity(self):
        self.prepare(foreign_order=True); first = self.launch("first"); identity = self.submit(first)
        result = self.send(first, "observe_before_cancel")
        self.assertEqual(result["kind"], "EVIDENCE"); self.assertEqual(result["payload"]["status"], "UNKNOWN")
        self.finish(first)
        state = self.assert_public_facts(7)
        self.assertEqual(self.facts_for(state, "observe_before_cancel"), [])
        self.assertEqual(retained_response(self.root / "first-evidence", "trade_observe"),
            self.peer.responses[(2201, SERIALS["observe_before_cancel"])])
        self.assertEqual(self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile).as_dict(), identity.as_dict())
        self.assertEqual((len(self.peer.clients), len(self.peer.frames)), (2, 8)); self.assertEqual(self.peer.errors, [])

    def test_injected_confirmed_quote_loss_preserves_trade_query_and_cancel_without_reconnect(self):
        self.prepare(); first = self.launch("first", quote_loss_after_ack=True); identity = self.submit(first)
        reserved = self.fixture.subject.journal.read()["financial"]["cash_reserved"]
        for name in ("observe_before_cancel", "cancel"):
            result = self.send(first, name)
            self.assertEqual(result["kind"], "EVIDENCE")
            self.assertEqual(result["payload"]["status"], "ACKNOWLEDGED" if name == "cancel" else "UNKNOWN")
            self.assertIn("quote", self.peer.closed_channels)  # Actual owned peer observed EOF.
        self.finish(first)
        state = self.assert_public_facts(9)
        self.assertEqual(state["financial"]["cash_reserved"], reserved)
        self.assertEqual(self.facts_for(state, "observe_before_cancel")[0]["status"], "READ_FACTS_MATCHED")
        self.assertEqual(self.facts_for(state, "cancel")[0]["status"], "CANCEL_ACK_NOT_TERMINAL")
        self.assert_ack_is_not_economic_finality(state, "cancel")
        self.assertEqual(self.fixture.subject.journal.read_acknowledged_order(self.fixture.profile).as_dict(), identity.as_dict())
        self.assertEqual((len(self.peer.clients), len(self.peer.frames)), (2, 9)); self.assertEqual(self.peer.errors, [])
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertIsNone(proof["preparation_error"])
        injection = [row for row in proof["scenario_notes"] if row["kind"] ==
            "EXPLICIT_CONFIRMED_QUOTE_LOSS_TEST_INJECTION_NOT_FIN_DETECTOR"]
        self.assertEqual(len(injection), 1); self.assertEqual(injection[0]["closed_quote_fd"], -1)
        self.assertTrue(injection[0]["accepted_identity_unchanged"])
        quote_connects = [row for row in proof["io_order"] if row["kind"] == "connect" and row["operation_id"] == IDS["quote_connect"]]
        self.assertEqual(len(quote_connects), 1)


class SyntheticOrderIdentityWorkerTests(OrderIdentityChainChecks, unittest.TestCase):
    """CI JSON-fake protocol only; actual dependency gate is independent."""


if __name__ == "__main__":
    unittest.main()
