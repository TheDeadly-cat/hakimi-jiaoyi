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
from hakimi_research.volatility_comparison import (  # noqa: E402
    COMPARISON_AUTHORITY_LOCK,
    VOLATILITY_MATCHED_ACTIVITY_FLOOR,
    VOLATILITY_MATCHED_COMPARISON_ID,
    annualization_factor,
    build_volatility_matched_comparison,
    verify_volatility_matched_comparison,
    volatility_match_method_spec,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class StringAlias(str):
    pass


class VolatilityMatchedComparisonV1Tests(unittest.TestCase):
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

    def test_annualization_factor_is_shared_and_exact(self) -> None:
        self.assertEqual(annualization_factor("stock", "1d"), 252)
        self.assertEqual(annualization_factor("synthetic", "1d"), 365)
        self.assertEqual(annualization_factor("stock", "1h"), 1638)
        for market, timeframe in (
            (StringAlias("stock"), "1d"),
            ("stock", StringAlias("1d")),
            (" stock", "1d"),
            ("stock", "0m"),
        ):
            with self.assertRaises(ValueError):
                annualization_factor(market, timeframe)  # type: ignore[arg-type]

    def test_protocol_preregisters_exact_analytical_method(self) -> None:
        self.assertEqual(len(self.protocol["comparison_methods"]), 1)
        method = self.protocol["comparison_methods"][0]
        self.assertEqual(method["comparison_id"], VOLATILITY_MATCHED_COMPARISON_ID)
        self.assertFalse(method["tradable"])
        self.assertFalse(method["parameter_selection_allowed"])
        self.assertEqual(method["zero_target_policy"], "GAP_NOT_ZERO_FILLED")
        self.assertEqual(
            method["activity_floor_annualized_volatility"],
            "0.000000000001",
        )
        core = {key: value for key, value in method.items() if key != "spec_hash"}
        self.assertEqual(method["spec_hash"], canonical_payload_hash(core))

    def test_report_has_complete_role_cost_comparison_matrix(self) -> None:
        expected = {
            (role, scenario_id)
            for role in ("VALIDATION", "FROZEN_TEST")
            for scenario_id in ("BASE", "DOUBLE_COST", "TRIPLE_COST")
        }
        comparisons = self.report["volatility_matched_comparisons"]
        self.assertEqual(
            {(item["role"], item["scenario_id"]) for item in comparisons},
            expected,
        )
        self.assertEqual(len(comparisons), 6)
        self.assertTrue(
            self.report["quality_gate"][
                "volatility_matched_comparison_matrix_complete"
            ]
        )
        self.assertFalse(
            self.report["quality_gate"][
                "volatility_matched_comparison_observation_complete"
            ]
        )
        self.assertIn(
            "VOLATILITY_MATCHED_COMPARISON_OBSERVATION_INCOMPLETE",
            self.report["quality_gate"]["blockers"],
        )
        for item in comparisons:
            self.assertEqual(item["comparison_status"], "GAP")
            self.assertEqual(
                item["blockers"],
                ["TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR"],
            )
            self.assertEqual(
                item["activity_floor_annualized_volatility"],
                VOLATILITY_MATCHED_ACTIVITY_FLOOR,
            )
            self.assertEqual(item["authority"], COMPARISON_AUTHORITY_LOCK)
            self.assertTrue(all(value is False for value in item["authority"].values()))
            self.assertIsNone(item["scale_factor"])
            self.assertIsNone(item["matched_benchmark_annualized_volatility"])
            self.assertIsNone(item["matched_benchmark_curve_total_return"])
            self.assertIsNone(
                item["strategy_minus_matched_benchmark_curve_total_return"]
            )

    def test_each_comparison_rebuilds_from_bound_source_runs(self) -> None:
        initial = self.protocol["config"]["initial_cash"]
        for item in self.report["volatility_matched_comparisons"]:
            strategy = next(
                record
                for record in self.report["strategy_runs"]
                if record["role"] == item["role"]
                and record["scenario_id"] == item["scenario_id"]
            )
            benchmark = next(
                record
                for record in self.report["benchmark_runs"]
                if record["role"] == item["role"]
                and record["scenario_id"] == item["scenario_id"]
                and record["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
            )
            core = {key: value for key, value in item.items() if key != "method_spec_hash"}
            self.assertTrue(
                verify_volatility_matched_comparison(
                    core,
                    strategy,
                    benchmark,
                    initial_equity=initial,
                    market=self.protocol["config"]["market"],
                    timeframe=self.protocol["config"]["timeframe"],
                )
            )

    def test_comparison_and_source_tampering_fail_closed(self) -> None:
        for field, value in (
            ("scale_factor", 99.0),
            ("comparison_status", "PASS"),
            ("method_spec_hash", "0" * 64),
            ("authority", {"tradable": True}),
            ("role", []),
        ):
            tampered = deepcopy(self.report)
            tampered["volatility_matched_comparisons"][0][field] = value
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
        missing["volatility_matched_comparisons"].pop()
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                missing,
                self.protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_zero_source_volatility_is_unknown_not_divide_by_zero(self) -> None:
        strategy = deepcopy(self.report["strategy_runs"][1])
        benchmark = next(
            deepcopy(item)
            for item in self.report["benchmark_runs"]
            if item["role"] == strategy["role"]
            and item["scenario_id"] == strategy["scenario_id"]
            and item["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
        )
        flat_equity = self.protocol["config"]["initial_cash"]
        for point in benchmark["result"]["equity_curve"]:
            point["equity"] = flat_equity
        strategy["result"]["equity_curve"][-1]["equity"] += 1.0
        comparison = build_volatility_matched_comparison(
            strategy,
            benchmark,
            initial_equity=self.protocol["config"]["initial_cash"],
            market=self.protocol["config"]["market"],
            timeframe=self.protocol["config"]["timeframe"],
        )
        self.assertEqual(comparison["comparison_status"], "GAP")
        self.assertIn(
            "SOURCE_BENCHMARK_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR",
            comparison["blockers"],
        )

    def test_positive_target_activity_remains_observed(self) -> None:
        strategy = deepcopy(self.report["strategy_runs"][1])
        benchmark = next(
            deepcopy(item)
            for item in self.report["benchmark_runs"]
            if item["role"] == strategy["role"]
            and item["scenario_id"] == strategy["scenario_id"]
            and item["benchmark_id"] == "ENGINE_BUY_AND_HOLD"
        )
        initial = self.protocol["config"]["initial_cash"]
        for index, point in enumerate(strategy["result"]["equity_curve"]):
            point["equity"] = initial * (
                1.0 + 0.001 * (index + 1) + (0.0004 if index % 2 else 0.0)
            )
        comparison = build_volatility_matched_comparison(
            strategy,
            benchmark,
            initial_equity=initial,
            market=self.protocol["config"]["market"],
            timeframe=self.protocol["config"]["timeframe"],
        )
        self.assertEqual(comparison["comparison_status"], "OBSERVED")
        self.assertEqual(comparison["blockers"], [])
        self.assertGreater(comparison["scale_factor"], 0.0)
        self.assertIsNotNone(comparison["matched_benchmark_curve_total_return"])

    def test_markdown_is_neutral_and_declares_analytical_limit(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Ex-post volatility-matched analytical comparisons", rendered)
        self.assertIn("ANALYTICAL_ONLY_NOT_TRADABLE", rendered)
        self.assertIn("GAP_NOT_ZERO_FILLED", rendered)
        self.assertIn(
            "TARGET_STRATEGY_VOLATILITY_AT_OR_BELOW_ACTIVITY_FLOOR",
            rendered,
        )
        self.assertIn("Volatility-matched comparator tradable: `false`", rendered)
        self.assertNotIn(
            "VOLATILITY_MATCHED_EXECUTION_BASELINE_NOT_AVAILABLE",
            rendered,
        )
        self.assertIn(
            "Prior-window volatility-target research-simulator benchmark",
            rendered,
        )
        self.assertNotIn("READY", rendered)

    def test_source_envelope_includes_comparison_math(self) -> None:
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/volatility_comparison.py"', source)


if __name__ == "__main__":
    unittest.main()
