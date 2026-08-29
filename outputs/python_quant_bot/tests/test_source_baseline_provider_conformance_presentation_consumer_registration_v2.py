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

from exchange_terminal.services.source_baseline_provider_conformance_presentation_consumer_registration_v2 import (
    ISOLATED_STYLESHEET_SHA256,
    PREDECESSOR_REGISTRATION_HASH,
    STYLE_PREREGISTRATION_HASH,
    STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
    build_source_baseline_provider_conformance_presentation_consumer_registration_v2,
    build_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2,
    verify_source_baseline_provider_conformance_presentation_consumer_registration_v2,
    verify_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document
from tests.test_source_baseline_provider_conformance_presentation_consumer_registration_v1 import (
    ExplodingMapping,
    SecondReadFlipMapping,
    SourceBaselinePresentationConsumerRegistrationV1Tests,
)


class SourceBaselinePresentationConsumerRegistrationV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        predecessor = SourceBaselinePresentationConsumerRegistrationV1Tests(
            methodName="runTest"
        )
        predecessor.setUp()
        self.predecessor = predecessor
        self.registration = build_source_baseline_provider_conformance_presentation_consumer_registration_v2()
        self.binding = self._binding()

    def _binding(self, **overrides: object) -> dict:
        p = self.predecessor
        values = {
            "consumer_registration_v2_document": self.registration,
            "predecessor_consumer_binding_document": p.binding,
            "predecessor_consumer_registration_document": p.registration,
            "payload_candidate_document": p.payload,
            "consumer_preregistration_document": p.preregistration,
            "source_envelope_document": p.envelope,
            "conformance_plan_document": p.plan,
            "provider_identity_binding_document": p.provider_binding,
            "namespace_preregistration_document": p.namespace,
            "identity_preregistration_document": p.identity,
            "organization_identity_intake_document": p.intake,
            "signer_source_trust_preregistration_document": p.source_trust,
            **p.kwargs,
        }
        values.update(overrides)
        return build_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
            **values
        )

    def _verify(self, document: object) -> bool:
        p = self.predecessor
        return verify_source_baseline_provider_conformance_presentation_consumer_style_binding_candidate_v2(
            document,
            self.registration,
            p.binding,
            p.registration,
            p.payload,
            p.preregistration,
            p.envelope,
            p.plan,
            p.provider_binding,
            p.namespace,
            p.identity,
            p.intake,
            p.source_trust,
            **p.kwargs,
        )

    def test_registration_v2_is_blocked_registered_and_unmounted(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "CARD_AND_ISOLATED_STYLESHEET_REGISTERED_UNMOUNTED",
        )

    def test_registration_v2_pins_predecessor_and_style_contract(self) -> None:
        self.assertEqual(
            self.registration["predecessor_contract"]["consumer_registration_hash"],
            PREDECESSOR_REGISTRATION_HASH,
        )
        self.assertEqual(
            self.registration["style_contract"]["style_preregistration_hash"],
            STYLE_PREREGISTRATION_HASH,
        )
        self.assertEqual(
            self.registration["style_contract"]["implementation_sha256"],
            STYLE_PREREGISTRATION_IMPLEMENTATION_SHA256,
        )

    def test_manifest_registers_isolated_css_but_not_app_or_html(self) -> None:
        manifest = self.registration["asset_manifest"]
        self.assertEqual(
            manifest["isolated_stylesheet"]["sha256"],
            ISOLATED_STYLESHEET_SHA256,
        )
        self.assertIsNone(manifest["app_importer"])
        self.assertIsNone(manifest["html_template"])

    def test_style_contract_is_bounded_and_neutral(self) -> None:
        contract = self.registration["style_contract"]
        self.assertEqual(contract["namespace"], ".sb-conformance-card")
        self.assertEqual(contract["visual_direction"], "COLD_AUDIT_FILM")
        self.assertEqual(contract["palette_color_count"], 6)
        self.assertEqual(contract["typography_role_count"], 3)
        self.assertTrue(contract["motion_mounted_state_only"])

    def test_protected_stylesheet_remains_guard_only(self) -> None:
        guard = self.registration["protected_asset_guard"]
        self.assertFalse(guard["imported"])
        self.assertFalse(guard["modified"])
        self.assertFalse(guard["reuse_authorized"])

    def test_registration_v2_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_source_baseline_provider_conformance_presentation_consumer_registration_v2(
                self.registration
            )
        )

    def test_exact_predecessor_builds_blocked_style_binding(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "PAYLOAD_CARD_AND_ISOLATED_STYLESHEET_HASH_BOUND_UNMOUNTED",
        )

    def test_style_binding_records_hashes_only(self) -> None:
        self.assertEqual(
            self.binding["consumer_registration_v2_hash"],
            self.registration["consumer_registration_hash"],
        )
        self.assertEqual(
            self.binding["predecessor_consumer_binding_hash"],
            self.predecessor.binding["consumer_binding_hash"],
        )
        self.assertEqual(
            self.binding["isolated_stylesheet_sha256"],
            ISOLATED_STYLESHEET_SHA256,
        )
        self.assertNotIn("payload", self.binding)
        self.assertNotIn("style_document", self.binding)

    def test_style_binding_authority_remains_locked(self) -> None:
        authority = self.binding["authority"]
        self.assertFalse(authority["stylesheet_runtime_binding_allowed"])
        self.assertFalse(authority["app_import_allowed"])
        self.assertFalse(authority["html_binding_allowed"])
        self.assertFalse(authority["route_registration_allowed"])
        self.assertFalse(authority["browser_execution_allowed"])
        self.assertFalse(authority["ui_consumer_mount_allowed"])
        self.assertFalse(authority["current_admission_allowed"])
        self.assertFalse(authority["paper_authorized"])
        self.assertFalse(authority["live_order_allowed"])

    def test_style_binding_has_no_identity_or_promotional_copy(self) -> None:
        serialized = json.dumps(self.binding, sort_keys=True)
        self.assertNotIn(self.predecessor.kwargs["registry_id"], serialized)
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

    def test_tampered_registration_v2_returns_unknown(self) -> None:
        tampered = deepcopy(self.registration)
        tampered["facts"]["ui_mounted"] = True
        result = self._binding(consumer_registration_v2_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_tampered_predecessor_binding_returns_unknown(self) -> None:
        tampered = deepcopy(self.predecessor.binding)
        tampered["facts"]["consumer_executed"] = True
        result = self._binding(predecessor_consumer_binding_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_source_context_drift_returns_unknown(self) -> None:
        result = self._binding(
            trust_domain=self.predecessor.kwargs["trust_domain"] + ".forged"
        )
        self.assertEqual(result["status"], "UNKNOWN")

    def test_registration_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            consumer_registration_v2_document=SecondReadFlipMapping(
                self.registration, "consumer_registration_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["consumer_registration_v2_hash"],
            self.registration["consumer_registration_hash"],
        )

    def test_predecessor_snapshot_blocks_second_read_hash_swap(self) -> None:
        forged = "f" * 64
        result = self._binding(
            predecessor_consumer_binding_document=SecondReadFlipMapping(
                self.predecessor.binding, "consumer_binding_hash", forged
            )
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["predecessor_consumer_binding_hash"],
            self.predecessor.binding["consumer_binding_hash"],
        )

    def test_snapshot_exception_returns_unknown(self) -> None:
        result = self._binding(consumer_registration_v2_document=ExplodingMapping())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"], "CONSUMER_REGISTRATION_V2_SNAPSHOT_FAILED"
        )

    def test_style_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(self._verify(self.binding))

    def test_style_binding_promotion_fails_exact_verifier(self) -> None:
        promoted = deepcopy(self.binding)
        promoted["facts"]["stylesheet_runtime_loaded"] = True
        promoted.pop("style_binding_hash")
        promoted = seal_strict_canonical_document(promoted, "style_binding_hash")
        self.assertFalse(self._verify(promoted))

    def test_inputs_are_not_mutated(self) -> None:
        before_registration = deepcopy(self.registration)
        before_predecessor = deepcopy(self.predecessor.binding)
        self._binding()
        self.assertEqual(self.registration, before_registration)
        self.assertEqual(self.predecessor.binding, before_predecessor)

    def test_registration_and_binding_are_deterministic(self) -> None:
        self.assertEqual(
            self.registration,
            build_source_baseline_provider_conformance_presentation_consumer_registration_v2(),
        )
        self.assertEqual(self.binding, self._binding())


if __name__ == "__main__":
    unittest.main()
