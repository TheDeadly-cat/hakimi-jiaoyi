"""Shared control on fresh synthetic TEMP roots; no broker or old store."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_account_control as control

SIM, REAL = "OFFICIAL_SIMULATION", "LIVE_CANDIDATE"


class AccountControlTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="new-account-controls-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.program = self.root / "program"
        self.program.mkdir()
        self.bound = control.bind_host_root(self.root / "shared", program_root=self.program,
                                            record_domain="SYNTHETIC_TEST")
        self.now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        self.store = self.account()
        for name in ("socket.socket.connect", "socket.socket.bind", "socket.getaddrinfo", "subprocess.Popen"):
            denied = patch(name, side_effect=AssertionError("No external operations in account controls"))
            denied.start(); self.addCleanup(denied.stop)

    def account(self, *, mode=SIM, account_id="900000000000001", bound=None):
        return control.AccountControl(bound or self.bound, mode=mode, account_id=account_id, clock=lambda: self.now)

    def stop(self, store=None, request="explicit-stop-0001"):
        return (store or self.store).stop({"request_id": request, "reason": "Explicit synthetic stop"})

    def resume(self, receipt, store=None, request="explicit-resume-0001"):
        return (store or self.store).resume({"request_id": request, "reason": "Explicit synthetic review",
                                            "expected_stop_receipt_id": receipt["id"]})

    def inventory(self):
        return {str(path.relative_to(self.root)): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in self.root.rglob("*") if path.is_file()}

    def test_binding_and_read_create_no_directory_or_authority(self):
        before = list(self.root.iterdir())
        first = self.store.read("unknown-request-0001")
        self.assertEqual(first["control"]["revision"], 0)
        self.assertFalse(first["control"]["dispatch_authorized"])
        self.assertFalse(any(first["permissions"].values()))
        self.assertIsNone(first["receipt"])
        self.assertEqual(list(self.root.iterdir()), before)
        self.assertFalse(self.bound.path.exists())

    def test_same_user_root_account_is_shared_and_other_modes_accounts_domains_are_separate(self):
        peer = self.account()
        stopped = self.stop()
        self.assertEqual(peer.read()["control"], stopped["control"])
        for other in (self.account(mode=REAL), self.account(account_id="900000000000002")):
            self.assertFalse(other.read()["control"]["stopped"])
            self.assertNotEqual(other.path, self.store.path)
        external = control.bind_host_root(self.root / "shared", program_root=self.program, record_domain="EXTERNAL_RECORD")
        self.assertFalse(self.account(bound=external).read()["control"]["stopped"])
        self.assertNotEqual(external.root_id, self.bound.root_id)

    def test_stop_resume_does_not_renew_old_revision_or_resend(self):
        with self.store.barrier(0) as before:
            self.assertFalse(before["control"]["dispatch_authorized"])
        stopped = self.stop()
        with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
            with self.account().barrier(0):
                self.fail("stopped account admitted")
        resumed = self.resume(stopped["receipt"])
        self.assertEqual(resumed["control"]["revision"], 2)
        self.assertFalse(resumed["control"]["stopped"])
        with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
            with self.store.barrier(0):
                self.fail("old revision renewed")
        with self.account().barrier(2) as current:
            self.assertFalse(current["control"]["dispatch_authorized"])
        self.assertFalse(resumed["broker_orders_cancelled"])

    def test_latest_stop_confirmation_required_and_every_new_stop_invalidates_revision(self):
        first = self.stop()
        second = self.stop(request="explicit-stop-0002")
        self.assertEqual(second["control"]["revision"], 2)
        with self.assertRaisesRegex(control.AccountControlError, "latest_stop_required"):
            self.resume(first["receipt"])
        self.assertEqual(self.resume(second["receipt"])["control"]["revision"], 3)

    def test_replayed_old_stop_returns_current_state_without_reapplying_transition(self):
        stopped = self.stop()
        self.resume(stopped["receipt"])
        before = self.inventory()
        replay = self.stop()
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"], stopped["receipt"])
        self.assertFalse(replay["control"]["stopped"])
        self.assertEqual(replay["control"]["revision"], 2)
        self.assertEqual(before, self.inventory())

    def test_same_request_changed_reason_is_conflict_and_read_is_immutable(self):
        self.stop()
        before = self.inventory()
        with self.assertRaisesRegex(control.AccountControlError, "request_conflict"):
            self.store.stop({"request_id": "explicit-stop-0001", "reason": "changed"})
        self.account().read("explicit-stop-0001")
        self.assertEqual(before, self.inventory())

    def test_stop_linearizes_after_short_write_barrier_and_blocks_next_partial_write(self):
        started = Event()
        def stop_peer():
            started.set()
            return self.stop(self.account())
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.store.barrier(0):
                pending = pool.submit(stop_peer)
                self.assertTrue(started.wait(1))
                self.assertFalse(pending.done())
            stopped = pending.result(timeout=1)
        self.assertTrue(stopped["control"]["stopped"])
        with self.assertRaisesRegex(control.AccountControlError, "changed_or_stopped"):
            with self.store.barrier(0):
                self.fail("next partial write admitted")

    def test_copied_database_cannot_rebind_another_account_or_root(self):
        self.stop()
        other = self.account(account_id="900000000000002")
        other.path.parent.mkdir(parents=True)
        shutil.copyfile(self.store.path, other.path)
        with self.assertRaisesRegex(control.AccountControlError, "scope_or_root_changed"):
            other.read()
        alternate = control.bind_host_root(self.root / "alternate", program_root=self.program, record_domain="SYNTHETIC_TEST")
        other = self.account(bound=alternate)
        other.path.parent.mkdir(parents=True)
        shutil.copyfile(self.store.path, other.path)
        with self.assertRaisesRegex(control.AccountControlError, "scope_or_root_changed"):
            other.read()

    def test_hot_rollback_and_hardlink_alias_reject_before_sqlite_open(self):
        self.stop()
        pending = Path(str(self.store.path) + "-journal")
        pending.write_bytes(b"new synthetic recovery marker")
        before = self.inventory()
        with patch.object(sqlite3, "connect", side_effect=AssertionError("No automatic recovery")):
            with self.assertRaisesRegex(control.AccountControlError, "pending_recovery"):
                self.store.read()
        self.assertEqual(before, self.inventory())
        pending.unlink()
        alias = self.root / "new-alias.sqlite3"
        os.link(self.store.path, alias)
        with patch.object(sqlite3, "connect", side_effect=AssertionError("No alias open")):
            with self.assertRaisesRegex(control.AccountControlError, "regular_bounded_store"):
                self.store.read()
        alias.unlink()

    def test_record_and_head_tampering_are_rejected_without_repair(self):
        self.stop()
        with closing(sqlite3.connect(self.store.path)) as connection:
            with connection:
                connection.execute("UPDATE metadata SET head=8")
        before = self.inventory()
        with self.assertRaisesRegex(control.AccountControlError, "head_changed"):
            self.store.read()
        self.assertEqual(before, self.inventory())

    def test_host_binding_cannot_be_inside_program_or_constructed_by_raw_dict(self):
        for path in (self.program, self.program / "data"):
            with self.assertRaisesRegex(control.AccountControlError, "outside_program"):
                control.bind_host_root(path, program_root=self.program, record_domain="SYNTHETIC_TEST")
        with self.assertRaisesRegex(control.AccountControlError, "typed_root"):
            control.AccountControl({}, mode=SIM, account_id="1")
        with self.assertRaisesRegex(control.AccountControlError, "host_binding"):
            control.SharedBrokerRoot({}, object())

    def test_capacity_keeps_last_slot_for_stop_and_bool_revision_is_not_integer(self):
        with patch.object(control, "MAX_EVENTS", 3):
            first = self.stop()
            self.resume(first["receipt"])
            last = self.stop(request="explicit-final-stop")
            self.assertEqual(last["control"]["revision"], 3)
            with self.assertRaisesRegex(control.AccountControlError, "capacity"):
                self.resume(last["receipt"], request="explicit-resume-last")
        with self.assertRaisesRegex(control.AccountControlError, "revision_required"):
            with self.store.barrier(False):
                self.fail("bool revision accepted")


if __name__ == "__main__":
    unittest.main()
