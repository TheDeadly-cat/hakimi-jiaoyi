from __future__ import annotations

import copy
import hashlib
import json
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_adapter_registration_v1 import (
    ASSERTION_DIGEST_ALGORITHM,
    ASSERTION_DIGEST_ENCODING,
    CHECKPOINT_DOMAIN,
    CHECKPOINT_SIGNATURE_ALGORITHM,
    CHECKPOINT_SIGNATURE_ENCODING,
    CONSISTENCY_PROOF_PROTOCOL,
    EMPTY_DOMAIN,
    GENESIS_ROOT_HASH,
    INCLUSION_PROOF_PROTOCOL,
    LEAF_DOMAIN,
    LOG_PROTOCOL,
    NODE_DOMAIN,
    REGISTERED_STATUS,
    REGISTRATION_SCHEMA,
    STATIC_FINGERPRINT,
    UNKNOWN_STATUS,
    build_provider_identity_assertion_replay_adapter_registration_v1,
    verify_provider_identity_assertion_replay_adapter_registration_v1,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _registration() -> dict[str, object]:
    return {
        "replay_registry_id": "synthetic-provider-identity-replay-registry-v1",
        "replay_registry_namespace": "hakimi.synthetic.provider-identity-replay",
        "adapter_id": "synthetic-provider-identity-assertion-replay-adapter-v1",
        "adapter_implementation_hash": _digest("adapter-implementation"),
        "provider_receipt_signing_key_id": "synthetic-provider-receipt-key-v1",
        "provider_receipt_signing_public_key_hash": _digest("provider-receipt-key"),
        "identity_registry_trust_root_key_id": "synthetic-identity-registry-root-v1",
        "identity_registry_trust_root_public_key_hash": _digest("identity-registry-root"),
        "replay_registry_trust_root_key_id": "synthetic-replay-registry-root-v1",
        "replay_registry_trust_root_public_key_hash": _digest("replay-registry-root"),
        "assertion_digest_algorithm": ASSERTION_DIGEST_ALGORITHM,
        "assertion_digest_encoding": ASSERTION_DIGEST_ENCODING,
        "log_protocol": LOG_PROTOCOL,
        "inclusion_proof_protocol": INCLUSION_PROOF_PROTOCOL,
        "consistency_proof_protocol": CONSISTENCY_PROOF_PROTOCOL,
        "checkpoint_signature_algorithm": CHECKPOINT_SIGNATURE_ALGORITHM,
        "checkpoint_signature_encoding": CHECKPOINT_SIGNATURE_ENCODING,
        "empty_domain": EMPTY_DOMAIN,
        "leaf_domain": LEAF_DOMAIN,
        "node_domain": NODE_DOMAIN,
        "checkpoint_domain": CHECKPOINT_DOMAIN,
        "genesis_tree_size": 0,
        "genesis_root_hash": GENESIS_ROOT_HASH,
    }


class ProviderIdentityAssertionReplayAdapterRegistrationV1Tests(unittest.TestCase):
    def test_valid_registration_is_sealed_and_permission_negative(self) -> None:
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(_registration())
        self.assertEqual(receipt["schema"], REGISTRATION_SCHEMA)
        self.assertEqual(receipt["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(receipt["status"], REGISTERED_STATUS)
        self.assertRegex(receipt["receipt_hash"], r"^[0-9a-f]{64}$")
        self.assertTrue(receipt["facts"]["adapter_registration_sealed"])
        self.assertTrue(receipt["facts"]["key_roles_separated"])
        self.assertTrue(receipt["facts"]["empty_genesis_root_pinned"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_registration_is_deterministic(self) -> None:
        first = build_provider_identity_assertion_replay_adapter_registration_v1(_registration())
        second = build_provider_identity_assertion_replay_adapter_registration_v1(_registration())
        self.assertEqual(first, second)

    def test_registration_copies_caller_input(self) -> None:
        registration = _registration()
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(registration)
        registration["adapter_id"] = "mutated-adapter-v1"
        self.assertEqual(receipt["registration"]["adapter_id"], "synthetic-provider-identity-assertion-replay-adapter-v1")

    def test_missing_field_is_unknown(self) -> None:
        registration = _registration()
        registration.pop("consistency_proof_protocol")
        self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_extra_field_is_unknown(self) -> None:
        registration = _registration()
        registration["unregistered_compatibility_field"] = True
        self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_malformed_identifiers_are_unknown(self) -> None:
        for field in ("replay_registry_id", "replay_registry_namespace", "adapter_id", "provider_receipt_signing_key_id", "identity_registry_trust_root_key_id", "replay_registry_trust_root_key_id"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = "INVALID VALUE"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_malformed_hashes_are_unknown(self) -> None:
        for field in ("adapter_implementation_hash", "provider_receipt_signing_public_key_hash", "identity_registry_trust_root_public_key_hash", "replay_registry_trust_root_public_key_hash", "genesis_root_hash"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = "not-a-sha256"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_uppercase_hashes_are_unknown(self) -> None:
        registration = _registration()
        registration["adapter_implementation_hash"] = str(registration["adapter_implementation_hash"]).upper()
        self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_key_role_ids_must_be_pairwise_distinct(self) -> None:
        pairs = (("identity_registry_trust_root_key_id", "provider_receipt_signing_key_id"), ("replay_registry_trust_root_key_id", "provider_receipt_signing_key_id"), ("replay_registry_trust_root_key_id", "identity_registry_trust_root_key_id"))
        for target, source in pairs:
            with self.subTest(target=target, source=source):
                registration = _registration()
                registration[target] = registration[source]
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_key_role_hashes_must_be_pairwise_distinct(self) -> None:
        pairs = (("identity_registry_trust_root_public_key_hash", "provider_receipt_signing_public_key_hash"), ("replay_registry_trust_root_public_key_hash", "provider_receipt_signing_public_key_hash"), ("replay_registry_trust_root_public_key_hash", "identity_registry_trust_root_public_key_hash"))
        for target, source in pairs:
            with self.subTest(target=target, source=source):
                registration = _registration()
                registration[target] = registration[source]
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_log_protocol_mismatch_is_unknown(self) -> None:
        for field in ("log_protocol", "inclusion_proof_protocol", "consistency_proof_protocol"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = "legacy-or-unknown-protocol"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_assertion_digest_contract_mismatch_is_unknown(self) -> None:
        for field in ("assertion_digest_algorithm", "assertion_digest_encoding"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = "unsupported"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_checkpoint_signature_contract_mismatch_is_unknown(self) -> None:
        for field in ("checkpoint_signature_algorithm", "checkpoint_signature_encoding"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = "unsupported"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_domain_mismatch_is_unknown(self) -> None:
        for field in ("empty_domain", "leaf_domain", "node_domain", "checkpoint_domain"):
            with self.subTest(field=field):
                registration = _registration()
                registration[field] = str(registration[field]) + ".legacy"
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_genesis_tree_size_requires_native_zero(self) -> None:
        for value in (True, 0.0, -1, 1):
            with self.subTest(value=value):
                registration = _registration()
                registration["genesis_tree_size"] = value
                self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_genesis_root_is_exactly_pinned(self) -> None:
        registration = _registration()
        registration["genesis_root_hash"] = _digest("alternate-empty-root")
        self.assertEqual(build_provider_identity_assertion_replay_adapter_registration_v1(registration)["status"], UNKNOWN_STATUS)

    def test_verifier_accepts_only_exact_valid_receipt(self) -> None:
        registration = _registration()
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(registration)
        self.assertTrue(verify_provider_identity_assertion_replay_adapter_registration_v1(receipt, registration=registration))

    def test_verifier_rejects_tampering(self) -> None:
        registration = _registration()
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(registration)
        tampered = copy.deepcopy(receipt)
        tampered["facts"]["replay_receipt_observed"] = True
        self.assertFalse(verify_provider_identity_assertion_replay_adapter_registration_v1(tampered, registration=registration))
        numeric_alias = copy.deepcopy(receipt)
        numeric_alias["facts"]["replay_receipt_observed"] = 0
        self.assertFalse(
            verify_provider_identity_assertion_replay_adapter_registration_v1(
                numeric_alias,
                registration=registration,
            )
        )

    def test_verifier_rejects_unknown_registration_receipt(self) -> None:
        registration = _registration()
        registration.pop("adapter_id")
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(registration)
        self.assertFalse(verify_provider_identity_assertion_replay_adapter_registration_v1(receipt, registration=registration))

    def test_unknown_state_never_exposes_replay_or_permission_facts(self) -> None:
        receipt = build_provider_identity_assertion_replay_adapter_registration_v1(None)
        self.assertEqual(receipt["status"], UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in receipt["facts"].values()))
        self.assertTrue(all(value is False for value in receipt["authority"].values()))
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("secret", serialized)


if __name__ == "__main__":
    unittest.main()
