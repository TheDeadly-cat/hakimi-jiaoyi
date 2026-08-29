from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 as registration_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_receipt_verifier_v1 as subject


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _leaf_hash(assertion_hash: str) -> str:
    payload = (
        registration_contract.LEAF_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(assertion_hash)
    )
    return hashlib.sha256(payload).hexdigest()


def _node_hash(left: str, right: str) -> str:
    payload = (
        registration_contract.NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left)
        + bytes.fromhex(right)
    )
    return hashlib.sha256(payload).hexdigest()


def _split(size: int) -> int:
    return 1 << ((size - 1).bit_length() - 1)


def _tree_root(assertions: list[str]) -> str:
    if not assertions:
        return registration_contract.GENESIS_ROOT_HASH
    if len(assertions) == 1:
        return _leaf_hash(assertions[0])
    split = _split(len(assertions))
    return _node_hash(
        _tree_root(assertions[:split]),
        _tree_root(assertions[split:]),
    )


def _inclusion_proof(assertions: list[str], index: int) -> list[str]:
    if len(assertions) == 1:
        return []
    split = _split(len(assertions))
    if index < split:
        return _inclusion_proof(assertions[:split], index) + [
            _tree_root(assertions[split:])
        ]
    return _inclusion_proof(assertions[split:], index - split) + [
        _tree_root(assertions[:split])
    ]


def _consistency_subproof(
    old_size: int,
    assertions: list[str],
    complete_subtree: bool,
) -> list[str]:
    if old_size == len(assertions):
        return [] if complete_subtree else [_tree_root(assertions)]
    split = _split(len(assertions))
    if old_size <= split:
        return _consistency_subproof(
            old_size,
            assertions[:split],
            complete_subtree,
        ) + [_tree_root(assertions[split:])]
    return _consistency_subproof(
        old_size - split,
        assertions[split:],
        False,
    ) + [_tree_root(assertions[:split])]


def _consistency_proof(assertions: list[str], old_size: int) -> list[str]:
    if old_size == 0:
        return []
    return _consistency_subproof(old_size, assertions, True)


def _registration(public_key: bytes) -> dict[str, object]:
    return {
        "replay_registry_id": "synthetic-replay-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.provider-identity-replay",
        "adapter_id": "synthetic-provider-identity-replay-adapter-v1",
        "adapter_implementation_hash": _hash_text("adapter-implementation"),
        "provider_receipt_signing_key_id": "synthetic-provider-receipt-key-v1",
        "provider_receipt_signing_public_key_hash": _hash_text("provider-key"),
        "identity_registry_trust_root_key_id": "synthetic-identity-root-v1",
        "identity_registry_trust_root_public_key_hash": _hash_text("identity-root"),
        "replay_registry_trust_root_key_id": "synthetic-replay-root-v1",
        "replay_registry_trust_root_public_key_hash": hashlib.sha256(public_key).hexdigest(),
        "assertion_digest_algorithm": registration_contract.ASSERTION_DIGEST_ALGORITHM,
        "assertion_digest_encoding": registration_contract.ASSERTION_DIGEST_ENCODING,
        "log_protocol": registration_contract.LOG_PROTOCOL,
        "inclusion_proof_protocol": registration_contract.INCLUSION_PROOF_PROTOCOL,
        "consistency_proof_protocol": registration_contract.CONSISTENCY_PROOF_PROTOCOL,
        "checkpoint_signature_algorithm": registration_contract.CHECKPOINT_SIGNATURE_ALGORITHM,
        "checkpoint_signature_encoding": registration_contract.CHECKPOINT_SIGNATURE_ENCODING,
        "empty_domain": registration_contract.EMPTY_DOMAIN,
        "leaf_domain": registration_contract.LEAF_DOMAIN,
        "node_domain": registration_contract.NODE_DOMAIN,
        "checkpoint_domain": registration_contract.CHECKPOINT_DOMAIN,
        "genesis_tree_size": 0,
        "genesis_root_hash": registration_contract.GENESIS_ROOT_HASH,
    }


def _sign_checkpoint(
    private_key: Ed25519PrivateKey,
    unsigned: dict[str, object],
) -> dict[str, object]:
    canonical = json.dumps(
        unsigned,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    message = registration_contract.CHECKPOINT_DOMAIN.encode("ascii") + b"\x00" + canonical
    return {**unsigned, "signature": _b64url(private_key.sign(message))}


def _fixture(
    *,
    tree_size: int = 7,
    old_size: int = 3,
    leaf_index: int = 4,
) -> dict[str, object]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    registration = _registration(public_key)
    registration_receipt = registration_contract.build_provider_identity_assertion_replay_adapter_registration_v1(
        registration
    )
    assertions = [_hash_text(f"assertion-{index}") for index in range(tree_size)]
    unsigned = {
        "schema": subject.CHECKPOINT_SCHEMA,
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
        "tree_size": tree_size,
        "root_hash": _tree_root(assertions),
        "issued_at_ms": 1_700_000_000_000,
        "key_id": registration["replay_registry_trust_root_key_id"],
        "signature_algorithm": registration["checkpoint_signature_algorithm"],
        "signature_encoding": registration["checkpoint_signature_encoding"],
    }
    checkpoint = _sign_checkpoint(private_key, unsigned)
    replay_receipt = {
        "schema": subject.REPLAY_RECEIPT_SCHEMA,
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
        "adapter_id": registration["adapter_id"],
        "adapter_implementation_hash": registration["adapter_implementation_hash"],
        "assertion_receipt_hash": assertions[leaf_index],
        "leaf_index": leaf_index,
        "checkpoint": checkpoint,
        "inclusion_proof": _inclusion_proof(assertions, leaf_index),
        "consistency_proof": _consistency_proof(assertions, old_size),
    }
    pinned_checkpoint = {
        "schema": subject.PINNED_CHECKPOINT_SCHEMA,
        "replay_registry_id": registration["replay_registry_id"],
        "replay_registry_namespace": registration["replay_registry_namespace"],
        "tree_size": old_size,
        "root_hash": (
            registration_contract.GENESIS_ROOT_HASH
            if old_size == 0
            else _tree_root(assertions[:old_size])
        ),
    }
    return {
        "private_key": private_key,
        "public_key": _b64url(public_key),
        "registration": registration,
        "registration_receipt": registration_receipt,
        "replay_receipt": replay_receipt,
        "pinned_checkpoint": pinned_checkpoint,
    }


def _evaluate(fixture: dict[str, object]) -> dict[str, object]:
    return subject.evaluate_provider_identity_assertion_replay_receipt_v1(
        registration=fixture["registration"],
        registration_receipt=fixture["registration_receipt"],
        replay_receipt=fixture["replay_receipt"],
        replay_registry_public_key=fixture["public_key"],
        pinned_checkpoint=fixture["pinned_checkpoint"],
    )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayReceiptVerifierV1Tests(unittest.TestCase):
    def test_valid_receipt_verifies_crypto_only(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["checkpoint_signature_verified"])
        self.assertTrue(result["facts"]["assertion_inclusion_verified"])
        self.assertTrue(result["facts"]["append_only_consistency_verified"])
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_non_power_of_two_tree_all_leaf_indices(self) -> None:
        for leaf_index in range(7):
            with self.subTest(leaf_index=leaf_index):
                self.assertEqual(
                    _evaluate(_fixture(leaf_index=leaf_index))["status"],
                    subject.VERIFIED_STATUS,
                )

    def test_genesis_consistency_is_supported(self) -> None:
        self.assertEqual(
            _evaluate(_fixture(old_size=0))["status"],
            subject.VERIFIED_STATUS,
        )

    def test_same_checkpoint_requires_equal_root_and_empty_proof(self) -> None:
        self.assertEqual(
            _evaluate(_fixture(old_size=7))["status"],
            subject.VERIFIED_STATUS,
        )

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_output_verifier_accepts_exact_evaluation(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        self.assertTrue(
            subject.verify_provider_identity_assertion_replay_receipt_evaluation_v1(
                result,
                registration=fixture["registration"],
                registration_receipt=fixture["registration_receipt"],
                replay_receipt=fixture["replay_receipt"],
                replay_registry_public_key=fixture["public_key"],
                pinned_checkpoint=fixture["pinned_checkpoint"],
            )
        )

    def test_output_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        result["facts"]["replay_absence_verified"] = True
        self.assertFalse(
            subject.verify_provider_identity_assertion_replay_receipt_evaluation_v1(
                result,
                registration=fixture["registration"],
                registration_receipt=fixture["registration_receipt"],
                replay_receipt=fixture["replay_receipt"],
                replay_registry_public_key=fixture["public_key"],
                pinned_checkpoint=fixture["pinned_checkpoint"],
            )
        )

    def test_output_verifier_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        result["authority"]["live_allowed"] = 0
        self.assertFalse(
            subject.verify_provider_identity_assertion_replay_receipt_evaluation_v1(
                result,
                registration=fixture["registration"],
                registration_receipt=fixture["registration_receipt"],
                replay_receipt=fixture["replay_receipt"],
                replay_registry_public_key=fixture["public_key"],
                pinned_checkpoint=fixture["pinned_checkpoint"],
            )
        )

    def test_registration_receipt_must_verify(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["facts"]["key_roles_separated"] = False
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_public_key_must_match_registered_hash(self) -> None:
        fixture = _fixture()
        other = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        fixture["public_key"] = _b64url(other)
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_public_key_encoding_is_strict(self) -> None:
        for value in ("bad=", "*not-base64url*", "A"):
            with self.subTest(value=value):
                fixture = _fixture()
                fixture["public_key"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_signature_must_verify(self) -> None:
        fixture = _fixture()
        signature = fixture["replay_receipt"]["checkpoint"]["signature"]
        replacement = "A" if signature[0] != "A" else "B"
        fixture["replay_receipt"]["checkpoint"]["signature"] = replacement + signature[1:]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_signature_encoding_is_strict(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["checkpoint"]["signature"] += "="
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_key_role_must_match(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["checkpoint"]["key_id"] = fixture["registration"]["identity_registry_trust_root_key_id"]
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_registry_identity_must_match(self) -> None:
        for container in ("replay_receipt", "pinned_checkpoint"):
            with self.subTest(container=container):
                fixture = _fixture()
                target = fixture[container]
                if container == "replay_receipt":
                    target = target["checkpoint"]
                target["replay_registry_id"] = "other-registry-v1"
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_algorithm_contract_is_exact(self) -> None:
        for field in ("signature_algorithm", "signature_encoding"):
            with self.subTest(field=field):
                fixture = _fixture()
                fixture["replay_receipt"]["checkpoint"][field] = "legacy"
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_issued_at_requires_positive_native_int(self) -> None:
        for value in (True, 0, -1, 1.0):
            with self.subTest(value=value):
                fixture = _fixture()
                fixture["replay_receipt"]["checkpoint"]["issued_at_ms"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_receipt_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"].pop("consistency_proof")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture()
        fixture["replay_receipt"]["legacy"] = True
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_adapter_binding_is_exact(self) -> None:
        for field in ("adapter_id", "adapter_implementation_hash"):
            with self.subTest(field=field):
                fixture = _fixture()
                fixture["replay_receipt"][field] = (
                    "other-adapter-v1" if field == "adapter_id" else _hash_text("other")
                )
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_assertion_hash_is_lowercase_sha256(self) -> None:
        for value in ("not-a-hash", _hash_text("assertion").upper()):
            with self.subTest(value=value):
                fixture = _fixture()
                fixture["replay_receipt"]["assertion_receipt_hash"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_leaf_index_requires_native_in_range(self) -> None:
        for value in (True, -1, 7, 1.0):
            with self.subTest(value=value):
                fixture = _fixture()
                fixture["replay_receipt"]["leaf_index"] = value
                self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_inclusion_proof_rejects_wrong_or_extra_nodes(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["inclusion_proof"][0] = _hash_text("wrong")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture()
        fixture["replay_receipt"]["inclusion_proof"].append(_hash_text("extra"))
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_consistency_proof_rejects_wrong_or_extra_nodes(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["consistency_proof"][0] = _hash_text("wrong")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture()
        fixture["replay_receipt"]["consistency_proof"].append(_hash_text("extra"))
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_pinned_checkpoint_cannot_roll_back(self) -> None:
        fixture = _fixture()
        fixture["pinned_checkpoint"]["tree_size"] = 8
        fixture["pinned_checkpoint"]["root_hash"] = _hash_text("future-root")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_pinned_and_genesis_roots_are_exact(self) -> None:
        fixture = _fixture()
        fixture["pinned_checkpoint"]["root_hash"] = _hash_text("split-view")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)
        fixture = _fixture(old_size=0)
        fixture["pinned_checkpoint"]["root_hash"] = _hash_text("false-genesis")
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_unknown_never_exposes_authority_or_sensitive_material(self) -> None:
        fixture = _fixture()
        fixture["replay_receipt"]["inclusion_proof"] = []
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["facts"].values()))
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        checkpoint_signature = fixture["replay_receipt"]["checkpoint"]["signature"]
        self.assertNotIn(checkpoint_signature, serialized)
        self.assertNotIn(fixture["public_key"], serialized)
        self.assertNotIn('"inclusion_proof"', serialized)
        self.assertNotIn('"consistency_proof"', serialized)


if __name__ == "__main__":
    unittest.main()
