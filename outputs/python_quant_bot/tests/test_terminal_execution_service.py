"""Service tests use only new temporary synthetic accounts and a fake resolver."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import Mock, patch

from exchange_terminal.services.offline_execution import BINDING_SCHEMA, SNAPSHOT_SCHEMA, OfflineExecutionStore
from exchange_terminal.services.terminal_execution_service import TerminalExecutionService, READ_RESOURCES, MUTATION_ACTIONS


class TerminalExecutionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="terminal-execution-service-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "current-workspace"
        self.resolver = Mock(side_effect=self.resolve)
        self.service = TerminalExecutionService(self.workspace, self.resolver)
        self.addCleanup(lambda: self.service.close())
        self.creation = dict(client_request_id="create-account-0001", account_id="synthetic-account-a", label="Explicit synthetic A",
            evidence_kind="SYNTHETIC_TEST", initial_cash="1000", securities={"TEST:id": {"symbol": "TEST", "tick_size": "0.01"}},
            rules=dict(max_order_notional="2000", max_total_exposure="3000", max_security_exposure="3000", cash_floor="0",
                       fee_buffer="1", max_account_loss="500", quote_max_age_ms=60000))
        self.now = 1000000

    @staticmethod
    def resolve(reference):
        identifier = reference["id"]
        if identifier == "missing":
            raise ValueError("saved_report_not_available")
        binding = dict(schema_version=BINDING_SCHEMA, status="UNKNOWN" if identifier == "unknown" else "COMPLETED",
                       engine_id="research.accepted-equity" if reference["kind"] == "core_run" else "terminal.test-v1",
                       strategy_id="momentum" if identifier == "other-strategy" else "dual_ma", strategy_params={"fast": 5, "slow": 20},
                       task_id="task-"+identifier, task_version=2 if identifier == "version-two" else 1,
                       input_id="synthetic-input", report_id=identifier, report_hash=sha256(identifier.encode()).hexdigest(), security_id="TEST:id")
        if identifier == "authority":
            binding["risk"] = {"live_order_allowed": True}
        owner = "task:"+binding["task_id"] if identifier.startswith("legacy") else "family:"+("other" if identifier == "other-strategy" else "verified-family")
        return dict(binding=binding, owner_id=owner, assumptions={"fill_model": "NEXT_BAR_OPEN"},
                    display=dict(security_id="TEST:id", symbol="TEST", currency="USD", asset_class="US_EQUITY"))

    def create(self, **changes):
        return self.service.mutate("terminal_execution_create_account", {**deepcopy(self.creation), **changes})

    def selected(self, account_id="synthetic-account-a"):
        view = self.service.read("terminal_execution_account", account_id)
        return dict(account_id=account_id, account_context=view["account_context"])

    def plan(self, request="create-plan-0001", kind="terminal_run", identity="run-one", stage="SIMULATION", **changes):
        payload = dict(client_request_id=request, **self.selected(), reference={"kind": kind, "id": identity}, stage=stage)
        payload.update(changes)
        return self.service.mutate("terminal_execution_create_plan", payload)

    def submit_payload(self, plan_id, request="submit-order-0001", **changes):
        payload = dict(client_request_id=request, **self.selected(), plan_id=plan_id, security_id="TEST:id", side="BUY", quantity=10,
                       limit_price="10", quote=dict(security_id="TEST:id", price="10", as_of=self.now, observed_at=self.now,
                       source_id="explicit-synthetic-fixture", evidence_kind="SYNTHETIC_TEST"), signal_at=self.now-1000,
                       execution_at=self.now, now_ms=self.now, outcome="ACCEPTED")
        payload.update(changes)
        return payload

    def saved_envelope(self, reference):
        binding = self.resolve(reference)["binding"]
        return dict(verification_status="VERIFIED_RECORD", id=reference["id"], report=dict(
            schema_version="hakimi-terminal-run-v1", id=binding["report_hash"], report_hash=binding["report_hash"],
            run_id=binding["report_id"], task_id=binding["task_id"], version=binding["task_version"],
            engine_id=binding["engine_id"], strategy_id=binding["strategy_id"], status="COMPLETED",
            configuration={"input_id": binding["input_id"], "strategy_params": binding["strategy_params"]},
            input_summary={"id": binding["input_id"]}, result={"total_return_pct": 0}))

    def explanation_request(self):
        self.create()
        plan = self.plan()["receipt"]["outcome"]["plan_id"]
        self.service.read_saved_result = Mock(side_effect=self.saved_envelope)
        self.resolver.reset_mock()
        return dict(**self.selected(), plan_id=plan, reference={"kind": "terminal_run", "id": "run-one"})

    def test_explanation_checks_context_before_callbacks_and_never_accepts_client_proof(self):
        payload = self.explanation_request()
        for changes in ({"account_context": None}, {"account_context": "stale"},
                        {"projection": {}}, {"research_binding": {}}, {"snapshot": {}},
                        {"reference": {"kind": "terminal_run", "id": "run-one", "status": "COMPLETED"}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.service.read("terminal_execution_explanation", {**payload, **changes})
        self.resolver.assert_not_called()
        self.service.read_saved_result.assert_not_called()

    def test_explanation_uses_one_verified_snapshot_without_history_or_mutation(self):
        payload = self.explanation_request()
        store = self.service._stores[payload["account_id"]]["store"]
        before = store.snapshot()
        with patch.object(store, "snapshot", wraps=store.snapshot) as snapshot, \
                patch.object(store, "history", side_effect=AssertionError("not a history tail")), \
                patch.object(store, "_mutate", side_effect=AssertionError("read cannot write")):
            value = self.service.read("terminal_execution_explanation", json.dumps(payload))
        self.assertEqual(snapshot.call_count, 1)
        self.assertEqual(value["scope"]["ledger_revision"], before["revision"])
        self.assertEqual(value["account_context"], payload["account_context"])
        self.assertEqual(value["status"], "BOUND_REPORT_CONTEXT_ONLY")
        self.assertFalse(value["attribution"]["numeric_performance_comparison_allowed"])
        self.assertEqual(store.snapshot(), before)
        self.resolver.assert_called_once_with(payload["reference"])
        self.service.read_saved_result.assert_called_once_with(payload["reference"])

    def test_explanation_rejects_changed_selection_during_trusted_read(self):
        payload = self.explanation_request()
        entry = self.service._stores[payload["account_id"]]
        def changed(reference):
            entry["context"] = "new-selection"
            return self.saved_envelope(reference)
        self.service.read_saved_result.side_effect = changed
        with patch.object(entry["store"], "snapshot", wraps=entry["store"].snapshot) as snapshot:
            with self.assertRaisesRegex(ValueError, "stale_account_context"):
                self.service.read("terminal_execution_explanation", payload)
            snapshot.assert_not_called()

    def test_explanation_rejects_mixed_saved_reads_and_foreign_plan_without_repair(self):
        payload = self.explanation_request()
        store = self.service._stores[payload["account_id"]]["store"]
        before = store.snapshot()
        self.service.read_saved_result.side_effect = lambda _: self.saved_envelope({"kind": "terminal_run", "id": "run-other"})
        with self.assertRaisesRegex(ValueError, "projection_binding_mismatch"):
            self.service.read("terminal_execution_explanation", payload)
        self.service.read_saved_result.side_effect = self.saved_envelope
        with self.assertRaisesRegex(ValueError, "plan_not_found"):
            self.service.read("terminal_execution_explanation", {**payload, "plan_id": "f"*64})
        self.assertEqual(store.snapshot(), before)

    def test_explanation_read_serializes_account_mutation_and_keeps_one_revision(self):
        payload = self.explanation_request()
        before = self.service._stores[payload["account_id"]]["store"].snapshot()["revision"]
        entered, release, mutation_started = Event(), Event(), Event()
        def blocked_reader(reference):
            entered.set()
            if not release.wait(5):
                raise AssertionError("test read was not released")
            return self.saved_envelope(reference)
        self.service.read_saved_result.side_effect = blocked_reader
        def stop():
            mutation_started.set()
            return self.service.mutate("terminal_execution_stop", dict(client_request_id="stop-explanation-race",
                account_id=payload["account_id"], account_context=payload["account_context"], reason="explicit synthetic pause"))
        with ThreadPoolExecutor(max_workers=2) as pool:
            reading = pool.submit(self.service.read, "terminal_execution_explanation", payload)
            try:
                self.assertTrue(entered.wait(3))
                mutation = pool.submit(stop)
                self.assertTrue(mutation_started.wait(3))
                self.assertFalse(mutation.done())
            finally:
                release.set()
            value, stopped = reading.result(timeout=5), mutation.result(timeout=5)
        self.assertEqual(value["scope"]["ledger_revision"], before)
        self.assertGreater(stopped["receipt"]["revision"], before)
        self.assertIsNone(value["groups"][-1]["items"][-1]["simulation"]["value"]["stop_reason"])

    def test_lazy_reads_and_unknown_routes_have_no_creation_or_resolver_effects(self):
        self.assertFalse(self.workspace.exists())
        self.assertEqual(self.service.read("terminal_execution_accounts")["items"], [])
        for resource, identity in (("terminal_execution_account", "synthetic-missing"), ("terminal_execution_unknown", None)):
            with self.assertRaises(ValueError):
                self.service.read(resource, identity)
        with self.assertRaisesRegex(ValueError, "unknown_action"):
            self.service.mutate("terminal_execution_live_order", {})
        self.assertFalse(self.workspace.exists())
        self.resolver.assert_not_called()

    def test_research_identity_read_uses_trusted_fields_without_creating_workspace(self):
        reference = {"kind": "terminal_run", "id": "run-one"}
        missing = self.resolve(reference)
        missing.pop("display")
        self.resolver.side_effect = lambda _: deepcopy(missing)
        result = self.service.read("terminal_execution_research", {"reference": reference})
        self.assertEqual(result["binding"]["report_id"], "run-one")
        self.assertEqual(result["display"], {})
        self.assertFalse(self.workspace.exists())
        self.resolver.assert_called_once_with(reference)
        resolved = self.resolve(reference)
        resolved["display"] = dict(symbol="TEST", security_id="TEST:id", currency="USD", quantity_unit="shares", asset_class="US_EQUITY")
        self.resolver.side_effect = lambda _: deepcopy(resolved)
        result = self.service.read("terminal_execution_research", {"reference": reference})
        self.assertEqual(result["display"], resolved["display"])
        self.assertFalse(self.workspace.exists())
        with self.assertRaises(ValueError):
            self.service.read("terminal_execution_research", {"reference": reference, "display": {"symbol": "FORGED"}})

    def test_account_creation_is_explicit_idempotent_and_rejects_client_paths(self):
        for changes in ({"path": "outside.sqlite"}, {"account_id": "../../outside"}, {"evidence_kind": "REAL_ACCOUNT"}):
            with self.assertRaises(ValueError):
                self.create(**changes)
        self.assertFalse(self.workspace.exists())
        created = self.create()
        self.assertEqual(created["status"], "ACCOUNT_CREATED")
        again = self.create()
        self.assertTrue(again["reused"])
        self.assertEqual(again["account_context"], created["account_context"])
        self.assertEqual(len(self.service.read("terminal_execution_accounts")["items"]), 1)
        with self.assertRaisesRegex(ValueError, "creation_conflict"):
            self.create(initial_cash="2000")
        self.assertEqual(self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]["cash"], "1000")

    def test_plan_uses_only_trusted_resolver_values_and_rejects_client_owner_or_binding(self):
        self.create()
        for changes in ({"owner_id": "victim-owner"}, {"research_binding": self.resolve({"kind": "terminal_run", "id": "forged"})["binding"]},
                        {"reference": {"kind": "terminal_run", "id": "run-one", "status": "COMPLETED"}}):
            with self.assertRaises(ValueError):
                self.plan(**changes)
        self.resolver.assert_not_called()
        result = self.plan()
        self.resolver.assert_called_once_with({"kind": "terminal_run", "id": "run-one"})
        plan = result["account"]["ledger"]["plans"][0]
        expected_owner = sha256(json.dumps(dict(account_id=self.creation["account_id"], engine_id="terminal.test-v1", owner="family:verified-family"),
                                          ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(plan["owner_id"], expected_owner)
        self.assertEqual(plan["research_binding"]["report_id"], "run-one")
        self.assertEqual(result["account"]["plan_links"][0]["owner_continuity"], "VERIFIED_TASK_FAMILY")

    def test_family_owner_continuity_is_engine_and_account_scoped_and_legacy_is_disclosed(self):
        self.create()
        one = self.plan()["account"]["ledger"]["plans"][0]
        two = self.plan("create-plan-0002", identity="version-two")["account"]["ledger"]["plans"][1]
        core = self.plan("create-plan-0003", kind="core_run")["account"]["ledger"]["plans"][2]
        self.assertEqual(one["owner_id"], two["owner_id"])
        self.assertNotEqual(one["owner_id"], core["owner_id"])
        legacy = self.plan("create-plan-0004", identity="legacy-one")
        self.assertEqual(legacy["account"]["plan_links"][-1]["owner_continuity"], "IMMUTABLE_TASK_ONLY_NO_CROSS_VERSION_CONTINUITY")
        self.create(account_id="synthetic-account-b", client_request_id="create-account-0002")
        other = self.plan("create-plan-0005", **self.selected("synthetic-account-b"))
        self.assertNotEqual(one["owner_id"], other["account"]["ledger"]["plans"][0]["owner_id"])

    def test_missing_unknown_or_authority_bearing_resolver_result_cannot_create_a_plan(self):
        self.create()
        before = self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]
        for identity in ("missing", "unknown", "authority"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.plan(identity=identity)
        after = self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]
        self.assertEqual(after, before)

    def test_plan_requires_verified_exact_us_equity_identity_matching_account(self):
        self.create()
        original = self.resolve({"kind": "terminal_run", "id": "run-one"})
        variants = []
        missing = deepcopy(original);missing["binding"].pop("security_id");variants.append(missing)
        missing = deepcopy(original);missing["display"]={};variants.append(missing)
        for name, value in (("security_id", "OTHER:id"), ("symbol", "OTHER"), ("currency", "EUR"), ("asset_class", "CRYPTO")):
            changed = deepcopy(original);changed["display"][name]=value;variants.append(changed)
        before = self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]
        for resolved in variants:
            self.resolver.side_effect = lambda _, value=resolved: deepcopy(value)
            with self.assertRaisesRegex(ValueError, "verified_us_equity_account_security_required"):
                self.plan()
        self.assertEqual(self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"], before)
        self.resolver.side_effect = self.resolve
        result = self.plan()
        plan_id = result["receipt"]["outcome"]["plan_id"]
        with self.assertRaisesRegex(ValueError, "plan_security_identity_required"):
            self.service.mutate("terminal_execution_submit", self.submit_payload(plan_id, security_id="OTHER:id"))

    def test_stale_or_other_account_context_rejects_before_resolving_or_writing(self):
        first = self.create()
        self.create(account_id="synthetic-account-b", client_request_id="create-account-0002")
        with self.assertRaisesRegex(ValueError, "stale_account_context"):
            self.plan(account_id="synthetic-account-b", account_context=first["account_context"])
        self.resolver.assert_not_called()
        before = self.service.read("terminal_execution_account", "synthetic-account-b")["ledger"]["revision"]
        self.assertEqual(before, 0)
        old = self.selected()
        self.service.close()
        self.service = TerminalExecutionService(self.workspace, self.resolver)
        with self.assertRaisesRegex(ValueError, "stale_account_context"):
            self.service.mutate("terminal_execution_stop", dict(client_request_id="stop-request-0001", **old, reason="old selection"))
        self.assertNotEqual(self.selected()["account_context"], old["account_context"])

    def test_multithread_creation_and_reads_share_exactly_one_account_store(self):
        original = OfflineExecutionStore.create
        with patch("exchange_terminal.services.terminal_execution_service.OfflineExecutionStore.create", wraps=original) as create:
            with ThreadPoolExecutor(max_workers=4) as pool:
                created = list(pool.map(lambda _: self.create(), range(4)))
            self.assertEqual(create.call_count, 1)
        self.assertEqual(len({item["account_context"] for item in created}), 1)
        with patch("exchange_terminal.services.terminal_execution_service.OfflineExecutionStore.open", wraps=OfflineExecutionStore.open) as opened:
            with ThreadPoolExecutor(max_workers=4) as pool:
                views = list(pool.map(lambda _: self.service.read("terminal_execution_account", self.creation["account_id"]), range(8)))
            opened.assert_not_called()
        self.assertEqual(len(self.service._stores), 1)
        self.assertTrue(all(view["ledger"]["revision"] == 0 for view in views))

    def test_threaded_strategy_submissions_obey_one_shared_cash_reservation(self):
        self.create()
        one = self.plan()["receipt"]["outcome"]["plan_id"]
        two = self.plan("create-plan-0002", identity="other-strategy")["receipt"]["outcome"]["plan_id"]
        payloads = [self.submit_payload(one, quantity=80), self.submit_payload(two, "submit-order-0002", quantity=80)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(lambda payload: self.service.mutate("terminal_execution_submit", payload), payloads))
        self.assertEqual(sorted(item["receipt"]["outcome"]["status"] for item in result), ["ACCEPTED", "REJECTED"])
        self.assertEqual(Decimal(self.service.read("terminal_execution_account", self.creation["account_id"])["ledger"]["reserved_cash"]), 801)

    def test_unknown_restart_keeps_original_order_and_requires_explicit_complete_snapshot(self):
        self.create()
        plan = self.plan()["receipt"]["outcome"]["plan_id"]
        payload = self.submit_payload(plan, outcome="TIMEOUT_UNCONFIRMED")
        result = self.service.mutate("terminal_execution_submit", payload)
        order_id = result["receipt"]["outcome"]["order_id"]
        self.assertEqual(result["account"]["status"], "OUTCOME_UNCONFIRMED")
        self.service.close()
        self.service = TerminalExecutionService(self.workspace, self.resolver)
        selected = self.selected()
        view = self.service.read("terminal_execution_account", self.creation["account_id"])
        self.assertTrue(view["reconciliation_required"])
        self.assertEqual(view["ledger"]["orders"][0]["state"], "TIMEOUT_UNCONFIRMED")
        self.assertEqual(Decimal(view["ledger"]["reserved_cash"]), 101)
        with self.assertRaises(ValueError):
            self.service.mutate("terminal_execution_reconcile", dict(client_request_id="reconcile-request-0001", **selected, now_ms=self.now))
        snapshot = dict(schema_version=SNAPSHOT_SCHEMA, evidence_kind="SYNTHETIC_TEST", account_id=selected["account_id"],
                        account_revision=view["ledger"]["revision"], observed_at=self.now, orders=[], cash="1000", positions=[])
        result = self.service.mutate("terminal_execution_reconcile", dict(client_request_id="reconcile-request-0002", **selected,
                                                                         now_ms=self.now, complete_snapshot=snapshot))
        self.assertEqual(result["receipt"]["outcome"]["reason"], "order_absence_does_not_prove_rejection")
        self.assertEqual(result["account"]["ledger"]["orders"][0]["order_id"], order_id)
        self.assertEqual(len(result["account"]["ledger"]["orders"]), 1)
        receipt = self.service.read("terminal_execution_receipt", json.dumps(dict(account_id=selected["account_id"], request_id=payload["client_request_id"])))
        self.assertEqual(receipt["status"], "COMMITTED")
        self.assertEqual(receipt["receipt"]["outcome"]["status"], "TIMEOUT_UNCONFIRMED")

    def test_supplied_reconciliation_and_order_observations_pass_through_without_synthesized_fields(self):
        self.create()
        plan = self.plan()["receipt"]["outcome"]["plan_id"]
        result = self.service.mutate("terminal_execution_submit", self.submit_payload(plan, outcome="TIMEOUT_UNCONFIRMED"))
        order_id = result["receipt"]["outcome"]["order_id"]
        selected = self.selected()
        snapshot = dict(schema_version=SNAPSHOT_SCHEMA, evidence_kind="SYNTHETIC_TEST", account_id=selected["account_id"],
            account_revision=result["account"]["ledger"]["revision"], observed_at=self.now,
            orders=[dict(evidence_id="independent-synthetic-query", order_id=order_id, state="ACCEPTED",
                         cumulative_quantity=0, cumulative_notional="0", cumulative_fee="0")], cash="1000", positions=[])
        original = deepcopy(snapshot)
        store = self.service._stores[selected["account_id"]]["store"]
        with patch.object(store, "reconcile", wraps=store.reconcile) as reconcile:
            result = self.service.mutate("terminal_execution_reconcile", dict(client_request_id="reconcile-request-0001", **selected,
                                                                             complete_snapshot=snapshot, now_ms=self.now))
        self.assertEqual(reconcile.call_args.kwargs["complete_snapshot"], original)
        self.assertEqual(snapshot, original)
        self.assertEqual(result["receipt"]["outcome"]["status"], "RECONCILED")
        observation = dict(evidence_id="independent-synthetic-partial", order_id=order_id, state="PARTIAL",
                           cumulative_quantity=4, cumulative_notional="40", cumulative_fee="0.4")
        partial = self.service.mutate("terminal_execution_observe", dict(client_request_id="observe-request-0001", **selected, observation=observation, now_ms=self.now))
        self.assertEqual(partial["account"]["ledger"]["positions"][0]["quantity"], 4)
        cancel = self.service.mutate("terminal_execution_cancel", dict(client_request_id="cancel-request-0001", **selected,
                                                                       order_id=order_id, now_ms=self.now, outcome="ACCEPTED"))
        self.assertEqual(Decimal(cancel["account"]["ledger"]["reserved_cash"]), Decimal("60.6"))
        stopped = self.service.mutate("terminal_execution_stop", dict(client_request_id="stop-request-0001", **selected, reason="explicit synthetic stop"))
        self.assertTrue(stopped["account"]["paused"])
        resumed = self.service.mutate("terminal_execution_resume", dict(client_request_id="resume-request-0001", **selected, reason="operator reviewed current state"))
        self.assertFalse(resumed["account"]["paused"])

    def test_public_views_keep_every_external_permission_false(self):
        created = self.create()
        planned = self.plan()
        def check(value):
            if type(value) is dict:
                for key, item in value.items():
                    if key in {"paper_order_allowed", "live_order_allowed", "order_allowed", "broker_connection_allowed", "model_calls_allowed"}:
                        self.assertIs(item, False)
                    check(item)
            elif type(value) is list:
                for item in value:
                    check(item)
        for value in (created, planned, self.service.read("terminal_execution_accounts"),
                      self.service.read("terminal_execution_receipt", dict(account_id=self.creation["account_id"], request_id="create-plan-0001"))):
            check(value)

    def test_plan_display_link_cannot_invent_owner_continuity(self):
        self.create()
        result = self.plan(identity="legacy-one")
        plan_id = result["receipt"]["outcome"]["plan_id"]
        path = self.workspace / "offline-execution" / self.creation["account_id"] / "plan-links" / (plan_id+".json")
        link = json.loads(path.read_text())
        link["owner_continuity"] = "VERIFIED_TASK_FAMILY"
        path.write_text(json.dumps(link))
        with self.assertRaisesRegex(ValueError, "plan_link_mismatch"):
            self.service.read("terminal_execution_account", self.creation["account_id"])

    def test_read_views_receipts_history_and_comparison_never_advance_ledger(self):
        self.create()
        result = self.plan()
        before = deepcopy(result["account"]["ledger"])
        account_id = self.creation["account_id"]
        self.service.read("terminal_execution_accounts")
        self.service.read("terminal_execution_receipt", dict(account_id=account_id, request_id="create-plan-0001"))
        self.service.read("terminal_execution_history", dict(account_id=account_id, limit=10))
        comparison = self.service.read("terminal_execution_compare", dict(account_id=account_id,
            plan_id=result["receipt"]["outcome"]["plan_id"], reference={"kind": "terminal_run", "id": "run-one"}))
        self.assertEqual(comparison["rules"]["engine_id"]["status"], "MATCH")
        self.assertFalse(comparison["numeric_performance_comparison_allowed"])
        self.assertEqual(self.service.read("terminal_execution_account", account_id)["ledger"], before)

    def test_unmanaged_or_partial_account_is_retained_without_auto_adoption(self):
        folder = self.workspace / "offline-execution" / "unmanaged-account"
        folder.mkdir(parents=True)
        original = b"unrelated historical bytes"
        (folder / "account.sqlite").write_bytes(original)
        result = self.service.read("terminal_execution_accounts")
        self.assertEqual(result["items"], [])
        self.assertEqual(len(result["warnings"]), 1)
        with self.assertRaises(ValueError):
            self.service.read("terminal_execution_account", "unmanaged-account")
        self.assertEqual((folder / "account.sqlite").read_bytes(), original)

    def test_manifest_or_account_history_replacement_invalidates_cached_context(self):
        self.create()
        selected = self.selected()
        self.plan()
        manifest_path = self.workspace / "offline-execution" / selected["account_id"] / "account.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["label"] = "replaced selection"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "stale_account_context"):
            self.service.mutate("terminal_execution_stop", dict(client_request_id="stop-request-0001", **selected, reason="must fail"))

    def test_committed_fact_survives_auxiliary_view_failure(self):
        with patch.object(self.service, "_view", side_effect=RuntimeError("synthetic view error")):
            created = self.create()
        self.assertEqual(created["status"], "ACCOUNT_CREATED")
        self.assertIsNone(created["account"])
        selected = self.selected()
        payload = dict(client_request_id="create-plan-0001", **selected, reference={"kind": "terminal_run", "id": "run-one"}, stage="SIMULATION")
        with patch.object(self.service, "_view", side_effect=RuntimeError("synthetic view error")):
            result = self.service.mutate("terminal_execution_create_plan", payload)
        self.assertEqual(result["receipt"]["outcome"]["status"], "PLAN_SAVED")
        self.assertIsNone(result["account"])
        self.assertEqual(len(self.service.read("terminal_execution_account", selected["account_id"])["ledger"]["plans"]), 1)

    def test_close_releases_own_store_and_prevents_implicit_reopen(self):
        self.create()
        store = self.service._stores[self.creation["account_id"]]["store"]
        self.service.close()
        self.service.close()
        for call in (lambda: self.service.read("terminal_execution_accounts"), self.create):
            with self.assertRaisesRegex(ValueError, "service_closed"):
                call()
        with self.assertRaises(Exception):
            store.snapshot()


if __name__ == "__main__":
    unittest.main()
