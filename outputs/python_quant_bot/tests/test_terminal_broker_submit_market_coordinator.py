"""Original v3 coordinator/barriers on new TEMP ledgers and explicit JSON fakes.

No SDK, OS socket or external account is used here. The separate private worker
probe supplies actual generated protobuf and an owned TCP peer.
"""
from dataclasses import replace
from contextlib import contextmanager
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_action_coordinator as coordinator
from exchange_terminal.services import terminal_broker_execution_plan as contract
from exchange_terminal.services import terminal_broker_submit_observation as observation
from tests.broker_submit_market_fixture import SubmitMarketFixture, response_values, IDS
from tests.test_futu_us_equity_simulate_wire_v2 import encode
from tests import test_terminal_broker_action_coordinator as legacy_tests


class SubmitMarketCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.h = legacy_tests.ActionCoordinatorTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def fixture(self, **kwargs):
        root = self.h.root / ("market-" + str(len(self.h.fixtures)))
        item = SubmitMarketFixture(root, **kwargs)
        self.h.fixtures.append(item)
        return item

    def ready(self, *, permit_until_profile=False):
        fixture = self.fixture()
        fixture.initialize()
        results = fixture.query_all()
        self.assertTrue(all(value["response_facts"] for value in results))
        fixture.seed()
        operation = fixture.prepare_submit(permit_expires_at=(
            fixture.profile.as_dict()["wire_bounds"]["valid_until"] if permit_until_profile else None))
        return fixture, operation

    @staticmethod
    def sends(fixture):
        return sum(row["kind"] == "send" for row in fixture.events)

    @staticmethod
    def expire(fixture, operation):
        expiry = contract._time(operation.submit_observation.as_dict()["expires_at"])
        fixture.clock.offset += (expiry - fixture.clock.utcnow()).total_seconds() + .01

    def assert_no_new_submit(self, fixture, sends):
        self.assertEqual(self.sends(fixture), sends)
        self.assertIsNone(fixture.subject.journal.read(IDS["trade_submit"])["receipt"])

    def test_matching_observations_reach_original_submit_ack_without_fills_or_secret_export(self):
        fixture, operation = self.ready()
        before = self.sends(fixture)
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "ACKNOWLEDGED", result)
        self.assertEqual(self.sends(fixture), before + 1)
        self.assertEqual(result["original_action_receipt"]["payload"]["submit_observation"],
                         operation.submit_observation.as_dict())
        state = fixture.subject.journal.read()
        claim = next(iter(state["claims"].values()))
        self.assertEqual(claim["submit_observation"], operation.submit_observation.as_dict())
        self.assertEqual(claim["filled_quantity"], 0)
        self.assertIsNone(claim["fees"])
        self.assertFalse(claim["fees_final"])
        self.assertGreater(Decimal(state["financial"]["cash_reserved"]), 0)
        self.assertEqual(len(state["response_facts"]), 7)  # Six observations plus the original submit ACK.
        encoded = json.dumps(state).encode()
        for secret in (b"private-fictional-key", b"private-fictional-iv", b"private-fictional-handshake-text"):
            self.assertNotIn(secret, encoded)
            self.assertTrue(any(secret in path.read_bytes() for path in fixture.subject._evidence.glob("frame-*.bin")))

    def test_v3_missing_observation_and_old_permit_cannot_enter_claim_or_send(self):
        fixture, operation = self.ready()
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        fixture.subject._operations[operation.operation_id] = replace(operation, submit_observation=None)
        with self.assertRaisesRegex(coordinator.CoordinatorError, "submit_observation_required"):
            fixture.execute("trade_submit")
        legacy = self.h.fixture()
        old_permit = next(row.permit for row in legacy.operations if row.action == "trade_submit")
        fixture.subject._operations[operation.operation_id] = replace(operation, permit=old_permit)
        with self.assertRaisesRegex(coordinator.CoordinatorError, "PRODUCTION_ADMISSION_UNAVAILABLE"):
            fixture.execute("trade_submit")
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assert_no_new_submit(fixture, sends)
        self.assertEqual(fixture.subject.journal.read()["claims"], {})
        details = operation.permit.as_dict()
        with self.assertRaisesRegex(coordinator.CoordinatorError, "version_mismatch"):
            coordinator.synthetic_test_permit(shared_root=fixture.bound, profile=fixture.profile,
                operation_id=operation.operation_id, action=operation.action, frame=operation.frame,
                local_revision=0, account_revision=0, issued_at=details["issued_at"], expires_at=details["expires_at"])

    def test_target_closed_or_unknown_refuses_even_when_global_market_is_open(self):
        for state_code in (0, 6, 8, 999):
            fixture = self.fixture()
            fixture.initialize()
            runtime = response_values("quote_runtime")
            runtime["s2c"]["marketUS"] = 5
            fixture.responses["quote_runtime"] = lambda action, serial, value=runtime: codec.pack_plaintext_frame(1002, serial, encode(value))
            response = response_values("quote_market_state", market_state=state_code)
            fixture.responses["quote_market_state"] = lambda action, serial, value=response: codec.pack_plaintext_frame(3223, serial, encode(value))
            fixture.query_all()
            before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
            with self.subTest(state_code=state_code), self.assertRaisesRegex(observation.SubmitObservationError, "target_market_not_continuous"):
                fixture.subject.journal.prepare_submit_observation(fixture.profile, fixture.codec.accepted_session_binding("trade"))
            self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
            self.assert_no_new_submit(fixture, sends)

    def test_bundle_expiry_blocks_before_claim_with_live_permit_and_clock_rollback_does_not_revive(self):
        fixture, operation = self.ready(permit_until_profile=True)
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        self.expire(fixture, operation)
        self.assertLess(fixture.clock.utcnow(), contract._time(operation.permit.as_dict()["expires_at"]))
        with self.assertRaisesRegex(observation.SubmitObservationError, "expired"):
            fixture.execute("trade_submit")
        fixture.clock.offset = 0
        with self.assertRaisesRegex(coordinator.CoordinatorError, "clock_regressed"):
            fixture.execute("trade_submit")
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assert_no_new_submit(fixture, sends)

    def test_newly_prepared_bundle_cannot_replace_the_permit_bound_observation(self):
        fixture, operation = self.ready()
        fixture.clock.offset += .01
        different = fixture.subject.journal.prepare_submit_observation(fixture.profile, fixture.codec.accepted_session_binding("trade"))
        self.assertNotEqual(different.as_dict()["id"], operation.submit_observation.as_dict()["id"])
        fixture.subject._operations[operation.operation_id] = replace(operation, submit_observation=different)
        sends = self.sends(fixture)
        with self.assertRaisesRegex(coordinator.CoordinatorError, "observation_binding_changed"):
            fixture.execute("trade_submit")
        self.assert_no_new_submit(fixture, sends)
        self.assertEqual(fixture.subject.journal.read()["claims"], {})

    def test_expiry_after_claim_prevents_action_and_preserves_original_reservation(self):
        fixture, operation = self.ready(permit_until_profile=True)
        sends = self.sends(fixture)
        original = fixture.subject.journal.claim
        def claim_then_expire(*args, **kwargs):
            result = original(*args, **kwargs)
            self.expire(fixture, operation)
            return result
        with patch.object(fixture.subject.journal, "claim", side_effect=claim_then_expire):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "JOURNAL_ADMISSION_UNCONFIRMED")
        self.assert_no_new_submit(fixture, sends)
        state = fixture.subject.journal.read()
        self.assertEqual(len(state["claims"]), 1)
        self.assertFalse(next(iter(state["claims"].values()))["submit_started"])
        self.assertGreater(Decimal(state["financial"]["cash_reserved"]), 0)

    def test_expiry_after_action_is_rechecked_before_first_send_without_journal_read_in_barrier(self):
        fixture, operation = self.ready(permit_until_profile=True)
        sends = self.sends(fixture)
        original = fixture.subject.journal.begin_action
        def action_then_expire(*args, **kwargs):
            result = original(*args, **kwargs)
            self.expire(fixture, operation)
            return result
        barrier = fixture.service.broker_dispatch_barrier
        @contextmanager
        def no_nested_journal(*args, **kwargs):
            with barrier(*args, **kwargs) as current:
                with patch.object(fixture.subject.journal, "_database",
                                  side_effect=AssertionError("No journal open while local/account barrier is held")):
                    yield current
        with patch.object(fixture.subject.journal, "begin_action", side_effect=action_then_expire), \
                patch.object(fixture.service, "broker_dispatch_barrier", side_effect=no_nested_journal):
            result = fixture.execute("trade_submit")
        self.assertNotEqual(result["status"], "ACKNOWLEDGED")
        self.assertIsNotNone(result["original_action_receipt"])
        self.assertEqual(self.sends(fixture), sends)
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 0)
        # The original NOT_DISPATCHED contract has positive evidence that no
        # write was attempted, so it can release this local reservation. This
        # is distinct from a partial send or an unconfirmed journal reply.
        self.assertEqual(result["status"], "NOT_DISPATCHED")
        self.assertEqual(result["action_state"]["outcome"]["possible_sent_bytes"], 0)
        self.assertFalse(result["action_state"]["outcome"]["write_attempted"])
        self.assertEqual(Decimal(fixture.subject.journal.read()["financial"]["cash_reserved"]), 0)

    def test_partial_send_rechecks_bundle_then_retains_unknown_and_never_resends_original_id(self):
        fixture, operation = self.ready(permit_until_profile=True)
        connection = fixture.connections["trade"]
        connection.parts = [9]
        original = fixture.subject._gate.after_write
        def expire_after_prefix(context, permit, written):
            original(context, permit, written)
            self.expire(fixture, operation)
        with patch.object(fixture.subject._gate, "after_write", side_effect=expire_after_prefix):
            result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["action_state"]["outcome"]["sent_bytes"], 9)
        self.assertEqual(bytes(connection.pending), operation.frame[:9])
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        with patch.object(fixture.subject, "_validate_permit", side_effect=AssertionError("Read must not revalidate for resend")):
            recovered = fixture.execute("trade_submit")
        self.assertTrue(recovered["recovered_original"])
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assertEqual(self.sends(fixture), sends)

    def test_shared_stop_after_preparation_blocks_new_claim_and_write(self):
        fixture, operation = self.ready()
        before, sends = fixture.subject.journal.path.read_bytes(), self.sends(fixture)
        fixture.stop_account()
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "JOURNAL_ADMISSION_UNCONFIRMED")
        self.assertEqual(fixture.subject.journal.path.read_bytes(), before)
        self.assert_no_new_submit(fixture, sends)


if __name__ == "__main__":
    unittest.main()
