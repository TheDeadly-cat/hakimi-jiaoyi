from __future__ import annotations

import json
import re
import sys
import unittest
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.source_baseline_provider_conformance_in_memory_payload_delivery_adapter_v1 import (
    LOAD_DESCRIPTOR_HASH,
    build_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1,
    verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document
from tests import test_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1 as descriptor_tests
from tests import test_source_baseline_provider_conformance_presentation_consumer_registration_v1 as predecessor_tests


class SourceBaselineInMemoryPayloadDeliveryAdapterV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        descriptor = descriptor_tests.SourceBaselineApplicationLoadDescriptorPreregistrationV1Tests(
            methodName="runTest"
        )
        descriptor.setUp()
        self.descriptor = descriptor
        self.envelope = self._envelope()

    def _envelope(self, **overrides: object) -> dict:
        d = self.descriptor
        p2 = d.predecessor
        p1 = p2.predecessor
        values = {
            "load_descriptor_binding_document": d.binding,
            "load_descriptor_document": d.descriptor,
            "style_binding_document": p2.binding,
            "consumer_registration_v2_document": p2.registration,
            "predecessor_consumer_binding_document": p1.binding,
            "predecessor_consumer_registration_document": p1.registration,
            "payload_candidate_document": p1.payload,
            "consumer_preregistration_document": p1.preregistration,
            "source_envelope_document": p1.envelope,
            "conformance_plan_document": p1.plan,
            "provider_identity_binding_document": p1.provider_binding,
            "namespace_preregistration_document": p1.namespace,
            "identity_preregistration_document": p1.identity,
            "organization_identity_intake_document": p1.intake,
            "signer_source_trust_preregistration_document": p1.source_trust,
            **p1.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
            **values
        )

    def _verify(self, document: object) -> bool:
        d = self.descriptor
        p2 = d.predecessor
        p1 = p2.predecessor
        return verify_source_baseline_provider_conformance_in_memory_payload_delivery_envelope_v1(
            document,
            d.binding,
            d.descriptor,
            p2.binding,
            p2.registration,
            p1.binding,
            p1.registration,
            p1.payload,
            p1.preregistration,
            p1.envelope,
            p1.plan,
            p1.provider_binding,
            p1.namespace,
            p1.identity,
            p1.intake,
            p1.source_trust,
            **p1.kwargs,
        )

    def test_exact_chain_builds_blocked_in_memory_envelope(self) -> None:
        self.assertEqual(self.envelope["status"], "BLOCKED")
        self.assertEqual(
            self.envelope["delivery_state"],
            "IN_MEMORY_DOCUMENT_BUILT_ENDPOINT_UNBOUND",
        )

    def test_transport_is_memory_only_and_endpoint_free(self) -> None:
        transport = self.envelope["transport"]
        self.assertEqual(transport["mode"], "IN_MEMORY_JSON_DOCUMENT")
        self.assertEqual(transport["cache_policy"], "NO_STORE")
        self.assertIsNone(transport["endpoint"])
        self.assertIsNone(transport["route"])
        self.assertFalse(transport["wire_bytes_built"])
        self.assertFalse(transport["network_transport_used"])
        self.assertFalse(transport["persistent_storage_used"])

    def test_envelope_embeds_only_exact_bounded_payload_candidate(self) -> None:
        payload = self.descriptor.predecessor.predecessor.payload
        self.assertEqual(self.envelope["payload_candidate"], payload)
        self.assertEqual(
            self.envelope["provenance"]["payload_candidate_hash"],
            payload["payload_candidate_hash"],
        )
        self.assertFalse(self.envelope["facts"]["raw_source_documents_embedded"])
        self.assertFalse(self.envelope["facts"]["raw_identity_material_embedded"])

    def test_envelope_pins_descriptor_and_style_binding_hashes(self) -> None:
        provenance = self.envelope["provenance"]
        self.assertEqual(provenance["load_descriptor_hash"], LOAD_DESCRIPTOR_HASH)
        self.assertEqual(
            provenance["load_descriptor_binding_hash"],
            self.descriptor.binding["load_descriptor_binding_hash"],
        )
        self.assertEqual(
            provenance["style_binding_hash"],
            self.descriptor.predecessor.binding["style_binding_hash"],
        )

    def test_consumer_contract_names_exact_javascript_functions(self) -> None:
        contract = self.envelope["consumer_contract"]
        self.assertEqual(
            contract["javascript_verify_function"],
            "verifyInMemoryPayloadDeliveryEnvelopeV1",
        )
        self.assertEqual(
            contract["javascript_extract_function"],
            "extractPayloadCandidateFromInMemoryEnvelopeV1",
        )
        self.assertEqual(
            contract["javascript_receipt_function"],
            "buildInMemoryPayloadConsumptionReceiptCandidateV1",
        )

    def test_delivery_and_render_facts_remain_false(self) -> None:
        facts = self.envelope["facts"]
        self.assertFalse(facts["delivery_attempted"])
        self.assertFalse(facts["consumer_executed"])
        self.assertFalse(facts["card_render_called"])
        self.assertFalse(facts["dom_accessed"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["ui_mounted"])

    def test_authority_remains_fully_locked(self) -> None:
        authority = self.envelope["authority"]
        self.assertFalse(authority["wire_transport_allowed"])
        self.assertFalse(authority["endpoint_registration_allowed"])
        self.assertFalse(authority["persistent_storage_allowed"])
        self.assertFalse(authority["consumer_execution_allowed"])
        self.assertFalse(authority["card_render_allowed"])
        self.assertFalse(authority["dom_access_allowed"])
        self.assertFalse(authority["browser_execution_allowed"])
        self.assertFalse(authority["ui_consumer_mount_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(self._verify(self.envelope))

    def test_tampered_descriptor_binding_returns_unknown_without_payload(self) -> None:
        tampered = deepcopy(self.descriptor.binding)
        tampered["facts"]["app_binding_present"] = True
        result = self._envelope(load_descriptor_binding_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["payload_candidate"])

    def test_tampered_payload_returns_unknown_without_payload(self) -> None:
        payload = deepcopy(self.descriptor.predecessor.predecessor.payload)
        payload["payload"]["display_tone"] = "POSITIVE"
        result = self._envelope(payload_candidate_document=payload)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["payload_candidate"])

    def test_payload_hash_mismatch_returns_unknown(self) -> None:
        payload = deepcopy(self.descriptor.predecessor.predecessor.payload)
        payload["payload_candidate_hash"] = "f" * 64
        result = self._envelope(payload_candidate_document=payload)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_source_context_drift_returns_unknown(self) -> None:
        p1 = self.descriptor.predecessor.predecessor
        result = self._envelope(
            registry_id=p1.kwargs["registry_id"] + ".forged"
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_descriptor_binding_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._envelope(
            load_descriptor_binding_document=predecessor_tests.SecondReadFlipMapping(
                self.descriptor.binding, "load_descriptor_binding_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["provenance"]["load_descriptor_binding_hash"],
            self.descriptor.binding["load_descriptor_binding_hash"],
        )

    def test_payload_snapshot_blocks_second_read_hash_swap(self) -> None:
        payload = self.descriptor.predecessor.predecessor.payload
        forged = "f" * 64
        result = self._envelope(
            payload_candidate_document=predecessor_tests.SecondReadFlipMapping(
                payload, "payload_candidate_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["provenance"]["payload_candidate_hash"],
            payload["payload_candidate_hash"],
        )

    def test_snapshot_exception_returns_unknown(self) -> None:
        result = self._envelope(
            load_descriptor_binding_document=predecessor_tests.ExplodingMapping()
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "LOAD_DESCRIPTOR_BINDING_SNAPSHOT_FAILED"
        )

    def test_unknown_envelope_has_no_payload_or_verified_facts(self) -> None:
        result = self._envelope(payload_candidate_document=None)
        self.assertIsNone(result["payload_candidate"])
        self.assertFalse(result["facts"]["descriptor_binding_exactly_verified"])
        self.assertFalse(result["facts"]["bounded_payload_embedded"])

    def test_envelope_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.envelope)
        promoted["facts"]["delivery_attempted"] = True
        promoted.pop("delivery_envelope_hash")
        promoted = seal_strict_canonical_document(promoted, "delivery_envelope_hash")
        self.assertFalse(self._verify(promoted))

    def test_envelope_omits_identity_and_promotional_claims(self) -> None:
        serialized = json.dumps(self.envelope, sort_keys=True)
        p1 = self.descriptor.predecessor.predecessor
        self.assertNotIn(p1.kwargs["registry_id"], serialized)
        strings = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)
            elif isinstance(value, str):
                strings.append(value)

        collect(self.envelope)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(strings),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.envelope["facts"]["profitability_proven"])

    def test_inputs_are_not_mutated(self) -> None:
        before_binding = deepcopy(self.descriptor.binding)
        before_payload = deepcopy(self.descriptor.predecessor.predecessor.payload)
        self._envelope()
        self.assertEqual(self.descriptor.binding, before_binding)
        self.assertEqual(self.descriptor.predecessor.predecessor.payload, before_payload)

    def test_envelope_is_deterministic(self) -> None:
        self.assertEqual(self.envelope, self._envelope())


if __name__ == "__main__":
    unittest.main()
