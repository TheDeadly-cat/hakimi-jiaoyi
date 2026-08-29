from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_complete_link as complete_link,
)
from exchange_terminal.services import strategy_correlation_cluster_gate as cluster_contract
from exchange_terminal.services import strategy_correlation_matrix_geometry_gate_v1 as geometry
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_complete_link_binding_v1 as binding,
)
from tests.test_strategy_correlation_cluster_complete_link import (
    StrategyCorrelationClusterCompleteLinkTests as CompleteLinkFixture,
)


class StrategyCorrelationMatrixGeometryCompleteLinkBindingTests(unittest.TestCase):
    @staticmethod
    def _rehash(document: dict, field: str) -> None:
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

    def _bundle(self, *, ac: float = 0.8) -> dict:
        cluster_preregistration = CompleteLinkFixture._preregistration()
        matrix = CompleteLinkFixture._matrix(ac=ac)
        cells = CompleteLinkFixture._cells()
        geometry_preregistration = (
            geometry.build_strategy_correlation_matrix_geometry_preregistration_v1(
                matrix["symbols"]
            )
        )
        self.assertIsNotNone(geometry_preregistration)
        geometry_gate = geometry.evaluate_strategy_correlation_matrix_geometry_gate_v1(
            geometry_preregistration,
            matrix,
            expected_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
        )
        self.assertIsNotNone(geometry_gate)
        binding_preregistration = binding.build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
            geometry_preregistration,
            cluster_preregistration,
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=cluster_preregistration[
                "preregistration_hash"
            ],
        )
        self.assertIsNotNone(binding_preregistration)
        return {
            "binding_preregistration": binding_preregistration,
            "geometry_preregistration": geometry_preregistration,
            "geometry_gate": geometry_gate,
            "cluster_preregistration": cluster_preregistration,
            "matrix": matrix,
            "cells": cells,
        }

    def _evaluate(self, bundle: dict, **overrides: object) -> dict:
        values = {
            "binding_preregistration": bundle["binding_preregistration"],
            "geometry_preregistration": bundle["geometry_preregistration"],
            "geometry_gate_document": bundle["geometry_gate"],
            "cluster_preregistration": bundle["cluster_preregistration"],
            "correlation_matrix": bundle["matrix"],
            "selection_cells": bundle["cells"],
            "expected_binding_preregistration_hash": bundle[
                "binding_preregistration"
            ]["preregistration_hash"],
            "expected_geometry_preregistration_hash": bundle[
                "geometry_preregistration"
            ]["preregistration_hash"],
            "expected_cluster_preregistration_hash": bundle[
                "cluster_preregistration"
            ]["preregistration_hash"],
            "strategy_id": "strategy-synthetic-1",
            "variant_id": "variant-synthetic-1",
            "lane": "research",
        }
        values.update(overrides)
        return binding.evaluate_strategy_correlation_matrix_geometry_complete_link_binding_v1(
            values["binding_preregistration"],
            values["geometry_preregistration"],
            values["geometry_gate_document"],
            values["cluster_preregistration"],
            values["correlation_matrix"],
            values["selection_cells"],
            expected_binding_preregistration_hash=values[
                "expected_binding_preregistration_hash"
            ],
            expected_geometry_preregistration_hash=values[
                "expected_geometry_preregistration_hash"
            ],
            expected_cluster_preregistration_hash=values[
                "expected_cluster_preregistration_hash"
            ],
            strategy_id=values["strategy_id"],
            variant_id=values["variant_id"],
            lane=values["lane"],
        )

    def test_dependency_source_pins_match(self) -> None:
        self.assertEqual(
            sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
            binding.GEOMETRY_PROVIDER_SOURCE_SHA256,
        )
        self.assertEqual(
            sha256(Path(complete_link.__file__).read_bytes()).hexdigest(),
            binding.COMPLETE_LINK_CONSUMER_SOURCE_SHA256,
        )
        self.assertEqual(
            sha256(Path(cluster_contract.__file__).read_bytes()).hexdigest(),
            binding.CLUSTER_CONTRACT_SOURCE_SHA256,
        )

    def test_binding_contract_is_versioned_and_stable_shape(self) -> None:
        self.assertEqual(len(binding.BINDING_CONTRACT_HASH), 64)
        self.assertEqual(
            binding.ACTIVATION_SEQUENCE[0], "VERIFY_EXACT_MATRIX_CONTRACT"
        )
        self.assertIn(
            "VERIFY_EXACT_GEOMETRY_GATE_FOR_SAME_MATRIX",
            binding.ACTIVATION_SEQUENCE,
        )
        self.assertNotIn("READY", binding.STATIC_FINGERPRINT)

    def test_preregistration_is_unmounted_and_exactly_verifiable(self) -> None:
        bundle = self._bundle()
        preregistration = bundle["binding_preregistration"]
        self.assertEqual(preregistration["status"], "PREREGISTERED_UNMOUNTED")
        self.assertFalse(preregistration["mounted"])
        self.assertFalse(preregistration["current_admission_allowed"])
        self.assertFalse(preregistration["current_writer_activation_allowed"])
        self.assertFalse(preregistration["permissions"]["paper"])
        self.assertFalse(preregistration["permissions"]["live"])
        self.assertTrue(
            binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
                preregistration,
                bundle["geometry_preregistration"],
                bundle["cluster_preregistration"],
                expected_binding_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "cluster_preregistration"
                ]["preregistration_hash"],
            )
        )

    def test_preregistration_tamper_is_rejected(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["binding_preregistration"])
        tampered["mounted"] = True
        self.assertFalse(
            binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
                tampered,
                bundle["geometry_preregistration"],
                bundle["cluster_preregistration"],
                expected_binding_preregistration_hash=bundle[
                    "binding_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "cluster_preregistration"
                ]["preregistration_hash"],
            )
        )

    def test_valid_geometry_runs_real_consumer_without_authority(self) -> None:
        result = self._evaluate(self._bundle())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["reason_code"],
            "GEOMETRY_AND_COMPLETE_LINK_CONSUMER_VERIFIED",
        )
        self.assertTrue(result["consumer_invocation_attempted"])
        self.assertTrue(result["embedded_complete_link_audit_verified"])
        self.assertTrue(result["complete_link_gate_verified"])
        self.assertEqual(result["complete_link_audit_status"], "PASS")
        self.assertEqual(result["complete_link_gate_status"], "BLOCK")
        self.assertFalse(result["current_admission_allowed"])
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["permissions"]["paper"])
        self.assertFalse(result["permissions"]["live"])

    def test_evaluation_verifier_accepts_exact_document(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        self.assertTrue(
            binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1(
                result,
                bundle["binding_preregistration"],
                bundle["geometry_preregistration"],
                bundle["geometry_gate"],
                bundle["cluster_preregistration"],
                bundle["matrix"],
                bundle["cells"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_binding_preregistration_hash=bundle[
                    "binding_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "cluster_preregistration"
                ]["preregistration_hash"],
                strategy_id="strategy-synthetic-1",
                variant_id="variant-synthetic-1",
                lane="research",
            )
        )

    def test_evaluation_verifier_rejects_tamper(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle)
        tampered = deepcopy(result)
        tampered["current_admission_allowed"] = True
        self.assertFalse(
            binding.verify_strategy_correlation_matrix_geometry_complete_link_binding_evaluation_v1(
                tampered,
                bundle["binding_preregistration"],
                bundle["geometry_preregistration"],
                bundle["geometry_gate"],
                bundle["cluster_preregistration"],
                bundle["matrix"],
                bundle["cells"],
                expected_evaluation_hash=result["evaluation_hash"],
                expected_binding_preregistration_hash=bundle[
                    "binding_preregistration"
                ]["preregistration_hash"],
                expected_geometry_preregistration_hash=bundle[
                    "geometry_preregistration"
                ]["preregistration_hash"],
                expected_cluster_preregistration_hash=bundle[
                    "cluster_preregistration"
                ]["preregistration_hash"],
                strategy_id="strategy-synthetic-1",
                variant_id="variant-synthetic-1",
                lane="research",
            )
        )

    def test_missing_geometry_never_invokes_consumer(self) -> None:
        bundle = self._bundle()
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, geometry_gate_document=None)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "GEOMETRY_GATE_EVIDENCE_MISSING")
        self.assertFalse(result["consumer_invocation_attempted"])

    def test_tampered_geometry_never_invokes_consumer(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["geometry_gate"])
        tampered["status"] = "PASS" if tampered["status"] != "PASS" else "BLOCK"
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, geometry_gate_document=tampered)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "GEOMETRY_GATE_EVIDENCE_INVALID_FOR_MATRIX"
        )

    def test_geometry_for_other_matrix_never_invokes_consumer(self) -> None:
        bundle = self._bundle(ac=0.8)
        other_matrix = CompleteLinkFixture._matrix(ac=0.7)
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, correlation_matrix=other_matrix)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "GEOMETRY_GATE_EVIDENCE_INVALID_FOR_MATRIX"
        )

    def test_pairwise_valid_non_psd_matrix_blocks_before_consumer(self) -> None:
        matrix = cluster_contract.build_correlation_matrix_contract(
            ["A", "B", "C"],
            {
                ("A", "B"): 0.9,
                ("A", "C"): 0.9,
                ("B", "C"): -0.9,
            },
        )
        geometry_preregistration = (
            geometry.build_strategy_correlation_matrix_geometry_preregistration_v1(
                matrix["symbols"]
            )
        )
        geometry_gate = geometry.evaluate_strategy_correlation_matrix_geometry_gate_v1(
            geometry_preregistration,
            matrix,
            expected_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
        )
        self.assertEqual(geometry_gate["status"], "BLOCK")
        cluster_preregistration = CompleteLinkFixture._preregistration()
        binding_preregistration = binding.build_strategy_correlation_matrix_geometry_complete_link_binding_preregistration_v1(
            geometry_preregistration,
            cluster_preregistration,
            expected_geometry_preregistration_hash=geometry_preregistration[
                "preregistration_hash"
            ],
            expected_cluster_preregistration_hash=cluster_preregistration[
                "preregistration_hash"
            ],
        )
        bundle = {
            "binding_preregistration": binding_preregistration,
            "geometry_preregistration": geometry_preregistration,
            "geometry_gate": geometry_gate,
            "cluster_preregistration": cluster_preregistration,
            "matrix": matrix,
            "cells": CompleteLinkFixture._cells(),
        }
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason_code"], "GEOMETRY_GATE_DID_NOT_PASS")

    def test_malformed_matrix_blocks_before_consumer(self) -> None:
        bundle = self._bundle()
        malformed = deepcopy(bundle["matrix"])
        malformed["matrix_hash"] = "0" * 64
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, correlation_matrix=malformed)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "CORRELATION_MATRIX_CONTRACT_INVALID")

    def test_tampered_binding_blocks_before_consumer(self) -> None:
        bundle = self._bundle()
        tampered = deepcopy(bundle["binding_preregistration"])
        tampered["mounted"] = True
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, binding_preregistration=tampered)
        consumer.assert_not_called()
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "BINDING_PREREGISTRATION_INVALID")

    def test_non_research_lane_blocks_before_consumer(self) -> None:
        bundle = self._bundle()
        with patch.object(complete_link, "evaluate_correlation_cluster_gate_v2") as consumer:
            result = self._evaluate(bundle, lane="paper")
        consumer.assert_not_called()
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason_code"], "NON_RESEARCH_LANE_REJECTED")

    def test_raw_excess_lane_is_supported_as_research_only(self) -> None:
        bundle = self._bundle()
        result = self._evaluate(bundle, lane="RAW_EXCESS")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["complete_link_gate"]["lane"], "RAW_EXCESS")
        self.assertFalse(result["current_admission_allowed"])
        self.assertFalse(result["current_writer_activation_allowed"])
        self.assertFalse(result["permissions"]["paper"])
        self.assertFalse(result["permissions"]["live"])

    def test_consumer_exception_fails_closed(self) -> None:
        bundle = self._bundle()
        with patch.object(
            complete_link,
            "evaluate_correlation_cluster_gate_v2",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "COMPLETE_LINK_CONSUMER_EXCEPTION")
        self.assertTrue(result["consumer_invocation_attempted"])
        self.assertIsNone(result["complete_link_audit"])
        self.assertIsNone(result["complete_link_gate"])

    def test_forged_embedded_audit_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = complete_link.evaluate_correlation_cluster_gate_v2(
            bundle["cluster_preregistration"],
            bundle["matrix"],
            bundle["cells"],
            strategy_id="strategy-synthetic-1",
            variant_id="variant-synthetic-1",
            lane="research",
        )
        forged = deepcopy(forged)
        forged["complete_link_audit"]["status"] = "FORGED"
        self._rehash(forged["complete_link_audit"], "audit_hash")
        self._rehash(forged, "gate_hash")
        with patch.object(
            complete_link,
            "evaluate_correlation_cluster_gate_v2",
            return_value=forged,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "EMBEDDED_COMPLETE_LINK_AUDIT_INVALID"
        )
        self.assertFalse(result["embedded_complete_link_audit_verified"])
        self.assertIsNone(result["complete_link_gate"])

    def test_forged_gate_is_rejected(self) -> None:
        bundle = self._bundle()
        forged = complete_link.evaluate_correlation_cluster_gate_v2(
            bundle["cluster_preregistration"],
            bundle["matrix"],
            bundle["cells"],
            strategy_id="strategy-synthetic-1",
            variant_id="variant-synthetic-1",
            lane="research",
        )
        forged = deepcopy(forged)
        forged["first_blocking_tier"] = "FORGED"
        self._rehash(forged, "gate_hash")
        with patch.object(
            complete_link,
            "evaluate_correlation_cluster_gate_v2",
            return_value=forged,
        ):
            result = self._evaluate(bundle)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "COMPLETE_LINK_GATE_DOCUMENT_INVALID")
        self.assertTrue(result["embedded_complete_link_audit_verified"])
        self.assertFalse(result["complete_link_gate_verified"])

    def test_geometry_verification_precedes_gate_and_embedded_audit(self) -> None:
        bundle = self._bundle()
        events: list[str] = []
        original_geometry_verify = (
            geometry.verify_strategy_correlation_matrix_geometry_gate_v1
        )
        original_gate = complete_link.evaluate_correlation_cluster_gate_v2
        original_audit = complete_link.build_correlation_cluster_complete_link_audit

        def observed_geometry(*args: object, **kwargs: object) -> bool:
            events.append("geometry")
            return original_geometry_verify(*args, **kwargs)

        def observed_gate(*args: object, **kwargs: object) -> dict:
            events.append("gate")
            return original_gate(*args, **kwargs)

        def observed_audit(*args: object, **kwargs: object) -> dict:
            events.append("audit")
            return original_audit(*args, **kwargs)

        with patch.object(
            geometry,
            "verify_strategy_correlation_matrix_geometry_gate_v1",
            side_effect=observed_geometry,
        ), patch.object(
            complete_link,
            "evaluate_correlation_cluster_gate_v2",
            side_effect=observed_gate,
        ), patch.object(
            complete_link,
            "build_correlation_cluster_complete_link_audit",
            side_effect=observed_audit,
        ):
            result = self._evaluate(bundle)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(events[0], "geometry")
        self.assertIn("gate", events[1:])
        self.assertIn("audit", events[1:])
        self.assertLess(events.index("geometry"), events.index("gate"))
        self.assertLess(events.index("geometry"), events.index("audit"))


if __name__ == "__main__":
    unittest.main()
