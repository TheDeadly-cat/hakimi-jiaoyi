from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from exchange_terminal import server
from exchange_terminal import config as config_module
from exchange_terminal import utils as utils_module
from exchange_terminal.market_data import futu_quotes as futu_quotes_module
from exchange_terminal.market_data import candle_contract as candle_contract_module
from exchange_terminal.market_data import provider_health as provider_health_module
from exchange_terminal.market_data import stock_candles as stock_candles_module
from exchange_terminal.market_data import stock_candle_quality as stock_candle_quality_module
from exchange_terminal.market_data import stock_candles_io as stock_candles_io_module
from exchange_terminal.market_data import stocks as stocks_module
from exchange_terminal.services import backtest_engine as backtest_engine_module
from exchange_terminal.services import corporate_action_ledger as corporate_action_ledger_module
from exchange_terminal.services import market_calendar as market_calendar_module
from exchange_terminal.services import market_data_revision_ledger as market_data_revision_ledger_module
from exchange_terminal.services import market_regime as market_regime_module
from exchange_terminal.services import portfolio_backtest as portfolio_backtest_module
from exchange_terminal.services import portfolio_admission as portfolio_admission_module
from exchange_terminal.services import portfolio_candidate as portfolio_candidate_module
from exchange_terminal.services import portfolio_experiment as portfolio_experiment_module
from exchange_terminal.services import portfolio_forward as portfolio_forward_module
from exchange_terminal.services import portfolio_forward_scheduler as portfolio_forward_scheduler_module
from exchange_terminal.services import portfolio_forward_performance as portfolio_forward_performance_module
from exchange_terminal.services import portfolio_execution_rehearsal as portfolio_execution_rehearsal_module
from exchange_terminal.services import portfolio_paper_account as portfolio_paper_account_module
from exchange_terminal.services import portfolio_paper_activation as portfolio_paper_activation_module
from exchange_terminal.services import portfolio_risk as portfolio_risk_module
from exchange_terminal.services import portfolio_robustness as portfolio_robustness_module
from exchange_terminal.services import portfolio_shadow as portfolio_shadow_module
from exchange_terminal.services import portfolio_shadow_risk as portfolio_shadow_risk_module
from exchange_terminal.services import portfolio_statistical_audit as portfolio_statistical_audit_module
from exchange_terminal.services import portfolio_backtest_pack as portfolio_backtest_pack_module
from exchange_terminal.services import portfolio_evidence_bundle as portfolio_evidence_bundle_module
from exchange_terminal.services import portfolio_universe as portfolio_universe_module
from exchange_terminal.services import provider_governance as provider_governance_module
from exchange_terminal.services import research_exposure as research_exposure_module
from exchange_terminal.services import security_lifecycle as security_lifecycle_module
from exchange_terminal.services import trusted_clock as trusted_clock_module
from exchange_terminal.services import event_lineage as event_lineage_module
from exchange_terminal.services import event_replay as event_replay_module
from exchange_terminal.services import guardian_service as guardian_service_module
from exchange_terminal.services import http_contract as http_contract_module
from exchange_terminal.services import market_data_service as market_data_service_module
from exchange_terminal.services import mutation_journal as mutation_journal_module
from exchange_terminal.services import paper_account as paper_account_module
from exchange_terminal.services import paper_executor as paper_executor_module
from exchange_terminal.services import paper_ledger as paper_ledger_module
from exchange_terminal.services import paper_order_contract as paper_order_contract_module
from exchange_terminal.services import paper_strategy_clock as paper_strategy_clock_module
from exchange_terminal.services import risk_service as risk_service_module
from exchange_terminal.services import strategy_benchmark as strategy_benchmark_module
from exchange_terminal.services.portfolio_backtest import (
    PORTFOLIO_BACKTEST_SCHEMA_VERSION,
    audit_relative_strength_causality,
    prepare_attested_portfolio_dataset,
    run_causal_relative_strength_backtest,
    slice_portfolio_payload_through_date,
)
from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.portfolio_execution_rehearsal import run_research_report_execution_rehearsal
from exchange_terminal.services.portfolio_candidate import build_frozen_portfolio_candidate
from exchange_terminal.services.portfolio_experiment import PortfolioExperimentRegistry
from exchange_terminal.services.portfolio_admission import (
    build_internal_backtest_admission,
    build_research_universe_contract,
)
from exchange_terminal.services.research_exposure import audit_portfolio_temporal_exposure
from exchange_terminal.services.strategy_benchmark import buy_and_hold_report
from exchange_terminal.services.trusted_clock import attest_utc_clock
from exchange_terminal.services.provider_governance import (
    build_unassessed_provider_governance_contract,
    required_provider_ids_from_evidence,
)


DEFAULT_BENCHMARK = "SPY"
DEFAULT_TRADABLES = [
    "AAPL", "NVDA", "MSFT", "MU", "WDC", "AMZN", "GOOGL",
    "META", "AVGO", "TSLA", "AMD", "ASML", "TSM",
]
DEFAULT_CLUSTERS = {
    "AAPL": "MEGA_PLATFORM",
    "MSFT": "MEGA_PLATFORM",
    "AMZN": "MEGA_PLATFORM",
    "GOOGL": "MEGA_PLATFORM",
    "META": "MEGA_PLATFORM",
    "NVDA": "SEMI_DESIGN",
    "AMD": "SEMI_DESIGN",
    "AVGO": "SEMI_DESIGN",
    "MU": "MEMORY_STORAGE",
    "WDC": "MEMORY_STORAGE",
    "ASML": "SEMI_SUPPLY",
    "TSM": "SEMI_SUPPLY",
    "TSLA": "EV",
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def finite_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_research_protocol(
    *,
    benchmark: str,
    tradables: list[str],
    limit: int,
    cutoff: str,
) -> dict[str, Any]:
    protocol = {
        "schema_version": "portfolio-research-protocol-v1",
        "research_generation": "PORTFOLIO_G46_RUNTIME_AUTHORIZATION_SEMANTICS",
        "hypothesis": (
            "A weekly, long-or-cash relative-strength portfolio with volatility, cluster, drawdown, liquidity, "
            "gap, fee and slippage controls can reproduce the frozen G45 development behavior after policy-level risk acceptance "
            "is separated from effective runtime paper authority, public pretrade results fail closed in read-only mode, and an "
            "armed automated strategy is bound to its exact authorized pipeline run, without changing the strategy, universe, "
            "data window, cost model, risk budget or promotion thresholds."
        ),
        "prior_generation_report": "portfolio_research_g45_isolated_runtime_task_attestation.json",
        "prior_generation_hash": "b203610373093f63656b3e8f041e36b6c3a0307c6a3f0d00f9dcb14c60663769",
        "prior_generation_file_sha256": "473b7b581e24631e1cfcdc93422f2146816deffaea47aa52618fa53b6415f53b",
        "prior_generation_experiment_id": "pexp-1785749792112-f92be5033dfc",
        "prior_generation_protocol_hash": "6abd51bcb8bb24d8e03a83b5849d8b6462584a0d31d10181f3c713b947ac3848",
        "prior_generation_implementation_fingerprint": "af0dafbcd86ab6b76f8acac1091d220cc42d55bdbdb14fb153890cc5b5763cff",
        "prior_generation_completion_receipt_hash": "e0773f8fe1a637542a07336b5396a1ef8cb7c550979e3729b55da0ecf03d70bd",
        "prior_generation_mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "prior_generation_internal_admission": "INTERNAL_BACKTEST_READY",
        "prior_generation_candidate_created": True,
        "prior_generation_execution_rehearsal_status": "PASS",
        "prior_generation_execution_rehearsal_hash": "795812f8c6d4f11eecfc4395c939a5b4cca6fb0538ff5354222ebe35e01e1020",
        "prior_generation_failure_reason": "RUNTIME_AUTHORIZATION_SEMANTICS_MISLEADING",
        "prior_generation_parameter_selection_allowed": False,
        "prior_candidate_generation": "PORTFOLIO_G45_ISOLATED_RUNTIME_TASK_ATTESTATION",
        "prior_candidate_is_immediate_prior_generation": True,
        "prior_candidate_hash": "0faa06988aca5396e3812136ebfa75f300e6fc9e9c2b0bc998cad82cf5a6a237",
        "prior_candidate_implementation_fingerprint": "af0dafbcd86ab6b76f8acac1091d220cc42d55bdbdb14fb153890cc5b5763cff",
        "prior_candidate_natural_observations": 0,
        "prior_candidate_forward_outcomes": 0,
        "prior_candidate_executed_rebalances": 0,
        "prior_candidate_neutral_capture_events": 1,
        "prior_candidate_missed_capture_count": 0,
        "prior_candidate_sample_migration_allowed": False,
        "prior_aborted_experiment_id": "pexp-1785726997066-27d564e8a8c5",
        "prior_aborted_experiment_protocol_hash": "8d8645cb52acc835be21543d29a5c44c7f4d685513384cde763879e064d24189",
        "prior_aborted_experiment_implementation_fingerprint": "f0aaca258e727c3e576b97e1f82914a97408768991b8dd8dfd9151b82370ee68",
        "prior_aborted_experiment_event_hash": "f08344f4add7252e36a3412bd826d45f425c3928f7ad808df8dd4eeca3b49364",
        "prior_aborted_experiment_reason": "G39_EVIDENCE_BUNDLE_REJECTED_NON_EMBEDDED_CROSS_SOURCE_SNAPSHOT",
        "prior_aborted_experiment_parameter_selection_allowed": False,
        "prior_operational_failure_report": "internal_portfolio_backtest_pack_g45_runtime_authorization_semantics_invalidated.json",
        "prior_operational_failure_status_hash": "b0fc73902aea51691f313b1a85e3eac68fe3528ccaf95bd98a3bdfdd1da2a67b",
        "prior_operational_failure_file_sha256": "0b14122d26c94ee139af99d87d5b305d13724483fdc893caf158944717650dc2",
        "prior_operational_failure_reason": "RISK_POLICY_PASS_WAS_PRESENTED_AS_EFFECTIVE_PAPER_EXECUTION_PERMISSION",
        "prior_candidate_retirement_report": "portfolio_candidate_retirement_0faa06988aca_1785751118169.json",
        "prior_candidate_retirement_file_sha256": "31f61c7ab1339e86715baea42c516b0846b061d032a5b88ecc3e92e4069888ff",
        "prior_candidate_retirement_hash": "4218553faeb58fe155d0a913a83c75fe3364b05f8a4bf64756be96c498dafe96",
        "prior_candidate_still_frozen_in_source_runtime": False,
        "prior_candidate_retired_before_implementation_change": True,
        "prior_statistical_audit_report": "portfolio_statistical_audit_g45_isolated_runtime_task_attestation_active_bound.json",
        "prior_statistical_audit_generation": "PORTFOLIO_G45_ISOLATED_RUNTIME_TASK_ATTESTATION",
        "prior_statistical_audit_hash": "f7bf2f001834eee71f2ffa75c2bf1bba98229368ef349de65efa490bd45a2ed4",
        "prior_statistical_audit_status": "BLOCK",
        "prior_internal_batch_report": "internal_portfolio_backtest_pack_g45_runtime_authorization_semantics_invalidated.json",
        "prior_internal_batch_generation": "PORTFOLIO_G45_ISOLATED_RUNTIME_TASK_ATTESTATION",
        "prior_internal_batch_hash": "b0fc73902aea51691f313b1a85e3eac68fe3528ccaf95bd98a3bdfdd1da2a67b",
        "prior_invalidated_internal_batch_file_sha256": "0b14122d26c94ee139af99d87d5b305d13724483fdc893caf158944717650dc2",
        "prior_internal_batch_failure_reason": "G45_RUNTIME_AUTHORIZATION_SEMANTICS_MISLEADING",
        "prior_execution_evidence_report": "portfolio_internal_execution_rehearsal_g45_isolated_runtime_task_attestation_active_bound.json",
        "prior_execution_evidence_hash": "795812f8c6d4f11eecfc4395c939a5b4cca6fb0538ff5354222ebe35e01e1020",
        "prior_execution_evidence_status": "PASS",
        "reference_g42_execution_evidence_report": "portfolio_internal_execution_rehearsal_g42_causal_point_in_time_universe_gaps.json",
        "reference_g42_execution_evidence_hash": "06ddeb5152b4d1df3b8bbddcd9287ca022ca25368c9c36c190188521c2116690",
        "reference_g42_execution_evidence_status": "PASS",
        "prior_robustness_report": "portfolio_robustness_g45_isolated_runtime_task_attestation.json",
        "prior_robustness_generation": "PORTFOLIO_G45_ISOLATED_RUNTIME_TASK_ATTESTATION",
        "prior_robustness_hash": "bd8d70201a8b2105075cc4ba5b0031974bdafcd34da924f5c0b767aa50db349b",
        "prior_robustness_status": "ROBUSTNESS_PASS",
        "prior_data_admission_report": "portfolio_data_admission_g45_isolated_runtime_task_attestation.json",
        "prior_data_admission_generation": "PORTFOLIO_G45_ISOLATED_RUNTIME_TASK_ATTESTATION",
        "prior_data_admission_hash": "9fed2f1b95044c9a2587dffa4abe5b62061e468cc5ba63cdbb78c9d367aa134c",
        "prior_data_admission_status": "READY_WITH_LIMITATIONS",
        "failed_prior_robustness_report": "portfolio_robustness_20260801_131734.json",
        "failed_prior_robustness_hash": "a1620f1b1e7559cb3a14065a8d66e67354b44cb6536f9bd64cebb34032807ed5",
        "prior_robustness_failure_reason": "ABLATION_UNIVERSE_CONTRACT_NOT_DERIVED_FROM_PARENT_SUBSET",
        "failed_cross_sectional_holdout_report": "portfolio_holdout_20260801_012712.json",
        "failed_cross_sectional_holdout_hash": "569afea12b1dca4113079883c3c913a0b87f4615441dcecd83d1ef648cbd20a5",
        "selection_policy": "PREREGISTERED_G45_RUNTIME_AUTHORIZATION_SEMANTICS_DEFECT_ONLY_STRATEGY_PARAMETERS_UNCHANGED_G46_REVALIDATION",
        "universe_selection_basis": "STATIC_USER_WATCHLIST_WITH_PRESENT_DAY_KNOWLEDGE",
        "development_cutoff": cutoff,
        "requested_history_limit": int(limit),
        "minimum_aligned_rows": 180,
        "split_policy": {
            "train_fraction": 0.50,
            "validation_end_fraction": 0.75,
            "indices_derived_only_after_preregistered_claim": True,
        },
        "contract_only_replay": True,
        "parameter_change_from_g13": True,
        "parameter_change_from_prior_generation": False,
        "strategy_parameter_change_from_prior_generation": False,
        "universe_change_from_prior_generation": False,
        "data_window_change_from_prior_generation": False,
        "cost_model_change_from_prior_generation": False,
        "promotion_threshold_change_from_prior_generation": False,
        "risk_snapshot_semantics_change_from_prior_generation": True,
        "execution_contract_change_from_prior_generation": False,
        "runtime_orchestration_change_from_prior_generation": False,
        "scheduled_task_namespace_change_from_prior_generation": True,
        "implementation_change_scope": [
            "separate_risk_policy_acceptance_from_effective_runtime_paper_authority",
            "fail_closed_public_pretrade_results_when_runtime_is_read_only",
            "bind_automated_paper_authority_to_exact_pipeline_run",
            "render_runtime_and_policy_authority_as_distinct_ui_states",
            "include_frontend_authorization_surface_in_candidate_implementation_manifest",
        ],
        "change_rationale": "G45 blocked every mutation correctly, but its public risk snapshot exposed model-level paper acceptance as paper_order_allowed and the UI rendered that value as executable permission even while the runtime was read-only, paper authorization was false and the account was not armed. G46 separates policy, runtime, manual paper availability and automated strategy authority; public pretrade results now fail closed in read-only mode and automated authority is bound to the exact pipeline run. G45 was explicitly retired before source changes, and its zero natural observations, zero outcomes and zero executed rebalances are not migrated or backfilled.",
        "protocol_declared_before_market_data_access": True,
        "protocol_declared_before_candidate_evaluation": True,
        "preprotocol_data_maintenance_only": True,
        "preprotocol_data_maintenance_report": "stock_data_audit_g39_preprotocol_v9_final.json",
        "preprotocol_data_maintenance_report_sha256": "a11f7b0089b5c734db3ebc064fcbbcaa64e99e6265f49bc34373084357cbf19c",
        "preprotocol_data_maintenance_report_hash": "fbcca5efee35b0878cb42046604e8305bc63a0586da304ac3a2e53343051f314",
        "preprotocol_data_maintenance_append_only": False,
        "preprotocol_destructive_cache_rewrite_performed": False,
        "preprotocol_post_repair_audit_report": "stock_data_audit_g39_preprotocol_v9_final.json",
        "preprotocol_post_repair_audit_report_sha256": "a11f7b0089b5c734db3ebc064fcbbcaa64e99e6265f49bc34373084357cbf19c",
        "preprotocol_post_repair_audit_report_hash": "fbcca5efee35b0878cb42046604e8305bc63a0586da304ac3a2e53343051f314",
        "preprotocol_post_repair_audit_status": "PASS",
        "preprotocol_cross_source_evidence_hash": "fbcca5efee35b0878cb42046604e8305bc63a0586da304ac3a2e53343051f314",
        "preprotocol_live_audit_evidence_hash": "fbcca5efee35b0878cb42046604e8305bc63a0586da304ac3a2e53343051f314",
        "preprotocol_operational_failure_diagnostic_report": "portfolio_evidence_claim_substitution_diagnostic_g37_preprotocol.json",
        "preprotocol_operational_failure_diagnostic_report_sha256": "5e679e2b6c8da261cc716c1860718b3277885ef490a366f8d15393c226652a2b",
        "preprotocol_operational_failure_diagnostic_report_hash": "d553af70b94cde79653f3293acb58e87ee0821441e194ef210c51b15a3e6f8ad",
        "preprotocol_replay_fix_validation_report": "portfolio_evidence_claim_substitution_diagnostic_g37_postfix.json",
        "preprotocol_replay_fix_validation_report_sha256": "b93503dd0a5af747c1216d8efa18840254c75474b9d527cd665ed654e071ba4a",
        "preprotocol_replay_fix_validation_report_hash": "cbb42a91e4e227f4791c5d88d2621ab23139d4f6823f4b750417613a1db70ab5",
        "preprotocol_replay_fix_validation_status": "PASS",
        "preprotocol_semantic_bypass_diagnostic_report": "portfolio_evidence_claim_substitution_diagnostic_g37_preprotocol.json",
        "preprotocol_semantic_bypass_diagnostic_report_sha256": "5e679e2b6c8da261cc716c1860718b3277885ef490a366f8d15393c226652a2b",
        "preprotocol_semantic_bypass_diagnostic_hash": "d553af70b94cde79653f3293acb58e87ee0821441e194ef210c51b15a3e6f8ad",
        "preprotocol_semantic_bypass_observed": True,
        "preprotocol_semantic_bypass_parameter_selection_allowed": False,
        "preprotocol_research_batch_hash_gap_report": "internal_portfolio_backtest_pack_g37_evidence_claim_substitution_invalidated.json",
        "preprotocol_research_batch_hash_gap_report_sha256": "7a0cee5b010d70a09bef61b1c6028352559413b85385251cd44fbdbe532f5acf",
        "preprotocol_research_batch_hash_gap_report_hash": "bd3f696a3bff41cd637faeac78a708a4d61a69d47059c28f1af7f8db9fd0824e",
        "preprotocol_research_batch_hash_gap_observed": True,
        "preprotocol_research_batch_hash_gap_parameter_selection_allowed": False,
        "preprotocol_aapl_repair_report": "market_data_revision_repair_aapl_g39_query_window_contract.json",
        "preprotocol_aapl_repair_report_sha256": "026f44b947b30c603a65a87a5e3dde2b9aa803161273711516f088305d5eb582",
        "preprotocol_aapl_repair_report_hash": "79fb9a7d1ca41b140d8a482abd05e0cbe312ee452c41aeedb016193ce13eda09",
        "preprotocol_nvda_repair_report": "market_data_revision_repair_nvda_g39_v8_root_chain_complete.json",
        "preprotocol_nvda_repair_report_sha256": "51db3124fc3c9bca013c8c6773d11cdcd6d211765999948cd6e8eb2b884ca36c",
        "preprotocol_nvda_repair_report_hash": "4b8d0666f0dd021f98da44e0348aef07c294a73555c4a5bcb599d6224f143ffb",
        "preprotocol_revision_ledger_backup": "market_data_revisions_before_g39_window_repair_20260803_103913.sqlite",
        "preprotocol_revision_ledger_backup_sha256": "230e85c4dfbe9474c53198bd6c96d55f76dc84bd5e2d9fcf51bb897b55b1b1ed",
        "preprotocol_evidence_bundle_diagnostic_report": "portfolio_evidence_bundle_diagnostic_g40_shared_alias_fixed.json",
        "preprotocol_evidence_bundle_diagnostic_report_sha256": "7f75a72a02a483d0252ce90fdd85e0e399ad56e01b38f679efccb53e03da066b",
        "preprotocol_evidence_bundle_diagnostic_report_hash": "5618074817f5bcc13fe8799c668cace558253527a454c6d30950e853136a0016",
        "preprotocol_evidence_bundle_diagnostic_status": "PASS",
        "preprotocol_runtime_build_diagnostic_report": "runtime_build_diagnostic_g41_preprotocol.json",
        "preprotocol_runtime_build_diagnostic_report_sha256": "2cf06cfa30a9765ae1d8202c5b9814cb3a77ad870f245a2fb955611060c9459e",
        "preprotocol_runtime_build_diagnostic_report_hash": "55f9d0ab75e2e399c45a53edab2aebe0a651ff5f9048f4cc6dedf5dbadc7d9d8",
        "preprotocol_runtime_build_diagnostic_status": "PASS",
        "preprotocol_runtime_build_diagnostic_market_access": False,
        "preprotocol_data_maintenance_parameter_selection_allowed": False,
        "evaluation_start_policy": "FIRST_CANDIDATE_ACTIVE_SESSION_CASH_UNTIL_FIRST_SCHEDULED_REBALANCE",
        "forward_state_start_policy": "FIRST_CANDIDATE_ACTIVE_SESSION_CASH",
        "forward_capture_policy": "SESSION_CLOSE_TO_NEXT_SESSION_OPEN_NO_BACKFILL",
        "forward_clock_policy": "HTTPS_EXTERNAL_TIME_ATTESTATION_V2_SEMANTIC_RECOMPUTATION_REQUIRED",
        "trusted_clock_semantic_policy": "SOURCE_HASH_TIME_ARITHMETIC_VALID_SOURCE_COUNT_OFFSET_MEDIAN_QUALITY_AND_EXPLICIT_FALSE_AUTHORITY_RECOMPUTED",
        "forward_scheduler_policy": "FIFTEEN_MINUTE_PREFLIGHT_SINGLE_WRITER",
        "forward_performance_policy": "APPEND_ONLY_HASH_CHAIN_CASH_POSITIONS_FEES_EQUITY_AND_SPY_BENCHMARK",
        "benchmark_binding_policy": "FULL_DETERMINISTIC_BENCHMARK_REPORT_HASH_BOUND_TO_RESEARCH_BATCH_AND_STATISTICAL_AUDIT",
        "statistical_audit_semantic_policy": "TRUSTED_DEFAULTS_RECOMPUTE_FROZEN_STRATEGY_AND_BENCHMARK_CURVES_AND_UNVERIFIED_PASS_FAILS_CLOSED",
        "internal_backtest_pack_policy": "ACTIVE_FROZEN_ARTIFACT_VERIFICATION_ONLY_NO_MARKET_FETCH_NO_PARAMETER_SEARCH_NO_EXECUTION",
        "implementation_manifest_policy": "FULL_RECURSIVE_CLOSURE_AT_REGISTER_AND_CLAIM_EXACT_SOURCE_AND_RUNTIME_RECHECK_AT_READ",
        "runtime_build_consistency_policy": "HEALTH_BINDS_THE_PROCESS_LOADED_BACKEND_PYTHON_SOURCE_TREE_TO_CURRENT_DISK_AND_FAILS_CLOSED_WITH_RESTART_REQUIRED_ON_ADD_DELETE_OR_CONTENT_DRIFT",
        "desktop_backend_compatibility_policy": "THE_DESKTOP_SHELL_ACCEPTS_ONLY_THE_CURRENT_RUNTIME_BUILD_SCHEMA_WITH_EXPLICIT_FALSE_EXECUTION_AUTHORITY_AND_RESTART_REQUIRED_FALSE",
        "verified_backend_termination_policy": "AUTOMATIC_RESTART_IS_LOOPBACK_ONLY_AND_TERMINATES_ONLY_A_PYTHON_PROCESS_WHOSE_COMMAND_LINE_IDENTIFIES_THE_EXPECTED_EXCHANGE_TERMINAL_SERVER_ENTRY",
        "paper_reduction_quantity_policy": "FILLED_QUANTITY_MUST_NOT_EXCEED_EXPLICIT_REQUESTED_QUANTITY",
        "funding_settlement_policy": "FILL_REPORT_ESTIMATE_ONLY_CHARGE_REQUIRES_DEDICATED_SETTLEMENT_EVENT",
        "risk_failure_policy": "AUTHORITATIVE_ACCOUNT_POSITION_OVERRIDES_CALLER_CONTEXT_AND_MISMATCH_BLOCKS_RISK_INCREASE_WHILE_VERIFIED_REDUCTION_REMAINS_AVAILABLE",
        "paper_lifecycle_immutability_policy": "ORDER_IDENTITY_AND_TRANSITION_PREFIX_ARE_IMMUTABLE_AND_SETTLED_FILLS_OR_TERMINAL_STATES_CANNOT_BE_REWRITTEN",
        "paper_settlement_order_policy": "PENDING_FILLS_SETTLE_STRICTLY_BY_CREATION_ORDER_AND_THE_FIRST_BLOCKER_STOPS_ALL_LATER_SETTLEMENT",
        "paper_reduce_only_settlement_policy": "REDUCE_ONLY_IS_REVALIDATED_AGAINST_THE_CURRENT_DURABLE_POSITION_BEFORE_ACCOUNT_MUTATION",
        "paper_idempotency_quantity_policy": "AMOUNT_BASED_AND_QUANTITY_CONSTRAINED_REQUESTS_WITH_THE_SAME_KEY_ARE_CONFLICTING_CONTRACTS",
        "paper_idempotency_eviction_policy": "AN_EVICTED_IDEMPOTENCY_KEY_WITHOUT_DURABLE_HISTORY_FAILS_CLOSED_AND_CANNOT_EXECUTE_AGAIN",
        "paper_numeric_integrity_policy": "BOOLEAN_AND_NON_FINITE_NUMBERS_ARE_REJECTED_BEFORE_RISK_EXECUTION_OR_DURABLE_PAPER_LEDGER_COMMIT",
        "paper_rejection_quantity_policy": "REJECTED_QUANTITY_CONSTRAINED_REQUESTS_PRESERVE_REQUESTED_QUANTITY_NOTIONAL_AND_CONSTRAINT_SEMANTICS",
        "paper_order_output_isolation_policy": "PUBLIC_WRITER_AND_AUDIT_ORDER_SNAPSHOTS_ARE_DEEP_COPIES_AND_CANNOT_MUTATE_INTERNAL_STATE",
        "paper_order_sequence_policy": "RESTORED_ORDER_IDS_RECOVER_THE_MAXIMUM_SEQUENCE_AND_NEW_IDS_CANNOT_COLLIDE",
        "paper_manual_input_policy": "SIDE_ORDER_TYPE_QUANTITY_PRICE_LIMIT_AND_CONDITIONAL_FIELDS_REQUIRE_EXPLICIT_FINITE_IN_RANGE_VALUES_WITHOUT_BUY_OR_FULL_SIZE_DEFAULTS",
        "paper_reconciliation_snapshot_policy": "ACCOUNT_VERSION_COMPARE_AND_SWAP_RETRIES_STALE_RECOVERY_AND_UNRESOLVED_PENDING_SETTLEMENTS_FAIL_CLOSED",
        "paper_pending_settlement_gate_policy": "ANY_UNRESOLVED_DURABLE_FILL_BLOCKS_ALL_NEW_SIMULATED_EXECUTION_UNTIL_RECONCILED",
        "paper_condition_execution_policy": "PERSISTENT_CONDITIONS_REQUIRE_AN_ENABLED_MATCHER_OCO_REQUIRES_EXPLICIT_CONDITIONAL_CONTEXT_AND_TRIGGER_EXECUTION_RECHECKS_RISK",
        "paper_pipeline_binding_policy": "ARM_AND_STOP_PERSIST_STRATEGY_RUN_BINDING_ATOMICALLY_AND_AUTOMATION_REQUIRES_A_FLAT_ACCOUNT_WITHOUT_ACTIVE_CONDITIONS",
        "paper_signal_lineage_policy": "COMPLETED_BAR_AND_QUOTE_RISK_SIGNALS_KEEP_ONE_STABLE_SIGNAL_ID_THROUGH_RISK_ORDER_FILL_AND_AUDIT",
        "paper_manual_pretrade_policy": "EXECUTION_TIME_ACCOUNT_STATE_REVALIDATES_CALLER_PRETRADE_SIDE_NOTIONAL_POSITION_REDUCE_ONLY_ORDER_TYPE_AND_IDEMPOTENCY",
        "paper_emergency_halt_policy": "EMERGENCY_HALT_DISARMS_CANCELS_ACTIVE_CONDITIONS_CLEARS_PENDING_BINDINGS_AND_REPORTS_REMAINING_POSITION_EXPLICITLY",
        "paper_snapshot_isolation_policy": "PUBLIC_ACCOUNT_SNAPSHOTS_ARE_DETACHED_FROM_MUTABLE_INTERNAL_STATE",
        "paper_automated_risk_level_policy": "AUTOMATED_MANUAL_PERCENT_RISK_LEVELS_ARE_DERIVED_ONLY_FROM_EXPLICIT_CONFIG_NOT_AI_ANALYSIS",
        "event_replay_policy": "VERIFY_FILL_ARITHMETIC_QUANTITY_BOUND_FUNDING_SEMANTICS_IMMUTABLE_SETTLEMENT_AND_EVENT_LINEAGE",
        "batch_quote_quality_policy": "TIMESTAMP_SOURCE_SESSION_FALLBACK_AND_QUARANTINE_MUST_BE_NORMALIZED_BEFORE_MULTI_CONSUMER_USE",
        "stock_daily_realtime_policy": "COMPLETED_DAILY_BARS_ARE_NOT_REALTIME_ONLY_PROVISIONAL_CURRENT_SESSION_BARS_MAY_BE_REALTIME",
        "stock_adjusted_volume_policy": "ADJUSTED_DAILY_PRICES_REQUIRE_INVERSE_SPLIT_FACTOR_VOLUME_REBASE_AND_CONTENT_ADDRESSED_MIGRATION_EVIDENCE",
        "stock_provider_completion_policy": "FUTU_YAHOO_AND_STOOQ_DAILY_ROWS_REQUIRE_EXPLICIT_CAUSAL_SESSION_COMPLETION_AND_EMPTY_COMPLETED_RESPONSES_CANNOT_MUTATE_PROVIDER_HISTORY",
        "provider_observation_vintage_policy": "QUERY_WINDOWS_MERGE_BY_DATE_WITH_KNOWN_PROVIDER_HISTORY_AND_CANNOT_DELETE_ABSENT_ROWS_WHILE_ONLY_AUTHORITATIVE_FULL_OBSERVATIONS_MAY_ASSERT_TRUNCATION",
        "query_window_unchanged_policy": "A_COMPLETE_CONTENT_IDENTICAL_QUERY_WINDOW_PASSES_WITHOUT_INHERITING_NONBLOCKING_REVIEW_STATE_WHILE_TRUE_SUBSETS_REMAIN_EXPLICIT_REVIEW",
        "revision_block_lineage_policy": "INTRINSIC_EVENT_STATUS_IS_DISTINCT_FROM_EFFECTIVE_CARRIED_STATE_AND_RESOLUTION_ADVANCES_TO_THE_NEXT_TRUE_UNRESOLVED_BLOCKER",
        "revision_repair_scope_policy": "REPAIR_STATUS_APPLIES_ONLY_TO_EXPLICITLY_RESTORED_PROVIDER_SCOPES_AND_UNRELATED_HISTORICAL_BLOCKS_REMAIN_IMMUTABLE",
        "backtest_dataset_lineage_policy": "EVERY_FROZEN_BACKTEST_DATASET_REQUIRES_THE_PREREGISTERED_EXPERIMENT_ID_IN_ITS_SCOPE_AND_SAME_DATE_WINDOWS_FROM_DIFFERENT_EXPERIMENTS_CANNOT_COLLIDE",
        "legacy_dataset_block_policy": "RETIRED_UNRESOLVED_DATASET_REVISIONS_REMAIN_AUDITABLE_BLOCKS_AND_NEVER_AUTHORIZE_OR_CONTAMINATE_A_NEW_EXPERIMENT_LINEAGE",
        "content_addressed_evidence_bundle_policy": "THE_INTERNAL_PACK_EMBEDS_A_SELF_CONTAINED_COMPRESSED_CONTENT_ADDRESSED_MANIFEST_WITHOUT_EXTERNAL_FILE_PATH_DEPENDENCIES",
        "evidence_bundle_deduplication_policy": "IDENTICAL_EVIDENCE_CONTENT_IS_STORED_ONCE_AND_REFERENCED_BY_CANONICAL_SHA256_WITH_ENTRY_AND_REFERENCE_COUNTS_REVERIFIED",
        "shared_evidence_alias_policy": "PACKING_ACCEPTS_ONLY_REFS_CREATED_DURING_THE_CURRENT_PASS_FOR_SHARED_OBJECT_PATHS_COUNTS_EVERY_LOGICAL_REFERENCE_AND_REJECTS_PREEXISTING_REFS_WITHOUT_A_BUNDLE",
        "cross_source_snapshot_binding_policy": "CROSS_SOURCE_METRICS_REQUIRE_COMPLETE_CANONICAL_PRIMARY_AND_SECONDARY_SNAPSHOTS_AND_A_FULL_SEMANTIC_REBUILD",
        "point_in_time_membership_binding_policy": "MEMBERSHIP_CLAIMS_REQUIRE_CONTENT_ADDRESSED_SOURCE_EVIDENCE_PUBLICATION_RETRIEVAL_AND_EXPLICIT_FALSE_EXECUTION_AUTHORITY",
        "point_in_time_pre_membership_gap_policy": "ONLY_DATES_BEFORE_A_VERIFIED_MEMBERSHIP_START_MAY_USE_A_CONTRACT_HASH_BOUND_NONTRADABLE_NO_POSITION_SENTINEL_AND_MISSING_DATES_ON_OR_AFTER_MEMBERSHIP_BLOCK",
        "point_in_time_benchmark_coverage_policy": "VERIFIED_HISTORICAL_UNIVERSES_PRESERVE_THE_OFFICIAL_BENCHMARK_CALENDAR_INSTEAD_OF_TRUNCATING_TO_THE_LATEST_SYMBOL_FIRST_DATE",
        "causal_observed_history_policy": "MOMENTUM_VOLATILITY_LIQUIDITY_AND_EXECUTION_COSTS_CONSUME_ONLY_OBSERVED_TRADABLE_NONVALUATION_ROWS_AND_SENTINELS_NEVER_SEED_A_PRIOR_PRICE",
        "portfolio_dataset_universe_binding_policy": "ALIGNED_DATASET_AND_MANIFEST_HASHES_BIND_THE_EXACT_VERIFIED_UNIVERSE_CONTRACT_AND_POINT_IN_TIME_MODE",
        "portfolio_replay_universe_binding_policy": "RESEARCH_ARCHIVE_SHADOW_FORWARD_AND_ISOLATED_REPLAY_REBUILD_THE_DATASET_WITH_THE_SAME_FROZEN_UNIVERSE_CONTRACT",
        "reference_data_intake_policy": "OFFICIAL_MEMBERSHIP_AND_CORPORATE_ACTION_SOURCE_DOCUMENTS_REQUIRE_RELATIVE_PATH_SHA256_TIME_COVERAGE_AND_MANUAL_LICENSE_REVIEW_BEFORE_IMPORT",
        "corporate_action_source_binding_policy": "OFFICIAL_ACTION_CLAIMS_REQUIRE_CONTENT_ADDRESSED_SOURCE_EVIDENCE_COVERAGE_RECORD_COUNT_AND_EXPLICIT_FALSE_EXECUTION_AUTHORITY",
        "provider_approval_binding_policy": "PROVIDER_APPROVAL_REQUIRES_A_CANONICAL_RECEIPT_BOUND_TO_TERMS_REVIEW_QUOTA_AND_REVIEWER_FIELDS",
        "provider_approval_freshness_policy": "APPROVED_PROVIDER_REVIEWS_ARE_RECHECKED_AT_THE_CURRENT_VERIFICATION_TIME_AND_EXPIRE_FAIL_CLOSED",
        "forced_refresh_truth_policy": "FAILED_FORCED_REFRESH_CACHE_FALLBACKS_MUST_DISCLOSE_FORCED_AND_REFRESH_FAILED_WITH_A_WARNING",
        "futu_sdk_log_isolation_policy": "FUTU_SDK_LOWERCASE_APPDATA_IS_SCOPED_TO_PROJECT_RUNTIME_DURING_IMPORT_AND_PROCESS_ENVIRONMENT_IS_RESTORED",
        "volume_revision_materiality_policy": "VOLUME_DRIFT_IS_MATERIAL_ONLY_ABOVE_ONE_SHARE_AND_ONE_THOUSANDTH_OF_ONE_PERCENT_RELATIVE_TOLERANCE",
        "data_audit_status_precedence_policy": "AGGREGATE_DATA_AUDITS_PRESERVE_STRICT_BLOCK_THEN_REVIEW_THEN_PASS_PRECEDENCE",
        "offline_replay_frozen_stage_evidence_policy": "VALIDATION_TEST_AND_FULL_REPLAYS_BIND_EXACT_STAGE_SPECIFIC_ADJUSTMENT_AND_MARKET_REVISION_EVIDENCE_FROM_THE_FROZEN_RESEARCH_REPORT",
        "offline_replay_failure_diagnostics_policy": "VALID_FAIL_CLOSED_JSON_FROM_A_NONZERO_REPLAY_SUBPROCESS_PRESERVES_ITS_SEMANTIC_BLOCKERS",
        "offline_replay_driver_closure_policy": "THE_REPLAY_DRIVER_IS_INCLUDED_IN_THE_FROZEN_IMPLEMENTATION_AND_ARCHIVES_COPY_IT_ONLY_FROM_THE_FROZEN_CANDIDATE_SOURCE_TREE",
        "daily_session_timestamp_policy": "DAILY_SESSION_DATE_MUST_MATCH_THE_UTC_DATE_DERIVED_FROM_ITS_TIMESTAMP_OR_THE_DATASET_BLOCKS",
        "boolean_numeric_contract_policy": "JSON_BOOLEANS_ARE_NEVER_ACCEPTED_AS_OHLCV_RISK_EXECUTION_ACCOUNT_OR_FORWARD_PERFORMANCE_NUMBERS",
        "backtest_causal_input_policy": "SIGNAL_FACTORIES_RECEIVE_PREFIX_COPIES_AND_EXCEPTIONS_OR_NON_CALLABLE_RESULTS_FAIL_CLOSED",
        "backtest_pending_exit_policy": "FORCED_EXITS_REQUIRE_OBSERVED_EXIT_LIQUIDITY_AND_SPLIT_ADJUSTED_PENDING_QUANTITY_WITHOUT_FABRICATED_CAPACITY",
        "backtest_residual_cash_policy": "POSITION_WEIGHT_CAPS_LEAVE_UNALLOCATED_CAPITAL_AS_EXPLICIT_CASH",
        "forward_corporate_action_policy": "FORWARD_ACCOUNTING_ACCEPTS_ONLY_EMBEDDED_ADJUSTED_SERIES_UNTIL_EXPLICIT_RAW_ACTION_SETTLEMENT_IS_IMPLEMENTED",
        "forward_threshold_policy": "OBSERVATION_OUTCOME_AND_REBALANCE_THRESHOLDS_REQUIRE_EXPLICIT_POSITIVE_INTEGERS_AND_INVALID_VALUES_BLOCK",
        "forward_evidence_binding_policy": "CALENDAR_LIFECYCLE_ADJUSTMENT_AND_DATA_REVISION_CHILD_HASHES_ARE_RECOMPUTED_BEFORE_FORWARD_USE",
        "active_candidate_retirement_policy": "EXPECTED_HASH_TRUSTED_CLOCK_AND_BLOCKED_PACK_BOUND_ATOMIC_RETIREMENT_WITH_NO_EXECUTION_AUTHORITY",
        "anomaly_priority_policy": "A_PRIORITY_REQUIRES_READY_REALTIME_QUALITY_STALE_CLOSED_UNKNOWN_AND_FALLBACK_DATA_CANNOT_ENTER_A",
        "legacy_ui_quality_policy": "MISSING_QUALITY_METADATA_DEFAULTS_TO_UNCONFIRMED_NOT_REALTIME",
        "active_candidate_verification_latency_budget_ms": 1500,
        "portfolio_forward_api_latency_budget_ms": 2500,
        "forward_snapshot_binding_policy": "OBSERVATION_AND_PERFORMANCE_SHADOW_AUDITS_MUST_MATCH_BY_CANONICAL_HASH",
        "execution_authority_type_policy": "AUTHORITY_FIELDS_MUST_BE_EXPLICIT_JSON_FALSE",
        "research_gate_type_policy": "RESEARCH_AND_FORWARD_GATES_REQUIRE_EXPLICIT_JSON_TRUE_OR_FALSE_WITHOUT_TRUTHINESS_COERCION",
        "evidence_count_type_policy": "OBSERVATION_REBALANCE_EVENT_AND_TIMESTAMP_COUNTS_REQUIRE_NATIVE_JSON_INTEGERS",
        "paper_restore_failure_policy": "PERSISTENT_HISTORY_LOAD_OR_VALIDATION_FAILURE_BLOCKS_ALL_NEW_SIMULATED_EXECUTION_BEFORE_MARKET_BOOK_ACCESS",
        "paper_restore_idempotency_policy": "DUPLICATE_RESTORED_IDEMPOTENCY_KEYS_BOUND_TO_DIFFERENT_ORDERS_BLOCK_THE_EXECUTOR",
        "forward_verifier_failure_policy": "MALFORMED_FORWARD_STATE_TYPES_RETURN_BLOCK_AND_NEVER_RAISE",
        "paper_activation_binding_policy": "MANUAL_APPROVAL_TIME_CANDIDATE_AND_READINESS_HASH_ARE_REVERIFIED_FROM_THE_RECEIPT",
        "paper_execution_authorization_policy": "RISK_RESULT_ALLOWED_MODE_REQUEST_ID_AND_REDUCE_ONLY_REQUIRE_EXPLICIT_NATIVE_TYPES_BEFORE_BOOK_ACCESS",
        "paper_order_contract_policy": "EVERY_DURABLE_ORDER_RESTORE_WRITE_RECONCILIATION_AND_REPLAY_VALIDATES_IDENTITY_STATE_TRANSITIONS_TIMESTAMPS_NUMBERS_AND_EXECUTION_REPORT",
        "paper_fill_arithmetic_policy": "FILLED_NOTIONAL_MUST_MATCH_FILLED_QUANTITY_TIMES_AVERAGE_PRICE_AND_CANNOT_EXCEED_THE_REQUESTED_QUANTITY_OR_NOTIONAL",
        "paper_cross_process_idempotency_policy": "CONCURRENT_EXECUTORS_WITH_ONE_IDEMPOTENCY_KEY_RESOLVE_TO_ONE_DURABLE_ORDER_AND_ONE_FILL",
        "paper_pretrade_freshness_policy": "EXECUTION_REUSES_ONLY_COMPLETE_MATCHING_NATIVE_TYPED_PRETRADE_RESULTS_AT_MOST_FIFTEEN_SECONDS_OLD",
        "portfolio_paper_state_contract_policy": "PERSISTED_AUTHORIZATION_CASH_POSITION_FEE_VERSION_AND_SIMULATION_FIELDS_REQUIRE_EXACT_TYPES_AND_FINITE_VALUES",
        "paper_strategy_clock_causality_policy": "ONLY_ONE_RECENT_NEWLY_COMPLETED_BAR_MAY_ADVANCE_THE_CLOCK_AND_MISSED_BARS_AFTER_DOWNTIME_ARE_NEVER_BACKFILLED",
        "candle_completion_contract_policy": "CACHE_RESEARCH_BACKTEST_REGIME_CORRELATION_AND_REPLAY_SHARE_ONE_EXPLICIT_FAIL_CLOSED_COMPLETION_PARSER",
        "market_permission_boolean_policy": "REALTIME_ENTRY_SIMULATION_PROVIDER_SESSION_FALLBACK_AND_QUARANTINE_FLAGS_USE_PERMISSION_OR_HAZARD_SPECIFIC_EXPLICIT_BOOLEAN_SEMANTICS",
        "critical_module_closure_policy": "ORDER_ACCOUNT_CLOCK_MARKET_RISK_GUARDIAN_MUTATION_AND_HTTP_CONTRACT_MODULES_ARE_INCLUDED_IN_THE_FROZEN_IMPLEMENTATION_MANIFEST",
        "minimum_forward_observations": 60,
        "minimum_forward_performance_outcomes": 60,
        "minimum_planned_rebalances": 8,
        "maximum_forward_contract_violations": 0,
        "benchmark_symbol": benchmark,
        "tradable_symbols": tradables,
        "clusters": {symbol: DEFAULT_CLUSTERS.get(symbol, symbol) for symbol in tradables},
        "lookback": 126,
        "skip_recent": 5,
        "rebalance_interval": 5,
        "rebalance_schedule": "FIRST_COMPLETED_TRADING_DAY_OF_ISO_WEEK",
        "top_n": 3,
        "rank_buffer": 2,
        "gross_target_pct": 60.0,
        "execution_risk_buffer_pct": 0.25,
        "max_per_cluster": 1,
        "minimum_trade_pct": 1.0,
        "drawdown_guard_pct": 12.0,
        "drawdown_cooldown_bars": 20,
        "volatility_window": 63,
        "target_portfolio_volatility_pct": 15.0,
        "max_position_weight_pct": 50.0,
        "liquidity_window": 20,
        "minimum_median_dollar_volume": 5_000_000.0,
        "max_entry_participation_pct": 1.0,
        "max_exit_participation_pct": 2.0,
        "max_entry_open_gap_pct": 12.0,
        "impact_bps_at_full_participation": 15.0,
        "fee_rate": 0.0005,
        "slippage_bps": 2.0,
        "cost_stress_contract": [
            {"label": "MODERATE", "fee_rate": 0.0010, "slippage_bps": 5.0},
            {"label": "SEVERE", "fee_rate": 0.0020, "slippage_bps": 10.0},
        ],
        "acceptance_contract": {
            "validation_and_test_return_positive": True,
            "validation_and_test_max_drawdown_below_pct": 15.0,
            "validation_and_test_annualized_turnover_below": 12.0,
            "severe_cost_test_return_positive": True,
            "causal_prefix_audit_required": True,
            "schedule_and_adjustment_contracts_required": True,
            "execution_rehearsal_all_stages_pass": True,
        },
        "optimizer_used": False,
        "prior_development_trial_count": 10,
        "current_generation_trial_count": 0,
        "consumption_policy": "SINGLE_REGISTERED_RUN_NO_REPLAY",
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    protocol["protocol_hash"] = canonical_hash(protocol)
    return protocol


def research_source_files() -> list[Path]:
    return [
        Path(__file__),
        Path(__file__).with_name("portfolio_reference_data.py"),
        Path(__file__).with_name("run_portfolio_reference_data_intake.py"),
        Path(__file__).with_name("run_portfolio_shadow_observation.py"),
        Path(__file__).with_name("run_portfolio_forward_scheduler.py"),
        Path(__file__).with_name("run_portfolio_forward_performance.py"),
        Path(__file__).with_name("run_internal_portfolio_statistical_audit.py"),
        Path(__file__).with_name("run_internal_portfolio_robustness.py"),
        Path(__file__).with_name("run_internal_execution_rehearsal.py"),
        Path(__file__).with_name("run_internal_portfolio_holdout.py"),
        Path(__file__).with_name("run_internal_backtest.py"),
        Path(__file__).with_name("run_internal_backtest_campaign.py"),
        Path(__file__).with_name("run_stock_data_audit.py"),
        Path(__file__).with_name("run_market_data_revision_repair.py"),
        Path(__file__).with_name("run_portfolio_evidence_bundle_diagnostic.py"),
        Path(__file__).with_name("run_runtime_build_diagnostic.py"),
        Path(__file__).with_name("run_portfolio_data_admission_audit.py"),
        Path(__file__).with_name("run_portfolio_evidence_archive.py"),
        Path(__file__).with_name("run_portfolio_forward_watchdog.py"),
        Path(__file__).with_name("run_portfolio_runtime_task.py"),
        Path(__file__).with_name("activate_portfolio_candidate.py"),
        Path(__file__).with_name("run_retire_portfolio_candidate.py"),
        Path(__file__).with_name("install_portfolio_forward_task.ps1"),
        Path(__file__).with_name("install_portfolio_forward_performance_task.ps1"),
        Path(__file__).with_name("install_portfolio_forward_backup_task.ps1"),
        Path(__file__).with_name("install_portfolio_forward_watchdog_task.ps1"),
        Path(server.__file__),
        Path(server.__file__).with_name("static") / "app.js",
        Path(config_module.__file__),
        Path(utils_module.__file__),
        Path(backtest_engine_module.__file__),
        Path(portfolio_admission_module.__file__),
        Path(portfolio_backtest_module.__file__),
        Path(portfolio_backtest_module.__file__).with_name("portfolio_backtest_replay_driver.py"),
        Path(portfolio_experiment_module.__file__),
        Path(market_regime_module.__file__),
        Path(portfolio_risk_module.__file__),
        Path(portfolio_robustness_module.__file__),
        Path(portfolio_candidate_module.__file__),
        Path(portfolio_forward_module.__file__),
        Path(portfolio_forward_scheduler_module.__file__),
        Path(portfolio_forward_performance_module.__file__),
        Path(portfolio_execution_rehearsal_module.__file__),
        Path(portfolio_paper_account_module.__file__),
        Path(portfolio_paper_activation_module.__file__),
        Path(portfolio_shadow_module.__file__),
        Path(portfolio_shadow_risk_module.__file__),
        Path(portfolio_statistical_audit_module.__file__),
        Path(portfolio_backtest_pack_module.__file__),
        Path(portfolio_evidence_bundle_module.__file__),
        Path(portfolio_universe_module.__file__),
        Path(provider_governance_module.__file__),
        Path(research_exposure_module.__file__),
        Path(corporate_action_ledger_module.__file__),
        Path(market_data_revision_ledger_module.__file__),
        Path(market_calendar_module.__file__),
        Path(security_lifecycle_module.__file__),
        Path(trusted_clock_module.__file__),
        Path(stock_candles_io_module.__file__),
        Path(candle_contract_module.__file__),
        Path(stock_candles_module.__file__),
        Path(stock_candle_quality_module.__file__),
        Path(stocks_module.__file__),
        Path(provider_health_module.__file__),
        Path(futu_quotes_module.__file__),
        Path(event_lineage_module.__file__),
        Path(event_replay_module.__file__),
        Path(guardian_service_module.__file__),
        Path(http_contract_module.__file__),
        Path(market_data_service_module.__file__),
        Path(mutation_journal_module.__file__),
        Path(paper_account_module.__file__),
        Path(paper_executor_module.__file__),
        Path(paper_ledger_module.__file__),
        Path(paper_order_contract_module.__file__),
        Path(paper_strategy_clock_module.__file__),
        Path(risk_service_module.__file__),
        Path(strategy_benchmark_module.__file__),
    ]


def _through_cutoff(payload: dict[str, Any], cutoff: str, dataset_lineage_id: str) -> dict[str, Any]:
    return slice_portfolio_payload_through_date(
        payload,
        cutoff,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
    )


def prefix_payloads_through_index(
    payloads: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    end_index: int,
    dataset_lineage_id: str,
) -> tuple[dict[str, dict[str, Any]], str]:
    expected_dates = list((manifest.get("market_calendar") or {}).get("expected_dates") or [])
    if end_index <= 0 or end_index > len(expected_dates):
        raise ValueError("prefix_end_index_out_of_range")
    cutoff = str(expected_dates[end_index - 1])
    return {
        symbol: _through_cutoff(dict(payload), cutoff, dataset_lineage_id)
        for symbol, payload in payloads.items()
    }, cutoff


def aligned_payloads(
    symbols: list[str],
    limit: int,
    benchmark: str,
    cutoff: str = "",
    dataset_lineage_id: str = "",
    universe_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = {
        symbol: _through_cutoff(
            server.backtest_market_rows(symbol, limit, dataset_lineage_id=dataset_lineage_id),
            cutoff,
            dataset_lineage_id,
        )
        for symbol in symbols
    }
    prepared = prepare_attested_portfolio_dataset(
        raw,
        benchmark_symbol=benchmark,
        minimum_rows=180,
        attest_backtest_rows=server.attest_stock_backtest_rows,
        dataset_lineage_id=dataset_lineage_id,
        universe_contract=universe_contract,
    )
    if prepared["status"] != "PASS":
        return {}, prepared["manifest"]
    return dict(prepared["payloads"]), prepared["manifest"]


def benchmark_report(
    payload: dict[str, Any],
    *,
    symbol: str,
    position_pct: float,
    evaluation_start_index: int,
    fee_rate: float = 0.0005,
    slippage_bps: float = 2.0,
) -> dict[str, Any]:
    report = buy_and_hold_report(
        rows=list(payload.get("rows") or []),
        symbol=symbol,
        source=f"{payload.get('source') or ''}:portfolio_benchmark",
        position_pct=position_pct,
        startup_candles=80,
        fee_rate=fee_rate,
        slippage_bps=slippage_bps,
        market="stock",
        evaluation_start_index=evaluation_start_index,
    )
    report["benchmark_run_hash"] = canonical_hash(report)
    return report


def comparison(strategy: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    strategy_return = finite_number(strategy.get("total_return_pct"))
    benchmark_return = finite_number(benchmark.get("total_return_pct"))
    strategy_drawdown = finite_number(strategy.get("max_drawdown_pct"))
    benchmark_drawdown = finite_number(benchmark.get("max_drawdown_pct"))
    strategy_sharpe = finite_number(strategy.get("sharpe"))
    benchmark_sharpe = finite_number(benchmark.get("sharpe"))
    strategy_efficiency = strategy_return / max(strategy_drawdown, 1.0)
    benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)
    return {
        "strategy_return_pct": round(strategy_return, 4),
        "benchmark_return_pct": round(benchmark_return, 4),
        "excess_return_pct": round(strategy_return - benchmark_return, 4),
        "strategy_max_drawdown_pct": round(strategy_drawdown, 4),
        "benchmark_max_drawdown_pct": round(benchmark_drawdown, 4),
        "drawdown_improvement_pct": round(benchmark_drawdown - strategy_drawdown, 4),
        "strategy_sharpe": round(strategy_sharpe, 4),
        "benchmark_sharpe": round(benchmark_sharpe, 4),
        "sharpe_excess": round(strategy_sharpe - benchmark_sharpe, 4),
        "risk_efficiency_excess": round(strategy_efficiency - benchmark_efficiency, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one frozen, development-only relative-strength portfolio study.")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--tradables", nargs="+", default=DEFAULT_TRADABLES)
    parser.add_argument("--limit", type=int, default=1600)
    parser.add_argument("--cutoff", default="2026-07-30")
    parser.add_argument("--output", default="")
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--experiment-db", default="")
    parser.add_argument("--register-only", action="store_true")
    parser.add_argument("--audit-registry", action="store_true")
    parser.add_argument("--abort-experiment", default="")
    parser.add_argument("--abort-reason", default="")
    args = parser.parse_args()

    benchmark = str(args.benchmark).upper()
    tradables = list(dict.fromkeys(str(symbol).upper() for symbol in args.tradables if str(symbol).upper() != benchmark))
    symbols = [benchmark, *tradables]
    cutoff = str(args.cutoff or "").strip()[:10]
    protocol = build_research_protocol(
        benchmark=benchmark,
        tradables=tradables,
        limit=max(int(args.limit), 180),
        cutoff=cutoff,
    )
    source_files = research_source_files()
    experiment_db = (
        Path(args.experiment_db).resolve()
        if args.experiment_db
        else Path(server.RUNTIME_DIR) / "portfolio_experiments.sqlite3"
    )
    experiment_registry = PortfolioExperimentRegistry(db_path=experiment_db)
    if args.audit_registry:
        registry_audit = experiment_registry.audit()
        print(json.dumps(registry_audit, ensure_ascii=False, indent=2))
        return 0 if registry_audit.get("status") == "PASS" else 2
    if args.abort_experiment:
        aborted = experiment_registry.abort(
            experiment_id=str(args.abort_experiment),
            reason=str(args.abort_reason or "explicit operator retirement"),
            clock_attestation=attest_utc_clock(),
        )
        print(json.dumps(aborted, ensure_ascii=False, indent=2))
        return 0 if aborted.get("status") == "ABORTED" else 2
    if args.register_only:
        registered = experiment_registry.register(
            protocol=protocol,
            source_files=source_files,
            clock_attestation=attest_utc_clock(),
        )
        print(json.dumps(registered, ensure_ascii=False, indent=2))
        return 0 if registered.get("status") == "REGISTERED" else 2
    if not str(args.experiment_id or "").strip():
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "blockers": ["preregistered_experiment_id_required"],
            "next_step": "Run this command once with --register-only, then rerun with --experiment-id.",
            "protocol_hash": protocol.get("protocol_hash"),
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    experiment_claim = experiment_registry.claim(
        experiment_id=str(args.experiment_id),
        protocol=protocol,
        source_files=source_files,
        clock_attestation=attest_utc_clock(),
    )
    if experiment_claim.get("status") != "CLAIMED":
        print(json.dumps(experiment_claim, ensure_ascii=False, indent=2))
        return 2
    experiment_binding = dict(experiment_claim.get("binding") or {})
    declared_at = datetime.fromtimestamp(
        int(experiment_binding.get("started_at") or 0) / 1000.0,
        tz=timezone.utc,
    ).isoformat()
    universe_contract = build_research_universe_contract(
        benchmark_symbol=benchmark,
        tradable_symbols=tradables,
        declared_at=declared_at,
        selection_basis=str(protocol.get("universe_selection_basis") or ""),
    )

    dataset_lineage_id = str(experiment_binding.get("experiment_id") or "")
    payloads, manifest = aligned_payloads(
        symbols,
        max(int(args.limit), 180),
        benchmark,
        cutoff,
        dataset_lineage_id,
        universe_contract,
    )
    if not payloads:
        aborted = experiment_registry.abort(
            experiment_id=str(args.experiment_id),
            reason="dataset preparation failed after registered experiment claim",
            clock_attestation=attest_utc_clock(),
        )
        print(json.dumps({
            "ok": False,
            "dataset_manifest": manifest,
            "experiment_abort": aborted,
        }, ensure_ascii=False, indent=2))
        return 2

    provider_ids = required_provider_ids_from_evidence(
        dict(manifest.get("adjustment_evidence") or {}),
        dict(manifest.get("data_revision_evidence") or {}),
    )
    provider_governance = build_unassessed_provider_governance_contract(
        provider_ids=provider_ids,
        generated_at=declared_at,
    )

    row_count = int(manifest.get("row_count") or 0)
    train_end = int(row_count * float(protocol["split_policy"]["train_fraction"]))
    validation_end = int(row_count * float(protocol["split_policy"]["validation_end_fraction"]))
    spec = {key: value for key, value in protocol.items() if key != "protocol_hash"}
    spec["research_protocol_schema_version"] = str(spec.pop("schema_version"))
    spec["schema_version"] = PORTFOLIO_BACKTEST_SCHEMA_VERSION
    spec["research_protocol_hash"] = str(protocol.get("protocol_hash") or "")
    spec["experiment_id"] = str(experiment_binding.get("experiment_id") or "")
    spec["experiment_intent_hash"] = str(experiment_binding.get("intent_hash") or "")
    spec["trial_count"] = int(protocol.get("prior_development_trial_count") or 0)
    spec["train_end_index"] = train_end
    spec["validation_end_index"] = validation_end
    engine_settings = {
        "benchmark_symbol": benchmark,
        "tradable_symbols": tradables,
        "clusters": spec["clusters"],
        "lookback": spec["lookback"],
        "skip_recent": spec["skip_recent"],
        "rebalance_interval": spec["rebalance_interval"],
        "top_n": spec["top_n"],
        "rank_buffer": spec["rank_buffer"],
        "gross_target_pct": spec["gross_target_pct"],
        "execution_risk_buffer_pct": spec["execution_risk_buffer_pct"],
        "max_per_cluster": spec["max_per_cluster"],
        "minimum_trade_pct": spec["minimum_trade_pct"],
        "drawdown_guard_pct": spec["drawdown_guard_pct"],
        "drawdown_cooldown_bars": spec["drawdown_cooldown_bars"],
        "volatility_window": spec["volatility_window"],
        "target_portfolio_volatility_pct": spec["target_portfolio_volatility_pct"],
        "max_position_weight_pct": spec["max_position_weight_pct"],
        "liquidity_window": spec["liquidity_window"],
        "minimum_median_dollar_volume": spec["minimum_median_dollar_volume"],
        "max_entry_participation_pct": spec["max_entry_participation_pct"],
        "max_exit_participation_pct": spec["max_exit_participation_pct"],
        "max_entry_open_gap_pct": spec["max_entry_open_gap_pct"],
        "impact_bps_at_full_participation": spec["impact_bps_at_full_participation"],
        "fee_rate": spec["fee_rate"],
        "slippage_bps": spec["slippage_bps"],
        "universe_contract": universe_contract,
    }
    validation_payloads, validation_cutoff = prefix_payloads_through_index(
        payloads,
        manifest,
        validation_end,
        dataset_lineage_id,
    )
    spec["validation_cutoff"] = validation_cutoff
    validation = run_causal_relative_strength_backtest(
        payloads=validation_payloads,
        evaluation_start_index=train_end,
        **engine_settings,
    )
    test = run_causal_relative_strength_backtest(
        payloads=payloads,
        evaluation_start_index=validation_end,
        **engine_settings,
    )
    full = run_causal_relative_strength_backtest(payloads=payloads, **engine_settings)
    validation_benchmark = benchmark_report(
        validation_payloads[benchmark],
        symbol=benchmark,
        position_pct=spec["gross_target_pct"],
        evaluation_start_index=train_end,
        fee_rate=spec["fee_rate"],
        slippage_bps=spec["slippage_bps"],
    )
    test_benchmark = benchmark_report(
        payloads[benchmark],
        symbol=benchmark,
        position_pct=spec["gross_target_pct"],
        evaluation_start_index=validation_end,
        fee_rate=spec["fee_rate"],
        slippage_bps=spec["slippage_bps"],
    )
    validation_comparison = comparison(validation, validation_benchmark)
    test_comparison = comparison(test, test_benchmark)
    causal_audit = audit_relative_strength_causality(payloads=payloads, **engine_settings)
    correlations = build_correlation_matrix(payloads)
    cost_stress = []
    for scenario in list(protocol.get("cost_stress_contract") or []):
        label = str(scenario.get("label") or "UNDECLARED")
        stress_fee = float(scenario.get("fee_rate") or 0.0)
        stress_slippage = float(scenario.get("slippage_bps") or 0.0)
        stress_settings = {**engine_settings, "fee_rate": stress_fee, "slippage_bps": stress_slippage}
        stress_report = run_causal_relative_strength_backtest(
            payloads=payloads,
            evaluation_start_index=validation_end,
            **stress_settings,
        )
        cost_stress.append({
            "label": label,
            "fee_rate": stress_fee,
            "slippage_bps": stress_slippage,
            "ok": stress_report.get("ok") is True,
            "total_return_pct": stress_report.get("total_return_pct"),
            "max_drawdown_pct": stress_report.get("max_drawdown_pct"),
            "sharpe": stress_report.get("sharpe"),
            "turnover": stress_report.get("turnover"),
            "total_fees": stress_report.get("total_fees"),
            "gap_block_count": stress_report.get("gap_block_count"),
            "partial_fill_count": stress_report.get("partial_fill_count"),
            "estimated_strategy_capacity": stress_report.get("estimated_strategy_capacity"),
            "run_hash": stress_report.get("run_hash", ""),
        })
    severe_cost = next((item for item in cost_stress if item["label"] == "SEVERE"), {})
    execution_rehearsal = run_research_report_execution_rehearsal(
        {
            "spec": spec,
            "validation": validation,
            "test": test,
            "full": full,
            "correlation_matrix": correlations,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        generated_at=int(datetime.now(timezone.utc).timestamp() * 1000),
    )

    acceptance = dict(protocol.get("acceptance_contract") or {})
    drawdown_limit = float(acceptance.get("validation_and_test_max_drawdown_below_pct") or 0.0)
    turnover_limit = float(acceptance.get("validation_and_test_annualized_turnover_below") or 0.0)
    development_checks = {
        "validation_positive": finite_number(validation.get("total_return_pct")) > 0,
        "test_positive": finite_number(test.get("total_return_pct")) > 0,
        "validation_drawdown_below_15": finite_number(validation.get("max_drawdown_pct"), 100.0) < drawdown_limit,
        "test_drawdown_below_15": finite_number(test.get("max_drawdown_pct"), 100.0) < drawdown_limit,
        "validation_risk_efficiency_positive": finite_number(validation_comparison.get("risk_efficiency_excess")) > 0,
        "test_risk_efficiency_positive": finite_number(test_comparison.get("risk_efficiency_excess")) > 0,
        "validation_annualized_turnover_below_12": finite_number(validation.get("annualized_turnover_multiple"), 100.0) < turnover_limit,
        "test_annualized_turnover_below_12": finite_number(test.get("annualized_turnover_multiple"), 100.0) < turnover_limit,
        "severe_cost_test_positive": severe_cost.get("ok") is True and finite_number(severe_cost.get("total_return_pct")) > 0,
        "causal_audit_pass": causal_audit.get("status") == "PASS",
        "correlation_coverage_pass": correlations.get("status") == "PASS",
        "adjustment_contracts_pass": all(
            item.get("backtest_eligible") is True
            and corporate_action_ledger_module.verify_adjustment_evidence(item).get("status") == "PASS"
            for item in dict(manifest.get("adjustment_evidence") or {}).values()
        ),
        "cross_source_evidence_integrity_pass": all(
            bool(list(dict(revision or {}).get("cross_source") or []))
            and all(
                market_data_revision_ledger_module.verify_cross_source_evidence(item).get("status") == "PASS"
                for item in list(dict(revision or {}).get("cross_source") or [])
            )
            for revision in dict(manifest.get("data_revision_evidence") or {}).values()
        ),
        "provider_governance_contract_integrity_pass": (
            provider_governance_module.verify_provider_governance_contract(
                provider_governance,
                required_providers=provider_ids,
                verification_at=declared_at,
            ).get("status") == "PASS"
        ),
        "market_calendar_pass": (manifest.get("market_calendar") or {}).get("status") == "PASS",
        "security_lifecycle_contracts_pass": all(
            item.get("status") == "PASS"
            for item in dict(manifest.get("security_lifecycle") or {}).values()
        ),
        "return_accounting_double_count_protection_pass": all(
            (item.get("return_accounting") or {}).get("double_count_protection") is True
            and (item.get("return_accounting") or {}).get("cash_execution_supported") is True
            for item in dict(manifest.get("adjustment_evidence") or {}).values()
        ),
        "no_tradability_execution_blocks": int(full.get("tradability_block_count") or 0) == 0,
        "no_pending_forced_exits": not list(full.get("pending_forced_exit_symbols") or []),
        "liquidity_capacity_above_research_equity": float(full.get("estimated_strategy_capacity") or 0.0) >= 100_000.0,
        "no_liquidity_execution_blocks": int(full.get("liquidity_block_count") or 0) == 0,
        "no_capacity_partial_fills_at_research_equity": int(full.get("partial_fill_count") or 0) == 0,
        "validation_rebalance_schedule_pass": (validation.get("schedule_contract") or {}).get("status") == "PASS",
        "test_rebalance_schedule_pass": (test.get("schedule_contract") or {}).get("status") == "PASS",
        "full_rebalance_schedule_pass": (full.get("schedule_contract") or {}).get("status") == "PASS",
        "universe_contract_enforced": all(
            str((item.get("run_spec") or {}).get("universe_contract_hash") or "")
            == str(universe_contract.get("contract_hash") or "")
            for item in (validation, test, full)
        ),
        "execution_rehearsal_all_stages_pass": execution_rehearsal.get("status") == "PASS",
    }
    mechanism_status = "PROMISING_NEEDS_FRESH_HOLDOUT" if all(development_checks.values()) else "REVISE_OR_REJECT"
    created_at = datetime.now(timezone.utc).isoformat()
    output = Path(args.output) if args.output else Path(server.RUNTIME_DIR) / "reports" / f"portfolio_research_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    test_window = dict(test.get("evaluation_window") or {})
    temporal_exposure_audit = audit_portfolio_temporal_exposure(
        output.parent,
        start_date=str(test_window.get("start") or ""),
        end_date=str(test_window.get("end") or ""),
        symbols=symbols,
        exclude_paths=[output],
    )
    report = {
        "schema_version": PORTFOLIO_BACKTEST_SCHEMA_VERSION,
        "created_at": created_at,
        "spec": spec,
        "spec_hash": canonical_hash(spec),
        "dataset_manifest": manifest,
        "validation": validation,
        "validation_benchmark": validation_benchmark,
        "validation_comparison": validation_comparison,
        "test": test,
        "test_benchmark": test_benchmark,
        "test_comparison": test_comparison,
        "full": full,
        "causal_audit": causal_audit,
        "correlation_matrix": correlations,
        "cost_stress": cost_stress,
        "execution_rehearsal": execution_rehearsal,
        "development_checks": development_checks,
        "mechanism_status": mechanism_status,
        "experiment_governance": experiment_binding,
        "universe_contract": universe_contract,
        "provider_governance": provider_governance,
        "temporal_exposure_audit": temporal_exposure_audit,
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "known_limitations": [
            "The engine now enforces dated membership contracts, but this generation still uses a present-day static watchlist and therefore retains survivorship and convenience-universe bias.",
            "The development pool is concentrated in US mega-cap technology and semiconductors.",
            "Corporate-action accounting prevents adjusted-return double counting and provider vintages are cross-checked, but actions are not yet verified against an official exchange action feed.",
            "Provider terms, storage rights, redistribution limits and quotas are structurally tracked but remain NOT_ASSESSED until a human compliance review records signed evidence.",
            "The official session calendar and declared halt/delisting contract cannot infer an undeclared provider outage; unexplained missing sessions block research.",
            "Liquidity capacity is estimated from trailing daily median dollar volume and does not model intraday auction depth.",
            "This report cannot authorize paper trading without a future untouched holdout and forward observation.",
            "Forward observations count only when captured after the official session close and before the next official session opens; missed dates cannot be backfilled.",
            "Forward state starts from cash on the first candidate-active session; pre-activation backtest positions and rank-buffer retention cannot enter the forward account.",
            "Forward promotion requires independently settled daily outcomes, not only captured decision counts; the historical statistical veto remains binding.",
            "Preregistration limits accidental protocol drift but is a local audit control, not an independent third-party notarization service.",
            "The execution rehearsal replays recorded fills at their recorded prices to verify software contracts; it is not an independent market-impact estimate.",
        ],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["backtest_admission"] = build_internal_backtest_admission(report)
    report = portfolio_evidence_bundle_module.pack_portfolio_evidence_bundle(report)
    report["batch_run_hash"] = portfolio_backtest_pack_module.research_batch_hash(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate: dict[str, Any] = {}
    candidate_output: Path | None = None
    if mechanism_status == "PROMISING_NEEDS_FRESH_HOLDOUT":
        candidate = build_frozen_portfolio_candidate(
            report,
            source_files=source_files,
        )
        candidate_output = output.with_name(output.name.replace("portfolio_research_", "portfolio_candidate_"))
        atomic_write_json(candidate_output, candidate)
        report["frozen_candidate"] = {
            "status": candidate.get("status"),
            "candidate_hash": candidate.get("candidate_hash"),
            "artifact": str(candidate_output.resolve()),
            "authorization_state": candidate.get("authorization_state"),
        }
    atomic_write_json(output, report)
    experiment_completion = experiment_registry.complete(
        experiment_id=str(args.experiment_id),
        report_path=output,
        candidate_path=candidate_output,
        clock_attestation=attest_utc_clock(),
    )
    if experiment_completion.get("status") != "COMPLETED":
        print(json.dumps({
            "ok": False,
            "status": "BLOCK",
            "blockers": ["experiment_completion_failed"],
            "experiment_completion": experiment_completion,
            "report": str(output.resolve()),
            "candidate": str(candidate_output.resolve()) if candidate_output else "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    registry_audit = experiment_registry.audit()
    print(json.dumps({
        "mechanism_status": mechanism_status,
        "development_cutoff": cutoff,
        "validation_comparison": validation_comparison,
        "test_comparison": test_comparison,
        "causal_audit_status": causal_audit.get("status"),
        "temporal_exposure_status": temporal_exposure_audit.get("classification"),
        "prior_temporal_report_count": temporal_exposure_audit.get("prior_report_count"),
        "internal_backtest_admission": report["backtest_admission"].get("status"),
        "statistical_claim_status": report["backtest_admission"].get("statistical_claim_status"),
        "correlation_status": correlations.get("status"),
        "execution_rehearsal_status": execution_rehearsal.get("status"),
        "cost_stress": cost_stress,
        "paper_authorized": False,
        "live_order_allowed": False,
        "batch_run_hash": report["batch_run_hash"],
        "experiment_id": str(args.experiment_id),
        "experiment_completion_receipt_hash": str((experiment_completion.get("receipt") or {}).get("receipt_hash") or ""),
        "experiment_registry_audit": registry_audit.get("status"),
        "frozen_candidate": report.get("frozen_candidate", {}),
        "report": str(output.resolve()),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
