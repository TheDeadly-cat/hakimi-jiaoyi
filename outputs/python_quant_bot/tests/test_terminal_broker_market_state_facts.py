"""Pure v3 presence/session contracts using explicit JSON protobuf-shaped fakes.

These are not actual SDK/OpenD or authenticated-source evidence. The actual
private-worker probe is separate. No database, socket, SDK or clock IO occurs.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec_module
from exchange_terminal.services import terminal_broker_execution_plan as contract
from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_response_facts as facts
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests import test_futu_us_equity_simulate_wire_v2 as fake
from tests.test_terminal_broker_response_facts import action_receipt, facts_fixture, response_payload
from tests.test_terminal_broker_quote_facts import quote_payload
from tests.test_terminal_broker_wire_profile import fixture as profile_fixture, NOW


def v3_profile():
    args = profile_fixture()
    args["wire_bounds"]["actions"]["quote_market_state"] = 1
    return wire.prepare_wire_profile_v3(**args)


def v3_codec(profile, *, prefilled=False):
    session = codec_module.bind_codec_session(profile, client_version=100, client_id="fictional-client",
        quote_connection_id=11 if prefilled else None, quote_user_id=22 if prefilled else None,
        trade_connection_id=33 if prefilled else None, trade_user_id=22 if prefilled else None)
    names = codec_module.PROTO_NAMES_V3
    return codec_module.SimulateCodec(profile, session,
        request_classes={protocol: type("Request", (fake.Request,), {"full_name": name + ".Request"})
                         for protocol, name in names.items()},
        response_classes={protocol: type("Response", (fake.Response,), {"full_name": name + ".Response"})
                          for protocol, name in names.items()})


def market_payload(state=5):
    return {"retType": 0, "s2c": {"marketInfoList": [{"security": {"market": 11, "code": "TSLA"},
        "name": "FICTIONAL", "marketState": state}]}}


def handshake_payload(channel):
    return {"retType": 0, "retMsg": "must-stay-private-free-text", "s2c": {"serverVer": 107, "loginUserID": 22,
        "connID": 11 if channel == "quote" else 33, "keepAliveInterval": 30,
        "connAESKey": "must-stay-private-aes-key", "aesCBCiv": "must-stay-private-iv",
        "futureSensitiveField": "must-stay-private-future-field"}}


def frame(profile, action, payload, serial=7):
    return codec_module.pack_plaintext_frame(wire.actions_for_profile(profile)[action][1], serial, fake.encode(payload))


def accept(subject, profile, channel):
    action = channel + "_init"
    subject.accept_handshake(profile, channel, 1, frame(profile, action, handshake_payload(channel), serial=1))


def v3_args(action="quote_market_state", *, response=None, accepted=True, profile=None, codec=None):
    profile = profile or v3_profile()
    subject = codec or v3_codec(profile)
    channel = wire.actions_for_profile(profile)[action][0]
    if accepted and channel not in subject._accepted_channels:
        accept(subject, profile, channel)
    request = ({"c2s": {"securityList": [{"market": 11, "code": "TSLA"}], "header": {"securityFirm": 0}}}
               if action == "quote_market_state" else fake.request_payload(action, serial=7))
    request_frame = frame(profile, action, request)
    if response is None:
        response = (handshake_payload(channel) if action.endswith("_init") else market_payload()
                    if action == "quote_market_state" else quote_payload(action) if action.startswith("quote_")
                    else response_payload(action))
    receipt = action_receipt(profile, action, request_frame)
    return dict(profile=profile, codec=subject, action_receipt=receipt, expected_action_receipt_id=receipt["id"],
        request_frame=request_frame, response_frame=frame(profile, action, response), received_at=NOW + timedelta(seconds=1))


def reseal_receipt(args):
    event = args["action_receipt"]
    event["request_hash"] = contract.digest({"kind": "ACTION", "payload": event["payload"]})
    args["action_receipt"] = journal.seal({key: value for key, value in event.items() if key != "id"})
    args["expected_action_receipt_id"] = args["action_receipt"]["id"]


class MarketStateFactsTests(unittest.TestCase):
    def setUp(self):
        for name in ("builtins.open", "socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "socket.getaddrinfo", "sqlite3.connect", "subprocess.Popen", "time.time"):
            guard = patch(name, side_effect=AssertionError("pure v3 facts cannot do IO or obtain a new clock"))
            guard.start(); self.addCleanup(guard.stop)

    def verify(self, **changes):
        return facts.verify_response_facts(**v3_args(**changes)).as_dict()

    def test_v2_fact_bytes_are_unchanged_for_trade_and_three_quote_examples(self):
        expected = {
            "trade_submit": "d87a47f4361526f8a268d9a6b4a8295494e1520ceb3448be2057cf231576353f",
            "quote_runtime": "57eb4d24a2ff5f331f9a10e0e1134177e56ebd8694fc2fb71b9a032ae66e8d61",
            "quote_security": "cd60d73ae05868ce39f407d53ab3a27fa665c3603e857e775c0722dd4d98ca6e",
            "quote_snapshot": "cd06e9921c583aedfd44ad7c3c15e7c4f2eef2d79120ed2f37284113ec3ecda9",
        }
        for action, digest in expected.items():
            args = facts_fixture(action, response=quote_payload(action)) if action.startswith("quote_") else facts_fixture(action)
            with self.subTest(action=action):
                value = facts.verify_response_facts(**args)
                self.assertEqual(sha256(value._data).hexdigest(), digest)
                self.assertNotIn("session_observation", value.as_dict())
        self.assertNotIn("quote_init", facts.SUPPORTED_ACTIONS)
        self.assertEqual(facts.QUOTE_ACTIONS, {"quote_runtime", "quote_security", "quote_snapshot"})

    def test_v3_catalog_enables_handshakes_and_target_market_only_explicitly(self):
        old = fake.make_profile()
        new = v3_profile()
        self.assertFalse(facts.HANDSHAKE_ACTIONS & facts.supported_actions_for_profile(old))
        self.assertNotIn("quote_market_state", facts.supported_actions_for_profile(old))
        self.assertTrue({"quote_init", "trade_init", "quote_market_state"} <= facts.supported_actions_for_profile(new))

    def test_exact_target_state_is_observation_not_currency_source_time_or_permission(self):
        args = v3_args()
        original = (args["request_frame"], args["response_frame"], contract.canonical_bytes(args["action_receipt"]))
        result = facts.verify_response_facts(**args).as_dict()
        self.assertEqual((result["schema_version"], result["protocol"], result["status"]),
                         (facts.SCHEMA_V3, 3223, "READ_FACTS_MATCHED"))
        detail = result["facts"]
        self.assertEqual((detail["market"], detail["code"], detail["market_state_code"]), (11, "TSLA", 5))
        self.assertEqual(detail["market_state_scope"], "EXACT_TARGET_SECURITY")
        for key in ("currency", "source_time", "source_age_seconds"):
            self.assertIsNone(detail[key])
        for key in ("freshness_verified", "quote_permission_verified", "trading_eligibility_verified"):
            self.assertFalse(detail[key])
        self.assertFalse(any(result["permissions"].values()))
        self.assertEqual(result["session_observation"], dict(channel="quote", connection_id="11", user_id="22",
            client_id="fictional-client", client_version=100))
        self.assertEqual((args["request_frame"], args["response_frame"], contract.canonical_bytes(args["action_receipt"])), original)

    def test_unknown_closed_and_other_raw_int32_states_do_not_become_eligibility(self):
        for state in (0, 3, 5, 6, 8, 10, 37, 999, -1, 2**31 - 1):
            with self.subTest(state=state):
                result = self.verify(response=market_payload(state))
                self.assertEqual(result["status"], "READ_FACTS_MATCHED")
                self.assertEqual(result["facts"]["market_state_code"], state)
                self.assertFalse(result["facts"]["trading_eligibility_verified"])

    def test_market_state_wrong_scalar_or_outside_int32_is_refused(self):
        for state in (True, 5.0, "5", 2**31, -(2**31) - 1):
            with self.subTest(state=state), self.assertRaises(facts.ResponseFactsError):
                self.verify(response=market_payload(state))

    def test_foreign_security_market_code_and_duplicate_rows_are_refused(self):
        for key, value in (("market", 1), ("market", True), ("code", "OTHER")):
            response = market_payload(); response["s2c"]["marketInfoList"][0]["security"][key] = value
            with self.subTest(key=key), self.assertRaises(facts.ResponseFactsError):
                self.verify(response=response)
        response = market_payload(); response["s2c"]["marketInfoList"] *= 2
        with self.assertRaisesRegex(facts.ResponseFactsError, "duplicate_or_foreign"):
            self.verify(response=response)

    def test_missing_market_row_fields_are_incomplete_and_empty_is_not_found(self):
        for key in ("security", "name", "marketState"):
            response = market_payload(); del response["s2c"]["marketInfoList"][0][key]
            with self.subTest(key=key):
                self.assertEqual(self.verify(response=response)["status"], "INCOMPLETE_EVIDENCE")
        response = market_payload(); response["s2c"]["marketInfoList"].clear()
        self.assertEqual(self.verify(response=response)["status"], "NOT_FOUND_UNCONFIRMED")

    def test_api_error_and_missing_s2c_keep_scope_session_but_never_match(self):
        for response, status in (({"retType": -1, "retMsg": "fictional API failure"}, "API_ERROR_RESPONSE"),
                                 ({"retType": 0}, "INCOMPLETE_EVIDENCE")):
            with self.subTest(status=status):
                args = v3_args(response=response)
                raw = args["response_frame"]
                result = facts.verify_response_facts(**args).as_dict()
                self.assertEqual(result["status"], status)
                self.assertEqual(result["response_frame"]["sha256"], sha256(raw).hexdigest())
                self.assertEqual(result["session_observation"]["connection_id"], "11")
                self.assertEqual(args["response_frame"], raw)

    def test_prefilled_connection_ids_are_not_an_accepted_quote_session(self):
        profile = v3_profile()
        for action in ("quote_runtime", "quote_security", "quote_snapshot", "quote_market_state"):
            subject = v3_codec(profile, prefilled=True)
            with self.subTest(action=action), self.assertRaisesRegex(facts.ResponseFactsError, "accepted_handshake_required"):
                self.verify(action=action, profile=profile, codec=subject, accepted=False)

    def test_trade_acceptance_does_not_substitute_for_quote_acceptance(self):
        profile = v3_profile(); subject = v3_codec(profile, prefilled=True)
        accept(subject, profile, "trade")
        with self.assertRaisesRegex(facts.ResponseFactsError, "accepted_handshake_required"):
            self.verify(profile=profile, codec=subject, accepted=False)

    def test_quote_session_observation_is_stable_when_trade_handshake_updates_full_binding(self):
        args = v3_args()
        old_id = args["codec"].session_binding().as_dict()["id"]
        before = facts.verify_response_facts(**args)._data
        accept(args["codec"], args["profile"], "trade")
        self.assertNotEqual(args["codec"].session_binding().as_dict()["id"], old_id)
        self.assertEqual(facts.verify_response_facts(**args)._data, before)

    def test_two_handshakes_record_only_public_identity_and_same_accepted_channel(self):
        for channel in ("quote", "trade"):
            args = v3_args(action=channel + "_init")
            original = args["response_frame"]
            value = facts.verify_response_facts(**args)
            result = value.as_dict()
            with self.subTest(channel=channel):
                self.assertEqual(result["status"], "HANDSHAKE_IDENTITY_MATCHED")
                self.assertEqual(result["session_observation"]["channel"], channel)
                self.assertEqual(result["facts"]["connection_id"], "11" if channel == "quote" else "33")
                self.assertEqual(result["facts"]["user_id"], "22")
                for secret in (b"connAESKey", b"aesCBCiv", b"futureSensitiveField", b"retMsg", b"must-stay-private"):
                    self.assertNotIn(secret, value._data)
                    self.assertIn(secret, original)
                self.assertEqual(args["response_frame"], original)
                self.assertEqual(result["response_frame"]["sha256"], sha256(original).hexdigest())

    def test_complete_handshake_without_acceptance_is_not_verified(self):
        profile = v3_profile(); subject = v3_codec(profile, prefilled=True)
        with self.assertRaisesRegex(facts.ResponseFactsError, "accepted_handshake_required"):
            self.verify(action="quote_init", profile=profile, codec=subject, accepted=False)

    def test_handshake_response_identity_cannot_differ_from_accepted_session(self):
        for key, value in (("connID", 12), ("loginUserID", 23)):
            response = handshake_payload("quote"); response["s2c"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(facts.ResponseFactsError, "accepted_session_mismatch"):
                self.verify(action="quote_init", response=response)

    def test_unsuccessful_or_incomplete_init_has_no_session_success_or_private_fields(self):
        for response, status in (({"retType": -1, "s2c": {"connAESKey": "must-stay-private"}}, "API_ERROR_RESPONSE"),
                                 ({"retType": 0, "s2c": {"connID": 11, "loginUserID": 22}}, "INCOMPLETE_EVIDENCE")):
            with self.subTest(status=status):
                result = self.verify(action="quote_init", response=response, accepted=False)
                self.assertEqual(result["status"], status)
                self.assertIsNone(result["session_observation"])
                self.assertNotIn(b"must-stay-private", contract.canonical_bytes(result))

    def test_expired_observation_is_retained_without_extending_permission(self):
        args = v3_args(); args["received_at"] = NOW + timedelta(minutes=20)
        result = facts.verify_response_facts(**args).as_dict()
        self.assertTrue(result["received_after_profile_expiry"])
        self.assertEqual(result["status"], "READ_FACTS_MATCHED")
        self.assertFalse(result["facts"]["freshness_verified"])
        self.assertFalse(result["facts"]["trading_eligibility_verified"])

    def test_wrong_serial_and_original_request_hash_are_refused(self):
        args = v3_args(); args["response_frame"] = frame(args["profile"], "quote_market_state", market_payload(), serial=8)
        with self.assertRaises(facts.ResponseFactsError): facts.verify_response_facts(**args)
        args = v3_args(); args["action_receipt"]["payload"]["frame_sha256"] = "f" * 64; reseal_receipt(args)
        with self.assertRaisesRegex(facts.ResponseFactsError, "original_request_frame_changed"):
            facts.verify_response_facts(**args)

    def test_only_v3_submit_action_may_have_the_new_observation_payload_field(self):
        args = v3_args(); args["action_receipt"]["payload"]["submit_observation"] = {}; reseal_receipt(args)
        with self.assertRaises(facts.ResponseFactsError): facts.verify_response_facts(**args)
        args = v3_args(action="trade_submit")
        with self.assertRaises(facts.ResponseFactsError): facts.verify_response_facts(**args)

    def test_v3_submit_calls_real_archived_validator_at_original_action_time(self):
        from exchange_terminal.services import terminal_broker_submit_observation as observation
        args = v3_args(action="trade_submit")
        args["action_receipt"]["payload"]["submit_observation"] = {"id": "malformed"}
        reseal_receipt(args)
        args["received_at"] = NOW + timedelta(minutes=20)
        with patch.object(observation, "validate_archived_submit_observation", wraps=observation.validate_archived_submit_observation) as validate:
            with self.assertRaises(facts.ResponseFactsError): facts.verify_response_facts(**args)
        validate.assert_called_once()
        self.assertEqual(validate.call_args.kwargs["now"], NOW)


if __name__ == "__main__":
    unittest.main()
