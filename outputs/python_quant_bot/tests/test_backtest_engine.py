from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.backtest_engine import (
    EXECUTION_MODEL_VERSION,
    causal_prefix_invariance_check,
    prepare_backtest_dataset,
    run_causal_long_only_backtest,
)
from exchange_terminal.services.market_calendar import build_market_calendar_contract
from exchange_terminal.services.strategy_quality import backtest_acceptance_report, backtest_reproducibility


def market_rows(count: int = 400, price: float = 100.0) -> list[dict[str, object]]:
    calendar = build_market_calendar_contract(
        calendar_name="XNYS",
        start_date="2024-01-01",
        end_date="2030-12-31",
    )
    dates = list(calendar["expected_dates"][:count])
    if len(dates) != count:
        raise AssertionError("XNYS fixture does not cover the requested row count")
    rows: list[dict[str, object]] = []
    for index, session_date in enumerate(dates):
        timestamp = datetime.fromisoformat(session_date).replace(tzinfo=timezone.utc)
        close = price + index * 0.05
        rows.append({
            "date": session_date,
            "ts_ms": int(timestamp.timestamp() * 1000),
            "open": close - 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000 + index,
            "complete": True,
        })
    return rows


def crypto_market_rows(count: int = 400, price: float = 100.0) -> list[dict[str, object]]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    for index in range(count):
        timestamp = start + timedelta(days=index)
        close = price + index * 0.05
        rows.append({
            "date": timestamp.date().isoformat(),
            "ts_ms": int(timestamp.timestamp() * 1000),
            "open": close - 0.1,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000 + index,
            "complete": True,
        })
    return rows


class BacktestEngineTests(unittest.TestCase):
    def test_full_ohlcv_hash_detects_a_middle_row_change(self) -> None:
        original = market_rows()
        changed = deepcopy(original)
        changed[177]["close"] = float(changed[177]["close"]) + 2.0
        changed[177]["high"] = float(changed[177]["high"]) + 2.0

        first = prepare_backtest_dataset(original, symbol="AAPL", source="futu")
        second = prepare_backtest_dataset(changed, symbol="AAPL", source="futu")

        self.assertEqual(first["manifest"]["hash_scope"], "FULL_OHLCV")
        self.assertNotEqual(first["manifest"]["data_hash"], second["manifest"]["data_hash"])

    def test_dataset_gate_rejects_unsorted_duplicate_and_preview_history(self) -> None:
        rows = market_rows()
        rows[200], rows[201] = rows[201], rows[200]
        rows[250]["ts_ms"] = rows[249]["ts_ms"]

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="quick_preview_seed")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("timestamps_not_strictly_increasing", prepared["manifest"]["blockers"])
        self.assertIn("duplicate_timestamps:1", prepared["manifest"]["blockers"])
        self.assertIn("synthetic_or_preview_source", prepared["manifest"]["blockers"])

    def test_dataset_gate_rejects_large_stock_history_gap(self) -> None:
        rows = market_rows()
        for row in rows[200:]:
            shifted = datetime.fromtimestamp(int(row["ts_ms"]) / 1000, timezone.utc) + timedelta(days=20)
            row["ts_ms"] = int(shifted.timestamp() * 1000)
            row["date"] = shifted.date().isoformat()

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("temporal_gaps_exceed_policy:1", prepared["manifest"]["blockers"])
        self.assertGreater(prepared["manifest"]["maximum_gap_days"], 10)
        self.assertEqual(prepared["manifest"]["temporal_gap_count"], 1)

    def test_dataset_gate_rejects_a_missing_crypto_daily_bar(self) -> None:
        rows = crypto_market_rows()
        del rows[200]

        prepared = prepare_backtest_dataset(rows, symbol="BTC-USDT", source="okx", market="crypto")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("temporal_gaps_exceed_policy:1", prepared["manifest"]["blockers"])

    def test_dataset_gate_rejects_a_missing_official_stock_session(self) -> None:
        rows = market_rows()
        missing_date = str(rows[200]["date"])
        del rows[200]

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("market_calendar:calendar_sessions_missing:1", prepared["manifest"]["blockers"])
        self.assertEqual(prepared["manifest"]["market_calendar"]["missing_dates"], [missing_date])

    def test_portfolio_lifecycle_policy_defers_stock_session_gap_only_explicitly(self) -> None:
        rows = market_rows(180)
        rows.pop(100)

        prepared = prepare_backtest_dataset(
            rows,
            symbol="AAPL",
            source="futu",
            market="stock",
            daily_continuity_policy="DEFER_TO_PORTFOLIO_LIFECYCLE",
        )

        self.assertEqual(prepared["status"], "PASS")
        self.assertEqual(
            prepared["manifest"]["daily_continuity_policy"],
            "DEFER_TO_PORTFOLIO_LIFECYCLE",
        )
        self.assertIn(
            "daily_continuity_deferred_to_portfolio_lifecycle",
            prepared["manifest"]["warnings"],
        )
        self.assertEqual(prepared["manifest"]["market_calendar"]["status"], "NOT_APPLICABLE")

    def test_dataset_gate_rejects_historical_incomplete_rows_but_allows_a_trailing_suffix(self) -> None:
        historical = market_rows()
        historical[200]["complete"] = False
        blocked = prepare_backtest_dataset(historical, symbol="AAPL", source="futu", market="stock")

        trailing = market_rows()
        trailing[-2]["complete"] = False
        trailing[-1]["complete"] = "provisional"
        accepted = prepare_backtest_dataset(trailing, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("historical_incomplete_rows:1", blocked["manifest"]["blockers"])
        self.assertEqual(blocked["manifest"]["historical_incomplete_examples"], [200])
        self.assertEqual(accepted["status"], "PASS")
        self.assertEqual(accepted["manifest"]["historical_incomplete_count"], 0)
        self.assertEqual(accepted["manifest"]["trailing_incomplete_count"], 2)

    def test_dataset_gate_rejects_duplicate_trading_dates_with_different_timestamps(self) -> None:
        rows = market_rows()
        duplicate = deepcopy(rows[200])
        duplicate["ts_ms"] = int(duplicate["ts_ms"]) + 60_000
        rows.insert(201, duplicate)

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("duplicate_trading_dates:1", prepared["manifest"]["blockers"])

    def test_dataset_gate_rejects_same_daily_session_with_mixed_date_encodings(self) -> None:
        rows = market_rows()
        duplicate = deepcopy(rows[200])
        duplicate["date"] = f"{duplicate['date']}T09:31:00Z"
        duplicate["ts_ms"] = int(duplicate["ts_ms"]) + 60_000
        rows.insert(201, duplicate)

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("duplicate_trading_dates:1", prepared["manifest"]["blockers"])

    def test_dataset_gate_rejects_session_date_timestamp_mismatch(self) -> None:
        rows = market_rows()
        expected_timestamp_session_date = str(rows[0]["date"])
        for row in rows:
            shifted = datetime.fromisoformat(str(row["date"])) + timedelta(days=20)
            row["date"] = shifted.date().isoformat()

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("session_date_timestamp_mismatch:400", prepared["manifest"]["blockers"])
        self.assertEqual(prepared["manifest"]["session_date_timestamp_mismatch_count"], 400)
        self.assertEqual(
            prepared["manifest"]["session_date_timestamp_mismatch_examples"][0]["timestamp_session_date_utc"],
            expected_timestamp_session_date,
        )

    def test_dataset_gate_rejects_boolean_ohlcv_fields(self) -> None:
        for field in ("ts_ms", "open", "high", "low", "close", "volume"):
            with self.subTest(field=field):
                rows = market_rows(130)
                rows[0][field] = True

                prepared = prepare_backtest_dataset(
                    rows,
                    symbol="AAPL",
                    source="futu",
                    market="stock",
                    minimum_rows=120,
                )

                self.assertEqual(prepared["status"], "BLOCK")
                self.assertIn("invalid_ohlcv_rows:1", prepared["manifest"]["blockers"])

    def test_dataset_excludes_string_false_and_malformed_completion_flags(self) -> None:
        rows = market_rows()
        rows[-2]["complete"] = "false"
        rows[-1]["complete"] = "malformed"

        prepared = prepare_backtest_dataset(rows, symbol="AAPL", source="futu", market="stock")

        self.assertEqual(prepared["manifest"]["excluded_incomplete_count"], 2)
        self.assertEqual(prepared["manifest"]["row_count"], len(rows) - 2)
        self.assertNotIn(str(rows[-1]["date"]), {str(row["date"]) for row in prepared["rows"]})

    def test_dataset_gate_rejects_nonfinite_derived_dollar_volume(self) -> None:
        rows = market_rows(130)
        for row in rows:
            row.update({
                "open": 1e308,
                "high": 1e308,
                "low": 1e308,
                "close": 1e308,
                "volume": 1e308,
            })

        prepared = prepare_backtest_dataset(
            rows,
            symbol="AAPL",
            source="futu",
            market="stock",
            minimum_rows=120,
        )

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn("invalid_ohlcv_rows:130", prepared["manifest"]["blockers"])

    def test_signal_fills_on_next_open_and_is_deterministic(self) -> None:
        rows = market_rows()

        def signal(closes: list[float], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
            return {"action": "BUY", "reason": "test entry"} if len(closes) == 30 and not has_position else {"action": "HOLD", "reason": "wait"}

        args = {
            "rows": rows,
            "symbol": "AAPL",
            "source": "futu",
            "signal_fn": signal,
            "position_pct": 25,
            "take_profit_pct": 0,
            "stop_loss_pct": 0,
            "startup_candles": 30,
            "fee_rate": 0.001,
            "slippage_bps": 10,
            "market": "stock",
        }
        first = run_causal_long_only_backtest(**args)
        second = run_causal_long_only_backtest(**args)

        self.assertTrue(first["ok"])
        self.assertEqual(first, second)
        self.assertEqual(first["execution_model"], EXECUTION_MODEL_VERSION)
        self.assertEqual(first["trades"][0]["signal_date"], rows[29]["date"])
        self.assertEqual(first["trades"][0]["date"], rows[30]["date"])
        self.assertAlmostEqual(first["trades"][0]["price"], float(rows[30]["open"]) * 1.001, places=6)
        self.assertGreater(first["max_drawdown_pct"], 0.0)

    def test_causal_prefix_audit_passes_a_history_only_signal(self) -> None:
        def factory(_run_rows: list[dict[str, object]]):
            def signal(closes: list[float], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
                if len(closes) >= 30 and closes[-1] > closes[-20] and not has_position:
                    return {"action": "BUY", "reason": "past_only"}
                return {"action": "HOLD", "reason": "wait"}
            return signal

        report = causal_prefix_invariance_check(
            rows=market_rows(240),
            symbol="AAPL",
            source="futu",
            signal_factory=factory,
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            market="stock",
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["checkpoint_count"], 3)

    def test_causal_prefix_audit_blocks_a_future_bound_signal(self) -> None:
        def factory(run_rows: list[dict[str, object]]):
            context_closes = [float(row["close"]) for row in run_rows]

            def signal(closes: list[float], price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
                next_price = context_closes[len(closes)] if len(closes) < len(context_closes) else price
                if next_price > price and not has_position:
                    return {"action": "BUY", "reason": "future_leak"}
                return {"action": "HOLD", "reason": "wait"}
            return signal

        report = causal_prefix_invariance_check(
            rows=market_rows(240),
            symbol="AAPL",
            source="futu",
            signal_factory=factory,
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            market="stock",
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(issue.startswith("signal_context_mismatch") for issue in report["issues"]))

    def test_causal_prefix_audit_fails_closed_when_signal_factory_raises(self) -> None:
        def factory(_run_rows: list[dict[str, object]]):
            raise RuntimeError("factory failure")

        report = causal_prefix_invariance_check(
            rows=market_rows(240),
            symbol="AAPL",
            source="futu",
            signal_factory=factory,
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            market="stock",
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(report["issues"], ["full_backtest_not_runnable"])

    def test_causal_prefix_audit_fails_closed_when_factory_result_is_not_callable(self) -> None:
        report = causal_prefix_invariance_check(
            rows=market_rows(240),
            symbol="AAPL",
            source="futu",
            signal_factory=lambda _run_rows: {"action": "HOLD"},
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            market="stock",
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(report["issues"], ["full_backtest_not_runnable"])

    def test_structured_bar_signal_fills_on_the_next_open(self) -> None:
        rows = market_rows()

        def signal(bars: list[dict[str, object]], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
            self.assertIn("volume", bars[-1])
            if len(bars) == 30 and not has_position:
                return {"action": "BUY", "reason": "bar_entry"}
            return {"action": "HOLD", "reason": "wait"}

        report = run_causal_long_only_backtest(
            rows=rows,
            symbol="AAPL",
            source="futu",
            signal_fn=signal,
            position_pct=25,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            market="stock",
            signal_input="BARS",
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["execution_assumptions"]["signal_input"], "BARS")
        self.assertEqual(report["trades"][0]["signal_date"], rows[29]["date"])
        self.assertEqual(report["trades"][0]["date"], rows[30]["date"])

    def test_causal_prefix_audit_passes_a_bar_history_signal(self) -> None:
        def factory(_run_rows: list[dict[str, object]]):
            def signal(bars: list[dict[str, object]], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
                if len(bars) >= 30 and float(bars[-1]["volume"]) > float(bars[-2]["volume"]) and not has_position:
                    return {"action": "BUY", "reason": "past_bars_only"}
                return {"action": "HOLD", "reason": "wait"}
            return signal

        report = causal_prefix_invariance_check(
            rows=market_rows(240),
            symbol="AAPL",
            source="futu",
            signal_factory=factory,
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            market="stock",
            signal_input="BARS",
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["signal_input"], "BARS")

    def test_same_bar_stop_and_target_uses_conservative_stop(self) -> None:
        rows = market_rows()
        rows[30]["open"] = 101.4
        rows[30]["high"] = 120.0
        rows[30]["low"] = 80.0
        rows[30]["close"] = 101.5

        def signal(closes: list[float], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
            return {"action": "BUY", "reason": "test entry"} if len(closes) == 30 and not has_position else {"action": "HOLD", "reason": "wait"}

        report = run_causal_long_only_backtest(
            rows=rows,
            symbol="AAPL",
            source="futu",
            signal_fn=signal,
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=5,
            startup_candles=30,
            market="stock",
        )

        self.assertEqual(report["ambiguous_intrabar_count"], 1)
        self.assertEqual(report["trades"][1]["reason"], "固定止损")
        self.assertEqual(report["trades"][1]["fill_basis"], "INTRABAR_STOP")

    def test_evaluation_window_uses_prior_history_without_counting_warmup(self) -> None:
        rows = market_rows()

        def signal(closes: list[float], _price: float, has_position: bool, _entry: float, _scale: float) -> dict[str, str]:
            if len(closes) == 200 and not has_position:
                return {"action": "BUY", "reason": "context entry"}
            return {"action": "HOLD", "reason": "wait"}

        report = run_causal_long_only_backtest(
            rows=rows,
            symbol="AAPL",
            source="futu",
            signal_fn=signal,
            position_pct=25,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            market="stock",
            evaluation_start_index=200,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["evaluation_window"]["start_index"], 200)
        self.assertEqual(report["evaluation_window"]["evaluated_rows"], 200)
        self.assertEqual(report["equity_curve"][0]["date"], rows[200]["date"])
        self.assertEqual(report["trades"][0]["signal_date"], rows[199]["date"])
        self.assertEqual(report["trades"][0]["date"], rows[200]["date"])

    def test_acceptance_cannot_average_away_a_critical_block(self) -> None:
        rows = market_rows()
        reproducibility = backtest_reproducibility(
            symbol="AAPL",
            strategy_id="dual_ma",
            params={"fast": 20, "slow": 60},
            market_payload={"rows": rows, "source": "futu", "bar": "1D"},
        )
        candidates = [{"ok": True}] * 10

        report = backtest_acceptance_report(
            {"ok": True, "trade_count": 0, "max_drawdown_pct": 2},
            candidates,
            reproducibility,
        )

        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(next(row for row in report["checks"] if row["name"] == "has_trades")["status"], "BLOCK")

    def test_cash_backtest_rejects_unmodelled_leverage(self) -> None:
        report = run_causal_long_only_backtest(
            rows=market_rows(),
            symbol="AAPL",
            source="futu",
            signal_fn=lambda *_: {"action": "HOLD", "reason": "wait"},
            position_pct=25,
            take_profit_pct=5,
            stop_loss_pct=2,
            startup_candles=30,
            leverage=2,
            market="stock",
        )

        self.assertFalse(report["ok"])
        self.assertIn("仅支持 1 倍现金账户", report["error"])

    def test_cash_backtest_rejects_nonfinite_or_nonpositive_initial_cash(self) -> None:
        for initial_cash in (float("nan"), float("inf"), 0.0, -100.0):
            with self.subTest(initial_cash=initial_cash):
                report = run_causal_long_only_backtest(
                    rows=market_rows(),
                    symbol="AAPL",
                    source="futu",
                    signal_fn=lambda *_args: {"action": "HOLD", "reason": "wait"},
                    position_pct=25,
                    take_profit_pct=0,
                    stop_loss_pct=0,
                    startup_candles=30,
                    initial_cash=initial_cash,
                    market="stock",
                )

                self.assertFalse(report["ok"])
                self.assertIn("initial_cash", report["error"])

    def test_repeated_add_signals_cannot_exceed_the_total_position_budget(self) -> None:
        rows = market_rows(80, price=100.0)
        for row in rows:
            row.update({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0})

        def signal(_history, _price, has_position, _entry, _scale):
            return {"action": "ADD" if has_position else "BUY", "reason": "repeat"}

        report = run_causal_long_only_backtest(
            rows=rows,
            symbol="AAPL",
            source="futu",
            signal_fn=signal,
            position_pct=20,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            fee_rate=0,
            slippage_bps=0,
            market="stock",
        )

        gross_exposure = report["open_position"]["quantity"] * 100.0 / report["final_equity"]
        self.assertTrue(report["ok"])
        self.assertLessEqual(gross_exposure, 0.20 + 1e-9)
        self.assertEqual(report["order_event_count"], 1)

    def test_add_signal_cannot_open_a_position_from_cash(self) -> None:
        report = run_causal_long_only_backtest(
            rows=market_rows(80),
            symbol="AAPL",
            source="futu",
            signal_fn=lambda *_args: {"action": "ADD", "reason": "invalid flat add"},
            position_pct=20,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            market="stock",
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["order_event_count"], 0)
        self.assertEqual(report["open_position"]["quantity"], 0.0)

    def test_invalid_execution_parameter_ranges_fail_closed(self) -> None:
        invalid_settings = (
            {"position_pct": 0},
            {"position_pct": 101},
            {"fee_rate": -0.001},
            {"fee_rate": 0.021},
            {"slippage_bps": -1},
            {"startup_candles": 1},
        )
        defaults = {
            "position_pct": 20,
            "take_profit_pct": 0,
            "stop_loss_pct": 0,
            "startup_candles": 30,
            "fee_rate": 0.001,
            "slippage_bps": 2,
        }
        for override in invalid_settings:
            with self.subTest(override=override):
                report = run_causal_long_only_backtest(
                    rows=market_rows(80),
                    symbol="AAPL",
                    source="futu",
                    signal_fn=lambda *_args: {"action": "HOLD", "reason": "wait"},
                    market="stock",
                    **{**defaults, **override},
                )

                self.assertFalse(report["ok"])
                self.assertIn("numeric parameter contract", report["error"])
                self.assertTrue(report["research_only"])
                self.assertFalse(report["paper_authorized"])
                self.assertFalse(report["live_order_allowed"])

    def test_numeric_string_parameters_are_normalized_once(self) -> None:
        report = run_causal_long_only_backtest(
            rows=market_rows(80),
            symbol="AAPL",
            source="futu",
            signal_fn=lambda *_args: {"action": "HOLD", "reason": "wait"},
            position_pct="20",
            take_profit_pct="5",
            stop_loss_pct="2",
            startup_candles="30",
            fee_rate="0.001",
            slippage_bps="2",
            initial_cash="10000",
            market="stock",
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["initial_cash"], 10000.0)

    def test_invalid_or_raising_strategy_signal_fails_closed(self) -> None:
        def raising_signal(*_args):
            raise RuntimeError("broken")

        for signal_fn, marker in (
            (lambda *_args: {"action": "MAGIC", "reason": "bad"}, "action_invalid"),
            (raising_signal, "signal_exception"),
        ):
            with self.subTest(marker=marker):
                report = run_causal_long_only_backtest(
                    rows=market_rows(80),
                    symbol="AAPL",
                    source="futu",
                    signal_fn=signal_fn,
                    position_pct=20,
                    take_profit_pct=0,
                    stop_loss_pct=0,
                    startup_candles=30,
                    market="stock",
                )

                self.assertFalse(report["ok"])
                self.assertIn(marker, report["error"])
                self.assertFalse(report["paper_authorized"])

    def test_full_cash_target_has_no_hidden_two_percent_reserve(self) -> None:
        rows = market_rows(80, price=100.0)
        for row in rows:
            row.update({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0})
        report = run_causal_long_only_backtest(
            rows=rows,
            symbol="AAPL",
            source="futu",
            signal_fn=lambda history, *_args: {
                "action": "BUY" if len(history) == 30 else "HOLD",
                "reason": "full allocation",
            },
            position_pct=100,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            fee_rate=0,
            slippage_bps=0,
            initial_cash=10_000,
            market="stock",
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["final_cash"], 0.0)
        self.assertAlmostEqual(report["open_position"]["quantity"], 100.0, places=8)

    def test_intraday_sharpe_uses_timeframe_annualization(self) -> None:
        report = run_causal_long_only_backtest(
            rows=market_rows(80),
            symbol="AAPL",
            source="futu",
            signal_fn=lambda *_args: {"action": "HOLD", "reason": "wait"},
            position_pct=20,
            take_profit_pct=0,
            stop_loss_pct=0,
            startup_candles=30,
            market="stock",
            timeframe="1h",
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["execution_assumptions"]["periods_per_year"], 1638)


if __name__ == "__main__":
    unittest.main()
