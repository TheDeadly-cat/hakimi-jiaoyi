"""Repository-only sidecar behavior; the installed engine remains authoritative."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.dataset_registry import save_snapshot
from hakimi_research.documents import digest, read_document
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec
from hakimi_research.reporting import save_json_report


ROOT = Path(__file__).resolve().parents[2]


def load_tool(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


study = load_tool("multiwindow_tool", "tools/run_multiwindow_study.py")
profiling = load_tool("pipeline_profile_tool", "tools/profile_research_pipeline.py")
fixtures = load_tool("multiwindow_fixtures", "tests/test_experiment_runner.py")


class MultiwindowResearchTests(unittest.TestCase):
    def plan(self):
        return read_document(ROOT / "docs/studies/multiwindow-plan-20260905.json")

    def test_exact_predeclared_matrix_and_seen_history(self):
        plan = study.validate_plan(self.plan())
        self.assertEqual(digest(plan), "925206d29125388574c641f14cbec16e9842b1c4f6abaaee6a3ce12cabb2dfab")
        self.assertEqual(len(plan["windows"]) * len(plan["methods"]) * len(plan["cost_factors"]), 240)
        changed = copy.deepcopy(plan)
        changed["windows"][-1]["split"] = "VALIDATION_HISTORY_NOT_BLIND"
        with self.assertRaisesRegex(ValueError, "previously_viewed"):
            study.validate_plan(changed)
        changed = copy.deepcopy(plan)
        changed["windows"][1]["score_start"] = plan["windows"][0]["score_start"]
        with self.assertRaisesRegex(ValueError, "nonoverlapping"):
            study.validate_plan(changed)

    def test_exposure_uses_real_interval_duration_and_excludes_initial_zero(self):
        points = [{"time": "2024-01-01T00:00:00Z", "equity": 100, "position_value": 0, "position_qty": 0},
                  {"time": "2024-01-01T01:00:00Z", "equity": 100, "position_value": 25, "position_qty": 1},
                  {"time": "2024-01-01T04:00:00Z", "equity": 100, "position_value": 75, "position_qty": 3}]
        exposure = study.duration_weighted_exposure(points)
        self.assertEqual(exposure["duration_weighted_close_exposure"], 0.625)
        self.assertEqual(exposure["duration_weighted_invested_close_fraction"], 1)
        self.assertEqual(exposure["scored_seconds"], 14400)
        self.assertIn("UNOBSERVABLE", exposure["intrabar_continuous_exposure"])
        points[-1]["time"] = points[-2]["time"]
        with self.assertRaisesRegex(ValueError, "positive_duration"):
            study.duration_weighted_exposure(points)

    def test_equal_requested_allocation_uses_existing_single_entry_policy(self):
        snapshot = fixtures.snapshot_fixture()
        plan = self.plan()
        window = {"window_id": "synthetic", "score_start": "2024-01-04T00:00:00Z", "score_end": "2024-01-08T12:00:00Z"}
        outcomes = {}
        for method in plan["methods"][1:3]:
            spec = study.cell_spec(plan, window, method, 1, snapshot).document
            self.assertEqual(spec["execution_policy"], "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET")
            spec["purpose"] = "SYNTHETIC_REGRESSION"
            report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec)).document
            row = study.summarize_result(report)
            self.assertEqual(row["fill_count"], 1)
            self.assertEqual(row["round_trip_count"], 0)
            self.assertGreater(row["fee_plus_slippage_cost"], row["total_fees"])
            outcomes[method["label"]] = row
        small, full = outcomes["buy_hold_25pct"], outcomes["buy_hold_full"]
        self.assertEqual(small["requested_initial_allocation_fraction"], 0.25)
        # The 25% request has spare cash for costs; full allocation is clipped
        # to reserve its entry fee. Equal requests do not imply equal outcomes.
        self.assertAlmostEqual(small["first_fill_notional_over_initial_cash"], 0.25 * (1 + plan["slippage_pct"]), places=10)
        self.assertAlmostEqual(full["first_fill_notional_over_initial_cash"], 1 / (1 + plan["fee_rate"]), places=10)
        self.assertLess(small["duration_weighted_close_exposure"], full["duration_weighted_close_exposure"])

    def test_profit_concentration_does_not_net_away_losses_or_drop_failures(self):
        plan = self.plan()
        rows = []
        for window, pnl in (("a", 100), ("b", 300), ("c", -900)):
            rows.append({"window_id": window, "method": "dual_ma", "cost_factor": 1, "split": "DEVELOPMENT_HISTORY",
                         "status": "COMPLETED", "net_pnl": pnl, "total_return": pnl / 10000, "max_drawdown": 0.12,
                         "total_fees": 2, "fee_plus_slippage_cost": 3, "fill_count": 2, "return_minus_buy_hold_25pct": None})
        rows.append({"window_id": "d", "method": "dual_ma", "cost_factor": 1, "split": "DEVELOPMENT_HISTORY", "status": "UNAVAILABLE_DATA"})
        result = next(g for g in study.aggregate_rows(rows, plan) if g["split"] == "ALL_HISTORY")
        self.assertEqual(result["sum_independently_reset_window_pnl"], -500)
        self.assertEqual(result["top_one_positive_window_profit_share"], 0.75)
        self.assertEqual(result["losing_windows"], ["c"])
        self.assertEqual(result["unavailable_or_failed_windows"], ["d"])

    def test_missing_data_preserves_all_240_cells_without_runner_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(study.ExperimentRunner, "run", side_effect=AssertionError("no data must not run")):
                result = study.run(ROOT / "docs/studies/multiwindow-plan-20260905.json", [], Path(directory))
            summary = read_document(result["summary"])
            self.assertEqual(result["planned"], 240)
            self.assertEqual(result["completed"], 0)
            self.assertEqual(len(summary["rows"]), 240)
            self.assertTrue(all(r["status"] == "UNAVAILABLE_DATA" for r in summary["rows"]))
            replay = study.replay(Path(result["run"]), Path(directory) / "replay")
            self.assertEqual(replay["verified"], 0)
            self.assertEqual(replay["planned"], 240)
            manifest = read_document(result["run"])
            manifest["attempts"].pop()
            incomplete = save_json_report(manifest, directory, "bad_run")
            with self.assertRaisesRegex(ValueError, "complete_unique"):
                study.replay(Path(incomplete), Path(directory) / "bad_replay")

    def test_pipeline_profile_exact_replay_and_original_bytes_preserved(self):
        snapshot = fixtures.snapshot_fixture()
        spec = fixtures.spec_fixture(snapshot)
        spec["strategy"] = {"name": "cash", "params": {}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_path = save_snapshot(snapshot, root / "inputs")
            spec_path = Path(save_json_report(spec, root / "inputs", "spec"))
            before = snapshot_path.read_bytes(), spec_path.read_bytes()
            outcome = profiling.profile(snapshot_path, spec_path, root / "profile", hotspots=True)
            receipt = read_document(outcome["profile"])
            self.assertTrue(receipt["decisions_and_results_exact"])
            self.assertFalse(receipt["optimization_applied"])
            self.assertEqual(before, (snapshot_path.read_bytes(), spec_path.read_bytes()))
            self.assertEqual(len(receipt["timings"]), 9)
            self.assertTrue(all(value >= 0 for value in receipt["timings"].values()))
            self.assertTrue(receipt["execution_hotspots"])
            self.assertNotIn(str(root), Path(outcome["profile"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
