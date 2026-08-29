from __future__ import annotations

import copy
import itertools
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_admission import (
    build_research_universe_contract,
)
from exchange_terminal.services.portfolio_correlation_admission_v1 import (
    SCHEMA_VERSION,
    build_portfolio_correlation_admission_v1,
    verify_portfolio_correlation_admission_v1,
)
from exchange_terminal.services.provider_governance import (
    build_unassessed_provider_governance_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    evaluate_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from tests.portfolio_governance_fixtures import experiment_binding


def synthetic_report() -> dict:
    return {
        "mechanism_status": "PROMISING_NEEDS_FRESH_HOLDOUT",
        "dataset_manifest": {"status": "PASS"},
        "validation": {"ok": True},
        "test": {"ok": True},
        "full": {"ok": True},
        "causal_audit": {"status": "PASS"},
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
        "universe_contract": build_research_universe_contract(
            benchmark_symbol="SPY",
            tradable_symbols=["AAA", "BBB"],
            declared_at="2026-08-01T00:00:00+00:00",
            selection_basis="STATIC_SYNTHETIC_FIXTURE",
        ),
        "temporal_exposure_audit": {
            "audit_hash": "1" * 64,
            "status": "BLOCK",
            "fresh_holdout_eligible": False,
        },
        "experiment_governance": experiment_binding(),
        "provider_governance": build_unassessed_provider_governance_contract(
            provider_ids=["synthetic-provider"],
            generated_at="2026-08-01T00:00:00Z",
        ),
    }


class FlippingMapping(dict):
    """A non-native mapping that must be rejected before a second read matters."""


class PortfolioCorrelationAdmissionV1Tests(unittest.TestCase):
    def _evidence(
        self,
        *,
        correlation: float = 0.10,
        shared_stratum: bool = False,
    ) -> dict:
        symbols = ("AAA", "BBB")
        preregistration = build_correlation_cluster_preregistration([
            {"cluster_id": "cluster-aaa", "members": ["AAA"]},
            {"cluster_id": "cluster-bbb", "members": ["BBB"]},
        ])
        matrix = build_correlation_matrix_contract(
            list(symbols),
            {pair: correlation for pair in itertools.combinations(symbols, 2)},
            overlap_observations=60,
        )
        cells = [
            {
                "strategy_id": "strategy-1",
                "variant_id": "variant-1",
                "symbol": symbol,
                "lane": "RAW_EXCESS",
                "gate_status": "PASS",
            }
            for symbol in symbols
        ]
        complete_link_gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            matrix,
            cells,
            strategy_id="strategy-1",
            variant_id="variant-1",
            lane="RAW_EXCESS",
        )
        strata = (
            [{
                "stratum_id": "shared-sector",
                "cluster_ids": ["cluster-aaa", "cluster-bbb"],
            }]
            if shared_stratum
            else [
                {"stratum_id": "family-aaa", "cluster_ids": ["cluster-aaa"]},
                {"stratum_id": "family-bbb", "cluster_ids": ["cluster-bbb"]},
            ]
        )
        if complete_link_gate["status"] == "PASS":
            strata_preregistration = build_strategy_correlation_strata_preregistration(
                preregistration,
                [{"dimension_id": "asset-family", "strata": strata}],
            )
            strata_gate = evaluate_strategy_correlation_strata_gate(
                strata_preregistration,
                complete_link_gate,
                source_preregistration=preregistration,
            )
        else:
            strata_preregistration = None
            strata_gate = None
        return {
            "report_document": synthetic_report(),
            "correlation_preregistration_document": preregistration,
            "correlation_matrix_document": matrix,
            "selection_cells_document": cells,
            "complete_link_gate_document": complete_link_gate,
            "strata_preregistration_document": strata_preregistration,
            "strata_gate_document": strata_gate,
            "strategy_id": "strategy-1",
            "variant_id": "variant-1",
            "lane": "RAW_EXCESS",
        }

    def test_exact_low_correlation_independent_strata_pass_research_admission(self):
        evidence = self._evidence()
        candidate = build_portfolio_correlation_admission_v1(**evidence)
        verification = verify_portfolio_correlation_admission_v1(
            candidate,
            **evidence,
        )

        self.assertEqual(candidate["schema_version"], SCHEMA_VERSION)
        self.assertEqual(candidate["status"], "PASS")
        self.assertIsNone(candidate["first_blocking_tier"])
        self.assertEqual(candidate["complete_link_status"], "PASS")
        self.assertEqual(candidate["strata_preregistration_status"], "PASS")
        self.assertEqual(candidate["strata_gate_status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["candidate_status"], "PASS")

    def test_highly_correlated_separate_clusters_cannot_count_as_independent(self):
        evidence = self._evidence(correlation=0.90)
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "COMPLETE_LINK")
        self.assertIn("complete_link_gate_blocked", candidate["blockers"])
        self.assertEqual(candidate["complete_link_status"], "BLOCK")
        self.assertEqual(
            candidate["strata_preregistration_status"],
            "NOT_EVALUATED",
        )
        self.assertEqual(candidate["strata_gate_status"], "NOT_EVALUATED")
        self.assertIsNone(candidate["checks"]["strata_preregistration_exact"])
        self.assertIsNone(candidate["checks"]["strata_gate_exact"])

    def test_shared_preregistered_stratum_collapses_two_cluster_votes(self):
        evidence = self._evidence(shared_stratum=True)
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(candidate["complete_link_status"], "PASS")
        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "STRATA_GATE")
        self.assertIn("strata_gate_blocked", candidate["blockers"])

    def test_missing_correlation_preregistration_fails_closed(self):
        evidence = self._evidence()
        evidence["correlation_preregistration_document"] = {}
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(
            candidate["first_blocking_tier"],
            "CORRELATION_PREREGISTRATION",
        )

    def test_matrix_reseal_without_gate_rebuild_is_rejected(self):
        evidence = self._evidence()
        matrix = copy.deepcopy(evidence["correlation_matrix_document"])
        matrix["pairs"][0]["pearson_correlation"] = 0.90
        matrix["matrix_hash"] = strict_canonical_hash({
            key: value for key, value in matrix.items() if key != "matrix_hash"
        })
        evidence["correlation_matrix_document"] = matrix
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertTrue(candidate["checks"]["correlation_matrix_exact"])
        self.assertFalse(candidate["checks"]["complete_link_gate_exact"])
        self.assertEqual(candidate["first_blocking_tier"], "COMPLETE_LINK")

    def test_base_report_authority_promotion_blocks_before_correlation(self):
        evidence = self._evidence()
        evidence["report_document"]["paper_authorized"] = True
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "BASE_ADMISSION")
        self.assertFalse(candidate["checks"]["base_admission_exact"])
        self.assertFalse(candidate["checks"]["evidence_has_no_execution_authority"])

    def test_resealed_candidate_permission_promotion_fails_exact_verification(self):
        evidence = self._evidence()
        candidate = build_portfolio_correlation_admission_v1(**evidence)
        promoted = copy.deepcopy(candidate)
        promoted["permissions"]["paper_authorized"] = True
        promoted.pop("correlation_admission_hash")
        promoted["correlation_admission_hash"] = strict_canonical_hash(promoted)

        verification = verify_portfolio_correlation_admission_v1(
            promoted,
            **evidence,
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "correlation_admission_not_exact_rebuild",
            verification["blockers"],
        )
        self.assertIn(
            "correlation_admission_has_execution_authority",
            verification["blockers"],
        )

    def test_non_native_mapping_is_rejected_at_snapshot_boundary(self):
        evidence = self._evidence()
        evidence["correlation_matrix_document"] = FlippingMapping(
            evidence["correlation_matrix_document"]
        )
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(candidate["first_blocking_tier"], "INPUT_SNAPSHOT")
        self.assertEqual(candidate["blockers"], ["evidence_snapshot_failed"])

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self):
        evidence = self._evidence()
        before = copy.deepcopy(evidence)
        first = build_portfolio_correlation_admission_v1(**evidence)
        second = build_portfolio_correlation_admission_v1(**evidence)

        self.assertEqual(first, second)
        self.assertEqual(evidence, before)

    def test_candidate_contains_hashes_not_raw_evidence(self):
        evidence = self._evidence()
        candidate = build_portfolio_correlation_admission_v1(**evidence)

        self.assertFalse(candidate["raw_report_embedded"])
        self.assertFalse(candidate["raw_correlation_evidence_embedded"])
        self.assertNotIn("report_document", candidate)
        self.assertNotIn("selection_cells_document", candidate)
        self.assertTrue(all(candidate["evidence_hashes"].values()))

    def test_blocked_candidate_can_verify_integrity_without_promotion(self):
        evidence = self._evidence(correlation=0.90)
        candidate = build_portfolio_correlation_admission_v1(**evidence)
        verification = verify_portfolio_correlation_admission_v1(
            candidate,
            **evidence,
        )

        self.assertEqual(candidate["status"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["candidate_status"], "BLOCK")

    def test_all_execution_and_activation_authority_remains_locked(self):
        candidate = build_portfolio_correlation_admission_v1(**self._evidence())

        self.assertTrue(candidate["consumer_only"])
        self.assertFalse(candidate["current_writer_activation_allowed"])
        self.assertFalse(candidate["current_admission_allowed"])
        self.assertFalse(candidate["automatic_internal_backtest_activation_allowed"])
        self.assertEqual(candidate["paper_admission_status"], "BLOCKED")
        self.assertFalse(candidate["permissions"]["paper_authorized"])
        self.assertFalse(candidate["permissions"]["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
