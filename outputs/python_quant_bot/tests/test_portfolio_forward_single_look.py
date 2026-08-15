from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import inspect
import unittest
from unittest.mock import patch

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.portfolio_forward_performance import (
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
    build_forward_performance_readiness,
    build_forward_performance_settlement,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
    audit_forward_portfolio_statistics,
    audit_forward_portfolio_statistics_v2,
    verify_forward_portfolio_statistical_audit_semantics,
    verify_forward_portfolio_statistical_audit_v2_semantics,
)
import run_portfolio_forward_performance as performance_runner
from tests.test_portfolio_forward_statistical_audit import (
    frozen_candidate,
    performance_summary_from,
    synthetic_settlement_chain,
    verified_historical_audit,
)
from tests.test_portfolio_forward_performance import canonical_hash
from tests.test_portfolio_forward_performance import (
    candidate as settlement_candidate,
    settlement_inputs,
)


MAX_SAFE_INTEGER = 9_007_199_254_740_991


def synthetic_stage_result(*, status_for_count):
    def build(**kwargs):
        observation_count = len(dict(kwargs["strategy_report"])["equity_curve"])
        status = str(status_for_count(observation_count))
        content = {
            "stage": str(kwargs["stage"]),
            "status": status,
            "blockers": [] if status == "PASS" else ["synthetic_statistical_threshold"],
            "observation_count": observation_count,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        return {**content, "stage_hash": canonical_hash(content)}

    return build


def settlement_chain_with_price_overrides(
    outcomes: int,
    *,
    prices_by_day: dict[int, dict[str, float]],
) -> list[dict[str, object]]:
    settlements: list[dict[str, object]] = []
    previous: dict[str, object] | None = None
    previous_observation: dict[str, object] | None = None
    previous_date = ""
    for day in range(outcomes + 1):
        settlement_date = (date(2026, 8, 3) + timedelta(days=day)).isoformat()
        observation, manifest, market_rows = settlement_inputs(
            settlement_date,
            day=day,
            execute=True,
        )
        for symbol, price in prices_by_day.get(day, {}).items():
            market_rows[symbol].update({
                "open": price,
                "high": price * 1.005,
                "low": price * 0.995,
                "close": price,
                "volume": 1_000_000.0,
            })
        settlement = build_forward_performance_settlement(
            candidate=settlement_candidate(),
            current_observation=observation,
            dataset_manifest=manifest,
            market_rows=market_rows,
            recorded_at=200 + day,
            previous_settlement=previous,
            previous_observation=previous_observation,
            previous_session_date=previous_date,
        )
        if settlement.get("status") != "READY":
            raise AssertionError(f"synthetic settlement blocked: {settlement.get('blockers')}")
        settlements.append(settlement)
        previous = settlement
        previous_observation = observation
        previous_date = settlement_date
    return settlements


def verified_v2_audit(frozen, settlements, historical, *, generated_at: int = 100):
    report = audit_forward_portfolio_statistics_v2(
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
        generated_at=generated_at,
    )
    verification = verify_forward_portfolio_statistical_audit_v2_semantics(
        report,
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
    )
    return {
        **report,
        "verification_status": verification["status"],
        "verification_blockers": list(verification["blockers"]),
        "semantic_recomputed": verification["recomputed_from_verified_forward_settlements"],
    }


def verified_v1_audit(frozen, settlements, historical):
    report = audit_forward_portfolio_statistics(
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
        generated_at=100,
    )
    verification = verify_forward_portfolio_statistical_audit_semantics(
        report,
        candidate=frozen,
        settlements=settlements,
        historical_statistical_audit=historical,
    )
    return {
        **report,
        "verification_status": verification["status"],
        "verification_blockers": list(verification["blockers"]),
        "semantic_recomputed": verification["recomputed_from_verified_forward_settlements"],
    }


class PortfolioForwardSingleLookTests(unittest.TestCase):
    def test_first_block_at_60_stays_blocked_when_full_series_would_pass_at_66(self) -> None:
        frozen = frozen_candidate(outcomes=60, rebalances=60)
        historical = verified_historical_audit(frozen)
        settlements_60 = synthetic_settlement_chain(60)
        settlements_66 = synthetic_settlement_chain(66)
        stage = synthetic_stage_result(
            status_for_count=lambda count: "BLOCK" if count == 60 else "PASS"
        )

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=stage,
        ):
            first = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements_60,
                historical_statistical_audit=historical,
                generated_at=100,
            )
            appended = verified_v2_audit(
                frozen,
                settlements_66,
                historical,
                generated_at=200,
            )
            full_series_v1 = audit_forward_portfolio_statistics(
                candidate=frozen,
                settlements=settlements_66,
                historical_statistical_audit=historical,
                generated_at=100,
            )

        self.assertEqual(first["status"], "BLOCK")
        self.assertEqual(appended["status"], "BLOCK")
        self.assertEqual(appended["verification_status"], "PASS")
        self.assertEqual(appended["stage"]["observation_count"], 60)
        self.assertEqual(appended["decision_window"]["research_action"], "STOP_RESEARCH")
        self.assertEqual(full_series_v1["status"], "PASS")
        self.assertEqual(full_series_v1["stage"]["observation_count"], 66)
        self.assertEqual(
            first["decision_window"]["decision_hash"],
            appended["decision_window"]["decision_hash"],
        )
        self.assertNotEqual(
            first["input_binding"]["forward_series_hash"],
            appended["input_binding"]["forward_series_hash"],
        )
        tampered = deepcopy(first)
        tampered["decision_window"]["risk_acceptance"][
            "required_max_drawdown_below_pct"
        ] = 99.0
        tamper_verification = verify_forward_portfolio_statistical_audit_v2_semantics(
            tampered,
            candidate=frozen,
            settlements=settlements_60,
            historical_statistical_audit=historical,
        )
        self.assertEqual(tamper_verification["status"], "BLOCK")
        self.assertIn(
            "forward_statistical_decision_hash_invalid",
            tamper_verification["blockers"],
        )

        readiness = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements_66)},
            performance_summary=performance_summary_from(settlements_66),
            historical_statistical_audit=historical,
            forward_statistical_audit=appended,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertEqual(readiness["research_action"], "STOP_RESEARCH")
        self.assertTrue(readiness["integrity_checks"]["forward_statistical_audit_v2_integrity_pass"])

    def test_first_pass_at_60_stays_passed_when_full_series_would_block_later(self) -> None:
        frozen = frozen_candidate(outcomes=60, rebalances=60)
        historical = verified_historical_audit(frozen)
        settlements_60 = synthetic_settlement_chain(60)
        settlements_66 = synthetic_settlement_chain(66)
        stage = synthetic_stage_result(
            status_for_count=lambda count: "PASS" if count == 60 else "BLOCK"
        )

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=stage,
        ):
            first = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements_60,
                historical_statistical_audit=historical,
                generated_at=100,
            )
            appended = verified_v2_audit(
                frozen,
                settlements_66,
                historical,
                generated_at=200,
            )
            full_series_v1 = audit_forward_portfolio_statistics(
                candidate=frozen,
                settlements=settlements_66,
                historical_statistical_audit=historical,
                generated_at=100,
            )

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(appended["status"], "PASS")
        self.assertEqual(appended["stage"]["observation_count"], 60)
        self.assertEqual(appended["decision_window"]["research_action"], "REVIEW_REQUIRED")
        self.assertEqual(full_series_v1["status"], "BLOCK")
        self.assertEqual(full_series_v1["stage"]["observation_count"], 66)
        self.assertEqual(
            first["decision_window"]["decision_hash"],
            appended["decision_window"]["decision_hash"],
        )

        readiness = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements_66)},
            performance_summary=performance_summary_from(settlements_66),
            historical_statistical_audit=historical,
            forward_statistical_audit=appended,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_READY")
        self.assertEqual(readiness["promotion_status"], "REVIEW_REQUIRED")

    def test_joint_maturity_waits_until_outcome_75_for_eighth_rebalance(self) -> None:
        frozen = frozen_candidate(outcomes=60, rebalances=8)
        historical = verified_historical_audit(frozen)
        execute_signal_days = {0, 1, 2, 3, 4, 5, 6, 74}
        settlements_74 = synthetic_settlement_chain(
            74,
            execute_signal_days=execute_signal_days,
        )
        settlements_75 = synthetic_settlement_chain(
            75,
            execute_signal_days=execute_signal_days,
        )

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            before = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements_74,
                historical_statistical_audit=historical,
                generated_at=100,
            )
            due = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements_75,
                historical_statistical_audit=historical,
                generated_at=100,
            )

        self.assertEqual(before["maturity"]["forward_outcomes"], 74)
        self.assertEqual(before["maturity"]["executed_rebalances"], 7)
        self.assertEqual(before["status"], "NOT_DUE")
        prefix = due["decision_window"]["first_joint_maturity_prefix"]
        self.assertEqual(due["status"], "PASS")
        self.assertEqual(prefix["first_due_settlement_index"], 75)
        self.assertEqual(prefix["outcome_period_count"], 75)
        self.assertEqual(prefix["rebalance_execution_count"], 8)
        self.assertEqual(due["stage"]["observation_count"], 75)

    def test_joint_maturity_exact_60_outcome_8_rebalance_boundaries(self) -> None:
        frozen = frozen_candidate(outcomes=60, rebalances=8)
        historical = verified_historical_audit(frozen)
        cases = (
            (59, set(range(8)), "NOT_DUE", 8, None),
            (60, set(range(7)), "NOT_DUE", 7, None),
            (60, set(range(8)), "PASS", 8, 60),
        )
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            for outcomes, signal_days, status, rebalances, first_due_index in cases:
                report = audit_forward_portfolio_statistics_v2(
                    candidate=frozen,
                    settlements=synthetic_settlement_chain(
                        outcomes,
                        execute_signal_days=signal_days,
                    ),
                    historical_statistical_audit=historical,
                    generated_at=100,
                )
                self.assertEqual(report["status"], status)
                self.assertEqual(report["maturity"]["forward_outcomes"], outcomes)
                self.assertEqual(report["maturity"]["executed_rebalances"], rebalances)
                self.assertEqual(
                    report["decision_window"]["first_joint_maturity_prefix"][
                        "first_due_settlement_index"
                    ],
                    first_due_index,
                )

    def test_bad_chain_and_nested_authority_are_integrity_blocks(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=5)
        historical = verified_historical_audit(frozen)
        settlements = synthetic_settlement_chain(5)
        broken = deepcopy(settlements)
        broken[3]["previous_settlement_hash"] = "f" * 64

        chain_report = audit_forward_portfolio_statistics_v2(
            candidate=frozen,
            settlements=broken,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        chain_verification = verify_forward_portfolio_statistical_audit_v2_semantics(
            chain_report,
            candidate=frozen,
            settlements=broken,
            historical_statistical_audit=historical,
        )
        self.assertEqual(chain_report["status"], "BLOCK")
        self.assertFalse(chain_report["checks"]["settlement_series_integrity_pass"])
        self.assertEqual(chain_verification["status"], "PASS")

        authority_candidate = deepcopy(frozen)
        authority_candidate["nested_governance"] = {"canTrade": True}
        authority_report = audit_forward_portfolio_statistics_v2(
            candidate=authority_candidate,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        self.assertEqual(authority_report["status"], "BLOCK")
        self.assertFalse(authority_report["checks"]["zero_execution_authority"])
        self.assertTrue(any(
            "$.candidate.nested_governance.canTrade" in item
            for item in authority_report["blockers"]
        ))
        self.assertFalse(authority_report["paper_authorized"])
        self.assertFalse(authority_report["live_order_allowed"])

    def test_pre_due_collects_and_decision_hash_tamper_fails_closed(self) -> None:
        collecting_candidate = frozen_candidate(outcomes=6, rebalances=6)
        collecting_historical = verified_historical_audit(collecting_candidate)
        collecting_settlements = synthetic_settlement_chain(5)
        collecting_audit = verified_v2_audit(
            collecting_candidate,
            collecting_settlements,
            collecting_historical,
        )
        collecting = build_forward_performance_readiness(
            candidate=collecting_candidate,
            shadow_audit={
                "status": "PASS",
                "valid_observation_count": len(collecting_settlements),
            },
            performance_summary=performance_summary_from(collecting_settlements),
            historical_statistical_audit=collecting_historical,
            forward_statistical_audit=collecting_audit,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(collecting_audit["status"], "NOT_DUE")
        self.assertEqual(collecting["status"], "COLLECTING")
        self.assertEqual(collecting["blockers"], [])

        due_candidate = frozen_candidate(outcomes=5, rebalances=5)
        due_historical = verified_historical_audit(due_candidate)
        due_settlements = synthetic_settlement_chain(5)
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            due_audit = verified_v2_audit(due_candidate, due_settlements, due_historical)
        tampered = deepcopy(due_audit)
        tampered["decision_window"]["research_action"] = "STOP_RESEARCH"
        tamper_verification = verify_forward_portfolio_statistical_audit_v2_semantics(
            tampered,
            candidate=due_candidate,
            settlements=due_settlements,
            historical_statistical_audit=due_historical,
        )
        tampered_readiness = build_forward_performance_readiness(
            candidate=due_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": len(due_settlements)},
            performance_summary=performance_summary_from(due_settlements),
            historical_statistical_audit=due_historical,
            forward_statistical_audit=tampered,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(tamper_verification["status"], "BLOCK")
        self.assertIn("forward_statistical_decision_hash_invalid", tamper_verification["blockers"])
        self.assertEqual(tampered_readiness["status"], "BLOCK")
        self.assertFalse(
            tampered_readiness["integrity_checks"]["first_joint_maturity_decision_hash_pass"]
        )

    def test_v2_cycles_fail_closed_without_changing_legacy_paths(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=5)
        historical = verified_historical_audit(frozen)
        settlements = synthetic_settlement_chain(5)
        frozen["nested"] = frozen

        preview = performance_runner.build_first_joint_maturity_statistical_status_preview(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=performance_summary_from(settlements),
            generated_at=100,
        )
        self.assertEqual(preview["forward_statistical_audit"]["status"], "BLOCK")
        self.assertEqual(preview["readiness"]["status"], "BLOCK")
        self.assertTrue(any(
            "input_cycle_invalid" in item
            for item in preview["forward_statistical_audit"]["blockers"]
        ))

        cyclic_report = dict(preview["forward_statistical_audit"])
        cyclic_report["cycle"] = cyclic_report
        verification = verify_forward_portfolio_statistical_audit_v2_semantics(
            cyclic_report,
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("forward_statistical_audit_cycle_invalid", verification["blockers"])
        self.assertEqual(PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION, "portfolio-forward-statistical-audit-v1")
        self.assertEqual(PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION, "portfolio-forward-readiness-v2")

    def test_v2_v3_reject_unsafe_and_non_native_thresholds_counts_and_bindings(self) -> None:
        frozen = frozen_candidate(outcomes=6, rebalances=6)
        frozen["spec"]["minimum_forward_performance_outcomes"] = MAX_SAFE_INTEGER + 1
        frozen["spec_hash"] = canonical_hash(frozen["spec"])
        historical = verified_historical_audit(frozen)
        settlements = synthetic_settlement_chain(5)

        legacy = audit_forward_portfolio_statistics(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        strict = audit_forward_portfolio_statistics_v2(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        self.assertEqual(legacy["status"], "NOT_DUE")
        self.assertEqual(strict["status"], "BLOCK")
        self.assertTrue(any(
            "positive_safe_integer_required" in item for item in strict["blockers"]
        ))

        string_threshold = frozen_candidate(outcomes=6, rebalances=6)
        string_threshold["spec"]["minimum_forward_performance_outcomes"] = "6"
        string_threshold["spec_hash"] = canonical_hash(string_threshold["spec"])
        string_historical = verified_historical_audit(string_threshold)
        string_report = audit_forward_portfolio_statistics_v2(
            candidate=string_threshold,
            settlements=settlements,
            historical_statistical_audit=string_historical,
            generated_at=100,
        )
        self.assertEqual(string_report["status"], "BLOCK")

        due_candidate = frozen_candidate(outcomes=5, rebalances=5)
        due_historical = verified_historical_audit(due_candidate)
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            due_audit = verified_v2_audit(
                due_candidate,
                settlements,
                due_historical,
            )
        unsafe_binding = deepcopy(due_audit)
        unsafe_binding["input_binding"]["outcome_period_count"] = MAX_SAFE_INTEGER + 1
        unsafe_binding_readiness = build_forward_performance_readiness(
            candidate=due_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=performance_summary_from(settlements),
            historical_statistical_audit=due_historical,
            forward_statistical_audit=unsafe_binding,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(unsafe_binding_readiness["status"], "BLOCK")
        self.assertFalse(
            unsafe_binding_readiness["integrity_checks"][
                "forward_statistical_audit_v2_binding_pass"
            ]
        )

        unsafe_summary = performance_summary_from(settlements)
        unsafe_summary["outcome_period_count"] = MAX_SAFE_INTEGER + 1
        unsafe_progress_readiness = build_forward_performance_readiness(
            candidate=due_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=unsafe_summary,
            historical_statistical_audit=due_historical,
            forward_statistical_audit=due_audit,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(unsafe_progress_readiness["status"], "BLOCK")
        self.assertFalse(
            unsafe_progress_readiness["integrity_checks"]["forward_progress_safe_integers"]
        )
        self.assertEqual(unsafe_progress_readiness["progress"]["forward_outcomes"], 0)

    def test_v2_rejects_unsafe_historical_counts_and_nonfinite_risk_limit(self) -> None:
        frozen = frozen_candidate(outcomes=6, rebalances=6)
        settlements = synthetic_settlement_chain(5)
        historical = verified_historical_audit(frozen)
        historical["config"]["resample_count"] = MAX_SAFE_INTEGER + 1

        legacy = audit_forward_portfolio_statistics(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        strict = audit_forward_portfolio_statistics_v2(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )
        self.assertEqual(legacy["status"], "NOT_DUE")
        self.assertEqual(strict["status"], "BLOCK")
        self.assertIn(
            "historical_statistical_config_unsafe_integer:resample_count",
            strict["blockers"],
        )

        nonfinite = frozen_candidate(outcomes=5, rebalances=5)
        nonfinite["spec"]["acceptance_contract"][
            "validation_and_test_max_drawdown_below_pct"
        ] = float("nan")
        nonfinite["spec_hash"] = canonical_hash(nonfinite["spec"])
        nonfinite_historical = verified_historical_audit(nonfinite)
        report = audit_forward_portfolio_statistics_v2(
            candidate=nonfinite,
            settlements=settlements,
            historical_statistical_audit=nonfinite_historical,
            generated_at=100,
        )
        self.assertEqual(report["status"], "BLOCK")
        self.assertTrue(any(
            "risk_acceptance_drawdown_limit_invalid" in item
            for item in report["blockers"]
        ))

    def test_v2_compute_budget_blocks_before_statistical_stage(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=5)
        settlements = synthetic_settlement_chain(5)
        historical = verified_historical_audit(frozen)
        historical["config"]["resample_count"] = 1_000_000_000

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=AssertionError("statistical stage must not start"),
        ) as stage_builder:
            first = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=historical,
                generated_at=100,
            )
            repeated = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=historical,
                generated_at=200,
            )

        stage_builder.assert_not_called()
        self.assertEqual(first["status"], "BLOCK")
        self.assertEqual(first["audit_hash"], repeated["audit_hash"])
        self.assertIn(
            "historical_statistical_compute_budget:"
            "bootstrap_resample_count_exceeds_budget:1000000000>50000",
            first["blockers"],
        )

        block_historical = verified_historical_audit(frozen)
        block_historical["config"]["block_length"] = 1_000_000_000
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=AssertionError("statistical stage must not start"),
        ) as block_stage_builder:
            block_report = audit_forward_portfolio_statistics_v2(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=block_historical,
                generated_at=100,
            )
        block_stage_builder.assert_not_called()
        self.assertEqual(block_report["status"], "BLOCK")
        self.assertIn(
            "historical_statistical_compute_budget:"
            "bootstrap_block_length_exceeds_budget:1000000000>1024",
            block_report["blockers"],
        )

    def test_prefix_drawdown_blocks_and_tail_recovery_cannot_change_decision(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=5)
        historical = verified_historical_audit(frozen)
        decline_prices = {
            day: {
                "AAPL": 202.0 * (0.92 ** (day - 1)),
                "NVDA": 101.0 * (0.92 ** (day - 1)),
            }
            for day in range(2, 6)
        }
        prefix_settlements = settlement_chain_with_price_overrides(
            5,
            prices_by_day=decline_prices,
        )
        recovery_prices = dict(decline_prices)
        last_aapl = decline_prices[5]["AAPL"]
        last_nvda = decline_prices[5]["NVDA"]
        for day in range(6, 9):
            last_aapl *= 1.08
            last_nvda *= 1.08
            recovery_prices[day] = {"AAPL": last_aapl, "NVDA": last_nvda}
        appended_settlements = settlement_chain_with_price_overrides(
            8,
            prices_by_day=recovery_prices,
        )

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            first = verified_v2_audit(frozen, prefix_settlements, historical)
            appended = verified_v2_audit(frozen, appended_settlements, historical)

        risk = first["decision_window"]["risk_acceptance"]
        self.assertEqual(first["stage"]["status"], "PASS")
        self.assertEqual(risk["status"], "BLOCK")
        self.assertGreaterEqual(risk["prefix_max_drawdown_pct"], 15.0)
        self.assertEqual(first["decision_window"]["decision_status"], "BLOCK")
        self.assertEqual(first["decision_window"]["research_action"], "STOP_RESEARCH")
        self.assertEqual(first["status"], "BLOCK")
        self.assertEqual(first["verification_status"], "PASS")
        self.assertEqual(
            first["decision_window"]["decision_hash"],
            appended["decision_window"]["decision_hash"],
        )
        self.assertEqual(risk["risk_hash"], appended["decision_window"]["risk_acceptance"]["risk_hash"])

        exact_limit_candidate = deepcopy(frozen)
        exact_limit_candidate["spec"]["acceptance_contract"][
            "validation_and_test_max_drawdown_below_pct"
        ] = risk["prefix_max_drawdown_pct"]
        exact_limit_candidate["spec_hash"] = canonical_hash(exact_limit_candidate["spec"])
        exact_limit_historical = verified_historical_audit(exact_limit_candidate)
        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            exact_limit = audit_forward_portfolio_statistics_v2(
                candidate=exact_limit_candidate,
                settlements=prefix_settlements,
                historical_statistical_audit=exact_limit_historical,
                generated_at=100,
            )
        self.assertEqual(exact_limit["status"], "BLOCK")
        self.assertIn(
            "risk_acceptance_max_drawdown_not_below_limit",
            exact_limit["decision_window"]["risk_acceptance"]["blockers"],
        )

        readiness = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(appended_settlements)},
            performance_summary=performance_summary_from(appended_settlements),
            historical_statistical_audit=historical,
            forward_statistical_audit=appended,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertTrue(
            readiness["integrity_checks"]["forward_statistical_audit_v2_integrity_pass"]
        )

    def test_prefix_risk_pass_is_frozen_when_later_tail_drawdown_worsens(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=5)
        historical = verified_historical_audit(frozen)
        prefix_settlements = synthetic_settlement_chain(5)
        tail_prices: dict[int, dict[str, float]] = {}
        aapl = 222.0
        nvda = 116.0
        for day in range(6, 9):
            aapl *= 0.92
            nvda *= 0.92
            tail_prices[day] = {"AAPL": aapl, "NVDA": nvda}
        appended_settlements = settlement_chain_with_price_overrides(
            8,
            prices_by_day=tail_prices,
        )

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            first = verified_v2_audit(frozen, prefix_settlements, historical)
            appended = verified_v2_audit(frozen, appended_settlements, historical)

        self.assertEqual(first["status"], "PASS")
        self.assertEqual(appended["status"], "PASS")
        self.assertEqual(first["decision_window"]["risk_acceptance"]["status"], "PASS")
        self.assertEqual(
            first["decision_window"]["decision_hash"],
            appended["decision_window"]["decision_hash"],
        )
        self.assertNotEqual(
            first["input_binding"]["forward_series_hash"],
            appended["input_binding"]["forward_series_hash"],
        )

    def test_version_crosses_fail_closed_and_preview_is_explicit(self) -> None:
        frozen = frozen_candidate(outcomes=10, rebalances=10)
        historical = verified_historical_audit(frozen)
        settlements = synthetic_settlement_chain(10)
        summary = performance_summary_from(settlements)
        shadow = {"status": "PASS", "valid_observation_count": len(settlements)}

        with patch(
            "exchange_terminal.services.portfolio_forward_statistical_audit."
            "audit_paired_equity_curve_stage",
            side_effect=synthetic_stage_result(status_for_count=lambda _count: "PASS"),
        ):
            audit_v1 = verified_v1_audit(frozen, settlements, historical)
            audit_v2 = verified_v2_audit(frozen, settlements, historical)
            preview = performance_runner.build_first_joint_maturity_statistical_status_preview(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=historical,
                shadow_audit=shadow,
                performance_summary=summary,
                generated_at=100,
            )
            legacy = performance_runner.build_legacy_full_series_statistical_status(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=historical,
                shadow_audit=shadow,
                performance_summary=summary,
                generated_at=100,
            )

        v1_into_v3 = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit=shadow,
            performance_summary=summary,
            historical_statistical_audit=historical,
            forward_statistical_audit=audit_v1,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        v2_into_v2 = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit=shadow,
            performance_summary=summary,
            historical_statistical_audit=historical,
            forward_statistical_audit=audit_v2,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        self.assertEqual(v1_into_v3["status"], "BLOCK")
        self.assertIn("forward_statistical_audit_v2_integrity_pass", v1_into_v3["blockers"])
        self.assertEqual(v2_into_v2["status"], "BLOCK")
        self.assertIn("forward_statistical_audit_integrity_pass", v2_into_v2["blockers"])
        self.assertEqual(
            preview["audit_schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION,
        )
        self.assertEqual(
            preview["readiness_schema_version"],
            PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
        )
        self.assertEqual(preview["readiness"]["status"], "RESEARCH_REVIEW_READY")
        self.assertEqual(authority_violations(preview), [])
        self.assertEqual(
            legacy["audit_schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
        )
        self.assertEqual(
            legacy["readiness_schema_version"],
            PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        with self.assertRaisesRegex(ValueError, "unsupported_forward_statistical_version_pair"):
            performance_runner.build_forward_statistical_status(
                candidate=frozen,
                settlements=settlements,
                historical_statistical_audit=historical,
                shadow_audit=shadow,
                performance_summary=summary,
                generated_at=100,
                audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
                readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION,
            )

        main_source = inspect.getsource(performance_runner.main)
        self.assertIn(
            "audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_V2_SCHEMA_VERSION",
            main_source,
        )
        self.assertIn(
            "readiness_schema_version=PORTFOLIO_FORWARD_READINESS_V3_SCHEMA_VERSION",
            main_source,
        )
        self.assertNotIn(
            "audit_schema_version=PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION",
            main_source,
        )
        self.assertNotIn("build_first_joint_maturity_statistical_status_preview(", main_source)

    def test_current_v1_fixture_hashes_remain_exact(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=6)
        historical = verified_historical_audit(frozen, claim_status="BLOCK")
        report = audit_forward_portfolio_statistics(
            candidate=frozen,
            settlements=synthetic_settlement_chain(5),
            historical_statistical_audit=historical,
            generated_at=100,
        )

        self.assertEqual(PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION, "portfolio-forward-statistical-audit-v1")
        self.assertEqual(PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION, "portfolio-forward-readiness-v2")
        self.assertEqual(
            report["audit_hash"],
            "1c6758b7a9bd0e38abe12c021b27eb1f51ee4d56b3f14622a7d76bb9461e7783",
        )
        self.assertEqual(
            report["input_binding"]["binding_hash"],
            "60f7d016b7b0d8e598e6ac3dfb5d49e2b361a5a2d3aff87a4b7a58bca7b4a101",
        )
        self.assertEqual(
            report["series_evidence"]["series_hash"],
            "36926a74825c7db2eba7cdf8097affd47d1cb03a3ca8d80af896f9766242ce97",
        )
        self.assertEqual(
            report["statistical_contract"]["contract_hash"],
            "a23dc088155047d6d4c3666826bc6040eafb432414b9d86c8fe1d94dae94f53e",
        )


if __name__ == "__main__":
    unittest.main()
