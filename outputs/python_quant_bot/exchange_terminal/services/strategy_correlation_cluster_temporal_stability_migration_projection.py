"""Redacted public projection for report21 and protocol-v10 temporal stability."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_protocol import (
    verify_strategy_correlation_cluster_temporal_stability_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-cluster-temporal-stability-migration-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA = (
    "strategy-correlation-cluster-temporal-stability-migration-public-summary-v1-verification-v1"
)
STATIC_FINGERPRINT = "20260821-temporal-report21-protocol-v10-lockboard-1"
WRITER_PREREQUISITE_COUNT = 13

_NOT_SUPPLIED = object()
_PERMISSION = {
    "status": "RESEARCH_ONLY",
    "descriptive_only": True,
    "profitability_claim_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "formal_registry_activation_allowed": False,
    "report_writer_activation_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
}
_REDACTION = {
    "registration_hashes_exposed": False,
    "extension_hashes_exposed": False,
    "policy_hashes_exposed": False,
    "source_registration_exposed": False,
    "report_extensions_exposed": False,
    "external_bindings_exposed": False,
    "strategy_identities_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
    "correlation_values_exposed": False,
    "interval_values_exposed": False,
    "return_values_exposed": False,
    "completed_price_datasets_exposed": False,
    "profitability_metrics_exposed": False,
}


def _summary(
    registration_observed: bool,
    report_contract_status: str,
    decision: str | None,
) -> dict[str, Any]:
    if not registration_observed:
        source = {
            "status": "UNKNOWN",
            "protocol_target": "UNKNOWN",
            "report_target": "UNKNOWN",
            "protocol_registration_status": "UNKNOWN",
            "report21_consumer_status": "UNKNOWN",
            "temporal_policy_status": "UNKNOWN",
            "report21_contract_status": "UNKNOWN",
            "registration_report_pairing_status": "UNKNOWN",
        }
        gap = {
            "status": "UNKNOWN",
            "temporal_decision": "UNKNOWN",
            "formal_binding_status": "UNKNOWN",
            "formal_registry_status": "UNKNOWN",
            "schema21_writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": "UNKNOWN",
            "temporal_policy": "UNKNOWN",
            "report21_consumer": "UNKNOWN",
            "report21_contract": "UNKNOWN",
            "consumer_decision": "UNKNOWN",
            "formal_binding": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": None,
        }
    else:
        pairing_status = {
            "NOT_SUPPLIED": "NOT_SUPPLIED",
            "UNKNOWN": "UNKNOWN",
            "VERIFIED": "NOT_FORMALLY_BOUND",
        }[report_contract_status]
        source = {
            "status": "OBSERVED",
            "protocol_target": "PROTOCOL_V10",
            "report_target": "REPORT21",
            "protocol_registration_status": "PREREGISTERED",
            "report21_consumer_status": "AVAILABLE",
            "temporal_policy_status": "SEALED",
            "report21_contract_status": report_contract_status,
            "registration_report_pairing_status": pairing_status,
        }
        if report_contract_status == "NOT_SUPPLIED":
            gap_status = "REPORT21_CONTRACT_NOT_SUPPLIED"
            maturity_status = "PROTOCOL_PREREGISTERED_REPORT_NOT_SUPPLIED"
            public_decision = "NOT_SUPPLIED"
        elif report_contract_status == "UNKNOWN":
            gap_status = "REPORT21_CONTRACT_UNKNOWN"
            maturity_status = "PROTOCOL_PREREGISTERED_REPORT_UNKNOWN"
            public_decision = "UNKNOWN"
        elif decision == "PASS":
            gap_status = "FORMAL_BINDING_AND_WRITER_NOT_SUPPLIED"
            maturity_status = "REPORT21_CONSUMER_PASS_UNBOUND"
            public_decision = "PASS"
        else:
            gap_status = "TEMPORAL_EVIDENCE_BLOCKED_AND_UNBOUND"
            maturity_status = "REPORT21_CONSUMER_BLOCK_UNBOUND"
            public_decision = "BLOCK"
        gap = {
            "status": gap_status,
            "temporal_decision": public_decision,
            "formal_binding_status": pairing_status,
            "formal_registry_status": "NOT_SUPPLIED",
            "schema21_writer_status": "NOT_IMPLEMENTED",
            "current_activation_status": "NOT_ACTIVATED",
        }
        maturity = {
            "status": maturity_status,
            "temporal_policy": "SEALED",
            "report21_consumer": "AVAILABLE",
            "report21_contract": report_contract_status,
            "consumer_decision": public_decision,
            "formal_binding": pairing_status,
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
            "writer_prerequisite_count": WRITER_PREREQUISITE_COUNT,
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


def build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
    registration: Any,
    *,
    report21_extension: Any = _NOT_SUPPLIED,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
) -> dict[str, Any]:
    try:
        registration_verification = (
            verify_strategy_correlation_cluster_temporal_stability_protocol_registration(
                registration
            )
            if type(registration) is dict
            else {"status": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        registration_verification = {"status": "BLOCK"}
    registration_observed = (
        type(registration) is dict
        and not strict_research_authority_violations(registration)
        and registration_verification.get("status") == "PASS"
    )
    if not registration_observed:
        return _summary(False, "UNKNOWN", None)
    if report21_extension is _NOT_SUPPLIED:
        return _summary(True, "NOT_SUPPLIED", None)

    try:
        report_verification = (
            verify_strategy_correlation_cluster_temporal_stability_report_extension(
                report21_extension,
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
            if type(report21_extension) is dict
            else {"status": "BLOCK", "decision": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        report_verification = {"status": "BLOCK", "decision": "BLOCK"}
    if report_verification.get("status") != "PASS":
        return _summary(True, "UNKNOWN", None)
    decision = report_verification.get("decision")
    if decision not in {"PASS", "BLOCK"}:
        return _summary(True, "UNKNOWN", None)
    return _summary(True, "VERIFIED", decision)


def verify_strategy_correlation_cluster_temporal_stability_migration_public_summary(
    document: Any,
    *,
    registration: Any,
    report21_extension: Any = _NOT_SUPPLIED,
    expected_base_report_hash: Any = None,
    expected_global_independence_extension_hash: Any = None,
    expected_cluster_stability_extension_hash: Any = None,
    expected_registry_bindings: Any = None,
    expected_stability_bindings: Any = None,
    expected_temporal_stability_bindings: Any = None,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_temporal_stability_migration_public_summary(
        registration,
        report21_extension=report21_extension,
        expected_base_report_hash=expected_base_report_hash,
        expected_global_independence_extension_hash=(
            expected_global_independence_extension_hash
        ),
        expected_cluster_stability_extension_hash=(
            expected_cluster_stability_extension_hash
        ),
        expected_registry_bindings=expected_registry_bindings,
        expected_stability_bindings=expected_stability_bindings,
        expected_temporal_stability_bindings=expected_temporal_stability_bindings,
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
        "report21_contract_status": (
            expected["source"]["report21_contract_status"]
            if status == "PASS"
            else "UNKNOWN"
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
    "WRITER_PREREQUISITE_COUNT",
    "build_strategy_correlation_cluster_temporal_stability_migration_public_summary",
    "verify_strategy_correlation_cluster_temporal_stability_migration_public_summary",
]
