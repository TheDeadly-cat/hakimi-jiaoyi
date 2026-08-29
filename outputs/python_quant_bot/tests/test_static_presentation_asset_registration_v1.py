from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
    SCHEMA_VERSION,
    build_portfolio_correlation_admission_rail_asset_registration_v1,
    build_static_presentation_asset_registration_v1,
    expected_portfolio_correlation_admission_rail_spec_v1,
    verify_portfolio_correlation_admission_rail_asset_registration_v1,
    verify_static_presentation_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationAssetRegistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = expected_portfolio_correlation_admission_rail_spec_v1()
        self.registration = (
            build_portfolio_correlation_admission_rail_asset_registration_v1()
        )

    def test_specific_registration_is_exact_blocked_and_unbound(self) -> None:
        self.assertEqual(self.registration["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            self.registration["registration_id"],
            PORTFOLIO_CORRELATION_ADMISSION_RAIL_REGISTRATION_ID,
        )
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND",
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_rail_asset_registration_v1(
                self.registration
            )
        )

    def test_every_pinned_source_file_hash_matches_disk(self) -> None:
        expected = {
            row["path"]: row["sha256"] for row in self.spec["assets"]
        }
        source = self.spec["source_contract"]
        expected.update({
            source["implementation_path"]: source["implementation_sha256"],
            source["test_path"]: source["test_sha256"],
            source["adr_path"]: source["adr_sha256"],
            self.spec["consumer_contract"]["protected_stylesheet_path"]: (
                self.spec["consumer_contract"]["protected_stylesheet_sha256"]
            ),
        })
        observed = {
            path: hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_asset_order_is_canonical_and_deterministic(self) -> None:
        reordered = copy.deepcopy(self.spec)
        reordered["assets"].reverse()
        first = build_static_presentation_asset_registration_v1(self.spec)
        second = build_static_presentation_asset_registration_v1(reordered)
        self.assertEqual(first, second)
        self.assertEqual(
            [row["asset_id"] for row in first["asset_manifest"]],
            sorted(row["asset_id"] for row in first["asset_manifest"]),
        )

    def test_builder_does_not_mutate_spec(self) -> None:
        before = copy.deepcopy(self.spec)
        build_static_presentation_asset_registration_v1(self.spec)
        self.assertEqual(self.spec, before)

    def test_host_plan_injection_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["host_plan"]["app_importer"] = "app.js"
        with self.assertRaisesRegex(ValueError, "fully unbound"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_path_traversal_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["assets"][0]["path"] = "../runtime/forged.js"
        with self.assertRaisesRegex(ValueError, "source boundary"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_duplicate_asset_id_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["assets"][1]["asset_id"] = tampered["assets"][0]["asset_id"]
        with self.assertRaisesRegex(ValueError, "must be unique"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_ready_label_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["consumer_contract"]["neutral_status_labels"]["pass"] = "READY"
        with self.assertRaisesRegex(ValueError, "neutral status"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_stage_order_drift_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["consumer_contract"]["stage_order"] = [
            "SOURCE", "MATURITY", "GAP", "PERMISSION"
        ]
        with self.assertRaisesRegex(ValueError, "stage order"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_unknown_export_or_asset_reference_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.spec)
        tampered["consumer_contract"]["script_load_order"].append("forged_asset")
        with self.assertRaisesRegex(ValueError, "unknown asset"):
            build_static_presentation_asset_registration_v1(tampered)

    def test_non_native_mapping_fails_snapshot_boundary(self) -> None:
        self.assertFalse(
            verify_static_presentation_asset_registration_v1(
                self.registration,
                NonNativeMapping(self.spec),
            )
        )

    def test_extra_registration_field_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["hidden_claim"] = True
        tampered.pop("registration_hash")
        tampered = seal_strict_canonical_document(tampered, "registration_hash")
        self.assertFalse(
            verify_portfolio_correlation_admission_rail_asset_registration_v1(
                tampered
            )
        )

    def test_resealed_authority_promotion_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["authority"]["paper_authorized"] = True
        tampered.pop("registration_hash")
        tampered = seal_strict_canonical_document(tampered, "registration_hash")
        self.assertFalse(
            verify_portfolio_correlation_admission_rail_asset_registration_v1(
                tampered
            )
        )

    def test_manifest_hash_swap_fails_specific_verifier(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["asset_manifest"][0]["sha256"] = "f" * 64
        tampered.pop("registration_hash")
        tampered = seal_strict_canonical_document(tampered, "registration_hash")
        self.assertFalse(
            verify_portfolio_correlation_admission_rail_asset_registration_v1(
                tampered
            )
        )

    def test_exports_stage_tier_and_style_pins_are_exact(self) -> None:
        consumer = self.registration["consumer_contract"]
        self.assertEqual(len(consumer["expected_commonjs_exports"]), 8)
        self.assertEqual(
            consumer["stage_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(len(consumer["tier_order"]), 8)
        self.assertFalse(consumer["ready_word_allowed"])
        self.assertEqual(
            consumer["protected_stylesheet_sha256"],
            "ee6a5ae746142e32df768fe3261746f66c2b1a902e38b85fa9c0ecc4ce7bdc2a",
        )

    def test_all_runtime_and_trading_authority_remains_locked(self) -> None:
        self.assertTrue(all(value is False for value in self.registration["authority"].values()))
        self.assertFalse(self.registration["facts"]["app_imported"])
        self.assertFalse(self.registration["facts"]["browser_executed"])
        self.assertFalse(self.registration["facts"]["ui_mounted"])
        self.assertFalse(self.registration["facts"]["runtime_mutations_performed"])


if __name__ == "__main__":
    unittest.main()
