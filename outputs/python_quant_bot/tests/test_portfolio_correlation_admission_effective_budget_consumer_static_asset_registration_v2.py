from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from exchange_terminal.services.portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1 import (
    build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1,
    verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2 import (
    DELTA_ASSETS,
    EXPECTED_ASSET_MANIFEST_HASH,
    EXPECTED_REGISTRATION_HASH,
    EXPECTED_SPEC_HASH,
    HOST_BINDING_CANDIDATES_HASH,
    HOST_BINDING_PREREGISTRATION_HASH,
    HOST_CANDIDATE_LOAD_ORDER,
    HOST_JAVASCRIPT_ASSET_MANIFEST_HASH,
    HOST_JAVASCRIPT_LOAD_ORDER_HASH,
    PREDECESSOR_REGISTRATION_HASH,
    PROTECTED_STYLESHEET_PATH,
    PROTECTED_STYLESHEET_SHA256,
    REGISTRATION_ID,
    SCHEMA_VERSION,
    SCRIPT_LOAD_ORDER,
    SOURCE_CONTRACT,
    STATIC_FINGERPRINT,
    build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2,
    expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2,
    verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1 import (
    build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
    verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1,
)
from exchange_terminal.services.static_presentation_asset_registration_v1 import (
    verify_static_presentation_asset_registration_v1,
)


MODULE = (
    "exchange_terminal.services.portfolio_correlation_admission_effective_budget_"
    "consumer_static_asset_registration_v2"
)
ROOT = Path(__file__).resolve().parents[1]


class ConsumerStaticAssetRegistrationV2Tests(TestCase):
    def setUp(self) -> None:
        self.spec = (
            expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2()
        )
        self.document = (
            build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2()
        )

    def assert_rejected(self, candidate: object) -> None:
        with self.assertRaises((TypeError, ValueError)):
            verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2(
                candidate
            )

    def test_exact_schema_state_and_hashes(self) -> None:
        self.assertEqual(self.document["registration_id"], REGISTRATION_ID)
        self.assertEqual(
            self.document["schema_version"],
            "static-presentation-asset-registration-v1",
        )
        self.assertEqual(self.document["consumer_contract"]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            self.document["consumer_contract"]["static_fingerprint"],
            STATIC_FINGERPRINT,
        )
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertEqual(
            self.document["registration_state"],
            "STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND",
        )
        self.assertEqual(self.document["spec_hash"], EXPECTED_SPEC_HASH)
        self.assertEqual(
            self.document["asset_manifest_hash"], EXPECTED_ASSET_MANIFEST_HASH
        )
        self.assertEqual(
            self.document["registration_hash"], EXPECTED_REGISTRATION_HASH
        )

    def test_build_is_deterministic_and_exactly_verifiable(self) -> None:
        rebuilt = (
            build_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2()
        )
        self.assertEqual(rebuilt, self.document)
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_consumer_static_asset_registration_v2(
                self.document
            )
        )
        self.assertTrue(
            verify_static_presentation_asset_registration_v1(self.document, self.spec)
        )

    def test_exact_predecessor_registrations_remain_valid(self) -> None:
        predecessor = (
            build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )
        host = (
            build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1(
                predecessor
            )
        )
        self.assertTrue(
            verify_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1(
                host
            )
        )
        self.assertEqual(
            predecessor["registration_hash"], PREDECESSOR_REGISTRATION_HASH
        )
        self.assertEqual(
            host["host_binding_preregistration_hash"],
            HOST_BINDING_PREREGISTRATION_HASH,
        )
        self.assertEqual(
            host["binding_candidates_hash"], HOST_BINDING_CANDIDATES_HASH
        )

    def test_source_contract_is_exact_adr0314(self) -> None:
        self.assertEqual(self.document["source_contract"], SOURCE_CONTRACT)

    def test_v1_manifest_is_preserved_without_rewriting(self) -> None:
        predecessor = (
            build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )
        old_assets = {
            asset["asset_id"]: asset for asset in predecessor["asset_manifest"]
        }
        new_assets = {
            asset["asset_id"]: asset for asset in self.document["asset_manifest"]
        }
        self.assertEqual(len(old_assets), 10)
        self.assertEqual(len(new_assets), 20)
        for asset_id, asset in old_assets.items():
            self.assertEqual(new_assets[asset_id], asset)

    def test_delta_manifest_is_exactly_adr0312_and_adr0313(self) -> None:
        manifest = {
            asset["asset_id"]: asset for asset in self.document["asset_manifest"]
        }
        expected = {
            asset["asset_id"]: {
                "asset_id": asset["asset_id"],
                "path": asset["path"],
                "role": asset["role"],
                "sha256": asset["sha256"],
            }
            for asset in DELTA_ASSETS
        }
        self.assertEqual(set(manifest).difference({
            asset["asset_id"]
            for asset in build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()[
                "asset_manifest"
            ]
        }), set(expected))
        for asset_id, asset in expected.items():
            self.assertEqual(manifest[asset_id], asset)

    def test_registered_source_and_asset_bytes_match_pins(self) -> None:
        pinned_paths = {
            asset["path"]: asset["sha256"]
            for asset in self.document["asset_manifest"]
        }
        for prefix in ("implementation", "test", "adr"):
            pinned_paths[self.document["source_contract"][f"{prefix}_path"]] = (
                self.document["source_contract"][f"{prefix}_sha256"]
            )
        for relative_path, expected_hash in pinned_paths.items():
            actual_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(actual_hash, expected_hash, relative_path)

    def test_host_candidate_assets_match_registered_runtime_assets(self) -> None:
        host = (
            build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        )
        javascript = host["binding_candidates"]["javascript_assets"]
        self.assertEqual(
            javascript["asset_manifest_hash"],
            HOST_JAVASCRIPT_ASSET_MANIFEST_HASH,
        )
        self.assertEqual(
            javascript["load_order_hash"], HOST_JAVASCRIPT_LOAD_ORDER_HASH
        )
        self.assertEqual(javascript["load_order"], list(HOST_CANDIDATE_LOAD_ORDER))

        manifest = {
            asset["asset_id"]: asset for asset in self.document["asset_manifest"]
        }
        registered_order = [
            manifest[asset_id]["path"] for asset_id in SCRIPT_LOAD_ORDER
        ]
        self.assertEqual(registered_order, javascript["load_order"])
        self.assertEqual(
            manifest[self.document["consumer_contract"]["stylesheet_asset_id"]][
                "path"
            ],
            host["binding_candidates"]["stylesheet"]["isolated_path"],
        )

    def test_consumer_first_script_order_is_exact(self) -> None:
        self.assertEqual(
            self.document["consumer_contract"]["script_load_order"],
            list(SCRIPT_LOAD_ORDER),
        )
        self.assertEqual(
            self.document["consumer_contract"]["javascript_asset_id"],
            "inspection_consumer_javascript",
        )
        self.assertEqual(
            self.document["consumer_contract"]["browser_global"],
            "HakimiPortfolioCorrelationAdmissionEffectiveBudgetInspectionConsumerV1",
        )

    def test_neutral_presentation_contract_is_preserved(self) -> None:
        consumer = self.document["consumer_contract"]
        self.assertEqual(
            consumer["stage_order"], ["SOURCE", "GAP", "MATURITY", "PERMISSION"]
        )
        self.assertEqual(
            consumer["neutral_status_labels"],
            {
                "block": "LOCAL BLOCK",
                "pass": "LOCAL ALIGNMENT",
                "unknown": "SOURCE UNKNOWN",
            },
        )
        self.assertFalse(consumer["ready_word_allowed"])
        self.assertFalse(consumer["raw_source_evidence_embedded"])

    def test_protected_stylesheet_remains_hash_only_and_unchanged(self) -> None:
        consumer = self.document["consumer_contract"]
        self.assertEqual(
            consumer["protected_stylesheet_path"], PROTECTED_STYLESHEET_PATH
        )
        self.assertEqual(
            consumer["protected_stylesheet_sha256"], PROTECTED_STYLESHEET_SHA256
        )

    def test_all_host_slots_remain_null(self) -> None:
        self.assertTrue(all(value is None for value in self.document["host_plan"].values()))

    def test_runtime_and_profitability_facts_remain_false(self) -> None:
        facts = self.document["facts"]
        for key in (
            "app_imported",
            "browser_executed",
            "browser_visual_review_performed",
            "current_activated",
            "html_script_bound",
            "profitability_proven",
            "route_registered",
            "runtime_mutations_performed",
            "stylesheet_runtime_loaded",
            "ui_mounted",
        ):
            self.assertFalse(facts[key], key)

    def test_all_authority_remains_denied(self) -> None:
        self.assertTrue(self.document["authority"])
        self.assertFalse(any(self.document["authority"].values()))
        self.assertFalse(self.document["authority"]["paper_authorized"])
        self.assertFalse(self.document["authority"]["live_order_allowed"])

    def test_source_contract_mutation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["source_contract"]["implementation_sha256"] = "0" * 64
        self.assert_rejected(candidate)

    def test_asset_hash_mutation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["asset_manifest"][0]["sha256"] = "0" * 64
        self.assert_rejected(candidate)

    def test_asset_removal_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["asset_manifest"].pop()
        self.assert_rejected(candidate)

    def test_script_order_mutation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        order = candidate["consumer_contract"]["script_load_order"]
        order[-1], order[-2] = order[-2], order[-1]
        self.assert_rejected(candidate)

    def test_browser_global_mutation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["consumer_contract"]["browser_global"] = "InjectedConsumer"
        self.assert_rejected(candidate)

    def test_host_binding_mutation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["host_plan"]["html_script"] = "/static/injected.js"
        self.assert_rejected(candidate)

    def test_authority_escalation_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["authority"]["runtime_asset_loading_allowed"] = True
        self.assert_rejected(candidate)

    def test_extra_top_level_field_is_rejected(self) -> None:
        candidate = deepcopy(self.document)
        candidate["current"] = True
        self.assert_rejected(candidate)

    def test_predecessor_registration_drift_fails_closed(self) -> None:
        predecessor = deepcopy(
            build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1()
        )
        predecessor["registration_hash"] = "0" * 64
        with patch(
            f"{MODULE}.build_portfolio_correlation_admission_effective_budget_bridge_asset_registration_v1",
            return_value=predecessor,
        ):
            with self.assertRaises(ValueError):
                expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2()

    def test_host_preregistration_drift_fails_closed(self) -> None:
        host = deepcopy(
            build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1()
        )
        host["host_binding_preregistration_hash"] = "0" * 64
        with patch(
            f"{MODULE}.build_portfolio_correlation_admission_effective_budget_host_binding_preregistration_v1",
            return_value=host,
        ):
            with self.assertRaises(ValueError):
                expected_portfolio_correlation_admission_effective_budget_consumer_static_asset_spec_v2()

    def test_non_mapping_document_is_rejected(self) -> None:
        self.assert_rejected(None)
