from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
_TESTS_DIR = str(Path(__file__).resolve().parent)
for _import_path in (_PROJECT_ROOT, _TESTS_DIR):
    if _import_path not in sys.path:
        sys.path.insert(0, _import_path)

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1
    as basis_gate,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1
    as edge_gate,
)
import test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_presentation_v9 as presentation_cases


class CrossClusterEdgeCommonObservationBasisGateV1Tests(unittest.TestCase):
    def setUp(self):
        cls = presentation_cases.StratifiedMultiWindowEdgeUncertaintyPresentationV9Tests
        self.case = cls(methodName=unittest.TestLoader().getTestCaseNames(cls)[0])
        self.case.setUp()
        self.edge_preregistration = self.case.preregistration
        self.policy_hash = "3" * 64
        self.sample_set_hash = "4" * 64
        self.edge_evidence_clear = self._edge_evidence(sample_count=800)
        self.edge_clear = self._edge_document(self.edge_evidence_clear)
        self.edge_evidence_block = self._edge_evidence(
            sample_count=800,
            observed_correlation_micros=800_000,
        )
        self.edge_block = self._edge_document(self.edge_evidence_block)
        self.preregistration = self._basis_preregistration()
        self.evidence = self._basis_evidence(self.edge_evidence_clear)

    def _edge_evidence(
        self,
        *,
        sample_count,
        observed_correlation_micros=300_000,
    ):
        return edge_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_evidence_v1(
            [
                {
                    "left_symbol": "A",
                    "right_symbol": "C",
                    "observed_correlation_micros": observed_correlation_micros,
                    "sample_count": sample_count,
                },
                {
                    "left_symbol": "B",
                    "right_symbol": "C",
                    "observed_correlation_micros": 250_000,
                    "sample_count": sample_count,
                },
            ],
            trade_identity_hash=self.case.trade_hash,
            cluster_partition_hash=self.case.partition_hash,
            evidence_sequence=self.edge_preregistration["registration_sequence"] + 1,
        )

    def _edge_document(self, evidence):
        return edge_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            self.edge_preregistration,
            evidence,
            expected_preregistration_hash=self.edge_preregistration[
                "preregistration_hash"
            ],
        )

    def _basis_preregistration(
        self,
        *,
        edge_preregistration_hash=None,
        observation_policy_hash=None,
        minimum_common_sample_count=30,
    ):
        return basis_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_preregistration_v1(
            trade_identity_hash=self.case.trade_hash,
            cluster_partition_hash=self.case.partition_hash,
            edge_preregistration_hash=(
                self.edge_preregistration["preregistration_hash"]
                if edge_preregistration_hash is None
                else edge_preregistration_hash
            ),
            observation_policy_hash=(
                self.policy_hash
                if observation_policy_hash is None
                else observation_policy_hash
            ),
            registration_sequence=self.edge_preregistration["registration_sequence"],
            minimum_common_sample_count=minimum_common_sample_count,
        )

    def _basis_evidence(
        self,
        edge_evidence,
        *,
        edge_evidence_hash=None,
        observation_policy_hash=None,
        common_sample_count=None,
        evidence_sequence=None,
    ):
        return basis_gate.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_evidence_v1(
            trade_identity_hash=self.case.trade_hash,
            cluster_partition_hash=self.case.partition_hash,
            edge_evidence_hash=(
                edge_evidence["evidence_hash"]
                if edge_evidence_hash is None
                else edge_evidence_hash
            ),
            observation_policy_hash=(
                self.policy_hash
                if observation_policy_hash is None
                else observation_policy_hash
            ),
            common_sample_set_hash=self.sample_set_hash,
            common_sample_count=(
                edge_evidence["pairs"][0]["sample_count"]
                if common_sample_count is None
                else common_sample_count
            ),
            evidence_sequence=(
                edge_evidence["evidence_sequence"]
                if evidence_sequence is None
                else evidence_sequence
            ),
        )

    @staticmethod
    def _edge_receipt(document, *, valid=True):
        return {
            "blockers": [] if valid else ["EDGE_GATE_V1_EXACT_REBUILD_FAILED"],
            "current_admission_allowed": False,
            "edge_uncertainty_gate_v1_exactly_verified": valid,
            "edge_uncertainty_gate_v1_hash": (
                document["edge_uncertainty_gate_v1_hash"] if valid else None
            ),
            "gate_decision": document["decision"] if valid else "UNKNOWN",
            "gate_status": document["status"] if valid else "UNKNOWN",
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": edge_gate.VERIFICATION_SCHEMA_VERSION,
            "source_known": valid,
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    def _evaluate(
        self,
        *,
        preregistration=None,
        evidence=None,
        edge_document=None,
        edge_evidence=None,
        edge_receipt=None,
    ):
        preregistration_value = (
            self.preregistration if preregistration is None else preregistration
        )
        evidence_value = self.evidence if evidence is None else evidence
        edge_document_value = self.edge_clear if edge_document is None else edge_document
        edge_evidence_value = (
            self.edge_evidence_clear if edge_evidence is None else edge_evidence
        )
        if edge_receipt is None:
            return basis_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
                preregistration_value,
                evidence_value,
                edge_document_value,
                edge_preregistration=self.edge_preregistration,
                edge_evidence=edge_evidence_value,
                expected_preregistration_hash=preregistration_value[
                    "preregistration_hash"
                ],
            )
        with patch.object(
            basis_gate,
            "_VERIFY_EDGE_GATE",
            return_value=edge_receipt,
        ):
            return basis_gate.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
                preregistration_value,
                evidence_value,
                edge_document_value,
                edge_preregistration=self.edge_preregistration,
                edge_evidence=edge_evidence_value,
                expected_preregistration_hash=preregistration_value[
                    "preregistration_hash"
                ],
            )

    def test_exact_common_observation_basis_passes_locally(self):
        document = self._evaluate()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(document["blockers"], [])
        self.assertTrue(document["facts"]["all_pair_sample_counts_match"])
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])

    def test_edge_uncertainty_block_is_preserved(self):
        evidence = self._basis_evidence(self.edge_evidence_block)
        document = self._evaluate(
            evidence=evidence,
            edge_document=self.edge_block,
            edge_evidence=self.edge_evidence_block,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("EDGE_UNCERTAINTY_GATE_V1_BLOCKED", document["blockers"])

    def test_common_sample_below_preregistered_minimum_blocks(self):
        edge_evidence = self._edge_evidence(sample_count=20, observed_correlation_micros=0)
        edge_document = self._edge_document(edge_evidence)
        evidence = self._basis_evidence(edge_evidence)
        document = self._evaluate(
            evidence=evidence,
            edge_document=edge_document,
            edge_evidence=edge_evidence,
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "COMMON_SAMPLE_COUNT_BELOW_PREREGISTERED_MINIMUM",
            document["blockers"],
        )
        self.assertNotIn("PAIR_SAMPLE_COUNTS_NOT_COMMON", document["blockers"])

    def test_pair_sample_count_mismatch_blocks(self):
        evidence = self._basis_evidence(
            self.edge_evidence_clear,
            common_sample_count=799,
        )
        document = self._evaluate(evidence=evidence)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("PAIR_SAMPLE_COUNTS_NOT_COMMON", document["blockers"])
        self.assertFalse(document["facts"]["all_pair_sample_counts_match"])

    def test_observation_policy_hash_splice_is_unknown(self):
        evidence = self._basis_evidence(
            self.edge_evidence_clear,
            observation_policy_hash="5" * 64,
        )
        document = self._evaluate(evidence=evidence)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_edge_evidence_hash_splice_is_unknown(self):
        evidence = self._basis_evidence(
            self.edge_evidence_clear,
            edge_evidence_hash="6" * 64,
        )
        document = self._evaluate(evidence=evidence)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("EDGE_EVIDENCE_HASH_SPLICE", document["blockers"])

    def test_edge_preregistration_hash_splice_is_unknown(self):
        preregistration = self._basis_preregistration(
            edge_preregistration_hash="7" * 64,
        )
        document = self._evaluate(preregistration=preregistration)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn("EDGE_PREREGISTRATION_HASH_SPLICE", document["blockers"])

    def test_evidence_coissue_sequence_splice_is_unknown(self):
        evidence = self._basis_evidence(
            self.edge_evidence_clear,
            evidence_sequence=self.edge_evidence_clear["evidence_sequence"] + 1,
        )
        document = self._evaluate(evidence=evidence)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIn(
            "REGISTRATION_OR_EVIDENCE_SEQUENCE_SPLICE",
            document["blockers"],
        )

    def test_malformed_edge_receipt_hides_all_summary(self):
        receipt = self._edge_receipt(self.edge_clear)
        receipt["route_registered"] = False
        document = self._evaluate(edge_receipt=receipt)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])
        self.assertIsNone(document["source"]["common_sample_set_hash"])

    def test_output_is_bounded_provenance_not_raw_sample_proof(self):
        document = self._evaluate()
        self.assertEqual(
            set(document["summary"]),
            {
                "common_sample_count",
                "edge_blocked_pair_count",
                "edge_pair_count",
                "minimum_common_sample_count",
                "pair_count_matching_common_sample_count",
                "verified_edge_pair_count",
            },
        )
        self.assertFalse(document["facts"]["raw_samples_recomputed"])
        self.assertTrue(document["facts"]["provenance_declaration_only"])
        self.assertNotIn("pairs", document)
        self.assertNotIn("sample_ids", document)

    def test_inputs_are_not_mutated(self):
        preregistration = deepcopy(self.preregistration)
        evidence = deepcopy(self.evidence)
        edge_document = deepcopy(self.edge_clear)
        preregistration_before = deepcopy(preregistration)
        evidence_before = deepcopy(evidence)
        edge_before = deepcopy(edge_document)
        self._evaluate(
            preregistration=preregistration,
            evidence=evidence,
            edge_document=edge_document,
        )
        self.assertEqual(preregistration, preregistration_before)
        self.assertEqual(evidence, evidence_before)
        self.assertEqual(edge_document, edge_before)

    def test_exact_verifier_rejects_permission_promotion(self):
        document = self._evaluate()
        receipt = basis_gate.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
            document,
            self.preregistration,
            self.evidence,
            self.edge_clear,
            edge_preregistration=self.edge_preregistration,
            edge_evidence=self.edge_evidence_clear,
            expected_preregistration_hash=self.preregistration[
                "preregistration_hash"
            ],
        )
        self.assertTrue(receipt["common_observation_basis_gate_v1_exactly_verified"])
        mutated = deepcopy(document)
        mutated["authority"]["paper_authorized"] = True
        rejected = basis_gate.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1(
            mutated,
            self.preregistration,
            self.evidence,
            self.edge_clear,
            edge_preregistration=self.edge_preregistration,
            edge_evidence=self.edge_evidence_clear,
            expected_preregistration_hash=self.preregistration[
                "preregistration_hash"
            ],
        )
        self.assertFalse(
            rejected["common_observation_basis_gate_v1_exactly_verified"]
        )


if __name__ == "__main__":
    unittest.main()
