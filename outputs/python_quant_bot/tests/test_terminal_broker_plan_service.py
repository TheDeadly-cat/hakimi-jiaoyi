"""New TEMP offline plan stores; no SDK, provider, GUI or research runner."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import terminal_broker_plan_service as module
from exchange_terminal.services import terminal_broker_candidate_service as candidate
from exchange_terminal.services.terminal_broker_package_loader import BrokerRuntimeLoad, PackageLoaderError
from tests import test_terminal_broker_execution_plan as fixture

SIM, REAL, NOW = fixture.SIM, fixture.REAL, fixture.NOW


class BrokerPlanServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="broker-plan-new-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "new-workspace"
        self.now = NOW
        for name in ("socket.socket.connect", "socket.socket.bind", "socket.getaddrinfo", "subprocess.Popen"):
            blocked = patch(name, side_effect=AssertionError("No external operation"))
            blocked.start(); self.addCleanup(blocked.stop)
        self.resolver = Mock(side_effect=lambda ref: deepcopy(fixture.RESOLUTION))
        self.loader = Mock(side_effect=lambda mode: BrokerRuntimeLoad("PACKAGED_IDENTITY_MATCHED", mode,
            module.contract.verify_runtime_identity(**fixture.runtime_inputs(mode=mode))))
        self.candidates = self.new_candidates()
        self.service = self.reopen()

    def new_candidates(self):
        return candidate.BrokerCandidateService(self.workspace / "broker-candidates-v2",
            research_resolver=self.resolver, clock=lambda: self.now)

    def reopen(self):
        service = module.BrokerPlanService(self.workspace, candidates=self.candidates,
            research_resolver=self.resolver, runtime_loader=self.loader, clock=lambda: self.now)
        self.addCleanup(service.close)
        return service

    def seed(self, mode=SIM, request_id="plan-synthetic-0001"):
        saved = self.candidates.save({"mode": mode, "request_id": "candidate-save-0001", "config": fixture.config(), "research_reference": fixture.REF})
        intent = self.candidates.prepare_intent({"mode": mode, "request_id": "candidate-intent-0001", "config_id": saved["config_id"]})["intent"]
        return {"mode": mode, "request_id": request_id, "config_id": saved["config_id"], "intent_id": intent["id"],
                "expected_control_revision": 0, "bounds": fixture.bounds()}

    def inventory(self, root=None):
        return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in (root or self.workspace).rglob("*") if p.is_file()}

    def test_lazy_reads_and_capabilities_create_zero_store_and_no_research(self):
        self.assertEqual(self.service.read("terminal_broker_plans", {"mode": SIM})["requests"], [])
        self.assertEqual(self.service.read("terminal_broker_plan_receipt", {"mode": SIM, "request_id": "unknown-request-0001"})["status"], "NOT_RECORDED")
        self.assertIsNone(self.service.read("terminal_broker_plan", {"mode": SIM, "plan_id": "a" * 64})["plan"])
        self.loader.side_effect = lambda mode: BrokerRuntimeLoad("NOT_PACKAGED", mode, None)
        cap = self.service.read("terminal_broker_plan_capabilities", {"mode": REAL})
        self.assertEqual(cap["status"], "NOT_PACKAGED")
        self.assertFalse(any(cap["permissions"].values()))
        self.resolver.assert_not_called()
        self.assertFalse(self.workspace.exists())

    def test_plan_and_receipt_commit_together_from_original_candidate_records(self):
        payload = self.seed()
        before = self.inventory(self.candidates.root)
        value = self.service.mutate(module.ACTION, payload)
        self.assertEqual(value["status"], "PLAN_SAVED")
        self.assertEqual(value["receipt"]["payload"], payload)
        self.assertEqual(value["claim"]["payload"], payload)
        self.assertEqual(value["result"]["config_id"], payload["config_id"])
        self.assertEqual(value["result"]["intent_id"], payload["intent_id"])
        self.assertEqual(value["result"]["plan_status"], "OFFLINE_ONLY_SYNTHETIC_RESEARCH")
        self.assertFalse(any(value["result"]["permissions"].values()))
        listing = self.service.read("terminal_broker_plans", {"mode": SIM})
        self.assertEqual(len(listing["items"]), 1); self.assertEqual(len(listing["requests"]), 1)
        self.assertEqual(listing["requests"][0]["state"], "COMPLETED")
        self.assertEqual(listing["items"][0]["symbol"], "TSLA")
        plan = self.service.read("terminal_broker_plan", {"mode": SIM, "plan_id": value["result"]["plan_id"]})["plan"]
        self.assertEqual(plan["candidate_intent"]["id"], payload["intent_id"])
        self.assertEqual(self.inventory(self.candidates.root), before)
        self.assertFalse(any(plan["permissions"].values()))

    def test_original_request_reads_and_replays_do_not_reload_research_package_or_expiry(self):
        payload = self.seed(); saved = self.service.prepare(payload)
        self.candidates.stop({"mode": SIM, "request_id": "stop-after-plan-0001", "reason": "pause new preparation"})
        self.now += timedelta(days=2)
        self.resolver.side_effect = AssertionError("Never resolve old operation")
        self.loader.side_effect = PackageLoaderError("PACKAGE_CHANGED", "synthetic changed package")
        reopened = self.reopen()
        before = self.inventory()
        self.assertEqual(reopened.prepare(payload)["receipt"], saved["receipt"])
        read = reopened.receipt(SIM, payload["request_id"])
        self.assertEqual(read["status"], "FOUND"); self.assertEqual(read["receipt"], saved["receipt"])
        self.assertEqual(len(reopened.plans(SIM)["items"]), 1)
        self.assertIsNotNone(reopened.read("terminal_broker_plan", {"mode": SIM, "plan_id": saved["result"]["plan_id"]})["plan"])
        self.assertEqual(self.inventory(), before)

    def test_exact_six_fields_and_changed_request_conflict_never_accept_client_authority(self):
        payload = self.seed()
        for name in ("runtime_identity", "manifest", "research", "permissions", "path", "owner_id", "source_hash"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "fields_invalid"):
                self.service.prepare({**payload, name: {"trusted": True}})
        self.assertFalse(self.service.root.exists())
        saved = self.service.prepare(payload); calls = self.loader.call_count
        changed = deepcopy(payload); changed["bounds"]["max_total_fees"] = "3"
        with self.assertRaisesRegex(ValueError, "request_payload_conflict"): self.service.prepare(changed)
        self.assertEqual(self.loader.call_count, calls)
        self.assertEqual(self.service.receipt(SIM, payload["request_id"])["receipt"], saved["receipt"])

    def test_not_packaged_and_package_changed_are_durable_refusals_without_fallback(self):
        payload = self.seed()
        self.loader.side_effect = lambda mode: BrokerRuntimeLoad("NOT_PACKAGED", mode, None)
        refused = self.service.prepare(payload)
        self.assertEqual(refused["status"], "PLAN_NOT_CREATED")
        self.assertEqual(refused["result"]["reason"], "NOT_PACKAGED")
        self.assertIsNone(refused["result"]["plan_id"])
        self.loader.side_effect = AssertionError("Old request cannot try a new package")
        self.assertEqual(self.reopen().prepare(payload)["receipt"], refused["receipt"])
        self.loader.side_effect = PackageLoaderError("PACKAGE_CHANGED", "new fixture bytes differ")
        second = self.service.prepare({**payload, "request_id": "plan-synthetic-0002"})
        self.assertEqual(second["result"]["reason"], "PACKAGE_CHANGED")
        self.assertEqual(self.service.plans(SIM)["items"], [])
        self.assertEqual([r["state"] for r in self.service.plans(SIM)["requests"]], ["REFUSED", "REFUSED"])

    def test_plain_runtime_dictionary_is_not_a_trusted_loader_result(self):
        payload = self.seed(); self.loader.side_effect = lambda mode: {"status": "PACKAGED_IDENTITY_MATCHED", "runtime_identity": {}}
        result = self.service.prepare(payload)
        self.assertEqual(result["status"], "PLAN_NOT_CREATED")
        self.assertEqual(result["result"]["reason"], "broker_plan_trusted_runtime_load_required")

    def test_cross_instance_same_id_has_one_durable_claim_and_one_preparation(self):
        payload = self.seed(); entered, release = threading.Event(), threading.Event()
        runtime = self.loader(SIM); self.loader.reset_mock()
        def blocked(mode):
            entered.set(); self.assertTrue(release.wait(5)); return runtime
        self.loader.side_effect = blocked
        second = self.reopen()
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(self.service.prepare, payload)
            self.assertTrue(entered.wait(3))
            try:
                duplicate = second.prepare(payload)
                self.assertEqual(duplicate["status"], "PREPARING_UNCONFIRMED")
                self.assertEqual(second.plans(SIM)["requests"][0]["state"], "PREPARING")
            finally: release.set()
            done = future.result(timeout=5)
        self.assertEqual(done["status"], "PLAN_SAVED")
        self.assertEqual(self.loader.call_count, 1)
        self.assertEqual(len(second.plans(SIM)["items"]), 1)
        self.assertEqual(second.prepare(payload)["receipt"], done["receipt"])

    def test_stop_and_resume_during_slow_loader_invalidate_old_preparation_revision(self):
        payload = self.seed(); entered, release = threading.Event(), threading.Event()
        runtime = self.loader(SIM)
        def blocked(mode):
            entered.set(); self.assertTrue(release.wait(5)); return runtime
        self.loader.side_effect = blocked
        other = self.new_candidates()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.service.prepare, payload)
            self.assertTrue(entered.wait(3))
            try:
                stopped = other.stop({"mode": SIM, "request_id": "plan-race-stop-0001", "reason": "explicit stop"})
                other.resume({"mode": SIM, "request_id": "plan-race-resume-0001", "reason": "only offline preparation",
                              "expected_stop_receipt_id": stopped["stop_receipt_id"]})
            finally: release.set()
            result = future.result(timeout=5)
        self.assertEqual(result["status"], "PLAN_NOT_CREATED")
        self.assertIn("control_changed", result["result"]["reason"])
        self.assertEqual(self.service.plans(SIM)["items"], [])
        self.assertEqual(other.read_plan_control(SIM)["control"]["revision"], 2)

    def test_plan_commit_linearizes_before_concurrent_stop_in_short_barrier(self):
        payload = self.seed(); entered, release, stopping = threading.Event(), threading.Event(), threading.Event()
        original = self.service._write_final
        def blocked(*args, **kwargs):
            entered.set(); self.assertTrue(release.wait(3)); return original(*args, **kwargs)
        def stop():
            stopping.set()
            return self.new_candidates().stop({"mode": SIM, "request_id": "commit-stop-0001", "reason": "stop after publication barrier"})
        with patch.object(self.service, "_write_final", side_effect=blocked), ThreadPoolExecutor(max_workers=2) as pool:
            prepare = pool.submit(self.service.prepare, payload)
            self.assertTrue(entered.wait(3)); stopped = pool.submit(stop); self.assertTrue(stopping.wait(2))
            try: self.assertFalse(stopped.done())
            finally: release.set()
            result, stop_receipt = prepare.result(timeout=4), stopped.result(timeout=4)
        self.assertEqual(result["status"], "PLAN_SAVED")
        self.assertEqual(stop_receipt["status"], "STOPPED")
        self.assertEqual(self.service.receipt(SIM, payload["request_id"])["receipt"], result["receipt"])
        self.assertEqual(self.candidates.read_plan_control(SIM)["control"]["revision"], 1)

    def test_interruption_and_write_rollback_keep_preparing_no_automatic_retry(self):
        payload = self.seed()
        self.loader.side_effect = KeyboardInterrupt("synthetic interruption before preparation")
        with self.assertRaises(KeyboardInterrupt): self.service.prepare(payload)
        reopened = self.reopen(); self.loader.side_effect = AssertionError("Never resume pending")
        self.assertEqual(reopened.prepare(payload)["status"], "PREPARING_UNCONFIRMED")
        self.assertFalse(reopened.receipt(SIM, payload["request_id"])["retry_allowed"])
        self.assertEqual(reopened.plans(SIM)["items"], [])

    def test_transaction_failure_rolls_back_both_plan_and_final_receipt(self):
        payload = self.seed()
        def half_write(connection, claim, receipt, plan=None):
            connection.execute("INSERT INTO plans VALUES(?,?)", (plan["id"], module._bytes(plan)))
            raise RuntimeError("synthetic interruption before receipt/commit")
        with patch.object(self.service, "_write_final", side_effect=half_write):
            result = self.service.prepare(payload)
        self.assertEqual(result["status"], "PREPARING_UNCONFIRMED")
        listing = self.reopen().plans(SIM)
        self.assertEqual(listing["items"], []); self.assertEqual(listing["requests"][0]["state"], "PREPARING")

    def test_lost_response_after_atomic_commit_reads_original_success_without_recomputation(self):
        payload = self.seed(); original = self.service._write_final
        def committed_then_lost(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("synthetic acknowledgement lost")
        with patch.object(self.service, "_write_final", side_effect=committed_then_lost):
            result = self.service.prepare(payload)
        self.assertEqual(result["status"], "PLAN_SAVED")
        self.loader.side_effect = AssertionError("No repeat load")
        self.assertEqual(self.reopen().prepare(payload)["receipt"], result["receipt"])
        self.assertEqual(len(self.service.plans(SIM)["items"]), 1)

    def test_expiry_is_rechecked_at_final_publication(self):
        payload = self.seed(); original = self.candidates.plan_commit_barrier
        @contextmanager
        def change_clock(*args):
            with original(*args) as control:
                self.now += timedelta(minutes=14)
                yield control
        with patch.object(self.candidates, "plan_commit_barrier", side_effect=change_clock):
            result = self.service.prepare(payload)
        self.assertEqual(result["status"], "PLAN_NOT_CREATED")
        self.assertIn("worker_budget_exceeds", result["result"]["reason"])
        self.assertEqual(self.service.plans(SIM)["items"], [])

    def test_modes_and_workspace_store_context_cannot_be_interchanged(self):
        first = self.service.prepare(self.seed(SIM))
        self.assertEqual(self.service.plans(REAL)["items"], [])
        second = self.service.prepare(self.seed(REAL))
        self.assertNotEqual(first["result"]["plan_id"], second["result"]["plan_id"])
        self.assertEqual(second["result"]["plan_status"], "OFFLINE_ONLY_SYNTHETIC_RESEARCH")
        self.assertFalse(any(second["permissions"].values()))
        with closing(sqlite3.connect(self.service._path(SIM))) as connection, connection:
            meta = self.service._meta(SIM); meta["workspace_context"] = "0" * 64
            connection.execute("UPDATE metadata SET body=?", (module._bytes(fixture.seal(meta)),))
        with self.assertRaisesRegex(ValueError, "store_context_changed"): self.service.plans(SIM)

    def test_resealed_receipt_permission_and_request_identity_drift_fail_closed(self):
        payload = self.seed(); result = self.service.prepare(payload)
        for change in (lambda r:r.update(request_id="OTHER-REQUEST-0001"),
                       lambda r:r["permissions"].update(submit_allowed=True),
                       lambda r:r["result"].update(intent_id="0" * 64)):
            altered = deepcopy(result["receipt"]); change(altered)
            with closing(sqlite3.connect(self.service._path(SIM))) as connection, connection:
                connection.execute("UPDATE requests SET receipt=? WHERE request_id=?", (module._bytes(fixture.seal(altered)), payload["request_id"]))
            with self.assertRaises(ValueError): self.service.receipt(SIM, payload["request_id"])
        with closing(sqlite3.connect(self.service._path(SIM))) as connection, connection:
            connection.execute("UPDATE requests SET receipt=? WHERE request_id=?", (module._bytes(result["receipt"]), payload["request_id"]))
        self.assertEqual(self.service.receipt(SIM, payload["request_id"])["receipt"], result["receipt"])

    def test_capacity_and_closed_service_do_not_start_more_preparation(self):
        payload = self.seed(); self.loader.side_effect = lambda mode: BrokerRuntimeLoad("NOT_PACKAGED", mode, None)
        with patch.object(module, "MAX_RECORDS", 2):
            self.service.prepare(payload); self.service.prepare({**payload, "request_id": "plan-capacity-0002"})
            calls = self.loader.call_count
            with self.assertRaisesRegex(ValueError, "capacity_exceeded"):
                self.service.prepare({**payload, "request_id": "plan-capacity-0003"})
            self.assertEqual(len(self.service.plans(SIM)["requests"]), 2)
            self.assertEqual(self.loader.call_count, calls)
        self.service.close()
        with self.assertRaisesRegex(ValueError, "service_closed"): self.service.plans(SIM)

    def test_workspace_scope_uses_physical_platform_case_semantics_and_rejects_copied_store(self):
        payload = self.seed(); self.service.prepare(payload)
        lower = Path(self.temp.name) / "case-scope"
        upper = Path(self.temp.name) / "CASE-SCOPE"
        lower.mkdir(); upper.mkdir(exist_ok=True)
        make = lambda path: module.BrokerPlanService(path, candidates=self.candidates, research_resolver=self.resolver, runtime_loader=self.loader)
        a, b = make(lower), make(upper)
        self.addCleanup(a.close); self.addCleanup(b.close)
        self.assertEqual(a.workspace_context == b.workspace_context,
                         os.path.normcase(str(lower.resolve())) == os.path.normcase(str(upper.resolve())))
        other = make(Path(self.temp.name) / "different-workspace")
        self.addCleanup(other.close)
        target = other._path(SIM); target.parent.mkdir(parents=True)
        shutil.copyfile(self.service._path(SIM), target)
        before = self.inventory(other.root)
        with self.assertRaisesRegex(ValueError, "store_context_changed"): other.plans(SIM)
        self.assertEqual(before, self.inventory(other.root))

    def test_closed_wal_store_is_rejected_before_sqlite_open_without_coordination_files(self):
        payload = self.seed(); self.service.prepare(payload)
        path = self.service._path(SIM)
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        self.assertFalse(Path(str(path) + "-wal").exists()); self.assertFalse(Path(str(path) + "-shm").exists())
        before = self.inventory(self.service.root)
        with patch.object(module.sqlite3, "connect", side_effect=AssertionError("WAL must be rejected before SQLite opens")):
            for callback in (lambda: self.service.plans(SIM), lambda: self.service.receipt(SIM, payload["request_id"])):
                with self.assertRaisesRegex(ValueError, "delete_journal_store_required"): callback()
        self.assertEqual(before, self.inventory(self.service.root))

    def test_hardlinked_store_is_rejected_before_sqlite_open(self):
        payload = self.seed(); self.service.prepare(payload)
        path = self.service._path(SIM); alias = path.with_name("alias.sqlite3")
        os.link(path, alias)
        before = self.inventory(self.service.root)
        with patch.object(module.sqlite3, "connect", side_effect=AssertionError("No aliased SQLite open")):
            with self.assertRaisesRegex(ValueError, "unaliased_regular_store_required"): self.service.plans(SIM)
        self.assertEqual(before, self.inventory(self.service.root))


if __name__ == "__main__":
    unittest.main()
