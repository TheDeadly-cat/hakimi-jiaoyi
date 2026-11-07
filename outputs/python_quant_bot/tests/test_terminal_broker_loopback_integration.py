"""Real local TCP + original coordinator/journal/worker, no broker or SDK.

Short-write and would-block fault injection are explicitly labelled. Other IO
uses the OS against a listener held by this test on its dynamic loopback port.
"""
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import select
import socket
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch

import hakimi_research
from exchange_terminal.services import terminal_broker_loopback_socket as adapter
from exchange_terminal.services import terminal_broker_worker_supervisor as supervisor
from tests.broker_action_coordinator_fixture import Fixture
from tests.broker_loopback_server_fixture import OwnedLoopbackServer, endpoint_guard
from tests import test_futu_us_equity_simulate_wire_v2 as frames
from tests import test_terminal_broker_worker_supervisor as worker_fixture


TERMINAL = Path(__file__).resolve().parents[1]
CANONICAL = Path(hakimi_research.__file__).resolve().parent.parent


class CountingSocket:
    """Optional fault injection delegates actual accepted bytes to the real fd."""
    def __init__(self, fd, before_io):
        self.fd = fd
        self.before_io = before_io
        self.actual_sends, self.send_calls = [], 0
        self.partial_next, self.failure_next = None, None
        self.close_reply_lost = False

    def __getattr__(self, name): return getattr(self.fd, name)
    def connect_ex(self, endpoint):
        self.before_io("connect")
        return self.fd.connect_ex(endpoint)
    def send(self, data):
        self.before_io("send")
        self.send_calls += 1
        if self.failure_next:
            error, self.failure_next = self.failure_next, None
            raise error
        offered = data if self.partial_next is None else data[:self.partial_next]
        self.partial_next = None
        amount = self.fd.send(offered)
        self.actual_sends.append(offered[:amount])
        return amount
    def close(self):
        self.fd.close()
        if self.close_reply_lost:
            raise OSError("explicit close-reply failure after owned fd release")


class LoopbackCoordinatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="new-owned-tcp-coordinator-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.connections, self.sockets = {}, {}
        self.factory_count = 0
        self.committed, self.io_order_proof = {}, []

    def setup_peer(self, *, wire_bounds_changes=None, **scenario):
        self.peer = OwnedLoopbackServer(**scenario)
        self.addCleanup(self.peer.close)
        guard = endpoint_guard(self.peer.endpoint)
        self.addCleanup(guard.close)
        self.fixture = Fixture(self.root, endpoint=self.peer.endpoint, wire_bounds_changes=wire_bounds_changes)
        self.addCleanup(self.fixture.close)
        self.peer.expected = {o.frame for o in self.fixture.operations if o.frame}
        begin = self.fixture.subject.journal.begin_action
        def committed_action(*args, **kwargs):
            result = begin(*args, **kwargs)
            if not result["replayed"]:
                # This read happens AFTER the real journal/stop transaction has
                # returned, outside the actual-write barrier. IO checks below
                # inspect only this immutable observation, not another DB lock.
                identity = result["receipt"]["request_id"]
                observed = self.fixture.subject.journal.read(identity)["receipt"]
                self.assertEqual(observed, result["receipt"])
                self.committed[identity] = observed
            return result
        self.fixture.subject.journal.begin_action = committed_action
        self.fixture.subject.factory = self.factory
        self.fixture.seed()
        return self.fixture

    def factory(self, channel):
        self.before_io("factory")
        self.factory_count += 1
        connection = adapter.LoopbackWireConnection(self.peer.endpoint)
        def open_socket():
            counted = CountingSocket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), self.before_io)
            self.sockets[channel] = counted
            return counted
        connection._open_socket = open_socket
        self.connections[channel] = connection
        return connection

    def before_io(self, kind):
        operation = self.fixture.subject._active
        self.assertIsNotNone(operation)
        self.assertIn(operation.operation_id, self.committed)
        receipt = self.committed[operation.operation_id]
        self.assertEqual(receipt["kind"], "ACTION")
        self.assertEqual(receipt["payload"]["frame_bytes"], len(operation.frame))
        self.assertEqual(receipt["payload"]["frame_sha256"], sha256(operation.frame).hexdigest() if operation.frame else None)
        self.io_order_proof.append((kind, operation.operation_id, receipt["id"]))

    def peer_workspace(self):
        peer = Fixture(self.root, workspace="workspace-peer", evidence="peer-evidence", endpoint=self.peer.endpoint)
        self.addCleanup(peer.close)
        return peer

    def test_real_fragmented_tcp_reply_enters_typed_ack_without_creating_fill(self):
        fixture = self.setup_peer(fragmented=True)
        fixture.initialize()
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "ACKNOWLEDGED", result.get("reason"))
        self.assertEqual(result["response_facts"][0]["status"], "ACK_SCOPE_MATCHED")
        self.assertTrue(result["response_facts"][0]["test_only"])
        self.assertFalse(result["response_facts"][0]["source_authenticated"])
        original = fixture.subject.journal.read()
        claim = next(iter(original["claims"].values()))
        self.assertEqual(claim["filled_quantity"], 0)
        self.assertIsNone(claim["fees"])
        self.assertFalse(claim["fees_final"])
        self.assertGreater(Decimal(original["financial"]["cash_reserved"]), 60)
        self.assertEqual(self.factory_count, 1)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertEqual(self.peer.frames, [fixture.operations[1].frame, fixture.operations[2].frame])
        self.assertEqual(b"".join(self.sockets["trade"].actual_sends), b"".join(self.peer.frames))
        self.assertEqual({row[0] for row in self.io_order_proof}, {"factory", "connect", "send"})
        self.assertEqual(len(self.committed), 3)

    def test_peer_stop_prevents_real_connection_before_factory(self):
        fixture = self.setup_peer()
        peer = self.peer_workspace()
        peer.stop_account()
        result = fixture.execute("trade_connect")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["original_action_receipt"])
        self.assertEqual(self.factory_count, 0)
        self.assertEqual(self.peer.clients, [])

    def test_complete_response_then_fin_is_kept_and_next_os_send_is_refused(self):
        fixture = self.setup_peer(fin_after="trade_submit")
        fixture.initialize()
        self.assertEqual(fixture.execute("trade_submit")["status"], "ACKNOWLEDGED")
        self.assertTrue(self.peer.fin_sent.wait(1))
        self.assertTrue(select.select([self.connections["trade"]._socket], [], [], 1)[0])
        sends = list(self.sockets["trade"].actual_sends)
        result = fixture.execute("trade_observe")
        self.assertEqual(result["status"], "UNKNOWN")  # Existing transport conservatively treats attempted send as unknown.
        self.assertEqual(self.sockets["trade"].actual_sends, sends)
        self.assertEqual(len(self.peer.frames), 2)
        self.assertEqual(self.factory_count, 1)
        self.assertEqual(fixture.subject.read("coordinator-trade_submit")["status"], "ACKNOWLEDGED")

    def test_eof_before_first_frame_never_enters_os_send_or_reconnects(self):
        fixture = self.setup_peer(eof_on_accept=True)
        self.assertEqual(fixture.execute("trade_connect")["status"], "CONNECTED")
        self.assertTrue(self.peer.fin_sent.wait(1))
        self.assertTrue(select.select([self.connections["trade"]._socket], [], [], 1)[0])
        result = fixture.execute("trade_init")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(self.sockets["trade"].send_calls, 0)
        self.assertEqual(self.peer.frames, [])
        before = fixture.subject.journal.path.read_bytes()
        fixture.execute("trade_init")
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.factory_count, 1)

    def test_real_response_timeout_does_not_hold_account_stop_barrier(self):
        fixture = self.setup_peer(stall_on="trade_submit", wire_bounds_changes=dict(rpc_timeout_seconds=1))
        peer = self.peer_workspace()
        fixture.initialize(); self.peer.frame_received.clear()
        values = []
        thread = Thread(target=lambda: values.append(fixture.execute("trade_submit")))
        thread.start()
        try:
            self.assertTrue(self.peer.frame_received.wait(2))
            start = time.monotonic(); peer.stop_account()
            self.assertLess(time.monotonic() - start, 1)
        finally:
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(values[0]["status"], "UNKNOWN")
        self.assertEqual(values[0]["action_state"]["outcome"]["sent_bytes"], len(fixture.operations[2].frame))
        self.assertFalse(values[0]["action_state"]["outcome"]["response_complete"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 60)
        self.assertEqual(len(self.peer.frames), 2)
        self.assertEqual(self.factory_count, 1)

    def test_injected_real_short_send_then_peer_stop_preserves_exact_os_prefix(self):
        fixture = self.setup_peer()
        peer = self.peer_workspace()
        fixture.initialize()
        self.sockets["trade"].partial_next = 9  # Explicit injection, not a natural-backpressure claim.
        original = fixture.subject._gate.after_write
        def stop_after_write(context, permit, written):
            original(context, permit, written)
            peer.stop_account()
        with patch.object(fixture.subject._gate, "after_write", side_effect=stop_after_write):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 9)
        self.assertEqual(result["action_state"]["outcome"]["possible_sent_bytes"], 9)
        self.assertEqual(self.sockets["trade"].actual_sends[-1], fixture.operations[2].frame[:9])
        deadline = time.monotonic() + 1
        while not self.peer.partial and time.monotonic() < deadline: time.sleep(.005)
        self.assertEqual(self.peer.partial, [fixture.operations[2].frame[:9]])
        self.assertEqual(len(self.peer.frames), 1)
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 60)

    def test_injected_would_block_does_not_retry_or_invent_no_dispatch(self):
        fixture = self.setup_peer(); fixture.initialize()
        counted = self.sockets["trade"]
        before, calls = list(counted.actual_sends), counted.send_calls
        counted.failure_next = BlockingIOError("explicit synthetic would-block injection")
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(counted.send_calls, calls + 1)
        self.assertEqual(counted.actual_sends, before)
        self.assertEqual(result["action_state"]["outcome"]["possible_sent_bytes"], len(fixture.operations[2].frame))
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 60)
        self.assertEqual(len(self.peer.frames), 1)

    def test_real_wrong_serial_reply_is_retained_unknown_not_typed_ack(self):
        fixture = self.setup_peer(); fixture.initialize()
        self.peer.replies["trade_submit"] = frames.response_frame("trade_submit", 999, payload=Fixture.response("trade_submit"))
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["response_facts"], [])
        self.assertGreater(result["action_state"]["outcome"]["sent_bytes"], 0)
        self.assertIsNone(next(iter(fixture.subject.journal.read()["claims"].values()))["broker_order_id"])

    def test_real_extra_response_frame_is_unknown_and_never_becomes_typed_ack(self):
        fixture = self.setup_peer(); fixture.initialize()
        reply = frames.response_frame("trade_submit", 2, payload=Fixture.response("trade_submit"))
        self.peer.replies["trade_submit"] = reply + reply  # Two complete frames in one actual peer write.
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["response_facts"], [])
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], len(fixture.operations[2].frame))
        self.assertFalse(result["action_state"]["outcome"]["response_complete"])
        raw = json.loads((fixture.subject._evidence / ("outcome-" + result["raw_evidence_id"] + ".json")).read_text())
        self.assertEqual(raw["raw_outcome"]["error"], "unsolicited_or_trailing_data")
        trailing = [record for record in fixture.subject._sink.records if record["header"]["kind"] == "unsolicited_peek"]
        self.assertEqual([record["raw"] for record in trailing], [reply[:1]])
        self.assertEqual(len(self.peer.clients), 1)
        self.assertEqual(self.peer.frames, [fixture.operations[1].frame, fixture.operations[2].frame])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 60)
        before = fixture.subject.journal.path.read_bytes()
        self.assertTrue(fixture.execute("trade_submit")["recovered_original"])
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(len(self.peer.clients), 1)

    def test_real_send_timeout_and_injected_close_reply_loss_never_report_clean_or_unsent(self):
        fixture = self.setup_peer(stall_on="trade_submit", wire_bounds_changes=dict(rpc_timeout_seconds=1))
        fixture.initialize()
        self.sockets["trade"].close_reply_lost = True  # The OS fd closes, but its wrapper's completion is deliberately lost.
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["action_state"]["outcome"]["status"], "UNKNOWN")
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], len(fixture.operations[2].frame))
        raw = json.loads((fixture.subject._evidence / ("outcome-" + result["raw_evidence_id"] + ".json")).read_text())
        self.assertFalse(raw["raw_outcome"]["cleanup_confirmed"])
        self.assertFalse(fixture.subject.close()["cleanup_confirmed"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 60)
        self.assertEqual(len(self.peer.frames), 2)


class LoopbackOwnedWorkerTests(unittest.TestCase):
    def setup_peer(self, *, stall=False):
        temp = tempfile.TemporaryDirectory(prefix="new-owned-tcp-worker-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.peer = OwnedLoopbackServer(stall_on="trade_submit" if stall else None)
        self.addCleanup(self.peer.close)
        guard = endpoint_guard(self.peer.endpoint)
        self.addCleanup(guard.close)
        self.wire_changes = dict(rpc_timeout_seconds=1) if stall else None
        self.fixture = Fixture(self.root, endpoint=self.peer.endpoint, wire_bounds_changes=self.wire_changes)
        self.addCleanup(self.fixture.close)
        self.fixture.seed()
        self.peer.expected = {o.frame for o in self.fixture.operations if o.frame}
        self.worker = worker_fixture.WorkerSupervisorTests()
        self.worker.setUp(); self.addCleanup(self.worker.doCleanups)
        self.sequence = {}

    def launch(self, name, *, extra="", wall_seconds=8):
        script = "\n".join([
            "import sys,argparse",
            "sys.path[:0]=" + repr([str(CANONICAL), str(TERMINAL)]),
            "from tests.broker_action_coordinator_fixture import Fixture",
            "from tests.broker_loopback_server_fixture import endpoint_guard",
            "from exchange_terminal.services.terminal_broker_loopback_socket import pinned_loopback_factory",
            "from exchange_terminal.services.terminal_broker_worker_entrypoint import serve",
            "p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()",
            "endpoint=" + repr(self.peer.endpoint),
            "guard=endpoint_guard(endpoint)",
            "f=Fixture(" + repr(str(self.root)) + ",initialize=False,evidence=" + repr(name) + ",endpoint=endpoint,wire_bounds_changes=" + repr(self.wire_changes) + ")",
            "f.subject.factory=pinned_loopback_factory(endpoint)",
            extra,
            "try: result=serve(run_id=a.run_id,request_id=a.request_id,coordinator=f.subject)",
            "finally: f.close();guard.close()",
            "raise SystemExit(result)",
        ])
        self.worker.count += 1
        path = self.worker.fixtures.path / (name + ".py")
        path.write_text(script, encoding="utf-8")
        spec = supervisor.make_test_spec(interpreter=self.worker.interpreter, interpreter_sha256=self.worker.python_hash,
            entrypoint=path, entrypoint_sha256=sha256(path.read_bytes()).hexdigest(), fixture_parent=self.worker.fixtures)
        handle = supervisor.launch(spec, output_parent=self.worker.outputs, run_dir=self.worker.outputs.path / name,
            run_id="owned-tcp-run", request_id="owned-tcp-request", limits=worker_fixture.limits(wall_seconds=wall_seconds, cleanup_seconds=1))
        self.worker.handles.append(handle); self.sequence[id(handle)] = 0
        self.assertEqual(self.poll(handle)["kind"], "READY")
        return handle

    def poll(self, handle):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            message = handle.poll_message(.1)
            if message is not None: return message
            if handle.finish(0) is not None:
                self.fail((handle.run_dir / "stderr.bin").read_bytes().decode("utf-8", errors="replace"))
        self.fail("owned worker message timeout")

    def write_input(self, handle, action=None):
        self.sequence[id(handle)] += 1
        reply = handle.reply(dict(schema_version="hakimi-broker-worker-message-v1", run_id="owned-tcp-run",
            request_id="owned-tcp-request", sequence=self.sequence[id(handle)], kind="INPUT" if action else "STOP",
            payload={"operation_id": "coordinator-" + action} if action else {}))
        self.assertEqual(reply["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")

    def send(self, handle, action=None):
        self.write_input(handle, action)
        return self.poll(handle)

    def finish(self, handle):
        self.assertEqual(self.send(handle)["kind"], "RESULT")
        result = handle.finish(9)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "PROTOCOL_RESULT_RECEIVED")
        self.assertEqual(result["spawn_count"], 1)
        self.assertEqual(result["restart_count"], 0)
        self.assertTrue(result["cleanup_confirmed"])

    def run_and_reopen(self, *, stall=False):
        self.setup_peer(stall=stall)
        first = self.launch("actual-tcp-first")
        statuses = [self.send(first, action)["payload"]["status"] for action in ("trade_connect", "trade_init", "trade_submit")]
        self.assertEqual(statuses, ["CONNECTED", "UNKNOWN", "UNKNOWN" if stall else "ACKNOWLEDGED"])
        self.finish(first)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertEqual(len(self.peer.frames), 2)
        before = self.fixture.subject.journal.path.read_bytes()
        frames_before = list(self.peer.frames)
        second = self.launch("actual-tcp-reopen")
        self.assertEqual(self.send(second, "trade_submit")["payload"]["status"], statuses[-1])
        self.finish(second)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.peer.frames, frames_before)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertFalse((self.root / "actual-tcp-reopen").exists())
        claim = next(iter(self.fixture.subject.journal.read()["claims"].values()))
        self.assertFalse(claim["fees_final"])
        self.assertEqual(claim["filled_quantity"], 0)

    def test_real_tcp_inside_original_worker_and_same_id_reopen(self):
        self.run_and_reopen()

    def test_real_tcp_timeout_inside_worker_stays_unknown_on_reopen(self):
        self.run_and_reopen(stall=True)

    def test_two_real_workers_race_original_id_and_only_one_os_connection_exists(self):
        self.setup_peer()
        handles = []
        names = ("actual-tcp-race-one", "actual-tcp-race-two")
        for name in names:
            extra = "\n".join([
                "import time",
                "begin=f.subject.journal.begin_action",
                "def synchronized_begin(*args,**kwargs):",
                " (f.root/" + repr(name + "-ready") + ").write_text('before-original-begin')",
                " deadline=time.monotonic()+3",
                " while not (f.root/'release-original-id-race').exists():",
                "  if time.monotonic()>=deadline: raise TimeoutError('test rendezvous deadline')",
                "  time.sleep(.005)",
                " return begin(*args,**kwargs)",
                "f.subject.journal.begin_action=synchronized_begin",
            ])
            handles.append(self.launch(name, extra=extra))
        for handle in handles:
            self.write_input(handle, "trade_connect")
        deadline = time.monotonic() + 2
        while not all((self.root / (name + "-ready")).exists() for name in names):
            self.assertLess(time.monotonic(), deadline)
            self.assertTrue(all(handle.finish(0) is None for handle in handles))
            time.sleep(.005)
        # Both actual processes read the old journal before either can begin;
        # this only coordinates scheduling, never bypasses its real transaction.
        self.assertEqual(self.fixture.subject.journal.read()["actions"], {})
        (self.root / "release-original-id-race").write_text("release both")
        messages = [self.poll(handle) for handle in handles]
        self.assertTrue(all(message["kind"] == "EVIDENCE" for message in messages), messages)
        self.assertIn("CONNECTED", [message["payload"]["status"] for message in messages])
        for handle in handles:
            self.finish(handle)
        self.assertTrue(self.peer.accepted.wait(1))
        self.assertEqual(len(self.peer.clients), 1)
        self.assertEqual(self.peer.frames, [])
        self.assertEqual(self.peer.received_chunks, [])
        self.assertEqual(len(self.fixture.subject.journal.read()["actions"]), 1)
        self.assertEqual(sum((self.root / name).exists() for name in names), 1)
        self.assertEqual(self.fixture.subject.read("coordinator-trade_connect")["status"], "CONNECTED")
        before = self.fixture.subject.journal.path.read_bytes()
        recovery = self.launch("actual-tcp-race-read-original")
        self.assertEqual(self.send(recovery, "trade_connect")["payload"]["status"], "CONNECTED")
        self.finish(recovery)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertFalse((self.root / "actual-tcp-race-read-original").exists())

    def test_real_peer_prefix_then_watchdog_death_preserves_unknown_original(self):
        self.setup_peer()
        extra = "\n".join([
            "import socket,time",
            "from exchange_terminal.services.terminal_broker_loopback_socket import LoopbackWireConnection",
            "from tests.test_terminal_broker_loopback_integration import CountingSocket",
            "def factory(channel):",
            " connection=LoopbackWireConnection(endpoint)",
            " def open_socket():",
            "  counted=CountingSocket(socket.socket(socket.AF_INET,socket.SOCK_STREAM),lambda kind:None)",
            "  f.actual_socket=counted",
            "  return counted",
            " connection._open_socket=open_socket",
            " return connection",
            "f.subject.factory=factory",
            "original_after=f.subject._gate.after_write",
            "def wedge_after_write(context,permit,written):",
            " original_after(context,permit,written)",
            " if context['action']=='trade_init': f.actual_socket.partial_next=9",
            " if context['action']=='trade_submit':",
            "  (f.root/'actual-prefix-sent').write_text(str(written))",
            "  time.sleep(30)  # Explicit hang injection after a real 9-byte OS send.",
            "f.subject._gate.after_write=wedge_after_write",
        ])
        handle = self.launch("actual-tcp-watchdog", extra=extra, wall_seconds=4)
        self.assertEqual(self.send(handle, "trade_connect")["payload"]["status"], "CONNECTED")
        self.assertEqual(self.send(handle, "trade_init")["payload"]["status"], "UNKNOWN")
        self.write_input(handle, "trade_submit")
        expected = self.fixture.operations[1].frame + self.fixture.operations[2].frame[:9]
        deadline = time.monotonic() + 2
        while b"".join(self.peer.received_chunks) != expected or not (self.root / "actual-prefix-sent").exists():
            self.assertLess(time.monotonic(), deadline)
            self.assertIsNone(handle.finish(0))
            time.sleep(.005)
        self.assertEqual((self.root / "actual-prefix-sent").read_text(), "9")
        self.assertIsNone(handle._process.poll())  # The peer observed these bytes before process death.
        start = time.monotonic(); self.fixture.stop_account()
        self.assertLess(time.monotonic() - start, 1)
        final = handle.finish(5)
        self.assertIsNotNone(final)
        self.assertEqual(final["status"], "UNKNOWN")
        self.assertIn("WALL_DEADLINE", final["reasons"])
        self.assertTrue(final["cleanup_confirmed"])
        self.assertEqual((final["spawn_count"], final["restart_count"]), (1, 0))
        self.assertIsNotNone(handle._process.poll())
        deadline = time.monotonic() + 1
        while not self.peer.partial and time.monotonic() < deadline: time.sleep(.005)
        self.assertEqual(self.peer.partial, [self.fixture.operations[2].frame[:9]])
        self.assertEqual(self.peer.frames, [self.fixture.operations[1].frame])
        self.assertEqual(len(self.peer.clients), 1)
        original = self.fixture.subject.read("coordinator-trade_submit")
        self.assertEqual(original["status"], "UNKNOWN")
        self.assertIsNone(original["action_state"]["outcome"])  # Volatile send count was never committed.
        self.assertEqual(original["response_facts"], [])
        ledger = self.fixture.subject.journal.read()
        self.assertEqual(next(iter(ledger["claims"].values()))["state"], "DISPATCH_INTENT")
        self.assertGreater(Decimal(ledger["financial"]["cash_reserved"]), 60)
        before = self.fixture.subject.journal.path.read_bytes()
        receipt = (handle.run_dir / "result.json").read_bytes()
        recovery = self.launch("actual-tcp-watchdog-read-original")
        self.assertEqual(self.send(recovery, "trade_submit")["payload"]["status"], "UNKNOWN")
        self.finish(recovery)
        self.assertEqual(self.fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual((handle.run_dir / "result.json").read_bytes(), receipt)
        self.assertEqual(b"".join(self.peer.received_chunks), expected)
        self.assertEqual(len(self.peer.clients), 1)
        self.assertFalse((self.root / "actual-tcp-watchdog-read-original").exists())


if __name__ == "__main__":
    unittest.main()
