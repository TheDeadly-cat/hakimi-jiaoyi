from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_backtest import (
    audit_relative_strength_causality,
    prepare_attested_portfolio_dataset,
    prepare_portfolio_dataset,
    relative_strength_settings_from_spec,
    run_causal_relative_strength_backtest,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services import portfolio_backtest as portfolio_backtest_module
from exchange_terminal.services.portfolio_universe import (
    build_membership_source_evidence,
    build_point_in_time_universe_contract,
)
from exchange_terminal.services.security_lifecycle import align_security_to_market_calendar


def make_rows(count: int, drift: float, *, wave: float = 0.001) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    close = 100.0
    trading_date = date(2024, 1, 2)
    for index in range(count):
        while trading_date.weekday() >= 5:
            trading_date += timedelta(days=1)
        previous = close
        daily_return = drift + (wave if index % 2 == 0 else -wave)
        close = max(1.0, previous * (1.0 + daily_return))
        rows.append({
            "date": trading_date.isoformat(),
            "ts_ms": (trading_date - date(1970, 1, 1)).days * 86_400_000,
            "open": previous,
            "high": max(previous, close) * 1.01,
            "low": min(previous, close) * 0.99,
            "close": close,
            "volume": 1_000_000,
            "complete": True,
        })
        trading_date += timedelta(days=1)
    return rows


def make_payloads(count: int = 220, *, benchmark_drift: float = 0.002) -> dict[str, dict[str, object]]:
    return {
        "SPY": {"source": "test", "rows": make_rows(count, benchmark_drift)},
        "AAA": {"source": "test", "rows": make_rows(count, 0.004)},
        "BBB": {"source": "test", "rows": make_rows(count, 0.003)},
        "CCC": {"source": "test", "rows": make_rows(count, 0.0015)},
    }


def first_planned_rebalance(report: dict[str, object]) -> dict[str, object]:
    return next(
        item
        for item in report["decisions"]
        if item.get("reason") == "relative_strength_rebalance"
    )


class PortfolioBacktestTests(unittest.TestCase):
    def test_frozen_settings_preserve_explicit_zero_values(self) -> None:
        settings = relative_strength_settings_from_spec({
            "top_n": 0,
            "gross_target_pct": 0.0,
            "max_entry_participation_pct": 0.0,
            "max_exit_participation_pct": 0.0,
            "fee_rate": 0.0,
            "slippage_bps": 0.0,
        })

        self.assertEqual(settings["top_n"], 0)
        self.assertEqual(settings["gross_target_pct"], 0.0)
        self.assertEqual(settings["max_entry_participation_pct"], 0.0)
        self.assertEqual(settings["max_exit_participation_pct"], 0.0)
        self.assertEqual(settings["fee_rate"], 0.0)
        self.assertEqual(settings["slippage_bps"], 0.0)

    @staticmethod
    def point_in_time_contract(
        payloads: dict[str, dict[str, object]],
        records: list[dict[str, str]],
    ) -> dict[str, object]:
        rows = list(payloads["SPY"]["rows"])
        enriched = []
        for record in records:
            evidence_ref = f"https://example.test/{record['symbol']}/{record['effective_from']}"
            evidence = build_membership_source_evidence(
                symbol=record["symbol"],
                effective_from=record["effective_from"],
                effective_to=record["effective_to"],
                source_authority="OFFICIAL_INDEX_PROVIDER",
                source_name="Official Test Index",
                evidence_ref=evidence_ref,
                source_document_sha256=hashlib.sha256(
                    f"document:{record['symbol']}:{record['effective_from']}".encode("utf-8")
                ).hexdigest(),
                evidence_published_at="2023-12-01T00:00:00Z",
                retrieved_at="2023-12-02T00:00:00Z",
            )
            enriched.append({
                **record,
                "source_authority": "OFFICIAL_INDEX_PROVIDER",
                "source_name": "Official Test Index",
                "evidence_ref": evidence_ref,
                "evidence_sha256": evidence["evidence_sha256"],
                "evidence_published_at": "2023-12-01T00:00:00Z",
                "evidence_payload": evidence,
            })
        return build_point_in_time_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            declared_at="2024-01-01T00:00:00Z",
            selection_basis="OFFICIAL_TEST_INDEX",
            selection_rule_id="official-test-index-v1",
            coverage_start=str(rows[0]["date"]),
            coverage_end=str(rows[-1]["date"]),
            membership_records=enriched,
        )

    def test_execution_risk_buffer_keeps_targets_below_the_hard_net_limit(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(220),
            benchmark_symbol="SPY",
            lookback=60,
            gross_target_pct=60.0,
            execution_risk_buffer_pct=0.25,
        )
        planned = [
            item for item in report["decisions"]
            if item.get("reason") == "relative_strength_rebalance" and item.get("target_symbols")
        ]

        self.assertTrue(report["ok"])
        self.assertTrue(planned)
        self.assertEqual(report["run_spec"]["execution_risk_buffer_pct"], 0.25)
        self.assertTrue(all(float(item["target_allocation_pct"]) <= 59.75 + 1e-9 for item in planned))
        self.assertTrue(all(
            abs(
                float(item["uncushioned_target_allocation_pct"])
                - float(item["target_allocation_pct"])
                - 0.25
            ) <= 1e-6
            for item in planned
        ))

    def test_dataset_hash_is_independent_from_strategy_schema_version(self) -> None:
        payloads = make_payloads(180)
        baseline = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=160)
        with patch.object(
            portfolio_backtest_module,
            "PORTFOLIO_BACKTEST_SCHEMA_VERSION",
            "causal-relative-strength-portfolio-test-only",
        ):
            changed_engine = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=160)

        self.assertEqual(baseline["manifest"]["data_hash"], changed_engine["manifest"]["data_hash"])
        self.assertEqual(baseline["manifest"]["manifest_hash"], changed_engine["manifest"]["manifest_hash"])
        self.assertNotEqual(
            baseline["manifest"]["strategy_schema_version"],
            changed_engine["manifest"]["strategy_schema_version"],
        )

    def test_point_in_time_membership_prevents_selection_before_effective_date(self) -> None:
        payloads = make_payloads(240)
        rows = list(payloads["SPY"]["rows"])
        aaa_start = str(rows[180]["date"])
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": aaa_start, "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(rows[0]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(rows[0]["date"]), "effective_to": ""},
        ])

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            universe_contract=contract,
            lookback=60,
            top_n=1,
            rank_buffer=0,
            max_per_cluster=1,
        )
        planned = [item for item in report["decisions"] if item.get("reason") == "relative_strength_rebalance"]
        before = [item for item in planned if str(item["signal_date"]) < aaa_start]
        after = [item for item in planned if str(item["signal_date"]) >= aaa_start]

        self.assertTrue(report["ok"])
        self.assertTrue(before)
        self.assertTrue(after)
        self.assertTrue(all("AAA" not in item["target_symbols"] for item in before))
        self.assertTrue(any("AAA" in item["target_symbols"] for item in after))
        self.assertEqual(report["run_spec"]["universe_contract_hash"], contract["contract_hash"])
        self.assertTrue(report["run_spec"]["point_in_time_universe_verified"])

    def test_membership_removal_forces_a_held_symbol_out(self) -> None:
        payloads = make_payloads(240)
        rows = list(payloads["SPY"]["rows"])
        aaa_end = str(rows[175]["date"])
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(rows[0]["date"]), "effective_to": aaa_end},
            {"symbol": "BBB", "effective_from": str(rows[0]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(rows[0]["date"]), "effective_to": ""},
        ])

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            universe_contract=contract,
            lookback=60,
            top_n=1,
            max_per_cluster=1,
        )

        self.assertTrue(report["ok"])
        self.assertGreaterEqual(report["forced_universe_exit_count"], 1)
        self.assertTrue(any(item.get("reason") == "universe_membership_exit" for item in report["orders"]))
        self.assertNotIn("AAA", report["final_positions"])

    def test_point_in_time_universe_keeps_benchmark_history_for_a_late_listing(self) -> None:
        payloads = make_payloads(260)
        benchmark_rows = list(payloads["SPY"]["rows"])
        listing_index = 130
        payloads["BBB"]["rows"] = make_rows(260, 0.01)[listing_index:]
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(benchmark_rows[listing_index]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
        ])

        prepared = prepare_portfolio_dataset(
            payloads,
            benchmark_symbol="SPY",
            minimum_rows=180,
            universe_contract=contract,
        )

        self.assertEqual(prepared["status"], "PASS")
        self.assertEqual(prepared["manifest"]["first"], benchmark_rows[0]["date"])
        self.assertEqual(prepared["manifest"]["row_count"], 260)
        self.assertEqual(
            prepared["manifest"]["coverage"]["symbols"]["BBB"]["outside_universe_session_count"],
            listing_index,
        )
        self.assertTrue(all(
            row["trading_status"] == "OUTSIDE_UNIVERSE"
            and row["tradable"] is False
            and row["valuation_only"] is True
            for row in prepared["rows"]["BBB"][:listing_index]
        ))

    def test_outside_universe_sentinel_replays_exactly_and_rejects_tampering(self) -> None:
        payloads = make_payloads(220)
        benchmark_rows = list(payloads["SPY"]["rows"])
        listing_index = 80
        payloads["BBB"]["rows"] = make_rows(220, 0.006)[listing_index:]
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(benchmark_rows[listing_index]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
        ])
        first = prepare_portfolio_dataset(
            payloads,
            benchmark_symbol="SPY",
            minimum_rows=180,
            universe_contract=contract,
        )
        replay_payloads = {
            symbol: {
                **{key: value for key, value in payloads[symbol].items() if key != "rows"},
                "adjustment_evidence": first["manifest"]["adjustment_evidence"][symbol],
                "rows": deepcopy(first["rows"][symbol]),
            }
            for symbol in first["manifest"]["symbols"]
        }

        replay = prepare_portfolio_dataset(
            replay_payloads,
            benchmark_symbol="SPY",
            minimum_rows=180,
            universe_contract=contract,
        )
        tampered_payloads = deepcopy(replay_payloads)
        tampered_payloads["BBB"]["rows"][0].update({
            "open": 2.0,
            "high": 2.0,
            "low": 2.0,
            "close": 2.0,
        })
        tampered = prepare_portfolio_dataset(
            tampered_payloads,
            benchmark_symbol="SPY",
            minimum_rows=180,
            universe_contract=contract,
        )

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(replay["status"], "PASS")
        self.assertEqual(first["manifest"]["data_hash"], replay["manifest"]["data_hash"])
        self.assertEqual(tampered["status"], "BLOCK")
        self.assertTrue(any(
            "outside_universe_sentinel_invalid" in blocker
            for blocker in tampered["manifest"]["blockers"]
        ))

    def test_missing_price_after_membership_start_is_not_filled_as_outside_universe(self) -> None:
        payloads = make_payloads(220)
        benchmark_rows = list(payloads["SPY"]["rows"])
        payloads["BBB"]["rows"] = make_rows(220, 0.006)[80:]
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(benchmark_rows[50]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
        ])

        prepared = prepare_portfolio_dataset(
            payloads,
            benchmark_symbol="SPY",
            minimum_rows=180,
            universe_contract=contract,
        )

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertIn(
            "BBB:lifecycle:unverified_missing_sessions:30",
            prepared["manifest"]["blockers"],
        )

    def test_outside_universe_alignment_requires_a_contract_hash_and_never_seeds_suspension_price(self) -> None:
        rows = make_rows(3, 0.001)
        dates = [str(row["date"]) for row in rows]
        missing_hash = align_security_to_market_calendar(
            symbol="BBB",
            rows_by_date={dates[2]: dict(rows[2])},
            expected_dates=dates,
            universe_membership_start=dates[1],
            universe_contract_hash="",
        )
        suspended_without_real_price = align_security_to_market_calendar(
            symbol="BBB",
            rows_by_date={dates[2]: dict(rows[2])},
            expected_dates=dates,
            lifecycle_events=[{
                "status": "SUSPENDED",
                "start_date": dates[1],
                "end_date": dates[1],
            }],
            universe_membership_start=dates[1],
            universe_contract_hash="a" * 64,
        )

        self.assertEqual(missing_hash["status"], "BLOCK")
        self.assertIn("universe_membership_contract_hash_invalid", missing_hash["blockers"])
        self.assertEqual(suspended_without_real_price["status"], "BLOCK")
        self.assertIn(
            f"nontradable_gap_without_prior_price:{dates[1]}:SUSPENDED",
            suspended_without_real_price["blockers"],
        )

    def test_late_listing_sentinel_cannot_enter_signal_or_volatility_history(self) -> None:
        payloads = make_payloads(260)
        benchmark_rows = list(payloads["SPY"]["rows"])
        listing_index = 130
        history_ready_index = listing_index + 63
        payloads["BBB"]["rows"] = make_rows(260, 0.01)[listing_index:]
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(benchmark_rows[listing_index]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
        ])

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            universe_contract=contract,
            lookback=60,
            top_n=1,
            rank_buffer=0,
            max_per_cluster=1,
        )
        decisions = [
            item for item in report["decisions"]
            if item.get("reason") == "relative_strength_rebalance"
        ]
        pre_ready = [
            item for item in decisions
            if str(benchmark_rows[listing_index]["date"])
            <= str(item["signal_date"])
            < str(benchmark_rows[history_ready_index]["date"])
        ]
        post_ready = [
            item for item in decisions
            if str(item["signal_date"]) >= str(benchmark_rows[history_ready_index]["date"])
        ]

        self.assertTrue(report["ok"])
        self.assertTrue(pre_ready)
        self.assertTrue(post_ready)
        self.assertTrue(all("BBB" not in item["scores"] for item in pre_ready))
        self.assertTrue(all(
            "BBB" in item["insufficient_causal_history_symbols"]
            for item in pre_ready
        ))
        self.assertTrue(any("BBB" in item["scores"] for item in post_ready))
        self.assertTrue(all(
            order["symbol"] != "BBB"
            or str(order["signal_date"]) >= str(benchmark_rows[history_ready_index]["date"])
            for order in report["orders"]
        ))

    def test_causal_prefix_before_listing_accepts_no_rows_only_while_outside_universe(self) -> None:
        payloads = make_payloads(300)
        benchmark_rows = list(payloads["SPY"]["rows"])
        listing_index = 200
        payloads["BBB"]["rows"] = make_rows(300, 0.01)[listing_index:]
        contract = self.point_in_time_contract(payloads, [
            {"symbol": "AAA", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
            {"symbol": "BBB", "effective_from": str(benchmark_rows[listing_index]["date"]), "effective_to": ""},
            {"symbol": "CCC", "effective_from": str(benchmark_rows[0]["date"]), "effective_to": ""},
        ])

        audit = audit_relative_strength_causality(
            payloads=payloads,
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB", "CCC"],
            universe_contract=contract,
            lookback=60,
            top_n=1,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(item["passed"] for item in audit["checkpoints"]))

    def test_attested_prepare_binds_the_aligned_row_window(self) -> None:
        calls: list[dict[str, object]] = []

        def attest(**kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            rows = list(kwargs.get("rows") or [])
            snapshot_hash = ":".join([
                str(kwargs.get("symbol") or ""),
                str(rows[0]["date"] if rows else ""),
                str(rows[-1]["date"] if rows else ""),
                str(len(rows)),
            ])
            return {"status": "PASS", "current": {"snapshot_hash": snapshot_hash}}

        prepared = prepare_attested_portfolio_dataset(
            make_payloads(150),
            benchmark_symbol="SPY",
            minimum_rows=140,
            attest_backtest_rows=attest,
            dataset_lineage_id="experiment-test-aligned",
        )

        self.assertEqual(prepared["status"], "PASS")
        self.assertEqual(len(calls), 4)
        self.assertEqual(set(prepared["payloads"]), {"SPY", "AAA", "BBB", "CCC"})
        for symbol in prepared["manifest"]["symbols"]:
            evidence = prepared["manifest"]["data_revision_evidence"][symbol]
            self.assertEqual(evidence["backtest_dataset"]["current"]["snapshot_hash"], f"{symbol}:{prepared['manifest']['first']}:{prepared['manifest']['last']}:150")

    def test_adjustment_string_authorization_cannot_enter_backtest(self) -> None:
        with patch.object(
            portfolio_backtest_module,
            "build_adjustment_evidence",
            return_value={"backtest_eligible": "false", "blockers": []},
        ):
            prepared = prepare_portfolio_dataset(
                make_payloads(150),
                benchmark_symbol="SPY",
                minimum_rows=140,
            )

        self.assertEqual(prepared["status"], "BLOCK")
        self.assertTrue(any("unverified_adjustment_contract" in item for item in prepared["manifest"]["blockers"]))

    def test_lifecycle_boolean_strings_use_permission_and_hazard_semantics(self) -> None:
        row = make_rows(1, 0.002)[0]
        row.update({
            "tradable": "false",
            "calendar_session": "false",
            "valuation_only": "false",
            "mandatory_cash_settlement": "false",
        })
        normalized = portfolio_backtest_module._normalize_symbol_rows([row])
        item = normalized[str(row["date"])]

        self.assertFalse(item["tradable"])
        self.assertFalse(item["calendar_session"])
        self.assertFalse(item["valuation_only"])
        self.assertFalse(item["mandatory_cash_settlement"])

        row["valuation_only"] = "malformed"
        row["mandatory_cash_settlement"] = "malformed"
        malformed = portfolio_backtest_module._normalize_symbol_rows([row])[str(row["date"])]
        self.assertTrue(malformed["valuation_only"])
        self.assertTrue(malformed["mandatory_cash_settlement"])

    def test_cutoff_slice_attests_the_exact_rows(self) -> None:
        calls: list[dict[str, object]] = []

        def attest(**kwargs: object) -> dict[str, object]:
            calls.append(dict(kwargs))
            return {
                "status": "PASS",
                "current": {"snapshot_hash": "cutoff-snapshot"},
            }

        rows = make_rows(5, 0.002)
        cutoff = str(rows[2]["date"])
        payload = {
            "symbol": "AAA",
            "source": "test",
            "adjustment_basis": "RAW_UNADJUSTED",
            "adjustment_evidence": {"corporate_actions_hash": "actions-hash"},
            "corporate_actions": [
                {"action_type": "SPLIT", "event_date": rows[1]["date"], "ratio": 2.0},
                {"action_type": "SPLIT", "event_date": rows[4]["date"], "ratio": 3.0},
            ],
            "data_revision_evidence": {
                "status": "PASS",
                "accepted_cache": {"status": "PASS"},
            },
            "rows": rows,
        }

        sliced = slice_portfolio_payload_through_date(
            payload,
            cutoff,
            attest_backtest_rows=attest,
            dataset_lineage_id="experiment-test-cutoff",
        )

        self.assertEqual(len(sliced["rows"]), 3)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]["rows"]), 3)
        self.assertEqual(calls[0]["dataset_lineage_id"], "experiment-test-cutoff")
        self.assertEqual(len(sliced["corporate_actions"]), 1)
        expected_actions = portfolio_backtest_module.normalize_corporate_actions(
            "AAA", "test", sliced["corporate_actions"]
        )
        self.assertEqual(
            calls[0]["corporate_actions_hash"],
            portfolio_backtest_module._canonical_hash(expected_actions),
        )
        self.assertNotEqual(calls[0]["corporate_actions_hash"], "actions-hash")
        self.assertEqual(
            sliced["data_revision_evidence"]["backtest_dataset"]["current"]["snapshot_hash"],
            "cutoff-snapshot",
        )

    def test_unverified_stock_adjustment_contract_blocks_portfolio_research(self) -> None:
        payloads = make_payloads(150)
        payloads["AAA"]["source"] = "yahoo"

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(item.startswith("AAA:adjustment:adjustment_basis_unverified") for item in report["manifest"]["blockers"]))

    def test_stale_adjustment_evidence_cannot_override_current_payload_basis(self) -> None:
        payloads = make_payloads(150)
        initial = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)
        payloads["AAA"]["adjustment_evidence"] = initial["manifest"]["adjustment_evidence"]["AAA"]
        payloads["AAA"]["adjustment_basis"] = "BACKWARD_ADJUSTED_HFQ"

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn(
            "AAA:adjustment:adjustment_basis_not_cash_executable:BACKWARD_ADJUSTED_HFQ",
            report["manifest"]["blockers"],
        )

    def test_unresolved_historical_revision_blocks_portfolio_research(self) -> None:
        payloads = make_payloads(150)
        payloads["AAA"]["data_revision_evidence"] = {
            "status": "BLOCK",
            "accepted_cache": {
                "status": "BLOCK",
                "blockers": ["completed_prices_revised:1"],
            },
            "backtest_dataset": {"status": "PASS"},
        }

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn(
            "AAA:data_revision:completed_prices_revised:1",
            report["manifest"]["blockers"],
        )

    def test_non_blocking_revision_stage_does_not_change_frozen_dataset_hash(self) -> None:
        payloads = make_payloads(150)
        base_revision = {
            "status": "PASS",
            "accepted_cache": {
                "status": "PASS",
                "current": {"snapshot_hash": "accepted-snapshot"},
            },
            "backtest_dataset": {
                "status": "PASS",
                "current": {"snapshot_hash": "backtest-snapshot"},
            },
        }
        payloads["AAA"]["data_revision_evidence"] = base_revision
        first = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        payloads["AAA"]["data_revision_evidence"] = {
            **base_revision,
            "status": "REVIEW",
            "accepted_cache": {
                **base_revision["accepted_cache"],
                "status": "REVIEW",
                "classification": "ADJUSTED_METADATA_REVISION",
            },
        }
        replay = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(replay["status"], "PASS")
        self.assertEqual(first["manifest"]["data_hash"], replay["manifest"]["data_hash"])

    def test_append_only_accepted_cache_snapshot_does_not_change_frozen_dataset_hash(self) -> None:
        payloads = make_payloads(150)
        payloads["AAA"]["data_revision_evidence"] = {
            "status": "PASS",
            "accepted_cache": {
                "status": "PASS",
                "current": {"snapshot_hash": "accepted-snapshot-v1"},
            },
            "backtest_dataset": {
                "status": "PASS",
                "current": {"snapshot_hash": "backtest-snapshot"},
            },
        }
        first = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)
        payloads["AAA"]["data_revision_evidence"]["accepted_cache"]["current"]["snapshot_hash"] = "accepted-snapshot-v2"
        revised = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(first["manifest"]["data_hash"], revised["manifest"]["data_hash"])

    def test_dataset_requires_a_common_calendar(self) -> None:
        payloads = make_payloads(150)
        payloads["AAA"]["rows"] = payloads["AAA"]["rows"][:-20]

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("AAA:lifecycle:unverified_missing_sessions:20", report["manifest"]["blockers"])

    def test_non_session_weekend_row_is_rejected(self) -> None:
        payloads = make_payloads(150)
        invalid = dict(payloads["AAA"]["rows"][-5])
        invalid_date = date.fromisoformat(str(invalid["date"]))
        while invalid_date.weekday() != 5:
            invalid_date += timedelta(days=1)
        invalid["date"] = invalid_date.isoformat()
        invalid["ts_ms"] = (invalid_date - date(1970, 1, 1)).days * 86_400_000
        payloads["AAA"]["rows"][-5] = invalid

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any("non_session_dates_present" in item for item in report["manifest"]["blockers"]))

    def test_coverage_truncation_is_explicit_instead_of_silent_intersection(self) -> None:
        payloads = make_payloads(220)
        payloads["AAA"]["rows"] = payloads["AAA"]["rows"][20:]

        report = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=180)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["manifest"]["coverage"]["excluded_benchmark_prefix_sessions"], 20)
        self.assertIn("universe_common_coverage_excludes_benchmark_prefix:20", report["manifest"]["warnings"])

    def test_aligned_lifecycle_dataset_replay_keeps_the_same_hash(self) -> None:
        payloads = make_payloads(180)
        suspended_date = str(payloads["AAA"]["rows"][150]["date"])
        payloads["AAA"]["rows"].pop(150)
        payloads["AAA"]["trading_status_events"] = [{
            "status": "SUSPENDED",
            "start_date": suspended_date,
            "end_date": suspended_date,
        }]
        first = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)
        replay_payloads = {
            symbol: {
                **{key: value for key, value in payloads[symbol].items() if key != "rows"},
                "adjustment_evidence": first["manifest"]["adjustment_evidence"][symbol],
                "rows": list(first["rows"][symbol]),
            }
            for symbol in first["manifest"]["symbols"]
        }

        replay = prepare_portfolio_dataset(replay_payloads, benchmark_symbol="SPY", minimum_rows=140)

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(replay["status"], "PASS")
        self.assertEqual(first["manifest"]["data_hash"], replay["manifest"]["data_hash"])

    def test_signal_at_close_executes_on_the_next_open(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            rebalance_interval=5,
        )

        self.assertTrue(report["ok"])
        first = report["orders"][0]
        self.assertEqual(first["side"], "BUY")
        self.assertEqual(first["symbol"], "AAA")
        self.assertNotEqual(first["signal_date"], first["date"])
        self.assertEqual(first["fill_basis"], "NEXT_BAR_OPEN")
        self.assertGreater(report["total_fees"], 0.0)
        self.assertFalse(report["paper_authorized"])

    def test_illiquid_top_ranked_symbol_is_excluded_before_selection(self) -> None:
        payloads = make_payloads()
        for row in payloads["AAA"]["rows"]:
            row["volume"] = 10

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            minimum_median_dollar_volume=5_000_000,
        )

        first = first_planned_rebalance(report)
        self.assertEqual(first["target_symbols"], ["BBB"])
        self.assertIn("AAA", first["liquidity_excluded_symbols"])
        self.assertGreater(report["liquidity_exclusion_count"], 0)

    def test_entry_gap_is_blocked_without_blocking_future_research(self) -> None:
        payloads = make_payloads()
        baseline = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )
        first_execution_date = baseline["orders"][0]["date"]
        execution_index = next(
            index
            for index, row in enumerate(payloads["AAA"]["rows"])
            if row["date"] == first_execution_date
        )
        execution_row = payloads["AAA"]["rows"][execution_index]
        previous_close = float(payloads["AAA"]["rows"][execution_index - 1]["close"])
        execution_row["open"] = previous_close * 1.20
        execution_row["high"] = max(float(execution_row["high"]), float(execution_row["open"]) * 1.01)
        execution_row["low"] = min(float(execution_row["low"]), float(execution_row["close"]) * 0.99)

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            max_entry_open_gap_pct=5,
        )

        event = next(item for item in report["execution_events"] if item["status"] == "BLOCKED_ENTRY_GAP")
        self.assertEqual(event["symbol"], "AAA")
        self.assertGreater(event["open_gap_pct"], 5.0)
        self.assertGreater(report["gap_block_count"], 0)
        self.assertTrue(report["ok"])

    def test_zero_entry_gap_limit_does_not_disable_the_guard(self) -> None:
        payloads = make_payloads()
        for row in payloads["AAA"]["rows"]:
            row["open"] = float(row["open"]) * 1.001
            row["high"] = max(float(row["high"]), float(row["open"]))
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            max_entry_open_gap_pct=0,
        )

        self.assertTrue(report["ok"])
        self.assertEqual([item for item in report["orders"] if item["side"] == "BUY"], [])
        self.assertTrue(any(
            item["side"] == "BUY" and item["status"] == "BLOCKED_ENTRY_GAP"
            for item in report["execution_events"]
        ))

    def test_open_fill_capacity_uses_only_prior_completed_volume(self) -> None:
        low_future_volume = make_payloads()
        high_future_volume = make_payloads()
        baseline = run_causal_relative_strength_backtest(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )
        first_execution_date = baseline["orders"][0]["date"]
        execution_index = next(
            index
            for index, row in enumerate(low_future_volume["AAA"]["rows"])
            if row["date"] == first_execution_date
        )
        low_future_volume["AAA"]["rows"][execution_index]["volume"] = 1
        high_future_volume["AAA"]["rows"][execution_index]["volume"] = 1_000_000_000

        low = run_causal_relative_strength_backtest(
            payloads=low_future_volume,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )
        high = run_causal_relative_strength_backtest(
            payloads=high_future_volume,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )

        self.assertEqual(low["orders"][0], high["orders"][0])

    def test_large_account_receives_a_capacity_limited_partial_fill(self) -> None:
        payloads = make_payloads()
        for row in payloads["AAA"]["rows"]:
            row["volume"] = 100_000

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            initial_cash=10_000_000,
            minimum_median_dollar_volume=5_000_000,
            max_entry_participation_pct=1.0,
        )

        first = report["orders"][0]
        self.assertEqual(first["status"], "PARTIAL")
        self.assertLessEqual(first["participation_pct"], 1.000001)
        self.assertGreater(first["impact_bps"], 0.0)
        self.assertGreater(report["partial_fill_count"], 0)

    def test_zero_exit_participation_never_fabricates_exit_liquidity(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            top_n=2,
            lookback=60,
            minimum_trade_pct=0,
            max_exit_participation_pct=0,
        )

        sell_orders = [item for item in report["orders"] if item["side"] == "SELL"]
        blocked_exits = [
            item for item in report["execution_events"]
            if item["side"] == "SELL" and item["status"] == "BLOCKED_NO_LIQUIDITY"
        ]

        self.assertTrue(report["ok"])
        self.assertEqual(sell_orders, [])
        self.assertTrue(blocked_exits)
        self.assertGreater(report["liquidity_block_count"], 0)
        self.assertTrue(report["pending_forced_exit_symbols"])

    def test_cluster_limit_prevents_duplicate_theme_exposure(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            clusters={"AAA": "CHIPS", "BBB": "CHIPS", "CCC": "SOFTWARE"},
            top_n=2,
            max_per_cluster=1,
            lookback=60,
        )

        first = first_planned_rebalance(report)
        self.assertEqual(first["target_symbols"], ["AAA", "CCC"])

    def test_down_market_regime_keeps_the_portfolio_in_cash(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(benchmark_drift=-0.003),
            benchmark_symbol="SPY",
            top_n=2,
            lookback=60,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["order_event_count"], 0)
        self.assertEqual(report["final_equity"], report["initial_cash"])

    def test_prefix_results_are_invariant_to_future_rows(self) -> None:
        audit = audit_relative_strength_causality(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            top_n=2,
            lookback=60,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["input_unchanged"])
        self.assertTrue(all(item["passed"] for item in audit["checkpoints"]))

    def test_causal_audit_uses_common_dates_for_staggered_symbol_histories(self) -> None:
        payloads = make_payloads(240)
        for symbol in ("AAA", "BBB", "CCC"):
            payloads[symbol]["rows"] = list(payloads[symbol]["rows"])[20:]

        audit = audit_relative_strength_causality(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=2,
            lookback=60,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(item["cutoff"] for item in audit["checkpoints"]))
        self.assertTrue(all(item["passed"] for item in audit["checkpoints"]))

    def test_drawdown_guard_moves_the_portfolio_to_cash_on_the_next_open(self) -> None:
        payloads = make_payloads()
        for row in payloads["AAA"]["rows"][160:]:
            for key in ("open", "high", "low", "close"):
                row[key] = float(row[key]) * 0.70
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            max_position_weight_pct=100,
            drawdown_guard_pct=12,
            drawdown_cooldown_bars=20,
        )

        self.assertGreaterEqual(report["risk_off_event_count"], 1)
        guard = next(item for item in report["decisions"] if item["reason"] == "portfolio_drawdown_guard")
        exit_order = next(item for item in report["orders"] if item["reason"] == "portfolio_drawdown_guard")
        self.assertNotEqual(guard["signal_date"], exit_order["date"])
        self.assertEqual(exit_order["side"], "SELL")

    def test_suspension_blocks_exit_and_retries_after_trading_resumes(self) -> None:
        payloads = make_payloads()
        suspended = dict(payloads["AAA"]["rows"][161])
        suspended_date = str(suspended["date"])
        payloads["AAA"]["rows"].pop(161)
        payloads["AAA"]["trading_status_events"] = [{
            "status": "SUSPENDED",
            "start_date": suspended_date,
            "end_date": suspended_date,
            "provider": "test",
        }]
        for row in payloads["AAA"]["rows"]:
            if str(row["date"]) >= str(payloads["SPY"]["rows"][160]["date"]):
                for key in ("open", "high", "low", "close"):
                    row[key] = float(row[key]) * 0.70

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
            max_position_weight_pct=100,
            drawdown_guard_pct=12,
            drawdown_cooldown_bars=20,
        )

        blocked = next(item for item in report["execution_events"] if item["status"] == "BLOCKED_NON_TRADABLE")
        resumed_exit = next(
            item for item in report["orders"]
            if item["side"] == "SELL" and item["date"] > suspended_date
        )
        self.assertEqual(blocked["date"], suspended_date)
        self.assertEqual(blocked["trading_status"], "SUSPENDED")
        self.assertEqual(resumed_exit["reason"], "drawdown_cooldown_liquidation")
        self.assertGreater(report["tradability_block_count"], 0)
        self.assertEqual(report["pending_forced_exit_symbols"], [])

    def test_delisting_cash_settlement_liquidates_a_held_position(self) -> None:
        payloads = make_payloads()
        delisting_date = str(payloads["AAA"]["rows"][150]["date"])
        payloads["AAA"]["rows"] = payloads["AAA"]["rows"][:150]
        payloads["AAA"]["trading_status_events"] = [{
            "status": "DELISTED",
            "start_date": delisting_date,
            "cash_settlement_price": 77.0,
            "provider": "test",
        }]

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )

        settlement = next(
            item for item in report["corporate_action_events"]
            if item["action_type"] == "DELISTING_CASH_SETTLEMENT"
        )
        self.assertEqual(settlement["date"], delisting_date)
        self.assertEqual(settlement["settlement_price"], 77.0)
        self.assertNotIn("AAA", report["final_positions"])

    def test_embedded_qfq_dividend_is_not_credited_twice(self) -> None:
        payloads = make_payloads()
        payloads["AAA"]["adjustment_basis"] = "FORWARD_ADJUSTED_QFQ"
        payloads["AAA"]["corporate_actions"] = [{
            "action_type": "DIVIDEND",
            "event_date": payloads["AAA"]["rows"][140]["date"],
            "pay_date": payloads["AAA"]["rows"][145]["date"],
            "cash_amount": 1.0,
        }]

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["total_dividends"], 0.0)
        self.assertEqual(report["corporate_action_event_count"], 0)

    def test_split_adjusted_dividend_accrues_then_settles_on_pay_date(self) -> None:
        payloads = make_payloads()
        ex_date = str(payloads["AAA"]["rows"][140]["date"])
        pay_date = str(payloads["AAA"]["rows"][145]["date"])
        payloads["AAA"].update({
            "adjustment_basis": "SPLIT_ADJUSTED",
            "corporate_action_coverage": "COMPLETE",
            "corporate_actions": [{
                "action_type": "DIVIDEND",
                "event_date": ex_date,
                "pay_date": pay_date,
                "cash_amount": 1.0,
            }],
        })

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )

        action_types = [item["action_type"] for item in report["corporate_action_events"]]
        self.assertTrue(report["ok"])
        self.assertGreater(report["total_dividends"], 0.0)
        self.assertEqual(report["total_dividends"], report["dividend_cash_paid"])
        self.assertEqual(report["dividend_receivable"], 0.0)
        self.assertEqual(action_types, ["DIVIDEND_RECEIVABLE_ACCRUED", "DIVIDEND_CASH_SETTLED"])
        self.assertEqual(report["corporate_action_events"][1]["date"], pay_date)

    def test_raw_split_adjusts_held_quantity_before_the_session_open(self) -> None:
        payloads = make_payloads()
        split_index = 140
        split_date = str(payloads["AAA"]["rows"][split_index]["date"])
        for row in payloads["AAA"]["rows"][split_index:]:
            for key in ("open", "high", "low", "close"):
                row[key] = float(row[key]) / 2.0
        payloads["AAA"].update({
            "adjustment_basis": "RAW_UNADJUSTED",
            "corporate_action_coverage": "COMPLETE",
            "corporate_actions": [{
                "action_type": "SPLIT",
                "event_date": split_date,
                "ratio": 2.0,
            }],
        })

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=1,
            lookback=60,
        )

        split = next(
            item for item in report["corporate_action_events"]
            if item["action_type"] == "SPLIT_QUANTITY_ADJUSTMENT"
        )
        self.assertTrue(report["ok"])
        self.assertEqual(split["date"], split_date)
        self.assertAlmostEqual(split["quantity_after"], split["quantity_before"] * 2.0, places=8)

    def test_split_adjusts_a_pending_partial_exit_target_before_open(self) -> None:
        payloads = make_payloads(260)
        split_date = "2024-07-03"
        split_index = next(
            index for index, row in enumerate(payloads["AAA"]["rows"])
            if row["date"] == split_date
        )
        for row in payloads["AAA"]["rows"][split_index:]:
            for key in ("open", "high", "low", "close"):
                row[key] = float(row[key]) / 2.0
        payloads["AAA"].update({
            "adjustment_basis": "RAW_UNADJUSTED",
            "corporate_action_coverage": "COMPLETE",
            "corporate_actions": [{
                "action_type": "SPLIT",
                "event_date": split_date,
                "ratio": 2.0,
            }],
        })

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=2,
            lookback=60,
            minimum_trade_pct=0,
            initial_cash=1_000_000,
            minimum_median_dollar_volume=0,
            max_entry_participation_pct=25,
            max_exit_participation_pct=0.001,
        )

        split = next(
            item for item in report["corporate_action_events"]
            if item["action_type"] == "SPLIT_QUANTITY_ADJUSTMENT"
        )
        retry = next(
            item for item in report["decisions"]
            if item["signal_date"] == "2024-07-02" and item["reason"] == "retry_blocked_exit"
        )
        split_day_sell = next(
            item for item in report["orders"]
            if item["symbol"] == "AAA" and item["side"] == "SELL" and item["date"] == split_date
        )
        adjusted_target = float(retry["target_quantities_override"]["AAA"]) * 2.0
        expected_sell = float(split["quantity_after"]) - adjusted_target

        self.assertTrue(report["ok"])
        self.assertGreater(expected_sell, 0.0)
        self.assertAlmostEqual(split_day_sell["requested_quantity"], expected_sell, places=6)
        self.assertFalse(any(
            item["signal_date"] == split_date and item["reason"] == "retry_blocked_exit"
            for item in report["decisions"]
        ))

    def test_run_hash_includes_initial_capital(self) -> None:
        small = run_causal_relative_strength_backtest(
            payloads=make_payloads(), benchmark_symbol="SPY", lookback=60, initial_cash=100_000
        )
        large = run_causal_relative_strength_backtest(
            payloads=make_payloads(), benchmark_symbol="SPY", lookback=60, initial_cash=1_000_000
        )

        self.assertTrue(small["ok"] and large["ok"])
        self.assertNotEqual(small["run_hash"], large["run_hash"])

    def test_invalid_numeric_contract_fails_closed_without_throwing(self) -> None:
        invalid_settings = (
            {"initial_cash": float("nan")},
            {"initial_cash": float("inf")},
            {"initial_cash": 0.0},
            {"initial_cash": -100.0},
            {"fee_rate": float("nan")},
            {"slippage_bps": float("inf")},
            {"fee_rate": -0.001},
            {"gross_target_pct": 101.0},
            {"top_n": 0},
            {"skip_recent": 41, "lookback": 60},
        )
        for settings in invalid_settings:
            with self.subTest(settings=settings):
                parameters = {"lookback": 60, **settings}
                report = run_causal_relative_strength_backtest(
                    payloads=make_payloads(),
                    benchmark_symbol="SPY",
                    **parameters,
                )

                self.assertFalse(report["ok"])
                self.assertIn("numeric parameter contract", report["error"])
                self.assertFalse(report["paper_authorized"])
                self.assertFalse(report["live_order_allowed"])

    def test_inverse_volatility_budget_reduces_the_noisiest_position_weight(self) -> None:
        payloads = {
            "SPY": {"source": "test", "rows": make_rows(220, 0.002)},
            "AAA": {"source": "test", "rows": make_rows(220, 0.004, wave=0.02)},
            "BBB": {"source": "test", "rows": make_rows(220, 0.003, wave=0.001)},
            "CCC": {"source": "test", "rows": make_rows(220, 0.002, wave=0.004)},
        }
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=3,
            lookback=60,
            volatility_window=63,
            target_portfolio_volatility_pct=15,
            max_position_weight_pct=50,
        )

        weights = first_planned_rebalance(report)["target_weights"]
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertLess(weights["AAA"], weights["BBB"])

    def test_single_eligible_signal_leaves_cash_instead_of_breaking_position_cap(self) -> None:
        payloads = {
            "SPY": {"source": "test", "rows": make_rows(220, 0.002)},
            "AAA": {"source": "test", "rows": make_rows(220, 0.004)},
            "BBB": {"source": "test", "rows": make_rows(220, -0.001)},
            "CCC": {"source": "test", "rows": make_rows(220, -0.002)},
        }
        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            top_n=3,
            lookback=60,
            max_position_weight_pct=50,
        )

        decision = first_planned_rebalance(report)
        self.assertEqual(decision["target_symbols"], ["AAA"])
        self.assertEqual(decision["target_weights"], {"AAA": 0.5})
        self.assertEqual(decision["unallocated_target_weight_pct"], 50.0)
        self.assertLessEqual(max(decision["target_weights"].values()), 0.5)

    def test_zero_position_weight_limit_fails_closed(self) -> None:
        report = run_causal_relative_strength_backtest(
            payloads=make_payloads(),
            benchmark_symbol="SPY",
            lookback=60,
            max_position_weight_pct=0,
        )

        self.assertFalse(report["ok"])
        self.assertIn("max_position_weight_pct:must_be_positive", report["error"])
        self.assertFalse(report["paper_authorized"])
        self.assertFalse(report["live_order_allowed"])

    def test_weekly_rebalance_dates_do_not_shift_with_history_depth(self) -> None:
        full_payloads = make_payloads(260)
        truncated_payloads = {
            symbol: {**payload, "rows": list(payload["rows"])[13:]}
            for symbol, payload in full_payloads.items()
        }
        full = run_causal_relative_strength_backtest(payloads=full_payloads, benchmark_symbol="SPY", lookback=60)
        truncated = run_causal_relative_strength_backtest(payloads=truncated_payloads, benchmark_symbol="SPY", lookback=60)
        overlap_start = truncated["evaluation_window"]["start"]
        full_dates = {
            item["signal_date"] for item in full["decisions"]
            if item.get("reason") == "relative_strength_rebalance" and item["signal_date"] > overlap_start
        }
        truncated_dates = {
            item["signal_date"] for item in truncated["decisions"]
            if item.get("reason") == "relative_strength_rebalance" and item["signal_date"] > overlap_start
        }

        self.assertEqual(full_dates, truncated_dates)
        self.assertTrue(all(date.fromisoformat(item).weekday() == 0 for item in full_dates))

    def test_evaluation_window_waits_for_the_next_scheduled_rebalance(self) -> None:
        payloads = make_payloads(240)
        prepared = prepare_portfolio_dataset(payloads, benchmark_symbol="SPY", minimum_rows=140)
        evaluation_start = next(
            index
            for index, session_date in enumerate(prepared["dates"])
            if index >= 150 and date.fromisoformat(session_date).weekday() == 4
        )

        report = run_causal_relative_strength_backtest(
            payloads=payloads,
            benchmark_symbol="SPY",
            lookback=60,
            evaluation_start_index=evaluation_start,
        )

        first = first_planned_rebalance(report)
        self.assertGreaterEqual(first["signal_date"], prepared["dates"][evaluation_start])
        self.assertEqual(date.fromisoformat(first["signal_date"]).weekday(), 0)
        self.assertTrue(all(order["signal_date"] >= first["signal_date"] for order in report["orders"]))
        self.assertEqual(report["schedule_contract"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
