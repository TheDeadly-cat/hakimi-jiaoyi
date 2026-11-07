"""Pure v3 catalog/profile/codec contracts; JSON fakes are not SDK evidence."""
from copy import deepcopy
from hashlib import sha256
import inspect
import json
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services import terminal_broker_wire_profile as wire
from exchange_terminal.services import terminal_broker_execution_plan as plan
from exchange_terminal.services import terminal_broker_scoped_transport as transport
from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.adapters import futu_verified_protobuf_loader as loader
from tests.test_terminal_broker_wire_profile import fixture, validate
from tests.test_terminal_broker_request_builder import ConstructibleRequest, fake_bindings
from tests.test_futu_us_equity_simulate_wire_v2 import Response, make_codec, response_frame
from tests.test_terminal_broker_scoped_transport import FakeClock, FixtureGate, FixturePermit, FakeConnection, Sink


def v3_inputs():
    args = fixture()
    args["wire_bounds"]["actions"] = dict(wire.PROTOCOL_LIMITS_V3)
    return args


def v3_profile(**bounds):
    args = v3_inputs(); args["wire_bounds"].update(bounds)
    return wire.prepare_wire_profile_v3(**args)


def v3_codec(profile=None, **session_changes):
    profile = profile or v3_profile()
    values = dict(client_version=100, client_id="fictional-client", quote_connection_id=None,
                  quote_user_id=None, trade_connection_id=None, trade_user_id=None, broker_order_id=None)
    values.update(session_changes)
    session = codec.bind_codec_session(profile, **values)
    return codec.SimulateCodec(profile, session,
        request_classes={p: type("Request", (ConstructibleRequest,), {"full_name": name + ".Request"})
                         for p, name in codec.PROTO_NAMES_V3.items()},
        response_classes={p: type("Response", (Response,), {"full_name": name + ".Response"})
                          for p, name in codec.PROTO_NAMES_V3.items()})


class WireV3Tests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "sqlite3.connect", "subprocess.Popen"):
            guard = patch(name, side_effect=AssertionError("No actual IO in v3 pure contracts"))
            guard.start(); self.addCleanup(guard.stop)

    def test_v2_default_exact_bytes_and_catalog_remain_the_dd21e70_contract(self):
        profile = wire.prepare_wire_profile(**fixture())
        # Computed independently from the immutable dd21e70 version before v3.
        self.assertEqual(sha256(profile._data).hexdigest(), "26bef5ecdc4f1513fed4b324e2ec2fec23b8cc8276c2dd0e008e8995e00fd8d6")
        self.assertNotIn("submit_observation_policy", profile.as_dict())
        self.assertNotIn("quote_market_state", wire.WIRE_ACTIONS)
        self.assertNotIn("quote_market_state", wire.PROTOCOL_LIMITS)
        self.assertNotIn(3223, codec.PROTO_NAMES)
        self.assertNotIn(3223, loader.PROTO_NAMES)
        self.assertEqual((len(codec.PROTO_NAMES), len(loader.PROTO_NAMES)), (11, 11))
        self.assertEqual(validate(profile, fixture())._data, profile._data)
        self.assertIs(wire.actions_for_profile(profile), wire.WIRE_ACTIONS)

    def test_v3_adds_one_bounded_protocol_without_new_account_or_intent_scope(self):
        args = v3_inputs(); before = deepcopy(args["wire_bounds"])
        profile = wire.prepare_wire_profile_v3(**args); value = profile.as_dict()
        old = wire.prepare_wire_profile(**fixture()).as_dict()
        self.assertEqual(value["schema_version"], wire.SCHEMA_V3)
        self.assertEqual(value["contract_id"], "hakimi-futu-us-equity-simulate-wire-v3")
        self.assertEqual(value["deduplication"], old["deduplication"])
        self.assertEqual(value["base_plan_id"], old["base_plan_id"])
        self.assertNotEqual(value["id"], old["id"])
        self.assertEqual(args["wire_bounds"], before)
        self.assertEqual(set(wire.WIRE_ACTIONS_V3) - set(wire.WIRE_ACTIONS), {"quote_market_state"})
        self.assertEqual(wire.WIRE_ACTIONS_V3["quote_market_state"], ("quote", 3223))
        self.assertEqual(wire.PROTOCOL_LIMITS_V3["quote_market_state"], 1)
        self.assertIs(wire.actions_for_profile(value), wire.WIRE_ACTIONS_V3)
        with self.assertRaises(TypeError): wire.WIRE_ACTIONS_V3["quote_market_state"] = ("trade", 3223)

    def test_v3_policy_is_fixed_and_binds_both_handshakes_and_original_query_age(self):
        value = v3_profile(max_evidence_age_seconds=7).as_dict()
        self.assertEqual(value["submit_observation_policy"], {
            "schema_version": "hakimi-submit-observation-policy-v1", "market_scope": "US_COMMON_STOCK",
            "required_handshakes": ["quote_init", "trade_init"],
            "required_actions": ["quote_runtime", "quote_security", "quote_snapshot", "quote_market_state"],
            "allowed_market_states": [5], "age_basis": "ORIGINAL_ACTION_QUERY_WINDOW", "max_evidence_age_seconds": 7})
        self.assertFalse(any(value["permissions"].values()))
        self.assertFalse(value["protocol_policy"]["production_transport_available"])
        self.assertFalse(value["budget_readiness"]["execution_ready"])

    def test_explicit_schema_and_action_budget_have_no_unknown_or_legacy_fallback(self):
        for value in (None, {}, {"schema_version": None}, {"schema_version": True},
                      {"schema_version": "hakimi-broker-wire-profile-v4"}):
            with self.subTest(value=value), self.assertRaisesRegex(wire.WireProfileError, "schema_invalid"):
                wire.actions_for_profile(value)
        with self.assertRaises(wire.WireProfileError):
            wire.prepare_wire_profile_v3(**fixture())
        with self.assertRaises(wire.WireProfileError):
            wire.prepare_wire_profile(**v3_inputs())
        for value in (-1, True, 2):
            args = v3_inputs(); args["wire_bounds"]["actions"]["quote_market_state"] = value
            with self.subTest(value=value), self.assertRaises(wire.WireProfileError):
                wire.prepare_wire_profile_v3(**args)

    def test_disabled_observation_budget_remains_disabled_not_implicit_authority(self):
        args = v3_inputs(); args["wire_bounds"]["actions"]["quote_market_state"] = 0
        profile = wire.prepare_wire_profile_v3(**args)
        self.assertFalse(profile.as_dict()["budget_readiness"]["stages"]["submit"]["budget_complete"])
        subject = v3_codec(profile, quote_connection_id=11, quote_user_id=22)
        with self.assertRaisesRegex(codec.CodecError, "action_not_allowed"):
            subject.encode_request(profile, "quote_market_state", 2)

    def test_validator_rebuilds_v3_and_rejects_resealed_policy_weakening(self):
        args = v3_inputs(); profile = wire.prepare_wire_profile_v3(**args)
        self.assertEqual(validate(profile, args)._data, profile._data)
        changes = {"allowed_market_states": [3, 5], "required_handshakes": [], "required_actions": [],
                   "age_basis": "RECEIVED_AT", "max_evidence_age_seconds": 31, "market_scope": "ANY"}
        for key, replacement in changes.items():
            value = profile.as_dict(); value["submit_observation_policy"][key] = replacement
            value["id"] = plan.digest({k: v for k, v in value.items() if k != "id"})
            with self.subTest(key=key), self.assertRaisesRegex(wire.WireProfileError, "profile_or_binding_changed"):
                validate(value, args, expected_profile_id=value["id"])

    def test_age_remains_bounded_and_input_cannot_supply_its_own_policy(self):
        for age in (0, 31, True):
            with self.subTest(age=age), self.assertRaises(wire.WireProfileError):
                v3_profile(max_evidence_age_seconds=age)
        args = v3_inputs(); args["submit_observation_policy"] = {}
        with self.assertRaises(TypeError): wire.prepare_wire_profile_v3(**args)

    def test_loader_explicit_version_selects_exact_11_or_12_without_loading_sdk(self):
        self.assertIs(loader._protocols_for_schema(wire.SCHEMA), loader.PROTO_NAMES)
        self.assertIs(loader._protocols_for_schema(wire.SCHEMA_V3), loader.PROTO_NAMES_V3)
        self.assertEqual(loader.PROTO_NAMES_V3[3223], "Qot_GetMarketState")
        self.assertEqual(set(loader.PROTO_NAMES_V3), set(codec.PROTO_NAMES_V3))
        self.assertEqual(inspect.signature(loader.load_verified_protobuf).parameters["profile_schema"].default, wire.SCHEMA)
        with patch.object(loader, "_private_process"), patch.object(loader.Path, "open", side_effect=AssertionError("No file read")):
            for schema in (None, True, "v4"):
                with self.subTest(schema=schema), self.assertRaisesRegex(loader.ProtobufLoaderError, "PROFILE_SCHEMA_UNSUPPORTED"):
                    loader.load_verified_protobuf(package_root="unused", expected_manifest_sha256="0" * 64,
                        runtime_identity=fixture()["runtime_identity"], profile_schema=schema)

    def test_v3_constructor_requires_exact_protocol_and_descriptor_map(self):
        profile = v3_profile(); subject = v3_codec(profile)
        for requests in ({p: c for p, c in subject._requests.items() if p != 3223},
                         {**subject._requests, 1005: subject._requests[1002]}):
            with self.assertRaisesRegex(codec.CodecError, "exact_codec_map"):
                codec.SimulateCodec(profile, subject.session_binding(), request_classes=requests,
                                    response_classes=subject._responses)
        requests = dict(subject._requests)
        requests[3223] = type("Wrong", (ConstructibleRequest,), {"full_name": "GetGlobalState.Request"})
        with self.assertRaisesRegex(codec.CodecError, "protocol_class_mismatch"):
            codec.SimulateCodec(profile, subject.session_binding(), request_classes=requests,
                                response_classes=subject._responses)

    def test_verified_bindings_require_matching_explicit_version_and_class_map(self):
        profile = v3_profile(); subject = v3_codec(profile)
        data = {key: subject._profile["runtime"][key] for key in ("package", "sdk")}
        with self.assertRaisesRegex(codec.CodecError, "profile_schema_mismatch"):
            codec.SimulateCodec.from_verified_bindings(profile, subject.session_binding(), fake_bindings(subject, data=data))
        data["profile_schema"] = wire.SCHEMA_V3
        bound = codec.SimulateCodec.from_verified_bindings(profile, subject.session_binding(), fake_bindings(subject, data=data))
        self.assertEqual(set(bound._requests), set(codec.PROTO_NAMES_V3))
        old_profile = wire.prepare_wire_profile(**fixture())
        old = make_codec(old_profile)
        with self.assertRaisesRegex(codec.CodecError, "profile_schema_mismatch"):
            codec.SimulateCodec.from_verified_bindings(old_profile, old.session_binding(),
                fake_bindings(old, data={**data, "profile_schema": wire.SCHEMA_V3}))

    def test_market_state_encodes_one_exact_security_and_decodes_actual_action_id(self):
        profile = v3_profile(); subject = v3_codec(profile)
        with self.assertRaisesRegex(codec.CodecError, "session_facts"):
            subject.encode_request(profile, "quote_market_state", 2)
        subject.accept_handshake(profile, "quote", 1, response_frame("quote_init"))
        frame = subject.encode_request(profile, "quote_market_state", 2)
        self.assertEqual(json.loads(frame[44:]), {"c2s": {"securityList": [{"market": 11, "code": "TSLA"}],
                                                        "header": {"securityFirm": 0}}})
        self.assertEqual(subject.validate_request(profile, "quote_market_state", frame).protocol, 3223)
        response = codec.pack_plaintext_frame(3223, 2, b'{"retType":0,"s2c":{"marketInfoList":[]}}')
        self.assertEqual(subject.decode_response(profile, "quote_market_state", 2, response).ret_type, 0)
        changed = json.loads(frame[44:]); changed["c2s"]["securityList"][0]["code"] = "OTHER"
        frame = codec.pack_plaintext_frame(3223, 2, json.dumps(changed, sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaisesRegex(codec.CodecError, "scope_mismatch"):
            subject.validate_request(profile, "quote_market_state", frame)

    def test_v2_codec_and_transport_cannot_dispatch_v3_action(self):
        profile = wire.prepare_wire_profile(**fixture()); subject = make_codec(profile)
        with self.assertRaisesRegex(codec.CodecError, "action_not_allowed"):
            subject.encode_request(profile, "quote_market_state", 2)
        factory = Mock(side_effect=AssertionError("No implicit connection"))
        value = transport.ScopedTransport(profile, factory=factory, clock=FakeClock(), gate=FixtureGate(), sink=Sink(), codec=subject)
        with self.assertRaisesRegex(transport.TransportError, "unknown_action"):
            value.exchange("quote", "quote_market_state", b"unused", FixturePermit(profile), 110)
        factory.assert_not_called()

    def test_accepted_session_requires_handshake_and_exports_no_handshake_secret(self):
        profile = v3_profile(); subject = v3_codec(profile, quote_connection_id=11, quote_user_id=22,
                                                trade_connection_id=33, trade_user_id=22)
        original = subject.session_binding()
        for channel in ("quote", "trade"):
            with self.assertRaisesRegex(codec.CodecError, "accepted_handshake_required"):
                subject.accepted_session_binding(channel)
        subject.accept_handshake(profile, "quote", 1, response_frame("quote_init", payload={"retType": 0,
            "s2c": {"connID": 11, "loginUserID": 22, "keepAliveInterval": 30, "connAESKey": "SYNTHETIC-SECRET"}}))
        self.assertEqual(subject.accepted_session_binding("quote").as_dict(), original.as_dict())
        with self.assertRaisesRegex(codec.CodecError, "accepted_handshake_required"):
            subject.accepted_session_binding("trade")
        subject.accept_handshake(profile, "trade", 1, response_frame("trade_init"))
        self.assertIs(subject.accepted_session_binding("quote"), subject.accepted_session_binding("trade"))
        self.assertNotIn("SYNTHETIC-SECRET", str(subject.accepted_session_binding("quote").as_dict()))

    def test_v3_transport_uses_selected_catalog_once_and_keeps_original_write_barrier(self):
        profile = v3_profile(); subject = v3_codec(profile)
        clock, gate, sink = FakeClock(), FixtureGate(), Sink()
        connection = FakeConnection(clock, gate)
        connection.responses = [response_frame("quote_init"), codec.pack_plaintext_frame(3223, 2,
            b'{"retType":0,"s2c":{"marketInfoList":[]}}')]
        value = transport.ScopedTransport(profile, factory=lambda _: connection, clock=clock, gate=gate, sink=sink, codec=subject)
        permit = FixturePermit(profile)
        self.assertEqual(value.connect("quote", permit, 120).status, "CONNECTED_NOT_INITIALIZED")
        self.assertEqual(value.exchange("quote", "quote_init", subject.encode_request(profile, "quote_init", 1), permit, 120).status,
                         "RESPONSE_RECEIVED")
        self.assertEqual(value.exchange("quote", "quote_market_state", subject.encode_request(profile, "quote_market_state", 2), permit, 120).status,
                         "RESPONSE_RECEIVED")
        self.assertEqual(connection.send_calls, 2)
        self.assertEqual(value.exchange("quote", "quote_market_state", subject.encode_request(profile, "quote_market_state", 3), permit, 120).status,
                         "NOT_WRITTEN")
        self.assertEqual(connection.send_calls, 2)
        self.assertEqual(connection.connects, 1)


if __name__ == "__main__":
    unittest.main()
