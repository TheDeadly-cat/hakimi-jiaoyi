from __future__ import annotations

import copy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1 import (
    CUTOFF_UTC_SEMANTICS,
    MANIFEST_SCHEMA_VERSION,
    MANIFEST_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1,
    verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_provider_dataset_content_attestation_v1 import (
    StrategyCorrelationProviderDatasetContentAttestationV1Tests,
)


class StrategyCorrelationClusterPortfolioRiskNativeCutoffManifestV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = StrategyCorrelationProviderDatasetContentAttestationV1Tests(
            methodName="runTest"
        )
        self.fixture.setUp()
        self.context = self.fixture.composition_context
        self.replay = self.context["matrix_replay"]
        self.completed = self.replay["completed_price_input"]
        self.derivation = self.context["derivation_receipt"]
        self.composition = self.fixture.composition_document
        self.cutoff_utc = f"{self.completed['cutoff_date']}T00:00:00Z"
        self.base_inputs = {
            "completed_price_input": self.completed,
            "matrix_replay": self.replay,
            "derivation_receipt": self.derivation,
            "composition_document": self.composition,
            "composition_context": self.context,
            "expected_observation_cutoff_utc": self.cutoff_utc,
        }

    def _build(self, **overrides):
        values = copy.deepcopy(self.base_inputs)
        values.update(copy.deepcopy(overrides))
        with self.fixture.source_verifiers():
            return build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                values.pop("completed_price_input"),
                values.pop("matrix_replay"),
                values.pop("derivation_receipt"),
                values.pop("composition_document"),
                values.pop("composition_context"),
                **values,
            )

    def _verify(self, document):
        values = copy.deepcopy(self.base_inputs)
        with self.fixture.source_verifiers():
            return verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
                document,
                values.pop("completed_price_input"),
                values.pop("matrix_replay"),
                values.pop("derivation_receipt"),
                values.pop("composition_document"),
                values.pop("composition_context"),
                **values,
            )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskNativeCutoffManifestV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskNativeCutoffManifestV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_gap_proof_matrix_payloads_lack_cutoff_but_completed_input_has_it(self):
        self.assertNotIn("cutoff_date", self.replay["correlation_matrix"])
        self.assertIn("cutoff_date", self.completed)
        self.assertEqual(
            self.completed["cutoff_date"],
            self.context["calendar_session_verification"]["last_observation_date"],
        )

    def test_valid_manifest_binds_native_cutoff_to_verified_sessions(self):
        document = self._build()
        self.assertEqual(document["status"], "PASS")
        self.assertEqual(
            document["decision"],
            "NATIVE_SESSION_LABEL_CUTOFF_VERIFIED_NOT_FRESHNESS",
        )
        self.assertEqual(
            document["cutoff"]["session_label_date"],
            self.completed["cutoff_date"],
        )
        self.assertEqual(
            document["cutoff"]["observation_cutoff_utc"],
            self.cutoff_utc,
        )
        self.assertEqual(document["cutoff"]["utc_semantics"], CUTOFF_UTC_SEMANTICS)
        self.assertEqual(len(document["datasets"]), self.completed["dataset_count"])
        self.assertTrue(document["facts"]["cutoff_native_to_completed_price_input"])
        self.assertTrue(document["facts"]["all_registered_sessions_completed"])
        self.assertEqual(
            document["source"]["calendar_session_verification_hash"],
            self.context["calendar_session_verification"]["verification_hash"],
        )
        self.assertRegex(
            document["source"]["calendar_session_verification_hash"],
            r"^[0-9a-f]{64}$",
        )
        self.assertEqual(
            document["source"]["calendar_registration_hash"],
            self.composition["source_calendar_registration_hash"],
        )

    def test_calendar_registration_hash_context_drift_is_blocked(self):
        from copy import deepcopy

        context = deepcopy(self.context)
        context["calendar_verification_bundle"][
            "expected_calendar_registration_hash"
        ] = "f" * 64
        document = self._build(composition_context=context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("calendar_session_cutoff", document["blockers"])

    def test_cutoff_utc_must_be_exact_midnight_session_label_encoding(self):
        for value in (
            self.completed["cutoff_date"],
            f"{self.completed['cutoff_date']}T16:00:00Z",
            True,
            None,
        ):
            with self.subTest(value=value):
                document = self._build(expected_observation_cutoff_utc=value)
                self.assertEqual(document["status"], "BLOCK")
                self.assertIn(
                    "expected_midnight_cutoff_alignment",
                    document["blockers"],
                )

    def test_wrong_but_well_formed_expected_date_blocks(self):
        document = self._build(
            expected_observation_cutoff_utc="2026-03-01T00:00:00Z"
        )
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("expected_midnight_cutoff_alignment", document["blockers"])

    def test_completed_cutoff_tamper_breaks_native_and_replay_evidence(self):
        completed = copy.deepcopy(self.completed)
        completed["cutoff_date"] = "2026-03-01"
        document = self._build(completed_price_input=completed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("completed_price_input_exact", document["blockers"])
        self.assertIn("matrix_replay_exact", document["blockers"])
        self.assertIn("native_completed_price_cutoff", document["blockers"])

    def test_single_symbol_date_grid_tamper_blocks(self):
        completed = copy.deepcopy(self.completed)
        completed["datasets"][0]["price_rows"][-1]["date"] = "2026-03-01"
        document = self._build(completed_price_input=completed)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("all_symbol_date_grids_exact", document["blockers"])
        self.assertIn("native_completed_price_cutoff", document["blockers"])

    def test_calendar_last_session_tamper_blocks(self):
        context = copy.deepcopy(self.context)
        context["calendar_session_verification"][
            "last_observation_date"
        ] = "2026-03-01"
        document = self._build(composition_context=context)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("calendar_provider_composition_exact", document["blockers"])
        self.assertIn("calendar_session_cutoff", document["blockers"])

    def test_derivation_common_index_tamper_blocks(self):
        derivation = copy.deepcopy(self.derivation)
        derivation["common_price_index_hash"] = "0" * 64
        derivation = seal_strict_canonical_document(derivation, "receipt_hash")
        document = self._build(derivation_receipt=derivation)
        self.assertEqual(document["status"], "BLOCK")
        self.assertIn("common_support_derivation_exact", document["blockers"])
        self.assertIn("common_price_index_cutoff", document["blockers"])

    def test_manifest_does_not_claim_freshness_or_timestamp_semantics(self):
        document = self._build()
        self.assertFalse(document["facts"]["freshness_policy_defined"])
        self.assertFalse(document["facts"]["freshness_evaluated"])
        self.assertFalse(document["facts"]["session_close_time_claimed"])
        self.assertFalse(document["facts"]["provider_timestamp_claimed"])
        self.assertFalse(document["facts"]["ingestion_time_claimed"])
        self.assertFalse(
            document["authority"]["shadow_consumer_activation_allowed"]
        )

    def test_inputs_are_unmutated_and_price_rows_are_redacted(self):
        expected = copy.deepcopy(self.base_inputs)
        document = self._build()
        self.assertEqual(self.base_inputs, expected)
        keys = self._all_keys(document)
        for forbidden in (
            "price_rows",
            "correlation_matrix",
            "observation_batch",
            "session_checks",
        ):
            self.assertNotIn(forbidden, keys)
        self.assertFalse(document["facts"]["price_rows_embedded"])

    def test_exact_verifier_rejects_resealed_cutoff_authority_and_type_tamper(self):
        document = self._build()
        self.assertEqual(self._verify(document)["status"], "PASS")
        variants = []
        cutoff_tamper = copy.deepcopy(document)
        cutoff_tamper["cutoff"]["observation_cutoff_utc"] = (
            "2026-03-01T00:00:00Z"
        )
        variants.append(cutoff_tamper)
        authority_tamper = copy.deepcopy(document)
        authority_tamper["authority"]["current_admission_allowed"] = True
        variants.append(authority_tamper)
        type_tamper = copy.deepcopy(document)
        type_tamper["cutoff"]["common_session_count"] = 61.0
        variants.append(type_tamper)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(tampered, "manifest_hash")
                verification = self._verify(resealed)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["manifest_decision"], "UNKNOWN")

    def test_schema_fingerprint_authority_and_verifier_are_locked(self):
        document = self._build()
        verification = self._verify(document)
        self.assertEqual(document["schema_version"], MANIFEST_SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            MANIFEST_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(document["facts"]["runtime_assets_accessed"])
        self.assertFalse(document["facts"]["runtime_consumer_bound"])


if __name__ == "__main__":
    unittest.main()
