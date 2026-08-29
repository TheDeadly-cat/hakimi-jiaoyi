from __future__ import annotations

from typing import Any

try:
    from .strategy_correlation_cluster_stability_registry import (
        verify_strategy_correlation_cluster_stability_registry_asset,
        verify_strategy_correlation_cluster_stability_registry_binding,
    )
    from .strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
    )
    from .strict_research_authority import strict_research_authority_invalid
except ImportError:  # pragma: no cover - project-root service import compatibility
    from services.strategy_correlation_cluster_stability_registry import (
        verify_strategy_correlation_cluster_stability_registry_asset,
        verify_strategy_correlation_cluster_stability_registry_binding,
    )
    from services.strict_governance_primitives import (
        strict_locked_fields,
        strict_native_false,
        strict_native_true,
    )
    from services.strict_research_authority import strict_research_authority_invalid


PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-public-summary-v1"
)
STATIC_BUILD_FINGERPRINT = (
    "20260821-cluster-stability-registry-candidate-migration-docket-1"
)

STATE_NOT_SUPPLIED = "NOT_SUPPLIED"
STATE_CANDIDATE_BOUND = "CANDIDATE_BOUND"
STATE_CANDIDATE_EVIDENCE_BLOCKED = "CANDIDATE_EVIDENCE_BLOCKED"
STATE_UNKNOWN = "UNKNOWN"

_LOCK_FIELDS = (
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
    maturity_status: str,
    candidate_evidence_bound: bool,
) -> dict[str, Any]:
    summary = {
        "schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
        "static_build_fingerprint": STATIC_BUILD_FINGERPRINT,
        "projection_state": projection_state,
        "source": {
            "status": source_status,
            "protocol": "protocol-v9",
            "report": "report-20",
            "contract": "cluster-stability-registry-candidate-v1",
        },
        "gap": {
            "status": "OPEN",
            "formal_registry": "MISSING",
            "report_writer": "MISSING",
            "current_pointer": "LOCKED",
            "next_required_boundary": "FORMAL_REGISTRY_FINGERPRINT",
        },
        "maturity": {
            "status": maturity_status,
            "candidate_evidence_bound": candidate_evidence_bound,
            "candidate_only": True,
        },
        "permission": {
            "status": "RESEARCH_ONLY",
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
        raise AssertionError("public registry projection must remain research-only")
    return summary


def _unknown_summary() -> dict[str, Any]:
    return _public_summary(
        projection_state=STATE_UNKNOWN,
        source_status="UNKNOWN",
        maturity_status="UNKNOWN",
        candidate_evidence_bound=False,
    )


def project_strategy_correlation_cluster_stability_registry_summary(
    registry_asset: Any = None,
    binding_assessment: Any = None,
    *,
    protocol_registration: Any = None,
    evidence_cutoff_date: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_registry_source_hash: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_cluster_stability_policy_hash: Any = None,
) -> dict[str, Any]:
    """Project candidate-registry evidence without exposing its identities or hashes."""

    if registry_asset is None and binding_assessment is None:
        return _public_summary(
            projection_state=STATE_NOT_SUPPLIED,
            source_status="NOT_SUPPLIED",
            maturity_status="NO_EVIDENCE",
            candidate_evidence_bound=False,
        )

    if not isinstance(registry_asset, dict) or not isinstance(binding_assessment, dict):
        return _unknown_summary()
    if not isinstance(protocol_registration, dict):
        return _unknown_summary()

    try:
        asset_verification = (
            verify_strategy_correlation_cluster_stability_registry_asset(
                registry_asset,
                protocol_registration=protocol_registration,
            )
        )
        binding_verification = (
            verify_strategy_correlation_cluster_stability_registry_binding(
                binding_assessment,
                registry_asset=registry_asset,
                protocol_registration=protocol_registration,
                evidence_cutoff_date=evidence_cutoff_date,
                expected_registry_asset_hash=expected_registry_asset_hash,
                expected_registry_source_hash=expected_registry_source_hash,
                expected_protocol_registration_hash=expected_protocol_registration_hash,
                expected_cluster_stability_policy_hash=(
                    expected_cluster_stability_policy_hash
                ),
            )
        )
    except Exception:
        return _unknown_summary()

    documents = (
        protocol_registration,
        registry_asset,
        binding_assessment,
        asset_verification,
        binding_verification,
    )
    if any(strict_research_authority_invalid(document) for document in documents):
        return _unknown_summary()
    if not all(strict_locked_fields(document, _LOCK_FIELDS) for document in documents[1:]):
        return _unknown_summary()
    if not strict_native_true(registry_asset.get("candidate_only")):
        return _unknown_summary()
    if not strict_native_true(binding_assessment.get("candidate_only")):
        return _unknown_summary()
    if not strict_native_true(asset_verification.get("candidate_only")):
        return _unknown_summary()
    if registry_asset.get("status") != "FROZEN_CANDIDATE":
        return _unknown_summary()
    if asset_verification.get("status") != "PASS":
        return _unknown_summary()
    if binding_verification.get("status") != "PASS":
        return _unknown_summary()

    binding_status = binding_assessment.get("status")
    assessment_bound = binding_assessment.get("candidate_bound")
    verification_bound = binding_verification.get("candidate_bound")
    if (
        binding_status == "CANDIDATE_BOUND"
        and strict_native_true(assessment_bound)
        and strict_native_true(verification_bound)
    ):
        return _public_summary(
            projection_state=STATE_CANDIDATE_BOUND,
            source_status="VERIFIED_CANDIDATE",
            maturity_status="CANDIDATE_BOUND",
            candidate_evidence_bound=True,
        )
    if (
        binding_status == "BLOCK"
        and strict_native_false(assessment_bound)
        and strict_native_false(verification_bound)
    ):
        return _public_summary(
            projection_state=STATE_CANDIDATE_EVIDENCE_BLOCKED,
            source_status="VERIFIED_BLOCK",
            maturity_status="BLOCKED",
            candidate_evidence_bound=False,
        )
    return _unknown_summary()


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "STATIC_BUILD_FINGERPRINT",
    "STATE_NOT_SUPPLIED",
    "STATE_CANDIDATE_BOUND",
    "STATE_CANDIDATE_EVIDENCE_BLOCKED",
    "STATE_UNKNOWN",
    "project_strategy_correlation_cluster_stability_registry_summary",
]
