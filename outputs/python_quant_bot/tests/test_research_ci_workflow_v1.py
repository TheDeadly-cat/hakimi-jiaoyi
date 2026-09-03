from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "research-contracts.yml"


class ResearchCiWorkflowV1Tests(unittest.TestCase):
    @classmethod
    def workflow(cls) -> str:
        return WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_root_workflow_has_read_only_bounded_activation(self) -> None:
        workflow = self.workflow()
        self.assertTrue(WORKFLOW_PATH.is_file())
        self.assertIn("name: Research Contracts", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("timeout-minutes: 15", workflow)
        self.assertIn('working-directory: outputs/python_quant_bot', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertEqual(workflow.count('- "src/**"'), 2)
        self.assertEqual(workflow.count('- "examples/**"'), 2)
        self.assertEqual(workflow.count('- "hakimi-research.ps1"'), 2)
        self.assertEqual(workflow.count('- ".gitattributes"'), 2)
        self.assertEqual(workflow.count('- "requirements.research.lock"'), 2)
        self.assertIn('PYTHONPATH: "${{ github.workspace }}/src"', workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("secrets.", workflow)

    def test_workflow_uses_locked_current_toolchain(self) -> None:
        workflow = self.workflow()
        self.assertEqual(workflow.count("uses: actions/checkout@v7"), 1)
        self.assertEqual(workflow.count("uses: actions/setup-python@v7"), 1)
        self.assertIn('python-version: "3.14"', workflow)
        self.assertIn(
            "python -m pip install --requirement requirements.research.lock",
            workflow,
        )
        self.assertIn(
            "      - name: Install active research dependency closure\n"
            "        working-directory: ${{ github.workspace }}\n"
            "        run: python -m pip install --requirement requirements.research.lock",
            workflow,
        )
        self.assertIn("python -m pip check", workflow)
        self.assertNotIn("pip install --upgrade", workflow)

    def test_windows_long_paths_are_enabled_before_checkout(self) -> None:
        workflow = self.workflow()
        long_paths_step = (
            "      - name: Enable Windows Git long paths before checkout\n"
            "        working-directory: ${{ github.workspace }}\n"
            "        run: git config --global core.longpaths true"
        )
        checkout_step = "      - name: Check out source without persisted credentials"
        self.assertEqual(
            workflow.count("git config --global core.longpaths true"),
            1,
        )
        self.assertIn(long_paths_step, workflow)
        self.assertLess(workflow.index(long_paths_step), workflow.index(checkout_step))
        self.assertNotIn("core.longpaths false", workflow)

    def test_workflow_runs_only_explicit_contract_consumers(self) -> None:
        workflow = self.workflow()
        modules = [
            "tests.test_exchange_terminal_layer_dependency_audit_v2",
            "tests.test_research_only_architecture",
            "tests.test_domain_contracts_fail_closed_v1",
            "tests.test_legacy_cli_boundary",
            "tests.test_quant_bot_backtest",
            "tests.test_reproducible_experiment_manifest_v1",
            "tests.test_research_dependency_lock_v1",
            "tests.test_research_ci_workflow_v1",
            "tests.test_canonical_product_capability_source_v1",
            "tests.test_canonical_experiment_manifest_source_v1",
            "tests.test_canonical_research_config_source_v1",
            "tests.test_canonical_research_models_source_v1",
            "tests.test_canonical_research_execution_source_v1",
            "tests.test_canonical_research_risk_source_v1",
            "tests.test_canonical_research_backtest_source_v1",
            "tests.test_canonical_research_data_source_v1",
            "tests.test_canonical_research_strategies_source_v1",
            "tests.test_canonical_research_indicators_source_v1",
            "tests.test_canonical_research_logging_reporting_source_v1",
            "tests.test_canonical_cli_entrypoint_v1",
            "tests.test_frozen_evaluation_protocol_v1",
            "tests.test_fixed_baseline_matrix_v1",
            "tests.test_volatility_matched_comparison_v1",
            "tests.test_prior_window_volatility_target_baseline_v1",
            "tests.test_fixed_parameter_walk_forward_v1",
            "tests.test_parameter_stability_matrix_v1",
            "tests.test_multiple_testing_ledger_v1",
            "tests.test_frozen_market_regime_analysis_v1",
            "tests.test_frozen_tail_distribution_analysis_v1",
            "tests.test_distribution_evidence_v1",
            "tests.test_quant_bot_compatibility_package_v1",
            "tests.test_canonical_terminal_utils_source_v1",
            "tests.test_canonical_terminal_config_source_v1",
            "tests.test_canonical_candle_contract_source_v1",
            "tests.test_canonical_stock_data_quality_source_v1",
            "tests.test_stock_data_quality_boundary_v2",
            "tests.test_stock_candle_temporal_conformance_v1",
            "tests.test_market_calendar_attestation_v1",
            "tests.test_canonical_stock_candle_structure_source_v1",
            "tests.test_canonical_stock_candle_revision_policy_v1",
            "tests.test_canonical_market_data_research_projection_v1",
            "tests.test_frozen_dataset_governance_v1",
            "tests.test_frozen_dataset_calendar_conformance_v1",
            "tests.test_frozen_execution_adversity_v1",
            "tests.test_frozen_bootstrap_confidence_v1",
            "tests.test_stock_market_data_governance_v1",
            "tests.test_frozen_statistical_correction_v1",
            "tests.test_deterministic_strategy_research_dossier_v1",
        ]
        self.assertEqual(workflow.count("python -B -m unittest"), 1)
        self.assertIn("python -B -m hakimi_research frozen-benchmark", workflow)
        self.assertIn("Verify deterministic Frozen OOS benchmark reference", workflow)
        self.assertIn(
            "python -B -m hakimi_research strategy-family-benchmark",
            workflow,
        )
        self.assertIn(
            "Verify deterministic strategy-family benchmark reference",
            workflow,
        )
        self.assertIn(
            "python -B -m hakimi_research strategy-robustness-benchmark",
            workflow,
        )
        self.assertIn(
            "Verify deterministic strategy-robustness benchmark reference",
            workflow,
        )
        self.assertIn(
            "python -B -m hakimi_research strategy-statistical-correction-benchmark",
            workflow,
        )
        self.assertIn(
            "Verify deterministic strategy statistical-correction reference",
            workflow,
        )
        self.assertIn(
            "python -B -m hakimi_research strategy-research-dossier",
            workflow,
        )
        self.assertIn(
            "Verify deterministic strategy research dossier",
            workflow,
        )
        self.assertIn(
            "Verify Electron research-only capability consumers",
            workflow,
        )
        self.assertIn("Verify neutral market-data research renderer", workflow)
        self.assertIn(
            "node outputs/python_quant_bot/exchange_terminal/static/market_data_research_projection.test.js",
            workflow,
        )
        self.assertEqual(
            workflow.count(
                "node outputs/hakimi_trade_electron/backend-runtime-contract.test.js"
            ),
            1,
        )
        self.assertEqual(
            workflow.count(
                "node outputs/hakimi_trade_electron/research-capability-lock.test.js"
            ),
            1,
        )
        for module in modules:
            self.assertEqual(workflow.count(module), 1)
        for forbidden in (
            "run_bot.py",
            "dashboard_app.py",
            "uvicorn",
            "streamlit run",
            "live_trading_enabled",
            "paper_trading",
            "git push",
        ):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
