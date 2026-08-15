from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import unittest

from exchange_terminal.services.portfolio_forward_performance import (
    LEGACY_PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
    build_forward_performance_readiness,
    build_forward_performance_settlement,
)
from exchange_terminal.services.portfolio_forward_statistical_audit import (
    PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION,
    audit_forward_portfolio_statistics,
    forward_statistical_audit_content,
    verify_forward_portfolio_statistical_audit_semantics,
)
from tests.test_portfolio_forward_performance import (
    candidate as settlement_candidate,
    canonical_hash,
    settlement_inputs,
)


def frozen_candidate(*, outcomes: int, rebalances: int, trials: int = 1) -> dict[str, object]:
    result = settlement_candidate(minimum_outcomes=outcomes)
    result["spec"]["minimum_forward_performance_outcomes"] = outcomes
    result["spec"]["minimum_planned_rebalances"] = rebalances
    result["spec"]["trial_count"] = trials
    result["development_trial_count"] = trials
    result["spec_hash"] = canonical_hash(result["spec"])
    return result


def verified_historical_audit(
    frozen: dict[str, object],
    *,
    claim_status: str = "BLOCK",
) -> dict[str, object]:
    config = {
        "method": "PAIRED_CIRCULAR_MOVING_BLOCK",
        "periods_per_year": 252,
        "resample_count": 200,
        "block_length": 5,
        "minimum_observations": 120,
        "confidence_level": 0.90,
        "required_positive_probability": 0.95,
        "required_selection_adjusted_probability": 0.90,
        "selection_adjustment": "BONFERRONI_ONE_SIDED",
        "selection_trial_count": int(frozen["spec"]["trial_count"]),
    }
    binding = {
        "batch_run_hash": "1" * 64,
        "candidate_hash": frozen["candidate_hash"],
        "dataset_hash": "2" * 64,
        "spec_hash": frozen["spec_hash"],
        "validation_run_hash": "3" * 64,
        "validation_benchmark_run_hash": "4" * 64,
        "test_run_hash": "5" * 64,
        "test_benchmark_run_hash": "6" * 64,
    }
    binding["binding_hash"] = canonical_hash(binding)
    return {
        "schema_version": "portfolio-statistical-audit-v3",
        "status": claim_status,
        "conclusion": (
            "STATISTICAL_PROMOTION_EVIDENCE_PASS"
            if claim_status == "PASS"
            else "INSUFFICIENT_STATISTICAL_PROMOTION_EVIDENCE"
        ),
        "audit_hash": "a" * 64,
        "artifact_hash": "b" * 64,
        "verification_status": "PASS",
        "verification_blockers": [],
        "semantic_recomputed": True,
        "config": config,
        "input_binding": binding,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def synthetic_settlement_chain(
    outcomes: int,
    *,
    weak_edge: bool = False,
    execute_signal_days: set[int] | None = None,
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
            execute=(True if execute_signal_days is None else day in execute_signal_days),
        )
        if weak_edge:
            weak_prices = {
                "SPY": (100.0 + day * 4.0, 101.0 + day * 4.0),
                "AAPL": (200.0 + day * 2.0, 201.0 + day * 2.0),
                "NVDA": (100.0 + day, 100.5 + day),
            }
            for symbol, (open_price, close_price) in weak_prices.items():
                market_rows[symbol].update({
                    "open": open_price,
                    "high": max(open_price, close_price) + 1.0,
                    "low": min(open_price, close_price) - 1.0,
                    "close": close_price,
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


def verified_forward_audit(
    frozen: dict[str, object],
    settlements: list[dict[str, object]],
    historical: dict[str, object],
) -> dict[str, object]:
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


def performance_summary_from(
    settlements: list[dict[str, object]],
) -> dict[str, object]:
    latest = settlements[-1]
    return {
        "status": "PASS",
        "candidate_hash": latest["candidate_hash"],
        "settlement_count": len(settlements),
        "outcome_period_count": len(settlements) - 1,
        "rebalance_execution_count": sum(
            int(
                dict(item.get("decision_execution") or {}).get("execute") is True
                and str(dict(item.get("decision_execution") or {}).get("reason") or "")
                == "relative_strength_rebalance"
                and str(dict(item.get("decision_execution") or {}).get("status") or "")
                in {"EXECUTED", "EXECUTED_NO_FILL"}
            )
            for item in settlements
        ),
        "unsettled_observation_dates": [],
        "execution_authority_violation_count": 0,
        "latest_settlement_hash": latest["settlement_hash"],
        "strategy": {
            "max_drawdown_pct": latest["strategy"]["state"]["max_drawdown_pct"],
        },
        "cumulative_excess_return_pct": latest["cumulative_excess_return_pct"],
    }


class PortfolioForwardStatisticalAuditTests(unittest.TestCase):
    def test_historical_block_claim_supplies_contract_but_does_not_decide_forward_result(self) -> None:
        frozen = frozen_candidate(outcomes=5, rebalances=6)
        historical = verified_historical_audit(frozen, claim_status="BLOCK")
        settlements = synthetic_settlement_chain(5)

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

        self.assertEqual(report["schema_version"], PORTFOLIO_FORWARD_STATISTICAL_AUDIT_SCHEMA_VERSION)
        self.assertEqual(report["status"], "NOT_DUE")
        self.assertEqual(report["maturity"]["status"], "NOT_DUE")
        self.assertEqual(report["stage"], {})
        self.assertEqual(report["statistical_contract"]["source_historical_claim_status"], "BLOCK")
        self.assertEqual(report["contract_comparison"]["status"], "PASS")
        self.assertEqual(
            report["contract_comparison"]["allowed_difference"],
            {
                "field": "minimum_observations",
                "historical": 120,
                "forward": 5,
                "reason": "FROZEN_CANDIDATE_FORWARD_MATURITY_FLOOR",
            },
        )
        self.assertTrue(all(
            item["matches"]
            for item in report["contract_comparison"]["copied_fields"].values()
        ))
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(report["profitability_proven"])
        self.assertFalse(report["paper_authorized"])
        self.assertFalse(report["live_order_allowed"])

    def test_due_forward_stage_recomputes_from_settlements_and_rejects_resealed_tamper(self) -> None:
        frozen = frozen_candidate(outcomes=10, rebalances=10)
        historical = verified_historical_audit(frozen, claim_status="BLOCK")
        settlements = synthetic_settlement_chain(10)
        report = audit_forward_portfolio_statistics(
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
            generated_at=100,
        )

        self.assertEqual(report["maturity"]["status"], "DUE")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["conclusion"], "FORWARD_STATISTICAL_CONTRACT_PASS")
        self.assertEqual(report["stage"]["status"], "PASS")

        forged = deepcopy(report)
        forged["series_evidence"]["rows"][1]["strategy_equity"] += 50_000.0
        series_content = dict(forged["series_evidence"])
        series_content.pop("series_hash", None)
        forged["series_evidence"]["series_hash"] = canonical_hash(series_content)
        forged["input_binding"]["forward_series_hash"] = forged["series_evidence"]["series_hash"]
        forged["input_binding"]["binding_hash"] = canonical_hash({
            key: value
            for key, value in forged["input_binding"].items()
            if key != "binding_hash"
        })
        forged["audit_hash"] = canonical_hash(forward_statistical_audit_content(forged))

        verification = verify_forward_portfolio_statistical_audit_semantics(
            forged,
            candidate=frozen,
            settlements=settlements,
            historical_statistical_audit=historical,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "forward_statistical_audit_semantic_mismatch:series_evidence",
            verification["blockers"],
        )
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])

    def test_v2_readiness_is_collecting_before_due_and_fail_closed_when_due_evidence_missing(self) -> None:
        collecting_candidate = frozen_candidate(outcomes=6, rebalances=6)
        historical = verified_historical_audit(collecting_candidate, claim_status="BLOCK")
        settlements = synthetic_settlement_chain(5)
        summary = performance_summary_from(settlements)
        collecting = build_forward_performance_readiness(
            candidate=collecting_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=summary,
            historical_statistical_audit=historical,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        self.assertEqual(collecting["status"], "COLLECTING")
        self.assertEqual(collecting["forward_statistical_audit_due_status"], "NOT_DUE")

        due_candidate = frozen_candidate(outcomes=5, rebalances=5)
        due_historical = verified_historical_audit(due_candidate, claim_status="BLOCK")
        missing = build_forward_performance_readiness(
            candidate=due_candidate,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=summary,
            historical_statistical_audit=due_historical,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        self.assertEqual(missing["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertIn("forward_statistical_audit_present", missing["blockers"])
        self.assertNotIn("historical_statistical_audit_pass", missing["evidence_checks"])
        self.assertEqual(missing["historical_statistical_claim_status"], "BLOCK")
        self.assertFalse(missing["paper_authorized"])
        self.assertFalse(missing["live_order_allowed"])

    def test_v2_readiness_uses_verified_forward_claim_and_legacy_contract_is_unchanged(self) -> None:
        frozen = frozen_candidate(outcomes=10, rebalances=10)
        historical = verified_historical_audit(frozen, claim_status="BLOCK")
        settlements = synthetic_settlement_chain(10)
        summary = performance_summary_from(settlements)
        forward_audit = verified_forward_audit(frozen, settlements, historical)

        readiness = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=summary,
            historical_statistical_audit=historical,
            forward_statistical_audit=forward_audit,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_READY")
        self.assertEqual(readiness["forward_statistical_audit_due_status"], "DUE")
        self.assertTrue(readiness["integrity_checks"]["forward_statistical_audit_integrity_pass"])
        self.assertTrue(readiness["evidence_checks"]["forward_statistical_audit_pass"])
        self.assertFalse(readiness["paper_authorized"])
        self.assertFalse(readiness["live_order_allowed"])

        invalid_schema = deepcopy(forward_audit)
        invalid_schema["schema_version"] = "portfolio-forward-statistical-audit-v0"
        blocked = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=summary,
            historical_statistical_audit=historical,
            forward_statistical_audit=invalid_schema,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("forward_statistical_audit_integrity_pass", blocked["blockers"])

        legacy = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=summary,
            historical_statistical_audit=historical,
        )
        self.assertEqual(legacy["schema_version"], LEGACY_PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION)
        self.assertEqual(legacy["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertIn("historical_statistical_audit_pass", legacy["blockers"])

    def test_due_negative_forward_result_is_valid_block_evidence_not_artifact_corruption(self) -> None:
        frozen = frozen_candidate(outcomes=10, rebalances=10)
        historical = verified_historical_audit(frozen, claim_status="BLOCK")
        settlements = synthetic_settlement_chain(10, weak_edge=True)
        forward_audit = verified_forward_audit(frozen, settlements, historical)

        self.assertEqual(forward_audit["maturity"]["status"], "DUE")
        self.assertEqual(forward_audit["status"], "BLOCK")
        self.assertEqual(forward_audit["conclusion"], "FORWARD_STATISTICAL_CONTRACT_FAILED")
        self.assertEqual(forward_audit["verification_status"], "PASS")
        self.assertEqual(forward_audit["stage"]["status"], "BLOCK")

        readiness = build_forward_performance_readiness(
            candidate=frozen,
            shadow_audit={"status": "PASS", "valid_observation_count": len(settlements)},
            performance_summary=performance_summary_from(settlements),
            historical_statistical_audit=historical,
            forward_statistical_audit=forward_audit,
            readiness_schema_version=PORTFOLIO_FORWARD_READINESS_SCHEMA_VERSION,
        )

        self.assertEqual(readiness["status"], "RESEARCH_REVIEW_BLOCKED")
        self.assertTrue(readiness["integrity_checks"]["forward_statistical_audit_integrity_pass"])
        self.assertFalse(readiness["evidence_checks"]["forward_statistical_audit_pass"])
        self.assertFalse(readiness["paper_authorized"])
        self.assertFalse(readiness["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
