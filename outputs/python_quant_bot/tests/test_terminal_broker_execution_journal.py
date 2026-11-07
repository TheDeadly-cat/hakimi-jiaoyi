"""New TEMP-only journal facts; no authorization, SDK, transport or old store.

Every profile and cash/holding/observation value is explicitly SYNTHETIC_TEST.
The pinned SDK manifest inherited from the profile fixture is fictional package
metadata, never a loaded SDK or real broker-account/provenance assertion.
"""
import builtins
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from exchange_terminal.services import terminal_broker_execution_journal as journal
from exchange_terminal.services import terminal_broker_execution_plan as original
from exchange_terminal.services import terminal_broker_wire_profile as wire
from tests.test_terminal_broker_wire_profile import fixture, NOW, SIM, REAL
from tests.test_terminal_broker_execution_plan import config, seal


AUTHORIZATION_REFERENCE = "8" * 64  # Synthetic reference only; grants nothing.
EVIDENCE = "9" * 64
FRAME = "a" * 64


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="new-synthetic-journal-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.now = NOW
        self.counter = 0
        self.instances = []
        self.addCleanup(lambda: [item.close() for item in self.instances])
        imported = builtins.__import__

        def no_sdk(name, *args, **kwargs):
            if name == "futu" or name.startswith("futu."):
                raise AssertionError("SDK imports are forbidden in journal tests")
            return imported(name, *args, **kwargs)

        connect = sqlite3.connect

        def only_new_store(database, *args, **kwargs):
            name = os.fspath(database)
            if name.startswith("file:"):
                name = unquote(urlparse(name).path)
                if os.name == "nt" and name.startswith("/"):
                    name = name[1:]
            if not Path(name).resolve().is_relative_to(self.root):
                raise AssertionError("Only this test's new TEMP SQLite files may be opened")
            return connect(database, *args, **kwargs)

        for target, replacement in (("builtins.__import__", no_sdk), ("sqlite3.connect", only_new_store)):
            blocker = patch(target, side_effect=replacement)
            blocker.start(); self.addCleanup(blocker.stop)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                       "socket.getaddrinfo", "subprocess.Popen", "urllib.request.urlopen"):
            blocker = patch(target, side_effect=AssertionError("No external action in journal tests"))
            blocker.start(); self.addCleanup(blocker.stop)

    def request(self, label="request"):
        self.counter += 1
        return "synthetic-" + label + "-" + str(self.counter).zfill(4)

    def profile(self, *, tag="original", side="BUY", quantity=3, owner=None,
                workspace="7" * 64, fee="1.50", mode=SIM, account=None):
        terms = config()
        terms.update(side=side, quantity=quantity, limit_price="20")
        if account is not None:
            terms["account_id"] = account
        args = fixture(mode, terms=terms)
        if owner is not None:
            # Owner is a real input to the pure candidate/plan fixture, never a
            # mutation of an already verified wire profile.
            resolution = deepcopy(args["research_resolution"])
            resolution["owner_id"] = owner
            args = fixture(mode, terms=terms, resolution=resolution)
        args["candidate_intent"] = seal({**args["candidate_intent"], "request_id": "synthetic-intent-" + tag})
        args["base_plan"] = original.prepare_acceptance_plan(**{
            key: args[key] for key in ("candidate_config", "candidate_intent", "research_resolution",
                                      "runtime_identity", "control", "now")}, bounds=args["base_plan"]["bounds"])
        args["workspace_context"] = workspace
        args["wire_bounds"]["max_total_fees"] = fee
        return wire.prepare_wire_profile(**args)

    def store(self, *, mode=SIM, account="900000000000001", domain="SYNTHETIC_TEST"):
        value = journal.BrokerExecutionJournal(self.root, mode=mode, account_id=account,
                                              record_domain=domain, clock=lambda: self.now)
        self.instances.append(value)
        return value

    @contextmanager
    def barrier(self, profile, *, change=None, after_wait=None):
        if after_wait:
            after_wait()
        current = deepcopy(profile.as_dict()["control"])
        if change:
            current["control"].update(change)
        yield current

    def position(self, profile, quantity):
        value = profile.as_dict()
        return {"owner_scope_id": value["research"]["owner_scope_id"],
                "security_id": value["order"]["security_id"], "quantity": quantity}

    def position_key(self, profile):
        row = self.position(profile, 0)
        row.pop("quantity")
        return original.digest(row)

    def seed(self, store, *, cash="100", positions=(), evidence=EVIDENCE, reconciliation=None, **changes):
        head = store.read()["head"]
        snapshot = {"evidence_id": evidence, "query_started_at": self.now.isoformat(),
                    "observed_at": self.now.isoformat(), "covered_head": head,
                    "valid_until": (self.now + timedelta(seconds=60)).isoformat(),
                    "cash_available": cash, "positions": list(positions)}
        snapshot.update(changes)
        return store.snapshot(snapshot, expected_head=head, request_id=self.request("snapshot"),
                              reconciliation=reconciliation)

    def claim(self, store, profile, **changes):
        args = {"evidence_id": EVIDENCE, "authorization_id": AUTHORIZATION_REFERENCE,
                "request_id": self.request("claim"), "control_barrier": lambda: self.barrier(profile)}
        args.update(changes)
        return store.claim(profile, **args)

    def begin(self, store, profile, action="trade_submit", **changes):
        args = {"request_id": self.request("action"), "frame_sha256": FRAME, "frame_bytes": 100,
                "authorization_id": AUTHORIZATION_REFERENCE, "control_barrier": lambda: self.barrier(profile)}
        if action in ("quote_connect", "trade_connect"):
            args["frame_sha256"] = None
            args["frame_bytes"] = 0
        args.update(changes)
        return store.begin_action(profile, action, **args)

    def outcome(self, store, operation, status="ACKNOWLEDGED", *, broker_id="123456", **changes):
        frame_bytes = operation["receipt"]["payload"]["frame_bytes"]
        value = {"status": status, "evidence_id": original.digest({"synthetic-outcome": self.request()}),
                 "sent_bytes": frame_bytes, "possible_sent_bytes": frame_bytes,
                 "frame_bytes": frame_bytes, "broker_order_id": broker_id,
                 "write_attempted": True, "response_complete": True}
        value.update(changes)
        return store.outcome(operation["receipt"]["request_id"], value, request_id=self.request("outcome"))

    def submitted(self, store, profile, *, broker_id="123456"):
        self.claim(store, profile)
        action = self.begin(store, profile)
        self.outcome(store, action, broker_id=broker_id)
        return action

    def observe(self, store, profile, *, quantity=0, notional="0", fees=None, final=False,
                state="OPEN", broker_id="123456", evidence=None, request_id=None):
        return store.observe(profile.as_dict()["deduplication"]["intent_scope_id"], {
            "evidence_id": evidence or original.digest({"synthetic-observation": self.request()}),
            "broker_order_id": broker_id, "filled_quantity": quantity, "filled_notional": notional,
            "fees": fees, "fees_final": final, "order_state": state},
            request_id=request_id or self.request("observation"))

    def financial(self, store):
        return store.read()["financial"]

    def money_equal(self, actual, expected):
        self.assertEqual(Decimal(actual), Decimal(expected))

    def inventory(self):
        return {str(path.relative_to(self.root)): (sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in self.root.rglob("*") if path.is_file()}

    def test_empty_and_existing_reads_create_no_records_and_domains_modes_are_separate(self):
        sim = self.store()
        external = self.store(domain="EXTERNAL_RECORD")
        real = self.store(mode=REAL)
        self.assertEqual(self.inventory(), {})
        for store in (sim, external, real):
            result = store.read("synthetic-missing-request")
            self.assertEqual(result["event_count"], 0)
            self.assertIsNone(result["receipt"])
            self.assertFalse(any(result["permissions"].values()))
            self.assertFalse(result["automatic_resume"])
        self.assertEqual(self.inventory(), {})
        self.assertEqual(sim.account_scope_id, external.account_scope_id)
        self.assertNotEqual(sim.path, external.path)
        self.assertNotEqual(sim.account_scope_id, real.account_scope_id)
        self.seed(sim)
        before = self.inventory()
        for _ in range(2):
            self.assertEqual(sim.read()["event_count"], 1)
            self.assertEqual(external.read()["event_count"], 0)
            self.assertEqual(real.read()["event_count"], 0)
        self.assertEqual(self.inventory(), before)

    def test_synthetic_profile_cannot_be_promoted_into_external_records(self):
        profile = self.profile()
        store = self.store(domain="EXTERNAL_RECORD")
        self.seed(store)
        before = self.inventory()
        with self.assertRaisesRegex(journal.JournalError, "synthetic_profile_cannot_enter_external_journal"):
            self.claim(store, profile)
        self.assertEqual(store.read()["event_count"], 1)
        self.assertEqual(self.inventory(), before)

    def competing_claims(self, *, side, cash, positions):
        first, second = self.store(), self.store()
        profiles = [self.profile(tag="first", side=side), self.profile(tag="second", side=side)]
        self.seed(first, cash=cash, positions=positions(profiles[0]))
        # Both instances pass the storage precheck before either obtains the
        # writer lock, so the loser must read the winner's committed reserve.
        ready = threading.Barrier(2)
        def worker(store, profile, request_id):
            original_check = store._check_file
            def check():
                original_check()
                ready.wait(timeout=5)
            with patch.object(store, "_check_file", side_effect=check):
                try:
                    return store.claim(profile, evidence_id=EVIDENCE, authorization_id=AUTHORIZATION_REFERENCE,
                                       request_id=request_id, control_barrier=lambda: self.barrier(profile))
                except journal.JournalError as error:
                    return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(worker, store, profile, "synthetic-racing-claim-" + str(index))
                    for index, (store, profile) in enumerate(zip((first, second), profiles))]
            results = [job.result(timeout=10) for job in jobs]
        self.assertEqual(sum(isinstance(row, dict) for row in results), 1, results)
        self.assertIn("journal_shared_cash_or_owner_holdings_insufficient", results)
        self.assertEqual(first.read(), second.read())
        self.assertEqual(first.read()["event_count"], 2)
        self.assertEqual(len(first.read()["claims"]), 1)
        return first, profiles

    def test_two_instances_cannot_reserve_the_same_cash(self):
        store, _ = self.competing_claims(side="BUY", cash="100", positions=lambda _: ())
        self.money_equal(self.financial(store)["cash_reserved"], "61.5")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "38.5")

    def test_two_instances_cannot_reserve_the_same_owner_shares(self):
        store, profiles = self.competing_claims(side="SELL", cash="100", positions=lambda p: [self.position(p, 3)])
        self.assertEqual(self.financial(store)["owner_positions"][self.position_key(profiles[0])], {"quantity": 3, "reserved": 3})

    def test_other_owner_holdings_are_not_available_and_sale_proceeds_are_not_cash(self):
        owner_a = self.profile(side="SELL", owner="family:" + "a" * 32)
        owner_b = self.profile(side="SELL", owner="family:" + "b" * 32)
        store = self.store()
        self.seed(store, cash="10", positions=[self.position(owner_a, 3)])
        with self.assertRaisesRegex(journal.JournalError, "shared_cash_or_owner_holdings_insufficient"):
            self.claim(store, owner_b)
        self.submitted(store, owner_a)
        self.observe(store, owner_a, quantity=3, notional="60", fees="1", final=True, state="FILLED")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "9")
        with self.assertRaisesRegex(journal.JournalError, "shared_cash_or_owner_holdings_insufficient"):
            self.claim(store, self.profile(tag="cannot-spend-proceeds", quantity=1))

    def test_workspace_or_new_profile_does_not_reset_original_intent_claim(self):
        store = self.store()
        self.seed(store)
        original_profile = self.profile()
        self.claim(store, original_profile)
        for changed in (self.profile(workspace="6" * 64), self.profile(fee="1")):
            self.assertNotEqual(changed.as_dict()["id"], original_profile.as_dict()["id"])
            self.assertEqual(changed.as_dict()["deduplication"], original_profile.as_dict()["deduplication"])
            with self.assertRaisesRegex(journal.JournalError, "original_intent_already_claimed"):
                self.claim(self.store(), changed)
        self.assertEqual(store.read()["event_count"], 2)

    def test_claim_and_begin_action_require_current_control_even_after_stop_resume(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        for change in ({"new_intents_blocked": True, "revision": 1}, {"revision": 2}):
            with self.assertRaisesRegex(journal.JournalError, "control_changed_or_stopped"):
                self.claim(store, profile, control_barrier=lambda: self.barrier(profile, change=change))
        self.claim(store, profile)
        for change in ({"new_intents_blocked": True, "revision": 1}, {"revision": 2}):
            with self.assertRaisesRegex(journal.JournalError, "control_changed_or_stopped"):
                self.begin(store, profile, control_barrier=lambda: self.barrier(profile, change=change))
        self.assertEqual(store.read()["event_count"], 2)
        self.assertFalse(next(iter(store.read()["claims"].values()))["submit_started"])

    def test_clock_is_rechecked_after_control_wait_for_claim_and_submit(self):
        def expire():
            self.now = NOW + timedelta(seconds=31)
        store, profile = self.store(), self.profile()
        self.seed(store)
        with self.assertRaisesRegex(journal.JournalError, "account_evidence_stale"):
            self.claim(store, profile, control_barrier=lambda: self.barrier(profile, after_wait=expire))
        self.now = NOW
        self.claim(store, profile)
        with self.assertRaisesRegex(journal.JournalError, "account_evidence_stale_before_dispatch"):
            self.begin(store, profile, control_barrier=lambda: self.barrier(profile, after_wait=expire))
        self.assertEqual(store.read()["event_count"], 2)
        self.now = NOW
        def expire_profile():
            self.now = NOW + timedelta(minutes=10)
        with self.assertRaisesRegex(journal.JournalError, "profile_expired"):
            self.begin(store, profile, "quote_connect", control_barrier=lambda: self.barrier(profile, after_wait=expire_profile))

    def test_actions_are_durable_budget_consumption_and_original_receipt_is_read_only(self):
        store, profile = self.store(), self.profile()
        first = self.begin(store, profile, "quote_connect", request_id="synthetic-connect-original")
        self.assertFalse(first["receipt"]["result"]["dispatch_authorization_granted"])
        store.close()
        reopened = self.store()
        before = self.inventory()
        self.assertEqual(reopened.read("synthetic-connect-original")["receipt"], first["receipt"])
        self.assertEqual(self.inventory(), before)
        with self.assertRaisesRegex(journal.JournalError, "action_budget_exhausted"):
            self.begin(reopened, profile, "quote_connect")
        for action in ("trade_unlock", "quote_reconnect", "application_retry", "push_acceptance"):
            with self.assertRaisesRegex(journal.JournalError, "action_budget_exhausted"):
                self.begin(reopened, profile, action)
        self.assertEqual(reopened.read()["event_count"], 1)
        self.outcome(reopened, first, status="CONNECTED", broker_id=None,
                     sent_bytes=0, possible_sent_bytes=0, write_attempted=False, response_complete=False)
        connected = reopened.read()["actions"]["synthetic-connect-original"]
        self.assertEqual(connected["frame_bytes"], 0)
        self.assertEqual(connected["outcome"]["frame_bytes"], 0)
        self.assertEqual(connected["outcome"]["possible_sent_bytes"], 0)
        self.assertEqual(connected["state"], "CONNECTED")
        self.now = NOW + timedelta(days=1)
        self.assertEqual(reopened.read("synthetic-connect-original")["receipt"], first["receipt"])

    def test_ack_loss_keeps_full_reservation_and_never_allows_broad_order_lookup(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.claim(store, profile)
        action = self.begin(store, profile)
        self.outcome(store, action, status="UNKNOWN", broker_id=None, response_complete=False)
        store.close()
        reopened = self.store()
        self.money_equal(self.financial(reopened)["cash_reserved"], "61.5")
        self.assertFalse(reopened.read()["automatic_resume"])
        for name in ("trade_observe", "trade_cancel", "trade_fees"):
            with self.assertRaisesRegex(journal.JournalError, "exact_original_broker_order_required"):
                self.begin(reopened, profile, name, broker_order_id=None)
            with self.assertRaisesRegex(journal.JournalError, "exact_original_broker_order_required"):
                self.begin(reopened, profile, name, broker_order_id="999999")
        with self.assertRaisesRegex(journal.JournalError, "action_budget_exhausted|unique_reserved_submit_required"):
            self.begin(reopened, profile)
        with self.assertRaisesRegex(journal.JournalError, "unresolved_claim_blocks_rebase"):
            self.seed(reopened, cash="99999")

    def test_partial_fill_and_cancel_ack_keep_remainder_until_terminal_evidence(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        self.observe(store, profile, quantity=1, notional="19")
        self.money_equal(self.financial(store)["cash_reserved"], "41.5")
        cancel = self.begin(store, profile, "trade_cancel", broker_order_id="123456")
        self.outcome(store, cancel)
        self.money_equal(self.financial(store)["cash_reserved"], "41.5")
        claim = next(iter(store.read()["claims"].values()))
        self.assertTrue(claim["cancel_acknowledged"])
        self.assertEqual(claim["order_state"], "OPEN")
        self.observe(store, profile, quantity=1, notional="19", state="CANCELLED")
        self.money_equal(self.financial(store)["cash_reserved"], "1.5")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "79.5")
        with self.assertRaisesRegex(journal.JournalError, "unresolved_claim_blocks_rebase"):
            self.seed(store)
        self.observe(store, profile, quantity=1, notional="19", state="CANCELLED", fees="0.4", final=True)
        self.money_equal(self.financial(store)["cash_reserved"], "0")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "80.6")
        self.assertEqual(self.financial(store)["owner_positions"][self.position_key(profile)], {"quantity": 1, "reserved": 0})

    def test_late_fill_preserves_fact_blocks_new_risk_and_survives_restart(self):
        store = self.store()
        a, b = self.profile(tag="sell-a", side="SELL"), self.profile(tag="sell-b", side="SELL")
        self.seed(store, positions=[self.position(a, 3)])
        self.submitted(store, a, broker_id="111")
        self.observe(store, a, state="CANCELLED", fees="0", final=True, broker_id="111")
        self.submitted(store, b, broker_id="222")
        self.observe(store, a, quantity=1, notional="20", state="CANCELLED", fees="0", final=True, broker_id="111")
        state = self.financial(store)
        self.assertIn("OWNER_HOLDINGS_BELOW_RESERVATIONS", state["reasons"])
        self.assertEqual(state["owner_positions"][self.position_key(a)], {"quantity": 2, "reserved": 3})
        store.close()
        reopened = self.store()
        self.assertEqual(self.financial(reopened), state)
        with self.assertRaisesRegex(journal.JournalError, "reconciliation_required"):
            self.claim(reopened, self.profile(tag="must-stop", quantity=1))
        self.observe(reopened, b, quantity=3, notional="60", state="FILLED", fees="0", final=True, broker_id="222")
        self.assertEqual(self.financial(reopened)["owner_positions"][self.position_key(a)]["quantity"], -1)
        self.assertTrue(self.financial(reopened)["reconciliation_required"])

    def test_late_fact_after_explicit_rebase_is_not_new_available_cash(self):
        store, profile = self.store(), self.profile(side="SELL")
        self.seed(store, positions=[self.position(profile, 3)])
        self.submitted(store, profile)
        self.observe(store, profile, state="CANCELLED", fees="0", final=True)
        self.seed(store, cash="77", positions=[self.position(profile, 3)], evidence="b" * 64)
        self.observe(store, profile, quantity=1, notional="20", state="CANCELLED", fees="0", final=True)
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "77")
        self.assertIn("LATE_OBSERVATION_AFTER_ACCOUNT_REBASE", self.financial(store)["reasons"])
        current_claim = next(iter(store.read()["claims"].values()))
        self.assertEqual(current_claim["filled_quantity"], 1)
        with self.assertRaisesRegex(journal.JournalError, "reconciliation_required"):
            self.claim(store, self.profile(tag="after-rebase", quantity=1), evidence_id="b" * 64)
        self.assertTrue(self.store().read()["financial"]["reconciliation_required"])

    def test_no_dispatch_is_distinct_from_partial_or_uncertain_write(self):
        for sent, attempted in ((1, True), (0, True)):
            with self.subTest(sent=sent, attempted=attempted):
                store = self.store(account=str(900000000000002 + sent))
                profile = self.profile(account=store.scope["account_id"])
                self.seed(store)
                self.claim(store, profile)
                action = self.begin(store, profile)
                with self.assertRaisesRegex(journal.JournalError, "partial_send_is_unknown"):
                    self.outcome(store, action, status="NOT_DISPATCHED", broker_id=None,
                                 sent_bytes=sent, possible_sent_bytes=sent,
                                 write_attempted=attempted, response_complete=False)
                self.outcome(store, action, status="UNKNOWN", broker_id=None,
                             sent_bytes=sent, possible_sent_bytes=sent,
                             write_attempted=attempted, response_complete=False)
                self.money_equal(self.financial(store)["cash_reserved"], "61.5")
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.claim(store, profile)
        action = self.begin(store, profile)
        self.outcome(store, action, status="NOT_DISPATCHED", broker_id=None,
                     sent_bytes=0, possible_sent_bytes=0, write_attempted=False, response_complete=False)
        self.money_equal(self.financial(store)["cash_reserved"], "0")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "100")
        with self.assertRaisesRegex(journal.JournalError, "original_intent_already_claimed"):
            self.claim(store, self.profile(workspace="6" * 64))

    def test_explicit_rejection_keeps_unknown_fee_until_separate_evidence(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.claim(store, profile)
        action = self.begin(store, profile)
        self.outcome(store, action, status="EXPLICIT_REJECTED", broker_id=None)
        self.money_equal(self.financial(store)["cash_reserved"], "1.5")
        claim = next(iter(store.read()["claims"].values()))
        self.assertIsNone(claim["fees"])
        self.assertFalse(claim["fees_final"])
        with self.assertRaisesRegex(journal.JournalError, "unresolved_claim_blocks_rebase"):
            self.seed(store)
        store.rejected_fee_evidence(profile.as_dict()["deduplication"]["intent_scope_id"],
                                    evidence_id="c" * 64, fees="0.25", request_id=self.request("fees"))
        self.money_equal(self.financial(store)["cash_reserved"], "0")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "99.75")

    def test_late_ack_or_rejection_appends_original_unknown_history_without_resubmission(self):
        for index, status in enumerate(("ACKNOWLEDGED", "EXPLICIT_REJECTED")):
            with self.subTest(status=status):
                account = str(900000000000010 + index)
                store, profile = self.store(account=account), self.profile(account=account)
                self.seed(store)
                self.claim(store, profile)
                action = self.begin(store, profile)
                unknown = self.outcome(store, action, status="UNKNOWN", broker_id=None, response_complete=False)
                operation_id = action["receipt"]["request_id"]
                prior = unknown["receipt"]["payload"]["outcome"]
                reply = {**prior, "status": status, "response_complete": True,
                         "evidence_id": "d" * 64, "broker_order_id": "123456" if status == "ACKNOWLEDGED" else None}
                args = {"previous_evidence_id": prior["evidence_id"], "original_frame_sha256": FRAME}
                for changed in ({"previous_evidence_id": "f" * 64}, {"original_frame_sha256": "f" * 64}):
                    with self.assertRaisesRegex(journal.JournalError, "original_unknown_dispatch_required"):
                        store.late_outcome(operation_id, reply, **{**args, **changed}, request_id=self.request("bad-late"))
                store.late_outcome(operation_id, reply, **args, request_id=self.request("late"))
                view = store.read()
                self.assertEqual(len(view["actions"]), 1)
                self.assertEqual([row["status"] for row in view["actions"][operation_id]["outcome_history"]], ["UNKNOWN", status])
                self.assertEqual(store.read(unknown["receipt"]["request_id"])["receipt"], unknown["receipt"])
                with self.assertRaisesRegex(journal.JournalError, "action_budget_exhausted|unique_reserved_submit_required"):
                    self.begin(store, profile)
                self.money_equal(view["financial"]["cash_reserved"], "61.5" if status == "ACKNOWLEDGED" else "1.5")
                self.assertEqual(self.store(account=account).read()["actions"], view["actions"])

    def test_late_ack_preserves_known_partial_send_and_unknown_history_without_second_submit(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.claim(store, profile)
        action = self.begin(store, profile, frame_bytes=64)
        unknown = self.outcome(store, action, status="UNKNOWN", broker_id=None,
                               sent_bytes=2, possible_sent_bytes=64, response_complete=False)
        original_unknown = original.canonical_bytes(unknown["receipt"])
        operation_id = action["receipt"]["request_id"]
        prior = unknown["receipt"]["payload"]["outcome"]
        late = {**prior, "status": "ACKNOWLEDGED", "evidence_id": "d" * 64,
                "broker_order_id": "123456", "response_complete": True}
        store.close()
        reopened = self.store()
        recorded = reopened.late_outcome(operation_id, late, previous_evidence_id=prior["evidence_id"],
                                         original_frame_sha256=FRAME, request_id=self.request("late-partial-ack"))
        self.assertEqual(recorded["receipt"]["result"]["status"], "LATE_OUTCOME_RECORDED")
        view = reopened.read()
        self.assertEqual(len(view["actions"]), 1)
        operation = view["actions"][operation_id]
        self.assertEqual(operation["frame_bytes"], 64)
        self.assertEqual([(row["status"], row["sent_bytes"], row["possible_sent_bytes"])
                          for row in operation["outcome_history"]], [("UNKNOWN", 2, 64), ("ACKNOWLEDGED", 2, 64)])
        self.assertEqual(operation["outcome"]["sent_bytes"], 2)
        self.assertEqual(original.canonical_bytes(reopened.read(unknown["receipt"]["request_id"])["receipt"]), original_unknown)
        self.money_equal(view["financial"]["cash_reserved"], "61.5")
        with self.assertRaisesRegex(journal.JournalError, "action_budget_exhausted|unique_reserved_submit_required"):
            self.begin(reopened, profile, frame_bytes=64)
        self.assertEqual(self.store().read()["actions"], view["actions"])

    def test_outcome_cannot_change_the_original_frame_length_before_or_after_unknown(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.claim(store, profile)
        action = self.begin(store, profile, frame_bytes=64)
        operation_id = action["receipt"]["request_id"]
        for changed_length in (63, 65):
            with self.assertRaisesRegex(journal.JournalError, "original_frame_length_changed"):
                self.outcome(store, action, status="UNKNOWN", broker_id=None, frame_bytes=changed_length,
                             sent_bytes=2, possible_sent_bytes=changed_length, response_complete=False)
        self.assertIsNone(store.read()["actions"][operation_id]["outcome"])
        unknown = self.outcome(store, action, status="UNKNOWN", broker_id=None,
                               sent_bytes=2, possible_sent_bytes=64, response_complete=False)
        prior = unknown["receipt"]["payload"]["outcome"]
        before = store.read()
        for changed_length in (63, 65):
            late = {**prior, "status": "ACKNOWLEDGED", "evidence_id": "d" * 64,
                    "broker_order_id": "123456", "response_complete": True,
                    "frame_bytes": changed_length, "possible_sent_bytes": changed_length}
            with self.assertRaisesRegex(journal.JournalError, "late_complete_response_required"):
                store.late_outcome(operation_id, late, previous_evidence_id=prior["evidence_id"],
                                   original_frame_sha256=FRAME, request_id=self.request("changed-frame"))
        with self.assertRaisesRegex(journal.JournalError, "request_payload_conflict"):
            self.begin(store, profile, request_id=operation_id, frame_bytes=65)
        self.assertEqual(store.read(), before)

    def test_snapshot_requires_new_evidence_and_query_started_after_known_account_facts(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        self.now = NOW + timedelta(seconds=1)
        self.observe(store, profile, quantity=3, notional="60", fees="0", final=True, state="FILLED")
        with self.assertRaisesRegex(journal.JournalError, "snapshot_evidence_already_used"):
            self.seed(store)
        with self.assertRaisesRegex(journal.JournalError, "snapshot_predates_recorded_account_facts"):
            self.seed(store, evidence="b" * 64, query_started_at=NOW.isoformat(),
                      valid_until=(NOW + timedelta(seconds=50)).isoformat())
        with self.assertRaisesRegex(journal.JournalError, "snapshot_freshness_invalid"):
            self.seed(store, evidence="b" * 64, covered_head="f" * 64)
        self.seed(store, cash="75", positions=[self.position(profile, 3)], evidence="b" * 64)
        self.assertEqual(store.read()["epoch"], 2)
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "75")

    def test_conflict_rebase_requires_exact_explicit_review_and_independent_new_snapshot(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        self.observe(store, profile, state="CANCELLED", fees="0", final=True)
        self.observe(store, profile, quantity=1, notional="20", state="CANCELLED", fees="0", final=True)
        view = store.read()
        self.assertIn("LATE_ECONOMIC_CHANGE_AFTER_TERMINAL", view["financial"]["reasons"])
        review = {"evidence_id": "d" * 64, "reviewed_event_head": view["head"],
                  "reviewed_reasons": view["financial"]["reasons"], "reviewed_observation_ids": view["observation_ids"]}
        before = self.inventory()
        with self.assertRaisesRegex(journal.JournalError, "explicit_conflict_reconciliation_required"):
            self.seed(store, evidence="b" * 64)
        for change in ({"reviewed_event_head": "f" * 64}, {"reviewed_reasons": []}, {"reviewed_observation_ids": []}):
            with self.assertRaisesRegex(journal.JournalError, "conflict_review_scope_changed"):
                self.seed(store, evidence="b" * 64, reconciliation={**review, **change})
        self.assertEqual(self.inventory(), before)
        # These new numbers are explicit synthetic independent observations;
        # copying the ledger's projected balance is deliberately not a helper.
        self.seed(store, cash="70", positions=[self.position(profile, 1)], evidence="b" * 64, reconciliation=review)
        self.assertFalse(self.financial(store)["reconciliation_required"])
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "70")
        self.claim(store, self.profile(tag="after-explicit-review", quantity=1), evidence_id="b" * 64)

    def test_stale_open_observation_cannot_downgrade_terminal_fee_finality(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        self.observe(store, profile, quantity=3, notional="60", fees="0.5", final=True, state="FILLED")
        self.observe(store, profile, quantity=3, notional="60", fees="0.5", final=False, state="OPEN")
        claim = next(iter(store.read()["claims"].values()))
        self.assertEqual(claim["order_state"], "FILLED")
        self.assertTrue(claim["fees_final"])
        self.money_equal(self.financial(store)["cash_reserved"], "0")
        self.money_equal(self.financial(store)["cash_available_after_local_liabilities"], "39.5")

    def test_observed_price_quantity_or_fee_limit_breach_is_retained_and_blocks_new_risk(self):
        cases = [("BUY", 1, "30", "0", "OBSERVED_FILL_OUTSIDE_LIMIT_PRICE"),
                 ("SELL", 1, "10", "0", "OBSERVED_FILL_OUTSIDE_LIMIT_PRICE"),
                 ("BUY", 1, "20", "2", "ORDER_OR_FEE_LIMIT_EXCEEDED"),
                 ("BUY", 4, "80", "0", "ORDER_OR_FEE_LIMIT_EXCEEDED")]
        for index, (side, quantity, notional, fees, reason) in enumerate(cases):
            with self.subTest(side=side, quantity=quantity, notional=notional, fees=fees):
                account = str(900000000000020 + index)
                store, profile = self.store(account=account), self.profile(account=account, side=side)
                self.seed(store, cash="300", positions=[self.position(profile, 3)] if side == "SELL" else [])
                self.submitted(store, profile)
                self.observe(store, profile, quantity=quantity, notional=notional, fees=fees)
                view = store.read()
                claim = next(iter(view["claims"].values()))
                self.assertEqual((claim["filled_quantity"], claim["filled_notional"], claim["fees"]),
                                 (quantity, notional, fees))
                self.assertIn(reason, view["financial"]["reasons"])
                with self.assertRaisesRegex(journal.JournalError, "reconciliation_required"):
                    self.claim(store, self.profile(tag="new-risk", quantity=1, account=account))
                self.assertIn(reason, self.store(account=account).read()["financial"]["reasons"])

    def test_filled_final_fee_cumulative_conflict_cannot_be_cleared_by_unreviewed_new_cash(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        self.observe(store, profile, quantity=3, notional="60", fees="0.5", final=True, state="FILLED")
        self.observe(store, profile, quantity=2, notional="40", fees="0.5", final=True, state="FILLED")
        self.observe(store, profile, quantity=3, notional="60", fees="0.5", final=True, state="CANCELLED")
        view = store.read()
        claim = next(iter(view["claims"].values()))
        self.assertEqual(claim["filled_quantity"], 3)
        self.assertEqual(claim["filled_notional"], "60")
        self.assertEqual(claim["order_state"], "FILLED")
        self.assertTrue(claim["fees_final"])
        self.assertEqual(view["financial"]["reasons"], ["CONFLICTING_CUMULATIVE_OBSERVATION", "CONFLICTING_TERMINAL_OBSERVATION"])
        with self.assertRaisesRegex(journal.JournalError, "explicit_conflict_reconciliation_required"):
            self.seed(store, cash="1000", evidence="b" * 64)
        self.assertEqual(store.read(), view)

    def test_commit_then_ack_loss_is_recoverable_by_original_id_without_duplicate(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        request_id = "synthetic-commit-ack-lost"
        commit = store._commit
        def commit_then_lose_ack(connection):
            commit(connection)
            raise OSError("synthetic acknowledgement lost after durable commit")
        with patch.object(store, "_commit", side_effect=commit_then_lose_ack):
            with self.assertRaisesRegex(OSError, "acknowledgement lost"):
                self.claim(store, profile, request_id=request_id)
        store.close()
        reopened = self.store()
        before = self.inventory()
        found = reopened.read(request_id)
        self.assertEqual(found["receipt"]["result"]["status"], "CLAIMED_RESERVED")
        self.assertEqual(found["event_count"], 2)
        self.assertEqual(self.inventory(), before)
        replay = self.claim(reopened, profile, request_id=request_id,
                            control_barrier=lambda: self.fail("Original receipt replay must not reacquire dispatch control"))
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"], found["receipt"])
        self.assertEqual(reopened.read()["event_count"], 2)
        with self.assertRaisesRegex(journal.JournalError, "request_payload_conflict"):
            self.claim(reopened, profile, request_id=request_id, evidence_id="f" * 64)

    def test_precommit_failure_rolls_back_all_local_economic_state(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        request_id = "synthetic-before-commit-loss"
        with patch.object(store, "_commit", side_effect=OSError("synthetic before commit failure")):
            with self.assertRaisesRegex(OSError, "before commit"):
                self.claim(store, profile, request_id=request_id)
        found = self.store().read(request_id)
        self.assertIsNone(found["receipt"])
        self.assertEqual(found["event_count"], 1)
        self.assertEqual(found["claims"], {})
        self.money_equal(found["financial"]["cash_reserved"], "0")

    def test_repeated_cumulative_observation_is_not_summed_and_conflict_is_retained(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        self.submitted(store, profile)
        evidence = "b" * 64
        self.observe(store, profile, quantity=1, notional="20", evidence=evidence)
        duplicate = self.observe(store, profile, quantity=1, notional="20", evidence=evidence)
        self.assertEqual(duplicate["receipt"]["result"]["status"], "DUPLICATE_OBSERVATION")
        self.assertEqual(next(iter(store.read()["claims"].values()))["filled_quantity"], 1)
        with self.assertRaisesRegex(journal.JournalError, "observation_identity_conflict"):
            self.observe(store, profile, quantity=2, notional="40", evidence=evidence)
        conflict = self.observe(store, profile, quantity=0, notional="0")
        self.assertEqual(conflict["receipt"]["result"]["status"], "OBSERVATION_CONFLICT_RETAINED")
        self.assertIn("CONFLICTING_CUMULATIVE_OBSERVATION", self.financial(store)["reasons"])
        self.assertEqual(next(iter(store.read()["claims"].values()))["filled_quantity"], 1)

    def test_wrong_account_mode_and_broker_order_cannot_rebind_existing_claim(self):
        store, profile = self.store(), self.profile()
        self.seed(store)
        for changed in (self.profile(mode=REAL), self.profile(account="900000000000002")):
            with self.assertRaisesRegex(journal.JournalError, "account_mode_mismatch"):
                self.claim(store, changed)
        with self.assertRaisesRegex(journal.JournalError, "verified_wire_profile_required"):
            self.claim(store, profile.as_dict())
        self.submitted(store, profile)
        with self.assertRaisesRegex(journal.JournalError, "broker_order_mismatch"):
            self.begin(store, profile, "trade_observe", broker_order_id="999")
        with self.assertRaisesRegex(journal.JournalError, "observation_order_mismatch"):
            self.observe(store, profile, broker_id="999")

    def test_opaque_broker_order_id_is_preserved_and_observe_cancel_require_exact_original(self):
        store, profile = self.store(), self.profile()
        opaque_id = "US-ORDER-0001"
        self.seed(store)
        self.claim(store, profile)
        submit = self.begin(store, profile)
        for invalid in ("", " " + opaque_id, opaque_id + " ", "US ORDER-0001", "US-\tORDER-0001"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(journal.JournalError, "exact_broker_order_id_required"):
                self.outcome(store, submit, broker_id=invalid)
        ack = self.outcome(store, submit, broker_id=opaque_id)
        self.assertEqual(ack["receipt"]["payload"]["outcome"]["broker_order_id"], opaque_id)
        for changed in ("US-ORDER-0002", "us-order-0001", "1", opaque_id + " "):
            with self.subTest(changed=changed):
                for action in ("trade_observe", "trade_cancel"):
                    with self.assertRaisesRegex(journal.JournalError, "broker_order_mismatch"):
                        self.begin(store, profile, action, broker_order_id=changed)
                with self.assertRaisesRegex(journal.JournalError, "observation_order_mismatch"):
                    self.observe(store, profile, broker_id=changed)
        observation = self.begin(store, profile, "trade_observe", broker_order_id=opaque_id)
        self.assertEqual(observation["receipt"]["payload"]["broker_order_id"], opaque_id)
        self.outcome(store, observation, broker_id=opaque_id)
        self.observe(store, profile, quantity=1, notional="20", broker_id=opaque_id)
        cancellation = self.begin(store, profile, "trade_cancel", broker_order_id=opaque_id)
        self.assertEqual(cancellation["receipt"]["payload"]["broker_order_id"], opaque_id)
        with self.assertRaisesRegex(journal.JournalError, "cancel_ack_order_mismatch"):
            self.outcome(store, cancellation, broker_id="US-ORDER-0002")
        self.outcome(store, cancellation, broker_id=opaque_id)
        self.money_equal(self.financial(store)["cash_reserved"], "41.5")
        self.observe(store, profile, quantity=1, notional="20", fees="0", final=True,
                     state="CANCELLED", broker_id=opaque_id)
        claim = next(iter(self.store().read()["claims"].values()))
        self.assertEqual(claim["broker_order_id"], opaque_id)
        self.assertIsInstance(claim["broker_order_id"], str)
        self.assertEqual(claim["order_state"], "CANCELLED")

    def test_event_mutation_or_head_truncation_is_detected_without_read_repair(self):
        for mutation in ("result", "remove-last"):
            with self.subTest(mutation=mutation):
                account = "900000000000002" if mutation == "result" else "900000000000003"
                store, profile = self.store(account=account), self.profile(account=account)
                self.seed(store)
                self.claim(store, profile)
                with closing(sqlite3.connect(str(store.path))) as connection:
                    if mutation == "result":
                        value = json.loads(connection.execute("SELECT body FROM events WHERE seq=2").fetchone()[0])
                        value["result"]["status"] = "AUTHORIZED_BY_TAMPERING"
                        # A self-consistent seal still cannot override reducer facts.
                        value = seal(value)
                        connection.execute("UPDATE events SET body=? WHERE seq=2", (original.canonical_bytes(value),))
                        connection.execute("UPDATE metadata SET head_hash=?", (value["id"],))
                    else:
                        connection.execute("DELETE FROM events WHERE seq=2")
                    connection.commit()
                before = self.inventory()
                with self.assertRaisesRegex(journal.JournalError, "journal_result_changed|journal_head_changed"):
                    store.read()
                self.assertEqual(self.inventory(), before)

    def test_wal_header_and_hardlink_alias_are_rejected_before_sqlite_read(self):
        store = self.store()
        self.seed(store)
        with closing(sqlite3.connect(str(store.path))) as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        self.assertFalse(Path(str(store.path) + "-wal").exists())
        self.assertFalse(Path(str(store.path) + "-shm").exists())
        before = self.inventory()
        with patch("sqlite3.connect", side_effect=AssertionError("WAL must be rejected before SQLite opens")):
            with self.assertRaisesRegex(journal.JournalError, "delete_mode_required"):
                store.read()
        self.assertEqual(self.inventory(), before)
        # Separate new account: a hardlink is never an accepted storage alias.
        other = self.store(account="900000000000002")
        self.seed(other)
        os.link(other.path, self.root / "synthetic-hardlink.sqlite3")
        before = self.inventory()
        with patch("sqlite3.connect", side_effect=AssertionError("Alias must be rejected before SQLite opens")):
            with self.assertRaisesRegex(journal.JournalError, "regular_unaliased_store_required"):
                other.read()
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    unittest.main()
