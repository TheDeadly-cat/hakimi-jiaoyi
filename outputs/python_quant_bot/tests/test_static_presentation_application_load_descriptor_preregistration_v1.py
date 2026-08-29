from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.static_presentation_application_load_descriptor_preregistration_v1 import (
    ADAPTER_REGISTRATION_HASH,
    BINDING_SCHEMA_VERSION,
    SCHEMA_VERSION,
    build_static_presentation_application_load_descriptor_binding_candidate_v1,
    build_static_presentation_application_load_descriptor_preregistration_v1,
    verify_static_presentation_application_load_descriptor_binding_candidate_v1,
    verify_static_presentation_application_load_descriptor_preregistration_v1,
)
from exchange_terminal.services.static_presentation_in_memory_delivery_adapter_registration_v1 import (
    build_static_presentation_in_memory_delivery_adapter_registration_v1,
    verify_static_presentation_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationApplicationLoadDescriptorPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration = (
            build_static_presentation_in_memory_delivery_adapter_registration_v1()
        )
        self.descriptor = (
            build_static_presentation_application_load_descriptor_preregistration_v1()
        )
        self.binding = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                self.descriptor,
                self.registration,
            )
        )

    def _reseal(self, document: dict, hash_key: str) -> dict:
        document.pop(hash_key)
        return seal_strict_canonical_document(document, hash_key)

    def test_descriptor_is_exact_blocked_and_unapplied(self) -> None:
        self.assertEqual(self.descriptor["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.descriptor["status"], "BLOCKED")
        self.assertEqual(
            self.descriptor["descriptor_state"],
            "HOST_AND_RELATIVE_LOAD_GRAPH_PINNED_CHANGES_NOT_APPLIED",
        )
        self.assertTrue(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                self.descriptor
            )
        )

    def test_source_contract_pins_exact_adapter_registration(self) -> None:
        self.assertTrue(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self.registration
            )
        )
        source = self.descriptor["source_contract"]
        self.assertEqual(
            source["adapter_registration_hash"],
            ADAPTER_REGISTRATION_HASH,
        )
        self.assertEqual(
            source["adapter_registration_hash"],
            self.registration["adapter_registration_hash"],
        )

    def test_every_pinned_source_and_host_hash_matches_disk(self) -> None:
        source = self.descriptor["source_contract"]
        host = self.descriptor["host_contract"]
        expected = {
            source["adapter_registration_implementation_path"]: source[
                "adapter_registration_implementation_sha256"
            ],
            source["adapter_registration_test_path"]: source[
                "adapter_registration_test_sha256"
            ],
            source["adr_path"]: source["adr_sha256"],
            host["index_html"]["path"]: host["index_html"]["observed_sha256"],
            host["app_javascript"]["path"]: host["app_javascript"][
                "observed_sha256"
            ],
            host["protected_stylesheet"]["path"]: host[
                "protected_stylesheet"
            ]["observed_sha256"],
        }
        for section in ("stylesheets", "scripts"):
            for row in self.descriptor["relative_load_order"][section]:
                expected[row["path"]] = row["sha256"]
        observed = {
            path: hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_host_files_are_pinned_but_not_modified_by_descriptor(self) -> None:
        host = self.descriptor["host_contract"]
        self.assertFalse(host["index_html"]["modified_by_descriptor"])
        self.assertFalse(host["app_javascript"]["modified_by_descriptor"])
        self.assertFalse(host["protected_stylesheet"]["modified_by_descriptor"])

    def test_anchor_exists_and_future_bindings_are_absent_in_pinned_source(self) -> None:
        index_source = (
            PROJECT_ROOT / "exchange_terminal/static/index.html"
        ).read_text(encoding="utf-8")
        app_source = (
            PROJECT_ROOT / "exchange_terminal/static/app.js"
        ).read_text(encoding="utf-8")
        combined = index_source + "\n" + app_source
        self.assertIn('id="researchDataQualityCards"', index_source)
        self.assertIn('$("researchDataQualityCards")', app_source)
        for token in (
            "portfolioCorrelationAdmissionRailHost",
            "HakimiPortfolioCorrelationAdmissionRailV1",
            "HakimiStaticPresentationInMemoryDeliveryV1",
            "evidence_portfolio_correlation_admission_rail_v1.js",
            "evidence_static_presentation_in_memory_delivery_v1.js",
        ):
            self.assertNotIn(token, combined)

    def test_relative_load_order_hash_is_exact(self) -> None:
        self.assertEqual(
            self.descriptor["relative_load_order_hash"],
            strict_canonical_hash(self.descriptor["relative_load_order"]),
        )

    def test_stylesheet_order_is_exact_and_isolated(self) -> None:
        rows = self.descriptor["relative_load_order"]["stylesheets"]
        self.assertEqual(
            [row["relation"] for row in rows],
            ["EXISTING_BASE", "AFTER_PROTECTED_STYLESHEET"],
        )
        self.assertEqual(rows[0]["state"], "OBSERVED_UNCHANGED")
        self.assertEqual(rows[1]["state"], "PREREGISTERED_NOT_LOADED")

    def test_script_order_is_exact_and_dependency_first(self) -> None:
        rows = self.descriptor["relative_load_order"]["scripts"]
        self.assertEqual(
            [row["relation"] for row in rows],
            [
                "BEFORE_ADMISSION_RAIL",
                "AFTER_CANONICAL_BEFORE_DELIVERY_ADAPTER",
                "AFTER_ADMISSION_RAIL_BEFORE_APP",
                "EXISTING_HOST_AFTER_DELIVERY_CANDIDATE",
            ],
        )
        self.assertEqual(rows[-1]["state"], "OBSERVED_UNCHANGED")

    def test_future_app_flow_is_exact_and_neutral(self) -> None:
        mount = self.descriptor["mount_contract"]
        self.assertEqual(
            mount["future_app_flow"],
            [
                "VERIFY_IN_MEMORY_ENVELOPE",
                "EXTRACT_EXACT_ADMISSION_CANDIDATE",
                "BUILD_NO_DOM_RECEIPT",
                "RENDER_NEUTRAL_ADMISSION_RAIL",
            ],
        )
        self.assertEqual(
            mount["render_function"],
            "renderPortfolioCorrelationAdmissionRailV1",
        )

    def test_endpoint_and_route_are_intentionally_not_required(self) -> None:
        mount = self.descriptor["mount_contract"]
        self.assertIsNone(mount["payload_endpoint"])
        self.assertFalse(mount["endpoint_required"])
        self.assertFalse(mount["new_route_required"])
        self.assertNotIn("PAYLOAD_ENDPOINT_ABSENT", self.descriptor["blockers"])
        self.assertNotIn(
            "PAYLOAD_DELIVERY_ADAPTER_NOT_PREREGISTERED",
            self.descriptor["blockers"],
        )

    def test_planned_mutations_are_complete_and_unperformed(self) -> None:
        rows = self.descriptor["planned_mutations"]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["performed"] is False for row in rows))

    def test_blockers_are_exact_and_actionable(self) -> None:
        self.assertEqual(
            self.descriptor["blockers"],
            [
                "HTML_ASSET_TAG_APPLICATION_UNAUTHORIZED",
                "APP_IN_MEMORY_ENVELOPE_BINDING_ABSENT",
                "FUTURE_HOST_SLOT_ABSENT",
                "UNMOUNTED_RENDER_DESCRIPTOR_UNREVIEWED",
                "BROWSER_EXECUTION_NOT_AUTHORIZED",
                "VISUAL_REVIEW_NOT_PERFORMED",
                "UI_MOUNT_NOT_AUTHORIZED",
                "CURRENT_ADMISSION_LOCKED",
            ],
        )

    def test_descriptor_records_no_runtime_or_host_mutation(self) -> None:
        facts = self.descriptor["facts"]
        self.assertTrue(facts["delivery_adapter_preregistered"])
        self.assertFalse(facts["html_assets_inserted"])
        self.assertFalse(facts["host_slot_inserted"])
        self.assertFalse(facts["app_binding_present"])
        self.assertFalse(facts["adapter_execution_observed"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["ui_mounted"])
        self.assertFalse(facts["runtime_mutations_performed"])

    def test_descriptor_authority_remains_fully_locked(self) -> None:
        self.assertTrue(
            all(value is False for value in self.descriptor["authority"].values())
        )

    def test_exact_inputs_build_hash_only_blocked_binding(self) -> None:
        self.assertEqual(self.binding["schema_version"], BINDING_SCHEMA_VERSION)
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(
            self.binding["binding_state"],
            "LOAD_DESCRIPTOR_AND_ADAPTER_REGISTRATION_HASH_BOUND_HOST_UNMODIFIED",
        )
        self.assertEqual(
            self.binding["load_descriptor_hash"],
            self.descriptor["load_descriptor_hash"],
        )
        self.assertEqual(
            self.binding["adapter_registration_hash"],
            self.registration["adapter_registration_hash"],
        )
        self.assertNotIn("load_descriptor", self.binding)
        self.assertNotIn("adapter_registration", self.binding)

    def test_binding_exact_verifier_accepts_rebuild(self) -> None:
        self.assertTrue(
            verify_static_presentation_application_load_descriptor_binding_candidate_v1(
                self.binding,
                self.descriptor,
                self.registration,
            )
        )

    def test_tampered_descriptor_returns_unknown_binding(self) -> None:
        tampered = copy.deepcopy(self.descriptor)
        tampered["facts"]["app_binding_present"] = True
        result = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                tampered,
                self.registration,
            )
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "LOAD_DESCRIPTOR_NOT_EXACT")

    def test_tampered_registration_returns_unknown_binding(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["facts"]["javascript_adapter_runtime_loaded"] = True
        result = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                self.descriptor,
                tampered,
            )
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason_code"], "ADAPTER_REGISTRATION_NOT_EXACT")

    def test_non_native_and_cyclic_binding_inputs_return_unknown(self) -> None:
        non_native = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                NonNativeMapping(self.descriptor),
                self.registration,
            )
        )
        self.assertEqual(non_native["status"], "UNKNOWN")
        self.assertEqual(
            non_native["reason_code"],
            "LOAD_DESCRIPTOR_SNAPSHOT_FAILED",
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        result = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                self.descriptor,
                cyclic,
            )
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason_code"],
            "ADAPTER_REGISTRATION_SNAPSHOT_FAILED",
        )

    def test_non_native_descriptor_fails_exact_verifier(self) -> None:
        self.assertFalse(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                NonNativeMapping(self.descriptor)
            )
        )

    def test_resealed_descriptor_extra_claim_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.descriptor)
        tampered["hidden_claim"] = True
        tampered = self._reseal(tampered, "load_descriptor_hash")
        self.assertFalse(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                tampered
            )
        )

    def test_resealed_load_order_swap_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.descriptor)
        tampered["relative_load_order"]["scripts"][0]["sha256"] = "f" * 64
        tampered["relative_load_order_hash"] = strict_canonical_hash(
            tampered["relative_load_order"]
        )
        tampered = self._reseal(tampered, "load_descriptor_hash")
        self.assertFalse(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                tampered
            )
        )

    def test_resealed_descriptor_authority_promotion_fails(self) -> None:
        tampered = copy.deepcopy(self.descriptor)
        tampered["authority"]["browser_execution_allowed"] = True
        tampered = self._reseal(tampered, "load_descriptor_hash")
        self.assertFalse(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                tampered
            )
        )

    def test_resealed_binding_promotion_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.binding)
        tampered["facts"]["ui_mounted"] = True
        tampered = self._reseal(tampered, "load_descriptor_binding_hash")
        self.assertFalse(
            verify_static_presentation_application_load_descriptor_binding_candidate_v1(
                tampered,
                self.descriptor,
                self.registration,
            )
        )

    def test_descriptor_and_binding_have_no_promotional_copy(self) -> None:
        values: list[str] = []

        def collect(value: object) -> None:
            if type(value) is dict:
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)
            elif type(value) is str:
                values.append(value)

        collect(self.descriptor)
        collect(self.binding)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.descriptor["facts"]["profitability_proven"])
        self.assertFalse(self.binding["facts"]["profitability_proven"])

    def test_descriptor_and_binding_are_deterministic_native_json(self) -> None:
        rebuilt_descriptor = (
            build_static_presentation_application_load_descriptor_preregistration_v1()
        )
        rebuilt_binding = (
            build_static_presentation_application_load_descriptor_binding_candidate_v1(
                self.descriptor,
                self.registration,
            )
        )
        self.assertEqual(self.descriptor, rebuilt_descriptor)
        self.assertEqual(self.binding, rebuilt_binding)
        self.assertEqual(
            json.loads(json.dumps(self.descriptor, sort_keys=True)),
            self.descriptor,
        )


if __name__ == "__main__":
    unittest.main()
