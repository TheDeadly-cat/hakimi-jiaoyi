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
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11
    as presentation_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (  # noqa: E402
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from tests import (  # noqa: E402
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_basis_presentation_v10
    as presentation_v10_tests,
)
from tests import (  # noqa: E402
    test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_adapter_v10
    as adapter_v10_tests,
)


ALTERNATE_HASH = "8" * 64


class StratifiedMultiWindowEdgeCommonObservationMembershipPresentationV11Tests(
    unittest.TestCase
):
    def _fixture(self, *, membership_block: bool = False) -> dict:
        presentation_case = presentation_v10_tests.StratifiedMultiWindowEdgeCommonObservationBasisPresentationV10Tests(
            "test_two_exact_clear_components_remain_outer_blocked"
        )
        presentation_case.setUp()
        presentation_document = presentation_case._build()
        adapter_case = adapter_v10_tests.StratifiedMultiWindowEdgeCommonObservationMembershipAdapterV10Tests(
            "test_two_exact_clear_components_pass_locally"
        )
        adapter_fixture = adapter_case._fixture(
            membership_block=membership_block
        )
        adapter_document = adapter_case._build(adapter_fixture)
        return {
            "presentation_case": presentation_case,
            "adapter_case": adapter_case,
            "presentation_document": presentation_document,
            "adapter_document": adapter_document,
            "presentation_context": {
                "adapter_v9_document": presentation_case.adapter_v9_clear,
                "adapter_v9_verification_context": (
                    presentation_case.adapter_context_clear
                ),
                "presentation_v9_document": presentation_case.presentation_v9,
                "presentation_v9_verification_context": (
                    presentation_case.presentation_context
                ),
            },
            "adapter_context": {
                "adapter_v9_document": adapter_fixture["adapter_document"],
                "adapter_v9_verification_context": adapter_fixture[
                    "adapter_context"
                ],
                "membership_gate_v2_document": adapter_fixture[
                    "membership_document"
                ],
                "membership_gate_v2_verification_context": adapter_fixture[
                    "membership_context"
                ],
            },
        }

    @staticmethod
    def _presentation_receipt(document: dict, *, valid: bool = True) -> dict:
        return {
            "blockers": [] if valid else ["INVALID"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "presentation_consumer_activation_allowed": False,
            "presentation_v10_exactly_verified": valid,
            "presentation_v10_hash": (
                document["presentation_v10_hash"] if valid else None
            ),
            "runtime_gate_activation_allowed": False,
            "schema_version": (
                "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
                "edge-uncertainty-common-observation-basis-presentation-v10-"
                "verification-v1"
            ),
            "status": "PASS" if valid else "BLOCK",
            "writer_allowed": False,
        }

    @staticmethod
    def _adapter_receipt(document: dict, *, valid: bool = True) -> dict:
        return {
            "adapter_v10_exactly_verified": valid,
            "adapter_v10_hash": document["adapter_v10_hash"] if valid else None,
            "adapter_v10_status": document["status"] if valid else "UNKNOWN",
            "blockers": deepcopy(document["blockers"]) if valid else ["INVALID"],
            "current_admission_allowed": False,
            "live_order_allowed": False,
            "paper_authorized": False,
            "runtime_gate_activation_allowed": False,
            "schema_version": (
                "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-"
                "edge-uncertainty-common-observation-membership-adapter-v10-"
                "verification-v1"
            ),
            "source_known": valid,
            "status": "PASS" if valid else "UNKNOWN",
            "writer_allowed": False,
        }

    def _build(
        self,
        fixture: dict,
        *,
        presentation_receipt: dict | None = None,
        adapter_receipt: dict | None = None,
    ) -> dict:
        presentation_receipt = presentation_receipt or self._presentation_receipt(
            fixture["presentation_document"]
        )
        adapter_receipt = adapter_receipt or self._adapter_receipt(
            fixture["adapter_document"]
        )
        with patch.object(
            presentation_v11,
            "_VERIFY_PRESENTATION_V10",
            return_value=presentation_receipt,
        ), patch.object(
            presentation_v11,
            "_VERIFY_ADAPTER_V10",
            return_value=adapter_receipt,
        ):
            return presentation_v11.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11(
                fixture["presentation_document"],
                fixture["adapter_document"],
                presentation_v10_verification_context=fixture[
                    "presentation_context"
                ],
                adapter_v10_verification_context=fixture["adapter_context"],
            )

    def _verify(self, document: dict, fixture: dict) -> dict:
        with patch.object(
            presentation_v11,
            "_VERIFY_PRESENTATION_V10",
            return_value=self._presentation_receipt(
                fixture["presentation_document"]
            ),
        ), patch.object(
            presentation_v11,
            "_VERIFY_ADAPTER_V10",
            return_value=self._adapter_receipt(fixture["adapter_document"]),
        ):
            return presentation_v11.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_presentation_v11(
                document,
                fixture["presentation_document"],
                fixture["adapter_document"],
                presentation_v10_verification_context=fixture[
                    "presentation_context"
                ],
                adapter_v10_verification_context=fixture["adapter_context"],
            )

    @staticmethod
    def _reseal(document: dict, hash_key: str) -> dict:
        unsigned = deepcopy(document)
        unsigned.pop(hash_key, None)
        return seal_strict_canonical_document(unsigned, hash_key)

    def test_two_exact_clear_components_remain_outer_blocked(self) -> None:
        fixture = self._fixture()
        document = self._build(fixture)
        receipt = self._verify(document, fixture)
        self.assertEqual(document["status"], "BLOCK")
        self.assertEqual(document["local_decision"]["joint_status"], "PASS")
        self.assertEqual(document["gaps"]["local_blocker_count"], 0)
        self.assertEqual(document["membership_summary"]["registered_pair_count"], 2)
        self.assertTrue(document["facts"]["membership_summary_projected"])
        self.assertTrue(receipt["presentation_v11_exactly_verified"])
        self.assertEqual(receipt["status"], "PASS")

    def test_adapter_v10_membership_block_overrides_presentation_v10_local_pass(self) -> None:
        fixture = self._fixture(membership_block=True)
        self.assertEqual(
            fixture["presentation_document"]["local_decision"]["joint_status"],
            "PASS",
        )
        self.assertEqual(fixture["adapter_document"]["status"], "BLOCK")
        document = self._build(fixture)
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(
            document["local_decision"][
                "common_observation_membership_gate_v2_status"
            ],
            "BLOCK",
        )
        self.assertEqual(
            document["membership_summary"]["membership_hash_match_pair_count"], 1
        )

    def test_presentation_v10_local_block_is_preserved(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["presentation_document"])
        altered["local_decision"]["joint_decision"] = "BLOCK_SYNTHETIC_V10_LOCAL"
        altered["local_decision"]["joint_status"] = "BLOCK"
        altered["gaps"]["local_blocker_count"] = 1
        fixture["presentation_document"] = self._reseal(
            altered, "presentation_v10_hash"
        )
        document = self._build(fixture)
        self.assertEqual(document["local_decision"]["joint_status"], "BLOCK")
        self.assertEqual(document["gaps"]["presentation_v10_local_blocker_count"], 1)

    def test_shared_adapter_v9_context_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["adapter_context"]["adapter_v9_document"])
        altered["authority"]["paper_authorized"] = True
        fixture["adapter_context"]["adapter_v9_document"] = self._reseal(
            altered, "adapter_v9_hash"
        )
        document = self._build(fixture)
        self.assertFalse(document["facts"]["cross_bindings_verified"])
        self.assertIsNone(document["membership_summary"])

    def test_adapter_v9_hash_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["adapter_document"])
        altered["source"]["adapter_v9_hash"] = ALTERNATE_HASH
        fixture["adapter_document"] = self._reseal(altered, "adapter_v10_hash")
        document = self._build(fixture)
        self.assertFalse(document["facts"]["cross_bindings_verified"])
        self.assertIsNone(document["risk_summary"])

    def test_membership_gate_hash_splice_is_unknown(self) -> None:
        for source_key in (
            "membership_gate_v2_hash",
            "membership_preregistration_hash",
            "membership_evidence_hash",
            "observation_identifier_scheme_hash",
        ):
            with self.subTest(source_key=source_key):
                fixture = self._fixture()
                altered = deepcopy(fixture["adapter_document"])
                altered["source"][source_key] = ALTERNATE_HASH
                fixture["adapter_document"] = self._reseal(
                    altered, "adapter_v10_hash"
                )
                document = self._build(fixture)
                self.assertFalse(document["facts"]["cross_bindings_verified"])
                self.assertIsNone(document["membership_summary"])

    def test_membership_count_splice_is_unknown(self) -> None:
        fixture = self._fixture()
        altered = deepcopy(fixture["adapter_document"])
        altered["summary"]["edge_pair_count"] = 3
        fixture["adapter_document"] = self._reseal(altered, "adapter_v10_hash")
        document = self._build(fixture)
        self.assertFalse(document["facts"]["cross_bindings_verified"])
        self.assertIsNone(document["common_observation_summary"])

    def test_malformed_presentation_receipt_hides_every_summary(self) -> None:
        fixture = self._fixture()
        document = self._build(
            fixture,
            presentation_receipt=self._presentation_receipt(
                fixture["presentation_document"], valid=False
            ),
        )
        self.assertIsNone(document["risk_summary"])
        self.assertIsNone(document["membership_summary"])

    def test_malformed_adapter_receipt_hides_every_summary(self) -> None:
        fixture = self._fixture()
        document = self._build(
            fixture,
            adapter_receipt=self._adapter_receipt(
                fixture["adapter_document"], valid=False
            ),
        )
        self.assertIsNone(document["edge_uncertainty_summary"])
        self.assertIsNone(document["membership_summary"])

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
        self.assertFalse(document["authority"]["http_candidate_creation_allowed"])
        self.assertEqual(
            [stage["axis"] for stage in document["stages"]], list(presentation_v11.AXIS_ORDER)
        )

    def test_inputs_are_not_mutated(self) -> None:
        fixture = self._fixture()
        before = {
            key: deepcopy(fixture[key])
            for key in (
                "presentation_document",
                "adapter_document",
                "presentation_context",
                "adapter_context",
            )
        }
        document = self._build(fixture)
        self.assertTrue(document["facts"]["cross_bindings_verified"])
        for key, value in before.items():
            self.assertTrue(strict_json_contract_equal(fixture[key], value))

    def test_exact_verifier_rejects_permission_promotion(self) -> None:
        fixture = self._fixture()
        document = self._build(fixture)
        altered = deepcopy(document)
        altered["authority"]["paper_authorized"] = True
        altered = self._reseal(altered, "presentation_v11_hash")
        receipt = self._verify(altered, fixture)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["presentation_v11_exactly_verified"])
        self.assertIsNone(receipt["presentation_v11_hash"])


if __name__ == "__main__":
    unittest.main()
