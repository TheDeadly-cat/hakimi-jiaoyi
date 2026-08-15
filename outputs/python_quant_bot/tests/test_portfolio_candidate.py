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

from exchange_terminal.services.portfolio_candidate import (
    build_frozen_portfolio_candidate,
    implementation_fingerprint,
    verify_frozen_portfolio_candidate,
)
from exchange_terminal.services.portfolio_admission import (
    build_internal_backtest_admission,
    build_research_universe_contract,
)
from exchange_terminal.services.research_exposure import audit_portfolio_temporal_exposure
from exchange_terminal.services.provider_governance import build_unassessed_provider_governance_contract
from tests.portfolio_governance_fixtures import experiment_binding


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def promising_report(report_dir: Path, source_files: list[Path] | None = None) -> dict[str, object]:
    report: dict[str, object] = {
        "mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "batch_run_hash": "report-hash",
        "spec": {"research_generation": "PORTFOLIO_G11", "trial_count": 3},
        "spec_hash": "spec-hash",
        "dataset_manifest": {
            "status": "PASS",
            "data_hash": "data-hash",
            "first": "2023-01-01",
            "last": "2026-01-01",
            "symbols": ["SPY", "AAPL"],
        },
        "validation": {"ok": True},
        "test": {"ok": True},
        "full": {"ok": True},
        "causal_audit": {"status": "PASS"},
        "correlation_matrix": {"status": "PASS"},
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
        tradable_symbols=["AAPL"],
        declared_at="2026-01-02T00:00:00+00:00",
        selection_basis="TEST_STATIC_LIST",
    )
    report["temporal_exposure_audit"] = audit_portfolio_temporal_exposure(
        report_dir,
        start_date="2025-07-01",
        end_date="2026-01-01",
        symbols=["SPY", "AAPL"],
    )
    fingerprint = implementation_fingerprint(source_files or [Path(__file__)])
    report["experiment_governance"] = experiment_binding(
        implementation_fingerprint=str(fingerprint["fingerprint"]),
    )
    report["provider_governance"] = build_unassessed_provider_governance_contract(
        provider_ids=["test_fixture"],
        generated_at="2026-01-02T00:00:00Z",
    )
    report["backtest_admission"] = build_internal_backtest_admission(report)
    return report


class PortfolioCandidateTests(unittest.TestCase):
    def test_promising_report_freezes_without_execution_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            report = promising_report(Path(temp_dir), [source])

            first = build_frozen_portfolio_candidate(report, source_files=[source])
            second = build_frozen_portfolio_candidate(report, source_files=[source])
            verification = verify_frozen_portfolio_candidate(first)

        self.assertEqual(first["status"], "FROZEN_DEVELOPMENT_CANDIDATE")
        self.assertEqual(first["candidate_hash"], second["candidate_hash"])
        self.assertEqual(first["authorization_state"], "BLOCKED_PENDING_FRESH_TEMPORAL_HOLDOUT_AND_FORWARD")
        self.assertFalse(first["paper_authorized"])
        self.assertFalse(first["live_order_allowed"])
        self.assertEqual(verification["status"], "PASS")

    def test_failed_research_cannot_be_frozen_as_a_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            report = {
                "mechanism_status": "REVISE_OR_REJECT",
                "causal_audit": {"status": "BLOCK"},
                "correlation_matrix": {"status": "PASS"},
            }

            candidate = build_frozen_portfolio_candidate(report, source_files=[source])

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertIn("mechanism_not_promising", candidate["blockers"])

    def test_candidate_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate = build_frozen_portfolio_candidate(
                promising_report(Path(temp_dir), [source]),
                source_files=[source],
            )
            candidate["spec"]["top_n"] = 99

            verification = verify_frozen_portfolio_candidate(candidate)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("candidate_hash_mismatch", verification["blockers"])

    def test_resealed_string_false_authority_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate = build_frozen_portfolio_candidate(
                promising_report(Path(temp_dir), [source]),
                source_files=[source],
            )
            candidate["research_only"] = "false"
            candidate.pop("candidate_hash")
            candidate["candidate_hash"] = canonical_hash(candidate)

            verification = verify_frozen_portfolio_candidate(candidate)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("candidate_has_invalid_execution_authority", verification["blockers"])

    def test_resealed_string_false_research_gate_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            candidate = build_frozen_portfolio_candidate(
                promising_report(Path(temp_dir), [source]),
                source_files=[source],
            )
            candidate["fresh_holdout_required"] = "false"
            candidate.pop("candidate_hash")
            candidate["candidate_hash"] = canonical_hash(candidate)

            verification = verify_frozen_portfolio_candidate(candidate)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("candidate_research_gate_missing", verification["blockers"])

    def test_candidate_without_registered_experiment_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir, "engine.py")
            source.write_text("VALUE = 1\n", encoding="utf-8")
            report = promising_report(Path(temp_dir), [source])
            report.pop("experiment_governance")
            report["backtest_admission"] = build_internal_backtest_admission(report)

            candidate = build_frozen_portfolio_candidate(report, source_files=[source])

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertTrue(any(item.startswith("experiment_binding:") for item in candidate["blockers"]))

    def test_imported_local_source_and_runtime_are_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "engine_pkg"
            package.mkdir()
            initializer = package / "__init__.py"
            helper = package / "helper.py"
            source = package / "engine.py"
            initializer.write_text("", encoding="utf-8")
            helper.write_text("VALUE = 1\n", encoding="utf-8")
            source.write_text("from .helper import VALUE\n", encoding="utf-8")
            report = promising_report(root, [source])
            candidate = build_frozen_portfolio_candidate(report, source_files=[source])
            frozen_names = {Path(item["path"]).name for item in candidate["implementation"]["files"]}
            helper.write_text("VALUE = 2\n", encoding="utf-8")

            verification = verify_frozen_portfolio_candidate(candidate)

        self.assertEqual(candidate["status"], "FROZEN_DEVELOPMENT_CANDIDATE")
        self.assertEqual(frozen_names, {"__init__.py", "engine.py", "helper.py"})
        self.assertTrue(candidate["implementation"]["runtime"]["python_version"])
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(any("implementation_source_changed:" in item for item in verification["blockers"]))


if __name__ == "__main__":
    unittest.main()
