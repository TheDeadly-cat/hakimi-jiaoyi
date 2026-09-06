"""Source-contract tests for the read-only Markdown projection, without engines."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("tested_research_view", ROOT / "tools/build_research_view.py")
view = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(view)


class ResearchViewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / "docs/research-evidence/continuous"
        self.folder.mkdir(parents=True)
        self.summary_path = self.folder / "summary.json"
        self.forward_path = self.root / "docs/research-evidence/forward.json"
        self.output = self.root / "docs/research-view.md"
        self.index = self.root / "docs/research-evidence/inputs.json"
        self.permissions = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
        self.plan = {"mode": "CONTINUOUS_HISTORY", "score_start": view.SCORE_START, "score_end": view.SCORE_END,
                     "input_start": view.INPUT_START, "input_end_exclusive": view.SCORE_END,
                     "initial_cash": 10000, "initialization_count": 1, "fee_rate": .0008, "slippage_pct": .0005,
                     "cost_factors": [1, 2, 3], "planned_trajectories": 15,
                     **self.permissions, "methods": [{"label": method, "name": method, "params": {}} for method in
                           ("cash", "buy_hold_full", "buy_hold_25pct", "dual_ma", "rsi")]}
        self.metrics = {key: 0 if kind == "count" else 0.0 for key, _, kind in view.METRICS}
        rows = []
        for method in self.plan["methods"]:
            for cost in (1, 2, 3):
                report_hash = view.digest({"method": method["label"], "cost": cost})
                trace = {"schema_version": "continuous-history-trace-projection-v1", "mode": "CONTINUOUS_HISTORY",
                         "plan_hash": view.digest(self.plan), "method": method["label"], "cost_factor": cost,
                         "report_hash": report_hash, "initialization_count": 1, "forced_end_liquidation": False,
                         "spec": self.spec(method, cost), "dataset": self.dataset(),
                         "source_identity": {"status": "BUILD_VERIFIED", "content_sha256": view.SOURCES["0.2.1"]},
                         "execution_permission": self.permissions, "metrics": deepcopy(self.metrics),
                         "monthly": self.periods(1), "quarterly": self.periods(3), "reset_comparisons": self.reset_periods(),
                         "fills": [], "round_trips": []}
                path = self.folder / f"{method['label']}-{cost}.json"
                self.write(path, trace)
                rows.append({"method": method["label"], "cost_factor": cost, "report_hash": report_hash,
                             "projection_file": path.name, "projection_sha256": view.sha(path), "metrics": deepcopy(self.metrics)})
        self.summary = {"schema_version": "continuous-history-summary-v1", "status": "COMPLETED", **self.permissions,
                        "plan": self.plan, "plan_hash": view.digest(self.plan), "trajectories": rows, "completed_trajectories": 15,
                        "runtime_source_sha256": view.SOURCES["0.2.1"], "snapshot_id": "a" * 64, "data_hash": "b" * 64}
        self.write(self.summary_path, self.summary)
        forward_source = ROOT / "docs/research-evidence/forward-reliability-20260906/coverage_3bda7c8c93b9b42d627c77fa09c44e05081ec15d317699765c8c486888f1891d.json"
        self.forward = view.read(forward_source)
        self.write(self.forward_path, self.forward)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def dataset(self):
        return {"snapshot_id": "a" * 64, "data_hash": "b" * 64, "start": view.INPUT_START,
                "end_exclusive": view.SCORE_END, "quote_unit": "USDT", "volume_unit": "base_currency"}

    def spec(self, method, factor):
        return {"score_start": view.SCORE_START, "score_end": view.SCORE_END, "initial_cash": 10000,
                "fee_rate": .0008 * factor, "slippage_pct": .0005 * factor, "end_policy": "MARK_TO_MARKET",
                "purpose": "DESCRIPTIVE_FIXED_PARAMETERS", "snapshot_id": "a" * 64,
                "strategy": {"name": method["name"], "params": method["params"]}}

    def period(self, start, end, label):
        return {"slice_id": label, "score_start": start, "score_end": end,
                "opening_equity": 10000, "closing_equity": 10000,
                "total_return": 0.0, "fill_count": 0, "reset_total_return": 0.0,
                "return_difference_vs_reset": 0.0, "reset_opening_cash": 10000,
                "reset_opening_position_qty": 0, "reset_fill_count": 0}

    def periods(self, months):
        cursor, end = datetime.fromisoformat(view.SCORE_START), datetime.fromisoformat(view.SCORE_END)
        rows = []
        while cursor < end:
            month = ((cursor.month - 1) // months + 1) * months
            year, month = cursor.year + month // 12, month % 12 + 1
            boundary = min(datetime(year, month, 1, tzinfo=timezone.utc), end)
            start_text, end_text = [value.isoformat().replace("+00:00", "Z") for value in (cursor, boundary)]
            rows.append(self.period(start_text, end_text, start_text[:7]))
            cursor = boundary
        return rows

    def reset_periods(self):
        rows = self.periods(3)
        last = rows.pop()
        rows += [self.period(last["score_start"], "2026-08-01T00:00:00Z", "2026-07"),
                 self.period("2026-08-01T00:00:00Z", last["score_end"], "2026-08")]
        return rows

    def edit_trace(self, key, value, *, method="cash", cost=1):
        row = next(row for row in self.summary["trajectories"] if row["method"] == method and row["cost_factor"] == cost)
        path = self.folder / row["projection_file"]
        trace = view.read(path)
        trace[key] = value
        self.write(path, trace)
        row["projection_sha256"] = view.sha(path)
        self.write(self.summary_path, self.summary)

    def diagnostics(self):
        folder = self.root / "docs/research-evidence/diagnostics"
        plan = deepcopy(self.plan)
        plan["methods"] = [{"label": name, "name": name, "params": {}} for name in ("D0", "D1", "R0", "R1")]
        plan["cost_factors"] = [0, 1, 2, 3]
        plan["budget"] = {"primary_trajectories": 16}
        rows = []
        for method in plan["methods"]:
            for factor in (0, 1, 2, 3):
                identity = view.digest({"diagnostic": method["label"], "cost": factor})
                refs = {}
                if factor:
                    for label in ("cash", "buy_hold_25pct"):
                        original = next(row for row in self.summary["trajectories"] if row["method"] == label and row["cost_factor"] == factor)
                        refs[label] = {"report_hash": original["report_hash"], "total_return": 0.0,
                                       "cost_factor": factor, "score_start": view.SCORE_START, "score_end": view.SCORE_END,
                                       "source_content_sha256": view.SOURCES["0.2.1"]}
                row = {"method": method["label"], "cost_factor": factor, "status": "COMPLETED", **deepcopy(self.metrics),
                       "source_content_sha256": view.SOURCES["0.2.2"], "report_hash": identity, "report_file_sha256": identity,
                       "monthly": self.periods(1), "periods": self.reset_periods(), "reference_reports": refs,
                       "return_minus_cash": 0.0, "return_minus_buy_hold_25pct": 0.0 if factor else None}
                trace = {"schema_version": "strategy-diagnostics-trace-projection-v1", "mode": "CONTINUOUS_HISTORY",
                         "plan_hash": view.digest(plan), "spec": self.spec(method, factor), "dataset": self.dataset(),
                         "report_hash": identity, "report_file_sha256": identity,
                         "source_identity": {"status": "BUILD_VERIFIED", "content_sha256": view.SOURCES["0.2.2"]},
                         "execution_permission": self.permissions, "fills": [], "round_trips": [],
                         "metrics": {key: value for key, value in row.items() if key not in {"periods", "monthly"}},
                         "monthly": row["monthly"], "periods": row["periods"]}
                path = folder / "traces" / f"{method['label']}-{factor}.json"
                self.write(path, trace)
                row.update(projection_file=path.relative_to(folder).as_posix(), projection_file_sha256=view.sha(path))
                rows.append(row)
        for row in rows:
            row["paired_change"] = None
            if row["method"] in {"D1", "R1"}:
                baseline_name = {"D1": "D0", "R1": "R0"}[row["method"]]
                baseline = next(item for item in rows if item["method"] == baseline_name and item["cost_factor"] == row["cost_factor"])
                row["paired_change"] = {"baseline": baseline_name, "baseline_report_hash": baseline["report_hash"], **deepcopy(self.metrics)}
        receipts = []
        for row in rows:
            public = {"schema_version": "research-replay-public-projection-v1", "original_report_hash": row["report_hash"],
                      "replay_verified": True, "original_receipt_hash": view.digest({"original": row["report_hash"]}),
                      "replay_provenance": {"source_content_sha256": view.SOURCES["0.2.2"]}}
            public["projection_hash"] = view.digest(public)
            receipts.append({"method": row["method"], "cost_factor": row["cost_factor"], "replay": public,
                             "ledger": {"status": "PASS"}, "report_file_sha256": row["report_file_sha256"]})
        replay = {"schema_version": "strategy-diagnostics-replay-public-v1", "verified": 16, "planned": 16,
                  "plan_hash": view.digest(plan), "source_content_sha256": view.SOURCES["0.2.2"],
                  "privacy": "MACHINE_RECEIPT_OMITTED_ORIGINAL_IDENTITIES_REFERENCED_SEPARATE_PUBLIC_PROJECTION",
                  "original_summary_file_sha256": "f" * 64, "receipts": receipts}
        replay["projection_hash"] = view.digest(replay)
        self.write(folder / "replay-summary.json", replay)
        summary = {"schema_version": "strategy-diagnostics-summary-v1", "mode": "CONTINUOUS_HISTORY",
                   **self.permissions, "plan": plan, "plan_hash": view.digest(plan), "source_content_sha256": view.SOURCES["0.2.2"],
                   "rows": rows, "planned_cells": 16, "completed_cells": 16,
                   "baseline_021_economic_equivalence": [{"all_equal": True} for _ in range(6)],
                   "replay": {"receipt_file_sha256": view.sha(folder / "replay-summary.json"),
                              "receipt_scope": "SANITIZED_PUBLIC_PROJECTION_NOT_CANONICAL_ORIGINAL",
                              "original_private_receipt_file_sha256": "f" * 64}}
        path = folder / "summary.json"
        self.write(path, summary)
        return path, summary

    def test_valid_projection_creates_local_links_and_exact_input_index(self):
        result = view.build(self.root, self.summary_path, None, self.forward_path, None, self.output, self.index)
        markdown = self.output.read_text(encoding="utf-8")
        self.assertEqual(len(result["inputs"]), 17)
        self.assertEqual(result["rendered_markdown_sha256"], view.sha(self.output))
        self.assertIn("0.2.1", markdown)
        self.assertIn("诊断规范摘要尚未提供", markdown)
        self.assertIn("待完整验收回执", markdown)
        self.assertIn("[34](research-evidence/forward.json)", markdown)
        self.assertIn("[110](research-evidence/forward.json)", markdown)
        self.assertFalse(result["forward_72_hour_window_complete"])
        self.assertTrue(all((self.root / entry["path"]).is_file() and view.sha(self.root / entry["path"]) == entry["file_sha256"]
                            for entry in result["inputs"]))

    def test_summary_metric_change_rejected_even_when_projection_hash_still_valid(self):
        self.summary["trajectories"][0]["metrics"]["total_return"] = .1
        self.write(self.summary_path, self.summary)
        with self.assertRaisesRegex(ValueError, "summary_vs_projection"):
            view.load_continuous(self.summary_path)

    def test_projection_byte_change_rejected(self):
        path = self.folder / self.summary["trajectories"][0]["projection_file"]
        path.write_text(path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "file_hash_mismatch"):
            view.load_continuous(self.summary_path)

    def test_resealed_cost_mode_or_range_mixing_is_rejected(self):
        row = self.summary["trajectories"][0]
        original = view.read(self.folder / row["projection_file"])
        for key, value in (("fee_rate", .0016), ("score_start", "2023-04-01T00:00:00Z")):
            spec = deepcopy(original["spec"])
            spec[key] = value
            self.edit_trace("spec", spec)
            with self.assertRaisesRegex(ValueError, "mode_range_cost_or_source"):
                view.load_continuous(self.summary_path)
        self.edit_trace("spec", original["spec"])
        self.edit_trace("mode", "RESET_WINDOWS")
        with self.assertRaisesRegex(ValueError, "mode_range_cost_or_source"):
            view.load_continuous(self.summary_path)

    def test_duplicate_cell_and_outside_projection_rejected(self):
        self.summary["trajectories"][-1] = deepcopy(self.summary["trajectories"][0])
        self.write(self.summary_path, self.summary)
        with self.assertRaisesRegex(ValueError, "matrix_or_source"):
            view.load_continuous(self.summary_path)
        with self.assertRaisesRegex(ValueError, "outside_family_or_missing"):
            view._safe_file(self.folder, "../../../../outside.json")

    def test_null_metric_preserved_and_exposure_can_exceed_initial_allocation(self):
        row = next(row for row in self.summary["trajectories"] if row["method"] == "buy_hold_25pct" and row["cost_factor"] == 1)
        metrics = deepcopy(row["metrics"])
        metrics.update(max_drawdown=None, duration_weighted_close_exposure=.5467)
        row["metrics"] = deepcopy(metrics)
        self.edit_trace("metrics", metrics, method="buy_hold_25pct")
        view.build(self.root, self.summary_path, None, self.forward_path, None, self.output, self.index)
        markdown = self.output.read_text(encoding="utf-8")
        self.assertIn("不可估计 / 未提供", markdown)
        self.assertIn("54.670%", markdown)
        self.assertIn("之后不再平衡", markdown)

    def test_external_text_and_source_paths_are_escaped(self):
        injection = '<script>alert(1)</script>|[click](javascript:evil)\n# forged'
        escaped = view.escape(injection)
        self.assertNotIn("<script>", escaped)
        self.assertNotIn("\n", escaped)
        self.assertIn("\\|", escaped)
        self.assertIn("\\[click\\]\\(javascript:evil\\)", escaped)
        path = self.folder / "source[bad](title).json"
        link = view._link(injection, path, self.output)
        self.assertIn("source%5Bbad%5D%28title%29.json", link)

    def test_nonfinite_bool_and_fractional_counts_rejected(self):
        for value in (float("inf"), float("nan"), True, "0"):
            with self.assertRaises(ValueError):
                view.formatted(value)
        with self.assertRaises(ValueError):
            view.formatted(.5, "count")
        for raw in ('{"x":NaN}', '{"x":1e400}', '{"x":1,"x":2}'):
            path = self.root / "invalid.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaises(ValueError):
                view.read(path)

    def test_forward_counts_recomputed_not_trusted_after_reseal(self):
        self.forward["counts"]["MISSING"] = 0
        self.forward["report_hash"] = view.digest({key: value for key, value in self.forward.items() if key != "report_hash"})
        self.write(self.forward_path, self.forward)
        with self.assertRaisesRegex(ValueError, "summary_vs_rows_count_mismatch"):
            view.load_forward(self.forward_path)

    def test_forward_planned_hours_cannot_be_counted_as_elapsed(self):
        row = next(row for row in self.forward["rows"] if row["status"] == "PLANNED")
        row["elapsed"] = True
        self.forward["report_hash"] = view.digest({key: value for key, value in self.forward.items() if key != "report_hash"})
        self.write(self.forward_path, self.forward)
        with self.assertRaisesRegex(ValueError, "elapsed_range_mismatch"):
            view.load_forward(self.forward_path)

    def test_forward_unique_count_does_not_allow_a_third_strategy_plan(self):
        self.forward["rows"][0]["plan_hash"] = "0" * 64
        self.forward["report_hash"] = view.digest({key: value for key, value in self.forward.items() if key != "report_hash"})
        self.write(self.forward_path, self.forward)
        with self.assertRaisesRegex(ValueError, "fixed_plan_denominator"):
            view.load_forward(self.forward_path)

    def test_complete_flag_requires_actual_replay_and_diagnostic_sources(self):
        with self.assertRaisesRegex(ValueError, "requires_diagnostics_and_continuous_replay"):
            view.build(self.root, self.summary_path, None, self.forward_path, None, self.output, self.index, require_complete=True)
        self.assertFalse(self.output.exists())

    def test_diagnostic_matrix_and_original_projection_metrics_are_checked(self):
        continuous = view.load_continuous(self.summary_path)
        path, summary = self.diagnostics()
        result = view.load_diagnostics(path, continuous)
        self.assertEqual(len(result["traces"]), 16)
        self.assertEqual(result["version"], "0.2.2")
        summary["rows"][0]["total_return"] = .4
        self.write(path, summary)
        with self.assertRaisesRegex(ValueError, "diagnostic_summary_vs_projection_metric"):
            view.load_diagnostics(path, continuous)

    def test_diagnostic_pair_difference_cannot_be_changed_independently(self):
        path, summary = self.diagnostics()
        row = next(row for row in summary["rows"] if row["method"] == "D1")
        row["paired_change"]["total_return"] = .2
        self.write(path, summary)
        with self.assertRaisesRegex(ValueError, "paired_summary_difference"):
            view.load_diagnostics(path, view.load_continuous(self.summary_path))

    def test_diagnostic_replay_hash_and_zero_cost_unavailable_reference_remain_explicit(self):
        path, summary = self.diagnostics()
        continuous = view.load_continuous(self.summary_path)
        result = view.load_diagnostics(path, continuous)
        zeros = [row["row"] for row in result["traces"] if row["row"]["cost_factor"] == 0]
        self.assertTrue(all(row["return_minus_buy_hold_25pct"] is None for row in zeros))
        replay_path = path.parent / "replay-summary.json"
        replay_path.write_text(replay_path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "diagnostic_replay_identity"):
            view.load_diagnostics(path, continuous)

    def test_public_projection_still_binds_each_matrix_cell_after_resealing(self):
        path, summary = self.diagnostics()
        replay_path = path.parent / "replay-summary.json"
        replay = view.read(replay_path)
        first, second = replay["receipts"][:2]
        first["replay"], second["replay"] = second["replay"], first["replay"]
        replay["projection_hash"] = view.digest({key: value for key, value in replay.items() if key != "projection_hash"})
        self.write(replay_path, replay)
        summary["replay"]["receipt_file_sha256"] = view.sha(replay_path)
        self.write(path, summary)
        with self.assertRaisesRegex(ValueError, "public_replay_projection_binding"):
            view.load_diagnostics(path, view.load_continuous(self.summary_path))

    def test_private_machine_provenance_cannot_reenter_resealed_public_projection(self):
        path, summary = self.diagnostics()
        replay_path = path.parent / "replay-summary.json"
        replay = view.read(replay_path)
        public = replay["receipts"][0]["replay"]
        public["replay_provenance"]["machine_receipt"] = {"executable": "synthetic-private-path"}
        public["projection_hash"] = view.digest({key: value for key, value in public.items() if key != "projection_hash"})
        replay["projection_hash"] = view.digest({key: value for key, value in replay.items() if key != "projection_hash"})
        self.write(replay_path, replay)
        summary["replay"]["receipt_file_sha256"] = view.sha(replay_path)
        self.write(path, summary)
        with self.assertRaisesRegex(ValueError, "public_replay_projection_binding"):
            view.load_diagnostics(path, view.load_continuous(self.summary_path))


if __name__ == "__main__":
    unittest.main()
