from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
import unittest

from _canonical_source import activate_canonical_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
activate_canonical_source()

from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_report,
    render_frozen_evaluation_markdown,
    verify_frozen_evaluation_report,
)
from hakimi_research.frozen_market_regime import (  # noqa: E402
    MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD,
    MARKET_REGIME_AUTHORITY_LOCK,
    MARKET_REGIME_DIRECTION_THRESHOLD,
    MARKET_REGIME_LOOKBACK_ROWS,
    MARKET_REGIME_TAXONOMY,
    fixed_market_regime_policy_spec,
)
from hakimi_research.volatility_comparison import (  # noqa: E402
    annualization_factor,
    annualized_volatility,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    protocol,
    synthetic_frame,
)


class FrozenMarketRegimeAnalysisV1Tests(unittest.TestCase):
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

    def test_policy_is_fixed_trailing_and_non_selecting(self) -> None:
        policy = self.protocol["market_regime_policy"]
        self.assertEqual(policy["lookback_rows"], 5)
        self.assertEqual(policy["direction_threshold"], 0.005)
        self.assertEqual(policy["annualized_volatility_threshold"], 0.2)
        self.assertEqual(policy["classification_scope"], "EX_POST_DESCRIPTIVE_NOT_SIGNAL")
        self.assertTrue(policy["trailing_only"])
        self.assertFalse(policy["signal_allowed"])
        self.assertFalse(policy["performance_selection_allowed"])
        self.assertFalse(policy["ranking_allowed"])
        core = {key: value for key, value in policy.items() if key != "spec_hash"}
        self.assertEqual(policy["spec_hash"], canonical_payload_hash(core))

    def test_roles_time_grid_taxonomy_and_authority_are_complete(self) -> None:
        analyses = self.report["market_regime_analysis"]
        self.assertEqual([item["role"] for item in analyses], ["VALIDATION", "FROZEN_TEST"])
        self.assertTrue(self.report["quality_gate"]["market_regime_slices_complete"])
        expected_taxonomy = [item[0] for item in MARKET_REGIME_TAXONOMY]
        for analysis in analyses:
            self.assertEqual(analysis["scenario_id"], "BASE")
            self.assertEqual(analysis["taxonomy"], expected_taxonomy)
            self.assertEqual(len(analysis["observations"]), 10)
            self.assertEqual(len(analysis["regime_slices"]), 6)
            self.assertEqual(
                sum(item["observation_count"] for item in analysis["regime_slices"]),
                10,
            )
            self.assertEqual(analysis["authority"], MARKET_REGIME_AUTHORITY_LOCK)
            self.assertTrue(all(value is False for value in analysis["authority"].values()))

    def test_every_observation_recomputes_from_current_and_past_close_only(self) -> None:
        windows = {
            item["name"]: item for item in self.protocol["partition_plan"]["windows"]
        }
        factor = annualization_factor(self.config.market, self.config.timeframe)
        for analysis in self.report["market_regime_analysis"]:
            window = windows[analysis["role"]]
            frame = self.frame.iloc[
                window["start_position"]:window["end_position_exclusive"]
            ]
            closes = [float(value) for value in frame["close"]]
            for offset, observation in enumerate(analysis["observations"]):
                position = 30 + offset
                trailing_return = closes[position] / closes[
                    position - MARKET_REGIME_LOOKBACK_ROWS
                ] - 1.0
                returns = [
                    closes[current] / closes[current - 1] - 1.0
                    for current in range(
                        position - MARKET_REGIME_LOOKBACK_ROWS + 1,
                        position + 1,
                    )
                ]
                volatility = annualized_volatility(returns, factor)
                direction = (
                    "UP"
                    if trailing_return > MARKET_REGIME_DIRECTION_THRESHOLD
                    else "DOWN"
                    if trailing_return < -MARKET_REGIME_DIRECTION_THRESHOLD
                    else "RANGE"
                )
                band = (
                    "HIGH"
                    if volatility >= MARKET_REGIME_ANNUALIZED_VOLATILITY_THRESHOLD
                    else "LOW"
                )
                self.assertEqual(observation["timestamp"], frame.index[position].isoformat())
                self.assertEqual(observation["regime_id"], f"{direction}_{band}")
                self.assertEqual(observation["trailing_close_return"], round(trailing_return, 12))
                self.assertEqual(observation["trailing_annualized_volatility"], volatility)

    def test_empty_taxonomy_cells_remain_explicit_unknowns(self) -> None:
        for analysis in self.report["market_regime_analysis"]:
            for item in analysis["regime_slices"]:
                if item["observation_count"] == 0:
                    self.assertEqual(item["status"], "NO_OBSERVATIONS")
                    self.assertIsNone(item["strategy_compounded_return"])
                    self.assertIsNone(item["strategy_mean_return"])
                    self.assertIsNone(item["market_compounded_return"])
                else:
                    self.assertEqual(item["status"], "OBSERVED")
                    self.assertTrue(math.isfinite(item["strategy_compounded_return"]))

    def test_policy_analysis_source_and_authority_tampering_fail_closed(self) -> None:
        mutations = (
            lambda value: value["market_regime_analysis"][0]["observations"][0].__setitem__("regime_id", "FORGED"),
            lambda value: value["market_regime_analysis"][0]["source_binding"].__setitem__("frame_data_hash", "0" * 64),
            lambda value: value["market_regime_analysis"][0]["regime_slices"][0].__setitem__("observation_count", 99),
            lambda value: value["market_regime_analysis"][0]["authority"].__setitem__("signal", True),
            lambda value: value["market_regime_analysis"][0].__setitem__("analysis_hash", "0" * 64),
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
        tampered_protocol["market_regime_policy"]["signal_allowed"] = True
        with self.assertRaises(ValueError):
            verify_frozen_evaluation_report(
                self.report,
                tampered_protocol,
                self.frame,
                self.config,
                experiment_context=context(),
            )

    def test_markdown_is_neutral_and_exposes_remaining_gap(self) -> None:
        rendered = render_frozen_evaluation_markdown(
            self.report,
            self.protocol,
            self.frame,
            self.config,
        experiment_context=context(),
        )
        self.assertIn("Fixed trailing market-regime analysis", rendered)
        self.assertIn("EX_POST_DESCRIPTIVE_NOT_SIGNAL", rendered)
        self.assertIn("MARKET_REGIME_SLICES_ONLY_SYNTHETIC_FIXED_THRESHOLDS", rendered)
        self.assertNotIn("MARKET_REGIME_SLICES_NOT_BOUND_TO_ADR0509", rendered)
        self.assertNotIn("READY", rendered)

    def test_policy_spec_is_fresh_and_source_envelope_is_current(self) -> None:
        first = fixed_market_regime_policy_spec()
        second = fixed_market_regime_policy_spec()
        first["taxonomy"].append({"regime_id": "FORGED"})
        self.assertEqual(len(second["taxonomy"]), 6)
        source = (
            SRC_ROOT / "hakimi_research" / "deterministic_frozen_benchmark.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"src/hakimi_research/frozen_market_regime.py"', source)


if __name__ == "__main__":
    unittest.main()
