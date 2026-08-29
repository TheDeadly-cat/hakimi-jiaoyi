from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2 as v2_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as content_replay_contract,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2 as v2_tests,
)


def _canonical_hash(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.v2_case = (
            v2_tests.StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV2Tests(
                methodName="runTest"
            )
        )
        self.v2_case.setUp()
        self.v2_document = v2_contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
            self.v2_case.v1_document,
            self.v2_case.v1_manifest,
            self.v2_case.manifest,
        )
        self.v2_context = {
            "preregistration_v1": self.v2_case.v1_document,
            "v1_implementation_sha256": self.v2_case.v1_manifest,
            "current_implementation_sha256": self.v2_case.manifest,
        }
        self.manifest = subject.expected_shadow_consumer_implementation_sha256_v3()
        self.document = self.build()

    def build(self, **overrides):
        values = {
            "preregistration_v2": self.v2_document,
            "v2_verification_context": self.v2_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
            **values
        )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "preregistration_v2": self.v2_document,
            "v2_verification_context": self.v2_context,
            "current_implementation_sha256": self.manifest,
        }
        values.update(overrides)
        return subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
            **values
        )

    def test_expected_manifest_matches_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        artifacts = self.document["source"]["artifacts"]
        self.assertEqual(len(artifacts), len(self.manifest))
        for artifact in artifacts:
            with self.subTest(artifact=artifact["artifact_id"]):
                payload = (root / artifact["path"]).read_bytes()
                self.assertEqual(
                    hashlib.sha256(payload).hexdigest(),
                    artifact["expected_sha256"],
                )

    def test_immutable_v2_is_exactly_verified_without_rewrite(self) -> None:
        self.assertEqual(
            self.document["source"]["immutable_v2_preregistration_hash"],
            self.v2_document["preregistration_hash"],
        )
        self.assertEqual(
            self.document["source"]["immutable_v2_schema_version"],
            self.v2_document["schema_version"],
        )
        self.assertTrue(
            self.document["source"]["immutable_v2_exactly_verified"]
        )
        self.assertNotIn(
            "newly_pinned_local_capabilities",
            self.v2_document,
        )

    def test_current_manifest_shape_and_types_are_exact(self) -> None:
        cases = []
        missing = dict(self.manifest)
        missing.pop("shadow_preregistration_v2")
        cases.append(missing)
        extra = {**self.manifest, "unexpected": "0" * 64}
        cases.append(extra)
        alias = dict(self.manifest)
        alias["shadow_preregistration_v2"] = True
        cases.append(alias)
        for manifest in cases:
            with self.subTest(keys=sorted(manifest)):
                with self.assertRaisesRegex(ValueError, "manifest_invalid"):
                    self.build(current_implementation_sha256=manifest)

    def test_current_manifest_hash_drift_fails_closed(self) -> None:
        manifest = dict(self.manifest)
        manifest["dataset_content_issuance_replay_gate_v1"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "manifest_invalid"):
            self.build(current_implementation_sha256=manifest)

    def test_v2_verification_context_shape_is_exact(self) -> None:
        context = {**self.v2_context, "unexpected": {}}
        with self.assertRaisesRegex(ValueError, "manifest_invalid"):
            self.build(v2_verification_context=context)

    def test_v2_manifest_subset_must_match_v3_manifest(self) -> None:
        context = deepcopy(self.v2_context)
        context["current_implementation_sha256"] = dict(
            context["current_implementation_sha256"]
        )
        context["current_implementation_sha256"]["risk_service"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "manifest_invalid"):
            self.build(v2_verification_context=context)

    def test_v2_public_verifier_is_required(self) -> None:
        failed = {
            "schema_version": (
                v2_contract.PREREGISTRATION_VERIFICATION_SCHEMA_VERSION
            ),
            "status": "FAIL",
            "preregistration_exactly_verified": False,
            "preregistration_status": "UNKNOWN",
            "blockers": ["forced"],
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with patch.object(
            v2_contract,
            "verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2",
            return_value=failed,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "v2_verification_invalid",
            ):
                self.build()

    def test_v2_blockers_are_preserved_not_silently_closed(self) -> None:
        for blocker in self.v2_document["blockers"]:
            self.assertIn(blocker, self.document["blockers"])
        self.assertIn(
            "provider_replay_registry_unchecked",
            self.document["blockers"],
        )

    def test_exactly_three_local_blockers_remain_closed(self) -> None:
        self.assertEqual(
            self.document["closed_local_blockers"],
            self.v2_document["closed_local_blockers"],
        )
        self.assertEqual(
            self.document["facts"]["closed_local_blocker_count"],
            3,
        )

    def test_adr0176_is_pinned_but_evidence_is_not_bound(self) -> None:
        capability = self.document["newly_pinned_local_capabilities"][0]
        self.assertTrue(capability["contract_pinned"])
        self.assertFalse(capability["evidence_bound"])
        self.assertFalse(capability["external_authority_verified"])
        self.assertTrue(
            self.document["facts"][
                "local_content_issuance_replay_contract_pinned"
            ]
        )
        self.assertFalse(
            self.document["facts"][
                "content_issuance_replay_evidence_bound"
            ]
        )

    def test_adr0176_schema_family_and_state_are_exactly_pinned(self) -> None:
        pins = self.document["contract_pins"]
        self.assertEqual(
            pins["content_issuance_replay_gate_schema_version"],
            content_replay_contract.SCHEMA_VERSION,
        )
        self.assertEqual(
            pins["content_issuance_replay_verification_state"],
            content_replay_contract.VERIFICATION_STATE,
        )
        self.assertEqual(
            pins["content_issuance_identity_policy"],
            content_replay_contract.CONTENT_IDENTITY_POLICY,
        )

    def test_required_inputs_are_versioned_and_exclude_ui(self) -> None:
        inputs = self.document["required_shadow_input_schemas"]
        names = [entry["input"] for entry in inputs]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(
            all(
                type(entry["schema_version"]) is str
                and entry["schema_version"].endswith("v1")
                for entry in inputs
            )
        )
        self.assertIn(
            "provider_dataset_content_issuance_replay_verification",
            names,
        )
        self.assertFalse(
            any("ui" in name or "projection" in name for name in names)
        )

    def test_replay_blocker_refinement_keeps_source_open(self) -> None:
        refinement = self.document["blocker_refinements"][0]
        self.assertEqual(
            refinement["source_blocker"],
            "provider_replay_registry_unchecked",
        )
        self.assertFalse(refinement["source_blocker_closed"])
        self.assertIn(
            "runtime_consumption_replay_enforcement_missing",
            refinement["remaining_requirements"],
        )

    def test_activation_order_binds_evidence_before_consumer(self) -> None:
        order = self.document["activation_order"]
        self.assertLess(
            order.index(
                "SUPPLY_EXACT_ADR0176_REGISTRATION_CHECKPOINT_PROOFS_AND_AUDIT"
            ),
            order.index("IMPLEMENT_ISOLATED_APPLICATION_SHADOW_CONSUMER_V3"),
        )
        self.assertEqual(
            order[-1],
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        )

    def test_matching_successor_remains_blocked(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertIn(
            "provider_content_issuance_replay_evidence_not_bound",
            self.document["blockers"],
        )
        self.assertIn(
            "current_switch_unauthorized",
            self.document["blockers"],
        )

    def test_external_and_runtime_facts_remain_false(self) -> None:
        facts = self.document["facts"]
        false_keys = (
            "provider_replay_registry_verified",
            "external_content_replay_registry_authority_verified",
            "external_occurrence_auditor_authority_verified",
            "external_provider_key_control_verified",
            "external_provider_data_issuance_verified",
            "durable_content_checkpoint_publication_verified",
            "runtime_consumption_replay_enforcement_verified",
            "future_replay_absence_verified",
            "external_time_authority_authenticated",
            "runtime_consumer_bound",
            "server_route_registered",
            "ui_mounted",
        )
        self.assertTrue(all(facts[key] is False for key in false_keys))

    def test_all_operational_authority_remains_false(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_reuse_plan_does_not_duplicate_provider_stacks(self) -> None:
        decisions = {
            entry["capability"]: entry["decision"]
            for entry in self.document["reuse_plan"]
        }
        self.assertIn("REUSE", decisions["PROVIDER_IDENTITY_AND_KEY_LIFECYCLE"])
        self.assertIn("REUSE", decisions["DATASET_CONTENT_ATTESTATION"])
        self.assertIn("REUSE_ADR0176", decisions["DATASET_CONTENT_ISSUANCE_REPLAY"])
        self.assertFalse(
            self.document["facts"]["provider_identity_stack_duplicated"]
        )
        self.assertFalse(
            self.document["facts"]["dataset_attestation_stack_duplicated"]
        )

    def test_build_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        before_v2 = deepcopy(self.v2_document)
        before_context = deepcopy(self.v2_context)
        before_manifest = dict(self.manifest)
        rebuilt = self.build()
        self.assertEqual(rebuilt, self.document)
        self.assertEqual(self.v2_document, before_v2)
        self.assertEqual(self.v2_context, before_context)
        self.assertEqual(self.manifest, before_manifest)

    def test_exact_verifier_accepts_matching_document(self) -> None:
        verification = self.verify()
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["preregistration_exactly_verified"])
        self.assertEqual(verification["preregistration_status"], "BLOCKED")
        self.assertEqual(verification["blockers"], [])
        self.assertFalse(verification["current_admission_allowed"])
        self.assertFalse(verification["paper_authorized"])
        self.assertFalse(verification["live_order_allowed"])

    def test_coherently_resealed_fact_tamper_is_rejected(self) -> None:
        tampered = deepcopy(self.document)
        tampered["facts"]["provider_replay_registry_verified"] = True
        body = {
            key: value
            for key, value in tampered.items()
            if key != "preregistration_hash"
        }
        tampered["preregistration_hash"] = _canonical_hash(body)
        verification = self.verify(document=tampered)
        self.assertEqual(verification["status"], "FAIL")
        self.assertFalse(verification["preregistration_exactly_verified"])

    def test_v2_document_tamper_fails_closed(self) -> None:
        tampered = deepcopy(self.v2_document)
        tampered["blockers"] = tampered["blockers"][1:]
        with self.assertRaises(ValueError):
            self.build(preregistration_v2=tampered)

    def test_schema_fingerprint_exports_and_api_are_locked(self) -> None:
        self.assertEqual(
            self.document["schema_version"],
            subject.PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.document["static_fingerprint"],
            subject.STATIC_FINGERPRINT,
        )
        functions = (
            subject.expected_shadow_consumer_implementation_sha256_v3,
            subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3,
            subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3,
        )
        for function in functions:
            with self.subTest(function=function.__name__):
                parameters = inspect.signature(function).parameters
                self.assertFalse(
                    any(
                        token in name.lower()
                        for name in parameters
                        for token in (
                            "private",
                            "database",
                            "runtime_store",
                            "cache",
                            "secret",
                        )
                    )
                )


if __name__ == "__main__":
    unittest.main()
