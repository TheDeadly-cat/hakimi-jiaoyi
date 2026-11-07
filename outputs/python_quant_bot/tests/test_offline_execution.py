"""New isolated synthetic accounts only; no broker, model, old ledger or server."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from exchange_terminal.services.offline_execution import (
    APP_ID, BINDING_SCHEMA, SNAPSHOT_SCHEMA, MAX_ACCOUNT_ORDERS, MAX_REQUEST_BYTES,
    ExecutionError, OfflineExecutionStore, compare_research_context,
)


class OfflineExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hakimi-offline-execution-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "account.sqlite"
        self.rules = dict(max_order_notional="2000", max_total_exposure="3000", max_security_exposure="3000",
                          cash_floor="0", fee_buffer="1", max_account_loss="500", quote_max_age_ms=60000)
        self.store = OfflineExecutionStore.create(self.path, account_id="synthetic-account", initial_cash="1000",
                     securities={"TEST:id": {"symbol": "TEST", "tick_size": "0.01"}}, rules=self.rules)
        self.addCleanup(lambda: self.store.close())
        self.now = 1000000
        self.serial = 0
        self.plan = self.make_plan()

    def make_plan(self, owner="owner-a", strategy="dual_ma", stage="SIMULATION", **changes):
        self.serial += 1
        binding = dict(schema_version=BINDING_SCHEMA, status="COMPLETED", engine_id="terminal.test-v1",
                       strategy_id=strategy, strategy_params={"fast": 5, "slow": 20}, task_id="task-" + owner,
                       task_version=1, input_id="synthetic-input", report_id="report-" + owner, report_hash="a" * 64)
        binding.update(changes)
        return self.store.create_plan("plan-"+str(self.serial), account_id="synthetic-account", owner_id=owner,
                    research_binding=binding, stage=stage)["outcome"]["plan_id"]

    def quote(self, **changes):
        return {**dict(security_id="TEST:id", price="10", as_of=self.now, observed_at=self.now,
                       source_id="explicit-synthetic-fixture", evidence_kind="SYNTHETIC_TEST"), **changes}

    def submit(self, request="order-1", **changes):
        args = dict(account_id="synthetic-account", plan_id=self.plan, security_id="TEST:id", side="BUY",
                    quantity=10, limit_price="10", quote=self.quote(), signal_at=self.now-1000,
                    execution_at=self.now, now_ms=self.now)
        args.update(changes)
        return self.store.submit(request, **args)

    def observation(self, order, *, state="FILLED", quantity=10, notional="100", fee="1", evidence_id=None):
        self.serial += 1
        return dict(evidence_id=evidence_id or "evidence-"+str(self.serial), order_id=order, state=state,
                    cumulative_quantity=quantity, cumulative_notional=notional, cumulative_fee=fee)

    def observe(self, order, **changes):
        observation = self.observation(order, **changes)
        return self.store.observe("observe-"+str(self.serial), account_id="synthetic-account", observation=observation, now_ms=self.now)

    def reconciliation(self, *, observations=None, cash=None, positions=None):
        view = self.store.snapshot()
        if observations is None:
            observations = [self.observation(row["order_id"], state=row["state"], quantity=row["filled"], notional=row["notional"], fee=row["fee"]) for row in view["orders"]]
        return dict(schema_version=SNAPSHOT_SCHEMA, evidence_kind="SYNTHETIC_TEST", account_id="synthetic-account",
                    account_revision=view["revision"], observed_at=self.now, orders=observations,
                    cash=view["cash"] if cash is None else cash, positions=view["positions"] if positions is None else positions)

    def reopen(self):
        self.store.close()
        self.store = OfflineExecutionStore.open(self.path, account_id="synthetic-account")

    def test_plan_binding_is_immutable_and_candidate_labels_do_not_grant_external_permissions(self):
        for stage in ("DRAFT", "BACKTESTED", "LIVE_CANDIDATE"):
            plan = self.make_plan(stage=stage)
            with self.assertRaisesRegex(ExecutionError, "only_simulation_plan"):
                self.submit("forbidden-"+stage, plan_id=plan)
        view = self.store.snapshot()
        self.assertEqual(len(view["orders"]), 0)
        for name, value in view["permissions"].items():
            if name != "local_simulation_allowed":
                self.assertFalse(value)
        self.assertEqual(view["plans"][0]["research_binding"]["task_version"], 1)
        with self.assertRaisesRegex(ExecutionError, "completed_research"):
            self.make_plan(status="UNKNOWN")

    def test_explicit_research_security_is_hash_bound_and_cannot_submit_another_account_symbol(self):
        bound = self.make_plan(security_id="OTHER:id")
        with self.assertRaisesRegex(ExecutionError, "research_security_mismatch"):
            self.submit(plan_id=bound)
        correct = self.make_plan(security_id="TEST:id")
        self.assertNotEqual(bound, correct)
        self.assertEqual(self.submit(plan_id=correct)["outcome"]["status"], "ACCEPTED")
        document = json.loads(self.store.db.execute("SELECT document FROM plans WHERE plan_id=?", (correct,)).fetchone()[0])
        document["research_binding"]["security_id"] = "CHANGED:id"
        self.store.db.execute("UPDATE plans SET document=? WHERE plan_id=?", (json.dumps(document), correct))
        with self.assertRaisesRegex(ExecutionError, "plan_corrupt"):
            self.store.snapshot()

    def test_accepted_and_definitively_rejected_are_distinct_from_fills(self):
        accepted = self.submit()["outcome"]
        rejected = self.submit("order-2", signal_at=self.now-2000, outcome="REJECTED")["outcome"]
        self.assertEqual(accepted["status"], "ACCEPTED")
        self.assertEqual(rejected["status"], "REJECTED")
        view = self.store.snapshot()
        self.assertEqual(view["positions"], [])
        self.assertEqual(Decimal(view["cash"]), 1000)
        self.assertEqual(Decimal(view["reserved_cash"]), 101)

    def test_two_strategies_cannot_spend_the_same_shared_cash(self):
        other = self.make_plan("owner-b", "momentum")
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda args: self.submit(args[0], plan_id=args[1], quantity=80)["outcome"],
                                    [("a", self.plan), ("b", other)]))
        self.assertEqual(sorted(row["status"] for row in outcomes), ["ACCEPTED", "REJECTED"])
        self.assertEqual(next(row["reason"] for row in outcomes if row["status"] == "REJECTED"), "SHARED_CASH_UNAVAILABLE")
        self.assertEqual(Decimal(self.store.snapshot()["available_cash"]), 199)

    def test_global_buy_opportunity_survives_copied_task_and_different_owner(self):
        original = self.submit()["outcome"]["order_id"]
        copied = self.make_plan("owner-b", task_id="copied-task", report_id="different-report", input_id="later-copy")
        outcome = self.submit("copied", plan_id=copied, quantity=20)["outcome"]
        self.assertEqual(outcome, {"status": "DUPLICATE_OPPORTUNITY", "order_id": original, "new_order": False})
        self.assertEqual(len(self.store.snapshot()["orders"]), 1)

    def test_request_retry_returns_same_receipt_and_changed_payload_is_rejected(self):
        first = self.submit()
        before = self.store.snapshot()
        self.assertEqual(self.submit(), first)
        self.assertEqual(self.store.snapshot(), before)
        with self.assertRaisesRegex(ExecutionError, "request_id_conflict"):
            self.submit(quantity=11)
        self.assertEqual(self.store.snapshot(), before)

    def test_partial_fill_and_duplicate_book_only_delta_and_keep_remaining_reservation(self):
        order = self.submit()["outcome"]["order_id"]
        observation = self.observation(order, state="PARTIAL", quantity=4, notional="40", fee="0.4")
        first = self.store.observe("partial", account_id="synthetic-account", observation=observation, now_ms=self.now)
        self.assertEqual(first["outcome"]["status"], "APPLIED")
        view = self.store.snapshot()
        self.assertEqual(Decimal(view["cash"]), Decimal("959.6"))
        self.assertEqual(Decimal(view["reserved_cash"]), Decimal("60.6"))
        self.assertEqual(view["positions"][0]["quantity"], 4)
        again = self.store.observe("same-evidence-new-request", account_id="synthetic-account", observation=observation, now_ms=self.now)
        self.assertEqual(again["outcome"]["status"], "DUPLICATE")
        self.assertEqual(self.store.snapshot()["cash"], view["cash"])

    def test_cancel_ack_keeps_reserves_terminal_cancel_releases_only_remainder_and_fill_can_win(self):
        order = self.submit()["outcome"]["order_id"]
        self.observe(order, state="PARTIAL", quantity=4, notional="40", fee="0.4")
        self.store.cancel("cancel", account_id="synthetic-account", order_id=order, now_ms=self.now)
        self.assertEqual(Decimal(self.store.snapshot()["reserved_cash"]), Decimal("60.6"))
        self.observe(order, state="CANCELLED", quantity=4, notional="40", fee="0.4")
        self.assertEqual(Decimal(self.store.snapshot()["reserved_cash"]), 0)
        self.assertEqual(Decimal(self.store.snapshot()["cash"]), Decimal("959.6"))
        self.observe(order)
        view = self.store.snapshot()
        self.assertEqual(view["orders"][0]["state"], "FILLED")
        self.assertEqual(view["positions"][0]["quantity"], 10)
        self.assertEqual(Decimal(view["cash"]), 899)

    def test_owner_shares_cannot_be_stolen_or_reserved_twice(self):
        buy = self.submit()["outcome"]["order_id"]
        self.observe(buy)
        other = self.make_plan("owner-b", "momentum")
        rejected = self.submit("steal", plan_id=other, side="SELL", quantity=1)["outcome"]
        self.assertEqual(rejected["reason"], "OWNER_SHARES_UNAVAILABLE")
        sell = self.submit("sell", side="SELL", quantity=6)["outcome"]["order_id"]
        blocked = self.submit("too-much", side="SELL", quantity=5, signal_at=self.now-2000)["outcome"]
        self.assertEqual(blocked["reason"], "OWNER_SHARES_UNAVAILABLE")
        self.observe(sell, state="PARTIAL", quantity=2, notional="20", fee="0.2")
        view = self.store.snapshot()
        self.assertEqual(view["positions"], [{"owner_id": "owner-a", "security_id": "TEST:id", "quantity": 8}])
        self.assertEqual(next(row["reserved_shares"] for row in view["orders"] if row["order_id"] == sell), 4)

    def test_timeout_restart_and_missing_query_never_resubmit_or_release_cash(self):
        order = self.submit(outcome="TIMEOUT_UNCONFIRMED")["outcome"]["order_id"]
        self.reopen()
        self.assertTrue(self.store.snapshot()["reconciliation_required"])
        with self.assertRaisesRegex(ExecutionError, "reconciliation_required"):
            self.submit("new", signal_at=self.now-2000)
        missing = self.reconciliation(observations=[])
        result = self.store.reconcile("missing-query", account_id="synthetic-account", complete_snapshot=missing, now_ms=self.now)
        self.assertEqual(result["outcome"]["reason"], "order_absence_does_not_prove_rejection")
        self.assertEqual(Decimal(self.store.snapshot()["reserved_cash"]), 101)
        accepted = self.observation(order, state="ACCEPTED", quantity=0, notional="0", fee="0")
        complete = self.reconciliation(observations=[accepted])
        result = self.store.reconcile("resolved-query", account_id="synthetic-account", complete_snapshot=complete, now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "RECONCILED")
        self.assertEqual(len(self.store.snapshot()["orders"]), 1)
        self.assertEqual(self.submit(outcome="TIMEOUT_UNCONFIRMED")["outcome"]["status"], "TIMEOUT_UNCONFIRMED")
        self.assertEqual(self.store.snapshot()["orders"][0]["state"], "ACCEPTED")

    def test_reopen_and_new_plan_do_not_bypass_explicit_reconciliation(self):
        self.reopen()
        self.make_plan("owner-new", "momentum")
        with self.assertRaisesRegex(ExecutionError, "reconciliation_required"):
            self.submit()
        result = self.store.reconcile("initial-reconcile", account_id="synthetic-account", complete_snapshot=self.reconciliation(), now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "RECONCILED")
        self.assertEqual(self.submit()["outcome"]["status"], "ACCEPTED")

    def test_stale_wrong_account_and_wrong_quote_identity_fail_without_order(self):
        before = self.store.snapshot()
        for changes in ({"account_id": "another-account"}, {"quote": self.quote(as_of=self.now-60001)},
                        {"quote": self.quote(security_id="OTHER")}, {"limit_price": "10.001"}):
            with self.subTest(changes=changes), self.assertRaises(ExecutionError):
                self.submit(**changes)
        self.assertEqual(self.store.snapshot(), before)

    def test_overfill_and_conflicting_cumulative_value_preserve_economic_state_and_stop_risk(self):
        order = self.submit()["outcome"]["order_id"]
        result = self.observe(order, quantity=11, notional="110")
        self.assertEqual(result["outcome"]["status"], "BLOCKED")
        view = self.store.snapshot()
        self.assertEqual(view["positions"], [])
        self.assertEqual(Decimal(view["cash"]), 1000)
        self.assertTrue(view["stop_reason"])
        outcome = self.submit("stopped", signal_at=self.now-2000)["outcome"]
        self.assertEqual(outcome["reason"], "NEW_RISK_STOPPED")

    def test_complete_reconcile_rolls_back_all_fills_when_account_balance_does_not_match(self):
        order = self.submit()["outcome"]["order_id"]
        observation = self.observation(order, state="PARTIAL", quantity=4, notional="40", fee="0.4")
        wrong = self.reconciliation(observations=[observation], cash="999", positions=[])
        result = self.store.reconcile("wrong", account_id="synthetic-account", complete_snapshot=wrong, now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "BLOCKED")
        self.assertEqual(Decimal(self.store.snapshot()["cash"]), 1000)
        right = self.reconciliation(observations=[observation], cash="959.6", positions=[dict(owner_id="owner-a", security_id="TEST:id", quantity=4)])
        result = self.store.reconcile("right", account_id="synthetic-account", complete_snapshot=right, now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "RECONCILED")
        self.assertEqual(self.store.snapshot()["positions"][0]["quantity"], 4)

    def test_unknown_cancel_is_not_reissued_and_reserves_survive_reopen(self):
        order = self.submit()["outcome"]["order_id"]
        self.store.cancel("cancel-lost", account_id="synthetic-account", order_id=order, now_ms=self.now, outcome="TIMEOUT_UNCONFIRMED")
        self.reopen()
        result = self.store.cancel("cancel-again", account_id="synthetic-account", order_id=order, now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "CANCEL_ALREADY_ATTEMPTED")
        self.assertEqual(Decimal(self.store.snapshot()["reserved_cash"]), 101)

    def test_same_evidence_id_changed_payload_stops_without_double_booking(self):
        order = self.submit()["outcome"]["order_id"]
        self.observe(order, state="PARTIAL", quantity=4, notional="40", fee="0.4", evidence_id="source-1")
        previous = self.store.snapshot()
        result = self.observe(order, state="PARTIAL", quantity=5, notional="50", fee="0.5", evidence_id="source-1")
        self.assertEqual(result["outcome"]["reason"], "execution_observation_id_conflict")
        self.assertEqual(self.store.snapshot()["cash"], previous["cash"])
        self.assertEqual(self.store.snapshot()["positions"], previous["positions"])

    def test_late_fees_are_booked_once_even_when_observed_cash_is_negative(self):
        order = self.submit(quantity=99)["outcome"]["order_id"]
        self.observe(order, quantity=99, notional="990", fee="1")
        self.observe(order, quantity=99, notional="990", fee="20", evidence_id="late-fee")
        view = self.store.snapshot()
        self.assertEqual(Decimal(view["cash"]), -10)
        self.assertEqual(view["positions"][0]["quantity"], 99)
        self.assertEqual(view["stop_reason"], "OBSERVED_ACCOUNT_DEFICIT")
        self.observe(order, quantity=99, notional="990", fee="20", evidence_id="late-fee")
        self.assertEqual(Decimal(self.store.snapshot()["cash"]), -10)
        self.reopen()
        self.assertEqual(Decimal(self.store.snapshot()["cash"]), -10)

    def late_cancelled_sell_fixture(self):
        buy = self.submit()["outcome"]["order_id"]
        self.observe(buy)
        first = self.submit("sell-a", side="SELL", quantity=10)["outcome"]["order_id"]
        self.observe(first, state="CANCELLED", quantity=0, notional="0", fee="0")
        second = self.submit("sell-b", side="SELL", quantity=10, signal_at=self.now-2000)["outcome"]["order_id"]
        self.observe(first, state="PARTIAL", quantity=4, notional="40", fee="0.4")
        return first, second

    def test_late_cancelled_sell_overreservation_blocks_new_risk_and_negative_position_cannot_resume(self):
        _, second = self.late_cancelled_sell_fixture()
        view = self.store.snapshot()
        self.assertEqual(view["positions"][0]["quantity"], 6)
        self.assertEqual(view["account_deficits"], [dict(kind="OWNER_SHARES_BELOW_RESERVATION", owner_id="owner-a",
                         security_id="TEST:id", quantity=6, reserved_shares=10)])
        self.assertEqual(view["stop_reason"], "OBSERVED_ACCOUNT_DEFICIT")
        self.assertTrue(view["reconciliation_required"])
        with self.assertRaisesRegex(ExecutionError, "reconciliation_required"):
            self.submit("new-risk", quantity=1, signal_at=self.now-3000)
        self.observe(second, quantity=10, notional="100", fee="1")
        self.assertEqual(self.store.snapshot()["positions"][0]["quantity"], -4)
        with self.assertRaisesRegex(ExecutionError, "reconciliation_required|deficit"):
            self.store.resume("invalid-resume", account_id="synthetic-account", reason="must not clear negative shares")
        self.reopen()
        self.assertEqual(self.store.snapshot()["positions"][0]["quantity"], -4)
        self.assertEqual(self.store.snapshot()["stop_reason"], "OBSERVED_ACCOUNT_DEFICIT")

    def test_legitimate_cancel_release_then_complete_reconcile_retains_late_fill_and_allows_explicit_resume(self):
        first, second = self.late_cancelled_sell_fixture()
        self.observe(second, state="CANCELLED", quantity=0, notional="0", fee="0")
        view = self.store.snapshot()
        self.assertEqual(view["account_deficits"], [])
        self.assertEqual(view["positions"][0]["quantity"], 6)
        self.assertEqual(Decimal(view["cash"]), Decimal("938.6"))
        self.assertEqual(next(row["filled"] for row in view["orders"] if row["order_id"] == first), 4)
        with self.assertRaisesRegex(ExecutionError, "reconciliation_required"):
            self.store.resume("too-soon", account_id="synthetic-account", reason="needs a complete query")
        result = self.store.reconcile("resolved-owner-query", account_id="synthetic-account", complete_snapshot=self.reconciliation(), now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "RECONCILED")
        self.assertEqual(self.store.snapshot()["stop_reason"], "OBSERVED_ACCOUNT_DEFICIT")
        self.store.resume("safe-resume", account_id="synthetic-account", reason="complete synthetic evidence verified")
        self.assertEqual(self.submit("new-risk", quantity=1, signal_at=self.now-3000)["outcome"]["status"], "ACCEPTED")
        self.assertEqual(self.store.snapshot()["positions"][0]["quantity"], 6)

    def test_persisted_stop_cannot_be_removed_without_a_matching_control_event(self):
        self.store.stop("hard-stop", account_id="synthetic-account", reason="explicit operator stop")
        self.store.db.execute("UPDATE meta SET stop_reason=NULL")
        for call in (self.store.snapshot, lambda: self.submit(), lambda: self.store.receipt("hard-stop")):
            with self.assertRaisesRegex(ExecutionError, "stop_state_mismatch"):
                call()

    def test_receipt_identity_and_permission_envelope_is_checked_even_after_local_rehash(self):
        self.submit()
        row = dict(self.store.db.execute("SELECT * FROM requests WHERE request_id='order-1'").fetchone())
        original = json.loads(row["receipt"])
        variants = [{**original, "account_id": "OTHER"}, {**original, "request_id": "OTHER"},
                    {**original, "schema_version": "another-version"},
                    {**original, "permissions": {**original["permissions"], "live_order_allowed": True}}]
        for receipt in variants:
            encoded = json.dumps(receipt, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            self.store.db.execute("UPDATE requests SET receipt=?,receipt_hash=? WHERE request_id='order-1'", (encoded, sha256(encoded.encode()).hexdigest()))
            for call in (self.store.snapshot, lambda: self.store.receipt("order-1"), self.submit):
                with self.assertRaisesRegex(ExecutionError, "receipt_envelope_mismatch"):
                    call()
        self.store.db.execute("UPDATE requests SET receipt=?,receipt_hash=? WHERE request_id='order-1'", (row["receipt"], row["receipt_hash"]))
        self.assertEqual(self.submit(), original)

    def test_account_capacity_stops_before_new_order_and_full_reconciliation_remains_possible(self):
        self.store.close()
        self.path = Path(self.temp.name) / "bounded.sqlite"
        with patch("exchange_terminal.services.offline_execution.MAX_ACCOUNT_ORDERS", 2):
            self.store = OfflineExecutionStore.create(self.path, account_id="synthetic-account", initial_cash="1000",
                securities={"TEST:id": {"symbol": "TEST", "tick_size": "0.01"}}, rules=self.rules)
        self.plan = self.make_plan()
        self.submit("one")
        self.submit("two", signal_at=self.now-2000)
        result = self.submit("over-capacity", signal_at=self.now-3000)
        self.assertEqual(result["outcome"]["status"], "CAPACITY_REACHED")
        self.assertEqual(len(self.store.snapshot()["orders"]), 2)
        self.reopen()
        result = self.store.reconcile("full-query", account_id="synthetic-account", complete_snapshot=self.reconciliation(), now_ms=self.now)
        self.assertEqual(result["outcome"]["status"], "RECONCILED")

    def test_complete_snapshot_maximum_bounded_fields_fit_request_budget(self):
        # Escape expansion for non-ASCII identifiers is included in the bound.
        orders = [dict(evidence_id="观"*155+str(index), order_id="a"*64, state="CANCELLED", cumulative_quantity=10**9,
                       cumulative_notional="1000000000000000.00000000", cumulative_fee="1000000000000000.00000000") for index in range(MAX_ACCOUNT_ORDERS)]
        positions = [dict(owner_id="归"*155+str(index), security_id="证"*80, quantity=10**12) for index in range(MAX_ACCOUNT_ORDERS)]
        document = self.reconciliation(observations=orders, positions=positions)
        self.assertLess(len(json.dumps(dict(snapshot=document, now_ms=self.now), ensure_ascii=True)), MAX_REQUEST_BYTES)

    def test_old_open_evidence_cannot_reopen_terminal_order_in_complete_snapshot(self):
        order = self.submit()["outcome"]["order_id"]
        earlier = self.observation(order, state="ACCEPTED", quantity=0, notional="0", fee="0", evidence_id="open-original")
        self.store.observe("open-original", account_id="synthetic-account", observation=earlier, now_ms=self.now)
        self.observe(order, state="CANCELLED", quantity=0, notional="0", fee="0")
        result = self.store.reconcile("stale-open-query", account_id="synthetic-account", complete_snapshot=self.reconciliation(observations=[earlier]), now_ms=self.now)
        self.assertEqual(result["outcome"]["reason"], "terminal_order_reported_open")
        self.assertEqual(self.store.snapshot()["orders"][0]["state"], "CANCELLED")

    def test_cancelled_owner_exit_cannot_reopen_through_parameter_revision(self):
        bought = self.submit()["outcome"]["order_id"]
        self.observe(bought)
        sell = self.submit("sell", side="SELL", quantity=4)["outcome"]["order_id"]
        self.observe(sell, state="CANCELLED", quantity=0, notional="0", fee="0")
        revised = self.make_plan(strategy_params={"fast": 6, "slow": 20}, task_version=2)
        outcome = self.submit("sell-revised", plan_id=revised, side="SELL", quantity=6)["outcome"]
        self.assertEqual(outcome["status"], "DUPLICATE_OPPORTUNITY")
        self.assertEqual(outcome["order_id"], sell)
        self.assertEqual(self.store.snapshot()["positions"][0]["quantity"], 10)

    def test_per_order_total_security_and_cash_floor_rules_are_immutable(self):
        for field, value, reason in (("max_order_notional", "50", "ORDER_NOTIONAL_LIMIT"),
                                     ("max_total_exposure", "50", "TOTAL_EXPOSURE_LIMIT"),
                                     ("max_security_exposure", "50", "SECURITY_EXPOSURE_LIMIT"),
                                     ("cash_floor", "950", "SHARED_CASH_UNAVAILABLE")):
            with self.subTest(rule=field):
                directory = Path(self.temp.name) / field / "account.sqlite"
                other = OfflineExecutionStore.create(directory, account_id="synthetic-account", initial_cash="1000",
                    securities={"TEST:id": {"symbol": "TEST", "tick_size": "0.01"}}, rules={**self.rules, field: value})
                try:
                    source = self.store.snapshot()["plans"][0]["research_binding"]
                    plan = other.create_plan("plan", account_id="synthetic-account", owner_id="owner-a", research_binding=source)["outcome"]["plan_id"]
                    result = other.submit("order", account_id="synthetic-account", plan_id=plan, security_id="TEST:id", side="BUY", quantity=10,
                        limit_price="10", quote=self.quote(), signal_at=self.now-1000, execution_at=self.now, now_ms=self.now)
                    self.assertEqual(result["outcome"]["reason"], reason)
                    self.assertEqual(Decimal(other.snapshot()["reserved_cash"]), 0)
                finally:
                    other.close()
        self.store.config["rules"]["cash_floor"] = "1"
        with self.assertRaisesRegex(ExecutionError, "config_mismatch"):
            self.submit()

    def test_stale_revision_snapshot_cannot_authorize_later_state(self):
        old = self.reconciliation()
        self.make_plan("other", "momentum")
        with self.assertRaisesRegex(ExecutionError, "revision_changed"):
            self.store.reconcile("old-query", account_id="synthetic-account", complete_snapshot=old, now_ms=self.now)

    def test_context_comparison_separates_explicit_rule_model_and_unknown_cost_differences(self):
        plan = self.store.snapshot()["plans"][0]
        reference = deepcopy(plan["research_binding"])
        reference["strategy_params"]["fast"] = 6
        reference["input_id"] = "different-saved-input"
        reference["source_hash"] = "a" * 64
        before = deepcopy(plan)
        result = compare_research_context(reference, plan, {"fill_model": "NEXT_BAR_OPEN", "quantity_policy": "FRACTIONAL_SHARES"})
        self.assertEqual(result["data"]["input_id"]["status"], "DIFFERENT")
        self.assertEqual(result["rules"]["strategy_params"]["status"], "DIFFERENT")
        self.assertNotIn("source_hash", result["data"])
        self.assertEqual(result["rules"]["source_hash"]["status"], "UNKNOWN")
        self.assertEqual(result["costs"]["status"], "UNKNOWN")
        self.assertEqual(result["execution_assumptions"]["fill_model"]["status"], "DIFFERENT")
        self.assertEqual(result["execution_assumptions"]["timing_policy"]["status"], "UNKNOWN")
        self.assertFalse(result["numeric_performance_comparison_allowed"])
        self.assertEqual(result["unexplained_economic_difference"], "UNKNOWN")
        self.assertEqual(plan, before)

    def test_missing_opportunity_index_and_forged_fill_are_detected_by_event_reconstruction(self):
        order = self.submit()["outcome"]["order_id"]
        self.store.db.execute("DELETE FROM opportunities")
        with self.assertRaisesRegex(ExecutionError, "opportunity_reconstruction"):
            self.store.snapshot()
        terms = json.loads(self.store.db.execute("SELECT terms FROM orders").fetchone()[0])
        self.store.db.execute("INSERT INTO opportunities VALUES(?,?)", (terms["opportunity_id"], order))
        self.store.db.execute("INSERT INTO fills VALUES('forged',?,1,'10','0')", (order,))
        with self.assertRaisesRegex(ExecutionError, "fill_event_mismatch"):
            self.store.snapshot()

    def test_reading_and_reopening_do_not_add_operations_or_fills(self):
        self.submit()
        before = self.store.snapshot()
        self.store.snapshot()
        self.store.receipt("nonexistent")
        self.reopen()
        after = self.store.snapshot()
        self.assertEqual(after["orders"], before["orders"])
        self.assertEqual(after["revision"], before["revision"])
        self.assertEqual(after["cash"], before["cash"])

    def test_foreign_and_corrupted_databases_are_not_adopted(self):
        foreign = Path(self.temp.name) / "foreign.sqlite"
        connection = sqlite3.connect(foreign)
        connection.execute("CREATE TABLE old_history(value TEXT)")
        connection.commit()
        connection.close()
        before = foreign.read_bytes()
        with self.assertRaisesRegex(ExecutionError, "identity_mismatch"):
            OfflineExecutionStore.open(foreign, account_id="synthetic-account")
        self.assertEqual(foreign.read_bytes(), before)
        self.store.db.execute("UPDATE meta SET cash='123'")
        with self.assertRaisesRegex(ExecutionError, "reconstruction_mismatch"):
            self.store.snapshot()

    def test_real_process_exit_before_and_after_commit_keeps_once_only_receipt(self):
        self.store.close()
        script = r'''
import json,os,sys
from exchange_terminal.services.offline_execution import OfflineExecutionStore,SNAPSHOT_SCHEMA
s=OfflineExecutionStore.open(sys.argv[1],account_id='synthetic-account')
v=s.snapshot()
s.reconcile('worker-reconcile-'+sys.argv[3],account_id='synthetic-account',complete_snapshot=dict(schema_version=SNAPSHOT_SCHEMA,evidence_kind='SYNTHETIC_TEST',account_id='synthetic-account',account_revision=v['revision'],observed_at=1000000,orders=[],cash=v['cash'],positions=[]),now_ms=1000000)
if sys.argv[3]=='before':
 old=s._event
 def event(kind,payload):
  if kind=='SYNTHETIC_ORDER_DECLARED':os._exit(41)
  return old(kind,payload)
 s._event=event
else:s._after_commit=lambda:os._exit(42)
s.submit('crash-submit',account_id='synthetic-account',plan_id=sys.argv[2],security_id='TEST:id',side='BUY',quantity=10,limit_price='10',quote=dict(security_id='TEST:id',price='10',as_of=1000000,observed_at=1000000,source_id='explicit-synthetic-fixture',evidence_kind='SYNTHETIC_TEST'),signal_at=999000,execution_at=1000000,now_ms=1000000)
'''
        # The gate may run from the repository root and only amend its own
        # sys.path. Give workers the terminal import root without injecting
        # canonical or frozen dependency directories into their environment.
        worker_root = Path(__file__).resolve().parents[1]
        before = subprocess.run([sys.executable, "-c", script, str(self.path), self.plan, "before"],
                                cwd=worker_root, capture_output=True, text=True, timeout=20)
        self.assertEqual(before.returncode, 41, before.stderr)
        self.store = OfflineExecutionStore.open(self.path, account_id="synthetic-account")
        self.assertEqual(self.store.receipt("crash-submit")["status"], "NOT_RECORDED")
        self.assertEqual(self.store.snapshot()["orders"], [])
        self.store.close()
        after = subprocess.run([sys.executable, "-c", script, str(self.path), self.plan, "after"],
                               cwd=worker_root, capture_output=True, text=True, timeout=20)
        self.assertEqual(after.returncode, 42, after.stderr)
        self.store = OfflineExecutionStore.open(self.path, account_id="synthetic-account")
        self.assertEqual(self.store.receipt("crash-submit")["status"], "COMMITTED")
        self.assertEqual(len(self.store.snapshot()["orders"]), 1)
        self.assertEqual(self.submit("crash-submit"), self.store.receipt("crash-submit")["receipt"])
        self.assertEqual(len(self.store.snapshot()["orders"]), 1)


if __name__ == "__main__":
    unittest.main()
