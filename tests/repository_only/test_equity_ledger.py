"""Hand-calculated stock accounting/timing checks; no numerical-engine import."""
import copy
from decimal import Decimal as D
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
module_spec = importlib.util.spec_from_file_location("equity_independent_ledger", ROOT / "scripts/reconcile_research_ledger.py")
ledger = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(ledger)


def example():
    snapshot_id, data_hash = "a" * 64, "b" * 64
    snapshot = {"schema_version": "us-equity-daily-snapshot-v1", "snapshot_id": snapshot_id, "data_hash": data_hash,
                "research_admission": {"allowed": True}, "bar_availability_lag_seconds": 60,
                "sessions": [{"date": "2024-11-27", "open_utc": "2024-11-27T14:30:00Z", "close_utc": "2024-11-27T21:00:00Z", "early_close": False},
                             {"date": "2024-11-29", "open_utc": "2024-11-29T14:30:00Z", "close_utc": "2024-11-29T18:00:00Z", "early_close": True},
                             {"date": "2024-12-02", "open_utc": "2024-12-02T14:30:00Z", "close_utc": "2024-12-02T21:00:00Z", "early_close": False}],
                "candles": [["2024-11-27T14:30:00Z", 100, 101, 99, 100, 1000],
                            ["2024-11-29T14:30:00Z", 100, 101, 99, 100, 1000],
                            ["2024-12-02T14:30:00Z", 100, 111, 99, 110, 1000]]}
    report = {"schema_version": "us-equity-research-report-v1", "report_hash": "c" * 64,
              "dataset": {"snapshot_id": snapshot_id, "data_hash": data_hash},
              "spec": {"snapshot_id": snapshot_id, "score_start_session": "2024-11-29", "score_end_session": "2024-12-02",
                       "initial_cash": 10000, "fee_rate": D("0.001")},
              "result": {
                  "fills": [{"fill_time": "2024-11-29T14:30:00Z", "signal_time": "2024-11-27T21:01:00Z", "fill_basis": "NEXT_BAR_OPEN",
                             "action": "BUY", "quantity": 10, "price": 100, "fee": 1, "pnl": 0,
                             "position_before": 0, "position_after": 10, "cash_after": 8999, "realized_pnl_after": 0}],
                  "equity_curve": [{"time": "2024-11-29T14:30:00Z", "equity": 10000},
                                   {"time": "2024-11-29T18:00:00Z", "equity": 9999, "cash": 8999, "position_qty": 10, "position_value": 1000},
                                   {"time": "2024-12-02T21:00:00Z", "equity": 10099, "cash": 8999, "position_qty": 10, "position_value": 1100}],
                  "return_series": [{"return": D("-0.0001")}, {"return": D(10099) / D(9999) - 1}],
                  "final_equity": 10099, "final_cash": 8999, "open_position_qty": 10, "total_fees": 1, "buy_fees": 1,
                  "sell_fees": 0, "realized_pnl": 0, "unrealized_pnl": 99, "unallocated_entry_fees": 1,
                  "total_return": D("0.0099"), "max_drawdown": D("0.0001"), "fill_count": 1, "round_trip_count": 0,
                  "exposure_ratio": (D(1000) / D(9999) + D(1100) / D(10099)) / 2}}
    return report, snapshot


class EquityIndependentLedgerTests(unittest.TestCase):
    def test_hand_calculated_early_close_weekend_ledger_rejects_wrong_mark_and_fee(self):
        original, snapshot = example()
        positive = ledger.reconcile(original, snapshot)
        self.assertEqual(positive["status"], "PASS")
        self.assertEqual(positive["score_bars"], 2)
        self.assertEqual(positive["reconciled_buy_fees"], "1")
        self.assertFalse(positive["project_numerical_engine_imported"])
        for scenario, field in [("close_time", "equity_mark_time"), ("fee", "fill_fee_model")]:
            report = copy.deepcopy(original)
            if scenario == "close_time":
                report["result"]["equity_curve"][1]["time"] = "2024-11-30T14:30:00Z"
            else:
                report["result"]["fills"][0]["fee"] = 2
            checked = ledger.reconcile(report, snapshot)
            with self.subTest(scenario=scenario):
                self.assertEqual(checked["status"], "FAIL")
                self.assertIn(field, [failure["field"] for failure in checked["failures"]])

    def test_signal_that_is_unavailable_at_open_is_rejected_independently(self):
        original, snapshot = example()
        self.assertEqual(ledger.reconcile(original, snapshot)["status"], "PASS")
        for clock in ["2024-11-29T14:30:00Z", "2024-11-29T18:01:00Z"]:
            report = copy.deepcopy(original)
            report["result"]["fills"][0]["signal_time"] = clock
            checked = ledger.reconcile(report, snapshot)
            with self.subTest(clock=clock):
                self.assertEqual(checked["status"], "FAIL")
                self.assertIn("signal_available_before_regular_open", [failure["field"] for failure in checked["failures"]])


if __name__ == "__main__":
    unittest.main()
