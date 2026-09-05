from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
activate_canonical_source()

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_distribution import (  # noqa: E402
    FROZEN_DISTRIBUTION_AUTHORITY_LOCK,
    frozen_distribution_policy_spec,
)
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FrozenTailDistributionAnalysisV1Tests(unittest.TestCase):
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

    def test_policy_is_fixed_partial_and_non_selecting(self) -> None:
        policy = self.protocol["tail_distribution_policy"]
        self.assertEqual(policy["tail_var_95_minimum_observations"], 20)
        self.assertEqual(policy["tail_var_99_minimum_observations"], 100)
        self.assertEqual(
            policy["unknown_metric_policy"],
            "NULL_WITH_EXPLICIT_GAP_NEVER_ZERO_FILL",
        )
        self.assertFalse(policy["formal_inference_allowed"])
        self.assertFalse(policy["performance_selection_allowed"])
        self.assertFalse(policy["ranking_allowed"])
        self.assertFalse(policy["signal_allowed"])
        core = {key: value for key, value in policy.items() if key != "spec_hash"}
        self.assertEqual(policy["spec_hash"], canonical_payload_hash(core))

    def test_six_source_bound_analyses_retain_all_returns(self) -> None:
        analyses = self.report["tail_distribution_analysis"]
        self.assertEqual(len(analyses), 6)
        self.assertEqual(
            [(item["role"], item["scenario_id"]) for item in analyses],
            [
                (role, scenario)
                for role in ("VALIDATION", "FROZEN_TEST")
                for scenario in ("BASE", "DOUBLE_COST", "TRIPLE_COST")
            ],
        )
        self.assertTrue(
            self.report["quality_gate"]["tail_distribution_analyses_complete"]
        )
        for analysis in analyses:
            self.assertEqual(analysis["coverage"]["period_return_count"], 10)
            self.assertTrue(analysis["coverage"]["all_source_observations_retained"])
            self.assertEqual(analysis["authority"], FROZEN_DISTRIBUTION_AUTHORITY_LOCK)
            self.assertTrue(all(value is False for value in analysis["authority"].values()))

    def test_insufficient_metrics_remain_unknown_with_explicit_gaps(self) -> None:
        for analysis in self.report["tail_distribution_analysis"]:
            evidence = analysis["distribution_evidence"]
            metrics = evidence["metrics"]
            self.assertEqual(evidence["status"], "PARTIAL")
            self.assertEqual(metrics["closed_trade_count"], 0)
            self.assertIsNone(metrics["tail_var_95"])
            self.assertIsNone(metrics["tail_cvar_95"])
            self.assertIsNone(metrics["tail_var_99"])
            self.assertIsNone(metrics["tail_cvar_99"])
            self.assertIsNone(metrics["sortino_ratio"])
            self.assertIsNone(metrics["calmar_ratio"])
            for gap in (
                "TAIL_SAMPLE_LT_20",
                "TAIL_SAMPLE_LT_100",
                "SORTINO_UNDEFINED_NO_DOWNSIDE",
                "CALMAR_UNDEFINED_NO_DRAWDOWN",
                "TRADE_DISTRIBUTION_UNAVAILABLE",
            ):
                self.assertIn(gap, evidence["gaps"])
            self.assertEqual(analysis["metric_states"]["tail_var_95"], "UNKNOWN")
            concentration = evidence["concentration"]
            self.assertEqual(
                concentration["best_fixed_21_period_window"]["state"],
                "GAP",
            )
            self.assertIn("FIXED_21_PERIOD_WINDOW_UNAVAILABLE", evidence["gaps"])

    def test_initial_equity_anchor_and_source_hashes_are_bound(self) -> None:
        windows = {
            item["name"]: item for item in self.protocol["partition_plan"]["windows"]
        }
        for analysis in self.report["tail_distribution_analysis"]:
            binding = analysis["source_binding"]
            window = windows[analysis["role"]]
            role_frame = self.frame.iloc[
                window["start_position"]:window["end_position_exclusive"]
            ]
            self.assertEqual(
                binding["initial_equity_anchor"],
                {
                    "time": str(role_frame.index[29]),
                    "equity": float(self.config.initial_cash),
                },
            )
            for field in (
                "frame_data_hash",
                "source_run_hash",
                "source_result_hash",
                "source_experiment_manifest_hash",
                "source_reproducibility_run_hash",
                "source_equity_curve_hash",
                "projected_result_hash",
            ):
                self.assertRegex(binding[field], r"^[0-9a-f]{64}$")

    def test_protocol_analysis_metric_and_authority_tampering_fail_closed(self) -> None:
        mutations = (
            lambda value: value["tail_distribution_analysis"][0]["distribution_evidence"]["metrics"].__setitem__("tail_var_95", "0"),
            lambda value: value["tail_distribution_analysis"][0]["source_binding"].__setitem__("frame_data_hash", "0" * 64),
            lambda value: value["tail_distribution_analysis"][0]["coverage"].__setitem__("period_return_count", 9),
            lambda value: value["tail_distribution_analysis"][0]["authority"].__setitem__("formal_inference", True),
            lambda value: value["tail_distribution_analysis"][0].__setitem__("analysis_hash", "0" * 64),
        )
        for mutate in mutations:
            tampered = deepcopy(self.report)
            mutate(tampered)
            with self.assertRaises(ValueError):
                verify_frozen_evaluation_report(
                    tampered,
                    self.protocol,
                    self.frame,
                    self.config,
                    experiment_context=context(),
                )
        tampered_protocol = deepcopy(self.protocol)
        tampered_protocol["tail_distribution_policy"]["formal_inference_allowed"] = True
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                self.report,
                tampered_protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_markdown_is_neutral_and_replaces_the_unbound_gap(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Partial tail and distribution analysis", rendered)
        self.assertIn("DESCRIPTIVE_PARTIAL_NOT_INFERENCE_NOT_SIGNAL", rendered)
        self.assertIn("TAIL_DISTRIBUTION_ONLY_TEN_SYNTHETIC_OBSERVATIONS", rendered)
        self.assertNotIn("TAIL_AND_DISTRIBUTION_METRICS_NOT_AVAILABLE", rendered)
        self.assertIn("UNKNOWN", rendered)
        self.assertIn("Return-contribution concentration", rendered)
        self.assertNotIn("READY", rendered)

    def test_policy_is_fresh_and_source_envelope_is_current(self) -> None:
        first = frozen_distribution_policy_spec()
        second = frozen_distribution_policy_spec()
        first["roles"].append("TRAIN")
        self.assertEqual(second["roles"], ["VALIDATION", "FROZEN_TEST"])
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/distribution_evidence.py"', source)
        self.assertIn('"src/hakimi_research/frozen_distribution.py"', source)


if __name__ == "__main__":
    unittest.main()
