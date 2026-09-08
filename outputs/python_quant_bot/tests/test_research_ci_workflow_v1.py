from __future__ import annotations

from pathlib import Path
import re
import json
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "research-contracts.yml"


class ResearchCiWorkflowV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.jobs = cls.workflow.split("\njobs:\n", 1)[1]

    def test_seven_failure_domains_are_independent_and_gate_requires_them_all(self) -> None:
        job_ids = re.findall(r"^  ([a-z][a-z0-9-]+):\s*$", self.jobs, re.MULTILINE)
        self.assertEqual(
            job_ids,
            [
                "python-contracts",
                "deterministic-references",
                "legacy-reference-replay",
                "mvp-contracts",
                "electron-capability-contract",
                "market-data-renderer",
                "package-install-smoke",
                "research-required",
            ],
        )
        domains, gate = self.jobs.split("  research-required:\n", 1)
        self.assertNotIn("\n    needs:", domains)
        self.assertNotIn("\n    if:", domains)
        self.assertIn("if: ${{ always() }}", gate)
        needed_jobs = re.findall(r"^      - ([a-z][a-z0-9-]+)$", gate, re.MULTILINE)
        self.assertEqual(needed_jobs, job_ids[:-1])
        self.assertIn("RESEARCH_CI_NEEDS: ${{ toJSON(needs) }}", gate)
        self.assertIn("run: node tools/research-ci-gate.js", gate)
        result = subprocess.run(
            ["node", "-e", "process.stdout.write(JSON.stringify(require('./tools/research-ci-gate').REQUIRED_JOBS))"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout), needed_jobs)

    def test_workflow_triggers_for_every_change_without_path_filters(self) -> None:
        triggers = self.workflow.split("\npermissions:", 1)[0]
        self.assertNotRegex(triggers, r"(?m)^\s+paths(?:-ignore)?:")
        self.assertIn("  pull_request:\n", triggers)
        self.assertIn("  push:\n", triggers)

    def test_workflow_is_read_only_and_does_not_persist_checkout_credentials(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertEqual(self.workflow.count("uses: actions/checkout@v7"), 9)
        self.assertEqual(self.workflow.count("persist-credentials: false"), 9)
        self.assertEqual(self.workflow.count("uses: actions/setup-python@v7"), 6)
        self.assertEqual(self.workflow.count("uses: actions/setup-node@v7"), 5)
        for forbidden in (
            "permissions:\n  contents: write",
            "pull_request_target:",
            "Start-Process",
            "server.py",
            "workflow_run:",
            "continue-on-error:",
        ):
            self.assertNotIn(forbidden, self.workflow)

    def test_python_jobs_install_the_canonical_package_without_path_injection(self) -> None:
        repository_step_pattern = (
            r"(?ms)^      - name: Verify repository-only signed handoff contracts\n"
            r".*?(?=^      - name:|^  [a-z][a-z0-9-]*:|\Z)"
        )
        repository_steps = re.findall(repository_step_pattern, self.workflow)
        self.assertEqual(len(repository_steps), 1)
        repository_step = repository_steps[0]
        # Only repository-only tests may load explicitly unshipped source modules.
        # Installed-package, MVP and reference jobs retain the no-injection rule.
        self.assertNotIn("PYTHONPATH", re.sub(repository_step_pattern, "", self.workflow))
        self.assertIn(
            '$env:PYTHONPATH = (Join-Path $PWD "src") + [IO.Path]::PathSeparator '
            '+ (Join-Path $PWD "outputs/python_quant_bot")',
            repository_step,
        )
        self.assertIn(
            'python -B -m unittest discover -s tests/repository_only -p "test_*.py" -v',
            repository_step,
        )
        self.assertIn('if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }', repository_step)
        self.assertNotIn("GITHUB_ENV", repository_step)
        self.assertNotIn("pip install", repository_step)
        self.assertEqual(
            self.workflow.count(
                "python -m pip install --requirement requirements.research.lock"
            ),
            5,
        )
        self.assertEqual(
            self.workflow.count("python -m pip install --no-deps --editable ."),
            4,
        )
        self.assertEqual(
            self.workflow.count("python -m pip install --no-deps ."),
            0,
        )
        self.assertEqual(self.workflow.count("python -m pip check"), 5)
        self.assertIn("python -B tools/generate_product_capabilities.py --check", self.workflow)

    def test_mvp_job_discovers_all_new_root_behavior_tests(self) -> None:
        mvp_job = self.jobs.split("  mvp-contracts:\n", 1)[1].split(
            "  electron-capability-contract:\n", 1,
        )[0]
        self.assertIn('python -B -m unittest discover -s tests -p "test_*.py" -v', mvp_job)
        self.assertNotIn("working-directory: outputs", mvp_job)

    def test_python_contract_job_runs_the_complete_pr_fa_suite(self) -> None:
        python_job = self.jobs.split(
            "  python-contracts:\n",
            1,
        )[1].split("  deterministic-references:\n", 1)[0]
        expected_modules = (
            "tests.test_exchange_terminal_layer_dependency_audit_v2",
            "tests.test_research_only_architecture",
            "tests.test_domain_contracts_fail_closed_v1",
            "tests.test_legacy_cli_boundary",
            "tests.test_quant_bot_backtest",
            "tests.test_quant_bot_protective_exit_contract_v1",
            "tests.test_reproducible_experiment_manifest_v1",
            "tests.test_backtest_reproducibility_builder_v1",
            "tests.test_research_dependency_lock_v1",
            "tests.test_research_ci_workflow_v1",
            "tests.test_canonical_product_capability_source_v1",
            "tests.test_canonical_cli_entrypoint_v1",
            "tests.test_frozen_evaluation_protocol_v1",
            "tests.test_canonical_research_core_source_v1",
            "tests.test_canonical_research_config_source_v1",
            "tests.test_canonical_research_data_source_v1",
            "tests.test_canonical_research_models_source_v1",
            "tests.test_canonical_research_strategy_base_hardening_v1",
            "tests.test_canonical_research_backtest_source_v1",
            "tests.test_canonical_research_execution_source_v1",
            "tests.test_canonical_research_risk_source_v1",
            "tests.test_package_metadata_v1",
            "tests.test_research_management_boundary",
            "tests.test_canonical_http_contract_source_v1",
            "tests.test_archived_execution_http_route_guard_v1",
            "tests.test_archived_paper_runtime_facade_v1",
            "tests.test_archived_paper_persistence_source_v1",
            "tests.test_stock_candle_market_schedule_gate_v1",
            "tests.test_stock_candle_completion_gate_v1",
            "tests.test_stock_candle_temporal_conformance_v1",
            "tests.test_stock_data_quality_boundary_v2",
        )
        for module in expected_modules:
            with self.subTest(module=module):
                self.assertEqual(python_job.count(module), 1)
        self.assertIn('HAKIMI_RUNTIME_READ_ONLY: "1"', python_job)
        self.assertIn('HAKIMI_SKIP_LOCAL_AI_ENV: "1"', python_job)

    def test_current_reference_job_uses_current_resources_and_history_is_separate(self) -> None:
        self.assertIn(
            "python -B examples/deterministic_experiment/verify.py",
            self.workflow,
        )
        self.assertIn(
            "python -B -m unittest tests.test_frozen_evaluation_protocol_v1",
            self.workflow,
        )
        for future_command in (
            "frozen-benchmark",
            "strategy-family-benchmark",
            "strategy-robustness-benchmark",
            "strategy-statistical-correction-benchmark",
            "strategy-research-dossier",
        ):
            self.assertNotIn(future_command, self.workflow)
        historical = self.jobs.split("  legacy-reference-replay:\n", 1)[1].split("  mvp-contracts:\n", 1)[0]
        self.assertIn("ref: 4fb6d191b282ea9a0d7136f4b94a9e9d49642178", historical)
        self.assertIn("tools/run_legacy_reference_checks.py", historical)
        harness = (REPO_ROOT / "tools/run_legacy_reference_checks.py").read_text(encoding="utf-8")
        for historical_command in ("frozen-benchmark", "strategy-family-benchmark", "strategy-robustness-benchmark", "strategy-statistical-correction-benchmark", "strategy-research-dossier"):
            self.assertIn(historical_command, harness)
        self.assertIn('"current_core_equivalence": False', harness)

    def test_node_jobs_use_only_contracts_available_at_pr_c(self) -> None:
        self.assertIn(
            "node outputs/hakimi_trade_electron/backend-runtime-contract.test.js",
            self.workflow,
        )
        self.assertIn(
            "node outputs/python_quant_bot/exchange_terminal/static/chart_controller.test.js",
            self.workflow,
        )
        self.assertIn(
            "node outputs/python_quant_bot/exchange_terminal/static/evidence_presentation.test.js",
            self.workflow,
        )
        self.assertNotIn("research-capability-lock.test.js", self.workflow)
        self.assertNotIn("market_data_research_projection.test.js", self.workflow)
        self.assertIn("run: node tools/research-ci-gate.test.js", self.workflow)

    def test_package_smoke_runs_outside_the_checkout(self) -> None:
        package_job = self.jobs.split(
            "  package-install-smoke:\n",
            1,
        )[1]
        self.assertIn("run: python tools/verify_wheel.py", package_job)
        self.assertNotIn("--editable", package_job)
        self.assertTrue((REPO_ROOT / "tools" / "verify_wheel.py").is_file())
        self.assertIn("os: [windows-latest, ubuntu-latest]", package_job)
        self.assertIn("fail-fast: false", package_job)
        self.assertIn('uses: actions/upload-artifact@v7', package_job)
        self.assertIn('python tools/verify_wheel.py --public-bundle-dir "${{ runner.temp }}/research-release-bundle"', package_job)
        self.assertIn('path: ${{ runner.temp }}/research-release-bundle', package_job)
        self.assertIn('name: hakimi-research-${{ matrix.os }}-${{ github.sha }}-${{ github.run_attempt }}', package_job)
        self.assertIn('RESEARCH_REVIEWED_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}', package_job)
        self.assertIn('if-no-files-found: error', package_job)
        self.assertIn('overwrite: false', package_job)
        self.assertIn('include-hidden-files: false', package_job)
        self.assertNotIn('if: ${{ always() }}', package_job.split('  research-required:\n', 1)[0])

    def test_stacked_pull_requests_trigger_and_later_steps_collect_evidence(self) -> None:
        pull_request = self.workflow.split("  pull_request:\n", 1)[1].split(
            "  workflow_dispatch:",
            1,
        )[0]
        self.assertNotIn("branches:", pull_request)
        self.assertGreaterEqual(
            self.workflow.count("if: ${{ !cancelled() }}"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
