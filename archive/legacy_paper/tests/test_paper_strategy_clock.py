from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import paper_account as paper_account_module
from exchange_terminal.services.paper_account import PaperAccount, configure_paper_account_runtime
from exchange_terminal.services.paper_strategy_clock import paper_clock_transition


def daily_rows(count: int, *, incomplete_last: bool = True) -> list[dict[str, object]]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []
    for index in range(count):
        close = 100 + index
        stamp = start + timedelta(days=index)
        rows.append({
            "date": stamp.date().isoformat(),
            "ts_ms": int(stamp.timestamp() * 1000),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1_000 + index,
            "complete": not (incomplete_last and index == count - 1),
        })
    return rows


def persisted_fill_report(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    *,
    order_id: str,
    filled_qty: float | None = None,
    market_snapshot_id: str = "test-market-snapshot",
) -> dict[str, object]:
    risk_result = dict(args[6])
    risk_context = dict(risk_result.get("context") or {})
    price = float(args[3])
    requested_notional = float(args[4])
    requested_qty = float(kwargs.get("requested_qty") or 0.0)
    quantity = float(filled_qty if filled_qty is not None else requested_qty or requested_notional / price)
    return {
        "status": "FILLED",
        "lifecycle_state": "FILLED",
        "persistence_status": "PERSISTED",
        "symbol": str(args[0]).upper(),
        "side": str(args[1]).upper(),
        "order_type": str(args[2]).upper(),
        "mark_price": price,
        "limit_price": float(args[5]),
        "requested_notional": requested_notional,
        "requested_qty": requested_qty,
        "quantity_constrained": requested_qty > 0,
        "reduce_only": risk_context.get("reduce_only") is True,
        "avg_price": price,
        "filled_qty": quantity,
        "filled_notional": quantity * price,
        "fee": 0.0,
        "funding_estimate": 0.0,
        "funding_charged": 0.0,
        "slippage_pct": 0.0,
        "order_id": order_id,
        "risk_request_id": str(risk_result.get("request_id") or ""),
        "market_snapshot_id": market_snapshot_id,
        "signal_id": risk_context.get("signal_id"),
        "idempotency_key": risk_context.get("idempotency_key"),
        "idempotent_replay": False,
    }


class PaperStrategyClockTests(unittest.TestCase):
    def test_snapshot_is_detached_from_mutable_account_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=lambda *_args, **_kwargs: {"allowed": True},
                execute_paper_order=lambda *_args, **_kwargs: {},
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.orders.append({"order_id": "immutable-order", "meta": {"status": "FILLED"}})
            account.signals.append({"action": "BUY"})
            account.ai_analysis = {"evidence": ["source"]}

            snapshot = account.snapshot(100.0)
            snapshot["orders"][0]["meta"]["status"] = "CORRUPTED"
            snapshot["signals"][0]["action"] = "SELL"
            snapshot["ai_analysis"]["evidence"].append("mutated")

        self.assertEqual(account.orders[0]["meta"]["status"], "FILLED")
        self.assertEqual(account.signals[0]["action"], "BUY")
        self.assertEqual(account.ai_analysis["evidence"], ["source"])

    def test_manual_reduce_revalidates_caller_pretrade_against_execution_contract(self) -> None:
        risk_calls: list[tuple[object, ...]] = []
        execution_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def risk_check(*args: object, **_kwargs: object) -> dict[str, object]:
            risk_calls.append(args)
            return {
                "allowed": True,
                "symbol": args[0],
                "side": args[1],
                "mode": args[2],
                "notional": round(float(args[3]), 2),
                "context": dict(args[5]),
                "request_id": "authoritative-risk",
                "checked_at": 10,
            }

        def execute(*args: object, **kwargs: object) -> dict[str, object]:
            execution_calls.append((args, dict(kwargs)))
            return persisted_fill_report(
                args,
                dict(kwargs),
                order_id="manual-reduce-1",
                market_snapshot_id="snapshot-reduce-1",
            )

        supplied_pretrade: dict[str, object] = {
            "allowed": True,
            "symbol": "AAPL",
            "side": "SELL",
            "mode": "PAPER",
            "notional": 2_500.0,
            "context": {
                "position_side": "LONG",
                "reduce_only": False,
                "order_type": "MARKET",
                "idempotency_key": "manual-reduce-key",
            },
            "request_id": "caller-risk",
            "checked_at": 9,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=risk_check,
                execute_paper_order=execute,
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.symbol = "AAPL"
            account.cash = 800.0
            account.position_qty = 2.0
            account.entry_price = 100.0

            account.manual_order(
                "SELL",
                100.0,
                25.0,
                "MARKET",
                idempotency_key="manual-reduce-key",
                pretrade_result=supplied_pretrade,
            )

        self.assertEqual(len(risk_calls), 1)
        self.assertEqual(risk_calls[0][1], "SELL")
        self.assertEqual(float(risk_calls[0][3]), 50.0)
        self.assertTrue(dict(risk_calls[0][5])["reduce_only"])
        self.assertEqual(supplied_pretrade["request_id"], "authoritative-risk")
        self.assertEqual(supplied_pretrade["notional"], 50.0)
        self.assertEqual(len(execution_calls), 1)
        self.assertEqual(account.position_qty, 1.5)
        self.assertTrue(account.orders[-1]["reduce_only"])

    def test_authoritative_pretrade_cache_reuses_only_fresh_complete_contracts(self) -> None:
        risk_calls: list[tuple[object, ...]] = []

        def risk_check(*args: object, **_kwargs: object) -> dict[str, object]:
            risk_calls.append(args)
            return {
                "allowed": True,
                "symbol": args[0],
                "side": args[1],
                "mode": args[2],
                "notional": round(float(args[3]), 2),
                "requested_price": float(args[4]),
                "context": {**dict(args[5]), "risk_audit_status": "PASS"},
                "request_id": "fresh-risk",
                "checked_at": 100_000,
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=risk_check,
                execute_paper_order=lambda *_args, **_kwargs: {},
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.symbol = "AAPL"
            base = {
                "allowed": True,
                "symbol": "AAPL",
                "side": "BUY",
                "mode": "PAPER",
                "notional": 100.0,
                "requested_price": 100.0,
                "context": {
                    "position_side": "FLAT",
                    "reduce_only": False,
                    "order_type": "MARKET",
                    "limit_price": 0.0,
                    "idempotency_key": "pretrade-cache-key",
                    "risk_audit_status": "PASS",
                },
                "request_id": "cached-risk",
                "checked_at": 99_000,
            }
            with patch.object(paper_account_module, "now_ms", return_value=100_000):
                reused = account.authoritative_execution_risk_check(
                    base, "BUY", 100.0, 100.0, "MARKET", False, "pretrade-cache-key"
                )
                stale = {**base, "checked_at": 80_000}
                revalidated = account.authoritative_execution_risk_check(
                    stale, "BUY", 100.0, 100.0, "MARKET", False, "pretrade-cache-key"
                )

        self.assertIs(reused, base)
        self.assertEqual(len(risk_calls), 1)
        self.assertEqual(revalidated["request_id"], "fresh-risk")
        self.assertEqual(revalidated["revalidated_from_request_id"], "cached-risk")

    def test_directional_account_methods_never_cross_an_existing_position(self) -> None:
        risk_calls: list[tuple[object, ...]] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=lambda *args, **_kwargs: risk_calls.append(args) or {"allowed": True},
                execute_paper_order=lambda *_args, **_kwargs: self.fail("invalid cross-position method must not execute"),
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.position_qty = -1.0
            account.entry_price = 100.0
            account.open_long_manual(100.0, 25.0, "MARKET", 0.0, "invalid direct long")
            self.assertEqual(account.position_qty, -1.0)

            account.position_qty = 1.0
            account.open_short_manual(100.0, 25.0, "MARKET", 0.0, "invalid direct short")
            self.assertEqual(account.position_qty, 1.0)

            account.position_qty = 0.0
            account.close_long_manual(100.0, 100.0, "MARKET", 0.0, "invalid close long")
            account.close_short_manual(100.0, 100.0, "MARKET", 0.0, "invalid close short")

        self.assertEqual(risk_calls, [])
        self.assertEqual(account.orders, [])

    def test_emergency_stop_halts_and_cancels_conditions_when_flatten_is_blocked(self) -> None:
        events: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=events.append,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=lambda *_args, **_kwargs: {
                    "allowed": False,
                    "reason": "pending ledger settlement",
                    "context": {},
                },
                execute_paper_order=lambda *_args, **_kwargs: self.fail("blocked emergency flatten must not execute"),
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.symbol = "AAPL"
            account.cash = 900.0
            account.position_qty = 1.0
            account.entry_price = 100.0
            account.armed = True
            account.pipeline_run_id = "pipeline-emergency-1"
            account.pending_strategy_signal = {"signal_id": "signal-pending-1", "action": "SELL"}
            account.conditional_orders.append({
                "id": "condition-active-1",
                "symbol": "AAPL",
                "side": "SELL",
                "status": "WAITING",
            })

            result = account.emergency_stop(100.0, "test emergency")

        emergency = dict(result["emergency_stop"])
        self.assertFalse(account.armed)
        self.assertEqual(account.pipeline_run_id, "")
        self.assertEqual(account.pending_strategy_signal, {})
        self.assertEqual(account.strategy_clock_status, "EMERGENCY_HALTED")
        self.assertEqual(account.conditional_orders[0]["status"], "CANCELLED")
        self.assertFalse(emergency["flattened"])
        self.assertFalse(emergency["safe_state_reached"])
        self.assertEqual(emergency["status"], "HALTED_WITH_POSITION")
        self.assertEqual(emergency["pipeline_run_id"], "pipeline-emergency-1")
        self.assertEqual(emergency["cancelled_condition_ids"], ["condition-active-1"])
        self.assertTrue(any(event.get("type") == "emergency_stop" for event in events))

    def test_quote_risk_exit_uses_unified_reduce_only_execution_with_signal_lineage(self) -> None:
        risk_contexts: list[dict[str, object]] = []
        execution_risks: list[dict[str, object]] = []

        def risk_check(*args: object, **_kwargs: object) -> dict[str, object]:
            context = dict(args[5])
            risk_contexts.append(context)
            return {
                "allowed": True,
                "symbol": args[0],
                "side": args[1],
                "mode": args[2],
                "notional": round(float(args[3]), 2),
                "context": context,
                "request_id": "risk-exit-1",
                "checked_at": 10,
            }

        def execute(*args: object, **kwargs: object) -> dict[str, object]:
            risk_result = dict(args[6])
            execution_risks.append(risk_result)
            return persisted_fill_report(
                args,
                dict(kwargs),
                order_id="risk-exit-order-1",
                market_snapshot_id="snapshot-exit-1",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=risk_check,
                execute_paper_order=execute,
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.symbol = "AAPL"
            account.cash = 900.0
            account.position_qty = 1.0
            account.entry_price = 100.0
            account.stop_loss_price = 99.0
            account.armed = True
            account.pipeline_run_id = "pipeline-risk-exit-1"

            account.evaluate(98.0)

        self.assertEqual(account.position_qty, 0.0)
        self.assertEqual(len(risk_contexts), 1)
        self.assertTrue(risk_contexts[0]["reduce_only"])
        self.assertTrue(str(risk_contexts[0]["signal_id"]).startswith("signal-"))
        self.assertEqual(len(execution_risks), 1)
        self.assertEqual(account.orders[-1]["signal_id"], risk_contexts[0]["signal_id"])
        self.assertTrue(account.orders[-1]["reduce_only"])

    def test_arm_rejects_unvalidated_execution_profile(self) -> None:
        account = PaperAccount()

        with self.assertRaisesRegex(ValueError, "Automated paper profile rejected"):
            account.arm("AAPL", "dual_ma", 2.0, 10.0, 100.0, {
                "direction_mode": "SHORT_ONLY",
                "risk_source": "AI",
                "value_mode": "PRICE",
                "order_type": "MARKET",
                "margin_mode": "ISOLATED",
            })

        self.assertFalse(account.armed)

    def test_arm_rejects_nonflat_account_and_active_conditions(self) -> None:
        account = PaperAccount()
        account.position_qty = 1.0
        account.entry_price = 100.0
        account.conditional_orders.append({"id": "condition-1", "status": "WAITING"})

        with self.assertRaisesRegex(ValueError, "flat account|active conditional"):
            account.arm(
                "BTC-USDT",
                "dual_ma",
                1.0,
                10.0,
                100.0,
                {
                    "direction_mode": "LONG_ONLY",
                    "risk_source": "MANUAL",
                    "value_mode": "PCT",
                    "trailing_take_enabled": False,
                    "trailing_stop_enabled": False,
                    "reduce_only": False,
                    "order_type": "CURRENT",
                    "margin_mode": "CROSS",
                },
            )

        self.assertFalse(account.armed)
        self.assertEqual(account.position_qty, 1.0)

    def test_reset_rolls_back_in_memory_when_persistence_fails(self) -> None:
        fail_persist = {"value": False}

        def persist_state(_payload: dict[str, object], _reason: str) -> None:
            if fail_persist["value"]:
                raise RuntimeError("simulated reset persistence failure")

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=lambda *_args, **_kwargs: {"allowed": True},
                execute_paper_order=lambda *_args, **_kwargs: {},
                persist_state=persist_state,
            )
            account = PaperAccount()
            account.cash = 7_500.0
            account.realized_pnl = -250.0
            account.orders.append({"order_id": "historical-order"})
            account.persist("seed")
            fail_persist["value"] = True

            with self.assertRaisesRegex(RuntimeError, "reset persistence failure"):
                account.reset()

        self.assertEqual(account.cash, 7_500.0)
        self.assertEqual(account.realized_pnl, -250.0)
        self.assertEqual(account.orders, [{"order_id": "historical-order"}])

    def test_arm_persists_pipeline_binding_atomically(self) -> None:
        persisted: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=lambda *_args, **_kwargs: {"allowed": True},
                execute_paper_order=lambda *_args, **_kwargs: {},
                persist_state=lambda payload, _reason: persisted.append(dict(payload)),
            )
            account = PaperAccount()
            account.arm(
                "AAPL",
                "dual_ma",
                1.0,
                10.0,
                100.0,
                {
                    "direction_mode": "LONG_ONLY",
                    "risk_source": "MANUAL",
                    "value_mode": "PCT",
                    "trailing_take_enabled": False,
                    "trailing_stop_enabled": False,
                    "reduce_only": False,
                    "order_type": "CURRENT",
                    "margin_mode": "CROSS",
                },
                pipeline_run_id="pipeline-run-1",
            )

        self.assertTrue(account.armed)
        self.assertEqual(account.pipeline_run_id, "pipeline-run-1")
        self.assertTrue(persisted[-1]["armed"])
        self.assertEqual(persisted[-1]["pipeline_run_id"], "pipeline-run-1")
        stopped_run_id = account.stop()
        self.assertEqual(stopped_run_id, "pipeline-run-1")
        self.assertFalse(account.armed)
        self.assertEqual(account.pipeline_run_id, "")
        self.assertEqual(persisted[-1]["pipeline_run_id"], "")

    def test_automated_manual_risk_profile_ignores_ai_execution_levels(self) -> None:
        def risk_check(*args: object, **_kwargs: object) -> dict[str, object]:
            return {
                "allowed": True,
                "symbol": args[0],
                "side": args[1],
                "mode": args[2],
                "notional": round(float(args[3]), 2),
                "context": dict(args[5]),
                "request_id": "manual-risk-profile",
                "checked_at": 10,
            }

        def execute(*args: object, **kwargs: object) -> dict[str, object]:
            return persisted_fill_report(
                args,
                dict(kwargs),
                order_id="manual-risk-entry-1",
                filled_qty=1.0,
                market_snapshot_id="snapshot-manual-risk-1",
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {
                    "take_profit": 120.0,
                    "stop_loss": 80.0,
                    "profit_probability": 0.95,
                },
                evaluate_directional_strategy_signal=lambda *_args, **_kwargs: {"action": "HOLD"},
                risk_pretrade_check=risk_check,
                execute_paper_order=execute,
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.arm(
                "AAPL",
                "dual_ma",
                1.0,
                10.0,
                100.0,
                {
                    "direction_mode": "LONG_ONLY",
                    "risk_source": "MANUAL",
                    "value_mode": "PCT",
                    "take_profit_pct": 10.0,
                    "stop_loss_pct": 5.0,
                    "trailing_take_enabled": False,
                    "trailing_stop_enabled": False,
                    "reduce_only": False,
                    "order_type": "CURRENT",
                    "margin_mode": "CROSS",
                },
                pipeline_run_id="pipeline-manual-risk-1",
            )

            self.assertEqual(account.take_profit_price, 110.0)
            self.assertEqual(account.stop_loss_price, 95.0)
            account.open_long_manual(102.0, 10.0, "CURRENT", 0.0, "test entry", manual=False)

        self.assertEqual(account.take_profit_price, 112.2)
        self.assertEqual(account.stop_loss_price, 96.9)
        self.assertNotEqual(account.take_profit_price, account.ai_analysis["take_profit"])
        self.assertNotEqual(account.stop_loss_price, account.ai_analysis["stop_loss"])

    def setUp(self) -> None:
        self._original_now_ms = paper_account_module.now_ms

    def tearDown(self) -> None:
        paper_account_module.now_ms = self._original_now_ms

    def test_clock_marks_a_stale_pending_signal_expired(self) -> None:
        rows = daily_rows(65)
        result = paper_clock_transition(
            rows=rows,
            now_ms=2_000_000,
            last_poll_ms=1_000_000,
            last_seen_bar_ts=int(rows[-1]["ts_ms"]),
            last_signal_bar_ts=int(rows[-2]["ts_ms"]),
            pending_signal={"action": "BUY", "signal_bar_ts": rows[-2]["ts_ms"]},
            execution_ready=True,
        )

        self.assertTrue(result["pending_expired"])
        self.assertIsNone(result["execution_bar"])

    def test_clock_does_not_backfill_a_completed_bar_after_long_downtime(self) -> None:
        rows = daily_rows(5, incomplete_last=False)
        result = paper_clock_transition(
            rows=rows,
            now_ms=2_000_000,
            last_poll_ms=1_000_000,
            last_seen_bar_ts=int(rows[-2]["ts_ms"]),
            last_signal_bar_ts=int(rows[-2]["ts_ms"]),
            pending_signal={},
            execution_ready=True,
        )

        self.assertEqual(result["status"], "MISSED_COMPLETED_BAR")
        self.assertIsNone(result["signal_bar"])
        self.assertEqual(result["missed_signal_bar"]["ts_ms"], rows[-1]["ts_ms"])

    def test_clock_requires_explicit_bar_and_execution_booleans(self) -> None:
        rows = daily_rows(5)
        rows[-1]["complete"] = "unknown"
        result = paper_clock_transition(
            rows=rows,
            now_ms=1_001_000,
            last_poll_ms=1_000_000,
            last_seen_bar_ts=int(rows[-2]["ts_ms"]),
            last_signal_bar_ts=int(rows[-2]["ts_ms"]),
            pending_signal={"action": "BUY", "signal_bar_ts": rows[-2]["ts_ms"]},
            execution_ready="true",  # type: ignore[arg-type]
        )

        self.assertIsNone(result["execution_bar"])
        self.assertIsNone(result["signal_bar"])
        self.assertFalse(result["bars"][-1]["complete"])

    def test_completed_bar_signal_is_queued_and_executed_once_on_next_bar(self) -> None:
        clock = {"now": 1_000_000}
        executions: list[tuple[object, ...]] = []
        signal_calls: list[int] = []
        signal_bar_calls: list[int] = []
        risk_contexts: list[dict[str, object]] = []
        events: list[dict[str, object]] = []

        def now_ms() -> int:
            clock["now"] += 1_000
            return clock["now"]

        def signal(*_args: object, **kwargs: object) -> dict[str, object]:
            closes = list(kwargs.get("closes") or [])
            bars = list(kwargs.get("bars") or [])
            signal_calls.append(len(closes))
            signal_bar_calls.append(len(bars))
            return {"action": "BUY", "reason": "test_completed_bar", "confidence": 0.8}

        def execute(*args: object, **kwargs: object) -> dict[str, object]:
            executions.append(args)
            report = persisted_fill_report(
                args,
                dict(kwargs),
                order_id="clock-order-1",
                filled_qty=5.0,
                market_snapshot_id="clock-snapshot-1",
            )
            report["fee"] = 0.25
            return report

        def risk_check(*args: object, **_kwargs: object) -> dict[str, object]:
            context = dict(args[5])
            risk_contexts.append(context)
            return {
                "allowed": True,
                "context": context,
                "request_id": "clock-risk-1",
            }

        paper_account_module.now_ms = now_ms
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=events.append,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=signal,
                risk_pretrade_check=risk_check,
                execute_paper_order=execute,
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.arm("AAPL", "dual_ma", 1.0, 10.0, 100.0, {
                "direction_mode": "LONG_ONLY",
                "risk_source": "MANUAL",
                "value_mode": "PCT",
                "trailing_take_enabled": False,
                "trailing_stop_enabled": False,
                "reduce_only": False,
                "order_type": "CURRENT",
                "margin_mode": "CROSS",
            })

            rows = daily_rows(65)
            account.process_strategy_bars(rows, source="futu", price=164.0, execution_ready=True)
            self.assertEqual(account.strategy_clock_status, "SYNCED_NO_BACKFILL")
            self.assertFalse(account.pending_strategy_signal)
            self.assertEqual(len(executions), 0)

            rows[-1]["complete"] = True
            next_row = daily_rows(66)[-1]
            rows.append(next_row)
            account.process_strategy_bars(rows, source="futu", price=165.0, execution_ready=False)
            self.assertEqual(account.strategy_clock_status, "SIGNAL_PENDING_NEXT_BAR")
            self.assertEqual(account.pending_strategy_signal["action"], "BUY")
            pending_signal_id = str(account.pending_strategy_signal.get("signal_id") or "")
            self.assertTrue(pending_signal_id.startswith("signal-"))
            self.assertEqual(len(signal_calls), 1)
            self.assertEqual(signal_bar_calls, signal_calls)
            self.assertEqual(len(executions), 0)

            account.process_strategy_bars(rows, source="futu", price=165.25, execution_ready=True)
            account.process_strategy_bars(rows, source="futu", price=165.50, execution_ready=True)

        self.assertEqual(len(executions), 1)
        self.assertEqual(account.position_qty, 5.0)
        self.assertFalse(account.pending_strategy_signal)
        self.assertEqual(account.last_strategy_fill_bar_ts, int(next_row["ts_ms"]))
        self.assertEqual(account.orders[-1]["fill_basis"], "FIRST_OBSERVED_QUOTE_AFTER_NEW_BAR")
        self.assertEqual(account.orders[-1]["signal_id"], pending_signal_id)
        self.assertEqual(risk_contexts[-1]["signal_id"], pending_signal_id)
        signal_event = next(event for event in events if event.get("type") == "paper_strategy_completed_bar_signal")
        self.assertEqual(dict(signal_event["signal"])["signal_id"], pending_signal_id)

    def test_quote_ticks_do_not_call_the_strategy_signal_engine(self) -> None:
        calls = 0

        def signal(*_args: object, **_kwargs: object) -> dict[str, object]:
            nonlocal calls
            calls += 1
            return {"action": "BUY", "reason": "must_not_run"}

        with tempfile.TemporaryDirectory() as temp_dir:
            configure_paper_account_runtime(
                state_file=Path(temp_dir) / "paper.json",
                write_json=lambda *_args: None,
                append_ledger=lambda *_args: None,
                choose_strategy=lambda strategy_id: {"id": strategy_id, "name": strategy_id},
                trade_direction_from_mode=lambda _value: "LONG",
                analyze_strategy_context=lambda *_args, **_kwargs: {},
                evaluate_directional_strategy_signal=signal,
                risk_pretrade_check=lambda *_args, **_kwargs: {"allowed": True, "context": {}},
                execute_paper_order=lambda *_args, **_kwargs: {},
                persist_state=lambda *_args: None,
            )
            account = PaperAccount()
            account.armed = True
            account.evaluate(100.0)
            account.evaluate(101.0)

        self.assertEqual(calls, 0)
        self.assertEqual(len(account.signals), 0)


if __name__ == "__main__":
    unittest.main()
