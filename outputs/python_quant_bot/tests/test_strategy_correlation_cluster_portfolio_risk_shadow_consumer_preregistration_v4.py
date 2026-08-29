from __future__ import annotations

import ast
import copy
import inspect
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4
    as contract,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3 as preregistration_v3_test_module


class StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV4Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case_type = getattr(
            preregistration_v3_test_module,
            "StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV3Tests",
        )
        self.v3_case = case_type(methodName="runTest")
        self.v3_case.setUp()
        self.preregistration_v3 = self.v3_case.document
        self.v3_context = {
            "preregistration_v2": self.v3_case.v2_document,
            "v2_verification_context": self.v3_case.v2_context,
        }
        self.manifest = contract.expected_shadow_consumer_implementation_sha256_v4()
        self.document = self.build()

    def build(self, **overrides):
        values = {
            "preregistration_v3": self.preregistration_v3,
            "v3_verification_context": self.v3_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
            **values
        )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "preregistration_v3": self.preregistration_v3,
            "v3_verification_context": self.v3_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4(
            **values
        )

    def test_v3_gap_is_byte_identical_when_unrelated_readiness_hash_drifts(self) -> None:
        first = self.v3_case.build()
        second = self.v3_case.build()
        self.assertEqual(first, second)
        encoded = json.dumps(first, sort_keys=True)
        self.assertNotIn("readiness-envelope-v3", encoded)
        self.assertNotIn("readiness_v3", encoded)

    def test_expected_manifest_extends_v3_with_complete_readiness_chain(self) -> None:
        for artifact_id in (
            "shadow_input_readiness_envelope_v1",
            "shadow_input_readiness_envelope_v2",
            "trusted_clock_authority_v3",
            "shadow_input_readiness_envelope_v3",
            "shadow_preregistration_v3",
        ):
            self.assertIn(artifact_id, self.manifest)
        self.assertEqual(len(self.manifest), len(set(self.manifest)))

    def test_status_remains_blocked(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(self.document["decision"], contract.DECISION)

    def test_immutable_v3_source_is_exactly_verified(self) -> None:
        self.assertTrue(self.document["source"]["immutable_v3_exactly_verified"])
        self.assertEqual(
            self.document["source"]["immutable_v3_preregistration_hash"],
            self.preregistration_v3["preregistration_hash"],
        )

    def test_exactly_three_local_blocker_closures_are_preserved(self) -> None:
        self.assertEqual(
            self.document["closed_local_blockers"],
            self.preregistration_v3["closed_local_blockers"],
        )
        self.assertEqual(len(self.document["closed_local_blockers"]), 3)

    def test_readiness_v3_is_pinned_but_not_evidence_bound(self) -> None:
        capability = self.document["newly_pinned_local_capabilities"][-1]
        self.assertEqual(
            capability["capability"],
            "PORTFOLIO_RISK_SHADOW_INPUT_READINESS_ENVELOPE_V3",
        )
        self.assertTrue(capability["contract_pinned"])
        self.assertFalse(capability["evidence_bound"])
        self.assertFalse(capability["consumer_executed"])
        self.assertFalse(capability["external_authority_verified"])

    def test_content_issuance_replay_capability_pin_is_preserved(self) -> None:
        self.assertEqual(
            self.document["newly_pinned_local_capabilities"][0],
            self.preregistration_v3["newly_pinned_local_capabilities"][0],
        )

    def test_fourteenth_signed_clock_schema_is_required(self) -> None:
        schemas = self.document["required_shadow_input_schemas"]
        self.assertEqual(len(schemas), 14)
        self.assertEqual(
            schemas[-1]["input"], "signed_trusted_clock_authority_attestation"
        )

    def test_contract_pins_readiness_schema_fingerprint_and_maturity(self) -> None:
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["readiness_v3_schema_version"],
            "strategy-correlation-cluster-portfolio-risk-shadow-input-readiness-envelope-v3",
        )
        self.assertEqual(
            pins["readiness_v3_static_fingerprint"],
            "20260822-portfolio-risk-shadow-input-readiness-envelope-3",
        )
        self.assertEqual(pins["readiness_v3_required_input_count"], 14)
        self.assertIn("EXTERNAL_TRUST_UNPROVEN", pins["readiness_v3_maturity_state"])

    def test_new_blockers_keep_evidence_and_external_trust_unproven(self) -> None:
        blockers = self.document["blockers"]
        self.assertIn("readiness_envelope_v3_evidence_not_bound", blockers)
        self.assertIn("readiness_envelope_v3_exact_hash_not_verified", blockers)
        self.assertIn("signed_time_external_authority_trust_unproven", blockers)
        self.assertIn(
            "trusted_clock_nonce_and_replay_durability_unproven", blockers
        )

    def test_facts_do_not_claim_readiness_evidence_or_execution(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["readiness_envelope_v3_contract_pinned"])
        self.assertTrue(facts["readiness_envelope_v3_implementation_chain_pinned"])
        self.assertFalse(facts["readiness_envelope_v3_evidence_bound"])
        self.assertFalse(facts["readiness_envelope_v3_exactly_verified"])
        self.assertFalse(facts["shadow_application_consumer_implemented"])
        self.assertFalse(facts["shadow_consumer_executed"])
        self.assertFalse(facts["risk_service_invoked"])

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

    def test_activation_order_requires_exact_adr0181_evidence_before_consumer(self) -> None:
        order = self.document["activation_order"]
        self.assertLess(
            order.index("SUPPLY_AND_EXACTLY_VERIFY_ADR0181_READINESS_ENVELOPE"),
            order.index("IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V4"),
        )
        self.assertEqual(order[-1], "SEPARATELY_AUTHORIZE_CURRENT_SWITCH")

    def test_build_is_deterministic(self) -> None:
        self.assertEqual(self.document, self.build())

    def test_public_verifier_accepts_exact_rebuild(self) -> None:
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["preregistration_exactly_verified"])
        self.assertEqual(result["preregistration_status"], "BLOCKED")

    def test_public_verifier_rejects_projection_tamper(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["authority"]["current_admission_allowed"] = True
        result = self.verify(document=changed)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["current_admission_allowed"])

    def test_rejects_tampered_v3_source(self) -> None:
        changed = copy.deepcopy(self.preregistration_v3)
        changed["facts"]["runtime_consumer_bound"] = True
        with self.assertRaises(contract.ShadowConsumerPreregistrationV4ContractError):
            self.build(preregistration_v3=changed)

    def test_rejects_wrong_v3_context(self) -> None:
        changed = copy.deepcopy(self.v3_context)
        changed["preregistration_v2"] = {}
        with self.assertRaises(contract.ShadowConsumerPreregistrationV4ContractError):
            self.build(v3_verification_context=changed)

    def test_rejects_missing_manifest_entry(self) -> None:
        changed = dict(self.manifest)
        del changed["shadow_input_readiness_envelope_v3"]
        with self.assertRaises(contract.ShadowConsumerPreregistrationV4ContractError):
            self.build(current_implementation_sha256=changed)

    def test_rejects_extra_manifest_entry(self) -> None:
        changed = dict(self.manifest)
        changed["extra"] = "0" * 64
        with self.assertRaises(contract.ShadowConsumerPreregistrationV4ContractError):
            self.build(current_implementation_sha256=changed)

    def test_rejects_each_new_implementation_hash_drift(self) -> None:
        for artifact_id in (
            "shadow_input_readiness_envelope_v1",
            "shadow_input_readiness_envelope_v2",
            "trusted_clock_authority_v3",
            "shadow_input_readiness_envelope_v3",
            "shadow_preregistration_v3",
        ):
            with self.subTest(artifact_id=artifact_id):
                changed = dict(self.manifest)
                changed[artifact_id] = "0" * 64
                with self.assertRaises(
                    contract.ShadowConsumerPreregistrationV4ContractError
                ):
                    self.build(current_implementation_sha256=changed)

    def test_v3_context_schema_is_exact(self) -> None:
        changed = copy.deepcopy(self.v3_context)
        changed["extra"] = None
        with self.assertRaises(contract.ShadowConsumerPreregistrationV4ContractError):
            self.build(v3_verification_context=changed)

    def test_api_does_not_accept_readiness_evidence_instance(self) -> None:
        parameters = inspect.signature(
            contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4
        ).parameters
        self.assertNotIn("readiness_envelope_v3", parameters)
        self.assertNotIn("trusted_clock_attestation", parameters)

    def test_production_module_does_not_import_runtime_or_shadow_execution(self) -> None:
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
            any(
                module.endswith(forbidden_suffixes)
                for module in imported_modules
            )
        )

    def test_output_has_no_ready_profit_or_current_claim(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn('"READY"', encoded)
        self.assertNotIn("profitability_verified", encoded)
        self.assertFalse(self.document["authority"]["current_admission_allowed"])
        self.assertFalse(self.document["authority"]["paper_authorized"])
        self.assertFalse(self.document["authority"]["live_order_allowed"])

    def test_build_does_not_mutate_inputs(self) -> None:
        source = copy.deepcopy(self.preregistration_v3)
        context = copy.deepcopy(self.v3_context)
        manifest = copy.deepcopy(self.manifest)
        snapshots = copy.deepcopy((source, context, manifest))
        self.build(
            preregistration_v3=source,
            v3_verification_context=context,
            current_implementation_sha256=manifest,
        )
        self.assertEqual(snapshots, (source, context, manifest))


if __name__ == "__main__":
    unittest.main()
