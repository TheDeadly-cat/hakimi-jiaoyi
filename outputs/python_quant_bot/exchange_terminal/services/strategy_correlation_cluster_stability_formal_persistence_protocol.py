from __future__ import annotations

from typing import Any

try:
    from .strategy_correlation_cluster_stability_formal_registry_adapter import (
        READ_ASSESSMENT_SCHEMA_VERSION,
        READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
        READ_RECORD_SCHEMA_VERSION,
        STATUS_CANDIDATE_RECORD_VERIFIED,
        verify_strategy_correlation_cluster_stability_formal_registry_read_assessment,
    )
    from .strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_json_contract_equal,
    )
    from .strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
        strict_sha256,
        strict_timestamp_date_before,
    )
    from .strict_research_authority import strict_research_authority_invalid
except ImportError:  # pragma: no cover - project-root service import compatibility
    from services.strategy_correlation_cluster_stability_formal_registry_adapter import (
        READ_ASSESSMENT_SCHEMA_VERSION,
        READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
        READ_RECORD_SCHEMA_VERSION,
        STATUS_CANDIDATE_RECORD_VERIFIED,
        verify_strategy_correlation_cluster_stability_formal_registry_read_assessment,
    )
    from services.strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_json_contract_equal,
    )
    from services.strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
        strict_sha256,
        strict_timestamp_date_before,
    )
    from services.strict_research_authority import strict_research_authority_invalid


PERSISTENCE_POLICY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-policy-v1"
)
PERSISTENCE_REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-registration-v1"
)
PERSISTENCE_REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-registration-verification-v1"
)
PERSISTENCE_READINESS_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-readiness-v1"
)
PERSISTENCE_READINESS_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-readiness-verification-v1"
)

STATUS_PREREGISTERED = "PREREGISTERED"
STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED = "READ_CONTRACT_COMPLETE_BUT_BLOCKED"
STATUS_READ_CONTRACT_BLOCKED = "READ_CONTRACT_BLOCKED"
STATUS_UNKNOWN = "UNKNOWN"

ACTIVATION_PREREQUISITES = (
    "PERSISTENCE_REGISTRATION_VERIFIED",
    "EXPLICIT_PROVIDER_IMPLEMENTATION_AUTHORIZATION",
    "PROVIDER_ARTIFACT_HASH_EXTERNALLY_BOUND",
    "ISOLATED_TEMPORARY_STORAGE_ONLY",
    "FORMAL_SOURCE_AND_REGISTRY_SNAPSHOT_EXTERNALLY_BOUND",
    "SEALED_DURABLE_WRITE_RECEIPT",
    "INDEPENDENT_REOPEN_READ_RECEIPT",
    "WRITE_AND_REOPEN_SESSION_SEPARATION",
    "PERSISTED_RECORD_HASH_EXACTLY_REPLAYED",
    "MISSING_DUPLICATE_AND_DRIFT_MATRIX_PASS",
    "NO_FORMAL_RUNTIME_MUTATION_DURING_RESEARCH",
    "FORMAL_PERSISTENCE_ASSET_VERIFIER_IMPLEMENTED",
    "REPORT20_WRITER_ACTIVATED_IN_SEPARATE_SLICE",
    "CURRENT_POINTER_ACTIVATED_IN_SEPARATE_SLICE",
)

REQUIRED_PROVIDER_EVIDENCE_FIELDS = (
    "provider_artifact_hash",
    "formal_registry_source_hash",
    "registry_snapshot_hash",
    "persisted_record_hash",
    "durable_write_receipt_hash",
    "durable_reopen_receipt_hash",
    "write_session_id",
    "reopen_session_id",
    "seeded_at",
    "reopened_at",
    "evidence_cutoff_date",
)

_LOCK_FIELDS = (
    "formal_persistence_verified",
    "formal_persistence_activation_allowed",
    "formal_registry_bound",
    "formal_registry_activation_allowed",
    "provider_implemented",
    "writer_implemented",
    "current_writer_activation_allowed",
    "current_admission_allowed",
)


def _permissions() -> dict[str, bool]:
    return {
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_cluster_stability_formal_persistence_registration(
    *,
    read_adapter_module_hash: Any,
    preregistered_at: Any,
    evidence_cutoff_date: Any,
) -> dict[str, Any]:
    policy = {
        "schema_version": PERSISTENCE_POLICY_SCHEMA_VERSION,
        "source_read_contract": {
            "read_record_schema_version": READ_RECORD_SCHEMA_VERSION,
            "read_assessment_schema_version": READ_ASSESSMENT_SCHEMA_VERSION,
            "read_assessment_verification_schema_version": (
                READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION
            ),
            "read_adapter_module_hash": read_adapter_module_hash,
        },
        "provider_isolation_contract": {
            "environment": "ISOLATED_TEMPORARY_ONLY",
            "provider_mode": "READ_ONLY_AFTER_ISOLATED_SEED",
            "formal_runtime_access_allowed": False,
            "network_provider_allowed": False,
            "production_database_allowed": False,
            "research_runtime_mutation_allowed": False,
            "receipt_producer_implemented": False,
            "required_evidence_fields": list(REQUIRED_PROVIDER_EVIDENCE_FIELDS),
            "session_policy": "WRITE_AND_REOPEN_MUST_BE_DISTINCT",
            "cardinality_policy": "EXACTLY_ONE_AFTER_REOPEN",
        },
        "activation_prerequisites": list(ACTIVATION_PREREQUISITES),
        "activation_prerequisite_count": len(ACTIVATION_PREREQUISITES),
        "provider_implemented": False,
        "formal_persistence_verified": False,
        "formal_persistence_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    document = {
        "schema_version": PERSISTENCE_REGISTRATION_SCHEMA_VERSION,
        "status": STATUS_PREREGISTERED,
        "preregistered_at": preregistered_at,
        "evidence_cutoff_date": evidence_cutoff_date,
        "target_persistence_asset_schema_version": (
            "strategy-correlation-cluster-stability-formal-persistence-asset-v1"
        ),
        "target_provider_receipt_schema_version": (
            "strategy-correlation-cluster-stability-formal-provider-receipt-v1"
        ),
        "policy": policy,
        "provider_implemented": False,
        "formal_persistence_verified": False,
        "formal_persistence_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def verify_strategy_correlation_cluster_stability_formal_persistence_registration(
    document: Any,
    *,
    expected_read_adapter_module_hash: Any,
    preregistered_at: Any,
    evidence_cutoff_date: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    registration = document if isinstance(document, dict) else {}
    if not isinstance(document, dict):
        blockers.append("REGISTRATION_NOT_OBJECT")
    if not strict_sha256(expected_read_adapter_module_hash):
        blockers.append("READ_ADAPTER_MODULE_HASH_INVALID")
    if not strict_timestamp_date_before(preregistered_at, evidence_cutoff_date):
        blockers.append("PREREGISTRATION_NOT_BEFORE_EVIDENCE")
    try:
        expected = build_strategy_correlation_cluster_stability_formal_persistence_registration(
            read_adapter_module_hash=expected_read_adapter_module_hash,
            preregistered_at=preregistered_at,
            evidence_cutoff_date=evidence_cutoff_date,
        )
        if not strict_json_contract_equal(registration, expected):
            blockers.append("REGISTRATION_REBUILD_MISMATCH")
    except Exception:
        blockers.append("REGISTRATION_REBUILD_FAILED")
    if registration.get("status") != STATUS_PREREGISTERED:
        blockers.append("REGISTRATION_STATUS_INVALID")
    policy = registration.get("policy")
    if not isinstance(policy, dict):
        blockers.append("PERSISTENCE_POLICY_MISSING")
    else:
        if policy.get("activation_prerequisites") != list(ACTIVATION_PREREQUISITES):
            blockers.append("ACTIVATION_PREREQUISITES_DRIFT")
        if policy.get("activation_prerequisite_count") != len(
            ACTIVATION_PREREQUISITES
        ):
            blockers.append("ACTIVATION_PREREQUISITE_COUNT_DRIFT")
        provider_contract = policy.get("provider_isolation_contract")
        if not isinstance(provider_contract, dict):
            blockers.append("PROVIDER_ISOLATION_CONTRACT_MISSING")
        elif provider_contract.get("required_evidence_fields") != list(
            REQUIRED_PROVIDER_EVIDENCE_FIELDS
        ):
            blockers.append("PROVIDER_EVIDENCE_FIELDS_DRIFT")
    if strict_research_authority_invalid(registration):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not strict_locked_fields(registration, _LOCK_FIELDS):
        blockers.append("REGISTRATION_AUTHORITY_NOT_LOCKED")
    if isinstance(policy, dict) and not strict_locked_fields(policy, _LOCK_FIELDS):
        blockers.append("POLICY_AUTHORITY_NOT_LOCKED")

    unique_blockers = list(dict.fromkeys(blockers))
    passed = not unique_blockers
    return {
        "schema_version": PERSISTENCE_REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique_blockers,
        "registration_verified": passed,
        "provider_implemented": False,
        "formal_persistence_verified": False,
        "formal_persistence_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


def assess_strategy_correlation_cluster_stability_formal_persistence_readiness(
    registration: Any,
    read_assessment: Any,
    *,
    expected_read_adapter_module_hash: Any,
    preregistered_at: Any,
    evidence_cutoff_date: Any,
    adapter: Any,
    expected_adapter_snapshot_hash: Any,
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
    provider_evidence: Any = None,
    durable_reopen_evidence: Any = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    registration_verification = (
        verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            registration,
            expected_read_adapter_module_hash=expected_read_adapter_module_hash,
            preregistered_at=preregistered_at,
            evidence_cutoff_date=evidence_cutoff_date,
        )
    )
    read_verification = (
        verify_strategy_correlation_cluster_stability_formal_registry_read_assessment(
            read_assessment,
            adapter=adapter,
            expected_adapter_snapshot_hash=expected_adapter_snapshot_hash,
            protocol_registration=protocol_registration,
            registry_asset=registry_asset,
            binding_assessment=binding_assessment,
            evidence_cutoff_date=evidence_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_registry_source_hash=expected_registry_source_hash,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_cluster_stability_policy_hash=(
                expected_cluster_stability_policy_hash
            ),
            registry_id=registry_id,
            formal_registry_source=formal_registry_source,
            formal_registry_source_version=formal_registry_source_version,
            formal_registry_source_hash=formal_registry_source_hash,
            registry_snapshot_hash=registry_snapshot_hash,
            effective_date=effective_date,
            frozen_at=frozen_at,
        )
    )
    registration_verified = registration_verification.get("status") == "PASS"
    read_contract_verified = (
        read_verification.get("status") == "PASS"
        and read_verification.get("decision_status")
        == STATUS_CANDIDATE_RECORD_VERIFIED
        and strict_native_true(read_verification.get("candidate_record_verified"))
        and isinstance(read_assessment, dict)
        and read_assessment.get("status") == STATUS_CANDIDATE_RECORD_VERIFIED
        and strict_native_false(read_assessment.get("formal_persistence_verified"))
        and strict_native_false(read_assessment.get("formal_registry_bound"))
    )

    if not registration_verified:
        blockers.append("PERSISTENCE_REGISTRATION_NOT_VERIFIED")
    if not read_contract_verified:
        blockers.append("ISOLATED_READ_CONTRACT_NOT_VERIFIED")
    blockers.extend(
        (
            "EXPLICIT_PROVIDER_IMPLEMENTATION_AUTHORIZATION_MISSING",
            "PROVIDER_ARTIFACT_MISSING",
            "FORMAL_PERSISTENCE_RECEIPT_MISSING",
            "DURABLE_REOPEN_RECEIPT_MISSING",
            "PROVIDER_SESSION_SEPARATION_MISSING",
            "FORMAL_PERSISTENCE_ASSET_VERIFIER_MISSING",
        )
    )
    if provider_evidence is not None:
        blockers.append("UNSUPPORTED_PROVIDER_EVIDENCE")
    if durable_reopen_evidence is not None:
        blockers.append("UNSUPPORTED_DURABLE_REOPEN_EVIDENCE")

    if not registration_verified:
        status = STATUS_UNKNOWN
    elif read_contract_verified:
        status = STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED
    else:
        status = STATUS_READ_CONTRACT_BLOCKED

    document = {
        "schema_version": PERSISTENCE_READINESS_SCHEMA_VERSION,
        "status": status,
        "decision": "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "facts": {
            "persistence_registration_verified": registration_verified,
            "isolated_read_contract_verified": read_contract_verified,
            "unique_candidate_record_verified": read_contract_verified,
            "provider_evidence_supplied": provider_evidence is not None,
            "durable_reopen_evidence_supplied": durable_reopen_evidence is not None,
            "provider_artifact_bound": False,
            "durable_write_receipt_verified": False,
            "durable_reopen_receipt_verified": False,
            "provider_session_separation_verified": False,
        },
        "provider_implemented": False,
        "formal_persistence_verified": False,
        "formal_persistence_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    return seal_strict_canonical_document(document, "assessment_hash")


def verify_strategy_correlation_cluster_stability_formal_persistence_readiness(
    document: Any,
    registration: Any,
    read_assessment: Any,
    *,
    expected_read_adapter_module_hash: Any,
    preregistered_at: Any,
    evidence_cutoff_date: Any,
    adapter: Any,
    expected_adapter_snapshot_hash: Any,
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
    provider_evidence: Any = None,
    durable_reopen_evidence: Any = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    readiness = document if isinstance(document, dict) else {}
    if not isinstance(document, dict):
        blockers.append("READINESS_NOT_OBJECT")
    try:
        expected = assess_strategy_correlation_cluster_stability_formal_persistence_readiness(
            registration,
            read_assessment,
            expected_read_adapter_module_hash=expected_read_adapter_module_hash,
            preregistered_at=preregistered_at,
            evidence_cutoff_date=evidence_cutoff_date,
            adapter=adapter,
            expected_adapter_snapshot_hash=expected_adapter_snapshot_hash,
            protocol_registration=protocol_registration,
            registry_asset=registry_asset,
            binding_assessment=binding_assessment,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_registry_source_hash=expected_registry_source_hash,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_cluster_stability_policy_hash=(
                expected_cluster_stability_policy_hash
            ),
            registry_id=registry_id,
            formal_registry_source=formal_registry_source,
            formal_registry_source_version=formal_registry_source_version,
            formal_registry_source_hash=formal_registry_source_hash,
            registry_snapshot_hash=registry_snapshot_hash,
            effective_date=effective_date,
            frozen_at=frozen_at,
            provider_evidence=provider_evidence,
            durable_reopen_evidence=durable_reopen_evidence,
        )
        if not strict_json_contract_equal(readiness, expected):
            blockers.append("READINESS_REBUILD_MISMATCH")
    except Exception:
        expected = {}
        blockers.append("READINESS_REBUILD_FAILED")
    if strict_research_authority_invalid(readiness):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not strict_locked_fields(readiness, _LOCK_FIELDS):
        blockers.append("READINESS_AUTHORITY_NOT_LOCKED")
    if readiness.get("decision") != "BLOCK":
        blockers.append("READINESS_DECISION_NOT_BLOCKED")

    unique_blockers = list(dict.fromkeys(blockers))
    passed = not unique_blockers
    return {
        "schema_version": PERSISTENCE_READINESS_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique_blockers,
        "readiness_verified": passed,
        "readiness_status": expected.get("status", STATUS_UNKNOWN),
        "decision": "BLOCK",
        "provider_implemented": False,
        "formal_persistence_verified": False,
        "formal_persistence_activation_allowed": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


__all__ = [
    "PERSISTENCE_POLICY_SCHEMA_VERSION",
    "PERSISTENCE_REGISTRATION_SCHEMA_VERSION",
    "PERSISTENCE_REGISTRATION_VERIFICATION_SCHEMA_VERSION",
    "PERSISTENCE_READINESS_SCHEMA_VERSION",
    "PERSISTENCE_READINESS_VERIFICATION_SCHEMA_VERSION",
    "STATUS_PREREGISTERED",
    "STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED",
    "STATUS_READ_CONTRACT_BLOCKED",
    "STATUS_UNKNOWN",
    "ACTIVATION_PREREQUISITES",
    "REQUIRED_PROVIDER_EVIDENCE_FIELDS",
    "build_strategy_correlation_cluster_stability_formal_persistence_registration",
    "verify_strategy_correlation_cluster_stability_formal_persistence_registration",
    "assess_strategy_correlation_cluster_stability_formal_persistence_readiness",
    "verify_strategy_correlation_cluster_stability_formal_persistence_readiness",
]
