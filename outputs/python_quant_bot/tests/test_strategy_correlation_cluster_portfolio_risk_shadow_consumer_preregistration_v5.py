from __future__ import annotations

import ast
import copy
import inspect
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5
    as contract,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4 as preregistration_v4_test_module


class StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV5Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case_type = getattr(
            preregistration_v4_test_module,
            "StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV4Tests",
        )
        self.v4_case = case_type(methodName="runTest")
        self.v4_case.setUp()
        self.preregistration_v4 = self.v4_case.document
        self.v4_context = {
            "preregistration_v3": self.v4_case.preregistration_v3,
            "v3_verification_context": self.v4_case.v3_context,
        }
        self.manifest = contract.expected_shadow_consumer_implementation_sha256_v5()
        self.document = self.build()

    def build(self, **overrides):
        values = {
            "preregistration_v4": self.preregistration_v4,
            "v4_verification_context": self.v4_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
            **values
        )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "preregistration_v4": self.preregistration_v4,
            "v4_verification_context": self.v4_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5(
            **values
        )

    def test_v4_is_unchanged_by_successor_presentation_pins(self) -> None:
        first = self.v4_case.build()
        second = self.v4_case.build()
        self.assertEqual(first, second)
        encoded = json.dumps(first, sort_keys=True)
        self.assertNotIn("portfolio-risk-public-projection-v2", encoded)
        self.assertNotIn("TemporalLatticeCardV2", encoded)

    def test_expected_manifest_extends_v4_with_five_successor_pins(self) -> None:
        v4_manifest = (
            preregistration_v4_test_module.contract.expected_shadow_consumer_implementation_sha256_v4()
        )
        self.assertTrue(set(v4_manifest).issubset(self.manifest))
        new_ids = set(self.manifest) - set(v4_manifest)
        self.assertEqual(
            new_ids,
            {
                "shadow_preregistration_v4",
                "portfolio_risk_adapter_v2",
                "portfolio_risk_projection_v2",
                "portfolio_risk_temporal_lattice_card_v2_js",
                "portfolio_risk_temporal_lattice_card_v2_css",
            },
        )

    def test_status_remains_blocked(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(self.document["decision"], contract.DECISION)

    def test_immutable_v4_source_is_exactly_verified(self) -> None:
        source = self.document["source"]
        self.assertTrue(source["immutable_v4_exactly_verified"])
        self.assertEqual(
            source["immutable_v4_preregistration_hash"],
            self.preregistration_v4["preregistration_hash"],
        )

    def test_exactly_three_local_blocker_closures_are_preserved(self) -> None:
        self.assertEqual(
            self.document["closed_local_blockers"],
            self.preregistration_v4["closed_local_blockers"],
        )
        self.assertEqual(len(self.document["closed_local_blockers"]), 3)

    def test_v4_capability_pins_are_byte_preserved(self) -> None:
        self.assertEqual(
            self.document["newly_pinned_local_capabilities"][:-1],
            self.preregistration_v4["newly_pinned_local_capabilities"],
        )

    def test_presentation_v2_is_pinned_but_not_evidence_bound(self) -> None:
        capability = self.document["newly_pinned_local_capabilities"][-1]
        self.assertEqual(
            capability["capability"],
            "PORTFOLIO_RISK_TEMPORAL_STABILITY_PUBLIC_PRESENTATION_V2",
        )
        self.assertTrue(capability["contract_pinned"])
        self.assertFalse(capability["evidence_bound"])
        self.assertFalse(capability["consumer_executed"])
        self.assertFalse(capability["external_authority_verified"])

    def test_required_shadow_inputs_remain_exactly_fourteen(self) -> None:
        self.assertEqual(
            self.document["required_shadow_input_schemas"],
            self.preregistration_v4["required_shadow_input_schemas"],
        )
        self.assertEqual(len(self.document["required_shadow_input_schemas"]), 14)

    def test_contract_pins_exact_adapter_projection_and_card_versions(self) -> None:
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["adapter_v2_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-adapter-v2",
        )
        self.assertEqual(
            pins["projection_v2_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-public-projection-v2",
        )
        self.assertEqual(
            pins["projection_v2_static_fingerprint"],
            "20260822-portfolio-risk-temporal-lattice-projection-lock-1",
        )
        self.assertEqual(
            pins["temporal_lattice_card_v2_global_name"],
            "HakimiPortfolioRiskTemporalLatticeCardV2",
        )

    def test_new_artifact_hashes_are_exposed_only_as_pins(self) -> None:
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["adapter_v2_implementation_sha256"],
            self.manifest["portfolio_risk_adapter_v2"],
        )
        self.assertEqual(
            pins["projection_v2_implementation_sha256"],
            self.manifest["portfolio_risk_projection_v2"],
        )
        self.assertEqual(
            pins["temporal_lattice_card_v2_javascript_sha256"],
            self.manifest["portfolio_risk_temporal_lattice_card_v2_js"],
        )
        self.assertEqual(
            pins["temporal_lattice_card_v2_stylesheet_sha256"],
            self.manifest["portfolio_risk_temporal_lattice_card_v2_css"],
        )

    def test_new_blockers_keep_evidence_dom_http_and_browser_unproven(self) -> None:
        blockers = self.document["blockers"]
        for blocker in (
            "portfolio_risk_adapter_v2_evidence_not_bound",
            "portfolio_risk_projection_v2_evidence_not_bound",
            "presentation_consumer_v2_not_registered",
            "temporal_lattice_card_v2_dom_not_reviewed",
            "browser_visual_review_not_performed",
            "presentation_http_contract_v2_not_versioned",
        ):
            self.assertIn(blocker, blockers)

    def test_facts_do_not_claim_evidence_consumer_or_visual_review(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["portfolio_risk_adapter_v2_contract_pinned"])
        self.assertTrue(facts["portfolio_risk_projection_v2_contract_pinned"])
        self.assertFalse(facts["portfolio_risk_adapter_v2_evidence_bound"])
        self.assertFalse(facts["portfolio_risk_projection_v2_evidence_bound"])
        self.assertFalse(facts["presentation_consumer_v2_registered"])
        self.assertFalse(facts["dom_contract_reviewed"])
        self.assertFalse(facts["browser_visual_review_performed"])
        self.assertFalse(facts["ui_mounted"])

    def test_all_authority_remains_denied(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_activation_order_preserves_consumer_first_and_current_last(self) -> None:
        order = self.document["activation_order"]
        self.assertLess(
            order.index("SUPPLY_AND_EXACTLY_VERIFY_ADR0181_READINESS_ENVELOPE"),
            order.index("IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V5"),
        )
        self.assertLess(
            order.index(
                "BIND_AND_EXACTLY_VERIFY_ADR0184_PORTFOLIO_RISK_ADAPTER_V2_EVIDENCE"
            ),
            order.index(
                "BIND_AND_EXACTLY_VERIFY_ADR0185_PUBLIC_PROJECTION_V2_EVIDENCE"
            ),
        )
        self.assertLess(
            order.index("AUTHORIZE_ISOLATED_DOM_AND_BROWSER_VISUAL_REVIEW"),
            order.index("VERSION_PRESENTATION_HTTP_CONTRACT_BEFORE_MOUNT"),
        )
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")

    def test_build_is_deterministic(self) -> None:
        self.assertEqual(self.document, self.build())

    def test_public_verifier_accepts_exact_rebuild(self) -> None:
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["preregistration_exactly_verified"])
        self.assertEqual(result["preregistration_status"], "BLOCKED")
        self.assertFalse(result["presentation_consumer_activation_allowed"])

    def test_public_verifier_rejects_authority_tamper(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["authority"]["current_admission_allowed"] = True
        result = self.verify(document=changed)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["current_admission_allowed"])

    def test_rejects_tampered_v4_source(self) -> None:
        changed = copy.deepcopy(self.preregistration_v4)
        changed["facts"]["ui_mounted"] = True
        with self.assertRaises(contract.ShadowConsumerPreregistrationV5ContractError):
            self.build(preregistration_v4=changed)

    def test_rejects_wrong_v4_context(self) -> None:
        changed = copy.deepcopy(self.v4_context)
        changed["preregistration_v3"] = {}
        with self.assertRaises(contract.ShadowConsumerPreregistrationV5ContractError):
            self.build(v4_verification_context=changed)

    def test_rejects_missing_manifest_entry(self) -> None:
        changed = dict(self.manifest)
        del changed["portfolio_risk_projection_v2"]
        with self.assertRaises(contract.ShadowConsumerPreregistrationV5ContractError):
            self.build(current_implementation_sha256=changed)

    def test_rejects_extra_manifest_entry(self) -> None:
        changed = dict(self.manifest)
        changed["extra"] = "0" * 64
        with self.assertRaises(contract.ShadowConsumerPreregistrationV5ContractError):
            self.build(current_implementation_sha256=changed)

    def test_rejects_each_new_implementation_hash_drift(self) -> None:
        for artifact_id in (
            "shadow_preregistration_v4",
            "portfolio_risk_adapter_v2",
            "portfolio_risk_projection_v2",
            "portfolio_risk_temporal_lattice_card_v2_js",
            "portfolio_risk_temporal_lattice_card_v2_css",
        ):
            with self.subTest(artifact_id=artifact_id):
                changed = dict(self.manifest)
                changed[artifact_id] = "0" * 64
                with self.assertRaises(
                    contract.ShadowConsumerPreregistrationV5ContractError
                ):
                    self.build(current_implementation_sha256=changed)

    def test_v4_context_schema_is_exact(self) -> None:
        changed = copy.deepcopy(self.v4_context)
        changed["extra"] = None
        with self.assertRaises(contract.ShadowConsumerPreregistrationV5ContractError):
            self.build(v4_verification_context=changed)

    def test_api_accepts_no_adapter_projection_or_browser_evidence(self) -> None:
        parameters = inspect.signature(
            contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5
        ).parameters
        self.assertEqual(
            set(parameters),
            {
                "preregistration_v4",
                "v4_verification_context",
                "current_implementation_sha256",
            },
        )

    def test_production_module_does_not_import_runtime_or_execution(self) -> None:
        source = inspect.getsource(contract)
        tree = ast.parse(source)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)
        forbidden_suffixes = (
            ".portfolio_shadow_risk",
            ".risk_service",
            ".server",
        )
        self.assertFalse(
            any(module.endswith(forbidden_suffixes) for module in imported_modules)
        )

    def test_output_has_no_ready_profit_or_current_claim(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn('"READY"', encoded)
        self.assertNotIn("profitability_verified", encoded)
        self.assertFalse(self.document["authority"]["current_admission_allowed"])
        self.assertFalse(self.document["authority"]["paper_authorized"])
        self.assertFalse(self.document["authority"]["live_order_allowed"])

    def test_output_embeds_no_adapter_projection_or_dom_instance(self) -> None:
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(value)
                for item in value.values():
                    collect(item)
            elif type(value) is list:
                for item in value:
                    collect(item)

        collect(self.document)
        for forbidden in (
            "adapter_v2_document",
            "projection_v2_document",
            "temporal_stability_gate",
            "innerHTML",
            "rendered_dom",
        ):
            self.assertNotIn(forbidden, keys)

    def test_build_does_not_mutate_inputs(self) -> None:
        source = copy.deepcopy(self.preregistration_v4)
        context = copy.deepcopy(self.v4_context)
        manifest = copy.deepcopy(self.manifest)
        snapshots = copy.deepcopy((source, context, manifest))
        self.build(
            preregistration_v4=source,
            v4_verification_context=context,
            current_implementation_sha256=manifest,
        )
        self.assertEqual(snapshots, (source, context, manifest))

    def test_public_exports_are_version_locked(self) -> None:
        self.assertEqual(
            contract.__all__,
            [
                "DECISION",
                "SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "STATUS",
                "ShadowConsumerPreregistrationV5ContractError",
                "VERIFICATION_SCHEMA_VERSION",
                "build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5",
                "expected_shadow_consumer_implementation_sha256_v5",
                "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v5",
            ],
        )


if __name__ == "__main__":
    unittest.main()
