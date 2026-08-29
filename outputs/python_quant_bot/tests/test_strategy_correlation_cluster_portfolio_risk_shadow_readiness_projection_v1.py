from __future__ import annotations

import ast
import copy
import inspect
import json
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1
    as contract,
)
import tests.test_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v4 as preregistration_test_module
import tests.test_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3 as readiness_test_module


class StrategyCorrelationClusterPortfolioRiskShadowReadinessProjectionV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        readiness_type = getattr(
            readiness_test_module,
            "StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV3Tests",
        )
        self.readiness_case = readiness_type(methodName="test_build_is_deterministic")
        self.readiness_case.setUp()
        self.readiness_document = self.readiness_case.document
        self.readiness_context = {
            "readiness_v2": self.readiness_case.readiness_v2,
            "trusted_clock_attestation": self.readiness_case.clock_attestation,
            "readiness_v2_verification_context": (
                self.readiness_case.readiness_v2_context
            ),
            "trusted_clock_verification_context": self.readiness_case.clock_context,
        }

        preregistration_type = getattr(
            preregistration_test_module,
            "StrategyCorrelationClusterPortfolioRiskShadowConsumerPreregistrationV4Tests",
        )
        self.preregistration_case = preregistration_type(methodName="test_build_is_deterministic")
        self.preregistration_case.setUp()
        self.preregistration_document = self.preregistration_case.document
        self.preregistration_context = {
            "preregistration_v3": self.preregistration_case.preregistration_v3,
            "v3_verification_context": self.preregistration_case.v3_context,
            "current_implementation_sha256": self.preregistration_case.manifest,
        }
        self.document = self.build()

    def build(self, **overrides):
        values = {
            "readiness_document": self.readiness_document,
            "preregistration_document": self.preregistration_document,
            "readiness_verification_context": self.readiness_context,
            "preregistration_verification_context": self.preregistration_context,
        }
        values.update(overrides)
        with self.readiness_case.v2_case.source_verifiers():
            return contract.build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1(
                **values
            )

    def verify(self, document=None, **overrides):
        values = {
            "document": self.document if document is None else document,
            "readiness_document": self.readiness_document,
            "preregistration_document": self.preregistration_document,
            "readiness_verification_context": self.readiness_context,
            "preregistration_verification_context": self.preregistration_context,
        }
        values.update(overrides)
        with self.readiness_case.v2_case.source_verifiers():
            return contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1(
                **values
            )

    def test_valid_sources_build_observed_projection(self) -> None:
        self.assertEqual(self.document["status"], "OBSERVED")
        self.assertEqual(
            [item["stage"] for item in self.document["pipeline"]],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(self.document["pipeline"][0]["state"], contract.SOURCE_STATE)
        self.assertEqual(self.document["pipeline"][1]["state"], contract.GAP_STATE)

    def test_summary_exposes_counts_without_promoting_authority(self) -> None:
        summary = self.document["summary"]
        self.assertEqual(summary["required_input_count"], 14)
        self.assertEqual(summary["verified_input_count"], 14)
        self.assertGreaterEqual(summary["signed_clock_source_count"], 2)
        self.assertEqual(summary["closed_local_blocker_count"], 3)
        self.assertEqual(summary["preregistration_status"], "BLOCKED")
        self.assertFalse(summary["readiness_evidence_bound_to_preregistration"])
        self.assertFalse(summary["consumer_executed"])
        self.assertFalse(summary["external_time_authority_authenticated"])
        self.assertFalse(summary["current_time_established"])

    def test_source_projection_is_hash_only_and_independently_verified(self) -> None:
        source = self.document["source"]
        self.assertTrue(source["readiness_envelope_exactly_verified"])
        self.assertTrue(source["preregistration_exactly_verified"])
        self.assertTrue(source["contract_pin_aligned"])
        self.assertRegex(source["readiness_envelope_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(source["preregistration_hash"], r"^[0-9a-f]{64}$")
        self.assertFalse(source["readiness_evidence_bound_to_preregistration"])

    def test_projection_redacts_documents_keys_signatures_and_contexts(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        for forbidden in (
            "public_key_base64",
            "signature_base64",
            "trusted_clock_attestation",
            "readiness_verification_context",
            "preregistration_verification_context",
            "readiness_v2_verification_context",
            "trusted_clock_verification_context",
            "authority_public_keys_by_id",
            "current_implementation_sha256",
            '"receipts"',
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertTrue(
            all(value is False for value in self.document["facts"].values())
        )

    def test_all_authority_remains_denied(self) -> None:
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def test_public_verifier_accepts_exact_rebuild(self) -> None:
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["projection_exactly_verified"])
        self.assertFalse(result["runtime_consumer_mounted"])

    def test_public_verifier_rejects_projection_tamper(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["summary"]["consumer_executed"] = True
        result = self.verify(document=changed)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["current_admission_allowed"])

    def test_not_supplied_is_neutral_and_deterministic(self) -> None:
        first = contract.build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1()
        second = contract.build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "NOT_SUPPLIED")
        self.assertEqual(first["pipeline"][0]["state"], "NOT_SUPPLIED")
        self.assertEqual(first["pipeline"][3]["state"], "UNAUTHORIZED")

    def test_tampered_readiness_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.readiness_document)
        changed["facts"]["current_time_established"] = True
        result = self.build(readiness_document=changed)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["pipeline"][3]["state"], "UNAUTHORIZED")

    def test_wrong_readiness_context_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.readiness_context)
        changed["trusted_clock_verification_context"]["expected_registration_hash"] = (
            "0" * 64
        )
        result = self.build(readiness_verification_context=changed)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_tampered_preregistration_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.preregistration_document)
        changed["facts"]["readiness_envelope_v3_evidence_bound"] = True
        result = self.build(preregistration_document=changed)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_wrong_preregistration_manifest_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.preregistration_context)
        changed["current_implementation_sha256"][
            "shadow_input_readiness_envelope_v3"
        ] = "0" * 64
        result = self.build(preregistration_verification_context=changed)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_context_extension_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.readiness_context)
        changed["extra"] = None
        self.assertEqual(
            self.build(readiness_verification_context=changed)["status"], "UNKNOWN"
        )
        preregistration_changed = copy.deepcopy(self.preregistration_context)
        preregistration_changed["extra"] = None
        self.assertEqual(
            self.build(
                preregistration_verification_context=preregistration_changed
            )["status"],
            "UNKNOWN",
        )

    def test_contract_pin_misalignment_fails_closed_to_unknown(self) -> None:
        changed = copy.deepcopy(self.preregistration_document)
        changed["contract_pins"]["readiness_v3_required_input_count"] = 13
        self.assertEqual(
            self.build(preregistration_document=changed)["status"], "UNKNOWN"
        )

    def test_build_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        readiness = copy.deepcopy(self.readiness_document)
        preregistration = copy.deepcopy(self.preregistration_document)
        readiness_context = copy.deepcopy(self.readiness_context)
        preregistration_context = copy.deepcopy(self.preregistration_context)
        snapshots = copy.deepcopy(
            (readiness, preregistration, readiness_context, preregistration_context)
        )
        first = self.build(
            readiness_document=readiness,
            preregistration_document=preregistration,
            readiness_verification_context=readiness_context,
            preregistration_verification_context=preregistration_context,
        )
        second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(
            snapshots,
            (readiness, preregistration, readiness_context, preregistration_context),
        )

    def test_production_module_has_no_runtime_imports(self) -> None:
        tree = ast.parse(inspect.getsource(contract))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        self.assertFalse(
            any(
                module.endswith((".portfolio_shadow_risk", ".risk_service", ".server"))
                for module in modules
            )
        )

    def test_output_has_no_ready_profit_or_execution_claim(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn('"READY"', encoded)
        self.assertFalse(self.document["facts"]["profitability_proof"])
        self.assertFalse(self.document["facts"]["runtime_consumer_mounted"])
        self.assertFalse(self.document["facts"]["risk_service_invoked"])

    def test_schema_fingerprint_and_api_are_version_locked(self) -> None:
        self.assertEqual(
            self.document["schema_version"], contract.PROJECTION_SCHEMA_VERSION
        )
        self.assertEqual(self.document["static_fingerprint"], contract.STATIC_FINGERPRINT)
        self.assertEqual(
            set(contract.__all__),
            {
                "GAP_STATE",
                "MATURITY_STATE",
                "PERMISSION_STATE",
                "PROJECTION_SCHEMA_VERSION",
                "SOURCE_STATE",
                "STATIC_FINGERPRINT",
                "VERIFICATION_SCHEMA_VERSION",
                "build_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1",
                "verify_strategy_correlation_cluster_portfolio_risk_shadow_readiness_projection_v1",
            },
        )


if __name__ == "__main__":
    unittest.main()
