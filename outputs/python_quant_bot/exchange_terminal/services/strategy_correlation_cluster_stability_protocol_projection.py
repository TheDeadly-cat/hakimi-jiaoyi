"""Redacted protocol-v9 migration projection for cluster stability."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_protocol import (
    verify_strategy_correlation_cluster_stability_protocol_registration,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-cluster-stability-protocol-migration-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-cluster-stability-protocol-migration-public-summary-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260821-cluster-stability-protocol-v9-migration-rail-1"

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
    "registration_hashes_exposed": False,
    "policy_hashes_exposed": False,
    "source_registration_exposed": False,
    "registry_identity_exposed": False,
    "strategy_identities_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
    "correlation_values_exposed": False,
    "interval_values_exposed": False,
    "return_values_exposed": False,
}


def _summary(observed: bool) -> dict[str, Any]:
    if observed:
        source = {
            "status": "OBSERVED",
            "protocol_target": "PROTOCOL_V9",
            "report_target": "REPORT20",
            "protocol_registration_status": "PREREGISTERED",
            "report20_consumer_status": "AVAILABLE",
            "stability_policy_status": "SEALED",
        }
        gap = {
            "status": "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
            "formal_registry_status": "NOT_SUPPLIED",
            "schema20_writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": "PROTOCOL_PREREGISTERED",
            "stability_policy": "SEALED",
            "report20_consumer": "AVAILABLE",
            "formal_registry": "PENDING",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": 12,
        }
    else:
        source = {
            "status": "UNKNOWN",
            "protocol_target": "UNKNOWN",
            "report_target": "UNKNOWN",
            "protocol_registration_status": "UNKNOWN",
            "report20_consumer_status": "UNKNOWN",
            "stability_policy_status": "UNKNOWN",
        }
        gap = {
            "status": "UNKNOWN",
            "formal_registry_status": "UNKNOWN",
            "schema20_writer_status": "UNKNOWN",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": "UNKNOWN",
            "stability_policy": "UNKNOWN",
            "report20_consumer": "UNKNOWN",
            "formal_registry": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": None,
        }
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": source,
        "gap": gap,
        "maturity": maturity,
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
    registration: Any,
) -> dict[str, Any]:
    try:
        verification = (
            verify_strategy_correlation_cluster_stability_protocol_registration(
                registration
            )
            if type(registration) is dict
            else {"status": "BLOCK"}
        )
    except (TypeError, ValueError):
        verification = {"status": "BLOCK"}
    observed = (
        type(registration) is dict
        and not strict_research_authority_violations(registration)
        and verification.get("status") == "PASS"
    )
    return _summary(observed)


def verify_strategy_correlation_cluster_stability_protocol_migration_public_summary(
    document: Any,
    *,
    registration: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_cluster_stability_protocol_migration_public_summary(
            registration
        )
    )
    blockers: list[str] = []
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
        "writer_prerequisite_count": (
            expected["maturity"]["writer_prerequisite_count"]
            if status == "PASS"
            else None
        ),
        "formal_registry_bound": False,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_stability_protocol_migration_public_summary",
    "verify_strategy_correlation_cluster_stability_protocol_migration_public_summary",
]
