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
        self.assertIn("python -m pip check", workflow)
        self.assertNotIn("pip install --upgrade", workflow)

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
            "tests.test_canonical_cli_entrypoint_v1",
            "tests.test_frozen_evaluation_protocol_v1",
        ]
        self.assertEqual(workflow.count("python -B -m unittest"), 1)
        self.assertIn("python -B examples/deterministic_experiment/verify.py", workflow)
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
