from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import strategy_correlation_cluster_gate as cluster_contract
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_complete_link_binding_v1 as upstream,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as binding,
)
from exchange_terminal.services import strategy_correlation_matrix_geometry_gate_v1 as geometry
from exchange_terminal.services import strategy_correlation_preregistered_strata as strata
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from tests import (
    test_strategy_correlation_cluster_effective_bet_budget_v3 as budget_fixtures,
)


class StrategyCorrelationMatrixGeometryEffectiveBetBudgetBindingTests(unittest.TestCase):
    @staticmethod
    def _rehash_external(document: dict, field: str) -> None:
        unsigned = deepcopy(document)
        unsigned.pop(field, None)
        document[field] = sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _rehash_binding(document: dict, field: str) -> None:
        unsigned = deepcopy(document)
        unsigned.pop(field, None)
        document[field] = sha256(
            json.dumps(
                unsigned,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
        ).hexdigest()

    def _bundle(self, *, non_psd: bool = False) -> dict:
        case = budget_fixtures.StrategyCorrelationClusterEffectiveBetBudgetV3Tests(
            methodName="test_balanced_active_exposure_in_separate_strata_passes"
        )
        case.setUp()
        if non_psd:
            case.matrix = cluster_contract.build_correlation_matrix_contract(
                case.matrix["symbols"],
                {
                    ("A", "B"): 0.7,
                    ("A", "C"): 0.7,
                    ("B", "C"): -0.1,
                },
            )
            case.audit = build_correlation_cluster_complete_link_audit(
                case.preregistration,
                case.matrix,
            )
            case.complete_link_gate = case._complete_link_gate(case.cells)

        direct_budget, registration, strata_gate, complete_link_gate, kwargs = (
            case._evaluate(shared=False)
        )
        geometry_preregistration = (
            geometry.build_strategy_correlation_matrix_geometry_preregistration_v1(
                case.matrix["symbols"]
            )
        )
        geometry_gate = geometry.evaluate_strategy_correlation_matrix_geometry_gate_v1(
            geometry_preregistration,
            case.matrix,
            expected_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
        )
        upstream_preregistration = upstream.build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
            geometry_preregistration,
            case.preregistration,
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=case.preregistration[
                "preregistration_hash"
            ],
        )
        upstream_evaluation = upstream.evaluate_strategy_correlation_matrix_geometry_complete_link_binding_v1(
            upstream_preregistration,
            geometry_preregistration,
            geometry_gate,
            case.preregistration,
            case.matrix,
            case.cells,
            expected_binding_preregistration_hash=upstream_preregistration[
                "preregistration_hash"
            ],
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=case.preregistration[
                "preregistration_hash"
            ],
            strategy_id=complete_link_gate["strategy_id"],
            variant_id=complete_link_gate["variant_id"],
            lane=complete_link_gate["lane"],
        )
        budget_preregistration = binding.build_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
            upstream_preregistration,
            geometry_preregistration,
            case.preregistration,
            registration,
            expected_geometry_complete_link_binding_preregistration_hash=(
                upstream_preregistration["preregistration_hash"]
            ),
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=case.preregistration[
                "preregistration_hash"
            ],
            expected_strata_registration_hash=registration["registration_hash"],
        )
        return {
            "case": case,
            "direct_budget": direct_budget,
            "registration": registration,
            "strata_gate": strata_gate,
            "complete_link_gate": complete_link_gate,
            "kwargs": kwargs,
            "geometry_preregistration": geometry_preregistration,
            "geometry_gate": geometry_gate,
            "upstream_preregistration": upstream_preregistration,
            "upstream_evaluation": upstream_evaluation,
            "budget_preregistration": budget_preregistration,
        }

    def _evaluate(self, bundle: dict, **overrides: object) -> dict:
        case = bundle["case"]
        kwargs = dict(bundle["kwargs"])
        kwargs.update(overrides.pop("budget_inputs", {}))
        values = {
            "budget_binding_preregistration": bundle["budget_preregistration"],
            "geometry_complete_link_binding_preregistration": bundle[
                "upstream_preregistration"
            ],
            "geometry_preregistration": bundle["geometry_preregistration"],
            "geometry_gate_document": bundle["geometry_gate"],
            "geometry_complete_link_binding_evaluation": bundle[
                "upstream_evaluation"
            ],
            "cluster_preregistration": case.preregistration,
            "correlation_matrix": case.matrix,
            "selection_cells": case.cells,
            "strata_registration": bundle["registration"],
            "strata_gate": bundle["strata_gate"],
            "expected_budget_binding_preregistration_hash": bundle[
                "budget_preregistration"
            ]["preregistration_hash"],
            "expected_geometry_complete_link_binding_preregistration_hash": bundle[
                "upstream_preregistration"
            ]["preregistration_hash"],
            "expected_geometry_preregistration_hash": bundle[
                "geometry_preregistration"
            ]["preregistration_hash"],
            "expected_cluster_preregistration_hash": case.preregistration[
                "preregistration_hash"
            ],
            "expected_strata_registration_hash": bundle["registration"][
                "registration_hash"
            ],
            "expected_geometry_complete_link_binding_evaluation_hash": bundle[
                "upstream_evaluation"
            ]["evaluation_hash"],
            "strategy_id": bundle["complete_link_gate"]["strategy_id"],
            "variant_id": bundle["complete_link_gate"]["variant_id"],
            "lane": bundle["complete_link_gate"]["lane"],
        }
        values.update(overrides)
        return binding.evaluate_strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1(
            values["budget_binding_preregistration"],
            values["geometry_complete_link_binding_preregistration"],
            values["geometry_preregistration"],
            values["geometry_gate_document"],
            values["geometry_complete_link_binding_evaluation"],
            values["cluster_preregistration"],
            values["correlation_matrix"],
            values["selection_cells"],
            values["strata_registration"],
            values["strata_gate"],
            expected_budget_binding_preregistration_hash=values[
                "expected_budget_binding_preregistration_hash"
            ],
            expected_geometry_complete_link_binding_preregistration_hash=values[
                "expected_geometry_complete_link_binding_preregistration_hash"
            ],
            expected_geometry_preregistration_hash=values[
                "expected_geometry_preregistration_hash"
            ],
            expected_cluster_preregistration_hash=values[
                "expected_cluster_preregistration_hash"
            ],
            expected_strata_registration_hash=values[
                "expected_strata_registration_hash"
            ],
            expected_geometry_complete_link_binding_evaluation_hash=values[
                "expected_geometry_complete_link_binding_evaluation_hash"
            ],
            strategy_id=values["strategy_id"],
            variant_id=values["variant_id"],
            lane=values["lane"],
            **kwargs,
        )

    def test_dependency_contracts_are_pinned(self) -> None:
        self.assertEqual(
            sha256(Path(budget_v3.__file__).read_bytes()).hexdigest(),
            binding.EFFECTIVE_BUDGET_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            sha256(Path(strata.__file__).read_bytes()).hexdigest(),
            binding.STRATA_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            upstream.BINDING_CONTRACT_HASH,
            binding._CONTRACT_MANIFEST["geometry_complete_link_binding"][
                "contract_hash"
            ],
        )

    def test_preregistration_is_unmounted_and_exact(self) -> None:
        bundle = self._bundle()
        document = bundle["budget_preregistration"]
        self.assertEqual(document["status"], "PREREGISTERED_UNMOUNTED")
        self.assertFalse(document["mounted"])
        self.assertFalse(document["permissions"]["paper"])
        self.assertFalse(document["permissions"]["live"])
        self.assertTrue(
            binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
                document,
                bundle["upstream_preregistration"],
                bundle["geometry_preregistration"],
                bundle["case"].preregistration,
                bundle["registration"],
                expected_budget_binding_preregistration_hash=document[
                    "preregistration_hash"
                ],
                expected_geometry_complete_link_binding_preregistration_hash=bundle[
                    "upstream_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "case"
                ].preregistration["preregistration_hash"],
                expected_strata_registration_hash=bundle["registration"][
                    "registration_hash"
                ],
            )
        )

    def test_preregistration_tamper_is_rejected(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["budget_preregistration"])
        tampered["mounted"] = True
        self.assertFalse(
            binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
                tampered,
                bundle["upstream_preregistration"],
                bundle["geometry_preregistration"],
                bundle["case"].preregistration,
                bundle["registration"],
                expected_budget_binding_preregistration_hash=bundle[
                    "budget_preregistration"
                ]["preregistration_hash"],
                expected_geometry_complete_link_binding_preregistration_hash=bundle[
                    "upstream_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "case"
                ].preregistration["preregistration_hash"],
                expected_strata_registration_hash=bundle["registration"][
                    "registration_hash"
                ],
            )
        )

    def test_happy_path_preserves_budget_and_zero_authority(self) -> None:
        result = self._evaluate(self._bundle())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_BOUND_EFFECTIVE_BET_BUDGET_VERIFIED",
        )
        self.assertEqual(result["effective_budget_status"], "PASS")
        self.assertEqual(
            result["effective_budget_decision"],
            "PASS_STRATIFIED_RESEARCH_BUDGET",
        )
        self.assertTrue(result["budget_document_verified"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["permissions"]["paper"])
        self.assertFalse(result["permissions"]["live"])

    def test_exact_evaluation_verifier_accepts_document(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        kwargs = bundle["kwargs"]
        self.assertTrue(
            binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1(
                result,
                bundle["budget_preregistration"],
                bundle["upstream_preregistration"],
                bundle["geometry_preregistration"],
                bundle["geometry_gate"],
                bundle["upstream_evaluation"],
                bundle["case"].preregistration,
                bundle["case"].matrix,
                bundle["case"].cells,
                bundle["registration"],
                bundle["strata_gate"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_budget_binding_preregistration_hash=bundle[
                    "budget_preregistration"
                ]["preregistration_hash"],
                expected_geometry_complete_link_binding_preregistration_hash=bundle[
                    "upstream_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "case"
                ].preregistration["preregistration_hash"],
                expected_strata_registration_hash=bundle["registration"][
                    "registration_hash"
                ],
                expected_geometry_complete_link_binding_evaluation_hash=bundle[
                    "upstream_evaluation"
                ]["evaluation_hash"],
                strategy_id=bundle["complete_link_gate"]["strategy_id"],
                variant_id=bundle["complete_link_gate"]["variant_id"],
                lane=bundle["complete_link_gate"]["lane"],
                **kwargs,
            )
        )

    def test_exact_evaluation_verifier_rejects_tamper(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        tampered = deepcopy(result)
        tampered["current_admission_allowed"] = True
        kwargs = bundle["kwargs"]
        self.assertFalse(
            binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1(
                tampered,
                bundle["budget_preregistration"],
                bundle["upstream_preregistration"],
                bundle["geometry_preregistration"],
                bundle["geometry_gate"],
                bundle["upstream_evaluation"],
                bundle["case"].preregistration,
                bundle["case"].matrix,
                bundle["case"].cells,
                bundle["registration"],
                bundle["strata_gate"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_budget_binding_preregistration_hash=bundle[
                    "budget_preregistration"
                ]["preregistration_hash"],
                expected_geometry_complete_link_binding_preregistration_hash=bundle[
                    "upstream_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "case"
                ].preregistration["preregistration_hash"],
                expected_strata_registration_hash=bundle["registration"][
                    "registration_hash"
                ],
                expected_geometry_complete_link_binding_evaluation_hash=bundle[
                    "upstream_evaluation"
                ]["evaluation_hash"],
                strategy_id=bundle["complete_link_gate"]["strategy_id"],
                variant_id=bundle["complete_link_gate"]["variant_id"],
                lane=bundle["complete_link_gate"]["lane"],
                **kwargs,
            )
        )

    def test_missing_upstream_evaluation_never_invokes_budget(self) -> None:
        bundle = self._bundle()
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
        ) as consumer:
            result = self._evaluate(
                bundle,
                geometry_complete_link_binding_evaluation=None,
            )
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["budget_consumer_invocation_attempted"])

    def test_rehashed_upstream_tamper_never_invokes_budget(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["upstream_evaluation"])
        tampered["status"] = "BLOCK"
        self._rehash_binding(tampered, "evaluation_hash")
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
        ) as consumer:
            result = self._evaluate(
                bundle,
                geometry_complete_link_binding_evaluation=tampered,
                expected_geometry_complete_link_binding_evaluation_hash=tampered[
                    "evaluation_hash"
                ],
            )
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_COMPLETE_LINK_EVALUATION_INVALID",
        )

    def test_non_psd_direct_gap_is_blocked_before_budget_consumer(self) -> None:
        bundle = self._bundle(non_psd=True)
        self.assertEqual(bundle["geometry_gate"]["status"], "BLOCK")
        self.assertEqual(bundle["direct_budget"]["status"], "PASS")
        self.assertEqual(
            bundle["direct_budget"]["decision"],
            "PASS_STRATIFIED_RESEARCH_BUDGET",
        )
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
        ) as consumer:
            result = self._evaluate(bundle)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_COMPLETE_LINK_EVALUATION_DID_NOT_PASS",
        )

    def test_rehashed_strata_gate_tamper_never_invokes_budget(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["strata_gate"])
        tampered["status"] = "BLOCK"
        self._rehash_external(tampered, "gate_hash")
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
        ) as consumer:
            result = self._evaluate(bundle, strata_gate=tampered)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "PREREGISTERED_STRATA_GATE_INVALID")

    def test_budget_consumer_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "EFFECTIVE_BET_BUDGET_CONSUMER_EXCEPTION"
        )
        self.assertTrue(result["budget_consumer_invocation_attempted"])
        self.assertIsNone(result["effective_budget_document"])

    def test_rehashed_forged_budget_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = deepcopy(bundle["direct_budget"])
        forged["decision"] = "FORGED"
        self._rehash_external(forged, "budget_v3_hash")
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
            return_value=forged,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "EFFECTIVE_BET_BUDGET_DOCUMENT_INVALID"
        )
        self.assertFalse(result["budget_document_verified"])

    def test_budget_block_is_preserved_as_verified_evidence(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(
            bundle,
            budget_inputs={"proposed_notional": 9000},
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["effective_budget_status"], "BLOCK")
        self.assertTrue(result["budget_document_verified"])
        self.assertFalse(result["current_admission_allowed"])

    def test_paper_lane_never_invokes_budget(self) -> None:
        bundle = self._bundle()
        with patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
        ) as consumer:
            result = self._evaluate(bundle, lane="paper")
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["permissions"]["paper"])

    def test_upstream_verification_precedes_budget_invocation(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_upstream_verify = (
            upstream.verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1
        )
        original_budget = (
            budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3
        )

        def observed_upstream(*args: object, **kwargs: object) -> bool:
            events.append("upstream")
            return original_upstream_verify(*args, **kwargs)

        def observed_budget(*args: object, **kwargs: object) -> dict:
            events.append("budget")
            return original_budget(*args, **kwargs)

        with patch.object(
            upstream,
            "verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1",
            side_effect=observed_upstream,
        ), patch.object(
            budget_v3,
            "evaluate_strategy_correlation_cluster_effective_bet_budget_v3",
            side_effect=observed_budget,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(events[0], "upstream")
        self.assertLess(events.index("upstream"), events.index("budget"))


if __name__ == "__main__":
    unittest.main()
