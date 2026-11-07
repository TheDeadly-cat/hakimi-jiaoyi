import unittest
from datetime import date, timedelta

from exchange_terminal.services.causal_structure import project_causal_structure


def candles(highs, lows, closes=None):
    closes = closes or [(high + low) / 2 for high, low in zip(highs, lows)]
    return [{"date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(),
             "open": close, "high": high, "low": low, "close": close,
             "complete": True, "provisional": False}
            for i, (high, low, close) in enumerate(zip(highs, lows, closes))]


class CausalStructureTests(unittest.TestCase):
    def test_pivots_have_distinct_pivot_and_confirmation_and_explicit_equals(self):
        rows = candles([10, 14, 9, 16, 11, 15, 10, 15, 9],
                       [8, 7, 5, 7, 6, 8, 4, 8, 7])
        result = project_causal_structure(rows, left_window=1, right_window=1)
        highs = [event for event in result["pivots"] if event["kind"] == "HIGH"]
        lows = [event for event in result["pivots"] if event["kind"] == "LOW"]
        self.assertEqual([event["classification"] for event in highs],
                         ["INITIAL_HIGH", "HH", "LH", "EQUAL_HIGH"])
        self.assertEqual([event["classification"] for event in lows],
                         ["INITIAL_LOW", "HL", "LL"])
        self.assertEqual((highs[0]["pivot_index"], highs[0]["confirmed_at_index"]), (1, 2))
        self.assertEqual(highs[0]["pivot_date"], rows[1]["date"])
        self.assertEqual(highs[0]["confirmed_at_date"], rows[2]["date"])

    def test_equal_extremes_inside_window_are_not_pivots(self):
        rows = candles([10, 14, 14, 11, 9], [8, 7, 7, 8, 8])
        result = project_causal_structure(rows, left_window=1, right_window=1)
        self.assertFalse([event for event in result["pivots"] if event["kind"] == "HIGH"])
        self.assertFalse([event for event in result["pivots"] if event["kind"] == "LOW"])

    def test_breakout_uses_only_earlier_confirmed_resistance(self):
        rows = candles([10, 15, 11, 14, 17], [8, 9, 8, 9, 10],
                       [9, 14, 10, 14, 16])
        result = project_causal_structure(rows, left_window=1, right_window=1)
        self.assertEqual(len(result["breakouts"]), 1)
        event = result["breakouts"][0]
        self.assertEqual((event["kind"], event["index"], event["level_pivot_index"],
                          event["level_confirmed_at_index"]), ("BREAK_UP", 4, 1, 2))
        self.assertEqual(project_causal_structure(rows[:4], left_window=1, right_window=1)["breakouts"], [])

    def test_each_historical_prefix_is_unchanged_by_future_rows(self):
        rows = candles([10, 14, 9, 16, 11, 15, 10, 15, 9],
                       [8, 7, 5, 7, 6, 8, 4, 8, 7])
        full = project_causal_structure(rows, left_window=1, right_window=1)
        for end in range(len(rows)):
            prefix = project_causal_structure(rows[:end + 1], left_window=1, right_window=1)
            as_of = project_causal_structure(rows, left_window=1, right_window=1, as_of_index=end)
            self.assertEqual(prefix, as_of)
            self.assertEqual(prefix["pivots"],
                             [event for event in full["pivots"] if event["confirmed_at_index"] <= end])
            self.assertEqual(prefix["breakouts"],
                             [event for event in full["breakouts"] if event["index"] <= end])
            self.assertEqual(prefix["levels"], full["levels"][:end + 1])

    def test_unfinished_or_unmarked_rows_are_rejected(self):
        rows = candles([10, 11, 10], [8, 7, 8])
        for mutation in ({"complete": False}, {"complete": None}, {"provisional": True}):
            with self.subTest(mutation=mutation):
                sample = [row.copy() for row in rows]
                sample[-1].update(mutation)
                with self.assertRaises(ValueError):
                    project_causal_structure(sample, left_window=1, right_window=1)


if __name__ == "__main__":
    unittest.main()
