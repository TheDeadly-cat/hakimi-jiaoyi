from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import inspect
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipt_verifier_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1
    as persistence_registration_fixtures,
)


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceReceiptVerifierV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = persistence_registration_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayCheckpointPersistenceRegistrationV1Tests(
            methodName="test_registration_binds_source_common_view_and_receipt_contracts"
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.context = self.source.context
        self.registration = self.source.registration
        self.configuration = self.source.configuration
        self.private_key = self.source.persistence_private_key
        self.public_key_base64 = self.source.persistence_public_key_base64
        self.asset = subject.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
            self.registration,
            asset_created_at_utc="2026-12-20T02:21:00Z",
        )
        self.assertIsNotNone(self.asset)
        unsigned_write = subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
            self.registration,
            self.asset,
            session_id="PERSISTENCE-WRITE-SESSION-01",
            written_at_utc="2026-12-20T02:25:00Z",
        )
        self.write_receipt = self._sign(
            unsigned_write,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
        )
        unsigned_reopen = subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
            self.registration,
            self.asset,
            self.write_receipt,
            session_id="PERSISTENCE-REOPEN-SESSION-01",
            reopened_at_utc="2026-12-20T02:30:00Z",
        )
        self.reopen_receipt = self._sign(
            unsigned_reopen,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )

    @staticmethod
    def _sign(
        unsigned: dict[str, object] | None,
        private_key: Ed25519PrivateKey,
        assembler,
    ) -> dict[str, object]:
        if unsigned is None:
            raise AssertionError("unsigned receipt missing")
        signature = private_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        receipt = assembler(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )
        if receipt is None:
            raise AssertionError("receipt assembly failed")
        return receipt

    @staticmethod
    def _reseal_unsigned(value: dict[str, object]) -> dict[str, object]:
        result = deepcopy(value)
        result.pop("receipt_content_sha256")
        result["receipt_content_sha256"] = strict_canonical_hash(result)
        return result

    def _evaluate(self, **overrides: object) -> dict[str, object]:
        values = {
            "persistence_registration": self.registration,
            "source_preregistration": self.context["replay_preregistration"],
            "lifecycle_binding_preregistration": self.context[
                "lifecycle_preregistration"
            ],
            "provider_binding_preregistration": self.context[
                "binding_preregistration"
            ],
            "overlap_preregistration": self.context[
                "overlap_preregistration"
            ],
            "multi_window_preregistration": self.context[
                "multi_preregistration"
            ],
            "persistence_configuration": self.configuration,
            "persistence_provider_public_key_base64": self.public_key_base64,
            "checkpoint_asset": self.asset,
            "write_receipt": self.write_receipt,
            "reopen_receipt": self.reopen_receipt,
            "expected_registration_hash": self.registration[
                "registration_hash"
            ],
            "expected_asset_hash": self.asset["asset_hash"],
            "expected_write_receipt_hash": self.write_receipt[
                "write_receipt_hash"
            ],
            "expected_reopen_receipt_hash": self.reopen_receipt[
                "reopen_receipt_hash"
            ],
        }
        values.update(overrides)
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
            **values
        )
        self.assertIsInstance(result, dict)
        return result

    def _verify(
        self,
        document: dict[str, object],
        *,
        expected_verification_hash: str | None = None,
    ) -> bool:
        return subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1(
            document,
            self.registration,
            self.context["replay_preregistration"],
            self.context["lifecycle_preregistration"],
            self.context["binding_preregistration"],
            self.context["overlap_preregistration"],
            self.context["multi_preregistration"],
            self.configuration,
            self.public_key_base64,
            self.asset,
            self.write_receipt,
            self.reopen_receipt,
            expected_verification_hash=(
                expected_verification_hash or document["verification_hash"]
            ),
            expected_registration_hash=self.registration["registration_hash"],
            expected_asset_hash=self.asset["asset_hash"],
            expected_write_receipt_hash=self.write_receipt[
                "write_receipt_hash"
            ],
            expected_reopen_receipt_hash=self.reopen_receipt[
                "reopen_receipt_hash"
            ],
        )

    def test_adr0353_registration_still_observes_no_receipts(self) -> None:
        self.assertFalse(
            self.registration["facts"]["write_receipt_observed"]
        )
        self.assertFalse(
            self.registration["facts"]["reopen_receipt_observed"]
        )

    def test_valid_receipts_pass_local_crypto_contract(self) -> None:
        result = self._evaluate()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["verification_state"], subject.VERIFICATION_STATE)
        self.assertTrue(result["facts"]["write_receipt_signature_verified"])
        self.assertTrue(result["facts"]["reopen_receipt_signature_verified"])
        self.assertTrue(result["facts"]["exact_record_replay_verified"])
        self.assertFalse(
            result["facts"]["durable_checkpoint_publication_verified"]
        )
        self.assertFalse(
            result["facts"]["source_replay_binding_gate_verified"]
        )

    def test_evaluation_is_deterministic_and_exactly_verifiable(self) -> None:
        first = self._evaluate()
        second = self._evaluate()

        self.assertEqual(first, second)
        self.assertTrue(self._verify(first))

    def test_registration_exact_rebuild_is_required(self) -> None:
        registration = deepcopy(self.registration)
        registration["authority"]["writer_allowed"] = True
        unsigned = deepcopy(registration)
        unsigned.pop("registration_hash")
        registration = seal_strict_canonical_document(
            unsigned,
            "registration_hash",
        )

        result = self._evaluate(
            persistence_registration=registration,
            expected_registration_hash=registration["registration_hash"],
        )

        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(
            result["reason"],
            "PERSISTENCE_REGISTRATION_EXACT_REBUILD_FAILED",
        )

    def test_asset_tamper_or_wrong_expected_hash_is_unknown(self) -> None:
        asset = deepcopy(self.asset)
        asset["source_checkpoint_root_hash"] = "0" * 64
        unsigned = deepcopy(asset)
        unsigned.pop("asset_hash")
        asset = seal_strict_canonical_document(unsigned, "asset_hash")
        self.assertEqual(
            self._evaluate(
                checkpoint_asset=asset,
                expected_asset_hash=asset["asset_hash"],
            )["status"],
            "UNKNOWN",
        )
        self.assertEqual(
            self._evaluate(expected_asset_hash="0" * 64)["status"],
            "UNKNOWN",
        )

    def test_previous_asset_hash_and_asset_time_are_strict(self) -> None:
        self.assertIsNone(
            subject.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
                self.registration,
                asset_created_at_utc="2026-12-20T02:21:00Z",
                previous_persisted_asset_hash="bad",
            )
        )
        self.assertIsNone(
            subject.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1(
                self.registration,
                asset_created_at_utc="2026-12-20T02:00:00Z",
            )
        )

    def test_wrong_write_signing_key_is_unknown(self) -> None:
        unsigned = subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
            self.registration,
            self.asset,
            session_id="PERSISTENCE-WRITE-SESSION-01",
            written_at_utc="2026-12-20T02:25:00Z",
        )
        receipt = self._sign(
            unsigned,
            Ed25519PrivateKey.generate(),
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
        )

        self.assertEqual(
            self._evaluate(
                write_receipt=receipt,
                expected_write_receipt_hash=receipt["write_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

    def test_wrong_reopen_signing_key_is_unknown(self) -> None:
        unsigned = subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
            self.registration,
            self.asset,
            self.write_receipt,
            session_id="PERSISTENCE-REOPEN-SESSION-01",
            reopened_at_utc="2026-12-20T02:30:00Z",
        )
        receipt = self._sign(
            unsigned,
            Ed25519PrivateKey.generate(),
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )

        self.assertEqual(
            self._evaluate(
                reopen_receipt=receipt,
                expected_reopen_receipt_hash=receipt["reopen_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

    def test_sessions_must_be_distinct_even_when_receipt_is_signed(self) -> None:
        unsigned = deepcopy(self.reopen_receipt)
        for field in ("reopen_receipt_hash", "signature_base64", "signature_sha256"):
            unsigned.pop(field)
        unsigned["session_id"] = self.write_receipt["session_id"]
        unsigned = self._reseal_unsigned(unsigned)
        receipt = self._sign(
            unsigned,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )

        self.assertEqual(
            self._evaluate(
                reopen_receipt=receipt,
                expected_reopen_receipt_hash=receipt["reopen_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

    def test_cardinality_and_record_replay_are_exact(self) -> None:
        unsigned = deepcopy(self.write_receipt)
        for field in ("write_receipt_hash", "signature_base64", "signature_sha256"):
            unsigned.pop(field)
        unsigned["record_count"] = True
        unsigned = self._reseal_unsigned(unsigned)
        receipt = self._sign(
            unsigned,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
        )
        self.assertEqual(
            self._evaluate(
                write_receipt=receipt,
                expected_write_receipt_hash=receipt["write_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

        unsigned = deepcopy(self.reopen_receipt)
        for field in ("reopen_receipt_hash", "signature_base64", "signature_sha256"):
            unsigned.pop(field)
        unsigned["record_hash"] = "0" * 64
        unsigned = self._reseal_unsigned(unsigned)
        receipt = self._sign(
            unsigned,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )
        self.assertEqual(
            self._evaluate(
                reopen_receipt=receipt,
                expected_reopen_receipt_hash=receipt["reopen_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

    def test_reopen_must_bind_exact_write_receipt_hash(self) -> None:
        unsigned = deepcopy(self.reopen_receipt)
        for field in ("reopen_receipt_hash", "signature_base64", "signature_sha256"):
            unsigned.pop(field)
        unsigned["source_write_receipt_hash"] = "0" * 64
        unsigned = self._reseal_unsigned(unsigned)
        receipt = self._sign(
            unsigned,
            self.private_key,
            subject.assemble_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
        )

        self.assertEqual(
            self._evaluate(
                reopen_receipt=receipt,
                expected_reopen_receipt_hash=receipt["reopen_receipt_hash"],
            )["status"],
            "UNKNOWN",
        )

    def test_timestamp_and_delay_policies_fail_closed(self) -> None:
        self.assertIsNone(
            subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1(
                self.registration,
                self.asset,
                session_id="PERSISTENCE-WRITE-SESSION-02",
                written_at_utc="2026-12-20T02:10:00Z",
            )
        )
        self.assertIsNone(
            subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1(
                self.registration,
                self.asset,
                self.write_receipt,
                session_id="PERSISTENCE-REOPEN-SESSION-02",
                reopened_at_utc="2026-12-20T02:25:30Z",
            )
        )

    def test_output_redacts_raw_material_and_keeps_claims_false(self) -> None:
        result = self._evaluate()
        rendered = json.dumps(result, sort_keys=True)

        self.assertNotIn(self.public_key_base64, rendered)
        self.assertNotIn(self.write_receipt["signature_base64"], rendered)
        self.assertNotIn(self.reopen_receipt["signature_base64"], rendered)
        self.assertNotIn('"checkpoint_asset"', rendered)
        self.assertFalse(any(result["authority"].values()))
        self.assertFalse(
            result["facts"]["external_persistence_provider_authority_verified"]
        )
        self.assertFalse(result["facts"]["authoritative_future_pin_verified"])

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        result = self._evaluate()
        forged = deepcopy(result)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("verification_hash")
        forged = seal_strict_canonical_document(unsigned, "verification_hash")

        self.assertFalse(
            self._verify(
                forged,
                expected_verification_hash=forged["verification_hash"],
            )
        )

    def test_source_pin_and_public_api_boundary(self) -> None:
        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        path = services / "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_registration_v1.py"
        self.assertEqual(
            sha256(path.read_bytes()).hexdigest(),
            subject.PERSISTENCE_REGISTRATION_V1_IMPLEMENTATION_SHA256,
        )
        functions = (
            subject.build_strategy_correlation_lifecycle_replay_checkpoint_persistence_asset_v1,
            subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_write_receipt_v1,
            subject.build_unsigned_strategy_correlation_lifecycle_replay_checkpoint_persistence_reopen_receipt_v1,
            subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_checkpoint_persistence_receipts_v1,
        )
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(
                    any(
                        "private" in name.lower()
                        for name in inspect.signature(function).parameters
                    )
                )


if __name__ == "__main__":
    unittest.main()
