from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 as replay_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_registration_v1 as persistence_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_receipt_verifier_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _source_registration() -> dict[str, object]:
    return {
        "replay_registry_id": "synthetic-replay-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.replay",
        "adapter_id": "synthetic-replay-adapter-v1",
        "adapter_implementation_hash": _hash("replay-adapter"),
        "provider_receipt_signing_key_id": "synthetic-provider-key-v1",
        "provider_receipt_signing_public_key_hash": _hash("provider-key"),
        "identity_registry_trust_root_key_id": "synthetic-identity-key-v1",
        "identity_registry_trust_root_public_key_hash": _hash("identity-key"),
        "replay_registry_trust_root_key_id": "synthetic-replay-key-v1",
        "replay_registry_trust_root_public_key_hash": _hash("replay-key"),
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


def _configuration(source_hash: str, public_key: bytes) -> dict[str, object]:
    return {
        "persistence_provider_id": "synthetic-store-v1",
        "persistence_namespace": "hakimi.synthetic.checkpoints",
        "adapter_id": "synthetic-persistence-adapter-v1",
        "adapter_implementation_hash": _hash("persistence-adapter"),
        "persistence_provider_key_id": "synthetic-persistence-key-v1",
        "persistence_provider_public_key_hash": hashlib.sha256(public_key).hexdigest(),
        "source_replay_registration_receipt_hash": source_hash,
        "canonical_hash_algorithm": persistence_contract.CANONICAL_HASH_ALGORITHM,
        "canonical_hash_encoding": persistence_contract.CANONICAL_HASH_ENCODING,
        "signature_algorithm": persistence_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": persistence_contract.SIGNATURE_ENCODING,
        "pinned_asset_schema": persistence_contract.PINNED_ASSET_SCHEMA,
        "write_receipt_schema": persistence_contract.WRITE_RECEIPT_SCHEMA,
        "reopen_receipt_schema": persistence_contract.REOPEN_RECEIPT_SCHEMA,
        "session_policy": persistence_contract.SESSION_POLICY,
        "cardinality_policy": persistence_contract.CARDINALITY_POLICY,
        "record_replay_policy": persistence_contract.RECORD_REPLAY_POLICY,
        "timestamp_order_policy": persistence_contract.TIMESTAMP_ORDER_POLICY,
        "provider_mode": persistence_contract.PROVIDER_MODE,
    }


def _sign(private_key: Ed25519PrivateKey, unsigned: dict[str, object]) -> dict[str, object]:
    message = (
        str(unsigned["schema"]).encode("ascii")
        + b"\x00"
        + json.dumps(
            unsigned,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {**unsigned, "signature": _b64url(private_key.sign(message))}


def _fixture() -> dict[str, object]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    replay_registration = _source_registration()
    replay_receipt = replay_contract.build_provider_identity_assertion_replay_adapter_registration_v1(
        replay_registration
    )
    configuration = _configuration(replay_receipt["receipt_hash"], public_key)
    persistence_receipt = persistence_contract.build_provider_identity_assertion_replay_checkpoint_persistence_registration_v1(
        replay_registration=replay_registration,
        replay_registration_receipt=replay_receipt,
        persistence_configuration=configuration,
    )
    asset = seal_strict_canonical_document(
        {
            "schema": persistence_contract.PINNED_ASSET_SCHEMA,
            "replay_registry_id": replay_registration["replay_registry_id"],
            "replay_registry_namespace": replay_registration["replay_registry_namespace"],
            "tree_size": 7,
            "root_hash": _hash("checkpoint-root"),
            "checkpoint_hash": _hash("checkpoint"),
            "source_replay_verifier_receipt_hash": _hash("replay-verifier-receipt"),
            "previous_pinned_asset_hash": None,
            "asset_created_at_ms": 1_000,
        },
        "asset_hash",
    )
    write_unsigned = {
        "schema": persistence_contract.WRITE_RECEIPT_SCHEMA,
        "operation": "WRITE",
        "persistence_provider_id": configuration["persistence_provider_id"],
        "persistence_namespace": configuration["persistence_namespace"],
        "adapter_id": configuration["adapter_id"],
        "asset_hash": asset["asset_hash"],
        "record_hash": asset["asset_hash"],
        "record_count": 1,
        "session_id": "synthetic-write-session-v1",
        "written_at_ms": 2_000,
        "key_id": configuration["persistence_provider_key_id"],
        "signature_algorithm": configuration["signature_algorithm"],
        "signature_encoding": configuration["signature_encoding"],
    }
    write_receipt = _sign(private_key, write_unsigned)
    reopen_unsigned = {
        "schema": persistence_contract.REOPEN_RECEIPT_SCHEMA,
        "operation": "REOPEN",
        "persistence_provider_id": configuration["persistence_provider_id"],
        "persistence_namespace": configuration["persistence_namespace"],
        "adapter_id": configuration["adapter_id"],
        "asset_hash": asset["asset_hash"],
        "record_hash": asset["asset_hash"],
        "record_count": 1,
        "session_id": "synthetic-reopen-session-v1",
        "reopened_at_ms": 3_000,
        "source_write_receipt_hash": strict_canonical_hash(write_receipt),
        "key_id": configuration["persistence_provider_key_id"],
        "signature_algorithm": configuration["signature_algorithm"],
        "signature_encoding": configuration["signature_encoding"],
    }
    reopen_receipt = _sign(private_key, reopen_unsigned)
    return {
        "private_key": private_key,
        "public_key": _b64url(public_key),
        "replay_registration": replay_registration,
        "replay_receipt": replay_receipt,
        "configuration": configuration,
        "persistence_receipt": persistence_receipt,
        "asset": asset,
        "write": write_receipt,
        "reopen": reopen_receipt,
    }


def _evaluate(fixture: dict[str, object]) -> dict[str, object]:
    return subject.evaluate_provider_identity_assertion_replay_checkpoint_persistence_receipts_v1(
        replay_registration=fixture["replay_registration"],
        replay_registration_receipt=fixture["replay_receipt"],
        persistence_configuration=fixture["configuration"],
        persistence_registration_receipt=fixture["persistence_receipt"],
        persistence_provider_public_key=fixture["public_key"],
        checkpoint_asset=fixture["asset"],
        write_receipt=fixture["write"],
        reopen_receipt=fixture["reopen"],
    )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceReceiptVerifierV1Tests(unittest.TestCase):
    def test_valid_receipts_verify_crypto_contract_only(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["write_receipt_signature_verified"])
        self.assertTrue(result["facts"]["reopen_receipt_signature_verified"])
        self.assertTrue(result["facts"]["exact_record_replay_verified"])
        self.assertFalse(result["facts"]["external_durability_attested"])
        self.assertFalse(result["facts"]["source_replay_evaluation_verified"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_output_verifier_accepts_exact_evaluation(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        self.assertTrue(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1(
            result,
            replay_registration=fixture["replay_registration"],
            replay_registration_receipt=fixture["replay_receipt"],
            persistence_configuration=fixture["configuration"],
            persistence_registration_receipt=fixture["persistence_receipt"],
            persistence_provider_public_key=fixture["public_key"],
            checkpoint_asset=fixture["asset"],
            write_receipt=fixture["write"],
            reopen_receipt=fixture["reopen"],
        ))

    def test_output_verifier_rejects_tampering(self) -> None:
        fixture = _fixture(); result = _evaluate(fixture)
        result["facts"]["external_durability_attested"] = True
        self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1(
            result, replay_registration=fixture["replay_registration"], replay_registration_receipt=fixture["replay_receipt"], persistence_configuration=fixture["configuration"], persistence_registration_receipt=fixture["persistence_receipt"], persistence_provider_public_key=fixture["public_key"], checkpoint_asset=fixture["asset"], write_receipt=fixture["write"], reopen_receipt=fixture["reopen"]))

    def test_output_verifier_rejects_bool_int_alias(self) -> None:
        fixture = _fixture(); result = _evaluate(fixture)
        result["authority"]["live_allowed"] = 0
        self.assertFalse(subject.verify_provider_identity_assertion_replay_checkpoint_persistence_evaluation_v1(
            result, replay_registration=fixture["replay_registration"], replay_registration_receipt=fixture["replay_receipt"], persistence_configuration=fixture["configuration"], persistence_registration_receipt=fixture["persistence_receipt"], persistence_provider_public_key=fixture["public_key"], checkpoint_asset=fixture["asset"], write_receipt=fixture["write"], reopen_receipt=fixture["reopen"]))

    def test_persistence_registration_receipt_must_verify(self) -> None:
        fixture = _fixture(); fixture["persistence_receipt"]["facts"]["persistence_key_role_separated"] = False
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_provider_public_key_must_match_registered_hash(self) -> None:
        fixture = _fixture()
        other = Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        fixture["public_key"] = _b64url(other)
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_provider_public_key_encoding_is_strict(self) -> None:
        for value in ("bad=", "*bad*", "A"):
            with self.subTest(value=value):
                fixture = _fixture(); fixture["public_key"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["asset"]["path"] = "forbidden"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_seal_must_verify(self) -> None:
        fixture = _fixture(); fixture["asset"]["root_hash"] = _hash("tampered-root")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_registry_identity_must_match_source(self) -> None:
        for field in ("replay_registry_id", "replay_registry_namespace"):
            with self.subTest(field=field):
                fixture = _fixture(); fixture["asset"][field] = "other-registry-v1"
                fixture["asset"] = seal_strict_canonical_document({key: value for key, value in fixture["asset"].items() if key != "asset_hash"}, "asset_hash")
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_native_values_are_strict(self) -> None:
        for field, value in (("tree_size", True), ("tree_size", 0), ("asset_created_at_ms", True), ("asset_created_at_ms", 0)):
            with self.subTest(field=field, value=value):
                fixture = _fixture(); fixture["asset"][field] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_previous_hash_is_strict(self) -> None:
        fixture = _fixture(); fixture["asset"]["previous_pinned_asset_hash"] = "bad"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_write_receipt_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["write"]["storage_path"] = "forbidden"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_reopen_receipt_shape_is_exact(self) -> None:
        fixture = _fixture(); fixture["reopen"].pop("source_write_receipt_hash")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_provider_binding_is_exact(self) -> None:
        for target in ("write", "reopen"):
            with self.subTest(target=target):
                fixture = _fixture(); fixture[target]["persistence_provider_id"] = "other-provider-v1"
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_adapter_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["write"]["adapter_id"] = "other-adapter-v1"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_key_role_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["reopen"]["key_id"] = fixture["replay_registration"]["replay_registry_trust_root_key_id"]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_signature_contract_is_exact(self) -> None:
        for target in ("write", "reopen"):
            with self.subTest(target=target):
                fixture = _fixture(); fixture[target]["signature_algorithm"] = "legacy"
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_write_signature_must_verify(self) -> None:
        fixture = _fixture(); signature = fixture["write"]["signature"]
        fixture["write"]["signature"] = ("A" if signature[0] != "A" else "B") + signature[1:]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_reopen_signature_must_verify(self) -> None:
        fixture = _fixture(); signature = fixture["reopen"]["signature"]
        fixture["reopen"]["signature"] = ("A" if signature[0] != "A" else "B") + signature[1:]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_asset_hash_binding_is_exact(self) -> None:
        fixture = _fixture(); fixture["write"]["asset_hash"] = _hash("other-asset")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_record_hash_replay_is_exact(self) -> None:
        fixture = _fixture(); fixture["reopen"]["record_hash"] = _hash("other-record")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_cardinality_requires_native_one(self) -> None:
        for target, value in (("write", 0), ("write", True), ("reopen", 2), ("reopen", True)):
            with self.subTest(target=target, value=value):
                fixture = _fixture(); fixture[target]["record_count"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_sessions_are_strict_and_distinct(self) -> None:
        fixture = _fixture(); fixture["reopen"]["session_id"] = fixture["write"]["session_id"]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(); fixture["write"]["session_id"] = "INVALID VALUE"
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_timestamp_order_and_native_types_are_strict(self) -> None:
        fixture = _fixture(); fixture["reopen"]["reopened_at_ms"] = fixture["write"]["written_at_ms"]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(); fixture["write"]["written_at_ms"] = True
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(); fixture["write"]["written_at_ms"] = 500
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_source_write_receipt_hash_must_match(self) -> None:
        fixture = _fixture(); fixture["reopen"]["source_write_receipt_hash"] = _hash("other-write")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_unknown_never_exposes_authority_or_sensitive_material(self) -> None:
        fixture = _fixture(); fixture["write"]["record_count"] = 0
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["facts"].values()))
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(fixture["public_key"], serialized)
        self.assertNotIn(fixture["write"]["signature"], serialized)
        self.assertNotIn(fixture["reopen"]["signature"], serialized)
        self.assertNotIn("storage_path", serialized)


if __name__ == "__main__":
    unittest.main()
