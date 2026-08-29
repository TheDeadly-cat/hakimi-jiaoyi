from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1 as subject,
)
from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    build_static_presentation_asset_registration_v1,
    verify_static_presentation_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


class _DictSubclass(dict):
    pass


class PortfolioCorrelationAdmissionEffectiveBudgetBridgeAssetRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.spec = (
            subject.expected_portfolio_correlation_admission_effective_budget_bridge_asset_spec_v1()
        )
        self.registration = (
            subject.build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )

    def test_registration_is_deterministic_and_exact(self) -> None:
        repeated = (
            subject.build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )
        self.assertEqual(self.registration, repeated)
        self.assertTrue(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                self.registration
            )
        )
        self.assertEqual(
            self.registration["registration_hash"],
            subject.EXPECTED_REGISTRATION_HASH,
        )
        self.assertEqual(
            self.registration["spec_hash"],
            subject.EXPECTED_SPEC_HASH,
        )
        self.assertEqual(
            self.registration["asset_manifest_hash"],
            subject.EXPECTED_ASSET_MANIFEST_HASH,
        )

    def test_registration_remains_blocked_and_unbound(self) -> None:
        self.assertEqual(self.registration["status"], "BLOCKED")
        self.assertEqual(
            self.registration["registration_state"],
            "STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND",
        )
        self.assertTrue(self.registration["blockers"])
        self.assertIn(
            "MOUNT_SLOT_UNBOUND",
            self.registration["blockers"],
        )
        self.assertIn(
            "CURRENT_ADMISSION_LOCKED",
            self.registration["blockers"],
        )

    def test_ten_asset_manifest_entries_are_unique_and_hash_only(self) -> None:
        manifest = self.registration["asset_manifest"]
        self.assertEqual(len(manifest), 10)
        self.assertEqual(
            len({entry["asset_id"] for entry in manifest}),
            10,
        )
        for entry in manifest:
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertNotIn("content", entry)
            self.assertNotIn("source_bytes", entry)

    def test_source_contract_pins_adr0305(self) -> None:
        source = self.registration["source_contract"]
        self.assertEqual(
            source["schema_version"],
            "portfolio-correlation-admission-effective-budget-binding-v1",
        )
        self.assertTrue(
            source["implementation_path"].endswith(
                "portfolio_correlation_admission_effective_budget_binding_v1.py"
            )
        )
        self.assertTrue(
            source["adr_path"].endswith(
                "0305-portfolio-correlation-admission-effective-budget-binding-v1.md"
            )
        )

    def test_consumer_contract_pins_load_export_stage_and_tier_order(self) -> None:
        consumer = self.registration["consumer_contract"]
        self.assertEqual(
            consumer["expected_commonjs_exports"],
            list(subject.COMMONJS_EXPORTS),
        )
        self.assertEqual(
            consumer["script_load_order"],
            list(subject.SCRIPT_LOAD_ORDER),
        )
        self.assertEqual(
            consumer["stage_order"],
            list(subject.STAGE_ORDER),
        )
        self.assertEqual(
            consumer["tier_order"],
            list(subject.TIER_ORDER),
        )
        self.assertFalse(consumer["ready_word_allowed"])
        self.assertFalse(consumer["raw_source_evidence_embedded"])

    def test_host_plan_and_all_runtime_authority_remain_locked(self) -> None:
        self.assertTrue(
            all(value is None for value in self.registration["host_plan"].values())
        )
        self.assertTrue(
            all(value is False for value in self.registration["authority"].values())
        )
        self.assertFalse(self.registration["facts"]["browser_executed"])
        self.assertFalse(self.registration["facts"]["ui_mounted"])
        self.assertFalse(self.registration["facts"]["current_activated"])
        self.assertFalse(self.registration["facts"]["profitability_proven"])

    def test_generic_registration_also_verifies_exact_wrapper_output(self) -> None:
        self.assertTrue(
            verify_static_presentation_asset_registration_v1(
                self.registration,
                self.spec,
            )
        )

    def test_valid_but_different_asset_hash_is_rejected_by_wrapper(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["assets"][0]["sha256"] = "0" * 64
        candidate = build_static_presentation_asset_registration_v1(spec)
        self.assertTrue(
            verify_static_presentation_asset_registration_v1(candidate, spec)
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                candidate
            )
        )

    def test_valid_but_different_load_order_is_rejected_by_wrapper(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["consumer_contract"]["script_load_order"][1:] = reversed(
            spec["consumer_contract"]["script_load_order"][1:]
        )
        candidate = build_static_presentation_asset_registration_v1(spec)
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                candidate
            )
        )

    def test_valid_but_ready_label_is_rejected_by_wrapper(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["consumer_contract"]["neutral_status_labels"]["pass"] = "READY"
        with self.assertRaisesRegex(
            ValueError,
            "neutral status labels are not exact",
        ):
            build_static_presentation_asset_registration_v1(spec)

    def test_resealed_host_plan_promotion_is_rejected(self) -> None:
        promoted = copy.deepcopy(self.registration)
        promoted["host_plan"]["mount_slot"] = "forged-slot"
        promoted = seal_strict_canonical_document(
            promoted,
            "registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                promoted
            )
        )

    def test_resealed_authority_promotion_is_rejected(self) -> None:
        promoted = copy.deepcopy(self.registration)
        promoted["authority"]["ui_mount_allowed"] = True
        promoted = seal_strict_canonical_document(
            promoted,
            "registration_hash",
        )
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                promoted
            )
        )

    def test_non_native_and_cyclic_documents_fail_closed(self) -> None:
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                _DictSubclass(self.registration)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                cyclic
            )
        )

    def test_all_pinned_files_match_current_bytes(self) -> None:
        source = self.spec["source_contract"]
        expected = {
            source["implementation_path"]: source["implementation_sha256"],
            source["test_path"]: source["test_sha256"],
            source["adr_path"]: source["adr_sha256"],
        }
        expected.update({
            asset["path"]: asset["sha256"]
            for asset in self.spec["assets"]
        })
        for path, digest in expected.items():
            with self.subTest(path=path):
                self.assertEqual(
                    sha256((ROOT / path).read_bytes()).hexdigest(),
                    digest,
                )

    def test_registration_contains_no_raw_evidence_or_permission_claim(self) -> None:
        encoded = json.dumps(self.registration, sort_keys=True)
        for forbidden in (
            '"positions":',
            '"symbol":',
            '"notional":',
            "synthetic-strategy",
            "synthetic-variant",
            "cluster_exposures",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            self.registration["consumer_contract"][
                "raw_source_evidence_embedded"
            ]
        )

    def test_generic_registration_implementation_pin_matches(self) -> None:
        path = (
            ROOT
            / "exchange_terminal/services/"
            "static_presentation_asset_registration_v1.py"
        )
        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.GENERIC_REGISTRATION_IMPLEMENTATION_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
