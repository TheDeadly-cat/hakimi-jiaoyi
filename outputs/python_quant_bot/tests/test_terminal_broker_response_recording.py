"""New synthetic stores only; protobuf-shaped fixtures are not SDK proof."""
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_response_facts as verifier
import tests.test_terminal_broker_execution_journal as jf
import tests.test_futu_us_equity_simulate_wire_v2 as cf


class ResponseRecordingTests(unittest.TestCase):
    def setUp(self):
        self.helper = jf.JournalTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.store = self.helper.store()
        self.profile = self.helper.profile()
        self.helper.seed(self.store)
        self.codec = cf.make_codec(self.profile)
        self.header = {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2}

    def action(self, name="trade_submit"):
        if name == "trade_submit":
            self.helper.claim(self.store, self.profile)
        payload = cf.request_payload(name)
        if name == "trade_submit":
            payload["c2s"]["price"] = 20.0
        request = cf.request_frame(name, payload=payload)
        changes = {"frame_sha256": sha256(request).hexdigest(), "frame_bytes": len(request)}
        if name in ("trade_cancel", "trade_observe", "trade_fees"):
            changes["broker_order_id"] = "fictional-order-44"
        action = self.helper.begin(self.store, self.profile, name, **changes)["receipt"]
        return action, request

    def facts(self, original, *, payload=None):
        action, request = original
        payload = payload or {"retType": 0, "s2c": {"header": deepcopy(self.header),
                                                   "orderIDEx": "fictional-order-44"}}
        return verifier.verify_response_facts(profile=self.profile, codec=self.codec,
            action_receipt=action, expected_action_receipt_id=action["id"], request_frame=request,
            response_frame=cf.response_frame(action["payload"]["action"], payload=payload),
            received_at=self.helper.now)

    def record(self, facts, **changes):
        args = {"request_id": self.helper.request("verified-response")}
        args.update(changes)
        return self.store.record_verified_response(facts, **args)

    def claim(self):
        return self.store.read()["claims"][self.profile.as_dict()["deduplication"]["intent_scope_id"]]

    def acknowledge(self):
        original = self.action()
        facts = self.facts(original)
        self.record(facts)
        return original

    def test_submit_ack_retains_complete_facts_and_never_creates_fill_or_releases_reserve(self):
        original = self.action()
        before = self.store.read()["financial"]
        facts = self.facts(original)
        result = self.record(facts)
        self.assertEqual(result["receipt"]["kind"], "VERIFIED_RESPONSE")
        self.assertEqual(result["receipt"]["result"]["disposition"], "ACKNOWLEDGED")
        view = self.store.read()
        self.assertEqual(view["financial"], before)
        self.assertEqual(view["response_facts"][facts.as_dict()["id"]], facts.as_dict())
        self.assertEqual(self.claim()["broker_order_id"], "fictional-order-44")
        self.assertEqual(self.claim()["filled_quantity"], 0)
        self.assertIsNone(self.claim()["fees"])
        self.assertFalse(self.claim()["fees_final"])
        outcome = view["actions"][original[0]["request_id"]]["outcome"]
        self.assertEqual(outcome["sent_bytes"], 0)
        self.assertEqual(outcome["possible_sent_bytes"], len(original[1]))
        self.assertEqual(len(view["actions"]), 1)
        self.assertFalse(any(view["permissions"].values()))

    def test_cancel_ack_is_not_terminal_and_reserve_is_unchanged(self):
        self.acknowledge()
        before = self.store.read()["financial"]
        self.record(self.facts(self.action("trade_cancel")))
        self.assertTrue(self.claim()["cancel_acknowledged"])
        self.assertEqual(self.claim()["order_state"], "OPEN")
        self.assertEqual(self.store.read()["financial"], before)

    def test_api_error_stays_unknown_not_rejected_or_zero_fee(self):
        facts = self.facts(self.action(), payload={"retType": -1, "retMsg": "synthetic error"})
        result = self.record(facts)
        self.assertEqual(result["receipt"]["result"]["disposition"], "UNKNOWN")
        self.assertEqual(self.claim()["state"], "UNKNOWN")
        self.assertEqual(self.claim()["order_state"], "OPEN")
        self.assertEqual(self.store.read()["financial"]["cash_reserved"], "61.50")
        self.assertIsNone(self.claim()["fees"])

    def test_missing_order_id_stays_unknown_and_reserves_all(self):
        facts = self.facts(self.action(), payload={"retType": 0, "s2c": {"header": self.header}})
        self.record(facts)
        self.assertEqual(self.claim()["state"], "UNKNOWN")
        self.assertIsNone(self.claim()["broker_order_id"])
        self.assertEqual(self.store.read()["financial"]["cash_reserved"], "61.50")

    def test_funds_read_is_archived_without_replacing_cash_or_marking_dispatch_ack(self):
        original = self.action("trade_funds")
        before = self.store.read()["financial"]
        facts = self.facts(original, payload={"retType": 0, "s2c": {"header": self.header,
            "funds": {"currency": 2, "cash": 2000., "availableFunds": 1000., "power": 4000., "frozenCash": 20.}}})
        result = self.record(facts)
        self.assertEqual(result["receipt"]["result"]["disposition"], "FACTS_ONLY")
        view = self.store.read()
        self.assertEqual(view["financial"], before)
        self.assertIsNone(view["actions"][original[0]["request_id"]]["outcome"])
        self.assertEqual(view["observation_ids"], [])

    def test_filled_order_row_and_fee_row_never_release_cash_or_create_economic_observation(self):
        self.acknowledge()
        before = self.store.read()["financial"]
        rows = {"trade_observe": {"orderList": [{"orderIDEx": "fictional-order-44", "code": "TSLA",
            "trdSide": 1, "orderType": 1, "secMarket": 2, "currency": 2, "qty": 3., "price": 20.,
            "fillQty": 3., "fillAvgPrice": 19., "orderStatus": 11}]},
            "trade_fees": {"orderFeeList": [{"orderIDEx": "fictional-order-44", "feeAmount": 0.}]}}
        for action, fields in rows.items():
            facts = self.facts(self.action(action), payload={"retType": 0,
                "s2c": {"header": self.header, **fields}})
            self.record(facts)
        view = self.store.read()
        self.assertEqual(view["financial"], before)
        self.assertEqual(view["observation_ids"], [])
        self.assertEqual(self.claim()["filled_quantity"], 0)
        self.assertIsNone(self.claim()["fees"])
        self.assertFalse(self.claim()["fees_final"])

    def test_second_different_ack_id_is_retained_as_conflict_and_never_rebinds_order(self):
        original = self.acknowledge()
        facts = self.facts(original, payload={"retType": 0, "s2c": {"header": self.header,
                                                                  "orderIDEx": "different-opaque-order"}})
        result = self.record(facts)
        self.assertEqual(result["receipt"]["result"]["disposition"], "CONFLICT_RETAINED")
        self.assertEqual(self.claim()["broker_order_id"], "fictional-order-44")
        self.assertTrue(self.store.read()["financial"]["reconciliation_required"])
        self.assertEqual(len(self.store.read()["actions"]), 1)

    def test_conflicting_observed_fill_blocks_risk_without_inventing_exact_notional(self):
        self.acknowledge()
        facts = self.facts(self.action("trade_observe"), payload={"retType": 0, "s2c": {"header": self.header,
            "orderList": [{"orderIDEx": "fictional-order-44", "code": "TSLA", "trdSide": 1,
                "orderType": 1, "secMarket": 2, "currency": 2, "qty": 3., "price": 20.,
                "fillQty": 4., "fillAvgPrice": 19., "orderStatus": 11}]}})
        self.assertTrue(facts.as_dict()["needs_reconciliation"])
        result = self.record(facts)
        self.assertTrue(result["receipt"]["result"]["reconciliation_required"])
        self.assertIn("RESPONSE_FACTS_REQUIRE_RECONCILIATION", self.store.read()["financial"]["reasons"])
        self.assertEqual(self.claim()["filled_quantity"], 0)
        self.assertEqual(self.claim()["filled_notional"], "0")

    def test_plausible_late_fill_after_terminal_and_rebase_blocks_new_risk(self):
        self.acknowledge()
        original = self.action("trade_observe")
        self.helper.observe(self.store, self.profile, fees="0", final=True, state="CANCELLED",
                            broker_id="fictional-order-44")
        self.helper.seed(self.store, evidence="b" * 64)
        facts = self.facts(original, payload={"retType": 0, "s2c": {"header": self.header,
            "orderList": [{"orderIDEx": "fictional-order-44", "code": "TSLA", "trdSide": 1,
                "orderType": 1, "secMarket": 2, "currency": 2, "qty": 3., "price": 20.,
                "fillQty": 1., "fillAvgPrice": 19., "orderStatus": 10}]}})
        self.assertFalse(facts.as_dict()["needs_reconciliation"])
        self.record(facts)
        view = self.store.read()
        self.assertIn("RESPONSE_FILL_CHANGED_AFTER_TERMINAL_OR_REBASE", view["financial"]["reasons"])
        self.assertEqual(self.claim()["filled_quantity"], 0)
        self.assertEqual(view["financial"]["cash_available_after_local_liabilities"], "100")
        with self.assertRaisesRegex(journal.JournalError, "reconciliation_required"):
            self.helper.claim(self.store, self.helper.profile(tag="next"), evidence_id="b" * 64)

    def test_late_fee_change_after_final_fee_blocks_risk_without_rewriting_cash(self):
        self.acknowledge()
        original = self.action("trade_fees")
        self.helper.observe(self.store, self.profile, fees="0", final=True, state="CANCELLED",
                            broker_id="fictional-order-44")
        before = self.store.read()["financial"]["cash_available_after_local_liabilities"]
        facts = self.facts(original, payload={"retType": 0, "s2c": {"header": self.header,
            "orderFeeList": [{"orderIDEx": "fictional-order-44", "feeAmount": 0.5}]}})
        self.record(facts)
        view = self.store.read()
        self.assertIn("RESPONSE_FEE_CONFLICTS_WITH_RECORDED_TOTAL", view["financial"]["reasons"])
        self.assertEqual(view["financial"]["cash_available_after_local_liabilities"], before)
        self.assertEqual(self.claim()["fees"], "0")

    def test_source_average_outside_limit_blocks_risk_without_becoming_notional(self):
        self.acknowledge()
        facts = self.facts(self.action("trade_observe"), payload={"retType": 0, "s2c": {"header": self.header,
            "orderList": [{"orderIDEx": "fictional-order-44", "code": "TSLA", "trdSide": 1,
                "orderType": 1, "secMarket": 2, "currency": 2, "qty": 3., "price": 20.,
                "fillQty": 1., "fillAvgPrice": 21., "orderStatus": 10}]}})
        self.record(facts)
        self.assertIn("RESPONSE_FILL_PRICE_OUTSIDE_LIMIT", self.store.read()["financial"]["reasons"])
        self.assertEqual(self.claim()["filled_notional"], "0")

    def test_late_ack_requires_original_unknown_reference_and_appends_without_resend(self):
        original = self.action()
        unknown = self.facts(original, payload={"retType": -1})
        first = self.record(unknown)
        self.helper.now = datetime.fromisoformat(self.profile.as_dict()["wire_bounds"]["valid_until"]) + timedelta(seconds=1)
        ack = self.facts(original)
        self.assertTrue(ack.as_dict()["received_after_profile_expiry"])
        with self.assertRaisesRegex(journal.JournalError, "previous_unknown_required"):
            self.record(ack)
        self.record(ack, previous_evidence_id=unknown.as_dict()["id"])
        view = self.store.read(first["receipt"]["request_id"])
        self.assertEqual(view["receipt"], first["receipt"])
        action = view["actions"][original[0]["request_id"]]
        self.assertEqual([x["status"] for x in action["outcome_history"]], ["UNKNOWN", "ACKNOWLEDGED"])
        self.assertEqual(len(view["actions"]), 1)
        self.assertEqual(len(view["response_facts"]), 2)
        self.assertEqual(view["financial"]["cash_reserved"], "61.50")

    def test_original_known_write_count_is_preserved_when_late_ack_arrives(self):
        original = self.action()
        unknown = {"status": "UNKNOWN", "evidence_id": "d" * 64, "sent_bytes": 7,
            "possible_sent_bytes": len(original[1]), "frame_bytes": len(original[1]),
            "broker_order_id": None, "write_attempted": True, "response_complete": False}
        self.store.outcome(original[0]["request_id"], unknown, request_id=self.helper.request())
        self.record(self.facts(original), previous_evidence_id="d" * 64)
        outcome = self.store.read()["actions"][original[0]["request_id"]]["outcome"]
        self.assertEqual(outcome["sent_bytes"], 7)

    def test_foreign_self_sealed_action_and_raw_dict_cannot_enter_this_journal(self):
        original = self.action()
        forged = deepcopy(original[0])
        forged["request_id"] = forged["payload"]["operation_id"] = forged["result"]["operation_id"] = "foreign-action-0001"
        forged["request_hash"] = journal.contract.digest({"kind": "ACTION", "payload": forged["payload"]})
        forged = jf.seal(forged)
        facts = self.facts((forged, original[1]))
        before = self.helper.inventory()
        with self.assertRaisesRegex(journal.JournalError, "original_action_mismatch"):
            self.record(facts)
        with self.assertRaisesRegex(journal.JournalError, "typed_response_facts_required"):
            self.record(self.facts(original).as_dict())
        self.assertEqual(self.helper.inventory(), before)

    def test_idempotent_receipt_read_and_reopen_create_no_new_action_or_record(self):
        original = self.action()
        facts = self.facts(original)
        request_id = self.helper.request()
        first = self.record(facts, request_id=request_id)
        before = self.helper.inventory()
        self.assertTrue(self.record(facts, request_id=request_id)["replayed"])
        reopened = self.helper.store()
        self.assertEqual(reopened.read(request_id)["receipt"], first["receipt"])
        self.assertEqual(len(reopened.read()["actions"]), 1)
        self.assertEqual(self.helper.inventory(), before)
        with self.assertRaisesRegex(journal.JournalError, "already_recorded"):
            self.record(facts)

    def test_lost_local_commit_ack_is_recovered_by_same_request_only(self):
        facts = self.facts(self.action())
        request_id = self.helper.request()
        commit = self.store._commit
        def committed_then_lost(connection):
            commit(connection)
            raise OSError("synthetic lost local acknowledgement")
        with patch.object(self.store, "_commit", side_effect=committed_then_lost):
            with self.assertRaises(OSError):
                self.record(facts, request_id=request_id)
        first = self.store.read(request_id)["receipt"]
        replay = self.record(facts, request_id=request_id)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"], first)
        self.assertEqual(len(self.store.read()["actions"]), 1)

    def test_contradictory_ack_is_retained_and_blocks_new_claims_without_rewriting_outcome(self):
        original = self.action()
        self.store.outcome(original[0]["request_id"], {"status": "NOT_DISPATCHED", "evidence_id": "e" * 64,
            "sent_bytes": 0, "possible_sent_bytes": 0, "frame_bytes": len(original[1]), "broker_order_id": None,
            "write_attempted": False, "response_complete": False}, request_id=self.helper.request())
        facts = self.facts(original)
        result = self.record(facts)
        self.assertEqual(result["receipt"]["result"]["disposition"], "CONFLICT_RETAINED")
        view = self.store.read()
        self.assertEqual(view["actions"][original[0]["request_id"]]["outcome"]["status"], "NOT_DISPATCHED")
        self.assertIn(facts.as_dict()["id"], view["response_facts"])
        self.assertIn("MATCHED_ACK_CONFLICTS_WITH_RECORDED_OUTCOME", view["financial"]["reasons"])
        self.assertTrue(view["financial"]["reconciliation_required"])

    def test_future_received_time_is_rejected_without_mutating_store(self):
        original = self.action()
        self.helper.now += timedelta(seconds=2)
        facts = self.facts(original)
        self.helper.now -= timedelta(seconds=2)
        before = self.helper.inventory()
        with self.assertRaisesRegex(journal.JournalError, "observation_time_invalid"):
            self.record(facts)
        self.assertEqual(self.helper.inventory(), before)


if __name__ == "__main__":
    unittest.main()
