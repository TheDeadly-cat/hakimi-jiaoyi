"""Redacted public projection for protocol-v8 migration state."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_global_independence_protocol import (
    REGISTRATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_protocol_registration,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-global-independence-protocol-migration-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-global-independence-protocol-migration-public-summary-verification-v1"
)
STATIC_FINGERPRINT = "20260821-global-independence-protocol-v8-migration-seal-1"

_PERMISSION = {
    "status": "RESEARCH_ONLY",
    "descriptive_only": True,
    "profitability_claim_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "formal_registry_activation_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
}
_REDACTION = {
    "artifact_hashes_exposed": False,
    "policy_hashes_exposed": False,
    "source_registration_exposed": False,
    "registry_identity_exposed": False,
    "classification_source_exposed": False,
    "selection_cutoff_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
}


def _unknown_summary() -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "UNKNOWN",
            "protocol_target": "UNKNOWN",
            "report_target": "UNKNOWN",
            "protocol_registration_status": "UNKNOWN",
            "report19_consumer_status": "UNKNOWN",
            "global_independence_policy_status": "UNKNOWN",
        },
        "gap": {
            "status": "UNKNOWN",
            "formal_registry_status": "UNKNOWN",
            "schema19_writer_status": "UNKNOWN",
            "current_activation_status": "UNKNOWN",
        },
        "maturity": {
            "status": "UNKNOWN",
            "exact_graph_policy": "UNKNOWN",
            "formal_registry": "UNKNOWN",
            "writer": "UNKNOWN",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": None,
        },
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def _observed_summary(source_registration: dict[str, Any]) -> dict[str, Any]:
    prerequisites = source_registration["global_independence_policy"][
        "writer_activation_prerequisites"
    ]
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "OBSERVED",
            "protocol_target": "PROTOCOL_V8",
            "report_target": "REPORT19",
            "protocol_registration_status": "PREREGISTERED",
            "report19_consumer_status": "AVAILABLE",
            "global_independence_policy_status": "SEALED",
        },
        "gap": {
            "status": "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
            "formal_registry_status": "NOT_SUPPLIED",
            "schema19_writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        },
        "maturity": {
            "status": "PROTOCOL_PREREGISTERED",
            "exact_graph_policy": "SEALED",
            "formal_registry": "PENDING",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": len(prerequisites),
        },
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_global_independence_protocol_migration_public_summary(
    source_protocol_registration: Any,
) -> dict[str, Any]:
    """Project verified preregistration state without exposing formal assets."""

    if type(source_protocol_registration) is not dict:
        return _unknown_summary()
    verification = (
        verify_strategy_correlation_global_independence_protocol_registration(
            source_protocol_registration
        )
    )
    if verification.get("status") != "PASS":
        return _unknown_summary()
    if strict_research_authority_violations(source_protocol_registration):
        return _unknown_summary()
    if source_protocol_registration.get("schema_version") != (
        REGISTRATION_SCHEMA_VERSION
    ):
        return _unknown_summary()
    if source_protocol_registration.get("target_protocol_schema_version") != (
        TARGET_PROTOCOL_SCHEMA_VERSION
    ):
        return _unknown_summary()
    if source_protocol_registration.get("target_report_schema_version") != (
        TARGET_REPORT_SCHEMA_VERSION
    ):
        return _unknown_summary()
    return _observed_summary(source_protocol_registration)


def verify_strategy_correlation_global_independence_protocol_migration_public_summary(
    document: Any,
    *,
    source_protocol_registration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    expected = (
        build_strategy_correlation_global_independence_protocol_migration_public_summary(
            source_protocol_registration
        )
    )
    if type(document) is not dict:
        blockers.append("public_summary_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        if not strict_json_contract_equal(document, expected):
            blockers.append("public_summary_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "projection_status": (
            expected["maturity"]["status"] if status == "PASS" else "UNKNOWN"
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_global_independence_protocol_migration_public_summary",
    "verify_strategy_correlation_global_independence_protocol_migration_public_summary",
]
