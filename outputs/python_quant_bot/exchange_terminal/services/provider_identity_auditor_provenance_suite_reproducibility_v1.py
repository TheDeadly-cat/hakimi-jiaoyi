from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import provider_identity_witness_conformance_key_governance_v1 as source_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA = "provider-identity-auditor-provenance-suite-reproducibility-registration-v1"
REGISTRATION_RECEIPT_SCHEMA = f"{REGISTRATION_SCHEMA}-receipt"
PROVENANCE_RECEIPT_SCHEMA = "provider-identity-auditor-provenance-receipt-v1"
SUITE_MANIFEST_RECEIPT_SCHEMA = "provider-identity-registered-suite-manifest-receipt-v1"
RUNNER_RECEIPT_SCHEMA = "provider-identity-suite-runner-result-receipt-v1"
EVALUATION_SCHEMA = "provider-identity-auditor-provenance-suite-reproducibility-evaluation-v1"
STATIC_FINGERPRINT = (
    "20260822-provider-identity-auditor-provenance-suite-reproducibility-contract-1"
)
REGISTERED_STATUS = (
    "AUDITOR_PROVENANCE_SUITE_REPRODUCIBILITY_REGISTERED_RECEIPTS_UNOBSERVED"
)
VERIFIED_STATUS = (
    "SIGNED_PROVENANCE_AND_DUAL_RUNNER_REGISTERED_SUITE_COVERAGE_CLAIMS_"
    "VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_ENCODING = "base64url-no-padding"
CANONICAL_HASH_ALGORITHM = "sha256"
CANONICAL_HASH_ENCODING = "lowercase-hex"
PROVENANCE_SIGNATURE_DOMAIN = "hakimi.provider-identity.auditor-provenance.v1"
SUITE_SIGNATURE_DOMAIN = "hakimi.provider-identity.registered-suite-manifest.v1"
RUNNER_SIGNATURE_DOMAIN_PREFIX = "hakimi.provider-identity.suite-runner-result.v1"
COVERAGE_POLICY = "every-registered-requirement-positive-and-negative-v1"
RESULT_POLICY = "every-vector-exactly-once-no-failure-no-skip-v1"
ROLE_ORDER = (
    "source_conformance_auditor",
    "source_governance_auditor",
    "provenance_registry_authority",
    "suite_custodian",
    "runner_a",
    "runner_b",
)
RUNNER_ROLES = frozenset({"runner_a", "runner_b"})
MAX_INT = 2**63 - 1
MAX_REQUIREMENTS = 256
MAX_VECTORS = 4096

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")

_ROLE_FIELDS = frozenset(
    {
        "role",
        "entity_id",
        "key_id",
        "public_key_hash",
        "organization_id",
        "control_group_id",
        "beneficial_owner_disclosure_hash",
        "runner_implementation_manifest_hash",
        "runner_environment_manifest_hash",
        "execution_id",
    }
)
_REQUIREMENT_FIELDS = frozenset({"requirement_id", "requirement_digest"})
_VECTOR_FIELDS = frozenset(
    {"vector_id", "requirement_id", "polarity", "input_hash", "expected_result_hash"}
)
_RESULT_FIELDS = frozenset({"vector_id", "actual_result_hash", "passed", "skipped"})

_REGISTRATION_FIELDS = frozenset(
    {
        "schema",
        "adapter_id",
        "adapter_implementation_hash",
        "source_witness_audit_registration_receipt_schema",
        "source_witness_audit_evaluation_schema",
        "source_witness_audit_static_fingerprint",
        "source_witness_audit_registration_receipt_hash",
        "source_witness_audit_evaluation_receipt_hash",
        "occurrence_provider_implementation_hash",
        "time_authority_implementation_hash",
        "role_registrations",
        "conflict_registry_id",
        "suite_id",
        "suite_version",
        "protocol_id",
        "protocol_version",
        "requirement_manifest_root_hash",
        "expected_requirement_count",
        "vector_corpus_root_hash",
        "expected_vector_count",
        "expected_positive_vector_count",
        "expected_negative_vector_count",
        "minimum_positive_vectors_per_requirement",
        "minimum_negative_vectors_per_requirement",
        "coverage_policy",
        "result_policy",
        "provenance_receipt_schema",
        "suite_manifest_receipt_schema",
        "runner_receipt_schema",
        "signature_algorithm",
        "signature_encoding",
        "canonical_hash_algorithm",
        "canonical_hash_encoding",
        "provenance_signature_domain",
        "suite_signature_domain",
        "runner_signature_domain_prefix",
        "max_provenance_snapshot_age_ms",
        "max_receipt_age_ms",
        "max_receipt_issue_delay_ms",
        "max_runner_duration_ms",
    }
)

_REGISTRATION_CONSTANTS = {
    "schema": REGISTRATION_SCHEMA,
    "source_witness_audit_registration_receipt_schema": source_contract.REGISTRATION_RECEIPT_SCHEMA,
    "source_witness_audit_evaluation_schema": source_contract.EVALUATION_SCHEMA,
    "source_witness_audit_static_fingerprint": source_contract.STATIC_FINGERPRINT,
    "coverage_policy": COVERAGE_POLICY,
    "result_policy": RESULT_POLICY,
    "provenance_receipt_schema": PROVENANCE_RECEIPT_SCHEMA,
    "suite_manifest_receipt_schema": SUITE_MANIFEST_RECEIPT_SCHEMA,
    "runner_receipt_schema": RUNNER_RECEIPT_SCHEMA,
    "signature_algorithm": SIGNATURE_ALGORITHM,
    "signature_encoding": SIGNATURE_ENCODING,
    "canonical_hash_algorithm": CANONICAL_HASH_ALGORITHM,
    "canonical_hash_encoding": CANONICAL_HASH_ENCODING,
    "provenance_signature_domain": PROVENANCE_SIGNATURE_DOMAIN,
    "suite_signature_domain": SUITE_SIGNATURE_DOMAIN,
    "runner_signature_domain_prefix": RUNNER_SIGNATURE_DOMAIN_PREFIX,
}

_PROVENANCE_FIELDS = frozenset(
    {
        "schema",
        "registration_receipt_hash",
        "source_witness_audit_evaluation_receipt_hash",
        "role_registrations",
        "conflict_registry_id",
        "conflict_registry_snapshot_hash",
        "conflict_registry_snapshot_at_ms",
        "declared_common_control",
        "declared_conflict_of_interest",
        "issued_at_ms",
        "authority_id",
        "authority_key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)

_SUITE_FIELDS = frozenset(
    {
        "schema",
        "registration_receipt_hash",
        "source_witness_audit_evaluation_receipt_hash",
        "suite_id",
        "suite_version",
        "protocol_id",
        "protocol_version",
        "occurrence_provider_implementation_hash",
        "time_authority_implementation_hash",
        "requirements",
        "vectors",
        "requirement_manifest_root_hash",
        "requirement_count",
        "vector_corpus_root_hash",
        "vector_count",
        "positive_vector_count",
        "negative_vector_count",
        "coverage_policy",
        "issued_at_ms",
        "custodian_id",
        "custodian_key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)

_RUNNER_FIELDS = frozenset(
    {
        "schema",
        "registration_receipt_hash",
        "source_witness_audit_evaluation_receipt_hash",
        "suite_manifest_receipt_hash",
        "requirement_manifest_root_hash",
        "vector_corpus_root_hash",
        "runner_role",
        "runner_id",
        "runner_organization_id",
        "runner_control_group_id",
        "runner_key_id",
        "runner_implementation_manifest_hash",
        "runner_environment_manifest_hash",
        "execution_id",
        "started_at_ms",
        "completed_at_ms",
        "issued_at_ms",
        "results",
        "result_count",
        "passed_count",
        "failed_count",
        "skipped_count",
        "result_transcript_root_hash",
        "result_policy",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)


def _authority() -> dict[str, bool]:
    return {
        "research_only": True,
        "observation_admission_allowed": False,
        "parameter_selection_allowed": False,
        "promotion_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _registration_facts(registered: bool = False) -> dict[str, bool]:
    return {
        "provenance_and_suite_scope_preregistered": registered,
        "six_role_separation_preregistered": registered,
        "signed_provenance_observed": False,
        "signed_suite_manifest_observed": False,
        "dual_runner_receipts_observed": False,
        "auditor_independence_verified": False,
        "suite_completeness_verified": False,
        "external_registry_trust_attested": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _evaluation_facts() -> dict[str, bool]:
    return {
        "source_witness_audit_reverified": False,
        "source_role_and_implementation_binding_verified": False,
        "provenance_registry_signature_verified": False,
        "declared_role_control_separation_bound": False,
        "conflict_snapshot_claim_bound": False,
        "suite_custodian_signature_verified": False,
        "requirement_manifest_root_verified": False,
        "registered_requirement_bidirectional_coverage_verified": False,
        "vector_corpus_root_verified": False,
        "runner_a_signature_verified": False,
        "runner_b_signature_verified": False,
        "runner_implementations_and_environments_distinct": False,
        "complete_vector_execution_verified": False,
        "dual_runner_result_agreement_verified": False,
        "external_registry_trust_attested": False,
        "auditor_independence_verified": False,
        "suite_completeness_verified": False,
        "deployed_code_identity_verified": False,
        "external_time_truth_verified": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _registration_evidence() -> dict[str, Any]:
    return {
        "registration_hash": None,
        "source_witness_audit_registration_receipt_hash": None,
        "source_witness_audit_evaluation_receipt_hash": None,
        "requirement_manifest_root_hash": None,
        "vector_corpus_root_hash": None,
        "expected_requirement_count": None,
        "expected_vector_count": None,
    }


def _evaluation_evidence() -> dict[str, Any]:
    return {
        "registration_receipt_hash": None,
        "source_witness_audit_evaluation_receipt_hash": None,
        "provenance_receipt_hash": None,
        "suite_manifest_receipt_hash": None,
        "runner_a_receipt_hash": None,
        "runner_b_receipt_hash": None,
        "conflict_registry_snapshot_hash": None,
        "requirement_manifest_root_hash": None,
        "vector_corpus_root_hash": None,
        "result_transcript_root_hash": None,
        "requirement_count": None,
        "vector_count": None,
        "positive_vector_count": None,
        "negative_vector_count": None,
        "reference_time_ms": None,
    }


def _sealed_registration(
    *, status: str, reason: str | None, facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": REGISTRATION_RECEIPT_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts if facts is not None else _registration_facts(),
            "evidence": evidence if evidence is not None else _registration_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _sealed_evaluation(
    *, status: str, reason: str | None, facts: dict[str, bool] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "reason": reason,
            "facts": facts if facts is not None else _evaluation_facts(),
            "evidence": evidence if evidence is not None else _evaluation_evidence(),
            "authority": _authority(),
        },
        "receipt_hash",
    )


def _strict_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _strict_int(value: Any, *, minimum: int = 0, maximum: int = MAX_INT) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _normalize_roles(value: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or len(value) != len(ROLE_ORDER):
        return None, "registration_role_registrations_shape_invalid"
    normalized: list[dict[str, Any]] = []
    for index, expected_role in enumerate(ROLE_ORDER):
        item = value[index]
        if type(item) is not dict or set(item) != _ROLE_FIELDS:
            return None, f"registration_role_{index}_shape_invalid"
        if item.get("role") != expected_role:
            return None, f"registration_role_{index}_order_invalid"
        for field in (
            "role", "entity_id", "key_id", "organization_id", "control_group_id"
        ):
            if not _strict_identifier(item.get(field)):
                return None, f"registration_role_{index}_{field}_invalid"
        for field in ("public_key_hash", "beneficial_owner_disclosure_hash"):
            if not _strict_hash(item.get(field)):
                return None, f"registration_role_{index}_{field}_invalid"
        runner_fields = (
            "runner_implementation_manifest_hash",
            "runner_environment_manifest_hash",
        )
        if expected_role in RUNNER_ROLES:
            for field in runner_fields:
                if not _strict_hash(item.get(field)):
                    return None, f"registration_role_{index}_{field}_invalid"
            if not _strict_identifier(item.get("execution_id")):
                return None, f"registration_role_{index}_execution_id_invalid"
        elif any(item.get(field) is not None for field in (*runner_fields, "execution_id")):
            return None, f"registration_role_{index}_runner_fields_must_be_null"
        normalized.append(copy.deepcopy(item))
    unique_fields = (
        "entity_id",
        "key_id",
        "public_key_hash",
        "organization_id",
        "control_group_id",
        "beneficial_owner_disclosure_hash",
    )
    for field in unique_fields:
        values = [item[field] for item in normalized]
        if len(set(values)) != len(values):
            return None, f"registration_role_{field}s_not_distinct"
    runner_a = normalized[ROLE_ORDER.index("runner_a")]
    runner_b = normalized[ROLE_ORDER.index("runner_b")]
    for field in (
        "runner_implementation_manifest_hash",
        "runner_environment_manifest_hash",
        "execution_id",
    ):
        if runner_a[field] == runner_b[field]:
            return None, f"registration_runner_{field}s_not_distinct"
    return normalized, None


def _normalize_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _REGISTRATION_FIELDS:
        return None, "registration_shape_invalid"
    for key, expected in _REGISTRATION_CONSTANTS.items():
        if not strict_json_contract_equal(value.get(key), expected):
            return None, f"registration_{key}_invalid"
    for field in (
        "adapter_id", "conflict_registry_id", "suite_id", "suite_version",
        "protocol_id", "protocol_version",
    ):
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    for field in (
        "adapter_implementation_hash",
        "source_witness_audit_registration_receipt_hash",
        "source_witness_audit_evaluation_receipt_hash",
        "occurrence_provider_implementation_hash",
        "time_authority_implementation_hash",
        "requirement_manifest_root_hash",
        "vector_corpus_root_hash",
    ):
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    count_limits = {
        "expected_requirement_count": MAX_REQUIREMENTS,
        "expected_vector_count": MAX_VECTORS,
        "expected_positive_vector_count": MAX_VECTORS,
        "expected_negative_vector_count": MAX_VECTORS,
        "minimum_positive_vectors_per_requirement": MAX_VECTORS,
        "minimum_negative_vectors_per_requirement": MAX_VECTORS,
    }
    for field, maximum in count_limits.items():
        if not _strict_int(value.get(field), minimum=1, maximum=maximum):
            return None, f"registration_{field}_invalid"
    for field in (
        "max_provenance_snapshot_age_ms", "max_receipt_age_ms",
        "max_receipt_issue_delay_ms", "max_runner_duration_ms",
    ):
        if not _strict_int(value.get(field), minimum=1):
            return None, f"registration_{field}_invalid"
    if value["expected_positive_vector_count"] + value[
        "expected_negative_vector_count"
    ] != value["expected_vector_count"]:
        return None, "registration_vector_polarity_counts_mismatch"
    minimum_vectors = value["expected_requirement_count"] * (
        value["minimum_positive_vectors_per_requirement"]
        + value["minimum_negative_vectors_per_requirement"]
    )
    if value["expected_vector_count"] < minimum_vectors:
        return None, "registration_vector_count_below_requirement_minimum"
    if value["source_witness_audit_registration_receipt_hash"] == value[
        "source_witness_audit_evaluation_receipt_hash"
    ]:
        return None, "registration_source_receipt_hashes_not_distinct"
    if value["occurrence_provider_implementation_hash"] == value[
        "time_authority_implementation_hash"
    ]:
        return None, "registration_witness_implementation_hashes_not_distinct"
    if value["requirement_manifest_root_hash"] == value["vector_corpus_root_hash"]:
        return None, "registration_manifest_roots_not_distinct"
    roles, error = _normalize_roles(value.get("role_registrations"))
    if roles is None:
        return None, error
    normalized = copy.deepcopy(value)
    normalized["role_registrations"] = roles
    return normalized, None


def build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_registration(status=UNKNOWN_STATUS, reason=error)
    evidence = _registration_evidence()
    for key in evidence:
        evidence[key] = (
            strict_canonical_hash(normalized)
            if key == "registration_hash"
            else normalized[key]
        )
    return _sealed_registration(
        status=REGISTERED_STATUS,
        reason=None,
        facts=_registration_facts(registered=True),
        evidence=evidence,
    )


def verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
    receipt: Any, *, registration: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    return strict_json_contract_equal(
        receipt,
        build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
            registration
        ),
    )


def _role_map(registration: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["role"]: item for item in registration["role_registrations"]}


def _canonical_bytes(value: dict[str, Any]) -> bytes | None:
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None


def _decode_b64url(value: Any) -> bytes | None:
    if type(value) is not str or _B64URL.fullmatch(value) is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (TypeError, ValueError):
        return None
    if base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != value:
        return None
    return decoded


def _verify_signature(
    *, receipt: dict[str, Any], public_key: Any, expected_hash: str, domain: str,
) -> bool:
    public_bytes = _decode_b64url(public_key)
    signature = _decode_b64url(receipt.get("signature"))
    if public_bytes is None or len(public_bytes) != 32 or signature is None:
        return False
    if hashlib.sha256(public_bytes).hexdigest() != expected_hash:
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    canonical = _canonical_bytes(unsigned)
    if canonical is None:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature, domain.encode("ascii") + b"\x00" + canonical
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True


def _validate_provenance(
    value: Any, *, registration: dict[str, Any], registration_hash: str,
    public_key: Any, reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _PROVENANCE_FIELDS:
        return None, "provenance_receipt_shape_invalid"
    authority = _role_map(registration)["provenance_registry_authority"]
    expected = {
        "schema": PROVENANCE_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_hash,
        "source_witness_audit_evaluation_receipt_hash": registration[
            "source_witness_audit_evaluation_receipt_hash"
        ],
        "role_registrations": registration["role_registrations"],
        "conflict_registry_id": registration["conflict_registry_id"],
        "declared_common_control": False,
        "declared_conflict_of_interest": False,
        "authority_id": authority["entity_id"],
        "authority_key_id": authority["key_id"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"provenance_{key}_mismatch"
    if not _strict_hash(value.get("conflict_registry_snapshot_hash")):
        return None, "provenance_conflict_registry_snapshot_hash_invalid"
    for field in ("conflict_registry_snapshot_at_ms", "issued_at_ms"):
        if not _strict_int(value.get(field)):
            return None, f"provenance_{field}_invalid"
    snapshot_at = value["conflict_registry_snapshot_at_ms"]
    issued_at = value["issued_at_ms"]
    if not snapshot_at <= issued_at <= reference_time_ms:
        return None, "provenance_time_order_invalid"
    if issued_at - snapshot_at > registration["max_provenance_snapshot_age_ms"]:
        return None, "provenance_snapshot_age_exceeded"
    if reference_time_ms - issued_at > registration["max_receipt_age_ms"]:
        return None, "provenance_receipt_age_exceeded"
    if not _verify_signature(
        receipt=value, public_key=public_key,
        expected_hash=authority["public_key_hash"],
        domain=PROVENANCE_SIGNATURE_DOMAIN,
    ):
        return None, "provenance_signature_invalid"
    return copy.deepcopy(value), None


def _normalize_requirements(value: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or not 1 <= len(value) <= MAX_REQUIREMENTS:
        return None, "suite_requirements_shape_invalid"
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != _REQUIREMENT_FIELDS:
            return None, f"suite_requirement_{index}_shape_invalid"
        if not _strict_identifier(item.get("requirement_id")):
            return None, f"suite_requirement_{index}_id_invalid"
        if not _strict_hash(item.get("requirement_digest")):
            return None, f"suite_requirement_{index}_digest_invalid"
        result.append(dict(item))
    identifiers = [item["requirement_id"] for item in result]
    if len(set(identifiers)) != len(identifiers):
        return None, "suite_requirement_ids_not_unique"
    if identifiers != sorted(identifiers):
        return None, "suite_requirement_ids_not_canonical"
    return result, None


def _normalize_vectors(
    value: Any, *, requirement_ids: set[str],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if type(value) is not list or not 1 <= len(value) <= MAX_VECTORS:
        return None, "suite_vectors_shape_invalid"
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != _VECTOR_FIELDS:
            return None, f"suite_vector_{index}_shape_invalid"
        if not _strict_identifier(item.get("vector_id")):
            return None, f"suite_vector_{index}_id_invalid"
        if item.get("requirement_id") not in requirement_ids:
            return None, f"suite_vector_{index}_requirement_unknown"
        if item.get("polarity") not in {"positive", "negative"}:
            return None, f"suite_vector_{index}_polarity_invalid"
        for field in ("input_hash", "expected_result_hash"):
            if not _strict_hash(item.get(field)):
                return None, f"suite_vector_{index}_{field}_invalid"
        result.append(dict(item))
    identifiers = [item["vector_id"] for item in result]
    if len(set(identifiers)) != len(identifiers):
        return None, "suite_vector_ids_not_unique"
    if identifiers != sorted(identifiers):
        return None, "suite_vector_ids_not_canonical"
    return result, None


def _validate_suite(
    value: Any, *, registration: dict[str, Any], registration_hash: str,
    public_key: Any, reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _SUITE_FIELDS:
        return None, "suite_manifest_receipt_shape_invalid"
    custodian = _role_map(registration)["suite_custodian"]
    expected = {
        "schema": SUITE_MANIFEST_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_hash,
        "source_witness_audit_evaluation_receipt_hash": registration[
            "source_witness_audit_evaluation_receipt_hash"
        ],
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
        "requirement_manifest_root_hash": registration["requirement_manifest_root_hash"],
        "requirement_count": registration["expected_requirement_count"],
        "vector_corpus_root_hash": registration["vector_corpus_root_hash"],
        "vector_count": registration["expected_vector_count"],
        "positive_vector_count": registration["expected_positive_vector_count"],
        "negative_vector_count": registration["expected_negative_vector_count"],
        "coverage_policy": COVERAGE_POLICY,
        "custodian_id": custodian["entity_id"],
        "custodian_key_id": custodian["key_id"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"suite_{key}_mismatch"
    requirements, error = _normalize_requirements(value.get("requirements"))
    if requirements is None:
        return None, error
    vectors, error = _normalize_vectors(
        value.get("vectors"),
        requirement_ids={item["requirement_id"] for item in requirements},
    )
    if vectors is None:
        return None, error
    if len(requirements) != registration["expected_requirement_count"]:
        return None, "suite_requirement_count_content_mismatch"
    if len(vectors) != registration["expected_vector_count"]:
        return None, "suite_vector_count_content_mismatch"
    if strict_canonical_hash(requirements) != registration["requirement_manifest_root_hash"]:
        return None, "suite_requirement_manifest_root_content_mismatch"
    if strict_canonical_hash(vectors) != registration["vector_corpus_root_hash"]:
        return None, "suite_vector_corpus_root_content_mismatch"
    positive_count = sum(item["polarity"] == "positive" for item in vectors)
    negative_count = sum(item["polarity"] == "negative" for item in vectors)
    if positive_count != registration["expected_positive_vector_count"]:
        return None, "suite_positive_vector_count_content_mismatch"
    if negative_count != registration["expected_negative_vector_count"]:
        return None, "suite_negative_vector_count_content_mismatch"
    for requirement in requirements:
        requirement_vectors = [
            item for item in vectors
            if item["requirement_id"] == requirement["requirement_id"]
        ]
        positive = sum(item["polarity"] == "positive" for item in requirement_vectors)
        negative = sum(item["polarity"] == "negative" for item in requirement_vectors)
        if positive < registration["minimum_positive_vectors_per_requirement"]:
            return None, f"suite_requirement_{requirement['requirement_id']}_positive_coverage_missing"
        if negative < registration["minimum_negative_vectors_per_requirement"]:
            return None, f"suite_requirement_{requirement['requirement_id']}_negative_coverage_missing"
    if not _strict_int(value.get("issued_at_ms")):
        return None, "suite_issued_at_ms_invalid"
    if not value["issued_at_ms"] <= reference_time_ms:
        return None, "suite_issued_in_future"
    if reference_time_ms - value["issued_at_ms"] > registration["max_receipt_age_ms"]:
        return None, "suite_receipt_age_exceeded"
    if not _verify_signature(
        receipt=value, public_key=public_key,
        expected_hash=custodian["public_key_hash"], domain=SUITE_SIGNATURE_DOMAIN,
    ):
        return None, "suite_signature_invalid"
    normalized = copy.deepcopy(value)
    normalized["requirements"] = requirements
    normalized["vectors"] = vectors
    return normalized, None


def _validate_runner(
    value: Any, *, role: str, registration: dict[str, Any], registration_hash: str,
    suite: dict[str, Any], public_key: Any, reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _RUNNER_FIELDS:
        return None, f"{role}_receipt_shape_invalid"
    runner = _role_map(registration)[role]
    suite_hash = strict_canonical_hash(suite)
    expected = {
        "schema": RUNNER_RECEIPT_SCHEMA,
        "registration_receipt_hash": registration_hash,
        "source_witness_audit_evaluation_receipt_hash": registration[
            "source_witness_audit_evaluation_receipt_hash"
        ],
        "suite_manifest_receipt_hash": suite_hash,
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
        "runner_environment_manifest_hash": runner["runner_environment_manifest_hash"],
        "execution_id": runner["execution_id"],
        "result_count": registration["expected_vector_count"],
        "passed_count": registration["expected_vector_count"],
        "failed_count": 0,
        "skipped_count": 0,
        "result_policy": RESULT_POLICY,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"{role}_{key}_mismatch"
    results = value.get("results")
    vectors = suite["vectors"]
    if type(results) is not list or len(results) != len(vectors):
        return None, f"{role}_results_shape_invalid"
    normalized_results: list[dict[str, Any]] = []
    for index, (result, vector) in enumerate(zip(results, vectors)):
        if type(result) is not dict or set(result) != _RESULT_FIELDS:
            return None, f"{role}_result_{index}_shape_invalid"
        if result.get("vector_id") != vector["vector_id"]:
            return None, f"{role}_result_{index}_vector_id_mismatch"
        if result.get("actual_result_hash") != vector["expected_result_hash"]:
            return None, f"{role}_result_{index}_actual_hash_mismatch"
        if type(result.get("passed")) is not bool or result["passed"] is not True:
            return None, f"{role}_result_{index}_not_passed"
        if type(result.get("skipped")) is not bool or result["skipped"] is not False:
            return None, f"{role}_result_{index}_skipped"
        normalized_results.append(dict(result))
    if value.get("result_transcript_root_hash") != strict_canonical_hash(
        normalized_results
    ):
        return None, f"{role}_result_transcript_root_mismatch"
    for field in ("started_at_ms", "completed_at_ms", "issued_at_ms"):
        if not _strict_int(value.get(field)):
            return None, f"{role}_{field}_invalid"
    started = value["started_at_ms"]
    completed = value["completed_at_ms"]
    issued = value["issued_at_ms"]
    if not started <= completed <= issued <= reference_time_ms:
        return None, f"{role}_time_order_invalid"
    if completed - started > registration["max_runner_duration_ms"]:
        return None, f"{role}_duration_exceeded"
    if issued - completed > registration["max_receipt_issue_delay_ms"]:
        return None, f"{role}_issue_delay_exceeded"
    if reference_time_ms - issued > registration["max_receipt_age_ms"]:
        return None, f"{role}_receipt_age_exceeded"
    if not _verify_signature(
        receipt=value, public_key=public_key,
        expected_hash=runner["public_key_hash"],
        domain=f"{RUNNER_SIGNATURE_DOMAIN_PREFIX}.{role}",
    ):
        return None, f"{role}_signature_invalid"
    normalized = copy.deepcopy(value)
    normalized["results"] = normalized_results
    return normalized, None


def evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    source_witness_audit_inputs: Any,
    source_witness_audit_evaluation_receipt: Any,
    provenance_receipt: Any,
    provenance_registry_public_key: Any,
    suite_manifest_receipt: Any,
    suite_custodian_public_key: Any,
    runner_a_receipt: Any,
    runner_a_public_key: Any,
    runner_b_receipt: Any,
    runner_b_public_key: Any,
    reference_time_ms: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    if not verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1(
        registration_receipt, registration=registration
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_receipt_invalid")
    if registration_receipt.get("status") != REGISTERED_STATUS:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_status_invalid")
    if not _strict_int(reference_time_ms):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="reference_time_ms_invalid")
    if type(source_witness_audit_inputs) is not dict or type(
        source_witness_audit_evaluation_receipt
    ) is not dict:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_shape_invalid")
    try:
        source_ok = source_contract.verify_provider_identity_witness_conformance_key_governance_evaluation_v1(
            source_witness_audit_evaluation_receipt,
            **source_witness_audit_inputs,
        )
    except Exception:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_verifier_error")
    if source_ok is not True:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_evaluation_not_verified")
    if (
        source_witness_audit_evaluation_receipt.get("schema") != source_contract.EVALUATION_SCHEMA
        or source_witness_audit_evaluation_receipt.get("status") != source_contract.VERIFIED_STATUS
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_evaluation_status_invalid")
    source_registration = source_witness_audit_inputs.get("registration")
    source_registration_receipt = source_witness_audit_inputs.get("registration_receipt")
    if type(source_registration) is not dict or type(source_registration_receipt) is not dict:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_registration_shape_invalid")
    source_registration_hash = source_registration_receipt.get("receipt_hash")
    source_evaluation_hash = source_witness_audit_evaluation_receipt.get("receipt_hash")
    if not _strict_hash(source_registration_hash) or not _strict_hash(source_evaluation_hash):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_receipt_hash_invalid")
    if source_registration_hash != normalized[
        "source_witness_audit_registration_receipt_hash"
    ]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS, reason="source_registration_receipt_hash_mismatch"
        )
    if source_evaluation_hash != normalized["source_witness_audit_evaluation_receipt_hash"]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS, reason="source_evaluation_receipt_hash_mismatch"
        )
    roles = _role_map(normalized)
    source_bindings = {
        "source_conformance_auditor": (
            "conformance_auditor_id", "conformance_auditor_key_id",
            "conformance_auditor_public_key_hash",
        ),
        "source_governance_auditor": (
            "governance_auditor_id", "governance_auditor_key_id",
            "governance_auditor_public_key_hash",
        ),
    }
    for role, fields in source_bindings.items():
        expected_role = roles[role]
        expected_values = (
            expected_role["entity_id"], expected_role["key_id"],
            expected_role["public_key_hash"],
        )
        for field, expected_value in zip(fields, expected_values):
            if not strict_json_contract_equal(source_registration.get(field), expected_value):
                return _sealed_evaluation(
                    status=UNKNOWN_STATUS, reason=f"source_{field}_mismatch"
                )
    for field in (
        "occurrence_provider_implementation_hash",
        "time_authority_implementation_hash",
    ):
        if source_registration.get(field) != normalized[field]:
            return _sealed_evaluation(status=UNKNOWN_STATUS, reason=f"source_{field}_mismatch")
    registration_hash = registration_receipt.get("receipt_hash")
    if not _strict_hash(registration_hash):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="registration_receipt_hash_invalid")
    provenance, error = _validate_provenance(
        provenance_receipt, registration=normalized, registration_hash=registration_hash,
        public_key=provenance_registry_public_key, reference_time_ms=reference_time_ms,
    )
    if provenance is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    suite, error = _validate_suite(
        suite_manifest_receipt, registration=normalized, registration_hash=registration_hash,
        public_key=suite_custodian_public_key, reference_time_ms=reference_time_ms,
    )
    if suite is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    runner_a, error = _validate_runner(
        runner_a_receipt, role="runner_a", registration=normalized,
        registration_hash=registration_hash, suite=suite,
        public_key=runner_a_public_key, reference_time_ms=reference_time_ms,
    )
    if runner_a is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    runner_b, error = _validate_runner(
        runner_b_receipt, role="runner_b", registration=normalized,
        registration_hash=registration_hash, suite=suite,
        public_key=runner_b_public_key, reference_time_ms=reference_time_ms,
    )
    if runner_b is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    transcript_root = runner_a["result_transcript_root_hash"]
    if runner_b["result_transcript_root_hash"] != transcript_root:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="dual_runner_result_disagreement")
    runner_a_hash = strict_canonical_hash(runner_a)
    runner_b_hash = strict_canonical_hash(runner_b)
    if runner_a_hash == runner_b_hash:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="dual_runner_receipt_reused")
    facts = _evaluation_facts()
    for key in (
        "source_witness_audit_reverified",
        "source_role_and_implementation_binding_verified",
        "provenance_registry_signature_verified",
        "declared_role_control_separation_bound",
        "conflict_snapshot_claim_bound",
        "suite_custodian_signature_verified",
        "requirement_manifest_root_verified",
        "registered_requirement_bidirectional_coverage_verified",
        "vector_corpus_root_verified",
        "runner_a_signature_verified",
        "runner_b_signature_verified",
        "runner_implementations_and_environments_distinct",
        "complete_vector_execution_verified",
        "dual_runner_result_agreement_verified",
    ):
        facts[key] = True
    evidence = _evaluation_evidence()
    evidence.update(
        {
            "registration_receipt_hash": registration_hash,
            "source_witness_audit_evaluation_receipt_hash": source_evaluation_hash,
            "provenance_receipt_hash": strict_canonical_hash(provenance),
            "suite_manifest_receipt_hash": strict_canonical_hash(suite),
            "runner_a_receipt_hash": runner_a_hash,
            "runner_b_receipt_hash": runner_b_hash,
            "conflict_registry_snapshot_hash": provenance[
                "conflict_registry_snapshot_hash"
            ],
            "requirement_manifest_root_hash": normalized["requirement_manifest_root_hash"],
            "vector_corpus_root_hash": normalized["vector_corpus_root_hash"],
            "result_transcript_root_hash": transcript_root,
            "requirement_count": normalized["expected_requirement_count"],
            "vector_count": normalized["expected_vector_count"],
            "positive_vector_count": normalized["expected_positive_vector_count"],
            "negative_vector_count": normalized["expected_negative_vector_count"],
            "reference_time_ms": reference_time_ms,
        }
    )
    return _sealed_evaluation(
        status=VERIFIED_STATUS, reason=None, facts=facts, evidence=evidence
    )


def verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1(
    receipt: Any, **inputs: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    return strict_json_contract_equal(
        receipt,
        evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1(
            **inputs
        ),
    )


__all__ = [
    "CANONICAL_HASH_ALGORITHM",
    "CANONICAL_HASH_ENCODING",
    "COVERAGE_POLICY",
    "EVALUATION_SCHEMA",
    "PROVENANCE_RECEIPT_SCHEMA",
    "PROVENANCE_SIGNATURE_DOMAIN",
    "REGISTERED_STATUS",
    "REGISTRATION_RECEIPT_SCHEMA",
    "REGISTRATION_SCHEMA",
    "RESULT_POLICY",
    "ROLE_ORDER",
    "RUNNER_RECEIPT_SCHEMA",
    "RUNNER_SIGNATURE_DOMAIN_PREFIX",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_ENCODING",
    "STATIC_FINGERPRINT",
    "SUITE_MANIFEST_RECEIPT_SCHEMA",
    "SUITE_SIGNATURE_DOMAIN",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "build_provider_identity_auditor_provenance_suite_reproducibility_registration_v1",
    "evaluate_provider_identity_auditor_provenance_suite_reproducibility_v1",
    "verify_provider_identity_auditor_provenance_suite_reproducibility_evaluation_v1",
    "verify_provider_identity_auditor_provenance_suite_reproducibility_registration_v1",
]
