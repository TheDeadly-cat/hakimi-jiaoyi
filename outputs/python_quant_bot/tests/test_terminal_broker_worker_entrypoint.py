"""Owned bounded children run the real coordinator; all wire IO is synthetic."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import time
import unittest

import hakimi_research

from exchange_terminal.services import terminal_broker_worker_entrypoint as entry
from exchange_terminal.services import terminal_broker_worker_supervisor as supervisor
from tests.broker_action_coordinator_fixture import Fixture
from tests import test_terminal_broker_worker_supervisor as worker_fixture


TERMINAL = Path(__file__).resolve().parents[1]
CANONICAL = Path(hakimi_research.__file__).resolve().parent.parent


class BrokerWorkerEntrypointTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="new-coordinator-child-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.fixture = Fixture(self.root)
        self.fixture.seed()
        self.addCleanup(self.fixture.close)
        self.worker = worker_fixture.WorkerSupervisorTests()
        self.worker.setUp()
        self.addCleanup(self.worker.doCleanups)
        self.sequence = {}

    def launch(self, *, evidence="child-evidence", extra="", standalone=False, **limits):
        if standalone:
            body = entry.__file__
            script = Path(body).read_text(encoding="utf-8")
        else:
            script = "\n".join([
                "import sys,pathlib,argparse,json",
                "sys.path.insert(0," + repr(str(CANONICAL)) + ")",
                "sys.path.insert(0," + repr(str(TERMINAL)) + ")",
                "from tests.broker_action_coordinator_fixture import Fixture,network_and_sdk_blockers",
                "from exchange_terminal.services.terminal_broker_worker_entrypoint import serve",
                "network_and_sdk_blockers()",
                "p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()",
                "f=Fixture(" + repr(str(self.root)) + ",initialize=False,evidence=" + repr(evidence) + ")",
                extra,
                "try: result=serve(run_id=a.run_id,request_id=a.request_id,coordinator=f.subject)",
                "finally: f.close()",
                "raise SystemExit(result)",
            ])
        self.worker.count += 1
        path = self.worker.fixtures.path / ("assembled-" + str(self.worker.count) + ".py")
        path.write_text(script, encoding="utf-8")
        spec = supervisor.make_test_spec(interpreter=self.worker.interpreter,
            interpreter_sha256=self.worker.python_hash, entrypoint=path,
            entrypoint_sha256=sha256(path.read_bytes()).hexdigest(), fixture_parent=self.worker.fixtures)
        handle = supervisor.launch(spec, output_parent=self.worker.outputs,
            run_dir=self.worker.outputs.path / ("run-" + str(self.worker.count)),
            run_id="coordinator-child-run", request_id="coordinator-child-request",
            limits=worker_fixture.limits(wall_seconds=6, cleanup_seconds=1, **limits))
        self.worker.handles.append(handle)
        self.sequence[id(handle)] = 0
        self.assertEqual(self.poll(handle)["kind"], "READY")
        return handle

    def poll(self, handle):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            message = handle.poll_message(.1)
            if message is not None:
                return message
            final = handle.finish(0)
            if final is not None:
                stderr = (handle.run_dir / "stderr.bin").read_bytes().decode("utf-8", errors="replace")
                self.fail("child finished without message: " + str(final) + "\n" + stderr)
        self.fail("owned child did not emit bounded protocol message")

    def send(self, handle, action=None, *, stop=False):
        self.sequence[id(handle)] += 1
        value = dict(schema_version=entry.SCHEMA, run_id="coordinator-child-run",
            request_id="coordinator-child-request", sequence=self.sequence[id(handle)],
            kind="STOP" if stop else "INPUT", payload={} if stop else {"operation_id": "coordinator-" + action})
        result = handle.reply(value)
        self.assertEqual(result["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")
        return self.poll(handle)

    def finished(self, handle):
        result = handle.finish(handle.limits.wall_seconds + handle.limits.cleanup_seconds)
        self.assertIsNotNone(result)
        self.assertEqual(result["spawn_count"], 1)
        self.assertEqual(result["restart_count"], 0)
        self.assertFalse(any(result["permissions"].values()))
        return result

    def wire_events(self):
        path = self.root / "wire-events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_standalone_production_entrypoint_denies_without_any_business_io(self):
        handle = self.launch(standalone=True)
        message = self.send(handle, "trade_connect")
        self.assertEqual(message["payload"]["status"], "DENIED")
        self.assertEqual(self.send(handle, stop=True)["payload"]["status"], "PROTOCOL_COMPLETE")
        self.assertEqual(self.finished(handle)["status"], "PROTOCOL_RESULT_RECEIVED")
        self.assertEqual(self.wire_events(), [])
        self.assertEqual(self.fixture.subject.journal.read()["actions"], {})

    def test_owned_worker_real_journal_transport_and_typed_ack_keep_financial_reserve(self):
        handle = self.launch()
        for action, status in (("trade_connect", "CONNECTED"), ("trade_init", "UNKNOWN"), ("trade_submit", "ACKNOWLEDGED")):
            message = self.send(handle, action)
            self.assertEqual((message["kind"], message["payload"]["status"]), ("EVIDENCE", status), message)
        self.assertEqual(self.send(handle, stop=True)["kind"], "RESULT")
        self.assertEqual(self.finished(handle)["status"], "PROTOCOL_RESULT_RECEIVED")
        result = self.fixture.subject.read("coordinator-trade_submit")
        self.assertEqual(result["status"], "ACKNOWLEDGED")
        original = result["action_state"]
        self.assertEqual(original["outcome"]["sent_bytes"], original["frame_bytes"])
        self.assertEqual(len(original["outcome_history"]), 2)
        self.assertEqual(original["outcome_history"][0]["status"], "UNKNOWN")
        ledger = self.fixture.subject.journal.read()
        claim = next(iter(ledger["claims"].values()))
        self.assertEqual(claim["filled_quantity"], 0)
        self.assertIsNone(claim["fees"])
        self.assertFalse(claim["fees_final"])
        self.assertGreater(float(ledger["financial"]["cash_reserved"]), 60)
        self.assertEqual(len(ledger["actions"]), 3)
        self.assertEqual(len([e for e in self.wire_events() if e["kind"] == "factory"]), 1)
        self.assertTrue((self.root / "child-evidence" / "coordinator-final.json").exists())

    def test_second_worker_reads_same_operations_without_factory_or_new_journal_bytes(self):
        first = self.launch(evidence="first-child")
        for action in ("trade_connect", "trade_init", "trade_submit"):
            self.send(first, action)
        self.send(first, stop=True); self.finished(first)
        before = self.fixture.subject.journal.path.read_bytes()
        events = self.wire_events()
        second = self.launch(evidence="second-child")
        for action in ("trade_submit", "trade_init", "trade_connect"):
            self.assertEqual(self.send(second, action)["kind"], "EVIDENCE")
        self.send(second, stop=True); self.finished(second)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.wire_events(), events)
        self.assertFalse((self.root / "second-child").exists())

    def test_lost_action_commit_reply_in_child_never_constructs_connection_on_recovery(self):
        extra = "\n".join([
            "original_commit=f.subject.journal._commit",
            "def lose_commit_reply(connection):",
            " original_commit(connection)",
            " raise OSError('synthetic commit reply lost')",
            "f.subject.journal._commit=lose_commit_reply",
        ])
        first = self.launch(extra=extra, evidence="lost-commit-child")
        self.assertEqual(self.send(first, "trade_connect")["payload"]["status"], "UNKNOWN")
        self.send(first, stop=True); self.finished(first)
        result = self.fixture.subject.read("coordinator-trade_connect")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["action_state"]["outcome"])
        second = self.launch(evidence="lost-commit-recovery")
        self.assertEqual(self.send(second, "trade_connect")["payload"]["status"], "UNKNOWN")
        self.send(second, stop=True); self.finished(second)
        self.assertEqual(self.wire_events(), [])
        self.assertEqual(len(self.fixture.subject.journal.read()["actions"]), 1)

    def test_two_processes_same_action_allow_only_one_actual_connection(self):
        first, second = self.launch(evidence="concurrent-one"), self.launch(evidence="concurrent-two")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda handle: self.send(handle, "trade_connect"), (first, second)))
        self.assertGreaterEqual(sum(r["kind"] == "EVIDENCE" and r["payload"]["status"] == "CONNECTED" for r in results), 1)
        for handle, message in zip((first, second), results):
            if message["kind"] == "EVIDENCE":
                self.send(handle, stop=True)
            self.finished(handle)
        self.assertEqual(len([e for e in self.wire_events() if e["kind"] == "factory"]), 1)
        self.assertEqual(len([e for e in self.wire_events() if e["kind"] == "connect"]), 1)
        self.assertEqual(len(self.fixture.subject.journal.read()["actions"]), 1)

    def test_partial_write_then_wedged_child_keeps_unknown_and_stop_remains_available(self):
        extra = "\n".join([
            "import time",
            "original_factory=f.factory",
            "def factory(channel):",
            " connection=original_factory(channel)",
            " return connection",
            "f.subject.factory=factory",
            "original_after=f.subject._gate.after_write",
            "def wedge_after_write(context,permit,written):",
            " original_after(context,permit,written)",
            " if context['action']=='trade_init': f.connections['trade'].parts=[10]",
            " if context['action']=='trade_submit':",
            "  (f.root/'partial-write-observed').write_text(str(written))",
            "  time.sleep(30)",
            "f.subject._gate.after_write=wedge_after_write",
        ])
        handle = self.launch(extra=extra, evidence="wedged-child")
        self.send(handle, "trade_connect"); self.send(handle, "trade_init")
        self.sequence[id(handle)] += 1
        handle.reply(dict(schema_version=entry.SCHEMA, run_id="coordinator-child-run", request_id="coordinator-child-request",
            sequence=self.sequence[id(handle)], kind="INPUT", payload={"operation_id": "coordinator-trade_submit"}))
        deadline = time.monotonic() + 3
        while not (self.root / "partial-write-observed").exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.01)
        start = time.monotonic()
        self.assertEqual((self.root / "partial-write-observed").read_text(), "10")
        self.fixture.stop_account()
        self.assertLess(time.monotonic() - start, 1)
        final = self.finished(handle)
        self.assertEqual(final["status"], "UNKNOWN")
        self.assertTrue(final["cleanup_confirmed"])
        original = self.fixture.subject.read("coordinator-trade_submit")
        self.assertEqual(original["status"], "UNKNOWN")
        self.assertIsNone(original["action_state"]["outcome"])
        claim = next(iter(self.fixture.subject.journal.read()["claims"].values()))
        self.assertEqual(claim["state"], "DISPATCH_INTENT")
        self.assertFalse(claim["fees_final"])
        recovery = self.launch(evidence="wedged-recovery")
        self.assertEqual(self.send(recovery, "trade_submit")["payload"]["status"], "UNKNOWN")
        before = self.wire_events()
        self.send(recovery, stop=True); self.finished(recovery)
        self.assertEqual(self.wire_events(), before)

    def test_worker_payload_cannot_supply_account_frame_path_or_new_binding(self):
        raw = dict(schema_version=entry.SCHEMA, run_id="run", request_id="request", sequence=1,
                   kind="INPUT", payload={"operation_id": "coordinator-trade_connect", "account_id": "900000000000001"})
        output = io.BytesIO()
        code = entry.serve(run_id="run", request_id="request", coordinator=self.fixture.subject,
            input_stream=io.BytesIO(json.dumps(raw).encode() + b"\n"), output_stream=output)
        self.assertEqual(code, 1)
        messages = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(messages[-1]["payload"]["status"], "UNKNOWN")
        self.assertEqual(self.wire_events(), [])
        self.assertEqual(self.fixture.subject.journal.read()["actions"], {})


if __name__ == "__main__":
    unittest.main()
