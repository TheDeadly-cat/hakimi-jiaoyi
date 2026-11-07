"""New TEMP journal plus JSON protobuf fakes; no SDK or external acceptance.

The real journal, v3 profile, handshake acceptance and response-facts factories
are used. Values are fictional; these tests do not prove broker compatibility.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import timedelta
from hashlib import sha256
import unittest
from unittest.mock import patch

from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_execution_plan as contract
from exchange_terminal.services import terminal_broker_response_facts as facts
from exchange_terminal.services import terminal_broker_submit_observation as observation
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_futu_us_equity_simulate_wire_v2 import Response, encode
from tests.test_terminal_broker_request_builder import ConstructibleRequest
from tests import test_terminal_broker_execution_journal as journal_fixture
from tests.test_terminal_broker_execution_journal import AUTHORIZATION_REFERENCE, EVIDENCE
from tests.test_terminal_broker_execution_plan import config
from tests.test_terminal_broker_quote_facts import quote_payload
from tests.test_terminal_broker_wire_profile import fixture, NOW


def make_profile(*, side="BUY"):
    terms = config()
    terms["side"] = side
    args = fixture(terms=terms)
    args["wire_bounds"]["actions"]["quote_market_state"] = 1
    return wire.prepare_wire_profile_v3(**args)


def make_codec(profile):
    session = codec.bind_codec_session(profile, client_version=100, client_id="fictional-v3-observation")
    return codec.SimulateCodec(profile, session,
        request_classes={proto: type("Request", (ConstructibleRequest,), {"full_name": name + ".Request"})
                         for proto, name in codec.PROTO_NAMES_V3.items()},
        response_classes={proto: type("Response", (Response,), {"full_name": name + ".Response"})
                          for proto, name in codec.PROTO_NAMES_V3.items()})


def payload(action):
    if action in observation.HANDSHAKES:
        return {"retType": 0, "s2c": {"serverVer": 107, "connID": 11 if action == "quote_init" else 33,
            "loginUserID": 22, "keepAliveInterval": 30, "connAESKey": "fictional-secret-never-project"}}
    if action == "quote_market_state":
        return {"retType": 0, "s2c": {"marketInfoList": [{"security": {"market": 11, "code": "TSLA"},
            "name": "FICTIONAL", "marketState": 5}]}}
    return quote_payload(action)


class SubmitObservationTests(unittest.TestCase):
    def setUp(self):
        self.h = journal_fixture.JournalTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)
        self.profile = make_profile()
        self.codec = make_codec(self.profile)
        self.serial = 0
        self.cases = 0
        self.frames = {}

    def store(self):
        self.cases += 1
        store = journal.BrokerExecutionJournal(self.h.root / str(self.cases), mode="OFFICIAL_SIMULATION",
            account_id="900000000000001", record_domain="SYNTHETIC_TEST", clock=lambda: self.h.now)
        self.h.instances.append(store)
        return store

    def record(self, store, action, *, response=None, delay=1, save=True):
        self.serial += 1
        frame = self.codec.encode_request(self.profile, action, self.serial)
        event = store.begin_action(self.profile, action, request_id=self.h.request(action),
            frame_sha256=sha256(frame).hexdigest(), frame_bytes=len(frame),
            authorization_id=AUTHORIZATION_REFERENCE, control_barrier=lambda: self.h.barrier(self.profile))["receipt"]
        response = payload(action) if response is None else response
        raw = codec.pack_plaintext_frame(wire.actions_for_profile(self.profile)[action][1], self.serial, encode(response))
        if action in observation.HANDSHAKES:
            self.codec.accept_handshake(self.profile, action.split("_")[0], self.serial, raw)
        self.h.now += timedelta(seconds=delay)
        arguments = dict(profile=self.profile, codec=self.codec, action_receipt=event,
            expected_action_receipt_id=event["id"], request_frame=frame, response_frame=raw, received_at=self.h.now)
        verified = facts.verify_response_facts(**arguments)
        if save:
            store.record_verified_response(verified, request_id=self.h.request("facts"))
        self.frames[action] = arguments
        self.h.now += timedelta(seconds=1)
        return verified

    def ready(self, *, omit=None, change=None, delay=None, side="BUY"):
        self.h.now, self.profile = NOW, make_profile(side=side)
        self.codec = make_codec(self.profile)
        store = self.store()
        for action in observation.HANDSHAKES + observation.QUERIES:
            response = payload(action)
            if change and action == change[0]:
                change[1](response)
            self.record(store, action, response=response, save=action != omit,
                        delay=(delay[1] if delay and delay[0] == action else 1))
        return store

    def prepare(self, store):
        return store.prepare_submit_observation(self.profile, self.codec.session_binding())

    def claim(self, store, bundle, **changes):
        args = dict(evidence_id=EVIDENCE, authorization_id=AUTHORIZATION_REFERENCE,
            request_id=self.h.request("claim"), control_barrier=lambda: self.h.barrier(self.profile),
            submit_observation=bundle, session_binding=self.codec.session_binding())
        args.update(changes)
        return store.claim(self.profile, **args)

    def begin(self, store, bundle, **changes):
        frame = self.codec.encode_request(self.profile, "trade_submit", 77)
        args = dict(request_id=self.h.request("submit"), frame_sha256=sha256(frame).hexdigest(), frame_bytes=len(frame),
            authorization_id=AUTHORIZATION_REFERENCE, control_barrier=lambda: self.h.barrier(self.profile),
            submit_observation=bundle, session_binding=self.codec.session_binding())
        args.update(changes)
        return store.begin_action(self.profile, "trade_submit", **args)

    def reproject(self, store, action):
        args = dict(self.frames[action], received_at=self.h.now)
        store.record_verified_response(facts.verify_response_facts(**args), request_id=self.h.request("late-facts"))

    def test_prepare_is_read_only_immutable_and_keeps_unknown_authority_boundaries(self):
        store = self.ready()
        before = store.read()
        bundle = self.prepare(store)
        self.assertEqual(before, store.read())
        value = bundle.as_dict()
        self.assertEqual(len(value["evidence"]), 6)
        self.assertEqual([r["action"] for r in value["evidence"]], list(observation.HANDSHAKES + observation.QUERIES))
        self.assertEqual(bundle.as_dict(), self.prepare(store).as_dict())
        self.assertIsNone(value["source_age_seconds"])
        for key in ("freshness_verified", "source_authenticated", "fees_known", "trading_authorization_granted"):
            self.assertFalse(value[key])
        self.assertFalse(any(value["permissions"].values()))
        with patch("sqlite3.connect", side_effect=AssertionError("pure barrier must not open the journal")):
            observation.validate_submit_observation(self.profile, bundle, self.codec.session_binding(), self.h.now)
        with self.assertRaises(FrozenInstanceError): bundle._data = b"{}"
        value["evidence"].clear()
        self.assertEqual(len(bundle.as_dict()["evidence"]), 6)
        with self.assertRaisesRegex(observation.SubmitObservationError, "private_factory"):
            observation.VerifiedSubmitObservation(b"{}", object())

    def test_missing_store_prepare_does_not_create_database(self):
        store = self.store()
        with self.assertRaises(ValueError): self.prepare(store)
        self.assertFalse(store.path.exists())
        self.assertIsNone(store.read_submit_observation("fictional-not-recorded"))
        self.assertFalse(store.path.exists())

    def test_six_original_facts_are_mandatory_including_both_actual_handshake_receipts(self):
        for action in observation.HANDSHAKES + observation.QUERIES:
            store = self.ready(omit=action)
            with self.subTest(action=action), self.assertRaisesRegex(observation.SubmitObservationError, "unique_facts"):
                self.prepare(store)

    def test_matching_claim_submit_and_reopen_recover_the_exact_bundle_without_renewal(self):
        store = self.ready()
        self.h.seed(store)
        bundle = self.prepare(store)
        claim = self.claim(store, bundle)
        submitted = self.begin(store, bundle)
        self.assertEqual(claim["receipt"]["payload"]["submit_observation"], bundle.as_dict())
        self.assertFalse(submitted["receipt"]["result"]["dispatch_authorization_granted"])
        operation = submitted["receipt"]["request_id"]
        before = store.read()
        self.assertEqual(before["claims"][self.profile.as_dict()["deduplication"]["intent_scope_id"]]["submit_observation"], bundle.as_dict())
        store.close()
        reopened = journal.BrokerExecutionJournal(self.h.root / str(self.cases), mode="OFFICIAL_SIMULATION",
            account_id="900000000000001", record_domain="SYNTHETIC_TEST",
            clock=lambda: (_ for _ in ()).throw(AssertionError("recovery must not read current clock")))
        self.h.instances.append(reopened)
        restored = reopened.read_submit_observation(operation)
        self.assertIs(type(restored), observation.VerifiedSubmitObservation)
        self.assertEqual(restored.as_dict(), bundle.as_dict())
        self.assertEqual(before, reopened.read())
        with self.assertRaisesRegex(observation.SubmitObservationError, "expired"):
            observation.validate_submit_observation(self.profile, restored, self.codec.session_binding(), NOW + timedelta(minutes=20))

    def test_v2_payloads_and_read_recovery_remain_original(self):
        store = self.store()
        profile = self.h.profile()
        self.h.seed(store)
        claim = self.h.claim(store, profile)
        action = self.h.begin(store, profile)
        self.assertNotIn("submit_observation", claim["receipt"]["payload"])
        self.assertNotIn("submit_observation", action["receipt"]["payload"])
        self.assertIsNone(store.read_submit_observation(action["receipt"]["request_id"]))
        self.assertNotIn("submit_observation", next(iter(store.read()["claims"].values())))

    def test_same_record_ids_replay_after_expiry_without_new_claim_action_or_barrier(self):
        store = self.ready(); self.h.seed(store); bundle = self.prepare(store)
        claimed, submitted = self.claim(store, bundle), self.begin(store, bundle)
        before = store.read()
        self.h.now += timedelta(minutes=20)
        def forbidden_barrier():
            raise AssertionError("original receipt read must not enter a write barrier")
        first = self.claim(store, bundle, request_id=claimed["receipt"]["request_id"], control_barrier=forbidden_barrier)
        second = self.begin(store, bundle, request_id=submitted["receipt"]["request_id"], control_barrier=forbidden_barrier)
        self.assertTrue(first["replayed"] and second["replayed"])
        self.assertEqual(first["receipt"], claimed["receipt"])
        self.assertEqual(second["receipt"], submitted["receipt"])
        self.assertEqual(before, store.read())

    def test_new_claim_and_submit_cannot_accept_missing_or_self_sealed_dict_bundle(self):
        store = self.ready()
        self.h.seed(store)
        bundle = self.prepare(store)
        before = store.read()
        for supplied in (None, bundle.as_dict()):
            with self.subTest(supplied=type(supplied)), self.assertRaisesRegex(journal.JournalError, "typed_submit"):
                self.claim(store, supplied)
        self.assertEqual(before, store.read())
        self.claim(store, bundle)
        before = store.read()
        for supplied in (None, bundle.as_dict()):
            with self.subTest(supplied=type(supplied)), self.assertRaisesRegex(journal.JournalError, "typed_submit"):
                self.begin(store, supplied)
        self.assertEqual(before, store.read())

    def test_pure_validator_rejects_untyped_inputs_and_changed_current_session(self):
        store = self.ready(); bundle = self.prepare(store)
        with self.assertRaisesRegex(observation.SubmitObservationError, "typed_inputs"):
            observation.validate_submit_observation(self.profile, bundle.as_dict(), self.codec.session_binding(), self.h.now)
        session = self.codec.session_binding().as_dict()
        arguments = {key: session[key] for key in ("client_version", "client_id", "quote_connection_id", "quote_user_id",
                                                  "trade_connection_id", "trade_user_id", "broker_order_id")}
        for key, value in (("client_id", "another-client"), ("quote_connection_id", 12), ("trade_user_id", 23)):
            changed = codec.bind_codec_session(self.profile, **{**arguments, key: value})
            with self.subTest(key=key), self.assertRaisesRegex(observation.SubmitObservationError, "session"):
                observation.validate_submit_observation(self.profile, bundle, changed, self.h.now)
            with self.subTest(prepare=key), self.assertRaises(ValueError):
                store.prepare_submit_observation(self.profile, changed)

    def test_fixed_observation_predicates_refuse_bad_or_missing_state_without_inventing_rules(self):
        def basic(response, action):
            return response["s2c"]["staticInfoList" if action == "quote_security" else "snapshotList"][0]["basic"]
        cases = [("quote_runtime", lambda r: r["s2c"].update(qotLogined=False)),
            ("quote_security", lambda r: basic(r, "quote_security").update(delisting=True)),
            ("quote_security", lambda r: basic(r, "quote_security").pop("delisting")),
            ("quote_snapshot", lambda r: basic(r, "quote_snapshot").update(isSuspend=True)),
            ("quote_snapshot", lambda r: basic(r, "quote_snapshot").update(secStatus=0)),
            ("quote_snapshot", lambda r: basic(r, "quote_snapshot").update(lotSize=2)),
            ("quote_snapshot", lambda r: basic(r, "quote_snapshot").update(curPrice=0.)),
            ("quote_market_state", lambda r: r["s2c"]["marketInfoList"][0].update(marketState=3))]
        for action, change in cases:
            store = self.ready(change=(action, change))
            with self.subTest(action=action), self.assertRaises(observation.SubmitObservationError):
                self.prepare(store)

    def test_original_query_start_not_late_received_time_controls_window(self):
        store = self.ready(delay=("quote_runtime", 31))
        with self.assertRaisesRegex(observation.SubmitObservationError, "query_window_expired"):
            self.prepare(store)

    def test_reprojection_cannot_replace_or_refresh_original_unique_query_evidence(self):
        store = self.ready(); bundle = self.prepare(store)
        self.h.seed(store)
        self.reproject(store, "quote_runtime")
        with self.assertRaisesRegex(observation.SubmitObservationError, "unique_facts"):
            self.prepare(store)
        before = store.read()
        with self.assertRaisesRegex(observation.SubmitObservationError, "unique_facts"):
            self.claim(store, bundle)
        self.assertEqual(before, store.read())

    def test_submit_rechecks_journal_evidence_after_claim(self):
        store = self.ready(); self.h.seed(store); bundle = self.prepare(store)
        self.claim(store, bundle)
        self.reproject(store, "quote_runtime")
        before = store.read()
        with self.assertRaisesRegex(observation.SubmitObservationError, "unique_facts"):
            self.begin(store, bundle)
        self.assertEqual(before, store.read())

    def test_submit_requires_same_frozen_bundle_as_claim_even_if_new_bundle_is_unexpired(self):
        store = self.ready(); self.h.seed(store); original = self.prepare(store)
        self.claim(store, original)
        self.h.now += timedelta(seconds=1)
        another = self.prepare(store)
        self.assertNotEqual(original.as_dict()["id"], another.as_dict()["id"])
        with self.assertRaisesRegex(journal.JournalError, "changed_since_claim"):
            self.begin(store, another)

    def test_claim_and_submit_recheck_age_after_control_wait(self):
        for stage in ("claim", "submit"):
            store = self.ready(); self.h.seed(store); bundle = self.prepare(store)
            if stage == "submit": self.claim(store, bundle)
            before = store.read()
            @contextmanager
            def delayed():
                self.h.now = contract._time(bundle.as_dict()["expires_at"]) + timedelta(microseconds=1)
                yield self.profile.as_dict()["control"]
            with self.subTest(stage=stage), self.assertRaisesRegex(observation.SubmitObservationError, "query_window_expired"):
                (self.claim if stage == "claim" else self.begin)(store, bundle, control_barrier=delayed)
            self.assertEqual(before, store.read())

    def test_exact_deadline_is_exclusive_but_original_time_recovery_does_not_renew(self):
        store = self.ready(); self.h.seed(store); bundle = self.prepare(store)
        self.claim(store, bundle)
        submitted = self.begin(store, bundle)["receipt"]
        deadline = contract._time(bundle.as_dict()["expires_at"])
        self.h.now = deadline - timedelta(microseconds=1)
        self.assertEqual(observation.validate_submit_observation(self.profile, bundle,
            self.codec.session_binding(), self.h.now)["id"], bundle.as_dict()["id"])
        self.assertEqual(self.prepare(store).as_dict()["expires_at"], bundle.as_dict()["expires_at"])
        self.h.now = deadline
        with self.assertRaisesRegex(observation.SubmitObservationError, "query_window_expired"):
            observation.validate_submit_observation(self.profile, bundle, self.codec.session_binding(), self.h.now)
        with self.assertRaisesRegex(observation.SubmitObservationError, "query_window_expired"):
            self.prepare(store)
        before = store.read()
        with patch.object(store, "_clock", side_effect=AssertionError("historical recovery must use original ACTION time")):
            restored = store.read_submit_observation(submitted["request_id"])
        self.assertEqual(restored.as_dict(), bundle.as_dict())
        self.assertEqual(observation.validate_archived_submit_observation(self.profile.as_dict(), restored.as_dict(),
            now=contract._time(submitted["at"]))["id"], bundle.as_dict()["id"])
        self.assertEqual(before, store.read())

    def test_frozen_query_age_does_not_discard_older_valid_handshake(self):
        self.h.now = NOW
        store = self.store()
        for action in observation.HANDSHAKES: self.record(store, action)
        self.h.now += timedelta(seconds=60)
        for action in observation.QUERIES: self.record(store, action)
        bundle = self.prepare(store)
        self.assertGreater((self.h.now - contract._time(bundle.as_dict()["evidence"][0]["action_recorded_at"])).total_seconds(), 30)
        observation.validate_submit_observation(self.profile, bundle, self.codec.session_binding(), self.h.now)

    def test_cash_and_owned_position_requirements_remain_mandatory(self):
        for side in ("BUY", "SELL"):
            store = self.ready(side=side)
            self.h.seed(store, cash="0" if side == "BUY" else "100", positions=[])
            bundle = self.prepare(store)
            before = store.read()
            with self.subTest(side=side), self.assertRaisesRegex(journal.JournalError, "shared_cash_or_owner_holdings_insufficient"):
                self.claim(store, bundle)
            self.assertEqual(before, store.read())

    def test_same_original_intent_cannot_claim_again_across_v2_and_v3_in_one_journal(self):
        for first_version in ("v2", "v3"):
            with self.subTest(first_version=first_version):
                self.h.now, self.profile = NOW, make_profile()
                self.codec = make_codec(self.profile)
                legacy = wire.prepare_wire_profile(**fixture())
                for key in ("candidate_config", "candidate_intent", "order", "deduplication"):
                    self.assertEqual(legacy.as_dict()[key], self.profile.as_dict()[key])
                store = self.store()
                if first_version == "v2":
                    snapshot = self.h.seed(store)
                    original = self.h.claim(store, legacy)
                    reserved = store.read()
                    for action in observation.HANDSHAKES + observation.QUERIES:
                        self.record(store, action)
                    bundle = self.prepare(store)
                    self.assertEqual(len(bundle.as_dict()["evidence"]), 6)
                    before = store.read()
                    self.assertEqual(before["financial"], reserved["financial"])
                    self.assertEqual(before["claims"], reserved["claims"])
                    with self.assertRaisesRegex(journal.JournalError, "original_intent_already_claimed"):
                        self.claim(store, bundle)
                else:
                    for action in observation.HANDSHAKES + observation.QUERIES:
                        self.record(store, action)
                    bundle = self.prepare(store)
                    snapshot = self.h.seed(store)
                    original = self.claim(store, bundle)
                    before = store.read()
                    with self.assertRaisesRegex(journal.JournalError, "original_intent_already_claimed"):
                        self.h.claim(store, legacy)
                self.assertGreater(float(before["financial"]["cash_reserved"]), 0)
                self.assertEqual(store.read(), before)
                self.assertEqual(store.read(original["receipt"]["request_id"])["receipt"], original["receipt"])
                self.assertEqual(store.read(snapshot["receipt"]["request_id"])["receipt"], snapshot["receipt"])


if __name__ == "__main__":
    unittest.main()
