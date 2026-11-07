"""Standard-library protobuf-shaped fakes, NOT pinned SDK compatibility proof.

The separate reviewed private-runtime probe exercises actual pinned protobuf
bytes. These always-available tests exercise contract refusals and presence.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha1
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_terminal_broker_wire_profile import fixture, REAL


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class FakeMessage:
    """JSON fake implements only the explicit protobuf operations used here."""
    direction = "Nested"

    def __init__(self, data=None, hints=()):
        self.data = data or {}
        names = list(dict.fromkeys([*hints, *self.data]))
        fields = []
        for name in names:
            val = self.data.get(name)
            nested = isinstance(val, dict) or isinstance(val, list) and val and isinstance(val[0], dict)
            fields.append(SimpleNamespace(name=name, is_repeated=isinstance(val, list),
                                          message_type=object() if nested else None))
        self.DESCRIPTOR = SimpleNamespace(name=self.direction, fields=fields,
                                          full_name=getattr(type(self), "full_name", self.direction))

    def ParseFromString(self, body):
        data = json.loads(body)
        hints = ("retType", "retMsg", "errCode", "s2c") if self.direction == "Response" else ()
        self.__init__(data, hints)

    def SerializeToString(self, deterministic=False):
        return encode(self.data)

    def DiscardUnknownFields(self):
        self.data.pop("_unknown", None)

    def IsInitialized(self):
        return ("c2s" in self.data) if self.direction == "Request" else ("retType" in self.data)

    def HasField(self, name):
        return name in self.data

    def __getattr__(self, name):
        value = self.data[name]
        if isinstance(value, dict):
            hints = ("keepAliveInterval", "localTime", "fee", "currency", "priceStep") if name == "s2c" else ()
            return FakeMessage(value, hints)
        if isinstance(value, list):
            return [FakeMessage(x) if isinstance(x, dict) else x for x in value]
        return value


class Request(FakeMessage):
    direction = "Request"


class Response(FakeMessage):
    direction = "Response"


def make_profile(**changes):
    args = fixture()
    args["wire_bounds"].update(changes)
    return wire.prepare_wire_profile(**args)


def make_codec(profile=None, **session_changes):
    profile = profile or make_profile()
    facts = dict(client_version=100, client_id="fictional-client", quote_connection_id=11,
                 quote_user_id=22, trade_connection_id=33, trade_user_id=22,
                 broker_order_id="fictional-order-44")
    facts.update(session_changes)
    session = codec.bind_codec_session(profile, **facts)
    protocols = (1001, 1002, 2001, 2101, 2102, 3202, 3203, 2202, 2201, 2205, 2225)
    return codec.SimulateCodec(profile, session,
        request_classes={p: type("Request", (Request,), {"full_name": codec.PROTO_NAMES[p] + ".Request"}) for p in protocols},
        response_classes={p: type("Response", (Response,), {"full_name": codec.PROTO_NAMES[p] + ".Response"}) for p in protocols})


def request_payload(action, serial=1):
    header = {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2}
    packet = {"connID": 33, "serialNo": serial}
    actions = {
        "quote_init": {"clientVer": 100, "clientID": "fictional-client", "recvNotify": False,
                       "packetEncAlgo": -1, "pushProtoFmt": 0, "programmingLanguage": "Python", "aiType": 0},
        "quote_runtime": {"userID": 22},
        "trade_accounts": {"userID": 22, "trdCategory": 1, "needGeneralSecAccount": False},
        "trade_funds": {"header": header, "refreshCache": True, "currency": 2, "assetCategory": 2},
        "trade_positions": {"header": header, "filterConditions": {"codeList": ["TSLA"], "filterMarket": 2},
                            "refreshCache": True, "currency": 2, "assetCategory": 2, "optionStrategyView": False},
        "quote_security": {"market": 0, "secType": 0, "securityList": [{"market": 11, "code": "TSLA"}], "header": {"securityFirm": 0}},
        "quote_snapshot": {"securityList": [{"market": 11, "code": "TSLA"}], "header": {"securityFirm": 0}},
        "trade_submit": {"header": header, "packetID": packet, "trdSide": 1, "orderType": 1,
                         "code": "TSLA", "qty": 3.0, "price": 20.00000001, "adjustPrice": False,
                         "adjustSideAndLimit": 0.0, "secMarket": 2, "timeInForce": 0,
                         "fillOutsideRTH": False, "session": 1},
        "trade_observe": {"header": header, "filterConditions": {"codeList": ["TSLA"],
                          "orderIDExList": ["fictional-order-44"], "filterMarket": 2}, "refreshCache": True},
        "trade_cancel": {"header": header, "packetID": packet, "orderID": 0,
                         "orderIDEx": "fictional-order-44", "modifyOrderOp": 2, "forAll": False},
        "trade_fees": {"header": header, "orderIdExList": ["fictional-order-44"]},
    }
    actions["trade_init"] = deepcopy(actions["quote_init"])
    return {"c2s": deepcopy(actions[action])}


def request_frame(action, serial=1, payload=None):
    return codec.pack_plaintext_frame(wire.WIRE_ACTIONS[action][1], serial,
                                      encode(payload if payload is not None else request_payload(action, serial)))


def response_frame(action, serial=1, payload=None):
    payload = payload if payload is not None else ({"retType": 0, "s2c": {"keepAliveInterval": 30,
               "connID": 11 if action == "quote_init" else 33, "loginUserID": 22}}
              if action.endswith("_init") else {"retType": 0})
    return codec.pack_plaintext_frame(wire.WIRE_ACTIONS[action][1], serial, encode(payload))


class SimulateCodecTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.create_connection", "sqlite3.connect", "subprocess.Popen"):
            blocked = patch(name, side_effect=AssertionError("offline codec test"))
            blocked.start(); self.addCleanup(blocked.stop)
        self.profile = make_profile()
        self.codec = make_codec(self.profile)

    def test_all_allowed_request_shapes_and_exact_decimal_pass_in_fake_codec(self):
        for action in wire.WIRE_ACTIONS:
            if wire.PROTOCOL_LIMITS[action] and wire.WIRE_ACTIONS[action][1] is not None:
                with self.subTest(action=action):
                    frame = request_frame(action, 77)
                    info = self.codec.validate_request(self.profile, action, frame)
                    self.assertEqual(info.serial, 77)
                    self.assertEqual(info.protocol, wire.WIRE_ACTIONS[action][1])

    def test_real_and_cross_profile_and_untrusted_sessions_rejected(self):
        real = wire.prepare_wire_profile(**fixture(REAL))
        with self.assertRaisesRegex(codec.CodecError, "simulate_only"):
            make_codec(real)
        other = make_profile(max_total_fees="1.00")
        with self.assertRaisesRegex(codec.CodecError, "profile_changed"):
            self.codec.validate_request(other, "trade_submit", request_frame("trade_submit"))
        with self.assertRaises(codec.CodecError):
            codec.CodecSessionBinding(b"{}", object())
        binding = codec.bind_codec_session(self.profile, client_version=100, client_id="fixture")
        with self.assertRaises(FrozenInstanceError):
            binding._data = b"{}"
        exposed = binding.as_dict(); exposed["client_id"] = "changed"
        self.assertEqual(binding.as_dict()["client_id"], "fixture")

    def test_every_order_scope_escape_and_optional_extra_rejected(self):
        changes = [({"header": {"trdEnv": 1, "accID": 900000000000001, "trdMarket": 2}}),
                   {"header": {"trdEnv": 0, "accID": 0, "trdMarket": 2}},
                   {"header": {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 1}},
                   {"qty": 3.5}, {"qty": 4}, {"code": "AMD"}, {"trdSide": 3}, {"orderType": 2},
                   {"price": 20.00000002}, {"adjustPrice": True}, {"adjustSideAndLimit": 0.1},
                   {"secMarket": 1}, {"timeInForce": 1}, {"fillOutsideRTH": True}, {"session": 3},
                   {"remark": "unbound"}, {"auxPrice": 0}, {"expireTime": "2099-01-01"}]
        for change in changes:
            payload = request_payload("trade_submit"); payload["c2s"].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(codec.CodecError, "scope_mismatch"):
                self.codec.validate_request(self.profile, "trade_submit", request_frame("trade_submit", payload=payload))

    def test_empty_or_broad_filters_and_cancel_all_rejected(self):
        cases = [("trade_positions", {"filterConditions": {}}),
                 ("trade_observe", {"filterConditions": {"codeList": ["TSLA"], "filterMarket": 2}}),
                 ("trade_cancel", {"forAll": True}), ("trade_cancel", {"orderIDEx": "another"}),
                 ("trade_cancel", {"modifyOrderOp": 1}), ("trade_fees", {"orderIdExList": []}),
                 ("quote_snapshot", {"securityList": [{"market": 11, "code": "TSLA"}, {"market": 11, "code": "AMD"}]}),
                 ("quote_security", {"securityList": []}), ("trade_funds", {"refreshCache": False}),
                 ("quote_init", {"recvNotify": True}), ("quote_init", {"packetEncAlgo": 2}),
                 ("quote_init", {"clientID": "different"})]
        for action, change in cases:
            payload = request_payload(action); payload["c2s"].update(change)
            with self.subTest(action=action, change=change), self.assertRaises(codec.CodecError):
                self.codec.validate_request(self.profile, action, request_frame(action, payload=payload))

    def test_order_id_and_session_facts_are_required_without_guessing(self):
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.subTest(action=action), self.assertRaisesRegex(codec.CodecError, "original_order"):
                make_codec(self.profile, broker_order_id=None).validate_request(self.profile, action, request_frame(action))
        with self.assertRaisesRegex(codec.CodecError, "session_facts"):
            make_codec(self.profile, trade_connection_id=None).validate_request(self.profile, "trade_submit", request_frame("trade_submit"))

    def test_one_frame_header_hash_serial_and_format_are_strict(self):
        valid = request_frame("trade_submit")
        candidates = [valid + b"tail", valid + valid, valid[:-1], b"XX" + valid[2:]]
        for index, replacement in ((6, 1), (7, 1), (36, 1), (16, 1)):
            altered = bytearray(valid); altered[index] = replacement; candidates.append(bytes(altered))
        for frame in candidates:
            with self.subTest(length=len(frame)), self.assertRaises(codec.CodecError):
                self.codec.validate_request(self.profile, "trade_submit", frame)
        with self.assertRaises(codec.CodecError):
            self.codec.decode_response(self.profile, "trade_submit", 2, response_frame("trade_submit", 1))

    def test_request_direction_and_unknown_fields_do_not_use_response_registry(self):
        self.codec._requests[2202] = Response
        with self.assertRaisesRegex(codec.CodecError, "direction"):
            self.codec.validate_request(self.profile, "trade_submit", request_frame("trade_submit"))
        self.codec._requests[2202] = Request
        payload = request_payload("trade_submit"); payload["_unknown"] = "unbound"
        with self.assertRaisesRegex(codec.CodecError, "unknown_or_noncanonical"):
            self.codec.validate_request(self.profile, "trade_submit", request_frame("trade_submit", payload=payload))

    def test_response_presence_keeps_missing_times_fees_currency_and_tick_unknown(self):
        raw = response_frame("quote_runtime", payload={"retType": 0, "s2c": {"localTime": 0}})
        decoded = self.codec.decode_response(self.profile, "quote_runtime", 1, raw)
        fields = decoded.fields()["s2c"]["value"]
        self.assertEqual(fields["localTime"], {"present": True, "value": 0})
        for key in ("fee", "currency", "priceStep"):
            self.assertEqual(fields[key], {"present": False, "value": None})
        self.assertEqual(decoded.raw_frame, raw)
        missing = self.codec.decode_response(self.profile, "quote_runtime", 1,
                   response_frame("quote_runtime", payload={"retType": 0, "s2c": {}}))
        self.assertEqual(missing.fields()["s2c"]["value"]["localTime"], {"present": False, "value": None})

    def test_missing_required_response_and_output_flood_refuse_without_defaults(self):
        for payload in ({"retMsg": "missing status"}, {"retType": 0, "retMsg": "x" * 8193}):
            with self.subTest(payload_length=len(encode(payload))), self.assertRaises(codec.CodecError):
                self.codec.decode_response(self.profile, "quote_runtime", 1, response_frame("quote_runtime", payload=payload))

    def test_boolean_numeric_aliases_nested_extra_and_missing_false_are_rejected(self):
        for change in ({"trdSide": True}, {"qty": True}, {"adjustPrice": 0}, {"timeInForce": False},
                       {"header": {"trdEnv": False, "accID": 900000000000001, "trdMarket": 2}},
                       {"header": {"trdEnv": 0, "accID": 900000000000001, "trdMarket": 2, "jpAccType": 0}}):
            payload = request_payload("trade_submit"); payload["c2s"].update(change)
            with self.subTest(change=change), self.assertRaises(codec.CodecError):
                self.codec.validate_request(self.profile, "trade_submit", request_frame("trade_submit", payload=payload))
        payload = request_payload("trade_submit"); del payload["c2s"]["adjustPrice"]
        with self.assertRaises(codec.CodecError):
            self.codec.validate_request(self.profile, "trade_submit", request_frame("trade_submit", payload=payload))

    def test_exact_protocol_descriptor_identity_required(self):
        session = codec.bind_codec_session(self.profile, client_version=100, client_id="fixture")
        requests, responses = dict(self.codec._requests), dict(self.codec._responses)
        requests[2202] = requests[2205]
        with self.assertRaisesRegex(codec.CodecError, "protocol_class_mismatch"):
            codec.SimulateCodec(self.profile, session, request_classes=requests, response_classes=responses)

    def test_handshake_binds_only_exact_channel_once_and_same_login_across_channels(self):
        subject = make_codec(self.profile, quote_connection_id=None, quote_user_id=None,
                             trade_connection_id=None, trade_user_id=None)
        with self.assertRaisesRegex(codec.CodecError, "session_facts"):
            subject.validate_request(self.profile, "quote_runtime", request_frame("quote_runtime"))
        result = subject.accept_handshake(self.profile, "quote", 1, response_frame("quote_init"))
        self.assertEqual(result.as_dict()["quote_connection_id"], 11)
        self.assertIsNone(result.as_dict()["trade_connection_id"])
        self.assertNotIn("connAESKey", result.as_dict())
        subject.validate_request(self.profile, "quote_runtime", request_frame("quote_runtime"))
        with self.assertRaisesRegex(codec.CodecError, "already_bound"):
            subject.accept_handshake(self.profile, "quote", 1, response_frame("quote_init"))
        wrong = response_frame("trade_init", payload={"retType": 0, "s2c": {"connID": 33, "loginUserID": 23}})
        with self.assertRaisesRegex(codec.CodecError, "login_user_mismatch"):
            subject.accept_handshake(self.profile, "trade", 1, wrong)
        subject.accept_handshake(self.profile, "trade", 1, response_frame("trade_init"))
        self.assertEqual(subject.session_binding().as_dict()["quote_connection_id"], 11)
        self.assertEqual(subject.session_binding().as_dict()["trade_connection_id"], 33)

    def test_handshake_missing_or_changed_identity_cannot_rebind(self):
        for facts in ({"connID": 0, "loginUserID": 22}, {"connID": 33},
                      {"connID": 34, "loginUserID": 22}):
            with self.subTest(facts=facts), self.assertRaises(codec.CodecError):
                self.codec.accept_handshake(self.profile, "trade", 1,
                    response_frame("trade_init", payload={"retType": 0, "s2c": facts}))


if __name__ == "__main__":
    unittest.main()
