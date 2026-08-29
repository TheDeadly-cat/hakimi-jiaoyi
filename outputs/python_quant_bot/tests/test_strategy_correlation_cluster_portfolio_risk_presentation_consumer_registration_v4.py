from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pathlib
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4 as subject
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskPresentationConsumerRegistrationV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = subject.expected_presentation_consumer_implementation_sha256_v4()
        self.document = self._build()

    def _build(self, manifest: object | None = None) -> dict:
        return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            copy.deepcopy(self.manifest if manifest is None else manifest)
        )

    def _verify(self, document: dict, manifest: object | None = None) -> dict:
        return subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4(
            copy.deepcopy(document),
            copy.deepcopy(self.manifest if manifest is None else manifest),
        )

    def test_versions_status_and_decision_are_locked(self) -> None:
        self.assertEqual(self.document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(self.document["decision"], subject.DECISION)

    def test_manifest_counts_and_roles_are_exact(self) -> None:
        source = self.document["source"]
        self.assertEqual(source["implementation_pin_count"], 12)
        self.assertEqual(source["predecessor_pin_count"], 1)
        self.assertEqual(source["production_pin_count"], 6)
        self.assertEqual(source["verification_pin_count"], 4)
        self.assertEqual(source["decision_record_pin_count"], 1)
        roles = [artifact["role"] for artifact in source["artifacts"]]
        self.assertEqual(roles.count("PREDECESSOR"), 1)
        self.assertEqual(roles.count("PRODUCTION"), 6)
        self.assertEqual(roles.count("VERIFICATION"), 4)
        self.assertEqual(roles.count("DECISION_RECORD"), 1)

    def test_actual_files_match_all_registered_hashes(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for artifact in self.document["source"]["artifacts"]:
            path = root / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                artifact["expected_sha256"],
            )

    def test_frontend_version_gap_is_closed_but_execution_receipt_remains_open(self) -> None:
        self.assertEqual(
            self.document["closed_local_blockers"],
            ["http_candidate_to_frontend_projection_v5_unversioned"],
        )
        self.assertNotIn(
            "http_candidate_to_frontend_projection_v5_unversioned",
            self.document["blockers"],
        )
        self.assertIn(
            "consumer_v5_execution_receipt_not_versioned",
            self.document["blockers"],
        )
        self.assertTrue(
            self.document["facts"][
                "http_candidate_to_frontend_projection_contract_versioned"
            ]
        )
        self.assertFalse(
            self.document["facts"]["consumer_v5_execution_receipt_versioned"]
        )

    def test_pinned_tests_do_not_self_certify_execution_or_review(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["verification_artifacts_pinned"])
        self.assertTrue(facts["static_cross_runtime_contract_versioned"])
        self.assertFalse(facts["static_cross_runtime_consumer_executed"])
        self.assertFalse(facts["consumer_v5_execution_evidence_independently_bound"])
        self.assertFalse(facts["render_descriptor_reviewed"])
        self.assertFalse(facts["dependency_load_order_reviewed"])

    def test_missing_extra_scalar_and_bool_alias_manifest_fail_closed(self) -> None:
        for key in tuple(self.manifest):
            malformed = copy.deepcopy(self.manifest)
            malformed.pop(key)
            document = self._build(malformed)
            self.assertFalse(document["source"]["implementation_manifest_contract_verified"])
            self.assertEqual(document["closed_local_blockers"], [])
        extra = copy.deepcopy(self.manifest)
        extra["frontend_ready"] = True
        self.assertFalse(self._build(extra)["source"]["implementation_manifest_contract_verified"])
        for alias in (True, False, 1, "PASS"):
            self.assertFalse(self._build(alias)["source"]["implementation_manifest_contract_verified"])

    def test_each_hash_drift_fails_closed(self) -> None:
        for key in tuple(self.manifest):
            drifted = copy.deepcopy(self.manifest)
            drifted[key] = "0" * 64 if drifted[key] != "0" * 64 else "1" * 64
            document = self._build(drifted)
            self.assertFalse(document["source"]["implementation_fingerprints_match"])
            self.assertFalse(document["facts"]["projection_v5_contract_pinned"])

    def test_role_hash_swap_fails_closed(self) -> None:
        swapped = copy.deepcopy(self.manifest)
        left = swapped["joint_evidence_card_v5_js"]
        right = swapped["joint_evidence_card_v5_css"]
        swapped["joint_evidence_card_v5_js"] = right
        swapped["joint_evidence_card_v5_css"] = left
        self.assertFalse(self._build(swapped)["source"]["implementation_fingerprints_match"])

    def test_expected_manifest_is_detached_and_build_is_deterministic(self) -> None:
        detached = subject.expected_presentation_consumer_implementation_sha256_v4()
        detached["presentation_registration_v3"] = "0" * 64
        self.assertNotEqual(
            detached,
            subject.expected_presentation_consumer_implementation_sha256_v4(),
        )
        manifest = copy.deepcopy(self.manifest)
        snapshot = copy.deepcopy(manifest)
        self.assertEqual(self._build(manifest), self._build(manifest))
        self.assertEqual(manifest, snapshot)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self) -> None:
        receipt = self._verify(self.document)
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["registration_exactly_verified"])
        tampered = copy.deepcopy(self.document)
        tampered["facts"]["ui_mounted"] = True
        tampered = seal_strict_canonical_document(tampered, "registration_hash")
        receipt = self._verify(tampered)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["registration_exactly_verified"])

    def test_invalid_manifest_receipt_does_not_claim_manifest_verification(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid.pop("joint_evidence_frontend_v5_adr")
        document = self._build(invalid)
        receipt = self._verify(document, invalid)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertTrue(receipt["registration_exactly_verified"])
        self.assertFalse(receipt["implementation_manifest_exactly_verified"])

    def test_all_authority_runtime_dom_browser_and_mount_claims_remain_denied(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value)
        facts = self.document["facts"]
        self.assertFalse(facts["runtime_assets_accessed"])
        self.assertFalse(facts["runtime_consumer_bound"])
        self.assertFalse(facts["dom_contract_reviewed"])
        self.assertFalse(facts["browser_visual_review_performed"])
        self.assertFalse(facts["server_route_registered"])
        self.assertFalse(facts["ui_mounted"])

    def test_activation_order_keeps_receipt_review_dom_browser_and_current_separate(self) -> None:
        order = self.document["activation_order"]
        self.assertLess(
            order.index("VERSION_CONSUMER_V5_EXECUTION_RECEIPT"),
            order.index("INDEPENDENTLY_REVIEW_RENDER_DESCRIPTOR_AND_LOAD_ORDER"),
        )
        self.assertLess(
            order.index("INDEPENDENTLY_REVIEW_RENDER_DESCRIPTOR_AND_LOAD_ORDER"),
            order.index("AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW"),
        )
        self.assertLess(
            order.index("AUTHORIZE_BROWSER_VISUAL_REVIEW"),
            order.index("SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT"),
        )
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")

    def test_dependency_order_and_consumer_contract_are_exact(self) -> None:
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["dependency_order"],
            [
                "HakimiStrictCanonicalJsonV1",
                "HakimiPortfolioRiskJointEvidenceCardV5",
                "HakimiPortfolioRiskJointEvidenceConsumerFixtureV5",
            ],
        )
        self.assertEqual(
            self.document["consumer"]["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(self.document["consumer"]["registration_state"], "CANDIDATE_ONLY")
        self.assertIsNone(self.document["consumer"]["dom_target"])
        self.assertIsNone(self.document["consumer"]["selector"])

    def test_api_accepts_only_static_manifest_and_output_embeds_no_manifest(self) -> None:
        build_signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
        )
        verify_signature = inspect.signature(
            subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v4
        )
        self.assertEqual(tuple(build_signature.parameters), ("current_implementation_sha256",))
        self.assertEqual(
            tuple(verify_signature.parameters),
            ("document", "current_implementation_sha256"),
        )
        self.assertFalse(self.document["source"]["supplied_manifest_embedded"])
        self.assertFalse(self.document["source"]["artifact_files_read"])
        self.assertFalse(self.document["source"]["artifacts_executed"])
        self.assertNotEqual(self.document["source"], self.manifest)

    def test_no_ready_profit_or_permission_claim(self) -> None:
        serialized = json.dumps(self.document, sort_keys=True)
        self.assertNotIn("READY", serialized)
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertEqual(
            self.document["contract_pins"]["permission_policy"],
            "ALWAYS_UNAUTHORIZED_V4",
        )


if __name__ == "__main__":
    unittest.main()
