from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.portfolio_execution_rehearsal import (
    run_portfolio_execution_rehearsal,
    run_research_report_execution_rehearsal,
)


CORRELATIONS = {
    "status": "PASS",
    "pairs": {"AAPL|MSFT": {"status": "PASS", "correlation": 0.20}},
}
CLUSTERS = {"AAPL": "MEGA_PLATFORM", "MSFT": "MEGA_PLATFORM_2"}


def backtest_fixture() -> dict[str, object]:
    return {
        "ok": True,
        "run_hash": "a" * 64,
        "dataset_manifest": {"data_hash": "b" * 64},
        "run_spec": {"dataset_hash": "b" * 64, "fee_rate": 0.0005, "initial_cash": 10_000.0},
        "initial_cash": 10_000.0,
        "final_equity": 10_098.95,
        "order_event_count": 2,
        "turnover": 2_100.0,
        "total_fees": 1.05,
        "dividend_receivable": 0.0,
        "corporate_action_events": [],
        "final_positions": {},
        "orders": [
            {
                "signal_date": "2026-01-02",
                "date": "2026-01-05",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 10.0,
                "price": 100.0,
                "fee": 0.5,
                "status": "FILLED",
                "reason": "fixture_entry",
                "fill_basis": "NEXT_BAR_OPEN",
            },
            {
                "signal_date": "2026-01-09",
                "date": "2026-01-12",
                "symbol": "AAPL",
                "side": "SELL",
                "quantity": 10.0,
                "price": 110.0,
                "fee": 0.55,
                "status": "FILLED",
                "reason": "fixture_exit",
                "fill_basis": "NEXT_BAR_OPEN",
            },
        ],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def multi_asset_backtest_fixture() -> dict[str, object]:
    payload = backtest_fixture()
    payload.update(
        {
            "final_equity": 10_147.925,
            "order_event_count": 4,
            "turnover": 4_150.0,
            "total_fees": 2.075,
            "orders": [
                {
                    "signal_date": "2026-01-02",
                    "date": "2026-01-05",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "quantity": 10.0,
                    "price": 100.0,
                    "fee": 0.5,
                    "status": "FILLED",
                    "reason": "fixture_entry",
                    "fill_basis": "NEXT_BAR_OPEN",
                },
                {
                    "signal_date": "2026-01-02",
                    "date": "2026-01-05",
                    "symbol": "MSFT",
                    "side": "BUY",
                    "quantity": 5.0,
                    "price": 200.0,
                    "fee": 0.5,
                    "status": "FILLED",
                    "reason": "fixture_entry",
                    "fill_basis": "NEXT_BAR_OPEN",
                },
                {
                    "signal_date": "2026-01-09",
                    "date": "2026-01-12",
                    "symbol": "AAPL",
                    "side": "SELL",
                    "quantity": 10.0,
                    "price": 110.0,
                    "fee": 0.55,
                    "status": "FILLED",
                    "reason": "fixture_exit",
                    "fill_basis": "NEXT_BAR_OPEN",
                },
                {
                    "signal_date": "2026-01-09",
                    "date": "2026-01-12",
                    "symbol": "MSFT",
                    "side": "SELL",
                    "quantity": 5.0,
                    "price": 210.0,
                    "fee": 0.525,
                    "status": "FILLED",
                    "reason": "fixture_exit",
                    "fill_basis": "NEXT_BAR_OPEN",
                },
            ],
        }
    )
    return payload


class PortfolioExecutionRehearsalTests(unittest.TestCase):
    def test_replays_risk_lifecycle_lineage_and_accounting(self) -> None:
        result = run_portfolio_execution_rehearsal(
            backtest_fixture(),
            stage="test",
            correlations=CORRELATIONS,
            clusters=CLUSTERS,
            generated_at=100,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["risk_pass_count"], 2)
        self.assertEqual(result["lifecycle_fill_count"], 2)
        self.assertEqual(result["lineage_pass_count"], 2)
        self.assertAlmostEqual(result["final_cash"], 10_098.95)
        self.assertTrue(all(check["ok"] for check in result["checks"]))
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_report_rehearsal_is_deterministic_across_all_stages(self) -> None:
        stage = backtest_fixture()
        report = {
            "batch_run_hash": "c" * 64,
            "frozen_candidate": {"candidate_hash": "d" * 64},
            "spec": {"clusters": CLUSTERS},
            "correlation_matrix": CORRELATIONS,
            "validation": deepcopy(stage),
            "test": deepcopy(stage),
            "full": deepcopy(stage),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

        result = run_research_report_execution_rehearsal(report, generated_at=200)
        repeated = run_research_report_execution_rehearsal(report, generated_at=300)

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checks"]["all_stage_rehearsals_deterministic"])
        self.assertTrue(all(item["status"] == "PASS" for item in result["determinism"].values()))
        self.assertEqual(result["report_hash"], repeated["report_hash"])

    def test_multi_asset_rehearsal_separates_symbol_and_gross_position_value(self) -> None:
        result = run_portfolio_execution_rehearsal(
            multi_asset_backtest_fixture(),
            stage="test",
            correlations=CORRELATIONS,
            clusters=CLUSTERS,
            generated_at=100,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["risk_pass_count"], 4)
        self.assertEqual(result["lifecycle_fill_count"], 4)
        self.assertEqual(result["lineage_pass_count"], 4)
        self.assertAlmostEqual(result["final_cash"], 10_147.925)

    def test_blocks_tampered_accounting_and_execution_authority(self) -> None:
        accounting = backtest_fixture()
        accounting["final_equity"] = 11_098.95
        authority = backtest_fixture()
        authority["paper_authorized"] = True

        accounting_result = run_portfolio_execution_rehearsal(
            accounting, stage="test", correlations=CORRELATIONS, clusters=CLUSTERS
        )
        authority_result = run_portfolio_execution_rehearsal(
            authority, stage="test", correlations=CORRELATIONS, clusters=CLUSTERS
        )

        self.assertEqual(accounting_result["status"], "BLOCK")
        self.assertFalse(next(check for check in accounting_result["checks"] if check["name"] == "cash_reconciliation")["ok"])
        self.assertEqual(authority_result["status"], "BLOCK")
        self.assertEqual(authority_result["order_evidence"], [])

    def test_blocks_boolean_numeric_and_string_boolean_contracts(self) -> None:
        boolean_numeric = backtest_fixture()
        boolean_numeric["dividend_receivable"] = False
        string_status = backtest_fixture()
        string_status["ok"] = "true"

        numeric_result = run_portfolio_execution_rehearsal(
            boolean_numeric, stage="test", correlations=CORRELATIONS, clusters=CLUSTERS
        )
        status_result = run_portfolio_execution_rehearsal(
            string_status, stage="test", correlations=CORRELATIONS, clusters=CLUSTERS
        )

        self.assertEqual(numeric_result["status"], "BLOCK")
        self.assertFalse(next(check for check in numeric_result["checks"] if check["name"] == "source_numeric_contract")["ok"])
        self.assertEqual(status_result["status"], "BLOCK")
        self.assertFalse(next(check for check in status_result["checks"] if check["name"] == "source_backtest_passed")["ok"])


if __name__ == "__main__":
    unittest.main()
