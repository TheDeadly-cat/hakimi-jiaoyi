from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_admission import (
    build_internal_backtest_admission,
    build_research_universe_contract,
    verify_internal_backtest_admission,
)
from exchange_terminal.services.research_exposure import audit_portfolio_temporal_exposure
from exchange_terminal.services.provider_governance import build_unassessed_provider_governance_contract
from tests.portfolio_governance_fixtures import experiment_binding


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def report_with_governance(report_dir: Path) -> dict[str, object]:
    report: dict[str, object] = {
        "mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "dataset_manifest": {"status": "PASS"},
        "validation": {"ok": True},
        "test": {"ok": True},
        "full": {"ok": True},
        "causal_audit": {"status": "PASS"},
        "development_checks": {
            "validation_rebalance_schedule_pass": True,
            "test_rebalance_schedule_pass": True,
            "full_rebalance_schedule_pass": True,
            "adjustment_contracts_pass": True,
            "return_accounting_double_count_protection_pass": True,
        },
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["universe_contract"] = build_research_universe_contract(
        benchmark_symbol="SPY",
        tradable_symbols=["AAPL", "NVDA"],
        declared_at="2026-08-01T00:00:00+00:00",
        selection_basis="STATIC_USER_WATCHLIST",
    )
    report["temporal_exposure_audit"] = audit_portfolio_temporal_exposure(
        report_dir,
        start_date="2026-01-01",
        end_date="2026-07-31",
        symbols=["SPY", "AAPL", "NVDA"],
    )
    report["experiment_governance"] = experiment_binding()
    report["provider_governance"] = build_unassessed_provider_governance_contract(
        provider_ids=["futu", "yahoo"],
        generated_at="2026-08-01T00:00:00Z",
    )
    return report


class PortfolioAdmissionTests(unittest.TestCase):
    def test_internal_backtest_can_be_ready_while_statistical_claims_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = report_with_governance(Path(temp_dir))
            audit = build_internal_backtest_admission(report)
            verification = verify_internal_backtest_admission(audit)

        self.assertEqual(audit["status"], "INTERNAL_BACKTEST_READY")
        self.assertEqual(audit["statistical_claim_status"], "DEVELOPMENT_EVIDENCE_ONLY")
        self.assertEqual(audit["paper_admission_status"], "BLOCKED")
        self.assertIn("static_universe_has_survivorship_bias", audit["blockers"])
        self.assertEqual(verification["status"], "PASS")

    def test_missing_causal_audit_blocks_internal_backtest_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = report_with_governance(Path(temp_dir))
            report["causal_audit"] = {"status": "BLOCK"}
            audit = build_internal_backtest_admission(report)

        self.assertEqual(audit["status"], "INTERNAL_BACKTEST_BLOCKED")
        self.assertIn("internal_check_failed:causal_prefix_audit_pass", audit["blockers"])

    def test_missing_preregistration_blocks_internal_backtest_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = report_with_governance(Path(temp_dir))
            report.pop("experiment_governance")
            audit = build_internal_backtest_admission(report)

        self.assertEqual(audit["status"], "INTERNAL_BACKTEST_BLOCKED")
        self.assertIn(
            "internal_check_failed:experiment_preregistered_and_single_claimed",
            audit["blockers"],
        )

    def test_tampered_admission_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit = build_internal_backtest_admission(report_with_governance(Path(temp_dir)))
            audit["paper_admission_status"] = "READY"
            verification = verify_internal_backtest_admission(audit)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("admission_hash_mismatch", verification["blockers"])
        self.assertIn("paper_admission_must_remain_blocked", verification["blockers"])

    def test_string_false_schedule_check_cannot_admit_backtest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = report_with_governance(Path(temp_dir))
            report["development_checks"]["validation_rebalance_schedule_pass"] = "false"

            audit = build_internal_backtest_admission(report)

        self.assertEqual(audit["status"], "INTERNAL_BACKTEST_BLOCKED")
        self.assertIn("internal_check_failed:validation_schedule_pass", audit["blockers"])

    def test_resealed_string_internal_check_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit = build_internal_backtest_admission(report_with_governance(Path(temp_dir)))
            audit["internal_checks"]["validation_schedule_pass"] = "false"
            audit.pop("admission_hash")
            audit["admission_hash"] = canonical_hash(audit)

            verification = verify_internal_backtest_admission(audit)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("admission_internal_check_types_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
