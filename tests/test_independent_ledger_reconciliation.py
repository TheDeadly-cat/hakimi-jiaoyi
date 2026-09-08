"""Arithmetic verifier checks use hand-authored numbers, no research engine."""
import copy
from decimal import Decimal as D
import importlib.util
from pathlib import Path
import unittest

_source = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_research_ledger.py"
_spec = importlib.util.spec_from_file_location("independent_ledger", _source)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def example():
    snapshot_id, data_hash = "a" * 64, "b" * 64
    snapshot = {"snapshot_id": snapshot_id, "data_hash": data_hash,
                "candles": [[f"2024-01-01T0{hour}:00:00Z", 100, 101, 99, 100, 1000] for hour in range(3)]}
    report = {"report_hash": "c" * 64, "dataset": {"snapshot_id": snapshot_id, "data_hash": data_hash},
              "spec": {"snapshot_id": snapshot_id, "score_start": "2024-01-01T01:00:00Z",
                       "score_end": "2024-01-01T03:00:00Z", "initial_cash": 10000, "fee_rate": D("0.001")},
              "result": {
                  "fills": [
                      {"fill_time": "2024-01-01T01:00:00Z", "action": "BUY", "quantity": 10, "price": 100,
                       "fee": 1, "pnl": 0, "position_before": 0, "position_after": 10, "cash_after": 8999, "realized_pnl_after": 0},
                      {"fill_time": "2024-01-01T02:00:00Z", "action": "SELL", "quantity": 10, "price": 100,
                       "fee": 1, "pnl": -2, "position_before": 10, "position_after": 0, "cash_after": 9998, "realized_pnl_after": -2}],
                  "equity_curve": [{"equity": 10000},
                      {"time": "2024-01-01T02:00:00Z", "equity": 9999, "cash": 8999, "position_qty": 10, "position_value": 1000},
                      {"time": "2024-01-01T03:00:00Z", "equity": 9998, "cash": 9998, "position_qty": 0, "position_value": 0}],
                  "return_series": [{"return": D("-0.0001")}, {"return": D(9998) / D(9999) - 1}],
                  "final_equity": 9998, "final_cash": 9998, "open_position_qty": 0,
                  "total_fees": 2, "buy_fees": 1, "sell_fees": 1, "realized_pnl": -2, "unrealized_pnl": 0,
                  "unallocated_entry_fees": 0, "total_return": D("-0.0002"), "max_drawdown": D("0.0002"),
                  "fill_count": 2, "round_trip_count": 1, "exposure_ratio": D(1000) / D(9999) / 2}}
    return report, snapshot


class IndependentReconciliationTests(unittest.TestCase):
    def test_hand_calculated_same_price_double_fee_ledger(self):
        report, snapshot = example()
        checked = _module.reconcile(report, snapshot)
        self.assertEqual(checked["status"], "PASS")
        self.assertEqual(checked["reconciled_buy_fees"], "1")
        self.assertEqual(checked["reconciled_sell_fees"], "1")
        self.assertFalse(checked["project_numerical_engine_imported"])

    def test_corrupt_final_cash_fees_initial_equity_and_partial_counts_rejected(self):
        original, snapshot = example()
        for field in ("final_cash", "buy_fees", "sell_fees", "round_trip_count", "unrealized_pnl"):
            report = copy.deepcopy(original)
            report["result"][field] += 1
            with self.subTest(field=field):
                self.assertEqual(_module.reconcile(report, snapshot)["status"], "FAIL")
        report = copy.deepcopy(original)
        report["result"]["equity_curve"][0]["equity"] = 9999
        self.assertEqual(_module.reconcile(report, snapshot)["status"], "FAIL")

    def test_wrong_fee_on_fill_is_not_hidden_by_consistent_totals(self):
        report, snapshot = example()
        report["result"]["fills"][0]["fee"] = 2
        checked = _module.reconcile(report, snapshot)
        self.assertEqual(checked["status"], "FAIL")
        self.assertIn("fill_fee_model", [failure["field"] for failure in checked["failures"]])


if __name__ == "__main__":
    unittest.main()
