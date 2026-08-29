from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.application.anti_replay_registry_identity_preregistration_v1 import (
    build_anti_replay_registry_identity_preregistration_v1,
    verify_anti_replay_registry_identity_preregistration_v1,
)
from exchange_terminal.application.anti_replay_registry_organization_identity_intake_preregistration_v1 import (
    build_anti_replay_registry_organization_identity_intake_preregistration_v1,
)
from exchange_terminal.application.anti_replay_registry_signer_source_trust_preregistration_v1 import (
    build_anti_replay_registry_signer_source_trust_preregistration_v1,
    verify_anti_replay_registry_signer_source_trust_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_namespace_preregistration_v1 import (
    build_source_baseline_nonce_anti_replay_namespace_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_plan_v2 import (
    PORT_V2_PROTOCOL_VERSION,
    build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2,
    build_source_baseline_nonce_anti_replay_provider_identity_binding_v2,
    expected_source_baseline_nonce_anti_replay_provider_conformance_cases_v2,
    verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2,
    verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class SourceBaselineNonceAntiReplayProviderConformancePlanV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.kwargs = {
            "registry_id": "synthetic.organization.registry.v2-source",
            "operator_identity_claim": "synthetic-organization-v2-operator-claim",
            "public_key_spki_sha256": sha256(
                b"synthetic-organization-v2-registry-spki"
            ).hexdigest(),
            "trust_domain": "synthetic.organization.v2-source.test",
        }
        self.identity = build_anti_replay_registry_identity_preregistration_v1(
            **self.kwargs
        )
        self.intake = (
            build_anti_replay_registry_organization_identity_intake_preregistration_v1(
                self.identity, **self.kwargs
            )
        )
        self.source_trust = (
            build_anti_replay_registry_signer_source_trust_preregistration_v1(
                self.intake, self.identity, **self.kwargs
            )
        )
        self.namespace = (
            build_source_baseline_nonce_anti_replay_namespace_preregistration_v1()
        )
        self.binding = self._binding()
        self.plan = self._plan()

    def _binding(self, **overrides: object) -> dict:
        values = {
            "namespace_preregistration_document": self.namespace,
            "identity_preregistration_document": self.identity,
            "organization_identity_intake_document": self.intake,
            "signer_source_trust_preregistration_document": self.source_trust,
            **self.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
            **values
        )

    def _plan(self, **overrides: object) -> dict:
        values = {
            "provider_identity_binding_document": self.binding,
            "namespace_preregistration_document": self.namespace,
            "identity_preregistration_document": self.identity,
            "organization_identity_intake_document": self.intake,
            "signer_source_trust_preregistration_document": self.source_trust,
            **self.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
            **values
        )

    def test_upstream_exact_pass_does_not_promote_identity_or_trust(self) -> None:
        identity_verification = verify_anti_replay_registry_identity_preregistration_v1(
            self.identity, **self.kwargs
        )
        trust_verification = verify_anti_replay_registry_signer_source_trust_preregistration_v1(
            self.source_trust, self.intake, self.identity, **self.kwargs
        )
        self.assertEqual(identity_verification["status"], "PASS")
        self.assertFalse(identity_verification["registry_identity_verified"])
        self.assertEqual(trust_verification["status"], "PASS")
        self.assertFalse(trust_verification["external_source_trust_verified"])

    def test_binding_is_blocked_claim_bound_and_unauthenticated(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_status"], "CLAIM_BOUND_UNAUTHENTICATED"
        )
        self.assertFalse(self.binding["facts"]["registry_identity_verified"])
        self.assertFalse(self.binding["facts"]["provider_conformance_verified"])

    def test_binding_explicitly_separates_v1_source_and_v2_target(self) -> None:
        protocol = self.binding["protocol_binding"]
        self.assertEqual(
            protocol["source_adapter_protocol_version"],
            "anti-replay-compare-and-consume-port-v1",
        )
        self.assertEqual(
            protocol["target_adapter_protocol_version"], PORT_V2_PROTOCOL_VERSION
        )
        self.assertFalse(self.binding["facts"]["v1_conformance_plan_applies_to_v2"])

    def test_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
                self.binding,
                self.namespace,
                self.identity,
                self.intake,
                self.source_trust,
                **self.kwargs,
            )
        )

    def test_namespace_substitution_returns_unknown_binding(self) -> None:
        tampered = deepcopy(self.namespace)
        tampered["namespace_contract"]["anti_replay_namespace"] = "alias-v2"
        result = self._binding(namespace_preregistration_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_identity_substitution_returns_unknown_binding(self) -> None:
        tampered = deepcopy(self.identity)
        tampered["identity"]["registry_id"] = "replacement"
        result = self._binding(identity_preregistration_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_source_trust_substitution_returns_unknown_binding(self) -> None:
        tampered = deepcopy(self.source_trust)
        tampered["status"] = "PASS"
        result = self._binding(
            signer_source_trust_preregistration_document=tampered
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_binding_redacts_raw_claims_and_private_material(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        self.assertNotIn(self.kwargs["registry_id"], serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertNotIn(self.kwargs["trust_domain"], serialized)
        self.assertFalse(self.binding["facts"]["raw_operator_claim_embedded"])
        self.assertFalse(self.binding["facts"]["private_key_embedded"])

    def test_plan_preregisters_fourteen_cases_without_execution(self) -> None:
        self.assertEqual(self.plan["status"], "BLOCKED")
        self.assertEqual(self.plan["plan_status"], "PREREGISTERED_NOT_RUN")
        self.assertEqual(len(self.plan["cases"]), 14)
        self.assertEqual(self.plan["facts"]["executed_case_count"], 0)
        self.assertEqual(self.plan["facts"]["passed_case_count"], 0)

    def test_cases_are_unique_required_and_not_run(self) -> None:
        cases = expected_source_baseline_nonce_anti_replay_provider_conformance_cases_v2()
        ids = [item["case_id"] for item in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(
            all(
                item["required"]
                and item["execution_status"] == "NOT_RUN"
                and item["evidence_hash"] is None
                for item in cases
            )
        )

    def test_plan_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
                self.plan,
                self.binding,
                self.namespace,
                self.identity,
                self.intake,
                self.source_trust,
                **self.kwargs,
            )
        )

    def test_resealed_binding_promotion_returns_unknown_plan(self) -> None:
        promoted = deepcopy(self.binding)
        promoted["facts"]["registry_identity_verified"] = True
        promoted.pop("provider_identity_binding_hash")
        promoted = seal_strict_canonical_document(
            promoted, "provider_identity_binding_hash"
        )
        result = self._plan(provider_identity_binding_document=promoted)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["cases"], [])

    def test_resealed_plan_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.plan)
        promoted["facts"]["provider_conformance_verified"] = True
        promoted.pop("conformance_plan_hash")
        promoted = seal_strict_canonical_document(promoted, "conformance_plan_hash")
        self.assertFalse(
            verify_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
                promoted,
                self.binding,
                self.namespace,
                self.identity,
                self.intake,
                self.source_trust,
                **self.kwargs,
            )
        )

    def test_plan_contains_no_endpoint_credentials_or_provider_call(self) -> None:
        serialized = json.dumps(self.plan, sort_keys=True)
        self.assertNotIn("http://", serialized)
        self.assertNotIn("https://", serialized)
        self.assertFalse(self.plan["facts"]["provider_endpoint_embedded"])
        self.assertFalse(self.plan["facts"]["provider_credentials_embedded"])
        self.assertFalse(self.plan["facts"]["provider_called"])
        self.assertFalse(self.plan["facts"]["network_accessed"])

    def test_all_authority_locks_remain_false(self) -> None:
        for document in (self.binding, self.plan):
            for field in (
                "provider_call_allowed",
                "writer_allowed",
                "runtime_gate_activation_allowed",
                "route_registration_allowed",
                "ui_consumer_mount_allowed",
                "current_admission_allowed",
                "paper_authorized",
                "live_order_allowed",
            ):
                self.assertFalse(document["authority"][field], field)

    def test_binding_and_plan_are_deterministic(self) -> None:
        self.assertEqual(self.binding, self._binding())
        self.assertEqual(self.plan, self._plan())


if __name__ == "__main__":
    unittest.main()
