from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.market_regime import (
    audit_market_regime_causality,
    classify_market_regime,
    summarize_market_regimes,
)


def make_bars(count: int, *, drift: float = 0.002, expanding: bool = False) -> list[dict[str, object]]:
    bars: list[dict[str, object]] = []
    close = 100.0
    start = date(2024, 1, 1)
    for index in range(count):
        previous = close
        shock = 0.0
        if expanding and index >= count - 20:
            shock = 0.035 if index % 2 == 0 else -0.028
        close = max(1.0, previous * (1.0 + drift + shock))
        open_price = previous
        high = max(open_price, close) * 1.01
        low = min(open_price, close) * 0.99
        bars.append({
            "date": (start + timedelta(days=index)).isoformat(),
            "ts_ms": index * 86_400_000,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1_000_000.0,
            "complete": True,
        })
    return bars


class MarketRegimeTests(unittest.TestCase):
    def test_uptrend_has_a_positive_long_only_budget(self) -> None:
        report = classify_market_regime(make_bars(160, drift=0.003))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["trend"], "UP")
        self.assertGreater(report["long_only_budget_multiplier"], 0.0)
        self.assertFalse(report["paper_authorized"])

    def test_downtrend_blocks_new_long_only_budget(self) -> None:
        report = classify_market_regime(make_bars(160, drift=-0.003))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["trend"], "DOWN")
        self.assertEqual(report["long_only_budget_multiplier"], 0.0)

    def test_recent_volatility_expansion_is_visible(self) -> None:
        report = classify_market_regime(make_bars(180, drift=0.001, expanding=True))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["volatility"], "EXPANDING")
        self.assertGreater(report["evidence"]["volatility_ratio"], 1.25)

    def test_classifier_blocks_insufficient_history(self) -> None:
        report = classify_market_regime(make_bars(80))

        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(report["blockers"])

    def test_future_rows_cannot_change_a_past_regime(self) -> None:
        bars = make_bars(180, drift=0.002)
        audit = audit_market_regime_causality(bars)

        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["input_unchanged"])
        self.assertTrue(all(item["passed"] for item in audit["checkpoints"]))

    def test_window_summary_is_research_only(self) -> None:
        summary = summarize_market_regimes(make_bars(180), start_index=130)

        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["observation_count"], 50)
        self.assertTrue(summary["dominant_regime"])
        self.assertFalse(summary["paper_authorized"])


if __name__ == "__main__":
    unittest.main()
