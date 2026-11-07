"""Persisted TEMP ACKs plus JSON codec fakes; no SDK or socket evidence.

The original coordinator and journal create each typed identity. Independent
codec instances accept the same fictional handshake responses so this file can
exercise adoption separately from the coordinator's automatic adoption hook.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.adapters import futu_verified_protobuf_loader as loader
from exchange_terminal.services import terminal_broker_order_identity as identity_contract
from tests.broker_submit_market_fixture import SubmitMarketFixture, response_values, SERIALS
from tests.test_futu_us_equity_simulate_wire_v2 import make_codec, make_profile, request_frame, response_frame
from tests.test_terminal_broker_request_builder import fake_bindings
from tests.test_terminal_broker_wire_v3 import v3_codec, v3_profile
from tests import test_terminal_broker_action_coordinator as legacy_tests


class OrderIdentityCodecTests(unittest.TestCase):
    def setUp(self):
        self.helper = legacy_tests.ActionCoordinatorTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)

    def acknowledged(self, *, order_id="fictional-order-44"):
        fixture = SubmitMarketFixture(self.helper.root / ("order-" + str(len(self.helper.fixtures))))
        self.helper.fixtures.append(fixture)
        fixture.initialize()
        fixture.query_all()
        fixture.seed()
        fixture.prepare_submit()
        payload = response_values("trade_submit")
        payload["s2c"]["orderIDEx"] = order_id
        fixture.responses["trade_submit"] = payload
        result = fixture.execute("trade_submit")
        self.assertEqual(result["status"], "ACKNOWLEDGED", result)
        identity = fixture.subject.journal.read_acknowledged_order(fixture.profile)
        self.assertIs(type(identity), identity_contract.VerifiedAcknowledgedOrder)
        self.assertEqual(identity.as_dict()["broker_order_id"], order_id)
        return fixture, identity

    @staticmethod
    def accept_handshakes(subject, profile, *, channels=("quote", "trade"), changes=None):
        for channel in channels:
            action = channel + "_init"
            payload = response_values(action)
            payload["s2c"].update(changes or {})
            subject.accept_handshake(profile, channel, SERIALS[action],
                response_frame(action, SERIALS[action], payload=payload))

    def subject(self, fixture, **changes):
        subject = v3_codec(fixture.profile)
        self.accept_handshakes(subject, fixture.profile, **changes)
        return subject

    def test_v3_constructor_refuses_prebound_string_but_v2_fixture_contract_remains(self):
        with self.assertRaisesRegex(codec.CodecError, "v3_initial_order_identity_forbidden"):
            v3_codec(broker_order_id="fictional-order-44")
        legacy = make_codec()
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            self.assertEqual(legacy.validate_request(make_profile(), action,
                request_frame(action)).protocol, codec.WIRE_ACTIONS[action][1])

    def test_v3_followup_requires_adopted_typed_ack_even_if_a_string_is_injected(self):
        profile = v3_profile()
        subject = v3_codec(profile)
        self.accept_handshakes(subject, profile)
        # Deliberate state fault injection: a string is not a typed ACK receipt.
        subject._session["broker_order_id"] = "fictional-order-44"
        for action in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.subTest(action=action), self.assertRaisesRegex(codec.CodecError, "accepted_acknowledged_order_required"):
                subject.encode_request(profile, action, 31)
        self.assertIsNone(subject.acknowledged_order_identity())

    def test_dict_string_none_and_duck_type_cannot_be_adopted(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        class PretendIdentity:
            def as_dict(self):
                return identity.as_dict()
        for value in (None, identity.as_dict(), "fictional-order-44", PretendIdentity()):
            with self.subTest(value=type(value)), self.assertRaisesRegex(codec.CodecError, "typed_acknowledged_order_required"):
                subject.accept_acknowledged_order(fixture.profile, value)
        self.assertIsNone(subject.acknowledged_order_identity())

    def test_accepted_both_handshakes_required_even_with_prepopulated_connection_ids(self):
        fixture, identity = self.acknowledged()
        for channels in ((), ("quote",), ("trade",)):
            subject = v3_codec(fixture.profile, quote_connection_id=11, quote_user_id=22,
                               trade_connection_id=33, trade_user_id=22)
            self.accept_handshakes(subject, fixture.profile, channels=channels)
            before = subject.session_binding()
            with self.subTest(channels=channels), self.assertRaisesRegex(codec.CodecError, "accepted_handshakes_required"):
                subject.accept_acknowledged_order(fixture.profile, identity)
            self.assertIs(subject.session_binding(), before)

    def test_persisted_identity_is_adopted_without_io_and_encodes_exact_owned_followups(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        before = subject.session_binding().as_dict()
        requests, responses = subject._requests, subject._responses
        database = fixture.subject.journal.path.read_bytes()
        with patch("sqlite3.connect", side_effect=AssertionError("Adoption must not open a journal")):
            accepted = subject.accept_acknowledged_order(fixture.profile, identity)
            self.assertIs(subject.acknowledged_order_identity(), identity)
        after = accepted.as_dict()
        self.assertEqual({k: v for k, v in before.items() if k not in {"id", "broker_order_id"}},
                         {k: v for k, v in after.items() if k not in {"id", "broker_order_id"}})
        self.assertEqual(after["broker_order_id"], "fictional-order-44")
        self.assertIs(subject.accepted_session_binding("quote"), accepted)
        self.assertIs(subject.accepted_session_binding("trade"), accepted)
        self.assertIs(subject._requests, requests); self.assertIs(subject._responses, responses)
        self.assertEqual(fixture.subject.journal.path.read_bytes(), database)
        expected = {"trade_observe": ("filterConditions", "orderIDExList"),
                    "trade_cancel": ("orderIDEx",), "trade_fees": ("orderIdExList",)}
        for action, path in expected.items():
            frame = subject.encode_request(fixture.profile, action, 31)
            self.assertEqual(subject.validate_request(fixture.profile, action, frame).protocol,
                             codec.WIRE_ACTIONS[action][1])
            value = json.loads(frame[codec.HEADER_BYTES:])["c2s"]
            for key in path: value = value[key]
            self.assertEqual(value, "fictional-order-44" if action == "trade_cancel" else ["fictional-order-44"])
        self.assertFalse(any(identity.as_dict()["permissions"].values()))

    def test_same_persisted_identity_is_idempotent_and_returns_original_binding(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        first = subject.accept_acknowledged_order(fixture.profile, identity)
        reread = fixture.subject.journal.read_acknowledged_order(fixture.profile)
        self.assertEqual(reread.as_dict(), identity.as_dict())
        self.assertIs(subject.accept_acknowledged_order(fixture.profile, reread), first)
        self.assertIs(subject.acknowledged_order_identity(), identity)

    def test_distinct_ack_source_cannot_replace_same_order_or_conflicting_order(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        first = subject.accept_acknowledged_order(fixture.profile, identity)
        for order_id in ("fictional-order-44", "fictional-order-55"):
            other, changed = self.acknowledged(order_id=order_id)
            self.assertEqual(other.profile.as_dict()["id"], fixture.profile.as_dict()["id"])
            self.assertNotEqual(changed.as_dict()["id"], identity.as_dict()["id"])
            with self.subTest(order_id=order_id), self.assertRaises((codec.CodecError, identity_contract.AcknowledgedOrderError)):
                subject.accept_acknowledged_order(fixture.profile, changed)
            self.assertIs(subject.session_binding(), first)
            self.assertIs(subject.acknowledged_order_identity(), identity)

    def test_foreign_current_handshake_identity_rejects_without_mutation(self):
        fixture, identity = self.acknowledged()
        for changes in ({"connID": 77}, {"loginUserID": 99}):
            subject = self.subject(fixture, changes=changes)
            before = subject.session_binding()
            with self.subTest(changes=changes), self.assertRaises(identity_contract.AcknowledgedOrderError):
                subject.accept_acknowledged_order(fixture.profile, identity)
            self.assertIs(subject.session_binding(), before)
            self.assertIsNone(subject.acknowledged_order_identity())

    def test_foreign_profile_and_v2_adoption_are_rejected(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        with self.assertRaisesRegex(codec.CodecError, "session_profile_changed"):
            subject.accept_acknowledged_order(v3_profile(max_evidence_age_seconds=3), identity)
        legacy = make_codec()
        with self.assertRaisesRegex(codec.CodecError, "v3_order_identity_required"):
            legacy.accept_acknowledged_order(make_profile(), identity)

    def test_typed_data_tampering_does_not_mutate_codec(self):
        fixture, identity = self.acknowledged()
        subject = self.subject(fixture)
        broken = object.__new__(identity_contract.VerifiedAcknowledgedOrder)
        value = deepcopy(identity.as_dict()); value["broker_order_id"] = "unproved-order"
        object.__setattr__(broken, "_data", json.dumps(value).encode())
        before = subject.session_binding()
        with self.assertRaises(identity_contract.AcknowledgedOrderError):
            subject.accept_acknowledged_order(fixture.profile, broken)
        self.assertIs(subject.session_binding(), before)
        self.assertIsNone(subject.acknowledged_order_identity())

    def test_adoption_preserves_verified_binding_and_followup_encode_rechecks_it(self):
        fixture, identity = self.acknowledged()
        template = v3_codec(fixture.profile)
        state = {"valid": True, "calls": 0}
        def verify():
            state["calls"] += 1
            if not state["valid"]:
                raise loader.ProtobufLoaderError("SYNTHETIC_STALE_BINDING")
        metadata = {key: fixture.profile.as_dict()["runtime"][key] for key in ("package", "sdk")}
        metadata["profile_schema"] = fixture.profile.as_dict()["schema_version"]
        bindings = fake_bindings(template, verify, data=metadata)
        subject = codec.SimulateCodec.from_verified_bindings(fixture.profile, template.session_binding(), bindings)
        self.accept_handshakes(subject, fixture.profile)
        subject.accept_acknowledged_order(fixture.profile, identity)
        self.assertIs(subject._verified_bindings, bindings)
        subject.encode_request(fixture.profile, "trade_observe", 31)
        self.assertGreaterEqual(state["calls"], 2)
        state["valid"] = False
        with self.assertRaisesRegex(loader.ProtobufLoaderError, "SYNTHETIC_STALE_BINDING"):
            subject.encode_request(fixture.profile, "trade_cancel", 32)


if __name__ == "__main__":
    unittest.main()
