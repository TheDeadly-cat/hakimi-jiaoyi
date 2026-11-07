"""Real worker/TCP/SQLite path with explicitly synthetic JSON protocol in CI.

Actual pinned protobuf reuses these assertions in a separate private-runtime
probe. A missing package must fail that probe, never skip or substitute fakes.
"""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import time
import unittest

import hakimi_research
from exchange_terminal.services import terminal_broker_worker_supervisor as supervisor
from tests.broker_loopback_server_fixture import endpoint_guard
from tests.broker_submit_market_fixture import (
    ACTUAL, SYNTHETIC, ALL_ACTIONS, INITIAL_ACTIONS, IDS, QUOTE_ACTIONS, SERIALS,
    SubmitMarketFixture, OwnedSubmitPeer, response_frame,
)
from tests import test_terminal_broker_worker_supervisor as worker_fixture


TERMINAL = Path(__file__).resolve().parents[1]
CANONICAL = Path(hakimi_research.__file__).resolve().parent.parent


class SubmitMarketChainChecks:
    actual_context = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="new-submit-market-worker-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.context = self.actual_context
        self.layer = ACTUAL if self.context else SYNTHETIC
        self.bindings = self.context["bindings"] if self.context else None
        self.runtime_identity = self.context["runtime_identity"] if self.context else None
        self.sequence, self.scenario_notes = {}, []
        self.worker = worker_fixture.WorkerSupervisorTests(); self.worker.setUp()
        self.addCleanup(self.worker.doCleanups)

    def prepare(self, *, market_state=5):
        responses = {action: response_frame(action, bindings=self.bindings, market_state=market_state)
                     for action in SERIALS}
        self.peer = OwnedSubmitPeer(responses, lifetime=100 if self.context else 45)
        self.addCleanup(self.peer.close)
        guard = endpoint_guard(self.peer.endpoint); self.addCleanup(guard.close)
        self.fixture = SubmitMarketFixture(self.root, endpoint=self.peer.endpoint, layer=self.layer,
            runtime_identity=self.runtime_identity, bindings=self.bindings, evidence="parent-read-only")
        self.addCleanup(self.fixture.close)
        # Only expected-byte construction in the parent. The original child
        # must obtain both handshakes over its two real TCP connections.
        for channel in ("quote", "trade"):
            self.fixture.codec.accept_handshake(self.fixture.profile, channel, SERIALS[channel + "_init"],
                responses[channel + "_init"])
        self.peer.expected = {op.frame for op in self.fixture.operations if op.frame}
        self.peer.expected.update(self.fixture.encode(action) for action in (*QUOTE_ACTIONS, "trade_submit"))

    def launch(self, name, *, recovery=False, expire_bundle=False):
        prelude = self.context["child_prelude"](self.peer.endpoint, self.root) if self.context else ""
        script = "\n".join([
            "import sys,argparse,json", "from pathlib import Path", "RUNTIME_IDENTITY=PROTOBUF_BINDINGS=ACTUAL_PROOF=None", prelude,
            "sys.path[:0]=" + repr([str(CANONICAL), str(TERMINAL)]),
            "from tests.broker_submit_market_fixture import SubmitMarketFixture,BindStagesBeforeInput",
            "from tests.broker_loopback_server_fixture import endpoint_guard",
            "from exchange_terminal.services.terminal_broker_worker_entrypoint import serve",
            "p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()",
            "endpoint=" + repr(self.peer.endpoint), "guard=endpoint_guard(endpoint)",
            "f=SubmitMarketFixture(" + repr(str(self.root)) + ",endpoint=endpoint,layer=" + repr(self.layer) +
                ",runtime_identity=RUNTIME_IDENTITY,bindings=PROTOBUF_BINDINGS,initialize=False,evidence=" +
                repr(name + "-evidence") + ",recovery=" + repr(recovery) + ")",
            "if callable(ACTUAL_PROOF): ACTUAL_PROOF.stage('submit_market_fixture_bound')",
            "try: result=serve(run_id=a.run_id,request_id=a.request_id,coordinator=f.subject,input_stream=BindStagesBeforeInput(f,sys.stdin.buffer,expire_bundle=" + repr(expire_bundle) + "))",
            "finally:", " f.close();guard.close()",
            " proof=dict(protocol_layer=f.layer,io_order=f.io_order,preparation_error=f.preparation_error,scenario_notes=f.scenario_notes,private_flags=dict(isolated=sys.flags.isolated,no_site=sys.flags.no_site,dont_write_bytecode=sys.flags.dont_write_bytecode),actual_loader=ACTUAL_PROOF() if callable(ACTUAL_PROOF) else ACTUAL_PROOF)",
            " with (f.root/" + repr(name + "-report.json") + ").open('x',encoding='utf-8') as stream: json.dump(proof,stream,sort_keys=True)",
            "raise SystemExit(result)",
        ])
        path = self.worker.fixtures.path / (name + ".py"); path.write_text(script, encoding="utf-8")
        interpreter = Path(self.context["interpreter"]) if self.context else self.worker.interpreter
        spec = supervisor.make_test_spec(interpreter=interpreter, interpreter_sha256=sha256(interpreter.read_bytes()).hexdigest(),
            entrypoint=path, entrypoint_sha256=sha256(path.read_bytes()).hexdigest(), fixture_parent=self.worker.fixtures)
        if self.context:
            self.context["authorize_child_command"](spec, "submit-fixture-run", "submit-fixture-request", self.worker.outputs.path / name)
        handle = supervisor.launch(spec, output_parent=self.worker.outputs, run_dir=self.worker.outputs.path / name,
            run_id="submit-fixture-run", request_id="submit-fixture-request",
            limits=worker_fixture.limits(wall_seconds=60 if self.context else 8, cleanup_seconds=1))
        self.worker.handles.append(handle); self.sequence[id(handle)] = 0
        self.assertEqual(self.poll(handle, initial=True)["kind"], "READY")
        return handle

    def poll(self, handle, *, initial=False):
        deadline = time.monotonic() + (30 if initial and self.context else 15 if self.context else 4)
        while time.monotonic() < deadline:
            message = handle.poll_message(.1)
            if message is not None:
                return message
            if handle.finish(0) is not None:
                self.fail("submit worker ended before message: " + (handle.run_dir / "stderr.bin").read_text(encoding="utf-8", errors="replace"))
        self.fail("bounded submit worker message wait expired")

    def send(self, handle, action=None):
        self.sequence[id(handle)] += 1
        result = handle.reply(dict(schema_version="hakimi-broker-worker-message-v1", run_id="submit-fixture-run",
            request_id="submit-fixture-request", sequence=self.sequence[id(handle)], kind="INPUT" if action else "STOP",
            payload={"operation_id": IDS[action]} if action else {}))
        self.assertEqual(result["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")
        return self.poll(handle)

    def finish(self, handle, *, already_result=False, exit_code=0):
        if not already_result:
            self.assertEqual(self.send(handle)["kind"], "RESULT")
        result = handle.finish(10 if self.context else 3)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROTOCOL_RESULT_RECEIVED" if exit_code == 0 else "UNKNOWN")
        self.assertEqual((result["spawn_count"], result["restart_count"]), (1, 0))
        self.assertTrue(result["cleanup_confirmed"])
        self.assertEqual(result["exit_code"], exit_code)

    def initialize_and_query(self, handle):
        for action in INITIAL_ACTIONS:
            response = self.send(handle, action)
            self.assertEqual(response["kind"], "EVIDENCE")
            self.assertEqual(response["payload"]["status"], "CONNECTED" if action.endswith("_connect") else "UNKNOWN")
        for action in QUOTE_ACTIONS:
            response = self.send(handle, action)
            self.assertEqual(response["kind"], "EVIDENCE")
            self.assertEqual(response["payload"]["status"], "UNKNOWN")

    def assert_public_facts(self, count):
        state = self.fixture.subject.journal.read()
        self.assertEqual(len(state["response_facts"]), count)
        raw = json.dumps(state, sort_keys=True)
        for marker in ("connAESKey", "aesCBCiv", "private-fictional-key", "private-fictional-iv", "private-fictional-handshake-text"):
            self.assertNotIn(marker, raw)
        for row in state["response_facts"].values():
            self.assertTrue(row["test_only"]); self.assertFalse(row["source_authenticated"])
        return state

    def test_six_original_observations_submit_ack_and_reopen_without_new_tcp(self):
        self.prepare(); first = self.launch("first"); self.initialize_and_query(first)
        response = self.send(first, "trade_submit")
        self.assertEqual(response["kind"], "EVIDENCE")
        self.assertEqual(response["payload"]["status"], "ACKNOWLEDGED")
        self.finish(first)
        state = self.assert_public_facts(7)
        self.assertEqual(len(state["actions"]), 9); self.assertEqual(state["epoch"], 1)
        submitted = self.fixture.subject.journal.read(IDS["trade_submit"])["receipt"]
        self.assertEqual(len(submitted["payload"]["submit_observation"]["evidence"]), 6)
        self.assertEqual(len(self.peer.frames), 7); self.assertEqual(len(self.peer.clients), 2); self.assertEqual(self.peer.errors, [])
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertIsNone(proof["preparation_error"])
        self.assertEqual([row["kind"] for row in proof["io_order"]].count("send"), 7)
        self.assertEqual([row["kind"] for row in proof["io_order"]].count("connect"), 2)
        before = self.fixture.subject.journal.path.read_bytes(); registry = self.fixture.registry.read_bytes()
        frames_before = list(self.peer.frames)
        second = self.launch("recovery", recovery=True)
        for action in ALL_ACTIONS:
            result = self.send(second, action)
            self.assertEqual(result["kind"], "EVIDENCE")
            if action == "trade_submit": self.assertEqual(result["payload"]["status"], "ACKNOWLEDGED")
        self.finish(second)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.fixture.registry.read_bytes(), registry)
        self.assertEqual(self.peer.frames, frames_before); self.assertEqual(len(self.peer.clients), 2)
        self.assertFalse((self.root / "recovery-evidence").exists())
        proof = json.loads((self.root / "recovery-report.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["io_order"], [])

    def test_expired_observation_blocks_submit_while_permit_remains_future(self):
        self.prepare(); first = self.launch("first", expire_bundle=True); self.initialize_and_query(first)
        response = self.send(first, "trade_submit")
        self.assertEqual(response["kind"], "RESULT")
        self.assertEqual(response["payload"]["status"], "UNKNOWN")
        self.finish(first, already_result=True, exit_code=1)
        state = self.assert_public_facts(6)
        self.assertNotIn(IDS["trade_submit"], state["actions"])
        self.assertEqual(state["claims"], {}); self.assertEqual(len(self.peer.frames), 6)
        self.assertEqual(self.peer.errors, [])
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertIsNone(proof["preparation_error"])
        self.assertEqual(proof["scenario_notes"][-1]["kind"], "EXPLICIT_CLOCK_AFTER_BUNDLE_EXPIRY_PERMIT_STILL_FUTURE")
        self.scenario_notes.extend(proof["scenario_notes"])

    def test_closed_target_state_keeps_response_and_prevents_submit_binding(self):
        self.prepare(market_state=6); first = self.launch("first"); self.initialize_and_query(first)
        # Test bootstrap attempts the real journal factory; closed state has
        # a retained matched observation but cannot prepare a submit bundle.
        self.finish(first)
        state = self.assert_public_facts(6)
        self.assertNotIn(IDS["trade_submit"], state["actions"])
        self.assertEqual(state["claims"], {}); self.assertEqual(len(self.peer.frames), 6)
        market = next(row for row in state["response_facts"].values() if row["action"] == "quote_market_state")
        self.assertEqual(market["facts"]["market_state_code"], 6)
        proof = json.loads((self.root / "first-report.json").read_text(encoding="utf-8"))
        self.assertIn("SubmitObservationError", proof["preparation_error"])
        self.assertEqual(self.peer.errors, [])


    def test_early_out_of_order_input_cannot_bind_or_send_a_later_query(self):
        self.prepare(); first = self.launch("first")
        for action in INITIAL_ACTIONS:
            self.assertEqual(self.send(first, action)["kind"], "EVIDENCE")
        # Only runtime is now prebound. An INPUT for the later snapshot cannot
        # tell trusted assembly to encode it or advance past the fixed stage.
        result = self.send(first, "quote_snapshot")
        self.assertEqual(result["kind"], "RESULT")
        self.assertEqual(result["payload"]["status"], "UNKNOWN")
        self.finish(first, already_result=True, exit_code=1)
        state = self.assert_public_facts(2)
        self.assertEqual(state["epoch"], 0); self.assertEqual(state["claims"], {})
        self.assertEqual(len(self.peer.frames), 2)
        self.assertTrue(all(IDS[action] not in state["actions"] for action in QUOTE_ACTIONS))
        registry = json.loads(self.fixture.registry.read_text(encoding="utf-8"))
        self.assertEqual([row["action"] for row in registry["operations"]], list(INITIAL_ACTIONS) + ["quote_runtime"])
        self.assertEqual(self.peer.errors, [])


class SyntheticSubmitMarketWorkerTests(SubmitMarketChainChecks, unittest.TestCase):
    """Standard CI only: JSON fakes, real owned TCP/original worker/journal."""


if __name__ == "__main__":
    unittest.main()
