"""Synthetic protobuf-shaped facts only; no SDK/provider or business store.

Frames use the existing explicit fake protobuf classes and real frame/receipt
binding code. This is not actual protobuf or installed SDK compatibility proof.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_response_facts as facts_module
from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_execution_plan as contract
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_terminal_broker_wire_profile import fixture as wire_fixture, NOW
from tests.test_terminal_broker_execution_plan import config
from tests.test_futu_us_equity_simulate_wire_v2 import (
    make_profile, make_codec, request_payload, request_frame, response_frame, Response,
)


ACCOUNT = 900000000000001
ORDER_ID = "fictional-order-44"  # Deliberately opaque; never coerce to numeric ID.


def header():
    return {"trdEnv": 0, "accID": ACCOUNT, "trdMarket": 2}


def order_row():
    return {"trdSide": 1, "orderType": 1, "orderStatus": 10, "orderID": 44, "orderIDEx": ORDER_ID,
            "code": "TSLA", "name": "FICTIONAL", "qty": 3.0, "price": 20.00000001,
            "createTime": "2026-10-30 04:00:00", "updateTime": "2026-10-30 04:00:01",
            "fillQty": 1.0, "fillAvgPrice": 20.0, "secMarket": 2, "currency": 2,
            "trdMarket": 2, "timeInForce": 0, "fillOutsideRTH": False, "session": 1}


def position_row():
    return {"positionID": 99, "positionSide": 0, "code": "TSLA", "name": "FICTIONAL",
            "qty": 4.5, "canSellQty": 4.0, "price": 20.0, "val": 90.0, "plVal": 4.5, "plRatio": 0.05,
            "secMarket": 2, "currency": 2, "trdMarket": 2, "accID": ACCOUNT}


def response_payload(action):
    bodies = {
        "trade_submit": {"header": header(), "orderIDEx": ORDER_ID},
        "trade_cancel": {"header": header(), "orderID": 0, "orderIDEx": ORDER_ID},
        "trade_observe": {"header": header(), "orderList": [order_row()]},
        "trade_accounts": {"accList": [
            {"accID": 9876, "trdEnv": 1, "trdMarketAuthList": [1]},
            {"accID": ACCOUNT, "trdEnv": 0, "trdMarketAuthList": [1, 2], "securityFirm": 2, "accStatus": 0}]},
        "trade_funds": {"header": header(), "funds": {"power": 1000.0, "totalAssets": 2000.0,
            "cash": 500.0, "marketVal": 0.0, "frozenCash": 10.0, "debtCash": 0.0,
            "avlWithdrawalCash": 500.0, "currency": 2, "availableFunds": 400.0}},
        "trade_positions": {"header": header(), "positionList": [position_row()]},
        "trade_fees": {"header": header(), "orderFeeList": [{"orderIDEx": ORDER_ID,
            "feeAmount": 0.0, "feeList": [{"title": "synthetic fixture fee", "value": 0.0}]}]},
    }
    return {"retType": 0, "s2c": deepcopy(bodies[action])}


def action_receipt(profile, action, frame, *, broker_order_id=None):
    request_id = "facts-action-" + action.replace("_", "-") + "-0001"
    payload = {"profile": profile.as_dict(), "action": action, "operation_id": request_id,
               "frame_sha256": sha256(frame).hexdigest(), "frame_bytes": len(frame),
               "authorization_id": "b" * 64, "broker_order_id": broker_order_id}
    return journal.seal({"schema_version": journal.SCHEMA, "seq": 2, "previous": "c" * 64,
        "at": NOW.isoformat(), "kind": "ACTION", "payload": payload, "request_id": request_id,
        "request_hash": contract.digest({"kind": "ACTION", "payload": payload}),
        "result": {"status": "DISPATCH_INTENT", "operation_id": request_id, "action": action,
                   "attempt_count": 1, "dispatch_authorization_granted": False}})


def facts_fixture(action="trade_submit", *, response=None, profile=None, request=None):
    profile = profile or make_profile()
    codec = make_codec(profile)
    request = request_payload(action) if request is None else request
    frame = request_frame(action, payload=request)
    original_id = ORDER_ID if action in ("trade_cancel", "trade_observe", "trade_fees") else None
    receipt = action_receipt(profile, action, frame, broker_order_id=original_id)
    return {"profile": profile, "codec": codec, "action_receipt": receipt,
            "expected_action_receipt_id": receipt["id"], "request_frame": frame,
            "response_frame": response_frame(action, payload=response if response is not None else response_payload(action)),
            "received_at": NOW + timedelta(seconds=1)}


def reseal_event(args):
    body = {key: value for key, value in args["action_receipt"].items() if key != "id"}
    body["request_hash"] = contract.digest({"kind": body["kind"], "payload": body["payload"]})
    args["action_receipt"] = journal.seal(body)
    # Only fixtures may explicitly choose a new trusted stored identity.
    args["expected_action_receipt_id"] = args["action_receipt"]["id"]


class ResponseFactsTests(unittest.TestCase):
    def setUp(self):
        for name in ("builtins.open", "socket.socket.connect", "socket.create_connection",
                     "sqlite3.connect", "subprocess.Popen"):
            guard = patch(name, side_effect=AssertionError("Pure facts must not access IO"))
            guard.start()
            self.addCleanup(guard.stop)

    def verify(self, action="trade_submit", **changes):
        return facts_module.verify_response_facts(**facts_fixture(action, **changes)).as_dict()

    def test_submit_ack_binds_original_frames_receipt_and_scopes_without_permissions(self):
        args = facts_fixture()
        result = facts_module.verify_response_facts(**args).as_dict()
        self.assertEqual(result["status"], "ACK_SCOPE_MATCHED")
        self.assertEqual(result["facts"], {"broker_order_id": ORDER_ID, "account_scope_matched": True,
                                          "order_terminal_confirmed": False, "fees_final": None})
        self.assertEqual(result["journal_receipt_id"], args["action_receipt"]["id"])
        self.assertEqual(result["request_frame"], {"sha256": sha256(args["request_frame"]).hexdigest(),
                                                 "bytes": len(args["request_frame"])})
        self.assertEqual(result["response_frame"]["sha256"], sha256(args["response_frame"]).hexdigest())
        self.assertEqual(result["account_scope_id"], args["profile"].as_dict()["deduplication"]["account_scope_id"])
        self.assertTrue(result["test_only"])
        self.assertFalse(result["source_authenticated"])
        self.assertTrue(result["research_eligibility"]["offline_only"])
        self.assertFalse(result["journal_observation_ready"])
        self.assertFalse(result["reservation_ready"])
        self.assertEqual(result["permissions"], dict(contract.PERMISSIONS))

    def test_private_facts_factory_and_copies_are_immutable(self):
        value = facts_module.verify_response_facts(**facts_fixture())
        original = value.as_dict()
        with self.assertRaises(FrozenInstanceError):
            value._data = b"{}"
        with self.assertRaises(facts_module.ResponseFactsError):
            facts_module.VerifiedResponseFacts(b"{}", object())
        copy = value.as_dict()
        copy["permissions"]["submit_allowed"] = True
        copy["facts"]["broker_order_id"] = "replacement"
        self.assertEqual(value.as_dict(), original)

    def test_typed_profile_codec_original_bytes_and_trusted_event_id_are_required(self):
        for key, replacement in (("profile", {}), ("codec", object()), ("request_frame", {}),
                                 ("response_frame", {"retType": 0}), ("expected_action_receipt_id", True)):
            args = facts_fixture()
            args[key] = replacement
            with self.subTest(key=key), self.assertRaises(facts_module.ResponseFactsError):
                facts_module.verify_response_facts(**args)
        args = facts_fixture()
        args["action_receipt"]["at"] = (NOW + timedelta(microseconds=1)).isoformat()
        body = {k: v for k, v in args["action_receipt"].items() if k != "id"}
        args["action_receipt"] = journal.seal(body)
        with self.assertRaisesRegex(facts_module.ResponseFactsError, "receipt_identity"):
            facts_module.verify_response_facts(**args)

    def test_event_schema_kind_result_hash_and_request_identity_are_not_self_attested(self):
        mutations = [lambda e: e.update(schema_version="wrong"), lambda e: e.update(kind="OUTCOME"),
                     lambda e: e.update(seq=True), lambda e: e.update(previous="not-hash"),
                     lambda e: e["payload"].update(operation_id="other-request-0001"),
                     lambda e: e["result"].update(operation_id="other-request-0001"),
                     lambda e: e["result"].update(dispatch_authorization_granted=True),
                     lambda e: e["result"].update(attempt_count=True),
                     lambda e: e["result"].update(status="ACKNOWLEDGED")]
        for mutate in mutations:
            args = facts_fixture()
            mutate(args["action_receipt"])
            reseal_event(args)
            with self.subTest(mutation=mutate), self.assertRaises(facts_module.ResponseFactsError):
                facts_module.verify_response_facts(**args)
        args = facts_fixture()
        args["action_receipt"]["request_hash"] = "0" * 64
        args["action_receipt"] = journal.seal({k: v for k, v in args["action_receipt"].items() if k != "id"})
        args["expected_action_receipt_id"] = args["action_receipt"]["id"]
        with self.assertRaisesRegex(facts_module.ResponseFactsError, "request_hash"):
            facts_module.verify_response_facts(**args)

    def test_original_request_frame_length_digest_and_actual_codec_are_checked(self):
        for change in (lambda a: a.update(request_frame=request_frame("trade_submit", serial=2)),
                       lambda a: a["action_receipt"]["payload"].update(frame_bytes=True),
                       lambda a: a["action_receipt"]["payload"].update(frame_sha256="0" * 64)):
            args = facts_fixture()
            change(args)
            reseal_event(args)
            with self.assertRaises(facts_module.ResponseFactsError):
                facts_module.verify_response_facts(**args)
        args = facts_fixture()
        args["codec"]._requests[2202] = Response
        with self.assertRaises(facts_module.ResponseFactsError):
            facts_module.verify_response_facts(**args)

    def test_response_protocol_serial_hash_partial_and_duplicate_frames_are_rejected(self):
        for replace in (lambda frame: frame + frame, lambda frame: frame[:-1],
                        lambda frame: frame[:16] + bytes([frame[16] ^ 1]) + frame[17:],
                        lambda _: response_frame("trade_submit", serial=2),
                        lambda _: response_frame("trade_cancel")):
            args = facts_fixture()
            args["response_frame"] = replace(args["response_frame"])
            with self.assertRaises(facts_module.ResponseFactsError):
                facts_module.verify_response_facts(**args)

    def test_ack_header_environment_account_market_bool_and_missing_id_do_not_pass(self):
        for key, replacement in (("trdEnv", 1), ("trdEnv", False), ("accID", ACCOUNT + 1),
                                 ("accID", True), ("trdMarket", 1)):
            response = response_payload("trade_submit")
            response["s2c"]["header"][key] = replacement
            with self.subTest(key=key), self.assertRaises(facts_module.ResponseFactsError):
                self.verify(response=response)
        response = response_payload("trade_submit")
        response["s2c"].pop("orderIDEx")
        response["s2c"]["orderID"] = 44
        result = self.verify(response=response)
        self.assertEqual(result["status"], "INCOMPLETE_EVIDENCE")
        self.assertIsNone(result["facts"]["broker_order_id"])
        for identity in ("", " padded", "id with space", 44, True):
            response = response_payload("trade_submit")
            response["s2c"]["orderIDEx"] = identity
            with self.assertRaises(facts_module.ResponseFactsError):
                self.verify(response=response)

    def test_cancel_ack_only_confirms_exact_original_id_never_terminal_cancellation(self):
        value = self.verify("trade_cancel")
        self.assertEqual(value["status"], "CANCEL_ACK_NOT_TERMINAL")
        self.assertFalse(value["facts"]["order_terminal_confirmed"])
        self.assertIsNone(value["facts"]["fees_final"])
        response = response_payload("trade_cancel")
        response["s2c"]["orderIDEx"] = "foreign-order"
        with self.assertRaises(facts_module.ResponseFactsError):
            self.verify("trade_cancel", response=response)

    def test_original_journal_order_id_must_match_the_actual_decoded_request(self):
        for action in ("trade_cancel", "trade_observe", "trade_fees"):
            args = facts_fixture(action)
            args["action_receipt"]["payload"]["broker_order_id"] = "different-original-order"
            reseal_event(args)
            with self.subTest(action=action), self.assertRaisesRegex(facts_module.ResponseFactsError, "request_order_id"):
                facts_module.verify_response_facts(**args)

    def test_order_list_empty_is_unconfirmed_and_duplicate_or_foreign_rows_reject(self):
        response = response_payload("trade_observe")
        response["s2c"]["orderList"] = []
        result = self.verify("trade_observe", response=response)
        self.assertEqual(result["status"], "NOT_FOUND_UNCONFIRMED")
        self.assertEqual(result["facts"], {})
        for rows in ([order_row(), order_row()], [dict(order_row(), orderIDEx="foreign")],
                     [order_row(), dict(order_row(), orderIDEx="foreign")]):
            response["s2c"]["orderList"] = rows
            with self.assertRaises(facts_module.ResponseFactsError):
                self.verify("trade_observe", response=response)

    def test_order_identity_security_side_quantity_price_and_currency_are_exact(self):
        for key, replacement in (("code", "AMD"), ("trdSide", 2), ("trdSide", True), ("qty", 4.0),
                                 ("qty", True), ("price", 20.00000002), ("orderType", 2),
                                 ("secMarket", 1), ("currency", 1), ("fillOutsideRTH", True)):
            response = response_payload("trade_observe")
            response["s2c"]["orderList"][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(facts_module.ResponseFactsError):
                self.verify("trade_observe", response=response)
        response = response_payload("trade_observe")
        response["s2c"]["orderList"][0].pop("code")
        result = self.verify("trade_observe", response=response)
        self.assertEqual(result["status"], "INCOMPLETE_EVIDENCE")
        self.assertIsNone(result["facts"]["code"])

    def test_missing_cumulative_fields_are_not_zero_and_order_amount_is_not_fill_notional(self):
        response = response_payload("trade_observe")
        row = response["s2c"]["orderList"][0]
        row.pop("fillQty"); row.pop("fillAvgPrice")
        row.update(orderStatus=11, orderAmount=999.0)
        value = self.verify("trade_observe", response=response)
        for key in ("filled_quantity", "fill_average_price", "filled_notional", "fees", "fees_final"):
            self.assertIsNone(value["facts"][key])
        self.assertEqual(value["derived"], {})
        self.assertEqual(value["facts"]["broker_status_name"], "FILLED_ALL")
        self.assertFalse(value["journal_observation_ready"])

    def test_derived_quantity_times_average_is_labelled_estimate_not_source_notional(self):
        value = self.verify("trade_observe")
        self.assertEqual(Decimal(value["derived"]["fill_notional_estimate"]), Decimal(20))
        self.assertFalse(value["derived"]["exact_notional"])
        self.assertIsNone(value["facts"]["filled_notional"])
        self.assertIsNone(value["facts"]["fees_final"])
        response = response_payload("trade_observe")
        response["s2c"]["orderList"][0].update(fillQty=0.0, fillAvgPrice=0.0)
        value = self.verify("trade_observe", response=response)
        self.assertEqual(Decimal(value["facts"]["filled_quantity"]), Decimal(0))
        self.assertIsNone(value["facts"]["filled_notional"])

    def test_conflicting_fill_values_are_retained_flagged_and_not_estimated(self):
        cases = [({"fillQty": -1.0}, "NEGATIVE_CUMULATIVE_FILL_QUANTITY"),
                 ({"fillQty": 4.0}, "CUMULATIVE_FILL_EXCEEDS_ORDER_QUANTITY"),
                 ({"fillAvgPrice": -1.0}, "NEGATIVE_FILL_AVERAGE_PRICE"),
                 ({"fillAvgPrice": 30.0}, "REPORTED_FILL_AVERAGE_OUTSIDE_LIMIT")]
        for update, diagnostic in cases:
            response = response_payload("trade_observe")
            response["s2c"]["orderList"][0].update(update)
            result = self.verify("trade_observe", response=response)
            self.assertEqual(result["status"], "READ_FACTS_MATCHED")
            self.assertTrue(result["needs_reconciliation"])
            self.assertIn(diagnostic, result["diagnostics"])
            self.assertEqual(result["derived"], {})
            self.assertFalse(result["journal_observation_ready"])

    def test_sell_order_scope_is_explicit_and_same_source_rules_apply(self):
        terms = config(); terms["side"] = "SELL"
        profile = wire.prepare_wire_profile(**wire_fixture(terms=terms))
        request = request_payload("trade_observe")
        response = response_payload("trade_observe")
        response["s2c"]["orderList"][0].update(trdSide=2, fillAvgPrice=21.0)
        value = self.verify("trade_observe", profile=profile, request=request, response=response)
        self.assertEqual(value["status"], "READ_FACTS_MATCHED")
        self.assertFalse(value["needs_reconciliation"])

    def test_fee_zero_is_present_but_currency_and_finality_are_not_invented(self):
        result = self.verify("trade_fees")
        self.assertEqual(Decimal(result["facts"]["fee_amount"]), Decimal(0))
        self.assertIsNone(result["facts"]["currency"])
        self.assertIsNone(result["facts"]["fees_final"])
        response = response_payload("trade_fees")
        response["s2c"]["orderFeeList"][0].pop("feeAmount")
        response["s2c"]["orderFeeList"][0]["feesFinal"] = True
        result = self.verify("trade_fees", response=response)
        self.assertIsNone(result["facts"]["fee_amount"])
        self.assertIsNone(result["facts"]["fees_final"])
        self.assertTrue(any(row["field"].endswith("feeAmount") for row in result["missing"]))

    def test_fee_empty_duplicate_and_foreign_order_are_not_selected_by_position(self):
        response = response_payload("trade_fees")
        original = response["s2c"]["orderFeeList"][0]
        response["s2c"]["orderFeeList"] = []
        self.assertEqual(self.verify("trade_fees", response=response)["status"], "NOT_FOUND_UNCONFIRMED")
        for rows in ([original, original], [dict(original, orderIDEx="other")]):
            response["s2c"]["orderFeeList"] = rows
            with self.assertRaises(facts_module.ResponseFactsError):
                self.verify("trade_fees", response=response)

    def test_multiple_accounts_select_exact_target_without_default_currency_or_permission(self):
        value = self.verify("trade_accounts")
        self.assertEqual(value["facts"]["target_account_id"], str(ACCOUNT))
        self.assertEqual(value["facts"]["returned_account_count"], 2)
        self.assertIsNone(value["facts"]["currency"])
        self.assertFalse(value["facts"]["trading_permission_verified"])
        response = response_payload("trade_accounts")
        response["s2c"]["accList"].pop()
        value = self.verify("trade_accounts", response=response)
        self.assertEqual(value["status"], "NOT_FOUND_UNCONFIRMED")
        self.assertIsNone(value["facts"]["target_account_id"])

    def test_duplicate_target_or_wrong_account_environment_market_and_bool_id_reject(self):
        for mutation in (lambda rows: rows.append(deepcopy(rows[1])), lambda rows: rows[1].update(trdEnv=1),
                         lambda rows: rows[1].update(trdEnv=False), lambda rows: rows[1].update(accID=True),
                         lambda rows: rows[1].update(trdMarketAuthList=[1])):
            response = response_payload("trade_accounts")
            mutation(response["s2c"]["accList"])
            with self.assertRaises(facts_module.ResponseFactsError):
                self.verify("trade_accounts", response=response)

    def test_cash_available_funds_and_power_remain_different_observed_fields(self):
        value = self.verify("trade_funds")
        facts = value["facts"]
        self.assertEqual([Decimal(facts[key]) for key in ("cash", "available_funds", "power")],
                         [Decimal(500), Decimal(400), Decimal(1000)])
        self.assertIsNone(facts["cash_available_for_reservation"])
        response = response_payload("trade_funds")
        response["s2c"]["funds"].pop("availableFunds")
        value = self.verify("trade_funds", response=response)
        self.assertIsNone(value["facts"]["available_funds"])
        self.assertEqual(Decimal(value["facts"]["power"]), Decimal(1000))
        response["s2c"]["funds"].pop("currency")
        value = self.verify("trade_funds", response=response)
        self.assertEqual(value["status"], "INCOMPLETE_EVIDENCE")
        self.assertIsNone(value["facts"]["currency"])
        response["s2c"]["funds"]["currency"] = 1
        with self.assertRaises(facts_module.ResponseFactsError):
            self.verify("trade_funds", response=response)

    def test_broker_positions_never_become_owner_allocations_or_zero_holdings(self):
        value = self.verify("trade_positions")
        self.assertEqual(Decimal(value["facts"]["broker_positions"][0]["quantity"]), Decimal("4.5"))
        self.assertIsNone(value["facts"]["broker_positions"][0]["owner_scope_id"])
        self.assertIsNone(value["facts"]["owner_positions"])
        self.assertFalse(value["facts"]["owner_allocation_verified"])
        response = response_payload("trade_positions")
        response["s2c"]["positionList"] = []
        result = self.verify("trade_positions", response=response)
        self.assertEqual(result["status"], "NOT_FOUND_UNCONFIRMED")
        self.assertIsNone(result["facts"]["owner_positions"])

    def test_position_foreign_security_account_currency_and_duplicate_ids_reject(self):
        for update in ({"code": "AMD"}, {"accID": ACCOUNT + 1}, {"currency": 1}, {"secMarket": 1}):
            response = response_payload("trade_positions")
            response["s2c"]["positionList"][0].update(update)
            with self.assertRaises(facts_module.ResponseFactsError):
                self.verify("trade_positions", response=response)
        response = response_payload("trade_positions")
        response["s2c"]["positionList"].append(position_row())
        with self.assertRaises(facts_module.ResponseFactsError):
            self.verify("trade_positions", response=response)

    def test_api_error_is_not_terminal_rejection_or_ack_even_with_an_s2c_body(self):
        response = response_payload("trade_submit")
        response.update(retType=-1, retMsg="synthetic API timeout", errCode=900)
        result = self.verify(response=response)
        self.assertEqual(result["status"], "API_ERROR_RESPONSE")
        self.assertEqual(result["facts"], {})
        self.assertEqual(result["economic_acceptance"], "NOT_INFERRED")
        self.assertFalse(result["journal_observation_ready"])

    def test_receipt_time_is_not_source_time_and_late_facts_do_not_restore_permission(self):
        args = facts_fixture()
        args["received_at"] = NOW + timedelta(hours=1)
        value = facts_module.verify_response_facts(**args).as_dict()
        self.assertTrue(value["received_after_profile_expiry"])
        self.assertFalse(value["received_at_is_source_update_time"])
        self.assertFalse(any(value["permissions"].values()))
        for at in (NOW - timedelta(seconds=1), NOW.replace(tzinfo=None)):
            args["received_at"] = at
            with self.assertRaises(facts_module.ResponseFactsError):
                facts_module.verify_response_facts(**args)

    def test_cross_profile_or_original_scope_cannot_be_rebound(self):
        args = facts_fixture()
        args["profile"] = make_profile(max_total_fees="1.00")
        with self.assertRaisesRegex(facts_module.ResponseFactsError, "profile_changed"):
            facts_module.verify_response_facts(**args)
        args["action_receipt"]["payload"]["profile"] = args["profile"].as_dict()
        reseal_event(args)
        with self.assertRaises(facts_module.ResponseFactsError):
            facts_module.verify_response_facts(**args)

    def test_other_valid_protocols_are_explicitly_outside_this_fact_projection(self):
        args = facts_fixture()
        frame = request_frame("quote_runtime")
        event = action_receipt(args["profile"], "quote_runtime", frame)
        args.update(action_receipt=event, expected_action_receipt_id=event["id"], request_frame=frame,
                    response_frame=response_frame("quote_runtime"))
        with self.assertRaisesRegex(facts_module.ResponseFactsError, "response_action_unsupported"):
            facts_module.verify_response_facts(**args)

    def test_original_receipt_frames_and_profile_are_not_modified(self):
        args = facts_fixture("trade_observe")
        original = contract.canonical_bytes(args["action_receipt"])
        profile = args["profile"].as_dict()
        request, response = args["request_frame"], args["response_frame"]
        facts_module.verify_response_facts(**args)
        self.assertEqual(contract.canonical_bytes(args["action_receipt"]), original)
        self.assertEqual(args["profile"].as_dict(), profile)
        self.assertEqual((args["request_frame"], args["response_frame"]), (request, response))


if __name__ == "__main__":
    unittest.main()
