from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pathlib
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3 as subject
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class PortfolioRiskPresentationConsumerRegistrationV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = subject.expected_presentation_consumer_implementation_sha256_v3()
        self.document = subject.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            copy.deepcopy(self.manifest)
        )

    def _build(self, manifest: object | None = None) -> dict:
        return subject.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            copy.deepcopy(self.manifest if manifest is None else manifest)
        )

    def test_versions_status_and_decision_are_locked(self) -> None:
        self.assertEqual(self.document["schema_version"], subject.SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(self.document["decision"], subject.DECISION)

    def test_manifest_has_predecessor_candidate_test_adr_and_canonical_pins(self) -> None:
        self.assertEqual(set(self.manifest), {
            "presentation_registration_v2",
            "presentation_http_candidate_v5",
            "presentation_http_candidate_v5_test",
            "presentation_http_candidate_v5_adr",
            "strict_canonical_json_hash_py",
        })
        source = self.document["source"]
        self.assertEqual(source["implementation_pin_count"], 5)
        self.assertEqual(source["predecessor_pin_count"], 1)
        self.assertEqual(source["production_pin_count"], 2)
        self.assertEqual(source["verification_pin_count"], 1)
        self.assertEqual(source["decision_record_pin_count"], 1)

    def test_artifact_roles_paths_and_hashes_are_exact(self) -> None:
        artifacts = self.document["source"]["artifacts"]
        self.assertEqual(len(artifacts), 5)
        self.assertEqual({item["artifact_id"] for item in artifacts}, set(self.manifest))
        for artifact in artifacts:
            self.assertEqual(artifact["expected_sha256"], self.manifest[artifact["artifact_id"]])
            self.assertIn(artifact["role"], {"PREDECESSOR", "PRODUCTION", "VERIFICATION", "DECISION_RECORD"})

    def test_http_contract_blocker_is_closed_but_frontend_binding_remains_open(self) -> None:
        self.assertEqual(
            self.document["closed_local_blockers"],
            ["presentation_http_contract_not_versioned"],
        )
        self.assertNotIn("presentation_http_contract_not_versioned", self.document["blockers"])
        self.assertIn(
            "http_candidate_to_frontend_projection_v5_unversioned",
            self.document["blockers"],
        )
        self.assertTrue(self.document["facts"]["presentation_http_contract_versioned"])
        self.assertFalse(
            self.document["facts"]["http_candidate_to_frontend_projection_bound"]
        )

    def test_candidate_pin_does_not_claim_route_runtime_dom_or_browser(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["presentation_http_candidate_v5_pinned"])
        self.assertFalse(facts["runtime_assets_accessed"])
        self.assertFalse(facts["runtime_consumer_bound"])
        self.assertFalse(facts["server_route_registered"])
        self.assertFalse(facts["ui_mounted"])
        self.assertFalse(facts["dom_contract_reviewed"])
        self.assertFalse(facts["browser_visual_review_performed"])

    def test_missing_extra_scalar_and_bool_alias_manifest_fail_closed(self) -> None:
        for key in tuple(self.manifest):
            malformed = copy.deepcopy(self.manifest)
            malformed.pop(key)
            document = self._build(malformed)
            self.assertFalse(document["source"]["implementation_manifest_contract_verified"])
            self.assertEqual(document["closed_local_blockers"], [])
        extra = copy.deepcopy(self.manifest)
        extra["candidate_v5_ready"] = True
        self.assertFalse(self._build(extra)["source"]["implementation_manifest_contract_verified"])
        for alias in (True, False, 1, "PASS"):
            self.assertFalse(self._build(alias)["source"]["implementation_manifest_contract_verified"])

    def test_each_hash_drift_fails_closed(self) -> None:
        for key in tuple(self.manifest):
            drifted = copy.deepcopy(self.manifest)
            drifted[key] = "0" * 64 if drifted[key] != "0" * 64 else "1" * 64
            document = self._build(drifted)
            self.assertFalse(document["source"]["implementation_fingerprints_match"])
            self.assertFalse(document["facts"]["presentation_http_contract_versioned"])

    def test_expected_manifest_is_detached_and_build_is_deterministic(self) -> None:
        detached = subject.expected_presentation_consumer_implementation_sha256_v3()
        detached["presentation_registration_v2"] = "0" * 64
        self.assertNotEqual(
            detached,
            subject.expected_presentation_consumer_implementation_sha256_v3(),
        )
        manifest = copy.deepcopy(self.manifest)
        snapshot = copy.deepcopy(manifest)
        self.assertEqual(self._build(manifest), self._build(manifest))
        self.assertEqual(manifest, snapshot)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self) -> None:
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            copy.deepcopy(self.document), copy.deepcopy(self.manifest)
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["registration_exactly_verified"])
        self.assertTrue(receipt["implementation_manifest_exactly_verified"])

        tampered = copy.deepcopy(self.document)
        tampered["facts"]["runtime_consumer_bound"] = True
        tampered = seal_strict_canonical_document(tampered, "registration_hash")
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            tampered, copy.deepcopy(self.manifest)
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["registration_exactly_verified"])

    def test_invalid_manifest_receipt_does_not_claim_manifest_verification(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid.pop("presentation_http_candidate_v5_adr")
        document = self._build(invalid)
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            document, invalid
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertTrue(receipt["registration_exactly_verified"])
        self.assertFalse(receipt["implementation_manifest_exactly_verified"])

    def test_all_authority_remains_denied(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertFalse(value)
        receipt = subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3(
            copy.deepcopy(self.document), copy.deepcopy(self.manifest)
        )
        for key, value in receipt.items():
            if key.endswith("_allowed") or key in {"paper_authorized", "live_order_allowed"}:
                self.assertFalse(value)

    def test_activation_order_keeps_binding_before_reviews_and_current_last(self) -> None:
        order = self.document["activation_order"]
        self.assertLess(
            order.index("VERSION_HTTP_CANDIDATE_V5_TO_FRONTEND_PROJECTION_CONSUMER"),
            order.index("AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW"),
        )
        self.assertLess(
            order.index("AUTHORIZE_BROWSER_VISUAL_REVIEW"),
            order.index("SEPARATELY_AUTHORIZE_PRESENTATION_CONSUMER_REGISTRATION"),
        )
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")

    def test_api_accepts_only_static_manifest(self) -> None:
        build_signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3
        )
        verify_signature = inspect.signature(
            subject.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v3
        )
        self.assertEqual(tuple(build_signature.parameters), ("current_implementation_sha256",))
        self.assertEqual(
            tuple(verify_signature.parameters),
            ("document", "current_implementation_sha256"),
        )
        rendered = (str(build_signature) + str(verify_signature)).lower()
        for token in ("route", "runtime", "browser", "dom", "paper", "live", "order"):
            self.assertNotIn(token, rendered)

    def test_output_embeds_no_manifest_document_markup_or_runtime_handle(self) -> None:
        self.assertFalse(self.document["source"]["supplied_manifest_embedded"])
        self.assertFalse(self.document["source"]["artifact_files_read"])
        serialized = json.dumps(self.document, sort_keys=True)
        for token in ("<script", "<style", "querySelector", "document.", "window."):
            self.assertNotIn(token, serialized)
        self.assertNotEqual(self.document.get("source"), self.manifest)

    def test_actual_files_match_all_registered_hashes(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for artifact in self.document["source"]["artifacts"]:
            path = root / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                artifact["expected_sha256"],
            )

    def test_no_ready_profit_or_permission_claim(self) -> None:
        serialized = json.dumps(self.document, sort_keys=True)
        self.assertNotIn("READY", serialized)
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertEqual(
            self.document["contract_pins"]["permission_policy"],
            "ALWAYS_UNAUTHORIZED_V3",
        )


if __name__ == "__main__":
    unittest.main()
