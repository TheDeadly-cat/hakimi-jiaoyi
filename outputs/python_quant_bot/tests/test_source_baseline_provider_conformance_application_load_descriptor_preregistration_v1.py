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

from exchange_terminal.services.source_baseline_provider_conformance_application_load_descriptor_preregistration_v1 import (
    CONSUMER_REGISTRATION_V2_HASH,
    HOST_APP_JS_SHA256,
    HOST_INDEX_HTML_SHA256,
    build_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1,
    build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1,
    verify_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1,
    verify_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document
from tests import test_source_baseline_provider_conformance_presentation_consumer_registration_v1 as predecessor_v1_tests
from tests import test_source_baseline_provider_conformance_presentation_consumer_registration_v2 as predecessor_v2_tests


class SourceBaselineApplicationLoadDescriptorPreregistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        predecessor = predecessor_v2_tests.SourceBaselinePresentationConsumerRegistrationV2Tests(
            methodName="runTest"
        )
        predecessor.setUp()
        self.predecessor = predecessor
        self.descriptor = build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1()
        self.binding = self._binding()

    def _binding(self, **overrides: object) -> dict:
        p2 = self.predecessor
        p1 = p2.predecessor
        values = {
            "load_descriptor_document": self.descriptor,
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
        return build_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
            **values
        )

    def _verify(self, document: object) -> bool:
        p2 = self.predecessor
        p1 = p2.predecessor
        return verify_source_baseline_provider_conformance_application_load_descriptor_binding_candidate_v1(
            document,
            self.descriptor,
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

    def test_descriptor_is_blocked_and_host_unmodified(self) -> None:
        self.assertEqual(self.descriptor["status"], "BLOCKED")
        self.assertEqual(
            self.descriptor["descriptor_state"],
            "HOST_PINNED_LOAD_AND_MOUNT_CHANGES_NOT_APPLIED",
        )
        self.assertFalse(self.descriptor["facts"]["runtime_mutations_performed"])

    def test_descriptor_pins_registration_v2(self) -> None:
        source = self.descriptor["source_contract"]
        self.assertEqual(
            source["consumer_registration_v2_hash"],
            CONSUMER_REGISTRATION_V2_HASH,
        )

    def test_descriptor_pins_current_index_and_app_without_modification(self) -> None:
        host = self.descriptor["host_contract"]
        self.assertEqual(host["index_html"]["observed_sha256"], HOST_INDEX_HTML_SHA256)
        self.assertEqual(host["app_javascript"]["observed_sha256"], HOST_APP_JS_SHA256)
        self.assertFalse(host["index_html"]["modified_by_descriptor"])
        self.assertFalse(host["app_javascript"]["modified_by_descriptor"])

    def test_mount_contract_uses_observed_anchor_and_absent_future_slot(self) -> None:
        mount = self.descriptor["mount_contract"]
        self.assertEqual(mount["host_anchor_id"], "researchDataQualityCards")
        self.assertTrue(mount["host_anchor_observed"])
        self.assertEqual(
            mount["future_slot_id"],
            "sourceBaselineProviderConformanceCardHost",
        )
        self.assertFalse(mount["future_slot_observed"])

    def test_relative_asset_order_is_exact(self) -> None:
        order = self.descriptor["relative_load_order"]
        self.assertTrue(order["relative_subset_only"])
        self.assertTrue(order["existing_unlisted_assets_preserved"])
        self.assertEqual(
            [item["relation"] for item in order["stylesheets"]],
            ["EXISTING_BASE", "AFTER_PROTECTED_STYLESHEET"],
        )
        self.assertEqual(
            [item["relation"] for item in order["scripts"]],
            ["BEFORE_CARD", "AFTER_CANONICAL_BEFORE_APP", "EXISTING_HOST_AFTER_CARD_CANDIDATE"],
        )

    def test_style_preregistration_is_not_a_runtime_asset(self) -> None:
        order = self.descriptor["relative_load_order"]
        self.assertFalse(order["style_preregistration_runtime_load_required"])
        paths = [item["path"] for item in order["scripts"]]
        self.assertNotIn(
            "exchange_terminal/static/evidence_source_baseline_provider_conformance_style_preregistration_v1.js",
            paths,
        )

    def test_payload_delivery_and_endpoint_remain_absent(self) -> None:
        mount = self.descriptor["mount_contract"]
        self.assertIsNone(mount["payload_delivery_adapter"])
        self.assertIsNone(mount["payload_endpoint"])
        self.assertFalse(self.descriptor["facts"]["payload_delivery_adapter_present"])
        self.assertFalse(self.descriptor["facts"]["payload_endpoint_present"])

    def test_blockers_are_exact_and_actionable(self) -> None:
        self.assertEqual(
            self.descriptor["blockers"],
            [
                "HTML_ASSET_TAGS_ABSENT",
                "FUTURE_HOST_SLOT_ABSENT",
                "APP_PAYLOAD_AND_RENDER_BINDING_ABSENT",
                "PAYLOAD_DELIVERY_ADAPTER_NOT_PREREGISTERED",
                "PAYLOAD_ENDPOINT_ABSENT",
                "BROWSER_EXECUTION_NOT_AUTHORIZED",
                "VISUAL_REVIEW_NOT_PERFORMED",
            ],
        )

    def test_descriptor_authority_remains_locked(self) -> None:
        authority = self.descriptor["authority"]
        self.assertFalse(authority["host_asset_write_allowed"])
        self.assertFalse(authority["script_runtime_loading_allowed"])
        self.assertFalse(authority["app_binding_allowed"])
        self.assertFalse(authority["payload_delivery_allowed"])
        self.assertFalse(authority["browser_execution_allowed"])
        self.assertFalse(authority["ui_consumer_mount_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_descriptor_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1(
                self.descriptor
            )
        )

    def test_exact_style_binding_builds_blocked_descriptor_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "LOAD_DESCRIPTOR_AND_STYLE_BINDING_HASH_BOUND_HOST_UNMODIFIED",
        )

    def test_descriptor_binding_records_hashes_only(self) -> None:
        self.assertEqual(
            self.binding["load_descriptor_hash"],
            self.descriptor["load_descriptor_hash"],
        )
        self.assertEqual(
            self.binding["style_binding_hash"],
            self.predecessor.binding["style_binding_hash"],
        )
        self.assertNotIn("payload", self.binding)
        self.assertNotIn("host_document", self.binding)

    def test_descriptor_binding_has_no_identity_or_promotional_copy(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        self.assertNotIn(self.predecessor.predecessor.kwargs["registry_id"], serialized)
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

        collect(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(strings),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_tampered_descriptor_returns_unknown(self) -> None:
        tampered = deepcopy(self.descriptor)
        tampered["facts"]["host_slot_inserted"] = True
        result = self._binding(load_descriptor_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_tampered_style_binding_returns_unknown(self) -> None:
        tampered = deepcopy(self.predecessor.binding)
        tampered["facts"]["stylesheet_runtime_loaded"] = True
        result = self._binding(style_binding_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_source_context_drift_returns_unknown(self) -> None:
        p1 = self.predecessor.predecessor
        result = self._binding(trust_domain=p1.kwargs["trust_domain"] + ".forged")
        self.assertEqual(result["status"], "UNKNOWN")

    def test_descriptor_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            load_descriptor_document=predecessor_v1_tests.SecondReadFlipMapping(
                self.descriptor, "load_descriptor_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["load_descriptor_hash"], self.descriptor["load_descriptor_hash"]
        )

    def test_style_binding_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            style_binding_document=predecessor_v1_tests.SecondReadFlipMapping(
                self.predecessor.binding, "style_binding_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["style_binding_hash"],
            self.predecessor.binding["style_binding_hash"],
        )

    def test_snapshot_exception_returns_unknown(self) -> None:
        result = self._binding(
            load_descriptor_document=predecessor_v1_tests.ExplodingMapping()
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "LOAD_DESCRIPTOR_SNAPSHOT_FAILED")

    def test_descriptor_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(self._verify(self.binding))

    def test_descriptor_binding_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.binding)
        promoted["facts"]["app_binding_present"] = True
        promoted.pop("load_descriptor_binding_hash")
        promoted = seal_strict_canonical_document(
            promoted, "load_descriptor_binding_hash"
        )
        self.assertFalse(self._verify(promoted))

    def test_descriptor_and_binding_are_deterministic_and_inputs_immutable(self) -> None:
        before_descriptor = deepcopy(self.descriptor)
        before_style_binding = deepcopy(self.predecessor.binding)
        self.assertEqual(
            self.descriptor,
            build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1(),
        )
        self.assertEqual(self.binding, self._binding())
        self.assertEqual(self.descriptor, before_descriptor)
        self.assertEqual(self.predecessor.binding, before_style_binding)


if __name__ == "__main__":
    unittest.main()
