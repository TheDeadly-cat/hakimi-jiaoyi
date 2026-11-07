"""Original new TEMP journal and JSON protocol fakes, not broker acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_execution_plan as contract
from exchange_terminal.services import terminal_broker_order_identity as identity
from exchange_terminal.services import terminal_broker_response_facts as facts
from tests import test_terminal_broker_submit_observation as fixture
from tests.test_futu_us_equity_simulate_wire_v2 import encode
from tests.test_terminal_broker_execution_journal import AUTHORIZATION_REFERENCE


ORDER = "fictional-opaque-order-0044"


class AcknowledgedOrderTests(unittest.TestCase):
    def setUp(self):
        self.h = fixture.SubmitObservationTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.store = self.h.ready()
        self.profile, self.codec = self.h.profile, self.h.codec
        self.h.h.seed(self.store)
        self.bundle = self.h.prepare(self.store)
        self.claim = self.h.claim(self.store, self.bundle)["receipt"]
        self.submitted = self.h.begin(self.store, self.bundle)["receipt"]
        self.frame = self.codec.encode_request(self.profile, "trade_submit", 77)

    def response(self, *, order=ORDER, header=None, ret_type=0, request_frame=None):
        response = {"retType": ret_type, "s2c": {"header": header if header is not None else
            {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2}}}
        if order is not None:
            response["s2c"]["orderIDEx"] = order
        return facts.verify_response_facts(profile=self.profile, codec=self.codec,
            action_receipt=self.submitted, expected_action_receipt_id=self.submitted["id"],
            request_frame=self.frame if request_frame is None else request_frame,
            response_frame=codec.pack_plaintext_frame(2202, 77, encode(response)), received_at=self.h.h.now)

    def acknowledge(self, **changes):
        verified = self.response(**changes)
        record = self.store.record_verified_response(verified, request_id=self.h.h.request("ack"))
        return verified, record["receipt"]

    def followup(self, action="trade_observe", *, broker_id=ORDER):
        return self.store.begin_action(self.profile, action, request_id=self.h.h.request(action),
            frame_sha256="a" * 64, frame_bytes=100, authorization_id=AUTHORIZATION_REFERENCE,
            broker_order_id=broker_id, control_barrier=lambda: self.h.h.barrier(self.profile))

    def test_empty_and_pending_sources_do_not_mint_identity_or_create_store(self):
        empty = self.h.store()
        self.assertIsNone(empty.read_acknowledged_order(self.profile))
        self.assertFalse(empty.path.exists())
        before = self.store.read()
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        unrecorded = self.response()
        self.assertEqual(unrecorded.as_dict()["status"], "ACK_SCOPE_MATCHED")
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        self.assertEqual(self.store.read(), before)
        with self.assertRaisesRegex(journal.JournalError, "verified_wire_profile_required"):
            self.store.read_acknowledged_order(self.profile.as_dict())

    def test_recorded_ack_chain_exports_exact_immutable_identity_and_no_new_authority(self):
        verified, receipt = self.acknowledge()
        before, database = self.store.read(), self.store.path.read_bytes()
        typed = self.store.read_acknowledged_order(self.profile)
        value = typed.as_dict()
        self.assertIs(type(typed), identity.VerifiedAcknowledgedOrder)
        self.assertEqual(value["broker_order_id"], ORDER)
        self.assertEqual(value["claim_receipt_id"], self.claim["id"])
        self.assertEqual(value["submit_action_receipt_id"], self.submitted["id"])
        self.assertEqual(value["ack_response_receipt_id"], receipt["id"])
        self.assertEqual(value["ack_facts_id"], verified.as_dict()["id"])
        self.assertEqual(value["submit_observation_id"], self.bundle.as_dict()["id"])
        self.assertEqual(value["ack_outcome"]["evidence_id"], value["ack_facts_id"])
        self.assertIsNone(value["fees_final"])
        self.assertFalse(value["order_terminal_confirmed"] or value["source_authenticated"])
        self.assertFalse(any(value["permissions"].values()))
        with self.assertRaises(FrozenInstanceError): typed._data = b"{}"
        value["order"]["asset_code"] = "US.OTHER"
        self.assertEqual(typed.as_dict()["order"], self.profile.as_dict()["order"])
        with self.assertRaisesRegex(identity.AcknowledgedOrderError, "private_factory"):
            identity.VerifiedAcknowledgedOrder(b"{}", object())
        self.assertEqual(self.store.read(), before)
        self.assertEqual(self.store.path.read_bytes(), database)

    def test_reopen_uses_original_chain_after_expiry_without_clock_or_refresh(self):
        self.acknowledge()
        original = self.store.read_acknowledged_order(self.profile).as_dict()
        before, database = self.store.read(), self.store.path.read_bytes()
        root = self.store.root.parent
        self.store.close()
        reopened = journal.BrokerExecutionJournal(root, mode="OFFICIAL_SIMULATION", account_id="900000000000001",
            record_domain="SYNTHETIC_TEST", clock=lambda: (_ for _ in ()).throw(AssertionError("no new clock")))
        self.h.h.instances.append(reopened)
        self.h.h.now += timedelta(days=1)
        restored = reopened.read_acknowledged_order(self.profile)
        self.assertEqual(restored.as_dict(), original)
        self.assertEqual(identity.validate_acknowledged_order(self.profile, restored, self.codec.session_binding()), original)
        self.assertEqual(reopened.read(), before)
        self.assertEqual(reopened.path.read_bytes(), database)

    def test_pure_validator_rejects_dict_and_matches_same_session_before_and_after_adoption(self):
        self.acknowledge(); typed = self.store.read_acknowledged_order(self.profile)
        with self.assertRaisesRegex(identity.AcknowledgedOrderError, "typed_inputs"):
            identity.validate_acknowledged_order(self.profile, typed.as_dict(), self.codec.session_binding())
        session = self.codec.session_binding().as_dict()
        arguments = {key: session[key] for key in ("client_version", "client_id", "quote_connection_id", "quote_user_id",
                                                  "trade_connection_id", "trade_user_id", "broker_order_id")}
        with patch("sqlite3.connect", side_effect=AssertionError("pure validator must not read the journal")):
            self.assertEqual(identity.validate_acknowledged_order(self.profile, typed, self.codec.session_binding())["broker_order_id"], ORDER)
            adopted = codec.bind_codec_session(self.profile, **{**arguments, "broker_order_id": ORDER})
            self.assertNotEqual(adopted.as_dict()["id"], session["id"])
            self.assertEqual(identity.validate_acknowledged_order(self.profile, typed, adopted)["id"], typed.as_dict()["id"])
            for key, changed in (("quote_connection_id", 12), ("trade_connection_id", 34), ("quote_user_id", 23),
                    ("trade_user_id", 23), ("client_id", "another-client"), ("client_version", 101), ("broker_order_id", "another-order")):
                current = codec.bind_codec_session(self.profile, **{**arguments, key: changed})
                with self.subTest(key=key), self.assertRaises(identity.AcknowledgedOrderError):
                    identity.validate_acknowledged_order(self.profile, typed, current)

    def test_bare_ack_outcome_does_not_authorize_any_new_v3_followup(self):
        self.h.h.outcome(self.store, {"receipt": self.submitted}, broker_id=ORDER)
        before = self.store.read()
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.subTest(action=action), self.assertRaisesRegex(journal.JournalError, "verified_acknowledged_order_required"):
                self.followup(action)
        self.assertEqual(self.store.read(), before)

    def test_frozen_base_v3_followup_remains_readable_but_cannot_admit_another_action(self):
        # This ACTION was produced by the actual BrokerExecutionJournal from
        # commit 1f04c393f4e6e463abb75b7e05b7e5bc50feae0f in a new TEMP store.
        # Original source SHA256: 67da6b5f4d16c448f6922d570c542a62f507ba015349ddc3bb141800bc6efc8d.
        # Reconstruct its immutable payload from the golden profile, then check
        # all 14996 canonical bytes by the independently frozen original hash.
        # The current implementation never creates this historical ACTION.
        self.h.h.outcome(self.store, {"receipt": self.submitted}, broker_id=ORDER)
        prefix = self.store.read()
        self.assertEqual(prefix["event_count"], 16)
        self.assertEqual(prefix["head"], "1517d98afc1362e203585d5e9ec88ca43fc9bfe64b1f415e4b2a9a27ff5220ee")
        self.assertEqual(sha256(self.profile._data).hexdigest(), "bbc321332c7cd3730e350ecb41310c9f8b18e25ee8fe1618c772b0e58e0e2029")
        operation = "synthetic-trade_observe-0018"
        event = {"schema_version": "hakimi-broker-execution-journal-v2", "seq": 17,
            "previous": "1517d98afc1362e203585d5e9ec88ca43fc9bfe64b1f415e4b2a9a27ff5220ee",
            "at": "2026-10-30T08:00:12+00:00", "kind": "ACTION", "request_id": operation,
            "request_hash": "2b6e4a261f4f500e6608af2561efb37cc360aa66c058dd82fe8bdf2b6a1bcc92",
            "payload": {"profile": self.profile.as_dict(), "action": "trade_observe", "operation_id": operation,
                "frame_sha256": "a" * 64, "frame_bytes": 100, "authorization_id": AUTHORIZATION_REFERENCE,
                "broker_order_id": ORDER},
            "result": {"status": "DISPATCH_INTENT", "operation_id": operation, "action": "trade_observe",
                "attempt_count": 1, "dispatch_authorization_granted": False},
            "id": "3121b3ad0eb3ecd91d1a5f4e5dc82d879ce319b7ee6cb3bb8678d881c95973e3"}
        original_bytes = contract.canonical_bytes(event)
        self.assertEqual(len(original_bytes), 14996)
        self.assertEqual(sha256(original_bytes).hexdigest(), "7106299471b3a9680a1d776dde1f58284149d182600919620aa495a66cb6972e")
        with self.store._database(write=True) as connection:
            connection.execute("INSERT INTO events VALUES(?,?,?)", (event["seq"], operation, original_bytes))
            connection.execute("UPDATE metadata SET head_seq=?,head_hash=? WHERE singleton=1", (event["seq"], event["id"]))
            connection.commit()
        before, database = self.store.read(), self.store.path.read_bytes()
        self.assertEqual(self.store.read(operation)["receipt"], event)
        def forbidden_barrier():
            raise AssertionError("historical replay must return before new admission")
        recovered = self.store.begin_action(self.profile, "trade_observe", request_id=operation,
            frame_sha256="a" * 64, frame_bytes=100, authorization_id=AUTHORIZATION_REFERENCE,
            broker_order_id=ORDER, control_barrier=forbidden_barrier)
        self.assertTrue(recovered["replayed"])
        self.assertEqual(recovered["receipt"], event)
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        with self.assertRaisesRegex(journal.JournalError, "verified_acknowledged_order_required"):
            self.followup("trade_fees")
        self.assertEqual(self.store.read(), before)
        self.assertEqual(self.store.path.read_bytes(), database)

    def test_valid_ack_allows_original_v3_followups_without_extending_observation_window(self):
        self.acknowledge()
        typed = self.store.read_acknowledged_order(self.profile)
        self.codec.accept_acknowledged_order(self.profile, typed)
        self.h.h.now = contract._time(self.bundle.as_dict()["expires_at"]) + timedelta(seconds=1)
        before = self.store.read()["financial"]
        for serial, action in enumerate(("trade_observe", "trade_cancel", "trade_fees"), 80):
            frame = self.codec.encode_request(self.profile, action, serial)
            receipt = self.store.begin_action(self.profile, action, request_id=self.h.h.request(action),
                frame_sha256=sha256(frame).hexdigest(), frame_bytes=len(frame), authorization_id=AUTHORIZATION_REFERENCE,
                broker_order_id=ORDER, control_barrier=lambda: self.h.h.barrier(self.profile))["receipt"]
            self.assertEqual(receipt["payload"]["broker_order_id"], ORDER)
            self.assertNotIn("acknowledged_order", receipt["payload"])
        self.assertEqual(self.store.read_acknowledged_order(self.profile).as_dict(), typed.as_dict())
        self.assertEqual(self.store.read()["financial"], before)

    def test_wrong_account_response_or_security_request_never_becomes_ack_identity(self):
        before = self.store.read()
        with self.assertRaises(ValueError):
            self.response(header={"trdEnv": 0, "accID": 900000000000002, "trdMarket": 2})
        changed = json.loads(self.frame[44:]); changed["c2s"]["code"] = "OTHER"
        with self.assertRaises(ValueError):
            self.response(request_frame=codec.pack_plaintext_frame(2202, 77, encode(changed)))
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        self.assertEqual(self.store.read(), before)

    def test_other_profile_intent_does_not_receive_original_identity(self):
        self.acknowledge(); typed = self.store.read_acknowledged_order(self.profile)
        other = fixture.make_profile(side="SELL")
        self.assertNotEqual(other.as_dict()["deduplication"]["intent_scope_id"], self.profile.as_dict()["deduplication"]["intent_scope_id"])
        self.assertIsNone(self.store.read_acknowledged_order(other))
        with self.assertRaisesRegex(identity.AcknowledgedOrderError, "profile_scope_changed"):
            identity.validate_acknowledged_order(other, typed, self.codec.session_binding())

    def test_conflicting_ack_is_an_explicit_error_and_blocks_transaction_followups(self):
        self.acknowledge()
        prior = self.store.read()
        self.h.h.now += timedelta(seconds=1)
        _, conflict = self.acknowledge(order="another-original-order")
        self.assertEqual(conflict["result"]["disposition"], "CONFLICT_RETAINED")
        before = self.store.read()
        self.assertEqual(before["financial"]["cash_reserved"], prior["financial"]["cash_reserved"])
        with self.assertRaisesRegex(identity.AcknowledgedOrderError, "ack_identity_conflict"):
            self.store.read_acknowledged_order(self.profile)
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.subTest(action=action), self.assertRaises(identity.AcknowledgedOrderError):
                self.followup(action)
        self.assertEqual(self.store.read(), before)

    def test_consistent_reprojection_keeps_original_canonical_identity(self):
        self.acknowledge(); original = self.store.read_acknowledged_order(self.profile).as_dict()
        self.h.h.now += timedelta(seconds=1)
        _, duplicate = self.acknowledge()
        self.assertEqual(duplicate["result"]["disposition"], "FACTS_ONLY")
        self.assertEqual(self.store.read_acknowledged_order(self.profile).as_dict(), original)

    def test_unknown_then_verified_late_ack_retains_unknown_history_and_reservations(self):
        original = {"status": "UNKNOWN", "evidence_id": "c" * 64, "sent_bytes": 5,
            "possible_sent_bytes": len(self.frame), "frame_bytes": len(self.frame), "broker_order_id": None,
            "write_attempted": True, "response_complete": False}
        self.store.outcome(self.submitted["request_id"], original, request_id=self.h.h.request("unknown"))
        before = self.store.read()
        self.assertIsNone(self.store.read_acknowledged_order(self.profile))
        verified = self.response()
        self.store.record_verified_response(verified, request_id=self.h.h.request("late-ack"), previous_evidence_id=original["evidence_id"])
        after = self.store.read()
        operation = after["actions"][self.submitted["request_id"]]
        self.assertEqual(operation["outcome_history"][0], original)
        self.assertEqual(len(operation["outcome_history"]), 2)
        self.assertEqual(after["financial"], before["financial"])
        self.assertEqual(self.store.read_acknowledged_order(self.profile).as_dict()["broker_order_id"], ORDER)

    def test_fee_unknown_and_unrelated_account_reconciliation_do_not_hide_order_identity(self):
        self.acknowledge(); original = self.store.read_acknowledged_order(self.profile).as_dict()
        self.h.h.observe(self.store, self.profile, quantity=1, notional="25", broker_id=ORDER)
        before = self.store.read()
        self.assertTrue(before["financial"]["reconciliation_required"])
        self.assertIsNone(next(iter(before["claims"].values()))["fees"])
        self.assertEqual(self.store.read_acknowledged_order(self.profile).as_dict(), original)
        self.assertEqual(self.store.read(), before)

    def test_shared_order_ownership_conflict_is_rejected_by_read_factory(self):
        self.acknowledge()
        with self.store._database() as connection:
            state, receipts, _ = self.store._load(connection)
        intent = self.profile.as_dict()["deduplication"]["intent_scope_id"]
        state["claims"]["f" * 64] = deepcopy(state["claims"][intent])
        with self.assertRaisesRegex(identity.AcknowledgedOrderError, "shared_ownership_conflict"):
            identity._acknowledged_order_from_state(self.profile.as_dict(), state, receipts)

    def test_v2_original_read_and_bare_outcome_followup_contract_remain_unchanged(self):
        legacy = self.h.h.profile()
        store = self.h.store(); self.h.h.seed(store)
        self.h.h.claim(store, legacy)
        action = self.h.h.begin(store, legacy)
        self.h.h.outcome(store, action, broker_id=ORDER)
        before = store.read()
        self.assertIsNone(store.read_acknowledged_order(legacy))
        self.assertEqual(store.read(), before)
        self.assertNotIn("_receipt_history", before)
        followup = self.h.h.begin(store, legacy, "trade_observe", broker_order_id=ORDER)
        self.assertNotIn("acknowledged_order", followup["receipt"]["payload"])


if __name__ == "__main__":
    unittest.main()
