"""Explicitly injected protobuf codecs for an OFFLINE, plaintext SIMULATE slice.

There are no SDK imports, sockets, contexts, authorization factories or registry
side effects here. Request/Response classes must be supplied by trusted code.
The fixed wire layout was inspected in futu-api 10.7.6708; fake codec tests do
not prove compatibility with that SDK or an OpenD instance. Encryption and REAL
are deliberately unsupported. A session binding describes supplied facts, not
proof that a handshake, order ownership check or authorization happened.
"""
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha1, sha256
import json
import math
import struct
from threading import Lock

from ..services.terminal_broker_wire_profile import (
    PROTOCOL_POLICY, VerifiedWireProfile, WIRE_ACTIONS,
)

HEADER = struct.Struct("<1s1sI2B2I20s8s")
HEADER_BYTES = HEADER.size
_TOKEN = object()
PROTO_NAMES = {1001: "InitConnect", 1002: "GetGlobalState", 2001: "Trd_GetAccList",
    2101: "Trd_GetFunds", 2102: "Trd_GetPositionList", 3202: "Qot_GetStaticInfo",
    3203: "Qot_GetSecuritySnapshot", 2202: "Trd_PlaceOrder", 2201: "Trd_GetOrderList",
    2205: "Trd_ModifyOrder", 2225: "Trd_GetOrderFee"}


class CodecError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise CodecError(code)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _uint(value, bits=64):
    return type(value) is int and 0 < value < 2 ** bits


def _profile(profile):
    _require(type(profile) is VerifiedWireProfile, "typed_profile_required")
    value = profile.as_dict()
    _require(value["mode"] == "OFFICIAL_SIMULATION" and value["sdk_environment"] == "SIMULATE",
             "simulate_only")
    _require(value.get("protocol_policy") == dict(PROTOCOL_POLICY) and
             value["protocol_policy"]["encryption_policy"] == "PLAINTEXT_OFFLINE_CODEC_TEST",
             "plaintext_offline_policy_required")
    return value


@dataclass(frozen=True, init=False, slots=True)
class CodecSessionBinding:
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN, "codec_private_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def bind_codec_session(profile, *, client_version, client_id,
                       quote_connection_id=None, quote_user_id=None,
                       trade_connection_id=None, trade_user_id=None,
                       broker_order_id=None):
    """Trusted-code input only; never read environment, SysConfig or user files.

    A subsequent binding can contain exact handshake/order facts obtained by a
    future verifier. This module does not invent or authorize those facts.
    """
    value = _profile(profile)
    _require(_uint(client_version, 31), "client_version_required")
    _require(type(client_id) is str and 1 <= len(client_id) <= 64 and
             client_id.isascii() and all(32 < ord(c) < 127 for c in client_id), "client_id_invalid")
    facts = dict(quote_connection_id=quote_connection_id, quote_user_id=quote_user_id,
                 trade_connection_id=trade_connection_id, trade_user_id=trade_user_id)
    _require(all(v is None or _uint(v) for v in facts.values()), "session_identity_invalid")
    _require(broker_order_id is None or (type(broker_order_id) is str and
             1 <= len(broker_order_id) <= 128 and broker_order_id.isascii() and
             all(32 < ord(c) < 127 for c in broker_order_id)), "order_identity_invalid")
    body = {"profile_id": value["id"], "client_version": client_version, "client_id": client_id,
            **facts, "broker_order_id": broker_order_id, "scope": "OFFLINE_CODEC_BINDING_ONLY"}
    return CodecSessionBinding(_json({**body, "id": sha256(_json(body)).hexdigest()}), _TOKEN)


@dataclass(frozen=True, slots=True)
class FrameInfo:
    protocol: int
    serial: int
    body_bytes: int
    frame_sha256: str


def parse_header(header, *, protocol, serial=None, max_frame_bytes=65536):
    _require(type(header) is bytes and len(header) == HEADER_BYTES, "header_length_invalid")
    first, second, proto, fmt, version, seq, length, digest, reserved = HEADER.unpack(header)
    _require((first, second) == (b"F", b"T"), "header_magic_invalid")
    _require(fmt == 0 and version == 0 and reserved == bytes(8), "header_policy_invalid")
    _require(proto == protocol and _uint(seq, 32) and (serial is None or seq == serial),
             "header_request_binding_invalid")
    _require(0 < length <= max_frame_bytes - HEADER_BYTES, "frame_length_exceeded")
    return seq, length, digest


def inspect_frame(frame, *, protocol, serial=None, max_frame_bytes=65536):
    _require(type(frame) is bytes and HEADER_BYTES < len(frame) <= max_frame_bytes, "frame_size_invalid")
    seq, length, digest = parse_header(frame[:HEADER_BYTES], protocol=protocol,
                                      serial=serial, max_frame_bytes=max_frame_bytes)
    _require(len(frame) == HEADER_BYTES + length, "one_frame_required")
    _require(sha1(frame[HEADER_BYTES:]).digest() == digest, "frame_body_hash_invalid")
    return FrameInfo(protocol, seq, length, sha256(frame).hexdigest())


def pack_plaintext_frame(protocol, serial, body):
    """No encrypted or production transport path is provided by this function."""
    _require(type(protocol) is int and _uint(serial, 32) and type(body) is bytes and body,
             "frame_arguments_invalid")
    _require(len(body) + HEADER_BYTES <= 65536, "frame_length_exceeded")
    return HEADER.pack(b"F", b"T", protocol, 0, 0, serial, len(body),
                       sha1(body).digest(), bytes(8)) + body


def _is_repeated(field):
    return bool(field.is_repeated)


def _tree(message, *, presence=False, budget=None, depth=0):
    """Bounded protobuf projection; absent optional facts remain explicitly null."""
    budget = [4096] if budget is None else budget
    _require(depth <= 8, "protobuf_depth_exceeded")
    output = {}
    for field in message.DESCRIPTOR.fields:
        budget[0] -= 1
        _require(budget[0] >= 0, "protobuf_fields_exceeded")
        repeated = _is_repeated(field)
        present = bool(len(getattr(message, field.name))) if repeated else message.HasField(field.name)
        if not present:
            if presence:
                output[field.name] = {"present": False, "value": [] if repeated else None}
            continue
        value = getattr(message, field.name)
        values = list(value) if repeated else [value]
        _require(len(values) <= budget[0] + 1, "protobuf_items_exceeded")
        converted = []
        for item in values:
            budget[0] -= 1
            _require(budget[0] >= 0, "protobuf_fields_exceeded")
            if field.message_type is not None:
                item = _tree(item, presence=presence, budget=budget, depth=depth + 1)
            elif isinstance(item, float):
                _require(math.isfinite(item), "protobuf_nonfinite_value")
            elif isinstance(item, (str, bytes)):
                _require(len(item) <= 8192, "protobuf_scalar_exceeded")
                if isinstance(item, bytes):
                    item = {"bytes_hex": item.hex()}
            converted.append(item)
        value = converted if repeated else converted[0]
        output[field.name] = {"present": True, "value": value} if presence else value
    return output


def _decode(cls, body, *, request):
    message = cls()
    _require(message.DESCRIPTOR.name == ("Request" if request else "Response"), "protobuf_direction_invalid")
    message.ParseFromString(body)
    _require(message.IsInitialized(), "protobuf_required_fields_missing")
    # Unknown/duplicate/noncanonical outbound fields must never evade the exact
    # field comparison. Responses retain original bytes, including unknowns.
    if request:
        encoded = message.SerializeToString(deterministic=True)
        message.DiscardUnknownFields()
        _require(message.SerializeToString(deterministic=True) == encoded == body,
                 "request_unknown_or_noncanonical_fields")
    return message


def _scope_equal(actual, expected, path=""):
    if type(expected) is dict:
        return (type(actual) is dict and set(actual) == set(expected) and
                all(_scope_equal(actual[k], v, path + "." + k) for k, v in expected.items()))
    if type(expected) is list:
        return (type(actual) is list and len(actual) == len(expected) and
                all(_scope_equal(a, e, path + "[]") for a, e in zip(actual, expected)))
    if type(expected) is Decimal:
        return type(actual) is float and math.isfinite(actual) and Decimal(str(actual)) == expected
    if path in (".c2s.qty", ".c2s.adjustSideAndLimit"):
        return type(actual) is float and math.isfinite(actual) and actual == expected
    return type(actual) is type(expected) and actual == expected


@dataclass(frozen=True, slots=True)
class DecodedResponse:
    raw_frame: bytes
    fields_json: bytes
    ret_type: int
    keep_alive_interval: int | None
    """Private raw evidence, not a UI response or proof of economic acceptance."""

    def fields(self):
        return json.loads(self.fields_json)


class SimulateCodec:
    """Exact Request class per action; SDK global Response map is never used."""

    def __init__(self, profile, session, *, request_classes, response_classes):
        self._profile = _profile(profile)
        _require(type(session) is CodecSessionBinding, "typed_session_required")
        self._session = session.as_dict()
        self._session_binding = session
        self._session_lock = Lock()
        self._accepted_channels = set()
        _require(self._session["profile_id"] == self._profile["id"], "session_profile_changed")
        protocols = {proto for _, proto in WIRE_ACTIONS.values() if proto is not None and
                     proto in (1001, 1002, 2001, 2101, 2102, 3202, 3203, 2202, 2201, 2205, 2225)}
        _require(set(request_classes) == protocols == set(response_classes), "exact_codec_map_required")
        for protocol in protocols:
            for classes, direction in ((request_classes, "Request"), (response_classes, "Response")):
                _require(classes[protocol]().DESCRIPTOR.full_name == PROTO_NAMES[protocol] + "." + direction,
                         "protobuf_protocol_class_mismatch")
        self._requests, self._responses = dict(request_classes), dict(response_classes)

    def session_binding(self):
        with self._session_lock:
            return self._session_binding

    def accept_handshake(self, profile, channel, serial, raw_frame):
        """Bind observed protocol identity only; this is no account authorization.

        Raw AES/key material remains in the private response evidence. Neither
        this binding nor the ordinary outcome exports those sensitive fields.
        """
        _require(channel in ("quote", "trade"), "handshake_channel_invalid")
        decoded = self.decode_response(profile, channel + "_init", serial, raw_frame)
        _require(type(decoded.ret_type) is int and decoded.ret_type == 0, "handshake_failed")
        fields = decoded.fields()
        _require(fields.get("s2c", {}).get("present") is True, "handshake_identity_missing")
        facts = fields["s2c"]["value"]
        conn, user = facts.get("connID", {}), facts.get("loginUserID", {})
        _require(conn.get("present") is True and user.get("present") is True and
                 _uint(conn.get("value")) and _uint(user.get("value")), "handshake_identity_missing")
        conn, user = conn["value"], user["value"]
        with self._session_lock:
            _require(channel not in self._accepted_channels, "handshake_already_bound")
            current = self._session
            _require(current[channel + "_connection_id"] in (None, conn) and
                     current[channel + "_user_id"] in (None, user), "handshake_previous_identity_changed")
            other = "trade" if channel == "quote" else "quote"
            _require(current[other + "_user_id"] in (None, user), "handshake_login_user_mismatch")
            arguments = {key: current[key] for key in ("client_version", "client_id", "quote_connection_id",
                "quote_user_id", "trade_connection_id", "trade_user_id", "broker_order_id")}
            arguments[channel + "_connection_id"], arguments[channel + "_user_id"] = conn, user
            binding = bind_codec_session(profile, **arguments)
            self._session_binding, self._session = binding, binding.as_dict()
            self._accepted_channels.add(channel)
            return binding

    def _expected(self, action, serial):
        order, session = self._profile["order"], self._session
        channel, protocol = WIRE_ACTIONS.get(action, (None, None))
        _require(protocol in self._requests and self._profile["wire_bounds"]["actions"].get(action, 0) > 0,
                 "action_not_allowed")
        if action.endswith("_init"):
            return {"clientVer": session["client_version"], "clientID": session["client_id"],
                    "recvNotify": False, "packetEncAlgo": -1, "pushProtoFmt": 0,
                    "programmingLanguage": "Python", "aiType": 0}
        conn, user = session[channel + "_connection_id"], session[channel + "_user_id"]
        _require(_uint(conn) and _uint(user), "verified_session_facts_required")
        header = {"trdEnv": 0, "accID": int(order["account_id"]), "trdMarket": 2}
        _require(_uint(header["accID"]), "account_identity_invalid")
        code = order["asset_code"][3:]
        _require(order["asset_code"].startswith("US.") and code, "saved_us_code_required")
        security = [{"market": 11, "code": code}]
        if action == "quote_runtime":
            return {"userID": user}
        if action == "trade_accounts":
            # This explicitly remains an account-list protocol, not an
            # assertion that the server reads only the selected account.
            return {"userID": user, "trdCategory": 1, "needGeneralSecAccount": False}
        if action == "trade_funds":
            return {"header": header, "refreshCache": True, "currency": 2, "assetCategory": 2}
        if action == "trade_positions":
            return {"header": header, "filterConditions": {"codeList": [code], "filterMarket": 2},
                    "refreshCache": True, "currency": 2, "assetCategory": 2, "optionStrategyView": False}
        if action == "quote_security":
            return {"market": 0, "secType": 0, "securityList": security, "header": {"securityFirm": 0}}
        if action == "quote_snapshot":
            return {"securityList": security, "header": {"securityFirm": 0}}
        packet = {"connID": conn, "serialNo": serial}
        if action == "trade_submit":
            return {"packetID": packet, "header": header, "trdSide": {"BUY": 1, "SELL": 2}[order["side"]],
                    "orderType": 1, "code": code, "qty": order["quantity"],
                    "price": Decimal(order["limit_price"]), "adjustPrice": False,
                    "adjustSideAndLimit": 0, "secMarket": 2, "timeInForce": 0,
                    "fillOutsideRTH": False, "session": 1}
        own = session["broker_order_id"]
        _require(own is not None, "verified_original_order_id_required")
        if action == "trade_observe":
            return {"header": header, "filterConditions": {"codeList": [code],
                    "orderIDExList": [own], "filterMarket": 2}, "refreshCache": True}
        if action == "trade_cancel":
            # The pinned SDK marks numeric orderID obsolete but required: 0;
            # actual ownership is bound to its original orderIDEx string.
            return {"packetID": packet, "header": header, "orderID": 0,
                    "orderIDEx": own, "modifyOrderOp": 2, "forAll": False}
        if action == "trade_fees":
            return {"header": header, "orderIdExList": [own]}
        raise CodecError("action_not_allowed")

    def validate_request(self, profile, action, frame):
        value = _profile(profile)
        _require(value["id"] == self._profile["id"], "codec_profile_changed")
        protocol = WIRE_ACTIONS.get(action, (None, None))[1]
        _require(protocol in self._requests, "action_not_allowed")
        info = inspect_frame(frame, protocol=protocol, max_frame_bytes=value["wire_bounds"]["max_frame_bytes"])
        message = _decode(self._requests[protocol], frame[HEADER_BYTES:], request=True)
        actual = _tree(message)
        expected = {"c2s": self._expected(action, info.serial)}
        _require(_scope_equal(actual, expected), "request_scope_mismatch")
        return info

    def response_header(self, profile, action, serial, header):
        _require(_profile(profile)["id"] == self._profile["id"], "codec_profile_changed")
        return parse_header(header, protocol=WIRE_ACTIONS[action][1], serial=serial,
                            max_frame_bytes=self._profile["wire_bounds"]["max_frame_bytes"])[1]

    def decode_response(self, profile, action, serial, frame):
        _require(_profile(profile)["id"] == self._profile["id"], "codec_profile_changed")
        protocol = WIRE_ACTIONS[action][1]
        inspect_frame(frame, protocol=protocol, serial=serial,
                      max_frame_bytes=self._profile["wire_bounds"]["max_frame_bytes"])
        message = _decode(self._responses[protocol], frame[HEADER_BYTES:], request=False)
        fields = _tree(message, presence=True)
        encoded = _json(fields)
        _require(len(encoded) <= self._profile["wire_bounds"]["max_output_bytes"] -
                 self._profile["wire_bounds"]["reserved_final_output_bytes"], "response_projection_exceeded")
        interval = None
        if action.endswith("_init") and message.HasField("s2c") and message.s2c.HasField("keepAliveInterval"):
            interval = message.s2c.keepAliveInterval
        return DecodedResponse(frame, encoded, message.retType, interval)
