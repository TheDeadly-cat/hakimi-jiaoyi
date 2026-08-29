from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_binding_v1 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_portfolio_correlation_admission_v2 as admission_v2_tests
from tests import (
    test_strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3_tests,
)


ROOT = Path(__file__).resolve().parents[1]


class _DictSubclass(dict):
    pass


class PortfolioCorrelationAdmissionEffectiveBudgetBindingV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.admission_case = (
            admission_v2_tests.PortfolioCorrelationAdmissionV2Tests()
        )
        self.admission_case.setUp()
        self.budget_case = (
            budget_v3_tests.StrategyCorrelationClusterEffectiveBetBudgetV3Tests()
        )
        self.budget_case.setUp()

        (
            self.strata_registration,
            self.strata_gate,
            self.complete_link_gate,
        ) = self.budget_case._strata_sources(shared=False)
        self.evidence = self.admission_case._replace_universe(
            self.admission_case._evidence(),
            list(self.budget_case.preregistration["symbols"]),
            selection_basis="SYNTHETIC_SHARED_SOURCE_BINDING",
        )
        self.evidence.update(
            {
                "correlation_preregistration_document": (
                    self.budget_case.preregistration
                ),
                "correlation_matrix_document": self.budget_case.matrix,
                "selection_cells_document": self.budget_case.cells,
                "complete_link_gate_document": self.complete_link_gate,
                "strata_preregistration_document": self.strata_registration,
                "strata_gate_document": self.strata_gate,
                "strategy_id": self.budget_case.cells[0]["strategy_id"],
                "variant_id": self.budget_case.cells[0]["variant_id"],
                "lane": self.budget_case.cells[0]["lane"],
            }
        )
        self.inputs = copy.deepcopy(self.budget_case.base_inputs)
        self.admission = self.admission_case._build(self.evidence)
        self.budget = self._build_budget(self.inputs)
        self.binding = self._build_binding()

    def _build_budget(self, inputs: dict) -> dict:
        return budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
            self.budget_case.preregistration,
            self.budget_case.matrix,
            self.budget_case.audit,
            strata_registration=self.strata_registration,
            strata_gate=self.strata_gate,
            complete_link_gate=self.complete_link_gate,
            **inputs,
        )

    def _build_binding(
        self,
        *,
        admission: object | None = None,
        budget: object | None = None,
        evidence: dict | None = None,
        inputs: dict | None = None,
        complete_link_audit: object | None = None,
    ) -> dict:
        clean_evidence = self.evidence if evidence is None else evidence
        clean_inputs = self.inputs if inputs is None else inputs
        return subject.build_portfolio_correlation_admission_effective_budget_binding_v1(
            self.admission if admission is None else admission,
            self.budget if budget is None else budget,
            clean_evidence["report_document"],
            clean_evidence["correlation_preregistration_document"],
            clean_evidence["correlation_matrix_document"],
            clean_evidence["selection_cells_document"],
            (
                self.budget_case.audit
                if complete_link_audit is None
                else complete_link_audit
            ),
            clean_evidence["complete_link_gate_document"],
            clean_evidence["strata_preregistration_document"],
            clean_evidence["strata_gate_document"],
            strategy_id=clean_evidence["strategy_id"],
            variant_id=clean_evidence["variant_id"],
            lane=clean_evidence["lane"],
            **clean_inputs,
        )

    def _verify(
        self,
        document: object,
        *,
        admission: object | None = None,
        budget: object | None = None,
        evidence: dict | None = None,
        inputs: dict | None = None,
    ) -> dict:
        clean_evidence = self.evidence if evidence is None else evidence
        clean_inputs = self.inputs if inputs is None else inputs
        return subject.verify_portfolio_correlation_admission_effective_budget_binding_v1(
            document,
            self.admission if admission is None else admission,
            self.budget if budget is None else budget,
            clean_evidence["report_document"],
            clean_evidence["correlation_preregistration_document"],
            clean_evidence["correlation_matrix_document"],
            clean_evidence["selection_cells_document"],
            self.budget_case.audit,
            clean_evidence["complete_link_gate_document"],
            clean_evidence["strata_preregistration_document"],
            clean_evidence["strata_gate_document"],
            strategy_id=clean_evidence["strategy_id"],
            variant_id=clean_evidence["variant_id"],
            lane=clean_evidence["lane"],
            **clean_inputs,
        )

    def test_exact_shared_source_passes_research_binding(self) -> None:
        self.assertEqual(self.admission["status"], "PASS")
        self.assertEqual(self.budget["status"], "PASS")
        self.assertEqual(self.binding["status"], "PASS")
        self.assertIsNone(self.binding["first_blocking_tier"])
        self.assertTrue(self.binding["checks"]["cross_source_hashes_exact"])
        receipt = self._verify(self.binding)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["binding_status"], "PASS")

    def test_admission_pass_cannot_bypass_concentrated_budget_block(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["positions"] = [
            {"symbol": "A", "notional": 5000, "direction": "LONG"}
        ]
        inputs["proposed_symbol"] = "B"
        inputs["proposed_notional"] = 5000
        inputs["max_cluster_gross_pct"] = 45.0
        blocked_budget = self._build_budget(inputs)
        binding = self._build_binding(budget=blocked_budget, inputs=inputs)

        self.assertEqual(self.admission["status"], "PASS")
        self.assertEqual(blocked_budget["status"], "BLOCK")
        self.assertEqual(binding["status"], "BLOCK")
        self.assertEqual(
            binding["first_blocking_tier"],
            "EFFECTIVE_BUDGET_V3_DECISION",
        )
        self.assertIn(
            "effective_budget_v3_decision_blocked",
            binding["blockers"],
        )
        self.assertTrue(binding["checks"]["effective_budget_v3_exact"])

    def test_exact_admission_block_remains_a_binding_block(self) -> None:
        evidence = self.admission_case._replace_universe(
            self.evidence,
            ["A", "B"],
            selection_basis="SYNTHETIC_MISMATCH",
        )
        blocked_admission = self.admission_case._build(evidence)
        binding = self._build_binding(
            admission=blocked_admission,
            evidence=evidence,
        )
        self.assertEqual(blocked_admission["status"], "BLOCK")
        self.assertTrue(binding["checks"]["admission_v2_exact"])
        self.assertEqual(binding["status"], "BLOCK")
        self.assertEqual(
            binding["first_blocking_tier"],
            "ADMISSION_V2_DECISION",
        )

    def test_resealed_admission_promotion_fails_exact_tier(self) -> None:
        promoted = copy.deepcopy(self.admission)
        promoted["permissions"]["paper_authorized"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "correlation_admission_v2_hash",
        )
        binding = self._build_binding(admission=promoted)
        self.assertEqual(binding["status"], "BLOCK")
        self.assertEqual(
            binding["first_blocking_tier"],
            "ADMISSION_V2_EXACT",
        )

    def test_resealed_budget_promotion_fails_exact_tier(self) -> None:
        promoted = copy.deepcopy(self.budget)
        promoted["authority"]["writer_allowed"] = True
        promoted = seal_strict_canonical_document(promoted, "budget_v3_hash")
        binding = self._build_binding(budget=promoted)
        self.assertEqual(binding["status"], "BLOCK")
        self.assertEqual(
            binding["first_blocking_tier"],
            "EFFECTIVE_BUDGET_V3_EXACT",
        )

    def test_proposal_change_without_budget_rebuild_fails_exact_tier(self) -> None:
        inputs = copy.deepcopy(self.inputs)
        inputs["proposed_notional"] += 1
        binding = self._build_binding(inputs=inputs)
        self.assertEqual(
            binding["first_blocking_tier"],
            "EFFECTIVE_BUDGET_V3_EXACT",
        )
        self.assertFalse(binding["checks"]["effective_budget_v3_exact"])

    def test_strategy_identity_change_fails_admission_exact_tier(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["strategy_id"] = "forged-strategy"
        binding = self._build_binding(evidence=evidence)
        self.assertEqual(
            binding["first_blocking_tier"],
            "ADMISSION_V2_EXACT",
        )
        self.assertFalse(binding["checks"]["strategy_identity_bound"])

    def test_complete_link_audit_drift_fails_budget_exact_tier(self) -> None:
        audit = copy.deepcopy(self.budget_case.audit)
        audit["status"] = "BLOCK"
        audit = seal_strict_canonical_document(audit, "audit_hash")
        binding = self._build_binding(complete_link_audit=audit)
        self.assertEqual(
            binding["first_blocking_tier"],
            "EFFECTIVE_BUDGET_V3_EXACT",
        )

    def test_output_is_hash_only_and_summary_only(self) -> None:
        self.assertEqual(
            set(self.binding["source"]),
            set(subject._SOURCE_FIELDS),
        )
        self.assertTrue(all(self.binding["source"].values()))
        encoded = json.dumps(self.binding, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"proposed_symbol":',
            '"strategy_id":',
            '"variant_id":',
            '"symbol":',
            '"notional":',
            '"direction":',
            "synthetic-strategy",
            "synthetic-variant",
            "selection_cells",
            "tradable_symbols",
            "cluster_exposures",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.binding["facts"]["source_documents_embedded"])
        self.assertFalse(self.binding["facts"]["positions_embedded"])

    def test_source_hash_chain_matches_shared_documents(self) -> None:
        source = self.binding["source"]
        self.assertEqual(
            source["correlation_preregistration_hash"],
            self.budget_case.preregistration["preregistration_hash"],
        )
        self.assertEqual(
            source["correlation_matrix_hash"],
            self.budget_case.matrix["matrix_hash"],
        )
        self.assertEqual(
            source["complete_link_audit_hash"],
            self.budget_case.audit["audit_hash"],
        )
        self.assertEqual(
            source["complete_link_gate_hash"],
            self.complete_link_gate["gate_hash"],
        )
        self.assertEqual(
            source["strata_registration_hash"],
            self.strata_registration["registration_hash"],
        )
        self.assertEqual(
            source["strata_gate_hash"],
            self.strata_gate["gate_hash"],
        )

    def test_non_native_mapping_and_cycle_fail_at_snapshot(self) -> None:
        subclass_binding = self._build_binding(
            admission=_DictSubclass(self.admission)
        )
        self.assertEqual(
            subclass_binding["first_blocking_tier"],
            "INPUT_SNAPSHOT",
        )

        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        cycle_binding = self._build_binding(budget=cyclic)
        self.assertEqual(
            cycle_binding["first_blocking_tier"],
            "INPUT_SNAPSHOT",
        )

    def test_non_finite_and_boolean_alias_inputs_fail_closed(self) -> None:
        for patch in (
            {"proposed_notional": float("inf")},
            {"equity": True},
            {"risk_increasing": 1},
        ):
            with self.subTest(patch=patch):
                inputs = copy.deepcopy(self.inputs)
                inputs.update(patch)
                binding = self._build_binding(inputs=inputs)
                self.assertEqual(binding["status"], "BLOCK")

    def test_builder_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        original = copy.deepcopy(
            (
                self.admission,
                self.budget,
                self.evidence,
                self.inputs,
                self.budget_case.audit,
            )
        )
        repeated = self._build_binding()
        self.assertEqual(repeated, self.binding)
        self.assertEqual(
            (
                self.admission,
                self.budget,
                self.evidence,
                self.inputs,
                self.budget_case.audit,
            ),
            original,
        )

    def test_exact_verifier_rejects_resealed_permission_promotion(self) -> None:
        promoted = copy.deepcopy(self.binding)
        promoted["authority"]["live_order_allowed"] = True
        promoted = seal_strict_canonical_document(promoted, "binding_hash")
        receipt = self._verify(promoted)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["binding_status"], "UNKNOWN")
        self.assertFalse(receipt["live_order_allowed"])

    def test_authority_and_policy_remain_research_only(self) -> None:
        self.assertTrue(self.binding["authority"]["descriptive_only"])
        self.assertTrue(self.binding["authority"]["consumer_only"])
        for key, value in self.binding["authority"].items():
            if key not in {"descriptive_only", "consumer_only"}:
                self.assertFalse(value)
        self.assertFalse(
            self.binding["policy"][
                "admission_pass_without_budget_pass_allowed"
            ]
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_implementation_pins_match_current_predecessors(self) -> None:
        paths = {
            subject.ADMISSION_V2_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/"
                "portfolio_correlation_admission_v2.py"
            ),
            subject.EFFECTIVE_BUDGET_V3_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/"
                "strategy_correlation_cluster_effective_bet_budget_v3.py"
            ),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/strict_canonical_json_hash.py"
            ),
        }
        for expected, path in paths.items():
            with self.subTest(path=str(path)):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
