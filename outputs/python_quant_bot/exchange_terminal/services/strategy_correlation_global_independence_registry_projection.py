"""Registry-aware redacted public projection for protocol-v8 migration."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_global_independence_protocol_projection import (
    build_strategy_correlation_global_independence_protocol_migration_public_summary,
)
from exchange_terminal.services.strategy_correlation_global_independence_registry import (
    verify_strategy_correlation_global_independence_registry_asset,
    verify_strategy_correlation_global_independence_registry_binding,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-global-independence-protocol-migration-public-summary-v2"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-global-independence-protocol-migration-public-summary-v2-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260821-global-independence-registry-candidate-migration-seal-1"
)

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
    "registry_candidate_identity_exposed": False,
    "registry_candidate_hash_exposed": False,
    "registry_source_exposed": False,
    "registry_source_hash_exposed": False,
    "selection_cutoff_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
}
_OPTIONAL_FIELDS = (
    "registry_asset",
    "registry_binding",
    "evidence_cutoff_date",
    "expected_registry_asset_hash",
    "expected_registry_source_hash",
    "expected_protocol_registration_hash",
    "expected_global_independence_policy_hash",
)


def _source(status: str) -> dict[str, Any]:
    if status == "UNKNOWN":
        return {
            "status": "UNKNOWN",
            "protocol_target": "UNKNOWN",
            "report_target": "UNKNOWN",
            "protocol_registration_status": "UNKNOWN",
            "report19_consumer_status": "UNKNOWN",
            "global_independence_policy_status": "UNKNOWN",
            "registry_candidate_contract_status": "UNKNOWN",
        }
    return {
        "status": "OBSERVED",
        "protocol_target": "PROTOCOL_V8",
        "report_target": "REPORT19",
        "protocol_registration_status": "PREREGISTERED",
        "report19_consumer_status": "AVAILABLE",
        "global_independence_policy_status": "SEALED",
        "registry_candidate_contract_status": "AVAILABLE",
    }


def _summary(state: str) -> dict[str, Any]:
    if state == "UNKNOWN":
        gap = {
            "status": "UNKNOWN",
            "registry_candidate_status": "UNKNOWN",
            "formal_registry_status": "UNKNOWN",
            "schema19_writer_status": "UNKNOWN",
            "current_activation_status": "UNKNOWN",
        }
        maturity = {
            "status": "UNKNOWN",
            "registry_candidate": "UNKNOWN",
            "exact_graph_policy": "UNKNOWN",
            "formal_registry": "UNKNOWN",
            "writer": "UNKNOWN",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": None,
        }
    else:
        states = {
            "NOT_SUPPLIED": (
                "REGISTRY_CANDIDATE_NOT_SUPPLIED",
                "NOT_SUPPLIED",
                "PROTOCOL_PREREGISTERED",
            ),
            "BLOCK": (
                "REGISTRY_CANDIDATE_BINDING_BLOCK",
                "BLOCK",
                "CANDIDATE_EVIDENCE_BLOCKED",
            ),
            "CANDIDATE_BOUND": (
                "FORMAL_REGISTRY_AND_WRITER_NOT_SUPPLIED",
                "CANDIDATE_BOUND",
                "REGISTRY_CANDIDATE_BOUND",
            ),
        }
        gap_status, candidate_status, maturity_status = states[state]
        gap = {
            "status": gap_status,
            "registry_candidate_status": candidate_status,
            "formal_registry_status": "NOT_SUPPLIED",
            "schema19_writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": maturity_status,
            "registry_candidate": candidate_status,
            "exact_graph_policy": "SEALED",
            "formal_registry": "PENDING",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": 7,
        }
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": _source("UNKNOWN" if state == "UNKNOWN" else "OBSERVED"),
        "gap": gap,
        "maturity": maturity,
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_global_independence_registry_migration_public_summary(
    source_protocol_registration: Any,
    *,
    registry_asset: Any = None,
    registry_binding: Any = None,
    evidence_cutoff_date: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_registry_source_hash: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_global_independence_policy_hash: Any = None,
) -> dict[str, Any]:
    base = (
        build_strategy_correlation_global_independence_protocol_migration_public_summary(
            source_protocol_registration
        )
    )
    if base["source"]["status"] != "OBSERVED":
        return _summary("UNKNOWN")

    optional = {
        "registry_asset": registry_asset,
        "registry_binding": registry_binding,
        "evidence_cutoff_date": evidence_cutoff_date,
        "expected_registry_asset_hash": expected_registry_asset_hash,
        "expected_registry_source_hash": expected_registry_source_hash,
        "expected_protocol_registration_hash": expected_protocol_registration_hash,
        "expected_global_independence_policy_hash": (
            expected_global_independence_policy_hash
        ),
    }
    supplied = [optional[field] is not None for field in _OPTIONAL_FIELDS]
    if not any(supplied):
        return _summary("NOT_SUPPLIED")
    if not all(supplied):
        return _summary("BLOCK")
    if any(
        strict_research_authority_violations(value)
        for value in (registry_asset, registry_binding)
    ):
        return _summary("BLOCK")

    asset_verification = (
        verify_strategy_correlation_global_independence_registry_asset(
            registry_asset,
            protocol_registration=source_protocol_registration,
        )
    )
    binding_verification = (
        verify_strategy_correlation_global_independence_registry_binding(
            registry_binding,
            registry_asset=registry_asset,
            protocol_registration=source_protocol_registration,
            evidence_cutoff_date=evidence_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_registry_source_hash=expected_registry_source_hash,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_global_independence_policy_hash=(
                expected_global_independence_policy_hash
            ),
        )
    )
    candidate_bound = (
        asset_verification.get("status") == "PASS"
        and binding_verification.get("status") == "PASS"
        and type(registry_binding) is dict
        and registry_binding.get("status") == "CANDIDATE_BOUND"
        and type(registry_binding.get("candidate_bound")) is bool
        and registry_binding.get("candidate_bound") is True
        and type(registry_binding.get("formal_registry_bound")) is bool
        and registry_binding.get("formal_registry_bound") is False
    )
    return _summary("CANDIDATE_BOUND" if candidate_bound else "BLOCK")


def verify_strategy_correlation_global_independence_registry_migration_public_summary(
    document: Any,
    *,
    source_protocol_registration: Any,
    registry_asset: Any = None,
    registry_binding: Any = None,
    evidence_cutoff_date: Any = None,
    expected_registry_asset_hash: Any = None,
    expected_registry_source_hash: Any = None,
    expected_protocol_registration_hash: Any = None,
    expected_global_independence_policy_hash: Any = None,
) -> dict[str, Any]:
    expected = build_strategy_correlation_global_independence_registry_migration_public_summary(
        source_protocol_registration,
        registry_asset=registry_asset,
        registry_binding=registry_binding,
        evidence_cutoff_date=evidence_cutoff_date,
        expected_registry_asset_hash=expected_registry_asset_hash,
        expected_registry_source_hash=expected_registry_source_hash,
        expected_protocol_registration_hash=expected_protocol_registration_hash,
        expected_global_independence_policy_hash=(
            expected_global_independence_policy_hash
        ),
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
        "registry_candidate_status": (
            expected["gap"]["registry_candidate_status"]
            if status == "PASS"
            else "UNKNOWN"
        ),
        "formal_registry_bound": False,
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
    "build_strategy_correlation_global_independence_registry_migration_public_summary",
    "verify_strategy_correlation_global_independence_registry_migration_public_summary",
]
