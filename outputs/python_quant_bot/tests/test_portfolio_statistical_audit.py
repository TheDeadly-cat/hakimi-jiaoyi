from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services.portfolio_statistical_audit import (
    DEFAULT_RESAMPLE_COUNT,
    MAX_BLOCK_LENGTH,
    MAX_RESAMPLE_COUNT,
    PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION,
    audit_portfolio_research_statistics,
    statistical_audit_content,
    statistical_bootstrap_budget_blockers,
    verify_portfolio_statistical_audit_semantics,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def backtest_stage(*, active_edge: float, rows: int = 150) -> tuple[dict[str, object], dict[str, object]]:
    start = date(2025, 1, 1)
    strategy_equity = 100_000.0
    benchmark_equity = 100_000.0
    strategy_curve = []
    benchmark_curve = []
    for index in range(rows):
        benchmark_return = 0.0002 + ((index % 7) - 3) * 0.00008
        active_return = active_edge + ((index % 5) - 2) * 0.00003
        strategy_equity *= 1.0 + benchmark_return + active_return
        benchmark_equity *= 1.0 + benchmark_return
        session_date = (start + timedelta(days=index)).isoformat()
        strategy_curve.append({"date": session_date, "equity": round(strategy_equity, 2)})
        benchmark_curve.append({"date": session_date, "equity": round(benchmark_equity, 2)})
    strategy = {
        "run_hash": "1" * 64,
        "initial_cash": 100_000.0,
        "equity_curve": strategy_curve,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    benchmark = {
        "benchmark_run_hash": "2" * 64,
        "initial_cash": 100_000.0,
        "equity_curve": benchmark_curve,
    }
    return strategy, benchmark


def research_report(*, active_edge: float) -> dict[str, object]:
    validation, validation_benchmark = backtest_stage(active_edge=active_edge)
    test, test_benchmark = backtest_stage(active_edge=active_edge)
    return {
        "batch_run_hash": "a" * 64,
        "spec_hash": "b" * 64,
        "spec": {"trial_count": 4},
        "dataset_manifest": {"data_hash": "c" * 64},
        "frozen_candidate": {"candidate_hash": "d" * 64},
        "validation": validation,
        "validation_benchmark": validation_benchmark,
        "test": test,
        "test_benchmark": test_benchmark,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class PortfolioStatisticalAuditTests(unittest.TestCase):
    def test_strong_paired_edge_passes_without_execution_authority(self) -> None:
        result = audit_portfolio_research_statistics(
            research_report(active_edge=0.0008),
            generated_at=100,
            resample_count=400,
        )

        self.assertEqual(result["schema_version"], PORTFOLIO_STATISTICAL_AUDIT_SCHEMA_VERSION)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stages"]["validation"]["status"], "PASS")
        self.assertEqual(result["stages"]["test"]["status"], "PASS")
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_weak_edge_is_blocked_by_resampling_contract(self) -> None:
        result = audit_portfolio_research_statistics(
            research_report(active_edge=0.0),
            generated_at=100,
            resample_count=400,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["stages"]["test"]["status"], "BLOCK")
        self.assertIn("observed_compound_excess_positive", result["stages"]["test"]["blockers"])

    def test_hash_is_deterministic_and_generated_time_is_not_evidence(self) -> None:
        report = research_report(active_edge=0.0008)
        first = audit_portfolio_research_statistics(report, generated_at=100, resample_count=400)
        repeated = audit_portfolio_research_statistics(report, generated_at=200, resample_count=400)

        self.assertEqual(first["audit_hash"], repeated["audit_hash"])
        self.assertEqual(first["stages"]["validation"]["stage_hash"], repeated["stages"]["validation"]["stage_hash"])
        self.assertNotEqual(first["generated_at"], repeated["generated_at"])

    def test_misaligned_dates_and_source_authority_fail_closed(self) -> None:
        misaligned = research_report(active_edge=0.0008)
        misaligned["test_benchmark"]["equity_curve"][0]["date"] = "2030-01-01"
        authority = deepcopy(research_report(active_edge=0.0008))
        authority["paper_authorized"] = True

        misaligned_result = audit_portfolio_research_statistics(
            misaligned,
            generated_at=100,
            resample_count=400,
        )
        authority_result = audit_portfolio_research_statistics(
            authority,
            generated_at=100,
            resample_count=400,
        )

        self.assertEqual(misaligned_result["status"], "BLOCK")
        self.assertIn("test:strategy_benchmark_dates_mismatch", misaligned_result["blockers"])
        self.assertEqual(authority_result["status"], "BLOCK")
        self.assertIn("source_contains_paper_authority", authority_result["blockers"])

    def test_missing_benchmark_binding_does_not_impersonate_execution_authority(self) -> None:
        report = research_report(active_edge=0.0008)
        report["validation_benchmark"].pop("benchmark_run_hash")

        result = audit_portfolio_research_statistics(
            report,
            generated_at=100,
            resample_count=400,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(result["checks"]["input_authority_is_research_only"])
        self.assertFalse(result["checks"]["input_binding_complete"])
        self.assertIn(
            "input_binding_missing:validation_benchmark_run_hash",
            result["blockers"],
        )

    def test_resealed_pass_claim_is_rejected_by_frozen_curve_recomputation(self) -> None:
        report = research_report(active_edge=0.0008)
        for stage in ("validation", "test"):
            report[stage]["equity_curve"] = report[stage]["equity_curve"][:30]
            report[f"{stage}_benchmark"]["equity_curve"] = report[f"{stage}_benchmark"]["equity_curve"][:30]
        forged = audit_portfolio_research_statistics(report, generated_at=100)
        self.assertEqual(forged["status"], "BLOCK")

        forged["status"] = "PASS"
        forged["conclusion"] = "STATISTICAL_PROMOTION_EVIDENCE_PASS"
        forged["blockers"] = []
        forged["checks"] = {key: True for key in forged["checks"]}
        for stage in ("validation", "test"):
            stage_payload = dict(forged["stages"][stage])
            stage_payload.pop("stage_hash", None)
            stage_payload["status"] = "PASS"
            stage_payload["blockers"] = []
            forged["stages"][stage] = {
                **stage_payload,
                "stage_hash": canonical_hash(stage_payload),
            }
        forged["audit_hash"] = canonical_hash(statistical_audit_content(forged))

        verification = verify_portfolio_statistical_audit_semantics(forged, report)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["expected_status"], "BLOCK")
        self.assertIn(
            "statistical_audit_semantic_mismatch:status",
            verification["blockers"],
        )
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])

    def test_boolean_initial_cash_cannot_pass_statistical_audit(self) -> None:
        report = research_report(active_edge=0.0008)
        report["validation"]["initial_cash"] = True

        result = audit_portfolio_research_statistics(
            report,
            generated_at=100,
            resample_count=400,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("validation:strategy:initial_cash_invalid", result["blockers"])
        self.assertEqual(result["stages"]["validation"]["status"], "BLOCK")

    def test_bootstrap_compute_budget_blocks_before_random_or_resampling_loops(self) -> None:
        self.assertEqual(DEFAULT_RESAMPLE_COUNT, 5_000)
        self.assertEqual(MAX_RESAMPLE_COUNT, 50_000)
        self.assertGreaterEqual(MAX_BLOCK_LENGTH, 150)
        report = research_report(active_edge=0.0008)

        with patch(
            "exchange_terminal.services.portfolio_statistical_audit.random.Random",
            side_effect=AssertionError("bootstrap loop must not start"),
        ) as random_constructor:
            huge_resamples = audit_portfolio_research_statistics(
                report,
                generated_at=100,
                resample_count=1_000_000_000,
                block_length=5,
            )
            repeated = audit_portfolio_research_statistics(
                report,
                generated_at=200,
                resample_count=1_000_000_000,
                block_length=5,
            )
            huge_block = audit_portfolio_research_statistics(
                report,
                generated_at=100,
                resample_count=400,
                block_length=1_000_000_000,
            )

        random_constructor.assert_not_called()
        self.assertEqual(huge_resamples["status"], "BLOCK")
        self.assertEqual(huge_block["status"], "BLOCK")
        self.assertEqual(huge_resamples["audit_hash"], repeated["audit_hash"])
        self.assertIn(
            "validation:bootstrap_resample_count_exceeds_budget:1000000000>50000",
            huge_resamples["blockers"],
        )
        self.assertIn(
            "test:bootstrap_block_length_exceeds_budget:1000000000>1024",
            huge_block["blockers"],
        )

    def test_bootstrap_block_length_cannot_exceed_sample_size(self) -> None:
        blockers = statistical_bootstrap_budget_blockers(
            resample_count=400,
            block_length=151,
            sample_size=150,
        )
        self.assertEqual(
            blockers,
            ["bootstrap_block_length_exceeds_sample_size:151>150"],
        )


if __name__ == "__main__":
    unittest.main()
