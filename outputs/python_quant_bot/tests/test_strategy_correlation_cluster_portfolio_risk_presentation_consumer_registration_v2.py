from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2 as module
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class PortfolioRiskPresentationConsumerRegistrationV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = (
            module.expected_presentation_consumer_implementation_sha256_v2()
        )
        self.document = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            self.manifest
        )

    def test_versions_status_and_decision_are_locked(self):
        self.assertEqual(self.document["schema_version"], module.SCHEMA_VERSION)
        self.assertEqual(
            self.document["static_fingerprint"], module.STATIC_FINGERPRINT
        )
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(self.document["decision"], module.DECISION)

    def test_manifest_has_one_predecessor_five_production_and_four_verification_pins(self):
        source = self.document["source"]
        self.assertEqual(len(self.manifest), 10)
        self.assertEqual(source["implementation_pin_count"], 10)
        self.assertEqual(source["predecessor_pin_count"], 1)
        self.assertEqual(source["production_pin_count"], 5)
        self.assertEqual(source["verification_pin_count"], 4)
        roles = [artifact["role"] for artifact in source["artifacts"]]
        self.assertEqual(roles.count("PREDECESSOR"), 1)
        self.assertEqual(roles.count("PRODUCTION"), 5)
        self.assertEqual(roles.count("VERIFICATION"), 4)

    def test_actual_files_match_all_registered_hashes(self):
        for artifact in self.document["source"]["artifacts"]:
            actual = hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["expected_sha256"])

    def test_each_hash_drift_fails_closed(self):
        for artifact_id in sorted(self.manifest):
            with self.subTest(artifact_id=artifact_id):
                manifest = dict(self.manifest)
                manifest[artifact_id] = "0" * 64
                document = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
                    manifest
                )
                self.assertEqual(document["status"], "BLOCKED")
                self.assertEqual(
                    document["decision"], "REGISTRATION_INPUT_INVALID_FAIL_CLOSED"
                )
                self.assertIn("implementation_manifest_mismatch", document["blockers"])
                self.assertFalse(document["facts"]["registration_candidate_built"])

    def test_missing_extra_scalar_and_bool_alias_manifest_fail_closed(self):
        missing = dict(self.manifest)
        missing.pop("portfolio_risk_projection_v4")
        extra = {**self.manifest, "unexpected": "0" * 64}
        scalar = "not-a-manifest"
        alias = dict(self.manifest)
        alias["portfolio_risk_projection_v4"] = True
        for manifest in (missing, extra, scalar, alias):
            document = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
                manifest
            )
            self.assertFalse(
                document["source"]["implementation_manifest_contract_verified"]
            )

    def test_predecessor_registration_v1_is_preserved_and_pinned(self):
        pins = self.document["contract_pins"]
        self.assertTrue(self.document["facts"]["predecessor_registration_preserved"])
        self.assertTrue(
            pins["predecessor_registration_schema_version"].endswith(
                "registration-candidate-v1"
            )
        )
        predecessor = next(
            item
            for item in self.document["source"]["artifacts"]
            if item["artifact_id"] == "presentation_registration_v1"
        )
        self.assertEqual(
            pins["predecessor_registration_implementation_sha256"],
            predecessor["expected_sha256"],
        )

    def test_projection_card_consumer_and_seal_contracts_are_exact(self):
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["projection_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-projection-v4",
        )
        self.assertEqual(
            pins["card_schema_version"],
            "portfolio-risk-weighted-diversification-card-v4",
        )
        self.assertEqual(
            pins["consumer_fixture_schema_version"],
            "portfolio-risk-weighted-diversification-presentation-consumer-fixture-v4",
        )
        self.assertEqual(
            pins["strict_canonical_global_name"], "HakimiStrictCanonicalJsonV1"
        )
        self.assertIn("PROJECTION_V4_SCHEMA_AWARE", pins["strict_canonical_usage_policy"])
        self.assertEqual(pins["stage_order"], list(module.STAGE_ORDER))
        self.assertEqual(pins["permission_policy"], "ALWAYS_UNAUTHORIZED_V2")

    def test_dependency_order_is_explicit_and_consumer_last(self):
        order = self.document["contract_pins"]["dependency_order"]
        self.assertEqual(order[0], "HakimiStrictCanonicalJsonV1")
        self.assertEqual(
            order[1], "HakimiPortfolioRiskWeightedDiversificationCardV4"
        )
        self.assertEqual(
            order[2], "HakimiPortfolioRiskWeightedDiversificationConsumerFixtureV4"
        )

    def test_candidate_is_not_registration_or_mount_activation(self):
        facts = self.document["facts"]
        self.assertTrue(facts["registration_candidate_built"])
        self.assertFalse(facts["registration_activated"])
        self.assertFalse(facts["ui_mounted"])
        self.assertEqual(
            self.document["consumer"]["registration_state"], "CANDIDATE_ONLY"
        )
        self.assertIsNone(self.document["consumer"]["dom_target"])
        self.assertIsNone(self.document["consumer"]["selector"])

    def test_manifest_match_is_not_external_attestation_or_file_read(self):
        self.assertTrue(
            self.document["source"]["implementation_manifest_contract_verified"]
        )
        self.assertFalse(self.document["source"]["artifact_files_read"])
        self.assertFalse(self.document["source"]["supplied_manifest_embedded"])
        self.assertFalse(
            self.document["facts"]["implementation_manifest_externally_attested"]
        )
        self.assertIn(
            "implementation_manifest_external_attestation_not_bound",
            self.document["blockers"],
        )

    def test_no_evidence_execution_review_http_or_runtime_claim(self):
        for key in (
            "projection_evidence_bound",
            "consumer_fixture_executed",
            "fixture_execution_receipt_versioned",
            "fixture_execution_evidence_bound",
            "render_descriptor_reviewed",
            "dependency_load_order_reviewed",
            "dom_contract_reviewed",
            "browser_visual_review_performed",
            "presentation_http_contract_versioned",
            "runtime_assets_accessed",
            "runtime_consumer_bound",
            "server_route_registered",
            "ui_mounted",
        ):
            self.assertIs(self.document["facts"][key], False)

    def test_all_authority_remains_denied(self):
        for key, value in self.document["authority"].items():
            self.assertIs(value, key == "descriptive_only")

    def test_activation_order_keeps_execution_before_reviews_and_current_last(self):
        order = self.document["activation_order"]
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")
        self.assertLess(
            order.index("VERSION_AND_EXECUTE_FIXTURE_V4_SYNTHETIC_MATRIX_RECEIPT"),
            order.index("AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW"),
        )
        self.assertLess(
            order.index("AUTHORIZE_BROWSER_VISUAL_REVIEW"),
            order.index("SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT"),
        )

    def test_api_accepts_only_static_manifest(self):
        parameters = list(
            inspect.signature(
                module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2
            ).parameters
        )
        self.assertEqual(parameters, ["current_implementation_sha256"])

    def test_output_embeds_no_projection_descriptor_markup_or_runtime_handle(self):
        serialized = json.dumps(self.document, sort_keys=True)
        for forbidden in (
            '"projection_document"',
            '"fixture_descriptor"',
            '"markup"',
            '"dom_instance"',
            '"browser_result"',
            '"runtime_handle"',
            '"supplied_manifest"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_registration_hash_is_canonical(self):
        payload = copy.deepcopy(self.document)
        supplied = payload.pop("registration_hash")
        self.assertEqual(supplied, strict_canonical_hash(payload))

    def test_build_is_deterministic_and_does_not_mutate_manifest(self):
        manifest = copy.deepcopy(self.manifest)
        first = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            manifest
        )
        second = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            manifest
        )
        self.assertEqual(first, second)
        self.assertEqual(manifest, self.manifest)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_tamper(self):
        receipt = module.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            self.document, self.manifest
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertTrue(receipt["implementation_manifest_exactly_verified"])
        self.assertFalse(receipt["registration_activated"])
        tampered = copy.deepcopy(self.document)
        tampered["authority"]["presentation_mount_allowed"] = True
        tampered.pop("registration_hash")
        tampered = module.seal_strict_canonical_document(
            tampered, "registration_hash"
        )
        receipt = module.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            tampered, self.manifest
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["registration_exactly_verified"])

    def test_invalid_manifest_receipt_does_not_claim_manifest_verification(self):
        invalid = dict(self.manifest)
        invalid["portfolio_risk_projection_v4"] = "0" * 64
        document = module.build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            invalid
        )
        receipt = module.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2(
            document, invalid
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["implementation_manifest_exactly_verified"])
        self.assertFalse(document["facts"]["registration_candidate_built"])

    def test_production_module_has_no_renderer_file_runtime_or_browser_imports(self):
        source = inspect.getsource(module)
        for forbidden in (
            "risk_service",
            "exchange_terminal.server",
            "subprocess",
            "selenium",
            "playwright",
            "requests",
            "sqlite3",
            "pathlib",
            "open(",
        ):
            self.assertNotIn(forbidden, source)

    def test_no_ready_profit_or_permission_claim(self):
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotRegex(serialized, r"\bREADY\b")
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertFalse(
            self.document["authority"]["presentation_consumer_activation_allowed"]
        )
        self.assertFalse(self.document["authority"]["presentation_mount_allowed"])


if __name__ == "__main__":
    unittest.main()
