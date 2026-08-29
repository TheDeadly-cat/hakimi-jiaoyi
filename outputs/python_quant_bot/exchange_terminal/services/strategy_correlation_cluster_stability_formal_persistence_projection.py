from __future__ import annotations

from typing import Any

try:
    from .strategy_correlation_cluster_stability_formal_persistence_protocol import (
        ACTIVATION_PREREQUISITES,
        STATUS_READ_CONTRACT_BLOCKED,
        STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED,
        verify_strategy_correlation_cluster_stability_formal_persistence_readiness,
        verify_strategy_correlation_cluster_stability_formal_persistence_registration,
    )
    from .strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
    )
    from .strict_research_authority import strict_research_authority_invalid
except ImportError:  # pragma: no cover - project-root service import compatibility
    from services.strategy_correlation_cluster_stability_formal_persistence_protocol import (
        ACTIVATION_PREREQUISITES,
        STATUS_READ_CONTRACT_BLOCKED,
        STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED,
        verify_strategy_correlation_cluster_stability_formal_persistence_readiness,
        verify_strategy_correlation_cluster_stability_formal_persistence_registration,
    )
    from services.strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
    )
    from services.strict_research_authority import strict_research_authority_invalid


PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-persistence-public-summary-v1"
)
STATIC_BUILD_FINGERPRINT = (
    "20260821-formal-persistence-preregistration-lockboard-1"
)

STATE_NOT_SUPPLIED = "NOT_SUPPLIED"
STATE_READ_CONTRACT_COMPLETE_BLOCKED = "READ_CONTRACT_COMPLETE_BLOCKED"
STATE_READ_CONTRACT_BLOCKED = "READ_CONTRACT_BLOCKED"
STATE_UNKNOWN = "UNKNOWN"

_LOCK_FIELDS = (
    "provider_implemented",
    "formal_persistence_verified",
    "formal_persistence_activation_allowed",
    "formal_registry_bound",
    "formal_registry_activation_allowed",
    "writer_implemented",
    "current_writer_activation_allowed",
    "current_admission_allowed",
)


def _public_summary(
    *,
    projection_state: str,
    source_status: str,
    read_contract_status: str,
    maturity_status: str,
    read_contract_complete: bool,
) -> dict[str, Any]:
    summary = {
        "schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
        "static_build_fingerprint": STATIC_BUILD_FINGERPRINT,
        "projection_state": projection_state,
        "source": {
            "status": source_status,
            "protocol": "formal-persistence-v1",
            "read_contract": read_contract_status,
        },
        "gap": {
            "status": "OPEN",
            "provider": "MISSING",
            "durable_write_receipt": "MISSING",
            "durable_reopen_receipt": "MISSING",
            "session_separation": "MISSING",
            "formal_persistence_asset": "MISSING",
            "report_writer": "MISSING",
            "current_pointer": "LOCKED",
            "next_required_boundary": "AUTHORIZED_ISOLATED_PROVIDER_EVIDENCE",
        },
        "maturity": {
            "status": maturity_status,
            "read_contract_complete": read_contract_complete,
            "activation_prerequisite_count": len(ACTIVATION_PREREQUISITES),
            "persistence_decision": "BLOCK",
        },
        "permission": {
            "status": "RESEARCH_ONLY",
            "provider_implemented": False,
            "formal_persistence_verified": False,
            "formal_persistence_activation_allowed": False,
            "formal_registry_bound": False,
            "formal_registry_activation_allowed": False,
            "writer_implemented": False,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    if strict_research_authority_invalid(summary):
        raise AssertionError("persistence public projection must remain research-only")
    return summary


def _unknown_summary() -> dict[str, Any]:
    return _public_summary(
        projection_state=STATE_UNKNOWN,
        source_status="UNKNOWN",
        read_contract_status="UNKNOWN",
        maturity_status="UNKNOWN",
        read_contract_complete=False,
    )


def project_strategy_correlation_cluster_stability_formal_persistence_summary(
    registration: Any = None,
    readiness: Any = None,
    *,
    expected_read_adapter_module_hash: Any = None,
    preregistered_at: Any = None,
    evidence_cutoff_date: Any = None,
    adapter: Any = None,
    expected_adapter_snapshot_hash: Any = None,
    protocol_registration: Any = None,
    registry_asset: Any = None,
    binding_assessment: Any = None,
    read_assessment: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_registry_source_hash: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_cluster_stability_policy_hash: Any = None,
    registry_id: Any = None,
    formal_registry_source: Any = None,
    formal_registry_source_version: Any = None,
    formal_registry_source_hash: Any = None,
    registry_snapshot_hash: Any = None,
    effective_date: Any = None,
    frozen_at: Any = None,
    provider_evidence: Any = None,
    durable_reopen_evidence: Any = None,
) -> dict[str, Any]:
    """Project persistence readiness without copying formal or candidate evidence."""

    if registration is None and readiness is None:
        return _public_summary(
            projection_state=STATE_NOT_SUPPLIED,
            source_status="NOT_SUPPLIED",
            read_contract_status="NOT_SUPPLIED",
            maturity_status="NO_EVIDENCE",
            read_contract_complete=False,
        )
    if not isinstance(registration, dict) or not isinstance(readiness, dict):
        return _unknown_summary()
    if not isinstance(read_assessment, dict):
        return _unknown_summary()

    try:
        registration_verification = verify_strategy_correlation_cluster_stability_formal_persistence_registration(
            registration,
            expected_read_adapter_module_hash=expected_read_adapter_module_hash,
            preregistered_at=preregistered_at,
            evidence_cutoff_date=evidence_cutoff_date,
        )
        readiness_verification = verify_strategy_correlation_cluster_stability_formal_persistence_readiness(
            readiness,
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
    except Exception:
        return _unknown_summary()

    documents = (
        registration,
        readiness,
        registration_verification,
        readiness_verification,
    )
    if any(strict_research_authority_invalid(document) for document in documents):
        return _unknown_summary()
    if not all(strict_locked_fields(document, _LOCK_FIELDS) for document in documents):
        return _unknown_summary()
    if registration.get("status") != "PREREGISTERED":
        return _unknown_summary()
    if registration_verification.get("status") != "PASS":
        return _unknown_summary()
    if readiness_verification.get("status") != "PASS":
        return _unknown_summary()
    if readiness.get("decision") != "BLOCK":
        return _unknown_summary()
    if readiness_verification.get("decision") != "BLOCK":
        return _unknown_summary()

    facts = readiness.get("facts")
    if not isinstance(facts, dict):
        return _unknown_summary()
    readiness_status = readiness.get("status")
    verified_status = readiness_verification.get("readiness_status")
    if (
        readiness_status == STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED
        and verified_status == STATUS_READ_CONTRACT_COMPLETE_BUT_BLOCKED
        and strict_native_true(facts.get("persistence_registration_verified"))
        and strict_native_true(facts.get("isolated_read_contract_verified"))
        and strict_native_true(facts.get("unique_candidate_record_verified"))
    ):
        return _public_summary(
            projection_state=STATE_READ_CONTRACT_COMPLETE_BLOCKED,
            source_status="PREREGISTRATION_VERIFIED",
            read_contract_status="COMPLETE",
            maturity_status="READ_CONTRACT_ONLY",
            read_contract_complete=True,
        )
    if (
        readiness_status == STATUS_READ_CONTRACT_BLOCKED
        and verified_status == STATUS_READ_CONTRACT_BLOCKED
        and strict_native_true(facts.get("persistence_registration_verified"))
        and strict_native_false(facts.get("isolated_read_contract_verified"))
        and strict_native_false(facts.get("unique_candidate_record_verified"))
    ):
        return _public_summary(
            projection_state=STATE_READ_CONTRACT_BLOCKED,
            source_status="PREREGISTRATION_VERIFIED",
            read_contract_status="BLOCKED",
            maturity_status="BLOCKED",
            read_contract_complete=False,
        )
    return _unknown_summary()


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "STATIC_BUILD_FINGERPRINT",
    "STATE_NOT_SUPPLIED",
    "STATE_READ_CONTRACT_COMPLETE_BLOCKED",
    "STATE_READ_CONTRACT_BLOCKED",
    "STATE_UNKNOWN",
    "project_strategy_correlation_cluster_stability_formal_persistence_summary",
]
