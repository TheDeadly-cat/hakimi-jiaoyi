"""New synthetic ledger fixtures and report projections; no engine/provider runs."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from exchange_terminal.services.offline_execution import BINDING_SCHEMA, OfflineExecutionStore
from exchange_terminal.services.terminal_execution_explanation import explain_execution
from exchange_terminal.services.terminal_result_comparison import project_saved_result


def report_fixture(core=False):
    """Explicit fictional verified-reader-shaped input for the pure projector."""
    binding = dict(schema_version=BINDING_SCHEMA, status="COMPLETED", engine_id="research.accepted-equity" if core else "synthetic-native-v1",
        strategy_id="price.dual_ma@1" if core else "dual_ma", strategy_params={"fast": 5, "slow": 20},
        task_id="synthetic-task", task_version=1, input_id="synthetic-input", report_id="b"*64,
        report_hash="a"*64, security_id="TEST:id", risk={"position_pct": 0.2}, costs={"fee_rate": 0.001})
    security = dict(security_id="TEST:id", symbol="TEST", currency="USD")
    if core:
        binding["source_hash"] = "c"*64
        binding["costs"]["slippage_pct"] = 0.002
        spec = dict(snapshot_id=binding["input_id"], strategy={"params": binding["strategy_params"]}, risk=binding["risk"],
            initial_cash=1000, fee_rate=0.001, slippage_pct=0.002, quantity_policy="FRACTIONAL_SHARES_RESEARCH_APPROXIMATION")
        report = dict(schema_version="us-equity-research-report-v1", report_hash=binding["report_hash"], spec=spec,
            dataset={"snapshot_id": binding["input_id"], "security": security, "price_basis": "RAW", "sessions": [{"date": "2026-01-02"}, {"date": "2026-06-30"}]},
            result={"execution_model": "NEXT_BAR_OPEN", "total_return": 0.01, "total_fees": 2.5})
        envelope = dict(verification_status="VERIFIED_RECORD", id="core-opaque-read-id", report=report,
            manifest={"run_id": binding["report_id"], "task_id": binding["task_id"],
                      "task": {"strategy": binding["strategy_id"], "experiment": spec, "management": {"revision": 1}},
                      "runtime": {"source_identity": {"content_sha256": binding["source_hash"]}}},
            snapshot={"snapshot_id": binding["input_id"], "security": security, "timeframe": "1d"})
    else:
        binding["costs"]["slippage_bps"] = 20
        report = dict(schema_version="hakimi-terminal-run-v1", id=binding["report_hash"], run_id=binding["report_id"],
            report_hash=binding["report_hash"], status="COMPLETED", task_id=binding["task_id"], version=1,
            strategy_id=binding["strategy_id"], engine_id=binding["engine_id"],
            configuration={"input_id": binding["input_id"], "strategy_params": binding["strategy_params"],
                "initial_cash": 1000, "risk": binding["risk"], "costs": binding["costs"], "execution_model": "NEXT_BAR_OPEN"},
            input_summary={"id": binding["input_id"], "symbol": "TEST", "bar": "1d", "date_start": "2026-01-02", "date_end": "2026-06-30", "meta": security},
            result={"execution_model": "NEXT_BAR_OPEN", "total_return_pct": 1, "total_fees": 2.5,
                "execution_assumptions": {"signal_time": "BAR_CLOSE", "entry_exit_time": "NEXT_BAR_OPEN"},
                "evaluation_window": {"context_rows": 80, "evaluated_rows": 40, "start": "2026-05-01", "end": "2026-06-30"}})
        envelope = dict(verification_status="VERIFIED_RECORD", id=binding["report_id"], report=report)
    return project_saved_result(envelope), binding


def item(result, key):
    return next(row for group in result["groups"] for row in group["items"] if row["id"] == key)


class ExecutionExplanationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="explanation-new-synthetic-")
        self.addCleanup(temp.cleanup)
        self.store = OfflineExecutionStore.create(Path(temp.name)/"account.sqlite", account_id="synthetic-a", initial_cash="1000",
            securities={"TEST:id": {"symbol": "TEST", "tick_size": "0.01"}},
            rules=dict(max_order_notional="2000", max_total_exposure="3000", max_security_exposure="3000", cash_floor="0", fee_buffer="1", max_account_loss="500", quote_max_age_ms=60000))
        self.addCleanup(self.store.close)
        self.projection, self.binding = report_fixture()
        self.serial = 0
        self.plan_id = self.plan(self.binding)

    def plan(self, binding, owner="family:owner-a"):
        self.serial += 1
        return self.store.create_plan("plan-"+str(self.serial), account_id="synthetic-a", owner_id=owner,
            research_binding=binding)["outcome"]["plan_id"]

    def submit(self, plan_id=None, *, outcome="ACCEPTED", fill=True):
        self.serial += 1
        now = 1000000+self.serial*1000
        result = self.store.submit("order-"+str(self.serial), account_id="synthetic-a", plan_id=plan_id or self.plan_id,
            security_id="TEST:id", side="BUY", quantity=4, limit_price="10", signal_at=now-1000, execution_at=now, now_ms=now,
            quote=dict(security_id="TEST:id", price="10", as_of=now, observed_at=now, source_id="fictional-test", evidence_kind="SYNTHETIC_TEST"), outcome=outcome)
        order_id = result["outcome"]["order_id"]
        if fill:
            self.store.observe("observe-"+str(self.serial), account_id="synthetic-a", now_ms=now+100,
                observation=dict(evidence_id="evidence-"+str(self.serial), order_id=order_id, state="PARTIAL",
                                 cumulative_quantity=2, cumulative_notional="20", cumulative_fee="0.2"))
        return order_id

    def arguments(self):
        snap = self.store.snapshot()
        plan = next(p for p in snap["plans"] if p["plan_id"] == self.plan_id)
        return deepcopy(self.projection), deepcopy(plan), snap, deepcopy(self.binding)

    def test_six_groups_preserve_scope_missing_fields_and_no_attribution(self):
        self.submit()
        args = self.arguments()
        before = deepcopy(args)
        value = explain_execution(*args)
        self.assertEqual(args, before)
        self.assertEqual([g["id"] for g in value["groups"]], ["DATA", "RULES", "TIMING", "MATCHING", "COSTS", "UNKNOWN"])
        self.assertEqual(value["status"], "BOUND_REPORT_CONTEXT_ONLY")
        self.assertEqual(item(value, "strategy_params")["status"], "MATCH")
        self.assertEqual(item(value, "fill_model")["status"], "DIFFERENT")
        self.assertEqual(item(value, "quantity_policy")["status"], "UNKNOWN")
        self.assertEqual(item(value, "fill_time")["simulation"]["value"], None)
        self.assertEqual(item(value, "source_hash")["status"], "UNKNOWN")
        self.assertNotIn("source_hash", [i["id"] for i in value["groups"][0]["items"]])
        self.assertFalse(value["attribution"]["numeric_performance_comparison_allowed"])
        self.assertIsNone(value["attribution"]["contributions"])
        self.assertEqual(value["new_economic_runs"], 0)
        self.assertEqual(value["external_calls"], 0)
        json.dumps(value, allow_nan=False)

    def test_fees_count_exact_plan_and_order_once_not_shared_account_or_observation_sum(self):
        first = self.submit()
        self.store.observe("observe-more", account_id="synthetic-a", now_ms=1100000,
            observation=dict(evidence_id="evidence-more", order_id=first, state="FILLED", cumulative_quantity=4, cumulative_notional="40", cumulative_fee="0.4"))
        other = deepcopy(self.binding)
        other.update(task_id="synthetic-other-task", report_id="d"*64, report_hash="e"*64)
        self.submit(self.plan(other))
        args = self.arguments()
        args[2]["orders"].append(deepcopy(args[2]["orders"][0]))
        value = explain_execution(*args)
        self.assertEqual(value["scope"]["order_count"], 1)
        self.assertEqual(item(value, "recorded_fees")["simulation"]["value"], "0.4")
        self.assertEqual(len(item(value, "order_observations")["simulation"]["value"]), 1)
        self.assertEqual(value["account_scope"]["owner_positions"][0]["quantity"], 6)
        self.assertEqual(value["account_scope"]["owner_positions_scope"], "OWNER_ACROSS_PLANS_NOT_SINGLE_PLAN")
        self.assertEqual(value["account_scope"]["cash"], "939.4")

    def test_conflicting_duplicate_order_is_rejected(self):
        self.submit()
        args = self.arguments()
        changed = deepcopy(args[2]["orders"][0]); changed["fee"] = "10"
        args[2]["orders"].append(changed)
        with self.assertRaisesRegex(ValueError, "conflicting_order_rows"):
            explain_execution(*args)

    def test_missing_fee_stays_null_not_zero(self):
        self.submit()
        args = self.arguments(); del args[2]["orders"][0]["fee"]
        value = explain_execution(*args)
        self.assertIsNone(item(value, "recorded_fees")["simulation"]["value"])
        self.assertEqual(item(value, "recorded_fees")["status"], "UNKNOWN")

    def test_other_report_is_context_only_and_does_not_inherit_order_observations(self):
        self.submit()
        p, plan, snap, binding = self.arguments()
        binding.update(report_id="d"*64, report_hash="e"*64)
        p["identities"].update(run_id=binding["report_id"], report_hash=binding["report_hash"])
        value = explain_execution(p, plan, snap, binding)
        self.assertEqual(value["status"], "ONLY_CONTEXT_NO_ATTRIBUTION")
        self.assertFalse(value["scope"]["orders_associated_with_reference"])
        self.assertIsNone(value["scope"]["order_count"])
        for key in ("order_observations", "order_times", "recorded_fees"):
            self.assertIsNone(item(value, key)["simulation"]["value"])

    def test_projection_and_plan_identity_conflicts_fail_closed(self):
        for mutate, error in ((lambda a: a[0]["identities"].update(report_hash="f"*64), "projection_binding"),
                              (lambda a: a[1].update(owner_id="changed"), "snapshot_plan"),
                              (lambda a: a[0].update(binding_conflicts=["input"]), "verified_projection"),
                              (lambda a: a[2]["permissions"].update(live_order_allowed=True), "synthetic_snapshot"),
                              (lambda a: a[0]["conditions"].update(record_integrity=None), "verified_projection")):
            with self.subTest(error=error):
                args = self.arguments(); mutate(args)
                with self.assertRaisesRegex(ValueError, error):
                    explain_execution(*args)

    def test_same_report_cannot_claim_different_parameters(self):
        args = self.arguments()
        args[0]["strategy_params"]["fast"] = 6
        args[3]["strategy_params"]["fast"] = 6
        with self.assertRaisesRegex(ValueError, "same_report_binding_conflict"):
            explain_execution(*args)

    def test_core_fractional_policy_and_cost_units_remain_recorded_units(self):
        self.projection, self.binding = report_fixture(core=True)
        self.plan_id = self.plan(self.binding)
        value = explain_execution(*self.arguments())
        self.assertEqual(item(value, "quantity_policy")["status"], "DIFFERENT")
        self.assertEqual(item(value, "slippage")["research"], {
            "value": 0.002, "unit": "ratio", "evidence_ref": [{"source": "SAVED_PROJECTION", "pointer": pointer, "report_hash": "a"*64, "record_id": "core-opaque-read-id"} for pointer in ("/costs/slippage_rate", "/costs/slippage_unit")]})
        native, binding = report_fixture()
        plan_id = self.plan(binding)
        snap = self.store.snapshot()
        native_value = explain_execution(native, next(p for p in snap["plans"] if p["plan_id"] == plan_id), snap, binding)
        self.assertEqual(item(native_value, "slippage")["research"]["unit"], "basis_points")
        self.assertEqual(item(native_value, "slippage")["research"]["value"], 20)

    def test_timeout_gate_remains_unknown_and_read_does_not_mutate_ledger(self):
        self.submit(outcome="TIMEOUT_UNCONFIRMED", fill=False)
        args = self.arguments(); revision = args[2]["revision"]
        value = explain_execution(*args)
        self.assertTrue(item(value, "ledger_gate")["simulation"]["value"]["reconciliation_required"])
        self.assertEqual(item(value, "order_observations")["simulation"]["value"][0]["state"], "TIMEOUT_UNCONFIRMED")
        self.assertEqual(self.store.snapshot()["revision"], revision)

    def test_evidence_pointers_address_exact_supplied_objects(self):
        self.submit()
        args = self.arguments(); value = explain_execution(*args)
        sources = dict(SAVED_PROJECTION=args[0], VALIDATED_SNAPSHOT=args[2], REFERENCE_BINDING=args[3])
        for group in value["groups"]:
            for row in group["items"]:
                for side in ("research", "simulation"):
                    for ref in row[side]["evidence_ref"]:
                        if ref["source"] not in sources:
                            continue
                        current = sources[ref["source"]]
                        for part in ref["pointer"].lstrip("/").split("/"):
                            current = current[int(part)] if isinstance(current, list) else current.get(part)
                            if current is None:
                                break  # Exact pointer to an absent field is useful absence evidence.
                        if ref["source"] == "VALIDATED_SNAPSHOT":
                            self.assertEqual(ref["ledger_revision"], args[2]["revision"])


if __name__ == "__main__":
    unittest.main()
