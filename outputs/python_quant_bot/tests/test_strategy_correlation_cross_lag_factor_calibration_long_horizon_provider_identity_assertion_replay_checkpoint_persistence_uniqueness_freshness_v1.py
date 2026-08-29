from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1 as lineage_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_registration_v1 as registration_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _sign(
    private_key: Ed25519PrivateKey,
    unsigned: dict[str, object],
    domain: str,
) -> dict[str, object]:
    canonical = json.dumps(
        unsigned,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **unsigned,
        "signature": _b64url(
            private_key.sign(domain.encode("ascii") + b"\x00" + canonical)
        ),
    }


def _fixture() -> dict[str, object]:
    occurrence_private = Ed25519PrivateKey.generate()
    time_private = Ed25519PrivateKey.generate()
    occurrence_public = _public_key(occurrence_private)
    time_public = _public_key(time_private)
    checkpoint = {
        "schema": "synthetic-checkpoint-v1",
        "issued_at_ms": 1_000,
        "tree_size": 4,
        "root_hash": _hash("checkpoint-root"),
    }
    checkpoint_hash = strict_canonical_hash(checkpoint)
    replay_registration_receipt_hash = _hash("replay-registration-receipt")
    persistence_registration_receipt_hash = _hash("persistence-registration-receipt")
    current_binding_receipt_hash = _hash("current-binding")
    lineage_evaluation = {
        "status": lineage_contract.VERIFIED_STATUS,
        "receipt_hash": _hash("lineage-evaluation"),
        "evidence": {
            "current_binding_receipt_hash": current_binding_receipt_hash,
            "replay_registry_id": "synthetic-registry-v1",
            "replay_registry_namespace": "hakimi.synthetic.identity-replay",
            "current_tree_size": 4,
            "current_root_hash": checkpoint["root_hash"],
            "current_checkpoint_hash": checkpoint_hash,
        },
    }
    replay_registration = {
        "provider_receipt_signing_key_id": "synthetic-provider-key-v1",
        "provider_receipt_signing_public_key_hash": _hash("provider-key"),
        "identity_registry_trust_root_key_id": "synthetic-identity-root-v1",
        "identity_registry_trust_root_public_key_hash": _hash("identity-root"),
        "replay_registry_trust_root_key_id": "synthetic-replay-root-v1",
        "replay_registry_trust_root_public_key_hash": _hash("replay-root"),
    }
    current_segment = {
        "binding": {"receipt_hash": current_binding_receipt_hash},
        "replay_inputs": {
            "registration": replay_registration,
            "registration_receipt": {
                "receipt_hash": replay_registration_receipt_hash
            },
            "replay_receipt": {
                "assertion_receipt_hash": _hash("assertion-receipt"),
                "leaf_index": 2,
                "checkpoint": checkpoint,
            },
        },
        "persistence_inputs": {
            "persistence_configuration": {
                "persistence_provider_key_id": "synthetic-persistence-key-v1",
                "persistence_provider_public_key_hash": _hash("persistence-key"),
            },
            "persistence_registration_receipt": {
                "receipt_hash": persistence_registration_receipt_hash
            },
        },
    }
    registration = {
        "schema": registration_contract.REGISTRATION_SCHEMA,
        "adapter_id": "synthetic-uniqueness-freshness-adapter-v1",
        "adapter_implementation_hash": _hash("uniqueness-freshness-adapter"),
        "source_lineage_schema": registration_contract.SOURCE_LINEAGE_SCHEMA,
        "source_lineage_static_fingerprint": registration_contract.SOURCE_LINEAGE_STATIC_FINGERPRINT,
        "source_replay_registration_receipt_hash": replay_registration_receipt_hash,
        "source_persistence_registration_receipt_hash": persistence_registration_receipt_hash,
        "occurrence_provider_id": "synthetic-occurrence-provider-v1",
        "occurrence_namespace": "hakimi.synthetic.occurrence-index",
        "occurrence_provider_key_id": "synthetic-occurrence-key-v1",
        "occurrence_provider_public_key_hash": hashlib.sha256(occurrence_public).hexdigest(),
        "time_authority_id": "synthetic-time-authority-v1",
        "time_namespace": "hakimi.synthetic.time-authority",
        "time_authority_key_id": "synthetic-time-key-v1",
        "time_authority_public_key_hash": hashlib.sha256(time_public).hexdigest(),
        "occurrence_receipt_schema": registration_contract.OCCURRENCE_RECEIPT_SCHEMA,
        "time_receipt_schema": registration_contract.TIME_RECEIPT_SCHEMA,
        "signature_algorithm": registration_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": registration_contract.SIGNATURE_ENCODING,
        "canonical_hash_algorithm": registration_contract.CANONICAL_HASH_ALGORITHM,
        "canonical_hash_encoding": registration_contract.CANONICAL_HASH_ENCODING,
        "scan_policy": registration_contract.SCAN_POLICY,
        "cardinality_policy": registration_contract.CARDINALITY_POLICY,
        "time_window_policy": registration_contract.TIME_WINDOW_POLICY,
        "occurrence_signature_domain": registration_contract.OCCURRENCE_SIGNATURE_DOMAIN,
        "time_signature_domain": registration_contract.TIME_SIGNATURE_DOMAIN,
        "max_checkpoint_age_ms": 500,
        "max_occurrence_to_reference_delay_ms": 100,
    }
    registration_receipt = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(
        registration
    )
    occurrence_unsigned = {
        "schema": registration_contract.OCCURRENCE_RECEIPT_SCHEMA,
        "lineage_receipt_hash": lineage_evaluation["receipt_hash"],
        "current_binding_receipt_hash": current_binding_receipt_hash,
        "replay_registration_receipt_hash": replay_registration_receipt_hash,
        "replay_registry_id": lineage_evaluation["evidence"]["replay_registry_id"],
        "replay_registry_namespace": lineage_evaluation["evidence"]["replay_registry_namespace"],
        "checkpoint_tree_size": 4,
        "checkpoint_root_hash": checkpoint["root_hash"],
        "checkpoint_hash": checkpoint_hash,
        "assertion_receipt_hash": current_segment["replay_inputs"]["replay_receipt"]["assertion_receipt_hash"],
        "assertion_leaf_index": 2,
        "scan_start_index": 0,
        "scan_end_index_exclusive": 4,
        "index_snapshot_record_count": 4,
        "index_snapshot_root_hash": _hash("occurrence-index-root"),
        "occurrence_count": 1,
        "occurrence_leaf_indices": [2],
        "scan_completed_at_ms": 1_200,
        "provider_id": registration["occurrence_provider_id"],
        "occurrence_namespace": registration["occurrence_namespace"],
        "key_id": registration["occurrence_provider_key_id"],
        "scan_policy": registration_contract.SCAN_POLICY,
        "cardinality_policy": registration_contract.CARDINALITY_POLICY,
        "signature_algorithm": registration_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": registration_contract.SIGNATURE_ENCODING,
    }
    occurrence_receipt = _sign(
        occurrence_private,
        occurrence_unsigned,
        registration_contract.OCCURRENCE_SIGNATURE_DOMAIN,
    )
    time_unsigned = {
        "schema": registration_contract.TIME_RECEIPT_SCHEMA,
        "lineage_receipt_hash": lineage_evaluation["receipt_hash"],
        "occurrence_receipt_hash": strict_canonical_hash(occurrence_receipt),
        "checkpoint_hash": checkpoint_hash,
        "checkpoint_issued_at_ms": 1_000,
        "scan_completed_at_ms": 1_200,
        "reference_time_ms": 1_250,
        "max_checkpoint_age_ms": 500,
        "max_occurrence_to_reference_delay_ms": 100,
        "authority_id": registration["time_authority_id"],
        "time_namespace": registration["time_namespace"],
        "key_id": registration["time_authority_key_id"],
        "time_window_policy": registration_contract.TIME_WINDOW_POLICY,
        "signature_algorithm": registration_contract.SIGNATURE_ALGORITHM,
        "signature_encoding": registration_contract.SIGNATURE_ENCODING,
    }
    time_receipt = _sign(
        time_private,
        time_unsigned,
        registration_contract.TIME_SIGNATURE_DOMAIN,
    )
    return {
        "occurrence_private": occurrence_private,
        "time_private": time_private,
        "lineage_evaluation": lineage_evaluation,
        "current_segment": current_segment,
        "registration": registration,
        "registration_receipt": registration_receipt,
        "occurrence_receipt": occurrence_receipt,
        "occurrence_public": _b64url(occurrence_public),
        "time_receipt": time_receipt,
        "time_public": _b64url(time_public),
    }


def _inputs(fixture: dict[str, object]) -> dict[str, object]:
    return {
        "lineage_evaluation": fixture["lineage_evaluation"],
        "current_segment": fixture["current_segment"],
        "evidence_registration": fixture["registration"],
        "evidence_registration_receipt": fixture["registration_receipt"],
        "occurrence_receipt": fixture["occurrence_receipt"],
        "occurrence_provider_public_key": fixture["occurrence_public"],
        "time_receipt": fixture["time_receipt"],
        "time_authority_public_key": fixture["time_public"],
    }


def _evaluate(fixture: dict[str, object], *, lineage_ok: bool = True) -> dict[str, object]:
    with patch.object(
        subject.lineage_contract,
        "verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1",
        return_value=lineage_ok,
    ):
        return subject.evaluate_provider_identity_assertion_uniqueness_freshness_evidence_v1(
            **_inputs(fixture)
        )


def _resign_occurrence(fixture: dict[str, object]) -> None:
    unsigned = {
        key: value
        for key, value in fixture["occurrence_receipt"].items()
        if key != "signature"
    }
    fixture["occurrence_receipt"] = _sign(
        fixture["occurrence_private"],
        unsigned,
        registration_contract.OCCURRENCE_SIGNATURE_DOMAIN,
    )


def _resign_time(fixture: dict[str, object], *, rebind_occurrence: bool = False) -> None:
    unsigned = {
        key: value for key, value in fixture["time_receipt"].items() if key != "signature"
    }
    if rebind_occurrence:
        unsigned["occurrence_receipt_hash"] = strict_canonical_hash(
            fixture["occurrence_receipt"]
        )
    fixture["time_receipt"] = _sign(
        fixture["time_private"],
        unsigned,
        registration_contract.TIME_SIGNATURE_DOMAIN,
    )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionReplayCheckpointPersistenceUniquenessFreshnessV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_configuration(self) -> None:
        fixture = _fixture()
        receipt = fixture["registration_receipt"]
        self.assertEqual(receipt["status"], registration_contract.REGISTERED_STATUS)
        self.assertTrue(
            registration_contract.verify_provider_identity_assertion_uniqueness_freshness_registration_v1(
                receipt,
                registration=fixture["registration"],
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        fixture = _fixture()
        fixture["registration"]["extra"] = True
        receipt = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(receipt["status"], registration_contract.UNKNOWN_STATUS)

    def test_registration_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_checkpoint_age_ms"] = True
        receipt = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(receipt["status"], registration_contract.UNKNOWN_STATUS)

    def test_registration_rejects_role_key_id_collision(self) -> None:
        fixture = _fixture()
        fixture["registration"]["time_authority_key_id"] = fixture["registration"]["occurrence_provider_key_id"]
        receipt = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(receipt["reason"], "registration_role_key_ids_not_distinct")

    def test_registration_rejects_role_key_hash_collision(self) -> None:
        fixture = _fixture()
        fixture["registration"]["time_authority_public_key_hash"] = fixture["registration"]["occurrence_provider_public_key_hash"]
        receipt = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(
            fixture["registration"]
        )
        self.assertEqual(receipt["reason"], "registration_role_key_hashes_not_distinct")

    def test_registration_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["status"] = "TAMPERED"
        self.assertFalse(
            registration_contract.verify_provider_identity_assertion_uniqueness_freshness_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_registered_receipt_never_exposes_authority(self) -> None:
        authority = _fixture()["registration_receipt"]["authority"]
        self.assertTrue(all(value is False for value in authority.values()))

    def test_signed_claims_verify_without_promoting_authority(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["complete_scan_claim_verified"])
        self.assertTrue(result["facts"]["exactly_one_occurrence_claim_verified"])
        self.assertTrue(result["facts"]["time_window_claim_verified"])
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertFalse(result["facts"]["freshness_verified"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_evaluation_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        with patch.object(
            subject.lineage_contract,
            "verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1",
            return_value=True,
        ):
            self.assertTrue(
                subject.verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1(
                    result,
                    **_inputs(fixture),
                )
            )

    def test_evaluation_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        result = _evaluate(fixture)
        result["facts"]["assertion_uniqueness_verified"] = True
        with patch.object(
            subject.lineage_contract,
            "verify_provider_identity_assertion_replay_checkpoint_persistence_lineage_v1",
            return_value=True,
        ):
            self.assertFalse(
                subject.verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1(
                    result,
                    **_inputs(fixture),
                )
            )

    def test_lineage_verifier_is_required(self) -> None:
        self.assertEqual(_evaluate(_fixture(), lineage_ok=False)["reason"], "lineage_evaluation_unverified")

    def test_verified_lineage_status_is_required(self) -> None:
        fixture = _fixture()
        fixture["lineage_evaluation"]["status"] = lineage_contract.UNKNOWN_STATUS
        self.assertEqual(_evaluate(fixture)["status"], subject.UNKNOWN_STATUS)

    def test_registration_receipt_is_required(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["receipt_hash"] = _hash("tampered")
        self.assertEqual(_evaluate(fixture)["reason"], "evidence_registration_unverified")

    def test_source_replay_registration_must_match(self) -> None:
        fixture = _fixture()
        fixture["registration"]["source_replay_registration_receipt_hash"] = _hash("other-replay")
        fixture["registration_receipt"] = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(fixture["registration"])
        self.assertEqual(_evaluate(fixture)["reason"], "source_replay_registration_mismatch")

    def test_source_persistence_registration_must_match(self) -> None:
        fixture = _fixture()
        fixture["registration"]["source_persistence_registration_receipt_hash"] = _hash("other-persistence")
        fixture["registration_receipt"] = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(fixture["registration"])
        self.assertEqual(_evaluate(fixture)["reason"], "source_persistence_registration_mismatch")

    def test_witness_key_hash_must_not_collide_with_upstream(self) -> None:
        fixture = _fixture()
        fixture["registration"]["occurrence_provider_public_key_hash"] = fixture["current_segment"]["replay_inputs"]["registration"]["replay_registry_trust_root_public_key_hash"]
        fixture["registration_receipt"] = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(fixture["registration"])
        self.assertEqual(_evaluate(fixture)["reason"], "witness_key_hash_role_collision")

    def test_witness_key_id_must_not_collide_with_upstream(self) -> None:
        fixture = _fixture()
        fixture["registration"]["occurrence_provider_key_id"] = fixture["current_segment"]["replay_inputs"]["registration"]["replay_registry_trust_root_key_id"]
        fixture["registration_receipt"] = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(fixture["registration"])
        self.assertEqual(_evaluate(fixture)["reason"], "witness_key_id_role_collision")

    def test_occurrence_receipt_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["extra"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_receipt_shape_invalid")

    def test_occurrence_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["signature"] = _b64url(b"tampered")
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_signature_invalid")

    def test_occurrence_public_key_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["occurrence_public"] = fixture["time_public"]
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_signature_invalid")

    def test_scan_must_start_at_zero(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["scan_start_index"] = 1
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_scan_start_index_mismatch")

    def test_scan_end_must_equal_checkpoint_tree_size(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["scan_end_index_exclusive"] = 3
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_scan_end_index_exclusive_mismatch")

    def test_snapshot_record_count_rejects_bool_int_alias(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["index_snapshot_record_count"] = True
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_index_snapshot_record_count_mismatch")

    def test_occurrence_count_must_be_exactly_one(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["occurrence_count"] = 2
        fixture["occurrence_receipt"]["occurrence_leaf_indices"] = [2, 3]
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_occurrence_count_mismatch")

    def test_occurrence_leaf_index_must_match_replay_leaf(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["occurrence_leaf_indices"] = [1]
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_occurrence_leaf_indices_mismatch")

    def test_assertion_hash_is_bound_to_lineage_segment(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["assertion_receipt_hash"] = _hash("other-assertion")
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_assertion_receipt_hash_mismatch")

    def test_checkpoint_content_is_bound_to_lineage(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["checkpoint_root_hash"] = _hash("other-root")
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "occurrence_checkpoint_root_hash_mismatch")

    def test_time_receipt_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["time_receipt"]["extra"] = True
        self.assertEqual(_evaluate(fixture)["reason"], "time_receipt_shape_invalid")

    def test_time_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["time_receipt"]["signature"] = _b64url(b"tampered")
        self.assertEqual(_evaluate(fixture)["reason"], "time_signature_invalid")

    def test_time_public_key_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["time_public"] = fixture["occurrence_public"]
        self.assertEqual(_evaluate(fixture)["reason"], "time_signature_invalid")

    def test_time_receipt_binds_occurrence_receipt_hash(self) -> None:
        fixture = _fixture()
        fixture["occurrence_receipt"]["index_snapshot_root_hash"] = _hash("new-index-root")
        _resign_occurrence(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "time_occurrence_receipt_hash_mismatch")

    def test_time_order_is_strictly_bounded(self) -> None:
        fixture = _fixture()
        fixture["time_receipt"]["reference_time_ms"] = 1_100
        _resign_time(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "time_order_invalid")

    def test_checkpoint_age_must_not_exceed_registration(self) -> None:
        fixture = _fixture()
        fixture["time_receipt"]["reference_time_ms"] = 1_600
        _resign_time(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "time_checkpoint_age_exceeds_registration")

    def test_occurrence_delay_must_not_exceed_registration(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_checkpoint_age_ms"] = 1_000
        fixture["registration"]["max_occurrence_to_reference_delay_ms"] = 100
        fixture["registration_receipt"] = registration_contract.build_provider_identity_assertion_uniqueness_freshness_registration_v1(fixture["registration"])
        fixture["time_receipt"]["max_checkpoint_age_ms"] = 1_000
        fixture["time_receipt"]["reference_time_ms"] = 1_350
        _resign_time(fixture)
        self.assertEqual(_evaluate(fixture)["reason"], "time_occurrence_delay_exceeds_registration")

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_unknown_never_exposes_inputs_or_authority(self) -> None:
        result = subject.evaluate_provider_identity_assertion_uniqueness_freshness_evidence_v1(
            lineage_evaluation=None,
            current_segment=None,
            evidence_registration=None,
            evidence_registration_receipt=None,
            occurrence_receipt=None,
            occurrence_provider_public_key=None,
            time_receipt=None,
            time_authority_public_key=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn('"current_segment":', serialized)
        self.assertNotIn('"occurrence_receipt":', serialized)
        self.assertNotIn('"time_receipt":', serialized)


if __name__ == "__main__":
    unittest.main()
