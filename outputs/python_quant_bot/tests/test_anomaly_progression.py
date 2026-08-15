from __future__ import annotations

import sys
import unittest
from pathlib import Path


PYTHON_QUANT_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_QUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_QUANT_ROOT))

from exchange_terminal.services.anomaly_progression import annotate_anomaly_progression, anomaly_progression_summary


def anomaly(
    symbol: str,
    score: float,
    change: float,
    *,
    priority: str = "B",
    severity: str = "HIGH",
    tags: list[str] | None = None,
    fallback: bool = False,
    quarantined: bool = False,
) -> dict:
    return {
        "symbol": symbol,
        "score": score,
        "raw_score": score,
        "change24h_pct": change,
        "severity": severity,
        "watch_priority": {"level": priority},
        "type_tags": tags or ["放量"],
        "data_quality": {"fallback": fallback, "quarantined": quarantined},
    }


class AnomalyProgressionTests(unittest.TestCase):
    def test_first_scan_creates_neutral_baseline(self) -> None:
        rows = annotate_anomaly_progression([anomaly("AAPL", 72, 2.1)])

        self.assertEqual(rows[0]["motion"]["state"], "BASELINE")
        self.assertFalse(rows[0]["motion"]["comparison_available"])
        self.assertFalse(anomaly_progression_summary(rows)["comparison_available"])

    def test_score_and_magnitude_expansion_are_marked_surging(self) -> None:
        previous = [anomaly("WDC", 70, -2.0, priority="B", severity="HIGH")]
        current = [anomaly("WDC", 86, -5.2, priority="A", severity="CRITICAL", tags=["急涨急跌", "放量"])]

        rows = annotate_anomaly_progression(current, previous)

        self.assertEqual(rows[0]["motion"]["state"], "SURGING")
        self.assertEqual(rows[0]["motion"]["score_delta"], 16.0)
        self.assertEqual(anomaly_progression_summary(rows)["strengthening"], 1)

    def test_shrinking_signal_is_marked_fading(self) -> None:
        previous = [anomaly("NVDA", 78, 4.0)]
        current = [anomaly("NVDA", 69, 1.8)]

        rows = annotate_anomaly_progression(current, previous)

        self.assertEqual(rows[0]["motion"]["state"], "FADING")
        self.assertLess(rows[0]["motion"]["magnitude_delta_pct"], 0)

    def test_bad_data_never_becomes_strengthening_signal(self) -> None:
        previous = [anomaly("TSM", 50, 1.0, priority="C")]
        current = [anomaly("TSM", 67, 36.0, priority="C", severity="REVIEW", fallback=True, quarantined=True)]

        rows = annotate_anomaly_progression(current, previous)

        self.assertEqual(rows[0]["motion"]["state"], "REVIEW")
        self.assertEqual(anomaly_progression_summary(rows)["review"], 1)


if __name__ == "__main__":
    unittest.main()
