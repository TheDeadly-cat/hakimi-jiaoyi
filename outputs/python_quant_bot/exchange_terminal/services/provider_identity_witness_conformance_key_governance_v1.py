from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1 as source_coverage_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_registration_v1 as source_registration_contract
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA = "provider-identity-witness-conformance-key-governance-registration-v1"
REGISTRATION_RECEIPT_SCHEMA = f"{REGISTRATION_SCHEMA}-receipt"
CONFORMANCE_RECEIPT_SCHEMA = "provider-identity-witness-conformance-audit-receipt-v1"
GOVERNANCE_RECEIPT_SCHEMA = "provider-identity-key-governance-audit-receipt-v1"
EVALUATION_SCHEMA = "provider-identity-witness-conformance-key-governance-evaluation-v1"
STATIC_FINGERPRINT = (
    "20260822-provider-identity-witness-conformance-key-governance-contract-2"
)
REGISTERED_STATUS = (
    "WITNESS_CONFORMANCE_KEY_GOVERNANCE_AUDIT_REGISTERED_RECEIPTS_UNOBSERVED"
)
VERIFIED_STATUS = (
    "SIGNED_WITNESS_CONFORMANCE_AND_KEY_GOVERNANCE_CLAIMS_VERIFIED_"
    "EXTERNAL_AUDITOR_TRUST_UNPROVEN"
)
UNKNOWN_STATUS = "UNKNOWN"
SIGNATURE_ALGORITHM = "ed25519"
SIGNATURE_ENCODING = "base64url-no-padding"
CANONICAL_HASH_ALGORITHM = "sha256"
CANONICAL_HASH_ENCODING = "lowercase-hex"
CONFORMANCE_SIGNATURE_DOMAIN = "hakimi.provider-identity.witness-conformance-audit.v1"
GOVERNANCE_SIGNATURE_DOMAIN = "hakimi.provider-identity.key-governance-audit.v1"
GENESIS_COMMITMENT = "GENESIS"
MAX_INT = 2**63 - 1
MAX_VECTOR_COUNT = 1_000_000

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")

_REGISTRATION_FIELDS = frozenset(
    {
        "schema",
        "adapter_id",
        "adapter_implementation_hash",
        "source_evidence_registration_receipt_schema",
        "source_evidence_registration_static_fingerprint",
        "source_evidence_registration_receipt_hash",
        "source_longitudinal_coverage_evaluation_schema",
        "source_longitudinal_coverage_static_fingerprint",
        "source_longitudinal_coverage_evaluation_receipt_hash",
        "occurrence_provider_id",
        "occurrence_provider_key_id",
        "occurrence_provider_public_key_hash",
        "occurrence_provider_implementation_hash",
        "time_authority_id",
        "time_authority_key_id",
        "time_authority_public_key_hash",
        "time_authority_implementation_hash",
        "conformance_auditor_id",
        "conformance_auditor_key_id",
        "conformance_auditor_public_key_hash",
        "governance_auditor_id",
        "governance_auditor_key_id",
        "governance_auditor_public_key_hash",
        "occurrence_audit_run_id",
        "occurrence_conformance_suite_id",
        "occurrence_conformance_suite_hash",
        "occurrence_required_vector_count",
        "time_audit_run_id",
        "time_conformance_suite_id",
        "time_conformance_suite_hash",
        "time_required_vector_count",
        "governance_audit_run_id",
        "key_ceremony_id",
        "key_ceremony_transcript_hash",
        "rotation_policy_id",
        "rotation_policy_hash",
        "revocation_registry_id",
        "custody_policy_id",
        "custody_policy_hash",
        "occurrence_key_epoch",
        "occurrence_previous_key_commitment",
        "time_authority_key_epoch",
        "time_authority_previous_key_commitment",
        "key_valid_from_ms",
        "key_valid_until_ms",
        "conformance_receipt_schema",
        "governance_receipt_schema",
        "signature_algorithm",
        "signature_encoding",
        "canonical_hash_algorithm",
        "canonical_hash_encoding",
        "conformance_signature_domain",
        "governance_signature_domain",
        "max_audit_duration_ms",
        "max_receipt_issue_delay_ms",
        "max_audit_age_ms",
        "max_revocation_snapshot_age_ms",
    }
)

_REGISTRATION_CONSTANTS = {
    "schema": REGISTRATION_SCHEMA,
    "source_evidence_registration_receipt_schema": source_registration_contract.RECEIPT_SCHEMA,
    "source_evidence_registration_static_fingerprint": source_registration_contract.STATIC_FINGERPRINT,
    "source_longitudinal_coverage_evaluation_schema": source_coverage_contract.EVALUATION_SCHEMA,
    "source_longitudinal_coverage_static_fingerprint": source_coverage_contract.STATIC_FINGERPRINT,
    "conformance_receipt_schema": CONFORMANCE_RECEIPT_SCHEMA,
    "governance_receipt_schema": GOVERNANCE_RECEIPT_SCHEMA,
    "signature_algorithm": SIGNATURE_ALGORITHM,
    "signature_encoding": SIGNATURE_ENCODING,
    "canonical_hash_algorithm": CANONICAL_HASH_ALGORITHM,
    "canonical_hash_encoding": CANONICAL_HASH_ENCODING,
    "conformance_signature_domain": CONFORMANCE_SIGNATURE_DOMAIN,
    "governance_signature_domain": GOVERNANCE_SIGNATURE_DOMAIN,
}

_CONFORMANCE_FIELDS = frozenset(
    {
        "schema",
        "audit_registration_receipt_hash",
        "source_evidence_registration_receipt_hash",
        "source_longitudinal_coverage_evaluation_receipt_hash",
        "audit_run_id",
        "target_role",
        "target_entity_id",
        "target_key_id",
        "target_public_key_hash",
        "target_implementation_hash",
        "audit_suite_id",
        "audit_suite_hash",
        "test_vector_count",
        "passed_vector_count",
        "failed_vector_count",
        "started_at_ms",
        "completed_at_ms",
        "issued_at_ms",
        "auditor_id",
        "auditor_key_id",
        "signature_algorithm",
        "signature_encoding",
        "signature",
    }
)

_GOVERNANCE_FIELDS = frozenset(
    {
        "schema",
        "audit_registration_receipt_hash",
        "source_evidence_registration_receipt_hash",
        "source_longitudinal_coverage_evaluation_receipt_hash",
        "audit_run_id",
        "occurrence_provider_id",
        "occurrence_provider_key_id",
        "occurrence_provider_public_key_hash",
        "occurrence_key_epoch",
        "occurrence_previous_key_commitment",
        "time_authority_id",
        "time_authority_key_id",
        "time_authority_public_key_hash",
        "time_authority_key_epoch",
        "time_authority_previous_key_commitment",
        "key_valid_from_ms",
        "key_valid_until_ms",
        "key_ceremony_id",
        "key_ceremony_transcript_hash",
        "rotation_policy_id",
        "rotation_policy_hash",
        "revocation_registry_id",
        "revocation_snapshot_hash",
        "revocation_snapshot_at_ms",
        "occurrence_key_revoked",
        "time_authority_key_revoked",
        "custody_policy_id",
        "custody_policy_hash",
        "custody_domains_separated",
        "audit_completed_at_ms",
        "issued_at_ms",
        "auditor_id",
        "auditor_key_id",
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
        "audit_scope_preregistered": registered,
        "auditor_roles_separated": registered,
        "signed_audit_receipts_observed": False,
        "external_conformance_auditor_trust_attested": False,
        "external_governance_auditor_trust_attested": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _evaluation_facts() -> dict[str, bool]:
    return {
        "source_evidence_registration_reverified": False,
        "source_longitudinal_coverage_reverified": False,
        "source_witness_key_binding_verified": False,
        "auditor_roles_separated": False,
        "occurrence_conformance_signature_verified": False,
        "time_conformance_signature_verified": False,
        "conformance_suites_and_vectors_bound": False,
        "key_governance_signature_verified": False,
        "key_ceremony_claim_bound": False,
        "rotation_lineage_claims_bound": False,
        "non_revocation_claims_bound": False,
        "custody_separation_claim_bound": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
        "external_conformance_auditor_trust_attested": False,
        "external_governance_auditor_trust_attested": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _registration_evidence() -> dict[str, Any]:
    return {
        "registration_hash": None,
        "source_evidence_registration_receipt_hash": None,
        "source_longitudinal_coverage_evaluation_receipt_hash": None,
        "occurrence_conformance_suite_hash": None,
        "time_conformance_suite_hash": None,
        "key_ceremony_transcript_hash": None,
        "rotation_policy_hash": None,
        "custody_policy_hash": None,
    }


def _evaluation_evidence() -> dict[str, Any]:
    return {
        "audit_registration_receipt_hash": None,
        "source_evidence_registration_receipt_hash": None,
        "source_longitudinal_coverage_evaluation_receipt_hash": None,
        "occurrence_conformance_receipt_hash": None,
        "time_conformance_receipt_hash": None,
        "key_governance_receipt_hash": None,
        "occurrence_conformance_suite_hash": None,
        "time_conformance_suite_hash": None,
        "key_ceremony_transcript_hash": None,
        "rotation_policy_hash": None,
        "revocation_snapshot_hash": None,
        "custody_policy_hash": None,
        "occurrence_key_epoch": None,
        "time_authority_key_epoch": None,
        "audit_reference_time_ms": None,
    }


def _sealed_registration(
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
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
    *,
    status: str,
    reason: str | None,
    facts: dict[str, bool] | None = None,
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


def _strict_int(
    value: Any,
    *,
    minimum: int = 0,
    maximum: int = MAX_INT,
) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _valid_previous_commitment(epoch: int, commitment: Any, current_hash: str) -> bool:
    if epoch == 0:
        return commitment == GENESIS_COMMITMENT
    return _strict_hash(commitment) and commitment != current_hash


def _normalize_registration(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _REGISTRATION_FIELDS:
        return None, "registration_shape_invalid"
    for key, expected in _REGISTRATION_CONSTANTS.items():
        if not strict_json_contract_equal(value.get(key), expected):
            return None, f"registration_{key}_invalid"
    identifier_fields = (
        "adapter_id",
        "occurrence_provider_id",
        "occurrence_provider_key_id",
        "time_authority_id",
        "time_authority_key_id",
        "conformance_auditor_id",
        "conformance_auditor_key_id",
        "governance_auditor_id",
        "governance_auditor_key_id",
        "occurrence_audit_run_id",
        "occurrence_conformance_suite_id",
        "time_audit_run_id",
        "time_conformance_suite_id",
        "governance_audit_run_id",
        "key_ceremony_id",
        "rotation_policy_id",
        "revocation_registry_id",
        "custody_policy_id",
    )
    for field in identifier_fields:
        if not _strict_identifier(value.get(field)):
            return None, f"registration_{field}_invalid"
    hash_fields = (
        "adapter_implementation_hash",
        "source_evidence_registration_receipt_hash",
        "source_longitudinal_coverage_evaluation_receipt_hash",
        "occurrence_provider_public_key_hash",
        "occurrence_provider_implementation_hash",
        "time_authority_public_key_hash",
        "time_authority_implementation_hash",
        "conformance_auditor_public_key_hash",
        "governance_auditor_public_key_hash",
        "occurrence_conformance_suite_hash",
        "time_conformance_suite_hash",
        "key_ceremony_transcript_hash",
        "rotation_policy_hash",
        "custody_policy_hash",
    )
    for field in hash_fields:
        if not _strict_hash(value.get(field)):
            return None, f"registration_{field}_invalid"
    vector_fields = (
        "occurrence_required_vector_count",
        "time_required_vector_count",
    )
    for field in vector_fields:
        if not _strict_int(value.get(field), minimum=1, maximum=MAX_VECTOR_COUNT):
            return None, f"registration_{field}_invalid"
    epoch_fields = ("occurrence_key_epoch", "time_authority_key_epoch")
    for field in epoch_fields:
        if not _strict_int(value.get(field), maximum=2**31 - 1):
            return None, f"registration_{field}_invalid"
    time_fields = (
        "key_valid_from_ms",
        "key_valid_until_ms",
        "max_audit_duration_ms",
        "max_receipt_issue_delay_ms",
        "max_audit_age_ms",
        "max_revocation_snapshot_age_ms",
    )
    for field in time_fields:
        if not _strict_int(value.get(field), minimum=1):
            return None, f"registration_{field}_invalid"
    if value["key_valid_until_ms"] <= value["key_valid_from_ms"]:
        return None, "registration_key_validity_window_invalid"
    if not _valid_previous_commitment(
        value["occurrence_key_epoch"],
        value["occurrence_previous_key_commitment"],
        value["occurrence_provider_public_key_hash"],
    ):
        return None, "registration_occurrence_previous_key_commitment_invalid"
    if not _valid_previous_commitment(
        value["time_authority_key_epoch"],
        value["time_authority_previous_key_commitment"],
        value["time_authority_public_key_hash"],
    ):
        return None, "registration_time_authority_previous_key_commitment_invalid"
    key_ids = (
        value["occurrence_provider_key_id"],
        value["time_authority_key_id"],
        value["conformance_auditor_key_id"],
        value["governance_auditor_key_id"],
    )
    if len(set(key_ids)) != len(key_ids):
        return None, "registration_role_key_ids_not_distinct"
    key_hashes = (
        value["occurrence_provider_public_key_hash"],
        value["time_authority_public_key_hash"],
        value["conformance_auditor_public_key_hash"],
        value["governance_auditor_public_key_hash"],
    )
    if len(set(key_hashes)) != len(key_hashes):
        return None, "registration_role_key_hashes_not_distinct"
    entity_ids = (
        value["occurrence_provider_id"],
        value["time_authority_id"],
        value["conformance_auditor_id"],
        value["governance_auditor_id"],
    )
    if len(set(entity_ids)) != len(entity_ids):
        return None, "registration_role_entity_ids_not_distinct"
    audit_run_ids = (
        value["occurrence_audit_run_id"],
        value["time_audit_run_id"],
        value["governance_audit_run_id"],
    )
    if len(set(audit_run_ids)) != len(audit_run_ids):
        return None, "registration_audit_run_ids_not_distinct"
    if value["occurrence_conformance_suite_id"] == value["time_conformance_suite_id"]:
        return None, "registration_conformance_suite_ids_not_distinct"
    if value["occurrence_conformance_suite_hash"] == value["time_conformance_suite_hash"]:
        return None, "registration_conformance_suite_hashes_not_distinct"
    if (
        value["source_evidence_registration_receipt_hash"]
        == value["source_longitudinal_coverage_evaluation_receipt_hash"]
    ):
        return None, "registration_source_receipt_hashes_not_distinct"
    return dict(value), None


def build_provider_identity_witness_conformance_key_governance_registration_v1(
    registration: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_registration(status=UNKNOWN_STATUS, reason=error)
    facts = _registration_facts(registered=True)
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
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_witness_conformance_key_governance_registration_v1(
    receipt: Any,
    *,
    registration: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    expected = build_provider_identity_witness_conformance_key_governance_registration_v1(
        registration
    )
    return strict_json_contract_equal(receipt, expected)


def _canonical_bytes(value: dict[str, Any]) -> bytes | None:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None


def _decode_b64url(value: Any) -> bytes | None:
    if type(value) is not str or _B64URL.fullmatch(value) is None:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError):
        return None
    if base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=") != value:
        return None
    return decoded


def _verify_signature(
    *,
    receipt: dict[str, Any],
    public_key: Any,
    expected_public_key_hash: str,
    domain: str,
) -> bool:
    public_key_bytes = _decode_b64url(public_key)
    signature = _decode_b64url(receipt.get("signature"))
    if public_key_bytes is None or len(public_key_bytes) != 32 or signature is None:
        return False
    if hashlib.sha256(public_key_bytes).hexdigest() != expected_public_key_hash:
        return False
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    canonical = _canonical_bytes(unsigned)
    if canonical is None:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            signature,
            domain.encode("ascii") + b"\x00" + canonical,
        )
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def _validate_conformance_receipt(
    value: Any,
    *,
    registration: dict[str, Any],
    registration_receipt_hash: str,
    role: str,
    public_key: Any,
    reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _CONFORMANCE_FIELDS:
        return None, f"{role}_conformance_receipt_shape_invalid"
    prefix = "occurrence" if role == "occurrence_provider" else "time"
    entity_prefix = "occurrence_provider" if role == "occurrence_provider" else "time_authority"
    expected = {
        "schema": CONFORMANCE_RECEIPT_SCHEMA,
        "audit_registration_receipt_hash": registration_receipt_hash,
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
        "auditor_id": registration["conformance_auditor_id"],
        "auditor_key_id": registration["conformance_auditor_key_id"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"{role}_conformance_{key}_mismatch"
    for field in ("started_at_ms", "completed_at_ms", "issued_at_ms"):
        if not _strict_int(value.get(field)):
            return None, f"{role}_conformance_{field}_invalid"
    started_at = value["started_at_ms"]
    completed_at = value["completed_at_ms"]
    issued_at = value["issued_at_ms"]
    if not started_at <= completed_at <= issued_at <= reference_time_ms:
        return None, f"{role}_conformance_time_order_invalid"
    if completed_at - started_at > registration["max_audit_duration_ms"]:
        return None, f"{role}_conformance_audit_duration_exceeded"
    if issued_at - completed_at > registration["max_receipt_issue_delay_ms"]:
        return None, f"{role}_conformance_issue_delay_exceeded"
    if reference_time_ms - issued_at > registration["max_audit_age_ms"]:
        return None, f"{role}_conformance_audit_age_exceeded"
    if not (
        registration["key_valid_from_ms"]
        <= started_at
        <= completed_at
        <= registration["key_valid_until_ms"]
    ):
        return None, f"{role}_conformance_target_key_validity_mismatch"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_public_key_hash=registration["conformance_auditor_public_key_hash"],
        domain=CONFORMANCE_SIGNATURE_DOMAIN,
    ):
        return None, f"{role}_conformance_signature_invalid"
    return dict(value), None


def _validate_governance_receipt(
    value: Any,
    *,
    registration: dict[str, Any],
    registration_receipt_hash: str,
    public_key: Any,
    reference_time_ms: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if type(value) is not dict or set(value) != _GOVERNANCE_FIELDS:
        return None, "governance_receipt_shape_invalid"
    expected = {
        "schema": GOVERNANCE_RECEIPT_SCHEMA,
        "audit_registration_receipt_hash": registration_receipt_hash,
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
        "occurrence_key_revoked": False,
        "time_authority_key_revoked": False,
        "custody_policy_id": registration["custody_policy_id"],
        "custody_policy_hash": registration["custody_policy_hash"],
        "custody_domains_separated": True,
        "auditor_id": registration["governance_auditor_id"],
        "auditor_key_id": registration["governance_auditor_key_id"],
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_encoding": SIGNATURE_ENCODING,
    }
    for key, expected_value in expected.items():
        if not strict_json_contract_equal(value.get(key), expected_value):
            return None, f"governance_{key}_mismatch"
    if not _strict_hash(value.get("revocation_snapshot_hash")):
        return None, "governance_revocation_snapshot_hash_invalid"
    for field in (
        "revocation_snapshot_at_ms",
        "audit_completed_at_ms",
        "issued_at_ms",
    ):
        if not _strict_int(value.get(field)):
            return None, f"governance_{field}_invalid"
    snapshot_at = value["revocation_snapshot_at_ms"]
    completed_at = value["audit_completed_at_ms"]
    issued_at = value["issued_at_ms"]
    if not snapshot_at <= completed_at <= issued_at <= reference_time_ms:
        return None, "governance_time_order_invalid"
    if issued_at - completed_at > registration["max_receipt_issue_delay_ms"]:
        return None, "governance_issue_delay_exceeded"
    if reference_time_ms - issued_at > registration["max_audit_age_ms"]:
        return None, "governance_audit_age_exceeded"
    if reference_time_ms - snapshot_at > registration["max_revocation_snapshot_age_ms"]:
        return None, "governance_revocation_snapshot_age_exceeded"
    if not (
        registration["key_valid_from_ms"]
        <= snapshot_at
        <= completed_at
        <= reference_time_ms
        <= registration["key_valid_until_ms"]
    ):
        return None, "governance_key_validity_window_mismatch"
    if not _verify_signature(
        receipt=value,
        public_key=public_key,
        expected_public_key_hash=registration["governance_auditor_public_key_hash"],
        domain=GOVERNANCE_SIGNATURE_DOMAIN,
    ):
        return None, "governance_signature_invalid"
    return dict(value), None


def evaluate_provider_identity_witness_conformance_key_governance_v1(
    *,
    registration: Any,
    registration_receipt: Any,
    source_evidence_registration: Any,
    source_evidence_registration_receipt: Any,
    source_longitudinal_registration: Any,
    source_longitudinal_registration_receipt: Any,
    source_longitudinal_evaluations: Any,
    source_longitudinal_evaluation_receipt: Any,
    occurrence_conformance_receipt: Any,
    time_conformance_receipt: Any,
    conformance_auditor_public_key: Any,
    key_governance_receipt: Any,
    governance_auditor_public_key: Any,
    reference_time_ms: Any,
) -> dict[str, Any]:
    normalized, error = _normalize_registration(registration)
    if normalized is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=error)
    if not verify_provider_identity_witness_conformance_key_governance_registration_v1(
        registration_receipt,
        registration=registration,
    ):
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="audit_registration_receipt_invalid",
        )
    if registration_receipt.get("status") != REGISTERED_STATUS:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="audit_registration_status_invalid",
        )
    if not _strict_int(reference_time_ms):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="reference_time_ms_invalid")
    source_values = (
        source_evidence_registration,
        source_evidence_registration_receipt,
        source_longitudinal_registration,
        source_longitudinal_registration_receipt,
        source_longitudinal_evaluation_receipt,
    )
    if any(type(value) is not dict for value in source_values):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_shape_invalid")
    try:
        source_registration_ok = source_registration_contract.verify_provider_identity_assertion_uniqueness_freshness_registration_v1(
            source_evidence_registration_receipt,
            registration=source_evidence_registration,
        )
        source_coverage_registration_ok = source_coverage_contract.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_registration_v1(
            source_longitudinal_registration_receipt,
            registration=source_longitudinal_registration,
        )
        source_coverage_evaluation_ok = source_coverage_contract.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1(
            source_longitudinal_evaluation_receipt,
            registration=source_longitudinal_registration,
            registration_receipt=source_longitudinal_registration_receipt,
            source_evaluations=source_longitudinal_evaluations,
        )
    except Exception:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_verifier_error")
    if source_registration_ok is not True:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_evidence_registration_not_verified",
        )
    if source_coverage_registration_ok is not True:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_registration_not_verified",
        )
    if source_coverage_evaluation_ok is not True:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_evaluation_not_verified",
        )
    if (
        source_evidence_registration_receipt.get("schema")
        != source_registration_contract.RECEIPT_SCHEMA
        or source_evidence_registration_receipt.get("status")
        != source_registration_contract.REGISTERED_STATUS
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_registration_status_invalid")
    if (
        source_longitudinal_registration_receipt.get("schema")
        != source_coverage_contract.REGISTRATION_RECEIPT_SCHEMA
        or source_longitudinal_registration_receipt.get("status")
        != source_coverage_contract.REGISTERED_STATUS
    ):
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_registration_status_invalid",
        )
    if (
        source_longitudinal_evaluation_receipt.get("schema")
        != source_coverage_contract.EVALUATION_SCHEMA
        or source_longitudinal_evaluation_receipt.get("status")
        != source_coverage_contract.VERIFIED_STATUS
    ):
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_evaluation_status_invalid",
        )
    source_registration_hash = source_evidence_registration_receipt.get("receipt_hash")
    source_coverage_hash = source_longitudinal_evaluation_receipt.get("receipt_hash")
    source_coverage_registration_hash = source_longitudinal_registration_receipt.get(
        "receipt_hash"
    )
    if not all(
        _strict_hash(value)
        for value in (
            source_registration_hash,
            source_coverage_hash,
            source_coverage_registration_hash,
        )
    ):
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="source_receipt_hash_invalid")
    if source_registration_hash != normalized["source_evidence_registration_receipt_hash"]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_evidence_registration_receipt_hash_mismatch",
        )
    if source_coverage_hash != normalized[
        "source_longitudinal_coverage_evaluation_receipt_hash"
    ]:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_evaluation_receipt_hash_mismatch",
        )
    source_key_bindings = {
        "occurrence_provider_id": normalized["occurrence_provider_id"],
        "occurrence_provider_key_id": normalized["occurrence_provider_key_id"],
        "occurrence_provider_public_key_hash": normalized[
            "occurrence_provider_public_key_hash"
        ],
        "time_authority_id": normalized["time_authority_id"],
        "time_authority_key_id": normalized["time_authority_key_id"],
        "time_authority_public_key_hash": normalized["time_authority_public_key_hash"],
    }
    for key, expected in source_key_bindings.items():
        if not strict_json_contract_equal(source_evidence_registration.get(key), expected):
            return _sealed_evaluation(
                status=UNKNOWN_STATUS,
                reason=f"source_{key}_mismatch",
            )
    if source_longitudinal_registration.get(
        "source_evidence_registration_receipt_hash"
    ) != source_registration_hash:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_registration_binding_mismatch",
        )
    source_coverage_evidence = source_longitudinal_evaluation_receipt.get("evidence")
    if type(source_coverage_evidence) is not dict:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_evidence_shape_invalid",
        )
    if source_coverage_evidence.get(
        "source_evidence_registration_receipt_hash"
    ) != source_registration_hash:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_evaluation_binding_mismatch",
        )
    if source_coverage_evidence.get(
        "coverage_registration_receipt_hash"
    ) != source_coverage_registration_hash:
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="source_longitudinal_registration_receipt_binding_mismatch",
        )
    audit_registration_hash = registration_receipt.get("receipt_hash")
    if not _strict_hash(audit_registration_hash):
        return _sealed_evaluation(
            status=UNKNOWN_STATUS,
            reason="audit_registration_receipt_hash_invalid",
        )
    occurrence_claim, claim_error = _validate_conformance_receipt(
        occurrence_conformance_receipt,
        registration=normalized,
        registration_receipt_hash=audit_registration_hash,
        role="occurrence_provider",
        public_key=conformance_auditor_public_key,
        reference_time_ms=reference_time_ms,
    )
    if occurrence_claim is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=claim_error)
    time_claim, claim_error = _validate_conformance_receipt(
        time_conformance_receipt,
        registration=normalized,
        registration_receipt_hash=audit_registration_hash,
        role="time_authority",
        public_key=conformance_auditor_public_key,
        reference_time_ms=reference_time_ms,
    )
    if time_claim is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=claim_error)
    occurrence_claim_hash = strict_canonical_hash(occurrence_claim)
    time_claim_hash = strict_canonical_hash(time_claim)
    if occurrence_claim_hash == time_claim_hash:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason="conformance_receipt_reused")
    governance_claim, claim_error = _validate_governance_receipt(
        key_governance_receipt,
        registration=normalized,
        registration_receipt_hash=audit_registration_hash,
        public_key=governance_auditor_public_key,
        reference_time_ms=reference_time_ms,
    )
    if governance_claim is None:
        return _sealed_evaluation(status=UNKNOWN_STATUS, reason=claim_error)
    facts = _evaluation_facts()
    for key in (
        "source_evidence_registration_reverified",
        "source_longitudinal_coverage_reverified",
        "source_witness_key_binding_verified",
        "auditor_roles_separated",
        "occurrence_conformance_signature_verified",
        "time_conformance_signature_verified",
        "conformance_suites_and_vectors_bound",
        "key_governance_signature_verified",
        "key_ceremony_claim_bound",
        "rotation_lineage_claims_bound",
        "non_revocation_claims_bound",
        "custody_separation_claim_bound",
    ):
        facts[key] = True
    evidence = _evaluation_evidence()
    evidence.update(
        {
            "audit_registration_receipt_hash": audit_registration_hash,
            "source_evidence_registration_receipt_hash": source_registration_hash,
            "source_longitudinal_coverage_evaluation_receipt_hash": source_coverage_hash,
            "occurrence_conformance_receipt_hash": occurrence_claim_hash,
            "time_conformance_receipt_hash": time_claim_hash,
            "key_governance_receipt_hash": strict_canonical_hash(governance_claim),
            "occurrence_conformance_suite_hash": normalized[
                "occurrence_conformance_suite_hash"
            ],
            "time_conformance_suite_hash": normalized["time_conformance_suite_hash"],
            "key_ceremony_transcript_hash": normalized["key_ceremony_transcript_hash"],
            "rotation_policy_hash": normalized["rotation_policy_hash"],
            "revocation_snapshot_hash": governance_claim["revocation_snapshot_hash"],
            "custody_policy_hash": normalized["custody_policy_hash"],
            "occurrence_key_epoch": normalized["occurrence_key_epoch"],
            "time_authority_key_epoch": normalized["time_authority_key_epoch"],
            "audit_reference_time_ms": reference_time_ms,
        }
    )
    return _sealed_evaluation(
        status=VERIFIED_STATUS,
        reason=None,
        facts=facts,
        evidence=evidence,
    )


def verify_provider_identity_witness_conformance_key_governance_evaluation_v1(
    receipt: Any,
    **inputs: Any,
) -> bool:
    if type(receipt) is not dict:
        return False
    expected = evaluate_provider_identity_witness_conformance_key_governance_v1(
        **inputs
    )
    return strict_json_contract_equal(receipt, expected)


__all__ = [
    "CANONICAL_HASH_ALGORITHM",
    "CANONICAL_HASH_ENCODING",
    "CONFORMANCE_RECEIPT_SCHEMA",
    "CONFORMANCE_SIGNATURE_DOMAIN",
    "EVALUATION_SCHEMA",
    "GENESIS_COMMITMENT",
    "GOVERNANCE_RECEIPT_SCHEMA",
    "GOVERNANCE_SIGNATURE_DOMAIN",
    "REGISTERED_STATUS",
    "REGISTRATION_RECEIPT_SCHEMA",
    "REGISTRATION_SCHEMA",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_ENCODING",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATUS",
    "VERIFIED_STATUS",
    "build_provider_identity_witness_conformance_key_governance_registration_v1",
    "evaluate_provider_identity_witness_conformance_key_governance_v1",
    "verify_provider_identity_witness_conformance_key_governance_evaluation_v1",
    "verify_provider_identity_witness_conformance_key_governance_registration_v1",
]
