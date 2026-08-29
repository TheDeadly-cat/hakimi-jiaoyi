from __future__ import annotations

import json
import re
import sys
import unittest
from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.application.anti_replay_registry_identity_preregistration_v1 import build_anti_replay_registry_identity_preregistration_v1
from exchange_terminal.application.anti_replay_registry_organization_identity_intake_preregistration_v1 import build_anti_replay_registry_organization_identity_intake_preregistration_v1
from exchange_terminal.application.anti_replay_registry_signer_source_trust_preregistration_v1 import build_anti_replay_registry_signer_source_trust_preregistration_v1
from exchange_terminal.application.source_baseline_nonce_anti_replay_namespace_preregistration_v1 import build_source_baseline_nonce_anti_replay_namespace_preregistration_v1
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_plan_v2 import build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2, build_source_baseline_nonce_anti_replay_provider_identity_binding_v2
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_consumer_preregistration_v1 import build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1, build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1 import build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1
from exchange_terminal.services.source_baseline_provider_conformance_presentation_consumer_registration_v1 import (
    CARD_IMPLEMENTATION_SHA256,
    CONSUMER_PREREGISTRATION_HASH,
    STRICT_CANONICAL_JS_SHA256,
    build_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1,
    build_source_baseline_provider_conformance_presentation_consumer_registration_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document


class SecondReadFlipMapping(Mapping):
    def __init__(self, source: Mapping, target: str, forged: object) -> None:
        self._source = source
        self._target = target
        self._forged = forged
        self._reads = 0

    def __iter__(self):
        return iter(self._source)

    def __len__(self) -> int:
        return len(self._source)

    def __getitem__(self, key: str) -> object:
        if key == self._target:
            self._reads += 1
            if self._reads >= 2:
                return self._forged
        return self._source[key]


class ExplodingMapping(Mapping):
    def __iter__(self):
        raise RuntimeError("synthetic registration snapshot failure")

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        raise RuntimeError("synthetic registration snapshot failure")


class SourceBaselinePresentationConsumerRegistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.kwargs = {
            "registry_id": "synthetic.registration.registry.v2",
            "operator_identity_claim": "synthetic-registration-operator-claim",
            "public_key_spki_sha256": sha256(
                b"synthetic-registration-registry-spki"
            ).hexdigest(),
            "trust_domain": "synthetic.registration.registry.test",
        }
        self.identity = build_anti_replay_registry_identity_preregistration_v1(
            **self.kwargs
        )
        self.intake = build_anti_replay_registry_organization_identity_intake_preregistration_v1(
            self.identity, **self.kwargs
        )
        self.source_trust = build_anti_replay_registry_signer_source_trust_preregistration_v1(
            self.intake, self.identity, **self.kwargs
        )
        self.namespace = build_source_baseline_nonce_anti_replay_namespace_preregistration_v1()
        self.provider_binding = build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.plan = build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(
            self.provider_binding,
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.envelope = build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(
            self.plan,
            self.provider_binding,
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.preregistration = build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1()
        self.payload = build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(
            self.preregistration,
            self.envelope,
            self.plan,
            self.provider_binding,
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )
        self.registration = build_source_baseline_provider_conformance_presentation_consumer_registration_v1()
        self.binding = self._binding()

    def _binding(self, **overrides: object) -> dict:
        values = {
            "consumer_registration_document": self.registration,
            "payload_candidate_document": self.payload,
            "consumer_preregistration_document": self.preregistration,
            "source_envelope_document": self.envelope,
            "conformance_plan_document": self.plan,
            "provider_identity_binding_document": self.provider_binding,
            "namespace_preregistration_document": self.namespace,
            "identity_preregistration_document": self.identity,
            "organization_identity_intake_document": self.intake,
            "signer_source_trust_preregistration_document": self.source_trust,
            **self.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
            **values
        )

    def _verify_binding(self, document: object) -> bool:
        return verify_source_baseline_provider_conformance_presentation_consumer_binding_candidate_v1(
            document,
            self.registration,
            self.payload,
            self.preregistration,
            self.envelope,
            self.plan,
            self.provider_binding,
            self.namespace,
            self.identity,
            self.intake,
            self.source_trust,
            **self.kwargs,
        )

    def test_registration_is_blocked_registered_and_unmounted(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "ASSET_MANIFEST_REGISTERED_UNMOUNTED",
        )
        self.assertFalse(self.registration["facts"]["ui_mounted"])

    def test_registration_pins_producer_card_and_canonical_assets(self) -> None:
        source = self.registration["source_contract"]
        manifest = self.registration["asset_manifest"]
        self.assertEqual(source["consumer_preregistration_hash"], CONSUMER_PREREGISTRATION_HASH)
        self.assertEqual(manifest["card_javascript"]["sha256"], CARD_IMPLEMENTATION_SHA256)
        self.assertEqual(manifest["strict_canonical_javascript"]["sha256"], STRICT_CANONICAL_JS_SHA256)

    def test_manifest_load_order_is_exact_and_unbound_assets_are_null(self) -> None:
        self.assertEqual(
            self.registration["consumer_contract"]["load_order"],
            [
                "strict_canonical_json_v1.js",
                "evidence_source_baseline_provider_conformance_card_v1.js",
            ],
        )
        manifest = self.registration["asset_manifest"]
        self.assertIsNone(manifest["stylesheet"])
        self.assertIsNone(manifest["app_importer"])
        self.assertIsNone(manifest["html_template"])

    def test_protected_stylesheet_is_observed_but_not_authorized(self) -> None:
        guard = self.registration["protected_asset_guard"]
        self.assertFalse(guard["bound_to_consumer"])
        self.assertFalse(guard["reuse_authorized"])
        self.assertFalse(guard["modification_authorized"])

    def test_exported_api_and_stage_order_are_exact(self) -> None:
        contract = self.registration["consumer_contract"]
        self.assertEqual(
            contract["exported_functions"],
            [
                "verifySourceBaselineProviderConformancePayloadCandidateV1",
                "buildSourceBaselineProviderConformanceViewModelV1",
                "renderSourceBaselineProviderConformanceCardV1",
            ],
        )
        self.assertEqual(
            contract["ordered_stage_contract"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )

    def test_registration_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_provider_conformance_presentation_consumer_registration_v1(
                self.registration
            )
        )

    def test_exact_payload_builds_blocked_unmounted_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "PAYLOAD_AND_CARD_HASH_BOUND_UNMOUNTED",
        )

    def test_binding_contains_hashes_only(self) -> None:
        self.assertEqual(
            self.binding["consumer_registration_hash"],
            self.registration["consumer_registration_hash"],
        )
        self.assertEqual(
            self.binding["payload_candidate_hash"],
            self.payload["payload_candidate_hash"],
        )
        self.assertNotIn("payload", self.binding)
        self.assertFalse(self.binding["facts"]["raw_payload_embedded"])

    def test_binding_authority_remains_fully_locked(self) -> None:
        authority = self.binding["authority"]
        self.assertFalse(authority["consumer_execution_allowed"])
        self.assertFalse(authority["stylesheet_binding_allowed"])
        self.assertFalse(authority["route_registration_allowed"])
        self.assertFalse(authority["ui_consumer_mount_allowed"])
        self.assertFalse(authority["current_admission_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_binding_omits_raw_identity_and_promotional_claims(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        self.assertNotIn(self.kwargs["registry_id"], serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        string_values: list[str] = []

        def collect_strings(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect_strings(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_strings(nested)
            elif isinstance(value, str):
                string_values.append(value)

        collect_strings(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(string_values),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_tampered_registration_returns_unknown(self) -> None:
        tampered = deepcopy(self.registration)
        tampered["facts"]["ui_mounted"] = True
        result = self._binding(consumer_registration_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_tampered_payload_returns_unknown(self) -> None:
        tampered = deepcopy(self.payload)
        tampered["payload"]["display_tone"] = "POSITIVE"
        result = self._binding(payload_candidate_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_identity_context_drift_returns_unknown(self) -> None:
        result = self._binding(
            operator_identity_claim=self.kwargs["operator_identity_claim"] + "-forged"
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_registration_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            consumer_registration_document=SecondReadFlipMapping(
                self.registration, "consumer_registration_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["consumer_registration_hash"],
            self.registration["consumer_registration_hash"],
        )

    def test_payload_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            payload_candidate_document=SecondReadFlipMapping(
                self.payload, "payload_candidate_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["payload_candidate_hash"],
            self.payload["payload_candidate_hash"],
        )

    def test_snapshot_exception_returns_unknown(self) -> None:
        result = self._binding(consumer_registration_document=ExplodingMapping())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "CONSUMER_REGISTRATION_SNAPSHOT_FAILED"
        )

    def test_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(self._verify_binding(self.binding))

    def test_binding_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.binding)
        promoted["facts"]["ui_mounted"] = True
        promoted.pop("consumer_binding_hash")
        promoted = seal_strict_canonical_document(
            promoted, "consumer_binding_hash"
        )
        self.assertFalse(self._verify_binding(promoted))

    def test_inputs_are_not_mutated(self) -> None:
        names = (
            "registration",
            "payload",
            "preregistration",
            "envelope",
            "plan",
            "provider_binding",
            "namespace",
            "identity",
            "intake",
            "source_trust",
        )
        before = {name: deepcopy(getattr(self, name)) for name in names}
        self._binding()
        self.assertEqual(before, {name: getattr(self, name) for name in names})

    def test_registration_and_binding_are_deterministic(self) -> None:
        self.assertEqual(
            self.registration,
            build_source_baseline_provider_conformance_presentation_consumer_registration_v1(),
        )
        self.assertEqual(self.binding, self._binding())


if __name__ == "__main__":
    unittest.main()
