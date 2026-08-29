from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import unittest

from exchange_terminal.services.portfolio_shadow_risk import (
    build_shadow_portfolio_risk,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1 import (
    ACTIVATION_ORDER,
    EXPECTED_IMPLEMENTATION_SHA256,
    FIXED_BLOCKERS,
    IMPLEMENTATION_PATHS,
    PREREGISTRATION_SCHEMA_VERSION,
    PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1,
    expected_shadow_consumer_implementation_sha256_v1,
    verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV1Tests(
    unittest.TestCase
):
    _UNSET = object()

    def setUp(self) -> None:
        self.manifest = expected_shadow_consumer_implementation_sha256_v1()

    def _build(self, manifest=_UNSET):
        return build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
            self.manifest if manifest is self._UNSET else manifest
        )

    def test_expected_implementation_pins_match_current_source_files(self):
        root = Path(__file__).resolve().parents[1]
        observed = {
            artifact_id: hashlib.sha256(
                (root / relative_path).read_bytes()
            ).hexdigest()
            for artifact_id, relative_path in IMPLEMENTATION_PATHS.items()
        }
        self.assertEqual(observed, EXPECTED_IMPLEMENTATION_SHA256)

    def test_legacy_shadow_signature_proves_new_consumer_gap(self):
        parameters = inspect.signature(build_shadow_portfolio_risk).parameters
        self.assertEqual(
            set(parameters),
            {
                "candidate",
                "backtest_report",
                "correlation_matrix",
                "hypothetical_equity",
            },
        )
        for missing in (
            "dual_source_receipt",
            "complete_link_audit",
            "portfolio_risk_adapter_v1",
        ):
            self.assertNotIn(missing, parameters)

    def test_matching_manifest_remains_immutably_blocked(self):
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(document["decision"], "PREREGISTERED_NOT_BOUND")
        self.assertTrue(
            document["source"]["implementation_manifest_contract_verified"]
        )
        self.assertTrue(document["source"]["implementation_fingerprints_match"])
        self.assertEqual(document["blockers"], FIXED_BLOCKERS)
        self.assertFalse(
            document["authority"]["shadow_consumer_activation_allowed"]
        )

    def test_hash_drift_adds_fingerprint_blocker_without_resealing_current(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["adapter_v1"] = "0" * 64
        document = self._build(manifest)
        self.assertEqual(document["status"], "BLOCKED")
        self.assertIn("implementation_fingerprint_mismatch", document["blockers"])
        self.assertFalse(document["source"]["implementation_fingerprints_match"])

    def test_manifest_missing_extra_and_type_aliases_fail_closed(self):
        missing = copy.deepcopy(self.manifest)
        missing.pop("adapter_v1")
        extra = copy.deepcopy(self.manifest)
        extra["unknown"] = "0" * 64
        alias = copy.deepcopy(self.manifest)
        alias["adapter_v1"] = True
        for manifest in (missing, extra, alias, [], None):
            with self.subTest(manifest=manifest):
                document = self._build(manifest)
                self.assertEqual(document["status"], "BLOCKED")
                self.assertIn(
                    "implementation_manifest_contract_invalid",
                    document["blockers"],
                )

    def test_reuse_plan_avoids_duplicate_provider_and_attestation_stacks(self):
        document = self._build()
        decisions = {
            item["capability"]: item["decision"]
            for item in document["reuse_plan"]
        }
        self.assertEqual(
            decisions["PROVIDER_IDENTITY_AND_KEY_LIFECYCLE"],
            "REUSE_EXISTING_CONTRACTS",
        )
        self.assertEqual(
            decisions["DATASET_CONTENT_ATTESTATION"],
            "REUSE_EXISTING_CONTRACT",
        )
        self.assertEqual(
            decisions["LEGACY_MATRIX_DERIVATION_BINDING"],
            "NEW_NARROW_ADAPTER_REQUIRED",
        )
        self.assertFalse(document["facts"]["provider_identity_stack_duplicated"])
        self.assertFalse(document["facts"]["dataset_attestation_stack_duplicated"])

    def test_activation_order_is_consumer_first_and_current_switch_last(self):
        document = self._build()
        self.assertEqual(document["activation_order"], ACTIVATION_ORDER)
        self.assertEqual(
            document["activation_order"][0],
            "BIND_LEGACY_MATRIX_TO_ATTESTED_COMPLETED_PRICE_INPUT",
        )
        self.assertEqual(
            document["activation_order"][-1],
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        )

    def test_preregistration_does_not_replace_or_mount_existing_consumers(self):
        document = self._build()
        self.assertFalse(document["facts"]["legacy_shadow_replaced"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["facts"]["server_route_registered"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(document["facts"]["legacy_shadow_accepts_adapter_v1"])

    def test_exact_verifier_rejects_resealed_status_authority_and_type_tamper(self):
        document = self._build()
        verification = verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
            document,
            self.manifest,
        )
        self.assertEqual(verification["status"], "PASS")
        variants = []
        status_tamper = copy.deepcopy(document)
        status_tamper["status"] = "READY"
        variants.append(status_tamper)
        authority_tamper = copy.deepcopy(document)
        authority_tamper["authority"]["current_admission_allowed"] = True
        variants.append(authority_tamper)
        type_tamper = copy.deepcopy(document)
        type_tamper["source"]["implementation_fingerprints_match"] = 1
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(
                    tampered,
                    "preregistration_hash",
                )
                result = verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
                    resealed,
                    self.manifest,
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["preregistration_status"], "UNKNOWN")

    def test_manifest_is_not_mutated(self):
        expected = copy.deepcopy(self.manifest)
        self._build()
        self.assertEqual(self.manifest, expected)

    def test_schema_fingerprint_authority_and_exports_are_locked(self):
        document = self._build()
        verification = verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
            document,
            self.manifest,
        )
        self.assertEqual(document["schema_version"], PREREGISTRATION_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", str(document))
        self.assertFalse(document["facts"]["runtime_assets_accessed"])


if __name__ == "__main__":
    unittest.main()
