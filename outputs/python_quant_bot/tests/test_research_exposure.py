from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.research_exposure import (
    audit_blind_holdout_symbols,
    audit_portfolio_temporal_exposure,
    prior_symbol_exposure,
)


class ResearchExposureTests(unittest.TestCase):
    def test_unloaded_holdout_does_not_become_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "batch-1",
                "batch_spec": {"selection_symbols": ["AAPL"], "holdout_symbols": ["QQQ"]},
                "dataset_manifest": [{"symbol": "AAPL", "data_hash": "a", "first": "2024-01-01", "last": "2025-01-01"}],
                "test_cells": [{"symbol": "AAPL"}],
                "holdout_cells": [],
            }
            Path(temp_dir, "strategy_research_1.json").write_text(json.dumps(report), encoding="utf-8")

            exposure = prior_symbol_exposure(temp_dir)
            qqq = audit_blind_holdout_symbols(temp_dir, ["QQQ"])
            aapl = audit_blind_holdout_symbols(temp_dir, ["AAPL"])

        self.assertIn("SELECTION_TEST_EXPOSED", exposure["AAPL"][0]["roles"])
        self.assertEqual(qqq["status"], "PASS")
        self.assertEqual(aapl["status"], "BLOCK")

    def test_loaded_holdout_is_blocked_for_future_blind_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "batch-2",
                "batch_spec": {"selection_symbols": ["AAPL"], "holdout_symbols": ["QQQ"]},
                "dataset_manifest": [
                    {"symbol": "AAPL", "data_hash": "a"},
                    {"symbol": "QQQ", "data_hash": "q"},
                ],
                "test_cells": [],
                "holdout_cells": [{"symbol": "QQQ"}],
            }
            Path(temp_dir, "strategy_research_2.json").write_text(json.dumps(report), encoding="utf-8")

            audit = audit_blind_holdout_symbols(temp_dir, ["QQQ"])

        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["exposed_symbols"], ["QQQ"])

    def test_portfolio_development_reports_enter_the_same_exposure_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "portfolio-batch",
                "spec": {
                    "benchmark_symbol": "SPY",
                    "tradable_symbols": ["AAPL", "NVDA"],
                },
                "dataset_manifest": {
                    "symbols": ["SPY", "AAPL", "NVDA"],
                    "data_hash": "portfolio-data",
                    "first": "2023-01-01",
                    "last": "2026-01-01",
                },
            }
            Path(temp_dir, "portfolio_research_1.json").write_text(json.dumps(report), encoding="utf-8")

            exposure = prior_symbol_exposure(temp_dir)
            audit = audit_blind_holdout_symbols(temp_dir, ["AAPL", "SPY", "QCOM"])

        self.assertIn("PORTFOLIO_DEVELOPMENT_EXPOSED", exposure["AAPL"][0]["roles"])
        self.assertIn("PORTFOLIO_BENCHMARK_EXPOSED", exposure["SPY"][0]["roles"])
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["exposed_symbols"], ["AAPL", "SPY"])

    def test_portfolio_holdout_report_prevents_reusing_the_same_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "holdout-batch",
                "spec": {"benchmark_symbol": "SPY", "holdout_symbols": ["AMAT", "LRCX"]},
                "dataset_manifest": {
                    "symbols": ["SPY", "AMAT", "LRCX"],
                    "data_hash": "holdout-data",
                    "first": "2023-01-01",
                    "last": "2026-01-01",
                },
            }
            Path(temp_dir, "portfolio_holdout_1.json").write_text(json.dumps(report), encoding="utf-8")

            exposure = prior_symbol_exposure(temp_dir)
            audit = audit_blind_holdout_symbols(temp_dir, ["AMAT", "QCOM"])

        self.assertIn("PORTFOLIO_CROSS_SECTIONAL_HOLDOUT_EXPOSED", exposure["AMAT"][0]["roles"])
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["exposed_symbols"], ["AMAT"])

    def test_overlapping_portfolio_test_window_is_not_fresh_holdout_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "portfolio-batch",
                "spec_hash": "spec-hash",
                "spec": {"benchmark_symbol": "SPY", "tradable_symbols": ["AAPL"]},
                "dataset_manifest": {"symbols": ["SPY", "AAPL"], "data_hash": "data-hash"},
                "validation": {"evaluation_window": {"start": "2025-01-01", "end": "2025-06-30"}},
                "test": {
                    "run_hash": "test-run",
                    "evaluation_window": {"start": "2025-07-01", "end": "2025-12-31"},
                },
                "full": {"evaluation_window": {"start": "2024-01-01", "end": "2025-12-31"}},
            }
            Path(temp_dir, "portfolio_research_1.json").write_text(json.dumps(report), encoding="utf-8")

            audit = audit_portfolio_temporal_exposure(
                temp_dir,
                start_date="2025-10-01",
                end_date="2026-03-31",
                symbols=["SPY", "AAPL"],
            )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["classification"], "EXPOSED")
        self.assertEqual(audit["prior_report_count"], 1)
        self.assertEqual(audit["distinct_test_run_count"], 1)

    def test_strictly_future_temporal_window_remains_unexposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {
                "batch_run_hash": "portfolio-batch",
                "spec": {"benchmark_symbol": "SPY", "tradable_symbols": ["AAPL"]},
                "dataset_manifest": {"symbols": ["SPY", "AAPL"]},
                "test": {"evaluation_window": {"start": "2025-07-01", "end": "2025-12-31"}},
            }
            Path(temp_dir, "portfolio_research_1.json").write_text(json.dumps(report), encoding="utf-8")

            audit = audit_portfolio_temporal_exposure(
                temp_dir,
                start_date="2026-01-01",
                end_date="2026-06-30",
                symbols=["SPY", "AAPL"],
            )

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["classification"], "UNTOUCHED")
        self.assertTrue(audit["fresh_holdout_eligible"])


if __name__ == "__main__":
    unittest.main()
