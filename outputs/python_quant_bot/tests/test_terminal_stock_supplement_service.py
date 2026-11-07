"""Fresh fictional collector bytes and real policy/store; no SDK or provider."""
import base64
from contextlib import closing
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from exchange_terminal.services import terminal_stock_supplement_service as service
from hakimi_research import daily_updates, stock_intake, stock_intake_futu_supplement as policy
from hakimi_research.documents import canonical_bytes, digest, parse_document


def fixture_module(name):
    path = Path(__file__).parents[3] / "tests" / (name + ".py")
    spec = importlib.util.spec_from_file_location("supplement_fixture_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()} if root.exists() else {}


class TerminalStockSupplementServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices_fixture = fixture_module("test_daily_updates")
        cls.collector_fixture = fixture_module("test_futu_rehab_evidence")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fresh-supplement-service-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.now = daily_updates._clock("2026-10-23T21:00:00Z")
        _, _, _, first, last = stock_intake._coverage(self.now, 20, "XNAS")
        value = self.prices_fixture.source_reply((date.fromisoformat(first) - timedelta(days=120)).isoformat(), last)
        value["chart"]["result"][0]["meta"].update(dataGranularity="1d", longName="FICTIONAL SERVICE TEST")
        value["chart"]["result"][0].pop("events")
        raw = self.prices_fixture.encoded(value)
        self.daily = TerminalDailyResearch(self.workspace, fetcher=lambda _: raw, clock=lambda: self.now)
        self.original = self.daily.mutate("terminal_daily_check_stock",
            dict(operation_id="original-fixture", symbol="TEST", history_sessions=20))
        self.assertEqual(self.original["reason"], "SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN")
        self.original_path = self.daily._lookup("intakes", self.original["id"])
        self.original_hashes = hashes(self.original_path)
        self.now = daily_updates._clock("2026-10-24T11:00:00Z")
        self.artifacts = self.collector_fixture.fixture()
        for index, key in enumerate(service.KEYS):
            doc = json.loads(self.artifacts[key])
            at = f"2026-10-24T10:00:0{index}Z"
            if key.endswith("request"):
                doc["started_at"] = at
                kwargs = doc["request"]["kwargs"]
                kwargs["code_list" if key == "security_request" else "code"] = ["US.TEST"] if key == "security_request" else "US.TEST"
            else:
                doc["completed_at"] = at
                if key == "security_response":
                    for rows in (doc["returned_reply"]["rows"], doc["sdk_decoded_protocol_reply"][2]):
                        rows[0]["code"] = "US.TEST"
                        rows[0]["name"] = "虚构测试资料"
            self.artifacts[key] = self.collector_fixture.encoded(doc)
        self.adapter = self.daily._supplements()
        for target in ("socket.socket.connect", "hakimi_research.daily_updates._fetch",
                       "hakimi_research.workbench_service.run_task"):
            blocker = patch(target, side_effect=AssertionError("No external or economic operation"))
            blocker.start(); self.addCleanup(blocker.stop)

    def check_payload(self, operation_id="check-operation"):
        return dict(operation_id=operation_id, intake_id=self.original["id"],
            expected_check_hash=self.original["check_hash"], source_format=service.FORMAT,
            artifacts={key: base64.b64encode(raw).decode("ascii") for key, raw in self.artifacts.items()})

    def save_payload(self, reviewed, operation_id="save-operation"):
        return dict(operation_id=operation_id, supplement_id=reviewed["id"],
            expected_check_hash=reviewed["check_hash"], confirmed_security=deepcopy(reviewed["security"]),
            acknowledge_source_limits=True)

    def check(self, payload=None):
        return self.daily.mutate("terminal_daily_check_supplement", payload or self.check_payload())

    def save(self, reviewed, payload=None):
        return self.daily.mutate("terminal_daily_save_supplement", payload or self.save_payload(reviewed))

    def receipt(self, identity):
        return self.daily.read("terminal_daily_supplement_requests", identity)

    def test_fresh_reads_create_no_store_and_context_does_not_evaluate(self):
        empty_path = self.root / "not-created-workspace"
        empty = TerminalDailyResearch(empty_path)
        self.assertEqual(empty.read("terminal_daily_supplements")["items"], [])
        self.assertEqual(empty.read("terminal_daily_supplement_requests", "empty-operation")["status"], "NOT_RECORDED")
        self.assertFalse(empty_path.exists())
        before = hashes(self.workspace)
        with patch.object(policy, "review_futu_supplement", side_effect=AssertionError("GET cannot review")):
            context = self.daily.read("terminal_daily_supplement_context", self.original["id"])
            self.assertEqual(context["original_check_hash"], self.original["check_hash"])
            self.assertEqual(context["supported_formats"][0]["id"], service.FORMAT)
            self.assertEqual(context["supported_formats"][0]["required_artifacts"][0]["filename"], "01-security.started.private.json")
            self.assertEqual(context["limits"], dict(file_bytes=1048576, total_bytes=4194304))
            self.assertEqual(self.daily.read("terminal_daily_supplements")["items"], [])
            missing = self.receipt("not-recorded-operation")
            self.assertEqual((missing["status"], missing["action"], missing["request_hash"], missing["result"]),
                             ("NOT_RECORDED", None, None, None))
        self.assertEqual(hashes(self.workspace), before)
        self.assertFalse(self.adapter.root.exists())

    def test_explicit_real_policy_save_is_native_canonical_and_preserves_all_originals(self):
        review = self.check()
        self.assertEqual((review["status"], review["can_save"]), ("REVIEW_REQUIRED", True))
        self.assertNotIn("raw_base64", json.dumps(review))
        self.assertEqual(list((self.daily.root / "data").rglob("*.json")), [])
        result = self.save(review)
        self.assertEqual(result["reason"], "SUPPLEMENT_INPUT_SAVED_NO_TASK_OR_RUN")
        self.assertEqual(result["saved_input_view_scope"], "SAVED_COMPLETION_RECEIPT_NOT_CURRENT_REVALIDATION")
        self.assertFalse(result["can_save"])
        saved = result["saved_input"]
        self.assertEqual(saved["record_namespace"], "canonical-daily-v1")
        self.assertEqual(saved["status"], "READY")
        raw, snapshot = self.daily.verified_input(saved["id"])
        self.assertEqual(parse_document(raw), snapshot)
        proof = json.loads(base64.b64decode(snapshot["corporate_actions"]["source"]["raw_base64"]))
        for name in service.ORIGINALS:
            self.assertEqual(base64.b64decode(proof["retained_originals"][name]["raw_base64"]), (self.original_path / name).read_bytes())
        for name, original in self.artifacts.items():
            self.assertEqual(base64.b64decode(proof["reader_diagnostic"]["retained_artifacts"][name]["raw_base64"]), original)
        restarted = TerminalDailyResearch(self.workspace)
        read = restarted.read("terminal_daily_inputs", saved["id"])
        self.assertEqual(read["supplement_lineage"]["supplement_id"], review["id"])
        self.assertEqual(restarted.read("terminal_daily_inputs")["items"][0], read)
        self.assertEqual(hashes(self.original_path), self.original_hashes)
        self.assertEqual(self.daily.read("terminal_daily_intakes", self.original["id"])["status"], "BLOCKED")
        for name in ("tasks", "runs"):
            self.assertEqual(list((self.daily.root / name).rglob("*.json")), [])

    def test_all_gets_are_byte_read_only_and_never_recheck_or_retain(self):
        reviewed = self.check(); saved = self.save(reviewed)
        before = hashes(self.workspace)
        with patch.object(policy, "review_futu_supplement", side_effect=AssertionError("No GET review")), \
             patch.object(policy, "build_futu_supplement", side_effect=AssertionError("No GET build")), \
             patch("hakimi_research.input_workflow._retain", side_effect=AssertionError("No GET retain")):
            self.daily.read("terminal_daily_supplement_context", self.original["id"])
            self.daily.read("terminal_daily_supplements")
            self.assertEqual(self.daily.read("terminal_daily_supplements", reviewed["id"]), saved)
            self.assertEqual(self.receipt("save-operation")["result"], saved)
            self.daily.read("terminal_daily_inputs", saved["saved_input_id"])
        self.assertEqual(hashes(self.workspace), before)

    def test_supplement_store_faults_preserve_verified_input_and_surface_unknown(self):
        reviewed = self.check(); saved = self.save(reviewed)
        identity = saved["saved_input_id"]
        verified_before = self.daily.verified_input(identity)
        store_bytes = self.adapter.path.read_bytes()
        sidecar = Path(str(self.adapter.path) + "-journal")
        for fault in ("journal", "foreign_schema", "malformed_sqlite_page"):
            with self.subTest(fault=fault):
                self.adapter.path.write_bytes(store_bytes)
                if fault == "journal":
                    sidecar.write_bytes(b"preserve an interrupted supplementary store")
                elif fault == "foreign_schema":
                    with closing(sqlite3.connect(self.adapter.path)) as connection:
                        connection.execute("CREATE TABLE foreign_data(value TEXT)")
                        connection.commit()
                else:
                    corrupted = bytearray(store_bytes)
                    corrupted[100] = 255  # Invalid first b-tree page, valid SQLite header.
                    self.adapter.path.write_bytes(corrupted)
                before = hashes(self.workspace)
                restarted = TerminalDailyResearch(self.workspace)
                with patch.object(policy, "review_futu_supplement", side_effect=AssertionError("No auxiliary retry")), \
                     patch.object(policy, "build_futu_supplement", side_effect=AssertionError("No auxiliary rebuild")), \
                     patch("hakimi_research.input_workflow._retain", side_effect=AssertionError("No auxiliary write")):
                    detail = restarted.read("terminal_daily_inputs", identity)
                    listed = restarted.read("terminal_daily_inputs")
                    self.assertEqual(listed["items"], [detail])
                    self.assertEqual(detail["status"], "READY")
                    self.assertEqual(detail["supplement_lineage_status"], "UNKNOWN")
                    self.assertNotIn("supplement_lineage", detail)
                    diagnostic = detail["supplement_lineage_diagnostic"]
                    self.assertFalse(diagnostic["source_truth_verified"])
                    self.assertFalse(diagnostic["automatic_retry"])
                    self.assertTrue(diagnostic["detail"])
                    self.assertIn(diagnostic["summary"], detail["limitations"])
                    self.assertIn(diagnostic["summary"], detail["warnings"])
                    self.assertIn(diagnostic["summary"], listed["warnings"][0])
                    self.assertEqual(detail["permissions"], service.PERMISSIONS)
                    self.assertEqual(restarted.verified_input(identity), verified_before)
                    with self.assertRaises((ValueError, sqlite3.Error)):
                        restarted.read("terminal_daily_supplements", reviewed["id"])
                    with self.assertRaises((ValueError, sqlite3.Error)):
                        restarted.mutate("terminal_daily_check_supplement", self.check_payload("check-after-store-fault"))
                    with self.assertRaises((ValueError, sqlite3.Error)):
                        restarted.mutate("terminal_daily_save_supplement", self.save_payload(reviewed))
                self.assertEqual(hashes(self.workspace), before)
                self.assertEqual(hashes(self.original_path), self.original_hashes)
                sidecar.unlink(missing_ok=True)
        self.adapter.path.write_bytes(store_bytes)
        self.assertEqual(self.daily.read("terminal_daily_inputs", identity)["supplement_lineage"],
                         saved["saved_input"]["supplement_lineage"])

    def test_lineage_fallback_never_hides_invalid_canonical_input(self):
        saved = self.save(self.check())
        identity = saved["saved_input_id"]
        self.daily._lookup("inputs", identity).write_bytes(b"{}")
        Path(str(self.adapter.path) + "-journal").write_bytes(b"preserve unknown supplementary state")
        before = hashes(self.workspace)
        listed = self.daily.read("terminal_daily_inputs")
        self.assertEqual(listed["items"], [])
        self.assertIn("unsupported_input_schema", listed["warnings"][0])
        with self.assertRaisesRegex(ValueError, "unsupported_input_schema"):
            self.daily.read("terminal_daily_inputs", identity)
        with self.assertRaises(ValueError):
            self.daily.verified_input(identity)
        self.assertEqual(hashes(self.workspace), before)
        self.assertEqual(hashes(self.original_path), self.original_hashes)

    def test_request_hash_replay_and_payload_collision_use_full_ascii_contract(self):
        payload = self.check_payload(); result = self.check(payload)
        receipt = self.receipt(payload["operation_id"])
        self.assertEqual(receipt["request_hash"], digest(dict(action="terminal_daily_check_supplement", payload=payload)))
        before = hashes(self.workspace)
        with patch.object(policy, "review_futu_supplement", side_effect=AssertionError("Completed replay cannot calculate")):
            self.assertEqual(self.check(payload), result)
            changed = deepcopy(payload); changed["expected_check_hash"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "payload_conflict"):
                self.check(changed)
        self.assertEqual(hashes(self.workspace), before)

    def test_bad_fields_identity_format_and_bounds_do_not_create_store(self):
        cases = []
        for key, value in (("path", str(self.root)), ("clock", "2026-01-01"), ("reader", {}), ("COMPLETE", True)):
            payload = self.check_payload(); payload[key] = value; cases.append(payload)
        payload = self.check_payload(); payload["intake_id"] = "../old"; cases.append(payload)
        payload = self.check_payload(); payload["expected_check_hash"] = "0" * 64; cases.append(payload)
        payload = self.check_payload(); payload["source_format"] = "fake-complete"; cases.append(payload)
        payload = self.check_payload(); payload["artifacts"]["actions_response"] = "!invalid"; cases.append(payload)
        payload = self.check_payload(); payload["artifacts"]["actions_response"] = base64.b64encode(b"x" * (service.FILE_BYTES + 1)).decode(); cases.append(payload)
        for payload in cases:
            with self.subTest(keys=list(payload)):
                with self.assertRaises(ValueError): self.check(payload)
        self.assertFalse(self.adapter.root.exists())
        self.assertEqual(hashes(self.original_path), self.original_hashes)

    def test_real_reader_blocks_missing_sdk_reply_and_wrong_security_save(self):
        bad = json.loads(self.artifacts["actions_response"]); bad.pop("sdk_decoded_protocol_reply")
        self.artifacts["actions_response"] = self.collector_fixture.encoded(bad)
        review = self.check()
        self.assertFalse(review["can_save"])
        with self.assertRaises(ValueError): self.save(review)
        self.assertEqual(list((self.daily.root / "data").rglob("*.json")), [])

    def test_security_confirmation_and_original_mutation_reject_before_save_claim(self):
        review = self.check()
        payload = self.save_payload(review); payload["confirmed_security"]["symbol"] = "OTHER"
        with self.assertRaises(ValueError): self.save(review, payload)
        payload = self.save_payload(review); payload["acknowledge_source_limits"] = False
        with self.assertRaises(ValueError): self.save(review, payload)
        path = self.original_path / "source-original.bin"; path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "original_artifact_changed"): self.save(review)
        self.assertEqual(self.receipt("save-operation")["status"], "NOT_RECORDED")
        self.assertEqual(list((self.daily.root / "data").rglob("*.json")), [])

    def test_failed_retain_is_pending_and_never_retried_by_read_or_another_instance(self):
        review = self.check()
        with patch("hakimi_research.input_workflow._retain", side_effect=OSError("fixture disk failure")) as retain:
            with self.assertRaisesRegex(OSError, "fixture disk"): self.save(review)
            before = hashes(self.workspace)
            self.assertEqual(self.receipt("save-operation")["status"], "PENDING")
            self.assertIsNone(self.receipt("save-operation")["result"])
            self.assertEqual(self.daily.read("terminal_daily_supplements", review["id"])["status"], "UNKNOWN")
            other = TerminalDailyResearch(self.workspace)
            with self.assertRaisesRegex(ValueError, "pending_query_only"):
                other.mutate("terminal_daily_save_supplement", self.save_payload(review))
            with self.assertRaisesRegex(ValueError, "already_claimed"):
                other.mutate("terminal_daily_save_supplement", self.save_payload(review, "different-save-operation"))
            self.assertEqual(retain.call_count, 1)
            self.assertEqual(hashes(self.workspace), before)

    def test_write_succeeded_but_receipt_unknown_remains_pending_and_input_not_resaved(self):
        review = self.check()
        original_view = self.daily._view
        def fail_view(kind, path):
            if kind == "inputs": raise OSError("lost completion after immutable write")
            return original_view(kind, path)
        with patch.object(self.daily, "_view", side_effect=fail_view):
            with self.assertRaisesRegex(OSError, "lost completion"): self.save(review)
        files = list((self.daily.root / "data").rglob("*.json"))
        self.assertEqual(len(files), 1)
        self.daily.verified_input(self.daily._id(files[0]))
        before = hashes(self.workspace)
        self.assertEqual(self.receipt("save-operation")["status"], "PENDING")
        with patch("hakimi_research.input_workflow._retain", side_effect=AssertionError("No second write")):
            with self.assertRaisesRegex(ValueError, "pending_query_only"): self.save(review)
        self.assertEqual(hashes(self.workspace), before)

    def test_lost_sqlite_commit_reply_recovers_only_by_reading_original_completed_request(self):
        def lost(connection):
            connection.commit()
            raise OSError("commit reply lost")
        payload = self.check_payload()
        with patch.object(self.adapter, "_commit", side_effect=lost):
            with self.assertRaisesRegex(OSError, "commit reply lost"): self.check(payload)
        receipt = self.receipt(payload["operation_id"])
        self.assertEqual(receipt["status"], "COMPLETED")
        with patch.object(policy, "review_futu_supplement", side_effect=AssertionError("Never repeat original")):
            self.assertEqual(self.check(payload), receipt["result"])
        count = 0
        def lose_second(connection):
            nonlocal count
            count += 1; connection.commit()
            if count == 2: raise OSError("save completion reply lost")
        with patch.object(self.adapter, "_commit", side_effect=lose_second):
            with self.assertRaisesRegex(OSError, "save completion reply lost"): self.save(receipt["result"])
        saved = self.receipt("save-operation")
        self.assertEqual(saved["status"], "COMPLETED")
        with patch.object(policy, "build_futu_supplement", side_effect=AssertionError("Never rebuild original save")):
            self.assertEqual(self.save(receipt["result"]), saved["result"])
        self.assertEqual(len(list((self.daily.root / "data").rglob("*.json"))), 1)

    def test_foreign_workspace_schema_and_sqlite_sidecars_are_rejected_without_repair(self):
        self.check()
        foreign = TerminalDailyResearch(self.root / "foreign")._supplements()
        foreign.root.mkdir(parents=True)
        foreign.path.write_bytes(self.adapter.path.read_bytes())
        before = hashes(foreign.root)
        with self.assertRaisesRegex(ValueError, "workspace_or_schema_changed"): foreign.read("supplements")
        self.assertEqual(hashes(foreign.root), before)
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.adapter.path) + suffix); sidecar.write_bytes(b"preserve this unknown state")
            before = hashes(self.adapter.root)
            with self.assertRaisesRegex(ValueError, "pending_recovery_or_writer"): self.daily.read("terminal_daily_supplements")
            self.assertEqual(hashes(self.adapter.root), before)
            sidecar.unlink()
        with closing(sqlite3.connect(self.adapter.path)) as connection:
            connection.execute("CREATE TABLE foreign_data(value TEXT)")
            connection.commit()
        before = hashes(self.adapter.root)
        with self.assertRaisesRegex(ValueError, "foreign_schema"): self.daily.read("terminal_daily_supplements")
        self.assertEqual(hashes(self.adapter.root), before)

    def test_hardlinked_store_or_original_is_rejected(self):
        self.check()
        alias = self.root / "db-alias"; os.link(self.adapter.path, alias)
        with self.assertRaisesRegex(ValueError, "regular_bounded_store"): self.daily.read("terminal_daily_supplements")
        alias.unlink()
        alias = self.root / "original-alias"; os.link(self.original_path / "source-original.bin", alias)
        with self.assertRaisesRegex(ValueError, "original_regular"): self.daily.read("terminal_daily_supplement_context", self.original["id"])

    def test_wal_header_is_rejected_without_implicit_sqlite_recovery(self):
        self.check()
        raw = bytearray(self.adapter.path.read_bytes()); raw[18:20] = b"\2\2"
        self.adapter.path.write_bytes(raw)
        before = hashes(self.adapter.root)
        with self.assertRaisesRegex(ValueError, "delete_mode_required"):
            self.daily.read("terminal_daily_supplements")
        self.assertEqual(hashes(self.adapter.root), before)

    def test_shuffled_request_and_later_save_clock_preserve_review_identity(self):
        payload = self.check_payload()
        payload["artifacts"] = dict(reversed(list(payload["artifacts"].items())))
        review = self.check(payload)
        self.now += timedelta(days=10)
        saved = self.save(review)
        self.assertEqual(saved["check_hash"], review["check_hash"])
        _, snapshot = self.daily.verified_input(saved["saved_input_id"])
        proof = json.loads(base64.b64decode(snapshot["corporate_actions"]["source"]["raw_base64"]))
        self.assertEqual(proof["times"]["supplement_checked_at"], review["times"]["supplement_checked_at"])

    def test_existing_content_address_collision_is_not_overwritten(self):
        review = self.check()
        originals = {name: (self.original_path / name).read_bytes() for name in service.ORIGINALS}
        built = policy.build_futu_supplement(originals, self.artifacts,
            checked_at=review["times"]["supplement_checked_at"], expected_check_hash=review["check_hash"],
            confirmed_security=review["security"], acknowledge_source_limits=True)
        raw = canonical_bytes(built["snapshot"])
        target = self.daily.root / "data" / "snapshots" / built["snapshot"]["snapshot_id"] / (sha256(raw).hexdigest() + ".json")
        target.parent.mkdir(parents=True)
        target.write_bytes(b"preserve pre-existing conflicting fixture")
        before = hashes(self.workspace)
        with self.assertRaisesRegex(ValueError, "input_collision"): self.save(review)
        self.assertEqual(hashes(self.workspace), before)
        self.assertEqual(self.receipt("save-operation")["status"], "NOT_RECORDED")

    def test_two_processes_cannot_retain_the_same_review_twice(self):
        review = self.check()
        signal = self.root / "start"
        script = r'''
import json, pathlib, socket, sys, time
from exchange_terminal.services.terminal_daily_research import TerminalDailyResearch
from hakimi_research import input_workflow
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No network'))
workspace, payload, marker, signal = map(pathlib.Path, sys.argv[1:])
original=input_workflow._retain
def retain(root, raw):
    marker.write_text('one actual retain', encoding='utf-8')
    time.sleep(.15)
    return original(root, raw)
input_workflow._retain=retain
marker.with_suffix('.ready').write_text('ready')
deadline=time.monotonic()+15
while not signal.exists():
    if time.monotonic()>deadline: raise TimeoutError('fixture start timeout')
    time.sleep(.01)
try:
    value=TerminalDailyResearch(workspace).mutate('terminal_daily_save_supplement',json.loads(payload.read_text()))
    print(json.dumps({'status':'SAVED','input_id':value['saved_input_id']}))
except (ValueError, OSError, __import__('sqlite3').OperationalError) as exc:
    print(json.dumps({'status':'REJECTED','reason':str(exc)}))
'''
        processes = []
        try:
            for index in range(2):
                payload = self.root / f"payload-{index}.json"
                payload.write_text(json.dumps(self.save_payload(review, f"process-save-{index}")), encoding="utf-8")
                processes.append(subprocess.Popen([sys.executable, "-B", "-c", script, str(self.workspace),
                    str(payload), str(self.root / f"retained-{index}"), str(signal)],
                    cwd=Path(__file__).resolve().parents[1],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            deadline = time.monotonic() + 15
            while len(list(self.root.glob("retained-*.ready"))) < 2:
                for index, process in enumerate(processes):
                    if process.poll() is not None:
                        stdout, stderr = process.communicate(timeout=1)
                        self.fail(f"fixture process {index} exited before readiness "
                                  f"(code {process.returncode}): {stderr or stdout}")
                self.assertLess(time.monotonic(), deadline, "fixture processes did not become ready")
                time.sleep(.01)
            signal.write_text("go")
            values = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stderr)
                values.append(json.loads(stdout))
            self.assertEqual(sum(row["status"] == "SAVED" for row in values), 1, values)
            self.assertEqual(len([p for p in self.root.glob("retained-*") if p.suffix != ".ready"]), 1)
            self.assertEqual(len(list((self.daily.root / "data").rglob("*.json"))), 1)
            self.assertEqual(hashes(self.original_path), self.original_hashes)
        finally:
            for process in processes:
                if process.poll() is None: process.kill()
                process.communicate(timeout=10)
                if process.stdout: process.stdout.close()
                if process.stderr: process.stderr.close()


if __name__ == "__main__":
    unittest.main()
