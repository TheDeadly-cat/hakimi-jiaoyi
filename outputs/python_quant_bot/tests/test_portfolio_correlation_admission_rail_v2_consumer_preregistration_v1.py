from __future__ import annotations

import copy
import json
import unittest

from exchange_terminal.services.portfolio_correlation_admission_rail_v2_consumer_preregistration_v1 import (
    DELIVERY_ADAPTER_REGISTRATION_HASH,
    RAIL_CSS_NAMESPACE,
    RAIL_IMPLEMENTATION_SHA256,
    STAGE_ORDER,
    TIER_ORDER,
    build_exact_portfolio_correlation_admission_rail_v2_consumer_bundle_v1,
    build_portfolio_correlation_admission_rail_v2_candidate_manifest_v1,
    build_portfolio_correlation_admission_rail_v2_consumer_binding_v1,
    build_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1,
    verify_portfolio_correlation_admission_rail_v2_candidate_manifest_v1,
    verify_portfolio_correlation_admission_rail_v2_consumer_binding_v1,
    verify_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_v2_in_memory_delivery_v1 import (
    seal_strict_canonical_document,
)


class _DictSubclass(dict):
    pass


class PortfolioCorrelationAdmissionRailV2ConsumerPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.bundle = (
            build_exact_portfolio_correlation_admission_rail_v2_consumer_bundle_v1()
        )
        self.registration = self.bundle["consumer_preregistration"]
        self.manifest = self.bundle["candidate_manifest"]
        self.adapter = self.bundle["adapter_registration"]
        self.binding = self.bundle["consumer_binding"]

    @staticmethod
    def _reseal(document: dict, hash_field: str) -> dict:
        return seal_strict_canonical_document(
            copy.deepcopy(document),
            hash_field,
        )

    def _bind(
        self,
        registration: object | None = None,
        manifest: object | None = None,
        adapter: object | None = None,
    ) -> dict:
        return build_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
            self.registration if registration is None else registration,
            self.manifest if manifest is None else manifest,
            self.adapter if adapter is None else adapter,
        )

    def test_registration_is_deterministic_and_fail_closed(self) -> None:
        repeated = (
            build_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1()
        )
        self.assertEqual(self.registration, repeated)
        self.assertTrue(
            verify_portfolio_correlation_admission_rail_v2_consumer_preregistration_v1(
                self.registration
            )
        )
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "PREREGISTERED_UNMOUNTED",
        )
        self.assertFalse(
            self.registration["authority"]["ui_consumer_mount_allowed"]
        )

    def test_candidate_manifest_is_exact_and_hash_only(self) -> None:
        repeated = (
            build_portfolio_correlation_admission_rail_v2_candidate_manifest_v1()
        )
        self.assertEqual(self.manifest, repeated)
        self.assertTrue(
            verify_portfolio_correlation_admission_rail_v2_candidate_manifest_v1(
                self.manifest
            )
        )
        self.assertEqual(
            self.manifest["source_artifacts"]["implementation"]["sha256"],
            RAIL_IMPLEMENTATION_SHA256,
        )
        self.assertTrue(self.manifest["facts"]["hash_only"])
        self.assertFalse(self.manifest["facts"]["source_bytes_embedded"])

    def test_exact_binding_passes_locally_but_remains_blocked(self) -> None:
        self.assertEqual(self.binding["status"], "BLOCKED")
        self.assertEqual(self.binding["binding_state"], "PASS")
        self.assertEqual(
            self.binding["reason_code"],
            "EXACT_HASH_ONLY_RAIL_CANDIDATE_BOUND_UNMOUNTED",
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
                self.binding,
                self.registration,
                self.manifest,
                self.adapter,
            )
        )
        self.assertFalse(self.binding["authority"]["render_allowed"])
        self.assertFalse(
            self.binding["authority"]["current_admission_allowed"]
        )

    def test_binding_contains_hashes_but_not_source_documents(self) -> None:
        self.assertEqual(
            set(self.binding["source"]),
            {
                "consumer_preregistration_hash",
                "candidate_manifest_hash",
                "adapter_registration_hash",
            },
        )
        self.assertEqual(
            self.binding["source"]["adapter_registration_hash"],
            DELIVERY_ADAPTER_REGISTRATION_HASH,
        )
        encoded = json.dumps(self.binding, sort_keys=True)
        self.assertNotIn("source_artifacts", encoded)
        self.assertNotIn("function_exports", encoded)
        self.assertFalse(
            self.binding["facts"]["raw_candidate_manifest_embedded"]
        )
        self.assertFalse(
            self.binding["facts"]["raw_adapter_registration_embedded"]
        )

    def test_malformed_registration_is_unknown(self) -> None:
        binding = self._bind(registration={"schema_version": "forged"})
        self.assertEqual(binding["status"], "UNKNOWN")
        self.assertEqual(binding["binding_state"], "UNKNOWN")
        self.assertEqual(
            binding["reason_code"],
            "CONSUMER_PREREGISTRATION_UNKNOWN",
        )

    def test_resealed_registration_drift_blocks(self) -> None:
        registration = copy.deepcopy(self.registration)
        registration["activation_order"] = list(reversed(
            registration["activation_order"]
        ))
        registration = self._reseal(
            registration,
            "consumer_preregistration_hash",
        )
        binding = self._bind(registration=registration)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(
            binding["reason_code"],
            "CONSUMER_PREREGISTRATION_DRIFT",
        )

    def test_malformed_candidate_manifest_is_unknown(self) -> None:
        binding = self._bind(manifest={"schema_version": "forged"})
        self.assertEqual(binding["status"], "UNKNOWN")
        self.assertEqual(
            binding["reason_code"],
            "CANDIDATE_MANIFEST_UNKNOWN",
        )

    def test_resealed_implementation_hash_drift_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["source_artifacts"]["implementation"]["sha256"] = "0" * 64
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        binding = self._bind(manifest=manifest)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(binding["reason_code"], "CANDIDATE_MANIFEST_DRIFT")

    def test_resealed_css_namespace_drift_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["stylesheet_contract"]["namespace"] = ".forged"
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        binding = self._bind(manifest=manifest)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(
            self.manifest["stylesheet_contract"]["namespace"],
            RAIL_CSS_NAMESPACE,
        )

    def test_resealed_export_order_drift_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["module_contract"]["function_exports"].reverse()
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        self.assertEqual(self._bind(manifest=manifest)["binding_state"], "BLOCK")

    def test_resealed_stage_order_drift_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["module_contract"]["stage_order"].reverse()
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        binding = self._bind(manifest=manifest)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(
            self.manifest["module_contract"]["stage_order"],
            list(STAGE_ORDER),
        )

    def test_resealed_tier_order_drift_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["module_contract"]["tier_order"] = list(
            manifest["module_contract"]["tier_order"][1:]
        )
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        binding = self._bind(manifest=manifest)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(
            self.manifest["module_contract"]["tier_order"],
            list(TIER_ORDER),
        )

    def test_malformed_adapter_registration_is_unknown(self) -> None:
        binding = self._bind(adapter={"schema_version": "forged"})
        self.assertEqual(binding["status"], "UNKNOWN")
        self.assertEqual(
            binding["reason_code"],
            "ADAPTER_REGISTRATION_UNKNOWN",
        )

    def test_resealed_adapter_registration_drift_blocks(self) -> None:
        adapter = copy.deepcopy(self.adapter)
        adapter["host_plan"]["presentation_rail"] = "forged"
        adapter = self._reseal(adapter, "adapter_registration_hash")
        binding = self._bind(adapter=adapter)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertEqual(binding["reason_code"], "ADAPTER_REGISTRATION_DRIFT")

    def test_resealed_extra_manifest_field_blocks(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["unexpected"] = True
        manifest = self._reseal(manifest, "candidate_manifest_hash")
        binding = self._bind(manifest=manifest)
        self.assertEqual(binding["binding_state"], "BLOCK")
        self.assertFalse(binding["facts"]["candidate_manifest_exact"])

    def test_binding_verifier_rejects_tamper_even_when_resealed(self) -> None:
        binding = copy.deepcopy(self.binding)
        binding["authority"]["live_order_allowed"] = True
        binding = self._reseal(binding, "consumer_binding_hash")
        self.assertFalse(
            verify_portfolio_correlation_admission_rail_v2_consumer_binding_v1(
                binding,
                self.registration,
                self.manifest,
                self.adapter,
            )
        )

    def test_cycles_and_container_subclasses_fail_closed(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        cyclic_binding = self._bind(manifest=cyclic)
        self.assertEqual(cyclic_binding["status"], "UNKNOWN")

        subclass_binding = self._bind(
            registration=_DictSubclass(self.registration)
        )
        self.assertEqual(subclass_binding["status"], "UNKNOWN")

    def test_permission_and_claim_locks_are_permanent(self) -> None:
        encoded = json.dumps(self.bundle, sort_keys=True)
        self.assertNotIn("READY", encoded)
        self.assertNotIn("paper_authorized\": true", encoded)
        self.assertNotIn("live_order_allowed\": true", encoded)
        self.assertFalse(self.binding["facts"]["profitability_proven"])
        self.assertFalse(self.binding["facts"]["ui_mounted"])
        self.assertFalse(self.binding["facts"]["current_activated"])


if __name__ == "__main__":
    unittest.main()
