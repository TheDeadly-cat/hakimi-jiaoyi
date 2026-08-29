from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1 as module
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1 import (
    DECISION,
    SCHEMA_VERSION,
    STAGE_ORDER,
    STATIC_FINGERPRINT,
    STATUS,
    build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1,
    expected_presentation_consumer_implementation_sha256_v1,
    verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1,
)


class PortfolioRiskPresentationConsumerRegistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = expected_presentation_consumer_implementation_sha256_v1()
        self.document = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
            self.manifest
        )

    def test_versions_status_and_decision_are_locked(self):
        self.assertEqual(self.document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(self.document["status"], STATUS)
        self.assertEqual(self.document["decision"], DECISION)
        self.assertEqual(STATUS, "BLOCKED")

    def test_manifest_contains_exactly_four_presentation_artifacts(self):
        self.assertEqual(
            set(self.manifest),
            {
                "portfolio_risk_projection_v3",
                "portfolio_risk_freshness_gate_card_v3_js",
                "portfolio_risk_freshness_gate_card_v3_css",
                "portfolio_risk_freshness_gate_consumer_fixture_v3_js",
            },
        )
        self.assertEqual(self.document["source"]["implementation_pin_count"], 4)

    def test_actual_files_match_all_four_registered_hashes(self):
        for artifact in self.document["source"]["artifacts"]:
            actual = hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["expected_sha256"])

    def test_each_hash_drift_fails_closed(self):
        for artifact_id in sorted(self.manifest):
            with self.subTest(artifact_id=artifact_id):
                manifest = dict(self.manifest)
                manifest[artifact_id] = "0" * 64
                document = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
                    manifest
                )
                self.assertEqual(document["status"], "BLOCKED")
                self.assertEqual(document["decision"], "REGISTRATION_INPUT_INVALID_FAIL_CLOSED")
                self.assertIn("implementation_manifest_mismatch", document["blockers"])

    def test_missing_extra_and_scalar_alias_manifest_fail_closed(self):
        missing = dict(self.manifest)
        missing.pop("portfolio_risk_projection_v3")
        extra = {**self.manifest, "unexpected": "0" * 64}
        alias = dict(self.manifest)
        alias["portfolio_risk_projection_v3"] = True
        for manifest in (missing, extra, alias):
            self.assertFalse(
                build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
                    manifest
                )["source"]["implementation_manifest_contract_verified"]
            )

    def test_contract_pins_projection_card_fixture_and_stage_order(self):
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["projection_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-projection-v3",
        )
        self.assertEqual(pins["card_schema_version"], "portfolio-risk-freshness-gate-card-v3")
        self.assertEqual(
            pins["consumer_fixture_schema_version"],
            "portfolio-risk-freshness-presentation-consumer-fixture-v3",
        )
        self.assertEqual(pins["stage_order"], list(STAGE_ORDER))
        self.assertEqual(pins["permission_policy"], "ALWAYS_UNAUTHORIZED_V1")

    def test_candidate_is_not_registration_activation(self):
        facts = self.document["facts"]
        self.assertTrue(facts["registration_candidate_built"])
        self.assertFalse(facts["registration_activated"])
        self.assertEqual(self.document["consumer"]["registration_state"], "CANDIDATE_ONLY")

    def test_no_evidence_execution_dom_browser_http_or_mount_claim(self):
        facts = self.document["facts"]
        for key in (
            "projection_evidence_bound",
            "consumer_fixture_executed",
            "render_descriptor_reviewed",
            "dom_contract_reviewed",
            "browser_visual_review_performed",
            "presentation_http_contract_versioned",
            "runtime_consumer_bound",
            "server_route_registered",
            "ui_mounted",
        ):
            self.assertIs(facts[key], False)

    def test_all_authority_remains_denied(self):
        for key, value in self.document["authority"].items():
            if key == "descriptive_only":
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)

    def test_activation_order_keeps_evidence_before_dom_and_current_last(self):
        order = self.document["activation_order"]
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")
        self.assertLess(
            order.index("BIND_AND_EXACTLY_VERIFY_PROJECTION_V3_EVIDENCE"),
            order.index("AUTHORIZE_ISOLATED_DOM_CONTRACT_REVIEW"),
        )
        self.assertLess(
            order.index("AUTHORIZE_BROWSER_VISUAL_REVIEW"),
            order.index("SEPARATELY_AUTHORIZE_PRESENTATION_MOUNT"),
        )

    def test_api_accepts_only_static_manifest(self):
        parameters = list(
            inspect.signature(
                build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1
            ).parameters
        )
        self.assertEqual(parameters, ["current_implementation_sha256"])

    def test_output_embeds_no_projection_fixture_markup_or_dom_instance(self):
        serialized = json.dumps(self.document, sort_keys=True)
        for forbidden in (
            '"projection_document"',
            '"fixture_descriptor"',
            '"markup"',
            '"dom_instance"',
            '"browser_result"',
            '"runtime_handle"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_build_is_deterministic_and_does_not_mutate_manifest(self):
        manifest = copy.deepcopy(self.manifest)
        first = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
            manifest
        )
        second = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
            manifest
        )
        self.assertEqual(first, second)
        self.assertEqual(manifest, self.manifest)

    def test_exact_verifier_accepts_rebuild_and_rejects_tamper(self):
        receipt = verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
            self.document, self.manifest
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["registration_activated"])
        tampered = copy.deepcopy(self.document)
        tampered["authority"]["presentation_mount_allowed"] = True
        receipt = verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v1(
            tampered, self.manifest
        )
        self.assertEqual(receipt["status"], "BLOCK")

    def test_production_module_has_no_renderer_runtime_or_browser_imports(self):
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

    def test_no_ready_profit_or_permission_claim(self):
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotRegex(serialized, r"\bREADY\b")
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertFalse(self.document["authority"]["presentation_mount_allowed"])


if __name__ == "__main__":
    unittest.main()
