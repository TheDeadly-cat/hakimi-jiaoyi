from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import provider_identity_artifact_transparency_availability_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash
from tests import test_provider_identity_auditor_provenance_suite_reproducibility_v1 as source_test


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash(value: str) -> str:
    return _hash_bytes(value.encode("ascii"))


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


def _leaf_hash(record: dict[str, object]) -> str:
    return hashlib.sha256(
        subject.LEAF_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(strict_canonical_hash(record))
    ).hexdigest()


def _node_hash(left: str, right: str) -> str:
    return hashlib.sha256(
        subject.NODE_DOMAIN.encode("ascii")
        + b"\x00"
        + bytes.fromhex(left)
        + bytes.fromhex(right)
    ).hexdigest()


def _split(size: int) -> int:
    value = 1
    while value << 1 < size:
        value <<= 1
    return value


def _tree_hash(leaves: list[str]) -> str:
    if len(leaves) == 1:
        return leaves[0]
    split = _split(len(leaves))
    return _node_hash(_tree_hash(leaves[:split]), _tree_hash(leaves[split:]))


def _inclusion_proof(leaves: list[str], index: int) -> list[str]:
    if len(leaves) == 1:
        return []
    split = _split(len(leaves))
    if index < split:
        return _inclusion_proof(leaves[:split], index) + [_tree_hash(leaves[split:])]
    return _inclusion_proof(leaves[split:], index - split) + [_tree_hash(leaves[:split])]


def _role(role: str, private_key: Ed25519PrivateKey) -> dict[str, object]:
    token = role.replace("_", "-")
    return {
        "role": role,
        "entity_id": f"synthetic-{token}-entity-v1",
        "key_id": f"synthetic-{token}-key-v1",
        "public_key_hash": _hash_bytes(_public_key(private_key)),
        "organization_id": f"synthetic-{token}-organization-v1",
        "control_group_id": f"synthetic-{token}-control-v1",
        "beneficial_owner_disclosure_hash": _hash(f"{role}-owner"),
        "retrieval_run_id": f"synthetic-{token}-retrieval-v1" if role in subject.OBSERVER_ROLES else None,
    }


def _fixture() -> dict[str, object]:
    source_fixture = source_test._fixture()
    source_inputs = source_test._inputs(source_fixture)
    source_evaluation = source_test._evaluate(source_fixture)

    log_private = Ed25519PrivateKey.generate()
    observer_a_private = Ed25519PrivateKey.generate()
    observer_b_private = Ed25519PrivateKey.generate()
    roles = [
        _role("transparency_log", log_private),
        _role("observer_a", observer_a_private),
        _role("observer_b", observer_b_private),
    ]
    contents = {
        "auditor-provenance": b'{"artifact":"auditor-provenance","version":1}',
        "runner-a-results": b'{"artifact":"runner-a-results","version":1}',
        "runner-b-results": b'{"artifact":"runner-b-results","version":1}',
        "suite-manifest": b'{"artifact":"suite-manifest","version":1}',
    }
    catalog = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_id,
            "content_hash": _hash_bytes(content),
            "size_bytes": len(content),
            "media_type": "application/json",
            "locator_commitment_hash": _hash(f"locator-{artifact_id}"),
            "required": True,
        }
        for artifact_id, content in sorted(contents.items())
    ]
    payloads = [
        {
            "artifact_id": artifact["artifact_id"],
            "content_base64url": _b64url(contents[artifact["artifact_id"]]),
        }
        for artifact in catalog
    ]
    registration = {
        "schema": subject.REGISTRATION_SCHEMA,
        "adapter_id": "synthetic-artifact-transparency-consumer-v1",
        "adapter_implementation_hash": _hash("artifact-transparency-consumer"),
        "source_reproducibility_registration_receipt_schema": subject.source_contract.REGISTRATION_RECEIPT_SCHEMA,
        "source_reproducibility_evaluation_schema": subject.source_contract.EVALUATION_SCHEMA,
        "source_reproducibility_static_fingerprint": subject.source_contract.STATIC_FINGERPRINT,
        "source_reproducibility_registration_receipt_hash": source_inputs[
            "registration_receipt"
        ]["receipt_hash"],
        "source_reproducibility_evaluation_receipt_hash": source_evaluation["receipt_hash"],
        "role_registrations": roles,
        "log_id": "synthetic-artifact-log-v1",
        "log_namespace": "hakimi.synthetic.artifact-transparency",
        "artifact_catalog_root_hash": strict_canonical_hash(catalog),
        "expected_artifact_count": len(catalog),
        "expected_total_payload_bytes": sum(len(value) for value in contents.values()),
        "max_artifact_payload_bytes": 1024,
        "pinned_checkpoint_tree_size": 0,
        "pinned_checkpoint_root_hash": subject.GENESIS_ROOT_HASH,
        "log_protocol": subject.LOG_PROTOCOL,
        "inclusion_proof_protocol": subject.INCLUSION_PROOF_PROTOCOL,
        "consistency_proof_protocol": subject.CONSISTENCY_PROOF_PROTOCOL,
        "content_hash_algorithm": subject.CONTENT_HASH_ALGORITHM,
        "content_hash_encoding": subject.CONTENT_HASH_ENCODING,
        "content_encoding": subject.CONTENT_ENCODING,
        "checkpoint_schema": subject.CHECKPOINT_SCHEMA,
        "observer_receipt_schema": subject.OBSERVER_RECEIPT_SCHEMA,
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
        "empty_domain": subject.EMPTY_DOMAIN,
        "leaf_domain": subject.LEAF_DOMAIN,
        "node_domain": subject.NODE_DOMAIN,
        "checkpoint_signature_domain": subject.CHECKPOINT_SIGNATURE_DOMAIN,
        "observer_signature_domain_prefix": subject.OBSERVER_SIGNATURE_DOMAIN_PREFIX,
        "retrieval_method": subject.RETRIEVAL_METHOD,
        "genesis_root_hash": subject.GENESIS_ROOT_HASH,
        "max_checkpoint_age_ms": 1_000,
        "max_observer_receipt_age_ms": 1_000,
        "max_observer_retrieval_duration_ms": 500,
        "max_receipt_issue_delay_ms": 100,
    }
    registration_receipt = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
        registration
    )
    leaves = [_leaf_hash(artifact) for artifact in catalog]
    checkpoint_unsigned = {
        "schema": subject.CHECKPOINT_SCHEMA,
        "log_id": registration["log_id"],
        "log_namespace": registration["log_namespace"],
        "tree_size": len(leaves),
        "root_hash": _tree_hash(leaves),
        "issued_at_ms": 1_400,
        "key_id": roles[0]["key_id"],
        "signature_algorithm": subject.SIGNATURE_ALGORITHM,
        "signature_encoding": subject.SIGNATURE_ENCODING,
    }
    checkpoint = _sign(
        log_private, checkpoint_unsigned, subject.CHECKPOINT_SIGNATURE_DOMAIN
    )
    inclusions = [
        {
            "artifact_id": artifact["artifact_id"],
            "leaf_index": index,
            "proof": _inclusion_proof(leaves, index),
        }
        for index, artifact in enumerate(catalog)
    ]
    observer_results = [
        {
            "artifact_id": artifact["artifact_id"],
            "locator_commitment_hash": artifact["locator_commitment_hash"],
            "retrieved_content_hash": artifact["content_hash"],
            "retrieved_size_bytes": artifact["size_bytes"],
            "retrieval_succeeded": True,
        }
        for artifact in catalog
    ]

    def observer_unsigned(role: str, started_at: int) -> dict[str, object]:
        observer = roles[subject.ROLE_ORDER.index(role)]
        return {
            "schema": subject.OBSERVER_RECEIPT_SCHEMA,
            "registration_receipt_hash": registration_receipt["receipt_hash"],
            "source_reproducibility_evaluation_receipt_hash": source_evaluation[
                "receipt_hash"
            ],
            "artifact_catalog_root_hash": registration["artifact_catalog_root_hash"],
            "transparency_checkpoint_hash": strict_canonical_hash(checkpoint),
            "observer_role": role,
            "observer_id": observer["entity_id"],
            "observer_organization_id": observer["organization_id"],
            "observer_control_group_id": observer["control_group_id"],
            "observer_key_id": observer["key_id"],
            "retrieval_run_id": observer["retrieval_run_id"],
            "retrieval_method": subject.RETRIEVAL_METHOD,
            "started_at_ms": started_at,
            "completed_at_ms": started_at + 100,
            "issued_at_ms": started_at + 150,
            "artifact_results": copy.deepcopy(observer_results),
            "result_count": len(catalog),
            "success_count": len(catalog),
            "failure_count": 0,
            "result_transcript_root_hash": strict_canonical_hash(observer_results),
            "signature_algorithm": subject.SIGNATURE_ALGORITHM,
            "signature_encoding": subject.SIGNATURE_ENCODING,
        }

    observer_a_receipt = _sign(
        observer_a_private,
        observer_unsigned("observer_a", 1_500),
        f"{subject.OBSERVER_SIGNATURE_DOMAIN_PREFIX}.observer_a",
    )
    observer_b_receipt = _sign(
        observer_b_private,
        observer_unsigned("observer_b", 1_550),
        f"{subject.OBSERVER_SIGNATURE_DOMAIN_PREFIX}.observer_b",
    )
    return {
        "log_private": log_private,
        "observer_a_private": observer_a_private,
        "observer_b_private": observer_b_private,
        "registration": registration,
        "registration_receipt": registration_receipt,
        "source_reproducibility_inputs": source_inputs,
        "source_reproducibility_evaluation_receipt": source_evaluation,
        "artifact_catalog": catalog,
        "artifact_payloads": payloads,
        "transparency_checkpoint": checkpoint,
        "transparency_log_public_key": _b64url(_public_key(log_private)),
        "transparency_inclusion_proofs": inclusions,
        "transparency_consistency_proof": [],
        "observer_a_receipt": observer_a_receipt,
        "observer_a_public_key": _b64url(_public_key(observer_a_private)),
        "observer_b_receipt": observer_b_receipt,
        "observer_b_public_key": _b64url(_public_key(observer_b_private)),
        "reference_time_ms": 2_000,
    }


def _inputs(fixture: dict[str, object]) -> dict[str, object]:
    private = {"log_private", "observer_a_private", "observer_b_private"}
    return {key: value for key, value in fixture.items() if key not in private}


def _evaluate(
    fixture: dict[str, object],
    *,
    source_ok: bool = True,
    isolate_source_receipt_checks: bool = False,
) -> dict[str, object]:
    source_module = (
        subject.source_contract
        if isolate_source_receipt_checks
        else subject.source_contract.source_contract
    )
    source_verifier = (
        "verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1"
        if isolate_source_receipt_checks
        else "verify_provider_identity_witness_conformance_key_governance_evaluation_v1"
    )
    with patch.object(
        source_module,
        source_verifier,
        return_value=source_ok,
    ):
        return subject.evaluate_provider_identity_artifact_transparency_availability_v1(
            **_inputs(fixture)
        )


def _resign(fixture: dict[str, object], key: str) -> None:
    settings = {
        "transparency_checkpoint": (
            "log_private", subject.CHECKPOINT_SIGNATURE_DOMAIN
        ),
        "observer_a_receipt": (
            "observer_a_private", f"{subject.OBSERVER_SIGNATURE_DOMAIN_PREFIX}.observer_a"
        ),
        "observer_b_receipt": (
            "observer_b_private", f"{subject.OBSERVER_SIGNATURE_DOMAIN_PREFIX}.observer_b"
        ),
    }
    private_name, domain = settings[key]
    unsigned = {field: value for field, value in fixture[key].items() if field != "signature"}
    fixture[key] = _sign(fixture[private_name], unsigned, domain)


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityArtifactTransparencyAvailabilityV1Tests(
    unittest.TestCase
):
    def test_registration_accepts_exact_scope(self) -> None:
        fixture = _fixture()
        self.assertEqual(fixture["registration_receipt"]["status"], subject.REGISTERED_STATUS)
        self.assertTrue(
            subject.verify_provider_identity_artifact_transparency_availability_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_registration_rejects_extra_field(self) -> None:
        registration = _fixture()["registration"]
        registration["extra"] = True
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_shape_invalid")

    def test_registration_rejects_bool_artifact_count(self) -> None:
        registration = _fixture()["registration"]
        registration["expected_artifact_count"] = True
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_expected_artifact_count_invalid")

    def test_registration_requires_role_order(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][1], registration["role_registrations"][2] = (
            registration["role_registrations"][2], registration["role_registrations"][1]
        )
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_1_order_invalid")

    def test_registration_rejects_key_collision(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][2]["public_key_hash"] = registration[
            "role_registrations"
        ][1]["public_key_hash"]
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_role_public_key_hashs_not_distinct")

    def test_registration_requires_log_retrieval_id_null(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][0]["retrieval_run_id"] = "unexpected-v1"
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_log_retrieval_run_id_must_be_null")

    def test_registration_requires_distinct_observer_runs(self) -> None:
        registration = _fixture()["registration"]
        registration["role_registrations"][2]["retrieval_run_id"] = registration[
            "role_registrations"
        ][1]["retrieval_run_id"]
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(
            result["reason"], "registration_observer_retrieval_run_ids_not_distinct"
        )

    def test_registration_requires_genesis_root(self) -> None:
        registration = _fixture()["registration"]
        registration["pinned_checkpoint_root_hash"] = _hash("not-genesis")
        result = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            registration
        )
        self.assertEqual(result["reason"], "registration_genesis_checkpoint_root_invalid")

    def test_registration_receipt_binds_complete_registration(self) -> None:
        fixture = _fixture()
        fixture["registration"]["max_checkpoint_age_ms"] += 1
        self.assertFalse(
            subject.verify_provider_identity_artifact_transparency_availability_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_registration_verifier_rejects_tampering(self) -> None:
        fixture = _fixture()
        fixture["registration_receipt"]["status"] = "TAMPERED"
        self.assertFalse(
            subject.verify_provider_identity_artifact_transparency_availability_registration_v1(
                fixture["registration_receipt"], registration=fixture["registration"]
            )
        )

    def test_complete_chain_verifies_without_public_availability_promotion(self) -> None:
        result = _evaluate(_fixture())
        self.assertEqual(result["status"], subject.VERIFIED_STATUS)
        self.assertTrue(result["facts"]["local_artifact_content_hashes_verified"])
        self.assertTrue(result["facts"]["all_artifact_inclusion_proofs_verified"])
        self.assertTrue(result["facts"]["dual_observer_result_agreement_verified"])
        self.assertFalse(result["facts"]["public_artifact_availability_verified"])
        self.assertFalse(result["facts"]["external_log_trust_attested"])
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
            "verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1",
            return_value=True,
        ):
            self.assertTrue(
                subject.verify_provider_identity_artifact_transparency_availability_evaluation_v1(
                    receipt, **_inputs(fixture)
                )
            )

    def test_source_verifier_is_required(self) -> None:
        result = _evaluate(_fixture(), source_ok=False)
        self.assertEqual(result["reason"], "source_evaluation_not_verified")

    def test_source_status_is_required(self) -> None:
        fixture = _fixture()
        fixture["source_reproducibility_evaluation_receipt"]["status"] = "UNKNOWN"
        result = _evaluate(fixture, isolate_source_receipt_checks=True)
        self.assertEqual(result["reason"], "source_evaluation_status_invalid")

    def test_source_evaluation_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["source_reproducibility_evaluation_receipt"]["receipt_hash"] = _hash("other")
        result = _evaluate(fixture, isolate_source_receipt_checks=True)
        self.assertEqual(result["reason"], "source_evaluation_receipt_hash_mismatch")

    def test_new_role_must_not_collide_with_source(self) -> None:
        fixture = _fixture()
        fixture["registration"]["role_registrations"][0]["organization_id"] = fixture[
            "source_reproducibility_inputs"
        ]["registration"]["role_registrations"][0]["organization_id"]
        fixture["registration_receipt"] = subject.build_provider_identity_artifact_transparency_availability_registration_v1(
            fixture["registration"]
        )
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "source_new_role_organization_id_collision")

    def test_catalog_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["artifact_catalog"][0]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_0_shape_invalid")

    def test_catalog_ids_are_canonical(self) -> None:
        fixture = _fixture()
        fixture["artifact_catalog"].reverse()
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_ids_not_canonical")

    def test_catalog_ids_are_unique(self) -> None:
        fixture = _fixture()
        fixture["artifact_catalog"][1]["artifact_id"] = fixture["artifact_catalog"][0][
            "artifact_id"
        ]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_ids_not_unique")

    def test_catalog_root_is_bound(self) -> None:
        fixture = _fixture()
        fixture["artifact_catalog"][0]["locator_commitment_hash"] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_catalog_root_mismatch")

    def test_catalog_requires_native_true(self) -> None:
        fixture = _fixture()
        fixture["artifact_catalog"][0]["required"] = 1
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_0_required_invalid")

    def test_payload_count_is_exact(self) -> None:
        fixture = _fixture()
        fixture["artifact_payloads"].pop()
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_payloads_shape_invalid")

    def test_payload_order_is_exact(self) -> None:
        fixture = _fixture()
        fixture["artifact_payloads"][0], fixture["artifact_payloads"][1] = (
            fixture["artifact_payloads"][1], fixture["artifact_payloads"][0]
        )
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_payload_0_id_mismatch")

    def test_payload_encoding_is_canonical(self) -> None:
        fixture = _fixture()
        fixture["artifact_payloads"][0]["content_base64url"] += "="
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "artifact_payload_0_encoding_invalid")

    def test_payload_content_hash_is_bound(self) -> None:
        fixture = _fixture()
        content = b"different-content-with-same-ish-length-000000000"
        fixture["artifact_payloads"][0]["content_base64url"] = _b64url(content)
        fixture["artifact_catalog"][0]["size_bytes"] = len(content)
        fixture["registration"]["expected_total_payload_bytes"] += (
            len(content) - fixture["artifact_catalog"][0]["size_bytes"]
        )
        result = _evaluate(fixture)
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)

    def test_checkpoint_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["transparency_checkpoint"]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "checkpoint_shape_invalid")

    def test_checkpoint_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["transparency_checkpoint"]["signature"] = fixture["observer_a_receipt"][
            "signature"
        ]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "checkpoint_signature_invalid")

    def test_checkpoint_time_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["transparency_checkpoint"]["issued_at_ms"] = 2_001
        _resign(fixture, "transparency_checkpoint")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "checkpoint_issued_in_future")

    def test_inclusion_proof_is_required(self) -> None:
        fixture = _fixture()
        fixture["transparency_inclusion_proofs"][0]["proof"][0] = _hash("other")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "inclusion_0_verification_failed")

    def test_inclusion_leaf_index_is_bound(self) -> None:
        fixture = _fixture()
        fixture["transparency_inclusion_proofs"][0]["leaf_index"] = 1
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "inclusion_0_verification_failed")

    def test_consistency_proof_is_required(self) -> None:
        fixture = _fixture()
        fixture["transparency_consistency_proof"] = [_hash("unexpected")]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "consistency_verification_failed")

    def test_observer_shape_is_exact(self) -> None:
        fixture = _fixture()
        fixture["observer_a_receipt"]["extra"] = True
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_a_receipt_shape_invalid")

    def test_observer_signature_is_required(self) -> None:
        fixture = _fixture()
        fixture["observer_a_receipt"]["signature"] = fixture["observer_b_receipt"][
            "signature"
        ]
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_a_signature_invalid")

    def test_observer_role_is_bound(self) -> None:
        fixture = _fixture()
        fixture["observer_b_receipt"]["observer_role"] = "observer_a"
        _resign(fixture, "observer_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_b_observer_role_mismatch")

    def test_observer_must_report_every_artifact(self) -> None:
        fixture = _fixture()
        fixture["observer_a_receipt"]["artifact_results"].pop()
        _resign(fixture, "observer_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_a_artifact_results_shape_invalid")

    def test_observer_content_hash_is_bound(self) -> None:
        fixture = _fixture()
        fixture["observer_b_receipt"]["artifact_results"][0][
            "retrieved_content_hash"
        ] = _hash("other")
        _resign(fixture, "observer_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"], "observer_b_result_0_retrieved_content_hash_mismatch"
        )

    def test_observer_retrieval_must_succeed(self) -> None:
        fixture = _fixture()
        fixture["observer_a_receipt"]["artifact_results"][0][
            "retrieval_succeeded"
        ] = False
        _resign(fixture, "observer_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(
            result["reason"], "observer_a_result_0_retrieval_succeeded_mismatch"
        )

    def test_observer_transcript_root_is_bound(self) -> None:
        fixture = _fixture()
        fixture["observer_a_receipt"]["result_transcript_root_hash"] = _hash("other")
        _resign(fixture, "observer_a_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_a_result_transcript_root_mismatch")

    def test_observer_time_is_bounded(self) -> None:
        fixture = _fixture()
        fixture["observer_b_receipt"]["issued_at_ms"] = 2_001
        _resign(fixture, "observer_b_receipt")
        result = _evaluate(fixture)
        self.assertEqual(result["reason"], "observer_b_time_order_invalid")

    def test_unknown_never_exposes_evidence_or_authority(self) -> None:
        result = subject.evaluate_provider_identity_artifact_transparency_availability_v1(
            registration=None,
            registration_receipt=None,
            source_reproducibility_inputs=None,
            source_reproducibility_evaluation_receipt=None,
            artifact_catalog=None,
            artifact_payloads=None,
            transparency_checkpoint=None,
            transparency_log_public_key=None,
            transparency_inclusion_proofs=None,
            transparency_consistency_proof=None,
            observer_a_receipt=None,
            observer_a_public_key=None,
            observer_b_receipt=None,
            observer_b_public_key=None,
            reference_time_ms=None,
        )
        self.assertEqual(result["status"], subject.UNKNOWN_STATUS)
        self.assertTrue(all(value is None for value in result["evidence"].values()))
        self.assertFalse(result["facts"]["public_artifact_availability_verified"])
        self.assertFalse(result["authority"]["paper_allowed"])
        self.assertFalse(result["authority"]["live_allowed"])


if __name__ == "__main__":
    unittest.main()
