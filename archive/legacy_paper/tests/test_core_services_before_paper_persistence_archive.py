from __future__ import annotations

from copy import deepcopy
import json
import math
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.audit_log import AuditLog
from exchange_terminal.services.backtest_engine import EXECUTION_MODEL_VERSION
from exchange_terminal.services.event_bus import EventBus
from exchange_terminal.services.event_lineage import build_signal_context
from exchange_terminal.services.event_replay import EventReplayService
from exchange_terminal.services.http_contract import MUTATION_PATHS, allowed_web_origin, payload_to_query, read_only_get_mutation_requested, trusted_refresh_get_allowed
from exchange_terminal.services.market_data_service import MarketDataService
from exchange_terminal.services.mutation_journal import MutationJournal
from exchange_terminal.services.paper_executor import PaperExecutor, simulated_execution_report
from exchange_terminal.services.paper_ledger import PaperLedger
from exchange_terminal.services.research_bridge import ResearchBridge
from exchange_terminal.services.risk_service import (
    RiskService,
    apply_runtime_pretrade_authorization,
    build_pretrade_check,
    build_risk_snapshot,
    build_runtime_risk_view,
)
from exchange_terminal.services.strategy_pipeline import StrategyPipeline
from exchange_terminal.services.strategy_data_admission import build_strategy_data_admission
from exchange_terminal.services.strategy_validation import chronological_folds, summarize_cost_sensitivity, summarize_walk_forward, temporal_data_split


def validated_paper_profile(**overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "direction_mode": "LONG_ONLY",
        "risk_source": "MANUAL",
        "risk_value_mode": "PCT",
        "trailing_take_enabled": False,
        "trailing_stop_enabled": False,
        "reduce_only": False,
        "leverage": 1.0,
        "order_type": "CURRENT",
        "margin_mode": "CROSS",
    }
    profile.update(overrides)
    return profile


TEST_STRATEGY_DATA_HASH = "d" * 64


def passing_strategy_data_admission(symbol: str, generated_at: int) -> dict[str, object]:
    first_ts = max(int(generated_at) - 2, 1)
    last_ts = max(int(generated_at) - 1, 1)
    rows = [
        {"date": "1970-01-01", "ts_ms": first_ts, "complete": True, "complete_attested": True},
        {"date": "1970-01-02", "ts_ms": last_ts, "complete": True, "complete_attested": True},
    ]
    return build_strategy_data_admission(
        market_payload={"symbol": symbol, "source": "okx_history_candles", "rows": rows},
        dataset_manifest={
            "symbol": symbol,
            "market": "crypto",
            "timeframe": "1D",
            "source": "okx_history_candles",
            "status": "PASS",
            "hash_scope": "FULL_OHLCV",
            "data_hash": TEST_STRATEGY_DATA_HASH,
            "row_count": 2,
            "first": "1970-01-01",
            "last": "1970-01-02",
            "first_ts_ms": first_ts,
            "last_ts_ms": last_ts,
            "blockers": [],
        },
        dataset_lineage_id=f"strategy-backtest:test-{generated_at}",
        market="crypto",
        generated_at=int(generated_at),
    )


def paper_risk_approval(
    request_id: str,
    *,
    symbol: str = "AAPL",
    side: str = "BUY",
    notional: float = 100.0,
    mark_price: float = 100.0,
    order_type: str = "MARKET",
    limit_price: float = 0.0,
    checked_at: int = 30,
    mode: str = "PAPER",
    idempotency_key: str = "",
    reduce_only: bool = False,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    risk_context: dict[str, object] = {
        "order_type": order_type,
        "limit_price": limit_price,
        "reduce_only": reduce_only,
        "idempotency_key": idempotency_key,
        "position_side": "LONG" if reduce_only and side == "SELL" else "SHORT" if reduce_only else "FLAT",
        "risk_audit_status": "PASS",
    }
    risk_context.update(dict(context or {}))
    return {
        "allowed": True,
        "paper_order_allowed": True,
        "live_order_allowed": False,
        "status": "PASS",
        "mode": mode,
        "request_id": request_id,
        "checked_at": checked_at,
        "symbol": symbol.upper(),
        "side": side.upper(),
        "notional": round(float(notional), 2),
        "requested_price": round(float(mark_price), 8),
        "context": risk_context,
    }


def paper_lifecycle_fill(
    order_id: str,
    side: str,
    quantity: float,
    price: float,
    created_at: int,
    *,
    reduce_only: bool = False,
    position_side_before: str | None = None,
) -> dict[str, object]:
    before = position_side_before or (
        "LONG" if reduce_only and side == "SELL" else
        "SHORT" if reduce_only and side == "BUY" else
        "FLAT"
    )
    return {
        "order_id": order_id,
        "account_id": "default",
        "risk_request_id": f"risk-{order_id}",
        "symbol": "AAPL",
        "side": side,
        "order_type": "MARKET",
        "mark_price": price,
        "limit_price": 0.0,
        "requested_notional": quantity * price,
        "requested_qty": quantity,
        "quantity_constrained": True,
        "state": "FILLED",
        "created_at": created_at,
        "updated_at": created_at,
        "reduce_only": reduce_only,
        "position_side_before": before,
        "transitions": [{"state": "FILLED", "time": created_at, "reason": "test fill"}],
        "execution_report": {
            "status": "FILLED",
            "avg_price": price,
            "filled_qty": quantity,
            "filled_notional": quantity * price,
            "fee": 0.0,
            "funding_estimate": 0.0,
            "funding_charged": 0.0,
        },
    }


class CoreServiceTests(unittest.TestCase):
    def test_runtime_risk_view_blocks_policy_pass_in_read_only_runtime(self) -> None:
        policy = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )

        result = build_runtime_risk_view(
            policy,
            runtime_read_only=True,
            paper={"armed": False, "pipeline_run_id": ""},
        )

        self.assertTrue(result["risk_policy_allows_paper"])
        self.assertFalse(result["runtime_mutations_allowed"])
        self.assertFalse(result["paper_order_allowed"])
        self.assertFalse(result["automated_paper_order_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertEqual(result["status"], "RUNTIME_READ_ONLY")
        self.assertEqual(result["pretrade"]["status"], "BLOCK")
        self.assertIn("runtime_read_only", result["authorization"]["paper_order_blockers"])

    def test_runtime_risk_view_does_not_expose_historical_authority_as_effective_in_read_only(self) -> None:
        policy = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        result = build_runtime_risk_view(
            policy,
            runtime_read_only=True,
            paper={"armed": True, "pipeline_run_id": "run-bound"},
            pipeline_run={"run_id": "run-bound", "paper_authorized": True},
        )

        self.assertTrue(result["binding_authorized"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["paper_order_allowed"])
        self.assertFalse(result["automated_paper_order_allowed"])
        self.assertEqual(result["status"], "RUNTIME_READ_ONLY")
        self.assertFalse(result["authorization"]["paper_authorized"])
        self.assertFalse(result["authorization"]["live_order_allowed"])

    def test_runtime_risk_view_requires_bound_authorized_run_for_automation(self) -> None:
        policy = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        mismatched = build_runtime_risk_view(
            policy,
            runtime_read_only=False,
            paper={"armed": True, "pipeline_run_id": "run-bound"},
            pipeline_run={"run_id": "run-latest", "paper_authorized": True},
        )
        ready = build_runtime_risk_view(
            policy,
            runtime_read_only=False,
            paper={"armed": True, "pipeline_run_id": "run-bound"},
            pipeline_run={"run_id": "run-bound", "paper_authorized": True},
        )

        self.assertTrue(mismatched["paper_order_allowed"])
        self.assertFalse(mismatched["automated_paper_order_allowed"])
        self.assertEqual(mismatched["status"], "STRATEGY_AUTHORIZATION_BLOCK")
        self.assertIn("paper_pipeline_run_mismatch", mismatched["authorization"]["automated_execution_blockers"])
        self.assertTrue(ready["paper_order_allowed"])
        self.assertTrue(ready["automated_paper_order_allowed"])
        self.assertEqual(ready["status"], "PAPER_STRATEGY_READY")

    def test_runtime_pretrade_authorization_preserves_policy_but_blocks_read_only(self) -> None:
        result = apply_runtime_pretrade_authorization(
            {
                "allowed": True,
                "paper_order_allowed": True,
                "live_order_allowed": False,
                "status": "PASS",
                "mode": "PAPER",
                "reason": "policy pass",
                "reject_reason": "",
                "checks": [],
            },
            runtime_read_only=True,
        )

        self.assertTrue(result["risk_policy_allowed"])
        self.assertFalse(result["allowed"])
        self.assertFalse(result["paper_order_allowed"])
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("read-only", result["reason"])
        self.assertIn("runtime_write_authority", {item["name"] for item in result["checks"]})

    def test_live_mode_is_always_blocked(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL",
                "equity": 100_000,
                "available_cash": 100_000,
                "drawdown_pct": 0,
                "max_drawdown_pct": 5,
                "position_value": 0,
                "leverage": 1,
                "position_side": "FLAT",
                "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        result = build_pretrade_check(risk, "AAPL", "BUY", "LIVE", 1_000)
        self.assertFalse(result["allowed"])
        self.assertFalse(result["live_order_allowed"])
        self.assertIn("实盘硬墙", result["reason"])

    def test_limit_orders_never_fake_fill_without_book(self) -> None:
        empty_book = lambda _symbol, _side: []
        limit = simulated_execution_report("BTC-USDT", "BUY", "LIMIT", 100, 1_000, 99, empty_book, lambda _symbol: 0)
        ioc = simulated_execution_report("BTC-USDT", "BUY", "IOC", 100, 1_000, 101, empty_book, lambda _symbol: 0)
        fok = simulated_execution_report("BTC-USDT", "BUY", "FOK", 100, 1_000, 101, empty_book, lambda _symbol: 0)
        self.assertEqual(limit["status"], "WAITING_LIMIT")
        self.assertEqual(ioc["status"], "IOC_CANCELLED")
        self.assertEqual(fok["status"], "REJECTED")
        self.assertEqual(limit["filled_notional"], 0)

    def test_post_only_rejects_marketable_price(self) -> None:
        result = simulated_execution_report("BTC-USDT", "BUY", "POST_ONLY", 100, 1_000, 101, lambda *_: [], lambda _symbol: 0)
        self.assertEqual(result["status"], "REJECTED")
        self.assertIn("立即成交", result["note"])

    def test_quantity_constrained_execution_never_overshoots_reduce_quantity(self) -> None:
        report = simulated_execution_report(
            "BTC-USDT",
            "SELL",
            "MARKET",
            100,
            100,
            book_reader=lambda _symbol, _side: [[90, 10]],
            funding_rate_reader=lambda _symbol: 0.01,
            requested_qty=1,
        )

        self.assertEqual(report["status"], "FILLED")
        self.assertEqual(report["filled_qty"], 1)
        self.assertEqual(report["filled_notional"], 90)
        self.assertAlmostEqual(report["fee"], 0.045)
        self.assertTrue(report["quantity_constrained"])
        self.assertEqual(report["funding_estimate"], 0)
        self.assertEqual(report["funding_charged"], 0)

    def test_quantity_rejection_preserves_requested_semantics(self) -> None:
        report = simulated_execution_report(
            "BTC-USDT",
            "BUY",
            "FOK",
            100,
            999,
            limit_price=100,
            book_reader=lambda _symbol, _side: [[100, 0.5]],
            funding_rate_reader=lambda _symbol: 0,
            requested_qty=1,
        )

        self.assertEqual(report["status"], "REJECTED")
        self.assertEqual(report["requested_qty"], 1)
        self.assertEqual(report["requested_notional"], 100)
        self.assertTrue(report["quantity_constrained"])

    def test_risk_and_executor_reject_boolean_numeric_inputs(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL",
                "equity": 10_000,
                "available_cash": 10_000,
                "drawdown_pct": 0,
                "max_drawdown_pct": 5,
                "position_value": 0,
                "leverage": 1,
                "position_side": "FLAT",
                "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )

        pretrade = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", True)
        execution = simulated_execution_report("AAPL", "BUY", "MARKET", 100, True)

        self.assertFalse(pretrade["allowed"])
        self.assertFalse(next(row for row in pretrade["checks"] if row["name"] == "notional_positive")["ok"])
        self.assertEqual(execution["status"], "REJECTED")
        self.assertEqual(execution["requested_notional"], 0)
        self.assertEqual(execution["filled_qty"], 0)

    def test_execution_rejects_non_finite_inputs_and_skips_invalid_book_levels(self) -> None:
        rejected = simulated_execution_report(
            "BTC-USDT",
            "BUY",
            "MARKET",
            math.nan,
            math.inf,
            requested_qty=math.nan,
        )
        filled = simulated_execution_report(
            "BTC-USDT-SWAP",
            "BUY",
            "MARKET",
            100,
            100,
            book_reader=lambda _symbol, _side: [[math.nan, 2], [100, math.inf], [100, 1]],
            funding_rate_reader=lambda _symbol: math.inf,
        )

        self.assertEqual(rejected["status"], "REJECTED")
        self.assertEqual(rejected["avg_price"], 0)
        self.assertEqual(rejected["requested_notional"], 0)
        self.assertEqual(filled["filled_qty"], 1)
        self.assertEqual(filled["filled_notional"], 100)
        self.assertEqual(filled["funding_rate"], 0)

    def test_execution_skips_boolean_book_price_and_size_levels(self) -> None:
        report = simulated_execution_report(
            "AAPL",
            "BUY",
            "MARKET",
            100,
            100,
            book_reader=lambda _symbol, _side: [[True, 100], [100, True], [100, 1]],
        )

        self.assertEqual(report["status"], "FILLED")
        self.assertEqual(report["filled_qty"], 1)
        self.assertEqual(report["filled_notional"], 100)
        self.assertEqual(report["levels_used"], 1)

    def test_spot_execution_does_not_query_swap_funding(self) -> None:
        calls = 0

        def funding_reader(_symbol: str) -> float:
            nonlocal calls
            calls += 1
            raise AssertionError("spot execution must not query swap funding")

        report = simulated_execution_report(
            "BTC-USDT",
            "BUY",
            "MARKET",
            100,
            1_000,
            book_reader=lambda _symbol, _side: [],
            funding_rate_reader=funding_reader,
        )

        self.assertEqual(report["status"], "FILLED")
        self.assertEqual(calls, 0)
        self.assertEqual(report["funding_rate"], 0)
        self.assertEqual(report["funding_estimate"], 0)

    def test_swap_funding_is_an_estimate_until_a_settlement_event_exists(self) -> None:
        report = simulated_execution_report(
            "BTC-USDT-SWAP",
            "BUY",
            "MARKET",
            100,
            1_000,
            book_reader=lambda _symbol, _side: [],
            funding_rate_reader=lambda _symbol: 0.01,
        )

        self.assertEqual(report["funding_rate"], 0.01)
        self.assertEqual(report["funding_estimate"], 10)
        self.assertEqual(report["funding_charged"], 0)

    def test_risk_service_is_audited_and_blocks_quarantined_entries(self) -> None:
        events: list[dict[str, object]] = []
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        service = RiskService(snapshot_provider=lambda _price: risk, now_ms=lambda: 10, audit_writer=events.append)
        result = service.evaluate(
            symbol="AAPL",
            side="BUY",
            mode="PAPER",
            notional=1_000,
            context={"data_quality": {"status": "REVIEW", "quarantined": True}, "source": "manual"},
        )
        self.assertFalse(result["allowed"])
        self.assertTrue(result["request_id"].startswith("risk-10-"))
        self.assertEqual(events[-1]["type"], "risk_pretrade_block")

    def test_caller_cannot_override_authoritative_leverage(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        result = build_pretrade_check(
            risk,
            "AAPL",
            "BUY",
            "PAPER",
            500_000,
            context={
                "position_side": "FLAT",
                "direction_mode": "LONG_ONLY",
                "leverage": 100,
                "order_type": "MARKET",
                "data_status": "READY",
                "data_realtime": True,
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["context"]["leverage"], 1)
        self.assertIn("leverage", {row["field"] for row in result["context"]["account_context_mismatches"]})
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "single_order_notional")["ok"])

    def test_caller_cannot_override_authoritative_direction_mode(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        result = build_pretrade_check(
            risk,
            "AAPL",
            "SELL",
            "PAPER",
            1_000,
            context={
                "position_side": "FLAT",
                "direction_mode": "SHORT_ONLY",
                "leverage": 1,
                "order_type": "MARKET",
                "data_status": "READY",
                "data_realtime": True,
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["context"]["direction_mode"], "LONG_ONLY")
        self.assertIn("direction_mode", {row["field"] for row in result["context"]["account_context_mismatches"]})
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "direction_mode")["ok"])

    def test_risk_service_rejects_non_object_context_without_raising(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 10,
            audit_writer=lambda _event: None,
            data_context_provider=lambda *_args: {
                "data_status": "READY",
                "data_realtime": True,
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
        )

        result = service.evaluate(
            symbol="AAPL", side="BUY", mode="PAPER", notional=100, price=100, context="bad",
        )

        self.assertFalse(result["allowed"])
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "execution_context_object")["ok"])

    def test_pretrade_rejects_non_object_risk_snapshot_without_raising(self) -> None:
        result = build_pretrade_check("bad", "AAPL", "BUY", "PAPER", 100)

        self.assertFalse(result["allowed"])
        self.assertFalse(next(row for row in result["checks"] if row["name"] == "risk_snapshot_object")["ok"])

    def test_risk_service_fails_closed_on_non_object_context_providers(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        market_invalid = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 10,
            audit_writer=lambda _event: None,
            data_context_provider=lambda *_args: None,
        ).evaluate(
            symbol="AAPL", side="BUY", mode="PAPER", notional=100, price=100,
            context={"order_type": "MARKET", "limit_price": 0, "reduce_only": False},
        )
        portfolio_invalid = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 10,
            audit_writer=lambda _event: None,
            data_context_provider=lambda *_args: {
                "data_status": "READY", "data_realtime": True,
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
            portfolio_context_provider=lambda *_args: [],
        ).evaluate(
            symbol="AAPL", side="BUY", mode="PAPER", notional=100, price=100,
            context={"order_type": "MARKET", "limit_price": 0, "reduce_only": False},
        )

        self.assertFalse(market_invalid["allowed"])
        self.assertEqual(market_invalid["context"]["data_status"], "OFFLINE")
        self.assertFalse(portfolio_invalid["allowed"])
        self.assertEqual(portfolio_invalid["context"]["portfolio_risk"]["status"], "BLOCK")

    def test_risk_service_blocks_invalid_account_state_and_audit_failure(self) -> None:
        invalid = build_risk_snapshot(
            {
                "symbol": "AAPL",
                "equity": "nan",
                "available_cash": "broken",
                "drawdown_pct": "broken",
                "max_drawdown_pct": 5,
                "position_value": "inf",
                "leverage": 1,
                "position_side": "FLAT",
                "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        self.assertFalse(invalid["paper_order_allowed"])
        self.assertIn("account_equity_positive", {check["name"] for check in invalid["checks"] if not check["ok"]})

        valid = build_risk_snapshot(
            {
                "symbol": "AAPL",
                "equity": 10_000,
                "available_cash": 5_000,
                "drawdown_pct": 0,
                "max_drawdown_pct": 5,
                "position_value": 5_000,
                "leverage": 1,
                "position_side": "LONG",
                "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        ready_data = lambda _symbol, _price, _context: {
            "data_status": "READY",
            "data_realtime": True,
            "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
        }

        def failing_audit(_event: dict[str, object]) -> None:
            raise OSError("audit unavailable")

        service = RiskService(
            snapshot_provider=lambda _price: valid,
            now_ms=lambda: 10,
            audit_writer=failing_audit,
            data_context_provider=ready_data,
        )
        entry = service.evaluate(
            symbol="AAPL",
            side="BUY",
            mode="PAPER",
            notional=1_000,
            price=100,
            context={"position_side": "FLAT", "direction_mode": "LONG_ONLY"},
        )
        reduction = service.evaluate(
            symbol="AAPL",
            side="SELL",
            mode="PAPER",
            notional=1_000,
            price=100,
            context={"position_side": "LONG", "direction_mode": "LONG_ONLY", "reduce_only": True},
        )

        self.assertFalse(entry["allowed"])
        self.assertEqual(entry["context"]["risk_audit_status"], "FAILED")
        self.assertTrue(reduction["allowed"])
        self.assertEqual(reduction["status"], "WATCH")

    def test_risk_service_returns_a_block_instead_of_raising_on_snapshot_failure(self) -> None:
        def failed_snapshot(_price: float) -> dict[str, object]:
            raise ValueError("corrupt account state")

        service = RiskService(
            snapshot_provider=failed_snapshot,
            now_ms=lambda: 10,
            data_context_provider=lambda _symbol, _price, _context: {
                "data_status": "READY",
                "data_realtime": True,
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
        )
        result = service.evaluate(
            symbol="AAPL",
            side="BUY",
            mode="PAPER",
            notional=1_000,
            price=100,
            context={"position_side": "FLAT", "direction_mode": "LONG_ONLY"},
        )

        self.assertFalse(result["allowed"])
        self.assertIn("risk_snapshot_error", result["context"])

    def test_market_data_gate_blocks_stale_entries_but_allows_reductions(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 5_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 5_000,
                "leverage": 1, "position_side": "LONG", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        stale_context = {
            "data_status": "STALE",
            "data_quality": {
                "status": "STALE",
                "realtime": False,
                "fallback": True,
                "quarantined": False,
                "can_increase_risk": False,
                "blocking_reasons": ["当前使用旧缓存"],
            },
        }

        entry = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", 1_000, stale_context)
        reduction = build_pretrade_check(risk, "AAPL", "SELL", "PAPER", 1_000, stale_context)

        self.assertFalse(entry["allowed"])
        self.assertIn("禁止增加模拟风险", entry["reason"])
        self.assertTrue(reduction["allowed"])

    def test_risk_rejects_string_boolean_authorization_fields(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        context = {
            "data_status": "READY",
            "data_realtime": "false",
            "data_fallback": False,
            "data_quarantined": False,
            "data_quality": {
                "status": "READY",
                "realtime": "false",
                "fallback": False,
                "quarantined": False,
                "can_increase_risk": "false",
            },
            "portfolio_risk_required": True,
            "portfolio_risk": {
                "status": "PASS",
                "portfolio_gate_passed": "false",
                "reject_reasons": [],
            },
        }

        result = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", 1_000, context)

        self.assertFalse(result["allowed"])
        failed = {row["name"] for row in result["checks"] if row["ok"] is not True}
        self.assertIn("market_data_boolean_contract", failed)
        self.assertIn("portfolio_risk_boolean_contract", failed)
        self.assertIn("market_data_quality", failed)
        self.assertIn("portfolio_risk_budget", failed)

    def test_risk_service_rejects_malformed_authoritative_boolean_fields(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 10,
            data_context_provider=lambda *_args: {
                "data_status": "READY",
                "data_realtime": "false",
                "data_fallback": False,
                "data_quarantined": False,
                "data_quality": {
                    "status": "READY",
                    "realtime": "false",
                    "fallback": False,
                    "quarantined": False,
                    "can_increase_risk": "false",
                },
            },
            portfolio_context_provider=lambda *_args: {
                "status": "PASS",
                "portfolio_gate_passed": "false",
                "reject_reasons": [],
            },
        )

        result = service.evaluate(symbol="AAPL", side="BUY", mode="PAPER", notional=1_000, price=100)

        self.assertFalse(result["allowed"])
        self.assertFalse(result["paper_order_allowed"])

    def test_oco_contract_requires_explicit_conditional_context(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 5_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 5_000,
                "leverage": 1, "position_side": "LONG", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        base_context = {
            "position_side": "LONG",
            "direction_mode": "LONG_ONLY",
            "reduce_only": True,
            "order_type": "OCO",
            "data_status": "READY",
            "data_quality": {
                "status": "READY",
                "realtime": True,
                "can_increase_risk": True,
            },
        }

        conditional = build_pretrade_check(
            risk,
            "AAPL",
            "SELL",
            "PAPER",
            1_000,
            {**base_context, "conditional_order": True},
        )
        ordinary = build_pretrade_check(risk, "AAPL", "SELL", "PAPER", 1_000, base_context)

        self.assertTrue(conditional["allowed"])
        self.assertFalse(ordinary["allowed"])
        ordinary_contract = next(check for check in ordinary["checks"] if check["name"] == "paper_order_contract")
        self.assertFalse(ordinary_contract["ok"])

    def test_pending_ledger_settlement_blocks_new_reduce_order(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 5_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 5_000,
                "leverage": 1, "position_side": "LONG", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        result = build_pretrade_check(
            risk,
            "AAPL",
            "SELL",
            "PAPER",
            5_000,
            {
                "position_side": "LONG",
                "direction_mode": "LONG_ONLY",
                "reduce_only": True,
                "order_type": "MARKET",
                "ledger_reconciliation_required": True,
                "ledger_pending_settlements": 1,
                "data_status": "READY",
                "data_quality": {
                    "status": "READY",
                    "realtime": True,
                    "can_increase_risk": True,
                },
            },
        )

        self.assertFalse(result["allowed"])
        ledger_check = next(check for check in result["checks"] if check["name"] == "paper_ledger_reconciled")
        self.assertFalse(ledger_check["ok"])
        self.assertIn("1", ledger_check["message"])

    def test_historical_simulation_uses_attested_frozen_data_contract(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        historical_context = {
            "data_status": "HISTORICAL_READY",
            "data_quality": {
                "status": "HISTORICAL_READY",
                "historical": True,
                "attested": True,
                "realtime": False,
                "fallback": False,
                "quarantined": False,
                "can_simulate": True,
                "can_increase_risk": False,
                "blocking_reasons": [],
            },
        }

        simulation = build_pretrade_check(risk, "AAPL", "BUY", "SIMULATION", 1_000, historical_context)
        paper = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", 1_000, historical_context)
        unattested = build_pretrade_check(
            risk,
            "AAPL",
            "BUY",
            "SIMULATION",
            1_000,
            {
                **historical_context,
                "data_quality": {**historical_context["data_quality"], "attested": False},
            },
        )

        self.assertTrue(simulation["allowed"])
        self.assertFalse(paper["allowed"])
        self.assertFalse(unattested["allowed"])
        self.assertIn("来源证明", unattested["reason"])

    def test_authoritative_market_context_cannot_be_overridden_by_caller(self) -> None:
        events: list[dict[str, object]] = []
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 11,
            audit_writer=events.append,
            data_context_provider=lambda _symbol, _price, _context: {
                "data_status": "DEGRADED",
                "data_realtime": False,
                "data_fallback": True,
                "data_quarantined": False,
                "market_snapshot_id": "snapshot-authoritative",
                "authoritative_price": 200,
                "price_deviation_pct": 0,
                "data_quality": {
                    "status": "DEGRADED",
                    "realtime": False,
                    "fallback": True,
                    "quarantined": False,
                    "can_increase_risk": False,
                    "blocking_reasons": ["权威行情为降级源"],
                },
            },
        )

        result = service.evaluate(
            symbol="AAPL",
            side="BUY",
            mode="PAPER",
            notional=1_000,
            price=200,
            context={
                "source": "manual",
                "data_status": "READY",
                "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
            },
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["context"]["market_snapshot_id"], "snapshot-authoritative")
        self.assertEqual(events[-1]["market_snapshot_id"], "snapshot-authoritative")
        self.assertEqual(events[-1]["data_quality"]["status"], "DEGRADED")

    def test_authoritative_position_side_cannot_be_spoofed_as_a_reduction(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        portfolio_position_sides: list[str] = []

        def portfolio_context(
            _risk: dict[str, object],
            _symbol: str,
            _side: str,
            _notional: float,
            _price: float,
            context: dict[str, object],
        ) -> dict[str, object]:
            portfolio_position_sides.append(str(context.get("position_side") or ""))
            return {"status": "PASS", "portfolio_gate_passed": True, "reject_reasons": []}

        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 11,
            data_context_provider=lambda _symbol, _price, _context: {
                "data_status": "STALE",
                "data_realtime": False,
                "data_fallback": True,
                "data_quarantined": False,
                "data_quality": {
                    "status": "STALE",
                    "realtime": False,
                    "fallback": True,
                    "quarantined": False,
                    "can_increase_risk": False,
                    "blocking_reasons": ["stale market data"],
                },
            },
            portfolio_context_provider=portfolio_context,
        )

        result = service.evaluate(
            symbol="AAPL",
            side="SELL",
            mode="PAPER",
            notional=1_000,
            price=200,
            context={"position_side": "LONG", "direction_mode": "LONG_ONLY"},
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["context"]["position_side"], "FLAT")
        self.assertEqual(portfolio_position_sides, ["FLAT"])
        self.assertEqual(
            result["context"]["account_context_mismatches"],
            [{"field": "position_side", "caller": "LONG", "authoritative": "FLAT"}],
        )
        failed_checks = {row["name"] for row in result["checks"] if not row["ok"]}
        self.assertIn("account_context_consistency", failed_checks)
        self.assertIn("market_data_quality", failed_checks)

    def test_authoritative_portfolio_budget_blocks_new_risk(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 12,
            data_context_provider=lambda _symbol, _price, _context: {
                "data_status": "READY",
                "data_realtime": True,
                "data_fallback": False,
                "data_quarantined": False,
                "data_quality": {
                    "status": "READY",
                    "realtime": True,
                    "fallback": False,
                    "quarantined": False,
                    "can_increase_risk": True,
                    "blocking_reasons": [],
                },
            },
            portfolio_context_provider=lambda *_args: {
                "status": "BLOCK",
                "portfolio_gate_passed": False,
                "reject_reasons": ["Correlated cluster 50.00% / limit 45.00%."],
            },
        )

        result = service.evaluate(symbol="AAPL", side="BUY", mode="PAPER", notional=1_000, price=200)

        self.assertFalse(result["allowed"])
        self.assertIn("组合风险预算阻断", result["reason"])
        self.assertTrue(result["context"]["portfolio_risk_required"])

    def test_market_data_execution_context_detects_price_mismatch(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1m",
                "rows": [{"ts": 99_000, "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10}],
                "source": "okx_realtime_candles",
                "latest_ts": 99_000,
                "data_age_ms": 1_000,
                "realtime": True,
                "fallback": False,
            },
            okx_first=lambda *_args: {
                "last": "100.123456789012345678901234567", "open24h": "95", "high24h": "102", "low24h": "94", "ts": "99000",
            },
        )

        ready = service.execution_context("BTC-USDT", 100)
        mismatch = service.execution_context("BTC-USDT", 90)

        self.assertEqual(ready["data_status"], "READY")
        self.assertTrue(ready["data_quality"]["can_increase_risk"])
        self.assertEqual(mismatch["data_status"], "PRICE_MISMATCH")
        self.assertFalse(mismatch["data_quality"]["can_increase_risk"])

    def test_market_data_string_permission_flags_fail_closed(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": "true",
                "bar": "1m",
                "rows": [{"ts": 99_000, "open": 100, "high": 100, "low": 100, "close": 100, "volume": 1}],
                "source": "okx_realtime_candles",
                "latest_ts": 99_000,
                "data_age_ms": 1_000,
                "realtime": "true",
                "fallback": False,
            },
            okx_first=lambda *_args: {
                "last": "100", "open24h": "99", "high24h": "101", "low24h": "98", "ts": "99000",
            },
        )

        result = service.execution_context("BTC-USDT", 100)

        self.assertNotEqual(result["data_status"], "READY")
        self.assertFalse(result["data_realtime"])
        self.assertFalse(result["data_quality"]["can_increase_risk"])

    def test_paper_executor_records_full_lifecycle(self) -> None:
        events: list[dict[str, object]] = []
        executor = PaperExecutor(
            now_ms=lambda: 20,
            audit_writer=events.append,
            book_reader=lambda _symbol, _side: [[100, 20]],
            funding_rate_reader=lambda _symbol: 0,
        )
        result = executor.submit(
            symbol="BTC-USDT",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=1_000,
            risk_result=paper_risk_approval(
                "risk-1", symbol="BTC-USDT", notional=1_000, checked_at=20,
            ),
            context={"source": "strategy", "strategy_id": "dual_ma", "run_id": "run-1"},
        )
        self.assertEqual(result["lifecycle_state"], "FILLED")
        self.assertEqual([row["state"] for row in result["transitions"]], ["CREATED", "RISK_CHECKED", "ACCEPTED", "FILLED"])
        self.assertEqual(executor.snapshot()["counts"]["FILLED"], 1)
        self.assertEqual(events[-1]["type"], "paper_order_snapshot")
        restored = PaperExecutor(
            now_ms=lambda: 21,
            history_loader=lambda: [event for event in events if event["type"] == "paper_order_snapshot"],
        )
        self.assertEqual(restored.snapshot()["counts"]["FILLED"], 1)

    def test_paper_executor_returns_isolated_nested_snapshots(self) -> None:
        events: list[dict[str, object]] = []
        stored: list[dict[str, object]] = []
        executor = PaperExecutor(
            now_ms=lambda: 22,
            audit_writer=events.append,
            order_writer=lambda order: stored.append(order),
            book_reader=lambda _symbol, _side: [[100, 20]],
            funding_rate_reader=lambda _symbol: 0,
        )
        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=1_000,
            risk_result=paper_risk_approval(
                "risk-isolation", symbol="AAPL", notional=1_000, checked_at=22,
            ),
        )
        order_id = str(result["order_id"])

        result["transitions"][0]["state"] = "MUTATED"
        result["filled_qty"] = -99
        fetched = executor.get(order_id)
        self.assertIsNotNone(fetched)
        fetched["execution_report"]["filled_qty"] = -88
        fetched["transitions"][0]["state"] = "MUTATED_AGAIN"
        listed = executor.list()
        listed[0]["execution_report"]["filled_qty"] = -77

        internal = executor.get(order_id)
        self.assertEqual(internal["execution_report"]["filled_qty"], 10)
        self.assertEqual(internal["transitions"][0]["state"], "CREATED")
        self.assertEqual(stored[-1]["execution_report"]["filled_qty"], 10)
        self.assertEqual(events[-1]["order"]["execution_report"]["filled_qty"], 10)

    def test_paper_executor_blocks_after_unresolved_persistence_failure(self) -> None:
        events: list[dict[str, object]] = []

        def fail_write(_order: dict[str, object]) -> None:
            raise RuntimeError("disk unavailable")

        executor = PaperExecutor(
            now_ms=lambda: 30,
            audit_writer=events.append,
            order_writer=fail_write,
            book_reader=lambda _symbol, _side: [[100, 20]],
        )
        request = {
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "mark_price": 100,
            "notional": 1_000,
            "risk_result": paper_risk_approval(
                "risk-persistence-failure",
                symbol="AAPL",
                notional=1_000,
                checked_at=30,
            ),
        }

        with self.assertRaisesRegex(RuntimeError, "disk unavailable"):
            executor.submit(**request)

        snapshot = executor.snapshot()
        self.assertEqual(snapshot["restore_status"], "BLOCK")
        self.assertEqual(snapshot["persistence_failed_count"], 1)
        self.assertFalse(snapshot["restart_ready"])
        self.assertIn("paper_order_persistence_failed:RuntimeError", snapshot["restore_blockers"])
        blocked = executor.submit(**{
            **request,
            "risk_result": paper_risk_approval(
                "risk-after-persistence-failure",
                symbol="AAPL",
                notional=1_000,
                checked_at=30,
            ),
        })
        self.assertEqual(blocked["persistence_status"], "RESTORE_BLOCKED")
        self.assertTrue(any(event.get("type") == "paper_order_persistence_failed" for event in events))

    def test_paper_executor_restores_highest_order_sequence(self) -> None:
        executor = PaperExecutor(
            now_ms=lambda: 42,
            history_loader=lambda: [{
                "order_id": "paper-42-000150",
                "account_id": "default",
                "risk_request_id": "risk-paper-42-000150",
                "symbol": "AAPL",
                "side": "BUY",
                "order_type": "MARKET",
                "mark_price": 100,
                "limit_price": 0,
                "requested_notional": 100,
                "requested_qty": 1,
                "quantity_constrained": True,
                "reduce_only": False,
                "position_side_before": "FLAT",
                "state": "FILLED",
                "created_at": 41,
                "updated_at": 41,
                "transitions": [{"state": "FILLED", "time": 41, "reason": "restored"}],
                "execution_report": {
                    "status": "FILLED",
                    "avg_price": 100,
                    "filled_qty": 1,
                    "filled_notional": 100,
                },
            }],
            book_reader=lambda _symbol, _side: [[100, 20]],
            funding_rate_reader=lambda _symbol: 0,
        )

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result=paper_risk_approval("risk-sequence", checked_at=42),
        )

        self.assertTrue(str(result["order_id"]).startswith("paper-42-"))
        self.assertTrue(str(result["order_id"]).endswith("-000151"))

    def test_paper_executor_fails_closed_when_persistent_history_restore_fails(self) -> None:
        book_calls: list[tuple[str, str]] = []

        def failed_history() -> list[dict[str, object]]:
            raise OSError("history unavailable")

        executor = PaperExecutor(
            now_ms=lambda: 42,
            history_loader=failed_history,
            order_writer=lambda _order: None,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 20]],
        )

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result={"allowed": True, "mode": "PAPER", "request_id": "risk-restore-failure"},
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertEqual(result["restore_status"], "BLOCK")
        self.assertEqual(result["filled_notional"], 0)
        self.assertEqual(book_calls, [])
        self.assertEqual(executor.snapshot()["order_count"], 0)
        self.assertEqual(executor.snapshot()["restore_status"], "BLOCK")

    def test_paper_executor_fails_closed_on_restored_idempotency_conflict(self) -> None:
        history = [
            {
                **paper_lifecycle_fill("paper-42-000001", "BUY", 1, 100, 40),
                "idempotency_key": "duplicate",
                "request_signature": "AAPL|BUY|MARKET|100.00000000|100.00000000|0.00000000|1.00000000",
            },
            {
                **paper_lifecycle_fill("paper-42-000002", "BUY", 1, 100, 41),
                "idempotency_key": "duplicate",
                "request_signature": "AAPL|BUY|MARKET|100.00000000|100.00000000|0.00000000|1.00000000",
            },
        ]
        executor = PaperExecutor(now_ms=lambda: 42, history_loader=lambda: history)

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result={"allowed": True, "mode": "PAPER", "request_id": "risk-restore-conflict"},
        )

        self.assertEqual(result["restore_status"], "BLOCK")
        self.assertIn("paper_order_history_idempotency_conflict", result["restore_blockers"])
        self.assertEqual(executor.snapshot()["order_count"], 0)

    def test_paper_executor_rejects_missing_risk_check(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[100, 20]])
        result = executor.submit(
            symbol="BTC-USDT", side="BUY", order_type="MARKET", mark_price=100,
            notional=1_000, risk_result=None,
        )
        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertEqual(result["filled_notional"], 0)

    def test_paper_executor_rejects_string_risk_authorization(self) -> None:
        book_calls: list[tuple[str, str]] = []
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 20]],
        )

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result={"allowed": "false", "mode": "PAPER", "request_id": "forged"},
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertEqual(result["filled_notional"], 0)
        self.assertEqual(book_calls, [])

    def test_paper_executor_rejects_non_object_context_without_raising(self) -> None:
        book_calls: list[tuple[str, str]] = []
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 20]],
        )

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result=paper_risk_approval("risk-context"),
            context="bad",
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertIn("execution_context_object_required", result["risk_authorization_blockers"])
        self.assertEqual(book_calls, [])

    def test_paper_executor_binds_risk_approval_to_exact_order(self) -> None:
        book_calls: list[tuple[str, str]] = []
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 100]],
        )

        result = executor.submit(
            symbol="BTC-USDT",
            side="SELL",
            order_type="MARKET",
            mark_price=100,
            notional=5_000,
            risk_result=paper_risk_approval("risk-aapl-small"),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertTrue({"risk_symbol_mismatch", "risk_side_mismatch", "risk_notional_mismatch"}.issubset(
            set(result["risk_authorization_blockers"])
        ))
        self.assertEqual(book_calls, [])

    def test_paper_executor_rejects_stale_future_and_malformed_authorizations(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 20_000, book_reader=lambda *_args: [[100, 20]])
        approvals = [
            paper_risk_approval("risk-stale", checked_at=1),
            paper_risk_approval("risk-future", checked_at=22_000),
            {**paper_risk_approval("risk-malformed", checked_at=20_000), "checked_at": "20000"},
        ]

        results = [
            executor.submit(
                symbol="AAPL", side="BUY", order_type="MARKET", mark_price=100,
                notional=100, risk_result=approval,
            )
            for approval in approvals
        ]

        self.assertIn("risk_authorization_expired", results[0]["risk_authorization_blockers"])
        self.assertIn("risk_checked_at_future", results[1]["risk_authorization_blockers"])
        self.assertIn("risk_checked_at_invalid", results[2]["risk_authorization_blockers"])
        self.assertEqual(executor.snapshot()["order_count"], 0)

    def test_paper_executor_rejects_unknown_order_type_before_book_read(self) -> None:
        book_calls: list[tuple[str, str]] = []
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 20]],
        )

        result = executor.submit(
            symbol="AAPL", side="BUY", order_type="UNKNOWN", mark_price=100, notional=100,
            risk_result=paper_risk_approval("risk-unknown"),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertEqual(result["order_type"], "UNKNOWN")
        self.assertIn("order_type_invalid", result["risk_authorization_blockers"])
        self.assertEqual(book_calls, [])

    def test_paper_executor_rejects_quantity_notional_mismatch(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[100, 20]])

        result = executor.submit(
            symbol="AAPL", side="BUY", order_type="MARKET", mark_price=100,
            notional=100, requested_qty=2, risk_result=paper_risk_approval("risk-quantity"),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertIn("requested_quantity_notional_mismatch", result["risk_authorization_blockers"])
        self.assertEqual(executor.snapshot()["order_count"], 0)

    def test_paper_executor_binds_limit_price_to_risk_approval(self) -> None:
        book_calls: list[tuple[str, str]] = []
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda symbol, side: book_calls.append((symbol, side)) or [[100, 20]],
        )

        result = executor.submit(
            symbol="AAPL", side="BUY", order_type="IOC", mark_price=100,
            limit_price=101, notional=100,
            risk_result=paper_risk_approval(
                "risk-limit-binding", order_type="IOC", limit_price=100,
            ),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertIn("risk_limit_price_mismatch", result["risk_authorization_blockers"])
        self.assertEqual(book_calls, [])

    def test_paper_executor_rejects_oversized_risk_request_id(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[100, 20]])
        result = executor.submit(
            symbol="AAPL", side="BUY", order_type="MARKET", mark_price=100, notional=100,
            risk_result=paper_risk_approval("r" * 161),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertIn("risk_request_id_invalid", result["risk_authorization_blockers"])

    def test_paper_risk_authorization_is_single_use(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[100, 20]])
        approval = paper_risk_approval("risk-single-use")

        first = executor.submit(
            symbol="AAPL", side="BUY", order_type="MARKET", mark_price=100,
            notional=100, risk_result=approval,
        )
        second = executor.submit(
            symbol="AAPL", side="BUY", order_type="MARKET", mark_price=100,
            notional=100, risk_result=approval,
        )

        self.assertEqual(first["lifecycle_state"], "FILLED")
        self.assertEqual(second["lifecycle_state"], "REJECTED")
        self.assertIn("risk_authorization_already_consumed", second["risk_authorization_blockers"])
        self.assertEqual(executor.snapshot()["order_count"], 1)

    def test_paper_executor_rejects_oversized_idempotency_key_without_truncation(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[100, 20]])

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result={"allowed": True, "mode": "PAPER", "request_id": "risk-long-key"},
            context={"idempotency_key": "x" * 161},
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertTrue(result["idempotency_contract_invalid"])
        self.assertEqual(executor.snapshot()["order_count"], 0)

    def test_paper_executor_blocks_malformed_restored_order_before_replay(self) -> None:
        malformed = paper_lifecycle_fill("paper-30-000001", "BUY", 1, 100, 30)
        malformed["idempotency_key"] = "malformed-history"
        malformed["request_signature"] = "AAPL|BUY|MARKET|100.00000000|100.00000000|0.00000000|1.00000000"
        malformed["execution_report"] = "not-an-object"
        executor = PaperExecutor(now_ms=lambda: 31, history_loader=lambda: [malformed])

        result = executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=100,
            risk_result={"allowed": True, "mode": "PAPER", "request_id": "risk-replay"},
            context={"idempotency_key": "malformed-history"},
        )

        self.assertEqual(result["restore_status"], "BLOCK")
        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertIn("execution_report_invalid", " ".join(result["restore_blockers"]))

    def test_paper_executor_blocks_persistent_orders_without_a_matcher(self) -> None:
        executor = PaperExecutor(now_ms=lambda: 30, book_reader=lambda *_args: [[99, 20]])

        result = executor.submit(
            symbol="BTC-USDT",
            side="BUY",
            order_type="LIMIT",
            mark_price=100,
            limit_price=99,
            notional=1_000,
            risk_result=paper_risk_approval(
                "risk-limit", symbol="BTC-USDT", notional=1_000, order_type="LIMIT", limit_price=99,
            ),
        )

        self.assertEqual(result["lifecycle_state"], "REJECTED")
        self.assertEqual(result["unsupported_capability"], "persistent_order_matching")
        self.assertEqual(executor.snapshot()["working_count"], 0)

    def test_partial_market_fill_cancels_the_unfilled_remainder(self) -> None:
        executor = PaperExecutor(
            now_ms=lambda: 30,
            book_reader=lambda *_args: [[100, 5]],
            funding_rate_reader=lambda _symbol: 0,
        )

        result = executor.submit(
            symbol="BTC-USDT",
            side="BUY",
            order_type="MARKET",
            mark_price=100,
            notional=1_000,
            risk_result=paper_risk_approval(
                "risk-partial", symbol="BTC-USDT", notional=1_000,
            ),
        )

        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["filled_notional"], 500)
        self.assertEqual(result["lifecycle_state"], "CANCELLED")
        self.assertEqual(result["transitions"][-2]["state"], "PARTIALLY_FILLED")
        self.assertEqual(executor.snapshot()["working_count"], 0)

    def test_paper_executor_cancel_is_persisted_and_restored(self) -> None:
        stored: list[dict[str, object]] = []
        original = {
            "order_id": "paper-cancel-1",
            "account_id": "default",
            "risk_request_id": "risk-paper-cancel-1",
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "mark_price": 100,
            "limit_price": 0,
            "requested_notional": 100,
            "requested_qty": 0,
            "quantity_constrained": False,
            "reduce_only": False,
            "position_side_before": "FLAT",
            "state": "ACCEPTED",
            "created_at": 1,
            "updated_at": 1,
            "transitions": [{"state": "ACCEPTED", "time": 1, "reason": "test"}],
            "execution_report": {
                "status": "ACCEPTED",
                "avg_price": 0,
                "filled_qty": 0,
                "filled_notional": 0,
            },
        }
        executor = PaperExecutor(
            now_ms=lambda: 31,
            history_loader=lambda: [original],
            order_writer=lambda order: stored.append(deepcopy(order)),
        )

        cancelled = executor.cancel("paper-cancel-1", "test cancel")
        restored = PaperExecutor(now_ms=lambda: 32, history_loader=lambda: stored)

        self.assertEqual(cancelled["state"], "CANCELLED")
        self.assertEqual(stored[-1]["state"], "CANCELLED")
        self.assertEqual(restored.get("paper-cancel-1")["state"], "CANCELLED")

    def test_risk_service_blocks_unimplemented_orders_and_unvalidated_arm_profile(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        data_context = {
            "data_status": "READY",
            "data_realtime": True,
            "data_quality": {"status": "READY", "realtime": True, "can_increase_risk": True},
        }

        limit = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", 1_000, {
            **data_context,
            "order_type": "LIMIT",
        })
        arm = build_pretrade_check(risk, "AAPL", "ARM", "PAPER", 1_000, {
            **data_context,
            "order_type": "MARKET",
            "leverage": 2,
            "direction_mode": "SHORT_ONLY",
        })

        self.assertFalse(limit["allowed"])
        self.assertIn("persistent matcher", limit["reason"])
        self.assertFalse(arm["allowed"])
        failed_arm_checks = {row["name"] for row in arm["checks"] if not row["ok"]}
        self.assertTrue({"paper_arm_order_type", "paper_arm_leverage", "paper_arm_direction"}.issubset(failed_arm_checks))

    def test_paper_ledger_restores_account_and_normalized_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 31)
            state = {
                "cash": 8_000,
                "short_margin": 0,
                "realized_pnl": 125,
                "symbol": "AAPL",
                "position_qty": 10,
                "entry_price": 200,
                "orders": [{"order_id": "paper-1", "time": 30, "symbol": "AAPL", "side": "BUY", "match_status": "FILLED"}],
                "conditional_orders": [{"id": "condition-1", "symbol": "AAPL", "side": "SELL", "status": "WAITING", "updated_at": 30}],
                "equity_curve": [{"time": 30, "equity": 10_125}],
            }

            saved = ledger.save_account(state, reason="test")
            restored = ledger.load_account()
            summary = ledger.summary()

            self.assertEqual(saved["version"], 1)
            self.assertEqual(restored["position_qty"], 10)
            self.assertEqual(summary["backend"], "sqlite")
            self.assertEqual(summary["account_version"], 1)
            self.assertEqual(summary["snapshot_count"], 1)

    def test_paper_ledger_migrates_legacy_funding_estimates_to_charged_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            ledger = PaperLedger(db_path=path, now_ms=lambda: 31)
            ledger.record_lifecycle_order({
                "order_id": "legacy-funding-1",
                "account_id": "default",
                "risk_request_id": "risk-legacy-funding-1",
                "symbol": "BTC-USDT-SWAP",
                "side": "SELL",
                "order_type": "MARKET",
                "mark_price": 100,
                "limit_price": 0,
                "requested_notional": 100,
                "requested_qty": 1,
                "quantity_constrained": True,
                "reduce_only": False,
                "position_side_before": "FLAT",
                "state": "FILLED",
                "created_at": 31,
                "updated_at": 31,
                "transitions": [{"state": "FILLED", "time": 31, "reason": "legacy"}],
                "execution_report": {
                    "status": "FILLED",
                    "avg_price": 100,
                    "filled_qty": 1,
                    "filled_notional": 100,
                    "fee": 0.05,
                    "funding_estimate": 9,
                },
            })
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("UPDATE paper_fills SET funding = 9 WHERE fill_id = 'legacy-funding-1:fill:1'")
                connection.execute("UPDATE paper_schema SET value = '1' WHERE key = 'schema_version'")
                connection.commit()

            PaperLedger(db_path=path, now_ms=lambda: 32)
            with closing(sqlite3.connect(path)) as connection:
                funding = float(connection.execute(
                    "SELECT funding FROM paper_fills WHERE fill_id = 'legacy-funding-1:fill:1'"
                ).fetchone()[0])
                schema = dict(connection.execute("SELECT key, value FROM paper_schema").fetchall())

            self.assertEqual(funding, 0)
            self.assertEqual(schema["schema_version"], "4")
            self.assertEqual(schema["funding_column_semantics"], "charged_only")

    def test_paper_executor_idempotency_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 32)

            def build_executor() -> PaperExecutor:
                return PaperExecutor(
                    now_ms=lambda: 32,
                    book_reader=lambda _symbol, _side: [[100, 20]],
                    funding_rate_reader=lambda _symbol: 0,
                    history_loader=lambda: ledger.load_lifecycle_orders(2000),
                    order_writer=ledger.record_lifecycle_order,
                    idempotency_loader=ledger.find_by_idempotency_key,
                )

            kwargs = {
                "symbol": "BTC-USDT",
                "side": "BUY",
                "order_type": "MARKET",
                "mark_price": 100,
                "notional": 1_000,
                "risk_result": paper_risk_approval(
                    "risk-32",
                    symbol="BTC-USDT",
                    notional=1_000,
                    checked_at=32,
                    idempotency_key="client-order-1",
                    context={"market_snapshot_id": "snapshot-32"},
                ),
                "context": {"idempotency_key": "client-order-1"},
            }
            first = build_executor().submit(**kwargs)
            replay = build_executor().submit(**kwargs)
            rotated_risk_replay = build_executor().submit(**{
                **kwargs,
                "risk_result": paper_risk_approval(
                    "risk-32-rotated",
                    symbol="BTC-USDT",
                    notional=1_000,
                    checked_at=32,
                    idempotency_key="client-order-1",
                    context={"market_snapshot_id": "snapshot-32-rotated"},
                ),
            })
            conflict = build_executor().submit(**{**kwargs, "notional": 1_500})

            self.assertFalse(first["idempotent_replay"])
            self.assertTrue(replay["idempotent_replay"])
            self.assertTrue(rotated_risk_replay["idempotent_replay"])
            self.assertEqual(first["order_id"], replay["order_id"])
            self.assertEqual(first["order_id"], rotated_risk_replay["order_id"])
            self.assertEqual(rotated_risk_replay["risk_request_id"], "risk-32")
            self.assertEqual(replay["market_snapshot_id"], "snapshot-32")
            self.assertTrue(conflict["idempotency_conflict"])
            self.assertEqual(ledger.summary()["order_count"], 1)
            self.assertEqual(ledger.summary()["fill_count"], 1)

    def test_concurrent_executors_resolve_same_idempotency_key_to_one_fill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            ledgers = [
                PaperLedger(db_path=path, now_ms=lambda stamp=stamp: stamp)
                for stamp in (50, 51)
            ]
            executors = []
            for stamp, ledger in zip((50, 51), ledgers):
                executors.append(PaperExecutor(
                    now_ms=lambda stamp=stamp: stamp,
                    book_reader=lambda _symbol, _side: [[100, 20]],
                    history_loader=lambda ledger=ledger: ledger.load_lifecycle_orders(2000),
                    order_writer=ledger.record_lifecycle_order,
                    idempotency_loader=ledger.find_by_idempotency_key,
                ))
            barrier = threading.Barrier(3)

            def submit(index: int) -> dict[str, object]:
                barrier.wait()
                return executors[index].submit(
                    symbol="AAPL",
                    side="BUY",
                    order_type="MARKET",
                    mark_price=100,
                    notional=1_000,
                    risk_result=paper_risk_approval(
                        f"risk-concurrent-{index}",
                        symbol="AAPL",
                        notional=1_000,
                        checked_at=50 + index,
                        idempotency_key="concurrent-order-1",
                    ),
                    context={"idempotency_key": "concurrent-order-1"},
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(submit, index) for index in range(2)]
                barrier.wait()
                results = [future.result(timeout=10) for future in futures]

            self.assertEqual(len({result["order_id"] for result in results}), 1)
            self.assertEqual(sorted(bool(result["idempotent_replay"]) for result in results), [False, True])
            self.assertEqual(ledgers[0].summary()["order_count"], 1)
            self.assertEqual(ledgers[0].summary()["fill_count"], 1)

    def test_paper_ledger_enforces_unique_risk_request_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 60)
            first = paper_lifecycle_fill("risk-order-1", "BUY", 1, 100, 58)
            second = paper_lifecycle_fill("risk-order-2", "BUY", 1, 100, 59)
            first["risk_request_id"] = "risk-durable-single-use"
            second["risk_request_id"] = "risk-durable-single-use"

            ledger.record_lifecycle_order(first)
            with self.assertRaisesRegex(ValueError, "paper_risk_request_id_conflict"):
                ledger.record_lifecycle_order(second)

            self.assertEqual(ledger.summary()["order_count"], 1)
            self.assertEqual(ledger.summary()["fill_count"], 1)

    def test_concurrent_executors_cannot_consume_same_risk_approval_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            ledgers = [PaperLedger(db_path=path, now_ms=lambda: 61) for _ in range(2)]
            executors = [
                PaperExecutor(
                    now_ms=lambda: 61,
                    book_reader=lambda _symbol, _side: [[100, 20]],
                    order_writer=ledger.record_lifecycle_order,
                )
                for ledger in ledgers
            ]
            barrier = threading.Barrier(3)

            def submit(index: int) -> dict[str, object]:
                key = f"risk-race-{index}"
                barrier.wait()
                return executors[index].submit(
                    symbol="AAPL",
                    side="BUY",
                    order_type="MARKET",
                    mark_price=100,
                    notional=100,
                    risk_result=paper_risk_approval(
                        "risk-race-shared", checked_at=61, idempotency_key=key,
                    ),
                    context={"idempotency_key": key},
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(submit, index) for index in range(2)]
                barrier.wait()
                results = [future.result(timeout=10) for future in futures]

            self.assertEqual(sorted(result["lifecycle_state"] for result in results), ["FILLED", "REJECTED"])
            rejected = next(result for result in results if result["lifecycle_state"] == "REJECTED")
            self.assertIn("risk_authorization_already_consumed", rejected["risk_authorization_blockers"])
            self.assertEqual(ledgers[0].summary()["order_count"], 1)
            self.assertEqual(ledgers[0].summary()["fill_count"], 1)

    def test_paper_executor_idempotency_rejects_amount_to_quantity_semantic_change(self) -> None:
        executor = PaperExecutor(
            now_ms=lambda: 32,
            book_reader=lambda _symbol, _side: [[50, 10]],
        )
        request = {
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "MARKET",
            "mark_price": 100,
            "notional": 100,
            "risk_result": paper_risk_approval(
                "risk-semantic", checked_at=32, idempotency_key="semantic-order-1",
            ),
            "context": {"idempotency_key": "semantic-order-1"},
        }

        amount_order = executor.submit(**request)
        quantity_retry = executor.submit(**request, requested_qty=1)

        self.assertEqual(amount_order["filled_qty"], 2)
        self.assertTrue(quantity_retry["idempotency_conflict"])
        self.assertFalse(quantity_retry.get("idempotent_replay", False))
        self.assertEqual(executor.snapshot()["order_count"], 1)

    def test_memory_idempotency_fails_closed_after_order_eviction(self) -> None:
        executor = PaperExecutor(
            now_ms=lambda: 40,
            max_orders=100,
            book_reader=lambda _symbol, _side: [[100, 20]],
            funding_rate_reader=lambda _symbol: 0,
        )
        def request(index: int) -> dict[str, object]:
            key = f"eviction-key-{index}"
            return {
                "symbol": "AAPL",
                "side": "BUY",
                "order_type": "MARKET",
                "mark_price": 100,
                "notional": 100,
                "risk_result": paper_risk_approval(
                    f"risk-eviction-{index}", checked_at=40, idempotency_key=key,
                ),
                "context": {"idempotency_key": key},
            }

        first_request = request(0)
        first = executor.submit(**first_request)
        for index in range(1, 101):
            executor.submit(**request(index))

        replay = executor.submit(**first_request)

        self.assertEqual(replay["order_id"], first["order_id"])
        self.assertTrue(replay["idempotency_history_unavailable"])
        self.assertEqual(replay["lifecycle_state"], "REJECTED")
        self.assertEqual(replay["filled_notional"], 0)
        self.assertEqual(executor.snapshot()["order_count"], 100)

    def test_paper_executor_requires_restart_after_failed_persistence(self) -> None:
        writes = 0
        stored: list[dict[str, object]] = []

        def writer(order: dict[str, object]) -> None:
            nonlocal writes
            writes += 1
            if writes == 1:
                raise OSError("simulated durable store failure")
            stored.append(deepcopy(order))

        executor = PaperExecutor(
            now_ms=lambda: 32,
            book_reader=lambda _symbol, _side: [[100, 20]],
            order_writer=writer,
        )
        kwargs = {
            "symbol": "BTC-USDT",
            "side": "BUY",
            "order_type": "MARKET",
            "mark_price": 100,
            "notional": 1_000,
            "risk_result": paper_risk_approval(
                "risk-retry",
                symbol="BTC-USDT",
                notional=1_000,
                checked_at=32,
                idempotency_key="retry-after-store-failure",
            ),
            "context": {"idempotency_key": "retry-after-store-failure"},
        }

        with self.assertRaises(OSError):
            executor.submit(**kwargs)
        replay = executor.submit(**kwargs)

        self.assertEqual(replay["persistence_status"], "RESTORE_BLOCKED")
        self.assertEqual(replay["lifecycle_state"], "REJECTED")
        self.assertEqual(replay["filled_notional"], 0)
        self.assertEqual(writes, 1)
        self.assertEqual(executor.snapshot()["order_count"], 1)
        self.assertEqual(executor.snapshot()["persistence_failed_count"], 1)
        self.assertEqual(len(stored), 0)

    def test_paper_ledger_reconciles_quantity_constrained_close_without_funding_charge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 33)
            ledger.save_account({
                "cash": 900,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "BTC-USDT-SWAP",
                "position_qty": 1,
                "entry_price": 100,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            executor = PaperExecutor(
                now_ms=lambda: 33,
                book_reader=lambda _symbol, _side: [[90, 10]],
                funding_rate_reader=lambda _symbol: 0.01,
                order_writer=ledger.record_lifecycle_order,
            )
            report = executor.submit(
                symbol="BTC-USDT-SWAP",
                side="SELL",
                order_type="MARKET",
                mark_price=100,
                notional=100,
                requested_qty=1,
                risk_result=paper_risk_approval(
                    "risk-close-33",
                    symbol="BTC-USDT-SWAP",
                    side="SELL",
                    checked_at=33,
                    reduce_only=True,
                    context={"market_snapshot_id": "snapshot-close-33"},
                ),
            )

            reconciled = ledger.reconcile_account()
            restored = ledger.load_account()

            self.assertEqual(report["filled_qty"], 1)
            self.assertEqual(report["filled_notional"], 90)
            self.assertEqual(report["funding_estimate"], 0.9)
            self.assertEqual(report["funding_charged"], 0)
            self.assertEqual(reconciled["reconciled"], 1)
            self.assertEqual(reconciled["blockers"], [])
            self.assertEqual(restored["position_qty"], 0)
            self.assertAlmostEqual(restored["cash"], 989.955)
            self.assertAlmostEqual(restored["realized_pnl"], -10.045)
            self.assertEqual(restored["orders"][-1]["funding_estimate"], 0.9)
            self.assertEqual(restored["orders"][-1]["funding_charged"], 0)
            self.assertTrue(ledger.summary()["restart_ready"])

    def test_paper_ledger_reconciles_fill_after_interrupted_account_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 33)
            ledger.save_account({
                "cash": 10_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "BTC-USDT",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 10_000}],
            }, reason="baseline")
            executor = PaperExecutor(
                now_ms=lambda: 33,
                book_reader=lambda _symbol, _side: [[100, 20]],
                funding_rate_reader=lambda _symbol: 0,
                order_writer=ledger.record_lifecycle_order,
            )
            report = executor.submit(
                symbol="BTC-USDT",
                side="BUY",
                order_type="MARKET",
                mark_price=100,
                notional=1_000,
                requested_qty=10,
                risk_result=paper_risk_approval(
                    "risk-33",
                    symbol="BTC-USDT",
                    notional=1_000,
                    checked_at=33,
                    context={"market_snapshot_id": "snapshot-33"},
                ),
            )

            self.assertEqual(ledger.summary()["pending_settlement_count"], 1)
            reconciled = ledger.reconcile_account()
            restored = ledger.load_account()

            self.assertEqual(reconciled["reconciled"], 1)
            self.assertEqual(restored["position_qty"], 10)
            self.assertAlmostEqual(restored["cash"], 8_999.5)
            self.assertEqual(restored["orders"][-1]["order_id"], report["order_id"])
            self.assertEqual(ledger.summary()["pending_settlement_count"], 0)
            self.assertTrue(ledger.summary()["restart_ready"])
            self.assertEqual(ledger.reconcile_account()["reconciled"], 0)

    def test_paper_ledger_reconciles_partial_fill_exactly_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 34)
            ledger.save_account({
                "cash": 10_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 10_000}],
            }, reason="baseline")
            executor = PaperExecutor(
                now_ms=lambda: 34,
                book_reader=lambda _symbol, _side: [[100, 5]],
                order_writer=ledger.record_lifecycle_order,
            )

            report = executor.submit(
                symbol="AAPL",
                side="BUY",
                order_type="MARKET",
                mark_price=100,
                notional=1_000,
                risk_result=paper_risk_approval(
                    "risk-partial-ledger", notional=1_000, checked_at=34,
                ),
            )
            first = ledger.reconcile_account()
            restored = ledger.load_account()
            second = ledger.reconcile_account()

            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(first["reconciled"], 1)
            self.assertEqual(restored["position_qty"], 5)
            self.assertAlmostEqual(restored["cash"], 9_499.75)
            self.assertEqual(len(restored["orders"]), 1)
            self.assertEqual(second["reconciled"], 0)
            self.assertTrue(ledger.summary()["restart_ready"])

    def test_paper_ledger_stale_reconciliation_cannot_overwrite_newer_settlement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            stale_ledger = PaperLedger(db_path=path, now_ms=lambda: 35)
            newer_ledger = PaperLedger(db_path=path, now_ms=lambda: 36)
            stale_ledger.save_account({
                "cash": 1_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            stale_ledger.record_lifecycle_order(paper_lifecycle_fill("first-fill", "BUY", 1, 100, 10))
            original_save = stale_ledger.save_account
            injected = False

            def interleaved_save(payload: dict[str, object], reason: str = "state_update", **kwargs: object) -> dict[str, object]:
                nonlocal injected
                if not injected:
                    injected = True
                    newer_ledger.record_lifecycle_order(
                        paper_lifecycle_fill(
                            "second-fill",
                            "BUY",
                            1,
                            100,
                            20,
                            position_side_before="LONG",
                        )
                    )
                    self.assertEqual(newer_ledger.reconcile_account()["reconciled"], 2)
                return original_save(payload, reason=reason, **kwargs)

            stale_ledger.save_account = interleaved_save  # type: ignore[method-assign]
            stale_ledger.reconcile_account()
            restored = newer_ledger.load_account()

            self.assertEqual(restored["position_qty"], 2)
            self.assertEqual([order["order_id"] for order in restored["orders"]], ["first-fill", "second-fill"])
            self.assertEqual(newer_ledger.summary()["pending_settlement_count"], 0)
            self.assertTrue(newer_ledger.summary()["restart_ready"])

    def test_paper_ledger_never_reports_ok_with_unresolved_applied_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 36)
            ledger.save_account({
                "cash": 900,
                "short_margin": 0,
                "realized_pnl": 0,
                "position_qty": 1,
                "entry_price": 100,
                "symbol": "AAPL",
                "orders": [{"order_id": "orphaned-applied-fill"}],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="inconsistent_baseline")
            ledger.record_lifecycle_order(paper_lifecycle_fill("orphaned-applied-fill", "BUY", 1, 100, 20))

            reconciliation = ledger.reconcile_account()

            self.assertFalse(reconciliation["ok"])
            self.assertEqual(reconciliation["reconciled"], 0)
            self.assertEqual(reconciliation["pending"], 1)
            self.assertTrue(reconciliation["blockers"])
            self.assertFalse(ledger.summary()["restart_ready"])

    def test_paper_ledger_reconciliation_stops_at_first_unsettleable_fill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 35)
            ledger.save_account({
                "cash": 900,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 1,
                "entry_price": 100,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            ledger.record_lifecycle_order(paper_lifecycle_fill("first-overclose", "SELL", 2, 100, 10))
            ledger.record_lifecycle_order(paper_lifecycle_fill("second-buy", "BUY", 1, 100, 20))

            reconciliation = ledger.reconcile_account()
            restored = ledger.load_account()

            self.assertFalse(reconciliation["ok"])
            self.assertEqual(reconciliation["reconciled"], 0)
            self.assertEqual(reconciliation["pending"], 2)
            self.assertEqual(restored["position_qty"], 1)
            self.assertEqual(restored["orders"], [])
            self.assertEqual(ledger.summary()["pending_settlement_count"], 2)

    def test_paper_ledger_reconciliation_rechecks_reduce_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 36)
            ledger.save_account({
                "cash": 1_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            ledger.record_lifecycle_order(
                paper_lifecycle_fill("flat-reduce-only", "SELL", 1, 100, 10, reduce_only=True)
            )

            reconciliation = ledger.reconcile_account()
            restored = ledger.load_account()

            self.assertFalse(reconciliation["ok"])
            self.assertEqual(reconciliation["reconciled"], 0)
            self.assertEqual(restored["position_qty"], 0)
            self.assertEqual(restored["orders"], [])
            self.assertEqual(ledger.summary()["pending_settlement_count"], 1)

    def test_paper_ledger_corrupt_lifecycle_payload_blocks_reconciliation_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            ledger = PaperLedger(db_path=path, now_ms=lambda: 36)
            ledger.save_account({
                "cash": 1_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            order = paper_lifecycle_fill("corrupt-reconcile", "BUY", 1, 100, 20)
            ledger.record_lifecycle_order(order)
            order["reduce_only"] = "false"
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    "UPDATE paper_lifecycle_orders SET payload_json = ? WHERE order_id = ?",
                    (json.dumps(order), "corrupt-reconcile"),
                )
                connection.commit()

            reconciliation = ledger.reconcile_account()
            restored = PaperExecutor(
                now_ms=lambda: 37,
                history_loader=lambda: ledger.load_lifecycle_orders(2000),
            )

            self.assertFalse(reconciliation["ok"])
            self.assertEqual(reconciliation["reconciled"], 0)
            self.assertEqual(reconciliation["pending"], 1)
            self.assertTrue(any("settlement_contract_invalid" in item for item in reconciliation["blockers"]))
            self.assertEqual(restored.snapshot()["restore_status"], "BLOCK")

    def test_paper_ledger_rejects_non_finite_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 37)
            invalid_state = {
                "cash": math.inf,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": math.inf}],
            }

            with self.assertRaisesRegex(ValueError, "paper_non_finite_payload"):
                ledger.save_account(invalid_state, reason="invalid")

            self.assertEqual(ledger.load_account(), {})

    def test_paper_ledger_rejects_boolean_account_and_fill_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 38)
            invalid_state = {
                "cash": True,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 10_000}],
            }
            invalid_order = paper_lifecycle_fill("boolean-fill", "BUY", 1, 100, 38)
            invalid_order["execution_report"]["filled_qty"] = True
            invalid_reduce_only = paper_lifecycle_fill("string-reduce-only", "SELL", 1, 100, 38)
            invalid_reduce_only["reduce_only"] = "false"

            with self.assertRaisesRegex(ValueError, "paper_boolean_numeric_field:cash"):
                ledger.save_account(invalid_state)
            with self.assertRaisesRegex(ValueError, "paper_order_contract_report_filled_qty_invalid"):
                ledger.record_lifecycle_order(invalid_order)
            with self.assertRaisesRegex(ValueError, "paper_order_contract_reduce_only_invalid"):
                ledger.record_lifecycle_order(invalid_reduce_only)

    def test_paper_ledger_rejects_inconsistent_fill_arithmetic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 38)
            invalid_order = paper_lifecycle_fill("inconsistent-fill", "BUY", 2, 100, 38)
            invalid_order["execution_report"]["filled_notional"] = 250

            with self.assertRaisesRegex(ValueError, "paper_order_contract_fill_notional_mismatch"):
                ledger.record_lifecycle_order(invalid_order)

            self.assertIsNone(ledger.get_lifecycle_order("inconsistent-fill"))

    def test_paper_ledger_rejects_rewrite_of_a_settled_fill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            ledger = PaperLedger(db_path=path, now_ms=lambda: 33)
            ledger.save_account({
                "cash": 1_000,
                "short_margin": 0,
                "realized_pnl": 0,
                "symbol": "AAPL",
                "position_qty": 0,
                "entry_price": 0,
                "leverage": 1,
                "orders": [],
                "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }, reason="baseline")
            order = {
                "order_id": "paper-immutable-1",
                "account_id": "default",
                "risk_request_id": "risk-paper-immutable-1",
                "idempotency_key": "immutable-request-1",
                "request_signature": "AAPL|BUY|MARKET|100.00000000|100.00000000|0.00000000|1.00000000",
                "symbol": "AAPL",
                "side": "BUY",
                "order_type": "MARKET",
                "mark_price": 100.0,
                "limit_price": 0.0,
                "requested_notional": 100.0,
                "requested_qty": 1.0,
                "quantity_constrained": True,
                "reduce_only": False,
                "position_side_before": "FLAT",
                "state": "FILLED",
                "created_at": 33,
                "updated_at": 33,
                "transitions": [
                    {"state": "CREATED", "time": 33, "reason": "created"},
                    {"state": "FILLED", "time": 33, "reason": "filled"},
                ],
                "execution_report": {
                    "status": "FILLED",
                    "avg_price": 100.0,
                    "filled_qty": 1.0,
                    "filled_notional": 100.0,
                    "fee": 0.05,
                    "funding_estimate": 0.0,
                    "funding_charged": 0.0,
                },
            }
            ledger.record_lifecycle_order(order)
            self.assertEqual(ledger.reconcile_account()["reconciled"], 1)

            rewritten = deepcopy(order)
            rewritten["execution_report"]["fee"] = 0.10
            with self.assertRaisesRegex(ValueError, "paper_fill_immutable_conflict"):
                ledger.record_lifecycle_order(rewritten)

            restored = ledger.load_account()
            stored_order = ledger.get_lifecycle_order("paper-immutable-1")
            with closing(sqlite3.connect(path)) as connection:
                stored_fill = connection.execute(
                    "SELECT quantity, notional FROM paper_fills WHERE fill_id = ?",
                    ("paper-immutable-1:fill:1",),
                ).fetchone()

            self.assertEqual(restored["position_qty"], 1)
            self.assertEqual(stored_order["execution_report"]["filled_qty"], 1)
            self.assertEqual(tuple(stored_fill), (1.0, 100.0))
            self.assertTrue(ledger.summary()["restart_ready"])

    def test_event_replay_verifies_market_risk_order_and_fill_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audit = AuditLog(path=root / "audit.jsonl", ensure_runtime=lambda: root.mkdir(exist_ok=True), now_ms=lambda: 34)
            ledger = PaperLedger(db_path=root / "paper.sqlite3", now_ms=lambda: 34)
            audit.append({
                "type": "market_snapshot",
                "snapshot_id": "snapshot-34",
                "symbol": "BTC-USDT",
                "last": 100,
                "quality": {"status": "READY", "realtime": True},
            })
            audit.append({
                "type": "risk_pretrade_pass",
                "request_id": "risk-34",
                "signal_id": "signal-34",
                "market_snapshot_id": "snapshot-34",
                "symbol": "BTC-USDT",
                "side": "BUY",
                "mode": "PAPER",
                "status": "PASS",
            })
            executor = PaperExecutor(
                now_ms=lambda: 34,
                audit_writer=audit.append,
                book_reader=lambda _symbol, _side: [[100, 20]],
                funding_rate_reader=lambda _symbol: 0,
                order_writer=ledger.record_lifecycle_order,
            )
            report = executor.submit(
                symbol="BTC-USDT",
                side="BUY",
                order_type="MARKET",
                mark_price=100,
                notional=1_000,
                requested_qty=10,
                risk_result=paper_risk_approval(
                    "risk-34",
                    symbol="BTC-USDT",
                    notional=1_000,
                    checked_at=34,
                    context={
                        "signal_id": "signal-34",
                        "signal_created_at": 33,
                        "signal_action": "BUY",
                        "signal_reason": "dual_ma entry",
                        "market_snapshot_id": "snapshot-34",
                        "data_quality": {"status": "READY"},
                    },
                ),
                context={"run_id": "run-34", "strategy_id": "dual_ma"},
            )
            replay = EventReplayService(
                now_ms=lambda: 35,
                audit_query=lambda **kwargs: audit.query(**kwargs),
                order_loader=ledger.get_lifecycle_order,
                run_order_loader=ledger.load_run_orders,
            )

            trace = replay.replay_order(report["order_id"])
            run_trace = replay.replay_run("run-34")
            corrupted_order = deepcopy(ledger.get_lifecycle_order(report["order_id"]))
            corrupted_order["execution_report"]["filled_qty"] = 11
            corrupted_order["execution_report"]["filled_notional"] = 1_100
            corrupted_replay = EventReplayService(
                now_ms=lambda: 35,
                audit_query=lambda **kwargs: audit.query(**kwargs),
                order_loader=lambda _order_id: corrupted_order,
                run_order_loader=lambda _run_id, _limit: [corrupted_order],
            ).replay_order(report["order_id"])

            self.assertEqual(trace["status"], "PASS")
            self.assertTrue(all(check["ok"] for check in trace["checks"]))
            self.assertEqual(trace["signal_id"], "signal-34")
            self.assertEqual(run_trace["status"], "PASS")
            self.assertEqual(run_trace["passed_count"], 1)
            quantity_check = next(check for check in corrupted_replay["checks"] if check["name"] == "fill_quantity_constraint")
            self.assertFalse(quantity_check["ok"])
            self.assertEqual(corrupted_replay["status"], "BLOCK")

    def test_signal_lineage_is_stable_for_an_idempotent_request(self) -> None:
        first = build_signal_context(
            {"idempotency_key": "manual-order-key", "source": "manual"},
            now_ms=lambda: 35,
            symbol="AAPL",
            side="BUY",
        )
        replay = build_signal_context(
            {"idempotency_key": "manual-order-key", "source": "manual"},
            now_ms=lambda: 99,
            symbol="AAPL",
            side="BUY",
        )

        self.assertEqual(first["signal_id"], replay["signal_id"])
        self.assertEqual(first["signal_action"], "BUY")
        self.assertNotIn("manual-order-key", first["signal_id"])

    def test_http_mutation_contract_protects_strategy_pipeline(self) -> None:
        self.assertIn("/api/strategy/pipeline", MUTATION_PATHS)
        self.assertEqual(allowed_web_origin("http://127.0.0.1:8765"), "http://127.0.0.1:8765")
        self.assertEqual(allowed_web_origin("http://127.0.0.1:8767"), "http://127.0.0.1:8767")
        self.assertEqual(allowed_web_origin("http://localhost:8767"), "http://localhost:8767")
        self.assertEqual(allowed_web_origin("http://[::1]:8767"), "http://[::1]:8767")
        self.assertEqual(allowed_web_origin("https://127.0.0.1:8767"), "")
        self.assertEqual(allowed_web_origin("http://127.0.0.1:8767/path"), "")
        self.assertEqual(allowed_web_origin("http://127.0.0.1"), "")
        self.assertEqual(allowed_web_origin("http://127.0.0.1:99999"), "")
        self.assertEqual(allowed_web_origin("https://example.invalid"), "")
        self.assertEqual(payload_to_query({"enabled": True, "params": {"fast": 20}, "empty": None}), {
            "enabled": "true",
            "params": '{"fast": 20}',
        })








    def test_mutation_journal_replays_same_request_and_rejects_key_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            journal = MutationJournal(db_path=Path(temp_dir) / "mutations.sqlite3", now_ms=lambda: 36)
            payload = {"symbol": "AAPL", "side": "BUY", "idempotencyKey": "mutation-key-1"}

            first = journal.begin("/api/paper/manual-order", "mutation-key-1", payload)
            journal.complete("mutation-key-1", 200, {"ok": True, "order_id": "paper-1"})
            replay = journal.begin("/api/paper/manual-order", "mutation-key-1", payload)
            conflict = journal.begin(
                "/api/paper/manual-order",
                "mutation-key-1",
                {**payload, "side": "SELL"},
            )
            oversized = journal.begin(
                "/api/paper/manual-order",
                "x" * 161,
                payload,
            )

            self.assertEqual(first["status"], "NEW")
            self.assertEqual(replay["status"], "REPLAY")
            self.assertEqual(replay["response"]["order_id"], "paper-1")
            self.assertEqual(conflict["status"], "CONFLICT")
            self.assertEqual(oversized["status"], "INVALID")

    def test_read_only_get_contract_blocks_hidden_mutations(self) -> None:
        self.assertTrue(read_only_get_mutation_requested(
            "/api/stocks/history-prewarm",
            {"start": "true"},
        ))
        self.assertTrue(read_only_get_mutation_requested(
            "/api/market/anomaly-radar",
            {"force": "1"},
        ))
        self.assertTrue(read_only_get_mutation_requested(
            "/api/market/anomaly-radar",
            {"notify": "yes"},
        ))
        self.assertTrue(read_only_get_mutation_requested(
            "/api/market/insights",
            {"notify": "true"},
        ))
        self.assertTrue(read_only_get_mutation_requested(
            "/api/market/scanner",
            {"notify": "on"},
        ))
        self.assertFalse(read_only_get_mutation_requested(
            "/api/market/anomaly-radar",
            {"force": "false", "notify": "off"},
        ))
        self.assertFalse(read_only_get_mutation_requested("/api/health", {}))

    def test_force_get_contract_requires_trusted_local_origin(self) -> None:
        path = "/api/market/snapshot"
        query = {"force": "true"}

        self.assertFalse(trusted_refresh_get_allowed(
            path,
            query,
            client_host="127.0.0.1",
            origin="https://attacker.invalid",
        ))
        self.assertFalse(trusted_refresh_get_allowed(
            path,
            query,
            client_host="192.0.2.10",
            origin=None,
        ))
        self.assertTrue(trusted_refresh_get_allowed(
            path,
            query,
            client_host="127.0.0.1",
            origin="http://127.0.0.1:8765",
        ))
        self.assertTrue(trusted_refresh_get_allowed(
            path,
            {"emit": "1"},
            client_host="::1",
            origin=None,
        ))
        self.assertFalse(trusted_refresh_get_allowed(
            path,
            query,
            client_host="127.0.0.1",
            origin=None,
            sec_fetch_site="cross-site",
        ))
        self.assertTrue(trusted_refresh_get_allowed(
            path,
            query,
            client_host="127.0.0.1",
            origin=None,
            sec_fetch_site="same-origin",
        ))
        self.assertTrue(trusted_refresh_get_allowed(
            path,
            {"force": "false"},
            client_host="127.0.0.1",
            origin="https://attacker.invalid",
        ))

    def test_strategy_pipeline_requires_backtest_and_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StrategyPipeline(db_path=Path(temp_dir) / "pipeline.sqlite3", now_ms=lambda: 40)
            run = service.define(strategy_id="dual_ma", symbol="BTC-USDT", params={"fast": 20, "slow": 60}, code_fingerprint="code-v1")
            same_version = service.define(strategy_id="dual_ma", symbol="MSFT", params={"slow": 60, "fast": 20}, code_fingerprint="code-v1")
            changed_version = service.define(strategy_id="dual_ma", symbol="BTC-USDT", params={"fast": 21, "slow": 60}, code_fingerprint="code-v1")
            self.assertEqual(run["strategy_version_id"], same_version["strategy_version_id"])
            self.assertNotEqual(run["strategy_version_id"], changed_version["strategy_version_id"])
            self.assertEqual(service.get_version(run["strategy_version_id"])["spec"]["params"]["fast"], 20)
            blocked = service.authorize_paper(run["run_id"])
            self.assertFalse(blocked["paper_authorized"])
            service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "reproducibility": {
                    "symbol": "BTC-USDT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {"fast": 20, "slow": 60},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "run-hash-1",
                    "data_hash": TEST_STRATEGY_DATA_HASH,
                    "param_hash": "param-hash-1",
                },
                "temporal_validation": {
                    "status": "PASS",
                    "data_split": {"status": "PASS"},
                    "walk_forward": {"status": "PASS"},
                    "cost_sensitivity": {"status": "PASS"},
                },
                "selection_evidence": {"status": "PASS", "batch_run_hash": "matrix-1"},
                "data_admission": passing_strategy_data_admission("BTC-USDT", 40),
                "current": {"trade_count": 12},
            })
            service.record_doctor(run["run_id"], {
                "ok": True,
                "score": 75,
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
            })
            drifted = service.authorize_paper(
                run["run_id"],
                requested_params={"fast": 21, "slow": 60},
                execution_profile=validated_paper_profile(),
            )
            self.assertFalse(drifted["paper_authorized"])
            self.assertIn("paper_parameter_binding", drifted["stages"]["paper_authorization"]["blockers"])
            unvalidated_exit = service.authorize_paper(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(trailing_stop_enabled=True),
            )
            self.assertFalse(unvalidated_exit["paper_authorized"])
            self.assertIn("trailing_stop_enabled", unvalidated_exit["paper_request_binding"]["profile_mismatches"])
            preview = service.preview_paper_authorization(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(),
            )
            self.assertTrue(preview["paper_authorized"])
            self.assertTrue(preview["paper_authorization_preview"])
            persisted_before_commit = service.get(run["run_id"])
            self.assertFalse(persisted_before_commit["paper_authorized"])
            self.assertNotIn("paper_authorization_preview", persisted_before_commit)
            ready = service.authorize_paper(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(),
            )
            self.assertTrue(ready["paper_authorized"])
            self.assertEqual(ready["paper_request_binding"]["status"], "PASS")
            artifact = service.get_backtest_artifact(run["run_id"])
            self.assertEqual(artifact["integrity_status"], "PASS")
            self.assertEqual(artifact["payload"]["strategy_version_id"], run["strategy_version_id"])
            self.assertFalse(artifact["payload"]["live_order_allowed"])
            paper_run = service.record_paper_run(run["run_id"], {"armed": True, "equity": 10_100, "orders": []})
            self.assertEqual(paper_run["status"], "PAPER_RUNNING")
            self.assertFalse(paper_run["live_order_allowed"])
            self.assertEqual(service.snapshot()["version_count"], 2)

    def test_legacy_strategy_runs_are_publicly_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StrategyPipeline(db_path=Path(temp_dir) / "pipeline.sqlite3", now_ms=lambda: 41)
            service._save({
                "run_id": "legacy-run",
                "strategy_id": "dual_ma",
                "symbol": "AAPL",
                "status": "VALIDATED",
                "current_stage": "doctor",
                "created_at": 1,
                "updated_at": 1,
                "stages": {
                    "definition": {"status": "PASS"},
                    "backtest": {"status": "PASS"},
                    "doctor": {"status": "PASS"},
                    "paper_authorization": {"status": "PASS"},
                },
                "backtest": {"ok": True},
                "paper_authorized": True,
                "live_order_allowed": False,
            })

            snapshot = service.snapshot()

            self.assertEqual(snapshot["latest"]["status"], "LEGACY_BLOCKED")
            self.assertFalse(snapshot["latest"]["paper_authorized"])
            self.assertIn("immutable_strategy_version", snapshot["latest"]["legacy_blockers"])
            self.assertIn("temporal_validation", snapshot["latest"]["legacy_blockers"])

    def test_current_strategy_validation_failure_is_not_mislabeled_as_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StrategyPipeline(db_path=Path(temp_dir) / "pipeline.sqlite3", now_ms=lambda: 42)
            run = service.define(strategy_id="dual_ma", symbol="BTC-USDT", params={}, code_fingerprint="code-v1")
            service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "temporal_validation": {"status": "PASS"},
                "selection_evidence": {"status": "BLOCK", "blockers": ["no_strategy_matrix_report"]},
                "reproducibility": {
                    "symbol": "BTC-USDT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "current-run",
                    "data_hash": TEST_STRATEGY_DATA_HASH,
                    "param_hash": "current-params",
                },
                "data_admission": passing_strategy_data_admission("BTC-USDT", 42),
            })

            snapshot = service.snapshot()

            self.assertEqual(snapshot["latest"]["status"], "VALIDATION_BLOCKED")
            self.assertNotIn("legacy_blockers", snapshot["latest"])
            self.assertIn("independent_selection_evidence", snapshot["latest"]["validation_blockers"])
            self.assertEqual(snapshot["latest"]["stages"]["backtest"]["status"], "BLOCK")

    def test_strategy_pipeline_rechecks_frozen_dataset_freshness_before_paper_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clock = {"now": 100}
            service = StrategyPipeline(
                db_path=Path(temp_dir) / "pipeline.sqlite3",
                now_ms=lambda: clock["now"],
            )
            run = service.define(strategy_id="dual_ma", symbol="BTC-USDT", params={}, code_fingerprint="code-v1")
            service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "temporal_validation": {"status": "PASS"},
                "selection_evidence": {"status": "PASS", "batch_run_hash": "matrix-freshness"},
                "data_admission": passing_strategy_data_admission("BTC-USDT", 100),
                "reproducibility": {
                    "symbol": "BTC-USDT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "run-freshness",
                    "data_hash": TEST_STRATEGY_DATA_HASH,
                    "param_hash": "params-freshness",
                },
            })
            service.record_doctor(run["run_id"], {
                "ok": True,
                "score": 80,
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
            })
            clock["now"] += 5 * 86_400_000

            snapshot = service.snapshot()["latest"]
            blocked = service.authorize_paper(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(),
            )

            self.assertEqual(snapshot["status"], "VALIDATION_BLOCKED")
            self.assertIn("strategy_data_admission", snapshot["validation_blockers"])
            self.assertFalse(blocked["paper_authorized"])
            self.assertIn("strategy_data_admission", blocked["stages"]["paper_authorization"]["blockers"])

    def test_strategy_pipeline_rejects_a_report_bound_to_another_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StrategyPipeline(db_path=Path(temp_dir) / "pipeline.sqlite3", now_ms=lambda: 42)
            run = service.define(strategy_id="dual_ma", symbol="AAPL", params={}, code_fingerprint="code-v1")
            rejected = service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "temporal_validation": {"status": "PASS"},
                "selection_evidence": {"status": "PASS", "batch_run_hash": "matrix-2"},
                "reproducibility": {
                    "symbol": "MSFT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "wrong-symbol-run",
                    "data_hash": "data-hash",
                    "param_hash": "param-hash",
                },
            })

            self.assertEqual(rejected["backtest"]["binding"]["status"], "BLOCK")
            self.assertIn("symbol_mismatch", rejected["backtest"]["binding"]["blockers"])
            self.assertEqual(rejected["stages"]["backtest"]["status"], "BLOCK")
            self.assertFalse(service.authorize_paper(run["run_id"])["paper_authorized"])

    def test_strategy_temporal_validation_helpers_enforce_real_splits(self) -> None:
        rows = [{"date": f"d-{index}"} for index in range(600)]
        split = temporal_data_split(rows)
        folds = chronological_folds(rows)
        walk = summarize_walk_forward([
            {"ok": True, "total_return_pct": 3, "max_drawdown_pct": 5, "trade_count": 3},
            {"ok": True, "total_return_pct": 2, "max_drawdown_pct": 6, "trade_count": 3},
            {"ok": True, "total_return_pct": -1, "max_drawdown_pct": 7, "trade_count": 2},
        ])
        costs = summarize_cost_sensitivity(
            {"total_return_pct": 10},
            [
                {"ok": True, "total_return_pct": 9, "max_drawdown_pct": 5},
                {"ok": True, "total_return_pct": 7, "max_drawdown_pct": 7},
            ],
        )

        self.assertEqual(split["status"], "PASS")
        self.assertEqual([split["segments"][name]["count"] for name in ("train", "validation", "test")], [360, 120, 120])
        self.assertEqual(folds["status"], "PASS")
        self.assertEqual(walk["status"], "PASS")
        self.assertEqual(walk["evaluation_mode"], "FIXED_PARAMETER_CHRONOLOGICAL_SLICES")
        self.assertFalse(walk["parameters_refit_per_fold"])
        self.assertFalse(walk["walk_forward_optimization_claim_allowed"])
        self.assertEqual(costs["status"], "PASS")
        self.assertTrue(costs["break_even_preserved"])

        fragile_costs = summarize_cost_sensitivity(
            {"total_return_pct": 3},
            [
                {"ok": True, "total_return_pct": 1, "max_drawdown_pct": 5},
                {"ok": True, "total_return_pct": -1, "max_drawdown_pct": 7},
            ],
        )
        self.assertEqual(fragile_costs["status"], "BLOCK")
        self.assertFalse(fragile_costs["break_even_preserved"])
        self.assertTrue(any("未保持正值" in item for item in fragile_costs["blockers"]))

        incomplete_costs = summarize_cost_sensitivity(
            {"total_return_pct": "not-a-number"},
            [{"ok": True, "total_return_pct": None, "max_drawdown_pct": 5}],
        )
        self.assertEqual(incomplete_costs["status"], "BLOCK")
        self.assertIsNone(incomplete_costs["baseline_return_pct"])
        self.assertIsNone(incomplete_costs["worst_return_pct"])
        self.assertIsNone(incomplete_costs["break_even_preserved"])
        self.assertTrue(any("基准收益缺失" in item for item in incomplete_costs["blockers"]))
        self.assertTrue(any("收益或回撤缺失" in item for item in incomplete_costs["blockers"]))

        incomplete_walk = summarize_walk_forward([
            {"ok": True, "total_return_pct": None, "max_drawdown_pct": 5, "trade_count": 3},
            {"ok": True, "total_return_pct": 1, "max_drawdown_pct": float("nan"), "trade_count": "3"},
            {"ok": False, "total_return_pct": 4, "max_drawdown_pct": 4, "trade_count": 2},
        ])
        self.assertEqual(incomplete_walk["status"], "BLOCK")
        self.assertIsNone(incomplete_walk["total_trades"])
        self.assertIsNone(incomplete_walk["worst_drawdown_pct"])
        self.assertTrue(any("可用时间折叠" in item for item in incomplete_walk["blockers"]))

    def test_strategy_forward_graduation_requires_samples_duration_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            clock = {"now": 100}
            service = StrategyPipeline(
                db_path=Path(temp_dir) / "pipeline.sqlite3",
                now_ms=lambda: clock["now"],
                minimum_forward_duration_ms=1_000,
                minimum_forward_closed_trades=2,
                maximum_forward_drawdown_pct=10,
            )
            run = service.define(strategy_id="dual_ma", symbol="BTC-USDT", code_fingerprint="code-v1")
            service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "reproducibility": {
                    "symbol": "BTC-USDT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "run-hash-2",
                    "data_hash": TEST_STRATEGY_DATA_HASH,
                    "param_hash": "param-hash-2",
                },
                "temporal_validation": {"status": "PASS"},
                "selection_evidence": {"status": "PASS", "batch_run_hash": "matrix-3"},
                "data_admission": passing_strategy_data_admission("BTC-USDT", 100),
            })
            service.record_doctor(run["run_id"], {"ok": True, "score": 80, "lookahead_check": {"status": "PASS"}})
            service.authorize_paper(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(),
            )
            running = service.record_paper_run(run["run_id"], {
                "armed": True,
                "equity": 10_000,
                "drawdown_pct": 0,
                "ledger_metrics": {"order_count": 0, "filled_order_count": 0, "closed_trade_count": 0},
            })
            blocked_review = service.review_paper_run(run["run_id"], decision="APPROVE", reviewer="tester")
            self.assertEqual(running["status"], "PAPER_RUNNING")
            self.assertFalse(blocked_review["validation_complete"])

            clock["now"] = 1_200
            eligible = service.record_paper_run(run["run_id"], {
                "armed": False,
                "equity": 10_200,
                "drawdown_pct": 4,
                "ledger_metrics": {"order_count": 4, "filled_order_count": 4, "closed_trade_count": 2},
            })
            approved = service.review_paper_run(run["run_id"], decision="APPROVE", reviewer="tester", notes="Evidence reviewed.")

            self.assertTrue(eligible["forward_graduation"]["eligible_for_audit"])
            self.assertEqual(approved["status"], "PAPER_VALIDATED")
            self.assertTrue(approved["validation_complete"])
            self.assertFalse(approved["live_order_allowed"])

    def test_strategy_pipeline_blocks_paper_without_independent_matrix_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = StrategyPipeline(db_path=Path(temp_dir) / "pipeline.sqlite3", now_ms=lambda: 43)
            run = service.define(strategy_id="dual_ma", symbol="BTC-USDT", params={}, code_fingerprint="code-v1")
            service.record_backtest(run["run_id"], {
                "ok": True,
                "acceptance": {"status": "PASS"},
                "lookahead_check": {"status": "PASS", "prefix_invariance": {"status": "PASS"}},
                "temporal_validation": {"status": "PASS"},
                "reproducibility": {
                    "symbol": "BTC-USDT",
                    "strategy_id": "dual_ma",
                    "strategy_fingerprint": "code-v1",
                    "params": {},
                    "dataset_status": "PASS",
                    "hash_scope": "FULL_OHLCV",
                    "execution_model": EXECUTION_MODEL_VERSION,
                    "run_hash": "run-hash-missing-matrix",
                    "data_hash": TEST_STRATEGY_DATA_HASH,
                    "param_hash": "param-hash-missing-matrix",
                },
                "data_admission": passing_strategy_data_admission("BTC-USDT", 43),
            })
            service.record_doctor(run["run_id"], {
                "ok": True,
                "score": 80,
                "lookahead_check": {"status": "PASS"},
            })

            blocked = service.authorize_paper(
                run["run_id"],
                requested_params=run["params"],
                execution_profile=validated_paper_profile(),
            )

            self.assertFalse(blocked["paper_authorized"])
            self.assertIn(
                "independent_selection_evidence",
                blocked["stages"]["paper_authorization"]["blockers"],
            )

    def test_research_bridge_rejects_execution_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ResearchBridge(db_path=Path(temp_dir) / "research.sqlite3", now_ms=lambda: 50)
            rejected = service.import_summary({
                "research_only": True, "symbol": "AAPL", "timeframe": "1D", "side": "BUY",
            })
            accepted = service.import_summary({
                "research_only": True,
                "symbol": "AAPL",
                "timeframe": "1D",
                "thesis": "Daily trend remains constructive.",
                "evidence": ["Volume expanded."],
                "counter_evidence": ["Resistance remains overhead."],
            })
            self.assertFalse(rejected["ok"])
            self.assertTrue(accepted["ok"])
            self.assertFalse(accepted["summary"]["live_order_allowed"])
            self.assertEqual(len(service.list("AAPL")), 1)

    def test_research_bridge_negotiates_schema_and_replays_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ResearchBridge(db_path=Path(temp_dir) / "research.sqlite3", now_ms=lambda: 50)
            contract = service.schema()
            self.assertEqual(contract["version"], "1.1")
            self.assertEqual(contract["supported_versions"], ["1.0", "1.1"])
            self.assertEqual(len(contract["contract_hash"]), 64)

            payload = {
                "schema_version": "1.1",
                "idempotency_key": "brief-AAPL-001",
                "research_only": True,
                "symbol": "AAPL",
                "timeframe": "1D",
                "thesis": "Daily trend remains constructive.",
                "evidence": ["Volume expanded."],
                "counter_evidence": ["Resistance remains overhead."],
            }
            imported = service.import_summary(payload)
            replayed = service.import_summary(dict(payload))
            conflicted = service.import_summary({
                **payload,
                "thesis": "A different thesis must not overwrite the first brief.",
            })

            self.assertEqual(imported["status"], "IMPORTED")
            self.assertEqual(replayed["status"], "IDEMPOTENT_REPLAY")
            self.assertEqual(replayed["summary"]["summary_id"], imported["summary"]["summary_id"])
            self.assertEqual(conflicted["status"], "IDEMPOTENCY_CONFLICT")
            self.assertEqual(len(service.list("AAPL")), 1)
            self.assertEqual(imported["summary"]["schema_version"], "1.1")
            self.assertEqual(len(imported["summary"]["payload_hash"]), 64)

            unsupported = service.validate({**payload, "schema_version": "9.9"})
            self.assertFalse(unsupported["ok"])
            self.assertIn("Unsupported ResearchBrief schema version", unsupported["errors"][0])

    def test_market_data_truth_is_unknown_without_snapshot_and_does_not_fetch(self) -> None:
        calls = {"quote": 0, "candles": 0}

        def quote(*_args, **_kwargs) -> dict[str, object]:
            calls["quote"] += 1
            raise AssertionError("truth inspection must not fetch a quote")

        def candles(*_args, **_kwargs) -> dict[str, object]:
            calls["candles"] += 1
            raise AssertionError("truth inspection must not fetch candles")

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=quote,
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=candles,
            okx_first=lambda *_args: {},
        )

        truth = service.data_truth("AAPL", bar="1Dutc", session="regular")
        health = service.health("AAPL", bar="1Dutc", session="regular")

        self.assertEqual(calls, {"quote": 0, "candles": 0})
        self.assertEqual(truth["status"], "UNKNOWN")
        self.assertEqual(truth["mode"], "UNOBSERVED")
        self.assertFalse(truth["analysis_ready"])
        self.assertTrue(health["service_ok"])
        self.assertEqual(health["ok_scope"], "SERVICE_OPERATIONAL_ONLY")
        self.assertEqual(health["status"], "UNKNOWN")

    def test_market_data_truth_reports_realtime_sources_and_completed_bar(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1m",
                "rows": [
                    {"ts": 99_000, "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10, "complete": True},
                    {"ts": 100_000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 5, "complete": False},
                ],
                "source": "okx_realtime_candles",
                "latest_ts": 100_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=lambda *_args: {
                "last": "99.987654321098765432109876543",
                "bidPx": "100.12",
                "askPx": "100.123456789012345678901234567",
                "askSz": "0.765432109876543210987654321",
                "open24h": "95", "high24h": "102", "low24h": "94", "ts": "99000",
            },
        )

        service.snapshot("BTC-USDT", bar="1m", session="all")
        truth = service.data_truth("BTC-USDT", bar="1m", session="all")

        self.assertEqual(truth["status"], "READY")
        self.assertEqual(truth["mode"], "REALTIME_READY")
        self.assertEqual(truth["quote"]["source"], "okx")
        self.assertEqual(truth["quote"]["reference_price"]["status"], "PASS")
        self.assertEqual(truth["quote"]["reference_price"]["value"], "99.987654321098765432109876543")
        self.assertFalse(truth["quote"]["reference_price"]["client_price_used"])
        self.assertEqual(truth["quote"]["sizing_reference"]["status"], "PASS")
        self.assertEqual(truth["quote"]["sizing_reference"]["value"], "100.123456789012345678901234567")
        self.assertEqual(truth["quote"]["sizing_reference"]["available_size"], "0.765432109876543210987654321")
        self.assertFalse(truth["quote"]["sizing_reference"]["is_executable_quote"])
        self.assertEqual(truth["candles"]["source"], "okx_realtime_candles")
        self.assertEqual(truth["candles"]["last_completed_ts"], 99_000)
        self.assertEqual(truth["candles"]["completed_count"], 1)
        self.assertNotIn("rows", truth["candles"])
        self.assertTrue(truth["realtime_ready"])
        self.assertFalse(truth["execution_usable"])
        self.assertFalse(truth["live_order_allowed"])

    def test_market_data_truth_blocks_quarantined_fallback(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: {
                "source": "stock_sqlite_cache",
                "status": "CACHE",
                "last": 200,
                "ts": 99_000,
                "quote_quality": {
                    "status": "REVIEW",
                    "fallback": True,
                    "quarantined": True,
                    "quarantine_reasons": ["复权待核"],
                },
                "market_session": {
                    "status": "LAST_SESSION",
                    "phase": "closed",
                    "is_open": False,
                    "provider_confirmed": True,
                    "analysis_ready": True,
                },
            },
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "日线"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [
                    {"ts": 99_000, "open": 198, "high": 202, "low": 197, "close": 200, "volume": 10, "complete": True},
                ],
                "source": "stock_sqlite_cache",
                "realtime": False,
                "fallback": True,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=lambda *_args: {},
        )

        service.snapshot("AAPL", bar="1d", session="regular")
        truth = service.data_truth("AAPL", bar="1Dutc", session="regular")

        self.assertEqual(truth["status"], "BLOCK")
        self.assertEqual(truth["mode"], "REVIEW")
        self.assertFalse(truth["analysis_ready"])
        self.assertFalse(truth["research_usable"])
        self.assertFalse(truth["paper_authorized"])
        self.assertFalse(truth["live_order_allowed"])

    def test_market_data_truth_never_promotes_invalid_or_stale_timestamps(self) -> None:
        now = 1_000_000

        def truth_for(*, quote_ts: int, candle_ts: int, candle_age_ms: int) -> dict[str, object]:
            service = MarketDataService(
                now_ms=lambda: now,
                pct=lambda value, *_args: float(value or 0),
                is_stock_symbol=lambda _symbol: False,
                read_stock_quote=lambda *_args, **_kwargs: {},
                stock_data_sources_snapshot=lambda *_args: {},
                market_chart_candles=lambda *_args: {},
                okx_first=lambda *_args: {},
            )
            service.cache["crypto:BTC-USDT:1m:all:300:0"] = {
                "time": now,
                "payload": {
                    "ok": True,
                    "symbol": "BTC-USDT",
                    "asset_type": "crypto",
                    "bar": "1m",
                    "session": "all",
                    "quote": {"source": "okx", "status": "ONLINE", "last": 100, "ts": quote_ts},
                    "candles": {
                        "ok": True,
                        "bar": "1m",
                        "rows": [{"ts": candle_ts, "close": 100, "complete": True}],
                        "source": "okx_realtime_candles",
                        "latest_ts": candle_ts,
                        "data_age_ms": candle_age_ms,
                        "realtime": True,
                        "fallback": False,
                        "data_revision_evidence": {"status": "PASS"},
                    },
                    "data_quality": {
                        "status": "READY", "realtime": True, "fallback": False,
                        "warnings": [], "quarantined": False,
                    },
                    "context": {"snapshot_id": "timestamp-boundary"},
                    "updated_at": now,
                },
            }
            return service.data_truth("BTC-USDT", bar="1m", session="all")

        stale = truth_for(quote_ts=999_000, candle_ts=100_000, candle_age_ms=900_000)
        future = truth_for(quote_ts=2_000_000, candle_ts=999_000, candle_age_ms=1_000)
        invalid = truth_for(quote_ts=999_000, candle_ts=0, candle_age_ms=1_000)

        self.assertEqual((stale["status"], stale["mode"]), ("STALE", "STALE"))
        self.assertFalse(stale["candles"]["current"])
        self.assertEqual(stale["quote"]["reference_price"]["status"], "NOT_CHECKED")
        self.assertEqual(future["status"], "BLOCK")
        self.assertFalse(future["quote"]["timestamp_valid"])
        self.assertEqual(future["quote"]["reference_price"]["status"], "NOT_CHECKED")
        self.assertNotEqual(invalid["status"], "READY")
        self.assertEqual(invalid["candles"]["last_completed_ts"], 0)

    def test_market_data_truth_rejects_regressed_public_best_ask(self) -> None:
        calls = {"quote": 0}

        def ticker(*_args: object) -> dict[str, str]:
            calls["quote"] += 1
            timestamp = "100000" if calls["quote"] == 1 else "99000"
            return {
                "last": "100",
                "bidPx": "99.9",
                "askPx": "100.1",
                "askSz": "1",
                "open24h": "95",
                "ts": timestamp,
            }

        service = MarketDataService(
            now_ms=lambda: 101_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1m",
                "rows": [{
                    "ts": 100_000,
                    "open": 99,
                    "high": 101,
                    "low": 98,
                    "close": 100,
                    "volume": 10,
                    "complete": True,
                }],
                "source": "okx_realtime_candles",
                "latest_ts": 100_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=ticker,
        )

        first = service.snapshot("BTC-USDT", bar="1m", session="all")
        regressed = service.snapshot("BTC-USDT", bar="1m", session="all", force=True)
        truth = service.data_truth("BTC-USDT", bar="1m", session="all")

        self.assertEqual(first["quote"]["cache_regression"], False)
        self.assertEqual(regressed["quote"]["cache_regression"], True)
        self.assertNotEqual(truth["status"], "READY")
        self.assertEqual(truth["quote"]["sizing_reference"]["status"], "BLOCK")
        self.assertTrue(truth["quote"]["sizing_reference"]["cache_regression"])

    def test_market_data_truth_blocks_crossed_public_best_ask(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1m",
                "rows": [{
                    "ts": 99_000,
                    "open": 99,
                    "high": 101,
                    "low": 98,
                    "close": 100,
                    "volume": 10,
                    "complete": True,
                }],
                "source": "okx_realtime_candles",
                "latest_ts": 99_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=lambda *_args: {
                "last": "100",
                "bidPx": "101",
                "askPx": "100",
                "askSz": "1",
                "open24h": "95",
                "ts": "99000",
            },
        )

        service.snapshot("BTC-USDT", bar="1m", session="all")
        truth = service.data_truth("BTC-USDT", bar="1m", session="all")

        self.assertEqual(truth["quote"]["sizing_reference"]["status"], "BLOCK")
        self.assertEqual(truth["quote"]["sizing_reference"]["value"], "")
        self.assertFalse(truth["execution_usable"])

    def test_quote_batch_preserves_newer_quote_on_timestamp_regression(self) -> None:
        calls = {"bulk": 0, "single": 0}

        def crypto_quotes() -> list[dict[str, str]]:
            calls["bulk"] += 1
            timestamp = "100000" if calls["bulk"] == 1 else "99000"
            return [{
                "instId": "BTC-USDT",
                "last": "100",
                "bidPx": "99.9",
                "askPx": "100.1",
                "askSz": "1",
                "open24h": "95",
                "ts": timestamp,
            }]

        def single_quote(*_args: object) -> dict[str, object]:
            calls["single"] += 1
            return {}

        service = MarketDataService(
            now_ms=lambda: 101_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1m",
                "rows": [{"ts": 100_000, "close": 100, "complete": True}],
                "source": "okx_realtime_candles",
                "latest_ts": 100_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=single_quote,
            read_crypto_quotes=crypto_quotes,
        )

        first = service.quote_batch(["BTC-USDT"], force=True)
        regressed = service.quote_batch(["BTC-USDT"], force=True)
        snapshot = service.snapshot("BTC-USDT", bar="1m", session="all")
        truth = service.data_truth("BTC-USDT", bar="1m", session="all")

        self.assertEqual(calls, {"bulk": 2, "single": 0})
        self.assertEqual(first["rows"][0]["ts"], 100000)
        self.assertEqual(regressed["rows"][0]["ts"], 100000)
        self.assertTrue(regressed["rows"][0]["cache_regression"])
        self.assertTrue(snapshot["context"]["quote_cache_hit"])
        self.assertTrue(snapshot["quote"]["cache_regression"])
        self.assertEqual(truth["quote"]["sizing_reference"]["status"], "BLOCK")

    def test_market_snapshot_singleflight_deduplicates_same_symbol(self) -> None:
        calls = {"quote": 0, "candles": 0}
        counter_lock = threading.Lock()

        def okx_first(_path: str, _query: dict[str, str]) -> dict[str, str]:
            with counter_lock:
                calls["quote"] += 1
            return {"last": "100", "open24h": "95", "high24h": "102", "low24h": "94"}

        def candles(*_args) -> dict[str, object]:
            with counter_lock:
                calls["candles"] += 1
            time.sleep(0.03)
            return {
                "ok": True,
                "bar": "1m",
                "rows": [{"ts": 1, "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10}],
                "source": "okx_realtime_candles",
                "latest_ts": 1,
                "realtime": True,
                "fallback": False,
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=candles,
            okx_first=okx_first,
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(lambda _index: service.snapshot("BTC-USDT", bar="1m"), range(8)))
        self.assertEqual(calls, {"quote": 1, "candles": 1})
        self.assertTrue(all(row["ok"] for row in rows))
        self.assertEqual(sum(bool(row["cached"]) for row in rows), 7)

    def test_market_snapshot_force_singleflight_uses_canonical_identity(self) -> None:
        calls = {"quote": 0, "candles": 0}
        counter_lock = threading.Lock()
        start_barrier = threading.Barrier(8)

        def stock_quote(*_args, **_kwargs) -> dict[str, object]:
            with counter_lock:
                calls["quote"] += 1
            time.sleep(0.05)
            return {
                "source": "futu",
                "status": "ONLINE",
                "last": 200,
                "ts": 99_000,
                "quote_quality": {"status": "READY", "fallback": False},
                "market_session": {
                    "status": "LIVE_SESSION",
                    "phase": "regular",
                    "is_open": True,
                    "analysis_ready": True,
                    "provider_confirmed": True,
                },
            }

        def candles(*_args) -> dict[str, object]:
            with counter_lock:
                calls["candles"] += 1
            return {
                "ok": True,
                "bar": "1d",
                "rows": [{"ts": 99_000, "open": 198, "high": 202, "low": 197, "close": 200, "volume": 10}],
                "source": "futu",
                "latest_ts": 99_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda symbol: symbol == "AAPL",
            read_stock_quote=stock_quote,
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "regular"},
            market_chart_candles=candles,
            okx_first=lambda *_args: {},
        )

        def request(index: int) -> dict[str, object]:
            start_barrier.wait()
            return service.snapshot(
                " aapl " if index % 2 else "AAPL",
                bar="1d" if index % 2 else "1D",
                session="ALL" if index % 2 else "all",
                fast=bool(index % 2),
                force=True,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(request, range(8)))

        self.assertEqual(calls, {"quote": 1, "candles": 1})
        self.assertEqual({row["context"]["refresh_generation"] for row in rows}, {1})
        self.assertEqual(sum(bool(row["context"]["force_coalesced"]) for row in rows), 7)
        self.assertTrue(all(row["symbol"] == "AAPL" and row["bar"] == "1d" for row in rows))

    def test_forced_snapshot_failure_preserves_last_good_quote(self) -> None:
        calls = {"quote": 0}

        def stock_quote(*_args, **_kwargs) -> dict[str, object]:
            calls["quote"] += 1
            if calls["quote"] == 1:
                return {
                    "source": "futu",
                    "status": "ONLINE",
                    "last": 200,
                    "ts": 99_000,
                    "quote_quality": {"status": "READY", "fallback": False},
                    "market_session": {
                        "status": "LIVE_SESSION",
                        "phase": "regular",
                        "is_open": True,
                        "analysis_ready": True,
                        "provider_confirmed": True,
                    },
                }
            return {
                "source": "offline-seed",
                "status": "OFFLINE",
                "last": 0,
                "ts": 100_000,
                "warning": "provider unavailable",
                "quote_quality": {"status": "DEGRADED", "fallback": True},
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda symbol: symbol == "AAPL",
            read_stock_quote=stock_quote,
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "regular"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [{"ts": 99_000, "open": 198, "high": 202, "low": 197, "close": 200, "volume": 10}],
                "source": "futu",
                "latest_ts": 99_000,
                "realtime": True,
                "fallback": False,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=lambda *_args: {},
        )

        initial = service.snapshot("AAPL", bar="1d")
        failed = service.snapshot(" aapl ", bar="1D", session="ALL", force=True)
        cached = service.snapshot("AAPL", bar="1D")

        self.assertEqual(initial["data_quality"]["status"], "READY")
        self.assertEqual(calls["quote"], 2)
        self.assertEqual((failed["quote"]["source"], failed["quote"]["last"]), ("futu", 200.0))
        self.assertTrue(failed["quote"]["refresh_failed"])
        self.assertNotEqual(failed["data_quality"]["status"], "READY")
        self.assertEqual((cached["quote"]["source"], cached["quote"]["last"]), ("futu", 200.0))

    def test_market_snapshot_shares_quote_across_different_consumers_and_limits(self) -> None:
        calls = {"quote": 0, "candles": 0}

        def okx_first(_path: str, _query: dict[str, str]) -> dict[str, str]:
            calls["quote"] += 1
            return {"last": "100", "open24h": "95", "high24h": "102", "low24h": "94"}

        def candles(*_args) -> dict[str, object]:
            calls["candles"] += 1
            return {
                "ok": True,
                "bar": "1m",
                "rows": [{"ts": 1, "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10}],
                "source": "okx_realtime_candles",
                "latest_ts": 1,
                "realtime": True,
                "fallback": False,
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=candles,
            okx_first=okx_first,
        )

        chart = service.snapshot("BTC-USDT", bar="1m", limit=300, consumer="chart")
        research = service.snapshot("BTC-USDT", bar="1m", limit=500, consumer="research")
        chart_again = service.snapshot("BTC-USDT", bar="1m", limit=300, consumer="ai")
        health = service.health()

        self.assertEqual(calls, {"quote": 1, "candles": 2})
        self.assertFalse(chart["context"]["shared"])
        self.assertTrue(research["context"]["quote_cache_hit"])
        self.assertTrue(chart_again["context"]["snapshot_cache_hit"])
        self.assertEqual(chart_again["context"]["consumers"], ["ai", "chart", "research"])
        self.assertEqual(health["stats"]["upstream_quote_calls"], 1)
        self.assertEqual(health["stats"]["snapshot_cache_hits"], 1)

    def test_fast_stock_snapshot_uses_local_quote_without_upstream_wait(self) -> None:
        calls = {"local": 0, "upstream": 0}

        def local_quote(_symbol: str) -> dict[str, object]:
            calls["local"] += 1
            return {
                "source": "stock_sqlite_cache",
                "status": "CACHE",
                "last": 200,
                "ts": 50_000,
                "quote_quality": {"status": "STALE", "fallback": True},
            }

        def upstream_quote(*_args, **_kwargs) -> dict[str, object]:
            calls["upstream"] += 1
            return {
                "source": "futu",
                "status": "ONLINE",
                "last": 201,
                "ts": 99_000,
                "quote_quality": {"status": "READY", "fallback": False},
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=upstream_quote,
            read_fast_stock_quote=local_quote,
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "日线"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [{"ts": 50_000, "open": 198, "high": 202, "low": 197, "close": 200, "volume": 10}],
                "source": "stock_sqlite_cache",
                "realtime": False,
                "fallback": True,
                "data_revision_evidence": {"status": "PASS"},
            },
            okx_first=lambda *_args: {},
        )

        fast = service.snapshot("AAPL", bar="1d", fast=True)
        forced = service.snapshot("AAPL", bar="1d", fast=True, force=True)
        health = service.health()

        self.assertEqual(calls, {"local": 1, "upstream": 1})
        self.assertEqual(fast["quote"]["source"], "stock_sqlite_cache")
        self.assertEqual(fast["candles"]["data_revision_evidence"]["status"], "PASS")
        self.assertEqual(forced["quote"]["source"], "futu")
        self.assertEqual(health["stats"]["local_quote_reads"], 1)
        self.assertEqual(health["stats"]["upstream_quote_calls"], 1)

    def test_quote_batch_singleflight_prewarms_snapshot_quote_cache(self) -> None:
        calls = {"crypto_bulk": 0, "stock_bulk": 0, "single_quote": 0, "candles": 0}
        counter_lock = threading.Lock()

        def crypto_quotes() -> list[dict[str, str]]:
            with counter_lock:
                calls["crypto_bulk"] += 1
            time.sleep(0.03)
            return [{
                "instId": "BTC-USDT",
                "last": "100",
                "open24h": "95",
                "high24h": "102",
                "low24h": "94",
                "volCcy24h": "1000",
                "ts": "99000",
            }]

        def stock_quotes(_force: bool) -> list[dict[str, object]]:
            with counter_lock:
                calls["stock_bulk"] += 1
            return [{
                "symbol": "AAPL",
                "source": "futu",
                "status": "ONLINE",
                "last": 200,
                "open24h": 198,
                "high24h": 202,
                "low24h": 197,
                "change24h_pct": 1.01,
                "ts": 99_000,
            }]

        def okx_first(_path: str, _query: dict[str, str]) -> dict[str, str]:
            calls["single_quote"] += 1
            return {}

        def candles(*_args) -> dict[str, object]:
            calls["candles"] += 1
            return {
                "ok": True,
                "bar": "1m",
                "rows": [{"ts": 1, "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10}],
                "source": "okx_realtime_candles",
                "latest_ts": 1,
                "realtime": True,
                "fallback": False,
            }

        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda symbol: symbol == "AAPL",
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=candles,
            okx_first=okx_first,
            read_crypto_quotes=crypto_quotes,
            read_stock_quotes=stock_quotes,
        )

        with ThreadPoolExecutor(max_workers=8) as pool:
            batches = list(pool.map(
                lambda _index: service.quote_batch(["BTC-USDT", "AAPL"], consumer="anomaly_radar"),
                range(8),
            ))
        chart = service.snapshot("BTC-USDT", bar="1m", consumer="chart")
        health = service.health()

        self.assertEqual(calls, {"crypto_bulk": 1, "stock_bulk": 1, "single_quote": 0, "candles": 1})
        self.assertEqual(sum(bool(item.get("context", {}).get("cache_hit")) for item in batches), 7)
        self.assertTrue(chart["context"]["quote_cache_hit"])
        self.assertEqual(chart["context"]["consumers"], ["anomaly_radar", "chart"])
        self.assertEqual(health["stats"]["batch_requests"], 8)
        self.assertEqual(health["stats"]["batch_cache_hits"], 7)
        self.assertEqual(health["stats"]["batch_source_calls"], 2)

    def test_quote_batch_keeps_working_when_one_source_fails(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda symbol: symbol == "AAPL",
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {},
            okx_first=lambda *_args: {},
            read_crypto_quotes=lambda: (_ for _ in ()).throw(RuntimeError("OKX offline")),
            read_stock_quotes=lambda _force: [{"symbol": "AAPL", "source": "futu", "last": 200, "ts": 99_000}],
        )

        batch = service.quote_batch(["BTC-USDT", "AAPL"], consumer="anomaly_radar")

        self.assertTrue(batch["ok"])
        self.assertEqual([row["symbol"] for row in batch["rows"]], ["AAPL"])
        self.assertEqual(batch["missing_symbols"], ["BTC-USDT"])
        self.assertIn("okx_bulk: OKX offline", batch["source_errors"])
        self.assertFalse(batch["live_trading_allowed"])

    def test_quote_batch_marks_closed_futu_quote_as_last_session(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {},
            okx_first=lambda *_args: {},
            read_stock_quotes=lambda _force: [{
                "symbol": "AAPL",
                "source": "futu",
                "status": "ONLINE",
                "last": 200,
                "ts": 99_000,
                "quote_quality": {"status": "READY", "fallback": False},
                "market_session": {
                    "status": "LAST_SESSION",
                    "phase": "closed",
                    "is_open": False,
                    "provider_confirmed": True,
                },
            }],
        )

        row = service.quote_batch(["AAPL"], force=True)["rows"][0]

        self.assertEqual(row["data_quality"]["status"], "LAST_SESSION")
        self.assertEqual(row["data_quality"]["label"], "Futu最近时段")
        self.assertFalse(row["data_quality"]["realtime"])
        self.assertFalse(row["data_quality"]["priority_eligible"])

    def test_quote_batch_accepts_fresh_live_futu_quote(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {},
            okx_first=lambda *_args: {},
            read_stock_quotes=lambda _force: [{
                "symbol": "AAPL",
                "source": "futu",
                "status": "ONLINE",
                "last": 200,
                "ts": 99_000,
                "quote_quality": {"status": "READY", "fallback": False},
                "market_session": {
                    "status": "LIVE_SESSION",
                    "phase": "regular",
                    "is_open": True,
                    "provider_confirmed": True,
                },
            }],
        )

        row = service.quote_batch(["AAPL"], force=True)["rows"][0]

        self.assertEqual(row["data_quality"]["status"], "READY")
        self.assertEqual(row["data_quality"]["label"], "Futu实时")
        self.assertTrue(row["data_quality"]["realtime"])
        self.assertTrue(row["data_quality"]["priority_eligible"])

    def test_quote_batch_rejects_stale_okx_timestamp(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: False,
            read_stock_quote=lambda *_args, **_kwargs: {},
            stock_data_sources_snapshot=lambda *_args: {},
            market_chart_candles=lambda *_args: {},
            okx_first=lambda *_args: {},
            read_crypto_quotes=lambda: [{
                "symbol": "BTC-USDT",
                "source": "okx",
                "status": "ONLINE",
                "last": 60_000,
                "open24h": 59_000,
                "ts": 80_000,
            }],
        )

        row = service.quote_batch(["BTC-USDT"], force=True)["rows"][0]

        self.assertEqual(row["data_quality"]["status"], "STALE")
        self.assertFalse(row["data_quality"]["realtime"])
        self.assertFalse(row["data_quality"]["priority_eligible"])

    def test_stock_snapshot_preserves_quote_quality_and_timestamp(self) -> None:
        quote = {
            "source": "stock_sqlite_cache",
            "status": "CACHE",
            "last": 200,
            "open24h": 100,
            "high24h": 210,
            "low24h": 95,
            "change24h_pct": 100,
            "prevClose": 100,
            "change_basis": "local_previous_close",
            "ts": 50_000,
            "quote_quality": {
                "status": "REVIEW",
                "fallback": True,
                "quarantined": True,
                "warnings": ["旧缓存"],
                "quarantine_reasons": ["复权待核"],
            },
        }
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: quote,
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "盘中"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [{"ts": 50_000, "open": 100, "high": 210, "low": 95, "close": 200, "volume": 10}],
                "source": "stock_sqlite_cache",
                "realtime": False,
                "fallback": True,
            },
            okx_first=lambda *_args: {},
        )

        snapshot = service.snapshot("WDC", bar="1d")

        self.assertEqual(snapshot["quote"]["ts"], 50_000)
        self.assertEqual(snapshot["quote"]["prevClose"], 100)
        self.assertEqual(snapshot["quote"]["change_basis"], "local_previous_close")
        self.assertTrue(snapshot["data_quality"]["quarantined"])
        self.assertIn("复权待核", snapshot["data_quality"]["warnings"])

    def test_stock_snapshot_surfaces_candle_scale_break(self) -> None:
        service = MarketDataService(
            now_ms=lambda: 100_000,
            pct=lambda value, *_args: float(value or 0),
            is_stock_symbol=lambda _symbol: True,
            read_stock_quote=lambda *_args, **_kwargs: {
                "source": "futu",
                "status": "ONLINE",
                "last": 539,
                "prevClose": 582,
                "change24h_pct": -7.39,
                "ts": 99_000,
                "quote_quality": {"status": "READY", "quarantined": False},
            },
            stock_data_sources_snapshot=lambda *_args: {"ok": True, "session_label": "日线"},
            market_chart_candles=lambda *_args: {
                "ok": True,
                "bar": "1d",
                "rows": [
                    {"ts": 1, "open": 198, "high": 202, "low": 197, "close": 200, "volume": 10},
                    {"ts": 2, "open": 552, "high": 585, "low": 532, "close": 539, "volume": 20},
                ],
                "source": "futu",
                "realtime": False,
                "fallback": False,
                "warning": "日线价格尺度断点待核",
                "candle_quality": {
                    "status": "REVIEW",
                    "has_break": True,
                    "segment_start": 1,
                    "segment_rows": 1,
                    "total_rows": 2,
                    "warning": "日线价格尺度断点待核",
                },
            },
            okx_first=lambda *_args: {},
        )

        snapshot = service.snapshot("WDC", bar="1d")

        self.assertEqual(snapshot["candles"]["candle_quality"]["status"], "REVIEW")
        self.assertTrue(snapshot["data_quality"]["quarantined"])
        self.assertIn("日线价格尺度断点待核", snapshot["data_quality"]["warnings"])

    def test_risk_reduction_is_bound_to_symbol_and_position_budget(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 9_900,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 100,
                "leverage": 1, "position_side": "LONG", "direction_mode": "LONG_ONLY",
                "reduce_only": False,
            },
            {"status": "STOPPED"},
            True,
            1_000,
        )

        def failed(*_args: object) -> dict[str, object]:
            raise OSError("provider unavailable")

        service = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 1_001,
            audit_writer=failed,
            data_context_provider=failed,
            portfolio_context_provider=failed,
        )
        cross_symbol = service.evaluate(
            symbol="BTC-USDT", side="SELL", mode="PAPER", notional=1_000_000, price=100,
            context={"order_type": "MARKET", "reduce_only": False},
        )
        over_reduction = service.evaluate(
            symbol="AAPL", side="SELL", mode="PAPER", notional=101, price=100,
            context={"order_type": "MARKET", "reduce_only": False},
        )
        valid_reduction = service.evaluate(
            symbol="AAPL", side="SELL", mode="PAPER", notional=100, price=100,
            context={"order_type": "MARKET", "reduce_only": False},
        )

        self.assertFalse(cross_symbol["allowed"])
        self.assertFalse(over_reduction["allowed"])
        self.assertTrue(valid_reduction["allowed"])
        self.assertTrue(valid_reduction["context"]["risk_reducing_authoritative"])

    def test_risk_state_machine_and_market_provider_contract_fail_closed(self) -> None:
        def snapshot(position_side: str, position_value: float = 0.0) -> dict[str, object]:
            return build_risk_snapshot(
                {
                    "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                    "drawdown_pct": 0, "max_drawdown_pct": 5,
                    "position_value": position_value, "leverage": 1,
                    "position_side": position_side, "direction_mode": "LONG_ONLY",
                    "reduce_only": False,
                },
                {"status": "STOPPED"},
                True,
                1_000,
            )

        for position_side, side in (("LONG", "SHORT"), ("FLAT", "COVER"), ("FLAT", "CLOSE")):
            result = RiskService(
                snapshot_provider=lambda _price, value=position_side: snapshot(
                    value,
                    100 if value != "FLAT" else 0,
                ),
                now_ms=lambda: 1_001,
                data_context_provider=lambda *_args: {},
            ).evaluate(
                symbol="AAPL", side=side, mode="PAPER", notional=100, price=100,
                context={"order_type": "MARKET", "reduce_only": False},
            )
            self.assertFalse(result["allowed"], f"{position_side}+{side} must fail closed")

        forged = RiskService(
            snapshot_provider=lambda _price: snapshot("FLAT"),
            now_ms=lambda: 1_001,
            data_context_provider=lambda *_args: {},
        ).evaluate(
            symbol="AAPL", side="BUY", mode="PAPER", notional=100, price=100,
            context={
                "order_type": "MARKET", "reduce_only": False,
                "data_status": "READY", "data_realtime": True,
                "data_fallback": False, "data_quarantined": False,
                "data_quality": {
                    "status": "READY", "realtime": True, "fallback": False,
                    "quarantined": False, "can_increase_risk": True,
                    "blocking_reasons": [],
                },
            },
        )
        self.assertFalse(forged["allowed"])
        self.assertEqual(forged["context"]["data_status"], "OFFLINE")

    def test_risk_malformed_collections_and_stale_snapshot_return_blocks(self) -> None:
        risk = build_risk_snapshot(
            {
                "symbol": "AAPL", "equity": 10_000, "available_cash": 10_000,
                "drawdown_pct": 0, "max_drawdown_pct": 5, "position_value": 0,
                "leverage": 1, "position_side": "FLAT", "direction_mode": "LONG_ONLY",
                "reduce_only": False,
            },
            {"status": "STOPPED"},
            True,
            1,
        )
        ready = {
            "order_type": "MARKET", "reduce_only": False,
            "data_status": "READY", "data_realtime": True,
            "data_fallback": False, "data_quarantined": False,
            "data_quality": {
                "status": "READY", "realtime": True, "fallback": False,
                "quarantined": False, "can_increase_risk": True,
                "blocking_reasons": [],
            },
        }
        for malformed in (
            {"account_context_mismatches": None},
            {"data_quality": {**ready["data_quality"], "blocking_reasons": 1}},
            {
                "portfolio_risk_required": True,
                "portfolio_risk": {
                    "status": "PASS", "portfolio_gate_passed": True, "reject_reasons": 1,
                },
            },
        ):
            result = build_pretrade_check(risk, "AAPL", "BUY", "PAPER", 100, {**ready, **malformed})
            self.assertFalse(result["allowed"])

        complete_market = {
            "data_status": "READY", "data_quarantined": False,
            "data_realtime": True, "data_fallback": False,
            "market_snapshot_id": "snapshot-1", "authoritative_price": 100,
            "price_deviation_pct": 0,
            "data_quality": {
                "status": "READY", "realtime": True, "fallback": False,
                "quarantined": False, "can_increase_risk": True,
                "blocking_reasons": [],
            },
        }
        stale = RiskService(
            snapshot_provider=lambda _price: risk,
            now_ms=lambda: 10_000,
            data_context_provider=lambda *_args: complete_market,
        ).evaluate(
            symbol="AAPL", side="BUY", mode="PAPER", notional=100, price=100,
            context={"order_type": "MARKET", "reduce_only": False},
        )
        self.assertFalse(stale["allowed"])
        self.assertFalse(next(row for row in stale["checks"] if row["name"] == "risk_snapshot_freshness")["ok"])

    def test_quantity_execution_never_exceeds_approved_notional(self) -> None:
        report = simulated_execution_report(
            "AAPL", "BUY", "MARKET", 100, 100,
            book_reader=lambda *_args: [[1_000_000, 1]],
            requested_qty=1,
        )

        self.assertEqual(report["status"], "PARTIAL")
        self.assertLessEqual(report["filled_notional"], 100)
        self.assertLess(report["filled_qty"], 1)

    def test_paper_ledger_binds_orders_to_one_account_and_rejects_spoofed_settlement(self) -> None:
        def baseline() -> dict[str, object]:
            return {
                "cash": 1_000, "short_margin": 0, "realized_pnl": 0,
                "symbol": "AAPL", "position_qty": 0, "entry_price": 0,
                "leverage": 1, "orders": [], "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paper.sqlite3"
            account_a = PaperLedger(db_path=path, now_ms=lambda: 2, account_id="A")
            account_b = PaperLedger(db_path=path, now_ms=lambda: 2, account_id="B")
            account_a.save_account(baseline())
            account_b.save_account(baseline())
            order = paper_lifecycle_fill("account-a-fill", "BUY", 1, 100, 1)
            order.pop("account_id")
            account_a.record_lifecycle_order(order)

            with self.assertRaisesRegex(ValueError, "paper_settlement_symbol_mismatch"):
                spoofed = {**baseline(), "orders": [{"order_id": "account-a-fill"}]}
                account_a.save_account(spoofed, applied_lifecycle_ids=["account-a-fill"])

            results = [account_a.reconcile_account(), account_b.reconcile_account()]
            self.assertEqual(results[0]["reconciled"], 1)
            self.assertEqual(results[1]["reconciled"], 0)
            self.assertEqual(account_a.load_account()["position_qty"], 1)
            self.assertEqual(account_b.load_account()["position_qty"], 0)

    def test_paper_ledger_stale_position_snapshot_cannot_reverse_position(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PaperLedger(db_path=Path(temp_dir) / "paper.sqlite3", now_ms=lambda: 3)
            ledger.save_account({
                "cash": 900, "short_margin": 0, "realized_pnl": 0,
                "symbol": "AAPL", "position_qty": 1, "entry_price": 100,
                "leverage": 1, "orders": [], "conditional_orders": [],
                "equity_curve": [{"time": 1, "equity": 1_000}],
            })
            ledger.record_lifecycle_order(
                paper_lifecycle_fill(
                    "close-long-1", "SELL", 1, 100, 1,
                    position_side_before="LONG",
                )
            )
            ledger.record_lifecycle_order(
                paper_lifecycle_fill(
                    "close-long-2", "SELL", 1, 100, 2,
                    position_side_before="LONG",
                )
            )

            result = ledger.reconcile_account()
            restored = ledger.load_account()

            self.assertFalse(result["ok"])
            self.assertEqual(result["reconciled"], 1)
            self.assertEqual(restored["position_qty"], 0)
            self.assertEqual(ledger.summary()["pending_settlement_count"], 1)



    def test_event_bus_and_audit_log_are_thread_safe(self) -> None:
        bus = EventBus(now_ms=lambda: 123, max_events=500)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"
            audit = AuditLog(
                path=path,
                ensure_runtime=lambda: path.parent.mkdir(parents=True, exist_ok=True),
                now_ms=lambda: 123,
                publish_event=lambda event_type, payload: bus.publish(event_type, payload),
            )
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda index: audit.append({"type": "test", "index": index}), range(120)))
            rows = audit.read(200, "test")
            self.assertFalse(path.exists())
            self.assertEqual(audit.summary()["backend"], "sqlite")
        self.assertEqual(len(rows), 120)
        self.assertEqual(sorted(row["event_seq"] for row in rows), list(range(1, 121)))
        self.assertEqual(len({json.dumps(row, sort_keys=True) for row in rows}), 120)

    def test_audit_log_serializes_structured_index_fields(self) -> None:
        bus = EventBus(now_ms=lambda: 123)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.jsonl"
            audit = AuditLog(
                path=path,
                ensure_runtime=lambda: path.parent.mkdir(parents=True, exist_ok=True),
                now_ms=lambda: 123,
                publish_event=lambda event_type, payload: bus.publish(event_type, payload),
            )

            saved = audit.append({
                "type": "market_snapshot",
                "symbol": "AAPL",
                "source": {"primary": "futu", "adapter": "futu_adapter"},
            })

            self.assertEqual(saved["type"], "market_snapshot")
            self.assertEqual(audit.read(1)[0]["source"]["primary"], "futu")


if __name__ == "__main__":
    unittest.main()
