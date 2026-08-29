from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.static_presentation_host_patch_preregistration_v1 import (
    build_static_presentation_host_patch_preregistration_v1,
    verify_static_presentation_host_patch_preregistration_v1,
)
from exchange_terminal.services.static_presentation_unmounted_render_review_asset_registration_v1 import (
    PATCH_PREREGISTRATION_HASH,
    REGISTRATION_ID,
    REVIEW_IMPLEMENTATION_SHA256,
    REVIEW_NODE_TEST_SHA256,
    SCHEMA_VERSION,
    build_static_presentation_unmounted_render_review_asset_registration_v1,
    verify_static_presentation_unmounted_render_review_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationUnmountedRenderReviewAssetRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration = (
            build_static_presentation_unmounted_render_review_asset_registration_v1()
        )

    def _reseal(self, document: dict) -> dict:
        document.pop("asset_registration_hash")
        return seal_strict_canonical_document(document, "asset_registration_hash")

    def test_registration_is_exact_blocked_and_unbound(self) -> None:
        self.assertEqual(self.registration["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.registration["registration_id"], REGISTRATION_ID)
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "NO_DOM_RENDER_REVIEW_ASSETS_REGISTERED_UNBOUND",
        )
        self.assertTrue(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                self.registration
            )
        )

    def test_source_contract_pins_exact_patch_preregistration(self) -> None:
        predecessor = build_static_presentation_host_patch_preregistration_v1()
        self.assertTrue(
            verify_static_presentation_host_patch_preregistration_v1(predecessor)
        )
        self.assertEqual(
            predecessor["patch_preregistration_hash"],
            PATCH_PREREGISTRATION_HASH,
        )
        self.assertEqual(
            self.registration["source_contract"]["patch_preregistration_hash"],
            predecessor["patch_preregistration_hash"],
        )

    def test_every_source_and_asset_hash_matches_disk(self) -> None:
        source = self.registration["source_contract"]
        expected = {
            source["implementation_path"]: source["implementation_sha256"],
            source["test_path"]: source["test_sha256"],
            source["adr_path"]: source["adr_sha256"],
        }
        expected.update({
            row["path"]: row["sha256"]
            for row in self.registration["asset_manifest"]
        })
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_review_implementation_and_node_test_hashes_are_pinned(self) -> None:
        by_id = {
            row["asset_id"]: row["sha256"]
            for row in self.registration["asset_manifest"]
        }
        self.assertEqual(
            by_id["review_javascript"],
            REVIEW_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(by_id["review_node_test"], REVIEW_NODE_TEST_SHA256)

    def test_asset_manifest_is_unique_sorted_and_hash_bound(self) -> None:
        rows = self.registration["asset_manifest"]
        ids = [row["asset_id"] for row in rows]
        paths = [row["path"] for row in rows]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(len(rows), 7)
        self.assertEqual(
            self.registration["asset_manifest_hash"],
            strict_canonical_hash(rows),
        )

    def test_production_load_order_is_exact(self) -> None:
        self.assertEqual(
            self.registration["production_load_order"],
            [
                "strict_canonical_javascript",
                "rail_javascript",
                "delivery_javascript",
                "review_javascript",
            ],
        )

    def test_test_only_python_fixture_is_excluded_from_runtime_order(self) -> None:
        test_contract = self.registration["test_contract"]
        self.assertEqual(
            test_contract["python_fixture_mode"],
            "TEST_ONLY_CHILD_PROCESS",
        )
        self.assertFalse(test_contract["python_fixture_is_runtime_asset"])
        self.assertFalse(test_contract["node_child_process_is_runtime_capability"])
        self.assertNotIn(
            test_contract["python_fixture_asset_id"],
            self.registration["production_load_order"],
        )

    def test_review_exports_stage_order_and_no_dom_contract_are_exact(self) -> None:
        contract = self.registration["review_contract"]
        self.assertEqual(len(contract["expected_commonjs_exports"]), 8)
        self.assertEqual(
            contract["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(contract["no_dom_environment_required"])
        self.assertTrue(contract["local_behavior_review_only"])
        self.assertFalse(contract["external_independent_review_complete"])
        self.assertFalse(contract["ready_word_allowed"])

    def test_review_context_hashes_match_predecessor(self) -> None:
        predecessor = build_static_presentation_host_patch_preregistration_v1()
        source = self.registration["source_contract"]
        self.assertEqual(source["patch_plan_hash"], predecessor["patch_plan_hash"])
        self.assertEqual(
            source["host_app_fragment_sha256"],
            predecessor["patch_plan"]["operations"][-1]["fragment_sha256"],
        )

    def test_host_plan_remains_fully_unbound(self) -> None:
        self.assertTrue(
            all(value is None for value in self.registration["host_plan"].values())
        )

    def test_registration_records_no_execution_or_review_promotion(self) -> None:
        facts = self.registration["facts"]
        self.assertTrue(facts["review_assets_registered"])
        self.assertFalse(facts["review_assets_runtime_loaded"])
        self.assertFalse(facts["node_test_executed_by_registration"])
        self.assertFalse(facts["python_fixture_executed_by_registration"])
        self.assertFalse(facts["external_independent_review_complete"])
        self.assertFalse(facts["host_patch_applied"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["dom_mounted"])
        self.assertFalse(facts["runtime_mutations_performed"])

    def test_all_runtime_review_mount_and_trading_authority_is_locked(self) -> None:
        self.assertTrue(
            all(value is False for value in self.registration["authority"].values())
        )

    def test_external_review_and_host_blockers_remain_explicit(self) -> None:
        blockers = self.registration["blockers"]
        self.assertIn("EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED", blockers)
        self.assertIn("HOST_WRITE_AUTHORIZATION_ABSENT", blockers)
        self.assertIn("APP_IMPORTER_UNBOUND", blockers)
        self.assertIn("BROWSER_VISUAL_REVIEW_NOT_PERFORMED", blockers)
        self.assertIn("DOM_MOUNT_UNAUTHORIZED", blockers)
        self.assertIn("CURRENT_ADMISSION_LOCKED", blockers)

    def test_non_native_and_cyclic_documents_fail_snapshot_boundary(self) -> None:
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                NonNativeMapping(self.registration)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                cyclic
            )
        )

    def test_resealed_extra_claim_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["hidden_claim"] = True
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_resealed_asset_hash_swap_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["asset_manifest"][0]["sha256"] = "f" * 64
        tampered["asset_manifest_hash"] = strict_canonical_hash(
            tampered["asset_manifest"]
        )
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_resealed_host_plan_injection_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["host_plan"]["app_importer"] = "app.js"
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_resealed_authority_promotion_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["authority"]["external_independent_review_completion_allowed"] = True
        self.assertFalse(
            verify_static_presentation_unmounted_render_review_asset_registration_v1(
                self._reseal(tampered)
            )
        )

    def test_registration_has_no_promotional_copy(self) -> None:
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

    def test_registration_is_deterministic_native_json(self) -> None:
        rebuilt = (
            build_static_presentation_unmounted_render_review_asset_registration_v1()
        )
        self.assertEqual(self.registration, rebuilt)
        self.assertEqual(
            json.loads(json.dumps(self.registration, sort_keys=True)),
            self.registration,
        )


if __name__ == "__main__":
    unittest.main()
