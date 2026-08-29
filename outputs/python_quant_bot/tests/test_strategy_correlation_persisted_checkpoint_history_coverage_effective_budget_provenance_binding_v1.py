from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1
    as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_gate as cluster_preregistration_contract,
)
from exchange_terminal.services import (
    strategy_correlation_return_replay as return_replay_contract,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_persisted_checkpoint_history_coverage_provider_identity_seam_closure_v1
    as history_fixture,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1
    as budget_fixture,
)
from tests import (
    test_strategy_correlation_return_replay as return_replay_fixture,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_cluster_gate_v1
    as uncertainty_fixture,
)


class StrategyCorrelationPersistedCheckpointHistoryCoverageEffectiveBudgetProvenanceBindingV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        with history_fixture.zero_seam_three_segment_fixture_v1() as material:
            cls.history_registration = deepcopy(material["registration"])
            cls.history_registration_receipt = deepcopy(
                material["registration_receipt"]
            )
            cls.history_gate = deepcopy(material["coverage_gate"])
            cls.lineage_items = deepcopy(material["lineage_items"])

        return_case = return_replay_fixture.StrategyCorrelationReturnReplayTests()
        return_case.setUp()

        def real_replay(
            series: dict[str, list[float]],
            clusters: list[dict[str, object]],
        ) -> dict[str, object]:
            preregistration = cluster_preregistration_contract.build_correlation_cluster_preregistration(
                clusters
            )
            scaled_returns = {
                symbol: [value / 100.0 for value in values]
                for symbol, values in series.items()
            }
            completed = return_case._input(
                returns=scaled_returns,
                preregistration=preregistration,
            )
            return return_replay_contract.build_correlation_matrix_replay(
                completed,
                preregistration,
            )

        budget_case = budget_fixture.StrategyCorrelationUncertaintyMultiWindowEffectiveBetBudgetBindingV1Tests()
        budget_case.setUp()
        try:
            with patch.object(
                uncertainty_fixture.FixtureCase,
                "_replay",
                real_replay,
            ):
                cls.budget_context = deepcopy(budget_case._context())
                cls.blocked_budget_context = deepcopy(
                    budget_case._context(blocked=True)
                )

            replay_results: list[dict[str, object]] = []
            for cleanup in reversed(budget_case._cleanups):
                nested_case = getattr(cleanup[0], "__self__", None)
                if not isinstance(nested_case, unittest.TestCase):
                    continue
                for nested_cleanup in list(nested_case._cleanups):
                    patcher = getattr(nested_cleanup[0], "__self__", None)
                    if (
                        getattr(patcher, "attribute", None)
                        != "verify_correlation_matrix_replay"
                    ):
                        continue
                    mocked = getattr(patcher.getter(), patcher.attribute)
                    original = patcher.temp_original
                    replay_results.extend(
                        original(*call.args, **call.kwargs)
                        for call in mocked.call_args_list
                    )
                    patcher.stop()
                    nested_case._cleanups.remove(nested_cleanup)
            if not replay_results or any(
                result != {"status": "PASS", "blockers": []}
                for result in replay_results
            ):
                raise AssertionError(
                    "budget source correlation replay did not pass original verifier"
                )
            cls.replay_original_pass_count = len(replay_results)
            cls.budget_evaluation = deepcopy(
                budget_case._evaluate(cls.budget_context)
            )
            cls.blocked_budget_evaluation = deepcopy(
                budget_case._evaluate(cls.blocked_budget_context)
            )
        finally:
            budget_case.doCleanups()
            return_case.doCleanups()

        cls.budget_preregistration_context = {
            "uncertainty_preregistration": cls.budget_context[
                "uncertainty_gate_context"
            ]["uncertainty_preregistration"],
            "geometry_budget_binding_preregistration": cls.budget_context[
                "budget_evaluation_context"
            ]["budget_binding_preregistration"],
            "uncertainty_preregistration_verification_context": cls.budget_context[
                "uncertainty_preregistration_context"
            ],
            "budget_preregistration_verification_context": cls.budget_context[
                "budget_preregistration_context"
            ],
        }
        cls.preregistration = subject.build_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
            cls.history_registration,
            cls.history_registration_receipt,
            cls.budget_context["preregistration"],
            budget_binding_preregistration_verification_context=(
                cls.budget_preregistration_context
            ),
        )
        if cls.preregistration is None:
            raise AssertionError("provenance preregistration did not build")
        cls.preregistration_context = {
            "history_coverage_registration": cls.history_registration,
            "history_coverage_registration_receipt": cls.history_registration_receipt,
            "uncertainty_budget_binding_preregistration": cls.budget_context[
                "preregistration"
            ],
            "budget_binding_preregistration_verification_context": (
                cls.budget_preregistration_context
            ),
        }
        cls.history_context = {
            "registration": cls.history_registration,
            "registration_receipt": cls.history_registration_receipt,
            "lineage_items": cls.lineage_items,
            "expected_gate_hash": cls.history_gate["gate_hash"],
        }
        cls.budget_verification_context = cls._budget_verification_context(
            cls.budget_context,
            cls.budget_evaluation,
        )
        cls.evaluation = cls._evaluate()

    @classmethod
    def _budget_verification_context(
        cls,
        context: dict[str, object],
        evaluation: dict[str, object],
    ) -> dict[str, object]:
        return {
            "uncertainty_budget_binding_preregistration": context[
                "preregistration"
            ],
            "uncertainty_gate_document": context["uncertainty_gate"],
            "geometry_budget_binding_evaluation": context[
                "budget_evaluation"
            ],
            "expected_evaluation_hash": evaluation["evaluation_hash"],
            "expected_preregistration_hash": context["preregistration"][
                "preregistration_hash"
            ],
            "uncertainty_gate_verification_context": context[
                "uncertainty_gate_context"
            ],
            "budget_evaluation_verification_context": context[
                "budget_evaluation_context"
            ],
        }

    @classmethod
    def _evaluate(
        cls,
        *,
        preregistration: dict[str, object] | None = None,
        history_gate: dict[str, object] | None = None,
        budget_evaluation: dict[str, object] | None = None,
        preregistration_context: dict[str, object] | None = None,
        history_context: dict[str, object] | None = None,
        budget_context: dict[str, object] | None = None,
    ) -> dict[str, object]:
        preregistration = preregistration or cls.preregistration
        return subject.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
            preregistration,
            history_gate or cls.history_gate,
            budget_evaluation or cls.budget_evaluation,
            expected_preregistration_hash=preregistration[
                "preregistration_hash"
            ],
            preregistration_verification_context=(
                preregistration_context or cls.preregistration_context
            ),
            history_gate_verification_context=(
                history_context or cls.history_context
            ),
            budget_evaluation_verification_context=(
                budget_context or cls.budget_verification_context
            ),
        )

    def test_exact_dual_source_provenance_passes_without_identity_claim(self) -> None:
        document = self.evaluation
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["reason_code"],
            "BOUNDED_HISTORY_AND_EFFECTIVE_BUDGET_PROVENANCE_BOUND_"
            "IDENTITY_EQUIVALENCE_UNPROVEN",
        )
        self.assertTrue(document["facts"]["history_coverage_exactly_verified"])
        self.assertTrue(
            document["facts"][
                "uncertainty_effective_budget_binding_exactly_verified"
            ]
        )
        self.assertFalse(
            document["facts"]["semantic_study_identity_equivalence_verified"]
        )
        self.assertGreater(self.replay_original_pass_count, 0)

    def test_preregistration_pins_distinct_window_identities_without_equating_them(
        self,
    ) -> None:
        document = self.preregistration
        self.assertNotEqual(
            document["history_window_order_hash"],
            document["budget_window_order_hash"],
        )
        self.assertFalse(document["source_window_order_hashes_equal"])
        self.assertEqual(
            document["identity_relationship_policy"],
            subject.IDENTITY_RELATIONSHIP_POLICY,
        )
        self.assertFalse(
            document["facts"]["semantic_study_identity_equivalence_verified"]
        )

    def test_preregistration_and_evaluation_reverify_exactly(self) -> None:
        self.assertTrue(
            subject.verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
                self.preregistration,
                self.history_registration,
                self.history_registration_receipt,
                self.budget_context["preregistration"],
                expected_preregistration_hash=self.preregistration[
                    "preregistration_hash"
                ],
                budget_binding_preregistration_verification_context=(
                    self.budget_preregistration_context
                ),
            )
        )
        self.assertTrue(
            subject.verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
                self.evaluation,
                self.preregistration,
                self.history_gate,
                self.budget_evaluation,
                expected_evaluation_hash=self.evaluation["evaluation_hash"],
                expected_preregistration_hash=self.preregistration[
                    "preregistration_hash"
                ],
                preregistration_verification_context=self.preregistration_context,
                history_gate_verification_context=self.history_context,
                budget_evaluation_verification_context=(
                    self.budget_verification_context
                ),
            )
        )

    def test_non_positive_history_short_circuits_budget_verification(self) -> None:
        missing = [
            deepcopy(self.lineage_items[0]),
            deepcopy(self.lineage_items[2]),
        ]
        history_gate = history_fixture.adr0360_fixture.adr0359_fixture.coverage_contract.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_gate_v1(
            registration=self.history_registration,
            registration_receipt=self.history_registration_receipt,
            lineage_items=missing,
        )
        history_context = {
            **self.history_context,
            "lineage_items": missing,
            "expected_gate_hash": history_gate["gate_hash"],
        }
        with patch.object(
            subject,
            "_VERIFY_BUDGET_BINDING_EVALUATION",
            wraps=subject._VERIFY_BUDGET_BINDING_EVALUATION,
        ) as budget_verifier:
            document = self._evaluate(
                history_gate=history_gate,
                history_context=history_context,
            )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["reason_code"],
            "BOUNDED_HISTORY_COVERAGE_NOT_POSITIVE",
        )
        self.assertFalse(document["facts"]["budget_verification_attempted"])
        budget_verifier.assert_not_called()

    def test_resealed_history_authority_promotion_is_rejected_before_budget(
        self,
    ) -> None:
        promoted = deepcopy(self.history_gate)
        promoted["authority"]["paper_authorized"] = True
        promoted = seal_strict_canonical_document(promoted, "gate_hash")
        context = {
            **self.history_context,
            "expected_gate_hash": promoted["gate_hash"],
        }
        with patch.object(
            subject,
            "_VERIFY_BUDGET_BINDING_EVALUATION",
            wraps=subject._VERIFY_BUDGET_BINDING_EVALUATION,
        ) as budget_verifier:
            document = self._evaluate(
                history_gate=promoted,
                history_context=context,
            )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(document["reason_code"], "HISTORY_COVERAGE_NOT_VERIFIED")
        budget_verifier.assert_not_called()

    def test_budget_authority_tamper_is_unknown(self) -> None:
        tampered = deepcopy(self.budget_evaluation)
        tampered["authority"]["paper_authorized"] = True
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")
        context = {
            **self.budget_verification_context,
            "expected_evaluation_hash": tampered["evaluation_hash"],
        }
        document = self._evaluate(
            budget_evaluation=tampered,
            budget_context=context,
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(
            document["reason_code"],
            "UNCERTAINTY_EFFECTIVE_BUDGET_BINDING_NOT_VERIFIED",
        )

    def test_verified_budget_block_is_preserved(self) -> None:
        self.assertEqual(
            self.blocked_budget_context["preregistration"]["preregistration_hash"],
            self.preregistration["budget_binding_preregistration_hash"],
        )
        context = self._budget_verification_context(
            self.blocked_budget_context,
            self.blocked_budget_evaluation,
        )
        document = self._evaluate(
            budget_evaluation=self.blocked_budget_evaluation,
            budget_context=context,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(
            document["reason_code"],
            "VERIFIED_EFFECTIVE_BUDGET_BINDING_BLOCK_PRESERVED",
        )

    def test_output_is_redacted_and_all_operational_authority_is_locked(self) -> None:
        document = self.evaluation
        forbidden = {
            "lineage_items",
            "window_audits",
            "trusted_effective_budget_document",
            "effective_budget_document",
            "positions",
            "correlation_matrix",
            "price_series",
            "return_series",
        }
        self.assertTrue(forbidden.isdisjoint(document))
        self.assertTrue(document["authority"]["research_evidence_only"])
        for key, value in document["authority"].items():
            if key != "research_evidence_only":
                self.assertFalse(value, key)

    def test_preregistration_hash_drift_is_fail_closed(self) -> None:
        document = subject.evaluate_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1(
            self.preregistration,
            self.history_gate,
            self.budget_evaluation,
            expected_preregistration_hash="0" * 64,
            preregistration_verification_context=self.preregistration_context,
            history_gate_verification_context=self.history_context,
            budget_evaluation_verification_context=(
                self.budget_verification_context
            ),
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(
            document["reason_code"],
            "PROVENANCE_PREREGISTRATION_NOT_VERIFIED",
        )


if __name__ == "__main__":
    unittest.main()
