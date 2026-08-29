from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2
    as readiness_v2_contract,
)
from exchange_terminal.application import (
    strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3
    as contract,
)
from exchange_terminal.services import trusted_clock_authority_v3 as clock_contract
import tests.test_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v2 as readiness_v2_test_module


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV3Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        case_type = getattr(
            readiness_v2_test_module,
            "StrategyCorrelationClusterPortfolioRiskShadowInputReadinessEnvelopeV2Tests",
        )
        self.v2_case = case_type(methodName="test_all_thirteen_inputs_are_locally_verified")
        self.v2_case.setUp()
        self.readiness_v2_context = {
            "readiness_v1": self.v2_case.readiness_v1,
            "portfolio_inputs": self.v2_case.portfolio_inputs,
            "readiness_v1_verification_context": self.v2_case.readiness_v1_context,
            "portfolio_verification_contexts": self.v2_case.portfolio_contexts,
        }
        self.readiness_v2 = self.v2_case.build()

        self.private_keys = {
            "TIME-A": Ed25519PrivateKey.from_private_bytes(bytes([21]) * 32),
            "TIME-B": Ed25519PrivateKey.from_private_bytes(bytes([22]) * 32),
            "TIME-C": Ed25519PrivateKey.from_private_bytes(bytes([23]) * 32),
        }
        self.key_ids = {
            "TIME-A": "time-a-readiness-v3",
            "TIME-B": "time-b-readiness-v3",
            "TIME-C": "time-c-readiness-v3",
        }
        self.public_keys = {
            authority_id: base64.b64encode(
                private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            ).decode("ascii")
            for authority_id, private_key in self.private_keys.items()
        }
        self.authorities = [
            {
                "authority_id": authority_id,
                "key_id": self.key_ids[authority_id],
                "public_key_base64": self.public_keys[authority_id],
            }
            for authority_id in ("TIME-A", "TIME-B", "TIME-C")
        ]
        self.registration = clock_contract.build_trusted_clock_authority_registration_v3(
            self.authorities,
            minimum_sources=2,
            max_receipt_age_ms=5_000,
            max_provider_spread_ms=500,
            max_local_skew_ms=5_000,
            max_receipt_issue_delay_ms=100,
            valid_from_ms=1_001_000,
            valid_until_ms=1_100_000,
            declared_at_ms=1_000_000,
        )
        self.nonce_hash = _hash_text("readiness-envelope-v3-synthetic-nonce")
        self.request_context_hash = contract.derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
            self.readiness_v2
        )
        self.receipt_a = self._clock_receipt("TIME-A", 1_010_000, 1_010_010)
        self.receipt_b = self._clock_receipt("TIME-B", 1_010_100, 1_010_110)
        self.receipts = [self.receipt_a, self.receipt_b]
        self.expected_receipt_hashes = self._expected_receipts(self.receipts)
        self.clock_attestation = self._clock_attestation()
        self.clock_context = self._clock_context()
        self.document = self._build()

    @staticmethod
    def _expected_receipts(receipts: list[dict]) -> dict[str, str]:
        return {
            receipt["authority"]["authority_id"]: receipt["receipt_hash"]
            for receipt in receipts
        }

    def _clock_receipt(
        self,
        authority_id: str,
        observed_at_ms: int,
        issued_at_ms: int,
        *,
        request_context_hash: str | None = None,
        signer_id: str | None = None,
    ) -> dict:
        unsigned = clock_contract.build_unsigned_trusted_clock_authority_receipt_v3(
            self.registration,
            authority_id=authority_id,
            key_id=self.key_ids[authority_id],
            request_nonce_hash=self.nonce_hash,
            request_context_hash=request_context_hash or self.request_context_hash,
            observed_at_ms=observed_at_ms,
            issued_at_ms=issued_at_ms,
        )
        signature = self.private_keys[signer_id or authority_id].sign(
            bytes.fromhex(unsigned["receipt_content_hash"])
        )
        return clock_contract.assemble_trusted_clock_authority_receipt_v3(
            self.registration,
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    def _clock_attestation(
        self,
        *,
        receipts: list[dict] | None = None,
        request_context_hash: str | None = None,
    ) -> dict:
        active_receipts = receipts if receipts is not None else self.receipts
        active_context_hash = request_context_hash or self.request_context_hash
        return clock_contract.evaluate_trusted_clock_authority_v3(
            self.registration,
            active_receipts,
            self.public_keys,
            expected_registration_hash=self.registration["registration_hash"],
            expected_receipt_hashes=self._expected_receipts(active_receipts),
            request_nonce_hash=self.nonce_hash,
            request_context_hash=active_context_hash,
            verification_time_ms=1_010_500,
        )

    def _clock_context(
        self,
        *,
        receipts: list[dict] | None = None,
        request_context_hash: str | None = None,
    ) -> dict:
        active_receipts = receipts if receipts is not None else self.receipts
        return {
            "registration": self.registration,
            "receipts": active_receipts,
            "authority_public_keys_by_id": self.public_keys,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_receipt_hashes": self._expected_receipts(active_receipts),
            "request_nonce_hash": self.nonce_hash,
            "request_context_hash": request_context_hash or self.request_context_hash,
            "verification_time_ms": 1_010_500,
        }

    def _build(
        self,
        *,
        readiness_v2: dict | None = None,
        clock_attestation: dict | None = None,
        readiness_v2_context: dict | None = None,
        clock_context: dict | None = None,
    ) -> dict:
        with self.v2_case.source_verifiers():
            return contract.build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
                self.readiness_v2 if readiness_v2 is None else readiness_v2,
                self.clock_attestation if clock_attestation is None else clock_attestation,
                readiness_v2_verification_context=(
                    self.readiness_v2_context
                    if readiness_v2_context is None
                    else readiness_v2_context
                ),
                trusted_clock_verification_context=(
                    self.clock_context if clock_context is None else clock_context
                ),
            )

    def _verify(self, document: dict) -> bool:
        with self.v2_case.source_verifiers():
            return contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v3(
                document,
                self.readiness_v2,
                self.clock_attestation,
                readiness_v2_verification_context=self.readiness_v2_context,
                trusted_clock_verification_context=self.clock_context,
            )

    def test_v2_gap_is_explicitly_reproduced(self) -> None:
        first = self.v2_case.build()
        second = self.v2_case.build()
        self.assertEqual(first, second)
        self.assertNotIn("trusted_clock", json.dumps(first).lower())

    def test_context_hash_is_deterministic_and_consumer_bound(self) -> None:
        first = contract.derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
            self.readiness_v2
        )
        second = contract.derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
            copy.deepcopy(self.readiness_v2)
        )
        changed = copy.deepcopy(self.readiness_v2)
        changed["envelope_hash"] = "0" * 64
        third = contract.derive_strategy_correlation_cluster_portfolio_risk_shadow_trusted_clock_context_hash_v3(
            changed
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_build_adds_exactly_one_fourteenth_verified_input(self) -> None:
        self.assertEqual(len(self.document["input_inventory"]), 14)
        self.assertEqual(self.document["summary"]["required_input_count"], 14)
        self.assertEqual(self.document["summary"]["verified_input_count"], 14)
        self.assertEqual(
            self.document["input_inventory"][-1],
            {
                "input": "signed_trusted_clock_authority_attestation",
                "schema_version": clock_contract.ATTESTATION_SCHEMA_VERSION,
                "state": "VERIFIED",
            },
        )

    def test_bounded_state_remains_unknown_and_denied(self) -> None:
        self.assertEqual(self.document["status"], "UNKNOWN")
        self.assertEqual(self.document["source_state"], contract.SOURCE_STATE)
        self.assertEqual(self.document["gap_state"], contract.GAP_STATE)
        self.assertEqual(self.document["maturity_state"], contract.MATURITY_STATE)
        self.assertEqual(self.document["permission_state"], "DENIED")

    def test_signed_time_facts_do_not_authenticate_external_authority(self) -> None:
        facts = self.document["facts"]
        self.assertTrue(facts["signed_time_detached_signatures_verified"])
        self.assertTrue(facts["signed_time_multi_authority_quorum_verified"])
        self.assertFalse(facts["signed_time_external_authority_trust_verified"])
        self.assertFalse(facts["signed_time_registration_governance_verified"])
        self.assertFalse(facts["signed_time_verification_source_trusted"])
        self.assertFalse(facts["current_time_established"])

    def test_all_operational_authority_remains_denied(self) -> None:
        self.assertTrue(self.document["authority"]["descriptive_only"])
        self.assertTrue(
            all(
                value is False
                for key, value in self.document["authority"].items()
                if key != "descriptive_only"
            )
        )
        self.assertTrue(all(value is False for value in self.document["permissions"].values()))

    def test_full_public_verifier_rebuilds_every_source(self) -> None:
        self.assertTrue(self._verify(self.document))

    def test_build_is_deterministic(self) -> None:
        self.assertEqual(self.document, self._build())

    def test_output_redacts_raw_clock_evidence(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn("public_key_base64", encoded)
        self.assertNotIn("signature_base64", encoded)
        self.assertNotIn('"receipts"', encoded)
        for public_key in self.public_keys.values():
            self.assertNotIn(public_key, encoded)

    def test_output_lineage_is_hash_only(self) -> None:
        for value in self.document["source_lineage"].values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")

    def test_build_does_not_mutate_inputs(self) -> None:
        v2 = copy.deepcopy(self.readiness_v2)
        clock = copy.deepcopy(self.clock_attestation)
        v2_context = copy.deepcopy(self.readiness_v2_context)
        clock_context = copy.deepcopy(self.clock_context)
        snapshots = copy.deepcopy((v2, clock, v2_context, clock_context))
        self._build(
            readiness_v2=v2,
            clock_attestation=clock,
            readiness_v2_context=v2_context,
            clock_context=clock_context,
        )
        self.assertEqual(snapshots, (v2, clock, v2_context, clock_context))

    def test_rejects_tampered_v2_document(self) -> None:
        changed = copy.deepcopy(self.readiness_v2)
        changed["facts"]["local_required_input_set_verified"] = False
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(readiness_v2=changed)

    def test_rejects_wrong_v2_verification_context(self) -> None:
        changed = copy.deepcopy(self.readiness_v2_context)
        changed["portfolio_inputs"]["portfolio_risk_adapter"] = {}
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(readiness_v2_context=changed)

    def test_rejects_v2_permission_inflation(self) -> None:
        changed = copy.deepcopy(self.readiness_v2)
        changed["permissions"]["paper_authorized"] = True
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(readiness_v2=changed)

    def test_rejects_tampered_clock_attestation(self) -> None:
        changed = copy.deepcopy(self.clock_attestation)
        changed["facts"]["external_time_authority_trust_verified"] = True
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_attestation=changed)

    def test_rejects_clock_current_time_inflation(self) -> None:
        changed = copy.deepcopy(self.clock_attestation)
        changed["facts"]["current_time_established"] = True
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_attestation=changed)

    def test_rejects_unbound_clock_request_context(self) -> None:
        changed = copy.deepcopy(self.clock_context)
        changed["request_context_hash"] = _hash_text("unbound-context")
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_valid_clock_for_a_different_consumer_context(self) -> None:
        other_context = _hash_text("another-readiness-envelope")
        receipt_a = self._clock_receipt(
            "TIME-A", 1_010_000, 1_010_010, request_context_hash=other_context
        )
        receipt_b = self._clock_receipt(
            "TIME-B", 1_010_100, 1_010_110, request_context_hash=other_context
        )
        receipts = [receipt_a, receipt_b]
        attestation = self._clock_attestation(
            receipts=receipts, request_context_hash=other_context
        )
        context = self._clock_context(
            receipts=receipts, request_context_hash=other_context
        )
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_attestation=attestation, clock_context=context)

    def test_rejects_clock_registration_hash_drift(self) -> None:
        changed = copy.deepcopy(self.clock_context)
        changed["expected_registration_hash"] = "0" * 64
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_clock_expected_receipt_hash_drift(self) -> None:
        changed = copy.deepcopy(self.clock_context)
        changed["expected_receipt_hashes"]["TIME-B"] = "0" * 64
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_clock_wrong_signer(self) -> None:
        invalid_b = self._clock_receipt(
            "TIME-B", 1_010_100, 1_010_110, signer_id="TIME-C"
        )
        changed = self._clock_context(receipts=[self.receipt_a, invalid_b])
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_clock_below_quorum(self) -> None:
        changed = self._clock_context(receipts=[self.receipt_a])
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_extra_v2_context_field(self) -> None:
        changed = copy.deepcopy(self.readiness_v2_context)
        changed["extra"] = None
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(readiness_v2_context=changed)

    def test_rejects_missing_clock_context_field(self) -> None:
        changed = copy.deepcopy(self.clock_context)
        del changed["expected_receipt_hashes"]
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_rejects_extra_clock_context_field(self) -> None:
        changed = copy.deepcopy(self.clock_context)
        changed["extra"] = None
        with self.assertRaises(contract.ReadinessEnvelopeV3ContractError):
            self._build(clock_context=changed)

    def test_public_verifier_rejects_projection_tamper(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["authority"]["runtime_gate_activation_allowed"] = True
        self.assertFalse(self._verify(changed))

    def test_schema_and_fingerprint_are_versioned(self) -> None:
        self.assertEqual(self.document["schema_version"], contract.SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], contract.STATIC_FINGERPRINT)
        self.assertEqual(
            contract.STATIC_FINGERPRINT,
            "20260822-portfolio-risk-shadow-input-readiness-envelope-3",
        )

    def test_production_api_has_no_signer_secret_or_runtime_service(self) -> None:
        source = inspect.getsource(contract)
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("portfolio_risk_shadow_service", source)
        self.assertFalse(any("private" in name.lower() for name in contract.__all__))

    def test_output_has_no_ready_profit_or_execution_claim(self) -> None:
        encoded = json.dumps(self.document, sort_keys=True)
        self.assertNotIn('"READY"', encoded)
        self.assertFalse(self.document["facts"]["profitability_verified"])
        self.assertFalse(self.document["authority"]["shadow_consumer_execution_allowed"])
        self.assertFalse(self.document["authority"]["risk_service_invocation_allowed"])


if __name__ == "__main__":
    unittest.main()
