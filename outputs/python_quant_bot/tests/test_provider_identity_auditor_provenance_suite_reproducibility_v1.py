from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import provider_identity_auditor_provenance_suite_reproducibility_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from tests import test_provider_identity_witness_conformance_key_governance_v1 as source_test


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def _sign(
    private_key: Ed25519PrivateKey, unsigned: dict[str, object], domain: str,
) -> dict[str, object]:
    canonical = json.dumps(
        unsigned, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **unsigned,
        "signature": _b64url(
            private_key.sign(domain.encode("ascii") + b"\x00" + canonical)
        ),
    }


def _role(
    role: str, private_key: Ed25519PrivateKey | None = None,
    *, entity_id: str | None = None, key_id: str | None = None,
    public_key_hash: str | None = None,
) -> dict[str, object]:
    role_token = role.replace("source_", "")
    if public_key_hash is None:
        assert private_key is not None
        public_key_hash = hashlib.sha256(_public_key(private_key)).hexdigest()
    runner = role in subject.RUNNER_ROLES
    return {
        "role": role,
        "entity_id": entity_id or f"synthetic-{role_token}-entity-v1",
        "key_id": key_id or f"synthetic-{role_token}-key-v1",
        "public_key_hash": public_key_hash,
        "organization_id": f"synthetic-{role_token}-organization-v1",
        "control_group_id": f"synthetic-{role_token}-control-v1",
        "beneficial_owner_disclosure_hash": _hash(f"{role}-beneficial-owner"),
        "runner_implementation_manifest_hash": _hash(f"{role}-implementation") if runner else None,
        "runner_environment_manifest_hash": _hash(f"{role}-environment") if runner else None,
        "execution_id": f"synthetic-{role_token}-execution-v1" if runner else None,
    }


def _fixture() -> dict[str, object]:
    source_fixture = source_test._fixture()
    source_inputs = source_test._inputs(source_fixture)
    source_evaluation = source_test._evaluate(source_fixture)
    source_registration = source_inputs["registration"]

    registry_private = Ed25519PrivateKey.generate()
    custodian_private = Ed25519PrivateKey.generate()
    runner_a_private = Ed25519PrivateKey.generate()
    runner_b_private = Ed25519PrivateKey.generate()
    roles = [
        _role(
            "source_conformance_auditor",
            entity_id=source_registration["conformance_auditor_id"],
            key_id=source_registration["conformance_auditor_key_id"],
            public_key_hash=source_registration["conformance_auditor_public_key_hash"],
        ),
        _role(
            "source_governance_auditor",
            entity_id=source_registration["governance_auditor_id"],
            key_id=source_registration["governance_auditor_key_id"],
            public_key_hash=source_registration["governance_auditor_public_key_hash"],
        ),
        _role("provenance_registry_authority", registry_private),
        _role("suite_custodian", custodian_private),
        _role("runner_a", runner_a_private),
        _role("runner_b", runner_b_private),
    ]
    requirements = [
        {"requirement_id": "occurrence-cardinality", "requirement_digest": _hash("requirement-occurrence")},
        {"requirement_id": "time-window", "requirement_digest": _hash("requirement-time")},
    ]
    vectors = [
        {
            "vector_id": "occurrence-negative", "requirement_id": "occurrence-cardinality",
            "polarity": "negative", "input_hash": _hash("occurrence-negative-input"),
            "expected_result_hash": _hash("occurrence-negative-result"),
        },
        {
            "vector_id": "occurrence-positive", "requirement_id": "occurrence-cardinality",
            "polarity": "positive", "input_hash": _hash("occurrence-positive-input"),
            "expected_result_hash": _hash("occurrence-positive-result"),
        },
        {
            "vector_id": "time-negative", "requirement_id": "time-window",
            "polarity": "negative", "input_hash": _hash("time-negative-input"),
            "expected_result_hash": _hash("time-negative-result"),
        },
        {
            "vector_id": "time-positive", "requirement_id": "time-window",
            "polarity": "positive", "input_hash": _hash("time-positive-input"),
            "expected_result_hash": _hash("time-positive-result"),
        },
    ]
    registration = {
        "schema": subject.REGISTRATION_SCHEMA,
        "adapter_id": "synthetic-provenance-suite-consumer-v1",
        "adapter_implementation_hash": _hash("provenance-suite-consumer"),
        "source_witness_audit_registration_receipt_schema": subject.source_contract.REGISTRATION_RECEIPT_SCHEMA,
        "source_witness_audit_evaluation_schema": subject.source_contract.EVALUATION_SCHEMA,
        "source_witness_audit_static_fingerprint": subject.source_contract.STATIC_FINGERPRINT,
        "source_witness_audit_registration_receipt_hash": source_inputs[
            "registration_receipt"
        ]["receipt_hash"],
        "source_witness_audit_evaluation_receipt_hash": source_evaluation["receipt_hash"],
        "occurrence_provider_implementation_hash": source_registration[
            "occurrence_provider_implementation_hash"
        ],
        "time_authority_implementation_hash": source_registration[
            "time_authority_implementation_hash"
        ],
        "role_registrations": roles,
        "conflict_registry_id": "synthetic-conflict-registry-v1",
        "suite_id": "synthetic-provider-suite-v1",
        "suite_version": "suite-v1",
        "protocol_id": "synthetic-provider-protocol-v1",
        "protocol_version": "protocol-v1",
        "requirement_manifest_root_hash": strict_canonical_hash(requirements),
        "expected_requirement_count": 2,
        "vector_corpus_root_hash": strict_canonical_hash(vectors),
        "expected_vector_count": 4,
        "expected_positive_vector_count": 2,
        "expected_negative_vector_count": 2,
        "minimum_positive_vectors_per_requirement": 1,
        "minimum_negative_vectors_per_requirement": 1,
        "coverage_policy": subject.COVERAGE_POLICY,
        "result_policy": subject.RESULT_POLICY,
        "provenance_receipt_schema": subject.PROVENANCE_RECEIPT_SCHEMA,
        "suite_manifest_receipt_schema": subject.SUITE_MANIFEST_RECEIPT_SCHEMA,
        "runner_receipt_schema": subject.RUNNER_RECEIPT_SCHEMA,
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
        "canonical_hash_algorithm": subject.CANONICAL_HASH_ALGORITHM,
        "canonical_hash_encoding": subject.CANONICAL_HASH_ENCODING,
        "provenance_signature_domain": subject.PROVENANCE_SIGNATURE_DOMAIN,
        "suite_signature_domain": subject.SUITE_SIGNATURE_DOMAIN,
        "runner_signature_domain_prefix": subject.RUNNER_SIGNATURE_DOMAIN_PREFIX,
        "max_provenance_snapshot_age_ms": 500,
        "max_receipt_age_ms": 1_000,
        "max_receipt_issue_delay_ms": 100,
        "max_runner_duration_ms": 500,
    }
    registration_receipt = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
        registration
    )
    provenance_unsigned = {
        "schema": subject.PROVENANCE_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_receipt["receipt_hash"],
        "source_witness_audit_evaluation_receipt_hash": source_evaluation["receipt_hash"],
        "role_registrations": copy.deepcopy(roles),
        "conflict_registry_id": registration["conflict_registry_id"],
        "conflict_registry_snapshot_hash": _hash("conflict-snapshot"),
        "conflict_registry_snapshot_at_ms": 1_000,
        "declared_common_control": False,
        "declared_conflict_of_interest": False,
        "issued_at_ms": 1_100,
        "authority_id": roles[2]["entity_id"],
        "authority_key_id": roles[2]["key_id"],
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
    }
    provenance_receipt = _sign(
        registry_private, provenance_unsigned, subject.PROVENANCE_SIGNATURE_DOMAIN
    )
    suite_unsigned = {
        "schema": subject.SUITE_MANIFEST_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_receipt["receipt_hash"],
        "source_witness_audit_evaluation_receipt_hash": source_evaluation["receipt_hash"],
        "suite_id": registration["suite_id"],
        "suite_version": registration["suite_version"],
        "protocol_id": registration["protocol_id"],
        "protocol_version": registration["protocol_version"],
        "occurrence_provider_implementation_hash": registration[
            "occurrence_provider_implementation_hash"
        ],
        "time_authority_implementation_hash": registration[
            "time_authority_implementation_hash"
        ],
        "requirements": requirements,
        "vectors": vectors,
        "requirement_manifest_root_hash": registration["requirement_manifest_root_hash"],
        "requirement_count": 2,
        "vector_corpus_root_hash": registration["vector_corpus_root_hash"],
        "vector_count": 4,
        "positive_vector_count": 2,
        "negative_vector_count": 2,
        "coverage_policy": subject.COVERAGE_POLICY,
        "issued_at_ms": 1_200,
        "custodian_id": roles[3]["entity_id"],
        "custodian_key_id": roles[3]["key_id"],
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
    }
    suite_receipt = _sign(custodian_private, suite_unsigned, subject.SUITE_SIGNATURE_DOMAIN)
    results = [
        {
            "vector_id": vector["vector_id"],
            "actual_result_hash": vector["expected_result_hash"],
            "passed": True,
            "skipped": False,
        }
        for vector in vectors
    ]

    def runner_unsigned(role: str, started_at: int) -> dict[str, object]:
        runner = roles[subject.ROLE_ORDER.index(role)]
        return {
            "schema": subject.RUNNER_RECEIPT_SCHEMA,
            "registration_receipt_hash": registration_receipt["receipt_hash"],
            "source_witness_audit_evaluation_receipt_hash": source_evaluation["receipt_hash"],
            "suite_manifest_receipt_hash": strict_canonical_hash(suite_receipt),
            "requirement_manifest_root_hash": registration["requirement_manifest_root_hash"],
            "vector_corpus_root_hash": registration["vector_corpus_root_hash"],
            "runner_role": role,
            "runner_id": runner["entity_id"],
            "runner_organization_id": runner["organization_id"],
            "runner_control_group_id": runner["control_group_id"],
            "runner_key_id": runner["key_id"],
            "runner_implementation_manifest_hash": runner[
                "runner_implementation_manifest_hash"
            ],
            "runner_environment_manifest_hash": runner[
                "runner_environment_manifest_hash"
            ],
            "execution_id": runner["execution_id"],
            "started_at_ms": started_at,
            "completed_at_ms": started_at + 100,
            "issued_at_ms": started_at + 150,
            "results": copy.deepcopy(results),
            "result_count": 4,
            "passed_count": 4,
            "failed_count": 0,
            "skipped_count": 0,
            "result_transcript_root_hash": strict_canonical_hash(results),
            "result_policy": subject.RESULT_POLICY,
            "signature_algorithm": subject.SIGNATURE_ALGORITHM,
            "signature_encoding": subject.SIGNATURE_ENCODING,
        }

    runner_a_receipt = _sign(
        runner_a_private, runner_unsigned("runner_a", 1_300),
        f"{subject.RUNNER_SIGNATURE_DOMAIN_PREFIX}.runner_a",
    )
    runner_b_receipt = _sign(
        runner_b_private, runner_unsigned("runner_b", 1_350),
        f"{subject.RUNNER_SIGNATURE_DOMAIN_PREFIX}.runner_b",
    )
    return {
        "registry_private": registry_private,
        "custodian_private": custodian_private,
        "runner_a_private": runner_a_private,
        "runner_b_private": runner_b_private,
        "registration": registration,
        "registration_receipt": registration_receipt,
        "source_witness_audit_inputs": source_inputs,
        "source_witness_audit_evaluation_receipt": source_evaluation,
        "provenance_receipt": provenance_receipt,
        "provenance_registry_public_key": _b64url(_public_key(registry_private)),
        "suite_manifest_receipt": suite_receipt,
        "suite_custodian_public_key": _b64url(_public_key(custodian_private)),
        "runner_a_receipt": runner_a_receipt,
        "runner_a_public_key": _b64url(_public_key(runner_a_private)),
        "runner_b_receipt": runner_b_receipt,
        "runner_b_public_key": _b64url(_public_key(runner_b_private)),
        "reference_time_ms": 2_000,
    }


def _inputs(fixture: dict[str, object]) -> dict[str, object]:
    private_keys = {
        "registry_private", "custodian_private", "runner_a_private", "runner_b_private"
    }
    return {key: value for key, value in fixture.items() if key not in private_keys}


def _evaluate(fixture: dict[str, object], *, source_ok: bool = True) -> dict[str, object]:
    with patch.object(
        subject.source_contract,
        "verify_provider_identity_witness_conformance_key_governance_evaluation_v1",
        return_value=source_ok,
    ):
        return subject.evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1(
            **_inputs(fixture)
        )


def _resign(fixture: dict[str, object], key: str) -> None:
    settings = {
        "provenance_receipt": (
            "registry_private", subject.PROVENANCE_SIGNATURE_DOMAIN
        ),
        "suite_manifest_receipt": (
            "custodian_private", subject.SUITE_SIGNATURE_DOMAIN
        ),
        "runner_a_receipt": (
            "runner_a_private", f"{subject.RUNNER_SIGNATURE_DOMAIN_PREFIX}.runner_a"
        ),
        "runner_b_receipt": (
            "runner_b_private", f"{subject.RUNNER_SIGNATURE_DOMAIN_PREFIX}.runner_b"
        ),
    }
    private_key_name, domain = settings[key]
    unsigned = {field: value for field, value in fixture[key].items() if field != "signature"}
    fixture[key] = _sign(fixture[private_key_name], unsigned, domain)


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAuditorProvenanceSuiteReproducibilityV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_scope(self) -> None:
        fixture = _fixture()
        self.assertEqual(fixture["registration_receipt"]["status"], subject.REGISTERED_STATUS)
        self.assertTrue(
            subject.verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        registration = _fixture()["registration"]
        registration["extra"] = True
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_shape_invalid")

    def test_registration_rejects_bool_count(self) -> None:
        registration = _fixture()["registration"]
        registration["expected_vector_count"] = True
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_expected_vector_count_invalid")

    def test_registration_requires_role_order(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][2], registration["role_registrations"][3] = (
            registration["role_registrations"][3], registration["role_registrations"][2]
        )
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_2_order_invalid")

    def test_registration_requires_exact_role_shape(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][0]["extra"] = True
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_0_shape_invalid")

    def test_registration_rejects_key_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][5]["public_key_hash"] = registration[
            "role_registrations"
        ][4]["public_key_hash"]
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_public_key_hashs_not_distinct")

    def test_registration_rejects_organization_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][5]["organization_id"] = registration[
            "role_registrations"
        ][4]["organization_id"]
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_organization_ids_not_distinct")

    def test_registration_rejects_control_group_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][3]["control_group_id"] = registration[
            "role_registrations"
        ][2]["control_group_id"]
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_control_group_ids_not_distinct")

    def test_registration_rejects_owner_disclosure_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][1]["beneficial_owner_disclosure_hash"] = registration[
            "role_registrations"
        ][0]["beneficial_owner_disclosure_hash"]
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"],
            "registration_role_beneficial_owner_disclosure_hashs_not_distinct",
        )

    def test_registration_requires_nonrunner_metadata_null(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][2]["execution_id"] = "unexpected-run-v1"
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_2_runner_fields_must_be_null")

    def test_registration_requires_distinct_runner_implementation(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][5]["runner_implementation_manifest_hash"] = registration[
            "role_registrations"
        ][4]["runner_implementation_manifest_hash"]
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"],
            "registration_runner_runner_implementation_manifest_hashs_not_distinct",
        )

    def test_registration_requires_polarity_count_sum(self) -> None:
        registration = _fixture()["registration"]
        registration["expected_negative_vector_count"] = 3
        result = subject.build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_vector_polarity_counts_mismatch")

    def test_registration_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["status"] = "TAMPERED"
        self.assertFalse(
            subject.verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_registration_receipt_binds_complete_registration(self) -> None:
        fixture = _fixture()
        fixture["registration"]["conflict_registry_id"] = "drifted-conflict-registry-v1"
        self.assertFalse(
            subject.verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_coordinated_registration_and_provenance_drift_is_rejected(self) -> None:
        fixture = _fixture()
        drifted_organization = "drifted-runner-a-organization-v1"
        fixture["registration"]["role_registrations"][4][
            "organization_id"
        ] = drifted_organization
        fixture["provenance_receipt"]["role_registrations"][4][
            "organization_id"
        ] = drifted_organization
        _resign(fixture, "provenance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "registration_receipt_invalid")

    def test_complete_registered_suite_chain_verifies_without_trust_promotion(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["dual_runner_result_agreement_verified"])
        self.assertTrue(
            result["facts"]["registered_requirement_bidirectional_coverage_verified"]
        )
        self.assertFalse(result["facts"]["auditor_independence_verified"])
        self.assertFalse(result["facts"]["suite_completeness_verified"])
        self.assertFalse(result["facts"]["external_registry_trust_attested"])
        self.assertFalse(result["authority"]["paper_allowed"])
        self.assertFalse(result["authority"]["live_allowed"])

    def test_evaluation_is_deterministic(self) -> None:
        fixture = _fixture()
        self.assertEqual(_evaluate(fixture), _evaluate(fixture))

    def test_evaluation_verifier_accepts_exact_output(self) -> None:
        fixture = _fixture()
        receipt = _evaluate(fixture)
        with patch.object(
            subject.source_contract,
            "verify_provider_identity_witness_conformance_key_governance_evaluation_v1",
            return_value=True,
        ):
            self.assertTrue(
                subject.verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1(
                    receipt, **_inputs(fixture)
                )
            )

    def test_evaluation_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        receipt = _evaluate(fixture)
        receipt["facts"]["suite_completeness_verified"] = True
        with patch.object(
            subject,
            "evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1",
            return_value=_evaluate(fixture),
        ):
            self.assertFalse(
                subject.verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1(
                    receipt, **_inputs(fixture)
                )
            )

    def test_source_verifier_is_required(self) -> None:
        result = _evaluate(_fixture(), source_ok=False)
        self.assertEqual(result["reason"], "source_evaluation_not_verified")

    def test_source_status_is_required(self) -> None:
        fixture = _fixture()
        fixture["source_witness_audit_evaluation_receipt"]["status"] = "UNKNOWN"
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_evaluation_status_invalid")

    def test_source_evaluation_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_witness_audit_evaluation_receipt"]["receipt_hash"] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_evaluation_receipt_hash_mismatch")

    def test_source_auditor_key_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_witness_audit_inputs"]["registration"][
            "conformance_auditor_key_id"
        ] = "other-key-v1"
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_conformance_auditor_key_id_mismatch")

    def test_source_implementation_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_witness_audit_inputs"]["registration"][
            "time_authority_implementation_hash"
        ] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_time_authority_implementation_hash_mismatch")

    def test_provenance_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "provenance_receipt_shape_invalid")

    def test_provenance_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["signature"] = fixture["suite_manifest_receipt"][
            "signature"
        ]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "provenance_signature_invalid")

    def test_provenance_rejects_common_control_claim(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["declared_common_control"] = True
        _resign(fixture, "provenance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "provenance_declared_common_control_mismatch")

    def test_provenance_rejects_conflict_claim(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["declared_conflict_of_interest"] = True
        _resign(fixture, "provenance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"], "provenance_declared_conflict_of_interest_mismatch"
        )

    def test_provenance_snapshot_age_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["conflict_registry_snapshot_at_ms"] = 500
        _resign(fixture, "provenance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "provenance_snapshot_age_exceeded")

    def test_provenance_roles_are_bound(self) -> None:
        fixture = _fixture()
        fixture["provenance_receipt"]["role_registrations"][4]["organization_id"] = (
            "drifted-runner-organization-v1"
        )
        _resign(fixture, "provenance_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "provenance_role_registrations_mismatch")

    def test_suite_shape_is_exact(self) -> None:
        fixture = _fixture()
        del fixture["suite_manifest_receipt"]["coverage_policy"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_manifest_receipt_shape_invalid")

    def test_suite_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["signature"] = fixture["provenance_receipt"][
            "signature"
        ]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_signature_invalid")

    def test_suite_requirement_ids_are_unique(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["requirements"][1]["requirement_id"] = (
            "occurrence-cardinality"
        )
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_requirement_ids_not_unique")

    def test_suite_vector_ids_are_unique(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["vectors"][1]["vector_id"] = (
            "occurrence-negative"
        )
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_vector_ids_not_unique")

    def test_suite_vector_requirement_must_exist(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["vectors"][0]["requirement_id"] = "unknown"
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_vector_0_requirement_unknown")

    def test_suite_requirement_root_is_content_bound(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["requirements"][0]["requirement_digest"] = _hash(
            "other"
        )
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_requirement_manifest_root_content_mismatch")

    def test_suite_vector_root_is_content_bound(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["vectors"][0]["input_hash"] = _hash("other")
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_vector_corpus_root_content_mismatch")

    def test_suite_requires_positive_coverage_per_requirement(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["vectors"][1]["requirement_id"] = "time-window"
        fixture["suite_manifest_receipt"]["vectors"][1]["vector_id"] = "occurrence-z-positive"
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_suite_rejects_bool_aggregate_count(self) -> None:
        fixture = _fixture()
        fixture["suite_manifest_receipt"]["vector_count"] = True
        _resign(fixture, "suite_manifest_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "suite_vector_count_mismatch")

    def test_runner_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_receipt_shape_invalid")

    def test_runner_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["signature"] = fixture["runner_b_receipt"]["signature"]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_signature_invalid")

    def test_runner_role_is_bound(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["runner_role"] = "runner_b"
        _resign(fixture, "runner_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_runner_role_mismatch")

    def test_runner_implementation_is_bound(self) -> None:
        fixture = _fixture()
        fixture["runner_b_receipt"]["runner_implementation_manifest_hash"] = _hash("other")
        _resign(fixture, "runner_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"], "runner_b_runner_implementation_manifest_hash_mismatch"
        )

    def test_runner_must_report_every_vector(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["results"].pop()
        _resign(fixture, "runner_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_results_shape_invalid")

    def test_runner_vector_order_is_exact(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["results"][0], fixture["runner_a_receipt"][
            "results"
        ][1] = fixture["runner_a_receipt"]["results"][1], fixture["runner_a_receipt"][
            "results"
        ][0]
        _resign(fixture, "runner_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_result_0_vector_id_mismatch")

    def test_runner_actual_hash_must_match_expected(self) -> None:
        fixture = _fixture()
        fixture["runner_b_receipt"]["results"][2]["actual_result_hash"] = _hash("other")
        _resign(fixture, "runner_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_b_result_2_actual_hash_mismatch")

    def test_runner_rejects_failure(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["results"][0]["passed"] = False
        _resign(fixture, "runner_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_result_0_not_passed")

    def test_runner_rejects_skip(self) -> None:
        fixture = _fixture()
        fixture["runner_b_receipt"]["results"][0]["skipped"] = True
        _resign(fixture, "runner_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_b_result_0_skipped")

    def test_runner_transcript_root_is_bound(self) -> None:
        fixture = _fixture()
        fixture["runner_a_receipt"]["result_transcript_root_hash"] = _hash("other")
        _resign(fixture, "runner_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_a_result_transcript_root_mismatch")

    def test_runner_time_order_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["runner_b_receipt"]["issued_at_ms"] = 2_001
        _resign(fixture, "runner_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "runner_b_time_order_invalid")

    def test_unknown_never_exposes_evidence_or_authority(self) -> None:
        result = subject.evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1(
            registration=None,
            registration_receipt=None,
            source_witness_audit_inputs=None,
            source_witness_audit_evaluation_receipt=None,
            provenance_receipt=None,
            provenance_registry_public_key=None,
            suite_manifest_receipt=None,
            suite_custodian_public_key=None,
            runner_a_receipt=None,
            runner_a_public_key=None,
            runner_b_receipt=None,
            runner_b_public_key=None,
            reference_time_ms=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is None for value in result["evidence"].values()))
        self.assertFalse(result["facts"]["suite_completeness_verified"])
        self.assertFalse(result["authority"]["paper_allowed"])
        self.assertFalse(result["authority"]["live_allowed"])


if __name__ == "__main__":
    unittest.main()
