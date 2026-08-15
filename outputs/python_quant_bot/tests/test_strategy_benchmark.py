from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_benchmark import (
    aggregate_strategy_selection,
    align_completed_daily_payloads,
    build_calendar_split_schedule,
    confirmation_summary,
)
from exchange_terminal.services.strategy_matrix_evidence import (
    MATRIX_REPORT_SCHEMA_VERSION,
    MATRIX_RESEARCH_GOVERNANCE_VERSION,
    canonical_hash,
    strategy_matrix_result_hash,
    strategy_matrix_run_hash,
    verify_strategy_matrix_evidence,
    verify_strategy_matrix_report,
)
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.backtest_engine import prepare_backtest_dataset
from exchange_terminal.services.strategy_matrix_protocol import (
    STRATEGY_MATRIX_CLAIM_VERSION,
    STRATEGY_MATRIX_COMPLETION_VERSION,
    build_strategy_matrix_protocol,
)
from tests.portfolio_governance_fixtures import attested_clock


def passing_cell(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "dataset_status": "PASS",
        "baseline_ok": True,
        "validation_return_pct": 2.0,
        "test_return_pct": 3.0,
        "test_excess_return_pct": 1.0,
        "test_trade_count": 2,
        "test_max_drawdown_pct": 5.0,
        "test_sharpe": 1.0,
        "cost_sensitivity_status": "PASS",
        "temporal_status": "PASS",
        "walk_forward_status": "PASS",
        "lookahead_status": "PASS",
    }


def valid_matrix_report() -> dict[str, object]:
    risk = {
        "position_pct": 35.0,
        "take_profit_pct": 8.0,
        "stop_loss_pct": 4.0,
        "fee_rate": 0.0005,
        "slippage_bps": 2.0,
        "leverage": 1.0,
    }
    batch_spec = {
        "schema_version": "strategy-benchmark-v7",
        "selection_symbols": ["AAPL"],
        "confirmation_symbols": ["QQQ"],
        "strategies": ["dual_ma"],
        "strategy_specs": {"dual_ma": {
            "params": {"fast_window": 20, "slow_window": 60},
            "implementation_fingerprint": "fingerprint-1",
            "risk": risk,
        }},
        "risk": risk,
        "limit": 780,
        "max_confirmation_candidates": 1,
        "split_policy": {
            "schema_version": "calendar-split-v1",
            "train_ratio": 0.50,
            "validation_ratio": 0.25,
            "minimum_segment_rows": 120,
        },
        "data_policy": {
            "timeframe": "1D",
            "completed_candles_only": True,
            "alignment_schema_version": "daily-batch-alignment-v2",
            "max_endpoint_skew_days": 3,
            "max_boundary_skew_days": 7,
            "frozen_stock_revision_evidence_required": True,
            "frozen_crypto_history_evidence_required": True,
            "exact_dataset_snapshot_required": True,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    session_dates = [
        (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).date().isoformat()
        for index in range(16)
        if (datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).weekday() < 5
    ][:10]
    dataset_rows = {
        symbol: [
            {
                "date": session_date,
                "open": base + index,
                "high": base + index + 1,
                "low": base + index - 1,
                "close": base + index + 0.5,
                "volume": 1_000 + index,
                "complete": True,
            }
            for index, session_date in enumerate(session_dates)
        ]
        for symbol, base in (("AAPL", 100.0), ("QQQ", 200.0))
    }
    manifest = []
    for symbol, rows in dataset_rows.items():
        prepared = prepare_backtest_dataset(
            rows,
            symbol=symbol,
            source="TEST_FIXTURE",
            timeframe="1D",
            minimum_rows=1,
            market="stock",
        )["manifest"]
        manifest.append({
            "symbol": symbol,
            "source": "TEST_FIXTURE",
            "status": prepared["status"],
            "row_count": prepared["row_count"],
            "first": prepared["first"],
            "last": prepared["last"],
            "data_hash": prepared["data_hash"],
            "data_revision_evidence": {"status": "PASS"},
            "blockers": prepared["blockers"],
        })
    cells = [{"strategy_id": "dual_ma", "symbol": "AAPL", "run_hash": "cell-1"}]
    rankings = [{"strategy_id": "dual_ma", "status": "PASS", "eligible_for_confirmation": True}]
    confirmations = [{"strategy_id": "dual_ma", "status": "PASS", "forward_candidate": True}]
    selection_regime = {
        "status": "PASS",
        "symbols": [{"symbol": "AAPL", "status": "PASS"}],
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    selection_regime["evidence_hash"] = canonical_hash(selection_regime)
    selection_correlation = {
        "status": "PASS",
        "symbols": ["AAPL"],
        "pairs": {},
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    selection_correlation["matrix_hash"] = canonical_hash(selection_correlation)
    confirmation_regime = {
        "status": "PASS",
        "symbols": [{"symbol": "QQQ", "status": "PASS"}],
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    confirmation_regime["evidence_hash"] = canonical_hash(confirmation_regime)
    created_at = datetime.now(timezone.utc)
    created_at_ms = int(created_at.timestamp() * 1000)
    exposure_audit: dict[str, object] = {
        "schema_version": "strategy-matrix-exposure-audit-v1",
        "status": "PASS",
        "evaluated_before_data_load": True,
        "symbols": ["QQQ"],
        "exposed_symbols": [],
        "evidence": {},
        "blockers": [],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    exposure_audit["audit_hash"] = canonical_hash(exposure_audit)
    protocol = build_strategy_matrix_protocol(
        registration_id="registration-1",
        research_generation="TEST",
        batch_spec=batch_spec,
        implementation_manifest=build_implementation_manifest([Path(__file__)]),
        exposure_audit=exposure_audit,
        registration_clock_attestation=attested_clock(created_at_ms - 3_000),
        expires_at_ms=created_at_ms + 60_000,
        registry_path=PROJECT_ROOT / "runtime" / "test-matrix-registry.sqlite3",
    )
    claim: dict[str, object] = {
        "schema_version": STRATEGY_MATRIX_CLAIM_VERSION,
        "status": "CLAIMED_FOR_SINGLE_RUN",
        "registration_id": "registration-1",
        "protocol_hash": protocol["protocol_hash"],
        "registered_at_ms": created_at_ms - 3_000,
        "started_at_ms": created_at_ms - 2_000,
        "clock_attestation": attested_clock(created_at_ms - 2_000),
        "holdout_exposure_audit": exposure_audit,
        "implementation_fingerprint": protocol["implementation_fingerprint"],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    claim["claim_hash"] = canonical_hash(claim)
    report: dict[str, object] = {
        "schema_version": MATRIX_REPORT_SCHEMA_VERSION,
        "created_at": created_at.isoformat(),
        "batch_spec": batch_spec,
        "batch_spec_hash": canonical_hash(batch_spec),
        "dataset_manifest": manifest,
        "dataset_manifest_hash": canonical_hash(manifest),
        "selection_cells": cells,
        "confirmation_cells": [{"strategy_id": "dual_ma", "symbol": "QQQ", "run_hash": "cell-2"}],
        "selection_rankings": rankings,
        "confirmation_candidates": ["dual_ma"],
        "confirmations": confirmations,
        "forward_candidates": ["dual_ma"],
        "selection_alignment": {"status": "PASS", "common_start": "2024-01-01", "common_as_of": "2026-01-01"},
        "selection_calendar_schedule": {"status": "PASS"},
        "selection_regime_evidence": selection_regime,
        "selection_correlation_matrix": selection_correlation,
        "confirmation_alignment": {"status": "PASS"},
        "confirmation_calendar_schedule": {"status": "PASS"},
        "confirmation_regime_evidence": confirmation_regime,
        "summary": {
            "selection_gate_status": "PASS",
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    snapshot: dict[str, object] = {
        "schema_version": "strategy-matrix-dataset-snapshot-v1",
        "registration_id": "registration-1",
        "batch_spec_hash": report["batch_spec_hash"],
        "dataset_manifest": manifest,
        "dataset_manifest_hash": report["dataset_manifest_hash"],
        "datasets": [
            {
                "role": "SELECTION" if symbol == "AAPL" else "CONFIRMATION",
                "symbol": symbol,
                "market": "stock",
                "timeframe": "1D",
                "source": "TEST_FIXTURE",
                "retrieval_source": "TEST_FIXTURE",
                "origin_sources": ["TEST_FIXTURE"],
                "adjustment_basis": "TEST",
                "corporate_action_coverage": "TEST",
                "data_revision_evidence": {"status": "PASS"},
                "rows": rows,
            }
            for symbol, rows in dataset_rows.items()
        ],
        "dataset_count": 2,
        "row_count": 20,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    snapshot["snapshot_hash"] = canonical_hash(snapshot)
    report["dataset_snapshot"] = snapshot
    report["matrix_result_hash"] = strategy_matrix_result_hash(report)
    completion: dict[str, object] = {
        "schema_version": STRATEGY_MATRIX_COMPLETION_VERSION,
        "status": "COMPLETED",
        "registration_id": "registration-1",
        "protocol_hash": protocol["protocol_hash"],
        "claim_hash": claim["claim_hash"],
        "result_hash": report["matrix_result_hash"],
        "dataset_manifest_hash": report["dataset_manifest_hash"],
        "completed_at_ms": created_at_ms - 1_000,
        "clock_attestation": attested_clock(created_at_ms - 1_000),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    completion["completion_hash"] = canonical_hash(completion)
    governance: dict[str, object] = {
        "schema_version": MATRIX_RESEARCH_GOVERNANCE_VERSION,
        "status": "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE",
        "selection_test_policy": "BLIND_ONCE",
        "development_only": False,
        "single_use_claim": True,
        "registration_id": "registration-1",
        "protocol_hash": protocol["protocol_hash"],
        "claim_hash": claim["claim_hash"],
        "completion_hash": completion["completion_hash"],
        "registered_at_ms": created_at_ms - 3_000,
        "started_at_ms": created_at_ms - 2_000,
        "completed_at_ms": created_at_ms - 1_000,
        "holdout_exposure_audit": exposure_audit,
        "protocol": protocol,
        "single_use_claim_receipt": claim,
        "completion_receipt": completion,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    governance["governance_hash"] = canonical_hash(governance)
    report["research_governance"] = governance
    report["batch_run_hash"] = strategy_matrix_run_hash(report)
    return report


class StrategyBenchmarkTests(unittest.TestCase):
    def test_matrix_report_resealed_registration_tamper_is_blocked(self) -> None:
        report = deepcopy(valid_matrix_report())
        snapshot = report["dataset_snapshot"]
        snapshot["registration_id"] = "different-registration"
        snapshot["snapshot_hash"] = canonical_hash({
            key: value for key, value in snapshot.items() if key != "snapshot_hash"
        })
        report["matrix_result_hash"] = strategy_matrix_result_hash(report)
        governance = report["research_governance"]
        completion = governance["completion_receipt"]
        completion["result_hash"] = report["matrix_result_hash"]
        completion["completion_hash"] = canonical_hash({
            key: value for key, value in completion.items() if key != "completion_hash"
        })
        governance["completion_hash"] = completion["completion_hash"]
        governance["governance_hash"] = canonical_hash({
            key: value for key, value in governance.items() if key != "governance_hash"
        })
        report["batch_run_hash"] = strategy_matrix_run_hash(report)

        result = verify_strategy_matrix_report(report)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_dataset_snapshot_registration_mismatch", result["blockers"])

    def test_matrix_report_created_at_must_match_completion_clock_without_freshness_gate(self) -> None:
        report = valid_matrix_report()
        completion_ms = report["research_governance"]["completion_receipt"]["completed_at_ms"]
        old_completion_ms = completion_ms - 30 * 24 * 60 * 60 * 1000
        protocol = report["research_governance"]["protocol"]
        claim = report["research_governance"]["single_use_claim_receipt"]
        protocol["registered_at_ms"] = old_completion_ms - 2_000
        protocol["registration_clock_attestation"] = attested_clock(old_completion_ms - 2_000)
        protocol["expires_at_ms"] = old_completion_ms + 60_000
        protocol["protocol_hash"] = canonical_hash({
            key: value for key, value in protocol.items() if key != "protocol_hash"
        })
        claim["protocol_hash"] = protocol["protocol_hash"]
        claim["registered_at_ms"] = protocol["registered_at_ms"]
        claim["started_at_ms"] = old_completion_ms - 1_000
        claim["clock_attestation"] = attested_clock(old_completion_ms - 1_000)
        claim["claim_hash"] = canonical_hash({
            key: value for key, value in claim.items() if key != "claim_hash"
        })
        completion = report["research_governance"]["completion_receipt"]
        completion["protocol_hash"] = protocol["protocol_hash"]
        completion["claim_hash"] = claim["claim_hash"]
        completion["completed_at_ms"] = old_completion_ms
        completion["clock_attestation"] = attested_clock(old_completion_ms)
        completion["completion_hash"] = canonical_hash({
            key: value for key, value in completion.items() if key != "completion_hash"
        })
        governance = report["research_governance"]
        governance.update({
            "protocol_hash": protocol["protocol_hash"],
            "claim_hash": claim["claim_hash"],
            "completion_hash": completion["completion_hash"],
            "registered_at_ms": protocol["registered_at_ms"],
            "started_at_ms": claim["started_at_ms"],
            "completed_at_ms": completion["completed_at_ms"],
        })
        report["dataset_snapshot"]["registration_id"] = governance["registration_id"]
        report["created_at"] = datetime.fromtimestamp(old_completion_ms / 1000, tz=timezone.utc).isoformat()
        report["matrix_result_hash"] = strategy_matrix_result_hash(report)
        completion["result_hash"] = report["matrix_result_hash"]
        completion["completion_hash"] = canonical_hash({
            key: value for key, value in completion.items() if key != "completion_hash"
        })
        governance["completion_hash"] = completion["completion_hash"]
        governance["governance_hash"] = canonical_hash({
            key: value for key, value in governance.items() if key != "governance_hash"
        })
        report["batch_run_hash"] = strategy_matrix_run_hash(report)
        result = verify_strategy_matrix_report(report)
        self.assertEqual(result["status"], "PASS", result["blockers"])

        report["created_at"] = datetime.fromtimestamp(
            (old_completion_ms + 1) / 1000,
            tz=timezone.utc,
        ).isoformat()
        report["matrix_result_hash"] = strategy_matrix_result_hash(report)
        completion["result_hash"] = report["matrix_result_hash"]
        completion["completion_hash"] = canonical_hash({
            key: value for key, value in completion.items() if key != "completion_hash"
        })
        governance = report["research_governance"]
        governance["completion_hash"] = completion["completion_hash"]
        governance["governance_hash"] = canonical_hash({
            key: value for key, value in governance.items() if key != "governance_hash"
        })
        report["batch_run_hash"] = strategy_matrix_run_hash(report)

        result = verify_strategy_matrix_report(report)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_created_at_completion_mismatch", result["blockers"])

        report["created_at"] = "invalid"
        result = verify_strategy_matrix_report(report)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_created_at_missing", result["blockers"])

    def test_matrix_evidence_binds_candidate_results_and_parameters(self) -> None:
        report = valid_matrix_report()
        risk = dict(report["batch_spec"]["risk"])
        params = {"fast_window": 20, "slow_window": 60}

        valid = verify_strategy_matrix_evidence(
            report,
            strategy_id="dual_ma",
            strategy_params=params,
            implementation_fingerprint="fingerprint-1",
            risk=risk,
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )
        tampered_report = deepcopy(report)
        tampered_report["forward_candidates"] = []
        tampered = verify_strategy_matrix_evidence(
            tampered_report,
            strategy_id="dual_ma",
            strategy_params=params,
            implementation_fingerprint="fingerprint-1",
            risk=risk,
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(valid["status"], "PASS")
        self.assertEqual(tampered["status"], "BLOCK")
        self.assertIn("matrix_result_hash_mismatch", tampered["blockers"])
        self.assertIn("strategy_not_forward_candidate", tampered["blockers"])

    def test_matrix_string_false_authority_is_rejected(self) -> None:
        report = valid_matrix_report()
        report["summary"]["paper_authorized"] = "false"

        result = verify_strategy_matrix_evidence(
            report,
            strategy_id="dual_ma",
            strategy_params={"fast_window": 20, "slow_window": 60},
            implementation_fingerprint="fingerprint-1",
            risk=dict(report["batch_spec"]["risk"]),
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_must_not_authorize_execution", result["blockers"])

    def test_matrix_nested_evidence_hashes_are_verified(self) -> None:
        report = valid_matrix_report()
        report["selection_regime_evidence"]["symbols"][0]["status"] = "BLOCK"
        report["batch_run_hash"] = strategy_matrix_run_hash(report)

        result = verify_strategy_matrix_evidence(
            report,
            strategy_id="dual_ma",
            strategy_params={"fast_window": 20, "slow_window": 60},
            implementation_fingerprint="fingerprint-1",
            risk=dict(report["batch_spec"]["strategy_specs"]["dual_ma"]["risk"]),
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("selection_regime_evidence_hash_mismatch", result["blockers"])

    def test_matrix_without_preregistered_blind_governance_is_blocked(self) -> None:
        report = valid_matrix_report()
        report["research_governance"] = {
            "schema_version": "strategy-matrix-governance-v1",
            "status": "DEVELOPMENT_ONLY",
            "selection_test_policy": "DEVELOPMENT_ONLY",
            "development_only": True,
            "single_use_claim": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        report["research_governance"]["governance_hash"] = canonical_hash(report["research_governance"])
        report["batch_run_hash"] = strategy_matrix_run_hash(report)

        result = verify_strategy_matrix_evidence(
            report,
            strategy_id="dual_ma",
            strategy_params={"fast_window": 20, "slow_window": 60},
            implementation_fingerprint="fingerprint-1",
            risk=dict(report["batch_spec"]["strategy_specs"]["dual_ma"]["risk"]),
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_not_preregistered_blind_single_use", result["blockers"])

    def test_matrix_malformed_nested_fields_fail_closed_without_crashing(self) -> None:
        report = valid_matrix_report()
        report["selection_regime_evidence"] = "not-a-mapping"
        report["selection_cells"] = 17
        report["confirmations"] = {"strategy_id": "dual_ma"}
        report["batch_run_hash"] = strategy_matrix_run_hash(report)

        result = verify_strategy_matrix_evidence(
            report,
            strategy_id="dual_ma",
            strategy_params={"fast_window": 20, "slow_window": 60},
            implementation_fingerprint="fingerprint-1",
            risk=dict(report["batch_spec"]["strategy_specs"]["dual_ma"]["risk"]),
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_field_type_invalid:selection_regime_evidence", result["blockers"])
        self.assertIn("matrix_field_type_invalid:selection_cells", result["blockers"])
        self.assertIn("matrix_field_type_invalid:confirmations", result["blockers"])

    def test_matrix_non_mapping_report_fails_closed_without_crashing(self) -> None:
        result = verify_strategy_matrix_evidence(
            ["not", "a", "report"],
            strategy_id="dual_ma",
            strategy_params={"fast_window": 20, "slow_window": 60},
            implementation_fingerprint="fingerprint-1",
            risk={},
            symbol="AAPL",
            now_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("matrix_report_type_invalid", result["blockers"])

    def test_calendar_schedule_uses_shared_dates_with_asset_specific_indexes(self) -> None:
        stock_rows = [
            {"date": f"2025-01-{day:02d}", "complete": True}
            for day in range(1, 31)
        ]
        crypto_rows = [
            {"date": f"2025-01-{day:02d}", "complete": True}
            for day in range(1, 31)
        ]
        schedule = build_calendar_split_schedule(
            {"AAPL": {"rows": stock_rows}, "BTC-USDT": {"rows": crypto_rows}},
            minimum_segment_rows=5,
        )

        self.assertEqual(schedule["status"], "PASS")
        self.assertEqual(schedule["common_start"], "2025-01-01")
        self.assertEqual(schedule["common_end"], "2025-01-30")
        self.assertEqual(schedule["symbol_boundaries"]["AAPL"]["counts"], {"train": 15, "validation": 7, "test": 8})

    def test_calendar_schedule_rejects_invalid_ratios_instead_of_clamping(self) -> None:
        schedule = build_calendar_split_schedule(
            {"AAPL": {"rows": [{"date": "2025-01-01", "complete": True}]}},
            train_ratio=0.95,
            validation_ratio=0.25,
            minimum_segment_rows=1,
        )

        self.assertEqual(schedule["status"], "BLOCK")
        self.assertEqual(schedule["train_ratio"], 0.95)
        self.assertIn("numeric_parameter_contract:train_ratio:above_maximum:0.7", schedule["blockers"])

    def test_daily_batch_alignment_trims_to_common_completed_date(self) -> None:
        payloads = {
            "AAPL": {"source": "stock", "rows": [
                {"date": "2026-07-29", "complete": True},
                {"date": "2026-07-30", "complete": True},
            ]},
            "BTC-USDT": {"source": "crypto", "rows": [
                {"date": "2026-07-29", "complete": True},
                {"date": "2026-07-30", "complete": True},
                {"date": "2026-07-31", "complete": True},
                {"date": "2026-08-01", "complete": False},
            ]},
        }

        aligned, report = align_completed_daily_payloads(payloads)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["common_as_of"], "2026-07-30")
        self.assertEqual(len(aligned["BTC-USDT"]["rows"]), 2)
        self.assertEqual(report["aligned_endpoints"]["AAPL"], "2026-07-30")
        self.assertEqual(report["aligned_endpoints"]["BTC-USDT"], "2026-07-30")

    def test_daily_batch_alignment_blocks_stale_symbol(self) -> None:
        payloads = {
            "AAPL": {"rows": [{"date": "2026-07-20", "complete": True}]},
            "BTC-USDT": {"rows": [{"date": "2026-07-30", "complete": True}]},
        }

        aligned, report = align_completed_daily_payloads(payloads, max_endpoint_skew_days=3)

        self.assertEqual(aligned, {})
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("endpoint_skew_days:10>3", report["blockers"])

    def test_daily_batch_alignment_accepts_stock_weekend_boundary(self) -> None:
        payloads = {
            "AAPL": {"rows": [
                {"date": "2026-07-31", "complete": True},
                {"date": "2026-08-03", "complete": True},
                {"date": "2026-08-04", "complete": True},
                {"date": "2026-08-05", "complete": True},
            ]},
            "BTC-USDT": {"rows": [
                {"date": "2026-08-01", "complete": True},
                {"date": "2026-08-02", "complete": True},
                {"date": "2026-08-03", "complete": True},
                {"date": "2026-08-04", "complete": True},
                {"date": "2026-08-05", "complete": True},
            ]},
        }

        aligned, report = align_completed_daily_payloads(payloads)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["common_start"], "2026-08-03")
        self.assertEqual(report["common_as_of"], "2026-08-05")
        self.assertEqual(aligned["AAPL"]["rows"][0]["date"], "2026-08-03")
        self.assertEqual(aligned["BTC-USDT"]["rows"][0]["date"], "2026-08-03")

    def test_daily_batch_alignment_blocks_large_start_boundary_gap(self) -> None:
        payloads = {
            "AAPL": {"rows": [
                {"date": "2026-01-01", "complete": True},
                {"date": "2026-01-20", "complete": True},
                {"date": "2026-01-30", "complete": True},
            ]},
            "BTC-USDT": {"rows": [
                {"date": "2026-01-02", "complete": True},
                {"date": "2026-01-30", "complete": True},
            ]},
        }

        aligned, report = align_completed_daily_payloads(payloads, max_boundary_skew_days=7)

        self.assertEqual(aligned, {})
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("AAPL:start_boundary_skew_days:18>7", report["blockers"])

    def test_confirmation_alignment_requires_selection_as_of(self) -> None:
        payloads = {"QQQ": {"rows": [{"date": "2026-07-29", "complete": True}]}}

        aligned, report = align_completed_daily_payloads(payloads, required_as_of="2026-07-30")

        self.assertEqual(aligned, {})
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn(
            "QQQ:endpoint_before_required_as_of:2026-07-29<2026-07-30",
            report["blockers"],
        )

    def test_selection_gate_applies_cross_symbol_and_multiple_trial_controls(self) -> None:
        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]

        result = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["eligible_for_confirmation"])
        self.assertGreater(result["multiple_trial_penalty"], 0)
        self.assertLess(result["adjusted_score"], result["raw_score"])

    def test_selection_gate_blocks_a_strategy_without_oos_excess_return(self) -> None:
        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        for cell in cells:
            cell["test_excess_return_pct"] = -1.0

        result = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("median_test_excess_not_positive", result["blockers"])

    def test_selection_gate_blocks_failed_temporal_and_lookahead_checks(self) -> None:
        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        for cell in cells[:3]:
            cell["temporal_status"] = "BLOCK"
            cell["walk_forward_status"] = "BLOCK"
        cells[-1]["lookahead_status"] = "BLOCK"

        result = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("temporal_pass_symbols:3<4", result["blockers"])
        self.assertIn("walk_forward_pass_symbols:3<4", result["blockers"])
        self.assertIn("lookahead_pass_symbols:5<6", result["blockers"])

    def test_selection_gate_requires_positive_score_after_trial_penalty(self) -> None:
        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        for cell in cells:
            cell.update({
                "validation_return_pct": 0.01,
                "test_return_pct": 0.01,
                "test_excess_return_pct": 0.01,
                "test_max_drawdown_pct": 0.0,
                "test_sharpe": 0.0,
            })

        result = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertLess(result["adjusted_score"], 0)
        self.assertIn("multiple_trial_adjusted_score_not_positive", result["blockers"])

    def test_selection_gate_rejects_pseudo_numeric_or_missing_trade_evidence(self) -> None:
        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        cells[0]["test_trade_count"] = "2"
        pseudo_numeric = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )
        self.assertEqual(pseudo_numeric["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", pseudo_numeric["blockers"])

        cells = [passing_cell(symbol) for symbol in ("AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT")]
        cells[0]["test_return_pct"] = None
        missing = aggregate_strategy_selection(
            "dual_ma",
            cells,
            strategy_trials=8,
            required_symbols=6,
        )
        self.assertEqual(missing["status"], "BLOCK")
        self.assertIn("usable_symbols:5<6", missing["blockers"])

    def test_confirmation_requires_every_reserved_symbol(self) -> None:
        result = confirmation_summary("dual_ma", [passing_cell("QQQ")], required_symbols=2)

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["forward_candidate"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_confirmation_rejects_pseudo_numeric_trade_count(self) -> None:
        cell = passing_cell("QQQ")
        cell["test_trade_count"] = "2"
        result = confirmation_summary("dual_ma", [cell], required_symbols=1)

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("QQQ:test_trade_count_missing_or_invalid", result["blockers"])


if __name__ == "__main__":
    unittest.main()
