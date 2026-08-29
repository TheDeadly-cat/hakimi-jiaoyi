from __future__ import annotations

import copy
import inspect
import json
import unittest

import exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6 as module
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6 import (
    DECISION,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    STATUS,
    V5_VERIFICATION_CONTEXT_KEYS,
    build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6,
    expected_shadow_consumer_implementation_sha256_v6,
    verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5 import (
    StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV5Tests,
)


NEW_PIN_IDS = {
    "shadow_preregistration_v5",
    "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
    "portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
    "portfolio_risk_adapter_v3",
    "portfolio_risk_projection_v3",
    "portfolio_risk_freshness_gate_card_v3_js",
    "portfolio_risk_freshness_gate_card_v3_css",
}


class PortfolioRiskShadowConsumerPreregistrationV6Tests(unittest.TestCase):
    def setUp(self) -> None:
        case = StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV5Tests(
            "test_status_remains_blocked"
        )
        case.setUp()
        self.v5_case = case
        self.v5_document = copy.deepcopy(case.document)
        self.v5_context = {
            "preregistration_v4": case.preregistration_v4,
            "v4_verification_context": case.v4_context,
            "v5_implementation_sha256": case.manifest,
        }
        self.manifest = expected_shadow_consumer_implementation_sha256_v6()
        self.document = self.build()

    def build(self, **overrides):
        return build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
            overrides.get("v5_document", self.v5_document),
            overrides.get("v5_context", self.v5_context),
            overrides.get("manifest", self.manifest),
        )

    def verify(self, document=None, **overrides):
        return verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6(
            self.document if document is None else document,
            overrides.get("v5_document", self.v5_document),
            overrides.get("v5_context", self.v5_context),
            overrides.get("manifest", self.manifest),
        )

    def test_public_versions_and_status_are_locked(self):
        self.assertEqual(self.document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(self.document["status"], STATUS)
        self.assertEqual(self.document["decision"], DECISION)
        self.assertEqual(STATUS, "BLOCKED")

    def test_immutable_v5_is_exactly_verified(self):
        source = self.document["source"]
        self.assertTrue(source["immutable_v5_exactly_verified"])
        self.assertEqual(
            source["immutable_v5_preregistration_hash"],
            self.v5_document["preregistration_hash"],
        )

    def test_manifest_extends_v5_by_exactly_seven_pins(self):
        self.assertEqual(len(self.v5_case.manifest), 26)
        self.assertEqual(len(self.manifest), 33)
        self.assertEqual(set(self.manifest) - set(self.v5_case.manifest), NEW_PIN_IDS)
        self.assertEqual(self.document["facts"]["new_implementation_pin_count"], 7)

    def test_new_artifact_hashes_are_exposed_only_as_pins(self):
        artifacts = self.document["source"]["new_artifacts"]
        self.assertEqual({item["artifact_id"] for item in artifacts}, NEW_PIN_IDS)
        for item in artifacts:
            self.assertEqual(item["expected_sha256"], self.manifest[item["artifact_id"]])
            self.assertEqual(len(item["expected_sha256"]), 64)

    def test_contract_pins_exact_lineage_adapter_projection_and_card_versions(self):
        pins = self.document["contract_pins"]
        self.assertTrue(pins["lineage_binding_v1_schema_version"].endswith("-v1"))
        self.assertTrue(pins["lineage_binding_v2_schema_version"].endswith("-v2"))
        self.assertEqual(
            pins["adapter_v3_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-adapter-v3",
        )
        self.assertEqual(
            pins["projection_v3_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-projection-v3",
        )
        self.assertEqual(
            pins["freshness_gate_card_v3_schema_version"],
            "portfolio-risk-freshness-gate-card-v3",
        )

    def test_each_new_hash_drift_is_rejected(self):
        for artifact_id in sorted(NEW_PIN_IDS):
            with self.subTest(artifact_id=artifact_id):
                manifest = dict(self.manifest)
                manifest[artifact_id] = "0" * 64
                document = self.build(manifest=manifest)
                self.assertEqual(document["status"], "BLOCKED")
                self.assertEqual(
                    document["decision"], "PREREGISTRATION_INPUT_INVALID_FAIL_CLOSED"
                )
                self.assertIn(
                    "successor_implementation_manifest_mismatch",
                    document["blockers"],
                )

    def test_missing_and_extra_manifest_entries_are_rejected(self):
        missing = dict(self.manifest)
        missing.pop("portfolio_risk_adapter_v3")
        extra = dict(self.manifest)
        extra["unexpected"] = "0" * 64
        for manifest in (missing, extra):
            self.assertFalse(
                self.build(manifest=manifest)["source"][
                    "successor_manifest_contract_verified"
                ]
            )

    def test_tampered_v5_fails_closed(self):
        predecessor = copy.deepcopy(self.v5_document)
        predecessor["status"] = "PASS"
        document = self.build(v5_document=predecessor)
        self.assertEqual(document["decision"], "PREREGISTRATION_INPUT_INVALID_FAIL_CLOSED")
        self.assertFalse(document["source"]["immutable_v5_exactly_verified"])
        self.assertIn("immutable_v5_exact_verification_failed", document["blockers"])

    def test_v5_context_requires_exact_three_keys(self):
        self.assertEqual(set(self.v5_context), V5_VERIFICATION_CONTEXT_KEYS)
        for context in (
            {key: value for key, value in self.v5_context.items() if key != "preregistration_v4"},
            {**self.v5_context, "unexpected": True},
        ):
            document = self.build(v5_context=context)
            self.assertFalse(document["source"]["immutable_v5_exactly_verified"])

    def test_required_fourteen_shadow_inputs_are_byte_preserved(self):
        self.assertEqual(
            self.document["required_shadow_input_schemas"],
            self.v5_document["required_shadow_input_schemas"],
        )
        self.assertEqual(len(self.document["required_shadow_input_schemas"]), 14)

    def test_three_closed_local_blockers_are_byte_preserved(self):
        self.assertEqual(
            self.document["closed_local_blockers"],
            self.v5_document["closed_local_blockers"],
        )
        self.assertEqual(len(self.document["closed_local_blockers"]), 3)

    def test_predecessor_blockers_are_preserved_and_new_gaps_are_appended(self):
        blockers = self.document["blockers"]
        prefix = blockers[: len(self.v5_document["blockers"])]
        self.assertEqual(prefix, self.v5_document["blockers"])
        for blocker in (
            "adapter_v2_freshness_lineage_v2_evidence_not_bound",
            "portfolio_risk_adapter_v3_evidence_not_bound",
            "portfolio_risk_projection_v3_evidence_not_bound",
            "freshness_gate_card_v3_dom_not_reviewed",
            "browser_visual_review_v3_not_performed",
            "presentation_http_contract_v3_not_versioned",
        ):
            self.assertIn(blocker, blockers)

    def test_activation_order_keeps_consumer_first_and_current_last(self):
        order = self.document["activation_order"]
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")
        self.assertLess(
            order.index("BIND_AND_EXACTLY_VERIFY_ADR0190_PROJECTION_V3_EVIDENCE"),
            order.index("REGISTER_UNMOUNTED_PRESENTATION_CONSUMER_FIXTURE_V3"),
        )
        self.assertLess(
            order.index("REGISTER_UNMOUNTED_PRESENTATION_CONSUMER_FIXTURE_V3"),
            order.index("AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW_V3"),
        )

    def test_contract_pins_do_not_claim_evidence_or_execution(self):
        facts = self.document["facts"]
        for key in (
            "lineage_v2_evidence_bound",
            "adapter_v3_evidence_bound",
            "adapter_v3_exactly_verified",
            "projection_v3_evidence_bound",
            "projection_v3_exactly_verified",
            "presentation_consumer_v3_registered",
            "dom_contract_v3_reviewed",
            "browser_visual_review_v3_performed",
            "runtime_consumer_bound",
            "shadow_consumer_executed",
            "ui_mounted",
        ):
            self.assertIs(facts[key], False)

    def test_all_authority_remains_denied(self):
        for key, value in self.document["authority"].items():
            if key == "descriptive_only":
                self.assertIs(value, True)
            else:
                self.assertIs(value, False)

    def test_api_accepts_no_adapter_projection_dom_or_browser_evidence(self):
        parameters = list(
            inspect.signature(
                build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v6
            ).parameters
        )
        self.assertEqual(
            parameters,
            [
                "preregistration_v5_document",
                "v5_verification_context",
                "current_implementation_sha256",
            ],
        )

    def test_output_embeds_no_new_evidence_instances(self):
        serialized = json.dumps(self.document, sort_keys=True)
        for forbidden in (
            '"adapter_v3_document"',
            '"projection_v3_document"',
            '"lineage_binding_v2_document"',
            '"dom_instance"',
            '"browser_result"',
            '"runtime_handle"',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_build_is_deterministic_and_does_not_mutate_inputs(self):
        predecessor = copy.deepcopy(self.v5_document)
        context = copy.deepcopy(self.v5_context)
        manifest = copy.deepcopy(self.manifest)
        first = self.build(
            v5_document=predecessor, v5_context=context, manifest=manifest
        )
        second = self.build(
            v5_document=predecessor, v5_context=context, manifest=manifest
        )
        self.assertEqual(first, second)
        self.assertEqual(predecessor, self.v5_document)
        self.assertEqual(context, self.v5_context)
        self.assertEqual(manifest, self.manifest)

    def test_public_verifier_accepts_exact_rebuild_and_rejects_tamper(self):
        self.assertEqual(self.verify()["status"], "PASS")
        tampered = copy.deepcopy(self.document)
        tampered["authority"]["paper_authorized"] = True
        receipt = self.verify(tampered)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertFalse(receipt["preregistration_exactly_verified"])

    def test_production_module_has_no_runtime_or_execution_imports(self):
        source = inspect.getsource(module)
        for forbidden in (
            "exchange_terminal.server",
            "exchange_terminal.services.risk_service",
            "quant_bot.engine",
            "subprocess",
            "sqlite3",
            "requests",
        ):
            self.assertNotIn(forbidden, source)

    def test_no_ready_profit_or_activation_claim(self):
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotRegex(serialized, r"\bREADY\b")
        self.assertFalse(self.document["facts"]["profitability_proven"])
        self.assertFalse(
            self.document["authority"]["shadow_consumer_activation_allowed"]
        )


if __name__ == "__main__":
    unittest.main()
