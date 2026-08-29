from __future__ import annotations

from copy import deepcopy
import inspect
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3 as preregistration_contract,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as content_replay_contract,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3 as preregistration_tests,
)
from tests import (
    test_strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as content_replay_tests,
)


class StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.preregistration_case = preregistration_tests.StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV3Tests(
            methodName="runTest"
        )
        self.preregistration_case.setUp()
        self.preregistration = self.preregistration_case.document
        self.preregistration_context = {
            "preregistration_v2": self.preregistration_case.v2_document,
            "v2_verification_context": self.preregistration_case.v2_context,
            "current_implementation_sha256": (
                self.preregistration_case.manifest
            ),
        }
        self.content_replay_case = content_replay_tests.StrategyCorrelationProviderDatasetContentIssuanceReplayGateV1Tests(
            methodName="runTest"
        )
        self.content_replay_case.setUp()
        self.content_replay_verification = self.content_replay_case.evaluate()
        self.content_replay_context = (
            self.content_replay_case.evaluation_values()
        )
        self.document = self.build()

    def source_verifiers(self):
        return self.content_replay_case.source_verifiers()

    def build(self, **overrides):
        values = {
            "preregistration_v3": self.preregistration,
            "content_issuance_replay_verification": (
                self.content_replay_verification
            ),
            "preregistration_verification_context": (
                self.preregistration_context
            ),
            "content_issuance_replay_verification_context": (
                self.content_replay_context
            ),
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
                **values
            )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "preregistration_v3": self.preregistration,
            "content_issuance_replay_verification": (
                self.content_replay_verification
            ),
            "preregistration_verification_context": (
                self.preregistration_context
            ),
            "content_issuance_replay_verification_context": (
                self.content_replay_context
            ),
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
                **values
            )

    def test_verified_replay_source_remains_unknown_partial_denied(self) -> None:
        self.assertEqual(self.document["status"], "UNKNOWN")
        self.assertEqual(
            self.document["source_state"],
            subject.POSITIVE_SOURCE_STATE,
        )
        self.assertEqual(
            self.document["gap_state"],
            subject.POSITIVE_GAP_STATE,
        )
        self.assertEqual(
            self.document["maturity_state"],
            subject.POSITIVE_MATURITY_STATE,
        )
        self.assertEqual(
            self.document["permission_state"],
            "DENIED",
        )

    def test_inventory_has_seven_verified_and_six_not_supplied(self) -> None:
        summary = self.document["summary"]
        self.assertEqual(summary["required_input_count"], 13)
        self.assertEqual(summary["verified_input_count"], 7)
        self.assertEqual(summary["not_supplied_input_count"], 6)
        self.assertEqual(summary["unverified_input_count"], 0)
        states = {
            entry["input"]: entry["state"]
            for entry in self.document["input_inventory"]
        }
        self.assertEqual(
            states["provider_dataset_content_issuance_replay_verification"],
            "VERIFIED",
        )
        self.assertEqual(states["dual_source_receipt"], "NOT_SUPPLIED")

    def test_inventory_is_unique_versioned_and_projection_free(self) -> None:
        inventory = self.document["input_inventory"]
        names = [entry["input"] for entry in inventory]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(
            all(
                type(entry["schema_version"]) is str
                and entry["schema_version"].endswith("v1")
                for entry in inventory
            )
        )
        self.assertFalse(
            any("ui" in name or "projection" in name for name in names)
        )

    def test_local_replay_binding_does_not_promote_external_facts(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["preregistration_v3_verified"])
        self.assertTrue(facts["content_issuance_replay_gate_verified"])
        self.assertTrue(facts["content_issuance_checkpoint_verified"])
        self.assertFalse(facts["external_provider_key_control_verified"])
        self.assertFalse(facts["external_provider_data_issuance_verified"])
        self.assertFalse(
            facts["external_content_replay_registry_authority_verified"]
        )
        self.assertFalse(
            facts["runtime_consumption_replay_enforcement_verified"]
        )

    def test_source_lineage_contains_hashes_only(self) -> None:
        lineage = self.document["source_lineage"]
        self.assertTrue(
            all(
                type(value) is str and len(value) == 64
                for value in lineage.values()
            )
        )
        self.assertEqual(
            lineage["future_evaluation_id_hash"],
            self.content_replay_verification[
                "future_evaluation_id_hash"
            ],
        )

    def test_documents_contexts_signatures_and_proofs_are_not_embedded(self) -> None:
        serialized = json.dumps(self.document, sort_keys=True)
        self.assertNotIn(
            self.content_replay_case.checkpoint["signature_base64"],
            serialized,
        )
        self.assertNotIn(
            self.content_replay_case.occurrence_audit["signature_base64"],
            serialized,
        )
        self.assertNotIn("signature_base64", self.document)
        self.assertNotIn("inclusion_proof", self.document)
        self.assertNotIn("consistency_proof", self.document)
        self.assertNotIn("verification_context", serialized)

    def test_all_operational_authority_is_denied(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )
        self.assertEqual(
            self.document["permissions"],
            {"paper_authorized": False, "live_order_allowed": False},
        )

    def test_missing_preregistration_context_fails_closed_to_unknown(self) -> None:
        context = dict(self.preregistration_context)
        context.pop("preregistration_v2")
        document = self.build(
            preregistration_verification_context=context
        )
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["maturity_state"], "UNKNOWN")
        self.assertEqual(document["permission_state"], "DENIED")
        self.assertEqual(document["input_inventory"], [])

    def test_extra_replay_context_fails_closed_to_unknown(self) -> None:
        context = {**self.content_replay_context, "unexpected": {}}
        document = self.build(
            content_issuance_replay_verification_context=context
        )
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_CONTEXT_INVALID", document["blockers"])

    def test_non_dict_context_fails_closed_to_unknown(self) -> None:
        document = self.build(
            preregistration_verification_context=[]
        )
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["summary"]["required_input_count"], 0)

    def test_preregistration_verification_failure_is_unknown(self) -> None:
        failed = {
            "schema_version": (
                preregistration_contract.PREREGISTRATION_VERIFICATION_SCHEMA_VERSION
            ),
            "status": "FAIL",
            "preregistration_exactly_verified": False,
            "preregistration_status": "UNKNOWN",
            "blockers": ["forced"],
            "shadow_consumer_activation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with patch.object(
            preregistration_contract,
            "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3",
            return_value=failed,
        ):
            document = self.build()
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_CONTRACT_UNVERIFIED", document["blockers"])

    def test_replay_verification_failure_is_unknown(self) -> None:
        with patch.object(
            content_replay_contract,
            "verify_provider_dataset_content_issuance_replay_gate_v1",
            return_value=False,
        ):
            document = self.build()
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_CONTRACT_UNVERIFIED", document["blockers"])

    def test_verifier_exception_is_unknown(self) -> None:
        with patch.object(
            content_replay_contract,
            "verify_provider_dataset_content_issuance_replay_gate_v1",
            side_effect=RuntimeError("synthetic"),
        ):
            document = self.build()
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_VERIFIER_ERROR", document["blockers"])

    def test_semantic_replay_source_tamper_is_unknown(self) -> None:
        tampered = deepcopy(self.content_replay_verification)
        tampered["facts"][
            "external_provider_data_issuance_verified"
        ] = True
        document = self.build(
            content_issuance_replay_verification=tampered
        )
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["permission_state"], "DENIED")

    def test_preregistration_authority_tamper_is_unknown(self) -> None:
        tampered = deepcopy(self.preregistration)
        tampered["authority"]["current_admission_allowed"] = True
        document = self.build(preregistration_v3=tampered)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_CONTRACT_UNVERIFIED", document["blockers"])

    def test_positive_build_is_deterministic_and_exactly_verified(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))

    def test_unknown_build_is_deterministic_and_exactly_verified(self) -> None:
        context = {}
        first = self.build(
            preregistration_verification_context=context
        )
        second = self.build(
            preregistration_verification_context=context
        )
        self.assertEqual(first, second)
        self.assertTrue(
            self.verify(
                first,
                preregistration_verification_context=context,
            )
        )

    def test_envelope_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.document)
        tampered["permission_state"] = "ALLOWED"
        self.assertFalse(self.verify(tampered))

    def test_coherent_reseal_cannot_promote_permission(self) -> None:
        tampered = deepcopy(self.document)
        tampered["authority"]["current_admission_allowed"] = True
        body = {
            key: value
            for key, value in tampered.items()
            if key != "envelope_hash"
        }
        tampered["envelope_hash"] = subject._sha256(body)
        self.assertFalse(self.verify(tampered))

    def test_inputs_are_not_mutated(self) -> None:
        before_preregistration = deepcopy(self.preregistration)
        before_replay = deepcopy(self.content_replay_verification)
        before_preregistration_context = deepcopy(
            self.preregistration_context
        )
        before_replay_context = deepcopy(self.content_replay_context)
        self.build()
        self.assertEqual(self.preregistration, before_preregistration)
        self.assertEqual(self.content_replay_verification, before_replay)
        self.assertEqual(
            self.preregistration_context,
            before_preregistration_context,
        )
        self.assertEqual(self.content_replay_context, before_replay_context)

    def test_blockers_include_missing_inputs_and_no_ready_wording(self) -> None:
        blockers = self.document["blockers"]
        self.assertIn(
            "required_input_not_supplied:dual_source_receipt",
            blockers,
        )
        self.assertIn("shadow_consumer_not_executed", blockers)
        self.assertIn("risk_service_not_invoked", blockers)
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotIn("READY", serialized)

    def test_api_and_module_do_not_accept_or_expose_execution_dependencies(self) -> None:
        functions = (
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1,
            subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1,
        )
        forbidden = (
            "private",
            "database",
            "cache",
            "runtime_store",
            "shadow_service",
            "risk_service",
            "order",
        )
        for function in functions:
            with self.subTest(function=function.__name__):
                parameters = inspect.signature(function).parameters
                self.assertFalse(
                    any(
                        token in name.lower()
                        for name in parameters
                        for token in forbidden
                    )
                )
        self.assertFalse(
            any(
                "portfolio_shadow" in name or name == "risk_service"
                for name in vars(subject)
            )
        )


if __name__ == "__main__":
    unittest.main()
