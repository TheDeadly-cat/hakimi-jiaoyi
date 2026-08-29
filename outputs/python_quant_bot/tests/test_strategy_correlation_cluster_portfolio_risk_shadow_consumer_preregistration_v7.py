from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7 as module
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7 import (
    DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    STATUS,
    V6_VERIFICATION_CONTEXT_KEYS,
    build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7,
    expected_shadow_consumer_successor_implementation_sha256_v7,
    verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6 import (
    PortfolioRiskShadowConsumerPreregistrationV6Tests,
)


class PortfolioRiskShadowConsumerPreregistrationV7Tests(unittest.TestCase):
    def setUp(self) -> None:
        case = PortfolioRiskShadowConsumerPreregistrationV6Tests(
            "test_public_versions_and_status_are_locked"
        )
        case.setUp()
        self.v6_case = case
        self.v6_document = copy.deepcopy(case.document)
        self.v6_context = {
            "preregistration_v5_document": case.v5_document,
            "v5_verification_context": case.v5_context,
            "v6_implementation_sha256": case.manifest,
        }
        self.manifest = expected_shadow_consumer_successor_implementation_sha256_v7()
        self.document = self.build()

    def build(self, **overrides):
        return build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7(
            overrides.get("v6_document", self.v6_document),
            overrides.get("v6_context", self.v6_context),
            overrides.get("manifest", self.manifest),
        )

    def verify(self, document=None, **overrides):
        return verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7(
            self.document if document is None else document,
            overrides.get("v6_document", self.v6_document),
            overrides.get("v6_context", self.v6_context),
            overrides.get("manifest", self.manifest),
        )

    def test_versions_status_and_decision_are_locked(self):
        self.assertEqual(self.document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(self.document["status"], STATUS)
        self.assertEqual(self.document["decision"], DECISION)
        self.assertEqual(STATUS, "BLOCKED")

    def test_immutable_v6_is_exactly_verified(self):
        self.assertTrue(self.document["source"]["immutable_v6_exactly_verified"])
        self.assertEqual(
            self.document["source"]["immutable_v6_preregistration_hash"],
            self.v6_document["preregistration_hash"],
        )

    def test_manifest_is_layered_as_33_plus_3_without_duplication(self):
        source = self.document["source"]
        self.assertEqual(source["predecessor_implementation_pin_count"], 33)
        self.assertEqual(source["successor_implementation_pin_count"], 3)
        self.assertEqual(source["total_implementation_pin_count"], 36)
        self.assertEqual(len(self.manifest), 3)

    def test_actual_successor_files_match_all_three_hashes(self):
        for artifact in self.document["source"]["new_artifacts"]:
            actual = hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["expected_sha256"])

    def test_each_successor_hash_drift_fails_closed(self):
        for artifact_id in sorted(self.manifest):
            with self.subTest(artifact_id=artifact_id):
                manifest = dict(self.manifest)
                manifest[artifact_id] = "0" * 64
                document = self.build(manifest=manifest)
                self.assertEqual(document["decision"], "PREREGISTRATION_INPUT_INVALID_FAIL_CLOSED")
                self.assertIn("successor_implementation_manifest_mismatch", document["blockers"])

    def test_missing_extra_and_scalar_alias_manifest_fail_closed(self):
        missing = dict(self.manifest)
        missing.pop("shadow_preregistration_v6")
        extra = {**self.manifest, "unexpected": "0" * 64}
        alias = dict(self.manifest)
        alias["shadow_preregistration_v6"] = True
        for manifest in (missing, extra, alias):
            self.assertFalse(
                self.build(manifest=manifest)["source"][
                    "successor_manifest_contract_verified"
                ]
            )

    def test_tampered_v6_fails_closed(self):
        predecessor = copy.deepcopy(self.v6_document)
        predecessor["status"] = "PASS"
        document = self.build(v6_document=predecessor)
        self.assertFalse(document["source"]["immutable_v6_exactly_verified"])
        self.assertIn("immutable_v6_exact_verification_failed", document["blockers"])

    def test_v6_context_requires_exact_three_keys(self):
        self.assertEqual(set(self.v6_context), V6_VERIFICATION_CONTEXT_KEYS)
        for context in (
            {key: value for key, value in self.v6_context.items() if key != "preregistration_v5_document"},
            {**self.v6_context, "unexpected": True},
        ):
            self.assertFalse(self.build(v6_context=context)["source"]["immutable_v6_exactly_verified"])

    def test_fourteen_inputs_and_three_closures_are_byte_preserved(self):
        self.assertEqual(
            self.document["required_shadow_input_schemas"],
            self.v6_document["required_shadow_input_schemas"],
        )
        self.assertEqual(self.document["closed_local_blockers"], self.v6_document["closed_local_blockers"])
        self.assertEqual(len(self.document["required_shadow_input_schemas"]), 14)
        self.assertEqual(len(self.document["closed_local_blockers"]), 3)

    def test_only_two_new_blockers_are_appended(self):
        predecessor_count = len(self.v6_document["blockers"])
        self.assertEqual(
            self.document["blockers"][:predecessor_count], self.v6_document["blockers"]
        )
        self.assertEqual(
            self.document["blockers"][predecessor_count:],
            [
                "presentation_consumer_fixture_v3_execution_evidence_not_bound",
                "presentation_consumer_registration_candidate_v1_evidence_not_bound",
            ],
        )

    def test_registration_contract_and_expected_document_hash_are_pinned(self):
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["presentation_registration_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v1",
        )
        self.assertEqual(
            pins["presentation_registration_expected_document_hash"],
            "eab3477889e172c337cc231e493f307f7929c006d476fcb4fb204359a30bc6e3",
        )

    def test_activation_order_places_fixture_and_registration_before_dom(self):
        order = self.document["activation_order"]
        dom = order.index("AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW_V3")
        self.assertLess(
            order.index("EXECUTE_ADR0192_FIXTURE_WITH_SYNTHETIC_PROJECTION_MATRIX"), dom
        )
        self.assertLess(
            order.index("BIND_AND_EXACTLY_VERIFY_ADR0193_PRESENTATION_REGISTRATION_CANDIDATE"), dom
        )
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")
        self.assertEqual(order[-2], "SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT")

    def test_pins_do_not_claim_fixture_or_registration_evidence(self):
        facts = self.document["facts"]
        for key in (
            "consumer_fixture_v3_execution_evidence_bound",
            "consumer_fixture_v3_executed",
            "presentation_registration_v1_evidence_bound",
            "presentation_registration_v1_exactly_verified",
            "presentation_registration_v1_activated",
            "dom_contract_v3_reviewed",
            "browser_visual_review_v3_performed",
            "presentation_http_contract_v3_versioned",
            "runtime_consumer_bound",
            "ui_mounted",
        ):
            self.assertIs(facts[key], False)

    def test_all_authority_remains_denied(self):
        for key, value in self.document["authority"].items():
            if key == "descriptive_only":
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)

    def test_api_accepts_no_fixture_registration_or_browser_evidence(self):
        parameters = list(
            inspect.signature(
                build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v7
            ).parameters
        )
        self.assertEqual(
            parameters,
            [
                "preregistration_v6_document",
                "v6_verification_context",
                "successor_implementation_sha256",
            ],
        )

    def test_output_embeds_no_fixture_or_registration_instance(self):
        serialized = json.dumps(self.document, sort_keys=True)
        for forbidden in (
            '"fixture_descriptor"',
            '"registration_document"',
            '"projection_document"',
            '"markup"',
            '"dom_instance"',
            '"browser_result"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_build_is_deterministic_and_does_not_mutate_inputs(self):
        predecessor = copy.deepcopy(self.v6_document)
        context = copy.deepcopy(self.v6_context)
        manifest = copy.deepcopy(self.manifest)
        first = self.build(v6_document=predecessor, v6_context=context, manifest=manifest)
        second = self.build(v6_document=predecessor, v6_context=context, manifest=manifest)
        self.assertEqual(first, second)
        self.assertEqual(predecessor, self.v6_document)
        self.assertEqual(context, self.v6_context)
        self.assertEqual(manifest, self.manifest)

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self):
        self.assertEqual(self.verify()["status"], "PASS")
        tampered = copy.deepcopy(self.document)
        tampered["authority"]["presentation_mount_allowed"] = True
        receipt = self.verify(tampered)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["preregistration_exactly_verified"])

    def test_production_module_has_no_runtime_browser_or_renderer_imports(self):
        source = inspect.getsource(module)
        for forbidden in (
            "risk_service",
            "exchange_terminal.server",
            "subprocess",
            "selenium",
            "playwright",
            "requests",
            "sqlite3",
        ):
            self.assertNotIn(forbidden, source)

    def test_no_ready_profit_or_activation_claim(self):
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotRegex(serialized, r"\bREADY\b")
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertFalse(
            self.document["authority"]["presentation_consumer_activation_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
