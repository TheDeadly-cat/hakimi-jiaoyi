from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 import (
    BINDING_SCHEMA_VERSION,
    BINDING_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1,
    verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_provider_dataset_content_attestation_v1 import (
    StrategyCorrelationProviderDatasetContentAttestationV1Tests,
)


class StrategyCorrelationClusterPortfolioRiskLegacyMatrixDerivationBindingV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = StrategyCorrelationProviderDatasetContentAttestationV1Tests(
            methodName="runTest"
        )
        self.fixture.setUp()
        self.composition_context = self.fixture.composition_context
        self.matrix_replay = self.composition_context["matrix_replay"]
        self.completed_price_input = self.matrix_replay["completed_price_input"]
        self.derivation_receipt = self.composition_context["derivation_receipt"]
        self.composition_document = self.fixture.composition_document
        self.registration = self.fixture.registration
        self.public_key = self.fixture.dataset_public_key_base64
        self.attestation_receipt = self.fixture.receipt
        with self.fixture.source_verifiers():
            self.attestation_verification = self.fixture.evaluate()
        preregistration = self.matrix_replay["preregistration"]
        payloads = {
            item["symbol"]: {"rows": item["price_rows"]}
            for item in self.completed_price_input["datasets"]
        }
        self.legacy_matrix = build_correlation_matrix(
            payloads,
            lookback=preregistration["lookback_observations"],
            minimum_overlap=preregistration["minimum_pair_overlap"],
        )
        self.base_inputs = {
            "legacy_correlation_matrix": self.legacy_matrix,
            "completed_price_input": self.completed_price_input,
            "matrix_replay": self.matrix_replay,
            "derivation_receipt": self.derivation_receipt,
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "dataset_attestation_verification": self.attestation_verification,
            "dataset_attestation_registration": self.registration,
            "provider_dataset_public_key_base64": self.public_key,
            "dataset_attestation_receipt": self.attestation_receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_attestation_hash": self.attestation_receipt["attestation_hash"],
        }

    def _build(self, **overrides):
        values = copy.deepcopy(self.base_inputs)
        values.update(copy.deepcopy(overrides))
        with self.fixture.source_verifiers():
            return (
                build_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
                    values.pop("legacy_correlation_matrix"),
                    values.pop("completed_price_input"),
                    values.pop("matrix_replay"),
                    values.pop("derivation_receipt"),
                    values.pop("composition_document"),
                    values.pop("composition_context"),
                    values.pop("dataset_attestation_verification"),
                    values.pop("dataset_attestation_registration"),
                    values.pop("provider_dataset_public_key_base64"),
                    values.pop("dataset_attestation_receipt"),
                    **values,
                )
            )

    def _verify(self, document):
        values = copy.deepcopy(self.base_inputs)
        with self.fixture.source_verifiers():
            return verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
                document,
                values.pop("legacy_correlation_matrix"),
                values.pop("completed_price_input"),
                values.pop("matrix_replay"),
                values.pop("derivation_receipt"),
                values.pop("composition_document"),
                values.pop("composition_context"),
                values.pop("dataset_attestation_verification"),
                values.pop("dataset_attestation_registration"),
                values.pop("provider_dataset_public_key_base64"),
                values.pop("dataset_attestation_receipt"),
                **values,
            )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskLegacyMatrixDerivationBindingV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskLegacyMatrixDerivationBindingV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_gap_proof_signed_composition_did_not_bind_legacy_matrix_hash(self):
        self.assertNotIn("legacy_matrix_hash", self.composition_document)
        self.assertNotIn("legacy_matrix_hash", self.attestation_receipt)
        self.assertNotIn("legacy_matrix_hash", self.attestation_verification)
        self.assertEqual(self.legacy_matrix["status"], "PASS")

    def test_valid_binding_closes_local_derivation_only(self):
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "LEGACY_MATRIX_BOUND_TO_SIGNED_CONTENT_CLAIM_EXTERNAL_TRUST_UNPROVEN",
        )
        self.assertEqual(
            document["source"]["completed_price_input_hash"],
            self.completed_price_input["input_hash"],
        )
        self.assertEqual(
            document["source"]["legacy_matrix_hash"],
            self.legacy_matrix["matrix_hash"],
        )
        self.assertTrue(document["facts"]["legacy_matrix_deterministically_rebuilt"])
        self.assertTrue(
            document["facts"]["signed_dataset_content_claim_verified"]
        )
        self.assertFalse(
            document["facts"]["external_provider_dataset_key_control_verified"]
        )

    def test_resealed_legacy_matrix_value_tamper_blocks_exact_rebuild(self):
        legacy = copy.deepcopy(self.legacy_matrix)
        first_key = sorted(legacy["pairs"])[0]
        legacy["pairs"][first_key]["correlation"] = 0.12345
        legacy = seal_strict_canonical_document(legacy, "matrix_hash")
        document = self._build(legacy_correlation_matrix=legacy)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("legacy_matrix_exact_rebuild", document["blockers"])

    def test_completed_price_tamper_breaks_input_replay_and_lineage(self):
        completed = copy.deepcopy(self.completed_price_input)
        completed["datasets"][0]["price_rows"][0]["close"] += 1.0
        document = self._build(completed_price_input=completed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("completed_price_input_exact", document["blockers"])
        self.assertIn("matrix_replay_exact", document["blockers"])

    def test_resealed_composition_lineage_tamper_blocks(self):
        composition = copy.deepcopy(self.composition_document)
        composition["source_completed_price_input_hash"] = "0" * 64
        composition = seal_strict_canonical_document(
            composition,
            "composition_hash",
        )
        document = self._build(composition_document=composition)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("calendar_provider_composition_exact", document["blockers"])
        self.assertIn("signed_dataset_content_claim_exact", document["blockers"])
        self.assertIn("completed_price_hash_lineage", document["blockers"])

    def test_attestation_verification_tamper_blocks_signed_claim(self):
        attestation = copy.deepcopy(self.attestation_verification)
        attestation["source_composition_hash"] = "0" * 64
        attestation = seal_strict_canonical_document(
            attestation,
            "verification_hash",
        )
        document = self._build(dataset_attestation_verification=attestation)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("signed_dataset_content_claim_exact", document["blockers"])

    def test_external_trust_promotion_is_rejected(self):
        attestation = copy.deepcopy(self.attestation_verification)
        attestation["facts"][
            "external_provider_dataset_key_control_verified"
        ] = True
        attestation = seal_strict_canonical_document(
            attestation,
            "verification_hash",
        )
        document = self._build(dataset_attestation_verification=attestation)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("signed_dataset_content_claim_exact", document["blockers"])
        self.assertIn("external_trust_not_promoted", document["blockers"])

    def test_scalar_type_alias_in_legacy_matrix_blocks(self):
        legacy = copy.deepcopy(self.legacy_matrix)
        legacy["lookback"] = 60.0
        legacy = seal_strict_canonical_document(legacy, "matrix_hash")
        document = self._build(legacy_correlation_matrix=legacy)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("legacy_matrix_exact_rebuild", document["blockers"])

    def test_existing_attestation_blockers_do_not_promote_or_block_local_binding(self):
        self.assertGreater(len(self.attestation_verification["blockers"]), 0)
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertFalse(document["facts"]["provider_replay_registry_checked"])
        self.assertFalse(document["facts"]["observation_admission_allowed"])
        self.assertFalse(document["facts"]["profitability_verified"])
        self.assertFalse(
            document["authority"]["shadow_consumer_activation_allowed"]
        )

    def test_inputs_are_unmutated_and_raw_documents_are_not_embedded(self):
        expected = copy.deepcopy(self.base_inputs)
        document = self._build()
        self.assertEqual(self.base_inputs, expected)
        keys = self._all_keys(document)
        for forbidden in (
            "price_rows",
            "datasets",
            "correlation_matrix",
            "signature_base64",
            "provider_dataset_public_key_base64",
            "composition_state",
        ):
            self.assertNotIn(forbidden, keys)
        self.assertFalse(document["facts"]["completed_price_rows_embedded"])
        self.assertFalse(document["facts"]["matrix_replay_embedded"])
        self.assertFalse(document["facts"]["attestation_receipt_embedded"])

    def test_exact_verifier_rejects_resealed_status_authority_and_type_tamper(self):
        document = self._build()
        self.assertEqual(self._verify(document)["status"], "PASS")
        variants = []
        status_tamper = copy.deepcopy(document)
        status_tamper["decision"] = "READY"
        variants.append(status_tamper)
        authority_tamper = copy.deepcopy(document)
        authority_tamper["authority"]["paper_authorized"] = True
        variants.append(authority_tamper)
        type_tamper = copy.deepcopy(document)
        type_tamper["portfolio_matrix"]["lookback_observations"] = 60.0
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(tampered, "binding_hash")
                verification = self._verify(resealed)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["binding_decision"], "UNKNOWN")

    def test_schema_fingerprint_and_authority_are_research_only(self):
        document = self._build()
        verification = self._verify(document)
        self.assertEqual(document["schema_version"], BINDING_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            BINDING_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(document["facts"]["runtime_assets_accessed"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])


if __name__ == "__main__":
    unittest.main()
