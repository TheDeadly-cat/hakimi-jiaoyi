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
    "tests.test_research_only_architecture.ResearchOnlyArchitectureTests",
    "tests.test_legacy_cli_boundary.LegacyCliBoundaryTests",
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
                "tests.test_strategy_correlation_cluster_gate.StrategyCorrelationClusterGateTests",
                "tests.test_strategy_correlation_cluster_common_support_gate_v2.StrategyCorrelationClusterCommonSupportGateV2Tests",
                "tests.test_strategy_correlation_common_support_derivation_receipt_v1.StrategyCorrelationCommonSupportDerivationReceiptV1Tests",
                "tests.test_strategy_correlation_common_support_calendar_provider_composition_v1.StrategyCorrelationCommonSupportCalendarProviderCompositionV1Tests",
                "tests.test_strategy_correlation_provider_dataset_content_attestation_v1.StrategyCorrelationProviderDatasetContentAttestationV1Tests",
                "tests.test_strategy_correlation_provider_dataset_key_lifecycle_gate_v1.StrategyCorrelationProviderDatasetKeyLifecycleGateV1Tests",
                "tests.test_strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1.StrategyCorrelationProviderDatasetKeyLifecycleReplayGateV1Tests",
                "tests.test_strategy_correlation_downside_tail_gate.StrategyCorrelationDownsideTailGateTests",
                "tests.test_strategy_correlation_downside_tail_report_consumer.StrategyCorrelationDownsideTailReportConsumerTests",
                "tests.test_strategy_correlation_downside_tail_protocol.StrategyCorrelationDownsideTailProtocolTests",
                "tests.test_strategy_correlation_downside_tail_public_projection.StrategyCorrelationDownsideTailPublicProjectionTests",
            "tests.test_strategy_correlation_cross_lag_gate.StrategyCorrelationCrossLagGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic.StrategyCorrelationCrossLagFactorConditionalDiagnosticTests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2.StrategyCorrelationCrossLagFactorConditionalDiagnosticV2Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_replay.StrategyCorrelationCrossLagFactorCalibrationReplayTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_report_consumer.StrategyCorrelationCrossLagFactorCalibrationReportConsumerTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_presentation_envelope.StrategyCorrelationCrossLagFactorCalibrationPresentationEnvelopeTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_stability_gate.StrategyCorrelationCrossLagFactorCalibrationStabilityGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate.StrategyCorrelationCrossLagFactorCalibrationResidualEnergyStabilityGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV2Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3.StrategyCorrelationCrossLagFactorCalibrationResidualOrderStabilityGateV3Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1.StrategyCorrelationCrossLagFactorCalibrationResidualOrderOmnibusGateV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonPreregistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationProtocolV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonFoldSchedulePreregistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarRegistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationBatchVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarSessionPresentationEnvelopeV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonCalendarBoundObservationAdmissionGateV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterRegistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAdapterRegistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityPresentationEnvelopeV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1.ProviderIdentityAssertionReplayAdapterRegistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_receipt_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayReceiptVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_registration_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceRegistrationV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_receipt_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceReceiptVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_binding_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceBindingV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceLineageV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceUniquenessFreshnessV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceUniquenessFreshnessLongitudinalCoverageV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityUniquenessFreshnessPresentationEnvelopeV1Tests",
            "tests.test_provider_identity_witness_conformance_key_governance_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityWitnessConformanceKeyGovernanceV1Tests",
            "tests.test_provider_identity_auditor_provenance_suite_reproducibility_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAuditorProvenanceSuiteReproducibilityV1Tests",
            "tests.test_provider_identity_artifact_transparency_availability_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityArtifactTransparencyAvailabilityV1Tests",
            "tests.test_provider_identity_artifact_transparency_presentation_envelope_v1.ProviderIdentityArtifactTransparencyPresentationEnvelopeV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1.StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterSignatureVerifierV1Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV2Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV3Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV4Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV5Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV6Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7.StrategyCorrelationCrossLagFactorCalibrationPrecommitGateV7Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV5Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV6Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7.StrategyCorrelationCrossLagFactorCalibrationPrecommitReportConsumerV7Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v4.StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeV4Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3.StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeV3Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2.StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeV2Tests",
            "tests.test_strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope.StrategyCorrelationCrossLagFactorCalibrationPrecommitPresentationEnvelopeTests",
            "tests.test_strategy_correlation_cross_lag_two_view_multiplicity_registration.StrategyCorrelationCrossLagTwoViewMultiplicityRegistrationTests",
            "tests.test_strategy_correlation_cross_lag_two_view_multiplicity_gate.StrategyCorrelationCrossLagTwoViewMultiplicityGateTests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_report_consumer.StrategyCorrelationCrossLagFactorConditionalReportConsumerTests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_report_consumer_v2.StrategyCorrelationCrossLagFactorConditionalReportConsumerV2Tests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_presentation_envelope.StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeTests",
            "tests.test_strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2.StrategyCorrelationCrossLagFactorConditionalPresentationEnvelopeV2Tests",
            "tests.test_strategy_correlation_cross_lag_report_consumer.StrategyCorrelationCrossLagReportConsumerTests",
            "tests.test_strategy_correlation_cross_lag_direction_contract.StrategyCorrelationCrossLagDirectionContractTests",
            "tests.test_strategy_correlation_cross_lag_registry_assignment_adapter.StrategyCorrelationCrossLagRegistryAssignmentAdapterTests",
            "tests.test_strategy_correlation_cross_lag_preregistration_adapter_binding.StrategyCorrelationCrossLagPreregistrationAdapterBindingTests",
            "tests.test_strategy_correlation_cross_lag_protocol.StrategyCorrelationCrossLagProtocolRegistrationTests",
            "tests.test_strategy_correlation_cross_lag_protocol_binding.StrategyCorrelationCrossLagProtocolBindingTests",
            "tests.test_strategy_correlation_cross_lag_public_projection.StrategyCorrelationCrossLagPublicProjectionTests",
            "tests.test_strategy_correlation_cross_lag_presentation_envelope.StrategyCorrelationCrossLagPresentationEnvelopeTests",
            "tests.test_strategy_correlation_cluster_complete_link.StrategyCorrelationClusterCompleteLinkTests",
                "tests.test_strategy_correlation_cluster_stability.StrategyCorrelationClusterStabilityTests",
            "tests.test_strategy_correlation_cluster_temporal_stability.StrategyCorrelationClusterTemporalStabilityTests",
            "tests.test_strategy_correlation_cluster_temporal_stability_report_consumer.StrategyCorrelationClusterTemporalStabilityReportConsumerTests",
            "tests.test_strategy_correlation_cluster_temporal_stability_protocol.StrategyCorrelationClusterTemporalStabilityProtocolTests",
            "tests.test_strategy_correlation_cluster_temporal_stability_migration_projection.StrategyCorrelationClusterTemporalStabilityMigrationProjectionTests",
            "tests.test_strategy_correlation_cluster_temporal_stability_report_binding.StrategyCorrelationClusterTemporalStabilityReportBindingTests",
            "tests.test_strategy_correlation_cluster_temporal_stability_report_binding_projection.StrategyCorrelationClusterTemporalStabilityReportBindingProjectionTests",
            "tests.test_strategy_correlation_cluster_stability_projection.StrategyCorrelationClusterStabilityProjectionTests",
                "tests.test_strategy_correlation_cluster_stability_report_consumer.StrategyCorrelationClusterStabilityReportConsumerTests",
                "tests.test_strategy_correlation_cluster_stability_protocol.StrategyCorrelationClusterStabilityProtocolTests",
                "tests.test_strategy_correlation_cluster_stability_protocol_projection.StrategyCorrelationClusterStabilityProtocolProjectionTests",
                "tests.test_strategy_correlation_cluster_stability_registry.StrategyCorrelationClusterStabilityRegistryTests",
                "tests.test_strategy_correlation_cluster_stability_registry_projection.StrategyCorrelationClusterStabilityRegistryProjectionTests",
                "tests.test_strategy_correlation_cluster_stability_formal_registry_adapter.StrategyCorrelationClusterStabilityFormalRegistryAdapterTests",
                "tests.test_strategy_correlation_cluster_stability_formal_persistence_protocol.StrategyCorrelationClusterStabilityFormalPersistenceProtocolTests",
                "tests.test_strategy_correlation_cluster_stability_formal_persistence_projection.StrategyCorrelationClusterStabilityFormalPersistenceProjectionTests",
                "tests.test_strategy_correlation_preregistered_strata.StrategyCorrelationPreregisteredStrataTests",
            "tests.test_strategy_correlation_strata_global_independence.StrategyCorrelationStrataGlobalIndependenceTests",
            "tests.test_strategy_correlation_global_independence_report_consumer.StrategyCorrelationGlobalIndependenceReportConsumerTests",
            "tests.test_strategy_correlation_global_independence_protocol.StrategyCorrelationGlobalIndependenceProtocolTests",
            "tests.test_strategy_correlation_global_independence_registry.StrategyCorrelationGlobalIndependenceRegistryTests",
            "tests.test_strategy_correlation_global_independence_registry_projection.StrategyCorrelationGlobalIndependenceRegistryProjectionTests",
            "tests.test_strategy_correlation_global_independence_protocol_projection.StrategyCorrelationGlobalIndependenceProtocolProjectionTests",
            "tests.test_strategy_correlation_strata_projection.StrategyCorrelationStrataProjectionTests",
            "tests.test_strategy_correlation_strata_registry.StrategyCorrelationStrataRegistryTests",
            "tests.test_strategy_correlation_strata_report_consumer.StrategyCorrelationStrataReportConsumerTests",
            "tests.test_strategy_correlation_strata_protocol.StrategyCorrelationStrataProtocolTests",
            "tests.test_strategy_correlation_strata_protocol_projection.StrategyCorrelationStrataProtocolProjectionTests",
            "tests.test_strict_research_authority.StrictResearchAuthorityTests",
            "tests.test_strategy_correlation_complete_link_report_consumer.StrategyCorrelationCompleteLinkReportConsumerTests",
    "tests.test_strategy_correlation_complete_link_protocol.StrategyCorrelationCompleteLinkProtocolTests",
    "tests.test_strategy_correlation_complete_link_registry_binding.StrategyCorrelationCompleteLinkRegistryBindingTests",
    "tests.test_strategy_correlation_complete_link_projection.StrategyCorrelationCompleteLinkProjectionTests",
            "tests.test_strict_canonical_json_hash.StrictCanonicalJsonHashTests",
                "tests.test_strict_json_contract.StrictJsonContractTests",
                "tests.test_strict_governance_primitives.StrictGovernancePrimitivesTests",
    "tests.test_strategy_correlation_return_replay.StrategyCorrelationReturnReplayTests",
        "tests.test_strategy_correlation_cluster_projection.StrategyCorrelationClusterProjectionTests",
        "tests.test_strategy_correlation_protocol_binding.StrategyCorrelationProtocolBindingTests",
        "tests.test_strategy_correlation_uncertainty_audit.StrategyCorrelationUncertaintyAuditTests",
            "tests.test_strategy_correlation_multiplicity_audit.StrategyCorrelationMultiplicityAuditTests",
            "tests.test_strategy_correlation_multiplicity_registration.StrategyCorrelationMultiplicityRegistrationTests",
            "tests.test_strategy_correlation_multiplicity_protocol.StrategyCorrelationMultiplicityProtocolTests",
            "tests.test_strategy_correlation_multiplicity_report.StrategyCorrelationMultiplicityReportTests",
            "tests.test_strategy_correlation_research_evidence.StrategyCorrelationResearchEvidenceTests",
            "tests.test_strategy_research_schema16.StrategyResearchSchema16Tests",
            "tests.test_strategy_matrix_multiplicity_report.StrategyMatrixMultiplicityReportTest",
                    "tests.test_strategy_correlation_multiplicity_projection.StrategyCorrelationMultiplicityProjectionTests",
                    "tests.test_strategy_correlation_multiplicity_projection.StrategyLabMultiplicityProjectionTests",
    "tests.test_market_data_envelope.MarketDataEnvelopeTest",
    "tests.test_market_data_envelope_integration.MarketDataEnvelopeLoaderIntegrationTest",
    "tests.test_market_data_envelope_server_integration.MarketDataEnvelopeServerIntegrationTest",
            "tests.test_strategy_correlation_multiplicity_registry.StrategyCorrelationMultiplicityRegistryTests",
            "tests.test_strategy_research_search_lineage_v2.StrategyResearchSearchLineageV2Tests",
            "tests.test_canonical_json_hash.CanonicalJsonHashTests",
        "tests.test_strategy_lab_correlation_projection.StrategyLabCorrelationProjectionTests",
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
                "exchange_terminal/services/strategy_correlation_cluster_gate.py",
                "exchange_terminal/services/strategy_correlation_cluster_common_support_gate_v2.py",
                "exchange_terminal/services/strategy_correlation_common_support_derivation_receipt_v1.py",
                "exchange_terminal/services/strategy_correlation_common_support_calendar_provider_composition_v1.py",
                "exchange_terminal/services/strategy_correlation_provider_dataset_content_attestation_v1.py",
                "exchange_terminal/services/strategy_correlation_provider_dataset_key_lifecycle_gate_v1.py",
                "exchange_terminal/services/strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1.py",
                "exchange_terminal/services/strategy_correlation_downside_tail_gate.py",
                "exchange_terminal/services/strategy_correlation_downside_tail_report_consumer.py",
                "exchange_terminal/services/strategy_correlation_downside_tail_protocol.py",
                "exchange_terminal/services/strategy_correlation_downside_tail_public_projection.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_diagnostic.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_diagnostic_v2.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_replay.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_report_consumer.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_presentation_envelope.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_stability_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_residual_energy_stability_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v2.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_residual_order_stability_gate_v3.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_residual_order_omnibus_gate_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_fold_schedule_preregistration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_batch_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_presentation_envelope_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_bound_observation_admission_gate_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_receipt_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_receipt_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_binding_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_registration_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1.py",
            "exchange_terminal/services/provider_identity_witness_conformance_key_governance_v1.py",
            "exchange_terminal/services/provider_identity_auditor_provenance_suite_reproducibility_v1.py",
            "exchange_terminal/services/provider_identity_artifact_transparency_availability_v1.py",
            "exchange_terminal/application/provider_identity_artifact_transparency_presentation_envelope_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v2.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v3.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v4.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v5.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v6.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_gate_v7.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v5.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v6.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_calibration_precommit_report_consumer_v7.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v4.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v3.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope_v2.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_calibration_precommit_presentation_envelope.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_two_view_multiplicity_registration.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_two_view_multiplicity_gate.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_factor_conditional_report_consumer_v2.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_conditional_presentation_envelope.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_factor_conditional_presentation_envelope_v2.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_direction_contract.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_registry_assignment_adapter.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_preregistration_adapter_binding.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_protocol.py",
            "exchange_terminal/services/strategy_correlation_cross_lag_public_projection.py",
            "exchange_terminal/application/strategy_correlation_cross_lag_presentation_envelope.py",
            "exchange_terminal/services/strategy_correlation_cluster_complete_link.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability_protocol.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability_migration_projection.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability_report_binding.py",
            "exchange_terminal/services/strategy_correlation_cluster_temporal_stability_report_binding_projection.py",
            "exchange_terminal/services/strategy_correlation_cluster_stability_projection.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_report_consumer.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_protocol.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_protocol_projection.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_registry.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_registry_projection.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_formal_registry_adapter.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_formal_persistence_protocol.py",
                "exchange_terminal/services/strategy_correlation_cluster_stability_formal_persistence_projection.py",
                "exchange_terminal/services/strategy_correlation_preregistered_strata.py",
            "exchange_terminal/services/strategy_correlation_strata_global_independence.py",
            "exchange_terminal/services/strategy_correlation_global_independence_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_global_independence_protocol.py",
            "exchange_terminal/services/strategy_correlation_global_independence_registry.py",
            "exchange_terminal/services/strategy_correlation_global_independence_registry_projection.py",
            "exchange_terminal/services/strategy_correlation_global_independence_protocol_projection.py",
            "exchange_terminal/services/strategy_correlation_strata_projection.py",
            "exchange_terminal/services/strategy_correlation_strata_registry.py",
            "exchange_terminal/services/strategy_correlation_strata_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_strata_protocol.py",
            "exchange_terminal/services/strategy_correlation_strata_protocol_projection.py",
            "exchange_terminal/services/strict_research_authority.py",
            "exchange_terminal/services/strategy_correlation_complete_link_report_consumer.py",
            "exchange_terminal/services/strategy_correlation_complete_link_protocol.py",
            "exchange_terminal/services/strategy_correlation_complete_link_registry_binding.py",
            "exchange_terminal/services/strategy_correlation_complete_link_projection.py",
                "exchange_terminal/services/strict_canonical_json_hash.py",
                "exchange_terminal/services/strict_governance_primitives.py",
            "exchange_terminal/services/strategy_correlation_return_replay.py",
        "exchange_terminal/services/strategy_correlation_cluster_projection.py",
        "exchange_terminal/services/strategy_correlation_protocol_binding.py",
        "exchange_terminal/services/strategy_correlation_uncertainty_audit.py",
            "exchange_terminal/services/strategy_correlation_multiplicity_audit.py",
            "exchange_terminal/services/strategy_correlation_multiplicity_registration.py",
            "exchange_terminal/services/strategy_correlation_multiplicity_protocol.py",
            "exchange_terminal/services/strategy_correlation_multiplicity_report.py",
            "exchange_terminal/services/strategy_correlation_research_evidence.py",
                "exchange_terminal/services/strategy_matrix_multiplicity_report.py",
                "exchange_terminal/services/strategy_correlation_multiplicity_projection.py",
            "exchange_terminal/application/market_data_envelope.py",
            "exchange_terminal/services/canonical_json_hash.py",
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
                "exchange_terminal/static/evidence_presentation_suite_v13.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify neutral evidence wording, frozen return/strategy evidence fail-closed mapping, and static source boundaries.",
    ),
    Check(
        "frontend-cross-lag-evidence-card",
        (
            "{node}",
            "exchange_terminal/static/cross_lag_evidence_card.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted four-axis cross-lag card, strict-canonical integrity, redaction, responsive CSS, and locked authority.",
    ),
    Check(
        "frontend-factor-conditional-evidence-card",
        (
            "{node}",
            "exchange_terminal/static/factor_conditional_evidence_card.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted factor-conditional ledger, Python-envelope integrity, neutral four-axis copy, detached rendering, scoped responsive CSS, and locked authority.",
    ),
    Check(
        'frontend-factor-conditional-evidence-card-v2',
        (
            "{node}",
            'exchange_terminal/static/factor_conditional_evidence_card_v2.test.js',
        ),
        ("frontend", "research", "core"),
        'Verify the unmounted global-family factor-conditional atlas, Python-envelope integrity, four-axis neutral copy, safe detached DOM rendering, scoped responsive CSS, and locked authority.',
    ),
    Check(
        "frontend-factor-calibration-evidence-card",
        (
            "{node}",
            "exchange_terminal/static/factor_calibration_evidence_card.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted calibration replay card, shared strict-canonical integrity, five-state mapping, aggregate privacy, responsive CSS, detached rendering, and locked authority.",
    ),
    Check(
        "frontend-factor-calibration-precommit-evidence-card",
        (
            "{node}",
            "exchange_terminal/static/factor_calibration_precommit_evidence_card.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted precommit and beta-stability instrument, strict-canonical integrity, monotone state mapping, aggregate privacy, responsive CSS, detached rendering, and locked authority.",
    ),
    Check(
        "frontend-factor-calibration-precommit-evidence-card-v2",
        (
            "{node}",
            "exchange_terminal/static/factor_calibration_precommit_evidence_card_v2.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted multi-lag phase-comb instrument, cross-language envelope integrity, aggregate-only privacy, neutral four-axis copy, responsive CSS, detached rendering, and locked authority.",
    ),
    Check(
        "frontend-factor-calibration-precommit-evidence-card-v3",
        (
            "{node}",
            "exchange_terminal/static/factor_calibration_precommit_evidence_card_v3.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the unmounted three-lag phase-comb instrument, exact envelope-v3 keys and hash cross-binding, aggregate-only privacy, neutral four-axis copy, responsive CSS, detached rendering, and locked authority.",
    ),
    Check(
        "frontend-factor-calibration-precommit-evidence-card-v4",
        (
            "{node}",
            "exchange_terminal/static/factor_calibration_precommit_evidence_card_v4.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the detached six-lag finite-horizon instrument, exact envelope-v4 keys and source hash cross-binding, dual-band Q guard, aggregate privacy, neutral four-axis copy, responsive CSS, safe detached rendering, and locked authority.",
    ),
    Check(
        "frontend-calendar-session-evidence-card-v1",
        (
            "{node}",
            "exchange_terminal/static/calendar_session_evidence_card_v1.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the detached calendar-session timetable ledger, strict envelope integrity, canonical/common-session aggregates, neutral four-axis copy, responsive reduced-motion CSS, safe rendering, and locked authority.",
    ),
    Check(
        "frontend-provider-identity-evidence-card-v1",
        (
            "{node}",
            "exchange_terminal/static/provider_identity_evidence_card_v1.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the detached provider-identity dossier, sealed envelope integrity, signature/membership aggregates, external-trust gap, neutral four-axis copy, scoped responsive CSS, safe rendering, and locked authority.",
    ),
    Check(
        "frontend-provider-identity-claim-coverage-card-v1",
        (
            "{node}",
            "exchange_terminal/static/provider_identity_claim_coverage_card_v1.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the detached signed-claim coverage ledger, bounded-prefix rail, external-trust gap, neutral four-axis copy, scoped responsive CSS, safe DOM rendering, and locked authority.",
    ),
    Check(
        "frontend-provider-identity-artifact-transparency-card-v1",
        (
            "{node}",
            "exchange_terminal/static/provider_identity_artifact_transparency_card_v1.test.js",
        ),
        ("frontend", "research", "core"),
        "Verify the detached artifact-transparency observatory, local-content/external-availability separation, exact aggregate arithmetic, neutral four-axis copy, scoped responsive CSS, safe DOM rendering, and locked authority.",
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
