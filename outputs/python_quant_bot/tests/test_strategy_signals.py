from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
import math
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_signals import (
    build_strategy_signal_fn,
    new_research_strategy_ids,
    rolling_bar_strategy_signal,
    rolling_strategy_signal,
    strategy_signal_input,
    strategy_signal_fingerprint,
    strategy_validation_capability,
    validated_strategy_ids,
)
from exchange_terminal.services.backtest_engine import causal_prefix_invariance_check


def volume_trend_bars(count: int = 130, *, breakout_volume: float = 3_000.0) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for index in range(count - 1):
        close = 100.0 + index * 0.05
        rows.append({
            "open": close - 0.2,
            "high": close + 0.6,
            "low": close - 1.4,
            "close": close,
            "volume": 1_000.0,
        })
    prior_high = max(row["high"] for row in rows[-40:])
    close = prior_high + 1.0
    rows.append({
        "open": close - 0.8,
        "high": close + 0.8,
        "low": close - 1.2,
        "close": close,
        "volume": breakout_volume,
    })
    return rows


def trend_pullback_bars(*, downtrend: bool = False) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    direction = -1.0 if downtrend else 1.0
    for index in range(118):
        close = 100.0 + direction * index * 0.1
        rows.append({
            "open": close - direction * 0.1,
            "high": close + 0.45,
            "low": close - 0.65,
            "close": close,
            "volume": 1_000.0,
        })
    if downtrend:
        rows.append({"open": 88.4, "high": 88.8, "low": 87.8, "close": 88.1, "volume": 1_000.0})
        rows.append({"open": 88.0, "high": 88.5, "low": 87.7, "close": 88.3, "volume": 1_000.0})
    else:
        rows.append({"open": 111.1, "high": 111.4, "low": 110.45, "close": 110.9, "volume": 850.0})
        rows.append({"open": 110.9, "high": 111.8, "low": 110.7, "close": 111.5, "volume": 1_050.0})
    return rows


def squeeze_breakout_bars(*, expansion_volume: float = 2_500.0) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for index in range(100):
        close = 100.0 + index * 0.08
        rows.append({
            "open": close - 0.1,
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "volume": 1_500.0,
        })
    for index in range(29):
        close = 108.0 + index * 0.02
        rows.append({
            "open": close - 0.05,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": 500.0,
        })
    prior_high = max(row["high"] for row in rows[-20:])
    close = prior_high + 0.35
    rows.append({
        "open": prior_high + 0.05,
        "high": close + 0.2,
        "low": prior_high - 0.4,
        "close": close,
        "volume": expansion_volume,
    })
    return rows


def causal_trend_pullback_rows(count: int = 180) -> list[dict[str, float | int | str | bool]]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, float | int | str | bool]] = []
    for index in range(count):
        baseline = 100.0 + index * 0.08
        pullback = -1.2 if index % 23 in {20, 21} else 0.0
        close = baseline + pullback
        timestamp = start + timedelta(days=index)
        rows.append({
            "date": timestamp.strftime("%Y-%m-%d"),
            "ts_ms": int(timestamp.timestamp() * 1000),
            "open": close - 0.15,
            "high": close + 0.55,
            "low": close - 0.65,
            "close": close,
            "volume": 1_300.0 if index % 23 == 22 else 1_000.0,
            "complete": True,
        })
    return rows


class StrategySignalTests(unittest.TestCase):
    def test_bound_signal_callback_uses_the_frozen_parameter_set(self) -> None:
        closes = [100.0] * 30 + [105.0, 110.0]
        custom = build_strategy_signal_fn("dual_ma", {"fast_window": 2, "slow_window": 3})
        default = build_strategy_signal_fn("dual_ma", {"fast_window": 20, "slow_window": 60})

        custom_signal = custom(closes, closes[-1], False, 0.0, 0.0)
        default_signal = default(closes, closes[-1], False, 0.0, 0.0)

        self.assertEqual(custom_signal["action"], "BUY")
        self.assertEqual(default_signal["action"], "HOLD")

    def test_unknown_strategy_never_falls_back_to_momentum(self) -> None:
        closes = [100 + index for index in range(100)]

        signal = rolling_strategy_signal("typo_strategy", closes, closes[-1], False)

        self.assertEqual(signal["action"], "HOLD")
        self.assertEqual(signal["reason"], "unsupported_strategy")
        self.assertIn("Unknown strategy id", signal["validation_blocker"])

    def test_stateful_strategies_are_blocked_until_their_execution_models_exist(self) -> None:
        for strategy_id in ("grid", "martingale", "anti_martingale"):
            capability = strategy_validation_capability(strategy_id)
            signal = rolling_strategy_signal(strategy_id, [100.0] * 100, 100.0, False)
            self.assertFalse(capability["backtest_supported"])
            self.assertEqual(signal["reason"], "unvalidated_stateful_strategy")
            self.assertNotIn(strategy_id, validated_strategy_ids())

    def test_turtle_exit_uses_the_prior_channel_not_the_current_close(self) -> None:
        closes = [100.0 + index * 0.1 for index in range(90)] + [80.0]

        signal = rolling_strategy_signal("turtle", closes, closes[-1], True)

        self.assertEqual(signal["action"], "EXIT")
        self.assertEqual(signal["reason"], "turtle_exit_channel_break")

    def test_livermore_exit_uses_the_prior_defensive_window(self) -> None:
        closes = [100.0 + index * 0.08 for index in range(90)] + [75.0]

        signal = rolling_strategy_signal("livermore", closes, closes[-1], True)

        self.assertEqual(signal["action"], "EXIT")
        self.assertEqual(signal["reason"], "livermore_defensive_pivot_break")

    def test_macd_has_an_independent_signal_implementation(self) -> None:
        closes = [100.0] * 85 + [100.0 + index ** 2 * 0.2 for index in range(1, 16)]

        macd = rolling_strategy_signal("macd", closes, closes[-1], False)
        momentum = rolling_strategy_signal("momentum", closes, closes[-1], False)

        self.assertEqual(macd["action"], "BUY")
        self.assertEqual(macd["reason"], "macd_bullish_and_strengthening")
        self.assertEqual(momentum["action"], "BUY")
        self.assertNotEqual(macd["reason"], momentum["reason"])

    def test_signal_fingerprint_binds_parameters_and_engine_source(self) -> None:
        first = strategy_signal_fingerprint("dual_ma", {"fast_window": 20, "slow_window": 60})
        second = strategy_signal_fingerprint("dual_ma", {"fast_window": 21, "slow_window": 60})

        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, second)

    def test_volume_trend_requires_structured_bars_and_remains_research_only(self) -> None:
        capability = strategy_validation_capability("volume_trend")

        self.assertEqual(strategy_signal_input("volume_trend"), "BARS")
        self.assertTrue(capability["backtest_supported"])
        self.assertFalse(capability["paper_clock_supported"])
        self.assertIn("research-only", capability["paper_blocker"])

    def test_volume_trend_uses_prior_breakout_high_and_volume_confirmation(self) -> None:
        confirmed = rolling_bar_strategy_signal("volume_trend", volume_trend_bars(), 108.0, False)
        low_volume = rolling_bar_strategy_signal(
            "volume_trend",
            volume_trend_bars(breakout_volume=1_000.0),
            108.0,
            False,
        )

        self.assertEqual(confirmed["action"], "BUY")
        self.assertEqual(confirmed["reason"], "volume_trend_breakout")
        self.assertGreater(confirmed["evidence"]["close"], confirmed["evidence"]["prior_breakout_high"])
        self.assertTrue(confirmed["checks"]["volume_confirmed"])
        self.assertEqual(low_volume["action"], "HOLD")
        self.assertFalse(low_volume["checks"]["volume_confirmed"])

    def test_volume_trend_bound_callback_consumes_bar_history(self) -> None:
        signal = build_strategy_signal_fn("volume_trend", {"volume_ratio": 1.2})(
            volume_trend_bars(),
            108.0,
            False,
            0.0,
            0.0,
        )

        self.assertEqual(signal["action"], "BUY")

    def test_volume_trend_position_exits_on_structure_not_a_fast_ma_wobble(self) -> None:
        bars: list[dict[str, float]] = []
        for index in range(129):
            close = 100.0 + index * 0.1
            bars.append({
                "open": close - 0.2,
                "high": close + 0.6,
                "low": close - 1.4,
                "close": close,
                "volume": 1_000.0,
            })
        bars.append({"open": 111.2, "high": 112.0, "low": 110.8, "close": 111.0, "volume": 1_000.0})

        signal = rolling_bar_strategy_signal("volume_trend", bars, 111.0, True)

        self.assertLess(signal["evidence"]["close"], signal["evidence"]["fast_ma"])
        self.assertEqual(signal["action"], "HOLD")
        self.assertEqual(signal["reason"], "volume_trend_position_intact")

    def test_trend_pullback_is_bar_based_and_research_only(self) -> None:
        capability = strategy_validation_capability("trend_pullback")

        self.assertTrue(capability["backtest_supported"])
        self.assertFalse(capability["new_research_allowed"])
        self.assertFalse(capability["paper_clock_supported"])
        self.assertEqual(strategy_signal_input("trend_pullback"), "BARS")
        self.assertIn("historical evidence replay only", capability["paper_blocker"])
        self.assertIn("new strategy ID", capability["paper_blocker"])

    def test_falsified_strategy_ids_remain_replayable_but_cannot_start_new_research(self) -> None:
        historical = set(validated_strategy_ids())
        eligible = set(new_research_strategy_ids())

        self.assertTrue({"trend_pullback", "squeeze_breakout"} <= historical)
        self.assertFalse({"trend_pullback", "squeeze_breakout"} & eligible)

    def test_trend_pullback_enters_on_reclaim_inside_a_rising_regime(self) -> None:
        signal = rolling_bar_strategy_signal(
            "trend_pullback",
            trend_pullback_bars(),
            111.5,
            False,
        )

        self.assertEqual(signal["action"], "BUY")
        self.assertEqual(signal["reason"], "trend_pullback_reclaim")
        self.assertTrue(signal["checks"]["trend_aligned"])
        self.assertTrue(signal["checks"]["pullback_reclaimed"])

    def test_trend_pullback_rejects_the_same_shape_in_a_downtrend(self) -> None:
        signal = rolling_bar_strategy_signal(
            "trend_pullback",
            trend_pullback_bars(downtrend=True),
            88.3,
            False,
        )

        self.assertEqual(signal["action"], "HOLD")
        self.assertFalse(signal["checks"]["trend_aligned"])

    def test_trend_pullback_exits_after_confirmed_fast_ma_failure(self) -> None:
        bars = trend_pullback_bars()
        bars[-2] = {"open": 109.8, "high": 110.0, "low": 108.8, "close": 109.1, "volume": 1_000.0}
        bars[-1] = {"open": 109.0, "high": 109.2, "low": 107.9, "close": 108.2, "volume": 1_100.0}

        signal = rolling_bar_strategy_signal("trend_pullback", bars, 108.2, True, 111.0)

        self.assertEqual(signal["action"], "EXIT")
        self.assertTrue(
            signal["checks"]["fast_break_confirmed"]
            or signal["checks"]["structure_break"]
            or signal["checks"]["atr_stop"]
        )

    def test_bar_normalizer_rejects_nonfinite_values(self) -> None:
        bars = trend_pullback_bars()
        bars[-1]["volume"] = math.nan

        signal = rolling_bar_strategy_signal("trend_pullback", bars, 111.5, False)

        self.assertEqual(signal, {"action": "HOLD", "reason": "invalid_bar_history"})

    def test_trend_pullback_passes_full_bar_prefix_invariance(self) -> None:
        params = {
            "trend_window": 100,
            "fast_window": 20,
            "breakout_window": 20,
            "exit_window": 10,
            "volume_window": 20,
            "atr_window": 14,
        }

        audit = causal_prefix_invariance_check(
            rows=causal_trend_pullback_rows(),
            symbol="BTC-USDT",
            source="causal-test",
            signal_factory=lambda _rows: build_strategy_signal_fn("trend_pullback", params),
            position_pct=20.0,
            take_profit_pct=0.0,
            stop_loss_pct=8.0,
            startup_candles=105,
            fee_rate=0.0005,
            slippage_bps=2.0,
            market="crypto",
            timeframe="1D",
            signal_input="BARS",
        )

        self.assertEqual(audit["status"], "PASS", audit.get("issues"))
        self.assertEqual(audit["issues"], [])
        self.assertTrue(audit["checks"])

    def test_squeeze_breakout_is_bar_based_and_development_only(self) -> None:
        capability = strategy_validation_capability("squeeze_breakout")

        self.assertTrue(capability["backtest_supported"])
        self.assertFalse(capability["new_research_allowed"])
        self.assertFalse(capability["paper_clock_supported"])
        self.assertEqual(strategy_signal_input("squeeze_breakout"), "BARS")
        self.assertIn("historical evidence replay only", capability["paper_blocker"])
        self.assertIn("new strategy ID", capability["paper_blocker"])

    def test_squeeze_breakout_requires_contraction_and_confirmed_expansion(self) -> None:
        confirmed_bars = squeeze_breakout_bars()
        low_volume_bars = squeeze_breakout_bars(expansion_volume=500.0)

        confirmed = rolling_bar_strategy_signal(
            "squeeze_breakout",
            confirmed_bars,
            confirmed_bars[-1]["close"],
            False,
        )
        low_volume = rolling_bar_strategy_signal(
            "squeeze_breakout",
            low_volume_bars,
            low_volume_bars[-1]["close"],
            False,
        )

        self.assertEqual(confirmed["action"], "BUY", confirmed)
        self.assertEqual(confirmed["reason"], "squeeze_breakout_confirmed")
        self.assertTrue(confirmed["checks"]["atr_compressed"])
        self.assertTrue(confirmed["checks"]["volume_contracted"])
        self.assertTrue(confirmed["checks"]["range_expanded"])
        self.assertEqual(low_volume["action"], "HOLD")
        self.assertFalse(low_volume["checks"]["volume_expanded"])

    def test_squeeze_breakout_exits_on_atr_or_structure_failure(self) -> None:
        bars = squeeze_breakout_bars()
        bars[-1] = {
            "open": 106.0,
            "high": 106.2,
            "low": 103.5,
            "close": 104.0,
            "volume": 2_000.0,
        }

        signal = rolling_bar_strategy_signal(
            "squeeze_breakout",
            bars,
            104.0,
            True,
            111.0,
        )

        self.assertEqual(signal["action"], "EXIT")
        self.assertTrue(signal["checks"]["atr_stop"] or signal["checks"]["structure_break"])


if __name__ == "__main__":
    unittest.main()
