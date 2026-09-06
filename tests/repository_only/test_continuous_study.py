"""Calendar boundaries are descriptors, not an engine restart or new capital."""
import copy
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from hakimi_research.backtest import BacktestEngine
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig
from hakimi_research.documents import canonical_bytes, read_document
from hakimi_research.models import Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase
from hakimi_research.strategies import build_strategy

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("continuous_study_test", ROOT / "tools/run_continuous_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class CalendarSignals(StrategyBase):
    name = "continuous_calendar_fixture"
    version = "1"

    def generate_signal(self, data, portfolio):
        decision = self.get("decisions", {}).get(str(len(data)), "HOLD")
        if decision == "BUY":
            return Signal.buy("fixed intention", 0.15, stop_loss_pct=0.03, take_profit_pct=0.08)
        if decision == "HALF":
            return Signal.sell("fixed partial exit", 0.5)
        return Signal.hold("fixed hold")


NORMAL = (100, 101, 99, 100, 1000)


def run(rows, decisions, start="2024-03-31T22:00:00Z", fee=0, daily=1):
    config = BotConfig(market="crypto_spot", initial_cash=10000,
                       risk=RiskConfig(max_position_pct=1, max_single_loss_pct=.03,
                                       max_daily_loss_pct=daily, min_cash_pct=0, max_leverage=1),
                       execution=ExecutionConfig(fee_rate=fee, slippage_pct=0))
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"],
                         index=pd.date_range(start, periods=len(rows), freq="h"))
    result = BacktestEngine(config, CalendarSignals({"decisions": decisions}), RiskManager(config.risk)).run(frame, score_start=1).to_dict()
    report = {"result": result, "spec": {"score_start": frame.index[1].isoformat().replace("+00:00", "Z"),
              "score_end": result["equity_curve"][-1]["time"].replace(" ", "T").replace("+00:00", "Z")}}
    return report


class ContinuousHistoryTests(unittest.TestCase):
    def test_changed_plan_or_unbound_input_cannot_reuse_old_receipts(self):
        plan = read_document(ROOT / "docs/studies/continuous-plan-20260906.json")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = output / "plan.json"
            study.frozen_write(path, plan)
            freeze = {"plan_hash": study.digest(plan), "plan_file_sha256": study.sha(path), "results_existed_at_freeze": False}
            study.save(freeze, output, "plan_freeze")
            self.assertEqual(study.require_frozen_plan(path, output), plan)
            input_path = output / "snapshot.json"
            input_path.write_text("original input", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "single_bound_input_derivation"):
                study.require_bound_input(path, input_path, output)
            study.save({"plan_hash": study.digest(plan), "snapshot_file_sha256": study.sha(input_path)}, output, "input_derivation")
            input_path.write_text("modified input", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bound_input_file_changed"):
                study.require_bound_input(path, input_path, output)
            altered = copy.deepcopy(plan)
            altered["fee_rate"] *= 2
            path.write_bytes(canonical_bytes(altered))
            with self.assertRaisesRegex(ValueError, "prefrozen_plan_receipt"):
                study.require_frozen_plan(path, output)

    def test_quarter_carries_position_and_equity_without_forced_trade(self):
        report = run([NORMAL] * 4, {"1": "BUY"})
        result = report["result"]
        self.assertEqual(result["fill_count"], 1)
        self.assertEqual(result["open_position_qty"], 15)
        self.assertEqual([p["point"] for p in result["equity_curve"]].count("INITIAL"), 1)
        second = study.slice_result(report, "2024-04-01T00:00:00Z", report["spec"]["score_end"], "Q2")
        self.assertEqual(second["opening_position_qty"], 15)
        self.assertEqual(second["opening_cash"], 8500)
        self.assertEqual(second["fill_count"], 0)

    def test_last_quarter_pending_decision_executes_after_boundary(self):
        result = run([NORMAL] * 3, {"2": "BUY"})["result"]
        fill = result["fills"][0]
        self.assertEqual(fill["signal_time"], "2024-03-31 23:00:00+00:00")
        self.assertEqual(fill["fill_time"], "2024-04-01 00:00:00+00:00")
        self.assertEqual(fill["fill_basis"], "NEXT_BAR_OPEN")

    def test_carried_protection_cancels_quarter_pending_addition(self):
        result = run([NORMAL, NORMAL, (95, 96, 94, 95, 1000)], {"1": "BUY", "2": "BUY"})["result"]
        self.assertEqual([f["action"] for f in result["fills"]], ["BUY", "SELL"])
        self.assertEqual(result["fills"][1]["price"], 95)
        self.assertEqual(result["fills"][1]["quantity"], 15)
        self.assertEqual(result["final_equity"], 9925)
        self.assertEqual(result["signals"][1]["execution_disposition"], "CANCELLED_OLD_POSITION_OPEN_PROTECTION")

    def test_daily_loss_halt_crosses_hours_and_resets_at_actual_utc_midnight(self):
        result = run([NORMAL, NORMAL, (95, 96, 94, 95, 1000), NORMAL, NORMAL, NORMAL],
                     {str(n): "BUY" for n in range(1, 6)}, start="2024-03-31T19:00:00Z", daily=.005)["result"]
        self.assertEqual([f["action"] for f in result["fills"]], ["BUY", "SELL", "BUY"])
        self.assertEqual(result["fills"][2]["fill_time"], "2024-04-01 00:00:00+00:00")
        self.assertAlmostEqual(result["fills"][2]["quantity"], 9925 * .15 / 100)

    def test_partial_exit_fee_allocation_and_open_mark_survive_boundary(self):
        result = run([NORMAL, NORMAL, (100, 106, 99, 105, 1000)], {"1": "BUY", "2": "HALF"}, fee=.001)["result"]
        self.assertEqual(result["open_position_qty"], 7.5)
        self.assertEqual(result["round_trip_count"], 0)
        self.assertAlmostEqual(result["unallocated_entry_fees"], .75)
        self.assertAlmostEqual(result["realized_pnl"], -1.5)
        self.assertAlmostEqual(result["unrealized_pnl"], 36.75)
        self.assertAlmostEqual(result["final_equity"], 10035.25)
        self.assertAlmostEqual(result["final_equity"], 10000 + result["realized_pnl"] + result["unrealized_pnl"])

    def test_calendar_return_product_reconciles_and_slicing_is_read_only(self):
        report = run([NORMAL, NORMAL, (100, 106, 99, 105, 1000), (105, 107, 103, 106, 1000)], {"1": "BUY"}, fee=.001)
        before = canonical_bytes(report)
        for months in (1, 3):
            periods = study.calendar_slices(report, months)
            self.assertEqual(len(periods), 2)
            self.assertEqual(study.reconcile_period_returns(periods, report["result"])["status"], "PASS")
            changed = copy.deepcopy(periods)
            changed[1]["opening_equity"] = 10000
            with self.assertRaisesRegex(ValueError, "same_continuous_equity"):
                study.reconcile_period_returns(changed, report["result"])
        self.assertEqual(canonical_bytes(report), before)

    def test_drawdown_duration_includes_recovery_and_open_episode(self):
        points = [{"time": f"2024-01-01T0{i}:00:00Z", "equity": value} for i, value in enumerate([100, 90, 80, 100, 90])]
        row = study.drawdown_stats(points)
        self.assertAlmostEqual(row["max_drawdown"], .2)
        self.assertEqual(row["max_drawdown_duration_hours"], 3)
        self.assertEqual(row["terminal_underwater_hours"], 1)

    def test_join_accepts_equal_overlap_but_rejects_revision_gap_and_bad_hour(self):
        a = {"candles": [["2024-01-01T00:00:00Z", 100, 101, 99, 100, 1], ["2024-01-01T01:00:00Z", 100, 101, 99, 100, 1]]}
        b = {"candles": [a["candles"][-1], ["2024-01-01T02:00:00Z", 100, 101, 99, 100, 1]]}
        rows, overlaps = study.merge_parent_rows([a, b], "2024-01-01T00:00:00Z", "2024-01-01T03:00:00Z")
        self.assertEqual((len(rows), overlaps), (3, 1))
        changed = copy.deepcopy(b)
        changed["candles"][0][-1] = 2
        with self.assertRaisesRegex(ValueError, "overlap_values_differ"):
            study.merge_parent_rows([a, changed], "2024-01-01T00:00:00Z", "2024-01-01T03:00:00Z")
        with self.assertRaisesRegex(ValueError, "coverage_incomplete"):
            study.merge_parent_rows([a], "2024-01-01T00:00:00Z", "2024-01-01T03:00:00Z")

    def test_future_prices_do_not_change_past_dual_ma_or_rsi_decisions(self):
        frame = pd.DataFrame({"open": [100 + 8 * math.sin(i / 9) for i in range(150)]})
        frame["close"] = frame["open"]
        frame["high"], frame["low"], frame["volume"] = frame["open"] + 1, frame["open"] - 1, 1000
        frame.index = pd.date_range("2024-03-28", periods=len(frame), freq="h", tz="UTC")
        future = frame.copy(deep=True)
        future.loc[future.index[120]:, ["open", "high", "low", "close"]] *= 2
        plan = read_document(ROOT / "docs/studies/multiwindow-plan-20260905.json")
        for method in plan["methods"][-2:]:
            config = BotConfig(market="crypto_spot", risk=RiskConfig(**plan["risk"]),
                               execution=ExecutionConfig(fee_rate=plan["fee_rate"], slippage_pct=plan["slippage_pct"]))
            outputs = [BacktestEngine(config, build_strategy(method["name"], method["params"]), RiskManager(config.risk)).run(data, score_start=72).to_dict() for data in (frame, future)]
            cutoff = frame.index[120]
            for field, stamp in (("signals", "time"), ("fills", "fill_time"), ("orders", "bar_time")):
                # Signals at the preceding close may be annotated later by the
                # changed future opening protection; compare causal decisions,
                # not annotations reporting the subsequent execution event.
                values = []
                for output in outputs:
                    rows = [{k: v for k, v in row.items() if k not in {"execution_disposition", "cancelled_at_bar_time"}} for row in output[field] if pd.Timestamp(row[stamp]) < cutoff]
                    values.append(rows)
                self.assertEqual(values[0], values[1], (method["label"], field))


if __name__ == "__main__":
    unittest.main()
