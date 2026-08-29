from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
    as registration_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5
    as registration_v5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskPresentationConsumerRegistrationV5Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.manifest = (
            registration_v5.expected_presentation_consumer_implementation_sha256_v5()
        )

    def _build(self, manifest: dict | None = None) -> dict:
        return registration_v5.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            self.manifest if manifest is None else manifest
        )

    def test_expected_manifest_has_exact_nine_artifact_pins(self) -> None:
        self.assertEqual(len(self.manifest), 9)
        self.assertEqual(
            self.manifest["presentation_registration_v4"],
            "b7b0b8faf64d34796b6ae97e6594ea08a0fcd930272fa4841e4a7bd0ebecd897",
        )
        self.assertEqual(
            self.manifest["consumer_execution_receipt_v3_js"],
            "9a90650656f63cd8026fcee224ed4e3d690ced6a7d8bd2970772c653e55c2acb",
        )
        self.assertEqual(
            self.manifest["consumer_execution_evidence_v3_py"],
            "0c42538f37bfc165d15ca34fe4136f87df9fdffb411ed1a64d8f2be26c2fdb85",
        )
        for value in self.manifest.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_exact_manifest_builds_blocked_candidate_with_closed_local_chain(
        self,
    ) -> None:
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(
            document["source"]["implementation_manifest_contract_verified"]
        )
        self.assertTrue(
            document["contract_pins"][
                "receipt_to_evidence_version_chain_exact"
            ]
        )
        self.assertEqual(len(document["closed_local_blockers"]), 3)
        self.assertTrue(
            document["facts"]["receipt_v3_contract_pinned"]
        )
        self.assertTrue(
            document["facts"]["evidence_v3_contract_pinned"]
        )
        self.assertFalse(document["facts"]["registration_activated"])

    def test_predecessor_registration_hash_is_exactly_rebuilt(self) -> None:
        predecessor_manifest = (
            registration_v4.expected_presentation_consumer_implementation_sha256_v4()
        )
        predecessor = registration_v4.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            predecessor_manifest
        )
        document = self._build()
        self.assertEqual(
            document["consumer"]["predecessor_registration_hash"],
            predecessor["registration_hash"],
        )
        self.assertEqual(
            document["contract_pins"]["predecessor_registration_hash"],
            predecessor["registration_hash"],
        )
        self.assertTrue(
            document["facts"]["predecessor_registration_preserved"]
        )

    def test_receipt_and_evidence_versions_are_explicitly_pinned(self) -> None:
        document = self._build()
        self.assertEqual(
            document["consumer"]["receipt_schema_version"],
            registration_v5.RECEIPT_V3_SCHEMA_VERSION,
        )
        self.assertEqual(
            document["consumer"]["evidence_schema_version"],
            registration_v5.EVIDENCE_V3_SCHEMA_VERSION,
        )
        self.assertEqual(
            document["consumer"]["receipt_implementation_sha256"],
            registration_v5.RECEIPT_V3_JAVASCRIPT_SHA256,
        )
        self.assertEqual(
            document["consumer"]["evidence_implementation_sha256"],
            registration_v5.EVIDENCE_V3_PYTHON_SHA256,
        )

    def test_missing_extra_and_wrong_manifest_values_fail_closed(self) -> None:
        missing = copy.deepcopy(self.manifest)
        missing.pop("consumer_execution_evidence_v3_adr")
        extra = copy.deepcopy(self.manifest)
        extra["unexpected"] = "f" * 64
        wrong = copy.deepcopy(self.manifest)
        wrong["consumer_execution_evidence_v3_py"] = "f" * 64
        for manifest in (missing, extra, wrong):
            document = self._build(manifest)
            self.assertEqual(document["status"], "BLOCKED")
            self.assertFalse(
                document["source"][
                    "implementation_manifest_contract_verified"
                ]
            )
            self.assertIn(
                "IMPLEMENTATION_MANIFEST_MISMATCH",
                document["blockers"],
            )
            self.assertEqual(document["closed_local_blockers"], [])

    def test_public_verifier_accepts_exact_blocked_registration(self) -> None:
        document = self._build()
        verification = registration_v5.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            document,
            self.manifest,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["registration_status"], "BLOCKED")
        self.assertTrue(verification["registration_exactly_rebuilt"])
        self.assertTrue(verification["manifest_exact"])

    def test_public_verifier_rejects_exact_document_for_wrong_manifest(
        self,
    ) -> None:
        document = self._build()
        wrong = copy.deepcopy(self.manifest)
        wrong["consumer_execution_receipt_v3_js"] = "f" * 64
        verification = registration_v5.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            document,
            wrong,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["manifest_exact"])

    def test_resealed_authority_promotion_fails_exact_verification(self) -> None:
        document = self._build()
        tampered = copy.deepcopy(document)
        tampered["authority"]["presentation_mount_allowed"] = True
        tampered = seal_strict_canonical_document(
            tampered,
            "registration_hash",
        )
        verification = registration_v5.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            tampered,
            self.manifest,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["registration_exactly_rebuilt"])

    def test_all_external_authority_and_execution_identity_remain_locked(
        self,
    ) -> None:
        document = self._build()
        self.assertFalse(
            document["facts"]["independent_node_process_witnessed"]
        )
        self.assertFalse(
            document["facts"]["node_process_identity_authenticated"]
        )
        self.assertFalse(document["facts"]["receipt_signature_verified"])
        self.assertFalse(document["facts"]["server_route_registered"])
        self.assertFalse(document["facts"]["ui_mounted"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_activation_order_keeps_identity_review_and_mount_later(self) -> None:
        order = self._build()["activation_order"]
        self.assertEqual(
            order[:4],
            [
                "REGISTRATION_V4_STATIC_FRONTEND_CHAIN",
                "RECEIPT_V3_LOCAL_NODE_EXECUTION_OBSERVATION",
                "EVIDENCE_V3_PYTHON_CROSS_DOCUMENT_BINDING",
                "REGISTRATION_V5_STATIC_CANDIDATE",
            ],
        )
        self.assertEqual(
            order[-1],
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        )

    def test_registration_is_deterministic_and_does_not_embed_input_manifest(
        self,
    ) -> None:
        before = copy.deepcopy(self.manifest)
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(self.manifest, before)
        self.assertFalse(first["source"]["supplied_manifest_embedded"])
        self.assertNotIn("current_implementation_sha256", first)

    def test_registration_contains_no_promotion_or_profitability_claim(
        self,
    ) -> None:
        document = self._build()
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(document), promotion)
        self.assertFalse(document["facts"]["profitability_proven"])
        self.assertFalse(document["authority"]["paper_authorized"])
        self.assertFalse(document["authority"]["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
