from __future__ import annotations

import copy
import hashlib
import inspect
from pathlib import Path
import unittest

from exchange_terminal.services.portfolio_shadow_risk import build_shadow_portfolio_risk
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1
    as v1_contract,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_DEFAULT = object()


class StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV2Tests(
    unittest.TestCase
):
    def setUp(self):
        self.v1_manifest = v1_contract.expected_shadow_consumer_implementation_sha256_v1()
        self.v1_document = v1_contract.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v1(
            self.v1_manifest
        )
        self.manifest = subject.expected_shadow_consumer_implementation_sha256_v2()

    def _build(
        self,
        v1_document=_DEFAULT,
        v1_manifest=_DEFAULT,
        manifest=_DEFAULT,
    ):
        return subject.build_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
            self.v1_document if v1_document is _DEFAULT else v1_document,
            self.v1_manifest if v1_manifest is _DEFAULT else v1_manifest,
            self.manifest if manifest is _DEFAULT else manifest,
        )

    def test_expected_implementation_pins_match_current_source_files(self):
        root = Path(__file__).resolve().parents[1]
        observed = {
            artifact_id: hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
            for artifact_id, relative_path in subject.IMPLEMENTATION_PATHS.items()
        }
        self.assertEqual(observed, subject.EXPECTED_IMPLEMENTATION_SHA256)

    def test_immutable_v1_is_exactly_inherited_without_rewrite(self):
        document = self._build()
        self.assertEqual(self.v1_document["status"], "BLOCKED")
        self.assertEqual(
            self.v1_document["preregistration_hash"], subject.V1_PREREGISTRATION_HASH
        )
        self.assertTrue(document["source"]["immutable_v1_exactly_verified"])
        self.assertEqual(
            document["source"]["immutable_v1_preregistration_hash"],
            subject.V1_PREREGISTRATION_HASH,
        )

    def test_matching_successor_remains_blocked_after_local_closure(self):
        document = self._build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertEqual(
            document["decision"],
            "SUCCESSOR_PREREGISTERED_LOCAL_INPUT_CHAIN_CLOSED_NOT_BOUND",
        )
        self.assertTrue(document["facts"]["local_blocker_closure_verified"])
        self.assertFalse(document["authority"]["shadow_consumer_activation_allowed"])

    def test_exactly_three_local_blockers_are_closed(self):
        document = self._build()
        self.assertEqual(
            [item["blocker"] for item in document["closed_local_blockers"]],
            [item["blocker"] for item in subject.CLOSED_LOCAL_BLOCKERS],
        )
        self.assertTrue(
            all(item["closure_verified"] for item in document["closed_local_blockers"])
        )
        for item in document["closed_local_blockers"]:
            self.assertNotIn(item["blocker"], document["blockers"])

    def test_external_runtime_and_current_blockers_remain_exact(self):
        document = self._build()
        self.assertEqual(document["blockers"], subject.FIXED_REMAINING_BLOCKERS)
        for blocker in (
            "provider_dataset_key_control_unproven",
            "external_provider_data_issuance_unproven",
            "provider_replay_registry_unchecked",
            "external_time_authority_unauthenticated",
            "shadow_application_consumer_missing",
            "risk_service_adapter_contract_not_versioned",
            "independent_shadow_review_missing",
            "current_switch_unauthorized",
        ):
            self.assertIn(blocker, document["blockers"])

    def test_v1_tamper_or_manifest_drift_fails_local_closure(self):
        tampered = copy.deepcopy(self.v1_document)
        tampered["decision"] = "ALTERED"
        tampered = seal_strict_canonical_document(tampered, "preregistration_hash")
        drifted = copy.deepcopy(self.v1_manifest)
        drifted["adapter_v1"] = "0" * 64
        for overrides in (
            {"v1_document": tampered},
            {"v1_manifest": drifted},
        ):
            with self.subTest(overrides=tuple(overrides)):
                document = self._build(**overrides)
                self.assertEqual(document["status"], "BLOCKED")
                self.assertFalse(document["facts"]["local_blocker_closure_verified"])
                self.assertEqual(document["decision"], "BLOCKED_SOURCE_OR_SCHEMA_DRIFT")

    def test_successor_hash_drift_adds_blocker_without_activation(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["native_cutoff_manifest_v1"] = "0" * 64
        document = self._build(manifest=manifest)
        self.assertIn(
            "successor_implementation_fingerprint_mismatch", document["blockers"]
        )
        self.assertFalse(document["facts"]["local_blocker_closure_verified"])
        self.assertFalse(document["authority"]["shadow_consumer_activation_allowed"])

    def test_manifest_missing_extra_and_type_aliases_fail_closed(self):
        missing = copy.deepcopy(self.manifest)
        missing.pop("session_freshness_v1")
        extra = copy.deepcopy(self.manifest)
        extra["unknown"] = "0" * 64
        alias = copy.deepcopy(self.manifest)
        alias["native_cutoff_manifest_v1"] = True
        for manifest in (missing, extra, alias, [], None):
            with self.subTest(manifest=manifest):
                document = self._build(manifest=manifest)
                self.assertIn(
                    "successor_implementation_manifest_contract_invalid",
                    document["blockers"],
                )
                self.assertFalse(document["facts"]["local_blocker_closure_verified"])

    def test_required_shadow_inputs_are_versioned_and_exclude_ui_projection(self):
        document = self._build()
        inputs = {
            item["input"]: item["schema_version"]
            for item in document["required_shadow_input_schemas"]
        }
        self.assertEqual(set(inputs), {
            "dual_source_receipt",
            "portfolio_risk_adapter",
            "legacy_matrix_derivation_binding",
            "native_cutoff_manifest",
            "session_freshness_registration",
            "session_freshness_evaluation",
        })
        self.assertNotIn("public_projection", inputs)
        self.assertNotIn("ui_card", inputs)

    def test_activation_order_starts_with_external_trust_and_current_is_last(self):
        document = self._build()
        self.assertEqual(document["activation_order"], subject.ACTIVATION_ORDER)
        self.assertEqual(
            document["activation_order"][0],
            "BIND_AUTHENTICATED_PROVIDER_IDENTITY_KEY_CONTROL_AND_DATA_ISSUANCE",
        )
        self.assertEqual(
            document["activation_order"][-1],
            "SEPARATELY_AUTHORIZE_CURRENT_SWITCH",
        )

    def test_legacy_shadow_signature_remains_unmodified_and_insufficient(self):
        parameters = set(inspect.signature(build_shadow_portfolio_risk).parameters)
        self.assertEqual(
            parameters,
            {"candidate", "backtest_report", "correlation_matrix", "hypothetical_equity"},
        )
        for required in (
            "dual_source_receipt",
            "portfolio_risk_adapter",
            "native_cutoff_manifest",
            "session_freshness_evaluation",
        ):
            self.assertNotIn(required, parameters)

    def test_reuse_plan_does_not_duplicate_identity_or_attestation_stacks(self):
        document = self._build()
        decisions = {
            item["capability"]: item["decision"] for item in document["reuse_plan"]
        }
        self.assertIn("REUSE_EXISTING", decisions["PROVIDER_IDENTITY_AND_KEY_LIFECYCLE"])
        self.assertEqual(
            decisions["SHADOW_APPLICATION_CONSUMER"],
            "NEW_VERSIONED_CONSUMER_V2_REQUIRED",
        )
        self.assertFalse(document["facts"]["provider_identity_stack_duplicated"])
        self.assertFalse(document["facts"]["dataset_attestation_stack_duplicated"])

    def test_preregistration_does_not_replace_mount_or_route_consumers(self):
        document = self._build()
        self.assertFalse(document["facts"]["legacy_shadow_replaced"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])
        self.assertFalse(document["facts"]["server_route_registered"])
        self.assertFalse(document["facts"]["ui_mounted"])
        self.assertFalse(document["facts"]["runtime_assets_accessed"])

    def test_exact_verifier_rejects_resealed_status_authority_and_type_tamper(self):
        document = self._build()
        verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
            document,
            self.v1_document,
            self.v1_manifest,
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
        type_tamper["source"]["successor_implementation_fingerprints_match"] = 1
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(
                    tampered, "preregistration_hash"
                )
                result = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
                    resealed,
                    self.v1_document,
                    self.v1_manifest,
                    self.manifest,
                )
                self.assertEqual(result["status"], "BLOCK")
                self.assertEqual(result["preregistration_status"], "UNKNOWN")

    def test_inputs_are_not_mutated(self):
        expected_v1 = copy.deepcopy(self.v1_document)
        expected_v1_manifest = copy.deepcopy(self.v1_manifest)
        expected_manifest = copy.deepcopy(self.manifest)
        self._build()
        self.assertEqual(self.v1_document, expected_v1)
        self.assertEqual(self.v1_manifest, expected_v1_manifest)
        self.assertEqual(self.manifest, expected_manifest)

    def test_schema_fingerprint_authority_and_exports_are_locked(self):
        document = self._build()
        verification = subject.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v2(
            document,
            self.v1_document,
            self.v1_manifest,
            self.manifest,
        )
        self.assertEqual(document["schema_version"], subject.PREREGISTRATION_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            subject.PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", str(document))


if __name__ == "__main__":
    unittest.main()
