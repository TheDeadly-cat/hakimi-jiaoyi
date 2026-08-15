from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
import unittest

from exchange_terminal.services.backtest_return_quality import (
    BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
    BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
    CURRENT_BACKTEST_RETURN_QUALITY_SCHEMA_VERSION,
    PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
    PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
    build_backtest_return_quality_projection,
)
from exchange_terminal.services.portfolio_backtest_pack import (
    PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
    assemble_internal_backtest_pack,
    canonical_hash,
    verify_internal_backtest_pack,
)


def research_report() -> dict[str, object]:
    return {
        "mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "fresh_holdout_required": True,
        "forward_observation_required": True,
        "spec": {
            "fee_rate": 0.0005,
            "slippage_bps": 2.0,
            "cost_stress_contract": [
                {"label": "MODERATE", "fee_rate": 0.001, "slippage_bps": 5.0},
                {"label": "SEVERE", "fee_rate": 0.002, "slippage_bps": 10.0},
            ],
        },
        "validation": {
            "total_return_pct": 8.0,
            "max_drawdown_pct": 6.0,
            "evaluation_window": {"evaluated_rows": 180},
            "order_event_count": 12,
            "decision_event_count": 20,
        },
        "validation_benchmark": {
            "total_return_pct": 5.0,
            "max_drawdown_pct": 9.0,
        },
        "validation_comparison": {"excess_return_pct": 3.0},
        "test": {
            "total_return_pct": 6.0,
            "max_drawdown_pct": 7.0,
            "run_spec": {"fee_rate": 0.0005, "slippage_bps": 2.0},
            "evaluation_window": {"evaluated_rows": 220},
            "order_event_count": 15,
            "decision_event_count": 24,
        },
        "test_benchmark": {
            "total_return_pct": 4.0,
            "max_drawdown_pct": 10.0,
        },
        "test_comparison": {"excess_return_pct": 2.0},
        "cost_stress": [
            {
                "label": "MODERATE",
                "fee_rate": 0.001,
                "slippage_bps": 5.0,
                "ok": True,
                "total_return_pct": 4.5,
                "max_drawdown_pct": 7.5,
            },
            {
                "label": "SEVERE",
                "fee_rate": 0.002,
                "slippage_bps": 10.0,
                "ok": True,
                "total_return_pct": 2.0,
                "max_drawdown_pct": 8.0,
            },
        ],
        "development_checks": {
            "validation_positive": True,
            "test_positive": True,
            "severe_cost_test_positive": True,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def statistical_audit() -> dict[str, object]:
    return {
        "status": "PASS",
        "stages": {
            "validation": {
                "status": "PASS",
                "blockers": [],
                "observation_count": 179,
                "observed": {
                    "strategy_compound_return_pct": 8.0,
                    "benchmark_compound_return_pct": 5.0,
                    "compound_excess_return_pct": 3.0,
                },
            },
            "test": {
                "status": "PASS",
                "blockers": [],
                "observation_count": 219,
                "observed": {
                    "strategy_compound_return_pct": 6.0,
                    "benchmark_compound_return_pct": 4.0,
                    "compound_excess_return_pct": 2.0,
                },
            },
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def seal_pack(payload: dict[str, object]) -> dict[str, object]:
    sealed = deepcopy(payload)
    sealed.pop("pack_hash", None)
    sealed.pop("evidence_hash", None)
    evidence = deepcopy(sealed)
    evidence.pop("generated_at", None)
    sealed["evidence_hash"] = canonical_hash(evidence)
    sealed["pack_hash"] = canonical_hash(sealed)
    return sealed


class BacktestReturnQualityTests(unittest.TestCase):
    def test_v2_is_v1_superset_and_binds_portfolio_source_identity(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        identity = {
            "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
            "source_artifact_family": PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
            "strategy_schema7_preregistration_status": "NOT_APPLICABLE",
            "candidate_hash": "1" * 64,
            "candidate_research_report_hash": "2" * 64,
            "candidate_spec_hash": "3" * 64,
            "research_batch_run_hash": "2" * 64,
            "research_spec_hash": "3" * 64,
            "research_generation": "PORTFOLIO_SYNTHETIC",
            "research_protocol_hash": "4" * 64,
            "implementation_fingerprint": "5" * 64,
            "research_file_sha256": "6" * 64,
            "statistical_audit_schema_version": "portfolio-statistical-audit-v3",
            "statistical_audit_hash": "7" * 64,
            "statistical_input_binding_hash": "8" * 64,
            "research_source_document_sha256": "a" * 64,
            "backtest_result_evidence_hash": "b" * 64,
            "experiment_completion_receipt_hash": "c" * 64,
            "active_candidate_registry_hash": "d" * 64,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        identity["identity_hash"] = canonical_hash(identity)

        legacy = build_backtest_return_quality_projection(research, statistical)
        current = build_backtest_return_quality_projection(
            research,
            statistical,
            schema_version=BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
            source_identity=identity,
            source_evidence_hash="9" * 64,
        )

        self.assertEqual(current["schema_version"], BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION)
        self.assertEqual(current["source_identity"], identity)
        self.assertEqual(current["source_evidence_hash"], "9" * 64)
        for field in legacy:
            if field != "schema_version":
                self.assertEqual(current[field], legacy[field])

    def test_v2_rejects_schema7_claim_and_nested_authority(self) -> None:
        identity = {
            "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
            "source_artifact_family": PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
            "strategy_schema7_preregistration_status": "PASS",
            "candidate_hash": "1" * 64,
            "candidate_research_report_hash": "2" * 64,
            "candidate_spec_hash": "3" * 64,
            "research_batch_run_hash": "2" * 64,
            "research_spec_hash": "3" * 64,
            "research_generation": "PORTFOLIO_SYNTHETIC",
            "research_protocol_hash": "4" * 64,
            "implementation_fingerprint": "5" * 64,
            "research_file_sha256": "6" * 64,
            "statistical_audit_schema_version": "portfolio-statistical-audit-v3",
            "statistical_audit_hash": "7" * 64,
            "statistical_input_binding_hash": "8" * 64,
            "research_source_document_sha256": "a" * 64,
            "backtest_result_evidence_hash": "b" * 64,
            "experiment_completion_receipt_hash": "c" * 64,
            "active_candidate_registry_hash": "d" * 64,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "nested": {"direction_signal_allowed": True},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        identity["identity_hash"] = canonical_hash(identity)

        result = build_backtest_return_quality_projection(
            research_report(),
            statistical_audit(),
            schema_version=BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
            source_identity=identity,
            source_evidence_hash="9" * 64,
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn(
            "return_quality_strategy_schema7_scope_invalid",
            result["failure_conditions"]["source_integrity"],
        )
        self.assertTrue(any(
            "direction_signal_allowed" in item
            for item in result["failure_conditions"]["source_integrity"]
        ))

    def test_authority_aliases_fail_closed_in_standalone_quality_builder(self) -> None:
        for key in (
            "Paper_Authorized",
            "canTrade",
            "parameter-selection-authority",
        ):
            with self.subTest(key=key):
                research = research_report()
                research["nested"] = (
                    MappingProxyType({key: True}),
                )

                result = build_backtest_return_quality_projection(
                    research,
                    statistical_audit(),
                )

                self.assertEqual(result["status"], "BLOCK")
                self.assertTrue(any(
                    key in blocker
                    for blocker in result["failure_conditions"]["source_integrity"]
                ))

    def test_v2_source_integrity_block_redacts_all_numeric_claims(self) -> None:
        identity = {
            "schema_version": PORTFOLIO_RETURN_QUALITY_SOURCE_IDENTITY_SCHEMA_VERSION,
            "source_artifact_family": PORTFOLIO_RESEARCH_SOURCE_ARTIFACT_FAMILY,
            "strategy_schema7_preregistration_status": "NOT_APPLICABLE",
            "candidate_hash": "1" * 64,
            "candidate_research_report_hash": "2" * 64,
            "candidate_spec_hash": "3" * 64,
            "research_batch_run_hash": "2" * 64,
            "research_spec_hash": "3" * 64,
            "research_generation": "PORTFOLIO_SYNTHETIC",
            "research_protocol_hash": "4" * 64,
            "implementation_fingerprint": "5" * 64,
            "research_file_sha256": "6" * 64,
            "statistical_audit_schema_version": "portfolio-statistical-audit-v3",
            "statistical_audit_hash": "7" * 64,
            "statistical_input_binding_hash": "8" * 64,
            "research_source_document_sha256": "a" * 64,
            "backtest_result_evidence_hash": "b" * 64,
            "experiment_completion_receipt_hash": "c" * 64,
            "active_candidate_registry_hash": "d" * 64,
            "external_anchor_verified": False,
            "cryptographic_authenticity_proven": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        identity["identity_hash"] = canonical_hash(identity)

        result = build_backtest_return_quality_projection(
            research_report(),
            statistical_audit(),
            schema_version=BACKTEST_RETURN_QUALITY_V2_SCHEMA_VERSION,
            source_identity=identity,
            source_evidence_hash="9" * 64,
            verified_source_integrity_status="BLOCK",
            verified_source_integrity_blockers=["equity_curve_return_mismatch"],
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["source_integrity_status"], "BLOCK")
        self.assertFalse(result["numeric_claims_available"])
        self.assertIn(
            "equity_curve_return_mismatch",
            result["failure_conditions"]["source_integrity"],
        )
        for field in (
            "strategy_return_pct",
            "benchmark_return_pct",
            "benchmark_excess_return_pct",
            "cost_after_return_pct",
            "worst_stress_return_pct",
            "max_drawdown_pct",
            "sample_size",
        ):
            self.assertIsNone(result["summary"][field])
        self.assertEqual(result["summary"]["benchmark_excess_status"], "UNKNOWN")
        self.assertEqual(result["summary"]["cost_after_status"], "UNKNOWN")
        self.assertEqual(result["cost_after"]["stress_scenarios"], [])

    def test_complete_projection_exposes_quality_without_profit_or_trade_authority(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        before_research = deepcopy(research)
        before_statistical = deepcopy(statistical)

        result = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(result["schema_version"], BACKTEST_RETURN_QUALITY_SCHEMA_VERSION)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["summary"]["benchmark_excess_return_pct"], 2.0)
        self.assertEqual(
            result["stages"]["test"]["benchmark_excess_basis"],
            "RECOMPUTED_FROM_STRATEGY_AND_BENCHMARK_RETURNS",
        )
        self.assertEqual(result["summary"]["cost_after_return_pct"], 6.0)
        self.assertEqual(
            result["cost_after"]["baseline_model"]["cost_binding_basis"],
            "TEST_RUN_SPEC_MATCHES_FROZEN_RESEARCH_SPEC",
        )
        self.assertEqual(result["summary"]["worst_stress_return_pct"], 2.0)
        self.assertEqual(result["summary"]["max_drawdown_pct"], 7.0)
        self.assertEqual(result["summary"]["sample_size"], 219)
        self.assertEqual(result["summary"]["evidence_stage"], "DEVELOPMENT_HISTORICAL")
        self.assertIn(
            "fresh_untouched_holdout_required",
            result["failure_conditions"]["promotion_gaps"],
        )
        self.assertFalse(result["profitability_proven"])
        self.assertFalse(result["performance_claim_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertEqual(research, before_research)
        self.assertEqual(statistical, before_statistical)

    def test_missing_benchmark_and_sample_remain_unknown_instead_of_zero(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research.pop("test_benchmark")
        research.pop("test_comparison")
        statistical["stages"]["test"].pop("observation_count")

        result = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIsNone(result["summary"]["benchmark_return_pct"])
        self.assertIsNone(result["summary"]["benchmark_excess_return_pct"])
        self.assertEqual(result["summary"]["benchmark_excess_status"], "UNKNOWN")
        self.assertEqual(result["summary"]["sample_size"], 220)
        self.assertEqual(result["summary"]["sample_unit"], "EVALUATED_ROWS")
        self.assertIn(
            "test_benchmark_return_unknown",
            result["failure_conditions"]["evidence_gaps"],
        )
        self.assertIn(
            "test_benchmark_excess_unknown",
            result["failure_conditions"]["evidence_gaps"],
        )

    def test_reported_excess_without_benchmark_is_not_presented_as_recomputed(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research.pop("test_benchmark")

        result = build_backtest_return_quality_projection(research, statistical)
        test_stage = result["stages"]["test"]

        self.assertEqual(result["status"], "PARTIAL")
        self.assertIsNone(result["summary"]["benchmark_excess_return_pct"])
        self.assertEqual(test_stage["reported_benchmark_excess_return_pct"], 2.0)
        self.assertEqual(test_stage["benchmark_excess_status"], "UNKNOWN")
        self.assertEqual(test_stage["benchmark_excess_basis"], "REPORTED_ONLY_NOT_USED")
        self.assertIn(
            "test_benchmark_excess_unknown",
            result["failure_conditions"]["evidence_gaps"],
        )

    def test_configured_cost_return_requires_test_run_spec_binding(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research["test"].pop("run_spec")

        unknown = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(unknown["status"], "PARTIAL")
        self.assertIsNone(unknown["summary"]["cost_after_return_pct"])
        self.assertEqual(unknown["cost_after"]["baseline_model"]["status"], "UNKNOWN")
        self.assertEqual(
            unknown["cost_after"]["baseline_model"]["cost_binding_basis"],
            "TEST_RUN_SPEC_NOT_VERIFIABLE",
        )
        self.assertIn(
            "configured_cost_test_run_binding_unknown",
            unknown["failure_conditions"]["evidence_gaps"],
        )

        research = research_report()
        research["test"]["run_spec"]["fee_rate"] = 0.009
        mismatch = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(mismatch["status"], "BLOCK")
        self.assertIsNone(mismatch["summary"]["cost_after_return_pct"])
        self.assertEqual(mismatch["cost_after"]["baseline_model"]["status"], "BLOCK")
        self.assertIn(
            "configured_cost_test_run_binding_mismatch",
            mismatch["failure_conditions"]["observed"],
        )

    def test_statistical_block_and_losing_stress_are_explicit_failure_conditions(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research["cost_stress"][1]["total_return_pct"] = -1.0
        research["development_checks"]["severe_cost_test_positive"] = False
        statistical["status"] = "BLOCK"
        statistical["stages"]["test"]["status"] = "BLOCK"
        statistical["stages"]["test"]["blockers"] = ["bootstrap_probability"]

        result = build_backtest_return_quality_projection(research, statistical)
        failures = result["failure_conditions"]["observed"]

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["cost_after"]["status"], "BLOCK")
        self.assertIn("historical_statistical_claim_block", failures)
        self.assertIn("test_statistical_claim_block", failures)
        self.assertIn("cost_stress_return_not_positive:SEVERE", failures)
        self.assertIn("development_check_failed:severe_cost_test_positive", failures)
        self.assertFalse(result["profitability_proven"])

    def test_stress_returns_require_frozen_contract_identity(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research["cost_stress"][1]["slippage_bps"] = 99.0

        mismatch = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(mismatch["status"], "BLOCK")
        self.assertEqual(mismatch["cost_after"]["stress_scenarios"][1]["status"], "BLOCK")
        self.assertIsNone(mismatch["cost_after"]["stress_scenarios"][1]["return_pct"])
        self.assertEqual(mismatch["cost_after"]["stress_scenarios"][1]["declared_return_pct"], 2.0)
        self.assertIsNone(mismatch["summary"]["worst_stress_return_pct"])
        self.assertIn(
            "cost_stress_contract_mismatch:SEVERE",
            mismatch["failure_conditions"]["observed"],
        )

        research = research_report()
        research["spec"].pop("cost_stress_contract")
        unknown = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(unknown["status"], "PARTIAL")
        self.assertIsNone(unknown["summary"]["worst_stress_return_pct"])
        self.assertEqual(unknown["cost_after"]["stress_contract"]["status"], "UNKNOWN")
        self.assertIn(
            "cost_stress_contract_unknown",
            unknown["failure_conditions"]["evidence_gaps"],
        )

    def test_nested_authority_cannot_upgrade_projection(self) -> None:
        research = research_report()
        statistical = statistical_audit()
        research["test"]["nested"] = {
            "live_order_allowed": True,
            "execution_allowed": "true",
        }
        statistical["stages"]["test"]["paper_authorized"] = True

        result = build_backtest_return_quality_projection(research, statistical)

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["failure_conditions"]["source_integrity"])
        self.assertTrue(
            any(
                "execution_allowed" in item
                for item in result["failure_conditions"]["source_integrity"]
            )
        )

    def test_pack_integration_is_hash_bound_and_legacy_pack_remains_valid(self) -> None:
        legacy = seal_pack(
            {
                "schema_version": PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
                "status": "INTERNAL_BACKTEST_EVIDENCE_READY",
                "promotion_status": "BLOCK",
                "blockers": [],
                "promotion_blockers": ["fresh_holdout_required"],
                "checks": {"evidence": True},
                "generated_at": 100,
                "source_mode": "FROZEN_ARTIFACT_VERIFICATION_ONLY",
                "parameter_selection_allowed": False,
                "automatic_paper_activation_allowed": False,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        )
        self.assertEqual(verify_internal_backtest_pack(legacy)["status"], "PASS")

        assembled = assemble_internal_backtest_pack(
            {"research": research_report(), "statistical": statistical_audit()},
            generated_at=100,
            schema_version=PORTFOLIO_INTERNAL_BACKTEST_PACK_SCHEMA_VERSION,
        )
        self.assertEqual(assembled["return_quality"]["status"], "AVAILABLE")
        self.assertEqual(verify_internal_backtest_pack(assembled)["status"], "PASS")

        tampered = deepcopy(assembled)
        tampered["return_quality"]["summary"]["benchmark_excess_return_pct"] = 999.0
        verification = verify_internal_backtest_pack(tampered)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("backtest_pack_hash_invalid", verification["blockers"])
        self.assertIn("backtest_pack_evidence_hash_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
