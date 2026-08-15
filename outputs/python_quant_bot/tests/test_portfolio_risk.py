from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_risk import (
    aligned_return_correlation,
    build_correlation_matrix,
    evaluate_portfolio_risk,
)


def price_rows(returns: list[float]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    close = 100.0
    start = date(2025, 1, 1)
    for index, daily_return in enumerate([0.0, *returns]):
        previous = close
        close *= 1.0 + daily_return
        rows.append({
            "date": (start + timedelta(days=index)).isoformat(),
            "ts_ms": index * 86_400_000,
            "open": previous,
            "high": max(previous, close) * 1.01,
            "low": min(previous, close) * 0.99,
            "close": close,
            "volume": 1_000_000,
            "complete": True,
        })
    return rows


class PortfolioRiskTests(unittest.TestCase):
    def test_aligned_returns_build_a_high_correlation(self) -> None:
        returns = [0.01 if index % 2 == 0 else -0.006 for index in range(60)]
        report = aligned_return_correlation(price_rows(returns), price_rows([value * 0.8 for value in returns]))

        self.assertEqual(report["status"], "PASS")
        self.assertGreater(report["correlation"], 0.99)

    def test_correlation_matrix_is_hashed_and_never_authorizes_paper(self) -> None:
        returns = [0.008 if index % 3 else -0.004 for index in range(60)]
        report = build_correlation_matrix({
            "AAPL": {"rows": price_rows(returns)},
            "MSFT": {"rows": price_rows([value * 0.7 for value in returns])},
        })

        self.assertEqual(report["status"], "PASS")
        self.assertIn("AAPL|MSFT", report["pairs"])
        self.assertTrue(report["matrix_hash"])
        self.assertFalse(report["paper_authorized"])

    def test_single_position_within_budget_passes(self) -> None:
        report = evaluate_portfolio_risk(
            equity=10_000,
            positions=[],
            proposed_symbol="AAPL",
            proposed_notional=3_500,
        )

        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["portfolio_gate_passed"])
        self.assertFalse(report["paper_authorized"])

    def test_single_position_above_budget_is_blocked(self) -> None:
        report = evaluate_portfolio_risk(
            equity=10_000,
            positions=[],
            proposed_symbol="AAPL",
            proposed_notional=3_501,
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("single_position_limit", [item["name"] for item in report["checks"] if not item["ok"]])

    def test_highly_correlated_positions_share_one_cluster_budget(self) -> None:
        report = evaluate_portfolio_risk(
            equity=10_000,
            positions=[{"symbol": "NVDA", "notional": 2_000, "direction": "LONG"}],
            proposed_symbol="AMD",
            proposed_notional=3_000,
            correlations={"AMD|NVDA": 0.92},
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("correlated_cluster_limit", [item["name"] for item in report["checks"] if not item["ok"]])

    def test_new_symbol_without_correlation_coverage_is_blocked(self) -> None:
        report = evaluate_portfolio_risk(
            equity=10_000,
            positions=[{"symbol": "NVDA", "notional": 1_000, "direction": "LONG"}],
            proposed_symbol="AAPL",
            proposed_notional=1_000,
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("correlation_coverage", [item["name"] for item in report["checks"] if not item["ok"]])

    def test_down_regime_has_zero_new_long_budget(self) -> None:
        report = evaluate_portfolio_risk(
            equity=10_000,
            positions=[],
            proposed_symbol="AAPL",
            proposed_notional=100,
            regime={"status": "PASS", "regime_id": "DOWN_NORMAL", "long_only_budget_multiplier": 0.0},
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(report["regime_budget_multiplier"], 0.0)

    def test_risk_reduction_is_never_blocked_by_portfolio_limits(self) -> None:
        report = evaluate_portfolio_risk(
            equity=0,
            positions=[{"symbol": "AAPL", "notional": 15_000, "direction": "LONG"}],
            proposed_symbol="AAPL",
            proposed_notional=15_000,
            risk_increasing=False,
        )

        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["portfolio_gate_passed"])


if __name__ == "__main__":
    unittest.main()
