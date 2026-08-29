from __future__ import annotations

import json
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
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_consumer_preregistration_v1 import (
    PAYLOAD_SCHEMA_VERSION,
    SOURCE_ENVELOPE_IMPLEMENTATION_SHA256,
    build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1,
    build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1,
    expected_source_envelope_top_level_fields_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1,
    verify_source_baseline_provider_conformance_presentation_consumer_preregistration_v1,
)
from exchange_terminal.application.source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1 import build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1
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
        raise RuntimeError("synthetic snapshot failure")

    def __len__(self) -> int:
        return 1

    def __getitem__(self, key: str) -> object:
        raise RuntimeError("synthetic snapshot failure")


class SourceBaselinePresentationConsumerPreregistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.kwargs = {
            "registry_id": "synthetic.consumer.registry.v2",
            "operator_identity_claim": "synthetic-consumer-operator-claim",
            "public_key_spki_sha256": sha256(b"synthetic-consumer-registry-spki").hexdigest(),
            "trust_domain": "synthetic.consumer.registry.test",
        }
        self.identity = build_anti_replay_registry_identity_preregistration_v1(**self.kwargs)
        self.intake = build_anti_replay_registry_organization_identity_intake_preregistration_v1(self.identity, **self.kwargs)
        self.source_trust = build_anti_replay_registry_signer_source_trust_preregistration_v1(self.intake, self.identity, **self.kwargs)
        self.namespace = build_source_baseline_nonce_anti_replay_namespace_preregistration_v1()
        self.binding = build_source_baseline_nonce_anti_replay_provider_identity_binding_v2(self.namespace, self.identity, self.intake, self.source_trust, **self.kwargs)
        self.plan = build_source_baseline_nonce_anti_replay_provider_conformance_plan_v2(self.binding, self.namespace, self.identity, self.intake, self.source_trust, **self.kwargs)
        self.envelope = build_source_baseline_nonce_anti_replay_provider_conformance_presentation_envelope_v1(self.plan, self.binding, self.namespace, self.identity, self.intake, self.source_trust, **self.kwargs)
        self.preregistration = build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1()
        self.candidate = self._candidate()

    def _candidate(self, **overrides: object) -> dict:
        values = {
            "consumer_preregistration_document": self.preregistration,
            "source_envelope_document": self.envelope,
            "conformance_plan_document": self.plan,
            "provider_identity_binding_document": self.binding,
            "namespace_preregistration_document": self.namespace,
            "identity_preregistration_document": self.identity,
            "organization_identity_intake_document": self.intake,
            "signer_source_trust_preregistration_document": self.source_trust,
            **self.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(**values)

    def test_preregistration_is_blocked_and_pins_exact_source(self) -> None:
        self.assertEqual(self.preregistration["status"], "BLOCKED")
        self.assertEqual(self.preregistration["source_pin"]["implementation_sha256"], SOURCE_ENVELOPE_IMPLEMENTATION_SHA256)
        self.assertTrue(self.preregistration["facts"]["source_schema_pinned"])

    def test_v9_is_explicitly_incompatible(self) -> None:
        boundary = self.preregistration["existing_consumer_boundary"]
        self.assertFalse(boundary["registration_v9_semantically_compatible"])

    def test_asset_manifest_is_empty_and_unauthorized(self) -> None:
        self.assertTrue(all(value is None for value in self.preregistration["asset_manifest"].values()))
        self.assertFalse(self.preregistration["facts"]["asset_manifest_complete"])
        self.assertFalse(self.preregistration["authority"]["asset_write_allowed"])

    def test_allowed_source_fields_are_exact_and_unique(self) -> None:
        fields = expected_source_envelope_top_level_fields_v1()
        self.assertEqual(len(fields), len(set(fields)))
        self.assertEqual(self.preregistration["consumer_contract"]["allowed_source_top_level_fields"], fields)

    def test_preregistration_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(verify_source_baseline_provider_conformance_presentation_consumer_preregistration_v1(self.preregistration))

    def test_exact_envelope_builds_blocked_payload_candidate(self) -> None:
        self.assertEqual(self.candidate["schema_version"], PAYLOAD_SCHEMA_VERSION)
        self.assertEqual(self.candidate["status"], "BLOCKED")
        self.assertEqual(self.candidate["consumer_status"], "PAYLOAD_BUILT_CONSUMER_UNREGISTERED")

    def test_payload_preserves_four_ordered_neutral_axes(self) -> None:
        payload = self.candidate["payload"]
        self.assertEqual(payload["display_tone"], "NEUTRAL")
        self.assertEqual(payload["ordered_stage_contract"], ["SOURCE", "GAP", "MATURITY", "PERMISSION"])
        self.assertEqual([item["stage"] for item in payload["axes"]], payload["ordered_stage_contract"])

    def test_payload_is_bounded_and_omits_lineage_and_source_documents(self) -> None:
        payload = self.candidate["payload"]
        self.assertNotIn("lineage", payload)
        self.assertNotIn("facts", payload)
        self.assertNotIn("source_documents", payload)
        self.assertFalse(self.candidate["facts"]["source_lineage_details_embedded"])
        self.assertFalse(self.candidate["facts"]["raw_source_documents_embedded"])

    def test_payload_summary_matches_source_counts(self) -> None:
        self.assertEqual(self.candidate["payload"]["summary"], self.envelope["summary"])

    def test_payload_contains_no_identity_ready_or_profitability_claim(self) -> None:
        serialized = json.dumps(self.candidate, sort_keys=True)
        self.assertNotIn(self.kwargs["registry_id"], serialized)
        self.assertNotIn(self.kwargs["operator_identity_claim"], serialized)
        self.assertNotIn(self.kwargs["trust_domain"], serialized)
        self.assertNotIn('"READY"', serialized.upper())
        self.assertFalse(self.candidate["facts"]["profitability_proven"])

    def test_assets_browser_route_ui_and_current_remain_absent(self) -> None:
        facts = self.candidate["facts"]
        self.assertFalse(facts["consumer_implementation_present"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["route_registered"])
        self.assertFalse(facts["ui_mounted"])
        self.assertFalse(facts["current_activated"])

    def test_invalid_envelope_returns_unknown_without_payload(self) -> None:
        tampered = deepcopy(self.envelope)
        tampered["display_tone"] = "POSITIVE"
        result = self._candidate(source_envelope_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["payload"])

    def test_tampered_preregistration_returns_unknown(self) -> None:
        tampered = deepcopy(self.preregistration)
        tampered["facts"]["consumer_implementation_present"] = True
        result = self._candidate(consumer_preregistration_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_preregistration_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged_hash = "f" * 64
        adversarial = SecondReadFlipMapping(
            self.preregistration,
            "consumer_preregistration_hash",
            forged_hash,
        )
        result = self._candidate(consumer_preregistration_document=adversarial)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["consumer_preregistration_hash"],
            self.preregistration["consumer_preregistration_hash"],
        )
        self.assertNotEqual(result["consumer_preregistration_hash"], forged_hash)

    def test_source_snapshot_blocks_second_read_display_swap(self) -> None:
        adversarial = SecondReadFlipMapping(
            self.envelope,
            "display_tone",
            "POSITIVE",
        )
        result = self._candidate(source_envelope_document=adversarial)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["payload"]["display_tone"], "NEUTRAL")

    def test_snapshot_exception_fails_closed_without_payload(self) -> None:
        result = self._candidate(
            consumer_preregistration_document=ExplodingMapping()
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "CONSUMER_PREREGISTRATION_SNAPSHOT_FAILED",
        )
        self.assertIsNone(result["payload"])

    def test_resealed_envelope_mount_promotion_returns_unknown(self) -> None:
        promoted = deepcopy(self.envelope)
        promoted["facts"]["ui_mounted"] = True
        promoted.pop("presentation_envelope_hash")
        promoted = seal_strict_canonical_document(promoted, "presentation_envelope_hash")
        result = self._candidate(source_envelope_document=promoted)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_payload_candidate_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(self.candidate, self.preregistration, self.envelope, self.plan, self.binding, self.namespace, self.identity, self.intake, self.source_trust, **self.kwargs))

    def test_payload_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.candidate)
        promoted["facts"]["ui_mounted"] = True
        promoted.pop("payload_candidate_hash")
        promoted = seal_strict_canonical_document(promoted, "payload_candidate_hash")
        self.assertFalse(verify_source_baseline_provider_conformance_presentation_consumer_payload_candidate_v1(promoted, self.preregistration, self.envelope, self.plan, self.binding, self.namespace, self.identity, self.intake, self.source_trust, **self.kwargs))

    def test_inputs_are_not_mutated(self) -> None:
        names = ("preregistration", "envelope", "plan", "binding", "namespace", "identity", "intake", "source_trust")
        before = {name: deepcopy(getattr(self, name)) for name in names}
        self._candidate()
        self.assertEqual(before, {name: getattr(self, name) for name in names})

    def test_preregistration_and_payload_are_deterministic(self) -> None:
        self.assertEqual(self.preregistration, build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1())
        self.assertEqual(self.candidate, self._candidate())


if __name__ == "__main__":
    unittest.main()
