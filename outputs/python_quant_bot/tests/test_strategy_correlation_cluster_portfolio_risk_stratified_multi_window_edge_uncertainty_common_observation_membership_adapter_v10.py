from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import (  # noqa: E402
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10
    as adapter_v10,
)
from exchange_terminal.services import (  # noqa: E402
    strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2
    as membership_gate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (  # noqa: E402
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from tests import (  # noqa: E402
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_adapter_v9
    as adapter_v9_tests,
)


SCHEME_HASH = "6" * 64
ALTERNATE_HASH = "7" * 64


class StratifiedMultiWindowEdgeCommonObservationMembershipAdapterV10Tests(
    unittest.TestCase
):
    def _fixture(
        self, *, membership_block: bool = False, adapter_block: bool = False
    ) -> dict:
        case = adapter_v9_tests.StratifiedMultiWindowEdgeCommonObservationBasisAdapterV9Tests(
            "test_two_exact_clear_components_pass_locally"
        )
        case.setUp()
        adapter_v8_document = deepcopy(case.adapter_clear)
        if adapter_block:
            adapter_v8_document["blockers"] = ["SYNTHETIC_ADAPTER_V8_BLOCK"]
            adapter_v8_document["decision"] = "BLOCK_SYNTHETIC_ADAPTER_V8"
            adapter_v8_document["status"] = "BLOCK"
            adapter_v8_document.pop("adapter_v8_hash")
            adapter_v8_document = seal_strict_canonical_document(
                adapter_v8_document, "adapter_v8_hash"
            )
        adapter_document = case._build(adapter_document=adapter_v8_document)
        basis_context = case.basis_context_clear
        basis_preregistration = basis_context["basis_preregistration"]
        basis_evidence = basis_context["basis_evidence"]
        edge_preregistration = basis_context["edge_preregistration"]
        edge_evidence = basis_context["edge_evidence"]
        common_hash = basis_evidence["common_sample_set_hash"]
        common_count = basis_evidence["common_sample_count"]
        registered_pairs = [
            {
                "left_symbol": row["left_symbol"],
                "right_symbol": row["right_symbol"],
            }
            for row in edge_evidence["pairs"]
        ]
        membership_preregistration = membership_gate_v2.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_preregistration_v2(
            trade_identity_hash=basis_preregistration["trade_identity_hash"],
            cluster_partition_hash=basis_preregistration["cluster_partition_hash"],
            basis_preregistration_hash=basis_preregistration["preregistration_hash"],
            edge_preregistration_hash=edge_preregistration["preregistration_hash"],
            observation_identifier_scheme_hash=SCHEME_HASH,
            expected_common_observation_membership_hash=common_hash,
            expected_common_sample_count=common_count,
            registered_pairs=registered_pairs,
            registration_sequence=basis_preregistration["registration_sequence"],
        )
        commitments = [
            {
                "left_symbol": row["left_symbol"],
                "observation_membership_hash": (
                    ALTERNATE_HASH if membership_block and index == 1 else common_hash
                ),
                "right_symbol": row["right_symbol"],
                "sample_count": common_count,
            }
            for index, row in enumerate(edge_evidence["pairs"])
        ]
        membership_evidence = membership_gate_v2.build_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_evidence_v2(
            trade_identity_hash=basis_evidence["trade_identity_hash"],
            cluster_partition_hash=basis_evidence["cluster_partition_hash"],
            basis_evidence_hash=basis_evidence["evidence_hash"],
            basis_gate_v1_hash=case.basis_clear[
                "common_observation_basis_gate_v1_hash"
            ],
            edge_evidence_hash=edge_evidence["evidence_hash"],
            observation_identifier_scheme_hash=SCHEME_HASH,
            common_observation_membership_hash=common_hash,
            common_sample_count=common_count,
            pair_membership_commitments=commitments,
            evidence_sequence=basis_evidence["evidence_sequence"],
        )
        membership_document = membership_gate_v2.evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_common_observation_membership_gate_v2(
            membership_preregistration,
            membership_evidence,
            case.basis_clear,
            basis_preregistration=basis_preregistration,
            basis_evidence=basis_evidence,
            edge_gate_v1_document=basis_context["edge_gate_v1_document"],
            edge_preregistration=edge_preregistration,
            edge_evidence=edge_evidence,
            expected_membership_preregistration_hash=membership_preregistration[
                "membership_preregistration_hash"
            ],
        )
        return {
            "case": case,
            "adapter_document": adapter_document,
            "membership_document": membership_document,
            "adapter_context": {
                "adapter_v8_document": adapter_v8_document,
                "adapter_v8_verification_context": case.adapter_context,
                "basis_gate_v1_document": case.basis_clear,
                "common_observation_basis_gate_v1_verification_context": (
                    case.basis_context_clear
                ),
            },
            "membership_context": {
                "basis_evidence": basis_evidence,
                "basis_gate_v1_document": case.basis_clear,
                "basis_preregistration": basis_preregistration,
                "edge_evidence": edge_evidence,
                "edge_gate_v1_document": basis_context["edge_gate_v1_document"],
                "edge_preregistration": edge_preregistration,
                "expected_membership_preregistration_hash": (
                    membership_preregistration["membership_preregistration_hash"]
                ),
                "membership_evidence": membership_evidence,
                "membership_preregistration": membership_preregistration,
            },
        }

    @staticmethod
    def _adapter_receipt(document: dict, *, valid: bool = True) -> dict:
        return {
            "adapter_v9_exactly_verified": valid,
            "adapter_v9_hash": document["adapter_v9_hash"] if valid else None,
            "adapter_v9_status": document["status"] if valid else "UNKNOWN",
            "blockers": deepcopy(document["blockers"]) if valid else ["INVALID"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": (
                "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
                "edge-uncertainty-common-observation-basis-adapter-v9-verification-v1"
            ),
            "source_known": valid,
            "status": "PASS" if valid else "UNKNOWN",
            "writer_allowed": False,
        }

    @staticmethod
    def _membership_receipt(document: dict, *, valid: bool = True) -> dict:
        return {
            "blockers": deepcopy(document["blockers"]) if valid else ["INVALID"],
            "common_observation_membership_gate_v2_exactly_verified": valid,
            "common_observation_membership_gate_v2_hash": (
                document["common_observation_membership_gate_v2_hash"]
                if valid
                else None
            ),
            "current_admission_allowed": False,
            "gate_decision": document["decision"] if valid else "UNKNOWN",
            "gate_status": document["status"] if valid else "UNKNOWN",
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": (
                "strategy-correlation-cluster-preregistered-cross-cluster-edge-common-"
                "observation-membership-gate-v2-verification-v2"
            ),
            "source_known": valid,
            "status": "PASS" if valid else "UNKNOWN",
            "writer_allowed": False,
        }

    def _build(
        self,
        fixture: dict,
        *,
        adapter_receipt: dict | None = None,
        membership_receipt: dict | None = None,
    ) -> dict:
        adapter_receipt = adapter_receipt or self._adapter_receipt(
            fixture["adapter_document"]
        )
        membership_receipt = membership_receipt or self._membership_receipt(
            fixture["membership_document"]
        )
        with patch.object(
            adapter_v10, "_VERIFY_ADAPTER_V9", return_value=adapter_receipt
        ), patch.object(
            adapter_v10,
            "_VERIFY_MEMBERSHIP_GATE_V2",
            return_value=membership_receipt,
        ):
            return adapter_v10.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10(
                fixture["adapter_document"],
                fixture["membership_document"],
                adapter_v9_verification_context=fixture["adapter_context"],
                membership_gate_v2_verification_context=fixture[
                    "membership_context"
                ],
            )

    def _verify(self, document: dict, fixture: dict) -> dict:
        with patch.object(
            adapter_v10,
            "_VERIFY_ADAPTER_V9",
            return_value=self._adapter_receipt(fixture["adapter_document"]),
        ), patch.object(
            adapter_v10,
            "_VERIFY_MEMBERSHIP_GATE_V2",
            return_value=self._membership_receipt(fixture["membership_document"]),
        ):
            return adapter_v10.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10(
                document,
                fixture["adapter_document"],
                fixture["membership_document"],
                adapter_v9_verification_context=fixture["adapter_context"],
                membership_gate_v2_verification_context=fixture[
                    "membership_context"
                ],
            )

    @staticmethod
    def _reseal(document: dict) -> dict:
        unsigned = deepcopy(document)
        unsigned.pop("adapter_v10_hash", None)
        return seal_strict_canonical_document(unsigned, "adapter_v10_hash")

    def test_two_exact_clear_components_pass_locally(self) -> None:
        fixture = self._fixture()
        document = self._build(fixture)
        receipt = self._verify(document, fixture)
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "PASS_STRATIFIED_MULTI_WINDOW_EDGE_MEMBERSHIP_ADAPTER_V10",
        )
        self.assertTrue(document["checks"]["membership_gate_v2_exactly_verified"])
        self.assertEqual(document["summary"]["membership_hash_match_pair_count"], 2)
        self.assertTrue(receipt["adapter_v10_exactly_verified"])
        self.assertEqual(receipt["status"], "PASS")

    def test_membership_gate_block_overrides_adapter_v9_pass(self) -> None:
        fixture = self._fixture(membership_block=True)
        self.assertEqual(fixture["adapter_document"]["status"], "PASS")
        self.assertEqual(fixture["membership_document"]["status"], "BLOCK")
        document = self._build(fixture)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn(
            "COMMON_OBSERVATION_MEMBERSHIP_GATE_V2_BLOCKED", document["blockers"]
        )
        self.assertEqual(document["summary"]["membership_hash_match_pair_count"], 1)

    def test_adapter_v9_block_is_preserved(self) -> None:
        fixture = self._fixture(adapter_block=True)
        self.assertEqual(fixture["adapter_document"]["status"], "BLOCK")
        document = self._build(fixture)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("ADAPTER_V9_BLOCKED", document["blockers"])

    def test_shared_basis_document_context_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["membership_context"]["basis_gate_v1_document"])
        altered["authority"]["paper_authorized"] = True
        altered.pop("common_observation_basis_gate_v1_hash")
        fixture["membership_context"]["basis_gate_v1_document"] = (
            seal_strict_canonical_document(
                altered, "common_observation_basis_gate_v1_hash"
            )
        )
        document = self._build(fixture)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_basis_gate_hash_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["membership_document"])
        altered["source"]["basis_gate_v1_hash"] = ALTERNATE_HASH
        altered.pop("common_observation_membership_gate_v2_hash")
        fixture["membership_document"] = seal_strict_canonical_document(
            altered, "common_observation_membership_gate_v2_hash"
        )
        document = self._build(fixture)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_common_membership_hash_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["membership_document"])
        altered["source"]["common_observation_membership_hash"] = ALTERNATE_HASH
        altered.pop("common_observation_membership_gate_v2_hash")
        fixture["membership_document"] = seal_strict_canonical_document(
            altered, "common_observation_membership_gate_v2_hash"
        )
        document = self._build(fixture)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_membership_pair_count_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["membership_document"])
        altered["summary"]["edge_pair_count"] = 3
        altered.pop("common_observation_membership_gate_v2_hash")
        fixture["membership_document"] = seal_strict_canonical_document(
            altered, "common_observation_membership_gate_v2_hash"
        )
        document = self._build(fixture)
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_malformed_adapter_receipt_hides_summary(self) -> None:
        fixture = self._fixture()
        document = self._build(
            fixture,
            adapter_receipt=self._adapter_receipt(
                fixture["adapter_document"], valid=False
            ),
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_malformed_membership_receipt_hides_summary(self) -> None:
        fixture = self._fixture()
        document = self._build(
            fixture,
            membership_receipt=self._membership_receipt(
                fixture["membership_document"], valid=False
            ),
        )
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertIsNone(document["summary"])

    def test_projection_is_bounded_and_commitment_calibrated(self) -> None:
        fixture = self._fixture()
        document = self._build(fixture)
        keys: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                keys.extend(value.keys())
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        collect(document)
        self.assertNotIn("pair_membership_commitments", keys)
        self.assertNotIn("observation_ids", keys)
        self.assertNotIn("raw_observations", keys)
        self.assertTrue(document["facts"]["membership_commitment_only"])
        self.assertFalse(document["facts"]["raw_samples_recomputed"])
        self.assertFalse(document["authority"]["current_admission_allowed"])

    def test_inputs_are_not_mutated(self) -> None:
        fixture = self._fixture()
        before = {
            key: deepcopy(fixture[key])
            for key in (
                "adapter_document",
                "membership_document",
                "adapter_context",
                "membership_context",
            )
        }
        document = self._build(fixture)
        self.assertEqual(document["status"], "PASS")
        for key, value in before.items():
            self.assertTrue(strict_json_contract_equal(fixture[key], value))

    def test_exact_verifier_rejects_permission_promotion(self) -> None:
        fixture = self._fixture()
        document = self._build(fixture)
        altered = deepcopy(document)
        altered["authority"]["paper_authorized"] = True
        altered = self._reseal(altered)
        receipt = self._verify(altered, fixture)
        self.assertEqual(receipt["status"], "UNKNOWN")
        self.assertEqual(receipt["adapter_v10_status"], "UNKNOWN")
        self.assertFalse(receipt["adapter_v10_exactly_verified"])
        self.assertIsNone(receipt["adapter_v10_hash"])


if __name__ == "__main__":
    unittest.main()
