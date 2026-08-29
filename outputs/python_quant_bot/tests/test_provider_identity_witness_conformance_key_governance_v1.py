from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import provider_identity_witness_conformance_key_governance_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document


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


def _sealed_source(schema: str, status: str, evidence: dict[str, object]) -> dict[str, object]:
    return seal_strict_canonical_document(
        {
            "schema": schema,
            "static_fingerprint": _hash(schema),
            "status": status,
            "reason": None,
            "facts": {},
            "evidence": evidence,
            "authority": {"paper_allowed": False, "live_allowed": False},
        },
        "receipt_hash",
    )


def _fixture() -> dict[str, object]:
    occurrence_private = Ed25519PrivateKey.generate()
    time_private = Ed25519PrivateKey.generate()
    conformance_private = Ed25519PrivateKey.generate()
    governance_private = Ed25519PrivateKey.generate()
    occurrence_public = _public_key(occurrence_private)
    time_public = _public_key(time_private)
    conformance_public = _public_key(conformance_private)
    governance_public = _public_key(governance_private)

    source_registration = {
        "occurrence_provider_id": "synthetic-occurrence-provider-v1",
        "occurrence_provider_key_id": "synthetic-occurrence-key-v1",
        "occurrence_provider_public_key_hash": hashlib.sha256(occurrence_public).hexdigest(),
        "time_authority_id": "synthetic-time-authority-v1",
        "time_authority_key_id": "synthetic-time-key-v1",
        "time_authority_public_key_hash": hashlib.sha256(time_public).hexdigest(),
    }
    source_registration_receipt = _sealed_source(
        subject.source_registration_contract.RECEIPT_SCHEMA,
        subject.source_registration_contract.REGISTERED_STATUS,
        {},
    )
    source_longitudinal_registration = {
        "source_evidence_registration_receipt_hash": source_registration_receipt[
            "receipt_hash"
        ]
    }
    source_longitudinal_registration_receipt = _sealed_source(
        subject.source_coverage_contract.REGISTRATION_RECEIPT_SCHEMA,
        subject.source_coverage_contract.REGISTERED_STATUS,
        {},
    )
    source_longitudinal_evaluation_receipt = _sealed_source(
        subject.source_coverage_contract.EVALUATION_SCHEMA,
        subject.source_coverage_contract.VERIFIED_STATUS,
        {
            "source_evidence_registration_receipt_hash": source_registration_receipt[
                "receipt_hash"
            ],
            "coverage_registration_receipt_hash": source_longitudinal_registration_receipt[
                "receipt_hash"
            ],
        },
    )
    registration = {
        "schema": subject.REGISTRATION_SCHEMA,
        "adapter_id": "synthetic-witness-audit-consumer-v1",
        "adapter_implementation_hash": _hash("witness-audit-consumer"),
        "source_evidence_registration_receipt_schema": subject.source_registration_contract.RECEIPT_SCHEMA,
        "source_evidence_registration_static_fingerprint": subject.source_registration_contract.STATIC_FINGERPRINT,
        "source_evidence_registration_receipt_hash": source_registration_receipt[
            "receipt_hash"
        ],
        "source_longitudinal_coverage_evaluation_schema": subject.source_coverage_contract.EVALUATION_SCHEMA,
        "source_longitudinal_coverage_static_fingerprint": subject.source_coverage_contract.STATIC_FINGERPRINT,
        "source_longitudinal_coverage_evaluation_receipt_hash": source_longitudinal_evaluation_receipt[
            "receipt_hash"
        ],
        "occurrence_provider_id": source_registration["occurrence_provider_id"],
        "occurrence_provider_key_id": source_registration["occurrence_provider_key_id"],
        "occurrence_provider_public_key_hash": source_registration[
            "occurrence_provider_public_key_hash"
        ],
        "occurrence_provider_implementation_hash": _hash("occurrence-provider-implementation"),
        "time_authority_id": source_registration["time_authority_id"],
        "time_authority_key_id": source_registration["time_authority_key_id"],
        "time_authority_public_key_hash": source_registration[
            "time_authority_public_key_hash"
        ],
        "time_authority_implementation_hash": _hash("time-authority-implementation"),
        "conformance_auditor_id": "synthetic-conformance-auditor-v1",
        "conformance_auditor_key_id": "synthetic-conformance-auditor-key-v1",
        "conformance_auditor_public_key_hash": hashlib.sha256(conformance_public).hexdigest(),
        "governance_auditor_id": "synthetic-governance-auditor-v1",
        "governance_auditor_key_id": "synthetic-governance-auditor-key-v1",
        "governance_auditor_public_key_hash": hashlib.sha256(governance_public).hexdigest(),
        "occurrence_audit_run_id": "synthetic-occurrence-conformance-run-v1",
        "occurrence_conformance_suite_id": "synthetic-occurrence-suite-v1",
        "occurrence_conformance_suite_hash": _hash("occurrence-suite"),
        "occurrence_required_vector_count": 32,
        "time_audit_run_id": "synthetic-time-conformance-run-v1",
        "time_conformance_suite_id": "synthetic-time-suite-v1",
        "time_conformance_suite_hash": _hash("time-suite"),
        "time_required_vector_count": 24,
        "governance_audit_run_id": "synthetic-key-governance-run-v1",
        "key_ceremony_id": "synthetic-key-ceremony-v1",
        "key_ceremony_transcript_hash": _hash("key-ceremony-transcript"),
        "rotation_policy_id": "synthetic-rotation-policy-v1",
        "rotation_policy_hash": _hash("rotation-policy"),
        "revocation_registry_id": "synthetic-revocation-registry-v1",
        "custody_policy_id": "synthetic-custody-policy-v1",
        "custody_policy_hash": _hash("custody-policy"),
        "occurrence_key_epoch": 1,
        "occurrence_previous_key_commitment": _hash("previous-occurrence-key"),
        "time_authority_key_epoch": 0,
        "time_authority_previous_key_commitment": subject.GENESIS_COMMITMENT,
        "key_valid_from_ms": 500,
        "key_valid_until_ms": 5_000,
        "conformance_receipt_schema": subject.CONFORMANCE_RECEIPT_SCHEMA,
        "governance_receipt_schema": subject.GOVERNANCE_RECEIPT_SCHEMA,
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
        "canonical_hash_algorithm": subject.CANONICAL_HASH_ALGORITHM,
        "canonical_hash_encoding": subject.CANONICAL_HASH_ENCODING,
        "conformance_signature_domain": subject.CONFORMANCE_SIGNATURE_DOMAIN,
        "governance_signature_domain": subject.GOVERNANCE_SIGNATURE_DOMAIN,
        "max_audit_duration_ms": 500,
        "max_receipt_issue_delay_ms": 100,
        "max_audit_age_ms": 1_000,
        "max_revocation_snapshot_age_ms": 1_000,
    }
    registration_receipt = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
        registration
    )

    def conformance_unsigned(role: str) -> dict[str, object]:
        prefix = "occurrence" if role == "occurrence_provider" else "time"
        entity_prefix = "occurrence_provider" if role == "occurrence_provider" else "time_authority"
        started_at = 1_000 if role == "occurrence_provider" else 1_200
        return {
            "schema": subject.CONFORMANCE_RECEIPT_SCHEMA,
            "audit_registration_receipt_hash": registration_receipt["receipt_hash"],
            "source_evidence_registration_receipt_hash": registration[
                "source_evidence_registration_receipt_hash"
            ],
            "source_longitudinal_coverage_evaluation_receipt_hash": registration[
                "source_longitudinal_coverage_evaluation_receipt_hash"
            ],
            "audit_run_id": registration[f"{prefix}_audit_run_id"],
            "target_role": role,
            "target_entity_id": registration[f"{entity_prefix}_id"],
            "target_key_id": registration[f"{entity_prefix}_key_id"],
            "target_public_key_hash": registration[f"{entity_prefix}_public_key_hash"],
            "target_implementation_hash": registration[f"{entity_prefix}_implementation_hash"],
            "audit_suite_id": registration[f"{prefix}_conformance_suite_id"],
            "audit_suite_hash": registration[f"{prefix}_conformance_suite_hash"],
            "test_vector_count": registration[f"{prefix}_required_vector_count"],
            "passed_vector_count": registration[f"{prefix}_required_vector_count"],
            "failed_vector_count": 0,
            "started_at_ms": started_at,
            "completed_at_ms": started_at + 100,
            "issued_at_ms": started_at + 150,
            "auditor_id": registration["conformance_auditor_id"],
            "auditor_key_id": registration["conformance_auditor_key_id"],
            "signature_algorithm": subject.SIGNATURE_ALGORITHM,
            "signature_encoding": subject.SIGNATURE_ENCODING,
        }

    occurrence_conformance_receipt = _sign(
        conformance_private,
        conformance_unsigned("occurrence_provider"),
        subject.CONFORMANCE_SIGNATURE_DOMAIN,
    )
    time_conformance_receipt = _sign(
        conformance_private,
        conformance_unsigned("time_authority"),
        subject.CONFORMANCE_SIGNATURE_DOMAIN,
    )
    governance_unsigned = {
        "schema": subject.GOVERNANCE_RECEIPT_SCHEMA,
        "audit_registration_receipt_hash": registration_receipt["receipt_hash"],
        "source_evidence_registration_receipt_hash": registration[
            "source_evidence_registration_receipt_hash"
        ],
        "source_longitudinal_coverage_evaluation_receipt_hash": registration[
            "source_longitudinal_coverage_evaluation_receipt_hash"
        ],
        "audit_run_id": registration["governance_audit_run_id"],
        "occurrence_provider_id": registration["occurrence_provider_id"],
        "occurrence_provider_key_id": registration["occurrence_provider_key_id"],
        "occurrence_provider_public_key_hash": registration[
            "occurrence_provider_public_key_hash"
        ],
        "occurrence_key_epoch": registration["occurrence_key_epoch"],
        "occurrence_previous_key_commitment": registration[
            "occurrence_previous_key_commitment"
        ],
        "time_authority_id": registration["time_authority_id"],
        "time_authority_key_id": registration["time_authority_key_id"],
        "time_authority_public_key_hash": registration["time_authority_public_key_hash"],
        "time_authority_key_epoch": registration["time_authority_key_epoch"],
        "time_authority_previous_key_commitment": registration[
            "time_authority_previous_key_commitment"
        ],
        "key_valid_from_ms": registration["key_valid_from_ms"],
        "key_valid_until_ms": registration["key_valid_until_ms"],
        "key_ceremony_id": registration["key_ceremony_id"],
        "key_ceremony_transcript_hash": registration["key_ceremony_transcript_hash"],
        "rotation_policy_id": registration["rotation_policy_id"],
        "rotation_policy_hash": registration["rotation_policy_hash"],
        "revocation_registry_id": registration["revocation_registry_id"],
        "revocation_snapshot_hash": _hash("revocation-snapshot"),
        "revocation_snapshot_at_ms": 1_400,
        "occurrence_key_revoked": False,
        "time_authority_key_revoked": False,
        "custody_policy_id": registration["custody_policy_id"],
        "custody_policy_hash": registration["custody_policy_hash"],
        "custody_domains_separated": True,
        "audit_completed_at_ms": 1_450,
        "issued_at_ms": 1_500,
        "auditor_id": registration["governance_auditor_id"],
        "auditor_key_id": registration["governance_auditor_key_id"],
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
    }
    key_governance_receipt = _sign(
        governance_private,
        governance_unsigned,
        subject.GOVERNANCE_SIGNATURE_DOMAIN,
    )
    return {
        "conformance_private": conformance_private,
        "governance_private": governance_private,
        "registration": registration,
        "registration_receipt": registration_receipt,
        "source_evidence_registration": source_registration,
        "source_evidence_registration_receipt": source_registration_receipt,
        "source_longitudinal_registration": source_longitudinal_registration,
        "source_longitudinal_registration_receipt": source_longitudinal_registration_receipt,
        "source_longitudinal_evaluations": [],
        "source_longitudinal_evaluation_receipt": source_longitudinal_evaluation_receipt,
        "occurrence_conformance_receipt": occurrence_conformance_receipt,
        "time_conformance_receipt": time_conformance_receipt,
        "conformance_auditor_public_key": _b64url(conformance_public),
        "key_governance_receipt": key_governance_receipt,
        "governance_auditor_public_key": _b64url(governance_public),
        "reference_time_ms": 2_000,
    }


def _inputs(fixture: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in fixture.items()
        if key not in {"conformance_private", "governance_private"}
    }


def _evaluate(
    fixture: dict[str, object],
    *,
    source_registration_ok: bool = True,
    source_coverage_registration_ok: bool = True,
    source_coverage_evaluation_ok: bool = True,
) -> dict[str, object]:
    with (
        patch.object(
            subject.source_registration_contract,
            "verify_provider_identity_assertion_uniqueness_freshness_registration_v1",
            return_value=source_registration_ok,
        ),
        patch.object(
            subject.source_coverage_contract,
            "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1",
            return_value=source_coverage_registration_ok,
        ),
        patch.object(
            subject.source_coverage_contract,
            "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1",
            return_value=source_coverage_evaluation_ok,
        ),
    ):
        return subject.evaluate_provider_identity_witness_conformance_key_governance_v1(
            **_inputs(fixture)
        )


def _resign_conformance(fixture: dict[str, object], key: str) -> None:
    unsigned = {
        field: value
        for field, value in fixture[key].items()
        if field != "signature"
    }
    fixture[key] = _sign(
        fixture["conformance_private"],
        unsigned,
        subject.CONFORMANCE_SIGNATURE_DOMAIN,
    )


def _resign_governance(fixture: dict[str, object]) -> None:
    unsigned = {
        field: value
        for field, value in fixture["key_governance_receipt"].items()
        if field != "signature"
    }
    fixture["key_governance_receipt"] = _sign(
        fixture["governance_private"],
        unsigned,
        subject.GOVERNANCE_SIGNATURE_DOMAIN,
    )


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityWitnessConformanceKeyGovernanceV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_preregistered_scope(self) -> None:
        fixture = _fixture()
        self.assertEqual(fixture["registration_receipt"]["status"], subject.REGISTERED_STATUS)
        self.assertTrue(
            subject.verify_provider_identity_witness_conformance_key_governance_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        registration = _fixture()["registration"]
        registration["extra"] = True
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_shape_invalid")

    def test_registration_rejects_bool_vector_count(self) -> None:
        registration = _fixture()["registration"]
        registration["occurrence_required_vector_count"] = True
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"],
            "registration_occurrence_required_vector_count_invalid",
        )

    def test_registration_rejects_key_id_role_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["governance_auditor_key_id"] = registration["time_authority_key_id"]
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_key_ids_not_distinct")

    def test_registration_rejects_key_hash_role_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["governance_auditor_public_key_hash"] = registration[
            "time_authority_public_key_hash"
        ]
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_key_hashes_not_distinct")

    def test_registration_rejects_entity_role_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["governance_auditor_id"] = registration["occurrence_provider_id"]
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_entity_ids_not_distinct")

    def test_registration_rejects_reused_audit_run(self) -> None:
        registration = _fixture()["registration"]
        registration["governance_audit_run_id"] = registration["time_audit_run_id"]
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_audit_run_ids_not_distinct")

    def test_registration_requires_genesis_marker_for_epoch_zero(self) -> None:
        registration = _fixture()["registration"]
        registration["time_authority_previous_key_commitment"] = _hash("not-genesis")
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"],
            "registration_time_authority_previous_key_commitment_invalid",
        )

    def test_registration_requires_hash_for_rotated_key(self) -> None:
        registration = _fixture()["registration"]
        registration["occurrence_previous_key_commitment"] = subject.GENESIS_COMMITMENT
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"],
            "registration_occurrence_previous_key_commitment_invalid",
        )

    def test_registration_requires_forward_validity_window(self) -> None:
        registration = _fixture()["registration"]
        registration["key_valid_until_ms"] = registration["key_valid_from_ms"]
        result = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_key_validity_window_invalid")

    def test_registration_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["status"] = "TAMPERED"
        self.assertFalse(
            subject.verify_provider_identity_witness_conformance_key_governance_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_registration_receipt_binds_complete_registration(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_audit_age_ms"] += 1
        self.assertFalse(
            subject.verify_provider_identity_witness_conformance_key_governance_registration_v1(
                fixture["registration_receipt"],
                registration=fixture["registration"],
            )
        )

    def test_evaluation_rejects_coordinated_registration_drift(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_audit_age_ms"] += 1
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "audit_registration_receipt_invalid")

    def test_signed_claims_verify_without_promoting_external_trust(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["conformance_suites_and_vectors_bound"])
        self.assertTrue(result["facts"]["rotation_lineage_claims_bound"])
        self.assertTrue(result["facts"]["non_revocation_claims_bound"])
        self.assertFalse(result["facts"]["external_conformance_auditor_trust_attested"])
        self.assertFalse(result["facts"]["external_governance_auditor_trust_attested"])
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertFalse(result["facts"]["freshness_verified"])
        self.assertFalse(result["authority"]["paper_allowed"])
        self.assertFalse(result["authority"]["live_allowed"])

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_evaluation_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        receipt = _evaluate(fixture)
        with (
            patch.object(
                subject.source_registration_contract,
                "verify_provider_identity_assertion_uniqueness_freshness_registration_v1",
                return_value=True,
            ),
            patch.object(
                subject.source_coverage_contract,
                "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1",
                return_value=True,
            ),
            patch.object(
                subject.source_coverage_contract,
                "verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1",
                return_value=True,
            ),
        ):
            self.assertTrue(
                subject.verify_provider_identity_witness_conformance_key_governance_evaluation_v1(
                    receipt,
                    **_inputs(fixture),
                )
            )

    def test_evaluation_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        receipt = _evaluate(fixture)
        receipt["facts"]["freshness_verified"] = True
        with patch.object(
            subject,
            "evaluate_provider_identity_witness_conformance_key_governance_v1",
            return_value=_evaluate(fixture),
        ):
            self.assertFalse(
                subject.verify_provider_identity_witness_conformance_key_governance_evaluation_v1(
                    receipt,
                    **_inputs(fixture),
                )
            )

    def test_source_registration_verifier_is_required(self) -> None:
        result = _evaluate(_fixture(), source_registration_ok=False)
        self.assertEqual(result["reason"], "source_evidence_registration_not_verified")

    def test_source_coverage_registration_verifier_is_required(self) -> None:
        result = _evaluate(_fixture(), source_coverage_registration_ok=False)
        self.assertEqual(result["reason"], "source_longitudinal_registration_not_verified")

    def test_source_coverage_evaluation_verifier_is_required(self) -> None:
        result = _evaluate(_fixture(), source_coverage_evaluation_ok=False)
        self.assertEqual(result["reason"], "source_longitudinal_evaluation_not_verified")

    def test_source_status_is_required(self) -> None:
        fixture = _fixture()
        fixture["source_longitudinal_evaluation_receipt"]["status"] = "UNKNOWN"
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_longitudinal_evaluation_status_invalid")

    def test_source_registration_receipt_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_evidence_registration_receipt"]["receipt_hash"] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_evidence_registration_receipt_hash_mismatch")

    def test_source_longitudinal_receipt_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_longitudinal_evaluation_receipt"]["receipt_hash"] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_longitudinal_evaluation_receipt_hash_mismatch")

    def test_source_longitudinal_registration_binds_source(self) -> None:
        fixture = _fixture()
        fixture["source_longitudinal_registration"][
            "source_evidence_registration_receipt_hash"
        ] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_longitudinal_registration_binding_mismatch")

    def test_source_longitudinal_evaluation_binds_source(self) -> None:
        fixture = _fixture()
        fixture["source_longitudinal_evaluation_receipt"]["evidence"][
            "source_evidence_registration_receipt_hash"
        ] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_longitudinal_evaluation_binding_mismatch")

    def test_source_occurrence_key_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_evidence_registration"]["occurrence_provider_key_id"] = "other-key-v1"
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_occurrence_provider_key_id_mismatch")

    def test_source_time_authority_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_evidence_registration"]["time_authority_id"] = "other-time-v1"
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_time_authority_id_mismatch")

    def test_conformance_receipt_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["occurrence_conformance_receipt"]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "occurrence_provider_conformance_receipt_shape_invalid")

    def test_conformance_target_role_is_bound(self) -> None:
        fixture = _fixture()
        fixture["occurrence_conformance_receipt"]["target_role"] = "time_authority"
        _resign_conformance(fixture, "occurrence_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"],
            "occurrence_provider_conformance_target_role_mismatch",
        )

    def test_conformance_implementation_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["time_conformance_receipt"]["target_implementation_hash"] = _hash("other")
        _resign_conformance(fixture, "time_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"],
            "time_authority_conformance_target_implementation_hash_mismatch",
        )

    def test_conformance_suite_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["time_conformance_receipt"]["audit_suite_hash"] = _hash("other")
        _resign_conformance(fixture, "time_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_conformance_vector_count_rejects_bool_alias(self) -> None:
        fixture = _fixture()
        fixture["occurrence_conformance_receipt"]["test_vector_count"] = True
        _resign_conformance(fixture, "occurrence_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_conformance_requires_all_vectors_to_pass(self) -> None:
        fixture = _fixture()
        fixture["occurrence_conformance_receipt"]["passed_vector_count"] = 31
        fixture["occurrence_conformance_receipt"]["failed_vector_count"] = 1
        _resign_conformance(fixture, "occurrence_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_conformance_time_order_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["time_conformance_receipt"]["completed_at_ms"] = 1_100
        _resign_conformance(fixture, "time_conformance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "time_authority_conformance_time_order_invalid")

    def test_conformance_audit_age_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["reference_time_ms"] = 2_500
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "occurrence_provider_conformance_audit_age_exceeded")

    def test_conformance_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["occurrence_conformance_receipt"]["signature"] = fixture[
            "time_conformance_receipt"
        ]["signature"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "occurrence_provider_conformance_signature_invalid")

    def test_conformance_public_key_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["conformance_auditor_public_key"] = fixture["governance_auditor_public_key"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "occurrence_provider_conformance_signature_invalid")

    def test_governance_receipt_shape_is_exact(self) -> None:
        fixture = _fixture()
        del fixture["key_governance_receipt"]["custody_policy_hash"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_receipt_shape_invalid")

    def test_governance_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["signature"] = fixture[
            "occurrence_conformance_receipt"
        ]["signature"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_signature_invalid")

    def test_governance_rotation_epoch_is_bound(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["occurrence_key_epoch"] = 2
        _resign_governance(fixture)
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_occurrence_key_epoch_mismatch")

    def test_governance_previous_key_commitment_is_bound(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["occurrence_previous_key_commitment"] = _hash(
            "other"
        )
        _resign_governance(fixture)
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"],
            "governance_occurrence_previous_key_commitment_mismatch",
        )

    def test_governance_rejects_revoked_occurrence_key(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["occurrence_key_revoked"] = True
        _resign_governance(fixture)
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_occurrence_key_revoked_mismatch")

    def test_governance_rejects_revoked_time_key(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["time_authority_key_revoked"] = True
        _resign_governance(fixture)
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_time_authority_key_revoked_mismatch")

    def test_governance_requires_custody_separation(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["custody_domains_separated"] = False
        _resign_governance(fixture)
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_custody_domains_separated_mismatch")

    def test_governance_revocation_snapshot_is_freshly_bounded(self) -> None:
        fixture = _fixture()
        fixture["key_governance_receipt"]["revocation_snapshot_at_ms"] = 900
        _resign_governance(fixture)
        fixture["reference_time_ms"] = 2_000
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "governance_revocation_snapshot_age_exceeded")

    def test_governance_reference_time_must_be_inside_key_validity(self) -> None:
        fixture = _fixture()
        fixture["registration"]["key_valid_until_ms"] = 1_900
        fixture["registration_receipt"] = subject.build_provider_identity_witness_conformance_key_governance_registration_v1(
            fixture["registration"]
        )
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_unknown_never_exposes_claims_or_authority(self) -> None:
        result = subject.evaluate_provider_identity_witness_conformance_key_governance_v1(
            registration=None,
            registration_receipt=None,
            source_evidence_registration=None,
            source_evidence_registration_receipt=None,
            source_longitudinal_registration=None,
            source_longitudinal_registration_receipt=None,
            source_longitudinal_evaluations=None,
            source_longitudinal_evaluation_receipt=None,
            occurrence_conformance_receipt=None,
            time_conformance_receipt=None,
            conformance_auditor_public_key=None,
            key_governance_receipt=None,
            governance_auditor_public_key=None,
            reference_time_ms=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is None for value in result["evidence"].values()))
        self.assertFalse(result["facts"]["assertion_uniqueness_verified"])
        self.assertFalse(result["authority"]["paper_allowed"])
        self.assertFalse(result["authority"]["live_allowed"])


if __name__ == "__main__":
    unittest.main()
