import copy
import unittest
from datetime import date, timedelta

from exchange_terminal.services.exit_comparison_math import compare_exit_rules


def candles(count=15):
    rows = []
    for index in range(count):
        rows.append({"date": (date(2026, 1, 1) + timedelta(days=index)).isoformat(),
                     "open": 100.0, "high": 102.0, "low": 98.0, "close": 100.0,
                     "complete": True, "provisional": False})
    rows[2]["low"] = 90.0  # Confirmed pivot low at index 3 with 1+1 window.
    return rows


def spec(rows, *, max_hold_bars=5, atr_mult=2.0):
    return {"split": {
        "TRAIN": {"start_date": rows[0]["date"], "end_date": rows[3]["date"]},
        "VALIDATION": {"start_date": rows[4]["date"], "end_date": rows[8]["date"]},
        "TEST": {"start_date": rows[9]["date"], "end_date": rows[-1]["date"]}},
        "fixed_stop_pct": 5.0, "atr_window": 2, "atr_mult": atr_mult,
        "structure_left_window": 1, "structure_right_window": 1,
        "emergency_stop_pct": 20.0, "max_hold_bars": max_hold_bars,
        "costs": {"fee_rate": 0.001, "slippage_bps": 50.0}}


def buy(row, *, price=100.1):
    return {"date": row["date"], "side": "BUY", "price": price,
            "quantity": 2.3456789012, "fee": 0.123456,
            "signal_date": "2026-01-04", "fill_basis": "NEXT_BAR_OPEN"}


class ExitComparisonMathTests(unittest.TestCase):
    def test_same_native_entry_gap_open_and_uniform_costs(self):
        rows = candles()
        rows[5].update(open=94.0, high=97.0, low=93.0, close=95.0)
        result = compare_exit_rules(rows, [buy(rows[4])], spec(rows))
        self.assertEqual(result["cohort_count"], 1)
        sample = result["samples"][0]
        self.assertEqual(sample["segment"], "VALIDATION")
        self.assertEqual(list(sample["outcomes"]),
                         ["fixed_pct", "atr_trailing", "confirmed_structure"])
        for outcome in sample["outcomes"].values():
            self.assertEqual(outcome["fees"]["entry"], 0.123456)
        fixed = sample["outcomes"]["fixed_pct"]
        self.assertEqual((fixed["status"], fixed["exit"]["fill_basis"]), ("EXITED", "GAP_OPEN"))
        self.assertEqual(fixed["exit"]["raw_price"], 94.0)
        self.assertAlmostEqual(fixed["exit"]["price"], 94.0 * 0.995)
        self.assertAlmostEqual(fixed["exit"]["fee"], fixed["exit"]["price"] * buy(rows[4])["quantity"] * 0.001)
        basis = 100.1 * buy(rows[4])["quantity"] + buy(rows[4])["fee"]
        expected = (fixed["exit"]["price"] * buy(rows[4])["quantity"] - fixed["exit"]["fee"] - basis) / basis * 100
        self.assertAlmostEqual(fixed["net_return_pct"], expected)
        summary = result["summaries"]["fixed_pct"]["VALIDATION"]
        self.assertEqual(summary["exited_count"], 1)
        self.assertAlmostEqual(summary["mean_net_return_pct_exited_only"], expected)
        self.assertAlmostEqual(summary["median_net_return_pct_exited_only"], expected)
        self.assertAlmostEqual(summary["worst_net_return_pct_exited_only"], expected)
        self.assertEqual(summary["loss_count_exited_only"], 1)
        self.assertEqual(summary["loss_rate_exited_only"], 1.0)
        self.assertAlmostEqual(summary["mean_total_fee_exited_only"], fixed["fees"]["total"])
        pair = result["segment_stats"]["VALIDATION"]["paired"]["fixed_pct_vs_atr_trailing"]
        self.assertEqual(pair["paired_exited_count"], 0)
        self.assertEqual(pair["excluded_censored_or_unavailable_count"], 1)
        self.assertIsNone(pair["right_minus_left_mean_net_return_pct_points"])
        self.assertEqual(len(result["exit_paths"]), 3)
        self.assertTrue(all(path["entry"] == sample["entry"] for path in result["exit_paths"]))
        self.assertIsNone(result["portfolio_equity_curve"])

    def test_atr_stop_uses_previous_close_not_same_bar_high(self):
        rows = candles()
        rows[4].update(open=100.0, high=150.0, low=96.0, close=100.0)
        rows[5].update(open=100.0, high=101.0, low=70.0, close=80.0)
        result = compare_exit_rules(rows, [buy(rows[4], price=100.0)], spec(rows, atr_mult=1.0))
        outcome = result["samples"][0]["outcomes"]["atr_trailing"]
        self.assertEqual(outcome["status"], "EXITED")
        self.assertEqual(outcome["exit"]["index"], 5)
        self.assertIsNone(outcome["threshold_trace"][0]["trigger"])
        self.assertEqual(outcome["threshold_trace"][0]["known_at_index"], 4)
        self.assertEqual(outcome["threshold_trace"][1]["known_at_index"], 4)
        self.assertLess(outcome["threshold_trace"][0]["threshold"], rows[4]["low"])
        self.assertLess(outcome["threshold_trace"][1]["threshold"], 100.0)

    def test_no_confirmed_structure_is_unavailable(self):
        rows = candles()
        rows[2]["low"] = 98.0
        result = compare_exit_rules(rows, [buy(rows[4])], spec(rows))
        structure = result["samples"][0]["outcomes"]["confirmed_structure"]
        self.assertEqual(structure["status"], "UNAVAILABLE")
        self.assertEqual(structure["reason"], "NO_CONFIRMED_SUPPORT_BEFORE_ENTRY")
        self.assertIsNone(structure["exit"])
        self.assertIsNone(structure["net_return_pct"])
        self.assertEqual(structure["threshold_trace"], [])
        self.assertEqual(result["summaries"]["confirmed_structure"]["VALIDATION"]["unavailable_count"], 1)

    def test_segment_end_censors_without_crossing_into_next_segment(self):
        rows = candles()
        rows[4].update(open=70.0, high=75.0, low=65.0, close=70.0)
        result = compare_exit_rules(rows, [buy(rows[3])], spec(rows, max_hold_bars=10))
        for outcome in result["samples"][0]["outcomes"].values():
            if outcome["status"] == "UNAVAILABLE":
                continue
            self.assertEqual(outcome["status"], "CENSORED")
            self.assertEqual(outcome["censor"], {"reason": "SEGMENT_END", "index": 3,
                                                  "date": rows[3]["date"]})
            self.assertLessEqual(max(point["index"] for point in outcome["threshold_trace"]), 3)
            self.assertIsNone(outcome["net_return_pct"])

    def test_hold_limit_censors_without_fake_exit_or_return(self):
        rows = candles()
        result = compare_exit_rules(rows, [buy(rows[4])], spec(rows, max_hold_bars=2))
        fixed = result["samples"][0]["outcomes"]["fixed_pct"]
        self.assertEqual(fixed["status"], "CENSORED")
        self.assertEqual(fixed["censor"]["reason"], "MAX_HOLD_BARS")
        self.assertEqual(fixed["censor"]["index"], 5)
        self.assertIsNone(fixed["exit"])
        self.assertIsNone(fixed["net_return_pct"])

    def test_rejects_add_and_buy_outside_preregistered_split(self):
        rows = candles()
        added = buy(rows[4])
        added["side"] = "ADD"
        with self.assertRaisesRegex(ValueError, "buy_only"):
            compare_exit_rules(rows, [added], spec(rows))
        outside = copy.deepcopy(spec(rows))
        outside["split"]["VALIDATION"] = {"start_date": rows[5]["date"], "end_date": rows[8]["date"]}
        with self.assertRaisesRegex(ValueError, "entry_outside_preregistered_split"):
            compare_exit_rules(rows, [buy(rows[4])], outside)
        beyond_frozen_end = copy.deepcopy(spec(rows))
        beyond_frozen_end["split"]["TEST"]["end_date"] = "2026-02-01"
        with self.assertRaisesRegex(ValueError, "split_outside_frozen_rows"):
            compare_exit_rules(rows, [buy(rows[4])], beyond_frozen_end)

    def test_causal_results_of_earlier_split_do_not_change_with_future_rows(self):
        rows = candles()
        rows[8].update(open=100.0, high=101.0, low=80.0, close=90.0)
        baseline = compare_exit_rules(rows, [buy(rows[4])], spec(rows, max_hold_bars=3))
        later = copy.deepcopy(rows)
        for row in later[10:]:
            row.update(open=150.0, high=200.0, low=1.0, close=160.0)
        modified = compare_exit_rules(later, [buy(rows[4])], spec(later, max_hold_bars=3))
        self.assertEqual(baseline["samples"], modified["samples"])
        self.assertEqual(baseline["summaries"]["fixed_pct"]["VALIDATION"],
                         modified["summaries"]["fixed_pct"]["VALIDATION"])


if __name__ == "__main__":
    unittest.main()
