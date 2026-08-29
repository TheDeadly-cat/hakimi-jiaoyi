from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5
    as registration_v5,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6
    as registration_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskPresentationConsumerRegistrationV6Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.manifest = (
            registration_v6.expected_presentation_consumer_implementation_sha256_v6()
        )

    def _build(self, manifest: dict | None = None) -> dict:
        return registration_v6.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
            self.manifest if manifest is None else manifest
        )

    def test_expected_manifest_has_exact_eleven_artifact_pins(self) -> None:
        self.assertEqual(len(self.manifest), 11)
        self.assertEqual(
            self.manifest["presentation_registration_v5"],
            "5205b4dfb3a33e5903c9f8c0015383352f2cd1fd84eb38563f2f6364f08d08d3",
        )
        self.assertEqual(
            self.manifest["execution_witness_signature_candidate_v1_js"],
            "8d085ae6528d16f50888b167b7ed3c913a5eed12977f80290c02bc07c55e7156",
        )
        self.assertEqual(
            self.manifest["descriptor_load_order_review_v1_js"],
            "cd6b70d2b7c131678e3c5f9de4095f9d8508836e336a8936efc61d21aa2424d5",
        )
        for value in self.manifest.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_exact_manifest_builds_blocked_candidate_with_three_local_closures(
        self,
    ) -> None:
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(
            document["source"]["implementation_manifest_contract_verified"]
        )
        self.assertTrue(
            document["contract_pins"][
                "witness_and_review_version_chain_exact"
            ]
        )
        self.assertEqual(len(document["closed_local_blockers"]), 3)
        self.assertFalse(document["facts"]["registration_activated"])

    def test_predecessor_registration_v5_hash_is_exactly_rebuilt(self) -> None:
        predecessor = registration_v5.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v5(
            registration_v5.expected_presentation_consumer_implementation_sha256_v5()
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

    def test_witness_and_review_schemas_and_implementations_are_explicit(
        self,
    ) -> None:
        consumer = self._build()["consumer"]
        self.assertEqual(
            consumer["witness_policy_schema_version"],
            registration_v6.WITNESS_POLICY_SCHEMA_VERSION,
        )
        self.assertEqual(
            consumer["witness_verification_schema_version"],
            registration_v6.WITNESS_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            consumer["witness_implementation_sha256"],
            registration_v6.WITNESS_SIGNATURE_JAVASCRIPT_SHA256,
        )
        self.assertEqual(
            consumer["descriptor_review_schema_version"],
            registration_v6.DESCRIPTOR_REVIEW_SCHEMA_VERSION,
        )
        self.assertEqual(
            consumer["descriptor_review_implementation_sha256"],
            registration_v6.DESCRIPTOR_REVIEW_JAVASCRIPT_SHA256,
        )

    def test_missing_extra_and_substituted_manifest_values_fail_closed(
        self,
    ) -> None:
        missing = copy.deepcopy(self.manifest)
        missing.pop("descriptor_load_order_review_v1_adr")
        extra = copy.deepcopy(self.manifest)
        extra["unexpected"] = "f" * 64
        wrong = copy.deepcopy(self.manifest)
        wrong["execution_witness_signature_candidate_v1_js"] = "f" * 64
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
        verification = registration_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
            document,
            self.manifest,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["registration_status"], "BLOCKED")
        self.assertTrue(verification["registration_exactly_rebuilt"])
        self.assertTrue(verification["manifest_exact"])

    def test_public_verifier_rejects_document_for_wrong_manifest(self) -> None:
        document = self._build()
        wrong = copy.deepcopy(self.manifest)
        wrong["descriptor_load_order_review_v1_js"] = "f" * 64
        verification = registration_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
            document,
            wrong,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["manifest_exact"])

    def test_resealed_authority_promotion_fails_exact_verification(self) -> None:
        document = self._build()
        altered = copy.deepcopy(document)
        altered["authority"]["presentation_mount_allowed"] = True
        altered = seal_strict_canonical_document(
            altered,
            "registration_hash",
        )
        verification = registration_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v6(
            altered,
            self.manifest,
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["registration_exactly_rebuilt"])

    def test_key_possession_is_versioned_without_external_identity(self) -> None:
        facts = self._build()["facts"]
        self.assertTrue(facts["witness_signature_contract_pinned"])
        self.assertTrue(
            facts["cryptographic_key_possession_verification_versioned"]
        )
        self.assertFalse(
            facts["external_witness_policy_registry_bound"]
        )
        self.assertFalse(facts["witness_organization_identity_verified"])
        self.assertFalse(facts["independent_execution_process_witnessed"])
        self.assertFalse(facts["shared_anti_replay_registry_checked"])

    def test_static_review_is_versioned_without_browser_or_mount(self) -> None:
        document = self._build()
        self.assertTrue(
            document["facts"]["descriptor_static_review_pinned"]
        )
        self.assertTrue(
            document["facts"]["dependency_load_order_static_review_pinned"]
        )
        self.assertFalse(
            document["facts"]["browser_visual_review_performed"]
        )
        self.assertFalse(document["facts"]["server_route_registered"])
        self.assertFalse(document["facts"]["ui_mounted"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value)

    def test_activation_order_keeps_external_and_browser_steps_later(
        self,
    ) -> None:
        order = self._build()["activation_order"]
        self.assertEqual(
            order[:4],
            [
                "REGISTRATION_V5_RECEIPT_EVIDENCE_CHAIN",
                "WITNESS_SIGNATURE_KEY_POSSESSION_CANDIDATE",
                "DESCRIPTOR_AND_LOAD_ORDER_STATIC_REVIEW",
                "REGISTRATION_V6_STATIC_CANDIDATE",
            ],
        )
        self.assertEqual(
            order[-1],
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        )

    def test_registration_is_deterministic_neutral_and_non_authorizing(
        self,
    ) -> None:
        before = copy.deepcopy(self.manifest)
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(self.manifest, before)
        self.assertFalse(first["source"]["supplied_manifest_embedded"])
        self.assertFalse(first["facts"]["profitability_proven"])
        self.assertFalse(first["authority"]["paper_authorized"])
        self.assertFalse(first["authority"]["live_order_allowed"])
        promotion = "\\b" + "R" + "EADY" + "\\b"
        self.assertNotRegex(json.dumps(first), promotion)


if __name__ == "__main__":
    unittest.main()
