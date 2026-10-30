"""Read-only preflight agrees with original runner admission, using new QA data."""
from copy import deepcopy
import json
import unittest

from tests import test_terminal_research as fixtures
from exchange_terminal.services.backtest_engine import run_causal_long_only_backtest


class TerminalDataPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TerminalResearchTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service

    def prepare(self, count, params=None):
        self.fixture.market["rows"] = self.fixture.market["rows"][:count]
        self.fixture.market.pop("digest", None)
        self.fixture.market["digest"] = fixtures.digest(self.fixture.market)
        data = self.fixture.freeze()
        return {"input_id": data["id"], "strategy_id": "dual_ma",
                "strategy_params": params or {"fast_window": 20, "slow_window": 60}}

    def read(self, payload):
        return self.service.read("terminal_preflight", json.dumps(payload))

    def files(self):
        return {p.relative_to(self.fixture.root).as_posix(): p.read_bytes()
                for p in self.fixture.root.rglob("*") if p.is_file()}

    def test_default_boundary_includes_next_bar_execution_and_is_read_only(self):
        for count in (79, 80, 81, 82):
            with self.subTest(count=count):
                # Restore fixture rows so all four cases remain independent snapshots.
                rows = deepcopy(self.fixture.market["rows"])
                if count > len(rows):
                    from datetime import date, timedelta
                    rows = [{**rows[0], "date": (date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                             "ts_ms": 1577836800000 + i * 86400000} for i in range(count)]
                    self.fixture.market["rows"] = rows
                payload = self.prepare(count)
                before = self.files()
                result = self.read(payload)
                self.assertEqual(result["complete_rows"], count)
                self.assertEqual(result["required_rows"], 82)
                self.assertEqual(result["warmup_rows"], 80)
                self.assertEqual(result["evaluated_rows"], max(0, count - 80))
                self.assertEqual(result["missing_rows"], max(0, 82 - count))
                self.assertEqual(result["data_sufficient"], count >= 82)
                self.assertEqual(result["status"], "DATA_READY" if count >= 82 else "BLOCKED")
                self.assertEqual(result["excluded_incomplete_count"], 2)
                self.assertEqual(result["new_economic_runs"], 0)
                self.assertFalse(result["source_authenticated"])
                self.assertFalse(result["permissions"]["live_order_allowed"])
                self.assertEqual(self.files(), before)
        self.fixture.runner.assert_not_called()

    def test_long_window_uses_effective_parameters_and_saved_task_same_boundary(self):
        payload = self.prepare(91, {"fast_window": 20, "slow_window": 85})
        result = self.read(payload)
        self.assertEqual((result["warmup_rows"], result["required_rows"]), (90, 92))
        self.assertEqual(result["evaluated_rows"], 1)
        self.assertFalse(result["data_sufficient"])
        task = self.fixture.task(strategy_params=payload["strategy_params"])
        saved = self.read({"task_id": task["id"]})
        self.assertEqual(saved["task_id"], task["id"])
        self.assertEqual(saved["required_rows"], result["required_rows"])
        before = self.files()
        with self.assertRaisesRegex(ValueError, "insufficient_completed_history_for_warmup"):
            self.fixture.run_task(task)
        self.assertEqual(before, self.files())
        self.fixture.runner.assert_not_called()

    def test_81_rows_reject_before_start_record_and_82_matches_real_runner(self):
        payload = self.prepare(81)
        task = self.fixture.task(strategy_params=payload["strategy_params"])
        with self.assertRaisesRegex(ValueError, "insufficient_completed_history_for_warmup"):
            self.fixture.run_task(task)
        self.assertFalse((self.service.workspace / "terminal-runs").exists())
        self.fixture.runner.assert_not_called()
        from datetime import date, timedelta
        rows = [{"date": (date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                 "ts_ms": 1577836800000 + i * 86400000, "open": 100, "high": 102,
                 "low": 99, "close": 101, "volume": 100, "complete": True, "provisional": False}
                for i in range(82)]
        for count in (79, 80, 81, 82):
            result = run_causal_long_only_backtest(rows=rows[:count], symbol="BTC-USDT", source="qa-fixture",
                startup_candles=80, signal_fn=lambda *args: {"action": "HOLD", "reason": "QA only"},
                position_pct=25, take_profit_pct=0, stop_loss_pct=8, fee_rate=.0005,
                slippage_bps=2, leverage=1, market="crypto")
            self.assertEqual(result["ok"], count >= 82, result)
            if result["ok"]:
                self.assertEqual(result["evaluation_window"]["evaluated_rows"], 2)
                self.assertEqual(result["evaluation_window"]["start"], rows[80]["date"])

    def test_invalid_parameters_and_blocked_strategy_are_not_ready(self):
        payload = self.prepare(100)
        with self.assertRaisesRegex(ValueError, "fast_window"):
            self.read({**payload, "strategy_params": {"fast_window": 60, "slow_window": 20}})
        result = self.read({**payload, "strategy_id": "trend_pullback", "strategy_params": {}})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("terminal_strategy_new_research_blocked", result["blockers"])

    def test_core_direct_run_is_bound_to_acknowledged_saved_version(self):
        from unittest.mock import Mock
        self.fixture.core.read = Mock(return_value={"id": "core-handle", "task_id": "stored-hash"})
        self.fixture.core.mutate = Mock(return_value={"id": "saved-result"})
        with self.assertRaisesRegex(ValueError, "version_changed"):
            self.service.mutate("run_task", {"task_id": "core-handle", "expected_task_id": "old-hash"})
        self.fixture.core.mutate.assert_not_called()
        self.assertEqual(self.service.mutate("run_task", {"task_id": "core-handle", "expected_task_id": "stored-hash"}),
                         {"id": "saved-result"})
        self.fixture.core.mutate.assert_called_once_with("run_task", {"task_id": "core-handle"})


if __name__ == "__main__":
    unittest.main()
