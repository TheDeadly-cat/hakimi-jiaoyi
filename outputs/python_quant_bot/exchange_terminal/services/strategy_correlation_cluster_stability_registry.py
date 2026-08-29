"""Pure candidate registry contracts for protocol-v9 cluster stability."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    AUDIT_SCHEMA_VERSION as STABILITY_AUDIT_SCHEMA_VERSION,
    GATE_SCHEMA_VERSION as STABILITY_GATE_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION as STABILITY_GATE_POLICY_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_protocol import (
    POLICY_SCHEMA_VERSION as CLUSTER_STABILITY_POLICY_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as PROTOCOL_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_stability_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_global_independence_registry import (
    BINDING_ASSESSMENT_SCHEMA_VERSION as SOURCE_REGISTRY_BINDING_SCHEMA_VERSION,
    REGISTRY_ASSET_SCHEMA_VERSION as SOURCE_REGISTRY_ASSET_SCHEMA_VERSION,
)


REGISTRY_ASSET_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-asset-v1"
)
REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-asset-v1-verification-v1"
)
BINDING_ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-binding-assessment-v1"
)
BINDING_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-binding-assessment-v1-verification-v1"
)
METHODOLOGY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-registry-methodology-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_date(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _is_utc_timestamp(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def _before_evidence_date(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        _is_date(value)
        and _is_date(evidence_cutoff_date)
        and date.fromisoformat(value) < date.fromisoformat(evidence_cutoff_date)
    )


def _timestamp_before_evidence(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        _is_utc_timestamp(value)
        and _is_date(evidence_cutoff_date)
        and datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").date()
        < date.fromisoformat(evidence_cutoff_date)
    )


def build_strategy_correlation_cluster_stability_registry_asset(
    protocol_registration: Any,
    *,
    registry_id: Any,
    registry_source: Any,
    registry_source_version: Any,
    registry_source_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    protocol = protocol_registration if type(protocol_registration) is dict else {}
    methodology = {
        "schema_version": METHODOLOGY_SCHEMA_VERSION,
        "protocol_registration_v7_required": True,
        "cluster_stability_policy_hash_required": True,
        "report20_consumer_contract_required": True,
        "stability_gate_contract_required": True,
        "external_stability_bindings_required": True,
        "selection_returns_used": False,
        "post_evidence_edits_allowed": False,
    }
    asset = {
        "schema_version": REGISTRY_ASSET_SCHEMA_VERSION,
        "registry_id": registry_id,
        "registry_source": registry_source,
        "registry_source_version": registry_source_version,
        "registry_source_hash": registry_source_hash,
        "effective_date": effective_date,
        "frozen_at": frozen_at,
        "protocol_registration_schema_version": PROTOCOL_REGISTRATION_SCHEMA_VERSION,
        "protocol_registration_hash": protocol.get("registration_hash"),
        "cluster_stability_policy_schema_version": CLUSTER_STABILITY_POLICY_SCHEMA_VERSION,
        "cluster_stability_policy_hash": protocol.get(
            "cluster_stability_policy_hash"
        ),
        "stability_gate_policy_schema_version": STABILITY_GATE_POLICY_SCHEMA_VERSION,
        "stability_audit_schema_version": STABILITY_AUDIT_SCHEMA_VERSION,
        "stability_gate_schema_version": STABILITY_GATE_SCHEMA_VERSION,
        "source_global_registry_asset_schema_version": SOURCE_REGISTRY_ASSET_SCHEMA_VERSION,
        "source_global_registry_binding_schema_version": (
            SOURCE_REGISTRY_BINDING_SCHEMA_VERSION
        ),
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "target_extension_verification_schema_version": (
            TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION
        ),
        "methodology": methodology,
        "status": "FROZEN_CANDIDATE",
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(asset, "registry_asset_hash")


def verify_strategy_correlation_cluster_stability_registry_asset(
    document: Any,
    *,
    protocol_registration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("registry_asset_invalid")
        document = {}
    elif strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    try:
        protocol_verification = (
            verify_strategy_correlation_cluster_stability_protocol_registration(
                protocol_registration
            )
            if type(protocol_registration) is dict
            else {"status": "BLOCK"}
        )
    except (TypeError, ValueError):
        protocol_verification = {"status": "BLOCK"}
    if protocol_verification.get("status") != "PASS":
        blockers.append("protocol_registration_v7_invalid")
    if not all(
        type(document.get(field)) is str and document.get(field)
        for field in ("registry_id", "registry_source", "registry_source_version")
    ):
        blockers.append("registry_identity_invalid")
    if not _is_sha256(document.get("registry_source_hash")):
        blockers.append("registry_source_hash_invalid")
    if not _is_date(document.get("effective_date")):
        blockers.append("effective_date_invalid")
    if not _is_utc_timestamp(document.get("frozen_at")):
        blockers.append("frozen_at_invalid")

    expected = build_strategy_correlation_cluster_stability_registry_asset(
        protocol_registration,
        registry_id=document.get("registry_id"),
        registry_source=document.get("registry_source"),
        registry_source_version=document.get("registry_source_version"),
        registry_source_hash=document.get("registry_source_hash"),
        effective_date=document.get("effective_date"),
        frozen_at=document.get("frozen_at"),
    )
    if not strict_json_contract_equal(document, expected):
        blockers.append("registry_asset_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def assess_strategy_correlation_cluster_stability_registry_binding(
    registry_asset: Any,
    protocol_registration: Any,
    *,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
) -> dict[str, Any]:
    try:
        asset_verification = verify_strategy_correlation_cluster_stability_registry_asset(
            registry_asset,
            protocol_registration=protocol_registration,
        )
        protocol_verification = verify_strategy_correlation_cluster_stability_protocol_registration(
            protocol_registration
        )
    except (TypeError, ValueError):
        asset_verification = {"status": "BLOCK"}
        protocol_verification = {"status": "BLOCK"}
    asset = registry_asset if type(registry_asset) is dict else {}
    protocol = protocol_registration if type(protocol_registration) is dict else {}
    facts = {
        "registry_asset_independently_verified": asset_verification.get("status")
        == "PASS",
        "protocol_registration_independently_verified": protocol_verification.get(
            "status"
        )
        == "PASS",
        "registry_asset_hash_bound": _is_sha256(expected_registry_asset_hash)
        and asset.get("registry_asset_hash") == expected_registry_asset_hash,
        "registry_source_hash_bound": _is_sha256(expected_registry_source_hash)
        and asset.get("registry_source_hash") == expected_registry_source_hash,
        "protocol_registration_hash_bound": _is_sha256(
            expected_protocol_registration_hash
        )
        and protocol.get("registration_hash")
        == expected_protocol_registration_hash,
        "cluster_stability_policy_hash_bound": _is_sha256(
            expected_cluster_stability_policy_hash
        )
        and protocol.get("cluster_stability_policy_hash")
        == expected_cluster_stability_policy_hash,
        "report20_contract_bound": asset.get("target_report_schema_version") == 20
        and asset.get("target_extension_schema_version")
        == TARGET_EXTENSION_SCHEMA_VERSION,
        "stability_gate_contract_bound": asset.get("stability_gate_schema_version")
        == STABILITY_GATE_SCHEMA_VERSION,
        "effective_before_evidence": _before_evidence_date(
            asset.get("effective_date"),
            evidence_cutoff_date,
        ),
        "frozen_before_evidence": _timestamp_before_evidence(
            asset.get("frozen_at"),
            evidence_cutoff_date,
        ),
        "candidate_only_asserted": asset.get("candidate_only") is True,
        "formal_registry_unbound_asserted": asset.get("formal_registry_bound")
        is False,
    }
    blockers = [name for name, passed in facts.items() if passed is not True]
    candidate_bound = not blockers
    assessment = {
        "schema_version": BINDING_ASSESSMENT_SCHEMA_VERSION,
        "registry_id": asset.get("registry_id"),
        "evidence_cutoff_date": evidence_cutoff_date,
        "facts": facts,
        "blockers": blockers,
        "status": "CANDIDATE_BOUND" if candidate_bound else "BLOCK",
        "candidate_bound": candidate_bound,
        "candidate_only": True,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(assessment, "assessment_hash")


def verify_strategy_correlation_cluster_stability_registry_binding(
    document: Any,
    *,
    registry_asset: Any,
    protocol_registration: Any,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("registry_binding_invalid")
    elif strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    expected = assess_strategy_correlation_cluster_stability_registry_binding(
        registry_asset,
        protocol_registration,
        evidence_cutoff_date=evidence_cutoff_date,
        expected_registry_asset_hash=expected_registry_asset_hash,
        expected_registry_source_hash=expected_registry_source_hash,
        expected_protocol_registration_hash=expected_protocol_registration_hash,
        expected_cluster_stability_policy_hash=(
            expected_cluster_stability_policy_hash
        ),
    )
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("registry_binding_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": BINDING_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "candidate_bound": (
            expected["candidate_bound"] if status == "PASS" else False
        ),
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "BINDING_ASSESSMENT_SCHEMA_VERSION",
    "BINDING_VERIFICATION_SCHEMA_VERSION",
    "METHODOLOGY_SCHEMA_VERSION",
    "REGISTRY_ASSET_SCHEMA_VERSION",
    "REGISTRY_ASSET_VERIFICATION_SCHEMA_VERSION",
    "assess_strategy_correlation_cluster_stability_registry_binding",
    "build_strategy_correlation_cluster_stability_registry_asset",
    "verify_strategy_correlation_cluster_stability_registry_asset",
    "verify_strategy_correlation_cluster_stability_registry_binding",
]
