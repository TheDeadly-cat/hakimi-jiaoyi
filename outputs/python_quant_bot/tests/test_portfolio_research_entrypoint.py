from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_internal_portfolio_research as research_entrypoint
from tests.portfolio_governance_fixtures import attested_clock


class PortfolioResearchEntrypointTests(unittest.TestCase):
    def test_missing_experiment_id_blocks_before_market_data_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()
            argv = [
                "run_internal_portfolio_research.py",
                "--experiment-db",
                str(Path(temp_dir) / "experiments.sqlite3"),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(research_entrypoint, "aligned_payloads") as aligned,
                redirect_stdout(output),
            ):
                result = research_entrypoint.main()

        payload = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(payload["status"], "BLOCK")
        self.assertIn("preregistered_experiment_id_required", payload["blockers"])
        aligned.assert_not_called()

    def test_protocol_drift_blocks_before_market_data_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "experiments.sqlite3"
            registration_output = io.StringIO()
            register_argv = [
                "run_internal_portfolio_research.py",
                "--experiment-db",
                str(db_path),
                "--register-only",
            ]
            with (
                patch.object(sys, "argv", register_argv),
                patch.object(research_entrypoint, "attest_utc_clock", return_value=attested_clock(100_000)),
                patch.object(research_entrypoint, "aligned_payloads") as aligned,
                redirect_stdout(registration_output),
            ):
                registered_result = research_entrypoint.main()
            registered = json.loads(registration_output.getvalue())
            experiment_id = str(registered["experiment_id"])

            run_output = io.StringIO()
            drift_argv = [
                "run_internal_portfolio_research.py",
                "--experiment-db",
                str(db_path),
                "--experiment-id",
                experiment_id,
                "--cutoff",
                "2026-07-29",
            ]
            with (
                patch.object(sys, "argv", drift_argv),
                patch.object(research_entrypoint, "attest_utc_clock", return_value=attested_clock(101_000)),
                patch.object(research_entrypoint, "aligned_payloads") as drift_aligned,
                redirect_stdout(run_output),
            ):
                run_result = research_entrypoint.main()

        blocked = json.loads(run_output.getvalue())
        self.assertEqual(registered_result, 0)
        self.assertEqual(run_result, 2)
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("experiment_protocol_drift", blocked["blockers"])
        aligned.assert_not_called()
        drift_aligned.assert_not_called()

    def test_protocol_hash_binds_universe_and_cutoff(self) -> None:
        base = research_entrypoint.build_research_protocol(
            benchmark="SPY",
            tradables=["AAPL", "NVDA"],
            limit=780,
            cutoff="2026-07-30",
        )
        changed_cutoff = research_entrypoint.build_research_protocol(
            benchmark="SPY",
            tradables=["AAPL", "NVDA"],
            limit=780,
            cutoff="2026-07-29",
        )
        changed_universe = research_entrypoint.build_research_protocol(
            benchmark="SPY",
            tradables=["AAPL"],
            limit=780,
            cutoff="2026-07-30",
        )

        self.assertNotEqual(base["protocol_hash"], changed_cutoff["protocol_hash"])
        self.assertNotEqual(base["protocol_hash"], changed_universe["protocol_hash"])
        self.assertFalse(base["paper_authorized"])
        self.assertFalse(base["live_order_allowed"])

    def test_g46_protocol_revalidates_runtime_authorization_without_strategy_drift(self) -> None:
        protocol = research_entrypoint.build_research_protocol(
            benchmark="SPY",
            tradables=["AAPL", "NVDA"],
            limit=780,
            cutoff="2026-07-30",
        )

        self.assertEqual(
            protocol["research_generation"],
            "PORTFOLIO_G46_RUNTIME_AUTHORIZATION_SEMANTICS",
        )
        self.assertEqual(protocol["prior_generation_mechanism_status"], "PROMISING_NEEDS_FRESH_HOLDOUT")
        self.assertEqual(protocol["prior_generation_internal_admission"], "INTERNAL_BACKTEST_READY")
        self.assertEqual(protocol["prior_generation_execution_rehearsal_status"], "PASS")
        self.assertTrue(protocol["prior_generation_candidate_created"])
        self.assertFalse(protocol["prior_generation_parameter_selection_allowed"])
        self.assertEqual(
            protocol["prior_candidate_hash"],
            "0faa06988aca5396e3812136ebfa75f300e6fc9e9c2b0bc998cad82cf5a6a237",
        )
        self.assertTrue(protocol["prior_candidate_is_immediate_prior_generation"])
        self.assertFalse(protocol["prior_candidate_still_frozen_in_source_runtime"])
        self.assertTrue(protocol["prior_candidate_retired_before_implementation_change"])
        self.assertFalse(protocol["parameter_change_from_prior_generation"])
        self.assertFalse(protocol["strategy_parameter_change_from_prior_generation"])
        self.assertFalse(protocol["universe_change_from_prior_generation"])
        self.assertFalse(protocol["data_window_change_from_prior_generation"])
        self.assertFalse(protocol["cost_model_change_from_prior_generation"])
        self.assertFalse(protocol["promotion_threshold_change_from_prior_generation"])
        self.assertTrue(protocol["risk_snapshot_semantics_change_from_prior_generation"])
        self.assertFalse(protocol["runtime_orchestration_change_from_prior_generation"])
        self.assertEqual(
            protocol["prior_operational_failure_report"],
            "internal_portfolio_backtest_pack_g45_runtime_authorization_semantics_invalidated.json",
        )
        self.assertIn(
            "separate_risk_policy_acceptance_from_effective_runtime_paper_authority",
            protocol["implementation_change_scope"],
        )
        self.assertIn(
            "bind_automated_paper_authority_to_exact_pipeline_run",
            protocol["implementation_change_scope"],
        )
        source_names = {
            path.resolve().relative_to(PROJECT_ROOT).as_posix()
            for path in research_entrypoint.research_source_files()
        }
        self.assertIn("exchange_terminal/static/app.js", source_names)
        self.assertFalse(protocol["prior_candidate_sample_migration_allowed"])
        self.assertFalse(protocol["paper_authorized"])
        self.assertFalse(protocol["live_order_allowed"])

    def test_finite_metric_reader_preserves_explicit_zero(self) -> None:
        self.assertEqual(research_entrypoint.finite_number(0.0, 100.0), 0.0)
        self.assertEqual(research_entrypoint.finite_number(float("nan"), 100.0), 100.0)

    def test_benchmark_report_has_deterministic_full_report_hash(self) -> None:
        rows = [
            {
                "date": f"2026-01-{day:02d}",
                "ts_ms": day * 86_400_000,
                "open": 100.0 + day,
                "high": 101.0 + day,
                "low": 99.0 + day,
                "close": 100.5 + day,
                "volume": 1_000_000.0,
                "complete": True,
            }
            for day in range(1, 21)
        ]
        payload = {"rows": rows, "source": "test"}

        first = research_entrypoint.benchmark_report(
            payload,
            symbol="SPY",
            position_pct=60.0,
            evaluation_start_index=0,
        )
        repeated = research_entrypoint.benchmark_report(
            payload,
            symbol="SPY",
            position_pct=60.0,
            evaluation_start_index=0,
        )

        self.assertTrue(first["benchmark_run_hash"])
        self.assertEqual(first["benchmark_run_hash"], repeated["benchmark_run_hash"])
        self.assertIn(
            Path(research_entrypoint.strategy_benchmark_module.__file__).resolve(),
            [path.resolve() for path in research_entrypoint.research_source_files()],
        )
        self.assertIn(
            Path(research_entrypoint.portfolio_backtest_module.__file__)
            .with_name("portfolio_backtest_replay_driver.py")
            .resolve(),
            [path.resolve() for path in research_entrypoint.research_source_files()],
        )

    def test_validation_prefix_uses_one_market_calendar_cutoff_for_every_symbol(self) -> None:
        payloads = {
            "SPY": {"rows": [{"date": "2026-01-01"}, {"date": "2026-01-02"}]},
            "AAPL": {"rows": [{"date": "2025-12-31"}, {"date": "2026-01-02"}]},
        }
        manifest = {
            "market_calendar": {
                "expected_dates": ["2026-01-01", "2026-01-02"],
            },
        }

        with patch.object(
            research_entrypoint,
            "_through_cutoff",
            side_effect=lambda payload, cutoff, lineage: {**payload, "cutoff": cutoff, "lineage": lineage},
        ) as through_cutoff:
            sliced, cutoff = research_entrypoint.prefix_payloads_through_index(
                payloads,
                manifest,
                1,
                "experiment-test",
            )

        self.assertEqual(cutoff, "2026-01-01")
        self.assertEqual({item["cutoff"] for item in sliced.values()}, {"2026-01-01"})
        self.assertEqual({item["lineage"] for item in sliced.values()}, {"experiment-test"})
        self.assertEqual(through_cutoff.call_count, 2)


if __name__ == "__main__":
    unittest.main()
