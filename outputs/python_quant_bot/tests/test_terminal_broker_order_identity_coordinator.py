"""Original coordinator ownership handoff on fresh synthetic SQLite fixtures."""
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from tests.broker_submit_market_fixture import SubmitMarketFixture, IDS
from tests import test_terminal_broker_action_coordinator as legacy_tests
from tests.test_futu_us_equity_simulate_wire_v2 import encode
from tests.test_terminal_broker_response_facts import response_payload, order_row


class OrderIdentityCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.h = legacy_tests.ActionCoordinatorTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def ready(self):
        fixture = SubmitMarketFixture(self.h.root / ("order-" + str(len(self.h.fixtures))))
        self.h.fixtures.append(fixture)
        fixture.initialize(); fixture.query_all(); fixture.seed(); fixture.prepare_submit()
        return fixture

    def acknowledged(self):
        fixture = self.ready()
        self.assertIsNone(fixture.codec.session_binding().as_dict()["broker_order_id"])
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "ACKNOWLEDGED", result)
        self.assertIsNotNone(fixture.codec.acknowledged_order_identity())
        return fixture

    @staticmethod
    def sends(fixture):
        return sum(event["kind"] == "send" for event in fixture.events)

    def bind(self, fixture, action, *, suffix="one", response=None):
        number = 30 + len(fixture.operations)
        frame = fixture.codec.encode_request(fixture.profile, action, number)
        identity = "order-identity-" + action + "-" + suffix
        permit = coordinator.synthetic_test_permit_v3(shared_root=fixture.bound,
            profile=fixture.profile, operation_id=identity, action=action, frame=frame,
            local_revision=0, account_revision=0, issued_at=fixture.clock.utcnow().isoformat(),
            expires_at=fixture.profile.as_dict()["wire_bounds"]["valid_until"])
        order_id = fixture.codec.acknowledged_order_identity().as_dict()["broker_order_id"]
        operation = coordinator.BoundOperation(identity, action, frame, permit, broker_order_id=order_id)
        fixture.operations.append(operation); fixture.subject.register(operation)
        if response is None:
            response = response_payload(action)
            if action == "trade_observe":
                row = order_row()
                order = fixture.profile.as_dict()["order"]
                row.update(qty=float(order["quantity"]), price=float(order["limit_price"]))
                response["s2c"]["orderList"] = [row]
        fixture.responses[action] = lambda _, serial: codec.pack_plaintext_frame(
            fixture.subject._actions[action][1], serial, encode(response))
        return operation

    def test_only_persisted_ack_is_adopted_then_original_query_and_cancel_preserve_money(self):
        fixture = self.ready()
        accept = fixture.codec.accept_acknowledged_order
        observed = []
        def after_commit(profile, identity):
            state = fixture.subject.journal.read(IDS["trade_submit"])
            self.assertEqual(state["actions"][IDS["trade_submit"]]["outcome"]["status"], "ACKNOWLEDGED")
            self.assertEqual(len(state["response_facts"]), 7)
            observed.append(identity.as_dict()["id"])
            return accept(profile, identity)
        with patch.object(fixture.codec, "accept_acknowledged_order", side_effect=after_commit):
            self.assertEqual(fixture.execute("trade_submit")["status"], "ACKNOWLEDGED")
        self.assertEqual(len(observed), 1)
        financial = fixture.subject.journal.read()["financial"]
        for action, status in (("trade_observe", "READ_FACTS_MATCHED"), ("trade_cancel", "CANCEL_ACK_NOT_TERMINAL")):
            operation = self.bind(fixture, action)
            result = fixture.subject.execute(operation.operation_id)
            self.assertEqual(result["response_facts"][0]["status"], status, result)
        state = fixture.subject.journal.read()
        claim = next(iter(state["claims"].values()))
        self.assertTrue(claim["cancel_acknowledged"])
        self.assertEqual(claim["order_state"], "OPEN")
        self.assertEqual(claim["filled_quantity"], 0)
        self.assertIsNone(claim["fees"])
        self.assertEqual(state["financial"], financial)
        self.assertEqual(state["observation_ids"], [])
        self.assertEqual(sum(e["kind"] == "connect" for e in fixture.events), 2)

    def test_unconfirmed_response_save_never_adopts_or_automatically_repeats(self):
        for commit_first in (False, True):
            with self.subTest(commit_first=commit_first):
                fixture = self.ready()
                save = fixture.subject.journal.record_verified_response
                def unavailable(*args, **kwargs):
                    if commit_first:
                        save(*args, **kwargs)
                    raise OSError("Synthetic save reply missing")
                with patch.object(fixture.subject.journal, "record_verified_response", side_effect=unavailable):
                    result = fixture.execute("trade_submit")
                self.assertEqual(result["status"], "UNKNOWN")
                self.assertIsNone(fixture.codec.acknowledged_order_identity())
                self.assertIsNone(fixture.codec.session_binding().as_dict()["broker_order_id"])
                before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
                with patch.object(fixture.subject.journal, "read_acknowledged_order", side_effect=AssertionError("Read only")):
                    recovered = fixture.execute("trade_submit")
                self.assertTrue(recovered["recovered_original"])
                self.assertEqual(recovered["status"], "ACKNOWLEDGED" if commit_first else "UNKNOWN")
                self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
                self.assertEqual(self.sends(fixture), sends)
                self.assertIsNone(fixture.codec.acknowledged_order_identity())

    def test_api_error_or_missing_original_id_cannot_enable_followup_encoding(self):
        for response in ({"retType": -1, "retMsg": "fictional failure"},
                         {"retType": 0, "s2c": {"header": response_payload("trade_submit")["s2c"]["header"], "orderID": 44}}):
            fixture = self.ready()
            fixture.responses["trade_submit"] = response
            self.assertEqual(fixture.execute("trade_submit")["status"], "UNKNOWN")
            self.assertIsNone(fixture.codec.acknowledged_order_identity())
            with self.assertRaises(codec.CodecError):
                fixture.codec.encode_request(fixture.profile, "trade_cancel", 40)

    def test_new_followup_requires_current_journal_readback_and_exact_operation_order(self):
        fixture = self.acknowledged()
        operation = self.bind(fixture, "trade_cancel")
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        with patch.object(fixture.subject.journal, "read_acknowledged_order", return_value=None):
            with self.assertRaisesRegex(coordinator.CoordinatorError, "journal_acknowledged_order_required"):
                fixture.subject.execute(operation.operation_id)
        fixture.subject._operations[operation.operation_id] = replace(operation, broker_order_id="foreign-order")
        with self.assertRaisesRegex(coordinator.CoordinatorError, "operation_original_order_changed"):
            fixture.subject.execute(operation.operation_id)
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.sends(fixture), sends)

    def test_followup_keeps_original_identity_after_observation_window_expires(self):
        fixture = self.acknowledged()
        identity = fixture.codec.acknowledged_order_identity().as_dict()
        fixture.clock.offset += 40
        operation = self.bind(fixture, "trade_cancel")
        result = fixture.subject.execute(operation.operation_id)
        self.assertEqual(result["status"], "ACKNOWLEDGED", result)
        self.assertEqual(fixture.codec.acknowledged_order_identity().as_dict(), identity)

    def test_followup_write_barriers_do_not_reopen_journal(self):
        fixture = self.acknowledged()
        operation = self.bind(fixture, "trade_cancel")
        barrier = fixture.service.broker_dispatch_barrier
        @contextmanager
        def no_nested_journal(*args, **kwargs):
            with barrier(*args, **kwargs) as current:
                with patch.object(fixture.subject.journal, "_database", side_effect=AssertionError("No database inside barrier")):
                    yield current
        with patch.object(fixture.service, "broker_dispatch_barrier", side_effect=no_nested_journal):
            result = fixture.subject.execute(operation.operation_id)
        self.assertEqual(result["status"], "ACKNOWLEDGED", result)

    def test_confirmed_quote_loss_does_not_block_cancel_but_trade_loss_does(self):
        # Explicit confirmed-loss injection, not a production FIN detector.
        for lost_channel in ("quote", "trade"):
            with self.subTest(lost_channel=lost_channel):
                fixture = self.acknowledged()
                operation = self.bind(fixture, "trade_cancel")
                identity = fixture.codec.acknowledged_order_identity().as_dict()
                financial = fixture.subject.journal.read()["financial"]
                connects = sum(event["kind"] == "connect" for event in fixture.events)
                fixture.connections[lost_channel].close(timeout=0)
                fixture.subject._connected.discard(lost_channel)
                fixture.subject._initialized.discard(lost_channel)
                if lost_channel == "quote":
                    result = fixture.subject.execute(operation.operation_id)
                    self.assertEqual(result["status"], "ACKNOWLEDGED", result)
                else:
                    before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
                    with self.assertRaisesRegex(coordinator.CoordinatorError, "current_trade_handshake_required"):
                        fixture.subject.execute(operation.operation_id)
                    self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
                    self.assertEqual(self.sends(fixture), sends)
                self.assertEqual(fixture.codec.acknowledged_order_identity().as_dict(), identity)
                self.assertEqual(fixture.subject.journal.read()["financial"], financial)
                self.assertEqual(sum(event["kind"] == "connect" for event in fixture.events), connects)

    def test_stop_after_followup_action_prevents_send_without_releasing_original_order(self):
        fixture = self.acknowledged()
        operation = self.bind(fixture, "trade_cancel")
        financial, sends = fixture.subject.journal.read()["financial"], self.sends(fixture)
        begin = fixture.subject.journal.begin_action
        def stop_after_commit(*args, **kwargs):
            result = begin(*args, **kwargs)
            fixture.stop_account()
            return result
        with patch.object(fixture.subject.journal, "begin_action", side_effect=stop_after_commit):
            result = fixture.subject.execute(operation.operation_id)
        self.assertEqual(result["status"], "NOT_DISPATCHED", result)
        self.assertEqual(self.sends(fixture), sends)
        self.assertEqual(fixture.subject.journal.read()["financial"], financial)
        self.assertGreater(Decimal(financial["cash_reserved"]), 0)

    def test_partial_cancel_keeps_unknown_and_reopen_reads_original_ids_without_admission(self):
        fixture = self.acknowledged()
        operation = self.bind(fixture, "trade_cancel")
        fixture.connections["trade"].parts = [9]
        after_write = fixture.subject._gate.after_write
        def stop_after_prefix(context, permit, written):
            after_write(context, permit, written)
            fixture.stop_account()
        with patch.object(fixture.subject._gate, "after_write", side_effect=stop_after_prefix):
            result = fixture.subject.execute(operation.operation_id)
        self.assertEqual(result["status"], "UNKNOWN", result)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 9)
        self.assertGreater(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)
        fixture.subject.close()
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        with patch.object(fixture.subject.journal, "read_acknowledged_order", side_effect=AssertionError("Read must not adopt")), \
             patch.object(fixture.subject, "_validate_permit", side_effect=AssertionError("Read must not dispatch")):
            for original in fixture.operations:
                self.assertTrue(fixture.subject.execute(original.operation_id)["recovered_original"])
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.sends(fixture), sends)


if __name__ == "__main__":
    unittest.main()
