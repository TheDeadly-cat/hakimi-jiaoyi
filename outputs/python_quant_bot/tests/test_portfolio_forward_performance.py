from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_forward_performance import (
    PortfolioForwardPerformanceLedger,
    _execute_benchmark_entry,
    _execute_strategy_decision,
    _normalize_market_rows,
    build_forward_performance_readiness,
    build_forward_performance_settlement,
    forward_evidence_thresholds_from_spec,
    verify_forward_performance_settlement,
)
from exchange_terminal.services.portfolio_backtest import portfolio_revision_evidence_hash
from exchange_terminal.services.portfolio_shadow import (
    build_forward_state_contract,
    build_shadow_observation,
)
from exchange_terminal.services.trusted_clock import build_trusted_clock_attestation


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sealed(payload: dict[str, object], field: str) -> dict[str, object]:
    result = dict(payload)
    result[field] = canonical_hash(result)
    return result


def candidate(*, minimum_outcomes: int = 2) -> dict[str, object]:
    return {
        "candidate_hash": "candidate-forward-1",
        "dataset_last": "2026-07-30",
        "spec": {
            "benchmark_symbol": "SPY",
            "tradable_symbols": ["AAPL", "NVDA"],
            "gross_target_pct": 60.0,
            "execution_risk_buffer_pct": 0.25,
            "max_position_weight_pct": 50.0,
            "minimum_trade_pct": 1.0,
            "max_entry_participation_pct": 1.0,
            "max_exit_participation_pct": 2.0,
            "max_entry_open_gap_pct": 12.0,
            "impact_bps_at_full_participation": 15.0,
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "minimum_forward_observations": minimum_outcomes,
            "minimum_planned_rebalances": 1,
            "acceptance_contract": {
                "validation_and_test_max_drawdown_below_pct": 15.0,
            },
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def capture(signal_date: str, *, observed_at: int) -> dict[str, object]:
    clock_evidence = sealed({
        "source": "TEST_CLOCK",
        "endpoint": "https://clock.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": observed_at - 1,
        "received_at_ms": observed_at + 1,
        "round_trip_ms": 2,
        "midpoint_local_ms": observed_at,
        "server_time_ms": observed_at,
        "offset_ms": 0,
    }, "evidence_hash")
    clock = build_trusted_clock_attestation(
        local_now_ms=observed_at,
        provider_evidence=[clock_evidence],
    )
    activation_at = 1
    activation_evidence = sealed({
        "source": "TEST_ACTIVATION_CLOCK",
        "endpoint": "https://clock.test/activation",
        "status": "PASS",
        "error": "",
        "requested_at_ms": activation_at,
        "received_at_ms": activation_at,
        "round_trip_ms": 0,
        "midpoint_local_ms": activation_at,
        "server_time_ms": activation_at,
        "offset_ms": 0,
    }, "evidence_hash")
    activation_clock = build_trusted_clock_attestation(
        local_now_ms=activation_at,
        provider_evidence=[activation_evidence],
    )
    return sealed({
        "status": "PASS",
        "signal_date": signal_date,
        "session_close_utc": f"{signal_date}T20:00:00+00:00",
        "timely": True,
        "backfill_allowed": False,
        "candidate_hash": "candidate-forward-1",
        "candidate_activated_at": activation_at,
        "candidate_activation_registry_hash": "registry-hash",
        "candidate_active_before_signal_close": True,
        "activation_clock_attestation_hash": activation_clock["attestation_hash"],
        "activation_clock_attestation": activation_clock,
        "observed_at": observed_at,
        "clock_attested": True,
        "clock_attestation_hash": clock["attestation_hash"],
        "clock_attestation": clock,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }, "capture_contract_hash")


def risk(status: str = "PASS") -> dict[str, object]:
    return sealed({
        "status": status,
        "blockers": [] if status == "PASS" else ["risk_blocked"],
        "paper_authorized": False,
        "live_order_allowed": False,
    }, "risk_snapshot_hash")


def decision(signal_date: str, *, execute: bool = True) -> dict[str, object]:
    if not execute:
        return {
            "signal_date": signal_date,
            "target_symbols": ["AAPL", "NVDA"],
            "target_weights": {},
            "target_allocation_pct": 59.75,
            "scores": {},
            "reason": "hold_between_rebalances",
            "execute": False,
        }
    liquidity = {
        symbol: {
            "window": 20,
            "observation_count": 20,
            "median_dollar_volume": 10_000_000.0,
            "minimum_median_dollar_volume": 5_000_000.0,
            "eligible": True,
            "as_of": signal_date,
        }
        for symbol in ("AAPL", "NVDA")
    }
    return {
        "signal_date": signal_date,
        "target_symbols": ["AAPL", "NVDA"],
        "target_weights": {"AAPL": 0.5, "NVDA": 0.5},
        "target_allocation_pct": 59.75,
        "uncushioned_target_allocation_pct": 60.0,
        "execution_risk_buffer_pct": 0.25,
        "liquidity": liquidity,
        "universe_ineligible_symbols": [],
        "reason": "relative_strength_rebalance",
        "execute": True,
    }


def observation(
    signal_date: str,
    *,
    dataset_hash: str,
    observed_at: int,
    execute: bool = True,
    risk_status: str = "PASS",
    preactivation_completed_session_count: int = 0,
) -> dict[str, object]:
    backtest = {
        "ok": True,
        "execution_model": "test-forward-execution",
        "initial_cash": 100_000.0,
        "run_spec": {
            "evaluation_start_index": 0,
            "execution_model": "test-forward-execution",
        },
        "evaluation_window": {
            "start_index": 0,
            "start": "2026-08-03",
            "end": signal_date,
        },
        "dataset_manifest": {"data_hash": dataset_hash, "last": signal_date},
        "pending_decision_at_end": decision(signal_date, execute=execute),
    }
    capture_contract = capture(signal_date, observed_at=observed_at)
    state_contract = build_forward_state_contract(
        candidate(),
        backtest,
        capture_contract=capture_contract,
        evaluation_start_index=0,
        evaluation_start_date="2026-08-03",
        preactivation_completed_session_count=preactivation_completed_session_count,
        start_capture_contract=capture_contract,
    )
    return build_shadow_observation(
        candidate(),
        backtest,
        observed_at=observed_at,
        risk_snapshot=risk(risk_status),
        capture_contract=capture_contract,
        forward_state_contract=state_contract,
    )


def manifest(signal_date: str, dataset_hash: str) -> dict[str, object]:
    symbols = ["AAPL", "NVDA", "SPY"]
    lifecycle = {}
    adjustments = {}
    revisions = {}
    for symbol in symbols:
        lifecycle_contract = {
            "schema_version": "security-lifecycle-contract-v1",
            "status": "PASS",
            "blockers": [],
            "warnings": [],
            "symbol": symbol,
            "events": [],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        lifecycle_contract["contract_hash"] = canonical_hash(lifecycle_contract)
        lifecycle[symbol] = lifecycle_contract
        adjustment = {
            "schema_version": "stock-corporate-action-ledger-v3",
            "status": "PASS",
            "backtest_eligible": True,
            "symbol": symbol,
            "return_accounting": {
                "cash_execution_supported": True,
                "double_count_protection": True,
                "split_mode": "EMBEDDED_IN_ADJUSTED_SERIES",
                "dividend_mode": "EMBEDDED_IN_ADJUSTED_RETURN",
            },
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        adjustment["evidence_hash"] = canonical_hash(adjustment)
        adjustments[symbol] = adjustment
        revision = {
            "status": "PASS",
            "accepted_cache": {"status": "PASS", "blockers": []},
            "backtest_dataset": {
                "status": "PASS",
                "blockers": [],
                "current": {"snapshot_hash": f"snapshot-{symbol}"},
            },
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        revision["evidence_hash"] = portfolio_revision_evidence_hash(revision)
        revisions[symbol] = revision
    actions = {symbol: [] for symbol in symbols}
    calendar = {
        "schema_version": "exchange-session-calendar-v1",
        "status": "PASS",
        "blockers": [],
        "warnings": [],
        "calendar_name": "XNYS",
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    calendar["contract_hash"] = canonical_hash(calendar)
    contract = {
        "schema_version": "portfolio-aligned-market-dataset-v2",
        "data_hash": dataset_hash,
        "market_calendar_hash": calendar["contract_hash"],
        "security_lifecycle_hashes": {
            symbol: lifecycle[symbol]["contract_hash"] for symbol in symbols
        },
        "adjustment_evidence_hashes": {
            symbol: adjustments[symbol]["evidence_hash"] for symbol in symbols
        },
        "data_revision_evidence_hashes": {
            symbol: revisions[symbol]["evidence_hash"] for symbol in symbols
        },
        "corporate_action_hashes": {
            symbol: canonical_hash(actions[symbol]) for symbol in symbols
        },
    }
    return {
        "schema_version": "portfolio-aligned-market-dataset-v2",
        "status": "PASS",
        "blockers": [],
        "warnings": [],
        "benchmark_symbol": "SPY",
        "symbols": symbols,
        "row_count": 180,
        "first": "2025-11-14",
        "last": signal_date,
        "data_hash": dataset_hash,
        "manifest_hash": canonical_hash(contract),
        "market_calendar": calendar,
        "security_lifecycle": lifecycle,
        "adjustment_evidence": adjustments,
        "data_revision_evidence": revisions,
        "corporate_actions": actions,
        "sources": {symbol: "test" for symbol in symbols},
    }


def rows(signal_date: str, *, day: int = 0, gap: bool = False) -> dict[str, dict[str, object]]:
    prices = {
        "SPY": (100.0 + day * 2.0, 101.0 + day * 2.0),
        "AAPL": (200.0 + day * 4.0, 202.0 + day * 4.0),
        "NVDA": (100.0 + day * 2.0, 101.0 + day * 3.0),
    }
    if gap:
        prices["AAPL"] = (250.0, 252.0)
    return {
        symbol: {
            "date": signal_date,
            "ts_ms": 1_800_000_000_000 + day * 86_400_000 + index,
            "open": open_price,
            "high": max(open_price, close_price) + 1.0,
            "low": min(open_price, close_price) - 1.0,
            "close": close_price,
            "volume": 1_000_000.0,
            "complete": True,
            "tradable": True,
        }
        for index, (symbol, (open_price, close_price)) in enumerate(prices.items())
    }


def settlement_inputs(
    signal_date: str,
    *,
    day: int,
    execute: bool = True,
    risk_status: str = "PASS",
    gap: bool = False,
) -> tuple[dict[str, object], dict[str, object], dict[str, dict[str, object]]]:
    dataset_hash = hashlib.sha256(f"dataset-{signal_date}".encode()).hexdigest()
    return (
        observation(
            signal_date,
            dataset_hash=dataset_hash,
            observed_at=100 + day,
            execute=execute,
            risk_status=risk_status,
        ),
        manifest(signal_date, dataset_hash),
        rows(signal_date, day=day, gap=gap),
    )


class PortfolioForwardPerformanceTests(unittest.TestCase):
    def test_forward_evidence_threshold_contract_rejects_explicit_zero_and_fraction(self) -> None:
        contract = forward_evidence_thresholds_from_spec({
            "minimum_forward_observations": 0,
            "minimum_forward_performance_outcomes": 2.5,
            "minimum_planned_rebalances": 0,
        })

        self.assertEqual(contract["status"], "BLOCK")
        self.assertEqual(contract["minimum_forward_observations"], 60)
        self.assertEqual(contract["minimum_forward_performance_outcomes"], 60)
        self.assertEqual(contract["minimum_planned_rebalances"], 8)
        self.assertEqual(len(contract["issues"]), 3)

    def test_zero_gross_target_keeps_benchmark_in_cash(self) -> None:
        frozen = dict(candidate()["spec"])
        frozen["gross_target_pct"] = 0.0

        cash, quantity, orders, blockers = _execute_benchmark_entry(
            cash=100_000.0,
            quantity=0.0,
            row={"symbol": "SPY", "open": 100.0, "tradable": True},
            spec=frozen,
            source_signal_date="2026-08-03",
        )

        self.assertEqual(cash, 100_000.0)
        self.assertEqual(quantity, 0.0)
        self.assertEqual(orders, [])
        self.assertEqual(blockers, [])

    def test_full_gross_target_has_no_hidden_benchmark_cash_buffer(self) -> None:
        frozen = dict(candidate()["spec"])
        frozen["gross_target_pct"] = 100.0
        frozen["fee_rate"] = 0.001
        frozen["slippage_bps"] = 0.0

        cash, quantity, orders, blockers = _execute_benchmark_entry(
            cash=100_000.0,
            quantity=0.0,
            row={"symbol": "SPY", "open": 100.0, "tradable": True},
            spec=frozen,
            source_signal_date="2026-08-03",
        )

        self.assertAlmostEqual(cash, 0.0, places=8)
        self.assertAlmostEqual(quantity, (100_000.0 / 1.001) / 100.0, places=8)
        self.assertEqual(len(orders), 1)
        self.assertEqual(blockers, [])

    def test_market_row_dollar_volume_overflow_is_blocked(self) -> None:
        market_rows = rows("2026-08-03")
        market_rows["AAPL"].update({
            "open": 1e308,
            "high": 1e308,
            "low": 1e308,
            "close": 1e308,
            "volume": 1e308,
        })

        _normalized, blockers = _normalize_market_rows(
            market_rows,
            signal_date="2026-08-03",
            required_symbols=["AAPL", "NVDA", "SPY"],
        )

        self.assertIn("market_row_dollar_volume_invalid:AAPL", blockers)

    def test_string_false_market_completion_flag_is_rejected(self) -> None:
        market_rows = rows("2026-08-03")
        market_rows["AAPL"]["complete"] = "false"

        normalized, blockers = _normalize_market_rows(
            market_rows,
            signal_date="2026-08-03",
            required_symbols=["AAPL", "NVDA", "SPY"],
        )

        self.assertFalse(normalized["AAPL"]["complete"])
        self.assertIn("market_row_boolean_invalid:AAPL:complete", blockers)
        self.assertIn("market_row_incomplete:AAPL", blockers)

    def test_invalid_decision_weight_is_not_silently_clamped(self) -> None:
        frozen = dict(candidate()["spec"])
        quantities = {"AAPL": 0.0, "NVDA": 0.0}
        market_rows = rows("2026-08-04", day=1)
        previous_rows = rows("2026-08-03", day=0)
        invalid = decision("2026-08-03")
        invalid["target_weights"] = {"AAPL": -0.5, "NVDA": 0.5}

        _cash, orders, events, blockers = _execute_strategy_decision(
            decision=invalid,
            source_signal_date="2026-08-03",
            rows={symbol: market_rows[symbol] for symbol in quantities},
            previous_rows={symbol: previous_rows[symbol] for symbol in quantities},
            quantities=quantities,
            cash=100_000.0,
            spec=frozen,
        )

        self.assertEqual(orders, [])
        self.assertEqual(events, [])
        self.assertIn("decision_target_weights_nonfinite_or_negative", blockers)

    def test_zero_exit_participation_does_not_fabricate_forward_liquidity(self) -> None:
        frozen = dict(candidate()["spec"])
        frozen["max_exit_participation_pct"] = 0.0
        quantities = {"AAPL": 10.0, "NVDA": 0.0}
        market_rows = rows("2026-08-04", day=1)
        previous_rows = rows("2026-08-03", day=0)
        cash, orders, events, blockers = _execute_strategy_decision(
            decision={
                "signal_date": "2026-08-03",
                "target_symbols": [],
                "target_weights": {},
                "target_allocation_pct": 0.0,
                "liquidity": {"AAPL": {"median_dollar_volume": 10_000_000.0}},
                "execute": True,
            },
            source_signal_date="2026-08-03",
            rows={symbol: market_rows[symbol] for symbol in quantities},
            previous_rows={symbol: previous_rows[symbol] for symbol in quantities},
            quantities=quantities,
            cash=1_000.0,
            spec=frozen,
        )

        self.assertEqual(cash, 1_000.0)
        self.assertEqual(orders, [])
        self.assertEqual(blockers, [])
        self.assertEqual(quantities["AAPL"], 10.0)
        self.assertTrue(any(event["event_type"] == "BLOCKED_NO_LIQUIDITY" for event in events))

    def test_forward_settlement_blocks_unimplemented_explicit_corporate_action_accounting(self) -> None:
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)
        accounting = data_manifest["adjustment_evidence"]["AAPL"]["return_accounting"]
        accounting["split_mode"] = "EXPLICIT_QUANTITY_ADJUSTMENT"

        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("forward_corporate_action_accounting_unsupported:AAPL", settlement["blockers"])
        self.assertIn("adjustment_evidence_hash_invalid:AAPL", settlement["blockers"])

    def test_forward_settlement_rejects_nonfinite_initial_cash(self) -> None:
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)

        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
            initial_cash=float("inf"),
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("initial_cash_invalid", settlement["blockers"])

    def test_forward_settlement_rejects_boolean_initial_cash(self) -> None:
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)

        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
            initial_cash=True,
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("initial_cash_invalid", settlement["blockers"])

    def build_baseline(self) -> tuple[dict[str, object], dict[str, object]]:
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)
        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
        )
        return settlement, obs

    def build_second(
        self,
        baseline: dict[str, object],
        source_observation: dict[str, object],
        *,
        current_execute: bool = False,
        gap: bool = False,
    ) -> tuple[dict[str, object], dict[str, object]]:
        obs, data_manifest, market_rows = settlement_inputs(
            "2026-08-04",
            day=1,
            execute=current_execute,
            gap=gap,
        )
        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=201,
            previous_settlement=baseline,
            previous_observation=source_observation,
            previous_session_date="2026-08-03",
        )
        return settlement, obs

    def test_baseline_starts_from_cash_without_inheriting_backtest_positions(self) -> None:
        baseline, _ = self.build_baseline()

        self.assertEqual(baseline["status"], "READY")
        self.assertEqual(baseline["settlement_type"], "BASELINE")
        self.assertEqual(baseline["decision_execution"]["status"], "BASELINE_AWAITING_NEXT_OPEN")
        self.assertEqual(baseline["strategy"]["equity"], 100_000.0)
        self.assertEqual(baseline["strategy"]["orders"], [])
        self.assertFalse(baseline["benchmark"]["state"]["started"])
        self.assertEqual(verify_forward_performance_settlement(baseline)["status"], "PASS")

    def test_next_session_executes_captured_decision_and_enters_benchmark(self) -> None:
        baseline, source = self.build_baseline()
        second, _ = self.build_second(baseline, source)

        self.assertEqual(second["status"], "READY")
        self.assertEqual(second["decision_execution"]["status"], "EXECUTED")
        self.assertEqual(len(second["strategy"]["orders"]), 2)
        self.assertEqual({order["side"] for order in second["strategy"]["orders"]}, {"BUY"})
        self.assertEqual(len(second["benchmark"]["orders"]), 1)
        self.assertGreater(second["strategy"]["state"]["total_fees"], 0)
        self.assertGreater(second["strategy"]["state"]["turnover"], 0)
        self.assertEqual(verify_forward_performance_settlement(second, baseline)["status"], "PASS")

    def test_risk_blocked_source_decision_cannot_trade(self) -> None:
        obs, data_manifest, market_rows = settlement_inputs(
            "2026-08-03",
            day=0,
            risk_status="BLOCK",
        )
        baseline = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
        )
        second, _ = self.build_second(baseline, obs)

        self.assertEqual(second["decision_execution"]["status"], "RISK_BLOCKED")
        self.assertEqual(second["strategy"]["orders"], [])
        self.assertTrue(any(
            event["event_type"] == "BLOCKED_BY_CAPTURED_RISK_GATE"
            for event in second["strategy"]["execution_events"]
        ))
        self.assertEqual(len(second["benchmark"]["orders"]), 1)

    def test_entry_gap_is_recorded_without_fabricating_fill(self) -> None:
        baseline, source = self.build_baseline()
        second, _ = self.build_second(baseline, source, gap=True)

        symbols = {order["symbol"] for order in second["strategy"]["orders"]}
        self.assertNotIn("AAPL", symbols)
        self.assertIn("NVDA", symbols)
        self.assertTrue(any(
            event["event_type"] == "BLOCKED_ENTRY_GAP" and event["symbol"] == "AAPL"
            for event in second["strategy"]["execution_events"]
        ))

    def test_market_session_gap_blocks_settlement(self) -> None:
        baseline, source = self.build_baseline()
        obs, data_manifest, market_rows = settlement_inputs("2026-08-04", day=1, execute=False)
        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=201,
            previous_settlement=baseline,
            previous_observation=source,
            previous_session_date="2026-08-02",
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("market_session_chain_gap", settlement["blockers"])

    def test_historical_retention_state_cannot_leak_into_clean_forward_account(self) -> None:
        source_hash = hashlib.sha256(b"dataset-2026-08-03-retained").hexdigest()
        source_backtest = {
            "ok": True,
            "execution_model": "test-forward-execution",
            "initial_cash": 100_000.0,
            "run_spec": {
                "evaluation_start_index": 0,
                "execution_model": "test-forward-execution",
            },
            "evaluation_window": {
                "start_index": 0,
                "start": "2026-08-03",
                "end": "2026-08-03",
            },
            "dataset_manifest": {"data_hash": source_hash, "last": "2026-08-03"},
            "pending_decision_at_end": {
                **decision("2026-08-03"),
                "retained_symbols": ["AAPL"],
            },
        }
        source_capture = capture("2026-08-03", observed_at=100)
        source_state = build_forward_state_contract(
            candidate(),
            source_backtest,
            capture_contract=source_capture,
            evaluation_start_index=0,
            evaluation_start_date="2026-08-03",
            preactivation_completed_session_count=0,
            start_capture_contract=source_capture,
        )
        source = build_shadow_observation(
            candidate(),
            source_backtest,
            observed_at=100,
            risk_snapshot=risk(),
            capture_contract=source_capture,
            forward_state_contract=source_state,
        )
        baseline = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=source,
            dataset_manifest=manifest("2026-08-03", source_hash),
            market_rows=rows("2026-08-03"),
            recorded_at=200,
        )
        current, current_manifest, current_rows = settlement_inputs(
            "2026-08-04",
            day=1,
            execute=False,
        )
        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=current,
            dataset_manifest=current_manifest,
            market_rows=current_rows,
            recorded_at=201,
            previous_settlement=baseline,
            previous_observation=source,
            previous_session_date="2026-08-03",
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("decision_retention_state_mismatch:AAPL", settlement["blockers"])

    def test_forward_state_contract_cannot_change_within_candidate(self) -> None:
        baseline, source = self.build_baseline()
        current_hash = hashlib.sha256(b"dataset-2026-08-04-state-change").hexdigest()
        current = observation(
            "2026-08-04",
            dataset_hash=current_hash,
            observed_at=101,
            execute=False,
            preactivation_completed_session_count=1,
        )
        settlement = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=current,
            dataset_manifest=manifest("2026-08-04", current_hash),
            market_rows=rows("2026-08-04", day=1),
            recorded_at=201,
            previous_settlement=baseline,
            previous_observation=source,
            previous_session_date="2026-08-03",
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("forward_state_contract_changed_within_candidate", settlement["blockers"])

    def test_ledger_is_idempotent_and_rejects_same_date_conflict(self) -> None:
        baseline, source = self.build_baseline()
        conflicting = build_forward_performance_settlement(
            candidate=candidate(),
            current_observation=source,
            dataset_manifest=manifest("2026-08-03", source["dataset_hash"]),
            market_rows=rows("2026-08-03"),
            recorded_at=201,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioForwardPerformanceLedger(Path(temp_dir, "forward.sqlite"))
            first = ledger.record(baseline)
            replay = ledger.record(baseline)
            conflict = ledger.record(conflicting)

        self.assertEqual(first["status"], "RECORDED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(conflict["status"], "CONFLICT")

    def test_restart_recovers_latest_state_and_extends_hash_chain(self) -> None:
        baseline, source = self.build_baseline()
        second, second_observation = self.build_second(baseline, source)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir, "forward.sqlite")
            first_process = PortfolioForwardPerformanceLedger(path)
            self.assertTrue(first_process.record(baseline)["ok"])
            self.assertTrue(first_process.record(second)["ok"])
            restarted = PortfolioForwardPerformanceLedger(path)
            recovered = restarted.latest("candidate-forward-1")
            third_observation, third_manifest, third_rows = settlement_inputs(
                "2026-08-05",
                day=2,
                execute=False,
            )
            third = build_forward_performance_settlement(
                candidate=candidate(),
                current_observation=third_observation,
                dataset_manifest=third_manifest,
                market_rows=third_rows,
                recorded_at=202,
                previous_settlement=recovered,
                previous_observation=second_observation,
                previous_session_date="2026-08-04",
            )
            result = restarted.record(third)
            audit = restarted.audit(
                "candidate-forward-1",
                observations={
                    "2026-08-03": source,
                    "2026-08-04": second_observation,
                    "2026-08-05": third_observation,
                },
            )

        self.assertEqual(recovered["settlement_hash"], second["settlement_hash"])
        self.assertEqual(third["decision_execution"]["status"], "NO_ACTION")
        self.assertEqual(result["status"], "RECORDED")
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["outcome_period_count"], 2)

    def test_tampered_persisted_payload_blocks_audit_and_future_append(self) -> None:
        baseline, source = self.build_baseline()
        second, _ = self.build_second(baseline, source)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir, "forward.sqlite")
            ledger = PortfolioForwardPerformanceLedger(path)
            ledger.record(baseline)
            ledger.record(second)
            with closing(sqlite3.connect(path)) as connection, connection:
                row = connection.execute(
                    "SELECT payload_json FROM portfolio_forward_performance_settlements "
                    "WHERE candidate_hash = ? AND settlement_date = ?",
                    ("candidate-forward-1", "2026-08-04"),
                ).fetchone()
                payload = json.loads(row[0])
                payload["strategy"]["equity"] += 1.0
                connection.execute(
                    "UPDATE portfolio_forward_performance_settlements SET payload_json = ? "
                    "WHERE candidate_hash = ? AND settlement_date = ?",
                    (json.dumps(payload), "candidate-forward-1", "2026-08-04"),
                )
            audit = ledger.audit("candidate-forward-1")

        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(any("settlement_hash_invalid" in item for item in audit["integrity_violations"]))

    def test_candidate_with_execution_authority_is_rejected(self) -> None:
        unsafe_candidate = candidate()
        unsafe_candidate["paper_authorized"] = True
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)
        settlement = build_forward_performance_settlement(
            candidate=unsafe_candidate,
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("candidate_execution_authority_invalid", settlement["blockers"])
        self.assertFalse(settlement["live_order_allowed"])

    def test_candidate_string_false_authority_is_rejected(self) -> None:
        unsafe_candidate = candidate()
        unsafe_candidate["paper_authorized"] = "false"
        obs, data_manifest, market_rows = settlement_inputs("2026-08-03", day=0)

        settlement = build_forward_performance_settlement(
            candidate=unsafe_candidate,
            current_observation=obs,
            dataset_manifest=data_manifest,
            market_rows=market_rows,
            recorded_at=200,
        )

        self.assertEqual(settlement["status"], "BLOCK")
        self.assertIn("candidate_execution_authority_invalid", settlement["blockers"])

    def test_readiness_reports_statistical_veto_without_granting_authority(self) -> None:
        baseline, source = self.build_baseline()
        second, second_observation = self.build_second(baseline, source)
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = PortfolioForwardPerformanceLedger(Path(temp_dir, "forward.sqlite"))
            ledger.record(baseline)
            ledger.record(second)
            summary = ledger.summary(
                "candidate-forward-1",
                observations={"2026-08-03": source, "2026-08-04": second_observation},
            )
        readiness = build_forward_performance_readiness(
            candidate=candidate(minimum_outcomes=1),
            shadow_audit={"status": "PASS", "valid_observation_count": 2},
            performance_summary=summary,
            historical_statistical_audit={
                "status": "BLOCK",
                "conclusion": "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE",
                "audit_hash": "audit-hash",
                "artifact_hash": "artifact-hash",
                "verification_status": "PASS",
            },
        )

        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertIn("historical_statistical_audit_pass", readiness["blockers"])
        self.assertFalse(readiness["paper_authorized"])
        self.assertFalse(readiness["live_order_allowed"])

        unverified_pass = build_forward_performance_readiness(
            candidate=candidate(minimum_outcomes=1),
            shadow_audit={"status": "PASS", "valid_observation_count": 2},
            performance_summary=summary,
            historical_statistical_audit={
                "status": "PASS",
                "conclusion": "STATISTICAL_PROMOTION_EVIDENCE_PASS",
                "audit_hash": "resealed-audit-hash",
                "artifact_hash": "resealed-artifact-hash",
            },
        )

        self.assertEqual(unverified_pass["status"], "BLOCK")
        self.assertIn(
            "historical_statistical_audit_integrity_pass",
            unverified_pass["blockers"],
        )
        self.assertFalse(unverified_pass["paper_authorized"])
        self.assertFalse(unverified_pass["live_order_allowed"])

    def test_readiness_blocks_invalid_candidate_forward_threshold_contract(self) -> None:
        invalid_candidate = candidate()
        invalid_candidate["spec"]["minimum_forward_observations"] = 0

        readiness = build_forward_performance_readiness(
            candidate=invalid_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": 0},
            performance_summary={
                "status": "PASS",
                "outcome_period_count": 0,
                "rebalance_execution_count": 0,
                "unsettled_observation_dates": [],
                "execution_authority_violation_count": 0,
            },
            historical_statistical_audit={"status": "BLOCK", "verification_status": "PASS"},
        )

        self.assertEqual(readiness["status"], "BLOCK")
        self.assertIn("candidate_forward_threshold_contract_pass", readiness["blockers"])
        self.assertEqual(readiness["forward_threshold_contract"]["status"], "BLOCK")

    def test_readiness_rejects_string_progress_counts(self) -> None:
        readiness = build_forward_performance_readiness(
            candidate=candidate(minimum_outcomes=1),
            shadow_audit={"status": "PASS", "valid_observation_count": 2},
            performance_summary={
                "status": "PASS",
                "outcome_period_count": "2",
                "rebalance_execution_count": 1,
                "settlement_count": 3,
                "unsettled_observation_dates": [],
                "execution_authority_violation_count": 0,
                "strategy": {"max_drawdown_pct": 1.0},
                "cumulative_excess_return_pct": 1.0,
            },
            historical_statistical_audit={"status": "PASS", "verification_status": "PASS"},
        )

        self.assertEqual(readiness["status"], "BLOCK")
        self.assertIn("forward_progress_types_valid", readiness["blockers"])


if __name__ == "__main__":
    unittest.main()
