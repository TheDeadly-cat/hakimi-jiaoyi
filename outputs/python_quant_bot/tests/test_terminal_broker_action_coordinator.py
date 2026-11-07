"""Real local SQLite/control/transport assembly on fresh synthetic fixtures only."""
import builtins
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from tests.broker_action_coordinator_fixture import Fixture


def inventory(root):
    return {p.relative_to(root).as_posix(): (sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


class ActionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="new-action-coordinator-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fixtures = []
        self.addCleanup(self.close_fixtures)
        original_import = builtins.__import__

        def no_sdk(name, *args, **kwargs):
            if name == "futu" or name.startswith("futu."):
                raise AssertionError("No SDK import in coordinator contracts")
            return original_import(name, *args, **kwargs)

        guard = patch("builtins.__import__", side_effect=no_sdk)
        guard.start(); self.addCleanup(guard.stop)
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.socket.bind",
                     "socket.create_connection", "socket.getaddrinfo", "urllib.request.urlopen", "subprocess.Popen"):
            guard = patch(name, side_effect=AssertionError("No external operation in in-process coordinator test"))
            blocked = guard.start(); self.addCleanup(guard.stop); self.addCleanup(blocked.assert_not_called)

    def close_fixtures(self):
        for fixture in reversed(self.fixtures):
            fixture.close()

    def fixture(self, *, group=None, **kwargs):
        path = self.root / (group or f"case-{len(self.fixtures)}")
        result = Fixture(path, **kwargs)
        self.fixtures.append(result)
        return result

    @staticmethod
    def sends(fixture):
        return sum(event["kind"] == "send" for event in fixture.events)

    @staticmethod
    def operation(fixture, action):
        return next(value for value in fixture.operations if value.action == action)

    @staticmethod
    def claim(fixture):
        return fixture.subject.journal.read()["claims"][fixture.profile.as_dict()["deduplication"]["intent_scope_id"]]

    def prepared(self, **kwargs):
        fixture = self.fixture(**kwargs)
        fixture.seed(); fixture.initialize()
        return fixture

    def test_actual_submit_and_cancel_ack_preserve_reservation_and_known_write_count(self):
        fixture = self.prepared()
        sent_before = self.sends(fixture)
        submitted = fixture.execute("trade_submit")
        frame = self.operation(fixture, "trade_submit").frame
        self.assertEqual(submitted["status"], "ACKNOWLEDGED")
        self.assertEqual(self.sends(fixture), sent_before + 1)
        self.assertEqual(submitted["action_state"]["outcome"]["sent_bytes"], len(frame))
        self.assertEqual(submitted["action_state"]["outcome"]["possible_sent_bytes"], len(frame))
        self.assertEqual(submitted["response_facts"][0]["status"], "ACK_SCOPE_MATCHED")
        self.assertEqual(self.claim(fixture)["filled_quantity"], 0)
        self.assertIsNone(self.claim(fixture)["fees"])
        self.assertFalse(self.claim(fixture)["fees_final"])
        financial = fixture.subject.journal.read()["financial"]
        self.assertGreater(Decimal(financial["cash_reserved"]), 0)
        cancelled = fixture.execute("trade_cancel")
        self.assertEqual(cancelled["status"], "ACKNOWLEDGED")
        self.assertEqual(cancelled["response_facts"][0]["status"], "CANCEL_ACK_NOT_TERMINAL")
        self.assertTrue(self.claim(fixture)["cancel_acknowledged"])
        self.assertEqual(self.claim(fixture)["order_state"], "OPEN")
        self.assertEqual(fixture.subject.journal.read()["financial"], financial)
        self.assertFalse(any(cancelled["permissions"].values()))
        self.assertEqual(len(fixture.subject.journal.read()["actions"]), 4)

    def test_api_error_retains_original_response_without_rejection_or_zero_fee(self):
        fixture = self.prepared()
        fixture.responses["trade_submit"] = {"retType": -1, "retMsg": "fictional transport API error"}
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["response_facts"][0]["status"], "API_ERROR_RESPONSE")
        self.assertEqual(self.claim(fixture)["order_state"], "OPEN")
        self.assertIsNone(self.claim(fixture)["fees"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], len(self.operation(fixture, "trade_submit").frame))

    def test_wrong_account_reply_remains_unknown_and_retained_without_typed_ack(self):
        fixture = self.prepared()
        payload = fixture.response("trade_submit")
        payload["s2c"]["header"]["accID"] += 1
        fixture.responses["trade_submit"] = payload
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["response_facts"], [])
        self.assertIsNone(self.claim(fixture)["broker_order_id"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        self.assertTrue(any(row["operation_id"] == result["operation_id"] and row["header"]["kind"] == "response_frame"
                            for row in fixture.subject._sink.records))

    def test_default_denial_and_missing_factory_create_no_action_or_connection(self):
        for permits in (False, True):
            with self.subTest(permits=permits):
                fixture = self.fixture(permits=permits)
                if permits:
                    fixture.subject.factory = None
                before = inventory(fixture.root)
                with self.assertRaisesRegex(coordinator.CoordinatorError,
                        "CONNECTION_FACTORY_UNAVAILABLE" if permits else "AUTHORIZATION_REQUIRED"):
                    fixture.execute("trade_connect")
                self.assertEqual(fixture.events, [])
                self.assertFalse(fixture.subject.journal.path.exists())
                self.assertFalse(fixture.subject._evidence.exists())
                self.assertEqual(inventory(fixture.root), before)

    def test_synthetic_permit_never_admits_an_external_record_host(self):
        synthetic = self.fixture()
        external = self.fixture(record_domain="EXTERNAL_RECORD", permits=False)
        operation = self.operation(synthetic, "trade_connect")
        with self.assertRaisesRegex(coordinator.CoordinatorError, "synthetic_host_root_required"):
            coordinator.synthetic_test_permit(shared_root=external.bound, profile=external.profile,
                operation_id=operation.operation_id, action=operation.action, frame=operation.frame,
                local_revision=0, account_revision=0,
                issued_at=operation.permit.as_dict()["issued_at"], expires_at=operation.permit.as_dict()["expires_at"])
        external.subject._operations[operation.operation_id] = operation
        before = inventory(external.root)
        with self.assertRaisesRegex(coordinator.CoordinatorError, "PRODUCTION_ADMISSION_UNAVAILABLE"):
            external.execute("trade_connect")
        self.assertEqual(external.events, [])
        self.assertFalse(external.subject.journal.path.exists())
        self.assertEqual(inventory(external.root), before)

    def test_reopen_same_id_is_byte_read_only_even_after_expiry_and_stop(self):
        original = self.prepared(group="reopen")
        saved = original.execute("trade_submit")
        original.stop_account(); original.subject.close()
        reopened = self.fixture(group="reopen", evidence="evidence-reopened")
        reopened.clock.offset = 3600
        before = inventory(reopened.root)
        result = reopened.execute("trade_submit")
        self.assertTrue(result["recovered_original"])
        self.assertEqual(result["original_action_receipt"], saved["original_action_receipt"])
        self.assertEqual(result["action_state"], saved["action_state"])
        self.assertEqual(reopened.events, [])
        self.assertFalse(reopened.subject._evidence.exists())
        self.assertEqual(inventory(reopened.root), before)

    def test_same_operation_id_with_changed_frame_cannot_read_or_dispatch_original(self):
        fixture = self.prepared()
        fixture.execute("trade_submit")
        operation = self.operation(fixture, "trade_submit")
        fixture.subject._operations[operation.operation_id] = replace(operation, frame=operation.frame + b" ")
        before = inventory(fixture.root)
        sends = self.sends(fixture)
        with self.assertRaisesRegex(coordinator.CoordinatorError, "original_operation_binding_changed"):
            fixture.execute("trade_submit")
        self.assertEqual(self.sends(fixture), sends)
        self.assertEqual(inventory(fixture.root), before)

    def test_lost_action_commit_reply_never_starts_connection_or_resumes_original(self):
        fixture = self.fixture()
        commit = fixture.subject.journal._commit
        def lost(connection):
            commit(connection)
            raise OSError("fictional ACTION commit reply lost")
        with patch.object(fixture.subject.journal, "_commit", side_effect=lost):
            result = fixture.execute("trade_connect")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNotNone(result["original_action_receipt"])
        self.assertEqual(fixture.events, [])
        self.assertIsNone(result["action_state"]["outcome"])
        before = inventory(fixture.root)
        self.assertTrue(fixture.execute("trade_connect")["recovered_original"])
        self.assertEqual(fixture.events, [])
        self.assertEqual(inventory(fixture.root), before)

    def test_lost_claim_reply_keeps_reserve_and_does_not_start_submit(self):
        fixture = self.prepared()
        sent = self.sends(fixture)
        commit = fixture.subject.journal._commit
        def lost(connection):
            commit(connection)
            raise OSError("fictional claim commit reply lost")
        with patch.object(fixture.subject.journal, "_commit", side_effect=lost):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["original_action_receipt"])
        self.assertEqual(self.sends(fixture), sent)
        self.assertFalse(self.claim(fixture)["submit_started"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        before = inventory(fixture.root)
        again = fixture.execute("trade_submit")
        self.assertEqual(again["reason"], "PRIOR_CLAIM_NO_AUTOMATIC_RESUME")
        self.assertEqual(self.sends(fixture), sent)
        self.assertEqual(inventory(fixture.root), before)

    def test_lost_outcome_commit_reply_preserves_known_count_and_never_repeats_send(self):
        fixture = self.prepared()
        commit = fixture.subject.journal._commit
        calls = 0
        def lose_third(connection):
            nonlocal calls
            calls += 1
            commit(connection)
            if calls == 3:
                raise OSError("fictional raw outcome commit reply lost")
        sent = self.sends(fixture)
        with patch.object(fixture.subject.journal, "_commit", side_effect=lose_third):
            result = fixture.execute("trade_submit")
        self.assertEqual(calls, 3)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], len(self.operation(fixture, "trade_submit").frame))
        self.assertEqual(result["response_facts"], [])
        before = inventory(fixture.root)
        self.assertTrue(fixture.execute("trade_submit")["recovered_original"])
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertEqual(inventory(fixture.root), before)

    def test_local_and_peer_account_stop_block_actual_connect(self):
        for scope in ("local", "account"):
            with self.subTest(scope=scope):
                group = "stopped-" + scope
                fixture = self.fixture(group=group)
                if scope == "local":
                    fixture.stop_local()
                else:
                    peer = self.fixture(group=group, workspace="workspace-peer", evidence="evidence-peer")
                    peer.stop_account()
                result = fixture.execute("trade_connect")
                self.assertIsNone(result["original_action_receipt"])
                self.assertEqual(fixture.events, [])
                self.assertEqual(fixture.subject.journal.read()["actions"], {})

    def test_peer_stop_between_partial_writes_preserves_partial_count_and_reserve(self):
        fixture = self.prepared(group="partial-stop")
        peer = self.fixture(group="partial-stop", workspace="workspace-peer", evidence="evidence-peer")
        fixture.connections["trade"].parts = [9]
        progress = fixture.subject._gate.after_write
        offsets = []
        def stop_after_first(context, permit, written):
            offsets.append(context["offset"])
            progress(context, permit, written)
            peer.stop_account()
        sent = self.sends(fixture)
        with patch.object(fixture.subject._gate, "after_write", side_effect=stop_after_first):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(offsets, [0])
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 9)
        self.assertEqual(result["action_state"]["outcome"]["possible_sent_bytes"], 9)
        self.assertTrue(fixture.connections["trade"].closed)
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        self.assertIsNone(self.claim(fixture)["fees"])
        self.assertEqual(len(fixture.subject.journal.read()["actions"]), 3)

    def test_stop_after_action_commit_before_write_records_not_dispatched(self):
        fixture = self.prepared()
        begin = fixture.subject.journal.begin_action
        def stop_after_commit(*args, **kwargs):
            result = begin(*args, **kwargs)
            fixture.stop_local()
            return result
        sent = self.sends(fixture)
        with patch.object(fixture.subject.journal, "begin_action", side_effect=stop_after_commit):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "NOT_DISPATCHED")
        self.assertEqual(self.sends(fixture), sent)
        self.assertFalse(result["action_state"]["outcome"]["write_attempted"])
        self.assertEqual(result["action_state"]["outcome"]["possible_sent_bytes"], 0)
        self.assertEqual(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        self.assertTrue(self.claim(fixture)["fees_final"])

    def test_request_evidence_failure_prevents_actual_write(self):
        fixture = self.prepared()
        write = fixture.subject._write_evidence
        def fail_request(name, raw, **kwargs):
            if name.startswith("frame-"):
                header = json.loads(raw.partition(b"\n")[0])
                if header.get("action") == "trade_submit" and header["kind"] == "request_frame":
                    raise OSError("fictional request evidence unavailable")
            return write(name, raw, **kwargs)
        sent = self.sends(fixture)
        with patch.object(fixture.subject, "_write_evidence", side_effect=fail_request):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "NOT_DISPATCHED")
        self.assertEqual(self.sends(fixture), sent)
        self.assertEqual(result["response_facts"], [])

    def test_outcome_evidence_failure_after_write_stays_unknown_with_reserve(self):
        fixture = self.prepared()
        write = fixture.subject._write_evidence
        def fail_outcome(name, raw, **kwargs):
            if name.startswith("outcome-"):
                raise OSError("fictional completion evidence unavailable")
            return write(name, raw, **kwargs)
        sent = self.sends(fixture)
        with patch.object(fixture.subject, "_write_evidence", side_effect=fail_outcome):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertIsNone(result["action_state"]["outcome"])
        self.assertEqual(result["response_facts"], [])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        before = inventory(fixture.root)
        self.assertTrue(fixture.execute("trade_submit")["recovered_original"])
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertEqual(inventory(fixture.root), before)

    def test_changed_retained_response_cannot_be_promoted_from_memory_to_ack(self):
        fixture = self.prepared()
        write = fixture.subject._write_evidence
        changed = []
        def tamper_after_write(name, raw, **kwargs):
            result = write(name, raw, **kwargs)
            if name.startswith("frame-"):
                header = json.loads(raw.partition(b"\n")[0])
                if header.get("action") == "trade_submit" and header["kind"] == "response_frame":
                    path = fixture.subject._evidence / name
                    path.write_bytes(path.read_bytes() + b"changed retained original")
                    changed.append(path)
            return result
        with patch.object(fixture.subject, "_write_evidence", side_effect=tamper_after_write):
            result = fixture.execute("trade_submit")
        self.assertEqual(len(changed), 1)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["response_facts"], [])
        self.assertIsNone(self.claim(fixture)["broker_order_id"])
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        self.assertTrue(changed[0].read_bytes().endswith(b"changed retained original"))

    def test_actual_small_budget_bounds_all_files_and_keeps_final_receipt_reserve(self):
        fixture = self.fixture(wire_bounds_changes=dict(max_frame_bytes=4096, max_wire_bytes=4096,
            max_output_bytes=20480, reserved_final_output_bytes=16384))
        fixture.seed()
        results = []
        for action in ("trade_connect", "trade_init", "trade_submit", "trade_observe", "trade_cancel", "trade_fees"):
            try:
                results.append(fixture.execute(action))
            except coordinator.CoordinatorError:
                break  # A prior exhausted operation removed the usable connection.
        self.assertTrue(any(row.get("reason") == "ACTION_COMPLETION_UNCONFIRMED" for row in results), results)
        directory = fixture.subject._evidence
        ordinary = sum(path.stat().st_size for path in directory.iterdir() if path.is_file())
        self.assertLessEqual(ordinary, 4096)
        result = fixture.subject.close()
        self.assertTrue(result["cleanup_confirmed"])
        self.assertTrue((directory / "coordinator-final.json").is_file())
        self.assertLessEqual(sum(path.stat().st_size for path in directory.iterdir() if path.is_file()), 20480)
        before = inventory(fixture.root)
        self.assertEqual(fixture.subject.close(), result)
        self.assertEqual(inventory(fixture.root), before)

    def test_expired_permission_between_partial_writes_does_not_send_remainder(self):
        fixture = self.prepared()
        fixture.connections["trade"].parts = [7]
        progress = fixture.subject._gate.after_write
        def expire(context, permit, written):
            progress(context, permit, written)
            fixture.clock.offset = 3600
        sent = self.sends(fixture)
        with patch.object(fixture.subject._gate, "after_write", side_effect=expire):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(self.sends(fixture), sent + 1)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 7)
        self.assertIsNone(self.claim(fixture)["fees"])


if __name__ == "__main__":
    unittest.main()
