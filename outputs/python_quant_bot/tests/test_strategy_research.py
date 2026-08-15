from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_research import (
    RAW_EXCESS_LANE,
    RISK_ADJUSTED_LANE,
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
    aggregate_validation_variant,
    build_parameter_variants,
    freeze_validation_candidates,
)


def validation_cell(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "dataset_status": "PASS",
        "train_ok": True,
        "validation_ok": True,
        "train_return_pct": 10.0,
        "validation_return_pct": 8.0,
        "validation_excess_return_pct": 5.0,
        "validation_trade_count": 3,
        "validation_max_drawdown_pct": 5.0,
        "validation_sharpe": 1.0,
        "validation_drawdown_improvement_pct": 3.0,
        "validation_sharpe_excess": 0.4,
        "validation_risk_efficiency_excess": 0.8,
        "fold_stability_status": "PASS",
        "cost_sensitivity_status": "PASS",
        "lookahead_status": "PASS",
    }


class StrategyResearchTests(unittest.TestCase):
    def test_parameter_variants_are_deterministic_and_preserve_base_metadata(self) -> None:
        base = {"position_pct": 0.25, "fast_window": 20, "slow_window": 60}

        first = build_parameter_variants("dual_ma", base)
        second = build_parameter_variants("dual_ma", base)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual(len({row["variant_id"] for row in first}), 3)
        self.assertTrue(all(row["params"]["position_pct"] == 0.25 for row in first))

    def test_cumulative_300_trials_flips_a_marginal_three_trial_candidate(self) -> None:
        variant = build_parameter_variants("dual_ma", {})[0]
        marginal = {
            "symbol": "AAPL",
            "dataset_status": "PASS",
            "train_ok": True,
            "validation_ok": True,
            "train_return_pct": 1.0,
            "validation_return_pct": 2.0,
            "validation_excess_return_pct": 0.5,
            "validation_trade_count": 2,
            "validation_max_drawdown_pct": 0.1,
            "validation_sharpe": 1.0,
            "validation_drawdown_improvement_pct": 0.0,
            "validation_sharpe_excess": 0.0,
            "validation_risk_efficiency_excess": 0.0,
            "fold_stability_status": "PASS",
            "cost_sensitivity_status": "PASS",
            "lookahead_status": "PASS",
        }

        local_grid = aggregate_validation_variant(
            variant,
            [marginal],
            required_symbols=1,
            total_variant_trials=3,
        )
        cumulative_search = aggregate_validation_variant(
            variant,
            [marginal],
            required_symbols=1,
            total_variant_trials=300,
        )

        self.assertTrue(local_grid["eligible_for_test"])
        self.assertEqual(local_grid["selection_lane"], RAW_EXCESS_LANE)
        self.assertFalse(cumulative_search["eligible_for_test"])
        self.assertIn(
            "RAW_EXCESS:multiple_trial_adjusted_score_not_positive",
            cumulative_search["blockers"],
        )

    def test_volume_trend_research_has_three_bounded_variants(self) -> None:
        variants = build_parameter_variants("volume_trend", {"atr_window": 14})

        self.assertEqual(len(variants), 3)
        self.assertEqual([row["variant_label"] for row in variants], ["responsive", "balanced", "strict"])
        self.assertTrue(all(row["params"]["atr_window"] == 14 for row in variants))
        self.assertTrue(all(row["params"]["volume_ratio"] >= 1.0 for row in variants))

    def test_squeeze_breakout_variants_freeze_distinct_contraction_thresholds(self) -> None:
        variants = build_parameter_variants("squeeze_breakout", {})

        self.assertEqual(len(variants), 3)
        self.assertEqual([row["variant_label"] for row in variants], ["responsive", "balanced", "strict"])
        self.assertEqual(len({row["param_hash"] for row in variants}), 3)
        self.assertTrue(all(row["params"]["atr_long_window"] > row["params"]["atr_short_window"] for row in variants))
        self.assertTrue(all(row["params"]["volume_expansion_ratio"] >= 1.2 for row in variants))

    def test_validation_gate_passes_only_cross_symbol_robust_variant(self) -> None:
        variant = build_parameter_variants("dual_ma", {})[0]
        cells = [validation_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]

        passed = aggregate_validation_variant(variant, cells, required_symbols=6, total_variant_trials=24)
        failed_cells = [dict(cell) for cell in cells]
        for cell in failed_cells[:3]:
            cell["validation_excess_return_pct"] = -2.0
            cell["validation_drawdown_improvement_pct"] = -1.0
            cell["validation_sharpe_excess"] = -0.2
            cell["validation_risk_efficiency_excess"] = -0.2
        failed = aggregate_validation_variant(variant, failed_cells, required_symbols=6, total_variant_trials=24)

        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(passed["selection_lane"], RAW_EXCESS_LANE)
        self.assertTrue(passed["eligible_for_test"])
        self.assertEqual(passed["validation_drawdown_improved_symbols"], 6)
        self.assertEqual(passed["validation_sharpe_excess_positive_symbols"], 6)
        self.assertEqual(passed["validation_risk_efficiency_positive_symbols"], 6)
        self.assertEqual(failed["status"], "BLOCK")
        self.assertIn("RAW_EXCESS:validation_excess_positive_symbols:3<4", failed["blockers"])

    def test_validation_can_freeze_a_strict_risk_adjusted_candidate(self) -> None:
        variant = build_parameter_variants("turtle", {})[0]
        cells = [validation_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC")]
        for cell in cells:
            cell.update({
                "validation_excess_return_pct": -1.0,
                "validation_drawdown_improvement_pct": 6.0,
                "validation_sharpe_excess": 0.5,
                "validation_risk_efficiency_excess": 1.2,
            })

        result = aggregate_validation_variant(variant, cells, required_symbols=5, total_variant_trials=27)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selection_lane"], RISK_ADJUSTED_LANE)
        self.assertGreater(result["risk_adjusted_score"], 0)

    def test_validation_gate_fails_closed_on_nonfinite_metrics_and_truthy_strings(self) -> None:
        variant = build_parameter_variants("dual_ma", {})[0]
        symbols = ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")
        nonfinite = [validation_cell(symbol) for symbol in symbols]
        nonfinite[0]["validation_return_pct"] = float("nan")
        truthy_string = [validation_cell(symbol) for symbol in symbols]
        truthy_string[0]["validation_ok"] = "true"

        nonfinite_result = aggregate_validation_variant(
            variant,
            nonfinite,
            required_symbols=6,
            total_variant_trials=3,
        )
        truthy_result = aggregate_validation_variant(
            variant,
            truthy_string,
            required_symbols=6,
            total_variant_trials=3,
        )

        self.assertEqual(nonfinite_result["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", nonfinite_result["blockers"])
        self.assertEqual(truthy_result["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", truthy_result["blockers"])

        pseudo_numeric = [validation_cell(symbol) for symbol in symbols]
        pseudo_numeric[0]["validation_trade_count"] = "3"
        pseudo_numeric_result = aggregate_validation_variant(
            variant,
            pseudo_numeric,
            required_symbols=6,
            total_variant_trials=3,
        )
        self.assertEqual(pseudo_numeric_result["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", pseudo_numeric_result["blockers"])

        negative_count = [validation_cell(symbol) for symbol in symbols]
        negative_count[0]["validation_trade_count"] = -1
        negative_count_result = aggregate_validation_variant(
            variant,
            negative_count,
            required_symbols=6,
            total_variant_trials=3,
        )
        self.assertEqual(negative_count_result["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", negative_count_result["blockers"])

    def test_freeze_selects_one_validation_winner_per_strategy_before_test(self) -> None:
        rows = [
            {"strategy_id": "dual_ma", "variant_id": "dual:1", "params": {}, "param_hash": "1", "implementation_fingerprint": "a", "eligible_for_test": True, "adjusted_score": 3.0, "selection_lane": RAW_EXCESS_LANE},
            {"strategy_id": "dual_ma", "variant_id": "dual:2", "params": {}, "param_hash": "2", "implementation_fingerprint": "b", "eligible_for_test": True, "adjusted_score": 2.0, "selection_lane": RAW_EXCESS_LANE},
            {"strategy_id": "turtle", "variant_id": "turtle:1", "params": {}, "param_hash": "3", "implementation_fingerprint": "c", "eligible_for_test": True, "adjusted_score": 4.0, "selection_lane": RISK_ADJUSTED_LANE},
            {"strategy_id": "rsi", "variant_id": "rsi:1", "params": {}, "param_hash": "4", "implementation_fingerprint": "d", "eligible_for_test": False, "adjusted_score": 9.0},
        ]

        frozen = freeze_validation_candidates(rows, max_candidates=2)

        self.assertEqual([row["variant_id"] for row in frozen], ["turtle:1", "dual:1"])
        self.assertTrue(all(row["frozen_before_test"] for row in frozen))
        self.assertEqual(frozen[0]["selection_lane"], RISK_ADJUSTED_LANE)

    def test_frozen_test_gate_requires_positive_excess_on_four_symbols(self) -> None:
        candidate = {"strategy_id": "dual_ma", "variant_id": "dual:1", "params": {}, "param_hash": "1"}
        cells = [{
            "symbol": symbol,
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 7.0,
            "test_excess_return_pct": 3.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 6.0,
            "test_cost_status": "PASS",
        } for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]

        passed = aggregate_frozen_test(candidate, cells, required_symbols=6)
        for cell in cells[:3]:
            cell["test_excess_return_pct"] = -1.0
        failed = aggregate_frozen_test(candidate, cells, required_symbols=6)

        self.assertEqual(passed["status"], "PASS")
        self.assertEqual(failed["status"], "BLOCK")
        self.assertIn("test_excess_positive_symbols:3<4", failed["blockers"])

    def test_frozen_test_gate_fails_closed_on_nonfinite_metrics(self) -> None:
        candidate = {
            "strategy_id": "dual_ma",
            "variant_id": "dual:1",
            "params": {},
            "param_hash": "1",
        }
        cells = [{
            "symbol": symbol,
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 7.0,
            "test_excess_return_pct": 3.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 6.0,
            "test_cost_status": "PASS",
        } for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        cells[0]["test_excess_return_pct"] = float("inf")

        result = aggregate_frozen_test(candidate, cells, required_symbols=6)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("usable_test_symbols:5<6", result["blockers"])

        pseudo_numeric = [dict(cell) for cell in cells]
        pseudo_numeric[0]["test_trade_count"] = "3"
        pseudo_numeric[0]["test_excess_return_pct"] = 3.0
        pseudo_numeric_result = aggregate_frozen_test(candidate, pseudo_numeric, required_symbols=6)
        self.assertEqual(pseudo_numeric_result["status"], "BLOCK")
        self.assertIn("usable_test_symbols:5<6", pseudo_numeric_result["blockers"])

    def test_risk_adjusted_lane_is_locked_for_test_and_holdout(self) -> None:
        candidate = {
            "strategy_id": "turtle",
            "variant_id": "turtle:short",
            "params": {},
            "param_hash": "1",
            "selection_lane": RISK_ADJUSTED_LANE,
        }
        cells = [{
            "symbol": symbol,
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 6.0,
            "test_excess_return_pct": -1.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 4.0,
            "test_drawdown_improvement_pct": 7.0,
            "test_sharpe_excess": 0.4,
            "test_risk_efficiency_excess": 1.0,
            "test_cost_status": "PASS",
        } for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC")]

        test_result = aggregate_frozen_test(candidate, cells, required_symbols=5)
        holdout_cell = {
            **cells[0],
            "symbol": "QQQ",
            "baseline_ok": True,
            "cost_sensitivity_status": "PASS",
            "temporal_status": "PASS",
            "walk_forward_status": "PASS",
            "lookahead_status": "PASS",
        }
        holdout_result = aggregate_holdout_confirmation(candidate, [holdout_cell], required_symbols=1)

        self.assertEqual(test_result["status"], "PASS")
        self.assertEqual(test_result["test_lane"], RISK_ADJUSTED_LANE)
        self.assertTrue(holdout_result["forward_candidate"])
        self.assertEqual(holdout_result["holdout_lane"], RISK_ADJUSTED_LANE)

    def test_risk_adjusted_test_gate_rejects_missing_risk_metrics(self) -> None:
        candidate = {
            "strategy_id": "turtle",
            "variant_id": "turtle:short",
            "params": {},
            "param_hash": "1",
            "selection_lane": RISK_ADJUSTED_LANE,
        }
        cells = [{
            "symbol": symbol,
            "dataset_status": "PASS",
            "test_ok": True,
            "test_return_pct": 6.0,
            "test_excess_return_pct": -1.0,
            "test_trade_count": 3,
            "test_max_drawdown_pct": 4.0,
            "test_drawdown_improvement_pct": 7.0,
            "test_sharpe_excess": 0.4,
            "test_risk_efficiency_excess": 1.0,
            "test_cost_status": "PASS",
        } for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC")]
        cells[0]["test_sharpe_excess"] = None

        result = aggregate_frozen_test(candidate, cells, required_symbols=5)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("usable_test_symbols:4<5", result["blockers"])


if __name__ == "__main__":
    unittest.main()
