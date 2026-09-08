from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for path in (str(SRC_ROOT), str(OUTPUT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.walk_forward import (  # noqa: E402
    WALK_FORWARD_AUTHORITY_LOCK,
    build_fixed_walk_forward_schedule,
    build_fixed_walk_forward_summary,
    fixed_walk_forward_method_spec,
    verify_fixed_walk_forward_schedule,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FixedParameterWalkForwardV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.frame = synthetic_frame()
        cls.config = config()
        cls.protocol = protocol(cls.frame, cls.config)
        cls.report = build_frozen_evaluation_report(
            cls.protocol,
            cls.frame,
            cls.config,
            experiment_context=context(),
        )

    def test_schedule_is_fixed_chronological_and_leaves_tail_unconsumed(self) -> None:
        schedule = self.protocol["walk_forward"]["schedule"]
        self.assertTrue(verify_fixed_walk_forward_schedule(schedule, self.frame))
        self.assertEqual(schedule["unused_tail_rows"], 21)
        self.assertEqual([item["fold_id"] for item in schedule["folds"]], ["WF01", "WF02"])
        first, second = schedule["folds"]
        self.assertEqual(first["evaluation"]["row_count"], 35)
        self.assertEqual(second["evaluation"]["row_count"], 35)
        self.assertEqual(second["calibration"], {
            **first["evaluation"],
            "name": "CALIBRATION",
        })
        self.assertLessEqual(
            first["evaluation"]["end_position_exclusive"],
            second["evaluation"]["start_position"],
        )

    def test_protocol_method_forbids_fitting_ranking_and_selection(self) -> None:
        method = self.protocol["walk_forward"]["method"]
        self.assertEqual(method["strategy_params_source"], "FROZEN_PROTOCOL_FIXED_NO_FITTING")
        self.assertEqual(method["calibration_action"], "NONE_FIXED_PARAMETERS")
        self.assertEqual(method["nested_manifest_role"], "UNCLASSIFIED")
        self.assertFalse(method["parameter_selection_allowed"])
        self.assertFalse(method["ranking_allowed"])
        core = {key: value for key, value in method.items() if key != "spec_hash"}
        self.assertEqual(method["spec_hash"], canonical_payload_hash(core))

    def test_report_has_complete_non_rankable_fold_cost_matrix(self) -> None:
        expected = {
            (fold_id, scenario_id)
            for fold_id in ("WF01", "WF02")
            for scenario_id in ("BASE", "DOUBLE_COST", "TRIPLE_COST")
        }
        runs = self.report["walk_forward_runs"]
        self.assertEqual(
            {(item["fold_id"], item["scenario_id"]) for item in runs},
            expected,
        )
        self.assertEqual(len(runs), 6)
        self.assertTrue(self.report["quality_gate"]["walk_forward_fixed_schedule_complete"])
        for record in runs:
            manifest = record["experiment_manifest"]
            self.assertEqual(record["role"], "WALK_FORWARD_EVAL")
            self.assertEqual(manifest["evaluation_role"], "UNCLASSIFIED")
            self.assertFalse(manifest["ranking_gate"]["input_allowed"])
            self.assertFalse(manifest["parameter_selection_allowed"])
            self.assertFalse(manifest["paper_authorized"])
            self.assertFalse(manifest["live_order_allowed"])
            self.assertFalse(manifest["order_entry_allowed"])

    def test_summary_covers_every_fold_without_selection(self) -> None:
        summary = self.report["walk_forward_summary"]
        expected = build_fixed_walk_forward_summary(
            self.report["walk_forward_runs"],
            self.protocol["walk_forward"]["schedule"],
        )
        self.assertEqual(summary, expected)
        self.assertFalse(summary["parameter_selection_performed"])
        self.assertFalse(summary["ranking_performed"])
        self.assertEqual(summary["authority"], WALK_FORWARD_AUTHORITY_LOCK)
        self.assertEqual(len(summary["scenario_summaries"]), 3)
        self.assertTrue(
            all(item["fold_count"] == 2 for item in summary["scenario_summaries"])
        )

    def test_schedule_method_and_report_tampering_fail_closed(self) -> None:
        for mutate in (
            lambda x: x["walk_forward"]["schedule"]["folds"].reverse(),
            lambda x: x["walk_forward"]["schedule"].__setitem__("schedule_hash", "0" * 64),
            lambda x: x["walk_forward"]["method"].__setitem__("ranking_allowed", True),
        ):
            tampered_protocol = deepcopy(self.protocol)
            mutate(tampered_protocol)
            with self.assertRaises(ValueError):
                verify_frozen_evaluation_report(
                    self.report,
                    tampered_protocol,
                    self.frame,
                    self.config,
                    experiment_context=context(),
                )
        for field, value in (
            ("fold_id", "WF99"),
            ("method_spec_hash", "0" * 64),
            ("evaluation_window", {}),
            ("result", []),
            ("experiment_manifest", []),
        ):
            tampered = deepcopy(self.report)
            tampered["walk_forward_runs"][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    verify_frozen_evaluation_report(
                        tampered,
                        self.protocol,
                        self.frame,
                        self.config,
                        experiment_context=context(),
                    )
        missing = deepcopy(self.report)
        missing["walk_forward_runs"].pop()
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                missing,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_method_and_schedule_builds_are_fresh(self) -> None:
        first = fixed_walk_forward_method_spec()
        second = fixed_walk_forward_method_spec()
        first["cost_scenarios"].append("FORGED")
        self.assertEqual(second["cost_scenarios"], ["BASE", "DOUBLE_COST", "TRIPLE_COST"])
        left = build_fixed_walk_forward_schedule(self.frame)
        right = build_fixed_walk_forward_schedule(self.frame)
        left["folds"][0]["evaluation"]["row_count"] = 1
        self.assertEqual(right["folds"][0]["evaluation"]["row_count"], 35)

    def test_markdown_is_neutral_and_exposes_maturity_limits(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Fixed-parameter walk-forward observations", rendered)
        self.assertIn("NONE_FIXED_PARAMETERS", rendered)
        self.assertIn("nested manifest role: `UNCLASSIFIED`", rendered)
        self.assertIn("ranking: `false`", rendered)
        self.assertIn("WALK_FORWARD_REAL_MARKET_AND_LONG_HORIZON_NOT_AVAILABLE", rendered)
        self.assertNotIn("WALK_FORWARD_NOT_BOUND_TO_ADR0509", rendered)
        self.assertNotIn("READY", rendered)

    def test_source_envelope_includes_walk_forward_producer(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/walk_forward.py"', source)


if __name__ == "__main__":
    unittest.main()
