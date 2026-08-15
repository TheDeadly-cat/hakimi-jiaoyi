from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.backtest_risk_control_surface import (
    BACKTEST_RISK_CONTROL_GRID,
    build_backtest_risk_control_surface,
)


class BacktestRiskControlSurfaceTests(unittest.TestCase):
    @staticmethod
    def grid(*, default_score: float = 0.0) -> list[dict[str, object]]:
        return [
            {
                "ok": True,
                "position_pct": position,
                "take_profit_pct": take,
                "stop_loss_pct": stop,
                "score": default_score,
                "total_return_pct": 2.0,
                "max_drawdown_pct": 5.0,
                "trade_count": 4,
            }
            for position in BACKTEST_RISK_CONTROL_GRID["position_pct"]
            for take in BACKTEST_RISK_CONTROL_GRID["take_profit_pct"]
            for stop in BACKTEST_RISK_CONTROL_GRID["stop_loss_pct"]
        ]

    @staticmethod
    def set_score(
        rows: list[dict[str, object]],
        position: float,
        take: float,
        stop: float,
        score: float,
        *,
        trade_count: int = 4,
    ) -> None:
        for row in rows:
            if (
                float(row["position_pct"]) == position
                and float(row["take_profit_pct"]) == take
                and float(row["stop_loss_pct"]) == stop
            ):
                row["score"] = score
                row["trade_count"] = trade_count
                return
        raise AssertionError("grid cell missing")

    def test_multiaxis_near_best_neighbors_form_local_plateau(self) -> None:
        rows = self.grid()
        center = (35.0, 2.6, 1.1)
        self.set_score(rows, *center, 10.0)
        for neighbor in (
            (20.0, 2.6, 1.1),
            (50.0, 2.6, 1.1),
            (35.0, 1.8, 1.1),
            (35.0, 3.8, 1.1),
            (35.0, 2.6, 0.7),
            (35.0, 2.6, 1.6),
        ):
            self.set_score(rows, *neighbor, 9.0)
        before = copy.deepcopy(rows)

        snapshot = build_backtest_risk_control_surface(rows)

        self.assertEqual(rows, before)
        self.assertEqual(snapshot["schema_version"], "backtest-risk-control-surface-v1")
        self.assertEqual(snapshot["status"], "LOCAL_PLATEAU")
        self.assertEqual(snapshot["expected_cell_count"], 100)
        self.assertEqual(snapshot["mapped_cell_count"], 100)
        self.assertEqual(snapshot["supported_axis_count"], 3)
        self.assertEqual(snapshot["connected_near_best_cell_count"], 7)
        self.assertFalse(snapshot["signal_parameter_stability_checked"])
        self.assertFalse(snapshot["parameter_selection_allowed"])
        self.assertFalse(snapshot["profitability_proven"])
        self.assertFalse(snapshot["automatic_paper_activation_allowed"])
        self.assertFalse(snapshot["execution_allowed"])
        self.assertFalse(snapshot["order_submission_allowed"])
        self.assertFalse(snapshot["paper_authorized"])
        self.assertFalse(snapshot["live_order_allowed"])

    def test_isolated_best_is_exposed_as_peak_only(self) -> None:
        rows = self.grid()
        self.set_score(rows, 35.0, 2.6, 1.1, 10.0)

        snapshot = build_backtest_risk_control_surface(rows)

        self.assertEqual(snapshot["status"], "PEAK_ONLY")
        self.assertEqual(snapshot["connected_near_best_cell_count"], 1)
        self.assertEqual(snapshot["supported_axis_count"], 0)
        self.assertIn(
            "risk_control_surface_peak_without_multiaxis_neighborhood",
            snapshot["blockers"],
        )

    def test_best_cell_with_no_trades_is_not_replaced_by_second_best(self) -> None:
        rows = self.grid()
        self.set_score(rows, 35.0, 2.6, 1.1, 10.0, trade_count=0)
        self.set_score(rows, 20.0, 2.6, 1.1, 9.0)

        snapshot = build_backtest_risk_control_surface(rows)

        self.assertEqual(snapshot["status"], "HIGHEST_SCORE_CELL_UNUSABLE")
        self.assertEqual(snapshot["highest_score_cell"]["position_pct"], 35)
        self.assertFalse(snapshot["highest_score_cell"]["quality_usable"])

    def test_missing_duplicate_and_unknown_cells_fail_closed(self) -> None:
        incomplete = self.grid()[:-1]
        self.assertEqual(
            build_backtest_risk_control_surface(incomplete)["status"],
            "INCOMPLETE_GRID",
        )

        duplicate = self.grid()
        duplicate.append(copy.deepcopy(duplicate[0]))
        duplicate_snapshot = build_backtest_risk_control_surface(duplicate)
        self.assertEqual(duplicate_snapshot["status"], "BLOCK")
        self.assertIn("risk_control_surface_duplicate_grid_cell", duplicate_snapshot["blockers"])

        outside = self.grid()
        outside[0]["position_pct"] = 99
        outside_snapshot = build_backtest_risk_control_surface(outside)
        self.assertEqual(outside_snapshot["status"], "BLOCK")
        self.assertIn("risk_control_surface_candidate_outside_frozen_grid", outside_snapshot["blockers"])

    def test_nonpositive_and_absent_surfaces_remain_descriptive(self) -> None:
        nonpositive = build_backtest_risk_control_surface(self.grid(default_score=-1.0))
        self.assertEqual(nonpositive["status"], "NON_POSITIVE_SURFACE")
        self.assertFalse(nonpositive["performance_claim_allowed"])

        absent = build_backtest_risk_control_surface([])
        self.assertEqual(absent["status"], "NOT_AVAILABLE")
        self.assertEqual(absent["cells"], [])
        self.assertFalse(absent["frozen_research_evidence"])


if __name__ == "__main__":
    unittest.main()
