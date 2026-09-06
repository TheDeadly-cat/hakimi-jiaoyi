"""Controlled policy semantics; no indicator or execution-model replacement."""
import copy
import unittest
from unittest.mock import patch

import pandas as pd

from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig, RiskConfig, StrategyConfig, ExecutionConfig
from hakimi_research.documents import canonical_bytes
from hakimi_research.experiment import ExperimentRunner, ExperimentSpec, StrategySpec, verify_report
from hakimi_research.models import Action, Portfolio
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import build_strategy
from test_experiment_runner import snapshot_fixture, spec_fixture


def frame(closes):
    values = list(map(float, closes))
    return pd.DataFrame({"open": values, "high": values, "low": values,
                         "close": values, "volume": [100000.] * len(values)},
                        index=pd.date_range("2024-03-30T00:00:00Z", periods=len(values), freq="h"))


def result(data, name, params):
    config = BotConfig(strategy=StrategyConfig(name=name, params=params),
                       execution=ExecutionConfig(fee_rate=0.0008, slippage_pct=0.0005))
    return BacktestEngine(config, build_strategy(name, params), RiskManager(config.risk)).run(
        data, score_start=30).to_dict()


class DiagnosticSpecTests(unittest.TestCase):
    def test_old_spec_and_declaration_remain_unchanged(self):
        snapshot = snapshot_fixture()
        old = spec_fixture(snapshot)
        self.assertEqual(ExperimentSpec.from_document(old).document, old)
        declaration = StrategySpec("rsi", {"window": 14}).declaration()
        self.assertNotIn("oversold_entry_policy", declaration)
        self.assertNotIn("oversold_event_semantics", declaration)
        self.assertTrue(declaration["adding_to_position"])

    def test_v1_rejects_new_policy_and_v2_rejects_unknown_or_nonstring_policy(self):
        snapshot = snapshot_fixture()
        spec = spec_fixture(snapshot)
        spec["strategy"]["params"]["fixed_take_profit_policy"] = "DISABLED"
        with self.assertRaisesRegex(ValueError, "unknown_strategy_parameter"):
            ExperimentSpec.from_document(spec)
        spec["schema_version"] = "research-experiment-spec-v2"
        for bad in [None, 0, True, 1e100, "OFF", [], {}]:
            candidate = copy.deepcopy(spec)
            candidate["strategy"]["params"]["fixed_take_profit_policy"] = bad
            with self.assertRaisesRegex(ValueError, "policy_invalid"):
                ExperimentSpec.from_document(candidate)
        spec["strategy"]["params"]["oversold_entry_policy"] = "ONCE_PER_EVENT"
        with self.assertRaisesRegex(ValueError, "unknown_strategy_parameter"):
            ExperimentSpec.from_document(spec)

    def test_disabled_policy_rejects_numeric_sentinels_or_conflicting_percentage(self):
        spec = spec_fixture(snapshot_fixture())
        spec["schema_version"] = "research-experiment-spec-v2"
        spec["strategy"]["params"]["fixed_take_profit_policy"] = "DISABLED"
        for value in [0, 1e100, None, 0.08]:
            spec["strategy"]["params"]["take_profit_pct"] = value
            with self.assertRaises(ValueError):
                ExperimentSpec.from_document(spec)

    def test_v2_report_verifies_with_explicit_event_declaration(self):
        snapshot = snapshot_fixture()
        spec = spec_fixture(snapshot)
        spec["schema_version"] = "research-experiment-spec-v2"
        spec["strategy"] = {"name": "rsi", "params": {"window": 14, "oversold_entry_policy": "ONCE_PER_EVENT"}}
        report = ExperimentRunner().run(snapshot, ExperimentSpec.from_document(spec)).document
        self.assertEqual(verify_report(report), report)
        self.assertEqual(report["strategy_spec"]["oversold_event_semantics"]["risk_rejection"], "CONSUMES_EVENT_OPPORTUNITY")
        self.assertFalse(report["execution_permission"]["order_allowed"])

    def test_explicit_disabled_target_preserves_original_stop_and_entry(self):
        data = frame([100.] * 30 + [99., 100., 102.])
        params = {"fast_window": 2, "slow_window": 3, "position_pct": 0.25, "stop_loss_pct": 0.03}
        old = build_strategy("dual_ma", params).generate_signal(data, Portfolio(cash=10000))
        disabled = build_strategy("dual_ma", {**params, "fixed_take_profit_policy": "DISABLED"}).generate_signal(data, Portfolio(cash=10000))
        self.assertEqual(old.action, Action.BUY)
        self.assertEqual((old.action, old.reason, old.size_pct, old.stop_loss_pct),
                         (disabled.action, disabled.reason, disabled.size_pct, disabled.stop_loss_pct))
        self.assertEqual(old.take_profit_pct, 0.08)
        self.assertIsNone(disabled.take_profit_pct)


class RsiEventTests(unittest.TestCase):
    def test_first_observed_oversold_consumes_intent_before_risk_rejection(self):
        data = frame(range(140, 100, -1))
        strategy = build_strategy("rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        portfolio = Portfolio(cash=10000)
        first = strategy.generate_signal(data, portfolio)
        self.assertEqual(first.action, Action.BUY)
        risk = RiskManager(RiskConfig())
        risk.reset_day(20000)  # Current equity is below the daily-loss boundary.
        self.assertIsNone(risk.signal_to_order("BTC-USDT", first, portfolio, 100))
        self.assertEqual(strategy.generate_signal(data, portfolio).action, Action.HOLD)
        self.assertEqual(strategy.generate_signal(frame(range(140, 99, -1)), portfolio).action, Action.HOLD)

    def test_exact_threshold_ends_event_and_new_event_can_emit_one_intent(self):
        strategy = build_strategy("rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        data, portfolio = frame(range(140, 100, -1)), Portfolio(cash=10000)
        actions = []
        for value in (29., 20., 30., 29., 20., 70., 29.):
            with patch("hakimi_research.strategies.templates.rsi", return_value=pd.Series([value])):
                actions.append(strategy.generate_signal(data, portfolio).action)
        self.assertEqual(actions, [Action.BUY, Action.HOLD, Action.HOLD, Action.BUY, Action.HOLD, Action.HOLD, Action.BUY])

    def test_protective_exit_and_quarter_boundary_do_not_reset_event(self):
        data = frame([140. - index for index in range(95)])
        baseline = result(data, "rsi", {})
        once = result(data, "rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        self.assertGreater(sum(f["action"] == "BUY" for f in baseline["fills"]), 1)
        self.assertEqual(sum(f["action"] == "BUY" for f in once["fills"]), 1)
        self.assertTrue(any("stop" in order["reason"] for order in once["orders"]))
        self.assertEqual(sum(s["action"] == "BUY" for s in once["signals"]), 1)
        self.assertEqual(once["open_position_qty"], 0)
        self.assertTrue(any("2024-04-01" in signal["time"] for signal in once["signals"]))

    def test_baseline_rsi_repeats_and_explicit_every_bar_is_economically_equal(self):
        data = frame([140. - index for index in range(95)])
        default = result(data, "rsi", {})
        explicit = result(data, "rsi", {"oversold_entry_policy": "EVERY_OVERSOLD_BAR"})
        for field in ("signals", "orders", "fills", "round_trips", "equity_curve", "accounting", "return_series"):
            self.assertEqual(canonical_bytes(default[field]), canonical_bytes(explicit[field]), field)

    def test_opening_protection_cancels_new_event_intent_without_rearming_it(self):
        data = frame([100.] * 32 + [95.] * 3)
        def observed_rsi(close, window):
            value = 29. if len(close) in {30, 32} else 40. if len(close) == 31 else 20.
            return pd.Series([value])
        with patch("hakimi_research.strategies.templates.rsi", side_effect=observed_rsi):
            report = result(data, "rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        self.assertEqual(sum(s["action"] == "BUY" for s in report["signals"]), 2)
        self.assertEqual(sum(f["action"] == "BUY" for f in report["fills"]), 1)
        cancelled = [s for s in report["signals"] if s.get("execution_disposition") == "CANCELLED_OLD_POSITION_OPEN_PROTECTION"]
        self.assertEqual(len(cancelled), 1)
        self.assertEqual(cancelled[0]["action"], "BUY")
        self.assertEqual(report["open_position_qty"], 0)

    def test_future_prices_do_not_change_past_signals_fills_or_equity(self):
        data = frame([140. - i if i < 60 else 80. + (i - 60) for i in range(95)])
        changed = data.copy()
        changed.loc[changed.index[70]:, ["open", "high", "low", "close"]] *= 3
        first = result(data, "rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        second = result(changed, "rsi", {"oversold_entry_policy": "ONCE_PER_EVENT"})
        boundary = data.index[70]
        for field, time_key in (("signals", "time"), ("orders", "bar_time"), ("fills", "fill_time"), ("equity_curve", "time")):
            a = [item for item in first[field] if pd.Timestamp(item[time_key]) < boundary]
            b = [item for item in second[field] if pd.Timestamp(item[time_key]) < boundary]
            self.assertEqual(canonical_bytes(a), canonical_bytes(b), field)

    def test_engine_repeated_runs_start_with_fresh_unconsumed_event(self):
        data = frame(range(140, 45, -1))
        params = {"oversold_entry_policy": "ONCE_PER_EVENT"}
        config = BotConfig(strategy=StrategyConfig(name="rsi", params=params))
        strategy = build_strategy("rsi", params)
        engine = BacktestEngine(config, strategy, RiskManager(config.risk))
        first = engine.run(data, score_start=30).to_dict()
        second = engine.run(data, score_start=30).to_dict()
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertFalse(strategy._oversold_event_consumed)


if __name__ == "__main__":
    unittest.main()
