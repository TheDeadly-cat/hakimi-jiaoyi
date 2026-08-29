from __future__ import annotations

from copy import deepcopy
import inspect
import json
import unittest
from unittest.mock import patch

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1 as readiness_v1_contract,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v1 as adapter_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1 as dual_source_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 as legacy_binding_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 as native_cutoff_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_session_freshness_v1 as freshness_contract,
)
from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    build_correlation_cluster_complete_link_audit,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_session_freshness_v1 as freshness_tests,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1 as readiness_v1_tests,
)


class StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.v1_case = readiness_v1_tests.StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV1Tests(
            methodName="runTest"
        )
        self.v1_case.setUp()
        self.readiness_v1 = self.v1_case.document
        self.readiness_v1_context = {
            "preregistration_v3": self.v1_case.preregistration,
            "content_issuance_replay_verification": (
                self.v1_case.content_replay_verification
            ),
            "preregistration_verification_context": (
                self.v1_case.preregistration_context
            ),
            "content_issuance_replay_verification_context": (
                self.v1_case.content_replay_context
            ),
        }
        replay_context = self.v1_case.content_replay_context
        attestation_document = replay_context["attestation_document"]
        attestation_context = replay_context["attestation_context"]
        composition = attestation_context["composition_document"]
        composition_context = attestation_context["composition_context"]
        registration = attestation_context["registration"]
        receipt = attestation_context["attestation_receipt"]
        public_key = attestation_context[
            "provider_dataset_public_key_base64"
        ]
        matrix_replay = composition_context["matrix_replay"]
        completed = matrix_replay["completed_price_input"]
        derivation = composition_context["derivation_receipt"]
        preregistration = matrix_replay["preregistration"]
        payloads = {
            item["symbol"]: {"rows": item["price_rows"]}
            for item in completed["datasets"]
        }
        legacy_matrix = build_correlation_matrix(
            payloads,
            lookback=preregistration["lookback_observations"],
            minimum_overlap=preregistration["minimum_pair_overlap"],
        )
        self.legacy_binding_context = {
            "legacy_correlation_matrix": legacy_matrix,
            "completed_price_input": completed,
            "matrix_replay": matrix_replay,
            "derivation_receipt": derivation,
            "composition_document": composition,
            "composition_context": composition_context,
            "dataset_attestation_verification": attestation_document,
            "dataset_attestation_registration": registration,
            "provider_dataset_public_key_base64": public_key,
            "dataset_attestation_receipt": receipt,
            "expected_registration_hash": registration[
                "registration_hash"
            ],
            "expected_attestation_hash": receipt["attestation_hash"],
        }
        cutoff = f"{completed['cutoff_date']}T00:00:00Z"
        self.native_context = {
            "completed_price_input": completed,
            "matrix_replay": matrix_replay,
            "derivation_receipt": derivation,
            "composition_document": composition,
            "composition_context": composition_context,
            "expected_observation_cutoff_utc": cutoff,
        }
        with self.source_verifiers():
            legacy_binding = legacy_binding_contract.build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
                **self.legacy_binding_context
            )
            native_manifest = native_cutoff_contract.build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                completed,
                matrix_replay,
                derivation,
                composition,
                composition_context,
                expected_observation_cutoff_utc=cutoff,
            )
        self.freshness_registration_context = {
            "native_cutoff_manifest": native_manifest,
            "native_cutoff_context": self.native_context,
            "expected_native_cutoff_manifest_hash": native_manifest[
                "manifest_hash"
            ],
            "max_completed_session_lag": 1,
            "declared_at_utc": "2026-09-18T00:00:00Z",
        }
        with self.source_verifiers():
            freshness_registration = freshness_contract.build_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1(
                **self.freshness_registration_context
            )
        clock_case = freshness_tests.StrategyCorrelationClusterPortfolioRiskSessionFreshnessV1Tests(
            methodName="runTest"
        )
        clock = clock_case._clock()
        self.freshness_evaluation_context = {
            "registration": freshness_registration,
            "registration_inputs": self.freshness_registration_context,
            "trusted_clock_attestation": clock,
            "expected_trusted_clock_attestation_hash": clock[
                "attestation_hash"
            ],
        }
        with self.source_verifiers():
            freshness_evaluation = freshness_contract.evaluate_strategy_correlation_cluster_portfolio_risk_session_freshness_v1(
                **self.freshness_evaluation_context
            )

        symbols = legacy_matrix["symbols"]
        cluster_preregistration = build_correlation_cluster_preregistration(
            [{"cluster_id": "AB", "members": symbols}]
        )
        cluster_matrix = build_correlation_matrix_contract(
            symbols,
            {("A", "B"): 0.80},
            overlap_observations={("A", "B"): 60},
        )
        complete_link_audit = build_correlation_cluster_complete_link_audit(
            cluster_preregistration,
            cluster_matrix,
        )
        self.adapter_context = {
            "preregistration": cluster_preregistration,
            "cluster_correlation_matrix": cluster_matrix,
            "complete_link_audit": complete_link_audit,
            "equity": 10_000,
            "positions": [
                {
                    "symbol": "A",
                    "notional": 1_800,
                    "direction": "LONG",
                }
            ],
            "proposed_symbol": "B",
            "proposed_notional": 500,
            "proposed_direction": "LONG",
            "legacy_correlations": {"pairs": legacy_matrix["pairs"]},
        }
        adapter_document = adapter_contract.evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
            **self.adapter_context
        )
        legacy_envelope = dual_source_contract.build_portfolio_risk_correlation_source_envelope_v1(
            legacy_matrix,
            source_role=dual_source_contract.LEGACY_SOURCE_ROLE,
            provider_id="SYNTHETIC.LEGACY.UNIFIED",
            observation_cutoff_utc=cutoff,
        )
        cluster_envelope = dual_source_contract.build_portfolio_risk_correlation_source_envelope_v1(
            cluster_matrix,
            source_role=dual_source_contract.CLUSTER_SOURCE_ROLE,
            provider_id="SYNTHETIC.CLUSTER.UNIFIED",
            observation_cutoff_utc=cutoff,
        )
        self.dual_context = {
            "legacy_payload": legacy_matrix,
            "legacy_envelope": legacy_envelope,
            "cluster_payload": cluster_matrix,
            "cluster_envelope": cluster_envelope,
            "expected_symbols": symbols,
            "expected_observation_cutoff_utc": cutoff,
            "expected_legacy_provider_id": "SYNTHETIC.LEGACY.UNIFIED",
            "expected_cluster_provider_id": "SYNTHETIC.CLUSTER.UNIFIED",
        }
        dual_document = dual_source_contract.build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
            **self.dual_context
        )
        self.portfolio_inputs = {
            "dual_source_receipt": dual_document,
            "portfolio_risk_adapter": adapter_document,
            "legacy_matrix_derivation_binding": legacy_binding,
            "native_cutoff_manifest": native_manifest,
            "session_freshness_registration": freshness_registration,
            "session_freshness_evaluation": freshness_evaluation,
        }
        self.portfolio_contexts = {
            "dual_source_receipt": self.dual_context,
            "portfolio_risk_adapter": self.adapter_context,
            "legacy_matrix_derivation_binding": (
                self.legacy_binding_context
            ),
            "native_cutoff_manifest": self.native_context,
            "session_freshness_registration": (
                self.freshness_registration_context
            ),
            "session_freshness_evaluation": (
                self.freshness_evaluation_context
            ),
        }
        self.document = self.build()

    def source_verifiers(self):
        return self.v1_case.source_verifiers()

    def build(self, **overrides):
        values = {
            "readiness_v1": self.readiness_v1,
            "portfolio_inputs": self.portfolio_inputs,
            "readiness_v1_verification_context": self.readiness_v1_context,
            "portfolio_verification_contexts": self.portfolio_contexts,
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
                **values
            )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "readiness_v1": self.readiness_v1,
            "portfolio_inputs": self.portfolio_inputs,
            "readiness_v1_verification_context": self.readiness_v1_context,
            "portfolio_verification_contexts": self.portfolio_contexts,
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2(
                **values
            )

    def test_complete_local_input_set_remains_unknown_and_denied(self) -> None:
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
        self.assertEqual(self.document["permission_state"], "DENIED")

    def test_all_thirteen_inputs_are_locally_verified(self) -> None:
        summary = self.document["summary"]
        self.assertEqual(summary["required_input_count"], 13)
        self.assertEqual(summary["verified_input_count"], 13)
        self.assertEqual(summary["not_supplied_input_count"], 0)
        self.assertEqual(summary["unverified_input_count"], 0)
        self.assertTrue(
            all(
                entry["state"] == "VERIFIED"
                for entry in self.document["input_inventory"]
            )
        )

    def test_gate_outcomes_are_preserved_not_collapsed(self) -> None:
        outcomes = self.document["gate_outcomes"]
        self.assertEqual(
            outcomes["dual_source_receipt"]["decision"],
            "DUAL_SOURCE_PROVIDER_ASSERTIONS_ALIGNED",
        )
        self.assertEqual(
            outcomes["portfolio_risk_adapter"]["decision"],
            "WITHIN_RESEARCH_RISK_BUDGET",
        )
        self.assertEqual(
            outcomes["session_freshness_evaluation"]["decision"],
            "SESSION_LAG_WITHIN_PREREGISTERED_POLICY_EXTERNAL_TIME_AUTHORITY_UNPROVEN",
        )

    def test_shared_lineage_facts_are_explicit(self) -> None:
        facts = self.document["facts"]
        true_keys = (
            "shared_dataset_attestation_lineage_verified",
            "shared_composition_lineage_verified",
            "shared_symbol_universe_verified",
            "shared_observation_cutoff_verified",
            "shared_legacy_payload_verified",
            "shared_cluster_payload_verified",
            "shared_freshness_registration_lineage_verified",
            "local_required_input_set_verified",
        )
        self.assertTrue(all(facts[key] is True for key in true_keys))

    def test_external_runtime_and_profitability_facts_remain_false(self) -> None:
        facts = self.document["facts"]
        false_keys = (
            "external_provider_key_control_verified",
            "external_provider_data_issuance_verified",
            "external_content_replay_registry_authority_verified",
            "external_occurrence_auditor_authority_verified",
            "durable_content_checkpoint_publication_verified",
            "external_time_authority_authenticated",
            "runtime_consumption_replay_enforcement_verified",
            "future_replay_absence_verified",
            "shadow_consumer_executed",
            "risk_service_invoked",
            "ui_mounted",
            "profitability_verified",
        )
        self.assertTrue(all(facts[key] is False for key in false_keys))

    def test_hash_only_lineage_covers_all_local_documents(self) -> None:
        lineage = self.document["source_lineage"]
        self.assertEqual(len(lineage), 9)
        self.assertTrue(
            all(
                type(value) is str and len(value) == 64
                for value in lineage.values()
            )
        )

    def test_payloads_contexts_and_sensitive_evidence_are_not_embedded(self) -> None:
        serialized = json.dumps(self.document, sort_keys=True)
        self.assertNotIn("price_rows", serialized)
        self.assertNotIn("signature_base64", serialized)
        self.assertNotIn("inclusion_proof", serialized)
        self.assertNotIn("trusted_clock_attestation", serialized)
        self.assertNotIn("verification_context", serialized)

    def test_all_operational_authority_remains_denied(self) -> None:
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

    def test_build_is_deterministic_and_exactly_verified(self) -> None:
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))

    def test_invalid_readiness_v1_fails_closed_to_unknown(self) -> None:
        tampered = deepcopy(self.readiness_v1)
        tampered["source_state"] = "UNKNOWN"
        document = self.build(readiness_v1=tampered)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["permission_state"], "DENIED")

    def test_missing_portfolio_input_fails_closed_to_unknown(self) -> None:
        inputs = dict(self.portfolio_inputs)
        inputs.pop("dual_source_receipt")
        document = self.build(portfolio_inputs=inputs)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_CONTEXT_INVALID", document["blockers"])

    def test_extra_portfolio_context_fails_closed_to_unknown(self) -> None:
        contexts = {**self.portfolio_contexts, "unexpected": {}}
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_each_public_verifier_is_required(self) -> None:
        patches = (
            (
                readiness_v1_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1",
                False,
            ),
            (
                dual_source_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1",
                {"status": "FAIL"},
            ),
            (
                adapter_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_adapter_v1",
                {"status": "FAIL"},
            ),
            (
                legacy_binding_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1",
                {"status": "FAIL"},
            ),
            (
                native_cutoff_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1",
                {"status": "FAIL"},
            ),
            (
                freshness_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_policy_registration_v1",
                False,
            ),
            (
                freshness_contract,
                "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1",
                False,
            ),
        )
        for module, name, result in patches:
            with self.subTest(verifier=name):
                with patch.object(module, name, return_value=result):
                    document = self.build()
                self.assertEqual(document["source_state"], "UNKNOWN")
                self.assertIn(
                    "SOURCE_CONTRACT_UNVERIFIED",
                    document["blockers"],
                )

    def test_verifier_exception_fails_closed_to_unknown(self) -> None:
        with patch.object(
            adapter_contract,
            "verify_strategy_correlation_cluster_portfolio_risk_adapter_v1",
            side_effect=RuntimeError("synthetic"),
        ):
            document = self.build()
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIn("SOURCE_VERIFIER_ERROR", document["blockers"])

    def test_dual_source_gate_outcome_block_is_not_promoted(self) -> None:
        inputs = deepcopy(self.portfolio_inputs)
        inputs["dual_source_receipt"]["status"] = "BLOCK"
        inputs["dual_source_receipt"][
            "decision"
        ] = "BLOCKED_DUAL_SOURCE_ALIGNMENT"
        document = self.build(portfolio_inputs=inputs)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_adapter_gate_outcome_block_is_not_promoted(self) -> None:
        inputs = deepcopy(self.portfolio_inputs)
        inputs["portfolio_risk_adapter"]["status"] = "BLOCK"
        document = self.build(portfolio_inputs=inputs)
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_legacy_payload_lineage_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["dual_source_receipt"]["legacy_payload"] = deepcopy(
            contexts["dual_source_receipt"]["legacy_payload"]
        )
        contexts["dual_source_receipt"]["legacy_payload"]["matrix_hash"] = (
            "0" * 64
        )
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_cluster_payload_lineage_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["portfolio_risk_adapter"][
            "cluster_correlation_matrix"
        ] = deepcopy(
            contexts["portfolio_risk_adapter"][
                "cluster_correlation_matrix"
            ]
        )
        contexts["portfolio_risk_adapter"][
            "cluster_correlation_matrix"
        ]["matrix_hash"] = "0" * 64
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_binding_native_composition_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["native_cutoff_manifest"]["composition_document"] = (
            deepcopy(
                contexts["native_cutoff_manifest"][
                    "composition_document"
                ]
            )
        )
        contexts["native_cutoff_manifest"]["composition_document"][
            "composition_hash"
        ] = "0" * 64
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_attestation_lineage_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["legacy_matrix_derivation_binding"][
            "dataset_attestation_verification"
        ] = deepcopy(
            contexts["legacy_matrix_derivation_binding"][
                "dataset_attestation_verification"
            ]
        )
        contexts["legacy_matrix_derivation_binding"][
            "dataset_attestation_verification"
        ]["verification_hash"] = "0" * 64
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_cutoff_lineage_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["dual_source_receipt"][
            "expected_observation_cutoff_utc"
        ] = "2026-12-18T00:00:00Z"
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_freshness_native_manifest_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["session_freshness_registration"][
            "native_cutoff_manifest"
        ] = deepcopy(
            contexts["session_freshness_registration"][
                "native_cutoff_manifest"
            ]
        )
        contexts["session_freshness_registration"][
            "native_cutoff_manifest"
        ]["manifest_hash"] = "0" * 64
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_freshness_registration_lineage_drift_is_rejected(self) -> None:
        contexts = deepcopy(self.portfolio_contexts)
        contexts["session_freshness_evaluation"]["registration"] = deepcopy(
            contexts["session_freshness_evaluation"]["registration"]
        )
        contexts["session_freshness_evaluation"]["registration"][
            "registration_hash"
        ] = "0" * 64
        document = self.build(
            portfolio_verification_contexts=contexts
        )
        self.assertEqual(document["source_state"], "UNKNOWN")

    def test_authority_injection_fails_closed_to_unknown(self) -> None:
        inputs = deepcopy(self.portfolio_inputs)
        inputs["portfolio_risk_adapter"]["authority"][
            "current_admission_allowed"
        ] = True
        document = self.build(portfolio_inputs=inputs)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertEqual(document["permission_state"], "DENIED")

    def test_envelope_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.document)
        tampered["permission_state"] = "ALLOWED"
        self.assertFalse(self.verify(tampered))

    def test_coherent_authority_reseal_is_rejected(self) -> None:
        tampered = deepcopy(self.document)
        tampered["authority"]["current_admission_allowed"] = True
        body = {
            key: value
            for key, value in tampered.items()
            if key != "envelope_hash"
        }
        tampered["envelope_hash"] = subject._sha256(body)
        self.assertFalse(self.verify(tampered))

    def test_inputs_and_contexts_are_not_mutated(self) -> None:
        before_v1 = deepcopy(self.readiness_v1)
        before_inputs = deepcopy(self.portfolio_inputs)
        before_v1_context = deepcopy(self.readiness_v1_context)
        before_contexts = deepcopy(self.portfolio_contexts)
        self.build()
        self.assertEqual(self.readiness_v1, before_v1)
        self.assertEqual(self.portfolio_inputs, before_inputs)
        self.assertEqual(self.readiness_v1_context, before_v1_context)
        self.assertEqual(self.portfolio_contexts, before_contexts)

    def test_no_ready_wording_or_execution_dependency_is_exposed(self) -> None:
        serialized = json.dumps(self.document, sort_keys=True).upper()
        self.assertNotIn("READY", serialized)
        functions = (
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2,
            subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2,
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
