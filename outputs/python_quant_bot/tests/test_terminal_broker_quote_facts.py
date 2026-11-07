"""Pure quote presence/scope contracts on explicit protobuf-shaped fakes.

These tests do not replace the separate pinned-protobuf/worker/OS probe. No SDK,
clock lookup, network, database or business calculation is performed here.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import unittest
from unittest.mock import patch

from exchange_terminal.services import terminal_broker_response_facts as facts
from exchange_terminal.services import terminal_broker_execution_plan as contract
from tests.test_terminal_broker_response_facts import facts_fixture
from tests.test_terminal_broker_wire_profile import NOW


def quote_payload(action):
    security = {"market": 11, "code": "TSLA"}
    values = {
        "quote_runtime": {"marketHK": 6, "marketUS": 3, "marketSH": 6, "marketSZ": 6, "marketHKFuture": 6,
            "qotLogined": True, "trdLogined": False, "serverVer": 107, "serverBuildNo": 6708,
            "time": 1793377800, "localTime": 1793377800.25, "connID": 11, "programStatus": {"type": 10}},
        "quote_security": {"staticInfoList": [{"basic": {"security": security, "id": 12345, "lotSize": 1,
            "secType": 3, "name": "FICTIONAL", "delisting": False, "exchType": 6}}]},
        "quote_snapshot": {"snapshotList": [{"basic": {"security": security, "type": 3, "isSuspend": False,
            "lotSize": 1, "priceSpread": 0.01, "updateTime": "2026-10-30 09:30:00", "curPrice": 20.,
            "updateTimestamp": 1793367000., "askPrice": 20.02, "bidPrice": 20.01, "secStatus": 1}}]},
    }
    return {"retType": 0, "s2c": deepcopy(values[action])}


def basic(response, action):
    return response["s2c"]["staticInfoList" if action == "quote_security" else "snapshotList"][0]["basic"]


class QuoteResponseFactsTests(unittest.TestCase):
    def setUp(self):
        for name in ("builtins.open", "socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "socket.getaddrinfo", "sqlite3.connect", "subprocess.Popen", "time.time"):
            guard = patch(name, side_effect=AssertionError("pure quote projection must not perform IO or clock lookup"))
            guard.start(); self.addCleanup(guard.stop)

    def verify(self, action, response=None, **changes):
        args = facts_fixture(action, response=response if response is not None else quote_payload(action))
        args.update(changes)
        return facts.verify_response_facts(**args).as_dict()

    def test_three_quote_actions_use_exact_original_receipt_and_frames_without_trade_header(self):
        for action in sorted(facts.QUOTE_ACTIONS):
            with self.subTest(action=action):
                args = facts_fixture(action, response=quote_payload(action))
                original = contract.canonical_bytes(args["action_receipt"])
                result = facts.verify_response_facts(**args).as_dict()
                self.assertEqual(result["status"], "READ_FACTS_MATCHED")
                self.assertEqual(result["journal_receipt_id"], args["expected_action_receipt_id"])
                self.assertEqual(result["request_frame"]["sha256"], sha256(args["request_frame"]).hexdigest())
                self.assertEqual(result["response_frame"]["sha256"], sha256(args["response_frame"]).hexdigest())
                self.assertEqual(contract.canonical_bytes(args["action_receipt"]), original)
                self.assertFalse(any(row["field"] == "s2c.header" for row in result["missing"]))
                self.assertTrue(result["test_only"])
                self.assertFalse(result["source_authenticated"])
                self.assertFalse(result["journal_observation_ready"])
                self.assertFalse(result["reservation_ready"])
                self.assertFalse(any(result["permissions"].values()))
                self.assertFalse(result["facts"]["freshness_verified"])
                self.assertFalse(result["facts"]["trading_eligibility_verified"])
                self.assertIsNone(result["facts"]["source_age_seconds"])
                self.assertEqual(result["derived"], {})

    def test_global_state_is_nasdaq_and_server_time_not_target_state_or_price_time(self):
        response = quote_payload("quote_runtime")
        response["s2c"].update(marketUS=6, qotLogined=False, trdLogined=True)
        value = self.verify("quote_runtime", response)["facts"]
        self.assertEqual(value["market_us_code"], 6)
        self.assertEqual(value["market_us_scope"], "NASDAQ_GLOBAL")
        self.assertFalse(value["quote_server_logged_in"])
        self.assertTrue(value["trade_server_logged_in"])
        self.assertIsNone(value["target_market_state"])
        self.assertFalse(value["quote_permission_verified"])
        self.assertNotIn("quote_state", value)
        self.assertEqual(value["server_time_seconds"], response["s2c"]["time"])
        self.assertEqual(value["server_time_scope"], "FUTU_SERVER_CURRENT_TIME_NOT_MARKET_SOURCE_TIME")
        self.assertEqual((value["server_version"], value["server_build"]), (107, 6708))

    def test_missing_local_time_connection_and_program_remain_absent_without_clock_fallback(self):
        response = quote_payload("quote_runtime")
        for key in ("localTime", "connID", "programStatus"):
            response["s2c"].pop(key)
        result = self.verify("quote_runtime", response)
        self.assertEqual(result["status"], "READ_FACTS_MATCHED")
        for key in ("local_time_seconds", "quote_connection_id", "quote_connection_scope_matched", "program_status_code"):
            self.assertIsNone(result["facts"][key])
        self.assertTrue({"s2c.localTime", "s2c.connID", "s2c.programStatus"} <= {r["field"] for r in result["missing"]})

    def test_runtime_connection_if_present_must_match_quote_handshake_not_trade_connection(self):
        self.assertTrue(self.verify("quote_runtime")["facts"]["quote_connection_scope_matched"])
        for identity in (33, 12, 0, True):
            response = quote_payload("quote_runtime"); response["s2c"]["connID"] = identity
            with self.subTest(identity=identity), self.assertRaises(facts.ResponseFactsError):
                self.verify("quote_runtime", response)

    def test_unknown_global_market_enum_is_retained_without_interpreting_tradability(self):
        response = quote_payload("quote_runtime"); response["s2c"]["marketUS"] = 999
        result = self.verify("quote_runtime", response)
        self.assertEqual(result["facts"]["market_us_code"], 999)
        self.assertFalse(result["facts"]["trading_eligibility_verified"])

    def test_required_runtime_field_absence_is_incomplete_and_invalid_scalar_is_rejected(self):
        for key in ("marketUS", "qotLogined", "trdLogined", "serverVer", "serverBuildNo", "time"):
            response = quote_payload("quote_runtime"); response["s2c"].pop(key)
            with self.subTest(missing=key):
                self.assertEqual(self.verify("quote_runtime", response)["status"], "INCOMPLETE_EVIDENCE")
        for key, value in (("marketUS", True), ("qotLogined", 1), ("time", "1793377800")):
            response = quote_payload("quote_runtime"); response["s2c"][key] = value
            with self.subTest(key=key), self.assertRaises(facts.ResponseFactsError):
                self.verify("quote_runtime", response)

    def test_static_identity_and_explicit_false_are_preserved_without_currency_or_rules(self):
        result = self.verify("quote_security")
        value = result["facts"]
        self.assertEqual((value["market"], value["code"], value["static_security_id"]), (11, "TSLA", "12345"))
        self.assertEqual((value["security_type"], value["lot_size"]), (3, 1))
        self.assertIs(value["delisting"], False)
        self.assertEqual(value["exchange_type"], 6)
        self.assertIsNone(value["currency"])
        self.assertEqual(value["expected_currency"], "USD")
        self.assertFalse(value["lot_is_complete_trading_rule"])
        self.assertIsNone(value["price_step"])

    def test_missing_static_optional_status_is_not_defaulted_to_normal(self):
        response = quote_payload("quote_security")
        row = basic(response, "quote_security"); row.pop("delisting"); row.pop("exchType")
        result = self.verify("quote_security", response)
        self.assertIsNone(result["facts"]["delisting"])
        self.assertIsNone(result["facts"]["exchange_type"])
        self.assertEqual(result["status"], "READ_FACTS_MATCHED")

    def test_exact_target_market_code_equity_type_and_single_row_required(self):
        for action in ("quote_security", "quote_snapshot"):
            for field, value in (("market", 1), ("code", "OTHER"), ("market", True)):
                response = quote_payload(action); basic(response, action)["security"][field] = value
                with self.subTest(action=action, field=field), self.assertRaises(facts.ResponseFactsError):
                    self.verify(action, response)
            response = quote_payload(action)
            basic(response, action)["secType" if action == "quote_security" else "type"] = 4
            with self.subTest(action=action, kind="non-equity"), self.assertRaises(facts.ResponseFactsError):
                self.verify(action, response)
            response = quote_payload(action); rows = next(iter(response["s2c"].values())); rows.append(deepcopy(rows[0]))
            with self.subTest(action=action, kind="duplicate"), self.assertRaises(facts.ResponseFactsError):
                self.verify(action, response)

    def test_empty_target_list_is_not_found_not_zero_or_complete(self):
        for action in ("quote_security", "quote_snapshot"):
            response = quote_payload(action)
            next(iter(response["s2c"].values())).clear()
            with self.subTest(action=action):
                result = self.verify(action, response)
                self.assertEqual(result["status"], "NOT_FOUND_UNCONFIRMED")
                self.assertNotIn("code", result["facts"])

    def test_missing_identity_basic_required_type_or_lot_is_incomplete(self):
        for action in ("quote_security", "quote_snapshot"):
            fields = ("security", "lotSize", "secType", "id") if action == "quote_security" else ("security", "lotSize", "type", "curPrice", "isSuspend", "updateTime")
            for field in fields:
                response = quote_payload(action); basic(response, action).pop(field)
                with self.subTest(action=action, field=field):
                    self.assertEqual(self.verify(action, response)["status"], "INCOMPLETE_EVIDENCE")

    def test_invalid_lot_or_identity_scalar_is_rejected(self):
        for field, value in (("lotSize", 0), ("lotSize", 1.0), ("id", True), ("id", -1), ("delisting", 0)):
            response = quote_payload("quote_security"); basic(response, "quote_security")[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(facts.ResponseFactsError):
                self.verify("quote_security", response)

    def test_snapshot_time_scope_and_spread_are_not_promoted_to_age_or_order_tick(self):
        value = self.verify("quote_snapshot")["facts"]
        self.assertEqual(value["current_price"], "20.0")
        self.assertEqual(value["source_time_scope"], "CURRENT_PRICE_ONLY")
        self.assertEqual(value["current_price_time_zone"], "America/New_York")
        self.assertEqual(value["current_price_update_time"], "2026-10-30 09:30:00")
        self.assertEqual(value["current_price_update_timestamp"], "1793367000.0")
        self.assertIsNone(value["source_time_utc"])
        self.assertFalse(value["source_time_normalized"])
        self.assertEqual(value["price_spread"], "0.01")
        self.assertEqual(value["price_spread_scope"], "ADJACENT_ASK_QUOTE_DIFFERENCE_NOT_ORDER_TICK")
        self.assertEqual((value["ask_price"], value["bid_price"]), ("20.02", "20.01"))
        self.assertIsNone(value["price_step"])

    def test_old_future_or_ambiguous_source_time_is_raw_observation_not_freshness(self):
        for timestamp in ("1999-01-01 09:30:00", "2099-01-01 09:30:00", "2026-11-01 01:30:00", "unparsed source time"):
            response = quote_payload("quote_snapshot"); basic(response, "quote_snapshot")["updateTime"] = timestamp
            with self.subTest(timestamp=timestamp):
                value = self.verify("quote_snapshot", response)["facts"]
                self.assertEqual(value["current_price_update_time"], timestamp)
                self.assertFalse(value["freshness_verified"])
                self.assertIsNone(value["source_age_seconds"])

    def test_snapshot_missing_optional_values_never_gain_time_status_or_prices(self):
        response = quote_payload("quote_snapshot"); row = basic(response, "quote_snapshot")
        for key in ("updateTimestamp", "secStatus", "askPrice", "bidPrice"):
            row.pop(key)
        value = self.verify("quote_snapshot", response)["facts"]
        for field in ("current_price_update_timestamp", "security_status_code", "ask_price", "bid_price"):
            self.assertIsNone(value[field])
        self.assertIsNone(value["currency"])

    def test_snapshot_nonpositive_price_unknown_status_and_suspend_are_only_observations(self):
        for price in (0., -1.):
            response = quote_payload("quote_snapshot")
            basic(response, "quote_snapshot").update(curPrice=price, secStatus=0, isSuspend=True)
            value = self.verify("quote_snapshot", response)["facts"]
            self.assertFalse(value["current_price_positive"])
            self.assertTrue(value["is_suspended"])
            self.assertEqual(value["security_status_code"], 0)
            self.assertFalse(value["trading_eligibility_verified"])

    def test_snapshot_empty_source_time_is_incomplete_and_bool_number_is_rejected(self):
        response = quote_payload("quote_snapshot"); basic(response, "quote_snapshot")["updateTime"] = ""
        self.assertEqual(self.verify("quote_snapshot", response)["status"], "INCOMPLETE_EVIDENCE")
        for field in ("curPrice", "priceSpread", "updateTimestamp", "askPrice"):
            response = quote_payload("quote_snapshot"); basic(response, "quote_snapshot")[field] = True
            with self.subTest(field=field), self.assertRaises(facts.ResponseFactsError):
                self.verify("quote_snapshot", response)

    def test_query_error_and_missing_s2c_preserve_failure_without_fabricating_quote(self):
        for action in facts.QUOTE_ACTIONS:
            with self.subTest(action=action):
                result = self.verify(action, {"retType": -1, "retMsg": "synthetic unavailable"})
                self.assertEqual((result["status"], result["facts"]), ("API_ERROR_RESPONSE", {}))
                result = self.verify(action, {"retType": 0})
                self.assertEqual((result["status"], result["facts"]), ("INCOMPLETE_EVIDENCE", {}))

    def test_late_quote_preserves_original_observation_without_renewing_profile(self):
        for action in facts.QUOTE_ACTIONS:
            with self.subTest(action=action):
                result = self.verify(action, received_at=NOW + timedelta(hours=1))
                self.assertTrue(result["received_after_profile_expiry"])
                self.assertEqual(result["status"], "READ_FACTS_MATCHED")
                self.assertFalse(result["facts"]["freshness_verified"])
                self.assertFalse(result["received_at_is_source_update_time"])


if __name__ == "__main__":
    unittest.main()
