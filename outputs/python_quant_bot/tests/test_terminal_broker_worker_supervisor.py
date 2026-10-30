"""New TEMP synthetic Python children only; no SDK, socket, DB or old workspace.

The explicitly hashed current test interpreter is a TEST_ONLY identity. These
tests do not attest that interpreter as an installed production package.
"""
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_worker_supervisor as worker

COMMON = '''import argparse,json,os,sys,time
p=argparse.ArgumentParser();p.add_argument('--run-id');p.add_argument('--request-id');a=p.parse_args()
seq=0
def emit(kind,payload=None,request_id=None,sequence=None):
 global seq
 seq+=1
 value={'schema_version':'hakimi-broker-worker-message-v1','run_id':a.run_id,
 'request_id':request_id or a.request_id,'sequence':seq if sequence is None else sequence,
 'kind':kind,'payload':payload or {}}
 sys.stdout.buffer.write(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()+b'\\n')
 sys.stdout.buffer.flush()
'''


def limits(**changes):
    values = dict(wall_seconds=3, stop_seconds=0.25, cleanup_seconds=0.6, reply_seconds=0.3, poll_seconds=1,
                  max_stdin_bytes=32768, max_stdout_bytes=65536, max_stderr_bytes=16384,
                  max_evidence_bytes=131072, reserved_final_bytes=16384,
                  max_stdin_messages=50, max_stdout_messages=50, max_stderr_records=64,
                  max_stdin_message_bytes=4096, max_stdout_message_bytes=8192)
    values.update(changes)
    return worker.WorkerLimits(**values)


class WorkerSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="new-worker-中文 space-")
        self.root = Path(self.temp.name).resolve()
        info = self.root.stat()
        self._root_identity = (info.st_dev, info.st_ino)
        self._fixture_resources_settled = False
        self.addCleanup(self.cleanup_temporary)
        self.fixtures = worker.create_output_parent(self.root / "fixture")
        self.outputs = worker.create_output_parent(self.root / "outputs")
        self.interpreter = Path(sys.executable).resolve(strict=True)
        self.python_hash = sha256(self.interpreter.read_bytes()).hexdigest()
        self.count = 0
        self.handles = []
        self.addCleanup(self.close_handles)

    def close_handles(self):
        # This is test-resource cleanup, after the production receipt/budgets.
        # A timed-out receipt is never changed into a successful business result.
        deadline = time.monotonic() + 3
        for handle in self.handles:
            original = handle.finish(0)
            receipt = handle.run_dir / "result.json"
            original_bytes = receipt.read_bytes() if receipt.is_file() else None
            handle.close()
            launcher = next(thread for thread in handle._threads if thread.name == "worker-launch")
            launcher.join(timeout=max(0, deadline - time.monotonic()))
            self.assertFalse(launcher.is_alive(), "retain fixture: owned launcher is not settled")
            # Popen can become available while joining the launcher. Read its
            # exact owned handle again; never search or kill an unrelated PID.
            process = handle._process
            if process is not None and process.poll() is None:
                # Only our own synthetic child. Never enumerate or kill by PID.
                process.kill()
            if process is not None:
                process.wait(timeout=max(0, deadline - time.monotonic()))
                self.assertIsNotNone(process.poll())
            for thread in tuple(handle._threads):
                thread.join(timeout=max(0, deadline - time.monotonic()))
                self.assertFalse(thread.is_alive(), "retain fixture: owned thread is not settled")
            self.assertIs(handle._process, process)
            if process is not None:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe is not None:
                        pipe.close()
            for stream in handle._streams.values():
                stream.close()
            if original is not None:
                self.assertEqual(handle.finish(0), original)
            if original_bytes is not None:
                self.assertEqual(receipt.read_bytes(), original_bytes)
        self._fixture_resources_settled = True

    def cleanup_temporary(self):
        if not self._fixture_resources_settled:
            self.temp._finalizer.detach()  # Retain only this new fixture for diagnosis.
            self.fail("retain fixture: owned process/thread cleanup was not confirmed")
        deadline = time.monotonic() + 2
        while True:
            self.assertEqual(worker._plain_path(Path(self.temp.name), exists=False), self.root)
            if self.root.exists():
                info = self.root.stat()
                self.assertEqual((info.st_dev, info.st_ino), self._root_identity)
            try:
                self.temp.cleanup()
                return
            except PermissionError as error:
                # Windows may briefly retain a directory handle after process
                # exit. Retry only this validated fresh TEMP and only WinError32.
                if getattr(error, "winerror", None) != 32 or time.monotonic() >= deadline:
                    raise
                time.sleep(min(0.02, max(0, deadline - time.monotonic())))

    def spec(self, body):
        self.count += 1
        entry = self.fixtures.path / ("child-" + str(self.count) + ".py")
        entry.write_text(COMMON + body + "\n", encoding="utf-8")
        return worker.make_test_spec(interpreter=self.interpreter, interpreter_sha256=self.python_hash,
            entrypoint=entry, entrypoint_sha256=sha256(entry.read_bytes()).hexdigest(), fixture_parent=self.fixtures)

    def launch(self, body, **changes):
        spec = self.spec(body)
        handle = worker.launch(spec, output_parent=self.outputs, run_dir=self.outputs.path / ("run-" + str(self.count)),
                               run_id="run-fixture-1", request_id="request-original-1", limits=limits(**changes))
        self.handles.append(handle)
        return handle

    def ready(self, handle):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            message = handle.poll_message(0.2)
            if message is not None:
                self.assertEqual(message["kind"], "READY")
                return message
            if handle.finish(0) is not None:
                self.fail(str(handle.finish(0)))
        self.fail("synthetic child did not become ready")

    def done(self, handle):
        result = handle.finish(handle.limits.wall_seconds + handle.limits.cleanup_seconds)
        self.assertIsNotNone(result)
        self.assertEqual(result["run_id"], "run-fixture-1")
        self.assertEqual(result["request_id"], "request-original-1")
        self.assertEqual(result["restart_count"], 0)
        self.assertFalse(result["automatic_retry"])
        self.assertEqual(result["economic_acceptance"], "NOT_INFERRED")
        self.assertFalse(any(result["permissions"].values()))
        self.assertEqual(result["scope"], "TEST_FIXTURE_ONLY")
        self.assertEqual(result["production_admission"], "UNAVAILABLE")
        self.assertLessEqual(sum(p.stat().st_size for p in handle.run_dir.glob("*") if p.is_file()),
                             handle.limits.max_evidence_bytes)
        return result

    def message(self, sequence=1, **changes):
        result = dict(schema_version=worker.SCHEMA, run_id="run-fixture-1", request_id="request-original-1",
                      sequence=sequence, kind="INPUT", payload={"fictional": True})
        result.update(changes)
        return result

    def test_normal_single_process_reply_result_and_real_isolation_flags(self):
        body = '''emit('READY',{'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,
 'no_bytecode':sys.dont_write_bytecode,'hostile_pythonpath':os.environ.get('PYTHONPATH'),
 'old_runtime':os.environ.get('HAKIMI_RUNTIME_DIR'),'label':'中文路径'})
original=json.loads(sys.stdin.buffer.readline())
assert original['request_id']==a.request_id
emit('EVIDENCE',{'received_sequence':original['sequence']})
emit('RESULT',{'fact':'protocol-only'})'''
        with patch.dict(os.environ, {"PYTHONPATH": "C:/untrusted-source", "HAKIMI_RUNTIME_DIR": "C:/old-runtime"}):
            handle = self.launch(body)
            ready = self.ready(handle)
            self.assertEqual(ready["payload"], {"isolated": 1, "no_site": 1, "no_bytecode": True,
                "hostile_pythonpath": None, "old_runtime": None, "label": "中文路径"})
            ack = handle.reply(self.message())
            self.assertEqual(ack["status"], "STDIN_WRITTEN_NOT_DISPATCH_ACK")
            result = self.done(handle)
        self.assertEqual(result["status"], "PROTOCOL_RESULT_RECEIVED")
        self.assertEqual(result["spawn_count"], 1)
        self.assertEqual(result["messages"], {"stdin": 1, "stdout": 3, "stderr": 0})
        reference = result["result_reference"]
        raw = (handle.run_dir / reference["file"]).read_bytes()[reference["offset"]:reference["offset"] + reference["bytes"]]
        self.assertEqual(sha256(raw).hexdigest(), reference["sha256"])
        self.assertTrue(result["streams_complete"])
        self.assertEqual(handle.close(), result)

    def test_stall_is_killed_by_wall_watchdog_without_any_parent_polling(self):
        handle = self.launch("emit('READY'); time.sleep(30)", wall_seconds=0.6)
        result = self.done(handle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("WALL_DEADLINE", result["reasons"])
        self.assertTrue(result["cleanup_confirmed"])
        self.assertIsNotNone(handle._process.poll())
        self.assertLess(result["elapsed_seconds"], 1.6)

    def test_stop_is_direct_while_parent_is_waiting_for_next_message(self):
        handle = self.launch("emit('READY'); time.sleep(30)")
        self.ready(handle)
        returned = []
        thread = threading.Thread(target=lambda: returned.append(handle.poll_message(1)))
        thread.start()
        started = time.monotonic(); handle.stop()
        self.assertLess(time.monotonic() - started, 0.1)
        result = self.done(handle); thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertIn("STOP_REQUESTED", result["reasons"])
        self.assertEqual(returned, [None])
        self.assertTrue(result["cleanup_confirmed"])

    def test_partial_json_exit_is_unknown_and_exit_zero_is_not_success(self):
        for body in ("emit('READY'); sys.stdout.buffer.write(b'{\"partial\":')",
                     "emit('READY')"):
            with self.subTest(body=body):
                result = self.done(self.launch(body))
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertEqual(result["exit_code"], 0)
                self.assertIn("RESULT_MISSING", result["reasons"])
                self.assertFalse(result["streams_complete"])

    def test_wrong_request_id_is_preserved_as_raw_rejection_not_adopted(self):
        handle = self.launch("emit('READY',request_id='wrong-original'); time.sleep(30)")
        result = self.done(handle)
        self.assertIn("message_identity_mismatch", result["reasons"])
        self.assertEqual(result["possible_dispatch_request_ids"], ["request-original-1"])
        self.assertIsNone(handle.poll_message(0))
        self.assertIn(b"wrong-original", (handle.run_dir / "stdout.bin").read_bytes())

    def test_duplicate_keys_wrong_sequence_and_message_after_result_are_rejected(self):
        cases = ["emit('READY',sequence=2)", "emit('READY'); emit('RESULT'); emit('EVIDENCE')",
                 "sys.stdout.buffer.write(b'{\"schema_version\":\"x\",\"schema_version\":\"y\"}\\n')"]
        for body in cases:
            with self.subTest(body=body):
                result = self.done(self.launch(body))
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertFalse(result["streams_complete"])

    def test_oversized_single_stdout_message_and_total_stdout_are_bounded(self):
        cases = [("emit('READY'); sys.stdout.buffer.write(b'x'*20000); time.sleep(30)",
                  {"max_stdout_bytes": 4096, "max_stdout_message_bytes": 512}),
                 ("emit('READY'); [emit('EVIDENCE',{'text':'x'*400}) for _ in range(50)]; time.sleep(30)",
                  {"max_stdout_bytes": 2048, "max_stdout_message_bytes": 1024})]
        for body, settings in cases:
            with self.subTest(settings=settings):
                handle = self.launch(body, **settings)
                result = self.done(handle)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertLessEqual(result["bytes_retained"]["stdout"], settings["max_stdout_bytes"])
                self.assertFalse(result["streams_complete"])
                self.assertLessEqual((handle.run_dir / "stdout.bin").stat().st_size, settings["max_stdout_bytes"])

    def test_stderr_flood_and_concurrent_stdout_cannot_block_watchdog(self):
        body = '''import threading
emit('READY')
def flood():
 while True: sys.stderr.buffer.write(b'fictional stderr'*1000)
threading.Thread(target=flood,daemon=True).start()
while True: emit('EVIDENCE',{'test':'only'})'''
        result = self.done(self.launch(body, max_stderr_bytes=512, max_stdout_messages=10))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertLessEqual(result["bytes_retained"]["stderr"], 512)
        self.assertTrue(result["cleanup_confirmed"])
        self.assertFalse(result["streams_complete"])

    def test_message_count_limit_and_json_depth_limit_are_not_truncated_success(self):
        handle = self.launch("emit('READY'); [emit('EVIDENCE') for _ in range(10)]", max_stdout_messages=3)
        result = self.done(handle)
        self.assertEqual(result["messages"]["stdout"], 3)
        self.assertIn("stdout_messages_exceeded", result["reasons"])
        deep = self.launch("x={};\nfor i in range(12): x={'next':x}\nemit('READY',x)")
        self.assertIn("json_structure_exceeded", self.done(deep)["reasons"])

    def test_result_then_stall_is_unknown_not_economic_completion(self):
        result = self.done(self.launch("emit('READY'); emit('RESULT',{'status':'ACK'}); time.sleep(30)", wall_seconds=0.6))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNotNone(result["result_reference"])
        self.assertIn("WALL_DEADLINE", result["reasons"])

    def test_lost_ack_keeps_original_id_and_does_not_restart_or_resend(self):
        handle = self.launch("emit('READY'); sys.stdin.buffer.readline(); emit('EVIDENCE',{'may_have_dispatched':True}); time.sleep(30)", wall_seconds=0.8)
        self.ready(handle); handle.reply(self.message())
        result = self.done(handle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["spawn_count"], 1)
        self.assertEqual(result["messages"]["stdin"], 1)
        self.assertEqual(result["possible_dispatch_request_ids"], ["request-original-1"])
        self.assertEqual((handle.run_dir / "stdin.bin").read_bytes().count(b"\n"), 1)

    def test_reply_wrong_id_and_oversized_input_never_write_to_child(self):
        for message in (self.message(request_id="changed"), self.message(payload={"big": "x" * 5000})):
            handle = self.launch("emit('READY'); time.sleep(30)")
            self.ready(handle)
            with self.assertRaises(worker.SupervisorError):
                handle.reply(message)
            handle.stop(); result = self.done(handle)
            self.assertEqual(result["stdin_bytes_written"], 0)
            self.assertEqual(result["stdin_possible_bytes_written"], 0)

    def test_input_total_budget_refuses_before_another_full_message_write(self):
        handle = self.launch("emit('READY');\nfor line in sys.stdin.buffer: emit('EVIDENCE')",
                             max_stdin_bytes=512, max_stdin_message_bytes=512)
        self.ready(handle)
        for sequence in range(1, 10):
            try:
                handle.reply(self.message(sequence))
            except worker.SupervisorError:
                break
        result = self.done(handle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertLessEqual(result["stdin_bytes_written"], 512)
        self.assertLessEqual(result["bytes_retained"]["stdin"], 512)
        self.assertFalse(result["streams_complete"])

    def test_cleanup_timeout_is_unknown_not_a_false_clean_exit(self):
        handle = self.launch("emit('READY'); time.sleep(30)", stop_seconds=0.1, cleanup_seconds=0.25)
        self.ready(handle)
        process = handle._process
        real_kill, real_poll = process.kill, process.poll
        try:
            process.kill = lambda: (_ for _ in ()).throw(OSError("synthetic kill failure"))
            process.poll = lambda: None
            started = time.monotonic(); handle.stop(); result = self.done(handle)
            self.assertLess(time.monotonic() - started, 0.8)
            self.assertFalse(result["cleanup_confirmed"])
            self.assertIn("CLEANUP_TIMEOUT", result["reasons"])
            self.assertEqual(result["status"], "UNKNOWN")
        finally:
            process.kill, process.poll = real_kill, real_poll
            if process.poll() is None:
                real_kill(); process.wait(timeout=2)

    def test_stop_during_blocked_stdin_writer_does_not_hold_watchdog_or_control(self):
        handle = self.launch("emit('READY'); time.sleep(30)", stop_seconds=0.1, cleanup_seconds=0.3,
                             reply_seconds=0.2)
        self.ready(handle)
        entered, release = threading.Event(), threading.Event()
        real_write = os.write
        descriptor = handle._process.stdin.fileno()
        def blocking(fd, data):
            if fd == descriptor:
                entered.set()
                self.assertTrue(release.wait(2))
            return real_write(fd, data)
        replies = []
        with patch.object(worker.os, "write", blocking):
            thread = threading.Thread(target=lambda: replies.append(handle.reply(self.message())))
            thread.start()
            try:
                self.assertTrue(entered.wait(1))
                started = time.monotonic(); handle.stop()
                self.assertLess(time.monotonic() - started, 0.1)
                result = self.done(handle)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertIsNotNone(handle._process.poll())
                self.assertFalse(result["cleanup_confirmed"])
                self.assertEqual(result["stdin_bytes_written"], 0)
                self.assertGreater(result["stdin_possible_bytes_written"], 0)
                self.assertEqual(result["possible_dispatch_request_ids"], ["request-original-1"])
            finally:
                release.set(); thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(replies[0]["status"], "UNKNOWN")
        for owned in handle._threads:
            owned.join(timeout=1)
        handle.close()
        self.assertTrue(handle._process.stdin.closed)
        self.assertTrue(all(stream.closed for stream in handle._streams.values()))
        self.assertEqual(handle.finish(0), result)

    def test_late_process_creation_after_timeout_is_killed_without_restart(self):
        entered, release = threading.Event(), threading.Event()
        original = worker.subprocess.Popen
        def delayed(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(2))
            return original(*args, **kwargs)
        with patch.object(worker.subprocess, "Popen", delayed):
            handle = self.launch("emit('READY'); time.sleep(30)", wall_seconds=0.3,
                                 stop_seconds=0.1, cleanup_seconds=0.3)
            try:
                self.assertTrue(entered.wait(1))
                result = handle.finish(0.6)
                if result is None:
                    result = handle.finish(0.2)
                self.assertIsNotNone(result)
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertTrue(result["launch_outcome_unconfirmed"])
                self.assertFalse(result["cleanup_confirmed"])
                self.assertEqual(result["possible_dispatch_request_ids"], ["request-original-1"])
            finally:
                release.set()
                self.assertTrue(handle._launcher_done.wait(2))
        self.assertEqual(handle._spawn_count, 1)
        self.assertIsNotNone(handle._process.poll())
        self.assertEqual(handle.finish(0), result)  # Original UNKNOWN is not repaired.

    def test_fixture_waits_for_late_owned_handle_and_directory_release_without_rewriting_unknown(self):
        entered, release, joined = threading.Event(), threading.Event(), threading.Event()
        original_popen = worker.subprocess.Popen
        def delayed(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(2))
            return original_popen(*args, **kwargs)
        with patch.object(worker.subprocess, "Popen", delayed):
            handle = self.launch("emit('READY'); time.sleep(30)", wall_seconds=0.3,
                                 stop_seconds=0.1, cleanup_seconds=0.3)
            self.assertTrue(entered.wait(1))
            result = handle.finish(0.6) or handle.finish(0.2)
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertFalse(result["cleanup_confirmed"])
            self.assertIsNone(handle._process)
            receipt_bytes = (handle.run_dir / "result.json").read_bytes()
            launcher = next(thread for thread in handle._threads if thread.name == "worker-launch")
            original_join = launcher.join
            def observed_join(timeout=None):
                joined.set()
                return original_join(timeout)
            releaser = threading.Thread(target=lambda: (joined.wait(1), release.set()))
            releaser.start()
            try:
                with patch.object(launcher, "join", observed_join):
                    self.close_handles()
            finally:
                release.set(); releaser.join(2)
            self.assertTrue(joined.is_set())
            self.assertFalse(releaser.is_alive())
        self.assertIsNotNone(handle._process.poll())
        self.assertEqual(handle._spawn_count, 1)
        self.assertFalse(any(thread.is_alive() for thread in handle._threads))
        self.assertEqual(handle.finish(0), result)
        self.assertEqual((handle.run_dir / "result.json").read_bytes(), receipt_bytes)
        original_cleanup = self.temp.cleanup
        attempts = []
        def transient_directory_handle():
            attempts.append(True)
            self.assertEqual(handle.finish(0), result)
            self.assertEqual((handle.run_dir / "result.json").read_bytes(), receipt_bytes)
            if len(attempts) == 1:
                error = PermissionError("synthetic owned directory handle still closing")
                error.winerror = 32
                raise error
            original_cleanup()
        with patch.object(self.temp, "cleanup", transient_directory_handle):
            self.cleanup_temporary()
        self.assertEqual(len(attempts), 2)
        self.assertFalse(self.root.exists())
        self.assertEqual(handle.finish(0), result)

    def test_fragmented_utf8_message_and_plain_stderr_preserve_complete_bytes(self):
        body = '''emit('READY')
value={'schema_version':'hakimi-broker-worker-message-v1','run_id':a.run_id,
'request_id':a.request_id,'sequence':2,'kind':'RESULT','payload':{'text':'中文完整'}}
raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()+b'\\n'
for byte in raw: os.write(sys.stdout.fileno(),bytes([byte]))
sys.stderr.buffer.write(b'fictional diagnostic only\\n')'''
        handle = self.launch(body)
        self.ready(handle)
        result = self.done(handle)
        message = handle.poll_message(0)
        self.assertEqual(message["payload"], {"text": "中文完整"})
        self.assertEqual(result["status"], "PROTOCOL_RESULT_RECEIVED")
        self.assertEqual((handle.run_dir / "stderr.bin").read_bytes(), b"fictional diagnostic only\n")
        self.assertTrue(result["streams_complete"])

    def test_hash_drift_and_existing_run_dir_are_rejected_without_launch(self):
        spec = self.spec("emit('READY'); emit('RESULT')")
        spec.entrypoint.write_text("raise RuntimeError('changed fixture')", encoding="utf-8")
        run = self.outputs.path / "must-not-exist"
        with self.assertRaisesRegex(worker.SupervisorError, "identity_changed"):
            worker.launch(spec, output_parent=self.outputs, run_dir=run, run_id="r", request_id="q", limits=limits())
        self.assertFalse(run.exists())
        fresh = self.spec("emit('READY'); emit('RESULT')")
        run.mkdir()
        with self.assertRaisesRegex(worker.SupervisorError, "fresh_direct_child"):
            worker.launch(fresh, output_parent=self.outputs, run_dir=run, run_id="r", request_id="q", limits=limits())

    def test_parent_binding_escape_and_replaced_parent_are_rejected(self):
        spec = self.spec("emit('READY'); emit('RESULT')")
        for target in (self.root / "escape", self.outputs.path / ".." / "escape"):
            with self.subTest(target=target), self.assertRaises(worker.SupervisorError):
                worker.launch(spec, output_parent=self.outputs, run_dir=target, run_id="r", request_id="q", limits=limits())
        self.outputs.path.rename(self.root / "original-outputs")
        self.outputs.path.mkdir()
        with self.assertRaisesRegex(worker.SupervisorError, "identity_changed"):
            worker.launch(spec, output_parent=self.outputs, run_dir=self.outputs.path / "run", run_id="r", request_id="q", limits=limits())

    def test_reparse_ancestor_is_refused_without_following_it(self):
        original = Path.lstat
        target = self.outputs.path
        def information(path):
            info = original(path)
            if path == target:
                class Reparse:
                    st_mode = info.st_mode
                    st_file_attributes = 0x400
                return Reparse()
            return info
        with patch.object(Path, "lstat", information), self.assertRaisesRegex(worker.SupervisorError, "reparse"):
            worker._parent(self.outputs)

    def test_package_spec_binding_cannot_be_promoted_to_production_launch(self):
        package = self.fixtures.path / "package"
        (package / "runtime/python").mkdir(parents=True)
        executable = package / "runtime/python/python.exe"
        executable.write_bytes(self.interpreter.read_bytes())
        child = package / "child.py"; child.write_text("raise RuntimeError('must never launch')", encoding="utf-8")
        manifest = package / "terminal-manifest.json"
        manifest.write_text(json.dumps({"files": {"runtime/python/python.exe": sha256(executable.read_bytes()).hexdigest(),
                                                  "child.py": sha256(child.read_bytes()).hexdigest()}}), encoding="utf-8")
        spec = worker.bind_package_spec(package_root=package, manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
                                         interpreter_relative="runtime/python/python.exe", entrypoint_relative="child.py")
        with self.assertRaisesRegex(worker.ProductionAdmissionUnavailable, "PRODUCTION_ADMISSION_UNAVAILABLE"):
            worker.launch(spec, output_parent=self.outputs, run_dir=self.outputs.path / "unavailable",
                          run_id="r", request_id="q", limits=limits())
        self.assertEqual(list(self.outputs.path.iterdir()), [])

    def test_bound_limits_reject_bool_nonfinite_and_unbounded_poll(self):
        for changes in ({"wall_seconds": True}, {"wall_seconds": float("inf")}, {"wall_seconds": 181},
                        {"max_stdout_bytes": 100000}, {"reserved_final_bytes": 1}):
            with self.subTest(changes=changes), self.assertRaises(worker.SupervisorError):
                limits(**changes)
        handle = self.launch("emit('READY'); emit('RESULT')")
        with self.assertRaisesRegex(worker.SupervisorError, "poll_timeout_invalid"):
            handle.poll_message(2)
        self.done(handle)


if __name__ == "__main__":
    unittest.main()
