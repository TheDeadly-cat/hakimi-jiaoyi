"""Pure candidate binding between protocol-v10 registration and report21."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    GATE_SCHEMA_VERSION as TEMPORAL_STABILITY_GATE_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_protocol import (
    REGISTRATION_SCHEMA_VERSION as PROTOCOL_REGISTRATION_SCHEMA_VERSION,
    TARGET_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)


ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-stability-report-binding-assessment-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-stability-report-binding-assessment-v1-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _binding_id(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        return ""
    return value


def _report_identity_set(
    report21_extension: Any,
) -> tuple[list[dict[str, str]], str] | None:
    entries = (
        report21_extension.get("entries")
        if type(report21_extension) is dict
        else None
    )
    if type(entries) is not list or not entries:
        return None
    identities: list[tuple[str, str, str]] = []
    for entry in entries:
        if type(entry) is not dict:
            return None
        identity = tuple(
            entry.get(field) for field in ("strategy_id", "variant_id", "lane")
        )
        if not all(type(value) is str and value for value in identity):
            return None
        identities.append(identity)
    if len(set(identities)) != len(identities):
        return None
    normalized = [
        {"strategy_id": identity[0], "variant_id": identity[1], "lane": identity[2]}
        for identity in sorted(identities)
    ]
    return normalized, strict_canonical_hash(normalized)


def _verification(blockers: list[str], *, candidate_bound: bool = False) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    status = "PASS" if not unique else "BLOCK"
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": unique,
        "candidate_bound": candidate_bound if status == "PASS" else False,
        "candidate_only": True,
        "formal_registration_report_binding": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def assess_strategy_correlation_cluster_temporal_stability_report_binding(
    protocol_registration: Any,
    report21_extension: Any,
    *,
    binding_id: Any,
    expected_protocol_registration_hash: Any,
    expected_report21_extension_hash: Any,
    expected_report_identity_set_hash: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
) -> dict[str, Any]:
    registration = protocol_registration if type(protocol_registration) is dict else {}
    report = report21_extension if type(report21_extension) is dict else {}
    normalized_binding_id = _binding_id(binding_id)
    try:
        registration_verification = (
            verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
                registration
            )
        )
    except (KeyError, TypeError, ValueError):
        registration_verification = {"status": "BLOCK"}
    try:
        report_verification = (
            verify_strategy_correlation_cluster_temporal_stability_report_extension(
                report,
                expected_base_report_hash=expected_base_report_hash,
                expected_global_independence_extension_hash=(
                    expected_global_independence_extension_hash
                ),
                expected_cluster_stability_extension_hash=(
                    expected_cluster_stability_extension_hash
                ),
                expected_registry_bindings=expected_registry_bindings,
                expected_stability_bindings=expected_stability_bindings,
                expected_temporal_stability_bindings=(
                    expected_temporal_stability_bindings
                ),
            )
        )
    except (KeyError, TypeError, ValueError):
        report_verification = {"status": "BLOCK", "decision": "BLOCK"}
    try:
        identity_set = _report_identity_set(report)
    except (TypeError, ValueError):
        identity_set = None
    identities = identity_set[0] if identity_set is not None else []
    identity_set_hash = identity_set[1] if identity_set is not None else ""
    report_entries = report.get("entries") if type(report.get("entries")) is list else []
    temporal_gate_schemas = {
        entry.get("temporal_stability_gate", {}).get("schema_version")
        for entry in report_entries
        if type(entry) is dict
        and type(entry.get("temporal_stability_gate")) is dict
    }
    facts = {
        "protocol_registration_independently_verified": registration_verification.get(
            "status"
        )
        == "PASS",
        "report21_extension_independently_verified": report_verification.get("status")
        == "PASS",
        "protocol_registration_hash_bound": _is_sha256(
            expected_protocol_registration_hash
        )
        and registration.get("registration_hash")
        == expected_protocol_registration_hash,
        "report21_extension_hash_bound": _is_sha256(
            expected_report21_extension_hash
        )
        and report.get("extension_hash") == expected_report21_extension_hash,
        "report_identity_set_valid": identity_set is not None,
        "report_identity_set_hash_bound": _is_sha256(
            expected_report_identity_set_hash
        )
        and identity_set_hash == expected_report_identity_set_hash,
        "protocol_preregistered": registration.get("status") == "PREREGISTERED",
        "target_report_schema_compatible": registration.get(
            "target_report_schema_version"
        )
        == TARGET_REPORT_SCHEMA_VERSION
        and report.get("target_report_schema_version")
        == TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_compatible": registration.get(
            "target_protocol_schema_version"
        )
        == TARGET_PROTOCOL_SCHEMA_VERSION
        and report.get("target_protocol_schema_version")
        == TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_extension_schema_compatible": registration.get(
            "target_extension_schema_version"
        )
        == TARGET_EXTENSION_SCHEMA_VERSION
        and report.get("schema_version") == TARGET_EXTENSION_SCHEMA_VERSION,
        "temporal_gate_schema_compatible": registration.get(
            "temporal_stability_gate_schema_version"
        )
        == TEMPORAL_STABILITY_GATE_SCHEMA_VERSION
        and temporal_gate_schemas == {TEMPORAL_STABILITY_GATE_SCHEMA_VERSION},
        "report21_consumer_only_asserted": report.get("consumer_only") is True,
        "writer_unavailable_asserted": registration.get("writer_available") is False
        and report.get("writer_available") is False,
        "current_unavailable_asserted": registration.get(
            "current_admission_allowed"
        )
        is False
        and report.get("current_admission_allowed") is False,
    }
    blockers = [name for name, passed in facts.items() if passed is not True]
    if not normalized_binding_id:
        blockers.insert(0, "binding_id_invalid")
    candidate_bound = not blockers
    decision = (
        report_verification.get("decision")
        if report_verification.get("status") == "PASS"
        else "UNKNOWN"
    )
    assessment = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "binding_id": normalized_binding_id,
        "protocol_registration_schema_version": PROTOCOL_REGISTRATION_SCHEMA_VERSION,
        "protocol_registration_hash": registration.get("registration_hash", ""),
        "report21_extension_schema_version": TARGET_EXTENSION_SCHEMA_VERSION,
        "report21_extension_hash": report.get("extension_hash", ""),
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "report_identity_count": len(identities),
        "report_identity_set_hash": identity_set_hash,
        "facts": facts,
        "blockers": blockers,
        "status": "CANDIDATE_BOUND" if candidate_bound else "BLOCK",
        "report21_decision": decision,
        "report21_decision_authority": False,
        "candidate_bound": candidate_bound,
        "candidate_only": True,
        "external_assets_embedded": False,
        "requires_caller_independent_hashes": True,
        "formal_registration_report_binding": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(assessment, "assessment_hash")


def verify_strategy_correlation_cluster_temporal_stability_report_binding(
    document: Any,
    *,
    protocol_registration: Any,
    report21_extension: Any,
    binding_id: Any,
    expected_protocol_registration_hash: Any,
    expected_report21_extension_hash: Any,
    expected_report_identity_set_hash: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("report_binding_invalid")
    elif strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    try:
        expected = assess_strategy_correlation_cluster_temporal_stability_report_binding(
            protocol_registration,
            report21_extension,
            binding_id=binding_id,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_report21_extension_hash=expected_report21_extension_hash,
            expected_report_identity_set_hash=expected_report_identity_set_hash,
            expected_base_report_hash=expected_base_report_hash,
            expected_global_independence_extension_hash=(
                expected_global_independence_extension_hash
            ),
            expected_cluster_stability_extension_hash=(
                expected_cluster_stability_extension_hash
            ),
            expected_registry_bindings=expected_registry_bindings,
            expected_stability_bindings=expected_stability_bindings,
            expected_temporal_stability_bindings=(
                expected_temporal_stability_bindings
            ),
        )
    except (KeyError, TypeError, ValueError):
        return _verification(["report_binding_source_invalid"])
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("report_binding_contract_invalid")
    return _verification(blockers, candidate_bound=expected["candidate_bound"])


__all__ = [
    "ASSESSMENT_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "assess_strategy_correlation_cluster_temporal_stability_report_binding",
    "verify_strategy_correlation_cluster_temporal_stability_report_binding",
]
