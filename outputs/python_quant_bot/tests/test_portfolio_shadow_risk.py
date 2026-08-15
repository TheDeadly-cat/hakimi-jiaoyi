from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_shadow_risk import build_shadow_portfolio_risk


def candidate(*, same_cluster: bool = False) -> dict[str, object]:
    return {
        "candidate_hash": "candidate-1",
        "spec": {
            "clusters": {
                "AAPL": "MEGA",
                "NVDA": "MEGA" if same_cluster else "CHIPS",
            },
        },
    }


def backtest(*, targets: bool = True, adjustment_ok: bool = True) -> dict[str, object]:
    symbols = ["AAPL", "NVDA"] if targets else []
    return {
        "ok": True,
        "dataset_manifest": {
            "data_hash": "data-1",
            "last": "2026-08-03",
            "adjustment_evidence": {
                symbol: {"backtest_eligible": adjustment_ok, "evidence_hash": f"evidence-{symbol}"}
                for symbol in symbols
            },
        },
        "pending_decision_at_end": {
            "signal_date": "2026-08-03",
            "target_symbols": symbols,
            "target_weights": {"AAPL": 0.5, "NVDA": 0.5} if targets else {},
            "target_allocation_pct": 60.0 if targets else 0.0,
            "liquidity": {
                symbol: {"eligible": True, "median_dollar_volume": 100_000_000}
                for symbol in symbols
            },
            "regime": {"status": "PASS", "regime_id": "UP_NORMAL", "long_only_budget_multiplier": 1.0},
        },
    }


def correlations() -> dict[str, object]:
    return {
        "status": "PASS",
        "matrix_hash": "matrix-1",
        "pairs": {"AAPL|NVDA": {"status": "PASS", "correlation": 0.20}},
    }


class PortfolioShadowRiskTests(unittest.TestCase):
    def test_diversified_liquid_target_passes_read_only_risk_snapshot(self) -> None:
        result = build_shadow_portfolio_risk(
            candidate=candidate(),
            backtest_report=backtest(),
            correlation_matrix=correlations(),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["per_symbol"]), 2)
        self.assertTrue(result["risk_snapshot_hash"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_named_cluster_concentration_is_blocked(self) -> None:
        result = build_shadow_portfolio_risk(
            candidate=candidate(same_cluster=True),
            backtest_report=backtest(),
            correlation_matrix=correlations(),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any("Named cluster" in item for item in result["blockers"]))

    def test_unverified_adjustment_evidence_is_blocked(self) -> None:
        result = build_shadow_portfolio_risk(
            candidate=candidate(),
            backtest_report=backtest(adjustment_ok=False),
            correlation_matrix=correlations(),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("AAPL:adjustment_not_eligible", result["blockers"])

    def test_risk_off_decision_is_valid_cash_state(self) -> None:
        result = build_shadow_portfolio_risk(
            candidate=candidate(),
            backtest_report=backtest(targets=False),
            correlation_matrix={"status": "BLOCK", "pairs": {}},
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["target_symbols"], [])
        self.assertEqual(result["target_allocation_pct"], 0.0)

    def test_hold_decision_recovers_weights_without_requiring_a_new_fill(self) -> None:
        report = backtest()
        report["pending_decision_at_end"] = {
            "signal_date": "2026-08-04",
            "target_symbols": ["AAPL", "NVDA"],
            "target_weights": {},
            "target_allocation_pct": 60.0,
            "reason": "hold_between_rebalances",
            "execute": False,
        }
        report["final_positions"] = {
            "AAPL": {"market_value": 30_000},
            "NVDA": {"market_value": 30_000},
        }
        report["decisions"] = [backtest()["pending_decision_at_end"]]

        result = build_shadow_portfolio_risk(
            candidate=candidate(),
            backtest_report=report,
            correlation_matrix=correlations(),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["hold_observation"])
        self.assertEqual(result["weight_source"], "FINAL_POSITION_MARKET_VALUES")

    def test_valid_underallocation_is_treated_as_a_cash_reserve(self) -> None:
        report = backtest()
        report["pending_decision_at_end"]["target_weights"] = {"AAPL": 0.25, "NVDA": 0.25}

        result = build_shadow_portfolio_risk(
            candidate=candidate(),
            backtest_report=report,
            correlation_matrix=correlations(),
        )

        self.assertEqual(result["status"], "PASS")
        weight_check = next(item for item in result["checks"] if item["name"] == "weight_sum")
        self.assertTrue(weight_check["ok"])
        self.assertEqual(weight_check["detail"], "0.50000000")


if __name__ == "__main__":
    unittest.main()
