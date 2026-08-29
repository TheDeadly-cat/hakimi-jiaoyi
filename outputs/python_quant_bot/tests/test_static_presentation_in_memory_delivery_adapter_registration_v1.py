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

from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    build_portfolio_correlation_admission_rail_asset_registration_v1,
    verify_portfolio_correlation_admission_rail_asset_registration_v1,
)
from exchange_terminal.services.static_presentation_in_memory_delivery_adapter_registration_v1 import (
    BASE_ASSET_REGISTRATION_HASH,
    JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
    JAVASCRIPT_ADAPTER_TEST_SHA256,
    PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
    PYTHON_ADAPTER_TEST_SHA256,
    REGISTRATION_ID,
    SCHEMA_VERSION,
    build_static_presentation_in_memory_delivery_adapter_registration_v1,
    verify_static_presentation_in_memory_delivery_adapter_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationInMemoryDeliveryAdapterRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration = (
            build_static_presentation_in_memory_delivery_adapter_registration_v1()
        )

    def _reseal(self, document: dict) -> dict:
        document.pop("adapter_registration_hash")
        return seal_strict_canonical_document(
            document,
            "adapter_registration_hash",
        )

    def test_registration_is_exact_blocked_and_unbound(self) -> None:
        self.assertEqual(self.registration["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.registration["registration_id"], REGISTRATION_ID)
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "DUAL_RUNTIME_DELIVERY_ADAPTER_ASSETS_REGISTERED_UNBOUND",
        )
        self.assertTrue(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self.registration
            )
        )

    def test_predecessor_registration_is_exact_and_hash_bound(self) -> None:
        predecessor = (
            build_portfolio_correlation_admission_rail_asset_registration_v1()
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_rail_asset_registration_v1(
                predecessor
            )
        )
        self.assertEqual(
            predecessor["registration_hash"],
            BASE_ASSET_REGISTRATION_HASH,
        )
        self.assertEqual(
            self.registration["predecessor_contract"]["registration_hash"],
            predecessor["registration_hash"],
        )

    def test_every_direct_and_predecessor_contract_hash_matches_disk(self) -> None:
        expected = {
            row["path"]: row["sha256"]
            for row in self.registration["asset_manifest"]
        }
        predecessor = self.registration["predecessor_contract"]
        expected.update({
            predecessor["implementation_path"]: predecessor[
                "implementation_sha256"
            ],
            predecessor["test_path"]: predecessor["test_sha256"],
            predecessor["adr_path"]: predecessor["adr_sha256"],
            self.registration["presentation_contract"][
                "protected_stylesheet_path"
            ]: self.registration["presentation_contract"][
                "protected_stylesheet_sha256"
            ],
        })
        observed = {
            path: hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_direct_asset_manifest_is_unique_sorted_and_complete(self) -> None:
        manifest = self.registration["asset_manifest"]
        ids = [row["asset_id"] for row in manifest]
        paths = [row["path"] for row in manifest]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(len(manifest), 5)

    def test_corrected_python_and_javascript_hashes_are_pinned(self) -> None:
        by_id = {
            row["asset_id"]: row["sha256"]
            for row in self.registration["asset_manifest"]
        }
        self.assertEqual(
            by_id["delivery_python_adapter"],
            PYTHON_ADAPTER_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            by_id["delivery_python_test"],
            PYTHON_ADAPTER_TEST_SHA256,
        )
        self.assertEqual(
            by_id["delivery_javascript_adapter"],
            JAVASCRIPT_ADAPTER_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(
            by_id["delivery_javascript_test"],
            JAVASCRIPT_ADAPTER_TEST_SHA256,
        )

    def test_python_contract_exports_are_exact(self) -> None:
        self.assertEqual(
            self.registration["python_contract"]["exports"],
            [
                "CONSUMER_SCHEMA_VERSION",
                "REGISTRATION_HASH",
                "SCHEMA_VERSION",
                "STATIC_FINGERPRINT",
                "build_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
                "verify_portfolio_correlation_admission_rail_in_memory_delivery_envelope_v1",
            ],
        )

    def test_javascript_exports_and_load_order_are_exact(self) -> None:
        contract = self.registration["javascript_contract"]
        self.assertEqual(len(contract["exports"]), 9)
        self.assertEqual(
            contract["relative_load_order"],
            [
                "strict_canonical_json_v1.js",
                "evidence_portfolio_correlation_admission_rail_v1.js",
                "evidence_static_presentation_in_memory_delivery_v1.js",
            ],
        )

    def test_transport_and_host_plan_remain_in_memory_and_unbound(self) -> None:
        transport = self.registration["transport_contract"]
        self.assertEqual(transport["mode"], "IN_MEMORY_ARGUMENT_ONLY")
        self.assertIsNone(transport["endpoint"])
        self.assertIsNone(transport["route"])
        self.assertIsNone(transport["host_slot"])
        self.assertTrue(
            all(value is None for value in self.registration["host_plan"].values())
        )

    def test_activation_order_removes_only_the_closed_delivery_gap(self) -> None:
        order = self.registration["activation_order"]
        self.assertLess(
            order.index("DELIVERY_ADAPTER_ASSET_REGISTRATION"),
            order.index("APP_IMPORT_PREREGISTRATION"),
        )
        self.assertLess(
            order.index("BROWSER_VISUAL_REVIEW"),
            order.index("ROUTE_AND_MOUNT_BINDING"),
        )
        self.assertNotIn(
            "CROSS_RUNTIME_DELIVERY_UNREGISTERED",
            self.registration["blockers"],
        )
        self.assertIn(
            "APP_IMPORT_PREREGISTRATION_ABSENT",
            self.registration["blockers"],
        )
        self.assertEqual(order[-1], "CURRENT_AND_RUNTIME_ACTIVATION")

    def test_registration_records_no_execution_or_activation(self) -> None:
        facts = self.registration["facts"]
        self.assertTrue(facts["dual_runtime_adapter_assets_registered"])
        self.assertFalse(facts["delivery_attempted"])
        self.assertFalse(facts["python_adapter_invoked"])
        self.assertFalse(facts["javascript_adapter_runtime_loaded"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["dom_mounted"])
        self.assertFalse(facts["current_activated"])
        self.assertFalse(facts["runtime_mutations_performed"])

    def test_all_runtime_and_trading_authority_remains_locked(self) -> None:
        self.assertTrue(
            all(value is False for value in self.registration["authority"].values())
        )

    def test_contract_has_neutral_stage_order_and_no_promotional_copy(self) -> None:
        presentation = self.registration["presentation_contract"]
        self.assertEqual(
            presentation["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertFalse(presentation["ready_word_allowed"])

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

        collect(self.registration)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.registration["facts"]["profitability_proven"])

    def test_non_native_and_cyclic_documents_fail_snapshot_boundary(self) -> None:
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                NonNativeMapping(self.registration)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                cyclic
            )
        )

    def test_extra_field_fails_exact_verifier_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["hidden_claim"] = True
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_authority_promotion_fails_exact_verifier_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["authority"]["paper_authorized"] = True
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_asset_hash_swap_fails_exact_verifier_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["asset_manifest"][0]["sha256"] = "f" * 64
        tampered["asset_manifest_hash"] = "f" * 64
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_predecessor_hash_swap_fails_exact_verifier_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["predecessor_contract"]["registration_hash"] = "f" * 64
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_host_plan_promotion_fails_exact_verifier_after_reseal(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["host_plan"]["app_importer"] = "app.js"
        self.assertFalse(
            verify_static_presentation_in_memory_delivery_adapter_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_registration_is_deterministic_and_native_json(self) -> None:
        rebuilt = (
            build_static_presentation_in_memory_delivery_adapter_registration_v1()
        )
        self.assertEqual(self.registration, rebuilt)
        self.assertEqual(
            json.loads(json.dumps(self.registration, sort_keys=True)),
            self.registration,
        )


if __name__ == "__main__":
    unittest.main()
