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

from exchange_terminal.services.source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1 import (
    JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
    PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
    build_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1,
    build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1,
    verify_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1,
    verify_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document
from tests import test_source_baseline_provider_conformance_in_memory_payload_delivery_adapter_v1 as adapter_tests
from tests import test_source_baseline_provider_conformance_presentation_consumer_registration_v1 as predecessor_tests


class SourceBaselineInMemoryDeliveryAdapterRegistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        adapter = adapter_tests.SourceBaselineInMemoryPayloadDeliveryAdapterV1Tests(
            methodName="runTest"
        )
        adapter.setUp()
        self.adapter = adapter
        self.registration = build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1()
        self.binding = self._binding()

    def _binding(self, **overrides: object) -> dict:
        a = self.adapter
        d = a.descriptor
        p2 = d.predecessor
        p1 = p2.predecessor
        values = {
            "adapter_registration_document": self.registration,
            "delivery_envelope_document": a.envelope,
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
        return build_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1(
            **values
        )

    def _verify(self, document: object) -> bool:
        a = self.adapter
        d = a.descriptor
        p2 = d.predecessor
        p1 = p2.predecessor
        return verify_source_baseline_provider_conformance_in_memory_delivery_adapter_binding_candidate_v1(
            document,
            self.registration,
            a.envelope,
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

    def test_registration_is_blocked_and_unbound(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "PYTHON_AND_JAVASCRIPT_ADAPTERS_REGISTERED_UNBOUND",
        )

    def test_registration_pins_python_and_javascript_implementations(self) -> None:
        self.assertEqual(
            self.registration["python_contract"]["implementation_sha256"],
            PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            self.registration["javascript_contract"]["implementation_sha256"],
            JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        )

    def test_javascript_exports_and_load_order_are_exact(self) -> None:
        contract = self.registration["javascript_contract"]
        self.assertEqual(len(contract["exports"]), 4)
        self.assertEqual(
            contract["relative_load_order"],
            [
                "strict_canonical_json_v1.js",
                "evidence_source_baseline_provider_conformance_card_v1.js",
                "evidence_source_baseline_provider_conformance_in_memory_delivery_adapter_v1.js",
            ],
        )

    def test_host_plan_remains_empty(self) -> None:
        self.assertTrue(all(value is None for value in self.registration["host_plan"].values()))

    def test_registration_records_no_runtime_execution(self) -> None:
        facts = self.registration["facts"]
        self.assertFalse(facts["python_adapter_invoked_by_registration"])
        self.assertFalse(facts["javascript_adapter_runtime_loaded"])
        self.assertFalse(facts["consumer_executed"])
        self.assertFalse(facts["dom_accessed"])
        self.assertFalse(facts["browser_executed"])

    def test_registration_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1(
                self.registration
            )
        )

    def test_exact_envelope_builds_blocked_adapter_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "REGISTERED_ADAPTERS_AND_EXACT_ENVELOPE_HASH_BOUND_EXECUTION_UNAUTHORIZED",
        )

    def test_binding_records_hashes_only(self) -> None:
        self.assertEqual(
            self.binding["adapter_registration_hash"],
            self.registration["adapter_registration_hash"],
        )
        self.assertEqual(
            self.binding["delivery_envelope_hash"],
            self.adapter.envelope["delivery_envelope_hash"],
        )
        self.assertNotIn("delivery_envelope", self.binding)
        self.assertNotIn("payload", self.binding)

    def test_binding_authority_remains_fully_locked(self) -> None:
        authority = self.binding["authority"]
        self.assertFalse(authority["payload_source_registration_allowed"])
        self.assertFalse(authority["endpoint_registration_allowed"])
        self.assertFalse(authority["route_registration_allowed"])
        self.assertFalse(authority["host_asset_write_allowed"])
        self.assertFalse(authority["adapter_execution_allowed"])
        self.assertFalse(authority["card_render_allowed"])
        self.assertFalse(authority["dom_access_allowed"])
        self.assertFalse(authority["browser_execution_allowed"])
        self.assertFalse(authority["ui_consumer_mount_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_binding_has_no_identity_or_promotional_copy(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        p1 = self.adapter.descriptor.predecessor.predecessor
        self.assertNotIn(p1.kwargs["registry_id"], serialized)
        values = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)
            elif isinstance(value, str):
                values.append(value)

        collect(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_tampered_registration_returns_unknown(self) -> None:
        tampered = deepcopy(self.registration)
        tampered["facts"]["javascript_adapter_runtime_loaded"] = True
        result = self._binding(adapter_registration_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_tampered_envelope_returns_unknown(self) -> None:
        tampered = deepcopy(self.adapter.envelope)
        tampered["facts"]["delivery_attempted"] = True
        result = self._binding(delivery_envelope_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_source_context_drift_returns_unknown(self) -> None:
        p1 = self.adapter.descriptor.predecessor.predecessor
        result = self._binding(
            operator_identity_claim=p1.kwargs["operator_identity_claim"] + "-forged"
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_registration_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            adapter_registration_document=predecessor_tests.SecondReadFlipMapping(
                self.registration, "adapter_registration_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["adapter_registration_hash"],
            self.registration["adapter_registration_hash"],
        )

    def test_envelope_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            delivery_envelope_document=predecessor_tests.SecondReadFlipMapping(
                self.adapter.envelope, "delivery_envelope_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["delivery_envelope_hash"],
            self.adapter.envelope["delivery_envelope_hash"],
        )

    def test_snapshot_exception_returns_unknown(self) -> None:
        result = self._binding(
            adapter_registration_document=predecessor_tests.ExplodingMapping()
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "ADAPTER_REGISTRATION_SNAPSHOT_FAILED")

    def test_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(self._verify(self.binding))

    def test_binding_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.binding)
        promoted["facts"]["adapter_execution_observed"] = True
        promoted.pop("adapter_binding_hash")
        promoted = seal_strict_canonical_document(promoted, "adapter_binding_hash")
        self.assertFalse(self._verify(promoted))

    def test_inputs_are_not_mutated(self) -> None:
        before_registration = deepcopy(self.registration)
        before_envelope = deepcopy(self.adapter.envelope)
        self._binding()
        self.assertEqual(self.registration, before_registration)
        self.assertEqual(self.adapter.envelope, before_envelope)

    def test_registration_and_binding_are_deterministic(self) -> None:
        self.assertEqual(
            self.registration,
            build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1(),
        )
        self.assertEqual(self.binding, self._binding())


if __name__ == "__main__":
    unittest.main()
