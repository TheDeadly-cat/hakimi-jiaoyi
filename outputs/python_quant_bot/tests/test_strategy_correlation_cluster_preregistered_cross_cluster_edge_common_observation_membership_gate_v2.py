from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import (
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2
    as membership_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from tests import (
    test_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_basis_gate_v1
    as basis_gate_v1_tests,
)


SCHEME_HASH = "6" * 64
ALTERNATE_HASH = "7" * 64


class CrossClusterEdgeCommonObservationMembershipGateV2Tests(unittest.TestCase):
    def _context(self, *, sample_count: int = 800) -> dict:
        v1_case = basis_gate_v1_tests.CrossClusterEdgeCommonObservationBasisGateV1Tests(
            "test_exact_common_observation_basis_passes_locally"
        )
        v1_case.setUp()
        edge_evidence = v1_case._edge_evidence(sample_count=sample_count)
        edge_document = v1_case._edge_document(edge_evidence)
        basis_preregistration = v1_case._basis_preregistration()
        basis_evidence = v1_case._basis_evidence(edge_evidence)
        basis_document = v1_case._evaluate(
            preregistration=basis_preregistration,
            evidence=basis_evidence,
            edge_document=edge_document,
            edge_evidence=edge_evidence,
        )
        registered_pairs = [
            {
                "left_symbol": pair["left_symbol"],
                "right_symbol": pair["right_symbol"],
            }
            for pair in edge_evidence["pairs"]
        ]
        common_hash = basis_evidence["common_sample_set_hash"]
        membership_preregistration = membership_gate_v2.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_preregistration_v2(
            trade_identity_hash=basis_preregistration["trade_identity_hash"],
            cluster_partition_hash=basis_preregistration["cluster_partition_hash"],
            basis_preregistration_hash=basis_preregistration["preregistration_hash"],
            edge_preregistration_hash=v1_case.case.preregistration[
                "preregistration_hash"
            ],
            observation_identifier_scheme_hash=SCHEME_HASH,
            expected_common_observation_membership_hash=common_hash,
            expected_common_sample_count=sample_count,
            registered_pairs=registered_pairs,
            registration_sequence=basis_preregistration["registration_sequence"],
        )
        commitments = [
            {
                "left_symbol": pair["left_symbol"],
                "observation_membership_hash": common_hash,
                "right_symbol": pair["right_symbol"],
                "sample_count": sample_count,
            }
            for pair in edge_evidence["pairs"]
        ]
        membership_evidence = membership_gate_v2.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_evidence_v2(
            trade_identity_hash=basis_evidence["trade_identity_hash"],
            cluster_partition_hash=basis_evidence["cluster_partition_hash"],
            basis_evidence_hash=basis_evidence["evidence_hash"],
            basis_gate_v1_hash=basis_document[
                "common_observation_basis_gate_v1_hash"
            ],
            edge_evidence_hash=edge_evidence["evidence_hash"],
            observation_identifier_scheme_hash=SCHEME_HASH,
            common_observation_membership_hash=common_hash,
            common_sample_count=sample_count,
            pair_membership_commitments=commitments,
            evidence_sequence=basis_evidence["evidence_sequence"],
        )
        return {
            "v1_case": v1_case,
            "edge_evidence": edge_evidence,
            "edge_document": edge_document,
            "basis_preregistration": basis_preregistration,
            "basis_evidence": basis_evidence,
            "basis_document": basis_document,
            "membership_preregistration": membership_preregistration,
            "membership_evidence": membership_evidence,
        }

    @staticmethod
    def _reseal(document: dict, hash_field: str) -> dict:
        unsigned = deepcopy(document)
        unsigned.pop(hash_field, None)
        return seal_strict_canonical_document(unsigned, hash_field)

    def _evaluate(self, context: dict, **overrides: dict) -> dict:
        values = dict(context)
        values.update(overrides)
        return membership_gate_v2.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
            values["membership_preregistration"],
            values["membership_evidence"],
            values["basis_document"],
            basis_preregistration=values["basis_preregistration"],
            basis_evidence=values["basis_evidence"],
            edge_gate_v1_document=values["edge_document"],
            edge_preregistration=values["v1_case"].case.preregistration,
            edge_evidence=values["edge_evidence"],
            expected_membership_preregistration_hash=values[
                "membership_preregistration"
            ]["membership_preregistration_hash"],
        )

    def _verify(self, document: dict, context: dict) -> dict:
        return membership_gate_v2.verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
            document,
            context["membership_preregistration"],
            context["membership_evidence"],
            context["basis_document"],
            basis_preregistration=context["basis_preregistration"],
            basis_evidence=context["basis_evidence"],
            edge_gate_v1_document=context["edge_document"],
            edge_preregistration=context["v1_case"].case.preregistration,
            edge_evidence=context["edge_evidence"],
            expected_membership_preregistration_hash=context[
                "membership_preregistration"
            ]["membership_preregistration_hash"],
        )

    def test_exact_pair_membership_commitments_pass_locally(self) -> None:
        context = self._context()
        document = self._evaluate(context)
        receipt = self._verify(document, context)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"], "PASS_COMMON_OBSERVATION_MEMBERSHIP_COMMITMENTS"
        )
        self.assertTrue(document["facts"]["membership_commitments_verified"])
        self.assertEqual(document["summary"]["membership_hash_match_pair_count"], 2)
        self.assertTrue(
            receipt["common_observation_membership_gate_v2_exactly_verified"]
        )
        self.assertFalse(receipt["paper_authorized"])

    def test_distinct_pair_membership_with_equal_count_blocks(self) -> None:
        context = self._context()
        evidence = deepcopy(context["membership_evidence"])
        evidence["pair_membership_commitments"][1][
            "observation_membership_hash"
        ] = ALTERNATE_HASH
        context["membership_evidence"] = self._reseal(
            evidence, "membership_evidence_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("PAIR_MEMBERSHIP_COMMITMENT_MISMATCH", document["blockers"])
        self.assertEqual(document["summary"]["membership_hash_match_pair_count"], 1)
        self.assertFalse(document["facts"]["membership_commitments_verified"])

    def test_preregistered_common_membership_hash_mismatch_blocks(self) -> None:
        context = self._context()
        preregistration = deepcopy(context["membership_preregistration"])
        preregistration["expected_common_observation_membership_hash"] = ALTERNATE_HASH
        context["membership_preregistration"] = self._reseal(
            preregistration, "membership_preregistration_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "PREREGISTERED_COMMON_MEMBERSHIP_HASH_MISMATCH", document["blockers"]
        )

    def test_pair_commitment_sample_count_mismatch_blocks(self) -> None:
        context = self._context()
        evidence = deepcopy(context["membership_evidence"])
        evidence["pair_membership_commitments"][0]["sample_count"] = 799
        context["membership_evidence"] = self._reseal(
            evidence, "membership_evidence_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("PAIR_MEMBERSHIP_SAMPLE_COUNT_MISMATCH", document["blockers"])

    def test_registered_pair_set_mismatch_blocks(self) -> None:
        context = self._context()
        preregistration = deepcopy(context["membership_preregistration"])
        preregistration["registered_pairs"] = preregistration["registered_pairs"][:1]
        context["membership_preregistration"] = self._reseal(
            preregistration, "membership_preregistration_hash"
        )
        evidence = deepcopy(context["membership_evidence"])
        evidence["pair_membership_commitments"] = evidence[
            "pair_membership_commitments"
        ][:1]
        context["membership_evidence"] = self._reseal(
            evidence, "membership_evidence_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("REGISTERED_MEMBERSHIP_PAIR_SET_MISMATCH", document["blockers"])

    def test_basis_gate_v1_block_is_preserved(self) -> None:
        context = self._context(sample_count=20)
        self.assertEqual(context["basis_document"]["status"], "BLOCK")
        document = self._evaluate(context)
        receipt = self._verify(document, context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("COMMON_OBSERVATION_BASIS_GATE_V1_BLOCKED", document["blockers"])
        self.assertTrue(document["facts"]["membership_commitments_verified"])
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["gate_status"], "BLOCK")
        self.assertTrue(
            receipt["common_observation_membership_gate_v2_exactly_verified"]
        )

    def test_observation_identifier_scheme_splice_is_unknown(self) -> None:
        context = self._context()
        evidence = deepcopy(context["membership_evidence"])
        evidence["observation_identifier_scheme_hash"] = ALTERNATE_HASH
        context["membership_evidence"] = self._reseal(
            evidence, "membership_evidence_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])
        self.assertFalse(document["facts"]["basis_gate_v1_exactly_verified"])

    def test_basis_gate_hash_splice_is_unknown(self) -> None:
        context = self._context()
        evidence = deepcopy(context["membership_evidence"])
        evidence["basis_gate_v1_hash"] = ALTERNATE_HASH
        context["membership_evidence"] = self._reseal(
            evidence, "membership_evidence_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])
        self.assertIsNone(document["source"]["basis_gate_v1_hash"])

    def test_extra_preregistration_key_is_unknown(self) -> None:
        context = self._context()
        preregistration = deepcopy(context["membership_preregistration"])
        preregistration["unregistered_override"] = True
        context["membership_preregistration"] = self._reseal(
            preregistration, "membership_preregistration_hash"
        )
        document = self._evaluate(context)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_exact_verifier_rejects_permission_promotion(self) -> None:
        context = self._context()
        document = self._evaluate(context)
        altered = deepcopy(document)
        altered["authority"]["paper_authorized"] = True
        altered = self._reseal(
            altered, "common_observation_membership_gate_v2_hash"
        )
        receipt = self._verify(altered, context)
        self.assertEqual(receipt["status"], "UNKNOWN")
        self.assertFalse(
            receipt["common_observation_membership_gate_v2_exactly_verified"]
        )
        self.assertIsNone(receipt["common_observation_membership_gate_v2_hash"])

    def test_output_is_bounded_commitment_not_raw_sample_proof(self) -> None:
        context = self._context()
        document = self._evaluate(context)
        serialized_keys: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                serialized_keys.extend(value.keys())
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(document)
        self.assertNotIn("observation_ids", serialized_keys)
        self.assertNotIn("raw_observations", serialized_keys)
        self.assertNotIn("pair_membership_commitments", serialized_keys)
        self.assertTrue(
            document["facts"][
                "membership_commitment_is_not_raw_sample_verification"
            ]
        )
        self.assertFalse(document["facts"]["raw_samples_recomputed"])
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_inputs_are_not_mutated(self) -> None:
        context = self._context()
        before = deepcopy(context)
        document = self._evaluate(context)
        self.assertEqual(document["status"], "PASS")
        for key in (
            "edge_evidence",
            "edge_document",
            "basis_preregistration",
            "basis_evidence",
            "basis_document",
            "membership_preregistration",
            "membership_evidence",
        ):
            self.assertTrue(strict_json_contract_equal(context[key], before[key]))


if __name__ == "__main__":
    unittest.main()
