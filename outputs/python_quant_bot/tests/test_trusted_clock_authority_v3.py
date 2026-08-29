from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import trusted_clock_authority_v3 as contract


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TrustedClockAuthorityV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_keys = {
            "TIME-A": Ed25519PrivateKey.from_private_bytes(bytes([1]) * 32),
            "TIME-B": Ed25519PrivateKey.from_private_bytes(bytes([2]) * 32),
            "TIME-C": Ed25519PrivateKey.from_private_bytes(bytes([3]) * 32),
        }
        self.key_ids = {
            "TIME-A": "time-a-key-20260822",
            "TIME-B": "time-b-key-20260822",
            "TIME-C": "time-c-key-20260822",
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
        self.nonce_hash = _hash_text("synthetic-request-nonce-0180")
        self.context_hash = _hash_text("synthetic-request-context-0180")
        self.registration = self._registration()
        self.receipt_a = self._receipt("TIME-A", 1_010_000, 1_010_010)
        self.receipt_b = self._receipt("TIME-B", 1_010_100, 1_010_110)

    def _registration(self, **overrides: int) -> dict:
        values = {
            "minimum_sources": 2,
            "max_receipt_age_ms": 5_000,
            "max_provider_spread_ms": 500,
            "max_local_skew_ms": 5_000,
            "max_receipt_issue_delay_ms": 100,
            "valid_from_ms": 1_001_000,
            "valid_until_ms": 1_100_000,
            "declared_at_ms": 1_000_000,
        }
        values.update(overrides)
        return contract.build_trusted_clock_authority_registration_v3(
            self.authorities, **values
        )

    def _receipt(
        self,
        authority_id: str,
        observed_at_ms: int,
        issued_at_ms: int,
        *,
        registration: dict | None = None,
        nonce_hash: str | None = None,
        context_hash: str | None = None,
        signer_id: str | None = None,
    ) -> dict:
        active_registration = registration or self.registration
        unsigned = contract.build_unsigned_trusted_clock_authority_receipt_v3(
            active_registration,
            authority_id=authority_id,
            key_id=self.key_ids[authority_id],
            request_nonce_hash=nonce_hash or self.nonce_hash,
            request_context_hash=context_hash or self.context_hash,
            observed_at_ms=observed_at_ms,
            issued_at_ms=issued_at_ms,
        )
        signature = self.private_keys[signer_id or authority_id].sign(
            bytes.fromhex(unsigned["receipt_content_hash"])
        )
        return contract.assemble_trusted_clock_authority_receipt_v3(
            active_registration,
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    @staticmethod
    def _expected(receipts: list[dict]) -> dict[str, str]:
        return {
            receipt["authority"]["authority_id"]: receipt["receipt_hash"]
            for receipt in receipts
        }

    def _evaluate(
        self,
        receipts: list[dict] | None = None,
        *,
        registration: dict | None = None,
        public_keys: dict[str, str] | None = None,
        expected_registration_hash: str | None = None,
        expected_receipt_hashes: dict[str, str] | None = None,
        nonce_hash: str | None = None,
        context_hash: str | None = None,
        verification_time_ms: int = 1_010_500,
    ) -> dict:
        active_registration = registration or self.registration
        active_receipts = receipts or [self.receipt_a, self.receipt_b]
        return contract.evaluate_trusted_clock_authority_v3(
            active_registration,
            active_receipts,
            public_keys or self.public_keys,
            expected_registration_hash=(
                expected_registration_hash or active_registration["registration_hash"]
            ),
            expected_receipt_hashes=(
                expected_receipt_hashes
                if expected_receipt_hashes is not None
                else self._expected(active_receipts)
            ),
            request_nonce_hash=nonce_hash or self.nonce_hash,
            request_context_hash=context_hash or self.context_hash,
            verification_time_ms=verification_time_ms,
        )

    def test_registration_is_deterministic_and_redacts_raw_keys(self) -> None:
        first = self._registration()
        second = self._registration()
        self.assertEqual(first, second)
        encoded = json.dumps(first, sort_keys=True)
        self.assertNotIn("public_key_base64", encoded)
        for public_key in self.public_keys.values():
            self.assertNotIn(public_key, encoded)

    def test_registration_authority_input_order_is_canonical(self) -> None:
        reversed_registration = contract.build_trusted_clock_authority_registration_v3(
            list(reversed(self.authorities)),
            minimum_sources=2,
            max_receipt_age_ms=5_000,
            max_provider_spread_ms=500,
            max_local_skew_ms=5_000,
            max_receipt_issue_delay_ms=100,
            valid_from_ms=1_001_000,
            valid_until_ms=1_100_000,
            declared_at_ms=1_000_000,
        )
        self.assertEqual(self.registration, reversed_registration)

    def test_registration_rejects_duplicate_authority_id(self) -> None:
        duplicate = copy.deepcopy(self.authorities)
        duplicate[1]["authority_id"] = duplicate[0]["authority_id"]
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.build_trusted_clock_authority_registration_v3(
                duplicate,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=500,
                max_local_skew_ms=5_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )

    def test_registration_rejects_duplicate_key_id(self) -> None:
        duplicate = copy.deepcopy(self.authorities)
        duplicate[1]["key_id"] = duplicate[0]["key_id"]
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.build_trusted_clock_authority_registration_v3(
                duplicate,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=500,
                max_local_skew_ms=5_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )

    def test_registration_rejects_duplicate_public_key(self) -> None:
        duplicate = copy.deepcopy(self.authorities)
        duplicate[1]["public_key_base64"] = duplicate[0]["public_key_base64"]
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.build_trusted_clock_authority_registration_v3(
                duplicate,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=500,
                max_local_skew_ms=5_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )

    def test_registration_requires_at_least_two_sources(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.build_trusted_clock_authority_registration_v3(
                self.authorities,
                minimum_sources=1,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=500,
                max_local_skew_ms=5_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )

    def test_registration_rejects_bool_as_integer(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._registration(max_receipt_age_ms=True)

    def test_registration_rejects_invalid_validity_order(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._registration(valid_from_ms=1_100_000, valid_until_ms=1_100_000)

    def test_registration_rejects_invalid_public_key_base64(self) -> None:
        invalid = copy.deepcopy(self.authorities)
        invalid[0]["public_key_base64"] = "not-base64"
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.build_trusted_clock_authority_registration_v3(
                invalid,
                minimum_sources=2,
                max_receipt_age_ms=5_000,
                max_provider_spread_ms=500,
                max_local_skew_ms=5_000,
                max_receipt_issue_delay_ms=100,
                valid_from_ms=1_001_000,
                valid_until_ms=1_100_000,
                declared_at_ms=1_000_000,
            )

    def test_registration_public_verifier_rebuilds_exactly(self) -> None:
        self.assertTrue(
            contract.verify_trusted_clock_authority_registration_v3(
                self.registration,
                self.public_keys,
                expected_registration_hash=self.registration["registration_hash"],
            )
        )

    def test_registration_public_verifier_fails_closed_on_hash_drift(self) -> None:
        self.assertFalse(
            contract.verify_trusted_clock_authority_registration_v3(
                self.registration,
                self.public_keys,
                expected_registration_hash="0" * 64,
            )
        )

    def test_unsigned_receipt_is_deterministic_and_does_not_mutate_registration(self) -> None:
        before = copy.deepcopy(self.registration)
        first = contract.build_unsigned_trusted_clock_authority_receipt_v3(
            self.registration,
            authority_id="TIME-A",
            key_id=self.key_ids["TIME-A"],
            request_nonce_hash=self.nonce_hash,
            request_context_hash=self.context_hash,
            observed_at_ms=1_010_000,
            issued_at_ms=1_010_010,
        )
        second = contract.build_unsigned_trusted_clock_authority_receipt_v3(
            self.registration,
            authority_id="TIME-A",
            key_id=self.key_ids["TIME-A"],
            request_nonce_hash=self.nonce_hash,
            request_context_hash=self.context_hash,
            observed_at_ms=1_010_000,
            issued_at_ms=1_010_010,
        )
        self.assertEqual(first, second)
        self.assertEqual(before, self.registration)

    def test_receipt_rejects_time_outside_registration(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._receipt("TIME-A", 1_000_999, 1_001_000)

    def test_receipt_rejects_issue_delay_over_policy(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._receipt("TIME-A", 1_010_000, 1_010_101)

    def test_receipt_rejects_malformed_request_hash(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._receipt("TIME-A", 1_010_000, 1_010_010, nonce_hash="bad")

    def test_assembler_rejects_wrong_signature_length(self) -> None:
        unsigned = contract.build_unsigned_trusted_clock_authority_receipt_v3(
            self.registration,
            authority_id="TIME-A",
            key_id=self.key_ids["TIME-A"],
            request_nonce_hash=self.nonce_hash,
            request_context_hash=self.context_hash,
            observed_at_ms=1_010_000,
            issued_at_ms=1_010_010,
        )
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            contract.assemble_trusted_clock_authority_receipt_v3(
                self.registration,
                unsigned,
                base64.b64encode(bytes(63)).decode("ascii"),
            )

    def test_happy_path_reports_only_bounded_local_verification(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["verification"]["status"], "PASS")
        self.assertEqual(result["verification"]["state"], contract.VERIFICATION_STATE)
        self.assertEqual(result["verification"]["source_count"], 2)
        self.assertTrue(result["facts"]["detached_signatures_verified"])
        self.assertFalse(result["facts"]["external_time_authority_trust_verified"])
        self.assertFalse(result["facts"]["current_time_established"])
        self.assertFalse(result["permission"]["paper_trading_authorized"])
        self.assertFalse(result["permission"]["live_trading_authorized"])

    def test_attestation_public_verifier_rebuilds_full_result(self) -> None:
        receipts = [self.receipt_a, self.receipt_b]
        result = self._evaluate(receipts)
        self.assertTrue(
            contract.verify_trusted_clock_authority_attestation_v3(
                result,
                self.registration,
                receipts,
                self.public_keys,
                expected_registration_hash=self.registration["registration_hash"],
                expected_receipt_hashes=self._expected(receipts),
                request_nonce_hash=self.nonce_hash,
                request_context_hash=self.context_hash,
                verification_time_ms=1_010_500,
            )
        )

    def test_attestation_public_verifier_rejects_projection_tamper(self) -> None:
        receipts = [self.receipt_a, self.receipt_b]
        result = self._evaluate(receipts)
        result["permission"]["live_trading_authorized"] = True
        self.assertFalse(
            contract.verify_trusted_clock_authority_attestation_v3(
                result,
                self.registration,
                receipts,
                self.public_keys,
                expected_registration_hash=self.registration["registration_hash"],
                expected_receipt_hashes=self._expected(receipts),
                request_nonce_hash=self.nonce_hash,
                request_context_hash=self.context_hash,
                verification_time_ms=1_010_500,
            )
        )

    def test_evaluation_rejects_below_quorum(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate([self.receipt_a])

    def test_evaluation_rejects_duplicate_authority_receipt(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate([self.receipt_a, self.receipt_a])

    def test_evaluation_rejects_wrong_public_key(self) -> None:
        wrong = dict(self.public_keys)
        wrong["TIME-B"] = self.public_keys["TIME-C"]
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(public_keys=wrong)

    def test_evaluation_rejects_extra_public_key_map_entry(self) -> None:
        extra = dict(self.public_keys)
        extra["TIME-D"] = self.public_keys["TIME-A"]
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(public_keys=extra)

    def test_evaluation_rejects_invalid_signature(self) -> None:
        invalid = self._receipt(
            "TIME-B", 1_010_100, 1_010_110, signer_id="TIME-C"
        )
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate([self.receipt_a, invalid])

    def test_evaluation_rejects_expected_registration_hash_drift(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(expected_registration_hash="0" * 64)

    def test_evaluation_rejects_expected_receipt_hash_drift(self) -> None:
        expected = self._expected([self.receipt_a, self.receipt_b])
        expected["TIME-B"] = "0" * 64
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(expected_receipt_hashes=expected)

    def test_evaluation_rejects_expected_receipt_map_omission(self) -> None:
        expected = {"TIME-A": self.receipt_a["receipt_hash"]}
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(expected_receipt_hashes=expected)

    def test_evaluation_rejects_nonce_drift(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(nonce_hash=_hash_text("different nonce"))

    def test_evaluation_rejects_context_drift(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(context_hash=_hash_text("different context"))

    def test_evaluation_rejects_provider_spread_over_policy(self) -> None:
        far_b = self._receipt("TIME-B", 1_010_900, 1_010_910)
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(
                [self.receipt_a, far_b], verification_time_ms=1_011_000
            )

    def test_evaluation_rejects_stale_receipt(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(verification_time_ms=1_016_000)

    def test_evaluation_rejects_local_skew_over_policy(self) -> None:
        registration = self._registration(
            max_receipt_age_ms=10_000,
            max_local_skew_ms=500,
        )
        receipt_a = self._receipt(
            "TIME-A", 1_010_000, 1_010_010, registration=registration
        )
        receipt_b = self._receipt(
            "TIME-B", 1_010_100, 1_010_110, registration=registration
        )
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(
                [receipt_a, receipt_b],
                registration=registration,
                verification_time_ms=1_011_000,
            )

    def test_evaluation_rejects_verification_time_outside_registration(self) -> None:
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate(verification_time_ms=1_100_001)

    def test_coherent_receipt_reseal_without_resigning_is_rejected(self) -> None:
        changed_unsigned = contract.build_unsigned_trusted_clock_authority_receipt_v3(
            self.registration,
            authority_id="TIME-A",
            key_id=self.key_ids["TIME-A"],
            request_nonce_hash=self.nonce_hash,
            request_context_hash=self.context_hash,
            observed_at_ms=1_010_001,
            issued_at_ms=1_010_011,
        )
        resealed = contract.assemble_trusted_clock_authority_receipt_v3(
            self.registration,
            changed_unsigned,
            self.receipt_a["signature"]["signature_base64"],
        )
        with self.assertRaises(contract.TrustedClockAuthorityContractError):
            self._evaluate([resealed, self.receipt_b])

    def test_evaluation_output_redacts_raw_keys_signatures_and_inputs(self) -> None:
        encoded = json.dumps(self._evaluate(), sort_keys=True)
        self.assertNotIn("public_key_base64", encoded)
        self.assertNotIn("signature_base64", encoded)
        for public_key in self.public_keys.values():
            self.assertNotIn(public_key, encoded)

    def test_production_api_does_not_accept_signer_secret_material(self) -> None:
        self.assertFalse(any("private" in name.lower() for name in contract.__all__))
        self.assertNotIn("Ed25519PrivateKey", inspect.getsource(contract))

    def test_output_has_no_ready_or_authorization_inflation(self) -> None:
        result = self._evaluate()
        encoded = json.dumps(result, sort_keys=True)
        self.assertNotIn('"READY"', encoded)
        self.assertFalse(result["permission"]["current_activation_authorized"])
        self.assertFalse(result["facts"]["profitability_proven"])

    def test_evaluation_does_not_mutate_inputs(self) -> None:
        registration = copy.deepcopy(self.registration)
        receipts = copy.deepcopy([self.receipt_a, self.receipt_b])
        public_keys = copy.deepcopy(self.public_keys)
        expected = self._expected(receipts)
        snapshots = copy.deepcopy((registration, receipts, public_keys, expected))
        contract.evaluate_trusted_clock_authority_v3(
            registration,
            receipts,
            public_keys,
            expected_registration_hash=registration["registration_hash"],
            expected_receipt_hashes=expected,
            request_nonce_hash=self.nonce_hash,
            request_context_hash=self.context_hash,
            verification_time_ms=1_010_500,
        )
        self.assertEqual(snapshots, (registration, receipts, public_keys, expected))


if __name__ == "__main__":
    unittest.main()
