from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 as replay_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_registration_v1 as subject


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _replay_registration() -> dict[str, object]:
    return {
        "replay_registry_id": "synthetic-replay-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.replay",
        "adapter_id": "synthetic-replay-adapter-v1",
        "adapter_implementation_hash": _hash("replay-adapter"),
        "provider_receipt_signing_key_id": "synthetic-provider-receipt-key-v1",
        "provider_receipt_signing_public_key_hash": _hash("provider-receipt-key"),
        "identity_registry_trust_root_key_id": "synthetic-identity-root-v1",
        "identity_registry_trust_root_public_key_hash": _hash("identity-root"),
        "replay_registry_trust_root_key_id": "synthetic-replay-root-v1",
        "replay_registry_trust_root_public_key_hash": _hash("replay-root"),
        "assertion_digest_algorithm": replay_contract.ASSERTION_DIGEST_ALGORITHM,
        "assertion_digest_encoding": replay_contract.ASSERTION_DIGEST_ENCODING,
        "log_protocol": replay_contract.LOG_PROTOCOL,
        "inclusion_proof_protocol": replay_contract.INCLUSION_PROOF_PROTOCOL,
        "consistency_proof_protocol": replay_contract.CONSISTENCY_PROOF_PROTOCOL,
        "checkpoint_signature_algorithm": replay_contract.CHECKPOINT_SIGNATURE_ALGORITHM,
        "checkpoint_signature_encoding": replay_contract.CHECKPOINT_SIGNATURE_ENCODING,
        "empty_domain": replay_contract.EMPTY_DOMAIN,
        "leaf_domain": replay_contract.LEAF_DOMAIN,
        "node_domain": replay_contract.NODE_DOMAIN,
        "checkpoint_domain": replay_contract.CHECKPOINT_DOMAIN,
        "genesis_tree_size": 0,
        "genesis_root_hash": replay_contract.GENESIS_ROOT_HASH,
    }


def _configuration(source_receipt_hash: str) -> dict[str, object]:
    return {
        "persistence_provider_id": "synthetic-checkpoint-store-v1",
        "persistence_namespace": "hakimi.synthetic.replay-checkpoints",
        "adapter_id": "synthetic-checkpoint-persistence-adapter-v1",
        "adapter_implementation_hash": _hash("persistence-adapter"),
        "persistence_provider_key_id": "synthetic-persistence-provider-key-v1",
        "persistence_provider_public_key_hash": _hash("persistence-provider-key"),
        "source_replay_registration_receipt_hash": source_receipt_hash,
        "canonical_hash_algorithm": subject.CANONICAL_HASH_ALGORITHM,
        "canonical_hash_encoding": subject.CANONICAL_HASH_ENCODING,
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
        "pinned_asset_schema": subject.PINNED_ASSET_SCHEMA,
        "write_receipt_schema": subject.WRITE_RECEIPT_SCHEMA,
        "reopen_receipt_schema": subject.REOPEN_RECEIPT_SCHEMA,
        "session_policy": subject.SESSION_POLICY,
        "cardinality_policy": subject.CARDINALITY_POLICY,
        "record_replay_policy": subject.RECORD_REPLAY_POLICY,
        "timestamp_order_policy": subject.TIMESTAMP_ORDER_POLICY,
        "provider_mode": subject.PROVIDER_MODE,
    }


def _fixture() -> dict[str, object]:
    replay_registration = _replay_registration()
    replay_receipt = replay_contract.build_provider_identity_assertion_replay_adapter_registration_v1(
        replay_registration
    )
    return {
        "replay_registration": replay_registration,
        "replay_receipt": replay_receipt,
        "configuration": _configuration(replay_receipt["receipt_hash"]),
    }


def _build(fixture: dict[str, object]) -> dict[str, object]:
    return subject.build_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
        replay_registration=fixture["replay_registration"],
        replay_registration_receipt=fixture["replay_receipt"],
        persistence_configuration=fixture["configuration"],
    )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceRegistrationV1Tests(unittest.TestCase):
    def test_valid_registration_is_sealed_and_permission_negative(self) -> None:
        receipt = _build(_fixture())
        self.assertEqual(receipt["schema"], subject.REGISTRATION_SCHEMA)
        self.assertEqual(receipt["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertEqual(receipt["status"], subject.REGISTERED_STATUS)
        self.assertTrue(receipt["facts"]["persistence_registration_sealed"])
        self.assertTrue(receipt["facts"]["persistence_key_role_separated"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_registration_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_build(fixture), _build(fixture))

    def test_registration_copies_caller_input(self) -> None:
        fixture = _fixture()
        receipt = _build(fixture)
        fixture["configuration"]["adapter_id"] = "mutated-adapter-v1"
        self.assertEqual(
            receipt["configuration"]["adapter_id"],
            "synthetic-checkpoint-persistence-adapter-v1",
        )

    def test_source_replay_registration_receipt_must_verify(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["facts"]["key_roles_separated"] = False
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_missing_configuration_field_is_unknown(self) -> None:
        fixture = _fixture()
        fixture["configuration"].pop("session_policy")
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_extra_configuration_field_is_unknown(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["storage_path"] = "forbidden"
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_identifiers_are_strict(self) -> None:
        for field in (
            "persistence_provider_id",
            "persistence_namespace",
            "adapter_id",
            "persistence_provider_key_id",
        ):
            with self.subTest(field=field):
                fixture = _fixture()
                fixture["configuration"][field] = "INVALID VALUE"
                self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_hashes_are_strict(self) -> None:
        for field in (
            "adapter_implementation_hash",
            "persistence_provider_public_key_hash",
            "source_replay_registration_receipt_hash",
        ):
            with self.subTest(field=field):
                fixture = _fixture()
                fixture["configuration"][field] = "not-a-hash"
                self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_uppercase_hash_is_unknown(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["adapter_implementation_hash"] = str(
            fixture["configuration"]["adapter_implementation_hash"]
        ).upper()
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_source_receipt_hash_must_match(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["source_replay_registration_receipt_hash"] = _hash("other")
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_key_id_is_separate_from_all_source_roles(self) -> None:
        for source_field in (
            "provider_receipt_signing_key_id",
            "identity_registry_trust_root_key_id",
            "replay_registry_trust_root_key_id",
        ):
            with self.subTest(source_field=source_field):
                fixture = _fixture()
                fixture["configuration"]["persistence_provider_key_id"] = fixture["replay_registration"][source_field]
                self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_key_hash_is_separate_from_all_source_roles(self) -> None:
        for source_field in (
            "provider_receipt_signing_public_key_hash",
            "identity_registry_trust_root_public_key_hash",
            "replay_registry_trust_root_public_key_hash",
        ):
            with self.subTest(source_field=source_field):
                fixture = _fixture()
                fixture["configuration"]["persistence_provider_public_key_hash"] = fixture["replay_registration"][source_field]
                self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_adapter_role_is_separate(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["adapter_id"] = fixture["replay_registration"]["adapter_id"]
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_persistence_provider_role_is_separate(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["persistence_provider_id"] = fixture["replay_registration"]["replay_registry_id"]
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_protocol_fields_are_exact(self) -> None:
        fields = (
            "canonical_hash_algorithm",
            "canonical_hash_encoding",
            "signature_algorithm",
            "signature_encoding",
            "pinned_asset_schema",
            "write_receipt_schema",
            "reopen_receipt_schema",
            "session_policy",
            "cardinality_policy",
            "record_replay_policy",
            "timestamp_order_policy",
        )
        for field in fields:
            with self.subTest(field=field):
                fixture = _fixture()
                fixture["configuration"][field] = "legacy"
                self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_provider_mode_is_exact_and_io_free(self) -> None:
        fixture = _fixture()
        fixture["configuration"]["provider_mode"] = "local-database"
        self.assertEqual(_build(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_verifier_accepts_exact_registration(self) -> None:
        fixture = _fixture()
        receipt = _build(fixture)
        self.assertTrue(
            subject.verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
                receipt,
                replay_registration=fixture["replay_registration"],
                replay_registration_receipt=fixture["replay_receipt"],
                persistence_configuration=fixture["configuration"],
            )
        )

    def test_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        receipt = _build(fixture)
        tampered = copy.deepcopy(receipt)
        tampered["facts"]["durable_write_verified"] = True
        self.assertFalse(
            subject.verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
                tampered,
                replay_registration=fixture["replay_registration"],
                replay_registration_receipt=fixture["replay_receipt"],
                persistence_configuration=fixture["configuration"],
            )
        )

    def test_verifier_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        receipt = _build(fixture)
        receipt["authority"]["live_allowed"] = 0
        self.assertFalse(
            subject.verify_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
                receipt,
                replay_registration=fixture["replay_registration"],
                replay_registration_receipt=fixture["replay_receipt"],
                persistence_configuration=fixture["configuration"],
            )
        )

    def test_unknown_never_exposes_authority_or_storage_inputs(self) -> None:
        fixture = _fixture()
        fixture["configuration"] = None
        receipt = _build(fixture)
        self.assertEqual(receipt["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in receipt["facts"].values()))
        self.assertTrue(all(value is False for value in receipt["authority"].values()))
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("database", serialized)
        self.assertNotIn("private_key", serialized)


if __name__ == "__main__":
    unittest.main()
