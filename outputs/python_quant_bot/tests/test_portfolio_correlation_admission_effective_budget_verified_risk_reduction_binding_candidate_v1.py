from __future__ import annotations

import copy
from hashlib import sha256
import inspect
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_verified_risk_reduction_binding_candidate_v1
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v4 as budget_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_portfolio_correlation_admission_effective_budget_binding_v1 import (
    PortfolioCorrelationAdmissionEffectiveBudgetBindingV1Tests,
)


ROOT = Path(__file__).resolve().parents[1]


class VerifiedRiskReductionBindingCandidateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = PortfolioCorrelationAdmissionEffectiveBudgetBindingV1Tests()
        self.case.setUp()
        self.before = [
            {"symbol": "A", "notional": 2_500, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        self.after = [
            {"symbol": "A", "notional": 2_000, "direction": "LONG"},
            {"symbol": "B", "notional": 1_000, "direction": "SHORT"},
        ]
        self.inputs = copy.deepcopy(self.case.inputs)
        self.inputs.update(
            {
                "positions": self.before,
                "proposed_symbol": "A",
                "proposed_notional": 500,
                "proposed_direction": "SHORT",
                "risk_increasing": False,
            }
        )
        self.transition = (
            budget_v4.build_strategy_correlation_cluster_risk_reduction_transition_v1(
                self.before,
                self.after,
                proposed_symbol="A",
                proposed_notional=500,
                proposed_direction="SHORT",
            )
        )
        self.budget_v3 = self.case._build_budget(self.inputs)
        self.legacy_binding = self.case._build_binding(
            budget=self.budget_v3,
            inputs=self.inputs,
        )
        self.budget_v4 = self._build_v4(
            self.inputs,
            positions_after=self.after,
            transition=self.transition,
        )
        self.candidate = self._build_candidate()

    def _build_v4(
        self,
        inputs: dict,
        *,
        positions_after: object,
        transition: object,
    ) -> dict:
        return budget_v4.evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
            self.case.budget_case.preregistration,
            self.case.budget_case.matrix,
            self.case.budget_case.audit,
            strata_registration=self.case.strata_registration,
            strata_gate=self.case.strata_gate,
            complete_link_gate=self.case.complete_link_gate,
            positions_after=positions_after,
            risk_reduction_transition=transition,
            **inputs,
        )

    def _build_candidate(
        self,
        *,
        legacy_binding: object | None = None,
        budget4: object | None = None,
        inputs: dict | None = None,
        positions_after: object | None = None,
        transition: object | None = None,
    ) -> dict:
        clean_inputs = self.inputs if inputs is None else inputs
        clean_after = self.after if positions_after is None else positions_after
        clean_transition = self.transition if transition is None else transition
        evidence = self.case.evidence
        return subject.build_verified_risk_reduction_effective_budget_binding_candidate_v1(
            self.legacy_binding if legacy_binding is None else legacy_binding,
            self.budget_v4 if budget4 is None else budget4,
            self.case.admission,
            self.budget_v3,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            self.case.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
            clean_after,
            clean_transition,
            strategy_id=evidence["strategy_id"],
            variant_id=evidence["variant_id"],
            lane=evidence["lane"],
            **clean_inputs,
        )

    def _verify(self, document: object) -> dict:
        evidence = self.case.evidence
        return subject.verify_verified_risk_reduction_effective_budget_binding_candidate_v1(
            document,
            self.legacy_binding,
            self.budget_v4,
            self.case.admission,
            self.budget_v3,
            evidence["report_document"],
            evidence["correlation_preregistration_document"],
            evidence["correlation_matrix_document"],
            evidence["selection_cells_document"],
            self.case.budget_case.audit,
            evidence["complete_link_gate_document"],
            evidence["strata_preregistration_document"],
            evidence["strata_gate_document"],
            self.after,
            self.transition,
            strategy_id=evidence["strategy_id"],
            variant_id=evidence["variant_id"],
            lane=evidence["lane"],
            **self.inputs,
        )

    def test_verified_reduction_closes_only_the_conservative_legacy_block(self) -> None:
        self.assertEqual(self.budget_v3["status"], "PASS")
        self.assertEqual(self.budget_v3["decision"], "RISK_REDUCTION_PATH")
        self.assertEqual(self.legacy_binding["status"], "BLOCK")
        self.assertEqual(
            self.legacy_binding["first_blocking_tier"],
            "CROSS_SOURCE_BINDING",
        )
        self.assertEqual(
            self.legacy_binding["blockers"],
            ["cross_source_hash_binding_failed"],
        )
        self.assertEqual(self.budget_v4["status"], "PASS")
        self.assertEqual(self.candidate["status"], "PASS")
        self.assertEqual(self.candidate["admission_status"], "BLOCKED")
        self.assertTrue(
            self.candidate["facts"]["legacy_current_consumer_fail_closed"]
        )
        self.assertTrue(
            self.candidate["facts"][
                "risk_reduction_derived_from_position_transition"
            ]
        )
        self.assertEqual(self._verify(self.candidate)["status"], "PASS")

    def test_same_direction_add_with_false_flag_remains_blocked(self) -> None:
        malicious = copy.deepcopy(self.inputs)
        malicious.update(
            {
                "positions": [
                    {"symbol": "A", "notional": 1_000, "direction": "LONG"}
                ],
                "proposed_direction": "LONG",
            }
        )
        v3_document = self.case._build_budget(malicious)
        legacy = self.case._build_binding(
            budget=v3_document,
            inputs=malicious,
        )
        v4_document = self._build_v4(
            malicious,
            positions_after=None,
            transition=None,
        )
        self.assertEqual(v3_document["status"], "PASS")
        self.assertEqual(v3_document["decision"], "RISK_REDUCTION_PATH")
        self.assertEqual(legacy["status"], "BLOCK")
        self.assertIn(
            "verified_risk_reduction_transition_missing",
            v4_document["blockers"],
        )
        candidate = self._build_candidate(
            legacy_binding=legacy,
            budget4=v4_document,
            inputs=malicious,
            positions_after=None,
            transition=None,
        )
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertIn(
            "verified_risk_reduction_transition_not_pass",
            candidate["blockers"],
        )

    def test_missing_or_mismatched_transition_blocks(self) -> None:
        blocked_v4 = self._build_v4(
            self.inputs,
            positions_after=self.after,
            transition=None,
        )
        candidate = self._build_candidate(
            budget4=blocked_v4,
            transition=None,
        )
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["checks"]["verified_transition_pass"])

        changed_after = copy.deepcopy(self.after)
        changed_after[0]["notional"] = 2_100
        candidate = self._build_candidate(positions_after=changed_after)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["checks"]["effective_budget_v4_exact"])

    def test_legacy_binding_must_be_exact_and_cross_source_only(self) -> None:
        forged = copy.deepcopy(self.legacy_binding)
        forged.pop("binding_hash")
        forged["blockers"] = []
        forged["status"] = "PASS"
        forged = seal_strict_canonical_document(forged, "binding_hash")
        candidate = self._build_candidate(legacy_binding=forged)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["checks"]["legacy_binding_exact"])

    def test_v4_permission_promotion_and_splice_are_rejected(self) -> None:
        promoted = copy.deepcopy(self.budget_v4)
        promoted.pop("budget_v4_hash")
        promoted["authority"]["current_admission_allowed"] = True
        promoted = seal_strict_canonical_document(promoted, "budget_v4_hash")
        candidate = self._build_candidate(budget4=promoted)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["checks"]["effective_budget_v4_exact"])

        changed = copy.deepcopy(self.inputs)
        changed["proposed_notional"] = 400
        candidate = self._build_candidate(inputs=changed)
        self.assertEqual(candidate["status"], "BLOCKED")
        self.assertFalse(candidate["checks"]["cross_version_binding_exact"])

    def test_only_false_boolean_reduction_lane_is_accepted(self) -> None:
        for value in (True, 0, None, "false"):
            with self.subTest(value=value):
                changed = copy.deepcopy(self.inputs)
                changed["risk_increasing"] = value
                candidate = self._build_candidate(inputs=changed)
                self.assertEqual(candidate["status"], "BLOCKED")
                self.assertFalse(
                    candidate["checks"]["risk_reduction_lane_exact"]
                )

    def test_nonfinite_cycle_and_container_subclass_fail_at_snapshot(self) -> None:
        changed = copy.deepcopy(self.inputs)
        changed["proposed_notional"] = float("inf")
        self.assertEqual(
            self._build_candidate(inputs=changed)["first_blocking_tier"],
            "INPUT_SNAPSHOT",
        )

        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertEqual(
            self._build_candidate(positions_after=cyclic)[
                "first_blocking_tier"
            ],
            "INPUT_SNAPSHOT",
        )

        class DictSubclass(dict):
            pass

        self.assertEqual(
            self._build_candidate(legacy_binding=DictSubclass(self.legacy_binding))[
                "first_blocking_tier"
            ],
            "INPUT_SNAPSHOT",
        )

    def test_output_is_deterministic_summary_only_and_inputs_are_immutable(self) -> None:
        original = copy.deepcopy(
            (
                self.legacy_binding,
                self.budget_v4,
                self.case.admission,
                self.budget_v3,
                self.case.evidence,
                self.inputs,
                self.after,
                self.transition,
            )
        )
        repeated = self._build_candidate()
        self.assertEqual(repeated, self.candidate)
        self.assertEqual(
            (
                self.legacy_binding,
                self.budget_v4,
                self.case.admission,
                self.budget_v3,
                self.case.evidence,
                self.inputs,
                self.after,
                self.transition,
            ),
            original,
        )
        encoded = json.dumps(self.candidate, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"positions_after":',
            '"transition":',
            '"cluster_exposures":',
            '"strata":',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.candidate["facts"]["source_documents_embedded"])

    def test_exact_verifier_rejects_resealed_candidate_promotion(self) -> None:
        promoted = copy.deepcopy(self.candidate)
        promoted.pop("candidate_hash")
        promoted["authority"]["paper_authorized"] = True
        promoted = seal_strict_canonical_document(promoted, "candidate_hash")
        receipt = self._verify(promoted)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertEqual(receipt["candidate_status"], "UNKNOWN")
        self.assertFalse(receipt["paper_authorized"])

    def test_activation_order_and_all_authority_locks_are_explicit(self) -> None:
        self.assertEqual(
            self.candidate["activation_order"],
            list(subject.ACTIVATION_ORDER),
        )
        self.assertEqual(
            self.candidate["activation_order"][-1],
            "SEPARATE_CURRENT_DECISION",
        )
        for key, value in self.candidate["authority"].items():
            if key not in {"descriptive_only", "consumer_only"}:
                self.assertFalse(value, key)
        self.assertFalse(self.candidate["facts"]["profitability_proven"])

    def test_dependency_pins_and_public_api_are_exact(self) -> None:
        paths = {
            subject.BINDING_V1_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/"
                "portfolio_correlation_admission_effective_budget_binding_v1.py"
            ),
            subject.BUDGET_V4_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/"
                "strategy_correlation_cluster_effective_bet_budget_v4.py"
            ),
            subject.STRICT_CANONICAL_IMPLEMENTATION_SHA256: (
                ROOT
                / "exchange_terminal/services/strict_canonical_json_hash.py"
            ),
        }
        for expected_hash, path in paths.items():
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected_hash)

        parameters = inspect.signature(
            subject.build_verified_risk_reduction_effective_budget_binding_candidate_v1
        ).parameters
        for forbidden in (
            "runtime",
            "database",
            "cache",
            "host",
            "writer",
            "paper",
            "live",
        ):
            self.assertNotIn(forbidden, parameters)


if __name__ == "__main__":
    unittest.main()
