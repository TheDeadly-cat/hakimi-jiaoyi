"""Original quote worker/TCP/journal contracts on explicit JSON protocol fakes.

This always-available suite is NOT actual protobuf evidence. A separate reviewed
private-runtime runner reuses the same checks with mandatory verified bindings.
It never skips a missing package or substitutes fakes for actual protobuf.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import hakimi_research
from exchange_terminal.services import terminal_broker_response_facts as facts
from exchange_terminal.services import terminal_broker_worker_supervisor as supervisor
from tests.broker_loopback_server_fixture import endpoint_guard
from tests.broker_quote_worker_fixture import (
    ACTUAL, SYNTHETIC, IDS, QUOTE_ACTIONS, QuoteFixture, OwnedQuotePeer,
    response_frame, retained_response,
)
from tests import test_terminal_broker_worker_supervisor as worker_fixture


TERMINAL = Path(__file__).resolve().parents[1]
CANONICAL = Path(hakimi_research.__file__).resolve().parent.parent


class QuoteChainChecks:
    """Shared assertions, not a second worker, ledger, codec or authority path."""
    actual_context = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="new-quote-worker-chain-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.context = self.actual_context
        self.layer = ACTUAL if self.context is not None else SYNTHETIC
        self.bindings = self.context["bindings"] if self.context else None
        self.runtime_identity = self.context["runtime_identity"] if self.context else None
        self.sequence = {}
        self.scenario_notes = []
        self.worker = worker_fixture.WorkerSupervisorTests()
        self.worker.setUp()
        self.addCleanup(self.worker.doCleanups)

    def prepare(self, *, wrong_security=False):
        responses = {protocol: response_frame(action, bindings=self.bindings,
            wrong_security=wrong_security and action == "quote_snapshot")
            for action, protocol in (("quote_init", 1001), ("quote_runtime", 1002),
                                     ("quote_security", 3202), ("quote_snapshot", 3203))}
        self.peer = OwnedQuotePeer(responses, lifetime=100 if self.context else 45)
        self.addCleanup(self.peer.close)
        guard = endpoint_guard(self.peer.endpoint)
        self.addCleanup(guard.close)
        self.fixture = QuoteFixture(self.root, endpoint=self.peer.endpoint, layer=self.layer,
            runtime_identity=self.runtime_identity, bindings=self.bindings, evidence="parent-read-only")
        self.addCleanup(self.fixture.close)
        # Parent-side expected frames use a plainly synthetic server response.
        # The worker under test must obtain and accept it via actual TCP before
        # binding its three query requests through the trusted input bootstrap.
        self.fixture.codec.accept_handshake(self.fixture.profile, "quote", 1, responses[1001])
        self.fixture.bind_queries(save=False)
        self.peer.expected = {operation.frame for operation in self.fixture.operations if operation.frame}

    def launch(self, name, *, recovery=False):
        prelude = self.context["child_prelude"](self.peer.endpoint, self.root) if self.context else ""
        script = "\n".join([
            "import sys,argparse,json",
            "from pathlib import Path",
            "RUNTIME_IDENTITY=PROTOBUF_BINDINGS=ACTUAL_PROOF=None",
            prelude,
            "sys.path[:0]=" + repr([str(CANONICAL), str(TERMINAL)]),
            "from tests.broker_quote_worker_fixture import QuoteFixture,BindQueriesBeforeInput",
            "from tests.broker_loopback_server_fixture import endpoint_guard",
            "from exchange_terminal.services.terminal_broker_worker_entrypoint import serve",
            "p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()",
            "endpoint=" + repr(self.peer.endpoint),
            "guard=endpoint_guard(endpoint)",
            "f=QuoteFixture(" + repr(str(self.root)) + ",endpoint=endpoint,layer=" + repr(self.layer) +
                ",runtime_identity=RUNTIME_IDENTITY,bindings=PROTOBUF_BINDINGS,initialize=False,evidence=" +
                repr(name + "-evidence") + ",recovery=" + repr(recovery) + ")",
            "if callable(ACTUAL_PROOF): ACTUAL_PROOF.stage('quote_fixture_bound')",
            "try: result=serve(run_id=a.run_id,request_id=a.request_id,coordinator=f.subject,input_stream=BindQueriesBeforeInput(f,sys.stdin.buffer))",
            "finally:",
            " f.close();guard.close()",
            " proof=dict(protocol_layer=f.layer,io_order=f.io_order,private_flags=dict(isolated=sys.flags.isolated,no_site=sys.flags.no_site,dont_write_bytecode=sys.flags.dont_write_bytecode),actual_loader=ACTUAL_PROOF() if callable(ACTUAL_PROOF) else ACTUAL_PROOF)",
            " with (f.root/" + repr(name + "-report.json") + ").open('x',encoding='utf-8') as stream: json.dump(proof,stream,sort_keys=True)",
            "raise SystemExit(result)",
        ])
        path = self.worker.fixtures.path / (name + ".py")
        path.write_text(script, encoding="utf-8")
        interpreter = Path(self.context["interpreter"]) if self.context else self.worker.interpreter
        spec = supervisor.make_test_spec(interpreter=interpreter,
            interpreter_sha256=sha256(interpreter.read_bytes()).hexdigest(), entrypoint=path,
            entrypoint_sha256=sha256(path.read_bytes()).hexdigest(), fixture_parent=self.worker.fixtures)
        if self.context:
            self.context["authorize_child_command"](spec, "quote-fixture-run", "quote-fixture-request",
                                                     self.worker.outputs.path / name)
        handle = supervisor.launch(spec, output_parent=self.worker.outputs, run_dir=self.worker.outputs.path / name,
            run_id="quote-fixture-run", request_id="quote-fixture-request",
            limits=worker_fixture.limits(wall_seconds=60 if self.context else 8, cleanup_seconds=1))
        self.worker.handles.append(handle)
        self.sequence[id(handle)] = 0
        self.assertEqual(self.poll(handle, initial=True)["kind"], "READY")
        return handle

    def poll(self, handle, *, initial=False):
        deadline = time.monotonic() + (30 if initial and self.context else 15 if self.context else 4)
        while time.monotonic() < deadline:
            message = handle.poll_message(.1)
            if message is not None:
                return message
            if handle.finish(0) is not None:
                stderr = (handle.run_dir / "stderr.bin").read_text(encoding="utf-8", errors="replace")
                self.fail("quote worker ended before message: " + stderr)
        self.fail("bounded quote worker message wait expired")

    def send(self, handle, action=None):
        self.sequence[id(handle)] += 1
        result = handle.reply(dict(schema_version="hakimi-broker-worker-message-v1", run_id="quote-fixture-run",
            request_id="quote-fixture-request", sequence=self.sequence[id(handle)], kind="INPUT" if action else "STOP",
            payload={"operation_id": IDS[action]} if action else {}))
        self.assertEqual(result["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")
        return self.poll(handle)

    def finish(self, handle):
        self.assertEqual(self.send(handle)["kind"], "RESULT")
        result = handle.finish(10 if self.context else 3)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROTOCOL_RESULT_RECEIVED")
        self.assertEqual((result["spawn_count"], result["restart_count"]), (1, 0))
        self.assertTrue(result["cleanup_confirmed"])

    def initialize(self, handle):
        self.assertEqual(self.send(handle, "quote_connect")["payload"]["status"], "CONNECTED")
        self.assertEqual(self.send(handle, "quote_init")["payload"]["status"], "UNKNOWN")

    def assertions_no_economics(self):
        state = self.fixture.subject.journal.read()
        self.assertEqual(state["epoch"], 0)  # Every cash SNAPSHOT advances the journal epoch.
        self.assertEqual(state["claims"], {})
        self.assertEqual(state["financial"]["cash_reserved"], "0")
        self.assertIsNone(state["financial"]["cash_available_after_local_liabilities"])
        return state

    def assert_recovery(self, expected_facts):
        before = self.fixture.subject.journal.path.read_bytes()
        registry = self.fixture.registry.read_bytes()
        frames_before = list(self.peer.frames)
        second = self.launch("recovery", recovery=True)
        for action in QUOTE_ACTIONS:
            self.assertEqual(self.send(second, action)["payload"]["status"], "UNKNOWN")
        self.finish(second)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.fixture.registry.read_bytes(), registry)
        self.assertEqual(self.peer.frames, frames_before)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertFalse((self.root / "recovery-evidence").exists())
        recovery = json.loads((self.root / "recovery-report.json").read_text(encoding="utf-8"))
        self.assertEqual(recovery["io_order"], [])
        self.assertEqual(len(self.assertions_no_economics()["response_facts"]), expected_facts)

    def test_three_quote_actions_persist_facts_and_reopen_without_tcp(self):
        self.prepare()
        first = self.launch("first")
        self.initialize(first)
        for action in QUOTE_ACTIONS:
            self.assertEqual(self.send(first, action)["payload"]["status"], "UNKNOWN")
        self.finish(first)
        state = self.assertions_no_economics()
        self.assertEqual(len(state["actions"]), 5)
        self.assertEqual({row["action"] for row in state["response_facts"].values()}, set(QUOTE_ACTIONS))
        for row in state["response_facts"].values():
            self.assertEqual(row["status"], "READ_FACTS_MATCHED")
            self.assertTrue(row["test_only"])
            self.assertFalse(row["source_authenticated"])
            self.assertFalse(row["facts"]["freshness_verified"])
            self.assertFalse(row["facts"]["trading_eligibility_verified"])
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["protocol_layer"], self.layer)
        self.assertEqual([row["kind"] for row in proof["io_order"]], ["factory", "connect", "send", "send", "send", "send"])
        self.assertEqual(len(self.peer.frames), 4)
        self.assertEqual(self.peer.errors, [])
        self.assert_recovery(3)

    def test_wrong_security_retains_actual_response_without_typed_match(self):
        self.prepare(wrong_security=True)
        first = self.launch("first")
        self.initialize(first)
        for action in QUOTE_ACTIONS:
            self.assertEqual(self.send(first, action)["payload"]["status"], "UNKNOWN")
        self.finish(first)
        state = self.assertions_no_economics()
        self.assertEqual(len(state["response_facts"]), 2)
        self.assertEqual(retained_response(self.root / "first-evidence", "quote_snapshot"), self.peer.responses[3203])
        self.assertEqual(self.fixture.subject.read(IDS["quote_snapshot"])["response_facts"], [])
        self.assert_recovery(2)

    def test_injected_future_reprojection_preserves_original_bytes_and_expired_facts(self):
        self.prepare()
        first = self.launch("first")
        self.initialize(first)
        for action in QUOTE_ACTIONS:
            self.send(first, action)
        self.finish(first)
        original = self.fixture.subject.read(IDS["quote_snapshot"])["original_action_receipt"]
        frame = next(operation.frame for operation in self.fixture.operations if operation.action == "quote_snapshot")
        response = retained_response(self.root / "first-evidence", "quote_snapshot")
        originals = {path.name: path.read_bytes() for path in (self.root / "first-evidence").iterdir()}
        prior = next(row for row in self.fixture.subject.journal.read()["response_facts"].values()
                     if row["action"] == "quote_snapshot")
        # Explicit logical-clock injection AFTER the actual response was already
        # received/recorded. This is expired reprojection, not a delayed network
        # response, and the new received_at never rewrites the original fact.
        self.fixture.clock.offset = 1200
        late = facts.verify_response_facts(profile=self.fixture.profile, codec=self.fixture.codec,
            action_receipt=original, expected_action_receipt_id=original["id"], request_frame=frame,
            response_frame=response, received_at=self.fixture.clock.utcnow())
        self.assertTrue(late.as_dict()["received_after_profile_expiry"])
        self.assertFalse(late.as_dict()["facts"]["freshness_verified"])
        self.assertNotEqual(late.as_dict()["id"], prior["id"])
        self.assertNotEqual(late.as_dict()["received_at"], prior["received_at"])
        self.fixture.subject.journal.record_verified_response(late, request_id="late-quote-fact-only")
        self.assertEqual(self.fixture.subject.journal.read()["response_facts"][prior["id"]], prior)
        self.scenario_notes.append(dict(kind="EXPLICIT_FUTURE_RECEIVED_AT_REPROJECTION_NOT_NETWORK_DELAY",
            clock_offset_seconds=1200, original_fact_id=prior["id"], reprojected_fact_id=late.as_dict()["id"],
            original_received_at=prior["received_at"], injected_received_at=late.as_dict()["received_at"]))
        self.assertEqual({path.name: path.read_bytes() for path in (self.root / "first-evidence").iterdir()}, originals)
        self.assertEqual(self.peer.frames[-1], frame)
        self.assertEqual(len(self.peer.frames), 4)
        self.assert_recovery(4)

    def test_shared_stop_after_runtime_prevents_later_quote_sends(self):
        self.prepare()
        first = self.launch("first")
        self.initialize(first)
        self.send(first, "quote_runtime")
        frames_before = list(self.peer.frames)
        self.fixture.stop_account()
        for action in ("quote_security", "quote_snapshot"):
            self.assertEqual(self.send(first, action)["payload"]["status"], "UNKNOWN")
            self.assertIsNone(self.fixture.subject.read(IDS[action])["original_action_receipt"])
        self.finish(first)
        self.assertEqual(self.peer.frames, frames_before)
        self.assertEqual(len(self.peer.frames), 2)
        self.assertEqual(len(self.assertions_no_economics()["response_facts"]), 1)
        self.assertEqual(self.peer.errors, [])


class SyntheticQuoteWorkerTests(QuoteChainChecks, unittest.TestCase):
    """Standard CI: JSON-fake protocol, actual owned TCP/worker/SQLite path."""


if __name__ == "__main__":
    unittest.main()
