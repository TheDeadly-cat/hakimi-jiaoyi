from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Iterable

from exchange_terminal.services.validation_receipts import (
    build_controlled_input_manifest,
    build_toolchain_fingerprint,
    build_validation_action,
    canonical_hash,
    create_validation_receipt,
    load_validation_receipt,
    prune_receipts,
    receipt_path,
    result_from_process,
    utc_now,
    verify_validation_receipt,
    write_validation_receipt,
)


PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent
DEFAULT_RECEIPT_CACHE = WORKSPACE_ROOT / "work" / "validation_receipts" / "lean"
LEAN_VALIDATION_SCHEMA = "hakimi-lean-validation-v2"


@dataclass(frozen=True)
class Check:
    check_id: str
    command: tuple[str, ...]
    profiles: tuple[str, ...]
    purpose: str


SAFETY_TESTS = (
    "tests.test_000_runtime_isolation.RuntimeIsolationTests",
    "tests.test_config_safety.ConfigSafetyTests",
    "tests.test_runtime_build.RuntimeBuildTests",
    "tests.test_core_services.CoreServiceTests.test_runtime_risk_view_blocks_policy_pass_in_read_only_runtime",
    "tests.test_core_services.CoreServiceTests.test_runtime_risk_view_does_not_expose_historical_authority_as_effective_in_read_only",
    "tests.test_core_services.CoreServiceTests.test_live_mode_is_always_blocked",
    "tests.test_core_services.CoreServiceTests.test_read_only_get_contract_blocks_hidden_mutations",
)

MARKET_TESTS = (
    "tests.test_candle_contract.CandleContractTests",
    "tests.test_stock_quote_quality.StockQuoteQualityTests",
    "tests.test_stock_symbol_classification.StockSymbolClassificationTests",
    "tests.test_public_order_book.PublicOrderBookTests",
    "tests.test_small_capital_trial.SmallCapitalTrialPlanTests",
    "tests.test_platform_control_center.PlatformControlCenterProjectionTests",
    "tests.test_platform_roadmap.PlatformRoadmapTests",
    "tests.test_core_services.CoreServiceTests.test_market_data_truth_is_unknown_without_snapshot_and_does_not_fetch",
    "tests.test_core_services.CoreServiceTests.test_market_data_truth_reports_realtime_sources_and_completed_bar",
    "tests.test_core_services.CoreServiceTests.test_market_data_truth_blocks_quarantined_fallback",
    "tests.test_core_services.CoreServiceTests.test_market_data_truth_never_promotes_invalid_or_stale_timestamps",
)

RESEARCH_TESTS = (
    "tests.test_forward_artifact_io.ForwardArtifactIoTests",
    "tests.test_portfolio_forward_performance_runner_io.PortfolioForwardPerformanceRunnerIoTests",
    "tests.test_portfolio_active_research_source.PortfolioActiveResearchSourceTests",
    "tests.test_research_symbol_market.ResearchSymbolMarketTests",
    "tests.test_strategy_selection_alignment.StrategySelectionAlignmentTests",
    "tests.test_backtest_risk_control_surface.BacktestRiskControlSurfaceTests",
    "tests.test_backtest_return_quality.BacktestReturnQualityTests",
    "tests.test_portfolio_backtest_pack.PortfolioBacktestPackTests",
    "tests.test_execution_authority.ExecutionAuthorityTests",
    "tests.test_strategy_frozen_evaluation_replay.StrategyFrozenEvaluationReplayTests",
    "tests.test_portfolio_backtest_campaign.PortfolioBacktestCampaignTests.test_resealed_contract_with_authority_alias_is_blocked",
    "tests.test_portfolio_backtest_replay.PortfolioBacktestReplayTests.test_resealed_snapshot_with_authority_alias_is_blocked",
    "tests.test_portfolio_evidence_archive.PortfolioEvidenceArchiveTests.test_resealed_backup_status_with_authority_alias_is_blocked",
    "tests.test_prepared_research_result.PreparedResearchResultTests",
    "tests.test_strategy_research_currentness_facts.StrategyResearchCurrentnessFactsTests",
    "tests.test_configuration_projection.ConfigurationProjectionTests",
    "tests.test_market_anomaly_projection.MarketAnomalyProjectionTests",
    "tests.test_market_scanner_projection.MarketScannerProjectionTests",
    "tests.test_portfolio_backtest_pack_pointer.PortfolioBacktestPackPointerTests",
    "tests.test_immutable_artifact_bundle.ImmutableArtifactBundleTests",
    "tests.test_strict_json_artifact.StrictJsonArtifactTests",
    "tests.test_portfolio_forward_projection.PortfolioForwardProjectionTests",
    "tests.test_portfolio_forward_statistical_maturity.PortfolioForwardStatisticalMaturityTests",
    "tests.test_portfolio_forward_server_maturity.PortfolioForwardServerMaturityTests",
    "tests.test_portfolio_forward_statistical_audit.PortfolioForwardStatisticalAuditTests",
    "tests.test_portfolio_forward_single_look.PortfolioForwardSingleLookTests",
    "tests.test_portfolio_forward_watchdog.PortfolioForwardWatchdogTests",
    "tests.test_research_query_projection.ResearchQueryProjectionTests",
    "tests.test_research_panel_projection.ResearchPanelProjectionTests",
    "tests.test_strategy_backtest_projection.StrategyBacktestProjectionTests",
    "tests.test_strategy_compare_projection.StrategyCompareProjectionTests",
    "tests.test_bot_research_projection.BotResearchProjectionTests",
    "tests.test_strategy_analysis_projection.StrategyAnalysisProjectionTests",
    "tests.test_market_ai_projection.MarketAiProjectionTests",
    "tests.test_deepseek_projection.DeepseekProjectionTests",
    "tests.test_trading_agents_projection.TradingAgentsProjectionTests",
    "tests.test_strategy_doctor_projection.StrategyDoctorProjectionTests",
    "tests.test_strategy_lab_projection.StrategyLabProjectionTests",
    "tests.test_strategy_research_pointer.StrategyResearchPointerTests",
    "tests.test_strategy_hypothesis_preregistration.StrategyHypothesisPreregistrationTests",
    "tests.test_strategy_preregistered_failure_admission.StrategyPreregisteredFailureAdmissionTests",
    "tests.test_strategy_research_search_lineage.StrategyResearchSearchLineageTests",
    "tests.test_strategy_matrix_protocol.StrategyMatrixProtocolTests",
    "tests.test_strategy_post_selection_replay_summary.StrategyPostSelectionReplaySummaryTests",
    "tests.test_strategy_research_preregistration_cli.StrategyResearchPreregistrationCliTests",
    "tests.test_strategy_research_failure_conditions.StrategyResearchFailureConditionsTests",
    "tests.test_implementation_manifest.ImplementationManifestTests.test_source_path_policy_blocks_before_reading_an_untrusted_path",
    "tests.test_implementation_manifest.ImplementationManifestTests.test_malformed_runtime_manifest_fails_closed_without_throwing",
    "tests.test_implementation_manifest.ImplementationManifestTests.test_entrypoint_verification_rebuilds_closure_and_blocks_resealed_omission",
    "tests.test_strategy_war_room_projection.StrategyWarRoomProjectionTests",
    "tests.test_portfolio_shadow.PortfolioShadowTests.test_latest_valid_observation_receipt_is_audited_sealed_and_status_bound",
    "tests.test_portfolio_shadow.PortfolioShadowTests.test_missing_or_invalid_risk_snapshot_never_becomes_ready",
    "tests.test_portfolio_shadow.PortfolioShadowTests.test_record_and_audit_require_exact_decision_projection",
    "tests.test_portfolio_shadow.PortfolioShadowTests.test_latest_observation_change_seals_insufficient_evidence_without_claiming_no_change",
    "tests.test_portfolio_shadow.PortfolioShadowTests.test_latest_two_observations_produce_audited_descriptive_change_and_tamper_blocks",
    "tests.test_portfolio_forward_scheduler.PortfolioForwardSchedulerTests.test_dashboard_keeps_verified_latest_receipt_when_current_run_has_no_new_bar",
    "tests.test_portfolio_forward_scheduler.PortfolioForwardSchedulerTests.test_dashboard_blocks_nonempty_receipt_tampering_but_tolerates_legacy_absence",
    "tests.test_portfolio_forward_scheduler.PortfolioForwardSchedulerTests.test_dashboard_blocks_nonempty_observation_change_tampering",
    "tests.test_portfolio_forward_scheduler.PortfolioForwardSchedulerTests.test_observer_job_receipt_classifies_only_proven_outcomes",
    "tests.test_portfolio_forward_scheduler.PortfolioForwardSchedulerTests.test_resealed_observer_job_chain_tampering_blocks_load",
    "tests.test_strategy_signals.StrategySignalTests.test_falsified_strategy_ids_remain_replayable_but_cannot_start_new_research",
    "tests.test_strategy_research.StrategyResearchTests.test_validation_gate_fails_closed_on_nonfinite_metrics_and_truthy_strings",
    "tests.test_strategy_research.StrategyResearchTests.test_risk_adjusted_test_gate_rejects_missing_risk_metrics",
    "tests.test_strategy_research.StrategyResearchTests.test_cumulative_300_trials_flips_a_marginal_three_trial_candidate",
    "tests.test_strategy_benchmark.StrategyBenchmarkTests.test_selection_gate_rejects_pseudo_numeric_or_missing_trade_evidence",
    "tests.test_strategy_benchmark.StrategyBenchmarkTests.test_confirmation_rejects_pseudo_numeric_trade_count",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_cell_evidence_v2_seals_nested_robustness_without_changing_legacy_hash",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema8_canonicalizes_high_precision_costs_without_weakening_exact_binding",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema8_negative_cost_drawdowns_block_selection_and_test_evidence",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema8_test_cost_evidence_rejects_resealed_severe_return",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema9_fixed_slice_evidence_rejects_coherently_resealed_topology",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema10_replays_fold_results_and_rejects_coherent_999_reseal",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema10_selection_runner_uses_pure_replay_not_server_backtest",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema10_formal_rebuilds_calendar_split_before_selecting_replay_rows",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema10_development_rebuilds_train_boundary_before_selection_replay",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema9_cell_hash_v4_default_remains_bound_to_schema9",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_current_writer_defaults_to_schema13_v2_and_schema12_remains_v1",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_verifier_recomputes_development_rankings_semantically",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema13_mechanism_block_never_runs_test_or_loads_confirmation",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_schema14_formal_block_uses_live_cumulative_lineage_and_no_protected_stage",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_falsified_strategy_cannot_create_a_new_research_spec",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_blind_once_without_registration_blocks_before_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_development_run_requires_explicit_strategies_before_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_development_run_requires_explicit_generation_before_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_development_run_requires_hypothesis_before_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_development_run_never_evaluates_test_or_loads_holdout_symbol",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_formal_blocked_alignment_never_completes_or_publishes_report",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_running_prepared_result_recovers_without_research_rerun",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_completed_prepared_result_restores_missing_final_without_rerun",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_pointer_publication_failure_is_not_reported_as_success",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_runner_rejects_unbound_published_pointer_receipt",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_formal_nested_output_blocks_before_store_claim_or_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_development_nested_output_blocks_before_hypothesis_build_or_data_load",
    "tests.test_strategy_research_runner.StrategyResearchRunnerTests.test_recovery_failure_response_does_not_expose_local_paths",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_falsified_strategy_cannot_create_a_new_matrix_spec",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_zero_forward_candidate_formal_report_passes_report_level_verification",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_running_prepared_result_recovers_without_research_rerun",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_completed_prepared_result_recovers_missing_final_without_research_rerun",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_resealed_semantic_tamper_in_prepared_report_blocks_before_research_rerun",
    "tests.test_strategy_matrix_runner.StrategyMatrixRunnerTests.test_final_publish_failure_is_non_success_after_registry_completion",
    "tests.test_internal_backtest_readiness.InternalBacktestReadinessTests.test_runtime_requires_read_only_and_hard_live_block",
    "tests.test_internal_backtest_readiness.InternalBacktestReadinessTests.test_claimed_pass_with_failed_or_unstructured_result_is_recomputed_as_block",
)


CHECKS = (
    Check(
        "python-safety-contracts",
        ("{python}", "-m", "unittest", "-q", *SAFETY_TESTS),
        ("safety", "core"),
        "Permanent live lock, read-only authority, isolated runtime, and build fingerprint.",
    ),
    Check(
        "python-market-contracts",
        ("{python}", "-m", "unittest", "-q", *MARKET_TESTS),
        ("market", "core"),
        "Candle/quote truth, fixed-bps public order-book depth, and execution-free small-capital planning.",
    ),
    Check(
        "python-research-guards",
        ("{python}", "-m", "unittest", "-q", *RESEARCH_TESTS),
        ("research", "core"),
        "Forward-observation receipts, versioned natural-forward maturity, frozen strategy-report pointers, falsified-strategy retirement, preregistered strategy hypotheses, explicit research inputs, and readiness recomputation.",
    ),
    Check(
        "python-critical-syntax",
        (
            "{python}",
            "-m",
            "py_compile",
            "exchange_terminal/server.py",
            "exchange_terminal/config.py",
            "exchange_terminal/services/risk_service.py",
            "exchange_terminal/services/paper_executor.py",
            "exchange_terminal/services/market_data_service.py",
            "exchange_terminal/services/backtest_return_quality.py",
            "exchange_terminal/services/backtest_risk_control_surface.py",
            "exchange_terminal/services/configuration_projection.py",
            "exchange_terminal/services/immutable_json_artifact.py",
            "exchange_terminal/services/immutable_artifact_bundle.py",
            "exchange_terminal/services/strict_json_artifact.py",
            "exchange_terminal/services/market_anomaly_projection.py",
            "exchange_terminal/services/market_scanner_projection.py",
            "exchange_terminal/services/platform_control_center.py",
            "exchange_terminal/services/platform_roadmap.py",
            "exchange_terminal/services/execution_authority.py",
            "exchange_terminal/services/forward_artifact_io.py",
            "exchange_terminal/services/portfolio_backtest_campaign.py",
            "exchange_terminal/services/portfolio_backtest_pack.py",
            "exchange_terminal/services/portfolio_backtest_pack_pointer.py",
            "exchange_terminal/services/portfolio_backtest_replay.py",
            "exchange_terminal/services/portfolio_backtest_replay_driver.py",
            "exchange_terminal/services/portfolio_active_research_source.py",
            "exchange_terminal/services/portfolio_evidence_archive.py",
            "exchange_terminal/services/portfolio_forward.py",
            "exchange_terminal/services/portfolio_forward_local_source_anchor.py",
            "exchange_terminal/services/portfolio_forward_local_source_receipt.py",
            "exchange_terminal/services/portfolio_forward_performance.py",
            "exchange_terminal/services/portfolio_forward_projection.py",
            "exchange_terminal/services/portfolio_forward_scheduler.py",
            "exchange_terminal/services/portfolio_forward_statistical_audit.py",
            "exchange_terminal/services/portfolio_forward_statistical_maturity.py",
            "exchange_terminal/services/portfolio_forward_watchdog.py",
            "exchange_terminal/services/portfolio_shadow.py",
            "exchange_terminal/services/portfolio_statistical_audit.py",
            "exchange_terminal/services/public_order_book.py",
            "exchange_terminal/services/research_query_projection.py",
            "exchange_terminal/services/research_panel_projection.py",
            "exchange_terminal/services/small_capital_trial.py",
            "exchange_terminal/services/strategy_signals.py",
            "exchange_terminal/services/strategy_risk_profiles.py",
            "exchange_terminal/services/strategy_benchmark.py",
            "exchange_terminal/services/strategy_validation.py",
            "exchange_terminal/services/implementation_manifest.py",
            "exchange_terminal/services/strategy_cost_stress.py",
            "exchange_terminal/services/strategy_chronological_slice.py",
            "exchange_terminal/services/strategy_fold_replay.py",
            "exchange_terminal/services/strategy_frozen_evaluation_replay.py",
            "exchange_terminal/services/research_symbol_market.py",
            "exchange_terminal/services/strategy_selection_alignment.py",
            "exchange_terminal/services/strategy_selection_replay.py",
            "exchange_terminal/services/strategy_research_evidence.py",
            "exchange_terminal/services/strategy_research_currentness_facts.py",
            "exchange_terminal/services/strategy_research_failure_conditions.py",
            "exchange_terminal/services/strategy_research_pointer.py",
            "exchange_terminal/services/prepared_research_result.py",
            "exchange_terminal/services/strategy_matrix_evidence.py",
            "exchange_terminal/services/strategy_matrix_protocol.py",
            "exchange_terminal/services/strategy_hypothesis_preregistration.py",
            "exchange_terminal/services/strategy_preregistered_failure_admission.py",
            "exchange_terminal/services/strategy_research_search_lineage.py",
            "exchange_terminal/services/strategy_post_selection_replay_summary.py",
            "exchange_terminal/services/strategy_research_protocol_artifact.py",
            "exchange_terminal/services/strategy_backtest_projection.py",
            "exchange_terminal/services/strategy_compare_projection.py",
            "exchange_terminal/services/bot_research_projection.py",
            "exchange_terminal/services/strategy_analysis_projection.py",
            "exchange_terminal/services/market_ai_projection.py",
            "exchange_terminal/services/deepseek_projection.py",
            "exchange_terminal/services/trading_agents_projection.py",
            "exchange_terminal/services/strategy_doctor_projection.py",
            "exchange_terminal/services/strategy_lab_projection.py",
            "exchange_terminal/services/strategy_war_room_projection.py",
            "run_internal_backtest.py",
            "run_internal_execution_rehearsal.py",
            "run_internal_portfolio_statistical_audit.py",
            "run_internal_strategy_research.py",
            "run_internal_strategy_matrix.py",
            "run_preregister_strategy_research.py",
            "run_internal_backtest_readiness.py",
            "run_portfolio_evidence_archive.py",
            "run_portfolio_forward_performance.py",
            "run_portfolio_forward_scheduler.py",
            "run_portfolio_forward_watchdog.py",
            "run_portfolio_shadow_observation.py",
        ),
        ("safety", "market", "research", "core"),
        "Syntax-check the main runtime and the risk/data/research boundaries.",
    ),
    Check(
        "frontend-market-guard",
        (
            "{node}",
            "--check",
            "exchange_terminal/static/app.js",
        ),
        ("frontend", "market", "core"),
        "Syntax-check the market workstation UI.",
    ),
    Check(
        "frontend-stock-quote-guard-syntax",
        (
            "{node}",
            "--check",
            "exchange_terminal/static/stock_quote_guard.js",
        ),
        ("frontend", "market", "core"),
        "Syntax-check the stock quote isolation guard.",
    ),
    Check(
        "frontend-chart-refresh-coordinator",
        (
            "{node}",
            "exchange_terminal/static/chart_controller.test.js",
        ),
        ("frontend", "market", "core"),
        "Verify per-key refresh singleflight, cooldown, manual bypass, and failure backoff.",
    ),
    Check(
        "frontend-stock-quote-guard-tests",
        (
            "{node}",
            "exchange_terminal/static/stock_quote_guard.test.js",
        ),
        ("frontend", "market", "core"),
        "Run the small stock quote guard regression only.",
    ),
    Check(
        "frontend-evidence-presentation",
        (
            "{node}",
            "exchange_terminal/static/evidence_presentation.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify neutral evidence wording, frozen return/strategy evidence fail-closed mapping, and static source boundaries.",
    ),
)


PROFILES = ("safety", "market", "research", "frontend", "core")


def build_plan(profile: str) -> list[Check]:
    requested = str(profile or "").strip().lower()
    if requested not in PROFILES:
        raise ValueError(f"unknown validation profile: {profile}")
    return [check for check in CHECKS if requested in check.profiles]


def isolated_environment(runtime_dir: Path) -> dict[str, str]:
    runtime = runtime_dir.resolve()
    env: dict[str, str] = {}
    for key in ("COMSPEC", "SYSTEMROOT", "WINDIR"):
        value = str(os.environ.get(key) or "").strip()
        if value:
            env[key] = value
    executable_dirs: list[str] = []
    for executable in (
        sys.executable,
        shutil.which("node") or "",
        shutil.which("npm.cmd") or shutil.which("npm") or "",
    ):
        if executable:
            parent = str(Path(executable).resolve().parent)
            if parent.casefold() not in {item.casefold() for item in executable_dirs}:
                executable_dirs.append(parent)
    system_root = str(env.get("SYSTEMROOT") or env.get("WINDIR") or "").strip()
    if system_root:
        system32 = str((Path(system_root) / "System32").resolve())
        if system32.casefold() not in {item.casefold() for item in executable_dirs}:
            executable_dirs.append(system32)
    env.update({
        "APPDATA": str((runtime / "appdata").resolve()),
        "LOCALAPPDATA": str((runtime / "localappdata").resolve()),
        "PATH": os.pathsep.join(executable_dirs),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": str(runtime),
        "TMP": str(runtime),
        "HAKIMI_TEST_MODE": "1",
        "HAKIMI_SKIP_LOCAL_AI_ENV": "1",
        "HAKIMI_RUNTIME_READ_ONLY": "1",
        "HAKIMI_RUNTIME_DIR": str(runtime),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PYTHONPYCACHEPREFIX": str((runtime / "pycache").resolve()),
    })
    return env


def resolve_command(command: Iterable[str]) -> list[str]:
    node = shutil.which("node") or ""
    resolved: list[str] = []
    for part in command:
        if part == "{python}":
            resolved.append(sys.executable)
        elif part == "{node}":
            if not node:
                raise RuntimeError("node executable is required for this validation profile")
            resolved.append(node)
        else:
            resolved.append(part)
    return resolved


def describe_plan(profile: str) -> dict[str, object]:
    plan = build_plan(profile)
    return {
        "schema_version": LEAN_VALIDATION_SCHEMA,
        "profile": profile,
        "check_count": len(plan),
        "checks": [
            {
                "id": check.check_id,
                "purpose": check.purpose,
                "command": list(check.command),
            }
            for check in plan
        ],
        "full_regression_included": False,
        "receipt_reuse_supported": True,
        "live_order_allowed": False,
    }


def _result_contract(check: Check) -> str:
    command = tuple(str(part) for part in check.command)
    return "unittest" if "-m" in command and "unittest" in command else "exit-zero"


def _receipt_action(
    check: Check,
    command: list[str],
    *,
    manifest: dict[str, object],
    toolchain: dict[str, object],
) -> dict[str, object]:
    contract = _result_contract(check)
    return build_validation_action(
        check_id=check.check_id,
        argv=command,
        cwd=PROJECT_ROOT,
        manifest=manifest,
        toolchain=toolchain,
        result_contract=contract,
        minimum_tests=1 if contract == "unittest" else 0,
        namespace="hakimi-lean-validation",
        full_regression_included=False,
    )


def run(
    profile: str,
    *,
    dry_run: bool = False,
    receipt_cache: Path | None = None,
    fresh: bool = False,
) -> dict[str, object]:
    started = time.perf_counter()
    plan = build_plan(profile)
    results: list[dict[str, object]] = []
    node = shutil.which("node") or ""
    npm = shutil.which("npm.cmd") or shutil.which("npm") or ""
    receipts_enabled = receipt_cache is not None
    manifest = build_controlled_input_manifest(PROJECT_ROOT) if receipts_enabled else {}
    toolchain = build_toolchain_fingerprint(
        node_executable=node,
        npm_executable=npm,
    ) if receipts_enabled else {}
    plan_identity: list[dict[str, object]] = []
    executed_count = 0
    reused_count = 0
    with tempfile.TemporaryDirectory(prefix="hakimi-lean-validation-") as temp_dir:
        runtime_dir = Path(temp_dir)
        env = isolated_environment(runtime_dir)
        for check in plan:
            command = resolve_command(check.command)
            action = _receipt_action(
                check,
                command,
                manifest=manifest,
                toolchain=toolchain,
            ) if receipts_enabled else {}
            validation_key = str(dict(action.get("digest", {})).get("sha256") or "")
            cached_path = receipt_path(receipt_cache, action) if receipt_cache is not None else None
            cached_receipt: dict[str, object] | None = None
            cached_verification: dict[str, object] = {"status": "MISS", "blockers": []}
            if cached_path is not None and cached_path.is_file() and not fresh:
                try:
                    cached_receipt = load_validation_receipt(cached_path)
                    cached_verification = verify_validation_receipt(
                        cached_receipt,
                        expected_action=action,
                    )
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    cached_verification = {
                        "status": "BLOCK",
                        "blockers": [f"validation_receipt_unreadable:{type(exc).__name__}"],
                    }
            plan_identity.append({
                "id": check.check_id,
                "validation_key": validation_key,
            })
            row: dict[str, object] = {
                "id": check.check_id,
                "purpose": check.purpose,
                "command": command,
                "status": "DRY_RUN" if dry_run else "RUNNING",
                "execution": "WOULD_REUSE" if dry_run and cached_verification.get("status") == "PASS" else "WOULD_RUN" if dry_run else "PENDING",
                "validation_key": validation_key,
            }
            if cached_path is not None:
                row["receipt_path"] = str(cached_path)
            if dry_run:
                results.append(row)
                continue
            if cached_receipt is not None and cached_verification.get("status") == "PASS":
                row.update({
                    "status": "PASS",
                    "execution": "REUSED",
                    "exit_code": 0,
                    "duration_sec": 0.0,
                    "receipt_hash": str(cached_verification.get("receipt_hash") or ""),
                    "tests_run": int(cached_verification.get("tests_run") or 0),
                })
                reused_count += 1
                results.append(row)
                continue
            check_started_at = utc_now()
            check_started = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
            )
            if completed.stdout:
                print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
            if completed.stderr:
                print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n", file=sys.stderr)
            duration = round(time.perf_counter() - check_started, 3)
            row["exit_code"] = int(completed.returncode)
            row["duration_sec"] = duration
            row["status"] = "PASS" if completed.returncode == 0 else "FAIL"
            row["execution"] = "EXECUTED"
            executed_count += 1
            if receipts_enabled:
                process_result = result_from_process(
                    action=action,
                    exit_code=int(completed.returncode),
                    stdout=str(completed.stdout or ""),
                    stderr=str(completed.stderr or ""),
                    duration_sec=duration,
                )
                row["tests_run"] = int(process_result.get("tests_run") or 0)
                if completed.returncode == 0:
                    finished_at = utc_now()
                    receipt = create_validation_receipt(
                        action=action,
                        result=process_result,
                        started_at=check_started_at,
                        finished_at=finished_at,
                    )
                    verification = verify_validation_receipt(receipt, expected_action=action)
                    if verification.get("status") == "PASS" and cached_path is not None:
                        write_validation_receipt(cached_path, receipt)
                        prune_receipts(receipt_cache, check.check_id)
                        row["receipt_hash"] = str(verification.get("receipt_hash") or "")
                    else:
                        row["status"] = "FAIL"
                        row["receipt_blockers"] = list(verification.get("blockers") or [])
            results.append(row)
            if row.get("status") != "PASS":
                break
    status = "DRY_RUN" if dry_run else "PASS" if len(results) == len(plan) and all(
        row.get("status") == "PASS" for row in results
    ) else "FAIL"
    receipt_hashes = [
        {"id": row.get("id"), "receipt_hash": row.get("receipt_hash")}
        for row in results
        if row.get("receipt_hash")
    ]
    return {
        "schema_version": LEAN_VALIDATION_SCHEMA,
        "profile": profile,
        "status": status,
        "check_count": len(plan),
        "planned_check_count": len(plan),
        "completed_check_count": 0 if dry_run else len(results),
        "executed_check_count": executed_count,
        "reused_check_count": reused_count,
        "duration_sec": round(time.perf_counter() - started, 3),
        "results": results,
        "plan_hash": canonical_hash(plan_identity) if receipts_enabled else "",
        "receipt_set_hash": canonical_hash(receipt_hashes) if receipts_enabled and receipt_hashes else "",
        "receipt_cache": str(receipt_cache.resolve()) if receipt_cache is not None else "DISABLED",
        "scope": "TARGETED",
        "full_regression_included": False,
        "runtime_mutations_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a small, area-specific Hakimi validation profile instead of the full regression suite."
    )
    parser.add_argument("--profile", choices=PROFILES, default="core")
    parser.add_argument("--list", action="store_true", help="Print the selected plan without resolving executables.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve commands but do not execute them.")
    parser.add_argument("--fresh", action="store_true", help="Ignore matching PASS receipts and execute every selected check.")
    parser.add_argument("--no-receipts", action="store_true", help="Disable receipt lookup and creation for this run.")
    parser.add_argument("--receipt-cache", default=str(DEFAULT_RECEIPT_CACHE), help="Directory for content-addressed PASS receipts.")
    args = parser.parse_args()
    cache = None if args.no_receipts else Path(args.receipt_cache)
    payload = describe_plan(args.profile) if args.list else run(
        args.profile,
        dry_run=args.dry_run,
        receipt_cache=cache,
        fresh=args.fresh,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {None, "PASS", "DRY_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
