"""Strict projection contracts; fixture writers use a mock runner, never markets."""
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.services.terminal_result_comparison import compare_saved_results, project_saved_result
from tests import test_terminal_research as native_fixtures


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def canonical(index, *, net=.01, benchmark=False):
    """Same fields as the current saved canonical manifest/report/snapshot.

    The verifier marker is an explicit trusted-reader stub for this pure
    projection test. This fixture is not a generated or accepted economic run.
    """
    strategy = "price.buy_and_hold@1" if benchmark else "price.dual_ma@1"
    policy = "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET" if benchmark else "STANDARD_STRATEGY_RISK"
    params = {"target_position_pct": .25} if benchmark else {
        "fast_window": 5, "slow_window": 10, "position_pct": .25, "stop_loss_pct": .03, "take_profit_pct": .06}
    spec = {"schema_version": "us-equity-experiment-spec-v1", "snapshot_id": "f" * 64,
        "score_start_session": "2026-10-15", "score_end_session": "2026-10-26", "initial_cash": 10000,
        "fee_rate": .0008, "slippage_pct": .0005, "end_policy": "MARK_TO_MARKET",
        "quantity_policy": "FRACTIONAL_SHARES_RESEARCH_APPROXIMATION", "execution_policy": policy,
        "strategy": {"name": "buy_and_hold" if benchmark else "dual_ma", "params": params},
        "risk": {"max_position_pct": .25, "min_cash_pct": 0, "max_single_loss_pct": .03, "max_daily_loss_pct": 1, "max_leverage": 1}}
    report = {"schema_version": "us-equity-research-report-v1", "report_hash": f"{index:064x}", "spec": spec,
        "dataset": {"snapshot_id": "f" * 64, "security": {"security_id": "QA:TEST", "symbol": "TEST", "currency": "USD"},
                    "sessions": [{"date": "2026-09-29"}, {"date": "2026-10-26"}], "price_basis": "RAW_UNADJUSTED",
                    "evidence_kind": "SYNTHETIC_TEST", "research_admission": {"scope": "ACTION_FREE_FIXED_WINDOW_ONLY"}},
        "scoring_protocol": {"score_start": "2026-10-15T13:30:00Z", "score_end": "2026-10-26T20:00:00Z",
            "scored_sessions": 8, "available_context_sessions": 12, "session_clock_hash": "d" * 64,
            "company_actions": "DECLARED_ACTION_FREE_WINDOW_ONLY"},
        "result": {"total_return": net, "total_fees": 0, "execution_model": "signal-close-next-open-ohlc-v6",
            "risk_semantics": {"protective_exits_enabled": not benchmark, "execution_policy": policy,
                "benchmark_policy": "EXPLICIT_NO_STOPS_NO_TARGETS_SINGLE_INITIAL_ATTEMPT" if benchmark else "NOT_APPLICABLE"},
            "statistical_status": {"status": "INSUFFICIENT_EVIDENCE"}}}
    return {"id": "opaque-" + str(index), "status": "COMPLETED", "verification_status": "VERIFIED_RECORD", "report": report,
        "manifest": {"run_id": "run-" + str(index), "task_id": "task-" + str(index),
            "task": {"strategy": strategy, "experiment": deepcopy(spec), "management": {"revision": "r0001-fixture"}},
            "runtime": {"source_identity": {"content_sha256": "a" * 64}, "environment_verified": {"status": "VERIFIED", "lock_sha256": "b" * 64}}},
        "snapshot": {"snapshot_id": "f" * 64, "timeframe": "1d", "timezone": "America/New_York", "as_of": "2026-10-27T00:00:00Z"}}


class StrictResultComparisonTests(unittest.TestCase):
    def test_identical_eligible_conditions_only_yield_descriptive_net_return_delta(self):
        first, second = canonical(1, net=.02), canonical(2, net=-.01)
        second["report"]["spec"]["strategy"]["params"]["fast_window"] = 7
        second["manifest"]["task"]["experiment"] = deepcopy(second["report"]["spec"])
        before = [digest(row) for row in (first, second)]
        view = compare_saved_results([first, second])
        self.assertEqual(view["status"], "COMPARABLE_CONDITIONS")
        self.assertEqual(view["differences_from_first"], [{"row": 2, "net_return_percentage_points": -3.0}])
        self.assertIsNone(view["ranking"])
        self.assertEqual(view["new_economic_runs"], 0)
        self.assertEqual([digest(row) for row in (first, second)], before)
        self.assertEqual(view["rows"][0]["statistical_status"]["status"], "INSUFFICIENT_EVIDENCE")

    def test_actual_native_25_vs_10_records_are_not_promoted_and_saved_hashes_do_not_change(self):
        fixture = native_fixtures.TerminalResearchTests("runTest")
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        first_task = fixture.task(); first = fixture.run_task(first_task)
        second_task = fixture.task(parent_task_id=first_task["id"],
            risk={"position_pct": 10, "take_profit_pct": 0, "stop_loss_pct": 8, "leverage": 1})
        second = fixture.run_task(second_task)
        before = {str(path.relative_to(fixture.core.workspace)): sha256(path.read_bytes()).hexdigest()
                  for path in fixture.core.workspace.rglob("*") if path.is_file()}
        calls = fixture.runner.call_count
        view = compare_saved_results([{"verification_status": "VERIFIED_RECORD", "report": row} for row in (first, second)])
        self.assertEqual(view["status"], "UNKNOWN_CONDITIONS")
        self.assertIn("risk.position_pct", view["mismatches"][0]["fields"])
        self.assertIn("quantity_policy", view["missing"][0]["fields"])
        self.assertIn("currency", view["missing"][0]["fields"])
        self.assertEqual(view["differences_from_first"], [])
        self.assertEqual(fixture.runner.call_count, calls)
        self.assertEqual({str(path.relative_to(fixture.core.workspace)): sha256(path.read_bytes()).hexdigest()
                          for path in fixture.core.workspace.rglob("*") if path.is_file()}, before)
        self.assertEqual(view["rows"][0]["identities"]["report_hash"], first["id"])

    def test_canonical_allocation_execution_and_cost_changes_prevent_differences(self):
        changes = [("allocation", lambda row: row["report"]["spec"]["strategy"]["params"].update(position_pct=.10)),
                   ("execution_model", lambda row: row["report"]["result"].update(execution_model="other-recorded-engine-v1")),
                   ("fee_rate", lambda row: row["report"]["spec"].update(fee_rate=.001)),
                   ("slippage_rate", lambda row: row["report"]["spec"].update(slippage_pct=.001)),
                   ("as_of", lambda row: row["snapshot"].update(as_of="2026-10-28T00:00:00Z"))]
        for field, change in changes:
            with self.subTest(field=field):
                a, b = canonical(1), canonical(2)
                change(b); b["manifest"]["task"]["experiment"] = deepcopy(b["report"]["spec"])
                result = compare_saved_results([a, b])
                self.assertEqual(result["status"], "SIDE_BY_SIDE_ONLY")
                self.assertIn(field, result["mismatches"][0]["fields"])
                self.assertEqual(result["differences_from_first"], [])

    def test_missing_facts_and_unverified_or_unknown_envelopes_never_get_defaults(self):
        for mutation, field in [(lambda row: row.pop("snapshot"), "as_of"),
                (lambda row: row["snapshot"].update(as_of="UNKNOWN"), "as_of"),
                (lambda row: row["report"]["dataset"]["security"].pop("currency"), "currency"),
                (lambda row: row["report"]["spec"]["risk"].pop("min_cash_pct"), "risk.min_cash_pct"),
                (lambda row: row.pop("verification_status"), "record_integrity"),
                (lambda row: row.update(status="UNKNOWN"), "envelope_completed_result")]:
            with self.subTest(field=field):
                a, b = canonical(1), canonical(2); mutation(b)
                b["manifest"]["task"]["experiment"] = deepcopy(b["report"]["spec"])
                before = digest(b)
                result = compare_saved_results([a, b])
                self.assertEqual(result["status"], "UNKNOWN_CONDITIONS")
                self.assertIn(field, result["missing"][0]["fields"])
                self.assertEqual(result["differences_from_first"], [])
                self.assertEqual(digest(b), before)

    def test_benchmark_is_explicit_separate_reference_with_recorded_no_stop_policy(self):
        a, benchmark = canonical(1), canonical(2, benchmark=True)
        result = compare_saved_results([a, benchmark])
        self.assertEqual(result["status"], "SIDE_BY_SIDE_ONLY")
        self.assertEqual(result["benchmark_rows"], [2])
        self.assertEqual(result["rows"][1]["role"], "BENCHMARK_REFERENCE")
        self.assertFalse(result["rows"][1]["benchmark_policy"]["protective_exits_enabled"])
        self.assertIn("SINGLE_INITIAL_ATTEMPT", result["rows"][1]["benchmark_policy"]["recorded_benchmark_policy"])
        self.assertEqual(result["differences_from_first"], [])
        unknown = canonical(3); unknown["report"]["spec"]["strategy"]["name"] = "buy_and_hold"
        self.assertEqual(project_saved_result(unknown)["role"], "STRATEGY_RESULT")

    def test_cost_display_does_not_invent_slippage_amount_or_model_and_zero_fee_is_known(self):
        row = canonical(1); row["report"]["spec"]["fee_rate"] = 0
        projected = project_saved_result(row)
        self.assertEqual(projected["costs"]["fee_rate"], 0)
        self.assertEqual(projected["costs"]["total_fees"], 0)
        self.assertEqual(projected["costs"]["slippage_rate"], .0005)
        self.assertEqual(projected["costs"]["slippage_unit"], "ratio")
        self.assertIsNone(projected["costs"]["slippage_amount_recorded"])
        self.assertIsNone(projected["costs"]["slippage_model_recorded"])
        self.assertEqual(projected["costs"]["execution_model"], "signal-close-next-open-ohlc-v6")

    def test_conflicting_input_binding_and_cross_engine_records_never_get_excess_return(self):
        a, b = canonical(1), canonical(2)
        b["snapshot"]["snapshot_id"] = "e" * 64
        result = compare_saved_results([a, b])
        self.assertEqual(result["status"], "UNKNOWN_CONDITIONS")
        self.assertEqual(result["binding_conflicts"], [{"row": 2, "fields": ["canonical_input_binding"]}])
        native = {"verification_status": "VERIFIED_RECORD", "report": {
            "schema_version": "hakimi-terminal-run-v1", "status": "COMPLETED", "id": "a-native-report",
            "task_id": "a-native-task", "strategy_id": "dual_ma", "engine_id": "terminal.causal-long-only-signals-v7",
            "configuration": {}, "result": {"total_return_pct": 10}}}
        mixed = compare_saved_results([native, canonical(2, benchmark=True)])
        self.assertIn("engine_family", mixed["mismatches"][0]["fields"])
        self.assertEqual(mixed["differences_from_first"], [])

    def test_invalid_metrics_and_partial_identities_are_unknown_not_zero_or_comparable(self):
        a, b = canonical(1), canonical(2)
        b["report"]["result"]["total_return"] = float("nan")
        result = compare_saved_results([a, b])
        self.assertEqual(result["status"], "UNKNOWN_CONDITIONS")
        self.assertIn("net_return", result["missing"][0]["fields"])
        partial = compare_saved_results([{"report": {}}, {"report": {"schema_version": "future"}}])
        self.assertEqual(partial["status"], "UNKNOWN_CONDITIONS")
        with self.assertRaisesRegex(ValueError, "distinct_saved"):
            compare_saved_results([a, deepcopy(a)])

    def test_current_event_and_content_report_contracts_retain_their_secondary_input_identity(self):
        for schema in ("us-equity-research-report-v2", "us-equity-content-task-report-v1"):
            with self.subTest(schema=schema):
                rows = [canonical(1), canonical(2)]
                for row in rows:
                    row["report"]["schema_version"] = schema
                    row["report"]["spec"].update(event_context_hash="c" * 64, event_rule="recorded-existing-rule")
                    row["report"]["event_context"] = {"context_hash": "c" * 64}
                    row["manifest"]["task"]["experiment"] = deepcopy(row["report"]["spec"])
                self.assertEqual(compare_saved_results(rows)["status"], "COMPARABLE_CONDITIONS")
                rows[1]["report"]["spec"]["event_context_hash"] = "e" * 64
                rows[1]["report"]["event_context"]["context_hash"] = "e" * 64
                rows[1]["manifest"]["task"]["experiment"] = deepcopy(rows[1]["report"]["spec"])
                compared = compare_saved_results(rows)
                self.assertEqual(compared["status"], "SIDE_BY_SIDE_ONLY")
                self.assertIn("event_input_identity", compared["mismatches"][0]["fields"])
                self.assertEqual(compared["differences_from_first"], [])


if __name__ == "__main__":
    unittest.main()
