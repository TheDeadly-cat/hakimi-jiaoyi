"""Offline request construction with JSON fakes, NOT actual protobuf evidence.

Typed binding fixtures below use the loader's test-only private token and fake
classes. Actual pinned classes belong to a separate isolated package probe.
"""
from copy import deepcopy
from decimal import Decimal
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.adapters import futu_verified_protobuf_loader as loader
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_futu_us_equity_simulate_wire_v2 import (
    Request, make_codec, make_profile, request_frame, request_payload, response_frame,
)
from tests.test_terminal_broker_execution_plan import config
from tests.test_terminal_broker_wire_profile import fixture, REAL


class ConstructibleRequest(Request):
    """The existing JSON fake plus generated-message keyword construction."""
    def __init__(self, data=None, hints=(), **fields):
        super().__init__(fields if fields else data, hints)


def builder(profile=None, **session_changes):
    subject = make_codec(profile, **session_changes)
    subject._requests = {protocol: type("Request", (ConstructibleRequest,),
        {"full_name": name + ".Request"}) for protocol, name in codec.PROTO_NAMES.items()}
    return subject


def fake_bindings(subject, verify=lambda: None, *, data=None):
    runtime = subject._profile["runtime"]
    data = data if data is not None else {key: runtime[key] for key in ("package", "sdk")}
    return loader.VerifiedProtobufBindings(subject._requests, subject._responses,
        json.dumps(data, sort_keys=True).encode(), verify, loader._TOKEN)


class RequestBuilderTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.create_connection", "sqlite3.connect", "subprocess.Popen"):
            blocker = patch(name, side_effect=AssertionError("offline fake request builder"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.profile = make_profile()
        self.codec = builder(self.profile)

    def test_all_twelve_allowed_actions_match_independent_exact_fixture_and_repeat(self):
        for action, (_, protocol) in wire.WIRE_ACTIONS.items():
            if protocol in codec.PROTO_NAMES and wire.PROTOCOL_LIMITS[action]:
                with self.subTest(action=action):
                    actual = self.codec.encode_request(self.profile, action, 77)
                    self.assertEqual(actual, request_frame(action, 77))
                    self.assertEqual(actual, self.codec.encode_request(self.profile, action, 77))
                    self.assertEqual(self.codec.validate_request(self.profile, action, actual).serial, 77)
                    self.assertEqual(json.loads(actual[codec.HEADER_BYTES:]), request_payload(action, 77))

    def test_serial_is_exact_positive_uint32_before_construction(self):
        for serial in (None, False, True, 0, -1, 2**32, 1.0, "1", [], {}):
            with self.subTest(serial=serial), self.assertRaisesRegex(codec.CodecError, "serial_invalid"):
                self.codec.encode_request(self.profile, "trade_submit", serial)
        frame = self.codec.encode_request(self.profile, "trade_submit", 2**32 - 1)
        self.assertEqual(self.codec.validate_request(self.profile, "trade_submit", frame).serial, 2**32 - 1)

    def test_non_string_unknown_disabled_and_transport_actions_refuse(self):
        actions = [None, True, 1, [], {}, b"quote_init", "missing", "QUOTE_INIT"]
        actions.extend(action for action, (_, protocol) in wire.WIRE_ACTIONS.items()
                       if protocol not in codec.PROTO_NAMES or not wire.PROTOCOL_LIMITS[action])
        for action in actions:
            with self.subTest(action=action), self.assertRaisesRegex(codec.CodecError, "action_not_allowed"):
                self.codec.encode_request(self.profile, action, 1)

    def test_profile_type_real_and_changed_identity_refuse(self):
        for profile, reason in ((self.profile.as_dict(), "typed_profile"),
                (wire.prepare_wire_profile(**fixture(REAL)), "simulate_only"),
                (make_profile(max_total_fees="1.00"), "profile_changed")):
            with self.subTest(reason=reason), self.assertRaisesRegex(codec.CodecError, reason):
                self.codec.encode_request(profile, "quote_init", 1)

    def test_session_facts_are_not_invented_and_handshake_enables_next_request(self):
        subject = builder(self.profile, quote_connection_id=None, quote_user_id=None,
                          trade_connection_id=None, trade_user_id=None, broker_order_id=None)
        self.assertEqual(subject.encode_request(self.profile, "quote_init", 1), request_frame("quote_init"))
        for action in ("quote_runtime", "quote_security", "quote_snapshot", "trade_submit"):
            with self.subTest(action=action), self.assertRaisesRegex(codec.CodecError, "session_facts"):
                subject.encode_request(self.profile, action, 2)
        subject.accept_handshake(self.profile, "quote", 1, response_frame("quote_init"))
        self.assertEqual(subject.encode_request(self.profile, "quote_runtime", 2), request_frame("quote_runtime", 2))
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.subTest(action=action), self.assertRaisesRegex(codec.CodecError, "original_order"):
                builder(self.profile, broker_order_id=None).encode_request(self.profile, action, 3)

    def test_decimal_roundtrip_matches_existing_scope_comparison(self):
        for value in (Decimal("20.00000001"), Decimal("0.1"), Decimal("20.10000000")):
            with self.subTest(value=value):
                actual = codec._request_values(value)
                self.assertEqual(Decimal(str(actual)), value)
                self.assertTrue(codec._scope_equal(actual, value))
        for value in (Decimal("20.000000000000001"), Decimal("1e999"), Decimal("1e-999"),
                      Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=value), self.assertRaisesRegex(codec.CodecError, "decimal_not_exact"):
                codec._request_values(value)

    def test_valid_saved_price_that_float_would_round_refuses_before_packing(self):
        terms = config()
        terms.update(limit_price="9999999999.99999999", max_notional="999999999999.00")
        profile = wire.prepare_wire_profile(**fixture(terms=terms))
        with patch.object(codec, "pack_plaintext_frame") as pack:
            with self.assertRaisesRegex(codec.CodecError, "decimal_not_exact"):
                builder(profile).encode_request(profile, "trade_submit", 1)
        pack.assert_not_called()

    def test_numeric_and_scalar_field_types_do_not_silently_coerce(self):
        for value in (True, 3.0, "3", None):
            with self.subTest(value=value), self.assertRaisesRegex(codec.CodecError, "numeric_type"):
                codec._request_values(value, ".c2s.qty")
        for value in (2**53 + 1, 10**999):
            with self.subTest(value=value), self.assertRaisesRegex(codec.CodecError, "integer_not_exact"):
                codec._request_values(value, ".c2s.qty")
        for value in (None, 1.5, object(), b"field"):
            with self.subTest(value=type(value)), self.assertRaisesRegex(codec.CodecError, "field_type"):
                codec._request_values(value)

    def test_new_frame_is_immediately_validated_and_scope_changes_refuse(self):
        with patch.object(self.codec, "validate_request", wraps=self.codec.validate_request) as validate:
            frame = self.codec.encode_request(self.profile, "trade_submit", 5)
        validate.assert_called_once_with(self.profile, "trade_submit", frame)
        original = self.codec._requests[2202]
        class ChangedRequest(original):
            def SerializeToString(self, deterministic=False):
                self.data["c2s"]["price"] = 21.0
                return super().SerializeToString(deterministic=deterministic)
        self.codec._requests[2202] = ChangedRequest
        with self.assertRaisesRegex(codec.CodecError, "scope_mismatch"):
            self.codec.encode_request(self.profile, "trade_submit", 5)

    def test_constructor_required_fields_unknown_fields_and_frame_size_fail_closed(self):
        original = self.codec._requests[1001]
        class RejectFields(original):
            def __init__(self, **fields):
                raise ValueError("unknown protobuf field")
        self.codec._requests[1001] = RejectFields
        with self.assertRaisesRegex(codec.CodecError, "request_fields_invalid"):
            self.codec.encode_request(self.profile, "quote_init", 1)
        class MissingRequired(original):
            def IsInitialized(self): return False
        self.codec._requests[1001] = MissingRequired
        with self.assertRaisesRegex(codec.CodecError, "required_fields_missing"):
            self.codec.encode_request(self.profile, "quote_init", 1)
        class UnknownField(original):
            def __init__(self, data=None, hints=(), **fields):
                super().__init__(data, hints, **fields)
                self.data["_unknown"] = "unexpected"
        self.codec._requests[1001] = UnknownField
        with self.assertRaisesRegex(codec.CodecError, "unknown_or_noncanonical"):
            self.codec.encode_request(self.profile, "quote_init", 1)
        class TooLarge(original):
            def SerializeToString(self, deterministic=False): return b"x" * 65536
        self.codec._requests[1001] = TooLarge
        with self.assertRaisesRegex(codec.CodecError, "frame_length_exceeded"):
            self.codec.encode_request(self.profile, "quote_init", 1)

    def test_factory_rejects_duck_type_subclass_and_runtime_mismatch(self):
        bindings = fake_bindings(self.codec)
        class ForeignBinding(loader.VerifiedProtobufBindings): pass
        foreign = ForeignBinding(bindings.request_classes, bindings.response_classes,
                                 bindings._data, lambda: None, loader._TOKEN)
        for value in (bindings.as_dict(), SimpleNamespace(**{"verify_current": lambda: {}}), foreign):
            with self.subTest(value=type(value)), self.assertRaisesRegex(codec.CodecError, "typed_protobuf_bindings"):
                codec.SimulateCodec.from_verified_bindings(self.profile, self.codec.session_binding(), value)
        for section, key, changed in (("package", "bundle_id", "0" * 64),
                                      ("sdk", "installed_file_count", 99999)):
            data = deepcopy(bindings.as_dict())
            data[section][key] = changed
            with self.subTest(section=section), self.assertRaisesRegex(codec.CodecError, "runtime_mismatch"):
                codec.SimulateCodec.from_verified_bindings(self.profile, self.codec.session_binding(),
                                                         fake_bindings(self.codec, data=data))

    def test_factory_and_each_encode_verify_current_but_old_frame_validation_remains_available(self):
        state = {"current": True, "calls": 0}
        def verify():
            state["calls"] += 1
            if not state["current"]:
                raise loader.ProtobufLoaderError("SYNTHETIC_STALE_BINDING")
        bindings = fake_bindings(self.codec, verify)
        subject = codec.SimulateCodec.from_verified_bindings(self.profile, self.codec.session_binding(), bindings)
        self.assertEqual(state["calls"], 1)
        frame = subject.encode_request(self.profile, "quote_init", 1)
        subject.encode_request(self.profile, "quote_init", 2)
        self.assertEqual(state["calls"], 3)
        state["current"] = False
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "SYNTHETIC_STALE_BINDING"):
            subject.encode_request(self.profile, "quote_init", 3)
        self.assertEqual(subject.validate_request(self.profile, "quote_init", frame).serial, 1)
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "SYNTHETIC_STALE_BINDING"):
            codec.SimulateCodec.from_verified_bindings(self.profile, self.codec.session_binding(), bindings)

    def test_verified_codec_refuses_replaced_request_or_response_class(self):
        for registry in ("_requests", "_responses"):
            subject = codec.SimulateCodec.from_verified_bindings(self.profile, self.codec.session_binding(),
                                                                fake_bindings(self.codec))
            classes = getattr(subject, registry)
            classes[1001] = type("SameDescriptorDifferentSource", (classes[1001],), {})
            with self.subTest(registry=registry), self.assertRaisesRegex(codec.CodecError, "classes_changed"):
                subject.encode_request(self.profile, "quote_init", 1)


if __name__ == "__main__":
    unittest.main()
