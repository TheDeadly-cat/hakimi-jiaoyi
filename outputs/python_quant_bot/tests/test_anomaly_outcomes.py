from __future__ import annotations

import sys
import unittest
from pathlib import Path


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.services.anomaly_outcomes import anomaly_outcome_summary, evaluate_anomaly_outcome


def event(
    direction: str = "偏多突破",
    *,
    entry_price: float = 100.0,
    first_seen: int = 1_000_000,
    priority: str = "B",
    fallback: bool = False,
    quarantined: bool = False,
    market_type: str = "crypto",
) -> dict:
    return {
        "direction": direction,
        "entry_price": entry_price,
        "first_seen": first_seen,
        "range24h_pct": 4.0,
        "market_type": market_type,
        "watch_priority": {"level": priority},
        "data_quality": {"fallback": fallback, "quarantined": quarantined},
    }


class AnomalyOutcomeTests(unittest.TestCase):
    def test_old_event_without_entry_price_is_not_backfilled(self) -> None:
        result = evaluate_anomaly_outcome(event(entry_price=0), 105, 3_000_000)

        self.assertEqual(result["state"], "NO_BASELINE")
        self.assertFalse(result["counts_toward_stats"])

    def test_bad_data_is_excluded_from_statistics(self) -> None:
        result = evaluate_anomaly_outcome(event(priority="C", fallback=True, quarantined=True), 108, 3_000_000)

        self.assertEqual(result["state"], "EXCLUDED")
        self.assertFalse(result["counts_toward_stats"])

    def test_directionless_event_remains_watch_only(self) -> None:
        result = evaluate_anomaly_outcome(event(direction="多空争夺"), 102, 3_000_000)

        self.assertEqual(result["state"], "WATCH_ONLY")

    def test_event_waits_for_minimum_observation_window(self) -> None:
        result = evaluate_anomaly_outcome(event(), 103, 1_100_000)

        self.assertEqual(result["state"], "PENDING")

    def test_long_and_short_follow_through_are_confirmed(self) -> None:
        long_result = evaluate_anomaly_outcome(event(), 101, 3_000_000)
        short_result = evaluate_anomaly_outcome(event(direction="偏空下破"), 99, 3_000_000)

        self.assertEqual(long_result["state"], "CONFIRMED")
        self.assertEqual(short_result["state"], "CONFIRMED")
        self.assertGreater(long_result["directional_return_pct"], 0)
        self.assertGreater(short_result["directional_return_pct"], 0)

    def test_opposite_move_invalidates_direction(self) -> None:
        result = evaluate_anomaly_outcome(event(), 99, 3_000_000)

        self.assertEqual(result["state"], "INVALIDATED")
        self.assertLess(result["directional_return_pct"], 0)

    def test_stalled_signal_and_summary_are_not_called_win_rate(self) -> None:
        stalled = evaluate_anomaly_outcome(
            event(),
            100.1,
            2_000_000,
            min_horizon_ms=100,
            max_horizon_ms=500,
        )
        confirmed = {"outcome": {"state": "CONFIRMED"}}
        invalidated = {"outcome": {"state": "INVALIDATED"}}
        no_follow = {"outcome": stalled}
        summary = anomaly_outcome_summary([confirmed, confirmed, confirmed, invalidated, no_follow])

        self.assertEqual(stalled["state"], "NO_FOLLOW_THROUGH")
        self.assertTrue(summary["sample_sufficient"])
        self.assertEqual(summary["direction_confirmation_rate_pct"], 60.0)
        self.assertNotIn("胜率", summary["summary"])


if __name__ == "__main__":
    unittest.main()
