from __future__ import annotations

import copy
from datetime import date, timedelta
import unittest

from exchange_terminal.services.portfolio_risk import build_correlation_matrix
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1 import (
    CLUSTER_SOURCE_ROLE,
    DUAL_SOURCE_RECEIPT_SCHEMA_VERSION,
    DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION,
    LEGACY_SOURCE_ROLE,
    SOURCE_ENVELOPE_SCHEMA_VERSION,
    SOURCE_ENVELOPE_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_portfolio_risk_correlation_source_envelope_v1,
    build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1,
    verify_portfolio_risk_correlation_source_envelope_v1,
    verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cluster_complete_link import (
    StrategyCorrelationClusterCompleteLinkTests,
)


class StrategyCorrelationClusterPortfolioRiskDualSourceReceiptV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        symbols = ["A", "B", "C", "D"]
        start = date(2026, 6, 22)
        payloads = {}
        for symbol_index, symbol in enumerate(symbols):
            rows = []
            for index in range(61):
                current = start + timedelta(days=index)
                close = (
                    80.0
                    + symbol_index * 17.0
                    + index * (0.08 + symbol_index * 0.017)
                    + index * index * (0.009 + symbol_index * 0.002)
                    + (index % (5 + symbol_index)) * 0.013
                )
                rows.append(
                    {
                        "date": current.isoformat(),
                        "close": close,
                        "complete": True,
                    }
                )
            payloads[symbol] = {"rows": rows}
        self.legacy_payload = build_correlation_matrix(
            payloads,
            lookback=60,
            minimum_overlap=40,
        )
        self.cluster_payload = (
            StrategyCorrelationClusterCompleteLinkTests._matrix(ac=0.92)
        )
        self.symbols = symbols
        self.cutoff = "2026-08-21T00:00:00Z"
        self.legacy_provider = "SYNTHETIC.LEGACY"
        self.cluster_provider = "SYNTHETIC.CLUSTER"
        self.legacy_envelope = (
            build_portfolio_risk_correlation_source_envelope_v1(
                self.legacy_payload,
                source_role=LEGACY_SOURCE_ROLE,
                provider_id=self.legacy_provider,
                observation_cutoff_utc=self.cutoff,
            )
        )
        self.cluster_envelope = (
            build_portfolio_risk_correlation_source_envelope_v1(
                self.cluster_payload,
                source_role=CLUSTER_SOURCE_ROLE,
                provider_id=self.cluster_provider,
                observation_cutoff_utc=self.cutoff,
            )
        )

    def _receipt(self, **overrides):
        values = {
            "legacy_payload": self.legacy_payload,
            "legacy_envelope": self.legacy_envelope,
            "cluster_payload": self.cluster_payload,
            "cluster_envelope": self.cluster_envelope,
            "expected_symbols": self.symbols,
            "expected_observation_cutoff_utc": self.cutoff,
            "expected_legacy_provider_id": self.legacy_provider,
            "expected_cluster_provider_id": self.cluster_provider,
        }
        values.update(overrides)
        return (
            build_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
                values.pop("legacy_payload"),
                values.pop("legacy_envelope"),
                values.pop("cluster_payload"),
                values.pop("cluster_envelope"),
                **values,
            )
        )

    def _verify_receipt(self, document):
        return verify_strategy_correlation_cluster_portfolio_risk_dual_source_receipt_v1(
            document,
            self.legacy_payload,
            self.legacy_envelope,
            self.cluster_payload,
            self.cluster_envelope,
            expected_symbols=self.symbols,
            expected_observation_cutoff_utc=self.cutoff,
            expected_legacy_provider_id=self.legacy_provider,
            expected_cluster_provider_id=self.cluster_provider,
        )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskDualSourceReceiptV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskDualSourceReceiptV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_gap_proof_payloads_have_no_native_observation_cutoff(self):
        self.assertNotIn("observation_cutoff_utc", self.legacy_payload)
        self.assertNotIn("observation_cutoff_utc", self.cluster_payload)
        self.assertEqual(self.legacy_payload["status"], "PASS")
        self.assertEqual(self.cluster_payload["status"], "PASS")

    def test_legacy_envelope_seals_pass_payload_without_embedding_it(self):
        envelope = self.legacy_envelope
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(envelope["decision"], "SEALED_PROVIDER_ASSERTION")
        self.assertEqual(envelope["source"]["symbols"], self.symbols)
        self.assertEqual(envelope["source"]["lookback_observations"], 60)
        self.assertEqual(envelope["source"]["minimum_pair_overlap"], 40)
        self.assertFalse(envelope["facts"]["payload_embedded"])
        self.assertFalse(envelope["facts"]["payload_cutoff_native"])
        self.assertFalse(envelope["facts"]["provider_identity_authenticated"])

    def test_cluster_envelope_uses_existing_matrix_verifier(self):
        envelope = self.cluster_envelope
        verification = verify_portfolio_risk_correlation_source_envelope_v1(
            envelope,
            self.cluster_payload,
            source_role=CLUSTER_SOURCE_ROLE,
            provider_id=self.cluster_provider,
            observation_cutoff_utc=self.cutoff,
        )
        self.assertEqual(envelope["status"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["envelope_exactly_verified"])

    def test_invalid_metadata_and_type_aliases_block_envelopes(self):
        cases = (
            {"provider_id": "synthetic legacy"},
            {"observation_cutoff_utc": "2026-08-21"},
            {"observation_cutoff_utc": 20260821},
            {"source_role": True},
            {"return_series": 1},
        )
        for overrides in cases:
            values = {
                "source_role": LEGACY_SOURCE_ROLE,
                "provider_id": self.legacy_provider,
                "observation_cutoff_utc": self.cutoff,
            }
            values.update(overrides)
            with self.subTest(overrides=overrides):
                envelope = build_portfolio_risk_correlation_source_envelope_v1(
                    self.legacy_payload,
                    **values,
                )
                self.assertEqual(envelope["status"], "BLOCK")
                self.assertIn("source_metadata_contract", envelope["blockers"])

    def test_payload_tamper_blocks_even_if_outer_envelope_is_resealed(self):
        tampered_payload = copy.deepcopy(self.legacy_payload)
        tampered_payload["pairs"]["A|B"]["correlation"] = 0.12345
        envelope = build_portfolio_risk_correlation_source_envelope_v1(
            tampered_payload,
            source_role=LEGACY_SOURCE_ROLE,
            provider_id=self.legacy_provider,
            observation_cutoff_utc=self.cutoff,
        )
        self.assertEqual(envelope["status"], "BLOCK")
        self.assertIn("source_payload_contract", envelope["blockers"])

    def test_envelope_verifier_rejects_resealed_metadata_authority_and_type_tamper(self):
        variants = []
        metadata = copy.deepcopy(self.legacy_envelope)
        metadata["source"]["observation_cutoff_utc"] = "2026-08-20T00:00:00Z"
        variants.append(metadata)
        authority = copy.deepcopy(self.legacy_envelope)
        authority["authority"]["paper_authorized"] = True
        variants.append(authority)
        scalar_type = copy.deepcopy(self.legacy_envelope)
        scalar_type["source"]["lookback_observations"] = 60.0
        variants.append(scalar_type)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(
                    tampered,
                    "envelope_hash",
                )
                verification = verify_portfolio_risk_correlation_source_envelope_v1(
                    resealed,
                    self.legacy_payload,
                    source_role=LEGACY_SOURCE_ROLE,
                    provider_id=self.legacy_provider,
                    observation_cutoff_utc=self.cutoff,
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["envelope_decision"], "UNKNOWN")

    def test_aligned_receipt_is_provider_assertion_only(self):
        receipt = self._receipt()
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(
            receipt["decision"],
            "DUAL_SOURCE_PROVIDER_ASSERTIONS_ALIGNED",
        )
        self.assertEqual(
            receipt["source"]["shared"]["observation_cutoff_utc"],
            self.cutoff,
        )
        self.assertEqual(receipt["source"]["shared"]["symbols"], self.symbols)
        self.assertEqual(receipt["source"]["shared"]["lookback_observations"], 60)
        self.assertEqual(receipt["source"]["shared"]["minimum_pair_overlap"], 40)
        self.assertTrue(receipt["facts"]["provider_assertion_only"])
        self.assertFalse(receipt["facts"]["provider_identity_authenticated"])
        self.assertFalse(receipt["facts"]["payload_cutoff_native"])

    def test_cutoff_mismatch_blocks_against_external_expectation(self):
        mismatched = build_portfolio_risk_correlation_source_envelope_v1(
            self.cluster_payload,
            source_role=CLUSTER_SOURCE_ROLE,
            provider_id=self.cluster_provider,
            observation_cutoff_utc="2026-08-20T00:00:00Z",
        )
        receipt = self._receipt(cluster_envelope=mismatched)
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("cluster_source_envelope_exact", receipt["blockers"])
        self.assertIn("shared_observation_cutoff", receipt["blockers"])

    def test_symbol_universe_mismatch_blocks(self):
        receipt = self._receipt(expected_symbols=["A", "B", "C"])
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("shared_symbol_universe", receipt["blockers"])

    def test_lookback_mismatch_blocks_after_valid_legacy_reseal(self):
        payload = copy.deepcopy(self.legacy_payload)
        payload["lookback"] = 59
        payload = seal_strict_canonical_document(payload, "matrix_hash")
        envelope = build_portfolio_risk_correlation_source_envelope_v1(
            payload,
            source_role=LEGACY_SOURCE_ROLE,
            provider_id=self.legacy_provider,
            observation_cutoff_utc=self.cutoff,
        )
        self.assertEqual(envelope["status"], "PASS")
        receipt = self._receipt(
            legacy_payload=payload,
            legacy_envelope=envelope,
        )
        self.assertEqual(receipt["status"], "BLOCK")
        self.assertIn("shared_lookback_window", receipt["blockers"])

    def test_expected_metadata_aliases_fail_closed(self):
        for overrides in (
            {"expected_symbols": ["A", "B", "C", 4]},
            {"expected_observation_cutoff_utc": True},
            {"expected_legacy_provider_id": "synthetic"},
            {"expected_return_series": True},
        ):
            with self.subTest(overrides=overrides):
                receipt = self._receipt(**overrides)
                self.assertEqual(receipt["status"], "BLOCK")
                self.assertIn("expected_metadata_contract", receipt["blockers"])

    def test_receipt_exact_verifier_rejects_resealed_permission_and_type_tamper(self):
        receipt = self._receipt()
        self.assertEqual(self._verify_receipt(receipt)["status"], "PASS")
        variants = []
        permission = copy.deepcopy(receipt)
        permission["authority"]["current_admission_allowed"] = True
        variants.append(permission)
        scalar_type = copy.deepcopy(receipt)
        scalar_type["source"]["shared"]["lookback_observations"] = 60.0
        variants.append(scalar_type)
        for tampered in variants:
            with self.subTest(tampered=tampered):
                resealed = seal_strict_canonical_document(tampered, "receipt_hash")
                verification = self._verify_receipt(resealed)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["receipt_decision"], "UNKNOWN")

    def test_inputs_are_unmutated_and_raw_payloads_are_not_embedded(self):
        inputs = [
            self.legacy_payload,
            self.legacy_envelope,
            self.cluster_payload,
            self.cluster_envelope,
        ]
        expected = copy.deepcopy(inputs)
        receipt = self._receipt()
        self.assertEqual(inputs, expected)
        keys = self._all_keys(receipt)
        for forbidden in (
            "pairs",
            "pearson_correlation",
            "correlation",
            "cluster_results",
        ):
            self.assertNotIn(forbidden, keys)
        self.assertFalse(receipt["facts"]["payloads_embedded"])
        self.assertFalse(receipt["facts"]["source_envelopes_embedded"])

    def test_schema_fingerprint_authority_and_verifier_exports_are_locked(self):
        receipt = self._receipt()
        verification = self._verify_receipt(receipt)
        self.assertEqual(
            self.legacy_envelope["schema_version"],
            SOURCE_ENVELOPE_SCHEMA_VERSION,
        )
        envelope_verification = verify_portfolio_risk_correlation_source_envelope_v1(
            self.legacy_envelope,
            self.legacy_payload,
            source_role=LEGACY_SOURCE_ROLE,
            provider_id=self.legacy_provider,
            observation_cutoff_utc=self.cutoff,
        )
        self.assertEqual(
            envelope_verification["schema_version"],
            SOURCE_ENVELOPE_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(receipt["schema_version"], DUAL_SOURCE_RECEIPT_SCHEMA_VERSION)
        self.assertEqual(receipt["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"],
            DUAL_SOURCE_RECEIPT_VERIFICATION_SCHEMA_VERSION,
        )
        self.assertTrue(receipt["authority"]["descriptive_only"])
        for key, value in receipt["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(receipt["facts"]["runtime_consumer_bound"])
        self.assertTrue(receipt["facts"]["shadow_consumer_input_candidate"])


if __name__ == "__main__":
    unittest.main()
